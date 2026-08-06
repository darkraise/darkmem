"""Layer-1 graph assertions derived from a repository's imports (doc 10 §6).

The narrow, deterministic, LLM-free half of the code bridge. It reads the
already-indexed code graph — the ``imports`` edges and the indexed file list —
and mints memory-side graph rows through the closed taxonomy: the repository
itself as a ``project``, every external dependency module as a
``tool``/``service``/``database``/… entity, every indexed language as a
``language`` entity, and one relation from the repo to each.

**The crossing is application-level and one-direction.** Every read here names
only code-side tables; every write goes through
``PostgresGraphRepository.assert_from_repo``, which names only memory-side
tables. No statement mentions both, which is what keeps the never-join
invariant structural rather than a matter of discipline (doc 10 §2).

**Imports are the entire reach.** Symbols, calls, communities and processes
never originate facts, and nothing here climbs to Layer 2 — a repo-asserted
entity is a candidate signal, not a verified fact.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.graph import PostgresGraphRepository
from app.services.extraction_clean import _TYPE_OVERRIDES
from app.services.suffix_index import SuffixIndex
from app.taxonomy import (
    normalize_entity_type,
    normalize_relation_type,
    refine_entity_type,
)

# A dependency the repo pulls in is something it *depends on*; a datastore,
# a running service or a wire protocol is something it *uses*. Both live in
# RELATIONSHIP_TYPES and both pass through normalize_relation_type, so the
# split is a naming choice inside the closed vocabulary, not an extension of
# it.
_USES_ENTITY_TYPES = frozenset({"database", "service", "protocol"})

# Import prefixes that can only ever name something inside this repository:
# a dotted or slash relative import, an absolute in-repo path, a bundler
# root alias (`@/components/x`, `~/lib/y`) or a Node subpath import
# (`#internal/x`). None of these can resolve to a published package.
_INTERNAL_PREFIXES = (".", "/", "@/", "~/", "#")

# Node's own builtin modules, which `node:`-prefixed imports also name. The
# Python half of the same question is answered by the interpreter itself
# (`sys.stdlib_module_names`) rather than by a list maintained here.
_NODE_BUILTINS = frozenset({
    "assert", "async_hooks", "buffer", "child_process", "cluster", "console",
    "constants", "crypto", "dgram", "diagnostics_channel", "dns", "domain",
    "events", "fs", "http", "http2", "https", "inspector", "module", "net",
    "os", "path", "perf_hooks", "process", "punycode", "querystring",
    "readline", "repl", "stream", "string_decoder", "sys", "timers", "tls",
    "trace_events", "tty", "url", "util", "v8", "vm", "wasi", "worker_threads",
    "zlib",
})

# A Go import path starts with a host (`github.com/org/repo`); the module is
# the first three segments, not the first one, which would assert `github.com`
# as a dependency of every Go repository indexed.
_HOSTLIKE_SEGMENT = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$", re.IGNORECASE)

_MIN_DEPENDENCY_NAME_LENGTH = 2


@dataclass(frozen=True)
class DerivedAssertions:
    """What one repository asserts, before any of it is written."""

    repo_id: UUID
    entities: list[dict] = field(default_factory=list)
    relations: list[dict] = field(default_factory=list)
    # Import sources classified as repo-internal, kept for the caller's
    # diagnostics: the internal/external line is the deriver's single
    # highest-leverage judgement and an operator needs to see where it fell.
    internal_imports: list[str] = field(default_factory=list)


def _entity_type_for(name: str, default_raw_type: str) -> str:
    """The closed-taxonomy type for a derived name.

    Runs the same curated-override -> normalise -> name-refine ladder the
    extraction path runs, so a name minted from code lands on the *same*
    ``(name, entity_type)`` row as the same name minted from a memory. Sending
    the two through different ladders would produce two nodes for one thing and
    forfeit the anchoring the bridge exists for.
    """
    raw = _TYPE_OVERRIDES.get(name, default_raw_type)
    return refine_entity_type(name, normalize_entity_type(raw))


def _relation_type_for(entity_type: str) -> str:
    raw = "USES" if entity_type in _USES_ENTITY_TYPES else "DEPENDS_ON"
    return normalize_relation_type(raw)


def _entity(name: str, entity_type: str) -> dict:
    canonical = name.strip().lower()
    properties: dict = {}
    if name.strip() != canonical:
        properties["display_name"] = name.strip()
    return {"name": canonical, "entity_type": entity_type, "properties": properties}


def is_internal_import(source: str, suffix_index: SuffixIndex) -> bool:
    """Whether an import source names a file inside this repository.

    Two rules, in order: a prefix that can only be repo-relative, then a
    suffix match against the repo's own indexed file list — the same
    ``SuffixIndex`` the indexer itself consults first when resolving imports,
    so the deriver's line falls exactly where the indexer's does.

    The suffix rule is deliberately ambiguity-tolerant, and that biases the
    deriver toward *excluding*: a repo file named ``redis.ts`` makes a real
    ``redis`` dependency look internal and costs one assertion, whereas the
    opposite bias would mint a dependency the repository does not have. For a
    fact-originating bridge a missing fact is cheaper than a wrong one.
    """
    stripped = source.strip()
    if not stripped:
        return True
    normalized = stripped.replace("\\", "/")
    if normalized.startswith(_INTERNAL_PREFIXES):
        return True
    return suffix_index.matches(normalized)


def dependency_name(source: str) -> str | None:
    """The package an import source names, or ``None`` if it names none.

    ``None`` covers the two cases that are not dependencies at all: a builtin
    module (the language's own standard library, which every repo in that
    language has and which therefore distinguishes nothing) and a name too
    short to be anything but noise. A builtin that the corpus has already
    curated a type for — ``asyncio`` is the live example — is kept, because
    the curated table is the corpus saying that name does carry meaning.
    """
    normalized = source.strip().replace("\\", "/").rstrip("/")
    if not normalized:
        return None
    if normalized.startswith("node:"):
        return None

    segments = normalized.split("/")
    if normalized.startswith("@") and len(segments) >= 2:
        head = "/".join(segments[:2])
    elif len(segments) >= 3 and _HOSTLIKE_SEGMENT.match(segments[0]):
        head = "/".join(segments[:3])
    else:
        head = segments[0]

    # A dotted head is a package path (`sqlalchemy.ext.asyncio`); its root is
    # the dependency. A curated dotted name (`next.js`) is the exception the
    # extraction path makes too — its tail is part of the real name.
    if "/" not in head and "." in head and head.lower() not in _TYPE_OVERRIDES:
        head = head.split(".")[0]

    name = head.strip()
    if len(name) < _MIN_DEPENDENCY_NAME_LENGTH:
        return None
    lowered = name.lower()
    if lowered in _TYPE_OVERRIDES:
        return name
    if lowered in sys.stdlib_module_names or lowered in _NODE_BUILTINS:
        return None
    return name


async def derive_assertions(session: AsyncSession, repo_id: UUID | str) -> DerivedAssertions:
    """Read one repository's code graph and build its Layer-1 assertions.

    Reads only; nothing here writes. Every statement names code-side tables
    exclusively.
    """
    rid = str(repo_id)

    repo_name = (await session.execute(
        text("SELECT name FROM repositories WHERE id = CAST(:rid AS uuid)"),
        {"rid": rid},
    )).scalar_one_or_none()
    if repo_name is None:
        raise ValueError(f"Repository not found: {rid}")

    file_rows = (await session.execute(
        text("SELECT file_path, language FROM code_files "
             "WHERE repo_id = CAST(:rid AS uuid)"),
        {"rid": rid},
    )).mappings().all()
    file_paths = [row["file_path"] for row in file_rows]
    languages = sorted({
        row["language"].strip().lower()
        for row in file_rows
        if row["language"] and row["language"].strip()
    })

    import_sources = [
        row for row in (await session.execute(
            text("""
                SELECT DISTINCT target_key
                FROM code_edges
                WHERE repo_id = CAST(:rid AS uuid)
                  AND edge_type = 'imports'
                  AND source_kind = 'file'
                  AND target_kind = 'module'
                ORDER BY target_key
            """),
            {"rid": rid},
        )).scalars().all()
    ]

    suffix_index = SuffixIndex(file_paths)

    repo_entity = _entity(repo_name, _entity_type_for(repo_name.strip().lower(), "project"))
    entities: dict[tuple[str, str], dict] = {
        (repo_entity["name"], repo_entity["entity_type"]): repo_entity
    }
    relations: dict[tuple[str, str, str, str, str], dict] = {}
    internal: list[str] = []

    def add(name: str, default_raw_type: str) -> None:
        entity_type = _entity_type_for(name.strip().lower(), default_raw_type)
        entity = _entity(name, entity_type)
        key = (entity["name"], entity["entity_type"])
        if key == (repo_entity["name"], repo_entity["entity_type"]):
            return
        entities.setdefault(key, entity)
        rel_type = _relation_type_for(entity["entity_type"])
        relations.setdefault(
            (repo_entity["name"], repo_entity["entity_type"],
             entity["name"], entity["entity_type"], rel_type),
            {
                "source": repo_entity["name"],
                "source_type": repo_entity["entity_type"],
                "target": entity["name"],
                "target_type": entity["entity_type"],
                "rel_type": rel_type,
                "properties": {},
                "weight": 1.0,
            },
        )

    for language in languages:
        add(language, "language")

    for source in import_sources:
        if is_internal_import(source, suffix_index):
            internal.append(source)
            continue
        name = dependency_name(source)
        if name is None:
            continue
        add(name, "tool")

    return DerivedAssertions(
        repo_id=UUID(rid),
        entities=list(entities.values()),
        relations=list(relations.values()),
        internal_imports=internal,
    )


async def assert_repo_graph(session: AsyncSession, repo_id: UUID | str) -> dict:
    """Derive one repository's assertions and replace its prior ones."""
    derived = await derive_assertions(session, repo_id)
    written = await PostgresGraphRepository(session).assert_from_repo(
        derived.repo_id, derived.entities, derived.relations,
    )
    return {
        "repo_id": str(derived.repo_id),
        "entities": written["entities"],
        "relations": written["relations"],
        "internal_imports": len(derived.internal_imports),
    }

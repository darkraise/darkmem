"""Doc 10 §6 / doc 06 §6.1 — the imports-only, LLM-free code deriver.

Four things are asserted here, and each of them is the kind of property a
naive test passes without proving:

* **Imports only, no LLM anywhere in the path** — proven structurally, by
  parsing every module in the deriver's transitive ``app`` import closure and
  failing on any AST-visible route to a dispatch surface. A source scan that
  matched line *text* would fire on prose in a comment and, worse, would be
  loosened the first time it did; this one walks the parsed tree.
* **The existing sweeps still behave correctly with ``repo_ids`` populated** —
  they were reviewed and frozen while every array was empty, so their
  ``NOT EXISTS (live repo)`` predicates had never once executed against a
  non-empty array. These tests are their first real exercise: a row a live
  repo asserts survives, a row only a *dead* repo asserts does not, and an
  edge whose endpoint was spared for repo reasons keeps its edge.
* **Re-derivation is idempotent per repo** — asserted by comparing full row
  contents across three runs, not row counts, and by asserting the repo id
  appears exactly *once* in each array. A second run over an empty derivation
  would satisfy a count comparison while proving nothing, so a changed import
  set is asserted to produce a changed graph in the same module.
* **The strip and the write are one atomic replace** — a write that fails
  mid-way leaves the repo's *previous* assertions standing, never the
  half-state where the strip landed and the write did not.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.services.code_deriver import (
    DERIVABLE_IMPORT_LANGUAGES,
    UNDERIVABLE_IMPORT_LANGUAGES,
    _entity_type_for,
    assert_repo_graph,
    dependency_name,
    derive_assertions,
    is_internal_import,
)
from app.services.suffix_index import SuffixIndex
from app.taxonomy import ENTITY_TYPES, RELATIONSHIP_TYPES
from tests._reachability_scan import ReachabilityRules, find_forbidden_reach

BACKEND = Path(__file__).resolve().parent.parent

REPO_FILES = [
    ("backend/app/services/store.py", "python"),
    ("backend/app/repositories/vault.py", "python"),
    ("frontend/src/components/Panel.tsx", "typescript"),
]

EXTERNAL_IMPORTS = [
    "sqlalchemy.ext.asyncio",
    "fastapi",
    "redis",
    "@tanstack/react-router",
    "react-dom/client",
]

INTERNAL_IMPORTS = [
    "app.services.store",
    ".vault",
    "../components/Panel",
    "@/components/Panel",
]

BUILTIN_IMPORTS = ["os", "json", "node:fs", "path"]


async def _seed_repo(
    session,
    name: str = "Deriver-Repo",
    files: list[tuple[str, str | None]] | None = None,
    imports: list[str] | None = None,
) -> UUID:
    repo_id = uuid4()
    await session.execute(
        text("INSERT INTO repositories (id, name, auto_sync, status) "
             "VALUES (CAST(:id AS uuid), :name, false, 'ready')"),
        {"id": str(repo_id), "name": name},
    )
    for file_path, language in (files if files is not None else REPO_FILES):
        await session.execute(
            text("INSERT INTO code_files (id, repo_id, file_path, language) "
                 "VALUES (CAST(:id AS uuid), CAST(:rid AS uuid), :fp, :lang)"),
            {"id": str(uuid4()), "rid": str(repo_id), "fp": file_path, "lang": language},
        )
    sources = imports if imports is not None else (
        EXTERNAL_IMPORTS + INTERNAL_IMPORTS + BUILTIN_IMPORTS
    )
    for entry in sources:
        # A bare string is an import from the repo's first file; a pair names
        # the importing file, which is what carries the language.
        importing_file, source = (
            entry if isinstance(entry, tuple) else (REPO_FILES[0][0], entry)
        )
        await session.execute(
            text("""
                INSERT INTO code_edges
                    (repo_id, source_kind, source_key, target_kind, target_key, edge_type)
                VALUES (CAST(:rid AS uuid), 'file', :src, 'module', :tgt, 'imports')
                ON CONFLICT DO NOTHING
            """),
            {"rid": str(repo_id), "src": importing_file, "tgt": source},
        )
    await session.flush()
    return repo_id


async def _repo_snapshot(session, repo_id: UUID) -> dict:
    """Full contents of everything one repo asserts, order-normalised.

    Contents rather than counts: a row-count comparison passes over a graph
    with the right cardinality and the wrong contents. Row *ids* are excluded,
    the same discipline ``test_idempotent_reextraction.py`` applies to the
    memory path and for the same reason — under strip-before-rewrite a row no
    other asserter holds is deleted and re-inserted, so its id necessarily
    changes. The identity that must survive is the identity of a *shared* row,
    which the strip's delete guard spares; that is asserted separately.
    """
    entity_rows = (await session.execute(
        text("""
            SELECT id, name, entity_type, properties, memory_ids, repo_ids
            FROM entities
            WHERE CAST(:rid AS uuid) = ANY(repo_ids)
            ORDER BY name, entity_type
        """),
        {"rid": str(repo_id)},
    )).mappings().all()
    relation_rows = (await session.execute(
        text("""
            SELECT s.name AS source, s.entity_type AS source_type,
                   t.name AS target, t.entity_type AS target_type,
                   r.rel_type, r.weight, r.memory_ids, r.repo_ids
            FROM entity_relations r
            JOIN entities s ON s.id = r.source_entity_id
            JOIN entities t ON t.id = r.target_entity_id
            WHERE CAST(:rid AS uuid) = ANY(r.repo_ids)
            ORDER BY s.name, t.name, r.rel_type
        """),
        {"rid": str(repo_id)},
    )).mappings().all()
    return {
        "entities": [
            (
                row["name"], row["entity_type"],
                dict(row["properties"] or {}).get("display_name"),
                tuple(sorted(str(m) for m in (row["memory_ids"] or []))),
                tuple(str(r) for r in (row["repo_ids"] or [])),
            )
            for row in entity_rows
        ],
        "relations": [
            (
                row["source"], row["source_type"], row["target"], row["target_type"],
                row["rel_type"], row["weight"],
                tuple(sorted(str(m) for m in (row["memory_ids"] or []))),
                tuple(str(r) for r in (row["repo_ids"] or [])),
            )
            for row in relation_rows
        ],
    }


# ── the internal/external line ───────────────────────────────────────────

def _index() -> SuffixIndex:
    return SuffixIndex([path for path, _ in REPO_FILES])


@pytest.mark.parametrize("source", INTERNAL_IMPORTS)
def test_repo_local_imports_are_never_dependencies(source):
    assert is_internal_import(source, _index())


@pytest.mark.parametrize("source", EXTERNAL_IMPORTS)
def test_published_packages_are_dependencies(source):
    assert not is_internal_import(source, _index())


def test_an_ambiguous_repo_suffix_still_counts_as_internal():
    # Two files share the `panel` suffix, so SuffixIndex.lookup() refuses to
    # pick one. Internal-vs-external does not need a pick — and reading the
    # refusal as "not in this repo" would mint a dependency the repo does not
    # have, the one direction this classifier must never err in.
    index = SuffixIndex(["src/a/panel.ts", "src/b/panel.ts"])
    assert index.lookup("panel") is None
    assert is_internal_import("panel", index)


@pytest.mark.parametrize("source", BUILTIN_IMPORTS)
def test_builtin_modules_are_not_dependencies(source):
    assert dependency_name(source) is None


def test_a_curated_builtin_survives():
    # `asyncio` is stdlib and would be dropped by the builtin rule, but the
    # curated override table types it as a tool — the corpus saying this name
    # carries meaning. The exemption is what keeps the two paths agreeing.
    assert dependency_name("asyncio") == "asyncio"


@pytest.mark.parametrize(
    "source,expected",
    [
        ("sqlalchemy.ext.asyncio", "sqlalchemy"),
        ("@tanstack/react-router", "@tanstack/react-router"),
        ("react-dom/client", "react-dom"),
        ("github.com/gin-gonic/gin", "github.com/gin-gonic/gin"),
        ("next.js", "next.js"),
        ("fastapi", "fastapi"),
    ],
)
def test_a_dependency_collapses_to_its_package_root(source, expected):
    assert dependency_name(source) == expected


# ── the languages the deriver can actually parse ─────────────────────────

# What the indexer writes for the grammars this module does not parse: raw
# statement text where the one-level scan found no dotted-name or string
# child, and scoped names whose root segment is meaningless. Every one of
# these produced an `entities` row before the language gate landed.
POLYGLOT_FILES = [
    ("src/main.rs", "rust"),
    ("cmd/serve.go", "go"),
    ("src/App.java", "java"),
    ("src/Api.cs", "csharp"),
]

POLYGLOT_IMPORTS = [
    ("src/main.rs", "use std::collections::HashMap;"),
    ("src/main.rs", "std::collections::HashMap"),
    ("cmd/serve.go", 'import "fmt"'),
    ("cmd/serve.go", "fmt"),
    ("cmd/serve.go", "encoding/json"),
    ("src/App.java", "com.fasterxml.jackson.databind"),
    ("src/App.java", "java.util.List"),
    ("src/Api.cs", "System.Collections.Generic"),
]


def test_every_indexed_language_is_classified_one_way_or_the_other():
    """A new indexed language must be a decision, not a default.

    ``code_parser.EXTENSION_TO_LANGUAGE`` widens freely — it is the indexer's
    business — while the deriver's import rules are Python's and JS/TS's and
    nobody else's. If a grammar joins the indexer without joining one of these
    two sets, the deriver would start reading its import statements with rules
    that do not fit them, which is how ``use std::collections::hashmap;``
    became a ``tool``. Fail the build at that moment instead.
    """
    from app.services.code_parser import EXTENSION_TO_LANGUAGE

    # `unknown` is `_fallback_parse`'s label for a file no grammar handled;
    # it reaches `code_files.language` like any other value.
    indexed = set(EXTENSION_TO_LANGUAGE.values()) | {"unknown"}
    unclassified = (
        indexed - DERIVABLE_IMPORT_LANGUAGES - UNDERIVABLE_IMPORT_LANGUAGES
    )
    assert not unclassified, (
        "the indexer learned a language the deriver has not been told about: "
        f"{sorted(unclassified)}. Either teach `dependency_name` its import "
        "shape and add it to DERIVABLE_IMPORT_LANGUAGES, or add it to "
        "UNDERIVABLE_IMPORT_LANGUAGES so its imports are skipped and counted."
    )
    assert not DERIVABLE_IMPORT_LANGUAGES & UNDERIVABLE_IMPORT_LANGUAGES


@pytest.mark.parametrize(
    "source",
    [
        "use std::collections::HashMap;",
        "std::collections::HashMap",
        'import "fmt"',
        "from typing import Any",
        "#include <stdio.h>",
    ],
)
def test_a_name_that_is_not_lexically_a_package_is_never_a_dependency(source):
    # The last stop before a name becomes an `entities` row, behind the
    # language gate rather than instead of it: a package name is one lexical
    # token, so whitespace, quotes, a terminator or a scope operator means
    # this is statement text, not a name anyone resolved.
    assert dependency_name(source) is None


@pytest.mark.asyncio
async def test_a_language_the_deriver_cannot_parse_asserts_no_dependency(session):
    """The whole of I5, as one repository.

    Every source here is what the indexer really writes for these grammars,
    and every one of them minted an entity before: a ``tool`` literally named
    ``use std::collections::hashmap;``, plus ``fmt``, ``encoding``, ``com``,
    ``java`` and ``system``. A repository the deriver cannot read now asserts
    its own name and its languages — facts that are true — and nothing else.
    """
    repo_id = await _seed_repo(
        session, name="polyglot-repo",
        files=POLYGLOT_FILES, imports=POLYGLOT_IMPORTS,
    )
    derived = await derive_assertions(session, repo_id)

    assert {entity["name"] for entity in derived.entities} == {
        "polyglot-repo", "rust", "go", "java", "csharp",
    }
    assert derived.skipped_by_language == {
        "csharp": 1, "go": 3, "java": 2, "rust": 2,
    }


@pytest.mark.asyncio
async def test_a_polyglot_repo_derives_from_the_half_it_can_read(session):
    # The gate is per importing file, not per repository: a Python service
    # with a Rust sidecar keeps its Python dependencies.
    repo_id = await _seed_repo(
        session, name="mixed-repo",
        files=[("backend/app/main.py", "python"), ("src/main.rs", "rust")],
        imports=[
            ("backend/app/main.py", "fastapi"),
            ("src/main.rs", "use std::collections::HashMap;"),
        ],
    )
    derived = await derive_assertions(session, repo_id)

    names = {entity["name"] for entity in derived.entities}
    assert "fastapi" in names
    assert names == {"mixed-repo", "python", "rust", "fastapi"}
    assert derived.skipped_by_language == {"rust": 1}


@pytest.mark.asyncio
async def test_an_unparsed_file_never_becomes_a_language(session):
    # `unknown` is a parse failure, not a language the repository is written
    # in — the same class of wrong fact the import gate exists to stop.
    repo_id = await _seed_repo(
        session, name="opaque-repo",
        files=[("data/blob.bin", "unknown"), ("app/x.py", "python")],
        imports=[],
    )
    derived = await derive_assertions(session, repo_id)

    assert {entity["name"] for entity in derived.entities} == {
        "opaque-repo", "python",
    }


# ── the closed taxonomy ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_every_derived_type_is_in_the_closed_vocabulary(session):
    repo_id = await _seed_repo(session)
    derived = await derive_assertions(session, repo_id)

    assert derived.entities
    for entity in derived.entities:
        assert entity["entity_type"] in ENTITY_TYPES
    for relation in derived.relations:
        assert relation["rel_type"] in RELATIONSHIP_TYPES


def test_the_type_ladder_is_the_extraction_path_s_ladder():
    """Each rung of ``normalize -> refine`` demonstrably runs.

    Asserting only that the output lands in ``ENTITY_TYPES`` proves nothing
    here: every raw type the deriver starts from — ``project``, ``tool``,
    ``language`` and the curated table's own values — is *already* canonical,
    so a ladder that was skipped entirely would still produce a legal
    vocabulary. These three cases each need a specific rung to have run.
    """
    # LEGACY_ENTITY_TYPE_MAP rewrites a historical name.
    assert _entity_type_for("anything", "framework") == "tool"
    # An unknown type falls back to concept rather than being stored raw.
    assert _entity_type_for("anything", "widget") == "concept"
    # refine_entity_type re-types a library-shaped name away from project.
    assert _entity_type_for("darkraise-ui", "project") == "tool"


@pytest.mark.asyncio
async def test_a_library_shaped_repo_name_is_typed_as_the_corpus_types_it(session):
    # The anchoring rule applied to the repo entity itself: a name a memory
    # would land as `tool` must not land as `project` here, or the bridge
    # produces two nodes for one thing — the exact failure it exists to avoid.
    repo_id = await _seed_repo(session, name="Deriver-UI")
    await assert_repo_graph(session, repo_id)

    entity_type = (await session.execute(
        text("SELECT entity_type FROM entities WHERE name = 'deriver-ui'")
    )).scalar()
    assert entity_type == "tool"


@pytest.mark.asyncio
async def test_a_curated_datastore_is_used_not_depended_on(session):
    repo_id = await _seed_repo(session)
    derived = await derive_assertions(session, repo_id)

    redis = [e for e in derived.entities if e["name"] == "redis"]
    assert redis and redis[0]["entity_type"] == "database"
    edge = [r for r in derived.relations if r["target"] == "redis"]
    assert edge and edge[0]["rel_type"] == "USES"

    library = [r for r in derived.relations if r["target"] == "fastapi"]
    assert library and library[0]["rel_type"] == "DEPENDS_ON"


@pytest.mark.asyncio
async def test_a_repo_uses_its_languages(session):
    # Doc 10 §6 fixes this edge by name — "the relations `repo —USES/DEPENDS_ON
    # → dep` and `repo —USES→ language`". The doc leaves the dependency half
    # open and the language half closed; the deriver shipped `DEPENDS_ON` for
    # both, and no test pinned it either way.
    repo_id = await _seed_repo(session)
    derived = await derive_assertions(session, repo_id)

    languages = {
        relation["target"]: relation["rel_type"]
        for relation in derived.relations
        if relation["target_type"] == "language"
    }
    assert languages == {"python": "USES", "typescript": "USES"}


# ── what one derivation asserts ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_derivation_mints_the_repo_its_deps_and_its_languages(session):
    repo_id = await _seed_repo(session)
    await assert_repo_graph(session, repo_id)

    snapshot = await _repo_snapshot(session, repo_id)
    names = {row[0] for row in snapshot["entities"]}

    assert "deriver-repo" in names
    assert {"sqlalchemy", "fastapi", "redis", "@tanstack/react-router",
            "react-dom"} <= names
    assert {"python", "typescript"} <= names

    types = {row[0]: row[1] for row in snapshot["entities"]}
    assert types["deriver-repo"] == "project"
    assert types["python"] == "language"

    # Every relation leaves the repo entity: the deriver asserts what this
    # repository uses, never a claim between two third-party packages.
    assert {row[0] for row in snapshot["relations"]} == {"deriver-repo"}


@pytest.mark.asyncio
async def test_internal_and_builtin_imports_never_become_entities(session):
    repo_id = await _seed_repo(session)
    derived = await derive_assertions(session, repo_id)
    await assert_repo_graph(session, repo_id)

    names = {row[0] for row in (await _repo_snapshot(session, repo_id))["entities"]}
    assert not names & {"app", "vault", "panel", "os", "json", "path", "fs"}
    assert set(derived.internal_imports) == set(INTERNAL_IMPORTS)


@pytest.mark.asyncio
async def test_names_are_lowercase_with_the_original_casing_preserved(session):
    repo_id = await _seed_repo(session)
    await assert_repo_graph(session, repo_id)

    snapshot = await _repo_snapshot(session, repo_id)
    for name, _type, display, _mids, _rids in snapshot["entities"]:
        assert name == name.lower()
        if display is not None:
            assert display.lower() == name

    repo_row = [row for row in snapshot["entities"] if row[0] == "deriver-repo"]
    assert repo_row[0][2] == "Deriver-Repo"


@pytest.mark.asyncio
async def test_a_repo_assertion_carries_no_memory_id(session):
    repo_id = await _seed_repo(session)
    await assert_repo_graph(session, repo_id)

    snapshot = await _repo_snapshot(session, repo_id)
    for row in snapshot["entities"]:
        assert row[3] == ()
        assert row[4] == (str(repo_id),)
    for row in snapshot["relations"]:
        assert row[6] == ()
        assert row[7] == (str(repo_id),)


# ── idempotence, and its non-vacuous other half ──────────────────────────

@pytest.mark.asyncio
async def test_re_derivation_is_idempotent_per_repo(session):
    repo_id = await _seed_repo(session)

    await assert_repo_graph(session, repo_id)
    first = await _repo_snapshot(session, repo_id)
    assert first["entities"] and first["relations"]

    for _ in range(2):
        await assert_repo_graph(session, repo_id)
        assert await _repo_snapshot(session, repo_id) == first

    # The repo id appears once per array, never N times after N runs.
    for table in ("entities", "entity_relations"):
        worst = (await session.execute(
            text(f"""
                SELECT max(cardinality(repo_ids))
                FROM {table}
                WHERE CAST(:rid AS uuid) = ANY(repo_ids)
            """),
            {"rid": str(repo_id)},
        )).scalar()
        assert worst == 1, f"{table}.repo_ids accumulated duplicate assertions"


@pytest.mark.asyncio
async def test_a_memory_shared_entity_keeps_its_identity_and_its_asserter(session):
    """The anchoring property, and the one identity re-derivation must not churn.

    A node both a memory and a repo assert is the point of the bridge: one
    ``postgres``, not two. Re-deriving must leave that row's id alone —
    ``entity_relations`` endpoints and the embedding partitions key on it —
    and must not strip the memory's own assertion along with the repo's.
    """
    repo_id = await _seed_repo(session)
    await assert_repo_graph(session, repo_id)

    memory_id = uuid4()
    session.add(Memory(id=memory_id, content="we run redis", source="test"))
    await session.flush()
    await session.execute(
        text("UPDATE entities SET memory_ids = ARRAY[CAST(:mid AS uuid)] "
             "WHERE name = 'redis'"),
        {"mid": str(memory_id)},
    )

    before = (await session.execute(
        text("SELECT id FROM entities WHERE name = 'redis'")
    )).scalar()

    await assert_repo_graph(session, repo_id)

    after = (await session.execute(
        text("SELECT id, memory_ids, repo_ids FROM entities WHERE name = 'redis'")
    )).mappings().one()
    assert after["id"] == before, "a shared node was deleted and re-minted"
    assert [str(m) for m in after["memory_ids"]] == [str(memory_id)]
    assert [str(r) for r in after["repo_ids"]] == [str(repo_id)]


@pytest.mark.asyncio
async def test_a_changed_import_set_changes_the_derivation(session):
    repo_id = await _seed_repo(session)
    await assert_repo_graph(session, repo_id)
    before = {row[0] for row in (await _repo_snapshot(session, repo_id))["entities"]}
    assert "fastapi" in before

    await session.execute(
        text("DELETE FROM code_edges WHERE repo_id = CAST(:rid AS uuid) "
             "AND target_key = 'fastapi'"),
        {"rid": str(repo_id)},
    )
    await session.execute(
        text("""
            INSERT INTO code_edges
                (repo_id, source_kind, source_key, target_kind, target_key, edge_type)
            VALUES (CAST(:rid AS uuid), 'file', :src, 'module', 'httpx', 'imports')
        """),
        {"rid": str(repo_id), "src": REPO_FILES[0][0]},
    )
    await assert_repo_graph(session, repo_id)

    after = {row[0] for row in (await _repo_snapshot(session, repo_id))["entities"]}
    assert "fastapi" not in after
    assert "httpx" in after

    survivors = (await session.execute(
        text("SELECT count(*) FROM entities WHERE name = 'fastapi'")
    )).scalar()
    assert survivors == 0, "a withdrawn dependency nothing else asserts must go"


@pytest.mark.asyncio
async def test_a_failed_write_leaves_the_previous_assertions_standing(session):
    repo_id = await _seed_repo(session)
    await assert_repo_graph(session, repo_id)
    before = await _repo_snapshot(session, repo_id)

    graph_repo = PostgresGraphRepository(session)
    with pytest.raises(KeyError):
        await graph_repo.assert_from_repo(
            repo_id,
            [
                {"name": "landed", "entity_type": "tool", "properties": {}},
                {"name": "broken"},  # no entity_type: raises after the strip
            ],
            [],
        )

    assert await _repo_snapshot(session, repo_id) == before
    leaked = (await session.execute(
        text("SELECT count(*) FROM entities WHERE name = 'landed'")
    )).scalar()
    assert leaked == 0, "the failed write's first row survived its own rollback"


# ── the strip ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_strip_removes_only_this_repos_assertions(session):
    first = await _seed_repo(session, name="repo-one")
    second = await _seed_repo(session, name="repo-two")
    await assert_repo_graph(session, first)
    await assert_repo_graph(session, second)

    await PostgresGraphRepository(session).strip_repo_assertions(first)

    assert (await _repo_snapshot(session, first))["entities"] == []
    survivors = {row[0] for row in (await _repo_snapshot(session, second))["entities"]}
    assert {"sqlalchemy", "fastapi", "redis"} <= survivors


@pytest.mark.asyncio
async def test_an_entity_two_repos_assert_survives_one_strip(session):
    first = await _seed_repo(session, name="repo-one")
    second = await _seed_repo(session, name="repo-two")
    await assert_repo_graph(session, first)
    await assert_repo_graph(session, second)

    await PostgresGraphRepository(session).strip_repo_assertions(first)

    shared = (await session.execute(
        text("SELECT repo_ids FROM entities WHERE name = 'sqlalchemy'")
    )).scalar()
    assert [str(r) for r in shared] == [str(second)]


# ── the amended sweeps, exercised against a non-empty array ──────────────

async def _entity(session, name: str, memory_ids: list[str], repo_ids: list[str]) -> UUID:
    entity_id = uuid4()
    await session.execute(
        text("""
            INSERT INTO entities (id, name, entity_type, memory_ids, repo_ids)
            VALUES (CAST(:id AS uuid), :name, 'concept',
                    CAST(:mids AS uuid[]), CAST(:rids AS uuid[]))
        """),
        {"id": str(entity_id), "name": name, "mids": memory_ids, "rids": repo_ids},
    )
    return entity_id


async def _relation(
    session, source: UUID, target: UUID, memory_ids: list[str], repo_ids: list[str],
) -> UUID:
    relation_id = uuid4()
    await session.execute(
        text("""
            INSERT INTO entity_relations
                (id, source_entity_id, target_entity_id, rel_type, memory_ids, repo_ids)
            VALUES (CAST(:id AS uuid), CAST(:src AS uuid), CAST(:tgt AS uuid),
                    'RELATED_TO', CAST(:mids AS uuid[]), CAST(:rids AS uuid[]))
        """),
        {"id": str(relation_id), "src": str(source), "tgt": str(target),
         "mids": memory_ids, "rids": repo_ids},
    )
    return relation_id


async def _exists(session, table: str, row_id: UUID) -> bool:
    return bool((await session.execute(
        text(f"SELECT count(*) FROM {table} WHERE id = CAST(:id AS uuid)"),
        {"id": str(row_id)},
    )).scalar())


@pytest.mark.asyncio
async def test_the_memory_strip_spares_a_repo_asserted_entity(session):
    repo_id = await _seed_repo(session, name="sparing-repo", imports=[])
    memory_id = uuid4()
    session.add(Memory(id=memory_id, content="x", source="test"))
    await session.flush()

    shared = await _entity(session, "shared-node", [str(memory_id)], [str(repo_id)])
    lonely = await _entity(session, "lonely-node", [str(memory_id)], [])
    await session.flush()

    await PostgresGraphRepository(session).delete_by_memory_id(memory_id)

    assert await _exists(session, "entities", shared)
    assert not await _exists(session, "entities", lonely)
    remaining = (await session.execute(
        text("SELECT memory_ids FROM entities WHERE id = CAST(:id AS uuid)"),
        {"id": str(shared)},
    )).scalar()
    assert list(remaining) == []


@pytest.mark.asyncio
async def test_an_edge_survives_when_its_endpoint_is_spared_for_repo_reasons(session):
    repo_id = await _seed_repo(session, name="edge-repo", imports=[])
    stripped = uuid4()
    keeper = uuid4()
    session.add(Memory(id=stripped, content="a", source="test"))
    session.add(Memory(id=keeper, content="b", source="test"))
    await session.flush()

    # The endpoint the strip would otherwise delete, kept alive by the repo.
    endpoint = await _entity(session, "repo-endpoint", [str(stripped)], [str(repo_id)])
    other = await _entity(session, "other-endpoint", [str(keeper)], [])
    edge = await _relation(session, endpoint, other, [str(keeper)], [])
    await session.flush()

    await PostgresGraphRepository(session).delete_by_memory_id(stripped)

    assert await _exists(session, "entities", endpoint)
    assert await _exists(session, "entity_relations", edge), (
        "the endpoint FK cascades — deleting a repo-asserted endpoint would "
        "silently destroy another memory's edge"
    )


@pytest.mark.asyncio
async def test_the_memory_strip_spares_a_repo_asserted_relation(session):
    """The *relation* half of the strip's live-repo guard, both directions.

    A relation both a memory and a live repo assert is a state this task
    creates on every run: ``assert_from_repo``'s ``ON CONFLICT`` appends
    ``repo_ids`` onto a relation a memory already wrote whenever the two
    assert the same triple. Stripping that memory must leave the repo's
    assertion standing. Nothing but a string count guarded this statement
    before, and a count catches a deleted predicate, not a weakened one: swap
    ``repo_ids`` for ``memory_ids`` in it — the copy-paste slip the shape
    invites — and the count still reads six while a repo's assertion is
    silently destroyed. The ``lonely`` relation is the other direction, so
    the delete cannot pass this test by simply never running.
    """
    repo_id = await _seed_repo(session, name="relation-sparing-repo", imports=[])
    memory_id = uuid4()
    session.add(Memory(id=memory_id, content="x", source="test"))
    await session.flush()

    source = await _entity(session, "rel-source", [str(memory_id)], [str(repo_id)])
    target = await _entity(session, "rel-target", [str(memory_id)], [str(repo_id)])
    shared = await _relation(
        session, source, target, [str(memory_id)], [str(repo_id)],
    )
    lonely_source = await _entity(session, "lonely-source", [str(memory_id)], [])
    lonely_target = await _entity(session, "lonely-target", [str(memory_id)], [])
    lonely = await _relation(session, lonely_source, lonely_target, [str(memory_id)], [])
    await session.flush()

    await PostgresGraphRepository(session).delete_by_memory_id(memory_id)

    assert await _exists(session, "entity_relations", shared), (
        "the memory strip deleted a relation a live repo still asserts"
    )
    assert not await _exists(session, "entity_relations", lonely)
    remaining = (await session.execute(
        text("SELECT memory_ids FROM entity_relations WHERE id = CAST(:id AS uuid)"),
        {"id": str(shared)},
    )).scalar()
    assert list(remaining) == [], "the stripped memory is still on the survivor"


async def _two_repos_of_one_name(session, name: str) -> tuple[UUID, UUID]:
    """Two distinct repositories sharing a name — a shipped row class.

    ``repositories.name`` carries no unique constraint, so two rows of the
    same name derive the same repo entity and the same relation triples;
    ``assert_from_repo``'s ``ON CONFLICT`` then appends, leaving rows both
    repos assert and no memory does. Stripping one is what puts the repo
    predicates of ``strip_repo_assertions`` on the critical path.
    """
    return (
        await _seed_repo(session, name=name, imports=[]),
        await _seed_repo(session, name=name, imports=[]),
    )


@pytest.mark.asyncio
async def test_the_repo_strip_spares_a_relation_a_second_repo_asserts(session):
    """The *relation* half of ``strip_repo_assertions``'s live-repo guard.

    Nothing but a string count guarded this statement: swap ``repo_ids`` for
    ``memory_ids`` in it — the copy-paste slip the shape invites — and every
    test stayed green while a live repo's assertion was destroyed. The
    ``lonely`` relation is the other direction, so the delete cannot pass by
    never running.
    """
    first, second = await _two_repos_of_one_name(session, "same-name-repo")
    source = await _entity(session, "both-repos-source", [], [str(first), str(second)])
    target = await _entity(session, "both-repos-target", [], [str(first), str(second)])
    shared = await _relation(session, source, target, [], [str(first), str(second)])
    lonely_source = await _entity(session, "one-repo-source", [], [str(first)])
    lonely_target = await _entity(session, "one-repo-target", [], [str(first)])
    lonely = await _relation(session, lonely_source, lonely_target, [], [str(first)])
    await session.flush()

    await PostgresGraphRepository(session).strip_repo_assertions(first)

    assert await _exists(session, "entity_relations", shared), (
        "the repo strip deleted a relation the second repo still asserts"
    )
    assert not await _exists(session, "entity_relations", lonely)
    remaining = (await session.execute(
        text("SELECT repo_ids FROM entity_relations WHERE id = CAST(:id AS uuid)"),
        {"id": str(shared)},
    )).scalar()
    assert [str(r) for r in remaining] == [str(second)]


@pytest.mark.asyncio
async def test_the_repo_strip_spares_an_entity_a_second_repo_asserts(session):
    """The *entity* half of the same guard, with no relation to mask it.

    ``test_an_entity_two_repos_assert_survives_one_strip`` looks like this
    coverage but is not: there the shared entity is spared by the
    surviving-relation FK guard, so the repo predicate never decides the
    outcome. These rows carry no relation at all, which is the only shape
    that puts the predicate on the critical path.
    """
    first, second = await _two_repos_of_one_name(session, "same-name-repo")
    shared = await _entity(session, "both-repos-node", [], [str(first), str(second)])
    lonely = await _entity(session, "one-repo-node", [], [str(first)])
    await session.flush()

    await PostgresGraphRepository(session).strip_repo_assertions(first)

    assert await _exists(session, "entities", shared), (
        "the repo strip deleted an entity the second repo still asserts"
    )
    assert not await _exists(session, "entities", lonely)
    remaining = (await session.execute(
        text("SELECT repo_ids FROM entities WHERE id = CAST(:id AS uuid)"),
        {"id": str(shared)},
    )).scalar()
    assert [str(r) for r in remaining] == [str(second)]


@pytest.mark.asyncio
async def test_the_unscoped_sweep_spares_a_repo_asserted_relation(session):
    repo_id = await _seed_repo(session, name="sweep-repo", imports=[])
    source = await _entity(session, "sweep-source", [], [str(repo_id)])
    target = await _entity(session, "sweep-target", [], [str(repo_id)])
    edge = await _relation(session, source, target, [], [str(repo_id)])
    await session.flush()

    await PostgresGraphRepository(session).prune_orphan_entities()

    assert await _exists(session, "entity_relations", edge)
    assert await _exists(session, "entities", source)
    assert await _exists(session, "entities", target)


@pytest.mark.asyncio
async def test_a_row_only_a_dead_repo_asserts_is_reaped(session):
    dead_repo = uuid4()
    ghost = await _entity(session, "dead-repo-node", [], [str(dead_repo)])
    await session.flush()

    result = await PostgresGraphRepository(session).prune_orphan_entities()

    assert not await _exists(session, "entities", ghost), (
        "a dangling repo_id must self-heal exactly as a dangling memory_id does"
    )
    assert result["entities_pruned"] >= 1


@pytest.mark.asyncio
async def test_memory_only_rows_are_reaped_unchanged_beside_repo_assertions(session):
    """The byte-identical clause: a populated array changes nothing elsewhere.

    A memory-only ghost, a live-memory row and a live-repo row all sit in the
    same table; the sweep must reap exactly the ghost. Before this task every
    ``repo_ids`` was empty, so the predicate had never once been evaluated
    against a non-empty array — this is the first run where it is not vacuous.
    """
    repo_id = await _seed_repo(session, name="coexist-repo", imports=[])
    memory_id = uuid4()
    session.add(Memory(id=memory_id, content="x", source="test"))
    await session.flush()

    ghost = await _entity(session, "ghost-node", [str(uuid4())], [])
    live_memory = await _entity(session, "memory-node", [str(memory_id)], [])
    live_repo = await _entity(session, "repo-node", [], [str(repo_id)])
    await session.flush()

    await PostgresGraphRepository(session).prune_orphan_entities()

    assert not await _exists(session, "entities", ghost)
    assert await _exists(session, "entities", live_memory)
    assert await _exists(session, "entities", live_repo)


# ── structural guards ────────────────────────────────────────────────────

# Every module that dispatches to a model, plus the HTTP clients a hand-rolled
# call would need. Matched as import routes, attribute reaches and literal
# dotted paths by the shared AST scanner — never as line text, so a comment
# naming one of these does not fire and the guard can never be "loosened" by
# rewording prose.
_LLM_SURFACES = frozenset({
    "app.services.llm",
    "app.services.extraction",
    "app.services.classification_llm",
    "app.services.classification_ml",
    "app.services.reranker",
    "app.services.verification_judge",
})

# The clients a hand-rolled model call would need, closing the route that
# bypasses the orchestrator entirely. Matched on **every** route the shared
# scanner offers, literals included: a literal is how the executable dynamic
# reach `importlib.import_module("httpx")` spells itself, and the import
# route is structurally blind to it. The one collision — `_TYPE_OVERRIDES`
# types the entity names "openai" and "anthropic" as services, corpus
# vocabulary rather than a reach — is exempted by node identity in
# `_curated_type_table_constants`, not by narrowing the vocabulary or
# dropping the route.
_HTTP_CLIENTS = frozenset({"httpx", "aiohttp", "requests", "openai", "anthropic"})

_LLM_DISPATCH_ATTRS = frozenset({
    "chat_completion",
    "chat_completion_stream",
    "embed",
    "embed_batch",
    "embed_batch_chunked",
    "get_llm_orchestrator",
    "LLMOrchestrator",
})

# The code graph. `repositories` is deliberately absent: the amended orphan
# sweeps read it by design (doc 06 §6.1), and it is the repo registry, not the
# code graph the never-join rule is about.
_CODE_GRAPH_TABLES = ("code_graph_nodes", "code_edges", "code_symbols",
                      "code_files", "code_chunks")
_MEMORY_GRAPH_TABLES = ("entities", "entity_relations")


def _module_path(dotted: str, root: Path) -> Path | None:
    module = root / Path(dotted.replace(".", "/") + ".py")
    if module.exists():
        return module
    package = root / Path(dotted.replace(".", "/")) / "__init__.py"
    return package if package.exists() else None


def _package_of(path: Path, root: Path) -> str:
    """The dotted package a module at ``path`` lives in.

    A module's package is its parent directory; a package's ``__init__.py``
    lives in the package it *is*, which is the same computation.
    """
    return ".".join(path.relative_to(root).parts[:-1])


def _resolve_relative(package: str, level: int, module: str | None) -> str | None:
    """The absolute dotted path a relative import names.

    ``from .pipeline import X`` inside ``app/services/code_deriver.py`` is a
    reach into ``app.services.pipeline`` and must enter the closure exactly as
    ``from app.services.pipeline import X`` does. Resolving it needs the
    importing file's own package, which is why this lives here rather than in
    the shared scanner: the scanner sees one file at a time and matches a
    relative import on its trailing segments, a discipline that answers "does
    *this* file reach a forbidden module" but cannot answer "which file does
    it pull into the set I am about to scan".
    """
    parts = package.split(".") if package else []
    if level - 1 > len(parts):
        return None
    base = parts[: len(parts) - (level - 1)]
    if module:
        base = base + module.split(".")
    return ".".join(base) or None


def _loader_call_package(node: ast.Call) -> str | None:
    """The literal ``package=`` a loader call passes, keyword or positional."""
    for keyword in node.keywords:
        if (
            keyword.arg == "package"
            and isinstance(keyword.value, ast.Constant)
            and isinstance(keyword.value.value, str)
        ):
            return keyword.value.value
    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
        candidate = node.args[1].value
        if isinstance(candidate, str):
            return candidate
    return None


def _loader_call_targets(node: ast.AST, package: str) -> list[str]:
    """The dotted modules a literal ``import_module``/``__import__`` call names.

    The closure's static-import walk is structurally blind to
    ``importlib.import_module("app.services.pipeline")``: it executes at
    import and hands back the live module, yet no ``Import`` node names it,
    so the reached module never enters the set the guards scan and every
    guard built on the closure stays green. That is the same class of hole
    the relative-import resolution closed, one route over — and it is the
    route the shared scanner's client rule already resolves for a literal
    ``import_module("httpx")``.

    An absolute literal name is the module. A relative one resolves through
    the same ``_resolve_relative`` the static walk uses, against the call's
    own literal ``package`` when it has one and otherwise against the
    importing file's package — which is what ``__package__`` evaluates to,
    the only executable spelling of a relative loader call whose package is
    not a literal. A non-literal name resolves to nothing here: reconstructing
    a computed string statically is impossible, and this is a tripwire, so
    the residual over-approximation of the package fallback (one extra module
    scanned) is the correct direction to err in.

    ``fromlist`` members are appended to the base exactly as the static
    ``ImportFrom`` branch appends its aliases, because they name the same
    thing: ``__import__("app.services", fromlist=["pipeline"])`` hands back
    the package while the caller reaches through to
    ``app.services.pipeline``, so following only the base would scan an
    ``__init__`` and leave the submodule unreached.

    **The bound this resolver does not cross, stated rather than
    discovered.** It resolves a *call shape*, never a binding. So
    ``import_module`` reached through an alias
    (``from importlib import import_module as im``) or through a variable
    holding the callable is outside it, as is any name assembled at runtime
    — an f-string, a join, a constant lookup — and so is the
    ``find_spec``/``module_from_spec``/``exec_module`` triple, which never
    names a module in a call argument at all. Each is a real escape, and
    each is left open deliberately: resolving bindings turns a tripwire into
    a dataflow analysis, and a guard that grows until it is wrong about
    something is worse than one whose edge is written down. What is *not*
    in that bound, and was closed rather than argued: the keyword spelling
    of the first argument, and ``fromlist``. Both read as oversights in a
    resolver that already accepts a keyword ``package=``.
    """
    if not isinstance(node, ast.Call):
        return []
    func = node.func
    if isinstance(func, ast.Name):
        called = func.id
    elif isinstance(func, ast.Attribute):
        called = func.attr
    else:
        return []
    if called not in {"import_module", "__import__"}:
        return []
    named = node.args[0] if node.args else next(
        (kw.value for kw in node.keywords if kw.arg == "name"), None
    )
    if not isinstance(named, ast.Constant):
        return []
    target = named.value
    if not isinstance(target, str) or not target:
        return []
    if target.startswith("."):
        level = len(target) - len(target.lstrip("."))
        base = _loader_call_package(node) or package
        resolved = _resolve_relative(base, level, target[level:] or None)
        if not resolved:
            return []
        target = resolved
    reached = [target]
    for keyword in node.keywords:
        if keyword.arg != "fromlist" or not isinstance(keyword.value, (ast.List, ast.Tuple)):
            continue
        reached += [
            f"{target}.{element.value}"
            for element in keyword.value.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        ]
    return reached


def _import_closure(entry: Path, root: Path) -> list[Path]:
    """Every module under ``app`` reachable from ``entry``, transitively.

    Transitive, not one hop: "no LLM call anywhere in the path" is a claim
    about everything the deriver can execute, and a one-hop scan would pass
    while a helper it imports dispatched freely. Relative and absolute
    imports both count — a closure that followed only ``level == 0`` would
    let ``from .pipeline import ProcessingPipeline`` pull the whole
    extraction pipeline into the deriver while every guard built on the
    closure stayed green. Literal loader calls count for the same reason
    (``_loader_call_targets``): an intermediate module carries no vocabulary
    entry of its own precisely because the closure is what scans it, so a
    dynamic hop into one is invisible to every layer unless the closure
    follows it. The closure is small by construction — if it ever
    grows to include a module that legitimately talks to a model, that is a
    design change to argue for, not an allowlist entry to add.
    """
    seen: set[Path] = set()
    stack = [entry]
    while stack:
        path = stack.pop()
        if path in seen:
            continue
        seen.add(path)
        tree = ast.parse(path.read_text(), filename=str(path))
        package = _package_of(path, root)
        for node in ast.walk(tree):
            dotted: list[str] = []
            if isinstance(node, ast.ImportFrom):
                base = (
                    node.module if node.level == 0
                    else _resolve_relative(package, node.level, node.module)
                )
                if base:
                    dotted.append(base)
                    dotted += [f"{base}.{alias.name}" for alias in node.names]
            elif isinstance(node, ast.Import):
                dotted += [alias.name for alias in node.names]
            else:
                dotted += _loader_call_targets(node, package)
            for name in dotted:
                if not name.startswith("app"):
                    continue
                resolved = _module_path(name, root)
                if resolved is not None and resolved not in seen:
                    stack.append(resolved)
    return sorted(seen)


def _deriver_path_modules() -> list[Path]:
    return _import_closure(BACKEND / "app" / "services" / "code_deriver.py", BACKEND)


def _curated_type_table_constants(rel: str, tree: ast.Module) -> set[int]:
    """The string constants of ``extraction_clean``'s curated type table.

    The client vocabulary is bare, ordinary words, and this one data
    structure types the entity names "openai" and "anthropic" as services —
    corpus vocabulary, not a reach. The narrow exemption is those specific
    constant nodes, identified by walking the assignment's own value; the
    literal route stays live for every other constant in that file and every
    other file in the closure. Dropping the route wholesale instead — which
    is what a first pass did — reopens
    ``importlib.import_module("httpx")``, an executable dynamic reach the
    import route structurally cannot see.
    """
    if rel != "app/services/extraction_clean.py":
        return set()
    exempt: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        named = any(
            isinstance(target, ast.Name) and target.id == "_TYPE_OVERRIDES"
            for target in targets
        )
        if not named or node.value is None:
            continue
        exempt |= {
            id(child) for child in ast.walk(node.value)
            if isinstance(child, ast.Constant)
        }
    return exempt


def _model_dispatch_offenders(paths: list[Path], root: Path) -> list[str]:
    offenders = find_forbidden_reach(
        paths, root,
        ReachabilityRules(forbidden_modules=_LLM_SURFACES,
                          forbidden_attrs=_LLM_DISPATCH_ATTRS),
    )
    offenders += find_forbidden_reach(
        paths, root, ReachabilityRules(forbidden_modules=_HTTP_CLIENTS),
        exempt_node_ids=_curated_type_table_constants,
    )
    return offenders


def test_the_deriver_path_reaches_no_model_dispatch():
    paths = _deriver_path_modules()
    assert len(paths) >= 5, (
        f"the import closure collapsed to {len(paths)} modules — the scan "
        "below would pass vacuously"
    )
    assert BACKEND / "app" / "repositories" / "graph.py" in paths, (
        "the graph repository is the deriver's write path and must be scanned"
    )

    offenders = _model_dispatch_offenders(paths, BACKEND)
    assert not offenders, (
        "the deriver path reached a model-dispatch surface — doc 10 §6: the "
        "deriver is deterministic and LLM-free:\n" + "\n".join(offenders)
    )


@pytest.mark.parametrize(
    "planted_source",
    [
        "from app.services.llm import LLMOrchestrator\n",
        "async def enrich(client, msgs):\n"
        "    return await client.chat_completion('extraction', msgs)\n",
        "import httpx\n",
        # The dynamic route. Executes at import, hands back the live client,
        # and names the client only as a literal — so an import-route-only
        # client rule walks straight past it.
        "import importlib\n"
        '_client = importlib.import_module("httpx")\n',
        '__import__("openai")\n',
    ],
)
def test_the_model_dispatch_scan_flags_a_planted_reach(tmp_path, planted_source):
    planted = tmp_path / "app" / "services" / "sneaky.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(planted_source)
    assert _model_dispatch_offenders([planted], tmp_path)


def test_the_curated_type_table_is_exempt_by_identity_not_by_wording(tmp_path):
    """Both directions of the one collision, in one file.

    A guard's negative control has to prove it still fires. Two dicts with
    the same words sit side by side here: the curated table the deriver
    genuinely reads, and an ordinary one. Exactly the ordinary one is
    flagged — so the exemption is scoped to a structurally identified node
    rather than to the file, the words, or the whole literal route.
    """
    planted = tmp_path / "app" / "services" / "extraction_clean.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        '_TYPE_OVERRIDES: dict[str, str] = {"openai": "service", '
        '"anthropic": "service"}\n'
        'ELSEWHERE = {"httpx": "tool"}\n'
    )

    offenders = _model_dispatch_offenders([planted], tmp_path)
    assert len(offenders) == 1, offenders
    assert "httpx" in offenders[0]


@pytest.mark.parametrize(
    "reach",
    ["from app.services.pipeline import ProcessingPipeline",
     "from app.services import pipeline"],
)
@pytest.mark.parametrize("spelling", ["absolute", "relative"])
def test_the_closure_follows_a_relative_reach_as_it_follows_an_absolute_one(
    tmp_path, reach, spelling,
):
    """The hole the closure had, and its own control.

    The absolute spelling of a reach was always caught; the relative one was
    not, because the closure skipped every ``level > 0`` import and the
    reached module therefore never entered the scanned set. Both spellings
    name the same module and both must pull it in — otherwise every guard
    built on this closure is one ``from .pipeline import X`` away from blind.
    """
    services = tmp_path / "app" / "services"
    services.mkdir(parents=True)
    (tmp_path / "app" / "__init__.py").write_text("")
    (services / "__init__.py").write_text("")
    (services / "pipeline.py").write_text("import httpx\n")
    entry = services / "code_deriver.py"
    if spelling == "relative":
        reach = reach.replace("from app.services.", "from .").replace(
            "from app.services import", "from . import"
        )
    entry.write_text(reach + "\n")

    closure = _import_closure(entry, tmp_path)
    assert services / "pipeline.py" in closure, (
        f"the {spelling} spelling of the same reach never entered the closure"
    )
    assert _model_dispatch_offenders(closure, tmp_path)


def test_the_closure_resolves_a_parent_relative_reach(tmp_path):
    # `from ..repositories import graph` two packages up: the resolution has
    # to drop one segment per extra level, not treat every relative import
    # as a sibling.
    (tmp_path / "app" / "services").mkdir(parents=True)
    (tmp_path / "app" / "repositories").mkdir(parents=True)
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "services" / "__init__.py").write_text("")
    (tmp_path / "app" / "repositories" / "__init__.py").write_text("")
    (tmp_path / "app" / "repositories" / "graph.py").write_text("import aiohttp\n")
    entry = tmp_path / "app" / "services" / "code_deriver.py"
    entry.write_text("from ..repositories.graph import PostgresGraphRepository\n")

    closure = _import_closure(entry, tmp_path)
    assert tmp_path / "app" / "repositories" / "graph.py" in closure
    assert _model_dispatch_offenders(closure, tmp_path)


def _scaffold_intermediate_reach(tmp_path: Path, reach: str) -> Path:
    """A deriver-shaped entry whose only content is ``reach``.

    The reached module is an ordinary intermediate — it carries no entry in
    either forbidden vocabulary, exactly as ``app.services.pipeline`` does
    not — so the reach is caught only if the closure pulls it in to be
    scanned.
    """
    services = tmp_path / "app" / "services"
    services.mkdir(parents=True)
    (tmp_path / "app" / "__init__.py").write_text("")
    (services / "__init__.py").write_text("")
    (services / "pipeline.py").write_text("import httpx\n")
    entry = services / "code_deriver.py"
    entry.write_text(reach)
    return entry


@pytest.mark.parametrize(
    "reach",
    [
        # The static spelling and the dynamic ones are the same reach: each
        # executes at import and hands the deriver the live pipeline. The
        # guard has to agree across all of them or it only forbids a spelling.
        "from app.services.pipeline import ProcessingPipeline\n",
        'import importlib\n_p = importlib.import_module("app.services.pipeline")\n',
        "from importlib import import_module\n"
        '_p = import_module("app.services.pipeline")\n',
        '_p = __import__("app.services.pipeline")\n',
        'import importlib\n_p = importlib.import_module(".pipeline", "app.services")\n',
        "import importlib\n"
        '_p = importlib.import_module(".pipeline", package="app.services")\n',
        'import importlib\n_p = importlib.import_module(".pipeline", __package__)\n',
    ],
)
def test_the_closure_follows_a_dynamic_reach_as_it_follows_a_static_one(tmp_path, reach):
    """The third guard spelling, and the static one it has to agree with.

    An intermediate module has no vocabulary entry of its own — the design
    relies on the closure to scan it — so a dynamic hop into one was
    invisible to both layers: the module route sees no import statement, and
    the literal route fires only on the client and surface vocabularies,
    neither of which names an intermediate. Planted in the real deriver,
    ``importlib.import_module("app.services.pipeline")`` handed it the whole
    extraction/classification surface with every test green.
    """
    entry = _scaffold_intermediate_reach(tmp_path, reach)

    closure = _import_closure(entry, tmp_path)
    assert tmp_path / "app" / "services" / "pipeline.py" in closure, (
        "this spelling of the reach never entered the closure"
    )
    assert _model_dispatch_offenders(closure, tmp_path)


def test_the_closure_follows_a_loader_call_only_when_the_name_is_literal(tmp_path):
    """The extension's scope: literals, not every call node.

    Without this, ``_loader_call_targets`` could pull in modules it never
    resolved and the positive controls above would still pass. A computed
    name is the shared scanner's documented bound (`_reachability_scan`'s
    module docstring) — no static rework reaches it — so the honest
    statement is that this route follows what is spelled, and this test is
    what pins the extension to that claim rather than to a wider one.
    """
    entry = _scaffold_intermediate_reach(
        tmp_path,
        "import importlib\n"
        '_name = "app.services" + ".pipeline"\n'
        "_p = importlib.import_module(_name)\n"
        "_q = importlib.import_module()\n",
    )

    closure = _import_closure(entry, tmp_path)
    assert closure == [entry]


def _cross_graph_statements(paths: list[Path], root: Path) -> list[str]:
    """String constants that name a code-graph table and a memory-graph table.

    The never-join rule is structural, not stylistic: no *statement* may read
    the code graph and the memory graph together. A statement is a SQL string
    here, so the check runs over parsed constants — a docstring naming both,
    like this one, is exempted by structural role rather than by its wording.
    """
    offenders: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(), filename=str(path))
        docstrings = {
            id(node.body[0].value)
            for node in ast.walk(tree)
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef))
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if id(node) in docstrings:
                continue
            words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", node.value))
            if words & set(_CODE_GRAPH_TABLES) and words & set(_MEMORY_GRAPH_TABLES):
                offenders.append(
                    f"{path.relative_to(root)}:{node.lineno}: {node.value.strip()[:80]}"
                )
    return offenders


def test_no_statement_reads_both_graphs():
    offenders = _cross_graph_statements(_deriver_path_modules(), BACKEND)
    assert not offenders, (
        "a statement named the code graph and the memory graph together — the "
        "bridge is application-level and one-direction (doc 10 §2):\n"
        + "\n".join(offenders)
    )


def test_the_cross_graph_scan_flags_a_planted_join(tmp_path):
    planted = tmp_path / "app" / "services" / "sneaky.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "SQL = 'SELECT e.name FROM entities e JOIN code_graph_nodes n "
        "ON n.label = e.name'\n"
    )
    assert _cross_graph_statements([planted], tmp_path)


# ── T2.96: production trigger (job) + withdrawal on repo delete ──────────
#
# Everything above proves the primitives are correct when called directly —
# which is exactly what T2.27 already proved. What was missing is a caller.
# The tests below drive the real entry points: `JobRegistry.trigger` for the
# forward direction, the `DELETE /repos/{id}` route for the withdrawal — and
# read the result off the database, never off the primitive's return value.


def _direct_job_registrations(source: str) -> list[ast.Call]:
    """Every `job_registry.register(Job(...))` call in `app/main.py`.

    Deliberately excludes the dream-job family, which never calls
    `job_registry.register` directly — it rides through
    `register_dream_jobs(job_registry, ...)` instead — so this collects
    exactly the roster CLAUDE.md calls "the fourteen live ones", the direct
    registrations `code_deriver` joined.
    """
    tree = ast.parse(source)
    calls = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "register"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "job_registry"
            and node.args
            and isinstance(node.args[0], ast.Call)
            and isinstance(node.args[0].func, ast.Name)
            and node.args[0].func.id == "Job"
        ):
            calls.append(node.args[0])
    return calls


def _job_kwarg(call: ast.Call, name: str) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _binding_token(node: ast.expr) -> str:
    """The source-level identity of a `Job(...)` keyword value: the
    referenced name for a `Name` node (e.g. `CODE_DERIVER_JOB_KEY`), the
    literal for a string `Constant` (e.g. `"repo_sync"`). Checking the
    *binding* rather than a resolved runtime value is what makes deleting
    either the import or the whole registration block fail this test — the
    RRF binding-scans in `test_chat_retrieval_parity.py` are the same shape,
    checked against `rank_fusion.py`.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return node.id
    raise AssertionError(f"unexpected Job() keyword expression: {ast.dump(node)}")


def test_main_registers_the_full_direct_job_roster():
    """A source-substring check over `inspect.getsource(app.main)` — the
    test this replaces — passes when the *entire*
    `job_registry.register(Job(key=CODE_DERIVER_JOB_KEY, ...))` block is
    deleted and only its import lines survive: measured directly by the
    T2.96 adversarial review, which deleted exactly that block and watched
    116/116 tests pass, the substring test included (import lines alone
    satisfy all three substrings). It proved nothing about production
    reachability, which is the one thing this task exists to establish.

    An AST scan over the *binding* each `Job(key=...)` resolves to, not the
    source text, closes that hole: deleting the block deletes its `Job(...)`
    call node, so its key vanishes from what this scan collects and the
    roster comparison goes red — imports lingering or not.

    Scanning the *full* direct roster, not only `code_deriver`'s row, closes
    the identical, pattern-inherited exposure the review flagged in
    `test_code_reconcile.py`'s twin and, by inspection, `ppr_snapshot`'s —
    both keys are asserted here through the same mechanism, at no extra
    cost, so their equivalent tests may keep their existing (weaker) shape
    without leaving the gap unclosed.
    """
    import app.main as main

    source = Path(main.__file__).read_text()
    registrations = _direct_job_registrations(source)
    keys = {_binding_token(_job_kwarg(call, "key")) for call in registrations}

    expected = {
        "repo_sync", "BUFFER_FLUSH_JOB_KEY", "code_enrichment",
        "CODE_RECONCILE_JOB_KEY", "CODE_DERIVER_JOB_KEY",
        "token_blocklist_cleanup", "pipeline_failure_cleanup",
        "graph_orphan_cleanup", "tag_orphan_cleanup",
        "expired_memory_cleanup", "PPR_SNAPSHOT_JOB_KEY",
        "RELATION_EMBEDDING_JOB_KEY", "REPO_ENTITY_ANCHORING_JOB_KEY",
        "REPO_ENTITY_MERGE_JOB_KEY", "CITATION_REVERIFY_JOB_KEY",
    }
    assert keys == expected, (
        f"direct job registrations in app/main.py drifted from the roster "
        f"CLAUDE.md documents: missing={expected - keys}, "
        f"unexpected={keys - expected}"
    )

    deriver_calls = [
        call for call in registrations
        if _binding_token(_job_kwarg(call, "key")) == "CODE_DERIVER_JOB_KEY"
    ]
    assert len(deriver_calls) == 1
    deriver = deriver_calls[0]

    runner_expr = _job_kwarg(deriver, "runner")
    assert isinstance(runner_expr, ast.Call) and isinstance(runner_expr.func, ast.Name)
    assert runner_expr.func.id == "make_code_deriver_runner", (
        "code_deriver's Job() is not wired to make_code_deriver_runner"
    )

    interval_expr = _job_kwarg(deriver, "min_interval_seconds")
    assert _binding_token(interval_expr) == "CODE_DERIVER_MIN_INTERVAL_SECONDS"


def test_code_deriver_is_not_a_dream_job_family_member():
    """Contract 6 fixes the dream-job family at six. This job must register
    directly in `app/main.py`, the same way `ppr_snapshot` does, and never
    ride in through `dream_jobs.register_dream_jobs`."""
    import app.services.dream_jobs as dream_jobs

    source = Path(dream_jobs.__file__).read_text()
    assert "code_deriver" not in source
    assert "CODE_DERIVER_JOB_KEY" not in source


def test_code_deriver_cron_and_floor_are_valid():
    from app.services.code_deriver_job import (
        CODE_DERIVER_CRON,
        CODE_DERIVER_MIN_INTERVAL_SECONDS,
    )
    from app.services.job_registry import is_valid_cron

    assert is_valid_cron(CODE_DERIVER_CRON)
    assert CODE_DERIVER_MIN_INTERVAL_SECONDS > 0


@pytest.mark.asyncio
async def test_code_deriver_shares_lock_with_manual_trigger():
    """Registered through the real `Job`/`JobRegistry` contract, the deriver
    job gets the same per-job lock the scheduled loop and manual trigger
    share — a trigger while it's held must busy-error, never queue."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import settings
    from app.services.code_deriver_job import (
        CODE_DERIVER_CRON,
        CODE_DERIVER_JOB_KEY,
        CODE_DERIVER_MAX_RUN_SECONDS,
        CODE_DERIVER_MIN_INTERVAL_SECONDS,
    )
    from app.services.job_registry import Job, JobBusyError, JobRegistry

    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    registry = JobRegistry(factory)

    async def _noop():
        return None

    registry.register(Job(
        key=CODE_DERIVER_JOB_KEY,
        display_name="Code Graph Deriver",
        description="d",
        default_cron=CODE_DERIVER_CRON,
        min_interval_seconds=CODE_DERIVER_MIN_INTERVAL_SECONDS,
        runner=_noop,
        max_run_seconds=CODE_DERIVER_MAX_RUN_SECONDS,
    ))
    job = registry.get(CODE_DERIVER_JOB_KEY)
    await job.lock.acquire()
    try:
        with pytest.raises(JobBusyError):
            await registry.trigger(CODE_DERIVER_JOB_KEY)
    finally:
        job.lock.release()
        await registry.stop_all()
        await engine.dispose()


@pytest.mark.asyncio
async def test_runner_derives_repo_ids_end_to_end(setup_database):
    """The real production trigger, not a direct `assert_repo_graph` call.

    Registers the job through a real `JobRegistry`, fires it with
    `trigger()` — exactly what a scheduled tick or a manual trigger does —
    and reads `entities.repo_ids` straight off the database.

    Also carries the idempotency clause: three triggers in a row, and each
    one is checked for the same property T2.27 asserted for the primitive —
    the repo id appears *exactly once* per array, and contents (not just
    counts) are identical run over run. Byte-identical row ids are not
    asserted, deliberately: strip-before-rewrite gives every row a fresh id
    on each run, which is expected, not a bug (see `_repo_snapshot`'s
    docstring above).

    Uses its own `async_sessionmaker` bound to `tests.conftest.test_engine`
    rather than the `session` fixture, because `make_code_deriver_runner`
    opens its own sessions via a session factory — those need to see
    committed rows from a genuinely separate connection, which the
    `session` fixture's rollback-only transaction never produces.
    """
    from sqlalchemy import delete as sa_delete
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.models.code import Repository
    from app.services.code_deriver_job import (
        CODE_DERIVER_CRON,
        CODE_DERIVER_JOB_KEY,
        CODE_DERIVER_MAX_RUN_SECONDS,
        CODE_DERIVER_MIN_INTERVAL_SECONDS,
    )
    from app.services.job_registry import Job, JobRegistry
    from app.services.job_runners import make_code_deriver_runner
    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async with factory() as session:
        repo_id = await _seed_repo(session, name="trigger-repo")
        # The runner selects repos by `last_indexed_commit IS NOT NULL` —
        # the same "already indexed" gate `code_reconcile` uses — so a repo
        # that was never indexed is correctly left alone.
        await session.execute(
            text("UPDATE repositories SET last_indexed_commit = 'sha-1' "
                 "WHERE id = CAST(:id AS uuid)"),
            {"id": str(repo_id)},
        )
        await session.commit()

    registry = JobRegistry(factory)
    registry.register(Job(
        key=CODE_DERIVER_JOB_KEY,
        display_name="Code Graph Deriver",
        description="d",
        default_cron=CODE_DERIVER_CRON,
        min_interval_seconds=CODE_DERIVER_MIN_INTERVAL_SECONDS,
        runner=make_code_deriver_runner(factory),
        max_run_seconds=CODE_DERIVER_MAX_RUN_SECONDS,
    ))

    try:
        first_snapshot = None
        for _ in range(3):
            await registry.trigger(CODE_DERIVER_JOB_KEY)
            async with factory() as session:
                snapshot = await _repo_snapshot(session, repo_id)
                # A per-row occurrence count, not `max(cardinality(repo_ids))`:
                # cardinality proves "this repo is the array's sole occupant",
                # which only coincides with "the repo id appears exactly once"
                # because no other committed test shares an entity with this
                # repo's rows. `sqlalchemy`/`fastapi` are global
                # (name, entity_type) keys a neighbouring test could
                # legitimately co-assert, which would push cardinality past 1
                # while the repo id still appears exactly once per row.
                not_exactly_once = {
                    table: (await session.execute(
                        text(
                            f"SELECT count(*) FROM {table} "
                            "WHERE (SELECT count(*) FROM unnest(repo_ids) u "
                            "WHERE u = CAST(:rid AS uuid)) != 1 "
                            "AND CAST(:rid AS uuid) = ANY(repo_ids)"
                        ),
                        {"rid": str(repo_id)},
                    )).scalar()
                    for table in ("entities", "entity_relations")
                }
            assert snapshot["entities"], "the trigger must actually write something"
            assert snapshot["relations"], "the trigger must actually write something"
            assert not_exactly_once["entities"] == 0, (
                "repo id duplicated within some entities.repo_ids row"
            )
            assert not_exactly_once["entity_relations"] == 0, (
                "repo id duplicated within some entity_relations.repo_ids row"
            )
            if first_snapshot is None:
                first_snapshot = snapshot
            else:
                assert snapshot == first_snapshot, (
                    "re-triggering changed the derivation contents"
                )
    finally:
        await registry.stop_all()
        async with factory() as session:
            # entities/entity_relations carry no FK to `repositories` — this
            # test commits for real (a genuinely separate connection is the
            # point), so an entity like `sqlalchemy` this run minted is a row
            # every other test in this file shares (entities are keyed by
            # `(name, entity_type)`, not scoped to a repo). Deleting only the
            # Repository row would leave it dangling and contaminate a later
            # test's `session`-fixture transaction, which reads the same
            # already-committed database under READ COMMITTED. Stripping
            # first is also the production withdrawal path exercised for
            # real, not a test-only shortcut.
            from app.repositories.graph import PostgresGraphRepository
            await PostgresGraphRepository(session).strip_repo_assertions(repo_id)
            await session.execute(sa_delete(Repository).where(Repository.id == repo_id))
            await session.commit()


@pytest.mark.asyncio
async def test_runner_skips_repos_never_indexed(setup_database):
    """A repo with no `last_indexed_commit` has no code graph to derive
    from — the runner must not even attempt it (it would just assert an
    empty repo entity with no dependencies, which is not "derived", it's
    noise)."""
    from sqlalchemy import delete as sa_delete
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.models.code import Repository
    from app.services.job_runners import make_code_deriver_runner
    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async with factory() as session:
        repo_id = await _seed_repo(session, name="never-indexed-repo")
        await session.commit()

    try:
        runner = make_code_deriver_runner(factory)
        await runner()

        async with factory() as session:
            snapshot = await _repo_snapshot(session, repo_id)
        assert snapshot == {"entities": [], "relations": []}
    finally:
        async with factory() as session:
            await session.execute(sa_delete(Repository).where(Repository.id == repo_id))
            await session.commit()


@pytest.mark.asyncio
async def test_delete_repo_route_strips_its_assertions(client, session, auth_headers):
    """Prove the withdrawal at the route (`DELETE /repos/{id}`), not at
    `PostgresGraphRepository.strip_repo_assertions` directly — T2.27 already
    proved the primitive; what was missing is a caller."""
    repo_id = await _seed_repo(session, name="withdraw-repo")
    await assert_repo_graph(session, repo_id)
    before = await _repo_snapshot(session, repo_id)
    assert before["entities"] and before["relations"], (
        "setup must actually assert something for the drill to mean anything"
    )

    resp = await client.delete(f"/api/v1/repos/{repo_id}", headers=auth_headers)
    assert resp.status_code == 204

    after = await _repo_snapshot(session, repo_id)
    assert after == {"entities": [], "relations": []}

    # Orphaned inline, not left for graph_orphan_cleanup: an entity only
    # this repo asserted, with no live memory and no surviving relation,
    # must be gone from the table entirely — not merely detached from an
    # array that still points at a deleted repository.
    still_present = (await session.execute(
        text("SELECT count(*) FROM entities WHERE name = 'sqlalchemy' AND entity_type = 'tool'")
    )).scalar()
    assert still_present == 0


@pytest.mark.asyncio
async def test_delete_repo_route_spares_an_entity_a_second_repo_still_asserts(
    client, session, auth_headers,
):
    first = await _seed_repo(session, name="shared-repo-1", imports=["redis"])
    second = await _seed_repo(session, name="shared-repo-2", imports=["redis"])
    await assert_repo_graph(session, first)
    await assert_repo_graph(session, second)

    row = (await session.execute(
        text("SELECT repo_ids FROM entities WHERE name = 'redis'"),
    )).mappings().first()
    assert {str(first), str(second)} <= {str(r) for r in row["repo_ids"]}

    resp = await client.delete(f"/api/v1/repos/{first}", headers=auth_headers)
    assert resp.status_code == 204

    row_after = (await session.execute(
        text("SELECT repo_ids FROM entities WHERE name = 'redis'"),
    )).mappings().first()
    assert row_after is not None, "the second repo's assertion must survive"
    assert [str(r) for r in row_after["repo_ids"]] == [str(second)]

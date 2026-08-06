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
    for source in sources:
        await session.execute(
            text("""
                INSERT INTO code_edges
                    (repo_id, source_kind, source_key, target_kind, target_key, edge_type)
                VALUES (CAST(:rid AS uuid), 'file', :src, 'module', :tgt, 'imports')
                ON CONFLICT DO NOTHING
            """),
            {"rid": str(repo_id), "src": REPO_FILES[0][0], "tgt": source},
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
# bypasses the orchestrator entirely. Matched on the **import route only**:
# these are bare, ordinary words that appear in this repository as data —
# `_TYPE_OVERRIDES` types the entity name "openai" as a service — so matching
# them as literals would flag the corpus's own vocabulary, and a guard that
# fires on data is a guard that gets deleted.
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


def _module_path(dotted: str) -> Path | None:
    module = BACKEND / Path(dotted.replace(".", "/") + ".py")
    if module.exists():
        return module
    package = BACKEND / Path(dotted.replace(".", "/")) / "__init__.py"
    return package if package.exists() else None


def _deriver_path_modules() -> list[Path]:
    """Every module under ``app`` the deriver reaches, transitively.

    Transitive, not one hop: "no LLM call anywhere in the path" is a claim
    about everything the deriver can execute, and a one-hop scan would pass
    while a helper it imports dispatched freely. The closure is small by
    construction — if it ever grows to include a module that legitimately
    talks to a model, that is a design change to argue for, not an allowlist
    entry to add.
    """
    seen: set[Path] = set()
    stack = [BACKEND / "app" / "services" / "code_deriver.py"]
    while stack:
        path = stack.pop()
        if path in seen:
            continue
        seen.add(path)
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            dotted: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                dotted.append(node.module)
                dotted += [f"{node.module}.{alias.name}" for alias in node.names]
            elif isinstance(node, ast.Import):
                dotted += [alias.name for alias in node.names]
            for name in dotted:
                if not name.startswith("app"):
                    continue
                resolved = _module_path(name)
                if resolved is not None and resolved not in seen:
                    stack.append(resolved)
    return sorted(seen)


def _model_dispatch_offenders(paths: list[Path], root: Path) -> list[str]:
    offenders = find_forbidden_reach(
        paths, root,
        ReachabilityRules(forbidden_modules=_LLM_SURFACES,
                          forbidden_attrs=_LLM_DISPATCH_ATTRS),
    )
    client_reaches = find_forbidden_reach(
        paths, root, ReachabilityRules(forbidden_modules=_HTTP_CLIENTS),
    )
    offenders += [
        offense for offense in client_reaches
        if "import route:" in offense or "loader-call route:" in offense
    ]
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
    ],
)
def test_the_model_dispatch_scan_flags_a_planted_reach(tmp_path, planted_source):
    planted = tmp_path / "app" / "services" / "sneaky.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(planted_source)
    assert _model_dispatch_offenders([planted], tmp_path)


def test_the_model_dispatch_scan_ignores_a_client_name_used_as_data(tmp_path):
    clean = tmp_path / "app" / "services" / "fine.py"
    clean.parent.mkdir(parents=True)
    clean.write_text('OVERRIDES = {"openai": "service", "anthropic": "service"}\n')
    assert _model_dispatch_offenders([clean], tmp_path) == []


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

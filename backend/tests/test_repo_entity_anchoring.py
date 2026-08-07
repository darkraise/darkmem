"""T2.97 — the code bridge's anchoring, past an exact name match.

Doc 10 §6 promises that a ``postgres`` entity minted from a repository's
imports is the *same* deduped node as ``postgres`` from a memory. T2.27
delivered that only for an exact ``(name, entity_type)`` match: a repo-minted
entity had no row in ``entity_embeddings__<slug>``, so Phase 4's ANN probe
could not see it at all. This suite drives the full path — derive, anchor,
ingest — at the threshold the memory path uses, and states the boundary of what
the fix reaches.

Four things are asserted, and each is one a naive test passes without proving:

* **The merge is caused by the anchoring pass, not by the ANN probe alone.**
  ``test_without_anchoring...`` is the negative control: the same derivation and
  the same memory, minus the pass, leaves two nodes. Without it a suite could
  pass because the deriver and the extraction happened to agree on a name.
* **The discriminator still bites.** ``psycopg2``/``psycopg3`` are driven at the
  *same* 0.974 as ``postgres``/``postgresql`` and must NOT merge. The test
  asserts the probe actually *returned* the neighbour at that score, so a
  threshold drift cannot turn it green for the wrong reason.
* **The order production produces is the one that fails.** A repo indexed after
  a memory already minted the near-named node still leaves two rows — Phase 4
  dedups at write time and nothing re-runs it. That is asserted here rather than
  only described in a report, because a silent narrowing is exactly what T2.97
  was minted to correct.
* **Invariant 2 rides the table, and the write follows the embedder.** A
  fingerprint that rotates between the selection query and the write lands its
  vectors in the new partition, never mixed into the old one.

The pipeline-driving tests use a real committing ``session_factory`` bound to
``test_engine`` (``process_batch`` builds and commits its own sessions) and tear
their rows, repositories, child tables and registry cache entries down by hand.
"""
from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services import entity_anchoring as anchor_mod
from app.services.code_deriver import assert_repo_graph
from app.services.embedder_registry import (
    EmbedderInfo,
    child_table,
    embedder_registry,
)
from app.services.entity_anchoring import (
    embed_repo_entities,
    refresh_repo_entity_anchors,
    repo_entities_missing_vectors,
)
from app.services.pipeline import _flag_cache_reset
from tests.conftest import test_engine
from tests.test_code_deriver import _seed_repo
from tests.test_dedup_discriminator import (
    DIMS,
    POSTGRES_POSTGRESQL_COSINE,
    CalibratedEmbedder,
    _pair,
    entities_of,
    entity_rows,
    make_pipeline,
    spy_probe,
)
from tests.test_pipeline_phase1 import cleanup, seed_memories

BACKEND = Path(__file__).resolve().parent.parent
MODULE_PATH = BACKEND / "app" / "services" / "entity_anchoring.py"

IMPORTING_FILE = "backend/app/main.py"


class AnchoringEmbedder(CalibratedEmbedder):
    """A calibrated embedder that also answers the static-config question.

    ``refresh_repo_entity_anchors`` resolves its read fingerprint through the
    vector repository, which starts from ``llm_fingerprint()``. The calibrated
    stand-in has no such surface, so it gains one here rather than the service
    growing a branch for tests.
    """

    def llm_fingerprint(self) -> str:
        return self.fingerprint


class RotatingEmbedder(AnchoringEmbedder):
    """An embedder whose configured fingerprint is not the one it produces.

    The mid-run rotation, reproduced without a live model: the selection query
    runs under the fingerprint config still names, and by the time the vectors
    come back they belong to a different embedding space.
    """

    def __init__(self, configured: str, produced: str, vectors: dict):
        super().__init__(produced, vectors)
        self._configured = configured

    def llm_fingerprint(self) -> str:
        return self._configured


async def register_fingerprint(session, fingerprint: str) -> None:
    """Register a fingerprint the way boot does, so a read can resolve it."""
    model_id, _, dims = fingerprint.rpartition("|")
    await embedder_registry.register(
        session,
        EmbedderInfo(
            fingerprint=fingerprint, model_id=model_id,
            dims=int(dims), source="llm",
        ),
    )


async def register(factory, fingerprint: str) -> None:
    async with factory() as s:
        await register_fingerprint(s, fingerprint)
        await s.commit()


async def seed_repo(factory, name: str, imports: list[str]):
    async with factory() as s:
        repo_id = await _seed_repo(
            s, name=name,
            files=[(IMPORTING_FILE, "python")],
            imports=[(IMPORTING_FILE, source) for source in imports],
        )
        await s.commit()
    return repo_id


async def derive(factory, repo_id) -> dict:
    async with factory() as s:
        written = await assert_repo_graph(s, repo_id)
        await s.commit()
    return written


async def anchor(factory, embedder, missing_batch=200):
    async with factory() as s:
        outcome = await refresh_repo_entity_anchors(
            s, embedder, missing_batch=missing_batch,
        )
        await s.commit()
    return outcome


async def embedded_names(factory, fingerprint: str) -> set[str]:
    table = child_table(anchor_mod.PARENT_TABLE, fingerprint)
    async with factory() as s:
        rows = await s.execute(text(
            f"SELECT e.name FROM {table} ee JOIN entities e ON e.id = ee.entity_id"
        ))
    return {row[0] for row in rows}


async def cleanup_repo(factory, repo_id) -> None:
    async with factory() as s:
        for table in ("code_edges", "code_files"):
            await s.execute(
                text(f"DELETE FROM {table} WHERE repo_id = CAST(:rid AS uuid)"),
                {"rid": str(repo_id)},
            )
        await s.execute(
            text("DELETE FROM repositories WHERE id = CAST(:rid AS uuid)"),
            {"rid": str(repo_id)},
        )
        await s.commit()


# ── the anchoring path, end to end ───────────────────────────────────────


@pytest.mark.asyncio
async def test_a_repo_minted_postgres_anchors_a_memory_minted_postgresql(
    setup_database, monkeypatch,
):
    """Done-when 1, driven through Phase 4's own probe at its own threshold."""
    fingerprint = "anchor-merge|8"
    full, short = _pair(2, POSTGRES_POSTGRESQL_COSINE)
    names = ["postgres", "postgresql", "python", "anchor-merge-repo"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["we run postgresql"])
    repo_id = await seed_repo(factory, "anchor-merge-repo", ["postgres"])

    try:
        embedder = AnchoringEmbedder(
            fingerprint, {"postgresql": full, "postgres": short}
        )
        await register(factory, fingerprint)
        await derive(factory, repo_id)

        outcome = await anchor(factory, embedder)
        assert outcome.fingerprint == fingerprint
        assert "postgres" in await embedded_names(factory, fingerprint), (
            "the repo-minted entity has no vector, so the probe below cannot "
            "see it and this test would prove nothing"
        )

        pipe = make_pipeline(
            factory, embedder,
            [entities_of(("PostgreSQL", "database"))],
            monkeypatch,
        )
        probes = spy_probe(monkeypatch)
        results = await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "we run postgresql",
              "source": "api"}]
        )
        assert results[0]["graph"] == "ok"

        match = probes[0]["match"]
        assert match is not None, (
            "the ANN probe found nothing — the repo-minted entity is invisible "
            "to Phase 4 and the anchoring claim is still false"
        )
        assert match["name"] == "postgres"
        assert match["score"] == pytest.approx(
            POSTGRES_POSTGRESQL_COSINE, abs=1e-6
        )
        assert probes[0]["threshold"] == 0.85

        assert await entity_rows(factory, ["postgres", "postgresql"]) == [
            ("postgres", "database", 1)
        ], "the memory-minted name must canonicalize onto the repo-minted node"

        async with factory() as s:
            row = (await s.execute(text(
                "SELECT cardinality(memory_ids), cardinality(repo_ids) "
                "FROM entities WHERE name = 'postgres'"
            ))).one()
        assert tuple(row) == (1, 1), (
            "the surviving node must be asserted by both the memory and the "
            "repository — that single node is the whole point of the bridge"
        )
    finally:
        await cleanup(factory, memory_ids, [fingerprint], names)
        await cleanup_repo(factory, repo_id)


@pytest.mark.asyncio
async def test_without_anchoring_the_repo_and_memory_nodes_stay_apart(
    setup_database, monkeypatch,
):
    """The negative control for the test above: no pass, no merge.

    Identical in every respect except that the anchoring pass never runs. If
    this went green with one node, the merge above would be evidence of
    something other than the vector this task writes.
    """
    fingerprint = "anchor-control|8"
    full, short = _pair(2, POSTGRES_POSTGRESQL_COSINE)
    names = ["postgres", "postgresql", "python", "anchor-control-repo"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["we run postgresql"])
    repo_id = await seed_repo(factory, "anchor-control-repo", ["postgres"])

    try:
        embedder = AnchoringEmbedder(
            fingerprint, {"postgresql": full, "postgres": short}
        )
        await register(factory, fingerprint)
        await derive(factory, repo_id)

        pipe = make_pipeline(
            factory, embedder,
            [entities_of(("PostgreSQL", "database"))],
            monkeypatch,
        )
        probes = spy_probe(monkeypatch)
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "we run postgresql",
              "source": "api"}]
        )

        assert probes[0]["match"] is None
        assert await entity_rows(factory, ["postgres", "postgresql"]) == [
            ("postgres", "database", 0),
            ("postgresql", "database", 1),
        ]
    finally:
        await cleanup(factory, memory_ids, [fingerprint], names)
        await cleanup_repo(factory, repo_id)


@pytest.mark.asyncio
async def test_a_discriminating_token_still_refuses_the_anchor(
    setup_database, monkeypatch,
):
    """The precision half: similarity alone must not be enough to merge.

    ``psycopg2``/``psycopg3`` are driven at the *same* 0.974 the merging pair
    sits at, and the probe is asserted to have returned the neighbour at that
    score — so what keeps them apart is ``names_distinct``, not a similarity
    that failed to clear the bar.
    """
    fingerprint = "anchor-version|8"
    two, three = _pair(4, POSTGRES_POSTGRESQL_COSINE)
    names = ["psycopg2", "psycopg3", "python", "anchor-version-repo"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["we moved to psycopg3"])
    repo_id = await seed_repo(factory, "anchor-version-repo", ["psycopg2"])

    try:
        embedder = AnchoringEmbedder(
            fingerprint, {"psycopg2": two, "psycopg3": three}
        )
        await register(factory, fingerprint)
        await derive(factory, repo_id)
        await anchor(factory, embedder)
        assert "psycopg2" in await embedded_names(factory, fingerprint)

        pipe = make_pipeline(
            factory, embedder,
            [entities_of(("psycopg3", "tool"))],
            monkeypatch,
        )
        probes = spy_probe(monkeypatch)
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "we moved to psycopg3",
              "source": "api"}]
        )

        match = probes[0]["match"]
        assert match is not None and match["name"] == "psycopg2", (
            "the probe never saw the repo-minted neighbour, so this proves "
            "nothing about the discriminator"
        )
        assert match["score"] == pytest.approx(
            POSTGRES_POSTGRESQL_COSINE, abs=1e-6
        )
        assert await entity_rows(factory, ["psycopg2", "psycopg3"]) == [
            ("psycopg2", "tool", 0),
            ("psycopg3", "tool", 1),
        ], "a version token must survive the anchoring pass as a discriminator"
    finally:
        await cleanup(factory, memory_ids, [fingerprint], names)
        await cleanup_repo(factory, repo_id)


@pytest.mark.asyncio
async def test_a_repo_indexed_after_the_memory_still_leaves_two_nodes(
    setup_database, monkeypatch,
):
    """The window this shape leaves open, asserted rather than described.

    Phase 4 dedups at write time. A vector that arrives after the memory-minted
    node was written merges nothing: the deriver's own write is an exact-key
    upsert with no ANN probe, so it mints its own row beside the existing one
    and both end up embedded and distinct. Closing this needs a retroactive
    merge pass over ``entities`` — a different mechanism from an embedding
    backfill, and not this job's.
    """
    fingerprint = "anchor-late|8"
    full, short = _pair(2, POSTGRES_POSTGRESQL_COSINE)
    names = ["postgres", "postgresql", "python", "anchor-late-repo"]
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    memory_ids = await seed_memories(factory, ["we run postgresql"])
    repo_id = await seed_repo(factory, "anchor-late-repo", ["postgres"])

    try:
        embedder = AnchoringEmbedder(
            fingerprint, {"postgresql": full, "postgres": short}
        )
        await register(factory, fingerprint)

        pipe = make_pipeline(
            factory, embedder,
            [entities_of(("PostgreSQL", "database"))],
            monkeypatch,
        )
        await pipe.process_batch(
            [{"memory_id": memory_ids[0], "content": "we run postgresql",
              "source": "api"}]
        )

        await derive(factory, repo_id)
        await anchor(factory, embedder)

        assert {"postgres", "postgresql"} <= await embedded_names(
            factory, fingerprint
        ), "both nodes are embedded, and they are still two nodes"
        assert await entity_rows(factory, ["postgres", "postgresql"]) == [
            ("postgres", "database", 0),
            ("postgresql", "database", 1),
        ]
    finally:
        await cleanup(factory, memory_ids, [fingerprint], names)
        await cleanup_repo(factory, repo_id)


# ── scope and partition discipline ───────────────────────────────────────

_PROBE_FINGERPRINTS = ("anchor-scope|8", "anchor-selected|8", "anchor-produced|8")


@pytest.fixture(autouse=True)
def _forget_probe_fingerprints():
    """The registry cache is process-wide while the ``session`` fixture rolls
    the database back; without this a later test finds the fingerprint "known",
    skips the DDL, and inserts into a child table its transaction never made."""
    for fp in _PROBE_FINGERPRINTS:
        embedder_registry.forget(fp)
    yield
    for fp in _PROBE_FINGERPRINTS:
        embedder_registry.forget(fp)


async def _entity(session, name: str, *, repo_ids=(), memory_ids=()) -> str:
    return (await session.execute(
        text("""
            INSERT INTO entities (name, entity_type, memory_ids, repo_ids)
            VALUES (:name, 'tool', CAST(:mids AS uuid[]), CAST(:rids AS uuid[]))
            RETURNING CAST(id AS text)
        """),
        {"name": name, "mids": list(memory_ids), "rids": list(repo_ids)},
    )).scalar_one()


@pytest.mark.asyncio
async def test_only_repo_asserted_entities_are_candidates(session):
    """The scope boundary, which is the argument for a narrow job.

    Every other unembedded entity already has a writer: Phase 5 for what
    extraction mints, the operator re-embed for what it missed. Widening this
    arm would turn a deliberate whole-corpus operation into a background drain.
    """
    fingerprint = "anchor-scope|8"
    repo_id = await _seed_repo(session, name="scope-repo", files=[], imports=[])
    await register_fingerprint(session, fingerprint)

    await _entity(session, "repo-asserted-tool", repo_ids=[str(repo_id)])
    await _entity(session, "memory-asserted-tool", memory_ids=[str(uuid4())])
    await session.flush()

    missing = await repo_entities_missing_vectors(session, fingerprint, 100)
    assert [row["name"] for row in missing] == ["repo-asserted-tool"]


@pytest.mark.asyncio
async def test_the_write_follows_the_fingerprint_the_embedder_produced(session):
    """Invariant 2 under a rotation mid-run.

    Candidates are selected under the fingerprint that holds data; minutes
    later the embedder may have rotated. The vector then belongs to the new
    embedding space, so it goes to the new partition — writing it under the
    selection key would put two geometries in one table, where a cosine has no
    defined meaning.

    Driven through the whole tick rather than through the writer alone: the
    writer takes no fingerprint argument, so calling it directly cannot tell a
    correct implementation from one that keys on static config.
    """
    selected = "anchor-selected|8"
    produced = "anchor-produced|8"
    repo_id = await _seed_repo(session, name="rotation-repo", files=[], imports=[])
    await register_fingerprint(session, selected)

    entity_id = await _entity(session, "rotating-tool", repo_ids=[str(repo_id)])
    await session.flush()

    missing = await repo_entities_missing_vectors(session, selected, 100)
    assert [row["entity_id"] for row in missing] == [entity_id]

    embedder = RotatingEmbedder(
        selected, produced, {"rotating-tool": [1.0] + [0.0] * (DIMS - 1)}
    )
    outcome = await refresh_repo_entity_anchors(session, embedder)
    assert (outcome.written, outcome.fingerprint) == (1, produced)

    for fingerprint, expected in ((produced, 1), (selected, 0)):
        table = child_table(anchor_mod.PARENT_TABLE, fingerprint)
        count = (await session.execute(
            text(f"SELECT COUNT(*) FROM {table} WHERE entity_id = CAST(:e AS uuid)"),
            {"e": entity_id},
        )).scalar_one()
        assert count == expected, f"wrong partition for {fingerprint}"


@pytest.mark.asyncio
async def test_the_name_cache_gets_the_same_vector_as_the_partition(session):
    """Phase 3 reads the cache by name before it spends an embed, so a memory
    that later names this entity must get back the identical vector rather than
    a fresh one that could land on the other side of the threshold."""
    fingerprint = "anchor-produced|8"
    repo_id = await _seed_repo(session, name="cache-repo", files=[], imports=[])
    entity_id = await _entity(session, "cached-tool", repo_ids=[str(repo_id)])
    await session.flush()

    embedder = AnchoringEmbedder(
        fingerprint, {"cached-tool": [0.6, 0.8] + [0.0] * (DIMS - 2)}
    )
    await embed_repo_entities(
        session, embedder,
        entities=[{"entity_id": entity_id, "name": "cached-tool"}],
    )

    partition = child_table(anchor_mod.PARENT_TABLE, fingerprint)
    cache = child_table(anchor_mod.CACHE_PARENT_TABLE, fingerprint)
    stored = (await session.execute(text(
        f"SELECT CAST(embedding AS text) FROM {partition}"
    ))).scalar_one()
    cached = (await session.execute(text(
        f"SELECT CAST(embedding AS text) FROM {cache} "
        "WHERE name_lower = 'cached-tool'"
    ))).scalar_one()
    assert cached == stored


# ── structural guards ────────────────────────────────────────────────────


def test_the_module_never_calls_llm_fingerprint():
    """The phantom-fingerprint trap, which is worse here than for a reader.

    ``llm_fingerprint()`` is a formatter over static config and can name a
    partition no embed ever wrote to. Keying the missing-vector arm on one
    would make every repo entity look unembedded forever: re-embedded every
    run, into a table Phase 4 never probes, reporting a healthy count.
    """
    tree = ast.parse(MODULE_PATH.read_text(), filename=str(MODULE_PATH))
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "llm_fingerprint" not in called


def test_every_child_table_is_reached_through_the_parent_constant():
    """No statement may name a ``__<slug>`` child literally: one hardcoded
    table and every read silently answers about the wrong embedder."""
    tree = ast.parse(MODULE_PATH.read_text(), filename=str(MODULE_PATH))
    parents = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "child_table"):
            first = node.args[0]
            parents.add(first.value if isinstance(first, ast.Constant) else first.id)
    assert parents == {"PARENT_TABLE", "CACHE_PARENT_TABLE"}
    assert anchor_mod.PARENT_TABLE == "entity_embeddings"
    assert anchor_mod.CACHE_PARENT_TABLE == "entity_embedding_cache"


def test_the_anchoring_module_is_outside_the_derivers_import_closure():
    """Done-when 2, stated structurally.

    The deriver's LLM-free guard forbids the whole orchestrator surface,
    ``embed_batch_chunked`` included. This module calls it. The two therefore
    stay apart by construction: if the deriver ever imports this module, that
    guard fails the build rather than this test needing to notice.
    """
    from tests.test_code_deriver import _deriver_path_modules

    assert MODULE_PATH not in _deriver_path_modules()

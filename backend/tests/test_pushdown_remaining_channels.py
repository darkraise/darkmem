"""Pushdown on the channels no consumer enumeration ever listed.

T1.29a-c scoped the channels doc 07 §9 names. This module covers the ones it
does not, found by re-deriving the inventory from the code:

* **The clustering bulk read** (``get_all_vectors``). Authenticated, up to 5000
  rows, each carrying a content snippet. It had no project, status or archived
  predicate at all, and the unified graph reaches it, so it is the largest
  memory-content surface in the codebase.
* **The duplicates probe** (``find_similar``). Called with no filters while
  serving a REST route and an MCP tool, and its rows carry the payload content.
* **The graph neighbour expansion**. Scoped project and archived but never
  status, so a superseded neighbour reached ``get_memory_context``.

Every fixture here is a *twin* corpus: each out-of-scope row shares the in-scope
row's content, source and memory_type, and sits within cosine noise of its
vector. Nothing but the predicate can separate them, so a channel that stops
scoping surfaces the twin rather than merely ranking it lower.

The graph arms are deliberately asymmetric, and
``test_memory_context_keeps_an_edge_its_only_asserter_superseded`` is what pins
that: the *same* superseded memory must be absent from the neighbour rows and
still able to carry a relation. One scope object cannot satisfy both, which is
the interaction T1.29b left open.
"""
from __future__ import annotations

import uuid

import numpy as np
import pytest
from sqlalchemy import select, text

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import MemoryFilter, PostgresVectorRepository
from app.services.embedder_registry import child_table
from app.services.graph import GRAPH_MEMORY_STATUSES, GraphService
from app.services.pipeline import DUPLICATE_STATUSES, ProcessingPipeline

FINGERPRINT = "remaining-embedder|4"
OTHER_FINGERPRINT = "remaining-other-embedder|4"
DIMS = 4
TWIN_CONTENT = "connection pooling notes for the ingest path"

ALPHA_ACTIVE = MemoryFilter(project="alpha", statuses=("active",))


class _FakeLLM:
    def __init__(self, fingerprint: str = FINGERPRINT):
        self._fingerprint = fingerprint

    def llm_fingerprint(self) -> str:
        return self._fingerprint

    async def embed(self, query: str):
        return [1.0, 0.0, 0.0, 0.0], self._fingerprint


class _SessionFactory:
    """Hands ``ProcessingPipeline`` the test's own transaction.

    The pipeline opens its own session, which on a real factory is a different
    connection and therefore cannot see the fixture's uncommitted rows.
    """

    def __init__(self, session):
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc):
        return False


async def _seed_partition(session, fingerprint: str = FINGERPRINT) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": fingerprint, "mid": fingerprint.split("|")[0], "dims": DIMS},
    )
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({DIMS}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))


async def _add_memory(
    session,
    *,
    vector: list[float] | None = None,
    fingerprint: str = FINGERPRINT,
    **fields,
) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content=TWIN_CONTENT,
        source="test",
        memory_type="fact",
        importance=0.5,
        metadata_={},
        project="alpha",
        status="active",
        is_archived=False,
    )
    base.update(fields)
    memory = Memory(**base)
    session.add(memory)
    await session.flush()

    if vector is not None:
        child = child_table("memory_embeddings", fingerprint)
        await session.execute(
            text(
                f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
                "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
            ),
            {
                "mid": base["id"],
                "fp": fingerprint,
                "vec": str(vector),
                "payload": '{"content": "%s", "source": "test", "tags": []}' % base["content"],
            },
        )
        await session.flush()
    return memory


async def _seed_twins(session) -> dict:
    """One in-scope row and four twins, each blocked by a different predicate.

    The vectors differ only by noise well inside the 0.9 duplicate threshold, so
    every twin is a legitimate ANN hit and only the scope can drop it.
    """
    await _seed_partition(session)

    mine = await _add_memory(session, vector=[1.0, 0.0, 0.0, 0.0])
    foreign = await _add_memory(session, project="beta", vector=[1.0, 0.02, 0.0, 0.0])
    deprecated = await _add_memory(session, status="deprecated", vector=[1.0, 0.0, 0.02, 0.0])
    archived = await _add_memory(session, is_archived=True, vector=[1.0, 0.0, 0.0, 0.02])
    # chk_superseded_has_pointer forbids status='superseded' without a pointer.
    superseded = await _add_memory(
        session, status="superseded", superseded_by=mine.id, vector=[1.0, 0.03, 0.0, 0.0],
    )
    return {
        "mine": mine,
        "foreign": foreign,
        "deprecated": deprecated,
        "archived": archived,
        "superseded": superseded,
    }


# ── the bulk partition read: clustering ──────────────────────────────


@pytest.mark.asyncio
async def test_bulk_read_drops_every_out_of_scope_twin(session):
    rows = await _seed_twins(session)

    repo = PostgresVectorRepository(session)
    points = await repo.get_all_vectors(FINGERPRINT, limit=500, filters=ALPHA_ACTIVE)

    assert {p["memory_id"] for p in points} == {rows["mine"].id}


@pytest.mark.asyncio
async def test_bulk_read_labels_every_row_even_when_unscoped(session):
    """``filters=None`` is still a legal call, and T1.35's bar counts
    *unlabelled* rows — so the labels cannot be a by-product of scoping."""
    rows = await _seed_twins(session)

    repo = PostgresVectorRepository(session)
    points = await repo.get_all_vectors(FINGERPRINT, limit=500, filters=None)

    labels = {p["memory_id"]: (p["project"], p["status"]) for p in points}
    assert labels == {
        rows["mine"].id: ("alpha", "active"),
        rows["foreign"].id: ("beta", "active"),
        rows["deprecated"].id: ("alpha", "deprecated"),
        rows["archived"].id: ("alpha", "active"),
        rows["superseded"].id: ("alpha", "superseded"),
    }


@pytest.mark.asyncio
async def test_bulk_read_applies_the_scope_before_the_limit(session):
    """The discriminating test between SQL and a Python drop. The foreign rows
    are inserted first, so an unscoped ``LIMIT 3`` reads three of them and a
    post-filter hands back nothing at all."""
    await _seed_partition(session)
    for _ in range(6):
        await _add_memory(session, project="beta", vector=[1.0, 0.0, 0.0, 0.0])
    for _ in range(3):
        await _add_memory(session, project="alpha", vector=[1.0, 0.0, 0.0, 0.0])

    repo = PostgresVectorRepository(session)
    points = await repo.get_all_vectors(FINGERPRINT, limit=3, filters=ALPHA_ACTIVE)

    assert len(points) == 3
    assert {p["project"] for p in points} == {"alpha"}


@pytest.mark.asyncio
async def test_clustered_reads_forward_the_scope_to_the_bulk_read(session, monkeypatch):
    """Both clustering wrappers sit on the same unscoped read. A wrapper that
    stops forwarding reopens the channel behind a view that still looks scoped."""
    seen: list = []

    async def spy(self, fingerprint, limit=500, filters=None):
        seen.append(filters)
        return []

    monkeypatch.setattr(PostgresVectorRepository, "get_all_vectors", spy)

    async def matrix_spy(self, fingerprint, limit=500, filters=None):
        seen.append(filters)
        return [], np.empty((0, 0), dtype=np.float32)

    monkeypatch.setattr(PostgresVectorRepository, "get_vector_matrix", matrix_spy)
    repo = PostgresVectorRepository(session)
    await repo.get_clustered_vectors(FINGERPRINT, filters=ALPHA_ACTIVE)
    await repo.get_louvain_clustered_vectors(FINGERPRINT, filters=ALPHA_ACTIVE)

    assert seen == [ALPHA_ACTIVE, ALPHA_ACTIVE]


@pytest.mark.asyncio
async def test_unified_graph_scopes_and_labels_its_memory_nodes(session):
    rows = await _seed_twins(session)

    svc = GraphService(session, vector_repo=PostgresVectorRepository(session), llm=_FakeLLM())
    result = await svc.get_unified_graph(limit=500)

    assert {n["id"]: (n["project"], n["status"]) for n in result["memories"]} == {
        str(rows["mine"].id): ("alpha", "active"),
        str(rows["foreign"].id): ("beta", "active"),
    }


@pytest.mark.asyncio
async def test_unified_graph_scope_is_reachable_from_the_front_door(session):
    rows = await _seed_twins(session)

    svc = GraphService(session, vector_repo=PostgresVectorRepository(session), llm=_FakeLLM())
    result = await svc.get_unified_graph(limit=500, project="beta")

    assert [n["id"] for n in result["memories"]] == [str(rows["foreign"].id)]


# ── the duplicates probe ─────────────────────────────────────────────


async def _find_duplicates(session, memory_id) -> list[dict]:
    pipe = ProcessingPipeline(_FakeLLM(), _SessionFactory(session))
    return await pipe.find_duplicates(memory_id)


@pytest.mark.asyncio
async def test_duplicates_returns_the_in_project_active_twin(session):
    """The corpus is hostile in both directions: if the scope were too wide the
    tests below fail, and if it were too narrow this one does."""
    rows = await _seed_twins(session)
    peer = await _add_memory(session, vector=[1.0, 0.01, 0.0, 0.0])

    found = await _find_duplicates(session, rows["mine"].id)

    assert {r["memory_id"] for r in found} == {peer.id}


@pytest.mark.asyncio
async def test_duplicates_drops_every_out_of_scope_twin(session):
    rows = await _seed_twins(session)

    found = await _find_duplicates(session, rows["mine"].id)

    assert found == []


@pytest.mark.asyncio
async def test_duplicates_derives_its_scope_from_the_source_memory(session):
    """The scope is not a caller argument, so neither front door can widen it —
    which is only true while this forwarding holds."""
    rows = await _seed_twins(session)
    seen: dict = {}
    original = PostgresVectorRepository.find_similar

    async def spy(self, memory_id, fingerprint, threshold=0.9, limit=10, filters=None):
        seen["filters"] = filters
        return await original(self, memory_id, fingerprint, threshold, limit, filters)

    PostgresVectorRepository.find_similar = spy
    try:
        await _find_duplicates(session, rows["foreign"].id)
    finally:
        PostgresVectorRepository.find_similar = original

    assert seen["filters"] == MemoryFilter(project="beta", statuses=DUPLICATE_STATUSES)


@pytest.mark.asyncio
async def test_find_similar_forwards_its_filters_to_the_channel(session):
    """``find_similar`` has nothing of its own behind it: the predicate is only
    ever rendered by ``search``."""
    rows = await _seed_twins(session)
    seen: dict = {}
    repo = PostgresVectorRepository(session)
    original = repo.search

    async def spy(vector, fingerprint, limit=20, filters=None):
        seen["filters"] = filters
        return await original(vector, fingerprint, limit, filters)

    repo.search = spy
    await repo.find_similar(rows["mine"].id, fingerprint=FINGERPRINT, filters=ALPHA_ACTIVE)

    assert seen["filters"] == ALPHA_ACTIVE


# ── the graph neighbour expansion ────────────────────────────────────


async def _seed_neighbour_graph(session) -> dict:
    """One entity asserted by the seed and by four neighbour candidates, plus an
    edge whose only asserter is the superseded one."""
    seed = await _add_memory(session, content="seed capture")
    active = await _add_memory(session, content="active neighbour")
    superseded_peer = await _add_memory(session, content="pointer target")
    superseded = await _add_memory(
        session, content="superseded neighbour",
        status="superseded", superseded_by=superseded_peer.id,
    )
    archived = await _add_memory(session, content="archived neighbour", is_archived=True)
    foreign = await _add_memory(session, content="foreign neighbour", project="beta")

    hub, spoke = uuid.uuid4(), uuid.uuid4()
    for eid, name, mids in (
        (hub, "hub-entity", [seed.id, active.id, superseded.id, archived.id, foreign.id]),
        (spoke, "spoke-entity", [seed.id]),
    ):
        await session.execute(
            text(
                "INSERT INTO entities (id, name, entity_type, memory_ids) "
                "VALUES (CAST(:id AS uuid), :name, 'tool', CAST(:mids AS uuid[]))"
            ),
            {"id": str(eid), "name": name, "mids": [str(m) for m in mids]},
        )
    await session.execute(
        text(
            "INSERT INTO entity_relations "
            "(id, source_entity_id, target_entity_id, rel_type, weight, memory_ids) "
            "VALUES (gen_random_uuid(), CAST(:s AS uuid), CAST(:t AS uuid), "
            "'USES', 0.9, CAST(:mids AS uuid[]))"
        ),
        {"s": str(hub), "t": str(spoke), "mids": [str(superseded.id)]},
    )
    await session.flush()
    return {
        "seed": seed, "active": active, "superseded": superseded,
        "archived": archived, "foreign": foreign,
    }


@pytest.mark.asyncio
async def test_memory_context_neighbours_exclude_every_dead_row(session):
    rows = await _seed_neighbour_graph(session)

    svc = GraphService(session, graph_repo=PostgresGraphRepository(session))
    context = await svc.get_memory_context(str(rows["seed"].id))

    assert {n["id"] for n in context["neighbors"]} == {str(rows["active"].id)}


@pytest.mark.asyncio
async def test_memory_context_labels_the_neighbours_it_returns(session):
    rows = await _seed_neighbour_graph(session)

    svc = GraphService(session, graph_repo=PostgresGraphRepository(session))
    context = await svc.get_memory_context(str(rows["seed"].id))

    assert context["neighbors"][0]["project"] == "alpha"
    assert context["neighbors"][0]["status"] == "active"


@pytest.mark.asyncio
async def test_memory_context_keeps_an_edge_its_only_asserter_superseded(session):
    """The interaction, pinned. The superseded memory is excluded from the rows
    above *and* is the sole asserter of this edge, so collapsing the two arms
    onto one scope object cannot pass both tests.

    An edge is a claim about structure, and the reader who opens the context of
    a memory the corpus has replaced is the reader who most needs to see what it
    claimed. The neighbour rows are different: they are memory content presented
    as live peers, which is what doc 07 §7's bar counts.
    """
    rows = await _seed_neighbour_graph(session)

    svc = GraphService(session, graph_repo=PostgresGraphRepository(session))
    context = await svc.get_memory_context(str(rows["seed"].id))

    assert [(r["source"], r["target"]) for r in context["relations"]] == [
        ("hub-entity", "spoke-entity"),
    ]


@pytest.mark.asyncio
async def test_memory_scope_applies_lifecycle_even_without_a_project(session):
    """An unresolvable seed must degrade to a narrower answer, never to an
    unscoped one."""
    assert GraphService._memory_scope(None) == MemoryFilter(
        project=None, statuses=GRAPH_MEMORY_STATUSES, include_archived=False,
    )
    assert GraphService._memory_scope(MemoryFilter(project="alpha")) == MemoryFilter(
        project="alpha", statuses=GRAPH_MEMORY_STATUSES, include_archived=False,
    )


# ── the two renderings of one scope ──────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filters",
    [
        MemoryFilter(),
        MemoryFilter(project="alpha"),
        MemoryFilter(statuses=("active",)),
        MemoryFilter(project="alpha", statuses=("active", "superseded")),
        MemoryFilter(project="alpha", statuses=("active",), include_archived=True),
        MemoryFilter(statuses=("no-such-status",)),
    ],
)
async def test_orm_criteria_and_where_sql_select_the_same_rows(session, filters):
    """``_fetch_neighbor_memories`` builds an ORM select while every other arm
    renders SQL text. Two renderings of one scope drift silently; this is the
    only thing standing between them."""
    await _seed_twins(session)

    sql_ids = set(
        (
            await session.execute(
                text(f"SELECT id FROM memories m WHERE {filters.where_sql('m')}"),
                filters.params(),
            )
        ).scalars().all()
    )
    orm_ids = set(
        (
            await session.execute(select(Memory.id).where(*filters.orm_criteria(Memory)))
        ).scalars().all()
    )

    assert sql_ids == orm_ids

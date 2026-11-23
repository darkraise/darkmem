"""Project / status / archived pushdown on the semantic retrieval channel.

Three properties are under test, and each has a mutation that breaks it:

* **The predicates live in the SQL.** Both semantic implementations — the
  vector repository's ``search`` and ``HybridSearchService._semantic_search`` —
  are called directly, with nothing downstream to re-filter their rows. A row
  outside the scope must never come back.
* **The fetch multiplier survives.** An HNSW scan applies the pushed-down
  predicate as a post-scan filter over its candidate stream, so a scoped query
  must over-fetch or it silently under-returns. The bound ``LIMIT`` is
  inspected directly, because on a table this small Postgres never picks the
  index and the shortfall the multiplier prevents cannot be provoked.
* **The str/UUID boundary still holds.** Hybrid search emits string ids and the
  vector repository emits ``UUID``; a consumer that fails to normalise drops
  the match with no error at all. Both channels are driven through
  ``MemoryService.search_memories`` and must resolve to the same row.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.repositories.vector import (
    SEMANTIC_FETCH_MULTIPLIER,
    MemoryFilter,
    PostgresVectorRepository,
)
from app.schemas.memory import MemorySearchRequest
from app.services.embedder_registry import child_table
from app.services.hybrid_search import HybridSearchService
from app.services.memory import MemoryService
from app.services.rank_fusion import FUSION_FETCH_DEPTH

FINGERPRINT = "pushdown-embedder|4"
DIMS = 4
QUERY_VECTOR = [1.0, 0.0, 0.0, 0.0]


class _FakeLLM:
    """Only ``embed`` is reached by the search paths under test."""

    def __init__(self, vector: list[float], fingerprint: str):
        self._vector = vector
        self._fingerprint = fingerprint

    async def embed(self, query: str):
        return self._vector, self._fingerprint


class _RecordingSession:
    """Proxies a real session, keeping the parameters of every execute call."""

    def __init__(self, inner):
        self._inner = inner
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, statement, params=None, *args, **kwargs):
        self.calls.append((str(statement), dict(params or {})))
        return await self._inner.execute(statement, params, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._inner, name)


async def _seed_partition(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": FINGERPRINT, "mid": "pushdown-embedder", "dims": DIMS},
    )
    child = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({DIMS}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))


async def _add_memory(session, *, vector=None, **fields) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content="pgbouncer connection pooling notes",
        source="test",
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

    child = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), '{}'::jsonb)"
        ),
        {"mid": base["id"], "fp": FINGERPRINT, "vec": str(vector or QUERY_VECTOR)},
    )
    await session.flush()
    return memory


# ── the predicates are in the SQL ────────────────────────────────────


@pytest.mark.asyncio
async def test_vector_search_scopes_project_in_sql(session):
    await _seed_partition(session)
    mine = await _add_memory(session, project="alpha")
    await _add_memory(session, project="beta")

    repo = PostgresVectorRepository(session)
    rows = await repo.search(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=10,
        filters=MemoryFilter(project="alpha"),
    )

    assert [r["memory_id"] for r in rows] == [mine.id]


@pytest.mark.asyncio
async def test_vector_search_excludes_archived_in_sql(session):
    await _seed_partition(session)
    live = await _add_memory(session)
    await _add_memory(session, is_archived=True)

    repo = PostgresVectorRepository(session)
    rows = await repo.search(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=10, filters=MemoryFilter(),
    )

    assert [r["memory_id"] for r in rows] == [live.id]


@pytest.mark.asyncio
async def test_vector_search_scopes_status_in_sql(session):
    await _seed_partition(session)
    active = await _add_memory(session)
    replacement = await _add_memory(session)
    gone = await _add_memory(session, status="superseded", superseded_by=replacement.id)

    repo = PostgresVectorRepository(session)
    active_only = await repo.search(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=10,
        filters=MemoryFilter(statuses=("active",)),
    )
    assert gone.id not in {r["memory_id"] for r in active_only}
    assert {active.id, replacement.id} <= {r["memory_id"] for r in active_only}

    # A caller that explicitly asks for lineage still gets the superseded row.
    with_lineage = await repo.search(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=10,
        filters=MemoryFilter(statuses=("active", "superseded")),
    )
    assert gone.id in {r["memory_id"] for r in with_lineage}


@pytest.mark.asyncio
async def test_vector_search_unfiltered_keeps_every_candidate(session):
    """``filters=None`` is the dedup/crossref probe's contract: no scoping."""
    await _seed_partition(session)
    live = await _add_memory(session)
    archived = await _add_memory(session, is_archived=True, project="beta")

    repo = PostgresVectorRepository(session)
    rows = await repo.search(QUERY_VECTOR, fingerprint=FINGERPRINT, limit=10)

    assert {live.id, archived.id} == {r["memory_id"] for r in rows}


@pytest.mark.asyncio
async def test_hybrid_semantic_channel_scopes_in_sql(session):
    await _seed_partition(session)
    mine = await _add_memory(session, project="alpha")
    foreign = await _add_memory(session, project="beta")
    archived = await _add_memory(session, project="alpha", is_archived=True)

    svc = HybridSearchService(_FakeLLM(QUERY_VECTOR, FINGERPRINT), session)
    rows = await svc._semantic_search(
        QUERY_VECTOR, FINGERPRINT, 10, MemoryFilter(project="alpha", statuses=("active",)),
    )

    ids = {r["memory_id"] for r in rows}
    assert str(mine.id) in ids
    assert str(foreign.id) not in ids
    assert str(archived.id) not in ids


@pytest.mark.asyncio
async def test_hybrid_search_passes_filters_to_semantic_channel(session):
    """End to end through ``search``: the fused list carries no foreign row
    from the semantic side."""
    await _seed_partition(session)
    mine = await _add_memory(session, project="alpha", content="alpha only marker")
    foreign = await _add_memory(session, project="beta", content="alpha only marker")

    svc = HybridSearchService(_FakeLLM(QUERY_VECTOR, FINGERPRINT), session)
    rows = await svc.search(
        "zzz-no-keyword-match", limit=10, filters=MemoryFilter(project="alpha"),
    )

    ids = {r["memory_id"] for r in rows}
    assert str(mine.id) in ids
    assert str(foreign.id) not in ids


# ── the fetch multiplier still compensates ───────────────────────────


def test_fetch_multiplier_is_still_three():
    """The literal is asserted here so the over-fetch tests below can use
    literal expectations; deriving them from the constant would make them
    pass no matter what it is changed to."""
    assert SEMANTIC_FETCH_MULTIPLIER == 3


@pytest.mark.asyncio
async def test_scoped_vector_search_overfetches_then_slices(session):
    """A scoped probe binds ``limit x SEMANTIC_FETCH_MULTIPLIER`` and returns
    at most ``limit``. Without the widened fetch, HNSW's post-scan filter would
    drop candidates below the requested page size."""
    await _seed_partition(session)
    for _ in range(8):
        await _add_memory(session)

    recording = _RecordingSession(session)
    repo = PostgresVectorRepository(recording)
    rows = await repo.search(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=3, filters=MemoryFilter(),
    )

    assert len(rows) == 3
    probe = recording.calls[-1][1]
    assert probe["limit"] == 9


@pytest.mark.asyncio
async def test_scoped_vector_search_breaks_ties_by_id_before_slicing(session):
    await _seed_partition(session)
    added = [await _add_memory(session) for _ in range(8)]

    rows = await PostgresVectorRepository(session).search(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=3, filters=MemoryFilter(),
    )

    assert len({row["score"] for row in rows}) == 1
    assert [str(row["memory_id"]) for row in rows] == sorted(str(m.id) for m in added)[:3]


@pytest.mark.asyncio
async def test_unscoped_vector_search_does_not_overfetch(session):
    await _seed_partition(session)
    for _ in range(8):
        await _add_memory(session)

    recording = _RecordingSession(session)
    repo = PostgresVectorRepository(recording)
    rows = await repo.search(QUERY_VECTOR, fingerprint=FINGERPRINT, limit=3)

    assert len(rows) == 3
    assert recording.calls[-1][1]["limit"] == 3


@pytest.mark.asyncio
async def test_hybrid_search_reads_both_arms_to_the_fixed_fusion_depth(session):
    """The arm depth does not follow the caller's page size.

    It used to be ``limit x SEMANTIC_FETCH_MULTIPLIER``, which made the fused
    ordering a function of how many rows the caller happened to want: chat
    asked for ten and fused thirty candidates, the search surface asked for
    sixty and fused a hundred and eighty, and the two ranked one corpus
    differently at fully default flags. RRF is not truncation-consistent
    across depths, so the depth is a constant and the caller's limit only
    truncates.
    """
    await _seed_partition(session)
    for _ in range(8):
        await _add_memory(session)

    recording = _RecordingSession(session)
    svc = HybridSearchService(_FakeLLM(QUERY_VECTOR, FINGERPRINT), recording)
    rows = await svc.search("pgbouncer pooling", limit=4, filters=MemoryFilter())

    assert len(rows) <= 4
    semantic_probe = recording.calls[0][1]
    keyword_probe = recording.calls[1][1]
    assert semantic_probe["limit"] == FUSION_FETCH_DEPTH
    assert keyword_probe["limit"] == FUSION_FETCH_DEPTH


@pytest.mark.asyncio
async def test_a_request_deeper_than_the_fusion_floor_widens_the_arms(session):
    """The floor is a floor, not a cap: two arms holding the same rows could
    not fill a request larger than it, so a deep pager still reads at least as
    many rows as it asked for."""
    await _seed_partition(session)
    await _add_memory(session)

    recording = _RecordingSession(session)
    svc = HybridSearchService(_FakeLLM(QUERY_VECTOR, FINGERPRINT), recording)
    await svc.search(
        "pgbouncer pooling", limit=FUSION_FETCH_DEPTH + 40, filters=MemoryFilter(),
    )

    assert recording.calls[0][1]["limit"] == FUSION_FETCH_DEPTH + 40


# ── asyncpg CAST on the bound parameters ─────────────────────────────


@pytest.mark.asyncio
async def test_scoped_search_binds_project_and_status_without_type_errors(session):
    """``= ANY(:param)`` is the shape that raises IndeterminateDatatypeError
    when the bound parameter is not cast."""
    await _seed_partition(session)
    mine = await _add_memory(session, project="alpha")

    repo = PostgresVectorRepository(session)
    rows = await repo.search(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=5,
        filters=MemoryFilter(project="alpha", statuses=("active", "deprecated")),
    )

    assert [r["memory_id"] for r in rows] == [mine.id]


@pytest.mark.asyncio
async def test_unknown_status_matches_nothing_rather_than_erroring(session):
    await _seed_partition(session)
    await _add_memory(session)

    repo = PostgresVectorRepository(session)
    rows = await repo.search(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=5,
        filters=MemoryFilter(statuses=("not-a-status",)),
    )

    assert rows == []


# ── the str/UUID boundary ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_channels_disagree_on_id_type_by_design(session):
    await _seed_partition(session)
    mem = await _add_memory(session)

    repo_rows = await PostgresVectorRepository(session).search(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=5, filters=MemoryFilter(),
    )
    hybrid_rows = await HybridSearchService(
        _FakeLLM(QUERY_VECTOR, FINGERPRINT), session,
    )._semantic_search(QUERY_VECTOR, FINGERPRINT, 5, MemoryFilter())

    assert all(isinstance(r["memory_id"], uuid.UUID) for r in repo_rows)
    assert all(isinstance(r["memory_id"], str) for r in hybrid_rows)
    assert mem.id in {r["memory_id"] for r in repo_rows}
    assert str(mem.id) in {r["memory_id"] for r in hybrid_rows}


class _IdTypePipeline:
    """Returns the ids a given channel would: ``str`` for hybrid, ``UUID`` for
    the vector repository."""

    def __init__(self, ids, as_string: bool):
        self._ids = ids
        self._as_string = as_string
        self.last_filters = None

    async def semantic_search(self, query, limit=20, semantic_weight=0.7, filters=None):
        self.last_filters = filters
        return [
            {"memory_id": str(i) if self._as_string else i, "score": 1.0}
            for i in self._ids
        ]


@pytest.mark.asyncio
@pytest.mark.parametrize("as_string", [True, False])
async def test_both_id_shapes_resolve_to_the_same_row(session, as_string):
    """The silent-drop guard: if the boundary stops normalising, the string
    channel resolves nothing and this returns an empty page with no error."""
    await _seed_partition(session)
    mem = await _add_memory(session, content="boundary marker")

    svc = MemoryService(session, pipeline=_IdTypePipeline([mem.id], as_string))
    rows = await svc.search_memories(MemorySearchRequest(query="q", limit=5))

    assert [r.id for r in rows] == [mem.id]


@pytest.mark.asyncio
async def test_service_forwards_request_scope_to_the_semantic_channel(session):
    await _seed_partition(session)
    mem = await _add_memory(session, project="alpha")

    pipeline = _IdTypePipeline([mem.id], as_string=True)
    svc = MemoryService(session, pipeline=pipeline)
    await svc.search_memories(
        MemorySearchRequest(query="q", limit=5, project="alpha", status=["active"]),
    )

    assert pipeline.last_filters == MemoryFilter(
        project="alpha", statuses=("active",), include_archived=False,
    )

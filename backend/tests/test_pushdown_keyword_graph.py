"""Project / status / archived pushdown on the keyword and graph channels.

The semantic channel landed first (``test_pushdown_semantic.py``) but had to
leave the service-layer Python drop in place, because hybrid fusion still mixed
in an unscoped keyword arm. This module covers the rest of that move:

* **The keyword arm renders the predicates itself.** ``ts_rank`` against
  ``memories.search_vector`` is an ordinary table scan, so the scope belongs in
  its ``WHERE`` — and once it is there, the Python drop is gone and nothing
  downstream re-applies it.
* **Both channels can show an index plan.** Unlike the semantic side, whose
  HNSW scan applies a predicate post-scan, these are index-eligible. The plans
  are read out of ``EXPLAIN`` rather than assumed.
* **The graph walk cannot cross a project boundary mid-walk.** Entities are not
  memory-scoped: an entity carries the ``memory_ids`` of every memory asserting
  it, so an entity shared between two projects is a legal stepping stone whose
  far side is not. Scoping only the seed walks straight over that boundary.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import MemoryFilter
from app.schemas.memory import MemorySearchRequest
from app.services.embedder_registry import child_table
from app.services.graph import GraphService
from app.services.hybrid_search import HybridSearchService
from app.services.memory import MemoryService

FINGERPRINT = "kwgraph-embedder|4"
DIMS = 4
QUERY_VECTOR = [1.0, 0.0, 0.0, 0.0]
RARE_TERM = "zarquon"


class _FakeLLM:
    def __init__(self, vector: list[float], fingerprint: str):
        self._vector = vector
        self._fingerprint = fingerprint

    async def embed(self, query: str):
        return self._vector, self._fingerprint


class _HybridPipeline:
    """Drives the real ``HybridSearchService`` from ``MemoryService``, so the
    service path is exercised with nothing between the SQL and the caller."""

    def __init__(self, session):
        self._session = session

    async def semantic_search(self, query, limit=20, semantic_weight=0.7, filters=None):
        svc = HybridSearchService(_FakeLLM(QUERY_VECTOR, FINGERPRINT), self._session)
        return await svc.search(
            query, limit=limit, semantic_weight=semantic_weight, filters=filters,
        )


async def _seed_partition(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": FINGERPRINT, "mid": "kwgraph-embedder", "dims": DIMS},
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


async def _add_memory(session, *, embed=False, **fields) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content=f"{RARE_TERM} pooling notes",
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

    if embed:
        child = child_table("memory_embeddings", FINGERPRINT)
        await session.execute(
            text(
                f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
                "VALUES (:mid, :fp, CAST(:vec AS vector), '{}'::jsonb)"
            ),
            {"mid": base["id"], "fp": FINGERPRINT, "vec": str(QUERY_VECTOR)},
        )
        await session.flush()
    return memory


# ── the keyword arm renders the predicates ───────────────────────────


@pytest.mark.asyncio
async def test_keyword_arm_scopes_project_in_sql(session):
    mine = await _add_memory(session, project="alpha")
    await _add_memory(session, project="beta")

    svc = HybridSearchService(_FakeLLM(QUERY_VECTOR, FINGERPRINT), session)
    rows = await svc._keyword_search(RARE_TERM, 20, MemoryFilter(project="alpha"))

    assert [r["memory_id"] for r in rows] == [str(mine.id)]


@pytest.mark.asyncio
async def test_keyword_arm_excludes_archived_in_sql(session):
    live = await _add_memory(session)
    await _add_memory(session, is_archived=True)

    svc = HybridSearchService(_FakeLLM(QUERY_VECTOR, FINGERPRINT), session)
    rows = await svc._keyword_search(RARE_TERM, 20, MemoryFilter())

    assert [r["memory_id"] for r in rows] == [str(live.id)]


@pytest.mark.asyncio
async def test_keyword_arm_scopes_status_in_sql(session):
    active = await _add_memory(session)
    replacement = await _add_memory(session)
    gone = await _add_memory(
        session, status="superseded", superseded_by=replacement.id,
    )

    svc = HybridSearchService(_FakeLLM(QUERY_VECTOR, FINGERPRINT), session)
    ids = {
        r["memory_id"]
        for r in await svc._keyword_search(
            RARE_TERM, 20, MemoryFilter(statuses=("active",)),
        )
    }
    assert str(gone.id) not in ids
    assert {str(active.id), str(replacement.id)} <= ids

    lineage = {
        r["memory_id"]
        for r in await svc._keyword_search(
            RARE_TERM, 20, MemoryFilter(statuses=("active", "superseded")),
        )
    }
    assert str(gone.id) in lineage


@pytest.mark.asyncio
async def test_keyword_arm_unfiltered_keeps_every_candidate(session):
    """``filters=None`` stays unscoped — the fallback the reason path still
    uses until its own pushdown lands."""
    live = await _add_memory(session)
    archived = await _add_memory(session, is_archived=True, project="beta")

    svc = HybridSearchService(_FakeLLM(QUERY_VECTOR, FINGERPRINT), session)
    rows = await svc._keyword_search(RARE_TERM, 20)

    assert {str(live.id), str(archived.id)} == {r["memory_id"] for r in rows}


@pytest.mark.asyncio
async def test_keyword_arm_binds_project_and_status_without_type_errors(session):
    """``= ANY(:param)`` raises IndeterminateDatatypeError when the bound
    parameter is not cast, which is the shape a project/status scope takes."""
    mine = await _add_memory(session, project="alpha")

    svc = HybridSearchService(_FakeLLM(QUERY_VECTOR, FINGERPRINT), session)
    rows = await svc._keyword_search(
        RARE_TERM, 20,
        MemoryFilter(project="alpha", statuses=("active", "deprecated")),
    )

    assert [r["memory_id"] for r in rows] == [str(mine.id)]


@pytest.mark.asyncio
async def test_keyword_arm_unknown_status_matches_nothing(session):
    await _add_memory(session)

    svc = HybridSearchService(_FakeLLM(QUERY_VECTOR, FINGERPRINT), session)
    rows = await svc._keyword_search(
        RARE_TERM, 20, MemoryFilter(statuses=("not-a-status",)),
    )

    assert rows == []


@pytest.mark.asyncio
async def test_fused_result_carries_no_foreign_keyword_row(session):
    """The whole point of scoping this arm: a keyword-only hit from another
    project must not enter the fusion. The semantic side cannot mask this —
    neither row is embedded, so only the keyword arm produces candidates."""
    await _seed_partition(session)
    mine = await _add_memory(session, project="alpha")
    foreign = await _add_memory(session, project="beta")

    svc = HybridSearchService(_FakeLLM(QUERY_VECTOR, FINGERPRINT), session)
    rows = await svc.search(RARE_TERM, limit=10, filters=MemoryFilter(project="alpha"))

    ids = {r["memory_id"] for r in rows}
    assert str(mine.id) in ids
    assert str(foreign.id) not in ids


# ── the service layer no longer re-filters in Python ─────────────────


@pytest.mark.asyncio
async def test_service_no_longer_drops_rows_in_python(session):
    """Project, status and archived are gone from the in-memory filter. If a
    channel stops scoping, this is where it shows: nothing downstream would
    catch it."""
    svc = MemoryService(session)
    params = MemorySearchRequest(
        query="q", project="alpha", status=["active"],
    )
    foreign = await _add_memory(session, project="beta", status="active")

    assert svc._matches_schema_v2_filters(foreign, params) is True


class _RecordingPipeline:
    def __init__(self):
        self.last_filters = "unset"

    async def semantic_search(self, query, limit=20, semantic_weight=0.7, filters=None):
        self.last_filters = filters
        return []


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["search_memories", "search_memories_paginated"])
async def test_service_forwards_request_scope_on_every_search_entry_point(session, method):
    """Both entry points forward the scope. Neither has anything behind it any
    more, so a call site that stops forwarding leaks silently."""
    pipeline = _RecordingPipeline()
    svc = MemoryService(session, pipeline=pipeline)

    await getattr(svc, method)(
        MemorySearchRequest(query="q", limit=5, project="alpha", status=["active"]),
    )

    assert pipeline.last_filters == MemoryFilter(
        project="alpha", statuses=("active",), include_archived=False,
    )


@pytest.mark.asyncio
async def test_hybrid_search_forwards_the_scope_to_the_keyword_arm(session):
    recorded: dict = {}
    svc = HybridSearchService(_FakeLLM(QUERY_VECTOR, FINGERPRINT), session)
    original = svc._keyword_search

    async def spy(query, limit, filters=None):
        recorded["filters"] = filters
        return await original(query, limit, filters)

    svc._keyword_search = spy
    scope = MemoryFilter(project="alpha", statuses=("active",))
    await _seed_partition(session)
    await svc.search(RARE_TERM, limit=5, filters=scope)

    assert recorded["filters"] == scope


@pytest.mark.asyncio
async def test_pipeline_forwards_the_scope_to_both_channels(monkeypatch):
    """``ProcessingPipeline.semantic_search`` is the only path the service
    layer has to a channel; if it drops the scope, every caller is unscoped."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    import app.services.pipeline as pipeline_mod
    from app.services.pipeline import ProcessingPipeline, _flag_cache_reset
    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    scope = MemoryFilter(project="alpha", statuses=("active",))
    seen: dict = {}

    class _StubHybrid:
        def __init__(self, llm, session):
            pass

        async def search(
                self, query, limit=20, semantic_weight=0.7, filters=None,
                ppr_weight=0.0,
            ):
            seen["hybrid"] = filters
            return []

    class _StubVectorRepo:
        def __init__(self, session):
            pass

        async def search(self, vector, fingerprint, limit=20, filters=None):
            seen["vector"] = filters
            return []

    class _StubLLM:
        async def embed(self, query):
            return QUERY_VECTOR, FINGERPRINT

    monkeypatch.setattr(
        "app.services.hybrid_search.HybridSearchService", _StubHybrid, raising=True,
    )
    monkeypatch.setattr(pipeline_mod, "PostgresVectorRepository", _StubVectorRepo)

    pipe = ProcessingPipeline(_StubLLM(), factory)
    _flag_cache_reset()
    try:
        monkeypatch.setattr(
            pipeline_mod, "_get_feature_flags_cached",
            _stub_flags(hybrid=True), raising=True,
        )
        await pipe.semantic_search("q", limit=5, filters=scope)
        assert seen["hybrid"] == scope

        monkeypatch.setattr(
            pipeline_mod, "_get_feature_flags_cached",
            _stub_flags(hybrid=False), raising=True,
        )
        await pipe.semantic_search("q", limit=5, filters=scope)
        assert seen["vector"] == scope
    finally:
        _flag_cache_reset()


def _stub_flags(hybrid: bool):
    async def _flags(_factory):
        return {
            "hybrid_search_enabled": hybrid,
            "reranker_enabled": False,
            "confidence_rank_gamma": 0.0,
        }
    return _flags


@pytest.mark.asyncio
async def test_search_memories_scopes_the_keyword_arm_end_to_end(session):
    """Through ``MemoryService.search_memories`` with the real hybrid service:
    a foreign-project keyword hit reaches the caller unless the SQL drops it."""
    await _seed_partition(session)
    mine = await _add_memory(session, project="alpha", embed=True)
    foreign = await _add_memory(session, project="beta")
    archived = await _add_memory(session, project="alpha", is_archived=True)

    svc = MemoryService(session, pipeline=_HybridPipeline(session))
    rows = await svc.search_memories(
        MemorySearchRequest(query=RARE_TERM, limit=20, project="alpha"),
    )

    ids = {m.id for m in rows}
    assert mine.id in ids
    assert foreign.id not in ids
    assert archived.id not in ids


@pytest.mark.asyncio
async def test_paginated_search_scopes_the_keyword_arm_end_to_end(session):
    await _seed_partition(session)
    mine = await _add_memory(session, project="alpha", embed=True)
    foreign = await _add_memory(session, project="beta")
    archived = await _add_memory(session, project="alpha", is_archived=True)

    svc = MemoryService(session, pipeline=_HybridPipeline(session))
    page = await svc.search_memories_paginated(
        MemorySearchRequest(query=RARE_TERM, limit=20, project="alpha"),
    )

    ids = {m.id for m in page["items"]}
    assert mine.id in ids
    assert foreign.id not in ids
    assert archived.id not in ids
    assert page["total"] == len(ids)


# ── index plans, read out of EXPLAIN ─────────────────────────────────
#
# The seeded corpus is far smaller than anything the planner would prefer an
# index for on its own merits, so ``enable_seqscan`` is forced off: what is
# under test is that the query SHAPE is index-eligible (predicate columns and
# expression form), not that Postgres always picks the index at this row count.


async def _plan(session, sql: str, params: dict) -> str:
    await session.execute(text("SET LOCAL enable_seqscan = off"))
    rows = await session.execute(text(f"EXPLAIN {sql}"), params)
    return "\n".join(r[0] for r in rows)


async def _seed_bulk_corpus(session, rows: int = 5000) -> None:
    """Enough rows that the FTS index is genuinely the cheapest path to the one
    document carrying the rare term. A handful of rows makes every index look
    the same to the planner and the plan assertion meaningless."""
    await session.execute(
        text(
            "INSERT INTO memories (id, content, source, project, status, is_archived) "
            "SELECT gen_random_uuid(), 'connection pooling notes number ' || i, "
            "'test', CASE WHEN i % 3 = 0 THEN 'beta' ELSE 'alpha' END, "
            "'active', false FROM generate_series(1, :n) i"
        ),
        {"n": rows},
    )


async def _settle_statistics(session) -> None:
    """A GIN index buffers fresh entries in a pending list, and the planner
    charges a scan for the whole of it — so a bulk insert makes the FTS index
    look arbitrarily expensive until the list is flushed. Without this the
    plan below is an artefact of the fixture, not of the query."""
    await session.execute(text("SELECT gin_clean_pending_list('ix_memories_fts')"))
    await session.execute(text("ANALYZE memories"))


@pytest.mark.asyncio
async def test_keyword_query_can_use_the_fts_index(session):
    await _seed_bulk_corpus(session)
    await _add_memory(session, project="alpha")
    await _settle_statistics(session)

    scope = MemoryFilter(project="alpha", statuses=("active",))
    svc = HybridSearchService(_FakeLLM(QUERY_VECTOR, FINGERPRINT), session)
    sql, params = svc.keyword_query(RARE_TERM, 20, scope)
    plan = await _plan(session, sql, params)

    assert "ix_memories_fts" in plan, plan
    assert "Seq Scan on memories" not in plan, plan


@pytest.mark.asyncio
async def test_keyword_scope_alone_can_use_the_project_index(session):
    """Without the FTS term the scope must still be sargable — this is the
    direct-scan side of the same predicate."""
    await _add_memory(session, project="alpha")

    scope = MemoryFilter(project="alpha")
    plan = await _plan(
        session,
        f"SELECT m.id FROM memories m WHERE {scope.where_sql('m')} LIMIT 20",
        scope.params(),
    )

    assert "Index Scan" in plan or "Bitmap Index Scan" in plan, plan
    assert "Seq Scan on memories" not in plan, plan


async def _seed_scope_selective_corpus(session, rows: int = 2000) -> None:
    """Make ``project = 'alpha'`` a genuinely selective predicate.

    On the walk's own three memories the scope matches nearly the whole table,
    which leaves the two project-bearing indexes costing the same; the planner
    then breaks the tie on ``memories``' physical page count, which is set by
    whichever bulk-inserting test ran earlier in the session and which this
    test cannot control. Sized like this the ``(id, project)`` unique index is
    the cheapest path outright, measured stable against a table bloated by up
    to 50k rolled-back rows.
    """
    await session.execute(
        text(
            "INSERT INTO memories (id, content, source, project, status, is_archived) "
            "SELECT gen_random_uuid(), 'scope filler ' || i, 'test', "
            "CASE WHEN i % 3 = 0 THEN 'alpha' ELSE 'beta' END, "
            "'active', false FROM generate_series(1, :n) i"
        ),
        {"n": rows},
    )


async def _settle_graph_statistics(session) -> None:
    """The seeded rows are uncommitted, and ANALYZE counts rows its own
    transaction inserted — so this describes the fixture rather than whatever
    the table held when the last ANALYZE ran."""
    for table in ("memories", "entities", "entity_relations"):
        await session.execute(text(f"ANALYZE {table}"))


@pytest.mark.asyncio
async def test_graph_walk_can_use_indexes_on_every_join(session):
    """Edge expansion, endpoint resolution and the scope predicate must each
    reach an index; a sequential scan on any of them means the walk degrades
    into a full-graph sweep once the corpus grows."""
    ids = await _seed_two_project_graph(session)
    await _seed_scope_selective_corpus(session)
    await _settle_graph_statistics(session)

    scope = MemoryFilter(project="alpha", statuses=("active",))
    repo = PostgresGraphRepository(session)
    await session.execute(text("SET LOCAL enable_seqscan = off"))
    sql, params = repo.neighbors_query(ids["seed"], max_depth=2, scope=scope)
    rows = await session.execute(text(f"EXPLAIN {sql}"), params)
    plan = "\n".join(r[0] for r in rows)

    assert "ix_entity_relations_target" in plan, plan
    assert "entities_pkey" in plan, plan
    assert "memories_id_project_key" in plan, plan
    assert "Seq Scan" not in plan, plan


# ── the graph walk cannot cross a project boundary mid-walk ──────────


async def _seed_two_project_graph(session) -> dict:
    """The hostile shape, built so each half of the scope is separately
    observable. ``shared`` is asserted by BOTH an alpha and a beta memory, so it
    is legitimately in scope for an alpha walk *and* is the stepping stone out
    of it. The three exits differ in which predicate has to stop them:

    * ``foreign`` — beta entity behind a beta edge; either predicate stops it.
    * ``foreign-via-local-edge`` — beta entity behind an **alpha** edge. Only
      scoping the expanded entity stops this one.
    * ``local-via-foreign-edge`` → ``beyond-foreign-edge`` — alpha entities
      behind a **beta** edge. Only scoping the traversed relation stops these,
      and the second hop is what makes the recursive predicate (rather than the
      output filter) the thing under test.
    """
    alpha = await _add_memory(session, project="alpha", content="alpha capture")
    alpha_two = await _add_memory(session, project="alpha", content="alpha capture two")
    beta = await _add_memory(session, project="beta", content="beta capture")

    names = {
        "seed": "seed-entity",
        "shared": "shared-entity",
        "foreign": "foreign-entity",
        "foreign_edge_ok": "foreign-via-local-edge",
        "local_edge_bad": "local-via-foreign-edge",
        "beyond": "beyond-foreign-edge",
    }
    ids = {key: uuid.uuid4() for key in names}
    for key, mids in (
        ("seed", [alpha.id]),
        ("shared", [alpha_two.id, beta.id]),
        ("foreign", [beta.id]),
        ("foreign_edge_ok", [beta.id]),
        ("local_edge_bad", [alpha_two.id]),
        ("beyond", [alpha_two.id]),
    ):
        await session.execute(
            text(
                "INSERT INTO entities (id, name, entity_type, memory_ids) "
                "VALUES (CAST(:id AS uuid), :name, 'tool', CAST(:mids AS uuid[]))"
            ),
            {"id": str(ids[key]), "name": names[key], "mids": [str(m) for m in mids]},
        )
    for src, tgt, rel_type, mids in (
        ("seed", "shared", "USES", [alpha_two.id]),
        ("shared", "foreign", "USES", [beta.id]),
        ("seed", "foreign_edge_ok", "USES", [alpha_two.id]),
        ("seed", "local_edge_bad", "USES", [beta.id]),
        ("local_edge_bad", "beyond", "USES", [alpha_two.id]),
        # Both endpoints are in scope; only the edge is foreign. Nothing in the
        # walk can stop this one — it is the output filter's job alone.
        ("seed", "shared", "DEPENDS_ON", [beta.id]),
    ):
        await session.execute(
            text(
                "INSERT INTO entity_relations "
                "(id, source_entity_id, target_entity_id, rel_type, weight, memory_ids) "
                "VALUES (gen_random_uuid(), CAST(:s AS uuid), CAST(:t AS uuid), "
                ":rel, 0.9, CAST(:mids AS uuid[]))"
            ),
            {
                "s": str(ids[src]), "t": str(ids[tgt]), "rel": rel_type,
                "mids": [str(m) for m in mids],
            },
        )
    await session.flush()
    ids["alpha_memory"] = alpha.id
    ids["alpha_two_memory"] = alpha_two.id
    ids["beta_memory"] = beta.id
    return ids


ALPHA_SCOPE = MemoryFilter(project="alpha", statuses=("active",))


@pytest.mark.asyncio
async def test_scoped_walk_stops_at_the_shared_entity(session):
    ids = await _seed_two_project_graph(session)

    repo = PostgresGraphRepository(session)
    result = await repo.get_neighbors_by_id(
        str(ids["seed"]), max_depth=3, scope=ALPHA_SCOPE,
    )

    names = {n["name"] for n in result["neighbors"]}
    assert names == {"shared-entity"}
    for rel in result["relations"]:
        assert {rel["source"], rel["target"]} <= {"seed-entity", "shared-entity"}


@pytest.mark.asyncio
async def test_scoped_walk_omits_a_foreign_edge_between_local_entities(session):
    """Both endpoints are in scope, so no hop predicate can exclude this edge —
    it survives unless the returned relations are scoped as well."""
    ids = await _seed_two_project_graph(session)

    repo = PostgresGraphRepository(session)
    result = await repo.get_neighbors_by_id(
        str(ids["seed"]), max_depth=3, scope=ALPHA_SCOPE,
    )

    assert [r["type"] for r in result["relations"]] == ["USES"]


@pytest.mark.asyncio
async def test_scoped_walk_blocks_a_foreign_entity_behind_a_local_edge(session):
    """Only the predicate on the *expanded entity* stops this: the edge is
    asserted by an alpha memory, so scoping the relation alone lets it through."""
    ids = await _seed_two_project_graph(session)

    repo = PostgresGraphRepository(session)
    result = await repo.get_neighbors_by_id(
        str(ids["seed"]), max_depth=3, scope=ALPHA_SCOPE,
    )

    assert "foreign-via-local-edge" not in {n["name"] for n in result["neighbors"]}


@pytest.mark.asyncio
async def test_scoped_walk_blocks_a_local_entity_behind_a_foreign_edge(session):
    """Only the predicate on the *traversed relation* stops this: both entities
    are alpha, and the second hop is reached through them, so an unscoped
    recursive term keeps expanding past a beta-only assertion."""
    ids = await _seed_two_project_graph(session)

    repo = PostgresGraphRepository(session)
    names = {
        n["name"]
        for n in (
            await repo.get_neighbors_by_id(
                str(ids["seed"]), max_depth=3, scope=ALPHA_SCOPE,
            )
        )["neighbors"]
    }

    assert "local-via-foreign-edge" not in names
    assert "beyond-foreign-edge" not in names


@pytest.mark.asyncio
async def test_unscoped_walk_does_reach_the_foreign_side(session):
    """The negative control. Without a scope the same walk surfaces every exit,
    so the tests above are measuring the scope and not the fixture."""
    ids = await _seed_two_project_graph(session)

    repo = PostgresGraphRepository(session)
    result = await repo.get_neighbors_by_id(str(ids["seed"]), max_depth=3)

    assert {n["name"] for n in result["neighbors"]} == {
        "shared-entity", "foreign-entity", "foreign-via-local-edge",
        "local-via-foreign-edge", "beyond-foreign-edge",
    }


@pytest.mark.asyncio
async def test_scoped_walk_rejects_a_foreign_seed(session):
    ids = await _seed_two_project_graph(session)

    repo = PostgresGraphRepository(session)
    result = await repo.get_neighbors_by_id(
        str(ids["foreign"]), max_depth=2,
        scope=MemoryFilter(project="alpha", statuses=("active",)),
    )

    assert result == {"entity": None, "neighbors": [], "relations": []}


@pytest.mark.asyncio
async def test_scoped_walk_by_name_scopes_the_seed_too(session):
    ids = await _seed_two_project_graph(session)

    repo = PostgresGraphRepository(session)
    scope = MemoryFilter(project="alpha", statuses=("active",))
    assert (await repo.get_neighbors_by_name("foreign-entity", scope=scope))["entity"] is None

    seeded = await repo.get_neighbors_by_name("seed-entity", max_depth=2, scope=scope)
    assert seeded["entity"]["id"] == str(ids["seed"])
    assert {n["name"] for n in seeded["neighbors"]} == {"shared-entity"}


@pytest.mark.asyncio
async def test_walk_depth_is_capped(session):
    """The hop limit is a real bound, not advice: an unbounded walk on a
    connected graph returns the whole component."""
    ids = await _seed_two_project_graph(session)

    repo = PostgresGraphRepository(session)
    one_hop = await repo.get_neighbors_by_id(str(ids["seed"]), max_depth=1)

    assert {n["name"] for n in one_hop["neighbors"]} == {
        "shared-entity", "foreign-via-local-edge", "local-via-foreign-edge",
    }


@pytest.mark.asyncio
async def test_unscoped_walk_matches_the_one_hop_contract(session):
    """``scope=None``, ``max_depth=1`` is what every existing caller gets, and
    it must still be the incident-edge neighbourhood of the seed."""
    ids = await _seed_two_project_graph(session)

    repo = PostgresGraphRepository(session)
    result = await repo.get_neighbors_by_id(str(ids["shared"]))

    assert {n["name"] for n in result["neighbors"]} == {"seed-entity", "foreign-entity"}
    assert len(result["relations"]) == 3


@pytest.mark.asyncio
async def test_relations_between_scopes_by_asserting_memory(session):
    ids = await _seed_two_project_graph(session)
    assert ids  # fixture seeded

    repo = PostgresGraphRepository(session)
    names = ["seed-entity", "shared-entity", "foreign-entity"]

    unscoped = await repo.get_relations_between(names)
    assert {(r["source"], r["target"]) for r in unscoped} == {
        ("seed-entity", "shared-entity"), ("shared-entity", "foreign-entity"),
    }

    scoped = await repo.get_relations_between(names, scope=ALPHA_SCOPE)
    assert [(r["source"], r["target"]) for r in scoped] == [("seed-entity", "shared-entity")]


@pytest.mark.asyncio
async def test_memory_context_neighbours_stay_in_project(session):
    """The live graph read path. ``shared-entity`` is asserted by a beta memory
    too, so its ``memory_ids`` are a direct route out of the project."""
    ids = await _seed_two_project_graph(session)

    svc = GraphService(session, graph_repo=PostgresGraphRepository(session))
    context = await svc.get_memory_context(str(ids["alpha_two_memory"]))

    neighbour_ids = {n["id"] for n in context["neighbors"]}
    assert str(ids["beta_memory"]) not in neighbour_ids

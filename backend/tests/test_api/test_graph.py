import uuid

import pytest
from sqlalchemy import text

from app.api.deps import get_graph_service
from app.main import app
from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import PostgresVectorRepository
from app.services.embedder_registry import child_table
from app.services.graph import GraphService

pytestmark = pytest.mark.asyncio


async def test_graph_entities_returns_200(client, auth_headers):
    response = await client.get("/api/v1/graph/entities", headers=auth_headers)
    assert response.status_code == 200


# ── T2.68/T2.83: an unconfirmed fingerprint must never silently read empty ──

_MODEL_ID = "graph-unified-model"
_REAL_FINGERPRINT = f"{_MODEL_ID}|4"
_SENTINEL_FINGERPRINT = f"{_MODEL_ID}|0"
# Wrong non-zero dims (T2.83): distinct from both the sentinel and the real
# one. Boot-time registration accepts it (dims > 0) and creates its child
# table, but no real embed will ever populate it.
_WRONG_FINGERPRINT = f"{_MODEL_ID}|8"
_DIMS = 4
_WRONG_DIMS = 8
_VECTOR = [1.0, 0.0, 0.0, 0.0]


class _SentinelLLM:
    """What both read paths receive when the embedding purpose's
    ``dimensions`` is unset (a legal, documented configuration)."""

    def llm_fingerprint(self) -> str:
        return _SENTINEL_FINGERPRINT

    async def chat_completion(self, *args, **kwargs):
        return "stub cluster name"


class _WrongDimsLLM:
    """What both read paths receive under a wrong non-zero ``dimensions``
    config (768 configured, 1024 real — T2.83)."""

    def llm_fingerprint(self) -> str:
        return _WRONG_FINGERPRINT

    async def chat_completion(self, *args, **kwargs):
        return "stub cluster name"


async def _register_real_fingerprint(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": _REAL_FINGERPRINT, "mid": _MODEL_ID, "dims": _DIMS},
    )
    child = child_table("memory_embeddings", _REAL_FINGERPRINT)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({_DIMS}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))


async def _add_memory_with_vector(session) -> uuid.UUID:
    memory_id = uuid.uuid4()
    session.add(Memory(
        id=memory_id, content="graph vector under the real fingerprint", source="test",
        importance=0.5, metadata_={}, project="default", status="active",
        memory_type="decision", is_archived=False,
    ))
    await session.flush()
    child = child_table("memory_embeddings", _REAL_FINGERPRINT)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
        ),
        {"mid": memory_id, "fp": _REAL_FINGERPRINT, "vec": str(_VECTOR), "payload": '{"content": "x"}'},
    )
    await session.flush()
    return memory_id


async def _register_wrong_fingerprint_empty(session) -> None:
    """What boot-time registration does under a wrong non-zero ``dimensions``:
    create the ``embedders`` row and the child table, but populate nothing."""
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": _WRONG_FINGERPRINT, "mid": _MODEL_ID, "dims": _WRONG_DIMS},
    )
    child = child_table("memory_embeddings", _WRONG_FINGERPRINT)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({_WRONG_DIMS}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))


def _make_service(session, llm=None) -> GraphService:
    return GraphService(
        session,
        vector_repo=PostgresVectorRepository(session),
        graph_repo=PostgresGraphRepository(session),
        llm=llm if llm is not None else _SentinelLLM(),
    )


async def test_unified_graph_reports_the_sentinel_instead_of_a_quiet_empty_result(session):
    """Nothing is registered for this model: there is no partition to read at
    all. Silently returning ``memories: []`` would be indistinguishable from a
    corpus with no vectors — the response must say so instead."""
    service = _make_service(session)

    result = await service.get_unified_graph()

    assert result["memories"] == []
    assert result["fingerprint_unresolved"] is True


async def test_unified_graph_finds_the_real_partition_behind_the_sentinel(session):
    """Dimensions cleared after a real embed already registered the model:
    the sentinel must resolve to the fingerprint holding the real data."""
    await _register_real_fingerprint(session)
    memory_id = await _add_memory_with_vector(session)
    service = _make_service(session)

    result = await service.get_unified_graph()

    assert result["fingerprint_unresolved"] is False
    assert [m["id"] for m in result["memories"]] == [str(memory_id)]


async def test_unified_graph_finds_the_real_partition_behind_a_wrong_nonzero_dims(session):
    """T2.83: 768 configured, 1024 real. Boot already created the empty
    ``model|8`` partition (a positive dims passes registration's only check),
    and real embeds already populated ``model|4`` before the config drifted.
    The vector arm must find the real data, not the empty phantom partition
    that happens to carry the configured name."""
    await _register_real_fingerprint(session)
    memory_id = await _add_memory_with_vector(session)
    await _register_wrong_fingerprint_empty(session)
    service = _make_service(session, llm=_WrongDimsLLM())

    result = await service.get_unified_graph()

    assert result["fingerprint_unresolved"] is False
    assert [m["id"] for m in result["memories"]] == [str(memory_id)]


class _SpyGraphService:
    def __init__(self):
        self.kwargs: dict = {}

    async def get_unified_graph(self, **kwargs):
        self.kwargs = kwargs
        return {"memories": [], "total_memories": 0, "memories_truncated": False}


async def test_unified_route_forwards_all_and_the_raised_limit(client, auth_headers):
    spy = _SpyGraphService()
    app.dependency_overrides[get_graph_service] = lambda: spy
    try:
        response = await client.get(
            "/api/v1/graph/unified?all=true&limit=20000", headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_graph_service, None)

    assert response.status_code == 200
    assert spy.kwargs["all_memories"] is True
    assert spy.kwargs["limit"] == 20000


async def test_unified_route_defaults_to_two_hundred_without_all(client, auth_headers):
    spy = _SpyGraphService()
    app.dependency_overrides[get_graph_service] = lambda: spy
    try:
        response = await client.get("/api/v1/graph/unified", headers=auth_headers)
    finally:
        app.dependency_overrides.pop(get_graph_service, None)

    assert response.status_code == 200
    assert spy.kwargs["all_memories"] is False
    assert spy.kwargs["limit"] == 200


async def test_unified_route_refuses_a_limit_past_the_ceiling(client, auth_headers):
    response = await client.get("/api/v1/graph/unified?limit=50001", headers=auth_headers)
    assert response.status_code == 422

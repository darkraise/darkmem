import uuid

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import PostgresVectorRepository
from app.services.embedder_registry import child_table
from app.services.graph import GraphService

pytestmark = pytest.mark.asyncio


async def test_graph_entities_returns_200(client, auth_headers):
    response = await client.get("/api/v1/graph/entities", headers=auth_headers)
    assert response.status_code == 200


# ── T2.68: a fingerprint that can be a sentinel must never silently read empty ──

_MODEL_ID = "graph-unified-model"
_REAL_FINGERPRINT = f"{_MODEL_ID}|4"
_SENTINEL_FINGERPRINT = f"{_MODEL_ID}|0"
_DIMS = 4
_VECTOR = [1.0, 0.0, 0.0, 0.0]


class _SentinelLLM:
    """What both read paths receive when the embedding purpose's
    ``dimensions`` is unset (a legal, documented configuration)."""

    def llm_fingerprint(self) -> str:
        return _SENTINEL_FINGERPRINT

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


def _make_service(session) -> GraphService:
    return GraphService(
        session,
        vector_repo=PostgresVectorRepository(session),
        graph_repo=PostgresGraphRepository(session),
        llm=_SentinelLLM(),
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

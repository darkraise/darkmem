"""Memory nodes of the unified graph carry a bounded preview of their content."""
from __future__ import annotations

import json
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

FINGERPRINT = "graph-preview-embedder|4"
DIMS = 4


class _FakeLLM:
    def llm_fingerprint(self) -> str:
        return FINGERPRINT


async def _seed_partition(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": FINGERPRINT, "mid": FINGERPRINT.split("|")[0], "dims": DIMS},
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


async def _add_memory(session, content: str, vector: list[float]) -> uuid.UUID:
    memory_id = uuid.uuid4()
    session.add(Memory(
        id=memory_id, content=content, source="test", importance=0.5, metadata_={},
        project="preview", status="active", memory_type="fact", is_archived=False,
    ))
    await session.flush()
    await session.execute(
        text(
            f"INSERT INTO {child_table('memory_embeddings', FINGERPRINT)} "
            "(memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
        ),
        {
            "mid": memory_id,
            "fp": FINGERPRINT,
            "vec": str(vector),
            "payload": json.dumps({"content": content, "source": "test", "tags": []}),
        },
    )
    await session.flush()
    return memory_id


@pytest.mark.asyncio
async def test_memory_nodes_carry_a_preview(session, client, auth_headers):
    await _seed_partition(session)
    long_content = "".join(chr(ord("a") + i % 26) for i in range(1000))
    short_content = "s" * 100
    long_id = await _add_memory(session, long_content, [1.0, 0.0, 0.0, 0.0])
    short_id = await _add_memory(session, short_content, [0.0, 1.0, 0.0, 0.0])

    async def _service():
        yield GraphService(
            session,
            PostgresVectorRepository(session),
            PostgresGraphRepository(session),
            _FakeLLM(),
        )

    app.dependency_overrides[get_graph_service] = _service
    try:
        response = await client.get(
            "/api/v1/graph/unified?project=preview", headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_graph_service, None)

    assert response.status_code == 200
    nodes = {m["id"]: m for m in response.json()["memories"]}
    long_node = nodes[str(long_id)]
    assert long_node["content"] == long_content[:280]
    assert long_node["content_truncated"] is True
    short_node = nodes[str(short_id)]
    assert short_node["content"] == short_content
    assert short_node["content_truncated"] is False

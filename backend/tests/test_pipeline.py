import json
import uuid
from unittest.mock import AsyncMock

import httpx
import pytest_asyncio

from app.config import LLMPurposeConfig
from app.repositories.vector import QdrantVectorRepository
from app.repositories.graph import Neo4jGraphRepository
from app.services.llm import LLMOrchestrator
from app.services.pipeline import ProcessingPipeline


def _make_mock_llm():
    """LLM that returns a fixed embedding and extraction."""
    call_count = {"embed": 0, "chat": 0}

    def handler(request: httpx.Request):
        url = str(request.url)
        if "embeddings" in url:
            call_count["embed"] += 1
            return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2, 0.3]}]})
        else:
            call_count["chat"] += 1
            return httpx.Response(200, json={
                "choices": [{"message": {"content": json.dumps({
                    "entities": [{"name": "TestEntity", "type": "concept", "properties": {}}],
                    "relationships": [],
                    "memory_type": "fact",
                    "importance": 0.7,
                })}}]
            })

    config = {k: LLMPurposeConfig(base_url="http://mock", model="test", dimensions=3)
              for k in ["embedding", "extraction", "reasoning", "summarization"]}
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return llm, call_count


async def test_pipeline_process_memory():
    llm, call_count = _make_mock_llm()
    vector_repo = AsyncMock(spec=QdrantVectorRepository)
    graph_repo = AsyncMock(spec=Neo4jGraphRepository)

    pipeline = ProcessingPipeline(llm, vector_repo, graph_repo)
    mid = uuid.uuid4()

    await pipeline.process_memory(
        memory_id=mid, content="Test content", source="test",
        tags=["tag-a"], memory_type=None, created_at="2026-01-01T00:00:00Z",
    )

    assert call_count["embed"] == 1
    assert call_count["chat"] == 1
    vector_repo.upsert.assert_called_once()
    graph_repo.create_entity.assert_called_once_with(
        name="TestEntity", entity_type="concept", properties={}, memory_id=mid,
    )
    await llm.close()


async def test_pipeline_delete_memory():
    llm, _ = _make_mock_llm()
    vector_repo = AsyncMock(spec=QdrantVectorRepository)
    graph_repo = AsyncMock(spec=Neo4jGraphRepository)

    pipeline = ProcessingPipeline(llm, vector_repo, graph_repo)
    mid = uuid.uuid4()

    await pipeline.delete_memory(mid)

    vector_repo.delete.assert_called_once_with(mid)
    graph_repo.delete_by_memory_id.assert_called_once_with(mid)
    await llm.close()

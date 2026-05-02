import pytest
from unittest.mock import AsyncMock

from app.services.llm import LLMOrchestrator


@pytest.mark.asyncio
async def test_embed_batch_chunked_preserves_order():
    llm = LLMOrchestrator.__new__(LLMOrchestrator)
    llm.embed_batch = AsyncMock(side_effect=[
        ([[0.1], [0.2], [0.3]], "test|1"),
        ([[0.4], [0.5]], "test|1"),
    ])

    vectors, fingerprint = await llm.embed_batch_chunked(
        ["a", "b", "c", "d", "e"], chunk_size=3, concurrency=2,
    )

    assert vectors == [[0.1], [0.2], [0.3], [0.4], [0.5]]
    assert fingerprint == "test|1"
    assert llm.embed_batch.await_count == 2


@pytest.mark.asyncio
async def test_embed_batch_chunked_empty():
    llm = LLMOrchestrator.__new__(LLMOrchestrator)
    llm.embed_batch = AsyncMock()
    llm.config = {
        "embedding": type("Cfg", (), {"model": "test", "dimensions": 1})(),
    }

    vectors, fingerprint = await llm.embed_batch_chunked([], chunk_size=10, concurrency=1)

    assert vectors == []
    assert fingerprint == "test|1"
    llm.embed_batch.assert_not_called()


@pytest.mark.asyncio
async def test_embed_batch_chunked_single_chunk():
    llm = LLMOrchestrator.__new__(LLMOrchestrator)
    llm.embed_batch = AsyncMock(return_value=([[0.1], [0.2]], "test|1"))

    vectors, fingerprint = await llm.embed_batch_chunked(
        ["a", "b"], chunk_size=5, concurrency=1,
    )

    assert vectors == [[0.1], [0.2]]
    assert fingerprint == "test|1"
    llm.embed_batch.assert_awaited_once_with(["a", "b"])


@pytest.mark.asyncio
async def test_embed_batch_chunked_rejects_mixed_fingerprints():
    """Active embedder cannot change mid-batch — protect callers from mixed
    vector spaces being persisted under one fingerprint."""
    llm = LLMOrchestrator.__new__(LLMOrchestrator)
    llm.embed_batch = AsyncMock(side_effect=[
        ([[0.1]], "fp_a|1"),
        ([[0.2]], "fp_b|1"),
    ])

    with pytest.raises(RuntimeError, match="mixed fingerprints"):
        await llm.embed_batch_chunked(["a", "b"], chunk_size=1, concurrency=2)

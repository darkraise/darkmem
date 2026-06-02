"""RerankerService must score the real document text.

Hybrid-search fused rows carry their content under ``payload`` (the semantic
side) — there is no top-level ``content`` key. If the reranker reads
``doc["content"]`` it scores empty strings and the LLM relevance signal is
noise, so enabling the reranker silently randomises ranking. These tests pin
that the reranker extracts content from the shapes the search paths actually
produce.
"""
from __future__ import annotations

import json

import httpx

from app.config import LLMPurposeConfig
from app.services.llm import LLMOrchestrator
from app.services.reranker import RerankerService


def _make_reranker(keyword: str) -> RerankerService:
    """Fake LLM that scores 9 when ``keyword`` is in the Document section, else 1."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        document = body["messages"][-1]["content"].split("Document:", 1)[-1]
        score = 9 if keyword in document else 1
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"score": score})}}]},
        )

    config = {
        "reasoning": LLMPurposeConfig(base_url="http://mock", model="test"),
        "reranker": LLMPurposeConfig(base_url="http://mock", model="test"),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return RerankerService(llm)


async def test_rerank_reads_content_from_hybrid_payload():
    svc = _make_reranker(keyword="postgres")
    # The matching doc is second, so a correct rerank must REORDER it to first.
    docs = [
        {"memory_id": "b", "payload": {"content": "totally unrelated note"}, "rrf_score": 0.2},
        {"memory_id": "a", "payload": {"content": "darkmem stores vectors in postgres"}, "rrf_score": 0.1},
    ]
    reranked = await svc.rerank("postgres", docs, top_k=2)
    assert reranked[0]["memory_id"] == "a"


async def test_rerank_reads_chunk_content_for_code_rows():
    svc = _make_reranker(keyword="parse_config")
    docs = [
        {"id": "b", "chunk_content": "def unrelated(): pass"},
        {"id": "a", "chunk_content": "def parse_config(): ..."},
    ]
    reranked = await svc.rerank("parse_config", docs, top_k=2)
    assert reranked[0]["id"] == "a"

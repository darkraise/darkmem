"""Reranker must bound its per-document LLM calls.

It fired one LLM call per fused document over the inflated over-fetch candidate
set (~70) at concurrency 3 — seconds of added latency per search. Cap scoring to
the top-N RRF candidates (the tail is lowest-ranked anyway) while still
returning the full candidate set so downstream filtering isn't starved.
"""
from __future__ import annotations

import json

import httpx

from app.config import LLMPurposeConfig
from app.services.llm import LLMOrchestrator
from app.services.reranker import RerankerService


def _counting_reranker():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps({"score": 5})}}]}
        )

    config = {
        "reasoning": LLMPurposeConfig(base_url="http://mock", model="m"),
        "reranker": LLMPurposeConfig(base_url="http://mock", model="m"),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return RerankerService(llm), calls


async def test_rerank_caps_llm_calls_at_max_candidates():
    svc, calls = _counting_reranker()
    docs = [
        {"memory_id": str(i), "payload": {"content": f"doc {i}"}, "rrf_score": 1.0 / (i + 1)}
        for i in range(100)
    ]
    out = await svc.rerank("q", docs, top_k=100, max_candidates=10)
    assert calls["n"] == 10            # only the top-10 RRF candidates are scored
    assert len(out) == 100             # full candidate set preserved for filtering

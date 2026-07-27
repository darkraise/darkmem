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


# ── T1.32 Ruling 4: the unscored tail past rank 40 must never re-order ──

_TAIL_ORDER = (
    "t17", "t03", "t09", "t20", "t01", "t14", "t06", "t19", "t02", "t11",
    "t08", "t15", "t04", "t18", "t07", "t13", "t10", "t16", "t05", "t12",
)


def _rows_with_scored_head_and_shuffled_tail(head_count: int = 40) -> list[dict]:
    """More than ``head_count`` rows, none matching the fake LLM's keyword.

    The head is in plain descending RRF order like a real fused result. The
    tail is deliberately *not* sorted by id, by rrf_score, or by any other
    obvious key — a fixture of 40-or-fewer rows, or a tail sorted the same
    way the head is, could pass even if a bug re-ordered the tail, because
    the "wrong" order would look identical to the right one. This shape
    guarantees any re-ordering (by rerank_score, by id, or by rrf_score)
    produces a detectably different sequence.
    """
    head = [
        {"memory_id": f"h{i}", "payload": {"content": f"head row {i}"}, "rrf_score": 1.0 - i * 0.01}
        for i in range(head_count)
    ]
    tail = [
        {
            "memory_id": tid,
            "payload": {"content": f"tail row {tid}"},
            # Non-monotonic on purpose: neither ascending nor descending,
            # and disagreeing with the id order above.
            "rrf_score": 0.1 + (hash(tid) % 7) * 0.001,
        }
        for tid in _TAIL_ORDER
    ]
    return head + tail


async def test_unscored_tail_past_rank_40_keeps_its_rrf_order():
    svc = _make_reranker(keyword="never-matches-anything-in-these-documents")
    rows = _rows_with_scored_head_and_shuffled_tail(head_count=40)
    tail_before = rows[40:]
    assert len(tail_before) == len(_TAIL_ORDER) > 0

    reranked = await svc.rerank("q", rows, top_k=len(rows), max_candidates=40)

    assert len(reranked) == len(rows)
    tail_after = reranked[40:]
    # Byte-for-byte: same rows, same order, same objects — not merely an
    # order that happens to look plausible.
    assert [d["memory_id"] for d in tail_after] == [d["memory_id"] for d in tail_before]
    assert [id(d) for d in tail_after] == [id(d) for d in tail_before]


async def test_unscored_tail_is_appended_after_the_scored_head_reorders():
    # Prove the head really did move (the matching doc starts mid-head) so
    # the tail-order assertion above is checking something the reranker
    # actually did, not a no-op call.
    svc = _make_reranker(keyword="the-matching-keyword")
    rows = _rows_with_scored_head_and_shuffled_tail(head_count=40)
    rows[20]["payload"]["content"] = "this row has the-matching-keyword in it"

    reranked = await svc.rerank("q", rows, top_k=len(rows), max_candidates=40)

    assert reranked[0]["memory_id"] == "h20"
    assert [d["memory_id"] for d in reranked[40:]] == list(_TAIL_ORDER)

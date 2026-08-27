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
import pytest

from app.config import LLMPurposeConfig
from app.services.llm import LLMOrchestrator
from app.services.reranker import RERANK_FAILURE_SENTINEL, RerankerService, _resolve_document_text


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


# ── T2.69: the producer's text contract, and the ask-vs-failed sentinel ──


def _always_200(score: int = 5):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps({"score": score})}}]},
        )
    return handler


def _make_reranker_with_handler(handler) -> RerankerService:
    config = {
        "reasoning": LLMPurposeConfig(base_url="http://mock", model="test"),
        "reranker": LLMPurposeConfig(base_url="http://mock", model="test"),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return RerankerService(llm)


def test_resolve_document_text_reads_the_closed_set_of_known_shapes():
    assert _resolve_document_text({"content": "x"}, "content") == "x"
    assert _resolve_document_text({"payload": {"content": "y"}}, "content") == "y"
    assert _resolve_document_text({"chunk_content": "z"}, "content") == "z"
    assert _resolve_document_text({"payload": {"chunk_content": "w"}}, "content") == "w"


def test_resolve_document_text_raises_on_an_unresolvable_document():
    """A ``knowledge_triples`` row's text lives under ``fact`` — none of the
    reranker's declared fields reach it. On unmodified code (pre-T2.69) this
    silently fell through to "" and scored a real number against an empty
    document; the fixed contract refuses instead."""
    fact_row = {"fact": "postgres stores vectors", "subject_name": "postgres"}
    with pytest.raises(ValueError):
        _resolve_document_text(fact_row, "content")


async def test_an_unresolvable_document_refuses_the_whole_rerank_call_loudly():
    """R3: drive a knowledge_triples-shaped row through rerank() itself (not
    just the resolver) and show the *service* refuses it — never a scored
    row, and not silently swallowed into the "reranker failed, return
    original order" degradation path either."""
    svc = _make_reranker_with_handler(_always_200())
    docs = [
        {"memory_id": "a", "payload": {"content": "a real memory"}},
        {"memory_id": "b", "fact": "a fact with no declared text field"},
    ]
    with pytest.raises(ValueError):
        await svc.rerank("q", docs, top_k=2)


async def test_a_single_failed_document_is_distinguishable_from_a_genuine_low_score():
    """One document's LLM call errors (a 500); the rest score normally. The
    failed document must not collapse into the same 0.0 a genuine worst-rated
    document gets, and the window must report how many documents failed."""
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        document = body["messages"][-1]["content"]
        if "BAD-DOC" in document:
            return httpx.Response(500, text="upstream error")
        score = 0 if "WORST-DOC" in document else 7
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps({"score": score})}}]},
        )

    svc = _make_reranker_with_handler(handler)
    docs = [
        {"memory_id": "good", "payload": {"content": "GOOD-DOC relevant text"}},
        {"memory_id": "worst", "payload": {"content": "WORST-DOC irrelevant text"}},
        {"memory_id": "failed", "payload": {"content": "BAD-DOC text"}},
    ]

    reranked = await svc.rerank("q", docs, top_k=3)
    by_id = {d["memory_id"]: d for d in reranked}

    assert by_id["failed"]["rerank_failed"] is True
    assert by_id["failed"]["rerank_score"] == RERANK_FAILURE_SENTINEL
    assert by_id["worst"]["rerank_failed"] is False
    assert by_id["worst"]["rerank_score"] == 0.0
    assert by_id["good"]["rerank_failed"] is False
    assert by_id["good"]["rerank_score"] > 0.0

    # Countable within the window, not just visible on one row.
    assert sum(1 for d in reranked if d["rerank_failed"]) == 1

    # R4: the failed document must never rank above (or tie-interleave with)
    # a document the model genuinely rated worst — "asked and failed" carries
    # less information than "asked and rated 0", so it sorts strictly below.
    assert [d["memory_id"] for d in reranked] == ["good", "worst", "failed"]


async def test_a_total_outage_still_reports_all_zero_for_the_all_zero_guard():
    """Every document in the window fails to score. T2.43's downstream
    all-zero guard (``layer_composition.derive_rerank_scores``) depends on
    every ``rerank_score`` reading exactly 0.0 in this case to recognise "no
    usable signal" — that numeric shape must survive unchanged; only the new
    ``rerank_failed`` flag is additive."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="upstream down")

    svc = _make_reranker_with_handler(handler)
    docs = [
        {"memory_id": "a", "payload": {"content": "doc a"}},
        {"memory_id": "b", "payload": {"content": "doc b"}},
    ]

    reranked = await svc.rerank("q", docs, top_k=2)

    assert all(d["rerank_score"] == 0.0 for d in reranked)
    assert all(d["rerank_failed"] is True for d in reranked)


async def test_a_response_missing_the_score_key_counts_as_a_failure():
    """A JSON-valid response with the wrong key is a failure, not a zero.

    ``parsed.get("score", 0)`` turns a well-formed body that happens to name
    its field ``rating`` into a real 0.0 — indistinguishable from a genuine
    worst rating, and carrying ``rerank_failed=False``, so none of the
    failure machinery above ever sees it.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        document = body["messages"][-1]["content"]
        if "WRONG-KEY" in document:
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": json.dumps({"rating": 7})}}]},
            )
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps({"score": 7})}}]},
        )

    svc = _make_reranker_with_handler(handler)
    docs = [
        {"memory_id": "ok", "payload": {"content": "normal text"}},
        {"memory_id": "wrong", "payload": {"content": "WRONG-KEY text"}},
    ]

    reranked = await svc.rerank("q", docs, top_k=2)
    by_id = {d["memory_id"]: d for d in reranked}

    assert by_id["wrong"]["rerank_failed"] is True
    assert by_id["wrong"]["rerank_score"] == RERANK_FAILURE_SENTINEL
    assert by_id["ok"]["rerank_failed"] is False

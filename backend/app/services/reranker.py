"""Cross-encoder reranker for refining search results via Ollama LLM scoring."""

from __future__ import annotations

import asyncio
import json
import logging

from app.services.llm import LLMOrchestrator

logger = logging.getLogger(__name__)

_RERANK_PROMPT = """Rate the relevance of the following document to the query on a scale of 0 to 10.
Return ONLY a JSON object: {{"score": <number>}}

Query: {query}

Document: {document}"""


class RerankerService:
    def __init__(self, llm: LLMOrchestrator):
        self.llm = llm

    async def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 10,
        content_key: str = "content",
        max_candidates: int = 40,
    ) -> list[dict]:
        """Re-score documents by asking the LLM to rate query-document relevance.

        Uses the reasoning LLM purpose to score each document 0-10. Only the top
        ``max_candidates`` (the input arrives RRF-ranked, so the tail is the
        lowest-ranked) are scored via the LLM, bounding per-search LLM calls; the
        unscored tail is appended in its incoming order so downstream filtering
        still sees the full candidate set. Falls back to original ordering if
        scoring fails.
        """
        if not documents:
            return []

        head = documents[:max_candidates]
        tail = documents[max_candidates:]

        try:
            sem = asyncio.Semaphore(8)

            async def _score_one(doc: dict) -> float:
                # Hybrid-search fused rows keep their content under ``payload``
                # (the semantic side stores the upserted payload dict); there is
                # no top-level ``content`` key. Fall through the shapes the
                # search paths actually emit so the LLM scores real text, not "".
                payload = doc.get("payload") or {}
                text = (
                    doc.get(content_key)
                    or payload.get("content")
                    or doc.get("chunk_content")
                    or payload.get("chunk_content")
                    or ""
                )
                prompt = _RERANK_PROMPT.format(query=query, document=text[:1000])
                try:
                    response = await self.llm.chat_completion(
                        "reranker",
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"},
                    )
                    parsed = json.loads(response)
                    return float(parsed.get("score", 0))
                except Exception:
                    return 0.0

            async def _score_with_limit(doc: dict) -> float:
                async with sem:
                    return await _score_one(doc)

            scores = await asyncio.gather(*[_score_with_limit(doc) for doc in head])

            max_score = max(scores) if scores else 1.0
            normalizer = max_score if max_score > 0 else 1.0

            for i, doc in enumerate(head):
                doc["rerank_score"] = scores[i] / normalizer

            reranked_head = sorted(head, key=lambda d: d.get("rerank_score", 0), reverse=True)
            for doc in tail:
                doc.setdefault("rerank_score", 0.0)
            return (reranked_head + tail)[:top_k]

        except Exception as e:
            logger.warning("Reranker failed, returning original order: %s", e)
            for doc in documents:
                doc["rerank_score"] = 0.0
            return documents[:top_k]

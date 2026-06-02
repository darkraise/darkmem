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
    ) -> list[dict]:
        """Re-score documents by asking the LLM to rate query-document relevance.

        Uses the reasoning LLM purpose to score each document 0-10.
        Falls back to original ordering if scoring fails.
        """
        if not documents:
            return []

        try:
            sem = asyncio.Semaphore(3)

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

            scores = await asyncio.gather(*[_score_with_limit(doc) for doc in documents])

            max_score = max(scores) if scores else 1.0
            normalizer = max_score if max_score > 0 else 1.0

            for i, doc in enumerate(documents):
                doc["rerank_score"] = scores[i] / normalizer

            reranked = sorted(documents, key=lambda d: d.get("rerank_score", 0), reverse=True)
            return reranked[:top_k]

        except Exception as e:
            logger.warning("Reranker failed, returning original order: %s", e)
            for doc in documents:
                doc["rerank_score"] = 0.0
            return documents[:top_k]

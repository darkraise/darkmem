"""Hybrid search combining pgvector semantic similarity with BM25 full-text search via RRF."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import LLMOrchestrator

logger = logging.getLogger(__name__)

RRF_K = 60


class HybridSearchService:
    def __init__(self, llm: LLMOrchestrator, session: AsyncSession, embedding_dims: int = 1024):
        self.llm = llm
        self.session = session
        self.embedding_dims = embedding_dims

    async def search(
        self,
        query: str,
        limit: int = 20,
        semantic_weight: float = 0.7,
    ) -> list[dict]:
        fetch_n = limit * 3
        vector = await self.llm.embed(query)

        try:
            semantic_results = await self._semantic_search(vector, fetch_n)
        except Exception as e:
            logger.error("Semantic search failed: %s", e)
            semantic_results = []

        try:
            keyword_results = await self._keyword_search(query, fetch_n)
        except Exception as e:
            logger.error("Keyword search failed: %s", e)
            keyword_results = []

        return self._rrf_fuse(semantic_results, keyword_results, semantic_weight, limit)

    async def search_code(
        self,
        query: str,
        limit: int = 20,
        repo_id: UUID | None = None,
        language: str | None = None,
        semantic_weight: float = 0.7,
    ) -> list[dict]:
        fetch_n = limit * 3
        vector = await self.llm.embed(query)

        try:
            semantic_results = await self._semantic_code_search(vector, fetch_n, repo_id, language)
        except Exception as e:
            logger.error("Semantic code search failed: %s", e)
            semantic_results = []

        try:
            keyword_results = await self._keyword_code_search(query, fetch_n, repo_id, language)
        except Exception as e:
            logger.error("Keyword code search failed: %s", e)
            keyword_results = []

        return self._rrf_fuse(semantic_results, keyword_results, semantic_weight, limit)

    async def _semantic_search(self, vector: list[float], limit: int) -> list[dict]:
        result = await self.session.execute(
            text("""
                SELECT memory_id,
                       1 - (embedding <=> CAST(:vec AS vector)) AS score,
                       payload
                FROM memory_embeddings
                ORDER BY embedding <=> CAST(:vec AS vector)
                LIMIT :limit
            """),
            {"vec": str(vector), "limit": limit},
        )
        return [
            {"memory_id": str(row.memory_id), "score": float(row.score), "payload": row.payload, "source": "semantic"}
            for row in result
        ]

    async def _keyword_search(self, query: str, limit: int) -> list[dict]:
        result = await self.session.execute(
            text("""
                SELECT m.id AS memory_id,
                       ts_rank(m.search_vector, plainto_tsquery('english', :q)) AS rank,
                       m.content
                FROM memories m
                WHERE m.search_vector @@ plainto_tsquery('english', :q)
                ORDER BY rank DESC
                LIMIT :limit
            """),
            {"q": query, "limit": limit},
        )
        return [
            {
                "memory_id": str(row.memory_id),
                "score": float(row.rank),
                "payload": {"content": row.content},
                "source": "keyword",
            }
            for row in result
        ]

    async def _semantic_code_search(
        self, vector: list[float], limit: int, repo_id: UUID | None, language: str | None,
    ) -> list[dict]:
        filters = ""
        params: dict = {"vec": str(vector), "limit": limit}
        if repo_id is not None:
            filters += " AND repo_id = :repo_id"
            params["repo_id"] = repo_id
        if language is not None:
            filters += " AND language = :language"
            params["language"] = language

        result = await self.session.execute(
            text(f"""
                SELECT id, repo_id, file_path, symbol_name, chunk_content,
                       line_start, line_end,
                       1 - (embedding <=> CAST(:vec AS vector)) AS score
                FROM code_chunk_embeddings
                WHERE TRUE {filters}
                ORDER BY embedding <=> CAST(:vec AS vector)
                LIMIT :limit
            """),
            params,
        )
        return [
            {
                "id": str(row.id), "repo_id": str(row.repo_id),
                "file_path": row.file_path, "symbol_name": row.symbol_name,
                "chunk_content": row.chunk_content,
                "line_start": row.line_start, "line_end": row.line_end,
                "score": float(row.score), "source": "semantic",
            }
            for row in result
        ]

    async def _keyword_code_search(
        self, query: str, limit: int, repo_id: UUID | None, language: str | None,
    ) -> list[dict]:
        filters = ""
        params: dict = {"q": query, "limit": limit}
        if repo_id is not None:
            filters += " AND repo_id = :repo_id"
            params["repo_id"] = repo_id
        if language is not None:
            filters += " AND language = :language"
            params["language"] = language

        result = await self.session.execute(
            text(f"""
                SELECT id, repo_id, file_path, symbol_name, chunk_content,
                       line_start, line_end,
                       ts_rank(search_vector, plainto_tsquery('english', :q)) AS rank
                FROM code_chunk_embeddings
                WHERE search_vector @@ plainto_tsquery('english', :q) {filters}
                ORDER BY rank DESC
                LIMIT :limit
            """),
            params,
        )
        return [
            {
                "id": str(row.id), "repo_id": str(row.repo_id),
                "file_path": row.file_path, "symbol_name": row.symbol_name,
                "chunk_content": row.chunk_content,
                "line_start": row.line_start, "line_end": row.line_end,
                "score": float(row.rank), "source": "keyword",
            }
            for row in result
        ]

    @staticmethod
    def _rrf_fuse(
        semantic_results: list[dict],
        keyword_results: list[dict],
        semantic_weight: float,
        limit: int,
    ) -> list[dict]:
        keyword_weight = 1.0 - semantic_weight
        fused: dict[str, dict] = {}

        for rank, item in enumerate(semantic_results, start=1):
            item_id = item.get("memory_id") or item.get("id")
            if item_id is None:
                continue
            rrf_score = semantic_weight / (RRF_K + rank)
            if item_id in fused:
                fused[item_id]["rrf_score"] += rrf_score
            else:
                entry = dict(item)
                entry["rrf_score"] = rrf_score
                entry.pop("source", None)
                fused[item_id] = entry

        for rank, item in enumerate(keyword_results, start=1):
            item_id = item.get("memory_id") or item.get("id")
            if item_id is None:
                continue
            rrf_score = keyword_weight / (RRF_K + rank)
            if item_id in fused:
                fused[item_id]["rrf_score"] += rrf_score
            else:
                entry = dict(item)
                entry["rrf_score"] = rrf_score
                entry.pop("source", None)
                fused[item_id] = entry

        sorted_results = sorted(fused.values(), key=lambda x: x["rrf_score"], reverse=True)
        return sorted_results[:limit]

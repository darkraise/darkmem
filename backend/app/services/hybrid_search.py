"""Hybrid search combining pgvector semantic similarity with BM25 full-text search via RRF."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.vector import SEMANTIC_FETCH_MULTIPLIER, MemoryFilter
from app.services.embedder_registry import child_table
from app.services.llm import LLMOrchestrator

logger = logging.getLogger(__name__)

RRF_K = 60


class HybridSearchService:
    def __init__(self, llm: LLMOrchestrator, session: AsyncSession):
        self.llm = llm
        self.session = session

    async def search(
        self,
        query: str,
        limit: int = 20,
        semantic_weight: float = 0.7,
        filters: MemoryFilter | None = None,
    ) -> list[dict]:
        fetch_n = limit * SEMANTIC_FETCH_MULTIPLIER
        vector, fingerprint = await self.llm.embed(query)

        semantic_failed = False
        keyword_failed = False

        try:
            semantic_results = await self._semantic_search(vector, fingerprint, fetch_n, filters)
        except Exception as e:
            logger.error("Semantic search failed: %s", e)
            semantic_results = []
            semantic_failed = True

        try:
            keyword_results = await self._keyword_search(query, fetch_n, filters)
        except Exception as e:
            logger.error("Keyword search failed: %s", e)
            keyword_results = []
            keyword_failed = True

        # A one-sided failure degrades gracefully to the other modality, but if
        # BOTH errored, an empty list is indistinguishable from a genuine
        # no-match — raise so the outage is loud instead of silently masked.
        if semantic_failed and keyword_failed:
            raise RuntimeError("Hybrid search failed on both semantic and keyword sides")

        return self._rrf_fuse(semantic_results, keyword_results, semantic_weight, limit)

    async def search_code(
        self,
        query: str,
        limit: int = 20,
        repo_id: UUID | None = None,
        language: str | None = None,
        semantic_weight: float = 0.7,  # noqa: ARG002 — kept for call-site stability
    ) -> list[dict]:
        # Code search is semantic-only. The per-fingerprint
        # ``code_chunk_embeddings__<slug>`` child tables carry the embedding
        # but no FTS column, so there is no keyword side to fuse with.
        vector, fingerprint = await self.llm.embed(query)
        try:
            return await self._semantic_code_search(
                vector, fingerprint, limit, repo_id, language,
            )
        except Exception as e:
            logger.error("Semantic code search failed: %s", e)
            return []

    async def _semantic_search(
        self,
        vector: list[float],
        fingerprint: str,
        limit: int,
        filters: MemoryFilter | None = None,
    ) -> list[dict]:
        table = child_table("memory_embeddings", fingerprint)
        params: dict = {"vec": str(vector), "limit": limit}
        join_sql = ""
        where_sql = ""
        if filters is not None:
            params.update(filters.params())
            join_sql = "JOIN memories m ON m.id = e.memory_id"
            where_sql = f"WHERE {filters.where_sql('m')}"

        result = await self.session.execute(
            text(f"""
                SELECT e.memory_id,
                       1 - (e.embedding <=> CAST(:vec AS vector)) AS score,
                       e.payload
                FROM {table} e
                {join_sql}
                {where_sql}
                ORDER BY e.embedding <=> CAST(:vec AS vector)
                LIMIT :limit
            """),
            params,
        )
        return [
            {"memory_id": str(row.memory_id), "score": float(row.score), "payload": row.payload, "source": "semantic"}
            for row in result
        ]

    def keyword_query(
        self,
        query: str,
        limit: int,
        filters: MemoryFilter | None = None,
    ) -> tuple[str, dict]:
        """The keyword statement and its bound parameters.

        Exposed so the query plan can be measured against the statement the
        channel actually runs, rather than against a transcription of it.
        """
        params: dict = {"q": query, "limit": limit}
        scope_sql = ""
        if filters is not None:
            params.update(filters.params())
            scope_sql = f"AND {filters.where_sql('m')}"

        sql = f"""
                SELECT m.id AS memory_id,
                       ts_rank(m.search_vector, plainto_tsquery('english', :q)) AS rank,
                       m.content
                FROM memories m
                WHERE m.search_vector @@ plainto_tsquery('english', :q)
                  {scope_sql}
                ORDER BY rank DESC
                LIMIT :limit
        """
        return sql, params

    async def _keyword_search(
        self,
        query: str,
        limit: int,
        filters: MemoryFilter | None = None,
    ) -> list[dict]:
        sql, params = self.keyword_query(query, limit, filters)
        result = await self.session.execute(text(sql), params)
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
        self,
        vector: list[float],
        fingerprint: str,
        limit: int,
        repo_id: UUID | None,
        language: str | None,
    ) -> list[dict]:
        table = child_table("code_chunk_embeddings", fingerprint)
        filters = ""
        params: dict = {"vec": str(vector), "limit": limit}
        if repo_id is not None:
            filters += " AND repo_id = CAST(:repo_id AS uuid)"
            params["repo_id"] = str(repo_id)
        if language is not None:
            filters += " AND language = :language"
            params["language"] = language
        if filters:
            params["limit"] = limit * SEMANTIC_FETCH_MULTIPLIER

        result = await self.session.execute(
            text(f"""
                SELECT id, repo_id, file_path, symbol_name, chunk_content,
                       line_start, line_end,
                       1 - (embedding <=> CAST(:vec AS vector)) AS score
                FROM {table}
                WHERE TRUE {filters}
                ORDER BY embedding <=> CAST(:vec AS vector)
                LIMIT :limit
            """),
            params,
        )
        rows = [
            {
                "id": str(row.id), "repo_id": str(row.repo_id),
                "file_path": row.file_path, "symbol_name": row.symbol_name,
                "chunk_content": row.chunk_content,
                "line_start": row.line_start, "line_end": row.line_end,
                "score": float(row.score), "source": "semantic",
            }
            for row in result
        ]
        return rows[:limit]

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

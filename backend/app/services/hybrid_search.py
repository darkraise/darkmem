"""Hybrid search combining pgvector semantic similarity with BM25 full-text search via RRF."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.vector import SEMANTIC_FETCH_MULTIPLIER, MemoryFilter
from app.services.access_stats import spawn_record_access
from app.services.embedder_registry import child_table
from app.services.llm import LLMOrchestrator
from app.services.rank_fusion import RRF_K, RankedList, normalize_row_id, rrf_fuse
from app.utils.scope_labels import SCOPE_LABEL_COLUMNS, SCOPE_LABEL_JOIN, scope_labels

logger = logging.getLogger(__name__)

__all__ = ["RRF_K", "ChannelTrace", "HybridSearchService"]


@dataclass(frozen=True)
class ChannelTrace:
    """The fused rows plus what each channel contributed before fusion.

    Built only by :meth:`HybridSearchService.search_with_trace` — the plain
    ``search`` path never constructs one, so a caller that does not ask for a
    trace never pays for this bookkeeping (doc 07 §8, T1.33).
    """

    results: list[dict]
    channel_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    semantic_failed: bool = False
    keyword_failed: bool = False


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
        semantic_results, keyword_results, _, _ = await self._run_channels(
            query, vector, fingerprint, fetch_n, filters,
        )
        fused = self._rrf_fuse(semantic_results, keyword_results, semantic_weight, limit)
        self._record_access(fused)
        return fused

    async def search_with_trace(
        self,
        query: str,
        limit: int = 20,
        semantic_weight: float = 0.7,
        filters: MemoryFilter | None = None,
    ) -> ChannelTrace:
        """Same channels and fusion as :meth:`search`, plus what each channel
        contributed per row — the input the retrieval trace envelope needs
        (doc 07 §8). Only the caller that wants a trace pays for this; the
        plain ``search`` path above never builds ``channel_scores``.
        """
        fetch_n = limit * SEMANTIC_FETCH_MULTIPLIER
        vector, fingerprint = await self.llm.embed(query)
        semantic_results, keyword_results, semantic_failed, keyword_failed = await self._run_channels(
            query, vector, fingerprint, fetch_n, filters,
        )

        channel_scores: dict[str, dict[str, float]] = {}
        for source_name, rows in (("semantic", semantic_results), ("keyword", keyword_results)):
            for row in rows:
                key = normalize_row_id(row)
                if key is None:
                    continue
                channel_scores.setdefault(key, {})[source_name] = float(row["score"])

        fused = self._rrf_fuse(semantic_results, keyword_results, semantic_weight, limit)
        self._record_access(fused)
        return ChannelTrace(
            results=fused,
            channel_scores=channel_scores,
            semantic_failed=semantic_failed,
            keyword_failed=keyword_failed,
        )

    async def _run_channels(
        self,
        query: str,
        vector: list[float],
        fingerprint: str,
        fetch_n: int,
        filters: MemoryFilter | None,
    ) -> tuple[list[dict], list[dict], bool, bool]:
        semantic_failed = False
        keyword_failed = False

        # Each side runs inside its own SAVEPOINT. Both share one session, and
        # a database-level error aborts the entire transaction, so without one
        # the surviving side's own valid SQL fails on the aborted transaction:
        # a one-sided outage reports as a both-sided one, naming a side that
        # never independently failed, and the caller's session is poisoned for
        # everything it does after the search. The facts channel carries the
        # same idiom (``facts_channel._run_arms``) and they change together.
        try:
            async with self.session.begin_nested():
                semantic_results = await self._semantic_search(
                    vector, fingerprint, fetch_n, filters,
                )
        except Exception as e:
            logger.error("Semantic search failed: %s", e)
            semantic_results = []
            semantic_failed = True

        try:
            async with self.session.begin_nested():
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

        return semantic_results, keyword_results, semantic_failed, keyword_failed

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
        where_sql = ""
        if filters is not None:
            params.update(filters.params())
            where_sql = f"WHERE {filters.where_sql('m')}"

        result = await self.session.execute(
            text(f"""
                SELECT e.memory_id,
                       1 - (e.embedding <=> CAST(:vec AS vector)) AS score,
                       e.payload,
                       {SCOPE_LABEL_COLUMNS}
                FROM {table} e
                {SCOPE_LABEL_JOIN}
                {where_sql}
                ORDER BY e.embedding <=> CAST(:vec AS vector)
                LIMIT :limit
            """),
            params,
        )
        return [
            {
                "memory_id": str(row.memory_id),
                "score": float(row.score),
                "payload": row.payload,
                "source": "semantic",
                **scope_labels(row),
            }
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
                       m.content,
                       {SCOPE_LABEL_COLUMNS}
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
                **scope_labels(row),
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
    def _record_access(rows: list[dict]) -> None:
        """Schedule an off-hot-path counter bump for the memories a search
        actually surfaced (T2.29). Never awaited here — see
        ``app.services.access_stats`` for why, and for the failure mode.
        """
        spawn_record_access(row.get("memory_id") for row in rows)

    @staticmethod
    def _rrf_fuse(
        semantic_results: list[dict],
        keyword_results: list[dict],
        semantic_weight: float,
        limit: int,
    ) -> list[dict]:
        """The memory channel's two ranked lists, joined under their weights.

        ``semantic_weight`` splits the memory channel's weight between its
        two sides; it is a list weight inside the fusion and never a
        per-row multiplier. Additional ranked producers join by appending a
        ``RankedList`` here, each with its own config-row weight.
        """
        return rrf_fuse(
            [
                RankedList("semantic", semantic_results, semantic_weight),
                RankedList("keyword", keyword_results, 1.0 - semantic_weight),
            ],
            limit,
        )

"""Hybrid search combining pgvector semantic similarity with BM25 full-text search via RRF."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.vector import MemoryFilter
from app.config import settings
from app.services.access_stats import spawn_record_access
from app.services.embedder_registry import child_table
from app.services.llm import LLMOrchestrator
from app.services.rank_fusion import (
    RRF_K,
    RankedList,
    fusion_fetch_depth,
    heat_signal,
    normalize_row_id,
    recency_signal,
    rrf_fuse,
)
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
        ppr_weight: float = 0.0,
        dual_weight: float = 0.0,
        access_signals: bool = False,
    ) -> list[dict]:
        """The fused rows, ``limit`` of them.

        ``limit`` truncates the fused list and nothing else: both arms are read
        to :func:`fusion_fetch_depth`, which is the same depth for every
        caller. A caller asking for ten rows and a caller asking for sixty
        therefore fuse the same candidate set and the first is a prefix of the
        second — deriving the arm depth from the caller's own limit is what let
        chat and the search surface rank one corpus two ways.

        ``ppr_weight`` defaults to zero, and at zero this method does exactly
        what it did before the graph arm existed: no snapshot read, no PPR run,
        and a fusion over the same two lists. Callers derive it from
        :func:`rank_fusion.ppr_list_weight` rather than reading the flag pair
        themselves.
        """
        fetch_n = fusion_fetch_depth(limit)
        # Owner ruling 2026-09-03: a backup worker is for viewing and
        # backup/restore only, so it must not depend on a third machine being
        # reachable. The semantic arm is SKIPPED rather than attempted and
        # caught -- `llm.embed` sits outside `_run_channels`' one-sided-failure
        # guard, so an unreachable embedder does not degrade to keyword, it
        # raises out of the whole search. Skipping keeps the keyword arm
        # answering and makes the posture a decision rather than an accident.
        if settings.read_only:
            vector, fingerprint = None, None
        else:
            vector, fingerprint = await self.llm.embed(query)
        semantic_results, keyword_results, _, _ = await self._run_channels(
            query, vector, fingerprint, fetch_n, filters,
        )
        ppr_results = await self._ppr_search(
            semantic_results, filters, ppr_weight, fetch_n,
        )
        dual_results = await self._dual_level_search(
            vector, fingerprint, filters, dual_weight, fetch_n,
        )
        fused = self._rrf_fuse(
            semantic_results, keyword_results, semantic_weight, limit,
            ppr_results, ppr_weight, dual_results, dual_weight,
        )
        if access_signals:
            await self._attach_access_signals(fused)
        self._record_access(fused)
        return fused

    async def search_with_trace(
        self,
        query: str,
        limit: int = 20,
        semantic_weight: float = 0.7,
        filters: MemoryFilter | None = None,
        ppr_weight: float = 0.0,
        dual_weight: float = 0.0,
        access_signals: bool = False,
    ) -> ChannelTrace:
        """Same channels and fusion as :meth:`search`, plus what each channel
        contributed per row — the input the retrieval trace envelope needs
        (doc 07 §8). Only the caller that wants a trace pays for this; the
        plain ``search`` path above never builds ``channel_scores``.
        """
        fetch_n = fusion_fetch_depth(limit)
        # Owner ruling 2026-09-03: a backup worker is for viewing and
        # backup/restore only, so it must not depend on a third machine being
        # reachable. The semantic arm is SKIPPED rather than attempted and
        # caught -- `llm.embed` sits outside `_run_channels`' one-sided-failure
        # guard, so an unreachable embedder does not degrade to keyword, it
        # raises out of the whole search. Skipping keeps the keyword arm
        # answering and makes the posture a decision rather than an accident.
        if settings.read_only:
            vector, fingerprint = None, None
        else:
            vector, fingerprint = await self.llm.embed(query)
        semantic_results, keyword_results, semantic_failed, keyword_failed = await self._run_channels(
            query, vector, fingerprint, fetch_n, filters,
        )
        ppr_results = await self._ppr_search(
            semantic_results, filters, ppr_weight, fetch_n,
        )
        dual_results = await self._dual_level_search(
            vector, fingerprint, filters, dual_weight, fetch_n,
        )

        channel_scores: dict[str, dict[str, float]] = {}
        for source_name, rows in (
            ("semantic", semantic_results),
            ("keyword", keyword_results),
            ("ppr", ppr_results),
            ("dual_level", dual_results),
        ):
            for row in rows:
                key = normalize_row_id(row)
                if key is None:
                    continue
                channel_scores.setdefault(key, {})[source_name] = float(row["score"])

        fused = self._rrf_fuse(
            semantic_results, keyword_results, semantic_weight, limit,
            ppr_results, ppr_weight, dual_results, dual_weight,
        )
        if access_signals:
            await self._attach_access_signals(fused)
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
        if vector is None:
            # Not asked, rather than asked and broke -- the distinction
            # `layer_composition` already draws. Under the read-only posture
            # the embedder is deliberately never called, so reporting this arm
            # as *failed* would put an outage in the trace that never happened
            # and would let a keyword-only answer look like a half-broken one.
            semantic_results = []
        else:
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
        ppr_results: list[dict] | None = None,
        ppr_weight: float = 0.0,
        dual_results: list[dict] | None = None,
        dual_weight: float = 0.0,
    ) -> list[dict]:
        """The memory channel's ranked lists, joined under their weights.

        ``semantic_weight`` splits the memory channel's weight between its
        two sides; it is a list weight inside the fusion and never a
        per-row multiplier. Additional ranked producers join by appending a
        ``RankedList`` here, each with its own config-row weight.

        The PPR list is appended only when it carries weight. Appending it at
        weight zero would be arithmetically inert but not *observably* so: a
        row found by PPR alone would enter the fused set with an
        ``rrf_score`` of exactly 0.0 and displace nothing, yet still appear in
        a result page that would not have contained it. Inert has to mean the
        same rows, not merely the same scores.
        """
        lists = [
            RankedList("semantic", semantic_results, semantic_weight),
            RankedList("keyword", keyword_results, 1.0 - semantic_weight),
        ]
        if ppr_results and ppr_weight:
            lists.append(RankedList("ppr", ppr_results, ppr_weight))
        if dual_results and dual_weight:
            lists.append(RankedList("dual_level", dual_results, dual_weight))
        return rrf_fuse(lists, limit)

    async def _dual_level_search(
        self,
        vector: list[float],
        fingerprint: str,
        filters: MemoryFilter | None,
        dual_weight: float,
        fetch_n: int,
    ) -> list[dict]:
        """The dual-level global arm: rank relations, resolve to memories.

        The graph's edges carry meaning no single memory's text does — a query
        about what replaced Redis matches the *edge* `redis REPLACES valkey`
        even when no memory says it that way — which is the whole reason doc 07
        §4 makes this a channel rather than another view of the memory vectors.

        **This is the one channel with no project column of its own** (doc 07
        §11, restated in §4 so no implementer re-opens it). `relation_embeddings`
        keys on `entity_relations`, which is global by design, so the scope
        cannot be pushed into the vector arm. It is re-applied on the
        **asserting memories** instead — the relation's own `memory_ids` joined
        to `memories` and filtered there. Skipping that join returns rows from
        every project that happens to assert a matching edge: a cross-project
        leak that looks like a good result, which is exactly what makes it the
        one exception the pushdown cannot cover with an index.

        Reuses the query vector the memory channel already embedded, so an
        active arm costs one extra SQL round trip and no extra model call.
        """
        if not dual_weight:
            return []
        table = child_table("relation_embeddings", fingerprint)
        params: dict = {
            "vec": str(vector), "fp": fingerprint, "limit": fetch_n,
        }
        where_sql = "TRUE"
        if filters is not None:
            params.update(filters.params())
            where_sql = filters.where_sql("m")

        try:
            async with self.session.begin_nested():
                result = await self.session.execute(
                    text(f"""
                    WITH hits AS (
                        SELECT re.relation_id,
                               1 - (re.embedding <=> CAST(:vec AS vector)) AS score
                        FROM {table} re
                        WHERE re.fingerprint = CAST(:fp AS text)
                        ORDER BY re.embedding <=> CAST(:vec AS vector)
                        LIMIT :limit
                    )
                    SELECT CAST(m.id AS text) AS memory_id, max(h.score) AS score
                    FROM hits h
                    JOIN entity_relations r ON r.id = h.relation_id
                    JOIN LATERAL unnest(r.memory_ids) AS u(mid) ON TRUE
                    JOIN memories m ON m.id = u.mid
                    WHERE {where_sql}
                    GROUP BY m.id
                    ORDER BY score DESC
                    LIMIT :limit
                """),
                    params,
                )
                rows = result.all()
        except Exception as e:
            # An augmentation that fails must cost the fused order nothing —
            # the same stance the PPR arm takes. A cold partition (no relation
            # vectors under this fingerprint yet) lands here as a missing
            # table, which is a not-yet rather than a fault.
            logger.error("Dual-level arm failed: %s", e)
            return []

        return [
            {"memory_id": str(row.memory_id), "score": float(row.score)}
            for row in rows
        ]

    async def _attach_access_signals(self, rows: list[dict]) -> None:
        """Stamp `heat` and `recency` onto the fused rows, in one read.

        **Attached here rather than derived at each door, and that is the whole
        point.** The chat door reads its arm signals off the row
        (`layer_composition._signals` over `SIGNAL_KEYS`), while the search door
        re-reads `memories` for confidence and importance. If heat and recency
        were derived separately at each of them, the two would rank one corpus
        differently the moment either arm was flipped on — the divergence T2.58
        closed for the channel itself, arriving again through the signals. One
        read, on the shared channel, and both doors see the same numbers.

        A memory with no counter row is left without the keys at all, not with
        a zero: `arm_factor` treats an absent signal as exactly 1.0, so a
        never-accessed memory is untouched rather than demoted.
        """
        if not rows:
            return
        ids = []
        for row in rows:
            key = normalize_row_id(row)
            if key:
                ids.append(key)
        if not ids:
            return

        result = await self.session.execute(
            text(
                "SELECT CAST(memory_id AS text), access_count, last_accessed "
                "FROM memory_access_stats "
                "WHERE memory_id = ANY(CAST(:ids AS uuid[]))"
            ),
            {"ids": ids},
        )
        stats = {row[0]: (row[1], row[2]) for row in result}
        if not stats:
            return

        for row in rows:
            key = normalize_row_id(row)
            entry = stats.get(key) if key else None
            if entry is None:
                continue
            heat = heat_signal(entry[0])
            recency = recency_signal(entry[1])
            if heat is not None:
                row["heat"] = heat
            if recency is not None:
                row["recency"] = recency

    async def _ppr_search(
        self,
        semantic_results: list[dict],
        filters: MemoryFilter | None,
        ppr_weight: float,
        fetch_n: int,
    ) -> list[dict]:
        """The graph arm's ranked list, seeded from the semantic hits.

        Returns immediately at weight zero — the import itself is deferred, so
        an install that never turns the arm on never pays for it. The seeds are
        the semantic side's own rows, so this adds no database read: the
        snapshot's entity→memory mapping is already in process (invariant 15),
        and the whole arm is skipped for a wide (project-less) request because
        the snapshot is project-scoped and there is no defined mass across two
        of them.
        """
        if not ppr_weight:
            return []
        project = getattr(filters, "project", None)
        if not project:
            return []
        from app.services.ppr_snapshot import ppr_ranked_list

        try:
            return await ppr_ranked_list(
                project,
                [str(row["memory_id"]) for row in semantic_results],
                limit=fetch_n,
            )
        except Exception as e:
            # An augmentation that fails must cost the fused order nothing;
            # the two base arms already carry their own outage semantics.
            logger.error("PPR arm failed: %s", e)
            return []

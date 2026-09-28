import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import numpy as np
from sqlalchemy import Text, cast, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedder_registry import child_table
from app.utils.scope_labels import SCOPE_LABEL_COLUMNS, SCOPE_LABEL_JOIN, scope_labels

# One server process (invariant 13) means this pass must not hold the event
# loop; one worker keeps peak memory at a single pass's worth.
_KNN_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="graph-knn")


def _cluster_and_edges(
    vectors: np.ndarray, ids: list[str], min_score: float, min_cluster_size: int,
) -> tuple[list[int], list[dict]]:
    from app.utils.graph_knn import CLUSTER_K, cluster_labels, knn_graph, similarity_edges

    graph = knn_graph(vectors, k=CLUSTER_K, threshold=min_score)
    return cluster_labels(graph, len(ids), min_cluster_size), similarity_edges(graph, ids)


# An HNSW scan applies a WHERE as a post-scan filter over the candidate stream
# it produces; it cannot seek on the predicate. Over-fetching by this factor is
# what stops a selective scope from silently under-returning.
SEMANTIC_FETCH_MULTIPLIER = 3


class EmbedderFingerprintUnresolved(RuntimeError):
    """A bulk-partition read would key on a fingerprint no embed ever produced.

    ``LLMOrchestrator.llm_fingerprint()`` is built from static config, never
    from an actual embed, so it can name a partition nothing real ever wrote
    to. Two shapes of that (T2.68, T2.83): ``dimensions`` unset, which yields
    the ``model|0`` sentinel and which boot-time registration refuses to
    create a table for; and ``dimensions`` set to the WRONG positive value,
    which boot registration does NOT refuse — it eagerly creates an empty,
    syntactically valid partition that no real embed will ever populate,
    because ``LLMOrchestrator._check_dims`` rejects any embed whose actual
    length disagrees with the configured one. Both shapes read as an
    apparently-successful, permanently-empty query with no error and no
    symptom unless a read path refuses to trust an unconfirmed fingerprint —
    see :meth:`PostgresVectorRepository.resolve_read_fingerprint`, which
    raises this when the model has no fingerprint, confirmed or not, to fall
    back to.
    """

    def __init__(self, model_id: str):
        self.model_id = model_id
        super().__init__(
            f"No embedding partition holds data for model {model_id!r}: the "
            "embedding purpose's 'dimensions' config may be unset or wrong, "
            "and no real embed call has produced data under any fingerprint "
            "for this model yet. Verify 'dimensions' on the embedding "
            "purpose, or perform an embed "
            "first so the true fingerprint registers."
        )


@dataclass(frozen=True)
class MemoryFilter:
    """Project / status / archived scope for the semantic retrieval channel.

    Rendered into the channel's SQL as a join against ``memories`` rather than
    re-applied in Python: an over-fetch-then-drop filter under-returns whenever
    the scope is selective, and any consumer that forgets the drop leaks
    foreign rows into its results.

    ``None`` (rather than an instance) means no scoping at all — the crossref
    probe wants every candidate regardless of lifecycle, because its output is
    ids and scores rather than content.
    """

    project: str | None = None
    statuses: tuple[str, ...] | None = None
    include_archived: bool = False

    def where_sql(self, alias: str) -> str:
        clauses: list[str] = []
        if not self.include_archived:
            clauses.append(f"{alias}.is_archived = FALSE")
        if self.project is not None:
            clauses.append(f"{alias}.project = CAST(:flt_project AS text)")
        if self.statuses:
            # memories.status is a Postgres enum; comparing as text keeps an
            # unrecognised status a no-match instead of a query-aborting
            # InvalidTextRepresentation.
            clauses.append(f"{alias}.status::text = ANY(CAST(:flt_statuses AS text[]))")
        return " AND ".join(clauses) if clauses else "TRUE"

    def asserted_by_sql(self, memory_ids_expr: str) -> str:
        """Scope a row that carries ``memory_ids`` instead of a ``project``.

        ``entities`` and ``entity_relations`` are not memory-scoped — the only
        project a graph row has is the one its asserting memories carry. A walk
        that scopes its seed but expands through an unscoped predicate steps
        straight over the boundary, so every hop renders this.
        """
        return (
            "EXISTS (SELECT 1 FROM memories flt_m "
            f"WHERE flt_m.id = ANY({memory_ids_expr}) AND {self.where_sql('flt_m')})"
        )

    def orm_criteria(self, model) -> list:
        """The same scope as ``where_sql``, for a caller building a Core/ORM select.

        Kept on the filter rather than open-coded at the call site: a second
        rendering of these predicates is how one arm silently stops applying a
        field the other one gained.
        """
        criteria: list = []
        if not self.include_archived:
            criteria.append(model.is_archived.is_(False))
        if self.project is not None:
            criteria.append(model.project == self.project)
        if self.statuses:
            criteria.append(cast(model.status, Text).in_(list(self.statuses)))
        return criteria

    def params(self) -> dict:
        out: dict = {}
        if self.project is not None:
            out["flt_project"] = self.project
        if self.statuses:
            out["flt_statuses"] = list(self.statuses)
        return out


class PostgresVectorRepository:
    """Per-fingerprint vector access.

    Reads and writes always target the child table that matches the
    fingerprint passed in. The repository never queries across fingerprints.
    """

    def __init__(self, session: AsyncSession, collection_name: str = "memories"):
        self.session = session
        self.collection_name = collection_name

    async def ensure_collection(self):
        pass

    async def upsert(
        self,
        memory_id: UUID,
        vector: list[float],
        payload: dict,
        fingerprint: str,
    ):
        table = child_table("memory_embeddings", fingerprint)
        await self.session.execute(
            text(f"""
                INSERT INTO {table} (memory_id, fingerprint, embedding, payload)
                VALUES (:memory_id, :fp, CAST(:embedding AS vector), CAST(:payload AS jsonb))
                ON CONFLICT (memory_id, fingerprint) DO UPDATE
                    SET embedding = EXCLUDED.embedding,
                        payload = EXCLUDED.payload
            """),
            {
                "memory_id": memory_id,
                "fp": fingerprint,
                "embedding": str(vector),
                "payload": json.dumps(payload),
            },
        )

    async def search(
        self,
        vector: list[float],
        fingerprint: str,
        limit: int = 20,
        filters: MemoryFilter | None = None,
    ) -> list[dict]:
        """One partition's ANN probe, every row labelled with the scope it came from.

        The join to ``memories`` is unconditional even when nothing is being
        scoped — the same shape :meth:`get_all_vectors` uses, and for the same
        reason: the FK makes it lossless, and it is what puts ``project`` and
        ``status`` on every row, so a row reaching a consumer nobody enumerated
        still names where it came from.
        """
        table = child_table("memory_embeddings", fingerprint)
        params: dict = {"vec": str(vector), "limit": limit}
        where_sql = ""
        if filters is not None:
            params["limit"] = limit * SEMANTIC_FETCH_MULTIPLIER
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
        rows = [
            {
                "memory_id": UUID(str(row.memory_id)),
                "score": float(row.score),
                "payload": row.payload,
                **scope_labels(row),
            }
            for row in result
        ]
        return rows[:limit]

    async def delete(self, memory_id: UUID):
        """Delete the memory's embedding from every registered fingerprint table.

        ``ON DELETE CASCADE`` on each child's FK makes this redundant when the
        parent memory row is dropped — and that path is the typical caller.
        Kept so callers cleaning stranded embeddings still work.

        The loop is one round-trip per registered fingerprint. Typical
        deployments have 1-2 fingerprints, so the cost is bounded.
        """
        rows = (
            await self.session.execute(text("SELECT fingerprint FROM embedders"))
        ).scalars().all()
        for fp in rows:
            table = child_table("memory_embeddings", fp)
            await self.session.execute(
                text(f"DELETE FROM {table} WHERE memory_id = :id"),
                {"id": memory_id},
            )

    @staticmethod
    def _parse_vector(raw) -> list[float]:
        if isinstance(raw, str):
            return [float(x) for x in raw.strip("[]").split(",")]
        return [float(x) for x in raw]

    def _bulk_read(
        self, fingerprint: str, limit: int, filters: MemoryFilter | None,
    ) -> tuple[str, dict]:
        """The bulk partition read, newest first.

        A limit keeps the most recent memories rather than an arbitrary slice.
        The embedding is cast to ``real[]`` so asyncpg decodes it natively;
        parsing the text form costs seconds at tens of thousands of rows.
        ``importance`` rides the same row because a lookup by id would pass one
        bind parameter per memory, past asyncpg's limit.

        The join to ``memories`` is unconditional even when nothing is being
        scoped: the FK makes it lossless, and it is what puts ``project`` and
        ``status`` on every point, so an unscoped caller still hands back
        labelled rows rather than anonymous content snippets.
        """
        table = child_table("memory_embeddings", fingerprint)
        params: dict = {"limit": limit}
        where_sql = ""
        if filters is not None:
            params.update(filters.params())
            where_sql = f"WHERE {filters.where_sql('m')}"
        sql = f"""
            SELECT e.memory_id,
                   e.embedding::real[] AS embedding,
                   e.payload,
                   m.importance AS importance,
                   {SCOPE_LABEL_COLUMNS}
            FROM {table} e
            {SCOPE_LABEL_JOIN}
            {where_sql}
            ORDER BY m.created_at DESC, e.memory_id DESC
            LIMIT :limit
        """
        return sql, params

    @staticmethod
    def _bulk_point(row) -> dict:
        return {
            "memory_id": UUID(str(row.memory_id)),
            "payload": row.payload,
            "importance": row.importance,
            **scope_labels(row),
        }

    async def get_all_vectors(
        self, fingerprint: str, limit: int = 500, filters: MemoryFilter | None = None,
    ) -> list[dict]:
        """Bulk read of one partition, for the projection and clustering views."""
        sql, params = self._bulk_read(fingerprint, limit, filters)
        result = await self.session.execute(text(sql), params)
        return [{**self._bulk_point(row), "vector": row.embedding} for row in result]

    async def get_vector_matrix(
        self, fingerprint: str, limit: int = 500, filters: MemoryFilter | None = None,
    ) -> tuple[list[dict], np.ndarray]:
        """``get_all_vectors`` without a Python list per vector.

        Rows stream in batches of 1,000 and each batch's embeddings are packed
        into float32 before the next arrives, so a 20,000 x 1024 read peaks
        near its 80 MB matrix rather than the ~0.65 GB its lists would hold.
        """
        sql, params = self._bulk_read(fingerprint, limit, filters)
        points: list[dict] = []
        blocks: list[np.ndarray] = []
        result = await self.session.stream(text(sql), params)
        async for batch in result.partitions(1000):
            points.extend(self._bulk_point(row) for row in batch)
            blocks.append(np.asarray([row.embedding for row in batch], dtype=np.float32))
        if not blocks:
            return [], np.empty((0, 0), dtype=np.float32)
        return points, np.vstack(blocks)

    async def scope_stamp(
        self, fingerprint: str, filters: MemoryFilter | None = None,
    ) -> tuple[int, datetime | None]:
        """How many rows ``get_all_vectors`` could return under ``filters``,
        and the newest ``memories.updated_at`` among them.

        Together they move whenever the readable set does: a capture or
        re-extraction bumps ``updated_at`` through the ``touch_updated_at``
        trigger, and a delete moves the count.
        """
        table = child_table("memory_embeddings", fingerprint)
        params: dict = {}
        where_sql = ""
        if filters is not None:
            params.update(filters.params())
            where_sql = f"WHERE {filters.where_sql('m')}"

        row = (
            await self.session.execute(
                text(f"""
                    SELECT count(*) AS n, max(m.updated_at) AS last_updated
                    FROM {table} e
                    {SCOPE_LABEL_JOIN}
                    {where_sql}
                """),
                params,
            )
        ).one()
        return int(row.n), row.last_updated

    async def get_clustered_vectors(
        self,
        fingerprint: str,
        eps: float = 0.5,
        min_samples: int = 2,
        limit: int = 300,
        filters: MemoryFilter | None = None,
    ) -> list[dict]:
        from sklearn.cluster import DBSCAN

        points = await self.get_all_vectors(fingerprint, limit=limit, filters=filters)
        if len(points) < 2:
            for p in points:
                p["cluster"] = 0
            return points

        vectors = np.array([p["vector"] for p in points], dtype=np.float32)
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine").fit(vectors)

        for i, p in enumerate(points):
            p["cluster"] = int(clustering.labels_[i])

        return points

    async def get_louvain_clustered_vectors(
        self,
        fingerprint: str,
        min_score: float = 0.5,
        min_cluster_size: int = 3,
        limit: int = 500,
        filters: MemoryFilter | None = None,
    ) -> tuple[list[dict], list[dict]]:
        """Points labelled with a ``cluster``, plus the similarity edges to draw.

        One exact k-nearest-neighbour pass feeds both: Louvain clusters the
        top-``CLUSTER_K`` graph, and the edges are the pairs in either
        endpoint's top ``EDGE_K``. Memory stays O(chunk x N). The pass itself
        runs off the event loop (`_KNN_EXECUTOR`): invariant 13 pins one
        server process, and a pass of several seconds would otherwise stall
        every capture, MCP call, websocket and job for its duration.
        """
        points, vectors = await self.get_vector_matrix(fingerprint, limit=limit, filters=filters)
        if not points:
            return [], []

        ids = [str(p["memory_id"]) for p in points]
        labels, edges = await asyncio.get_running_loop().run_in_executor(
            _KNN_EXECUTOR, _cluster_and_edges, vectors, ids, min_score, min_cluster_size,
        )
        for point, label in zip(points, labels):
            point["cluster"] = label
        return points, edges

    async def resolve_read_fingerprint(self, llm) -> str:
        """Resolve the fingerprint a bulk-partition read (projection, clustering)
        may safely key on.

        ``llm.llm_fingerprint()`` is a pure, session-less formatter built from
        static config, never from an actual embed (T2.68, widened by T2.83): a
        read must never trust it blindly, because it can name a partition no
        real embed ever wrote to. That happens in more than one shape — an
        unset ``dimensions`` (the ``|0`` sentinel, which boot-time
        registration refuses to create a table for at all) and a WRONG
        positive ``dimensions`` (768 configured, 1024 real — which boot
        registration does NOT refuse: it happily creates an empty,
        syntactically valid partition, because ``dims > 0`` passes the only
        check registration runs. No real embed will ever populate it, since
        ``LLMOrchestrator._check_dims`` refuses any embed whose actual length
        disagrees with the configured one — but nothing stops a read from
        finding the empty table and returning zero rows forever, with no
        error at all). Both shapes are one class: "the configured fingerprint
        might not be the one an embed would produce", so this resolves by
        data, not by shape:

        1. If the configured fingerprint's own partition already holds data,
           use it — the fast, overwhelmingly common path.
        2. Otherwise, if a different live fingerprint for the same model
           holds data (dims drifted after real embeds already ran under the
           true one), resolve to that instead, preferring the most recently
           registered.
        3. Otherwise, if the configured fingerprint is at least a live
           registered partition, pass it through: a fresh, correctly
           configured deployment with nothing embedded yet looks identical to
           a wrong one with nothing embedded yet, and only an actual embed
           call could tell them apart — an honestly empty result is not the
           bug this guards against (invariant 14).
        4. Otherwise — the configured fingerprint is not registered at all
           and nothing else for this model holds data either — there is no
           partition to read, and this raises
           :class:`EmbedderFingerprintUnresolved` rather than let the caller
           proceed on a key nothing was ever written under.

        **Data-probe resolution is structurally biased toward whichever
        partition already has content** (T-doc-door.6 review, round 2,
        2026-08-24). A round-1 change here briefly took a ``parent_table``
        parameter so a caller could point the "has data" check at its own
        family's partition instead of always at ``memory_embeddings``. That
        was itself wrong for a *backstop writer*: the fingerprint a sweep
        must target is the one the active embedder produces *right now* —
        exactly the one whose partition for this family is most likely to be
        EMPTY (a fresh rotation, a family with no traffic yet), which is
        precisely the case a data probe, no matter which family it checks,
        prefers to skip in favour of a stale sibling that already has rows.
        No parameterisation of this method can fix a backstop's resolution;
        a job with that shape must resolve its fingerprint from a real embed
        call instead (see ``block_embeddings.resolve_active_fingerprint``),
        the same way retrieval already does. The parameter was reverted with
        that fix, since nothing in the tree needs it once the sweep stopped
        using this method.

        Never used by retrieval — ``hybrid_search`` derives its fingerprint
        from ``embed()``'s return value (an actual vector's length), which
        structurally cannot be wrong, so it has no need of this lookup.
        """
        fingerprint = llm.llm_fingerprint()
        model_id, _, _ = fingerprint.rpartition("|")

        live = (
            await self.session.execute(
                text(
                    "SELECT fingerprint FROM embedders "
                    "WHERE model_id = :model_id AND retired_at IS NULL "
                    "ORDER BY registered_at DESC"
                ),
                {"model_id": model_id},
            )
        ).scalars().all()
        if not live:
            raise EmbedderFingerprintUnresolved(model_id)

        is_registered = fingerprint in live
        # Check the configured fingerprint first (the common case resolves in
        # one query), then every other live sibling, newest first.
        candidates = ([fingerprint] if is_registered else []) + [
            fp for fp in live if fp != fingerprint
        ]
        for candidate in candidates:
            if await self._partition_has_data(candidate):
                return candidate

        if is_registered:
            return fingerprint
        raise EmbedderFingerprintUnresolved(model_id)

    async def _partition_has_data(self, fingerprint: str) -> bool:
        """Whether a live fingerprint's memory partition holds any row.

        ``fingerprint`` must already be a live row in ``embedders`` — its
        registration is what created the table, so no ``to_regclass``
        existence probe is needed here.
        """
        table = child_table("memory_embeddings", fingerprint)
        return bool(
            (
                await self.session.execute(text(f"SELECT EXISTS(SELECT 1 FROM {table} LIMIT 1)"))
            ).scalar_one()
        )

    async def find_fingerprint_for_memory(self, memory_id: UUID) -> str | None:
        """Return a registered fingerprint whose child table holds this memory.

        Vectors live only in per-fingerprint child tables; there is no parent
        ``memory_embeddings`` table to scan. Walk the registry and probe each
        child table (typically 1-2), returning the first match.
        """
        fingerprints = (
            await self.session.execute(text("SELECT fingerprint FROM embedders"))
        ).scalars().all()
        for fp in fingerprints:
            table = child_table("memory_embeddings", fp)
            row = await self.session.execute(
                text(f"SELECT 1 FROM {table} WHERE memory_id = :id LIMIT 1"),
                {"id": memory_id},
            )
            if row.scalar_one_or_none() is not None:
                return fp
        return None

    async def find_similar(
        self,
        memory_id: UUID,
        fingerprint: str,
        threshold: float = 0.9,
        limit: int = 10,
        filters: MemoryFilter | None = None,
    ) -> list[dict]:
        table = child_table("memory_embeddings", fingerprint)
        result = await self.session.execute(
            text(f"""
                SELECT embedding::text AS embedding_text
                FROM {table}
                WHERE memory_id = :memory_id
            """),
            {"memory_id": memory_id},
        )
        row = result.mappings().first()
        if row is None:
            return []
        vector = self._parse_vector(row["embedding_text"])
        results = await self.search(
            vector, fingerprint=fingerprint, limit=limit + 1, filters=filters,
        )
        # Slice back to ``limit``: the +1 over-fetch only leaves room to drop the
        # source row, but when the source isn't in the ANN result nothing is
        # dropped and up to limit+1 rows would be returned.
        filtered = [r for r in results if r["memory_id"] != memory_id and r["score"] >= threshold]
        return filtered[:limit]

    async def find_similar_memories(
        self, memory_id: UUID, fingerprint: str, top_k: int = 5, min_score: float = 0.4,
    ) -> list[dict]:
        # Fetch the source vector first, then run the ANN probe with it as a
        # literal so the HNSW index serves the ORDER BY. The previous self-join
        # ordered by a column-vs-column distance (me1.embedding <=> me2.embedding)
        # which the index cannot accelerate, forcing a full partition scan on
        # every ingest (this runs per-memory for crossrefs).
        table = child_table("memory_embeddings", fingerprint)
        row = (await self.session.execute(
            text(f"SELECT embedding::text AS embedding_text FROM {table} WHERE memory_id = :memory_id"),
            {"memory_id": memory_id},
        )).mappings().first()
        if row is None:
            return []
        vector = self._parse_vector(row["embedding_text"])
        candidates = await self.search(vector, fingerprint=fingerprint, limit=top_k + 1)
        out = [
            {"memory_id": str(c["memory_id"]), "score": c["score"]}
            for c in candidates
            if str(c["memory_id"]) != str(memory_id) and c["score"] > min_score
        ]
        return out[:top_k]

    async def store_crossrefs(self, memory_id: UUID, crossrefs: list[dict]):
        # DELETE+INSERT, and the DELETE runs unconditionally: an empty
        # similar-set is a real result — the neighbours were deleted, or an
        # embedder rotation moved this memory into a sparse partition — and it
        # has to clear the previous run's rows rather than leave them pointing
        # at similarities that no longer hold and that nothing else ever clears.
        mem_id = str(memory_id)
        await self.session.execute(
            text("DELETE FROM memory_crossrefs "
                 "WHERE memory_id = CAST(:memory_id AS uuid)"),
            {"memory_id": mem_id},
        )
        if not crossrefs:
            return
        # Single multi-row insert; was N round-trips per memory ingest.
        related = [str(ref["memory_id"]) for ref in crossrefs]
        scores = [float(ref["score"]) for ref in crossrefs]
        await self.session.execute(
            text("""
                INSERT INTO memory_crossrefs (memory_id, related_memory_id, score)
                SELECT CAST(:memory_id AS uuid), r, s
                FROM unnest(CAST(:related AS uuid[]), CAST(:scores AS double precision[])) AS t(r, s)
                ON CONFLICT (memory_id, related_memory_id) DO UPDATE SET score = EXCLUDED.score
            """),
            {"memory_id": mem_id, "related": related, "scores": scores},
        )

    async def get_crossrefs(self, memory_id: UUID) -> list[dict]:
        result = await self.session.execute(
            text("""
                SELECT related_memory_id AS memory_id, score FROM memory_crossrefs WHERE memory_id = :id
                UNION
                SELECT memory_id, score FROM memory_crossrefs WHERE related_memory_id = :id
                ORDER BY score DESC
            """),
            {"id": memory_id},
        )
        return [{"memory_id": str(row.memory_id), "score": float(row.score)} for row in result]

    # --- Code chunk methods ---

    async def upsert_code_chunks(self, chunks: list[dict], fingerprint: str):
        if not chunks:
            return
        table = child_table("code_chunk_embeddings", fingerprint)
        await self.session.execute(
            text(f"""
                INSERT INTO {table}
                    (id, fingerprint, repo_id, file_path, language, symbol_name,
                     chunk_content, line_start, line_end, embedding)
                SELECT
                    gen_random_uuid(),
                    :fp,
                    d.repo_id::uuid,
                    d.file_path,
                    d.language,
                    d.symbol_name,
                    d.chunk_content,
                    d.line_start::int,
                    d.line_end::int,
                    CAST(d.embedding AS vector)
                FROM jsonb_to_recordset(CAST(:data AS jsonb)) AS d(
                    repo_id       text,
                    file_path     text,
                    language      text,
                    symbol_name   text,
                    chunk_content text,
                    line_start    text,
                    line_end      text,
                    embedding     text
                )
            """),
            {
                "fp": fingerprint,
                "data": json.dumps([
                    {
                        "repo_id": str(c["repo_id"]),
                        "file_path": c.get("file_path", ""),
                        "language": c.get("language"),
                        "symbol_name": c.get("symbol_name"),
                        "chunk_content": c.get("chunk_content"),
                        "line_start": str(c["line_start"]) if c.get("line_start") is not None else None,
                        "line_end": str(c["line_end"]) if c.get("line_end") is not None else None,
                        "embedding": str(c["embedding"]),
                    }
                    for c in chunks
                ]),
            },
        )

    async def search_code_chunks(
        self,
        vector: list[float],
        fingerprint: str,
        limit: int = 20,
        repo_id: UUID | None = None,
        language: str | None = None,
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
                SELECT id,
                       repo_id,
                       file_path,
                       language,
                       symbol_name,
                       chunk_content,
                       line_start,
                       line_end,
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
                "id": UUID(str(row.id)),
                "repo_id": UUID(str(row.repo_id)),
                "file_path": row.file_path,
                "language": row.language,
                "symbol_name": row.symbol_name,
                "chunk_content": row.chunk_content,
                "line_start": row.line_start,
                "line_end": row.line_end,
                "score": float(row.score),
            }
            for row in result
        ]
        return rows[:limit]

    async def delete_code_chunks_by_repo(self, repo_id: UUID):
        rows = (
            await self.session.execute(text("SELECT fingerprint FROM embedders"))
        ).scalars().all()
        for fp in rows:
            table = child_table("code_chunk_embeddings", fp)
            await self.session.execute(
                text(f"DELETE FROM {table} WHERE repo_id = :rid"),
                {"rid": repo_id},
            )

    async def delete_code_chunks_by_file(self, repo_id: UUID, file_path: str):
        rows = (
            await self.session.execute(text("SELECT fingerprint FROM embedders"))
        ).scalars().all()
        for fp in rows:
            table = child_table("code_chunk_embeddings", fp)
            await self.session.execute(
                text(
                    f"DELETE FROM {table} WHERE repo_id = :rid AND file_path = :fp_path"
                ),
                {"rid": repo_id, "fp_path": file_path},
            )

import json
from uuid import UUID, uuid4

import numpy as np
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding import CodeChunkEmbedding, MemoryEmbedding

_COMMUNITY_SAMPLE_CAP = 10_000


class PostgresVectorRepository:
    def __init__(self, session: AsyncSession, dimensions: int = 1024, collection_name: str = "memories"):
        self.session = session
        self.dimensions = dimensions
        self.collection_name = collection_name

    async def ensure_collection(self):
        pass

    async def upsert(self, memory_id: UUID, vector: list[float], payload: dict, model_fingerprint: str | None = None):
        await self.session.execute(
            text("""
                INSERT INTO memory_embeddings (id, memory_id, embedding, payload, model_fingerprint)
                VALUES (:id, :memory_id, :embedding, CAST(:payload AS jsonb), :fingerprint)
                ON CONFLICT (memory_id) DO UPDATE
                    SET embedding = EXCLUDED.embedding,
                        payload = EXCLUDED.payload,
                        model_fingerprint = EXCLUDED.model_fingerprint
            """),
            {
                "id": uuid4(),
                "memory_id": memory_id,
                "embedding": str(vector),
                "payload": json.dumps(payload),
                "fingerprint": model_fingerprint,
            },
        )

    async def search(self, vector: list[float], limit: int = 20) -> list[dict]:
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
            {"memory_id": UUID(str(row.memory_id)), "score": float(row.score), "payload": row.payload}
            for row in result
        ]

    async def delete(self, memory_id: UUID):
        await self.session.execute(
            delete(MemoryEmbedding).where(MemoryEmbedding.memory_id == memory_id)
        )

    @staticmethod
    def _parse_vector(raw) -> list[float]:
        if isinstance(raw, str):
            return [float(x) for x in raw.strip("[]").split(",")]
        if isinstance(raw, (list, tuple)):
            return [float(x) for x in raw]
        return list(raw)

    async def get_all_vectors(self, limit: int = 500) -> list[dict]:
        result = await self.session.execute(
            text("""
                SELECT memory_id, embedding, payload
                FROM memory_embeddings
                LIMIT :limit
            """),
            {"limit": limit},
        )
        return [
            {
                "memory_id": UUID(str(row.memory_id)),
                "vector": self._parse_vector(row.embedding),
                "payload": row.payload,
            }
            for row in result
        ]

    async def get_clustered_vectors(self, eps: float = 0.5, min_samples: int = 2, limit: int = 300) -> list[dict]:
        from sklearn.cluster import DBSCAN

        points = await self.get_all_vectors(limit=limit)
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
        self, min_score: float = 0.5, min_cluster_size: int = 3, limit: int = 500
    ) -> list[dict]:
        import igraph

        points = await self.get_all_vectors(limit=limit)
        if len(points) < 2:
            for p in points:
                p["cluster"] = 0
            return points

        vectors_arr = np.array([p["vector"] for p in points], dtype=np.float32)

        if len(points) > _COMMUNITY_SAMPLE_CAP:
            rng = np.random.default_rng(seed=42)
            sample_idx = rng.choice(len(points), size=_COMMUNITY_SAMPLE_CAP, replace=False)
            remainder_mask = np.ones(len(points), dtype=bool)
            remainder_mask[sample_idx] = False
            remainder_idx = np.where(remainder_mask)[0]

            sample_vecs = vectors_arr[sample_idx]
            membership = self._louvain_igraph(sample_vecs, min_score)

            comm_members: dict[int, list[int]] = {}
            for local_i, comm_id in enumerate(membership):
                comm_members.setdefault(comm_id, []).append(local_i)

            valid_clusters: dict[int, int] = {}
            next_id = 0
            for comm_id, members in sorted(comm_members.items()):
                if len(members) >= min_cluster_size:
                    valid_clusters[comm_id] = next_id
                    next_id += 1

            all_clusters: list[int] = [-1] * len(points)
            for local_i, global_i in enumerate(sample_idx.tolist()):
                all_clusters[global_i] = valid_clusters.get(membership[local_i], -1)

            if valid_clusters:
                centroids: dict[int, np.ndarray] = {}
                for comm_id, new_id in valid_clusters.items():
                    centroids[new_id] = sample_vecs[comm_members[comm_id]].mean(axis=0)

                centroid_ids = sorted(centroids.keys())
                centroid_matrix = np.array([centroids[c] for c in centroid_ids], dtype=np.float32)
                remainder_vecs = vectors_arr[remainder_idx]
                sims = remainder_vecs @ centroid_matrix.T
                norms_r = np.linalg.norm(remainder_vecs, axis=1, keepdims=True)
                norms_c = np.linalg.norm(centroid_matrix, axis=1, keepdims=True).T
                sims = sims / (norms_r * norms_c + 1e-8)
                best_centroid = np.argmax(sims, axis=1)
                for local_i, global_i in enumerate(remainder_idx.tolist()):
                    all_clusters[global_i] = centroid_ids[best_centroid[local_i]]

            for i, p in enumerate(points):
                p["cluster"] = all_clusters[i]

            return points

        membership = self._louvain_igraph(vectors_arr, min_score)

        comm_members: dict[int, list[int]] = {}
        for i, comm_id in enumerate(membership):
            comm_members.setdefault(comm_id, []).append(i)

        valid_clusters: dict[int, int] = {}
        next_id = 0
        for comm_id, members in sorted(comm_members.items()):
            if len(members) >= min_cluster_size:
                valid_clusters[comm_id] = next_id
                next_id += 1

        for i, p in enumerate(points):
            p["cluster"] = valid_clusters.get(membership[i], -1)

        return points

    @staticmethod
    def _build_sparse_edges(
        normalized: np.ndarray, threshold: float, chunk_size: int = 500
    ) -> tuple[list[tuple[int, int]], list[float]]:
        n = len(normalized)
        edges: list[tuple[int, int]] = []
        weights: list[float] = []
        for i in range(0, n, chunk_size):
            chunk = normalized[i : i + chunk_size]
            sims = chunk @ normalized.T
            for local_idx in range(len(chunk)):
                global_idx = i + local_idx
                for j in range(global_idx + 1, n):
                    if sims[local_idx, j] >= threshold:
                        edges.append((global_idx, j))
                        weights.append(float(sims[local_idx, j]))
        return edges, weights

    @staticmethod
    def _louvain_igraph(vectors: np.ndarray, min_score: float) -> list[int]:
        import igraph

        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = vectors / norms

        n = len(vectors)
        edges, weights = PostgresVectorRepository._build_sparse_edges(normalized, threshold=min_score)

        if not edges:
            return list(range(n))

        g = igraph.Graph(n=n, edges=edges, directed=False)
        g.es["weight"] = weights
        partition = g.community_multilevel(weights="weight")
        return partition.membership

    async def find_similar(self, memory_id: UUID, threshold: float = 0.9, limit: int = 10) -> list[dict]:
        result = await self.session.execute(
            select(MemoryEmbedding.embedding).where(MemoryEmbedding.memory_id == memory_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return []
        vector = self._parse_vector(row)
        results = await self.search(vector, limit=limit + 1)
        return [r for r in results if r["memory_id"] != memory_id and r["score"] >= threshold]

    async def find_similar_memories(self, memory_id: UUID, top_k: int = 5, min_score: float = 0.4) -> list[dict]:
        result = await self.session.execute(
            text("""
                SELECT me2.memory_id,
                       1 - (me1.embedding <=> me2.embedding) AS score
                FROM memory_embeddings me1, memory_embeddings me2
                WHERE me1.memory_id = :memory_id
                  AND me2.memory_id != :memory_id
                  AND 1 - (me1.embedding <=> me2.embedding) > :min_score
                ORDER BY me1.embedding <=> me2.embedding
                LIMIT :top_k
            """),
            {"memory_id": memory_id, "min_score": min_score, "top_k": top_k},
        )
        return [{"memory_id": str(row.memory_id), "score": float(row.score)} for row in result]

    async def store_crossrefs(self, memory_id: UUID, crossrefs: list[dict]):
        if not crossrefs:
            return
        await self.session.execute(
            text("DELETE FROM memory_crossrefs WHERE memory_id = :memory_id"),
            {"memory_id": memory_id},
        )
        for ref in crossrefs:
            await self.session.execute(
                text("""
                    INSERT INTO memory_crossrefs (memory_id, related_memory_id, score)
                    VALUES (:memory_id, :related_memory_id, :score)
                    ON CONFLICT (memory_id, related_memory_id) DO UPDATE SET score = EXCLUDED.score
                """),
                {"memory_id": memory_id, "related_memory_id": ref["memory_id"], "score": ref["score"]},
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

    async def upsert_code_chunks(self, chunks: list[dict]):
        """Insert code chunk embeddings. Callers must call delete_code_chunks_by_file
        for the relevant file before calling this to avoid duplicate rows."""
        if not chunks:
            return
        import json

        await self.session.execute(
            text("""
                INSERT INTO code_chunk_embeddings
                    (id, repo_id, file_path, language, symbol_name, chunk_content,
                     line_start, line_end, embedding)
                SELECT
                    gen_random_uuid(),
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
            {"data": json.dumps([
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
            ])},
        )

    async def search_code_chunks(
        self,
        vector: list[float],
        limit: int = 20,
        repo_id: UUID | None = None,
        language: str | None = None,
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
                SELECT id,
                       repo_id,
                       file_path,
                       language,
                       symbol_name,
                       chunk_content,
                       line_start,
                       line_end,
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

    async def delete_code_chunks_by_repo(self, repo_id: UUID):
        await self.session.execute(
            delete(CodeChunkEmbedding).where(CodeChunkEmbedding.repo_id == repo_id)
        )

    async def delete_code_chunks_by_file(self, repo_id: UUID, file_path: str):
        await self.session.execute(
            delete(CodeChunkEmbedding).where(
                CodeChunkEmbedding.repo_id == repo_id,
                CodeChunkEmbedding.file_path == file_path,
            )
        )

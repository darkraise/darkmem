from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


class QdrantVectorRepository:
    def __init__(self, client: AsyncQdrantClient, dimensions: int = 768, collection_name: str = "memories"):
        self.client = client
        self.dimensions = dimensions
        self.collection_name = collection_name

    async def ensure_collection(self):
        import logging
        log = logging.getLogger(__name__)
        collections = await self.client.get_collections()
        names = [c.name for c in collections.collections]
        if self.collection_name in names:
            info = await self.client.get_collection(self.collection_name)
            current_dim = info.config.params.vectors.size
            if current_dim != self.dimensions:
                log.warning(f"Collection dimension mismatch: {current_dim} vs {self.dimensions}. Recreating.")
                await self.client.delete_collection(self.collection_name)
                names.remove(self.collection_name)
        if self.collection_name not in names:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.dimensions, distance=Distance.COSINE),
            )
            log.info(f"Created Qdrant collection '{self.collection_name}' with {self.dimensions} dimensions")

    async def upsert(self, memory_id: UUID, vector: list[float], payload: dict):
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(id=str(memory_id), vector=vector, payload=payload)],
        )

    async def search(self, vector: list[float], limit: int = 20) -> list[dict]:
        results = await self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=limit,
        )
        return [
            {"memory_id": UUID(p.id), "score": p.score, "payload": p.payload}
            for p in results.points
        ]

    async def delete(self, memory_id: UUID):
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=[str(memory_id)],
        )

    async def get_all_vectors(self, limit: int = 500) -> list[dict]:
        points, _offset = await self.client.scroll(
            collection_name=self.collection_name,
            limit=limit,
            with_vectors=True,
            with_payload=True,
        )
        return [
            {
                "memory_id": p.id,
                "vector": list(p.vector),
                "payload": p.payload,
            }
            for p in points
        ]

    async def get_clustered_vectors(self, eps: float = 0.5, min_samples: int = 2, limit: int = 300) -> list[dict]:
        """Get all vectors with DBSCAN cluster assignments."""
        points = await self.get_all_vectors(limit=limit)
        if len(points) < 2:
            for p in points:
                p["cluster"] = 0
            return points

        import numpy as np
        vectors = np.array([p["vector"] for p in points], dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = vectors / norms
        similarity = normalized @ normalized.T
        distance_matrix = 1 - similarity

        n = len(points)
        labels = [-1] * n
        cluster_id = 0
        visited = [False] * n

        def region_query(idx):
            return [j for j in range(n) if distance_matrix[idx][j] <= eps]

        for i in range(n):
            if visited[i]:
                continue
            visited[i] = True
            neighbors = region_query(i)
            if len(neighbors) < min_samples:
                continue
            labels[i] = cluster_id
            seed_set = list(neighbors)
            j = 0
            while j < len(seed_set):
                q = seed_set[j]
                if not visited[q]:
                    visited[q] = True
                    q_neighbors = region_query(q)
                    if len(q_neighbors) >= min_samples:
                        seed_set.extend([x for x in q_neighbors if x not in seed_set])
                if labels[q] == -1:
                    labels[q] = cluster_id
                j += 1
            cluster_id += 1

        for i, p in enumerate(points):
            p["cluster"] = labels[i]

        return points

    async def get_fuzzy_clustered_vectors(self, n_clusters: int = 5, membership_threshold: float = 0.2, limit: int = 500) -> list[dict]:
        """Get all vectors with fuzzy cluster memberships (memories can belong to multiple clusters)."""
        points = await self.get_all_vectors(limit=limit)
        if len(points) < 3:
            for p in points:
                p["clusters"] = [0]
                p["memberships"] = {0: 1.0}
            return points

        import numpy as np
        vectors = np.array([p["vector"] for p in points], dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = vectors / norms

        # Auto-determine n_clusters if too many requested
        actual_clusters = min(n_clusters, max(2, len(points) // 3))

        # Fuzzy c-means
        n = len(points)
        m = 2.0  # fuzziness coefficient

        # Random init membership matrix
        rng = np.random.default_rng(42)
        U = rng.random((n, actual_clusters)).astype(np.float32)
        U = U / U.sum(axis=1, keepdims=True)  # normalize rows

        for _ in range(100):  # max iterations
            # Update centers
            Um = U ** m
            centers = (Um.T @ normalized) / Um.sum(axis=0)[:, np.newaxis]
            # Normalize centers
            center_norms = np.linalg.norm(centers, axis=1, keepdims=True)
            center_norms[center_norms == 0] = 1
            centers = centers / center_norms

            # Update membership matrix
            # Distance from each point to each center (cosine distance)
            dist = 1 - normalized @ centers.T  # (n, k)
            dist = np.maximum(dist, 1e-10)

            new_U = np.zeros_like(U)
            for j in range(actual_clusters):
                denom = np.zeros(n, dtype=np.float32)
                for k in range(actual_clusters):
                    denom += (dist[:, j] / dist[:, k]) ** (2 / (m - 1))
                new_U[:, j] = 1.0 / denom

            if np.allclose(U, new_U, atol=1e-4):
                break
            U = new_U

        # Assign clusters based on threshold
        for i, p in enumerate(points):
            memberships = {}
            clusters = []
            for j in range(actual_clusters):
                if U[i, j] >= membership_threshold:
                    memberships[j] = round(float(U[i, j]), 3)
                    clusters.append(j)
            if not clusters:
                # Assign to highest membership cluster
                best = int(np.argmax(U[i]))
                clusters = [best]
                memberships = {best: round(float(U[i, best]), 3)}
            p["clusters"] = clusters
            p["memberships"] = memberships

        return points

    async def find_similar(self, memory_id: UUID, threshold: float = 0.9, limit: int = 10) -> list[dict]:
        points = await self.client.retrieve(
            collection_name=self.collection_name, ids=[str(memory_id)], with_vectors=True,
        )
        if not points:
            return []
        vector = points[0].vector
        results = await self.search(vector, limit=limit + 1)
        return [r for r in results if r["memory_id"] != memory_id and r["score"] >= threshold]

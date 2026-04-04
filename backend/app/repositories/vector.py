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
        from app.utils.math import cosine_similarity_matrix
        vectors = np.array([p["vector"] for p in points], dtype=np.float32)
        similarity = cosine_similarity_matrix(vectors)
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

    async def get_louvain_clustered_vectors(self, min_score: float = 0.5, min_cluster_size: int = 3, limit: int = 500) -> list[dict]:
        """Get all vectors with Louvain community detection clusters.

        Builds a similarity graph from cosine similarity, then runs Louvain
        to find natural communities. Each memory belongs to exactly one cluster.
        Number of clusters is auto-detected from data structure.
        """
        points = await self.get_all_vectors(limit=limit)
        if len(points) < 2:
            for p in points:
                p["cluster"] = 0
            return points

        import numpy as np
        from app.utils.math import cosine_similarity_matrix
        vectors = np.array([p["vector"] for p in points], dtype=np.float32)
        sim_matrix = cosine_similarity_matrix(vectors)

        n = len(points)

        # Build weighted adjacency list (edges where similarity >= min_score)
        adj: dict[int, dict[int, float]] = {i: {} for i in range(n)}
        for i in range(n):
            for j in range(i + 1, n):
                score = float(sim_matrix[i][j])
                if score >= min_score:
                    adj[i][j] = score
                    adj[j][i] = score

        # Louvain community detection
        node2comm = self._louvain(adj)

        # Group by community, filter small clusters
        comm_members: dict[int, list[int]] = {}
        for node_id, comm_id in node2comm.items():
            comm_members.setdefault(comm_id, []).append(node_id)

        # Renumber valid clusters (>= min_cluster_size) starting from 0
        valid_clusters: dict[int, int] = {}
        next_id = 0
        for comm_id, members in sorted(comm_members.items()):
            if len(members) >= min_cluster_size:
                valid_clusters[comm_id] = next_id
                next_id += 1

        # Assign cluster to each point (-1 for noise/small clusters)
        for i, p in enumerate(points):
            orig_comm = node2comm.get(i, -1)
            p["cluster"] = valid_clusters.get(orig_comm, -1)

        return points

    @staticmethod
    def _louvain(adj: dict[int, dict[int, float]]) -> dict[int, int]:
        """Louvain community detection on a weighted graph."""
        if not adj:
            return {}

        nodes = list(adj.keys())
        node2comm = {n: n for n in nodes}

        # Total weight of all edges
        m2 = sum(w for n in nodes for w in adj[n].values())
        if m2 == 0.0:
            return node2comm

        k = {n: sum(adj[n].values()) for n in nodes}

        def _one_level(adj_, node2comm_, k_, m2_):
            sigma_tot: dict[int, float] = {}
            for n in adj_:
                c = node2comm_[n]
                sigma_tot[c] = sigma_tot.get(c, 0.0) + k_[n]

            improved = True
            changed = False
            while improved:
                improved = False
                for n in adj_:
                    c_old = node2comm_[n]
                    k_n = k_[n]

                    comm_weights: dict[int, float] = {}
                    for nb, w in adj_[n].items():
                        c_nb = node2comm_[nb]
                        comm_weights[c_nb] = comm_weights.get(c_nb, 0.0) + w

                    k_in_old = comm_weights.get(c_old, 0.0)
                    sigma_tot[c_old] -= k_n

                    best_comm = c_old
                    best_gain = 0.0

                    for c_target, k_in_target in comm_weights.items():
                        gain = (k_in_target - k_in_old) / m2_ - \
                               k_n * (sigma_tot.get(c_target, 0.0) - sigma_tot.get(c_old, 0.0)) / (m2_ * m2_)
                        if gain > best_gain:
                            best_gain = gain
                            best_comm = c_target

                    node2comm_[n] = best_comm
                    sigma_tot[best_comm] = sigma_tot.get(best_comm, 0.0) + k_n

                    if best_comm != c_old:
                        improved = True
                        changed = True
            return changed

        _one_level(adj, node2comm, k, m2)

        for _ in range(20):
            comm_set = set(node2comm.values())
            if len(comm_set) == len(adj):
                break

            super_adj: dict[int, dict[int, float]] = {c: {} for c in comm_set}
            for n in adj:
                c_n = node2comm[n]
                for nb, w in adj[n].items():
                    c_nb = node2comm[nb]
                    if c_n != c_nb:
                        super_adj[c_n][c_nb] = super_adj[c_n].get(c_nb, 0.0) + w

            super_k: dict[int, float] = {}
            for c in comm_set:
                super_k[c] = sum(super_adj[c].values())
                for n in adj:
                    if node2comm[n] == c:
                        for nb, w in adj[n].items():
                            if node2comm[nb] == c:
                                super_k[c] += w

            super_node2comm = {c: c for c in comm_set}
            changed = _one_level(super_adj, super_node2comm, super_k, m2)

            if not changed:
                break

            for n in list(node2comm.keys()):
                node2comm[n] = super_node2comm.get(node2comm[n], node2comm[n])

        comm_ids = sorted(set(node2comm.values()))
        remap = {c: i for i, c in enumerate(comm_ids)}
        return {n: remap[c] for n, c in node2comm.items()}

    async def find_similar(self, memory_id: UUID, threshold: float = 0.9, limit: int = 10) -> list[dict]:
        points = await self.client.retrieve(
            collection_name=self.collection_name, ids=[str(memory_id)], with_vectors=True,
        )
        if not points:
            return []
        vector = points[0].vector
        results = await self.search(vector, limit=limit + 1)
        return [r for r in results if r["memory_id"] != memory_id and r["score"] >= threshold]

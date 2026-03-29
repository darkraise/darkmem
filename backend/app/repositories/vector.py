from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


class QdrantVectorRepository:
    def __init__(self, client: AsyncQdrantClient, dimensions: int = 768, collection_name: str = "memories"):
        self.client = client
        self.dimensions = dimensions
        self.collection_name = collection_name

    async def ensure_collection(self):
        collections = await self.client.get_collections()
        names = [c.name for c in collections.collections]
        if self.collection_name not in names:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.dimensions, distance=Distance.COSINE),
            )

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

    async def get_similarity_graph(self, threshold: float = 0.3, limit: int = 200) -> dict:
        """Build a memory similarity graph: nodes = memories, edges = similarity pairs."""
        points = await self.get_all_vectors(limit=limit)
        if len(points) < 2:
            return {"nodes": [{"memory_id": p["memory_id"], "payload": p["payload"]} for p in points], "edges": []}

        import numpy as np
        vectors = np.array([p["vector"] for p in points], dtype=np.float32)
        # Normalize for cosine similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = vectors / norms
        # Pairwise cosine similarity
        sim_matrix = normalized @ normalized.T

        nodes = [{"memory_id": p["memory_id"], "payload": p["payload"]} for p in points]
        edges = []
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                score = float(sim_matrix[i][j])
                if score >= threshold:
                    edges.append({
                        "source": points[i]["memory_id"],
                        "target": points[j]["memory_id"],
                        "score": round(score, 3),
                    })

        return {"nodes": nodes, "edges": edges}

    async def find_similar(self, memory_id: UUID, threshold: float = 0.9, limit: int = 10) -> list[dict]:
        points = await self.client.retrieve(
            collection_name=self.collection_name, ids=[str(memory_id)], with_vectors=True,
        )
        if not points:
            return []
        vector = points[0].vector
        results = await self.search(vector, limit=limit + 1)
        return [r for r in results if r["memory_id"] != memory_id and r["score"] >= threshold]

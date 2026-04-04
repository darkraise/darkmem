import logging
from uuid import UUID

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.repositories.graph import Neo4jGraphRepository
from app.repositories.vector import QdrantVectorRepository
from app.services.llm import LLMOrchestrator

logger = logging.getLogger(__name__)


class GraphService:
    def __init__(
        self,
        session: AsyncSession,
        vector_repo: QdrantVectorRepository | None = None,
        graph_repo: Neo4jGraphRepository | None = None,
        llm: LLMOrchestrator | None = None,
    ):
        self.session = session
        self.vector_repo = vector_repo
        self.graph_repo = graph_repo
        self.llm = llm

    async def get_unified_graph(
        self,
        limit: int = 200,
        similarity_threshold: float = 0.75,
        min_cluster_size: int = 3,
        include_entities: bool = False,
    ) -> dict:
        importance_map = await self._fetch_importance_map()

        memory_nodes = []
        clusters: dict[int, list[str]] = {}
        similarity_edges: list[dict] = []

        if self.vector_repo:
            try:
                clustered = await self.vector_repo.get_louvain_clustered_vectors(
                    min_score=similarity_threshold,
                    min_cluster_size=min_cluster_size,
                    limit=limit,
                )
                for p in clustered:
                    payload = p.get("payload", {})
                    mid = str(p["memory_id"])
                    cluster_id = p.get("cluster", -1)
                    memory_nodes.append({
                        "id": mid,
                        "content": payload.get("content", "") or "",
                        "source": payload.get("source", ""),
                        "tags": payload.get("tags", []),
                        "memory_type": payload.get("memory_type"),
                        "importance": importance_map.get(mid, 0.5),
                        "cluster": cluster_id,
                    })
                    if cluster_id >= 0:
                        clusters.setdefault(cluster_id, []).append(mid)

                similarity_edges = self._compute_similarity_edges(clustered, similarity_threshold)
            except Exception:
                logger.exception("Failed to fetch vector data")

        cluster_names = await self._generate_cluster_names(clusters, memory_nodes)

        result = {
            "memories": memory_nodes,
            "clusters": {str(k): v for k, v in clusters.items()},
            "cluster_names": cluster_names,
            "similarity_edges": similarity_edges,
        }

        if include_entities:
            entities, entity_relations = await self._fetch_entity_overlay(memory_nodes)
            result["entities"] = entities
            result["entity_relations"] = entity_relations

        return result

    async def get_memory_context(self, memory_id: str) -> dict:
        if not self.graph_repo:
            return {"entities": [], "relations": [], "neighbors": []}

        entities = await self.graph_repo.get_entities_by_memory_id(memory_id)
        entity_names = [e["name"] for e in entities]
        relations = await self.graph_repo.get_relations_between(entity_names)

        neighbor_memory_ids = set()
        for entity in entities:
            for mid in entity.get("memory_ids", []):
                if mid != memory_id:
                    neighbor_memory_ids.add(mid)

        neighbors = await self._fetch_neighbor_memories(list(neighbor_memory_ids)[:20])

        return {
            "entities": entities,
            "relations": relations,
            "neighbors": neighbors,
        }

    async def _fetch_importance_map(self) -> dict[str, float]:
        try:
            result = await self.session.execute(select(Memory.id, Memory.importance))
            return {str(row[0]): row[1] for row in result.all()}
        except Exception:
            logger.exception("Failed to fetch importance data")
            return {}

    def _compute_similarity_edges(
        self, clustered: list[dict], threshold: float
    ) -> list[dict]:
        if len(clustered) < 2:
            return []

        from app.utils.math import cosine_similarity_matrix
        vectors = np.array([p["vector"] for p in clustered], dtype=np.float32)
        sim_matrix = cosine_similarity_matrix(vectors)
        ids = [str(p["memory_id"]) for p in clustered]

        edges = []
        n = len(ids)
        for i in range(n):
            for j in range(i + 1, n):
                score = float(sim_matrix[i, j])
                if score >= threshold:
                    edges.append({
                        "source": ids[i],
                        "target": ids[j],
                        "score": round(score, 3),
                    })
        return edges

    async def _generate_cluster_names(
        self, clusters: dict[int, list[str]], memory_nodes: list[dict]
    ) -> dict[str, str]:
        cluster_names: dict[str, str] = {}

        if not self.llm or not clusters:
            for cid in clusters:
                cluster_names[str(cid)] = f"Cluster {cid}"
            return cluster_names

        content_by_cluster: dict[int, list[str]] = {}
        for m in memory_nodes:
            cid = m.get("cluster", -1)
            if cid >= 0:
                content_by_cluster.setdefault(cid, []).append(m["content"][:100])

        for cid, contents in content_by_cluster.items():
            try:
                sample = "\n".join(contents[:8])
                name = await self.llm.chat_completion(
                    "extraction",
                    messages=[
                        {"role": "system", "content": "You are a naming assistant. Given a group of related memory snippets, generate a short descriptive name (2-4 words, no quotes). Just output the name, nothing else."},
                        {"role": "user", "content": sample},
                    ],
                )
                cluster_names[str(cid)] = name.strip().strip('"').strip("'")[:40]
            except Exception:
                cluster_names[str(cid)] = f"Cluster {cid}"

        return cluster_names

    async def _fetch_entity_overlay(
        self, memory_nodes: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        if not self.graph_repo:
            return [], []

        try:
            memory_id_set = {m["id"] for m in memory_nodes}
            full_graph = await self.graph_repo.get_full_graph(limit=500)
            entities = [
                e for e in full_graph["entities"]
                if any(mid in memory_id_set for mid in e.get("memory_ids", []))
            ]
            entity_id_set = {e["id"] for e in entities}
            relations = [
                r for r in full_graph["relations"]
                if r.get("source") in entity_id_set and r.get("target") in entity_id_set
            ]
            return entities, relations
        except Exception:
            logger.exception("Failed to fetch entity data")
            return [], []

    async def _fetch_neighbor_memories(self, memory_ids: list[str]) -> list[dict]:
        neighbors = []
        for mid in memory_ids:
            try:
                result = await self.session.execute(
                    select(Memory).where(Memory.id == UUID(mid))
                )
                mem = result.scalar_one_or_none()
                if mem:
                    neighbors.append({
                        "id": str(mem.id),
                        "content": mem.content[:100],
                        "source": mem.source,
                        "memory_type": mem.memory_type,
                    })
            except Exception:
                logger.warning(f"Failed to fetch neighbor memory {mid}")
        return neighbors

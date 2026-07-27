import asyncio
import logging
from uuid import UUID

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import MemoryFilter, PostgresVectorRepository
from app.services.llm import LLMOrchestrator
from app.services import prompt

logger = logging.getLogger(__name__)

# The memory-row arms of the graph service default to the same lifecycle scope
# the search surface does. The entity and relation arms deliberately do not
# carry it: an edge asserted only by a superseded memory is still a true
# statement about what the corpus once claimed, and dropping it would empty the
# context view of exactly the memory a reader opened it to understand.
GRAPH_MEMORY_STATUSES: tuple[str, ...] = ("active",)


class GraphService:
    def __init__(
        self,
        session: AsyncSession,
        vector_repo: PostgresVectorRepository | None = None,
        graph_repo: PostgresGraphRepository | None = None,
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
        project: str | None = None,
    ) -> dict:
        memory_nodes = []
        clusters: dict[int, list[str]] = {}
        similarity_edges: list[dict] = []

        if self.vector_repo and self.llm is not None:
            try:
                fingerprint = self.llm.llm_fingerprint()
                clustered = await self.vector_repo.get_louvain_clustered_vectors(
                    fingerprint=fingerprint,
                    min_score=similarity_threshold,
                    min_cluster_size=min_cluster_size,
                    limit=limit,
                    filters=self._memory_scope(
                        MemoryFilter(project=project) if project is not None else None
                    ),
                )
                # Fetch importance only for the IDs we actually plot. The
                # previous implementation did a full-table scan on every
                # request, which gets expensive once the corpus grows.
                clustered_ids = [p["memory_id"] for p in clustered]
                importance_map = await self._fetch_importance_map(clustered_ids)
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
                        "project": p.get("project"),
                        "status": p.get("status"),
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

        # Entities are not memory-scoped, so their memory_ids reach into every
        # project that asserts them. Scope the expansion by the seed memory's
        # own project or the walk hands back foreign rows.
        scope = await self._project_scope(memory_id)

        entities = await self.graph_repo.get_entities_by_memory_id(memory_id)
        entity_names = [e["name"] for e in entities]
        relations = await self.graph_repo.get_relations_between(entity_names, scope=scope)

        neighbor_memory_ids = set()
        for entity in entities:
            for mid in entity.get("memory_ids", []):
                if mid != memory_id:
                    neighbor_memory_ids.add(mid)

        neighbors = await self._fetch_neighbor_memories(
            list(neighbor_memory_ids)[:20], self._memory_scope(scope),
        )

        return {
            "entities": entities,
            "relations": relations,
            "neighbors": neighbors,
        }

    async def _fetch_importance_map(self, memory_ids: list) -> dict[str, float]:
        if not memory_ids:
            return {}
        try:
            result = await self.session.execute(
                select(Memory.id, Memory.importance).where(Memory.id.in_(memory_ids))
            )
            return {str(row[0]): row[1] for row in result.all()}
        except Exception:
            logger.exception("Failed to fetch importance data")
            return {}

    def _compute_similarity_edges(
        self, clustered: list[dict], threshold: float, max_edges: int = 1000
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
        if len(edges) > max_edges:
            edges.sort(key=lambda e: e["score"], reverse=True)
            edges = edges[:max_edges]
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

        cluster_system_prompt = prompt.get("cluster_naming")
        sem = asyncio.Semaphore(3)

        async def _name_one(cid: int, contents: list[str]) -> tuple[int, str]:
            async with sem:
                try:
                    sample = "\n".join(contents[:8])
                    name = await self.llm.chat_completion(
                        "extraction",
                        messages=[
                            {"role": "system", "content": cluster_system_prompt},
                            {"role": "user", "content": sample},
                        ],
                    )
                    return cid, name.strip().strip('"').strip("'")[:40]
                except Exception:
                    return cid, f"Cluster {cid}"

        results = await asyncio.gather(
            *[_name_one(cid, contents) for cid, contents in content_by_cluster.items()]
        )
        for cid, name in results:
            cluster_names[str(cid)] = name

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

    async def _project_scope(self, memory_id: str) -> MemoryFilter | None:
        try:
            project = (
                await self.session.execute(
                    select(Memory.project).where(Memory.id == UUID(memory_id))
                )
            ).scalar_one_or_none()
        except ValueError:
            return None
        return MemoryFilter(project=project) if project is not None else None

    @staticmethod
    def _memory_scope(scope: MemoryFilter | None) -> MemoryFilter:
        """Widen a structural scope into the one the memory-row arms use.

        A seed whose project could not be resolved still gets the lifecycle
        predicates, so an unresolvable seed degrades to a narrower answer rather
        than to an unscoped one.
        """
        project = scope.project if scope is not None else None
        return MemoryFilter(project=project, statuses=GRAPH_MEMORY_STATUSES)

    async def _fetch_neighbor_memories(
        self, memory_ids: list[str], scope: MemoryFilter | None = None,
    ) -> list[dict]:
        if not memory_ids:
            return []
        try:
            uuids = [UUID(mid) for mid in memory_ids]
            stmt = select(Memory).where(Memory.id.in_(uuids))
            if scope is not None:
                stmt = stmt.where(*scope.orm_criteria(Memory))
            result = await self.session.execute(stmt)
            return [
                {
                    "id": str(mem.id),
                    "content": mem.content[:100],
                    "source": mem.source,
                    "memory_type": mem.memory_type,
                    "project": mem.project,
                    "status": mem.status,
                }
                for mem in result.scalars().all()
            ]
        except Exception:
            logger.warning("Failed to fetch neighbor memories")
            return []

import logging
from collections import OrderedDict
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import EmbedderFingerprintUnresolved, MemoryFilter, PostgresVectorRepository
from app.schemas.graph import GraphMemoryNode
from app.services.llm import LLMOrchestrator
from app.utils.cluster_names import name_clusters

logger = logging.getLogger(__name__)

# The memory-row arms of the graph service default to the same lifecycle scope
# the search surface does. The entity and relation arms deliberately do not
# carry it: an edge asserted only by a superseded memory is still a true
# statement about what the corpus once claimed, and dropping it would empty the
# context view of exactly the memory a reader opened it to understand.
GRAPH_MEMORY_STATUSES: tuple[str, ...] = ("active",)

GRAPH_MAX_NODES = 50_000
# Labels, the page's text filter and the detail panel's first paint need only
# this much; the panel reads the whole memory when a node says it was cut.
NODE_PREVIEW_CHARS = 280
GRAPH_MAX_ENTITIES = 20_000
_RESULT_CACHE_SIZE = 4

# The assembled memory arm, keyed on everything that decides it. Module-level
# state is sound only because invariant 13 pins one process. A hit hands out
# the cached lists themselves, not copies: mutating a result corrupts every
# later hit.
_result_cache: OrderedDict[tuple, dict] = OrderedDict()


def reset_graph_caches() -> None:
    """Test hook: forget every cached memory arm."""
    _result_cache.clear()


def _empty_memory_arm() -> dict:
    return {
        "memories": [],
        "clusters": {},
        "cluster_names": {},
        "similarity_edges": [],
        "total_memories": 0,
        "memories_truncated": False,
    }


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
        all_memories: bool = False,
    ) -> dict:
        effective_limit = GRAPH_MAX_NODES if all_memories else min(limit, GRAPH_MAX_NODES)
        memory_arm = _empty_memory_arm()
        fingerprint_unresolved = False

        if self.vector_repo and self.llm is not None:
            try:
                fingerprint = await self.vector_repo.resolve_read_fingerprint(self.llm)
                scope = self._memory_scope(
                    MemoryFilter(project=project) if project is not None else None
                )
                total, last_updated = await self.vector_repo.scope_stamp(fingerprint, scope)
                key = (
                    fingerprint, project, similarity_threshold, min_cluster_size,
                    effective_limit, total, last_updated,
                )
                cached = _result_cache.get(key)
                if cached is not None:
                    _result_cache.move_to_end(key)
                    memory_arm = cached
                else:
                    memory_arm, degraded = await self._build_memory_arm(
                        fingerprint, scope, similarity_threshold, min_cluster_size,
                        effective_limit, total,
                    )
                    # A degraded arm's names were built without entity terms;
                    # caching it would pin them until the corpus next changes.
                    if not degraded:
                        _result_cache[key] = memory_arm
                        while len(_result_cache) > _RESULT_CACHE_SIZE:
                            _result_cache.popitem(last=False)
            except EmbedderFingerprintUnresolved:
                # Distinguishable from "no data": the embedding purpose's
                # dimensions is unset, or set to a value no real embed has
                # produced, and nothing has ever embedded under this model, so
                # there is no partition to read at all (invariant 2,
                # T2.68/T2.83) — surfaced on the response rather than only
                # logged, so an empty vector arm can never be mistaken for
                # "no data".
                fingerprint_unresolved = True
                logger.warning(
                    "Unified graph vector arm skipped: embedding fingerprint unresolved"
                )
            except Exception:
                logger.exception("Failed to fetch vector data")

        result = {**memory_arm, "fingerprint_unresolved": fingerprint_unresolved}

        if include_entities:
            entities, entity_relations, entities_truncated = await self._fetch_entity_overlay(
                result["memories"]
            )
            result["entities"] = entities
            result["entity_relations"] = entity_relations
            result["entities_truncated"] = entities_truncated

        return result

    async def _build_memory_arm(
        self,
        fingerprint: str,
        scope: MemoryFilter,
        similarity_threshold: float,
        min_cluster_size: int,
        limit: int,
        total: int,
    ) -> tuple[dict, bool]:
        clustered, similarity_edges = await self.vector_repo.get_louvain_clustered_vectors(
            fingerprint=fingerprint,
            min_score=similarity_threshold,
            min_cluster_size=min_cluster_size,
            limit=limit,
            filters=scope,
        )
        memory_nodes: list[GraphMemoryNode] = []
        clusters: dict[int, list[str]] = {}
        for p in clustered:
            payload = p.get("payload") or {}
            mid = str(p["memory_id"])
            cluster_id = p.get("cluster", -1)
            importance = p.get("importance")
            content = payload.get("content", "") or ""
            memory_nodes.append({
                "id": mid,
                "content": content[:NODE_PREVIEW_CHARS],
                "content_truncated": len(content) > NODE_PREVIEW_CHARS,
                "source": payload.get("source", ""),
                "tags": payload.get("tags", []),
                "memory_type": payload.get("memory_type"),
                "importance": importance if importance is not None else 0.5,
                "cluster": cluster_id,
                "project": p.get("project"),
                "status": p.get("status"),
            })
            if cluster_id >= 0:
                clusters.setdefault(cluster_id, []).append(mid)

        tags = {m["id"]: m["tags"] or [] for m in memory_nodes}
        projects = {m["id"]: m["project"] for m in memory_nodes}
        entity_terms: dict[str, set[str]] = {}
        degraded = False
        if self.graph_repo:
            try:
                # The repository shares the request session: a failed statement
                # outside a savepoint would abort the request's transaction.
                async with self.session.begin_nested():
                    entity_terms = await self.graph_repo.entity_terms_for_memories(
                        [m["id"] for m in memory_nodes]
                    )
            except Exception:
                logger.exception("Failed to fetch entity terms for cluster names")
                entity_terms = {}
                degraded = True
        cluster_names = name_clusters(clusters, tags, projects, entity_terms)
        return {
            "memories": memory_nodes,
            "clusters": {str(k): v for k, v in clusters.items()},
            "cluster_names": cluster_names,
            "similarity_edges": similarity_edges,
            "total_memories": total,
            "memories_truncated": len(memory_nodes) < total,
        }, degraded

    async def get_memory_context(self, memory_id: UUID | str) -> dict:
        if not self.graph_repo:
            return {"entities": [], "relations": [], "neighbors": []}
        # Entity memory_ids come back in canonical lower case; an upper-case
        # seed would otherwise never match itself and list itself as a peer.
        memory_id = str(UUID(str(memory_id)))

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
            sorted(neighbor_memory_ids), self._memory_scope(scope),
        )

        return {
            "entities": entities,
            "relations": relations,
            "neighbors": neighbors,
        }

    async def _fetch_entity_overlay(
        self, memory_nodes: list[dict]
    ) -> tuple[list[dict], list[dict], bool]:
        if not self.graph_repo:
            return [], [], False

        try:
            result = await self.graph_repo.get_entities_for_memories(
                [m["id"] for m in memory_nodes], limit=GRAPH_MAX_ENTITIES,
            )
            return result["entities"], result["relations"], result["truncated"]
        except Exception:
            logger.exception("Failed to fetch entity data")
            return [], [], False

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
            ids = [str(UUID(mid)) for mid in memory_ids]
            stmt = select(Memory).where(
                text("memories.id = ANY(CAST(:ids AS uuid[]))").bindparams(ids=ids),
            )
            if scope is not None:
                stmt = stmt.where(*scope.orm_criteria(Memory))
            stmt = stmt.order_by(Memory.id).limit(20)
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

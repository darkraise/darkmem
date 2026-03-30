from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.auth import require_auth
from app.repositories.graph import Neo4jGraphRepository
from app.schemas.graph import EntityResponse, FullGraphResponse, NeighborsResponse, RelationResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


def _get_graph_repo(request: Request) -> Neo4jGraphRepository:
    repo = getattr(request.app.state, "graph_repo", None)
    if not repo:
        raise HTTPException(status_code=503, detail="Graph service not available")
    return repo


@router.get("/full", response_model=FullGraphResponse)
async def get_full_graph(
    limit: int = Query(200),
    _user=Depends(require_auth),
    request: Request = None,
):
    repo = _get_graph_repo(request)
    result = await repo.get_full_graph(limit=limit)
    return FullGraphResponse(
        entities=[EntityResponse(**e) for e in result["entities"]],
        relations=[RelationResponse(**r) for r in result["relations"]],
    )


@router.get("/entities", response_model=list[EntityResponse])
async def list_entities(
    entity_type: str | None = Query(None),
    name: str | None = Query(None),
    limit: int = Query(50),
    _user=Depends(require_auth),
    request: Request = None,
):
    repo = _get_graph_repo(request)
    entities = await repo.get_entities(entity_type=entity_type, name_query=name, limit=limit)
    return [EntityResponse(**e) for e in entities]


@router.get("/unified")
async def get_unified_graph(
    limit: int = Query(200),
    similarity_threshold: float = Query(0.75, ge=0.0, le=1.0),
    _user=Depends(require_auth),
    request: Request = None,
):
    from app.database import async_session_factory
    from app.models.memory import Memory
    from sqlalchemy import select

    vector_repo = getattr(request.app.state, "vector_repo", None)

    # Fetch importance map from Postgres
    importance_map: dict[str, float] = {}
    try:
        async with async_session_factory() as session:
            result = await session.execute(select(Memory.id, Memory.importance))
            importance_map = {str(row[0]): row[1] for row in result.all()}
    except Exception:
        logger.exception("Failed to fetch importance data")

    memory_nodes = []
    clusters: dict = {}
    similarity_edges: list[dict] = []

    if vector_repo:
        try:
            import numpy as np
            clustered = await vector_repo.get_fuzzy_clustered_vectors(limit=limit)
            for p in clustered:
                payload = p.get("payload", {})
                mid = str(p["memory_id"])
                memory_nodes.append({
                    "id": mid,
                    "content": payload.get("content", "") or "",
                    "source": payload.get("source", ""),
                    "tags": payload.get("tags", []),
                    "memory_type": payload.get("memory_type"),
                    "importance": importance_map.get(mid, 0.5),
                    "clusters": p["clusters"],
                    "memberships": {str(k): v for k, v in p["memberships"].items()},
                })
                for c in p["clusters"]:
                    clusters.setdefault(c, []).append(mid)

            # Compute pairwise cosine similarity edges
            if len(clustered) >= 2:
                vectors = np.array([p["vector"] for p in clustered], dtype=np.float32)
                norms = np.linalg.norm(vectors, axis=1, keepdims=True)
                norms[norms == 0] = 1
                normalized = vectors / norms
                sim_matrix = normalized @ normalized.T
                ids = [str(p["memory_id"]) for p in clustered]
                n = len(ids)
                for i in range(n):
                    for j in range(i + 1, n):
                        score = float(sim_matrix[i, j])
                        if score >= similarity_threshold:
                            similarity_edges.append({
                                "source": ids[i],
                                "target": ids[j],
                                "score": round(score, 3),
                            })
        except Exception:
            logger.exception("Failed to fetch vector data")

    return {
        "memories": memory_nodes,
        "clusters": {str(k): v for k, v in clusters.items()},
        "similarity_edges": similarity_edges,
    }


@router.get("/memory-context/{memory_id}")
async def get_memory_context(
    memory_id: str,
    _user=Depends(require_auth),
    request: Request = None,
):
    from app.database import async_session_factory
    from app.models.memory import Memory
    from sqlalchemy import select
    from uuid import UUID

    graph_repo = getattr(request.app.state, "graph_repo", None)
    if not graph_repo:
        return {"entities": [], "relations": [], "neighbors": []}

    # Find entities that reference this memory_id
    entities = await graph_repo.get_entities_by_memory_id(memory_id)

    # Find relations between those entities
    entity_names = [e["name"] for e in entities]
    relations = await graph_repo.get_relations_between(entity_names)

    # Find neighboring memories that share the same entities
    neighbor_memory_ids = set()
    for entity in entities:
        for mid in entity.get("memory_ids", []):
            if mid != memory_id:
                neighbor_memory_ids.add(mid)

    # Get neighbor memory content from Postgres
    neighbors = []
    async with async_session_factory() as session:
        for mid in list(neighbor_memory_ids)[:20]:
            try:
                result = await session.execute(select(Memory).where(Memory.id == UUID(mid)))
                mem = result.scalar_one_or_none()
                if mem:
                    neighbors.append({
                        "id": str(mem.id),
                        "content": mem.content[:100],
                        "source": mem.source,
                        "memory_type": mem.memory_type,
                    })
            except Exception:
                pass

    return {
        "entities": entities,
        "relations": relations,
        "neighbors": neighbors,
    }


@router.get("/entities/{entity_id}/neighbors", response_model=NeighborsResponse)
async def get_neighbors(
    entity_id: str,
    depth: int = Query(1, ge=1, le=3),
    _user=Depends(require_auth),
    request: Request = None,
):
    repo = _get_graph_repo(request)
    result = await repo.get_neighbors_by_id(entity_id, depth=depth)
    if not result["entity"]:
        raise HTTPException(status_code=404, detail="Entity not found")
    return NeighborsResponse(
        entity=EntityResponse(**result["entity"]) if result["entity"] else None,
        neighbors=[EntityResponse(**n) for n in result["neighbors"]],
        relations=result["relations"],
    )

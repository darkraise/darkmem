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
    _user=Depends(require_auth),
    request: Request = None,
):
    graph_repo = getattr(request.app.state, "graph_repo", None)
    vector_repo = getattr(request.app.state, "vector_repo", None)

    entities = []
    relations = []
    if graph_repo:
        try:
            full = await graph_repo.get_full_graph(limit=limit)
            entities = full["entities"]
            relations = full["relations"]
        except Exception:
            logger.exception("Failed to fetch graph data")

    memory_nodes = []
    clusters: dict = {}
    if vector_repo:
        try:
            clustered = await vector_repo.get_clustered_vectors(limit=limit)
            for p in clustered:
                payload = p.get("payload", {})
                memory_nodes.append({
                    "id": str(p["memory_id"]),
                    "content": (payload.get("content", "") or "")[:120],
                    "source": payload.get("source", ""),
                    "tags": payload.get("tags", []),
                    "memory_type": payload.get("memory_type"),
                    "cluster": p["cluster"],
                })
                c = p["cluster"]
                if c >= 0:
                    clusters.setdefault(c, []).append(str(p["memory_id"]))
        except Exception:
            logger.exception("Failed to fetch vector data")

    memory_id_set = {m["id"] for m in memory_nodes}
    mentions = []
    for entity in entities:
        entity_id = entity.get("id") or entity.get("name")
        for mid in (entity.get("memory_ids") or []):
            if str(mid) in memory_id_set:
                mentions.append({"source": str(mid), "target": entity_id})

    return {
        "entities": [
            {
                "id": e.get("id") or e.get("name"),
                "name": e.get("name", ""),
                "entity_type": e.get("entity_type", "concept"),
                "node_type": "entity",
            }
            for e in entities
        ],
        "memories": memory_nodes,
        "relations": relations,
        "mentions": mentions,
        "clusters": {str(k): v for k, v in clusters.items()},
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

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.auth import require_auth
from app.api.deps import get_graph_service
from app.repositories.graph import Neo4jGraphRepository
from app.schemas.graph import EntityResponse, FullGraphResponse, NeighborsResponse, RelationResponse
from app.services.graph import GraphService

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
    min_cluster_size: int = Query(3, ge=2, le=10),
    include_entities: bool = Query(False),
    _user=Depends(require_auth),
    service: GraphService = Depends(get_graph_service),
):
    return await service.get_unified_graph(
        limit=limit,
        similarity_threshold=similarity_threshold,
        min_cluster_size=min_cluster_size,
        include_entities=include_entities,
    )


@router.get("/memory-context/{memory_id}")
async def get_memory_context(
    memory_id: str,
    _user=Depends(require_auth),
    service: GraphService = Depends(get_graph_service),
):
    return await service.get_memory_context(memory_id)


@router.get("/entities/{entity_id}/neighbors", response_model=NeighborsResponse)
async def get_neighbors(
    entity_id: str,
    _user=Depends(require_auth),
    request: Request = None,
):
    repo = _get_graph_repo(request)
    result = await repo.get_neighbors_by_id(entity_id)
    if not result["entity"]:
        raise HTTPException(status_code=404, detail="Entity not found")
    return NeighborsResponse(
        entity=EntityResponse(**result["entity"]) if result["entity"] else None,
        neighbors=[EntityResponse(**n) for n in result["neighbors"]],
        relations=result["relations"],
    )

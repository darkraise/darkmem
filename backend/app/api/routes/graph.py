from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import GraphServiceDep
from app.database import SessionDep
from app.repositories.graph import PostgresGraphRepository
from app.schemas.graph import EntityResponse, FullGraphResponse, NeighborsResponse, RelationResponse
from app.services.graph import GRAPH_MAX_NODES, GraphService

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


def _get_graph_repo(request: Request, session: AsyncSession) -> PostgresGraphRepository:
    return PostgresGraphRepository(session)


@router.get("/full", response_model=FullGraphResponse)
async def get_full_graph(
    limit: int = Query(200, ge=1, le=1000),
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = SessionDep,
):
    repo = _get_graph_repo(request, session)
    result = await repo.get_full_graph(limit=limit)
    return FullGraphResponse(
        entities=[EntityResponse(**e) for e in result["entities"]],
        relations=[RelationResponse(**r) for r in result["relations"]],
    )


@router.get("/entities", response_model=list[EntityResponse])
async def list_entities(
    entity_type: str | None = Query(None),
    name: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = SessionDep,
):
    repo = _get_graph_repo(request, session)
    entities = await repo.get_entities(entity_type=entity_type, name_query=name, limit=limit)
    return [EntityResponse(**e) for e in entities]


@router.get("/unified")
async def get_unified_graph(
    limit: int = Query(200, ge=1, le=GRAPH_MAX_NODES),
    all_memories: bool = Query(
        False,
        alias="all",
        description="Every in-scope memory, newest first, up to the node ceiling; overrides limit.",
    ),
    similarity_threshold: float = Query(0.75, ge=0.0, le=1.0),
    min_cluster_size: int = Query(3, ge=2, le=10),
    include_entities: bool = Query(False),
    project: str | None = Query(None),
    _user=Depends(require_auth),
    service: GraphService = GraphServiceDep,
):
    return await service.get_unified_graph(
        limit=limit,
        similarity_threshold=similarity_threshold,
        min_cluster_size=min_cluster_size,
        include_entities=include_entities,
        project=project,
        all_memories=all_memories,
    )


@router.get("/memory-context/{memory_id}")
async def get_memory_context(
    memory_id: UUID,
    _user=Depends(require_auth),
    service: GraphService = GraphServiceDep,
):
    return await service.get_memory_context(memory_id)


@router.get("/entities/{entity_id}/neighbors", response_model=NeighborsResponse)
async def get_neighbors(
    entity_id: UUID,
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = SessionDep,
):
    repo = _get_graph_repo(request, session)
    result = await repo.get_neighbors_by_id(entity_id)
    if not result["entity"]:
        raise HTTPException(status_code=404, detail="Entity not found")
    return NeighborsResponse(
        entity=EntityResponse(**result["entity"]) if result["entity"] else None,
        neighbors=[EntityResponse(**n) for n in result["neighbors"]],
        relations=result["relations"],
    )

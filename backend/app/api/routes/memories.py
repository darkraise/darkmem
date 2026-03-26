from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import require_auth
from app.api.deps import get_memory_service
from app.models.memory import Memory
from app.schemas.memory import MemoryBatchCreate, MemoryCreate, MemoryMergeRequest, MemoryResponse, MemorySearchRequest, MemoryUpdate
from app.schemas.reason import ReasonRequest, ReasonResponse
from app.services.memory import MemoryService

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])


def _to_response(memory: Memory) -> MemoryResponse:
    return MemoryResponse(
        id=memory.id,
        content=memory.content,
        source=memory.source,
        source_agent=memory.source_agent,
        memory_type=memory.memory_type,
        importance=memory.importance,
        metadata=memory.metadata_,
        tags=[t.name for t in memory.tags],
        created_at=memory.created_at,
        updated_at=memory.updated_at,
        expires_at=memory.expires_at,
        is_archived=memory.is_archived,
    )


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    body: MemoryCreate,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    memory = await service.create_memory(body, api_key_id=None)
    return _to_response(memory)


@router.post("/reason", response_model=ReasonResponse)
async def reason(
    body: ReasonRequest,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    result = await service.reason(body.question, limit=body.limit)
    return ReasonResponse(**result)


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: UUID,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    memory = await service.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return _to_response(memory)


@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: UUID,
    body: MemoryUpdate,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    memory = await service.update_memory(memory_id, body, api_key_id=None)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return _to_response(memory)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: UUID,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    if not await service.delete_memory(memory_id, api_key_id=None):
        raise HTTPException(status_code=404, detail="Memory not found")


@router.post("/search", response_model=list[MemoryResponse])
async def search_memories(
    body: MemorySearchRequest,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    memories = await service.search_memories(body)
    return [_to_response(m) for m in memories]


@router.post("/batch", response_model=list[MemoryResponse], status_code=status.HTTP_201_CREATED)
async def batch_create(
    body: MemoryBatchCreate,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    results = []
    for entry in body.entries:
        memory = await service.create_memory(entry, api_key_id=None)
        results.append(_to_response(memory))
    return results


@router.post("/{memory_id}/merge", response_model=MemoryResponse)
async def merge_memory(
    memory_id: UUID,
    body: MemoryMergeRequest,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    memory = await service.merge_memories(memory_id, body.target_id, api_key_id=None)
    if not memory:
        raise HTTPException(status_code=404, detail="One or both memories not found")
    return _to_response(memory)


@router.get("/{memory_id}/duplicates")
async def find_duplicates(
    memory_id: UUID,
    threshold: float = 0.9,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    duplicates = await service.find_duplicates(memory_id, threshold)
    return duplicates

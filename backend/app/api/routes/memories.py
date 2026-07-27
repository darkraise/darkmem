from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.auth import require_auth
from app.api.deps import get_memory_service
from app.api.mcp.client_identity import ORIGIN_HEADER, resolve_origin_key
from app.models.memory import Memory
from app.schemas.memory import CaptureAck, MemoryBatchCreate, MemoryBulkDelete, MemoryBulkDeleteResponse, MemoryCreate, MemoryMergeRequest, MemoryResponse, MemorySearchRequest, MemoryUpdate, PaginatedMemoryResponse
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
        llm_classified_type=memory.classified_type,
        llm_summary=memory.summary,
        llm_emotions=memory.emotions,
        llm_flags=memory.flags,
        project=memory.project,
        status=memory.status,
        superseded_by=memory.superseded_by,
        technologies=list(memory.technologies or []),
        confidence=memory.confidence,
    )


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    body: MemoryCreate,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    memory = await service.create_memory(body, api_key_id=None)
    return _to_response(memory)


def _resolve_capture_origin_key(entry: MemoryCreate, request: Request) -> str:
    # Reuses T1.11's resolution verbatim (doc 05 §2.1) rather than
    # reimplementing the declared-identity/merge-to-one chain: an explicit
    # body field wins, then the X-Darkmem-Origin header, then the coarse
    # per-(source, project) fallback. `ctx=None` here is fine — the MCP
    # `ctx`-based header lookup this function was written for is bypassed by
    # resolving the header ourselves, since a REST call has no MCP Context.
    return resolve_origin_key(
        entry.origin_key or request.headers.get(ORIGIN_HEADER),
        None, source=entry.source, project=entry.project or "default",
    )


@router.post("/capture", response_model=CaptureAck, status_code=status.HTTP_202_ACCEPTED)
async def capture_memory(
    body: MemoryCreate,
    request: Request,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    """Tier-A synchronous accept (doc 05 §2): durably buffer the capture and
    hand back its pre-minted memory id. No embedding, extraction, or
    classification runs on this path. ``POST /memories`` still runs the
    pipeline inline until the buffer flush (T1.13) and the interactive
    `wait_process` bypass (T1.14) land behind it."""
    project = body.project or "default"
    resolved = body.model_copy(update={
        "project": project,
        "origin_key": _resolve_capture_origin_key(body, request),
    })
    return await service.accept_capture(resolved, api_key_id=None)


@router.post("/capture/batch", response_model=list[CaptureAck], status_code=status.HTTP_202_ACCEPTED)
async def capture_memory_batch(
    body: MemoryBatchCreate,
    request: Request,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    # Resolved per entry but against the SAME request, mirroring
    # memory_batch_add: an undeclared batch of N collapses to one origin,
    # never N counterfeit ones (doc 05 §2.1).
    entries = [
        entry.model_copy(update={
            "project": entry.project or "default",
            "origin_key": _resolve_capture_origin_key(entry, request),
        })
        for entry in body.entries
    ]
    return await service.accept_capture_batch(entries, api_key_id=None)


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
    resp = _to_response(memory)
    crossrefs = await service.get_crossrefs(memory_id)
    resp.related_memories = crossrefs
    return resp


@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: UUID,
    body: MemoryUpdate,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    # 'superseded' requires an atomically-set superseded_by (enforced by
    # chk_superseded_has_pointer) and is only ever produced by the pipeline's
    # detect_supersessions. Setting it through this generic update would violate
    # the CHECK and 500, so reject it here.
    if body.status == "superseded":
        raise HTTPException(
            status_code=400,
            detail="status 'superseded' is managed by the pipeline and cannot be set directly",
        )
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


@router.post("/delete", response_model=MemoryBulkDeleteResponse)
async def bulk_delete(
    body: MemoryBulkDelete,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    """Delete multiple memories in one request (processed server-side in series
    to avoid the deadlock that concurrent per-row deletes hit on shared graph
    rows). Missing ids are reported, not fatal."""
    result = await service.bulk_delete_memories(body.ids, api_key_id=None)
    return MemoryBulkDeleteResponse(**result)


@router.post("/search", response_model=list[MemoryResponse])
async def search_memories(
    body: MemorySearchRequest,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    memories = await service.search_memories(body)
    return [_to_response(m) for m in memories]


@router.post("/search/paginated", response_model=PaginatedMemoryResponse)
async def search_memories_paginated(
    body: MemorySearchRequest,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    result = await service.search_memories_paginated(body)
    return PaginatedMemoryResponse(
        items=[_to_response(m) for m in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.post("/batch", response_model=list[MemoryResponse], status_code=status.HTTP_201_CREATED)
async def batch_create(
    body: MemoryBatchCreate,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    memories = await service.batch_create_memories(body.entries, api_key_id=None)
    return [_to_response(m) for m in memories]


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

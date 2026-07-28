from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.api.auth import require_auth
from app.api.deps import get_memory_service
from app.api.mcp.client_identity import (
    ORIGIN_HEADER,
    REST_FALLBACK_SOURCE,
    resolve_client_source,
    resolve_entry_identity,
    resolve_origin_key,
    resolve_source_agent,
)
from app.models.memory import Memory
from app.schemas.memory import MemoryBatchCreate, MemoryBulkDelete, MemoryBulkDeleteResponse, MemoryCreate, MemoryLineageEntry, MemoryMergeRequest, MemoryResponse, MemorySearchRequest, MemoryUpdate, PaginatedMemoryResponse
from app.schemas.reason import ReasonRequest, ReasonResponse
from app.schemas.retrieval_trace import MemoryResultTrace
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
        classified_type=memory.classified_type,
        summary=memory.summary,
        emotions=memory.emotions,
        flags=memory.flags,
        project=memory.project,
        status=memory.status,
        superseded_by=memory.superseded_by,
        technologies=list(memory.technologies or []),
        confidence=memory.confidence,
    )


async def _json_body(request: Request):
    try:
        return await request.json()
    except ValueError:
        raise RequestValidationError(
            [{"type": "json_invalid", "loc": ("body",), "msg": "malformed JSON body", "input": None}]
        )


def _validated(model, raw):
    """Validate a hand-read body into ``model``, keeping FastAPI's 422.

    A raw ``ValidationError`` escaping a route body is a 500; converting it to
    ``RequestValidationError`` is what keeps a malformed batch answering with
    the same error envelope as every other malformed request.
    """
    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors())


def _resolve_request_origin_key(entry: MemoryCreate, request: Request, source: str) -> str:
    # Reuses T1.11's resolution verbatim (doc 05 §2.1) rather than
    # reimplementing the declared-identity/merge-to-one chain: an explicit
    # body field wins, then the X-Darkmem-Origin header, then the coarse
    # per-(source, project) fallback. `ctx=None` here is fine — the MCP
    # `ctx`-based header lookup this function was written for is bypassed by
    # resolving the header ourselves, since a REST call has no MCP Context.
    #
    # `source` is the *resolved* label, never `entry.source`: origin_key's own
    # logic is unchanged, but feeding it the unresolved body field is what made
    # every REST fallback key read `unknown:api:<project>` no matter which
    # client sent the request. It must be resolved before this call, so the
    # coarse fallback can never mint `unknown:None:<project>`.
    return resolve_origin_key(
        entry.origin_key or request.headers.get(ORIGIN_HEADER),
        None, source=source, project=entry.project or "default",
    )


@router.post("")
async def create_memory(
    body: MemoryCreate,
    request: Request,
    response: Response,
    wait_process: bool = False,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    """Tier-A buffered accept (doc 05 §2): durably buffers the capture and
    hands back its pre-minted memory id — a 202 accept by default. Pass
    ``wait_process=true`` to drive that row's flush inline instead, bounded by
    ``buffer_wait_timeout_seconds`` (doc 05 §2.2, T1.14); on settling in time
    this returns the fully processed memory (201) rather than the ack, and on
    timeout it degrades to the plain 202 — the row is already durably
    buffered either way."""
    project = body.project or "default"
    source = resolve_client_source(
        body.source, headers=request.headers, fallback=REST_FALLBACK_SOURCE,
    )
    resolved = body.model_copy(update={
        "project": project,
        "source": source,
        "source_agent": resolve_source_agent(body.source_agent, headers=request.headers),
        "origin_key": _resolve_request_origin_key(body, request, source),
    })
    result = await service.create_memory(resolved, api_key_id=None, wait_process=wait_process)
    if result.memory is not None:
        response.status_code = status.HTTP_201_CREATED
        return _to_response(result.memory)
    response.status_code = status.HTTP_202_ACCEPTED
    return result.ack


@router.post("/reason", response_model=ReasonResponse)
async def reason(
    body: ReasonRequest,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    result = await service.reason(body.question, limit=body.limit, project=body.project)
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
    # `service.get_memory` always attaches `predecessors` (possibly `[]`,
    # never absent) — see MemoryService.get_memory. Building the response
    # list explicitly here, rather than reusing the attribute as-is, is what
    # coerces each ORM row into MemoryLineageEntry's declared shape.
    resp.predecessors = [
        MemoryLineageEntry(
            id=predecessor.id,
            content=predecessor.content,
            created_at=predecessor.created_at,
            status=predecessor.status,
        )
        for predecessor in memory.predecessors
    ]
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
    request: Request,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    result = await service.search_memories_paginated(body, headers=request.headers)
    if body.with_trace:
        items = []
        for row in result["items"]:
            resp = _to_response(row.memory)
            resp.trace = MemoryResultTrace(
                scores=row.scores,
                rank_fusion_factor=row.rank_fusion_factor,
                rank_fusion_breakdown=row.rank_fusion_breakdown,
            )
            items.append(resp)
        return PaginatedMemoryResponse(
            items=items,
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"],
            envelope=result["envelope"],
        )
    return PaginatedMemoryResponse(
        items=[_to_response(m) for m in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.post("/batch")
async def batch_create(
    request: Request,
    response: Response,
    wait_process: bool = False,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    """Batch counterpart of ``POST /memories`` — one 202-buffered accept per
    entry by default; ``wait_process=true`` drives the whole batch's flush
    inline as a single ``process_batch`` call (never one per entry).

    Body: ``MemoryBatchCreate`` — validated below rather than by a signature
    annotation, because identity resolution reads the **raw** entry dicts.
    Whatever the schema's defaults are, the raw dict is what the caller
    actually sent, and it is the only thing an absent-versus-explicit
    ``source`` distinction can be read from. The MCP batch door runs the same
    helper on the same shape.
    """
    raw = await _json_body(request)
    if isinstance(raw, dict) and isinstance(raw.get("entries"), list):
        raw = {
            **raw,
            "entries": [
                resolve_entry_identity(
                    entry, headers=request.headers, fallback=REST_FALLBACK_SOURCE,
                )
                for entry in raw["entries"]
            ],
        }
    body = _validated(MemoryBatchCreate, raw)
    entries = [
        entry.model_copy(update={"project": entry.project or "default"})
        for entry in body.entries
    ]
    results = await service.batch_create_memories(entries, api_key_id=None, wait_process=wait_process)
    response.status_code = (
        status.HTTP_201_CREATED
        if wait_process and all(r.memory is not None for r in results)
        else status.HTTP_202_ACCEPTED
    )
    return [
        _to_response(r.memory) if r.memory is not None else r.ack
        for r in results
    ]


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

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.auth import require_auth, require_auth_for_stream
from app.api.deps import ChatServiceDep, get_chat_service_for_stream, refuse_when_read_only
from app.schemas.chat import (
    CompletionRequest,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
)
from app.services.chat import ChatService

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# ── Conversation CRUD ─────────────────────────────────

@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    archived: bool = False,
    _user=Depends(require_auth),
    service: ChatService = ChatServiceDep,
):
    rows = await service.list_conversations(limit=limit, offset=offset, archived=archived)
    return ConversationListResponse(
        conversations=[
            ConversationResponse(
                id=r["id"],
                title=r["title"],
                created_at=r["created_at"].isoformat(),
                updated_at=r["updated_at"].isoformat(),
                is_archived=r["is_archived"],
                message_count=r["message_count"],
            )
            for r in rows
        ]
    )


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    _user=Depends(require_auth),
    service: ChatService = ChatServiceDep,
):
    conv = await service.create_conversation(title=body.title)
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        is_archived=conv.is_archived,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    _user=Depends(require_auth),
    service: ChatService = ChatServiceDep,
):
    conv = await service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetailResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                context=m.context,
                created_at=m.created_at.isoformat(),
            )
            for m in conv.messages
        ],
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: uuid.UUID,
    body: ConversationUpdate,
    _user=Depends(require_auth),
    service: ChatService = ChatServiceDep,
):
    conv = await service.update_conversation(
        conversation_id, title=body.title, is_archived=body.is_archived
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        is_archived=conv.is_archived,
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    _user=Depends(require_auth),
    service: ChatService = ChatServiceDep,
):
    deleted = await service.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")


# ── Streaming Chat Completion ─────────────────────────

@router.post("/completions")
async def chat_completion(
    body: CompletionRequest,
    _user=Depends(require_auth_for_stream),
    _read_only=Depends(refuse_when_read_only),
    service: ChatService = Depends(get_chat_service_for_stream),
) -> StreamingResponse:
    context = body.context.model_dump(exclude_none=True) if body.context else None

    async def event_stream():
        async for event in service.send_message(
            conversation_id=body.conversation_id,
            content=body.content,
            context=context,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

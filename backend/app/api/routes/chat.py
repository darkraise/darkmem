import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.auth import require_auth
from app.api.deps import get_chat_service
from app.services.chat import ChatService

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# ── Schemas ───────────────────────────────────────────

class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None
    is_archived: bool | None = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: str
    updated_at: str
    is_archived: bool
    message_count: int = 0


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    context: dict | None
    created_at: str


class ConversationDetailResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: str
    updated_at: str
    messages: list[MessageResponse]


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]


class CompletionRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    content: str
    context: dict | None = Field(default=None)


# ── Conversation CRUD ─────────────────────────────────

@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    archived: bool = False,
    _user=Depends(require_auth),
    service: ChatService = Depends(get_chat_service),
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
    service: ChatService = Depends(get_chat_service),
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
    service: ChatService = Depends(get_chat_service),
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
    service: ChatService = Depends(get_chat_service),
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
    service: ChatService = Depends(get_chat_service),
):
    deleted = await service.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")


# ── Streaming Chat Completion ─────────────────────────

@router.post("/completions")
async def chat_completion(
    body: CompletionRequest,
    _user=Depends(require_auth),
    service: ChatService = Depends(get_chat_service),
):
    async def event_stream():
        async for event in service.send_message(
            conversation_id=body.conversation_id,
            content=body.content,
            context=body.context,
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

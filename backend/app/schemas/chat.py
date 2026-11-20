import uuid

from pydantic import BaseModel, Field


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


class ChatContext(BaseModel):
    """The keys `ChatService` reads off a turn's context; others are ignored."""

    mentions: list[str] = Field(default_factory=list)
    project: str | None = None
    selected_node_id: str | None = None
    selected_entity_id: str | None = None


class CompletionRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    content: str = Field(max_length=32000)
    context: ChatContext | None = None

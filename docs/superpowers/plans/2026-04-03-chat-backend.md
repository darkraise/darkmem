# Chat Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full chat backend with persistent conversations, SSE streaming responses, and dual retrieval (vector search + knowledge graph) for RAG.

**Architecture:** New `conversations` and `messages` PostgreSQL tables, a `ChatService` that orchestrates retrieval and streaming, and REST + SSE endpoints. Follows the existing service/repository/route pattern.

**Tech Stack:** FastAPI, SQLAlchemy (async), PostgreSQL, Qdrant, Neo4j, httpx (streaming), SSE

**Spec:** `docs/superpowers/specs/2026-04-03-chat-backend-design.md`

---

### Task 1: Database Models for Conversation and Message

**Files:**
- Create: `backend/app/models/chat.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create the chat models file**

```python
# backend/app/models/chat.py
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="selectin",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
```

- [ ] **Step 2: Register models in __init__.py**

Add to `backend/app/models/__init__.py`:

```python
from app.models.chat import Conversation, Message  # noqa: F401
```

This ensures alembic's `Base.metadata` picks up the new tables.

- [ ] **Step 3: Generate alembic migration**

Run: `cd backend && alembic revision --autogenerate -m "add conversations and messages tables"`

Verify the generated migration has `create_table("conversations", ...)` and `create_table("messages", ...)` with the correct columns and foreign key.

- [ ] **Step 4: Apply migration**

Run: `cd backend && alembic upgrade head`

Expected: Tables created successfully.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/chat.py backend/app/models/__init__.py backend/migrations/versions/
git commit -m "feat(chat): add Conversation and Message database models"
```

---

### Task 2: Add Streaming to LLMOrchestrator

**Files:**
- Modify: `backend/app/services/llm.py`

- [ ] **Step 1: Add chat_completion_stream method**

Add this method to the `LLMOrchestrator` class after the existing `chat_completion` method:

```python
    async def chat_completion_stream(
        self,
        purpose: str,
        messages: list[dict],
    ):
        """Yields token strings as they arrive from the LLM."""
        cfg = self.config[purpose]
        headers = self._headers(cfg)

        body: dict = {"model": cfg.model, "messages": messages, "stream": True}
        for key, value in cfg.params.items():
            if key != "extra_body":
                body[key] = value
        if "extra_body" in cfg.params:
            body.update(cfg.params["extra_body"])

        async with self._client.stream(
            "POST",
            f"{cfg.base_url}/chat/completions",
            headers=headers,
            json=body,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    break
                import json
                chunk = json.loads(data)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield content
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/llm.py
git commit -m "feat(chat): add streaming chat_completion_stream to LLMOrchestrator"
```

---

### Task 3: Chat Service — Retrieval Pipeline and Streaming

**Files:**
- Create: `backend/app/services/chat.py`

- [ ] **Step 1: Create the chat service**

```python
# backend/app/services/chat.py
import re
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from sqlalchemy import select, func as sa_func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Conversation, Message
from app.services.llm import LLMOrchestrator
from app.repositories.vector import QdrantVectorRepository
from app.repositories.graph import Neo4jGraphRepository

SYSTEM_PROMPT = (
    "You are a knowledge assistant for a personal memory system called darkmem. "
    "Answer questions based on the retrieved memories and entity data provided below. "
    "When citing information, reference the memory source and content. "
    "If the retrieved context doesn't contain enough information to answer, say so honestly. "
    "Keep answers concise and well-structured. Use markdown formatting."
)

MENTION_RE = re.compile(r"@([\w./-]+)")
CLUSTER_RE = re.compile(r"@cluster:(\d+)")

MAX_HISTORY_MESSAGES = 20


class ChatService:
    def __init__(
        self,
        session: AsyncSession,
        llm: LLMOrchestrator,
        vector_repo: QdrantVectorRepository | None = None,
        graph_repo: Neo4jGraphRepository | None = None,
    ):
        self.session = session
        self.llm = llm
        self.vector_repo = vector_repo
        self.graph_repo = graph_repo

    # ── Conversation CRUD ─────────────────────────────────

    async def list_conversations(
        self, limit: int = 50, offset: int = 0, archived: bool = False
    ) -> list[dict]:
        stmt = (
            select(
                Conversation.id,
                Conversation.title,
                Conversation.created_at,
                Conversation.updated_at,
                Conversation.is_archived,
                sa_func.count(Message.id).label("message_count"),
            )
            .outerjoin(Message)
            .where(Conversation.is_archived == archived)
            .group_by(Conversation.id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "id": r.id,
                "title": r.title,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "is_archived": r.is_archived,
                "message_count": r.message_count,
            }
            for r in rows
        ]

    async def create_conversation(self, title: str | None = None) -> Conversation:
        conv = Conversation(title=title)
        self.session.add(conv)
        await self.session.flush()
        await self.session.refresh(conv)
        return conv

    async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation | None:
        return await self.session.get(Conversation, conversation_id)

    async def update_conversation(
        self, conversation_id: uuid.UUID, title: str | None = None, is_archived: bool | None = None
    ) -> Conversation | None:
        conv = await self.get_conversation(conversation_id)
        if not conv:
            return None
        if title is not None:
            conv.title = title
        if is_archived is not None:
            conv.is_archived = is_archived
        await self.session.flush()
        await self.session.refresh(conv)
        return conv

    async def delete_conversation(self, conversation_id: uuid.UUID) -> bool:
        conv = await self.get_conversation(conversation_id)
        if not conv:
            return False
        await self.session.delete(conv)
        await self.session.flush()
        return True

    # ── Chat Completion ───────────────────────────────────

    async def send_message(
        self,
        conversation_id: uuid.UUID | None,
        content: str,
        context: dict | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Yields SSE event dicts: {type, ...payload}"""

        # Create conversation if needed
        if conversation_id is None:
            conv = await self.create_conversation()
            conversation_id = conv.id
        else:
            conv = await self.get_conversation(conversation_id)
            if not conv:
                yield {"type": "error", "message": "Conversation not found"}
                return

        # Save user message
        user_msg = Message(conversation_id=conversation_id, role="user", content=content)
        self.session.add(user_msg)
        await self.session.flush()

        # Retrieve context
        retrieval = await self._retrieve(content, context)

        # Emit sources event
        yield {
            "type": "sources",
            "memories": retrieval["memories"],
            "entities": retrieval["entities"],
        }

        # Build LLM messages
        llm_messages = await self._build_prompt(conversation_id, content, retrieval)

        # Stream LLM response
        full_response = []
        async for token in self.llm.chat_completion_stream("reasoning", llm_messages):
            full_response.append(token)
            yield {"type": "token", "content": token}

        # Save assistant message
        assistant_content = "".join(full_response)
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            context={
                "memories": [
                    {"id": str(m["memory_id"]), "score": m["score"]}
                    for m in retrieval["raw_memories"]
                ],
                "entities": [
                    {"id": e.get("id", ""), "name": e["name"]}
                    for e in retrieval["entities"]
                ],
            },
        )
        self.session.add(assistant_msg)
        await self.session.flush()

        # Auto-title if first message
        if conv and not conv.title:
            conv.title = content[:60] + ("…" if len(content) > 60 else "")
            await self.session.flush()

        # Update conversation timestamp
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.now(timezone.utc))
        )
        await self.session.flush()

        yield {
            "type": "done",
            "message_id": str(assistant_msg.id),
            "conversation_id": str(conversation_id),
        }

    # ── Retrieval ─────────────────────────────────────────

    async def _retrieve(self, question: str, context: dict | None = None) -> dict:
        """Run vector search and graph lookup in parallel."""
        import asyncio

        context = context or {}
        mentions = set(MENTION_RE.findall(question))
        if context.get("mentions"):
            mentions.update(context["mentions"])

        # Vector search
        memories_task = self._search_memories(question)

        # Graph lookup
        entity_names = list(mentions - {m for m in mentions if m.startswith("cluster:")})
        graph_task = self._lookup_entities(
            entity_names,
            context.get("selected_entity_id"),
            context.get("selected_node_id"),
        )

        raw_memories, entities = await asyncio.gather(memories_task, graph_task)

        # Format memories for prompt
        formatted_memories = []
        for i, m in enumerate(raw_memories, 1):
            payload = m.get("payload", {})
            formatted_memories.append({
                "index": i,
                "content": payload.get("content", ""),
                "source": payload.get("source", ""),
                "tags": payload.get("tags", []),
                "score": round(m.get("score", 0), 3),
            })

        return {
            "memories": formatted_memories,
            "entities": entities,
            "raw_memories": raw_memories,
        }

    async def _search_memories(self, query: str, limit: int = 10) -> list[dict]:
        if not self.vector_repo:
            return []
        vector = await self.llm.embed(query)
        return await self.vector_repo.search(vector, limit=limit)

    async def _lookup_entities(
        self,
        entity_names: list[str],
        selected_entity_id: str | None = None,
        selected_node_id: str | None = None,
    ) -> list[dict]:
        if not self.graph_repo:
            return []

        entities = []

        if selected_entity_id:
            result = await self.graph_repo.get_neighbors_by_id(selected_entity_id)
            if result.get("entity"):
                entities.append(result["entity"])
                entities.extend(result.get("neighbors", [])[:5])

        for name in entity_names[:5]:
            found = await self.graph_repo.get_entities(name_query=name, limit=1)
            for e in found:
                if not any(ex.get("name") == e["name"] for ex in entities):
                    entities.append(e)
                    neighbors = await self.graph_repo.get_neighbors_by_id(e["id"])
                    for rel in neighbors.get("relations", [])[:5]:
                        entities.append({"_relation": True, **rel})

        return entities

    # ── Prompt Building ───────────────────────────────────

    async def _build_prompt(
        self, conversation_id: uuid.UUID, current_message: str, retrieval: dict
    ) -> list[dict]:
        messages: list[dict] = []

        # System prompt with retrieved context
        context_parts = [SYSTEM_PROMPT, "", "## Retrieved Memories", ""]
        for m in retrieval["memories"]:
            context_parts.append(
                f"[{m['index']}] (source: {m['source']}, tags: {', '.join(m['tags'])}, relevance: {m['score']})\n{m['content']}"
            )

        entity_facts = [e for e in retrieval["entities"] if not e.get("_relation")]
        relations = [e for e in retrieval["entities"] if e.get("_relation")]

        if entity_facts:
            context_parts.append("")
            context_parts.append("## Entity Knowledge")
            for e in entity_facts:
                context_parts.append(f"- {e.get('name', '?')} ({e.get('entity_type', '?')})")

        if relations:
            context_parts.append("")
            context_parts.append("## Entity Relationships")
            for r in relations:
                context_parts.append(f"- {r.get('source', '?')} --[{r.get('type', '?')}]--> {r.get('target', '?')}")

        messages.append({"role": "system", "content": "\n".join(context_parts)})

        # Conversation history
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(MAX_HISTORY_MESSAGES + 1)
        )
        history = list(reversed((await self.session.execute(stmt)).scalars().all()))

        # Skip the last message (it's the current user message we just saved)
        for msg in history[:-1]:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": current_message})
        return messages
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/chat.py
git commit -m "feat(chat): add ChatService with retrieval pipeline and streaming"
```

---

### Task 4: API Routes — Conversation CRUD

**Files:**
- Create: `backend/app/api/routes/chat.py`
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add chat service dependency**

Add to `backend/app/api/deps.py`:

```python
from app.services.chat import ChatService


async def get_chat_service(request: Request, session: AsyncSession = Depends(get_session)) -> ChatService:
    llm = getattr(request.app.state, "llm", None)
    vector_repo = getattr(request.app.state, "vector_repo", None)
    graph_repo = getattr(request.app.state, "graph_repo", None)
    if not llm:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="LLM service unavailable")
    return ChatService(session, llm, vector_repo, graph_repo)
```

- [ ] **Step 2: Create the chat routes file with CRUD endpoints**

```python
# backend/app/api/routes/chat.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
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


# ── Endpoints ─────────────────────────────────────────

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
```

- [ ] **Step 3: Register the chat router in main.py**

Add to `backend/app/main.py` after the other router imports:

```python
from app.api.routes import chat
```

And after the other `app.include_router(...)` calls:

```python
app.include_router(chat.router)
```

- [ ] **Step 4: Verify server starts**

Run: `cd backend && python -m uvicorn app.main:app --reload`

Expected: Server starts without import errors. Visit `http://localhost:8000/docs` to see the new chat endpoints.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/chat.py backend/app/api/deps.py backend/app/main.py
git commit -m "feat(chat): add conversation CRUD API endpoints"
```

---

### Task 5: API Route — Streaming Chat Completion

**Files:**
- Modify: `backend/app/api/routes/chat.py`

- [ ] **Step 1: Add the streaming completions endpoint**

Add these imports at the top of `backend/app/api/routes/chat.py`:

```python
import json
from fastapi.responses import StreamingResponse
```

Add this schema after the existing schemas:

```python
class CompletionRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    content: str
    context: dict | None = Field(default=None)
```

Add this endpoint after the existing endpoints:

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/routes/chat.py
git commit -m "feat(chat): add SSE streaming chat completions endpoint"
```

---

### Task 6: Tests — Chat Models and Service

**Files:**
- Create: `backend/tests/test_chat.py`

- [ ] **Step 1: Write chat tests**

```python
# backend/tests/test_chat.py
import pytest
import pytest_asyncio
from app.models.chat import Conversation, Message
from app.services.chat import ChatService, MENTION_RE


class TestChatModels:
    @pytest.mark.asyncio
    async def test_create_conversation(self, session):
        conv = Conversation(title="Test Chat")
        session.add(conv)
        await session.flush()
        assert conv.id is not None
        assert conv.title == "Test Chat"
        assert conv.is_archived is False

    @pytest.mark.asyncio
    async def test_create_message(self, session):
        conv = Conversation()
        session.add(conv)
        await session.flush()

        msg = Message(conversation_id=conv.id, role="user", content="Hello")
        session.add(msg)
        await session.flush()
        assert msg.id is not None
        assert msg.role == "user"

    @pytest.mark.asyncio
    async def test_cascade_delete(self, session):
        conv = Conversation()
        session.add(conv)
        await session.flush()

        msg = Message(conversation_id=conv.id, role="user", content="Hello")
        session.add(msg)
        await session.flush()

        await session.delete(conv)
        await session.flush()

        result = await session.get(Message, msg.id)
        assert result is None


class TestMentionParsing:
    def test_extract_entity_mentions(self):
        matches = MENTION_RE.findall("What about @PostgreSQL and @Docker?")
        assert "PostgreSQL" in matches
        assert "Docker" in matches

    def test_extract_cluster_mentions(self):
        from app.services.chat import CLUSTER_RE
        match = CLUSTER_RE.search("Tell me about @cluster:3")
        assert match is not None
        assert match.group(1) == "3"

    def test_no_mentions(self):
        matches = MENTION_RE.findall("Just a normal question")
        assert len(matches) == 0


class TestChatServiceCRUD:
    @pytest_asyncio.fixture
    async def chat_service(self, session):
        from unittest.mock import AsyncMock
        llm = AsyncMock()
        return ChatService(session, llm)

    @pytest.mark.asyncio
    async def test_create_and_list_conversations(self, chat_service):
        await chat_service.create_conversation(title="Chat 1")
        await chat_service.create_conversation(title="Chat 2")
        convs = await chat_service.list_conversations()
        assert len(convs) >= 2

    @pytest.mark.asyncio
    async def test_update_conversation_title(self, chat_service):
        conv = await chat_service.create_conversation(title="Old")
        updated = await chat_service.update_conversation(conv.id, title="New")
        assert updated.title == "New"

    @pytest.mark.asyncio
    async def test_delete_conversation(self, chat_service):
        conv = await chat_service.create_conversation()
        deleted = await chat_service.delete_conversation(conv.id)
        assert deleted is True
        result = await chat_service.get_conversation(conv.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, chat_service):
        import uuid
        deleted = await chat_service.delete_conversation(uuid.uuid4())
        assert deleted is False
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/test_chat.py -v`

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_chat.py
git commit -m "test(chat): add tests for chat models, mention parsing, and CRUD"
```

---

### Task 7: Tests — Chat API Endpoints

**Files:**
- Create: `backend/tests/test_api/test_chat_api.py`

- [ ] **Step 1: Write API integration tests**

```python
# backend/tests/test_api/test_chat_api.py
import pytest


class TestConversationAPI:
    @pytest.mark.asyncio
    async def test_create_conversation(self, client, auth_headers):
        resp = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Test Convo"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Convo"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_conversations(self, client, auth_headers):
        await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Convo A"},
            headers=auth_headers,
        )
        resp = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["conversations"]) >= 1

    @pytest.mark.asyncio
    async def test_get_conversation_detail(self, client, auth_headers):
        create_resp = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Detail Test"},
            headers=auth_headers,
        )
        conv_id = create_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/chat/conversations/{conv_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Detail Test"
        assert "messages" in data

    @pytest.mark.asyncio
    async def test_update_conversation(self, client, auth_headers):
        create_resp = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Old Title"},
            headers=auth_headers,
        )
        conv_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/chat/conversations/{conv_id}",
            json={"title": "New Title"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    @pytest.mark.asyncio
    async def test_delete_conversation(self, client, auth_headers):
        create_resp = await client.post(
            "/api/v1/chat/conversations",
            json={},
            headers=auth_headers,
        )
        conv_id = create_resp.json()["id"]
        resp = await client.delete(
            f"/api/v1/chat/conversations/{conv_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, client, auth_headers):
        resp = await client.get(
            "/api/v1/chat/conversations/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_requires_auth(self, client):
        resp = await client.get("/api/v1/chat/conversations")
        assert resp.status_code == 401
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/test_api/test_chat_api.py -v`

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_api/test_chat_api.py
git commit -m "test(chat): add API integration tests for conversation CRUD"
```

---

### Task 8: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v --tb=short`

Expected: All existing tests still pass, plus the new chat tests.

- [ ] **Step 2: Run type check (if mypy configured)**

Run: `cd backend && python -m mypy app/services/chat.py app/api/routes/chat.py app/models/chat.py --ignore-missing-imports 2>&1 | head -20`

Expected: No critical type errors.

- [ ] **Step 3: Manual smoke test**

Start the server: `cd backend && python -m uvicorn app.main:app --reload`

Test conversation CRUD:
```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"password":"your-password"}' | jq -r '.access_token')

# Create conversation
curl -s -X POST http://localhost:8000/api/v1/chat/conversations -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"title":"Test"}' | jq

# List conversations
curl -s http://localhost:8000/api/v1/chat/conversations -H "Authorization: Bearer $TOKEN" | jq

# Test streaming (will fail if LLM not running, but should return SSE format)
curl -N -X POST http://localhost:8000/api/v1/chat/completions -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"content":"What do you know about darkmem?"}'
```

- [ ] **Step 4: Commit any fixes**

```bash
git add -u backend/
git commit -m "chore(chat): final fixes from verification"
```

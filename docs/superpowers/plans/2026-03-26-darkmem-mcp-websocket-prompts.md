# darkmem MCP + WebSocket + Prompts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add MCP server (StreamableHTTP), WebSocket live events, system prompt profiles with seed data, and a RAG-based reason endpoint.

**Architecture:** MCP server is a FastMCP instance mounted at `/mcp` on the existing FastAPI app. WebSocket uses a global EventManager for broadcasting. System prompt profiles are seeded into Postgres on first startup. The reason endpoint performs RAG: embed query → search Qdrant → build context → ask LLM.

**Tech Stack:** mcp[server] (FastMCP, StreamableHTTP), FastAPI WebSocket, asyncio

---

## Prerequisites

- Plans 1 and 2 complete (54 tests passing)
- PostgreSQL on localhost:5433, Qdrant on localhost:6333, Neo4j on localhost:7687

---

## File Structure

```
backend/
├── pyproject.toml                          # MODIFY: add mcp[server]
├── app/
│   ├── main.py                             # MODIFY: mount MCP, init WebSocket, seed prompts
│   ├── api/
│   │   ├── websocket.py                    # CREATE: EventManager + WS endpoint
│   │   ├── mcp/
│   │   │   ├── __init__.py                 # CREATE
│   │   │   └── server.py                   # CREATE: FastMCP with all tools
│   │   └── routes/
│   │       ├── memories.py                 # MODIFY: add reason endpoint
│   │       └── config.py                   # MODIFY: add system-prompt endpoint
│   ├── services/
│   │   ├── memory.py                       # MODIFY: add reason method
│   │   └── pipeline.py                     # MODIFY: emit WebSocket events
│   └── db/
│       └── seed.py                         # CREATE: seed system prompt profiles
├── tests/
│   ├── test_websocket.py                   # CREATE
│   ├── test_api/
│   │   └── test_reason.py                  # CREATE
│   └── test_mcp.py                         # CREATE
```

---

### Task 1: WebSocket Event Manager

**Files:**
- Create: `backend/app/api/websocket.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/pipeline.py`
- Create: `backend/tests/test_websocket.py`

- [ ] **Step 1: Write WebSocket tests — `backend/tests/test_websocket.py`**

```python
import asyncio

from app.api.websocket import EventManager


async def test_event_manager_broadcast():
    manager = EventManager()

    received = []

    class MockWS:
        async def accept(self):
            pass
        async def send_text(self, data):
            received.append(data)

    ws = MockWS()
    await manager.connect(ws)
    await manager.broadcast("memory.created", {"id": "123"})

    assert len(received) == 1
    assert "memory.created" in received[0]


async def test_event_manager_disconnect():
    manager = EventManager()

    class MockWS:
        async def accept(self):
            pass
        async def send_text(self, data):
            pass

    ws = MockWS()
    await manager.connect(ws)
    assert len(manager.connections) == 1

    manager.disconnect(ws)
    assert len(manager.connections) == 0
```

- [ ] **Step 2: Create `backend/app/api/websocket.py`**

```python
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class EventManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, event_type: str, data: dict):
        message = json.dumps({"event": event_type, "data": data})
        for ws in self.connections[:]:
            try:
                await ws.send_text(message)
            except Exception:
                self.connections.remove(ws)


event_manager = EventManager()


async def websocket_endpoint(ws: WebSocket):
    await event_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        event_manager.disconnect(ws)
```

- [ ] **Step 3: Update `backend/app/services/pipeline.py` — emit events**

Add `event_manager` import and emit events after processing. Add these lines after successful operations:

At the top, add:
```python
from app.api.websocket import event_manager
```

In `process_memory`, after successful embedding+extraction, add before the final except:
```python
        await event_manager.broadcast("pipeline.completed", {"memory_id": str(memory_id)})
```

In `delete_memory`, after the gather:
```python
        await event_manager.broadcast("memory.deleted", {"memory_id": str(memory_id)})
```

- [ ] **Step 4: Add WebSocket route to `backend/app/main.py`**

Add import:
```python
from app.api.websocket import websocket_endpoint
```

After the router includes, add:
```python
app.add_api_websocket_route("/ws", websocket_endpoint)
```

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_websocket.py -v`
Expected: 2 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/websocket.py backend/app/services/pipeline.py backend/app/main.py backend/tests/test_websocket.py
git commit -m "feat: add WebSocket event manager with live broadcasting"
```

---

### Task 2: System Prompt Profiles + Seed Data

**Files:**
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/seed.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/routes/config.py`
- Create: `backend/app/schemas/prompt.py`

- [ ] **Step 1: Create `backend/app/schemas/prompt.py`**

```python
from pydantic import BaseModel


class SystemPromptResponse(BaseModel):
    name: str
    display_name: str
    content: str
    extraction_depth: str
    is_default: bool

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create `backend/app/db/__init__.py`** — empty

- [ ] **Step 3: Create `backend/app/db/seed.py`**

```python
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import SystemPromptProfile

logger = logging.getLogger(__name__)

PROFILES = [
    {
        "name": "default",
        "display_name": "Default",
        "content": """You have access to a centralized memory system. Use it to store and retrieve important context.

## When to save
- Decisions and their reasoning
- User preferences and corrections
- Infrastructure details (IPs, ports, services)
- Debugging insights and root causes
- Project context (deadlines, people, constraints)

## When to search
- At the start of conversations for relevant context
- When working on unfamiliar code or systems
- Before making architectural decisions

## Tagging
Use slash-separated tags: project/<name>, infra/<component>, user/preferences, debug/root-cause""",
        "save_triggers": {"decisions": True, "preferences": True, "infrastructure": True, "debugging": True},
        "search_behavior": {"on_start": True, "on_unfamiliar": True, "frequency": "balanced"},
        "tagging_conventions": {"prefixes": ["project", "infra", "user", "debug", "workflow"]},
        "extraction_depth": "full",
        "dedup_strategy": {"threshold": 0.9, "auto_merge": False},
        "is_default": True,
    },
    {
        "name": "coding-assistant",
        "display_name": "Coding Assistant",
        "content": """You have access to a centralized memory system optimized for software development.

## When to save
- Architectural decisions and trade-offs
- Debugging insights: what failed and why
- Code patterns and conventions specific to this project
- User corrections to your behavior
- Cross-session context (what was started but not finished)

## When to search
- At conversation start: search for project context
- When touching unfamiliar code areas
- Before proposing architectural changes
- When debugging: search for past similar issues

## Tagging
- project/<repo-name> — always include
- debug/root-cause, debug/workaround
- project/decisions, project/architecture
- feedback/behavior, feedback/style""",
        "save_triggers": {"decisions": True, "preferences": True, "debugging": True, "architecture": True, "corrections": True},
        "search_behavior": {"on_start": True, "on_unfamiliar": True, "frequency": "aggressive"},
        "tagging_conventions": {"prefixes": ["project", "debug", "feedback", "workflow"]},
        "extraction_depth": "full",
        "dedup_strategy": {"threshold": 0.85, "auto_merge": False},
        "is_default": False,
    },
    {
        "name": "devops-agent",
        "display_name": "DevOps Agent",
        "content": """You have access to a centralized memory system optimized for infrastructure work.

## When to save
- Service configurations, IPs, ports
- Networking topology and routing rules
- Incident root causes and resolutions
- Configuration gotchas and workarounds
- Version incompatibilities encountered

## When to search
- Before modifying any service configuration
- When debugging infrastructure issues
- When setting up new services

## Tagging
- infra/services, infra/networking, infra/environment
- debug/root-cause, debug/workaround, debug/gotcha
- workflow/migration, workflow/performance""",
        "save_triggers": {"infrastructure": True, "debugging": True, "networking": True, "incidents": True},
        "search_behavior": {"on_start": True, "on_unfamiliar": True, "frequency": "aggressive"},
        "tagging_conventions": {"prefixes": ["infra", "debug", "workflow"]},
        "extraction_depth": "full",
        "dedup_strategy": {"threshold": 0.9, "auto_merge": False},
        "is_default": False,
    },
    {
        "name": "research-agent",
        "display_name": "Research Agent",
        "content": """You have access to a centralized memory system optimized for knowledge gathering.

## When to save
- Facts and findings from research
- Sources and references
- Summaries of long documents
- Comparisons and evaluations

## When to search
- Always search before saving to avoid duplicates
- Search for existing knowledge before researching

## Tagging
- research/findings, research/sources
- project/<topic>""",
        "save_triggers": {"facts": True, "sources": True, "summaries": True},
        "search_behavior": {"on_start": True, "before_save": True, "frequency": "aggressive"},
        "tagging_conventions": {"prefixes": ["research", "project"]},
        "extraction_depth": "full",
        "dedup_strategy": {"threshold": 0.8, "auto_merge": True},
        "is_default": False,
    },
    {
        "name": "automation",
        "display_name": "Automation",
        "content": """Centralized memory system for automated pipelines. Store structured data. Minimal LLM processing.

Save: pipeline results, job outputs, structured findings.
Search: by tags for specific data.
Tags: automation/<pipeline-name>, data/<type>""",
        "save_triggers": {"results": True, "outputs": True},
        "search_behavior": {"on_start": False, "frequency": "minimal"},
        "tagging_conventions": {"prefixes": ["automation", "data"]},
        "extraction_depth": "light",
        "dedup_strategy": {"threshold": 0.95, "auto_merge": False},
        "is_default": False,
    },
    {
        "name": "minimal",
        "display_name": "Minimal",
        "content": "Raw memory storage. No LLM processing. Store and retrieve content as-is.",
        "save_triggers": {},
        "search_behavior": {"on_start": False, "frequency": "none"},
        "tagging_conventions": {"prefixes": []},
        "extraction_depth": "none",
        "dedup_strategy": {"threshold": 1.0, "auto_merge": False},
        "is_default": False,
    },
]


async def seed_profiles(session: AsyncSession):
    for profile_data in PROFILES:
        existing = await session.execute(
            select(SystemPromptProfile).where(SystemPromptProfile.name == profile_data["name"])
        )
        if existing.scalar_one_or_none():
            continue

        profile = SystemPromptProfile(**profile_data)
        session.add(profile)
        logger.info(f"Seeded profile: {profile_data['name']}")

    await session.commit()
```

- [ ] **Step 4: Update `backend/app/main.py` — seed on startup**

In the lifespan function, after the pipeline initialization (before `yield`), add:

```python
    # Seed system prompt profiles
    from app.db.seed import seed_profiles
    from app.database import async_session_factory
    try:
        async with async_session_factory() as session:
            await seed_profiles(session)
        logger.info("System prompt profiles seeded")
    except Exception as e:
        logger.warning(f"Failed to seed profiles: {e}")
```

- [ ] **Step 5: Add system-prompt endpoint to `backend/app/api/routes/config.py`**

Add imports at top:
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.models.config import SystemPromptProfile
from app.schemas.prompt import SystemPromptResponse
```

Add endpoint:
```python
@router.get("/system-prompt", response_model=SystemPromptResponse)
async def get_system_prompt(
    profile: str = "default",
    _api_key=Depends(require_scope("read")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(SystemPromptProfile).where(SystemPromptProfile.name == profile)
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Profile '{profile}' not found")
    return SystemPromptResponse.model_validate(prompt)


@router.get("/system-prompt/list", response_model=list[SystemPromptResponse])
async def list_system_prompts(
    _api_key=Depends(require_scope("read")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(SystemPromptProfile).order_by(SystemPromptProfile.name))
    return [SystemPromptResponse.model_validate(p) for p in result.scalars().all()]
```

Also add missing imports: `HTTPException` from fastapi.

- [ ] **Step 6: Run all tests**

Run: `cd backend && pytest -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/db/ backend/app/schemas/prompt.py backend/app/api/routes/config.py backend/app/main.py
git commit -m "feat: add system prompt profiles with seed data"
```

---

### Task 3: Reason Endpoint (RAG)

**Files:**
- Modify: `backend/app/services/memory.py`
- Modify: `backend/app/api/routes/memories.py`
- Create: `backend/app/schemas/reason.py`
- Create: `backend/tests/test_api/test_reason.py`

- [ ] **Step 1: Create `backend/app/schemas/reason.py`**

```python
from pydantic import BaseModel


class ReasonRequest(BaseModel):
    question: str
    limit: int = 10


class ReasonResponse(BaseModel):
    answer: str
    sources: list[dict]
```

- [ ] **Step 2: Add `reason` method to `backend/app/services/memory.py`**

Add at the end of the MemoryService class:

```python
    async def reason(self, question: str, limit: int = 10) -> dict:
        if not self.pipeline:
            return {"answer": "Reasoning not available (no LLM pipeline configured)", "sources": []}

        # Step 1: Semantic search for relevant memories
        semantic_results = await self.pipeline.semantic_search(question, limit=limit)
        if not semantic_results:
            return {"answer": "No relevant memories found to answer this question.", "sources": []}

        # Step 2: Fetch full memory content
        sources = []
        context_parts = []
        for i, result in enumerate(semantic_results):
            memory = await self.memory_repo.get(result["memory_id"])
            if memory and not memory.is_archived:
                context_parts.append(f"[{i+1}] {memory.content}")
                sources.append({
                    "memory_id": str(memory.id),
                    "content": memory.content[:200],
                    "score": result["score"],
                    "tags": [t.name for t in memory.tags],
                })

        if not context_parts:
            return {"answer": "No relevant memories found.", "sources": []}

        # Step 3: Ask LLM with context
        context = "\n\n".join(context_parts)
        prompt = f"""Based on the following stored memories, answer the question.
If the memories don't contain enough information, say so.
Reference the memory numbers [1], [2], etc. when citing sources.

Memories:
{context}

Question: {question}"""

        answer = await self.pipeline.llm.chat_completion(
            "reasoning",
            messages=[
                {"role": "system", "content": "You are a knowledge retrieval assistant. Answer questions using only the provided memory context. Be concise and accurate."},
                {"role": "user", "content": prompt},
            ],
        )

        return {"answer": answer, "sources": sources}
```

- [ ] **Step 3: Add reason route to `backend/app/api/routes/memories.py`**

Add imports:
```python
from app.schemas.reason import ReasonRequest, ReasonResponse
```

Add route (can go at the end, before any path-parameter routes to avoid conflicts):
```python
@router.post("/reason", response_model=ReasonResponse)
async def reason(
    body: ReasonRequest,
    api_key: ApiKey = Depends(require_scope("read")),
    service: MemoryService = Depends(get_memory_service),
):
    result = await service.reason(body.question, limit=body.limit)
    return ReasonResponse(**result)
```

**IMPORTANT:** This route MUST be defined BEFORE routes with `{memory_id}` path parameters, otherwise `/reason` would be captured by `/{memory_id}`. Move it above `get_memory`.

- [ ] **Step 4: Write tests — `backend/tests/test_api/test_reason.py`**

```python
async def test_reason_without_pipeline(client, auth_headers):
    response = await client.post(
        "/api/v1/memories/reason",
        json={"question": "What is darkmem?"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert data["sources"] == []


async def test_reason_requires_auth(client):
    response = await client.post("/api/v1/memories/reason", json={"question": "test"})
    assert response.status_code in (401, 403)
```

- [ ] **Step 5: Run all tests**

Run: `cd backend && pytest -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/reason.py backend/app/services/memory.py backend/app/api/routes/memories.py backend/tests/test_api/test_reason.py
git commit -m "feat: add RAG-based reason endpoint"
```

---

### Task 4: MCP Server

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/app/api/mcp/__init__.py`
- Create: `backend/app/api/mcp/server.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_mcp.py`

- [ ] **Step 1: Add MCP dependency to `backend/pyproject.toml`**

Add to dependencies:
```toml
    "mcp[server]>=1.9.0",
```

Run: `cd backend && pip install -e ".[dev]"`

- [ ] **Step 2: Create `backend/app/api/mcp/__init__.py`** — empty

- [ ] **Step 3: Create `backend/app/api/mcp/server.py`**

```python
import json
import logging
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from app.database import async_session_factory
from app.schemas.memory import MemoryCreate, MemorySearchRequest, MemoryUpdate
from app.services.memory import MemoryService

logger = logging.getLogger(__name__)

mcp = FastMCP("darkmem", json_response=True, stateless_http=True, streamable_http_path="/")

# Module-level reference set during app lifespan
_pipeline = None


def set_pipeline(pipeline):
    global _pipeline
    _pipeline = pipeline


async def _get_service():
    session = async_session_factory()
    return MemoryService(session, pipeline=_pipeline), session


def _memory_to_dict(memory) -> dict:
    return {
        "id": str(memory.id),
        "content": memory.content,
        "source": memory.source,
        "source_agent": memory.source_agent,
        "memory_type": memory.memory_type,
        "importance": memory.importance,
        "tags": [t.name for t in memory.tags],
        "created_at": memory.created_at.isoformat(),
    }


@mcp.tool(description="Create a new memory")
async def memory_add(content: str, tags: list[str] = [], source: str = "mcp", source_agent: str | None = None, memory_type: str | None = None) -> str:
    service, session = await _get_service()
    try:
        data = MemoryCreate(content=content, tags=tags, source=source, source_agent=source_agent, memory_type=memory_type)
        memory = await service.create_memory(data, api_key_id=None)
        await session.commit()
        return json.dumps(_memory_to_dict(memory))
    except Exception as e:
        await session.rollback()
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Search memories by query, tags, or filters")
async def memory_search(query: str | None = None, tags_any: list[str] | None = None, tags_all: list[str] | None = None, memory_type: str | None = None, source: str | None = None, limit: int = 20) -> str:
    service, session = await _get_service()
    try:
        params = MemorySearchRequest(query=query, tags_any=tags_any, tags_all=tags_all, memory_type=memory_type, source=source, limit=limit)
        memories = await service.search_memories(params)
        return json.dumps([_memory_to_dict(m) for m in memories])
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Get a memory by ID")
async def memory_get(memory_id: str) -> str:
    service, session = await _get_service()
    try:
        memory = await service.get_memory(UUID(memory_id))
        if not memory:
            return json.dumps({"error": "Memory not found"})
        return json.dumps(_memory_to_dict(memory))
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Update a memory")
async def memory_update(memory_id: str, content: str | None = None, tags: list[str] | None = None, memory_type: str | None = None) -> str:
    service, session = await _get_service()
    try:
        data = MemoryUpdate(content=content, tags=tags, memory_type=memory_type)
        memory = await service.update_memory(UUID(memory_id), data, api_key_id=None)
        if not memory:
            return json.dumps({"error": "Memory not found"})
        await session.commit()
        return json.dumps(_memory_to_dict(memory))
    except Exception as e:
        await session.rollback()
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Delete a memory")
async def memory_delete(memory_id: str) -> str:
    service, session = await _get_service()
    try:
        result = await service.delete_memory(UUID(memory_id), api_key_id=None)
        await session.commit()
        return json.dumps({"deleted": result})
    except Exception as e:
        await session.rollback()
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Create multiple memories at once")
async def memory_batch_add(entries: list[dict]) -> str:
    service, session = await _get_service()
    try:
        results = []
        for entry in entries:
            data = MemoryCreate(**entry)
            memory = await service.create_memory(data, api_key_id=None)
            results.append(_memory_to_dict(memory))
        await session.commit()
        return json.dumps(results)
    except Exception as e:
        await session.rollback()
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Ask a question about stored knowledge (RAG)")
async def memory_reason(question: str, limit: int = 10) -> str:
    service, session = await _get_service()
    try:
        result = await service.reason(question, limit=limit)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Find near-duplicate memories")
async def memory_find_duplicates(memory_id: str, threshold: float = 0.9) -> str:
    service, session = await _get_service()
    try:
        results = await service.find_duplicates(UUID(memory_id), threshold)
        return json.dumps(results, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Get memory system statistics")
async def memory_stats() -> str:
    from app.repositories.relational import PostgresTagRepository
    from sqlalchemy import func, select
    from app.models.memory import Memory, Tag

    session = async_session_factory()
    try:
        memory_count = (await session.execute(select(func.count()).select_from(Memory))).scalar()
        tag_count = (await session.execute(select(func.count()).select_from(Tag))).scalar()
        sources_result = await session.execute(select(Memory.source).distinct())
        sources = [r[0] for r in sources_result.all()]
        return json.dumps({"memories": memory_count, "tags": tag_count, "sources": sources})
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="List all tags with memory counts")
async def memory_tags() -> str:
    from app.repositories.relational import PostgresTagRepository

    session = async_session_factory()
    try:
        repo = PostgresTagRepository(session)
        tags_with_counts = await repo.get_with_counts()
        return json.dumps([{"name": t.name, "category": t.category, "count": c} for t, c in tags_with_counts])
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        await session.close()
```

- [ ] **Step 4: Mount MCP in `backend/app/main.py`**

Add imports:
```python
import contextlib
from starlette.routing import Mount
from app.api.mcp.server import mcp as mcp_server, set_pipeline
```

In the lifespan, after pipeline is created (before yield), add:
```python
        set_pipeline(pipeline)
```

Also, the MCP session manager needs to run during the app lifespan. Wrap the yield:
```python
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp_server.session_manager.run())
        yield
```

Mount the MCP app. After creating the FastAPI app, add:
```python
app.mount("/mcp", mcp_server.streamable_http_app())
```

- [ ] **Step 5: Write MCP tests — `backend/tests/test_mcp.py`**

```python
from app.api.mcp.server import mcp


async def test_mcp_tools_registered():
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "memory_add" in tool_names
    assert "memory_search" in tool_names
    assert "memory_get" in tool_names
    assert "memory_update" in tool_names
    assert "memory_delete" in tool_names
    assert "memory_batch_add" in tool_names
    assert "memory_reason" in tool_names
    assert "memory_find_duplicates" in tool_names
    assert "memory_stats" in tool_names
    assert "memory_tags" in tool_names
    assert len(tool_names) == 10
```

- [ ] **Step 6: Run all tests**

Run: `cd backend && pytest -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/pyproject.toml backend/app/api/mcp/ backend/app/main.py backend/tests/test_mcp.py
git commit -m "feat: add MCP server with StreamableHTTP transport"
```

---

## Limitations / Deferred to Plan 4

- **Frontend dashboard** — React SPA (Plan 4)
- **Production Docker Compose** — pull-based images (Plan 4)
- **Build scripts** — build-push.sh (Plan 4)
- **LLM config persistence** — currently env-based, not Postgres config table
- **MCP auth** — MCP tools run without API key auth (suitable for localhost/trusted network)
- **WebSocket auth** — WS connections not authenticated
- **Graph query MCP tools** — graph entity/neighbor queries via MCP (can be added later)

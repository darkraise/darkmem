# Chat Backend Design

**Date:** 2026-04-03
**Branch:** feat/backend-foundation
**Scope:** Sub-project 1 of 2 — backend only. Frontend (sub-project 2) will be designed separately.

## Summary

Add a full chat system backend with persistent conversations, SSE streaming responses, dual retrieval (vector search + knowledge graph), @-mention and graph selection context, and conversation CRUD API. Reuses the existing `llm_reasoning` provider and LLM orchestrator.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data retrieval | Vector search + knowledge graph in parallel | Richer context than vector-only, simpler than tool-use |
| Storage | PostgreSQL conversations + messages tables | Matches existing data layer, persists across sessions/devices |
| Streaming | SSE via POST endpoint | Simple, HTTP-based, matches Ollama/OpenAI streaming pattern |
| LLM config | Reuse `llm_reasoning` purpose | Same task, avoids config bloat |
| Context references | Automatic graph selection + @-mention parsing | Flexible, works on dedicated page and graph overlay |

## 1. Database Schema

### `conversations` table

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `title` | VARCHAR, nullable | Auto-generated from first message, editable |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |
| `is_archived` | BOOLEAN | Default false |

### `messages` table

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `conversation_id` | UUID | Foreign key → conversations, cascade delete |
| `role` | VARCHAR | `"user"` or `"assistant"` |
| `content` | TEXT | Message body |
| `context` | JSONB, nullable | Retrieval snapshot: memory IDs, entity IDs, scores |
| `created_at` | TIMESTAMP | |

The `context` JSONB on assistant messages stores the retrieval data that informed the response. This freezes the source snapshot in time and avoids extra joins. Structure:

```json
{
  "memories": [
    { "id": "uuid", "content": "...", "score": 0.87, "source": "claude-code", "tags": ["infra/services"] }
  ],
  "entities": [
    { "id": "uuid", "name": "PostgreSQL", "entity_type": "technology", "relationships": [...] }
  ]
}
```

## 2. API Endpoints

### Conversation CRUD

All endpoints require authentication via existing `require_auth` dependency.

**`GET /api/v1/chat/conversations`**
- Query params: `limit` (default 50), `offset` (default 0), `archived` (default false)
- Returns: `{ conversations: [{ id, title, created_at, updated_at, is_archived, message_count }] }`
- Ordered by `updated_at` descending

**`POST /api/v1/chat/conversations`**
- Body: `{ title?: string }` (optional, can be set later)
- Returns: `{ id, title, created_at }`

**`GET /api/v1/chat/conversations/{id}`**
- Returns: `{ id, title, created_at, updated_at, messages: [{ id, role, content, context, created_at }] }`
- Messages ordered by `created_at` ascending

**`PATCH /api/v1/chat/conversations/{id}`**
- Body: `{ title?: string, is_archived?: boolean }`
- Returns: updated conversation

**`DELETE /api/v1/chat/conversations/{id}`**
- Cascade deletes all messages
- Returns: 204

### Chat Completion (Streaming)

**`POST /api/v1/chat/completions`**

Request body:
```json
{
  "conversation_id": "uuid",
  "content": "What services does darkmem depend on?",
  "context": {
    "selected_node_id": "optional-memory-uuid",
    "selected_entity_id": "optional-entity-uuid",
    "mentions": ["PostgreSQL", "cluster:3"]
  }
}
```

Response: SSE stream (`text/event-stream`)

```
data: {"type": "sources", "memories": [...], "entities": [...]}
data: {"type": "token", "content": "Dark"}
data: {"type": "token", "content": "mem"}
data: {"type": "token", "content": " depends"}
...
data: {"type": "done", "message_id": "uuid"}
```

Event types:
- `sources` — sent once after retrieval completes (before LLM tokens start). Contains the memories and entities used as context. Allows the UI to render source cards while waiting for the first token.
- `token` — incremental text from the LLM. The frontend concatenates these to build the response.
- `done` — sent after the full response is persisted. Contains the saved `message_id` for the assistant response.

On error:
```
data: {"type": "error", "message": "LLM provider unreachable"}
```

The user message is saved to the database immediately on request receipt. The assistant message is saved after streaming completes.

If `conversation_id` is omitted, a new conversation is created automatically and its ID is included in the `done` event:
```
data: {"type": "done", "message_id": "uuid", "conversation_id": "uuid"}
```

## 3. Retrieval Pipeline

Executed between receiving the user message and calling the LLM.

### Step 1: Parse References

- Regex-extract @-mentions from message content: `@entity-name` and `@cluster:N` patterns
- Combine with `context.selected_node_id` and `context.selected_entity_id` from the request body
- If a selected node ID is a memory, look up its linked entities

### Step 2: Parallel Retrieval

Run concurrently:

**Vector search:**
- Embed the user message via `LLMOrchestrator.embed()`
- Search Qdrant for top-10 similar memories via `VectorRepository.search()`
- Returns: memory content, tags, source, importance, similarity score

**Graph lookup:**
- For each referenced entity name: query Neo4j via `GraphRepository.get_entities()` and `get_neighbors_by_id()`
- Returns: entity properties, relationships (type, target, weight)
- If no explicit entities referenced but vector search returned memories, extract entity names from those memories and do a lightweight graph lookup

### Step 3: Build LLM Prompt

Assemble messages array for the chat completion:

1. **System prompt** — the chat system prompt (from prompt profile config)
2. **Retrieved context** — formatted as a system-level context block:
   - Numbered memory passages with metadata (source, tags, importance)
   - Entity facts with relationship lists
3. **Conversation history** — last 20 messages from this conversation (role + content only, no context blobs). Truncated if total token estimate exceeds 80% of the model's context window.
4. **Current user message**

### Step 4: Stream LLM Response

- Call `LLMOrchestrator.chat_completion()` but in streaming mode
- The existing httpx client supports streaming from Ollama/OpenAI-compatible endpoints
- Add a new method `LLMOrchestrator.chat_completion_stream()` that yields token chunks
- Forward each chunk as an SSE `token` event

### Step 5: Persist

After streaming completes:
- Save the full concatenated assistant response to the `messages` table
- Store retrieval context (memory IDs with scores, entity IDs with relationships) in the `context` JSONB column
- Update the conversation's `updated_at` timestamp
- If the conversation has no title, auto-generate one from the first user message (truncate to 60 chars)

## 4. LLM Configuration

- Reuses the existing `llm_reasoning` purpose slot — same model, temperature, base URL
- No new LLM provider configuration needed
- Chat system prompt stored as a prompt profile via existing `/config/system-prompt/list` infrastructure

Default system prompt:
```
You are a knowledge assistant for a personal memory system called darkmem.
Answer questions based on the retrieved memories and entity data provided below.
When citing information, reference the memory source and content.
If the retrieved context doesn't contain enough information to answer, say so honestly.
Keep answers concise and well-structured. Use markdown formatting.
```

## 5. Files to Create/Modify

### New files

| File | Purpose |
|------|---------|
| `backend/app/models/chat.py` | SQLAlchemy models for `Conversation` and `Message` |
| `backend/app/api/routes/chat.py` | API endpoints for conversation CRUD and chat completions |
| `backend/app/services/chat.py` | Chat service — retrieval pipeline, prompt building, streaming orchestration |

### Modified files

| File | Change |
|------|--------|
| `backend/app/services/llm.py` | Add `chat_completion_stream()` method that yields token chunks |
| `backend/app/api/routes/__init__.py` | Register chat router |
| `alembic/versions/` | New migration for conversations and messages tables |

### No changes to

- Vector repository (used as-is for search)
- Graph repository (used as-is for entity/relationship queries)
- Existing `/memories/reason` endpoint (kept for backward compatibility)
- Frontend (sub-project 2)

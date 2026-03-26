# darkmem — Centralized Memory System for AI Agents

**Date:** 2026-03-26
**Status:** Draft
**Author:** quang + Claude

## Overview

darkmem is a centralized, tool-agnostic memory system that consolidates agent persistent memory into a single engine. It replaces the current dual-system setup (mem0 + memora) with a unified platform featuring knowledge graph, vector search, LLM-powered processing, MCP interface, REST API, and an interactive visualization dashboard.

### Motivation

- **Operational overhead** — maintaining two memory systems (dual writes, deduplication, sync)
- **Feature gaps** — neither system provides graph traversal, visualization, or unified search
- **Universal access** — any tool (Claude Code, Cursor, n8n, custom agents, scripts) should be able to store/retrieve memories via a single API

### Success Criteria (v1)

1. Fully replace mem0 + memora — swap Claude Code MCP config to darkmem
2. Interactive dashboard with knowledge graph and vector space visualization
3. Universal REST API usable by any tool that can make HTTP requests

## Architecture

Layered monolith deployed as a single Docker Compose stack (5 containers).

### Layers

```
API Layer (REST + MCP + WebSocket)
  → Service Layer (memory engine, LLM orchestration, graph manager, analytics)
    → Repository Layer (storage abstraction interfaces)
      → Storage (Qdrant, Neo4j, PostgreSQL)
```

Strict downward dependencies — each layer only calls the layer directly below it.

### Compose Stack

| Container | Image | Role | Port |
|-----------|-------|------|------|
| darkmem-api | `darkraise/darkmem-api` | FastAPI — core engine, REST API, MCP server, WebSocket | 8000 |
| darkmem-ui | `darkraise/darkmem-ui` | React dashboard (nginx) | 3000 |
| postgres | `postgres:17-alpine` | Relational data (memories, tags, API keys, audit) | 5432 |
| qdrant | `qdrant/qdrant:latest` | Vector embeddings for semantic search | 6333 |
| neo4j | `neo4j:5-community` | Knowledge graph (entities, relationships, hierarchy) | 7687 |

LLM providers (Ollama, OpenAI, Google AI Studio, etc.) are external — darkmem connects to whatever is configured.

### Deployment Model

- **Production (`docker-compose.yml`)** — pulls pre-built images from Docker Hub (`darkraise/darkmem-api`, `darkraise/darkmem-ui`)
- **Development (`docker-compose.dev.yml`)** — builds from local Dockerfiles, mounts source for hot-reload
- **Build script (`scripts/build-push.sh`)** — builds, tags (`latest` + git SHA + optional semver), pushes to Docker Hub under `darkraise` account

## Data Model

### Three-Store Architecture

All three stores are linked by `memory_id` (UUID) as the universal join key.

### PostgreSQL — Source of Truth

#### `memories`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | Memory identifier |
| content | TEXT | Raw memory content |
| source | TEXT | Origin: "claude-code", "api", "n8n", etc. |
| source_agent | TEXT | Agent/session identifier |
| memory_type | TEXT | fact, decision, preference, debug, session, etc. |
| importance | REAL | LLM-scored 0.0–1.0 |
| metadata | JSONB | Arbitrary key-value data |
| created_at | TIMESTAMPTZ | Creation time |
| updated_at | TIMESTAMPTZ | Last modification |
| expires_at | TIMESTAMPTZ NULL | Optional TTL |
| is_archived | BOOLEAN | Soft delete flag |

#### `tags`

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Tag identifier |
| name | TEXT UNIQUE | e.g., "project/darkmem" |
| category | TEXT | e.g., "project", "infra", "user" |

#### `memory_tags`

| Column | Type | Description |
|--------|------|-------------|
| memory_id | UUID FK | References memories.id |
| tag_id | INTEGER FK | References tags.id |

#### `api_keys`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | Key identifier |
| name | TEXT | Human label: "claude-code-home" |
| key_hash | TEXT | Bcrypt hash (never store plaintext) |
| scopes | JSONB | ["read", "write", "admin"] |
| profile | TEXT | System prompt profile name |
| created_at | TIMESTAMPTZ | |
| last_used_at | TIMESTAMPTZ | |
| expires_at | TIMESTAMPTZ NULL | Optional expiry |

#### `audit_log`

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | |
| action | TEXT | create, update, delete, search, merge |
| memory_id | UUID NULL | Affected memory |
| api_key_id | UUID FK | Who performed it |
| details | JSONB | Action-specific data |
| timestamp | TIMESTAMPTZ | |

#### `config`

| Column | Type | Description |
|--------|------|-------------|
| key | TEXT PK | Config key |
| value | JSONB | Config value |

#### `system_prompt_profiles`

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | Profile identifier |
| name | TEXT UNIQUE | Profile slug: "coding-assistant" |
| display_name | TEXT | Human label: "Coding Assistant" |
| content | TEXT | Full system prompt markdown |
| save_triggers | JSONB | What warrants a memory |
| search_behavior | JSONB | When/how to pull context |
| tagging_conventions | JSONB | Suggested tag prefixes |
| extraction_depth | TEXT | full, light, none |
| dedup_strategy | JSONB | Threshold, auto-merge rules |
| is_default | BOOLEAN | Exactly one profile is default |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### Qdrant — Vector Store

**Collection:** `memories`

| Field | Type | Description |
|-------|------|-------------|
| vector | FLOAT[N] | Embedding (dimension from model config) |
| payload.memory_id | UUID | Cross-reference to Postgres |
| payload.content | TEXT | Denormalized for display |
| payload.source | TEXT | For filtered search |
| payload.tags | TEXT[] | For filtered search |
| payload.memory_type | TEXT | For filtered search |
| payload.created_at | TIMESTAMP | For time-range queries |

### Neo4j — Knowledge Graph

**Node: Entity**

| Property | Type | Description |
|----------|------|-------------|
| id | UUID | Entity identifier |
| name | STRING | Entity name |
| entity_type | STRING | person, service, project, technology, concept, etc. |
| properties | MAP | Arbitrary properties |
| memory_ids | UUID[] | Source memories (provenance) |

**Relationships (typed edges)**

| Property | Type | Description |
|----------|------|-------------|
| type | STRING | WORKS_ON, DEPENDS_ON, IS_A, HAS_PART, USES, etc. |
| properties | MAP | Edge-specific data |
| weight | FLOAT | Relationship strength |
| memory_ids | UUID[] | Provenance |
| created_at | TIMESTAMP | |

### Memory Lifecycle

1. Raw input received (content + tags + source) → stored in PostgreSQL
2. LLM extraction: content → entities + relationships + memory_type + importance → Neo4j
3. LLM embedding: content → vector → Qdrant
4. Steps 2-3 run asynchronously after step 1 completes

### Cross-Store Consistency

- **PostgreSQL is source of truth** — if a memory exists in Qdrant/Neo4j but not Postgres, it's orphaned
- **Eventual consistency** — writes go to Postgres first, async fan-out to Qdrant + Neo4j
- **Rebuild capability** — Qdrant and Neo4j can be fully rebuilt from PostgreSQL content (re-embed, re-extract)

## Service Layer

### Memory Engine

Core CRUD + search orchestration:

- `create_memory(content, tags, source)` → stores in Postgres, triggers async LLM pipeline
- `search(query, filters)` → hybrid search: semantic (Qdrant) + tag/metadata (Postgres) + graph context (Neo4j), results fused and ranked
- `update_memory(id, content, tags)` → update Postgres, re-trigger LLM pipeline
- `delete_memory(id)` → cascade delete across all three stores
- `merge_memories(source_id, target_id)` → combine content, merge tags, update graph references
- `find_duplicates(threshold)` → vector similarity scan, surface near-duplicates
- `archive_memory(id)` → soft delete with is_archived flag

### LLM Orchestrator

Provider-agnostic via OpenAI API standard. Each purpose independently configurable.

#### Per-Purpose Configuration

```yaml
llm:
  embedding:
    provider: ollama
    base_url: http://ollama:11434/v1
    model: nomic-embed-text
    api_key: null
    dimensions: 768
    params: {}

  extraction:
    provider: openai
    base_url: https://api.openai.com/v1
    model: gpt-4o-mini
    api_key: ${OPENAI_API_KEY}
    params:
      temperature: 0.2
      extra_body: {}

  reasoning:
    provider: google
    base_url: https://generativelanguage.googleapis.com/v1beta/openai
    model: gemini-2.5-flash
    api_key: ${GOOGLE_API_KEY}
    params:
      temperature: 0.7
      max_tokens: 4096

  summarization:
    provider: ollama
    base_url: http://ollama:11434/v1
    model: qwen3:8b
    api_key: null
    params:
      temperature: 0.3
      extra_body:
        thinking: false
```

#### Configuration Fields

| Field | Description |
|-------|-------------|
| provider | Label (ollama, openai, google, anthropic, etc.) |
| base_url | OpenAI-compatible endpoint |
| model | Model identifier |
| api_key | API key (null for local) |
| params | Standard OpenAI params (temperature, max_tokens, top_p, etc.) |
| params.extra_body | Provider-specific params merged into request body (e.g., Ollama's `thinking`, `num_ctx`) |

Config stored in Postgres `config` table, editable from admin dashboard. No restart required to swap models.

### Graph Manager

- **Entity resolution** — LLM identifies that "Postgres", "PostgreSQL", "postgres" are the same entity
- **Relationship inference** — detects implicit relationships from co-occurring entities
- **Traversal queries** — "what depends on service X?", "what does person Y work on?"
- **Hierarchy management** — IS_A chains, category trees

### Analytics

- Memory stats (count by type, source, tag, time)
- Knowledge graph metrics (node degrees, clusters, orphans)
- Duplicate detection reports
- Usage patterns (most queried, most linked)

## API Layer

Three interfaces sharing the same service layer.

### REST API

Auth: `Authorization: Bearer dm_xxxx` header. Scopes: `read`, `write`, `admin`.

| Endpoint | Method | Scope | Description |
|----------|--------|-------|-------------|
| `/api/v1/memories` | POST | write | Create memory |
| `/api/v1/memories/{id}` | GET | read | Get by ID |
| `/api/v1/memories/{id}` | PUT | write | Update |
| `/api/v1/memories/{id}` | DELETE | write | Delete (cascades) |
| `/api/v1/memories/search` | POST | read | Hybrid search |
| `/api/v1/memories/batch` | POST | write | Batch create |
| `/api/v1/memories/{id}/merge` | POST | write | Merge two memories |
| `/api/v1/memories/duplicates` | GET | read | Find near-duplicates |
| `/api/v1/graph/entities` | GET | read | List/search entities |
| `/api/v1/graph/entities/{id}/neighbors` | GET | read | Traverse relationships |
| `/api/v1/graph/query` | GET | read | Graph query |
| `/api/v1/reason` | POST | read | RAG over memory store |
| `/api/v1/analytics/stats` | GET | read | Statistics |
| `/api/v1/analytics/insights` | GET | read | LLM-generated insights |
| `/api/v1/tags` | GET | read | List all tags |
| `/api/v1/config/llm` | GET/POST | admin | LLM provider config |
| `/api/v1/config/system-prompt` | GET | read | Get system prompt for agent profile |
| `/api/v1/keys` | GET/POST/DELETE | admin | Manage API keys |

### MCP Server

StreamableHTTP transport mounted at `/mcp` on the same FastAPI app.

| MCP Tool | Maps To | Description |
|----------|---------|-------------|
| memory_add | POST /memories | Create memory |
| memory_search | POST /memories/search | Hybrid search |
| memory_get | GET /memories/{id} | Get by ID |
| memory_update | PUT /memories/{id} | Update |
| memory_delete | DELETE /memories/{id} | Delete |
| memory_batch_add | POST /memories/batch | Batch create |
| memory_merge | POST /memories/{id}/merge | Merge |
| memory_find_duplicates | GET /memories/duplicates | Find duplicates |
| memory_reason | POST /reason | Ask questions about stored knowledge |
| memory_graph_query | GET /graph/query | Graph query |
| memory_graph_entities | GET /graph/entities | List entities |
| memory_graph_neighbors | GET /graph/entities/{id}/neighbors | Traverse |
| memory_stats | GET /analytics/stats | Statistics |
| memory_tags | GET /tags | List tags |

Auth via API key in MCP client config.

### WebSocket

Endpoint: `ws://host:8000/ws`

Events pushed to connected clients:
- `memory.created`, `memory.updated`, `memory.deleted`
- `graph.entity_added`, `graph.relation_added`
- `pipeline.started`, `pipeline.completed`, `pipeline.failed`

Enables real-time dashboard updates without polling.

## System Prompt Profiles

Pre-defined profiles stored in Postgres, selectable per API key. Configurable from admin dashboard.

| Profile | Optimized For |
|---------|---------------|
| `default` | General-purpose agent — balanced save/search triggers, standard tagging |
| `coding-assistant` | Claude Code, Cursor, Copilot — save decisions, debug insights, architecture; search on conversation start + when touching unfamiliar code |
| `devops-agent` | Infrastructure work — save service configs, networking details, incident root causes, gotchas; tag with `infra/*` conventions |
| `research-agent` | Knowledge gathering — aggressive save on facts/sources/findings; dedup-aware; summarize before storing |
| `automation` | n8n, scripts, pipelines — minimal reasoning, structured input/output, batch-friendly |
| `minimal` | Dumb pipe — no LLM processing, store and retrieve raw content |

Each profile defines:
- **Save triggers** — what warrants a memory
- **Search behavior** — when and how aggressively to pull context
- **Tagging conventions** — suggested tag prefixes and categories
- **Extraction depth** — full LLM extraction vs. light vs. none
- **Dedup strategy** — search-before-save threshold, auto-merge rules

## Admin Dashboard

React SPA with sidebar navigation. Dark theme using Tailwind CSS 4 + shadcn/ui.

### Pages

| Page | Description |
|------|-------------|
| **Overview** | Stat cards (memories, entities, relations, sources), recent memories list, live activity feed via WebSocket |
| **Memories** | Searchable/filterable table (tag, source, type, date). Inline edit, delete, merge. |
| **Knowledge Graph** | Interactive force-directed graph (Cytoscape.js). Click node → entity details + linked memories. Filter by entity type, relationship type. |
| **Vector Space** | 2D/3D projection of embedding space (plotly.js). Color by tag/source/type. Click point → memory detail. |
| **Search** | Unified search bar — hybrid results ranked by relevance. Toggle semantic/tag/graph modes. |
| **Analytics** | Charts (Recharts): memories over time, by source, by type. Graph metrics: most connected entities, orphan nodes, cluster analysis. |
| **API Keys** | Create/revoke keys, set scopes, assign prompt profiles, view usage stats. |
| **LLM Config** | Per-purpose provider/model/params editor. Test connection button. |
| **Settings** | General config, system prompt profile editor, data export/import, rebuild indexes. |

### Visualization Libraries

| Purpose | Library |
|---------|---------|
| Knowledge graph | Cytoscape.js |
| Vector space | plotly.js |
| Charts | Recharts |
| UI components | shadcn/ui (Radix UI primitives) |

## Tech Stack

### Backend

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI (Python 3.12+) |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| HTTP client | httpx (LLM API calls) |
| Qdrant client | qdrant-client |
| Neo4j client | neo4j-driver |
| MCP SDK | mcp[server] (StreamableHTTP) |
| Validation | Pydantic v2 |
| Settings | pydantic-settings |
| Task queue | asyncio (in-process background tasks) |

### Frontend

| Component | Technology |
|-----------|-----------|
| Framework | React 18+ with TypeScript |
| Build tool | Vite |
| Routing | React Router |
| Styling | Tailwind CSS 4 |
| UI components | shadcn/ui |
| Graph viz | Cytoscape.js |
| Vector viz | plotly.js |
| Charts | Recharts |
| Data fetching | TanStack Query |
| WebSocket | native WebSocket API |

### Infrastructure

| Component | Technology |
|-----------|-----------|
| Containerization | Docker, Docker Compose |
| Database | PostgreSQL 17 |
| Vector DB | Qdrant |
| Graph DB | Neo4j 5 Community |
| Registry | Docker Hub (darkraise/*) |

## Project Structure

```
darkmem/
├── docker-compose.yml              # Production — pulls from darkraise/*
├── docker-compose.dev.yml          # Development — builds from Dockerfile
├── .env.example
├── scripts/
│   └── build-push.sh               # Build + tag + push to Docker Hub
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app/
│       ├── main.py                  # FastAPI app + startup
│       ├── config.py                # Settings (pydantic-settings)
│       │
│       ├── api/                     # API Layer
│       │   ├── routes/
│       │   │   ├── memories.py
│       │   │   ├── graph.py
│       │   │   ├── analytics.py
│       │   │   ├── config.py
│       │   │   └── keys.py
│       │   ├── mcp/
│       │   │   └── server.py        # MCP StreamableHTTP handler
│       │   ├── websocket.py
│       │   ├── auth.py              # API key validation
│       │   └── deps.py              # Dependency injection
│       │
│       ├── services/                # Service Layer
│       │   ├── memory.py            # Memory engine
│       │   ├── llm.py               # LLM orchestrator
│       │   ├── graph.py             # Graph manager
│       │   ├── analytics.py
│       │   └── extraction.py        # Entity/relation extraction
│       │
│       ├── repositories/            # Repository Layer
│       │   ├── base.py              # Abstract interfaces
│       │   ├── vector.py            # Qdrant implementation
│       │   ├── graph.py             # Neo4j implementation
│       │   └── relational.py        # Postgres implementation
│       │
│       ├── models/                  # Data models
│       │   ├── memory.py            # SQLAlchemy + Pydantic
│       │   ├── entity.py
│       │   ├── api_key.py
│       │   └── audit.py
│       │
│       ├── prompts/                 # System prompt profiles
│       │   ├── default.md
│       │   ├── coding-assistant.md
│       │   ├── devops-agent.md
│       │   ├── research-agent.md
│       │   ├── automation.md
│       │   └── minimal.md
│       │
│       └── db/
│           ├── migrations/          # Alembic
│           └── seed.py              # Default profiles + initial config
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── pages/
│       │   ├── Overview.tsx
│       │   ├── Memories.tsx
│       │   ├── KnowledgeGraph.tsx
│       │   ├── VectorSpace.tsx
│       │   ├── Search.tsx
│       │   ├── Analytics.tsx
│       │   ├── ApiKeys.tsx
│       │   ├── LlmConfig.tsx
│       │   └── Settings.tsx
│       ├── components/
│       │   ├── Sidebar.tsx
│       │   ├── MemoryCard.tsx
│       │   ├── GraphViewer.tsx
│       │   ├── VectorScatter.tsx
│       │   └── ActivityFeed.tsx
│       └── hooks/
│           ├── useWebSocket.ts
│           └── useApi.ts
│
└── docs/
    └── system-prompts.md
```

## Auth & Multi-Tenancy

### Current (v1)

- Single user
- API key auth (`dm_xxxx` prefix, bcrypt-hashed in Postgres)
- Scopes: `read`, `write`, `admin`
- Each API key maps to a system prompt profile

### Future-Ready

- `api_keys` table supports `scopes` and `profile` per key
- Data model has no user-scoping columns yet, but adding `owner_id` to `memories` table is a non-breaking migration
- Repository layer abstraction means auth logic stays in the API layer, storage is unaware

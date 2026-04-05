# Codebase Indexer and Code Knowledge Store

## Goal

Add codebase indexing to darkmem so that source code from local and remote repositories is parsed, embedded, and stored as searchable knowledge. This is the foundation for a future MCP server that provides coding context to AI agents, a code knowledge UI, and memory-to-code linking.

## Scope

This spec covers the Indexer and Store only. The following are separate future sub-projects:
- MCP server exposing code knowledge tools
- Code knowledge UI in the darkmem dashboard
- Memory-to-code linking (connecting existing memories to source code)

## Architecture

Three new components extend the darkmem backend:

1. **Repository Manager** — Manages registered repos (local paths or remote git URLs). Handles cloning, periodic git pull, webhook-triggered pulls, and tracking the last indexed commit SHA per repo. Supports GitHub/GitLab private repos via stored auth tokens.

2. **Code Indexer** — Two-phase pipeline. Phase 1 (synchronous): diffs changed files against last indexed commit, parses with tree-sitter to extract symbols, generates embeddings via Ollama. Phase 2 (async background queue): feeds symbols to the LLM for summary generation, prioritizing exported/public symbols first.

3. **Code Knowledge Store** — New tables in PostgreSQL (repositories, code_files, code_symbols), a new Qdrant collection (`code_chunks`) for semantic code search, and new Neo4j nodes/edges for the code dependency graph.

All components run within the existing darkmem FastAPI backend process. No new containers.

## Data Model

### PostgreSQL

**`repositories` table:**
- `id` (UUID, PK)
- `name` (string) — display name
- `url` (string, nullable) — remote git URL
- `local_path` (string, nullable) — local filesystem path
- `provider` (string) — github, gitlab, local
- `default_branch` (string, default "main")
- `auth_token_ref` (string, nullable) — key name in config table referencing the stored token
- `last_indexed_commit` (string, nullable) — SHA of the last indexed commit
- `last_indexed_at` (datetime, nullable)
- `sync_interval_minutes` (int, default 30)
- `is_active` (bool, default true)
- `created_at`, `updated_at` (datetime)

**`code_files` table:**
- `id` (UUID, PK)
- `repo_id` (UUID, FK to repositories)
- `file_path` (string) — relative path within the repo
- `language` (string) — detected from file extension
- `last_commit_sha` (string)
- `content_hash` (string) — SHA256 of file content for dedup
- `indexed_at` (datetime)

**`code_symbols` table:**
- `id` (UUID, PK)
- `file_id` (UUID, FK to code_files)
- `name` (string)
- `kind` (string) — function, class, method, interface, struct, trait, enum, module, namespace
- `line_start` (int)
- `line_end` (int)
- `signature` (string, nullable) — function params and return type as text
- `docstring` (text, nullable)
- `visibility` (string, nullable) — public, private, exported
- `parent_symbol_id` (UUID, nullable, self-FK) — for nested classes/methods
- `source_code` (text) — raw source of the symbol body
- `summary` (text, nullable) — LLM-generated description
- `enrichment_status` (string, default "pending") — pending, completed, failed
- `enrichment_priority` (int, default 0) — higher = process first

### Qdrant

**Collection: `code_chunks`**
- Vector: nomic-embed-text embedding (768 dimensions)
- Payload: repo_id, file_path, language, symbol_name (nullable), chunk_content, line_start, line_end

### Neo4j

- `CodeSymbol` nodes — name, kind, file_path, repo_id, language
- `DEFINES` edges — file defines symbol
- `CONTAINS` edges — class/struct contains method
- `IMPORTS` edges — file/module imports another file/module
- `CALLS` edges — function calls another function

## Indexing Pipeline

### Phase 1 — Fast (synchronous)

1. **Git sync** — For remote repos: `git fetch` + `git merge`. For new repos: `git clone`. For local repos: no-op (read directly). Record new commit SHA.
2. **Diff detection** — `git diff --name-status <last_indexed_commit> <new_commit>`. Identify added (A), modified (M), and deleted (D) files. For first-time indexing, treat all files as added.
3. **File processing** — For each changed file with a recognized extension:
   - Detect language from file extension
   - Parse with tree-sitter using the appropriate grammar
   - Extract symbols via language-specific query module (7 languages) or generic fallback (all others)
   - Split into semantic chunks (per-function/per-class boundaries; fallback to ~100-line windows with 20-line overlap for non-parseable files)
   - Generate embeddings for each chunk via Ollama nomic-embed-text
4. **Store** — Upsert into PostgreSQL (code_files, code_symbols), Qdrant (code_chunks collection), Neo4j (CodeSymbol nodes, IMPORTS/CALLS/DEFINES/CONTAINS edges)
5. **Cleanup** — Remove entries for deleted files from all three stores
6. **Queue enrichment** — Add new/modified symbols to the enrichment queue with priority (exported/public = high, class definitions = medium, internal/private = low)
7. **Update tracking** — Set `last_indexed_commit` and `last_indexed_at` on the repository record

### Phase 2 — Background enrichment (async queue)

1. Worker pulls symbols from the queue ordered by `enrichment_priority` DESC
2. Sends the symbol's `source_code` to the LLM with prompt: "Summarize what this [kind] does in 1-2 sentences. Be specific about inputs, outputs, and side effects."
3. Stores the summary in `code_symbols.summary`, sets `enrichment_status` to "completed"
4. On LLM failure, sets `enrichment_status` to "failed" for retry
5. Rate-limited: configurable concurrency (default 1 concurrent request to avoid saturating Ollama)

### Triggers

- **Periodic schedule** — Configurable per repo via `sync_interval_minutes` (default 30). A background task checks all active repos and triggers indexing for any due.
- **Webhook** — `POST /api/v1/repos/webhook` accepts GitHub/GitLab push event payloads. Identifies the repo by URL match and triggers immediate indexing.
- **Manual** — `POST /api/v1/repos/{id}/reindex` triggers a full or incremental re-index.

## tree-sitter Integration

### Parser architecture

A `CodeParser` class manages tree-sitter grammars and delegates extraction to language-specific query modules when available, falling back to a generic extractor.

**Language-specific query modules (7 languages):**

| Language | Key patterns extracted |
|----------|----------------------|
| Python | functions, classes, methods, decorators, imports, `__init__`, `@property` |
| TypeScript | functions, classes, interfaces, type aliases, imports, exports, generics |
| JavaScript | functions, classes, arrow functions, imports, exports, CommonJS requires |
| Go | functions, methods (with receiver), structs, interfaces, imports, goroutine calls |
| Rust | functions, structs, enums, traits, impl blocks, use statements, macros |
| C# | classes, methods, namespaces, using statements, interfaces, properties |
| C++ | functions, classes, namespaces, includes, templates, struct definitions |

**Generic fallback extractor:**
Uses common tree-sitter node type patterns (`function_definition`, `class_definition`, `import_statement`, etc.) that appear across most grammars. Captures function/class names, basic signatures, and import relationships. Falls back to line-based chunking for files where no symbols are detected.

**Language detection:** Map file extensions to tree-sitter grammars. Extensible via configuration. Unrecognized extensions get line-based chunking with embeddings only (no symbol extraction).

**Chunking strategy:**
- Primary: one chunk per symbol (function/class body). Semantically coherent.
- Large symbols (>200 lines): split at logical breaks (blank lines, comment blocks).
- Files without symbols: ~100-line windows, 20-line overlap.
- Config/markup files (YAML, JSON, TOML, Markdown, Dockerfile): line-based chunking only.

### Dependency

`py-tree-sitter` Python binding with official tree-sitter organization parsers. The following official grammars are used:

**7 target languages (language-specific query modules):**
`tree-sitter-python`, `tree-sitter-typescript` (includes JavaScript), `tree-sitter-go`, `tree-sitter-rust`, `tree-sitter-c-sharp`, `tree-sitter-cpp`

**Additional official parsers (generic fallback):**
`tree-sitter-java`, `tree-sitter-ruby`, `tree-sitter-php`, `tree-sitter-haskell`, `tree-sitter-scala`, `tree-sitter-julia`, `tree-sitter-ocaml`, `tree-sitter-html`, `tree-sitter-css`, `tree-sitter-json`, `tree-sitter-bash`, `tree-sitter-c`, `tree-sitter-agda`, `tree-sitter-verilog`, `tree-sitter-regex`, `tree-sitter-jsdoc`, `tree-sitter-embedded-template` (ERB/EJS)

All parsers sourced from the official tree-sitter GitHub organization (https://tree-sitter.github.io/tree-sitter/). Third-party parsers from the tree-sitter wiki can be added later for additional language coverage.

## API Endpoints

### Repository management

- `POST /api/v1/repos` — Register a new repo. Body: `{ name, url?, local_path?, provider, default_branch?, auth_token?, sync_interval_minutes? }`
- `GET /api/v1/repos` — List all repos with status (last indexed, file count, symbol count, enrichment progress)
- `GET /api/v1/repos/{id}` — Repo detail with full indexing stats
- `PUT /api/v1/repos/{id}` — Update settings (sync interval, auth token, active/inactive)
- `DELETE /api/v1/repos/{id}` — Unregister and remove all indexed data
- `POST /api/v1/repos/{id}/reindex` — Trigger manual re-index
- `POST /api/v1/repos/webhook` — GitHub/GitLab webhook receiver (push events)

### Code knowledge queries

- `POST /api/v1/code/search` — Semantic search across code chunks. Body: `{ query, repo_id?, language?, limit? }`. Returns matching chunks with scores.
- `GET /api/v1/code/symbols` — List symbols with filters. Query params: `repo_id, file_path, kind, name, limit, offset`
- `GET /api/v1/code/symbols/{id}` — Symbol detail: source code, summary, callers (via Neo4j CALLS edges), callees, parent symbol
- `GET /api/v1/code/files/{repo_id}` — List files in a repo. Query params: `path_prefix, language`
- `GET /api/v1/code/files/{repo_id}/{path}` — File detail with all extracted symbols
- `GET /api/v1/code/graph/{repo_id}` — Dependency graph: symbol nodes + import/call/define edges

### Credential management

Git auth tokens stored in the existing `config` table, following the same pattern as LLM API keys. Managed through the existing Settings API. The `repositories.auth_token_ref` field references the config key name.

## Files to Create or Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `backend/app/models/code.py` | Repository, CodeFile, CodeSymbol SQLAlchemy models |
| Create | `backend/app/schemas/code.py` | Pydantic schemas for repos, symbols, search |
| Create | `backend/app/repositories/code.py` | PostgreSQL repo for code tables |
| Create | `backend/app/services/repo_manager.py` | Git clone/pull, webhook handling, repo CRUD |
| Create | `backend/app/services/code_indexer.py` | Indexing pipeline: diff, parse, embed, store |
| Create | `backend/app/services/code_parser.py` | tree-sitter parsing engine + language query modules |
| Create | `backend/app/services/enrichment_worker.py` | Background LLM summarization queue |
| Create | `backend/app/api/routes/repos.py` | Repository management API routes |
| Create | `backend/app/api/routes/code.py` | Code knowledge query API routes |
| Modify | `backend/app/main.py` | Register new routers, start background tasks |
| Modify | `backend/app/api/deps.py` | Add dependency injectors for new services |
| Create | `backend/migrations/versions/xxx_add_code_tables.py` | Alembic migration for new tables |

## Out of Scope

- MCP server exposing code knowledge tools (separate sub-project)
- Code knowledge UI in the darkmem dashboard (separate sub-project)
- Memory-to-code linking (separate sub-project)
- Code modification or generation
- Live file-watching (uses git diff instead)
- Branch-aware indexing (indexes default branch only)

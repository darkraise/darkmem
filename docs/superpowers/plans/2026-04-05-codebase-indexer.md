# Codebase Indexer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add codebase indexing to darkmem: parse source code from git repos using tree-sitter, store symbols/chunks/graphs, enrich with LLM summaries, and expose via REST API.

**Architecture:** Repository Manager handles git clone/pull/webhooks. Code Indexer runs a two-phase pipeline: fast synchronous phase (tree-sitter parsing + embeddings) and async background enrichment (LLM summarization). All data stored in existing PostgreSQL, Qdrant, and Neo4j instances with new tables/collections.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, py-tree-sitter, Qdrant, Neo4j, Ollama (nomic-embed-text + qwen3:8b), Alembic

**Spec:** `docs/superpowers/specs/2026-04-05-codebase-indexer-design.md`

---

## Group A: Data Models and Migration

### Task 1: Create code models

**Files:**
- Create: `backend/app/models/code.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create the SQLAlchemy models**

Create `backend/app/models/code.py` with three models: `Repository`, `CodeFile`, and `CodeSymbol`. Repository has fields for name, url, local_path, provider, default_branch, auth_token_ref, last_indexed_commit, last_indexed_at, sync_interval_minutes, is_active. CodeFile links to Repository with file_path, language, last_commit_sha, content_hash. CodeSymbol links to CodeFile with name, kind, line_start, line_end, signature, docstring, visibility, parent_symbol_id (self-FK), source_code, summary, enrichment_status, enrichment_priority. Follow the same patterns as `app/models/memory.py` (UUID PKs, DateTime with timezone, mapped_column style).

- [ ] **Step 2: Register models in `__init__.py`**

Add `from .code import Repository, CodeFile, CodeSymbol` to `backend/app/models/__init__.py` and update `__all__`.

- [ ] **Step 3: Verify imports work**

Run: `cd backend && python -c "from app.models.code import Repository, CodeFile, CodeSymbol; print('OK')"`

- [ ] **Step 4: Commit**

```
git commit -m "feat(code): add Repository, CodeFile, CodeSymbol models"
```

---

### Task 2: Create Alembic migration

**Files:**
- Create: `backend/migrations/versions/xxxx_add_code_tables.py`

- [ ] **Step 1: Generate migration**

Run: `cd backend && alembic revision --autogenerate -m "add code indexing tables"`

- [ ] **Step 2: Verify migration has all three tables**

Check the generated file for `repositories`, `code_files`, `code_symbols` tables.

- [ ] **Step 3: Apply migration**

Run: `cd backend && alembic upgrade head`

- [ ] **Step 4: Commit**

```
git commit -m "feat(code): add migration for code indexing tables"
```

---

### Task 3: Create Pydantic schemas

**Files:**
- Create: `backend/app/schemas/code.py`

- [ ] **Step 1: Create schemas**

Create `backend/app/schemas/code.py` with: `RepoCreate` (name, url, local_path, provider, default_branch, auth_token, sync_interval_minutes), `RepoUpdate` (name, sync_interval_minutes, auth_token, is_active, default_branch — all optional), `RepoResponse` (all fields + file_count + symbol_count), `CodeFileResponse` (id, file_path, language, last_commit_sha, indexed_at), `CodeSymbolResponse` (id, name, kind, file_path, line_start, line_end, signature, docstring, visibility, source_code, summary, enrichment_status), `CodeSearchRequest` (query, repo_id, language, limit), `CodeSearchResult` (chunk_content, file_path, repo_id, language, symbol_name, line_start, line_end, score).

- [ ] **Step 2: Verify**

Run: `cd backend && python -c "from app.schemas.code import RepoCreate, RepoResponse; print('OK')"`

- [ ] **Step 3: Commit**

```
git commit -m "feat(code): add Pydantic schemas for repos and code"
```

---

## Group B: Repository Manager

### Task 4: Create repository CRUD service

**Files:**
- Create: `backend/app/services/repo_manager.py`

- [ ] **Step 1: Create RepoManager**

Create `backend/app/services/repo_manager.py` with a `RepoManager` class that takes an `AsyncSession`. Methods: `create(data: RepoCreate)` — creates repo, stores auth token in Config table if provided, clones if URL given. `get(repo_id)`, `list_all()` — returns repos with file_count and symbol_count via COUNT queries. `update(repo_id, data: RepoUpdate)`. `delete(repo_id)` — removes repo, config token, and clone directory. `get_auth_token(repo)` — reads from Config table. `pull_repo(repo)` — runs git fetch + reset --hard, returns new HEAD SHA. `repo_working_dir(repo)` — returns local_path or clone path. Private methods: `_clone_repo`, `_auth_url` (inserts token into HTTPS URL), `_run_git`. Clone path: `DARKMEM_REPOS_DIR` env var (default `/tmp/darkmem/repos`) / repo.id. All git operations use `asyncio.create_subprocess_exec`.

- [ ] **Step 2: Verify syntax**

Run: `cd backend && python -c "import ast; ast.parse(open('app/services/repo_manager.py').read()); print('OK')"`

- [ ] **Step 3: Commit**

```
git commit -m "feat(code): add RepoManager service for git operations and CRUD"
```

---

### Task 5: Create repository API routes

**Files:**
- Create: `backend/app/api/routes/repos.py`
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add dependency injector for RepoManager**

In `backend/app/api/deps.py`, add `get_repo_manager(session) -> RepoManager`.

- [ ] **Step 2: Create routes**

Create `backend/app/api/routes/repos.py` with CRUD routes: POST (create), GET list, GET by id, PUT update, DELETE. All require auth. Use `_to_response` helper to build `RepoResponse` from model + counts.

- [ ] **Step 3: Register router in main.py**

Add `repos` to the import and `app.include_router(repos.router)`.

- [ ] **Step 4: Verify syntax**

Run: `cd backend && python -c "import ast; ast.parse(open('app/api/routes/repos.py').read()); print('OK')"`

- [ ] **Step 5: Commit**

```
git commit -m "feat(code): add repository management API routes"
```

---

### Task 6: Test repository API

**Files:**
- Create: `backend/tests/test_repos.py`

- [ ] **Step 1: Write tests**

Tests: `test_create_repo_local` (POST with local_path, assert 201 and fields), `test_list_repos` (create two, GET list, assert >= 2), `test_delete_repo` (create, DELETE, assert 204, GET returns 404), `test_repos_require_auth` (GET without auth, assert 401/403).

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/test_repos.py -v`

- [ ] **Step 3: Commit**

```
git commit -m "test(code): add repository API tests"
```

---

## Group C: Code Parser (tree-sitter)

### Task 7: Create the code parser engine

**Files:**
- Create: `backend/app/services/code_parser.py`

- [ ] **Step 1: Create parser**

Create `backend/app/services/code_parser.py` with:

**Data classes:** `ExtractedSymbol` (name, kind, line_start, line_end, signature, docstring, visibility, source_code, children list), `ExtractedImport` (source, names), `ParseResult` (language, symbols, imports, chunks).

**Constants:** `EXTENSION_TO_LANGUAGE` mapping file extensions to language names. `LANGUAGE_MODULES` mapping language names to tree-sitter grammar modules (tree_sitter_python, tree_sitter_typescript, etc). `FUNCTION_NODE_TYPES`, `CLASS_NODE_TYPES`, `IMPORT_NODE_TYPES` sets of AST node type strings. `KIND_MAP` mapping node types to symbol kinds.

**Functions:** `detect_language(file_path) -> str | None`. `parse_file(file_path, content) -> ParseResult | None` — detects language, creates Parser with appropriate Language, parses to AST, walks tree extracting symbols and imports via node type matching, builds chunks. `_fallback_parse` — line-based chunking for unsupported languages.

**Helpers:** `_get_text(node, source)`, `_find_docstring(node, source)`, `_extract_name(node, source)`, `_extract_signature(node, source)`, `_extract_visibility(node, source)`.

**Chunking:** `_build_chunks` — one chunk per symbol, falls back to line-based. `_split_large_symbol` — splits >200 line symbols at 100-line windows with 20-line overlap. `_line_based_chunks` — 100-line windows, 20-line overlap.

The tree-sitter grammar modules are imported as: `import tree_sitter_python as tspython`, etc. Language objects created via `Language(module.language())`.

- [ ] **Step 2: Verify syntax**

Run: `cd backend && python -c "import ast; ast.parse(open('app/services/code_parser.py').read()); print('OK')"`

- [ ] **Step 3: Commit**

```
git commit -m "feat(code): add tree-sitter code parser with generic extraction"
```

---

## Group D: Indexing Pipeline

### Task 8: Create the code indexer service

**Files:**
- Create: `backend/app/services/code_indexer.py`

- [ ] **Step 1: Create CodeIndexer**

Create `backend/app/services/code_indexer.py` with a `CodeIndexer` class taking session, llm, vector_repo, graph_repo. 

**Main method:** `index_repo(repo_id, full=False)` — gets repo, pulls latest, diffs files (or lists all for full reindex), processes each changed file, deletes removed files, updates last_indexed_commit/at.

**File processing:** `_index_file(repo, work_dir, rel_path)` — reads file, computes content_hash, skips if unchanged, parses with `parse_file`, stores symbols to PostgreSQL, chunks to Qdrant `code_chunks` collection, graph nodes/edges to Neo4j.

**Storage helpers:** `_store_symbol` — inserts CodeSymbol with enrichment_priority (exported=2, class=1, other=0). `_store_chunks` — embeds each chunk via llm.embed, upserts to Qdrant with payload. `_store_graph` — creates CodeSymbol nodes, DEFINES edges (file->symbol), CONTAINS edges (parent->child), IMPORTS edges.

**Diff helpers:** `_diff_files(work_dir, old_sha, new_sha)` — runs `git diff --name-status`, returns (changed, deleted) lists. `_list_all_files(work_dir)` — rglob, filtering IGNORED_DIRS and IGNORED_EXTENSIONS.

**Constants:** `IGNORED_DIRS` (`.git`, `node_modules`, `__pycache__`, `.venv`, `dist`, `build`, `target`, `bin`, `obj`), `IGNORED_EXTENSIONS` (`.lock`, `.min.js`, `.map`, `.wasm`, `.pyc`, `.exe`, etc), `MAX_FILE_SIZE` = 500KB.

- [ ] **Step 2: Verify syntax**

Run: `cd backend && python -c "import ast; ast.parse(open('app/services/code_indexer.py').read()); print('OK')"`

- [ ] **Step 3: Commit**

```
git commit -m "feat(code): add CodeIndexer service with diff-based indexing pipeline"
```

---

### Task 9: Ensure code_chunks Qdrant collection on startup

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add collection creation**

In `backend/app/main.py`, after `await vector_repo.ensure_collection()`, add:

```python
code_vector_repo = QdrantVectorRepository(qdrant_client, dimensions=embedding_dims, collection_name="code_chunks")
await code_vector_repo.ensure_collection()
```

- [ ] **Step 2: Verify syntax**

Run: `cd backend && python -c "import ast; ast.parse(open('app/main.py').read()); print('OK')"`

- [ ] **Step 3: Commit**

```
git commit -m "feat(code): ensure code_chunks Qdrant collection on startup"
```

---

### Task 10: Add reindex route and code query routes

**Files:**
- Modify: `backend/app/api/routes/repos.py`
- Create: `backend/app/api/routes/code.py`
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add CodeIndexer dependency injector**

In `backend/app/api/deps.py`, add `get_code_indexer(request, session) -> CodeIndexer` that gets llm, vector_repo, graph_repo from app.state.

- [ ] **Step 2: Add reindex route to repos.py**

Add `POST /{repo_id}/reindex` that takes optional `full` bool param, calls `indexer.index_repo(repo_id, full)`, returns the result dict.

- [ ] **Step 3: Create code query routes**

Create `backend/app/api/routes/code.py` with routes:
- `POST /api/v1/code/search` — semantic search via Qdrant code_chunks collection. Embeds query, applies optional repo_id and language filters, returns CodeSearchResult list.
- `GET /api/v1/code/symbols` — list symbols with filters (repo_id, file_path, kind, name query). Returns paginated response with total.
- `GET /api/v1/code/symbols/{symbol_id}` — symbol detail with source_code, summary, file_path.
- `GET /api/v1/code/files/{repo_id}` — list files with optional path_prefix and language filters.

- [ ] **Step 4: Register code router in main.py**

Add `code` to the route imports and `app.include_router(code.router)`.

- [ ] **Step 5: Verify syntax**

Run: `cd backend && python -c "import ast; ast.parse(open('app/api/routes/code.py').read()); print('OK')"`

- [ ] **Step 6: Commit**

```
git commit -m "feat(code): add reindex route and code query API endpoints"
```

---

## Group E: Enrichment Worker

### Task 11: Create background enrichment worker

**Files:**
- Create: `backend/app/services/enrichment_worker.py`

- [ ] **Step 1: Create EnrichmentWorker**

Create `backend/app/services/enrichment_worker.py` with an `EnrichmentWorker` class taking session and llm. Method `process_batch(batch_size=10)` — queries CodeSymbols where enrichment_status="pending" ordered by priority DESC, sends source_code to LLM with summarization prompt, stores summary, marks completed or failed. Method `run_loop(interval=10, batch_size=5)` — loops processing batches, sleeping when queue is empty. Method `stop()` — sets flag to exit loop.

The LLM prompt: "Summarize what this {kind} does in 1-2 sentences. Be specific about inputs, outputs, and side effects. Do not include the code itself." Uses `llm.chat_completion("summarization", messages=[...])`.

- [ ] **Step 2: Verify syntax**

Run: `cd backend && python -c "import ast; ast.parse(open('app/services/enrichment_worker.py').read()); print('OK')"`

- [ ] **Step 3: Commit**

```
git commit -m "feat(code): add background enrichment worker for LLM summarization"
```

---

## Group F: Webhook and Periodic Sync

### Task 12: Add webhook endpoint and periodic sync

**Files:**
- Modify: `backend/app/api/routes/repos.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add webhook endpoint**

Add `POST /api/v1/repos/webhook` to repos.py. Parses the JSON body, extracts repository URL from `body["repository"]["clone_url"]` or `html_url` or `url`. Matches against registered repos by URL. If matched, triggers `indexer.index_repo`. No auth required (webhooks come from GitHub/GitLab).

- [ ] **Step 2: Add periodic sync to main.py lifespan**

Add an `asyncio.create_task` in the lifespan that loops every 5 minutes, checks all active repos, and triggers indexing for any that are due (based on sync_interval_minutes and last_indexed_at). Cancel the task on shutdown.

- [ ] **Step 3: Verify syntax**

Run: `cd backend && python -c "import ast; ast.parse(open('app/api/routes/repos.py').read()); ast.parse(open('app/main.py').read()); print('OK')"`

- [ ] **Step 4: Commit**

```
git commit -m "feat(code): add webhook endpoint and periodic repo sync"
```

---

## Group G: Dependencies and Verification

### Task 13: Add tree-sitter dependencies

**Files:**
- Modify: `backend/requirements.txt` (or `backend/pyproject.toml`)

- [ ] **Step 1: Check dependency file**

Run: `ls backend/requirements.txt backend/pyproject.toml 2>/dev/null`

- [ ] **Step 2: Add packages**

Add: `tree-sitter>=0.23.0`, `tree-sitter-python>=0.23.0`, `tree-sitter-javascript>=0.23.0`, `tree-sitter-typescript>=0.23.0`, `tree-sitter-go>=0.23.0`, `tree-sitter-rust>=0.23.0`, `tree-sitter-c-sharp>=0.23.0`, `tree-sitter-cpp>=0.23.0`

- [ ] **Step 3: Install**

Run: `cd backend && pip install tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript tree-sitter-go tree-sitter-rust tree-sitter-c-sharp tree-sitter-cpp`

- [ ] **Step 4: Commit**

```
git commit -m "chore(code): add tree-sitter dependencies"
```

---

### Task 14: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Verify all Python files parse**

Run syntax check on all new files: `app/models/code.py`, `app/schemas/code.py`, `app/services/repo_manager.py`, `app/services/code_parser.py`, `app/services/code_indexer.py`, `app/services/enrichment_worker.py`, `app/api/routes/repos.py`, `app/api/routes/code.py`, `app/api/deps.py`, `app/main.py`

- [ ] **Step 2: Run repo API tests**

Run: `cd backend && python -m pytest tests/test_repos.py -v`

- [ ] **Step 3: Verify all imports work**

Run: `cd backend && python -c "from app.models.code import Repository, CodeFile, CodeSymbol; from app.schemas.code import RepoCreate, RepoResponse; from app.services.repo_manager import RepoManager; from app.services.code_parser import parse_file; from app.services.code_indexer import CodeIndexer; from app.services.enrichment_worker import EnrichmentWorker; print('All imports OK')"`

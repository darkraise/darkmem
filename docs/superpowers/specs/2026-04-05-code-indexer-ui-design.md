# Code Indexer UI, Backend Additions, and MCP Tools

## Goal

Add two new pages to the darkmem dashboard for managing indexed repositories and visually exploring code knowledge graphs, plus backend endpoints and MCP tools to support them.

## Scope

- Repositories management page (dashboard + CRUD)
- Code Graph page (GitNexus-inspired visual exploration)
- Backend: graph data endpoint, blast radius endpoint, repo stats endpoint
- MCP tools for coding agents to query code knowledge
- Two new sidebar links

## Pages

### Repositories Page (`/repos`)

Sidebar link with GitBranch icon. Dashboard-style management for indexed repos.

**Summary cards (top):**
- Total repositories (count)
- Total files indexed (count)
- Total symbols extracted (count)
- Enrichment progress (pending/completed percentage)

Data from new `GET /api/v1/repos/stats` endpoint.

**Repo list (below cards):**

Table-style rows. Each row shows: repo name, provider icon (GitHub/GitLab/local), URL or local path, last indexed time (relative), file count, symbol count, active/inactive status indicator. Action buttons per row: Reindex, Edit, Delete.

**Expandable rows:**

Clicking a repo row expands it inline to show:
- File list grouped by language (e.g., "Python: 42 files, TypeScript: 18 files")
- Last indexed commit SHA
- Enrichment progress for this repo (N pending, M completed)

**Add repo dialog:**

Button at top right opens a Dialog with fields:
- Name (text input, required)
- URL (text input, for remote repos)
- Local path (text input, for local repos)
- Provider dropdown (GitHub, GitLab, Local)
- Default branch (text input, defaults to "main")
- GitHub/GitLab token (password input, optional)
- Sync interval in minutes (number input, default 30)

Token stored via existing Config table mechanism.

**Reindex feedback:**

When reindex is triggered, the row shows a spinner/progress indicator. Polls the repo status until indexing completes, then refreshes counts.

### Code Graph Page (`/code-graph`)

Sidebar link with Network icon. Full-height interactive code knowledge graph.

**Layout:** Full-height graph canvas with a toolbar at top and a detail panel (Sheet) on the right.

**Toolbar:**
- Repo selector dropdown (filter to one repo or all)
- View toggle: "File Dependencies" / "Symbol Call Graph" (two buttons)
- Search input: semantic search, highlights matching nodes
- Layout controls: zoom in/out, fit to screen

**File Dependencies view:**
- Nodes are files, colored by language (using existing ENTITY_TYPE_COLORS pattern or a code-specific palette)
- Edges are IMPORTS relationships between files
- Node size scaled by number of symbols defined in the file
- Clicking a file node shows its symbols in the detail panel

**Symbol Call Graph view:**
- Nodes are functions/classes/methods, colored by kind (function=blue, class=green, interface=purple, struct=orange, etc.)
- Edges are CALLS and CONTAINS relationships
- Node size scaled by connection count
- Clicking a symbol node shows full details in the detail panel

**Graph rendering:** Uses Sigma.js + Graphology + ForceAtlas2, same stack as KnowledgeGraph and UnifiedGraph pages. Reuses existing patterns from `Graph2DRenderer.tsx` and `KnowledgeGraphRenderer.tsx` for Sigma setup, node/edge reducers, hover/selection effects.

**Blast radius analysis:**
- Triggered via a "Blast Radius" button in the detail panel (when a symbol is selected)
- Calls `POST /api/v1/code/blast-radius` with the selected symbol ID
- Highlights affected nodes in red/orange, dims all other nodes
- Detail panel shows a list of affected symbols with file paths
- "Clear" button to reset highlighting

**Detail panel:**
- Opens from the right as a Sheet when a node is clicked
- For file nodes: file path, language, symbol list with kinds
- For symbol nodes: name, kind, file path, line range, signature, docstring, LLM summary, source code block, callers list (symbols that call this one), callees list (symbols this one calls)

**Search behavior:**
- Typing in the search bar queries `POST /api/v1/code/search`
- Results shown in a dropdown below the input
- Selecting a result pans/zooms the graph to that node and opens its detail panel
- Matching nodes highlighted in the graph

## Backend Additions

### `GET /api/v1/repos/stats`

Returns aggregate stats for the Repositories dashboard.

```json
{
  "total_repos": 5,
  "total_files": 342,
  "total_symbols": 1847,
  "enrichment_pending": 120,
  "enrichment_completed": 1727
}
```

### `GET /api/v1/code/graph/{repo_id}?view=files|symbols`

Returns graph data for visualization.

**`view=files`** response:
```json
{
  "nodes": [
    { "id": "file-uuid", "label": "src/main.py", "language": "python", "symbol_count": 12 }
  ],
  "edges": [
    { "source": "file-uuid-1", "target": "file-uuid-2", "type": "imports" }
  ]
}
```

**`view=symbols`** response:
```json
{
  "nodes": [
    { "id": "symbol-uuid", "label": "process_memory", "kind": "function", "file_path": "src/pipeline.py", "visibility": "public" }
  ],
  "edges": [
    { "source": "sym-1", "target": "sym-2", "type": "calls" },
    { "source": "class-1", "target": "method-1", "type": "contains" }
  ]
}
```

### `POST /api/v1/code/blast-radius`

Request:
```json
{ "symbol_id": "uuid", "max_depth": 10 }
```

Response:
```json
{
  "source": { "id": "uuid", "name": "process_memory", "file_path": "src/pipeline.py" },
  "affected": [
    { "id": "uuid", "name": "reprocess_all", "kind": "function", "file_path": "src/analytics.py", "depth": 1 },
    { "id": "uuid", "name": "handle_webhook", "kind": "function", "file_path": "src/routes.py", "depth": 2 }
  ],
  "total_affected": 12
}
```

Neo4j query: `MATCH (s:CodeSymbol {id: $id})<-[:CALLS*1..N]-(affected) RETURN affected`

## MCP Tools

Add to existing MCP server at `backend/app/api/mcp/server.py`:

**`code_search(query, repo_name?, language?, limit?)`**
Semantic search across indexed code chunks. Returns matching code with file paths, symbol names, line ranges, and relevance scores.

**`code_symbol(name, repo_name?)`**
Look up a symbol by name. Returns source code, LLM summary, signature, file path, line range, callers, and callees.

**`code_file_symbols(repo_name, file_path)`**
List all symbols extracted from a specific file. Returns names, kinds, line ranges, and summaries.

**`code_blast_radius(symbol_name, repo_name?)`**
Analyze the impact of changing a symbol. Returns all transitively dependent symbols with file paths and depth.

**`code_dependencies(repo_name, file_path?)`**
Show import/dependency relationships for a file or entire repo. Returns import edges.

**`list_repos()`**
List all indexed repositories with name, URL, last indexed time, file count, and symbol count.

## Files to Create or Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `frontend/src/pages/Repositories.tsx` | Repositories management page |
| Create | `frontend/src/pages/CodeGraph.tsx` | Code Graph visualization page |
| Create | `frontend/src/components/graph/CodeGraphRenderer.tsx` | Sigma.js renderer for code graph |
| Create | `frontend/src/hooks/api/useCodeApi.ts` | Hooks for repos, code search, graph, blast radius |
| Modify | `frontend/src/hooks/api/index.ts` | Export new hooks |
| Modify | `frontend/src/App.tsx` | Add routes for /repos and /code-graph |
| Modify | `frontend/src/components/Sidebar.tsx` | Add Repositories and Code Graph nav items |
| Modify | `backend/app/api/routes/repos.py` | Add /repos/stats endpoint |
| Modify | `backend/app/api/routes/code.py` | Add /code/graph/{repo_id} and /code/blast-radius endpoints |
| Modify | `backend/app/api/mcp/server.py` | Add 6 MCP tools for code knowledge |

## Out of Scope

- Inline code editing or modification
- Branch-aware graph (indexes default branch only)
- Diff visualization between commits
- Code Graph 3D view (2D only for now)
- File content viewer page (symbols link to file path but no dedicated file viewer)

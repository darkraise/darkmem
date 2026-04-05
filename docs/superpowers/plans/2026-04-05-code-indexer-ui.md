# Code Indexer UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Repositories management page, Code Graph visualization page, backend graph/blast-radius/stats endpoints, and MCP tools for coding agents to query indexed code.

**Architecture:** Two new frontend pages consuming existing + new backend endpoints. Code Graph uses Sigma.js (same stack as KnowledgeGraph page). MCP tools wrap the code query services. Backend adds three new endpoints to existing route files.

**Tech Stack:** React + TypeScript + Sigma.js + Graphology + ForceAtlas2 (frontend), FastAPI + Neo4j + Qdrant (backend), FastMCP (MCP tools)

**Spec:** `docs/superpowers/specs/2026-04-05-code-indexer-ui-design.md`

---

## Group A: Backend Additions

### Task 1: Add repo stats and graph endpoints

**Files:**
- Modify: `backend/app/api/routes/repos.py`
- Modify: `backend/app/api/routes/code.py`

- [ ] **Step 1: Add stats endpoint to repos.py**

Add `GET /api/v1/repos/stats` that returns aggregate counts. Add this BEFORE the `/{repo_id}` routes (so FastAPI doesn't match "stats" as a UUID):

```python
@router.get("/stats")
async def repo_stats(
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select, func
    from app.models.code import Repository, CodeFile, CodeSymbol
    
    total_repos = (await session.execute(select(func.count()).select_from(Repository))).scalar() or 0
    total_files = (await session.execute(select(func.count()).select_from(CodeFile))).scalar() or 0
    total_symbols = (await session.execute(select(func.count()).select_from(CodeSymbol))).scalar() or 0
    pending = (await session.execute(
        select(func.count()).select_from(CodeSymbol).where(CodeSymbol.enrichment_status == "pending")
    )).scalar() or 0
    completed = (await session.execute(
        select(func.count()).select_from(CodeSymbol).where(CodeSymbol.enrichment_status == "completed")
    )).scalar() or 0
    
    return {
        "total_repos": total_repos,
        "total_files": total_files,
        "total_symbols": total_symbols,
        "enrichment_pending": pending,
        "enrichment_completed": completed,
    }
```

Add the needed import at the top: `from app.database import get_session` and `from sqlalchemy.ext.asyncio import AsyncSession`.

- [ ] **Step 2: Add graph endpoint to code.py**

Add `GET /api/v1/code/graph/{repo_id}` to `backend/app/api/routes/code.py`:

```python
@router.get("/graph/{repo_id}")
async def get_code_graph(
    repo_id: UUID,
    view: str = Query("symbols"),
    _user=Depends(require_auth),
    request: Request = None,
):
    graph_repo = getattr(request.app.state, "graph_repo", None)
    if not graph_repo:
        raise HTTPException(status_code=503, detail="Graph service not available")

    repo_id_str = str(repo_id)

    async with graph_repo.driver.session() as neo_session:
        if view == "files":
            nodes_result = await neo_session.run(
                "MATCH (f:CodeFile {repo_id: $repo_id}) RETURN f",
                repo_id=repo_id_str,
            )
            nodes = []
            async for record in nodes_result:
                f = record["f"]
                nodes.append({"id": f.get("path", ""), "label": f.get("path", ""), "language": None, "symbol_count": 0})

            edges_result = await neo_session.run(
                "MATCH (f1:CodeFile {repo_id: $repo_id})-[:IMPORTS]->(i:CodeImport {repo_id: $repo_id})<-[:IMPORTS]-(f2:CodeFile {repo_id: $repo_id}) WHERE f1.path <> f2.path RETURN DISTINCT f1.path AS source, f2.path AS target",
                repo_id=repo_id_str,
            )
            edges = []
            async for record in edges_result:
                edges.append({"source": record["source"], "target": record["target"], "type": "imports"})

        else:
            nodes_result = await neo_session.run(
                "MATCH (s:CodeSymbol {repo_id: $repo_id}) RETURN s",
                repo_id=repo_id_str,
            )
            nodes = []
            async for record in nodes_result:
                s = record["s"]
                nodes.append({
                    "id": s.get("name", "") + "::" + s.get("file_path", ""),
                    "label": s.get("name", ""),
                    "kind": s.get("kind", "function"),
                    "file_path": s.get("file_path", ""),
                })

            edges_result = await neo_session.run(
                """
                MATCH (s1:CodeSymbol {repo_id: $repo_id})-[r:CALLS|CONTAINS]->(s2:CodeSymbol {repo_id: $repo_id})
                RETURN s1.name + '::' + s1.file_path AS source,
                       s2.name + '::' + s2.file_path AS target,
                       type(r) AS rel_type
                """,
                repo_id=repo_id_str,
            )
            edges = []
            async for record in edges_result:
                edges.append({"source": record["source"], "target": record["target"], "type": record["rel_type"].lower()})

    return {"nodes": nodes, "edges": edges}
```

Add needed import: `from fastapi import Query`.

- [ ] **Step 3: Add blast radius endpoint to code.py**

Add `POST /api/v1/code/blast-radius`:

```python
from pydantic import BaseModel

class BlastRadiusRequest(BaseModel):
    symbol_id: UUID
    max_depth: int = 10

@router.post("/blast-radius")
async def blast_radius(
    body: BlastRadiusRequest,
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    graph_repo = getattr(request.app.state, "graph_repo", None)
    if not graph_repo:
        raise HTTPException(status_code=503, detail="Graph service not available")

    sym = (await session.execute(
        select(CodeSymbol).where(CodeSymbol.id == body.symbol_id)
    )).scalar_one_or_none()
    if not sym:
        raise HTTPException(status_code=404, detail="Symbol not found")

    file = (await session.execute(
        select(CodeFile).where(CodeFile.id == sym.file_id)
    )).scalar_one_or_none()
    repo_id_str = str(file.repo_id) if file else ""

    async with graph_repo.driver.session() as neo_session:
        result = await neo_session.run(
            """
            MATCH (s:CodeSymbol {name: $name, repo_id: $repo_id, file_path: $file_path})
            MATCH (s)<-[:CALLS*1..$depth]-(affected:CodeSymbol)
            RETURN DISTINCT affected.name AS name, affected.kind AS kind,
                   affected.file_path AS file_path, affected.repo_id AS repo_id
            """,
            name=sym.name,
            repo_id=repo_id_str,
            file_path=file.file_path if file else "",
            depth=body.max_depth,
        )
        affected = []
        async for record in result:
            affected.append({
                "name": record["name"],
                "kind": record["kind"],
                "file_path": record["file_path"],
            })

    return {
        "source": {"id": str(sym.id), "name": sym.name, "file_path": file.file_path if file else None},
        "affected": affected,
        "total_affected": len(affected),
    }
```

- [ ] **Step 4: Verify syntax**

Run: `cd backend && python -c "import ast; ast.parse(open('app/api/routes/repos.py').read()); ast.parse(open('app/api/routes/code.py').read()); print('OK')"`

- [ ] **Step 5: Commit**

```
git commit -m "feat(code): add repo stats, code graph, and blast radius endpoints"
```

---

### Task 2: Add MCP tools for code knowledge

**Files:**
- Modify: `backend/app/api/mcp/server.py`

- [ ] **Step 1: Add code service context and 6 MCP tools**

Add a new context manager and tools at the end of `backend/app/api/mcp/server.py`. The tools follow the same pattern as existing memory tools: async context manager yields a service, tool function uses it.

Add these after the existing MCP tools:

```python
@asynccontextmanager
async def _code_service_context():
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        try:
            await session.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            await session.close()
        except Exception:
            pass


@mcp.tool(description="List all indexed code repositories with their status, file counts, and symbol counts.")
async def list_repos() -> str:
    from app.services.repo_manager import RepoManager
    async with _code_service_context() as session:
        manager = RepoManager(session)
        repos = await manager.list_all()
        return json.dumps([{
            "name": r["repo"].name,
            "url": r["repo"].url,
            "local_path": r["repo"].local_path,
            "provider": r["repo"].provider,
            "last_indexed_at": r["repo"].last_indexed_at.isoformat() if r["repo"].last_indexed_at else None,
            "file_count": r["file_count"],
            "symbol_count": r["symbol_count"],
            "is_active": r["repo"].is_active,
        } for r in repos])


@mcp.tool(description="Semantic search across indexed code. Returns matching code chunks with file paths, symbol names, and relevance scores.")
async def code_search(
    query: str,
    repo_name: str | None = None,
    language: str | None = None,
    limit: int = 10,
) -> str:
    """
    Args:
        query: Natural language or code search query.
        repo_name: Filter to a specific repository by name.
        language: Filter by programming language (python, typescript, go, etc.).
        limit: Maximum results to return.
    """
    if not _pipeline or not _pipeline.llm:
        return json.dumps({"error": "LLM not available for code search"})

    vector = await _pipeline.llm.embed(query)

    from qdrant_client.models import FieldCondition, Filter, MatchValue
    conditions = []
    if language:
        conditions.append(FieldCondition(key="language", match=MatchValue(value=language)))

    if repo_name:
        async with _code_service_context() as session:
            from sqlalchemy import select
            from app.models.code import Repository
            repo = (await session.execute(
                select(Repository).where(Repository.name == repo_name)
            )).scalar_one_or_none()
            if repo:
                conditions.append(FieldCondition(key="repo_id", match=MatchValue(value=str(repo.id))))

    qdrant_filter = Filter(must=conditions) if conditions else None
    results = await _pipeline.vector_repo.client.query_points(
        collection_name="code_chunks",
        query=vector,
        limit=limit,
        query_filter=qdrant_filter,
    )

    return json.dumps([{
        "file_path": p.payload.get("file_path", ""),
        "symbol_name": p.payload.get("symbol_name"),
        "chunk_content": p.payload.get("chunk_content", "")[:500],
        "language": p.payload.get("language"),
        "line_start": p.payload.get("line_start", 0),
        "line_end": p.payload.get("line_end", 0),
        "score": p.score,
    } for p in results.points])


@mcp.tool(description="Look up a code symbol by name. Returns source code, LLM summary, signature, callers, and callees.")
async def code_symbol(
    name: str,
    repo_name: str | None = None,
) -> str:
    """
    Args:
        name: Symbol name to look up (function, class, method name).
        repo_name: Filter to a specific repository.
    """
    async with _code_service_context() as session:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.code import CodeSymbol, CodeFile, Repository

        stmt = select(CodeSymbol).join(CodeFile).where(CodeSymbol.name == name)
        if repo_name:
            stmt = stmt.join(Repository, CodeFile.repo_id == Repository.id).where(Repository.name == repo_name)
        stmt = stmt.limit(1)

        sym = (await session.execute(stmt)).scalar_one_or_none()
        if not sym:
            return json.dumps({"error": f"Symbol '{name}' not found"})

        file = (await session.execute(select(CodeFile).where(CodeFile.id == sym.file_id))).scalar_one_or_none()

        return json.dumps({
            "name": sym.name,
            "kind": sym.kind,
            "file_path": file.file_path if file else None,
            "line_start": sym.line_start,
            "line_end": sym.line_end,
            "signature": sym.signature,
            "docstring": sym.docstring,
            "summary": sym.summary,
            "source_code": sym.source_code,
            "visibility": sym.visibility,
        })


@mcp.tool(description="List all symbols in a specific file. Returns names, kinds, line ranges, and summaries.")
async def code_file_symbols(
    repo_name: str,
    file_path: str,
) -> str:
    """
    Args:
        repo_name: Repository name.
        file_path: Relative file path within the repository.
    """
    async with _code_service_context() as session:
        from sqlalchemy import select
        from app.models.code import CodeSymbol, CodeFile, Repository

        stmt = (
            select(CodeSymbol)
            .join(CodeFile)
            .join(Repository, CodeFile.repo_id == Repository.id)
            .where(Repository.name == repo_name, CodeFile.file_path == file_path)
            .order_by(CodeSymbol.line_start)
        )
        symbols = (await session.execute(stmt)).scalars().all()

        return json.dumps([{
            "name": s.name,
            "kind": s.kind,
            "line_start": s.line_start,
            "line_end": s.line_end,
            "signature": s.signature,
            "summary": s.summary,
            "visibility": s.visibility,
        } for s in symbols])


@mcp.tool(description="Analyze blast radius: find all symbols that would be affected by changing the given symbol.")
async def code_blast_radius(
    symbol_name: str,
    repo_name: str | None = None,
    max_depth: int = 10,
) -> str:
    """
    Args:
        symbol_name: Name of the symbol to analyze.
        repo_name: Filter to a specific repository.
        max_depth: Maximum depth of transitive dependency chain.
    """
    async with _code_service_context() as session:
        from sqlalchemy import select
        from app.models.code import CodeSymbol, CodeFile, Repository

        stmt = select(CodeSymbol).join(CodeFile).where(CodeSymbol.name == symbol_name)
        if repo_name:
            stmt = stmt.join(Repository, CodeFile.repo_id == Repository.id).where(Repository.name == repo_name)
        sym = (await session.execute(stmt.limit(1))).scalar_one_or_none()
        if not sym:
            return json.dumps({"error": f"Symbol '{symbol_name}' not found"})

        file = (await session.execute(select(CodeFile).where(CodeFile.id == sym.file_id))).scalar_one_or_none()
        if not file:
            return json.dumps({"error": "File not found for symbol"})

        graph_repo = None
        if _pipeline:
            graph_repo = _pipeline.graph_repo
        if not graph_repo:
            return json.dumps({"error": "Graph service not available"})

        async with graph_repo.driver.session() as neo_session:
            result = await neo_session.run(
                """
                MATCH (s:CodeSymbol {name: $name, repo_id: $repo_id, file_path: $file_path})
                MATCH (s)<-[:CALLS*1..$depth]-(affected:CodeSymbol)
                RETURN DISTINCT affected.name AS name, affected.kind AS kind, affected.file_path AS file_path
                """,
                name=sym.name, repo_id=str(file.repo_id), file_path=file.file_path, depth=max_depth,
            )
            affected = []
            async for record in result:
                affected.append({"name": record["name"], "kind": record["kind"], "file_path": record["file_path"]})

        return json.dumps({
            "source": {"name": sym.name, "kind": sym.kind, "file_path": file.file_path},
            "affected": affected,
            "total_affected": len(affected),
        })


@mcp.tool(description="Show import/dependency relationships for a file or repo.")
async def code_dependencies(
    repo_name: str,
    file_path: str | None = None,
) -> str:
    """
    Args:
        repo_name: Repository name.
        file_path: Optional file path to show dependencies for. If omitted, shows all repo dependencies.
    """
    async with _code_service_context() as session:
        from sqlalchemy import select
        from app.models.code import Repository

        repo = (await session.execute(
            select(Repository).where(Repository.name == repo_name)
        )).scalar_one_or_none()
        if not repo:
            return json.dumps({"error": f"Repository '{repo_name}' not found"})

        graph_repo = None
        if _pipeline:
            graph_repo = _pipeline.graph_repo
        if not graph_repo:
            return json.dumps({"error": "Graph service not available"})

        async with graph_repo.driver.session() as neo_session:
            if file_path:
                result = await neo_session.run(
                    "MATCH (f:CodeFile {path: $path, repo_id: $repo_id})-[:IMPORTS]->(i:CodeImport) RETURN f.path AS file, i.source AS imports",
                    path=file_path, repo_id=str(repo.id),
                )
            else:
                result = await neo_session.run(
                    "MATCH (f:CodeFile {repo_id: $repo_id})-[:IMPORTS]->(i:CodeImport) RETURN f.path AS file, i.source AS imports",
                    repo_id=str(repo.id),
                )

            deps = []
            async for record in result:
                deps.append({"file": record["file"], "imports": record["imports"]})

        return json.dumps(deps)
```

- [ ] **Step 2: Verify syntax**

Run: `cd backend && python -c "import ast; ast.parse(open('app/api/mcp/server.py').read()); print('OK')"`

- [ ] **Step 3: Commit**

```
git commit -m "feat(mcp): add 6 code knowledge tools for coding agents"
```

---

## Group B: Frontend Hooks

### Task 3: Create code API hooks

**Files:**
- Create: `frontend/src/hooks/api/useCodeApi.ts`
- Modify: `frontend/src/hooks/api/index.ts`

- [ ] **Step 1: Create the hooks file**

Create `frontend/src/hooks/api/useCodeApi.ts` with types and hooks for repos, code search, graph data, and blast radius. Uses `useQuery` and `useMutation` from TanStack Query, `apiFetch` from `@/lib/api`.

Types: `RepoStats`, `Repo`, `RepoCreate`, `CodeGraphData` (nodes + edges arrays), `BlastRadiusResult`, `CodeSearchResult`, `CodeSymbolDetail`.

Hooks: `useRepoStats()`, `useRepos()`, `useCreateRepo()`, `useUpdateRepo()`, `useDeleteRepo()`, `useReindexRepo()`, `useCodeGraph(repoId, view)`, `useCodeSearch(params)`, `useCodeSymbol(symbolId)`, `useBlastRadius()`.

- [ ] **Step 2: Export from index.ts**

Add `export * from "./useCodeApi";` to `frontend/src/hooks/api/index.ts`.

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 4: Commit**

```
git commit -m "feat(hooks): add code API hooks for repos, graph, and search"
```

---

## Group C: Repositories Page

### Task 4: Create Repositories page

**Files:**
- Create: `frontend/src/pages/Repositories.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/pages/Repositories.tsx` with:
- Summary cards at top (total repos, files, symbols, enrichment progress) from `useRepoStats()`
- Repo list as table rows from `useRepos()` — name, provider, URL/path, last indexed time, file count, symbol count, status
- Expandable rows showing language breakdown and enrichment progress
- Action buttons: Reindex (calls `useReindexRepo`), Edit, Delete
- Add repo dialog (Dialog component) with form fields for name, url, local_path, provider, branch, token, interval
- Follow same patterns as Memories page (native selects, Card components, Button/Input from shadcn)

- [ ] **Step 2: Add route to App.tsx**

Add import: `import Repositories from "@/pages/Repositories";`
Add route: `<Route path="/repos" element={<Repositories />} />`

- [ ] **Step 3: Add sidebar link**

In `frontend/src/components/Sidebar.tsx`, add import `GitBranch` from lucide-react. Add nav item before the separator: `{ to: "/repos", label: "Repositories", icon: GitBranch }`.

- [ ] **Step 4: Type-check**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 5: Commit**

```
git commit -m "feat(ui): add Repositories management page"
```

---

## Group D: Code Graph Page

### Task 5: Create CodeGraphRenderer component

**Files:**
- Create: `frontend/src/components/graph/CodeGraphRenderer.tsx`

- [ ] **Step 1: Create the Sigma.js renderer**

Create `frontend/src/components/graph/CodeGraphRenderer.tsx` — a Sigma.js + Graphology renderer for code graphs. Follow the same patterns as `KnowledgeGraphRenderer.tsx`:

Props: `nodes` array, `edges` array, `selectedId`, `onSelect` callback, `highlightedIds` (Set for blast radius highlighting).

Internal logic:
- Build Graphology graph from nodes/edges
- Assign colors by kind (function=blue, class=green, interface=purple, struct=orange) or by language (for file view)
- ForceAtlas2 layout with 5-second timeout
- nodeReducer: highlight selected + neighbors, dim others. If highlightedIds is set, highlight those in red/orange and dim everything else (blast radius mode)
- edgeReducer: same selection-based highlighting pattern
- Click handlers: clickNode calls onSelect, clickStage deselects
- ResizeObserver for responsive sizing
- Cleanup on unmount

- [ ] **Step 2: Verify syntax**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```
git commit -m "feat(ui): add CodeGraphRenderer Sigma.js component"
```

---

### Task 6: Create Code Graph page

**Files:**
- Create: `frontend/src/pages/CodeGraph.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/pages/CodeGraph.tsx` with:

**Toolbar:** Repo selector dropdown (from `useRepos()`), view toggle buttons ("Files" / "Symbols"), search input, zoom/fit buttons.

**Graph area:** Full-height `CodeGraphRenderer` consuming data from `useCodeGraph(selectedRepoId, viewMode)`.

**Search:** Input submits to `useCodeSearch()`. Results shown in a dropdown below the input. Selecting a result sets it as the selected node.

**Blast radius:** When a symbol is selected, a "Blast Radius" button appears in the detail panel. Clicking it calls `useBlastRadius()` mutation, which returns affected symbol IDs. These are passed as `highlightedIds` to the renderer. A "Clear" button resets.

**Detail panel:** Sheet that opens on node click. For file nodes: file path, language, symbol list. For symbol nodes: name, kind, signature, summary, source code, callers, callees. Source code displayed in a `<pre>` block with monospace font. "Blast Radius" button at bottom.

- [ ] **Step 2: Add route to App.tsx**

Add import: `import CodeGraph from "@/pages/CodeGraph";`
Add route: `<Route path="/code-graph" element={<CodeGraph />} />`

- [ ] **Step 3: Add sidebar link**

In Sidebar.tsx, add import `GitGraph` from lucide-react. Add nav item after Repositories: `{ to: "/code-graph", label: "Code Graph", icon: GitGraph }`.

- [ ] **Step 4: Type-check**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 5: Commit**

```
git commit -m "feat(ui): add Code Graph visualization page with blast radius"
```

---

## Group E: Verification

### Task 7: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Backend syntax check**

Run: `cd backend && python -c "import ast; ast.parse(open('app/api/routes/repos.py').read()); ast.parse(open('app/api/routes/code.py').read()); ast.parse(open('app/api/mcp/server.py').read()); print('OK')"`

- [ ] **Step 2: Frontend type-check**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Verify new pages render**

Check that `/repos` and `/code-graph` routes are registered in App.tsx, sidebar links exist, and imports resolve correctly.

- [ ] **Step 4: Verify MCP tools registered**

Run: `cd backend && python -c "from app.api.mcp.server import mcp; print([t.name for t in mcp._tool_manager._tools.values()])"`
Expected: list includes `list_repos`, `code_search`, `code_symbol`, `code_file_symbols`, `code_blast_radius`, `code_dependencies`

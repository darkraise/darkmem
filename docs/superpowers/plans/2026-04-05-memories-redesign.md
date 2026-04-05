# Memories Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the plain Memories page with a polished browser featuring paginated search, filters, bulk actions, and a detail side panel — absorbing the separate Search page.

**Architecture:** New `POST /memories/search/paginated` endpoint adds offset-based pagination without changing the existing search endpoint. Frontend rewrites the Memories page with hybrid two-line rows, filter dropdowns, checkbox selection, bulk actions, and a Sheet side panel. The Search page is removed (Chat handles Reason/Q&A).

**Tech Stack:** FastAPI + SQLAlchemy (backend), React + TanStack Query + shadcn/ui (frontend)

**Spec:** `docs/superpowers/specs/2026-04-05-memories-redesign-design.md`

---

### Task 1: Backend — Add paginated search endpoint

**Files:**
- Modify: `backend/app/schemas/memory.py`
- Modify: `backend/app/services/memory.py`
- Modify: `backend/app/api/routes/memories.py`

The existing `MemorySearchRequest` schema already has `query`, `tags_any`, `tags_all`, `memory_type`, `source`, and `limit`. We just need to add `offset` for pagination, create a paginated response schema, a service method, and a route.

- [ ] **Step 1: Add `offset` to `MemorySearchRequest` and create paginated response schema**

In `backend/app/schemas/memory.py`, add `offset` field to `MemorySearchRequest` and add a new response model after `MemoryResponse`:

```python
class MemorySearchRequest(BaseModel):
    query: str | None = None
    tags_any: list[str] | None = None
    tags_all: list[str] | None = None
    memory_type: str | None = None
    source: str | None = None
    limit: int = 20
    offset: int = 0


class PaginatedMemoryResponse(BaseModel):
    items: list[MemoryResponse]
    total: int
    limit: int
    offset: int
```

- [ ] **Step 2: Add `search_memories_paginated` to `MemoryService`**

In `backend/app/services/memory.py`, add this method after `search_memories`:

```python
    async def search_memories_paginated(self, params: MemorySearchRequest) -> dict:
        if params.query and self.pipeline:
            semantic_results = await self.pipeline.semantic_search(params.query, limit=params.limit + params.offset + 50)
            if semantic_results:
                memory_ids = [r["memory_id"] for r in semantic_results]
                memories = []
                for mid in memory_ids:
                    m = await self.memory_repo.get(mid)
                    if m and not m.is_archived:
                        if params.memory_type and m.memory_type != params.memory_type:
                            continue
                        if params.source and m.source != params.source:
                            continue
                        if params.tags_any:
                            tag_names = [t.name for t in m.tags]
                            if not any(t in tag_names for t in params.tags_any):
                                continue
                        memories.append(m)
                total = len(memories)
                page = memories[params.offset:params.offset + params.limit]
                return {"items": page, "total": total, "limit": params.limit, "offset": params.offset}

        items, total = await self.memory_repo.search_by_tags_paginated(
            query=params.query, tags_any=params.tags_any, tags_all=params.tags_all,
            memory_type=params.memory_type, source=params.source,
            limit=params.limit, offset=params.offset,
        )
        return {"items": items, "total": total, "limit": params.limit, "offset": params.offset}
```

- [ ] **Step 3: Add `search_by_tags_paginated` to `PostgresMemoryRepository`**

In `backend/app/repositories/relational.py`, add this method after `search_by_tags`:

```python
    async def search_by_tags_paginated(self, query=None, tags_any=None, tags_all=None, memory_type=None, source=None, limit=20, offset=0):
        base = select(Memory).options(selectinload(Memory.tags)).where(Memory.is_archived == False)  # noqa: E712

        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            base = base.where(Memory.content.ilike(f"%{escaped}%"))

        if tags_any:
            base = base.where(Memory.tags.any(Tag.name.in_(tags_any)))

        if tags_all:
            for tag_name in tags_all:
                base = base.where(Memory.tags.any(Tag.name == tag_name))

        if memory_type:
            base = base.where(Memory.memory_type == memory_type)

        if source:
            base = base.where(Memory.source == source)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        items_stmt = base.order_by(Memory.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(items_stmt)
        return list(result.scalars().all()), total
```

- [ ] **Step 4: Add the route**

In `backend/app/api/routes/memories.py`, add after the existing `/search` route. Import `PaginatedMemoryResponse` from the schemas:

```python
@router.post("/search/paginated", response_model=PaginatedMemoryResponse)
async def search_memories_paginated(
    body: MemorySearchRequest,
    _user=Depends(require_auth),
    service: MemoryService = Depends(get_memory_service),
):
    result = await service.search_memories_paginated(body)
    return PaginatedMemoryResponse(
        items=[_to_response(m) for m in result["items"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )
```

- [ ] **Step 5: Verify syntax**

Run: `cd backend && python -c "import ast; ast.parse(open('app/schemas/memory.py').read()); ast.parse(open('app/services/memory.py').read()); ast.parse(open('app/repositories/relational.py').read()); ast.parse(open('app/api/routes/memories.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/memory.py backend/app/services/memory.py backend/app/repositories/relational.py backend/app/api/routes/memories.py
git commit -m "feat(memories): add paginated search endpoint"
```

---

### Task 2: Backend — Test paginated search

**Files:**
- Create: `backend/tests/test_paginated_search.py`

- [ ] **Step 1: Write the tests**

```python
from app.models.memory import Memory


async def test_paginated_search_returns_structure(client, session, auth_headers):
    for i in range(3):
        session.add(Memory(content=f"paginated test {i}", source="api"))
    await session.flush()

    resp = await client.post(
        "/api/v1/memories/search/paginated",
        json={"limit": 2, "offset": 0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert data["total"] >= 3
    assert len(data["items"]) == 2


async def test_paginated_search_offset(client, session, auth_headers):
    for i in range(5):
        session.add(Memory(content=f"offset test {i}", source="api"))
    await session.flush()

    page1 = await client.post(
        "/api/v1/memories/search/paginated",
        json={"limit": 2, "offset": 0},
        headers=auth_headers,
    )
    page2 = await client.post(
        "/api/v1/memories/search/paginated",
        json={"limit": 2, "offset": 2},
        headers=auth_headers,
    )
    ids1 = {m["id"] for m in page1.json()["items"]}
    ids2 = {m["id"] for m in page2.json()["items"]}
    assert ids1.isdisjoint(ids2)


async def test_paginated_search_filters(client, session, auth_headers):
    session.add(Memory(content="filter by source", source="dashboard"))
    session.add(Memory(content="filter by source other", source="api"))
    await session.flush()

    resp = await client.post(
        "/api/v1/memories/search/paginated",
        json={"source": "dashboard", "limit": 50},
        headers=auth_headers,
    )
    data = resp.json()
    assert all(m["source"] == "dashboard" for m in data["items"])


async def test_paginated_search_requires_auth(client):
    resp = await client.post("/api/v1/memories/search/paginated", json={})
    assert resp.status_code in (401, 403)
```

- [ ] **Step 2: Run the tests**

Run: `cd backend && python -m pytest tests/test_paginated_search.py -v`
Expected: 4 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_paginated_search.py
git commit -m "test(memories): add paginated search endpoint tests"
```

---

### Task 3: Frontend — Add `usePaginatedSearch` hook

**Files:**
- Modify: `frontend/src/hooks/api/useMemoryApi.ts`

- [ ] **Step 1: Add types and hook**

Append at the end of the file (after `useTags`):

```typescript
export interface PaginatedSearchParams {
  query?: string;
  tags_any?: string[];
  source?: string;
  memory_type?: string;
  limit?: number;
  offset?: number;
}

export interface PaginatedMemories {
  items: Memory[];
  total: number;
  limit: number;
  offset: number;
}

export function usePaginatedSearch(params: PaginatedSearchParams) {
  return useQuery<PaginatedMemories>({
    queryKey: ["memoriesPaginated", params],
    queryFn: () =>
      apiFetch("/memories/search/paginated", {
        method: "POST",
        body: JSON.stringify({
          query: params.query || undefined,
          tags_any: params.tags_any?.length ? params.tags_any : undefined,
          source: params.source || undefined,
          memory_type: params.memory_type || undefined,
          limit: params.limit ?? 50,
          offset: params.offset ?? 0,
        }),
      }),
  });
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/api/useMemoryApi.ts
git commit -m "feat(hooks): add usePaginatedSearch hook"
```

---

### Task 4: Frontend — Rewrite Memories page

**Files:**
- Rewrite: `frontend/src/pages/Memories.tsx`

This is the largest task. The page has: search bar, filter dropdowns, memory list with checkboxes, pagination, bulk action bar, and a detail side panel.

- [ ] **Step 1: Write the complete Memories page**

Replace the entire file with:

```tsx
import { useState, useMemo } from "react";
import { usePaginatedSearch, useDeleteMemory, useTags } from "@/hooks/useApi";
import type { Memory } from "@/hooks/useApi";
import { apiFetch } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetClose,
} from "@/components/ui/sheet";
import { X } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

const PAGE_SIZE = 50;

const SOURCE_COLORS: Record<string, string> = {
  "claude-code": "#58a6ff",
  "mcp-test": "#3fb950",
  api: "#d2a8ff",
  "rest-test": "#ffa657",
  dashboard: "#f778ba",
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function Memories() {
  const [searchInput, setSearchInput] = useState("");
  const [query, setQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [detailMemory, setDetailMemory] = useState<Memory | null>(null);

  const { data, isLoading } = usePaginatedSearch({
    query: query || undefined,
    tags_any: tagFilter ? [tagFilter] : undefined,
    source: sourceFilter || undefined,
    memory_type: typeFilter || undefined,
    limit: PAGE_SIZE,
    offset,
  });
  const { data: tagsData } = useTags();
  const deleteMemory = useDeleteMemory();
  const qc = useQueryClient();

  const memories = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageStart = offset + 1;
  const pageEnd = Math.min(offset + PAGE_SIZE, total);

  const distinctSources = useMemo(() => {
    const set = new Set(memories.map((m) => m.source));
    return Array.from(set).sort();
  }, [memories]);

  const distinctTypes = useMemo(() => {
    const set = new Set(memories.map((m) => m.memory_type).filter(Boolean) as string[]);
    return Array.from(set).sort();
  }, [memories]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setQuery(searchInput);
    setOffset(0);
    setSelected(new Set());
  };

  const handleFilterChange = (setter: (v: string) => void) => (value: string) => {
    setter(value === "__all__" ? "" : value);
    setOffset(0);
    setSelected(new Set());
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === memories.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(memories.map((m) => m.id)));
    }
  };

  const handleDelete = (id: string) => {
    if (!window.confirm("Delete this memory?")) return;
    deleteMemory.mutate(id, {
      onSuccess: () => {
        setSelected((prev) => { const next = new Set(prev); next.delete(id); return next; });
        if (detailMemory?.id === id) setDetailMemory(null);
        qc.invalidateQueries({ queryKey: ["memoriesPaginated"] });
      },
    });
  };

  const handleBulkDelete = () => {
    if (!window.confirm(`Delete ${selected.size} memories?`)) return;
    const ids = Array.from(selected);
    Promise.all(ids.map((id) => deleteMemory.mutateAsync(id))).then(() => {
      setSelected(new Set());
      setDetailMemory(null);
      qc.invalidateQueries({ queryKey: ["memoriesPaginated"] });
    });
  };

  const handleBulkArchive = () => {
    if (!window.confirm(`Archive ${selected.size} memories?`)) return;
    const ids = Array.from(selected);
    Promise.all(ids.map((id) => apiFetch(`/memories/${id}`, { method: "PUT", body: JSON.stringify({ is_archived: true }) }))).then(() => {
      setSelected(new Set());
      setDetailMemory(null);
      qc.invalidateQueries({ queryKey: ["memoriesPaginated"] });
    });
  };

  return (
    <div className="p-6 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Memories</h2>
        {total > 0 && (
          <span className="text-sm text-muted-foreground">{total} memories</span>
        )}
      </div>

      {/* Search + filters */}
      <form onSubmit={handleSearch} className="flex flex-col lg:flex-row gap-2 mb-4">
        <Input
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search memories..."
          className="flex-1"
        />
        <div className="flex gap-2 flex-wrap">
          <Select value={sourceFilter || "__all__"} onValueChange={handleFilterChange(setSourceFilter)}>
            <SelectTrigger className="w-32"><SelectValue placeholder="Source" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All sources</SelectItem>
              {distinctSources.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={tagFilter || "__all__"} onValueChange={handleFilterChange(setTagFilter)}>
            <SelectTrigger className="w-32"><SelectValue placeholder="Tags" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All tags</SelectItem>
              {tagsData?.map((t) => <SelectItem key={t.name} value={t.name}>{t.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={typeFilter || "__all__"} onValueChange={handleFilterChange(setTypeFilter)}>
            <SelectTrigger className="w-32"><SelectValue placeholder="Type" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All types</SelectItem>
              {distinctTypes.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button type="submit" size="sm">Search</Button>
        </div>
      </form>

      {/* Loading */}
      {isLoading && <p className="text-muted-foreground">Loading...</p>}

      {/* Memory list */}
      {!isLoading && memories.length === 0 && (
        <p className="text-muted-foreground">
          {query || sourceFilter || tagFilter || typeFilter
            ? "No memories match your filters."
            : "No memories yet. Create one via the API or Claude Code to get started."}
        </p>
      )}

      {memories.length > 0 && (
        <Card className="flex-1 overflow-hidden">
          <CardContent className="p-0">
            {/* Select all header */}
            <div className="flex items-center gap-3 px-4 py-2 border-b border-border text-xs text-muted-foreground">
              <input
                type="checkbox"
                checked={selected.size === memories.length && memories.length > 0}
                onChange={toggleSelectAll}
                className="accent-primary"
              />
              <span>Select all</span>
            </div>

            {/* Rows */}
            <div className="divide-y divide-border">
              {memories.map((m) => (
                <div
                  key={m.id}
                  className={`flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-accent/30 ${selected.has(m.id) ? "bg-accent/20" : ""}`}
                  onClick={() => setDetailMemory(m)}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(m.id)}
                    onChange={(e) => { e.stopPropagation(); toggleSelect(m.id); }}
                    onClick={(e) => e.stopPropagation()}
                    className="accent-primary mt-1"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm truncate flex-1">{m.content}</span>
                      <button
                        className="text-muted-foreground hover:text-destructive shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={(e) => { e.stopPropagation(); handleDelete(m.id); }}
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground flex-wrap">
                      {m.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-[10px] px-1.5 py-0">{tag}</Badge>
                      ))}
                      <span className="ml-auto flex items-center gap-1.5 shrink-0">
                        <span style={{ color: SOURCE_COLORS[m.source] ?? "#8b949e" }}>{m.source}</span>
                        {m.memory_type && <><span>·</span><span>{m.memory_type}</span></>}
                        <span>·</span>
                        <span>{relativeTime(m.created_at)}</span>
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between mt-3 text-sm text-muted-foreground">
          <span>Showing {pageStart}–{pageEnd} of {total}</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => { setOffset(Math.max(0, offset - PAGE_SIZE)); setSelected(new Set()); }}>
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={offset + PAGE_SIZE >= total} onClick={() => { setOffset(offset + PAGE_SIZE); setSelected(new Set()); }}>
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Bulk action bar */}
      {selected.size > 0 && (
        <div className="flex items-center gap-4 mt-3 p-3 bg-card border border-border rounded-lg text-sm">
          <span className="text-primary font-medium">{selected.size} selected</span>
          <Button variant="destructive" size="sm" onClick={handleBulkDelete}>Delete</Button>
          <Button variant="outline" size="sm" onClick={handleBulkArchive}>Archive</Button>
        </div>
      )}

      {/* Detail side panel */}
      <Sheet open={!!detailMemory} onOpenChange={(open) => { if (!open) setDetailMemory(null); }}>
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-base">Memory Details</SheetTitle>
          </SheetHeader>
          {detailMemory && (
            <div className="space-y-4 mt-4">
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-1">Content</div>
                <p className="text-sm whitespace-pre-wrap">{detailMemory.content}</p>
              </div>
              {detailMemory.tags.length > 0 && (
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-1">Tags</div>
                  <div className="flex gap-1.5 flex-wrap">
                    {detailMemory.tags.map((tag) => <Badge key={tag} variant="secondary">{tag}</Badge>)}
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">Source</div>
                  <span style={{ color: SOURCE_COLORS[detailMemory.source] ?? "#c9d1d9" }}>{detailMemory.source}</span>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">Type</div>
                  <span>{detailMemory.memory_type ?? "—"}</span>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">Importance</div>
                  <span>{detailMemory.importance}</span>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">Created</div>
                  <span>{new Date(detailMemory.created_at).toLocaleString()}</span>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">Updated</div>
                  <span>{new Date(detailMemory.updated_at).toLocaleString()}</span>
                </div>
              </div>
              <div className="pt-3 border-t border-border">
                <Button variant="destructive" size="sm" onClick={() => handleDelete(detailMemory.id)}>
                  Delete Memory
                </Button>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean (if `SheetContent` doesn't accept `side` prop, check the Sheet component API and adjust)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Memories.tsx
git commit -m "feat(memories): redesign page with search, filters, pagination, and side panel"
```

---

### Task 5: Frontend — Remove Search page and sidebar link

**Files:**
- Delete: `frontend/src/pages/Search.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Remove the Search route from App.tsx**

In `frontend/src/App.tsx`:

Remove the import line:
```typescript
import Search from "@/pages/Search";
```

Remove the route line:
```typescript
<Route path="/search" element={<Search />} />
```

- [ ] **Step 2: Remove the Search link from Sidebar.tsx**

In `frontend/src/components/Sidebar.tsx`:

Remove the Search nav item from the `navItems` array:
```typescript
{ to: "/search", label: "Search", icon: Search },
```

Also remove the `Search` import from lucide-react (it's used as both nav icon and nav item — check if `Search` icon is used elsewhere; if not, remove from the import).

- [ ] **Step 3: Delete the Search page file**

Delete `frontend/src/pages/Search.tsx`.

- [ ] **Step 4: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean. If there are references to `useSearchMemories` or `useReason` that are now unused, they can stay in the hooks file — they're still exported and may be used by the MCP or other consumers.

- [ ] **Step 5: Commit**

```bash
git rm frontend/src/pages/Search.tsx
git add frontend/src/App.tsx frontend/src/components/Sidebar.tsx
git commit -m "refactor: remove Search page, absorb into Memories"
```

---

### Task 6: Verify full build

**Files:** none (verification only)

- [ ] **Step 1: Type-check frontend**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean

- [ ] **Step 2: Backend syntax check**

Run: `cd backend && python -c "import ast; ast.parse(open('app/schemas/memory.py').read()); ast.parse(open('app/services/memory.py').read()); ast.parse(open('app/repositories/relational.py').read()); ast.parse(open('app/api/routes/memories.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Run backend tests**

Run: `cd backend && python -m pytest tests/test_paginated_search.py -v`
Expected: all tests PASS

- [ ] **Step 4: Build frontend**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: build completes (pre-existing warnings in unmodified files are acceptable)

- [ ] **Step 5: Verify no dangling Search references**

Run: `cd frontend/src && grep -r "Search" --include="*.tsx" --include="*.ts" -l`
Expected: no references to the deleted Search page (search-related hooks in useMemoryApi.ts are fine — they're reusable)

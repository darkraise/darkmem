# Workspace UI Implementation Plan (Increment 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementer assignments:** each task names its implementer agent in an
> `**Implementer:**` line. When executing with
> superpowers:subagent-driven-development, REQUIRED SUB-SKILL:
> dcc-superpower-companions:dispatching-tiered-implementers. Under
> superpowers:executing-plans these lines are inert; ignore them.

**Goal:** The project workspace: a `/projects` index of every project the corpus holds, and a `/projects/$project` workspace with an Artifacts tab (uri-segment document tree, outline, block reader, section search) and a Progress tab (pinned ledger document plus the project's checkpoint runs). `/documents` stays the personal surface and re-renders through the same extracted components. This is the spec's increment 4, **as amended by §2.1: it is not backend-free** — the projects endpoint is memories-only and must become the corpus-unioning scope source.

**Architecture:** One backend change, then composition. `GET /api/v1/projects` is widened in place to derive from all three project-carrying corpora (`memories`, `documents`, `session_checkpoints`) with the aggregates the index cards need; everything else is frontend composition over shipped document routes and darkraise-ui primitives (`tree-view`, `tabs`, `card`, `stat`, `combobox`, `empty-state`, `skeleton`, `badge` — all enumerated in `frontend/node_modules/darkraise-ui/dist/components/`, none re-implemented locally). The document list/outline/reader are extracted into shared components under `frontend/src/features/documents/components/` so the workspace, the personal surface — and increment 8's editor — render one implementation.

**Spec:** `docs/superpowers/specs/2026-08-31-project-artifact-store-design.md` §2 (as amended by §2.1), §3, §6 (increment 4).
**Review:** M2 (projects endpoint memories-only — fixed here, Task 1), m1 (list clamp truncates the tree — fixed here, Task 3), m2 (checkpoint history is content-free — carried, Task 6, consistent with `docs/superpowers/plans/2026-08-31-watchable-progress.md`). Where spec and review disagree, the review wins.

**Amendments (2026-09-02, cross-plan adversarial review of all eight plans).** Three defects, fixed in place: **B-3** — the new `_seed_document` helper calls `upsert_by_uri`, whose signature increment 3 changes; the coupling is now stated in the Prerequisites and the helper passes `content=None` explicitly (Task 1). **m-1** — this plan claimed three existing tests in `test_projects_endpoint.py` pass untouched; there are four, and `test_counts_every_status_not_only_active` asserts exact dict equality that the new fields break (Task 1 Step 1). **M-7** — the `table` component deferral contradicts spec §2 and is now recorded as a stated deviation with the one additive read change that would close it (Task 5 Step 1). Tasks 2, 3, 4, 6 and 7 were found sound, and the components this plan owns (`BlockView`, `DocumentTree`, `buildUriTree`) match increment 8's call sites exactly.

## Prerequisites

1. **Increment 1 is landed** (`docs/superpowers/plans/2026-08-31-watchable-progress.md`): Task 6 consumes its `useCheckpointRuns(project: string | null)` signature and `LIVE_POLL_MS` export, and extends the `CheckpointsTab` that plan reshapes. Executing this plan first would produce a merge conflict on the same files.
2. **Increments 2, 3 and 5 are NOT prerequisites — with one coupling to increment 3 that is not a prerequisite but must be honoured** (cross-plan review B-3, 2026-09-02). Nothing here reads `documents.content`, the oversized-warning fields or the imported corpus. The workspace renders empty states until increment 5 files the corpus; landing 4 before 5 just means the owner sees the empty shell first. (Increment 5's plan requires 2 and 3 before *it* runs; this plan is independent of that chain.)

   The coupling is a **shared signature**: increment 3 adds a keyword-only `content` parameter to `repositories.documents.upsert_by_uri`, which this plan's new test helper calls. Increment 3 has been amended to give that parameter a `= None` default, so the two compose in either order — **but this plan's helper must pass `content=None` explicitly anyway** (Task 1 Step 1), so it reads correctly against both signatures and states which column it is deliberately leaving empty. Do not remove that argument as redundant; it is the marker that this seam was checked.

## The scope-source decision (review M2), recorded

**Decision: widen `GET /api/v1/projects` in place to a derived union over `memories`, `documents` and `session_checkpoints`. No new endpoint, no registry write.** The alternatives, and why they lose:

- **Register projects on document filing** (`project_registry.register` from `document_ingest`) repairs one corpus of three — `checkpoint_save` does not register either, so a checkpoint-only project stays invisible — and it inverts the route's own documented stance (`backend/app/api/routes/projects.py:15-20`: "derived, never a registry"). Registry rows also outlive content: a project whose last document is deleted would haunt the picker forever, where a derivation self-heals. The `projects` registry table keeps its real job (`compute_triple_key` namespace identity, `backend/app/models/project.py`); it is not a UI catalogue and does not become one here.
- **A second endpoint** (`GET /api/v1/projects/summary` or similar) means two scope catalogues that can disagree — the switcher fed by one and the index by the other is the M2 trap moved one door over. One source, both consumers.
- **REST conventions** (`docs/api-rest-conventions.md`): this stays a collection `GET` answering 200 — no complex query, so no `POST .../search`; the new fields are additive on the existing response model, and `sdks/generate.py` binds no projects verb, so `make generate` is a zero-diff verification, not a regeneration.

**Latest-event age is served at day granularity, deliberately.** `events` is RANGE-partitioned by month with no `(project, created_at)` index; the one project-keyed index is `ix_events_day` on `(project, ((created_at AT TIME ZONE 'UTC')::date))` (`backend/migrations/versions/0001_baseline.py:1475`). The query reuses that indexed expression **verbatim** (the same rule CLAUDE.md states for the calendar bucket) and reports the latest UTC day, not a timestamp — "active today / 3 days ago" is what an index-only scan can serve, and a card does not need seconds. Do not "improve" this to `max(created_at)`: that is a full scan of every monthly partition.

## Global Constraints

- **Backend tests** (from `backend/`): `.venv/bin/python -m pytest -q`. Needs the `darkmem_test` database on the dev-compose Postgres (127.0.0.1:5433) per CLAUDE.md.
- **Frontend** (from `frontend/`): `npm run typecheck` (= `tsc -b`), `npm test` (vitest), `npm run build`. `routeTree.gen.ts` is generated — new route files regenerate it via the router plugin during dev/build; **never hand-edit it**.
- **Merge gate:** `./scripts/gate.sh` before the final commit. `--full` is unreliable on this host (earlyoom kills Chromium); never invoke Playwright bare — `backend/scripts/e2e/run_playwright_e2e.py` only.
- **UI components come from darkraise-ui first.** Every primitive this plan names ships there; read the `.d.ts` beside the component before using it (`tree-view.d.ts` exposes a composable `TreeView`/`TreeViewBranch`/`TreeViewItem` API plus a data-driven `TreeViewNode`).
- **Demo mode must make no API calls** (session memory): every new query rides `enabled: !DEMO`. The Playwright spec `tests/demo-makes-no-api-calls.spec.ts` is the enforcement; do not fight it.
- **Do not re-derive the checkpoint m2 limit.** The timeline is content-free and only the latest note's text is readable; `2026-08-31-watchable-progress.md` states this and Task 6 must stay consistent with it — no claim of step-content history anywhere in the new copy.
- **Commits:** `<type>(<scope>): <subject>`, ≤50 chars, imperative. A `feat` on master cuts a release; the final task writes the CHANGELOG section.
- **Comments:** only where the WHY is non-obvious.

## File Structure

```
backend/app/api/routes/projects.py                       # Task 1: corpus-union derivation
backend/tests/test_projects_endpoint.py                  # Task 1: extend
frontend/src/hooks/api/use-projects-api.ts               # Task 2: widened ProjectSummary
frontend/src/components/app-chrome/project-switcher.tsx  # Task 2: copy + hint
frontend/src/hooks/api/use-documents-api.ts              # Task 3: stitch + outline/blocks/search hooks
frontend/src/features/documents/uri-tree.ts              # Task 4: pure grouping util (create)
frontend/src/features/documents/components/document-tree.tsx    # Task 4 (create)
frontend/src/features/documents/components/block-view.tsx       # Task 5 (create)
frontend/src/features/documents/components/document-reader.tsx  # Task 5 (create)
frontend/src/routes/_authenticated/projects_.$project.tsx       # Task 6 (create)
frontend/src/features/activity/components/checkpoints-tab.tsx   # Task 6: optional project prop
frontend/src/routes/_authenticated/projects.tsx                 # Task 7 (create)
frontend/src/routes/_authenticated.tsx                          # Task 7: nav entries
frontend/src/features/documents/components/documents-view.tsx   # Task 8: refactor onto shared parts
frontend/src/features/documents/__tests__/                      # Tasks 4, 5, 8: extend
CHANGELOG.md                                                    # Task 9
```

---

### Task 1: The projects endpoint derives from every corpus that carries a project

**Files:**
- Modify: `backend/app/api/routes/projects.py` (whole route body, `backend/app/api/routes/projects.py:38-49`)
- Modify: `backend/tests/test_projects_endpoint.py`

**Interfaces:**
- Consumes: `memories.project`, `documents.project`, `session_checkpoints.project`, `events(project, created_at)` — all shipped columns; `ix_session_checkpoints_latest` (`0001_baseline.py:752`) serves the checkpoint max, `ix_events_day` (`0001_baseline.py:1475`) serves the event day.
- Produces: the widened `ProjectSummary` — the one scope source Tasks 2, 6 and 7 consume.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4
**Approach:** inline - skip 3: the spec's §2.1 amendment fixes the requirement and the widen-vs-register decision is recorded in this plan's header, with the alternatives and their costs.

- [ ] **Step 1: Write the failing tests**

Extend `backend/tests/test_projects_endpoint.py`. **There are four existing tests, not three, and one of them must change** (cross-plan review m-1, 2026-09-02): `test_counts_every_status_not_only_active` (`:54-72`) ends in `assert resp.json() == [{"name": "mixed", "memory_count": 2}]` — exact dict equality, which fails the moment `document_count` joins the response. Widen that assertion to the new shape (`memory_count` 2, `document_count` 0, `checkpoint_count` 0) in this step, as part of the same change that adds the fields; do not weaken it to a subset match, because exact equality is what makes it catch an accidental extra field. The other three (`test_list_projects_requires_auth`, `test_lists_distinct_projects_busiest_first`, `test_empty_corpus_lists_no_projects`) pass untouched. Add:

```python
from uuid import uuid4

from app.models.checkpoint import SessionCheckpoint
from app.repositories.documents import upsert_by_uri


async def _seed_document(session, project: str, uri: str) -> None:
    await upsert_by_uri(
        session, document_id=uuid4(), project=project, uri=uri,
        title=None, source_type="md", content_hash="x" * 64, properties=None,
        # Increment 3 adds this keyword (defaulted to None there, so this file
        # compiles against both signatures). Passed explicitly rather than
        # omitted: the project index counts documents and never reads their
        # source, so a seeded row with no content is the honest fixture.
        content=None,
    )


@pytest.mark.asyncio
async def test_a_document_only_project_is_visible(client, auth_headers, session):
    """Review M2: the increment-5 corpus import creates exactly this shape —
    documents, zero memories — and the index must show it."""
    await _seed_document(session, "docs-only", "docs/readme.md")
    await session.flush()

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    body = {p["name"]: p for p in resp.json()}
    assert "docs-only" in body
    assert body["docs-only"]["memory_count"] == 0
    assert body["docs-only"]["document_count"] == 1


@pytest.mark.asyncio
async def test_a_checkpoint_only_project_is_visible(client, auth_headers, session):
    session.add(SessionCheckpoint(
        origin_key="cc-run-1", project="ckpt-only", summary="s", next_steps=[],
    ))
    await session.flush()

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    body = {p["name"]: p for p in resp.json()}
    assert "ckpt-only" in body
    assert body["ckpt-only"]["checkpoint_count"] == 1
    assert body["ckpt-only"]["last_checkpoint_at"] is not None


@pytest.mark.asyncio
async def test_one_project_in_two_corpora_is_one_row(client, auth_headers, session):
    await _seed(session, ("m", "both"))
    await _seed_document(session, "both", "docs/a.md")
    await session.flush()

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    rows = [p for p in resp.json() if p["name"] == "both"]
    assert len(rows) == 1
    assert rows[0]["memory_count"] == 1
    assert rows[0]["document_count"] == 1
```

Run: `cd backend && .venv/bin/python -m pytest tests/test_projects_endpoint.py -q` — expected: FAIL (no `document_count` key; document-only project absent).

- [ ] **Step 2: Widen the route**

Replace the body of `backend/app/api/routes/projects.py` with a raw-SQL union (the asyncpg CAST rule does not bite here — no bound parameters):

```python
from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import get_session

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectSummary(BaseModel):
    """A project any corpus actually contains.

    Derived, never a registry — a project exists here because a memory, a
    document or a checkpoint carries it, and stops existing when the last of
    them is deleted. Widened 2026-08-31 (spec §2.1, review M2): grouping
    `memories.project` alone made a document-only project — exactly what the
    corpus import creates — invisible to its own scope picker.
    """

    name: str
    memory_count: int
    document_count: int
    checkpoint_count: int
    last_checkpoint_at: datetime | None
    # Day granularity on purpose: `ix_events_day` indexes the UTC-day
    # expression and nothing indexes (project, created_at); a timestamp here
    # would be a full scan of every monthly events partition.
    last_event_day: date | None


_UNION_SQL = text(
    """
    WITH names AS (
        SELECT project FROM memories
        UNION
        SELECT project FROM documents
        UNION
        SELECT project FROM session_checkpoints
    ),
    m AS (SELECT project, count(*) AS n FROM memories GROUP BY project),
    d AS (SELECT project, count(*) AS n FROM documents GROUP BY project),
    c AS (SELECT project, count(*) AS n, max(created_at) AS latest
          FROM session_checkpoints GROUP BY project),
    e AS (SELECT project,
                 max((created_at AT TIME ZONE 'UTC')::date) AS latest_day
          FROM events GROUP BY project)
    SELECT names.project AS name,
           COALESCE(m.n, 0) AS memory_count,
           COALESCE(d.n, 0) AS document_count,
           COALESCE(c.n, 0) AS checkpoint_count,
           c.latest AS last_checkpoint_at,
           e.latest_day AS last_event_day
    FROM names
    LEFT JOIN m ON m.project = names.project
    LEFT JOIN d ON d.project = names.project
    LEFT JOIN c ON c.project = names.project
    LEFT JOIN e ON e.project = names.project
    WHERE names.project IS NOT NULL AND names.project <> ''
    ORDER BY COALESCE(m.n, 0) + COALESCE(d.n, 0) + COALESCE(c.n, 0) DESC,
             names.project ASC
    """
)


@router.get("", response_model=list[ProjectSummary])
async def list_projects(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Every distinct project across memories, documents and checkpoints,
    busiest first.

    Counts every row rather than only the active ones: this drives a *scope*
    picker, and a project holding nothing but superseded rows is still a
    scope worth being able to switch into.
    """
    rows = (await session.execute(_UNION_SQL)).mappings().all()
    return [ProjectSummary(**dict(row)) for row in rows]
```

The `events` CTE reuses `ix_events_day`'s expression **verbatim** — see the header note; a reviewer who "simplifies" it to `created_at::date` de-indexes it and changes what a day means.

- [ ] **Step 3: Run the endpoint tests, then the suite**

```bash
cd backend && .venv/bin/python -m pytest tests/test_projects_endpoint.py tests/test_api/test_rest_conformance.py -q
```

All green (`("GET", "/api/v1/projects"): 200` in the conformance table is unchanged — same route, same status). Then the full `pytest -q`.

- [ ] **Step 4: SDK zero-diff check**

`cd sdks && make generate && git diff --exit-code sdks/` — the generator binds no projects verb, so this must be a no-op. A diff here means something else drifted; stop and investigate.

---

### Task 2: Frontend projects type and the switcher's widened copy

**Files:**
- Modify: `frontend/src/hooks/api/use-projects-api.ts`
- Modify: `frontend/src/components/app-chrome/project-switcher.tsx`

**Interfaces:**
- Consumes: Task 1's response shape.
- Produces: the widened `ProjectSummary` TS type Tasks 6 and 7 consume.

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2

- [ ] **Step 1: Widen the type**

In `use-projects-api.ts`:

```ts
export interface ProjectSummary {
  name: string
  memory_count: number
  document_count: number
  checkpoint_count: number
  last_checkpoint_at: string | null
  /** UTC day (YYYY-MM-DD), not a timestamp — see the backend's own comment. */
  last_event_day: string | null
}
```

- [ ] **Step 2: Fix the switcher's now-stale claims** (invariant 23 — "full list" prose must move with its referent)

In `project-switcher.tsx`:
- The doc comment "The list is exactly the corpus's own … a scope is offered only once a memory carries it" → "… a scope is offered once a memory, document or checkpoint carries it".
- The row hint `${row.memory_count} memories` → an item summary: `const total = row.memory_count + row.document_count + row.checkpoint_count`, hint `` `${total} ${total === 1 ? "item" : "items"}` `` (a document-only project showing "0 memories" would look broken).
- The empty state "No project holds a memory yet." → "No project holds anything yet."

- [ ] **Step 3: Typecheck + targeted tests**

`cd frontend && npm run typecheck && npm test -- project-switcher` (and whatever app-chrome test renders it — `src/components/app-chrome/__tests__/`).

---

### Task 3: Document data hooks — the stitched full list, outline, blocks, search

**Files:**
- Modify: `frontend/src/hooks/api/use-documents-api.ts`
- Extend: `frontend/src/hooks/api/__tests__/` (documents hooks test)

**Interfaces:**
- Consumes: shipped routes only — `GET /documents` (clamped at 200, `backend/app/api/routes/documents.py:279`), `GET /documents/{id}/outline`, `GET /documents/{id}`, `POST /documents/search`.
- Produces: `useAllDocuments(project)`, `useDocumentOutline(id)`, `useDocumentBlocks(id)`, `useDocumentSearch()` — consumed by Tasks 4-6, 8 and by increment 8.

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 1 = 2

- [ ] **Step 1: The stitching hook (review m1 — do not ship the silent version)**

The list route clamps `limit` to 200 against a ~465-file corpus and returns no `total`, so a single page silently drops over half the tree. Paginate-and-stitch, dedupe by id (the order is `created_at DESC` and a filing that lands mid-pagination shifts offsets), and report truncation honestly:

```ts
/** The list route clamps limit to 200 (backend documents.py:279) and carries
 *  no total, so one page cannot hold the corpus and cannot even say it was
 *  cut (review m1). Stitch pages until a short one; dedupe by id because a
 *  concurrent filing shifts created_at-DESC offsets between pages. */
const PAGE_LIMIT = 200
const MAX_PAGES = 25 // 5,000 documents; a guard, not a target

export interface AllDocumentsResult {
  items: DocumentListItem[]
  /** True only when MAX_PAGES was exhausted while pages were still full —
   *  render this as a visible banner, never drop it (invariant 14). */
  truncated: boolean
}

export function useAllDocuments(project: string) {
  return useQuery<AllDocumentsResult>({
    queryKey: ["documents-all", project],
    enabled: !DEMO,
    queryFn: async () => {
      const byId = new Map<string, DocumentListItem>()
      let truncated = false
      for (let page = 0; ; page++) {
        if (page >= MAX_PAGES) {
          truncated = true
          break
        }
        const res = await apiFetch<DocumentListResponse>(
          `/documents?project=${encodeURIComponent(project)}&limit=${PAGE_LIMIT}&offset=${page * PAGE_LIMIT}`,
        )
        for (const item of res.items) byId.set(item.id, item)
        if (res.items.length < PAGE_LIMIT) break
      }
      return { items: [...byId.values()], truncated }
    },
  })
}
```

- [ ] **Step 2: Outline, blocks and search hooks**

```ts
export interface OutlineNode {
  block_id: string
  level: number
  text: string
  order_index: number | null
}

export interface BlockRow {
  block_id: string
  type: string | null
  text: string
  order_index: number | null
  char_span: [number, number] | null
}

export function useDocumentOutline(documentId: string | null) {
  return useQuery<{ document_id: string; items: OutlineNode[] }>({
    queryKey: ["documentOutline", documentId],
    enabled: !DEMO && Boolean(documentId),
    queryFn: () => apiFetch(`/documents/${documentId}/outline`),
  })
}

export function useDocumentBlocks(documentId: string | null) {
  return useQuery<{ document_id: string; blocks: BlockRow[] }>({
    queryKey: ["documentBlocks", documentId],
    enabled: !DEMO && Boolean(documentId),
    queryFn: () => apiFetch(`/documents/${documentId}`),
  })
}

export interface SectionHit {
  block_id: string
  document_id: string
  uri: string | null
  title: string | null
  heading_path: string[]
  path_truncated: boolean
  text: string
  score: number
}

export function useDocumentSearch() {
  return useMutation<{ items: SectionHit[] }, Error, { query: string; project: string; limit?: number }>({
    mutationFn: (params) =>
      apiFetch(`/documents/search`, { method: "POST", body: JSON.stringify(params) }),
  })
}
```

- [ ] **Step 3: Hook tests**

Extend the hooks test directory with a stitching test: mock `apiFetch` to serve 200 + 200 + 37 items across three calls and assert one query returns 437 deduped items with `truncated: false`; a second test serves `MAX_PAGES` full pages and asserts `truncated: true`. `cd frontend && npm test -- use-documents` green.

---

### Task 4: The uri-segment tree — pure util plus the tree component

**Files:**
- Create: `frontend/src/features/documents/uri-tree.ts`
- Create: `frontend/src/features/documents/components/document-tree.tsx`
- Extend: `frontend/src/features/documents/__tests__/` (uri-tree unit test + tree render test)

**Interfaces:**
- Consumes: `DocumentListItem[]` (Task 3), darkraise-ui `tree-view`.
- Produces: `buildUriTree` and `DocumentTree` — the one hierarchy implementation both surfaces render, and the one increment 8's nesting reuses verbatim (spec §8.3: nesting derives from the uri path; the tree is this grouping).

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: The pure util, with its unit test first**

`uri-tree.ts`:

```ts
import type { DocumentListItem } from "@/hooks/api"

export interface UriTreeNode {
  /** Last path segment — what the row renders. */
  name: string
  /** Full path prefix, "/"-joined; unique within the tree. */
  path: string
  /** The document filed exactly at this path, when one is. A node can be
   *  both a document and a folder: `a/b.md` and `a/b.md/c.md` coexist —
   *  uris are opaque keys, not a filesystem. */
  document: DocumentListItem | null
  children: UriTreeNode[]
}

/** Group documents by uri "/" segments. Documents with a null uri collect
 *  under a trailing "(no path)" node so nothing silently drops. Children
 *  sort folders-first, then name. */
export function buildUriTree(items: DocumentListItem[]): UriTreeNode[]
```

Implementation: insert each item by splitting `item.uri` on `/`, creating intermediate nodes as needed and setting `document` on the leaf; a second pass sorts children (`children.length > 0` first, then `name.localeCompare`). Null-uri items become children of a synthetic `{ name: "(no path)", path: "(no path)" }` node appended last. Unit tests: nested grouping, the both-document-and-folder case, null-uri collection, sort order.

- [ ] **Step 2: The tree component**

`document-tree.tsx`, on the library's composable tree (read `tree-view.d.ts` — `TreeView` + `TreeViewTree` + `TreeViewBranch`/`TreeViewBranchControl`/`TreeViewBranchText`/`TreeViewBranchContent` + `TreeViewItem`, `selectionMode="single"`, `onSelectedChange`):

```tsx
export function DocumentTree({
  items,
  selectedId,
  onSelect,
  truncated,
  /** Optional per-node action slot — increment 8 mounts its "new subpage"
   *  affordance here; this surface passes nothing. Designed now so the
   *  editor extends this component instead of rewriting it. */
  nodeActions,
}: {
  items: DocumentListItem[]
  selectedId: string | null
  onSelect: (doc: DocumentListItem) => void
  truncated: boolean
  nodeActions?: (node: UriTreeNode) => React.ReactNode
})
```

- Build the tree with `buildUriTree(items)`; render a `TreeViewBranch` per folder node (value = `node.path`) and a `TreeViewItem` per leaf (value = the document id). A node that is both renders as a branch whose control row is also selectable.
- Map `onSelectedChange` values back to documents by id.
- When `truncated`, render a dashed warning line above the tree: *"showing the first {items.length} documents — the list was cut at the pagination guard"*. Never omit it.
- Empty state: darkraise-ui `empty-state` ("No documents filed in this project").

- [ ] **Step 3: Render test + checks**

Render `DocumentTree` with a three-level fixture; assert branch/leaf text, selection callback, and the truncation banner when `truncated`. `cd frontend && npm test -- document-tree && npm run typecheck`.

---

### Task 5: The block reader — per-block markdown render and the reader panel

**Files:**
- Create: `frontend/src/features/documents/components/block-view.tsx`
- Create: `frontend/src/features/documents/components/document-reader.tsx`
- Extend: `frontend/src/features/documents/__tests__/`

**Interfaces:**
- Consumes: `useDocumentOutline` / `useDocumentBlocks` (Task 3), `react-markdown` (already a dependency, `frontend/package.json:37`), darkraise-ui `table`, `breadcrumb`, `skeleton`.
- Produces: `BlockView` (one block, type-aware) and `DocumentReader` (outline + blocks) — `BlockView` is the exact component increment 8's editor wraps for its unfocused state; keep it a pure render of `{ type, text, properties? }` with no fetching.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: `BlockView`**

Blocks store **markdown source** (the parser keeps `inline.content`), so rendering `text` raw would show `**bold**` literally. One component, type-switched:

```tsx
import Markdown from "react-markdown"

export function BlockView({ block }: { block: BlockRow }) {
  switch (block.type) {
    case "heading":   // level is not on BlockRow; render as emphasized text,
                      // sized by a heading class — the outline carries levels
      return <div className="font-semibold"><Markdown>{block.text}</Markdown></div>
    case "code":
      return <pre className="overflow-x-auto rounded-md bg-muted/40 p-2 text-sm"><code>{block.text}</code></pre>
    case "quote":
      return <blockquote className="border-l-2 pl-3 text-muted-foreground"><Markdown>{block.text}</Markdown></blockquote>
    case "table":     // header cells ride text as "a | b" (increment 2's shape)
    case "table_row":
      return <div className="font-mono text-sm">{block.text}</div>
    case "list":
      return <div className="flex gap-2"><span aria-hidden>•</span><Markdown>{block.text}</Markdown></div>
    default:
      return <Markdown>{block.text}</Markdown>
  }
}
```

Notes for the implementer: `react-markdown` renders inline markdown; block-level nesting is not reconstructed here — the reader shows reading order, which is what `document_blocks` serves (flat, `order_index`-sorted, `backend/app/services/document_door.py:654-687`).

**Stated deviation from spec §2 / §4.1** (cross-plan review M-7, 2026-09-02): the spec says `table` blocks "render through the library `table` component". They do not here, and the reason is a gap no plan currently closes — increment 2 *writes* the `{header, alignments}` / `{cells}` properties a real table needs, but `properties` is on neither read surface (`BlockRow`, `document_door.py:601-606`; `BlockRowModel`, `routes/documents.py:246-251`), so the data never reaches this component. `table`/`table_row` therefore render as flat cell-joined text, which is what the door actually serves. This is a deviation, not a deferral of convenience: it is recorded here, in the CHANGELOG entry (Task 8) and in the spec's §2 as an open item. **Do not invent the properties client-side.** Closing it is one additive read change — `properties` on `BlockRow`/`BlockRowModel`, both doors, one service — and **increment 8 now owns it** (its Task 5a, assigned 2026-09-02), because its editor needs the same field to show a heading's level or a list's marker: one fix serving two consumers. If increment 8 has landed by the time this task runs, take the library `table` component as the spec specifies and strike this note; if it has not, render flat and leave the note standing.

- [ ] **Step 2: `DocumentReader`**

```tsx
export function DocumentReader({ documentId }: { documentId: string })
```

- Left rail: outline from `useDocumentOutline` — heading text indented by `level`, clicking scrolls to the block (anchor by `block_id` DOM id).
- Body: `useDocumentBlocks` mapped through `BlockView`, each wrapped in `<div id={block.block_id}>`.
- Loading: `skeleton`; error: the honest "could not be read — a failed read, not an empty corpus" copy the existing view uses; a document with zero blocks: an explicit empty line, not blankness.

- [ ] **Step 3: Tests + checks**

Render with mocked hooks: outline click scrolls (assert `scrollIntoView` spy), each block type renders its branch, markdown bold in a paragraph becomes `<strong>`. `cd frontend && npm test -- document-reader && npm run typecheck`.

---

### Task 6: The project workspace route — Artifacts and Progress tabs

**Files:**
- Create: `frontend/src/routes/_authenticated/projects_.$project.tsx`
- Modify: `frontend/src/features/activity/components/checkpoints-tab.tsx` (optional `project` prop)
- Extend: `frontend/src/features/activity/__tests__/checkpoints.test.tsx`, new route test under `frontend/src/routes/_authenticated/__tests__/`

**Interfaces:**
- Consumes: Tasks 3-5's hooks/components; increment 1's `useCheckpointRuns(project)` and the filter UI it added to `CheckpointsTab`.
- Produces: the workspace page; the `CheckpointsTab` prop the Progress tab pins.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 3: the spec (§2) fixes the page shape — two tabs mirroring `activity.tsx`'s pattern — and the reuse-vs-fork question for the checkpoint surface is settled by the shared-components mandate: extend `CheckpointsTab`, do not fork it.

- [ ] **Step 1: `CheckpointsTab` gains a pinned-project mode**

```tsx
export function CheckpointsTab({ project }: { project?: string } = {}) {
```

When `project` is provided: pass it straight to `useCheckpointRuns(project)` and **hide the filter select** (the workspace's scope is the route param; a second filter inside it would offer escapes from its own page). When absent, behaviour is exactly increment 1's. Extend the checkpoints test: rendering with `project="darkmem"` issues the events read with `project=darkmem` and renders no filter control.

- [ ] **Step 2: The workspace route**

`projects_.$project.tsx` (the `knowledge_.facts_.$factId.tsx` convention gives the flat `/projects/$project` path):

- `validateSearch` for `tab: "artifacts" | "progress"` (default `artifacts`), mirroring `activity.tsx:44-52`.
- Header: `PageChrome` with the project name; beside it a darkraise-ui `combobox` (read `combobox.d.ts` for the item API) listing `useProjects()` names, navigating to the sibling workspace on select.
- **Artifacts tab**: two-pane layout — left: `DocumentTree` over `useAllDocuments(project)` (pass `truncated` through); right: `DocumentReader` for the selection, `empty-state` when nothing is selected. Above the panes: a search input driving `useDocumentSearch` scoped to the project; hits render text + a `breadcrumb` from `heading_path` (`path_truncated` appends an ellipsis segment — the walk was cut, the path is real as far as it goes); clicking a hit selects its document.
- **Progress tab**:
  - Top: the pinned ledger — `useAllDocuments(project).items.find(d => d.uri?.endsWith("planning/progress.md"))`, rendered through `DocumentReader`. **Suffix match, not equality**: the spec's convention says uri `planning/progress.md` but increment 5's import files repo-relative paths, so the darkmem corpus ledger lands at `docs/planning/progress.md` — the suffix resolves both spellings (discrepancy flagged in Notes). No match: `empty-state` naming the convention ("file a document whose path ends in planning/progress.md to pin the project ledger").
  - Below: `<CheckpointsTab project={project} />`. Its copy already states the m2 limit (increment 1, Task 1 Step 5); do not restate or contradict it — the timeline is content-free and only the latest note's text is readable, and that stays true here.

- [ ] **Step 3: Tests, typecheck, build**

Route test: renders both tabs, tab switch updates search param, Artifacts shows the tree, Progress shows the pinned-ledger empty state when no uri matches. `cd frontend && npm test && npm run typecheck && npm run build` (the build regenerates `routeTree.gen.ts` — commit the regenerated file, never hand-edit it).

---

### Task 7: The projects index route and navigation

**Files:**
- Create: `frontend/src/routes/_authenticated/projects.tsx`
- Modify: `frontend/src/routes/_authenticated.tsx` (nav groups, `frontend/src/routes/_authenticated.tsx:50-93`)
- Extend: route tests

**Interfaces:**
- Consumes: `useProjects()` (Task 2's widened shape).
- Produces: the `/projects` entry point.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 0 = 3
**Approach:** inline - skip 3: the spec (§2) fixes the surface — cards per project from the widened endpoint; only layout is left to the implementer.

- [ ] **Step 1: The index route**

`projects.tsx`: `PageChrome` ("Projects", "Every project the corpus holds — memories, documents and checkpoint runs."), then a responsive card grid (darkraise-ui `card` + `stat`), one card per `ProjectSummary`:

- Title: `name`; stats: memories / documents / checkpoints counts (`stat`);
- `last_checkpoint_at` as relative time (`relativeTime` from `@/lib/format`); `last_event_day` as "active <day>" (relative at day granularity — "today", "3d ago"; it is a UTC day string, never fed to `relativeTime` as a timestamp);
- The whole card links to `/projects/$project`.
- Loading: `skeleton` cards; empty: `empty-state` ("No project holds anything yet").

- [ ] **Step 2: Navigation**

In the `nav` array (`_authenticated.tsx:50`), add to a fitting group — a new group between Memories and Knowledge:

```ts
{
  label: "Projects",
  items: [
    { label: "Projects", href: "/projects", icon: FolderKanban },
    { label: "Documents", href: "/documents", icon: FileText },
  ],
},
```

(`FolderKanban` from lucide; `FileText` is already imported.) Note `/documents` has existed since TH1.16 with **no nav entry at all** — the spec's own "the gap is UI only" reachability point; this closes it for both surfaces.

- [ ] **Step 3: Tests, typecheck, build**

Index route test (cards render from a mocked `useProjects`, link targets); `npm test && npm run typecheck && npm run build`.

---

### Task 8: The personal surface re-renders through the shared components

**Files:**
- Modify: `frontend/src/features/documents/components/documents-view.tsx`
- Modify: `frontend/src/routes/_authenticated/documents.tsx`
- Extend: `frontend/src/features/documents/__tests__/documents.real.test.tsx`

**Interfaces:**
- Consumes: Tasks 3-5's hooks and components.
- Produces: the personal surface increment 8's editor mounts on.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 3: the spec (§2) fixes what stays (QA/summary/connections panels, the horizon labelling) and what changes (the flat list becomes the shared tree + reader; the project pins `default`).

- [ ] **Step 1: Refactor `DocumentsView`**

- The route passes `project="default"` explicitly (`documents.tsx`), making the pin visible at the call site instead of a default parameter nobody reads (`documents-view.tsx:30`).
- Replace the flat document `Card` list with `DocumentTree` over `useAllDocuments(project)`; selection feeds the existing `DocumentDetail` (summary/connections) **and** the new `DocumentReader` — reader above, horizon panels below.
- Keep, byte-for-byte in intent: the horizon badge + copy, the withheld-answer rendering, the unbadged-summary copy, the grounded-QA card. These are honesty surfaces; the refactor moves the list, not the labels.
- Every existing test in `documents.real.test.tsx` must still pass; extend with: the tree renders, selecting a leaf mounts the reader.

- [ ] **Step 2: Full frontend check**

`cd frontend && npm test && npm run typecheck && npm run build`.

---

### Task 9: Gate, changelog, deploy

**Files:**
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: Tasks 1-8 landed.
- Produces: the running instance the owner reviews.

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 0 - spec 0 - coupling 0 - risk 2 = 2

- [ ] **Step 1:** `./scripts/gate.sh` from the repo root — green before commit.
- [ ] **Step 2:** CHANGELOG section for the next derived version. **Coordinate with the other in-flight increment plans** — if several land in one push, one `## vN.N.N` section covers them; the release workflow fails a push whose derived version has no section.
- [ ] **Step 3:** Commits (atomic): `feat(projects): corpus-union project index endpoint` (Task 1), `feat(frontend): project workspace and shared document surfaces` (Tasks 2-8, or split by surface if the diff is reviewable that way).
- [ ] **Step 4:** Redeploy (owner ruling 2026-08-21 — backend and frontend both changed):

```bash
DARKMEM_PUSH=0 ./scripts/build-push.sh   # DARKMEM_PUSH=0 is not optional
docker compose up -d
# wait for healthy, then confirm the running image carries the change:
curl -s http://127.0.0.1:8000/openapi.json | grep -c document_count   # non-zero
docker exec darkmem-prod-darkmem-1 grep -rl "documents-all" /app/static/assets/ | head -1
```

- [ ] **Step 5:** Watch it work: open `/projects`, confirm a document-only project appears once increment 5's import has run (or seed one document by hand), open its workspace, browse the tree, and watch the Progress tab poll.

## Rollback

Task 1 is a widened response on an existing GET — additive fields, same route; `git revert` restores the memories-only derivation and the old frontend continues to work (it reads only `name`/`memory_count`). Tasks 2-8 are additive UI plus one refactor; revert and redeploy. No schema, no data, no new backend surface beyond the widened model.

## Notes on scope

- **The ledger-uri discrepancy, flagged:** spec §2 pins the ledger at uri `planning/progress.md`; increment 5's import (`2026-08-31-docs-corpus-import.md`, Task 1) files repo-relative paths, so the actual darkmem ledger lands at `docs/planning/progress.md`. This plan resolves by suffix (`endsWith("planning/progress.md")`), which serves both spellings; the conventions doc (increment 5) should state one canonical spelling when it is next touched.
- **The checkpoint m2 limit is carried, not re-litigated:** the Progress tab shows the latest note plus a content-free save/resume timeline — exactly what `2026-08-31-watchable-progress.md` states. No history read verb exists; wanting one is a spec amendment.
- **What the Artifacts tab does not do:** no editing (increment 8), no document filing from the UI, no wiki-style rendering of whole documents from raw source (blocks are the read unit until increment 3's `include_content` is consumed by a later surface).
- **Increment 8 dependency, designed for now:** `DocumentTree`'s `nodeActions` slot, `BlockView`'s pure `{type, text}` contract, and `buildUriTree` as a standalone util are the extension points the personal-workspace plan (`2026-08-31-personal-workspace.md`) builds on. Changing their shapes there, not here.
- Increments 3, 6, 7 belong to other plans; nothing here touches `documents.content`, backups, or the worker.

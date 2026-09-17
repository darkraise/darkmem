# Pages, Increment B2 — the `/notes` workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repoint `/notes` at the page tree B1 shipped — a sidebar tree with drag-to-reorder, per-row create/rename/delete, a trash sheet, and a page pane with a title field and a block editor over the page block verbs — and return `ProjectWorkspace` to being the corpus browser `/projects/$project` needs.

**Architecture:** A new `features/notes/` owns the whole surface and shares nothing with `features/documents/` but `BlockView` and the `createMutationQueue` primitive. Two pure modules carry the logic worth testing on its own — `build-page-tree.ts` (flat rows to a nested tree) and `drop-target.ts` (pointer position over a row to a `PATCH {parent_id, after_id}`) — so the React components stay thin. All thirteen page routes land in one `hooks/api/use-pages-api.ts`, whose block verbs run through a per-page mutation queue exactly as the document block verbs do, and whose page read normalises the wire's `PageBlock` rows into the editor's existing `BlockRow` shape so the copied editor and `BlockView` need no second row type. `ProjectWorkspace` loses `treeManagement`, `freeUri` and every branch they gated, which is a deletion rather than a refactor.

**Tech Stack:** React 19, TypeScript, TanStack Router (file-based) + TanStack Query v5, darkraise-ui v6 (TreeView, Sheet, Dialog, AlertDialog, sonner), `@dnd-kit/core` v6, vitest + @testing-library/react, vite.

**Spec:** `docs/superpowers/specs/2026-09-17-pages-increment-b-workspace-editor-design.md` (B2 is §1, §2, §4, §6, §7 "B2", §8)

**Execution:** inline — `claude --model sonnet --effort high` — no task is heavy; the 3 four-band tasks (8, 10, 11) are a third of the plan (3 x 3 <= 12), so they are delegated, and the highest self-implemented total is 3

**Program:** `docs/superpowers/specs/2026-09-17-pages-increment-b-workspace-editor-design.md` — sub-project 2 of 3 — next: B3 — the BlockNote editor

**Plan review:** 2026-09-18 — dr-superpowers:judge-opus — executability 17 / coherence 17 / coverage 18 / assumptions 16 (round 2)

## Global Constraints

- **`/documents` and `/projects/$project` must not change in behaviour.** Owner requirement, spec §2. `DocumentsView`, `DocumentTree`, `EditableDocument`, `BlockEditor`, `use-documents-api.ts` and `use-blocks-api.ts` keep their current behaviour. `ProjectWorkspace` loses only the `treeManagement`-gated branches and the members that exist solely to serve them; everything the corpus browser renders today renders identically after.
- **`page-block-editor.tsx` is a deliberate copy, not a parameterisation** (spec §4.1). `features/documents/components/block-editor.tsx` is not edited, not generalised and not imported. The copy is recorded as a duplicate that B3 deletes.
- **No conversion of existing notes** (spec §2). Today's notes are documents in the personal project; after this increment they are visible nowhere in the SPA and that is the ruling. Do not add a compatibility view, a migration, a redirect or a second tab.
- **No project picker on `/notes`** (spec §2). It stays the personal project only, resolved from the catalogue by `kind === "personal"`, never by a hardcoded name.
- **Out of scope, do not build:** wiki-links, tags, page search, MCP tools for pages, version history, the BlockNote editor and everything in spec §5 (`page-sync-queue.ts`, `editor-changes.ts`, `inline-markdown.ts`, `block-properties.ts`, the slash menu, the outline rail, a demo sample page). B2 ships the copied per-block textarea editor and nothing more.
- **`enabled: !DEMO` on every query** (spec §4.1). Demo mode makes no API call: an unguarded read 401s and `handleUnauthorized` navigates the whole demo to `/login`. B2 ships no page fixtures, matching `use-documents-api.ts`.
- **Every leading query-key string must be registered in `QUERY_KEY_SCOPE`** (`frontend/src/lib/query-keys.ts`) before it exists, and every `queryKey:` **declaration** must live in `src/hooks/api/` — `query-keys.test.ts` scans only that directory, so a key declared in a feature directory is unregistered silently. An `invalidateQueries` or `getQueryData` call in a feature file naming an already-registered key is fine and is what the repo already does (`features/settings/use-maintenance-tab-binding.ts:81-82`, invalidating `pipelineFailureCounts`, registered at `lib/query-keys.ts:195`; also `features/chat/hooks/use-chat-stream.ts:67`); the rule is about where a key is *introduced*.
- **`apiFetch` prepends `/api/v1` itself.** No call site spells the base; `lib/__tests__/api-paths.test.ts` fails the build on one.
- **UI components come from darkraise-ui first** (CLAUDE.md). Enumerate with `ls frontend/node_modules/darkraise-ui/dist/components/` and read the `.d.ts` before writing a local component. A local component written against a library gap records which gap.
- **Comments:** default to none; only where the WHY is non-obvious. Never reference the task, the increment or a review finding.
- **English only** in code, comments, docs, commits and tests.
- **Commits:** `<type>(<scope>): <subject>`, type = feat|fix|docs|style|refactor|test|chore|perf, subject <= 50 chars, imperative, no period. Every commit message ends with:
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  ```
- **Frontend commands run from `frontend/`:** `npm run typecheck` (= `tsc -b`; plain `tsc` misses the project refs), `npm test` (= `vitest run`), `npm run build`. A single file: `npx vitest run src/path/to/file.test.ts`. `npm run lint` is advisory.
- **Never run Playwright bare.** `npx playwright test` points `/api` at the live instance on `:8000`. The e2e leg is `backend/scripts/e2e/run_playwright_e2e.py` and it is **not** a task here.
- **Host hazard:** an `earlyoom` daemon kills memory-heavy runs at ~80% swap. **Exit 143 is a SIGTERM, not a failure** — check `free -h` and re-run the leg alone before believing a red.
- **No schema change and no backend change.** B1 shipped every route B2 calls. If a task finds it needs a backend edit, stop and report rather than widening the increment.
- **Deploy is not a task here.** After merge, CLAUDE.md's redeploy sequence applies (spec §8): `./scripts/gate.sh` legs, `DARKMEM_PUSH=0 ./scripts/build-push.sh`, `docker compose up -d`, then confirm the change is in the running image.

## Contracts

**`frontend/src/lib/api.ts` (Task 1)**
- `export async function apiFetchWithHeaders<T>(path: string, options?: ApiFetchOptions): Promise<{ data: T; headers: Headers }>` — the existing `apiFetch` body, returning the parsed body beside the `Response`'s headers. `apiFetch<T>` becomes `(await apiFetchWithHeaders<T>(path, options)).data`, so the 401 burst guard, the `ApiError` shape and the 204 rule have exactly one implementation.

**`frontend/src/lib/query-keys.ts` (Task 2)** — three new `QUERY_KEY_SCOPE` entries: `pages` (`manual`), `page` (`global`), `pagesTrash` (`manual`).

**`frontend/src/hooks/api/use-pages-api.ts` (Tasks 2 and 3)** — re-exported from `hooks/api/index.ts`.
- Wire types: `PageListItem { id, project, parent_id, order_index, title, content_hash, properties, created_at, updated_at }`; `PageTrashItem { id, title, parent_id, deleted_at }`; `PageBlockWriteResponse { page_id, block_id, outcome, content_hash, blocks_total, blocks_embedded }`; `PageBlockBatchWriteResponse`, the same but with `block_ids: string[]` and **no** `block_id` — the batch route answers its own model (`backend/app/api/routes/pages.py:314-357`). Note the owner field is `page_id`, not `document_id` — `BlockWriteResponse` from `use-blocks-api.ts` is not reused.
- `PageView { id, project, parent_id, order_index, title, content_hash: string | null, blocks: BlockRow[] }` — the normalised page read. `BlockRow` is `use-documents-api.ts`'s existing type; the wire's `PageBlock.id` becomes `block_id` and `char_start`/`char_end` become `char_span`, so `BlockView` and the copied editor need no second row type.
- `pageQuery(pageId: string)` — the shared `{ queryKey: ["page", pageId], queryFn }` factory, so the mutation queue's hash re-read resolves the same cache entry the pane renders from.
- Queries: `usePages(project: string)` (key `["pages", project]`), `usePage(pageId: string | null)`, `usePagesTrash(project: string, open: boolean)` (key `["pagesTrash", project]`, `enabled: !DEMO && open`).
- Page mutations: `usePageCreate()` (`{ project, title?, parentId?, afterId?, content? } -> { id: string }`), `usePageRename()` (`{ pageId, title }`), `usePageMove()` (`{ pageId, parentId, afterId }`), `usePageDelete()` (`pageId -> void`), `usePageRestore()` (`pageId -> { restored: number }`), `usePageTrashEmpty()` (`project -> { purged: number }`). `usePageRename` and `usePageMove` are two hooks over the one `PATCH` route because it dispatches on field **presence**: a rename must not send `parent_id` and a move must not send `title`.
- Block verbs, each over the per-page mutation queue: `usePageBlockUpdate(pageId)`, `usePageBlockInsert(pageId)`, `usePageBlockMove(pageId)`, `usePageBlockDelete(pageId)`, `usePageBlocksInsertBatch(pageId)`. Value shapes mirror `use-blocks-api.ts`'s, plus `blockId?: string` on insert (the client-chosen id B1 accepts) and `{ blocks: NewPageBlock[] }` on the batch, where `NewPageBlock { block_id, type, text, properties?, parent_id?, after_block_id? }`.
- `usePageBlockDelete` reads the new hash from the `X-Content-Hash` response header (B1 §3.7) and feeds it to the queue, so a page delete does not force the re-read a document delete does.

**`frontend/src/features/notes/lib/build-page-tree.ts` (Task 4)**
- `export interface PageNode { id: string; title: string | null; parent_id: string | null; order_index: number; children: PageNode[] }`
- `export const PAGE_TITLE_FALLBACK = "Untitled"` — what the tree, the pane and the trash sheet render for a null title.
- `export function buildPageTree(rows: PageListItem[]): PageNode[]` — tolerant of any row order; siblings sorted by `(order_index, id)`; a row whose `parent_id` names no row in the list is a root.
- `export function pageNodeIndex(roots: PageNode[]): Map<string, PageNode>`

**`frontend/src/features/notes/lib/drop-target.ts` (Task 5)**
- `export type DropZone = "before" | "after" | "inside"`
- `export interface DropPlacement { parentId: string | null; afterId: string | null }`
- `export function dropZoneFor(offsetY: number, height: number): DropZone` — top third `before`, bottom third `after`, middle `inside`; a non-positive height is `inside`.
- `export function isDescendant(node: PageNode, candidateId: string): boolean`
- `export function resolvePageDrop(roots: PageNode[], index: Map<string, PageNode>, draggedId: string, overId: string | null, zone: DropZone): DropPlacement | null` — `null` refuses. Refuses a null `overId`, a drop onto the dragged page itself or any descendant of it, and a placement equal to the dragged page's current one.
- `export function applyPlacement(rows: PageListItem[], pageId: string, placement: DropPlacement): PageListItem[]` — the same placement applied to the flat list, for the optimistic update. Pure, returns a new array, reindexes only the rows whose sibling run changed.
- `DropPlacement` maps to the route body `{ parent_id: parentId, after_id: afterId }`. A null `afterId` places **first** among `parentId`'s children (`PagePatchRequest.after_id`'s documented semantics, the opposite of `POST /pages`, where absent appends).

**`frontend/src/features/notes/page-block-editor.tsx` (Task 6)**
- `export function promote(source: string, stored?: string | null): { type: string; text: string; properties?: Record<string, unknown> }` — a verbatim copy of the document editor's helper.
- `export type PageSaveStatus = { kind: "idle" } | { kind: "saving" } | { kind: "saved" } | { kind: "blocked"; message: string }`
- `export function PageBlockEditor({ pageId, blocks, onStatus }: { pageId: string; blocks: BlockRow[]; onStatus: (status: PageSaveStatus) => void })`

**`frontend/src/features/notes/page-pane.tsx` (Task 6)**
- `export function PagePane({ page, autoFocusTitle }: { page: PageView; autoFocusTitle: boolean })`

**`frontend/src/features/notes/page-tree.tsx` (Tasks 7 and 8)**
- `export function notesExpansionStorageKey(project: string): string` — `darkmem:notes:expanded:<project>`
- Task 8 adds five more exports to the same module: `DRAG_PREFIX = "drag:"`, `DROP_PREFIX = "drop:"`, `pointerZone(rect: { top: number; height: number } | null, pointerY: number): DropZone`, `shouldHoverExpand(index: Map<string, PageNode>, expanded: string[], pageId: string): boolean`, and `resolveDrop(roots, index, activeId, overId, zone): DropPlacement | null` — the prefix-stripping wrapper over `resolvePageDrop`.
- `export function PageTree({ roots, index, project, selectedId, onSelect, onNewChild, onRename, onDelete, onMove }: { roots: PageNode[]; index: Map<string, PageNode>; project: string; selectedId: string | null; onSelect: (pageId: string) => void; onNewChild: (parentId: string) => void; onRename: (node: PageNode) => void; onDelete: (node: PageNode) => void; onMove: (pageId: string, placement: DropPlacement) => void })`

**`frontend/src/features/notes/page-trash-sheet.tsx` (Task 9)**
- `export function PageTrashSheet({ project, open, onOpenChange, onRestored }: { project: string; open: boolean; onOpenChange: (open: boolean) => void; onRestored: () => void })`

**`frontend/src/features/notes/notes-workspace.tsx` (Task 10)**
- `export function NotesWorkspace({ project, selectedId, onSelect }: { project: string; selectedId: string | null; onSelect: (pageId: string | null) => void })`

**`frontend/src/routes/_authenticated/notes.tsx` (Task 10)**
- `validateSearch` yields `{ page?: string }`; the selected page id lives in the URL as `/notes?page=<id>`.

## Assumptions (evidence)

- **Baseline is green in this worktree.** `npm run typecheck` clean, `npm test` 196 files / 1616 tests passed, `npm run build` succeeded — all run 2026-09-18 in `.worktrees/pages-increment-b2-workspace/frontend`.
- **B1 is merged and every route B2 calls exists.** `backend/app/api/routes/pages.py:1-20` lists all thirteen; handler signatures and response models read 2026-09-18 at `:104-429`. `X-Content-Hash` is set only on the page block delete (`:405-429`), and it is the only route in the repo that sets it.
- **`@dnd-kit/core` is already a dependency** at `^6.3.1` (`frontend/package.json`), with `@dnd-kit/accessibility`, `core` and `utilities` installed. `features/documents/components/document-tree.tsx` is the only file in `src/` that imports it. **No new dependency is added by this plan.**
- **`apiFetchWithHeaders` does not exist**, and nothing in `src/` reads a response header: grep for `apiFetchWithHeaders`, `X-Content-Hash` and `response.headers` over `frontend/src` returned zero hits, 2026-09-18. `API_BASE` and `handleUnauthorized` are module-private in `lib/api.ts`, so the variant has to live in that file.
- **Spec §4.1's conditional on `move-target.ts` and `uri-tree.ts` resolves to: neither is deleted.** `features/documents/components/document-tree.tsx:30-31` imports both, and `DocumentTree` has a second consumer in `documents-view.tsx:8` (`/documents`) besides `/projects/$project`. Only `project-workspace.tsx`'s own imports of them go.
- **Spec §4.1's conditional on sharing `document-tree.tsx`'s row resolves to: `page-tree.tsx` gets its own row.** Every part of that component is keyed on `UriTreeNode` and uri paths — `buildPathMap`/`buildUriTree`, `fileIcon(node.name)`, `dropTargetFor`'s path-slicing parent walk, `resolveDrop`'s `DRAG_PREFIX`/`DROP_PREFIX` path ids and `moveTarget`'s uri rewrite — and lifting a row out would change the component `/documents` and `/projects/$project` both render. The page tree reuses the *pattern* (darkraise-ui `TreeView` parts, a drag layer hung off an inner span, `MouseSensor` + `TouchSensor`) and none of the code.
- **`tree-expansion.ts` stays.** Its `expansionStorageKey`/`pathsToDocument`/`rootFolderPaths` are read by `project-workspace.tsx:239`, `:253`, `:266` and `:294`, none of which is behind `treeManagement`, so the corpus browser keeps them.
- **The queue's hash re-read resolves a WHOLE page, not a hash.** `pageQuery(pageId).queryFn` is `toPageView(await apiFetch<PageWire>(...))` and `toPageView` ends in `wire.blocks.map(...)`, so a test stub answering a bare `{content_hash}` throws inside the normaliser and every write rejects before it is sent. Tasks 3 and 6 route their GET arm separately for this reason; the repo's own equivalent does the same at `frontend/src/hooks/api/__tests__/use-blocks-api.test.tsx:50-54`.
- **`TreeViewBranchContent` renders `null` while its branch is closed** (`frontend/node_modules/darkraise-ui/dist/chunk-4GT6M5U4.js:529`), so a test expecting a child row has to seed the expanded set first. Task 7's suite does.
- **No darkraise-ui TreeView part exposes a labelled expand button.** `TreeViewBranchControl` renders a `div` with `role="treeitem"` (`chunk-4GT6M5U4.js:473-497`) and `TreeViewBranchIndicator` a span whose icon is `aria-hidden` (`:499-515`, the attribute at `:508`). The control's own `onClick` calls `toggleExpanded` then `toggleSelected` (`:465-466`) and the label is its descendant, so clicking the branch's label is what toggles it under test; `setExpanded` then fires `onExpandedChange({ value })` against the controlled prop (`:38`).
- **TanStack Query keeps a query's existing `data` when a refetch rejects**, at the installed `@tanstack/react-query@^5.96.2`. Task 10's move test turns on this: it fails the list read after its first success so the hook's own invalidation cannot refetch the server's copy over the rollback and pass for the wrong reason. If the behaviour ever changed, that test would go red rather than falsely green.
- **`note-tree-actions.tsx` is deleted with the `treeManagement` branches.** Its only production importer is `project-workspace.tsx:67`, it is mounted only under `treeManagement`, and it is typed on `UriTreeNode` and offers folder and pin verbs a page has no analogue for. Its test `features/documents/__tests__/note-tree-actions.test.tsx` goes with it.
- **The nine `treeManagement` branches are enumerated** — `grep -n treeManagement` over `project-workspace.tsx` on 2026-09-18 gives exactly `:188`, `:197` (the prop), `:228`, `:548`, `:564`, `:603`, `:686`, `:735`, `:736`, `:825`, `:980`. `freeUri` is a module-local function at `:98` whose only caller is `handleNewNote` at `:345`; `NO_DOCUMENTS` is at `:93`; `commitNewFolder` at `:436` and `commitDelete` at `:509`. The corpus browser's own expansion readers — not behind `treeManagement` — are at `:239`, `:253`, `:266` and `:294`.
- **`project-workspace-render.test.tsx` counts `DocumentTree`'s renders and fails on any fresh object at its call site** (noted at `project-workspace.tsx:352-361`). Task 11 removes props from that call site; if the count assertion moves, the test is updated to the new number rather than loosened.
- **`page_count` is already on the wire and on the frontend type** (`backend/app/api/routes/projects.py:35`, `frontend/src/hooks/api/use-projects-api.ts:13`) and is simply absent from `itemHint`'s total at `components/app-chrome/project-switcher.tsx:38`.
- **Two distinct 409s reach the block verbs** — a hash conflict and a client-chosen-id collision — and `ApiError.status` cannot tell them apart; only `ApiError.message` (the server's `detail`) can. B2 shows the server's message in the banner and does not branch on which it is (spec §3.4 says the client does not need to).
- **Toasts come from `darkraise-ui/components/sonner`** and its `ToastOptions.action: { label, onClick }` supports the undo affordance (`node_modules/darkraise-ui/dist/components/sonner.d.ts:29-45`, read 2026-09-18).
- **`project-switcher.test.tsx`'s `renderSwitcher()` takes no arguments** (`:19-25`); rows come from `mockUseProjects.mockReturnValue({ data, isLoading: false })` and live inside a `PopoverContent`, so a row assertion clicks `getByRole("button", { name: /project scope/i })` first — the whole shape is at `:100-128`. Its existing item-count cases already carry `page_count: 0`, so Task 12's change leaves them green.
- **A mock factory reads its spies through `vi.hoisted`.** `vi.mock` is hoisted above every import, so a module-scope `const` the factory closes over is still in its temporal dead zone when the factory runs. The repo's form is at `components/darkmem/__tests__/detail-level-placement.test.tsx:13`.
- **The documents feature raises no toasts** — `block-editor.tsx` renders an inline `text-destructive` paragraph instead. B2's toasts on tree and trash refusals are spec §6's requirement, not the copied editor's behaviour, and the copied editor keeps the inline failure line.
- **`api-paths.test.ts`'s regex does not match `apiFetchWithHeaders(`** — `apiFetch(?:<[^>]*>)?\(` requires `(` or `<` immediately after `apiFetch`. Task 1 widens it to `apiFetch(?:WithHeaders)?` so the new function's call sites are covered rather than silently exempt.
- **The external-executor lane is closed for this plan.** `scripts/codex-gate` printed `usable=false reason=plugin-version:1.0.6 review=false lane=false source=probe` on 2026-09-18, so no task carries an `**Executor:**` line and plan review round 1 runs on a Claude judge.
- **Spec §8 is carried by Global Constraints rather than by a task, deliberately.** §8's content for B2 is "this increment changes no schema, so it is an ordinary redeploy". No frontend task can verify that claim — there is nothing to verify, since no task touches `backend/`, `0001_baseline.py`, the `Dockerfile`, compose or `entrypoint.sh` — and CLAUDE.md's redeploy rule already fires on merge. A task whose only step was "run the deploy sequence" would be ceremony, and the constraint states the sequence where an executor will read it.
- **Spec §5.4's `Unsaved — retrying` state is not reachable in B2.** That state belongs to B3's retry queue; B2's copied editor has no retry, so its save states are `Saving…`, `Saved` and the blocked banner. Recorded rather than faked with a state nothing can enter.

## Task index

1. `apiFetchWithHeaders` and the widened api-paths guard
2. Page query keys and the page read hooks
3. Page and page-block mutation hooks
4. `build-page-tree.ts`
5. `drop-target.ts`
6. The page pane and the copied block editor
7. `PageTree` rows, selection, expansion and row actions
8. `PageTree` drag to reorder
9. The trash sheet
10. `NotesWorkspace` and the `/notes` route
11. Return `ProjectWorkspace` to the corpus browser
12. Carried items, docs and the frontend leg

---

### Task 1: `apiFetchWithHeaders` and the widened api-paths guard

**Files:**
- Modify: `frontend/src/lib/api.ts:62-94`
- Modify: `frontend/src/lib/__tests__/api-paths.test.ts:28-33,49-61`
- Test: `frontend/src/lib/__tests__/api-fetch-headers.test.ts` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `apiFetchWithHeaders` — see Contracts, `frontend/src/lib/api.ts`. Task 3's page block delete is its only caller.

**Implementer:** dr-superpowers:impl-sonnet-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 0 = 1
**Approach:** inline - skip 2: one obvious refactor, the body moves unchanged into the new function

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/__tests__/api-fetch-headers.test.ts`:

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/features/auth", () => ({
  useAuthStore: { getState: () => ({ logout: vi.fn(), setAuthenticated: vi.fn() }) },
}))

import { ApiError, apiFetch, apiFetchWithHeaders } from "../api"

function respond(init: {
  status: number
  body?: unknown
  headers?: Record<string, string>
}) {
  return {
    ok: init.status >= 200 && init.status < 300,
    status: init.status,
    statusText: "",
    headers: new Headers(init.headers ?? {}),
    json: async () => init.body,
  } as unknown as Response
}

describe("apiFetchWithHeaders", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn())
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("returns the parsed body beside the response headers", async () => {
    vi.mocked(fetch).mockResolvedValue(
      respond({ status: 200, body: { id: "p1" }, headers: { "X-Content-Hash": "h9" } }),
    )
    const { data, headers } = await apiFetchWithHeaders<{ id: string }>("/pages/p1")
    expect(data).toEqual({ id: "p1" })
    expect(headers.get("X-Content-Hash")).toBe("h9")
    expect(vi.mocked(fetch).mock.calls[0]![0]).toBe("/api/v1/pages/p1")
  })

  it("serves headers on a 204, where the body is undefined", async () => {
    vi.mocked(fetch).mockResolvedValue(
      respond({ status: 204, headers: { "X-Content-Hash": "h10" } }),
    )
    const { data, headers } = await apiFetchWithHeaders<void>("/pages/p1/blocks/b1", {
      method: "DELETE",
    })
    expect(data).toBeUndefined()
    expect(headers.get("X-Content-Hash")).toBe("h10")
  })

  it("throws the same ApiError apiFetch does, carrying the server's detail", async () => {
    vi.mocked(fetch).mockResolvedValue(
      respond({ status: 409, body: { detail: "expected_hash a does not match b" } }),
    )
    await expect(apiFetchWithHeaders("/pages/p1/blocks/b1")).rejects.toBeInstanceOf(
      ApiError,
    )
    await expect(apiFetchWithHeaders("/pages/p1/blocks/b1")).rejects.toMatchObject({
      status: 409,
      message: "expected_hash a does not match b",
    })
  })

  it("apiFetch still answers the bare body", async () => {
    vi.mocked(fetch).mockResolvedValue(respond({ status: 200, body: { ok: true } }))
    await expect(apiFetch<{ ok: boolean }>("/pages")).resolves.toEqual({ ok: true })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run, from `frontend/`: `npx vitest run src/lib/__tests__/api-fetch-headers.test.ts`
Expected: FAIL — `api.ts` has no export named `apiFetchWithHeaders`.

- [ ] **Step 3: Write the implementation**

In `frontend/src/lib/api.ts`, replace the whole `apiFetch` function (lines 62-94, from `export async function apiFetch<T>(` through its closing brace) with:

```ts
/** The one request implementation. `apiFetch` is the body-only view of it;
 *  a caller that needs a response header — today only the page block delete,
 *  whose 204 carries the page's new `content_hash` — takes this one. */
export async function apiFetchWithHeaders<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<{ data: T; headers: Headers }> {
  const { on401 = "redirect", ...init } = options
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  })
  if (response.status === 401 && on401 === "redirect") {
    handleUnauthorized()
    throw new ApiError("Unauthorized", 401)
  }
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }))
    const body = error as { detail?: string; error?: { details?: unknown[] } }
    throw new ApiError(
      body.detail || `API error: ${response.status}`,
      response.status,
      body.error?.details,
    )
  }
  if (response.status === 204) {
    return { data: undefined as T, headers: response.headers }
  }
  return { data: (await response.json()) as T, headers: response.headers }
}

export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  return (await apiFetchWithHeaders<T>(path, options)).data
}
```

Then widen the guard in `frontend/src/lib/__tests__/api-paths.test.ts`. Replace the two regex constants (lines 28-33) with:

```ts
// `apiFetch("/x")`, `apiFetch<T>(`/x`)`, the same with the path on the
// following line, and the header-reading variant beside it — the shapes a
// formatter produces from one call.
const PREFIXED_CALL = new RegExp(
  `apiFetch(?:WithHeaders)?(?:<[^>]*>)?\\(\\s*\\n?\\s*['"\`]${API_BASE}`,
  "g",
)
const ANY_CALL = /apiFetch(?:WithHeaders)?(?:<[^>]*>)?\(/g
```

Extend the self-test's `doubled` array (line 50) with the new shape:

```ts
    const doubled = [
      `apiFetch("${API_BASE}/knowledge/facts")`,
      "apiFetch<FactListResponse>(\n  `" + API_BASE + "/knowledge/facts`,\n)",
      `apiFetch<T>('${API_BASE}/x')`,
      `apiFetchWithHeaders<void>("${API_BASE}/pages/p/blocks/b")`,
    ]
```

and add a second negative case beside the existing one (after line 58):

```ts
    expect(
      new RegExp(PREFIXED_CALL.source).test('apiFetchWithHeaders<void>("/pages/p")'),
    ).toBe(false)
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run, from `frontend/`:
`npx vitest run src/lib/__tests__/api-fetch-headers.test.ts src/lib/__tests__/api-paths.test.ts`
Expected: PASS, both files.

Then `npm run typecheck`. Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/__tests__/api-paths.test.ts frontend/src/lib/__tests__/api-fetch-headers.test.ts
git commit -m "feat(api): expose response headers to callers"
```

---

### Task 2: Page query keys and the page read hooks

**Files:**
- Create: `frontend/src/hooks/api/use-pages-api.ts`
- Modify: `frontend/src/lib/query-keys.ts` (add three entries to `QUERY_KEY_SCOPE`)
- Modify: `frontend/src/hooks/api/index.ts` (add one re-export line beside lines 22-23)
- Test: `frontend/src/hooks/api/__tests__/use-pages-reads.test.tsx` (create)
- Test: `frontend/src/hooks/api/__tests__/use-pages-api.demo.test.tsx` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: the wire types, `PageView`, `pageQuery`, `usePages`, `usePage`, `usePagesTrash` — see Contracts, `frontend/src/hooks/api/use-pages-api.ts`. Task 3 adds the mutations to this same file; Tasks 4, 7, 9 and 10 consume the types and hooks.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2
**Approach:** inline - skip 2: follows `use-documents-api.ts`'s established query idiom exactly

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/hooks/api/__tests__/use-pages-reads.test.tsx`:

```tsx
import { describe, expect, it, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { pageQuery, usePage, usePages, usePagesTrash } from "../use-pages-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const PAGE_WIRE = {
  id: "p1",
  project: "personal",
  parent_id: null,
  order_index: 0,
  title: "Notes",
  content_hash: "h1",
  properties: null,
  content: null,
  blocks: [
    {
      id: "b1",
      parent_id: null,
      order_index: 0,
      type: "heading",
      text: "Sub",
      properties: { level: 2 },
      char_start: 0,
      char_end: 6,
      source: "## Sub",
    },
    {
      id: "b2",
      parent_id: null,
      order_index: 1,
      type: "paragraph",
      text: null,
      properties: null,
      char_start: null,
      char_end: null,
      source: null,
    },
  ],
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("usePages", () => {
  it("reads the project's flat list and keys on the project", async () => {
    vi.mocked(apiFetch).mockResolvedValue([])
    const { result } = renderHook(() => usePages("my project"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/pages?project=my%20project")
  })
})

describe("usePage", () => {
  it("normalises wire blocks into the editor's BlockRow shape", async () => {
    vi.mocked(apiFetch).mockResolvedValue(PAGE_WIRE)
    const { result } = renderHook(() => usePage("p1"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/pages/p1")
    expect(result.current.data).toEqual({
      id: "p1",
      project: "personal",
      parent_id: null,
      order_index: 0,
      title: "Notes",
      content_hash: "h1",
      blocks: [
        {
          block_id: "b1",
          type: "heading",
          text: "Sub",
          order_index: 0,
          char_span: [0, 6],
          parent_id: null,
          properties: { level: 2 },
          source: "## Sub",
        },
        {
          block_id: "b2",
          type: "paragraph",
          text: "",
          order_index: 1,
          char_span: null,
          parent_id: null,
          properties: null,
          source: null,
        },
      ],
    })
  })

  it("is idle with no page selected", () => {
    const { result } = renderHook(() => usePage(null), { wrapper })
    expect(result.current.fetchStatus).toBe("idle")
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })

  it("shares pageQuery's key so a hash re-read hits the rendered entry", () => {
    expect(pageQuery("p1").queryKey).toEqual(["page", "p1"])
  })
})

describe("usePagesTrash", () => {
  it("does not read while the sheet is closed", () => {
    const { result } = renderHook(() => usePagesTrash("personal", false), { wrapper })
    expect(result.current.fetchStatus).toBe("idle")
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })

  it("reads the trash roots when the sheet opens", async () => {
    vi.mocked(apiFetch).mockResolvedValue([])
    const { result } = renderHook(() => usePagesTrash("personal", true), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/pages/trash?project=personal")
  })
})
```

Create `frontend/src/hooks/api/__tests__/use-pages-api.demo.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { usePage, usePages, usePagesTrash } from "../use-pages-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

// A demo read 401s, and `handleUnauthorized` answers a 401 with a hard
// navigation to /login — one unguarded query takes the whole demo down.
describe("the page reads make no request in demo mode", () => {
  it("leaves every query idle", () => {
    const list = renderHook(() => usePages("personal"), { wrapper })
    const one = renderHook(() => usePage("p1"), { wrapper })
    const trash = renderHook(() => usePagesTrash("personal", true), { wrapper })
    expect(list.result.current.fetchStatus).toBe("idle")
    expect(one.result.current.fetchStatus).toBe("idle")
    expect(trash.result.current.fetchStatus).toBe("idle")
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run, from `frontend/`:
`npx vitest run src/hooks/api/__tests__/use-pages-reads.test.tsx src/hooks/api/__tests__/use-pages-api.demo.test.tsx`
Expected: FAIL — cannot resolve `../use-pages-api`.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/hooks/api/use-pages-api.ts`:

```ts
import { useQuery } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import type { BlockRow } from "./use-documents-api"

export interface PageListItem {
  id: string
  project: string
  parent_id: string | null
  order_index: number
  title: string | null
  content_hash: string
  properties: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface PageTrashItem {
  id: string
  title: string | null
  parent_id: string | null
  deleted_at: string
}

/** The wire row. `PageBlock` names its id `id` and its span as two columns,
 *  where the editor and `BlockView` both read `block_id` and `char_span`. */
interface PageBlockWire {
  id: string
  parent_id: string | null
  order_index: number | null
  type: string | null
  text: string | null
  properties: Record<string, unknown> | null
  char_start: number | null
  char_end: number | null
  source: string | null
}

interface PageWire {
  id: string
  project: string
  parent_id: string | null
  order_index: number
  title: string | null
  content_hash: string
  properties: Record<string, unknown> | null
  content: string | null
  blocks: PageBlockWire[]
}

/** A page and its blocks in the shape the editor already renders. Normalised
 *  here rather than at the view so the block editor and `BlockView` need no
 *  page-specific row type, and so the mutation queue's hash re-read and the
 *  pane read the one cache entry. */
export interface PageView {
  id: string
  project: string
  parent_id: string | null
  order_index: number
  title: string | null
  content_hash: string | null
  blocks: BlockRow[]
}

function toBlockRow(block: PageBlockWire): BlockRow {
  return {
    block_id: block.id,
    type: block.type,
    text: block.text ?? "",
    order_index: block.order_index,
    char_span:
      block.char_start === null || block.char_end === null
        ? null
        : [block.char_start, block.char_end],
    parent_id: block.parent_id,
    properties: block.properties,
    source: block.source,
  }
}

function toPageView(wire: PageWire): PageView {
  return {
    id: wire.id,
    project: wire.project,
    parent_id: wire.parent_id,
    order_index: wire.order_index,
    title: wire.title,
    content_hash: wire.content_hash,
    blocks: wire.blocks.map(toBlockRow),
  }
}

/** Shared so the queue's hash re-read resolves the same cache entry the pane
 *  renders from, rather than a second one under a duplicated key. */
export function pageQuery(pageId: string) {
  return {
    queryKey: ["page", pageId] as const,
    queryFn: async (): Promise<PageView> =>
      toPageView(await apiFetch<PageWire>(`/pages/${pageId}`)),
  }
}

/** Demo mode carries no page fixtures and no backend, so this read 401s there
 *  — and `handleUnauthorized` answers a 401 with a hard navigation to /login,
 *  which takes the page down rather than leaving the tree empty. */
export function usePages(project: string) {
  return useQuery<PageListItem[]>({
    queryKey: ["pages", project],
    queryFn: () =>
      apiFetch<PageListItem[]>(`/pages?project=${encodeURIComponent(project)}`),
    enabled: !DEMO,
  })
}

export function usePage(pageId: string | null) {
  return useQuery<PageView>({
    ...pageQuery(pageId ?? ""),
    enabled: !DEMO && Boolean(pageId),
  })
}

/** `open` gates the read: the trash is a sheet, and a closed sheet has no
 *  reason to hold a list the operator cannot see. */
export function usePagesTrash(project: string, open: boolean) {
  return useQuery<PageTrashItem[]>({
    queryKey: ["pagesTrash", project],
    queryFn: () =>
      apiFetch<PageTrashItem[]>(`/pages/trash?project=${encodeURIComponent(project)}`),
    enabled: !DEMO && open,
  })
}
```

In `frontend/src/lib/query-keys.ts`, add these three entries to `QUERY_KEY_SCOPE`, immediately after the `documentConnections` entry:

```ts
  pages: {
    kind: "manual",
    reason:
      "GET /pages takes an explicit `project` the notes workspace supplies (resolved from the catalogue by kind, not from the global switcher), the same posture `documents` carries",
  },
  page: {
    kind: "global",
    reason:
      "Addressed by page id and carrying no project param, the same shape as documentBlocks: the page's own project scopes the read server-side, so a project-keyed cache entry would key on something the request never sends",
  },
  pagesTrash: {
    kind: "manual",
    reason:
      "GET /pages/trash takes an explicit `project`, the same posture `pages` carries; the notes workspace is the only caller and it is pinned to the personal project",
  },
```

In `frontend/src/hooks/api/index.ts`, add beside the existing document re-exports:

```ts
export * from "./use-pages-api"
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run, from `frontend/`:
`npx vitest run src/hooks/api/__tests__/use-pages-reads.test.tsx src/hooks/api/__tests__/use-pages-api.demo.test.tsx src/lib/__tests__/query-keys.test.ts`
Expected: PASS, all three files. `query-keys.test.ts` is in the list because it scans `src/hooks/api/` for unregistered key literals and fails by name on one.

Then `npm run typecheck`. Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/api/use-pages-api.ts frontend/src/hooks/api/index.ts frontend/src/lib/query-keys.ts frontend/src/hooks/api/__tests__/use-pages-reads.test.tsx frontend/src/hooks/api/__tests__/use-pages-api.demo.test.tsx
git commit -m "feat(notes): add page read hooks and query keys"
```

---

### Task 3: Page and page-block mutation hooks

**Files:**
- Modify: `frontend/src/hooks/api/use-pages-api.ts` (append; Task 2 created it)
- Test: `frontend/src/hooks/api/__tests__/use-pages-mutations.test.tsx` (create)

**Interfaces:**
- Consumes: `apiFetchWithHeaders` (Contracts, Task 1); `pageQuery`, `PageView`, `PageListItem` (Contracts, Task 2); `createMutationQueue` from `@/features/documents/lib/mutation-queue`.
- Produces: `usePageCreate`, `usePageRename`, `usePageMove`, `usePageDelete`, `usePageRestore`, `usePageTrashEmpty`, `usePageBlockUpdate`, `usePageBlockInsert`, `usePageBlockMove`, `usePageBlockDelete`, `usePageBlocksInsertBatch`, `PageBlockWriteResponse`, `NewPageBlock` — see Contracts. Tasks 6, 7, 9 and 10 call them.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3
**Approach:** inline - skip 2: clones `use-blocks-api.ts`'s queue-per-owner pattern, which is the established idiom for exactly this

- [ ] **Step 1: Write the failing test**

Create `frontend/src/hooks/api/__tests__/use-pages-mutations.test.tsx`:

```tsx
import { describe, expect, it, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
  apiFetchWithHeaders: vi.fn(),
}))

import { apiFetch, apiFetchWithHeaders } from "@/lib/api"
import {
  usePageBlockDelete,
  usePageBlockInsert,
  usePageBlockUpdate,
  usePageBlocksInsertBatch,
  usePageCreate,
  usePageMove,
  usePageRename,
} from "../use-pages-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function lastBody() {
  const calls = vi.mocked(apiFetch).mock.calls
  const init = calls[calls.length - 1]![1] as RequestInit
  return JSON.parse(String(init.body))
}

/** The queue's hash re-read goes through `pageQuery`, which normalises a WHOLE
 *  page -- `blocks` included. A stub answering a bare `{content_hash}` throws
 *  inside the normaliser and every write below rejects before it is sent. */
function pageWire(content_hash: string) {
  return {
    id: "p1",
    project: "personal",
    parent_id: null,
    order_index: 0,
    title: "Notes",
    content_hash,
    properties: null,
    content: null,
    blocks: [],
  }
}

/** Writes are the calls carrying a body; the GET arms are not. */
function writeBodies() {
  return vi
    .mocked(apiFetch)
    .mock.calls.filter((c) => (c[1] as RequestInit | undefined)?.body)
    .map((c) => JSON.parse(String((c[1] as RequestInit).body)))
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetchWithHeaders).mockReset()
})

describe("page mutations", () => {
  it("creates a page at the named parent", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ id: "p2" })
    const { result } = renderHook(() => usePageCreate(), { wrapper })
    result.current.mutate({ project: "personal", parentId: "p1", title: "Child" })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe("/pages")
    expect(lastBody()).toEqual({
      project: "personal",
      title: "Child",
      parent_id: "p1",
      after_id: null,
      content: null,
    })
  })

  // The route dispatches on field PRESENCE, so a rename carrying parent_id
  // would move the page to the root and a move carrying title would rename it.
  it("renames without naming parent_id", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ id: "p1" })
    const { result } = renderHook(() => usePageRename(), { wrapper })
    result.current.mutate({ pageId: "p1", title: "New" })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe("/pages/p1")
    expect(lastBody()).toEqual({ title: "New" })
  })

  it("moves without naming title", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ id: "p1" })
    const { result } = renderHook(() => usePageMove(), { wrapper })
    result.current.mutate({ pageId: "p1", parentId: null, afterId: "p3" })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(lastBody()).toEqual({ parent_id: null, after_id: "p3" })
  })
})

describe("page block verbs", () => {
  it("chains the hash from one write into the next", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(pageWire("h1")) // the queue's seed re-read
      .mockResolvedValueOnce({ page_id: "p1", content_hash: "h2" })
      .mockResolvedValueOnce({ page_id: "p1", content_hash: "h3" })
    const { result } = renderHook(() => usePageBlockUpdate("p1"), { wrapper })
    result.current.mutate({ blockId: "b1", text: "one" })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    result.current.mutate({ blockId: "b1", text: "two" })
    await waitFor(() => expect(writeBodies()).toHaveLength(2))
    const bodies = writeBodies()
    expect(bodies[0]!.expected_hash).toBe("h1")
    // The second write carries the first write's answer, not a re-read: only
    // one GET happened.
    expect(bodies[1]!.expected_hash).toBe("h2")
  })

  it("sends a client-chosen block id on insert", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(pageWire("h1"))
      .mockResolvedValueOnce({ page_id: "p1", content_hash: "h2" })
    const { result } = renderHook(() => usePageBlockInsert("p1"), { wrapper })
    result.current.mutate({
      type: "paragraph",
      text: "",
      afterBlockId: "b1",
      blockId: "b9",
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(lastBody()).toMatchObject({
      type: "paragraph",
      text: "",
      after_block_id: "b1",
      block_id: "b9",
    })
  })

  it("takes the delete's new hash from X-Content-Hash, sparing a re-read", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(pageWire("h1"))
      .mockResolvedValueOnce({ page_id: "p1", content_hash: "h3" })
    vi.mocked(apiFetchWithHeaders).mockResolvedValue({
      data: undefined,
      headers: new Headers({ "X-Content-Hash": "h2" }),
    })

    const del = renderHook(() => usePageBlockDelete("p1"), { wrapper })
    del.result.current.mutate({ blockId: "b1" })
    await waitFor(() => expect(del.result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetchWithHeaders).mock.calls[0]![0]).toBe(
      "/pages/p1/blocks/b1?expected_hash=h1",
    )

    const upd = renderHook(() => usePageBlockUpdate("p1"), { wrapper })
    upd.result.current.mutate({ blockId: "b2", text: "x" })
    await waitFor(() => expect(writeBodies()).toHaveLength(1))
    // Exactly one GET, the seed: the delete answered a hash in its header, so
    // the write after it did not have to re-read one. Without the header the
    // queue would null the hash and this would be two.
    expect(
      vi.mocked(apiFetch).mock.calls.filter((c) => !(c[1] as RequestInit | undefined)?.body),
    ).toHaveLength(1)
    expect(lastBody().expected_hash).toBe("h2")
  })

  it("posts a batch insert as one request", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(pageWire("h1"))
      .mockResolvedValueOnce({ page_id: "p1", block_ids: ["b8", "b9"], content_hash: "h2" })
    const { result } = renderHook(() => usePageBlocksInsertBatch("p1"), { wrapper })
    result.current.mutate({
      blocks: [
        { block_id: "b8", type: "paragraph", text: "a" },
        { block_id: "b9", type: "paragraph", text: "b", after_block_id: "b8" },
      ],
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[1]![0]).toBe("/pages/p1/blocks/batch")
    expect(lastBody().blocks).toHaveLength(2)
    expect(lastBody().expected_hash).toBe("h1")
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run, from `frontend/`: `npx vitest run src/hooks/api/__tests__/use-pages-mutations.test.tsx`
Expected: FAIL — `use-pages-api` exports none of the mutation hooks.

- [ ] **Step 3: Write the implementation**

Append to `frontend/src/hooks/api/use-pages-api.ts`, and widen its import line to
`import { useEffect } from "react"` plus
`import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query"` and
`import { apiFetch, apiFetchWithHeaders } from "@/lib/api"` and
`import { createMutationQueue } from "@/features/documents/lib/mutation-queue"`:

```ts
export interface PageBlockWriteResponse {
  page_id: string
  block_id: string | null
  outcome: string
  content_hash: string
  blocks_total: number
  blocks_embedded: number
}

/** The batch route answers its own model: `block_ids`, and no `block_id`. */
export interface PageBlockBatchWriteResponse {
  page_id: string
  block_ids: string[]
  outcome: string
  content_hash: string
  blocks_total: number
  blocks_embedded: number
}

export interface NewPageBlock {
  block_id: string
  type: string
  text: string
  properties?: Record<string, unknown> | null
  parent_id?: string | null
  after_block_id?: string | null
}

function invalidatePageLists(qc: QueryClient) {
  void qc.invalidateQueries({ queryKey: ["pages"] })
  void qc.invalidateQueries({ queryKey: ["pagesTrash"] })
}

export function usePageCreate() {
  const qc = useQueryClient()
  return useMutation<
    { id: string },
    Error,
    {
      project: string
      title?: string | null
      parentId?: string | null
      afterId?: string | null
      content?: string | null
    }
  >({
    mutationFn: ({ project, title, parentId, afterId, content }) =>
      apiFetch<{ id: string }>("/pages", {
        method: "POST",
        body: JSON.stringify({
          project,
          title: title ?? null,
          parent_id: parentId ?? null,
          after_id: afterId ?? null,
          content: content ?? null,
        }),
      }),
    onSuccess: () => invalidatePageLists(qc),
  })
}

/** Rename and move are two hooks over one route because PATCH dispatches on
 *  field PRESENCE: a rename that also named `parent_id` would move the page to
 *  the root, and a move that also named `title` would rename it. */
export function usePageRename() {
  const qc = useQueryClient()
  return useMutation<{ id: string }, Error, { pageId: string; title: string | null }>({
    mutationFn: ({ pageId, title }) =>
      apiFetch<{ id: string }>(`/pages/${pageId}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
      }),
    onSuccess: (_data, { pageId }) => {
      invalidatePageLists(qc)
      void qc.invalidateQueries({ queryKey: ["page", pageId] })
    },
  })
}

export function usePageMove() {
  const qc = useQueryClient()
  return useMutation<
    { id: string },
    Error,
    { pageId: string; parentId: string | null; afterId: string | null }
  >({
    mutationFn: ({ pageId, parentId, afterId }) =>
      apiFetch<{ id: string }>(`/pages/${pageId}`, {
        method: "PATCH",
        body: JSON.stringify({ parent_id: parentId, after_id: afterId }),
      }),
    // Settled rather than succeeded: a refused move is exactly when the
    // optimistically reordered tree is known to be wrong.
    onSettled: () => invalidatePageLists(qc),
  })
}

export function usePageDelete() {
  const qc = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (pageId) => apiFetch<void>(`/pages/${pageId}`, { method: "DELETE" }),
    onSuccess: () => invalidatePageLists(qc),
  })
}

export function usePageRestore() {
  const qc = useQueryClient()
  return useMutation<{ restored: number }, Error, string>({
    mutationFn: (pageId) =>
      apiFetch<{ restored: number }>(`/pages/${pageId}/restore`, { method: "POST" }),
    onSuccess: () => invalidatePageLists(qc),
  })
}

export function usePageTrashEmpty() {
  const qc = useQueryClient()
  return useMutation<{ purged: number }, Error, string>({
    mutationFn: (project) =>
      apiFetch<{ purged: number }>(
        `/pages/trash/empty?project=${encodeURIComponent(project)}`,
        { method: "POST" },
      ),
    onSuccess: () => invalidatePageLists(qc),
  })
}

/** One queue per page, held outside React and created at its first write, so
 *  the update and the insert that follow one keystroke chain rather than both
 *  carrying the hash read before either started. */
const queues = new Map<string, ReturnType<typeof createMutationQueue>>()
const holders = new Map<string, number>()

function queueFor(pageId: string, qc: QueryClient) {
  const existing = queues.get(pageId)
  if (existing) return existing
  const seed = qc.getQueryData<PageView>(pageQuery(pageId).queryKey)?.content_hash ?? null
  const queue = createMutationQueue(seed, async () => {
    if (DEMO) return ""
    const data = await pageQuery(pageId).queryFn()
    return data.content_hash ?? ""
  })
  queues.set(pageId, queue)
  return queue
}

function useQueueLifetime(pageId: string) {
  useEffect(() => {
    holders.set(pageId, (holders.get(pageId) ?? 0) + 1)
    return () => {
      const left = (holders.get(pageId) ?? 1) - 1
      if (left > 0) {
        holders.set(pageId, left)
      } else {
        holders.delete(pageId)
        queues.delete(pageId)
      }
    }
  }, [pageId])
}

function usePageBlockMutation<V>(
  fn: (
    value: V,
    expectedHash: string,
  ) => Promise<{ content_hash: string | null } | void>,
  pageId: string,
) {
  const qc = useQueryClient()
  useQueueLifetime(pageId)
  return useMutation({
    mutationFn: (value: V) =>
      queueFor(pageId, qc).enqueue(async (hash) => {
        const result = await fn(value, hash)
        return { result, content_hash: result?.content_hash ?? null }
      }),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["page", pageId] })
      void qc.invalidateQueries({ queryKey: ["pages"] })
    },
  })
}

function precondition(hash: string) {
  return hash === "" ? undefined : hash
}

export function usePageBlockUpdate(pageId: string) {
  return usePageBlockMutation<{
    blockId: string
    text: string
    type?: string
    properties?: Record<string, unknown> | null
  }>(
    ({ blockId, text, type, properties }, expectedHash) =>
      apiFetch<PageBlockWriteResponse>(`/pages/${pageId}/blocks/${blockId}`, {
        method: "PATCH",
        body: JSON.stringify({
          text,
          type,
          properties,
          expected_hash: precondition(expectedHash),
        }),
      }),
    pageId,
  )
}

export function usePageBlockInsert(pageId: string) {
  return usePageBlockMutation<{
    type: string
    text: string
    parentId?: string | null
    afterBlockId?: string | null
    properties?: Record<string, unknown> | null
    blockId?: string
  }>(
    ({ type, text, parentId, afterBlockId, properties, blockId }, expectedHash) =>
      apiFetch<PageBlockWriteResponse>(`/pages/${pageId}/blocks`, {
        method: "POST",
        body: JSON.stringify({
          type,
          text,
          parent_id: parentId ?? null,
          after_block_id: afterBlockId ?? null,
          properties: properties ?? null,
          block_id: blockId,
          expected_hash: precondition(expectedHash),
        }),
      }),
    pageId,
  )
}

export function usePageBlockMove(pageId: string) {
  return usePageBlockMutation<{
    blockId: string
    newParentId?: string | null
    afterBlockId?: string | null
  }>(
    ({ blockId, newParentId, afterBlockId }, expectedHash) =>
      apiFetch<PageBlockWriteResponse>(`/pages/${pageId}/blocks/${blockId}/move`, {
        method: "POST",
        body: JSON.stringify({
          new_parent_id: newParentId ?? null,
          after_block_id: afterBlockId ?? null,
          expected_hash: precondition(expectedHash),
        }),
      }),
    pageId,
  )
}

export function usePageBlockDelete(pageId: string) {
  return usePageBlockMutation<{ blockId: string }>(
    async ({ blockId }, expectedHash) => {
      // The hash rides the query string because DELETE carries no body, and
      // comes back in a header because a 204 carries none either -- which is
      // what spares the next write a re-read.
      const query = precondition(expectedHash)
        ? `?expected_hash=${encodeURIComponent(expectedHash)}`
        : ""
      const { headers } = await apiFetchWithHeaders<void>(
        `/pages/${pageId}/blocks/${blockId}${query}`,
        { method: "DELETE" },
      )
      return { content_hash: headers.get("X-Content-Hash") }
    },
    pageId,
  )
}

export function usePageBlocksInsertBatch(pageId: string) {
  return usePageBlockMutation<{ blocks: NewPageBlock[] }>(
    ({ blocks }, expectedHash) =>
      apiFetch<PageBlockBatchWriteResponse>(`/pages/${pageId}/blocks/batch`, {
        method: "POST",
        body: JSON.stringify({
          blocks,
          expected_hash: precondition(expectedHash),
        }),
      }),
    pageId,
  )
}
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run, from `frontend/`:
`npx vitest run src/hooks/api/__tests__/use-pages-mutations.test.tsx src/hooks/api/__tests__/use-pages-reads.test.tsx src/hooks/api/__tests__/use-pages-api.demo.test.tsx src/lib/__tests__/query-keys.test.ts`
Expected: PASS, all four files.

Then `npm run typecheck`. Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/api/use-pages-api.ts frontend/src/hooks/api/__tests__/use-pages-mutations.test.tsx
git commit -m "feat(notes): add page and page-block mutations"
```

---

### Task 4: `build-page-tree.ts`

**Files:**
- Create: `frontend/src/features/notes/lib/build-page-tree.ts`
- Test: `frontend/src/features/notes/__tests__/build-page-tree.test.ts` (create)

**Interfaces:**
- Consumes: `PageListItem` (Contracts, Task 2).
- Produces: `PageNode`, `PAGE_TITLE_FALLBACK`, `buildPageTree`, `pageNodeIndex` — see Contracts. Tasks 5, 7, 8, 9 and 10 consume them.

**Implementer:** dr-superpowers:impl-sonnet-low
**Evaluation:** files 0 - spec 0 - coupling 1 - risk 0 = 1
**Approach:** inline - skip 2: a pure tree builder with the complete code below

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/notes/__tests__/build-page-tree.test.ts`:

```ts
import { describe, expect, it } from "vitest"
import type { PageListItem } from "@/hooks/api"
import { buildPageTree, pageNodeIndex } from "../lib/build-page-tree"

function row(
  id: string,
  parent_id: string | null,
  order_index: number,
  title: string | null = id,
): PageListItem {
  return {
    id,
    project: "personal",
    parent_id,
    order_index,
    title,
    content_hash: "h",
    properties: null,
    created_at: "2026-09-18T00:00:00Z",
    updated_at: "2026-09-18T00:00:00Z",
  }
}

const ids = (nodes: { id: string }[]) => nodes.map((n) => n.id)

describe("buildPageTree", () => {
  it("nests children under their parent and sorts by order_index", () => {
    const roots = buildPageTree([
      row("b", null, 1),
      row("a", null, 0),
      row("a2", "a", 1),
      row("a1", "a", 0),
    ])
    expect(ids(roots)).toEqual(["a", "b"])
    expect(ids(roots[0]!.children)).toEqual(["a1", "a2"])
    expect(roots[1]!.children).toEqual([])
  })

  // The route orders by (parent_id, order_index) with NULL parents last, so
  // the list carries no parent-before-child guarantee at all.
  it("is indifferent to row order", () => {
    const rows = [row("c", "b", 0), row("b", "a", 0), row("a", null, 0)]
    const forward = buildPageTree(rows)
    const reversed = buildPageTree([...rows].reverse())
    expect(ids(forward[0]!.children[0]!.children)).toEqual(["c"])
    expect(JSON.stringify(reversed)).toBe(JSON.stringify(forward))
  })

  it("breaks an order_index tie on id, so the tree is stable", () => {
    const roots = buildPageTree([row("z", null, 0), row("m", null, 0)])
    expect(ids(roots)).toEqual(["m", "z"])
  })

  it("treats a row whose parent is not in the list as a root", () => {
    const roots = buildPageTree([row("orphan", "gone", 3), row("a", null, 0)])
    expect(ids(roots)).toEqual(["a", "orphan"])
  })

  it("carries the title through, null included", () => {
    const roots = buildPageTree([row("a", null, 0, null)])
    expect(roots[0]!.title).toBeNull()
  })

  it("returns no roots for an empty list", () => {
    expect(buildPageTree([])).toEqual([])
  })
})

describe("pageNodeIndex", () => {
  it("indexes every node at every depth", () => {
    const roots = buildPageTree([row("a", null, 0), row("b", "a", 0), row("c", "b", 0)])
    const index = pageNodeIndex(roots)
    expect([...index.keys()].sort()).toEqual(["a", "b", "c"])
    expect(index.get("c")!.parent_id).toBe("b")
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run, from `frontend/`: `npx vitest run src/features/notes/__tests__/build-page-tree.test.ts`
Expected: FAIL — cannot resolve `../lib/build-page-tree`.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/features/notes/lib/build-page-tree.ts`:

```ts
import type { PageListItem } from "@/hooks/api"

export interface PageNode {
  id: string
  title: string | null
  parent_id: string | null
  order_index: number
  children: PageNode[]
}

/** What every page surface renders for a page whose title is null. One
 *  constant so the tree, the pane and the trash sheet cannot disagree. */
export const PAGE_TITLE_FALLBACK = "Untitled"

function sortSiblings(nodes: PageNode[]): void {
  // The id tie-break is what makes the tree stable: two siblings can share an
  // order_index, and without it their rendered order would follow whatever
  // order the list happened to arrive in.
  nodes.sort((a, b) =>
    a.order_index === b.order_index
      ? a.id.localeCompare(b.id)
      : a.order_index - b.order_index,
  )
  for (const node of nodes) sortSiblings(node.children)
}

/** Flat rows to a nested tree.
 *
 *  `GET /pages` orders by `(parent_id, order_index)` with NULL parents last,
 *  so a child can arrive before its parent and children of different parents
 *  interleave. Every node is created up front and only then attached, which is
 *  what makes any arrival order give the same tree.
 */
export function buildPageTree(rows: PageListItem[]): PageNode[] {
  const byId = new Map<string, PageNode>()
  for (const row of rows) {
    byId.set(row.id, {
      id: row.id,
      title: row.title,
      parent_id: row.parent_id,
      order_index: row.order_index,
      children: [],
    })
  }
  const roots: PageNode[] = []
  for (const row of rows) {
    const node = byId.get(row.id)!
    const parent = row.parent_id === null ? undefined : byId.get(row.parent_id)
    if (parent) {
      parent.children.push(node)
    } else {
      // A parent outside the list cannot happen against a whole-project read,
      // but a row hidden behind one would otherwise vanish from the tree
      // rather than appear at the root.
      roots.push(node)
    }
  }
  sortSiblings(roots)
  return roots
}

export function pageNodeIndex(roots: PageNode[]): Map<string, PageNode> {
  const index = new Map<string, PageNode>()
  const walk = (nodes: PageNode[]) => {
    for (const node of nodes) {
      index.set(node.id, node)
      walk(node.children)
    }
  }
  walk(roots)
  return index
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run, from `frontend/`: `npx vitest run src/features/notes/__tests__/build-page-tree.test.ts`
Expected: PASS, 7 tests.

Then `npm run typecheck`. Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/lib/build-page-tree.ts frontend/src/features/notes/__tests__/build-page-tree.test.ts
git commit -m "feat(notes): build the nested page tree"
```

---

### Task 5: `drop-target.ts`

**Files:**
- Create: `frontend/src/features/notes/lib/drop-target.ts`
- Test: `frontend/src/features/notes/__tests__/drop-target.test.ts` (create)

**Interfaces:**
- Consumes: `PageNode`, `buildPageTree`, `pageNodeIndex` (Contracts, Task 4).
- Produces: `DropZone`, `DropPlacement`, `dropZoneFor`, `isDescendant`, `resolvePageDrop`, `applyPlacement` — see Contracts. Task 8 consumes the first five; Task 10 consumes `applyPlacement` and `DropPlacement`.

**Implementer:** dr-superpowers:impl-sonnet-low
**Evaluation:** files 0 - spec 0 - coupling 1 - risk 0 = 1
**Approach:** inline - skip 2: the placement rules are stated in the spec and the complete code is below

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/notes/__tests__/drop-target.test.ts`:

```ts
import { describe, expect, it } from "vitest"
import type { PageListItem } from "@/hooks/api"
import { buildPageTree, pageNodeIndex } from "../lib/build-page-tree"
import {
  applyPlacement,
  dropZoneFor,
  isDescendant,
  resolvePageDrop,
} from "../lib/drop-target"

function row(id: string, parent_id: string | null, order_index: number): PageListItem {
  return {
    id,
    project: "personal",
    parent_id,
    order_index,
    title: id,
    content_hash: "h",
    properties: null,
    created_at: "2026-09-18T00:00:00Z",
    updated_at: "2026-09-18T00:00:00Z",
  }
}

//  a          roots: a, d
//  |- b
//  |  |- c
//  |- e
//  d
const ROWS = [
  row("a", null, 0),
  row("b", "a", 0),
  row("c", "b", 0),
  row("e", "a", 1),
  row("d", null, 1),
]
const roots = buildPageTree(ROWS)
const index = pageNodeIndex(roots)
const resolve = (dragged: string, over: string | null, zone: Parameters<typeof resolvePageDrop>[4]) =>
  resolvePageDrop(roots, index, dragged, over, zone)

describe("dropZoneFor", () => {
  it("splits a row into thirds", () => {
    expect(dropZoneFor(1, 30)).toBe("before")
    expect(dropZoneFor(15, 30)).toBe("inside")
    expect(dropZoneFor(29, 30)).toBe("after")
  })

  it("puts the boundaries on the outer side of each third", () => {
    expect(dropZoneFor(10, 30)).toBe("inside")
    expect(dropZoneFor(20, 30)).toBe("inside")
  })

  // jsdom and a collapsed row both produce a zero box; guessing `before`
  // there would make every unmeasured drop a reorder.
  it("falls back to inside when the row has no height", () => {
    expect(dropZoneFor(0, 0)).toBe("inside")
    expect(dropZoneFor(5, -1)).toBe("inside")
  })
})

describe("isDescendant", () => {
  it("finds a descendant at any depth and excludes the node itself", () => {
    expect(isDescendant(index.get("a")!, "c")).toBe(true)
    expect(isDescendant(index.get("a")!, "a")).toBe(false)
    expect(isDescendant(index.get("b")!, "e")).toBe(false)
  })
})

describe("resolvePageDrop", () => {
  it("drops before a row as that row's previous sibling", () => {
    expect(resolve("d", "b", "before")).toEqual({ parentId: "a", afterId: null })
    expect(resolve("d", "e", "before")).toEqual({ parentId: "a", afterId: "b" })
  })

  it("drops after a row as that row itself", () => {
    expect(resolve("d", "b", "after")).toEqual({ parentId: "a", afterId: "b" })
  })

  it("drops inside a row as its last child", () => {
    expect(resolve("d", "a", "inside")).toEqual({ parentId: "a", afterId: "e" })
    expect(resolve("d", "c", "inside")).toEqual({ parentId: "c", afterId: null })
  })

  it("skips the dragged page when reading the target's children", () => {
    // `e` is already a's last child. Unfiltered, "inside a" would anchor it
    // after ITSELF; filtered it resolves to where it already is, which is the
    // no-op the next case refuses.
    expect(resolve("e", "a", "inside")).toBeNull()
    expect(resolve("b", "a", "inside")).toEqual({ parentId: "a", afterId: "e" })
  })

  it("refuses a drop onto the page itself or a descendant of it", () => {
    expect(resolve("a", "a", "inside")).toBeNull()
    expect(resolve("a", "c", "inside")).toBeNull()
    expect(resolve("a", "b", "after")).toBeNull()
  })

  it("refuses a drop on nothing", () => {
    expect(resolve("d", null, "inside")).toBeNull()
    expect(resolve("d", "missing", "inside")).toBeNull()
  })

  it("refuses a placement equal to where the page already is", () => {
    expect(resolve("e", "b", "after")).toBeNull()
    // Before its own next sibling is where `b` already is.
    expect(resolve("b", "e", "before")).toBeNull()
    expect(resolve("d", "a", "after")).toBeNull()
  })
})

describe("applyPlacement", () => {
  const tree = (rows: PageListItem[]) =>
    buildPageTree(rows).map((r) => ({
      id: r.id,
      children: r.children.map((c) => c.id),
    }))

  it("reparents and reorders so the optimistic tree matches the move", () => {
    const next = applyPlacement(ROWS, "d", { parentId: "a", afterId: "b" })
    expect(tree(next)).toEqual([{ id: "a", children: ["b", "d", "e"] }])
  })

  it("places first under a null afterId, as the route does", () => {
    const next = applyPlacement(ROWS, "d", { parentId: "a", afterId: null })
    expect(tree(next)).toEqual([{ id: "a", children: ["d", "b", "e"] }])
  })

  it("moves a page back to the root", () => {
    const next = applyPlacement(ROWS, "b", { parentId: null, afterId: "a" })
    expect(tree(next)).toEqual([
      { id: "a", children: ["e"] },
      { id: "b", children: ["c"] },
      { id: "d", children: [] },
    ])
  })

  it("leaves the input untouched", () => {
    const before = JSON.stringify(ROWS)
    applyPlacement(ROWS, "d", { parentId: "a", afterId: "b" })
    expect(JSON.stringify(ROWS)).toBe(before)
  })

  it("returns the rows unchanged when the page is not in the list", () => {
    expect(applyPlacement(ROWS, "missing", { parentId: null, afterId: null })).toEqual(
      ROWS,
    )
  })
})
```


- [ ] **Step 2: Run the test to verify it fails**

Run, from `frontend/`: `npx vitest run src/features/notes/__tests__/drop-target.test.ts`
Expected: FAIL — cannot resolve `../lib/drop-target`.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/features/notes/lib/drop-target.ts`:

```ts
import type { PageListItem } from "@/hooks/api"
import type { PageNode } from "./build-page-tree"

export type DropZone = "before" | "after" | "inside"

/** What the move sends. A null `afterId` places FIRST among `parentId`'s
 *  children -- `PagePatchRequest.after_id`'s own semantics, and the opposite of
 *  `POST /pages`, where an absent `after_id` appends. */
export interface DropPlacement {
  parentId: string | null
  afterId: string | null
}

export function dropZoneFor(offsetY: number, height: number): DropZone {
  if (height <= 0) return "inside"
  const ratio = offsetY / height
  if (ratio < 1 / 3) return "before"
  if (ratio > 2 / 3) return "after"
  return "inside"
}

export function isDescendant(node: PageNode, candidateId: string): boolean {
  for (const child of node.children) {
    if (child.id === candidateId || isDescendant(child, candidateId)) return true
  }
  return false
}

function siblingsOf(
  roots: PageNode[],
  index: Map<string, PageNode>,
  node: PageNode,
): PageNode[] {
  if (node.parent_id === null) return roots
  return index.get(node.parent_id)?.children ?? roots
}

function placementOf(
  roots: PageNode[],
  index: Map<string, PageNode>,
  node: PageNode,
): DropPlacement {
  const siblings = siblingsOf(roots, index, node)
  const at = siblings.findIndex((s) => s.id === node.id)
  return { parentId: node.parent_id, afterId: at > 0 ? siblings[at - 1]!.id : null }
}

/** Pointer release to a move, or `null` for a refusal.
 *
 *  Every sibling read excludes the dragged page: it is still in the tree the
 *  caller holds, so anchoring on it would send the page after itself.
 */
export function resolvePageDrop(
  roots: PageNode[],
  index: Map<string, PageNode>,
  draggedId: string,
  overId: string | null,
  zone: DropZone,
): DropPlacement | null {
  if (overId === null || overId === draggedId) return null
  const dragged = index.get(draggedId)
  const over = index.get(overId)
  if (!dragged || !over) return null
  // The server refuses a cycle again under its own lock; refusing here is what
  // keeps the optimistic tree from showing one for a round trip.
  if (isDescendant(dragged, overId)) return null

  let placement: DropPlacement
  if (zone === "inside") {
    const children = over.children.filter((c) => c.id !== draggedId)
    placement = {
      parentId: over.id,
      afterId: children.length > 0 ? children[children.length - 1]!.id : null,
    }
  } else if (zone === "after") {
    placement = { parentId: over.parent_id, afterId: over.id }
  } else {
    const siblings = siblingsOf(roots, index, over).filter((s) => s.id !== draggedId)
    const at = siblings.findIndex((s) => s.id === over.id)
    placement = {
      parentId: over.parent_id,
      afterId: at > 0 ? siblings[at - 1]!.id : null,
    }
  }

  const current = placementOf(roots, index, dragged)
  if (current.parentId === placement.parentId && current.afterId === placement.afterId) {
    return null
  }
  return placement
}

/** The same placement applied to the flat list, for the optimistic update.
 *
 *  The move is shown before the server answers and the refusal path rolls it
 *  back, so this has to reproduce the server's own ordering: a null `afterId`
 *  places FIRST, and the new sibling run is renumbered from zero because
 *  `buildPageTree` sorts on `(order_index, id)`.
 */
export function applyPlacement(
  rows: PageListItem[],
  pageId: string,
  placement: DropPlacement,
): PageListItem[] {
  if (!rows.some((row) => row.id === pageId)) return rows

  const moved = { ...rows.find((row) => row.id === pageId)!, parent_id: placement.parentId }
  const others = rows.filter((row) => row.id !== pageId)
  const siblings = others
    .filter((row) => row.parent_id === placement.parentId)
    .sort((a, b) =>
      a.order_index === b.order_index
        ? a.id.localeCompare(b.id)
        : a.order_index - b.order_index,
    )

  const at =
    placement.afterId === null
      ? 0
      : siblings.findIndex((row) => row.id === placement.afterId) + 1
  siblings.splice(at, 0, moved)

  const renumbered = new Map(
    siblings.map((row, order_index) => [row.id, { ...row, order_index }]),
  )
  return [...others, moved].map((row) => renumbered.get(row.id) ?? row)
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run, from `frontend/`: `npx vitest run src/features/notes/__tests__/drop-target.test.ts`
Expected: PASS, 16 tests.

Then `npm run typecheck`. Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/lib/drop-target.ts frontend/src/features/notes/__tests__/drop-target.test.ts
git commit -m "feat(notes): resolve a page drop to a move"
```

---

### Task 6: The page pane and the copied block editor

**Files:**
- Create: `frontend/src/features/notes/page-block-editor.tsx`
- Create: `frontend/src/features/notes/page-pane.tsx`
- Test: `frontend/src/features/notes/__tests__/page-block-editor.test.tsx` (create)
- Test: `frontend/src/features/notes/__tests__/page-pane.test.tsx` (create)

**Interfaces:**
- Consumes: `PageView`, `usePageBlockUpdate`, `usePageBlockInsert`, `usePageBlockDelete`, `usePageRename` (Contracts, Tasks 2 and 3); `PAGE_TITLE_FALLBACK` (Contracts, Task 4); `BlockView` from `@/features/documents/components/block-view`.
- Produces: `promote`, `PageSaveStatus`, `PageBlockEditor`, `PagePane` — see Contracts. Task 10 mounts `PagePane`.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3
**Approach:** inline - skip 2: a deliberate copy of `block-editor.tsx` plus the save-state and banner spec §6 names

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/features/notes/__tests__/page-block-editor.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { useState, type ReactNode } from "react"
import { describe, expect, it, vi, beforeEach } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
  return { apiFetch: vi.fn(), apiFetchWithHeaders: vi.fn(), ApiError }
})

import { apiFetch, ApiError } from "@/lib/api"
import type { BlockRow } from "@/hooks/api"
import { PageBlockEditor, promote } from "../page-block-editor"

function wrapper({ children }: { children: ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      }),
  )
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const BLOCKS: BlockRow[] = [
  {
    block_id: "b1",
    type: "paragraph",
    text: "hello",
    order_index: 0,
    char_span: [0, 5],
    parent_id: null,
    properties: null,
    source: "hello",
  },
]

/** The queue's hash re-read goes through `pageQuery`, which normalises a WHOLE
 *  page. A stub answering every call with a write response throws inside the
 *  normaliser and every edit below rejects before it is sent, so the GET arm
 *  is routed separately. */
function route(path: string, init?: RequestInit) {
  if (!init?.body) {
    return Promise.resolve({
      id: "p1",
      project: "personal",
      parent_id: null,
      order_index: 0,
      title: "Notes",
      content_hash: "h1",
      properties: null,
      content: null,
      blocks: [],
    })
  }
  return Promise.resolve({ page_id: "p1", content_hash: "h2" })
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetch).mockImplementation(route as never)
})

describe("promote", () => {
  it("reads the markers the serialiser emits", () => {
    expect(promote("## Sub")).toEqual({
      type: "heading",
      text: "Sub",
      properties: { level: 2 },
    })
    expect(promote("- item")).toEqual({
      type: "list",
      text: "item",
      properties: { marker: "-" },
    })
    expect(promote("> quoted")).toEqual({ type: "quote", text: "quoted" })
    expect(promote("---")).toEqual({ type: "divider", text: "" })
    expect(promote("plain")).toEqual({ type: "paragraph", text: "plain" })
  })

  it("preserves an html block's type, which has no marker to read back", () => {
    expect(promote("<b>bold</b> text", "html")).toEqual({
      type: "html",
      text: "<b>bold</b> text",
    })
  })
})

describe("PageBlockEditor", () => {
  it("edits the block's source and sends the promoted type", async () => {
    render(
      <PageBlockEditor pageId="p1" blocks={BLOCKS} onStatus={vi.fn()} />,
      { wrapper },
    )
    fireEvent.click(screen.getByRole("button", { name: /hello/ }))
    const area = screen.getByLabelText("block source")
    expect(area).toHaveValue("hello")
    fireEvent.change(area, { target: { value: "## Head" } })
    fireEvent.blur(area)
    await waitFor(() => {
      const call = vi
        .mocked(apiFetch)
        .mock.calls.find((c) => String(c[0]).includes("/blocks/b1"))
      expect(call).toBeTruthy()
      expect(JSON.parse(String((call![1] as RequestInit).body))).toMatchObject({
        type: "heading",
        text: "Head",
        properties: { level: 2 },
      })
    })
  })

  it("reports Saving then Saved", async () => {
    const onStatus = vi.fn()
    render(<PageBlockEditor pageId="p1" blocks={BLOCKS} onStatus={onStatus} />, {
      wrapper,
    })
    fireEvent.click(screen.getByRole("button", { name: /hello/ }))
    fireEvent.change(screen.getByLabelText("block source"), {
      target: { value: "changed" },
    })
    fireEvent.blur(screen.getByLabelText("block source"))
    await waitFor(() =>
      expect(onStatus.mock.calls.map(([s]) => s.kind)).toContain("saving"),
    )
    await waitFor(() =>
      expect(onStatus.mock.calls.map(([s]) => s.kind)).toContain("saved"),
    )
  })

  it("reports the server's own message when a write is refused", async () => {
    vi.mocked(apiFetch).mockImplementation(((path: string, init?: RequestInit) =>
      init?.body
        ? Promise.reject(new ApiError("expected_hash a does not match b", 409))
        : route(path)) as never)
    const onStatus = vi.fn()
    render(<PageBlockEditor pageId="p1" blocks={BLOCKS} onStatus={onStatus} />, {
      wrapper,
    })
    fireEvent.click(screen.getByRole("button", { name: /hello/ }))
    fireEvent.change(screen.getByLabelText("block source"), {
      target: { value: "changed" },
    })
    fireEvent.blur(screen.getByLabelText("block source"))
    await waitFor(() => {
      const blocked = onStatus.mock.calls
        .map(([s]) => s)
        .find((s) => s.kind === "blocked")
      expect(blocked?.message).toBe("expected_hash a does not match b")
    })
  })

  it("does not write when the source is unchanged", async () => {
    render(<PageBlockEditor pageId="p1" blocks={BLOCKS} onStatus={vi.fn()} />, {
      wrapper,
    })
    fireEvent.click(screen.getByRole("button", { name: /hello/ }))
    fireEvent.blur(screen.getByLabelText("block source"))
    await waitFor(() => expect(screen.queryByLabelText("block source")).toBeNull())
    expect(
      vi.mocked(apiFetch).mock.calls.filter(
        (c) => (c[1] as RequestInit | undefined)?.body,
      ),
    ).toHaveLength(0)
  })
})
```

Create `frontend/src/features/notes/__tests__/page-pane.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { useState, type ReactNode } from "react"
import { describe, expect, it, vi, beforeEach } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn(), apiFetchWithHeaders: vi.fn() }))
vi.mock("../page-block-editor", () => ({
  PageBlockEditor: ({
    pageId,
    onStatus,
  }: {
    pageId: string
    onStatus: (s: { kind: string; message?: string }) => void
  }) => (
    <div>
      editor:{pageId}
      <button type="button" onClick={() => onStatus({ kind: "saving" })}>
        report saving
      </button>
      <button
        type="button"
        onClick={() => onStatus({ kind: "blocked", message: "the page moved" })}
      >
        report blocked
      </button>
    </div>
  ),
}))

import { apiFetch } from "@/lib/api"
import type { PageView } from "@/hooks/api"
import { PagePane } from "../page-pane"

function wrapper({ children }: { children: ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      }),
  )
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const PAGE: PageView = {
  id: "p1",
  project: "personal",
  parent_id: null,
  order_index: 0,
  title: "Notes",
  content_hash: "h1",
  blocks: [],
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetch).mockResolvedValue({ id: "p1" })
})

describe("PagePane", () => {
  it("renders the title in an editable field and the editor below it", () => {
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    expect(screen.getByLabelText("Page title")).toHaveValue("Notes")
    expect(screen.getByText("editor:p1")).toBeInTheDocument()
  })

  it("shows the fallback for an untitled page without sending it as a title", () => {
    render(<PagePane page={{ ...PAGE, title: null }} autoFocusTitle={false} />, {
      wrapper,
    })
    const field = screen.getByLabelText("Page title")
    expect(field).toHaveValue("")
    expect(field).toHaveAttribute("placeholder", "Untitled")
  })

  it("renames on blur, and not when the title is unchanged", async () => {
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    const field = screen.getByLabelText("Page title")
    fireEvent.blur(field)
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
    fireEvent.change(field, { target: { value: "Renamed" } })
    fireEvent.blur(field)
    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/pages/p1", {
        method: "PATCH",
        body: JSON.stringify({ title: "Renamed" }),
      }),
    )
  })

  it("focuses the title when asked", () => {
    render(<PagePane page={PAGE} autoFocusTitle />, { wrapper })
    expect(screen.getByLabelText("Page title")).toHaveFocus()
  })

  it("shows the save state and the blocked banner the editor reports", async () => {
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    fireEvent.click(screen.getByText("report saving"))
    expect(await screen.findByText("Saving…")).toBeInTheDocument()
    fireEvent.click(screen.getByText("report blocked"))
    expect(await screen.findByText(/the page moved/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Reload page" })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run, from `frontend/`:
`npx vitest run src/features/notes/__tests__/page-block-editor.test.tsx src/features/notes/__tests__/page-pane.test.tsx`
Expected: FAIL — neither module resolves.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/features/notes/page-block-editor.tsx`:

```tsx
import { useEffect, useRef, useState } from "react"
import { Textarea } from "darkraise-ui/components/textarea"
import { cn } from "darkraise-ui/lib"
import { BlockView } from "@/features/documents/components/block-view"
import {
  usePageBlockDelete,
  usePageBlockInsert,
  usePageBlockUpdate,
  type BlockRow,
} from "@/hooks/api"

/** Promote a block's source to its type, mirroring the serialiser's emit
 *  rules and nothing more.
 *
 *  This duplicates `backend/app/services/block_serializer.py`'s markers in
 *  TypeScript. `block_serializer` is the authority; if the two disagree, it
 *  wins. It offers none of the page-only markers -- to-do, toggle and callout
 *  reach a page through the editor B3 ships, never through a markdown marker
 *  here.
 *
 *  Deleting a marker DEMOTES: no marker means paragraph. That is only
 *  possible because the editor holds `source` rather than `text`.
 *
 *  `stored` decides the fallback for the one type with no marker to read
 *  back: an `html` block's source IS its text, so every marker rule misses it
 *  and the fallback would demote it to paragraph on its first edit.
 */
export function promote(
  source: string,
  stored?: string | null,
): {
  type: string
  text: string
  properties?: Record<string, unknown>
} {
  const heading = /^(#{1,6})\s+(.*)$/.exec(source)
  if (heading) {
    return {
      type: "heading",
      text: heading[2] ?? "",
      properties: { level: heading[1]!.length },
    }
  }
  if (/^(?:-{3,}|\*{3,}|_{3,})\s*$/.test(source.trim())) {
    return { type: "divider", text: "" }
  }
  const list = /^([-*+]|\d+[.)])\s+([\s\S]*)$/.exec(source)
  if (list) {
    return { type: "list", text: list[2] ?? "", properties: { marker: list[1] } }
  }
  const quote = /^>\s?([\s\S]*)$/.exec(source)
  if (quote) return { type: "quote", text: quote[1] ?? "" }
  if (source.startsWith("```")) {
    const lines = source.split("\n")
    return { type: "code", text: lines.slice(1, -1).join("\n") }
  }
  if (stored === "html") return { type: "html", text: source }
  return { type: "paragraph", text: source }
}

export type PageSaveStatus =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved" }
  | { kind: "blocked"; message: string }

/** A deliberate copy of `features/documents/components/block-editor.tsx` over
 *  the page hooks, recorded as a duplicate that B3 deletes. The document
 *  editor is not parameterised, so `/documents` does not change.
 *
 *  It reports its save state upward rather than rendering it, because spec §6
 *  puts that state and the refusal banner in the pane's header.
 */
export function PageBlockEditor({
  pageId,
  blocks,
  onStatus,
}: {
  pageId: string
  blocks: BlockRow[]
  onStatus: (status: PageSaveStatus) => void
}) {
  const [focused, setFocused] = useState<string | null>(null)
  const [draft, setDraft] = useState("")
  const [failure, setFailure] = useState<{ id: string; message: string } | null>(null)
  const update = usePageBlockUpdate(pageId)
  const insert = usePageBlockInsert(pageId)
  const remove = usePageBlockDelete(pageId)
  const area = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    if (focused) area.current?.focus()
  }, [focused])

  const sourceOf = (block: BlockRow) => block.source ?? block.text

  const report = (status: PageSaveStatus) => onStatus(status)

  const settle = (blockId: string) => ({
    onSuccess: () => {
      setFailure(null)
      report({ kind: "saved" })
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error)
      setFailure({ id: blockId, message })
      report({ kind: "blocked", message })
    },
  })

  const commit = (block: BlockRow) => {
    const next = draft
    setFocused(null)
    if (next === sourceOf(block)) return
    const { type, text, properties } = promote(next, block.type)
    report({ kind: "saving" })
    update.mutate(
      { blockId: block.block_id, text, type, properties: properties ?? null },
      settle(block.block_id),
    )
  }

  return (
    <div className="space-y-1.5">
      {blocks.map((block) => (
        <div key={block.block_id} id={block.block_id}>
          {focused === block.block_id ? (
            <Textarea
              ref={area}
              value={draft}
              rows={Math.max(1, draft.split("\n").length)}
              aria-label="block source"
              className="font-mono text-sm"
              onChange={(e) => setDraft(e.target.value)}
              onBlur={() => commit(block)}
              onKeyDown={(e) => {
                if (e.key === "Escape") {
                  commit(block)
                } else if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault()
                  commit(block)
                  report({ kind: "saving" })
                  insert.mutate(
                    {
                      type: "paragraph",
                      text: "",
                      afterBlockId: block.block_id,
                      blockId: crypto.randomUUID(),
                    },
                    settle(block.block_id),
                  )
                } else if (e.key === "Backspace" && draft === "") {
                  e.preventDefault()
                  setFocused(null)
                  report({ kind: "saving" })
                  remove.mutate({ blockId: block.block_id }, settle(block.block_id))
                }
              }}
            />
          ) : (
            <button
              type="button"
              className={cn(
                "hover:bg-muted/40 block w-full rounded px-1 py-0.5 text-left",
              )}
              onClick={() => {
                setDraft(sourceOf(block))
                setFocused(block.block_id)
              }}
            >
              <BlockView block={block} />
            </button>
          )}
          {failure?.id === block.block_id ? (
            <p className="text-destructive text-sm">
              the edit was not saved — {failure.message}
            </p>
          ) : null}
        </div>
      ))}
    </div>
  )
}
```

Create `frontend/src/features/notes/page-pane.tsx`:

```tsx
import { useEffect, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import { usePageRename, type PageView } from "@/hooks/api"
import { PAGE_TITLE_FALLBACK } from "./lib/build-page-tree"
import { PageBlockEditor, type PageSaveStatus } from "./page-block-editor"

const SAVE_LABEL: Record<string, string> = {
  saving: "Saving…",
  saved: "Saved",
}

/** The title field and the body.
 *
 *  The title is `pages.title` over `PATCH /pages/{id}`, never a block, so it
 *  is the one edit here that does not go through the block queue.
 */
export function PagePane({
  page,
  autoFocusTitle,
}: {
  page: PageView
  autoFocusTitle: boolean
}) {
  const qc = useQueryClient()
  const rename = usePageRename()
  const [title, setTitle] = useState(page.title ?? "")
  const [status, setStatus] = useState<PageSaveStatus>({ kind: "idle" })
  const field = useRef<HTMLInputElement | null>(null)

  // Remount-free page switch: the pane is keyed on nothing, so the draft has
  // to follow the page it is showing.
  useEffect(() => {
    setTitle(page.title ?? "")
    setStatus({ kind: "idle" })
  }, [page.id, page.title])

  useEffect(() => {
    if (autoFocusTitle) field.current?.focus()
  }, [autoFocusTitle, page.id])

  const commitTitle = () => {
    const next = title.trim()
    if (next === (page.title ?? "")) return
    rename.mutate({ pageId: page.id, title: next === "" ? null : next })
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <div className="flex items-center gap-3">
        <Label htmlFor="page-title" className="sr-only">
          Page title
        </Label>
        <Input
          id="page-title"
          ref={field}
          aria-label="Page title"
          placeholder={PAGE_TITLE_FALLBACK}
          value={title}
          className="h-auto border-0 px-0 text-2xl font-semibold shadow-none focus-visible:ring-0"
          onChange={(e) => setTitle(e.target.value)}
          onBlur={commitTitle}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault()
              e.currentTarget.blur()
            }
          }}
        />
        {SAVE_LABEL[status.kind] ? (
          <span className="text-muted-foreground shrink-0 text-xs">
            {SAVE_LABEL[status.kind]}
          </span>
        ) : null}
      </div>

      {status.kind === "blocked" ? (
        <div className="border-destructive/50 flex items-center justify-between gap-3 rounded-md border border-dashed px-3 py-2">
          <p className="text-destructive text-sm">
            This page changed elsewhere — {status.message}
          </p>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => {
              setStatus({ kind: "idle" })
              void qc.invalidateQueries({ queryKey: ["page", page.id] })
            }}
          >
            Reload page
          </Button>
        </div>
      ) : null}

      <ScrollArea className="min-h-0 flex-1 pr-3">
        <PageBlockEditor pageId={page.id} blocks={page.blocks} onStatus={setStatus} />
      </ScrollArea>
    </div>
  )
}
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run, from `frontend/`:
`npx vitest run src/features/notes/__tests__/page-block-editor.test.tsx src/features/notes/__tests__/page-pane.test.tsx`
Expected: PASS, both files.

Then `npm run typecheck`. Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/page-block-editor.tsx frontend/src/features/notes/page-pane.tsx frontend/src/features/notes/__tests__/page-block-editor.test.tsx frontend/src/features/notes/__tests__/page-pane.test.tsx
git commit -m "feat(notes): add the page pane and block editor"
```

---

### Task 7: `PageTree` rows, selection, expansion and row actions

**Files:**
- Create: `frontend/src/features/notes/page-tree.tsx`
- Test: `frontend/src/features/notes/__tests__/page-tree.test.tsx` (create)

**Interfaces:**
- Consumes: `PageNode`, `PAGE_TITLE_FALLBACK` (Contracts, Task 4).
- Produces: `notesExpansionStorageKey`, `PageTree` — see Contracts. Task 8 adds the drag layer to this file; Task 10 mounts it.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 0 - spec 1 - coupling 1 - risk 1 = 3
**Approach:** inline - skip 2: mirrors `document-tree.tsx`'s use of darkraise-ui TreeView parts, which is the established row idiom

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/notes/__tests__/page-tree.test.tsx`:

```tsx
import { fireEvent, render, screen, within } from "@testing-library/react"
import { describe, expect, it, vi, beforeEach } from "vitest"

import type { PageListItem } from "@/hooks/api"
import { buildPageTree, pageNodeIndex } from "../lib/build-page-tree"
import { PageTree, notesExpansionStorageKey } from "../page-tree"

function row(
  id: string,
  parent_id: string | null,
  order_index: number,
  title: string | null = id,
): PageListItem {
  return {
    id,
    project: "personal",
    parent_id,
    order_index,
    title,
    content_hash: "h",
    properties: null,
    created_at: "2026-09-18T00:00:00Z",
    updated_at: "2026-09-18T00:00:00Z",
  }
}

const ROWS = [row("a", null, 0, "Alpha"), row("b", "a", 0, "Beta"), row("c", null, 1, null)]

/** Seeds the persisted expansion, because `TreeViewBranchContent` renders
 *  nothing while its branch is closed -- a test that expects a child row has to
 *  open its parent first. */
function seedExpanded(...ids: string[]) {
  window.localStorage.setItem(
    notesExpansionStorageKey("personal"),
    JSON.stringify(ids),
  )
}

function renderTree(props: Partial<Parameters<typeof PageTree>[0]> = {}) {
  const roots = buildPageTree(ROWS)
  const handlers = {
    onSelect: vi.fn(),
    onNewChild: vi.fn(),
    onRename: vi.fn(),
    onDelete: vi.fn(),
    onMove: vi.fn(),
  }
  render(
    <PageTree
      roots={roots}
      index={pageNodeIndex(roots)}
      project="personal"
      selectedId={null}
      {...handlers}
      {...props}
    />,
  )
  return handlers
}

beforeEach(() => {
  window.localStorage.clear()
})

describe("PageTree", () => {
  it("renders the roots, untitled ones by their fallback", () => {
    renderTree()
    expect(screen.getByText("Alpha")).toBeInTheDocument()
    expect(screen.getByText("Untitled")).toBeInTheDocument()
    // The branch is closed, so its child is not in the document at all.
    expect(screen.queryByText("Beta")).toBeNull()
  })

  it("renders a child once its parent is expanded", () => {
    seedExpanded("a")
    renderTree()
    expect(screen.getByText("Beta")).toBeInTheDocument()
  })

  it("reports a selection by page id", () => {
    const { onSelect } = renderTree()
    fireEvent.click(screen.getByText("Alpha"))
    expect(onSelect).toHaveBeenCalledWith("a")
  })

  it("offers new child, rename and delete on a row", () => {
    const { onNewChild, onRename, onDelete } = renderTree()
    fireEvent.click(screen.getByRole("button", { name: "New page under Alpha" }))
    expect(onNewChild).toHaveBeenCalledWith("a")

    fireEvent.click(screen.getByRole("button", { name: "Actions for Alpha" }))
    const menu = screen.getByRole("menu")
    fireEvent.click(within(menu).getByText("Rename"))
    expect(onRename).toHaveBeenCalledWith(expect.objectContaining({ id: "a" }))

    fireEvent.click(screen.getByRole("button", { name: "Actions for Alpha" }))
    fireEvent.click(within(screen.getByRole("menu")).getByText("Delete"))
    expect(onDelete).toHaveBeenCalledWith(expect.objectContaining({ id: "a" }))
  })

  it("writes the expanded set when a branch is toggled", () => {
    seedExpanded("a")
    renderTree()
    // `TreeViewBranchControl`'s own click handler calls `toggleExpanded`, so
    // clicking the label closes the branch.
    fireEvent.click(screen.getByText("Alpha"))
    expect(screen.queryByText("Beta")).toBeNull()
    expect(
      JSON.parse(window.localStorage.getItem(notesExpansionStorageKey("personal"))!),
    ).toEqual([])
  })

  // Storage can be absent or throw (private browsing, blocked site data), and
  // the tree must render either way.
  it("renders collapsed when storage throws", () => {
    const getItem = vi
      .spyOn(window.localStorage, "getItem")
      .mockImplementation(() => {
        throw new Error("blocked")
      })
    expect(() => renderTree()).not.toThrow()
    expect(screen.getByText("Alpha")).toBeInTheDocument()
    getItem.mockRestore()
  })

  it("shows an empty state with a create affordance when there are no pages", () => {
    render(
      <PageTree
        roots={[]}
        index={new Map()}
        project="personal"
        selectedId={null}
        onSelect={vi.fn()}
        onNewChild={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
        onMove={vi.fn()}
      />,
    )
    expect(screen.getByText(/No pages yet/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run, from `frontend/`: `npx vitest run src/features/notes/__tests__/page-tree.test.tsx`
Expected: FAIL — cannot resolve `../page-tree`.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/features/notes/page-tree.tsx`:

```tsx
import { useCallback, useState, type CSSProperties, type ReactNode } from "react"
import { ChevronRight, FileText, MoreHorizontal, Plus } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "darkraise-ui/components/dropdown-menu"
import {
  TreeView,
  TreeViewBranch,
  TreeViewBranchContent,
  TreeViewBranchControl,
  TreeViewBranchIndicator,
  TreeViewBranchText,
  TreeViewItem,
  TreeViewTree,
} from "darkraise-ui/components/tree-view"
import { EmptyState } from "@/components/darkmem"
import { PAGE_TITLE_FALLBACK, type PageNode } from "./lib/build-page-tree"
import type { DropPlacement } from "./lib/drop-target"

const ROW = "w-full min-w-0 text-base"
const ROW_GAP = "gap-1.5"
const INDENT = "calc(var(--icon-size) + 0.375rem)"

export function notesExpansionStorageKey(project: string): string {
  return `darkmem:notes:expanded:${project}`
}

/** Storage is per viewer and can be absent or throw outright (private
 *  browsing, blocked site data), so every access is guarded and the tree
 *  renders collapsed when it fails rather than not at all. */
function readExpanded(project: string): string[] {
  try {
    const raw = window.localStorage.getItem(notesExpansionStorageKey(project))
    const parsed = raw ? (JSON.parse(raw) as unknown) : null
    return Array.isArray(parsed) ? parsed.filter((v) => typeof v === "string") : []
  } catch {
    return []
  }
}

function writeExpanded(project: string, ids: string[]): void {
  try {
    window.localStorage.setItem(notesExpansionStorageKey(project), JSON.stringify(ids))
  } catch {
    // A viewer convenience, never state the tree depends on.
  }
}

function titleOf(node: PageNode): string {
  return node.title?.trim() ? node.title : PAGE_TITLE_FALLBACK
}

function RowActions({
  node,
  onNewChild,
  onRename,
  onDelete,
}: {
  node: PageNode
  onNewChild: (parentId: string) => void
  onRename: (node: PageNode) => void
  onDelete: (node: PageNode) => void
}) {
  const label = titleOf(node)
  // Both stop propagation: React synthetic events bubble the React ancestor
  // chain even out of a portal, so without it opening the menu also selects
  // the row and navigates away from whatever the pane is editing.
  return (
    <span className="ml-auto flex shrink-0 items-center opacity-0 group-hover:opacity-100 focus-within:opacity-100">
      <button
        type="button"
        aria-label={`New page under ${label}`}
        className="text-muted-foreground hover:text-foreground rounded p-0.5"
        onClick={(event) => {
          event.stopPropagation()
          onNewChild(node.id)
        }}
      >
        <Plus aria-hidden className="size-4" />
      </button>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label={`Actions for ${label}`}
          className="text-muted-foreground hover:text-foreground rounded p-0.5"
          onClick={(event) => event.stopPropagation()}
        >
          <MoreHorizontal aria-hidden className="size-4" />
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="end"
          onClick={(event) => event.stopPropagation()}
        >
          <DropdownMenuItem onSelect={() => onRename(node)}>Rename</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => onDelete(node)}>Delete</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </span>
  )
}

/** The page hierarchy.
 *
 *  darkraise-ui's TreeView ships the behaviour (roving focus, selection,
 *  keyboard traversal) and no drag support; the drag layer beside it is local
 *  for that gap and should be retired if a later version closes it. The row
 *  itself is this feature's own rather than `DocumentTree`'s: that component
 *  is keyed on uri paths at every level and is rendered by `/documents` and
 *  `/projects/$project`, which this increment does not change.
 */
export function PageTree({
  roots,
  index,
  project,
  selectedId,
  onSelect,
  onNewChild,
  onRename,
  onDelete,
  onMove,
}: {
  roots: PageNode[]
  index: Map<string, PageNode>
  project: string
  selectedId: string | null
  onSelect: (pageId: string) => void
  onNewChild: (parentId: string) => void
  onRename: (node: PageNode) => void
  onDelete: (node: PageNode) => void
  onMove: (pageId: string, placement: DropPlacement) => void
}) {
  const [expanded, setExpanded] = useState<string[]>(() => readExpanded(project))

  const handleExpandedChange = useCallback(
    (next: string[]) => {
      setExpanded(next)
      writeExpanded(project, next)
    },
    [project],
  )

  void index
  void onMove

  if (roots.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={FileText}
        title="No pages yet"
        description="New page starts one. Nothing here is a project artifact."
      />
    )
  }

  const renderNode = (node: PageNode): ReactNode => {
    const actions = (
      <RowActions
        node={node}
        onNewChild={onNewChild}
        onRename={onRename}
        onDelete={onDelete}
      />
    )
    if (node.children.length > 0) {
      return (
        <TreeViewBranch key={node.id} value={node.id}>
          <TreeViewBranchControl className={`group relative ${ROW_GAP} ${ROW}`}>
            <TreeViewBranchIndicator className="text-muted-foreground shrink-0">
              <ChevronRight aria-hidden className="size-3.5" />
            </TreeViewBranchIndicator>
            <TreeViewBranchText className="truncate">
              {titleOf(node)}
            </TreeViewBranchText>
            {actions}
          </TreeViewBranchControl>
          <TreeViewBranchContent className="gap-0">
            {node.children.map(renderNode)}
          </TreeViewBranchContent>
        </TreeViewBranch>
      )
    }
    return (
      <TreeViewItem
        key={node.id}
        value={node.id}
        className={`group relative ${ROW_GAP} ${ROW}`}
      >
        {/* Aligns a leaf's text with a sibling branch's, whose row spends this
            width on the chevron. */}
        <span aria-hidden className="w-[var(--icon-size)] shrink-0" />
        <span className="truncate">{titleOf(node)}</span>
        {actions}
      </TreeViewItem>
    )
  }

  return (
    <TreeView
      expanded={expanded}
      onExpandedChange={(d: { value: string[] }) => handleExpandedChange(d.value)}
      selectionMode="single"
      selected={selectedId ? [selectedId] : []}
      onSelectedChange={({ value }: { value: string[] }) => {
        const id = value.find((v) => index.has(v))
        if (id) onSelect(id)
      }}
    >
      <TreeViewTree
        className="gap-0 pl-1"
        style={{ "--tree-view-indent": INDENT } as CSSProperties}
      >
        {roots.map(renderNode)}
      </TreeViewTree>
    </TreeView>
  )
}
```

The two `void` statements carry no behaviour — they keep the unused props from
failing `tsc` until Task 8 reads them, and Task 8 replaces both lines. They are
deliberately placed **below** `handleExpandedChange`, because Task 8's drag
handlers name that callback in their dependency arrays, which JavaScript
evaluates eagerly: declared above it, the component would throw
`Cannot access 'handleExpandedChange' before initialization` on first render.
Neither `void` line carries a comment, per the repo's comment rule.

- [ ] **Step 4: Run the test to verify it passes**

Run, from `frontend/`: `npx vitest run src/features/notes/__tests__/page-tree.test.tsx`
Expected: PASS, 7 tests.

If a darkraise-ui TreeView part's prop names differ from the shapes above, read
`frontend/node_modules/darkraise-ui/dist/components/tree-view.d.ts` and follow it —
`document-tree.tsx:432-535` is the working reference for every part used here.

Then `npm run typecheck`. Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/page-tree.tsx frontend/src/features/notes/__tests__/page-tree.test.tsx
git commit -m "feat(notes): render the page tree with row actions"
```

---

### Task 8: `PageTree` drag to reorder

**Files:**
- Modify: `frontend/src/features/notes/page-tree.tsx` (Task 7 created it)
- Test: `frontend/src/features/notes/__tests__/page-tree-drag.test.tsx` (create)

**Interfaces:**
- Consumes: `PageNode` (Contracts, Task 4); `DropZone`, `DropPlacement`, `dropZoneFor`, `resolvePageDrop` (Contracts, Task 5).
- Produces: the wired `onMove` on `PageTree`, plus `DRAG_PREFIX`, `DROP_PREFIX`, `pointerZone`, `shouldHoverExpand` and `resolveDrop` — see Contracts, `frontend/src/features/notes/page-tree.tsx`.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 0 - spec 1 - coupling 1 - risk 2 = 4
**Approach:** inline - skip 2: follows `document-tree.tsx`'s drag layer, with the three-zone resolver already settled in Task 5

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/notes/__tests__/page-tree-drag.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { PageListItem } from "@/hooks/api"
import { buildPageTree, pageNodeIndex } from "../lib/build-page-tree"
import {
  DRAG_PREFIX,
  DROP_PREFIX,
  PageTree,
  pointerZone,
  resolveDrop,
  shouldHoverExpand,
} from "../page-tree"

function row(id: string, parent_id: string | null, order_index: number): PageListItem {
  return {
    id,
    project: "personal",
    parent_id,
    order_index,
    title: id,
    content_hash: "h",
    properties: null,
    created_at: "2026-09-18T00:00:00Z",
    updated_at: "2026-09-18T00:00:00Z",
  }
}

const roots = buildPageTree([
  row("a", null, 0),
  row("b", "a", 0),
  row("d", null, 1),
])
const index = pageNodeIndex(roots)

// The expanded set is per-viewer storage shared across this file, so a case
// that seeds it would otherwise decide what the cases after it render.
beforeEach(() => {
  window.localStorage.clear()
})

describe("pointerZone", () => {
  it("reads the zone from the pointer's offset inside the row's own rect", () => {
    const rect = { top: 100, height: 30 } as { top: number; height: number }
    expect(pointerZone(rect, 102)).toBe("before")
    expect(pointerZone(rect, 115)).toBe("inside")
    expect(pointerZone(rect, 128)).toBe("after")
  })

  it("is inside when there is no rect to measure", () => {
    expect(pointerZone(null, 115)).toBe("inside")
  })
})

describe("resolveDrop", () => {
  it("strips the drag and drop prefixes before resolving", () => {
    expect(
      resolveDrop(roots, index, `${DRAG_PREFIX}d`, `${DROP_PREFIX}a`, "inside"),
    ).toEqual({ parentId: "a", afterId: "b" })
  })

  it("refuses when nothing is under the pointer", () => {
    expect(resolveDrop(roots, index, `${DRAG_PREFIX}d`, null, "inside")).toBeNull()
  })

  it("refuses a drop onto a descendant", () => {
    expect(
      resolveDrop(roots, index, `${DRAG_PREFIX}a`, `${DROP_PREFIX}b`, "after"),
    ).toBeNull()
  })
})

describe("PageTree drag layer", () => {
  it("mounts a drag handle on every rendered row", () => {
    render(
      <PageTree
        roots={roots}
        index={index}
        project="personal"
        selectedId={null}
        onSelect={vi.fn()}
        onNewChild={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
        onMove={vi.fn()}
      />,
    )
    // Two: the tree starts collapsed, so only the roots `a` and `d` render.
    expect(document.querySelectorAll("[data-drag-handle]")).toHaveLength(2)
    expect(screen.getByText("a")).toBeInTheDocument()
  })

  it("mounts a handle on a nested row too, once its parent is open", () => {
    window.localStorage.setItem(
      "darkmem:notes:expanded:personal",
      JSON.stringify(["a"]),
    )
    render(
      <PageTree
        roots={roots}
        index={index}
        project="personal"
        selectedId={null}
        onSelect={vi.fn()}
        onNewChild={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
        onMove={vi.fn()}
      />,
    )
    expect(document.querySelectorAll("[data-drag-handle]")).toHaveLength(3)
  })

})

// dnd-kit's pointer pipeline does not run under jsdom, so the hover-to-expand
// DECISION is a pure function and is tested here. The `setTimeout` that fires
// it is untested, and is stated as such rather than left to look covered.
describe("shouldHoverExpand", () => {
  it("opens a closed branch that has children", () => {
    expect(shouldHoverExpand(index, [], "a")).toBe(true)
  })

  it("leaves an already-open branch alone", () => {
    expect(shouldHoverExpand(index, ["a"], "a")).toBe(false)
  })

  it("does not arm on a leaf or an unknown id", () => {
    expect(shouldHoverExpand(index, [], "d")).toBe(false)
    expect(shouldHoverExpand(index, [], "missing")).toBe(false)
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run, from `frontend/`: `npx vitest run src/features/notes/__tests__/page-tree-drag.test.tsx`
Expected: FAIL — `page-tree` exports no `resolveDrop`, `pointerZone`, `shouldHoverExpand`, `DRAG_PREFIX` or `DROP_PREFIX`.

- [ ] **Step 3: Write the implementation**

Edit `frontend/src/features/notes/page-tree.tsx`. Add to its imports:

```tsx
import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react"
import {
  DndContext,
  MouseSensor,
  TouchSensor,
  getClientRect,
  pointerWithin,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type CollisionDetection,
  type DragEndEvent,
  type DragOverEvent,
} from "@dnd-kit/core"
import { dropZoneFor, resolvePageDrop, type DropPlacement, type DropZone } from "./lib/drop-target"
```

Add these module-level members above `PageTree`:

```tsx
export const DRAG_PREFIX = "drag:"
export const DROP_PREFIX = "drop:"

/** A droppable's hit area is the ROW, not the span the listeners hang off: a
 *  branch's element encloses its whole subtree, so its hit area would swallow
 *  every descendant row. */
const DROP_ROW_ATTR = "data-drop-row"

function measureDropRow(node: HTMLElement) {
  return getClientRect(node.closest<HTMLElement>(`[${DROP_ROW_ATTR}]`) ?? node)
}

const MEASURING = { droppable: { measure: measureDropRow } }

/** Mouse and touch are separate sensors. One `PointerSensor` needs
 *  `touch-action: none` on the handle, which covers most of every row and
 *  would disable native panning of the tree outright. */
const MOUSE_ACTIVATION = { activationConstraint: { distance: 6 } } as const
const TOUCH_ACTIVATION = {
  activationConstraint: { delay: 220, tolerance: 6 },
} as const

/** How long a collapsed row is hovered before it opens under the pointer. */
const HOVER_EXPAND_MS = 600

/** Whether hovering `pageId` should arm the expand timer. Separated from the
 *  timer because dnd-kit's pointer pipeline does not run under jsdom, so this
 *  is the half a unit test can reach; the timer itself is untested. */
export function shouldHoverExpand(
  index: Map<string, PageNode>,
  expanded: string[],
  pageId: string,
): boolean {
  const node = index.get(pageId)
  return Boolean(node) && node!.children.length > 0 && !expanded.includes(pageId)
}

export function pointerZone(
  rect: { top: number; height: number } | null,
  pointerY: number,
): DropZone {
  if (!rect) return "inside"
  return dropZoneFor(pointerY - rect.top, rect.height)
}

/** The whole drop decision, as a pure function of the tree, the two ids and
 *  the zone. Prefixed ids keep the drag and drop key spaces apart, which is
 *  what lets one element be both. */
export function resolveDrop(
  roots: PageNode[],
  index: Map<string, PageNode>,
  activeId: string,
  overId: string | null,
  zone: DropZone,
): DropPlacement | null {
  return resolvePageDrop(
    roots,
    index,
    activeId.slice(DRAG_PREFIX.length),
    overId === null ? null : overId.slice(DROP_PREFIX.length),
    zone,
  )
}

function RowHandle({
  node,
  zone,
  activeId,
  children,
}: {
  node: PageNode
  zone: DropZone | null
  activeId: string | null
  children: ReactNode
}) {
  const { setNodeRef: setDragRef, listeners, isDragging } = useDraggable({
    id: `${DRAG_PREFIX}${node.id}`,
  })
  const { setNodeRef: setDropRef, isOver } = useDroppable({
    id: `${DROP_PREFIX}${node.id}`,
  })
  // Stable across renders: an inline arrow re-registers the droppable and
  // re-runs its ResizeObserver on every one.
  const setRef = useCallback(
    (el: HTMLElement | null) => {
      setDragRef(el)
      setDropRef(el)
    },
    [setDragRef, setDropRef],
  )
  const showing = isOver && activeId !== null ? zone : null
  return (
    <span
      data-drag-handle
      data-drop-zone={showing ?? undefined}
      data-dragging={isDragging || undefined}
      ref={setRef}
      {...listeners}
      className="ring-primary border-primary flex min-w-0 flex-1 items-center gap-1.5 rounded-sm border-y border-transparent data-[dragging]:opacity-50 data-[drop-zone=after]:border-b-current data-[drop-zone=before]:border-t-current data-[drop-zone=inside]:ring-1"
    >
      {children}
    </span>
  )
}
```

Inside `PageTree`, replace `void index` / `void onMove` with the drag state and handlers:

```tsx
  const [activeId, setActiveId] = useState<string | null>(null)
  const [zone, setZone] = useState<DropZone | null>(null)
  const pointerY = useRef(0)
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const hoveredId = useRef<string | null>(null)

  const sensors = useSensors(
    // Without a distance every click is a zero-length drag and the row never
    // selects.
    useSensor(MouseSensor, MOUSE_ACTIVATION),
    useSensor(TouchSensor, TOUCH_ACTIVATION),
  )

  // The pointer's own position is what picks the zone, and the collision pass
  // is the only place dnd-kit hands it over.
  const collisionDetection = useCallback<CollisionDetection>((args) => {
    if (args.pointerCoordinates) pointerY.current = args.pointerCoordinates.y
    return pointerWithin(args)
  }, [])

  const cancelHover = useCallback(() => {
    if (hoverTimer.current) clearTimeout(hoverTimer.current)
    hoverTimer.current = null
    hoveredId.current = null
  }, [])

  useEffect(() => cancelHover, [cancelHover])

  const handleDragOver = useCallback(
    (event: DragOverEvent) => {
      const overId = event.over ? String(event.over.id) : null
      const next = pointerZone(event.over?.rect ?? null, pointerY.current)
      setZone(next)
      if (overId === null) {
        cancelHover()
        return
      }
      const pageId = overId.slice(DROP_PREFIX.length)
      if (hoveredId.current === pageId) return
      cancelHover()
      hoveredId.current = pageId
      if (!shouldHoverExpand(index, expanded, pageId)) return
      hoverTimer.current = setTimeout(
        () => handleExpandedChange([...expanded, pageId]),
        HOVER_EXPAND_MS,
      )
    },
    [cancelHover, expanded, handleExpandedChange, index],
  )

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      cancelHover()
      const activeKey = String(event.active.id)
      const placement = resolveDrop(
        roots,
        index,
        activeKey,
        event.over ? String(event.over.id) : null,
        pointerZone(event.over?.rect ?? null, pointerY.current),
      )
      setActiveId(null)
      setZone(null)
      if (placement) onMove(activeKey.slice(DRAG_PREFIX.length), placement)
    },
    [cancelHover, index, onMove, roots],
  )

  const handleDragCancel = useCallback(() => {
    cancelHover()
    setActiveId(null)
    setZone(null)
  }, [cancelHover])
```

Wrap each row's label in the handle and mark the row as the measured box. In
`renderNode`, the branch control becomes:

```tsx
          <TreeViewBranchControl
            data-drop-row=""
            className={`group relative ${ROW_GAP} ${ROW}`}
          >
            <TreeViewBranchIndicator className="text-muted-foreground shrink-0">
              <ChevronRight aria-hidden className="size-3.5" />
            </TreeViewBranchIndicator>
            <RowHandle node={node} zone={zone} activeId={activeId}>
              <TreeViewBranchText className="truncate">
                {titleOf(node)}
              </TreeViewBranchText>
            </RowHandle>
            {actions}
          </TreeViewBranchControl>
```

and the leaf becomes:

```tsx
      <TreeViewItem
        key={node.id}
        data-drop-row=""
        value={node.id}
        className={`group relative ${ROW_GAP} ${ROW}`}
      >
        <span aria-hidden className="w-[var(--icon-size)] shrink-0" />
        <RowHandle node={node} zone={zone} activeId={activeId}>
          <span className="truncate">{titleOf(node)}</span>
        </RowHandle>
        {actions}
      </TreeViewItem>
```

Finally wrap the returned `<TreeView>` in the context:

```tsx
  return (
    <DndContext
      sensors={sensors}
      measuring={MEASURING}
      collisionDetection={collisionDetection}
      onDragStart={(event) => setActiveId(String(event.active.id))}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <TreeView
        ...unchanged...
      </TreeView>
    </DndContext>
  )
```

`useDraggable().attributes` is deliberately never spread: `TreeViewItem` and
`TreeViewBranchControl` spread `...props` after `role="treeitem"`, the roving
`tabIndex` and the `aria-*` attributes, so the drag attributes would replace the
accessible tree and its arrow-key traversal.

- [ ] **Step 4: Run the tests and make sure they pass**

Run, from `frontend/`:
`npx vitest run src/features/notes/__tests__/page-tree-drag.test.tsx src/features/notes/__tests__/page-tree.test.tsx`
Expected: PASS — 10 tests in the drag file, and the Task 7 suite's 7 still green,
since the `DndContext` wraps the tree without changing what it renders.

Then `npm run typecheck`. Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/page-tree.tsx frontend/src/features/notes/__tests__/page-tree-drag.test.tsx
git commit -m "feat(notes): drag pages to reorder and renest"
```

---

### Task 9: The trash sheet

**Files:**
- Create: `frontend/src/features/notes/page-trash-sheet.tsx`
- Test: `frontend/src/features/notes/__tests__/page-trash-sheet.test.tsx` (create)

**Interfaces:**
- Consumes: `usePagesTrash`, `usePageRestore`, `usePageTrashEmpty`, `PageTrashItem` (Contracts, Tasks 2 and 3); `PAGE_TITLE_FALLBACK` (Contracts, Task 4).
- Produces: `PageTrashSheet` — see Contracts. Task 10 mounts it.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 0 - spec 0 - coupling 1 - risk 1 = 2
**Approach:** inline - skip 2: a darkraise-ui Sheet plus AlertDialog over hooks that already exist

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/notes/__tests__/page-trash-sheet.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { useState, type ReactNode } from "react"
import { describe, expect, it, vi, beforeEach } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
  return { apiFetch: vi.fn(), apiFetchWithHeaders: vi.fn(), ApiError }
})
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

import { toast } from "darkraise-ui/components/sonner"
import { apiFetch, ApiError } from "@/lib/api"
import { PageTrashSheet } from "../page-trash-sheet"

function wrapper({ children }: { children: ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      }),
  )
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const TRASH = [
  {
    id: "p1",
    title: "Gone",
    parent_id: null,
    deleted_at: new Date(Date.now() - 3600_000).toISOString(),
  },
  { id: "p2", title: null, parent_id: null, deleted_at: new Date().toISOString() },
]

function open(props: Partial<Parameters<typeof PageTrashSheet>[0]> = {}) {
  const onRestored = vi.fn()
  render(
    <PageTrashSheet
      project="personal"
      open
      onOpenChange={vi.fn()}
      onRestored={onRestored}
      {...props}
    />,
    { wrapper },
  )
  return { onRestored }
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(toast.error).mockReset()
})

describe("PageTrashSheet", () => {
  it("lists the trashed roots with a relative deletion time", async () => {
    vi.mocked(apiFetch).mockResolvedValue(TRASH)
    open()
    expect(await screen.findByText("Gone")).toBeInTheDocument()
    expect(screen.getByText("Untitled")).toBeInTheDocument()
    expect(screen.getByText(/ago/)).toBeInTheDocument()
  })

  it("restores a row and tells the workspace", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) =>
      path.endsWith("/restore")
        ? Promise.resolve({ restored: 1 })
        : Promise.resolve(TRASH),
    )
    const { onRestored } = open()
    fireEvent.click(await screen.findByRole("button", { name: "Restore Gone" }))
    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/pages/p1/restore", {
        method: "POST",
      }),
    )
    await waitFor(() => expect(onRestored).toHaveBeenCalled())
  })

  it("shows the server's own message when a restore is refused", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) =>
      path.endsWith("/restore")
        ? Promise.reject(new ApiError("the parent page is still trashed", 409))
        : Promise.resolve(TRASH),
    )
    open()
    fireEvent.click(await screen.findByRole("button", { name: "Restore Gone" }))
    await waitFor(() =>
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
        "the parent page is still trashed",
      ),
    )
  })

  it("empties the trash only behind the confirmation", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) =>
      path.includes("/trash/empty")
        ? Promise.resolve({ purged: 2 })
        : Promise.resolve(TRASH),
    )
    open()
    fireEvent.click(await screen.findByRole("button", { name: "Empty trash" }))
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalledWith(
      expect.stringContaining("/trash/empty"),
      expect.anything(),
    )
    fireEvent.click(await screen.findByRole("button", { name: "Delete permanently" }))
    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith(
        "/pages/trash/empty?project=personal",
        { method: "POST" },
      ),
    )
  })

  it("says the trash is empty rather than showing nothing", async () => {
    vi.mocked(apiFetch).mockResolvedValue([])
    open()
    expect(await screen.findByText(/Trash is empty/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run, from `frontend/`: `npx vitest run src/features/notes/__tests__/page-trash-sheet.test.tsx`
Expected: FAIL — cannot resolve `../page-trash-sheet`.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/features/notes/page-trash-sheet.tsx`:

```tsx
import { useState } from "react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "darkraise-ui/components/alert-dialog"
import { Button } from "darkraise-ui/components/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "darkraise-ui/components/sheet"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import { relativeTime } from "@/lib/format"
import { usePageRestore, usePageTrashEmpty, usePagesTrash } from "@/hooks/api"
import { PAGE_TITLE_FALLBACK } from "./lib/build-page-tree"

export function PageTrashSheet({
  project,
  open,
  onOpenChange,
  onRestored,
}: {
  project: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onRestored: () => void
}) {
  const trash = usePagesTrash(project, open)
  const restore = usePageRestore()
  const empty = usePageTrashEmpty()
  const [confirming, setConfirming] = useState(false)

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Trash</SheetTitle>
          <SheetDescription>
            The root of every trashed subtree. Restoring one brings its children
            back with it.
          </SheetDescription>
        </SheetHeader>

        {trash.isLoading ? <Skeleton className="h-24 w-full" /> : null}
        {trash.isError ? (
          <p className="text-destructive text-sm">
            The trash could not be read — a failed read, not an empty trash.
          </p>
        ) : null}
        {trash.isSuccess && trash.data.length === 0 ? (
          <p className="text-muted-foreground text-sm">Trash is empty.</p>
        ) : null}

        <ul className="space-y-1">
          {(trash.data ?? []).map((item) => {
            const label = item.title?.trim() ? item.title : PAGE_TITLE_FALLBACK
            return (
              <li
                key={item.id}
                className="flex items-center justify-between gap-3 rounded px-1 py-1.5"
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm">{label}</span>
                  <span className="text-muted-foreground text-xs">
                    {relativeTime(item.deleted_at)}
                  </span>
                </span>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  aria-label={`Restore ${label}`}
                  onClick={() =>
                    restore.mutate(item.id, {
                      onSuccess: () => onRestored(),
                      // The server's own message, because the only refusal
                      // here -- a still-trashed parent -- names the page the
                      // operator has to restore first.
                      onError: (error) => toast.error(String(error.message)),
                    })
                  }
                >
                  Restore
                </Button>
              </li>
            )
          })}
        </ul>

        <div className="pt-2">
          <Button
            type="button"
            variant="outline"
            disabled={(trash.data ?? []).length === 0}
            onClick={() => setConfirming(true)}
          >
            Empty trash
          </Button>
        </div>

        <AlertDialog open={confirming} onOpenChange={setConfirming}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Empty the trash?</AlertDialogTitle>
              <AlertDialogDescription>
                This deletes every trashed page and its blocks for good. It
                cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={() =>
                  empty.mutate(project, {
                    onError: (error) => toast.error(String(error.message)),
                  })
                }
              >
                Delete permanently
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </SheetContent>
    </Sheet>
  )
}
```

`relativeTime` is the repo's existing helper (`frontend/src/lib/format.ts:23`),
answering `just now` / `Nm ago` / `Nh ago` / `Nd ago`.

- [ ] **Step 4: Run the test to verify it passes**

Run, from `frontend/`: `npx vitest run src/features/notes/__tests__/page-trash-sheet.test.tsx`
Expected: PASS, 5 tests.

Then `npm run typecheck`. Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/page-trash-sheet.tsx frontend/src/features/notes/__tests__/page-trash-sheet.test.tsx
git commit -m "feat(notes): add the page trash sheet"
```

---

### Task 10: `NotesWorkspace` and the `/notes` route

**Files:**
- Create: `frontend/src/features/notes/notes-workspace.tsx`
- Modify: `frontend/src/routes/_authenticated/notes.tsx` (whole file)
- Modify: `frontend/src/routes/_authenticated/__tests__/notes.test.tsx`
- Test: `frontend/src/features/notes/__tests__/notes-workspace.test.tsx` (create)
- Test: `frontend/src/features/notes/__tests__/notes-workspace-move.test.tsx` (create)

**Interfaces:**
- Consumes: `usePages`, `usePage`, `usePageCreate`, `usePageDelete`, `usePageRestore`, `usePageMove`, `usePageRename` (Contracts, Tasks 2 and 3); `buildPageTree`, `pageNodeIndex`, `PAGE_TITLE_FALLBACK` (Task 4); `DropPlacement`, `applyPlacement` (Task 5); `PagePane` (Task 6); `PageTree` (Tasks 7 and 8); `PageTrashSheet` (Task 9).
- Produces: `NotesWorkspace` and the route's `{ page?: string }` search — see Contracts.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4
**Approach:** inline - skip 2: composes components whose interfaces the earlier tasks fixed; the only open call is error copy, which spec §6 states

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/features/notes/__tests__/notes-workspace.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { useState, type ReactNode } from "react"
import { describe, expect, it, vi, beforeEach } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
  return { apiFetch: vi.fn(), apiFetchWithHeaders: vi.fn(), ApiError }
})
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))
// The pane is exercised by its own suite; here it stands in so the assertions
// are about what the workspace hands it.
vi.mock("../page-pane", () => ({
  PagePane: ({ page }: { page: { id: string } }) => <div>pane:{page.id}</div>,
}))

import { toast } from "darkraise-ui/components/sonner"
import { apiFetch, ApiError } from "@/lib/api"
import { NotesWorkspace } from "../notes-workspace"

function wrapper({ children }: { children: ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      }),
  )
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const LIST = [
  {
    id: "p1",
    project: "personal",
    parent_id: null,
    order_index: 0,
    title: "Alpha",
    content_hash: "h",
    properties: null,
    created_at: "2026-09-18T00:00:00Z",
    updated_at: "2026-09-18T00:00:00Z",
  },
]
const PAGE = {
  id: "p1",
  project: "personal",
  parent_id: null,
  order_index: 0,
  title: "Alpha",
  content_hash: "h",
  properties: null,
  content: null,
  blocks: [],
}

function route(path: string) {
  if (path.startsWith("/pages/trash")) return Promise.resolve([])
  if (path.startsWith("/pages?")) return Promise.resolve(LIST)
  if (path === "/pages/p1") return Promise.resolve(PAGE)
  return Promise.resolve({})
}

function renderWorkspace(props: Partial<Parameters<typeof NotesWorkspace>[0]> = {}) {
  const onSelect = vi.fn()
  render(
    <NotesWorkspace
      project="personal"
      selectedId={null}
      onSelect={onSelect}
      {...props}
    />,
    { wrapper },
  )
  return { onSelect }
}

beforeEach(() => {
  window.localStorage.clear()
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetch).mockImplementation(route as never)
  vi.mocked(toast.error).mockReset()
  vi.mocked(toast.success).mockReset()
})

describe("NotesWorkspace", () => {
  it("renders the tree and the empty pane with nothing selected", async () => {
    renderWorkspace()
    expect(await screen.findByText("Alpha")).toBeInTheDocument()
    expect(screen.getByText(/Pick a page/)).toBeInTheDocument()
  })

  it("renders the pane for the selected page", async () => {
    renderWorkspace({ selectedId: "p1" })
    expect(await screen.findByText("pane:p1")).toBeInTheDocument()
  })

  // A 404 means the selection no longer exists -- trashed or purged, the
  // server does not distinguish -- which is a state, not a fault.
  it("clears the selection on a 404 and shows the empty pane", async () => {
    vi.mocked(apiFetch).mockImplementation(((path: string) =>
      path === "/pages/p1"
        ? Promise.reject(new ApiError("no page p1", 404))
        : route(path)) as never)
    const { onSelect } = renderWorkspace({ selectedId: "p1" })
    await waitFor(() => expect(onSelect).toHaveBeenCalledWith(null))
  })

  it("shows an error, never the empty pane, when the page read fails otherwise", async () => {
    vi.mocked(apiFetch).mockImplementation(((path: string) =>
      path === "/pages/p1"
        ? Promise.reject(new ApiError("boom", 500))
        : route(path)) as never)
    const { onSelect } = renderWorkspace({ selectedId: "p1" })
    expect(await screen.findByText(/could not be loaded/)).toBeInTheDocument()
    expect(screen.queryByText(/Pick a page/)).toBeNull()
    expect(onSelect).not.toHaveBeenCalled()
  })

  it("creates a root page and selects it", async () => {
    vi.mocked(apiFetch).mockImplementation(((path: string, init?: RequestInit) =>
      path === "/pages" && init?.method === "POST"
        ? Promise.resolve({ id: "p9" })
        : route(path)) as never)
    const { onSelect } = renderWorkspace()
    fireEvent.click(await screen.findByRole("button", { name: "New page" }))
    await waitFor(() => expect(onSelect).toHaveBeenCalledWith("p9"))
  })

  it("trashes a page and offers an undo that restores it", async () => {
    vi.mocked(apiFetch).mockImplementation(((path: string, init?: RequestInit) => {
      if (path === "/pages/p1" && init?.method === "DELETE") return Promise.resolve()
      if (path === "/pages/p1/restore") return Promise.resolve({ restored: 1 })
      return route(path)
    }) as never)
    renderWorkspace()
    fireEvent.click(await screen.findByRole("button", { name: "Actions for Alpha" }))
    fireEvent.click(screen.getByText("Delete"))
    await waitFor(() => expect(vi.mocked(toast.success)).toHaveBeenCalled())
    const [, options] = vi.mocked(toast.success).mock.calls[0]!
    options!.action!.onClick()
    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/pages/p1/restore", {
        method: "POST",
      }),
    )
  })

  it("opens the trash sheet from the sidebar foot", async () => {
    renderWorkspace()
    fireEvent.click(await screen.findByRole("button", { name: "Trash" }))
    expect(await screen.findByText(/Trash is empty/)).toBeInTheDocument()
  })
})
```

The move handler gets its own file, `frontend/src/features/notes/__tests__/notes-workspace-move.test.tsx`,
because it needs the tree stubbed from the top of the file: swapping a mock
mid-file would mean `vi.resetModules()` plus a dynamic re-import, which
re-evaluates every `vi.mock` factory and leaves the statically-imported `apiFetch`
and `toast` spies attached to objects the re-imported component never touches.
It drives the handler through the stub rather than faking a drag — the drop
resolution is already proven in `drop-target`'s suite, and dnd-kit needs a
pointer pipeline jsdom does not provide.

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi, beforeEach } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
  return { apiFetch: vi.fn(), apiFetchWithHeaders: vi.fn(), ApiError }
})
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))
vi.mock("../page-pane", () => ({ PagePane: () => <div>pane</div> }))
// The tree's own suites cover its rows and its drag layer; here it is the one
// thing that must not be real, so the move handler can be driven directly.
vi.mock("../page-tree", () => ({
  notesExpansionStorageKey: (project: string) => `k:${project}`,
  PageTree: ({
    onMove,
  }: {
    onMove: (
      id: string,
      placement: { parentId: string | null; afterId: string | null },
    ) => void
  }) => (
    <button
      type="button"
      onClick={() => onMove("p2", { parentId: "p1", afterId: null })}
    >
      drop
    </button>
  ),
}))

import { toast } from "darkraise-ui/components/sonner"
import { apiFetch, ApiError } from "@/lib/api"
import type { PageListItem } from "@/hooks/api"
import { NotesWorkspace } from "../notes-workspace"

function row(id: string, order_index: number): PageListItem {
  return {
    id,
    project: "personal",
    parent_id: null,
    order_index,
    title: id,
    content_hash: "h",
    properties: null,
    created_at: "2026-09-18T00:00:00Z",
    updated_at: "2026-09-18T00:00:00Z",
  }
}
const LIST = [row("p1", 0), row("p2", 1)]

function parentOf(qc: QueryClient, id: string) {
  return qc
    .getQueryData<PageListItem[]>(["pages", "personal"])!
    .find((r) => r.id === id)!.parent_id
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(toast.error).mockReset()
})

describe("NotesWorkspace move", () => {
  it("shows the move before the server answers, then rolls it back on refusal", async () => {
    // The list read fails after its first success, so the hook's own
    // invalidation cannot refetch the server's copy over the rollback and
    // pass this test for the wrong reason.
    let listCalls = 0
    let refuse: (reason: unknown) => void = () => {}
    vi.mocked(apiFetch).mockImplementation(((path: string, init?: RequestInit) => {
      if (path === "/pages/p2" && init?.method === "PATCH") {
        return new Promise((_resolve, reject) => {
          refuse = reject
        })
      }
      if (path.startsWith("/pages?")) {
        listCalls += 1
        return listCalls === 1
          ? Promise.resolve(LIST)
          : Promise.reject(new ApiError("unavailable", 503))
      }
      if (path.startsWith("/pages/trash")) return Promise.resolve([])
      return Promise.resolve({})
    }) as never)

    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    render(
      <QueryClientProvider client={qc}>
        <NotesWorkspace project="personal" selectedId={null} onSelect={vi.fn()} />
      </QueryClientProvider>,
    )
    await waitFor(() => expect(parentOf(qc, "p2")).toBeNull())

    fireEvent.click(screen.getByText("drop"))
    await waitFor(() => expect(parentOf(qc, "p2")).toBe("p1"))

    refuse(new ApiError("a page cannot be its own ancestor", 422))
    await waitFor(() => expect(parentOf(qc, "p2")).toBeNull())
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      "a page cannot be its own ancestor",
    )
  })

  it("keeps the optimistic move when the server accepts it", async () => {
    let listCalls = 0
    vi.mocked(apiFetch).mockImplementation(((path: string, init?: RequestInit) => {
      if (path === "/pages/p2" && init?.method === "PATCH") {
        return Promise.resolve({ id: "p2" })
      }
      if (path.startsWith("/pages?")) {
        listCalls += 1
        return listCalls === 1
          ? Promise.resolve(LIST)
          : Promise.reject(new ApiError("unavailable", 503))
      }
      if (path.startsWith("/pages/trash")) return Promise.resolve([])
      return Promise.resolve({})
    }) as never)

    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    render(
      <QueryClientProvider client={qc}>
        <NotesWorkspace project="personal" selectedId={null} onSelect={vi.fn()} />
      </QueryClientProvider>,
    )
    await waitFor(() => expect(parentOf(qc, "p2")).toBeNull())
    fireEvent.click(screen.getByText("drop"))
    await waitFor(() => expect(parentOf(qc, "p2")).toBe("p1"))
    expect(vi.mocked(toast.error)).not.toHaveBeenCalled()
  })
})
```

Then rewrite `frontend/src/routes/_authenticated/__tests__/notes.test.tsx`'s
workspace mock and its assertions. Replace the `vi.mock` of
`@/features/documents/components/project-workspace` (lines 18-30) with:

```tsx
vi.mock("@/features/notes/notes-workspace", () => ({
  NotesWorkspace: ({
    project,
    selectedId,
  }: {
    project: string
    selectedId: string | null
  }) => (
    <div data-testid="notes-project" data-selected={selectedId ?? ""}>
      {project}
    </div>
  ),
}))
```

and change every `findByTestId("workspace-project")` assertion to
`findByTestId("notes-project")`, dropping the `data-tree-management` assertion.
Add these two cases:

```tsx
  // `await findByTestId`, as every other case in this file does: `NotesPage`
  // renders a Skeleton while `useProjects()` is pending, so nothing with this
  // id exists on the synchronous first render.
  it("passes the page id from the search param through to the workspace", async () => {
    vi.mocked(apiFetch).mockResolvedValue([row("personal-space", "personal")])
    renderRoute({ page: "p7" })
    expect(await screen.findByTestId("notes-project")).toHaveAttribute(
      "data-selected",
      "p7",
    )
  })

  it("keeps only a non-empty string page param", () => {
    const validate = (Route.options ?? Route).validateSearch as (
      s: Record<string, unknown>,
    ) => { page?: string }
    expect(validate({ page: "p7" })).toEqual({ page: "p7" })
    expect(validate({ page: "" })).toEqual({ page: undefined })
    expect(validate({ page: 7 })).toEqual({ page: undefined })
    expect(validate({})).toEqual({ page: undefined })
  })
```

`renderRoute` takes the search now, so update its helper (line ~43) to:

```tsx
function renderRoute(search: { page?: string } = {}) {
  const Component = (Route.options ?? Route).component as ComponentType
  routerMocks.useSearch.mockReturnValue(search)
  render(<Component />, { wrapper })
}
```

and extend the `@tanstack/react-router` mock to serve `useSearch` and
`useNavigate`. The two spies go through `vi.hoisted`, not a bare `const`: the
mock factory is hoisted above every import, so a `const` declared at module
scope would still be in its temporal dead zone when the factory runs. This is
the form `components/darkmem/__tests__/detail-level-placement.test.tsx:13`
already uses.

```tsx
const routerMocks = vi.hoisted(() => ({
  useSearch: vi.fn((): { page?: string } => ({})),
  navigate: vi.fn(),
}))
vi.mock("@tanstack/react-router", async () => {
  const actual = await vi.importActual<Record<string, unknown>>(
    "@tanstack/react-router",
  )
  return {
    ...actual,
    createFileRoute: () => (opts: Record<string, unknown>) => opts,
    useSearch: () => routerMocks.useSearch(),
    useNavigate: () => routerMocks.navigate,
    Link: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  }
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run, from `frontend/`:
`npx vitest run src/features/notes/__tests__/notes-workspace.test.tsx src/routes/_authenticated/__tests__/notes.test.tsx`
Expected: FAIL — `../notes-workspace` does not resolve, and the route serves no `page` search.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/features/notes/notes-workspace.tsx`:

```tsx
import { useCallback, useEffect, useMemo, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { Plus, Trash2 } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "darkraise-ui/components/resizable"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import { ApiError } from "@/lib/api"
import { EmptyState } from "@/components/darkmem"
import {
  usePage,
  usePageCreate,
  usePageDelete,
  usePageMove,
  usePageRename,
  usePageRestore,
  usePages,
  type PageListItem,
} from "@/hooks/api"
import {
  buildPageTree,
  pageNodeIndex,
  PAGE_TITLE_FALLBACK,
  type PageNode,
} from "./lib/build-page-tree"
import { applyPlacement, type DropPlacement } from "./lib/drop-target"
import { PagePane } from "./page-pane"
import { PageTree } from "./page-tree"
import { PageTrashSheet } from "./page-trash-sheet"

const NOT_FOUND = 404

function labelOf(node: PageNode): string {
  return node.title?.trim() ? node.title : PAGE_TITLE_FALLBACK
}

export function NotesWorkspace({
  project,
  selectedId,
  onSelect,
}: {
  project: string
  selectedId: string | null
  onSelect: (pageId: string | null) => void
}) {
  const list = usePages(project)
  const page = usePage(selectedId)
  const qc = useQueryClient()
  const create = usePageCreate()
  const rename = usePageRename()
  const remove = usePageDelete()
  const restore = usePageRestore()
  const move = usePageMove()

  const roots = useMemo(() => buildPageTree(list.data ?? []), [list.data])
  const index = useMemo(() => pageNodeIndex(roots), [roots])

  const [trashOpen, setTrashOpen] = useState(false)
  const [focusTitle, setFocusTitle] = useState(false)
  const [renameTarget, setRenameTarget] = useState<PageNode | null>(null)
  const [renameValue, setRenameValue] = useState("")

  // A 404 says the selection no longer exists -- trashed or purged elsewhere,
  // which the server does not distinguish. Every other failure is a fault and
  // renders as one.
  const vanished =
    page.isError && page.error instanceof ApiError && page.error.status === NOT_FOUND
  useEffect(() => {
    if (vanished) onSelect(null)
  }, [onSelect, vanished])

  const refuse = useCallback(
    (error: unknown) =>
      toast.error(error instanceof Error ? error.message : String(error)),
    [],
  )

  const createPage = useCallback(
    (parentId: string | null) => {
      create.mutate(
        { project, parentId },
        {
          onSuccess: ({ id }) => {
            onSelect(id)
            setFocusTitle(true)
          },
          onError: refuse,
        },
      )
    },
    [create, onSelect, project, refuse],
  )

  const deletePage = useCallback(
    (node: PageNode) => {
      const label = labelOf(node)
      remove.mutate(node.id, {
        onSuccess: () => {
          if (selectedId === node.id) onSelect(null)
          toast.success(`${label} moved to trash`, {
            action: {
              label: "Undo",
              onClick: () => restore.mutate(node.id, { onError: refuse }),
            },
          })
        },
        onError: refuse,
      })
    },
    [onSelect, refuse, remove, restore, selectedId],
  )

  // Optimistic, with the snapshot rolled back on refusal: a drag that waited
  // for the round trip would snap the row back under the pointer. The hook's
  // own `onSettled` invalidation is what reconciles either outcome.
  const movePage = useCallback(
    (pageId: string, placement: DropPlacement) => {
      const key = ["pages", project]
      const snapshot = qc.getQueryData<PageListItem[]>(key)
      if (snapshot) {
        qc.setQueryData(key, applyPlacement(snapshot, pageId, placement))
      }
      move.mutate(
        { pageId, parentId: placement.parentId, afterId: placement.afterId },
        {
          onError: (error) => {
            if (snapshot) qc.setQueryData(key, snapshot)
            refuse(error)
          },
        },
      )
    },
    [move, project, qc, refuse],
  )

  const commitRename = useCallback(() => {
    if (!renameTarget) return
    const next = renameValue.trim()
    rename.mutate(
      { pageId: renameTarget.id, title: next === "" ? null : next },
      { onError: refuse },
    )
    setRenameTarget(null)
  }, [refuse, rename, renameTarget, renameValue])

  return (
    <ResizablePanelGroup
      orientation="horizontal"
      className="min-h-[60vh] lg:min-h-0 lg:flex-1"
    >
      <ResizablePanel defaultSize={26} minSize={15} maxSize={45} id="page-tree">
        <div className="flex h-full min-h-0 flex-col">
          <div className="mb-1.5 flex items-center justify-end">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => createPage(null)}
            >
              <Plus className="mr-1 size-3.5" />
              New page
            </Button>
          </div>
          <ScrollArea className="min-h-0 flex-1 pr-3">
            {list.isLoading ? <Skeleton className="h-64 w-full" /> : null}
            {list.isError ? (
              <p className="text-destructive text-sm">
                The page tree could not be loaded — a failed read, not an empty
                space.
              </p>
            ) : null}
            {list.isSuccess ? (
              <PageTree
                roots={roots}
                index={index}
                project={project}
                selectedId={selectedId}
                onSelect={(id) => {
                  setFocusTitle(false)
                  onSelect(id)
                }}
                onNewChild={createPage}
                onRename={(node) => {
                  setRenameTarget(node)
                  setRenameValue(node.title ?? "")
                }}
                onDelete={deletePage}
                onMove={movePage}
              />
            ) : null}
          </ScrollArea>
          <div className="pt-2">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => setTrashOpen(true)}
            >
              <Trash2 className="mr-1 size-3.5" />
              Trash
            </Button>
          </div>
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      <ResizablePanel defaultSize={74} id="page-pane">
        <div className="h-full min-h-0 pl-3">
          {selectedId === null || vanished ? (
            <EmptyState
              kind="empty"
              icon={Plus}
              title="Nothing selected"
              description="Pick a page from the tree, or start a new one."
            />
          ) : page.isError ? (
            <p className="text-destructive text-sm">
              This page could not be loaded — a failed read, not an empty page.
            </p>
          ) : page.isLoading || !page.data ? (
            <Skeleton className="h-64 w-full" />
          ) : (
            <PagePane page={page.data} autoFocusTitle={focusTitle} />
          )}
        </div>
      </ResizablePanel>

      <PageTrashSheet
        project={project}
        open={trashOpen}
        onOpenChange={setTrashOpen}
        onRestored={() => setTrashOpen(false)}
      />

      <Dialog
        open={renameTarget !== null}
        onOpenChange={(open) => {
          if (!open) setRenameTarget(null)
        }}
      >
        <DialogContent>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              commitRename()
            }}
          >
            <DialogHeader>
              <DialogTitle>
                Rename {renameTarget ? labelOf(renameTarget) : ""}
              </DialogTitle>
            </DialogHeader>
            <Label htmlFor="page-rename" className="sr-only">
              New title
            </Label>
            <Input
              id="page-rename"
              autoFocus
              aria-label="New title"
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
            />
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setRenameTarget(null)}
              >
                Cancel
              </Button>
              <Button type="submit">Rename</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </ResizablePanelGroup>
  )
}
```

Replace `frontend/src/routes/_authenticated/notes.tsx` entirely with:

```tsx
import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router"
import { NotebookPen } from "lucide-react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import { EmptyState } from "@/components/darkmem"
import { NotesWorkspace } from "@/features/notes/notes-workspace"
import { useProjects } from "@/hooks/api"

export const Route = createFileRoute("/_authenticated/notes")({
  validateSearch: (search: Record<string, unknown>) => ({
    page:
      typeof search.page === "string" && search.page.length > 0
        ? search.page
        : undefined,
  }),
  component: NotesPage,
})

function NotesPage() {
  const { data, isLoading, isError } = useProjects()
  // The standalone hook rather than `Route.useSearch()`: the route test
  // replaces `createFileRoute` with a passthrough, so the route object it gets
  // back carries no methods.
  const { page } = useSearch({ from: "/_authenticated/notes" })
  const navigate = useNavigate()
  // Resolved from the catalogue, never hardcoded: `ux_projects_one_personal`
  // guarantees at most one row of this kind, so following `kind` keeps this
  // route correct if the seeded name ever changes.
  const personal = data?.find((p) => p.kind === "personal")

  return (
    <div className="flex flex-col gap-4 lg:h-full lg:min-h-0">
      <PageChrome
        icon={NotebookPen}
        title="Notes"
        description="Your personal workspace. Nothing here is a project artifact."
      />

      {isError ? (
        // Never the empty state: "there is no personal space" is a claim
        // about the catalogue, and on a failed read it is an unfounded one.
        <p className="text-destructive text-sm">
          Notes could not be loaded — a failed read, not an empty space.
        </p>
      ) : isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : !personal ? (
        <EmptyState
          kind="empty"
          icon={NotebookPen}
          title="No personal space yet"
          description="The notes workspace appears here once the personal project exists."
        />
      ) : (
        <NotesWorkspace
          key={personal.name}
          project={personal.name}
          selectedId={page ?? null}
          onSelect={(id) =>
            // Merged rather than replaced, so a later param on this route is
            // not cleared by a selection.
            navigate({
              to: ".",
              search: (prev) => ({ ...prev, page: id ?? undefined }),
            })
          }
        />
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run, from `frontend/`:
`npx vitest run src/features/notes src/routes/_authenticated/__tests__/notes.test.tsx`
Expected: PASS, every file under `src/features/notes` plus the route suite.

Then `npm run typecheck`. Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/notes-workspace.tsx frontend/src/routes/_authenticated/notes.tsx frontend/src/features/notes/__tests__/notes-workspace.test.tsx frontend/src/features/notes/__tests__/notes-workspace-move.test.tsx frontend/src/routes/_authenticated/__tests__/notes.test.tsx
git commit -m "feat(notes): point /notes at the page workspace"
```

---

### Task 11: Return `ProjectWorkspace` to the corpus browser

**Files:**
- Modify: `frontend/src/features/documents/components/project-workspace.tsx` (the `treeManagement` prop at `:184-198`, `freeUri` at `:91-101`, and the nine branches at `:228`, `:546-564`, `:603`, `:686`, `:735`, `:736`, `:825`, `:980`)
- Delete: `frontend/src/features/documents/components/note-tree-actions.tsx`
- Delete: `frontend/src/features/documents/__tests__/note-tree-actions.test.tsx`
- Modify: `frontend/src/features/documents/__tests__/project-workspace.test.tsx`
- Modify: `frontend/src/features/documents/__tests__/project-workspace-move.test.tsx`
- Modify: `frontend/src/features/documents/__tests__/project-workspace-memo.test.tsx`
- Modify: `frontend/src/features/documents/__tests__/project-workspace-render.test.tsx`

**Interfaces:**
- Consumes: nothing. This task runs **after** Task 10, because until `/notes` renders `NotesWorkspace` it is `ProjectWorkspace`'s only `treeManagement` caller.
- Produces: `ProjectWorkspace`'s narrowed signature — `{ project, tab, onTabChange }`, with `treeManagement` gone.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 1: a deletion with no design choice, every site enumerated in Assumptions

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/features/documents/__tests__/project-workspace.test.tsx`, in
its own `describe` at the end:

```tsx
describe("the corpus browser carries no tree management", () => {
  // `Function.length` cannot see this: the prop is a default inside one
  // destructured parameter, so it is 1 either way. The source is the only
  // observable that distinguishes a removed prop from a defaulted one.
  it("names treeManagement nowhere in its body", () => {
    expect(ProjectWorkspace.toString()).not.toContain("treeManagement")
  })

  it("renders the tab strip and the documents label", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [], total: 0 })
    renderWorkspace()
    expect(await screen.findByRole("tab", { name: /Artifacts/i })).toBeInTheDocument()
    expect(screen.getByText("documents")).toBeInTheDocument()
  })

  it("offers no per-row actions and no create buttons", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [], total: 0 })
    renderWorkspace()
    await screen.findByRole("tab", { name: /Artifacts/i })
    expect(screen.queryByText("New note")).toBeNull()
    expect(screen.queryByText("New folder")).toBeNull()
    expect(screen.queryByRole("button", { name: /^Actions for/ })).toBeNull()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run, from `frontend/`:
`npx vitest run src/features/documents/__tests__/project-workspace.test.tsx`
Expected: FAIL on the first new case — the source still contains
`treeManagement`. The other two new cases pass already, because the prop
defaults to `false`; they are the regression net for the deletion, not its
driver.

- [ ] **Step 3: Write the implementation**

In `frontend/src/features/documents/components/project-workspace.tsx`, make these
deletions. Nothing is added.

1. **The prop** (`:184-198`): drop `treeManagement = false` from the destructuring
   and `treeManagement?: boolean` with its doc comment from the type, leaving:

   ```tsx
   export function ProjectWorkspace({
     project,
     tab,
     onTabChange,
   }: {
     project: string
     tab: WorkspaceTab
     onTabChange: (tab: WorkspaceTab) => void
   }) {
   ```

2. **`freeUri`** (`:91-101`): delete the function outright. Its only caller is
   `handleNewNote`, which goes in step 5.

3. **The progress corpus** (`:228`): `useProgressCorpus(treeManagement ? NO_DOCUMENTS : items)`
   becomes `useProgressCorpus(items)`. `NO_DOCUMENTS` (`:93`) then has no reader
   and is deleted too.

4. **`emptyAction`** (`:546-564`): delete the whole `useMemo` and pass nothing for
   `emptyAction` at the `DocumentTree` call site.

5. **The create and management handlers and their state**: delete `handleNewNote`
   (`:331`), `handleTogglePin` (`:363`), `handleMove` (`:382`),
   `handleOpenNewFolder` (`:402`), `handleOpenMove` (`:407`), `commitNewFolder`
   (`:436`), `commitMove` (`:454`), `handleOpenRename` (`:460`), `commitRename`
   (`:465`), `commitDelete` (`:509`), `nodeActions` (`:567`), the derived
   `byPath` (`:412`) and `moveOptions` (`:420`), and the state at `:316-323`
   (`renameTarget`, `renameValue`, `deleteTarget`, `newFolderParent`,
   `newFolderValue`, `moveSource`, `moveValue`). Delete the four dialogs they
   drive — Rename (`:833`), New folder (`:874`), Move (`:915`) and the Delete
   `AlertDialog` (`:956`) — which are rendered unconditionally today and can be
   opened by nothing once the handlers are gone. Delete the mutation hooks that
   then have no caller: `useDocumentCreate`, `useDocumentMetadataUpdate`,
   `useDocumentSubtreeRename`, `useDocumentSubtreeDelete`, `useDocumentDelete`
   (`:310-314`), and the `reportNothingMatched` (`:125`), `parentPath` (`:129`)
   and `underPrefix` (`:137`) helpers if nothing else reads them.

Every line number above is from a `grep -n` over the file on 2026-09-18; each
symbol is also named, so navigate by name if an earlier deletion in the same
pass has shifted them.

6. **The tab strip** (`:603`): `{treeManagement ? null : (<TabsList>…)}` becomes the
   `<TabsList>…</TabsList>` alone.

7. **The tree pane header** (`:686`): keep the `<RegionLabel>documents</RegionLabel>`
   branch and delete the `treeManagement` branch with its two ghost buttons.

8. **The `DocumentTree` call site** (`:735-736`): delete the `nodeActions` and
   `onMove` props entirely, and the `emptyAction` prop from step 4.

9. **The empty-reader description** (`:825`): the ternary becomes the literal
   `"Pick a document from the tree to read it."`.

10. **The progress tab** (`:980`): `{treeManagement ? null : (<TabsContent value="progress">…)}`
    becomes the `<TabsContent>…</TabsContent>` alone.

Then delete the imports the removals orphan — at minimum `NoteTreeActions`,
`moveTarget` / `MoveTarget`, `buildPathMap`, `NO_PATH`, `FolderPlus`, `Plus`,
`Dialog*`, `AlertDialog*`, `Label`, `Input`, `Select*`, `toast`, and the five
mutation hooks — and delete the two files:

```
frontend/src/features/documents/components/note-tree-actions.tsx
frontend/src/features/documents/__tests__/note-tree-actions.test.tsx
```

`buildUriTree`, `type UriTreeNode`, `expansionStorageKey`, `pathsToDocument` and
`rootFolderPaths` stay — the corpus browser's own expansion and tree building
are not behind `treeManagement`.

Finally, update the three other workspace suites. In each, delete every render
that passes `treeManagement` and every assertion about a create button, a row
action menu, a dialog or a drag layer; keep the corpus-browser assertions
unchanged. `project-workspace-move.test.tsx` covered `handleMove`, which no
longer exists — delete that file if nothing in it survives the removal.
`project-workspace-render.test.tsx` counts `DocumentTree`'s renders: removing
props from its call site may change the count, and the assertion is updated to
the number the run reports, never loosened.

- [ ] **Step 4: Run the tests and make sure they pass**

Run, from `frontend/`:
`npx vitest run src/features/documents src/routes/_authenticated/__tests__/notes.test.tsx src/features/notes`
Expected: PASS. `documents.real.test.tsx` and the `document-tree` suites must be
green untouched — they are the proof `/documents` and `/projects/$project` did
not move.

Then `npm run typecheck`. Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add -A frontend/src/features/documents
git commit -m "refactor(documents): drop notes-only workspace branches"
```

---

### Task 12: Carried items, docs and the frontend leg

**Files:**
- Modify: `frontend/src/components/app-chrome/project-switcher.tsx:34-40`
- Modify: `frontend/src/components/app-chrome/__tests__/project-switcher.test.tsx`
- Modify: `frontend/src/routes/_authenticated.tsx:155-165` (the `FULL_WIDTH_ROUTES` comment)
- Modify: `CLAUDE.md` (the Documents section's Pages paragraph)

**Interfaces:**
- Consumes: nothing.
- Produces: nothing. This is the increment's closing task.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 0 = 2
**Approach:** inline - skip 2: two one-line edits plus prose, with the exact text below

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/components/app-chrome/__tests__/project-switcher.test.tsx`:

```tsx
  it("counts pages in a project's item total", async () => {
    mockUseProjects.mockReturnValue({
      data: [
        {
          name: "darkmem",
          kind: "project" as const,
          memory_count: 1,
          document_count: 2,
          checkpoint_count: 3,
          page_count: 4,
          last_checkpoint_at: null,
          last_event_day: null,
        },
      ],
      isLoading: false,
    })
    const user = userEvent.setup()
    renderSwitcher()

    await user.click(screen.getByRole("button", { name: /project scope/i }))

    // 1 + 2 + 3 + 4. Under the three-corpus total it read "6 items".
    expect(
      await screen.findByRole("button", { name: /darkmem.*10 items/ }),
    ).toBeInTheDocument()
  })
```

That file's `renderSwitcher()` takes no arguments — rows come from
`mockUseProjects.mockReturnValue({ data, isLoading: false })` — and every row
lives inside a `PopoverContent`, so the trigger has to be clicked first. Both
shapes are copied from the existing item-count case at
`project-switcher.test.tsx:112-128`. That case stays green unchanged: its rows
already carry `page_count: 0`.

- [ ] **Step 2: Run the test to verify it fails**

Run, from `frontend/`:
`npx vitest run src/components/app-chrome/__tests__/project-switcher.test.tsx`
Expected: FAIL on the new case only — the switcher renders `6 items`, because
`page_count` is not in the total.

- [ ] **Step 3: Write the implementation**

In `frontend/src/components/app-chrome/project-switcher.tsx`, replace `itemHint`
(lines 34-40) with:

```tsx
/** Items across all four corpora. A document-only project -- which the
 *  corpus import creates -- would read as broken under a memories-only
 *  count, showing "0 memories" for a scope that holds a hundred files. */
function itemHint(row: ProjectSummary): string {
  const total =
    row.memory_count + row.document_count + row.checkpoint_count + row.page_count
  return `${total} ${total === 1 ? "item" : "items"}`
}
```

In `frontend/src/routes/_authenticated.tsx`, the `FULL_WIDTH_ROUTES` comment says
`/notes` "renders that same workspace over the personal space". Replace that
clause so it names what is there now:

```
 *  resizable the same way -- and `/notes` is its own tree/pane split over the
 *  personal space's pages, so it is here for exactly that argument and no
 *  other.
```

In `CLAUDE.md`, the Documents section's pages paragraph currently ends
`...each `page_embeddings__<slug>` child adds a cascade trigger to every
`DELETE FROM blocks`.` Append to that paragraph:

```
**The SPA's `/notes` is the page tree's only surface, and it replaced the
document one on 2026-09-18** (increment B2). `features/notes/` renders it:
a sidebar tree with drag-to-reorder over `PATCH /pages/{id}`, per-row create,
rename and soft delete, a trash sheet over `GET /pages/trash`, and a page pane
whose block editor is a **deliberate copy** of the document block editor over
the page verbs, recorded as a duplicate that increment B3's BlockNote editor
deletes. `ProjectWorkspace` lost `treeManagement` in the same change and is the
corpus browser again. The cost is stated rather than discovered: **the personal
project's documents are now visible nowhere in the SPA** — `/documents` and the
project switcher both filter that project out — and the rows stay in the
database and reachable over REST and MCP. That is the owner's ruling (spec §2),
not an oversight, and no conversion is owed.
```

- [ ] **Step 4: Run the whole frontend leg**

Run, from `frontend/`, each on its own:

```
npm run typecheck
npm test
npm run build
```

Expected: `typecheck` silent; `npm test` green with no failures and a file count
at or above the 196 the baseline had; `build` succeeds. If a run returns exit
143, that is a SIGTERM from `earlyoom`, not a failure — check `free -h` and
re-run that leg alone.

Confirm by hand, and record the numbers in the commit body:
- `npm test` reports 0 failures.
- `src/lib/__tests__/query-keys.test.ts`, `src/lib/__tests__/api-paths.test.ts`
  and `src/__tests__/no-restricted-imports-count.test.ts` are all green — those
  are the enumeration guards a new surface trips.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/app-chrome/project-switcher.tsx frontend/src/components/app-chrome/__tests__/project-switcher.test.tsx frontend/src/routes/_authenticated.tsx CLAUDE.md
git commit -m "docs(notes): record the /notes page workspace"
```

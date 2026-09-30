# Pages, Increment B3 — the BlockNote editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace B2's copied per-block textarea editor on `/notes` with a BlockNote editor whose edits reach the page block verbs through a save engine that diffs the editor's document against the last tree the server acknowledged.

**Architecture:** Pure modules carry every decision worth testing on its own — `inline-markdown.ts` (block text ↔ inline content, verified and idempotent), `block-properties.ts` (the server's property and nesting rules), `sync-tree.ts` (the diff, a mirror of the server's refusals, and applying a write), `page-sync.ts` (one write in flight, the landed check, backoff, stops) and `block-mapping.ts` (server tree ↔ editor blocks, and canonicalisation). A thin React layer binds them: `use-page-sync.ts` keeps one engine per page outside React, `use-page-editor.ts` builds the editor with the nesting guard, and `page-editor.tsx` is lazy-loaded with BlockNote's CSS so neither reaches the main chunk. B2's copied editor and its five block-verb hooks are deleted.

**Tech Stack:** React 19, TypeScript, TanStack Query v5, BlockNote 0.54.2 (`@blocknote/core`, `@blocknote/react`, `@blocknote/shadcn`), `mdast-util-from-markdown` / `mdast-util-to-markdown` with GFM strikethrough, darkraise-ui v6, Tailwind v4, vitest + @testing-library/react, vite, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-18-pages-increment-b3-blocknote-editor-design.md` (refines §5 of the program spec)

**Execution:** inline — `claude --model sonnet --effort high` — 5 of 15 tasks are heavy (3, 4, 5, 6, 9), not a majority, so they are delegated; the 5 four-band tasks (2, 8, 10, 11, 12) are exactly a third of the plan (3 x 5 <= 15), so they are delegated too; the highest self-implemented total is 3

**Program:** `docs/superpowers/specs/2026-09-17-pages-increment-b-workspace-editor-design.md` — sub-project 3 of 3 — last

**Plan review:** 2026-09-18 — dr-superpowers:judge-opus — executability 14 / coherence 17 / coverage 14 / assumptions 15 (round 1)

## Global Constraints

- **Every code block in this plan was built and run** in a scratch copy of `frontend/` on 2026-09-18: `npm run typecheck` clean, every notes, hooks and route test passing (34 files, 192 tests), `npm run build` green, and `eslint` clean on every new file. Transcribe it exactly. If a step's result differs from its **Expected** line, stop and report rather than adapting the code.
- **`/documents` and `/projects/$project` must not change.** `features/documents/**`, `use-documents-api.ts`, `use-blocks-api.ts` and `features/documents/lib/mutation-queue.ts` are not edited.
- **No backend change and no schema change.** B1 shipped every route this increment calls. A task that finds it needs a backend edit stops and reports.
- **BlockNote is pinned exactly at `0.54.2`** — `@blocknote/core`, `@blocknote/react`, `@blocknote/shadcn`, installed with `--save-exact`. **No `@blocknote/xl-*` package** (AGPL-3.0 or commercial) and **no Yjs**.
- **The markdown packages are pinned at the versions already installed** through `react-markdown`: `mdast-util-from-markdown` 2.0.3, `mdast-util-to-markdown` 2.1.2, `micromark-extension-gfm-strikethrough` 2.1.0, `mdast-util-gfm-strikethrough` 2.0.0, and `@types/mdast` 4.0.4 as a dev dependency. No other dependency is added.
- **Nothing from BlockNote may reach the main chunk.** Only `page-editor.tsx`, `use-page-editor.ts`, `page-outline.tsx`, `lib/editor-schema.tsx` and `lib/nesting-guard.ts` import `@blocknote/*` or are imported by something that does; every other module imports at most their *types*. `page-pane.tsx` and `demo-notes.tsx` load `page-editor.tsx` only through `React.lazy`.
- **`enabled: !DEMO` on every query, and demo mode makes no request** (`tests/demo-makes-no-api-calls.spec.ts` covers `/notes`).
- **`apiFetch` prepends `/api/v1` itself.** No call site spells the base; `lib/__tests__/api-paths.test.ts` fails the build on one.
- **No new query key.** The page read keeps its registered `["page", pageId]` key through `pageQuery`; `invalidateQueries`/`removeQueries` on it are fine.
- **UI components come from darkraise-ui first** (CLAUDE.md). The editor's menus are BlockNote's own shadcn primitives because darkraise-ui's DropdownMenu, Popover and Select portal and BlockNote's slots must not; `page-editor.tsx` records that gap.
- **Comments:** default to none; only where the WHY is non-obvious. Never reference the task, the increment or a review finding.
- **English only** in code, comments, docs, commits and tests.
- **Commits:** `<type>(<scope>): <subject>`, type = feat|fix|docs|style|refactor|test|chore|perf, subject <= 50 chars, imperative, no period.
- **Every `git` command runs from the repo root**, and every path in a `git` command is repo-relative (`frontend/src/...`), unless its step says otherwise.
- **Frontend commands run from `frontend/`:** `npm run typecheck` (= `tsc -b`), `npm test` (= `vitest run`), `npm run build`. One file: `npx vitest run <path>`. `npm run lint` is advisory, and the repo has pre-existing lint errors (`page-pane.tsx`'s title-sync effect, the tests' `wrapper` components); a task leaves no *new* one.
- **Never run Playwright bare.** `npx playwright test` points `/api` at the live instance on `:8000`. The e2e leg is `backend/scripts/e2e/run_playwright_e2e.py` only (Task 15).
- **Host hazard:** an `earlyoom` daemon kills memory-heavy runs at ~80% swap. **Exit 143 is a SIGTERM, not a failure** — check `free -h` and re-run the leg alone before believing a red.
- **Deploy is not a task here.** After merge, CLAUDE.md's redeploy sequence applies: gate legs, `DARKMEM_PUSH=0 ./scripts/build-push.sh`, the image's sha tag equal to HEAD, `docker compose up -d`, then confirm a `page-editor-*.js` asset in the running image's `/app/web`. B2 is merged but not deployed (production ran `5d13b529` on 2026-09-18), so that deploy ships B2 as well.

## Contracts

Paths are under `frontend/src/features/notes/` unless stated.

**`lib/block-properties.ts` (Task 1)**
- `type Properties = Record<string, unknown> | null`
- `PAGE_TYPE_PROPERTIES: Readonly<Record<string, readonly string[]>>` — a copy of `block_verbs.py`'s `_PAGE_TYPE_PROPERTIES`.
- `PAGE_CONTAINERS: ReadonlySet<string>` = `list`, `todo`, `toggle`.
- `CALLOUT_VARIANTS = ["error", "info", "success", "warning"] as const`; `type CalloutVariant`; `isCalloutVariant(value: unknown): value is CalloutVariant`.
- `mergeProperties(stored, sent, oldType, newType): Properties` — `update_block`'s merge, then the type-change drop.
- `propertiesEqual(a, b): boolean` — deep, key-order-free, `null` ≡ `{}`.
- `canHold(parentType: string | null, childType: string): boolean` — `_check_page_nesting`.
- `invalidProperties(type, props): string | null` — `_validate_page_block`'s required properties.

**`lib/editor-schema.tsx` (Task 2)**
- `pageSchema` — the BlockNote schema: `paragraph`, `heading` (levels 1–6, no toggle headings), `bulletListItem`, `numberedListItem`, `checkListItem`, `toggleListItem`, `quote`, `codeBlock`, `table`, `divider`, custom `callout` (prop `variant`), custom `raw` (prop `source`, `content: "none"`); inline `text`, `link`, custom `rawInline` (prop `source`); styles `bold`, `italic`, `strike`, `code`.
- `type PageEditorInstance` — `BlockNoteEditor` over `pageSchema`'s three schemas (the editor *instance*; `PageEditor` is the Task 11 component). `type PageEditorBlock`, `type PagePartialBlock`.

**`lib/inline-markdown.ts` (Task 3)**
- `InlineStyles { bold?, italic?, code?, strike?: true }`, `StyledText { type: "text"; text; styles }`, `InlineLink { type: "link"; href; content: StyledText[] }`, `RawInline { type: "rawInline"; props: { source } }`, `type InlineNode = StyledText | InlineLink | RawInline` — the same shapes BlockNote's inline content uses.
- `parseInline(text: string): InlineNode[]`; `emitInline(nodes: InlineNode[]): string`, with `emitInline(parseInline(emitInline(c))) === emitInline(c)` for every `c`.

**`__tests__/seeded.ts` (Task 3)** — `rng(seed: number): () => number` (mulberry32) and `pick<T>(items: readonly T[], r): T`.

**`lib/sync-tree.ts` (Task 4)**
- `SyncBlock { id; parentId: string | null; type; text; properties: Properties }`; `type SyncTree = readonly SyncBlock[]` — pre-order, siblings in order.
- `NewBlock { block_id; type; text; properties; parent_id; after_block_id }` — the batch route's item shape.
- `type SyncOp = { kind: "insert"; blocks: NewBlock[] } | { kind: "move"; id; parentId; afterId } | { kind: "update"; id; type; text; properties } | { kind: "delete"; id }`.
- `type Refusal = { status: 404 | 409 | 422; message }`; `refusalOf(tree, op, placedType?): Refusal | null`.
- `applyOp(tree, op): SyncBlock[]`; `treesEqual(a, b): boolean`; `nextOp(snapshot, desired): SyncOp | null` (throws when the trees differ and no write is acceptable).

**`__tests__/fake-page-server.ts` (Task 4)** — `class FakeServer` (constructor from a `SyncTree`; `rows`, `kids`, `get`, `subtree`, `apply(op)` throwing `Refused`, `tree()`), `class Refused extends Error { status }`, `CONTAINERS`, `type Props`.

**`lib/page-sync.ts` (Task 5)**
- `class SyncTransportError extends Error { status?: number }` — `status` absent for a network failure.
- `interface PageTransport { read(): Promise<{ tree: SyncTree; hash: string }>; send(op: SyncOp, expectedHash: string): Promise<string> }`.
- `type SyncStatus = { kind: "idle" } | { kind: "saved" } | { kind: "saving" } | { kind: "retrying" } | { kind: "stopped"; reason: "conflict" | "gone" | "refused"; message: string }`.
- `class PageSync(snapshot: SyncTree, hash: string, transport: PageTransport, sleep?: (ms) => Promise<void>)` with `snapshot`, `desired`, `status`, `stopped`, `pending`, `subscribe(listener)`, `onSettled(listener)` (called after each drain, once `pending` reads its final value), `setDesired(tree)`, `flush(): Promise<void>`.

**`lib/block-mapping.ts` (Task 6)**
- `EditorBlockLike { id; type; props: Record<string, unknown>; content?: unknown; children: EditorBlockLike[] }`; `type TableRowIds = Map<string, string[]>`.
- `toEditorBlocks(tree): { blocks: EditorBlockLike[]; rowIds: TableRowIds }`.
- `toSyncTree(blocks, previous: SyncTree, rowIds, mintId: () => string): { tree: SyncBlock[]; rowIds: TableRowIds }`.
- `canonicalTree(tree): { tree: SyncBlock[]; rowIds: TableRowIds }` — `toSyncTree(toEditorBlocks(tree))`.
- `fromPageBlocks(rows: readonly BlockRow[]): SyncBlock[]`.

**`lib/nesting-guard.ts` (Task 7)** — `nestingViolations(doc): Set<string>`; `addsNestingViolation(before, after): boolean`.

**`lib/page-transport.ts` (Task 8)** — `KEEPALIVE_MAX_BODY = 60_000`; `createPageTransport(pageId: string): PageTransport`.

**`use-page-sync.ts` (Task 9)**
- `TEXT_IDLE_MS = 800`.
- `PageSyncBinding { initialBlocks: EditorBlockLike[]; status: SyncStatus; onDocumentChange(blocks); flushNow(); discard() }`.
- `usePageSync(page: PageView, generation: number, createTransport = createPageTransport): PageSyncBinding`.
- `resetPageSyncEngines()` — test hook.

**`use-document-mode.ts` (Task 10)** — `type DocumentMode = "light" | "dark"`; `useDocumentMode(): DocumentMode`.

**`use-page-editor.ts` (Task 10)** — `pageSlashItems(editor: PageEditorInstance, query): DefaultReactSuggestionItem[]`; `usePageEditor(initialBlocks): PageEditorInstance`.

**`page-outline.tsx` (Task 11)** — `PageOutline({ editor }: { editor: PageEditorInstance })`.

**`page-editor.tsx` (Task 11)** — `PageEditorProps { initialBlocks; editable; onDocumentChange?; onBlur? }`; `PageEditor(props)`.

**`page-pane.tsx` (Task 12)** — `PagePane({ page, autoFocusTitle }: { page: PageView; autoFocusTitle: boolean })`, unchanged signature.

**`demo-notes.tsx` / `lib/demo-page.ts` (Task 14)** — `DemoNotes()`; `DEMO_PAGE: readonly SyncBlock[]`, `DEMO_PAGE_TITLE`.

## Assumptions (evidence)

- **Every module, test and edit in this plan ran green in a scratch copy of `frontend/`** with its own `node_modules` on 2026-09-18: `npx tsc -b` clean; `npx vitest run src/features/notes src/hooks/api src/routes/_authenticated/__tests__/notes` 33 files / 183 tests passed; the full `npx vitest run` passed except four files that read `../backend` and `../docs`, which do not exist beside a scratch copy (`graph-colors`, `no-second-claim-producer`, `progress/parsers`, `progress/startable` — all `ENOENT`); `npm run build` green with a 952 kB `page-editor-*.js` and its own `page-editor-*.css`, and `grep -c "bn-block-outer\|useCreateBlockNote"` over `index-*.js` and `notes-*.js` gave 0.
- **BlockNote 0.54.2** is MPL-2.0 for all three packages, `@blocknote/react` accepts React 19, `@blocknote/shadcn` wants `tailwindcss ^4.1.12` (repo: 4.2.2); `npm view`, 2026-09-18. The Yjs peers of `@blocknote/core` are optional.
- **The markdown packages are already in the tree** at 2.0.3 / 2.1.2 / 2.1.0 / 2.0.0 and `@types/mdast` 4.0.4, through `react-markdown` (`npm ls`, 2026-09-18), so pinning them adds no new code.
- **BlockNote's own markdown conversion is lossy** (probe, 2026-09-18: `<kbd>` and `![img](u)` vanished, `\*lit\*` came back as emphasis), which is why `inline-markdown.ts` exists.
- **`mdast-util-to-markdown` alone is not round-trip safe** for emphasis beside punctuation or whitespace (the scratch property test found non-settling strings in under 1,000 generated cases); the degrade-and-verify emitter is the measured fix, passing 5,000 cases on each of five seeds.
- **The server's page rules** are `backend/app/services/block_verbs.py:283-341` (`_PAGE_TYPE_PROPERTIES`, `_PAGE_CONTAINERS`, `_validate_page_block`, `_check_page_nesting`), `:644-687` (`update_block`: merge, drop, retype nesting), `:603-641` (`_insert_into`: a null `after_block_id` is the first child; an anchor that is not a child of the parent is `BlockTargetUnresolved`) and `:759-810` (`move_block`: `BlockCycleError` at `:776` for a move into the own subtree). Route statuses: `backend/app/api/routes/pages.py:254-267` — `BlockTargetUnresolved` 404, `BlockCycleError`/`PageBlockInvalid`/`DocumentTooLarge` 422, `PageBlockIdTaken`/`DocumentHashConflict` 409.
- **`content_hash` covers only the stored content, not the title** (`page_door.py:478`, `compute_content_hash(stored_content)`), which is why a 409 with no change behind it has no benign cause.
- **Request shapes**: `PageBlockUpdateRequest`, `PageBlockMoveRequest`, `PageBlockBatchItem`, `PageBlockBatchInsertRequest` at `backend/app/schemas/page.py:138-170`, all `extra="forbid"`; the delete route answers `X-Content-Hash` (B1 §3.7).
- **darkraise-ui's `useTheme()` throws outside a `ThemeProvider`** (`node_modules/darkraise-ui/dist/chunk-FVOKEH2M.js:2554-2559`) and the provider writes `<html data-mode>` (`:1664`), so the editor reads the mode from the document.
- **darkraise-ui ships every one of BlockNote's 13 shadcn slots** (`ls node_modules/darkraise-ui/dist/components/`), but its DropdownMenu and Popover export portals (`components/dropdown-menu.d.ts:21-26`, `components/popover.d.ts:2`) and its Select's implementation (`dist/chunk-AHBRB45H.js`, imported by `components/select.js`) imports the portal primitive `dist/chunk-PAKNQHL5.js` (`src/primitives/portal/Portal.tsx`, `createPortal` into `document.body`). BlockNote's shadcn page says the DropdownMenu, Popover and Select passed through `shadCNComponents` must not use portals (https://www.blocknotejs.org/docs/getting-started/shadcn, source `docs/content/docs/getting-started/shadcn.mdx` at v0.54.0, read 2026-09-18) — so no overrides.
- **The notes workspace tests mock `PagePane`** (`notes-workspace.test.tsx:23`, `notes-workspace-move.test.tsx:20`), so rewiring the pane leaves them unaffected.
- **`routes/_authenticated/__tests__/*.test.tsx` all draw a "does not export a Route" warning from the route generator** — seven after this plan, six before — and `routeTree.gen.ts` is unchanged (diffed, 2026-09-18). The new route test is named `notes.demo.test.tsx`, following `memory-graph-route.demo.test.tsx`.
- **The e2e harness sets the spec's environment**: `backend/scripts/e2e/run_playwright_e2e.py:93` exports `E2E_DISPOSABLE_STACK=1` and `:100` `E2E_ADMIN_PASSWORD`; `frontend/tests/helpers/seed-admin.ts:82` is `seedAdminPassword`, called only without a disposable stack. The toggle selectors (`.bn-toggle-wrapper[data-show-children]`, `.bn-toggle-button`) were read off the rendered 0.54.2 DOM under jsdom on 2026-09-18.
- **The e2e spec in Task 15 has not been run**: the disposable stack is booted only by `run_playwright_e2e.py`, which the prototype did not start. It is the one unverified code block in this plan, and Task 15 runs it.
- **The external-executor lane is closed.** `scripts/codex-gate` printed `usable=false reason=plugin-not-enabled review=false lane=false source=probe` on 2026-09-18, so no task carries an `**Executor:**` line and plan review runs on a Claude judge.

## Task index

1. Page property and nesting rules
2. BlockNote dependencies, the page schema and the probe
3. Inline markdown converter
4. The sync tree diff
5. The page save engine
6. Block mapping and canonicalisation
7. The nesting guard
8. The page transport
9. `usePageSync`
10. The editor hooks: document mode and `usePageEditor`
11. The page editor and its outline rail
12. Wire the editor into the page pane
13. Retire B2's copied editor and block hooks
14. Demo mode's sample page
15. End-to-end spec, docs and the frontend legs

---


### Task 1: Page property and nesting rules

**Files:**
- Create: `frontend/src/features/notes/lib/block-properties.ts`
- Test: `frontend/src/features/notes/__tests__/block-properties.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: every `lib/block-properties.ts` name in Contracts.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3


- [ ] **Step 1: Write the failing test**


`frontend/src/features/notes/__tests__/block-properties.test.ts`:

````ts
import { describe, expect, it } from "vitest"
import {
  canHold,
  invalidProperties,
  isCalloutVariant,
  mergeProperties,
  propertiesEqual,
} from "../lib/block-properties"

describe("block properties", () => {
  it("merges sent keys over stored ones when the type stays", () => {
    expect(mergeProperties({ ordered: true, marker: "3.", number: 3 }, { ordered: true, marker: "1." }, "list", "list")).toEqual({
      ordered: true,
      marker: "1.",
      number: 3,
    })
  })

  it("keeps only the new type's keys on a type change", () => {
    expect(mergeProperties({ ordered: false, marker: "-" }, { checked: false }, "list", "todo")).toEqual({ checked: false })
    expect(mergeProperties({ checked: true }, null, "todo", "paragraph")).toBeNull()
  })

  it("stores an empty merge as null", () => {
    expect(mergeProperties(null, {}, "paragraph", "paragraph")).toBeNull()
  })

  it("compares with null and {} equal and key order ignored", () => {
    expect(propertiesEqual(null, {})).toBe(true)
    expect(propertiesEqual({ a: 1, b: [1, { c: 2, d: 3 }] }, { b: [1, { d: 3, c: 2 }], a: 1 })).toBe(true)
    expect(propertiesEqual({ a: 1 }, { a: 2 })).toBe(false)
  })

  it("lets only list, todo and toggle hold children, and a table its rows", () => {
    expect(canHold(null, "paragraph")).toBe(true)
    for (const parent of ["list", "todo", "toggle"]) expect(canHold(parent, "code")).toBe(true)
    for (const parent of ["paragraph", "heading", "quote", "callout", "code"]) expect(canHold(parent, "paragraph")).toBe(false)
    expect(canHold("table", "table_row")).toBe(true)
    expect(canHold("table", "paragraph")).toBe(false)
  })

  it("requires checked on a todo and a known variant on a callout", () => {
    expect(invalidProperties("todo", { checked: false })).toBeNull()
    expect(invalidProperties("todo", null)).toMatch(/checked/)
    expect(invalidProperties("callout", { variant: "warning" })).toBeNull()
    expect(invalidProperties("callout", { variant: "tip" })).toMatch(/variant/)
    expect(isCalloutVariant("success")).toBe(true)
    expect(isCalloutVariant("note")).toBe(false)
  })
})
````


- [ ] **Step 2: Run it to verify it fails**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/block-properties.test.ts`
Expected: FAIL — `Failed to resolve import "../lib/block-properties"`.


- [ ] **Step 3: Write the module**


`frontend/src/features/notes/lib/block-properties.ts`:

````ts
export type Properties = Record<string, unknown> | null

/** The keys each page block type defines -- a copy of
 *  `backend/app/services/block_verbs.py`'s `_PAGE_TYPE_PROPERTIES`, which is
 *  the authority. A type change drops every other key. */
export const PAGE_TYPE_PROPERTIES: Readonly<Record<string, readonly string[]>> = {
  paragraph: [],
  heading: ["level"],
  list: ["ordered", "marker", "number"],
  code: ["language"],
  quote: [],
  table: ["header", "alignments"],
  table_row: ["cells"],
  divider: [],
  html: [],
  todo: ["checked"],
  toggle: [],
  callout: ["variant"],
}

/** `_PAGE_CONTAINERS`: the only types that hold children on a page, besides a
 *  table holding its rows. */
export const PAGE_CONTAINERS: ReadonlySet<string> = new Set(["list", "todo", "toggle"])

export const CALLOUT_VARIANTS = ["error", "info", "success", "warning"] as const
export type CalloutVariant = (typeof CALLOUT_VARIANTS)[number]

export function isCalloutVariant(value: unknown): value is CalloutVariant {
  return typeof value === "string" && (CALLOUT_VARIANTS as readonly string[]).includes(value)
}

function nonEmpty(props: Record<string, unknown>): Properties {
  return Object.keys(props).length === 0 ? null : props
}

/** The properties `update_block` stores: the sent keys merged over the stored
 *  ones, then, on a type change, only the keys the new type defines. */
export function mergeProperties(
  stored: Properties,
  sent: Properties,
  oldType: string,
  newType: string,
): Properties {
  const merged = nonEmpty({ ...(stored ?? {}), ...(sent ?? {}) })
  if (merged === null || oldType === newType) return merged
  const defined = PAGE_TYPE_PROPERTIES[newType] ?? []
  return nonEmpty(Object.fromEntries(Object.entries(merged).filter(([k]) => defined.includes(k))))
}

function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical)
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value as object)
        .sort()
        .map((k) => [k, canonical((value as Record<string, unknown>)[k])]),
    )
  }
  return value
}

/** Deep equality with `null` and `{}` equal, since the server stores an empty
 *  merge as NULL. */
export function propertiesEqual(a: Properties, b: Properties): boolean {
  return JSON.stringify(canonical(nonEmpty(a ?? {}))) === JSON.stringify(canonical(nonEmpty(b ?? {})))
}

/** `_check_page_nesting`: may a block of `parentType` (null = the page root)
 *  hold a block of `childType`. */
export function canHold(parentType: string | null, childType: string): boolean {
  if (parentType === null || PAGE_CONTAINERS.has(parentType)) return true
  return parentType === "table" && childType === "table_row"
}

/** `_validate_page_block`'s required properties; the message is the server's. */
export function invalidProperties(type: string, props: Properties): string | null {
  const p = props ?? {}
  if (type === "todo" && typeof p.checked !== "boolean") {
    return "a todo block needs a boolean `checked` property"
  }
  if (type === "callout" && !isCalloutVariant(p.variant)) {
    return `a callout block needs \`variant\` set to one of ${CALLOUT_VARIANTS.join(", ")}`
  }
  return null
}
````


- [ ] **Step 4: Run the test to verify it passes**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/block-properties.test.ts`
Expected: PASS, 6 tests.


- [ ] **Step 5: Commit**


From the repo root:

```bash
git add frontend/src/features/notes/lib/block-properties.ts frontend/src/features/notes/__tests__/block-properties.test.ts
git commit -m "feat(notes): mirror the page block property rules"
```



### Task 2: BlockNote dependencies, the page schema and the probe

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json` (through `npm install` only)
- Create: `frontend/src/features/notes/lib/editor-schema.tsx`
- Test: `frontend/src/features/notes/__tests__/blocknote-probe.test.tsx`

**Interfaces:**
- Consumes: `CALLOUT_VARIANTS`, `CalloutVariant` (Task 1).
- Produces: `pageSchema`, `PageEditorInstance`, `PageEditorBlock`, `PagePartialBlock` (Contracts, Task 2), and the dependencies every later task imports.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4


- [ ] **Step 1: Install the pinned dependencies**


From `frontend/`:

```bash
npm install --no-audit --no-fund --save-exact @blocknote/core@0.54.2 @blocknote/react@0.54.2 @blocknote/shadcn@0.54.2 mdast-util-from-markdown@2.0.3 mdast-util-to-markdown@2.1.2 micromark-extension-gfm-strikethrough@2.1.0 mdast-util-gfm-strikethrough@2.0.0
npm install --no-audit --no-fund --save-dev --save-exact @types/mdast@4.0.4
git diff package.json
```

Expected: `package.json` gains exactly these lines and nothing else — in `dependencies`: `"@blocknote/core": "0.54.2"`, `"@blocknote/react": "0.54.2"`, `"@blocknote/shadcn": "0.54.2"`, `"mdast-util-from-markdown": "2.0.3"`, `"mdast-util-gfm-strikethrough": "2.0.0"`, `"mdast-util-to-markdown": "2.1.2"`, `"micromark-extension-gfm-strikethrough": "2.1.0"`; in `devDependencies`: `"@types/mdast": "4.0.4"`. `ls node_modules/@blocknote` lists `core react shadcn` and no `xl-*`.


- [ ] **Step 2: Write the failing probe test**


These are the BlockNote facts the rest of the plan builds on (spec §1), one assertion per row that a test can observe; the file's header comment names the two that cannot. An upgrade that changes one must fail here.

`frontend/src/features/notes/__tests__/blocknote-probe.test.tsx`:

````tsx
import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { act, render } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { BlockNoteEditor, defaultBlockSpecs } from "@blocknote/core"
import { getDefaultReactSlashMenuItems, useCreateBlockNote } from "@blocknote/react"
import { BlockNoteView } from "@blocknote/shadcn"
import { pageSchema, type PageEditorInstance } from "../lib/editor-schema"

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

async function mount(initialContent: unknown[]) {
  let editor!: PageEditorInstance
  function Probe() {
    editor = useCreateBlockNote({
      schema: pageSchema,
      trailingBlock: false,
      tables: { headers: false, splitCells: false, cellBackgroundColor: false, cellTextColor: false },
      initialContent: initialContent as never,
    })
    return <BlockNoteView editor={editor} />
  }
  const view = render(<Probe />)
  await act(async () => {})
  return { editor, container: view.container }
}

/** Facts about BlockNote 0.54.2 the page editor is built on. An upgrade that
 *  changes one fails here rather than in a user's page. */
function manifest(name: string): { version: string; license: string; peerDependencies?: Record<string, string>; peerDependenciesMeta?: Record<string, { optional?: boolean }> } {
  return JSON.parse(readFileSync(resolve("node_modules", name, "package.json"), "utf8"))
}

/** Facts no test can observe, and so not asserted here: that
 *  `trailingBlock: false` removes the rendered empty trailing line (it is a
 *  decoration, not a block in the document), and that darkraise-ui's menus
 *  would break BlockNote's slots by portalling (spec section 4.5). */
describe("BlockNote 0.54.2", () => {
  it("is MPL-2.0, takes React 19, and leaves Yjs optional", () => {
    for (const name of ["@blocknote/core", "@blocknote/react", "@blocknote/shadcn"]) {
      expect(manifest(name)).toMatchObject({ version: "0.54.2", license: "MPL-2.0" })
    }
    expect(manifest("@blocknote/react").peerDependencies?.react).toContain("^19.0")
    expect(manifest("@blocknote/core").peerDependenciesMeta?.yjs?.optional).toBe(true)
  })

  it("ships the list, to-do, toggle and divider blocks with these props", () => {
    expect(Object.keys(defaultBlockSpecs)).toEqual(
      expect.arrayContaining(["checkListItem", "toggleListItem", "divider", "numberedListItem", "bulletListItem"]),
    )
    const props = (name: keyof typeof defaultBlockSpecs) => Object.keys(defaultBlockSpecs[name].config.propSchema)
    expect(props("checkListItem")).toContain("checked")
    expect(props("numberedListItem")).toContain("start")
  })

  it("loses content in its own markdown conversion", async () => {
    const editor = BlockNoteEditor.create()
    const blocks = await editor.tryParseMarkdownToBlocks("a <kbd>k</kbd> ![i](u) \\*lit\\*")
    const text = JSON.stringify(blocks)
    expect(text).not.toContain("kbd")
    expect(text).not.toContain("![i](u)")
    expect(await editor.blocksToMarkdownLossy(blocks)).toContain("*lit*")
  })

  it("mints UUID v4 block ids and honours explicit ones", () => {
    const editor = BlockNoteEditor.create({ trailingBlock: false })
    expect(editor.document[0]!.id).toMatch(UUID_V4)
    editor.insertBlocks([{ id: "given", type: "paragraph", content: "x" }], editor.document[0]!.id, "after")
    expect(editor.document.map((b) => b.id)).toContain("given")
  })

  it("keeps heading levels 4 to 6 and an arbitrary code language", async () => {
    const { editor } = await mount([
      { id: "h", type: "heading", props: { level: 6 }, content: "H" },
      { id: "k", type: "codeBlock", props: { language: "weirdlang" }, content: "x" },
    ])
    const heading = editor.getBlock("h")!.props as Record<string, unknown>
    expect(heading.level).toBe(6)
    expect(heading).not.toHaveProperty("isToggleable")
    expect((editor.getBlock("k")!.props as Record<string, unknown>).language).toBe("weirdlang")
  })

  it("keeps a table's header row with header toggling off", async () => {
    const { editor } = await mount([
      { id: "t", type: "table", content: { type: "tableContent", headerRows: 1, rows: [{ cells: ["h"] }, { cells: ["a"] }] } },
    ])
    expect((editor.getBlock("t")!.content as { headerRows?: number }).headerRows).toBe(1)
  })

  it("reports moves as their own change, and a child's edit without its parent", async () => {
    const { editor } = await mount([
      { id: "l", type: "bulletListItem", content: "l", children: [{ id: "c", type: "paragraph", content: "c" }] },
      { id: "p", type: "paragraph", content: "p" },
    ])
    const seen: string[] = []
    editor.onChange((_e, { getChanges }) => {
      for (const change of getChanges()) seen.push(`${change.type}:${change.block.id}`)
    })
    editor.updateBlock("c", { content: "edited" })
    editor.setTextCursorPosition("p")
    editor.moveBlocksUp()
    expect(seen).toEqual(["update:c", "move:p"])
  })

  it("names a move's parents and marks a programmatic change local", async () => {
    const { editor } = await mount([
      { id: "l", type: "bulletListItem", content: "l", children: [{ id: "c", type: "paragraph", content: "c" }] },
      { id: "p", type: "paragraph", content: "p" },
    ])
    const moves: { prev?: string; current?: string; source: string }[] = []
    editor.onChange((_e, { getChanges }) => {
      for (const change of getChanges()) {
        if (change.type === "move") {
          moves.push({ prev: change.prevParent?.id, current: change.currentParent?.id, source: change.source.type })
        }
      }
    })
    editor.setTextCursorPosition("p")
    editor.moveBlocksUp()
    expect(moves).toEqual([{ prev: undefined, current: "l", source: "local" }])
  })

  it("holds a table as one block of rows and cells, and reports its edit as one update", async () => {
    const { editor } = await mount([
      { id: "t", type: "table", content: { type: "tableContent", headerRows: 1, rows: [{ cells: ["h"] }, { cells: ["a"] }] } },
    ])
    expect(editor.getBlock("t")!.content).toMatchObject({
      type: "tableContent",
      rows: [{ cells: [{ type: "tableCell", content: [{ type: "text", text: "h" }] }] }, { cells: [{ type: "tableCell" }] }],
    })
    const seen: string[] = []
    editor.onChange((_e, { getChanges }) => {
      for (const change of getChanges()) seen.push(`${change.type}:${change.block.id}`)
    })
    editor.updateBlock("t", { content: { type: "tableContent", rows: [{ cells: ["h"] }, { cells: ["b"] }] } as never })
    expect(seen).toEqual(["update:t"])
  })

  it("offers these slash menu keys", async () => {
    const { editor } = await mount([{ id: "p", type: "paragraph", content: "p" }])
    expect(getDefaultReactSlashMenuItems(editor).map((item) => (item as unknown as { key: string }).key)).toEqual([
      "heading",
      "heading_2",
      "heading_3",
      "quote",
      "toggle_list",
      "numbered_list",
      "bullet_list",
      "check_list",
      "paragraph",
      "code_block",
      "divider",
      "table",
      "heading_4",
      "heading_5",
      "heading_6",
      "emoji",
    ])
  })

  it("marks each block's outer element with its id", async () => {
    const { container } = await mount([{ id: "p", type: "paragraph", content: "p" }])
    expect(container.querySelector('.bn-block-outer[data-id="p"]')).not.toBeNull()
  })
})
````


- [ ] **Step 3: Run it to verify it fails**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/blocknote-probe.test.tsx`
Expected: FAIL — `Failed to resolve import "../lib/editor-schema"`.


- [ ] **Step 4: Write the schema**


`frontend/src/features/notes/lib/editor-schema.tsx`:

````tsx
import {
  BlockNoteSchema,
  type BlockNoteEditor,
  createHeadingBlockSpec,
  defaultBlockSpecs,
  defaultInlineContentSpecs,
  defaultStyleSpecs,
} from "@blocknote/core"
import { createReactBlockSpec, createReactInlineContentSpec } from "@blocknote/react"
import { cn } from "darkraise-ui/lib"
import { CALLOUT_VARIANTS, type CalloutVariant } from "./block-properties"

const CALLOUT_TONE: Record<CalloutVariant, string> = {
  info: "border-sky-500/40 bg-sky-500/10",
  warning: "border-amber-500/40 bg-amber-500/10",
  error: "border-red-500/40 bg-red-500/10",
  success: "border-emerald-500/40 bg-emerald-500/10",
}


export const createCallout = createReactBlockSpec(
  {
    type: "callout",
    propSchema: { variant: { default: "info", values: CALLOUT_VARIANTS } },
    content: "inline",
  },
  {
    render: ({ block, contentRef }) => (
      <div
        className={cn("w-full rounded-md border px-3 py-2", CALLOUT_TONE[block.props.variant])}
        data-variant={block.props.variant}
      >
        <div ref={contentRef} />
      </div>
    ),
  },
)

export const createRaw = createReactBlockSpec(
  {
    type: "raw",
    propSchema: { source: { default: "" } },
    content: "none",
  },
  {
    render: ({ block }) => (
      <pre className="bg-muted/40 text-muted-foreground w-full overflow-x-auto rounded px-2 py-1 font-mono text-xs">
        {block.props.source}
      </pre>
    ),
  },
)

export const rawInline = createReactInlineContentSpec(
  {
    type: "rawInline",
    propSchema: { source: { default: "" } },
    content: "none",
  },
  {
    render: ({ inlineContent }) => (
      <code className="bg-muted rounded px-1 font-mono text-xs">{inlineContent.props.source}</code>
    ),
  },
)

export const pageSchema = BlockNoteSchema.create({
  blockSpecs: {
    paragraph: defaultBlockSpecs.paragraph,
    heading: createHeadingBlockSpec({ levels: [1, 2, 3, 4, 5, 6], allowToggleHeadings: false }),
    bulletListItem: defaultBlockSpecs.bulletListItem,
    numberedListItem: defaultBlockSpecs.numberedListItem,
    checkListItem: defaultBlockSpecs.checkListItem,
    toggleListItem: defaultBlockSpecs.toggleListItem,
    quote: defaultBlockSpecs.quote,
    codeBlock: defaultBlockSpecs.codeBlock,
    table: defaultBlockSpecs.table,
    divider: defaultBlockSpecs.divider,
    callout: createCallout(),
    raw: createRaw(),
  },
  inlineContentSpecs: {
    text: defaultInlineContentSpecs.text,
    link: defaultInlineContentSpecs.link,
    rawInline,
  },
  styleSpecs: {
    bold: defaultStyleSpecs.bold,
    italic: defaultStyleSpecs.italic,
    strike: defaultStyleSpecs.strike,
    code: defaultStyleSpecs.code,
  },
})

export type PageSchema = typeof pageSchema
export type PageEditorBlock = typeof pageSchema.Block
export type PagePartialBlock = typeof pageSchema.PartialBlock
export type PageEditorInstance = BlockNoteEditor<
  typeof pageSchema.blockSchema,
  typeof pageSchema.inlineContentSchema,
  typeof pageSchema.styleSchema
>
````


- [ ] **Step 5: Run the probe to verify it passes**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/blocknote-probe.test.tsx`
Expected: PASS, 11 tests.


- [ ] **Step 6: Typecheck**


Run (from `frontend/`): `npm run typecheck`
Expected: exit 0, no output.


- [ ] **Step 7: Commit**


From the repo root:

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/features/notes/lib/editor-schema.tsx frontend/src/features/notes/__tests__/blocknote-probe.test.tsx
git commit -m "feat(notes): add BlockNote and the page schema"
```



### Task 3: Inline markdown converter

**Files:**
- Create: `frontend/src/features/notes/lib/inline-markdown.ts`
- Create: `frontend/src/features/notes/__tests__/seeded.ts`
- Test: `frontend/src/features/notes/__tests__/inline-markdown.test.ts`

**Interfaces:**
- Consumes: the markdown packages (Task 2).
- Produces: `parseInline`, `emitInline` and the inline types; `rng`, `pick` (Contracts, Task 3).

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5


- [ ] **Step 1: Write the seeded generator helper**


A deterministic PRNG so the property suites are reproducible without a property-testing dependency.

`frontend/src/features/notes/__tests__/seeded.ts`:

````ts
/** A deterministic PRNG (mulberry32): the property suites are reproducible
 *  from their seeds without a property-testing dependency. */
export function rng(seed: number): () => number {
  let s = seed >>> 0
  return () => {
    s = (s + 0x6d2b79f5) >>> 0
    let t = s
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export function pick<T>(items: readonly T[], r: () => number): T {
  return items[Math.floor(r() * items.length)]!
}
````


- [ ] **Step 2: Write the failing test**


Three properties carry the design (spec §4.2): **idempotence** over adversarial content (the diff compares emitted strings, so a string that moves on a round trip would be rewritten on every flush), full fidelity for typed content, and no visible character lost for arbitrary content. The named cases pin each raw-atom kind byte for byte.

`frontend/src/features/notes/__tests__/inline-markdown.test.ts`:

````ts
import { describe, expect, it } from "vitest"
import { emitInline, parseInline, type InlineNode, type InlineStyles } from "../lib/inline-markdown"
import { pick, rng } from "./seeded"

const ALPHABET = ["a", "b", "Z", "1", " ", "  ", "\n", "*", "_", "`", "~", "[", "]", "(", ")", "<", ">", "&", "#", "\\", "!", "|", "-", "+", ".", "é", "&amp;", "http://x.y", "1.", "# "]

function genText(r: () => number): string {
  let out = ""
  const n = 1 + Math.floor(r() * 5)
  for (let i = 0; i < n; i++) out += pick(ALPHABET, r)
  return out
}

function genStyles(r: () => number): InlineStyles {
  const s: InlineStyles = {}
  if (r() < 0.3) s.bold = true
  if (r() < 0.3) s.italic = true
  if (r() < 0.2) s.strike = true
  if (r() < 0.15) s.code = true
  return s
}

function genContent(r: () => number): InlineNode[] {
  const out: InlineNode[] = []
  const n = Math.floor(r() * 5)
  for (let i = 0; i < n; i++) {
    const k = r()
    if (k < 0.75) out.push({ type: "text", text: genText(r), styles: genStyles(r) })
    else if (k < 0.9) out.push({ type: "link", href: "https://ex.am/p?q=" + Math.floor(r() * 9), content: [{ type: "text", text: genText(r).replace(/\n/g, "") || "l", styles: genStyles(r) }] })
    else out.push({ type: "rawInline", props: { source: pick(["<kbd>", "![i](u)", "<http://a.b>", '[t](u "t")'], r) } })
  }
  return out
}

const WORDS = ["alpha", "Beta", "x1", "déjà", "a_b", "2*3", "c++", "don't", "e.g.", "50%", "[x]", "<tag>", "&amp;", "~tilde~", "`tick`", "#hash", "1."]

/** Content the way typing produces it: a styled run starts and ends on a
 *  word, and runs are separated by plain spaces or punctuation. */
function genTyped(r: () => number): InlineNode[] {
  const out: InlineNode[] = []
  const n = 1 + Math.floor(r() * 4)
  for (let i = 0; i < n; i++) {
    if (i > 0) out.push({ type: "text", text: pick([" ", ", ", " - ", "\n"], r), styles: {} })
    const words = Array.from({ length: 1 + Math.floor(r() * 3) }, () => pick(WORDS, r)).join(" ")
    if (r() < 0.2) out.push({ type: "link", href: "https://ex.am/" + i, content: [{ type: "text", text: words.replace(/`/g, ""), styles: {} }] })
    else out.push({ type: "text", text: words, styles: genStyles(r) })
  }
  return out
}

type Cell = [string, boolean, boolean, boolean, boolean, string | null]

function cells(nodes: InlineNode[]): Cell[] {
  const out: Cell[] = []
  for (const n of nodes) {
    if (n.type === "rawInline") out.push([n.props.source, false, false, false, false, "atom"])
    const runs = n.type === "text" ? [n] : n.type === "link" ? n.content : []
    const href = n.type === "link" ? n.href : null
    for (const run of runs)
      for (const ch of run.text) {
        const styled = ch.trim() !== ""
        out.push([ch, styled && !!run.styles.bold, styled && !!run.styles.italic, styled && !!run.styles.strike, ch !== "\n" && !!run.styles.code, href])
      }
  }
  return out
}

describe("inline markdown", () => {
  it("settles: emit(parse(emit(c))) === emit(c) for arbitrary content", () => {
    const r = rng(7)
    for (let i = 0; i < 5000; i++) {
      const c = genContent(r)
      const once = emitInline(c)
      const twice = emitInline(parseInline(once))
      if (twice !== once) throw new Error(`case ${i}: ${JSON.stringify(c)}\nonce=${JSON.stringify(once)}\ntwice=${JSON.stringify(twice)}`)
    }
  })

  it("keeps every character, mark and link of typed content", () => {
    const r = rng(11)
    for (let i = 0; i < 5000; i++) {
      const c = genTyped(r)
      const back = parseInline(emitInline(c))
      if (JSON.stringify(cells(back)) !== JSON.stringify(cells(c)))
        throw new Error(`case ${i}: ${JSON.stringify(c)} -> ${JSON.stringify(emitInline(c))} -> ${JSON.stringify(back)}`)
    }
  })

  it("keeps every visible character of arbitrary content", () => {
    const r = rng(13)
    for (let i = 0; i < 5000; i++) {
      const c = genContent(r)
      const text = (nodes: InlineNode[]) => cells(nodes).map((x) => x[0]).join("").replace(/\s+/g, "")
      const back = parseInline(emitInline(c))
      if (text(back) !== text(c)) throw new Error(`case ${i}: ${JSON.stringify(c)} -> ${JSON.stringify(emitInline(c))}`)
    }
  })

  it.each([
    ["<kbd>k</kbd> tail", "<kbd>"],
    ["an ![img](u) here", "![img](u)"],
    ["go <http://a.b> now", "<http://a.b>"],
    ['[t](u "title")', '[t](u "title")'],
    ["**bold ![i](u)**", "**bold ![i](u)**"],
    ["hard  \nbreak", "  \n"],
  ])("keeps %j byte for byte through an edit elsewhere", (text, atom) => {
    const nodes = parseInline(text)
    expect(nodes.some((n) => n.type === "rawInline" && n.props.source === atom)).toBe(true)
    const edited: InlineNode[] = [...nodes, { type: "text", text: " more", styles: {} }]
    expect(emitInline(edited)).toContain(atom)
  })

  it("reads a reference link or footnote with no definition as text", () => {
    expect(parseInline("see [x][1]")).toEqual([{ type: "text", text: "see [x][1]", styles: {} }])
    expect(parseInline(emitInline(parseInline("note[^n]")))).toEqual([{ type: "text", text: "note[^n]", styles: {} }])
  })
  it("maps marks and inline links", () => {
    expect(parseInline("a **b** *c* `d` ~~e~~ [f](https://x.y)")).toEqual([
      { type: "text", text: "a ", styles: {} },
      { type: "text", text: "b", styles: { bold: true } },
      { type: "text", text: " ", styles: {} },
      { type: "text", text: "c", styles: { italic: true } },
      { type: "text", text: " ", styles: {} },
      { type: "text", text: "d", styles: { code: true } },
      { type: "text", text: " ", styles: {} },
      { type: "text", text: "e", styles: { strike: true } },
      { type: "text", text: " ", styles: {} },
      { type: "link", href: "https://x.y", content: [{ type: "text", text: "f", styles: {} }] },
    ])
  })

  it("does not read block markers in inline text", () => {
    expect(parseInline("# not a heading")).toEqual([{ type: "text", text: "# not a heading", styles: {} }])
    expect(parseInline("- not a list")).toEqual([{ type: "text", text: "- not a list", styles: {} }])
  })

  it("decodes escapes and entities, then escapes them back", () => {
    expect(parseInline("\\*lit\\* &lt;kbd&gt;")).toEqual([{ type: "text", text: "*lit* <kbd>", styles: {} }])
    const back = emitInline(parseInline("\\*lit\\* &lt;kbd&gt;"))
    expect(parseInline(back)).toEqual([{ type: "text", text: "*lit* <kbd>", styles: {} }])
  })

  it("keeps a soft line break as a newline", () => {
    expect(parseInline("one\ntwo")).toEqual([{ type: "text", text: "one\ntwo", styles: {} }])
    expect(emitInline(parseInline("one\ntwo"))).toBe("one\ntwo")
  })

  it("keeps text it cannot rebuild as one atom", () => {
    expect(parseInline("a\n\nb")).toEqual([{ type: "rawInline", props: { source: "a\n\nb" } }])
  })

  it("empty text is no content", () => {
    expect(parseInline("")).toEqual([])
    expect(emitInline([])).toBe("")
  })
})
````


- [ ] **Step 3: Run it to verify it fails**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/inline-markdown.test.ts`
Expected: FAIL — `Failed to resolve import "../lib/inline-markdown"`.


- [ ] **Step 4: Write the converter**


`frontend/src/features/notes/lib/inline-markdown.ts`:

````ts
import type { Html, InlineCode, Nodes, PhrasingContent, Root, Text } from "mdast"
import { fromMarkdown } from "mdast-util-from-markdown"
import { toMarkdown } from "mdast-util-to-markdown"
import { gfmStrikethrough } from "micromark-extension-gfm-strikethrough"
import {
  gfmStrikethroughFromMarkdown,
  gfmStrikethroughToMarkdown,
} from "mdast-util-gfm-strikethrough"

export interface InlineStyles {
  bold?: true
  italic?: true
  code?: true
  strike?: true
}

export interface StyledText {
  type: "text"
  text: string
  styles: InlineStyles
}

export interface InlineLink {
  type: "link"
  href: string
  content: StyledText[]
}

export interface RawInline {
  type: "rawInline"
  props: { source: string }
}

export type InlineNode = StyledText | InlineLink | RawInline

const FLOW_CONSTRUCTS = [
  "blockQuote",
  "codeFenced",
  "codeIndented",
  "definition",
  "headingAtx",
  "htmlFlow",
  "list",
  "setextUnderline",
  "thematicBreak",
]

const STYLE_ORDER = ["bold", "italic", "strike"] as const

function raw(source: string): RawInline {
  return { type: "rawInline", props: { source } }
}

function sliceOf(text: string, node: Nodes): string {
  return text.slice(node.position!.start.offset!, node.position!.end.offset!)
}

function sameStyles(a: InlineStyles, b: InlineStyles): boolean {
  return (
    Boolean(a.bold) === Boolean(b.bold) &&
    Boolean(a.italic) === Boolean(b.italic) &&
    Boolean(a.code) === Boolean(b.code) &&
    Boolean(a.strike) === Boolean(b.strike)
  )
}

function mergeRuns(runs: StyledText[]): StyledText[] {
  const out: StyledText[] = []
  for (const run of runs) {
    if (run.text === "") continue
    const last = out[out.length - 1]
    if (last && sameStyles(last.styles, run.styles)) last.text += run.text
    else out.push({ type: "text", text: run.text, styles: { ...run.styles } })
  }
  return out
}

/** Styled runs for a subtree built only from text, emphasis, strong, delete
 *  and inline code; null when it holds anything else, so the caller keeps the
 *  whole subtree as one raw atom rather than dropping the part it cannot show
 *  (a raw atom carries no styles, so an image inside bold would lose the
 *  bold). */
function runsOf(node: PhrasingContent, styles: InlineStyles): StyledText[] | null {
  switch (node.type) {
    case "text":
      return [{ type: "text", text: node.value, styles }]
    case "inlineCode":
      return [{ type: "text", text: node.value, styles: { ...styles, code: true } }]
    case "strong":
    case "emphasis":
    case "delete": {
      const key = node.type === "strong" ? "bold" : node.type === "emphasis" ? "italic" : "strike"
      const out: StyledText[] = []
      for (const child of node.children) {
        const runs = runsOf(child, { ...styles, [key]: true })
        if (runs === null) return null
        out.push(...runs)
      }
      return out
    }
    default:
      return null
  }
}

function isInlineLink(text: string, node: PhrasingContent): boolean {
  if (node.type !== "link" || node.title) return false
  const source = sliceOf(text, node)
  return source.startsWith("[") && source.endsWith(")")
}

function convert(text: string, node: PhrasingContent, out: InlineNode[]) {
  if (node.type === "link") {
    if (isInlineLink(text, node)) {
      const content: StyledText[] = []
      for (const child of node.children) {
        const runs = runsOf(child, {})
        if (runs === null) {
          out.push(raw(sliceOf(text, node)))
          return
        }
        content.push(...runs)
      }
      out.push({ type: "link", href: node.url, content: mergeRuns(content) })
      return
    }
    out.push(raw(sliceOf(text, node)))
    return
  }
  const runs = runsOf(node, {})
  if (runs === null) out.push(raw(sliceOf(text, node)))
  else out.push(...runs)
}

function mergeNodes(nodes: InlineNode[]): InlineNode[] {
  const out: InlineNode[] = []
  for (const node of nodes) {
    if (node.type === "text") {
      if (node.text === "") continue
      const last = out[out.length - 1]
      if (last?.type === "text" && sameStyles(last.styles, node.styles)) {
        last.text += node.text
        continue
      }
      out.push({ ...node, styles: { ...node.styles } })
    } else {
      out.push(node)
    }
  }
  return out
}

export function parseInline(text: string): InlineNode[] {
  if (text === "") return []
  const tree: Root = fromMarkdown(text, {
    extensions: [gfmStrikethrough(), { disable: { null: FLOW_CONSTRUCTS } }],
    mdastExtensions: [gfmStrikethroughFromMarkdown()],
  })
  const paragraph = tree.children[0]
  // Anything that is not exactly one paragraph spanning the whole string --
  // a blank line splitting two paragraphs, whitespace the paragraph trimmed --
  // cannot be rebuilt from runs, so the text survives as one atom.
  if (
    tree.children.length !== 1 ||
    paragraph?.type !== "paragraph" ||
    paragraph.position!.start.offset !== 0 ||
    paragraph.position!.end.offset !== text.length
  ) {
    return [raw(text)]
  }
  const out: InlineNode[] = []
  for (const child of paragraph.children) convert(text, child, out)
  return mergeNodes(out)
}

function leaf(run: StyledText): PhrasingContent[] {
  if (run.styles.code) return [{ type: "inlineCode", value: run.text } satisfies InlineCode]
  return [{ type: "text", value: run.text } satisfies Text]
}

/** A code span turns a line ending into a space, so a newline inside a code
 *  run leaves the span and stays a newline with the run's other marks. */
function splitCodeNewlines(runs: StyledText[]): StyledText[] {
  const out: StyledText[] = []
  for (const run of runs) {
    if (!run.styles.code || !run.text.includes("\n")) {
      out.push(run)
      continue
    }
    const { code: _code, ...rest } = run.styles
    run.text.split("\n").forEach((part, i) => {
      if (i > 0) out.push({ type: "text", text: "\n", styles: rest })
      if (part !== "") out.push({ type: "text", text: part, styles: run.styles })
    })
  }
  return out
}

/** The one form both sides of a comparison are reduced to, and the only form
 *  `emitOnce` reads, so two contents with the same normal form emit the same
 *  string. */
function canonicalStyles(styles: InlineStyles): InlineStyles {
  const out: InlineStyles = {}
  if (styles.bold) out.bold = true
  if (styles.italic) out.italic = true
  if (styles.strike) out.strike = true
  if (styles.code) out.code = true
  return out
}

function normalizeRuns(runs: StyledText[]): StyledText[] {
  return mergeRuns(unstyleEdgeSpace(mergeRuns(splitCodeNewlines(runs)))).map((run) => ({
    ...run,
    styles: canonicalStyles(run.styles),
  }))
}

function normalize(nodes: InlineNode[]): InlineNode[] {
  const out: InlineNode[] = []
  let runs: StyledText[] = []
  const flush = () => {
    out.push(...normalizeRuns(runs))
    runs = []
  }
  for (const node of nodes) {
    if (node.type === "text") {
      runs.push(node)
      continue
    }
    flush()
    out.push(node.type === "link" ? { ...node, content: normalizeRuns(node.content) } : node)
  }
  flush()
  return trimEdges(stripLineEdgeSpace(out))
}

/** Spaces before a line ending are dropped or turn it into a hard break,
 *  spaces after one are indentation the paragraph strips, and a blank line
 *  ends the paragraph, so none of them is part of what the text says. Runs
 *  are walked as one string so a space and the newline beside it may sit in
 *  different runs. */
function stripLineEdgeSpace(nodes: InlineNode[]): InlineNode[] {
  const out = nodes.map((n) => (n.type === "text" ? { ...n } : n))
  for (let i = 0; i < out.length; i++) {
    const node = out[i]
    if (node?.type !== "text") continue
    node.text = node.text
      .replace(/[ \t]+\n/g, "\n")
      .replace(/\n[ \t]+/g, "\n")
      .replace(/\n{2,}/g, "\n")
    const next = out[i + 1]
    if (next?.type !== "text") continue
    if (next.text.startsWith("\n")) node.text = node.text.replace(/[ \t]+$/, "")
    if (node.text.endsWith("\n")) next.text = next.text.replace(/^[ \t\n]+/, "")
  }
  return mergeNodes(out.filter((n) => n.type !== "text" || n.text !== ""))
}

/** A paragraph cannot begin or end with whitespace, so the text's outer
 *  whitespace is not part of what it says. */
function trimEdges(nodes: InlineNode[]): InlineNode[] {
  const out = [...nodes]
  for (let first = out[0]; first?.type === "text"; first = out[0]) {
    const text = first.text.replace(/^\s+/, "")
    if (text !== "") {
      out[0] = { ...first, text }
      break
    }
    out.shift()
  }
  for (let last = out[out.length - 1]; last?.type === "text"; last = out[out.length - 1]) {
    const text = last.text.replace(/\s+$/, "")
    if (text !== "") {
      out[out.length - 1] = { ...last, text }
      break
    }
    out.pop()
  }
  return out
}

function nest(runs: StyledText[], level: number): PhrasingContent[] {
  if (level === STYLE_ORDER.length) return runs.flatMap(leaf)
  const key = STYLE_ORDER[level]!
  const out: PhrasingContent[] = []
  const marked = (run: StyledText | undefined) => Boolean(run?.styles[key])
  let i = 0
  while (i < runs.length) {
    const has = marked(runs[i])
    let j = i
    while (j < runs.length && marked(runs[j]) === has) j++
    const inner = nest(runs.slice(i, j), level + 1)
    if (!has) out.push(...inner)
    else if (key === "bold") out.push({ type: "strong", children: inner })
    else if (key === "italic") out.push({ type: "emphasis", children: inner })
    else out.push({ type: "delete", children: inner })
    i = j
  }
  return out
}

/** Whitespace at the edge of a bold, italic or strike run cannot be written
 *  as markdown emphasis (a delimiter next to a space does not open or close),
 *  and styling a space shows nothing, so the space moves outside the run. */
function unstyleEdgeSpace(runs: StyledText[]): StyledText[] {
  const out: StyledText[] = []
  for (const run of runs) {
    const { code, ...marks } = run.styles
    if (code || Object.keys(marks).length === 0) {
      out.push(run)
      continue
    }
    const m = /^(\s*)([\s\S]*?)(\s*)$/.exec(run.text)!
    if (m[1]) out.push({ type: "text", text: m[1], styles: {} })
    if (m[2]) out.push({ type: "text", text: m[2], styles: run.styles })
    if (m[3]) out.push({ type: "text", text: m[3], styles: {} })
  }
  return out
}

function emitOnce(nodes: InlineNode[]): string {
  const children: PhrasingContent[] = []
  let runs: StyledText[] = []
  const flush = () => {
    children.push(...nest(normalizeRuns(runs), 0))
    runs = []
  }
  for (const node of nodes) {
    if (node.type === "text") {
      runs.push(node)
      continue
    }
    flush()
    if (node.type === "link") {
      children.push({
        type: "link",
        url: node.href,
        children: nest(normalizeRuns(node.content), 0),
      })
    } else {
      children.push({ type: "html", value: node.props.source } satisfies Html)
    }
  }
  flush()
  if (children.length === 0) return ""
  const out = toMarkdown(
    { type: "paragraph", children },
    {
      emphasis: "*",
      strong: "*",
      extensions: [gfmStrikethroughToMarkdown()],
    },
  )
  return out.endsWith("\n") ? out.slice(0, -1) : out
}

type Degrade = (run: StyledText) => InlineStyles

const HAS_WORD = /[\p{L}\p{N}]/u

/** Markdown cannot express every placement of emphasis (a delimiter between
 *  punctuation and a letter neither opens nor closes), so marks are dropped
 *  in this order until the string reads back as what it was built from. */
const DEGRADE: Degrade[] = [
  (run) => run.styles,
  (run) => (HAS_WORD.test(run.text) ? run.styles : run.styles.code ? { code: true } : {}),
  (run) => (run.styles.code ? { code: true } : {}),
  () => ({}),
]

function degrade(nodes: InlineNode[], rule: Degrade): InlineNode[] {
  const apply = (run: StyledText): StyledText => ({ ...run, styles: rule(run) })
  return nodes.map((node) =>
    node.type === "text" ? apply(node) : node.type === "link" ? { ...node, content: node.content.map(apply) } : node,
  )
}

/** The markdown for `nodes`. The result always reads back through
 *  `parseInline` as exactly the content it was emitted from, which is what
 *  makes emitting settle: emit(parse(emit(c))) === emit(c). The sync diff
 *  compares emitted strings, so a string that moved on every round trip would
 *  be rewritten on every flush. When marks had to be dropped, the saved text
 *  carries fewer marks than the editor showed until the next reload. */
export function emitInline(nodes: InlineNode[]): string {
  let current = nodes
  let out = ""
  // The second pass starts from what the last attempt actually reads back
  // as, which always verifies; it exists for the few spellings the markdown
  // writer rewrites on purpose (a line ending before `<` becomes a space).
  for (let pass = 0; pass < 2; pass++) {
    for (const rule of DEGRADE) {
      const target = normalize(degrade(current, rule))
      out = emitOnce(target)
      if (JSON.stringify(normalize(parseInline(out))) === JSON.stringify(target)) return out
    }
    current = parseInline(out)
  }
  return out
}
````


- [ ] **Step 5: Run the test to verify it passes**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/inline-markdown.test.ts`
Expected: PASS, 16 tests (three of them 5,000 generated cases each).


- [ ] **Step 6: Commit**


From the repo root:

```bash
git add frontend/src/features/notes/lib/inline-markdown.ts frontend/src/features/notes/__tests__/seeded.ts frontend/src/features/notes/__tests__/inline-markdown.test.ts
git commit -m "feat(notes): convert block text to inline content"
```



### Task 4: The sync tree diff

**Files:**
- Create: `frontend/src/features/notes/lib/sync-tree.ts`
- Create: `frontend/src/features/notes/__tests__/fake-page-server.ts`
- Test: `frontend/src/features/notes/__tests__/sync-tree.test.ts`

**Interfaces:**
- Consumes: `mergeProperties`, `propertiesEqual`, `canHold`, `invalidProperties`, `Properties` (Task 1); `rng`, `pick` (Task 3).
- Produces: every `lib/sync-tree.ts` name and the `FakeServer` helper (Contracts, Task 4).

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5


- [ ] **Step 1: Write the fake server**


An independent port of `block_verbs.py`'s page verbs. It is deliberately **not** built on `refusalOf`: a test whose server shares the client's mirror of the rules could not catch a mistake in that mirror.

`frontend/src/features/notes/__tests__/fake-page-server.ts`:

````ts
import type { SyncBlock, SyncOp, SyncTree } from "../lib/sync-tree"

export type Props = Record<string, unknown> | null

interface Row {
  id: string
  parent: string | null
  type: string
  text: string
  props: Props
}

const DEFINED: Record<string, readonly string[]> = {
  paragraph: [],
  heading: ["level"],
  list: ["ordered", "marker", "number"],
  code: ["language"],
  quote: [],
  table: ["header", "alignments"],
  table_row: ["cells"],
  divider: [],
  html: [],
  todo: ["checked"],
  toggle: [],
  callout: ["variant"],
}

export const CONTAINERS: readonly string[] = ["list", "todo", "toggle"]

export class Refused extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

/** A port of `backend/app/services/block_verbs.py`'s page verbs, written
 *  from the Python rather than from the module under test, so a mistake in
 *  the client's mirror of those rules cannot hide behind the same mistake
 *  here. Rows sit in one flat list; a sibling run is the list order. */
export class FakeServer {
  rows: Row[]

  constructor(tree: SyncTree) {
    this.rows = tree.map((b) => ({ id: b.id, parent: b.parentId, type: b.type, text: b.text, props: b.properties }))
  }

  kids(parent: string | null): Row[] {
    return this.rows.filter((r) => r.parent === parent)
  }

  get(id: string): Row | undefined {
    return this.rows.find((r) => r.id === id)
  }

  subtree(id: string): Set<string> {
    const out = new Set([id])
    let grew = true
    while (grew) {
      grew = false
      for (const r of this.rows) {
        if (r.parent !== null && out.has(r.parent) && !out.has(r.id)) {
          out.add(r.id)
          grew = true
        }
      }
    }
    return out
  }

  private nest(parent: Row | undefined, childType: string) {
    if (!parent || CONTAINERS.includes(parent.type)) return
    if (parent.type === "table" && childType === "table_row") return
    throw new Refused(422, `a ${parent.type} block cannot hold a ${childType} block on a page`)
  }

  private validate(type: string, props: Props) {
    const p = props ?? {}
    if (type === "todo" && typeof p.checked !== "boolean") throw new Refused(422, "todo needs checked")
    if (type === "callout" && !["error", "info", "success", "warning"].includes(p.variant as string)) {
      throw new Refused(422, "callout needs variant")
    }
  }

  private place(row: Row, after: string | null) {
    const siblings = this.kids(row.parent)
    let at: number
    if (after === null) {
      const first = siblings[0]
      at = first ? this.rows.indexOf(first) : this.rows.length
    } else {
      const anchor = siblings.find((s) => s.id === after)
      if (!anchor) throw new Refused(404, `after_block_id ${after} is not a child of the target parent`)
      at = this.rows.indexOf(anchor) + 1
    }
    this.rows.splice(at, 0, row)
  }

  /** Applies `op` or throws `Refused` with the route's status, leaving the
   *  rows untouched on a refusal as the savepoint does. */
  apply(op: SyncOp) {
    const before = this.rows.map((r) => ({ ...r }))
    try {
      this.applyUnchecked(op)
    } catch (error) {
      this.rows = before
      throw error
    }
  }

  private applyUnchecked(op: SyncOp) {
    switch (op.kind) {
      case "insert":
        for (const item of op.blocks) {
          if (this.get(item.block_id)) throw new Refused(409, `block id ${item.block_id} already exists`)
          const parent = item.parent_id === null ? undefined : this.get(item.parent_id)
          if (item.parent_id !== null && !parent) throw new Refused(404, `no parent block ${item.parent_id}`)
          this.nest(parent, item.type)
          this.validate(item.type, item.properties)
          this.place(
            { id: item.block_id, parent: item.parent_id, type: item.type, text: item.text, props: item.properties },
            item.after_block_id,
          )
        }
        return
      case "move": {
        const row = this.get(op.id)
        if (!row) throw new Refused(404, `block ${op.id} is not in this page`)
        if (op.parentId !== null && this.subtree(op.id).has(op.parentId)) {
          throw new Refused(422, "a block cannot be moved inside its own subtree")
        }
        const parent = op.parentId === null ? undefined : this.get(op.parentId)
        if (op.parentId !== null && !parent) throw new Refused(404, `no parent block ${op.parentId}`)
        this.nest(parent, row.type)
        if (op.afterId !== null && !this.kids(op.parentId).some((s) => s.id === op.afterId && s.id !== op.id)) {
          throw new Refused(404, `after_block_id ${op.afterId} is not a child of the target parent`)
        }
        this.rows.splice(this.rows.indexOf(row), 1)
        this.place({ ...row, parent: op.parentId }, op.afterId)
        return
      }
      case "update": {
        const row = this.get(op.id)
        if (!row) throw new Refused(404, `block ${op.id} is not in this page`)
        let merged: Props = { ...(row.props ?? {}), ...(op.properties ?? {}) }
        if (Object.keys(merged).length === 0) merged = null
        if (merged !== null && row.type !== op.type) {
          const defined = DEFINED[op.type] ?? []
          const kept = Object.fromEntries(Object.entries(merged).filter(([k]) => defined.includes(k)))
          merged = Object.keys(kept).length ? kept : null
        }
        this.validate(op.type, merged)
        if (row.type !== op.type) {
          this.nest(row.parent === null ? undefined : this.get(row.parent), op.type)
          for (const child of this.kids(row.id)) this.nest({ ...row, type: op.type }, child.type)
        }
        Object.assign(row, { type: op.type, text: op.text, props: merged })
        return
      }
      case "delete": {
        if (!this.get(op.id)) throw new Refused(404, `block ${op.id} is not in this page`)
        const doomed = this.subtree(op.id)
        this.rows = this.rows.filter((r) => !doomed.has(r.id))
      }
    }
  }

  /** The rows in pre-order, the order a page read serves them in. */
  tree(): SyncBlock[] {
    const out: SyncBlock[] = []
    const walk = (parent: string | null) => {
      for (const r of this.kids(parent)) {
        out.push({ id: r.id, parentId: r.parent, type: r.type, text: r.text, properties: r.props })
        walk(r.id)
      }
    }
    walk(null)
    return out
  }
}
````


- [ ] **Step 2: Write the failing test**


The convergence property runs 1,500 seeded random trees and edit sequences through the real loop against the fake server, failing on any refusal, any drift between the snapshot and the server, a runaway loop or stopping short. The named cases pin the orderings the spec calls out (§5.2).

`frontend/src/features/notes/__tests__/sync-tree.test.ts`:

````ts
import { describe, expect, it } from "vitest"
import { applyOp, nextOp, treesEqual, type SyncBlock, type SyncTree } from "../lib/sync-tree"
import { CONTAINERS, FakeServer, Refused, type Props } from "./fake-page-server"
import { pick, rng } from "./seeded"

const TYPES = ["paragraph", "heading", "list", "todo", "toggle", "quote", "code", "callout", "divider"]

function propsFor(type: string, r: () => number): Props {
  switch (type) {
    case "heading":
      return { level: 1 + Math.floor(r() * 6) }
    case "list":
      return { ordered: r() < 0.5, marker: r() < 0.5 ? "-" : "1." }
    case "todo":
      return { checked: r() < 0.5 }
    case "callout":
      return { variant: pick(["info", "warning", "error", "success"], r) }
    case "code":
      return { language: r() < 0.5 ? "text" : "py" }
    default:
      return null
  }
}

let counter = 0
const freshId = () => `b${++counter}`

function randomInsert(server: FakeServer, r: () => number) {
  const containers = server.rows.filter((x) => CONTAINERS.includes(x.type))
  const parent = r() < 0.4 && containers.length ? pick(containers, r).id : null
  const siblings = server.kids(parent)
  const after = r() < 0.3 || !siblings.length ? null : pick(siblings, r).id
  const type = pick(TYPES, r)
  server.apply({
    kind: "insert",
    blocks: [{ block_id: freshId(), type, text: `t${Math.floor(r() * 5)}`, properties: propsFor(type, r), parent_id: parent, after_block_id: after }],
  })
}

/** A random tree obeying the page rules, built through the fake server. */
function genTree(r: () => number, n: number): SyncBlock[] {
  const server = new FakeServer([])
  for (let i = 0; i < n; i++) randomInsert(server, r)
  return server.tree()
}

/** Random edits of the kinds the editor makes. An edit the rules refuse is
 *  skipped, so every desired tree is one the editor could hold. */
function edit(tree: SyncTree, r: () => number, k: number): SyncBlock[] {
  const server = new FakeServer(tree)
  for (let i = 0; i < k; i++) {
    const kind = r()
    try {
      if (kind < 0.3 || server.rows.length === 0) {
        randomInsert(server, r)
      } else if (kind < 0.45) {
        server.apply({ kind: "delete", id: pick(server.rows, r).id })
      } else if (kind < 0.7) {
        const row = pick(server.rows, r)
        const inside = server.subtree(row.id)
        const containers = server.rows.filter((x) => CONTAINERS.includes(x.type) && !inside.has(x.id))
        const parent = r() < 0.5 && containers.length ? pick(containers, r).id : null
        const siblings = server.kids(parent).filter((s) => s.id !== row.id)
        const after = r() < 0.3 || !siblings.length ? null : pick(siblings, r).id
        server.apply({ kind: "move", id: row.id, parentId: parent, afterId: after })
      } else if (kind < 0.85) {
        const row = pick(server.rows, r)
        const type = pick(TYPES, r)
        server.apply({ kind: "update", id: row.id, type, text: row.text, properties: propsFor(type, r) })
      } else {
        const row = pick(server.rows, r)
        server.apply({ kind: "update", id: row.id, type: row.type, text: `${row.text}!`, properties: row.props })
      }
    } catch (error) {
      if (!(error instanceof Refused)) throw error
    }
  }
  return server.tree()
}

/** Runs the sync loop against the fake server and returns how many writes
 *  it took, failing on any refusal, any drift between the snapshot and the
 *  server, a runaway loop, or stopping short. */
function converge(start: SyncTree, desired: SyncTree, label: string): number {
  const server = new FakeServer(start)
  let snapshot: SyncTree = start
  let writes = 0
  for (let op = nextOp(snapshot, desired); op !== null; op = nextOp(snapshot, desired)) {
    let refusal: Error | null = null
    try {
      server.apply(op)
    } catch (error) {
      refusal = error as Error
    }
    if (refusal) throw new Error(`${label}: server refused ${JSON.stringify(op)}: ${refusal.message}`)
    snapshot = applyOp(snapshot, op)
    if (!treesEqual(snapshot, server.tree())) {
      throw new Error(`${label}: snapshot drifted from the server after ${JSON.stringify(op)}`)
    }
    if (++writes > 4 * (start.length + desired.length) + 10) throw new Error(`${label}: did not converge`)
  }
  if (!treesEqual(snapshot, desired)) throw new Error(`${label}: stopped short of the desired tree`)
  return writes
}

const block = (id: string, parentId: string | null, type: string, properties: Props = null): SyncBlock => ({
  id,
  parentId,
  type,
  text: id,
  properties,
})
const BULLET = { ordered: false, marker: "-" }

describe("sync tree", () => {
  it("converges on any legal edit sequence, and the server accepts every write", () => {
    for (let seed = 0; seed < 1500; seed++) {
      const r = rng(seed)
      const start = genTree(r, Math.floor(r() * 12))
      const desired = edit(start, r, 1 + Math.floor(r() * 8))
      converge(start, desired, `seed ${seed}`)
    }
  })

  it("sends every new block as one batch and moves nothing else", () => {
    const start = [block("a", null, "paragraph"), block("b", null, "paragraph"), block("c", null, "paragraph")]
    const desired = [
      block("x", null, "paragraph"),
      start[0]!,
      block("y", null, "list", BULLET),
      block("y1", "y", "paragraph"),
      start[1]!,
      start[2]!,
    ]
    expect(nextOp(start, desired)).toEqual({
      kind: "insert",
      blocks: [
        { block_id: "x", type: "paragraph", text: "x", properties: null, parent_id: null, after_block_id: null },
        { block_id: "y", type: "list", text: "y", properties: BULLET, parent_id: null, after_block_id: "a" },
        { block_id: "y1", type: "paragraph", text: "y1", properties: null, parent_id: "y", after_block_id: null },
      ],
    })
    expect(converge(start, desired, "batch")).toBe(1)
  })

  it("never anchors on a sibling that only a later move brings under the parent", () => {
    const list = block("L", null, "list", BULLET)
    const x = block("X", null, "paragraph")
    const desired = [list, { ...x, parentId: "L" }, block("N", "L", "paragraph")]
    expect(converge([list, x], desired, "anchor")).toBe(2)
  })

  it("swaps an ancestor and its descendant without asking for a cycle", () => {
    const a = block("A", null, "list", BULLET)
    const b = block("B", "A", "list", BULLET)
    expect(converge([a, b], [{ ...b, parentId: null }, { ...a, parentId: "B" }], "swap")).toBe(2)
  })

  it("moves a child out before deleting its old parent", () => {
    const a = block("A", null, "toggle")
    const c = block("C", "A", "paragraph")
    expect(converge([a, c], [{ ...c, parentId: null }], "rescue")).toBe(2)
  })

  it("retypes a paragraph into a list before inserting its first child", () => {
    const p = block("P", null, "paragraph")
    expect(converge([p], [{ ...p, type: "list", properties: BULLET }, block("K", "P", "paragraph")], "retype")).toBe(2)
  })

  it("deletes only the topmost block of a removed subtree", () => {
    const a = block("A", null, "toggle")
    expect(nextOp([a, block("C", "A", "paragraph")], [])).toEqual({ kind: "delete", id: "A" })
  })

  it("writes nothing when the trees agree", () => {
    const tree = genTree(rng(3), 10)
    expect(nextOp(tree, tree)).toBeNull()
  })
})
````


- [ ] **Step 3: Run it to verify it fails**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/sync-tree.test.ts`
Expected: FAIL — `Failed to resolve import "../lib/sync-tree"`.


- [ ] **Step 4: Write the module**


`frontend/src/features/notes/lib/sync-tree.ts`:

````ts
import {
  canHold,
  invalidProperties,
  mergeProperties,
  propertiesEqual,
  type Properties,
} from "./block-properties"

/** One block in the form both sync trees use. A tree is an array in
 *  pre-order: a block's children follow it, in sibling order. */
export interface SyncBlock {
  id: string
  parentId: string | null
  type: string
  text: string
  properties: Properties
}

export type SyncTree = readonly SyncBlock[]

export interface NewBlock {
  block_id: string
  type: string
  text: string
  properties: Properties
  parent_id: string | null
  after_block_id: string | null
}

export type SyncOp =
  | { kind: "insert"; blocks: NewBlock[] }
  | { kind: "move"; id: string; parentId: string | null; afterId: string | null }
  | { kind: "update"; id: string; type: string; text: string; properties: Properties }
  | { kind: "delete"; id: string }

/** Why a tree cannot take an op, in the server's words; null when it can. */
export type Refusal = { status: 404 | 409 | 422; message: string }

function childrenOf(tree: SyncTree): Map<string | null, SyncBlock[]> {
  const map = new Map<string | null, SyncBlock[]>()
  for (const block of tree) {
    const list = map.get(block.parentId)
    if (list) list.push(block)
    else map.set(block.parentId, [block])
  }
  return map
}

function preOrder(byParent: Map<string | null, SyncBlock[]>): SyncBlock[] {
  const out: SyncBlock[] = []
  const walk = (parent: string | null) => {
    for (const child of byParent.get(parent) ?? []) {
      out.push(child)
      walk(child.id)
    }
  }
  walk(null)
  return out
}

function subtreeIds(tree: SyncTree, root: string): Set<string> {
  const byParent = childrenOf(tree)
  const out = new Set<string>()
  const stack = [root]
  while (stack.length) {
    const id = stack.pop()!
    out.add(id)
    for (const child of byParent.get(id) ?? []) stack.push(child.id)
  }
  return out
}

function placeIn(
  byParent: Map<string | null, SyncBlock[]>,
  block: SyncBlock,
  afterId: string | null,
) {
  const siblings = byParent.get(block.parentId) ?? []
  const index = afterId === null ? 0 : siblings.findIndex((b) => b.id === afterId) + 1
  siblings.splice(index, 0, block)
  byParent.set(block.parentId, siblings)
}

/** The refusal the server would answer `op` with against `tree`, mirroring
 *  `block_verbs.py`'s checks and their route statuses; null when it would
 *  accept it. */
export function refusalOf(tree: SyncTree, op: SyncOp, placedType?: string): Refusal | null {
  const byId = new Map(tree.map((b) => [b.id, b]))
  const byParent = childrenOf(tree)
  const placement = (
    parentId: string | null,
    afterId: string | null,
    type: string,
    self: string | null,
  ): Refusal | null => {
    const parent = parentId === null ? null : byId.get(parentId)
    if (parentId !== null && !parent) return { status: 404, message: `no parent block ${parentId}` }
    if (afterId !== null && !(byParent.get(parentId) ?? []).some((b) => b.id === afterId && b.id !== self)) {
      return { status: 404, message: `after_block_id ${afterId} is not a child of the target parent` }
    }
    if (!canHold(parent?.type ?? null, type)) {
      return { status: 422, message: `a ${parent!.type} block cannot hold a ${type} block on a page` }
    }
    return null
  }
  switch (op.kind) {
    case "insert": {
      let current: SyncTree = tree
      for (const item of op.blocks) {
        if (current.some((b) => b.id === item.block_id)) {
          return { status: 409, message: `block id ${item.block_id} already exists` }
        }
        const refused =
          refusalOf(current, { kind: "move", id: "", parentId: item.parent_id, afterId: item.after_block_id }, item.type) ??
          invalidOf(item.type, item.properties)
        if (refused) return refused
        current = applyOp(current, { kind: "insert", blocks: [item] })
      }
      return null
    }
    case "move": {
      // An insert is checked as the placement of a block not yet in the tree.
      if (placedType !== undefined) return placement(op.parentId, op.afterId, placedType, null)
      const block = byId.get(op.id)
      if (!block) return { status: 404, message: `block ${op.id} is not in this page` }
      if (op.parentId !== null && subtreeIds(tree, op.id).has(op.parentId)) {
        return { status: 422, message: "a block cannot be moved inside its own subtree" }
      }
      return placement(op.parentId, op.afterId, block.type, op.id)
    }
    case "update": {
      const block = byId.get(op.id)
      if (!block) return { status: 404, message: `block ${op.id} is not in this page` }
      const merged = mergeProperties(block.properties, op.properties, block.type, op.type)
      const invalid = invalidOf(op.type, merged)
      if (invalid) return invalid
      if (op.type !== block.type) {
        const parent = block.parentId === null ? null : byId.get(block.parentId)!
        if (!canHold(parent?.type ?? null, op.type)) {
          return { status: 422, message: `a ${parent!.type} block cannot hold a ${op.type} block on a page` }
        }
        const child = (byParent.get(op.id) ?? []).find((c) => !canHold(op.type, c.type))
        if (child) return { status: 422, message: `a ${op.type} block cannot hold a ${child.type} block on a page` }
      }
      return null
    }
    case "delete":
      return byId.has(op.id) ? null : { status: 404, message: `block ${op.id} is not in this page` }
  }

}

function invalidOf(type: string, props: Properties): Refusal | null {
  const message = invalidProperties(type, props)
  return message === null ? null : { status: 422, message }
}

/** `tree` after the server accepted `op`, by the server's own rules. */
export function applyOp(tree: SyncTree, op: SyncOp): SyncBlock[] {
  const byParent = childrenOf(tree.map((b) => ({ ...b })))
  switch (op.kind) {
    case "insert":
      for (const item of op.blocks) {
        placeIn(
          byParent,
          { id: item.block_id, parentId: item.parent_id, type: item.type, text: item.text, properties: item.properties },
          item.after_block_id,
        )
      }
      break
    case "move": {
      const all = [...byParent.values()].flat()
      const block = all.find((b) => b.id === op.id)!
      const from = byParent.get(block.parentId)!
      from.splice(from.indexOf(block), 1)
      placeIn(byParent, { ...block, parentId: op.parentId }, op.afterId)
      break
    }
    case "update":
      for (const siblings of byParent.values()) {
        const i = siblings.findIndex((b) => b.id === op.id)
        const block = siblings[i]
        if (!block) continue
        siblings[i] = {
          ...block,
          type: op.type,
          text: op.text,
          properties: mergeProperties(block.properties, op.properties, block.type, op.type),
        }
      }
      break
    case "delete": {
      const doomed = subtreeIds(tree, op.id)
      for (const [parent, siblings] of byParent) {
        byParent.set(parent, siblings.filter((b) => !doomed.has(b.id)))
      }
      break
    }
  }
  return preOrder(byParent)
}

export function treesEqual(a: SyncTree, b: SyncTree): boolean {
  if (a.length !== b.length) return false
  return a.every((x, i) => {
    const y = b[i]!
    return (
      x.id === y.id &&
      x.parentId === y.parentId &&
      x.type === y.type &&
      x.text === y.text &&
      propertiesEqual(x.properties, y.properties)
    )
  })
}

/** Indices of a longest strictly increasing subsequence of `values`. */
function lisIndices(values: readonly number[]): Set<number> {
  const at = (i: number) => values[i]!
  const tails: number[] = []
  const prev: number[] = new Array<number>(values.length).fill(-1)
  for (let i = 0; i < values.length; i++) {
    let lo = 0
    let hi = tails.length
    while (lo < hi) {
      const mid = (lo + hi) >> 1
      if (at(tails[mid]!) < at(i)) lo = mid + 1
      else hi = mid
    }
    if (lo > 0) prev[i] = tails[lo - 1]!
    tails[lo] = i
  }
  const out = new Set<number>()
  let k = tails.length ? tails[tails.length - 1]! : -1
  while (k !== -1) {
    out.add(k)
    k = prev[k]!
  }
  return out
}

/** Every op that would move `snapshot` toward `desired`, in the order they
 *  are preferred: new blocks first (as one batch), then moves in the desired
 *  tree's pre-order, then updates, then deletes of the topmost removed
 *  blocks. */
function candidates(snapshot: SyncTree, desired: SyncTree): SyncOp[] {
  const snapById = new Map(snapshot.map((b) => [b.id, b]))
  const desiredIds = new Set(desired.map((b) => b.id))
  const desiredByParent = childrenOf(desired)
  const snapByParent = childrenOf(snapshot)
  const out: SyncOp[] = []

  const fresh = desired.filter((b) => !snapById.has(b.id))
  const freshIds = new Set(fresh.map((b) => b.id))
  /** The nearest earlier desired sibling the server will already hold under
   *  the same parent when this block is placed: a sibling already there, or
   *  one earlier in the same batch. */
  const anchorFor = (block: SyncBlock, batch: boolean): string | null => {
    const siblings = desiredByParent.get(block.parentId) ?? []
    for (let i = siblings.findIndex((b) => b.id === block.id) - 1; i >= 0; i--) {
      const s = siblings[i]!
      if (batch && freshIds.has(s.id)) return s.id
      if (snapById.get(s.id)?.parentId === block.parentId) return s.id
    }
    return null
  }
  if (fresh.length) {
    out.push({
      kind: "insert",
      blocks: fresh.map((b) => ({
        block_id: b.id,
        type: b.type,
        text: b.text,
        properties: b.properties,
        parent_id: b.parentId,
        after_block_id: anchorFor(b, true),
      })),
    })
  }

  const moves: SyncOp[] = []
  const inPlace = new Set<string>()
  for (const [parent, desiredKids] of desiredByParent) {
    const snapKids = snapByParent.get(parent) ?? []
    const kept = desiredKids.filter((b) => snapById.get(b.id)?.parentId === parent)
    const positions = kept.map((b) => snapKids.findIndex((s) => s.id === b.id))
    const lis = lisIndices(positions)
    kept.forEach((b, i) => {
      if (lis.has(i)) inPlace.add(b.id)
    })
  }
  for (const block of desired) {
    if (!snapById.has(block.id) || inPlace.has(block.id)) continue
    moves.push({ kind: "move", id: block.id, parentId: block.parentId, afterId: anchorFor(block, false) })
  }
  out.push(...moves)

  for (const block of desired) {
    const stored = snapById.get(block.id)
    if (!stored) continue
    if (stored.type !== block.type || stored.text !== block.text || !propertiesEqual(stored.properties, block.properties)) {
      out.push({ kind: "update", id: block.id, type: block.type, text: block.text, properties: block.properties })
    }
  }

  for (const block of snapshot) {
    if (desiredIds.has(block.id)) continue
    const parentGoing = block.parentId !== null && !desiredIds.has(block.parentId)
    if (!parentGoing) out.push({ kind: "delete", id: block.id })
  }
  return out
}

/** The next write that moves the server toward `desired`: the first
 *  preferred op the server would accept, with a batch cut to its longest
 *  acceptable prefix. `null` when the trees already agree. Throws when they
 *  differ and no op is acceptable, which only a desired tree breaking the
 *  server's rules can cause. */
export function nextOp(snapshot: SyncTree, desired: SyncTree): SyncOp | null {
  const ops = candidates(snapshot, desired)
  if (ops.length === 0) return null
  for (const op of ops) {
    if (op.kind === "insert") {
      let n = op.blocks.length
      while (n > 0 && refusalOf(snapshot, { kind: "insert", blocks: op.blocks.slice(0, n) }) !== null) n--
      if (n > 0) return { kind: "insert", blocks: op.blocks.slice(0, n) }
      continue
    }
    // A delete whose subtree still holds a block the desired tree keeps would
    // take that block with it; it waits for the block to move out.
    if (op.kind === "delete") {
      const doomed = subtreeIds(snapshot, op.id)
      if (desired.some((b) => doomed.has(b.id))) continue
    }
    if (refusalOf(snapshot, op) === null) return op
  }
  throw new Error("no write the server would accept moves this page toward the editor")
}
````


- [ ] **Step 5: Run the test to verify it passes**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/sync-tree.test.ts`
Expected: PASS, 8 tests.


- [ ] **Step 6: Commit**


From the repo root:

```bash
git add frontend/src/features/notes/lib/sync-tree.ts frontend/src/features/notes/__tests__/fake-page-server.ts frontend/src/features/notes/__tests__/sync-tree.test.ts
git commit -m "feat(notes): diff a page tree into block writes"
```



### Task 5: The page save engine

**Files:**
- Create: `frontend/src/features/notes/lib/page-sync.ts`
- Test: `frontend/src/features/notes/__tests__/page-sync.test.ts`

**Interfaces:**
- Consumes: `nextOp`, `applyOp`, `treesEqual`, `SyncOp`, `SyncTree` (Task 4); `FakeServer` (Task 4).
- Produces: `PageSync`, `PageTransport`, `SyncStatus`, `SyncTransportError` (Contracts, Task 5).

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5


- [ ] **Step 1: Write the failing test**


`frontend/src/features/notes/__tests__/page-sync.test.ts`:

````ts
import { describe, expect, it } from "vitest"
import { FakeServer } from "./fake-page-server"
import { PageSync, SyncTransportError, type PageTransport, type SyncStatus } from "../lib/page-sync"
import type { SyncBlock, SyncOp } from "../lib/sync-tree"

const para = (id: string, text = id): SyncBlock => ({ id, parentId: null, type: "paragraph", text, properties: null })

/** The fake server behind a transport, with a content hash that moves on
 *  every accepted write and failures injected per call. */
function harness(start: SyncBlock[]) {
  const server = new FakeServer(start)
  let version = 0
  const hash = () => `h${version}`
  const sent: { op: SyncOp; expected: string }[] = []
  const faults: ((op: SyncOp) => "drop-response" | "drop-request" | number | null)[] = []
  const transport: PageTransport = {
    async read() {
      return { tree: server.tree(), hash: hash() }
    },
    async send(op, expected) {
      sent.push({ op, expected })
      const fault = faults.shift()?.(op) ?? null
      if (fault === "drop-request") throw new SyncTransportError("network")
      if (typeof fault === "number") throw new SyncTransportError(`status ${fault}`, fault)
      if (expected !== hash()) throw new SyncTransportError("stale hash", 409)
      server.apply(op)
      version++
      if (fault === "drop-response") throw new SyncTransportError("network")
      return hash()
    },
  }
  const sleeps: number[] = []
  const sync = new PageSync(start, "h0", transport, async (ms) => {
    sleeps.push(ms)
  })
  const statuses: SyncStatus["kind"][] = []
  sync.subscribe((s) => statuses.push(s.kind))
  return { server, sync, sent, faults, sleeps, statuses, bump: () => version++ }
}

describe("PageSync", () => {
  it("drains to the server, chaining each write on the hash the last one answered", async () => {
    const h = harness([para("a")])
    h.sync.setDesired([para("a", "edited"), para("b")])
    await h.sync.flush()
    expect(h.server.tree()).toEqual([para("a", "edited"), para("b")])
    expect(h.sent.map((s) => s.expected)).toEqual(["h0", "h1"])
    expect(h.sync.status).toEqual({ kind: "saved" })
    expect(h.sync.pending).toBe(false)
  })

  it("treats a lost response whose write landed as done, without resending", async () => {
    const h = harness([para("a")])
    h.faults.push(() => "drop-response")
    h.sync.setDesired([para("a", "x")])
    await h.sync.flush()
    expect(h.sent).toHaveLength(1)
    expect(h.sleeps).toEqual([])
    expect(h.server.tree()).toEqual([para("a", "x")])
  })

  it("resends a write that never arrived, backing off 1s, 2s, 4s", async () => {
    const h = harness([para("a")])
    h.faults.push(() => "drop-request", () => 503, () => "drop-request")
    h.sync.setDesired([para("a", "x")])
    await h.sync.flush()
    expect(h.sleeps).toEqual([1000, 2000, 4000])
    expect(h.statuses).toContain("retrying")
    expect(h.server.tree()).toEqual([para("a", "x")])
  })

  it("caps the backoff at 30s", async () => {
    const h = harness([para("a")])
    for (let i = 0; i < 8; i++) h.faults.push(() => "drop-request")
    h.sync.setDesired([para("a", "x")])
    await h.sync.flush()
    expect(h.sleeps).toEqual([1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000])
  })

  it("stops on a change made elsewhere", async () => {
    const h = harness([para("a")])
    h.faults.push(() => {
      h.server.apply({ kind: "update", id: "a", type: "paragraph", text: "theirs", properties: null })
      h.bump()
      return null
    })
    h.sync.setDesired([para("a", "mine")])
    await h.sync.flush()
    expect(h.sync.status).toMatchObject({ kind: "stopped", reason: "conflict" })
    expect(h.server.tree()).toEqual([para("a", "theirs")])
  })

  it("stops after a second 409 with nothing changed behind it", async () => {
    const h = harness([para("a")])
    h.faults.push(() => 409, () => 409)
    h.sync.setDesired([para("a", "x")])
    await h.sync.flush()
    expect(h.sync.status).toMatchObject({ kind: "stopped", reason: "conflict" })
    expect(h.sent).toHaveLength(2)
  })

  it("stops on 404 and on 422, keeping the server's message for a refusal", async () => {
    const gone = harness([para("a")])
    gone.faults.push(() => 404)
    gone.sync.setDesired([para("a", "x")])
    await gone.sync.flush()
    expect(gone.sync.status).toMatchObject({ kind: "stopped", reason: "gone" })

    const refused = harness([para("a")])
    refused.faults.push(() => 422)
    refused.sync.setDesired([para("a", "x")])
    await refused.sync.flush()
    expect(refused.sync.status).toEqual({ kind: "stopped", reason: "refused", message: "status 422" })
    expect(refused.sync.pending).toBe(false)
  })

  it("joins a flush already running and sends an edit made mid-write", async () => {
    const h = harness([para("a")])
    h.faults.push(() => {
      h.sync.setDesired([para("a", "one"), para("b")])
      return null
    })
    h.sync.setDesired([para("a", "one")])
    const first = h.sync.flush()
    const second = h.sync.flush()
    expect(second).toBe(first)
    await first
    expect(h.server.tree()).toEqual([para("a", "one"), para("b")])
  })

  it("tells settled listeners once the drain is over and nothing is pending", async () => {
    const h = harness([para("a")])
    const seen: boolean[] = []
    h.sync.onSettled(() => seen.push(h.sync.pending))
    h.sync.setDesired([para("a", "x")])
    await h.sync.flush()
    expect(seen).toEqual([false])
  })

  it("writes nothing once stopped", async () => {
    const h = harness([para("a")])
    h.faults.push(() => 422)
    h.sync.setDesired([para("a", "x")])
    await h.sync.flush()
    h.sync.setDesired([para("a", "y")])
    await h.sync.flush()
    expect(h.sent).toHaveLength(1)
  })
})
````


- [ ] **Step 2: Run it to verify it fails**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/page-sync.test.ts`
Expected: FAIL — `Failed to resolve import "../lib/page-sync"`.


- [ ] **Step 3: Write the engine**


`frontend/src/features/notes/lib/page-sync.ts`:

````ts
import { applyOp, nextOp, treesEqual, type SyncOp, type SyncTree } from "./sync-tree"

/** A failed write or read. `status` is the HTTP status, absent for a network
 *  failure. */
export class SyncTransportError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message)
    this.name = "SyncTransportError"
  }
}

export interface PageTransport {
  /** The page as the server holds it now, canonicalised by the caller. */
  read(): Promise<{ tree: SyncTree; hash: string }>
  /** Sends one write preconditioned on `expectedHash`; resolves to the
   *  page's new content hash. */
  send(op: SyncOp, expectedHash: string): Promise<string>
}

export type SyncStatus =
  | { kind: "idle" }
  | { kind: "saved" }
  | { kind: "saving" }
  | { kind: "retrying" }
  | { kind: "stopped"; reason: "conflict" | "gone" | "refused"; message: string }

const BACKOFF_START_MS = 1000
const BACKOFF_CAP_MS = 30_000
const CONFLICT_MESSAGE = "This page was changed somewhere else."
const GONE_MESSAGE = "This page is no longer available."

function isRetryable(error: unknown): error is SyncTransportError {
  return (
    error instanceof SyncTransportError &&
    (error.status === undefined || error.status >= 500 || error.status === 409)
  )
}

/** One page's save queue. It holds the last tree the server acknowledged
 *  and the tree the editor asks for, and drains the difference one write at
 *  a time. Pure of React and of the editor: the caller feeds it trees. */
export class PageSync {
  private snapshotTree: SyncTree
  private desiredTree: SyncTree
  private hash: string
  private running: Promise<void> | null = null
  private current: SyncStatus = { kind: "idle" }
  private readonly listeners = new Set<(status: SyncStatus) => void>()
  private readonly settledListeners = new Set<() => void>()

  constructor(
    snapshot: SyncTree,
    hash: string,
    private readonly transport: PageTransport,
    private readonly sleep: (ms: number) => Promise<void> = (ms) =>
      new Promise((resolve) => setTimeout(resolve, ms)),
  ) {
    this.snapshotTree = snapshot
    this.desiredTree = snapshot
    this.hash = hash
  }

  get snapshot(): SyncTree {
    return this.snapshotTree
  }

  get desired(): SyncTree {
    return this.desiredTree
  }

  get status(): SyncStatus {
    return this.current
  }

  get stopped(): boolean {
    return this.current.kind === "stopped"
  }

  /** Work not yet on the server: a write in flight, or a difference left. */
  get pending(): boolean {
    if (this.running !== null) return true
    if (this.stopped) return false
    try {
      return nextOp(this.snapshotTree, this.desiredTree) !== null
    } catch {
      return true
    }
  }

  subscribe(listener: (status: SyncStatus) => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  /** Called each time a drain has finished and `pending` reads its final
   *  value — which a status listener cannot rely on, since statuses are
   *  emitted from inside the drain. */
  onSettled(listener: () => void): () => void {
    this.settledListeners.add(listener)
    return () => this.settledListeners.delete(listener)
  }

  setDesired(tree: SyncTree) {
    this.desiredTree = tree
  }

  /** Drains until the server holds the desired tree or the queue stops. A
   *  call while a drain runs joins it; the drain re-reads the desired tree
   *  before every write, so a later edit is never left behind. */
  flush(): Promise<void> {
    if (this.stopped) return Promise.resolve()
    this.running ??= this.drain().finally(() => {
      this.running = null
      for (const listener of this.settledListeners) listener()
    })
    return this.running
  }

  private emit(status: SyncStatus) {
    this.current = status
    for (const listener of this.listeners) listener(status)
  }

  private stop(reason: "conflict" | "gone" | "refused", message: string) {
    this.emit({ kind: "stopped", reason, message })
  }

  private async drain() {
    let backoff = BACKOFF_START_MS
    let unexplained409 = 0
    for (;;) {
      let op: SyncOp | null
      try {
        op = nextOp(this.snapshotTree, this.desiredTree)
      } catch (error) {
        this.stop("refused", (error as Error).message)
        return
      }
      if (op === null) {
        this.emit({ kind: "saved" })
        return
      }
      if (this.current.kind !== "retrying") this.emit({ kind: "saving" })
      try {
        this.hash = await this.transport.send(op, this.hash)
        this.snapshotTree = applyOp(this.snapshotTree, op)
        backoff = BACKOFF_START_MS
        unexplained409 = 0
        this.emit({ kind: "saving" })
        continue
      } catch (error) {
        if (error instanceof SyncTransportError && error.status === 404) {
          this.stop("gone", GONE_MESSAGE)
          return
        }
        if (!isRetryable(error)) {
          this.stop("refused", (error as Error).message)
          return
        }
        const outcome = await this.landed(op)
        if (outcome === "landed") {
          backoff = BACKOFF_START_MS
          unexplained409 = 0
          continue
        }
        if (outcome === "stopped") return
        // Not landed and nothing else changed. A 409 with no change behind it
        // has no benign cause (the hash covers only the content), so a second
        // one in a row stops rather than looping.
        if (outcome === "unchanged" && error.status === 409 && ++unexplained409 >= 2) {
          this.stop("conflict", CONFLICT_MESSAGE)
          return
        }
        this.emit({ kind: "retrying" })
        await this.sleep(backoff)
        backoff = Math.min(backoff * 2, BACKOFF_CAP_MS)
      }
    }
  }

  /** Whether `op` reached the server, judged by one comparison of the
   *  re-read tree: the snapshot with the op applied, the snapshot unchanged,
   *  or anything else (someone else wrote). */
  private async landed(op: SyncOp): Promise<"landed" | "unchanged" | "unreadable" | "stopped"> {
    let read: { tree: SyncTree; hash: string }
    try {
      read = await this.transport.read()
    } catch (error) {
      if (error instanceof SyncTransportError && error.status === 404) {
        this.stop("gone", GONE_MESSAGE)
        return "stopped"
      }
      return "unreadable"
    }
    const applied = applyOp(this.snapshotTree, op)
    if (treesEqual(read.tree, applied)) {
      this.snapshotTree = applied
      this.hash = read.hash
      return "landed"
    }
    if (treesEqual(read.tree, this.snapshotTree)) {
      this.hash = read.hash
      return "unchanged"
    }
    this.stop("conflict", CONFLICT_MESSAGE)
    return "stopped"
  }
}
````


- [ ] **Step 4: Run the test to verify it passes**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/page-sync.test.ts`
Expected: PASS, 10 tests.


- [ ] **Step 5: Commit**


From the repo root:

```bash
git add frontend/src/features/notes/lib/page-sync.ts frontend/src/features/notes/__tests__/page-sync.test.ts
git commit -m "feat(notes): add the page save engine"
```



### Task 6: Block mapping and canonicalisation

**Files:**
- Create: `frontend/src/features/notes/lib/block-mapping.ts`
- Test: `frontend/src/features/notes/__tests__/block-mapping.test.tsx`

**Interfaces:**
- Consumes: `isCalloutVariant` (Task 1); `pageSchema`, `PageEditorInstance` (Task 2); `parseInline`, `emitInline`, `InlineNode` (Task 3); `SyncBlock`, `SyncTree`, `nextOp`, `treesEqual` (Task 4); `BlockRow` from `@/hooks/api` (existing).
- Produces: `EditorBlockLike`, `TableRowIds`, `toEditorBlocks`, `toSyncTree`, `canonicalTree`, `fromPageBlocks` (Contracts, Task 6).

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5


- [ ] **Step 1: Write the failing test**


The last case is the one that matters most: a page stored with every spelling the editor writes differently is loaded into the **real** editor and converted back, and must ask for no write. Without canonicalisation the first flush would rewrite the whole page (spec §5.1).

`frontend/src/features/notes/__tests__/block-mapping.test.tsx`:

````tsx
import { act, render } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { useCreateBlockNote } from "@blocknote/react"
import { BlockNoteView } from "@blocknote/shadcn"
import { canonicalTree, toEditorBlocks, toSyncTree, type EditorBlockLike } from "../lib/block-mapping"
import { pageSchema, type PageEditorInstance } from "../lib/editor-schema"
import { nextOp, treesEqual, type SyncBlock } from "../lib/sync-tree"

const b = (
  id: string,
  parentId: string | null,
  type: string,
  text: string,
  properties: SyncBlock["properties"] = null,
): SyncBlock => ({ id, parentId, type, text, properties })

/** A page stored with every spelling the editor writes differently. */
const STORED: SyncBlock[] = [
  b("h", null, "heading", "__Big__ &amp; _small_", { level: 5 }),
  b("p", null, "paragraph", "a <kbd>K</kbd> ![i](u) [x][1] \\*lit\\* line\nnext"),
  b("l", null, "list", "star", { ordered: false, marker: "*", number: 4 }),
  b("l1", "l", "list", "three", { ordered: true, marker: "3)", number: 3 }),
  b("t", null, "todo", "task", { checked: true }),
  b("g", null, "toggle", "fold"),
  b("g1", "g", "paragraph", "inside"),
  b("c", null, "callout", "note **it**", { variant: "warning" }),
  b("k", null, "code", "print(1)\n  x", { language: "py" }),
  b("k2", null, "code", "plain"),
  b("d", null, "divider", ""),
  b("x", null, "html", "<div>raw</div>"),
  b("q", null, "quote", "legacy"),
  b("q1", "q", "code", "inner", { language: "sh" }),
  b("tb", null, "table", "A | B", { header: ["A", "**B**"], alignments: ["left", null] }),
  b("r1", "tb", "table_row", "1 | a|b", { cells: ["1", "a|b"] }),
  b("r2", "tb", "table_row", "3 | `4`", { cells: ["3", "`4`"] }),
]

const noMint = () => {
  throw new Error("minted a row id")
}

describe("block mapping", () => {
  it("maps each server type to its editor block", () => {
    const { blocks, rowIds } = toEditorBlocks(STORED)
    const byId = new Map<string, EditorBlockLike>()
    const walk = (list: EditorBlockLike[]) =>
      list.forEach((x) => {
        byId.set(x.id, x)
        walk(x.children)
      })
    walk(blocks)
    expect(byId.get("h")).toMatchObject({ type: "heading", props: { level: 5 } })
    expect(byId.get("l")).toMatchObject({ type: "bulletListItem" })
    expect(byId.get("l1")).toMatchObject({ type: "numberedListItem" })
    expect(byId.get("t")).toMatchObject({ type: "checkListItem", props: { checked: true } })
    expect(byId.get("g")).toMatchObject({ type: "toggleListItem" })
    expect(byId.get("c")).toMatchObject({ type: "callout", props: { variant: "warning" } })
    expect(byId.get("k")).toMatchObject({ type: "codeBlock", props: { language: "py" }, content: "print(1)\n  x" })
    expect(byId.get("k2")).toMatchObject({ type: "codeBlock", props: { language: "text" } })
    expect(byId.get("d")).toMatchObject({ type: "divider" })
    expect(byId.get("x")).toMatchObject({ type: "raw", props: { source: "<div>raw</div>" } })
    expect(byId.get("q")!.children.map((x) => x.id)).toEqual(["q1"])
    expect(byId.get("tb")!.children).toEqual([])
    expect(rowIds.get("tb")).toEqual(["r1", "r2"])
    expect(byId.has("r1")).toBe(false)
  })

  it("keeps a stored marker when the list kind is unchanged, and resets it when it flips", () => {
    const previous = [b("a", null, "list", "a", { ordered: false, marker: "*" }), b("n", null, "list", "n", { ordered: true, marker: "3)" })]
    const blocks: EditorBlockLike[] = [
      { id: "a", type: "bulletListItem", props: {}, content: [], children: [] },
      { id: "n", type: "bulletListItem", props: {}, content: [], children: [] },
      { id: "z", type: "numberedListItem", props: {}, content: [], children: [] },
    ]
    const { tree } = toSyncTree(blocks, previous, new Map(), noMint)
    expect(tree.map((x) => x.properties)).toEqual([
      { ordered: false, marker: "*" },
      { ordered: false, marker: "-" },
      { ordered: true, marker: "1." },
    ])
  })

  it("matches table rows by position, minting ids for new rows once", () => {
    const { tree: canonical, rowIds } = canonicalTree(STORED)
    const table = toEditorBlocks(canonical).blocks.find((x) => x.id === "tb")!
    const content = table.content as { rows: { cells: unknown[] }[] }
    const grown: EditorBlockLike = { ...table, content: { ...content, rows: [...content.rows, { cells: [[], []] }] } }
    let minted = 0
    const mint = () => `new${++minted}`
    const first = toSyncTree([grown], canonical, rowIds, mint)
    const second = toSyncTree([grown], canonical, first.rowIds, mint)
    const rows = (tree: SyncBlock[]) => tree.filter((x) => x.type === "table_row").map((x) => x.id)
    expect(rows(first.tree)).toEqual(["r1", "r2", "new1"])
    expect(rows(second.tree)).toEqual(["r1", "r2", "new1"])
    expect(minted).toBe(1)
    const tableBlock = first.tree.find((x) => x.id === "tb")!
    expect(tableBlock.properties).toEqual({ header: ["A", "**B**"], alignments: ["left", null] })
  })

  it("pads the stored alignments with null for a new column", () => {
    const { tree: canonical, rowIds } = canonicalTree(STORED)
    const table = toEditorBlocks(canonical).blocks.find((x) => x.id === "tb")!
    const content = table.content as { rows: { cells: unknown[] }[] }
    const wider: EditorBlockLike = {
      ...table,
      content: { ...content, rows: content.rows.map((row) => ({ cells: [...row.cells, []] })) },
    }
    const { tree } = toSyncTree([wider], canonical, rowIds, noMint)
    expect(tree.find((x) => x.id === "tb")!.properties).toEqual({ header: ["A", "**B**", ""], alignments: ["left", null, null] })
  })

  it("sends every key a type models, so a cleared value clears", () => {
    const { tree } = toSyncTree(
      [{ id: "k", type: "codeBlock", props: { language: "text" }, content: [{ type: "text", text: "x", styles: {} }], children: [] }],
      [b("k", null, "code", "x", { language: "py" })],
      new Map(),
      noMint,
    )
    expect(tree[0]!.properties).toEqual({ language: "text" })
  })

  it("canonicalises idempotently", () => {
    const once = canonicalTree(STORED).tree
    expect(treesEqual(canonicalTree(once).tree, once)).toBe(true)
  })

  it("asks for no write when a stored page is loaded into the editor", async () => {
    const { tree: canonical, rowIds } = canonicalTree(STORED)
    let editor!: PageEditorInstance
    function Probe() {
      editor = useCreateBlockNote({
        schema: pageSchema,
        trailingBlock: false,
        initialContent: toEditorBlocks(canonical).blocks as never,
      })
      return <BlockNoteView editor={editor} />
    }
    render(<Probe />)
    await act(async () => {})
    const { tree: desired } = toSyncTree(editor.document as unknown as EditorBlockLike[], canonical, rowIds, noMint)
    expect(nextOp(canonical, desired)).toBeNull()
  })
})
````


- [ ] **Step 2: Run it to verify it fails**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/block-mapping.test.tsx`
Expected: FAIL — `Failed to resolve import "../lib/block-mapping"`.


- [ ] **Step 3: Write the module**


`frontend/src/features/notes/lib/block-mapping.ts`:

````ts
import { isCalloutVariant } from "./block-properties"
import { emitInline, parseInline, type InlineNode } from "./inline-markdown"
import type { BlockRow } from "@/hooks/api"
import type { SyncBlock, SyncTree } from "./sync-tree"

/** The fields of an editor block this module reads and writes. The editor's
 *  own `Block` satisfies it, and so does what `toEditorBlocks` returns, which
 *  is what lets the snapshot be canonicalised with no editor running. */
export interface EditorBlockLike {
  id: string
  type: string
  props: Record<string, unknown>
  content?: unknown
  children: EditorBlockLike[]
}

/** Per table block, its `table_row` ids in row order. Rows have no identity
 *  in the editor, so they are matched to server rows by position. */
export type TableRowIds = Map<string, string[]>

const DEFAULT_BULLET = "-"
const DEFAULT_ORDERED = "1."
const ORDERED_MARKER = /^\d+[.)]$/

function inline(text: string): InlineNode[] {
  return parseInline(text)
}

function contentOf(content: unknown): InlineNode[] {
  return Array.isArray(content) ? (content as InlineNode[]) : []
}

function plainText(content: unknown): string {
  if (typeof content === "string") return content
  return contentOf(content)
    .map((n) => (n.type === "text" ? n.text : ""))
    .join("")
}

interface TableCellLike {
  type: "tableCell"
  content: InlineNode[]
}

interface TableContentLike {
  type: "tableContent"
  headerRows?: number
  rows: { cells: (InlineNode[] | TableCellLike)[] }[]
}

function cellText(cell: InlineNode[] | TableCellLike): string {
  return emitInline(Array.isArray(cell) ? cell : cell.content)
}

function childrenByParent(tree: SyncTree): Map<string | null, SyncBlock[]> {
  const map = new Map<string | null, SyncBlock[]>()
  for (const block of tree) {
    const list = map.get(block.parentId)
    if (list) list.push(block)
    else map.set(block.parentId, [block])
  }
  return map
}

/** The server tree as editor blocks, plus each table's row ids. */
export function toEditorBlocks(tree: SyncTree): { blocks: EditorBlockLike[]; rowIds: TableRowIds } {
  const byParent = childrenByParent(tree)
  const rowIds: TableRowIds = new Map()
  const build = (block: SyncBlock): EditorBlockLike => {
    const props = block.properties ?? {}
    const kids = (byParent.get(block.id) ?? []).filter((k) => k.type !== "table_row")
    const children = kids.map(build)
    const base = { id: block.id, children }
    switch (block.type) {
      case "heading": {
        const level = Number(props.level)
        return { ...base, type: "heading", props: { level: level >= 1 && level <= 6 ? level : 1 }, content: inline(block.text) }
      }
      case "list":
        return {
          ...base,
          type: props.ordered === true ? "numberedListItem" : "bulletListItem",
          props: {},
          content: inline(block.text),
        }
      case "todo":
        return { ...base, type: "checkListItem", props: { checked: props.checked === true }, content: inline(block.text) }
      case "toggle":
        return { ...base, type: "toggleListItem", props: {}, content: inline(block.text) }
      case "quote":
        return { ...base, type: "quote", props: {}, content: inline(block.text) }
      case "callout": {
        const variant = isCalloutVariant(props.variant) ? props.variant : "info"
        return { ...base, type: "callout", props: { variant }, content: inline(block.text) }
      }
      case "code":
        return {
          ...base,
          type: "codeBlock",
          props: { language: typeof props.language === "string" && props.language ? props.language : "text" },
          content: block.text,
        }
      case "divider":
        return { ...base, type: "divider", props: {}, content: undefined }
      case "html":
        return { ...base, type: "raw", props: { source: block.text }, content: undefined }
      case "table": {
        const rows = (byParent.get(block.id) ?? []).filter((k) => k.type === "table_row")
        rowIds.set(block.id, rows.map((r) => r.id))
        const header = Array.isArray(props.header) ? (props.header as string[]) : []
        const width = Math.max(header.length, ...rows.map((r) => ((r.properties?.cells as string[]) ?? []).length), 1)
        const pad = (cells: string[]) => Array.from({ length: width }, (_, i) => inline(cells[i] ?? ""))
        const content: TableContentLike = {
          type: "tableContent",
          headerRows: 1,
          rows: [{ cells: pad(header) }, ...rows.map((r) => ({ cells: pad((r.properties?.cells as string[]) ?? []) }))],
        }
        return { ...base, type: "table", props: {}, content }
      }
      default:
        return { ...base, type: "paragraph", props: {}, content: inline(block.text) }
    }
  }
  return { blocks: (byParent.get(null) ?? []).map(build), rowIds }
}

/** The editor's document as the server tree it asks for, in pre-order.
 *  `previous` is the canonical snapshot: a list item keeps its stored marker
 *  spelling and a table its column alignments, which the editor does not
 *  model. New table rows take ids from `mintId`, recorded in the returned
 *  `rowIds` so the next conversion reuses them. */
export function toSyncTree(
  blocks: EditorBlockLike[],
  previous: SyncTree,
  rowIds: TableRowIds,
  mintId: () => string,
): { tree: SyncBlock[]; rowIds: TableRowIds } {
  const before = new Map(previous.map((b) => [b.id, b]))
  const nextRowIds: TableRowIds = new Map()
  const out: SyncBlock[] = []
  const markerFor = (id: string, ordered: boolean): string => {
    const stored = before.get(id)
    const marker = stored?.type === "list" ? stored.properties?.marker : undefined
    if (typeof marker === "string" && ORDERED_MARKER.test(marker) === ordered) return marker
    return ordered ? DEFAULT_ORDERED : DEFAULT_BULLET
  }
  const walk = (block: EditorBlockLike, parentId: string | null) => {
    const text = () => emitInline(contentOf(block.content))
    const push = (type: string, body: string, properties: SyncBlock["properties"]) =>
      out.push({ id: block.id, parentId, type, text: body, properties })
    switch (block.type) {
      case "heading":
        push("heading", text(), { level: Number(block.props.level) || 1 })
        break
      case "bulletListItem":
        push("list", text(), { ordered: false, marker: markerFor(block.id, false) })
        break
      case "numberedListItem":
        push("list", text(), { ordered: true, marker: markerFor(block.id, true) })
        break
      case "checkListItem":
        push("todo", text(), { checked: block.props.checked === true })
        break
      case "toggleListItem":
        push("toggle", text(), null)
        break
      case "quote":
        push("quote", text(), null)
        break
      case "callout":
        push("callout", text(), { variant: String(block.props.variant) })
        break
      case "codeBlock":
        push("code", plainText(block.content), { language: String(block.props.language || "text") })
        break
      case "divider":
        push("divider", "", null)
        break
      case "raw":
        push("html", String(block.props.source ?? ""), null)
        break
      case "table": {
        const table = block.content as TableContentLike
        const [head, ...rows] = table.rows
        const header = (head?.cells ?? []).map(cellText)
        const stored = before.get(block.id)?.properties?.alignments
        const alignments = header.map((_, i) => (Array.isArray(stored) ? (stored[i] ?? null) : null))
        push("table", header.join(" | "), { header, alignments })
        const known = rowIds.get(block.id) ?? []
        const ids: string[] = []
        rows.forEach((row, i) => {
          const id = known[i] ?? mintId()
          ids.push(id)
          const cells = row.cells.map(cellText)
          out.push({ id, parentId: block.id, type: "table_row", text: cells.join(" | "), properties: { cells } })
        })
        nextRowIds.set(block.id, ids)
        break
      }
      default:
        push("paragraph", text(), null)
    }
    for (const child of block.children) walk(child, block.id)
  }
  for (const block of blocks) walk(block, null)
  return { tree: out, rowIds: nextRowIds }
}

/** The server tree in the form the editor would ask for it: what every
 *  comparison is made in, so a stored spelling the editor writes differently
 *  never reads as an edit. */
export function canonicalTree(tree: SyncTree): { tree: SyncBlock[]; rowIds: TableRowIds } {
  const { blocks, rowIds } = toEditorBlocks(tree)
  let n = 0
  const { tree: out } = toSyncTree(blocks, tree, rowIds, () => {
    throw new Error(`canonicalTree minted a row id (${++n}); a table row lost its id`)
  })
  return { tree: out, rowIds }
}

/** A page read's flat rows as a tree in pre-order: children grouped under
 *  their parent and ordered by `order_index`. */
export function fromPageBlocks(rows: readonly BlockRow[]): SyncBlock[] {
  const byParent = new Map<string | null, BlockRow[]>()
  for (const row of rows) {
    const list = byParent.get(row.parent_id)
    if (list) list.push(row)
    else byParent.set(row.parent_id, [row])
  }
  const out: SyncBlock[] = []
  const walk = (parent: string | null) => {
    const kids = [...(byParent.get(parent) ?? [])].sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0))
    for (const row of kids) {
      out.push({ id: row.block_id, parentId: row.parent_id, type: row.type ?? "paragraph", text: row.text, properties: row.properties })
      walk(row.block_id)
    }
  }
  walk(null)
  return out
}
````


- [ ] **Step 4: Run the test to verify it passes**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/block-mapping.test.tsx`
Expected: PASS, 7 tests.


- [ ] **Step 5: Typecheck**


Run (from `frontend/`): `npm run typecheck`
Expected: exit 0.


- [ ] **Step 6: Commit**


From the repo root:

```bash
git add frontend/src/features/notes/lib/block-mapping.ts frontend/src/features/notes/__tests__/block-mapping.test.tsx
git commit -m "feat(notes): map page blocks to editor blocks"
```



### Task 7: The nesting guard

**Files:**
- Create: `frontend/src/features/notes/lib/nesting-guard.ts`
- Test: `frontend/src/features/notes/__tests__/nesting-guard.test.tsx`

**Interfaces:**
- Consumes: `pageSchema`, `PageEditorInstance` (Task 2) in the test only.
- Produces: `nestingViolations`, `addsNestingViolation` (Contracts, Task 7).

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3


- [ ] **Step 1: Write the failing test**


`frontend/src/features/notes/__tests__/nesting-guard.test.tsx`:

````tsx
import { act, render } from "@testing-library/react"
import { expect, it } from "vitest"
import { useCreateBlockNote } from "@blocknote/react"
import { BlockNoteView } from "@blocknote/shadcn"
import { pageSchema, type PageEditorInstance } from "../lib/editor-schema"
import { addsNestingViolation } from "../lib/nesting-guard"

it("refuses a new child under a non-container and allows it under a list item", async () => {
  let editor!: PageEditorInstance
  function Probe() {
    editor = useCreateBlockNote({
      schema: pageSchema,
      trailingBlock: false,
      initialContent: [
        { id: "p", type: "paragraph", content: "p" },
        { id: "q", type: "paragraph", content: "q" },
        { id: "l", type: "bulletListItem", content: "l", children: [{ id: "l1", type: "paragraph", content: "l1" }] },
        { id: "m", type: "paragraph", content: "m" },
        { id: "quote", type: "quote", content: "legacy", children: [{ id: "qc", type: "codeBlock", content: "x" }] },
      ],
    })
    return <BlockNoteView editor={editor} />
  }
  render(<Probe />)
  await act(async () => {})
  editor.onBeforeChange(({ tr }) => (addsNestingViolation(tr.before, tr.doc) ? false : undefined))
  const shape = () => JSON.stringify(editor.document.map((x) => [x.id, x.type, x.children.map((c) => c.id)]))
  const start = shape()

  editor.setTextCursorPosition("q")
  editor.nestBlock()
  expect(shape()).toBe(start)

  editor.updateBlock("l", { type: "paragraph" })
  expect(shape()).toBe(start)

  editor.updateBlock("p", { children: [{ id: "px", type: "paragraph", content: "x" }] })
  expect(shape()).toBe(start)

  editor.setTextCursorPosition("m")
  editor.nestBlock()
  expect(editor.getBlock("l")!.children.map((c) => c.id)).toEqual(["l1", "m"])

  editor.updateBlock("qc", { content: "edited" })
  expect(editor.getBlock("qc")!.content).toMatchObject([{ text: "edited" }])

  editor.updateBlock("l", { type: "checkListItem", props: { checked: true } })
  expect(editor.getBlock("l")!.type).toBe("checkListItem")
})
````


- [ ] **Step 2: Run it to verify it fails**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/nesting-guard.test.tsx`
Expected: FAIL — `Failed to resolve import "../lib/nesting-guard"`.


- [ ] **Step 3: Write the guard**


It types the ProseMirror node structurally rather than importing `prosemirror-model`, which is only a transitive dependency.

`frontend/src/features/notes/lib/nesting-guard.ts`:

````ts
/** The slice of a ProseMirror node this module reads, so it needs no import
 *  of the editor's internals. */
interface DocNode {
  type: { name: string }
  attrs: Record<string, unknown>
  firstChild: DocNode | null
  childCount: number
  child(index: number): DocNode
  forEach(visit: (node: DocNode) => void): void
  descendants(visit: (node: DocNode) => boolean | void): void
}

/** The editor block types that may hold children on a page: the editor's
 *  names for `list`, `todo` and `toggle`. */
const EDITOR_CONTAINERS: ReadonlySet<string> = new Set([
  "bulletListItem",
  "numberedListItem",
  "checkListItem",
  "toggleListItem",
])

/** Every `parent>child` id pair in `doc` whose parent may not hold children
 *  on a page. */
export function nestingViolations(doc: DocNode): Set<string> {
  const out = new Set<string>()
  doc.descendants((node) => {
    if (node.type.name !== "blockContainer") return true
    const content = node.firstChild
    const group = node.childCount > 1 ? node.child(1) : null
    if (content && group && !EDITOR_CONTAINERS.has(content.type.name)) {
      group.forEach((child) => out.add(`${node.attrs.id}>${child.attrs.id}`))
    }
    return true
  })
  return out
}

/** True when `after` breaks the page nesting rule somewhere `before` did not.
 *  Comparing against the previous document lets a shape already on the page
 *  (a quote holding a code block) keep loading and taking edits, while no
 *  edit can make a new one: not an indent, a drag, a paste, nor a retype of a
 *  list item that has children. */
export function addsNestingViolation(before: DocNode, after: DocNode): boolean {
  const existing = nestingViolations(before)
  for (const pair of nestingViolations(after)) if (!existing.has(pair)) return true
  return false
}
````


- [ ] **Step 4: Run the test to verify it passes**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/nesting-guard.test.tsx`
Expected: PASS, 1 test.


- [ ] **Step 5: Commit**


From the repo root:

```bash
git add frontend/src/features/notes/lib/nesting-guard.ts frontend/src/features/notes/__tests__/nesting-guard.test.tsx
git commit -m "feat(notes): refuse new nesting under non-containers"
```



### Task 8: The page transport

**Files:**
- Create: `frontend/src/features/notes/lib/page-transport.ts`
- Test: `frontend/src/features/notes/__tests__/page-transport.test.ts`

**Interfaces:**
- Consumes: `canonicalTree`, `fromPageBlocks` (Task 6); `PageTransport`, `SyncTransportError` (Task 5); `SyncOp` (Task 4); `apiFetchWithHeaders`, `ApiError` from `@/lib/api` and `pageQuery` from `@/hooks/api` (existing).
- Produces: `createPageTransport`, `KEEPALIVE_MAX_BODY` (Contracts, Task 8).

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4


- [ ] **Step 1: Write the failing test**


`frontend/src/features/notes/__tests__/page-transport.test.ts`:

````ts
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>()
  return { ...actual, apiFetch: vi.fn(), apiFetchWithHeaders: vi.fn() }
})

import { ApiError, apiFetch, apiFetchWithHeaders } from "@/lib/api"
import { createPageTransport, KEEPALIVE_MAX_BODY } from "../lib/page-transport"
import { SyncTransportError } from "../lib/page-sync"

const answer = (data: unknown, headers: Record<string, string> = {}) => ({ data, headers: new Headers(headers) })

beforeEach(() => {
  vi.mocked(apiFetchWithHeaders).mockReset()
  vi.mocked(apiFetch).mockReset()
})

describe("page transport", () => {
  it("sends inserts as one batch with the precondition and keepalive", async () => {
    vi.mocked(apiFetchWithHeaders).mockResolvedValue(answer({ content_hash: "h2" }) as never)
    const blocks = [{ block_id: "n", type: "paragraph", text: "x", properties: null, parent_id: null, after_block_id: null }]
    await expect(createPageTransport("p1").send({ kind: "insert", blocks }, "h1")).resolves.toBe("h2")
    const [path, init] = vi.mocked(apiFetchWithHeaders).mock.calls[0]!
    expect(path).toBe("/pages/p1/blocks/batch")
    expect(init).toMatchObject({ method: "POST", keepalive: true })
    expect(JSON.parse(String(init!.body))).toEqual({ blocks, expected_hash: "h1" })
  })

  it("maps move and update to their routes", async () => {
    vi.mocked(apiFetchWithHeaders).mockResolvedValue(answer({ content_hash: "h2" }) as never)
    const t = createPageTransport("p1")
    await t.send({ kind: "move", id: "b", parentId: "l", afterId: null }, "h1")
    await t.send({ kind: "update", id: "b", type: "todo", text: "t", properties: { checked: true } }, "h2")
    const calls = vi.mocked(apiFetchWithHeaders).mock.calls
    expect(calls[0]![0]).toBe("/pages/p1/blocks/b/move")
    expect(JSON.parse(String(calls[0]![1]!.body))).toEqual({ new_parent_id: "l", after_block_id: null, expected_hash: "h1" })
    expect(calls[1]![0]).toBe("/pages/p1/blocks/b")
    expect(calls[1]![1]).toMatchObject({ method: "PATCH" })
    expect(JSON.parse(String(calls[1]![1]!.body))).toEqual({ text: "t", type: "todo", properties: { checked: true }, expected_hash: "h2" })
  })

  it("takes a delete's new hash from X-Content-Hash", async () => {
    vi.mocked(apiFetchWithHeaders).mockResolvedValue(answer(undefined, { "X-Content-Hash": "h9" }) as never)
    await expect(createPageTransport("p1").send({ kind: "delete", id: "b" }, "h1")).resolves.toBe("h9")
    expect(vi.mocked(apiFetchWithHeaders).mock.calls[0]![0]).toBe("/pages/p1/blocks/b?expected_hash=h1")
  })

  it("drops keepalive for a body over the browser's budget", async () => {
    vi.mocked(apiFetchWithHeaders).mockResolvedValue(answer({ content_hash: "h2" }) as never)
    const big = "x".repeat(KEEPALIVE_MAX_BODY)
    await createPageTransport("p1").send({ kind: "update", id: "b", type: "paragraph", text: big, properties: null }, "h1")
    expect(vi.mocked(apiFetchWithHeaders).mock.calls[0]![1]).toMatchObject({ keepalive: false })
  })

  it("carries the HTTP status of a refusal, and none for a network failure", async () => {
    vi.mocked(apiFetchWithHeaders).mockRejectedValueOnce(new ApiError("stale", 409))
    const refused = await createPageTransport("p1")
      .send({ kind: "delete", id: "b" }, "h1")
      .catch((e: unknown) => e)
    expect(refused).toBeInstanceOf(SyncTransportError)
    expect((refused as SyncTransportError).status).toBe(409)

    vi.mocked(apiFetchWithHeaders).mockRejectedValueOnce(new TypeError("Failed to fetch"))
    const offline = await createPageTransport("p1")
      .send({ kind: "delete", id: "b" }, "h1")
      .catch((e: unknown) => e)
    expect((offline as SyncTransportError).status).toBeUndefined()
  })

  it("reads the page back canonicalised", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      id: "p1",
      project: "personal",
      parent_id: null,
      order_index: 0,
      title: null,
      content_hash: "h5",
      properties: null,
      content: null,
      blocks: [
        { id: "b", parent_id: null, order_index: 1, type: "paragraph", text: "__x__", properties: null, char_start: 0, char_end: 5, source: "__x__" },
        { id: "a", parent_id: null, order_index: 0, type: "list", text: "a", properties: { ordered: false, marker: "*", number: 1 }, char_start: 0, char_end: 3, source: "* a" },
      ],
    })
    await expect(createPageTransport("p1").read()).resolves.toEqual({
      hash: "h5",
      tree: [
        { id: "a", parentId: null, type: "list", text: "a", properties: { ordered: false, marker: "*" } },
        { id: "b", parentId: null, type: "paragraph", text: "**x**", properties: null },
      ],
    })
  })
})
````


- [ ] **Step 2: Run it to verify it fails**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/page-transport.test.ts`
Expected: FAIL — `Failed to resolve import "../lib/page-transport"`.


- [ ] **Step 3: Write the transport**


`frontend/src/features/notes/lib/page-transport.ts`:

````ts
import { ApiError, apiFetchWithHeaders } from "@/lib/api"
import { pageQuery } from "@/hooks/api"
import { canonicalTree, fromPageBlocks } from "./block-mapping"
import { SyncTransportError, type PageTransport } from "./page-sync"
import type { SyncOp } from "./sync-tree"

/** Browsers cap the bodies of all in-flight keepalive requests together at
 *  64 KiB; one write stays under it with room for the headers. */
export const KEEPALIVE_MAX_BODY = 60_000

function toTransportError(error: unknown): SyncTransportError {
  if (error instanceof ApiError) return new SyncTransportError(error.message, error.status)
  return new SyncTransportError(error instanceof Error ? error.message : String(error))
}

/** The page block verbs as the sync engine's transport. Every write is sent
 *  with `keepalive` when it fits, so the one in flight when the tab closes
 *  still lands. */
export function createPageTransport(pageId: string): PageTransport {
  const send = async (path: string, method: string, body?: object) => {
    const json = body === undefined ? undefined : JSON.stringify(body)
    const keepalive = (json?.length ?? 0) <= KEEPALIVE_MAX_BODY
    return apiFetchWithHeaders<{ content_hash?: string } | undefined>(path, { method, body: json, keepalive })
  }
  return {
    async read() {
      try {
        const page = await pageQuery(pageId).queryFn()
        return { tree: canonicalTree(fromPageBlocks(page.blocks)).tree, hash: page.content_hash ?? "" }
      } catch (error) {
        throw toTransportError(error)
      }
    },
    async send(op: SyncOp, expectedHash: string) {
      const expected_hash = expectedHash === "" ? undefined : expectedHash
      try {
        switch (op.kind) {
          case "insert": {
            const { data } = await send(`/pages/${pageId}/blocks/batch`, "POST", { blocks: op.blocks, expected_hash })
            return data?.content_hash ?? ""
          }
          case "move": {
            const { data } = await send(`/pages/${pageId}/blocks/${op.id}/move`, "POST", {
              new_parent_id: op.parentId,
              after_block_id: op.afterId,
              expected_hash,
            })
            return data?.content_hash ?? ""
          }
          case "update": {
            const { data } = await send(`/pages/${pageId}/blocks/${op.id}`, "PATCH", {
              text: op.text,
              type: op.type,
              properties: op.properties,
              expected_hash,
            })
            return data?.content_hash ?? ""
          }
          case "delete": {
            // DELETE carries no body, so the precondition rides the query and
            // the new hash comes back in a header.
            const query = expected_hash ? `?expected_hash=${encodeURIComponent(expected_hash)}` : ""
            const { headers } = await send(`/pages/${pageId}/blocks/${op.id}${query}`, "DELETE")
            const hash = headers.get("X-Content-Hash")
            if (hash === null) throw new SyncTransportError("the delete answered no content hash")
            return hash
          }
        }
      } catch (error) {
        throw error instanceof SyncTransportError ? error : toTransportError(error)
      }
    },
  }
}
````


- [ ] **Step 4: Run the test to verify it passes**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/page-transport.test.ts`
Expected: PASS, 6 tests.


- [ ] **Step 5: Run the path guard**


Run (from `frontend/`): `npx vitest run src/lib/__tests__/api-paths.test.ts`
Expected: PASS — no call site spells `/api/v1`.


- [ ] **Step 6: Commit**


From the repo root:

```bash
git add frontend/src/features/notes/lib/page-transport.ts frontend/src/features/notes/__tests__/page-transport.test.ts
git commit -m "feat(notes): send sync writes over the page routes"
```



### Task 9: `usePageSync`

**Files:**
- Create: `frontend/src/features/notes/use-page-sync.ts`
- Test: `frontend/src/features/notes/__tests__/use-page-sync.test.tsx`

**Interfaces:**
- Consumes: `canonicalTree`, `fromPageBlocks`, `toEditorBlocks`, `toSyncTree`, `EditorBlockLike`, `TableRowIds` (Task 6); `PageSync`, `PageTransport`, `SyncStatus` (Task 5); `createPageTransport` (Task 8); `SyncTree` (Task 4); `pageQuery`, `PageView` (existing).
- Produces: `usePageSync`, `PageSyncBinding`, `TEXT_IDLE_MS`, `resetPageSyncEngines` (Contracts, Task 9).

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5


- [ ] **Step 1: Write the failing test**


The engine is released from `onSettled`, never from a status listener: statuses are emitted from inside the drain, while `pending` still reads true, so a release attempted there never happens for a write that was in flight at unmount. The cache-removal cases give their `QueryClient` an infinite `gcTime` on purpose: `runAllTimersAsync` also fires TanStack Query's five-minute collection timer, which would remove the entry on its own and let the test pass with the removal deleted (measured in the prototype).

`frontend/src/features/notes/__tests__/use-page-sync.test.tsx`:

````tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("darkraise-ui/components/sonner", () => ({ toast: { error: vi.fn() } }))

import { toast } from "darkraise-ui/components/sonner"
import type { PageView } from "@/hooks/api"
import type { EditorBlockLike } from "../lib/block-mapping"
import { SyncTransportError, type PageTransport } from "../lib/page-sync"
import type { SyncOp } from "../lib/sync-tree"
import { resetPageSyncEngines, TEXT_IDLE_MS, usePageSync } from "../use-page-sync"

const PAGE: PageView = {
  id: "p1",
  project: "personal",
  parent_id: null,
  order_index: 0,
  title: "Plans",
  content_hash: "h0",
  blocks: [
    { block_id: "a", type: "paragraph", text: "a", order_index: 0, char_span: null, parent_id: null, properties: null, source: "a" },
  ],
}

const para = (id: string, text: string): EditorBlockLike => ({
  id,
  type: "paragraph",
  props: {},
  content: [{ type: "text", text, styles: {} }],
  children: [],
})

function transport(fail?: number, latencyMs = 0) {
  const sent: SyncOp[] = []
  let n = 0
  const t: PageTransport = {
    read: async () => ({ tree: [], hash: "x" }),
    send: async (op) => {
      sent.push(op)
      if (latencyMs > 0) await new Promise((resolve) => setTimeout(resolve, latencyMs))
      if (fail !== undefined) throw new SyncTransportError(`status ${fail}`, fail)
      return `h${++n}`
    },
  }
  return { t, sent }
}

let qc: QueryClient
function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.useFakeTimers()
  qc = new QueryClient()
  vi.mocked(toast.error).mockReset()
})

afterEach(() => {
  resetPageSyncEngines()
  vi.useRealTimers()
})

describe("usePageSync", () => {
  it("mounts the page's blocks and sends typing after the idle pause", async () => {
    const { t, sent } = transport()
    const { result } = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    expect(result.current.initialBlocks.map((b) => b.id)).toEqual(["a"])
    act(() => result.current.onDocumentChange([para("a", "ab")]))
    await act(async () => vi.advanceTimersByTimeAsync(TEXT_IDLE_MS - 1))
    expect(sent).toEqual([])
    await act(async () => vi.advanceTimersByTimeAsync(1))
    expect(sent).toEqual([{ kind: "update", id: "a", type: "paragraph", text: "ab", properties: null }])
    expect(result.current.status).toEqual({ kind: "saved" })
  })

  it("sends a structural change at once", async () => {
    const { t, sent } = transport()
    const { result } = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    await act(async () => result.current.onDocumentChange([para("a", "a"), para("b", "b")]))
    expect(sent.map((op) => op.kind)).toEqual(["insert"])
  })

  it("flushes pending typing when the tab is hidden", async () => {
    const { t, sent } = transport()
    const { result } = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    act(() => result.current.onDocumentChange([para("a", "ab")]))
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden")
    await act(async () => document.dispatchEvent(new Event("visibilitychange")))
    expect(sent).toHaveLength(1)
  })

  it("asks before leaving while work is unsent", () => {
    const { t } = transport()
    const { result } = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    const quiet = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(quiet)
    expect(quiet.defaultPrevented).toBe(false)
    act(() => result.current.onDocumentChange([para("a", "ab")]))
    const leaving = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(leaving)
    expect(leaving.defaultPrevented).toBe(true)
  })

  it("keeps draining after unmount and hands a remount the unsent work", async () => {
    const { t, sent } = transport()
    const first = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    act(() => first.result.current.onDocumentChange([para("a", "draft")]))
    first.unmount()
    const again = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    expect(again.result.current.initialBlocks[0]!.content).toEqual([{ type: "text", text: "draft", styles: {} }])
    await act(async () => vi.runAllTimersAsync())
    expect(sent).toHaveLength(1)
  })

  it("forgets the page's cached read once its engine is released", async () => {
    const { t } = transport()
    // Never collected on its own, so only the release can remove it.
    qc = new QueryClient({ defaultOptions: { queries: { gcTime: Infinity } } })
    qc.setQueryData(["page", "p1"], PAGE)
    const view = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    await act(async () => view.result.current.onDocumentChange([para("a", "a"), para("b", "b")]))
    view.unmount()
    await act(async () => vi.runAllTimersAsync())
    expect(qc.getQueryData(["page", "p1"])).toBeUndefined()
  })

  it("releases an engine whose write was still in flight when its pane unmounted", async () => {
    const { t } = transport(undefined, 50)
    qc = new QueryClient({ defaultOptions: { queries: { gcTime: Infinity } } })
    qc.setQueryData(["page", "p1"], PAGE)
    const view = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    act(() => view.result.current.onDocumentChange([para("a", "a"), para("b", "b")]))
    view.unmount()
    expect(qc.getQueryData(["page", "p1"])).toBeDefined()
    await act(async () => vi.advanceTimersByTimeAsync(50))
    expect(qc.getQueryData(["page", "p1"])).toBeUndefined()
    const reopened = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    expect(reopened.result.current.initialBlocks.map((b) => b.id)).toEqual(["a"])
  })

  it("sends pending typing at once when the editor loses focus", async () => {
    const { t, sent } = transport()
    const { result } = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    act(() => result.current.onDocumentChange([para("a", "ab")]))
    await act(async () => result.current.flushNow())
    expect(sent).toHaveLength(1)
  })

  it("raises a toast when a page nobody is looking at fails to save", async () => {
    const { t } = transport(422)
    const view = renderHook(() => usePageSync(PAGE, 0, () => t), { wrapper })
    act(() => view.result.current.onDocumentChange([para("a", "ab")]))
    view.unmount()
    await act(async () => vi.runAllTimersAsync())
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith("“Plans” was not saved — status 422")
  })

  it("builds a fresh engine for a new generation after a discard", () => {
    const { t } = transport()
    const view = renderHook(({ gen }) => usePageSync(PAGE, gen, () => t), { wrapper, initialProps: { gen: 0 } })
    act(() => view.result.current.onDocumentChange([para("a", "local")]))
    act(() => view.result.current.discard())
    view.rerender({ gen: 1 })
    expect(view.result.current.initialBlocks[0]!.content).toEqual([{ type: "text", text: "a", styles: {} }])
  })
})
````


- [ ] **Step 2: Run it to verify it fails**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/use-page-sync.test.tsx`
Expected: FAIL — `Failed to resolve import "../use-page-sync"`.


- [ ] **Step 3: Write the hook**


Every mutation of an engine entry goes through a module function (`mount`, `unmount`, `mountBlocks`, `acceptDocument`, `discard`): the React Compiler lint rule `react-hooks/immutability` refuses a direct write to a value a hook returned.

`frontend/src/features/notes/use-page-sync.ts`:

````ts
import { useEffect, useMemo, useSyncExternalStore } from "react"
import { useQueryClient, type QueryClient } from "@tanstack/react-query"
import { toast } from "darkraise-ui/components/sonner"
import { pageQuery, type PageView } from "@/hooks/api"
import {
  canonicalTree,
  fromPageBlocks,
  toEditorBlocks,
  toSyncTree,
  type EditorBlockLike,
  type TableRowIds,
} from "./lib/block-mapping"
import { PageSync, type PageTransport, type SyncStatus } from "./lib/page-sync"
import { createPageTransport } from "./lib/page-transport"
import type { SyncTree } from "./lib/sync-tree"

/** How long typing may pause before the text it produced is saved. */
export const TEXT_IDLE_MS = 800

interface Entry {
  sync: PageSync
  rowIds: TableRowIds
  title: string
  mounted: number
  timer: ReturnType<typeof setTimeout> | null
  queryClient: QueryClient
}

/** One engine per page, outside React, so a page's unsaved work keeps
 *  draining after its pane unmounts and a page that is reopened mid-drain
 *  shows the work rather than the older server copy. */
const engines = new Map<string, Entry>()

function anyPending(): boolean {
  for (const entry of engines.values()) if (entry.sync.pending) return true
  return false
}

function flushEntry(entry: Entry) {
  if (entry.timer !== null) clearTimeout(entry.timer)
  entry.timer = null
  void entry.sync.flush()
}

function flushAll() {
  for (const entry of engines.values()) flushEntry(entry)
}

/** Discards a finished engine whose page nothing shows, together with the
 *  page's cached read: that read predates every edit the engine sent, and a
 *  page reopened from it would show old content and meet its own writes as a
 *  change made elsewhere. */
function release(pageId: string, entry: Entry) {
  if (entry.mounted !== 0 || entry.sync.pending || engines.get(pageId) !== entry) return
  engines.delete(pageId)
  entry.queryClient.removeQueries({ queryKey: pageQuery(pageId).queryKey, exact: true })
}

function acquire(
  page: PageView,
  createTransport: (pageId: string) => PageTransport,
  queryClient: QueryClient,
): Entry {
  const existing = engines.get(page.id)
  if (existing) return existing
  const { tree, rowIds } = canonicalTree(fromPageBlocks(page.blocks))
  const entry: Entry = {
    sync: new PageSync(tree, page.content_hash ?? "", createTransport(page.id)),
    rowIds,
    title: page.title?.trim() || "Untitled",
    mounted: 0,
    timer: null,
    queryClient,
  }
  entry.sync.subscribe((status) => {
    if (status.kind === "stopped" && entry.mounted === 0) {
      toast.error(`“${entry.title}” was not saved — ${status.message}`)
    }
  })
  entry.sync.onSettled(() => release(page.id, entry))
  engines.set(page.id, entry)
  return entry
}

function mount(entry: Entry) {
  entry.mounted++
}

function unmount(pageId: string, entry: Entry) {
  entry.mounted--
  flushEntry(entry)
  release(pageId, entry)
}

/** The editor blocks to mount, from the engine's desired tree: the server's
 *  copy for a fresh engine, the unsent work for one still draining. */
function mountBlocks(entry: Entry): EditorBlockLike[] {
  const { blocks, rowIds } = toEditorBlocks(entry.sync.desired)
  entry.rowIds = rowIds
  return blocks
}

function acceptDocument(entry: Entry, blocks: EditorBlockLike[]) {
  const before = entry.sync.desired
  const { tree, rowIds } = toSyncTree(blocks, entry.sync.snapshot, entry.rowIds, () => crypto.randomUUID())
  entry.rowIds = rowIds
  entry.sync.setDesired(tree)
  if (!sameShape(before, tree)) {
    flushEntry(entry)
    return
  }
  if (entry.timer !== null) clearTimeout(entry.timer)
  entry.timer = setTimeout(() => flushEntry(entry), TEXT_IDLE_MS)
}

function discard(pageId: string, entry: Entry) {
  if (entry.timer !== null) clearTimeout(entry.timer)
  if (engines.get(pageId) === entry) engines.delete(pageId)
}

/** Same blocks under the same parents in the same order with the same
 *  types: a change that keeps this is typing, anything else is structure. */
function sameShape(a: SyncTree, b: SyncTree): boolean {
  return a.length === b.length && a.every((x, i) => {
    const y = b[i]!
    return x.id === y.id && x.parentId === y.parentId && x.type === y.type
  })
}

export interface PageSyncBinding {
  initialBlocks: EditorBlockLike[]
  status: SyncStatus
  onDocumentChange: (blocks: EditorBlockLike[]) => void
  flushNow: () => void
  /** Drops the engine and any work it had not sent. */
  discard: () => void
}

/** Binds one mounted editor to its page's save engine. `generation` moves
 *  on a reload so a fresh engine is built from the fresh read. */
export function usePageSync(
  page: PageView,
  generation: number,
  createTransport: (pageId: string) => PageTransport = createPageTransport,
): PageSyncBinding {
  const queryClient = useQueryClient()
  const entry = useMemo(
    () => acquire(page, createTransport, queryClient),
    // The page's later reads must not rebuild the engine: the editor owns
    // the content once mounted, and only a reload replaces it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [page.id, generation],
  )

  const initialBlocks = useMemo(() => mountBlocks(entry), [entry])

  const status = useSyncExternalStore(
    (onChange) => entry.sync.subscribe(onChange),
    () => entry.sync.status,
  )

  useEffect(() => {
    mount(entry)
    return () => unmount(page.id, entry)
  }, [entry, page.id])

  useEffect(() => {
    const onHidden = () => {
      if (document.visibilityState === "hidden") flushAll()
    }
    const onLeave = (event: BeforeUnloadEvent) => {
      if (!anyPending()) return
      event.preventDefault()
      event.returnValue = ""
    }
    document.addEventListener("visibilitychange", onHidden)
    window.addEventListener("beforeunload", onLeave)
    return () => {
      document.removeEventListener("visibilitychange", onHidden)
      window.removeEventListener("beforeunload", onLeave)
    }
  }, [])

  return useMemo(
    () => ({
      initialBlocks,
      status,
      onDocumentChange: (blocks: EditorBlockLike[]) => acceptDocument(entry, blocks),
      flushNow: () => flushEntry(entry),
      discard: () => discard(page.id, entry),
    }),
    [entry, initialBlocks, page.id, status],
  )
}

/** Test hook: forget every engine between tests. */
export function resetPageSyncEngines() {
  for (const entry of engines.values()) if (entry.timer !== null) clearTimeout(entry.timer)
  engines.clear()
}
````


- [ ] **Step 4: Run the test to verify it passes**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/use-page-sync.test.tsx`
Expected: PASS, 10 tests.


- [ ] **Step 5: Lint the new file**


Run (from `frontend/`): `npx eslint src/features/notes/use-page-sync.ts`
Expected: no output.


- [ ] **Step 6: Commit**


From the repo root:

```bash
git add frontend/src/features/notes/use-page-sync.ts frontend/src/features/notes/__tests__/use-page-sync.test.tsx
git commit -m "feat(notes): bind the save engine to the editor"
```



### Task 10: The editor hooks: document mode and `usePageEditor`

**Files:**
- Create: `frontend/src/features/notes/use-document-mode.ts`
- Create: `frontend/src/features/notes/use-page-editor.ts`
- Test: `frontend/src/features/notes/__tests__/use-document-mode.test.tsx`
- Test: `frontend/src/features/notes/__tests__/use-page-editor.test.tsx`

**Interfaces:**
- Consumes: `pageSchema`, `PageEditorInstance` (Task 2); `CalloutVariant` (Task 1); `EditorBlockLike`, `toEditorBlocks` (Task 6); `addsNestingViolation` (Task 7).
- Produces: `useDocumentMode`, `DocumentMode`, `usePageEditor`, `pageSlashItems` (Contracts, Task 10).

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4


- [ ] **Step 1: Write the failing tests**


`frontend/src/features/notes/__tests__/use-document-mode.test.tsx`:

````tsx
import { act, renderHook } from "@testing-library/react"
import { afterEach, expect, it } from "vitest"
import { useDocumentMode } from "../use-document-mode"

afterEach(() => {
  delete document.documentElement.dataset.mode
})

it("reads the mode the theme provider writes and follows a change", async () => {
  const { result } = renderHook(() => useDocumentMode())
  expect(result.current).toBe("light")
  await act(async () => {
    document.documentElement.dataset.mode = "dark"
  })
  expect(result.current).toBe("dark")
})
````

`frontend/src/features/notes/__tests__/use-page-editor.test.tsx`:

````tsx
import { act, render } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { BlockNoteView } from "@blocknote/shadcn"
import { toEditorBlocks, type EditorBlockLike } from "../lib/block-mapping"
import type { PageEditorInstance } from "../lib/editor-schema"
import type { SyncBlock } from "../lib/sync-tree"
import { pageSlashItems, usePageEditor } from "../use-page-editor"

const b = (id: string, type: string, text: string, properties: SyncBlock["properties"] = null): SyncBlock => ({
  id,
  parentId: null,
  type,
  text,
  properties,
})

const BLOCKS: EditorBlockLike[] = toEditorBlocks([
  b("h1", "heading", "Plans", { level: 1 }),
  b("p1", "paragraph", "first"),
  b("h2", "heading", "Details", { level: 2 }),
  b("p2", "paragraph", "second"),
]).blocks

async function mountHook() {
  let editor!: PageEditorInstance
  function Probe() {
    editor = usePageEditor(BLOCKS)
    return <BlockNoteView editor={editor} />
  }
  render(<Probe />)
  await act(async () => {})
  return editor
}

describe("usePageEditor", () => {
  it("refuses an indent under a paragraph", async () => {
    const editor = await mountHook()
    editor.setTextCursorPosition("p1")
    editor.nestBlock()
    expect(editor.document.map((x) => x.id)).toEqual(["h1", "p1", "h2", "p2"])
  })

  it("offers the allowed blocks and one callout per variant", async () => {
    const editor = await mountHook()
    const titles = pageSlashItems(editor, "").map((item) => item.title)
    expect(titles).toEqual(
      expect.arrayContaining(["Paragraph", "Heading 1", "Heading 3", "Check List", "Toggle List", "Table", "Divider"]),
    )
    for (const hidden of ["Heading 4", "Emoji", "Image", "Video", "File", "Audio"]) expect(titles).not.toContain(hidden)
    expect(pageSlashItems(editor, "callout").map((item) => item.title)).toEqual([
      "Callout: info",
      "Callout: warning",
      "Callout: error",
      "Callout: success",
    ])
  })

  it("inserts a callout with the picked variant", async () => {
    const editor = await mountHook()
    editor.setTextCursorPosition("p2", "end")
    pageSlashItems(editor, "warning")[0]!.onItemClick()
    const callout = editor.document.find((x) => x.type === "callout")
    expect(callout?.props).toEqual({ variant: "warning" })
  })
})
````


- [ ] **Step 2: Run them to verify they fail**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/use-document-mode.test.tsx src/features/notes/__tests__/use-page-editor.test.tsx`
Expected: FAIL — `Failed to resolve import "../use-document-mode"` and `"../use-page-editor"`.


- [ ] **Step 3: Write the document-mode hook**


`frontend/src/features/notes/use-document-mode.ts`:

````ts
import { useSyncExternalStore } from "react"

export type DocumentMode = "light" | "dark"

function read(): DocumentMode {
  return document.documentElement.dataset.mode === "dark" ? "dark" : "light"
}

function subscribe(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange)
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-mode"] })
  return () => observer.disconnect()
}

/** The resolved colour mode darkraise-ui's ThemeProvider writes to
 *  `<html data-mode>`. Read from the document rather than through
 *  `useTheme()`, which throws outside a ThemeProvider, so the editor renders
 *  in any tree a test mounts it in. */
export function useDocumentMode(): DocumentMode {
  return useSyncExternalStore(subscribe, read, () => "light")
}
````


- [ ] **Step 4: Write the editor hook**


`frontend/src/features/notes/use-page-editor.ts`:

````ts
import { useEffect } from "react"
import { filterSuggestionItems, insertOrUpdateBlockForSlashMenu } from "@blocknote/core/extensions"
import {
  getDefaultReactSlashMenuItems,
  useCreateBlockNote,
  type DefaultReactSuggestionItem,
} from "@blocknote/react"
import type { EditorBlockLike } from "./lib/block-mapping"
import type { CalloutVariant } from "./lib/block-properties"
import { pageSchema, type PageEditorInstance } from "./lib/editor-schema"
import { addsNestingViolation } from "./lib/nesting-guard"

/** The built-in slash menu entries a page offers. Headings 4-6 stay
 *  loadable but are not offered; emoji and every file block are out. */
const SLASH_KEYS: ReadonlySet<string> = new Set([
  "paragraph",
  "heading",
  "heading_2",
  "heading_3",
  "bullet_list",
  "numbered_list",
  "check_list",
  "toggle_list",
  "quote",
  "code_block",
  "table",
  "divider",
])

const CALLOUT_ITEMS: readonly { variant: CalloutVariant; title: string }[] = [
  { variant: "info", title: "Callout: info" },
  { variant: "warning", title: "Callout: warning" },
  { variant: "error", title: "Callout: error" },
  { variant: "success", title: "Callout: success" },
]

/** The slash menu for `query`: the allowed built-ins plus one callout entry
 *  per variant. */
export function pageSlashItems(editor: PageEditorInstance, query: string): DefaultReactSuggestionItem[] {
  const builtIns = getDefaultReactSlashMenuItems(editor).filter((item) =>
    SLASH_KEYS.has((item as unknown as { key: string }).key),
  )
  const callouts: DefaultReactSuggestionItem[] = CALLOUT_ITEMS.map(({ variant, title }) => ({
    title,
    group: "Basic blocks",
    aliases: ["callout", "alert", variant],
    onItemClick: () => {
      insertOrUpdateBlockForSlashMenu(editor, { type: "callout", props: { variant } })
    },
  }))
  return filterSuggestionItems([...builtIns, ...callouts], query)
}

/** A page editor instance: the page schema and options, with the nesting
 *  rule installed as a transaction filter. */
export function usePageEditor(initialBlocks: EditorBlockLike[]): PageEditorInstance {
  const editor = useCreateBlockNote({
    schema: pageSchema,
    trailingBlock: false,
    tables: { headers: false, splitCells: false, cellBackgroundColor: false, cellTextColor: false },
    initialContent: initialBlocks.length > 0 ? (initialBlocks as never) : undefined,
  })
  useEffect(
    () => editor.onBeforeChange(({ tr }) => (addsNestingViolation(tr.before, tr.doc) ? false : undefined)),
    [editor],
  )
  return editor
}
````


- [ ] **Step 5: Run the tests to verify they pass**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/use-document-mode.test.tsx src/features/notes/__tests__/use-page-editor.test.tsx`
Expected: PASS, 4 tests.


- [ ] **Step 6: Commit**


From the repo root:

```bash
git add frontend/src/features/notes/use-document-mode.ts frontend/src/features/notes/use-page-editor.ts frontend/src/features/notes/__tests__/use-document-mode.test.tsx frontend/src/features/notes/__tests__/use-page-editor.test.tsx
git commit -m "feat(notes): add the page editor hooks"
```



### Task 11: The page editor and its outline rail

**Files:**
- Create: `frontend/src/features/notes/page-outline.tsx`
- Create: `frontend/src/features/notes/page-editor.tsx`
- Modify: `frontend/src/styles/globals.css:2` (one line after it)
- Test: `frontend/src/features/notes/__tests__/page-editor.test.tsx`

**Interfaces:**
- Consumes: `PageEditorInstance` (Task 2); `EditorBlockLike`, `toEditorBlocks` (Task 6); `useDocumentMode`, `usePageEditor`, `pageSlashItems` (Task 10).
- Produces: `PageEditor`, `PageEditorProps`, `PageOutline` (Contracts, Task 11).

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4


- [ ] **Step 1: Write the failing test**


`frontend/src/features/notes/__tests__/page-editor.test.tsx`:

````tsx
import { act, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { toEditorBlocks, type EditorBlockLike } from "../lib/block-mapping"
import type { SyncBlock } from "../lib/sync-tree"
import { PageEditor } from "../page-editor"

const b = (id: string, type: string, text: string, properties: SyncBlock["properties"] = null): SyncBlock => ({
  id,
  parentId: null,
  type,
  text,
  properties,
})

const BLOCKS: EditorBlockLike[] = toEditorBlocks([
  b("h1", "heading", "Plans", { level: 1 }),
  b("p1", "paragraph", "first"),
  b("h2", "heading", "Details", { level: 2 }),
  b("p2", "paragraph", "second"),
]).blocks

afterEach(() => {
  delete document.documentElement.dataset.mode
})

describe("PageEditor", () => {
  it("renders the page's blocks and an outline of its headings", async () => {
    render(<PageEditor initialBlocks={BLOCKS} editable />)
    const outline = await screen.findByRole("navigation", { name: "Page outline" })
    expect(outline).toHaveTextContent("Plans")
    expect(outline).toHaveTextContent("Details")
    expect(screen.getAllByText("first").length).toBeGreaterThan(0)
  })

  it("scrolls to a heading picked in the outline", async () => {
    const scroll = vi.fn()
    Element.prototype.scrollIntoView = scroll
    render(<PageEditor initialBlocks={BLOCKS} editable />)
    const outline = await screen.findByRole("navigation", { name: "Page outline" })
    fireEvent.click(outline.querySelectorAll("button")[1]!)
    expect(scroll).toHaveBeenCalledOnce()
    expect(scroll.mock.contexts[0]).toBe(document.querySelector('.bn-block-outer[data-id="h2"]'))
  })

  it("locks the document when not editable", async () => {
    const { container } = render(<PageEditor initialBlocks={BLOCKS} editable={false} />)
    await act(async () => {})
    expect(container.querySelector('.bn-block-outer[data-id="p1"]')).toHaveTextContent("first")
    expect(container.querySelector('[contenteditable="true"]')).toBeNull()
  })

  it("follows the document's colour mode", async () => {
    document.documentElement.dataset.mode = "dark"
    const { container } = render(<PageEditor initialBlocks={BLOCKS} editable />)
    await act(async () => {})
    expect(container.querySelector('[data-color-scheme="dark"]')).not.toBeNull()
  })
})
````


- [ ] **Step 2: Run it to verify it fails**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/page-editor.test.tsx`
Expected: FAIL — `Failed to resolve import "../page-editor"`.


- [ ] **Step 3: Write the outline rail**


`frontend/src/features/notes/page-outline.tsx`:

````tsx
import { useEffect, useState } from "react"
import { cn } from "darkraise-ui/lib"
import type { PageEditorInstance } from "./lib/editor-schema"

interface Heading {
  id: string
  level: number
  text: string
}

function headingsOf(editor: PageEditorInstance): Heading[] {
  const out: Heading[] = []
  const walk = (blocks: PageEditorInstance["document"]) => {
    for (const block of blocks) {
      if (block.type === "heading") {
        const text = (block.content as { type: string; text?: string }[])
          .map((part) => (part.type === "text" ? (part.text ?? "") : ""))
          .join("")
        out.push({ id: block.id, level: Number((block.props as { level?: number }).level ?? 1), text })
      }
      walk(block.children)
    }
  }
  walk(editor.document)
  return out
}

/** The page's headings, read from the live document so an edit shows at
 *  once; a click scrolls the heading into view. */
export function PageOutline({ editor }: { editor: PageEditorInstance }) {
  const [headings, setHeadings] = useState(() => headingsOf(editor))
  useEffect(() => editor.onChange(() => setHeadings(headingsOf(editor))), [editor])
  if (headings.length === 0) return null
  return (
    <nav aria-label="Page outline" className="text-sm">
      <ul className="space-y-1">
        {headings.map((heading) => (
          <li key={heading.id} style={{ paddingLeft: `${(heading.level - 1) * 0.75}rem` }}>
            <button
              type="button"
              className={cn("text-muted-foreground hover:text-foreground w-full truncate text-left")}
              onClick={() =>
                document
                  .querySelector(`.bn-block-outer[data-id="${heading.id}"]`)
                  ?.scrollIntoView({ block: "start", behavior: "smooth" })
              }
            >
              {heading.text || "Untitled heading"}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}
````


- [ ] **Step 4: Write the editor component**


It imports `@blocknote/shadcn/style.css` itself (the package's JS does not), so the stylesheet lands in the lazy chunk.

`frontend/src/features/notes/page-editor.tsx`:

````tsx
import "@blocknote/shadcn/style.css"
import {
  BasicTextStyleButton,
  CreateLinkButton,
  FormattingToolbar,
  FormattingToolbarController,
  SuggestionMenuController,
} from "@blocknote/react"
import { BlockNoteView } from "@blocknote/shadcn"
import type { EditorBlockLike } from "./lib/block-mapping"
import { PageOutline } from "./page-outline"
import { useDocumentMode } from "./use-document-mode"
import { pageSlashItems, usePageEditor } from "./use-page-editor"

export interface PageEditorProps {
  initialBlocks: EditorBlockLike[]
  editable: boolean
  onDocumentChange?: (blocks: EditorBlockLike[]) => void
  onBlur?: () => void
}

/** The page body. Loaded lazily with BlockNote's styles so neither reaches
 *  the main chunk.
 *
 *  darkraise-ui gap: BlockNote's shadcn slots (menus, popovers, selects) must
 *  not render into a portal, and darkraise-ui's DropdownMenu, Popover and
 *  Select do, so the package's own shadcn primitives render here. They read
 *  the same Tailwind colour tokens darkraise-ui defines, which is what keeps
 *  them on theme. */
export function PageEditor({ initialBlocks, editable, onDocumentChange, onBlur }: PageEditorProps) {
  const mode = useDocumentMode()
  const editor = usePageEditor(initialBlocks)

  return (
    <div className="flex min-h-0 gap-6">
      <div className="min-w-0 flex-1">
        <BlockNoteView
          editor={editor}
          editable={editable}
          theme={mode}
          slashMenu={false}
          formattingToolbar={false}
          emojiPicker={false}
          onChange={() => onDocumentChange?.(editor.document as unknown as EditorBlockLike[])}
          onBlur={onBlur}
        >
          <SuggestionMenuController triggerCharacter="/" getItems={async (query) => pageSlashItems(editor, query)} />
          <FormattingToolbarController
            formattingToolbar={() => (
              <FormattingToolbar>
                <BasicTextStyleButton basicTextStyle="bold" />
                <BasicTextStyleButton basicTextStyle="italic" />
                <BasicTextStyleButton basicTextStyle="code" />
                <BasicTextStyleButton basicTextStyle="strike" />
                <CreateLinkButton />
              </FormattingToolbar>
            )}
          />
        </BlockNoteView>
      </div>
      <aside className="hidden w-48 shrink-0 lg:block">
        <PageOutline editor={editor} />
      </aside>
    </div>
  )
}
````


- [ ] **Step 5: Let Tailwind see the package's classes**


In `frontend/src/styles/globals.css`, insert one line directly after line 2 (`@import "darkraise-ui/styles.css";`), so the file begins:

```css
@import "tailwindcss";
@import "darkraise-ui/styles.css";
@source "../../node_modules/@blocknote/shadcn";
@plugin "@tailwindcss/typography";
```


- [ ] **Step 6: Run the test to verify it passes**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/page-editor.test.tsx`
Expected: PASS, 4 tests.


- [ ] **Step 7: Typecheck and lint the new files**


Run (from `frontend/`): `npm run typecheck && npx eslint src/features/notes/page-editor.tsx src/features/notes/page-outline.tsx src/features/notes/use-page-editor.ts src/features/notes/use-document-mode.ts`
Expected: exit 0, no eslint output.


- [ ] **Step 8: Commit**


From the repo root:

```bash
git add frontend/src/features/notes/page-outline.tsx frontend/src/features/notes/page-editor.tsx frontend/src/styles/globals.css frontend/src/features/notes/__tests__/page-editor.test.tsx
git commit -m "feat(notes): add the BlockNote page editor"
```



### Task 12: Wire the editor into the page pane

**Files:**
- Modify: `frontend/src/features/notes/page-pane.tsx` (whole file replaced)
- Test: `frontend/src/features/notes/__tests__/page-pane.test.tsx` (whole file replaced)

**Interfaces:**
- Consumes: `usePageSync` (Task 9); `PageEditor` (Task 11, lazily); `SyncStatus` (Task 5); `pageQuery`, `usePageRename`, `PageView` (existing).
- Produces: `PagePane`, signature unchanged (Contracts, Task 12).

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4


- [ ] **Step 1: Replace the pane test**


The workspace tests mock `PagePane` (`notes-workspace.test.tsx:23`), so only this suite changes.

`frontend/src/features/notes/__tests__/page-pane.test.tsx`:

````tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { useState, type ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn(), apiFetchWithHeaders: vi.fn() }))

const binding = vi.hoisted(() => ({
  status: { kind: "idle" } as { kind: string; reason?: string; message?: string },
  discard: vi.fn(),
  generations: [] as number[],
}))

vi.mock("../use-page-sync", () => ({
  usePageSync: (_page: unknown, generation: number) => {
    binding.generations.push(generation)
    return {
      initialBlocks: [],
      status: binding.status,
      onDocumentChange: () => {},
      flushNow: () => {},
      discard: binding.discard,
    }
  },
}))

vi.mock("../page-editor", () => ({
  PageEditor: ({ editable }: { editable: boolean }) => <div>editor {editable ? "editable" : "read-only"}</div>,
}))

import { apiFetch } from "@/lib/api"
import type { PageView } from "@/hooks/api"
import { PagePane } from "../page-pane"

function wrapper({ children }: { children: ReactNode }) {
  const [qc] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } }),
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
  binding.status = { kind: "idle" }
  binding.discard.mockReset()
  binding.generations.length = 0
})

describe("PagePane", () => {
  it("renders the title in an editable field and the editor below it", async () => {
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    expect(screen.getByLabelText("Page title")).toHaveValue("Notes")
    expect(await screen.findByText("editor editable")).toBeInTheDocument()
  })

  it("shows the fallback for an untitled page without sending it as a title", () => {
    render(<PagePane page={{ ...PAGE, title: null }} autoFocusTitle={false} />, { wrapper })
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

  it.each([
    ["idle", null],
    ["saving", "Saving…"],
    ["saved", "Saved"],
    ["retrying", "Unsaved — retrying"],
  ])("labels the %s state", (kind, label) => {
    binding.status = { kind }
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    for (const text of ["Saving…", "Saved", "Unsaved — retrying"]) {
      if (text === label) expect(screen.getByText(text)).toBeInTheDocument()
      else expect(screen.queryByText(text)).not.toBeInTheDocument()
    }
  })

  it("shows a stopped engine as a banner, locks the editor, and reloads", async () => {
    binding.status = { kind: "stopped", reason: "refused", message: "a paragraph block cannot hold a list block" }
    vi.mocked(apiFetch).mockResolvedValue({ ...PAGE, properties: null, content: null, blocks: [] })
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    expect(screen.getByText("This edit was refused — a paragraph block cannot hold a list block")).toBeInTheDocument()
    expect(await screen.findByText("editor read-only")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Reload page" }))
    expect(binding.discard).toHaveBeenCalledOnce()
    await waitFor(() => expect(binding.generations).toContain(1))
  })

  it("shows a conflict in the engine's own words", () => {
    binding.status = { kind: "stopped", reason: "conflict", message: "This page was changed somewhere else." }
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    expect(screen.getByText("This page was changed somewhere else.")).toBeInTheDocument()
  })
})
````


- [ ] **Step 2: Run it to verify it fails**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/page-pane.test.tsx`
Expected: FAIL — the old pane renders the B2 block editor, so `editor editable`, the state labels and the banner are not found.


- [ ] **Step 3: Replace the pane**


`page-editor.tsx` is reached only through `React.lazy`, which is what keeps BlockNote out of the main chunk. The editor is keyed on the page and the reload generation, so a refetch of the page never resets it.

`frontend/src/features/notes/page-pane.tsx`:

````tsx
import { lazy, Suspense, useEffect, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { pageQuery, usePageRename, type PageView } from "@/hooks/api"
import { PAGE_TITLE_FALLBACK } from "./lib/build-page-tree"
import type { SyncStatus } from "./lib/page-sync"
import { usePageSync } from "./use-page-sync"

const PageEditor = lazy(() => import("./page-editor").then((m) => ({ default: m.PageEditor })))

const SAVE_LABEL: Partial<Record<SyncStatus["kind"], string>> = {
  saving: "Saving…",
  saved: "Saved",
  retrying: "Unsaved — retrying",
}

function bannerText(status: Extract<SyncStatus, { kind: "stopped" }>): string {
  return status.reason === "refused" ? `This edit was refused — ${status.message}` : status.message
}

/** The title field and the body.
 *
 *  The title is `pages.title` over `PATCH /pages/{id}`, never a block, so it
 *  is the one edit here that does not go through the save engine.
 */
export function PagePane({ page, autoFocusTitle }: { page: PageView; autoFocusTitle: boolean }) {
  const qc = useQueryClient()
  const rename = usePageRename()
  const [title, setTitle] = useState(page.title ?? "")
  const [generation, setGeneration] = useState(0)
  const field = useRef<HTMLInputElement | null>(null)
  const sync = usePageSync(page, generation)

  // Remount-free page switch: the pane is keyed on nothing, so the draft has
  // to follow the page it is showing.
  useEffect(() => {
    setTitle(page.title ?? "")
  }, [page.id, page.title])

  useEffect(() => {
    if (autoFocusTitle) field.current?.focus()
  }, [autoFocusTitle, page.id])

  const commitTitle = () => {
    const next = title.trim()
    if (next === (page.title ?? "")) return
    rename.mutate({ pageId: page.id, title: next === "" ? null : next })
  }

  const reload = async () => {
    sync.discard()
    await qc.invalidateQueries({ queryKey: pageQuery(page.id).queryKey, exact: true })
    setGeneration((g) => g + 1)
  }

  const label = SAVE_LABEL[sync.status.kind]

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
        {label ? <span className="text-muted-foreground shrink-0 text-xs">{label}</span> : null}
      </div>

      {sync.status.kind === "stopped" ? (
        <div className="border-destructive/50 flex items-center justify-between gap-3 rounded-md border border-dashed px-3 py-2">
          <p className="text-destructive text-sm">{bannerText(sync.status)}</p>
          <Button type="button" size="sm" variant="outline" onClick={() => void reload()}>
            Reload page
          </Button>
        </div>
      ) : null}

      <ScrollArea className="min-h-0 flex-1 pr-3">
        <Suspense fallback={<Skeleton className="h-40 w-full" />}>
          <PageEditor
            key={`${page.id}:${generation}`}
            initialBlocks={sync.initialBlocks}
            editable={sync.status.kind !== "stopped"}
            onDocumentChange={sync.onDocumentChange}
            onBlur={sync.flushNow}
          />
        </Suspense>
      </ScrollArea>
    </div>
  )
}
````


- [ ] **Step 4: Run the test to verify it passes**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/page-pane.test.tsx`
Expected: PASS, 10 tests.


- [ ] **Step 5: Run the notes suites**


Run (from `frontend/`): `npx vitest run src/features/notes`
Expected: PASS. `page-block-editor.test.tsx` still passes here; Task 13 deletes it.


- [ ] **Step 6: Commit**


From the repo root:

```bash
git add frontend/src/features/notes/page-pane.tsx frontend/src/features/notes/__tests__/page-pane.test.tsx
git commit -m "feat(notes): edit pages with the BlockNote editor"
```



### Task 13: Retire B2's copied editor and block hooks

**Files:**
- Delete: `frontend/src/features/notes/page-block-editor.tsx`, `frontend/src/features/notes/__tests__/page-block-editor.test.tsx`
- Modify: `frontend/src/hooks/api/use-pages-api.ts` (whole file replaced)
- Modify: `frontend/src/hooks/api/__tests__/use-pages-mutations.test.tsx` (whole file replaced)

**Interfaces:**
- Consumes: nothing new; Task 12 removed the last importer of `PageBlockEditor`.
- Produces: nothing. Removes `PageBlockEditor`, `promote`, `PageSaveStatus`, `usePageBlockUpdate`, `usePageBlockInsert`, `usePageBlockMove`, `usePageBlockDelete`, `usePageBlocksInsertBatch`, `PageBlockWriteResponse`, `PageBlockBatchWriteResponse` and `NewPageBlock`.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3


- [ ] **Step 1: Confirm nothing else uses what goes**


From `frontend/`:

```bash
grep -rn "PageBlockEditor\|page-block-editor\|usePageBlock\|PageBlockWriteResponse\|PageBlockBatchWriteResponse\|NewPageBlock\|PageSaveStatus" src --include=*.ts --include=*.tsx | grep -v "features/notes/page-block-editor.tsx\|__tests__/page-block-editor.test.tsx\|hooks/api/use-pages-api.ts\|__tests__/use-pages-mutations.test.tsx"
```

Expected: no output. Any hit is a consumer this plan did not account for: stop and report.


- [ ] **Step 2: Delete the copied editor**


From the repo root (`git rm` stages the deletions, so the commit step does not name these paths again):

```bash
git rm frontend/src/features/notes/page-block-editor.tsx frontend/src/features/notes/__tests__/page-block-editor.test.tsx
```


- [ ] **Step 3: Replace the page hooks module**


The file keeps every read and page mutation hook unchanged and loses the block-verb hooks, their per-page mutation queue and the write response types.

`frontend/src/hooks/api/use-pages-api.ts`:

````ts
import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query"

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
````


- [ ] **Step 4: Replace the mutation hook tests**


The `page block verbs` suite goes with the hooks it tested; `page-transport.test.ts` (Task 8) covers those routes now.

`frontend/src/hooks/api/__tests__/use-pages-mutations.test.tsx`:

````tsx
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
import {
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

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
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
````


- [ ] **Step 5: Typecheck and run the affected suites**


Run (from `frontend/`): `npm run typecheck && npx vitest run src/hooks/api src/features/notes`
Expected: typecheck exit 0; every file PASS.


- [ ] **Step 6: Commit**


From the repo root:

```bash
git add frontend/src/hooks/api/use-pages-api.ts frontend/src/hooks/api/__tests__/use-pages-mutations.test.tsx
git commit -m "refactor(notes): drop the copied block editor"
```



### Task 14: Demo mode's sample page

**Files:**
- Create: `frontend/src/features/notes/lib/demo-page.ts`
- Create: `frontend/src/features/notes/demo-notes.tsx`
- Modify: `frontend/src/routes/_authenticated/notes.tsx` (whole file replaced)
- Test: `frontend/src/features/notes/__tests__/demo-notes.test.tsx`
- Test: `frontend/src/routes/_authenticated/__tests__/notes.demo.test.tsx`

**Interfaces:**
- Consumes: `SyncBlock` (Task 4); `toEditorBlocks` (Task 6); `PageEditor` (Task 11, lazily); `DEMO` from `@/lib/demo-flag` (existing).
- Produces: `DemoNotes`, `DEMO_PAGE`, `DEMO_PAGE_TITLE` (Contracts, Task 14).

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 0 = 3


- [ ] **Step 1: Write the failing tests**


The route test is named `*.demo.test.tsx` after `memory-graph-route.demo.test.tsx`; like every test file under `routes/`, it draws a harmless "does not export a Route" warning from the route generator, and `routeTree.gen.ts` does not change.

`frontend/src/features/notes/__tests__/demo-notes.test.tsx`:

````tsx
import { render, screen } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import { DemoNotes } from "../demo-notes"

afterEach(() => vi.unstubAllGlobals())

it("shows the sample page read-only and makes no request", async () => {
  const fetchSpy = vi.fn()
  vi.stubGlobal("fetch", fetchSpy)
  const { container } = render(<DemoNotes />)
  expect(screen.getByRole("heading", { name: "Welcome to notes" })).toBeInTheDocument()
  expect((await screen.findAllByText("Draft the release notes")).length).toBeGreaterThan(0)
  expect(container.querySelector('[contenteditable="true"]')).toBeNull()
  expect(fetchSpy).not.toHaveBeenCalled()
})
````

`frontend/src/routes/_authenticated/__tests__/notes.demo.test.tsx`:

````tsx
import { render, screen } from "@testing-library/react"
import type { ComponentType } from "react"
import { expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@tanstack/react-router", async () => ({
  ...(await vi.importActual<Record<string, unknown>>("@tanstack/react-router")),
  createFileRoute: () => (opts: Record<string, unknown>) => opts,
  useSearch: () => ({}),
  useNavigate: () => vi.fn(),
}))
vi.mock("@/features/notes/demo-notes", () => ({ DemoNotes: () => <div>demo notes</div> }))
vi.mock("@/hooks/api", () => ({ useProjects: () => ({ data: undefined, isLoading: false, isError: false }) }))

import { Route } from "../notes"

it("renders the demo page instead of the catalogue branches", () => {
  const Component = (Route.options ?? Route).component as ComponentType
  render(<Component />)
  expect(screen.getByText("demo notes")).toBeInTheDocument()
  expect(screen.queryByText("No personal space yet")).not.toBeInTheDocument()
})
````


- [ ] **Step 2: Run them to verify they fail**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/demo-notes.test.tsx src/routes/_authenticated/__tests__/notes.demo.test.tsx`
Expected: FAIL — `Failed to resolve import "../demo-notes"`, and the route renders "No personal space yet" instead of the demo page.


- [ ] **Step 3: Write the sample page**


`frontend/src/features/notes/lib/demo-page.ts`:

````ts
import type { SyncBlock } from "./sync-tree"

export const DEMO_PAGE_TITLE = "Welcome to notes"

const block = (
  id: string,
  parentId: string | null,
  type: string,
  text: string,
  properties: SyncBlock["properties"] = null,
): SyncBlock => ({ id, parentId, type, text, properties })

/** The page demo mode shows on `/notes`. There is no backend in demo mode,
 *  so this is the whole of what it renders. */
export const DEMO_PAGE: readonly SyncBlock[] = [
  block("d-h1", null, "heading", "Notes are pages of blocks", { level: 2 }),
  block("d-p1", null, "paragraph", "Type **/** for a block menu, or start a line with `#`, `-` or `[]`."),
  block("d-t1", null, "todo", "Draft the release notes", { checked: true }),
  block("d-t2", null, "todo", "Review the *pages* increment", { checked: false }),
  block("d-g1", null, "toggle", "Details fold away"),
  block("d-g2", "d-g1", "paragraph", "A toggle holds any blocks you nest under it."),
  block("d-c1", null, "callout", "Every edit saves on its own.", { variant: "info" }),
  block("d-k1", null, "code", "curl localhost:8000/health", { language: "sh" }),
]
````


- [ ] **Step 4: Write the demo view**


`frontend/src/features/notes/demo-notes.tsx`:

````tsx
import { lazy, Suspense } from "react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toEditorBlocks } from "./lib/block-mapping"
import { DEMO_PAGE, DEMO_PAGE_TITLE } from "./lib/demo-page"

const PageEditor = lazy(() => import("./page-editor").then((m) => ({ default: m.PageEditor })))

const DEMO_BLOCKS = toEditorBlocks(DEMO_PAGE).blocks

/** `/notes` in demo mode: a fixed page in a read-only editor, with no save
 *  engine and so no request. */
export function DemoNotes() {
  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-2xl font-semibold">{DEMO_PAGE_TITLE}</h2>
      <Suspense fallback={<Skeleton className="h-40 w-full" />}>
        <PageEditor initialBlocks={DEMO_BLOCKS} editable={false} />
      </Suspense>
    </div>
  )
}
````


- [ ] **Step 5: Replace the route**


The only change is the `DEMO` branch ahead of the catalogue branches, and its two imports.

`frontend/src/routes/_authenticated/notes.tsx`:

````tsx
import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router"
import { NotebookPen } from "lucide-react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import { EmptyState } from "@/components/darkmem"
import { DemoNotes } from "@/features/notes/demo-notes"
import { NotesWorkspace } from "@/features/notes/notes-workspace"
import { DEMO } from "@/lib/demo-flag"
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

      {DEMO ? (
        <DemoNotes />
      ) : isError ? (
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
````


- [ ] **Step 6: Run the tests to verify they pass**


Run (from `frontend/`): `npx vitest run src/features/notes/__tests__/demo-notes.test.tsx src/routes/_authenticated/__tests__/notes.demo.test.tsx src/routes/_authenticated/__tests__/notes.test.tsx`
Expected: PASS, every test.


- [ ] **Step 7: Confirm the route tree did not change**


From `frontend/`:

```bash
npm run build >/dev/null && git diff --exit-code src/routeTree.gen.ts
```

Expected: exit 0.


- [ ] **Step 8: Commit**


From the repo root:

```bash
git add frontend/src/features/notes/lib/demo-page.ts frontend/src/features/notes/demo-notes.tsx frontend/src/routes/_authenticated/notes.tsx frontend/src/features/notes/__tests__/demo-notes.test.tsx frontend/src/routes/_authenticated/__tests__/notes.demo.test.tsx
git commit -m "feat(notes): show a sample page in demo mode"
```



### Task 15: End-to-end spec, docs and the frontend legs

**Files:**
- Create: `frontend/tests/notes-editor.spec.ts`
- Modify: `CLAUDE.md` (the `/notes` paragraph under Documents)

**Interfaces:**
- Consumes: the whole increment.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 0 = 3


- [ ] **Step 1: Write the end-to-end spec**


This is the one code block in the plan the prototype could not run (it needs the disposable stack). Step 5 runs it; a failure there is fixed in this spec's selectors or waits, never by loosening an assertion about what was saved.

`frontend/tests/notes-editor.spec.ts`:

````ts
import { test, expect, type Page } from "@playwright/test"
import { seedAdminPassword } from "./helpers/seed-admin"

/**
 * The /notes page editor end to end: what only a real browser against a real
 * server can show is that an edit leaves the editor, reaches the page block
 * verbs and comes back on a reload. The unit suite drives the save engine
 * against a fake server; this drives the real one.
 */

const PASSWORD = process.env.E2E_ADMIN_PASSWORD

async function signIn(page: Page) {
  await page.goto("/login")
  await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
  await page.getByRole("button", { name: /sign in/i }).click()
  await expect(page).toHaveURL("/")
}

test.beforeAll(() => {
  if (!PASSWORD) {
    throw new Error("E2E_ADMIN_PASSWORD must be set — this spec never soft-skips for a missing credential.")
  }
  if (!process.env.E2E_DISPOSABLE_STACK) {
    seedAdminPassword()
  }
})

async function personalProject(page: Page): Promise<string> {
  const response = await page.request.get("/api/v1/projects")
  expect(response.ok()).toBe(true)
  const projects = (await response.json()) as { name: string; kind: string }[]
  const personal = projects.find((p) => p.kind === "personal")
  expect(personal, "the boot seeds a personal project").toBeTruthy()
  return personal!.name
}

async function createPage(page: Page, title: string, content?: string): Promise<string> {
  const project = await personalProject(page)
  const response = await page.request.post("/api/v1/pages", { data: { project, title, content: content ?? null } })
  expect(response.status()).toBe(201)
  return ((await response.json()) as { id: string }).id
}

async function openPage(page: Page, id: string) {
  await page.goto(`/notes?page=${id}`)
  await expect(page.locator(".bn-editor")).toBeVisible()
}

async function saved(page: Page) {
  await expect(page.getByText("Saved", { exact: true })).toBeVisible()
}

async function pageBlocks(page: Page, id: string) {
  const response = await page.request.get(`/api/v1/pages/${id}`)
  return ((await response.json()) as { blocks: { type: string; text: string; properties: Record<string, unknown> | null }[] })
    .blocks
}

test("typing persists across a reload", async ({ page }) => {
  await signIn(page)
  const id = await createPage(page, "Typing")
  await openPage(page, id)
  await page.locator(".bn-editor").click()
  await page.keyboard.type("Hello from the editor")
  await saved(page)
  await page.reload()
  await expect(page.locator(".bn-editor")).toContainText("Hello from the editor")
})

test("a to-do, a toggle and a callout save with their properties", async ({ page }) => {
  await signIn(page)
  const id = await createPage(page, "Blocks")
  await openPage(page, id)
  await page.locator(".bn-editor").click()
  await page.keyboard.type("[] ship it")
  await page.locator('.bn-editor input[type="checkbox"]').first().check()
  await page.keyboard.press("End")
  await page.keyboard.press("Enter")
  await page.keyboard.press("Enter")
  await page.keyboard.type("/toggle")
  await page.getByText("Toggle List", { exact: true }).click()
  await page.keyboard.type("folded")
  await page.keyboard.press("Enter")
  await page.keyboard.press("Enter")
  await page.keyboard.type("/callout")
  await page.getByText("Callout: warning", { exact: true }).click()
  await page.keyboard.type("careful")
  await saved(page)

  const blocks = await pageBlocks(page, id)
  expect(blocks.find((b) => b.type === "todo")).toMatchObject({ text: "ship it", properties: { checked: true } })
  expect(blocks.find((b) => b.type === "toggle")).toMatchObject({ text: "folded" })
  expect(blocks.find((b) => b.type === "callout")).toMatchObject({ text: "careful", properties: { variant: "warning" } })

  await page.reload()
  await expect(page.locator('.bn-editor input[type="checkbox"]').first()).toBeChecked()
  await expect(page.locator('[data-variant="warning"]')).toContainText("careful")

  const toggle = page.locator(".bn-toggle-wrapper").first()
  const shown = await toggle.getAttribute("data-show-children")
  await toggle.locator(".bn-toggle-button").click()
  await expect(toggle).not.toHaveAttribute("data-show-children", shown ?? "")
})

test("a pasted multi-block snippet arrives as blocks", async ({ page }) => {
  await signIn(page)
  const id = await createPage(page, "Paste")
  await openPage(page, id)
  await page.locator(".bn-editor").click()
  await page.evaluate(() => {
    const data = new DataTransfer()
    data.setData("text/plain", "- one\n- two\n\n> quoted")
    document
      .querySelector(".bn-editor")!
      .dispatchEvent(new ClipboardEvent("paste", { clipboardData: data, bubbles: true, cancelable: true }))
  })
  await saved(page)
  const blocks = await pageBlocks(page, id)
  expect(blocks.filter((b) => b.type === "list").map((b) => b.text)).toEqual(["one", "two"])
  expect(blocks.some((b) => b.type === "quote" && b.text === "quoted")).toBe(true)
})

test("inline HTML survives an edit to the words beside it", async ({ page }) => {
  await signIn(page)
  const id = await createPage(page, "Atoms", "Press <kbd>K</kbd> now")
  await openPage(page, id)
  await page.locator(".bn-editor").getByText("now").click()
  await page.keyboard.press("End")
  await page.keyboard.type(" please")
  await saved(page)
  const [first] = await pageBlocks(page, id)
  expect(first!.text).toBe("Press <kbd>K</kbd> now please")
})

test("a page moves in the tree, goes to the trash and comes back", async ({ page }) => {
  await signIn(page)
  const first = await createPage(page, "Tree first")
  const second = await createPage(page, "Tree second")
  await page.goto(`/notes?page=${first}`)
  const source = page.getByText("Tree second", { exact: true }).first()
  const target = page.getByText("Tree first", { exact: true }).first()
  const box = (await target.boundingBox())!
  await source.hover()
  await page.mouse.down()
  await page.mouse.move(box.x + box.width / 2, box.y + 2, { steps: 12 })
  await page.mouse.up()
  await expect
    .poll(async () => {
      const list = await page.request.get(`/api/v1/pages?project=${encodeURIComponent(await personalProject(page))}`)
      const rows = (await list.json()) as { id: string; order_index: number; parent_id: string | null }[]
      const a = rows.find((r) => r.id === first)!
      const b = rows.find((r) => r.id === second)!
      return a.parent_id === b.parent_id && b.order_index < a.order_index
    })
    .toBe(true)

  const deleted = await page.request.delete(`/api/v1/pages/${second}`)
  expect(deleted.status()).toBe(204)
  await page.goto("/notes")
  await page.getByRole("button", { name: "Trash" }).click()
  await page.getByRole("button", { name: "Restore Tree second" }).click()
  await expect(page.getByText("Tree second", { exact: true }).first()).toBeVisible()
})
````


- [ ] **Step 2: Update CLAUDE.md**


In `CLAUDE.md`, replace this paragraph opening:

````markdown
**The SPA's `/notes` is the page tree's only surface, and it replaced the
document one on 2026-09-18** (increment B2). `features/notes/` renders it:
a sidebar tree with drag-to-reorder over `PATCH /pages/{id}`, per-row create,
rename and soft delete, a trash sheet over `GET /pages/trash`, and a page pane
whose block editor is a **deliberate copy** of the document block editor over
the page verbs, recorded as a duplicate that increment B3's BlockNote editor
deletes. `ProjectWorkspace` lost `treeManagement` in the same change and is the
corpus browser again.
````

with:

````markdown
**The SPA's `/notes` is the page tree's only surface, and it replaced the
document one on 2026-09-18** (increment B2). `features/notes/` renders it:
a sidebar tree with drag-to-reorder over `PATCH /pages/{id}`, per-row create,
rename and soft delete, a trash sheet over `GET /pages/trash`, and a page pane
whose body is a **BlockNote 0.54.2 editor** (increment B3,
`docs/superpowers/specs/2026-09-18-pages-increment-b3-blocknote-editor-design.md`),
lazy-loaded so none of it reaches the main chunk. Its save engine
(`features/notes/lib/page-sync.ts`) **diffs the editor's document against the
last tree the server acknowledged** and sends one page block write at a time,
the first one a local mirror of `block_verbs.py`'s refusals says the server
would accept (`lib/sync-tree.ts`). **Every tree it compares is canonicalised**
through the editor mapping first, so a stored spelling the editor writes
differently is never read as an edit, and **an update sends every property
key its type models** because the server merges properties and never clears an
omitted key. Change a page rule in `block_verbs.py` and the mirror in
`lib/block-properties.ts` / `lib/sync-tree.ts` changes with it, or the editor
starts sending writes the server refuses. Inline markdown the editor cannot
show (inline HTML, images, autolinks, titled links, hard breaks) rides as a
`rawInline` atom written back byte for byte, and `emitInline` is idempotent by
construction — it drops marks until its output reads back as its input.
`ProjectWorkspace` lost `treeManagement` in B2 and is the corpus browser
again.
````

The rest of that paragraph ("The cost is stated rather than discovered: …") stays as it is.


- [ ] **Step 3: Run the frontend legs**


From `frontend/`:

```bash
npm run typecheck && npm test && npm run build
```

Expected: typecheck exit 0; every vitest file PASS; build green. On exit 143, check `free -h` and re-run the leg alone (Global Constraints).


- [ ] **Step 4: Confirm BlockNote stayed out of the main chunk**


From `frontend/`:

```bash
ls dist/assets | grep -E '^page-editor-.*\.(js|css)$'
grep -c 'bn-block-outer\|useCreateBlockNote' dist/assets/index-*.js
```

Expected: one `page-editor-*.js` and one `page-editor-*.css`; the count is `0`.


- [ ] **Step 5: Run the Playwright leg through the harness**


From `backend/` (never bare Playwright — it would point `/api` at the live instance):

```bash
python scripts/e2e/run_playwright_e2e.py
```

Expected: every spec passes, including the five in `notes-editor.spec.ts` (the second also folds a toggle) and `demo mode issues no API request on /notes`. A red leg is re-run standalone before it is believed (CLAUDE.md: 47 passed → 13 failed → 47 passed on one unchanged commit, 2026-09-02).


- [ ] **Step 6: Commit**


From the repo root:

```bash
git add frontend/tests/notes-editor.spec.ts CLAUDE.md
git commit -m "test(notes): cover the page editor end to end"
```

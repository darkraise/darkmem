# Artifacts workspace, increment 1 — frame and tree

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Artifacts tab from a fixed-width two-column list into a
full-bleed, resizable, independently-scrolling document browser whose tree is
navigable at 475 documents.

**Architecture:** Three composed changes, no backend. The workspace gains a
resizable frame with per-pane scroll areas; `DocumentTree` swaps uncontrolled
all-expanded state for a controlled `expanded`/`onExpandedChange` pair; the
workspace owns that state, persists it per project, and derives a default from
the selected document's path. A breadcrumb over the reader names where you are.

**Tech Stack:** React 19, TanStack Router, `darkraise-ui` primitives
(`tree-view`, `resizable`, `scroll-area`, `breadcrumb`), vitest +
@testing-library/react.

**Spec:** `docs/superpowers/specs/2026-09-03-artifacts-workspace-revamp-design.md`
(§3.1 frame, §3.2 tree, §3.3 reader, §3.4 states)

## Global Constraints

- **Library first.** No new local component. Every primitive used here already
  exists under `frontend/node_modules/darkraise-ui/dist/components/`
  (CLAUDE.md, "UI components come from darkraise-ui first").
- **Four states everywhere.** Loading / failed / empty / populated must stay
  distinguishable. A failed read must never render as an empty one — nine
  surfaces were repaired for exactly this on 2026-09-03.
- **`enabled: !DEMO`.** Any new query respects it; a hook without it
  401-redirects the whole demo to `/login`.
- **No second global Ctrl+K.** Not in this increment at all (spec §3.2).
- **Verification per task:** `npm run typecheck` (= `tsc -b`), `npm test`,
  `npm run build`, run from `frontend/`.
- **Existing behaviour that must not regress:** `focusBlockId` scroll-to-block
  (shipped 2026-09-03), the four state branches in `ProjectWorkspace`, and
  `DocumentTree`'s `nodeActions` slot, which increment 8's editor mounts into.

## File Structure

| File | Responsibility |
|---|---|
| `frontend/src/features/documents/tree-expansion.ts` | **Create.** Pure helpers: derive default expanded paths from a selected document, and the localStorage key. No React. |
| `frontend/src/features/documents/__tests__/tree-expansion.test.ts` | **Create.** Unit tests for the above. |
| `frontend/src/features/documents/components/document-tree.tsx` | **Modify.** Accept controlled `expanded` + `onExpandedChange`; stop collecting `allFolderPaths`. Add folder child counts. |
| `frontend/src/features/documents/components/project-workspace.tsx` | **Modify.** Own expansion state, persist it, render the resizable frame with scroll areas and the breadcrumb. |
| `frontend/src/features/documents/__tests__/project-workspace.test.tsx` | **Modify.** Extend the existing four-state suite. |
| `frontend/src/routes/_authenticated/projects_.$project.tsx` | **Modify.** Opt the route out of the centred container. |

---

### Task 1: Expansion helpers

**Implementer:** `dcc-superpower-companions:impl-sonnet-low`
**Evaluation:** spec completeness 1 (exact signatures given), coupling 0 (pure
module, no imports from the app), risk 1 (no runtime path yet), scale 1 (one
small file + test).
**Approach:** inline — pure functions with stated behaviour, no decision open.

**Files:**
- Create: `frontend/src/features/documents/tree-expansion.ts`
- Test: `frontend/src/features/documents/__tests__/tree-expansion.test.ts`

**Interfaces:**
- Consumes: `UriTreeNode` from `../uri-tree`, whose exact shape is:

```ts
export interface UriTreeNode {
  name: string                          // last path segment
  path: string                          // full "/"-joined prefix, unique
  document: DocumentListItem | null     // NOT optional — null for a folder
  children: UriTreeNode[]
}
```

  Note `document` is `| null`, not `?:`. A node can be **both** a document and
  a folder (`a/b.md` and `a/b.md/c.md` coexist; uris are opaque keys, not a
  filesystem), so never infer "is a folder" from `document === null` — use
  `children.length > 0`.
- Produces:
  - `expansionStorageKey(project: string): string`
  - `pathsToDocument(roots: UriTreeNode[], documentId: string | null): string[]`
  - `rootFolderPaths(roots: UriTreeNode[]): string[]`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from "vitest"
import {
  expansionStorageKey,
  pathsToDocument,
  rootFolderPaths,
} from "../tree-expansion"
import type { UriTreeNode } from "../uri-tree"

const node = (
  path: string,
  name: string,
  children: UriTreeNode[] = [],
  document: unknown = null,
): UriTreeNode => ({ path, name, children, document } as UriTreeNode)

const ROOTS: UriTreeNode[] = [
  node("docs", "docs", [
    node("docs/planning", "planning", [
      node("docs/planning/progress.md", "progress.md", [], { id: "doc-1" }),
    ]),
    node("docs/readme.md", "readme.md", [], { id: "doc-2" }),
  ]),
  node("src", "src", [node("src/main.ts", "main.ts", [], { id: "doc-3" })]),
]

describe("tree expansion", () => {
  it("keys storage per project so two projects do not share expansion", () => {
    expect(expansionStorageKey("darkmem")).not.toEqual(expansionStorageKey("other"))
    expect(expansionStorageKey("darkmem")).toContain("darkmem")
  })

  it("expands only the folders on the path to the selected document", () => {
    // The whole point: 475 documents must not all expand. Only the ancestors
    // of the open document open.
    expect(pathsToDocument(ROOTS, "doc-1").sort()).toEqual(
      ["docs", "docs/planning"].sort(),
    )
  })

  it("returns no paths when nothing is selected", () => {
    expect(pathsToDocument(ROOTS, null)).toEqual([])
  })

  it("returns no paths when the id matches no document", () => {
    expect(pathsToDocument(ROOTS, "missing")).toEqual([])
  })

  it("opens only the top level as the no-selection default", () => {
    expect(rootFolderPaths(ROOTS).sort()).toEqual(["docs", "src"].sort())
  })

  it("does not treat a leaf as a folder", () => {
    expect(rootFolderPaths([node("a.md", "a.md", [], { id: "x" })])).toEqual([])
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/tree-expansion.test.ts`
Expected: FAIL — `Failed to resolve import "../tree-expansion"`.

- [ ] **Step 3: Write minimal implementation**

```ts
import type { UriTreeNode } from "./uri-tree"

/** Per-project, so opening one project does not inherit another's tree. */
export function expansionStorageKey(project: string): string {
  return `darkmem:artifacts:expanded:${project}`
}

/** Folder paths on the route from a root to `documentId`, excluding the
 *  document's own node. Empty when nothing is selected or the id is unknown —
 *  "expand nothing" is the honest answer to "expand the path to nowhere". */
export function pathsToDocument(
  roots: UriTreeNode[],
  documentId: string | null,
): string[] {
  if (!documentId) return []
  const trail: string[] = []
  const walk = (nodes: UriTreeNode[], ancestors: string[]): boolean => {
    for (const n of nodes) {
      if (n.document?.id === documentId) {
        trail.push(...ancestors)
        return true
      }
      if (n.children.length > 0 && walk(n.children, [...ancestors, n.path])) {
        return true
      }
    }
    return false
  }
  walk(roots, [])
  return trail
}

/** The no-selection default: top-level folders only. */
export function rootFolderPaths(roots: UriTreeNode[]): string[] {
  return roots.filter((n) => n.children.length > 0).map((n) => n.path)
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/tree-expansion.test.ts`
Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/documents/tree-expansion.ts \
        frontend/src/features/documents/__tests__/tree-expansion.test.ts
git commit -m "feat(ui): expansion helpers for the artifacts tree"
```

---

### Task 2: DocumentTree takes controlled expansion

**Implementer:** `dcc-superpower-companions:impl-sonnet-medium`
**Evaluation:** spec completeness 2 (exact props given, but the executor must
read the existing file), coupling 2 (two call sites — this workspace and
increment 8's editor path), risk 2 (a shared component; `nodeActions` must
survive), scale 1.
**Approach:** inline — the library already defines the controlled contract.

**Files:**
- Modify: `frontend/src/features/documents/components/document-tree.tsx`
- Test: `frontend/src/features/documents/__tests__/document-tree.test.tsx` (create)

**Interfaces:**
- Consumes: nothing from Task 1 (the workspace wires them together in Task 3).
- Produces: `DocumentTree` gains two optional props:
  - `expanded?: string[]`
  - `onExpandedChange?: (paths: string[]) => void`

  When `expanded` is omitted the component keeps today's behaviour, so
  increment 8's call site is unaffected.

`TreeView`'s own contract, copied from
`node_modules/darkraise-ui/dist/components/tree-view.d.ts`:

```ts
expanded?: string[]
defaultExpanded?: string[]
onExpandedChange?: (details: { value: string[] }) => void
```

Note `onExpandedChange` receives `{ value }`, not a bare array — unwrap it.

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen, fireEvent } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { DocumentTree } from "../components/document-tree"
import type { DocumentListItem } from "@/hooks/api"

const ITEMS = [
  { id: "doc-1", title: "Progress", uri: "docs/planning/progress.md",
    source_type: "note", project: "darkmem", block_count: 1 },
  { id: "doc-2", title: "Readme", uri: "docs/readme.md",
    source_type: "note", project: "darkmem", block_count: 1 },
] as unknown as DocumentListItem[]

describe("DocumentTree expansion", () => {
  it("shows only what the controlled expanded set opens", () => {
    // The defect this fixes: the component expanded every folder, so 475
    // documents rendered as one wall.
    render(
      <DocumentTree
        items={ITEMS}
        selectedId={null}
        onSelect={vi.fn()}
        truncated={false}
        expanded={["docs"]}
        onExpandedChange={vi.fn()}
      />,
    )
    expect(screen.getByText("readme.md")).toBeInTheDocument()
    expect(screen.queryByText("progress.md")).not.toBeInTheDocument()
  })

  it("reports expansion changes as a bare array", () => {
    const onExpandedChange = vi.fn()
    render(
      <DocumentTree
        items={ITEMS}
        selectedId={null}
        onSelect={vi.fn()}
        truncated={false}
        expanded={[]}
        onExpandedChange={onExpandedChange}
      />,
    )
    fireEvent.click(screen.getByText("docs"))
    expect(onExpandedChange).toHaveBeenCalledWith(expect.any(Array))
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/document-tree.test.tsx`
Expected: FAIL — `progress.md` is in the document because the component still
expands everything.

- [ ] **Step 3: Write minimal implementation**

In `document-tree.tsx`:

1. Add the two props to the signature and its type:

```tsx
  expanded,
  onExpandedChange,
}: {
  items: DocumentListItem[]
  selectedId: string | null
  onSelect: (doc: DocumentListItem) => void
  truncated: boolean
  nodeActions?: (node: UriTreeNode) => ReactNode
  /** Controlled expansion. Omitted keeps the legacy expand-everything
   *  behaviour, so increment 8's call site is unaffected. */
  expanded?: string[]
  onExpandedChange?: (paths: string[]) => void
}) {
```

2. Keep the `allFolderPaths` collection ONLY as the uncontrolled fallback, and
   pass the controlled pair when given:

```tsx
  const controlled = expanded !== undefined
  const treeProps = controlled
    ? {
        expanded,
        onExpandedChange: (d: { value: string[] }) => onExpandedChange?.(d.value),
      }
    : { defaultExpanded: allFolderPaths }
```

3. Spread `{...treeProps}` onto `<TreeView>` in place of the current
   `defaultExpanded={allFolderPaths}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/document-tree.test.tsx`
Expected: PASS, 2 tests. Then `npx vitest run src/features/documents` — the
existing suites must stay green, proving the uncontrolled path is untouched.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/documents/components/document-tree.tsx \
        frontend/src/features/documents/__tests__/document-tree.test.tsx
git commit -m "feat(ui): DocumentTree accepts controlled expansion"
```

---

### Task 3: The workspace owns and persists expansion

**Implementer:** `dcc-superpower-companions:impl-sonnet-high`
**Evaluation:** spec completeness 2, coupling 3 (joins Tasks 1 and 2 to the
live component and to localStorage), risk 2 (must not regress the four state
branches or `focusBlockId`), scale 2.
**Approach:** inline — the design is settled by Tasks 1-2.

**Files:**
- Modify: `frontend/src/features/documents/components/project-workspace.tsx`
- Test: `frontend/src/features/documents/__tests__/project-workspace.test.tsx`

**Interfaces:**
- Consumes: `expansionStorageKey`, `pathsToDocument`, `rootFolderPaths`
  (Task 1); `DocumentTree`'s `expanded` / `onExpandedChange` (Task 2).
- Produces: nothing new for later tasks.

- [ ] **Step 1: Write the failing test**

Append to the existing suite:

```tsx
it("opens only the top level, not every folder, on first load", async () => {
  // 475 documents all expanded is the reported "hard to navigate".
  mockDocuments({ items: [DOC, { ...DOC, id: "doc-2", uri: "docs/planning/progress.md" }] })
  renderWorkspace()
  expect(await screen.findByText("notes")).toBeInTheDocument()
  expect(screen.queryByText("progress.md")).not.toBeInTheDocument()
})

it("remembers expansion per project across mounts", async () => {
  mockDocuments({ items: [DOC] })
  window.localStorage.setItem(
    "darkmem:artifacts:expanded:darkmem",
    JSON.stringify(["notes"]),
  )
  renderWorkspace()
  expect(await screen.findByText("design.md")).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/project-workspace.test.tsx`
Expected: FAIL — the first test finds `progress.md`, because the workspace
passes no `expanded` and the tree still expands everything.

- [ ] **Step 3: Write minimal implementation**

In `ProjectWorkspace`:

```tsx
import {
  expansionStorageKey,
  pathsToDocument,
  rootFolderPaths,
} from "../tree-expansion"
import { buildUriTree } from "../uri-tree"

  const roots = useMemo(() => buildUriTree(items), [items])
  const [expanded, setExpanded] = useState<string[] | null>(null)

  // Read once per project. A read that throws (private mode, blocked storage)
  // falls back to the derived default rather than failing the pane.
  useEffect(() => {
    let stored: string[] | null = null
    try {
      const raw = window.localStorage.getItem(expansionStorageKey(project))
      if (raw) stored = JSON.parse(raw) as string[]
    } catch {
      stored = null
    }
    setExpanded(stored ?? null)
  }, [project])

  const effectiveExpanded =
    expanded ??
    (selected ? pathsToDocument(roots, selected.id) : rootFolderPaths(roots))

  const handleExpandedChange = (paths: string[]) => {
    setExpanded(paths)
    try {
      window.localStorage.setItem(
        expansionStorageKey(project),
        JSON.stringify(paths),
      )
    } catch {
      // Persistence is a convenience; losing it must not break the tree.
    }
  }
```

Pass `expanded={effectiveExpanded}` and `onExpandedChange={handleExpandedChange}`
to `<DocumentTree>`. Import `useEffect`, `useMemo` from react.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/project-workspace.test.tsx`
Expected: PASS — all six tests (the four state tests plus these two).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/documents/components/project-workspace.tsx \
        frontend/src/features/documents/__tests__/project-workspace.test.tsx
git commit -m "feat(ui): persist artifacts tree expansion per project"
```

---

### Task 4: Full-bleed resizable frame with per-pane scrolling

**Implementer:** `dcc-superpower-companions:impl-sonnet-medium`
**Evaluation:** spec completeness 2, coupling 2 (route + workspace), risk 2
(layout regressions are invisible to unit tests), scale 2.
**Approach:** inline — the primitives fix the structure.

**Files:**
- Modify: `frontend/src/features/documents/components/project-workspace.tsx`
- Modify: `frontend/src/routes/_authenticated/projects_.$project.tsx`
- Test: `frontend/src/features/documents/__tests__/project-workspace.test.tsx`

**Interfaces:**
- Consumes: Task 3's expansion wiring.
- Produces: nothing for later tasks.

`Resizable`'s contract, copied from
`node_modules/darkraise-ui/dist/components/resizable.d.ts`:

```ts
ResizablePanelGroup: { orientation?: "horizontal" | "vertical";
                       onLayoutChange?: (sizes: number[]) => void }
ResizablePanel:      { defaultSize?: number; minSize?: number; maxSize?: number; id?: string }
ResizableHandle:     { withHandle?: boolean; step?: number; disabled?: boolean }
```

- [ ] **Step 1: Write the failing test**

```tsx
it("gives the tree and reader a draggable split", async () => {
  mockDocuments({ items: [DOC] })
  renderWorkspace()
  await screen.findByText("design.md")
  // The handle is the affordance; without it the panes are a fixed w-72 rail.
  // The library gives it role="separator" with aria-orientation (verified in
  // dist/chunk-ZU5NS2PO.js), so assert the accessible role, not a data
  // attribute that could change with a bundler bump.
  expect(await screen.findByRole("separator")).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/project-workspace.test.tsx`
Expected: FAIL — no resize handle in the tree.

- [ ] **Step 3: Write minimal implementation**

Replace the artifacts tab's `<div className="flex flex-col gap-5 lg:flex-row">`
with:

```tsx
<ResizablePanelGroup orientation="horizontal" className="min-h-[60vh]">
  <ResizablePanel defaultSize={26} minSize={15} maxSize={45} id="tree">
    <ScrollArea className="h-full pr-2">
      <RegionLabel>documents</RegionLabel>
      {/* the existing isError / isLoading / DocumentTree branches, unchanged */}
    </ScrollArea>
  </ResizablePanel>
  <ResizableHandle withHandle />
  <ResizablePanel defaultSize={74} id="reader">
    <ScrollArea className="h-full pl-2">
      {/* the existing selected / EmptyState branches, unchanged */}
    </ScrollArea>
  </ResizablePanel>
</ResizablePanelGroup>
```

Imports:

```tsx
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "darkraise-ui/components/resizable"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
```

Take the page full-bleed in `frontend/src/routes/_authenticated.tsx`, which is
where the caps live. Two lists, both matched with `pathname.startsWith(route)`:

```ts
const FULL_HEIGHT_ROUTES = ["/chat", "/projects/"] as const
const FULL_WIDTH_ROUTES = ["/chat", "/projects/"] as const
```

**Both, and the trailing slash matters twice.** `FULL_WIDTH_ROUTES` drops the
reading-width cap; `FULL_HEIGHT_ROUTES` gives `main` a definite height, without
which `h-full` resolves against an auto-height parent and **the resizable panes
collapse to zero with no error and an empty-looking page** — the failure that
file's own comment documents. The trailing slash keeps `/projects` (the index
card grid) capped, since only `/projects/<name>` is a workspace.

Do **not** add the route to `FULL_BLEED_ROUTES`: that list additionally means
"measures its own container with a ResizeObserver", which is a claim about the
canvas pages and false here.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run typecheck && npx vitest run src/features/documents`
Expected: PASS. Then `npm run build`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/documents/components/project-workspace.tsx \
        frontend/src/routes/_authenticated/projects_.\$project.tsx \
        frontend/src/features/documents/__tests__/project-workspace.test.tsx
git commit -m "feat(ui): full-bleed resizable artifacts frame"
```

---

### Task 5: Breadcrumb over the reader

**Implementer:** `dcc-superpower-companions:impl-sonnet-low`
**Evaluation:** spec completeness 1, coupling 1, risk 1, scale 1.
**Approach:** inline.

**Files:**
- Modify: `frontend/src/features/documents/components/project-workspace.tsx`
- Test: `frontend/src/features/documents/__tests__/project-workspace.test.tsx`

**Interfaces:**
- Consumes: `selected` (a `DocumentListItem` with a `uri`).
- Produces: nothing.

- [ ] **Step 1: Write the failing test**

```tsx
it("names where the open document lives", async () => {
  mockDocuments({ items: [DOC] })
  renderWorkspace()
  fireEvent.click(await screen.findByText("design.md"))
  // DOC.uri is "notes/design.md"; both segments must be readable.
  const crumbs = await screen.findByLabelText("document path")
  expect(crumbs).toHaveTextContent("notes")
  expect(crumbs).toHaveTextContent("design.md")
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/project-workspace.test.tsx`
Expected: FAIL — no element labelled `document path`.

- [ ] **Step 3: Write minimal implementation**

```tsx
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "darkraise-ui/components/breadcrumb"

function DocumentCrumbs({ uri }: { uri: string | null }) {
  if (!uri) return null
  const parts = uri.split("/").filter(Boolean)
  return (
    <Breadcrumb aria-label="document path" className="pb-2">
      <BreadcrumbList>
        {parts.map((part, i) => (
          <BreadcrumbItem key={`${part}-${i}`}>
            <BreadcrumbPage>{part}</BreadcrumbPage>
            {i < parts.length - 1 ? <BreadcrumbSeparator /> : null}
          </BreadcrumbItem>
        ))}
      </BreadcrumbList>
    </Breadcrumb>
  )
}
```

Render `<DocumentCrumbs uri={selected?.uri ?? null} />` immediately above the
`DocumentReader` inside the reader panel.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run typecheck && npm test && npm run build`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/documents/components/project-workspace.tsx \
        frontend/src/features/documents/__tests__/project-workspace.test.tsx
git commit -m "feat(ui): breadcrumb over the artifacts reader"
```

---

## Done when

- The Artifacts tab renders full-bleed with a draggable tree/reader split and
  independent scrolling.
- A fresh visit opens the top level only; opening a document opens its path;
  expansion survives a remount and is scoped per project.
- A breadcrumb names the open document's path.
- `npm run typecheck`, `npm test` and `npm run build` are green, and
  `./scripts/gate.sh` passes before the increment is called done.
- The four state branches and `focusBlockId` still behave — asserted by the
  existing tests, which must not be weakened to accommodate the new layout.

## Deliberately not in this increment

Context menus and document management (increment 3), the inspector pane and
related memories (increment 4), the markdown rendering defects (increment 2),
folder child counts and the command palette (spec §3.2, deferred with the
chord question), and the sticky outline rail (spec §3.3) — that one lives in
`document-reader.tsx`, which this increment deliberately does not touch, and it
is cheap to add once the reader sits inside a `ScrollArea`.

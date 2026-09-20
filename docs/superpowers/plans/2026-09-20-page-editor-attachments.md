# Page Editor Images and Files Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the operator put an image or a file into a page — uploaded from the editor by paste, drag-drop or the slash menu, rendered in place, and stored as ordinary markdown in the block's own text.

**Architecture:** BlockNote's built-in `image` and `file` block specs join the page schema. A paragraph whose whole text is one image, or one link to an attachment URL, reads as one of those blocks and writes back as the same paragraph text, gated by an emit-and-verify round trip so the save engine never rewrites a block it merely read. Upload goes through the raw-body attachment route shipped in sub-project 1, with its in-flight count tracked outside the sync tree so a tab closed mid-upload still warns.

**Deliberate departure from the spec:** spec §7.3 places the in-flight upload counter on `usePageEditor`. It lives in module scope in `lib/attachments.ts` instead, because `use-page-sync.ts` reads it from `anyPending()`, a module-level function over every engine with no editor in scope. The counter is therefore global across mounted editors, which is what the unload guard wants — it asks whether *any* work is outstanding.

**Tech Stack:** React 19, TypeScript, BlockNote 0.54.2, mdast / mdast-util-to-markdown, TanStack Query, vitest + @testing-library/react, darkraise-ui (sonner), FastAPI (one header change).

**Spec:** `docs/superpowers/specs/2026-09-20-page-editor-attachments-design.md`

**Execution:** inline — `claude --model sonnet --effort high` — two heavy tasks (3, 8) and three four-band tasks (4, 6, 9) out of eleven, so the majority is not heavy; the five are delegated and the six self-implemented tasks top out at total 3.

**Program:** `docs/superpowers/specs/2026-09-19-notion-import-design.md` — sub-project 3 of 4 — next: The Notion import route and its dialog (§4, §5.1)

## Global Constraints

- **English only** in code, comments, docs, commits, configs, errors and tests.
- **Comments carry the WHY, never the WHAT.** Add one only for a hidden constraint, a subtle invariant, or behaviour that would surprise a reader. Never reference the task, the plan or a ticket.
- **No new backend route and no new MCP tool is registered**, so the guards leg is not triggered. Do not add a `content_surfaces.py` entry or a `docs/two-door-parity.md` row: the two attachment routes already carry theirs from sub-project 1.
- **Frontend commands run from `frontend/`:** `npm run typecheck` (`tsc -b`; plain `tsc` misses the project refs), `npm test` (vitest), `npm run build`. `npm run lint` is advisory. **Never run `prettier --write` over the repo** — the tree is not prettier-clean and it reformats 200+ unrelated files.
- **Never run Playwright bare.** This plan adds no Playwright test.
- **Do not reformat a file you are editing.** Match the surrounding style: no semicolons, double quotes, 2-space indent, 100-column soft wrap.
- **Commit after every task** with `<type>(<scope>): <subject>`, subject ≤50 chars, imperative, no period.
- The editor is loaded lazily and must stay out of the main chunk: never import `@blocknote/*` from a module outside `features/notes/lib/`, `page-editor.tsx` or `use-page-editor.ts`.

## Contracts

Names one task produces and another consumes. Use them exactly as written.

- `frontend/src/features/notes/lib/attachments.ts` exports:
  - `ATTACHMENT_URL: RegExp` — the anchored attachment-URL pattern (Task 1).
  - `isAttachmentUrl(url: string): boolean` (Task 1).
  - `interface UploadedAttachment { url: string; contentType: string }` (Task 6).
  - `isImageType(contentType: string): boolean` (Task 6).
  - `uploadAttachment(pageId: string, file: File): Promise<UploadedAttachment>` (Task 6).
  - `uploadsInFlight(): number` (Task 6).
  - `subscribeUploads(listener: () => void): () => void` (Task 6).
  - `resetUploadsInFlight(): void` — test hook only (Task 6).
- `frontend/src/features/notes/__tests__/use-page-editor.test.tsx` holds one helper Tasks 4 and 8 share, added by Task 4 and used verbatim by Task 8:

  ```tsx
  async function mountEditor(pageId?: string, initialContent?: unknown[]) {
    let editor!: PageEditorInstance
    function Probe() {
      editor = usePageEditor((initialContent as EditorBlockLike[]) ?? BLOCKS, pageId)
      return <BlockNoteView editor={editor} />
    }
    render(<Probe />)
    await act(async () => {})
    return { editor }
  }
  ```

  The file's existing `mountHook()` returns the editor bare and takes no arguments; leave it and its callers alone.
- `frontend/src/features/notes/lib/inline-markdown.ts` exports:
  - `interface StandaloneFile { kind: "image" | "link"; url: string; name: string }` (Task 2).
  - `asStandaloneFile(text: string): StandaloneFile | null` (Task 2).
  - `fileMarkdown(kind: "image" | "link", url: string, name: string): string` (Task 2).
- `frontend/src/features/notes/lib/editor-schema.tsx`'s `pageSchema` gains block types `"file"` and `"image"` (Task 4). Their props are `url` and `name`; every other prop stays at its default.
- `frontend/src/features/notes/use-page-editor.ts` exports `usePageEditor(initialBlocks: EditorBlockLike[], pageId?: string): PageEditorInstance` (Task 4 adds the parameter; Task 8 gives it behaviour).
- `frontend/src/features/notes/page-editor.tsx`'s `PageEditorProps` gains `pageId?: string` (Task 7).
- The attachment URL served by the backend is `/api/v1/pages/attachments/<uuid>` and the upload response body is `{id, url, filename, content_type, size_bytes}` (`backend/app/api/routes/page_attachments.py:42-95`).

## Assumptions (evidence)

- BlockNote 0.54.2 is installed and exports `defaultBlockSpecs.file` / `defaultBlockSpecs.image` with props `url`, `name`, `caption`, `backgroundColor` (image also `showPreview`, `previewWidth`, `textAlignment`) — `frontend/node_modules/@blocknote/core/types/src/blocks/defaultBlocks.d.ts`, read 2026-09-20.
- `"file"` is the hardcoded fallback block type in BlockNote's file-insertion handler — `frontend/node_modules/@blocknote/core/dist/src-Buuo5l7X.js:1369`, read 2026-09-20.
- The `file` spec's `fileBlockAccept: ["*/*"]` matches nothing but an exactly equal type, because the matcher's wildcard branch compares the two type halves — `frontend/node_modules/@blocknote/core/dist/src-Buuo5l7X.js:1342`, read 2026-09-20. Task 5 pins the resulting behaviour.
- BlockNote replaces, rather than inserts after, any block whose content is an empty array — `frontend/node_modules/@blocknote/core/dist/src-Buuo5l7X.js:1348`, read 2026-09-20.
- The file block's wrapper swaps a "Loading…" element in on `onUploadStart` and has no completion reset — `frontend/node_modules/@blocknote/core/src/blocks/File/helpers/render/createFileBlockWrapper.ts:39-52`, read 2026-09-20.
- `FileDownloadButton` is exported from `@blocknote/react` — `frontend/node_modules/@blocknote/react/types/src/index.d.ts:33`, read 2026-09-20.
- The resize handle's class is `bn-resize-handle` — `frontend/node_modules/@blocknote/core/dist/blocks-Dol85hpH.js:2137`, read 2026-09-20.
- The cleanup job's reference pattern is `[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}` — `backend/app/services/page_attachment_cleanup.py:78`, read 2026-09-20.
- The CSP is declared twice and a test compares the two character for character — `backend/app/main.py:694-698`, `frontend/nginx.conf:29`, `backend/tests/test_edge_response_policy.py:88-93`, read 2026-09-20.
- vitest runs with `cwd` = `frontend/`, so `resolve("..", "backend", …)` reaches the backend — `frontend/src/features/notes/__tests__/blocknote-probe.test.tsx:31` resolves `node_modules` the same way, read 2026-09-20.
- `apiFetch` sets `Content-Type: application/json` and then spreads the caller's headers over it, so a caller can override it, and passes `body` through to `fetch` unchanged — `frontend/src/lib/api.ts:69-78`, read 2026-09-20.
- The route's inline image set is exactly `{image/png, image/jpeg, image/gif, image/webp}` — `backend/app/services/page_attachments.py:29` (`INLINE_IMAGE_TYPES`), read 2026-09-20.
- BlockNote's default slash-menu item keys for these two blocks are `"image"` and `"file"`, and the default item list is filtered by the schema, which is why neither appears today — `frontend/node_modules/@blocknote/core/dist/blocks-Dol85hpH.js:3341,3362`, read 2026-09-20.
- A block spec's accept list is reachable as `pageSchema.blockSpecs[type].implementation.meta.fileBlockAccept` — `frontend/node_modules/@blocknote/core/dist/src-Buuo5l7X.js:1370` reads it by that path, read 2026-09-20.
- **Two existing assertions go red on the schema change** and are corrected by name rather than discovered: `use-page-editor.test.tsx:49`'s `hidden` list contains `"Image"` and `"File"` (corrected in Task 4, same file), and `blocknote-probe.test.tsx:141-158` pins the exact default slash key array (corrected in Task 5). Read 2026-09-20. `blocknote-probe.test.tsx` is therefore red between Task 4's commit and Task 5's, which Task 4's Step 4 states.
- **Not pinned, deliberately:** that a dropped PNG becomes an `image` and a dropped PDF a `file`. Task 5 asserts each spec's declared `fileBlockAccept` instead, which would stay green if BlockNote changed its matcher so `*/*` began matching everything. The matcher is not exported, and driving a synthetic drop event through jsdom pins the test harness more than the library. Recorded in the spec's §12 rather than left as a silent gap.
- **unverified — Task 5 verifies it:** what BlockNote's follow-up `updateBlock(blockId, {props: {url}})` does when `blockId` is no longer a file block. Task 8's code is correct either way (the recovery insert has already placed the attachment), and spec §8 records a throw as a console-only limit.

## Task index

1. The attachment URL predicate
2. The standalone-file detector and its inverse
3. Mapping image and file blocks
4. The schema, the slash menu and the editor's page id
5. Library probes and the assertions the new block types move
6. Upload transport and the in-flight store
7. Threading the page id to the editor
8. The uploadFile behaviour
9. The unload guard and the saving indicator
10. The download button and the resize handle
11. The content-security-policy and the docs
12. Deploy and confirm the policy on the running instance

---

### Task 1: The attachment URL predicate

**Files:**
- Create: `frontend/src/features/notes/lib/attachments.ts`
- Create: `frontend/src/features/notes/__tests__/attachments.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `ATTACHMENT_URL` and `isAttachmentUrl` — see Contracts.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/notes/__tests__/attachments.test.ts`:

```ts
import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { describe, expect, it } from "vitest"
import { ATTACHMENT_URL, isAttachmentUrl } from "../lib/attachments"

const CLEANUP_JOB = resolve("..", "backend", "app", "services", "page_attachment_cleanup.py")
const ID = "0123abcd-4567-89ef-0123-456789abcdef"

describe("isAttachmentUrl", () => {
  it("ends in the cleanup job's own character class", () => {
    const source = readFileSync(CLEANUP_JOB, "utf8")
    const pattern = /'\/api\/v1\/pages\/attachments\/\(([^']+)\)'/.exec(source)
    expect(pattern).not.toBeNull()
    expect(ATTACHMENT_URL.source.endsWith(`${pattern![1]}$`)).toBe(true)
  })

  it("accepts a served attachment url", () => {
    expect(isAttachmentUrl(`/api/v1/pages/attachments/${ID}`)).toBe(true)
  })

  it("accepts an uppercase id, which the cleanup job retains", () => {
    expect(isAttachmentUrl(`/api/v1/pages/attachments/${ID.toUpperCase()}`)).toBe(true)
  })

  it("rejects a value of the right length that is not a uuid", () => {
    expect(isAttachmentUrl(`/api/v1/pages/attachments/${"-".repeat(36)}`)).toBe(false)
  })

  it("rejects a different path, a suffix and an empty string", () => {
    expect(isAttachmentUrl(`/api/v1/documents/attachments/${ID}`)).toBe(false)
    expect(isAttachmentUrl(`/api/v1/pages/attachments/${ID}/raw`)).toBe(false)
    expect(isAttachmentUrl("")).toBe(false)
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/attachments.test.ts`
Expected: FAIL — `Failed to resolve import "../lib/attachments"`.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/features/notes/lib/attachments.ts`:

```ts
/** The attachment URL, anchored, in the one spelling the whole feature uses.
 *
 *  The character class is `page_attachment_cleanup`'s own: that job scans
 *  `blocks.text` for this shape to decide which files are still referenced,
 *  and it deliberately retains an uppercase id. A looser class would be wrong
 *  in both directions — it would reject a URL the job keeps alive, and accept
 *  a malformed one the serving route answers 422 for. */
export const ATTACHMENT_URL =
  /^\/api\/v1\/pages\/attachments\/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/

export function isAttachmentUrl(url: string): boolean {
  return ATTACHMENT_URL.test(url)
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/attachments.test.ts`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/lib/attachments.ts frontend/src/features/notes/__tests__/attachments.test.ts
git commit -m "feat(notes): add the attachment url predicate"
```

---

### Task 2: The standalone-file detector and its inverse

**Files:**
- Modify: `frontend/src/features/notes/lib/inline-markdown.ts`
- Modify: `frontend/src/features/notes/__tests__/inline-markdown.test.ts`

**Interfaces:**
- Consumes: `isAttachmentUrl` — see Contracts.
- Produces: `StandaloneFile`, `asStandaloneFile`, `fileMarkdown` — see Contracts.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/features/notes/__tests__/inline-markdown.test.ts`. Add `asStandaloneFile` and `fileMarkdown` to the existing import from `../lib/inline-markdown`.

```ts
const ATTACHMENT = "/api/v1/pages/attachments/0123abcd-4567-89ef-0123-456789abcdef"

describe("asStandaloneFile", () => {
  it("reads a whole-paragraph image at any url", () => {
    expect(asStandaloneFile(`![shot](${ATTACHMENT})`)).toEqual({
      kind: "image", url: ATTACHMENT, name: "shot",
    })
    expect(asStandaloneFile("![d](https://example.org/d.png)")).toEqual({
      kind: "image", url: "https://example.org/d.png", name: "d",
    })
  })

  it("reads a whole-paragraph link only when it points at an attachment", () => {
    expect(asStandaloneFile(`[notes.pdf](${ATTACHMENT})`)).toEqual({
      kind: "link", url: ATTACHMENT, name: "notes.pdf",
    })
    expect(asStandaloneFile("[docs](https://example.org/)")).toBeNull()
  })

  // An empty destination round-trips byte for byte, so the emit-and-verify
  // gate accepts it. A block carrying an empty url is dropped when the tree
  // is written, so taking this one would delete the paragraph from the
  // editor while the server still holds it.
  it("rejects an empty destination", () => {
    expect(asStandaloneFile("![draft]()")).toBeNull()
    expect(asStandaloneFile("[draft]()")).toBeNull()
  })

  it("rejects anything that is not the whole paragraph", () => {
    expect(asStandaloneFile(`see ![shot](${ATTACHMENT})`)).toBeNull()
    expect(asStandaloneFile(`![a](${ATTACHMENT}) ![b](${ATTACHMENT})`)).toBeNull()
    expect(asStandaloneFile(`![shot](${ATTACHMENT} "title")`)).toBeNull()
    expect(asStandaloneFile("plain text")).toBeNull()
    expect(asStandaloneFile("")).toBeNull()
  })

  // The writer escapes both labels and destinations, so a bracket or a
  // parenthesis is not by itself a reason to refuse: only a spelling the
  // writer would rewrite is.
  it("accepts a canonical escaped spelling and refuses one the writer rewrites", () => {
    expect(asStandaloneFile("![a\\[b\\]](https://example.org/x.png)")).toEqual({
      kind: "image", url: "https://example.org/x.png", name: "a[b]",
    })
    expect(asStandaloneFile("![a](<https://example.org/x.png>)")).toBeNull()
  })
})

describe("fileMarkdown", () => {
  it("is the inverse of the detector for everything it accepts", () => {
    for (const text of [
      `![shot](${ATTACHMENT})`,
      `[notes.pdf](${ATTACHMENT})`,
      "![d](https://example.org/d.png)",
      "![a\\[b\\]](https://example.org/x.png)",
      `![](${ATTACHMENT})`,
    ]) {
      const read = asStandaloneFile(text)
      expect(read, text).not.toBeNull()
      expect(fileMarkdown(read!.kind, read!.url, read!.name)).toBe(text)
    }
  })

  it("emits a link with no text as an empty label", () => {
    expect(fileMarkdown("link", ATTACHMENT, "")).toBe(`[](${ATTACHMENT})`)
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/inline-markdown.test.ts`
Expected: FAIL — `asStandaloneFile is not a function` (or an import error).

- [ ] **Step 3: Write the implementation**

In `frontend/src/features/notes/lib/inline-markdown.ts`, add `Image`, `Link` and `Paragraph` to the existing `import type { … } from "mdast"` list, and add `import { isAttachmentUrl } from "./attachments"` beside the other relative imports. Then append to the end of the file:

```ts
/** A paragraph that is exactly one image, or exactly one link to an
 *  attachment: the two shapes the editor shows as a block of its own rather
 *  than as text. */
export interface StandaloneFile {
  kind: "image" | "link"
  url: string
  name: string
}

/** The markdown for one of those shapes, written through the same writer
 *  `emitInline` uses so escaping is decided in one place. */
export function fileMarkdown(kind: "image" | "link", url: string, name: string): string {
  const node: Image | Link =
    kind === "image"
      ? { type: "image", url, alt: name }
      : { type: "link", url, children: name === "" ? [] : [{ type: "text", value: name }] }
  const paragraph: Paragraph = { type: "paragraph", children: [node] }
  const out = toMarkdown(paragraph, {
    emphasis: "*",
    strong: "*",
    extensions: [gfmStrikethroughToMarkdown()],
  })
  return out.endsWith("\n") ? out.slice(0, -1) : out
}

/** `text` as a standalone file, or null when it is ordinary text.
 *
 *  Two gates, and neither implies the other. Re-emitting must reproduce
 *  `text` byte for byte, or reading a page would rewrite the block the save
 *  engine had just read. And the destination must be non-empty: `![draft]()`
 *  does reproduce itself, but a block with an empty url is dropped on the way
 *  back out, so accepting one would lose the paragraph from the editor while
 *  the server still holds it. Idempotence is not preservation. */
export function asStandaloneFile(text: string): StandaloneFile | null {
  if (text === "") return null
  const tree: Root = fromMarkdown(text, {
    extensions: [gfmStrikethrough(), { disable: { null: FLOW_CONSTRUCTS } }],
    mdastExtensions: [gfmStrikethroughFromMarkdown()],
  })
  const paragraph = tree.children[0]
  if (
    tree.children.length !== 1 ||
    paragraph?.type !== "paragraph" ||
    paragraph.position!.start.offset !== 0 ||
    paragraph.position!.end.offset !== text.length ||
    paragraph.children.length !== 1
  ) {
    return null
  }
  const node = paragraph.children[0]!
  if (node.type === "image") {
    if (node.title) return null
    return verified({ kind: "image", url: node.url, name: node.alt ?? "" }, text)
  }
  if (node.type === "link") {
    if (node.title || !isAttachmentUrl(node.url)) return null
    if (!node.children.every((child) => child.type === "text")) return null
    const name = node.children.map((child) => (child as Text).value).join("")
    return verified({ kind: "link", url: node.url, name }, text)
  }
  return null
}

function verified(candidate: StandaloneFile, text: string): StandaloneFile | null {
  if (candidate.url === "") return null
  return fileMarkdown(candidate.kind, candidate.url, candidate.name) === text ? candidate : null
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/inline-markdown.test.ts && npm run typecheck`
Expected: every test PASSES and typecheck exits 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/lib/inline-markdown.ts frontend/src/features/notes/__tests__/inline-markdown.test.ts
git commit -m "feat(notes): detect a standalone image or file link"
```

---

### Task 3: Mapping image and file blocks

**Files:**
- Modify: `frontend/src/features/notes/lib/block-mapping.ts`
- Modify: `frontend/src/features/notes/__tests__/block-mapping.test.tsx`

**Interfaces:**
- Consumes: `asStandaloneFile`, `fileMarkdown` — see Contracts. Emits editor blocks of the types `pageSchema` gains in Task 4; this task does not need the schema to compile, because `toEditorBlocks` returns `EditorBlockLike`.
- Produces: nothing a later task imports.

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/features/notes/__tests__/block-mapping.test.tsx`. Add `fromPageBlocks` to the existing import if it is not already there.

```ts
const URL_A = "/api/v1/pages/attachments/0123abcd-4567-89ef-0123-456789abcdef"

describe("image and file blocks", () => {
  it("reads an image paragraph as an image block and writes it back", () => {
    const stored: SyncBlock[] = [b("p", null, "paragraph", `![shot](${URL_A})`)]
    const { blocks } = toEditorBlocks(stored)
    expect(blocks).toEqual([
      { id: "p", type: "image", props: { url: URL_A, name: "shot" }, content: undefined, children: [] },
    ])
    expect(canonicalTree(stored).tree).toEqual(stored)
  })

  it("reads an attachment link as a file block and writes it back", () => {
    const stored: SyncBlock[] = [b("p", null, "paragraph", `[notes.pdf](${URL_A})`)]
    const { blocks } = toEditorBlocks(stored)
    expect(blocks[0]!.type).toBe("file")
    expect(blocks[0]!.props).toEqual({ url: URL_A, name: "notes.pdf" })
    expect(canonicalTree(stored).tree).toEqual(stored)
  })

  it("leaves an external link and an image inside text as paragraphs", () => {
    const stored: SyncBlock[] = [
      b("a", null, "paragraph", "[docs](https://example.org/)"),
      b("c", null, "paragraph", `see ![shot](${URL_A})`),
    ]
    expect(toEditorBlocks(stored).blocks.every((x) => x.type === "paragraph")).toBe(true)
    expect(canonicalTree(stored).tree).toEqual(stored)
  })

  // The detector refuses an empty destination for exactly this reason: the
  // write side drops a block with no url, so accepting one here would make
  // reading the page delete the paragraph.
  it("keeps a paragraph whose image has no destination", () => {
    const stored: SyncBlock[] = [b("p", null, "paragraph", "![draft]()")]
    expect(toEditorBlocks(stored).blocks[0]!.type).toBe("paragraph")
    expect(canonicalTree(stored).tree).toEqual(stored)
  })

  it("omits an image or file block that has no url", () => {
    const blocks: EditorBlockLike[] = [
      { id: "a", type: "image", props: { url: "", name: "x.png" }, content: undefined, children: [] },
      { id: "b", type: "file", props: { url: "", name: "x.pdf" }, content: undefined, children: [] },
      { id: "c", type: "paragraph", props: {}, content: [{ type: "text", text: "kept", styles: {} }], children: [] },
    ]
    const { tree } = toSyncTree(blocks, [], new Map(), () => "never")
    expect(tree.map((x) => x.id)).toEqual(["c"])
  })

  // The cleanup job finds a referenced attachment by scanning `blocks.text`,
  // so what this mapping writes has to be what that scan matches.
  it("writes a url the cleanup job's scan finds", () => {
    const blocks: EditorBlockLike[] = [
      { id: "a", type: "image", props: { url: URL_A, name: "shot" }, content: undefined, children: [] },
    ]
    const { tree } = toSyncTree(blocks, [], new Map(), () => "never")
    expect(tree[0]!.type).toBe("paragraph")
    expect(
      /\/api\/v1\/pages\/attachments\/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})/.test(
        tree[0]!.text,
      ),
    ).toBe(true)
  })

  it("is a fixed point over a page holding both", () => {
    const stored: SyncBlock[] = [
      b("i", null, "paragraph", `![shot](${URL_A})`),
      b("f", null, "paragraph", `[notes.pdf](${URL_A})`),
    ]
    const once = canonicalTree(stored).tree
    expect(canonicalTree(once).tree).toEqual(once)
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/block-mapping.test.tsx`
Expected: FAIL — the first test reports `type: "paragraph"` where `"image"` was expected.

- [ ] **Step 3: Write the implementation**

In `frontend/src/features/notes/lib/block-mapping.ts`, extend the existing import from `./inline-markdown` to `import { asStandaloneFile, emitInline, fileMarkdown, parseInline, type InlineNode } from "./inline-markdown"`.

Inside `toEditorBlocks`, in the `build` function, insert this immediately before `switch (block.type) {`:

```ts
    // A paragraph that is exactly one image, or one link to an attachment,
    // is shown as a block rather than as the markdown that spells it. The
    // detector refuses an empty destination, so no block built here can
    // carry the empty url `toSyncTree` drops.
    if (block.type === "paragraph") {
      const file = asStandaloneFile(block.text)
      if (file) {
        return {
          ...base,
          type: file.kind === "image" ? "image" : "file",
          props: { url: file.url, name: file.name },
          content: undefined,
        }
      }
    }
```

Inside `toSyncTree`, in the `walk` function's switch, add this case immediately above `default:`:

```ts
      case "image":
      case "file": {
        const url = String(block.props.url ?? "")
        // A block with no url is the placeholder the editor shows before a
        // file is chosen, or what a failed upload left behind. Neither is
        // content, so neither is stored -- and returning here skips the
        // children walk, which is right because the nesting rule gives these
        // blocks none.
        if (url === "") return
        push(
          "paragraph",
          fileMarkdown(block.type === "image" ? "image" : "link", url, String(block.props.name ?? "")),
          null,
        )
        break
      }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/block-mapping.test.tsx src/features/notes/__tests__/page-sync.test.ts src/features/notes/__tests__/sync-tree.test.ts && npm run typecheck`
Expected: every test PASSES and typecheck exits 0. If an existing `block-mapping` fixture regresses, it is because it holds a paragraph that is exactly one image or one attachment link; that is the intended change — update the fixture's expectation, never the mapping.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/lib/block-mapping.ts frontend/src/features/notes/__tests__/block-mapping.test.tsx
git commit -m "feat(notes): map image and file blocks to markdown"
```

---

### Task 4: The schema, the slash menu and the editor's page id

**Files:**
- Modify: `frontend/src/features/notes/lib/editor-schema.tsx`
- Modify: `frontend/src/features/notes/use-page-editor.ts`
- Modify: `frontend/src/features/notes/__tests__/use-page-editor.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: `pageSchema`'s `"file"` and `"image"` block types, and `usePageEditor`'s second parameter — see Contracts. Task 8 fills that parameter's behaviour; this task only accepts and ignores it.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

Two edits to `frontend/src/features/notes/__tests__/use-page-editor.test.tsx`.

First, at line 49, the existing `hidden` list asserts these two titles are absent. They are about to be present on purpose, so drop them from it and leave the other four:

```ts
    for (const hidden of ["Heading 4", "Emoji", "Video", "Audio"]) expect(titles).not.toContain(hidden)
```

Second, add the shared helper from Contracts beside the file's existing `mountHook`, and append the new cases:

```tsx
async function mountEditor(pageId?: string, initialContent?: unknown[]) {
  let editor!: PageEditorInstance
  function Probe() {
    editor = usePageEditor((initialContent as EditorBlockLike[]) ?? BLOCKS, pageId)
    return <BlockNoteView editor={editor} />
  }
  render(<Probe />)
  await act(async () => {})
  return { editor }
}
```

```ts
describe("the page schema's file blocks", () => {
  it("carries a block type spelled exactly file", () => {
    // BlockNote's drop handler falls back to this literal type name when no
    // spec accepts the dropped MIME type, so the spelling is load-bearing.
    expect(Object.keys(pageSchema.blockSchema)).toContain("file")
    expect(Object.keys(pageSchema.blockSchema)).toContain("image")
  })

  it("offers image and file in the slash menu", async () => {
    const { editor } = await mountEditor()
    const titles = pageSlashItems(editor, "").map((item) => item.title.toLowerCase())
    expect(titles.some((t) => t.includes("image"))).toBe(true)
    expect(titles.some((t) => t.includes("file"))).toBe(true)
  })

  it("takes a page id without changing anything else", async () => {
    const { editor } = await mountEditor("11111111-2222-3333-4444-555555555555")
    expect(editor.document.length).toBeGreaterThanOrEqual(0)
  })
})
```

Add `pageSchema` to the file's import from `../lib/editor-schema`, and `EditorBlockLike` from `../lib/block-mapping` if it is not imported already.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/use-page-editor.test.tsx`
Expected: FAIL — `blockSchema` has no `file` key, and `usePageEditor` takes one argument.

- [ ] **Step 3: Write the implementation**

In `frontend/src/features/notes/lib/editor-schema.tsx`, add two entries to `pageSchema`'s `blockSpecs`, after `table` and before `divider`:

```ts
    // `file` must be spelled exactly this: it is the literal type BlockNote's
    // drop handler falls back to when no spec accepts a dropped file's type.
    // Their order does not matter -- the installed matcher's wildcard branch
    // compares the two type halves, so the file spec's `*/*` matches nothing
    // but an exactly equal type, and a PNG can only match `image/*`.
    file: defaultBlockSpecs.file,
    image: defaultBlockSpecs.image,
```

In `frontend/src/features/notes/use-page-editor.ts`, add `"image"` and `"file"` to `SLASH_KEYS` after `"table"`, and change the hook's signature and its doc comment:

```ts
/** A page editor instance: the page schema and options, with the nesting
 *  rule installed as a transaction filter. `pageId` is the page attachments
 *  are uploaded for; without one the editor has no upload path at all, which
 *  is what keeps demo mode from making a request. */
export function usePageEditor(
  initialBlocks: EditorBlockLike[],
  pageId?: string,
): PageEditorInstance {
```

Leave `pageId` unused in this task: put `void pageId` immediately after the signature, with no comment, so `tsc`'s `noUnusedParameters` does not flag it. Task 8 deletes that line.

The `SLASH_KEYS` doc comment above it says "emoji and every file block are out", which this task makes false. Rewrite that sentence to "emoji is out; the image and file blocks are offered".

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/use-page-editor.test.tsx && npm run typecheck`
Expected: every test in that file PASSES and typecheck exits 0.

**`blocknote-probe.test.tsx` is now red and stays red until Task 5.** Its
`offers these slash menu keys` case pins the exact array BlockNote's default
item list returns, and that list is filtered by the schema, so the two block
types added here add the keys `"image"` and `"file"` to it. Do not touch that
file here; Task 5 owns it. Run only the command above, not the whole
`src/features/notes` directory.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/lib/editor-schema.tsx frontend/src/features/notes/use-page-editor.ts frontend/src/features/notes/__tests__/use-page-editor.test.tsx
git commit -m "feat(notes): add image and file blocks to the schema"
```

---

### Task 5: Library probes and the assertions the new block types move

**Files:**
- Modify: `frontend/src/features/notes/__tests__/blocknote-probe.test.tsx`
- Modify: `frontend/src/features/notes/__tests__/nesting-guard.test.tsx`

**Interfaces:**
- Consumes: `pageSchema`'s new block types — see Contracts.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2

This task is not test-first: Task 4 already changed the library's behaviour, so
these assertions are written to pass. One of them is currently red and is being
repaired; the rest are new probes recording facts the feature relies on.

- [ ] **Step 1: Repair the red slash-key assertion**

`blocknote-probe.test.tsx`'s `offers these slash menu keys` case pins the exact
array `getDefaultReactSlashMenuItems` returns. That list is filtered by the
schema, so Task 4's two block types added `"image"` and `"file"` to it.

Run: `cd frontend && npx vitest run src/features/notes/__tests__/blocknote-probe.test.tsx`
Expected: FAIL, with the received array printed.

Add `"image"` and `"file"` to the expected array **at the positions the failure
prints**. Do not guess them: BlockNote's default item order is not part of any
contract this plan can cite, and the point of the assertion is that the order is
pinned, not that it is predicted.

- [ ] **Step 2: Add the drop-routing and update probes**

Append to `frontend/src/features/notes/__tests__/blocknote-probe.test.tsx`:

```tsx
describe("file blocks", () => {
  // What each spec says it accepts. This pins the schema's own metadata, not
  // BlockNote's matcher: the handler reads `fileBlockAccept` by exactly this
  // path, so a spec that stopped declaring it would route drops elsewhere.
  it("declares the accept lists the drop handler reads", () => {
    const specs = pageSchema.blockSpecs as unknown as Record<
      string,
      { implementation: { meta?: { fileBlockAccept?: string[] } } }
    >
    const meta = (type: string) => specs[type]?.implementation.meta?.fileBlockAccept
    expect(meta("image")).toEqual(["image/*"])
    expect(meta("file")).toEqual(["*/*"])
  })

  // The block wrapper swaps its add-file button for a "Loading..." element
  // when an upload starts and resets it only when the node view is rebuilt.
  // Setting `url` to the "" it already holds is not a change, so the failure
  // path retypes the block instead. This pins that the retype is a change.
  it("retypes a placeholder even though setting its url again is not a change", async () => {
    const { editor } = await mount([{ type: "image", props: { url: "", name: "x.png" } }])
    await act(async () => {
      editor.updateBlock(editor.document[0]!, { props: { url: "" } } as never)
    })
    expect(editor.document[0]!.type).toBe("image")
    await act(async () => {
      editor.updateBlock(editor.document[0]!, { type: "paragraph", content: [] } as never)
    })
    expect(editor.document[0]!.type).toBe("paragraph")
  })

  // The one fact the plan's Assumptions record as unverified. After an upload
  // whose block the nesting rule refused to convert, BlockNote updates the
  // original id with the url anyway -- on a block that has no `url` prop. This
  // records whether that is inert or throws; either way the recovery insert in
  // `use-page-editor.ts` has already placed the attachment, so the answer
  // changes no code. It is written down so the next reader does not have to
  // re-derive it, and so an upgrade that changes it is visible.
  //
  // It reaches the paragraph by retyping rather than by a refused conversion,
  // which is a proxy: the question is what a write of an undeclared prop does,
  // and how the block came to lack that prop does not change the answer.
  it("records what setting a foreign prop on a paragraph does", async () => {
    const { editor } = await mount([{ type: "image", props: { url: "", name: "x.png" } }])
    const id = editor.document[0]!.id
    await act(async () => {
      editor.updateBlock(id, { type: "paragraph", content: [] } as never)
    })
    let thrown: unknown = null
    await act(async () => {
      try {
        editor.updateBlock(id, { props: { url: "https://example.org/x.png" } } as never)
      } catch (error) {
        thrown = error
      }
    })
    // Whichever branch holds, the block must still be a paragraph and the page
    // must still be intact.
    expect(editor.document[0]!.type).toBe("paragraph")
    expect(editor.document).toHaveLength(1)
    // Record the observed behaviour. If this assertion fails, flip it and note
    // the flip in the ledger -- it is a recording, not a requirement.
    expect(thrown).toBeNull()
  })
})
```

Append to `frontend/src/features/notes/__tests__/nesting-guard.test.tsx`:

```tsx
it("refuses a child under an image or a file block", async () => {
  let editor!: PageEditorInstance
  function Probe() {
    editor = useCreateBlockNote({
      schema: pageSchema,
      trailingBlock: false,
      initialContent: [
        { id: "i", type: "image", props: { url: "https://example.org/x.png", name: "x.png" } },
        {
          id: "f",
          type: "file",
          props: { url: "/api/v1/pages/attachments/0123abcd-4567-89ef-0123-456789abcdef", name: "n.pdf" },
        },
        { id: "p", type: "paragraph", content: "p" },
      ],
    })
    return <BlockNoteView editor={editor} />
  }
  render(<Probe />)
  await act(async () => {})
  editor.onBeforeChange(({ tr }) => (addsNestingViolation(tr.before, tr.doc) ? false : undefined))
  const shape = () => JSON.stringify(editor.document.map((x) => [x.id, x.type, x.children.map((c) => c.id)]))
  const start = shape()

  editor.updateBlock("i", { children: [{ id: "ic", type: "paragraph", content: "x" }] })
  expect(shape()).toBe(start)

  editor.updateBlock("f", { children: [{ id: "fc", type: "paragraph", content: "x" }] })
  expect(shape()).toBe(start)
})
```

Add `describe` to the probe file's vitest import if it is not there, and
`pageSchema`, `useCreateBlockNote`, `BlockNoteView`, `PageEditorInstance` to the
nesting file's imports if any are missing.

- [ ] **Step 3: Run both files to verify they pass**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/blocknote-probe.test.tsx src/features/notes/__tests__/nesting-guard.test.tsx && npm run typecheck`
Expected: PASS, and typecheck exits 0.

If the `records what setting a foreign prop on a paragraph does` case fails on
its last assertion, the library throws rather than ignoring the write: flip
that assertion to `expect(thrown).not.toBeNull()`, keep going, and record the
observation in the ledger. Any other failure stops the plan.

- [ ] **Step 4: Run the whole notes suite, which is green again**

Run: `cd frontend && npx vitest run src/features/notes`
Expected: every test PASSES. Task 4 left this directory red on purpose; it is
this step that closes it.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/__tests__/blocknote-probe.test.tsx frontend/src/features/notes/__tests__/nesting-guard.test.tsx
git commit -m "test(notes): pin file block routing and nesting"
```

---

### Task 6: Upload transport and the in-flight store

**Files:**
- Modify: `frontend/src/features/notes/lib/attachments.ts`
- Modify: `frontend/src/features/notes/__tests__/attachments.test.ts`

**Interfaces:**
- Consumes: `apiFetch` from `@/lib/api`.
- Produces: `UploadedAttachment`, `isImageType`, `uploadAttachment`, `uploadsInFlight`, `subscribeUploads`, `resetUploadsInFlight` — see Contracts.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/features/notes/__tests__/attachments.test.ts`, adding `afterEach`, `beforeEach` and `vi` to the vitest import and the new names to the module import:

```ts
const UPLOADED = { id: ID, url: `/api/v1/pages/attachments/${ID}`, filename: "x.png", content_type: "image/png", size_bytes: 3 }

// The parameters are declared even though the body ignores them: the mock's
// call tuple is what the first test destructures, and `noUnusedParameters` is
// on, so they carry the leading underscore.
function stubFetch(body: unknown, status = 201) {
  const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) =>
    new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } }),
  )
  vi.stubGlobal("fetch", fetchMock)
  return fetchMock
}

describe("uploadAttachment", () => {
  beforeEach(() => resetUploadsInFlight())
  afterEach(() => vi.unstubAllGlobals())

  it("sends the file as the raw body with an encoded filename", async () => {
    const fetchMock = stubFetch(UPLOADED)
    const file = new File(["abc"], "a b/c.png", { type: "image/png" })
    const result = await uploadAttachment("page-1", file)
    expect(result).toEqual({ url: UPLOADED.url, contentType: "image/png" })
    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toBe("/api/v1/pages/page-1/attachments")
    expect(init!.method).toBe("POST")
    expect(init!.body).toBe(file)
    const headers = init!.headers as Record<string, string>
    expect(headers["X-Filename"]).toBe(encodeURIComponent("a b/c.png"))
    expect(headers["Content-Type"]).toBe("application/octet-stream")
  })

  it("counts an upload in flight and notifies subscribers", async () => {
    stubFetch(UPLOADED)
    const seen: number[] = []
    const stop = subscribeUploads(() => seen.push(uploadsInFlight()))
    await uploadAttachment("page-1", new File(["abc"], "a.png"))
    stop()
    expect(seen).toEqual([1, 0])
    expect(uploadsInFlight()).toBe(0)
  })

  it("decrements the count when the upload is refused", async () => {
    stubFetch({ detail: "attachment exceeds 52428800 bytes" }, 413)
    await expect(uploadAttachment("page-1", new File(["abc"], "a.png"))).rejects.toThrow(
      "attachment exceeds",
    )
    expect(uploadsInFlight()).toBe(0)
  })
})

describe("isImageType", () => {
  it("is the four types the route serves inline", () => {
    for (const t of ["image/png", "image/jpeg", "image/gif", "image/webp"]) {
      expect(isImageType(t)).toBe(true)
    }
    expect(isImageType("image/svg+xml")).toBe(false)
    expect(isImageType("application/octet-stream")).toBe(false)
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/attachments.test.ts`
Expected: FAIL — `uploadAttachment is not a function`.

- [ ] **Step 3: Write the implementation**

Add the import at the top of `frontend/src/features/notes/lib/attachments.ts`, beside nothing (the file has no imports yet):

```ts
import { apiFetch } from "@/lib/api"
```

Then append the rest to the end of that file:

```ts
export interface UploadedAttachment {
  url: string
  contentType: string
}

/** The four types the serving route sniffs and serves inline. Everything else
 *  it stores as `application/octet-stream` and serves as a download, so an
 *  image block pointing at one would render nothing. */
const INLINE_IMAGE_TYPES: ReadonlySet<string> = new Set([
  "image/png",
  "image/jpeg",
  "image/gif",
  "image/webp",
])

export function isImageType(contentType: string): boolean {
  return INLINE_IMAGE_TYPES.has(contentType)
}

/** Uploads in flight, counted across every mounted editor.
 *
 *  It lives outside the sync tree because a block whose upload has not
 *  resolved carries no url and so appears in no tree: without this count the
 *  save engine reports "saved" and the unload warning stays silent while a
 *  file is still going up. Module scope rather than editor scope because the
 *  reader is `use-page-sync`'s `anyPending`, which runs over every engine with
 *  no editor in hand -- and "is any work outstanding" is the question the
 *  unload guard actually asks. */
let inFlight = 0
const listeners = new Set<() => void>()

export function uploadsInFlight(): number {
  return inFlight
}

export function subscribeUploads(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/** Test hook: forget the count between tests. */
export function resetUploadsInFlight(): void {
  inFlight = 0
  listeners.clear()
}

function setInFlight(next: number) {
  inFlight = next
  for (const listener of listeners) listener()
}

export async function uploadAttachment(pageId: string, file: File): Promise<UploadedAttachment> {
  setInFlight(inFlight + 1)
  try {
    const data = await apiFetch<{ url: string; content_type: string }>(
      `/pages/${pageId}/attachments`,
      {
        method: "POST",
        body: file,
        headers: {
          // The route ignores the request's own type and sniffs the bytes, so
          // this only stops the shared helper's JSON default from being sent.
          "Content-Type": "application/octet-stream",
          "X-Filename": encodeURIComponent(file.name),
        },
      },
    )
    return { url: data.url, contentType: data.content_type }
  } finally {
    setInFlight(inFlight - 1)
  }
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/attachments.test.ts && npm run typecheck`
Expected: every test PASSES and typecheck exits 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/lib/attachments.ts frontend/src/features/notes/__tests__/attachments.test.ts
git commit -m "feat(notes): upload an attachment and count it in flight"
```

---

### Task 7: Threading the page id to the editor

**Files:**
- Modify: `frontend/src/features/notes/page-editor.tsx`
- Modify: `frontend/src/features/notes/page-pane.tsx`
- Modify: `frontend/src/features/notes/__tests__/page-pane.test.tsx`
- Modify: `frontend/src/features/notes/__tests__/page-editor.test.tsx`

**Interfaces:**
- Consumes: `usePageEditor`'s second parameter — see Contracts.
- Produces: `PageEditorProps.pageId` — see Contracts.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2

- [ ] **Step 1: Write the failing test**

In `frontend/src/features/notes/__tests__/page-pane.test.tsx`, widen the existing
`PageEditor` mock so it renders the prop, then assert on it:

```tsx
vi.mock("../page-editor", () => ({
  PageEditor: ({ editable, pageId }: { editable: boolean; pageId?: string }) => (
    <div data-page-id={pageId}>editor {editable ? "editable" : "read-only"}</div>
  ),
}))
```

```tsx
it("gives the editor the page it is showing", () => {
  const { container } = render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
  expect(container.querySelector(`[data-page-id="${PAGE.id}"]`)).not.toBeNull()
})
```

Append to `frontend/src/features/notes/__tests__/page-editor.test.tsx`:

```tsx
it("carries its page id on the editor root", () => {
  const { container } = render(<PageEditor initialBlocks={BLOCKS} editable pageId="page-7" />)
  expect(container.querySelector('[data-page-id="page-7"]')).not.toBeNull()
})

it("renders without one, which is what demo mode passes", () => {
  const { container } = render(<PageEditor initialBlocks={BLOCKS} editable={false} />)
  expect(container.querySelector("[data-page-id]")).toBeNull()
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/page-pane.test.tsx src/features/notes/__tests__/page-editor.test.tsx`
Expected: FAIL — no element carries `data-page-id`, and `PageEditor` has no `pageId` prop.

- [ ] **Step 3: Write the implementation**

In `frontend/src/features/notes/page-editor.tsx`:

```ts
export interface PageEditorProps {
  initialBlocks: EditorBlockLike[]
  editable: boolean
  /** The page attachments are uploaded for. Omitted in demo mode, which must
   *  make no request, so the editor then has no upload path at all. */
  pageId?: string
  onDocumentChange?: (blocks: EditorBlockLike[]) => void
  onBlur?: () => void
}

export function PageEditor({ initialBlocks, editable, pageId, onDocumentChange, onBlur }: PageEditorProps) {
  const mode = useDocumentMode()
  const editor = usePageEditor(initialBlocks, pageId)
```

and add `data-page-id={pageId}` to the `<div ref={editorRoot} className="max-w-3xl">` element.

In `frontend/src/features/notes/page-pane.tsx`, add `pageId={page.id}` to the `<PageEditor …>` element's props.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/features/notes && npm run typecheck`
Expected: every test PASSES and typecheck exits 0. `demo-notes.test.tsx` must stay green: it renders `PageEditor` with no `pageId`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/page-editor.tsx frontend/src/features/notes/page-pane.tsx frontend/src/features/notes/__tests__/page-pane.test.tsx frontend/src/features/notes/__tests__/page-editor.test.tsx
git commit -m "feat(notes): give the editor its page id"
```

---

### Task 8: The uploadFile behaviour

**Files:**
- Modify: `frontend/src/features/notes/use-page-editor.ts`
- Modify: `frontend/src/features/notes/__tests__/use-page-editor.test.tsx`

**Interfaces:**
- Consumes: `uploadAttachment`, `isImageType`, `UploadedAttachment` — see Contracts.
- Produces: nothing a later task imports.

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/features/notes/__tests__/use-page-editor.test.tsx`. Put the mock at the top of the file, beside the other imports:

```ts
vi.mock("../lib/attachments", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/attachments")>()),
  uploadAttachment: vi.fn(),
}))
```

```ts
import { toast } from "darkraise-ui/components/sonner"
import { uploadAttachment } from "../lib/attachments"

const PAGE = "11111111-2222-3333-4444-555555555555"
const URL_A = "/api/v1/pages/attachments/0123abcd-4567-89ef-0123-456789abcdef"

describe("uploadFile", () => {
  beforeEach(() => vi.mocked(uploadAttachment).mockReset())

  it("is absent without a page id, so demo mode makes no request", async () => {
    const { editor } = await mountEditor()
    expect(editor.uploadFile).toBeUndefined()
  })

  it("returns the url and keeps an image block an image", async () => {
    vi.mocked(uploadAttachment).mockResolvedValue({ url: URL_A, contentType: "image/png" })
    const { editor } = await mountEditor(PAGE, [{ type: "image", props: { url: "", name: "a.png" } }])
    const id = editor.document[0]!.id
    await act(async () => {
      await expect(editor.uploadFile!(new File(["a"], "a.png"), id)).resolves.toBe(URL_A)
    })
    expect(editor.getBlock(id)!.type).toBe("image")
  })

  // The route sniffs the bytes and serves anything but the four image types
  // as a download, so an image block pointing at one would render nothing.
  it("retypes to a file block when the stored type is not an inline image", async () => {
    vi.mocked(uploadAttachment).mockResolvedValue({ url: URL_A, contentType: "application/octet-stream" })
    const { editor } = await mountEditor(PAGE, [{ type: "image", props: { url: "", name: "a.svg" } }])
    const id = editor.document[0]!.id
    await act(async () => {
      await editor.uploadFile!(new File(["a"], "a.svg"), id)
    })
    expect(editor.getBlock(id)!.type).toBe("file")
  })

  it("toasts and retypes the block to a paragraph when the upload is refused", async () => {
    vi.mocked(uploadAttachment).mockRejectedValue(new Error("attachment exceeds 52428800 bytes"))
    const { editor } = await mountEditor(PAGE, [{ type: "image", props: { url: "", name: "a.png" } }])
    const id = editor.document[0]!.id
    await act(async () => {
      await expect(editor.uploadFile!(new File(["a"], "a.png"), id)).resolves.toBe("")
    })
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith("attachment exceeds 52428800 bytes")
    expect(editor.getBlock(id)!.type).toBe("paragraph")
  })

  // The editor replaces any block whose content is an empty array, not only
  // an empty paragraph, so a paste into an empty list item holding a child
  // retypes that item -- which the nesting rule refuses, leaving a block that
  // never became the attachment.
  it("inserts the attachment beside a block the nesting rule kept as it was", async () => {
    vi.mocked(uploadAttachment).mockResolvedValue({ url: URL_A, contentType: "image/png" })
    const { editor } = await mountEditor(PAGE, [
      { type: "bulletListItem", content: [], children: [{ type: "paragraph", content: "kid" }] },
    ])
    const id = editor.document[0]!.id
    await act(async () => {
      await expect(editor.uploadFile!(new File(["a"], "a.png"), id)).resolves.toBe("")
    })
    expect(editor.document.map((b) => b.type)).toEqual(["bulletListItem", "image"])
    expect((editor.document[1]! as { props: { url: string } }).props.url).toBe(URL_A)
  })
})
```

Use the `mountEditor` helper exactly as Contracts defines it — Task 4 already wrote it into this file; do not restate or re-edit it.

The file's vitest import is `import { describe, expect, it } from "vitest"`. Widen it to `import { beforeEach, describe, expect, it, vi } from "vitest"`, or the mocks above fail with `vi is not defined`. Add `vi.mock("darkraise-ui/components/sonner", () => ({ toast: { error: vi.fn() } }))` above the imports if the file does not already mock it.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/use-page-editor.test.tsx`
Expected: FAIL — `editor.uploadFile` is undefined even with a page id.

- [ ] **Step 3: Write the implementation**

In `frontend/src/features/notes/use-page-editor.ts`, delete the `void pageId` line Task 4 left, add the imports, and replace the `useCreateBlockNote` call:

```ts
import { toast } from "darkraise-ui/components/sonner"
import { isImageType, uploadAttachment } from "./lib/attachments"
```

```ts
export function usePageEditor(
  initialBlocks: EditorBlockLike[],
  pageId?: string,
): PageEditorInstance {
  const editor = useCreateBlockNote({
    schema: pageSchema,
    trailingBlock: false,
    domAttributes: { editor: { "aria-label": "Page content" } },
    tables: { headers: false, splitCells: false, cellBackgroundColor: false, cellTextColor: false },
    initialContent: initialBlocks.length > 0 ? (initialBlocks as never) : undefined,
    uploadFile:
      pageId === undefined
        ? undefined
        : async (file: File, blockId?: string) => {
            let uploaded
            try {
              uploaded = await uploadAttachment(pageId, file)
            } catch (error) {
              toast.error(error instanceof Error ? error.message : "The upload failed.")
              // The editor swapped its add-file button for a loader when the
              // upload started and resets it only when the node view is
              // rebuilt, which resolving the url it already has ("") does not
              // do. Retyping the block is a real change, so the operator is
              // left with an empty paragraph to retry in rather than a loader
              // that never finishes.
              if (blockId !== undefined && editor.getBlock(blockId)) {
                editor.updateBlock(blockId, { type: "paragraph", content: [] } as never)
              }
              return ""
            }
            const type = isImageType(uploaded.contentType) ? "image" : "file"
            const placed = blockId === undefined ? undefined : editor.getBlock(blockId)
            if (placed && (placed.type === "image" || placed.type === "file")) {
              if (placed.type !== type) editor.updateBlock(placed, { type } as never)
              return uploaded.url
            }
            // The block the editor meant to fill is not a file block: either
            // the nesting rule refused a conversion it attempted in place, or
            // the block was removed while the upload was in flight. Either
            // way the file is already stored, so it is placed rather than
            // dropped, and the empty return leaves the editor's own follow-up
            // with nothing to change.
            const anchor = placed ?? editor.document[editor.document.length - 1]
            if (!anchor) {
              toast.error("The file was uploaded but there was nowhere to put it.")
              return ""
            }
            editor.insertBlocks(
              [{ type, props: { url: uploaded.url, name: file.name } } as never],
              anchor,
              "after",
            )
            return ""
          },
  })
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/features/notes && npm run typecheck`
Expected: every test PASSES and typecheck exits 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/use-page-editor.ts frontend/src/features/notes/__tests__/use-page-editor.test.tsx
git commit -m "feat(notes): upload a file from the editor"
```

---

### Task 9: The unload guard and the saving indicator

**Files:**
- Modify: `frontend/src/features/notes/use-page-sync.ts`
- Modify: `frontend/src/features/notes/__tests__/use-page-sync.test.tsx`

**Interfaces:**
- Consumes: `uploadsInFlight`, `subscribeUploads` — see Contracts.
- Produces: nothing a later task imports.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4

- [ ] **Step 1: Write the failing test**

In `frontend/src/features/notes/__tests__/use-page-sync.test.tsx`, add a mock for
the attachments module beside the existing `sonner` mock, above the imports. The
real module is never needed here: the hook reads only the count and the
subscription, so driving them directly keeps the test off `fetch` and off the
file's fake timers.

```tsx
// The spread keeps the module's other exports real. `isAttachmentUrl` lives
// here too and `inline-markdown` imports it, so a factory that returned only
// these three would make every standalone-link fixture in this file throw.
vi.mock("../lib/attachments", async (importOriginal) => {
  let inFlight = 0
  const listeners = new Set<() => void>()
  return {
    ...(await importOriginal<typeof import("../lib/attachments")>()),
    uploadsInFlight: () => inFlight,
    subscribeUploads: (listener: () => void) => {
      listeners.add(listener)
      return () => {
        listeners.delete(listener)
      }
    },
    __setUploads: (n: number) => {
      inFlight = n
      for (const listener of listeners) listener()
    },
  }
})
```

```tsx
import * as attachments from "../lib/attachments"

const setUploads = (n: number) =>
  (attachments as unknown as { __setUploads: (n: number) => void }).__setUploads(n)
```

```tsx
describe("an upload in flight", () => {
  afterEach(() => setUploads(0))

  it("warns on unload even when the tree is settled", () => {
    renderHook(() => usePageSync(PAGE, 0, () => transport().t), { wrapper })

    const settled = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(settled)
    expect(settled.defaultPrevented).toBe(false)

    setUploads(1)
    const pending = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(pending)
    expect(pending.defaultPrevented).toBe(true)
  })

  it("shows the saving state while a file is going up", async () => {
    const { result } = renderHook(() => usePageSync(PAGE, 0, () => transport().t), { wrapper })
    expect(result.current.status.kind).not.toBe("saving")
    await act(async () => setUploads(1))
    expect(result.current.status.kind).toBe("saving")
    await act(async () => setUploads(0))
    expect(result.current.status.kind).not.toBe("saving")
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/use-page-sync.test.tsx`
Expected: FAIL — the second `beforeunload` is not prevented, and the status stays `saved`.

- [ ] **Step 3: Write the implementation**

In `frontend/src/features/notes/use-page-sync.ts`, add the import and change two places:

```ts
import { subscribeUploads, uploadsInFlight } from "./lib/attachments"
```

```ts
function anyPending(): boolean {
  // A block whose upload has not resolved carries no url, so it is absent
  // from every sync tree: the engines alone cannot see that work.
  if (uploadsInFlight() > 0) return true
  for (const entry of engines.values()) if (entry.sync.pending) return true
  return false
}
```

Inside `usePageSync`, after the existing `status` subscription:

```ts
  const uploading = useSyncExternalStore(subscribeUploads, uploadsInFlight)
```

and in the returned `useMemo`, replace the `status` field and extend the dependency list:

```ts
      status:
        uploading > 0 && (status.kind === "idle" || status.kind === "saved")
          ? ({ kind: "saving" } as SyncStatus)
          : status,
```

```ts
    [entry, initialBlocks, page.id, status, uploading],
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/features/notes && npm run typecheck`
Expected: every test PASSES and typecheck exits 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/use-page-sync.ts frontend/src/features/notes/__tests__/use-page-sync.test.tsx
git commit -m "fix(notes): warn on unload while a file uploads"
```

---

### Task 10: The download button and the resize handle

**Files:**
- Modify: `frontend/src/features/notes/page-editor.tsx`
- Modify: `frontend/src/features/notes/page-editor.css`
- Modify: `frontend/src/features/notes/__tests__/page-editor.test.tsx`

**Interfaces:**
- Consumes: `pageSchema`'s new block types — see Contracts.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/features/notes/__tests__/page-editor.test.tsx`:

```tsx
const URL_A = "/api/v1/pages/attachments/0123abcd-4567-89ef-0123-456789abcdef"

const FILE_BLOCK: EditorBlockLike[] = [
  { id: "f", type: "file", props: { url: URL_A, name: "notes.pdf" }, content: undefined, children: [] },
]

describe("file affordances", () => {
  // A CSS rule can only be wrong in one of two ways: the rule is gone, or the
  // class it targets was renamed upstream. Each assertion catches one of them,
  // and the second is the reason the pair exists -- a rename would otherwise
  // leave the handle visible with a stylesheet that still looks correct.
  it("hides the resize handle, which has nowhere to be stored", () => {
    const css = readFileSync(resolve("src/features/notes/page-editor.css"), "utf8")
    expect(css).toMatch(/\.bn-resize-handle\s*\{[^}]*display:\s*none/)
    // `dist/style.css` rather than a bundle: the bundle's filename carries a
    // content hash, so a version bump would fail this with ENOENT instead of
    // the class-rename failure it is here to produce.
    const shipped = readFileSync(resolve("node_modules/@blocknote/core/dist/style.css"), "utf8")
    expect(shipped).toContain("bn-resize-handle")
  })

  it("renders a file block with its name", async () => {
    render(<PageEditor initialBlocks={FILE_BLOCK} editable />)
    await act(async () => {})
    expect(await screen.findByText("notes.pdf")).toBeInTheDocument()
  })

  // The block renderer draws an inert name and icon; the control that opens
  // the url is a toolbar button, and this editor builds its toolbar from an
  // explicit list. Asserting on the rendered toolbar would mean driving a
  // selection and a popover, so this pins the two things that can actually
  // break: the button is still exported, and it is still in the list.
  it("puts the download control in the toolbar", () => {
    expect(typeof FileDownloadButton).toBe("function")
    const source = readFileSync(resolve("src/features/notes/page-editor.tsx"), "utf8")
    expect(source).toContain("<FileDownloadButton />")
  })
})
```

Add `import { readFileSync } from "node:fs"`, `import { resolve } from "node:path"` and `import { FileDownloadButton } from "@blocknote/react"` to the file.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/notes/__tests__/page-editor.test.tsx`
Expected: FAIL — two of the three new cases fail, because the CSS rule is
absent and `page-editor.tsx` holds no `<FileDownloadButton />`. The third,
`renders a file block with its name`, already passes: Task 4 put the block type
in the schema, and this case guards that the renderer keeps working.

- [ ] **Step 3: Write the implementation**

Append to `frontend/src/features/notes/page-editor.css`:

```css
/* `previewWidth` has no place in the markdown a block is stored as, so a
   resize would be silently lost on the next reload. `display: none` also
   takes the handle out of the pointer path, so the prop can never move. */
.bn-container.bn-shadcn .bn-resize-handle {
  display: none;
}
```

In `frontend/src/features/notes/page-editor.tsx`, add `FileDownloadButton` to the existing `@blocknote/react` import and put it in the toolbar after `CreateLinkButton`:

```tsx
                  <CreateLinkButton />
                  {/* Without this an uploaded file is unreachable: the block
                      renderer draws an inert name and icon, and the anchor
                      that opens the url exists only in exported HTML. It
                      renders for a file or image block and nothing else. */}
                  <FileDownloadButton />
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/features/notes && npm run typecheck && npm run build`
Expected: every test PASSES, typecheck exits 0, and the build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/page-editor.tsx frontend/src/features/notes/page-editor.css frontend/src/features/notes/__tests__/page-editor.test.tsx
git commit -m "feat(notes): add a download control, hide resize"
```

---

### Task 11: The content-security-policy and the docs

**Files:**
- Modify: `backend/app/main.py:694-698`
- Modify: `frontend/nginx.conf:29`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 2 = 3

- [ ] **Step 1: Run the existing test to see it green before the change**

The backend suite needs the dev-compose Postgres, which is often down on this
host. Start only that service — the dev `app` service collides with the live
instance on `:8000`:

Run: `cd /root/repositories/darkmem && docker compose -f docker-compose.dev.yml up -d postgres`

Then:

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 python -m pytest -q tests/test_edge_response_policy.py`
Expected: PASS. This test parses `nginx.conf` and compares it to the app's header character for character, so it fails if only one of the two files below is edited. That is the check for this task; no new test is written.

- [ ] **Step 2: Edit the app's header**

In `backend/app/main.py`, change the `img-src` term inside `SECURITY_HEADERS` and extend the comment above it:

```python
# The four security headers, the gzip threshold and the body cap below are
# nginx's own values, moved rather than retuned: the nginx-in-image fallback
# (doc 03 section 3.2) must present the same policy as the app-as-edge build,
# and a value that drifts here makes the two postures disagree.
#
# `img-src` is the one deliberate retune. A page block may hold an external
# image, which the original policy blocked outright. `http:` is left out: the
# LAN deployment serves plain HTTP, and allowing cleartext image loads would
# let a pasted note beacon a third party in the clear.
SECURITY_HEADERS = (
    ("x-frame-options", "DENY"),
    ("x-content-type-options", "nosniff"),
    ("referrer-policy", "strict-origin-when-cross-origin"),
    (
        "content-security-policy",
        "default-src 'self'; script-src 'self'; worker-src 'self' blob:; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
        "font-src 'self' data:; connect-src 'self' ws: wss:; object-src 'none'; "
        "frame-ancestors 'none'; base-uri 'self'",
    ),
)
```

- [ ] **Step 3: Edit nginx's header**

In `frontend/nginx.conf:29`, change `img-src 'self' data:` to `img-src 'self' data: https:` inside the `Content-Security-Policy` value. Change nothing else on the line.

- [ ] **Step 4: Run the test to verify the two still agree**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 python -m pytest -q tests/test_edge_response_policy.py`
Expected: PASS. A failure here means exactly one of the two files was edited.

- [ ] **Step 5: Update CLAUDE.md**

In the paragraph beginning "**The SPA's `/notes` is the page tree's only surface**", after the sentence about inline markdown riding as a `rawInline` atom, add:

```
A paragraph that is exactly one image, or one link to an attachment, is shown
as a BlockNote `image` or `file` block and stored as that same markdown in the
block's own text — which is what the `page_attachment_cleanup` reference scan
reads, so the mapping and that job's pattern move together. Upload runs through
`POST /api/v1/pages/{id}/attachments` from paste, drag-drop and the slash menu;
an upload in flight is counted outside the sync tree, because a block with no
url yet is in no tree and the unload warning would otherwise stay silent. The
CSP's `img-src` carries `https:` for external images, deliberately not `http:`.
```

- [ ] **Step 6: Run the full frontend suite and commit, in two commits**

Run: `cd frontend && npm test && npm run typecheck && npm run build`
Expected: every test PASSES, typecheck exits 0, the build succeeds.

The header retune and the documentation are separate concerns, so they are
separate commits:

```bash
git add backend/app/main.py frontend/nginx.conf
git commit -m "feat(security): allow https images in the csp"
git add CLAUDE.md
git commit -m "docs(notes): record editor images and files"
```

---

### Task 12: Deploy and confirm the policy on the running instance

**Files:**
- Modify: none.

**Interfaces:**
- Consumes: everything the previous tasks built.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 0 - spec 0 - coupling 0 - risk 2 = 2

This host runs the live instance the owner reviews, so a merged-but-undeployed
change leaves them looking at the previous build. The change alters `backend/`
and `frontend/`, so the redeploy rule applies.

- [ ] **Step 1: Run the gate legs this change touches**

The backend leg needs the dev-compose Postgres, which is often down on this
host. Start only that service — the dev `app` service collides with the live
instance on `:8000`:

Run: `cd /root/repositories/darkmem && docker compose -f docker-compose.dev.yml up -d postgres`

Run, from the repository root: `cd frontend && npm run typecheck && npm test && npm run build`
Expected: all three succeed.

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 python -m pytest -q tests/test_edge_response_policy.py tests/test_spa_edge.py`
Expected: PASS.

Do not run `./scripts/gate.sh --full` — it cannot complete on this host. An
exit 143 anywhere is a SIGTERM from the `earlyoom` daemon, not a failure: check
`free -h` before believing a red.

- [ ] **Step 2: Build the image**

Run: `cd /root/repositories/darkmem && DARKMEM_PUSH=0 ./scripts/build-push.sh`
Expected: the build succeeds. `DARKMEM_PUSH=0` is not optional — the script's
default pushes, and publishing an image from this machine is forbidden.

- [ ] **Step 3: Confirm the image is the tree you just built**

The image carries no revision label — the `Dockerfile` declares none and
`build-push.sh` passes no `--label`. What it does write is a tag named for the
short git sha, so that tag existing is the evidence:

Run: `docker image inspect "darkraise/darkmem:$(git rev-parse --short HEAD)" > /dev/null && echo present`
Expected: `present`. If the inspect fails with "No such image", the build did
not run on this commit — a failed commit does not stop a build, so the tagged
image may predate the work. Rebuild before deploying, and do not skip ahead.

- [ ] **Step 4: Deploy and wait for health**

Run: `cd /root/repositories/darkmem && docker compose up -d`
Expected: the stack comes up. Then poll until the container reports `healthy`:

Run: `docker inspect --format '{{.State.Health.Status}}' darkmem-prod-darkmem-1`
Expected: `healthy`.

- [ ] **Step 5: Confirm the new policy on a live response, not in the tree**

Run: `curl -sI http://127.0.0.1:8000/health | grep -i content-security-policy`
Expected: the value contains `img-src 'self' data: https:`. Compose reuses an
image whose tag did not move, so a skipped or failed build redeploys the old
bits and still reports `Started`; this is the step that catches it.

- [ ] **Step 6: Record the deploy**

No commit. Note in the ledger the image sha deployed and the policy line the
live instance answered with.

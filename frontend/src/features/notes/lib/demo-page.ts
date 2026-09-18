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

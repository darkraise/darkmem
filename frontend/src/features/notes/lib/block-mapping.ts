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

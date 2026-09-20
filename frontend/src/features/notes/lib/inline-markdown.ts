import type {
  Html,
  Image,
  InlineCode,
  Link,
  Nodes,
  Paragraph,
  PhrasingContent,
  Root,
  Text,
} from "mdast"
import { fromMarkdown } from "mdast-util-from-markdown"
import { toMarkdown } from "mdast-util-to-markdown"
import { gfmStrikethrough } from "micromark-extension-gfm-strikethrough"
import {
  gfmStrikethroughFromMarkdown,
  gfmStrikethroughToMarkdown,
} from "mdast-util-gfm-strikethrough"
import { isAttachmentUrl } from "./attachments"

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

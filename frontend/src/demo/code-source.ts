import type { CodeNodeKind, DemoCodeGraph, DemoCodeNode } from "@/features/code/types"

export type SourceLanguage = "python" | "typescript" | "text"

export interface SourceAnchor {
  /** Graph node id — lets a graph selection scroll the inspector to it. */
  id: string
  name: string
  kind: CodeNodeKind
  /** 1-based line of the symbol's declaration. */
  line: number
}

export interface FileSource {
  path: string
  language: SourceLanguage
  lines: string[]
  anchors: SourceAnchor[]
  /** Symbols the indexer extracted from this file. */
  symbols: DemoCodeNode[]
}

const PY = /\.py$/
const TS = /\.(ts|tsx|js|jsx)$/

export function languageOf(path: string): SourceLanguage {
  if (PY.test(path)) return "python"
  if (TS.test(path)) return "typescript"
  return "text"
}

function moduleName(path: string): string {
  return path.replace(/\.[^./]+$/, "").replace(/\//g, ".")
}

function snake(name: string): string {
  return name
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .replace(/[^A-Za-z0-9_]/g, "_")
    .toLowerCase()
}

/**
 * Demo source text, derived from the indexed graph rather than stored: the
 * file's symbols become declarations in CONTAINS order, and its CALLS edges
 * become body statements. Nothing here is fetched — the point is a code
 * surface whose symbol lines are real anchors into the graph, so selecting
 * a node scrolls to the declaration the graph actually knows about.
 */
export function buildFileSource(
  graph: DemoCodeGraph | undefined,
  path: string,
): FileSource {
  const language = languageOf(path)
  const nodes = graph?.nodes.filter((n) => n.file === path) ?? []
  const symbols = nodes.filter((n) => n.kind !== "file" && n.kind !== "module")

  const byId = new Map(nodes.map((n) => [n.id, n]))
  const contains = new Map<string, string[]>()
  const calls = new Map<string, string[]>()
  const containedIds = new Set<string>()
  for (const edge of graph?.edges ?? []) {
    if (edge.type === "CONTAINS") {
      const parent = byId.get(edge.source)
      // A file CONTAINS its symbols, but that is membership, not nesting —
      // treating it as nesting would leave every top-level declaration
      // looking like it belongs to something and drop it from the listing.
      if (!parent || parent.kind === "file" || parent.kind === "module") {
        continue
      }
      if (byId.has(edge.target)) {
        contains.set(edge.source, [
          ...(contains.get(edge.source) ?? []),
          edge.target,
        ])
        containedIds.add(edge.target)
      }
    } else if (edge.type === "CALLS" && byId.has(edge.source)) {
      calls.set(edge.source, [...(calls.get(edge.source) ?? []), edge.target])
    }
  }

  const roots = symbols.filter((n) => !containedIds.has(n.id))
  const graphNodes = new Map(graph?.nodes.map((n) => [n.id, n]) ?? [])

  const lines: string[] = []
  const anchors: SourceAnchor[] = []
  const push = (text: string) => lines.push(text)
  const anchor = (node: DemoCodeNode) =>
    anchors.push({
      id: node.id,
      name: node.name,
      kind: node.kind,
      line: lines.length + 1,
    })

  // Imports: every out-of-file call target this file reaches.
  const imports = new Map<string, Set<string>>()
  for (const [sourceId, targets] of calls) {
    if (!byId.has(sourceId)) continue
    for (const targetId of targets) {
      const target = graphNodes.get(targetId)
      if (!target || target.file === path) continue
      const set = imports.get(target.file) ?? new Set<string>()
      set.add(target.name)
      imports.set(target.file, set)
    }
  }

  if (language === "python") {
    push(`"""${path}"""`)
    push("")
    push("from __future__ import annotations")
    for (const [file, names] of imports) {
      push(`from ${moduleName(file)} import ${[...names].sort().join(", ")}`)
    }
    push("")
    push("")
  } else {
    push(`// ${path}`)
    push("")
    for (const [file, names] of imports) {
      push(
        `import { ${[...names].sort().join(", ")} } from "${moduleName(file).replace(/\./g, "/")}"`,
      )
    }
    if (imports.size > 0) push("")
  }

  const emitCalls = (node: DemoCodeNode, indent: string, selfCall: boolean) => {
    const targets = (calls.get(node.id) ?? [])
      .map((id) => graphNodes.get(id))
      .filter((n): n is DemoCodeNode => Boolean(n))
    if (targets.length === 0) {
      push(`${indent}${language === "python" ? "..." : "// no traced calls"}`)
      return
    }
    for (const target of targets) {
      const call =
        selfCall && target.file === path && target.kind === "method"
          ? `self.${snake(target.name)}(batch)`
          : `${target.name}(batch)`
      push(`${indent}${call}`)
    }
  }

  const emitPython = (node: DemoCodeNode, depth: number) => {
    const indent = "    ".repeat(depth)
    const children = (contains.get(node.id) ?? [])
      .map((id) => byId.get(id))
      .filter((n): n is DemoCodeNode => Boolean(n))
    if (node.kind === "class") {
      anchor(node)
      push(`${indent}class ${node.name}:`)
      push(
        `${indent}    """${node.name} — ${children.length} member${
          children.length === 1 ? "" : "s"
        }."""`,
      )
      if (children.length === 0) push(`${indent}    ...`)
      for (const child of children) {
        push("")
        emitPython(child, depth + 1)
      }
    } else {
      anchor(node)
      // `self` only where the symbol actually sits inside a class body: a
      // method the graph never nested is emitted as the module-level
      // function it looks like here.
      const bound = node.kind === "method" && depth > 0
      push(`${indent}def ${snake(node.name)}(${bound ? "self, " : ""}batch):`)
      emitCalls(node, `${indent}    `, bound)
    }
    push("")
  }

  const emitTs = (node: DemoCodeNode, depth: number) => {
    const indent = "  ".repeat(depth)
    const children = (contains.get(node.id) ?? [])
      .map((id) => byId.get(id))
      .filter((n): n is DemoCodeNode => Boolean(n))
    if (node.kind === "class") {
      anchor(node)
      push(`${indent}export class ${node.name} {`)
      for (const child of children) emitTs(child, depth + 1)
      push(`${indent}}`)
    } else {
      anchor(node)
      const keyword = depth === 0 ? "export function " : ""
      push(`${indent}${keyword}${node.name}(batch) {`)
      emitCalls(node, `${indent}  `, false)
      push(`${indent}}`)
    }
    push("")
  }

  for (const root of roots) {
    if (language === "python") emitPython(root, 0)
    else emitTs(root, 0)
  }

  if (roots.length === 0) {
    push(
      language === "python"
        ? "# No symbols were extracted from this file in the current graph."
        : "// No symbols were extracted from this file in the current graph.",
    )
    push(
      language === "python"
        ? "# It is tracked and parsed, but contributes no nodes."
        : "// It is tracked and parsed, but contributes no nodes.",
    )
  }

  while (lines.length > 0 && lines[lines.length - 1] === "") lines.pop()

  return { path, language, lines, anchors, symbols }
}

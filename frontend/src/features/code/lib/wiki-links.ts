import type { DemoCodeGraph } from "@/features/code/types"

export interface WikiCodeTarget {
  /** Display text as it appeared in the prose. */
  text: string
  /** Graph node id when the reference resolved to a symbol. */
  symbolId?: string
  /** Repo-relative path when it resolved to a file. */
  file?: string
  kind: "file" | "symbol"
}

export type ProseSegment =
  | { type: "text"; text: string }
  | { type: "code"; target: WikiCodeTarget }

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

/**
 * A token is worth linking only if it reads as code rather than English:
 * an identifier with an underscore or internal capital, or a path with a
 * separator or extension. Without this the word "search" in a sentence
 * would light up as the `search` method.
 */
function looksLikeCode(token: string): boolean {
  if (token.includes("/") || /\.[a-z]{1,4}$/.test(token)) return true
  if (token.length < 6) return false
  return token.includes("_") || /[a-z][A-Z]/.test(token)
}

export interface WikiLinkIndex {
  /** Splits prose into plain text and resolvable code references. */
  linkify: (text: string) => ProseSegment[]
  /** Resolves a bullet's `code` value, which is always a path or symbol. */
  resolve: (token: string) => WikiCodeTarget
}

export function buildWikiLinkIndex(
  files: string[],
  graph: DemoCodeGraph | undefined,
): WikiLinkIndex {
  const targets = new Map<string, WikiCodeTarget>()

  const add = (token: string, target: WikiCodeTarget) => {
    if (!looksLikeCode(token) || targets.has(token)) return
    targets.set(token, target)
  }

  const byId = new Map((graph?.nodes ?? []).map((n) => [n.id, n]))

  for (const node of graph?.nodes ?? []) {
    if (node.kind === "file" || node.kind === "module") {
      add(node.file, { text: node.file, file: node.file, kind: "file" })
    } else {
      add(node.name, {
        text: node.name,
        symbolId: node.id,
        file: node.file,
        kind: "symbol",
      })
    }
  }

  // Prose names a method as `Owner.method`. Register the qualified form so
  // the whole reference becomes one link instead of a linked class followed
  // by a stranded `.method`.
  for (const edge of graph?.edges ?? []) {
    if (edge.type !== "CONTAINS") continue
    const owner = byId.get(edge.source)
    const member = byId.get(edge.target)
    if (!owner || !member) continue
    if (owner.kind === "file" || owner.kind === "module") continue
    add(`${owner.name}.${member.name}`, {
      text: `${owner.name}.${member.name}`,
      symbolId: member.id,
      file: member.file,
      kind: "symbol",
    })
  }
  for (const file of files) {
    add(file, { text: file, file, kind: "file" })
  }

  // Longest first so `services/pipeline.py` wins over `pipeline.py`.
  const tokens = [...targets.keys()].sort((a, b) => b.length - a.length)
  const pattern =
    tokens.length === 0
      ? null
      : new RegExp(
          `(?<![\\w./-])(?:${tokens.map(escapeRegExp).join("|")})(?![\\w-])`,
          "g",
        )

  const resolve = (token: string): WikiCodeTarget =>
    targets.get(token) ?? { text: token, file: token, kind: "file" }

  const linkify = (text: string): ProseSegment[] => {
    if (!pattern) return [{ type: "text", text }]
    const segments: ProseSegment[] = []
    let last = 0
    for (const match of text.matchAll(pattern)) {
      const start = match.index ?? 0
      if (start > last) {
        segments.push({ type: "text", text: text.slice(last, start) })
      }
      segments.push({ type: "code", target: resolve(match[0]) })
      last = start + match[0].length
    }
    if (last < text.length) {
      segments.push({ type: "text", text: text.slice(last) })
    }
    return segments
  }

  return { linkify, resolve }
}

/** Distinct code references across a run of prose, in first-seen order. */
export function collectTargets(segments: ProseSegment[][]): WikiCodeTarget[] {
  const seen = new Set<string>()
  const out: WikiCodeTarget[] = []
  for (const run of segments) {
    for (const segment of run) {
      if (segment.type !== "code") continue
      const key = segment.target.symbolId ?? segment.target.file ?? ""
      if (seen.has(key)) continue
      seen.add(key)
      out.push(segment.target)
    }
  }
  return out
}

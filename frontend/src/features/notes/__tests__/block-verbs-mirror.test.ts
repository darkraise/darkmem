import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { CALLOUT_VARIANTS, PAGE_CONTAINERS, PAGE_TYPE_PROPERTIES } from "../lib/block-properties"

const backend = (file: string) => readFileSync(join(process.cwd(), "../backend/app/services", file), "utf8")
const verbs = backend("block_verbs.py")
const serializer = backend("block_serializer.py")

// The client's copy of the page rules. Template literals escape their
// backticks, which the server's messages carry bare.
const mirror = ["sync-tree.ts", "block-properties.ts"]
  .map((file) => readFileSync(join(process.cwd(), "src/features/notes/lib", file), "utf8"))
  .join("\n")
  .replace(/\\`/g, "`")

/** Refusals the save engine cannot predict, each with the reason: the
 *  engine meets them as the server's answer, never ahead of the write. */
const SERVER_ONLY: Record<string, string> = {
  DocumentHashConflict: "the hash precondition, which the engine settles by re-reading",
  DocumentMirrorOwned: "documents only: no page is mirror-owned",
  DocumentNotConvertible: "documents only: a page is block-first from its creation",
  DocumentTooLarge: "a size bound the client does not measure",
  "PageBlockInvalid(<expression>)": "a missing attachment reference: the client holds no attachment list",
  "with id": "the page itself is gone, which the engine stops on as a 404",
  "no block with id": "resolves a block's owner from its id alone; the page routes name the page",
  "does not belong to any": "resolves a block's owner from its id alone; the page routes name the page",
}

interface Refusal {
  exception: string
  reason: string | null
  line: number
}

/** Every `raise X(...)` in the module, with its message's literal text
 *  joined across implicit concatenation. */
function refusals(source: string): Refusal[] {
  const found: Refusal[] = []
  for (const match of source.matchAll(/raise (\w+)\(/g)) {
    let rest = source.slice(match.index! + match[0].length)
    const parts: string[] = []
    for (;;) {
      const literal = /^\s*f?(["'])((?:\\.|(?!\1).)*)\1/.exec(rest)
      if (!literal) break
      parts.push(literal[2]!)
      rest = rest.slice(literal[0].length)
    }
    found.push({
      exception: match[1]!,
      reason: parts.length > 0 ? parts.join("") : null,
      line: source.slice(0, match.index).split("\n").length,
    })
  }
  return found
}

/** The longest literal run of a message, before any explanation after a
 *  colon: the words a client copy of the rule must also say. */
function reasonOf(message: string): string {
  const head = message.replace(/\{[^{}]*\}/g, "\u0000").split(": ")[0]!
  return head
    .split("\u0000")
    .map((part) => part.trim())
    .reduce((a, b) => (b.length > a.length ? b : a), "")
}

function setOf(body: string): string[] {
  return [...body.matchAll(/"(\w+)"/g)].map((m) => m[1]!).sort()
}

describe("the page rules mirror block_verbs.py", () => {
  it("every server refusal has a client mirror", () => {
    const missing: string[] = []
    const all = refusals(verbs)
    expect(all.length).toBeGreaterThan(10)
    for (const { exception, reason, line } of all) {
      if (exception in SERVER_ONLY) continue
      const key = reason === null ? `${exception}(<expression>)` : reasonOf(reason)
      if (key in SERVER_ONLY) continue
      if (reason === null || !mirror.includes(key)) {
        missing.push(`block_verbs.py:${line} ${exception}: ${key}`)
      }
    }
    expect(missing).toEqual([])
  })

  it("the page rule tables match the server's", () => {
    const table = /_PAGE_TYPE_PROPERTIES[^=]*=\s*\{([\s\S]*?)\n\}/.exec(verbs)![1]!
    const properties = Object.fromEntries(
      [...table.matchAll(/"(\w+)":\s*frozenset\((?:\{([^}]*)\})?\)/g)].map((m) => [m[1]!, setOf(m[2] ?? "")]),
    )
    expect(properties).toEqual(
      Object.fromEntries(Object.entries(PAGE_TYPE_PROPERTIES).map(([type, keys]) => [type, [...keys].sort()])),
    )
    const containers = /_PAGE_CONTAINERS = frozenset\(\{([^}]*)\}\)/.exec(verbs)![1]!
    expect(setOf(containers)).toEqual([...PAGE_CONTAINERS].sort())
    const labels = /_CALLOUT_LABELS = \{([^}]*)\}/.exec(serializer)![1]!
    expect([...labels.matchAll(/"(\w+)":/g)].map((m) => m[1]!).sort()).toEqual([...CALLOUT_VARIANTS].sort())
  })
})

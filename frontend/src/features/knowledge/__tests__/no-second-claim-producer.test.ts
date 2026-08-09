import { describe, it, expect } from "vitest"
import { readdirSync, readFileSync, statSync } from "node:fs"
import { join, dirname, relative } from "node:path"
import { fileURLToPath } from "node:url"

/**
 * The frontend half of doc 12 §4's one-producer rule.
 *
 * `backend/tests/test_layer_composition.py` fails the build when a second
 * file under `backend/app` builds the badge's claim sentence, and its own
 * docstring records the hole: "the scan's scope is `backend/app` —
 * `frontend/` and `backend/scripts/` are unscanned". That hole is not
 * theoretical. The Facts tab shipped with a `meta` line reading
 * "asserted by N distinct origins of kinds [...]" — the claim's opening
 * clause, re-worded in the frontend with its own pluralization grammar,
 * green through every backend guard and every adapter test. This is the
 * guard that would have caught it.
 *
 * Same predicate as the backend's, deliberately: a file carrying **two or
 * more** distinct fragments of the claim vocabulary is composing the
 * sentence. One is a word — `fact-sources.tsx` legitimately labels an
 * origin group "1 distinct origin · 4 rows", and a count is not a claim.
 *
 * The vocabulary is read from `fact_badge.py` rather than copied, so a
 * fragment added to the producer starts guarding this side on the same
 * commit instead of drifting silently.
 */

const __dirname = dirname(fileURLToPath(import.meta.url))
const FRONTEND = join(__dirname, "..", "..", "..", "..")
const FACT_BADGE = join(
  FRONTEND,
  "..",
  "backend",
  "app",
  "services",
  "fact_badge.py",
)

const SCANNED = [
  join(FRONTEND, "src", "features", "knowledge"),
  join(FRONTEND, "src", "hooks", "api", "use-knowledge-api.ts"),
]

function claimVocabulary(): string[] {
  const source = readFileSync(FACT_BADGE, "utf-8")
  const block = source.match(
    /CLAIM_VOCABULARY: tuple\[str, \.\.\.\] = \(([\s\S]*?)\)\n/,
  )
  if (!block) throw new Error(`CLAIM_VOCABULARY not found in ${FACT_BADGE}`)
  // The tuple names the fragment constants; their values are the strings.
  const names = [...block[1]!.matchAll(/_([A-Z_]+),/g)].map((m) => `_${m[1]}`)
  const fragments: string[] = []
  for (const name of names) {
    const assignment = source.match(
      new RegExp(`^${name} = "([^"]+)"`, "m"),
    )
    if (assignment) fragments.push(assignment[1]!.toLowerCase())
  }
  return fragments
}

/** Everything in a TS/TSX source except its comments — string literals,
 *  template literals and JSX text alike, since a sentence composed in JSX
 *  text is composed just as surely as one in quotes. Comments are excluded
 *  the way the backend scan excludes nothing but reasons about literals:
 *  prose explaining the rule is not a second producer of it. */
function withoutComments(source: string): string {
  let out = ""
  let i = 0
  const n = source.length
  while (i < n) {
    const c = source[i]!
    const next = source[i + 1]
    if (c === "/" && next === "/") {
      while (i < n && source[i] !== "\n") i++
      continue
    }
    if (c === "/" && next === "*") {
      i += 2
      while (i < n && !(source[i] === "*" && source[i + 1] === "/")) i++
      i += 2
      continue
    }
    if (c === '"' || c === "'" || c === "`") {
      const quote = c
      out += c
      i++
      while (i < n) {
        if (source[i] === "\\") {
          out += source[i]! + (source[i + 1] ?? "")
          i += 2
          continue
        }
        out += source[i]
        if (source[i] === quote) {
          i++
          break
        }
        i++
      }
      continue
    }
    out += c
    i++
  }
  return out
}

function fragmentsIn(source: string, vocabulary: string[]): string[] {
  const text = withoutComments(source).toLowerCase()
  return vocabulary.filter((fragment) => text.includes(fragment))
}

function sourceFiles(path: string): string[] {
  if (statSync(path).isFile()) return [path]
  const found: string[] = []
  for (const entry of readdirSync(path)) {
    const full = join(path, entry)
    if (statSync(full).isDirectory()) {
      // Tests carry whole claim strings as fixtures on purpose.
      if (entry === "__tests__") continue
      found.push(...sourceFiles(full))
      continue
    }
    if (entry.endsWith(".ts") || entry.endsWith(".tsx")) found.push(full)
  }
  return found
}

describe("doc 12 §4: the claim sentence has one producer, and it is not the frontend", () => {
  it("reads the vocabulary from the producer itself", () => {
    const vocabulary = claimVocabulary()
    expect(vocabulary.length).toBeGreaterThanOrEqual(8)
    expect(vocabulary).toContain("asserted by")
    expect(vocabulary).toContain("no known contradiction")
  })

  it("detects the composition it exists to prevent (the scan is not vacuous)", () => {
    // The exact `meta` line the Facts tab shipped with, and the exact
    // shape a copy of this pattern would reach for next.
    const composed =
      'const meta = `asserted by ${n} distinct ${n === 1 ? "origin" : "origins"} of kinds [${kinds}]`'
    expect(fragmentsIn(composed, claimVocabulary()).length).toBeGreaterThanOrEqual(2)
  })

  it("sees through a comment but not into one", () => {
    const vocabulary = claimVocabulary()
    const commented =
      "// asserted by N distinct origins of kinds [x]\nconst a = 1"
    expect(fragmentsIn(commented, vocabulary)).toEqual([])
    // JSX text is not quoted and must still count.
    const jsx = "<p>asserted by {n} distinct origins of kinds [{k}]</p>"
    expect(fragmentsIn(jsx, vocabulary).length).toBeGreaterThanOrEqual(2)
  })

  it("finds no second producer under the knowledge feature", () => {
    const vocabulary = claimVocabulary()
    const offenders: Record<string, string[]> = {}
    const scanned: string[] = []
    for (const root of SCANNED) {
      for (const file of sourceFiles(root)) {
        scanned.push(file)
        const found = fragmentsIn(readFileSync(file, "utf-8"), vocabulary)
        if (found.length >= 2) offenders[relative(FRONTEND, file)] = found
      }
    }
    // A scan over an empty file list passes for the wrong reason.
    expect(scanned.length).toBeGreaterThan(5)
    expect(
      offenders,
      "doc 12's claim sentence has a second producer in the frontend; every " +
        "consumer renders the backend's `claim` verbatim and lays the badge's " +
        `parts out beside it, never re-worded: ${JSON.stringify(offenders)}`,
    ).toEqual({})
  })
})

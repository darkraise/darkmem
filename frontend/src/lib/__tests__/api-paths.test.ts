import { describe, it, expect } from "vitest"
import { readdirSync, readFileSync, statSync } from "node:fs"
import { join, dirname, relative } from "node:path"
import { fileURLToPath } from "node:url"

/**
 * `apiFetch` prepends the API base itself (`lib/api.ts`), so every call site
 * passes a path *without* it. A call site that spells the prefix resolves to
 * `/api/v1/api/v1/...` and 404s on every request.
 *
 * This is not hypothetical and it is not catchable by a hook's own tests:
 * the Facts tab shipped with the doubled prefix and stayed green, because
 * every test mocks `apiFetch` — the base is never applied under test — and
 * the one assertion that looked at the URL checked three query-parameter
 * substrings, all of which pass whether the path is right or doubled. A
 * whole surface was non-functional on live data behind a green suite.
 *
 * The rule is mechanical, so the guard is: no argument to `apiFetch` may
 * begin with the base. Call-site tests should still assert the whole path
 * rather than a substring of it — this catches the class, not the case.
 */

const __dirname = dirname(fileURLToPath(import.meta.url))
const SRC = join(__dirname, "..", "..")
const API_BASE = "/api/v1"

// `apiFetch("/x")`, `apiFetch<T>(`/x`)`, and the same with the path on the
// following line — the shapes a formatter produces from one call.
const PREFIXED_CALL = new RegExp(
  `apiFetch(?:<[^>]*>)?\\(\\s*\\n?\\s*['"\`]${API_BASE}`,
  "g",
)
const ANY_CALL = /apiFetch(?:<[^>]*>)?\(/g

function sourceFiles(path: string): string[] {
  const found: string[] = []
  for (const entry of readdirSync(path)) {
    const full = join(path, entry)
    if (statSync(full).isDirectory()) {
      found.push(...sourceFiles(full))
      continue
    }
    if (entry.endsWith(".ts") || entry.endsWith(".tsx")) found.push(full)
  }
  return found
}

describe("apiFetch call sites never spell the API base", () => {
  it("detects a doubled prefix in every shape one call can be written in", () => {
    const doubled = [
      `apiFetch("${API_BASE}/knowledge/facts")`,
      "apiFetch<FactListResponse>(\n  `" + API_BASE + "/knowledge/facts`,\n)",
      `apiFetch<T>('${API_BASE}/x')`,
    ]
    for (const call of doubled) {
      expect(new RegExp(PREFIXED_CALL.source).test(call), call).toBe(true)
    }
    expect(new RegExp(PREFIXED_CALL.source).test('apiFetch("/knowledge/facts")')).toBe(
      false,
    )
  })

  it("finds no call site under src that carries the base", () => {
    const offenders: string[] = []
    let calls = 0
    for (const file of sourceFiles(SRC)) {
      const source = readFileSync(file, "utf-8")
      calls += [...source.matchAll(ANY_CALL)].length
      if ([...source.matchAll(PREFIXED_CALL)].length > 0) {
        offenders.push(relative(SRC, file))
      }
    }
    // A scan that reaches no call site passes for the wrong reason.
    expect(calls).toBeGreaterThan(20)
    expect(
      offenders,
      "apiFetch prepends /api/v1 itself; these call sites spell it again " +
        `and resolve to /api/v1/api/v1/...: ${offenders.join(", ")}`,
    ).toEqual([])
  })
})

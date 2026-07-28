import { execFileSync } from "node:child_process"
import path from "node:path"
import { describe, expect, it } from "vitest"

// T1.64: proves the src/demo/data/**-scoped `error` flip is a real gate, and
// keeps the broader, still-warn src/demo/* rule's count honest — a number
// measured at execution time and written here as a literal, never parsed out
// of eslint.config.js's own comment (that self-contradiction was Minor M1 in
// the plan's review).
//
// NOTE: this file lives under src/__tests__/, not frontend/tests/lint/ as
// the task's own plan draft named it — vitest.config.ts excludes `tests/**`
// (that directory is Playwright's), so a file placed there would never be
// collected by `npm test` and this gate would silently never run. Corrected
// here rather than worked around (runbook §5, Tier 1).
const FRONTEND_ROOT = path.resolve(__dirname, "../..")

interface EslintMessage {
  ruleId: string | null
}
interface EslintFileResult {
  filePath: string
  messages: EslintMessage[]
}

function runEslint(): EslintFileResult[] {
  const output = execFileSync(
    "./node_modules/.bin/eslint",
    ["src/", "--format", "json"],
    { cwd: FRONTEND_ROOT, encoding: "utf-8", maxBuffer: 32 * 1024 * 1024 },
    // eslint exits 1 when it finds any error-level problem (expected: our
    // count assertions below are what actually gate this, not the exit code).
  ).toString()
  return JSON.parse(output)
}

function runEslintTolerant(): EslintFileResult[] {
  try {
    return runEslint()
  } catch (err: unknown) {
    const e = err as { stdout?: Buffer | string }
    if (e.stdout) return JSON.parse(e.stdout.toString())
    throw err
  }
}

function countByRule(results: EslintFileResult[], ruleId: string): number {
  let count = 0
  for (const file of results) {
    for (const message of file.messages) {
      if (message.ruleId === ruleId) count++
    }
  }
  return count
}

describe("no-restricted-imports: src/demo/*", () => {
  const results = runEslintTolerant()

  it("the src/demo/data/**-scoped rule is a real error-level gate: zero violations", () => {
    expect(countByRule(results, "demo-data-import/no-restricted-imports")).toBe(0)
  })

  it("the broader src/demo/* rule's warn-level count matches the measured floor", () => {
    // Two-sided on purpose: fails if a new file starts importing a covered
    // src/demo/* path (ceiling) and fails if the count silently drops
    // without this literal being updated (floor) — measured 2026-07-28,
    // after T1.64's flag relocation and in-lane data/** fixes.
    expect(countByRule(results, "no-restricted-imports")).toBe(150)
  })
})

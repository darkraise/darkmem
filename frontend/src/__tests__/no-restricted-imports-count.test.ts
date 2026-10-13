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
    expect(countByRule(results, "demo-data-import/no-restricted-imports")).toBe(
      0,
    )
  })

  it("the real-API-type-scoped rule (Memory/MemoryStatus/Repo/Job) is a real error-level gate: zero violations", () => {
    // T1.67: the dead re-export in src/demo/types.ts is gone, so this is
    // currently unreachable through normal code — see this file's own
    // falsification proof (T1.67's report) for how it was shown to fire.
    expect(
      countByRule(results, "demo-realtype-import/no-restricted-imports"),
    ).toBe(0)
  })

  it("the T1.68-relocated-types rule is a real error-level gate: zero violations", () => {
    // T1.68 moved 33 names (ContributionDay, CodeNodeKind, DemoCodeGraph,
    // DemoMemory, DemoJob, FeedCategory, DemoRankArm, ...) out of
    // src/demo/types.ts into features/{dashboard,code,memories,activity,
    // settings}/types.ts because real code is genuinely load-bearing on
    // them. Falsification proof is in the task's report: a throwaway
    // `DemoMemory` import from `@/demo/types` in src/lib/, watched to fire
    // at error, then reverted.
    expect(
      countByRule(results, "demo-relocated-types-import/no-restricted-imports"),
    ).toBe(0)
  })

  it("the broader src/demo/* rule's warn-level count matches the measured floor", () => {
    // Two-sided on purpose: fails if a new file starts importing a covered
    // src/demo/* path (ceiling) and fails if the count silently drops
    // without this literal being updated (floor) — measured 2026-07-28,
    // after T1.68 relocated 33 real-consumed types out of src/demo/types.ts
    // (down from 150/80 files at T1.64's last measurement; the residual is
    // recorded in the task's report — genuinely demo-fixture-only types,
    // plus a handful of real, non-demo-exclusive files that legitimately
    // still need a demo-shaped type for their `if (DEMO)` branch, e.g.
    // use-feed.ts's DemoFeedEvent). Re-measured 2026-08-04 (T2.86):
    // `belief-window.tsx`'s prop type widened to a structural
    // `BeliefWindowLike` so the live fact detail page could reuse the
    // component without importing `@/demo/types`' `BeliefWindow`, dropping
    // the count to 115. Re-measured again when the Flags tab stopped
    // summarising job cadences and no longer needed `useDemoJobs`: 114.
    // Re-measured when the Git accounts tab landed: 115. Its binding
    // (`use-git-accounts-binding.ts`) reaches `useDemoGitAccounts` for its
    // `if (DEMO)` branch, the same shape as the other settings-tab bindings —
    // the fixture itself stays inside src/demo/, which is what the
    // error-level rule above governs. Re-measured when the project and usage
    // demo fixtures landed: 117 — `use-projects-api.ts` and `use-usage-api.ts`
    // import them for their `initialData` in demo mode, the same shape.
    // Re-measured when the pipeline stepper test landed: 118 — it reads a
    // curated run out of `useDemoStore`, one more `@/demo/store` import.
    // Re-measured when the job card test landed: 119 — it reads a fixture job
    // out of `useDemoStore` the same way. Re-measured when the checkpoint
    // views were removed: 117 — `checkpoints-tab.tsx` and
    // `use-checkpoints-api.ts` each imported a demo fixture. Re-measured when
    // the work-log demo fixtures landed: 118 — `use-worklog-api.ts` imports
    // them for its `initialData` in demo mode, the same shape as projects.
    // Re-measured when the UI copy prune removed the distribution mock, the
    // monitors tab and the review/hygiene count hooks: 109. Re-measured when
    // the UI review fixes landed: 110 — the activity Jobs tab reuses the /jobs
    // board and drops its demo import (-1), while the activity component test
    // and the review-queue demo test each read one more fixture (+2).
    // Re-measured when the MCP calls tab landed: 112 — `use-mcp-calls-api.ts`
    // imports its fixture for `initialData` in demo mode (the usage shape),
    // and the tab's test reads the same fixture.
    // Re-measured when the board hooks landed: 113 — `use-board-api.ts`
    // imports its fixtures for `initialData` in demo mode (the work-log shape).
    expect(countByRule(results, "no-restricted-imports")).toBe(113)
  })
})

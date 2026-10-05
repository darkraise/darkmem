import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

import { assignPlanCodes, derivePlanCode } from "../plan-code"
import {
  parseCompletedPlans,
  parsePlanLedger,
  parsePlanSections,
  planFromOutline,
} from "../parse-plan"
import { planTaskStatus } from "../plan-status"
import { PLAN_REF } from "../../types"
import type { OutlineNode } from "@/hooks/api"

/**
 * Golden tests against the REAL committed plans, as `parsers.test.ts` does for
 * the ledger and epic files: the plans' format is only as stable as the
 * corpus, so the corpus is the fixture.
 */

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "../../../../../..")
const PLANS = join(ROOT, "docs/superpowers/plans")
const planFiles = () =>
  readdirSync(PLANS).filter((f) => f.endsWith(".md") && f !== "completed.md").sort()
const read = (f: string) => readFileSync(join(PLANS, f), "utf-8")

/** A `## Task index` section's numbered rows, read independently of the
 *  parser under test. */
function indexNumbers(markdown: string): string[] {
  const start = markdown.indexOf("## Task index")
  if (start === -1) return []
  const rest = markdown.slice(start).split("\n").slice(1)
  const numbers: string[] = []
  for (const line of rest) {
    if (/^#{1,6}\s/.test(line) || line.trim() === "---") break
    const m = /^(\d+)\.\s/.exec(line)
    if (m?.[1]) numbers.push(m[1])
  }
  return numbers
}

describe("plan codes", () => {
  it("derives a code from the filename, date dropped", () => {
    expect(derivePlanCode("2026-10-03-comprehensive-review-fixes.md")).toBe("CRF")
    expect(derivePlanCode("2026-09-23-work-log-increment-1-store-and-verbs.md")).toBe("WLI1SV")
    expect(derivePlanCode("2026-07-31-t2.26-groundedness-judge.md")).toBe("T226GJ")
    expect(derivePlanCode("2026-08-14-t2.124-round5-frame-fix.md")).toBe("T2124R5FF")
    expect(derivePlanCode("2026-04-01-3d-unified-graph.md")).toBe("3DUG")
  })

  it("gives every committed plan a distinct code", () => {
    const codes = assignPlanCodes(planFiles())
    expect(new Set(codes.values()).size).toBe(planFiles().length)
    for (const code of codes.values()) expect(PLAN_REF.test(`${code}-1`)).toBe(true)
  })

  it("suffixes a collision in filename order, so the older plan keeps its code", () => {
    const codes = assignPlanCodes([
      "2026-10-02-memory-graph-scale.md",
      "2026-09-29-memory-graph-scale.md",
    ])
    expect(codes.get("2026-09-29-memory-graph-scale.md")).toBe("MGS")
    expect(codes.get("2026-10-02-memory-graph-scale.md")).toBe("MGS2")
  })
})

describe("parsePlanSections against the committed plans", () => {
  it("finds one section per task-index row, in every plan that has an index", () => {
    const indexed = planFiles().filter((f) => read(f).includes("## Task index"))
    expect(indexed.length).toBe(19)
    for (const f of indexed) {
      const text = read(f)
      expect([...parsePlanSections(text).keys()], f).toEqual(indexNumbers(text))
    }
  })

  it("ignores task headings quoted inside fenced code", () => {
    // attachment-backups quotes test files whose comments read
    // `# ── Task 3: ...`; as headings they would cut Task 3's section short.
    const sections = parsePlanSections(read("2026-09-20-attachment-backups.md"))
    expect(sections.size).toBe(16)
    expect(sections.get("3")?.title).toBe("Family arguments across every destination")
    expect(sections.get("3")?.body).toContain("Task 3: the two families never see each other")
  })

  it("reads a task's step checkboxes", () => {
    const sections = parsePlanSections(read("2026-10-03-comprehensive-review-fixes.md"))
    expect(sections.size).toBe(9)
    const steps = sections.get("1")?.steps ?? []
    expect(steps.length).toBeGreaterThan(0)
    expect(steps.every((s) => s.checked)).toBe(true)
  })
})

describe("parseCompletedPlans", () => {
  it("names every plan the committed completed.md records", () => {
    const done = parseCompletedPlans(readFileSync(join(PLANS, "completed.md"), "utf-8"))
    expect(done.has("2026-09-29-memory-graph-scale.md")).toBe(true)
    expect(done.has("completed.md")).toBe(false)
    expect(done.has("2026-08-24-r2-shipped-image.md")).toBe(false)
  })
})

describe("planFromOutline", () => {
  const node = (text: string, level = 3, id = text): OutlineNode => ({
    block_id: id, level, text, order_index: null,
  })

  it("makes each Task N heading a task referenced <code>-N, chained in order", () => {
    const plan = planFromOutline(
      [
        node("Comprehensive Review Fixes", 1),
        node("Task index", 2),
        node("Task 1: Repository ingestion boundaries", 3, "b1"),
        node("Task 2: Note draft recovery", 3, "b2"),
        node("Task 2: Amended", 3, "b2-dup"),
      ],
      { code: "CRF", filename: "x.md", documentId: "d", title: null },
    )
    expect(plan.kind).toBe("plan")
    expect(plan.title).toBe("Comprehensive Review Fixes")
    expect(plan.tasks.map((t) => [t.id, t.number, t.title, t.after, t.blockId])).toEqual([
      ["CRF-1", "1", "Repository ingestion boundaries", undefined, "b1"],
      ["CRF-2", "2", "Note draft recovery", "CRF-1", "b2"],
    ])
  })

  it("yields no tasks for a free-form plan", () => {
    const plan = planFromOutline([node("Plan", 1), node("Step 1", 2)], {
      code: "P", filename: "p.md", documentId: "d", title: "Plan",
    })
    expect(plan.tasks).toEqual([])
  })
})

describe("parsePlanLedger", () => {
  it("reads the agent's task lines, latest winning", () => {
    const ledger = parsePlanLedger(
      [
        "Task 1: projects endpoint reports work-log activity — done",
        "Task 2: frontend project summaries — wip",
        "#3 blocked: waiting on fixture",
        "| 4 | inventory route | review |",
        "Task 2: frontend project summaries — done, review approved",
        "Task 5: dispatched implementer",
        "- **Task 06** — DONE",
      ].join("\n"),
    )
    expect(Object.fromEntries(ledger)).toEqual({
      "1": "done",
      "2": "done",
      "3": "blocked",
      "4": "review",
      "6": "done",
    })
  })

  it("does not read a vocabulary word inside an identifier", () => {
    expect(parsePlanLedger("Task 1: DONE_WITH_CONCERNS").size).toBe(0)
  })
})

describe("planTaskStatus", () => {
  const steps = (...ticks: boolean[]) => ticks.map((checked) => ({ text: "s", checked }))

  it("reads a landed plan as done whatever its boxes say, except a dropped task", () => {
    const ledger = new Map([["2", "dropped" as const]])
    expect(planTaskStatus({ number: "1", completed: true, ledger, steps: steps(false) }))
      .toEqual({ status: "done", source: "completed" })
    expect(planTaskStatus({ number: "2", completed: true, ledger, steps: undefined }))
      .toEqual({ status: "dropped", source: "completed" })
  })

  it("prefers the ledger to the boxes", () => {
    const ledger = new Map([["1", "blocked" as const]])
    expect(planTaskStatus({ number: "1", completed: false, ledger, steps: steps(true) }))
      .toEqual({ status: "blocked", source: "ledger" })
  })

  it("falls back to the step boxes", () => {
    const at = (s: { text: string; checked: boolean }[]) =>
      planTaskStatus({ number: "1", completed: false, ledger: undefined, steps: s }).status
    expect(at(steps(true, true))).toBe("done")
    expect(at(steps(true, false))).toBe("wip")
    expect(at(steps(false, false))).toBe("todo")
    expect(at([])).toBe("todo")
  })
})

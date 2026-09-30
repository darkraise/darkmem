import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

import { parseLedger } from "../parse-ledger"
import { parseEpics } from "../parse-epics"
import { TASK_ID } from "../../types"

/**
 * Golden tests against the REAL committed planning files, not fixtures.
 *
 * The spec's §8 reasoning: these formats are only as stable as the corpus, so
 * the corpus is the fixture. A fixture would have passed for both of the bugs
 * these tests exist to catch.
 *
 * The pinned numbers below are MEASURED from the files at
 * `bb2215ee`, and they differ from the ones the design spec states. The spec
 * claimed 312 rows / 307 done / 2 todo / 2 dropped / 1 blocked; the file holds
 * 309 rows / 306 done / 1 todo / 2 dropped / 0 blocked. The spec's task-id
 * pattern (`^T\d+\.\d+[a-z]?$`) is why: it silently drops all 18 `TH*` rows
 * while still parsing 291 rows and looking perfectly healthy — exactly the
 * "parser that silently drops rows" failure §8 wanted pinned.
 */

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "../../../../../..")
const LEDGER = join(ROOT, "docs/planning/progress.md")
const TASKS = join(ROOT, "docs/planning/tasks")

const ledgerText = () => readFileSync(LEDGER, "utf-8")
const epicFiles = () => readdirSync(TASKS).filter((f) => f.endsWith(".md")).sort()
const allEpics = () =>
  epicFiles().map((f) => parseEpics(readFileSync(join(TASKS, f), "utf-8"), f))

describe("parseLedger against the committed ledger", () => {
  it("parses every task row and no non-task row", () => {
    const rows = parseLedger(ledgerText())
    expect(rows).toHaveLength(309)
    expect(rows.every((r) => TASK_ID.test(r.id))).toBe(true)
    expect(new Set(rows.map((r) => r.id)).size).toBe(rows.length)
  })

  it("keeps the TH-prefixed epic, which the spec's own pattern dropped", () => {
    const rows = parseLedger(ledgerText())
    expect(rows.filter((r) => r.id.startsWith("TH"))).toHaveLength(18)
  })

  it("reports the measured status distribution", () => {
    const rows = parseLedger(ledgerText())
    const counts: Record<string, number> = {}
    for (const r of rows) counts[r.rawStatus] = (counts[r.rawStatus] ?? 0) + 1
    expect(counts).toEqual({ done: 306, dropped: 2, todo: 1 })
  })

  it("skips the summary and legend tables rather than parsing them as tasks", () => {
    // The per-epic summary table's first cell is an epic name, the legend's is
    // a backticked status. Neither may reach the board as a card.
    const rows = parseLedger(ledgerText())
    expect(rows.some((r) => r.id.startsWith("E") || r.id.includes("`"))).toBe(false)
  })

  it("keeps a Note whose prose contains an unescaped pipe", () => {
    // Six rows split into 12-14 cells against an 11-column header. Zipping
    // would truncate the Note — the one cell a `blocked` card renders in full.
    const rows = parseLedger(ledgerText())
    const wide = rows.filter((r) => r.note.includes(" | ") || r.review.includes(" | "))
    expect(wide.length).toBeGreaterThan(0)
    expect(rows.find((r) => r.id === "T0.18")?.note).not.toBe("")
  })

  it("surfaces an unrecognised status instead of coercing it to todo", () => {
    const table = [
      "| Task | Title | Size | Model | Effort | Version | Owner | Status | Commit | Review | Note |",
      "|---|---|---|---|---|---|---|---|---|---|---|",
      "| T9.99 | Invented | S | Opus | high | — | nobody | dnoe | — | — | — |",
    ].join("\n")
    const rows = parseLedger(table)
    expect(rows).toHaveLength(1)
    expect(rows[0]?.status).toBeNull()
    expect(rows[0]?.rawStatus).toBe("dnoe")
  })
})

describe("parseEpics against the committed epic files", () => {
  it("parses EH2 to an epic with no tasks rather than throwing", () => {
    const file = "EH2-dotnet-migration.md"
    const epic = parseEpics(readFileSync(join(TASKS, file), "utf-8"), file)
    expect(epic.key).toBe("EH2")
    expect(epic.tasks).toEqual([])
    expect(epic.lanes).toEqual([])
    expect(epic.goal).toBeNull()
  })

  it("reads a multi-line field whole, not just its first line", () => {
    const file = "E3-synthesis-and-reach.md"
    const epic = parseEpics(readFileSync(join(TASKS, file), "utf-8"), file)
    // The startable filter reads this text to honour E3's G-D amendment, which
    // holds three named tasks shut and lets the rest of the epic through.
    expect(epic.entryGate).toContain("T3.02")
    expect(epic.entryGate).toContain("T3.03")
    expect(epic.entryGate).toContain("T3.10")
    expect(epic.branch).toBe("`feat/e3-synthesis-and-reach`")
  })

  it("gives every task a model tier from its metadata line", () => {
    const tasks = allEpics().flatMap((e) => e.tasks)
    expect(tasks).toHaveLength(309)
    expect(tasks.filter((t) => !t.meta.Model)).toEqual([])
    expect(tasks.filter((t) => !t.meta.Size)).toEqual([])
  })

  it("splits a metadata pair on its first colon only", () => {
    const t301 = allEpics()
      .flatMap((e) => e.tasks)
      .find((t) => t.id === "T3.01")
    expect(t301?.meta.Gate).toBe("G-D (entry)")
    expect(t301?.meta.Doc).toContain("§4.1")
  })

  it("assigns each task to the lane it sits under, and none where there is none", () => {
    const tasks = allEpics().flatMap((e) => e.tasks)
    expect(tasks.filter((t) => t.lane !== null)).toHaveLength(297)

    // Not every task sits under a lane: `M1-measurement.md` files 12 of its 33
    // under a plain `## Tasks` heading, ahead of its four lanes. `null` is the
    // honest parse, so grouping by lane needs an explicit unlaned bucket rather
    // than assuming the spec's "lanes are the structure" holds everywhere.
    const unlaned = tasks.filter((t) => t.lane === null)
    expect(unlaned).toHaveLength(12)
    expect(new Set(allEpics().filter((e) => e.tasks.some((t) => t.lane === null)).map((e) => e.key)))
      .toEqual(new Set(["M1"]))
  })

  it("carries the done-when checklist without aggregating it", () => {
    const tasks = allEpics().flatMap((e) => e.tasks)
    const items = tasks.flatMap((t) => t.doneWhen)
    // The measurement the board's UI copy must state: an unchecked list is not
    // unfinished work, and 806/17 across a substantially-shipped project is why
    // checkbox state is never read as status.
    expect(items.filter((i) => !i.checked)).toHaveLength(806)
    expect(items.filter((i) => i.checked)).toHaveLength(17)
  })
})

describe("the two files describe the same 309 tasks", () => {
  it("has no task in one file and not the other", () => {
    const ledger = new Set(parseLedger(ledgerText()).map((r) => r.id))
    const epic = new Set(allEpics().flatMap((e) => e.tasks.map((t) => t.id)))
    expect([...epic].filter((id) => !ledger.has(id))).toEqual([])
    expect([...ledger].filter((id) => !epic.has(id))).toEqual([])
  })
})

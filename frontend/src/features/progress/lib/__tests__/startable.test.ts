import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

import { parseLedger } from "../parse-ledger"
import { parseEpics } from "../parse-epics"
import { parseGates, gateHeldTaskIds } from "../parse-gates"
import { parseDepends, startableVerdict, unmetDependencies } from "../startable"
import type { LedgerRow } from "../../types"

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "../../../../../..")
const LEDGER = join(ROOT, "docs/planning/progress.md")
const TASKS = join(ROOT, "docs/planning/tasks")

const ledgerText = () => readFileSync(LEDGER, "utf-8")
const allEpics = () =>
  readdirSync(TASKS)
    .filter((f) => f.endsWith(".md"))
    .sort()
    .map((f) => parseEpics(readFileSync(join(TASKS, f), "utf-8"), f))

describe("parseGates against the committed summary table", () => {
  it("reads each epic's gate state and skips the Total row", () => {
    const gates = parseGates(ledgerText())
    expect(gates.get("E0")?.holding).toBe(false) // G-A CLEARED
    expect(gates.get("EH1")?.holding).toBe(false) // G-F CLEARED
    expect(gates.get("E2")?.holding).toBe(true) // G-C, G-D open
    expect(gates.get("E3")?.holding).toBe(true) // G-E open
    expect(gates.get("EH2")?.holding).toBe(true) // G-G closed
    // Neither of these is a gate, so neither holds anything.
    expect(gates.get("E4")?.holding).toBe(false) // demand-gated
    expect(gates.get("M1")?.holding).toBe(false) // gates nothing
    expect(gates.has("Total")).toBe(false)
  })
})

describe("gateHeldTaskIds", () => {
  it("honours E3's amendment: three tasks held, the rest of the epic open", () => {
    // The spec pins this case by name. E3's G-D was amended to hold only what
    // asserts groundedness; a board that blanked the epic would contradict
    // the file it renders.
    const e3 = allEpics().find((e) => e.key === "E3")!
    const held = gateHeldTaskIds(e3.entryGate, e3.tasks.map((t) => t.id))
    expect([...held].sort()).toEqual(["T3.02", "T3.03", "T3.10"])
    expect(e3.tasks.length).toBeGreaterThan(3)
  })

  it("ignores a named task the epic does not own", () => {
    // E3's gate text also names T2.41 -- the task that CLEARS G-D, which
    // lives in another epic. Held-shut and clears-the-gate are opposites.
    const e3 = allEpics().find((e) => e.key === "E3")!
    expect(e3.entryGate).toContain("T2.41")
    expect(gateHeldTaskIds(e3.entryGate, e3.tasks.map((t) => t.id)).has("T2.41"))
      .toBe(false)
  })
})

describe("parseDepends", () => {
  it("reads none, one and many", () => {
    expect(parseDepends("—")).toEqual({ ids: [], prose: [] })
    expect(parseDepends("T2.26, T2.54")).toEqual({
      ids: ["T2.26", "T2.54"],
      prose: [],
    })
  })

  it("keeps a human precondition rather than dropping it", () => {
    // `Depends: T2.109, **an owner-recorded argument**` is real in the
    // corpus. Dropping the prose half reports a task as startable when what
    // blocks it is a decision nobody has taken.
    const { ids, prose } = parseDepends("T2.109, **an owner-recorded argument**")
    expect(ids).toEqual(["T2.109"])
    expect(prose).toEqual(["**an owner-recorded argument**"])
  })
})

describe("startableVerdict", () => {
  const rows = () => new Map(parseLedger(ledgerText()).map((r) => [r.id, r]))

  it("refuses a task whose status is not todo", () => {
    const epics = allEpics()
    const map = rows()
    const gates = parseGates(ledgerText())
    const done = epics
      .flatMap((e) => e.tasks.map((t) => ({ t, e })))
      .find(({ t }) => map.get(t.id)?.rawStatus === "done")!
    const v = startableVerdict(done.t, map.get(done.t.id), done.e, gates.get(done.e.key), map)
    expect(v.startable).toBe(false)
    expect(v.reason).toContain("done")
  })

  it("refuses a todo whose dependency is unmet, naming it", () => {
    const map = new Map<string, LedgerRow>([
      ["T9.01", { ...blank("T9.01"), status: "todo", rawStatus: "todo" }],
      ["T9.00", { ...blank("T9.00"), status: "wip", rawStatus: "wip" }],
    ])
    const task = {
      id: "T9.01", number: "9.01", title: "t", lane: "Lane A",
      meta: { Depends: "T9.00" }, doneWhen: [],
    }
    const epic = {
      key: "E9", kind: "epic" as const, filename: "E9.md", title: "E9", goal: null,
      entryGate: null, doneWhen: null, branch: null,
      lanes: ["Lane A"], tasks: [task],
    }
    const v = startableVerdict(task, map.get("T9.01"), epic, undefined, map)
    expect(v.startable).toBe(false)
    expect(v.reason).toBe("waiting on T9.00")
    expect(unmetDependencies(task, map)).toEqual(["T9.00"])
  })

  it("accepts a todo with satisfied dependencies and no holding gate", () => {
    const map = new Map<string, LedgerRow>([
      ["T9.01", { ...blank("T9.01"), status: "todo", rawStatus: "todo" }],
      ["T9.00", { ...blank("T9.00"), status: "dropped", rawStatus: "dropped" }],
    ])
    const task = {
      id: "T9.01", number: "9.01", title: "t", lane: "Lane A",
      meta: { Depends: "T9.00" }, doneWhen: [],
    }
    const epic = {
      key: "E9", kind: "epic" as const, filename: "E9.md", title: "E9", goal: null,
      entryGate: null, doneWhen: null, branch: null,
      lanes: ["Lane A"], tasks: [task],
    }
    // `dropped` satisfies: its premise no longer holds, so nothing waits on it.
    expect(startableVerdict(task, map.get("T9.01"), epic, undefined, map).startable)
      .toBe(true)
  })
})

function blank(id: string): LedgerRow {
  return {
    id, title: "", size: "", model: "", effort: "", version: "", owner: "",
    status: null, rawStatus: "", commit: "", review: "", note: "",
  }
}

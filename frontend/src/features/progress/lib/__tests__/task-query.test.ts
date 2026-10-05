import { describe, it, expect } from "vitest"
import { findTaskByRef, matchesTaskQuery, parseTaskQuery } from "../task-query"
import type { BoardTask } from "../../use-progress-corpus"
import type { Epic } from "../../types"

const EPIC: Epic = {
  key: "CRF", kind: "plan", filename: "p.md", title: "p", goal: null, entryGate: null,
  doneWhen: null, branch: null, lanes: [], tasks: [],
}

function entry(id: string, number: string, title = `${id} title`): BoardTask {
  return {
    task: { id, number, title, lane: null, meta: {}, doneWhen: [] },
    row: undefined,
    epic: EPIC,
  }
}

describe("parseTaskQuery", () => {
  it("reads #n as a task number", () => {
    expect(parseTaskQuery("#6")).toEqual({ kind: "number", number: "6" })
    expect(parseTaskQuery(" #06 ")).toEqual({ kind: "number", number: "6" })
    expect(parseTaskQuery("#3.01")).toEqual({ kind: "number", number: "3.01" })
  })

  it("reads a plan reference in any of its spellings", () => {
    for (const q of ["CRF-6", "crf-6", "CRF#6", "crf # 6", "CRF-06"]) {
      expect(parseTaskQuery(q)).toEqual({ kind: "ref", ref: "CRF-6" })
    }
    expect(parseTaskQuery("pw-5a")).toEqual({ kind: "ref", ref: "PW-5A" })
    expect(parseTaskQuery("#5A")).toEqual({ kind: "number", number: "5a" })
  })

  it("reads words and a number without a dash as text", () => {
    expect(parseTaskQuery("phase 5")).toEqual({ kind: "text", text: "phase 5" })
  })

  it("reads an epic task id", () => {
    expect(parseTaskQuery("t3.01")).toEqual({ kind: "ref", ref: "T3.01" })
    expect(parseTaskQuery("TH1.14")).toEqual({ kind: "ref", ref: "TH1.14" })
  })

  it("falls back to text", () => {
    expect(parseTaskQuery("draft recovery")).toEqual({ kind: "text", text: "draft recovery" })
    expect(parseTaskQuery("  ")).toEqual({ kind: "empty" })
  })
})

describe("matchesTaskQuery", () => {
  const six = entry("CRF-6", "6", "Incremental code convergence")
  const t301 = entry("T3.01", "3.01")

  it("matches a number exactly, never as a substring", () => {
    expect(matchesTaskQuery(six, parseTaskQuery("#6"), "#6")).toBe(true)
    expect(matchesTaskQuery(entry("CRF-16", "16"), parseTaskQuery("#6"), "#6")).toBe(false)
    expect(matchesTaskQuery(t301, parseTaskQuery("#3.01"), "#3.01")).toBe(true)
  })

  it("matches a reference, and the raw text as a title fragment", () => {
    expect(matchesTaskQuery(six, parseTaskQuery("crf#6"), "crf#6")).toBe(true)
    const e2e = entry("AB-1", "1", "Fix the e2e-2 leg")
    expect(matchesTaskQuery(e2e, parseTaskQuery("e2e-2"), "e2e-2")).toBe(true)
  })

  it("shows a found reference alone, never its prefix-sharing neighbours", () => {
    const sixty = entry("CRF-60", "60")
    const q = parseTaskQuery("CRF-6")
    expect(matchesTaskQuery(sixty, q, "CRF-6", true)).toBe(false)
    expect(matchesTaskQuery(six, q, "CRF-6", true)).toBe(true)
  })
})

describe("findTaskByRef", () => {
  it("finds a task by any spelling of its reference, and nothing by a number", () => {
    const tasks = [entry("CRF-6", "6"), entry("T3.01", "3.01")]
    expect(findTaskByRef(tasks, "crf#6")?.task.id).toBe("CRF-6")
    expect(findTaskByRef(tasks, "T3.01")?.task.id).toBe("T3.01")
    expect(findTaskByRef(tasks, "#6")).toBeNull()
    expect(findTaskByRef(tasks, "CRF-7")).toBeNull()
  })
})

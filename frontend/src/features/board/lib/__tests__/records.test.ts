import { describe, expect, it } from "vitest"
import type { BoardRecords, ViewDefinition } from "@/hooks/api/use-board-api"
import {
  applyView,
  boardLanes,
  flattenRecords,
  formatProgress,
  isBlankNote,
  planMove,
  type BoardRecord,
} from "../records"

const DATA: BoardRecords = {
  project: "p",
  registers: [
    {
      document_id: "reg",
      uri: "superpowers/registers/r.md",
      title: "Register",
      covers: null,
      content_hash: "h1",
      block_first: false,
      malformed: [],
      error: null,
      rows: [
        {
          number: 1,
          item: "Alpha",
          assigned: "-",
          acceptance: "-",
          state: "open",
          raw_state: "open",
          note: "-",
          note_blank: true,
          line: 5,
          plan_uri: null,
          plan_progress: null,
        },
        {
          number: 2,
          item: "Beta",
          assigned: "docs/superpowers/plans/p.md",
          acceptance: "-",
          state: "verify",
          raw_state: "verify",
          note: "check beta",
          note_blank: false,
          line: 6,
          plan_uri: "superpowers/plans/p.md",
          plan_progress: { done: 1, total: 3, untracked: null },
        },
        {
          number: 3,
          item: "Gamma",
          assigned: "-",
          acceptance: "-",
          state: "unrecognised",
          raw_state: "parked",
          note: "-",
          note_blank: true,
          line: 7,
          plan_uri: null,
          plan_progress: null,
        },
      ],
    },
  ],
  plans: [
    {
      document_id: "plan",
      uri: "superpowers/plans/p.md",
      title: "Plan",
      content_hash: "h2",
      workstream: { id: "w", key: "plan-key", state: "open" },
      other_workstreams: 0,
      spec_uri: "superpowers/specs/s.md",
      untracked: null,
      orphans: [],
      error: null,
      tasks: [
        {
          number: 1,
          label: "Task 1: One",
          title: "One",
          line: 3,
          state: "done",
          raw_state: "done",
          untracked: null,
          shared_number: false,
          blocked_reason: null,
          commit: "abc1234",
          last_activity: "2026-10-13T00:00:00Z",
          steps: [],
        },
        {
          number: 2,
          label: "Task 2: Two",
          title: "Two",
          line: 9,
          state: "blocked",
          raw_state: "blocked",
          untracked: null,
          shared_number: false,
          blocked_reason: "waiting on beta",
          commit: null,
          last_activity: null,
          steps: [],
        },
      ],
    },
    {
      document_id: "loose",
      uri: "superpowers/plans/loose.md",
      title: "Loose",
      content_hash: "h3",
      workstream: null,
      other_workstreams: 0,
      spec_uri: null,
      untracked: "no_workstream",
      orphans: [],
      error: null,
      tasks: [
        {
          number: 1,
          label: "Task 1: Loose",
          title: "Loose",
          line: 3,
          state: "untracked",
          raw_state: null,
          untracked: "no_workstream",
          shared_number: false,
          blocked_reason: null,
          commit: null,
          last_activity: null,
          steps: [],
        },
      ],
    },
  ],
}

const BOARD: ViewDefinition = {
  layout: "board",
  group_by: "state",
  filters: [],
  sort: { property: "number", direction: "asc" },
  columns: [],
  show_untracked: false,
}

const records = flattenRecords(DATA)
const byTitle = (title: string) =>
  records.find((r) => r.title === title) as BoardRecord

describe("flattenRecords", () => {
  it("makes one record per row and per task, with type-specific fields", () => {
    expect(records.map((r) => [r.type, r.label])).toEqual([
      ["register_row", "#1"],
      ["register_row", "#2"],
      ["register_row", "#3"],
      ["plan_task", "Task 1: One"],
      ["plan_task", "Task 2: Two"],
      ["plan_task", "Task 1: Loose"],
    ])
    expect(byTitle("Beta").contentHash).toBe("h1")
    expect(byTitle("Two").note).toBe("waiting on beta")
    expect(byTitle("One").workstreamKey).toBe("plan-key")
    expect(new Set(records.map((r) => r.id)).size).toBe(records.length)
  })
})

describe("applyView", () => {
  it("hides untracked tasks unless asked", () => {
    expect(applyView(records, BOARD, "").map((r) => r.title)).not.toContain(
      "Loose",
    )
    expect(
      applyView(records, { ...BOARD, show_untracked: true }, "").map(
        (r) => r.title,
      ),
    ).toContain("Loose")
  })

  it("applies in, not_in and contains filters", () => {
    const view: ViewDefinition = {
      ...BOARD,
      filters: [
        { property: "type", operator: "in", values: ["register_row"] },
        { property: "state", operator: "not_in", values: ["open"] },
        { property: "title", operator: "contains", values: ["ET", "zzz"] },
      ],
    }
    expect(applyView(records, view, "").map((r) => r.title)).toEqual(["Beta"])
  })

  it("matches the text box against title and note", () => {
    expect(applyView(records, BOARD, "BETA").map((r) => r.title)).toEqual([
      "Beta",
      "Two",
    ])
  })

  it("sorts by the view's property and direction", () => {
    const view: ViewDefinition = {
      ...BOARD,
      sort: { property: "title", direction: "desc" },
    }
    expect(applyView(records, view, "").map((r) => r.title)).toEqual([
      "Two",
      "One",
      "Gamma",
      "Beta",
      "Alpha",
    ])
  })
})

describe("boardLanes", () => {
  it("splits a State grouping into one lane per type over its own vocabulary", () => {
    const lanes = boardLanes(applyView(records, BOARD, ""), "state", false)
    expect(lanes.map((l) => l.key)).toEqual(["register_row", "plan_task"])
    expect(lanes[0]!.columns.map((c) => c.key)).toEqual([
      "open",
      "planned",
      "doing",
      "verify",
      "done",
      "deferred",
      "n/a",
      "unrecognised",
    ])
    expect(lanes[1]!.columns.map((c) => c.key)).toEqual([
      "todo",
      "wip",
      "review",
      "blocked",
      "done",
      "unrecognised",
    ])
    expect(
      lanes[0]!.columns.find((c) => c.key === "unrecognised")!.records[0]!
        .title,
    ).toBe("Gamma")
  })

  it("adds the untracked column only when untracked tasks are shown", () => {
    const shown = { ...BOARD, show_untracked: true }
    const lanes = boardLanes(applyView(records, shown, ""), "state", true)
    expect(lanes[1]!.columns.map((c) => c.key)).toContain("untracked")
  })

  it("drops a lane the filters emptied", () => {
    const registersOnly: ViewDefinition = {
      ...BOARD,
      filters: [{ property: "type", operator: "in", values: ["register_row"] }],
    }
    expect(
      boardLanes(applyView(records, registersOnly, ""), "state", false),
    ).toHaveLength(1)
  })

  it("mixes types in shared columns for any other grouping", () => {
    const [lane] = boardLanes(applyView(records, BOARD, ""), "plan", false)
    expect(lane!.columns.map((c) => [c.title, c.records.length])).toEqual([
      ["p", 3],
      ["(none)", 2],
    ])
  })
})

describe("planMove", () => {
  it("locks plan tasks, ignores a same-column drop and asks for a note where needed", () => {
    expect(planMove(byTitle("One"), "todo")).toBe("locked")
    expect(planMove(byTitle("Alpha"), "open")).toBe("noop")
    expect(planMove(byTitle("Alpha"), "deferred")).toBe("note")
    expect(planMove(byTitle("Alpha"), "doing")).toBe("patch")
  })
})

describe("notes and progress", () => {
  it("reads a dash as a blank note", () => {
    expect(isBlankNote("-")).toBe(true)
    expect(isBlankNote("  ")).toBe(true)
    expect(isBlankNote("why")).toBe(false)
  })

  it("formats progress or names the untracked kind", () => {
    expect(formatProgress({ done: 1, total: 3, untracked: null })).toBe(
      "1 of 3 done",
    )
    expect(
      formatProgress({ done: 0, total: 3, untracked: "no_properties" }),
    ).toMatch(/no task properties/)
  })
})

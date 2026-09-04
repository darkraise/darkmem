import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { ProgressBoard } from "../progress-board"
import type { ProgressCorpus, BoardTask } from "../../use-progress-corpus"
import type { Epic, EpicTask, LedgerRow } from "../../types"

function row(id: string, status: string, extra: Partial<LedgerRow> = {}): LedgerRow {
  return {
    id, title: `${id} title`, size: "M", model: "Opus", effort: "high",
    version: "—", owner: "claude/lane-a",
    status: (["todo", "wip", "blocked", "review", "done", "dropped"].includes(status)
      ? status
      : null) as LedgerRow["status"],
    rawStatus: status, commit: "", review: "", note: "", ...extra,
  }
}

function task(id: string, lane: string | null, meta: Record<string, string> = {}): EpicTask {
  return { id, title: `${id} title`, lane, meta: { Model: "Opus", ...meta }, doneWhen: [] }
}

const BASE: Epic = {
  key: "E1", filename: "E1.md", title: "E1", goal: null, entryGate: null,
  doneWhen: null, branch: null, lanes: [], tasks: [],
}

function corpusOf(entries: [EpicTask, LedgerRow][]): ProgressCorpus {
  const rows = new Map(entries.map(([, r]) => [r.id, r]))
  const ep: Epic = { ...BASE, tasks: entries.map(([t]) => t) }
  const tasks: BoardTask[] = entries.map(([t, r]) => ({ task: t, row: r, epic: ep }))
  return {
    present: true, loading: false, tasks, epics: [ep], rows,
    gates: new Map(), orphanRows: [],
  }
}

describe("ProgressBoard", () => {
  it("renders a column per live status and hides dropped behind a disclosure", async () => {
    const corpus = corpusOf([
      [task("T1.01", "Lane A"), row("T1.01", "done")],
      [task("T1.02", "Lane A"), row("T1.02", "dropped")],
    ])
    render(<ProgressBoard corpus={corpus} />)

    expect(screen.getByRole("heading", { name: "todo" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "done" })).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: "dropped" })).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: /show dropped/i }))
    expect(screen.getByRole("heading", { name: "dropped" })).toBeInTheDocument()
  })

  it("surfaces an unrecognised status in its own column, never as todo", () => {
    // A typo in the file that gates merges must be visible on the board that
    // renders it -- bucketing it as `todo` would hide it.
    const corpus = corpusOf([[task("T1.01", "Lane A"), row("T1.01", "dnoe")]])
    render(<ProgressBoard corpus={corpus} />)

    expect(screen.getByRole("heading", { name: "unrecognised" })).toBeInTheDocument()
    expect(screen.getByText("T1.01")).toBeInTheDocument()
  })

  it("omits the unrecognised column when nothing lands in it", () => {
    const corpus = corpusOf([[task("T1.01", "Lane A"), row("T1.01", "done")]])
    render(<ProgressBoard corpus={corpus} />)
    expect(screen.queryByRole("heading", { name: "unrecognised" })).not.toBeInTheDocument()
  })

  it("gives unlaned tasks their own column rather than an invented lane", async () => {
    // M1 files 12 of its 33 tasks under a plain `## Tasks` heading.
    const corpus = corpusOf([
      [task("T1.01", null), row("T1.01", "done")],
      [task("T1.02", "Lane A"), row("T1.02", "done")],
    ])
    render(<ProgressBoard corpus={corpus} />)
    await userEvent.click(screen.getByText("Lane"))

    expect(screen.getByRole("heading", { name: "(no lane)" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Lane A" })).toBeInTheDocument()
  })

  it("renders a blocked task's note on the card, not behind a click", () => {
    // The one thing the eleven-column table genuinely hides.
    const corpus = corpusOf([
      [task("T1.01", "Lane A"), row("T1.01", "blocked", { note: "waiting on an owner ruling" })],
    ])
    render(<ProgressBoard corpus={corpus} />)
    expect(screen.getByText("waiting on an owner ruling")).toBeInTheDocument()
  })

  it("narrows to startable tasks and says why the others are not", async () => {
    const corpus = corpusOf([
      [task("T1.01", "Lane A", { Depends: "—" }), row("T1.01", "todo")],
      [task("T1.02", "Lane A", { Depends: "T1.03" }), row("T1.02", "todo")],
      [task("T1.03", "Lane A"), row("T1.03", "wip")],
    ])
    render(<ProgressBoard corpus={corpus} />)

    expect(screen.getByText("waiting on T1.03")).toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: /startable only/i }))
    expect(screen.getByText("T1.01")).toBeInTheDocument()
    expect(screen.queryByText("T1.02")).not.toBeInTheDocument()
  })
})

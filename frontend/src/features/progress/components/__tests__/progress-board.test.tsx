import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

vi.mock("@/hooks/api", () => ({
  // The plan source a plan task's detail reads on open.
  useDocumentContents: () => ({
    data: new Map([
      ["plan-doc", "# Plan\n\n### Task 2: Note draft recovery\n\n- [ ] Write the failing test\n"],
    ]),
    isLoading: false,
    isError: false,
  }),
}))

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
  return {
    id, number: id.replace(/^T[A-Z]?/, ""), title: `${id} title`, lane,
    meta: { Model: "Opus", ...meta }, doneWhen: [],
  }
}

const BASE: Epic = {
  key: "E1", kind: "epic", filename: "E1.md", title: "E1", goal: null, entryGate: null,
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

function planCorpus(): ProgressCorpus {
  const plan: Epic = {
    ...BASE, key: "CRF", kind: "plan", filename: "2026-10-03-crf.md",
    title: "Comprehensive review fixes", documentId: "plan-doc",
  }
  const other: Epic = { ...plan, key: "MGS", filename: "2026-09-29-mgs.md", title: "Graph scale" }
  const planTask = (epic: Epic, n: number, title: string): EpicTask => ({
    id: `${epic.key}-${n}`, number: String(n), title, lane: null, meta: {}, doneWhen: [],
    after: n > 1 ? `${epic.key}-${n - 1}` : undefined, blockId: `b${n}`,
  })
  const entries: [EpicTask, LedgerRow, Epic][] = [
    [planTask(plan, 1, "Repository ingestion boundaries"), row("CRF-1", "done"), plan],
    [planTask(plan, 2, "Note draft recovery"), row("CRF-2", "todo"), plan],
    [planTask(other, 2, "Bulk vector read"), row("MGS-2", "done"), other],
  ]
  return {
    present: true, loading: false,
    tasks: entries.map(([t, r, e]) => ({ task: t, row: r, epic: e, statusFrom: "steps" as const })),
    epics: [plan, other],
    rows: new Map(entries.map(([, r]) => [r.id, r])),
    gates: new Map(), orphanRows: [],
  }
}

describe("ProgressBoard task references", () => {
  it("shows each plan task under its reference and chains it after its predecessor", () => {
    render(<ProgressBoard corpus={planCorpus()} />)
    expect(screen.getByText("CRF-1")).toBeInTheDocument()
    expect(screen.getByText("CRF-2")).toBeInTheDocument()
    expect(screen.getByText("MGS-2")).toBeInTheDocument()
    // CRF-1 is done, so CRF-2 is the plan's next startable task.
    expect(screen.queryByText("waiting on CRF-1")).not.toBeInTheDocument()
  })

  it("narrows #n to every task numbered n and opens it once one is left", async () => {
    render(<ProgressBoard corpus={planCorpus()} />)
    const box = screen.getByRole("textbox", { name: /filter by reference/i })

    await userEvent.type(box, "#2")
    expect(screen.queryByText("CRF-1")).not.toBeInTheDocument()
    expect(screen.getByText("CRF-2")).toBeInTheDocument()
    expect(screen.getByText("MGS-2")).toBeInTheDocument()
    expect(screen.getByText(/2 tasks match/)).toBeInTheDocument()

    // Ambiguous: Enter opens nothing.
    await userEvent.keyboard("{Enter}")
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole("combobox", { name: "Epic / plan" }))
    await userEvent.click(await screen.findByRole("option", { name: /CRF — Comprehensive/ }))
    expect(screen.getByText("Enter opens CRF-2.")).toBeInTheDocument()

    await userEvent.click(box)
    await userEvent.keyboard("{Enter}")
    const dialog = await screen.findByRole("dialog")
    expect(dialog).toHaveTextContent("CRF-2")
    expect(dialog).toHaveTextContent("Task 2 of plan CRF")
    expect(dialog).toHaveTextContent("Write the failing test")
  })

  it("opens a reference typed in any spelling with Enter", async () => {
    render(<ProgressBoard corpus={planCorpus()} />)
    await userEvent.type(
      screen.getByRole("textbox", { name: /filter by reference/i }),
      "mgs#2{Enter}",
    )
    expect(await screen.findByRole("dialog")).toHaveTextContent("Bulk vector read")
  })

  it("lets the route own the open task, and reports opening and closing it", async () => {
    const onChange = vi.fn()
    const { rerender } = render(
      <ProgressBoard corpus={planCorpus()} openTask="crf-2" onOpenTaskChange={onChange} />,
    )
    expect(await screen.findByRole("dialog")).toHaveTextContent("Note draft recovery")

    await userEvent.keyboard("{Escape}")
    expect(onChange).toHaveBeenLastCalledWith(null)

    rerender(<ProgressBoard corpus={planCorpus()} openTask={null} onOpenTaskChange={onChange} />)
    await userEvent.click(screen.getByText("CRF-1"))
    expect(onChange).toHaveBeenLastCalledWith("CRF-1")
  })

  it("says so when the linked reference names no task", () => {
    render(<ProgressBoard corpus={planCorpus()} openTask="CRF-99" onOpenTaskChange={() => {}} />)
    expect(screen.getByText(/No task CRF-99 on this board/)).toBeInTheDocument()
  })

  it("opens the plan at the task's heading", async () => {
    const onOpenDocument = vi.fn()
    render(
      <ProgressBoard corpus={planCorpus()} openTask="CRF-2" onOpenTaskChange={() => {}}
        onOpenDocument={onOpenDocument} />,
    )
    await userEvent.click(await screen.findByRole("button", { name: /open in plan/i }))
    expect(onOpenDocument).toHaveBeenCalledWith("plan-doc", "b2")
  })
})

describe("ProgressBoard while loading", () => {
  it("shows a loading board, never the false no-match state or a missing-task notice", () => {
    const corpus: ProgressCorpus = { ...planCorpus(), loading: true, tasks: [] }
    render(<ProgressBoard corpus={corpus} openTask="CRF-2" onOpenTaskChange={() => {}} />)
    expect(screen.getByLabelText("Loading the board")).toBeInTheDocument()
    expect(screen.queryByText(/No tasks match/)).not.toBeInTheDocument()
    expect(screen.queryByText(/No task CRF-2/)).not.toBeInTheDocument()
  })
})

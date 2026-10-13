import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { boardLanes, flattenRecords, type BoardRecord } from "../lib/records"
import { BoardView, dropTarget } from "../components/board-view"
import { RECORDS } from "./fixtures"

const records = flattenRecords(RECORDS)
const byTitle = (title: string) =>
  records.find((r) => r.title === title) as BoardRecord

describe("BoardView", () => {
  it("renders one swimlane per type, each over its own vocabulary", () => {
    const tracked = records.filter((r) => r.state !== "untracked")
    render(
      <BoardView
        lanes={boardLanes(tracked, "state", false)}
        isPending={() => false}
        onMove={vi.fn()}
        onOpen={vi.fn()}
      />,
    )
    const rows = screen.getByRole("region", { name: "Register rows" })
    const tasks = screen.getByRole("region", { name: "Plan tasks" })
    expect(
      within(rows).getByRole("heading", { name: /^verify/ }),
    ).toBeInTheDocument()
    expect(within(rows).queryByRole("heading", { name: /^todo/ })).toBeNull()
    expect(
      within(tasks).getByRole("heading", { name: /^blocked/ }),
    ).toBeInTheDocument()
    expect(
      within(tasks).queryByRole("heading", { name: /^planned/ }),
    ).toBeNull()
  })

  it("makes register cards draggable and plan-task cards locked", () => {
    render(
      <BoardView
        lanes={boardLanes(records, "state", false)}
        isPending={() => false}
        onMove={vi.fn()}
        onOpen={vi.fn()}
      />,
    )
    const row = screen.getByRole("group", { name: /#1 Alpha/ })
    expect(row).toHaveAttribute("aria-roledescription", "draggable")
    const task = screen.getByRole("article", { name: "Task 2: Two" })
    expect(task).not.toHaveAttribute("aria-roledescription")
    expect(
      within(task).getByLabelText("state comes from the plan's ledger"),
    ).toBeInTheDocument()
    expect(within(task).getByText("waiting on beta")).toBeInTheDocument()
  })

  it("opens any card from the keyboard, and Enter on a draggable card's title opens rather than drags", async () => {
    const onOpen = vi.fn()
    const onMove = vi.fn()
    const user = userEvent.setup()
    render(
      <BoardView
        lanes={boardLanes(records, "state", false)}
        isPending={() => false}
        onMove={onMove}
        onOpen={onOpen}
      />,
    )
    screen.getByRole("button", { name: "Alpha" }).focus()
    await user.keyboard("{Enter}")
    expect(onOpen).toHaveBeenLastCalledWith(byTitle("Alpha"))
    screen.getByRole("button", { name: "Two" }).focus()
    await user.keyboard(" ")
    expect(onOpen).toHaveBeenLastCalledWith(byTitle("Two"))
    expect(onOpen).toHaveBeenCalledTimes(2)
    expect(onMove).not.toHaveBeenCalled()
  })

  it("says when a row's plan could not be read", () => {
    const alpha = byTitle("Alpha")
    const linked: BoardRecord = {
      ...alpha,
      plan: "superpowers/plans/p.md",
      planProgress: null,
      planError: "RuntimeError: parser exploded",
    }
    render(
      <BoardView
        lanes={boardLanes([linked], "state", false)}
        isPending={() => false}
        onMove={vi.fn()}
        onOpen={vi.fn()}
      />,
    )
    expect(screen.getByText("plan unreadable")).toHaveAttribute(
      "title",
      "RuntimeError: parser exploded",
    )
  })

  it("shows a pending card as saving", () => {
    render(
      <BoardView
        lanes={boardLanes(records, "state", false)}
        isPending={(id) => id === byTitle("Alpha").id}
        onMove={vi.fn()}
        onOpen={vi.fn()}
      />,
    )
    expect(screen.getByText("saving…")).toBeInTheDocument()
  })

  it("reads a drop's target state only from a register column", () => {
    expect(dropTarget({ over: { id: "state:planned" } } as never)).toBe(
      "planned",
    )
    expect(dropTarget({ over: { id: "elsewhere" } } as never)).toBeNull()
    expect(dropTarget({ over: null })).toBeNull()
  })

  it("names which untracked kind applies on a plan-task card", () => {
    const loose = byTitle("Loose")
    const unpushed: BoardRecord = {
      ...loose,
      id: "t:unpushed:3",
      title: "Unpushed",
      untracked: "no_properties",
    }
    render(
      <BoardView
        lanes={boardLanes([loose, unpushed], "state", true)}
        isPending={() => false}
        onMove={vi.fn()}
        onOpen={vi.fn()}
      />,
    )
    expect(
      screen.getByText(/no workstream names this plan/),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/the ledger carries no task properties/),
    ).toBeInTheDocument()
  })
})

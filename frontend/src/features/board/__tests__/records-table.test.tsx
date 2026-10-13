import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import type { ViewDefinition } from "@/hooks/api"
import { flattenRecords, type BoardRecord } from "../lib/records"
import { RecordsTable } from "../components/records-table"
import { RecordDetailSheet } from "../components/record-detail-sheet"
import type { RowEditor } from "../use-row-editor"
import { RECORDS } from "./fixtures"

const records = flattenRecords(RECORDS)
const byTitle = (title: string) =>
  records.find((r) => r.title === title) as BoardRecord
const TABLE: ViewDefinition = {
  layout: "table",
  group_by: null,
  filters: [],
  sort: null,
  columns: ["number", "title", "state", "assigned", "note"],
  show_untracked: true,
}

function editor(): RowEditor {
  return {
    save: vi.fn(),
    move: vi.fn(),
    prompt: null,
    confirmPrompt: vi.fn(),
    cancelPrompt: vi.fn(),
    isPending: () => false,
    promptPending: false,
    editEpoch: () => 0,
  }
}

describe("RecordsTable", () => {
  it("sorts on a header click, flipping direction on a second click", async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    const { rerender } = render(
      <RecordsTable
        records={records}
        definition={TABLE}
        onDefinitionChange={onChange}
        editor={editor()}
        onOpen={vi.fn()}
      />,
    )
    await user.click(screen.getByRole("button", { name: "Title" }))
    expect(onChange).toHaveBeenLastCalledWith({
      ...TABLE,
      sort: { property: "title", direction: "asc" },
    })
    const sorted = {
      ...TABLE,
      sort: { property: "title", direction: "asc" } as const,
    }
    rerender(
      <RecordsTable
        records={records}
        definition={sorted}
        onDefinitionChange={onChange}
        editor={editor()}
        onOpen={vi.fn()}
      />,
    )
    expect(screen.getByRole("columnheader", { name: /Title/ })).toHaveAttribute(
      "aria-sort",
      "ascending",
    )
    await user.click(screen.getByRole("button", { name: "Title ↑" }))
    expect(onChange).toHaveBeenLastCalledWith({
      ...TABLE,
      sort: { property: "title", direction: "desc" },
    })
  })

  it("edits State only on register rows", () => {
    render(
      <RecordsTable
        records={records}
        definition={TABLE}
        onDefinitionChange={vi.fn()}
        editor={editor()}
        onOpen={vi.fn()}
      />,
    )
    expect(
      screen.getByRole("combobox", { name: "State of #1" }),
    ).toBeInTheDocument()
    expect(screen.queryByRole("combobox", { name: /State of Task/ })).toBeNull()
    const taskRow = screen.getByRole("button", { name: "Two" }).closest("tr")!
    expect(within(taskRow).getByText("blocked")).toBeInTheDocument()
  })

  it("commits an edited Note through the same PATCH", async () => {
    const rows = editor()
    const user = userEvent.setup()
    render(
      <RecordsTable
        records={records}
        definition={TABLE}
        onDefinitionChange={vi.fn()}
        editor={rows}
        onOpen={vi.fn()}
      />,
    )
    await user.click(screen.getByLabelText("Note of #2"))
    const input = screen.getByLabelText("Edit Note of #2")
    await user.clear(input)
    await user.type(input, "checked by hand{Enter}")
    expect(rows.save).toHaveBeenCalledWith(byTitle("Beta"), {
      note: "checked by hand",
    })
  })

  it("shows the stored Note again after its edit is refused", async () => {
    const rows = editor()
    const user = userEvent.setup()
    const show = () => (
      <RecordsTable
        records={records}
        definition={TABLE}
        onDefinitionChange={vi.fn()}
        editor={rows}
        onOpen={vi.fn()}
      />
    )
    const { rerender } = render(show())
    const stored = screen.getByLabelText("Note of #2").textContent
    await user.click(screen.getByLabelText("Note of #2"))
    const input = screen.getByLabelText("Edit Note of #2")
    await user.clear(input)
    await user.type(input, "rejected text{Enter}")
    expect(screen.getByLabelText("Note of #2")).toHaveTextContent("rejected text")

    rows.editEpoch = () => 1
    rerender(show())
    expect(screen.getByLabelText("Note of #2").textContent).toBe(stored)
  })
})

describe("RecordDetailSheet", () => {
  it("shows every property, the labelled checklist and the Work log link", async () => {
    const onShow = vi.fn()
    const onOpenDocument = vi.fn()
    const user = userEvent.setup()
    render(
      <RecordDetailSheet
        record={byTitle("One")}
        onClose={vi.fn()}
        onOpenDocument={onOpenDocument}
        onShowInWorkLog={onShow}
      />,
    )
    expect(screen.getByText("Commit")).toBeInTheDocument()
    expect(screen.getByText("abc1234def")).toBeInTheDocument()
    const checklist = screen.getByRole("region", {
      name: "implementer's checklist",
    })
    expect(
      within(checklist).getByText("Step 1: Write the failing test"),
    ).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Show in Work log" }))
    expect(onShow).toHaveBeenCalledWith("plan-key", 1)
    await user.click(screen.getByRole("button", { name: "Open spec" }))
    expect(onOpenDocument).toHaveBeenCalledWith("superpowers/specs/s.md")
  })

  it("links a register row to its register and its assigned plan", async () => {
    const onOpenDocument = vi.fn()
    const user = userEvent.setup()
    render(
      <RecordDetailSheet
        record={byTitle("Beta")}
        onClose={vi.fn()}
        onOpenDocument={onOpenDocument}
        onShowInWorkLog={vi.fn()}
      />,
    )
    await user.click(screen.getByRole("button", { name: "Open register" }))
    await user.click(screen.getByRole("button", { name: "Open plan" }))
    expect(onOpenDocument.mock.calls).toEqual([
      ["superpowers/registers/r.md"],
      ["superpowers/plans/p.md"],
    ])
  })
})

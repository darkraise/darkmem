import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import type { ViewDefinition } from "@/hooks/api"
import { BoardToolbar, withInFilter } from "../components/board-toolbar"
import { ViewNameDialog } from "../components/view-dialogs"
import { flattenRecords } from "../lib/records"
import { RECORDS } from "./fixtures"

const BUILTIN: ViewDefinition = {
  layout: "board",
  group_by: "state",
  filters: [
    { property: "type", operator: "in", values: ["register_row"] },
    { property: "state", operator: "not_in", values: ["done", "n/a"] },
  ],
  sort: null,
  columns: [],
  show_untracked: false,
}

describe("withInFilter", () => {
  it("replaces only the property's in filter and keeps its not_in", () => {
    const next = withInFilter(BUILTIN, "state", ["open"])
    expect(next.filters).toEqual([
      { property: "type", operator: "in", values: ["register_row"] },
      { property: "state", operator: "not_in", values: ["done", "n/a"] },
      { property: "state", operator: "in", values: ["open"] },
    ])
  })

  it("drops the in filter when nothing is selected", () => {
    expect(withInFilter(BUILTIN, "type", []).filters).toEqual([
      { property: "state", operator: "not_in", values: ["done", "n/a"] },
    ])
  })
})

describe("BoardToolbar", () => {
  it("switches layout, toggles untracked and reports the text match", async () => {
    const onChange = vi.fn()
    const onTextChange = vi.fn()
    const user = userEvent.setup()
    render(
      <BoardToolbar
        records={flattenRecords(RECORDS)}
        definition={BUILTIN}
        onChange={onChange}
        text=""
        onTextChange={onTextChange}
      />,
    )
    await user.click(screen.getByRole("radio", { name: "Table" }))
    expect(onChange).toHaveBeenLastCalledWith({ ...BUILTIN, layout: "table" })
    await user.click(screen.getByRole("switch"))
    expect(onChange).toHaveBeenLastCalledWith({
      ...BUILTIN,
      show_untracked: true,
    })
    await user.type(
      screen.getByRole("textbox", { name: "Search title and note" }),
      "b",
    )
    expect(onTextChange).toHaveBeenLastCalledWith("b")
  })
})

describe("ViewNameDialog", () => {
  it("submits a trimmed name and refuses a blank one", async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(
      <ViewNameDialog
        open
        title="Save as view"
        initial=""
        pending={false}
        onSubmit={onSubmit}
        onCancel={vi.fn()}
      />,
    )
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled()
    await user.type(screen.getByLabelText("Name"), "  Mine  ")
    await user.click(screen.getByRole("button", { name: "Save" }))
    expect(onSubmit).toHaveBeenCalledWith("Mine")
  })
})

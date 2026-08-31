import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { IndexingModesFields } from "../components/indexing-modes-fields"

const OFF = {
  fetch_enabled: false,
  fetch_interval_seconds: 300,
  index_on_commit_enabled: false,
  commit_poll_seconds: 60,
  index_uncommitted: false,
}

describe("IndexingModesFields", () => {
  it("disables an interval while its switch is off", () => {
    render(<IndexingModesFields value={OFF} onChange={vi.fn()} />)

    expect(screen.getByLabelText(/fetch interval/i)).toBeDisabled()
    expect(screen.getByLabelText(/commit poll interval/i)).toBeDisabled()
  })

  it("disables the uncommitted option until commit watching is on", () => {
    const { rerender } = render(
      <IndexingModesFields value={OFF} onChange={vi.fn()} />,
    )
    expect(screen.getByRole("switch", { name: /uncommitted/i })).toBeDisabled()

    rerender(
      <IndexingModesFields
        value={{ ...OFF, index_on_commit_enabled: true }}
        onChange={vi.fn()}
      />,
    )
    expect(
      screen.getByRole("switch", { name: /uncommitted/i }),
    ).not.toBeDisabled()
  })

  it("says which switch writes to the working tree", () => {
    // The asymmetry an operator sharing a checkout needs, and the one thing
    // not inferable from the switch names.
    render(<IndexingModesFields value={OFF} onChange={vi.fn()} />)

    expect(screen.getByText(/advances your working tree/i)).toBeInTheDocument()
  })

  it("toggles a switch when its caption is clicked", async () => {
    // The caption has to be a real <label> for its switch: an aria-label on
    // the switch names it for assistive tech but associates nothing, so the
    // visible text beside it stops being a click target.
    const onChange = vi.fn()
    render(<IndexingModesFields value={OFF} onChange={onChange} />)

    await userEvent.click(screen.getByText("Fetch from remote"))
    expect(onChange).toHaveBeenCalledWith({ ...OFF, fetch_enabled: true })

    onChange.mockClear()
    await userEvent.click(screen.getByText("Also index uncommitted changes"))
    expect(onChange).not.toHaveBeenCalled() // still disabled

    onChange.mockClear()
    await userEvent.click(screen.getByText("Index on new commit"))
    expect(onChange).toHaveBeenCalledWith({
      ...OFF,
      index_on_commit_enabled: true,
    })
  })

  it("shows each interval in the unit it is stored in", async () => {
    // Displayed in minutes, the fetch interval's 30-second floor rendered as
    // 0.5 and its stepper walked half-minutes off the stored grain.
    const onChange = vi.fn()
    const ON = { ...OFF, fetch_enabled: true, index_on_commit_enabled: true }
    render(<IndexingModesFields value={ON} onChange={onChange} />)

    expect(screen.getByLabelText(/fetch interval/i)).toHaveValue("300")
    expect(screen.getByLabelText(/commit poll interval/i)).toHaveValue("60")

    // One step off the stored value, never a fraction of it.
    await userEvent.clear(screen.getByLabelText(/fetch interval/i))
    await userEvent.type(screen.getByLabelText(/fetch interval/i), "330")
    expect(onChange).toHaveBeenLastCalledWith({
      ...ON,
      fetch_interval_seconds: 330,
    })
  })

  it("emits the whole value on a toggle", async () => {
    const onChange = vi.fn()
    render(<IndexingModesFields value={OFF} onChange={onChange} />)

    await userEvent.click(
      screen.getByRole("switch", { name: /fetch from remote/i }),
    )

    expect(onChange).toHaveBeenCalledWith({ ...OFF, fetch_enabled: true })
  })
})

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
    const { rerender } = render(<IndexingModesFields value={OFF} onChange={vi.fn()} />)
    expect(screen.getByRole("switch", { name: /uncommitted/i })).toBeDisabled()

    rerender(
      <IndexingModesFields
        value={{ ...OFF, index_on_commit_enabled: true }}
        onChange={vi.fn()}
      />,
    )
    expect(screen.getByRole("switch", { name: /uncommitted/i })).not.toBeDisabled()
  })

  it("says which switch writes to the working tree", () => {
    // The asymmetry an operator sharing a checkout needs, and the one thing
    // not inferable from the switch names.
    render(<IndexingModesFields value={OFF} onChange={vi.fn()} />)

    expect(screen.getByText(/advances your working tree/i)).toBeInTheDocument()
  })

  it("emits the whole value on a toggle", async () => {
    const onChange = vi.fn()
    render(<IndexingModesFields value={OFF} onChange={onChange} />)

    await userEvent.click(screen.getByRole("switch", { name: /fetch from remote/i }))

    expect(onChange).toHaveBeenCalledWith({ ...OFF, fetch_enabled: true })
  })
})

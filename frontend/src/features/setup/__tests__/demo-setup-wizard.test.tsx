import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { DemoSetupWizard } from "../components/demo-setup-wizard"

const password = (value: string) => {
  fireEvent.change(screen.getByLabelText("Admin password"), {
    target: { value },
  })
  fireEvent.change(screen.getByLabelText("Confirm password"), {
    target: { value },
  })
}

describe("DemoSetupWizard", () => {
  it("gates step 1 on a matching 8+ char password", () => {
    render(<DemoSetupWizard onFinish={() => {}} />)
    const next = screen.getByRole("button", { name: "Next" })
    expect(next).toBeDisabled()
    fireEvent.change(screen.getByLabelText("Admin password"), {
      target: { value: "hunter2hunter2" },
    })
    fireEvent.change(screen.getByLabelText("Confirm password"), {
      target: { value: "different" },
    })
    expect(screen.getByText("Passwords do not match.")).toBeInTheDocument()
    expect(next).toBeDisabled()
    password("hunter2hunter2")
    expect(next).toBeEnabled()
  })

  it("walks password → LLM → repo → finish and calls onFinish", () => {
    vi.useFakeTimers()
    const onFinish = vi.fn()
    render(<DemoSetupWizard onFinish={onFinish} />)
    password("hunter2hunter2")
    fireEvent.click(screen.getByRole("button", { name: "Next" }))

    // Step 2 — default LLM provider; fetch fills the per-purpose models.
    expect(screen.getByText("Per-purpose models")).toBeInTheDocument()
    fireEvent.click(
      screen.getByRole("button", { name: /Fetch available models/ }),
    )
    expect(screen.getByText("14 models loaded")).toBeInTheDocument()
    expect(screen.getByLabelText("reasoning model")).toHaveValue("gpt-5.1")
    fireEvent.click(screen.getByRole("button", { name: "Next" }))

    // Step 3 — git dirs are pre-selected.
    expect(screen.getByText(/found/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Next" }))

    // Step 4 — review, then finish.
    expect(screen.getByText(/Nothing has been sent yet/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Finish" }))
    expect(onFinish).not.toHaveBeenCalled()
    vi.runAllTimers()
    expect(onFinish).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })

  it("Skip records the skipped state in the finish summary", () => {
    render(<DemoSetupWizard onFinish={() => {}} />)
    password("hunter2hunter2")
    fireEvent.click(screen.getByRole("button", { name: "Next" }))
    fireEvent.click(screen.getByRole("button", { name: "Skip" }))
    fireEvent.click(screen.getByRole("button", { name: "Skip" }))
    expect(
      screen.getByText(/defaults to a local Ollama/),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/register repositories later/i),
    ).toBeInTheDocument()
  })
})

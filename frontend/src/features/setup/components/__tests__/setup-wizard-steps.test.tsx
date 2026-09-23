import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn().mockResolvedValue({}) }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  useNavigate: () => vi.fn(),
}))

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useSetupWizardStore } from "@/features/setup/setupWizardStore"
import { SetupWizard } from "../SetupWizard"

function renderWizard() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <SetupWizard />
    </QueryClientProvider>,
  )
}

const stepButton = (name: RegExp) => screen.getByRole("button", { name })

describe("SetupWizard step list", () => {
  beforeEach(() => {
    useSetupWizardStore.getState().reset()
    useSetupWizardStore.getState().setPassword("hunter2hunter2", "hunter2hunter2")
  })

  it("does not let an unvisited step be clicked", () => {
    renderWizard()
    expect(stepButton(/Default LLM provider/)).toBeDisabled()
  })

  it("navigates back and forward between visited steps", () => {
    const s = useSetupWizardStore.getState()
    s.setStep(2)
    s.setLlmSkipped(true)
    s.setStep(3)
    renderWizard()

    fireEvent.click(stepButton(/Admin password/))
    expect(useSetupWizardStore.getState().step).toBe(1)

    fireEvent.click(stepButton(/Default code repo path/))
    expect(useSetupWizardStore.getState().step).toBe(3)
    expect(stepButton(/Review & finish/)).toBeDisabled()
  })

  it("will not jump forward past a step that fails its own check", () => {
    const s = useSetupWizardStore.getState()
    s.setStep(3)
    s.setStep(1)
    s.setPassword("short", "short")
    renderWizard()
    expect(stepButton(/Default code repo path/)).toBeDisabled()
  })
})

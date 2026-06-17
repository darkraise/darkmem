import { describe, expect, it, vi } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

vi.mock("@/hooks/api", () => ({
  useProviderModels: vi.fn(() => ({
    data: { models: ["model-a", "model-b"], error: null, fetched_via: "" },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  useTestLlmProvider: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

import { LLMProviderTestDialog } from "@/features/pipeline/LLMProviderTestDialog"

describe("LLMProviderTestDialog", () => {
  it("stays open when a model is picked from the portaled dropdown", async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    render(
      <LLMProviderTestDialog
        providerName="ollama"
        mode="chat"
        open
        onOpenChange={onOpenChange}
      />,
    )

    await user.click(screen.getByRole("combobox"))
    const option = await screen.findByRole("option", { name: "model-b" })
    await user.click(option)

    // The dropdown is portaled outside the dialog DOM; without the
    // pointerdown-outside guard this click dismissed the whole dialog.
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
    expect(screen.getByRole("dialog")).toBeInTheDocument()
    await waitFor(() =>
      expect(screen.getByRole("combobox")).toHaveTextContent("model-b"),
    )
  })
})

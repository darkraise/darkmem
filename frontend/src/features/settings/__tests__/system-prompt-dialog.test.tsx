import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { SystemPromptDialog } from "../components/system-prompt-dialog"

const DEFAULT_PROMPT = "# Extract\n\nReturn JSON."
const OVERRIDE_PROMPT = "# Extract\n\nReturn JSON, and be terse."

function payload(overrides: Record<string, string> = {}) {
  return {
    defaults: { extraction: DEFAULT_PROMPT },
    overrides,
    effective: { extraction: overrides.extraction ?? DEFAULT_PROMPT },
  }
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function renderDialog() {
  return render(
    <SystemPromptDialog
      open
      onOpenChange={() => {}}
      promptKey="extraction"
      title="extraction system prompt"
      description="Sent on every extraction call."
    />,
    { wrapper },
  )
}

async function openAndWait() {
  const user = userEvent.setup()
  renderDialog()
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Edit prompt" })).toBeInTheDocument(),
  )
  return user
}

describe("SystemPromptDialog", () => {
  afterEach(() => vi.clearAllMocks())

  it("shows the effective prompt and labels an unedited one as the default", async () => {
    vi.mocked(apiFetch).mockResolvedValue(payload())
    await openAndWait()

    expect(apiFetch).toHaveBeenCalledWith("/config/system-prompts")
    expect(screen.getByText("default")).toBeInTheDocument()
    expect(screen.getByText(/Return JSON\./)).toBeInTheDocument()
  })

  // `effective`, not `defaults`: an override is what the model is actually
  // served, so rendering the default would misreport the running system.
  it("shows the override, badged as overridden, when one exists", async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      payload({ extraction: OVERRIDE_PROMPT }),
    )
    await openAndWait()

    expect(screen.getByText("overridden")).toBeInTheDocument()
    expect(screen.getByText(/be terse/)).toBeInTheDocument()
  })

  it("renders markdown in the rendered view and raw text in the plain view", async () => {
    vi.mocked(apiFetch).mockResolvedValue(payload())
    const user = await openAndWait()

    // Plain is the default view: the literal bytes, heading marker included.
    expect(screen.getByText(/# Extract/)).toBeInTheDocument()

    await user.click(screen.getByRole("radio", { name: "Rendered markdown" }))
    expect(screen.getByRole("heading", { name: "Extract" })).toBeInTheDocument()
  })

  it("shows both panes at once in split view", async () => {
    vi.mocked(apiFetch).mockResolvedValue(payload())
    const user = await openAndWait()

    await user.click(screen.getByRole("radio", { name: "Split view" }))
    expect(screen.getByText(/# Extract/)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Extract" })).toBeInTheDocument()
  })

  it("PUTs an edited prompt as an override for its own key", async () => {
    vi.mocked(apiFetch).mockResolvedValue(payload())
    const user = await openAndWait()

    await user.click(screen.getByRole("button", { name: "Edit prompt" }))
    const field = screen.getByRole("textbox", {
      name: "extraction system prompt",
    })
    await user.clear(field)
    await user.type(field, "Be terse.")
    await user.click(screen.getByRole("button", { name: "Save" }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith("/config/system-prompts", {
        method: "PUT",
        body: JSON.stringify({ overrides: { extraction: "Be terse." } }),
      }),
    )
  })

  // Storing a copy of the default would pin the prompt to today's wording, so
  // a later default improvement would never reach this installation.
  it("clears the override rather than storing a copy of the default", async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      payload({ extraction: OVERRIDE_PROMPT }),
    )
    const user = await openAndWait()

    await user.click(screen.getByRole("button", { name: "Edit prompt" }))
    await user.click(screen.getByRole("button", { name: /Reset to default/ }))
    await user.click(screen.getByRole("button", { name: "Save" }))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith("/config/system-prompts", {
        method: "PUT",
        body: JSON.stringify({ overrides: { extraction: "" } }),
      }),
    )
  })

  it("refuses to save an unchanged draft", async () => {
    vi.mocked(apiFetch).mockResolvedValue(payload())
    const user = await openAndWait()

    await user.click(screen.getByRole("button", { name: "Edit prompt" }))
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled()
  })

  // Mirrors the cap PUT /config/system-prompts enforces, so an over-long
  // prompt is refused where it is typed rather than after a round-trip.
  it("refuses to save a prompt past the 20,000-character cap", async () => {
    vi.mocked(apiFetch).mockResolvedValue(payload())
    const user = await openAndWait()

    await user.click(screen.getByRole("button", { name: "Edit prompt" }))
    const field = screen.getByRole("textbox", {
      name: "extraction system prompt",
    })
    await user.clear(field)
    // Pasted rather than typed: 20k keystrokes would take minutes.
    await user.click(field)
    await user.paste("x".repeat(20_001))

    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled()
  })

  it("reports a failed load as an error, never as an empty prompt", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    render(
      <SystemPromptDialog
        open
        onOpenChange={() => {}}
        promptKey="extraction"
        title="extraction system prompt"
        description="Sent on every extraction call."
      />,
      { wrapper },
    )

    await waitFor(() =>
      expect(screen.getByText("Couldn't load the prompt")).toBeInTheDocument(),
    )
  })

  it("names the empty case as empty rather than rendering a blank pane", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      defaults: { extraction: "" },
      overrides: {},
      effective: { extraction: "" },
    })
    renderDialog()

    await waitFor(() =>
      expect(screen.getByText("No prompt is configured")).toBeInTheDocument(),
    )
  })
})

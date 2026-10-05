import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/hooks/api", () => ({
  useProjects: () => ({ data: [], isLoading: false, isSuccess: true }),
}))
vi.mock("../minimal-theme-switcher", () => ({
  MinimalThemeSwitcher: () => <button type="button">Theme</button>,
}))
vi.mock("@/components/darkmem", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/darkmem")>()),
  DetailLevelToggle: () => <div>detail-level</div>,
}))

import { HeaderControls } from "../header-controls"
import { useProjectStore } from "@/stores/project-store"

const realMatchMedia = window.matchMedia

function setWide(wide: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: wide,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))
}

function wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      {children}
    </QueryClientProvider>
  )
}

beforeEach(() => {
  useProjectStore.setState({ activeProject: null, missingProject: null })
})
afterEach(() => {
  window.matchMedia = realMatchMedia
})

describe("HeaderControls", () => {
  it("renders every control inline from md up", () => {
    setWide(true)
    render(<HeaderControls />, { wrapper })
    expect(
      screen.getByRole("button", { name: "Project scope" }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: "Session context" }),
    ).toBeInTheDocument()
    expect(screen.getByText("detail-level")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Theme" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "View options" })).toBeNull()
  })

  it("collapses the controls into one overflow popover below md", async () => {
    setWide(false)
    const user = userEvent.setup()
    render(<HeaderControls />, { wrapper })
    expect(screen.queryByRole("button", { name: "Project scope" })).toBeNull()

    await user.click(screen.getByRole("button", { name: "View options" }))
    expect(
      await screen.findByRole("button", { name: "Project scope" }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: "Session context" }),
    ).toBeInTheDocument()
    expect(screen.getByText("detail-level")).toBeInTheDocument()
  })

  it("keeps the overflow open while a control's own popover is used", async () => {
    setWide(false)
    const user = userEvent.setup()
    render(<HeaderControls />, { wrapper })
    await user.click(screen.getByRole("button", { name: "View options" }))
    await user.click(
      await screen.findByRole("button", { name: "Project scope" }),
    )
    await user.click(
      await screen.findByRole("button", { name: /^All projects/ }),
    )
    expect(
      screen.getByRole("button", { name: "Session context" }),
    ).toBeInTheDocument()
  })

  it("captions each control in the overflow popover", async () => {
    setWide(false)
    const user = userEvent.setup()
    render(<HeaderControls />, { wrapper })
    await user.click(screen.getByRole("button", { name: "View options" }))
    await screen.findByRole("button", { name: "Project scope" })
    for (const caption of ["Project", "Context", "Theme"]) {
      expect(
        screen.getByText(caption, { selector: "span" }),
      ).toBeInTheDocument()
    }
  })

  it("offers a palette button below md, where the rail's search is hidden", async () => {
    // Narrow for the wide query, matching for the rail-hidden one.
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query.includes("max-width"),
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))
    const user = userEvent.setup()
    const seen: KeyboardEvent[] = []
    const listener = (event: KeyboardEvent) => seen.push(event)
    window.addEventListener("keydown", listener)
    render(<HeaderControls />, { wrapper })
    await user.click(screen.getByRole("button", { name: "Go to page" }))
    window.removeEventListener("keydown", listener)
    expect(seen.some((e) => e.key === "k" && e.ctrlKey)).toBe(true)
  })

  it("passes the code-page reason to the switcher", () => {
    setWide(true)
    render(
      <HeaderControls projectDisabledReason="Code is scoped by repository, not by project" />,
      { wrapper },
    )
    expect(screen.getByRole("button", { name: "Project scope" })).toBeDisabled()
  })
})

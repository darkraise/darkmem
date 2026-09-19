import { render, screen } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import { DemoNotes } from "../demo-notes"

afterEach(() => vi.unstubAllGlobals())

it("shows the sample page read-only and makes no request", async () => {
  const fetchSpy = vi.fn()
  vi.stubGlobal("fetch", fetchSpy)
  const { container } = render(<DemoNotes />)
  expect(screen.getByRole("heading", { name: "Welcome to notes" })).toBeInTheDocument()
  // The editor is lazy-loaded; a cold import outlasts the 1s default wait.
  expect((await screen.findAllByText("Draft the release notes", {}, { timeout: 10_000 })).length).toBeGreaterThan(0)
  expect(container.querySelector('[contenteditable="true"]')).toBeNull()
  expect(fetchSpy).not.toHaveBeenCalled()
})

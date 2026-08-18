import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { EmptyState } from "../empty-state"

describe("EmptyState", () => {
  it("renders the title and description it is given", () => {
    render(
      <EmptyState
        kind="empty"
        title="No memories yet"
        description="Capture one."
      />,
    )
    expect(screen.getByText("No memories yet")).toBeInTheDocument()
    expect(screen.getByText("Capture one.")).toBeInTheDocument()
  })

  // The whole point of the redesign: the kind picks the icon and the colour,
  // so a caller cannot give two surfaces different marks for the same event.
  it.each([
    ["empty", "text-muted-foreground"],
    ["filtered", "text-info"],
    ["missing", "text-warning"],
    ["failed", "text-destructive"],
    ["resolved", "text-success"],
  ] as const)("paints %s with the %s token", (kind, token) => {
    const { container } = render(<EmptyState kind={kind} title="t" />)
    const tone = container.querySelector(".dr-empty-state-icon > span")
    expect(tone?.className).toContain(token)
  })

  it("gives each kind its own icon", () => {
    const marks = new Set<string>()
    for (const kind of [
      "empty",
      "filtered",
      "missing",
      "failed",
      "resolved",
    ] as const) {
      const { container, unmount } = render(
        <EmptyState kind={kind} title="t" />,
      )
      marks.add(
        container.querySelector(".dr-empty-state-icon svg")?.innerHTML ?? kind,
      )
      unmount()
    }
    expect(marks.size, "two kinds share an icon").toBe(5)
  })

  // Page scope centres in the content area; panel scope sits at natural
  // height inside the card that already owns the section's boundary.
  it("reserves height at page scope and not at panel scope", () => {
    const { container: page } = render(
      <EmptyState kind="empty" title="t" scope="page" />,
    )
    expect(page.firstElementChild?.className).toMatch(/min-h-/)

    const { container: panel } = render(<EmptyState kind="empty" title="t" />)
    expect(panel.firstElementChild?.className).not.toMatch(/min-h-/)
  })

  it("renders an action only when one is given", () => {
    const { rerender } = render(<EmptyState kind="failed" title="t" />)
    expect(screen.queryByRole("button")).not.toBeInTheDocument()
    rerender(
      <EmptyState kind="failed" title="t" action={<button>Retry</button>} />,
    )
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument()
  })
})

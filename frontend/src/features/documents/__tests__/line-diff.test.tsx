import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { LineDiff } from "../components/line-diff"

function lines(container: HTMLElement, change: string): string[] {
  return [...container.querySelectorAll(`[data-change="${change}"]`)].map(
    (row) => row.querySelector("[data-line]")?.textContent ?? "",
  )
}

describe("LineDiff", () => {
  it("marks removed, added and unchanged lines", () => {
    const { container } = render(<LineDiff before={"a\nb\nc\n"} after={"a\nB\nc\nd\n"} />)
    expect(lines(container, "removed")).toEqual(["b"])
    expect(lines(container, "added")).toEqual(["B", "d"])
    expect(lines(container, "same")).toEqual(["a", "c"])
  })

  it("keeps a blank line as a line", () => {
    const { container } = render(<LineDiff before={"a\n\nb\n"} after={"a\nb\n"} />)
    expect(lines(container, "removed")).toEqual([""])
  })

  it("says so when the two sides are identical", () => {
    render(<LineDiff before={"same\n"} after={"same\n"} />)
    expect(screen.getByText("The two revisions are identical.")).toBeInTheDocument()
  })
})

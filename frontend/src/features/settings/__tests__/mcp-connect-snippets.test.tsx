import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { McpConnectSnippets } from "../components/mcp-connect-snippets"

describe("McpConnectSnippets", () => {
  it("gives the copy button its own column instead of laying it over the code", () => {
    render(<McpConnectSnippets />)
    const snippet = screen.getAllByTestId("snippet")[0]!
    const copy = screen.getAllByRole("button", { name: "Copy snippet" })[0]!
    const pre = snippet.querySelector("pre")!
    // The button is not inside the scrolling code, and nothing positions it
    // on top of it.
    expect(pre.contains(copy)).toBe(false)
    expect(snippet.className).toContain("flex")
    expect(snippet.querySelector(".absolute")).toBeNull()
    expect(pre.className).toContain("min-w-0")
  })
})

import { fireEvent, render, screen } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, it, expect, vi } from "vitest"

vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({
    children,
    to,
    search,
    ...rest
  }: {
    children?: ReactNode
    to: string
    search?: { q?: string }
  }) => (
    <a href={`${to}?q=${encodeURIComponent(search?.q ?? "")}`} {...rest}>
      {children}
    </a>
  ),
}))
import { AppPageHeader } from "@/components/app-chrome"
import { useProjectStore } from "@/stores/project-store"
import { MemoryGraphExplorer } from "../components/memory-graph-explorer"

describe("MemoryGraphExplorer", () => {
  beforeEach(() => {
    useProjectStore.setState({ activeProject: "darkmem", missingProject: null })
  })

  it("renders the project-scoped entity graph with topics", () => {
    render(<MemoryGraphExplorer />)
    expect(
      screen.getByRole("group", { name: /Entity graph for project darkmem/ }),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/12 entities · 14 relations · 3 topics/),
    ).toBeInTheDocument()
    expect(screen.getByText("Community navigator")).toBeInTheDocument()
    expect(screen.getByText("Retrieval & ranking")).toBeInTheDocument()
  })

  it("click-to-inspect shows the entity's relations", () => {
    render(<MemoryGraphExplorer />)
    fireEvent.click(screen.getByRole("button", { name: "postgres (database)" }))
    expect(screen.getByText(/relations \(2\)/)).toBeInTheDocument()
  })

  it("lets the inspector deselect, clear on Escape and search memories", () => {
    render(<MemoryGraphExplorer />)
    fireEvent.click(screen.getByRole("button", { name: "postgres (database)" }))
    expect(
      screen.getByRole("link", { name: /Search memories mentioning postgres/ }),
    ).toHaveAttribute("href", "/memories?q=postgres")
    fireEvent.click(screen.getByRole("button", { name: "Deselect entity" }))
    expect(screen.queryByText(/relations \(2\)/)).toBeNull()

    fireEvent.click(screen.getByRole("button", { name: "postgres (database)" }))
    fireEvent.keyDown(document.body, { key: "Escape" })
    expect(screen.queryByText(/relations \(2\)/)).toBeNull()
  })

  it("spells out relation direction in the inspector", () => {
    render(<MemoryGraphExplorer />)
    fireEvent.click(screen.getByRole("button", { name: "postgres (database)" }))
    const relations = screen.getAllByRole("button", { name: /; inspect / })
    expect(relations.length).toBe(2)
    for (const rel of relations) {
      expect(rel.textContent).toMatch(/this/)
      expect(rel.textContent).toMatch(/→ [A-Z_]+ →/)
    }
  })

  it("dims non-matches while searching and reports a zero-match query", () => {
    render(<MemoryGraphExplorer />)
    const search = screen.getByRole("textbox", { name: "Search entities" })
    fireEvent.change(search, { target: { value: "postgres" } })
    const match = screen.getByRole("button", { name: "postgres (database)" })
    expect(match.style.opacity).toBe("1")
    const other = screen
      .getAllByRole("button")
      .find(
        (b) =>
          b.tagName.toLowerCase() === "g" &&
          !b.getAttribute("aria-label")?.startsWith("postgres"),
      )!
    expect(other.style.opacity).toBe("0.25")

    fireEvent.change(search, { target: { value: "zzzzqq" } })
    expect(screen.getByRole("status")).toHaveTextContent(
      /No entity matches .zzzzqq./,
    )
  })

  it("offers zoom controls", () => {
    render(<MemoryGraphExplorer />)
    const svg = screen.getByRole("group", { name: /Entity graph/ })
    const before = svg.getAttribute("viewBox")
    fireEvent.click(screen.getByRole("button", { name: "Zoom in" }))
    expect(svg.getAttribute("viewBox")).not.toBe(before)
    fireEvent.click(screen.getByRole("button", { name: "Fit graph" }))
    expect(svg.getAttribute("viewBox")).toBe(before)
  })

  it("reads the header scope and offers no project select", () => {
    render(<MemoryGraphExplorer />)
    expect(screen.queryByRole("combobox", { name: "Project scope" })).toBeNull()
  })

  it("shows a hidden label while its node has focus", () => {
    // Every project at once, in the Community layout: the fixture overlaps
    // labels in that layout only (Force and Tree place all sixteen clear).
    useProjectStore.setState({ activeProject: null, missingProject: null })
    render(<MemoryGraphExplorer />)
    fireEvent.click(screen.getByRole("radio", { name: /Community/ }))
    const nodes = screen
      .getAllByRole("button")
      .filter((b) => b.tagName.toLowerCase() === "g")
    const hidden = nodes.find((n) => n.querySelector("text") === null)
    expect(
      hidden,
      "the fixture places at least one overlapping label",
    ).toBeDefined()
    fireEvent.focus(hidden!)
    expect(hidden!.querySelector("text")).not.toBeNull()
    fireEvent.blur(hidden!)
    expect(hidden!.querySelector("text")).toBeNull()
  })

  it("is not an image around its node buttons", () => {
    render(<MemoryGraphExplorer />)
    expect(screen.queryByRole("img")).toBeNull()
  })

  it("shows a theme-coloured ring on the node that has keyboard focus", () => {
    render(<MemoryGraphExplorer />)
    const node = screen.getByRole("button", { name: "postgres (database)" })
    expect(node.getAttribute("class")).not.toMatch(/(^|\s)outline-none(\s|$)/)
    const ring = node.querySelector("[data-focus-ring]")!
    expect(ring.getAttribute("class")).toMatch(/stroke-ring/)
    expect(ring.getAttribute("class")).toMatch(
      /group-focus-visible:opacity-100/,
    )
  })

  it("publishes the page chrome the real page does", () => {
    render(
      <>
        <MemoryGraphExplorer />
        <AppPageHeader />
      </>,
    )
    expect(
      screen.getByRole("heading", { name: "Memory Graph" }),
    ).toBeInTheDocument()
  })
})

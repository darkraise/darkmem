import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { CodeCanvas } from "../components/code-canvas"

const GRAPH = {
  repo_id: "r1",
  nodes: [
    { id: "a", name: "main.py", kind: "file" as const, file: "main.py", community: "c1" },
    { id: "b", name: "run", kind: "function" as const, file: "main.py", community: "c1" },
  ],
  edges: [{ source: "a", target: "b", type: "CONTAINS" }],
  communities: [{ id: "c1", label: "core", chart: 1 as const }],
  processes: [],
}

describe("CodeCanvas", () => {
  it("is a named group of node buttons, not an image, and not itself focusable", () => {
    render(
      <CodeCanvas
        graph={GRAPH}
        layout="force"
        colorBy="kind"
        selectedId={null}
        onSelect={vi.fn()}
        visibleIds={null}
        blastIds={null}
        highlightCommunity={null}
        processIds={null}
        playing={false}
        zoom={1}
        center={null}
      />,
    )
    const canvas = screen.getByRole("group", { name: /^Code graph — 2 nodes, 1 edges/ })
    expect(canvas).not.toHaveAttribute("tabindex")
    expect(screen.queryByRole("img")).toBeNull()
    expect(screen.getByRole("button", { name: "run (function)" })).toBeInTheDocument()
  })

  it("shows a theme-coloured ring on the node that has keyboard focus", () => {
    render(
      <CodeCanvas
        graph={GRAPH}
        layout="force"
        colorBy="kind"
        selectedId={null}
        onSelect={vi.fn()}
        visibleIds={null}
        blastIds={null}
        highlightCommunity={null}
        processIds={null}
        playing={false}
        zoom={1}
        center={null}
      />,
    )
    const node = screen.getByRole("button", { name: "run (function)" })
    expect(node.getAttribute("class")).not.toMatch(/(^|\s)outline-none(\s|$)/)
    const ring = node.querySelector('[data-focus-ring]')!
    expect(ring.getAttribute("class")).toMatch(/stroke-ring/)
    expect(ring.getAttribute("class")).toMatch(/group-focus-visible:opacity-100/)
  })

  it("draws a folded file edge thicker the more symbol edges it carries", () => {
    const files = {
      repo_id: "r1",
      nodes: ["a.py", "b.py", "c.py"].map((id) => ({
        id,
        name: id,
        kind: "file" as const,
        file: id,
        community: "",
      })),
      edges: [
        { source: "a.py", target: "b.py", type: "depends_on", weight: 64 },
        { source: "a.py", target: "c.py", type: "depends_on", weight: 1 },
      ],
      communities: [],
      processes: [],
    }
    const { container } = render(
      <CodeCanvas
        graph={files}
        layout="force"
        colorBy="kind"
        selectedId={null}
        onSelect={vi.fn()}
        visibleIds={null}
        blastIds={null}
        highlightCommunity={null}
        processIds={null}
        playing={false}
        zoom={1}
        center={null}
      />,
    )
    const widths = [...container.querySelectorAll("line")].map((l) =>
      Number(l.getAttribute("stroke-width")),
    )
    expect(widths).toEqual([4, 1])
  })
})

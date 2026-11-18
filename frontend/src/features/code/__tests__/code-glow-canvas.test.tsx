import { describe, it, expect, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"

// sigma's programs read WebGL enums off the global constructors at module
// load; happy-dom ships neither. Real GL constant values. Hoisted, because
// the imports below are hoisted above any plain statement.
vi.hoisted(() => {
  const GL = { FLOAT: 0x1406, UNSIGNED_BYTE: 0x1401, TRIANGLES: 0x0004 }
  Object.assign(globalThis, { WebGLRenderingContext: GL, WebGL2RenderingContext: GL })
})

vi.mock("sigma", () => ({
  default: class {
    constructor() {
      throw new Error("WebGL unavailable")
    }
  },
}))
vi.mock("graphology-layout-forceatlas2/worker", () => ({
  default: class {
    start() {}
    stop() {}
    kill() {}
    isRunning() {
      return false
    }
  },
}))

import {
  edgeSize,
  canvasKeyAction,
  codeNodeColor,
  CodeGlowCanvas,
  drawnGraph,
  isDimmed,
  KIND_CHART,
  showsLabel,
} from "../components/code-glow-canvas"

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

const renderCanvas = (onSelect = vi.fn(), hiddenKinds?: ReadonlySet<"file">) =>
  render(
    <CodeGlowCanvas
      graph={GRAPH}
      colorBy="kind"
      selectedId="b"
      onSelect={onSelect}
      visibleIds={null}
      hiddenKinds={hiddenKinds}
      blastIds={null}
      highlightCommunity={null}
      processIds={null}
    />,
  )

describe("canvasKeyAction", () => {
  it.each([
    ["+", { type: "zoom", factor: 1.25 }],
    ["=", { type: "zoom", factor: 1.25 }],
    ["-", { type: "zoom", factor: 0.8 }],
    ["ArrowLeft", { type: "pan", dx: -1, dy: 0 }],
    ["ArrowRight", { type: "pan", dx: 1, dy: 0 }],
    ["ArrowUp", { type: "pan", dx: 0, dy: -1 }],
    ["ArrowDown", { type: "pan", dx: 0, dy: 1 }],
    ["0", { type: "fit" }],
    ["Escape", { type: "clear" }],
    ["a", null],
    ["Tab", null],
  ])("%s → %o", (key, action) => {
    expect(canvasKeyAction(key)).toEqual(action)
  })
})

describe("drawnGraph", () => {
  it("drops hidden kinds and every edge touching them", () => {
    const d = drawnGraph(GRAPH, new Set(["file"]))
    expect(d.nodes.map((n) => n.id)).toEqual(["b"])
    expect(d.edges).toHaveLength(0)
  })

  it("keeps everything when nothing is hidden", () => {
    const d = drawnGraph(GRAPH)
    expect(d.nodes).toHaveLength(2)
    expect(d.edges).toHaveLength(1)
  })
})

describe("codeNodeColor", () => {
  const chart = ["#111111", "#222222", "#333333", "#444444", "#555555"]

  it("colours by community through its chart slot", () => {
    expect(codeNodeColor(GRAPH.nodes[1]!, "community", GRAPH.communities, chart)).toBe("#111111")
  })

  it("colours by kind through the kind tiers", () => {
    expect(KIND_CHART.file).not.toBe(KIND_CHART.function)
    expect(codeNodeColor(GRAPH.nodes[0]!, "kind", GRAPH.communities, chart)).toBe(chart[KIND_CHART.file - 1])
    expect(codeNodeColor(GRAPH.nodes[1]!, "kind", GRAPH.communities, chart)).toBe(chart[KIND_CHART.function - 1])
  })
})

describe("isDimmed", () => {
  it.each([
    [null, null, false],
    [new Set(["b"]), null, true],
    [new Set(["a"]), null, false],
    [null, "c2", true],
    [null, "c1", false],
  ])("visible %o, community %s → %s", (visible, community, dimmed) => {
    expect(isDimmed(GRAPH.nodes[0]!, visible, community)).toBe(dimmed)
  })
})

describe("edgeSize", () => {
  it("draws a folded file edge thicker the more symbol edges it carries", () => {
    expect(edgeSize(undefined)).toBe(1)
    expect(edgeSize(1)).toBe(1)
    expect(edgeSize(4)).toBe(2)
    expect(edgeSize(64)).toBe(4)
    expect(edgeSize(4096)).toBe(4)
  })
})

describe("showsLabel", () => {
  const base = { selected: false, blast: false, process: false, degree: 0, cameraRatio: 1 }
  it.each([
    [{}, false],
    [{ selected: true }, true],
    [{ blast: true }, true],
    [{ process: true }, true],
    [{ degree: 5 }, false],
    [{ degree: 5, cameraRatio: 0.5 }, true],
    [{ degree: 4, cameraRatio: 0.5 }, false],
  ])("%o → %s", (over, shown) => {
    expect(showsLabel({ ...base, ...over })).toBe(shown)
  })
})

describe("CodeGlowCanvas", () => {
  it("is one named, focusable stop", () => {
    renderCanvas()
    const canvas = screen.getByRole("group", { name: "Code graph — 2 nodes, 1 edges" })
    expect(canvas.tabIndex).toBe(0)
    expect(screen.queryAllByRole("button")).toHaveLength(0)
  })

  it("counts only what it draws", () => {
    renderCanvas(vi.fn(), new Set(["file"]))
    expect(screen.getByRole("group", { name: "Code graph — 1 nodes, 0 edges" })).toBeInTheDocument()
  })

  it("says so when the browser has no WebGL", () => {
    renderCanvas()
    expect(
      screen.getByText("The graph needs WebGL, which this browser has turned off."),
    ).toBeInTheDocument()
  })

  it("clears the selection on Escape", () => {
    const onSelect = vi.fn()
    renderCanvas(onSelect)
    fireEvent.keyDown(screen.getByRole("group", { name: /^Code graph/ }), { key: "Escape" })
    expect(onSelect).toHaveBeenCalledWith(null)
  })
})

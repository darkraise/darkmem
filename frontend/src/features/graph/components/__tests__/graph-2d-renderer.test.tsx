import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { useMemo } from "react"

// sigma's programs read WebGL enums off the global constructors at module
// load; happy-dom ships neither. Real GL constant values.
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
const motion = vi.hoisted(() => ({ start: vi.fn(() => vi.fn()) }))
vi.mock("@/features/graph/lib/ambient-motion", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/graph/lib/ambient-motion")>()),
  startAmbientMotion: motion.start,
}))

import { Graph2DRenderer } from "../graph-2d-renderer"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
import { syntheticMemoryGraph } from "@/features/graph/lib/synthetic-graph"

const noopSelect = (_id: string | null) => {}

function Harness({ onReady }: { onReady: () => void }) {
  const { tokens, palette } = useMemoryGraphTheme()
  const graph = useMemo(() => syntheticMemoryGraph(30, 3, 2), [])
  return (
    <div style={{ position: "relative", width: 800, height: 600 }}>
      <Graph2DRenderer
        filteredMemories={graph.memories}
        filteredEdges={graph.edges}
        selectedNodeId={null}
        onNodeSelect={noopSelect}
        onReady={onReady}
        sizeMode="connections"
        colorMode="cluster"
        hullMode="none"
        entityLayerEnabled={false}
        entities={[]}
        entityRelations={[]}
        tokens={tokens}
        palette={palette}
        clusterNames={graph.clusterNames}
      />
    </div>
  )
}

describe("Graph2DRenderer without WebGL", () => {
  it("says so, still reports ready, and starts no motion", async () => {
    // The global setup records rAF calls without running them; the build is
    // deferred to one, and on this path nothing else schedules a frame.
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb: FrameRequestCallback) => {
      cb(0)
      return 1
    })
    const onReady = vi.fn()
    render(<Harness onReady={onReady} />)
    expect(
      await screen.findByText("The graph needs WebGL, which this browser has turned off."),
    ).toBeInTheDocument()
    expect(onReady).toHaveBeenCalled()
    expect(motion.start).not.toHaveBeenCalled()
  })
})

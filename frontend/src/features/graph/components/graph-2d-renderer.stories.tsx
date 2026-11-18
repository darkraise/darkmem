import type { Meta, StoryObj } from "@storybook/react"
import { useMemo } from "react"
import { Graph2DRenderer } from "./graph-2d-renderer"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
import { syntheticMemoryGraph } from "@/features/graph/lib/synthetic-graph"

// Stable identities: the renderer rebuilds its whole graph when a callback
// prop changes, which would restart the layout being measured.
const markReady = () => performance.mark("graph-ready")
const noopSelect = (_id: string | null) => {}

function ScaleHarness({ nodes }: { nodes: number }) {
  const { tokens, palette } = useMemoryGraphTheme()
  // Six draws per node give about 110,000 distinct edges at 20,000 nodes,
  // above the 100,000 the scale measurement is specified at.
  const graph = useMemo(() => syntheticMemoryGraph(nodes, 60, 6), [nodes])
  return (
    <div
      data-testid="scale-harness"
      style={{ position: "relative", width: "100vw", height: "100vh" }}
    >
      <Graph2DRenderer
        filteredMemories={graph.memories}
        filteredEdges={graph.edges}
        selectedNodeId={null}
        onNodeSelect={noopSelect}
        onReady={markReady}
        sizeMode="connections"
        colorMode="cluster"
        hullMode="cluster"
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

const meta: Meta<typeof ScaleHarness> = {
  title: "Graph/Graph2DRenderer",
  component: ScaleHarness,
  parameters: { layout: "fullscreen" },
}
export default meta

type S = StoryObj<typeof ScaleHarness>

export const Scale2k: S = { args: { nodes: 2000 } }
export const Scale20k: S = { args: { nodes: 20000 } }

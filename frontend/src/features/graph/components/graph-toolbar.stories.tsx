import type { Meta, StoryObj } from "@storybook/react"
import { useState } from "react"
import { GraphToolbar } from "./graph-toolbar"
import type { ColorMode } from "@/features/graph/lib/graph-colors"
import type { HullMode } from "@/features/graph/lib/graph-geometry"
import type { SizeMode } from "@/features/graph/lib/graph-utils"

const meta: Meta<typeof GraphToolbar> = {
  title: "Graph/GraphToolbar",
  component: GraphToolbar,
  parameters: { layout: "fullscreen" },
  decorators: [
    (Story) => (
      <div className="bg-background relative h-[200px]">
        <Story />
      </div>
    ),
  ],
}
export default meta

type S = StoryObj<typeof GraphToolbar>

const defaultArgs = {
  viewMode: "2d" as const,
  onViewModeChange: () => {},
  colorMode: "type" as ColorMode,
  onColorModeChange: () => {},
  hullMode: "cluster" as HullMode,
  onHullModeChange: () => {},
  entityLayer: true,
  sharedEntitiesOnly: true,
  onSharedEntitiesOnlyChange: () => {},
  onEntityLayerChange: () => {},
  sizeMode: "connections" as SizeMode,
  onSizeModeChange: () => {},
  similarityThreshold: 0.65,
  onSimilarityChange: () => {},
  minClusterSize: 3,
  onMinClusterSizeChange: () => {},
  spacing: 200,
  onSpacingChange: () => {},
  clusterTightness: 120,
  onClusterTightnessChange: () => {},
  onReset: () => {},
}

export const Default: S = {
  args: defaultArgs,
}

export const View3D: S = {
  args: {
    ...defaultArgs,
    viewMode: "3d",
    spacing: 80,
  },
}

export const TagColor: S = {
  args: {
    ...defaultArgs,
    colorMode: "tag",
    hullMode: "tag",
  },
}

// A real component rather than hooks inside `render`: Storybook calls that
// function like a component, but it is not one, so the hooks rules cannot see
// it and neither can React's own dev warnings. Extracting it costs nothing and
// makes the story obey the same rules the app does.
function InteractiveToolbar() {
  const [viewMode, setViewMode] = useState<"2d" | "3d">("2d")
  const [colorMode, setColorMode] = useState<ColorMode>("type")
  const [hullMode, setHullMode] = useState<HullMode>("cluster")
  const [entityLayer, setEntityLayer] = useState(true)
  const [sharedOnly, setSharedOnly] = useState(true)
  const [sizeMode, setSizeMode] = useState<SizeMode>("connections")
  const [threshold, setThreshold] = useState(0.65)
  const [minCluster, setMinCluster] = useState(3)
  const [spacing, setSpacing] = useState(200)
  const [tightness, setTightness] = useState(120)

  return (
    <div className="bg-background relative h-[300px]">
      <GraphToolbar
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        colorMode={colorMode}
        onColorModeChange={setColorMode}
        hullMode={hullMode}
        onHullModeChange={setHullMode}
        entityLayer={entityLayer}
        sharedEntitiesOnly={sharedOnly}
        onSharedEntitiesOnlyChange={setSharedOnly}
        onEntityLayerChange={setEntityLayer}
        sizeMode={sizeMode}
        onSizeModeChange={setSizeMode}
        similarityThreshold={threshold}
        onSimilarityChange={setThreshold}
        minClusterSize={minCluster}
        onMinClusterSizeChange={setMinCluster}
        spacing={spacing}
        onSpacingChange={setSpacing}
        clusterTightness={tightness}
        onClusterTightnessChange={setTightness}
        onReset={() => {
          setViewMode("2d")
          setColorMode("type")
          setHullMode("cluster")
          setEntityLayer(true)
          setSizeMode("connections")
          setThreshold(0.65)
          setMinCluster(3)
          setSpacing(200)
          setTightness(120)
        }}
    />
  </div>
  )
}

export const Interactive: S = {
  render: () => <InteractiveToolbar />,
}

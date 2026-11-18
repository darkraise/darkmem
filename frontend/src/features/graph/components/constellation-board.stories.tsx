import type { Decorator, Meta, StoryObj } from "@storybook/react"
import { useEffect, useMemo, useState, type ReactNode } from "react"
import { Graph2DRenderer } from "./graph-2d-renderer"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
import {
  syntheticMemoryGraph,
  syntheticShape,
  type SyntheticGraph,
  type SyntheticShape,
} from "@/features/graph/lib/synthetic-graph"
import type { EntityRelation, GraphEntity } from "@/hooks/api"

// Stable identities: the renderer rebuilds its whole graph when a callback
// prop changes.
const markReady = () => performance.mark("graph-ready")
const noopSelect = (_id: string | null) => {}

const WEBGL_CONTEXTS = new Set(["webgl", "webgl2", "experimental-webgl"])

/** Makes every WebGL context request fail while mounted, as on a browser with
 *  WebGL turned off. Patched during render: the canvas builds before a
 *  decorator's effect would run. */
function WebGLOff({ children }: { children: ReactNode }) {
  const [original] = useState(() => {
    const getContext = HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
      type: string,
      ...rest: unknown[]
    ) {
      if (WEBGL_CONTEXTS.has(type)) return null
      return (getContext as (...a: unknown[]) => unknown).call(this, type, ...rest)
    } as typeof getContext
    return getContext
  })
  useEffect(
    () => () => {
      HTMLCanvasElement.prototype.getContext = original
    },
    [original],
  )
  return children
}

const withoutWebGL: Decorator = (Story) => (
  <WebGLOff>
    <Story />
  </WebGLOff>
)

type GraphSource = { shape: SyntheticShape; n: number } | { scale: number }

function entitiesFor(graph: SyntheticGraph): { entities: GraphEntity[]; relations: EntityRelation[] } {
  const ids = graph.memories.map((m) => m.id)
  const entities: GraphEntity[] = Array.from({ length: 6 }, (_, i) => ({
    id: `e${i}`,
    name: `entity-${i}`,
    entity_type: i % 2 ? "tool" : "concept",
    properties: {},
    memory_ids: ids.filter((_, j) => j % 6 === i).slice(0, 8),
  }))
  const relations: EntityRelation[] = [
    { source: "e0", target: "e1", type: "USES", weight: 1 },
    { source: "e2", target: "e3", type: "RELATED_TO", weight: 1 },
  ]
  return { entities, relations }
}

function Board({
  source,
  selected = null,
  withEntities = false,
}: {
  source: GraphSource
  selected?: string | null
  withEntities?: boolean
}) {
  const { tokens, palette } = useMemoryGraphTheme()
  const graph = useMemo(
    () =>
      "scale" in source
        ? syntheticMemoryGraph(source.scale, 60, 6)
        : syntheticShape(source.shape, source.n),
    [source],
  )
  const overlay = useMemo(() => entitiesFor(graph), [graph])
  return (
    <div style={{ position: "relative", width: "100vw", height: "100vh" }}>
      <Graph2DRenderer
        filteredMemories={graph.memories}
        filteredEdges={graph.edges}
        selectedNodeId={selected}
        onNodeSelect={noopSelect}
        onReady={markReady}
        sizeMode="connections"
        colorMode="cluster"
        hullMode="none"
        entityLayerEnabled={withEntities}
        entities={withEntities ? overlay.entities : []}
        entityRelations={withEntities ? overlay.relations : []}
        tokens={tokens}
        palette={palette}
        clusterNames={graph.clusterNames}
      />
    </div>
  )
}

const meta: Meta<typeof Board> = {
  title: "Graph/Constellation/Memory",
  component: Board,
  parameters: { layout: "fullscreen" },
}
export default meta

type S = StoryObj<typeof Board>

const shape = (s: SyntheticShape, n = 300) => ({ shape: s, n })

export const OneComponent: S = { args: { source: shape("one-component") } }
export const AllOrphans: S = { args: { source: shape("all-orphans") } }
export const NoOrphans: S = { args: { source: shape("no-orphans") } }
export const ManySatellites: S = { args: { source: shape("many-satellites") } }
export const Mixed: S = { args: { source: shape("mixed") } }
export const OneNode: S = { args: { source: shape("all-orphans", 1) } }
// m0 opens the mixed shape's core component.
export const Selected: S = { args: { source: shape("mixed"), selected: "m0" } }
export const EntityLayer: S = { args: { source: shape("mixed"), withEntities: true } }
export const WebGLUnavailable: S = {
  args: { source: shape("mixed") },
  decorators: [withoutWebGL],
}
export const Scale20k: S = { args: { source: { scale: 20000 } } }

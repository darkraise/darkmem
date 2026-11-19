import type { Meta, StoryObj } from "@storybook/react"
import { useMemo } from "react"
import { Graph2DRenderer } from "./graph-2d-renderer"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
import { loadRealCorpus, type RealCorpusSize } from "@/features/graph/fixtures/real-corpus"
import { entityVisible } from "@/features/graph/hooks/use-graph-filters"

// Stable identities: the renderer rebuilds its whole graph when a callback
// prop changes.
const markReady = () => performance.mark("graph-ready")
const noopSelect = (_id: string | null) => {}

function highestDegree(edges: readonly { source: string; target: string }[]): string | null {
  const degree = new Map<string, number>()
  for (const e of edges) {
    degree.set(e.source, (degree.get(e.source) ?? 0) + 1)
    degree.set(e.target, (degree.get(e.target) ?? 0) + 1)
  }
  let best: string | null = null
  let bestDegree = -1
  for (const [id, d] of degree) {
    if (d > bestDegree || (d === bestDegree && best !== null && id < best)) {
      best = id
      bestDegree = d
    }
  }
  return best
}

function Board({
  size,
  minScore = 0,
  withEntities = false,
  sharedEntitiesOnly = true,
  selectTopHub = false,
  regions = false,
}: {
  size: RealCorpusSize
  minScore?: number
  withEntities?: boolean
  /** The page's default: only entities two or more drawn memories assert. */
  sharedEntitiesOnly?: boolean
  selectTopHub?: boolean
  regions?: boolean
}) {
  const { tokens, palette } = useMemoryGraphTheme()
  const corpus = useMemo(() => loadRealCorpus(size), [size])
  const edges = useMemo(
    () => corpus.edges.filter((e) => e.score >= minScore),
    [corpus, minScore],
  )
  const entities = useMemo(() => {
    if (!withEntities) return []
    const memoryIds = new Set(corpus.memories.map((m) => m.id))
    return corpus.entities.filter((e) => entityVisible(e, memoryIds, sharedEntitiesOnly))
  }, [corpus, withEntities, sharedEntitiesOnly])
  const entityRelations = useMemo(() => {
    const ids = new Set(entities.map((e) => e.id))
    return corpus.entityRelations.filter((r) => ids.has(r.source) && ids.has(r.target))
  }, [corpus, entities])
  const selected = useMemo(
    () => (selectTopHub ? highestDegree(corpus.edges) : null),
    [corpus, selectTopHub],
  )
  return (
    <div style={{ position: "relative", width: "100vw", height: "100vh" }}>
      <Graph2DRenderer
        filteredMemories={corpus.memories}
        filteredEdges={edges}
        selectedNodeId={selected}
        onNodeSelect={noopSelect}
        onReady={markReady}
        sizeMode="connections"
        colorMode="cluster"
        hullMode={regions ? "cluster" : "none"}
        entityLayerEnabled={withEntities}
        entities={entities}
        entityRelations={entityRelations}
        tokens={tokens}
        palette={palette}
        clusterNames={corpus.clusterNames}
      />
    </div>
  )
}

const meta: Meta<typeof Board> = {
  title: "Graph/Constellation/RealCorpus",
  component: Board,
  parameters: { layout: "fullscreen" },
}
export default meta

type S = StoryObj<typeof Board>

export const Default1000: S = { args: { size: 1000 } }
export const All: S = { args: { size: "all" } }
export const Small200: S = { args: { size: 200 } }
export const HighEdges: S = { args: { size: 1000, minScore: 0.8 } }
export const EntityLayer: S = { args: { size: 1000, withEntities: true } }
export const EntityLayerAll: S = { args: { size: 1000, withEntities: true, sharedEntitiesOnly: false } }
export const Selected: S = { args: { size: 1000, selectTopHub: true } }
export const Regions: S = { args: { size: 1000, regions: true } }

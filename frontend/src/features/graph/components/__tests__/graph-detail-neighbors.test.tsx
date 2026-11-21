import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { GraphDetailPanel } from "../graph-detail-panel"
import type { UnifiedMemory, SimilarityEdge } from "@/hooks/api"

function memory(over: Partial<UnifiedMemory> = {}): UnifiedMemory {
  return {
    id: "seed",
    content: "Import workflow: card to Lightroom, then the ZFS mirror.",
    source: "mcp",
    tags: [],
    memory_type: "procedural",
    importance: 0.5,
    cluster: 1,
    ...over,
  }
}

const SEED = memory()
const NEAR = memory({ id: "near", content: "Shooting on a Sony A7 IV." })
const FAR = memory({ id: "far", content: "The backup CLI uses Tokio." })

// The panel reads the whole memory for a cut node, through a query.
function QueryWrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
}

function renderPanel(
  edges: SimilarityEdge[],
  over: {
    memories?: UnifiedMemory[]
    children?: React.ReactNode
    onNavigateToMemory?: (id: string) => void
  } = {},
) {
  return render(
    <GraphDetailPanel
      selectedMemory={SEED}
      clusterName="Photography"
      memories={over.memories ?? [SEED, NEAR, FAR]}
      clusterNames={{}}
      visibleEdges={edges}
      onClose={() => {}}
      colorMode="cluster"
      onNavigateToMemory={over.onNavigateToMemory}
    >
      {over.children}
    </GraphDetailPanel>,
    { wrapper: QueryWrapper },
  )
}

describe("MemoryDetail neighbors", () => {
  // The panel reported only the entity-sharing neighbours while the canvas drew
  // cosine edges, so a memory with five spokes and one shared entity read as a
  // panel disagreeing with the graph. Both relations are now named.
  describe("similar memories", () => {
    it("lists every memory the canvas drew an edge to", () => {
      renderPanel([
        { source: "seed", target: "near", score: 0.64 },
        { source: "far", target: "seed", score: 0.5 },
      ])
      expect(screen.getByText(/Similar memories/)).toHaveTextContent("(2)")
      expect(screen.getByText(NEAR.content)).toBeInTheDocument()
      expect(screen.getByText(FAR.content)).toBeInTheDocument()
    })

    // Direction is an artifact of how the pair was enumerated, not a relation.
    it("finds a neighbor whichever endpoint the seed sits on", () => {
      renderPanel([{ source: "far", target: "seed", score: 0.5 }])
      expect(screen.getByText(FAR.content)).toBeInTheDocument()
    })

    it("orders by score, strongest first", () => {
      renderPanel([
        { source: "seed", target: "far", score: 0.5 },
        { source: "seed", target: "near", score: 0.64 },
      ])
      const shown = screen
        .getAllByText(/Sony A7 IV|uses Tokio/)
        .map((n) => n.textContent)
      expect(shown).toEqual([NEAR.content, FAR.content])
    })

    it("shows each neighbor's similarity", () => {
      renderPanel([{ source: "seed", target: "near", score: 0.638 }])
      expect(screen.getByText("0.64")).toBeInTheDocument()
    })

    it("ignores an edge between two other memories", () => {
      renderPanel([{ source: "near", target: "far", score: 0.9 }])
      expect(screen.getByText(/Similar memories/)).toHaveTextContent("(0)")
    })

    // A neighbor filtered off the canvas has no spoke on it either, so listing
    // it would put the panel back out of step with the graph.
    it("drops a neighbor that is not among the visible memories", () => {
      renderPanel([{ source: "seed", target: "hidden", score: 0.8 }], {
        memories: [SEED, NEAR],
      })
      expect(screen.getByText(/Similar memories/)).toHaveTextContent("(0)")
    })

    it("says so when no edge cleared the threshold", () => {
      renderPanel([])
      expect(
        screen.getByText(/No edge above the current similarity threshold/),
      ).toBeInTheDocument()
    })

    it("navigates to a neighbor when its row is clicked", async () => {
      const onNavigate = vi.fn()
      renderPanel([{ source: "seed", target: "near", score: 0.64 }], {
        onNavigateToMemory: onNavigate,
      })
      await userEvent.click(screen.getByText(NEAR.content))
      expect(onNavigate).toHaveBeenCalledWith("near")
    })
  })

  describe("entity context", () => {
    // Its neighbours are memories sharing an entity, scoped to one project —
    // a different relation. Beside a canvas carrying no entities at all, its
    // smaller count reads as the canvas being wrong.
    it("is absent when the page passes no entity child", () => {
      renderPanel([{ source: "seed", target: "near", score: 0.64 }])
      expect(screen.queryByText("Entity Context")).not.toBeInTheDocument()
    })

    it("names what its neighbors mean when it is shown", () => {
      renderPanel([], { children: <div>mini graph</div> })
      expect(screen.getByText("Entity Context")).toBeInTheDocument()
      expect(
        screen.getByText(/share an entity with this one/),
      ).toBeInTheDocument()
    })

    it("distinguishes itself from the canvas edges in words", () => {
      renderPanel([], { children: <div>mini graph</div> })
      expect(
        screen.getByText(/Linked by an edge on the canvas/),
      ).toBeInTheDocument()
    })
  })
})

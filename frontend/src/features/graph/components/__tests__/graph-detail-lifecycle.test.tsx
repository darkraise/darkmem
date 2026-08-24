import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { GraphDetailPanel } from "../graph-detail-panel"
import type { UnifiedMemory } from "@/hooks/api"

function memory(over: Partial<UnifiedMemory> = {}): UnifiedMemory {
  return {
    id: "m1",
    content: "Retrieval fuses the semantic and keyword arms under RRF at k=60.",
    source: "mcp",
    tags: [],
    memory_type: "architecture",
    importance: 0.5,
    cluster: 1,
    ...over,
  }
}

function renderPanel(m: UnifiedMemory) {
  return render(
    <GraphDetailPanel
      selectedMemory={m}
      clusterName="Retrieval & ranking"
      memories={[m]}
      clusterNames={{}}
      visibleEdges={[]}
      onClose={() => {}}
      colorMode="cluster"
    />,
  )
}

describe("GraphDetailPanel lifecycle", () => {
  // Lifecycle is deliberately absent from the canvas — a graph that fades and
  // dashes half its nodes stops being a picture of structure — so the panel is
  // the only place it is reported. Before this it was reported nowhere at all.
  it("names the status of the selected memory", () => {
    renderPanel(memory({ status: "active" }))
    expect(screen.getByText(/^active$/i)).toBeInTheDocument()
  })

  it("distinguishes a superseded memory from a live one", () => {
    renderPanel(memory({ status: "superseded" }))
    expect(screen.getByText(/^superseded$/i)).toBeInTheDocument()
  })

  // The graph payload is free text from an older row's perspective: a node
  // whose status never arrived must not render a blank chip claiming nothing.
  it("says nothing when the payload carried no status", () => {
    renderPanel(memory({ status: undefined }))
    expect(screen.queryByTestId("memory-status")).not.toBeInTheDocument()
  })
})

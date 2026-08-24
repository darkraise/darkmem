import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { GraphSummary } from "../graph-summary"
import type { UnifiedMemory, GraphEntity, EntityRelation } from "@/hooks/api"

function memory(over: Partial<UnifiedMemory> = {}): UnifiedMemory {
  return {
    id: "m1",
    content: "…",
    source: "mcp",
    tags: ["project/darkmem"],
    memory_type: "fact",
    importance: 0.5,
    cluster: 0,
    ...over,
  }
}

function entity(over: Partial<GraphEntity> = {}): GraphEntity {
  return {
    id: "e1",
    name: "postgres",
    entity_type: "database",
    properties: {},
    memory_ids: ["m1"],
    ...over,
  }
}

function renderSummary(over: {
  memories?: UnifiedMemory[]
  entities?: GraphEntity[]
  relations?: EntityRelation[]
} = {}) {
  return render(
    <GraphSummary
      memories={over.memories ?? [memory()]}
      edges={[]}
      entities={over.entities ?? []}
      entityRelations={over.relations ?? []}
      clusterNames={{ "0": "Retrieval & ranking" }}
      colorMode="cluster"
    />,
  )
}

describe("GraphSummary", () => {
  it("leads with the size of the visible graph", () => {
    renderSummary({ memories: [memory({ id: "a" }), memory({ id: "b" })] })
    expect(screen.getByTestId("graph-summary-memory-count")).toHaveTextContent(
      "2",
    )
    expect(screen.getByText("memories")).toBeInTheDocument()
  })

  it("names the largest cluster rather than only its id", () => {
    renderSummary()
    expect(screen.getByText(/Retrieval & ranking/)).toBeInTheDocument()
  })

  describe("lifecycle", () => {
    it("reports the split when the payload carried a status", () => {
      renderSummary({
        memories: [
          memory({ id: "a", status: "active" }),
          memory({ id: "b", status: "superseded" }),
        ],
      })
      const section = screen.getByTestId("graph-summary-lifecycle")
      expect(section).toHaveTextContent("active")
      expect(section).toHaveTextContent("superseded")
    })

    // Same rule the memory-detail chip follows: a graph of rows whose status
    // never arrived must report nothing, not a bar claiming it did.
    it("is absent when no memory carried a status", () => {
      renderSummary({ memories: [memory({ id: "a" })] })
      expect(
        screen.queryByTestId("graph-summary-lifecycle"),
      ).not.toBeInTheDocument()
    })
  })

  describe("breakdown drawers", () => {
    // The five census lists were the whole panel and ran unbounded. They stay
    // reachable, but the summary's own measures come first.
    it("keeps the facet rows collapsed until asked", () => {
      renderSummary({ memories: [memory({ source: "mcp" })] })
      expect(screen.getByText("Sources")).toBeInTheDocument()
      expect(screen.queryByText("mcp")).not.toBeInTheDocument()
    })

    it("offers a drawer per facet that has rows", () => {
      renderSummary({ entities: [entity()] })
      for (const label of [
        "Clusters",
        "Types",
        "Tag categories",
        "Sources",
        "Entity types",
      ]) {
        expect(screen.getByText(label)).toBeInTheDocument()
      }
    })

    it("omits a drawer for a facet with no rows", () => {
      renderSummary({ entities: [] })
      expect(screen.queryByText("Entity types")).not.toBeInTheDocument()
    })
  })

  describe("hub entities", () => {
    it("ranks the entities asserted by the most visible memories", () => {
      renderSummary({
        memories: [memory({ id: "a" }), memory({ id: "b" })],
        entities: [
          entity({ id: "e1", name: "postgres", memory_ids: ["a"] }),
          entity({ id: "e2", name: "fastapi", memory_ids: ["a", "b"] }),
        ],
      })
      const names = screen
        .getAllByText(/postgres|fastapi/)
        .map((n) => n.textContent)
      expect(names).toEqual(["fastapi", "postgres"])
    })

    // With the entity layer off the canvas carries no entity, so the panel
    // must not report a population that is not on it.
    it("is absent when no entity is on the canvas", () => {
      renderSummary({ entities: [] })
      expect(screen.queryByText("Top entities")).not.toBeInTheDocument()
    })
  })
})

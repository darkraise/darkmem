import { describe, it, expect } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { useGraphFilters } from "../use-graph-filters"
import type { UnifiedGraphData } from "@/hooks/api"

const memory = (id: string) => ({
  id,
  content: id,
  source: "api",
  tags: [] as string[],
  memory_type: "fact",
  importance: 0.5,
  cluster: -1,
})

const entity = (id: string, memory_ids: string[]) => ({
  id,
  name: id,
  entity_type: "tool",
  properties: {},
  memory_ids,
})

const DATA: UnifiedGraphData = {
  memories: [memory("m1"), memory("m2"), memory("m3")],
  clusters: {},
  cluster_names: {},
  similarity_edges: [],
  entities: [
    entity("lonely", ["m1"]),
    entity("bridge", ["m1", "m2"]),
    // Lists two memories, but only one is in the graph — so it bridges
    // nothing you can actually see.
    entity("half", ["m1", "gone"]),
  ],
  entity_relations: [
    { source: "lonely", target: "bridge", type: "USES", weight: 1 },
  ],
}

const render = () =>
  renderHook(() => useGraphFilters(DATA, true, new Set<string>()))

describe("shared-entities filter", () => {
  it("defaults to on, because most entities join nothing", () => {
    expect(render().result.current.sharedEntitiesOnly).toBe(true)
  })

  it("keeps only entities asserted by two or more visible memories", () => {
    expect(render().result.current.filteredEntities.map((e) => e.id)).toEqual([
      "bridge",
    ])
  })

  it("counts against the memories on screen, not the whole memory_ids", () => {
    expect(
      render().result.current.filteredEntities.map((e) => e.id),
    ).not.toContain("half")
  })

  it("shows every attached entity when switched off", () => {
    const { result } = render()
    act(() => result.current.setSharedEntitiesOnly(false))
    expect(result.current.filteredEntities.map((e) => e.id).sort()).toEqual([
      "bridge",
      "half",
      "lonely",
    ])
  })

  it("drops relations whose endpoint the filter removed", () => {
    const { result } = render()
    expect(result.current.filteredEntityRelations).toHaveLength(0)
    act(() => result.current.setSharedEntitiesOnly(false))
    expect(result.current.filteredEntityRelations).toHaveLength(1)
  })
})

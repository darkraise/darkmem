import { describe, it, expect } from "vitest"
import { deriveGraphSummary } from "../graph-summary-stats"
import type {
  UnifiedMemory,
  GraphEntity,
  EntityRelation,
  SimilarityEdge,
} from "@/hooks/api"

function memory(over: Partial<UnifiedMemory> = {}): UnifiedMemory {
  return {
    id: "m1",
    content: "…",
    source: "mcp",
    tags: [],
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
    memory_ids: [],
    ...over,
  }
}

function edge(source: string, target: string): SimilarityEdge {
  return { source, target, score: 0.8 }
}

function relation(type: string): EntityRelation {
  return { source: "e1", target: "e2", type, weight: 1 }
}

const empty = () => deriveGraphSummary([], [], [], [])

describe("deriveGraphSummary", () => {
  describe("an empty graph", () => {
    // The panel renders these straight into the DOM, so a NaN or an Infinity
    // here is a visible "NaN avg degree", not a caught error.
    it("reports no average degree rather than NaN", () => {
      expect(empty().averageDegree).toBeNull()
    })

    it("reports no mean importance rather than NaN", () => {
      expect(empty().meanImportance).toBeNull()
    })

    it("names no largest cluster", () => {
      expect(empty().largestCluster).toBeNull()
    })
  })

  describe("degree and isolation", () => {
    it("counts each edge twice across the two endpoints it joins", () => {
      const stats = deriveGraphSummary(
        [memory({ id: "a" }), memory({ id: "b" }), memory({ id: "c" })],
        [edge("a", "b"), edge("b", "c")],
        [],
        [],
      )
      expect(stats.edgeCount).toBe(2)
      expect(stats.averageDegree).toBeCloseTo(4 / 3)
    })

    it("counts a memory with no edge to another visible memory as isolated", () => {
      const stats = deriveGraphSummary(
        [memory({ id: "a" }), memory({ id: "b" }), memory({ id: "lonely" })],
        [edge("a", "b")],
        [],
        [],
      )
      expect(stats.isolatedCount).toBe(1)
    })

    // The caller passes a pre-filtered edge list today, but an edge reaching a
    // memory that is off the canvas must never make an on-screen node look
    // connected — that is the whole meaning of the number.
    it("ignores an edge whose other endpoint is not on screen", () => {
      const stats = deriveGraphSummary(
        [memory({ id: "a" })],
        [edge("a", "filtered-away")],
        [],
        [],
      )
      expect(stats.edgeCount).toBe(0)
      expect(stats.isolatedCount).toBe(1)
    })
  })

  describe("lifecycle", () => {
    it("splits the visible memories by status", () => {
      const stats = deriveGraphSummary(
        [
          memory({ id: "a", status: "active" }),
          memory({ id: "b", status: "active" }),
          memory({ id: "c", status: "superseded" }),
        ],
        [],
        [],
        [],
      )
      expect(stats.lifecycle).toEqual([
        { status: "active", count: 2 },
        { status: "superseded", count: 1 },
      ])
    })

    it("orders the rungs by lifecycle, not by count", () => {
      const stats = deriveGraphSummary(
        [
          memory({ id: "a", status: "deprecated" }),
          memory({ id: "b", status: "deprecated" }),
          memory({ id: "c", status: "active" }),
        ],
        [],
        [],
        [],
      )
      expect(stats.lifecycle?.map((r) => r.status)).toEqual([
        "active",
        "deprecated",
      ])
    })

    // `status` is optional on the payload: a graph of rows that predate the
    // field must not render a full-width "unknown" bar implying it said so.
    it("says nothing when no memory carried a status", () => {
      const stats = deriveGraphSummary(
        [memory({ id: "a" }), memory({ id: "b", status: null })],
        [],
        [],
        [],
      )
      expect(stats.lifecycle).toBeNull()
    })

    it("keeps the memories that carried no status visible in the split", () => {
      const stats = deriveGraphSummary(
        [memory({ id: "a", status: "active" }), memory({ id: "b" })],
        [],
        [],
        [],
      )
      expect(stats.lifecycle).toEqual([
        { status: "active", count: 1 },
        { status: "unknown", count: 1 },
      ])
    })
  })

  describe("clusters", () => {
    it("reports the largest cluster as a share of the visible graph", () => {
      const stats = deriveGraphSummary(
        [
          memory({ id: "a", cluster: 3 }),
          memory({ id: "b", cluster: 3 }),
          memory({ id: "c", cluster: 3 }),
          memory({ id: "d", cluster: 1 }),
        ],
        [],
        [],
        [],
      )
      expect(stats.largestCluster).toEqual({ id: 3, count: 3, share: 0.75 })
    })

    it("counts an unclustered memory apart from the clusters", () => {
      const stats = deriveGraphSummary(
        [memory({ id: "a", cluster: -1 }), memory({ id: "b", cluster: 2 })],
        [],
        [],
        [],
      )
      expect(stats.unclusteredCount).toBe(1)
      expect(stats.clusters).toEqual([{ id: 2, count: 1 }])
    })
  })

  describe("hubs", () => {
    // An entity's `memory_ids` spans the whole corpus; ranking on it puts an
    // entity with one visible memory above one with five.
    it("ranks an entity by its memories on screen, not by memory_ids", () => {
      const stats = deriveGraphSummary(
        [memory({ id: "a" }), memory({ id: "b" })],
        [],
        [
          entity({ id: "e1", name: "wide", memory_ids: ["a", "x", "y", "z"] }),
          entity({ id: "e2", name: "here", memory_ids: ["a", "b"] }),
        ],
        [],
      )
      expect(stats.hubs.map((h) => [h.name, h.count])).toEqual([
        ["here", 2],
        ["wide", 1],
      ])
    })

    it("drops an entity none of whose memories are on screen", () => {
      const stats = deriveGraphSummary(
        [memory({ id: "a" })],
        [],
        [entity({ id: "e1", memory_ids: ["elsewhere"] })],
        [],
      )
      expect(stats.hubs).toEqual([])
    })

    // Its type still belongs in the census — the node is on the canvas.
    it("still counts that entity's type", () => {
      const stats = deriveGraphSummary(
        [memory({ id: "a" })],
        [],
        [entity({ entity_type: "database", memory_ids: ["elsewhere"] })],
        [],
      )
      expect(stats.entityTypes).toEqual([
        { key: "database", label: "database", count: 1 },
      ])
    })
  })

  describe("facets", () => {
    it("groups a tag by the segment before its slash", () => {
      const stats = deriveGraphSummary(
        [
          memory({ id: "a", tags: ["project/darkmem", "area/retrieval"] }),
          memory({ id: "b", tags: ["project/other", "standalone"] }),
        ],
        [],
        [],
        [],
      )
      expect(stats.tagCategories).toEqual([
        { key: "project", label: "project", count: 2 },
        { key: "area", label: "area", count: 1 },
        { key: "standalone", label: "standalone", count: 1 },
      ])
    })

    it("labels a memory carrying no type", () => {
      const stats = deriveGraphSummary(
        [memory({ id: "a", memory_type: null })],
        [],
        [],
        [],
      )
      expect(stats.types).toEqual([
        { key: "(none)", label: "(none)", count: 1 },
      ])
    })

    it("counts relations by type, most common first", () => {
      const stats = deriveGraphSummary(
        [],
        [],
        [],
        [relation("USES"), relation("DEPENDS_ON"), relation("USES")],
      )
      expect(stats.relationTypes).toEqual([
        { key: "USES", label: "USES", count: 2 },
        { key: "DEPENDS_ON", label: "DEPENDS_ON", count: 1 },
      ])
    })

    // Two facets of equal count must not swap places between renders.
    it("breaks a count tie on the label", () => {
      const stats = deriveGraphSummary(
        [
          memory({ id: "a", source: "zulu" }),
          memory({ id: "b", source: "alpha" }),
        ],
        [],
        [],
        [],
      )
      expect(stats.sources.map((r) => r.label)).toEqual(["alpha", "zulu"])
    })
  })
})

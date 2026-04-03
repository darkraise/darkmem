import { describe, it, expect } from "vitest";
import { transformToGraphData, computeNodeVal } from "@/lib/graph-utils";
import { resolveNodeColor, UNIFIED_PALETTE, UNCLUSTERED_COLOR } from "@/lib/graph-colors";
import type { UnifiedGraphData } from "@/hooks/useApi";
import type { FilterState } from "@/lib/graph-utils";

const emptyFilters: FilterState = {
  searchText: "",
  selectedTags: new Set(),
  selectedTypes: new Set(),
  selectedSources: new Set(),
  selectedClusters: new Set(),
};

const sampleData: UnifiedGraphData = {
  memories: [
    { id: "a", content: "Alpha memory", source: "mem0", tags: ["test"], memory_type: "fact", importance: 0.8, cluster: 0 },
    { id: "b", content: "Beta memory", source: "memora", tags: ["debug"], memory_type: "debug", importance: 0.3, cluster: 0 },
    { id: "c", content: "Gamma memory", source: "mem0", tags: ["test"], memory_type: "fact", importance: 0.5, cluster: 1 },
    { id: "d", content: "Delta orphan", source: "mem0", tags: [], memory_type: null, importance: 0.1, cluster: -1 },
  ],
  clusters: { "0": ["a", "b"], "1": ["c"] },
  cluster_names: { "0": "Test Cluster", "1": "Gamma Cluster" },
  similarity_edges: [
    { source: "a", target: "b", score: 0.9 },
    { source: "a", target: "c", score: 0.8 },
    { source: "b", target: "c", score: 0.7 },
  ],
};

describe("resolveNodeColor", () => {
  it("returns palette color for valid cluster", () => {
    expect(resolveNodeColor({ cluster: 0, memory_type: null, tags: [] }, "cluster")).toBe(UNIFIED_PALETTE[0]);
    expect(resolveNodeColor({ cluster: 3, memory_type: null, tags: [] }, "cluster")).toBe(UNIFIED_PALETTE[3]);
  });

  it("wraps around palette for large cluster IDs", () => {
    expect(resolveNodeColor({ cluster: 51, memory_type: null, tags: [] }, "cluster")).toBe(UNIFIED_PALETTE[0]);
  });

  it("returns gray for unclustered (-1)", () => {
    expect(resolveNodeColor({ cluster: -1, memory_type: null, tags: [] }, "cluster")).toBe(UNCLUSTERED_COLOR);
  });

  it("returns consistent color for known types", () => {
    const factColor = resolveNodeColor({ cluster: 0, memory_type: "fact", tags: [] }, "type");
    expect(UNIFIED_PALETTE).toContain(factColor);
    expect(resolveNodeColor({ cluster: 1, memory_type: "fact", tags: [] }, "type")).toBe(factColor);
  });

  it("returns gray for null type", () => {
    expect(resolveNodeColor({ cluster: 0, memory_type: null, tags: [] }, "type")).toBe(UNCLUSTERED_COLOR);
  });

  it("returns consistent color for tag prefix", () => {
    const color1 = resolveNodeColor({ cluster: 0, memory_type: null, tags: ["project/darkmem"] }, "tag");
    const color2 = resolveNodeColor({ cluster: 1, memory_type: null, tags: ["project/homelab"] }, "tag");
    expect(color1).toBe(color2);
    expect(UNIFIED_PALETTE).toContain(color1);
  });

  it("returns gray for no tags", () => {
    expect(resolveNodeColor({ cluster: 0, memory_type: null, tags: [] }, "tag")).toBe(UNCLUSTERED_COLOR);
  });
});

describe("computeNodeVal", () => {
  it("returns fixed value for uniform mode", () => {
    expect(computeNodeVal("uniform", 10, 0.9)).toBe(2);
  });

  it("scales by importance", () => {
    const low = computeNodeVal("importance", 0, 0.1);
    const high = computeNodeVal("importance", 0, 0.9);
    expect(high).toBeGreaterThan(low);
  });

  it("scales by connections with log dampening", () => {
    const few = computeNodeVal("connections", 1, 0);
    const many = computeNodeVal("connections", 100, 0);
    expect(many).toBeGreaterThan(few);
  });
});

describe("transformToGraphData", () => {
  it("maps all memories to nodes with no filters", () => {
    const result = transformToGraphData(sampleData, "connections", emptyFilters);
    expect(result.nodes).toHaveLength(4);
    expect(result.links).toHaveLength(3);
  });

  it("uses type coloring by default", () => {
    const result = transformToGraphData(sampleData, "connections", emptyFilters);
    const nodeA = result.nodes.find((n) => n.id === "a")!;
    expect(nodeA.color).toBe(resolveNodeColor({ cluster: 0, memory_type: "fact", tags: ["test"] }, "type"));
    const nodeD = result.nodes.find((n) => n.id === "d")!;
    expect(nodeD.color).toBe(UNCLUSTERED_COLOR);
  });

  it("uses cluster coloring when specified", () => {
    const result = transformToGraphData(sampleData, "connections", emptyFilters, "cluster");
    const nodeA = result.nodes.find((n) => n.id === "a")!;
    expect(nodeA.color).toBe(UNIFIED_PALETTE[0]);
    const nodeD = result.nodes.find((n) => n.id === "d")!;
    expect(nodeD.color).toBe(UNCLUSTERED_COLOR);
  });

  it("resolves cluster names", () => {
    const result = transformToGraphData(sampleData, "connections", emptyFilters);
    const nodeA = result.nodes.find((n) => n.id === "a")!;
    expect(nodeA.clusterName).toBe("Test Cluster");
    const nodeD = result.nodes.find((n) => n.id === "d")!;
    expect(nodeD.clusterName).toBe("");
  });

  it("filters by search text", () => {
    const filters: FilterState = { ...emptyFilters, searchText: "alpha" };
    const result = transformToGraphData(sampleData, "connections", filters);
    expect(result.nodes).toHaveLength(1);
    expect(result.nodes[0].id).toBe("a");
  });

  it("filters by source", () => {
    const filters: FilterState = { ...emptyFilters, selectedSources: new Set(["memora"]) };
    const result = transformToGraphData(sampleData, "connections", filters);
    expect(result.nodes).toHaveLength(1);
    expect(result.nodes[0].id).toBe("b");
  });

  it("filters by cluster", () => {
    const filters: FilterState = { ...emptyFilters, selectedClusters: new Set([1]) };
    const result = transformToGraphData(sampleData, "connections", filters);
    expect(result.nodes).toHaveLength(1);
    expect(result.nodes[0].id).toBe("c");
  });

  it("excludes edges where either node is filtered out", () => {
    const filters: FilterState = { ...emptyFilters, selectedSources: new Set(["mem0"]) };
    const result = transformToGraphData(sampleData, "connections", filters);
    expect(result.nodes).toHaveLength(3);
    expect(result.links).toHaveLength(1);
    expect(result.links[0].source).toBe("a");
    expect(result.links[0].target).toBe("c");
  });

  it("filters by tags", () => {
    const filters: FilterState = { ...emptyFilters, selectedTags: new Set(["debug"]) };
    const result = transformToGraphData(sampleData, "connections", filters);
    expect(result.nodes).toHaveLength(1);
    expect(result.nodes[0].id).toBe("b");
  });

  it("filters by type", () => {
    const filters: FilterState = { ...emptyFilters, selectedTypes: new Set(["fact"]) };
    const result = transformToGraphData(sampleData, "connections", filters);
    expect(result.nodes).toHaveLength(2);
    expect(result.nodes.map((n) => n.id).sort()).toEqual(["a", "c"]);
  });
});

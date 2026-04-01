import { describe, it, expect } from "vitest";
import {
  transformToGraphData,
  clusterColor,
  computeNodeVal,
  CLUSTER_PALETTE,
  UNCLUSTERED_COLOR,
} from "@/lib/graph-utils";
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

describe("clusterColor", () => {
  it("returns palette color for valid cluster", () => {
    expect(clusterColor(0)).toBe(CLUSTER_PALETTE[0]);
    expect(clusterColor(3)).toBe(CLUSTER_PALETTE[3]);
  });

  it("wraps around palette for large cluster IDs", () => {
    expect(clusterColor(12)).toBe(CLUSTER_PALETTE[0]);
  });

  it("returns gray for unclustered (-1)", () => {
    expect(clusterColor(-1)).toBe(UNCLUSTERED_COLOR);
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

  it("assigns cluster color to nodes", () => {
    const result = transformToGraphData(sampleData, "connections", emptyFilters);
    const nodeA = result.nodes.find((n) => n.id === "a")!;
    expect(nodeA.color).toBe(CLUSTER_PALETTE[0]);
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

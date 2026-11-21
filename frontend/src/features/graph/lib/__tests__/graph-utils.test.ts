import { describe, it, expect, vi, afterEach } from "vitest"
import { transformToGraphData, type FilterState } from "../graph-utils"
import { buildMemoryPalette } from "../graph-colors"
import type { GraphThemeTokens } from "../code-graph-theme"
import type { UnifiedGraphData } from "@/hooks/api"

const NO_FILTERS: FilterState = {
  searchText: "",
  selectedTags: new Set(),
  selectedTypes: new Set(),
  selectedSources: new Set(),
  selectedClusters: new Set(),
}

const PALETTE = buildMemoryPalette({
  background: "#0b0f17",
  foreground: "#e6edf3",
  card: "#111",
  cardForeground: "#eee",
  popover: "#111",
  popoverForeground: "#eee",
  muted: "#222",
  mutedForeground: "#8b949e",
  border: "#333",
  primary: "#5b8cff",
  ring: "#5b8cff",
  destructive: "#ff5b5b",
  destructiveSolid: "#e5383b",
  canvas: "#09070e",
  nebula: "#5a1bbd",
  chart: ["#1", "#2", "#3", "#4", "#5"],
  primaryHue: 222,
  isDark: true,
  fontMono: "monospace",
} as GraphThemeTokens)

afterEach(() => {
  vi.restoreAllMocks()
})

describe("transformToGraphData", () => {
  it("3D build is linear in nodes", () => {
    const n = 5000
    const data: UnifiedGraphData = {
      memories: Array.from({ length: n }, (_, i) => ({
        id: `m${i}`,
        content: `memory ${i}`,
        source: "api",
        tags: [],
        memory_type: "fact",
        importance: 0.5,
        cluster: i % 50,
      })),
      clusters: {},
      cluster_names: {},
      similarity_edges: [],
    }
    const find = vi.spyOn(Array.prototype, "find")

    const { nodes, links } = transformToGraphData(
      data, "uniform", NO_FILTERS, "cluster", false, [], [], PALETTE,
    )

    expect(find).not.toHaveBeenCalled()
    expect(nodes).toHaveLength(n)
    const cluster = new Map(nodes.map((node) => [node.id, node.cluster]))
    expect(
      links.filter((l) => cluster.get(l.source) === cluster.get(l.target)),
    ).toHaveLength(0)
    expect(nodes.every((node) => node.anchor !== undefined)).toBe(true)
  })

  it("the text filter reads the preview and the tags", () => {
    const data: UnifiedGraphData = {
      memories: [
        { id: "a", content: "about postgres", source: "api", tags: [], memory_type: null, importance: 0.5, cluster: -1 },
        { id: "b", content: "unrelated", source: "api", tags: ["postgres"], memory_type: null, importance: 0.5, cluster: -1 },
        { id: "c", content: "unrelated", source: "api", tags: [], memory_type: null, importance: 0.5, cluster: -1 },
      ],
      clusters: {},
      cluster_names: {},
      similarity_edges: [],
    }
    const { nodes } = transformToGraphData(
      data, "uniform", { ...NO_FILTERS, searchText: "Postgres" }, "type", false, [], [], PALETTE,
    )
    expect(nodes.map((node) => node.id)).toEqual(["a", "b"])
  })
})

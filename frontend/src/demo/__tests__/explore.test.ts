import { describe, it, expect, beforeEach } from "vitest"
import {
  buildReindexPhases,
  computeBlastRadius,
  layoutGraph,
  matchEntities,
  mermaidForProcess,
  neighborhoodWithin,
  scopeMemoryGraph,
} from "../explore"
import {
  CURATED_CODE_GRAPHS,
  CURATED_CODE_REPOS,
  INDEX_PHASE_LABELS,
} from "../data/code-curated"
import { CURATED_MEMORY_GRAPH } from "../data/memory-graph-curated"
import { useDemoStore } from "../store"

const backendGraph = CURATED_CODE_GRAPHS.find(
  (g) => g.repo_id === "repo-backend",
)
if (!backendGraph) throw new Error("backend graph fixture missing")

describe("buildReindexPhases", () => {
  it("marks the opt-in LLM phases skipped when their toggles are off", () => {
    const phases = buildReindexPhases({
      full: false,
      enrich_symbols: false,
      generate_wiki: false,
    })
    expect(phases).toHaveLength(INDEX_PHASE_LABELS.length)
    expect(phases[0]?.state).toBe("current")
    expect(phases[12]?.state).toBe("skipped")
    expect(phases[13]?.state).toBe("skipped")
  })

  it("runs phases 13/14 when their toggles are on", () => {
    const phases = buildReindexPhases({
      full: true,
      enrich_symbols: true,
      generate_wiki: true,
    })
    expect(phases[12]?.state).toBe("pending")
    expect(phases[13]?.state).toBe("pending")
  })
})

describe("layoutGraph", () => {
  const items = backendGraph.nodes.map((n) => ({
    id: n.id,
    group: n.community,
  }))

  it.each(["force", "tree", "circles"] as const)(
    "%s layout positions every node inside the canvas",
    (mode) => {
      const positions = layoutGraph(items, backendGraph.edges, mode, 640, 400)
      for (const item of items) {
        const p = positions[item.id]
        expect(p).toBeDefined()
        expect(p!.x).toBeGreaterThanOrEqual(0)
        expect(p!.x).toBeLessThanOrEqual(640)
        expect(p!.y).toBeGreaterThanOrEqual(0)
        expect(p!.y).toBeLessThanOrEqual(400)
      }
    },
  )

  it("is deterministic for the same inputs", () => {
    const a = layoutGraph(items, backendGraph.edges, "force", 640, 400)
    const b = layoutGraph(items, backendGraph.edges, "force", 640, 400)
    expect(a).toEqual(b)
  })
})

describe("neighborhoodWithin", () => {
  it("returns only the start node at depth 0", () => {
    const set = neighborhoodWithin(backendGraph.edges, "n-process-batch", 0)
    expect(set).toEqual(new Set(["n-process-batch"]))
  })

  it("expands over undirected hops", () => {
    const d1 = neighborhoodWithin(backendGraph.edges, "n-process-batch", 1)
    expect(d1.has("n-extract-classify")).toBe(true)
    expect(d1.has("n-memory-add")).toBe(true)
    expect(d1.has("n-search")).toBe(false)
  })
})

describe("computeBlastRadius", () => {
  it("walks reverse edges — dependents, not callees", () => {
    const blast = computeBlastRadius(backendGraph, "n-process-batch")
    const ids = blast.affected.map((a) => a.id)
    // callers/containers of process_batch are affected
    expect(ids).toContain("n-memory-add")
    expect(ids).toContain("n-processing-pipeline")
    // its own callees are NOT
    expect(ids).not.toContain("n-extract-classify")
    expect(blast.total).toBe(blast.affected.length)
  })

  it("buckets depths and assigns a risk tier", () => {
    const blast = computeBlastRadius(backendGraph, "n-process-batch")
    const sum = blast.depths.reduce((s, d) => s + d.count, 0)
    expect(sum).toBe(blast.total)
    expect(["low", "medium", "high", "critical"]).toContain(blast.risk)
  })

  it("returns an empty radius for a leaf nobody depends on", () => {
    const blast = computeBlastRadius(backendGraph, "n-pipeline-py")
    expect(blast.total).toBe(0)
    expect(blast.risk).toBe("low")
  })
})

describe("mermaidForProcess", () => {
  it("renders a flowchart with resolved node names", () => {
    const process = backendGraph.processes.find((p) => p.id === "p-ingest")
    expect(process).toBeDefined()
    const mermaid = mermaidForProcess(process!, backendGraph)
    expect(mermaid.startsWith("flowchart TD")).toBe(true)
    expect(mermaid).toContain("A[process_batch] --> B[extract_and_classify]")
    expect(mermaid.split("\n")).toHaveLength(process!.steps.length)
  })
})

describe("memory graph scoping", () => {
  it("scopes entities, relations, and topics to one project", () => {
    const scoped = scopeMemoryGraph(CURATED_MEMORY_GRAPH, "darkmem")
    expect(scoped.entities.length).toBe(12)
    expect(scoped.topics.length).toBe(3)
    expect(
      scoped.relations.every((r) =>
        scoped.entities.some((e) => e.id === r.source),
      ),
    ).toBe(true)
    const other = scopeMemoryGraph(CURATED_MEMORY_GRAPH, "acme-storefront")
    expect(other.entities.length).toBe(4)
    expect(other.topics.length).toBe(1)
  })

  it("never uses the caution chart slot for a topic", () => {
    expect(
      CURATED_MEMORY_GRAPH.topics.every((t) => t.chart !== (4 as number)),
    ).toBe(true)
  })

  it("matches entities case-insensitively, empty query matches nothing", () => {
    const scoped = scopeMemoryGraph(CURATED_MEMORY_GRAPH, "darkmem")
    expect(matchEntities(scoped, "POSTGRES")).toEqual(new Set(["e-postgres"]))
    expect(matchEntities(scoped, "")).toEqual(new Set())
  })
})

describe("store actions", () => {
  beforeEach(() => {
    useDemoStore.setState({
      codeRepos: CURATED_CODE_REPOS.map((r) => ({ ...r })),
      chatThreads: [],
    })
  })

  it("triggerReindex flips a repo to indexing and clears stale/error", () => {
    useDemoStore.getState().triggerReindex("repo-payments", {
      full: true,
      enrich_symbols: false,
      generate_wiki: true,
    })
    const repo = useDemoStore
      .getState()
      .codeRepos.find((r) => r.id === "repo-payments")
    expect(repo?.status).toBe("indexing")
    expect(repo?.stale).toBeNull()
    expect(repo?.phases?.[13]?.state).toBe("pending")
    expect(repo?.phases?.[12]?.state).toBe("skipped")
  })

  it("sendChatMessage creates a thread and appends a canned reply", () => {
    const id = useDemoStore.getState().sendChatMessage(null, "hello demo")
    const thread = useDemoStore
      .getState()
      .chatThreads.find((t) => t.id === id)
    expect(thread).toBeDefined()
    expect(thread?.messages).toHaveLength(2)
    expect(thread?.messages[0]?.role).toBe("user")
    expect(thread?.messages[1]?.role).toBe("assistant")
    expect(thread?.messages[1]?.context).toBeDefined()
  })

  it("sendChatMessage appends to an existing thread", () => {
    const id = useDemoStore.getState().sendChatMessage(null, "first")
    useDemoStore.getState().sendChatMessage(id, "second")
    const thread = useDemoStore
      .getState()
      .chatThreads.find((t) => t.id === id)
    expect(thread?.messages).toHaveLength(4)
  })
})

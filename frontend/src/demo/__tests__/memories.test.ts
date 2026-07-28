import { describe, expect, it } from "vitest"
import {
  deriveTimeline,
  enrichBulkMemories,
  searchDemoMemories,
  type RawBulkMemory,
} from "../memories"
import { CURATED_IDS, CURATED_MEMORIES } from "../data/memories-curated"
import { useDemoStore } from "../store"
import type { DemoMemory } from "../types"

function rawRows(n: number): RawBulkMemory[] {
  return Array.from({ length: n }, (_, i) => ({
    id: `raw-${i}`,
    content: `Demo memory ${i}: python setup for auth`,
    source: "api",
    memory_type: "fact",
    technologies: ["python"],
    tags: ["auth"],
    project: "default",
    confidence: 0.6,
    status: "active",
    created_at: new Date(Date.now() - i * 60_000).toISOString(),
  }))
}

describe("enrichBulkMemories", () => {
  it("fills the full Memory shape and marks rows as layer 0", () => {
    const m = enrichBulkMemories(rawRows(1))[0]!
    expect(m.layer).toBe(0)
    expect(m.is_archived).toBe(false)
    expect(m.updated_at).toBe(m.created_at)
    expect(m.classified_type).toBe("fact")
  })

  it("spreads created_at deterministically across the last ~12 months", () => {
    const now = new Date("2026-07-25T12:00:00").getTime()
    const a = enrichBulkMemories(rawRows(1000), now)
    const b = enrichBulkMemories(rawRows(1000), now)
    expect(a.map((m) => m.created_at)).toEqual(b.map((m) => m.created_at))
    const yearAgo = now - 366 * 86_400_000
    const distinctDays = new Set<string>()
    for (const m of a) {
      const t = Date.parse(m.created_at)
      expect(t).toBeLessThanOrEqual(now)
      expect(t).toBeGreaterThanOrEqual(yearAgo)
      distinctDays.add(m.created_at.slice(0, 10))
    }
    expect(distinctDays.size).toBeGreaterThan(150)
  })

  it("never produces a superseded row without a pointer (chk mirror)", () => {
    const rows = enrichBulkMemories(rawRows(300))
    const superseded = rows.filter((m) => m.status === "superseded")
    expect(superseded.length).toBeGreaterThan(0)
    for (const m of superseded) {
      expect(m.superseded_by).toBeTruthy()
      expect(rows.some((other) => other.id === m.superseded_by)).toBe(true)
    }
  })
})

describe("searchDemoMemories", () => {
  const memories: DemoMemory[] = [
    ...CURATED_MEMORIES,
    ...enrichBulkMemories(rawRows(50)),
  ]

  it("returns ranked results each carrying a full trace", () => {
    const { results, totalMatches } = searchDemoMemories(memories, {
      query: "reranker",
      project: "all",
      context: null,
    })
    expect(results.length).toBeGreaterThan(0)
    expect(totalMatches).toBeGreaterThanOrEqual(results.length)
    for (const { trace } of results) {
      expect(trace.channels.map((c) => c.name)).toEqual([
        "semantic",
        "keyword",
        "ppr",
        "rerank",
      ])
      expect(trace.rrf_score).toBeGreaterThan(0)
      expect(trace.summary).toContain("ranked")
    }
    const scores = results.map((r) => r.trace.rrf_score)
    expect([...scores].sort((a, b) => b - a)).toEqual(scores)
  })

  it("keeps superseded matches in the results, labelled — never dropped", () => {
    const { results } = searchDemoMemories(memories, {
      query: "reranker",
      project: "all",
      context: null,
    })
    const stale = results.find(
      (r) => r.memory.id === CURATED_IDS.rerankFullList,
    )
    expect(stale).toBeDefined()
    expect(stale!.memory.status).toBe("superseded")
  })

  it("is deterministic for the same query", () => {
    const q = { query: "reranker rrf", project: "all", context: null }
    const a = searchDemoMemories(memories, q)
    const b = searchDemoMemories(memories, q)
    expect(a.results.map((r) => [r.memory.id, r.trace.rrf_score])).toEqual(
      b.results.map((r) => [r.memory.id, r.trace.rrf_score]),
    )
  })

  it("excludes context-conflicting rows with a counted reason", () => {
    const withContext = searchDemoMemories(memories, {
      query: "plain-http lan logins",
      project: "all",
      context: "env=prod",
    })
    expect(
      withContext.results.some((r) => r.memory.id === CURATED_IDS.cookieLan),
    ).toBe(false)
    const conflict = withContext.exclusions.find(
      (e) => e.tag === "by_context_conflict",
    )
    expect(conflict).toBeDefined()
    expect(conflict!.count).toBeGreaterThanOrEqual(1)

    const withoutContext = searchDemoMemories(memories, {
      query: "plain-http lan logins",
      project: "all",
      context: null,
    })
    expect(
      withoutContext.results.some((r) => r.memory.id === CURATED_IDS.cookieLan),
    ).toBe(true)
  })

  it("counts out-of-scope matches as by_project exclusions", () => {
    const scoped = searchDemoMemories(memories, {
      query: "auth",
      project: "darkmem",
      context: null,
    })
    expect(scoped.results.every((r) => r.memory.project === "darkmem")).toBe(
      true,
    )
    const byProject = scoped.exclusions.find((e) => e.tag === "by_project")
    expect(byProject).toBeDefined()
    expect(byProject!.count).toBeGreaterThan(0)
  })

  it("returns the empty no-match outcome for an unmatched query", () => {
    const outcome = searchDemoMemories(memories, {
      query: "wireshark packet capture",
      project: "all",
      context: null,
    })
    expect(outcome.results).toEqual([])
    expect(outcome.totalMatches).toBe(0)
  })
})

describe("deriveTimeline", () => {
  it("derives created + extracted for a plain bulk row", () => {
    const m = enrichBulkMemories(rawRows(1))[0]!
    const events = deriveTimeline(m)
    expect(events.map((e) => e.kind)).toEqual(["created", "extracted"])
  })

  it("appends the lifecycle transition for a superseded row", () => {
    const rows = enrichBulkMemories(rawRows(98))
    const superseded = rows.find((m) => m.status === "superseded")!
    const events = deriveTimeline(superseded)
    const last = events[events.length - 1]!
    expect(last.kind).toBe("superseded")
    expect(last.transition).toEqual({ from: null, to: "superseded" })
  })

  it("returns a handcrafted timeline unchanged", () => {
    const hero = CURATED_MEMORIES.find(
      (m) => m.id === CURATED_IDS.rerankTop40,
    )!
    expect(deriveTimeline(hero)).toBe(hero.timeline)
  })
})

describe("demo store memory actions", () => {
  it("addMemory prepends and bumps the stat; updateMemory patches in place", () => {
    const initialCount = useDemoStore.getState().memories.length
    const m: DemoMemory = {
      ...CURATED_MEMORIES[0]!,
      id: "test-added-memory",
      content: "added via test",
      relations: [],
      timeline: [],
    }
    useDemoStore.getState().addMemory(m)
    let state = useDemoStore.getState()
    expect(state.memories[0]!.id).toBe("test-added-memory")
    expect(state.stats.totalMemories).toBe(initialCount + 1)

    useDemoStore.getState().updateMemory("test-added-memory", {
      content: "patched",
    })
    state = useDemoStore.getState()
    expect(state.memories[0]!.content).toBe("patched")

    useDemoStore.getState().resetMemories()
    expect(useDemoStore.getState().memories.length).toBe(initialCount)
  })
})

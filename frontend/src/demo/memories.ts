import type { DemoMemory, MemoryTimelineEvent } from "@/features/memories/types"
import type {
  MemoryExclusion,
  MemorySearchOutcome,
  MemorySearchQuery,
  MemoryTrace,
  MemoryTraceChannel,
} from "./types"

/** Raw shape of the generated bulk fixture rows (data/memories.json). */
export interface RawBulkMemory {
  id: string
  content: string
  source: string
  memory_type: string
  technologies: string[]
  tags: string[]
  project: string
  confidence: number
  status: string
  created_at: string
}

// Every 97th bulk row is superseded by its predecessor, mirroring the
// chk_superseded_has_pointer invariant: superseded always carries a pointer.
const SUPERSEDED_EVERY = 97

const DAY_MS = 86_400_000
const MINUTE_MS = 60_000
const SPREAD_DAYS = 364

function hash32(n: number): number {
  return (Math.imul(n + 1, 2654435761) >>> 0) % 2 ** 31
}

// ~1 in 5 calendar days carries no captures at all, so the year heatmap and
// the timeline scrubber both show honest gaps instead of a uniform wash.
function isQuietDay(daysAgo: number): boolean {
  return daysAgo > 0 && hash32(daysAgo * 31) % 5 === 0
}

function spreadDaysAgo(i: number): number {
  const u = (hash32(i) % 10_000) / 10_000
  const recentBurst = hash32(i + 70_001) % 3 === 0
  let d = recentBurst ? Math.floor(u * 56) : Math.floor(u * SPREAD_DAYS)
  for (let hop = 0; isQuietDay(d) && hop < 3; hop++) d = d > 1 ? d - 1 : d + 2
  return d
}

/**
 * Deterministic per-index timestamp spread over the last ~12 months, relative
 * to `now` — recent weeks are denser, quiet days stay empty. This is what
 * makes the year heatmap and the timeline scrubber meaningful demo surfaces.
 */
export function spreadCreatedAt(i: number, now: number): string {
  const todayStart = new Date(now)
  todayStart.setHours(0, 0, 0, 0)
  const daysAgo = spreadDaysAgo(i)
  const dayStart = todayStart.getTime() - daysAgo * DAY_MS
  let minute = hash32(i * 7 + 13) % (24 * 60)
  if (daysAgo === 0) {
    const elapsed = Math.max(
      1,
      Math.floor((now - todayStart.getTime()) / MINUTE_MS),
    )
    minute %= elapsed
  }
  return new Date(dayStart + minute * MINUTE_MS).toISOString()
}

export function enrichBulkMemories(
  rows: RawBulkMemory[],
  now: number = Date.now(),
): DemoMemory[] {
  return rows.map((row, i) => {
    const predecessorId =
      i > 0 && i % SUPERSEDED_EVERY === 0 ? rows[i - 1]?.id : undefined
    const superseded = predecessorId != null
    const created_at = spreadCreatedAt(i, now)
    return {
      ...row,
      created_at,
      source_agent: null,
      importance: 5,
      metadata: {},
      updated_at: created_at,
      expires_at: null,
      is_archived: false,
      classified_type: row.memory_type,
      summary: null,
      emotions: [],
      flags: [],
      layer: 0,
      status: superseded ? "superseded" : "active",
      superseded_by: predecessorId ?? null,
      confidence: Math.round(row.confidence * 100) / 100,
    }
  })
}

/** Deterministic 0–1 hash so trace scores are stable across renders. */
export function hash01(input: string): number {
  let h = 2166136261
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return ((h >>> 0) % 1000) / 1000
}

function tokenize(query: string): string[] {
  return query
    .toLowerCase()
    .split(/[^a-z0-9_.=-]+/)
    .filter((t) => t.length > 1)
}

function haystack(m: DemoMemory): string {
  return [m.content, ...(m.tags ?? []), ...(m.technologies ?? [])]
    .join(" ")
    .toLowerCase()
}

const RESULT_CAP = 30
const RERANK_WINDOW = 5

interface ScoredMemory {
  memory: DemoMemory
  semantic: number
  keyword: number
  hits: number
  tokenCount: number
  contextMatch: boolean
  rrf: number
}

function scoreMemory(
  m: DemoMemory,
  tokens: string[],
  query: string,
  context: string | null,
): ScoredMemory | null {
  const hay = haystack(m)
  const hits = tokens.filter((t) => hay.includes(t)).length
  if (hits === 0) return null
  const keyword = hits / tokens.length
  const jitter = hash01(m.id + query)
  const semantic =
    Math.round((0.4 + 0.55 * (0.6 * keyword + 0.4 * jitter)) * 100) / 100
  const contextMatch = context != null && m.applies_when === context
  let rrf = 0.015 + 0.035 * (0.7 * semantic + 0.3 * keyword)
  if (contextMatch) rrf *= 1.18
  return {
    memory: m,
    semantic,
    keyword: Math.round(keyword * 100) / 100,
    hits,
    tokenCount: tokens.length,
    contextMatch,
    rrf: Math.round(rrf * 10_000) / 10_000,
  }
}

function buildTrace(s: ScoredMemory, rank: number): MemoryTrace {
  const reranked = rank < RERANK_WINDOW
  const rerankScore = reranked
    ? Math.round((4 + 5.5 * (0.7 * s.semantic + 0.3 * s.keyword)) * 10) / 10
    : null
  const channels: MemoryTraceChannel[] = [
    { name: "semantic", fraction: s.semantic },
    { name: "keyword", fraction: s.keyword },
    { name: "ppr", fraction: null },
    {
      name: "rerank",
      fraction: rerankScore != null ? rerankScore / 10 : null,
      display: rerankScore != null ? `${rerankScore.toFixed(1)} / 10` : undefined,
    },
  ]
  const strength =
    s.semantic >= 0.75 ? "strong" : s.semantic >= 0.55 ? "moderate" : "weak"
  const parts = [
    `${strength} semantic match`,
    `${s.hits} of ${s.tokenCount} keyword${s.tokenCount === 1 ? "" : "s"} hit`,
  ]
  if (s.contextMatch) parts.push("boosted by the matching declared context")
  if (!reranked) parts.push("rode the unscored tail past the rerank window")
  return {
    channels,
    rrf_score: s.rrf,
    summary: `${parts.join("; ")} — ranked #${rank + 1} by the fused score.`,
  }
}

/**
 * Deterministic mock of the hybrid retrieval path: token matching stands in
 * for both channels, RRF-style fusion orders the list, and exclusions are
 * counted (never silently dropped rows). Superseded and deprecated matches
 * stay in the results, labelled — lifecycle is a badge, not a filter.
 */
export function searchDemoMemories(
  memories: DemoMemory[],
  { query, project, context }: MemorySearchQuery,
): MemorySearchOutcome {
  const tokens = tokenize(query)
  if (tokens.length === 0) {
    return { results: [], exclusions: [], totalMatches: 0 }
  }

  const scoped: ScoredMemory[] = []
  let outOfProject = 0
  let contextConflicts = 0
  const conflictingContexts = new Set<string>()

  for (const m of memories) {
    const scored = scoreMemory(m, tokens, query, context)
    if (!scored) continue
    if (project !== "all" && m.project !== project) {
      outOfProject += 1
      continue
    }
    if (context != null && m.applies_when && m.applies_when !== context) {
      contextConflicts += 1
      conflictingContexts.add(m.applies_when)
      continue
    }
    scoped.push(scored)
  }

  scoped.sort(
    (a, b) => b.rrf - a.rrf || a.memory.id.localeCompare(b.memory.id),
  )

  const exclusions: MemoryExclusion[] = []
  if (contextConflicts > 0) {
    exclusions.push({
      count: contextConflicts,
      unit: contextConflicts === 1 ? "memory" : "memories",
      reason: `your declared context ${context} conflicts with a ${[...conflictingContexts].join(", ")}-only row`,
      tag: "by_context_conflict",
    })
  }
  if (outOfProject > 0) {
    exclusions.push({
      count: outOfProject,
      unit: outOfProject === 1 ? "memory" : "memories",
      reason: `outside the current project scope (${project})`,
      tag: "by_project",
    })
  }

  return {
    results: scoped
      .slice(0, RESULT_CAP)
      .map((s, rank) => ({ memory: s.memory, trace: buildTrace(s, rank) })),
    exclusions,
    totalMatches: scoped.length,
  }
}

/** Fallback timeline for rows without a handcrafted one (bulk fixtures). */
export function deriveTimeline(m: DemoMemory): MemoryTimelineEvent[] {
  if (m.timeline && m.timeline.length > 0) return m.timeline
  const events: MemoryTimelineEvent[] = [
    {
      at: m.created_at,
      kind: "created",
      description: "object: this memory",
      note: `captured via ${m.source}`,
    },
    {
      at: m.created_at,
      kind: "extracted",
      description: "object: this memory",
      note: `classified_type set to ${m.classified_type ?? m.memory_type ?? "unknown"}`,
    },
  ]
  if (m.status === "superseded") {
    events.push({
      at: m.updated_at,
      kind: "superseded",
      description: "object: this memory",
      note: "status and superseded_by written atomically, per chk_superseded_has_pointer",
      transition: { from: null, to: "superseded" },
    })
  }
  if (m.status === "deprecated") {
    events.push({
      at: m.updated_at,
      kind: "deprecated",
      description: "object: this memory",
      note: "successor removed; superseded_by cleared to satisfy chk_superseded_has_pointer",
      transition: { from: "superseded", to: "deprecated" },
    })
  }
  return events
}

export function distinctProjects(memories: DemoMemory[]): string[] {
  return [...new Set(memories.map((m) => m.project))].sort()
}

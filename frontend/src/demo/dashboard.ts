import type {
  ActivityEvent,
  ContributionDay,
  DashboardStats,
} from "./types"

export function buildDashboardStats(memoryCount: number): DashboardStats {
  return {
    totalMemories: memoryCount,
    verifiedFacts: 412,
    liveArticles: 37,
    pendingReview: 9,
    disputedFacts: 2,
  }
}

const DAY_MS = 86_400_000

// Knuth multiplicative hash keeps the calendar deterministic per day index
// while looking organically sparse.
function seededCount(dayIndex: number): number {
  const h = (dayIndex * 2654435761) % 2 ** 31
  const v = h % 10
  return v < 4 ? 0 : v - 3
}

export function buildContributions(
  weeks = 26,
  now = Date.now(),
): ContributionDay[] {
  const total = weeks * 7
  return Array.from({ length: total }, (_, i) => {
    const daysAgo = total - 1 - i
    return {
      date: new Date(now - daysAgo * DAY_MS).toISOString().slice(0, 10),
      count: seededCount(daysAgo),
    }
  })
}

const FEED: Array<Omit<ActivityEvent, "id" | "at"> & { minutesAgo: number }> = [
  {
    minutesAgo: 4,
    kind: "pipeline",
    title: "Batch of 3 memories processed",
    detail: "12 entities, 9 relations extracted",
  },
  {
    minutesAgo: 11,
    kind: "fact",
    title: "cookie_secure defaults to Secure-only-in-production",
    detail: "ratified by a human — lifted to confirmed",
    verification: "confirmed",
    layer: 2,
  },
  {
    minutesAgo: 26,
    kind: "memory",
    title: "Speculative REPLACES markers are scoped per target sentence",
    verification: "corroborated",
    layer: 0,
  },
  {
    minutesAgo: 58,
    kind: "article",
    title: "Retrieval pipeline overview re-synthesised",
    detail: "3 citations refreshed",
    layer: 3,
  },
  {
    minutesAgo: 95,
    kind: "review",
    title: "2 disputed facts queued for review",
    detail: "conflicting sources on the MCP host allowlist default",
    verification: "disputed",
    layer: 2,
  },
  {
    minutesAgo: 130,
    kind: "job",
    title: "graph_orphan_cleanup completed",
    detail: "0 orphans pruned",
  },
  {
    minutesAgo: 245,
    kind: "memory",
    title: "Dev-proxy 502 note superseded by the keep-alive fix",
    verification: "superseded",
    layer: 0,
  },
  {
    minutesAgo: 380,
    kind: "fact",
    title: "MCP endpoint is localhost-only until MCP_ALLOWED_HOSTS extends it",
    detail: "single origin so far — awaiting corroboration",
    verification: "candidate",
    layer: 2,
  },
]

export function buildActivityFeed(now = Date.now()): ActivityEvent[] {
  return FEED.map(({ minutesAgo, ...event }, i) => ({
    ...event,
    id: `demo-event-${i}`,
    at: new Date(now - minutesAgo * 60_000).toISOString(),
  }))
}

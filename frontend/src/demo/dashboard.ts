import { localDayKey } from "@/lib/format"
import type { ContributionDay } from "@/features/dashboard/types"
import type { ActivityEvent, DashboardStats } from "./types"

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
const YEAR_DAYS = 364

export interface ContributionSourceRow {
  created_at: string
  memory_type?: string | null
  verification_status?: string | null
}

interface DayAggregate {
  count: number
  types: Map<string, number>
  verified: number
}

/**
 * Derive the full-year contribution calendar from the memory set itself, so
 * a heatmap cell's count always matches what the Memories timeline shows for
 * that day. Range: the Monday on/before (today − 52 weeks) through today,
 * chronological, one entry per local calendar day.
 */
export function buildContributions(
  memories: ContributionSourceRow[],
  now = Date.now(),
): ContributionDay[] {
  const today = new Date(now)
  today.setHours(0, 0, 0, 0)
  const start = new Date(today.getTime() - YEAR_DAYS * DAY_MS)
  start.setDate(start.getDate() - ((start.getDay() + 6) % 7))

  const byDay = new Map<string, DayAggregate>()
  for (const m of memories) {
    const at = new Date(m.created_at)
    if (Number.isNaN(at.getTime())) continue
    const key = localDayKey(at)
    let agg = byDay.get(key)
    if (!agg) {
      agg = { count: 0, types: new Map(), verified: 0 }
      byDay.set(key, agg)
    }
    agg.count += 1
    const type = m.memory_type ?? "untyped"
    agg.types.set(type, (agg.types.get(type) ?? 0) + 1)
    if (
      m.verification_status === "corroborated" ||
      m.verification_status === "confirmed"
    ) {
      agg.verified += 1
    }
  }

  const days: ContributionDay[] = []
  const cursor = new Date(start)
  while (cursor.getTime() <= today.getTime()) {
    const key = localDayKey(cursor)
    const agg = byDay.get(key)
    days.push({
      date: key,
      count: agg?.count ?? 0,
      types: agg
        ? [...agg.types.entries()]
            .map(([label, count]) => ({ label, count }))
            .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
        : [],
      verified: agg?.verified ?? 0,
    })
    cursor.setDate(cursor.getDate() + 1)
  }
  return days
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

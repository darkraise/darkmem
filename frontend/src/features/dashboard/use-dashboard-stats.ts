import { DEMO } from "@/lib/demo-flag"
import { useDemoStats } from "@/demo/hooks"
import type { DashboardStats } from "@/features/dashboard/types"
import {
  useFactCount,
  useProjects,
  useReviewQueueCounts,
  useStats,
} from "@/hooks/api"
import { useProjectStore } from "@/stores/project-store"
import { useArticles } from "@/hooks/api/use-articles-api"

export interface DashboardStatsState {
  stats: DashboardStats
  isLoading: boolean
  isError: boolean
}

/**
 * Binds the dashboard tiles to the real API outside demo mode, following
 * `use-contribution-calendar.ts`. The route used to call `useDemoStats()`
 * unconditionally, so every tile rendered the fixture store's numbers —
 * 5010 memories on a vault holding none, while the memories page beside it
 * correctly showed nothing.
 *
 * Five tiles over five endpoints rather than one aggregate: no endpoint
 * serves this set, and inventing a dashboard-shaped one would put a second
 * definition of "verified" and "live" behind a route, next to the ladder's.
 * All hooks run unconditionally (rules of hooks); only the request is
 * skipped via `enabled`.
 */
export function useDashboardStats(): DashboardStatsState {
  const demo = useDemoStats()
  const enabled = !DEMO
  // The header scope narrows every tile. `/analytics/stats` has no project
  // filter, so a scoped memory total comes from the project catalogue's own
  // count; every other tile's read takes `project` directly.
  const project = useProjectStore((s) => s.activeProject) ?? undefined

  const stats = useStats({ enabled: enabled && !project })
  const projects = useProjects()
  // `verified` is the machine rung plus the human one, matching the demo
  // store's own predicate and the ladder's: `corroborated` is the machine's
  // ceiling, `confirmed` is human-only.
  const corroborated = useFactCount({ project, verification_status: "corroborated" }, { enabled })
  const confirmed = useFactCount({ project, verification_status: "confirmed" }, { enabled })
  const disputed = useFactCount({ project, verification_status: "disputed" }, { enabled })
  // `GET /knowledge/articles` is already the live page — superseded articles
  // are off it by contract — so its `total` is the live count, not a total
  // needing a client-side filter.
  const articles = useArticles({ project, limit: 1 }, { enabled })
  const review = useReviewQueueCounts({ project }, { enabled })

  if (DEMO) {
    return { stats: demo, isLoading: false, isError: false }
  }

  const memoryTotal = project
    ? (projects.data?.find((p) => p.name === project)?.memory_count ?? 0)
    : (stats.data?.memories ?? 0)
  const queries = [
    project ? projects : stats,
    corroborated,
    confirmed,
    disputed,
    articles,
    review,
  ]

  return {
    stats: {
      totalMemories: memoryTotal,
      verifiedFacts: (corroborated.data?.total ?? 0) + (confirmed.data?.total ?? 0),
      liveArticles: articles.data?.total ?? 0,
      pendingReview: (review.data?.facts ?? 0) + (review.data?.articles ?? 0),
      disputedFacts: disputed.data?.total ?? 0,
    },
    isLoading: queries.some((q) => q.isLoading),
    isError: queries.some((q) => q.isError),
  }
}

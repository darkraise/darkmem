import { DEMO } from "@/lib/demo-flag"
import { useDemoStats } from "@/demo/hooks"
import type { DashboardStats } from "@/features/dashboard/types"
import { useStats, useFactCount, useReviewQueueCounts } from "@/hooks/api"
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

  const stats = useStats({ enabled })
  // `verified` is the machine rung plus the human one, matching the demo
  // store's own predicate and the ladder's: `corroborated` is the machine's
  // ceiling, `confirmed` is human-only.
  const corroborated = useFactCount({ verification_status: "corroborated" }, { enabled })
  const confirmed = useFactCount({ verification_status: "confirmed" }, { enabled })
  const disputed = useFactCount({ verification_status: "disputed" }, { enabled })
  // `GET /knowledge/articles` is already the live page — superseded articles
  // are off it by contract — so its `total` is the live count, not a total
  // needing a client-side filter.
  const articles = useArticles({ limit: 1 }, { enabled })
  const review = useReviewQueueCounts({}, { enabled })

  if (DEMO) {
    return { stats: demo, isLoading: false, isError: false }
  }

  const queries = [stats, corroborated, confirmed, disputed, articles, review]

  return {
    stats: {
      totalMemories: stats.data?.memories ?? 0,
      verifiedFacts: (corroborated.data?.total ?? 0) + (confirmed.data?.total ?? 0),
      liveArticles: articles.data?.total ?? 0,
      pendingReview: (review.data?.facts ?? 0) + (review.data?.articles ?? 0),
      disputedFacts: disputed.data?.total ?? 0,
    },
    isLoading: queries.some((q) => q.isLoading),
    isError: queries.some((q) => q.isError),
  }
}

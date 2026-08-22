import { useProjectStore } from "@/stores/project-store"

/**
 * The query-key layer (doc 13 §2): the one place that decides whether a
 * TanStack Query domain is scoped by the active project, and the one place
 * a new domain must be classified before its key can exist.
 *
 * Four kinds, deliberately not a two-way "scoped or not" bit:
 *
 * - `"auto"` — built exclusively through `projectScopedKey` /
 *   `useProjectScopedKey` below, which prepend the active project. The key
 *   is mechanically guaranteed to change when the project changes.
 * - `"manual"` — the request already carries an explicit `project` field
 *   the caller supplies (e.g. a page-local filter), so the query key
 *   already varies with project — just not automatically from the global
 *   switcher yet. Wiring that up is a follow-on integration for whoever
 *   owns that surface, not a re-classification here.
 * - `"global"` — the resource genuinely has no project axis: settings,
 *   jobs, code repos, chat, or a lookup addressed by an id that already
 *   uniquely determines its row (a memory or its graph context by id).
 * - `"deferred"` — a real, named gap: the backend can scope this resource
 *   by project (or plausibly should) and no frontend caller passes one
 *   yet. Recorded rather than mislabelled `"global"`, so the gap stays
 *   visible instead of reading as a deliberate design choice.
 *
 * `query-keys.test.ts` scans `src/hooks/api/**` for every `queryKey:`
 * literal's leading string and fails on any that is not a key of this
 * map — so a new query key must be classified here before it can exist,
 * rather than silently inheriting whatever scope its neighbours happened
 * to have (Ruling 1).
 */
export type QueryKeyScope =
  | { kind: "auto" }
  | { kind: "manual"; reason: string }
  | { kind: "global"; reason?: string }
  | { kind: "deferred"; reason: string }

export const QUERY_KEY_SCOPE: Record<string, QueryKeyScope> = {
  // ── auto: routed through projectScopedKey / useProjectScopedKey ──
  memories: { kind: "auto" },
  unifiedGraph: { kind: "auto" },

  // ── manual: already carries an explicit project field, not yet wired
  //    to the global switcher ──
  memoriesPaginated: {
    kind: "manual",
    reason:
      "PaginatedSearchParams.project is caller-supplied (the Memories page's own project filter), not yet the global switcher",
  },
  knowledge: {
    kind: "manual",
    reason:
      "GET /knowledge/facts takes an explicit `project` the Facts tab supplies from its own filter (doc 13 §5.1), not yet the global switcher",
  },
  articles: {
    kind: "manual",
    reason:
      "GET /knowledge/articles takes an explicit `project` the Articles tab supplies from its own filter (doc 13 §5.2), the same posture its Facts sibling carries and for the same reason: a browsing surface silently scoped to one project makes the others read as absent. The detail read is addressed by article id and carries no project param at all",
  },
  dreamDigest: {
    kind: "manual",
    reason:
      "GET /dream-digest/cycles takes an explicit `project` filter (doc 13 §6.3); the single-cycle read is addressed by cycle_id and carries no project param at all",
  },
  distribution: {
    kind: "global",
    reason:
      "Distribution config is per-installation, not per-project: the adapter registry maps a tool to a file path, and the curb stops push everywhere at once (doc 13 §6.5). Scoping it to a project would imply push could be curbed for one and live for another, which is the opposite of what a single stop control means",
  },
  reviewQueue: {
    kind: "manual",
    reason:
      "GET /review-queue/{facts,articles,counts} all take an explicit `project` the Review queue supplies from its own filter (doc 13 §6.2), not yet the global switcher. The counts door gained that parameter in T2.88; until then it had none and the surface rendered its number with an explicit unscoped qualifier",
  },
  hygieneQueue: {
    kind: "manual",
    reason:
      "GET /hygiene-queue/* take an explicit `project` the Hygiene queue supplies from its own filter (doc 13 §6.2), not yet the global switcher",
  },
  events: {
    kind: "manual",
    reason: "EventListParams.project is caller-supplied, not yet the global switcher",
  },
  eventsCalendar: {
    kind: "manual",
    reason: "params.project is caller-supplied, not yet the global switcher",
  },

  documents: {
    kind: "manual",
    reason:
      "GET /documents takes an explicit `project` the Documents surface supplies, the same posture its Facts and Articles siblings carry (TH1.16, doc 16 §6)",
  },
  documentSummary: {
    kind: "global",
    reason:
      "Addressed by document id and carrying no project param: the document's own project is what scopes the read server-side, so a project-keyed cache entry would key on something the request does not send",
  },
  documentConnections: {
    kind: "global",
    reason:
      "Addressed by document id, and the connections query scopes itself to that document's project in SQL — deliberately, since a cross-project suggestion surface is the worst place to leak an isolation boundary",
  },

  autoResearch: {
    kind: "global",
    reason:
      "The research loop's arm switch and budgets are per-installation, not per-project: the loop files evidence a caller gathered, and arming it for one project while another stays disarmed is not a distinction the config row can express (T3.28, doc 09 §6)",
  },

  // ── deferred: named gaps ──
  tags: {
    kind: "deferred",
    reason: "GET /tags has no project filter on the backend at all yet",
  },

  // ── global: addressed by id (already unique) or genuinely project-free ──
  memory: { kind: "global", reason: "addressed by id, which already determines the row" },
  memoryContext: {
    kind: "global",
    reason: "GET /graph/memory-context/{id} takes no project param; addressed by id",
  },
  projects: {
    kind: "global",
    reason:
      "GET /api/v1/projects IS the scope catalog the switcher reads — scoping it by the active project would leave the switcher able to offer only the scope you are already in",
  },
  fullGraph: { kind: "global" },
  graphEntities: { kind: "global" },
  vectorProjection: { kind: "global" },
  knowledgeEntities: { kind: "global" },
  knowledgeTimeline: { kind: "global" },
  jobs: { kind: "global" },
  llmConfig: { kind: "global" },
  llmProviders: {
    kind: "global",
    reason:
      "an llm_providers connection row is per-installation, the same as the llm_purpose_configs rows it feeds",
  },
  featureFlags: { kind: "global" },
  repoAllowlist: { kind: "global" },
  verificationLadder: {
    kind: "global",
    reason:
      "the corroboration promotion gate's thresholds are one per-installation config row, the same as the feature flags beside it",
  },
  classificationAreas: { kind: "global" },
  systemPrompts: { kind: "global" },
  notifications: { kind: "global" },
  auditLog: { kind: "global" },
  conversations: { kind: "global" },
  conversation: { kind: "global" },
  stats: { kind: "global" },
  health: { kind: "global" },
  pipeline: { kind: "global" },
  pipelineLogs: { kind: "global" },
  overview: { kind: "global" },
  pipelineFailures: { kind: "global" },
  pipelineFailureCounts: { kind: "global" },
  retryBatchProgress: { kind: "global" },
  obsoleteCounts: { kind: "global" },
  reembedBatchProgress: { kind: "global" },
  repoStats: { kind: "global" },
  repos: { kind: "global" },
  repoTasks: { kind: "global" },
  codeGraph: { kind: "global" },
  codeFiles: { kind: "global" },
  codeSymbols: { kind: "global" },
  codeSymbol: { kind: "global" },
  fs: { kind: "global" },
  reposPath: { kind: "global" },
}

function assertAuto(domain: string): void {
  const scope = QUERY_KEY_SCOPE[domain]
  if (!scope || scope.kind !== "auto") {
    throw new Error(
      `"${domain}" is not registered as "auto" in QUERY_KEY_SCOPE (src/lib/query-keys.ts) — ` +
        `classify it there before building a project-scoped key for it`,
    )
  }
}

/**
 * Build a project-scoped query key outside a component (mutation
 * `onSuccess` handlers, imperative cache reads). Reads the store's current
 * snapshot; for a key computed during render, prefer `useProjectScopedKey`
 * so the component re-renders — and re-keys — when the active project
 * changes.
 */
export function projectScopedKey(
  domain: string,
  ...rest: readonly unknown[]
): readonly unknown[] {
  assertAuto(domain)
  return [domain, useProjectStore.getState().activeProject, ...rest]
}

/**
 * The reactive form: subscribes to the active project, so a query key
 * built with this hook changes on the same render the switcher changes it
 * — the point of Ruling 2, a project switch must never leave a mounted
 * view reading the old project's cache entry.
 */
export function useProjectScopedKey(
  domain: string,
  ...rest: readonly unknown[]
): readonly unknown[] {
  assertAuto(domain)
  const project = useProjectStore((s) => s.activeProject)
  return [domain, project, ...rest]
}

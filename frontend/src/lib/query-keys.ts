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
  // The pipeline journals each run under its memory's project.
  pipelineLogs: { kind: "auto" },
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
      "Distribution config is per-installation, not per-project: the adapter registry maps a tool to a file path for every project at once (doc 13 §6.5), so scoping it to a project would imply a per-project mapping that does not exist",
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
  documentsAll: {
    kind: "manual",
    reason:
      "The workspace's stitched full list takes the project as an explicit argument (the route param, not the global switcher), the same posture `documents` carries; it pages the same route until a short page and dedupes by id (review m1)",
  },
  worklogWorkstreams: {
    kind: "manual",
    reason:
      "GET /worklog/workstreams requires an explicit `project`; the Work log passes the workspace's route param and the Activity list passes each project it enumerates, never the global switcher",
  },
  worklogEntries: {
    kind: "global",
    reason:
      "Addressed by workstream id and carrying no project param, the same shape as documentBlocks",
  },
  worklogLedgerAll: {
    kind: "global",
    reason:
      "Every ledger entry of one workstream, addressed by workstream id like worklogEntries",
  },
  boardRecords: {
    kind: "manual",
    reason:
      "GET /board/records requires an explicit `project`; the Progress tab passes the workspace's route param",
  },
  boardViews: {
    kind: "manual",
    reason:
      "GET /board/views requires an explicit `project`; the Progress tab passes the workspace's route param",
  },
  worklogResume: {
    kind: "manual",
    reason:
      "GET /worklog/resume takes an explicit `project` and workstream key, supplied per row by the Activity list",
  },
  documentOutline: {
    kind: "global",
    reason:
      "Addressed by document id and carrying no project param, exactly like documentSummary: the document's own project scopes the read server-side, so a project-keyed cache entry would key on something the request never sends",
  },
  documentBlocks: {
    kind: "global",
    reason:
      "Addressed by document id and carrying no project param — the same shape as documentOutline, and the read the block reader and increment 8's editor both share",
  },
  documentRevisions: {
    kind: "global",
    reason:
      "Addressed by document id and carrying no project param, the same shape as documentBlocks",
  },
  documentRevision: {
    kind: "global",
    reason:
      "Addressed by document id and revision id; the same shape as documentRevisions",
  },
  documentContents: {
    kind: "global",
    reason:
      "Addressed by document ids and carrying no project param, the same shape as documentBlocks. The key is the sorted id list rather than one id: the Progress board reads nine documents at once, and a hook per document would mean a variable number of hooks",
  },
  documentRelatedMemories: {
    kind: "global",
    reason:
      "Addressed by document id and carrying no project param, the same shape as documentConnections: the read picks the newest shared fingerprint out of the data (never the active one — resolving that is an embed call a test forbids by name) and derives the document's own project server-side, so a project-keyed cache entry would key on something the request never sends",
  },
  documentSummary: {
    kind: "global",
    reason:
      "Addressed by document id and carrying no project param: the document's own project is what scopes the read server-side, so a project-keyed cache entry would key on something the request does not send",
  },
  documentConnections: {
    kind: "global",
    reason:
      "Addressed by document id, and the passage-similarity query scopes itself to that document's project and to a fingerprint both sides hold vectors under — picked from the data, never the active embedder, which the read is forbidden to resolve. Deliberate on both counts: a cross-project suggestion surface is the worst place to leak an isolation boundary, and a cross-fingerprint cosine has no defined meaning",
  },
  pages: {
    kind: "manual",
    reason:
      "GET /pages takes an explicit `project` the notes workspace supplies (resolved from the catalogue by kind, not from the global switcher), the same posture `documents` carries",
  },
  page: {
    kind: "global",
    reason:
      "Addressed by page id and carrying no project param, the same shape as documentBlocks: the page's own project scopes the read server-side, so a project-keyed cache entry would key on something the request never sends",
  },
  pagesTrash: {
    kind: "manual",
    reason:
      "GET /pages/trash takes an explicit `project`, the same posture `pages` carries; the notes workspace is the only caller and it is pinned to the personal project",
  },

  backupDestinations: {
    kind: "global",
    reason:
      "Where this whole instance ships its own encrypted snapshots. A snapshot is the entire database, so there is no per-project destination to express and never will be -- scoping this would imply backups a project could own, which the artefact cannot represent (increment 6, spec §9.3)",
  },
  backupInventory: {
    kind: "global",
    reason:
      "The same instance-wide artefacts read back: filenames, sizes and a per-destination verification badge. It enumerates what each destination holds, which is a property of the box rather than of any project in it (increment 7, spec §9.6)",
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
  overview: { kind: "global" },
  pipelineFailures: { kind: "global" },
  pipelineFailureCounts: { kind: "global" },
  memoryBuffer: {
    kind: "global",
    reason:
      "the failed-capture triage queue spans every project, and each row names its own",
  },
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
  setupProbe: { kind: "global" },
  usage: {
    kind: "global",
    reason:
      "Deliberately unscoped, not an unwired switcher. Most spend carries no project at all -- a job run, a maintenance sweep and a mixed-project batch embed all write project NULL -- so a page-wide project filter would silently drop exactly the categories a cost review is looking for, and the remaining total would read as the whole bill. The hooks still take an optional `project` for drilling into one project's ingest spend, which is why it rides the key",
  },
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

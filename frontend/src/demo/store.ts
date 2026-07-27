import { create } from "zustand"
import memoriesData from "./data/memories.json"
import reposData from "./data/repos.json"
import jobsData from "./data/jobs.json"
import { CURATED_MEMORIES } from "./data/memories-curated"
import {
  CURATED_ARTICLES,
  CURATED_COMMUNITIES,
  CURATED_FACTS,
  CURATED_HYGIENE,
  CURATED_PIN_SUGGESTIONS,
  CURATED_REVIEW_ITEMS,
  LAST_DETECTION_RUN,
} from "./data/knowledge-curated"
import { CURATED_CODE_GRAPHS, CURATED_CODE_REPOS } from "./data/code-curated"
import { CURATED_MEMORY_GRAPH } from "./data/memory-graph-curated"
import {
  CURATED_CHAT_THREADS,
  DEMO_REPLY_CONTENT,
  DEMO_REPLY_CONTEXT,
} from "./data/chat-curated"
import {
  CURATED_BUFFER_MONITOR,
  CURATED_DAY_BUCKETS,
  CURATED_DREAM_ACTIONS,
  CURATED_DREAM_CYCLE,
  CURATED_DREAM_MONITOR,
  CURATED_DREAM_PAST_ACTIONS,
  CURATED_FEED_EVENTS,
  CURATED_PIPELINE_FAILURES,
  CURATED_PIPELINE_RUNS,
  CURATED_SESSION_RUNS,
} from "./data/activity-curated"
import {
  CURATED_CODE_BUCKETS,
  CURATED_DISTRIBUTION,
  CURATED_FLAGS,
  CURATED_LLM_PURPOSES,
  CURATED_MAINTENANCE,
  CURATED_SECURITY,
} from "./data/settings-curated"
import { enrichBulkMemories, type RawBulkMemory } from "./memories"
import { buildReindexPhases } from "./explore"
import { liveArticles } from "./knowledge"
import {
  buildActivityFeed,
  buildContributions,
  buildDashboardStats,
} from "./dashboard"
import type {
  DemoStoreState,
  DemoMemory,
  DemoFact,
  DemoArticle,
  DemoChatThread,
  DemoFlagsState,
  DemoJob,
  DemoRankArm,
  MaintenanceOpKey,
  Repo,
} from "./types"

const initialMemories: DemoMemory[] = [
  ...CURATED_MEMORIES,
  ...enrichBulkMemories(memoriesData as RawBulkMemory[]),
]

// Deep-copy the knowledge fixtures so store mutations (ratify, hygiene
// bulk actions) never write back into the module-level curated constants.
const initialKnowledge = () => ({
  facts: CURATED_FACTS.map((f) => ({ ...f })),
  articles: CURATED_ARTICLES.map((a) => ({ ...a })),
  communities: CURATED_COMMUNITIES.map((c) => ({ ...c })),
  pinSuggestions: CURATED_PIN_SUGGESTIONS.map((p) => ({ ...p })),
  reviewItems: CURATED_REVIEW_ITEMS.map((r) => ({ ...r })),
  hygiene: {
    duplicates: [...CURATED_HYGIENE.duplicates],
    lowConfidence: [...CURATED_HYGIENE.lowConfidence],
    expiring: [...CURATED_HYGIENE.expiring],
    lineage: [...CURATED_HYGIENE.lineage],
  },
})

const initialStats = {
  ...buildDashboardStats(initialMemories.length),
  verifiedFacts: CURATED_FACTS.filter(
    (f) =>
      f.verification_status === "corroborated" ||
      f.verification_status === "confirmed",
  ).length,
  liveArticles: liveArticles(CURATED_ARTICLES, "all").length,
  pendingReview: CURATED_REVIEW_ITEMS.length,
  disputedFacts: CURATED_FACTS.filter(
    (f) => f.verification_status === "disputed",
  ).length,
}

const ratifyFact = (fact: DemoFact, by: string, on: string): DemoFact => ({
  ...fact,
  verification_status: "confirmed",
  claim: `human-ratified by ${by} on ${on}; the pre-ratification record remains below`,
  meta: `ratified by ${by}, ${on}`,
  review_state: null,
  ratified: { by, on },
  sources: [
    ...fact.sources,
    {
      origin_key: `human:${by}`,
      kind: "human" as const,
      ref: `human ${by}`,
      detail:
        "ratified via the Review queue — the ratification wrote this human-kind fact_source (who / when / what-was-shown)",
      at: `ratified ${on}`,
    },
  ],
  ladder: [
    ...fact.ladder,
    {
      at: on,
      description: `ratified by ${by} — the human origin was written as a fact_source`,
      transition: { from: fact.verification_status, to: "confirmed" },
      note: "only a human ratify reaches confirmed; the machine ceiling is corroborated",
    },
  ],
})

const ratifyArticle = (article: DemoArticle, by: string, on: string): DemoArticle => ({
  ...article,
  verification_status: "confirmed",
  claim: `human-ratified by ${by} on ${on}`,
  meta: `ratified ${on}`,
  review_state: null,
  ungrounded_note: undefined,
})

const RATIFY_DATE = "2026-07-25"

// Deep-copy the activity fixtures so store mutations (retry, trigger, undo)
// never write back into the module-level curated constants.
const initialActivity = () => ({
  pipelineRuns: CURATED_PIPELINE_RUNS.map((r) => ({ ...r })),
  feedEvents: CURATED_FEED_EVENTS.map((e) => ({ ...e })),
  pipelineFailures: CURATED_PIPELINE_FAILURES.map((f) => ({ ...f })),
  jobs: (jobsData as unknown as DemoJob[]).map((j) => ({
    ...j,
    config_schema: j.config_schema.map((f) => ({ ...f })),
  })),
  bufferMonitor: structuredClone(CURATED_BUFFER_MONITOR),
  dreamMonitor: CURATED_DREAM_MONITOR,
  dreamCycle: CURATED_DREAM_CYCLE,
  dreamActions: CURATED_DREAM_ACTIONS.map((a) => ({ ...a })),
  dreamPastActions: CURATED_DREAM_PAST_ACTIONS.map((a) => ({ ...a })),
  dayBuckets: CURATED_DAY_BUCKETS,
  sessionRuns: CURATED_SESSION_RUNS,
})

// Deep-copy the Wave-5 settings fixtures so store mutations (arm writes,
// curbs, maintenance ops) never write back into the curated constants.
const initialSettings = () => ({
  flags: structuredClone(CURATED_FLAGS),
  llm: {
    purposes: structuredClone(CURATED_LLM_PURPOSES),
    buckets: structuredClone(CURATED_CODE_BUCKETS),
    classifier_kind: "llm" as const,
    last_save: null,
  },
  security: structuredClone(CURATED_SECURITY),
  maintenance: structuredClone(CURATED_MAINTENANCE),
  distribution: structuredClone(CURATED_DISTRIBUTION),
})

const countOverrides = (flags: DemoFlagsState): number => {
  const armOverrides = [
    ...flags.fusion_arms,
    ...flags.graph_flags.flatMap((f) => (f.paired_arm ? [f.paired_arm] : [])),
    flags.context_boost,
  ].filter((a) => a.source === "override").length
  const flagOverrides = flags.graph_flags.filter(
    (f) => f.source === "override",
  ).length
  const behavioralOverrides = flags.behavioral_flags.filter(
    (f) => f.source === "override",
  ).length
  return (
    armOverrides +
    flagOverrides +
    behavioralOverrides +
    (flags.corroboration.source === "override" ? 1 : 0)
  )
}

const writeArm = (arm: DemoRankArm, key: string, value: number): DemoRankArm =>
  arm.key === key ? { ...arm, value, source: "override" } : arm

export const useDemoStore = create<DemoStoreState>((set, get) => ({
  memories: initialMemories,
  repos: reposData as unknown as Repo[],
  ...initialActivity(),
  ...initialSettings(),
  stats: initialStats,
  events: buildActivityFeed(),
  contributions: buildContributions(initialMemories),
  ...initialKnowledge(),
  lastDetectionRun: LAST_DETECTION_RUN,
  // Deep-copy so reindex mutations never write back into the fixtures.
  codeRepos: CURATED_CODE_REPOS.map((r) => ({ ...r })),
  codeGraphs: CURATED_CODE_GRAPHS,
  memoryGraph: CURATED_MEMORY_GRAPH,
  chatThreads: CURATED_CHAT_THREADS.map((t) => ({
    ...t,
    messages: [...t.messages],
  })),
  addMemory: (m) =>
    set((s) => ({
      memories: [m, ...s.memories],
      stats: { ...s.stats, totalMemories: s.memories.length + 1 },
    })),
  updateMemory: (id, patch) =>
    set((s) => ({
      memories: s.memories.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    })),
  deleteMemory: (id) =>
    set((s) => {
      const memories = s.memories.filter((x) => x.id !== id)
      return {
        memories,
        stats: { ...s.stats, totalMemories: memories.length },
      }
    }),
  resetMemories: () =>
    set((s) => ({
      memories: initialMemories,
      stats: { ...s.stats, totalMemories: initialMemories.length },
    })),
  ratifyReviewItem: (id, ratifiedBy) =>
    set((s) => {
      const item = s.reviewItems.find((r) => r.id === id)
      if (!item) return s
      return {
        reviewItems: s.reviewItems.filter((r) => r.id !== id),
        stats: { ...s.stats, pendingReview: s.stats.pendingReview - 1 },
        facts:
          item.kind === "fact"
            ? s.facts.map((f) =>
                f.id === item.target_id
                  ? ratifyFact(f, ratifiedBy, RATIFY_DATE)
                  : f,
              )
            : s.facts,
        articles:
          item.kind === "article"
            ? s.articles.map((a) =>
                a.id === item.target_id
                  ? ratifyArticle(a, ratifiedBy, RATIFY_DATE)
                  : a,
              )
            : s.articles,
      }
    }),
  regroundReviewItem: (id) =>
    set((s) => ({
      reviewItems: s.reviewItems.map((r) =>
        r.id === id ? { ...r, reground_queued: true } : r,
      ),
    })),
  clearReviewItem: (id) =>
    set((s) => {
      const item = s.reviewItems.find((r) => r.id === id)
      if (!item) return s
      return {
        reviewItems: s.reviewItems.filter((r) => r.id !== id),
        stats: { ...s.stats, pendingReview: s.stats.pendingReview - 1 },
      }
    }),
  decidePinSuggestion: (id, decision) =>
    set((s) => ({
      pinSuggestions: s.pinSuggestions.map((p) =>
        p.id === id ? { ...p, decision } : p,
      ),
    })),
  resolveHygiene: (category, ids) =>
    set((s) => {
      const keep = <T extends { id: string }>(items: T[]): T[] =>
        items.filter((item) => !ids.includes(item.id))
      const h = s.hygiene
      return {
        hygiene: {
          duplicates:
            category === "duplicates" ? keep(h.duplicates) : h.duplicates,
          lowConfidence:
            category === "lowConfidence"
              ? keep(h.lowConfidence)
              : h.lowConfidence,
          expiring: category === "expiring" ? keep(h.expiring) : h.expiring,
          lineage: category === "lineage" ? keep(h.lineage) : h.lineage,
        },
      }
    }),
  resetKnowledge: () =>
    set(() => ({ ...initialKnowledge(), stats: initialStats })),
  triggerReindex: (repoId, opts) =>
    set((s) => ({
      codeRepos: s.codeRepos.map((r) =>
        r.id === repoId
          ? {
              ...r,
              status: "indexing" as const,
              phases: buildReindexPhases(opts),
              stale: null,
              error: null,
              registered_note: null,
            }
          : r,
      ),
    })),
  sendChatMessage: (threadId, content) => {
    const state = useDemoStore.getState()
    const existing = threadId
      ? state.chatThreads.find((t) => t.id === threadId)
      : undefined
    const target: DemoChatThread = existing ?? {
      id: `thread-new-${state.chatThreads.length + 1}`,
      title: content.length > 42 ? `${content.slice(0, 42)}…` : content,
      updated_label: "just now",
      messages: [],
    }
    const n = target.messages.length
    const updated: DemoChatThread = {
      ...target,
      updated_label: "just now",
      messages: [
        ...target.messages,
        { id: `m${n + 1}`, role: "user", content },
        {
          id: `m${n + 2}`,
          role: "assistant",
          content: DEMO_REPLY_CONTENT,
          context: DEMO_REPLY_CONTEXT,
        },
      ],
    }
    set((s) => ({
      chatThreads: existing
        ? s.chatThreads.map((t) => (t.id === updated.id ? updated : t))
        : [updated, ...s.chatThreads],
    }))
    return updated.id
  },
  retryFailure: (id) =>
    set((s) => ({
      pipelineFailures: s.pipelineFailures.map((f) =>
        f.id === id ? { ...f, retry_queued: true } : f,
      ),
    })),
  retryAllFailures: () =>
    set((s) => ({
      pipelineFailures: s.pipelineFailures.map((f) => ({
        ...f,
        retry_queued: true,
      })),
    })),
  forgetFailure: (id) =>
    set((s) => ({
      pipelineFailures: s.pipelineFailures.filter((f) => f.id !== id),
    })),
  retryBufferRow: (id) =>
    set((s) => ({
      bufferMonitor: {
        ...s.bufferMonitor,
        target: {
          ...s.bufferMonitor.target,
          error: Math.max(0, s.bufferMonitor.target.error - 1),
          pending: s.bufferMonitor.target.pending + 1,
          poisonRows: s.bufferMonitor.target.poisonRows.filter(
            (r) => r.id !== id,
          ),
        },
      },
    })),
  forgetBufferRow: (id) =>
    set((s) => ({
      bufferMonitor: {
        ...s.bufferMonitor,
        target: {
          ...s.bufferMonitor.target,
          error: Math.max(0, s.bufferMonitor.target.error - 1),
          poisonRows: s.bufferMonitor.target.poisonRows.filter(
            (r) => r.id !== id,
          ),
        },
      },
    })),
  triggerJob: (key) => {
    const job = get().jobs.find((j) => j.key === key)
    if (!job) return { ok: false, status: 409, lock_held_since: "unknown" }
    if (job.running) {
      return {
        ok: false,
        status: 409,
        lock_held_since: job.lock_held_since ?? "just now",
      }
    }
    set((s) => ({
      jobs: s.jobs.map((j) =>
        j.key === key
          ? {
              ...j,
              last_run_label: "just now (manual)",
              last_status: "ok" as const,
              last_summary: "ok — manual trigger completed",
            }
          : j,
      ),
    }))
    return { ok: true }
  },
  saveJobConfig: (key, values) =>
    set((s) => ({
      jobs: s.jobs.map((j) =>
        j.key === key
          ? {
              ...j,
              config_schema: j.config_schema.map((f) =>
                values[f.key] !== undefined
                  ? { ...f, value: values[f.key] as number }
                  : f,
              ),
            }
          : j,
      ),
    })),
  undoDreamAction: (id) =>
    set((s) => ({
      dreamActions: s.dreamActions.map((a) =>
        a.id === id && !a.undo_blocked && !a.undone
          ? { ...a, undone: true }
          : a,
      ),
    })),
  undoDreamBatch: (type) =>
    set((s) => ({
      dreamActions: s.dreamActions.map((a) =>
        a.type === type && !a.undo_blocked && !a.undone
          ? { ...a, undone: true }
          : a,
      ),
    })),
  resetActivity: () => set(() => initialActivity()),
  saveArm: (key, value) =>
    set((s) => {
      const flags: DemoFlagsState = {
        ...s.flags,
        fusion_arms: s.flags.fusion_arms.map((a) => writeArm(a, key, value)),
        graph_flags: s.flags.graph_flags.map((f) =>
          f.paired_arm
            ? { ...f, paired_arm: writeArm(f.paired_arm, key, value) }
            : f,
        ),
        context_boost: writeArm(s.flags.context_boost, key, value),
      }
      return { flags: { ...flags, overrides_written: countOverrides(flags) } }
    }),
  setGraphFlag: (key, enabled) =>
    set((s) => {
      const flags: DemoFlagsState = {
        ...s.flags,
        graph_flags: s.flags.graph_flags.map((f) =>
          f.key === key ? { ...f, enabled, source: "override" } : f,
        ),
      }
      return { flags: { ...flags, overrides_written: countOverrides(flags) } }
    }),
  saveCorroboration: (nBase, nDiverse) =>
    set((s) => {
      const flags: DemoFlagsState = {
        ...s.flags,
        corroboration: {
          ...s.flags.corroboration,
          n_base: nBase,
          n_diverse: nDiverse,
          source: "override",
        },
      }
      return { flags: { ...flags, overrides_written: countOverrides(flags) } }
    }),
  setBehavioralFlag: (key, enabled) =>
    set((s) => {
      const flags: DemoFlagsState = {
        ...s.flags,
        behavioral_flags: s.flags.behavioral_flags.map((f) =>
          f.key === key ? { ...f, enabled, source: "override" } : f,
        ),
      }
      return { flags: { ...flags, overrides_written: countOverrides(flags) } }
    }),
  saveRepoAllowlist: (patterns) =>
    set((s) => ({
      flags: { ...s.flags, repo_allowlist: { patterns } },
    })),
  saveLLMPurpose: (purpose, patch) =>
    set((s) => ({
      llm: {
        ...s.llm,
        purposes: s.llm.purposes.map((p) =>
          p.purpose === purpose ? { ...p, ...patch } : p,
        ),
        last_save: { purpose, fields: Object.keys(patch) },
      },
    })),
  saveCodeBucket: (key, model) =>
    set((s) => ({
      llm: {
        ...s.llm,
        buckets: s.llm.buckets.map((b) =>
          b.key === key ? { ...b, model } : b,
        ),
        last_save: { purpose: "summarization", fields: [`bucket:${key}`] },
      },
    })),
  setClassifierKind: (kind) =>
    set((s) => ({
      llm: {
        ...s.llm,
        classifier_kind: kind,
        last_save: { purpose: "classification", fields: ["classifier_kind"] },
      },
    })),
  dismissLLMSave: () => set((s) => ({ llm: { ...s.llm, last_save: null } })),
  setJobEnabled: (key, enabled) =>
    set((s) => ({
      jobs: s.jobs.map((j) => (j.key === key ? { ...j, enabled } : j)),
    })),
  saveJobCron: (key, cron) =>
    set((s) => ({
      jobs: s.jobs.map((j) =>
        j.key === key ? { ...j, cron, cron_label: "saved this session" } : j,
      ),
    })),
  runMaintenanceOp: (op: MaintenanceOpKey) =>
    set((s) => {
      const m = s.maintenance
      switch (op) {
        case "reembed_memories":
          return {
            maintenance: {
              ...m,
              reembed: { ...m.reembed, memories: 0 },
              last_op_note: `re-embed memories started — ${m.reembed.memories} embedding calls dispatched (POST returned 202)`,
            },
          }
        case "reembed_entities":
          return {
            maintenance: {
              ...m,
              reembed: { ...m.reembed, entities: 0 },
              last_op_note: `re-embed entities started — ${m.reembed.entities} embedding calls dispatched (POST returned 202)`,
            },
          }
        case "expired_memory_cleanup":
          return {
            maintenance: {
              ...m,
              cleanup: { ...m.cleanup, expired: 0, expired_dependents: 0 },
              last_op_note: `${m.cleanup.expired} expired memories deleted; ${m.cleanup.expired_dependents} dependents demoted to deprecated first (chk_superseded_has_pointer)`,
            },
          }
        case "graph_orphan_cleanup":
          return {
            maintenance: {
              ...m,
              last_op_note:
                "graph_orphan_cleanup ran now — the same job the hourly schedule already runs",
            },
          }
        case "tag_orphan_cleanup":
          return {
            maintenance: {
              ...m,
              last_op_note:
                "tag_orphan_cleanup ran now — the same job the hourly schedule already runs",
            },
          }
        case "prune_caches":
          return {
            maintenance: {
              ...m,
              dbops: { ...m.dbops, retired_fingerprints: [] },
              last_op_note: `${m.dbops.retired_fingerprints.length} retired cache tables dropped — each rebuilds lazily on next use of its embedder`,
            },
          }
      }
    }),
  setDistributionCurb: (clientId, curbed) =>
    set((s) => {
      const d = s.distribution
      const clients = d.clients.map((c) => {
        if (c.id !== clientId) return c
        return curbed
          ? {
              ...c,
              status: "curbed" as const,
              push_note: "curbed by operator, just now",
              curbed_note:
                "Pull (MCP tools) is unaffected — only push stopped. The managed block was rewritten to an empty marker pair, not removed; re-enabling resumes idempotently.",
            }
          : {
              ...c,
              status: "connected" as const,
              push_note: "active — awaiting the next session-start inject",
              curbed_note: null,
            }
      })
      const log = curbed
        ? [
            {
              id: `log-curb-${d.log.length + 1}`,
              target: clientId,
              event_type: "inject_curbed" as const,
              detail: "push disabled by operator (this demo session)",
              time_label: "just now",
              meta: "block → empty markers",
            },
            ...d.log,
          ]
        : d.log
      return { distribution: { ...d, clients, log } }
    }),
  resetSettings: () => set(() => initialSettings()),
}))

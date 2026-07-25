import { create } from "zustand"
import memoriesData from "./data/memories.json"
import reposData from "./data/repos.json"
import jobsData from "./data/jobs.json"
import llmProfilesData from "./data/llm-profiles.json"
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
import { enrichBulkMemories, type RawBulkMemory } from "./memories"
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
  Repo,
  Job,
  LlmProfile,
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

export const useDemoStore = create<DemoStoreState>((set) => ({
  memories: initialMemories,
  repos: reposData as unknown as Repo[],
  jobs: jobsData as unknown as Job[],
  llmProfiles: llmProfilesData as unknown as LlmProfile[],
  stats: initialStats,
  events: buildActivityFeed(),
  contributions: buildContributions(),
  ...initialKnowledge(),
  lastDetectionRun: LAST_DETECTION_RUN,
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
}))

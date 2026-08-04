import type { ExclusionItem } from "@/components/darkmem"
import type { KnowledgeLayer, VerificationStatus } from "@/components/darkmem"
import type { MemoryStatus } from "@/hooks/api"
import {
  EXCLUSION_CAVEAT,
  traceToView,
  type MemoryTraceView,
} from "@/features/memories/use-memory-search"

/**
 * The shapes a chat turn's retrieval arrives in, and the adapters that turn
 * them into what the shared honesty components render.
 *
 * Chat retrieves through the same composition the search surface does (T2.58),
 * so the trace it renders is built with the **same** adapter Memories uses:
 * `traceToView` writes the "why it ranked" sentence once, and a chat-local
 * copy of it would be a second explanation of one ranking, drifting exactly
 * where the two disagreed about what the numbers mean.
 */

export interface ChatChannelStatus {
  ran: boolean
  failed: boolean
}

export interface ChatRetrievalEnvelope {
  query: string
  channels: Record<string, ChatChannelStatus>
  reranked: boolean
  weights: Record<string, number>
  excluded: Record<string, number>
  /** Computed server-side: any channel that ran and failed. */
  partial: boolean
}

export interface ChatRowScores {
  semantic?: number | null
  keyword?: number | null
  name?: number | null
  rrf_score?: number | null
  rerank_score?: number | null
}

export interface ChatContextRow {
  id?: string
  index?: number
  content?: string
  source?: string
  tags?: string[]
  created_at?: string
  status?: MemoryStatus
  project?: string
  layer?: string
  score?: number
  scores?: ChatRowScores
  rank_fusion_factor?: number
  channel_rank?: number
  /** The id of the fact this memory sources, when the composition nested it. */
  grouped_under?: string | null
}

export interface ChatContextFact {
  id: string
  index?: number
  text: string
  layer?: string
  verification_status?: VerificationStatus | null
  /** Doc 12 §4's badge. `claim` is shown verbatim or not at all. */
  badge?: { claim: string } | null
  score?: number
  scores?: ChatRowScores
  rank_fusion_factor?: number
  supports?: string[]
}

// Human copy for the counts the composed envelope actually carries. Distinct
// from the Memories surface's schema-v2 reasons: those name a filter applied
// after the fusion, these name the composition's own two tallies plus the
// re-read gap chat counts for itself.
const EXCLUSION_COPY: Record<string, string> = {
  by_context_conflict:
    "conflicted with the context declared for this turn, so it was left out of the answer",
  by_result_limit:
    "ranked below this turn's context budget — composed and ordered, but not sent to the model",
  not_found: "ranked, then could not be re-read before the answer was built",
}

export const CHAT_EXCLUSION_CAVEAT = EXCLUSION_CAVEAT

export function layerNumber(layer: string | undefined): KnowledgeLayer {
  const parsed = Number((layer ?? "L0").replace(/^L/, ""))
  return (parsed === 2 || parsed === 3 || parsed === 1 ? parsed : 0) as KnowledgeLayer
}

/** The turn-level header: which channels the composition asked, and how each fared. */
export function channelStates(
  envelope: ChatRetrievalEnvelope | null | undefined,
): { name: string; state: "ok" | "failed" | "not asked" }[] {
  if (!envelope) return []
  return Object.entries(envelope.channels).map(([name, status]) => ({
    name,
    state: status.failed ? "failed" : status.ran ? "ok" : "not asked",
  }))
}

export function exclusionItems(
  envelope: ChatRetrievalEnvelope | null | undefined,
): ExclusionItem[] {
  if (!envelope) return []
  return Object.entries(envelope.excluded)
    .filter(([, count]) => count > 0)
    .map(([reason, count]) => ({
      count,
      unit: count === 1 ? "row" : "rows",
      reason: EXCLUSION_COPY[reason] ?? `excluded — ${reason}`,
      tag: reason,
    }))
}

/** `undefined` when the row carries no breakdown — never a fabricated one. */
export function rowTrace(
  row: { scores?: ChatRowScores; rank_fusion_factor?: number },
): MemoryTraceView | undefined {
  if (!row.scores) return undefined
  return traceToView({
    scores: row.scores as Record<string, number | null>,
    rank_fusion_factor: row.rank_fusion_factor ?? 1,
    rank_fusion_breakdown: {},
  })
}

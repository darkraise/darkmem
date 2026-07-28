import type { DemoMemory } from "@/features/memories/types"

// Timestamps are relative to load time so the curated rows surface at the
// top of the recency-ordered browse view alongside the generated bulk rows.
const NOW = Date.now()
const MINUTE = 60_000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

const ago = (ms: number) => new Date(NOW - ms).toISOString()

const ID_RERANK_TOP40 = "a1b2c3d4-9e0f-4a1b-8c2d-3e4f5a6b7c8d"
const ID_RERANK_FULL_LIST = "b7e2f001-2a3b-4c4d-8e5f-6a7b8c9d0e1f"
const ID_CACHE_PRUNE = "d4f9a112-3b4c-4d5e-8f6a-7b8c9d0e1f2a"
const ID_HYBRID_K60 = "5c81e0f2-4c5d-4e6f-8a7b-8c9d0e1f2a3b"
const ID_RERANKER_FLAG = "902fbb14-5d6e-4f7a-8b8c-9d0e1f2a3b4c"
const ID_GAMMA_ORDER = "33ad61c7-6e7f-4a8b-8c9d-0e1f2a3b4c5d"
const ID_SEMANTIC_WEIGHT = "771e4f9a-7f8a-4b9c-8d0e-1f2a3b4c5d6e"
const ID_COOKIE_LAN = "c93f7a12-8a9b-4c0d-8e1f-2a3b4c5d6e7f"
const ID_TRUST_PROXY = "71b0d5e6-9b0c-4d1e-8f2a-3b4c5d6e7f8a"
const ID_CHUNKING_IDEA = "e5a8c320-0c1d-4e2f-8a3b-4c5d6e7f8a9b"

export const CURATED_IDS = {
  rerankTop40: ID_RERANK_TOP40,
  rerankFullList: ID_RERANK_FULL_LIST,
  cachePrune: ID_CACHE_PRUNE,
  cookieLan: ID_COOKIE_LAN,
} as const

const base = {
  source: "mcp",
  source_agent: null,
  importance: 5,
  metadata: {},
  updated_at: ago(2 * HOUR),
  expires_at: null,
  is_archived: false,
  project: "darkmem",
  layer: 0 as const,
}

export const CURATED_MEMORIES: DemoMemory[] = [
  {
    ...base,
    id: ID_RERANK_TOP40,
    content:
      "RerankerService LLM-scores the top 40 RRF-ranked rows on a 0–10 scale; the unscored tail past rank 40 is appended in its original RRF order, never re-ranked.",
    memory_type: "fact",
    classified_type: "fact",
    summary:
      "Reranking only touches the top 40 fused rows — anything ranked below 40 keeps its RRF-computed order.",
    emotions: ["neutral"],
    flags: [],
    technologies: ["reranker", "rrf", "hybrid-search"],
    tags: ["retrieval", "reranker"],
    confidence: 0.82,
    status: "active",
    created_at: ago(2 * HOUR),
    verification_status: "corroborated",
    verification_detail:
      "supports a fact asserted by 3 distinct origins of kinds [code, memory], no known contradiction",
    relations: [
      {
        rel_type: "CONTRADICTS",
        memory_id: ID_RERANK_FULL_LIST,
        excerpt: "the reranker scores every fused row, not just the top 40",
      },
      {
        rel_type: "ELABORATES",
        memory_id: ID_HYBRID_K60,
        excerpt: "hybrid_search_enabled defaults on; RRF fusion runs k=60",
      },
      {
        rel_type: "DEPENDS_ON",
        memory_id: ID_RERANKER_FLAG,
        excerpt: "reranker_enabled flag gates whether RerankerService runs at all",
      },
      {
        rel_type: "FOLLOWS",
        memory_id: ID_GAMMA_ORDER,
        excerpt:
          "confidence_rank_gamma weighting runs before rerank, preserve_order=True after",
      },
      {
        rel_type: "RELATES_TO",
        memory_id: ID_SEMANTIC_WEIGHT,
        excerpt: "semantic_weight defaults to 0.7 in the RRF fusion formula",
      },
    ],
    timeline: [
      {
        at: ago(2 * HOUR),
        kind: "created",
        description: "object: this memory",
        note: "captured via mcp",
      },
      {
        at: ago(2 * HOUR - MINUTE),
        kind: "extracted",
        description: "object: this memory",
        note: "classified_type set to fact (single-call merge with extraction)",
      },
      {
        at: ago(90 * MINUTE),
        kind: "extracted",
        description: `object: this memory — RELATES_TO → memory ${ID_SEMANTIC_WEIGHT.slice(0, 8)}`,
        note: '"semantic_weight defaults to 0.7 in the RRF fusion formula"',
      },
      {
        at: ago(50 * MINUTE),
        kind: "verified",
        description:
          'object: fact — "the top-40 rerank cutoff is a latency/quality tradeoff"',
        note: "this memory became one of the distinct origins corroborating the fact",
        transition: { from: "candidate", to: "corroborated" },
      },
    ],
  },
  {
    ...base,
    id: ID_RERANK_FULL_LIST,
    content:
      "The reranker previously scored the full RRF list (all fused rows) before the top-40 cutoff was introduced.",
    memory_type: "fact",
    classified_type: "fact",
    summary:
      "Legacy behavior: full-list reranking, since replaced by the top-40 cutoff.",
    emotions: ["neutral"],
    flags: ["stale-claim"],
    technologies: ["reranker", "rrf"],
    tags: ["retrieval", "reranker"],
    confidence: 0.6,
    status: "superseded",
    superseded_by: ID_RERANK_TOP40,
    created_at: ago(38 * DAY),
    timeline: [
      {
        at: ago(38 * DAY),
        kind: "created",
        description: "object: this memory",
        note: "captured via mcp",
      },
      {
        at: ago(50 * MINUTE),
        kind: "superseded",
        description: "object: this memory",
        note: "status and superseded_by written atomically, per chk_superseded_has_pointer",
        transition: { from: null, to: "superseded" },
      },
    ],
  },
  {
    ...base,
    id: ID_CACHE_PRUNE,
    content:
      "Entity-embedding cache invalidates per fingerprint rotation; old rows are pruned nightly.",
    memory_type: "fact",
    classified_type: "fact",
    summary:
      "Early note on cache pruning cadence, since superseded and then orphaned.",
    emotions: ["neutral"],
    flags: [],
    technologies: ["pgvector", "entity-embedding-cache"],
    tags: ["embedding", "pipeline"],
    confidence: 0.55,
    status: "deprecated",
    superseded_by: null,
    created_at: ago(85 * DAY),
    timeline: [
      {
        at: ago(85 * DAY),
        kind: "created",
        description: "object: this memory",
      },
      {
        at: ago(66 * DAY),
        kind: "superseded",
        description: "object: this memory",
        note: "superseded_by → memory e88ca241 (since deleted)",
        transition: { from: null, to: "superseded" },
      },
      {
        at: ago(10 * DAY),
        kind: "deprecated",
        description: "object: this memory",
        note: "successor deleted by expired_memory_cleanup; superseded_by cleared to satisfy chk_superseded_has_pointer",
        transition: { from: "superseded", to: "deprecated" },
      },
    ],
  },
  {
    ...base,
    id: ID_HYBRID_K60,
    content:
      "hybrid_search_enabled defaults on; RRF fusion runs k=60 weighted by semantic_weight.",
    memory_type: "fact",
    classified_type: "fact",
    summary: "Hybrid search fuses semantic and keyword ranks with RRF k=60.",
    emotions: ["neutral"],
    flags: [],
    technologies: ["hybrid-search", "rrf", "postgres"],
    tags: ["retrieval"],
    confidence: 0.8,
    status: "active",
    created_at: ago(5 * HOUR),
    relations: [
      {
        rel_type: "RELATES_TO",
        memory_id: ID_RERANK_TOP40,
        excerpt: "RerankerService LLM-scores the top 40 RRF-ranked rows",
      },
    ],
  },
  {
    ...base,
    id: ID_RERANKER_FLAG,
    content:
      "reranker_enabled flag gates whether RerankerService runs at all; the flag merges DB values over FEATURE_FLAGS_DEFAULTS.",
    memory_type: "fact",
    classified_type: "fact",
    summary: "The reranker is feature-flag gated, defaulting from config.",
    emotions: ["neutral"],
    flags: [],
    technologies: ["reranker", "feature-flags"],
    tags: ["retrieval", "config"],
    confidence: 0.78,
    status: "active",
    created_at: ago(9 * HOUR),
  },
  {
    ...base,
    id: ID_GAMMA_ORDER,
    content:
      "confidence_rank_gamma weighting runs before rerank; after a rerank it runs with preserve_order=True, rescaling scores without reordering.",
    memory_type: "fact",
    classified_type: "fact",
    summary:
      "Confidence weighting never reorders an already-reranked list.",
    emotions: ["neutral"],
    flags: [],
    technologies: ["reranker", "hybrid-search"],
    tags: ["retrieval"],
    confidence: 0.76,
    status: "active",
    created_at: ago(12 * HOUR),
  },
  {
    ...base,
    id: ID_SEMANTIC_WEIGHT,
    content:
      "semantic_weight defaults to 0.7 in the RRF fusion formula; the keyword side carries the remaining 0.3.",
    memory_type: "fact",
    classified_type: "fact",
    summary: "RRF fusion weights semantic 0.7 / keyword 0.3 by default.",
    emotions: ["neutral"],
    flags: [],
    technologies: ["hybrid-search", "rrf"],
    tags: ["retrieval"],
    confidence: 0.81,
    status: "active",
    created_at: ago(16 * HOUR),
    relations: [
      {
        rel_type: "RELATES_TO",
        memory_id: ID_RERANK_TOP40,
        excerpt: "RerankerService LLM-scores the top 40 RRF-ranked rows",
      },
    ],
  },
  {
    ...base,
    id: ID_COOKIE_LAN,
    content:
      "COOKIE_SECURE=false unblocks plain-HTTP LAN logins for the LXC deploy — dev-only; production keeps the Secure flag.",
    memory_type: "fact",
    classified_type: "fact",
    summary: "Explicit COOKIE_SECURE=false allows login over plain-HTTP LAN.",
    emotions: ["neutral"],
    flags: [],
    technologies: ["cookie-secure", "nginx"],
    tags: ["auth", "deploy"],
    confidence: 0.74,
    status: "active",
    created_at: ago(1 * DAY),
    applies_when: "env=dev",
  },
  {
    ...base,
    id: ID_TRUST_PROXY,
    content:
      "trust_proxy_headers defaults to True; cookie_secure is tri-state, explicit false allows plain-HTTP LAN login.",
    memory_type: "fact",
    classified_type: "fact",
    summary:
      "Proxy-header trust is on by default; cookie_secure has three states.",
    emotions: ["neutral"],
    flags: [],
    technologies: ["cookie-secure", "nginx"],
    tags: ["auth", "config"],
    confidence: 0.79,
    status: "active",
    created_at: ago(2 * DAY),
  },
  {
    ...base,
    id: ID_CHUNKING_IDEA,
    content:
      "Considering swapping the article synthesiser's chunking strategy to spans instead of blocks.",
    memory_type: "episodic",
    classified_type: "episodic",
    summary: "A speculative note on chunking strategy, not a decision yet.",
    emotions: ["curious"],
    flags: ["speculative"],
    technologies: [],
    tags: ["articles", "ideas"],
    confidence: 0.5,
    status: "active",
    created_at: ago(3 * DAY),
  },
]

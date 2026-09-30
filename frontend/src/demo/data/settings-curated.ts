import type { ApiKind, DemoCodeBucket, DemoLLMPurpose } from "@/features/settings/types"
import type {
  DemoFlagsState,
  DemoMaintenanceState,
  DemoSecurityState,
} from "../types"

// ---------------------------------------------------------------------------
// S25 — Flags. w_conf, w_dual, and w_context_boost are measured, non-zero
// overrides on this instance (the same weights snapshot the S03 trace reads);
// the rest sit at their coded default of 0 and render inactive.
// ---------------------------------------------------------------------------

export const CURATED_FLAGS: DemoFlagsState = {
  fusion_arms: [
    {
      key: "w_conf",
      alias: "confidence_rank_gamma",
      desc: "Ranks results with a higher confidence estimate above the rest",
      value: 0.4,
      coded_default: 0,
      source: "override",
      step: 0.05,
    },
    {
      key: "w_importance",
      desc: "Ranks more important memories higher",
      value: 0,
      coded_default: 0,
      source: "default",
      step: 0.05,
      activatesWith: "T2.30",
      unmeasured: true,
    },
    {
      key: "w_heat",
      desc: "Ranks frequently read memories higher",
      value: 0,
      coded_default: 0,
      source: "default",
      step: 0.05,
      activatesWith: "T2.31",
      unmeasured: true,
    },
    {
      key: "w_recency",
      desc: "Ranks recently used or created memories higher",
      value: 0,
      coded_default: 0,
      source: "default",
      step: 0.05,
      activatesWith: "T2.31",
      unmeasured: true,
    },
  ],
  graph_flags: [
    {
      key: "ppr_enabled",
      desc: "Adds results ranked by how close they are in the entity graph to the entities in the query",
      enabled: false,
      source: "default",
      paired_arm: {
        key: "w_ppr",
        desc: "How much the graph-proximity results count in the ranking",
        value: 0,
        coded_default: 0,
        source: "default",
        step: 0.05,
      },
    },
    {
      key: "dual_level_enabled",
      desc: "Adds results found by searching the relations between entities",
      enabled: true,
      source: "override",
      paired_arm: {
        key: "w_dual",
        desc: "How much the relation-search results count in the ranking",
        value: 0.15,
        coded_default: 0,
        source: "override",
        step: 0.05,
      },
    },
    {
      key: "community_injection_enabled",
      desc: "Adds a summary of the matching entity group as context. It adds no ranked list, so it has no weight",
      enabled: false,
      source: "default",
      paired_arm: null,
      no_weight_note:
        "context augmentation, not a ranking signal — no paired RRF weight",
    },
  ],
  context_boost: {
    key: "w_context_boost",
    desc: "Boosts results whose context conditions match the query; results whose conditions conflict are left out",
    value: 0.25,
    coded_default: 0,
    source: "override",
    step: 0.05,
    unmeasured: true,
  },
  corroboration: {
    // The shipped floors, uncommitted — an instance nobody has tuned. Demo
    // mode renders the same committed/effective split real mode does, so the
    // clamp is visible here rather than only on a live install.
    params: [
      { name: "n_default", committed: null, effective: 3, floor: 3, measured: false, state: "default" },
      { name: "n_diverse", committed: null, effective: 2, floor: 2, measured: false, state: "default" },
      { name: "time_gap_days", committed: null, effective: 7, floor: 7, measured: false, state: "default" },
    ],
    measured: [],
    rowPresent: false,
    measurementTask: "T2.40",
    gate_note:
      "N drops from 3 to 2 when the origins differ in source-kind (e.g. memory + code beats three memories) or are ≥ 7 days apart across distinct sessions. Source-kind diversity outweighs raw count; derived rows (a fact, an article) never count as an origin, and an origin of unknown identity merges to one — the count undercounts, it never manufactures agreement.",
  },
  behavioral_flags: [
    {
      key: "hybrid_search_enabled",
      desc: "Combines semantic and keyword search. Off, search uses semantic matching only",
      enabled: true,
      source: "default",
    },
    {
      key: "reranker_enabled",
      desc: "Has an LLM re-score the top 40 results before they are returned. Adds latency and cost",
      enabled: false,
      source: "default",
      unmeasured: true,
    },
    {
      key: "relation_rescue",
      desc: "Recovers relations the extractor missed, using text patterns",
      enabled: true,
      source: "default",
    },
  ],
  // Throughput and cache knobs, all at their coded defaults on this instance.
  // Bounds mirror `FeatureFlagsUpdate`'s `Field(ge=, le=)` so the field refuses
  // locally exactly what the API would 422 on.
  tunables: [
    {
      key: "pipeline_concurrency",
      desc: "How many memories are processed at once",
      value: 5,
      coded_default: 5,
      source: "default",
      min: 1,
      max: 20,
    },
    {
      key: "embedding_batch_size",
      desc: "How many texts go into one embedding call",
      value: 20,
      coded_default: 20,
      source: "default",
      min: 1,
      max: 200,
    },
    {
      key: "embedding_concurrency",
      desc: "How many embedding calls run at once",
      value: 1,
      coded_default: 1,
      source: "default",
      min: 1,
      max: 10,
    },
    {
      key: "entity_cache_ttl_minutes",
      desc: "How long an entity embedding stays cached in memory",
      value: 60,
      coded_default: 60,
      source: "default",
      min: 1,
      max: 1440,
      unit: "minutes",
    },
  ],
  classification_mode: "simple",
  classification_areas: ["general", "technical", "debugging", "infrastructure"],
  repo_allowlist: {
    patterns: ["github.com/darkraise/*"],
  },
  overrides_written: 4,
}

// ---------------------------------------------------------------------------
// S26 — LLM. Seven purpose cards (six live plus seeded-inert `synthesis`,
// which is writable), each naming a shared provider row; no profile or
// ml-profile chrome.
// ---------------------------------------------------------------------------

// Provider names below mirror the shared `llm_providers` connection rows
// the Providers sub-tab edits: "ollama-local" serves four purposes (the
// point of the consolidation — one credential, four routes), "zai-primary"
// and "openai-primary" each serve one.
export const CURATED_LLM_PURPOSES: DemoLLMPurpose[] = [
  {
    purpose: "embedding",
    tier: "tier A / B / C",
    role: "every vector: content, entity, code chunk, query",
    provider_name: "ollama-local",
    model: "qwen3-embedding:0.6b",
    api_kind: "ollama",
    base_url: "localhost:11434",
    api_key: "",
    params: '{"batch_size": 64}',
    dimensions: 1024,
  },
  {
    purpose: "extraction",
    tier: "tier B",
    role: "the merged ingest call — entities + relations + classification fields",
    provider_name: "ollama-local",
    model: "qwen3:4b-instruct",
    api_kind: "ollama",
    base_url: "localhost:11434",
    api_key: "",
    params: '{"temperature": 0}',
    reasoning: false,
    hint: {
      tone: "info",
      text: "Reasoning is off so long outputs are not cut short.",
    },
  },
  {
    purpose: "classification",
    tier: "tier B",
    role: "classification, folded into extraction in simple mode",
    provider_name: "ollama-local",
    model: "qwen3:4b-instruct",
    api_kind: "ollama",
    base_url: "localhost:11434",
    api_key: "",
    params: '{"temperature": 0}',
    reasoning: false,
  },
  {
    purpose: "summarization",
    tier: "tier B / C",
    role: "code enrichment + wiki, fanning out to three code-summarization buckets; Tier-C topic/community reports",
    provider_name: "ollama-local",
    model: "qwen3:4b-instruct",
    api_kind: "ollama",
    base_url: "localhost:11434",
    api_key: "",
    params: '{"temperature": 0.3}',
    reasoning: false,
  },
  {
    purpose: "reranker",
    tier: "tier A",
    role: "retrieval rerank scoring, top-40 RRF rows, flag-gated",
    provider_name: "zai-primary",
    model: "glm-4.6-flash",
    api_kind: "zai",
    base_url: "api.z.ai/api/paas/v4",
    api_key: "zk-demo-000000000000000091cd",
    params: '{"temperature": 0, "max_tokens": 16}',
    reasoning: false,
    hint: {
      tone: "info",
      text: "Turn the reranker on or off under Settings → Flags.",
    },
  },
  {
    purpose: "reasoning",
    tier: "tier A / C",
    role: "memory_reason, conversational chat, Tier-C dream-refine judgments",
    provider_name: "openai-primary",
    model: "gpt-5.1-mini",
    api_kind: "openai",
    base_url: "api.openai.com/v1",
    api_key: "sk-demo-0000000000000000004f2a",
    params: '{"temperature": 0.7}',
    reasoning: true,
  },
  {
    purpose: "synthesis",
    tier: "tier C",
    role: "Layer-3 article write-ups, auto-research write-ups",
    provider_name: "ollama-local",
    model: "qwen2.5:3b",
    api_kind: "ollama",
    base_url: "localhost:11434",
    api_key: "",
    params: '{"temperature": 0.3}',
    reasoning: false,
    hint: {
      tone: "info",
      text: "Used when writing summary articles.",
    },
  },
]

export const CURATED_CODE_BUCKETS: DemoCodeBucket[] = [
  {
    key: "symbol",
    model: "qwen3:4b-instruct",
    note: "short, cheap, high-volume — not billed at the overview model's rate",
  },
  { key: "module", model: "qwen3:4b-instruct", note: "per-file rollups" },
  {
    key: "overview",
    model: "qwen3:8b-instruct",
    note: "repo-level, priced for depth",
  },
]

// ---------------------------------------------------------------------------
// S28 — Security.
// ---------------------------------------------------------------------------

export const CURATED_SECURITY: DemoSecurityState = {
  rate_limit: {
    attempt_threshold: 5,
    lockout_window: "15 minutes",
  },
  cookie_secure: {
    value: "off — set explicitly",
  },
  mcp_hosts: [
    { host: "localhost" },
    { host: "192.168.0.195:8000" },
    { host: "*", wild: true },
  ],
}

// ---------------------------------------------------------------------------
// S29 — Maintenance.
// ---------------------------------------------------------------------------

export const CURATED_MAINTENANCE: DemoMaintenanceState = {
  reembed: { memories: 182, entities: 47 },
  cleanup: {
    expired: 14,
    expired_dependents: 2,
    failures_memory_ingest: 6,
    failures_code_repo: 1,
  },
  dbops: {
    retired_fingerprints: [
      "nomic-embed-text|768",
      "text-embedding-3-small|1536",
      "bge-base-en-v1.5|768",
    ],
  },
  last_op_note: null,
}

// ---------------------------------------------------------------------------
// S32 — Setup wizard fixtures (demo-only; no fs or provider calls).
// ---------------------------------------------------------------------------

export interface SetupKindFixture {
  kind: ApiKind
  label: string
  base_url: string
  supports_embedding: boolean
  models: {
    embedding: string
    extraction: string
    classification: string
    reasoning: string
  }
  fetched_note: string
}

export const SETUP_API_KINDS: SetupKindFixture[] = [
  {
    kind: "openai",
    label: "OpenAI-compatible (/v1)",
    base_url: "api.openai.com/v1",
    supports_embedding: true,
    models: {
      embedding: "text-embedding-3-large",
      extraction: "gpt-5.1-mini",
      classification: "gpt-5.1-mini",
      reasoning: "gpt-5.1",
    },
    fetched_note: "14 models loaded",
  },
  {
    kind: "ollama",
    label: "Ollama (native)",
    base_url: "localhost:11434",
    supports_embedding: true,
    models: {
      embedding: "qwen3-embedding:0.6b",
      extraction: "qwen3:4b-instruct",
      classification: "qwen3:4b-instruct",
      reasoning: "qwen3:8b-instruct",
    },
    fetched_note: "6 local models found",
  },
  {
    kind: "anthropic",
    label: "Anthropic",
    base_url: "api.anthropic.com",
    supports_embedding: false,
    models: {
      embedding: "",
      extraction: "claude-haiku-4-5",
      classification: "claude-haiku-4-5",
      reasoning: "claude-sonnet-4-6",
    },
    fetched_note: "5 models loaded",
  },
  {
    kind: "google",
    label: "Google (OpenAI-compat shim)",
    base_url: "generativelanguage.googleapis.com/v1beta/openai",
    supports_embedding: true,
    models: {
      embedding: "text-embedding-004",
      extraction: "gemini-2.5-flash",
      classification: "gemini-2.5-flash",
      reasoning: "gemini-2.5-pro",
    },
    fetched_note: "8 models loaded",
  },
  {
    kind: "deepseek",
    label: "DeepSeek",
    base_url: "api.deepseek.com/v1",
    supports_embedding: false,
    models: {
      embedding: "",
      extraction: "deepseek-v4-flash",
      classification: "deepseek-v4-flash",
      reasoning: "deepseek-v4",
    },
    fetched_note: "3 models loaded",
  },
  {
    kind: "zai",
    label: "z.ai",
    base_url: "api.z.ai/api/paas/v4",
    supports_embedding: true,
    models: {
      embedding: "embedding-3",
      extraction: "glm-4.6-flash",
      classification: "glm-4.6-flash",
      reasoning: "glm-4.6",
    },
    fetched_note: "7 models loaded; you can also type a model name",
  },
]

export interface SetupDirFixture {
  name: string
  git: boolean
}

export const SETUP_CRUMBS = ["D:", "Repositories", "_local_projects"]
export const SETUP_BASE_PATH = "D:\\Repositories\\_local_projects"
export const SETUP_DIRS: SetupDirFixture[] = [
  { name: "darkmem", git: true },
  { name: "darkraise-ui", git: true },
  { name: "node_modules", git: false },
]

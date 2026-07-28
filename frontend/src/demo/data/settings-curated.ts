import type { ApiKind, DemoCodeBucket, DemoLLMPurpose } from "@/features/settings/types"
import type {
  DemoDistributionState,
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
      desc: "1 + w·(confidence − 0.75)",
      value: 0.4,
      coded_default: 0,
      source: "override",
      step: 0.05,
    },
    {
      key: "w_importance",
      desc: "1 + w·(importance − 0.5) — column populated, unread before this arm ships",
      value: 0,
      coded_default: 0,
      source: "default",
      step: 0.05,
      activatesWith: "T2.30",
      unmeasured: true,
    },
    {
      key: "w_heat",
      desc: "1 + w·heat_norm, heat computed in SQL from memory_access_stats",
      value: 0,
      coded_default: 0,
      source: "default",
      step: 0.05,
      activatesWith: "T2.31",
      unmeasured: true,
    },
    {
      key: "w_recency",
      desc: "1 + w·recency_norm, from last_accessed / created_at",
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
      desc: "personalized PageRank list, seeded from the query's resolved entities, read from a cached in-process snapshot",
      enabled: false,
      source: "default",
      paired_arm: {
        key: "w_ppr",
        desc: "RRF list weight — PPR-ranked memories",
        value: 0,
        coded_default: 0,
        source: "default",
        step: 0.05,
      },
    },
    {
      key: "dual_level_enabled",
      desc: "global relation arm over relation_embeddings, scoped through asserting memories",
      enabled: true,
      source: "override",
      paired_arm: {
        key: "w_dual",
        desc: "RRF list weight — dual-level relation channel",
        value: 0.15,
        coded_default: 0,
        source: "override",
        step: 0.05,
      },
    },
    {
      key: "community_injection_enabled",
      desc: "injects a resolved community's report_string as local context",
      enabled: false,
      source: "default",
      paired_arm: null,
      no_weight_note:
        "context augmentation, not a ranking signal — no paired RRF weight",
    },
  ],
  context_boost: {
    key: "w_context_boost",
    desc: "post-fusion multiplier on a MATCH outcome only — NEUTRAL carries a label with no boost, CONFLICT excludes and counts",
    value: 0.25,
    coded_default: 0,
    source: "override",
    step: 0.05,
    unmeasured: true,
  },
  corroboration: {
    n_base: 3,
    n_diverse: 2,
    source: "default",
    gate_note:
      "N drops from 3 to 2 when the origins differ in source-kind (e.g. memory + code beats three memories) or are ≥ 7 days apart across distinct sessions. Source-kind diversity outweighs raw count; derived rows (a fact, an article) never count as an origin, and an origin of unknown identity merges to one — the count undercounts, it never manufactures agreement.",
  },
  behavioral_flags: [
    {
      key: "hybrid_search_enabled",
      desc: "RRF fusion of semantic + keyword search, k=60 — the retrieval baseline the G-A gate already measured",
      enabled: true,
      source: "default",
    },
    {
      key: "reranker_enabled",
      desc: "LLM-scores the top-40 RRF rows before serving — flips only on a measured win including its p95 cost (gate-ledger.md standing conditional gate)",
      enabled: false,
      source: "default",
      unmeasured: true,
    },
    {
      key: "relation_rescue",
      desc: "pattern-based rescue layer for relations the extractor misses (adjacency, subject-tracking, REPLACES)",
      enabled: true,
      source: "default",
    },
  ],
  repo_allowlist: {
    patterns: ["github.com/darkraise/*"],
  },
  overrides_written: 4,
}

// ---------------------------------------------------------------------------
// S26 — LLM. Six inline purpose cards; no provider/profile chrome.
// ---------------------------------------------------------------------------

export const CURATED_LLM_PURPOSES: DemoLLMPurpose[] = [
  {
    purpose: "embedding",
    tier: "tier A / B / C",
    role: "every vector: content, entity, code chunk, query",
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
    model: "qwen3:4b-instruct",
    api_kind: "ollama",
    base_url: "localhost:11434",
    api_key: "",
    params: '{"temperature": 0}',
    reasoning: false,
    hint: {
      tone: "info",
      text: "seeded reasoning: off — a hidden chain-of-thought would otherwise peg the output cap on a reasoning-by-default vendor and truncate the extraction JSON.",
    },
  },
  {
    purpose: "classification",
    tier: "tier B",
    role: "classification, folded into extraction in simple mode",
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
    model: "glm-4.6-flash",
    api_kind: "zai",
    base_url: "api.z.ai/api/paas/v4",
    api_key: "zk-demo-000000000000000091cd",
    params: '{"temperature": 0, "max_tokens": 16}',
    reasoning: false,
    hint: {
      tone: "info",
      text: "the rerank purpose whose reranker_enabled activation toggle lives on Settings · Flags, not here.",
    },
  },
  {
    purpose: "reasoning",
    tier: "tier A / C",
    role: "memory_reason, conversational chat, Tier-C dream-refine judgments",
    model: "gpt-5.1-mini",
    api_kind: "openai",
    base_url: "api.openai.com/v1",
    api_key: "sk-demo-0000000000000000004f2a",
    params: '{"temperature": 0.7}',
    reasoning: true,
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
  blocklisted: 186,
  lockouts_30d: 2,
  session: {
    issued_label: "cookie-JWT, HttpOnly, HS256, issued 2026-07-24 09:12 UTC",
    jti: "7f3a…c02e",
  },
  rate_limit: {
    attempt_threshold: 5,
    lockout_window: "15 minutes",
    ip_source:
      "X-Real-IP (bundled-nginx posture, trusted proxy) — the leftmost X-Forwarded-For is never trusted",
    journaled: "2 auth_lockout events in the last 30 days",
  },
  cookie_secure: {
    value: "false — explicit, permits login over plain-HTTP LAN",
    note: "Unset would mean Secure-only when environment=production; this deployment set it explicitly for the no-TLS home LAN and it flips back to enforced-Secure the moment an exposed deployment puts TLS in front.",
  },
  tofu: {
    claimed_label:
      "2026-05-02 08:03 UTC — this wizard run is the box's only owner",
    journaled: "events: setup_completed @ 2026-05-02 08:03 UTC",
  },
  mcp_hosts: [
    { host: "localhost (always)" },
    { host: "192.168.0.195:8000" },
    {
      host: "* — disables the check entirely (explicit operator decision, not a fix)",
      wild: true,
    },
  ],
  api_key_scopes: [
    { label: "capture" },
    { label: "read" },
    { label: "admin" },
    {
      label: "ratify — never a scope, human cookie session only",
      never: true,
    },
  ],
}

// ---------------------------------------------------------------------------
// S29 — Maintenance.
// ---------------------------------------------------------------------------

export const CURATED_MAINTENANCE: DemoMaintenanceState = {
  fingerprint: "bge-large-en-v1.5|1024",
  reembed: { memories: 182, entities: 47, code_chunks: 940 },
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
    vacuum_target: "memory_embeddings__…5_1024",
    vacuum_note: "340 MB, last analyzed 6 days ago — due after a memories re-embed.",
    reindex_target: "ix_memories_technologies",
    reindex_note:
      "The GIN index supersession and retrieval filtering both consult (memories.technologies).",
  },
  last_op_note: null,
}

// ---------------------------------------------------------------------------
// S30 — Distribution.
// ---------------------------------------------------------------------------

export const CURATED_DISTRIBUTION: DemoDistributionState = {
  clients: [
    {
      id: "claude-code",
      name: "Claude Code",
      status: "connected",
      handshake: "handshake ok · 14 tools listed",
      context_file: "CLAUDE.md",
      mcp_config: ".mcp.json",
      push_note: "active · last inject 14:12 UTC · 8 items, 1,840/2,000 tokens",
      curbed_note: null,
    },
    {
      id: "cursor",
      name: "Cursor",
      status: "connected",
      handshake: "handshake ok · 14 tools listed",
      context_file: ".cursor/rules/darkmem.mdc",
      mcp_config: ".cursor/mcp.json",
      push_note: "active · last inject 14:10 UTC · 6 items, 1,510/2,000 tokens",
      curbed_note: null,
    },
    {
      id: "codex-cli",
      name: "Codex CLI",
      status: "curbed",
      handshake: "handshake ok · 14 tools listed",
      context_file: "AGENTS.md",
      mcp_config: "~/.codex/config.toml [mcp_servers]",
      push_note: "curbed by operator, 2026-07-24 13:58 UTC",
      curbed_note:
        "Pull (MCP tools) is unaffected — only push stopped. AGENTS.md's managed block was rewritten to an empty marker pair, not removed; re-enabling resumes idempotently.",
    },
    {
      id: "cline",
      name: "Cline",
      status: "disconnected",
      handshake: null,
      context_file: ".clinerules/darkmem.md",
      mcp_config: "(none detected)",
      push_note: null,
      curbed_note: null,
      connect_hint:
        "Its adapter row exists in the registry but no `darkmem connect cline` has run yet.",
    },
  ],
  policy: [
    {
      key: "inject_token_budget",
      value: "2,000 tokens",
      desc: "config row, per-target tunable — Codex CLI overrides to 1,200",
    },
    {
      key: "refresh cadence",
      value: "session-start",
      desc: "one read + one idempotent write per session; watch mode is a deferred, config-gated Phase-4 enhancement",
    },
    {
      key: "cold-start fallback",
      value: "candidates, labelled",
      desc: "served only when nothing corroborated/confirmed fits the budget yet",
    },
    {
      key: "codex-cli override",
      value: "inject_token_budget = 1,200 tokens",
      desc: "a smaller per-target budget, tuned for AGENTS.md's terser convention — the adapter registry and the budget are both config rows, never hard-coded",
    },
  ],
  block_preview: [
    "# Project notes",
    "(the human's own rules — never touched)",
    "<!-- darkmem:begin -->",
    "# generated 2026-07-24T14:12:03Z, project darkmem, 8 items, 1,840/2,000 tokens",
    "- [L2 · corroborated] hybrid_search_enabled is on by default; RRF k=60",
    "- [L2 · corroborated] confidence_rank_gamma defaults to 0 — inactive until raised",
    "- [L0 · summary] pipeline Phase 5 writes vector + graph in two savepoints",
    "  … 5 more, truth-first order, top-K under the token budget",
    "<!-- darkmem:end -->",
  ].join("\n"),
  log: [
    {
      id: "log-1",
      target: "claude-code",
      event_type: "inject",
      detail: "project darkmem · 8 items",
      time_label: "2026-07-24 14:12:03 UTC",
      meta: "1,840/2,000 tok",
    },
    {
      id: "log-2",
      target: "cursor",
      event_type: "inject",
      detail: "project darkmem · 6 items",
      time_label: "2026-07-24 14:10:41 UTC",
      meta: "1,510/2,000 tok",
    },
    {
      id: "log-3",
      target: "codex-cli",
      event_type: "inject_curbed",
      detail: "push disabled by operator q.tran",
      time_label: "2026-07-24 13:58:12 UTC",
      meta: "block → empty markers",
    },
    {
      id: "log-4",
      target: "codex-cli",
      event_type: "inject",
      detail: "project darkmem · 5 items (last delivery before the curb above)",
      time_label: "2026-07-24 13:40:02 UTC",
      meta: "960/1,200 tok",
    },
  ],
  inject_items: [
    {
      layer: 2,
      badge: "corroborated",
      as_label: "corroborated",
      text: "asserted by 3 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-20 — hybrid_search_enabled is on by default; RRF k=60",
    },
    {
      layer: 0,
      badge: "superseded",
      as_label: "superseded, amber, lineage-requested",
      text: '"the reranker was skipped by default" — superseded_by → memory 7a1c4e0, kept only because this session\'s declared context asked for supersession lineage on retrieval ranking',
    },
  ],
  watermarks: [
    {
      key: "distribution:watermark:claude-code",
      value: "{ items: 8, delivered: 2026-07-24T14:12:03Z, project: darkmem }",
    },
    {
      key: "distribution:watermark:cursor",
      value: "{ items: 6, delivered: 2026-07-24T14:10:41Z, project: darkmem }",
    },
    {
      key: "distribution:watermark:codex-cli",
      value:
        "{ items: 0, delivered: 2026-07-24T13:58:12Z, project: darkmem, note: curbed }",
    },
  ],
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
    fetched_note: "7 models loaded (vendor /v1/models omits some — free-text entry still works)",
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

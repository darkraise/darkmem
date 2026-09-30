import type {
  DemoArticle,
  DemoCommunity,
  DemoFact,
  DemoPinSuggestion,
  DemoReviewItem,
  HygieneQueueState,
} from "../types"

// Fixed dates keep every knowledge surface deterministic across reloads.
// All verification strings are stored verbatim — the UI renders them, it
// never recomputes or softens them (honesty invariant 14/15).

export const FACT_IDS = {
  semanticWeight: "fb31c908",
  codeSearch: "f8b6e210",
  rerankerDefault: "f9d3e7a1",
  deployCompose: "f4d0c2b7",
  hybridRrf: "f7aa10c3",
  extractionModel: "f2e91b44",
  rerankerCrossEncoder: "f5cc0e88",
  testDb: "f1d99a02",
  cookieSecure: "f6b2d4e9",
  cookieLan: "f3a7c5d1",
  rerankTop40: "f0e4b8a6",
  degradedChannel: "fd12e7c9",
  llmPurposes: "f88d4a6f",
  mcpHosts: "fe201c77",
  toggleGroup: "f77aa001",
} as const

export const ARTICLE_IDS = {
  retrievalFusion: "a4c9a7e2",
  retrievalFusionV1: "af0b3d9a",
  cookieSecurity: "a6e00c13",
  degradedChannel: "a7d3b0f2",
  llmPurposes: "a9f1e6b4",
  providerQuirks: "a2b8c4d0",
} as const

export const CURATED_FACTS: DemoFact[] = [
  {
    id: FACT_IDS.deployCompose,
    project: "darkmem",
    subject_name: "darkmem",
    rel_type: "DEPLOYED_ON",
    object_name: "docker-compose",
    fact_text:
      "darkmem's production stack is deployed on docker-compose with host networking.",
    verification_status: "confirmed",
    claim:
      "asserted by 2 distinct origins of kinds [human, memory], no known contradiction, as of 2026-07-21, human-ratified",
    meta: "ratified by q.tran, 2026-07-21",
    review_state: null,
    as_of: "2026-07-21",
    ratified: { by: "q.tran", on: "2026-07-21" },
    sources: [
      {
        origin_key: "session:2c88f1a0",
        kind: "memory",
        ref: "memory 4b7712ce",
        detail:
          "“prod stack runs docker compose up -d with host networking; requires DB_PASSWORD + JWT_SECRET”",
        at: "captured 2026-06-09 18:40",
      },
      {
        origin_key: "human:q.tran",
        kind: "human",
        ref: "human q.tran",
        detail:
          "ratified after checking the deployed compose file directly — the ratification wrote this human-kind source",
        at: "ratified 2026-07-21 10:05",
      },
    ],
    windows: [
      {
        valid_at: "2026-06-09 18:40",
        invalid_at: null,
        expired_at: null,
        note: "current live belief — window still open.",
      },
    ],
    ladder: [
      {
        at: "2026-06-09 18:40",
        description: "lifted from an L1 DEPLOYED_ON relation",
        transition: { from: null, to: "candidate" },
      },
      {
        at: "2026-06-10 03:00",
        description: "second distinct origin corroborated the assertion",
        transition: { from: "candidate", to: "corroborated" },
      },
      {
        at: "2026-07-21 10:05",
        description: "ratified by q.tran — the human origin was written as a fact_source",
        transition: { from: "corroborated", to: "confirmed" },
        note: "only a human ratify reaches confirmed; the machine ceiling is corroborated",
      },
    ],
    applies_when: [{ key: "env", value: "production", tag: "human" }],
  },
  {
    id: FACT_IDS.semanticWeight,
    project: "darkmem",
    subject_name: "semantic_weight",
    rel_type: "DEFAULTS_TO",
    object_name: "0.7",
    fact_text:
      "semantic_weight defaults to 0.7 in the RRF fusion formula (k=60) — the semantic channel is weighted 70% against the keyword channel's 30% before fusion.",
    verification_status: "corroborated",
    claim:
      "asserted by 3 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-22",
    meta: "asserted by 3 distinct origins",
    review_state: null,
    as_of: "2026-07-22",
    sources: [
      {
        origin_key: "session:9f21b7c4",
        kind: "memory",
        ref: "memory 5c81e0f2",
        detail: "“hybrid_search_enabled defaults on; RRF fusion runs k=60”",
        at: "captured 2026-06-01 09:00",
      },
      {
        origin_key: "session:9f21b7c4",
        kind: "memory",
        ref: "memory 771e4f9a",
        detail: "“semantic_weight defaults to 0.7 in the RRF fusion formula”",
        at: "captured 2026-06-01 09:04",
      },
      {
        origin_key: "repo:darkmem-backend",
        kind: "code",
        ref: "code backend/app/services/hybrid_search.py@d81e4f0",
        detail: "basis: constant SEMANTIC_WEIGHT_DEFAULT = 0.7 parsed from source",
        at: "indexed 2026-06-03",
      },
      {
        origin_key: "session:review-2026-07-19",
        kind: "memory",
        ref: "memory 3a9c02e1",
        detail:
          "“weekly config audit reconfirmed semantic_weight=0.7 against the live RRF fusion call”",
        at: "captured 2026-07-19 08:15",
      },
    ],
    windows: [
      {
        valid_at: "2026-06-01 09:00",
        invalid_at: null,
        expired_at: null,
        note: "darkmem's current live belief — expired_at IS NULL, window still open.",
      },
      {
        valid_at: "2026-02-01 09:00",
        invalid_at: "2026-06-01 09:00",
        expired_at: null,
        note: "retained as history, NOT a live claim — superseded by the 2026-06-01 reconfirmation (stale-on-arrival); the row was never deleted.",
      },
    ],
    ladder: [
      {
        at: "2026-06-01 09:04",
        description: "extracted from the capturing session",
        transition: { from: null, to: "candidate" },
      },
      {
        at: "2026-06-03 02:00",
        description: "code parse independently asserted the same default",
        transition: { from: "candidate", to: "corroborated" },
        note: "two distinct origin_keys crossed the corroboration floor",
      },
    ],
    applies_when: [
      { key: "hybrid_search_enabled", value: "on", tag: "human" },
      { key: "reranker_profile", value: "default", tag: "human" },
    ],
  },
  {
    id: FACT_IDS.hybridRrf,
    project: "darkmem",
    subject_name: "hybrid_search",
    rel_type: "USES",
    object_name: "reciprocal rank fusion",
    fact_text:
      "hybrid_search combines the semantic and keyword channels via reciprocal rank fusion with k=60.",
    verification_status: "corroborated",
    claim:
      "asserted by 3 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-20",
    meta: "asserted by 3 distinct origins",
    review_state: null,
    as_of: "2026-07-20",
    sources: [
      {
        origin_key: "repo:darkmem-backend",
        kind: "code",
        ref: "code backend/app/services/hybrid_search.py@d81e4f0",
        detail: "basis: RRF fusion call with k=60 parsed from HybridSearchService.search",
        at: "indexed 2026-06-03",
      },
      {
        origin_key: "session:9f21b7c4",
        kind: "memory",
        ref: "memory 5c81e0f2",
        detail: "“hybrid_search_enabled defaults on; RRF fusion runs k=60”",
        at: "captured 2026-06-01 09:00",
      },
      {
        origin_key: "session:41d0b2ee",
        kind: "memory",
        ref: "memory 90a1cc37",
        detail: "“RRF fuses both channels; consumers must prefer rrf_score”",
        at: "captured 2026-06-20 14:12",
      },
    ],
    windows: [
      {
        valid_at: "2026-06-01 09:00",
        invalid_at: null,
        expired_at: null,
        note: "current live belief — window still open.",
      },
    ],
    ladder: [
      {
        at: "2026-06-01 09:00",
        description: "extracted from the capturing session",
        transition: { from: null, to: "candidate" },
      },
      {
        at: "2026-06-03 02:00",
        description: "code parse corroborated the fusion call",
        transition: { from: "candidate", to: "corroborated" },
      },
    ],
    applies_when: [],
  },
  {
    id: FACT_IDS.rerankTop40,
    project: "darkmem",
    subject_name: "reranker",
    rel_type: "LIMITS_TO",
    object_name: "top 40 fused rows",
    fact_text:
      "when reranker_enabled, RerankerService LLM-scores only the top 40 RRF-ranked rows; the unscored tail is appended in its original fused order.",
    verification_status: "corroborated",
    claim:
      "asserted by 2 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-18",
    meta: "asserted by 2 distinct origins",
    review_state: null,
    as_of: "2026-07-18",
    sources: [
      {
        origin_key: "repo:darkmem-backend",
        kind: "code",
        ref: "code backend/app/services/reranker.py@b402ce1",
        detail: "basis: RERANK_WINDOW = 40 slice before LLM scoring",
        at: "indexed 2026-07-01",
      },
      {
        origin_key: "session:70cf22b8",
        kind: "memory",
        ref: "memory a1b2c3d4",
        detail: "“the reranker LLM-scores the top 40 fused rows on a 0–10 scale”",
        at: "captured 2026-07-03 11:30",
      },
    ],
    windows: [
      {
        valid_at: "2026-07-01 02:00",
        invalid_at: null,
        expired_at: null,
        note: "current live belief — window still open.",
      },
    ],
    ladder: [
      {
        at: "2026-07-01 02:00",
        description: "code parse asserted the top-40 window",
        transition: { from: null, to: "corroborated" },
        note: "code-originated: the parse is the verification — no candidate phase",
      },
    ],
    applies_when: [{ key: "reranker_enabled", value: "on", tag: "human" }],
  },
  {
    id: FACT_IDS.degradedChannel,
    project: "darkmem",
    subject_name: "hybrid_search",
    rel_type: "DEGRADES_TO",
    object_name: "surviving channel",
    fact_text:
      "when one retrieval channel fails, hybrid search degrades to the surviving channel rather than narrowing the result set.",
    verification_status: "corroborated",
    claim:
      "asserted by 2 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-12",
    meta: "asserted by 2 distinct origins",
    review_state: null,
    as_of: "2026-07-12",
    sources: [
      {
        origin_key: "repo:darkmem-backend",
        kind: "code",
        ref: "code backend/app/services/hybrid_search.py@d81e4f0",
        detail: "basis: single-channel fallback branch in the fusion path",
        at: "indexed 2026-06-03",
      },
      {
        origin_key: "session:88e01f2d",
        kind: "memory",
        ref: "memory 2f00ab19",
        detail:
          "“a single-channel failure never silently returns fewer rows — the surviving channel serves”",
        at: "captured 2026-07-12 09:45",
      },
    ],
    windows: [
      {
        valid_at: "2026-06-03 02:00",
        invalid_at: null,
        expired_at: null,
        note: "current live belief — window still open.",
      },
    ],
    ladder: [
      {
        at: "2026-06-03 02:00",
        description: "code parse asserted the degrade path",
        transition: { from: null, to: "corroborated" },
        note: "code-originated: born corroborated",
      },
    ],
    applies_when: [],
  },
  {
    id: FACT_IDS.codeSearch,
    project: "darkmem",
    subject_name: "search_code",
    rel_type: "IS",
    object_name: "semantic_only",
    fact_text:
      "search_code is semantic-only — the code_chunk_embeddings__<slug> partitions carry no FTS column, so there is nothing to fuse with hybrid search.",
    verification_status: "corroborated",
    claim:
      "asserted by 2 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-15",
    meta: "code@e7a2b4c",
    review_state: null,
    as_of: "2026-07-15",
    code_provenance: {
      commit_sha: "e7a2b4c",
      basis:
        "no FTS column found on code_chunk_embeddings__<slug> in the parsed migration + repository schema scan",
      file_path: "backend/app/services/code_pipeline.py",
      symbol_key: "CodeSearchService.search_code",
    },
    sources: [
      {
        origin_key: "repo:darkmem-backend",
        kind: "code",
        ref: "code backend/app/services/code_pipeline.py@e7a2b4c",
        detail: "basis: no FTS column on the code-chunk embedding partition",
        at: "indexed 2026-07-15 09:50",
      },
      {
        origin_key: "session:4b71ea9c",
        kind: "memory",
        ref: "memory f02c88a1",
        detail:
          "“search_code never fuses with FTS since code chunks carry no search_vector column”",
        at: "captured 2026-07-15 10:30",
      },
    ],
    windows: [
      {
        valid_at: "2026-07-15 09:50",
        invalid_at: null,
        expired_at: null,
        note: "born corroborated at write time — no candidate phase preceded it.",
      },
    ],
    ladder: [
      {
        at: "2026-07-15 09:50",
        description: "code parse asserted the schema fact",
        transition: { from: null, to: "corroborated" },
        note: "code-originated, born corroborated: parse is verification",
      },
    ],
    applies_when: [
      { key: "repo", value: "darkmem-backend", tag: "human" },
      { key: "index_mode", value: "semantic-only", tag: "human" },
    ],
  },
  {
    id: FACT_IDS.llmPurposes,
    project: "darkmem",
    subject_name: "llm purposes",
    rel_type: "ROUTES_VIA",
    object_name: "shared llm_providers connection row",
    fact_text:
      "six LLM purposes — embedding, extraction, classification, reasoning, summarization, reranker — each carry a provider_name pointing at a shared llm_providers row, so rotating that row's credential reaches every purpose pointed at it in one edit.",
    verification_status: "corroborated",
    claim:
      "asserted by 2 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-10",
    meta: "asserted by 2 distinct origins",
    review_state: null,
    as_of: "2026-07-10",
    sources: [
      {
        origin_key: "repo:darkmem-backend",
        kind: "code",
        ref: "code backend/app/models/llm_config.py@91cd7e3",
        detail: "basis: LLMPurposeConfig rows with a provider_name column resolving into llm_providers",
        at: "indexed 2026-07-02",
      },
      {
        origin_key: "session:5510ffe2",
        kind: "memory",
        ref: "memory 8c33d0b5",
        detail: "“each purpose resolves independently; rotation lives in one place”",
        at: "captured 2026-07-10 15:20",
      },
    ],
    windows: [
      {
        valid_at: "2026-07-02 02:00",
        invalid_at: null,
        expired_at: null,
        note: "current live belief — window still open.",
      },
    ],
    ladder: [
      {
        at: "2026-07-02 02:00",
        description: "code parse asserted the routing model",
        transition: { from: null, to: "corroborated" },
      },
    ],
    applies_when: [],
  },
  {
    id: FACT_IDS.cookieSecure,
    project: "darkmem",
    subject_name: "cookie_secure",
    rel_type: "DEFAULTS_TO",
    object_name: "secure-only-in-production",
    fact_text:
      "cookie_secure is tri-state: unset means the Secure flag is applied only when environment=production.",
    verification_status: "corroborated",
    claim:
      "asserted by 2 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-08",
    meta: "asserted by 2 distinct origins",
    review_state: null,
    as_of: "2026-07-08",
    sources: [
      {
        origin_key: "repo:darkmem-backend",
        kind: "code",
        ref: "code backend/app/config.py@4f00ab2",
        detail: "basis: tri-state cookie_secure resolution parsed from settings",
        at: "indexed 2026-06-10",
      },
      {
        origin_key: "session:6a2290cd",
        kind: "memory",
        ref: "memory c93f7a12",
        detail: "“unset = Secure only when environment=production”",
        at: "captured 2026-06-09 19:02",
      },
    ],
    windows: [
      {
        valid_at: "2026-06-09 19:02",
        invalid_at: null,
        expired_at: null,
        note: "current live belief — window still open.",
      },
    ],
    ladder: [
      {
        at: "2026-06-09 19:02",
        description: "extracted from the compose-simplification session",
        transition: { from: null, to: "candidate" },
      },
      {
        at: "2026-06-10 02:00",
        description: "code parse corroborated the tri-state default",
        transition: { from: "candidate", to: "corroborated" },
      },
    ],
    applies_when: [],
  },
  {
    id: FACT_IDS.cookieLan,
    project: "darkmem",
    subject_name: "COOKIE_SECURE=false",
    rel_type: "ALLOWS",
    object_name: "plain-http lan login",
    fact_text:
      "an explicit COOKIE_SECURE=false permits login over plain-HTTP LAN deploys without weakening the production default.",
    verification_status: "corroborated",
    claim:
      "asserted by 2 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-08",
    meta: "asserted by 2 distinct origins",
    review_state: null,
    as_of: "2026-07-08",
    sources: [
      {
        origin_key: "repo:darkmem-backend",
        kind: "code",
        ref: "code backend/app/config.py@4f00ab2",
        detail: "basis: explicit-false branch bypasses the environment check",
        at: "indexed 2026-06-10",
      },
      {
        origin_key: "session:6a2290cd",
        kind: "memory",
        ref: "memory 71b0d5e6",
        detail: "“COOKIE_SECURE=false for plain-HTTP LAN — decoupled from environment”",
        at: "captured 2026-06-09 19:05",
      },
    ],
    windows: [
      {
        valid_at: "2026-06-09 19:05",
        invalid_at: null,
        expired_at: null,
        note: "current live belief — window still open.",
      },
    ],
    ladder: [
      {
        at: "2026-06-09 19:05",
        description: "extracted from the compose-simplification session",
        transition: { from: null, to: "candidate" },
      },
      {
        at: "2026-06-10 02:00",
        description: "code parse corroborated the override",
        transition: { from: "candidate", to: "corroborated" },
      },
    ],
    applies_when: [{ key: "deployment", value: "plain-http-lan", tag: "human" }],
  },
  {
    id: FACT_IDS.testDb,
    project: "darkmem",
    subject_name: "darkmem_test",
    rel_type: "HOSTED_ON",
    object_name: "127.0.0.1:5433",
    fact_text:
      "the darkmem_test database lives on the dev-compose Postgres at 127.0.0.1:5433.",
    verification_status: "corroborated",
    claim:
      "asserted by 1 distinct origin of kinds [memory], no known contradiction, as of 2026-07-23",
    meta: "under-sourced — 1 origin remains",
    review_state: "open",
    as_of: "2026-07-23",
    under_sourced_note:
      "origin count dropped to 1 after a duplicate memory was pruned by dreaming; will demote to candidate after verification_demote_grace_cycles consecutive recompute cycles unless re-corroborated — the label keeps retrieval honest now, the grace period absorbs transient churn.",
    sources: [
      {
        origin_key: "session:e19c04b7",
        kind: "memory",
        ref: "memory 60d2fa11",
        detail: "“create darkmem_test once on the dev-compose Postgres at 127.0.0.1:5433”",
        at: "captured 2026-06-01 12:00",
      },
    ],
    windows: [
      {
        valid_at: "2026-06-01 12:00",
        invalid_at: null,
        expired_at: null,
        note: "current live belief — window still open, held in demotion hysteresis.",
      },
    ],
    ladder: [
      {
        at: "2026-06-01 12:00",
        description: "extracted from the test-setup session",
        transition: { from: null, to: "candidate" },
      },
      {
        at: "2026-06-02 03:00",
        description: "a second session corroborated the port",
        transition: { from: "candidate", to: "corroborated" },
      },
      {
        at: "2026-07-23 03:00",
        description:
          "the corroborating duplicate was pruned by dreaming — origin count fell back to 1; rung unchanged, held in demotion hysteresis",
        note: "no silent demotion: the under-sourced overlay labels the drop while the grace period runs",
      },
    ],
    applies_when: [{ key: "env", value: "dev", tag: "human" }],
  },
  {
    id: FACT_IDS.rerankerDefault,
    project: "darkmem",
    subject_name: "reranker_enabled",
    rel_type: "DEFAULT_STATE",
    object_name: "— two competing object_name values",
    fact_text:
      "the default state of reranker_enabled in production is contested — two competing assertions carry overlapping validity windows.",
    verification_status: "disputed",
    claim:
      "disputed: 2 origins assert the reranker is enabled by default in production, 1 origin asserts the reranker is opt-in per profile and disabled by default, as of 2026-07-21",
    meta: "view both sides →",
    review_state: "open",
    as_of: "2026-07-21",
    dispute: {
      summary:
        "disputed: 2 origins assert the reranker is enabled by default in production, 1 origin asserts the reranker is opt-in per profile and disabled by default, as of 2026-07-21",
      sides: [
        {
          object_name: "on_by_default",
          assertion: "asserts X — the reranker is enabled by default in production",
          origin_count: 2,
          origin_kinds: ["code", "memory"],
          sources: [
            {
              origin_key: "repo:darkmem-backend",
              kind: "code",
              ref: "code config.py@f9b2e11",
              detail: "reranker_enabled default — on",
              at: "2026-05-10",
            },
            {
              origin_key: "session:8f0091d2",
              kind: "memory",
              ref: "memory 6c04af2e",
              detail: "“Enabled reranker by default after eval showed +12% nDCG”",
              at: "2026-05-10",
            },
          ],
          window: {
            valid_at: "2026-05-10",
            invalid_at: null,
            expired_at: null,
            note: "",
          },
          applies_when: [
            { key: "deployment", value: "cloud-hosted-default", tag: "human" },
          ],
        },
        {
          object_name: "opt_in_per_profile",
          assertion:
            "asserts not-X — the reranker is opt-in per profile, disabled by default",
          origin_count: 1,
          origin_kinds: ["human"],
          sources: [
            {
              origin_key: "human:q.tran",
              kind: "human",
              ref: "human q.tran",
              detail:
                "reviewed the deployed config directly: reranker_enabled defaults off; profiles opt in explicitly",
              at: "2026-07-20",
            },
          ],
          window: {
            valid_at: "2026-07-20",
            invalid_at: null,
            expired_at: null,
            note: "",
          },
          applies_when: [
            { key: "deployment", value: "self-hosted-config-override", tag: "human" },
          ],
        },
      ],
    },
    sources: [],
    windows: [],
    ladder: [
      {
        at: "2026-05-10 09:00",
        description: "two origins asserted the on-by-default side",
        transition: { from: null, to: "corroborated" },
      },
      {
        at: "2026-07-20 16:00",
        description:
          "a human origin contradicted over an overlapping window — one non-echo contradiction vetoes regardless of count",
        transition: { from: "corroborated", to: "disputed" },
      },
    ],
    applies_when: [],
  },
  {
    id: FACT_IDS.extractionModel,
    project: "darkmem",
    subject_name: "extraction purpose",
    rel_type: "USES",
    object_name: "glm-4.5-flash",
    fact_text:
      "the extraction purpose is served by glm-4.5-flash — contested by one origin asserting gpt-5.4-mini.",
    verification_status: "disputed",
    claim:
      "disputed: 2 origins assert extraction purpose uses glm-4.5-flash, 1 origin asserts extraction purpose uses gpt-5.4-mini, as of 2026-07-15",
    meta: "view both sides →",
    review_state: "open",
    as_of: "2026-07-15",
    dispute: {
      summary:
        "disputed: 2 origins assert extraction purpose uses glm-4.5-flash, 1 origin asserts extraction purpose uses gpt-5.4-mini, as of 2026-07-15",
      sides: [
        {
          object_name: "glm-4.5-flash",
          assertion: "asserts X — the extraction purpose is served by glm-4.5-flash",
          origin_count: 2,
          origin_kinds: ["memory"],
          sources: [
            {
              origin_key: "session:31bb08e4",
              kind: "memory",
              ref: "memory 19d47f02",
              detail: "“extraction moved to glm-4.5-flash after the eval round”",
              at: "2026-06-28",
            },
            {
              origin_key: "session:9902d1af",
              kind: "memory",
              ref: "memory 7e15cc90",
              detail: "“extraction seed run logged against glm-4.5-flash”",
              at: "2026-07-02",
            },
          ],
          window: {
            valid_at: "2026-06-28",
            invalid_at: null,
            expired_at: null,
            note: "",
          },
          applies_when: [
            {
              key: "purpose",
              value: "extraction",
              tag: "LLM-guessed, not human-checked",
            },
          ],
        },
        {
          object_name: "gpt-5.4-mini",
          assertion: "asserts not-X — the extraction purpose is served by gpt-5.4-mini",
          origin_count: 1,
          origin_kinds: ["memory"],
          sources: [
            {
              origin_key: "session:c07714b9",
              kind: "memory",
              ref: "memory 0b82ee43",
              detail: "“switched extraction to gpt-5.4-mini for the latency test”",
              at: "2026-07-15",
            },
          ],
          window: {
            valid_at: "2026-07-15",
            invalid_at: null,
            expired_at: null,
            note: "",
          },
          applies_when: [
            {
              key: "purpose",
              value: "extraction",
              tag: "LLM-guessed, not human-checked",
            },
          ],
        },
      ],
    },
    sources: [],
    windows: [],
    ladder: [
      {
        at: "2026-06-28 10:00",
        description: "two sessions asserted glm-4.5-flash",
        transition: { from: null, to: "corroborated" },
      },
      {
        at: "2026-07-15 18:00",
        description: "an overlapping-window contradiction arrived",
        transition: { from: "corroborated", to: "disputed" },
      },
    ],
    applies_when: [
      { key: "purpose", value: "extraction", tag: "LLM-guessed, not human-checked" },
    ],
  },
  {
    id: FACT_IDS.mcpHosts,
    project: "darkmem",
    subject_name: "MCP_ALLOWED_HOSTS",
    rel_type: "DEFAULT_STATE",
    object_name: "— two competing object_name values",
    fact_text:
      "the default of MCP_ALLOWED_HOSTS is contested: open-to-all versus localhost-only.",
    verification_status: "disputed",
    claim:
      "disputed: 1 origin asserts MCP_ALLOWED_HOSTS defaults to * (open), 1 origin asserts the default is empty — localhost-only, as of 2026-06-20",
    meta: "view both sides →",
    review_state: "open",
    as_of: "2026-06-20",
    dispute: {
      summary:
        "disputed: 1 origin asserts MCP_ALLOWED_HOSTS defaults to * (open), 1 origin asserts the default is empty — localhost-only, as of 2026-06-20",
      sides: [
        {
          object_name: "star_open",
          assertion: "asserts X — MCP_ALLOWED_HOSTS defaults to * and any Host is served",
          origin_count: 1,
          origin_kinds: ["memory"],
          sources: [
            {
              origin_key: "session:aa41c07e",
              kind: "memory",
              ref: "memory 3fb70d21",
              detail: "“MCP just works from the LAN — the allowlist must default open”",
              at: "2026-06-02",
            },
          ],
          window: {
            valid_at: "2026-06-02",
            invalid_at: null,
            expired_at: null,
            note: "",
          },
          applies_when: [],
        },
        {
          object_name: "empty_localhost_only",
          assertion:
            "asserts not-X — the default is empty: localhost-only, a foreign Host gets 421",
          origin_count: 1,
          origin_kinds: ["memory"],
          sources: [
            {
              origin_key: "session:bd90e13c",
              kind: "memory",
              ref: "memory 55c1a9e8",
              detail:
                "“default (empty) is localhost-only — fix a LAN 421 by extending the allowlist”",
              at: "2026-06-20",
            },
          ],
          window: {
            valid_at: "2026-06-20",
            invalid_at: null,
            expired_at: null,
            note: "",
          },
          applies_when: [],
        },
      ],
    },
    sources: [],
    windows: [],
    ladder: [
      {
        at: "2026-06-02 11:00",
        description: "first assertion extracted",
        transition: { from: null, to: "candidate" },
      },
      {
        at: "2026-06-20 09:00",
        description: "contradiction over an overlapping window",
        transition: { from: "candidate", to: "disputed" },
      },
    ],
    applies_when: [],
  },
  {
    id: FACT_IDS.rerankerCrossEncoder,
    project: "darkmem",
    subject_name: "reranker",
    rel_type: "REPLACES",
    object_name: "cross-encoder model",
    fact_text: "considering moving the reranker to a cross-encoder model.",
    verification_status: "candidate",
    claim:
      "asserted by 1 distinct origin of kinds [memory], no known contradiction, as of 2026-07-18",
    meta: "as of 2026-07-18",
    review_state: null,
    as_of: "2026-07-18",
    candidate_note:
      "lifted from an L1 relation, served labelled, ranked below every verified rung — extracted signal, not yet corroborated",
    sources: [
      {
        origin_key: "session:d2207ab1",
        kind: "memory",
        ref: "memory e5a8c320",
        detail: "“considering moving the reranker to a cross-encoder model”",
        at: "captured 2026-07-18 16:40",
      },
    ],
    windows: [
      {
        valid_at: "2026-07-18 16:40",
        invalid_at: null,
        expired_at: null,
        note: "speculative — the SPECULATIVE_REPLACES_MARKERS gate held this at candidate.",
      },
    ],
    ladder: [
      {
        at: "2026-07-18 16:40",
        description: "lifted from an L1 REPLACES relation",
        transition: { from: null, to: "candidate" },
      },
    ],
    applies_when: [],
  },
  {
    id: FACT_IDS.toggleGroup,
    project: "darkraise-ui",
    subject_name: "ToggleGroup",
    rel_type: "EMITS",
    object_name: "empty string on deselect",
    fact_text:
      "darkraise-ui's single-type ToggleGroup can emit \"\" when the active item is clicked again — consumers must guard the empty value.",
    verification_status: "corroborated",
    claim:
      "asserted by 2 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-24",
    meta: "asserted by 2 distinct origins",
    review_state: null,
    as_of: "2026-07-24",
    sources: [
      {
        origin_key: "repo:darkraise-ui",
        kind: "code",
        ref: "code src/components/toggle-group.tsx@77aa001",
        detail: "basis: deselect path calls onValueChange(\"\")",
        at: "indexed 2026-07-20",
      },
      {
        origin_key: "session:f00d4e21",
        kind: "memory",
        ref: "memory 41cc90b2",
        detail: "“ToggleGroup type=single emits \"\" — guard it before narrowing”",
        at: "captured 2026-07-24 08:30",
      },
    ],
    windows: [
      {
        valid_at: "2026-07-20 02:00",
        invalid_at: null,
        expired_at: null,
        note: "current live belief — window still open.",
      },
    ],
    ladder: [
      {
        at: "2026-07-20 02:00",
        description: "code parse asserted the deselect emission",
        transition: { from: null, to: "corroborated" },
      },
    ],
    applies_when: [],
  },
]

const RETRIEVAL_CLAIM =
  "asserted by 4 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-20"

export const CURATED_ARTICLES: DemoArticle[] = [
  {
    id: ARTICLE_IDS.cookieSecurity,
    project: "darkmem",
    subject_key: "cookie-security-defaults",
    subject_kind: "concept",
    title: "Cookie security defaults across environments",
    excerpt:
      "cookie_secure defaults to Secure only when environment=production; an explicit COOKIE_SECURE=false permits plain-HTTP LAN deploys without weakening the production default…",
    verification_status: "confirmed",
    claim:
      "asserted by 2 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-10, human-ratified",
    review_state: null,
    coverage: { ratio: 1, entailed: 2, total: 2 },
    stale: null,
    fact_set_hash: "6f21ab90c3e4",
    current_fact_set_hash: "6f21ab90c3e4",
    synthesized_at: "2026-07-05 03:00",
    meta: "ratified 2026-07-10",
    applies_when_label: "none — project-neutral",
    sections: [
      {
        label: "Defaults & overrides",
        sentences: [
          {
            text: "cookie_secure is tri-state: left unset, the Secure flag is applied only when environment=production, so development deploys never fight the browser over plain HTTP.",
            cite: "F1",
          },
          {
            text: "An explicit COOKIE_SECURE=false permits login over plain-HTTP LAN deploys without weakening the production default.",
            cite: "F2",
          },
        ],
      },
    ],
    citations: [
      {
        key: "F1",
        fact_id: FACT_IDS.cookieSecure,
        claim_span: "[0,168)",
        quote:
          "cookie_secure is tri-state: unset means the Secure flag is applied only when environment=production",
      },
      {
        key: "F2",
        fact_id: FACT_IDS.cookieLan,
        claim_span: "[169,291)",
        quote:
          "an explicit COOKIE_SECURE=false permits login over plain-HTTP LAN deploys without weakening the production default",
      },
    ],
    supersedes: null,
    superseded_by: null,
  },
  {
    id: ARTICLE_IDS.retrievalFusion,
    project: "darkmem",
    subject_key: "retrieval-fusion-weights",
    subject_kind: "concept",
    title: "Retrieval fusion weights — how darkmem ranks results",
    excerpt:
      "Hybrid search fuses semantic and keyword channels via Reciprocal Rank Fusion (k=60), weighted 0.7 toward the semantic side by default; a reranker, when enabled, rescores only the top 40 fused rows…",
    verification_status: "corroborated",
    claim: RETRIEVAL_CLAIM,
    review_state: null,
    coverage: { ratio: 0.8, entailed: 4, total: 5 },
    coverage_note:
      "One drafted sentence — “the keyword channel is disabled entirely for queries under three tokens” — failed the entailment check against its proposed citation (an unverified over-generalisation the synthesis model proposed) and was dropped before shipping. Every sentence rendered below is one of the 4 that passed; nothing uncited or unentailed is ever shown as knowledge.",
    stale: null,
    fact_set_hash: "8b31e9d2f4a7",
    current_fact_set_hash: "8b31e9d2f4a7",
    synthesized_at: "2026-07-19 03:00",
    meta: "asserted across 4 facts",
    applies_when_label: "none — project-neutral",
    sections: [
      {
        label: "Fusion",
        sentences: [
          {
            text: "Hybrid search combines the semantic and keyword channels via reciprocal rank fusion with k=60, and the fused rrf_score is the ordering signal consumers must prefer.",
            cite: "F1",
          },
          {
            text: "The semantic side is weighted 0.7 by default against the keyword channel's 0.3 before fusion.",
            cite: "F2",
          },
        ],
      },
      {
        label: "Reranking & degradation",
        sentences: [
          {
            text: "When reranker_enabled, only the top 40 fused rows are LLM-scored; the unscored tail is appended in its original fused order rather than re-ranked.",
            cite: "F3",
          },
          {
            text: "If one retrieval channel fails, fusion degrades to the surviving channel rather than narrowing the result set — a single-channel failure never silently returns fewer rows.",
            cite: "F4",
          },
        ],
      },
    ],
    citations: [
      {
        key: "F1",
        fact_id: FACT_IDS.hybridRrf,
        claim_span: "[0,171)",
        quote:
          "hybrid_search combines the semantic and keyword channels via reciprocal rank fusion with k=60",
      },
      {
        key: "F2",
        fact_id: FACT_IDS.semanticWeight,
        claim_span: "[172,266)",
        quote:
          "semantic_weight defaults to 0.7 in the RRF fusion formula (k=60)",
      },
      {
        key: "F3",
        fact_id: FACT_IDS.rerankTop40,
        claim_span: "[270,421)",
        quote:
          "when reranker_enabled, RerankerService LLM-scores only the top 40 RRF-ranked rows",
      },
      {
        key: "F4",
        fact_id: FACT_IDS.degradedChannel,
        claim_span: "[422,596)",
        quote:
          "when one retrieval channel fails, hybrid search degrades to the surviving channel rather than narrowing the result set",
      },
    ],
    supersedes: ARTICLE_IDS.retrievalFusionV1,
    superseded_by: null,
  },
  {
    id: ARTICLE_IDS.retrievalFusionV1,
    project: "darkmem",
    subject_key: "retrieval-fusion-weights",
    subject_kind: "concept",
    title: "Retrieval fusion weights — how darkmem ranks results (v1)",
    excerpt:
      "Hybrid search fuses semantic and keyword channels via Reciprocal Rank Fusion (k=60), weighted 0.7 toward the semantic side by default…",
    verification_status: "superseded",
    claim: null,
    review_state: null,
    coverage: { ratio: 1, entailed: 2, total: 2 },
    stale: null,
    fact_set_hash: "21c4f0b3d9a4",
    current_fact_set_hash: "8b31e9d2f4a7",
    synthesized_at: "2026-06-30 03:00",
    meta: "superseded 2026-07-19",
    applies_when_label: "none — project-neutral",
    sections: [
      {
        label: "Fusion",
        sentences: [
          {
            text: "Hybrid search combines the semantic and keyword channels via reciprocal rank fusion with k=60.",
            cite: "F1",
          },
          {
            text: "The semantic side is weighted 0.7 by default against the keyword channel's 0.3 before fusion.",
            cite: "F2",
          },
        ],
      },
    ],
    citations: [
      {
        key: "F1",
        fact_id: FACT_IDS.hybridRrf,
        claim_span: "[0,96)",
        quote:
          "hybrid_search combines the semantic and keyword channels via reciprocal rank fusion with k=60",
      },
      {
        key: "F2",
        fact_id: FACT_IDS.semanticWeight,
        claim_span: "[97,191)",
        quote:
          "semantic_weight defaults to 0.7 in the RRF fusion formula (k=60)",
      },
    ],
    supersedes: null,
    superseded_by: ARTICLE_IDS.retrievalFusion,
    last_rung_note:
      "last known rung before superseding: corroborated — asserted by 3 distinct origins of kinds [code, memory], no known contradiction, as of 2026-06-30 (not rendered as a live badge; the terminal status replaces it). This early synthesis only had two corroborated facts to draw from — the reranker and degradation facts had not corroborated yet; their later corroboration changed fact_set_hash, this article was labelled stale, and a debounced re-synthesis superseded it. The citations still resolve to live facts — nothing about supersession invalidates a fact, only the article that read it.",
  },
  {
    id: ARTICLE_IDS.degradedChannel,
    project: "darkmem",
    subject_key: "hybrid-degraded-channel",
    subject_kind: "concept",
    title: "Hybrid search fusion — degraded-channel behaviour",
    excerpt:
      "When one retrieval channel fails, darkmem degrades to the surviving channel rather than narrowing the result set; a single-channel failure never silently returns fewer rows…",
    verification_status: "corroborated",
    claim:
      "asserted by 2 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-12",
    review_state: null,
    coverage: { ratio: 0.67, entailed: 2, total: 3 },
    coverage_note:
      "One drafted sentence about retry semantics failed entailment and was dropped before shipping.",
    stale: {
      since: "2026-07-23",
      reason:
        "On 2026-07-23 a new fact about reranker fallback under channel failure corroborated for this subject, changing its verified fact set and therefore its fact_set_hash. Re-synthesis is debounced in the dream job and will supersede this article once the new draft clears the grounding gate again; if it fails grounding instead, this standing article is left exactly as-is.",
    },
    fact_set_hash: "9920acd17e55",
    current_fact_set_hash: "c7d4a10f92b6",
    synthesized_at: "2026-07-12 03:00",
    meta: "stale since 2026-07-23",
    applies_when_label: "none — project-neutral",
    sections: [
      {
        label: "Degrade, never narrow",
        sentences: [
          {
            text: "When one retrieval channel fails, hybrid search degrades to the surviving channel rather than narrowing the result set.",
            cite: "F1",
          },
          {
            text: "Code search cannot degrade the same way — it is semantic-only, since the code-chunk partitions carry no FTS column to fuse with.",
            cite: "F2",
          },
        ],
      },
    ],
    citations: [
      {
        key: "F1",
        fact_id: FACT_IDS.degradedChannel,
        claim_span: "[0,121)",
        quote:
          "when one retrieval channel fails, hybrid search degrades to the surviving channel rather than narrowing the result set",
      },
      {
        key: "F2",
        fact_id: FACT_IDS.codeSearch,
        claim_span: "[122,254)",
        quote:
          "search_code is semantic-only — the code_chunk_embeddings__<slug> partitions carry no FTS column",
      },
    ],
    supersedes: null,
    superseded_by: null,
  },
  {
    id: ARTICLE_IDS.llmPurposes,
    project: "darkmem",
    subject_key: "llm-purpose-routing",
    subject_kind: "concept",
    title: "LLM purpose routing across six roles",
    excerpt:
      "Six LLM purposes — embedding, extraction, classification, reasoning, summarization, reranker — each carry a provider_name pointing at a shared llm_providers row, so rotating that row's credential reaches every purpose pointed at it…",
    verification_status: "corroborated",
    claim:
      "asserted by 2 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-10",
    review_state: null,
    coverage: { ratio: 1, entailed: 2, total: 2 },
    stale: null,
    fact_set_hash: "3d0f81b6aa29",
    current_fact_set_hash: "3d0f81b6aa29",
    synthesized_at: "2026-07-10 03:00",
    meta: "asserted across 1 fact",
    applies_when_label: "none — project-neutral",
    sections: [
      {
        label: "Shared connection",
        sentences: [
          {
            text: "Six LLM purposes — embedding, extraction, classification, reasoning, summarization, reranker — each carry a provider_name pointing at a shared llm_providers row.",
            cite: "F1",
          },
          {
            text: "Because several purposes can point at the same row, rotating that row's credential now reaches every purpose pointed at it in one edit.",
            cite: "F2",
          },
        ],
      },
    ],
    citations: [
      {
        key: "F1",
        fact_id: FACT_IDS.llmPurposes,
        claim_span: "[0,161)",
        quote:
          "six LLM purposes each carry a provider_name pointing at a shared llm_providers row",
      },
      {
        key: "F2",
        fact_id: FACT_IDS.llmPurposes,
        claim_span: "[162,287)",
        quote:
          "rotating that row's credential reaches every purpose pointed at it in one edit",
      },
    ],
    supersedes: null,
    superseded_by: null,
  },
  {
    id: ARTICLE_IDS.providerQuirks,
    project: "darkmem",
    subject_key: "llm-provider-quirks",
    subject_kind: "concept",
    title: "LLM provider quirks — api_kind dispatch table",
    excerpt:
      "Vendor auth and reasoning-control quirks live behind api_kind — but most of this draft's claims found no verified fact to ground them…",
    verification_status: "candidate",
    claim: null,
    review_state: "open",
    coverage: { ratio: 0.33, entailed: 3, total: 9 },
    coverage_note:
      "6 of 9 drafted sentences found no confirmed-or-corroborated fact entailing them and were dropped; the 3 that passed render below. Coverage fell below the configured threshold, so this article never shipped as corroborated — it carries review_state=open and sits in the Review queue.",
    ungrounded_note:
      "flagged ungrounded by article_synthesis — withheld from the corroborated Articles view and routed to Review; the draft still renders here, coverage labelled, never hidden.",
    stale: null,
    fact_set_hash: "b17c40e92d38",
    current_fact_set_hash: "b17c40e92d38",
    synthesized_at: "2026-07-22 03:00",
    meta: "claim-support coverage 0.33",
    applies_when_label: "none — project-neutral",
    sections: [
      {
        label: "What survived grounding",
        sentences: [
          {
            text: "Each of the six LLM purposes carries a provider_name pointing at a shared llm_providers row, which is where vendor rotation happens.",
            cite: "F1",
          },
          {
            text: "The reranker purpose, when enabled, scores only the top 40 fused rows.",
            cite: "F2",
          },
          {
            text: "Code search never consults a keyword channel at all — it is semantic-only.",
            cite: "F3",
          },
        ],
      },
    ],
    citations: [
      {
        key: "F1",
        fact_id: FACT_IDS.llmPurposes,
        claim_span: "[0,131)",
        quote:
          "six LLM purposes each carry a provider_name pointing at a shared llm_providers row",
      },
      {
        key: "F2",
        fact_id: FACT_IDS.rerankTop40,
        claim_span: "[132,204)",
        quote:
          "RerankerService LLM-scores only the top 40 RRF-ranked rows",
      },
      {
        key: "F3",
        fact_id: FACT_IDS.codeSearch,
        claim_span: "[205,284)",
        quote: "search_code is semantic-only",
      },
    ],
    supersedes: null,
    superseded_by: null,
  },
]

export const CURATED_COMMUNITIES: DemoCommunity[] = [
  {
    id: "comm-2026-07-22-01",
    label: "Hybrid search & RRF weighting",
    member_count: 17,
    impact: "high",
    dominant_entities: [
      "hybrid_search_enabled",
      "rrf_score",
      "semantic_weight",
      "reranker",
    ],
    report:
      "Memories in this cluster converge on tuning the RRF fusion weight and troubleshooting keyword-only degradation.",
    report_pending: null,
    note: "Already has a live article — “Retrieval fusion weights — how darkmem ranks results.” No pin suggestion.",
  },
  {
    id: "comm-2026-07-22-02",
    label: "Retry & backoff tuning",
    member_count: 9,
    impact: "medium",
    dominant_entities: ["retry_backoff_strategy", "job_registry"],
    report: null,
    report_pending: "not yet generated — next detection run: 2026-07-27",
    note: null,
  },
  {
    id: "comm-2026-07-22-03",
    label: "Cookie & session security",
    member_count: 22,
    impact: "high",
    dominant_entities: ["cookie_secure", "jwt_secret", "trust_proxy_headers"],
    report:
      "Sessions cluster around the Secure-cookie/proxy-trust defaults and their plain-HTTP LAN exceptions.",
    report_pending: null,
    note: "Stable since the last two runs — no new/grown reason to nominate.",
  },
]

export const CURATED_PIN_SUGGESTIONS: DemoPinSuggestion[] = [
  {
    id: "pin-retry-backoff",
    subject: "retry_backoff_strategy (concept)",
    reason: "new community",
    reason_kind: "new",
    supporting_community: "Retry & backoff tuning",
    member_count: 9,
    anchored_fact_count: 3,
    decision: null,
  },
  {
    id: "pin-confidence-gamma",
    subject: "confidence_rank_gamma (concept)",
    reason: "grown: 8 → 15 members",
    reason_kind: "grown",
    supporting_community: "Hybrid search & RRF weighting",
    member_count: 15,
    anchored_fact_count: 6,
    decision: null,
  },
]

export const CURATED_REVIEW_ITEMS: DemoReviewItem[] = [
  {
    id: "review-reranker-default",
    kind: "fact",
    target_id: FACT_IDS.rerankerDefault,
    layer: 2,
    title: "the reranker's default state in production",
    state_tag: "review_state: open",
    claim_line:
      "disputed: 2 origins assert the reranker is enabled by default in production, 1 origin asserts the reranker is opt-in per profile and disabled by default, as of 2026-07-21",
    badge: "disputed",
    rank_note:
      "retrieval frequency — hit 47×/7d; subject salience — core ranking config",
    dispute_sides: [
      {
        assertion: "asserts X — the reranker is enabled by default in production",
        origins: "2 origins · kinds [code, memory]",
      },
      {
        assertion:
          "asserts not-X — the reranker is opt-in per profile, disabled by default",
        origins: "1 origin · kind [human]",
      },
    ],
    decayed: false,
  },
  {
    id: "review-provider-quirks",
    kind: "article",
    target_id: ARTICLE_IDS.providerQuirks,
    layer: 3,
    title: "“LLM provider quirks — api_kind dispatch table”",
    state_tag: "review_state: open",
    coverage_pct: 33,
    note: "6 of 9 inline claim citations have no matching confirmed-or-corroborated fact behind them — flagged ungrounded by article_synthesis; the article still renders, coverage is labelled not hidden.",
    rank_note:
      "retrieval frequency — hit 31×/7d; subject salience — high-traffic settings page",
    decayed: false,
  },
  {
    id: "review-extraction-model",
    kind: "fact",
    target_id: FACT_IDS.extractionModel,
    layer: 2,
    title: "the extraction purpose's serving model",
    state_tag: "review_state: open",
    claim_line:
      "disputed: 2 origins assert extraction purpose uses glm-4.5-flash, 1 origin asserts extraction purpose uses gpt-5.4-mini, as of 2026-07-15",
    badge: "disputed",
    rank_note:
      "retrieval frequency — hit 19×/7d; subject salience — pipeline configuration",
    dispute_sides: [
      {
        assertion: "asserts X — the extraction purpose is served by glm-4.5-flash",
        origins: "2 origins · kind [memory]",
      },
      {
        assertion: "asserts not-X — the extraction purpose is served by gpt-5.4-mini",
        origins: "1 origin · kind [memory]",
      },
    ],
    decayed: false,
  },
  {
    id: "review-test-db",
    kind: "fact",
    target_id: FACT_IDS.testDb,
    layer: 2,
    title: "darkmem_test lives on the dev-compose Postgres at 127.0.0.1:5433",
    state_tag: "review_state: open",
    badge: "corroborated",
    under_sourced: true,
    note: "origin count dropped to 1 after a duplicate memory was pruned by dreaming; will demote to candidate after verification_demote_grace_cycles consecutive recompute cycles unless re-corroborated — the label keeps retrieval honest now, the grace period absorbs transient churn.",
    rank_note:
      "retrieval frequency — hit 12×/7d; subject salience — referenced by CLAUDE.md test setup",
    decayed: false,
  },
  {
    id: "review-mcp-hosts",
    kind: "fact",
    target_id: FACT_IDS.mcpHosts,
    layer: 2,
    title: "MCP_ALLOWED_HOSTS' default",
    state_tag: "review_state: open · stale_labelled",
    badge: "disputed",
    rank_note: "priority decayed off the active queue — status unchanged",
    note: "Unreviewed 34 days (past dispute_stale_days=30) — 1 origin asserts “MCP_ALLOWED_HOSTS defaults to * (open)” vs 1 origin asserting “empty default — localhost-only.” Still disputed, still served labelled with both sides.",
    dispute_sides: [
      {
        assertion: "asserts X — MCP_ALLOWED_HOSTS defaults to * and any Host is served",
        origins: "1 origin · kind [memory]",
      },
      {
        assertion: "asserts not-X — the default is empty: localhost-only",
        origins: "1 origin · kind [memory]",
      },
    ],
    decayed: true,
    decayed_note: "decayed — still served labelled",
  },
]

export const CURATED_HYGIENE: HygieneQueueState = {
  duplicates: [
    {
      id: "dup-cookie-secure",
      connector: "≈ 0.93 similarity · dreaming associative edge · flagged 2026-07-22",
      rows: [
        {
          id: "dup-cookie-secure-a",
          text: "cookie_secure defaults to Secure only when environment=production",
          meta: "captured 2026-06-09",
        },
        {
          id: "dup-cookie-secure-b",
          text: "COOKIE_SECURE decouples the Secure flag from environment — set false for plain-HTTP LAN deploys",
          why: "why ranked here — both memories co-retrieved in 5 of the last 10 cookie_secure searches",
          meta: "captured 2026-06-09",
        },
      ],
    },
    {
      id: "dup-reranker-top40",
      connector: "≈ 0.89 similarity · dreaming associative edge · flagged 2026-07-20",
      rows: [
        {
          id: "dup-reranker-top40-a",
          text: "the reranker LLM-scores the top 40 RRF-ranked rows after fusion",
          meta: "captured 2026-05-01",
        },
        {
          id: "dup-reranker-top40-b",
          text: "RerankerService scores the top 40 fused rows before final ordering",
          why: "why ranked here — subject salience: “reranker” referenced by 3 active facts",
          meta: "captured 2026-07-03",
        },
      ],
    },
  ],
  lowConfidence: [
    {
      id: "lowconf-chunking",
      text: "might be worth swapping the article synthesiser's chunking strategy to spans instead of blocks",
      why: "why ranked here — confidence well under the 0.75 default, never retrieved since capture",
      meta: "confidence 0.31 · captured 2026-07-21",
    },
    {
      id: "lowconf-vectors-route",
      text: "possibly deprecate the /vectors route once Knowledge fully ships",
      why: "why ranked here — 0 retrievals in 30 days, low salience",
      meta: "confidence 0.28 · captured 2026-06-20",
    },
  ],
  expiring: [
    {
      id: "exp-uvloop-pin",
      text: "temporary workaround: pin uvloop<0.20 until the upstream asyncio fix ships",
      why: "why ranked here — expires_at inside the lookahead window, still referenced by an open job config",
      meta: "expires_at 2026-07-27 · in 3 days",
    },
    {
      id: "exp-glm-trial",
      text: "trial LLM profile: glm-4.5-flash evaluation window",
      why: "why ranked here — expires_at inside the lookahead window",
      meta: "expires_at 2026-07-30 · in 6 days",
    },
  ],
  lineage: [
    {
      id: "chain-reranker-topk",
      connector: "chain depth 2 · still linked from 1 active memory",
      links: [
        {
          text: "reranker top-K fixed at 20 rows",
          status: "superseded",
          meta: "superseded 2026-05-01",
        },
        {
          text: "reranker top-K raised to 40 rows",
          status: "superseded",
          meta: "superseded 2026-06-15",
        },
        {
          text: "reranker top-K raised to 40 rows, applied after RRF fusion",
          status: "active",
          meta: "active · current",
          why: "why ranked here — active head of a 2-deep chain, both ancestors past dream_undo_retention",
        },
      ],
    },
  ],
}

export const LAST_DETECTION_RUN = "2026-07-22"


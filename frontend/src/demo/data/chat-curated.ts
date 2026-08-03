import type { DemoChatThread, DemoTurnContext } from "../types"

// Chat rides the same one ranking path as Memories (invariant 17), so every
// turn context reuses the identical layer-chip / verification-badge / trace
// vocabulary — never a chat-only honesty treatment.

const RANKING_TURN_CONTEXT: DemoTurnContext = {
  sources_line: "3 sources used this turn — see context panel",
  degraded: null,
  rows: [
    {
      id: "ctx-gamma",
      layer: 2,
      verification: "corroborated",
      subject_text:
        "confidence_rank_gamma defaults to 0 — weighting is inactive until raised above zero",
      badge_line:
        "asserted by 3 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-20",
      trace: {
        channels: [
          { name: "semantic", fraction: 0.82, display: "0.82" },
          { name: "keyword", fraction: 0.61, display: "0.61" },
        ],
        rrf_score: 0.0312,
        summary:
          "strong semantic match on the flag name, reinforced by an exact keyword hit",
      },
    },
    {
      id: "ctx-hybrid",
      layer: 2,
      verification: "confirmed",
      subject_text: "hybrid_search_enabled is on by default; RRF k=60",
      badge_line:
        "asserted by 4 distinct origins of kinds [code, human, memory], no known contradiction, as of 2026-07-15, human-ratified",
      trace: {
        channels: [
          { name: "semantic", fraction: 0.74, display: "0.74" },
          { name: "keyword", fraction: 0.88, display: "0.88" },
        ],
        rrf_score: 0.0298,
        summary: "exact keyword hit on hybrid_search_enabled, semantic close",
      },
    },
    {
      id: "ctx-reranker-memory",
      layer: 0,
      verification: null,
      subject_text: "“Considering moving the reranker to a cross-encoder model”",
      badge_line:
        "no verification badge on this row — badge: null, verification_status: null (L0 memories carry lifecycle, not the ladder)",
    },
  ],
  exclusions: [
    {
      count: 1,
      reason: "status is superseded, not active",
      tag: "by_status",
    },
  ],
}

const DEGRADED_TURN_CONTEXT: DemoTurnContext = {
  sources_line: "2 sources used this turn, keyword-only — see context panel",
  degraded: "showing keyword-only results — semantic search unavailable",
  rows: [
    {
      id: "ctx-cookie-fact",
      layer: 2,
      verification: "corroborated",
      subject_text:
        "cookie_secure is tri-state: unset = Secure only in production; explicit false allows login over plain-HTTP LAN",
      badge_line:
        "asserted by 3 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-18",
      channel: "keyword",
    },
    {
      id: "ctx-cookie-memory",
      layer: 0,
      verification: null,
      subject_text:
        "“Set COOKIE_SECURE=false on the LAN box — login kept bouncing until the Secure flag came off”",
      badge_line:
        "no verification badge on this row — badge: null (L0 memories carry lifecycle, not the ladder)",
      channel: "keyword",
    },
  ],
  exclusions: [],
}

const SUPERSESSION_TURN_CONTEXT: DemoTurnContext = {
  sources_line: "2 sources used this turn — see context panel",
  degraded: null,
  rows: [
    {
      id: "ctx-window-fact",
      layer: 2,
      verification: "corroborated",
      subject_text: "SUPERSESSION_WINDOW_DAYS defaults to 90",
      badge_line:
        "asserted by 3 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-12",
      trace: {
        channels: [
          { name: "semantic", fraction: 0.79, display: "0.79" },
          { name: "keyword", fraction: 0.7, display: "0.70" },
        ],
        rrf_score: 0.0305,
        summary: "both channels rank the supersession-window fact first",
      },
    },
    {
      id: "ctx-window-memory",
      layer: 0,
      verification: null,
      subject_text:
        "“Candidates older than the window never flip — burned us on the March backfill”",
      badge_line:
        "no verification badge on this row — badge: null (L0 memories carry lifecycle, not the ladder)",
    },
  ],
  exclusions: [],
}

export const CURATED_CHAT_THREADS: DemoChatThread[] = [
  {
    id: "thread-ranking",
    title: "Retrieval & ranking questions",
    updated_label: "just now",
    messages: [
      {
        id: "m1",
        role: "user",
        content: "What does the supersession window default to?",
      },
      {
        id: "m2",
        role: "assistant",
        content:
          "90 days — SUPERSESSION_WINDOW_DAYS = 90. A candidate only flips an older row to superseded if it's still active and inside that window.",
        context: SUPERSESSION_TURN_CONTEXT,
      },
      {
        id: "m3",
        role: "user",
        content: "Is the reranker on by default, and what's our RRF k?",
      },
      {
        id: "m4",
        role: "assistant",
        content:
          "Yes — hybrid_search_enabled is on by default, fusing semantic and keyword channels via Reciprocal Rank Fusion with k = 60. The reranker is a separate flag (reranker_enabled) and stays off by default.",
        bullets: [
          "hybrid_search_enabled — on, RRF k=60",
          "reranker_enabled — off by default",
          "confidence_rank_gamma — 0 (inactive until raised above zero)",
        ],
        context: RANKING_TURN_CONTEXT,
      },
    ],
  },
  {
    id: "thread-cookie",
    title: "cookie_secure LAN login flow",
    updated_label: "1d ago",
    messages: [
      {
        id: "m1",
        role: "user",
        content: "Why did LAN login fail until COOKIE_SECURE went false?",
      },
      {
        id: "m2",
        role: "assistant",
        content:
          "cookie_secure is tri-state: unset means the Secure flag applies only when environment=production, so over plain-HTTP LAN the browser refuses to send the cookie. Setting COOKIE_SECURE=false explicitly allows the login cookie on HTTP. This turn degraded to the keyword channel only — see the caution banner in the context panel.",
        context: DEGRADED_TURN_CONTEXT,
      },
    ],
  },
  {
    id: "thread-savepoints",
    title: "pipeline phase 5 write savepoints",
    updated_label: "1w ago",
    messages: [
      {
        id: "m1",
        role: "user",
        content: "Why two savepoints in the write phase?",
      },
      {
        id: "m2",
        role: "assistant",
        content:
          "Phase 5 commits in two savepoints — A: vector upsert plus memory-row enrichment; B: the entity/relationship graph, technologies denorm, and supersession — so a graph failure never rolls back the vector write.",
        context: {
          sources_line: "1 source used this turn — see context panel",
          degraded: null,
          rows: [
            {
              id: "ctx-savepoint-fact",
              layer: 2,
              verification: "corroborated",
              subject_text:
                "Phase-5 writes split into savepoint A (vector) and savepoint B (graph) so a graph failure does not roll back the vector write",
              badge_line:
                "asserted by 2 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-08",
            },
          ],
          exclusions: [],
        },
      },
    ],
  },
]

// The canned reply appended by the demo store's sendChatMessage — honest
// about being a skeleton, and honest about where a real answer's labels live.
export const DEMO_REPLY_CONTENT =
  "This is the demo skeleton — replies are canned, not generated. In the real app this turn would stream an answer composed only from the ranked, labelled rows shown in the context panel."

export const DEMO_REPLY_CONTEXT: DemoTurnContext = {
  sources_line: "2 sources used this turn — see context panel",
  degraded: null,
  rows: [
    {
      id: "ctx-demo-fact",
      layer: 2,
      verification: "corroborated",
      subject_text:
        "the demo store serves every surface in this skeleton; no backend calls are made",
      badge_line:
        "asserted by 2 distinct origins of kinds [code, human], no known contradiction, as of 2026-07-25",
    },
    {
      id: "ctx-demo-memory",
      layer: 0,
      verification: null,
      subject_text: "“Wave 3 wires Chat to the demo layer, real streaming comes later”",
      badge_line:
        "no verification badge on this row — badge: null (L0 memories carry lifecycle, not the ladder)",
    },
  ],
  exclusions: [],
}

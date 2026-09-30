import type { DemoCodeGraph } from "@/features/code/types"
import type { DemoIndexPhase, DemoRepo, DemoWiki } from "../types"

// The fixed 14-phase indexing pipeline topology (doc 10 §2). Phases 13–14
// are the two opt-in LLM-cost phases the reindex toggles gate.
export const INDEX_PHASE_LABELS: string[] = [
  "File discovery",
  "Parsing",
  "Structure",
  "Import resolution",
  "Named bindings",
  "Call tracing",
  "Inheritance",
  "Cross-file binding",
  "Community detection",
  "Process detection",
  "Validation",
  "Embeddings",
  "Enrich symbols",
  "Generate wiki",
]

const midIndexPhases: DemoIndexPhase[] = INDEX_PHASE_LABELS.map(
  (label, i) => ({
    n: i + 1,
    label,
    state:
      i + 1 < 6
        ? "done"
        : i + 1 === 6
          ? "current"
          : i + 1 >= 13
            ? "skipped"
            : "pending",
  }),
)

const BACKEND_WIKI: DemoWiki = {
  generated_at: "2026-07-20 04:12",
  head: "a1c9f02",
  sections: [
    {
      id: "overview",
      label: "Overview",
      paragraphs: [
        "backend/app is a FastAPI service organised into api/routes (REST), api/mcp (the FastMCP tool family mounted at /mcp), services (the ingestion pipeline and its supporting orchestration), repositories (graph, relational, and vector data access), and models/schemas. The process entry point is main.py, which also registers the seven periodic jobs through services/job_registry.py.",
      ],
    },
    {
      id: "ingestion",
      label: "Ingestion pipeline",
      paragraphs: [
        "ProcessingPipeline.process_batch is the central write path. It moves a batch of memories through five phases — content embed, extract-and-classify, entity embed with cache, dedup, and write — committing the vector and graph halves of phase five in separate savepoints so a graph failure never rolls back the vector write.",
      ],
      bullets: [
        {
          code: "services/pipeline.py",
          text: "phase orchestration, savepoint boundaries",
        },
        {
          code: "services/extraction_clean.py",
          text: "entity/relationship extraction",
        },
        {
          code: "services/code_pipeline.py",
          text: "this repository's own indexing path",
        },
      ],
    },
    {
      id: "api-routes",
      label: "api/routes",
      paragraphs: [
        "REST endpoints follow the repo convention: 201 on create, 204 on delete, 202 for async-accepted work, and POST .../search for complex queries. Auth rides the bundled nginx; the client IP is read from X-Real-IP when trust_proxy_headers is on.",
      ],
    },
    {
      id: "retrieval",
      label: "Retrieval",
      paragraphs: [
        "Default semantic search delegates to HybridSearchService.search: a semantic channel over the per-fingerprint memory_embeddings partition and a keyword channel over memories.search_vector, fused with Reciprocal Rank Fusion (k = 60, semantic_weight 0.7). Consumers order by rrf_score — the per-modality score key that survives on a row is the first-seen side's raw score, not the ordering signal.",
      ],
      bullets: [
        {
          code: "services/hybrid_search.py",
          text: "channel fan-out and RRF fusion",
        },
        {
          code: "services/reranker.py",
          text: "optional LLM rescoring of the top 40 fused rows",
        },
      ],
    },
  ],
}

export const CURATED_CODE_REPOS: DemoRepo[] = [
  {
    id: "repo-backend",
    name: "darkmem/backend",
    branch: "main",
    head: "e91a3f2",
    status: "ready",
    last_indexed_at: "2026-07-24 09:12 UTC",
    index_on_commit_enabled: true,
    debt: null,
    auto_provisioned: null,
    stale: null,
    error: null,
    phases: null,
    registered_note: null,
    wiki: BACKEND_WIKI,
    files: [
      "api/mcp/mcp_tools.py",
      "api/mcp/server.py",
      "api/routes/config.py",
      "api/routes/jobs.py",
      "api/routes/memories.py",
      "api/routes/repos.py",
      "api/routes/search.py",
      "config.py",
      "main.py",
      "models/entity.py",
      "models/memory.py",
      "repositories/graph.py",
      "repositories/relational.py",
      "repositories/vector.py",
      "schemas/memory.py",
      "services/code_pipeline.py",
      "services/extraction_clean.py",
      "services/hybrid_search.py",
      "services/job_registry.py",
      "services/llm_seed.py",
      "services/pipeline.py",
      "services/reranker.py",
      "taxonomy.py",
    ],
  },
  {
    id: "repo-frontend",
    name: "darkmem/frontend",
    branch: "main",
    head: "7c410ab",
    status: "ready",
    last_indexed_at: "2026-07-24 06:40 UTC",
    index_on_commit_enabled: true,
    debt: {
      queued_files: 168,
      note: "dependent files queued for reindex",
    },
    auto_provisioned: null,
    stale: null,
    error: null,
    phases: null,
    registered_note: null,
    wiki: null,
    files: [
      "src/app.tsx",
      "src/components/app-chrome/page-chrome.tsx",
      "src/components/timeline-scrubber.tsx",
      "src/demo/activity.ts",
      "src/demo/explore.ts",
      "src/demo/hooks.ts",
      "src/demo/knowledge.ts",
      "src/demo/memories.ts",
      "src/demo/store.ts",
      "src/demo/types.ts",
      "src/features/code/components/code-graph-tab.tsx",
      "src/features/knowledge/components/facts-tab.tsx",
      "src/lib/format.ts",
      "src/lib/timeline.ts",
      "src/main.tsx",
      "src/routes/__root.tsx",
      "src/routes/_authenticated.tsx",
      "src/routes/_authenticated/code.tsx",
      "src/routes/_authenticated/knowledge.tsx",
      "src/routes/_authenticated/memories.tsx",
      "src/styles/globals.css",
      "vite.config.ts",
    ],
  },
  {
    id: "repo-storefront",
    name: "acme-storefront-api",
    branch: "main",
    head: null,
    status: "registered",
    last_indexed_at: null,
    index_on_commit_enabled: true,
    debt: null,
    auto_provisioned: {
      on: "2026-07-22",
      from_memory:
        "“the storefront API lives at github.com/acme/storefront-api, deployed alongside checkout…”",
    },
    stale: null,
    error: null,
    phases: null,
    registered_note:
      "queued for first index",
    wiki: null,
    files: [],
  },
  {
    id: "repo-billing",
    name: "legacy-billing-service",
    branch: "main",
    head: "a12c9de",
    status: "indexing",
    last_indexed_at: "2026-07-17 22:30 UTC",
    index_on_commit_enabled: true,
    debt: null,
    auto_provisioned: null,
    stale: null,
    error: null,
    phases: midIndexPhases,
    registered_note: null,
    wiki: null,
    files: [],
  },
  {
    id: "repo-payments",
    name: "payments-service",
    branch: "main",
    head: "4b7e120",
    status: "stale",
    last_indexed_at: "2026-07-19 14:02 UTC",
    index_on_commit_enabled: true,
    debt: null,
    auto_provisioned: null,
    stale: {
      last_good_head: "4b7e120",
      last_good_at: "2026-07-19 14:02 UTC",
      cause:
        "community detection timed out.",
    },
    error: null,
    phases: null,
    registered_note: null,
    wiki: null,
    files: [
      "app/__init__.py",
      "app/charges.py",
      "app/ledger.py",
      "app/models.py",
      "app/settings.py",
      "app/webhooks/stripe.py",
      "tests/test_charges.py",
      "tests/test_ledger.py",
    ],
  },
  {
    id: "repo-tools",
    name: "internal-tools-cli",
    branch: "main",
    head: null,
    status: "error",
    last_indexed_at: null,
    index_on_commit_enabled: false,
    debt: null,
    auto_provisioned: null,
    stale: null,
    error: {
      headline: "Clone failed — 3 consecutive attempts",
      detail:
        "Indexing is disabled. Fix access to the remote, then reindex.",
      message:
        "git@github.com:acme/internal-tools-cli.git — Permission denied (publickey). Could not read from remote repository.",
    },
    phases: null,
    registered_note: null,
    wiki: null,
    files: [],
  },
]

// ---------------------------------------------------------------------------
// Demo code graphs — a representative sketch, not production physics.
// ---------------------------------------------------------------------------

const backendGraph: DemoCodeGraph = {
  repo_id: "repo-backend",
  communities: [
    { id: "c-ingest", label: "ingestion & pipeline", chart: 1 },
    { id: "c-retrieval", label: "retrieval & ranking", chart: 3 },
    { id: "c-mcp", label: "mcp tool surface", chart: 5 },
  ],
  nodes: [
    // ingestion & pipeline
    { id: "n-pipeline-py", name: "pipeline.py", kind: "file", file: "services/pipeline.py", community: "c-ingest" },
    { id: "n-processing-pipeline", name: "ProcessingPipeline", kind: "class", file: "services/pipeline.py", community: "c-ingest" },
    { id: "n-process-batch", name: "process_batch", kind: "method", file: "services/pipeline.py", community: "c-ingest" },
    { id: "n-extract-classify", name: "extract_and_classify", kind: "method", file: "services/pipeline.py", community: "c-ingest" },
    { id: "n-entity-embed", name: "entity_embed", kind: "method", file: "services/pipeline.py", community: "c-ingest" },
    { id: "n-dedup", name: "dedup_entities", kind: "method", file: "services/pipeline.py", community: "c-ingest" },
    { id: "n-write-graph", name: "write_graph", kind: "method", file: "services/pipeline.py", community: "c-ingest" },
    // retrieval & ranking
    { id: "n-hybrid-py", name: "hybrid_search.py", kind: "file", file: "services/hybrid_search.py", community: "c-retrieval" },
    { id: "n-hybrid-service", name: "HybridSearchService", kind: "class", file: "services/hybrid_search.py", community: "c-retrieval" },
    { id: "n-search", name: "search", kind: "method", file: "services/hybrid_search.py", community: "c-retrieval" },
    { id: "n-rrf", name: "rrf_fuse", kind: "function", file: "services/hybrid_search.py", community: "c-retrieval" },
    { id: "n-reranker", name: "RerankerService", kind: "class", file: "services/reranker.py", community: "c-retrieval" },
    { id: "n-conf-weight", name: "_apply_confidence_weighting", kind: "function", file: "services/hybrid_search.py", community: "c-retrieval" },
    // mcp tool surface
    { id: "n-mcp-py", name: "mcp_tools.py", kind: "file", file: "api/mcp/mcp_tools.py", community: "c-mcp" },
    { id: "n-memory-search", name: "memory_search", kind: "function", file: "api/mcp/mcp_tools.py", community: "c-mcp" },
    { id: "n-memory-add", name: "memory_add", kind: "function", file: "api/mcp/mcp_tools.py", community: "c-mcp" },
    { id: "n-batch-add", name: "memory_batch_add", kind: "function", file: "api/mcp/mcp_tools.py", community: "c-mcp" },
    { id: "n-code-search", name: "code_search", kind: "function", file: "api/mcp/mcp_tools.py", community: "c-mcp" },
  ],
  edges: [
    { source: "n-pipeline-py", target: "n-processing-pipeline", type: "CONTAINS" },
    { source: "n-processing-pipeline", target: "n-process-batch", type: "CONTAINS" },
    { source: "n-process-batch", target: "n-extract-classify", type: "CALLS" },
    { source: "n-process-batch", target: "n-entity-embed", type: "CALLS" },
    { source: "n-process-batch", target: "n-dedup", type: "CALLS" },
    { source: "n-process-batch", target: "n-write-graph", type: "CALLS" },
    { source: "n-hybrid-py", target: "n-hybrid-service", type: "CONTAINS" },
    { source: "n-hybrid-service", target: "n-search", type: "CONTAINS" },
    { source: "n-search", target: "n-rrf", type: "CALLS" },
    { source: "n-search", target: "n-reranker", type: "CALLS" },
    { source: "n-search", target: "n-conf-weight", type: "CALLS" },
    { source: "n-mcp-py", target: "n-memory-search", type: "CONTAINS" },
    { source: "n-mcp-py", target: "n-memory-add", type: "CONTAINS" },
    { source: "n-mcp-py", target: "n-code-search", type: "CONTAINS" },
    { source: "n-memory-add", target: "n-process-batch", type: "CALLS" },
    { source: "n-batch-add", target: "n-process-batch", type: "CALLS" },
    { source: "n-memory-search", target: "n-search", type: "CALLS" },
    { source: "n-code-search", target: "n-hybrid-service", type: "CALLS" },
  ],
  processes: [
    {
      id: "p-ingest",
      label: "memory ingestion pipeline",
      steps: [
        "n-process-batch",
        "n-extract-classify",
        "n-entity-embed",
        "n-dedup",
        "n-write-graph",
      ],
    },
    {
      id: "p-retrieval",
      label: "hybrid retrieval flow",
      steps: ["n-memory-search", "n-search", "n-rrf", "n-reranker"],
    },
    {
      id: "p-mcp",
      label: "mcp tool dispatch",
      steps: ["n-memory-add", "n-batch-add", "n-process-batch"],
    },
  ],
}

const frontendGraph: DemoCodeGraph = {
  repo_id: "repo-frontend",
  communities: [
    { id: "c-routes", label: "routes & shell", chart: 1 },
    { id: "c-demo", label: "demo data layer", chart: 3 },
  ],
  nodes: [
    { id: "f-root", name: "__root.tsx", kind: "file", file: "src/routes/__root.tsx", community: "c-routes" },
    { id: "f-memories", name: "memories.tsx", kind: "file", file: "src/routes/_authenticated/memories.tsx", community: "c-routes" },
    { id: "f-knowledge", name: "knowledge.tsx", kind: "file", file: "src/routes/_authenticated/knowledge.tsx", community: "c-routes" },
    { id: "f-code", name: "code.tsx", kind: "file", file: "src/routes/_authenticated/code.tsx", community: "c-routes" },
    { id: "f-store", name: "useDemoStore", kind: "function", file: "src/demo/store.ts", community: "c-demo" },
    { id: "f-hooks", name: "hooks.ts", kind: "file", file: "src/demo/hooks.ts", community: "c-demo" },
    { id: "f-types", name: "types.ts", kind: "file", file: "src/demo/types.ts", community: "c-demo" },
    { id: "f-search", name: "searchMemories", kind: "function", file: "src/demo/memories.ts", community: "c-demo" },
  ],
  edges: [
    { source: "f-root", target: "f-memories", type: "ROUTES" },
    { source: "f-root", target: "f-knowledge", type: "ROUTES" },
    { source: "f-root", target: "f-code", type: "ROUTES" },
    { source: "f-memories", target: "f-hooks", type: "IMPORTS" },
    { source: "f-knowledge", target: "f-hooks", type: "IMPORTS" },
    { source: "f-hooks", target: "f-store", type: "IMPORTS" },
    { source: "f-store", target: "f-types", type: "IMPORTS" },
    { source: "f-memories", target: "f-search", type: "CALLS" },
  ],
  processes: [
    {
      id: "p-demo-read",
      label: "demo store read path",
      steps: ["f-memories", "f-hooks", "f-store"],
    },
  ],
}

// payments-service — the LAST-GOOD graph (T1): still served after the failed
// run, marked stale by the toolbar, never wiped.
const paymentsGraph: DemoCodeGraph = {
  repo_id: "repo-payments",
  communities: [
    { id: "c-charge", label: "charge lifecycle", chart: 1 },
    { id: "c-ledger", label: "ledger & reconciliation", chart: 5 },
  ],
  nodes: [
    { id: "p-charges-py", name: "charges.py", kind: "file", file: "app/charges.py", community: "c-charge" },
    { id: "p-charge", name: "Charge", kind: "class", file: "app/charges.py", community: "c-charge" },
    { id: "p-capture", name: "capture", kind: "method", file: "app/charges.py", community: "c-charge" },
    { id: "p-refund", name: "refund", kind: "method", file: "app/charges.py", community: "c-charge" },
    { id: "p-ledger-py", name: "ledger.py", kind: "file", file: "app/ledger.py", community: "c-ledger" },
    { id: "p-post-entry", name: "post_entry", kind: "function", file: "app/ledger.py", community: "c-ledger" },
    { id: "p-reconcile", name: "reconcile", kind: "function", file: "app/ledger.py", community: "c-ledger" },
  ],
  edges: [
    { source: "p-charges-py", target: "p-charge", type: "CONTAINS" },
    { source: "p-charge", target: "p-capture", type: "CONTAINS" },
    { source: "p-charge", target: "p-refund", type: "CONTAINS" },
    { source: "p-capture", target: "p-post-entry", type: "CALLS" },
    { source: "p-refund", target: "p-post-entry", type: "CALLS" },
    { source: "p-ledger-py", target: "p-reconcile", type: "CONTAINS" },
    { source: "p-reconcile", target: "p-post-entry", type: "CALLS" },
  ],
  processes: [
    {
      id: "p-charge-flow",
      label: "charge capture flow",
      steps: ["p-capture", "p-post-entry", "p-reconcile"],
    },
  ],
}

export const CURATED_CODE_GRAPHS: DemoCodeGraph[] = [
  backendGraph,
  frontendGraph,
  paymentsGraph,
]

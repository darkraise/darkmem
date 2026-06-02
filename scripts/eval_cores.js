export const meta = {
  name: 'darkmem-core-eval',
  description: 'Deep accuracy/reliability/efficiency review of the memory + code-analysis cores; analyze then adversarially verify each finding',
  phases: [
    { title: 'Analyze', detail: 'one deep reviewer per core component' },
    { title: 'Verify', detail: 're-read the code, drop/correct each finding' },
  ],
}

const ROOT = 'D:/Repositories/_local_projects/darkmem'

const CONTEXT = `darkmem is a centralized memory system for AI agents (FastAPI + Postgres/pgvector backend). You are reviewing the CURRENT code on branch fix/eval-p0-2026-06-02, which has already been hardened by a prior review — so verify every claim against what the code ACTUALLY does now; do not assume historical bugs still exist. Read ${ROOT}/CLAUDE.md FIRST for the behavioral contract (treat documented invariants as intended).`

const RUBRIC = `Review along THREE axes and tag every finding with exactly one:
- accuracy: correctness of RESULTS — extraction/dedup/canonicalization quality, supersession correctness, retrieval relevance & ranking, call/heritage/import resolution correctness, off-by-one, boundary conditions, id/type normalization, ranking-signal soundness (RRF, confidence, similarity thresholds).
- reliability: crashes, unhandled errors, races/locks, partial-failure handling, idempotency, data loss/corruption, transaction boundaries, silent drops, resource leaks, non-determinism.
- efficiency: ALGORITHMIC COMPLEXITY (O(n^2)/quadratic loops, full table scans), DB round-trips & N+1 patterns, ANN/GIN index usage vs sequential scans, redundant recomputation/re-parsing, serial work that could be bounded-concurrent, unbounded memory, wasteful payloads. Efficiency was under-covered by the prior review — hunt it hard, with concrete complexity/round-trip analysis.
Ground EVERY finding in file:line you actually opened. Give a concrete scenario (data shape / scale at which it bites). Prefer depth over breadth.`

const FORMAT = `Return GitHub-flavored markdown ONLY. Structure:

## <component name>
**Assessment:** 3-5 sentences — what it does, what is solid, and where the main accuracy/reliability/efficiency risk concentrates.

### Findings
4-9 findings, each:

#### F<n>. <short imperative title>  [axis: accuracy|reliability|efficiency] [severity: blocker|high|medium|low] [effort: small|medium|large]
- **Current:** precisely what the code does today (grounded).
- **Problem:** the concrete failure/degradation, and for efficiency the complexity / round-trip count and the scale at which it bites.
- **Improvement:** concrete change.
- **Reason:** why it's correct and better.
- **Evidence:** file:line.

No trivial nits. If a component is genuinely solid on an axis, say so and report fewer findings.`

const COMPONENTS = [
  {
    key: 'mem-ingestion',
    title: 'Memory ingestion pipeline (phases, concurrency, batching)',
    brief: 'The 5-phase ProcessingPipeline.process_batch: content embed -> extract/classify -> entity embed w/ cache -> dedup ANN -> per-memory write+supersession+crossrefs. Focus efficiency: per-phase DB round-trips, the per-batch classifier-resolution query, entity-embedding cache hit/miss path, dedup fan-out, crossref computation per memory, and whether work is bounded-concurrent vs serial. Plus reliability of phase checkpoints/partial failure and accuracy of status derivation.',
    files: 'backend/app/services/pipeline.py, backend/app/services/pipeline_aggregator.py, backend/app/services/feature_flags.py, backend/app/services/pipeline_failures.py',
  },
  {
    key: 'mem-extraction',
    title: 'LLM extraction, prompts, rescue layers, dedup',
    brief: 'Entity/relationship extraction from content. Focus accuracy: rescue layers (known-entity rescue, generic REPLACES rescue), relation direction validation, dedup-by-target-predicate, negation, the brace-balanced JSON salvage, seed reproducibility. Efficiency: regex/scan complexity over content, repeated passes, any O(n^2) entity/relation matching.',
    files: 'backend/app/services/extraction.py, backend/app/services/prompt.py, backend/app/services/relations.py',
  },
  {
    key: 'mem-graph-supersession',
    title: 'Entity/relation graph, ANN dedup, supersession',
    brief: 'Entity persistence ((name,type) uniqueness, memory_ids[] append, property merge, ANN dedup find_similar_entity@0.85, canonical_map), technologies denorm, delete_by_memory_id idempotency + the relation-preservation guard, supersession (6 gates, clause-scoped speculative). Focus accuracy of dedup/canonicalization/supersession + efficiency of the graph queries (per-name ANN probe fan-out, delete_by_memory_id full-table deletes, neighbor/full-graph queries, missing indexes).',
    files: 'backend/app/services/entity_registry.py, backend/app/services/entity_detector.py, backend/app/services/knowledge_graph.py, backend/app/services/graph.py, backend/app/repositories/graph.py, backend/app/services/supersession.py, backend/app/taxonomy.py',
  },
  {
    key: 'mem-retrieval',
    title: 'Retrieval: hybrid search, RRF, reranker, confidence',
    brief: 'HybridSearchService: semantic (1-cosine ANN) + keyword (ts_rank/plainto_tsquery) fused via RRF k=60 weighted by semantic_weight; reranker (LLM per-doc); confidence weighting; over-fetch + in-memory filter in MemoryService. Focus accuracy: RRF correctness, plainto_tsquery recall, the over-fetch+filter+slice math, id str/UUID normalization, reranker scoring. Efficiency: fetch_n sizing, reranker 1-LLM-call-per-doc latency, get_many ordering, the in-memory filter vs server-side filter, ANN index usage on the partition queries.',
    files: 'backend/app/services/hybrid_search.py, backend/app/services/reranker.py, backend/app/services/confidence.py, backend/app/services/memory.py, backend/app/repositories/relational.py',
  },
  {
    key: 'mem-embedders-vector',
    title: 'Embedders, fingerprint partitioning, vector ops',
    brief: 'Per-fingerprint child tables, embedder registry, reembed backfill, vector repo (search, find_similar, find_similar_memories crossrefs, clustering DBSCAN/Louvain, code-chunk ops). Focus efficiency HARD: does find_similar_memories use the ANN index or a full self-join scan per ingest? clustering LIMIT/sample sizes and O(n^2) edge building; reembed batch sizing & round-trips; embed dimension guard; the slug-collision scan. Plus accuracy of similarity thresholds and reliability of partition existence guards.',
    files: 'backend/app/services/embedder_registry.py, backend/app/services/reembed.py, backend/app/repositories/vector.py, backend/app/services/llm.py',
  },
  {
    key: 'code-parsing',
    title: 'Code parsing, symbol table, type env',
    brief: 'Tree-sitter parsing (grammar caching, fallback), symbol-table construction & lookup (by file/name/owner), type environment build + propagate_types, dialect. Focus accuracy: symbol resolution, constructor/self typing, cyclic-import type propagation determinism. Efficiency: parse concurrency/batching, symbol-table lookup complexity, type-env build cost per file, re-parsing in later phases.',
    files: 'backend/app/services/code_parser.py, backend/app/services/symbol_table.py, backend/app/services/type_env.py, backend/app/services/dialect.py',
  },
  {
    key: 'code-imports',
    title: 'Import resolution, named bindings, suffix index',
    brief: 'Per-language import resolvers, named/wildcard binding propagation, SuffixIndex. Focus accuracy: resolver correctness per language, suffix-index basename collisions falling to slow fallback, binding-chain resolution. Efficiency: SuffixIndex build/lookup complexity, the resolve_import fallback cost, binding propagation passes, any O(files^2) or repeated work.',
    files: 'backend/app/services/import_resolvers/, backend/app/services/named_bindings/, backend/app/services/suffix_index.py, backend/app/services/call_resolver.py',
  },
  {
    key: 'code-call-heritage',
    title: 'Call resolution & heritage/MRO',
    brief: 'CallResolver (confidence-tiered resolution: same-file -> import -> global) and HeritageResolver (per-language MRO, method_inherited, find_inherited_method). Focus accuracy: resolution tiers, the inherited-method call edge gap, override/implements keying, symbol-key collisions. Efficiency: per-call resolution cost, lookups per call site, MRO computation complexity, any quadratic scans over symbols/edges.',
    files: 'backend/app/services/call_resolver.py, backend/app/services/heritage_resolver.py, backend/app/services/symbol_table.py',
  },
  {
    key: 'code-pipeline',
    title: 'Code pipeline phases, communities, processes, wiki',
    brief: 'The 14-phase repo indexing: discovery/diff, parse, structure, import resolution, bindings, call tracing, heritage, phase-08 cross-file binding (skip heuristic), communities (Leiden/Louvain), process traces, validation, embeddings, enrich, wiki. Focus efficiency HARD: phase-08 skip-heuristic denominator, the incremental dependent-retrace cost, full symbol-table reload per phase, re-parsing across phases, community/process complexity, embedding batching. Reliability: incremental staleness, phase partial-failure, _delete_file_data. Accuracy: process-trace seeding, route/tool node cleanup.',
    files: 'backend/app/services/code_pipeline.py, backend/app/services/community_detector.py, backend/app/services/process_tracer.py, backend/app/services/wiki_generator.py',
  },
  {
    key: 'code-query',
    title: 'Code query, blast radius, code search',
    brief: 'code_query (search_code RRF over semantic+ilike, blast-radius recursive CTE, dependency walks) and the MCP code tools (code_context, code_blast_radius, code_rename, code_processes). Focus accuracy: the unordered ilike pass fused as RRF, blast-radius CTE keyspace/collisions, label-vs-id matching. Efficiency: recursive CTE cost & depth caps, repeated queries per tool call (code_context fires many separate queries), missing indexes on code_edges, N+1 over symbols.',
    files: 'backend/app/services/code_query.py, backend/app/api/mcp/server.py, backend/app/repositories/vector.py',
  },
]

phase('Analyze')
log(`Reviewing ${COMPONENTS.length} core components along accuracy/reliability/efficiency`)

const reports = await pipeline(
  COMPONENTS,
  (c) => agent(
    `You are a principal engineer doing a deep accuracy / reliability / EFFICIENCY review of ONE core component.

${CONTEXT}

COMPONENT: ${c.title}
FOCUS: ${c.brief}
KEY FILES (open these; glob directories): ${c.files}

${RUBRIC}

${FORMAT}

Read the files deeply and follow the real control/data flow (including the SQL) before writing. Your markdown is the deliverable.`,
    { label: `analyze:${c.key}`, phase: 'Analyze' }
  ),
  (md, c) => {
    if (!md || typeof md !== 'string' || md.length < 40) return md
    return agent(
      `You are an adversarial verifier for the "${c.title}" component of darkmem (branch fix/eval-p0-2026-06-02). RE-READ THE ACTUAL CODE and judge each finding skeptically. Keep a finding only if the code truly behaves as claimed AND the problem is real AND the fix isn't already implemented. For EFFICIENCY findings, verify the complexity/round-trip claim against the actual code path and SQL (does the query use the ANN/GIN index? is the loop really quadratic? is the round-trip really per-row?). DROP misreads and already-fixed items (say which). CORRECT severities to true impact x likelihood/scale.

KEY FILES: ${c.files}
${CONTEXT}

Return the FINAL cleaned markdown in the SAME format (## component / **Assessment:** / ### Findings / #### F<n> ...). Append to each surviving finding a line "- **Verified:** confirmed|adjusted (one phrase on what re-reading showed)". Output markdown only.

REVIEWER'S DRAFT:
${md}`,
      { label: `verify:${c.key}`, phase: 'Verify' }
    )
  }
)

const out = COMPONENTS.map((c, i) => ({ key: c.key, title: c.title, report: reports[i] || '(no report)' }))
return { reports: out, count: out.filter((r) => typeof r.report === 'string' && r.report.length > 80).length }

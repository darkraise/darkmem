export const meta = {
  name: 'darkmem-eval-prose',
  description: 'Prose-based design+correctness review of darkmem subsystems not yet covered by hand; analyze then adversarially verify; return one clean markdown report per subsystem',
  phases: [
    { title: 'Analyze', detail: 'one reviewer per subsystem, returns markdown findings' },
    { title: 'Verify', detail: 're-read code, drop/correct each finding' },
  ],
}

const ROOT = 'D:/Repositories/_local_projects/darkmem'

const INVARIANTS = `Read ${ROOT}/CLAUDE.md FIRST — it is the behavioral contract. Treat documented invariants (lowercase entity names, no cross-fingerprint joins, closed taxonomy, status lifecycle, REPLACES family, technologies denorm, etc.) as INTENDED. You may critique whether a contract is itself well-designed, but do not flag deliberate contract behavior as a bug. Distinguish "code violates the contract" from "the design could be better".`

const RUBRIC = `Evaluate five dimensions: algorithm choice, logic correctness, data/control flow, system design, feature design. Tag every finding with exactly one axis — reliability (crashes, races, partial-failure, idempotency, data loss, leaks, error handling), accuracy (correctness of results: extraction/dedup/ranking/metrics, off-by-one, boundary, id/type normalization), usability (API/UX ergonomics, error surfacing, defaults, discoverability, empty/loading/error states, a11y), or design (structural concerns affecting maintainability/future correctness). Ground EVERY finding in file:line you actually opened. Prefer concrete failure scenarios over vague "could be better". Severity = user-facing impact x likelihood, not fix difficulty.`

const FORMAT = `Return GitHub-flavored markdown ONLY (no preamble, no JSON). Structure:

## <subsystem name>
**Assessment:** 3-5 sentences — what it does, what is well-designed, where the main reliability/accuracy/usability risk concentrates.

### Findings
Then 4-8 findings, each as:

#### F<n>. <short imperative title>  [axis: reliability|accuracy|usability|design] [severity: blocker|high|medium|low] [effort: small|medium|large]
- **Current:** what the code does today (grounded).
- **Problem:** concrete failure/degradation scenario and why it hurts.
- **Improvement:** concrete actionable change.
- **Reason:** why the change is correct and better.
- **Evidence:** file:line references.

Depth over breadth. No trivial style nits. If the subsystem is genuinely solid, say so and report fewer findings.`

const SUBSYSTEMS = [
  {
    key: 'classification-enrichment',
    title: 'Classification / enrichment (LLM + in-process ML)',
    brief: 'Classification populates the llm_* columns and is gated by llm_enrichment_enabled. Per-batch the pipeline swaps in MLClassificationService when the classification purpose has ml_profile_ref set, else the LLM classifier. Evaluate the shared classify(content, areas, prompt, mode)->{hall,summary,emotions,flags} surface, classification_areas selection, the regex memory_classifier, the enrichment_worker background job, ml_runtime model loading/TTL/eviction, and flag-gating correctness.',
    files: 'backend/app/services/classification_llm.py, backend/app/services/classification_ml.py, backend/app/services/classification_areas.py, backend/app/services/memory_classifier.py, backend/app/services/enrichment_worker.py, backend/app/services/ml_runtime.py, backend/app/services/ml_seed.py',
  },
  {
    key: 'embedders-partitioning',
    title: 'Embedders, fingerprint partitioning, reembed',
    brief: 'Per-fingerprint child tables. Evaluate embedder_registry.register idempotency + CREATE-TABLE ordering, child_table() indirection, parse_fingerprint/slug collisions, the reembed/migration path (rotation, backfill, dimension mismatch, progress/resumability), and how a fingerprint rotation interacts with existing embeddings and search.',
    files: 'backend/app/services/embedder_registry.py, backend/app/services/reembed.py, backend/app/api/routes/reembed.py, backend/app/models/embedding.py',
  },
  {
    key: 'code-parsing-symbols',
    title: 'Code parsing, symbol table, imports, bindings',
    brief: 'Tree-sitter parsing across languages, symbol-table construction, type env, dialect handling, suffix index, per-language import resolvers and named bindings, wildcard synthesis. Evaluate parsing robustness (grammar quirks, failed-grammar caching), symbol-resolution accuracy, import-resolution correctness, and language-specific edge cases.',
    files: 'backend/app/services/code_parser.py, backend/app/services/symbol_table.py, backend/app/services/type_env.py, backend/app/services/dialect.py, backend/app/services/suffix_index.py, backend/app/services/import_resolvers/, backend/app/services/named_bindings/',
  },
  {
    key: 'code-pipeline-resolution',
    title: 'Code pipeline, call/heritage resolution, wiki, communities',
    brief: 'Repo indexing: parse -> symbols -> call graph -> heritage -> communities -> wiki. Evaluate call_resolver and heritage_resolver accuracy (false/missed edges), community_detector algorithm choice, code_query correctness, process_tracer, wiki_generator design, and the reindex toggles (full/enrich_symbols/generate_wiki) flow + incremental vs full reindex.',
    files: 'backend/app/services/code_pipeline.py, backend/app/services/call_resolver.py, backend/app/services/heritage_resolver.py, backend/app/services/code_query.py, backend/app/services/community_detector.py, backend/app/services/process_tracer.py, backend/app/services/wiki_generator.py, backend/app/api/routes/code.py',
  },
  {
    key: 'llm-orchestration',
    title: 'LLM orchestration, providers/profiles/purposes, config',
    brief: 'Six LLM purposes; LLMPurposeConfig may inline or reference provider_ref/profile_ref/ml_profile_ref. Evaluate api_kind dispatch (openai compat, ollama native think:false, anthropic x-api-key, deepseek/gemini reasoning-disable injection, zai), reasoning-control correctness, seed forwarding, embed_batch_chunked, timeout/retry/error behavior at the HTTP boundary, supports_embedding gating, and config route validation/resolution (get_llm_config overlay).',
    files: 'backend/app/services/llm.py, backend/app/services/llm_seed.py, backend/app/services/config.py, backend/app/api/routes/config.py, backend/app/models/llm_config.py',
  },
  {
    key: 'jobs-scheduling',
    title: 'Jobs registry, scheduling, repo sync, convo mining',
    brief: 'JobRegistry cron dispatch (5/6-field seconds-first), per-job asyncio.Lock shared by loop+manual trigger, min_interval_seconds floor, job:<key> config rows, no-immediate-fire-on-cron-only-edit. Evaluate cron correctness, lock/race safety, malformed-config guards, repo_manager sync (wakeup event, git safe.directory, fetch errors), convo_miner, task_registry, and the jobs route.',
    files: 'backend/app/services/job_registry.py, backend/app/services/job_runners.py, backend/app/services/repo_manager.py, backend/app/services/convo_miner.py, backend/app/services/task_registry.py, backend/app/api/routes/jobs.py',
  },
  {
    key: 'auth-setup',
    title: 'Auth, setup wizard, API keys, audit',
    brief: 'JWT/typed tokens, refresh, password change/revocation, login audit, token blocklist, setup-secret enforcement (prod validator), the multi-step setup wizard + finalize seeding, API-key model. Evaluate token lifecycle correctness, revocation completeness (blocklist coverage, refresh rotation), setup-secret gating + one-shot inertness, audit coverage, CORS, and setup-flow usability/safety.',
    files: 'backend/app/api/auth.py, backend/app/api/deps.py, backend/app/api/routes/auth.py, backend/app/api/routes/setup.py, backend/app/models/api_key.py, backend/app/models/audit.py, backend/app/models/token_blocklist.py',
  },
  {
    key: 'observability',
    title: 'Analytics, system metrics, websocket, pipeline-failures API',
    brief: 'Analytics aggregations, system_metrics, websocket broadcast (pipeline.completed/partial/failed, reconnect, missed events, backpressure, auth on the ws), and the pipeline-failures record/resolve/retry-all API + derive_memory_failed_step. Evaluate metric correctness, websocket reliability, failure-tracking accuracy, and the retry-all flow.',
    files: 'backend/app/services/analytics.py, backend/app/services/system_metrics.py, backend/app/api/websocket.py, backend/app/api/routes/analytics.py, backend/app/services/pipeline_failures.py, backend/app/api/routes/pipeline_failures.py, backend/app/schemas/events.py',
  },
  {
    key: 'fe-core',
    title: 'Frontend core feature UX (memories, graph, chat, code)',
    brief: 'React + TanStack Router/Query. Evaluate usability, data-fetching/caching correctness (query keys, invalidation, optimistic updates, refetch), error/empty/loading states, accessibility, and large-list/graph rendering performance for: memories view, knowledge + code graph renderers, chat, code-wiki/code-graph, unified-graph.',
    files: 'frontend/src/routes/_authenticated/memories.tsx, frontend/src/routes/_authenticated/graph.tsx, frontend/src/routes/_authenticated/code-graph.tsx, frontend/src/routes/_authenticated/code-wiki.tsx, frontend/src/routes/_authenticated/unified-graph.tsx, frontend/src/routes/_authenticated/chat.tsx, frontend/src/features/graph/, frontend/src/features/chat/, frontend/src/features/memories/, frontend/src/features/code/, frontend/src/hooks/api/',
  },
  {
    key: 'fe-config',
    title: 'Frontend config/admin UX (LLM, settings, jobs, repos, reindex, setup, auth, pipeline)',
    brief: 'Evaluate usability, form validation, error surfacing, and data-flow correctness for admin surfaces: LLM profiles/providers/purposes/ML panels, settings (feature flags), jobs page + per-job config dialog, repos + reindex toggles, setup wizard steps, login, pipeline visualization, and the overview dashboard.',
    files: 'frontend/src/routes/_authenticated/llm.tsx, frontend/src/routes/_authenticated/settings.tsx, frontend/src/routes/_authenticated/jobs.tsx, frontend/src/routes/_authenticated/repos.tsx, frontend/src/routes/_authenticated/reindex.tsx, frontend/src/routes/_authenticated/index.tsx, frontend/src/routes/_authenticated/pipeline.tsx, frontend/src/features/pipeline/, frontend/src/features/settings/, frontend/src/features/jobs/, frontend/src/features/repos/, frontend/src/features/setup/, frontend/src/features/auth/, frontend/src/features/llm/',
  },
]

phase('Analyze')
log(`Prose review of ${SUBSYSTEMS.length} subsystems: analyze -> adversarial verify`)

const reports = await pipeline(
  SUBSYSTEMS,
  (s) => agent(
    `You are a principal engineer doing a rigorous design + correctness review of ONE subsystem of "darkmem", a centralized memory system for AI agents (FastAPI + Postgres/pgvector backend, React/TanStack frontend).

SUBSYSTEM: ${s.title}
FOCUS: ${s.brief}
KEY FILES (open these; glob directories with the file-search tools): ${s.files}

${INVARIANTS}

${RUBRIC}

${FORMAT}

Read the files deeply and follow the real control flow before writing anything. Your markdown is the deliverable.`,
    { label: `analyze:${s.key}`, phase: 'Analyze' }
  ),
  (analysisMd, s) => {
    if (!analysisMd || typeof analysisMd !== 'string' || analysisMd.length < 40) return analysisMd
    return agent(
      `You are an adversarial verifier for the "${s.title}" subsystem of darkmem. A reviewer produced the markdown findings below. RE-READ THE ACTUAL CODE and judge each finding skeptically.

KEY FILES: ${s.files}
${INVARIANTS}

For each finding: open the cited file:line and surrounding code. Keep it only if the code truly behaves as claimed AND the problem is real AND the improvement is not already implemented. DROP findings that misread the code or whose fix already exists (say which). CORRECT severities to true impact x likelihood. You may ADD at most 2 high-confidence findings the reviewer missed if you verified them in the code.

Return the FINAL cleaned markdown report in the SAME format the reviewer used (## subsystem / **Assessment:** / ### Findings / #### F<n> ...). Append to each finding a line "- **Verified:** confirmed|adjusted (one phrase on what re-reading showed)". Output markdown only.

REVIEWER'S DRAFT:
${analysisMd}`,
      { label: `verify:${s.key}`, phase: 'Verify' }
    )
  }
)

const out = SUBSYSTEMS.map((s, i) => ({ key: s.key, title: s.title, report: reports[i] || '(no report produced)' }))
return { reports: out, count: out.filter((r) => typeof r.report === 'string' && r.report.length > 80).length }

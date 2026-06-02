export const meta = {
  name: 'darkmem-comprehensive-eval',
  description: 'Evaluate algorithm/logic/flow/design of every darkmem subsystem; verify each finding; synthesize a prioritized reliability/accuracy/usability report',
  phases: [
    { title: 'Analyze', detail: 'one deep design+correctness reviewer per subsystem' },
    { title: 'Verify', detail: 'adversarially re-check each finding against the code' },
    { title: 'Synthesize', detail: 'dedup cross-cutting themes, prioritize' },
  ],
}

const ROOT = 'D:/Repositories/_local_projects/darkmem'

const FINDINGS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['subsystem', 'assessment', 'findings'],
  properties: {
    subsystem: { type: 'string' },
    assessment: { type: 'string', description: '3-5 sentences: what this subsystem does, what is well-designed, and where the main reliability/accuracy/usability risks concentrate.' },
    findings: {
      type: 'array',
      description: 'The 4-9 most impactful issues. Depth over breadth. No trivial style nits.',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['title', 'axis', 'severity', 'current_behavior', 'problem', 'improvement', 'reason', 'effort', 'evidence'],
        properties: {
          title: { type: 'string', description: 'short imperative title' },
          axis: { type: 'string', enum: ['reliability', 'accuracy', 'usability', 'design'] },
          severity: { type: 'string', enum: ['blocker', 'high', 'medium', 'low'] },
          current_behavior: { type: 'string', description: 'precisely what the code does today, grounded in what you read' },
          problem: { type: 'string', description: 'why it hurts reliability/accuracy/usability; concrete failure or degradation scenario' },
          improvement: { type: 'string', description: 'concrete, actionable change' },
          reason: { type: 'string', description: 'why the improvement is correct and better' },
          effort: { type: 'string', enum: ['small', 'medium', 'large'] },
          evidence: { type: 'string', description: 'file:line references that ground current_behavior' },
        },
      },
    },
  },
}

const VERIFY_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['verified'],
  properties: {
    verified: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['title', 'verdict', 'severity', 'note'],
        properties: {
          title: { type: 'string', description: 'must match the finding title being judged' },
          verdict: { type: 'string', enum: ['confirmed', 'partially', 'refuted', 'redundant'] },
          severity: { type: 'string', enum: ['blocker', 'high', 'medium', 'low'], description: 'your corrected severity' },
          note: { type: 'string', description: 'what re-reading the code showed; for refuted/redundant explain exactly why (e.g. behavior already exists at file:line, or the claim misreads the code)' },
          refined_improvement: { type: 'string', description: 'optional: a better or corrected improvement' },
        },
      },
    },
  },
}

const INVARIANTS = `Read ${ROOT}/CLAUDE.md FIRST. It is the behavioral contract. Treat documented invariants (lowercase entity names, no cross-fingerprint joins, REPLACES family, technologies denorm, closed taxonomy, status lifecycle, etc.) as INTENDED. You may still critique whether a contract is itself well-designed, but do not flag deliberate contract behavior as a bug. Distinguish "code violates the contract" from "the contract/design could be better".`

const RUBRIC = `Evaluate FIVE dimensions: algorithm choice, logic correctness, data/control flow, system design, feature design. Map every finding to ONE axis:
- reliability: crashes, unhandled errors, races/locks, partial-failure handling, idempotency, data loss/corruption, resource leaks, retry/backoff, transaction boundaries, silent drops.
- accuracy: correctness of RESULTS — extraction quality, dedup/canonicalization, supersession correctness, retrieval relevance/ranking, metric/analytics correctness, type/id normalization, off-by-one, boundary conditions.
- usability: API/UX ergonomics, error surfacing to the user, sensible defaults, discoverability, empty/loading/error states, accessibility, config clarity, footguns.
- design: structural/architectural concerns that don't fit the above but materially affect maintainability or future correctness.
Be grounded: cite file:line. Prefer concrete failure scenarios over vague "could be better". If something is genuinely well-designed, say so in the assessment and don't manufacture findings. Severity reflects user-facing impact x likelihood, not how easy it is to fix.`

const SUBSYSTEMS = [
  {
    key: 'ingestion-pipeline',
    title: 'Memory ingestion pipeline (5-phase batch)',
    brief: 'The core ProcessingPipeline.process_batch: content embed -> extract/classify -> entity embed w/ cache -> dedup ANN -> write+supersession+crossrefs. Evaluate phase checkpoints, concurrency bounds (pipeline_concurrency), fingerprint registration ordering, per-memory savepoint isolation, partial-failure semantics, idempotent re-extraction (delete_by_memory_id), and pipeline_failures/websocket status derivation.',
    files: 'backend/app/services/pipeline.py, backend/app/services/pipeline_aggregator.py, backend/app/services/feature_flags.py, backend/app/services/pipeline_failures.py',
  },
  {
    key: 'extraction-prompts',
    title: 'LLM extraction, prompts, rescue layers',
    brief: 'Entity/relationship extraction from content via LLM. Evaluate JSON parsing robustness, the rescue layers (known-entity rescue, generic REPLACES rescue), relation direction validation, dedup-by-target-predicate tie-breaks, negation handling, seed reproducibility, and prompt design quality/clarity.',
    files: 'backend/app/services/extraction.py, backend/app/services/prompt.py, backend/app/services/relations.py',
  },
  {
    key: 'entity-graph-registry',
    title: 'Entity/relation registry, knowledge graph, taxonomy',
    brief: 'Entity/relation persistence: (name,type) uniqueness, memory_ids[] append-not-duplicate, canonical_map application, ANN dedup (find_similar_entity @0.85), taxonomy normalization (closed types, legacy maps, concept/RELATED_TO fallbacks), technologies denorm recompute, display_name casing. Evaluate correctness of dedup/canonicalization and graph integrity.',
    files: 'backend/app/services/entity_registry.py, backend/app/services/entity_detector.py, backend/app/services/knowledge_graph.py, backend/app/services/graph.py, backend/app/repositories/graph.py, backend/app/taxonomy.py, backend/app/utils/graph_keys.py',
  },
  {
    key: 'supersession',
    title: 'Supersession detection',
    brief: 'detect_supersessions: flips candidates active->superseded on REPLACES. Evaluate the 6 gates (same project, active, technologies overlap, 90d window, strictly-older, speculative markers), REPLACES-family collapse, lowercase alignment with technologies, and the bidirectional-supersession guard. Look for missed/over-eager supersession and ordering hazards.',
    files: 'backend/app/services/supersession.py',
  },
  {
    key: 'embedders-partitioning',
    title: 'Embedders, fingerprint partitioning, reembed',
    brief: 'Per-fingerprint child tables (memory/entity/code/entity-cache embeddings). Evaluate embedder_registry.register idempotency + CREATE-table ordering, _register_fingerprint-before-insert discipline, child_table indirection, no-cross-fingerprint-join enforcement, and the reembed/migration path (rotation mid-batch, backfill, dimension mismatch).',
    files: 'backend/app/services/embedder_registry.py, backend/app/services/reembed.py, backend/app/repositories/vector.py, backend/app/models/embedding.py, backend/app/api/routes/reembed.py',
  },
  {
    key: 'retrieval-hybrid',
    title: 'Retrieval: hybrid search, reranker, confidence',
    brief: 'HybridSearchService: semantic (1 - cosine) + keyword (ts_rank/plainto_tsquery) fused via RRF k=60 weighted by semantic_weight; confidence_rank_gamma weighting; reranker integration; code search semantic-only. Evaluate fusion correctness, memory_id str/UUID normalization at boundaries, ranking quality, threshold/weight defaults, and reranker flow.',
    files: 'backend/app/services/hybrid_search.py, backend/app/services/reranker.py, backend/app/services/confidence.py, backend/app/services/memory.py, backend/app/api/routes/memories.py',
  },
  {
    key: 'classification-enrichment',
    title: 'Classification / enrichment (LLM + in-process ML)',
    brief: 'Classification populates llm_* columns (flag-gated by llm_enrichment_enabled). Per-batch classifier swap: MLClassificationService when ml_profile_ref set, else LLM. Evaluate the shared classify() surface, classification_areas logic, enrichment_worker queue/job, ml_runtime dispatch, hallucination/summary/emotions/flags handling, and flag gating correctness.',
    files: 'backend/app/services/classification_llm.py, backend/app/services/classification_ml.py, backend/app/services/classification_areas.py, backend/app/services/memory_classifier.py, backend/app/services/enrichment_worker.py, backend/app/services/ml_runtime.py',
  },
  {
    key: 'code-parsing-symbols',
    title: 'Code parsing, symbol table, imports, bindings',
    brief: 'Tree-sitter parsing across languages, symbol table construction, type env, dialect handling, suffix index, per-language import resolvers and named bindings, wildcard synthesis. Evaluate parsing robustness (grammar quirks, failed-grammar caching), symbol resolution accuracy, import resolution correctness, and language-specific edge cases.',
    files: 'backend/app/services/code_parser.py, backend/app/services/symbol_table.py, backend/app/services/type_env.py, backend/app/services/dialect.py, backend/app/services/suffix_index.py, backend/app/services/import_resolvers/, backend/app/services/named_bindings/',
  },
  {
    key: 'code-pipeline-resolution',
    title: 'Code pipeline, call/heritage resolution, wiki, communities',
    brief: 'Repo indexing pipeline: parse -> symbols -> call graph -> heritage (inheritance) -> communities -> wiki. Evaluate call_resolver and heritage_resolver accuracy (false edges, missed edges), community_detector algorithm, code_query correctness, wiki_generator design, and the overall indexing flow + reindex toggles (full/enrich_symbols/generate_wiki).',
    files: 'backend/app/services/code_pipeline.py, backend/app/services/call_resolver.py, backend/app/services/heritage_resolver.py, backend/app/services/code_query.py, backend/app/services/community_detector.py, backend/app/services/wiki_generator.py, backend/app/api/routes/code.py',
  },
  {
    key: 'llm-orchestration',
    title: 'LLM orchestration, providers/profiles/purposes, config',
    brief: 'Six LLM purposes; LLMPurposeConfig may inline or reference provider_ref/profile_ref/ml_profile_ref. api_kind dispatch (openai compat, ollama native think:false, anthropic/deepseek/google/zai quirks), reasoning-control injection, seed forwarding, supports_embedding gating. Evaluate vendor-quirk handling, error/timeout/retry behavior, config validation, and seed/finalize seeding flow.',
    files: 'backend/app/services/llm.py, backend/app/services/llm_seed.py, backend/app/services/config.py, backend/app/api/routes/config.py, backend/app/models/llm_config.py',
  },
  {
    key: 'jobs-scheduling',
    title: 'Jobs registry, scheduling, repo sync, convo mining',
    brief: 'JobRegistry: cron dispatch (5/6-field seconds-first), per-job asyncio.Lock shared by loop+manual trigger, min_interval_seconds floor, job:<key> config rows. Evaluate cron correctness, lock/race safety, malformed-config guards, no-immediate-fire-on-cron-only-edit, repo_manager sync (wakeup event, safe.directory), convo_miner, and task_registry.',
    files: 'backend/app/services/job_registry.py, backend/app/services/job_runners.py, backend/app/services/repo_manager.py, backend/app/services/convo_miner.py, backend/app/services/task_registry.py, backend/app/api/routes/jobs.py',
  },
  {
    key: 'mcp-server',
    title: 'MCP server (agent-facing API)',
    brief: 'The MCP tool surface agents use to add/search/manage memories. Evaluate tool design (clarity, naming, params), input caps (batch/search), error handling and partial-batch semantics, search behavior, relation endpoint resolution by (name,type), and the local-network-only auth posture. Focus on usability for an AI agent consumer + reliability under malformed input.',
    files: 'backend/app/api/mcp/server.py',
  },
  {
    key: 'auth-setup',
    title: 'Auth, setup wizard, API keys, audit',
    brief: 'JWT/typed tokens, refresh, password change/revocation, login audit, token blocklist, setup secret enforcement (prod validator), multi-step setup wizard + finalize seeding, API key model. Evaluate token lifecycle correctness, revocation completeness, setup-secret gating, audit coverage, and setup-flow usability/safety.',
    files: 'backend/app/api/auth.py, backend/app/api/deps.py, backend/app/api/routes/auth.py, backend/app/api/routes/setup.py, backend/app/models/api_key.py, backend/app/models/audit.py, backend/app/models/token_blocklist.py',
  },
  {
    key: 'observability',
    title: 'Analytics, system metrics, websocket, pipeline-failures API',
    brief: 'Analytics aggregations, system_metrics, process_tracer, websocket broadcast (pipeline.completed/partial/failed), pipeline-failures retry/resolution API. Evaluate metric correctness, websocket reliability (reconnect, missed events, backpressure), failure-tracking accuracy, and the retry-all-failures flow.',
    files: 'backend/app/services/analytics.py, backend/app/services/system_metrics.py, backend/app/services/process_tracer.py, backend/app/api/websocket.py, backend/app/api/routes/analytics.py, backend/app/api/routes/pipeline_failures.py, backend/app/schemas/events.py',
  },
  {
    key: 'fe-core',
    title: 'Frontend core feature UX (memories, graph, chat, code, pipeline)',
    brief: 'React + TanStack Router/Query. Evaluate usability, data-fetching/caching correctness (query keys, invalidation, optimistic updates), error/empty/loading states, accessibility, and large-list/graph rendering performance for: memories view, knowledge + code graph renderers, chat, code-wiki/code-graph, and pipeline visualization.',
    files: 'frontend/src/routes/_authenticated/memories.tsx, frontend/src/routes/_authenticated/graph.tsx, frontend/src/routes/_authenticated/code-graph.tsx, frontend/src/routes/_authenticated/code-wiki.tsx, frontend/src/routes/_authenticated/unified-graph.tsx, frontend/src/routes/_authenticated/chat.tsx, frontend/src/routes/_authenticated/pipeline.tsx, frontend/src/features/graph/, frontend/src/features/chat/, frontend/src/features/memories/, frontend/src/features/code/, frontend/src/features/pipeline/, frontend/src/hooks/api/',
  },
  {
    key: 'fe-config',
    title: 'Frontend config/admin UX (LLM, settings, jobs, repos, reindex, setup, auth, analytics)',
    brief: 'Evaluate usability, form validation, error surfacing, and data-flow correctness for the admin surfaces: LLM profiles/providers/purposes/ML panels, settings (feature flags), jobs page + per-job config dialog, repos + reindex toggles, setup wizard steps, login, and analytics/overview dashboards.',
    files: 'frontend/src/routes/_authenticated/llm.tsx, frontend/src/routes/_authenticated/settings.tsx, frontend/src/routes/_authenticated/jobs.tsx, frontend/src/routes/_authenticated/repos.tsx, frontend/src/routes/_authenticated/reindex.tsx, frontend/src/routes/_authenticated/analytics.tsx, frontend/src/routes/_authenticated/index.tsx, frontend/src/features/pipeline/, frontend/src/features/settings/, frontend/src/features/jobs/, frontend/src/features/repos/, frontend/src/features/setup/, frontend/src/features/auth/, frontend/src/features/llm/',
  },
]

phase('Analyze')
log(`Evaluating ${SUBSYSTEMS.length} subsystems: deep analysis -> adversarial verify -> synthesize`)

const perSubsystem = await pipeline(
  SUBSYSTEMS,
  (s) => agent(
    `You are a principal engineer doing a rigorous design + correctness review of ONE subsystem of "darkmem", a centralized memory system for AI agents (FastAPI + Postgres/pgvector backend, React frontend).

SUBSYSTEM: ${s.title}
WHAT IT IS / WHAT TO FOCUS ON: ${s.brief}
KEY FILES (read these thoroughly; glob directories): ${s.files}

${INVARIANTS}

${RUBRIC}

Read the files deeply — follow the actual control flow, don't skim. Then produce your assessment and the 4-9 highest-impact findings. Ground every finding in file:line. Your output is consumed by another agent and a synthesis step, so be precise and self-contained, not conversational.`,
    { label: `analyze:${s.key}`, phase: 'Analyze', schema: FINDINGS_SCHEMA }
  ),
  (analysis, s) => {
    if (!analysis || !analysis.findings || !analysis.findings.length) return analysis
    return agent(
      `You are an adversarial verifier. Another reviewer produced findings for the "${s.title}" subsystem of darkmem. Your job is to RE-READ THE ACTUAL CODE and judge each finding skeptically. Default to skepticism: a finding survives only if the code truly behaves as claimed AND the problem is real AND the improvement is not already implemented.

KEY FILES: ${s.files}
${INVARIANTS}

For EACH finding below, open the cited file:line (and surrounding code), and decide:
- confirmed: current_behavior is accurate and the problem is real.
- partially: real but overstated/misattributed; correct the severity and note what's actually true.
- refuted: the claim misreads the code or the problem doesn't actually occur. Explain the misread.
- redundant: the proposed improvement already exists in the code (cite where).
Also correct severity to reflect true user-facing impact x likelihood.

FINDINGS (JSON):
${JSON.stringify(analysis.findings.map((f, i) => ({ n: i + 1, title: f.title, axis: f.axis, severity: f.severity, current_behavior: f.current_behavior, problem: f.problem, improvement: f.improvement, evidence: f.evidence })), null, 1)}

Return one verified entry per finding, matching titles exactly.`,
      { label: `verify:${s.key}`, phase: 'Verify', schema: VERIFY_SCHEMA }
    ).then((v) => ({ subsystem: s.title, key: s.key, assessment: analysis.assessment, findings: analysis.findings, verified: (v && v.verified) || [] }))
  }
)

const subsystems = perSubsystem.filter(Boolean).filter((r) => r && r.findings)

// Join verdicts onto findings; keep only survivors (confirmed/partially).
const survivors = []
for (const sub of subsystems) {
  const vmap = new Map((sub.verified || []).map((v) => [v.title, v]))
  for (const f of sub.findings) {
    const v = vmap.get(f.title)
    const verdict = v ? v.verdict : 'unverified'
    if (verdict === 'refuted' || verdict === 'redundant') continue
    survivors.push({
      subsystem: sub.subsystem,
      key: sub.key,
      title: f.title,
      axis: f.axis,
      severity: v && v.severity ? v.severity : f.severity,
      verdict,
      current_behavior: f.current_behavior,
      problem: f.problem,
      improvement: (v && v.refined_improvement) || f.improvement,
      reason: f.reason,
      effort: f.effort,
      evidence: f.evidence,
      verify_note: v ? v.note : 'not verified',
    })
  }
}

log(`${survivors.length} findings survived verification across ${subsystems.length} subsystems`)

phase('Synthesize')
const SYNTH_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['themes', 'top_priorities'],
  properties: {
    themes: {
      type: 'array', description: 'cross-cutting themes that recur across subsystems',
      items: {
        type: 'object', additionalProperties: false,
        required: ['theme', 'why_it_matters', 'subsystems'],
        properties: {
          theme: { type: 'string' },
          why_it_matters: { type: 'string' },
          subsystems: { type: 'array', items: { type: 'string' } },
        },
      },
    },
    top_priorities: {
      type: 'array', description: 'the 12-18 highest-leverage fixes overall, ordered',
      items: {
        type: 'object', additionalProperties: false,
        required: ['title', 'subsystem', 'axis', 'severity', 'effort', 'why_now'],
        properties: {
          title: { type: 'string' },
          subsystem: { type: 'string' },
          axis: { type: 'string' },
          severity: { type: 'string' },
          effort: { type: 'string' },
          why_now: { type: 'string', description: 'one line: impact vs effort justification' },
        },
      },
    },
  },
}

const synthesis = await agent(
  `You are the lead synthesizing a comprehensive evaluation of darkmem. Below are all verified findings (refuted/redundant already removed) across every subsystem. Each is tagged with axis (reliability/accuracy/usability/design), severity, effort, and a verification note.

Produce:
1) cross-cutting themes — patterns that recur across multiple subsystems (e.g. a systemic reliability or accuracy weakness), with which subsystems they touch.
2) top_priorities — the 12-18 highest-leverage items overall, ordered by (impact x likelihood) / effort, biased toward reliability and accuracy of the core memory pipeline and retrieval, then usability. For each give a one-line impact-vs-effort justification.

Be selective and decisive. Do not just re-list everything.

VERIFIED FINDINGS (JSON):
${JSON.stringify(survivors.map((f) => ({ subsystem: f.subsystem, title: f.title, axis: f.axis, severity: f.severity, effort: f.effort, problem: f.problem, improvement: f.improvement })), null, 1)}`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA }
)

return {
  subsystem_assessments: subsystems.map((s) => ({ subsystem: s.subsystem, key: s.key, assessment: s.assessment })),
  survivors,
  synthesis,
  stats: {
    subsystems: subsystems.length,
    total_findings: subsystems.reduce((a, s) => a + s.findings.length, 0),
    survivors: survivors.length,
  },
}

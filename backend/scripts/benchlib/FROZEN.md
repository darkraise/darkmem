# benchlib — frozen decisions

Decisions recorded here are load-bearing for every bench run built on top of
`benchlib`. Changing one is a behavior change to the harness, not a cleanup —
treat an edit here the same way CLAUDE.md's domain-model section is treated.

## Ingestion granularity — memory-per-corpus-entry

**Frozen 2026-07-26.**

One `process_batch` entry per `memories[]` item in a corpus file. `run_ingest`
(`benchlib/ingest.py`) passes the whole `entries` list to a single
`ProcessingPipeline.process_batch(...)` call, so every corpus entry is one
row in `outcomes` and one memory in the batch — never grouped, split, or
re-chunked by the harness itself. `process_batch`'s own internal chunking
(`embedding_batch_size`, `pipeline_concurrency`) is a pipeline concern, not a
harness one; the harness's granularity promise is 1:1 at the corpus-entry
level, independent of how the pipeline internally batches embed/chat calls.

This is what makes a corpus file's entry count and a run's `outcomes` length
provably equal, and what lets `IngestResult.fingerprint` / `live_calls`
describe one coherent unit of work per `run_ingest` call.

## Three-database rule

`darkmem` (real), `darkmem_test` (pytest only, pinned by
`backend/tests/conftest.py`), `darkmem_bench` (benchlib/eval only, pinned by
`benchlib/bench_db.py`). Three databases, three purposes, zero overlap. A
harness or test pointed at the wrong one of these is a defect even if it
passes. `bench_db.reset_bench_db()` does `DROP SCHEMA public CASCADE` +
`alembic upgrade head` against `darkmem_bench` only — never call it against
anything else.

## LLM cache-key rule

`benchlib/caching_llm.CachingLLMOrchestrator` keys every cached call on a
SHA-256 hash (truncated to 16 hex chars) of a JSON-serialized
`[kind, payload]` pair (`_key()` in `caching_llm.py`):

- `embed` / `embed_batch`: `payload` is `[text, <embedding purpose identity>]`
  (one cache entry per unique text per embedder, shared between the two
  entry points).
- `chat_completion`: `payload` is
  `[purpose, <purpose identity>, messages, sorted(kwargs.items())]` —
  `messages` includes the system prompt, so a cached output is valid only
  for the exact prompt it was produced under (doc 17 §7: "a cached output
  is valid only for the prompt it was keyed under"). Changing the
  extraction/classification prompt, the gate state that selects it
  (`classification_mode`, `ml_profile_ref` — see `ingest.GateConfig`), or
  any call kwarg (e.g. `seed`) invalidates the cache for that call
  automatically, by construction, with no separate invalidation step.

**Purpose identity — the full invalidation contract.** The key folds in the
resolved `LLMPurposeConfig` for the purpose being called
(`_KEYED_CONFIG_FIELDS` in `caching_llm.py`): **`model`, `base_url`,
`api_kind`, `dimensions`, `reasoning`, `params`**. Changing any of them is
a cache miss. This is what makes benchlib safe for its actual purpose —
comparing model configurations. Without it, swapping the seeded extraction
model and re-running replays the *previous* model's answers at
`live_calls == 0`, so the gate exits 0 and the ledger records metrics for a
model that never ran.

`api_key` is deliberately **excluded**: rotating a credential does not change
an answer, and a secret has no business being hashed into a cache key. Adding
a field to `_KEYED_CONFIG_FIELDS` invalidates every cache entry on every
machine — that is correct when the field genuinely changes model output, and
wrong otherwise.

Cache entries are one JSON file per key under the orchestrator's `cache_dir`,
written once and read on every subsequent call with the same key. Nothing in
`benchlib` commits a populated cache directory to git — `run_smoke.py`'s
cache lives at `backend/scripts/benchlib/smoke/cache/`, gitignored, so every
environment (a fresh CI checkout, a fresh dev machine) pays the first pass's
genuine model cost once and then reuses it locally, the same way
`extraction_bench/.cache/` already works.

## A corpus declares its own expected work

**Frozen 2026-07-26.**

A corpus file may carry an `expected` object next to `memories`, holding the
counts ingesting it should produce: `{"memories": N, "entities": N,
"relations": N}`. `smoke/corpus.json` declares `3 / 6 / 3`.
`benchlib.corpus.load_expectations()` reads and validates it (unknown keys and
non-negative-integer violations are load errors); a corpus that declares
nothing returns `None`, which is the normal case for gold files.

`run_smoke.find_work_shortfalls()` holds every pass to that floor. The counts
live in the corpus because the corpus is the thing that declares what
ingesting it produces — do not move them into `run_smoke.py`. It is a floor
(`actual >= expected`), not an equality: a richer extraction is not a
regression, a thinner one is.

Without this floor the gate only catches work that *errors*. A cached chat
entry replaced by *valid* JSON with empty `entities`/`relationships`, a
silently regressed `clean_extraction`, or a model swap replaying another
model's answers all produce all-ok outcomes, zero live calls, and exit 0.

`run_smoke.main()` also refuses a corpus that yields zero entries, before it
resets the bench DB. Zero entries satisfies every count trivially, so the
gate would certify nothing and exit green.

## Gate pinning rewrites the whole feature-flags row

**Frozen 2026-07-26.**

`ingest.pin_gate_config()` writes `FEATURE_FLAGS_DEFAULTS` plus `GateConfig`'s
overrides — it does **not** merge over whatever the row already holds. A bench
run therefore measures under a fully determined flag state, not a partly
inherited one.

This matters for flags `GateConfig` does not model. `process_batch` reads
`classification_areas` (`pipeline.py:605`) to build the classification
prompt's allowed-type list, so a leftover `classification_areas` from a prior
experiment would change every `llm_classified_type` the run measures while the
recorded `gate_config` stayed byte-identical to a clean run's. The
concurrency and batch-size flags are pinned for the same reason. Adding a
knob a bench run must vary means adding it to `GateConfig`, not leaving it
ambient.

## A corpus `created_at` is honoured, never discarded

**Frozen 2026-07-26.**

`MemoryCreate` carries no `created_at`, so the row is server-stamped `now()`.
`ingest._create_memory_rows()` overwrites that stamp with the corpus value
before the commit — that is, before `process_batch` runs — and raises a
`ValueError` naming the entry index for a value it cannot parse. Nothing the
corpus declares is silently dropped.

`detect_supersessions` orders candidates by `created_at` (`pipeline.py:463-470`
— the 90-day window rule and the older-than rule). Discarding the declared
value would give every same-batch row one identical timestamp, quietly
reducing a corpus written to exercise the date rules to a test of the id
tie-break instead.

## `refine_entity_type` is not mirrored in the loader

**Frozen 2026-07-26.**

`refine_entity_type` (`app/taxonomy.py:145-151`) runs after
`normalize_entity_type` on the ingest path (`app/services/extraction_clean.py:346`)
and rewrites **`project` → `tool` for any entity whose name ends in `-ui`,
`-kit`, `-sdk`, `.js`, or `-js`**. So `{"name": "darkraise-ui", "type":
"project"}` is stored as `tool`, not `project`.

`benchlib.corpus` deliberately does **not** mirror this. It validates raw
membership in the closed tables and nothing else, so that gold entry loads
clean while the pipeline can never produce the type it declares.

This asymmetry is left open on purpose: whether gold should be authored
pre- or post-refinement is a scorer-design decision, and the scorer is what
must settle it. **A type-sensitive entity scorer has to decide which side to
normalise on** — apply `refine_entity_type` to gold before comparing, or
compare against the pre-refinement type — and say so explicitly. Until then,
a `project`-typed gold entity with one of those name suffixes will read as an
extractor miss it structurally cannot avoid. (Latent today: every
`project`-typed entity in both gold files is named "darkmem".)

## Bench-DB LLM seeding (`run_smoke.py`)

`reset_bench_db()` drops the whole `public` schema, which destroys every
`llm_*` config row along with everything else. `run_smoke.py` therefore
seeds three `llm_purpose_configs` rows itself, after every reset and before
building the orchestrator's config, via
`run_smoke.seed_llm_purpose_configs()`. These are the actual seeded values
(GLOBAL.md, verified reachable by the controller on 2026-07-26):

| purpose | api_kind | base_url | model | dimensions | api_key |
|---|---|---|---|---|---|
| `embedding` | `ollama` | `http://192.168.0.196:11434` | `qwen3-embedding:0.6b` | 1024 | none — Ollama is unauthenticated on this network |
| `extraction` | `deepseek` | `https://api.deepseek.com/v1` | `deepseek-v4-flash` | — | `DEEPSEEK_API_KEY` env var, read at run time |
| `classification` | `deepseek` | `https://api.deepseek.com/v1` | `deepseek-v4-flash` | — | `DEEPSEEK_API_KEY` env var, read at run time |

The rows are written inline (`provider_id`/`profile_id` left `NULL`) rather
than through the setup wizard's provider/profile bookkeeping —
`LLMPurposeConfigRow` supports a purpose running standalone this way; see
`app/api/routes/setup.py`'s finalize handler for the full wizard path this
intentionally does not replicate. `seed_llm_purpose_configs()` is
update-or-insert per purpose, so it is safe to call again against a schema
it already seeded.

The DeepSeek API key is never written to this file, to git, to a fixture, or
to the ledger. `run_smoke.require_deepseek_api_key()` fails with an explicit
`RuntimeError` naming the missing environment variable if `DEEPSEEK_API_KEY`
is unset, rather than letting a call reach the vendor and come back a bare
401.

## Why pass 1's live-call count is reported but deliberately not asserted

`run_smoke.py` prints `pass 1 live LLM calls: N` but never asserts `N > 0`.
This is intentional, not an oversight: the disk cache is keyed on content,
not on which pass wrote it, so a rerun of `run_smoke.py` against an
already-warm `smoke/cache/` directory (the normal case after the first
invocation on a given machine) legitimately makes zero live calls on pass 1
too — asserting `first.live_calls > 0` would make the gate fail on its own
second consecutive run, which is useless for CI. The actual health check —
`find_outcome_failures`, asserted on both passes — does not depend on
`live_calls` at all: it reads each outcome's `embed`/`extract`/`vector`/
`graph` status and `error` field directly, so a broken pipeline is caught
whether the cache was cold or warm. Do not add a `first.live_calls > 0`
assertion back in; it does not detect anything `find_outcome_failures`
doesn't already catch, and it breaks idempotent re-runs.

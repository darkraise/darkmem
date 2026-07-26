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

- `embed` / `embed_batch`: `payload` is the literal text (one cache entry
  per unique text, shared between the two entry points).
- `chat_completion`: `payload` is `[purpose, messages, sorted(kwargs.items())]`
  — `messages` includes the system prompt, so a cached output is valid only
  for the exact prompt it was produced under (doc 17 §7: "a cached output
  is valid only for the prompt it was keyed under"). Changing the
  extraction/classification prompt, the gate state that selects it
  (`classification_mode`, `ml_profile_ref` — see `ingest.GateConfig`), or
  any call kwarg (e.g. `seed`) invalidates the cache for that call
  automatically, by construction, with no separate invalidation step.

Cache entries are one JSON file per key under the orchestrator's `cache_dir`,
written once and read on every subsequent call with the same key. Nothing in
`benchlib` commits a populated cache directory to git — `run_smoke.py`'s
cache lives at `backend/scripts/benchlib/smoke/cache/`, gitignored, so every
environment (a fresh CI checkout, a fresh dev machine) pays the first pass's
genuine model cost once and then reuses it locally, the same way
`extraction_bench/.cache/` already works.

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

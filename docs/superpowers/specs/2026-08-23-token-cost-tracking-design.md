# Token and cost tracking — what each operation costs, and where the waste is

**Status:** design, pre-implementation. **Touches:** the baseline schema,
`LLMOrchestrator` and its six vendor request paths, `llm_quirks.py`,
`pipeline.py` Phase 2, `JobRegistry`, the retrieval and chat request scopes,
`reembed`/`repos` maintenance routes, a new REST surface, a new settings panel,
a new dashboard surface, and the deployment runbook.

**Goal, in the owner's words:** *"When know the cost of operation, I can optimize
the wasted part."* Visibility is the means; optimisation is the end. The design
is therefore sliced by the things an operator can actually change — purpose,
model, cache-hit rate, retries, and failed work — not merely totalled. No
budgets, no enforcement, no capture-time refusal.

**This revision incorporates an adversarial review** that found three
load-bearing errors in the first draft: `_log_usage` is not a chokepoint
(embeddings, both stream paths, and every failure bypass it), the contextvar
attribution mechanism was stated falsely, and `job_runs.id` does not exist at
call time. §9 records the disposition.

---

## 0. What already exists, and what it proves

Three pieces of prior art constrain this design more than any new decision in
it.

`LLMOrchestrator._log_usage` (`app/services/llm.py:458`) already parses the
usage envelope for the two non-streaming chat paths, and its docstring is
already the per-vendor catalogue of cache-hit field names and billing ratios:
OpenAI at `usage.prompt_tokens_details.cached_tokens` billed at 50% of input,
DeepSeek at `usage.prompt_cache_hit_tokens` billed at roughly 5%, z.ai
surfacing no field through the compat path, and Anthropic caching that never
fires there at all. That prose is the price model's source data.

`benchlib/twin.py` establishes the doctrine this design inherits: a spy that
wraps a shipping method and calls straight through is a measurement, while
reimplementing a channel to time it is a fork. Its report prints
`tokens: not measured` rather than `0` when no purpose recorded usage. A number
nobody observed is not zero.

`JobRegistry._record_run`'s docstring (`app/services/job_registry.py:434`)
already decided this feature's storage question for job telemetry: *"Writes go
to `job_runs`, never `events`: that table is append-only by trigger and
permanent by ruling, and telemetry that wants pruning has no business in the
substrate gate metrics are computed from."* Token metering is telemetry of
exactly that kind. This design follows the precedent rather than inventing one.

---

## 1. Storage: a dedicated table, not `events`

`events` was considered and rejected. It is append-only by three trigger kinds
and permanent by the T2.59 ruling; G-C's promotion metrics are SQL over it
alone; `EVENT_TYPES` is a closed vocabulary requiring taxonomy-first widening;
and `/events`, `/events/timeline` and `/events/calendar` enumerate object types,
so the highest-frequency operation in the system would flood the audit read
surfaces. A monthly child could be dropped by DDL, so "unprunable" is
technically overstated — but building a partition-drop retention path against a
substrate that is append-only *by ruling* is a policy breach dressed as a
feature.

`llm_usage` is a plain table shaped after `job_runs`: no partitioning, its own
cleanup job, no foreign keys to the things it describes.

| column | type | note |
|---|---|---|
| `id` | uuid pk | |
| `occurred_at` | timestamptz | |
| `purpose` | text | one of the eight |
| `model`, `provider`, `api_kind` | text | resolved at call time |
| `subject_type` | text | closed set, §3 |
| `subject_id` | text | not a uuid column: job subjects are composite |
| `project` | text, null | |
| `prompt_tokens`, `cached_tokens`, `completion_tokens`, `reasoning_tokens` | int, null | null when unmeasured |
| `tokens_measured` | bool | false ≠ zero |
| `cost_micros` | bigint, null | integer micro-USD; null when unpriced |
| `rates_used` | jsonb | the three rates actually applied |
| `usage_raw` | jsonb | the whole envelope, unflattened |
| `ok` | bool | |
| `error_kind` | text, null | |
| `duration_ms` | int | |

Indexes: `(subject_type, subject_id)` for the detail views, `(occurred_at)` for
the overview and the retention sweep, `(purpose, occurred_at)` for the
by-purpose rollup.

`cost_micros` is an integer, not a float. `memories.confidence` being REAL is
not a precedent for money. `subject_id` is text because job subjects are
`job_key@started_at` composites and search subjects are request ids; a uuid
column would force a fake id for two of the six subject types.

`usage_raw` exists because the envelope carries fields this design has not
thought to name — `completion_tokens_details.reasoning_tokens` today, whatever
a vendor adds next. Flattening to four integers at write time makes a future
question unanswerable against history that was already paid for.

---

## 2. Capture: six paths, not one function

`LLMOrchestrator` is the only module in `backend/app` that spends tokens. The
three call sites that reach a vendor outside it — `api/routes/setup.py:106`,
`api/routes/llm_providers.py:122`, `main.py:920` — are model-list probes with no
token cost. The module is a chokepoint; `_log_usage` is not.

`_log_usage` is reached only from the compat chat path (`llm.py:339`) and,
conditionally, the native one (`llm.py:424`). Bypassing it entirely:

- **Embeddings.** `embed` (:159), `embed_batch` (:196) and
  `embed_batch_chunked` (:238) read only `["data"][0]["embedding"]` and
  `["embeddings"][0]`. OpenAI-compat embeddings carry `usage.prompt_tokens`;
  Ollama `/api/embed` carries `prompt_eval_count`. Both are discarded.
- **Both stream paths.** `chat_completion_stream` (:566) builds its compat body
  with `stream: True` and no `stream_options: {"include_usage": true}`, so no
  usage is ever sent. The native branch does `if chunk.get("done"): break`
  (:602) — and Ollama's `done` chunk is precisely the one carrying
  `prompt_eval_count`/`eval_count`. The numbers arrive and are dropped one line
  before they could be read. `ChatService` streams every answer, so **all chat
  generation cost is unmeasurable today.**
- **Every failure.** `httpx.ReadTimeout` (:325) and `HTTPStatusError` (:335)
  raise before the logging line. Failed work — the waste this feature exists to
  find — cannot be recorded there.

`_log_usage` is also a synchronous `@staticmethod` with no session.

**Therefore:** a `UsageRecorder` wraps the request/response cycle of six paths —
chat compat, chat native, stream compat, stream native, `embed`, `embed_batch`
— capturing success and failure alike. `_log_usage` remains as the human-facing
log line and gains no new duty. `embed_batch_chunked` composes `embed_batch`
and needs no separate wrapping.

Two enabling fixes ship with it, without which two of the four required sources
stay invisible:

1. The embed paths read and return their usage envelope.
2. The native stream reads the `done` chunk before breaking; the compat stream
   sends `stream_options` where the vendor accepts it.

### 2.1 Vendor differences live in `VendorQuirks`

`tests/test_api_kind_dispatch.py:264` walks every module under `app/` except
`llm_quirks.py` and fails the build on any `ast.Compare` containing a vendor-name
string. The natural
`if api_kind == "deepseek": read prompt_cache_hit_tokens` is a build failure.

Two fields join `VendorQuirks` beside `honours_seed` and `output_cap_key`:

- `stream_usage_option: bool` — whether the compat stream accepts
  `stream_options: {"include_usage": true}`.
- `cache_hit_fields: tuple[str, ...]` — the envelope paths to try for the
  cached-token count, in order. Empty for vendors that surface none.

The orchestrator, the recorder and the price model all read these. No call site
compares `api_kind` to a literal.

### 2.2 Writes go on an independent session

The pipeline's Phase 5 runs in two savepoints, and an extraction failure never
enters savepoint B at all. A usage row written on the caller's session is rolled
back with the work it describes — so the failed-work rows, the ones this feature
is for, would delete their own evidence.

The recorder commits on its own short-lived session after the vendor call
returns. It degrades loudly and never raises into the LLM path, mirroring
`record_event`'s contract. Invariant 13's single worker makes this safe without
cross-process coordination; the "async session lifetime" invariant permits it
because the rows share no locks with the caller's transaction.

The orchestrator is rebuilt whenever the LLM config is saved
(`api/routes/config.py:95`), so the recorder holds no buffered state that would
need flushing across that swap: one row, one commit, per call.

---

## 3. Attribution

The subject is passed explicitly. The first draft claimed a `contextvar` would
attribute per memory because "contextvars copy into asyncio tasks at creation".
They do — and every task created by `asyncio.gather` at `pipeline.py:1008`/1027
copies the *same parent* context, so without a per-entry write every call in a
batch attributes to the batch. The claim was false and the mechanism is
abandoned for ingest.

| `subject_type` | `subject_id` | set where |
|---|---|---|
| `memory` | memory uuid | threaded into `run_extract`/`run_classify` (`pipeline.py:967,983`) |
| `job_run` | `{job_key}@{started_at.isoformat()}` | `JobRegistry` around the runner |
| `search` | request id | retrieval request scope |
| `chat` | request id | chat request scope |
| `maintenance` | `{kind}:{target_id}` | reembed, repo reindex, wiki generation |
| `batch` | pipeline batch id | content and entity-name embeds |

A contextvar still carries the *ambient* subject for jobs and requests, where
one scope genuinely wraps many calls. Ingest overrides it explicitly per entry.
Innermost wins; an unattributed call inside a job inherits the job subject
rather than falling to null. A call with no subject at all is still recorded and
still counted in totals.

**Why not `job_runs.id`:** the row is written by `_record_run` *after* the
runner returns (`job_registry.py:414`) from a server-side `gen_random_uuid()`,
and a runner returning a falsy summary writes no row at all (:443). At call
time the id does not exist, and for some runs it never will. The composite key
is always available — `started_at` is set at :380 before the runner fires — and
needs no foreign key, matching how `job_runs` itself references jobs by key.

### 3.1 Three places where per-memory attribution would be a lie

**Content embeds.** `embed_batch_chunked` (`pipeline.py:918`) sends one call for
the whole batch. Recorded against `batch`, never divided.

**Entity-name embeds.** `_embed_entity_names` (`pipeline.py:383`) dedupes names
across memories and serves hits from a memory cache and then a DB cache before
embedding the remainder. A per-memory share is not imprecise, it is undefined:
a memory whose entities were all cache hits cost nothing. Recorded against
`batch`.

**The merged call.** When the classifier is LLM-backed and
`classification_mode == 'simple'`, extraction and classification fold into one
call (`pipeline.py:1004`). One row, `purpose='extraction'`, with
`merged_classification=true` in `usage_raw`. Splitting the tokens across two
purposes would be invention.

The consequence must be stated on the surface, not buried: **under the default
configuration, classification's purpose total will read near zero.** An operator
hunting waste who reads that as "classification is free" has been misled by the
feature. The overview labels the extraction row *"includes folded
classification"* whenever merged rows exist in the window.

---

## 4. Pricing

Three rates per model, not two: input, cached-input, output. A cached input
token bills at roughly 5% on DeepSeek and 50% on OpenAI, so a two-rate table
would be wrong by up to twentyfold on the one axis most worth optimising. An
Anthropic row must not carry a cache discount, because caching never fires
through the compat path this orchestrator dispatches it on.

Prices follow the `feature_flags` pattern exactly: a shipped
`DEFAULT_MODEL_PRICES` table merged under a `config` row (`model_prices`), so an
absent model falls back to its default and an operator override is one row. The
settings surface edits that row.

Cost is computed at call time and stored, together with `rates_used`. A later
price edit never rewrites history — you paid what you paid — and an operator can
audit the arithmetic without knowing what the table said that day.

Four states are distinct and must never collapse into each other:

- **priced** — tokens measured, a rate existed, `cost_micros` is a number.
- **free** — tokens measured, the model is local, `cost_micros = 0`. A true
  measured zero.
- **unpriced** — tokens measured, no rate for this model. `cost_micros` null,
  surfaced as *"not priced"* with the model named, so the fix is obvious.
- **unmeasured** — `tokens_measured = false`. Surfaced as *"not measured"*.
  Never rendered as 0.

---

## 5. Read API

Four endpoints under `/api/v1/usage`, following `docs/api-rest-conventions.md`.

- `GET /usage/overview?window=30d` — totals, plus breakdowns by purpose, by
  model, and by subject type; cache-hit ratio; failed-call count and their cost;
  the merged-classification caveat flag; and counts of unpriced and unmeasured
  calls so the numbers carry their own confidence.
- `GET /usage/series?window=30d&bucket=day` — cost and tokens per bucket, for
  the trend that answers "did my change help".
- `GET /usage/by-subject/{subject_type}/{subject_id}` — the per-memory and
  per-job-run detail.
- `GET /usage/top?window=30d&by=cost&limit=20` — the outlier list. The most
  directly actionable surface: the memories and job runs that cost
  disproportionately.

All aggregation is SQL over `llm_usage`. No post-fetch Python filtering, matching
how `list_events` builds its predicates.

---

## 6. UI

**Overview** — a new dashboard surface. Headline spend for the window, a trend
sparkline, breakdown tables by purpose and model, cache-hit ratio, and a "waste"
panel: failed calls and what they cost, unpriced models, and the top-N most
expensive subjects. Every aggregate that excludes unmeasured or unpriced calls
says so beside the number.

**Per-memory** — a cost row on the memory detail view: total, and the per-purpose
lines that produced it, with embedding shown as *batched* rather than as a
fabricated share.

**Per-job** — a cost column in the existing job history dialog.

**Settings** — a prices panel beside the LLM tab, editing the `model_prices`
config row, showing which models are seeded and which are operator-set.

All of it uses the shared `settings-rows.tsx` primitives and `darkraise-ui`
components; no new local component without a stated library gap.

---

## 7. Retention

`llm_usage_cleanup`, a registered job on the `job_run_cleanup` pattern, with a
`config_schema` carrying its retention window. Volume at homelab scale is
modest — roughly two rows per ingested memory under the merged path, up to
forty-one per reranked search, a handful per chat — so row-level retention with
no rollup table is enough. No pre-aggregation until the overview demonstrably
needs it.

Adding it is a deliberate three-file diff: `app/main.py`, the roster pin in
`tests/test_code_deriver.py`, and CLAUDE.md's registered-job count, which has
gone stale three times before and is exactly the invariant-23 shape that file
warns about.

---

## 8. Rollout

This adds a table, so the pre-freeze policy applies in full: regenerate
`0001_baseline.py`, then drop and recreate the deployed database.

**The cost is larger than the memories.** A drop destroys the entire `events`
journal — the substrate G-C's promotion metrics are computed from and where the
G-E corpus clock armed on 2026-08-17 is running — plus `knowledge_triples`,
`fact_sources`, research origins, and every `config` row including feature
flags, job configs, the armed `auto_research` row and `admin_password_hash`.

Procedure, per `docs/runbook-deployment.md`:

1. `pg_dump` the live database. `darkmem-backup.timer` runs nightly at 03:30
   with `Persistent=true`, so a recent dump already exists; take a fresh one
   regardless.
2. Regenerate the baseline; verify `scripts/gate.sh`'s single-revision assertion.
3. Drop and recreate; `alembic upgrade head`.
4. Restore data. A data-only restore needs the historical monthly `events`
   partitions to exist first — boot only ensures current-and-next month — so
   either call `events_ensure_partition` for the historical months or restore
   schema-with-data.
5. Re-seed `admin_password_hash` and all eight `llm_purpose_configs` rows.
   `llm_seed.py:196` seeds `verification` at a local Ollama model, **not** at the
   qualified judge identity `gpt-5.5`/OpenAI; that row is restored by hand or
   G-D's minted qualification stops resolving.
6. Boot. `schema_guard` adopts the new hash automatically against a freshly
   created database — a NULL stored hash stamps and admits. It fails closed only
   when the new image meets a database that was *not* recreated.

---

## 9. Review disposition

An adversarial review of revision 0 returned six findings; five changed the
design.

| finding | disposition |
|---|---|
| `_log_usage` is not a chokepoint — embeds, both streams and all failures bypass it; chat cost is unmeasurable today | **Design changed.** §2: six wrapped paths plus two enabling fixes. |
| The contextvar/`gather` mechanism was stated falsely | **Design changed.** §3: explicit threading for ingest; ambient scope kept only where one scope truly wraps many calls. |
| `job_runs.id` does not exist at call time and sometimes never exists | **Design changed.** §3: composite `job_key@started_at`, no FK. |
| Savepoint rollback would erase the failed-work rows | **Design changed.** §2.2: independent session. |
| A vendor literal outside `llm_quirks.py` fails the build | **Design changed.** §2.1: two new quirk fields. |
| `events` rejection correct, and already precedented by `_record_run` | **Accepted.** §0 and §1 now cite the precedent. |
| Drop/recreate cost understated as "50 memories" | **Accepted.** §8 states the full inventory. |
| `schema_guard` auto-stamps; there is no manual hash step | **Accepted.** §8 step 6 corrected. |
| Reranker is one call per document, ~41 per reranked search | **Accepted** as the headline cardinality driver; §7 sizes retention on it. |
| Maintenance spend (reembed, reindex, wiki) fits no named subject | **Design changed.** §3 adds `maintenance`. |
| Three price rates, integer money, raw envelope retained | **Design changed.** §1 and §4. |

**Out of scope, stated so it is not assumed:** `backend/scripts` bench and gate
runs spend real vendor money through `benchlib`, outside the app runtime and
outside the production database. This feature will never see that spend. If
"the cost of operation" is meant to include gate re-measurements, that is a
ledger-side problem and a separate design.

**Unverified at design time:** whether the `/mcp` mounted sub-app propagates a
request-scoped contextvar into tool bodies. If MCP tool execution spawns tasks
outside the request context, `memory_reason`'s chat calls land unattributed
rather than under `chat`. To be confirmed during implementation; the fallback is
harmless (null subject, still counted).

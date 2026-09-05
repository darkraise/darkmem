# Darkmem — business logic baseline

Centralized memory system for AI agents. Commands and layout first;
everything from "Domain model" down is contract, not implementation
detail. A refactor that breaks one of the listed invariants is a
behavior change, not a cleanup.

## Greenfield until the freeze (owner ruling 2026-08-31)

**Darkmem is in development and is treated as a greenfield project. No
backward compatibility is owed and no data migration is ever required.** No
deployed database, no earlier release and no previously captured corpus is a
constraint on a change: if a new shape is better, take it and recreate the
data. Do not design a compatibility shim, a dual-write, a version negotiation
or an import path for existing rows, and do not weigh "what about the data
already in there" when choosing between designs — the answer is always that it
is disposable.

This is what the baseline's drop-and-recreate rule below already assumes, and
it is now stated once here rather than inferred per task. It holds **until the
schema freeze** — the first deploy whose data must survive, defined under
Migrations below. At that event this section is retired and ordinary additive
migration discipline begins; nothing before it is grandfathered.

## Commands

- **Merge gate (from the repo root): `./scripts/gate.sh`** — one command for
  the whole floor: the alembic single-revision assertion, backend pytest,
  frontend typecheck/test/build, the browser-extension suite, **both SDK
  suites** (`sdks/python` under pytest, `sdks/ts` under the frontend's vitest),
  the benchlib harness suite, and the F1 bench
  in `--algo-only` mode. `--full` adds the retrieval eval, the API e2e
  suite (`backend/scripts/e2e/`, boots its own disposable stack), the
  Playwright e2e run, and a port-hygiene diff.
  Exits non-zero naming the failing gate; `GATE BLOCKED` (exit 2) means a
  missing toolchain, not a red gate.
  **`--full` needs `DEEPSEEK_API_KEY` exported** (the retrieval eval refuses to
  start without it) — though on a warm cache that eval is a replay at **0 live
  calls**, so the key is a precondition rather than a spend.
  **A red Playwright leg on this host is a kill before it is a regression.**
  An `earlyoom` daemon runs here and the suite is already at `workers: 1`, so
  there is no tuning headroom: measured 2026-09-02, one unchanged commit gave
  47 passed → 13 failed → 47 passed, the failures being `Target crashed` and
  `ERR_CONNECTION_REFUSED` after the vite server died. Re-run it standalone
  through `backend/scripts/e2e/run_playwright_e2e.py` before believing a red,
  and never invoke Playwright bare. This was recorded in five 2026-08-31 plans
  and nowhere a later session would look, which is why it kept being
  rediscovered. **`pyproject.toml` sets
  `testpaths = ["tests"]`, so plain `pytest -q` does NOT collect
  `scripts/benchlib/tests`** — run the gate, or the harness can break while the
  floor stays green.
- Backend tests (from `backend/`): `python -m pytest -q`. Needs a
  `darkmem_test` database on the dev-compose Postgres
  (127.0.0.1:5433); create it once:
  `psql -h localhost -p 5433 -U darkmem -d darkmem -c "CREATE DATABASE darkmem_test;"`.
  conftest pins `DATABASE_URL` to `TEST_DATABASE_URL` (default
  `postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test`),
  then runs `DROP SCHEMA public CASCADE` and `alembic upgrade head` —
  never point it at a real database.
- Frontend (from `frontend/`): `npm run typecheck` (= `tsc -b`; plain
  `tsc` misses the project refs), `npm test` (vitest; excludes
  `tests/`, which is Playwright e2e via `npm run test:e2e`),
  `npm run build`. `npm run lint` is advisory.
- Dev servers: `./scripts/start_dev_server.sh` = alembic upgrade +
  uvicorn :8000 `--reload --timeout-keep-alive 75` (the 75 prevents
  sporadic 502s through the vite proxy); `cd frontend && npm run dev`
  = vite :3636 proxying `/api`, `/health`, `/ws` to :8000.
- Migrations (from `backend/`): `python -m alembic upgrade head`.
  `migrations/env.py` reads `DATABASE_URL` via app settings (default
  port 5432) and ignores `alembic.ini`'s URL; the dev-compose Postgres
  is on 5433, so set `DATABASE_URL` explicitly for host-side runs.
  Containers migrate at startup via `entrypoint.sh`;
  docker-compose.dev.yml overrides the command and skips migrations.
- **The schema is ONE revision — `0001_baseline.py` — and it is not
  frozen yet.** Until the freeze, a schema change **regenerates that
  file in place** and you drop/recreate the database; it never appends
  a `0002`. `./scripts/gate.sh` asserts exactly one revision and fails
  loudly otherwise.
  **The drop/recreate half is not enforced anywhere, and a deployed
  database silently drifts because of it** (measured on production
  2026-08-17). The revision id never moves, so `alembic upgrade head` —
  which `entrypoint.sh` runs at every container start — finds current ==
  head on a database already stamped `0001` and does nothing. **Every
  deploy since a baseline change therefore reports a clean migration
  while running against a schema it does not have.** Production was
  missing five columns and `article_synthesis` had been dying on every
  scheduled run; the failure surfaced only in that job's `config` row,
  not in any log or health check. The gate asserts the *tree* holds one
  revision and says nothing about any running database. **After
  regenerating the baseline, drop and recreate every deployed database
  yourself**, and re-seed `admin_password_hash` plus all eight
  `llm_purpose_configs` rows — the `verification` row especially, since
  `llm_seed.py` does not reproduce it at the qualified judge identity.
  **Since 2026-08-17 a boot check enforces this rather than trusting the
  policy**: `app/schema_guard.py` runs from `entrypoint.sh` after the
  migration, stamps a hash of the baseline file into the database it
  migrated, and **refuses to start** when the two disagree — the revision
  id cannot detect a regenerated baseline, but its content can. It fails
  closed with no override flag, and **must be retired at the freeze**,
  when revisions become additive and alembic's own comparison does the
  job. Procedure, and the two rows a re-seed does NOT reproduce:
  `docs/runbook-deployment.md`.
  Analysis: `docs/planning/analyses/2026-08-17-production-schema-drift.md`. Schema changes **serialise through one owner per
  epic**: the baseline is a single shared mutable file, so two lanes
  editing it conflict every time. The freeze is an **event, not a
  date** — the first deploy whose data must survive (the homelab
  cutover). At that event the revision is tagged `schema-frozen`, the
  gate assertion stands down, and every later change is an ordinary
  additive revision forever. **Freeze date: not yet frozen, and the trigger is now
  stated rather than inferred (owner ruling 2026-08-15).** This is a greenfield
  project, so a deploy carrying disposable data is *not* the trigger — v0.5 is
  deployed and did not fire it. The freeze happens **after v1.0 ships and after
  the owner's review of the visual web UI passes**, and not before. Do not read
  "the corpus can begin" or any deploy as the event. Full
  protocol and the object inventory the baseline implements:
  `docs/planning/baseline-schema-inventory.md`.
- Stacks: dev `docker compose -f docker-compose.dev.yml up -d` (no
  .env needed); prod `docker compose up -d` (requires `DB_PASSWORD` +
  `JWT_SECRET` ≥ 32 chars in .env, `COOKIE_SECURE=false` for plain-HTTP LAN).
  Rebuild the image first: `DARKMEM_PUSH=0 ./scripts/build-push.sh` — the
  `DARKMEM_PUSH=0` is not optional and this line carried a bare invocation
  until 2026-08-21, which is the one command the CI-only ruling below forbids:
  the script's default is `DARKMEM_PUSH=1` and it pushes. **One** image,
  `darkraise/darkmem`, built from the repo-root `Dockerfile`, carrying the API
  and the built SPA together; the app serves the UI on `:8000` and nothing
  binds `:80`. **Renamed from `darkraise/darkmem-api` on 2026-08-18** (owner
  ruling) because the `-api` name described half the artifact; the compose
  service was renamed `darkmem-api → darkmem` in the same change, so a stack
  brought up from the old file leaves an orphan container and the cutover
  needs `docker compose down --remove-orphans`. Any `DARKMEM_VERSION` pinned
  under the old image name no longer resolves.
- **Redeploy this machine after every change that lands** (owner ruling
  2026-08-21). Implementing a feature or fixing a bug is not finished when the
  gate goes green: this host runs the live instance the owner reviews, so a
  merged-but-undeployed change leaves them looking at the previous build —
  reporting bugs that are already fixed, or missing ones that are not. Both
  happen; the second is worse, because the review reads as a pass.
  Scoped to changes that alter the running artifact — `backend/`, `frontend/`,
  the `Dockerfile`, compose, `entrypoint.sh`. A docs, planning or CLAUDE.md
  change carries nothing the image does, and rebuilding for one only makes the
  rule read as ceremony.
  The sequence is `./scripts/gate.sh` → `DARKMEM_PUSH=0 ./scripts/build-push.sh`
  → `docker compose up -d` → wait for the container to report `healthy`, then
  **confirm the change is in the running image rather than only in the tree**
  (`docker exec darkmem-prod-darkmem-1 grep ...` against the built file, or the
  new field on `/openapi.json`) — compose reuses an image whose tag did not
  move, so a skipped or failed build redeploys the old bits and still reports
  `Started`.
  **This is a deploy, not a release.** No tag is written and nothing reaches a
  registry; the running image is an untagged local `:latest`. **Since 2026-08-29
  a push to master is what releases** (owner ruling): `release.yml` derives the
  next version from the conventional-commit types since the last tag, runs CI,
  publishes to Docker Hub and GHCR, and **only then** writes the tag and the
  GitHub release — so a tag that exists is a tag whose image was published, and
  a failed publish leaves nothing to explain away. Two guards replace the old
  hand-pushed tag: a push carrying no `feat`, `fix`, `perf` or breaking commit
  cuts nothing, and a push whose derived version has no `## vN.N.N` section in
  `CHANGELOG.md` fails before the suite runs. The changelog stays hand-written;
  only the GitHub release body is generated (`scripts/next_version.py`).
  `./scripts/release.sh vN.N.N` **no longer tags** — it is the local pre-flight
  (sync the version fields, build, deploy, probe `/openapi.json`), and CI then
  skips its own bump because the fields already name the version. Never publish
  an image from this machine: `.github/workflows/release.yml` is still the only
  path to a registry. Prefer the script over a bare `docker build` for one concrete
  reason: it also tags the image with the short git sha, so `docker inspect`
  answers *which commit is running* rather than only `:latest`.
- **Prod networking is bridge, not host** — re-decided 2026-08-18 (owner
  ruling), replacing the host networking both services used since v0.1. Ports
  are now published explicitly: the app `8000:8000`, Postgres
  `127.0.0.1:5432:5432` (host loopback only, the same reachability host
  networking gave it, so host-side `pg_dump`/`psql` are unaffected). Two
  couplings make this more than a flag. **Postgres must listen beyond
  loopback** (`listen_addresses=*`, was `127.0.0.1`): the API now connects
  across the stack network, and the old pin would refuse every application
  connection while `pg_isready` still reported healthy. And **the login rate
  limiter's bucket changes for some callers**: `_client_ip` keys on the
  transport peer (`trust_proxy_headers` off, `--no-proxy-headers` everywhere),
  and measured on this host, a LAN client's source address survives the DNAT
  intact while a request to `127.0.0.1` and a request from another Docker
  network both arrive as the bridge gateway and therefore **share one
  bucket** — five failed host-local logins lock out host-local logins.
  Accepted for a single-operator homelab. It is **not** repaired by turning
  `TRUST_PROXY_HEADERS` on: Docker's NAT sets neither `X-Real-IP` nor
  `X-Forwarded-For`, so the fallback lands on the same gateway address, and
  the flag would additionally clamp `cookie_secure` to true (breaking
  plain-HTTP LAN login) and arm the `/mcp` proxied guard. Reintroducing
  `network_mode: host` is a silent regression rather than a loud one — it
  ignores every `ports:` mapping without erroring — so
  `tests/test_deployment_artifact.py` asserts the bridge network, both
  publish bindings, and the `listen_addresses` pairing.
- **Backups (homelab, T1.54): `systemd` timer `darkmem-backup.timer`**, nightly at
  03:30 with `Persistent=true` so a night the host was down is caught up rather
  than skipped. It runs `scripts/backup.sh /root/darkmem-backups`, which dumps
  the live compose database and **prunes to the newest `BACKUP_KEEP` (14)** —
  the script had no retention until 2026-08-13, and an unpruned nightly cadence
  on the host that also runs the database is a slow disk-fill that takes
  production down with it. Dumps are local only: copying them off-host is still
  a manual step and nothing enforces it.
- Backend lock: regenerate only with
  `uv pip compile --universal pyproject.toml -o requirements.lock` —
  a non-universal Windows resolve leaks pywin32 and drops uvloop.
  `entrypoint.sh` must stay LF (.gitattributes enforces it).

## Layout

`backend/app`: `api/routes` (REST), `api/mcp` (`MCPServer`, mounted at
`/mcp`), `services` (pipeline.py, extraction_clean.py,
code_pipeline.py, job_registry.py, ...), `repositories`
(graph/relational/vector), `models`, `schemas`; entry point
`app/main.py`. `backend/migrations/versions` is Alembic;
`backend/scripts` holds the eval harnesses: `extraction_bench/` (the F1
bench and its gold files) and `benchlib/` (corpus loader, offline ingest
driver, run ledger, retrieval gold + scorer, latency/token twin,
full-context comparator, and the `run_*.py` runners).
`frontend/src`: `features/*` plus TanStack Router file-based `routes/`
— `routeTree.gen.ts` is generated, never hand-edit it. `docs/` holds
dated audit reports, `api-rest-conventions.md` (the REST contract new
endpoints must match: 201 create, 204 delete, 202 async-accepted,
POST `.../search` for complex queries), `superpowers/specs/` design
specs, and `e2e/` runbooks.

## UI components come from darkraise-ui first

**Before building any UI, check whether `darkraise-ui` already ships the
component.** It is a large library — segmented controls (`segment-group`),
`number-input`, `switch`, `toggle-group`, `empty-state`, `sonner` toasts,
`dialog`, `card`, `tabs`, `stat`, `timeline`, `tree-view`, `combobox`,
`multi-select`, `date-picker` and ~70 more live under
`darkraise-ui/components/*`. Enumerate them with
`ls frontend/node_modules/darkraise-ui/dist/components/`, and read the `.d.ts`
beside the one you want — the props carry their own doc comments.

A new local component is a last resort, justified only by the library having no
equivalent. **Restyling a built-in to fit darkmem's design is encouraged**;
re-implementing one is not. The cost of ignoring this is not hypothetical: the
sidebar carried a hand-rolled search palette for months as a workaround for a
library limitation, and when v6 lifted that limitation the workaround became a
duplicate search box that also suppressed the built-in's Ctrl+K. **A local
component written against a library gap must record which gap**, so the next
upgrade can retire it.

Two distribution clients sit **outside** the box (doc 15 §2) and speak REST
or MCP into the one instance: `extension/` (the browser capture shell) and
`sdks/` (the minimal client, three verbs). **`sdks/ts/src/client.ts` and
`sdks/python/darkmem_sdk/client.py` are generated** — edit `sdks/generate.py`
and run `make generate` in `sdks/`, never the emitted files. The generator
reads the live OpenAPI document off the app object and **refuses to generate**
when a verb names a route, a request-body field, or a header the contract does
not serve; that refusal is the whole reason the SDK is generated rather than
written (invariant 17).

## Domain model

Memory rows live in `memories`. Each row has a status lifecycle:
`active → superseded → deprecated`. The CHECK constraint
`chk_superseded_has_pointer` forbids `status='superseded'` without
`superseded_by` set; supersession code must always set both atomically.
Memories may carry `expires_at` (nullable TTL); the
`expired_memory_cleanup` job deletes rows past it. Before deleting any
memory that others reference via `superseded_by` (TTL sweep or
interactive delete), demote those dependents to `status='deprecated'`
with `superseded_by=NULL` first — the FK is ON DELETE SET NULL, so
skipping the demotion violates `chk_superseded_has_pointer` and aborts
the whole batch.

A memory carries:

- `content` (Text) and `source` (where it came from: `mcp`, `api`, ...).
- `project` (Text, default `default`) — the supersession scope.
- `memory_type` from `MEMORY_TYPES` in `app.taxonomy`.
- `classified_type` / `summary` / `emotions` / `flags` —
  classification/enrichment output, populated on every ingest. The `llm_`
  prefix was dropped in the baseline (doc 04 §3.1) because the classifier
  may be the local model, and T1.42e (2026-07-28) retired the prefix from
  every wire surface too: REST (`MemoryResponse`, `app/utils/serialization.py`)
  and the websocket broadcast payload (`app/services/pipeline.py`) now read
  `classified_type` / `summary` / `emotions` / `flags`, matching the columns
  exactly, with no compatibility shim and no dual emission. The regex
  classifier and its `classified_confidence` column are gone; classification
  runs through the LLM, or the in-process classifier when the classification
  purpose's inline `classifier_kind` is `local`.
- `origin_key` (Text, nullable) — capture-session identity, the
  corroboration-independence key facts count `DISTINCT` on. **It has writers on
  both doors** since T1.11 (`resolve_origin_key`, called from
  `api/routes/memories.py` and `api/mcp/server.py`, and on the raw entry dicts
  for batch adds) — **and since T3.07 from a third caller that is not a door**,
  `services/auto_research.py` (the count above updated 2026-08-12; this said
  "both doors" full stop, which is the "here is the full list" shape invariant
  23 is about). **That third caller stamps one origin per evidence *source*,
  and the identity is the source's, never the run's or the finding's** — T3.07
  landed it merged to one bucket and T3.08 filled the seam, so the paragraph
  saying it "resolves a *merged* key on purpose" describes only what an
  unestablishable identity still does. `research_origin_id` canonicalises the
  gatherer's locator (scheme, host case, `www.`, default port, credentials,
  trailing and duplicated slashes, fragment, campaign parameters, parameter
  order all collapse, and since T3.08's review the RFC 3986 §6.2.2-6.2.3
  equivalences too — percent-encoding, dot-segments, punycode, NFC/NFD, a
  duplicated identical parameter), so a refetch, a re-run or a paraphrase of one
  page adds no origin. **Two genuine sources promote only on the ladder's own
  terms** — both carry `source_kind='memory'`, so there is no kind diversity and
  two same-day research origins *hold* at N = 3; they promote ≥ 7 days apart, or
  same-day at three. Every step of that canonicalisation aims to be
  merge-only: no input should split one source into two ids, because an
  undercount delays a promotion and an overcount fabricates one. **That claim
  was stated as holding "by construction" and has now been falsified four
  times — twice by reviews, then twice by the repairs themselves.** T3.08's
  review found six splitting inputs; v0.5's version review found eleven more
  over 26 same-source pairs (2026-08-15), including the one that matters most: this
  module normalised hosts through Python's IDNA**2003** codec while `httpx`
  emits IDNA**2008**, so `straße.example` and the `xn--strae-oqa.example` the
  client produces for it were two attributable origins — one page, and at seven
  days' spacing a promotion. Then the repair reattached a non-default port
  before the host passes ran and thereby split IDN-with-port pairs, and the
  repair of *that* widened the slash fold and thereby split `file:`
  empty-authority pairs — `httpx` emits `file:/tmp/a.pdf` for
  `file:///tmp/a.pdf`, and the fold read that spelling as host `tmp`. All are
  repaired and pinned; the host pass goes through the `idna` package with
  `httpx`'s own parameters (which also stopped IDNA2003 conflating
  `strasse.example` with `straße.example`), and the slash fold is scheme-aware,
  because no single slash rule is correct for both `https:` and `file:`.
  **Treat "merge-only" as a tested property, never as a structural guarantee**
  — three consecutive hand-written repairs introduced the failure class they
  were closing, so `tests/test_research_origins.py` now carries the reviewers'
  own instrument: a deterministic generator over mechanical URL spellings
  asserting every one agrees with the spelling `httpx` itself emits for it,
  which on its first run found three splits no review round had seen
  (percent-encoded hosts, percent-encoded NFD bytes, leading-zero ports).
  Extend the generator before extending the canonicaliser. Two splits are deliberate and
  documented as correct: `;` versus `&` in a query is not variation a fetcher
  produces, and two punycode labels that decode to different strings are
  different hosts. A blank or unresolvable `source_id` returns `None` and falls
  to `unknown:research:<project>`, the bucket that counts once and fires no
  gate. Both shapes stay machine-sliceable through `is_researched_origin`, so a
  measurement pooling manufactured origins with observed ones does it on
  purpose — the "no writer yet" note here was stale and was corrected
  2026-07-28. **No *capture* response echoes it**: it is absent from
  `MemoryResponse`, so on the capture doors it is write-only over the wire and
  a test asserting it through a capture door's response will assert nothing.
  That is a statement about those doors, not about observability — two other
  read surfaces serve resolved keys on purpose: `GET
  /api/v1/knowledge/facts/{id}` (`FactSourceGroup.origin_key`, the
  corroboration audit) and `GET /events` (`checkpoint_saved` payloads). Saying
  "only a direct database read can observe it" was wrong and was corrected
  2026-08-10. **The capture-door claim is also not tree-wide, and
  this said "any door" from `ad19c53a` until it was corrected 2026-08-10**:
  `session_checkpoints` carries its own `origin_key` and `CheckpointResponse`
  serves it on both verbs of both doors. The difference is what the key is
  *for* — counting corroboration-independence on the capture side, where
  observing another run's key is the hazard; a lookup key on the checkpoint
  side, where a caller is only ever handed back the row it fetched under its
  own declared identity.
- `updated_at` is bumped by the **`touch_updated_at` SQL trigger**, not by
  SQLAlchemy's client-side `onupdate`: a raw-SQL UPDATE must move it too.
- `technologies` (lowercase Text[]) — denormalised cache of entity names
  whose `entity_type` is in `TECH_TYPES`. The supersession detector and
  the retrieval filter both consult this column instead of joining.
- `confidence` (REAL, default 0.75) — content-quality estimate; used by
  `_apply_rank_fusion_factor` when `confidence_rank_gamma > 0`.

Entities and relations live in `entities` / `entity_relations` and are
**not memory-scoped**: each row carries a `memory_ids` UUID[] of every
memory that asserts it. Uniqueness is `(entities.name, entity_type)` and
`(entity_relations.source_entity_id, target_entity_id, rel_type)`.
Creating an entity or relation that already exists must append the new
memory to `memory_ids`, not insert a duplicate row.

## Taxonomy is closed

`ENTITY_TYPES` and `RELATIONSHIP_TYPES` in `app/taxonomy.py` are the
**only** values stored. The LLM may emit anything; everything must pass
through `normalize_entity_type` / `normalize_relation_type` first.
Unknown entity types fall back to `concept`; unknown relations fall
back to `RELATED_TO`. `LEGACY_*_TYPE_MAP` rewrites historical names
(e.g. `framework → tool`, `RUNS_ON → DEPLOYED_ON`) at runtime so old
rows keep matching new code. Adding a type means editing those tables;
relying on a free-form value will silently get rewritten.

## Capture is buffered (`memory_buffer`, doc 05 §2)

All four capture doors — REST `POST /memories` (+`/batch`) and MCP
`memory_add` / `memory_batch_add` — validate, resolve `source` and
`origin_key`, enqueue a `memory_buffer` row and return **202** with a
`CaptureAck`. The ack's id is the **pre-minted memory id**, which rides
the buffer row's `metadata_`; the buffer row's own id is a separate
tracking handle — never conflate the two. `wait_process=true` is the
opt-in synchronous escape: it drives that row's flush inline through the
same `FOR UPDATE SKIP LOCKED` claim the scheduled job uses and returns
the processed memory (201), bounded by `buffer_wait_timeout_seconds`
before degrading to the plain ack. The `buffer_flush` job drains the
queue; its four thresholds (`buffer_claim_batch`, `buffer_max_attempts`,
`buffer_claim_visibility_seconds`, `buffer_done_retention_hours`) are the
job's `config_schema`, persisted in the `config` row `job:buffer_flush`.
A batch that fails to materialize retries row-at-a-time so the poisonous
row settles alone into `error` with a `last_error` naming the real
failure; a flush overrunning its deadline returns the batch to `pending`
with the attempt refunded and shrinks the next claim. `error` rows are
retained until resolved (the sweep deletes only `done`) and are triaged
over `GET /api/v1/memory-buffer` (REST single-door; requeue resets
attempts and journals `buffer_requeued`, discard journals
`buffer_discarded`). The claim SQL bounds its batch with a
`WITH ... AS MATERIALIZED` CTE — a plain sub-select lets the planner
re-execute it per outer row and claim the entire backlog, ignoring the
`LIMIT`; do not "simplify" it.

## Pipeline phases (`ProcessingPipeline.process_batch`)

A batch flows through five phases. Each phase is a hard checkpoint:

1. **Content embed.** All contents in one chunked call to the embedder.
   Returns `(vectors, fingerprint)`. Failure marks every memory's
   `embed=error` and skips writes. Fingerprint is registered exactly
   once (`_register_fingerprint`) before any partition write.
2. **Extract + classify.** Per-memory, bounded by `pipeline_concurrency`.
   Classification always runs alongside extraction. The classifier
   instance is chosen per
   batch: if the classification purpose's inline `classifier_kind` is
   `local`, the pipeline swaps in the in-process classifier; otherwise it
   uses the LLM-backed one. (`ml_profiles` and the `*_ref` indirection were
   dropped in the baseline; wiring the dispatch to read `classifier_kind`
   is T1.04's.) The two implementations share the same surface
   (`classify(content, areas, prompt, mode) → {hall, summary, emotions, flags}`).
   **Single-call merge:** when the classifier is the LLM-backed one
   (`classifier_kind` not `local`) AND `classification_mode == 'simple'`, the
   pipeline folds classification into the one extraction call
   (`extract(..., with_classification=True)`) instead of a second LLM
   round-trip — the merged schema adds `summary`/`emotions`/`flags`, and
   extraction's `memory_type` (already the simple-7 vocabulary) doubles
   as the classification label written to `classified_type`. Any
   other config (an ML classifier, or an area-grained non-simple mode
   whose larger label space the extraction schema does not carry) keeps
   the two concurrent calls. Because the gate changes the extraction
   prompt, re-extracting the same content under a different gate state
   (mode flip, `classifier_kind` set/cleared) is not bit-identical even
   with the same content seed.
3. **Entity embed with cache.** Lookup `(name_lower, fingerprint)` in
   memory cache, fall back to DB cache, fall back to embedding the
   misses. Newly produced embeddings are written to both. The fingerprint
   may change between Phase 1 and Phase 3 if the active embedder rotated;
   in that case Phase 3 registers and switches to the new fingerprint.
4. **Dedup.** One ANN probe per unique `(name, entity_type)` pair —
   `find_similar_entity` is type-constrained at threshold 0.85, so
   same-named entities of different types dedup separately. A match
   only canonicalizes when `names_distinct(lower_name, match)` is
   False: names that differ by a discriminating token (numbers, dates,
   versions, month names) never merge despite high cosine similarity.
   Record `(name_lower, entity_type) → canonical_name` in
   `canonical_map`; Phase 5 resolves relation endpoints by the same
   key. Probes fan out bounded by `pipeline_concurrency`.
5. **Write.** Per memory, in two savepoints — A: vector upsert +
   memory-row enrichment; B: entity/relationship graph + technologies
   + supersession — so a graph failure does not roll back the vector
   write:
   - Strip prior contributions of this `memory_id` from the graph
     (`delete_by_memory_id`) before writing the new set, **inside
     savepoint B** (T1.21, 2026-07-28). The strip and the write are one
     atomic replace: a savepoint-B failure rolls the strip back so the
     prior graph survives, and an extraction failure never enters B so
     the strip never runs. Running it outside the savepoints — which is
     what doc 05 §8's flowchart used to show — silently left a memory
     with **no** graph on either path. A failed strip fails savepoint B;
     it must never be swallowed and written over. This is what
     makes re-extraction idempotent. `delete_by_memory_id` deletes a
     relation only when no live memory still asserts it (self-healing
     dangling `memory_ids`), and an entity only when no live memory
     asserts it and no surviving relation references it (the FK
     cascades, so deleting a referenced entity would destroy another
     memory's edge). Entities shared with other live memories survive.
     The hourly `graph_orphan_cleanup` job runs the unscoped sweep
     (`prune_orphan_entities`) as a backstop so Phase-4 dedup never
     merges fresh entities onto stale ghosts.
   - Apply `canonical_map` to entity names and relationship endpoints.
   - Lowercase entity names on write; if the original casing differs,
     stash it in `properties.display_name` so the UI can render it back.
   - Write rows; recompute `memories.technologies` from entities whose
     type is in `TECH_TYPES`; run supersession.
   - Compute crossrefs in a separate session after the main commit.

After Phase 5, `derive_memory_failed_step` records or resolves a row in
`pipeline_failures` per memory. The websocket broadcasts
`pipeline.completed | partial | failed` based on the per-step status.

## Pipeline terminology — never conflate

- **Extraction** builds the entity/relationship graph and is always on.
- **Classification / enrichment** populates the `llm_*` columns and also
  always runs. There is no longer a regex classifier or an
  `llm_enrichment_enabled` gate; the only choice is which model-backed
  classifier serves the `classification` purpose (LLM by default, or the
  in-process classifier when `classifier_kind` is `local`).

The **only** surviving ingestion-side behavioral flag is `relation_rescue`
(pattern-based rescue layer for relations the LLM misses); retrieval has
its own flags (see Feature flags). All `ml_*` flags were removed in the
2026-05-01 LLM-only consolidation; do not reintroduce a generic ML on/off
switch, and do not reintroduce a classification on/off flag.

## Supersession (`detect_supersessions`)

Triggered inside Phase 5 when the new memory carries a relation in the
**`REPLACES` family** — `REPLACES`, `IMPROVES_ON`, or the legacy
`BUILDS_ON` — not the literal `REPLACES` alone (T1.36, 2026-07-28). The
predicate is **one shared function**, `supersession.is_supersession_trigger`,
which `pipeline.py` imports (corrected 2026-08-08 — this said the predicate
lived in both files and had to change together, which was true when written
and describes a drift hazard that has since been engineered out). Narrowing
it is still a silent behaviour change rather than a cleanup; there is now
just one place to narrow. A candidate is flipped to `superseded` only if
**all** hold:

1. Same `project` as the new memory.
2. Candidate `status = 'active'`.
3. `candidate.technologies` overlaps the lowercased `REPLACES` targets
   (the GIN index on `memories.technologies` carries this).
4. `candidate.created_at >= now - SUPERSESSION_WINDOW_DAYS` (90 days).
5. Candidate is older, with an id tie-break for equal timestamps:
   `created_at < new.created_at OR (created_at = new.created_at AND
   id < new.id)`. Same-batch rows share one server-side `created_at`,
   so the tie-break lets within-batch supersession fire while still
   blocking the mutual flip (without this guard a reprocess flips two
   same-relation memories into mutual supersession; both vanish from
   the default `active` view).
6. The speculative gate, scoped per target: only the sentences
   mentioning that `REPLACES` target are checked for
   `SPECULATIVE_REPLACES_MARKERS` ("might", "considering", "planning
   to switch", ...), falling back to the whole text only when no
   sentence mentions the target — an unrelated speculative aside
   elsewhere in the memory does not suppress a definitive replacement.
   This is the per-relation confidence gate until the extractor emits
   a numeric one.

The detector lowercases REPLACES targets because `memories.technologies`
is lowercase; do not change either side without the other.

## Embedders are partitioned by fingerprint

Pgvector requires a fixed-dim `vector(N)` column, so every fingerprint
gets its own child table:
`memory_embeddings__<slug>`, `entity_embeddings__<slug>`,
`code_chunk_embeddings__<slug>`, `entity_embedding_cache__<slug>`.
The `embedders` table is the registry; `embedder_registry.register`
inserts the row and runs the four `CREATE TABLE IF NOT EXISTS` once,
idempotently. Application code never names a child table directly —
always go through `child_table(parent, fingerprint)`. A query that
joins across fingerprints is a bug; cross-fingerprint comparisons
have no defined cosine distance.

`_register_fingerprint` must be called before any insert into a
partition. Phase 1 does this for the content fingerprint; Phase 3 does
it again if the active embedder rotated mid-batch.

## Retrieval

Default semantic search delegates to `HybridSearchService.search` when
`hybrid_search_enabled`:

- Semantic side: `1 - (embedding <=> :vec)` against the per-fingerprint
  `memory_embeddings__<slug>` table.
- Keyword side: `ts_rank` against `memories.search_vector` with
  `plainto_tsquery('english', :q)`.
- Fusion: Reciprocal Rank Fusion with `k = 60`, weighted by
  `semantic_weight` (default 0.7). Output rows carry `rrf_score` as
  the ordering signal; the per-modality `score` key survives on the
  row (the first-seen side's raw score), so consumers must prefer
  `rrf_score`.
- When `reranker_enabled`, `RerankerService` LLM-scores the top 40
  RRF-ranked rows (0–10; the unscored tail is appended) after fusion.
- If `confidence_rank_gamma > 0`, weighting multiplies `rrf_score` by
  `(1 + γ·(confidence - 0.75))`; after a rerank it runs with
  `preserve_order=True`, rescaling scores without reordering.

Code search (`CodeQueryService.search_code`) **does** fuse, contrary to
what this file said until 2026-07-28: a vector arm over
`code_chunk_embeddings__<slug>` and an `ILIKE` arm over `CodeSymbol.name`
/ `source_code`, combined under RRF. What it has no FTS column for is a
`ts_rank` arm — the partitions carry none — so the keyword side is
`ILIKE`, not Postgres full-text. `code_query.py` **imports** `RRF_K` from
`app/services/rank_fusion.py` since T2.58 (2026-08-04) — it used to
declare its own copy, and this file used to say no task owned closing
that. Two AST scans now fail the build on a second RRF constant
*declared* anywhere outside `rank_fusion.py`; they check the binding, not
the literal 60, so renaming the value does not evade them. MCP's
`code_search` and `code_blast_radius` route through this service
(T1.42c); before that they held parallel implementations and had already
diverged.

**Chat retrieval is the same path, not a third one.** `ChatService` used
to call `vector_repo.search` directly — semantic-only, no keyword arm, no
RRF, no trace — so a chat answer and the search surface could rank one
corpus differently. Since T2.58 it goes through
`LayerCompositionService.search`, whose memory channel is
`HybridSearchService.search_with_trace`, and `ChatService` holds no vector
repository at all. **Ranking parity between the two doors is asserted on
order, not on shape** (`tests/test_chat_retrieval_parity.py`): a
shape-comparison test passes while orders diverge, which is why the
assertion is written the way it is. Note parity is only proven while every
rank arm sits at weight 0 — the doors weight `confidence_rank_gamma` on
different bases, so activating an arm obliges re-measuring both.

## Feature flags

Source of truth: `config` table row with key `feature_flags`. At read
time `get_feature_flags_dict` merges DB values **over**
`FEATURE_FLAGS_DEFAULTS` from `app/config.py`, so a flag absent from
the DB row falls back to its default. The pipeline reads the merged
dict through a 5-second TTL single-flight cache (`_get_feature_flags_cached`)
so per-call dispatching does not hammer the DB; concurrent refreshers
share one task. `_flag_cache_reset` is a test hook only.

Current behavioral flags (the rest govern concurrency or thresholds):
`hybrid_search_enabled`, `reranker_enabled`, `relation_rescue`,
`confidence_rank_gamma`. The graph arms landed inert with T2.32 —
`ppr_enabled` / `dual_level_enabled` / `community_injection_enabled` off,
`w_ppr` / `w_dual` at 0. `w_ppr` and `w_dual` are RRF **list** weights
(`rank_fusion.LIST_WEIGHT_KEYS`), never `RankArm` multipliers, and both
doors derive the PPR weight through `rank_fusion.ppr_list_weight` so a
half-flipped config cannot mean one thing to chat and another to search.
The dual-level channel itself is T2.49's; only its flag exists today. The ranking arms `w_importance` / `w_heat` /
`w_recency` / `w_context_boost` exist at weight 0 and are provably inert
there (`rank_fusion.RANK_ARMS`); each flips only on a measured retrieval
win reported with its latency/cost twin, recorded in the gate ledger's
arm activation log — never by intuition.

## LLM configuration

Eight purposes, and **all eight are live** (corrected 2026-08-27): `embedding`,
`extraction`, `classification`, `reasoning`, `summarization`, `reranker`,
`verification` — which `app/services/verification_judge.py` resolves and
dispatches on since T2.26 — and `synthesis`, which
`app/services/article_synthesis.py` dispatches on through its
`SYNTHESIS_PURPOSE` constant since T3.02 shipped. This paragraph read "Seven
are live … only `synthesis` is still seeded inert (first consumer T3.02)"
after T3.02 had already landed, which is the same stale-count shape as the
job roster and the dream-job family above: a reader planning work would have
believed activating that purpose was still an unmade decision, and gone
looking for code that already exists. It described *both* Tier-C rows as
inert until 2026-08-02, when the `verification` half was corrected.
Note `verification` being dispatched is not the same as it being *usable*:
`VerificationJudge.judge()` refuses unconditionally without a qualification
record, which only a cleared gate run mints and which is behind T2.54's gold.
**Since T2.117 (doc 17 §6 amended 2026-08-12, owner-ratified) there is one
record per consumer *role* over one judge identity, and `judge()` takes a
keyword-only `role`** — `entailment` for the article claim pass, gated on
`entailed_precision`/`entailed_recall`; `contradiction` for the Tier-C scan,
gated on the contradiction pair. `JUDGE_ROLES` partitions `BAR_METRICS` and a
test fails the build if it stops doing so; a record carries the role it was
minted for, so copying one onto the other's path qualifies nothing, and a
pre-split bundled record (no role field) qualifies **neither**. **The entailment
record is MINTED and on master since 2026-08-17** (corrected the same day — this
said both records were absent, which stopped being true when T2.124's fresh gold
and T2.125's run merged). It qualifies judge identity `fd39e7b2c47fa375`
(`gpt-5.5`) on precision 0.9906/0.95 and recall 0.9545/0.90 with
`contradicted → entailed` at 0, and **G-D is CLEARED on that role alone** by the
owner's 2026-08-17 ruling. The **contradiction role is still absent and still
missed** — recall 0.7875 against an unmoved 0.95, the fourth miss across two
vendors — so no consumer may ship on its verdicts. Two limits ride with the mint
and are easy to lose: the judge had already met **114 of the 280** measured pairs
in two earlier blind sittings on that gold and all three pairs it was known to
disagree with were retired before the run (worst-case restoration still clears at
recall 105/113 = 0.9292, so no verdict moves — but "cleared on pairs it had never
seen" is not a sentence anyone may write); and **a minted record is not a served
label** — `judge()` resolves the `verification` purpose from the *database*, so
the row must exist there at the qualified identity, and `llm_seed.py` seeds that
purpose at a local Ollama model instead. Two tripwires are
tests rather than prose: relaxing a contradiction-role bar, and any
qualification contact with pair set `4975c5cc` **for any role** (refused at the
harness before a model call, at the writer, and at the app-side reader). The
cost the amendment names and this file repeats because it is easy to miss:
"articles may ship" no longer implies "a qualified contradiction judge exists".
T2.109 put the judge behind a fourth bar: `BAR_METRICS` gates `contradiction_recall`, and that bar was
deliberately left with no default so `get_verification_bars` would raise and
`qualification_state` fail closed until someone wrote the number down —
stating it alongside the amendment would have meant choosing it while looking
at both measured judges' public results, which is the fitting doc 17 §6
forbids. **The number has since been stated: `contradiction_recall_bar` = 0.95
and `contradiction_precision_bar` = 0.95 → 0.70, both by derivation from doc 17
§6's own rule, recorded in the gate ledger's "G-D redesign" section and in
`VERIFICATION_BAR_DEFAULTS`** (corrected 2026-08-08 — this paragraph said the
bar was unstated and the gate fails closed on it, which stopped being true when
`bb522848` landed the value and left `BAR_METRICS`' own comment behind saying
the same thing). The check that the 0.95 is a derivation and not a fit is that
the measured judge does **not** clear it: gpt-5.5 scored 0.945, so a laundered
bar would sit at 0.90, and a test pins it against exactly that. Both bars are
the owner's to move with a recorded argument; neither may be moved to make a
run pass. **Since T2.126 (doc 17 §6 amended 2026-08-13, owner-ruled) that rule
holds at runtime too, not only in source**: all four shipped defaults are
**floors**, on the verification ladder's shape. Tightening is free; a `config`
row below a floor clamps back with a warning unless the
`verification_bar_licences` row names that parameter, states the lowest value
its recorded argument supports and cites where that argument lives — a licence
bounds one loosening rather than blessing whatever the bar row says, which is
what stops it being the bar row licensing itself. An *unreadable* bar row still
raises and fails the role closed; the clamp is for readable-but-lower ones. No
bar value moved. The limit is stated rather than claimed away: an operator who
writes both rows is stopped by nothing in-process — `ladder_measurements` has
the same limit — what changes is that a loosening is no longer a single number
edit with no trace. Note the qualification *runner* stamps
`VERIFICATION_BAR_DEFAULTS` directly and was never on the config surface, and
G-C's `scripts/benchlib/promotion_bars.py` inherited the pre-clamp posture
verbatim **until T2.127 closed it on 2026-08-13** (doc 17 §6 amended, owner-ruled)
— same licence shape under the key `promotion_bar_licences`, but the conservative
direction is carried **per bar** there, because G-C's six do not share one:
`verification_false_promotion_bar` (scored with a strict `<`) is a **ceiling**
whose laundering move is *upward*, and a direction-blind clamp would have read
its abuse as a tightening. **`promotion_rate_min_eligible` has no conservative
direction at all** — higher is stricter at its own comparison site, but its
negation is the domain of the composed "every powered bucket must clear the
floor" rule, so raising it silences buckets and can flip a failing axis to
cleared; it takes a licence in **either** direction. Two limits worth knowing
before quoting that module as G-C's floor: `promotion_journal_completeness_bar`
is read by no predicate, so its clamp is prophylactic rather than live; and the
clamp used to be **invisible** in the artifact the ledger quotes — it spoke only
through `logging`, so a clamped run's report body was byte-identical to an
unclamped one. **T2.128 closed that on 2026-08-13**: resolution returns a
`BarReport`, `resolve_promotion_bars` is derived from it so the printed numbers
and the verdict's numbers cannot be two resolutions, and every run that resolves
bars prints per bar the committed value, the effective value and which of *no
config row* / *honoured* / *CLAMPED* happened — a run with no rows saying so in
words, because "silent" must not render like "clean".

Each purpose is **one `llm_purpose_configs` row naming a shared
`llm_providers` row** through a NOT NULL `provider_name` foreign key. The
purpose row carries only what varies per purpose — `{model, params,
dimensions?, reasoning?}`, plus `classifier_kind` on classification — and
the provider row carries the connection, `{api_kind, base_url, api_key}`.
Resolution is **one query with one join** and returns the same **flat**
`LLMPurposeConfig` it always did. That flatness is a correctness
requirement, not a style preference: `benchlib/caching_llm.py`'s cache key
and `verification_judge.py`'s identity hash both fold the same six field
*names* off the resolved object, so a nested provider or a renamed field
would miss every cache entry on every machine (G-C's clear rests on an
independent party reproducing a run byte-identically at 0 live calls) and
would move the qualified judge identity. `tests/test_llm_config.py`
asserts the one-query-one-join property with a query-counting test.

**The provider layer was reinstated by the owner's ruling of 2026-08-20**
(`docs/superpowers/specs/2026-08-20-llm-providers-design.md`), reversing
doc 04 §7 and doc 19 §3 — which are amended, not deleted, because their
"darkmem is not an LLM proxy" argument is still why the *resolved object*
stayed flat. The reversal rests on one requirement the flat shape cannot
meet: a credential rotation or endpoint move must reach every purpose that
uses it with no re-apply step, and a live reference is the only thing that
does that. `llm_profiles` and `ml_profiles` stay dropped along with every
`*_id` column; the classification purpose keeps its inline
`classifier_kind` (`llm` | `local`) where it used to reference a profile.
The eight purpose rows **and the two provider rows** are written by the
setup wizard's finalize step from `app/services/llm_seed.py`, never by a
migration.

**The provider serving `verification` is the one exception to that
propagation, and the freeze is field-scoped, not row-scoped.**
`app/services/llm_provider_guard.py` refuses a `PUT` that changes
`base_url` or `api_kind` on it: two of the judge's six `IDENTITY_FIELDS`
moved onto the provider row, and repointing that identity from a settings
form is exactly the capability T2.106 refused on the purpose door. The
read side already fails closed, so the damage would not be wrong verdicts
— it is G-D's clear silently evaporating on an unrelated settings edit,
and the entailment record minted 2026-08-17 is expensive to re-mint.
**`api_key` on that provider still rotates, and rotating it is owed.** The
key is deliberately absent from `IDENTITY_FIELDS` ("rotating a credential
is not a model swap"), so freezing it would protect nothing while blocking
the rotation the "Live model endpoints" ruling below says is still the only
thing that retires the leaked judge key. A reader who takes away only "the
judge's provider is frozen" will skip a rotation that is both permitted and
due. Exclusivity is a **default with a remedy**, not an enforced invariant:
the seed and the wizard give `verification` its own provider
(`verification-judge`), the purpose write path refuses to point another
purpose at a provider that serves it, and where a restore has already
shared one, the escape runs the other way — repoint the *other* purposes
off it, which stays permitted.

**A deploy across this change cannot use the runbook's plain restore.** An
old-schema `llm_purpose_configs` dump carries columns the new table does
not have, and stripping them still violates the NOT NULL FK against a
recreated database holding zero provider rows.
`backend/scripts/cutover/llm_providers_transition.py` transforms such a
dump into provider rows plus purpose rows that reference them, splitting
`verification` onto its own provider; `docs/runbook-deployment.md` carries
the procedure.

`api_kind` selects the wire protocol and is the only place vendor
quirks live: `openai` (compat path), `ollama` (native, exposes
`think:false`), and reserved slots for `anthropic`, `google`, `deepseek`,
`zai` that today still dispatch through the OpenAI-compat path. Every
quirk — auth scheme, reasoning-disable knob, structured-output and seed
acceptance, embeddings capability, output-cap key, model-probe endpoint —
is **one `VendorQuirks` row in `app/services/llm_quirks.py`**, which the
orchestrator, the health check and the setup wizard's probe all read; no
call site may compare `api_kind` to a vendor name, and a test fails the
build if one does. Adding a vendor is the four-step rule in doc 11 §4:
enum, quirk row, doc table, seed. Some vendors (Anthropic, DeepSeek
today) lack embeddings; the runtime guard against an embed call landing
on a no-embeddings vendor is the `api_kind`-keyed `assert_can_embed`
(reached via `LLMOrchestrator._assert_can_embed`), and the settings
picker derives its cannot-embed hint from `api_kind` the same way.
Anthropic needs `x-api-key` + `anthropic-version` rather than Bearer;
DeepSeek and z.ai need `thinking:{type:disabled}`; Gemini's compat shim
honours only `reasoning_effort=none`; and `minimal` is no longer in
OpenAI's effort set, so a config carrying it fails loud instead of 400ing
at the vendor.

LLM seeds for the eight purposes and the two provider rows
(`DEFAULT_PROVIDER_ROWS`) live in `app/services/llm_seed.py`, not in any
migration. The setup wizard finalize step writes the provider rows first,
then seed-plus-overlay into the purpose rows. `DEFAULT_PROVIDERS` beside
them is a vendor *catalogue* keyed by `api_kind` and is written to no
table; conflating the two flips a fresh install's wire protocol, because
its `ollama` entry is `api_kind='ollama'` while every seeded purpose
resolves `api_kind='openai'` against a `/v1`-suffixed URL.

## Reproducibility

Extraction and classification calls forward `seed = sha256(content)[:8]`
as a 32-bit int so the same input produces the same JSON across calls.
Vendors that honour the parameter (OpenAI, DeepSeek, z.ai, Google compat,
Ollama) do; Anthropic ignores it, which is harmless. Removing the seed
forwarding will unstick reproducibility tests and make extraction E2E
flaky.

## Jobs (`JobRegistry`)

Periodic work is unified under `JobRegistry` and dispatched by cron
expressions. **Twenty-four** registered jobs (`app/main.py`) in two groups
(count corrected 2026-09-02: increment 6's `backup_ship` moved the prior
**Twenty-three** up by one; that count had itself been corrected
2026-08-29, when the per-repo indexing modes epic retired the
standalone `code_reconcile` job and dropped a **Twenty-four** by one.
That count had in turn been corrected 2026-08-07, when it read
"Sixteen" / "ten live ones" since T2.49 landed `relation_embedding_refresh`
without updating it, and four concurrent lanes each found it stale
independently — a stale count on a "here is the full list" sentence is
exactly invariant 23's concern. `tests/test_code_deriver.py` now derives the
roster from `app/main.py`'s AST, so the next job added cannot silently
desynchronise this list).
The eighteen live ones: `repo_sync`,
`buffer_flush`, `code_enrichment`, `code_deriver`,
`token_blocklist_cleanup`, `pipeline_failure_cleanup`,
`graph_orphan_cleanup`, `tag_orphan_cleanup`,
`expired_memory_cleanup`, `ppr_snapshot`,
`relation_embedding_refresh`, `repo_entity_anchoring`,
`repo_entity_merge`, `citation_reverify`, `job_run_cleanup`,
`block_embedding_refresh`, `llm_usage_cleanup`, `backup_ship`. **`code_reconcile`'s
standalone working-tree drift scan is retired; the same scan now runs
inside `repo_sync`, per repo, gated on that repo's own
`index_on_commit_enabled` switch and its `index_uncommitted` switch
both: the scan only widens the check the commit-poll tick already runs,
so it does nothing while `index_on_commit_enabled` is off** — see Code
indexing below. Note
`buffer_flush`, `code_deriver`, `ppr_snapshot`,
`relation_embedding_refresh`, `repo_entity_anchoring`,
`repo_entity_merge`, `citation_reverify`, `job_run_cleanup`,
`block_embedding_refresh`, `llm_usage_cleanup` and `backup_ship`
register via the constants `BUFFER_FLUSH_JOB_KEY`,
`CODE_DERIVER_JOB_KEY`, `PPR_SNAPSHOT_JOB_KEY`,
`RELATION_EMBEDDING_JOB_KEY`, `REPO_ENTITY_ANCHORING_JOB_KEY`,
`REPO_ENTITY_MERGE_JOB_KEY`, `CITATION_REVERIFY_JOB_KEY`,
`JOB_RUN_CLEANUP_JOB_KEY`, `BLOCK_EMBEDDING_JOB_KEY`,
`LLM_USAGE_CLEANUP_JOB_KEY` and `BACKUP_SHIP_JOB_KEY` rather
than string literals, so a grep for quoted keys undercounts the list —
which is precisely how this sentence went stale for four landings.
**`llm_usage_cleanup` prunes by age where `job_run_cleanup` beside it
prunes by row count**, and the difference is deliberate: `llm_usage`
exists to answer "what did the last N days cost", so a row ceiling would
shorten that answer during exactly the busy period worth investigating.
The accepted cost is that a burst inside the window is unbounded on disk.

**`backup_ship` is the off-host path, and it is the *second* producer, not
the only one** (increment 6, spec §9.3-9.4). It runs the image's own
`pg_dump` over the stack network — it cannot call `scripts/backup.sh`, which
is why the runtime stage installs `postgresql-client`, `age`,
`openssh-client` and `rsync` — encrypts with each destination's `age`
recipient, ships, **reads every upload back and hashes it**, and prunes per
destination. The host-side `darkmem-backup.timer` stays exactly as it is: a
backup system that depends on the service it protects is not one, so the
timer is the floor that survives the app being down. **Nothing serialises
the two** — different processes, and the per-job `asyncio.Lock` binds
in-process only — so the separation is a directory (`/srv/darkmem-dumps`
versus `/root/darkmem-backups`), a filename prefix (`darkmem-app-` versus
`darkmem-`) and an hour of cron (04:30 versus 03:30). Note `backup.sh`'s own
retention glob `darkmem-*.sql.gz` **would** match this producer's files, so
the two must never be pointed at one directory; the job's prune matches only
its own prefix and never a `.part`, so it cannot delete a systemd dump even
where an operator has done exactly that. Destinations and their secrets live
in the `config` row `backup_destinations`, never in the job's
`config_schema` (`FieldDescriptor.default` is typed `int`).
**Size the retention against a ~250 MB dump, not the ~3 MB one this repo's
history shows** (measured 2026-09-02): `block_embedding_refresh` filled
`block_embeddings__qwen3_embedding_0_6b_1024` to 665 MB of a 710 MB database,
so a dump went from 2.8 MB to 252 MB inside one day and both producers' `14`
was chosen when the artefact was 90x smaller. A **`local` destination is the
one kind that double-counts**: it writes to the same disk the systemd floor
already keeps 14 copies on, and it ships nowhere, so this host runs it at
`retention_keep=3` while `BACKUP_KEEP` stays 14. Note what that means today:
**no configured destination takes data off this host** — the off-host path
exists and is exercised, but arming it is configuring an `ssh`, `s3` or
`worker` destination on the Backups tab. **The `age`
identity is never stored in this database**: a snapshot carrying its own
decryption key is not encrypted at rest, so only the public recipient is
configurable and decryption happens where the operator's identity file
lives.
**`ppr_snapshot`, `relation_embedding_refresh`, `repo_entity_anchoring`,
`repo_entity_merge`, `code_deriver`, `citation_reverify` and
`block_embedding_refresh` are Tier C but are deliberately not dream-job
family members** (T2.32, T2.49, T2.97, T2.101, T2.96, T2.48,
T-doc-door.6): contract 6 fixes that family as
the consolidation passes, while doc 07 §4 and doc 10 §6 own their
artefact refreshes separately (`block_embedding_refresh` is the document
door's own artefact refresh, doc 16 §3). Invariant 15 is unaffected either
way — retrieval reads the cached snapshot and Phase 4 reads the entity
partition, never the job.

**`code_deriver` is the production trigger for
`code_deriver.assert_repo_graph`** (doc 10 §6, T2.96) — T2.27 shipped
that primitive with no caller anywhere in `backend/app`. The job sweeps
every repo with a non-null `last_indexed_commit` on its own hourly cron
and journals a derivation failure under `pipeline_failures` with
`pipeline_name="code_deriver"`, distinct from `"code_index"`, so a
derivation failure never fails an index run. The withdrawal half lives
in `RepoManager.delete`, which calls
`PostgresGraphRepository.strip_repo_assertions` before removing the
repository row — `entities.repo_ids[]` / `entity_relations.repo_ids[]`
carry no foreign key to `repositories`, so without it an entity's
`repo_ids` keeps a dangling id after the repo is gone.

**`citation_reverify` is doc 10 §6's second sanctioned crossing** (T2.48): it
re-resolves each code citation's recorded `symbol_key` against its repository's
current HEAD, marks a citation that no longer resolves stale, and **enqueues the
citing fact for the verification recompute, which downgrades the badge — never
expiring the fact**, because a deleted symbol may be a rename a human should
confirm. It reads the code graph and writes the memory-side vault, one direction,
no join. Note it does **not** scope by the run's changed-file set at all. Doc 10 §6
named `detail.symbol_key` as the scoping key, which is basis-dependent — a module
name (`httpx`) for an import-basis citation, never a path — so its literal predicate
would have matched only language citations and reported a clean pass; **that defect
was corrected 2026-08-07 (Tier-3, ratified) and §6 now scopes on `detail.file_path`.**
The job itself still scopes differently, and deliberately: it compares a citation's
`detail.reverified_at_sha` against the repository's `last_indexed_commit` —
self-healing where an event-payload design is not, since `record_event` never raises.
The declared cost is that an unchanged file's citation is re-resolved once per HEAD
move rather than never, bounded by citation count, not repository size.

**`repo_entity_anchoring` is what makes the code bridge's anchoring
reach past an exact name match** (T2.97): the deriver is LLM-free by
structural guard, so the embed that lets Phase 4's ANN probe see a
repo-minted entity happens in this job, one tick behind derivation. That
closes **one order only** — repo indexed, anchored, then the memory
ingested.

**`repo_entity_merge` closes the other order, which is the common one**
(T2.101). A repo indexed *after* a memory already minted the near-named
node used to leave two rows forever: Phase 4 dedups at write time,
`assert_from_repo` is an exact-key `ON CONFLICT (name, entity_type)`
upsert with no probe, and the strip-and-rewrite is keyed the same way, so
re-derivation reproduces them. That is what every existing install
produces the first time it indexes a repo. The job re-runs Phase 4's own
comparison after the fact — `find_similar_entity` at the same 0.85 under
the same `names_distinct` gate, with the query vector read out of the
partition rather than re-embedded, so both sides of every cosine come
from one child table and the pass needs no embedder call. **The survivor
is the repo-asserted row**, older `created_at` with an id tie-break when
both are, so the two indexing orders converge on the same node rather
than trading an order-dependent node count for an order-dependent node
name. A merge moves, in one savepoint per pair: the `memory_ids` /
`repo_ids[]` unions, **every** relation endpoint in both directions
(a repointed endpoint colliding with the `(source, target, rel_type)`
uniqueness is a relation merge of its own — union, keep the greater
weight, drop the duplicate — never an error left for the constraint), the
fact layer's identity, and the lowercase `technologies` denorm for
every memory whose entity set changed. The losing row's vectors go with
it through the `entity_embeddings__<slug>` cascade, in every partition.
A relation the repointing missed **fails the savepoint** rather than
being swallowed by that same cascade.

**The fact layer moves by name, not only by id** (T2.101 fix round 1).
`knowledge_triples.subject_id` / `object_id` are entity ids carrying **no**
foreign key, which `review_ranking`'s salience arm reads as zero neighbours
when they dangle — but repointing them is only half the move, because fact
*identity* is name-keyed: the table denormalises both endpoint names and
derives `triple_key` from them, and `compute_triple_key`'s canonicalisation
is lexical, so `postgres` and `postgresql` are two identities. `fact_lift`
groups the graph by live entity name and matches open facts on that name, so
an id-only repoint re-qualifies every already-lifted group as pending and
mints a **second** open triple for one assertion set on the next tick —
corroboration and verification split across two rows. So the names and the
key move with the ids. Recomputing the key can collide with an already-open
row on `ux_knowledge_triples_open`, and **that collision is a fact merge**:
the higher `verification_status` rung keeps the id (`confirmed` >
`disputed` > `corroborated` > `candidate`, ties to the older `created_at`
then the smaller id), which is what lets the fold write **no** verification
column at all — the surviving rung is the one the sanctioned door already
wrote, so no promotion escapes the ladder and no `verified` row appears for
a transition no evidence explains. `fact_sources` is **moved** onto the
keeper (copied, one memory would corroborate one claim twice), serving heat
is summed, the belief window takes the earlier `reference_time` / `valid_at`
and the earlier `stated_expiry`, and the duplicate is **expired, never
deleted** — `article_citations` takes a hard FK on the premise that facts
are invalidate-not-delete, and `expired_at` rather than `invalid_at` is what
keeps the contradiction scan from pairing a fact against itself under its
other name. A fact row whose endpoint id is NULL or already dangling keeps
its name: nothing ties it to the losing row, and the group it came from no
longer exists under the vanished name, so nothing re-lifts it.

The candidate scan **rotates** through the repo-asserted population on a
`(created_at, id)` keyset cursor in the `config` row
`repo_entity_merge_state`, wrapping when a window comes back short —
`candidate_batch` bounds one run's cost, never the coverage. A merge
journals one `merged` `events` row against the surviving entity. The six added by T2.08 are the
**Tier-C dream-job family** (`app/services/dream_jobs.py`, wired at boot
by `register_dream_jobs`): `verification_recompute`, `fact_lift`,
`contradiction_scan`, `memory_dream`, `article_synthesis`,
`topic_detection`. Each is scheduled, locked and configurable for real,
and a member's body is a `PlaceholderJobRunner` until its owning task
lands (T2.09, T2.10, T2.11, T2.12, T3.02, T2.53 respectively) — the
marker is a type a test asserts, not a comment, so a placeholder can
never be mistaken for a shipped job. **Five of the six now have real
runners** (corrected 2026-08-06, when this paragraph's "its body is a
`PlaceholderJobRunner`" had been stale through four landings and read as
a claim that the whole family was inert): `fact_lift`,
`verification_recompute`, `contradiction_scan`, `memory_dream` and
`topic_detection` are live bodies. **All six have shipped and the family
holds no placeholders** — corrected 2026-08-16. This paragraph said
`article_synthesis` was "the one remaining placeholder" whose productive run
was "a Phase-3 task behind G-D", and both halves were false from the day T3.02
landed: `_make_article_runner` is its runner, `SHIPPED_DREAM_JOBS` lists the
key, and `test_the_family_holds_no_placeholders_left` asserts the whole set. It
is the same stale-count shape as the job roster two paragraphs down, and it
cost more than tidiness — the G-E gate's blocker was recorded as "T3.02 is
unshipped", which sent a reader looking for code to write instead of at the
empty corpus that is the real one. **Invariant 15 binds the family: none of the
six may be reached from capture or retrieval** to "accelerate" a gate,
and a source scan over `backend/app` fails the build if one is. Five-field
expressions are minute-precision; six-field expressions put the seconds
field first, Quartz-style. `min_interval_seconds` is a per-job floor
that protects against runaway expressions; the loop will not fire more
often than the floor regardless of what the cron computes. Per-job
state lives in `config` rows keyed `job:<key>`. Manual `trigger(key)`
acquires the **same** per-job `asyncio.Lock` the loop uses, so a
manual run and a scheduled run can never race; a trigger while the
lock is held returns busy (HTTP 409) rather than queueing. Jobs may
declare a `config_schema` (FieldDescriptor list); `set_config`
validates partial updates against it (type + min/max, unknown keys
rejected) and writes under that same lock
(`PUT /api/v1/jobs/{key}/config`).

## Events journal (`events` — `audit_log` is gone)

`events` is the sole, append-only audit substrate; `audit_log` was
dropped at the baseline's genesis and no such table, model or query
exists. Every subsystem journals through one writer, `record_event`
(`app/services/events.py`), which degrades loudly but never raises into
its caller — **and since T2.113 returns whether the row landed**, because
that contract is right for most callers and wrong for a few. A capture must
survive a journal failure; a *verification transition* must not, since doc 17
§5.1's metrics are SQL over this table alone, so a status change whose row never
landed is not a lost log line but a row that silently leaves the measurement's
**denominator** — and under-power announces itself where that does not. **Four**
callers raise `JournalWriteFailed` on a `False`, making the write and its row
atomic (corrected 2026-08-09 — this said "the two callers", which undercounted
from the day T2.113 landed): `set_verification_status` and `ratify` for the
machine's and the human's rungs, and `record_human_verdict` and
`dismiss_contradiction_suspicion` for the adjudication stream. **The human
verdict is the one with no second trace at all.** No column records that a human
rejected a fact, so that event row *is* the audit's `rejected_after` arm — and
since T2.109 moved the LLM scan off the veto, that arm is the scan's only route
into the audit. A loss there does not shrink a denominator, it deletes a
numerator: the gate reads cleaner than the system is. Every other caller ignores
the return and behaves exactly as before.
Making `record_event` itself raise would impose the strict contract on capture,
extraction and auth, which is why it does not. The stated cost: a broken
partition now fails recomputes instead of degrading past them, bounded by
`events_ensure_partition`'s boot and maintenance arms.
`EVENT_TYPES` / `OBJECT_TYPES` are closed vocabularies living
beside the writer, deliberately NOT in `app.taxonomy`: event types are
never LLM output, so an unknown value logs a warning instead of being
rewritten to a fallback. Widening is taxonomy-first — land the value in
the vocabulary before its emitter ships. The table is RANGE-partitioned
by month; every partition-creating path goes through the SQL function
`events_ensure_partition` (boot reconciliation plus a maintenance arm on
`pipeline_failure_cleanup`), and append-only is enforced by three trigger
kinds — a row-level UPDATE/DELETE guard on the parent, a statement-level
TRUNCATE guard on the parent, and a per-child TRUNCATE guard stamped by
`events_ensure_partition`, because statement triggers do not cascade to
children. Readers: `GET /events`, `/events/timeline`, `/events/calendar`
(the calendar bucket expression must match `ix_events_day`'s immutable
UTC expression verbatim), and `GET /auth/audit`, which filters
`auth_*`/`setup_*` rows from the same table. Journal payloads may carry
content previews that **outlive deletion of their memory** — append-only
by design. **The retention policy is settled (T2.59, ruled 2026-08-06):
accept the residue and document it.** Deleting a memory is not a content
purge and the DELETE route says so. The residue is wider than two stores —
full refine summaries in `consolidated`/`undone`, contradiction counterparts
in `verified`, `knowledge_triples.fact` by design, 24h of raw content in
`memory_buffer` done rows, and `messages.context` keeping cited fact rows
untrimmed. The pasted-secret case is answered by an operator break-glass
procedure (`docs/runbook-content-purge.md`), **never an in-app
journal-rewriting path**: that would put "make this never have happened" one
bug away from the audit substrate. The ruling's load-bearing argument is
measured, not aesthetic — the assistant's own unbounded `messages.content`
prose and the storage substrate sit *below* every option considered, so the
alternatives pay permanent costs to narrow a gap none of them closes.
**Write-time minimization is the standing rule**: a new event payload copies
content only when a feature demonstrably needs it, and says so at the writer.

`undone` joined the vocabulary with T2.13, and it is the **first by-id
consumer of `events`** — the composite `PRIMARY KEY (id, created_at)`
means a bare `WHERE id = :id` scans every monthly child, so every undo
lookup carries a `created_at` bound and prunes to one or two of them.
The **dream digest** (`app/services/dream_digest.py`) reads the
`consolidated` stream grouped by `payload.cycle_id`, and within a cycle
by object, in `(created_at, id)` order — journal order is application
order, and regrouping by action kind would describe a cycle that did not
occur. **Undo is all-or-nothing per request and has no per-action code
path**: a single-action undo is a batch of one through
`dream_undo.undo`, whose result types have no field that could carry a
per-item outcome and whose module owns no savepoint, no commit and no
`try` — an AST scan fails the build on all five shapes. That makes the
module unable to self-heal, so it has **three** outcomes, not two: only
`UndoRefused` guarantees nothing was written, and **any other raise
leaves restores in the caller's session for the caller to roll back**.
The HTTP door gets that from the request-scoped session dependency; an
in-process caller does not. **An undo that could not be journalled does
not happen** — `record_event` never raises, so the batch counts its own
`undone` rows back and raises when short. An undone subsumption leaves a
suppression tombstone at
`memories.metadata.dream.undone_subsume.<counterpart_id>`, keyed on both
memories' `content_sha` so it lapses when either text changes; it is
read at **nomination** time by `generate_pairs`, which is not a
lifecycle change — `supersede()` still retires that exact pair for any
caller that asks.

## Verified facts (L2)

`knowledge_triples` is the fact vault, on two independent axes. The
**belief** axis is the validity window (`reference_time` / `valid_at` /
`invalid_at` / `expired_at`) and is invalidate-not-delete —
`article_citations` takes a hard FK on that premise. The **verification**
axis is the ladder `candidate → corroborated → confirmed`, with
`disputed` sideways: `confirmed` is human-only (`ratify` is the one
writer in the tree); the machine's ceiling is `corroborated`.
Corroboration counts `COUNT(DISTINCT origin_key)` over `fact_sources`,
never rows: N = 3, or 2 when two **attributable** origins differ in
source-kind or lie ≥ 7 days apart. Anonymous origins (NULL, blank,
`unknown:*`) fold into one reserved bucket per fact that counts once and
never fires a gate, and a citation `citation_reverify` marked stale is
retained but corroborates nothing (`LIVE_SOURCE_PREDICATE`). The three
thresholds are **floors** (`verification_ladder` config row): tightening
is free; loosening below a floor is honoured only for parameters named in
the `ladder_measurements` config row by a recorded G-C measurement, else
clamped with a warning. **That resolution lives in
`app/services/ladder_config.py`, not in `verification_ladder.py`, and the
split is load-bearing** (2026-08-21): invariant 15's tree-wide scan matches
any line naming the ladder module — prose included — so the settings door
`GET`/`PUT /api/v1/config/verification-ladder` could not have imported the
thresholds from there without an allowlist entry, and an allowlist entry
buys a route the whole module. `verification_ladder` re-exports every moved
name, so existing imports are unaffected, and `ladder_config` is guarded by
the same scan because it is not on the allowlist either. **Resolution
returns a `LadderReport` and `get_ladder_config` is derived from it**, the
`BarReport` discipline T2.128 established for G-C's bars and for the same
reason: a clamp that speaks only through `logging` renders identically to no
clamp, so an operator who types 1 into the settings form is shown 1 and
never learns the ladder is still running at 3. The door answers with the
committed value, the effective value and which of *default* / *honoured* /
*clamped* happened, per parameter. A clamped value is still **written** —
the row is what the operator asked for, so a later `ladder_measurements`
entry licenses the value they already chose. The decision
(`verification_ladder.decide`) is a
pure function; the contradiction veto is absolute — one non-echo
contradiction beats any count, no config on its path.

**The veto stands on ONE instrument, and which one is a ratified design
decision, not an accident of what happens to be wired** (T2.109, doc 08 §4.2
amended 2026-08-08, owner-ratified). The **deterministic scan** is the veto,
and it is judge-free: `adjudicate_contradiction_finding` runs
`CONTRADICTION_DETECTORS` — now a one-member tuple — and the ladder reaches it
on every recompute, so its `inverse_replacement` arm can dispute a fact with no
qualification record anywhere. Whether it *fires* is a property of the corpus,
not the code — it needs a stored REPLACES-family edge, and the measurement
corpus had none, which is what T2.108's vacuity finding actually established.
Its sibling `single_valued` arm is separately disarmed because
`SINGLE_VALUED_RELATIONS` is empty. The **Tier-C LLM `contradiction_scan`** is
**no longer a veto input**: three G-D runs across two vendors measured its
contradiction-precision at 0.7937 / 0.8814 / 0.9020 against a 0.95 bar, so each
false positive behind an unappealable veto was a near-permanent manufactured
dispute. Its journalled verdict now reaches the ladder on a *separate*
parameter (`recompute_fact(..., contradiction_suspected=...)`), lands on
`LadderDecision.contradiction_suspected`, and is read by the fourth review
opener — flagging the fact for a human while it keeps its rung, its badge and
its place in retrieval. Routing that signal into `open_contradiction` restores
the wiring the amendment removed; the two parameters are separate so that
mistake has to be made on purpose. It still dead-ends on the unqualified judge
(T2.54 → T2.41), so today it produces nothing at all. Demotion carries
hysteresis (`verification_demote_grace_cycles`; the `under-sourced` label is
served, never withheld).

**`review_state` has four openers and one derivation.**
`verification_ladder.REVIEW_OPENERS` is the registry — disputed, under-sourced
(hysteresis), contradiction-suspected — plus doc 09's ungrounded articles in a
different table. `derive_review_state` is total and the clear is the absence of
**every** opener, never the negation of one; adding an opener is appending a
predicate, never adding a writer. The queue's *reason* is derived from the
fact's own columns, and **all four openers now have one** (corrected
2026-08-09 — this said a contradiction-suspected fact renders `unspecified`
because the flag was persisted nowhere, which T2.112 closed). The suspicion
rides `contradiction_suspected_at` / `contradiction_counterpart_id`, written by
the ladder in the **same UPDATE** as `verification_status`, exactly as
`demotion_pending_since` does for the under-sourced opener. It is a cache the
authority refreshes every recompute — `detect_scanned_contradiction` re-applies
every guard against live rows each cycle — never a frozen verdict, which is what
keeps the flag self-clearing. `since` is when the flag **opened**, not when it
was last seen. Reading the finding from the queue instead was tried and is
barred: it puts an `app.services.contradiction_veto` import on a read surface,
which invariant 15's source scan fails the build on. A human dismissal journals
`contradiction_dismissed` — its own event type, **not** a fifth
`HUMAN_VERDICTS` value, because those four adjudicate the *fact* and a
dismissal adjudicates the *finding*; recorded as a rejection it would
manufacture a false promotion in doc 17 §5.1's human-rejection arm out of the
scan's own false positive. Clearing the column alone would be undone by the next
recompute, so the journalled dismissal is what makes it stick.

**One journaller for the machine's rungs.** `KnowledgeTripleRepository.set_verification_status`
writes the `verified` events for every transition the ladder makes
(before/after status plus the full decision evidence — `outcome`,
`origin_count`, `required_n`, `gate_fired`, `source_kinds`, the two
blocked flags, T2.64's contradiction counterpart). Ordinary holds journal
nothing; contradiction- and supersession-blocked holds journal. It is
**not** the sole writer of the stream, and this sentence said it was until
2026-08-08: `ratify` is a second, deliberate writer and *cannot* route
through the first, because `set_verification_status` refuses `confirmed` —
the human-only rung is exactly what the machine's journaller must not be
able to write. `promotion_metrics.py` already reads the stream with both
writers in mind; a new consumer that assumes one will misread it.
`_write_born_rung` — the deriver birth **and** the post-dispute restore —
writes `corroborated` with no journal row on doc 10 §6's licence (*the
parse is the verification*); G-C's metrics knowingly exclude those rows,
and the gate ledger says so where the number lives.

**An evidence record gates the label, never the code** (`claim_gates`,
T2.95/T2.100): a promoted fact status reaches a reader only while
`app/services/promotion_metrics_record.json` exists with `gate_eligible`
exactly `true` — minted only by a cleared G-C run, never by hand.
**G-C CLEARED on 2026-08-16 (T2.131) and the record is minted, so promoted and
born fact statuses now reach readers.** This paragraph said the opposite from
T2.111 until that date and the reversal is recent — read it, not a memory of it.
T2.131's authorised run measured the grown corpus (sha `78dbc4c5c8756dcd`, 849
captures) and every pre-stated axis cleared in both passes: **509** in-window
corroborations with a 95% Clopper-Pearson upper bound of **0.009286** against the
0.01 bar on the unsimulated pass that carries the target, **528** and **0.008953**
with the capture clock on, all `gate_fired` buckets powered and clearing, 0
journal-completeness violations over 682 facts, and every bar at its committed
default — no `config` row for any bar and no licence row in either measured
database. An independent party that neither authored the growth nor ran the
passes verdicted it CLEARED after recomputing every axis itself and reproducing
the run byte-identically at 0 live calls, and the gate owner minted
`promotion_metrics_record.json` on that verdict. The runner still never mints it.
**What the clear does not license is part of the result, not a footnote**: every
capture, origin, repo and the single dispute were authored by the measured party,
the deterministic detector has never fired on an unauthored contradiction, the
human-rejection arm has never met a human, the `time_gap` path exists only under
the harness's simulated clock, and the kind diversity carrying 363 of the 509
promotions means one hand wrote the assertion twice in two formats. Two
instrument defects surfaced and are recorded rather than smoothed: the `none` arm
converted **144/145** (basalt's `bs-h3` produced no fact and *no instrument
prints a `none` reconciliation*), and the diversity aggregate counts unauthored
promotions, so authored-claim conversion is **363/365**, not the printed 0.9973 /
1.0000. Numbers, artifacts and the full disclosure are in the gate ledger's
"G-C on the grown corpus" section. **Note `groundedness_gate` is unaffected and
stays closed** — that is G-D's, and no article may be served labelled grounded. It read "not
evaluable: under-powered on every probe — no fact has ever exited `candidate` in
any journal this machine can see" from T2.111 (2026-08-08), and that stopped
being true on **2026-08-13**, when the bench-arm run became the first powered
measurement (31 corroborations, all three `gate_fired` buckets clearing) — and
again on **2026-08-14**, when T2.129 armed the deterministic detector so the
false-promotion audit acquired a numerator at all: 1 disputed over 149 in-window
corroborations. **What replaced vacuity is not a pass.** The point estimate
0.0067 reads under the 0.01 bar, but T2.130 measured what that rule is worth —
comparing a point estimate to the bar it is centred on is a coin flip at the
boundary at *every* sample size (0.56 at n = 149, 0.49 at n = 10 000), so corpus
growth was never the repair and every earlier statement treating the census size
as the limiting factor aimed at the wrong quantity. The exact 95% Clopper-Pearson
upper bound on 1/149 is **0.0314**, over three times the bar, and n = 149 cannot
clear the bound even at zero observed. Three limits belong beside the number
rather than after it: the numerator is **one** fact, the corpus is authored end
to end by the measured party, and the unsimulated pass shows one of the three
gate paths (`time_gap`) exists only under the harness's simulated capture clock —
it does not shrink without the simulation, it disappears. **The scored rule is
now the bound, and the point estimate is context** (T2.132, owner's ruling
2026-08-15 — this paragraph said the switch "is the owner's" and that the
numbers "land beside the existing verdict until then", which stopped being true
the day it was taken). `audit_clears` takes **counts, not a rate**, because
1/149 and 20/2980 are the same 0.0067 and bound to 0.0314 and 0.0097 — opposite
verdicts from one observation. It is a strict tightening, so no bar moved and no
licence is involved; its visible effect is that **the audit axis now reports
`clears=False` where it reported `clears=True`**, retiring a pass this file had
already disowned. Two consequences worth carrying: the corpus-growth targets
T2.131 derives (299 / 473 / the 490 floor) were computed off this bound while
the gate still scored the estimate, so reaching that target and clearing the
audit are now one event rather than two; and `false_promotion_min_corroborations`
= 20 is **subsumed** — nothing clears 0.01 below 299 corroborations at any
observed count — kept for the empty-window guard and for the licensed-ceiling
case, not because it decides anything today. Every figure and its provenance is
in the gate ledger's G-C sections. The bars are stated as
config rows over pinned defaults in `scripts/benchlib/promotion_bars.py`
(committed before the first measurement; the pin test makes moving one a
visible two-file diff), and the metrics are SQL over `events` alone in
`benchlib/promotion_metrics.py`.

**The audit's arms were re-derived, not merely re-run, and the G-C→G-D
cross-edge changed** (T2.111; this paragraph said both arms "dead-end on the
unqualified judge", which stopped being true when T2.109 landed). The audit has
exactly two arms — `disputed_after` and `rejected_after` — and the LLM
`contradiction_scan` **no longer feeds the first at all**: its finding rides
`contradiction_suspected`, which `decide` holds inert by construction, so it can
produce no status transition. That arm is therefore **judge-free**, its only
producer being the deterministic detector, and the 2026-08-07 ruling that
"G-C has G-D's judge qualification on its critical path" (doc 20 §3) no longer
holds as written. The edge does not vanish, it lengthens: the scan reaches the
audit only through `rejected_after`, which needs a human to confirm a flag — so
it is gated on G-D passing *and* on the reviewer surface T2.112 shipped. **The
honest cost, recorded where it will be read:** the amendment bought veto
precision by moving the scan off the veto, and the same move strictly *lowers*
the audit's reach, converting an automatic detection route into a human-gated
one. The audit's precision claim is unaffected; its power is not.

## MCP endpoint

`/mcp` speaks MCP protocol revision `2026-07-28` on SDK `mcp==2.1.1`; the
server object is `MCPServer` (`app.api.mcp.server`), not `FastMCP` — the v2
SDK renamed it. **Every call requires `Authorization: Bearer
dmk_<key_id>_<secret>`** (doc 18 §5's second activation, 2026-08-26); there
is no flag that disables this. Auth is checked before the Host allowlist, so
the two guards can produce different refusals for the same foreign Host: an
unkeyed request gets `401` regardless of `Host`, and only a *keyed* request
that also fails the Host check gets `421`. The allowlist itself is
unchanged and still applies beside auth, not instead of it: localhost is
always allowed; `MCP_ALLOWED_HOSTS` (comma-separated, `192.168.0.195:8000`
or `host:*`) adds LAN hosts; `*` disables the check entirely. Default
(empty) is localhost-only. Fix a LAN 421 by extending the allowlist, never
by disabling either guard. Browser Origins are allowlisted to the same
hosts. `memory_batch_add` mirrors the HTTP 1–100 batch cap.

Authorization is per tool, not per door: `capture` covers the 12 writers
(`memory_add`, `memory_batch_add`, `memory_update`, `memory_delete`,
`document_put`, `document_delete`, `checkpoint_save`, `research_run`, and
increment 8's four block verbs `block_update`, `block_insert`, `block_move`,
`block_delete` — a key that can edit a document's blocks can rewrite its
content, which is `document_put`'s own power);
`read` covers 25; `admin` covers the 1 repository-control tool
(`code_reindex`, the first MCP write door into the code subsystem —
`docs/superpowers/specs/2026-08-28-file-scoped-reindex-design.md` §6.1).
Scopes do not imply one another. `admin` reaches exactly one
tool, `code_reindex` — repository control, not memory writing — so a key
holding only `admin` reaches nothing else, and a `capture` key cannot
trigger an index. `ratify` stays outside the scope vocabulary, unchanged by
this activation: no MCP tool can reach `confirmed` power no matter what a
key holds. `tools/list` is deliberately **not** scope-filtered — any
authenticated key sees the full 38-tool catalogue, including writers it
cannot invoke; that is intended, not an oversight. A keyed capture call
stamps `events.api_key_id` (the key's row UUID) and `events.actor` (the
key's name) on the journaled row.

Memory writes resolve `source` per call: explicit arg (the literal `mcp`
counts as unspecified) > `X-Darkmem-Client` header > User-Agent product
map > `mcp`; `memory_batch_add` resolves on the raw entry dicts before
validation. `source_agent` defaults to the caller's raw User-Agent.

**The F7 research loop's one door is here too, and deliberately not on REST**
(T3.27, doc 09 §6). `research_run` files evidence the *caller* gathered:
`ResearchGatherer` has no in-tree implementation by design, so the door cannot
call a gatherer and the caller has to be one — which is true of an MCP agent
and of neither REST caller (the SPA nor the generated three-verb SDK), where
the honest shape of "research subject S" would be a route that gathers
server-side. A cron is excluded separately: it carries no per-request subject
and `FieldDescriptor.default` is typed `int`, so a `config_schema` cannot
carry one either. The tool takes **no `source`, no `origin_key` and no `ctx`**,
so the header ladder that steers every other MCP capture's identity has no
route into a research run: every row it files carries `RESEARCH_SOURCE` and an
`is_researched_origin` key, and a finding naming either field is a validation
error rather than a silently dropped key. It refuses while the `auto_research`
row is not enabled (the default) — building the door is not arming the loop.
**T3.28 shipped the config and trigger surface, so arming is now a UI act rather
than a manual database write, and production was armed 2026-08-17** on the
owner's ruling, to start the G-E corpus clock. **Armed is still not driving**:
the loop has no `JobRegistry` job on purpose (a cron'd pass would refetch the
same sources every tick, manufacturing its own corroboration), and
`ResearchGatherer` has no in-tree implementation, so the caller must be the
gatherer. Nothing in this tree produces a research origin on its own; an MCP
agent with real web access has to call `research_run`.
`tests/test_auto_research.py`'s blanket invariant-15 scan records this as the
one **sanctioned** crossing through `exempt_node_ids`, scoped to nodes inside
the tool's own body, so the same import at module level or inside `memory_add`
still fails the build.

**Why raw-dict resolution still matters after T1.42a** (updated 2026-07-28).
The original reason — `MemoryCreate` stamping an `api` default that erased
the absent-vs-explicit distinction — is gone: T1.42a removed that default,
so `MemoryCreate.source` has no default and the erasure is no longer
representable. But the discipline is **not** merely historical, and the
doors differ. Restoring the default and resolving post-hoc still *passes*
on REST, where `api` is REST's own sentinel so absent and explicit resolve
identically — and *fails* on MCP with `'api' != 'codex'`, because there
`api` is a foreign literal that dodges MCP's `mcp` sentinel. So the
raw-dict rule has a live, demonstrated justification on the MCP door and a
by-construction one on REST. Do not "simplify" it away on the strength of
the REST case alone.

## Setup, auth, runtime config

- `/api/v1/setup/*` is trust-on-first-use: gated only by
  `require_uninitialized`, which 403s once the `admin_password_hash`
  config row exists. `SETUP_SECRET` no longer exists; do not
  reintroduce a pre-setup shared secret.
- Login rate limiting is per-IP with lockout. The IP source is a posture
  selector and **both postures are live and tested**: with
  `trust_proxy_headers` off (the default) the transport peer wins and no
  request header is read; with it on, `X-Real-IP` wins and the **rightmost**
  `X-Forwarded-For` hop is the fallback. The spoofable **leftmost**
  `X-Forwarded-For` is read in neither. Layer 3 is not the whole ladder:
  uvicorn's own `ProxyHeadersMiddleware` defaults on and would rewrite the
  peer from `X-Forwarded-For` for any loopback client, so **all three launch
  paths pass `--no-proxy-headers`** (`entrypoint.sh`,
  `scripts/start_dev_server.sh`, and `docker-compose.dev.yml`'s `command:`).
  Dropping it from any one of them re-opens the bucket the flag closes.
  Refresh and change-password rotate (blocklist) the presented token;
  password change revokes all pre-change tokens via the `iat` check.
- `DATABASE_URL` is derived from the `DB_*` vars with percent-encoded
  credentials; an explicit `DATABASE_URL` overrides the derivation.
  `trust_proxy_headers` defaults to False — the app is the network edge and
  serves the SPA itself, so nothing trustworthy sits in front; the prod
  compose passes it through so a posture change stays a config flip.
  `cookie_secure` is tri-state **in the LAN posture only**: unset = Secure
  only when `environment=production`; explicit false allows login
  over plain-HTTP LAN. **`trust_proxy_headers` is the exposed-deployment
  switch, not only a limiter setting (T4.03, doc 18 §9)** — with it on the
  tri-state collapses to enforced and an explicit `cookie_secure=false` is
  **clamped** to true rather than honoured, because in this tree the only live
  reason to trust proxy headers is an operator TLS proxy in front (the
  nginx-in-image fallback is recorded and not taken). The clamp is reported,
  never silent: a boot warning, `session_cookie_secure_clamped`, and
  `cookie_secure_clamped` on `GET /auth/security-posture`. Operator procedure:
  `docs/runbook-exposed-deployment.md`, which also records that `/mcp` must not
  be routed from the public side. That guidance predates and now outlives the
  bearer requirement doc 18 §5 shipped 2026-08-26: a bearer key closes the old
  "any LAN peer can call any tool" gap, but the app's own proxied-`/mcp` guard
  refuses a proxied call regardless of whether it carries a valid key, and MCP
  auth has no login-style lockout — every attempt, including an invented key,
  costs one fixed-cost bcrypt verification on the shared thread executor that
  also serves git subprocesses, code parsing and local classification. There
  are no `LLM_*` env vars — all LLM config lives in the DB via the setup
  wizard.

## Live model endpoints (dev machine)

Recorded at the owner's explicit instruction, 2026-07-28 (DeepSeek, Ollama) and
2026-08-10 (OpenAI). **The keys are NOT in this file and must never return to
it.** They live in `.claude/local-credentials.md`, which `.gitignore` covers
(`.claude/**`) — read that file when a bench, gate or qualification pass needs
a real key, and export it rather than copying it anywhere tracked.

**Owner ruling 2026-08-20, superseding the 2026-08-15 one**: the keys came out
of this file and the history was rewritten so no past commit carries them
either, which is what the earlier ruling deferred until publication. The
rewrite is not the end of it — **both keys were also pasted into a chat
transcript**, a copy outside this repo's control, so **rotation is still the
only thing that actually retires them** and is owed before the repo is
published. What the rewrite bought is that a push is no longer the event that
makes rotation urgent.

- **Extraction / classification / reasoning — DeepSeek.**
  `base_url=https://api.deepseek.com/v1`, `api_kind=deepseek`,
  key in `.claude/local-credentials.md`. Models offered:
  **`deepseek-v4-flash`** and `deepseek-v4-pro`. **The F1 baseline and every
  gate re-measurement use `deepseek-v4-flash`** — the gate ledger fixes the
  model, so a run on `-pro` is not comparable and must not be used for
  parity. Export as `DEEPSEEK_API_KEY` for `run_bench.py` and
  `benchlib/run_smoke.py`.
- **G-D judge — OpenAI.** `base_url=https://api.openai.com/v1`,
  `api_kind=openai`, key in `.claude/local-credentials.md`.
  Recorded 2026-08-10 for the owner-ruled **`gpt-5.5`** G-D judge attempt
  (T2.114). Export as `OPENAI_API_KEY`; `run_judge_qualification.py` takes the
  key as an argument and the model/base_url/api_kind as overrides, so a judge
  swap lands in the identity hash and can never read as a re-run of the same
  judge. **This is a judge credential, not an ingestion one** — it is not the
  extraction/classification path and must not be pointed at one, because the F1
  baseline and every gate re-measurement are fixed to `deepseek-v4-flash` and a
  run on another model is not comparable.

- **Embeddings — Ollama on the LAN.** `http://192.168.0.196:11434`,
  `api_kind=ollama`. Two embedding models, and the choice is load-bearing
  because the fingerprint partitions on it:

  | Model | Dims | Context |
  |---|---|---|
  | `nomic-embed-text:latest` | 768 | 2048 |
  | `qwen3-embedding:0.6b` | 1024 | 32768 |

  Switching between them is an embedder rotation, not a config tweak: each
  fingerprint gets its own `memory_embeddings__<slug>` child table and a
  cross-fingerprint comparison has no defined cosine distance. DeepSeek has
  **no** embeddings capability, so `assert_can_embed` will refuse an embed
  call routed there — that guard is working, not a misconfiguration.

## Code indexing

`POST /repos/{id}/reindex` accepts `{full, enrich_symbols,
generate_wiki}`, all default False. An unchanged HEAD sha
short-circuits the reindex unless `full=true` **or the repo carries
outstanding index debt** (below). Symbol enrichment and
wiki generation run only when their toggles are set; `GET /code/wiki`
is read-only and never implicitly generates.

An incremental run re-traces the callers of every changed file, because
re-indexing a file deletes every call edge pointing into it. That
re-trace is capped at `DEPENDENT_RETRACE_CAP` (500); the callers past
the cap are **persisted to `repositories.index_debt`, never dropped** —
dropping them leaves a graph that is quietly wrong, with no error and
no symptom but missing callers. Later runs fold a bounded batch
(`config` row `code_index_debt`, default the cap) of that queue back
into their changed set until it reaches zero, and the batch leaves the
queue only after the run that re-traced it succeeded. Debt files are
only ever *added* to a changed set: their content hash is unchanged, so
phase 03 skips them and the drain deletes nothing. Both the deferral
and the drain journal a `repo_indexed` `events` row and surface on
`RepoResponse.index_debt`.

**Every recurring indexing behaviour is a per-repo switch, and every switch
defaults off** (the per-repo indexing modes epic, 2026-08-29, replacing the
single always-on `auto_sync` flag): `fetch_enabled` (interval
`fetch_interval_seconds`, default 300s, floor 30s), `index_on_commit_enabled`
(interval `commit_poll_seconds`, default 60s, floor 15s), and
`index_uncommitted`. `HEAD` is the single indexing trigger — a pull, another
agent's commit and the operator's own commit are the same event once `HEAD`
has moved. Fetching is a separate lane whose only job is to move `HEAD`; the
recurring index lane never fetches (`CodePipeline.run(..., pull=False)`), so
it can never fast-forward the operator's branch or reset over working-tree
drift the run was meant to index. `index_uncommitted` covers the case `HEAD`
can't see at all: a working tree edited without a commit — but it has no lane
of its own. It only widens the check `index_on_commit_enabled`'s commit-poll
tick already runs (`job_runners.make_repo_sync_runner` checks
`index_on_commit_enabled` before it ever looks at `index_uncommitted`), so it
does nothing while that switch is off, no matter what the API accepted or the
row says. **Manual reindex, the push webhook and MCP `code_reindex` bypass
every one of these switches entirely** and keep the old fetch-then-index
behaviour — the switches govern only the unattended, recurring loop, never an
explicit operator-triggered run.

## Documents (`app/services/document_door.py`, block channel)

A document is filed markdown or plain text, parsed into a `blocks`
tree (headings, paragraphs, lists, code, quotes, tables and their rows,
dividers) that is deliberately
**not** run through the memory pipeline: filing a document never extracts
entities or relationships. The parser stack also handles PDF, but no
production caller can deliver one — `content` is `str` on both doors and
`parse_pdf` takes bytes, so a PDF is a designed 422 rather than an
unimplemented case. `tests/test_block_pipeline.py` walks the transitive
import closure of **this module and `block_pipeline` both** and fails the
build if `app.services.pipeline` is reachable from either — rooted at the
door as well as the pipeline, since the door imports the pipeline and a
seed of the pipeline alone would leave the door itself unscanned. A
document is candidate signal, not an asserted graph. **Documents are
parsed, embedded and retrievable, and never extracted into memories** —
the on-demand proposition lift that would have carried candidate signal
into the fact vault was retired (2026-09-05); see the firewall paragraph
below.

**A document is content-first or block-first, and the flag decides who may
write it** (increment 8, spec §8.2). `documents.properties.ingest_direction`
is absent on every document filed through `put`, which means content-first.
The first block verb against one **converts** it: markers the parser discarded
are derived from the stored `content` through each block's own `char_span`, so
the conversion is faithful rather than defaulting every list to `-`. After
conversion `document_put` at that uri is **refused** — 409 on the route, a
`direction_conflict` envelope from the tool — because a content push over an
editing session would strip every block the editor placed. That refusal is
taken under a `SELECT … FOR UPDATE` on the document row and the block verbs
take the same lock, so the two serialise; a check ahead of the savepoint would
be check-then-act, which is the race increment 3's compare-and-set closed.

**Conversion refuses rather than converting lossily.** The parser mints no
block for a raw HTML block or a link-reference definition, so regenerating
`content` from the tree would silently delete them;
`block_serializer.reproduces_source` detects those in the token stream and the
verb raises `DocumentNotConvertible`. It also refuses when a construct is
representable but missing from *this* tree — a document filed before its block
type existed carries the construct in its content and no row for it, and
`ingest_document` returns `UNCHANGED` on a byte-identical re-push without
touching blocks, so a token-versus-block count check is what stops that
becoming silent loss. **Widening a block type therefore obliges a re-import,
not merely a redeploy** (measured 2026-09-02: adding `divider` left exactly
201 filed documents with `---` in their content and no divider row).

**Four block verbs, both doors** — `block_update`, `block_insert`,
`block_move`, `block_delete` over `app/services/block_verbs.py`. Every verb
runs one pass: lock, load the tree, apply one mutation in memory, serialise,
write placement and document row in a SAVEPOINT, journal `blocks_edited`
(carrying no block text), commit, then embed **only** the touched block.
`char_span` is recomputed in that same pass — the serialiser is the only thing
that knows where each block landed — so spans never drift and are never NULL.
The cost model: one edit is one bulk placement UPDATE over the document's
blocks, one document write, and one single-block embed.

**Five verbs, both doors.** `put`, `search`, `outline`, `get` and
`delete` are reachable from REST (`POST /api/v1/documents`,
`POST .../search`, `GET .../{id}/outline`, `GET .../{id}` and the
`by-uri` twins, `DELETE .../{id}` and `DELETE .../by-uri`) and from MCP
(`document_put`, `document_search`, `document_outline`, `document_get`,
`document_delete`). Both doors call the same `document_door` functions
and resolve a caller-named target the same way, `resolve_document_target`,
by id or by `(project, uri)`. **`(project, uri)` is the document's
identity**: re-filing the same path updates the existing row in place
rather than creating a second one. That upsert is this door's own shape
and has no analogue on the memory side, where all four capture doors
append a row per capture and `origin_key` is corroboration identity, never
a dedup key.

**Bounds, refused at the door.** `MAX_CONTENT_CHARS` (1,000,000
characters) and `MAX_BLOCKS` (5,000) are both checked in `put_document`.
The character bound is checked first, before any parse or write starts.
The block-count bound can only be known after parsing, so it is checked
inside a SAVEPOINT wrapped around the filing itself: a document that
parses to too many blocks raises `DocumentTooLarge` from inside that
SAVEPOINT, rolling the document row, its blocks and the `document_filed`
event back — never leaving a half-filed, oversized document staged for
the caller's next commit.

**`documents.content` is the stored source of record** (2026-08-31 spec §5,
the round-trip increment). A text filing stores its source verbatim; a bytes
source stores NULL rather than a lossy decode. `content_hash` remains the
change gate, and `blocks.char_span` indexes into this column — spans have
always pointed at the source, and now the source is kept. Both keyed reads
take `include_content` (default off, so no existing reader pays for a
potentially megabyte field): on, `GET /documents/{id}` and the `by-uri` twin
add `content` to the envelope, and MCP `document_get` answers
`{content, blocks}` in place of its bare array — the one flag under which that
tool returns an object. One service read, `document_door.document_content`,
serves both doors.

**`put` takes an optional `expected_hash` compare-and-set.** The predicate
rides the writer's own UPDATE with a rowcount check (`update_document` returns
the matched count); a read-then-compare in Python passes for both of two
racing lanes and the second still clobbers the first, which is what review
finding M1 was about. A stale hash answers 409 on the route and a
`hash_conflict` envelope from the tool — one `DocumentHashConflict` behind two
wire shapes — and `PutResult` echoes `content_hash` so a caller can
precondition its next edit. Omitting it keeps last-writer-wins. Note a
byte-identical re-push carrying a *stale* `expected_hash` is a conflict rather
than `unchanged`: the precondition is "the document is as I last saw it", not
"this write would change something". The batch ingest path deliberately takes
no `expected_hash` — the corpus import is last-writer-wins re-runnable by
design.

**An edit re-embeds the whole document.** Filing a `(project, uri)` that
already exists strips every prior block row and writes a fresh set —
`strip_blocks` then a plain `INSERT INTO blocks` that mints a new `id`
for every row — so there is no per-block identity carried across a
change: block N in the new tree is not "the same row" as block N in the
old one even when its text is unchanged. There is no diffing and no
partial re-embed; the cost of editing one paragraph in a large document
is the same as filing it from scratch. State this as the cost model, not
a defect — the door has no cheaper path today.

**`unchanged` still embeds.** `ingest_document`'s content-hash gate
returns `UNCHANGED` before touching any block when a re-push is
byte-identical to what is already filed, which means it also does
nothing for a filing whose block write committed but whose *embed* failed
afterward (embedding runs after the filing commits, never inside it, so
that split is possible). Stopping at `UNCHANGED` would make the caller's
one natural repair — re-push the same content — a silent no-op, so this
path additionally finds the document's blocks that carry no vector under
the active embedder fingerprint and embeds those. Resolving that
fingerprint costs a real embed call (never a cheap data probe: a probe
answers "which fingerprint holds data", which is biased toward a stale,
already-complete partition after a rotation rather than the active one
retrieval reads), so **every `unchanged` re-push spends one embed call**,
unconditionally, even on a document that already has nothing to repair —
where the door used to spend a cheap database probe instead. A caller
re-pushing N unchanged documents in a pass now makes N embedding calls;
the hourly sweep still pays this once, this door pays it once per
request.

**Delete removes the row and cascades; there is no provenance to
withdraw.** This paragraph described `delete_document` withdrawing
`fact_sources` rows a block corroborated and expiring any fact left
unsourced, until the proposition lift and the block-to-fact bridge that
would have written those sources were retired (2026-09-05). Nothing
mints a `fact_sources` row from a block, so a document's blocks
corroborate no fact: `delete_document` removes the document row, which
cascades its blocks and their vectors, withdraws no provenance, expires
no fact, and journals nothing at all — there is no delete event type.
The withdraw-then-expire
pass it used to run was the withdrawal half of a bridge whose attaching
half never had a caller, which made it a permanent no-op; it went with
the bridge.

**Owner ruling, 2026-08-23: `documents.write` and `documents.retrieval`
are two-door.** `docs/two-door-parity.md` is the audit of record. The
five verbs above generate nothing and label nothing — they file a
document or return its own text with a cosine score, the way `code.search`
returns source — so they do not touch the faithfulness judge that gates
`POST /api/v1/documents/qa` (single-door, still G-F-gated, unaffected by
this ruling). Landing both verbs on both doors **clears no gate and moves
no bar**; it is a parity decision, not a capability one. `documents.reads`
(the list/summary/connections browsing routes) stays REST-only for its
own, unrelated reasons.

**The block channel is firewalled from memory composition, and the
firewall is now absolute.** A block row is retrievable only through the
verbs above; it is never fused into `HybridSearchService` or
`LayerCompositionService`'s ranking, and it is never lifted into the L1
graph — the on-demand proposition lift (doc 16 §5) and the
block-to-fact bridge (`block_fact_sources`) that would have carried a
route from a block to a fact are both retired (2026-09-05). This
paragraph used to name `block_fact_sources` as a deliberate, narrow
exception to the forbidden set, excluded because it queried `blocks`
only to resolve ids and let no block text cross into the vault; that
exception is gone along with the module, and there is no route from a
block to a fact at all. `tests/test_block_retrieval.py` enforces both
halves structurally, rather than only checking that today's ranked
results happen not to contain a block. The retrieval half walks the
fusion modules' own imports and the composition's channel and id-kind
registries and fails the build if a block becomes reachable from either.
The vault half walks the import closure of every module that mints a
fact, moves one on the ladder or synthesises an article from the vault,
and fails the build if one can reach a module that reads a block row.
Scoped to minting rather than to "writes `knowledge_triples`"
deliberately, and the difference is directional, not a matter of which
set is bigger: the firewall is about a block *becoming* a verified
fact, so the scan is rooted at the modules that can *make* one — mint,
promote on the ladder, or synthesise an article from the vault — and a
module that only reads blocks without ever minting or promoting
anything is not one of its subjects. A raw-SQL-text derivation over
`INSERT INTO` / `UPDATE` / `DELETE FROM knowledge_triples` finds three
modules today — the repository itself, `verification_recompute` and
`entity_merge` — and that is deliberately *narrower* than the nine
`VAULT_WRITERS` seeds: `fact_lift` and `article_synthesis` write
through the repository, so a text scan cannot see them at all. That is
why the derivation is a **staleness guard on the hand-written seed
list** rather than the root rule, and why the method-level scan exists
beside it. "Writes the vault" and "mints or promotes a fact" are also
not the same predicate — `fact_provenance` calls `expire` and mints
nothing — so rooting the scan at minting names the property the
firewall is about rather than a proxy for it. A list rooted at "touches
`knowledge_triples`" would additionally have swept `document_door` in
(it reads blocks by construction) and then asserted something false
about it: `document_door` was once the withdraw-then-expire pass's own
writer, calling the bridge's withdrawal and then `expire` itself, but
that pass went with the bridge and it writes nothing today — the
negative control at `test_block_retrieval.py:471-475` shows its
closure still reaches the block channel, which is exactly why the
minting root, not a "touches the vault" root, is the one that stays
correct. **That the block channel may only read the
vault, never write or promote, is pinned at the method level:**
a third scan reads every block-channel module's own AST and fails the
build if one names any `KnowledgeTripleRepository` method outside a
four-method allowlist — `as_of`, `get`, `get_live`, `list_live`, all
reads. `expire` is not on it: the withdraw-then-expire pass that once
called it was the withdrawal half of the retired bridge, and it has no
caller left to permit. The forbidden set is the complement of the
allowlist with no exception, so a method added to that repository is
forbidden to this channel until someone classifies it. Without it,
`insert_open` or `set_verification_status` inside `document_door` would
satisfy both other scans: the coverage guard derives writers from raw
SQL text, which a call through the repository does not produce.

## Cross-cutting invariants

- **memory_id type drift.** Hybrid search returns string ids; the
  vector repo returns `UUID`. Every consumer must normalize at the
  boundary or matches drop silently.
- **Lowercase entity names** on disk; preserve original casing in
  `properties.display_name`. The supersession detector and the
  `technologies` denorm both assume lowercase.
- **No cross-fingerprint joins** on embedding tables.
- **Idempotent re-extraction.** Always strip prior `memory_id` graph
  contributions before writing a new set.
- **`technologies` is lowercase, denormalised, GIN-indexed.** Keep all
  three; dropping any one breaks supersession or retrieval.
- **REPLACES family.** `REPLACES`, `IMPROVES_ON`, and the legacy
  `BUILDS_ON` collapse to one bucket via `family_key` for rescue dedup
  **and they are the supersession trigger** — the family scopes both, not
  rescue dedup alone.
  Adding a new replacement-family relation means editing
  `REPLACES_FAMILY` too.
- **Async session lifetime.** Never open a fresh session while the
  request transaction still holds locks on the same rows; commit first.
- **asyncpg needs CAST on raw-SQL params.** Any bound param whose
  type Postgres cannot infer must be cast (`CAST(:vec AS vector)`,
  `CAST(:id AS uuid)`, `CAST(:props AS jsonb)`), especially with
  variadic ANY / unnest / jsonb_build_object — otherwise
  `IndeterminateDatatypeError`. And roll back the session before
  mutating ORM objects in an error handler.
- **The backup worker is a third launch path** (increment 7, 2026-09-02):
  `docker-compose.worker.yml`, on a **second machine**, running the same image
  against nightly-restored snapshots. It is bound by every invariant this one
  is — the worker-count guards are parametrised over all three compose files,
  and the `--no-proxy-headers` scan covers it too.
  **The enforcement of "read-only" is a Postgres role, never the flag.** The app
  connects as `darkmem_viewer`, which holds `SELECT` and nothing else
  (`scripts/worker/viewer-grants.sql`); every refused write arrives as SQLSTATE
  `42501` and one global handler maps it to a 403 `read_only` envelope, so no
  per-route allowlist is maintained. `DARKMEM_READ_ONLY` (default **off**;
  reported on `GET /auth/security-posture` and rendered on the Security tab) is
  ergonomics on top: it skips the boot writers, never arms `JobRegistry`,
  refuses chat and job triggers, clamps `reranker_enabled`, and quiets the
  write-on-read paths. A reader who takes away "the flag makes it read-only" has
  been misled — with the flag off and the role in place the instance is still
  read-only; with the owner role and the flag on it is **not**.
  Token rotation is disabled and stated rather than discovered: refresh
  reissues without blocklisting, so a captured pre-refresh token lives to its
  own `exp`. **The worker needs no external service at all** (owner ruling
  2026-09-03, replacing an earlier requirement that it reach the embedding
  endpoint — a host whose job is surviving another machine's failure is the
  worst place to depend on a third). Under the flag the semantic arm is
  *skipped* rather than attempted: `llm.embed` sits outside
  `_run_channels`' one-sided-failure guard, so an unreachable embedder would
  raise out of the whole search instead of degrading. Memory and code search
  answer on their keyword/`ILIKE` arms; the articles channel reports
  `semantic_ran=False`. **Document search is refused rather than emptied** —
  its ranking is cosine-only with no keyword arm, so an empty result would be
  indistinguishable from "no matches". And the doors that would spend or dial
  out before they write are refused at a shared `refuse_when_read_only`
  dependency (`api/deps.py`): `memories/reason`, `documents/qa`, every
  `reembed` POST, repo create/reindex/reindex-files/webhook, chat, job
  triggers. That list is not the per-route allowlist review B1 rejected — that
  argument is about *writes*, which the SQLSTATE 42501 handler catches
  generically; an external call is not a write and the database never sees it.
  The **receiver** (`app/worker_receiver.py`, its own uvicorn process) is the
  worker's one write door and it writes files, not rows: a closure walk fails
  the build if it can reach `app.main`, `app.database` or any service. The
  restore loop is a host-side script (`scripts/worker/restore-cycle.sh`) that
  **verifies before it swaps** — replay, migrate and `schema_guard` all run
  against a *side* database while the app serves the previous one, and a
  snapshot from an older baseline is rejected with the viewer left up. Procedure:
  `docs/runbook-backup-worker.md`.
- **Single worker (invariant 13), re-decided 2026-08-16.** Exactly one
  uvicorn worker, one replica, on every launch path. The knob has three
  silent spellings — `--workers`, the `WEB_CONCURRENCY` env var uvicorn
  reads when the flag is absent, and compose `deploy.replicas` — and
  none may appear in an ops change. The reason is T4.09's audit (38
  in-process assumptions; 17 BREAKS at N = 2), not the inert PPR
  snapshot the design docs lead with: the WebSocket fan-out, the job
  scheduler (no lease — every registered job fires N times per tick; 21
  when T4.09 counted, 24 today, and the number is not what the finding
  rests on), the per-IP
  login limiter, the live orchestrator swap and seven unlocked job
  cursors all break first, and `backend/app` holds no cross-process
  serialisation primitive to build on. Raising the count is a flagged
  decision through the T4.10 record
  (`docs/planning/analyses/2026-08-16-t4.10-replica-decision.md`, which
  states what would flip it) — never a side effect of a deployment
  task.

# Darkmem — business logic baseline

Centralized memory system for AI agents. Commands and layout first;
everything from "Domain model" down is contract, not implementation
detail. A refactor that breaks one of the listed invariants is a
behavior change, not a cleanup.

This file states current rules only. The reasoning trail behind them —
which claims were corrected when, and why — lives in `git log -p CLAUDE.md`
(the last long-form revision is `d200bf58`), in the design docs and specs
named below, and in `docs/planning/gate-ledger.md` for every gate number.
When you change the code a sentence here describes, correct the sentence in
place. Don't add a note saying it was corrected.

## Deployed data is durable (owner ruling 2026-09-28)

**Darkmem runs in production, on this host and on 192.168.0.199, and their
data must survive every release.** A schema change ships as a new Alembic
revision that upgrades a populated database in place, so `alembic upgrade
head` at boot is the whole schema deploy. Never make a change that works
only on an empty database, and never plan a release around dropping and
recreating one: a new NOT NULL column carries a default or a backfill in the
same revision, a renamed or retyped column carries its data across, and a
table or column is dropped only once no released code reads it.

## Commands

### Host environment (verified)

- **There is no `python` on PATH** (only `python3`). The backend interpreter
  is `backend/.venv/bin/python`; every `python` below means that one, run
  from `backend/`.
- **`psql` is not installed on the host.** Reach Postgres through its
  container: `docker exec darkmem-postgres-1 psql -U darkmem -d <db> -c "…"`
  (dev, `127.0.0.1:5433`) or `darkmem-prod-postgres-1` (production,
  `127.0.0.1:5432`, never a test target).
- **Databases on the dev Postgres:** `darkmem_test` is pytest's (and the
  controller's when lanes run in parallel); `darkmem_test_2..5` are for
  parallel lanes, one each; `darkmem_bench` is the harness database, free to
  reset. Never point a harness at `darkmem_test`.
- **The dev Postgres is often stopped.** Start only its service:
  `docker compose -f docker-compose.dev.yml up -d postgres`. Starting the
  whole dev stack also starts its `darkmem` app on `8000:8000`, which
  collides with production.
- **This host runs production**: `darkmem-prod-darkmem-1` on `:8000` and
  `darkmem-prod-postgres-1` on `:5432`.

### Gate and tests

- **Merge gate (repo root): `./scripts/gate.sh`**. It runs the alembic
  single-head assertion, backend pytest, frontend typecheck/test/build,
  the browser-extension suite, both SDK suites (`sdks/python` under pytest,
  `sdks/ts` under the frontend's vitest), the benchlib harness suite, and the
  F1 bench in `--algo-only` mode. `--full` adds the retrieval eval, the API
  e2e suite (`backend/scripts/e2e/`, boots its own disposable stack), the
  Playwright e2e run and a port-hygiene diff. It exits non-zero naming the
  failing gate; `GATE BLOCKED` (exit 2) means a missing toolchain, not a red
  gate. `--full` needs `DEEPSEEK_API_KEY` exported, though on a warm cache
  the eval replays at 0 live calls.
- **A red leg on this host is a kill before it is a regression.** An
  `earlyoom` daemon kills at ~80% swap, on whichever leg is running (measured
  on Playwright, frontend vitest and backend pytest). **Exit 143 is SIGTERM,
  not a failure — check `free -h` before believing a red.**
  **`./scripts/gate.sh --full` cannot complete on this host**; run its legs
  individually: `tests/test_api/test_rest_conformance.py`,
  `scripts/benchlib/tests` (name the path), and `make generate` in `sdks/`
  plus both SDK suites. Re-run Playwright standalone through
  `backend/scripts/e2e/run_playwright_e2e.py` before believing a red (its
  arguments pass through to `playwright test`, so `run_playwright_e2e.py
  tests/x.spec.ts --project=chromium` runs one spec), and
  **never run Playwright bare**: `npx playwright test` points `/api` at the
  live instance on `:8000`.
- **`pyproject.toml` sets `testpaths = ["tests"]`, so plain `pytest -q` does
  not collect `scripts/benchlib/tests`.** Run the gate, or name that path.
- Backend tests (from `backend/`): `.venv/bin/python -m pytest -q`. They need
  a `darkmem_test` database on the dev Postgres; create it once with
  `docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -c "CREATE DATABASE darkmem_test;"`.
  conftest **unconditionally** pins `DATABASE_URL` to `TEST_DATABASE_URL`
  (default `postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test`),
  so setting `DATABASE_URL` in front of pytest tests the wrong database. It
  then runs `DROP SCHEMA public CASCADE` and `alembic upgrade head`: never
  point it at a real database.
- **Run the backend suite in parallel**: `.venv/bin/python -m pytest -q -n 4
  --dist loadfile` (pytest-xdist, in the `dev` extra) took it from 19 min to
  3.5 min on 4 cores. Each worker creates and uses its own
  `<TEST_DATABASE_URL's database>_gwN` on the same server (`darkmem_test_gw0`,
  or `darkmem_test_2_gw0` from a lane), so lanes never share one. The gate
  does this with `GATE_PYTEST_WORKERS` workers (default 4, `0` for serial).
  A test that passes alone and fails under `-n` is leaking state across
  files; fix the leak, never pin the test to serial.
- **The guards leg is mandatory after registering any route or MCP tool.** A
  new door trips full-list enumeration guards that live outside the module
  you worked in and that no door-local test touches, and a full-suite run on
  this host can't be relied on to reach them. From `backend/`, on a lane
  database of its own (~40s, no LLM key):

  ```
  TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
    .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py \
      tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py \
      tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py \
      tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py \
      tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py \
      tests/test_event_taxonomy_map.py
  ```

  It does **not** cover two prose counts; re-read them by hand: the headline
  counts sentence in `docs/two-door-parity.md` (outside the generated block)
  and this file's tool and job counts.
- Frontend (from `frontend/`): `npm run typecheck` (= `tsc -b`; plain `tsc`
  misses the project refs), `npm test` (vitest on happy-dom; excludes
  `tests/`, which is Playwright via `npm run test:e2e`), `npm run build`. `npm run lint` is
  advisory. The frontend is not prettier-clean; never run a repo-wide
  `prettier --write`.

### Dev servers, migrations, schema

- Dev servers: `./scripts/start_dev_server.sh` runs alembic upgrade, then
  uvicorn :8000 `--reload --timeout-keep-alive 75` (the 75 prevents sporadic
  502s through the vite proxy); `cd frontend && npm run dev` runs vite :3636
  proxying `/api`, `/health`, `/ws`, `/mcp` to :8000. On this host `:8000` is
  production, so the dev uvicorn cannot bind and vite proxies to prod.
- Migrations (from `backend/`): `.venv/bin/python -m alembic upgrade head`.
  `migrations/env.py` reads `DATABASE_URL` via app settings (default port
  5432) and ignores `alembic.ini`'s URL, so set `DATABASE_URL` explicitly for
  host-side runs against the dev Postgres on 5433. Containers migrate at
  startup via `entrypoint.sh`; `docker-compose.dev.yml` overrides the command
  and skips migrations.
- **`0001_baseline.py` is permanent.** Never edit it, not even a comment:
  its hash is pinned (`schema_guard.FROZEN_BASELINE_SHA`, asserted by
  `tests/test_schema_guard.py`) and stamped into every deployed database. A
  schema change is a new file in `backend/migrations/versions/` whose
  `down_revision` is the current head. The chain stays linear: the gate and
  the same test assert exactly one head, so when two lanes each add a
  revision, rebase the later one's `down_revision` onto the other. The test
  suite migrates an empty schema only, which proves a revision runs, not
  that it keeps rows; run a new revision against a database holding data
  (a restored backup on the dev Postgres) before shipping it.
- **A database on an older copy of the baseline needs a one-time repair.**
  Until 2026-09-28 a schema change regenerated `0001` in place, so a database
  built from an earlier copy is still stamped `0001` and `alembic upgrade
  head` does nothing to it.
  `app/schema_guard.py` (run from `entrypoint.sh`) stamps a hash of the
  baseline file into the database and **refuses to start** when they
  disagree; it fails closed with no override. Bring the schema to the
  permanent baseline by hand (the runbook's additive path when the diff
  allows it, otherwise drop and restore), re-seeding `admin_password_hash`
  and all eight `llm_purpose_configs` rows if the data is not restored,
  especially `verification`, which `llm_seed.py` does not reproduce at the
  qualified judge identity. Procedure: `docs/runbook-deployment.md`. Both
  production databases are on the permanent baseline (192.168.0.199 was
  repaired in place on 2026-09-28). Background:
  `docs/planning/analyses/2026-08-17-production-schema-drift.md`.

### Build, deploy, release

- Stacks: dev `docker compose -f docker-compose.dev.yml up -d postgres` (see
  Host environment); prod `docker compose up -d` (needs `DB_PASSWORD` and a
  `JWT_SECRET` of ≥ 32 chars in `.env`, plus `COOKIE_SECURE=false` for
  plain-HTTP LAN).
- **Build with `DARKMEM_PUSH=0 ./scripts/build-push.sh`.** The script
  defaults to `DARKMEM_PUSH=1` and pushes, and this machine must never
  publish an image. It builds **one** image, `darkraise/darkmem`, from the
  repo-root `Dockerfile`, carrying the API and the built SPA; the app serves
  the UI on `:8000` and nothing binds `:80`. The script also tags the short
  git sha, so `docker inspect` answers which commit is running. (The image
  was `darkraise/darkmem-api` and the compose service `darkmem-api` before
  2026-08-18; an old stack needs `docker compose down --remove-orphans`.)
- **Redeploy this machine after every change that lands** (owner ruling
  2026-08-21) when it alters the running artifact: `backend/`, `frontend/`,
  `Dockerfile`, compose or `entrypoint.sh`. Docs and planning changes don't
  need it. The owner reviews the live instance, so an undeployed fix gets
  reported again and an undeployed regression reads as a pass. Sequence:
  `./scripts/gate.sh` → `DARKMEM_PUSH=0 ./scripts/build-push.sh` →
  `docker compose up -d` → wait for `healthy` → **confirm the change is in
  the running image** (`docker exec darkmem-prod-darkmem-1 grep …`, or the
  new field on `/openapi.json`). Compose reuses an image whose tag didn't
  move, so a failed build redeploys the old bits and still reports
  `Started`.
- **A deploy is not a release.** A deploy writes no tag and pushes nothing.
  **A push to master releases** (owner ruling 2026-08-29):
  `.github/workflows/release.yml` derives the next version from the
  conventional-commit types since the last tag, runs CI, publishes to Docker
  Hub and GHCR, and only then writes the tag and GitHub release. A push with
  no `feat`, `fix`, `perf` or breaking commit cuts nothing, and a push whose
  derived version has no `## vN.N.N` section in `CHANGELOG.md` fails before
  the suite runs. The changelog is hand-written; only the release body is
  generated (`scripts/next_version.py`). `./scripts/release.sh vN.N.N` does
  not tag: it is the local pre-flight (sync version fields, build, deploy,
  probe `/openapi.json`). Fetch tags before deriving a version locally.
- **CI verification prefers `darkmem-linux`**: `scripts/pick_runner.py`'s
  default `fallback` mode routes backend/frontend checks to self-hosted
  while a labelled runner is online (queuing when busy) and to `ubuntu-latest` when none is online. Seeing the runners needs
  the `RUNNER_PICKER_TOKEN` secret (fine-grained PAT, Administration:
  Read-only); without it the picker queues on self-hosted. Manual dispatch
  can select `self-hosted`, `hosted` or `auto` for those checks. API and Playwright e2e always
  run on `darkmem-linux` in isolated job containers with their own Postgres,
  using the LAN model endpoint (`vars.DARKMEM_OLLAMA_BASE_URL`). Image builds,
  scans and the image boot smoke (one job, so CI stores no image artifact),
  publishing and release writes run on `ubuntu-latest`; publishing
  waits for all checks, including e2e. Picker jobs also run hosted, so hosted
  minutes are still required. Jobs must not use fixed host ports, container
  names or image tags, or `--network host` (`tests/test_ci_workflows.py`).
  Setup: `docs/runbook-ci.md`.
- **Prod networking is bridge, not host** (owner ruling 2026-08-18). The app
  publishes `8000:8000` and Postgres `127.0.0.1:5432:5432`. Postgres must
  listen on `listen_addresses=*`, because the API connects across the stack
  network; a loopback pin refuses every app connection while `pg_isready`
  still reports healthy. The login limiter keys on the transport peer: a LAN
  client keeps its address through the DNAT, while `127.0.0.1` and other
  Docker networks arrive as the bridge gateway and **share one bucket**, so
  five failed host-local logins lock out host-local logins. That is accepted,
  and `TRUST_PROXY_HEADERS` does **not** fix it (Docker NAT sets neither
  header, and the flag clamps `cookie_secure` and arms the `/mcp` proxied
  guard). `network_mode: host` silently ignores every `ports:` mapping;
  `tests/test_deployment_artifact.py` asserts the bridge network, both
  bindings and the `listen_addresses` pairing.
- **Backups: `systemd` timer `darkmem-backup.timer`**, nightly at 03:30 with
  `Persistent=true`. It runs `scripts/backup.sh /root/darkmem-backups` **from
  this working tree**, so the checked-out branch is what runs against
  production. The script dumps the live database and prunes to the newest
  `BACKUP_KEEP` (14). Dumps are local only. **Attachments are a second
  artefact family on both producers**: a manifest hash over `(id, sha256)`,
  computed by Postgres, decides whether the set changed; if it did, each
  producer writes one whole-set tarball beside its dump under the same stamp
  (`darkmem-attachments-<stamp>.tar.gz` plus `.manifest` for `backup.sh`,
  `BACKUP_ATTACHMENTS_KEEP` default 3; `darkmem-app-attachments-<stamp>.tar.gz[.age]`
  for `backup_ship`, per-destination `attachments_retention_keep` default 3).
  **`_is_snapshot` is never widened**: families are separated by
  `Family.matches` and each prune takes one, because tarballs sort after
  dumps and a shared predicate would delete dumps. A restore pairs a dump
  with the newest tarball whose stamp is ≤ its own. On the backup worker the
  tarball unpacks into `gen-<stamp>/` under a read-only bind mount and a
  relative `current` symlink swaps beside the database rename;
  `restore-cycle.sh`'s no-op predicate covers both halves.
  `python -m app.services.attachment_verify` reports rows without files
  after any restore.
- Backend lock: regenerate only with
  `uv pip compile --universal pyproject.toml -o requirements.lock` (a
  non-universal Windows resolve leaks pywin32 and drops uvloop).
  `entrypoint.sh` must stay LF (`.gitattributes` enforces it).

## Layout

`backend/app`: `api/routes` (REST), `api/mcp` (`MCPServer`, mounted at
`/mcp`; scopes in `api/mcp/scopes.py`), `services` (pipeline.py,
extraction_clean.py, code_pipeline.py, job_registry.py, page_door.py, ...),
`repositories` (graph/relational/vector), `models`, `schemas`; entry point
`app/main.py`. `backend/migrations/versions` is Alembic. `backend/scripts`
holds the eval harnesses: `extraction_bench/` (F1 bench and gold files) and
`benchlib/` (corpus loader, offline ingest driver, run ledger, retrieval
gold and scorer, latency/token twin, full-context comparator, `run_*.py`
runners). Harness caches under `backend/scripts/` are warm and gitignored;
if a re-run suddenly wants live model calls, the cache key changed, so find
out why before paying for it. `frontend/src`: `features/*` plus TanStack
Router file-based `routes/` (`routeTree.gen.ts` is generated; never
hand-edit it). `docs/`: dated audit reports, `api-rest-conventions.md` (the
REST contract new endpoints must match: 201 create, 204 delete, 202
async-accepted, POST `.../search` for complex queries),
`two-door-parity.md`, `superpowers/specs/` design specs, `planning/`
(including `gate-ledger.md` and `agent-runbook.md`), and `e2e/` runbooks.

Two distribution clients sit **outside** the box and speak REST or MCP into
the one instance: `extension/` (the browser capture shell) and `sdks/` (the
minimal client, three verbs). **`sdks/ts/src/client.ts` and
`sdks/python/darkmem_sdk/client.py` are generated**: edit `sdks/generate.py`
and run `make generate` in `sdks/`. The generator reads the live OpenAPI
document off the app object and refuses to generate when a verb names a
route, body field or header the contract does not serve (invariant 17).

## UI components come from darkraise-ui first

**Before building any UI, check whether `darkraise-ui` already ships the
component** (~85, including `segment-group`, `number-input`, `switch`,
`toggle-group`, `empty-state`, `sonner`, `dialog`, `card`, `tabs`, `stat`,
`timeline`, `tree-view`, `combobox`, `multi-select`, `date-picker`, ...).
List them with `ls frontend/node_modules/darkraise-ui/dist/components/` and
read the `.d.ts` beside the one you want. Restyling a built-in is
encouraged; re-implementing one is not. A local component is a last resort,
and one written against a library gap **must record which gap** so the next
upgrade can retire it.

## Domain model

Memory rows live in `memories`, with status lifecycle
`active → superseded → deprecated`. The CHECK constraint
`chk_superseded_has_pointer` forbids `status='superseded'` without
`superseded_by`; supersession sets both atomically. `expires_at` is a
nullable TTL swept by `expired_memory_cleanup`. Before deleting any memory
that others reference via `superseded_by` (TTL sweep or interactive
delete), demote those dependents to `status='deprecated'` with
`superseded_by=NULL` first: the FK is ON DELETE SET NULL, so skipping the
demotion violates the CHECK and aborts the whole batch.

A memory carries:

- `content` (Text) and `source` (`mcp`, `api`, ...).
- `project` (Text, default `default`), the supersession scope.
- `memory_type` from `MEMORY_TYPES` in `app.taxonomy`.
- `classified_type` / `summary` / `emotions` / `flags`: classification
  output, populated on every ingest. There is no `llm_` prefix on the
  columns or on any wire surface (REST `MemoryResponse`,
  `app/utils/serialization.py`, the websocket payload), and no compatibility
  shim. There is no regex classifier and no `classified_confidence`.
- `origin_key` (Text, nullable): capture-session identity, the key facts
  count `DISTINCT` on for corroboration independence. Writers: both capture
  doors via `resolve_origin_key` (`api/routes/memories.py`,
  `api/mcp/server.py`, on raw entry dicts for batch adds) and
  `services/auto_research.py`, which stamps **one origin per evidence
  source** (never per run or finding) through `research_origin_id`. That
  canonicaliser collapses scheme, host case, `www.`, default port,
  credentials, trailing/duplicated slashes (scheme-aware; `file:` differs
  from `https:`), fragment, campaign parameters, parameter order, and the
  RFC 3986 §6.2.2–6.2.3 equivalences (percent-encoding, dot-segments,
  punycode through the `idna` package with `httpx`'s parameters, NFC/NFD,
  duplicated identical parameters). It must be **merge-only**: no input
  may split one source into two ids (an overcount fabricates a promotion).
  **Treat merge-only as a tested property, never a structural guarantee**:
  hand-written repairs have repeatedly introduced splits.
  `tests/test_research_origins.py` carries a generator asserting every
  mechanical spelling agrees with the one `httpx` emits; **extend the
  generator before extending the canonicaliser.** Two splits are deliberate:
  `;` vs `&` in a query, and punycode labels that decode to different
  strings. An unresolvable `source_id` falls to
  `unknown:research:<project>`, which counts once and fires no gate; both
  shapes are sliceable via `is_researched_origin`. Two research origins
  both carry `source_kind='memory'`, so they promote only ≥ 7 days apart or
  at three. **No capture response echoes `origin_key`** (absent from
  `MemoryResponse`), so a test asserting it through a capture door asserts
  nothing. It **is** served by `GET /api/v1/knowledge/facts/{id}`
  (`FactSourceGroup.origin_key`).
- `updated_at` is bumped by the **`touch_updated_at` SQL trigger**, not by
  SQLAlchemy's `onupdate`, so a raw-SQL UPDATE moves it too.
- `technologies` (lowercase Text[]): a denormalised cache of entity names
  whose `entity_type` is in `TECH_TYPES`, consulted by the supersession
  detector and the retrieval filter instead of a join.
- `confidence` (REAL, default 0.75): used by
  `HybridSearchService.apply_rank_fusion_factor` when
  `confidence_rank_gamma > 0`.

Entities and relations (`entities` / `entity_relations`) are **not
memory-scoped**: each row carries a `memory_ids` UUID[] of every asserting
memory. Uniqueness is `(entities.name, entity_type)` and
`(source_entity_id, target_entity_id, rel_type)`. Creating one that exists
appends to `memory_ids`; it never inserts a duplicate.

## Taxonomy is closed

`ENTITY_TYPES` and `RELATIONSHIP_TYPES` in `app/taxonomy.py` are the
**only** stored values. Everything the LLM emits passes through
`normalize_entity_type` / `normalize_relation_type`: unknown entity types
become `concept`, unknown relations `RELATED_TO`. `LEGACY_*_TYPE_MAP`
rewrites historical names (`framework → tool`, `RUNS_ON → DEPLOYED_ON`) at
runtime. Adding a type means editing those tables; a free-form value is
silently rewritten.

## Capture is buffered (`memory_buffer`, doc 05 §2)

All four capture doors (REST `POST /memories` and `/batch`, MCP `memory_add`
/ `memory_batch_add`) validate, resolve `source` and `origin_key`, enqueue a
`memory_buffer` row and return **202** with a `CaptureAck`. The ack's id is
the **pre-minted memory id**, carried in the buffer row's `metadata_`; the
buffer row's own id is a separate tracking handle. Never conflate the two.
`wait_process=true` drives that row's flush inline through the same `FOR
UPDATE SKIP LOCKED` claim as the scheduled job and returns the processed
memory (201), degrading to the plain ack after
`buffer_wait_timeout_seconds`. Every capture runs through `capture_lint` (a
pure function: named signals, two or more of them or over 1,500 characters
flags). **A flag never refuses**: the ack carries `warnings`, the 201 path
answers `CapturedMemoryResponse` (`MemoryResponse` plus `warnings`, served
only by the capture routes) or a `warnings` key from the tool, and the
capture journals `capture_flagged` with signal names only. The
`buffer_flush` job drains the queue; its thresholds (`buffer_claim_batch`,
`buffer_max_attempts`, `buffer_claim_visibility_seconds`,
`buffer_done_retention_hours`) are its `config_schema`, in the `config` row
`job:buffer_flush`. A failed batch retries row-at-a-time so the poisonous
row settles alone into `error` with a real `last_error`; a flush overrunning
its deadline returns the batch to `pending`, refunds the attempt and shrinks
the next claim. `error` rows are kept until resolved (the sweep deletes only
`done`) and are triaged over `GET /api/v1/memory-buffer` (REST only; requeue
resets attempts and journals `buffer_requeued`, discard journals
`buffer_discarded`). The claim SQL bounds its batch with a `WITH ... AS
MATERIALIZED` CTE: a plain sub-select lets the planner re-execute it per row
and claim the whole backlog. Don't "simplify" it.
A tick whose every claimed row failed raises `BufferFlushFailed` after the
rows are settled, so the run records `error` instead of `ok`; a tick with
any success reports its counts.

## Pipeline phases (`ProcessingPipeline.process_batch`)

Five phases, each a hard checkpoint:

1. **Content embed.** One chunked embedder call returns
   `(vectors, fingerprint)`. Failure marks every memory `embed=error` and
   skips writes. `_register_fingerprint` runs exactly once before any
   partition write.
2. **Extract + classify.** Per memory, bounded by `pipeline_concurrency`.
   Classification always runs. The classifier is chosen per batch from the
   classification purpose's inline `classifier_kind`: `local` selects the
   in-process classifier, otherwise the LLM-backed one; both expose
   `classify(content, areas, prompt, mode) → {hall, summary, emotions, flags}`.
   **Single-call merge:** with the LLM-backed classifier and
   `classification_mode == 'simple'`, classification folds into the one
   extraction call (`extract(..., with_classification=True)`); the merged
   schema adds `summary`/`emotions`/`flags`, and extraction's `memory_type`
   (the simple-7 vocabulary) is written to `classified_type`. Any other
   config keeps two concurrent calls. Because the merge changes the
   extraction prompt, re-extraction under a different mode or
   `classifier_kind` is not bit-identical even with the same seed.
3. **Entity embed with cache.** Look up `(name_lower, fingerprint)` in the
   memory cache, then the DB cache, then embed the misses and write both. If
   the active embedder rotated since Phase 1, register and switch to the new
   fingerprint.
4. **Dedup.** One ANN probe per unique `(name, entity_type)`:
   `find_similar_entity` is type-constrained at 0.85. A match canonicalises
   only when `names_distinct(lower_name, match)` is False, so names differing
   by a discriminating token (numbers, dates, versions, month names) never
   merge. Record `(name_lower, entity_type) → canonical_name` in
   `canonical_map`; Phase 5 resolves relation endpoints by the same key.
   Probes fan out bounded by `pipeline_concurrency`.
5. **Write.** Per memory, two savepoints: A = vector upsert + memory-row
   enrichment; B = graph + technologies + preexisting-memory supersession, so a graph failure
   does not roll back the vector write.
   - **Strip prior graph contributions (`delete_by_memory_id`) inside
     savepoint B**, as one atomic replace with the write: a B failure rolls
     the strip back, and an extraction failure never enters B. A failed
     strip fails B; never swallow it and write over it. This makes
     re-extraction idempotent. `delete_by_memory_id` deletes a relation only
     when no live memory asserts it, and an entity only when no live memory
     asserts it and no surviving relation references it (the FK cascades).
     The hourly `graph_orphan_cleanup` (`prune_orphan_entities`) is the
     backstop so Phase 4 never merges onto stale ghosts.
   - Apply `canonical_map` to entity names and relation endpoints.
   - Lowercase entity names on write; stash differing original casing in
     `properties.display_name`.
   - Write rows, recompute `memories.technologies` from `TECH_TYPES`
     entities, run supersession excluding same-batch candidates.
   - Compute crossrefs in a separate session after the main commit.

After every Phase 5 write is visible, same-batch supersession reconciles
in `(created_at, id)` order before multi-memory extraction journals.
Then `derive_memory_failed_step` records or resolves a
`pipeline_failures` row per memory, and the websocket broadcasts
`pipeline.completed | partial | failed`.

## Pipeline terminology: never conflate

- **Extraction** builds the entity/relationship graph and is always on.
- **Classification / enrichment** populates `classified_type` / `summary` /
  `emotions` / `flags` and also always runs. The only choice is which
  model-backed classifier serves the `classification` purpose (LLM by
  default, in-process when `classifier_kind` is `local`).

The **only** ingestion-side behavioural flag is `relation_rescue`. Don't
reintroduce a generic ML on/off switch, any `ml_*` flag, a regex
classifier, or a classification on/off flag.

## Supersession (`detect_supersessions`)

Triggered in Phase 5 when the new memory carries a relation in the
**`REPLACES` family** (`REPLACES`, `IMPROVES_ON`, legacy `BUILDS_ON`). The
predicate is one shared function, `supersession.is_supersession_trigger`,
imported by `pipeline.py`; narrowing it is a behaviour change. A candidate
flips to `superseded` only if **all** hold. Preexisting candidates are checked
inside the graph savepoint; same-batch candidates are checked deterministically
after the batch's graph writes become visible:

1. Same `project` as the new memory.
2. Candidate `status = 'active'`.
3. `candidate.technologies` overlaps the lowercased `REPLACES` targets (GIN
   index on `memories.technologies`).
4. `candidate.created_at >= now - SUPERSESSION_WINDOW_DAYS` (90).
5. Candidate is older, with an id tie-break:
   `created_at < new.created_at OR (created_at = new.created_at AND id < new.id)`.
   Same-batch rows share one `created_at`; the tie-break lets within-batch
   supersession fire while blocking a mutual flip that would hide both rows.
6. Speculative gate, per target: only sentences mentioning that target are
   checked for `SPECULATIVE_REPLACES_MARKERS` ("might", "considering",
   "planning to switch", ...), falling back to the whole text only when no
   sentence mentions it.

The detector lowercases targets because `memories.technologies` is
lowercase; change neither side without the other.

## Embedders are partitioned by fingerprint

pgvector needs a fixed-dim `vector(N)`, so each fingerprint gets one child
table per family in `embedder_registry._TABLE_TEMPLATES`: `memory_embeddings`,
`entity_embeddings`, `code_chunk_embeddings`, `entity_embedding_cache`,
`block_embeddings`, `page_embeddings`, `relation_embeddings`,
`article_embeddings`, `triple_embeddings`, `worklog_embeddings` (each
`<family>__<slug>`). `worklog_embeddings` alone gets no HNSW index
(`_EXACT_SCAN_PARENTS`): work-log search scans one project's rows exactly,
through a `project` column copied onto each vector row. The
`embedders` table is the registry; `embedder_registry.register` inserts the
row and runs every `CREATE TABLE IF NOT EXISTS` idempotently. Never name a
child table directly; go through `child_table(parent, fingerprint)`. A
cross-fingerprint join is a bug. `_register_fingerprint` must run before any
insert into a partition.

## Retrieval

With `hybrid_search_enabled`, semantic search delegates to
`HybridSearchService.search`:

- Semantic: `1 - (embedding <=> :vec)` on `memory_embeddings__<slug>`.
- Keyword: `ts_rank` on `memories.search_vector` with
  `plainto_tsquery('english', :q)`.
- Fusion: RRF with `k = 60`, weighted by `semantic_weight` (default 0.7).
  Rows carry `rrf_score` as the ordering signal; the per-modality `score`
  also survives, so consumers must prefer `rrf_score`.
- With `reranker_enabled`, `RerankerService` LLM-scores the top 40 rows
  (0–10; the unscored tail is appended).
- With `confidence_rank_gamma > 0`, `rrf_score` is multiplied by
  `(1 + γ·(confidence - 0.75))`; after a rerank it runs with
  `preserve_order=True`.
- A failed query embed is the semantic arm failing: the keyword arm answers
  alone, the trace reports `semantic_failed`, and the embedder is not dialled
  again for `EMBEDDER_RETRY_COOLDOWN_SECONDS` (60). Both sides down raises.

Code search (`CodeQueryService.search_code`) fuses a vector arm over
`code_chunk_embeddings__<slug>` with an `ILIKE` arm over `CodeSymbol.name` /
`source_code` under RRF (no `ts_rank`; the partitions carry no FTS column).
`RRF_K` is declared only in `app/services/rank_fusion.py`; two AST scans fail
the build on a second declaration. MCP `code_search` and `code_blast_radius`
route through this service.

**Chat retrieval is the same path**: `ChatService` goes through
`LayerCompositionService.search`, whose memory channel is
`HybridSearchService.search_with_trace`, and holds no vector repository.
`tests/test_chat_retrieval_parity.py` asserts parity **on order**, not shape.
Parity is proven only while every rank arm is at weight 0; activating an arm
obliges re-measuring both doors.

Ordinary and traced memory search share `HybridSearchService.search_ranked`.
Both apply all-tag filters and supported hybrid/graph flags, and read
confidence, importance and channel-provided heat/recency for ranking.
Pure-vector mode and SQL fallback match across these memory-search doors.
These correctness tests do not authorize dormant-arm activation or replace
the separate chat-versus-search retrieval-quality measurements.

## Feature flags

Source of truth: the `config` row `feature_flags`. `get_feature_flags_dict`
merges DB values **over** `FEATURE_FLAGS_DEFAULTS` (`app/config.py`). The
pipeline reads through a 5-second TTL single-flight cache
(`_get_feature_flags_cached`); `_flag_cache_reset` is a test hook only.

Behavioural flags: `hybrid_search_enabled`, `reranker_enabled`,
`relation_rescue`, `confidence_rank_gamma`. Graph arms are inert:
`ppr_enabled` / `dual_level_enabled` / `community_injection_enabled` off and
`w_ppr` / `w_dual` at 0. Those two are RRF **list** weights
(`rank_fusion.LIST_WEIGHT_KEYS`), never `RankArm` multipliers, and both doors
derive the PPR weight through `rank_fusion.ppr_list_weight`. The dual-level
channel is built (`HybridSearchService._dual_level_search`) and inert behind
its flag. Each arm's artefact job skips its tick while the arm is off:
`ppr_snapshot` on `ppr_enabled`, `relation_embedding_refresh` on
`dual_level_enabled`. Arming a flag takes effect on the job's next tick, or
at once through a manual trigger. The ranking arms
`w_importance` / `w_heat` / `w_recency` / `w_context_boost` sit at weight 0
and are provably inert there (`rank_fusion.RANK_ARMS`); each flips only on a
measured retrieval win reported with its latency/cost twin and recorded in
the gate ledger's arm activation log.

## LLM configuration

Provider generations are leased from acquisition through request, stream
or job completion, including pre-dispatch awaits, exceptions and
cancellation. Configuration replacement retires old orchestrators only
after their active leases drain. Detached tasks transfer a lease at spawn
and release it even when canceled before first execution; this relies on
the existing single-event-loop/worker contract.

Eight purposes, all live: `embedding`, `extraction`, `classification`,
`reasoning`, `summarization`, `reranker`, `verification`
(`app/services/verification_judge.py`) and `synthesis`
(`app/services/article_synthesis.py`, `SYNTHESIS_PURPOSE`).

**Storage.** Each purpose is one `llm_purpose_configs` row naming a shared
`llm_providers` row through a NOT NULL `provider_name` FK. The purpose row
carries `{model, params, dimensions?, reasoning?}` (plus `classifier_kind`,
`llm` | `local`, on classification); the provider row carries
`{api_kind, base_url, api_key}`. Resolution is **one query with one join**
returning a **flat** `LLMPurposeConfig`
(`tests/test_llm_config.py` counts the queries). Flatness is a correctness
requirement: `benchlib/caching_llm.py`'s cache key and the judge's identity
hash both fold the same six field names off it, so nesting or renaming a
field misses every cache entry and moves the qualified judge identity.
`llm_profiles`, `ml_profiles` and every `*_id` column stay dropped. Purpose
and provider rows are written by the setup wizard's finalize step from
`app/services/llm_seed.py` (`DEFAULT_PROVIDER_ROWS` first, then
seed-plus-overlay), never by a migration. `DEFAULT_PROVIDERS` beside them is
a vendor catalogue written to no table; conflating the two flips a fresh
install's wire protocol. Design: `docs/superpowers/specs/2026-08-20-llm-providers-design.md`.
An old-schema `llm_purpose_configs` dump cannot be restored plainly; use
`backend/scripts/cutover/llm_providers_transition.py` (procedure in
`docs/runbook-deployment.md`).

**The judge's provider.** `app/services/llm_provider_guard.py` refuses a
`PUT` changing `base_url` or `api_kind` on the provider serving
`verification` (they are judge `IDENTITY_FIELDS`; changing them silently
voids the minted qualification). **`api_key` on it still rotates, and
rotation is owed.** The seed gives `verification` its own provider
(`verification-judge`), and the purpose write path refuses to point another
purpose at it; if a restore already shared one, repoint the *other* purposes.

**Judge qualification.** `VerificationJudge.judge()` refuses without a
qualification record for the keyword-only `role` it is called with:
`entailment` (article claim pass; gated on `entailed_precision` /
`entailed_recall`) or `contradiction` (Tier-C scan; gated on the
contradiction pair). `JUDGE_ROLES` partitions `BAR_METRICS` (a test enforces
it); a record qualifies only the role it was minted for, and a bundled
pre-split record qualifies neither. **Today the entailment record is minted
and G-D is cleared on that role alone; the contradiction role is absent and
missed**, so no consumer may ship on contradiction verdicts, and "articles
may ship" does not imply a qualified contradiction judge. A minted record is
not a served label: `judge()` resolves `verification` from the database,
which must hold the row at the qualified identity (`llm_seed.py` seeds a
local Ollama model instead). Tripwire tests refuse relaxing a
contradiction-role bar and any qualification contact with pair set
`4975c5cc`. Numbers, identity and caveats: gate ledger, G-D sections.

**Bars are floors.** `VERIFICATION_BAR_DEFAULTS` (four bars, including
`contradiction_recall_bar` 0.95 and `contradiction_precision_bar` 0.70) are
floors: tightening is free; a `config` row below a floor clamps back with a
warning unless the `verification_bar_licences` row names that parameter,
the lowest value its argument supports and where that argument lives. An
unreadable bar row fails the role closed. G-C's
`scripts/benchlib/promotion_bars.py` uses the same licence shape under
`promotion_bar_licences`, with direction **per bar**:
`verification_false_promotion_bar` is a ceiling (laundering moves it up),
and `promotion_rate_min_eligible` needs a licence in **either** direction.
`promotion_journal_completeness_bar` is read by no predicate. Resolution
returns a `BarReport` (`resolve_promotion_bars` derives from it), and every
run prints per bar the committed value, effective value and *no config row*
/ *honoured* / *CLAMPED*. Bars are the owner's to move with a recorded
argument, never to make a run pass. The qualification runner stamps
`VERIFICATION_BAR_DEFAULTS` directly.

**Vendors.** `api_kind` selects the wire protocol: `openai` (compat),
`ollama` (native, exposes `think:false`), and `anthropic`, `google`,
`deepseek`, `zai` (reserved, dispatched through the compat path). Every
vendor quirk (auth scheme, reasoning-disable knob, structured-output and
seed acceptance, embeddings capability, output-cap key, model-probe
endpoint) is one `VendorQuirks` row in `app/services/llm_quirks.py`; no call
site may compare `api_kind` to a vendor name (a test enforces it). Adding a
vendor is doc 11 §4's four steps: enum, quirk row, doc table, seed.
Embedding on a no-embeddings vendor (Anthropic, DeepSeek) is refused by
`assert_can_embed` (via `LLMOrchestrator._assert_can_embed`). Anthropic needs
`x-api-key` + `anthropic-version`; DeepSeek and z.ai need
`thinking:{type:disabled}`; Gemini's shim honours only
`reasoning_effort=none`; `minimal` is not an OpenAI effort and fails loud.

## Reproducibility

Extraction and classification forward `seed = sha256(content)[:8]` as a
32-bit int. Vendors that honour it (OpenAI, DeepSeek, z.ai, Google compat,
Ollama) return identical JSON; Anthropic ignores it. Removing the seed
breaks reproducibility tests and makes extraction E2E flaky.

## Jobs (`JobRegistry`)

**Twenty-seven** registered jobs (`app/main.py`; `tests/test_code_deriver.py`
derives the roster from its AST). Keep this count and list current when you
add one. Many register via `*_JOB_KEY` constants, so grepping for quoted keys
undercounts.

- **Twenty-one live jobs:** `repo_sync`, `buffer_flush`, `code_enrichment`,
  `code_deriver`, `token_blocklist_cleanup`, `pipeline_failure_cleanup`,
  `graph_orphan_cleanup`, `tag_orphan_cleanup`, `expired_memory_cleanup`,
  `ppr_snapshot`, `relation_embedding_refresh`, `repo_entity_anchoring`,
  `repo_entity_merge`, `citation_reverify`, `job_run_cleanup`,
  `block_embedding_refresh`, `llm_usage_cleanup`, `backup_ship`,
  `page_attachment_cleanup`, `worklog_cleanup`, `mcp_call_cleanup`.
- **Six Tier-C dream jobs** (`app/services/dream_jobs.py`,
  `register_dream_jobs`), all shipped (`SHIPPED_DREAM_JOBS`;
  `test_the_family_holds_no_placeholders_left`): `verification_recompute`,
  `fact_lift`, `contradiction_scan`, `memory_dream`, `article_synthesis`,
  `topic_detection`. A future placeholder must be a `PlaceholderJobRunner`
  (a type a test asserts). **Invariant 15: none of the six may be reached
  from capture or retrieval**; a source scan over `backend/app` fails the
  build.
- `ppr_snapshot`, `relation_embedding_refresh`, `repo_entity_anchoring`,
  `repo_entity_merge`, `code_deriver`, `citation_reverify` and
  `block_embedding_refresh` are Tier C but deliberately **not** dream-job
  members; they are artefact refreshes (doc 07 §4, doc 10 §6, doc 16 §3).
  `block_embedding_refresh` also sweeps page blocks on its own `page_batch`
  budget and work-log entries on `worklog_batch`, the only writer of
  `worklog_embeddings`.

**Scheduling.** Five-field cron is minute-precision; six-field puts seconds
first (Quartz-style). `min_interval_seconds` is a per-job floor the loop
never undercuts. State lives in `config` rows `job:<key>`. Manual
`trigger(key)` takes the **same** per-job `asyncio.Lock` as the loop; a
trigger while it's held returns 409. `set_config`
(`PUT /api/v1/jobs/{key}/config`) validates partial updates against the
job's `config_schema` (type, min/max, unknown keys rejected) under that
lock. A failed run sends the job-failure notification only when its
error differs from the previous run's, so an outage announces itself once
per job rather than once per tick; every run still gets its `job_runs` row.

**Per-job contracts:**

- `repo_sync` also runs the working-tree drift scan (the retired
  `code_reconcile`), per repo, only when both `index_on_commit_enabled` and
  `index_uncommitted` are on (see Code indexing).
- `llm_usage_cleanup` and `mcp_call_cleanup` prune **by age**,
  `job_run_cleanup` **by row count**, deliberately: a row ceiling would shorten "what did the last N days cost"
  during exactly the busy period worth investigating.
- `backup_ship` is the **second** backup producer. It runs the image's own
  `pg_dump` (the runtime stage installs `postgresql-client`, `age`,
  `openssh-client`, `rsync`), encrypts per destination with its `age`
  recipient, ships, **reads every upload back and hashes it**, then prunes
  per destination and artifact family using journalled-success candidates
  whose prospective survivors pass a fresh checksum read-back. Failed or
  unjournalled artifacts never consume the verified retention window and
  remain for inspection; missing evidence can retain extra copies. This
  adds retention read-back I/O. The host timer stays as the floor that survives the app
  being down. Nothing serialises the two producers, so they are kept apart by
  directory (`/srv/darkmem-dumps` vs `/root/darkmem-backups`), prefix
  (`darkmem-app-` vs `darkmem-`) and hour (the job's 04:30 is UTC, since the
  registry evaluates cron in UTC; the timer's 03:30 is host-local, 20:30 UTC
  on this UTC+7 host). Never point them
  at one directory: `backup.sh`'s glob `darkmem-*.sql.gz` matches this
  producer's files (the job's own prune matches only its prefix and never a
  `.part`, so it cannot delete a systemd dump). Destinations and secrets live in the `config` row
  `backup_destinations`, never in `config_schema`. **Size retention against
  a ~250 MB dump**: `block_embeddings__qwen3_embedding_0_6b_1024` is ~665 MB
  of a ~710 MB database (measured 2026-09-02). This host
  runs its `local` destination at `retention_keep=3`, and **no configured
  destination takes data off this host yet** (arming one is an `ssh`, `s3`
  or `worker` destination on the Backups tab). The `age` identity is never
  stored in the database.
- `code_deriver` is the production trigger for
  `code_deriver.assert_repo_graph`: hourly over every repo with a non-null
  `last_indexed_commit`, journalling failures to `pipeline_failures` with
  `pipeline_name="code_deriver"` so a derivation failure never fails an
  index run. Withdrawal: `RepoManager.delete` calls
  `PostgresGraphRepository.strip_repo_assertions` before removing the repo
  row, because `entities.repo_ids[]` / `entity_relations.repo_ids[]` carry
  no FK.
- `citation_reverify` (doc 10 §6's second sanctioned crossing) re-resolves
  each code citation's `symbol_key` against the repo's current HEAD, marks
  unresolvable ones stale, and **enqueues the citing fact for the
  verification recompute, which downgrades the badge and never expires the
  fact** (a deleted symbol may be a rename). It reads the code graph and
  writes the memory-side vault, one direction, no join. It scopes by
  comparing `detail.reverified_at_sha` with `last_indexed_commit`, not by
  changed files, so an unchanged file's citation is re-resolved once per
  HEAD move.
- `repo_entity_anchoring` embeds repo-minted entities one tick after
  derivation (the deriver is LLM-free by structural guard), so Phase 4's
  ANN probe sees them when a memory arrives after the repo.
- `repo_entity_merge` handles the other order: a repo indexed after a memory
  minted a near-named node. `assert_from_repo` is an exact-key
  `ON CONFLICT (name, entity_type)` upsert, so the job re-runs Phase 4's
  comparison (`find_similar_entity` at 0.85 under `names_distinct`, query
  vector read from the partition, so no embedder call). **The survivor is
  the repo-asserted row** (older `created_at`, id tie-break). One savepoint
  per pair moves the `memory_ids` / `repo_ids[]` unions, **every** relation
  endpoint in both directions (a collision on `(source, target, rel_type)`
  is a relation merge: union, keep the greater weight, drop the duplicate),
  the fact layer's identity, and the `technologies` denorm. The loser's
  vectors cascade away; a relation the repointing missed **fails the
  savepoint**. **Facts move by name, not only id**:
  `knowledge_triples.subject_id` / `object_id` have no FK, and `triple_key`
  derives from the lexical endpoint names, so the names and key move with
  the ids, or `fact_lift` mints a second open triple next tick. A resulting
  collision on `ux_knowledge_triples_open` is a fact merge: the higher rung
  keeps the id (`confirmed` > `disputed` > `corroborated` > `candidate`,
  then older `created_at`, then smaller id), no verification column is
  written, `fact_sources` rows are **moved** (never copied), serving heat is
  summed, the belief window takes the earlier `reference_time` / `valid_at`
  / `stated_expiry`, and the duplicate is **expired, never deleted**
  (`expired_at`, not `invalid_at`). A fact whose endpoint id is NULL or
  dangling keeps its name. The scan rotates over repo-asserted entities on a
  `(created_at, id)` keyset cursor in `config` row `repo_entity_merge_state`;
  `candidate_batch` bounds cost, not coverage. Each merge journals one
  `merged` event.

## Events journal (`events`; `audit_log` is gone)

`events` is the sole append-only audit substrate. Every subsystem journals
through `record_event` (`app/services/events.py`), which never raises into
its caller and **returns whether the row landed**.

**Strict callers.** Seven callers read that return and raise on `False`,
making the write and its row atomic: `set_verification_status`, `ratify`,
`record_human_verdict` and `dismiss_contradiction_suspicion` (raise the
vault's `JournalWriteFailed`); `document_door.delete_documents`
(`DocumentJournalWriteFailed`); `page_door._journal_each`, behind page
trash/restore/purge (`PageJournalWriteFailed`); and
`worklog._journal_then_delete`, behind the purge verb and the
`worklog_cleanup` retention sweep (`WorklogJournalWriteFailed`). The
contract is a shape, not a shared type: block-channel modules are
firewalled from the vault and mint their own exception.
`contradiction_scan._journal` (reads its
row back) and `dream_undo` (counts `undone` rows back) hold the same posture
by other means and are not in the seven. Why strict: verification metrics
are SQL over this table, so a lost transition leaves the denominator; a lost
human verdict deletes the audit's only `rejected_after` numerator; a
subtree, page or workstream erase is unrecoverable. `record_event` itself
stays non-raising so capture, extraction and auth survive a journal failure.

**Vocabulary and storage.** `EVENT_TYPES` / `OBJECT_TYPES` are closed
vocabularies beside the writer, **not** in `app.taxonomy`: an unknown value
logs a warning rather than being rewritten. Widening is taxonomy-first. The
table is RANGE-partitioned by month; every partition goes through the SQL
function `events_ensure_partition` (boot reconciliation plus a maintenance
arm on `pipeline_failure_cleanup`). Append-only is enforced by three trigger
kinds: row-level UPDATE/DELETE and statement-level TRUNCATE guards on the
parent, and a per-child TRUNCATE guard stamped by `events_ensure_partition`.
Readers: `GET /events`, `/events/timeline`, `/events/calendar` (its bucket
expression must match `ix_events_day`'s immutable UTC expression verbatim),
and `GET /auth/audit` (filters `auth_*` / `setup_*`). The composite
`PRIMARY KEY (id, created_at)` means a bare `WHERE id = :id` scans every
child, so by-id lookups (undo) carry a `created_at` bound.

**Retention (ruled 2026-08-06).** Journal payloads may carry content
previews that outlive their memory; deleting a memory is not a content
purge, and the DELETE route says so. The residue also includes refine
summaries in `consolidated`/`undone`, contradiction counterparts in
`verified`, `knowledge_triples.fact`, 24h of raw content in `memory_buffer`
done rows, `messages.context`, and every earlier content of a document in
`document_revisions` until the document is deleted. Pasted secrets go through
the operator break-glass procedure `docs/runbook-content-purge.md`, **never an
in-app journal-rewriting path**. **Write-time minimisation is the standing
rule**: a new payload copies content only when a feature demonstrably needs it,
and says so at the writer.

**Dream digest and undo.** `app/services/dream_digest.py` reads the
`consolidated` stream grouped by `payload.cycle_id`, then by object, in
`(created_at, id)` order; never regroup by action kind. **Undo is
all-or-nothing per request with no per-action path**: a single undo is a
batch of one through `dream_undo.undo`, whose module owns no savepoint,
commit or `try` and whose result types can't carry per-item outcomes (an
AST scan enforces all five shapes). Only `UndoRefused` guarantees nothing
was written; any other raise leaves restores in the caller's session for the
caller to roll back (the HTTP door's request session does; an in-process
caller must). An undo whose `undone` rows fall short raises. An undone
subsumption leaves a tombstone at
`memories.metadata.dream.undone_subsume.<counterpart_id>`, keyed on both
`content_sha` values, read at nomination time by `generate_pairs`;
`supersede()` still retires that pair for any caller that asks.

## Verified facts (L2)

`knowledge_triples` is the fact vault, on two independent axes. **Belief**
is the validity window (`reference_time` / `valid_at` / `invalid_at` /
`expired_at`), invalidate-not-delete (`article_citations` takes a hard FK on
that). **Verification** is the ladder `candidate → corroborated →
confirmed`, with `disputed` sideways; `confirmed` is human-only (`ratify` is
its one writer) and the machine's ceiling is `corroborated`.

Memory/code source withdrawal locks affected facts in ID order before
deleting sources and counting survivors, preserving a concurrent witness
and the existing fact identity.

**Corroboration** counts `COUNT(DISTINCT origin_key)` over `fact_sources`,
never rows: N = 3, or 2 when two **attributable** origins differ in
source-kind or lie ≥ 7 days apart. Anonymous origins (NULL, blank,
`unknown:*`) fold into one bucket per fact that counts once and fires no
gate; a citation `citation_reverify` marked stale corroborates nothing
(`LIVE_SOURCE_PREDICATE`). The three thresholds are **floors** in the
`verification_ladder` config row: tightening is free; loosening is honoured
only for parameters named in `ladder_measurements` by a recorded G-C
measurement, else clamped with a warning. Resolution lives in
`app/services/ladder_config.py`, **not** `verification_ladder.py`, because
invariant 15's scan matches any line naming the ladder module; that is what
lets `GET`/`PUT /api/v1/config/verification-ladder` import it.
`verification_ladder` re-exports the moved names. Resolution returns a
`LadderReport`, and the door answers committed value, effective value and
*default* / *honoured* / *clamped* per parameter; a clamped value is still
written. `verification_ladder.decide` is pure; the contradiction veto is
absolute (one non-echo contradiction beats any count). Demotion carries
hysteresis (`verification_demote_grace_cycles`; the `under-sourced` label is
served, never withheld).

**The veto is the deterministic scan only** (doc 08 §4.2, owner-ratified).
`adjudicate_contradiction_finding` runs `CONTRADICTION_DETECTORS` (one
member) on every recompute, judge-free; its `inverse_replacement` arm needs
a stored REPLACES-family edge, and the `single_valued` arm is disarmed
(`SINGLE_VALUED_RELATIONS` is empty). The Tier-C LLM `contradiction_scan`
is **not** a veto input: its verdict reaches the ladder on the separate
`recompute_fact(..., contradiction_suspected=...)` parameter, lands on
`LadderDecision.contradiction_suspected`, and flags the fact for a human
while it keeps its rung, badge and retrieval place. Never route it into
`open_contradiction`. It dead-ends on the unqualified contradiction judge,
so today it produces nothing.

**`review_state`: four openers, one derivation.**
`verification_ladder.REVIEW_OPENERS` (disputed, under-sourced,
contradiction-suspected) plus doc 09's ungrounded articles in another
table. `derive_review_state` is total; the clear is the absence of **every**
opener. Adding one is appending a predicate, never adding a writer. The
suspicion rides `contradiction_suspected_at` /
`contradiction_counterpart_id`, written by the ladder in the **same UPDATE**
as `verification_status` (as `demotion_pending_since` is for
under-sourced), refreshed every recompute, so it self-clears; `since` is
when it opened. Never read the finding from the queue (that puts an
`app.services.contradiction_veto` import on a read surface, which the
invariant-15 scan fails). A human dismissal journals `contradiction_dismissed`,
its own event type, **not** a fifth `HUMAN_VERDICTS` value (those
adjudicate the fact; this adjudicates the finding). Clearing the column
alone is undone by the next recompute.

**Journalling.** `KnowledgeTripleRepository.set_verification_status` writes
the `verified` events for every ladder transition (before/after status and
the full decision evidence: `outcome`, `origin_count`, `required_n`,
`gate_fired`, `source_kinds`, the two blocked flags, the contradiction
counterpart). Ordinary holds journal nothing; contradiction- and
supersession-blocked holds do. `ratify` is a **second** writer of the
stream (`set_verification_status` refuses `confirmed`); consumers such as
`promotion_metrics.py` must expect both. `_write_born_rung` (deriver birth
and post-dispute restore) writes `corroborated` with no journal row; G-C
metrics knowingly exclude those.

**Labels are gated by evidence records, never by code** (`claim_gates`). A
promoted fact status reaches readers only while
`app/services/promotion_metrics_record.json` exists with `gate_eligible`
exactly `true`, minted only on a cleared G-C verdict (the runner never mints
it). **G-C is cleared and the record is minted**, so promoted and born
statuses are served. `groundedness_gate` is G-D's and **stays closed**: no
article may be served labelled grounded. The false-promotion audit scores
the **95% Clopper-Pearson upper bound** against the 0.01 bar; the point
estimate is context only. `audit_clears` takes **counts, not a rate**, and
`false_promotion_min_corroborations` (20) is subsumed by the bound. The
audit has two arms, `disputed_after` (judge-free; fed only by the
deterministic detector) and `rejected_after` (the LLM scan's only route in,
through a human confirming a flag). Bars live in
`scripts/benchlib/promotion_bars.py` (pinned defaults; moving one is a
visible two-file diff); metrics are SQL over `events` in
`benchlib/promotion_metrics.py`. Every measured figure, and what the clear
does **not** license: `docs/planning/gate-ledger.md`, G-C sections.

## MCP endpoint

`/mcp` speaks MCP revision `2026-07-28` on `mcp==2.1.1`; the server object
is `MCPServer` (`app.api.mcp.server`), not `FastMCP`. **Every call requires
`Authorization: Bearer dmk_<key_id>_<secret>`**, with no disabling flag.
Auth runs before the Host allowlist: an unkeyed request gets `401`
regardless of `Host`; only a keyed request failing the Host check gets
`421`. Localhost is always allowed; `MCP_ALLOWED_HOSTS` (comma-separated,
`192.168.0.195:8000` or `host:*`) adds LAN hosts; `*` disables the check.
Fix a LAN 421 by extending the allowlist, never by disabling either guard.
Browser Origins are allowlisted to the same hosts. `memory_batch_add`
mirrors the HTTP 1–100 batch cap. To exercise a local deploy, call `/mcp/`
directly with a script (the trailing slash matters); don't repoint the
session's MCP client config.

**Scopes are per tool** (`app/api/mcp/scopes.py`, `TOOL_SCOPES`, 46 tools):

- `capture` (14): `memory_add`, `memory_batch_add`, `memory_update`,
  `memory_delete`, `document_put`, `document_update`, `document_delete`,
  `research_run`, `worklog_append`, `worklog_update`,
  `block_update`, `block_insert`, `block_move`, `block_delete`.
- `read` (29).
- `admin` (3): `code_reindex` (the only MCP write door into the code
  subsystem; `docs/superpowers/specs/2026-08-28-file-scoped-reindex-design.md`),
  `document_delete_subtree`, `worklog_purge`.

Scopes don't imply one another. The subtree delete is a separate `admin`
tool, not a mode on `document_delete`, because a mode would inherit
`capture`. Its REST twin `POST /api/v1/documents/delete` sits behind
ordinary login auth, like every document route except the six a
dr-forge mirror syncs through (filing, the single-document metadata
PATCH, the by-uri read, the manifest and the two revision reads, which admit
a scoped key). That asymmetry is
deliberate and recorded on `docs/two-door-parity.md`'s `documents.write` row.
`ratify` is outside the scope vocabulary: no MCP tool reaches `confirmed`.
`tools/list` is deliberately **not** scope-filtered. A keyed capture stamps
`events.api_key_id` and `events.actor` on the journalled row.

**Call log.** `ToolScopeMiddleware` hands every `tools/call` (allowed,
errored or scope-denied) to `app/services/mcp_call_log.py`, which buffers
in-process and writes `mcp_tool_calls` rows from one background task; a log
failure never reaches the call, and read-only mode records nothing. Arguments
are minimised at write time: `CONTENT_ARGS` become sizes, `QUERY_ARGS` are
kept only while `mcp_call_cleanup`'s `log_query_text` is 1, and results reduce
to a count plus up to 50 ids. It is not `events` (read traffic needs age
retention, which the journal forbids). Read through `GET /api/v1/mcp-calls`
and `/summary` (REST-only, login) on Activity → MCP calls.

**Source resolution.** Memory writes resolve `source` per call: explicit
arg (the literal `mcp` counts as unspecified) > `X-Darkmem-Client` header >
User-Agent product map > `mcp`. `memory_batch_add` resolves on the **raw
entry dicts before validation**. `MemoryCreate.source` has no default; keep
it that way and keep raw-dict resolution. A post-hoc resolution passes on
REST (where `api` is REST's own sentinel) but fails on MCP
(`'api' != 'codex'`). `source_agent` defaults to the raw User-Agent.

**`research_run`** (F7, doc 09 §6) is MCP-only by design: it files evidence
the **caller** gathered, because `ResearchGatherer` has no in-tree
implementation and no REST caller can be a gatherer. There is no
`JobRegistry` job (a cron'd pass would refetch its own sources and
manufacture corroboration). The tool takes **no `source`, `origin_key` or
`ctx`**: every row carries `RESEARCH_SOURCE` and an `is_researched_origin`
key, and a finding naming either field is a validation error. It refuses
while the `auto_research` row is not enabled; production is armed
(2026-08-17), but nothing produces a research origin unless an MCP agent
with web access calls the tool. `tests/test_auto_research.py` records it as
the one sanctioned invariant-15 crossing via `exempt_node_ids`, scoped to
the tool's own body.

## Setup, auth, runtime config

- `/api/v1/setup/*` is trust-on-first-use, gated only by
  `require_uninitialized` (403 once `admin_password_hash` exists). Never
  reintroduce a pre-setup shared secret (`SETUP_SECRET` is gone).
- Login rate limiting is per IP with lockout. With `trust_proxy_headers`
  off (default) the transport peer wins and no header is read; with it on,
  `X-Real-IP` wins and the **rightmost** `X-Forwarded-For` hop is the
  fallback. The leftmost hop is never read. **Every launch path passes
  `--no-proxy-headers`** (`entrypoint.sh`, `scripts/start_dev_server.sh`,
  `docker-compose.dev.yml`'s `command:`, and both `command:`s in
  `docker-compose.worker.yml`), because
  uvicorn's `ProxyHeadersMiddleware` would otherwise rewrite the peer for
  loopback clients. Refresh and change-password rotate (blocklist) the
  presented token; a password change revokes all pre-change tokens via the
  `iat` check.
- Password creation/change validates at most 72 UTF-8 bytes, without
  truncating existing hashes. Oversized login inputs fail normally and
  participate in failed-attempt handling. REST and WebSocket handshakes
  share session validation; established sockets revalidate before sending
  and at one-second idle intervals for expiry, epoch change and revocation.
- `DATABASE_URL` is derived from the `DB_*` vars (percent-encoded); an
  explicit `DATABASE_URL` overrides. There are no `LLM_*` env vars; LLM
  config lives in the database via the setup wizard.
- `cookie_secure` is tri-state in the LAN posture (unset = Secure only when
  `environment=production`; explicit false allows plain-HTTP LAN login).
  **`trust_proxy_headers` is the exposed-deployment switch**: with it on,
  `cookie_secure=false` is **clamped** to true, reported by a boot warning,
  `session_cookie_secure_clamped`, and `cookie_secure_clamped` on
  `GET /auth/security-posture`. Procedure:
  `docs/runbook-exposed-deployment.md`. **Never route `/mcp` from the public
  side**: the app refuses proxied `/mcp` calls even with a valid key, and MCP
  auth has no lockout (every attempt costs a bcrypt on the shared thread
  executor).
- `SECURITY_HEADERS`' `img-src` is `'self' data: https:`, and
  `frontend/nginx.conf` must match it character for character
  (`tests/test_edge_response_policy.py`). `http:` is deliberately absent so a
  pasted note cannot beacon a third party in cleartext.

## Live model endpoints (dev machine)

**Keys are never in this file or any tracked file.** They live in
`.claude/local-credentials.md` (gitignored). Read it when a bench, gate or
qualification pass needs a key, and export it. Both keys were exposed in a
chat transcript; rotation is owed before publication, and the owner has
deliberately deferred it (don't list it as a blocker).

- **Extraction / classification / reasoning: DeepSeek.**
  `base_url=https://api.deepseek.com/v1`, `api_kind=deepseek`. Models
  `deepseek-v4-flash` and `deepseek-v4-pro`. **The F1 baseline and every gate
  re-measurement use `deepseek-v4-flash`**; a `-pro` run is not comparable.
  Export `DEEPSEEK_API_KEY` for `run_bench.py` and `benchlib/run_smoke.py`.
- **G-D judge: OpenAI** `gpt-5.5`. `base_url=https://api.openai.com/v1`,
  `api_kind=openai`. Export `OPENAI_API_KEY`; `run_judge_qualification.py`
  takes the key as an argument and model/base_url/api_kind as overrides, so a
  judge swap moves the identity hash. **A judge credential only**; never point
  it at extraction or classification.
- **Embeddings: Ollama on the LAN**, `http://192.168.0.196:11434`,
  `api_kind=ollama`. Switching models is an embedder rotation (new
  fingerprint, new partitions), not a config tweak:

  | Model | Dims | Context |
  |---|---|---|
  | `nomic-embed-text:latest` | 768 | 2048 |
  | `qwen3-embedding:0.6b` | 1024 | 32768 |

  DeepSeek has no embeddings; `assert_can_embed` refusing it is correct.

## Code indexing

Parser reads resolve both the repository root and file target and reject
targets outside the root, including escaping symlinks; internal symlinks
remain supported. Explicit-file classification rechecks containment before
hashing. Git diagnostics redact URL userinfo for every forge, including
checkout warnings and formatted timeout tracebacks. This is not a
descriptor-based sandbox against concurrent hostile filesystem mutation.

Incremental import resolution uses every surviving indexed repository file,
while parsing, rewriting, embedding and phase-08 benefit accounting retain
their incremental work subset. Direct binding metadata persists on file
graph nodes; missing legacy metadata is reconstructed through the checked
parser without rewriting or embedding unchanged files. Code-search fusion
identity is `(repo_id, file_path, line_start)`, never path/line alone.

`POST /repos/{id}/reindex` accepts `{full, enrich_symbols, generate_wiki}`,
all default false. An unchanged HEAD short-circuits unless `full=true` **or
the repo carries index debt**. Enrichment and wiki generation run only when
toggled; `GET /code/wiki` never generates.

An incremental run re-traces the callers of every changed file (re-indexing
a file deletes every call edge into it), capped at `DEPENDENT_RETRACE_CAP`
(500). Callers past the cap are **persisted to `repositories.index_debt`,
never dropped**. Later runs fold a bounded batch (`config` row
`code_index_debt`, default the cap) back into their changed set; a batch
leaves the queue only after the run that re-traced it succeeded. Debt files
are only added (their hash is unchanged, so phase 03 skips them and the
drain deletes nothing). Deferral and drain journal a `repo_indexed` event and
surface on `RepoResponse.index_debt`.

A claim (`status` `indexing` or `cloning`) outlives the process that took
it: a run resets its status only in handlers a cancellation never reaches.
Boot therefore calls `RepoManager.release_interrupted_runs` before arming
jobs, moving each claimed repo to `stale` (or `error` when it was never
indexed). That is safe only under the single-worker invariant.

Debt alone does not trigger a recurring poll at unchanged HEAD. Drain it
through a later HEAD-triggered run or manual reindex; manual runs bypass
the unchanged-HEAD shortcut when debt remains.

**Every recurring indexing behaviour is a per-repo switch, all default
off**: `fetch_enabled` (`fetch_interval_seconds`, default 300s, floor 30s),
`index_on_commit_enabled` (`commit_poll_seconds`, default 60s, floor 15s)
and `index_uncommitted`. `HEAD` is the single indexing trigger; fetching is a
separate lane whose only job is moving `HEAD`, and the recurring index lane
never fetches (`CodePipeline.run(..., pull=False)`), so it can't
fast-forward the operator's branch or reset over drift.
`index_uncommitted` has no lane of its own: it only widens the commit-poll
tick (`job_runners.make_repo_sync_runner` checks `index_on_commit_enabled`
first), so it does nothing while that switch is off. **Manual reindex, the
push webhook and MCP `code_reindex` bypass every switch** and keep
fetch-then-index.

## Documents (`app/services/document_door.py`, block channel)

A document is filed markdown or plain text parsed into a `blocks` tree
(headings, paragraphs, lists, code, quotes, tables and rows, dividers, raw
`html`). It is **never** run through the memory pipeline and never extracted
into memories or facts; it is parsed, embedded and retrievable. PDF parsing
exists but `content` is `str` on both doors, so a PDF is a designed 422.
`tests/test_block_pipeline.py` fails the build if `app.services.pipeline` is
reachable from this module or `block_pipeline`.

**Identity and verbs.** `(project, uri)` is a document's identity:
re-filing the same path updates the row in place (unlike memory capture,
which always appends). All verbs are on both doors (REST and MCP) and call
the same `document_door` functions; targets resolve through
`resolve_document_target` (id or `(project, uri)`).

- **Five core verbs**: `put`, `search`, `outline`, `get`, `delete`
  (`POST /api/v1/documents`, `POST .../search`, `GET .../{id}/outline`,
  `GET .../{id}` and `by-uri` twins, `DELETE .../{id}` and
  `DELETE .../by-uri`; MCP `document_put`, `document_search`,
  `document_outline`, `document_get`, `document_delete`).
- **Metadata**: `PATCH /api/v1/documents/{document_id}` (title, uri, pinned,
  tags) and `POST /api/v1/documents/rename` (a `uri_prefix` subtree, answers
  the count). MCP carries both as modes of `document_update`, dispatched on
  `document_id` vs `uri_prefix` (refusing both or neither). A rename onto a
  taken `(project, uri)` is refused: 409, or a `uri_conflict` envelope. The
  single-document mode takes an optional `expected_hash`, carried in the
  writer's own UPDATE (a stale hash answers 409, or a `hash_conflict`
  envelope, and moves nothing), and its PATCH admits a `capture` key: the
  dr-forge mirror archives a deleted document that way. Tags
  are bounded by `validate_tag_lengths` before any write
  (`PostgresTagRepository.get_or_create` validates nothing); that validator's
  `ValueError` escapes the tool as a tool error, not an envelope.
- **Subtree delete**: `POST /api/v1/documents/delete` and MCP
  `document_delete_subtree` (`admin` scope; see MCP endpoint) erase every
  document under a `uri_prefix` and answer the count. An empty prefix is
  refused. Each removed document journals a `documents_deleted` row
  **before** the `DELETE` (a strict caller). The single delete journals
  nothing, deliberately.
- **Prefix predicate** (shared by subtree rename, subtree delete and the sync
  manifest `GET /api/v1/documents/manifest`, which strips a trailing slash
  and reads an empty prefix as the whole project): `uri = prefix OR
  left(uri, len+1) = prefix || '/'`, unnormalised. A leading-slash uri
  (`/notes/a.md`) matches at no level; a doubled slash or a scheme's `//`
  matches only at folders above the anomaly; a trailing slash always
  matches. An empty prefix would match only `''` and leading-slash uris,
  which is why it is refused.

**Content, hashes and bounds.**

- `documents.content` is the stored source of record (verbatim for text,
  NULL for bytes); `content_hash` is the change gate; `blocks.char_span`
  indexes into `content`. `include_content` (default off) adds `content` to
  `GET /documents/{id}` and its `by-uri` twin; on MCP `document_get`,
  `include_content` and/or `include_hash` box the reply into an object
  (`content`, `content_hash`, `blocks`). One service read,
  `document_door.document_content`, serves both doors.
- `MAX_CONTENT_CHARS` (1,000,000) is checked before any parse or write;
  `MAX_BLOCKS` (5,000) after parsing, inside a SAVEPOINT around the filing,
  so `DocumentTooLarge` rolls back the row, blocks and `document_filed`
  event.
- **`put` takes an optional `expected_hash` compare-and-set** carried in the
  writer's own UPDATE with a rowcount check (never read-then-compare). A
  stale hash answers 409, or a `hash_conflict` envelope
  (`DocumentHashConflict`); `PutResult` echoes `content_hash`. A
  byte-identical re-push with a stale hash is a conflict, not `unchanged`.
  Omitting it keeps last-writer-wins; batch ingest takes none.
- **An edit re-embeds the whole document**: re-filing strips every block and
  inserts a fresh set with new ids. There is no diffing and no per-block
  identity across a re-file.
- **Revisions** (`document_revisions`): `document_ingest`'s filing body, inside
  its SAVEPOINT, writes the filed `content` as a post-image row stamped with
  `actor`, `api_key_id` and `clock_timestamp()` whenever the filing changes
  the row's `content_hash` (a filing that resolved no row compares with the
  newest revision under the row lock, so two racing first filings of one
  content write one), so the newest revision equals `content` until a block
  verb edits it or a bytes filing leaves `content` NULL. An unchanged
  re-push, a stale `expected_hash`, a forced reparse of identical bytes, a
  bytes source and every block verb write none, and a
  refused put rolls its revision back. Reads come newest first, pages carry
  no content and page back through `before` (a revision id):
  `GET /api/v1/documents/{id}/revisions` and `.../revisions/{revision_id}`
  (both admit a read key) and MCP `document_revisions` (by id or
  `(project, uri)`; `revision_id` fetches one with its content). Revisions
  cascade with their document.
- **`unchanged` still embeds**: a byte-identical re-push returns `UNCHANGED`
  without touching blocks, then embeds any of the document's blocks missing
  a vector under the **active** fingerprint, so re-pushing repairs a failed
  embed. Resolving the active fingerprint costs one real embed call per
  `unchanged` re-push, unconditionally.
- **`embed_inline=False`** (the board's register edit) returns once the
  filing commits and embeds nothing, so `llm` may be None and an embedder
  outage cannot fail the write; `block_embedding_refresh` embeds the new
  blocks within the hour.
- Delete removes the row and cascades blocks and vectors. Nothing links a
  block to a fact, so there is no provenance to withdraw.

**Content-first vs block-first** (`documents.properties.ingest_direction`,
absent = content-first). The first block verb **converts** a document,
deriving discarded markers from `content` through each block's `char_span`.
After conversion `document_put` at that uri is **refused** (409, or a
`direction_conflict` envelope), under a `SELECT … FOR UPDATE` on the
document row that the block verbs also take. Conversion **refuses rather
than converting lossily** (`DocumentNotConvertible`): when
`block_serializer.reproduces_source` finds a link-reference definition in
the parser's `env`, or a construct present in `content` but missing from the
tree (a document filed before its block type existed). **Widening a block
type therefore obliges a reparse, not merely a redeploy**, and re-running
the importer does not reparse: `content_hash` short-circuits unchanged
content. Use `backend/scripts/reparse_documents.py` (sets `force_reparse`,
re-files from `documents.content`; `--project`, `--uri`, `--limit`,
`--dry-run`); no door sets `force_reparse`.
`reproduces_source` compares token kinds and counts, not a full round trip;
`ROUND_TRIP_SOURCES` pins the serialiser's known cases. One known **parser**
defect remains: a blockquote's paragraph children fold into the quote's own
`text`, so a round trip moves them ahead of a sibling heading (no text
lost). Fixing it obliges a reparse.

**Block verbs** (`app/services/block_verbs.py`): `block_update`,
`block_insert`, `block_move`, `block_delete`, on both doors for documents
and REST-only for pages (via a `BlockOwner` descriptor). They refuse
registers and plans (`superpowers/registers/`, `superpowers/plans/`) after
the row lock with `DocumentMirrorOwned`, a `DocumentNotConvertible` (REST
422, MCP `not_convertible`): the dr-forge mirror owns those documents
through content puts, and the SPA offers no edit mode for them. Each runs one pass:
lock, load tree, mutate in memory, serialise, write placement and owner row
in a SAVEPOINT, journal `blocks_edited` (no block text), commit, then embed
**only** the touched block for a document. A page write embeds nothing
(`BlockOwner.embed_inline`): an update that changes a block's text or type
deletes its `page_embeddings__<slug>` rows for every fingerprint with
`retired_at IS NULL` in the same savepoint, so the hourly sweep refills it.
`char_span` is recomputed in the same pass. All four verbs take an optional
`expected_hash`, compared **after** the row lock; a stale hash answers 409 /
`hash_conflict` and writes nothing (on `DELETE .../blocks/{block_id}` it
rides the query string). The blocks read always serves `content_hash`, and
MCP `document_get` takes `include_hash`, so each read or write's hash
preconditions the next write.

The document editor removes structural ancestor prefixes before promoting
its supported blocks, including compact imported quotes, and nested
insert-after preserves the predecessor's parent. Chat streams belong to
their originating conversation; completion cannot reclaim a newer route
selection. Send errors expose a retryable draft only for definite
rejections, while uncertain delivery warns against duplicating an already
stored turn. Recovery is in-memory, not idempotent replay or crash storage.

Block embedding responses revalidate current text under owner locks before
writing; stale provider responses are discarded. A page-refresh sweep
reports convergence only when no skipped embedding gaps remain.

**Two-door ruling (2026-08-23).** `documents.write` and
`documents.retrieval` are two-door; `docs/two-door-parity.md` is the audit
of record. This clears no gate. `POST /api/v1/documents/qa` stays
single-door and G-F-gated; `documents.reads` (list, summary, connections)
stays REST-only.

## Pages (`app/services/page_door.py`, second owner of `blocks`)

Design: `docs/superpowers/specs/2026-09-08-pages-notion-model-design.md`. A
page is the operator's note in a per-project tree (`pages`, composite
`(parent_id, project)` FK). `blocks` has nullable `document_id` and
`page_id`, and `blocks_exactly_one_owner` (`num_nonnulls(...) = 1`) refuses
an ownerless block. Document statements exclude page blocks by NULL
semantics; `tests/test_page_document_isolation.py` asserts it across
document search, connections, outline, the document block routes and the
embedding sweep. Page vectors live in their **own `page_embeddings__<slug>`
family** (a shared partition would let page rows crowd document hits out
of the post-filtered HNSW stream).

Attachment reference writers and placement acquire a global shared
transaction lifecycle lock before root/owner locks; collection acquires
the exclusive form. Writers revalidate attachment URLs under that lock,
refusing already-collected references. Collection's filesystem phase and
rowless scan/unlink cannot invalidate a committed reference. Import/upload
cleanup preserves placed bytes when commit or rollback outcome is
uncertain; only proved-uncommitted bytes are removed after a successful
precommit rollback. Raw SQL/admin changes bypassing this protocol are not
covered; new writers must join it.

**REST-only, sixteen routes**: thirteen in `api/routes/pages.py`, two
attachment routes in `api/routes/page_attachments.py` (upload and serve;
files on the `attachment_data` volume at `ATTACHMENTS_DIR`), and
`POST /api/v1/pages/import/notion` in `api/routes/page_import.py`. There is
no MCP tool and no scope; they are recorded as `pages.*` single-door rows on
`docs/two-door-parity.md`.

- **Block-first by construction**: create stores the serialiser's output; a
  create carrying source the tree can't hold (frontmatter fence, link-reference
  definition) is refused 422. Create **flattens heading nesting** (a block
  under a heading moves to the nearest non-heading ancestor), because only
  `list`, `todo` and `toggle` hold children (a `table` holds `table_row`s);
  the verbs refuse other parents with `PageBlockInvalid` → 422.
- Page-only block types `todo`, `toggle`, `callout` live in
  `PAGE_BLOCK_TYPES` (normalised by `normalize_page_block_type`), with
  required properties (`checked`, `variant`) checked on the merged block;
  a type change drops keys the new type doesn't define. Emit forms
  (`- [ ]`, `<details>`, `> [!NOTE]`) are write-only.
- A block insert may name its own `block_id` (409 when taken);
  `POST .../blocks/batch` inserts many in one pass; block delete answers the
  new hash in `X-Content-Hash`; `GET /pages/trash` lists trashed subtree
  roots. Nothing embeds a page inline; the sweep does.
- Delete is a **soft delete** of the subtree (`deleted_at`), restore clears
  it, and only emptying the trash runs the real `DELETE`. All three journal
  one row per page before writing (strict caller), under
  `object_type='page'` and six `page_*` event types.
- Page blocks share the `blocks` heap with document blocks on a host where
  autovacuum never runs; bulk rewrites need a manual `VACUUM` on `blocks`
  and the embedding partitions.

**SPA `/notes`** (`features/notes/`) is the page tree's only surface: sidebar
tree (drag-to-reorder via `PATCH /pages/{id}`, create, rename, soft delete,
trash sheet) and a lazy-loaded **BlockNote 0.54.2** editor
(`docs/superpowers/specs/2026-09-18-pages-increment-b3-blocknote-editor-design.md`).
- Its save engine (`features/notes/lib/page-sync.ts`) diffs the editor
  document against the last server-acknowledged tree, canonicalising both
  through the editor mapping, and sends one block write at a time that a
  local mirror of `block_verbs.py`'s refusals (`lib/sync-tree.ts`,
  `lib/block-properties.ts`) says will be accepted. **Change a page rule in
  `block_verbs.py` and change the mirror with it.**
- Stopped retries do not clear unsaved work: refused/conflicting drafts stay
  in the module registry across same-tab navigation and reopen read-only.
  Copy retained content before explicit **Discard draft and reload**.
  Module-lifetime unload protection checks retained drafts and in-flight
  uploads even after every pane unmounts; this is not durable crash recovery.
- An update sends a **fixed property key set per type** regardless of value,
  since the server merges properties and never clears an omitted key.
- Inline markdown the editor can't show rides as a `rawInline` atom written
  back byte for byte; `emitInline` drops marks until its output reads back
  as its input.
- A paragraph that is exactly one image, or one link to an attachment,
  renders as a BlockNote `image`/`file` block and is stored as that
  markdown; `page_attachment_cleanup`'s reference scan reads it, so the
  mapping and that job's pattern move together.
- Uploads go through `POST /api/v1/pages/{id}/attachments` (paste, drag-drop,
  slash menu). In-flight uploads are counted module-wide, outside the sync
  tree, for the unload warning; an upload resolving after its pane unmounts
  is lost.
- "Import from Notion" derives hierarchy from database membership and
  standalone links (a sample export lives at
  `/root/notion-export/export.zip`, outside the repo).
- `ProjectWorkspace` is the corpus browser. **The personal project's
  documents are visible nowhere in the SPA** (owner ruling); they stay
  reachable over REST and MCP.

## The block firewall

A block row (document or page) is retrievable only through the document
verbs and page routes. It is never fused into `HybridSearchService` or
`LayerCompositionService` ranking and never lifted into the graph or the
fact vault; there is no route from a block to a fact.
`tests/test_block_retrieval.py` enforces it structurally, with three scans:

1. **Retrieval**: walks the fusion modules' imports and the composition's
   channel and id-kind registries; fails if a block becomes reachable.
2. **Vault**: walks the import closure of every module that **mints,
   promotes or synthesises from** a fact (the `VAULT_WRITERS` seeds) and
   fails if one can reach a module that reads a block row. The root is
   minting, not "touches `knowledge_triples`"; a raw-SQL derivation of vault
   writers is a staleness guard on the hand-written seed list, not the rule.
3. **Methods**: every block-channel module may name only
   `KnowledgeTripleRepository.as_of`, `get`, `get_live`, `list_live`. Any
   other method, including one added later, is forbidden until classified.

## Work log (`app/services/worklog.py`)

A coding client's working data (self-summarised checkpoints, ledger chunks,
notes to its next session) lives in `workstreams` / `worklog_entries`, never
in `memories` (`docs/superpowers/specs/2026-09-23-work-log-lane-design.md`).
Entries are append-only from the API and ordered by `seq` (identity), never
`created_at` (one append shares `now()`). A `ledger` entry's body is the
exact appended text, so concatenating a workstream's ledger entries
reproduces its file. The run key resolves through `worklog.resolve_run_key`
(capture's derivation, doc 05 §2.1); an undeclared run is refused, never
merged into an `unknown:` bucket. An append locks the workstream row
(`SELECT … FOR UPDATE`, or the creating insert) first, serialising it
against purge and retention deletes. An optional `expected_last_seq` makes
the append a compare-and-set on the newest entry of its one kind (0 when
there is none), checked under that lock: a mismatch raises
`WorklogSeqConflict` inside the savepoint, so nothing is written, created or
reopened, and answers 409 / `seq_conflict`. Every append answers `last_seq`.
`worklog_purge` and its REST twin are `admin`-scoped and strict-journal;
payloads carry the workstream key and counts, never entry text. The daily
`worklog_cleanup` job (`retention_days`, default 90) erases each closed,
unretained workstream closed longer than that, one transaction each,
through the purge's journal-first helper (payload adds `retention_days`);
open and `retain` workstreams are never swept, and `SKIP LOCKED` passes
over one an append holds. Nothing in the lane is extracted, ranked with
memories or reachable from the vault.

`worklog_search` (REST `POST /api/v1/worklog/search`, `read`) takes a
required project and fuses, by RRF at equal weights, a `ts_rank` arm over
the whole body and an exact cosine arm over the first 8,000 characters
(`worklog_embeddings__<slug>`, filled only by `block_embedding_refresh`).
With no orchestrator, a read-only instance or a failed query embed the
keyword arm answers alone and the answer says `semantic_ran: false`.

## Progress board (`app/services/board*.py`)

Spec `docs/superpowers/specs/2026-10-13-notion-progress-board-design.md`.
The Progress tab's board is a **projection, never a store**: every read
derives register rows (`superpowers/registers/*.md`) and plan tasks
(`superpowers/plans/*.md`) from `documents.content` and the ledger entries'
`task` / `state` / `commit` properties; a ledger without them reads as
untracked. `board_parse` holds the pure parsers, which mirror dr-forge's
`plan.sh` / `register.sh` (fences, escaped `\|` cells, `is_task`): change
both sides together. `board` reads and sits inside the work-log wall, so it
must never import `document_door` (its closure reaches a memory model).
`board_edit` is the one write: a register row edit spliced into the original
line, never re-serialised, and filed through `put_document` with the
caller's `expected_hash`, no `properties` and `embed_inline=False`, so a
racing writer gets 409 `hash_conflict` and no edit waits on an embedder.
Plan-task state is read-only (the ledger is the plugin's). Refusals are
`BoardRefusal`, answered with `error.code` = the reason. Six REST-only login
routes under `/api/v1/board` (`board.reads` / `board.write` on the parity
doc); `GET /records` serves a weak ETag with `Cache-Control: private,
no-cache` and answers 304 from two aggregates. Saved views are `board_views`
rows (revision `0003`); the two built-ins are code constants with `builtin:`
ids and refuse writes.

## Cross-cutting invariants

- **memory_id type drift.** Hybrid search returns string ids; the vector
  repo returns `UUID`. Normalise at every boundary or matches drop silently.
- **Lowercase entity names** on disk, original casing in
  `properties.display_name`. Supersession and the `technologies` denorm
  assume lowercase.
- **No cross-fingerprint joins** on embedding tables.
- **Idempotent re-extraction.** Strip prior `memory_id` graph contributions
  before writing a new set.
- **`technologies` is lowercase, denormalised, GIN-indexed.** Dropping any
  one breaks supersession or retrieval.
- **REPLACES family.** `REPLACES`, `IMPROVES_ON` and legacy `BUILDS_ON`
  collapse to one bucket via `family_key` for rescue dedup **and** are the
  supersession trigger. A new replacement relation goes into
  `REPLACES_FAMILY`.
- **Async session lifetime.** Never open a fresh session while the request
  transaction holds locks on the same rows; commit first.
- **asyncpg needs CAST on raw-SQL params** whose type Postgres can't infer
  (`CAST(:vec AS vector)`, `CAST(:id AS uuid)`, `CAST(:props AS jsonb)`),
  especially with variadic ANY / unnest / jsonb_build_object, or you get
  `IndeterminateDatatypeError`. Roll back the session before mutating ORM
  objects in an error handler.
- **Single worker (invariant 13).** Exactly one uvicorn worker and one
  replica on every launch path. None of `--workers`, `WEB_CONCURRENCY` or
  compose `deploy.replicas` may appear in an ops change. The WebSocket
  fan-out, the job scheduler (no lease: every job would fire N times), the
  login limiter, the live orchestrator swap and unlocked job cursors all
  break at N = 2, and there is no cross-process serialisation primitive.
  Raising it is a flagged decision through
  `docs/planning/analyses/2026-08-16-t4.10-replica-decision.md`.
- **The backup worker is a third launch path** (`docker-compose.worker.yml`,
  on a second machine, serving nightly-restored snapshots) and is bound by
  every invariant here; the worker-count and `--no-proxy-headers` guards
  cover all three compose files. **Read-only is enforced by the Postgres
  role, never the flag**: the app connects as `darkmem_viewer` (`SELECT`
  only, `scripts/worker/viewer-grants.sql`), and one global handler maps
  SQLSTATE `42501` to a 403 `read_only` envelope. `DARKMEM_READ_ONLY`
  (default off; shown on `GET /auth/security-posture`) is ergonomics: it
  skips boot writers, never arms `JobRegistry`, refuses chat and job
  triggers and outbound provider/Git/notification/setup probes, uses local
  graph-name fallbacks and skips provider health probes,
  clamps `reranker_enabled`, quiets write-on-read paths, and
  skips the semantic search arm, so the worker needs **no external
  service** (attempting it against an unreachable embedder would still answer
  on the keyword arm, but only after the connect retries, and would report an
  outage). Memory and code search answer on their keyword/`ILIKE` arms;
  the articles channel reports `semantic_ran=False`; **document search is
  refused** (cosine-only, so empty would read as "no matches"). Doors that
  spend, dial out or write a file are refused by `refuse_when_read_only`
  (`api/deps.py`): `memories/reason`, `documents/qa`, every `reembed` POST,
  repo create/reindex/reindex-files/webhook, chat, job triggers, page
  attachment upload. Token refresh reissues without blocklisting there. The
  receiver (`app/worker_receiver.py`, its own uvicorn) writes files, never
  rows; a closure walk fails the build if it reaches `app.main`,
  `app.database` or any service. `scripts/worker/restore-cycle.sh`
  **verifies before it swaps** (replay, migrate and `schema_guard` on a side
  database) and rejects a snapshot from an older baseline. Procedure:
  `docs/runbook-backup-worker.md`.

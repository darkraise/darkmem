# Centralize background workers into the Jobs page

- **Date:** 2026-06-01 (rev 2 — after codebase-grounded review)
- **Status:** Approved (design, revised)
- **Scope:** backend (`backend/app`) + frontend (`frontend/src`)

## Problem

Background-job management is split across two overlapping surfaces:

- **Settings → Workers tab** renders one inline card (`EnrichmentCard`,
  `settings.tsx:69-156`) for the code-symbol enrichment worker: an
  **Enabled** toggle, a **Batch Size** field, a **Run Now** button, and a
  note that scheduling lives on the Jobs page.
- **Jobs page** owns scheduling (cron), an **enabled** switch, last-run
  status, and a per-row **Run Now** trigger for every registered job,
  including `code_enrichment`.

The overlap is real and partly misleading:

- The Settings **Enabled** toggle already writes the job's `enabled`:
  `update_enrichment_config` calls
  `job_registry.update_config("code_enrichment", enabled=...)`
  (`config.py:951`) and stores a redundant `enrichment_config.enabled`
  mirror the runner never reads.
- The `code_enrichment` runner reads only `enrichment_config.batch_size`
  (`job_runners.py:124`); it ignores the mirror.
- **Run Now** in Settings (`POST /config/enrichment/trigger`) duplicates
  the Jobs trigger. The same enrichment-trigger hook also powers a second,
  separate button on the **Repositories page** (`repos.tsx:451-464`).

So the only state the Jobs page does not already model is `batch_size`.

## Goal

Make the Jobs page the single surface for every background job and its
settings. Remove the Workers tab, the redundant Enabled/Run Now, and the
`enrichment_config` row. Add a **generic per-job config** mechanism so any
job can expose settings; `code_enrichment` uses it for `batch_size`.

### Non-goals

- No change to scheduling, the cron editor, or the JobRegistry run loop.
- No change to the `JobRunner` signature or the Jobs trigger contract —
  so the Jobs trigger does **not** surface a "processed" count (the
  Repositories toast loses that number).
- No new descriptor field types beyond `int` (the one real field today).
- No deprecated compatibility shims for the removed enrichment routes.

## Design

### Backend — generic per-job config

- **`JobConfig`** (per-job state persisted in the `config` row keyed
  `job:<key>`) gains `config: dict` (default `{}`), included in `to_dict`
  and `from_dict` with a `data.get("config", {})` fallback. This is
  load-bearing: `_run_once` rewrites the whole row via `to_dict` on every
  scheduled run and trigger, so `config` MUST round-trip or the first run
  after a save erases `batch_size`.
- **`Job`** (static registration) gains `config_schema: list[FieldDescriptor]`
  (default `[]`); `default_config` is derived from the descriptor defaults.
  `config_schema` is static on `Job`, so it is injected into the per-job
  dict in `list_with_config` (`job_registry.py:199-207`), **not** in
  `JobConfig.to_dict`.
- **Registry write path** (net-new — none exists today; `update_config`
  takes only `enabled`/`cron`): add `set_config(key, partial: dict)` (or
  extend `update_config`) that read-modify-writes the `job:<key>` row,
  preserving `last_run_at`/`last_status`/`last_error` and shallow-merging
  `config` per key. `load_config` already returns the row and now exposes
  `config` for the runner.
- **`FieldDescriptor`** (backend Pydantic model + a single mirrored TS type):

  ```
  { key: str, type: "int", label: str, default: int,
    min?: int, max?: int, step?: int, help?: str }
  ```

- `code_enrichment` declares one field:

  ```
  { key: "batch_size", type: "int", label: "Batch Size", default: 5,
    min: 1, max: 100, step: 1,
    help: "Code symbols summarised per scheduled run." }
  ```

  `max` is **100** — the existing ceiling (`EnrichmentConfigUpdate` is
  `ge=1, le=100`; the old trigger clamped `min(100, …)`). The unrelated
  `embedding_batch_size` flag is the one bounded at 200.

- **Endpoints** (`backend/app/api/routes/jobs.py`):
  - `GET /api/v1/jobs` — `JobItem` gains `config: dict` (current values
    merged over `default_config`) and `config_schema: list[FieldDescriptor]`.
  - `PUT /api/v1/jobs/{key}/config` — **manual** validation against the
    job's `config_schema` (FastAPI cannot generate a model from a per-job
    schema): 404 on unknown key, 422 on an unknown config key / wrong type
    / out-of-range value, then shallow read-modify-write merge into
    `job:<key>.config`; return the refreshed `JobItem`. Mirror `update_job`'s
    structure and the manual-validation precedent in `update_system_prompts`
    (`config.py:1009-1024`).
  - `PUT /api/v1/jobs/{key}` (enabled/cron) and
    `POST /api/v1/jobs/{key}/trigger` are unchanged.
- **Runner** `make_code_enrichment_runner` reads `batch_size` from the
  `code_enrichment` job config. It must read `app.state.job_registry`
  **lazily inside `run()`** — `app.state.job_registry` is set at
  `main.py:221`, after the runner is constructed at `main.py:189`. Default
  5 when unset.

### Backend — retire the old enrichment surface

- Delete `GET/PUT/POST /config/enrichment` (`config.py:913/929/1085`) and
  the `EnrichmentConfigUpdate` model (`config.py:908-910`). This removes
  the `enabled`-mirror (`config.py:951`) and the trigger handler's
  `batch_size` read (`config.py:1100-1106`) wholesale — those are inside
  the deleted routes, not separate readers. The only surviving runtime
  reader is `job_runners.py:124`, repointed above.
- `main.py:182-186` is the `code_enrichment` Job **description string**
  (not a reader); update its text to stop referencing "the legacy
  enrichment_config row".
- **Startup copy** (idempotent, application-startup logic — *not* Alembic):
  after `code_enrichment` is registered (`main.py:167-212`) and before/at
  `start_all` (`main.py:222`), if its job config has no `batch_size`, copy
  from the `enrichment_config` row **if present**, else default 5. The row
  is created only lazily by the old `PUT /config/enrichment`, so on most
  installs it is absent and the copy is a no-op landing on 5 (matching the
  current runner fallback). After this the `enrichment_config` row is
  unused; no DB migration needed to drop it.
- `EnrichmentWorker.process_batch` stays (the real work). Its now-orphaned
  `run_loop`/`stop`/`interval`/`_running` (`enrichment_worker.py:24-26,
  98-116`) become dead code; remove them in this pass after confirming no
  other caller, or note as explicit out-of-scope.

### Frontend — Jobs page (per-row config Dialog)

The darkraise-ui `DataTable` exposes no row-expansion API (props are only
`columns/data/isLoading/searchKey/searchPlaceholder`; no
`getExpandedRowModel`/sub-component slot), so config opens from an
actions-column button, not an inline expanded row.

- The `Job` type gains `config: Record<string, unknown>` and
  `config_schema: FieldDescriptor[]`; the consumer treats a missing
  `config_schema` as `[]` to survive a rollout window. `FieldDescriptor`
  is one exported TS type in `use-jobs-api.ts`, re-exported via
  `hooks/api/index.ts`.
- Add a **Configure** (gear) action to the existing actions column — an
  in-cell component like the current `CronCell`/`TriggerCell`. For rows
  with a non-empty `config_schema` it opens a **Dialog** hosting a generic
  `JobConfigForm`; rows without a schema render no gear button.
- **`JobConfigForm`** renders fields from `config_schema`. `type: "int"`
  maps to the **composed** darkraise-ui `NumberInput` anatomy
  (`NumberInput > NumberInputControl > NumberInputField +
  NumberInputTriggerGroup > Increment/DecrementTrigger`), reading
  `onValueChange`'s `valueAsNumber`, mirroring the existing `NumericRow`
  pattern in `settings.tsx`. It holds a draft; **Save** calls
  `PUT /jobs/{key}/config` (rounding `valueAsNumber` for ints) with a
  toast; **Cancel** closes.
- Bump `DataTableSkeleton columnCount` from 8 to 9 for the new gear column
  (`jobs.tsx:275`).
- The per-row `enabled` switch and cron editor are unchanged.

### Frontend — Settings cleanup

- Remove the inline `EnrichmentCard` function (`settings.tsx:69-156`) and
  its imports (`settings.tsx:4-6`).
- Remove the `SETTINGS_TABS` `workers` entry (`settings.tsx:667`) and its
  `TabsContent` (`settings.tsx:714-716`).
- Remove `"workers"` from **both** the `SettingsTabValue` union and the
  `KNOWN` array in `lib/settings-tab.ts` so a stale
  `darkmem.settings.tab="workers"` falls back to `flags`.
- Update the `PageHeader` description (`settings.tsx:693`) to drop "workers".
- Remove the now-unused `useEnrichmentConfig` / `useUpdateEnrichmentConfig`
  / `useTriggerEnrichment` hooks and the `EnrichmentConfig` type
  (`use-config-api.ts:281-315`). Note `useTriggerEnrichment` has **two**
  callers — `settings.tsx` (removed here) and `repos.tsx` (repointed next).

### Frontend — Repositories page

- Repoint the **Run Enrichment** button (`repos.tsx:11/259/451-464`) from
  `useTriggerEnrichment` to `useTriggerJob("code_enrichment")`. The Jobs
  trigger returns `{key,last_status,last_error,last_run_at}` (no `processed`
  count), so change the success toast from `Enriched ${data.processed}
  symbols` to `Enrichment run started`.

## Data flow

1. Jobs page `GET /jobs` → rows carrying `config` + `config_schema`.
2. User clicks the gear on `code_enrichment` → Dialog opens `JobConfigForm`
   with **Batch Size** (composed `NumberInput`) at the current value.
3. Save → `PUT /jobs/code_enrichment/config { batch_size }` → validated and
   shallow-merged (read-modify-write) into `job:code_enrichment.config`.
4. The job fires on its schedule (`enabled` + `cron`); the runner lazily
   reads `app.state.job_registry` → job config → `batch_size`.

## Decisions (baked in)

- A per-row **Dialog** hosts config (the `DataTable` has no expandable-row
  API).
- The Repositories **Run Enrichment** button is repointed to the Jobs
  trigger; its toast drops the symbol count.
- `/config/enrichment` routes are **deleted**, not shimmed.
- `batch_size` default **5**, max **100**.
- The field renderer supports only `type: "int"` now; the descriptor
  leaves room for `bool`/`float`/`select` later, built when a job needs it.

## Migration / compat

- Startup copy as above; tolerates an absent `enrichment_config` row.
- `JobItem` field additions are additive/backward-compatible. The
  `/config/enrichment` deletions are breaking, but the API is
  local-network-only with no external SLA, so no shim.

## Testing

- **Backend unit:** `JobConfig` round-trip including `config` (update the
  two tests in `test_job_registry.py:51-67`); `set_config`/`load_config`;
  `PUT /jobs/{key}/config` validation (unknown key → 422, out-of-range →
  422, shallow merge); **`batch_size` survives a subsequent `trigger()`
  and a subsequent enabled toggle** (the clobber guard); the runner reads
  `batch_size` from job config (net-new — no runner test exists today);
  `list_with_config` emits `config` + `config_schema`; the
  `/config/enrichment` routes are gone.
- **Backend e2e:** update `docs/e2e/scripts/02_config_flow.py` (lines
  104-111) — remove/replace the `GET /config/enrichment` assertion (which
  is already partly stale: it expects an `interval_seconds` key the route
  never returns).
- **Frontend:** a Jobs-page test for the config Dialog save; a Settings
  test asserting no Workers tab; the `repos.tsx` button repoint; typecheck,
  build, and the unit suite stay green. (No Jobs/Settings spec exists today
  — net-new.)
- **Sequence:** backend-first (config field + registry write path +
  endpoint + runner read + startup copy, tests green) before the frontend,
  so the API contract is settled before the UI is built.

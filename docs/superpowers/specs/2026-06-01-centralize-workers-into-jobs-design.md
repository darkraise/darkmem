# Centralize background workers into the Jobs page

- **Date:** 2026-06-01
- **Status:** Approved (design)
- **Scope:** backend (`backend/app`) + frontend (`frontend/src`)

## Problem

Background-job management is split across two surfaces that overlap:

- **Settings → Workers tab** renders one card (`EnrichmentCard`) for the
  code-symbol enrichment worker: an **Enabled** toggle, a **Batch Size**
  field, a **Run Now** button, and a note that scheduling lives on the
  Jobs page.
- **Jobs page** owns scheduling (cron), an **enabled** switch, last-run
  status, and a **Run Now** trigger for every registered job, including
  `code_enrichment`.

The overlap is real and partly misleading:

- The Settings **Enabled** toggle already writes the job's `enabled`:
  `update_enrichment_config` calls
  `job_registry.update_config("code_enrichment", enabled=...)`
  (`backend/app/api/routes/config.py:951`) and also stores a redundant
  `enrichment_config.enabled` mirror that the runner never reads.
- The `code_enrichment` runner reads only `enrichment_config.batch_size`
  (`backend/app/services/job_runners.py:127`); it ignores the mirror.
- **Run Now** in Settings (`POST /config/enrichment/trigger`) duplicates
  the Jobs trigger (`POST /jobs/{key}/trigger`).

So the only piece of state the Jobs page does not already model is
`batch_size`. Everything else on the Workers tab is redundant.

## Goal

Make the Jobs page the single surface for every background job and its
settings. Remove the Workers tab, the redundant Enabled/Run Now, and the
`enrichment_config` row. Add a **generic per-job config** mechanism so any
job can expose inline settings; `code_enrichment` uses it for `batch_size`.

### Non-goals

- No change to scheduling, the cron editor, or the run loop.
- No new field types beyond what the one real field needs (`int`).
- No deprecated compatibility shims for the removed enrichment routes.

## Design

### Backend — generic per-job config

`JobConfig` (per-job state persisted in the `config` row keyed
`job:<key>`) gains a `config: dict` field, serialized in `to_dict` /
`from_dict` next to `enabled` / `cron` / `min_interval_seconds`. Default
`{}`.

`Job` (static registration dataclass) gains `config_schema: list[FieldDescriptor]`
(default `[]`). `default_config` is derived from the schema defaults.

`FieldDescriptor` (backend Pydantic + mirrored TS type):

```
{ key: str, type: "int", label: str, default: int|float,
  min?: number, max?: number, step?: number, help?: str }
```

`code_enrichment` declares one field:

```
{ key: "batch_size", type: "int", label: "Batch Size", default: 5,
  min: 1, max: 200,
  help: "Code symbols summarised per scheduled run." }
```

Endpoints (`backend/app/api/routes/jobs.py`):

- `GET /api/v1/jobs` — `JobItem` gains `config: dict` (current values,
  merged over `default_config`) and `config_schema: list[FieldDescriptor]`.
- `PUT /api/v1/jobs/{key}/config` — body validated against the job's
  `config_schema` (bounds-checked); merged into the `job:<key>` row's
  `config`; returns the updated `JobItem`. Unknown keys rejected.
- `PUT /api/v1/jobs/{key}` (enabled/cron) and
  `POST /api/v1/jobs/{key}/trigger` are unchanged.

`make_code_enrichment_runner` reads `batch_size` from the
`code_enrichment` job config via the registry instead of the
`enrichment_config` row, defaulting to 5 if unset.

### Backend — retire the old enrichment surface

- Delete `GET/PUT/POST /config/enrichment` and the `EnrichmentConfigUpdate`
  model, including the `enabled`-mirror call at `config.py:951`. Audit the
  remaining `enrichment_config` readers (`config.py:1100-1106`, `main.py:185`)
  and redirect them to the job config or remove them.
- One-time, idempotent migration on registry startup: if the
  `code_enrichment` job config has no `batch_size`, copy it from the
  `enrichment_config` row (default 5). `enabled` is already mirrored onto
  the job, so nothing to migrate there. After this, the `enrichment_config`
  row is unused.

### Frontend — Jobs page

- The `Job` type gains `config: Record<string, unknown>` and
  `config_schema: FieldDescriptor[]`.
- A generic **`JobConfigForm`** renders fields from `config_schema`:
  `type: "int"` maps to the existing darkraise-ui `NumberInput` (min/max/step
  from the descriptor). It holds a local draft and a **Save** that calls
  `PUT /jobs/{key}/config`, with a success/error toast.
- Rows whose `config_schema` is non-empty get an expand chevron; the
  expanded content is `JobConfigForm`. Rows without a schema (e.g.
  `repo_sync`) have no expand. `code_enrichment` shows **Batch Size**.
- The per-row `enabled` switch and cron editor are unchanged.

### Frontend — Settings cleanup

Remove the `workers` tab entry, its `TabsContent`, the `EnrichmentCard`
component, and the now-unused `useEnrichmentConfig` /
`useUpdateEnrichmentConfig` / `useTriggerEnrichment` hooks and
`EnrichmentConfig` type.

## Data flow

1. Jobs page `GET /jobs` → rows carrying `config` + `config_schema`.
2. User expands `code_enrichment` → `JobConfigForm` renders **Batch Size**
   (`NumberInput`) from the schema and current value.
3. Save → `PUT /jobs/code_enrichment/config { batch_size }` → updates the
   `job:code_enrichment` row's `config`.
4. The job fires on its schedule (`enabled` + `cron`); the runner reads
   `batch_size` from the job config.

## Decisions (baked in)

- The `/config/enrichment` routes are **deleted**, not shimmed.
- `code_enrichment` `batch_size` default is **5** (its current runner
  default), distinct from the unrelated `embedding_batch_size` feature
  flag (default 20).
- The generic field renderer supports only `type: "int"` now; the
  descriptor shape leaves room for `bool` / `float` / `select` later, built
  only when a job needs them.

## Testing

- **Backend:** job-config get/set; schema bounds validation (reject
  out-of-range and unknown keys); runner reads `batch_size` from job
  config; the startup copy is idempotent; the `/config/enrichment` routes
  are gone.
- **Frontend:** expandable row renders from `config_schema` and saves;
  the Workers tab no longer exists; typecheck, build, and the unit suite
  stay green.

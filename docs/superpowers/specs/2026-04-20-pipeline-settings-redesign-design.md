# Pipeline & Settings UI Redesign — Design Spec

**Date:** 2026-04-20
**Branch:** feat/ml-pipeline-integration (planned follow-up branch)
**Status:** Approved design — ready for implementation plan

## 1. Goal

Rework the settings surface so the core choice a user makes when adding memories — "use the local fine-tuned Darkmem ML stack or route everything through an LLM" — becomes the top-level concept. Device selection, persistence, live system metrics, and per-stage model/prompt configuration all hang off that choice on a single new `/pipeline` page. The existing `/settings` and `/llm` pages are split and rebuilt so related controls live together.

## 2. Non-goals

- Encryption-at-rest for LLM API keys (flagged separately in the 2026-04-19 settings review).
- Admin-role gating on config endpoints (ditto).
- PUT→PATCH semantic cleanup on `/config/feature-flags`.
- Any backend schema migration: `FEATURE_FLAGS_DEFAULTS` and the `PROMPTS` dict stay unchanged.

## 3. Information architecture

### 3.1 New route map

| Route | Today | After |
|---|---|---|
| `/pipeline` | Re-embed progress page | **New Pipeline page (this design)** |
| `/reindex` | — | Renamed from the old `/pipeline` re-embed progress page |
| `/llm` | LLM purpose config page | Redirects to `/pipeline` |
| `/settings` | Five tabs | Four tabs (see 3.3) |

The `Dialog` on the LLM purpose save flow currently links "Re-embed now" to `/pipeline`; that target updates to `/reindex`.

### 3.2 New `/pipeline` page layout

One scrolling page with three bands:

1. **PageHeader** — title "Pipeline" + one-line description.
2. **Mode toggle card** — segmented `[ Darkmem ML stack | LLM ]`, `Shadow mode` switch, `Advanced ▾` expander. A single derived summary line below (`Extraction · Classification · Retrieval — all 3 on ML`).
3. **Two panels side-by-side at `lg`+, stacked below** — **ML panel** on the left, **LLM panel** on the right. Both are always visible regardless of the toggle state; non-active stacks render slightly dimmed. Each panel has a header status chip (`active · 3/3`, `inactive · 0/3`, `mixed · 2/3`).

### 3.3 Settings tabs after migration

| Tab | Contents |
|---|---|
| Feature Flags | `hybrid_search_enabled`, `reranker_enabled`, `llm_enrichment_enabled`, `confidence_rank_gamma`, `pipeline_concurrency`, `embedding_batch_size`, `embedding_concurrency`, `entity_cache_ttl_minutes` |
| Classification | areas + mode (unchanged) |
| Workers | enrichment card (unchanged) |
| Assistant Prompts | `chat`, `cluster_naming`, `agent_instructions` — identical textarea/override pattern, scoped to the three orphans |

The "ML Pipeline" tab disappears. The "System Prompts" tab is replaced by "Assistant Prompts". The persisted tab key `darkmem.settings.tab` migrates `"ml"` or `"prompts"` → `"flags"` on first mount.

## 4. Mode toggle semantics

- **Preset writer, not a state field.** The segmented control issues a `POST /api/v1/pipeline/mode` with `{"mode": "ml" | "llm"}`. The backend writes the same value to `ml_extraction`, `ml_classification`, `ml_retrieval` atomically.
- **Derived selection.** The segmented control's highlighted segment is computed from the three flags: all-true → ML, all-false → LLM, any mix → neither highlighted. A small `Mixed` pill appears to the right when stages disagree.
- **Advanced disclosure.** Three labeled switches bound directly to the three stage flags. Flipping one never touches the others; the `Mixed` indicator is the only drift feedback.
- **Shadow mode.** The existing `ml_shadow_mode` feature flag is promoted out of the feature-flags list. It sits on the mode-toggle card header row, visible by default — not inside the Advanced disclosure — so its interaction with the stack choice stays discoverable.

## 5. ML panel specification

Single card with four stacked regions. Always visible; dim when all three stages are LLM.

### 5.1 Device picker

- `ToggleGroup` with options: `Auto`, one `CUDA:<index> (<gpu name>)` per available CUDA device, `CPU`.
- Labels and ids come from `GET /api/v1/config/ml-devices` (unchanged backend).
- Click calls `POST /api/v1/config/ml-device/apply` (unchanged). Same-device reselect is guarded client-side.
- On `reload_error` in the response, toast the error text and revert the segmented selection to `effective_device`.

### 5.2 Persistence toggle

- Segmented `[ Persistent | Idle TTL ]` bound to the backend `ml_idle_ttl_minutes` flag.
- `Persistent` writes `0`. `Idle TTL` reveals an adjacent minutes input (default `30`, range `1–1440`) and writes that value.
- No backend schema change — the existing integer field carries both cases.

### 5.3 Metrics dashboard

Two tiles rendered based on the effective device from `/api/health/ml_models`:

| Device | Tile 1 | Tile 2 |
|---|---|---|
| `cpu` | CPU LOAD % | RAM used / total GB |
| `cuda:*` | GPU LOAD % | VRAM used / total GB |

Each tile is a label + large number + thin progress bar. Polled at 5s via `useMLModelsHealth` (adjusted `refetchInterval`).

### 5.4 Loaded-groups row

Three chips (`extraction`, `classification`, `retriever`):
- Loaded: green with idle-seconds (`extraction · 42s`).
- Idle/not loaded: dimmed.

Reuses the existing `groups` field from `/api/health/ml_models`.

### 5.5 Unload controls

- Primary CTA `Unload all models` (destructive style) — calls `POST /api/v1/pipeline/unload` with no `group` parameter.
- `Advanced — per-group unload` disclosure reveals three buttons (`Unload extraction`, `Unload classification`, `Unload retriever`), each disabled when its group is not currently loaded. Calls `POST /api/v1/pipeline/unload?group=<name>`.

## 6. LLM panel specification

Single card with six stacked child cards — one per purpose (`embedding`, `extraction`, `classification`, `reasoning`, `summarization`, `reranker`). Each card is independently collapsible.

### 6.1 Collapsed card

Header row only: purpose name on the left, one-line config summary on the right (`qwen3-embedding:0.6b · 1024d · ollama`). Click anywhere on the header toggles open.

### 6.2 Expanded card — Model region

Replaces today's `/llm` click-Edit-then-Save flow with always-editable inline inputs and autosave-on-blur using `POST /api/v1/config/llm` with a single-purpose body (the endpoint's existing merge logic already supports partial payloads; see the 2026-04-19 fix that made empty `params` preserve the stored value).

Common fields: provider, base_url, model, api_key (shown as `***` placeholder, sent verbatim preserves the stored key).

Purpose-specific fields:

| Purpose | Extra fields |
|---|---|
| embedding | dimensions |
| extraction | extraction_mode (`json`/`flat`/`nested`), reasoning switch |
| classification, reasoning, summarization, reranker | reasoning switch |

JSON params editor under a "More…" disclosure.

### 6.3 Expanded card — System prompts region

Rendered only for purposes that own prompts:

| Purpose | Prompts shown |
|---|---|
| embedding | *(none — region hidden)* |
| extraction | `extraction` · `extraction_entities` · `extraction_relationships` (pills above one textarea) |
| classification | `classification` (single textarea) |
| reasoning | `reasoning` |
| summarization | `summarization` |
| reranker | *(none — region hidden)* |

For the multi-prompt case (extraction), pills display which `tool_call_mode` uses each prompt. The currently-overridden prompt shows a `custom` badge on its pill. Below the textarea: character count / 20,000, `Load default` button, `Save override` button (calls existing `PUT /api/v1/config/system-prompts` with empty string to clear).

### 6.4 Dimension-change dialog

The existing obsolete-counts dialog triggered by embedding model or dimensions changes is kept verbatim. Its `Re-embed now` button navigates to `/reindex` (renamed route).

## 7. Backend changes

### 7.1 New endpoints

**`GET /api/v1/pipeline`** — aggregator returning the whole page state in one payload:

```
{
  mode: "ml" | "llm" | "mixed",
  stages: { extraction: "ml"|"llm", classification: ..., retrieval: ... },
  shadow_mode: bool,
  ml: {
    device: "auto"|"cpu"|"cuda",
    effective_device: string|null,
    cuda_index: int,
    persistence: "persistent"|"ttl",
    idle_ttl_minutes: int,
    eviction_check_interval_seconds: int,
    cpu_fallback: bool,
    available_devices: [{id, label, kind, index}],
    groups: { extraction: {loaded, idle_seconds}, classification: {...}, retriever: {...} }
  },
  llm: {
    embedding: LLMPurposeConfigSchema,
    extraction: LLMPurposeConfigSchema,
    classification: LLMPurposeConfigSchema,
    reasoning: LLMPurposeConfigSchema,
    summarization: LLMPurposeConfigSchema,
    reranker: LLMPurposeConfigSchema
  },
  prompts: {
    extraction: {default, override, effective},
    extraction_entities: {...},
    extraction_relationships: {...},
    classification: {...},
    reasoning: {...},
    summarization: {...}
  }
}
```

Composed from existing services (`fetch_llm_config`, `get_feature_flags_dict`, `list_available_devices`, `prompt.get_overrides`). No new DB access patterns; no schema changes. The `persistence` string and the top-level `mode` are derived — `persistence` is `"persistent"` when `ml_idle_ttl_minutes == 0` else `"ttl"`; `mode` is `"ml"` when all three stage flags are true, `"llm"` when all three are false, else `"mixed"`.

**`POST /api/v1/pipeline/mode`** — preset writer. Body `{"mode": "ml" | "llm"}`. Writes all three stage flags atomically. Returns `{mode, stages}`.

**`POST /api/v1/pipeline/unload`** — optional query param `group=extraction|classification|retriever`, omit for all. Body empty. Returns `{unloaded: [...], groups: {...}}`. Calls the existing `unload_*` functions in `services/ml_models.py` under the appropriate `_GROUP_LOCKS` entry.

### 7.2 Health endpoint extension

`GET /api/health/ml_models` gains additive fields:

- `cpu_percent: float | null` — system-wide from `psutil.cpu_percent()`.
- `ram_used_mb: int | null`, `ram_total_mb: int | null` — from `psutil.virtual_memory()`.
- `gpu_util_percent: float | null` — from `pynvml.nvmlDeviceGetUtilizationRates(handle).gpu`.
- `vram_total_mb: int | null` — from `pynvml.nvmlDeviceGetMemoryInfo(handle).total / 1e6`.

Fields are `null` when the corresponding library is unavailable or the host doesn't support them. No existing consumers break.

### 7.3 Dependencies

Add `psutil` and `pynvml` to the backend package manifest. Both are pure-Python pip installs.

### 7.4 Existing endpoints

Every existing config endpoint keeps its current shape and behaviour: the new Pipeline UI writes through them for individual edits. The aggregator is a read shortcut, the mode writer is the only new mutation beyond unload.

## 8. Frontend component inventory

New components under `frontend/src/components/pipeline/`:

| Component | Responsibility |
|---|---|
| `PipelineModeToggle` | Segmented preset + shadow switch + Advanced disclosure with three stage switches |
| `MLPanel` | Composition root for the ML stack side |
| `MLDeviceSection` | Device picker + persistence toggle |
| `SysMetricsDashboard` | Two tiles (CPU+RAM or GPU+VRAM) + loaded-groups row |
| `UnloadControls` | `Unload all` CTA + per-group Advanced disclosure |
| `LLMPanel` | Composition root for the LLM side |
| `LLMPurposeCard` | Collapsible card with Model region + integrated System prompts |
| `LLMPurposePromptEditor` | Pills + textarea + save/load controls |

Hooks under `frontend/src/hooks/api/`:

- `usePipeline()` — new `GET /api/v1/pipeline` query with `staleTime: 15s`, so cross-tab edits reconcile without hammering the endpoint.
- `useSetPipelineMode()` — new `POST /api/v1/pipeline/mode` mutation.
- `useUnloadPipeline()` — new `POST /api/v1/pipeline/unload` mutation.
- Existing `useLlmConfig`, `useUpdateLlmConfig`, `useFeatureFlags`, `useUpdateFeatureFlags`, `useSystemPrompts`, `useUpdateSystemPrompts`, `useMLDevices`, `useApplyMLDevice`, `useMLModelsHealth` all stay. The Pipeline page invalidates the aggregator query on every mutation that touches its fields.

The Settings page's existing cards that survive (`FeatureFlagsCard` trimmed, `ClassificationAreasCard`, `EnrichmentCard`, and a new `AssistantPromptsCard` scoped to the three orphans) remain self-contained; no cross-page state sharing beyond React Query's cache.

## 9. Error handling

| Failure | Behaviour |
|---|---|
| `GET /api/v1/pipeline` | Full-page error card with status, message, retry button. Page does not become interactive until the aggregator succeeds. |
| `POST /pipeline/mode` | Segmented control reverts to derived state from the last-known flags. Toast the error. |
| `POST /pipeline/unload` | Toast. Next poll of `/api/health/ml_models` reconciles the groups row. |
| `POST /config/ml-device/apply` returning `reload_error` | Toast with the error text. Segmented device selection reverts to `effective_device`. |
| `/api/health/ml_models` failure | Individual tiles render `—` with tooltip "metrics unavailable". Loaded-groups row is independent and keeps its last known state. |
| `pynvml` unavailable | `gpu_util_percent` is `null`; tile shows `—` with tooltip "driver didn't report utilization". VRAM allocated continues to render via `torch.cuda.memory_allocated`. |
| `psutil` unavailable | CPU and RAM tiles show `—`. Treated as install-broken; health endpoint should log a warning once at startup. |

## 10. Loading and empty states

- **Page-level.** Skeleton with the four bands outlined while the aggregator resolves. No partial rendering.
- **Metrics dashboard.** Tiles show `—` until the first health response lands. No spinner — 5s cadence.
- **Optimistic mutations.** Device apply, mode preset, per-group unload flip the UI immediately and reconcile on server echo. LLM config saves and prompt saves stay non-optimistic because the obsolete-counts dialog depends on server-computed fields.
- **No CUDA devices.** Device picker shows only "CPU" with a small note.
- **Fresh install, no LLM config row.** Aggregator composes from `settings.llm_*` env defaults in `backend/app/config.py`; the six purpose cards render with those defaults.
- **Pipeline init failed at startup.** Aggregator still returns; embedding card's summary shows `(dimensions unknown)` and the obsolete-counts dialog is skipped on save.

## 11. Testing plan

### 11.1 Backend (`backend/tests/`)

- `test_pipeline_aggregator.py` — shape; defaults when DB rows are missing; composition correctness against the four underlying services; `mode` derivation across all-true / all-false / mixed.
- `test_pipeline_mode.py` — POST with `"ml"` flips all three stage flags; `"llm"` flips them back; unknown value returns 422; existing non-ML feature-flag keys are preserved.
- `test_pipeline_unload.py` — POST without `group` unloads everything; `group=extraction` unloads only that group; `group=bogus` returns 422; response `groups` payload matches the new state.
- `test_ml_health_metrics.py` — monkey-patch `psutil` and `pynvml` to return fixed values; assert new fields populate; assert graceful degradation when either import fails.
- Extend `test_ml_device_config.py` and `test_ml_lazy_load.py` for the extended health payload.

### 11.2 Frontend

- `npx tsc --noEmit` must stay green.
- One Playwright smoke test: navigate to `/pipeline`, click `Darkmem ML stack`, expand Advanced, verify the three stage switches read `true`.
- Existing settings tests keep passing after the tab migration.

### 11.3 Manual QA checklist

- Switch mode ML↔LLM with no in-flight memory-add; verify the three flags in DB flip.
- Start from a fresh container without `pynvml`; confirm `gpu_util_percent` degrades to `—` without crashing the page.
- Open two browser tabs, change the LLM extraction model in one, verify the other picks up the new config on next aggregator poll (aggregator is `staleTime: 15s`).
- Exercise `Unload all` while a memory-add is in flight; verify the in-flight request completes on the old model group and the next request triggers a fresh lazy-load.

## 12. Open questions / deferred items

- Encryption-at-rest for LLM API keys (deferred to a security pass).
- Admin-role gating on all `/api/v1/config/*` and `/api/v1/pipeline/*` endpoints (deferred).
- Whether `confidence_rank_gamma` belongs on Pipeline vs. Settings long-term — it lives in Settings for this redesign; revisit if user feedback pushes it onto Pipeline.

## 13. Rollout

Single-PR rollout against `main` is feasible — the feature is self-contained, existing endpoints are unchanged, and the DB schema is untouched. The `/llm` redirect and the `/pipeline` rename to `/reindex` are the only URL-facing breaking changes; both are announced in the PR description and covered by route tests.

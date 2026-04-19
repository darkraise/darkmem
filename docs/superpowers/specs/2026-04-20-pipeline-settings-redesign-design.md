# Pipeline & Settings UI Redesign — Design Spec

**Date:** 2026-04-20
**Base branch:** `master` (earlier `feat/ml-pipeline-integration` work was merged; implementation will branch off `master`)
**Status:** Approved design — ready for implementation plan

## 1. Goal

Rework the settings surface so the core choice a user makes when adding memories — "use the local fine-tuned Darkmem ML stack or route everything through an LLM" — becomes the top-level concept. Device selection, persistence, live system metrics, and per-stage model/prompt configuration all hang off that choice on a single new `/pipeline` page. The existing `/settings` and `/llm` pages are split and rebuilt so related controls live together.

## 2. Non-goals

- Encryption-at-rest for LLM API keys (flagged separately in the 2026-04-19 settings review).
- Admin-role gating on config endpoints (ditto).
- PUT→PATCH semantic cleanup on `/config/feature-flags`.
- Any backend schema migration: `FEATURE_FLAGS_DEFAULTS` and the `PROMPTS` dict stay unchanged.

## 3. Information architecture

### 3.1 New route map and file renames

| Route | Today | After |
|---|---|---|
| `/pipeline` | Re-embed progress page | **New Pipeline page (this design)** |
| `/reindex` | — | Renamed from the old `/pipeline` re-embed progress page |
| `/llm` | LLM purpose config page | Redirects to `/pipeline` |
| `/settings` | Five tabs | Four tabs (see 3.3) |

**File-level renames and additions.**

- `frontend/src/routes/_authenticated/pipeline.tsx` → `reindex.tsx` with `createFileRoute("/_authenticated/reindex")`. The file move must happen *before* the new Pipeline page file is created, otherwise TanStack Router auto-generates conflicting route entries.
- A new file `frontend/src/routes/_authenticated/pipeline.tsx` holds the new Pipeline page (same pathname, entirely different component).
- The existing `frontend/src/hooks/api/use-pipeline-api.ts` contains heterogeneous hooks (stats, health, pipeline logs, reprocess stream, failures) — **do not rename or split it**. The new aggregator/mode/unload/metrics hooks go in a new file `frontend/src/hooks/api/use-pipeline-config.ts` to avoid re-exporting `usePipeline` from a file that already exports adjacent names.

The `Dialog` on the LLM purpose save flow currently links "Re-embed now" to `/pipeline`; that target updates to `/reindex`. Before shipping, audit all internal callers of `/pipeline` (TanStack Router `<Link>`, programmatic `navigate({ to: ... })`, toast links) and update them — grep `navigate.*pipeline` and `to=.*pipeline` across `frontend/src`.

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

The "ML Pipeline" tab disappears. The "System Prompts" tab is replaced by "Assistant Prompts" (persisted key `"assistant"`). Migration for `localStorage["darkmem.settings.tab"]` on first mount: `"ml"` → `"flags"` (ML controls moved off Settings entirely), `"prompts"` → `"assistant"` (the user was editing prompts — send them to the prompts-adjacent tab).

## 4. Mode toggle semantics

- **Preset writer, not a state field.** The segmented control issues a `POST /api/v1/pipeline/mode` with `{"mode": "ml" | "llm"}`. The backend writes the same value to `ml_extraction`, `ml_classification`, `ml_retrieval` inside a single DB transaction (one UPDATE on the `feature_flags` Config row) so concurrent admins can't observe partial state.
- **Derived selection.** The segmented control's highlighted segment is computed from the three flags: all-true → ML, all-false → LLM, any mix → neither highlighted. A small `Mixed` pill appears to the right when stages disagree.
- **Advanced disclosure.** Three labeled switches bound directly to the three stage flags. Flipping one never touches the others; the `Mixed` indicator is the only drift feedback.
- **Shadow mode.** The existing `ml_shadow_mode` feature flag is promoted out of the feature-flags list. It sits on the mode-toggle card header row, visible by default — not inside the Advanced disclosure — so its interaction with the stack choice stays discoverable.

## 5. ML panel specification

Single card with five stacked regions (device picker, persistence toggle, metrics dashboard, loaded-groups row, unload controls). Always visible; dim when all three stages are LLM.

**Naming note.** The stage is `retrieval` (feature-flag `ml_retrieval`, aggregator `stages.retrieval`), but the ML-model group for that stage is `retriever` (aggregator `ml.groups.retriever`, unload function `unload_retriever`). Keep the distinction intact in code and tests — mixing them is a common trap.

### 5.1 Device picker

- `ToggleGroup` with options: `Auto`, one `CUDA:<index> (<gpu name>)` per available CUDA device, `CPU`.
- Labels and ids come from `GET /api/v1/config/ml-devices` (unchanged backend).
- Click calls `POST /api/v1/config/ml-device/apply` (unchanged). Same-device reselect is guarded client-side.
- On `reload_error` in the response, toast the error text and revert the segmented selection to `effective_device`.

### 5.2 Persistence toggle

- Segmented `[ Persistent | Idle TTL ]` bound to the backend `ml_idle_ttl_minutes` flag.
- `Persistent` writes `0`. `Idle TTL` reveals an adjacent minutes input (range `1–1440`) and writes that value.
- **Value preservation across round-trips.** When the user flips from `Idle TTL` (e.g. 15 min) to `Persistent`, the component remembers the previous non-zero value in `localStorage["darkmem.pipeline.lastIdleTtl"]` and restores it if the user flips back to `Idle TTL`. First-time selection of `Idle TTL` (no stored prior value) defaults to `30`.
- **Advanced — Eviction check interval.** A small power-user input inside the Persistence region reveals the `ml_eviction_check_interval_seconds` flag (range `10–3600`, default `60`). Visible only when `Idle TTL` is selected and only inside an `Advanced ▾` disclosure so casual users don't see it.
- No backend schema change — both fields already exist in `FEATURE_FLAGS_DEFAULTS`.

### 5.3 Metrics dashboard

Two tiles rendered based on the effective device reported by `GET /api/v1/pipeline` and `GET /api/v1/pipeline/metrics`:

| Device | Tile 1 | Tile 2 |
|---|---|---|
| `cpu` | CPU LOAD % | RAM used / total GB |
| `cuda:*` | GPU LOAD % | VRAM used / total GB |

When `effective_device` is `null` (no ML group has ever been loaded in this process) the tiles fall back to **host-level** CPU/RAM — the dashboard stays informative before the first lazy load.

**VRAM tile sourcing.** The primary value is `vram_used_mb` / `vram_total_mb` from `pynvml` (whole-device view, what the tile actually wants). When `pynvml` is unavailable, the tile falls back to `vram_allocated_mb` from `/api/health/ml_models` (process-only, from `torch.cuda.memory_allocated`) with a subdued "process only" label and no total, since torch has no `total_mb` equivalent. GPU-load tile has no fallback — it shows `—` with a tooltip when `pynvml` is unavailable.

Each tile is a label + large number + thin progress bar. Polled at **5s** via a new `useMLMetrics()` hook (query key `["mlMetrics"]`) against the new auth-gated `/api/v1/pipeline/metrics` endpoint. The existing `useMLModelsHealth` hook continues to poll `/api/health/ml_models` at 10s for the fallback VRAM-allocated number — we do not raise its cadence.

### 5.4 Loaded-groups row

Three chips (`extraction`, `classification`, `retriever`):
- Loaded: green with idle-seconds (`extraction · 42s`).
- Idle/not loaded: dimmed.

Reads the `groups` field from `GET /api/v1/pipeline/metrics` (auth-gated, 5s cadence). The unauthenticated `/api/health/ml_models` endpoint continues to carry the same `groups` field for external monitoring consumers but the Pipeline UI does not depend on it.

### 5.5 Unload controls

- **Primary CTA `Unload all models`** (destructive style) — opens a confirmation dialog before firing the request: *"Unload all ML models? In-flight requests finish on the currently-loaded models; the next request reloads from disk (5–30s depending on device)."*. On confirm, calls `POST /api/v1/pipeline/unload` with no `group` parameter. Explicit confirmation is required because a misclick during heavy ingestion cascades into reloads on every subsequent request.
- **`Advanced — per-group unload` disclosure** reveals three buttons (`Unload extraction`, `Unload classification`, `Unload retriever`), each disabled when its group is not currently loaded. These are surgical enough to skip the confirmation dialog — one click, one group.
- **Shadow mode interaction.** When `ml_shadow_mode=true` and the *effective* path for a stage is LLM, the ML group for that stage still loads lazily to run shadow predictions. Unloading it is permitted but triggers a silent reload on the next shadow path. The confirmation dialog includes an extra line when shadow mode is on: *"Shadow mode is enabled — shadow predictions will trigger reloads after this."*

## 6. LLM panel specification

Single card with six stacked child cards — one per purpose (`embedding`, `extraction`, `classification`, `reasoning`, `summarization`, `reranker`). Each card is independently collapsible.

### 6.1 Collapsed card

Header row only: purpose name on the left, one-line config summary on the right (`qwen3-embedding:0.6b · 1024d · ollama`). Click anywhere on the header toggles open.

### 6.2 Expanded card — Model region

Replaces today's `/llm` click-Edit-then-Save flow with always-editable inline inputs **and a per-card `Save` / `Cancel` pair** that appears only while the card is dirty. `Save` sends one `POST /api/v1/config/llm` with every changed field on that purpose batched — e.g. `{"extraction": {"provider": "openai", "model": "gpt-4o-mini", "base_url": "https://api.openai.com/v1"}}`. `Cancel` resets every field on the card to the server-side value from the cached aggregator response and clears the dirty flag. Autosave-on-blur was considered but rejected: each `POST /api/v1/config/llm` rebuilds the `LLMOrchestrator` (cheap) and, when the embedding purpose is changed without an explicit `dimensions` value, probes the embedder (can take 500ms–2s). Batching per card keeps that cost to one rebuild/probe per user-initiated save.

Editing a card without saving then navigating away prompts a "Discard unsaved changes?" dialog (TanStack Router's block-on-navigation hook). Collapsing the card without saving does NOT discard — the draft persists in component state until the card is unmounted or `Cancel` is clicked.

Common fields: provider, base_url, model, api_key (shown as `***` placeholder, sent verbatim preserves the stored key).

Purpose-specific fields:

| Purpose | Extra fields |
|---|---|
| embedding | dimensions |
| extraction | extraction_mode (`json`/`flat`/`nested`), reasoning switch |
| classification, reasoning, summarization, reranker | reasoning switch |

JSON params editor under a "More…" disclosure.

### 6.3 Expanded card — System prompts region

Rendered only for purposes that own prompts. The mapping lives in one place — `frontend/src/components/pipeline/prompt-map.ts` — so adding a new stage-bound prompt is a one-line edit:

| Purpose | Prompts shown |
|---|---|
| embedding | *(none — region hidden)* |
| extraction | `extraction` · `extraction_entities` · `extraction_relationships` (pills above one textarea) |
| classification | `classification` (single textarea) |
| reasoning | `reasoning` |
| summarization | `summarization` |
| reranker | *(none — region hidden)* |

Any prompt key in `/api/v1/config/system-prompts` not listed in this map (today: `chat`, `cluster_naming`, `agent_instructions`) is treated as an orphan and rendered on Settings → Assistant Prompts instead. The orphan set is not inferred — it is declared explicitly.

`frontend/src/components/pipeline/prompt-map.ts` exports **three** constants, all of which are the single source of truth:

- `PROMPT_PURPOSE_MAP: Record<LLMPurpose, string[]>` — keys are the six LLM purposes, values are the stage-bound prompt keys shown on that purpose card.
- `ORPHAN_PROMPTS: readonly string[]` — the list of prompt keys rendered on Settings → Assistant Prompts.
- `EXPECTED_PROMPT_KEYS = new Set([...Object.values(PROMPT_PURPOSE_MAP).flat(), ...ORPHAN_PROMPTS])` — derived.

**Exhaustiveness guard.** On app boot the frontend asserts `new Set(Object.keys(systemPromptsResponse.defaults))` equals `EXPECTED_PROMPT_KEYS`; mismatches log a warning with the extra and missing keys so a new stage-bound prompt added to `PROMPTS` without a corresponding `prompt-map.ts` entry doesn't silently land on Settings.

For the multi-prompt case (extraction), pills display which `tool_call_mode` uses each prompt. The currently-overridden prompt shows a `custom` badge on its pill. Below the textarea: character count / 20,000, `Load default` button, `Save override` button (calls existing `PUT /api/v1/config/system-prompts` with empty string to clear).

### 6.4 Dimension-change dialog

The existing obsolete-counts dialog triggered by embedding model or dimensions changes is kept verbatim. Its `Re-embed now` button navigates to `/reindex` (renamed route).

## 7. Backend changes

### 7.1 New endpoints

All new endpoints use `Depends(require_auth)` — same contract as every existing `/api/v1/config/*` route.

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
    available_devices: [{id, label, kind, index}]
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

**Groups live only in `/api/v1/pipeline/metrics`.** The aggregator intentionally does not ship `groups` — that state changes every few seconds as models load and idle, and the metrics endpoint is the single source of truth for it. The Pipeline UI reads groups exclusively from `useMLMetrics()`.

**`POST /api/v1/pipeline/mode`** — preset writer. Body `{"mode": "ml" | "llm"}`. Writes all three stage flags in a single DB transaction, then calls `app.services.pipeline._refresh_flag_cache(session_factory)` so the 5-second `_FLAG_CACHE_TTL` doesn't stall propagation to the running pipeline. Response is intentionally thin — `{mode, stages}` only; the frontend invalidates its `["pipeline"]` query on success to pull the full aggregator state, rather than the endpoint duplicating the aggregator's payload.

**`POST /api/v1/pipeline/unload`** — takes a `group` query param validated as `Literal["extraction","classification","retriever"] | None` via FastAPI's `Query(None)`; unknown values return 422 automatically. Omit for all groups. Body empty. Returns `{unloaded: [...], groups: {...}}`. Calling with nothing loaded is a no-op that returns `{unloaded: [], groups: {...}}` with status 200. Calls the existing `unload_*` functions in `services/ml_models.py` under the appropriate `_GROUP_LOCKS["<group>"]` entry, wrapped in `asyncio.to_thread` because those locks are `threading.Lock` rather than `asyncio.Lock`.

**`GET /api/v1/pipeline/metrics`** — auth-gated host telemetry endpoint. Returns `{cpu_percent, ram_used_mb, ram_total_mb, gpu_util_percent, vram_used_mb, vram_total_mb, groups}` — the per-request host and GPU numbers plus the loaded-groups snapshot. This is a new endpoint *on purpose* rather than extending `/api/health/ml_models` (see 7.2 below).

### 7.2 Health endpoint — unchanged

`GET /api/health/ml_models` stays as-is: unauthenticated, model-loaded status only. The host-level telemetry (`cpu_percent`, `ram_used_mb`, `ram_total_mb`, `gpu_util_percent`, `vram_total_mb`, `vram_used_mb`) moves to the new auth-gated `GET /api/v1/pipeline/metrics` in 7.1 so we don't leak host fingerprinting to unauthenticated callers. `vram_allocated_mb` continues to ship in `/api/health/ml_models` since it's a model-process statistic and existing consumers depend on it.

### 7.3 Dependencies

Add `psutil` and `pynvml` to the backend package manifest. Both are pure-Python pip installs.

- `psutil` works on Linux, macOS, and Windows.
- `pynvml` is Nvidia-specific. On AMD/ROCm, Apple-Silicon MPS, or CUDA-less hosts the module either refuses to initialise or reports no devices. The graceful-degrade path (Section 9) already covers this; no spec change needed, but the implementation must wrap the init call in a try/except and short-circuit when it fails.

### 7.4 Existing endpoints

Every existing config endpoint keeps its current shape and behaviour: the new Pipeline UI writes through them for individual edits. The aggregator is a read shortcut, the mode writer is the only new mutation beyond unload.

## 8. Frontend component inventory

New components under `frontend/src/components/pipeline/`:

| Component | Responsibility |
|---|---|
| `PipelineModeToggle` | Segmented preset + shadow switch + Advanced disclosure with three stage switches |
| `MLPanel` | Composition root for the ML stack side; renders loading overlay while device-apply is pending |
| `MLDeviceSection` | Device picker (disabled during `applyDevice.isPending`) |
| `PersistenceModeToggle` | `[ Persistent | Idle TTL ]` segmented + minutes input; writes `ml_idle_ttl_minutes` |
| `SysMetricsDashboard` | Two tiles (CPU+RAM or GPU+VRAM) + loaded-groups row |
| `UnloadControls` | `Unload all` CTA + per-group Advanced disclosure |
| `UnloadConfirmDialog` | Confirmation shell used only by the `Unload all` CTA |
| `LLMPanel` | Composition root for the LLM side |
| `LLMPurposeCard` | Collapsible card with Model region + integrated System prompts + per-card Save |
| `LLMPurposePromptEditor` | Pills + textarea + save/load controls |

A small `frontend/src/components/pipeline/prompt-map.ts` constant holds the purpose → prompts mapping described in Section 6.3. The Pipeline page root owns the dim-when-inactive logic and passes a `status: "active" | "mixed" | "inactive"` prop down to each panel.

Hooks in **new** file `frontend/src/hooks/api/use-pipeline-config.ts`:

- `usePipeline()` — `GET /api/v1/pipeline` query with `staleTime: 0` and `refetchOnWindowFocus: true` so cross-tab edits reconcile when the tab regains focus.
- `useSetPipelineMode()` — `POST /api/v1/pipeline/mode` mutation. `onSuccess` invalidates `["pipeline"]` to pull full fresh state.
- `useUnloadPipeline()` — `POST /api/v1/pipeline/unload` mutation. `onSuccess` invalidates `["pipeline"]` and `["mlMetrics"]`.
- `useMLMetrics()` — `GET /api/v1/pipeline/metrics` query with `queryKey: ["mlMetrics"]` and `refetchInterval: 5_000`. Source of truth for the loaded-groups row.

Existing hooks (`useLlmConfig`, `useUpdateLlmConfig`, `useFeatureFlags`, `useUpdateFeatureFlags`, `useSystemPrompts`, `useUpdateSystemPrompts`, `useMLDevices`, `useApplyMLDevice`, `useMLModelsHealth`) all stay. **Each of the `useUpdate*` / `useApply*` mutations must add `qc.invalidateQueries({ queryKey: ["pipeline"] })` to its `onSuccess`** so the Pipeline page sees individual-endpoint edits immediately. This is the only required change to the existing hooks.

The Settings page's existing cards that survive (`FeatureFlagsCard` trimmed, `ClassificationAreasCard`, `EnrichmentCard`, and a new `AssistantPromptsCard` scoped to the three orphans) remain self-contained; no cross-page state sharing beyond React Query's cache.

## 9. Error handling

| Failure | Behaviour |
|---|---|
| `GET /api/v1/pipeline` | Full-page error card with status, message, retry button. Page does not become interactive until the aggregator succeeds. |
| `POST /pipeline/mode` | Segmented control reverts to derived state from the last-known flags. Toast the error. |
| `POST /pipeline/unload` | Toast. Next poll of `/api/v1/pipeline/metrics` reconciles the groups row. |
| `POST /config/ml-device/apply` returning `reload_error` | Toast with the error text. Segmented device selection reverts to `effective_device`. Spinner state clears. |
| `GET /api/v1/pipeline/metrics` failure | Individual tiles render `—` with tooltip "metrics unavailable". Loaded-groups row keeps its last known state. |
| `GET /api/health/ml_models` failure | Loaded-groups row dims to last known state; no cascade to other UI (tiles drive off the metrics endpoint, not health). |
| `pynvml` unavailable | `gpu_util_percent` and `vram_total_mb` are `null`; GPU tile shows `—` with tooltip "driver didn't report utilization". VRAM allocated still renders via `torch.cuda.memory_allocated` in `/api/health/ml_models`. |
| `psutil` unavailable | CPU and RAM tiles show `—`. Treated as install-broken; the metrics endpoint should log a warning once at startup. |

## 10. Loading and empty states

- **Page-level.** Skeleton with the three bands (page header, mode toggle card, two-panel grid) outlined while the aggregator resolves. No partial rendering.
- **Metrics dashboard.** Tiles show `—` until the first `/api/v1/pipeline/metrics` response lands. No spinner — 5s cadence.
- **Mode preset.** Optimistic via React Query cache. Since the segmented selection is purely derived from `pipeline.stages`, the optimistic write is implemented as `qc.setQueryData(["pipeline"], prev => ({ ...prev, mode: target, stages: { extraction: target, classification: target, retrieval: target } }))` before the mutation fires. On error the mutation rolls back by invalidating `["pipeline"]`; on success it invalidates to reconcile with the server's authoritative derived state. No local `useState` should ever hold the mode — two sources of truth is the failure mode to avoid.
- **Per-group unload.** Optimistic via the same `setQueryData` pattern on `["mlMetrics"]` — flip the `loaded` flag on the target group's chip before the request fires; invalidate on error to correct.
- **Device apply.** *Not optimistic* — `reload_ml_models()` can block for 5–30 seconds loading CUDA weights. Device picker shows a spinner via `applyDevice.isPending`; the rest of the ML panel disables while pending; a success toast fires on completion with the effective device. A failure toast restores the picker to the prior selection.
- **LLM config saves.** Non-optimistic — the obsolete-counts dialog depends on server-computed fields.
- **No CUDA devices.** Device picker shows only "CPU" with a small note.
- **Fresh install, no LLM config row.** Aggregator composes from `settings.llm_*` env defaults in `backend/app/config.py`; the six purpose cards render with those defaults.
- **Fresh install, no feature-flags row.** Aggregator composes from `FEATURE_FLAGS_DEFAULTS` — mode renders as `"llm"` (all three ML stage flags default `False`), persistence renders as `"ttl"` with 30 minutes, eviction check at 60 seconds.
- **Pipeline init failed at startup.** Aggregator still returns; embedding card's summary shows `(dimensions unknown)` and the obsolete-counts dialog is skipped on save.

## 11. Testing plan

### 11.1 Backend (`backend/tests/`)

- `test_pipeline_aggregator.py` — shape; defaults when DB rows are missing; composition correctness against the four underlying services; `mode` derivation across all-true / all-false / mixed; `persistence` derivation across `ml_idle_ttl_minutes == 0` vs positive.
- `test_pipeline_mode.py` — POST with `"ml"` flips all three stage flags in one transaction; `"llm"` flips them back; unknown value returns 422; existing non-ML feature-flag keys are preserved; `_refresh_flag_cache` is invoked exactly once per successful mode flip.
- `test_pipeline_unload.py` — POST without `group` unloads everything; `group=extraction` unloads only that group; `group=bogus` returns 422 via the FastAPI `Literal` + `Query` validation; calling unload when nothing is loaded returns 200 with `unloaded: []`.
- `test_pipeline_metrics.py` — new endpoint; monkey-patch `psutil` and `pynvml` to return fixed values; assert fields populate; assert `require_auth` is enforced (no-token request returns 401); assert graceful degradation (`null` fields) when either library fails to import or `pynvml` init raises.
- Confirm `test_ml_health_metrics.py` does NOT regress — the health endpoint payload is intentionally unchanged.

### 11.2 Frontend

- `npx tsc --noEmit` must stay green.
- Playwright smoke test: navigate to `/pipeline`, click `Darkmem ML stack`, expand Advanced, verify the three stage switches read `true`. Stubs `/api/v1/pipeline` and `/api/v1/pipeline/metrics` so the test runs without a live backend.
- Playwright test for the `Unload all` confirmation dialog: click the button, verify the dialog appears, click cancel, verify no request fires; re-open, click confirm, verify the request fires with no `group` param.
- Unit test for the `localStorage["darkmem.settings.tab"]` migration: seed `"ml"` → resolves to `"flags"`; seed `"prompts"` → resolves to `"assistant"`; seed `"assistant"` → stays at `"assistant"` (idempotent under React strict-mode double-render).
- Unit test for the exhaustiveness guard on `prompt-map.ts` — fake a new prompt key and assert the boot-time warning fires.
- Existing settings tests keep passing after the tab migration.

### 11.3 Manual QA checklist

- Switch mode ML↔LLM with no in-flight memory-add; verify the three flags in DB flip.
- Start from a fresh container without `pynvml`; confirm `gpu_util_percent` degrades to `—` without crashing the page.
- Open two browser tabs, change the LLM extraction model in one, verify the other picks up the new config on next window-focus (aggregator has `staleTime: 0` + `refetchOnWindowFocus: true`).
- Exercise `Unload all` while a memory-add is in flight; verify the in-flight request completes on the old model group and the next request triggers a fresh lazy-load.

## 12. Open questions / deferred items

- Encryption-at-rest for LLM API keys (deferred to a security pass).
- Admin-role gating on all `/api/v1/config/*` and `/api/v1/pipeline/*` endpoints (deferred).
- Whether `confidence_rank_gamma` belongs on Pipeline vs. Settings long-term — it lives in Settings for this redesign; revisit if user feedback pushes it onto Pipeline.

## 13. Rollout

Three sequential PRs against `master`. Each merges green independently; each is small enough to review in one sitting.

**PR 1 — Backend.** Aggregator + mode + unload + metrics endpoints; `psutil` + `pynvml` dependencies; all new backend tests (`test_pipeline_aggregator.py`, `test_pipeline_mode.py`, `test_pipeline_unload.py`, `test_pipeline_metrics.py`). No frontend changes. The endpoints are dormant until PR 2 wires a UI.

**PR 2 — Pipeline page.** New `pipeline.tsx` route, new `use-pipeline-config.ts` hook file, all components under `frontend/src/components/pipeline/`. Adds invalidation calls on existing `useUpdate*` / `useApply*` mutations. Does NOT yet rename the old `/pipeline` — that ships in PR 3. In this PR the new page lives temporarily at `/pipeline-v2` behind a route alias; existing `/pipeline` keeps pointing at the re-embed page.

**PR 3 — Settings migration + route rename.** Strict rename order (file-based routing means two files cannot both claim `/pipeline` at once):

1. Rename `frontend/src/routes/_authenticated/pipeline.tsx` → `reindex.tsx` (with `createFileRoute("/_authenticated/reindex")`). `/pipeline` is now free.
2. Rename `frontend/src/routes/_authenticated/pipeline-v2.tsx` → `pipeline.tsx` (with `createFileRoute("/_authenticated/pipeline")`). `/pipeline-v2` is now free.
3. Add the `/llm` → `/pipeline` redirect.
4. Run the internal-link audit and update every `to="/pipeline"` that referred to the old re-embed page.
5. Split Settings tabs per Section 3.3 and ship the `localStorage["darkmem.settings.tab"]` migration shim.

Commit these as distinct commits within PR 3 so the rename is visible in isolation — reviewers can verify the TanStack Router generated route tree at each step.

The PR boundaries are chosen so that URL-facing breakage happens in exactly one PR (PR 3), which can be released together with a changelog note. Anyone reviewing PR 3 can verify the redirect is in place just by diffing the route files.

## 14. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `pynvml` init fails silently on non-Nvidia hosts, leaving the GPU tile empty | Medium | Low (tiles show `—`) | Log once at startup; document in `/api/v1/pipeline/metrics` endpoint docstring that pynvml is optional. |
| Tab-migration shim runs twice in dev (React strict-mode double-render) and re-maps already-migrated keys | Low | Low (shim is idempotent) | Shim compares the stored key to the current `SETTINGS_TABS` set; only remaps known-legacy keys. |
| `/pipeline` route collision with an unreviewed internal `<Link to="/pipeline">` missed in the audit | Medium | Medium (broken link lands on new Pipeline page instead of reindex) | Internal-link audit during PR 3; route-integration test that asserts `<Link to="/reindex">` resolves on the re-embed dialog and obsolete-count dialog. |
| Device apply UI appears successful while 5–30s CUDA load still in progress | Medium | Medium (users ingest memories on old device) | Device picker disabled during `applyDevice.isPending`; spinner on the card; success/failure toast on completion. Non-optimistic by design. |
| `Unload all` misclick during ingestion cascades reloads | Medium | Medium (seconds of latency per request until models re-warm) | Confirmation dialog (Section 5.5). |
| Extending `/api/health/ml_models` would leak host telemetry | — | — | **Avoided in this spec** — metrics live on the auth-gated `/api/v1/pipeline/metrics` endpoint instead. |
| Aggregator cached response goes stale after individual-endpoint writes | Medium | Medium (Pipeline page shows outdated config) | Every existing `useUpdate*` / `useApply*` mutation invalidates `["pipeline"]` on success (Section 8). |
| Mode flip doesn't reach the running pipeline for ~5s due to `_FLAG_CACHE_TTL` | Medium | Low (next extraction still uses old path) | `POST /pipeline/mode` invalidates the cache via `_refresh_flag_cache` (Section 7.1). |
| New stage-bound prompt added to `PROMPTS` without updating `prompt-map.ts` | Low | Medium (prompt silently lands on Settings) | Boot-time exhaustiveness guard logs a warning (Section 6.3) + unit test (Section 11.2). |

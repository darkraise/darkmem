## PR 1 — Pipeline backend

Adds four new endpoints under `/api/v1/pipeline` + host-metrics instrumentation.

**New endpoints (auth-gated):**
- `GET /api/v1/pipeline` — aggregator for the upcoming Pipeline UI page.
- `POST /api/v1/pipeline/mode` — preset writer, flips all three ML stage flags atomically.
- `POST /api/v1/pipeline/unload` — unloads ML groups (all or one via `?group=`).
- `GET /api/v1/pipeline/metrics` — auth-gated CPU/RAM/GPU telemetry.

**Unchanged on purpose:** `/api/health/ml_models` keeps its current payload. Host telemetry lives on the new auth-gated endpoint to avoid leaking fingerprinting to unauthenticated callers.

**New deps:** `psutil`, `pynvml` (pynvml degrades gracefully on non-Nvidia hosts).

Endpoints are dormant until PR 2 adds the UI.

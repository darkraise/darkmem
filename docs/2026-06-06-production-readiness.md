# Darkmem — Production-Readiness Audit (2026-06-06)

An operational/release audit across 10 dimensions (security, deployment,
configuration, reliability, performance, data durability, observability,
frontend build, testing/CI, docs/licensing). This is **separate** from the
code-correctness audit (`docs/2026-06-06-comprehensive-audit.md`, remediated on
`fix/audit-2026-06-06`); it asks whether darkmem is safe and operable to **run
in production**, not whether the code is bug-free.

## Verdict: NO-GO (as shipped)

The codebase is functionally solid, but the **release/operational surface is not
production-ready**. A literal `docker compose up` of the shipped `docker-compose.yml`
deploys a system with its security hardening silently disabled, no backups, no
operator documentation, no CI gate, and an unauthenticated tool endpoint reachable
from the network. None of the blockers are deep — most are configuration, packaging,
and ops-tooling gaps — but they must be closed before any production release.

| Severity | Count |
| --- | --- |
| Launch-blocker | 9 |
| High | ~18 |
| Medium | ~10 |
| Low | several |

Per-dimension verdict: **config/env, docs/licensing, data-durability, secrets/auth,
containers, frontend, testing/CI = not-ready**; **reliability, performance,
observability = needs-work**.

---

## Launch-blockers (must fix before release)

### LB1 — `ENVIRONMENT=production` is never set, so every prod guard is off
`docker-compose.yml` sets only `DATABASE_URL`/`JWT_SECRET`/`API_KEY_HMAC_SECRET`;
`config.py` defaults `environment="development"`. The JWT-strength validator,
the SETUP_SECRET requirement, and the auth-cookie `Secure` flag (`auth.py:56`)
all gate on `environment == "production"`. With the shipped compose they only
**warn** (and may not even log — see LB-obs), so prod boots with a weak/default
JWT secret, an unauthenticated `/setup` window, and session cookies sent in the
clear. **Fix:** set `ENVIRONMENT=production` in compose; the existing fail-fast
validators then do their job. (Root cause of the cookie-`Secure` blocker too.)

### LB2 — No LICENSE (legal blocker for distributing the images)
No `LICENSE` anywhere, and neither `backend/pyproject.toml` nor
`frontend/package.json` declares a license, yet compose ships
`darkraise/darkmem-api:latest` / `darkmem-ui:latest`. Without a license, default
copyright forbids others from using/deploying the images. **Fix:** choose and add
a license (this needs your decision — see the question at the end) and declare it
in both manifests.

### LB3 — No README / operator documentation
Repo root has only `CLAUDE.md` (dev-internal). There is no quickstart, deployment
guide, env reference, setup-wizard walkthrough, backup/upgrade runbook, or the
critical `ENVIRONMENT=production` instruction. An operator following the repo
cannot produce a safe deployment. **Fix:** author a production README + a deploy
runbook.

### LB4 — MCP endpoint is unauthenticated and re-exposed through the UI proxy
`/mcp` is mounted with no auth (`main.py:334`, `mcp/server.py`); every tool
(`memory_add`, `memory_delete`, `code_search`, …) is reachable by anyone who can
hit it. The API is loopback-bound, but the UI container publishes `0.0.0.0:3000`
and nginx proxies `/api`, `/ws`, **and `/mcp`** to it, so exposing the UI
re-exposes the unauthenticated tool surface to the LAN/internet. **Fix:** gate
`/mcp` behind auth (or a dedicated MCP token), or block `/mcp` at the nginx layer
and bind the UI to loopback behind a TLS/auth proxy.

### LB5 — No `.dockerignore`; `frontend/.env` enters the build context
Neither `backend/` nor `frontend/` has a `.dockerignore`, and `frontend/Dockerfile`
does `COPY . .`. The committed `frontend/.env` (plus `node_modules`, `dist`,
`.git`) lands in the build layer, and Vite inlines any `VITE_*` vars into the
shipped bundle. **Fix:** add `.dockerignore` to both contexts; verify no secret is
in `frontend/.env`.

### LB6 — No backup/restore for the `postgres_data` volume
All state (memories, graph, embeddings, auth/LLM config) lives in one named volume
with no `pg_dump` job, WAL archiving, snapshot script, or runbook. A `down -v`,
volume prune, disk failure, or botched upgrade is unrecoverable. **Fix:** ship a
scheduled backup (dump sidecar or WAL archiving) to off-host storage + a documented
restore procedure.

### LB7 — Destructive migration runs automatically on boot, with a multi-replica race
`entrypoint.sh` runs `alembic upgrade head` on every container start. Migration
`0003` unconditionally `DELETE`s `code_edges`/`code_graph_nodes` and nulls
`last_indexed_commit` — the first deploy silently wipes the code graph (recoverable,
it's derived, but unannounced). Two replicas starting together race on
`alembic_version` with no advisory lock. **Fix:** run migrations as a one-shot init
step (separate service / advisory lock); document the 0003 graph rebuild in release
notes; backup-before-migrate.

### LB8 — No security headers in the nginx serving layer
`frontend/nginx.conf` sets none of CSP, `X-Frame-Options`, `X-Content-Type-Options`,
`Referrer-Policy`, or HSTS. The app (which holds API keys) is clickjackable and
MIME-sniffable. **Fix:** add the baseline headers + a CSP validated against the
Three.js/sigma bundle.

### LB9 — No CI gate before images are published
No `.github/workflows` (or any pipeline). The only release path,
`scripts/build-push.sh`, runs `docker build && docker push …:latest` with **no**
pytest/vitest/tsc/lint/scan first, from any working tree. The ~568 backend / ~106
frontend tests exist but nothing enforces them, and backend deps are unpinned
(`pip install .` with `>=` ranges, no lockfile) so builds aren't reproducible.
**Fix:** add CI (test against an ephemeral pgvector service, vitest, tsc, ruff,
image scan) gating a tagged push; commit a backend lockfile.

---

## High-severity (fix before launch or immediately after)

**Secrets/auth & config**
- `API_KEY_HMAC_SECRET` is injected by compose but read nowhere in the backend — dead, security-suggestive config. Remove it (or implement API-key auth).
- `CORS_ORIGINS` unset falls back to `localhost:3000/5173` with `allow_credentials` (`main.py:302-308`) — wrong for a real hostname (though the bundled UI is same-origin via relative `/api/v1`, so it may not bite the default topology).
- Git auth tokens and LLM provider api_keys stored **plaintext** at rest (`repo_manager.py:161`, `llm_config.py:34-47`) — a volume/dump snapshot leaks every credential. Encrypt at rest or document + access-control the volume.
- Login rate-limiter is per-process in-memory keyed on client IP; behind the bundled nginx with `trust_proxy_headers=false` (default) all clients share one bucket (lockout DoS); resets on restart.
- `.env.example` is misleading: weak `DB_PASSWORD=darkmem`, placeholder `JWT_SECRET`, legacy unused `LLM_*` JSON, omits real settings (ENVIRONMENT, CORS_ORIGINS, TRUST_PROXY_HEADERS, DB_POOL_SIZE, LLM_CLASSIFICATION).

**Observability**
- No application logging configuration at all (no `dictConfig`/handler/level); relies on uvicorn defaults, so most `logger.info` (incl. pipeline lifecycle + LLM token telemetry) is dropped.
- Logs are plain f-strings, not structured; no request-ID/correlation; no tracing.
- No error alerting/monitoring (no Sentry/OTel/Prometheus); the metrics endpoint is auth-gated and exposes only host CPU/RAM/GPU, no app counters.

**Performance/scale**
- Code indexing holds every changed file's full text in `self._parsed` for the whole pipeline; a large repo OOM-kills the 512m api container mid-index (leaves repo stuck `indexing`).
- DB pool (30/process) vs untuned Postgres `max_connections=100` and the 512m limit; per-phase session fan-out can exhaust the pool under concurrent ingest+jobs; 2-3 replicas approach the server cap.

**Reliability**
- Several fire-and-forget `asyncio.create_task` calls (retry, reembed, orchestrator-close in `pipeline_failures.py`, `reembed.py`, `config.py`, `pipeline.py`) store no reference and aren't in `TaskRegistry` — can be GC'd mid-run and aren't cancelled on SIGTERM.
- No DB connectivity probe at startup — the app boots "green" when Postgres is down; every request then fails.

**Containers**
- Single uvicorn worker, no init/PID-1 reaper (zombie `git` children from repo sync), no `--timeout-graceful-shutdown`; `:latest` tags are non-reproducible; only the api has a (memory-only) resource limit.

**Data durability**
- `memories.expires_at` retention is dead — accepted, stored, never swept; TTL'd memories live forever.
- Embedder retirement leaves orphan partition tables (`memory_embeddings__*` etc.) that grow unbounded across model rotations (`retired_at` is read but never written; only the cache partition is pruned).

**Testing/CI**
- No backend linter/type-checker configured (no ruff/mypy); no image vulnerability scanning/SBOM; version drift (`pyproject 0.1.0` vs `main.py 0.2.0`); the end-to-end `process_batch` test is skipped.

---

## Medium / Low (representative)
- No Docker healthcheck on `darkmem-api` despite a well-built `/health` (503 on pgvector down, 200/degraded on LLM down); UI `depends_on` is start-order only.
- `TRUST_PROXY_HEADERS=false` default + bundled nginx breaks rate-limiter IP attribution; nginx forwards `X-Real-IP` but not `X-Forwarded-For`.
- nginx lacks gzip, asset caching (`immutable`), `client_max_body_size`, and `/ws` `proxy_read_timeout` (idle pipeline sockets drop at 60s; prod entrypoint also drops the dev `--timeout-keep-alive 75`, reintroducing the keep-alive 502 race).
- `_is_production()` in `setup.py` (`/.dockerenv` probe) diverges from `config.py` and can self-lockout a containerized non-prod install (503 on /setup when SETUP_SECRET empty).
- FastAPI `/docs`, `/redoc`, `/openapi.json` served unauthenticated by default.
- No down-migration recovery; no dependency-license inventory; no upgrade guide.
- WebSocket has no reconnect resync (events missed during a disconnect are lost) — a real freshness gap (the higher-value reliability fix).
- Vector analytics endpoints load up to 500 embeddings + DBSCAN/Louvain in-process on the request thread (bounded by caps, but a memory/CPU spike risk alongside indexing).
- LLM transient 429/5xx have no retry/backoff (only connection-level retries) — failures churn `pipeline_failures` rows.

## Confirmed strengths (preserve)
- `/health` status-code policy is well-designed (hard-fail pgvector, soft-fail LLM).
- No secrets are logged (token counts only; git URLs scrubbed).
- HNSW + GIN index coverage on the hot retrieval paths is correct and production-grade.
- Embedding child tables FK-cascade on delete (clean per-row deletes).
- `JobRegistry` shuts down cleanly; pipeline writes use savepoints (interrupted writes roll back atomically — no half-written graph).
- Postgres image is version-pinned; demo data is tree-shaken out of the prod bundle; no prod source maps; relative API base.

---

## Prioritized launch checklist

**P0 — blockers (do before any release):**
1. Set `ENVIRONMENT=production` in compose; add an `env`-driven secret-generation step; verify the validators fail-fast on weak secrets. (LB1)
2. Add `LICENSE` + declare it in both manifests. (LB2 — needs your license choice)
3. Write a production README + deploy/backup/upgrade runbook. (LB3)
4. Gate or proxy-block `/mcp`; bind the UI behind TLS/auth (don't publish `0.0.0.0:3000`). (LB4)
5. Add `backend/.dockerignore` and `frontend/.dockerignore`. (LB5)
6. Add a backup/restore mechanism + runbook for `postgres_data`. (LB6)
7. Decouple migrations from app start (one-shot/advisory-lock); document the 0003 graph rebuild. (LB7)
8. Add nginx security headers + CSP. (LB8)
9. Add a CI pipeline (test/lint/type/scan → gated tagged push) + commit a backend lockfile. (LB9)

**P1 — high (before launch / first week):** remove `API_KEY_HMAC_SECRET`; set `CORS_ORIGINS` + `TRUST_PROXY_HEADERS`; encrypt secrets at rest (or document); add logging `dictConfig` + structured logs + request-ID; fix code-indexing memory footprint; tune pool vs `max_connections`; strong-reference background tasks + cancel on shutdown; DB startup probe; add api healthcheck; pin backend deps; add ruff + image scan; sweep `expires_at`; drop orphan embedding partitions on retirement; rewrite `.env.example`.

**P2 — medium/low:** WebSocket reconnect resync; nginx gzip/caching/ws-timeout; unify `_is_production`; gate `/docs` in prod; move analytics clustering off the request thread; LLM 429/5xx backoff; error alerting hook; dependency-license inventory.

---

## Next step
I'll start remediating the code/config blockers and high items I can resolve
deterministically (ENVIRONMENT + compose hardening, `.dockerignore`, nginx headers,
healthcheck, logging config, MCP gating, `.env.example`, README, backup script + CI,
and the reliability/perf/durability code fixes). Two items need **your** input
because they're genuine product/ops decisions: which **license** to apply, and the
**deployment topology** (is the UI meant to be public behind your own TLS proxy, or
strictly LAN/loopback?). Everything else I can take to green.

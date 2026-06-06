# darkmem

A centralized memory system for AI agents: stores and retrieves natural-language
**memories** (semantic + keyword hybrid search over pgvector), builds an
**entity/relationship knowledge graph** from them, and indexes **code
repositories** into a navigable symbol/call graph. It exposes a REST API, a
WebSocket event stream, and an **MCP** tool endpoint for agents, with a React UI.

- **Backend:** FastAPI + SQLAlchemy (async) + Postgres/pgvector
- **Frontend:** React + TanStack Router/Query (served by nginx)
- **LLM:** pluggable per-purpose providers (OpenAI-compatible, Ollama, Anthropic,
  Google, DeepSeek, z.ai), configured at runtime via the setup wizard

> Licensed under Apache-2.0 (see `LICENSE`).

---

## Quickstart (Docker Compose)

Prerequisites: Docker + Docker Compose v2.

```bash
cp .env.example .env
# Edit .env: set ENVIRONMENT=production and generate strong secrets:
#   DB_PASSWORD   = openssl rand -base64 24
#   JWT_SECRET    = openssl rand -hex 32      (must be >= 32 chars)
#   SETUP_SECRET  = openssl rand -hex 32
# Pin the image tag for a real deploy:  DARKMEM_VERSION=0.2.0

docker compose up -d
```

The API boots only after Postgres is healthy, runs database migrations
automatically, then serves on `127.0.0.1:8000`. The UI is on `127.0.0.1:3000`.

Both services bind to **loopback** by design (single-operator / LAN model). To
reach the UI from another machine, put your own **TLS-terminating reverse proxy**
(nginx/Caddy/Traefik) in front of `127.0.0.1:3000` — the session cookie is only
sent with the `Secure` flag over HTTPS.

### First-run setup

Open the UI and complete the setup wizard (`/setup`):

1. Set the admin password (you authenticate as a single admin).
2. Configure LLM providers and assign a model to each **purpose** (embedding,
   extraction, classification, reasoning, summarization, reranker). LLM config
   lives in the database — it is **not** set via environment variables.
3. Optionally register a repository path to index.

`/setup` is gated by `SETUP_SECRET` in production (supply it via the
`X-Setup-Secret` header / wizard), so the admin bootstrap can't be claimed by
anyone else on the network.

---

## Configuration reference

All backend settings are environment variables (see `.env.example`). The
production-critical ones:

| Variable | Required in prod | Purpose |
| --- | --- | --- |
| `ENVIRONMENT` | **yes** (`production`) | Arms fail-fast validators (JWT strength, SETUP_SECRET) and the `Secure` cookie. Without it the app runs in dev posture with guards off. |
| `DB_PASSWORD` | **yes** | Postgres password (used in `DATABASE_URL`). |
| `JWT_SECRET` | **yes** | Session-token signing key. Must be ≥ 32 chars and not a placeholder, or the app refuses to boot. |
| `SETUP_SECRET` | **yes** | Gates the `/setup` admin bootstrap. |
| `TRUST_PROXY_HEADERS` | recommended `true` | Honor `X-Forwarded-For` from the bundled nginx so the login rate limiter sees real client IPs. Keep `false` only if the API has no trusted proxy in front. |
| `CORS_ORIGINS` | only if cross-origin | Comma-separated browser origins. Usually empty (UI is same-origin behind nginx). |
| `DARKMEM_VERSION` | recommended | Image tag for compose; pin to a release. |
| `LOG_LEVEL` | no | `DEBUG`/`INFO`/`WARNING`/`ERROR` (default `INFO`). |

Runtime **LLM configuration is stored in the database** via the setup wizard and
the Settings → LLM Pipeline UI; there are no `LLM_*` environment variables.

---

## Operations

### Health

`GET /health` is the liveness/readiness probe (used by the compose healthcheck):
`503` when Postgres/pgvector is unreachable, `200` (degraded) when only the LLM
provider is unreachable. The container is `unhealthy` until the API can serve.

### Backups (do this before going live)

**All state lives in the `postgres_data` Docker volume.** There is no automatic
backup — losing the volume loses everything. Use the provided scripts and run
them on a schedule (cron):

```bash
./scripts/backup.sh /path/to/backups        # writes darkmem-YYYYMMDD-HHMMSS.sql.gz
./scripts/restore.sh /path/to/backups/darkmem-20260607-030000.sql.gz
```

Store backups off-host. Always **back up before an upgrade**.

### Upgrades

1. Back up (above).
2. Pull the new image tag (bump `DARKMEM_VERSION` in `.env`).
3. `docker compose up -d`.

Migrations run automatically on API startup (`alembic upgrade head`). Notes:

- The first upgrade to 0.2.0 runs migration `0003`, which **rebuilds the derived
  code graph** (it clears `code_edges`/`code_graph_nodes` and forces a reindex on
  next sync). Memories and code symbols are untouched; the graph is regenerated.
- Migrations run inline at startup, so run **one API replica at a time** during an
  upgrade (the bundled topology is single-replica). Downgrades are not a recovery
  path — restore from backup if a migration fails.

### Logs & diagnostics

Logs go to the container stdout (`docker compose logs -f darkmem-api`), formatted
with timestamp/level/logger and controlled by `LOG_LEVEL`. Pipeline failures are
recorded in the database and surfaced under Settings → Pipeline. No secrets are
logged (token counts and scrubbed git URLs only).

### Security checklist (before exposing beyond loopback)

- [ ] `ENVIRONMENT=production`, strong `JWT_SECRET` (≥32 chars) and `SETUP_SECRET`, non-default `DB_PASSWORD`.
- [ ] UI reached only through your TLS reverse proxy (HTTPS); do not publish port 3000 publicly.
- [ ] `/mcp` is the **unauthenticated** agent tool endpoint — keep it on loopback (it is not proxied by the bundled UI). Never expose it to untrusted networks.
- [ ] FastAPI `/docs`, `/redoc`, `/openapi.json` are served unauthenticated — keep them behind the loopback bind / your proxy's auth.
- [ ] Provider API keys and git tokens are stored in the database in plaintext (single-operator model) — keep the `postgres_data` volume and backups access-controlled and encrypted at rest.

---

## Development

```bash
docker compose -f docker-compose.dev.yml up -d   # builds locally, hot-reload, ports on all interfaces
```

Backend tests (need a `darkmem_test` database on the dev Postgres):

```bash
cd backend && python -m pytest -q
```

Frontend:

```bash
cd frontend && npm ci && npm run typecheck && npx vitest run && npm run build
```

See `CLAUDE.md` for the internal architecture/business-logic contract and `docs/`
for design specs and audit reports.

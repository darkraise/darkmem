# darkmem

[![CI](https://github.com/darkraise/darkmem/actions/workflows/ci.yml/badge.svg)](https://github.com/darkraise/darkmem/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

A centralized memory system for AI agents. It stores and retrieves
natural-language **memories** (hybrid semantic + keyword search over pgvector),
builds an **entity/relationship knowledge graph** from them, promotes
corroborated claims into a **verified fact layer**, and indexes **code
repositories** into a navigable symbol and call graph.

One container serves it all: a REST API, a WebSocket event stream, an **MCP**
endpoint for agents, and the web UI.

- **Backend:** FastAPI + SQLAlchemy (async) + Postgres/pgvector
- **Frontend:** React + TanStack Router/Query, built into the API image
- **Models:** pluggable per purpose — OpenAI-compatible, Ollama, Anthropic,
  Google, DeepSeek, z.ai — configured at runtime, never in environment variables

---

## Documentation

| Guide | For |
| --- | --- |
| [Introduction](docs/wiki/introduction.md) | What it is, what it stores, what it is not |
| [Quick Start](docs/wiki/quick-start.md) | Running in ten minutes |
| [Deployment Guide](docs/wiki/deployment-guide.md) | Backups, upgrades, exposing it safely |
| [Usage Guide](docs/wiki/usage-guide.md) | Day-to-day use and agent patterns |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Changing the code |

`CLAUDE.md` is the internal business-logic contract; `docs/design/` holds design
specifications and `docs/` the audit reports and operator runbooks.

---

## Quickstart

Prerequisites: Docker and Compose v2.

```bash
git clone https://github.com/darkraise/darkmem.git
cd darkmem
cp .env.example .env
# Generate the two secrets in .env:
#   DB_PASSWORD = openssl rand -base64 24
#   JWT_SECRET  = openssl rand -hex 32     (32+ chars, or the app refuses to boot)
# Reaching the UI over plain HTTP? Also set COOKIE_SECURE=false.

docker compose up -d
```

Postgres comes up first; the API then migrates the database, verifies the
schema matches the code, and serves everything on **`:8000`** — REST, WebSocket,
MCP and the UI. One container, one port. Nothing binds `:80`, and Postgres
stays on loopback.

Open `http://localhost:8000` and complete the setup wizard.

### Images

Published to two registries on every version tag, from one build:

```bash
docker pull darkraise/darkmem:1.0.0            # Docker Hub
docker pull ghcr.io/darkraise/darkmem:1.0.0    # GHCR
```

Pin the tag in production with `DARKMEM_VERSION` — `latest` moves under you.

### First-run setup

`/setup` is **trust-on-first-use**: it stays open only until an admin password
exists, so the first caller to finish claims the account. Run it promptly, on a
network you trust.

The wizard sets the admin password, then assigns a model to each of the eight
**purposes** — `embedding`, `extraction`, `classification`, `reasoning`,
`summarization`, `reranker`, `verification`, `synthesis`. Each carries its own
model, base URL and key, so cheap and expensive work can sit on different
providers. `embedding` and `extraction` are the two that matter on day one.

Model configuration lives in the database. There are no `LLM_*` environment
variables.

---

## Configuration

All backend settings are environment variables (see `.env.example`). The ones
that matter in production:

| Variable | Required | Purpose |
| --- | --- | --- |
| `DB_PASSWORD` | **yes** | Postgres password; the API derives its connection URL from it. |
| `JWT_SECRET` | **yes** | Session signing key. Must be ≥ 32 chars and not a placeholder, or the app refuses to boot. |
| `DARKMEM_VERSION` | recommended | Image tag compose deploys. Pin it to a release. |
| `COOKIE_SECURE` | no (`true`) | `false` allows login over plain HTTP on a trusted LAN; the cookie then travels in cleartext. |
| `TRUST_PROXY_HEADERS` | no (`false`) | Turn on only when a trusted TLS proxy really is in front. |
| `MCP_ALLOWED_HOSTS` | no (empty) | Host allowlist for `/mcp`, applied *beside* the bearer-key requirement. Empty means localhost only. |
| `LOG_LEVEL` | no (`INFO`) | `DEBUG`/`INFO`/`WARNING`/`ERROR`. |

`ENVIRONMENT=production` is set by the compose file, not by you; it arms the
fail-fast validators and the `Secure` cookie default.

Both secrets are read at runtime and baked into no image layer, so rotating one
is "edit `.env`, `docker compose up -d`" — a container recreate, never a
rebuild.

### Network posture

The app is the network edge by default: it trusts no proxy headers and the
login rate limiter keys on the transport peer. Putting a **TLS-terminating
reverse proxy** in front is a different posture — that proxy becomes the edge,
so set `TRUST_PROXY_HEADERS=true` as well, or every client shares the proxy's
single rate-limit bucket. With proxy headers trusted, `COOKIE_SECURE=false` is
clamped back to `true` and the clamp is reported rather than silent.

---

## Operations

**Health.** `GET /health` is the liveness probe: `503` when Postgres/pgvector is
unreachable, `200` with a degraded body when only the model provider is down.

**Backups.** All state lives in the `postgres_data` volume; there is no
automatic backup.

```bash
./scripts/backup.sh /path/to/backups     # prunes to the newest BACKUP_KEEP (14)
./scripts/restore.sh /path/to/backups/darkmem-20260820-033000.sql.gz
```

Store them off-host, and back up before every upgrade. The
[Deployment Guide](docs/wiki/deployment-guide.md) has a systemd timer for this.

**Upgrades.** Back up, bump `DARKMEM_VERSION`, `docker compose up -d`.
Migrations run at startup, followed by a schema guard that refuses to boot if
the database does not match the code. There is no downgrade path — restore from
backup.

**One replica.** Exactly one worker, one replica, on every launch path. The job
scheduler, WebSocket fan-out and rate limiter are all in-process state; two
processes break seventeen documented assumptions. Raising it is a deliberate
decision, not a flag.

**Logs.** `docker compose logs -f darkmem`. No secrets are logged — token counts
and scrubbed git URLs only.

### Security checklist (before exposing beyond loopback)

- [ ] Strong `JWT_SECRET` (≥ 32 chars) and a non-default `DB_PASSWORD`. Run
      `/setup` immediately — it is open until the admin password is set.
- [ ] UI reached only through your TLS reverse proxy; do not publish `:8000`
      publicly. Set `TRUST_PROXY_HEADERS=true` when you add that proxy.
- [ ] **`/mcp` requires a bearer API key** on every call, scoped per tool, and
      the Host allowlist still applies beside it. Mint keys in Settings → API
      keys. Keep `/mcp` off the public side regardless: a key authenticates a
      caller, it does not make the surface safe to expose.
- [ ] `/docs`, `/redoc` and `/openapi.json` are served unauthenticated — keep
      them behind your proxy's auth.
- [ ] Provider keys and git tokens are stored in the database in plaintext
      (single-operator model). Access-control the volume and every backup, and
      encrypt them at rest.
- [ ] The audit journal is append-only and outlives deletion of a memory. A
      secret pasted into a memory needs rotating, not deleting.

---

## Development

```bash
docker compose -f docker-compose.dev.yml up -d      # Postgres on 127.0.0.1:5433
```

```bash
cd backend  && python -m pytest -q
cd frontend && npm ci && npm run typecheck && npm test && npm run build
```

One command decides mergeability:

```bash
./scripts/gate.sh
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow, the commit
convention, and the schema rule that applies before the freeze.

---

## License

Apache-2.0 — see [LICENSE](LICENSE).

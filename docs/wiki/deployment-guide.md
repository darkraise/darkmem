# Deployment Guide

Running darkmem as something you depend on, rather than something you are
trying out. Assumes you have finished the [Quick Start](quick-start.md).

This is the user-facing guide. The operator runbooks in `docs/` —
`runbook-deployment.md`, `runbook-exposed-deployment.md`,
`runbook-content-purge.md` — carry the procedures for this specific homelab and
go deeper where it matters.

---

## The topology

Two containers on their own bridge network:

| Service | Published on | Reachable from |
| --- | --- | --- |
| `darkmem` | `8000:8000` | anywhere that can route to the host |
| `postgres` | `127.0.0.1:5432:5432` | the host loopback only |

One image carries **both** the API and the built web UI, and serves them on the
same port. Nothing binds `:80`. Postgres is deliberately not on the LAN; the
loopback publish is there so host-side `pg_dump` and `psql` keep working.

**The app is the network edge by default.** It trusts no proxy headers, and the
login rate limiter keys on the transport peer. That changes if you put TLS in
front — see [Exposing it beyond the LAN](#exposing-it-beyond-the-lan).

## Getting the image

Published on a tag, to two registries, from the same build:

```bash
docker pull darkraise/darkmem:1.0.0          # Docker Hub
docker pull ghcr.io/darkraise/darkmem:1.0.0  # GitHub Container Registry
```

**Pin a version in production.** `latest` moves under you on the next release:

```bash
# .env
DARKMEM_VERSION=1.0.0
```

To build locally instead:

```bash
DARKMEM_PUSH=0 ./scripts/build-push.sh 1.0.0
DARKMEM_VERSION=1.0.0 docker compose up -d
```

## Configuration

Everything is `.env`, read at runtime and baked into no image layer — so
rotating a secret is `docker compose up -d`, never a rebuild.

| Variable | Required | What it does |
| --- | --- | --- |
| `DB_PASSWORD` | **yes** | Postgres password. The app derives its connection URL from it. |
| `JWT_SECRET` | **yes** | Session signing key, 32+ chars. A short or placeholder value fails the boot. |
| `COOKIE_SECURE` | no (`true`) | `false` permits login over plain HTTP on a trusted LAN. |
| `DARKMEM_VERSION` | recommended | Image tag compose deploys. Pin it. |
| `TRUST_PROXY_HEADERS` | no (`false`) | Turn on **only** when a trusted TLS proxy is genuinely in front. |
| `MCP_ALLOWED_HOSTS` | no (empty) | Host allowlist for `/mcp`. Empty means localhost only. |
| `LOG_LEVEL` | no (`INFO`) | `DEBUG`/`INFO`/`WARNING`/`ERROR`. |

Model configuration is **not** here — it lives in the database, set through the
setup wizard and **Settings → LLM Pipeline**.

## Backups

**All state is in the `postgres_data` Docker volume.** Lose it and you lose
everything: memories, graph, facts, code index, settings, credentials.

```bash
./scripts/backup.sh /path/to/backups     # darkmem-YYYYMMDD-HHMMSS.sql.gz
./scripts/restore.sh /path/to/backups/darkmem-20260820-033000.sql.gz
```

`backup.sh` prunes to the newest `BACKUP_KEEP` dumps (default **14**). Keep
that pruning: an unpruned nightly dump on the host that also runs the database
fills the disk and takes production down with it.

`restore.sh` **drops and recreates** the database and prompts before doing it.
Stop the app first. It replays into an empty database on purpose: a
`--clean` dump cannot be replayed over a live schema, because PostgreSQL
refuses to drop the `events` partitions' inherited primary keys and psql
aborts partway through the dump's DROP phase.

### Schedule it

A systemd timer is more reliable than cron here, because `Persistent=true`
catches up a run the host slept through:

```ini
# /etc/systemd/system/darkmem-backup.service
[Unit]
Description=darkmem database backup
[Service]
Type=oneshot
WorkingDirectory=/path/to/darkmem
ExecStart=/path/to/darkmem/scripts/backup.sh /var/backups/darkmem
```

```ini
# /etc/systemd/system/darkmem-backup.timer
[Unit]
Description=Nightly darkmem backup
[Timer]
OnCalendar=*-*-* 03:30:00
Persistent=true
[Install]
WantedBy=timers.target
```

```bash
sudo systemctl enable --now darkmem-backup.timer
```

> **Dumps on the same host are not a backup.** Copying them off-host is a
> separate step and nothing enforces it. A disk failure takes the database and
> every dump beside it.

## Upgrades

1. **Back up.** Every time. Restoring is the only recovery path — there is no
   downgrade.
2. Bump `DARKMEM_VERSION` in `.env`.
3. `docker compose up -d`.

The app runs `alembic upgrade head` at startup, then a **schema guard** that
compares a hash of the schema definition against what the database was actually
built with. If they disagree it **refuses to start** and prints the remedy.

That guard exists because of a real incident: before the schema is frozen, a
change *regenerates* the single baseline migration in place rather than adding
a new one, so the revision id never moves and `alembic upgrade head` finds
nothing to do. Production ran for days against a schema missing five columns,
reporting clean migrations the whole time. The guard fails closed and has no
override flag on purpose.

**Practical consequence:** if the guard stops your upgrade, the database needs
recreating from the new schema and reseeding — do not go looking for a bypass.
`docs/runbook-deployment.md` has the procedure.

## Run one replica

Exactly one app process. Not two workers, not two replicas.

This is not conservatism: an audit found 38 in-process assumptions, 17 of which
break outright at two processes. The job scheduler holds no lease, so all
twenty-odd jobs would fire once per process per tick; the WebSocket fan-out,
the login rate limiter and several job cursors are all in-process state. The
knob has three spellings — `--workers`, the `WEB_CONCURRENCY` environment
variable, and compose `deploy.replicas` — and none of them belongs in an ops
change here.

## Exposing it beyond the LAN

The default posture assumes you are the network edge. Putting darkmem on the
public internet is a different posture with real obligations:

1. **Terminate TLS in front** (nginx, Caddy, Traefik). That proxy becomes the
   edge.
2. **Set `TRUST_PROXY_HEADERS=true`.** Without it every client shares the
   proxy's single rate-limit bucket, so one attacker locks out everyone.
3. **Expect `COOKIE_SECURE` to be forced on.** With proxy headers trusted, an
   explicit `false` is clamped to `true` and the clamp is reported — in a boot
   warning, in the audit journal, and on `GET /auth/security-posture`.
4. **Do not route `/mcp` from the public side.** It is unauthenticated by
   design; a Host allowlist is its only defence. Bearer auth for it is designed
   and *not shipped*.
5. **Keep `/docs`, `/redoc` and `/openapi.json` behind your proxy's auth.**
   They are served unauthenticated.

`docs/runbook-exposed-deployment.md` is the full procedure.

## Operating it

### Health

`GET /health` is the liveness probe compose uses. `503` when Postgres or
pgvector is unreachable; `200` with a degraded body when only the model
provider is down. The container stays `unhealthy` until the API can serve.

### Logs

```bash
docker compose logs -f darkmem
```

Container logs are UTC. If your host is not, timestamps will look stale next to
`docker inspect` — that is a timezone difference, not a hung container.

### Jobs

Roughly twenty scheduled jobs handle buffer flushing, cleanup, code
reconciliation and the derived knowledge layers. **Jobs** in the UI shows each
one's schedule, last run and outcome, and lets you trigger one by hand. A
manual trigger takes the same lock the scheduler does, so it can never race a
scheduled run — it returns `409` if one is already going.

### When something is wrong

| Symptom | Look at |
| --- | --- |
| Captures pile up unprocessed | **Settings → Pipeline**, and the `buffer_flush` job |
| A memory failed to process | **Settings → Pipeline** — failures are recorded per memory with the real error |
| Container will not start | `docker compose logs darkmem` — usually the schema guard or `JWT_SECRET` |
| Searches return nothing | The embedding model is unreachable, or the corpus was embedded with a different one |
| Everything is slow | Check the model provider first; most latency is upstream |

## Security notes

- **One admin.** No user accounts, roles or per-user isolation. Projects scope
  memories, not permissions.
- **Provider keys and git tokens are stored in the database in plaintext**, per
  the single-operator model. Treat the volume and every backup as secret
  material: access-control them and encrypt them at rest.
- **`/setup` is open until an admin password exists.** Finish it immediately on
  first boot.
- **The audit journal is append-only and outlives deletion.** Event payloads can
  carry content previews that survive deleting the memory itself. If a secret
  is ever pasted into a memory, deleting it is not enough — see
  `docs/runbook-content-purge.md` for the break-glass procedure.

---

## Next

- [Usage Guide](usage-guide.md) — day-to-day work
- [CONTRIBUTING.md](../../CONTRIBUTING.md) — changing the code

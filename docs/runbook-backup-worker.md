# Runbook — the backup worker

A second machine that runs the same darkmem image against nightly-restored
snapshots and serves them **read-only**. It exists to answer one question
without touching production: *is what we backed up actually a working darkmem?*

Bring-up happens on the worker machine. Nothing in this repo's gate runs there.

**This procedure was rehearsed end to end on 2026-09-02** — the whole stack on one
host as its own compose project, ship → restore → serve → reject, then torn down.
Every step below has been run. If you are rehearsing rather than provisioning, set
`WORKER_APP_PORT`, `WORKER_RECEIVER_PORT` and `WORKER_DB_PORT` in `.env`, since the
defaults collide with an existing darkmem on the same host.

---

## What "read-only" honestly means

Three layers, and only one of them is a guarantee.

1. **The `darkmem_viewer` Postgres role is the enforcement.** It holds `SELECT`
   and nothing else (`scripts/worker/viewer-grants.sql`). No application bug can
   dig under it, and every write refusal arrives as SQLSTATE `42501`, which the
   app maps to a 403 `read_only` envelope.
2. **Process separation.** Migrations, the `schema_guard` stamp and the restore
   itself run privileged, from the host, with the app stopped. The app's
   `command:` overrides `entrypoint.sh` so the serving process never migrates.
3. **`DARKMEM_READ_ONLY` is ergonomics, not enforcement.** It stops *spend* (the
   job scheduler is never armed, chat and the reranker are refused) and *noise*
   (known write-on-read paths no-op instead of erroring once per request).

**A reader who takes away "the flag makes it read-only" has been misled.** If
the flag were unset and the role were still `darkmem_viewer`, the instance
would still be read-only — noisier, and spending money on jobs that fail, but
read-only. If the role were the owner and the flag were set, it would **not**
be.

### What this costs, stated rather than discovered

- **Token rotation is disabled.** `POST /auth/refresh` reissues without
  blocklisting the token it replaces, and `POST /auth/logout` clears the cookie
  without recording it. A captured pre-refresh token therefore stays valid until
  its own `exp`. The alternative was a viewer session that dies silently at
  every access-token expiry. It is reported on `GET /auth/security-posture` as
  `read_only_token_rotation_disabled` and rendered on the Security settings tab.
- **Journal rows and usage rows are left to degrade.** `record_event` and
  `UsageRecorder` swallow their own failures by contract, so login audits and
  per-call cost rows are silently lost on the worker. Guarding them would spread
  the flag into shared writers for no behavioural gain.

### What does not work on the worker, by design

| Surface | What happens |
|---|---|
| Chat | 403 before any LLM is constructed |
| Captures (REST and MCP), settings PUTs, ratify, hygiene actions | 403 `read_only` from the 42501 handler |
| `POST /jobs/{key}/trigger` | 403 — a disarmed scheduler does not disarm the manual door |
| Change password | 403 — the next restore overwrites it anyway |
| Repository *file* browsing | Degrades: the worker's `repo_data` volume holds no clones. DB-backed code-graph reads work. |
| The setup wizard | 403 on `require_uninitialized`, because the snapshot carries `admin_password_hash`. Correct, no handling needed. |

**Semantic search requires one live external call per query.** The query embed
is not optional — a search surface that cannot embed cannot search — so the
worker needs the snapshot's embedding endpoint reachable. On this owner's
topology that is the LAN Ollama at `192.168.0.196:11434`, reachable from any LAN
machine. There is deliberately **no keyword-only fallback**: the failure is loud
and the requirement is stated instead.

---

## Prerequisites

- A LAN machine with Docker and Docker Compose.
- The `darkraise/darkmem` image (pull it, or copy it across with
  `docker save` / `docker load` — this repo never pushes to a registry).
- `age` on the **host**, not just in the image: the restore loop decrypts before
  it replays.
- The **age identity file** (the private key). It never enters any database and
  never enters this repository. Generate the pair once, on a machine you trust:
  ```bash
  age-keygen -o ~/darkmem-backup-identity.txt   # keep this; chmod 0600
  age-keygen -y ~/darkmem-backup-identity.txt   # the RECIPIENT — this goes in the UI
  ```
  The recipient (public key) goes in the destination's `age_recipient` field on
  production's Backups settings tab. The identity stays here.
- Network reachability from production to this machine's receiver port, and
  from this machine to the embedding endpoint.

---

## Provisioning

### 1. The dump directory

The receiver runs as the image's unprivileged `app` user and **Docker does not
chown a bind mount**. Create it first, owned by the image's uid — read the uid,
never assume it, because `adduser --system` allocates from Debian's system range
and the number is not stable across rebases:

```bash
APP_UID=$(docker run --rm darkraise/darkmem:latest id -u)
sudo install -d -o "$APP_UID" -g "$APP_UID" -m 0750 /srv/darkmem-dumps
```

### 2. The environment file

Beside `docker-compose.worker.yml`, in `.env`:

```ini
# The owner role — the restore loop replays, migrates, stamps and swaps as this.
# The app NEVER sees it.
OWNER_PASSWORD=<generate>
# The SELECT-only role the app connects as. This is the enforcement.
VIEWER_PASSWORD=<generate>
# 32+ characters. The app refuses to start below that.
JWT_SECRET=<generate>
# 32+ characters. The receiver refuses to start below that.
RECEIVER_TOKEN=<generate>
# Plain-HTTP LAN login.
COOKIE_SECURE=false
```

Every one of these is generated on this machine and shared with nothing.

### 3. First boot, and the probe that matters

```bash
docker compose -f docker-compose.worker.yml up -d receiver
docker compose -f docker-compose.worker.yml exec -T receiver \
  sh -c 'touch /dumps/.probe && rm /dumps/.probe' && echo "receiver mount writable"
```

The receiver also refuses to start outright when `RECEIVER_DIR` is unwritable,
so a green boot already means more than it looks like. Run the probe anyway: it
is the difference between "the process started" and "an upload will land".

The app and Postgres cannot come up until a snapshot has been restored — there
is no database and no `darkmem_viewer` role yet. That is the correct order:

```bash
docker compose -f docker-compose.worker.yml up -d postgres
```

### 4. Point production at it

On **production's** Settings → Backups tab, add a `worker` destination:

- **url** — `http://<worker-lan-ip>:8100`
- **token** — the `RECEIVER_TOKEN` above
- **age recipient** — the public key from step 1's prerequisites
- **retention** — how many snapshots this worker keeps

A `worker` destination without a recipient is refused at save. The bearer token
is **authorisation, not confidentiality**: it says who may upload, not who may
read the bytes in flight. Front TLS if the path crosses anything you do not
control; over a trusted LAN carrying ciphertext, the token is enough.

### 5. The nightly cycle

`/etc/systemd/system/darkmem-restore.service`:

```ini
[Unit]
Description=darkmem worker nightly restore cycle
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/root/darkmem-worker
EnvironmentFile=/root/darkmem-worker/.env
Environment=AGE_IDENTITY=/root/darkmem-backup-identity.txt
Environment=WORKER_COMPOSE=docker-compose.worker.yml
ExecStart=/root/darkmem-worker/scripts/worker/restore-cycle.sh
```

`/etc/systemd/system/darkmem-restore.timer` — after production's 04:30 ship, with
`Persistent=true` so a night the worker was off is caught up rather than skipped:

```ini
[Unit]
Description=darkmem worker nightly restore

[Timer]
OnCalendar=*-*-* 05:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now darkmem-restore.timer
sudo systemctl start darkmem-restore.service   # run one by hand first
```

---

## What the cycle does, and what it refuses

Verify, then swap. In order:

1. Pick the newest `darkmem-app-*.sql.gz.age` that is not already recorded in
   `$STATE_FILE` as the one being served. Ordering is by **name**, not mtime —
   the stamp is zero-padded and big-endian, and a copy resets an mtime.
2. Decrypt with the identity, and check the `pg_dump` completion marker. gzip of
   a truncated stream is still valid gzip, so integrity proves nothing; the
   marker is written last and only on a run that finished.
3. Replay into a **side** database. The app is still serving the previous one.
4. Migrate and stamp `schema_guard` against the side database, privileged.
5. Apply `viewer-grants.sql` to the side database.
6. Only now: stop the app, drop, rename, start. Downtime is the swap — seconds.
7. Record the served snapshot name.

### A snapshot from an older baseline is rejected, not fatal

`schema_guard` hashes the baseline file and refuses a database it does not
match. That happens at step 4, **against the side database**, so:

- the side database is dropped,
- the swap never happens,
- the viewer keeps serving what it had,
- the script exits **0** with a loud `SNAPSHOT REJECTED` line.

This is deliberate and is B1's schema-mismatch answer: a viewer that went down
for exactly the snapshots one most wants to inspect would be worse than useless.
Fix it by rebuilding the worker's image from the commit that produced the
snapshot, or by taking a fresh snapshot from a production that matches.

### If a cycle fails partway

The script prints what to do, per stage. The one window worth knowing about
without reading the script is `app_stopped`: the app is down and `darkmem` may
not exist, with the restored data safe in the side database. Finish by hand:

```bash
docker compose -f docker-compose.worker.yml exec -T postgres \
  psql -U darkmem -d postgres -c 'ALTER DATABASE "darkmem_restore_<pid>" RENAME TO "darkmem";'
docker compose -f docker-compose.worker.yml start darkmem
```

Every other stage leaves the viewer untouched and the side database as debris to
drop.

---

## Verifying it worked

```bash
# The posture the SPA reads
curl -s -b cookies.txt http://<worker>:8000/api/v1/auth/security-posture | grep read_only

# A write is refused at the database, not by a route allowlist
curl -s -X POST http://<worker>:8000/api/v1/memories \
  -b cookies.txt -H 'content-type: application/json' \
  -d '{"content":"should be refused"}' | grep read_only
```

Then log in and search. If search returns nothing, the embedding endpoint is
unreachable — that is group E, and it is an operating requirement rather than a
bug.

**The receiver is the only write door, and it writes files, not rows.** It holds
no database connection at all; `backend/tests/test_worker_receiver.py` walks its
import closure and fails the build if that stops being true.

---

## Tearing it down

```bash
docker compose -f docker-compose.worker.yml down -v
```

The worker is a separate compose project on a separate machine, so this removes
it wholesale. If the `darkmem_viewer` role was ever created on the **production**
cluster by mistake, it holds SELECT only — but drop it anyway:

```sql
DROP OWNED BY darkmem_viewer;
DROP ROLE darkmem_viewer;
```

# Backup Off-Host Implementation Plan (Increment 6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementer assignments:** each task names its implementer agent in an
> `**Implementer:**` line. When executing with
> superpowers:subagent-driven-development, REQUIRED SUB-SKILL:
> dcc-superpower-companions:dispatching-tiered-implementers. Under
> superpowers:executing-plans these lines are inert; ignore them.

**Goal:** Nightly snapshots leave the host that runs the database — encrypted before egress, read back and checksummed after upload, retained per destination — driven by a `backup_ship` `JobRegistry` job that dumps over the stack network, with a settings panel for destinations. The systemd producer (`scripts/backup.sh` + `darkmem-backup.timer`) stays untouched as the independent floor.

**Spec:** `docs/superpowers/specs/2026-08-31-project-artifact-store-design.md` §9.1–§9.4 (§9.3 as amended after review finding M4).
**Review:** M4 (process boundary) and m4 (no cross-process lock; event-loop stalls) are upheld and drive the architecture below. Where spec and review disagree, the review wins.

**Amendments (2026-09-02, cross-plan adversarial review of all eight plans).** Five defects, fixed in place. **B-1 (blocker)** — the dump bind mount defaulted under `/root` (mode 0700) while the container runs as the unprivileged `app` user, so every ship would have failed on its first `.part` open and nothing would have surfaced until Task 10; the default moves to `/srv/darkmem-dumps`, Task 1 creates and chowns it to the image's uid, and a write probe proves it. **B-2 (blocker)** — Task 2's two new REST routes have no `PARITY_TABLE` row and no `EXPECTED_STATUS` entry, and both enumeration tests fail on an unclassified route; new Step 4b adds them, regenerates the parity doc and recomputes its headline. **m-2** — a third job-count sentence at `CLAUDE.md:1648-1649` that a grep for "Twenty-three" does not find. **m-11** — `PG_DUMP_ARGV` versus `_dump_argv()` described as both shapes at once. **m-15** — the deployment-test helper names do not exist; the real ones are `_unwrapped` / `_compose` / `_compose_command`. Tasks 3-10 were otherwise found sound.

## Architecture — the M4 correction, restated as what gets built

**The job does NOT call `scripts/backup.sh`, and cannot:** the app container has no `pg_dump`, no compose binary, and no mount reaching the host's docker socket or `/root/darkmem-backups` — its only mounts are `repo_data` (`docker-compose.yml`, `volumes:` on the `darkmem` service) and, in dev, `/host-repos`. Instead:

- The runtime image gains `postgresql-client`, `age`, `openssh-client` and `rsync`. **Verified 2026-08-31 against the live base image**: `python:3.12-slim` is Debian 13.6 (trixie), whose `postgresql-client` candidate is **17+278** — the same major as the `pgvector/pgvector:0.8.2-pg17` server, which matters because `pg_dump` refuses a server *newer* than itself — and whose `age` candidate is 1.2.1. No PGDG repo needed. Task 1 re-verifies at build time.
- The job runs `pg_dump -h $DB_HOST` **over the stack network** (bridge networking; the API already reaches Postgres by service name — `docker-compose.yml` `DB_HOST=${DB_HOST:-postgres}`), streams through gzip to a `.part` file in a new dump bind mount, checks pg_dump's completion marker, renames, encrypts, ships, verifies, journals, prunes.
- **Two independent producers is the design** (§9.3's floor argument): the systemd path writes `darkmem-<stamp>.sql.gz` into `/root/darkmem-backups`; the job writes `darkmem-app-<stamp>.sql.gz[.age]` into `${DARKMEM_DUMP_DIR:-/srv/darkmem-dumps}` (not under `/root`, which the container's unprivileged user cannot traverse — see Task 1). **Different directories are the real separation; distinct prefixes are the belt** — note `backup.sh`'s retention glob `darkmem-*.sql.gz` (`scripts/backup.sh`, `find … -name 'darkmem-*.sql.gz'`) *would* match `darkmem-app-*`, so the two producers must never be pointed at one directory, and Task 4's prune matches only the job's own `darkmem-app-` prefix so it can never delete a systemd dump even if an operator does.
- **m4:** nothing serializes the job against the 03:30 timer — different processes, and the per-job `asyncio.Lock` binds only in-process. The job's default cron is `30 4 * * *` (04:30), an hour clear of the timer, and both producers' `.part` discipline makes a rare overlap benign. This is stated, not repaired.
- **Invariant 13:** hashing, encryption and uploads are executor-offloaded (`asyncio.to_thread`) or run as subprocesses; nothing CPU-heavy blocks the single worker's event loop.

**Encryption is asymmetric on purpose.** The `age` X25519 *recipient* (public key) lives in the destinations `config` row and encrypts; the *identity* (private key) is generated once by the operator (`age-keygen`) and **never enters the database** — a snapshot that carried its own decryption key would defeat encryption-at-rest, because the key would ride inside every dump. Decryption happens only where the identity file lives (the restore host; increment 7's worker). `age`'s passphrase mode is interactive-only, so recipient/identity is also the only scriptable shape.

**Destination scope:** this increment ships `local`, `ssh` and `s3` kinds. The `worker` (https) kind is increment 7's, landing together with the receiver process it talks to (`docs/superpowers/plans/2026-08-31-backup-worker.md`).

## Global Constraints

- **Backend tests** (from `backend/`): `python -m pytest -q` against `darkmem_test` on the dev-compose Postgres (127.0.0.1:5433). Never point at a real database.
- **Merge gate:** `./scripts/gate.sh` from the repo root. `--full` is unreliable on this host (earlyoom kills Chromium); never invoke Playwright bare.
- **No schema change.** Destinations live in a `config` row (the LLM-provider shape; per-repo git tokens are the credential precedent — `backend/app/services/repo_manager.py:330` `git_token_<repo_id>`). The job's `config_schema` can carry **ints only** (`FieldDescriptor.default: int`, `backend/app/services/job_registry.py:89-98`) — no URL, bucket or credential may be smuggled into it.
- **Taxonomy-first:** new event types land in `EVENT_TYPES` (`backend/app/services/events.py:124`) in the same task as (and before) their first emitter. `object_type="system"` is already in `OBJECT_TYPES` — do not widen it.
- **Every new REST route must be classified in the same commit that adds it** (review B-2): `test_door_parity.py::test_every_rest_route_is_classified` and `test_rest_conformance.py::test_every_route_status_code_matches_the_convention` both enumerate `app.routes` and fail on anything unclassified. A single-door row additionally needs a *stated reason* of at least 80 characters that is not a placeholder — a design decision, not a form field. Task 2 Step 4b is where this happens for this plan.
- **Invariant 23:** adding a job desynchronises two "full list" surfaces — `tests/test_code_deriver.py:1520-1528` (the AST roster) and CLAUDE.md's job counts ("Twenty-three", "seventeen live ones"). Task 7 updates both in the same commit as the registration.
- **Secrets never in tree or logs:** ssh private keys and S3 secrets are stored in the config row, masked as `"***"` on every GET (the `MASKED_KEY` idiom, `backend/app/api/routes/llm_providers.py:73,107,205`), and never logged. Journal payloads carry filenames, sizes and checksums — never credentials.
- **Backend lock:** the boto3 dependency (Task 6) regenerates `requirements.lock` only via `uv pip compile --universal pyproject.toml -o requirements.lock` (CLAUDE.md, Backend lock).
- **UI from darkraise-ui first**: `dialog`, `card`, `switch`, `number-input`, `empty-state` all ship in `frontend/node_modules/darkraise-ui/dist/components/`.
- **Redeploy rule:** every task here touches `backend/`, the `Dockerfile` or compose — the final task redeploys this machine and verifies the change is in the running image.
- **Commits:** `<type>(<scope>): <subject>`, ≤50 chars, imperative, atomic per concern.

## File Structure

```
Dockerfile                                   # Task 1: apt packages in the runtime stage
docker-compose.yml                           # Task 1: /dumps bind mount
backend/tests/test_deployment_artifact.py    # Task 1: package + mount assertions
backend/app/services/events.py               # Task 2: event vocabulary
backend/app/services/backup_config.py        # Task 2: destinations config row service (new)
backend/app/api/routes/config.py             # Task 2: GET/PUT /config/backup-destinations
backend/tests/test_backup_config.py          # Task 2 (new)
backend/tests/test_door_parity.py            # Task 2: PARITY_TABLE row (review B-2)
backend/tests/test_api/test_rest_conformance.py  # Task 2: EXPECTED_STATUS (B-2)
docs/two-door-parity.md                      # Task 2: regenerated + headline
backend/app/services/backup_ship.py          # Task 3: dump/encrypt core; Tasks 4-6: destinations
backend/tests/test_backup_ship.py            # Tasks 3–6 (new)
backend/pyproject.toml, requirements.lock    # Task 6: boto3
backend/app/services/job_runners.py          # Task 7: make_backup_ship_runner
backend/app/main.py                          # Task 7: registration
backend/tests/test_code_deriver.py           # Task 7: roster
CLAUDE.md                                    # Task 7: job counts (invariant 23)
frontend/src/features/settings/use-backups-tab-binding.ts   # Task 8 (new)
frontend/src/features/settings/components/backups-tab.tsx   # Task 9 (new)
frontend/src/routes/_authenticated/settings.tsx             # Task 9: tab wiring
frontend/src/features/settings/__tests__/backups.test.tsx   # Task 9 (new)
CHANGELOG.md                                 # Task 10
```

---

### Task 1: Image packages and the dump mount

**Files:**
- Modify: `Dockerfile` (runtime stage apt line — the block that installs `git`)
- Modify: `docker-compose.yml` (`darkmem` service `volumes:`, and the `volumes:` assertions' subjects)
- Modify: `backend/tests/test_deployment_artifact.py` (extend `test_runtime_stage_installs_git` at :475 with a sibling; extend `test_prod_app_service_publishes_its_port_and_keeps_its_repo_volume` at :151)

**The mount must be writable by the image's unprivileged user — this is the task's real risk** (cross-plan review B-1, 2026-09-02). The runtime image drops privileges: `Dockerfile:87-88` runs `adduser --system --ingroup app app` then `USER app`. A **host bind mount is not chowned by Docker** the way a fresh named volume is, so `${DARKMEM_DUMP_DIR}` arrives owned by whoever created it — and if it does not exist, Docker creates it `root:root`. The plan's original default put it under `/root`, which is mode `0700`, so uid `app` could not even traverse into it. Every ship would fail on the first `.part` open, and Task 10 Step 5 ("watch one ship") is nine tasks later — the whole increment would land looking green.

Two consequences the steps below carry:
- **The default moves out of `/root`** to `/srv/darkmem-dumps`. `/root` is unreadable to any non-root user by design; a directory the container must write does not belong under it. The systemd producer keeps `/root/darkmem-backups` — different directories is still the m4 separation, and now one of them is actually reachable.
- **The host directory is created and chowned to the image's uid at deploy time, not guessed.** Do **not** "simplify" this by pinning a fixed uid in the `adduser` line: `repo_data` is an existing named volume whose files are owned by the current uid, and changing it would leave the app unable to write its own clones — a silent second failure worse than the one being fixed.

**Interfaces:**
- Produces: `pg_dump` 17, `age`, `ssh`/`scp`, `rsync` binaries inside the image; `/dumps` bind mount (`${DARKMEM_DUMP_DIR:-/srv/darkmem-dumps}`, created and chowned to the image's uid) — consumed by Tasks 3–7 and by increment 7's restore pull.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

- [ ] **Step 1: Failing tests first.** In `backend/tests/test_deployment_artifact.py`, beside `test_runtime_stage_installs_git` (:475), add:

```python
def test_runtime_stage_installs_backup_toolchain():
    """The backup_ship job runs pg_dump over the stack network and encrypts
    with age; the ssh destination shells out to scp/rsync. None of these are
    in the base image, and an image missing them boots green while every
    nightly ship fails (M4's process-boundary lesson, applied to the fix)."""
    runtime = _unwrapped(DOCKERFILE)  # the helper test_runtime_stage_installs_git uses
    for pkg in ("postgresql-client", "age", "openssh-client", "rsync"):
        assert pkg in runtime, f"runtime stage does not install {pkg}"


def test_prod_app_service_mounts_the_dump_directory():
    compose = _compose(PROD_COMPOSE)
    volumes = compose["services"]["darkmem"]["volumes"]
    mount = next((v for v in volumes if "/dumps" in v), None)
    assert mount and "DARKMEM_DUMP_DIR" in mount, (
        "backup_ship writes to /dumps; without the bind mount the host (and "
        "restore.sh --from) cannot see what the job produced"
    )
    # Review B-1: the container runs as the unprivileged `app` user
    # (Dockerfile USER app) and /root is 0700, so a default under /root is a
    # directory the job can neither traverse nor write.
    assert "/root" not in mount, (
        "the dump mount's default must be reachable by the image's "
        "unprivileged user; /root is 0700"
    )
```

**Helper names, corrected** (review m-15): the file defines `_unwrapped(path)` for Dockerfile text, `_compose(path)` for a parsed compose file and `_compose_command(path, service)` (`test_deployment_artifact.py:38-52`) — there is no `_runtime_stage()` and no `_prod_compose()`. Use `_unwrapped(DOCKERFILE)` where the sketch above says `_runtime_stage()`, matching how `test_runtime_stage_installs_git` reads the file at `:475`. Run: `cd backend && python -m pytest -q tests/test_deployment_artifact.py` — the two new tests FAIL.

- [ ] **Step 2: Dockerfile.** In the runtime stage, widen the existing apt install (keep the comment discipline — say why, not what):

```dockerfile
# git: code indexing shells out to it (see below). postgresql-client: the
# backup_ship job dumps over the stack network — the client major must be
# >= the server's (pg17); trixie ships 17, verified at plan time. age: dumps
# are encrypted before egress with an X25519 recipient; the identity never
# enters the image or the database. openssh-client + rsync: the ssh
# destination ships via scp/rsync with a pinned host key.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git postgresql-client age openssh-client rsync \
    && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 3: Compose.** In `docker-compose.yml`, `darkmem` service `volumes:`:

```yaml
    volumes:
      # Persist cloned repositories across container restarts.
      - repo_data:/app/data/repositories
      # Where backup_ship writes its dumps. A host bind mount, not a named
      # volume, so the host-side restore path and the operator can read what
      # the job produced. Distinct from the systemd producer's
      # /root/darkmem-backups on purpose (m4): the two producers never share
      # a directory, so neither's retention can prune the other's artefacts.
      # NOT under /root: the container runs as the unprivileged `app` user and
      # /root is 0700, so a dump directory there is unwritable and unreachable.
      - ${DARKMEM_DUMP_DIR:-/srv/darkmem-dumps}:/dumps
```

The host side of that mount has to exist with the right owner before the first ship. Add it to this task as an operator step, run once on this machine and recorded in Task 10's deploy sequence:

```bash
# The uid is read from the image, never assumed: `adduser --system` allocates
# from Debian's system range and the number is not stable across rebases.
APP_UID=$(docker run --rm darkraise/darkmem:latest id -u)
sudo install -d -o "$APP_UID" -g "$APP_UID" -m 0750 /srv/darkmem-dumps
```

- [ ] **Step 4: Verify.** `cd backend && python -m pytest -q tests/test_deployment_artifact.py` all green. Then a real build proof (the plan's package-availability claim, re-verified where it counts): `DARKMEM_PUSH=0 ./scripts/build-push.sh` and `docker run --rm darkraise/darkmem:latest sh -c "pg_dump --version && age --version && rsync --version | head -1 && ssh -V"` — expect `pg_dump (PostgreSQL) 17.x`.

**Then prove the mount is writable by the process that will write it** (review B-1) — this is the assertion the whole increment rests on, and it costs one command:

```bash
docker compose up -d
docker exec darkmem-prod-darkmem-1 sh -c 'touch /dumps/.probe && rm /dumps/.probe' \
  && echo "dump mount writable"
```

A failure here is the increment's core deliverable not working, not a permissions detail: fix the host directory's ownership before writing Task 3. Task 3's `run_dump` should additionally fail fast on an unwritable `DUMP_DIR` with a message naming the directory and the uid, rather than surfacing as a truncated `.part` at 04:30.

---

### Task 2: Destination config — vocabulary, service, routes

**Files:**
- Modify: `backend/app/services/events.py` (append to `EVENT_TYPES` at :124: `"backup_shipped"`, `"backup_verify_failed"`)
- Create: `backend/app/services/backup_config.py`
- Modify: `backend/app/api/routes/config.py` (new GET/PUT pair; the `/config/auto-research` pair at :736-810 is the shape to copy, including `_lock_config_row` at :418 on the PUT)
- Create: `backend/tests/test_backup_config.py`

**Interfaces:**
- Consumes: `Config` model, `_lock_config_row`, `record_event` vocabulary.
- Produces: `BACKUP_DESTINATIONS_KEY = "backup_destinations"`, `load_destinations(session) -> list[DestinationConfig]`, `save_destinations(session, body) -> list[DestinationConfig]` and the masked REST pair — consumed by Tasks 4–7 and by increment 7.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Failing tests.** `backend/tests/test_backup_config.py` (use the existing `session` fixture from `conftest.py`):

```python
import pytest
from app.services import backup_config as bc

LOCAL = {"name": "local", "kind": "local", "enabled": True, "retention_keep": 14}
SSH = {"name": "nas", "kind": "ssh", "enabled": True, "retention_keep": 30,
       "age_recipient": "age1qqq…", "ssh": {
           "host": "192.0.2.10", "port": 22, "user": "backup",
           "remote_dir": "/srv/darkmem", "host_key": "192.0.2.10 ssh-ed25519 AAAA…",
           "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\n…"}}
S3 = {"name": "r2", "kind": "s3", "enabled": False, "retention_keep": 8,
      "age_recipient": "age1qqq…", "s3": {
          "endpoint_url": "https://x.r2.cloudflarestorage.com", "bucket": "b",
          "prefix": "darkmem/", "region": "auto",
          "access_key_id": "AK", "secret_access_key": "SK"}}

async def test_round_trip_and_masking(session):
    await bc.save_destinations(session, {"destinations": [LOCAL, SSH, S3]})
    masked = [d.model_dump() for d in await bc.load_destinations(session, masked=True)]
    assert masked[1]["ssh"]["private_key"] == bc.MASKED
    assert masked[2]["s3"]["secret_access_key"] == bc.MASKED
    # Unmasked load (the job's read) returns the real values.
    raw = await bc.load_destinations(session, masked=False)
    assert raw[1].ssh.private_key.startswith("-----BEGIN")

async def test_put_with_mask_keeps_stored_secret(session):
    await bc.save_destinations(session, {"destinations": [SSH]})
    edited = {**SSH, "retention_keep": 60,
              "ssh": {**SSH["ssh"], "private_key": bc.MASKED}}
    await bc.save_destinations(session, {"destinations": [edited]})
    raw = await bc.load_destinations(session, masked=False)
    assert raw[0].retention_keep == 60
    assert raw[0].ssh.private_key.startswith("-----BEGIN")  # unchanged

async def test_egress_without_recipient_is_refused(session):
    bad = {**SSH, "age_recipient": None}
    with pytest.raises(bc.DestinationInvalid):
        await bc.save_destinations(session, {"destinations": [bad]})
    # local is the one kind allowed unencrypted (§9.4 rule 1)
    await bc.save_destinations(session, {"destinations": [LOCAL]})

async def test_duplicate_names_refused(session):
    with pytest.raises(bc.DestinationInvalid):
        await bc.save_destinations(session, {"destinations": [LOCAL, LOCAL]})
```

Run: FAIL (module absent).

- [ ] **Step 2: The service.** `backend/app/services/backup_config.py` — complete shape:

```python
"""The backup destinations config row (spec §9.3, amended).

One `config` row, key `backup_destinations`, holding the full destination
list — the LLM-provider shape, and the same credential posture as per-repo
git tokens (`repo_manager.py`, `git_token_<repo_id>`): secrets live in the
row, are masked on every read that leaves the process, and never appear in
a job `config_schema` (`FieldDescriptor.default` is typed `int`).

The age *recipient* (public key) is stored here and encrypts; the identity
(private key) must never be stored in this database — a snapshot carrying
its own decryption key is not encrypted at rest, because every dump would
include the key that opens it. §9.4 rule 1 is enforced at save: every
non-local destination must carry a recipient.
"""
from __future__ import annotations

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config

BACKUP_DESTINATIONS_KEY = "backup_destinations"
MASKED = "***"
SECRET_FIELDS = {"ssh": ("private_key",), "s3": ("secret_access_key",)}


class DestinationInvalid(ValueError):
    pass


class SshSettings(BaseModel):
    host: str
    port: int = 22
    user: str
    remote_dir: str
    host_key: str          # known_hosts line, pinned — never trust-on-first-use
    private_key: str


class S3Settings(BaseModel):
    endpoint_url: str
    bucket: str
    prefix: str = ""
    region: str = "auto"
    access_key_id: str
    secret_access_key: str


class DestinationConfig(BaseModel):
    name: str
    kind: str              # "local" | "ssh" | "s3"   (increment 7 adds "worker")
    enabled: bool = True
    retention_keep: int = 14
    age_recipient: str | None = None
    ssh: SshSettings | None = None
    s3: S3Settings | None = None


KINDS = ("local", "ssh", "s3")


def _validate(items: list[DestinationConfig]) -> None:
    names = [d.name for d in items]
    if len(names) != len(set(names)):
        raise DestinationInvalid("destination names must be unique")
    for d in items:
        if d.kind not in KINDS:
            raise DestinationInvalid(f"unknown kind {d.kind!r}")
        if d.kind != "local" and not d.age_recipient:
            raise DestinationInvalid(
                f"{d.name}: encrypt before egress — a non-local destination "
                f"requires an age recipient (spec §9.4 rule 1)")
        if d.kind == "ssh" and d.ssh is None:
            raise DestinationInvalid(f"{d.name}: ssh settings required")
        if d.kind == "s3" and d.s3 is None:
            raise DestinationInvalid(f"{d.name}: s3 settings required")
        if d.retention_keep < 1 or d.retention_keep > 3650:
            raise DestinationInvalid(f"{d.name}: retention_keep out of range")


async def _load_row(session: AsyncSession) -> Config | None:
    return (await session.execute(
        select(Config).where(Config.key == BACKUP_DESTINATIONS_KEY)
    )).scalar_one_or_none()


def _mask(d: DestinationConfig) -> DestinationConfig:
    out = d.model_copy(deep=True)
    for group, fields in SECRET_FIELDS.items():
        sub = getattr(out, group, None)
        if sub is not None:
            for f in fields:
                if getattr(sub, f, None):
                    setattr(sub, f, MASKED)
    return out


async def load_destinations(
    session: AsyncSession, *, masked: bool = True,
) -> list[DestinationConfig]:
    row = await _load_row(session)
    items = [DestinationConfig.model_validate(v)
             for v in (row.value or {}).get("destinations", [])] if row else []
    return [_mask(d) for d in items] if masked else items


async def save_destinations(session: AsyncSession, body: dict) -> list[DestinationConfig]:
    try:
        items = [DestinationConfig.model_validate(v)
                 for v in body.get("destinations", [])]
    except ValidationError as exc:
        raise DestinationInvalid(str(exc)) from exc
    # A masked secret on PUT means "unchanged": resolve it against the stored
    # row before validating, the llm_providers MASKED_KEY contract.
    stored = {d.name: d for d in await load_destinations(session, masked=False)}
    for d in items:
        prev = stored.get(d.name)
        for group, fields in SECRET_FIELDS.items():
            sub = getattr(d, group, None)
            prev_sub = getattr(prev, group, None) if prev else None
            if sub is not None:
                for f in fields:
                    if getattr(sub, f, None) == MASKED:
                        if prev_sub is None or not getattr(prev_sub, f, None):
                            raise DestinationInvalid(
                                f"{d.name}: masked {f} with no stored value")
                        setattr(sub, f, getattr(prev_sub, f))
    _validate(items)
    payload = {"destinations": [d.model_dump() for d in items]}
    row = await _load_row(session)
    if row:
        row.value = payload
    else:
        session.add(Config(key=BACKUP_DESTINATIONS_KEY, value=payload))
    await session.commit()
    return items
```

- [ ] **Step 3: Vocabulary.** Append `"backup_shipped"` and `"backup_verify_failed"` to `EVENT_TYPES` (`backend/app/services/events.py:124` list), each with a one-line comment ("a snapshot landed on a destination and its read-back checksum matched" / "uploaded is not restorable: the read-back disagreed or failed"). Emitters land in Task 4 — vocabulary first, taxonomy-first rule.

- [ ] **Step 4: Routes.** In `backend/app/api/routes/config.py`, copy the auto-research pair's shape (:736-810):
  - `GET /api/v1/config/backup-destinations` → `{"destinations": [...]}` masked.
  - `PUT /api/v1/config/backup-destinations` → validates via `save_destinations` under `_lock_config_row(session, BACKUP_DESTINATIONS_KEY)`; `DestinationInvalid` → 422. Response is the masked list (echo the mask, never the secret).
  Route-level tests go in `test_backup_config.py` using the app test client pattern the file's siblings use (see `tests/test_security_posture.py` for the authenticated-client fixture idiom).

- [ ] **Step 4b: Classify the two new routes, or the gate is red** (cross-plan review B-2, 2026-09-02)

Two enumeration-driven tests walk `app.routes` and fail on any route nobody classified. Neither was in this plan's File Structure, and both go red the moment Step 4's routes exist:

1. **`backend/tests/test_door_parity.py`** — `test_every_rest_route_is_classified` (`:1362-1380`) fails a route with no `PARITY_TABLE` row. Add a `Surface` beside `config.auto_research` (`:135-150`), which is the exact precedent this task already copies:

```python
    Surface(
        name="config.backup_destinations",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/config/backup-destinations"),
            ("PUT", f"{V1}/config/backup-destinations"),
        ),
        mcp=(),
        reason=(
            "Operator configuration of where this instance ships its own "
            "encrypted snapshots, including ssh and S3 credentials. An agent "
            "that could read or rewrite the destination list could redirect "
            "every future backup to a destination it chose, which is exfiltration "
            "wearing the backup system's own clothes; the secrets are masked on "
            "read for the same reason. Backups are an operator concern with a "
            "human at the console, so this is deliberately single-door."
        ),
    ),
```

`test_every_single_door_surface_states_a_real_reason` enforces a real rationale — at least `_MIN_REASON_CHARS` (80) and none of the `_NON_REASONS` placeholders ("planned", "not yet built", …). Write the reason for the person who will question the decision, not to clear the length check.

2. **`backend/tests/test_api/test_rest_conformance.py`** — `test_every_route_status_code_matches_the_convention` (`:297-310`) fails a route with no `EXPECTED_STATUS` entry. Add both, mirroring the auto-research pair's values (`GET` 200, `PUT` 200 — the PUT echoes the masked list rather than creating a resource, so 200 is right and 201 would be wrong).

3. **Regenerate `docs/two-door-parity.md`**, which is generated from `PARITY_TABLE`, never hand-edited (`test_door_parity.py:9-11`, `:1834-1849`):

```bash
cd backend && .venv/bin/python -c \
  "from tests.test_door_parity import render_markdown; print(render_markdown())"
```

Paste between the generated-table markers, then update the doc's **headline counts** to what `test_the_committed_table_reports_its_own_counts` (`:1851-1875`) derives — this task adds one surface and one REST-only row, so the totals move. Do not copy a number from another plan: increment 7 adds a surface too, and increment 8's plan states literal totals computed before either existed. Read the count off the failing assertion, which prints the exact string the doc must contain.

Add `backend/tests/test_door_parity.py`, `backend/tests/test_api/test_rest_conformance.py` and `docs/two-door-parity.md` to this task's Files list.

- [ ] **Step 5:** `cd backend && python -m pytest -q tests/test_backup_config.py` green; full `python -m pytest -q` green.

---

### Task 3: The dump-and-encrypt core

**Files:**
- Create: `backend/app/services/backup_ship.py` (this task: constants + `run_dump` + `encrypt` + `sha256_file`)
- Create: `backend/tests/test_backup_ship.py`

**Interfaces:**
- Consumes: `/dumps` mount and the `age` binary (Task 1); `settings.db_host/db_port/db_user/db_name/db_password` (`backend/app/config.py`).
- Produces: `BACKUP_SHIP_JOB_KEY = "backup_ship"`, `DUMP_DIR = Path("/dumps")`, `JOB_PREFIX = "darkmem-app-"`, `run_dump() -> Path`, `encrypt(path, recipient) -> Path`, `sha256_file(path) -> str` — consumed by Tasks 4–7.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 2 = 5

- [ ] **Step 1: Failing tests.** In `backend/tests/test_backup_ship.py`:

```python
async def test_dump_refuses_a_stream_without_the_completion_marker(tmp_path, monkeypatch):
    # Fake pg_dump: exits 0 but never writes the marker — the truncated
    # stream backup.sh's marker check exists for, one layer in.
    ...  # monkeypatch backup_ship._dump_argv to return ["sh","-c","echo partial"]
    with pytest.raises(backup_ship.DumpIncomplete):
        await backup_ship.run_dump(dest_dir=tmp_path)
    assert not list(tmp_path.glob("*.sql.gz"))      # nothing renamed
    assert not list(tmp_path.glob("*.part"))        # .part cleaned up

async def test_dump_renames_only_on_marker(tmp_path, monkeypatch):
    ...  # fake pg_dump printing "…\n-- PostgreSQL database dump complete\n"
    out = await backup_ship.run_dump(dest_dir=tmp_path)
    assert out.name.startswith("darkmem-app-") and out.name.endswith(".sql.gz")
    import gzip
    assert b"dump complete" in gzip.decompress(out.read_bytes())

async def test_encrypt_round_trips_with_age(tmp_path):
    if shutil.which("age") is None or shutil.which("age-keygen") is None:
        pytest.skip("age not installed on this host")
    # age-keygen a throwaway identity, encrypt with its recipient,
    # decrypt with the identity, compare bytes.
```

- [ ] **Step 2: Implement.** Core points the code must hit:
  - **`_dump_argv()` is a module-level function, and there is no `PG_DUMP_ARGV` constant** (cross-plan review m-11, 2026-09-02 — this bullet previously described both shapes in one sentence, and the test sketch at Step 1 monkeypatches the constant that the description says does not exist). Pick the function: settings are read at call time, and tests monkeypatch `backup_ship._dump_argv` to return `["sh", "-c", "echo partial"]`. Fix the Step 1 sketch's `monkeypatch.setattr(backup_ship, "PG_DUMP_ARGV", ...)` to patch `_dump_argv` accordingly. It returns: `["pg_dump", "--clean", "--if-exists", "-h", settings.db_host, "-p", str(settings.db_port), "-U", settings.db_user, settings.db_name]` — the same `--clean --if-exists` flags as `scripts/backup.sh`, so `scripts/restore.sh` replays either producer's dump identically. `PGPASSWORD` rides the subprocess env only.
  - Stream `proc.stdout` in chunks through `gzip.GzipFile` onto `<name>.part`, keeping the **last 512 raw bytes** across chunk boundaries. (Compression runs on the event loop inside that chunk loop, which on a single worker is a real stall for the duration of the dump. Acceptable at 04:30 against this corpus size, and stated rather than hidden; if it ever bites, the repair is a `pg_dump | gzip` subprocess pipe, which keeps the marker check on the raw stream and moves the CPU out of the loop entirely.) after `wait()`, require exit 0 AND `b"PostgreSQL database dump complete"` in that tail (the `backup.sh` marker check, applied to the raw stream so nothing re-decompresses). On failure: delete `.part`, raise `DumpIncomplete` with stderr's tail in the message. On success: `os.replace` to `darkmem-app-<YYYYmmdd-HHMMSS>.sql.gz`.
  - `encrypt(path, recipient)`: `asyncio.create_subprocess_exec("age", "-r", recipient, "-o", str(path) + ".age", str(path))`; on success **delete the plaintext** and return the `.age` path — the plaintext must not linger beside the ciphertext on the local disk when the destination demanded encryption. (The `local` destination kind is served by the unencrypted dump when it carries no recipient; Task 4 wires who calls encrypt.)
  - `sha256_file(path)`: `await asyncio.to_thread(...)` chunked hashlib — never inline on the event loop (m4 rider / invariant 13).
- [ ] **Step 3:** `python -m pytest -q tests/test_backup_ship.py` green.

---

### Task 4: Destination protocol, local destination, journal, prune

**Files:**
- Modify: `backend/app/services/backup_ship.py`
- Modify: `backend/tests/test_backup_ship.py`

**Interfaces:**
- Consumes: Task 2's `DestinationConfig`, Task 3's core, `record_event` (`backend/app/services/events.py:224` — degrades, never raises; a lost `backup_shipped` row must not fail a ship that succeeded).
- Produces: `Destination` protocol — `ship(local_path)`, `read_back_sha256(name) -> str`, `list_snapshots() -> list[SnapshotInfo]`, `prune(keep) -> list[str]` — and `build_destination(cfg) -> Destination`, `ship_all(session_factory) -> dict` (the runner's body). Consumed by Tasks 5, 6 and 7 and by increment 7.

**Implementer:** dcc-superpower-companions:impl-opus-high
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 3 = 6
(Risk 3 is the prune: a deletion pass over backup artefacts is data loss when the glob or the sort is wrong — the tests below pin both.)

- [ ] **Step 1: Failing tests**, the prune pinned hardest:

```python
async def test_prune_touches_only_the_job_prefix(tmp_path):
    # A systemd-style dump sitting in the same directory (operator error the
    # design says must be survivable) is never deleted, whatever its age.
    (tmp_path / "darkmem-20250101-000000.sql.gz").write_bytes(b"x")
    for i in range(5):
        (tmp_path / f"darkmem-app-2026010{i}-000000.sql.gz.age").write_bytes(b"x")
    dest = backup_ship.LocalDestination(name="local", directory=tmp_path)
    deleted = await dest.prune(keep=2)
    assert len(deleted) == 3
    assert (tmp_path / "darkmem-20250101-000000.sql.gz").exists()
    survivors = sorted(p.name for p in tmp_path.glob("darkmem-app-*"))
    assert survivors == ["darkmem-app-20260103-000000.sql.gz.age",
                         "darkmem-app-20260104-000000.sql.gz.age"]

async def test_prune_never_matches_part_files(tmp_path):
    (tmp_path / "darkmem-app-20260101-000000.sql.gz.part").write_bytes(b"x")
    ...  # keep=0 edge: prune must not delete an in-flight .part

async def test_ship_all_verifies_and_journals(session, tmp_path, monkeypatch):
    # Fake destination whose read_back_sha256 disagrees → backup_verify_failed
    # journalled, run summary carries verified=False for it; a second, honest
    # fake → backup_shipped with the matching sha256 in the payload.

async def test_one_failing_destination_does_not_stop_the_others(session, tmp_path):
    # First destination's ship() raises; second still ships and verifies.
```

- [ ] **Step 2: Implement.**
  - `SnapshotInfo` dataclass: `name: str, size: int, modified_at: datetime`.
  - `LocalDestination`: `ship` = no-op beyond the dump already sitting in its directory (`/dumps` is the local destination); `read_back_sha256` re-reads the file (via `sha256_file`); `list_snapshots` = sorted glob `darkmem-app-*.sql.gz*` **excluding `*.part`**; `prune(keep)` deletes beyond the newest `keep` by `(mtime, name)` descending, matching **only** `darkmem-app-*.sql.gz` / `darkmem-app-*.sql.gz.age`, never `.part`.
  - `ship_all(session_factory)`: load destinations unmasked → `run_dump()` once → per enabled destination, in sequence: pick artifact (encrypt to `.age` when the destination carries a recipient — encrypt once per recipient, reuse for destinations sharing one), `ship`, `read_back_sha256`, compare against the local hash; journal `backup_shipped` (payload `{"destination", "file", "bytes", "sha256", "elapsed_seconds"}`) on match, `backup_verify_failed` (payload adds `"expected"`, `"got"` or `"error"`) on mismatch/exception; then `prune(cfg.retention_keep)`. Each destination's failure is caught, journalled and folded into the return dict — never allowed to skip the remaining destinations. Return a summary dict for the job-run record (`{"dump": name, "shipped": n, "verify_failed": [...], "pruned": {...}}`).
  - Journal via `record_event` with `object_type="system"`; the boolean return is ignored (a ship is not a verification transition — CLAUDE.md, Events journal).
- [ ] **Step 3:** targeted tests green; whole suite green.

---

### Task 5: The ssh destination

**Files:**
- Modify: `backend/app/services/backup_ship.py` (`SshDestination`)
- Modify: `backend/tests/test_backup_ship.py`

**Interfaces:**
- Consumes: `SshSettings` (Task 2), the protocol (Task 4), `openssh-client`/`rsync` binaries (Task 1).
- Produces: `SshDestination` registered in `build_destination`.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 2 = 5

- [ ] **Step 1: Failing tests.** All subprocess argv construction is unit-tested without a network: expose `_ssh_base_argv(cfg, tmpdir)` and assert:
  - `-o StrictHostKeyChecking=yes` and `-o UserKnownHostsFile=<tmp>/known_hosts` are present; the known_hosts temp file contains exactly `cfg.ssh.host_key`; the identity temp file has mode `0o600` and holds the private key. **Pinned host key, never trust-on-first-use** (spec §9.2).
  - `ship` uses `scp` (or `rsync -e ssh`) to `user@host:remote_dir/<name>.part` then a remote `mv` — the `.part` discipline crosses the wire too, so a torn upload is never listed as a snapshot.
  - `read_back_sha256` streams the remote file back (`ssh user@host cat remote/<name>` into a local hash) — a full byte read-back, not a remote checksum, because "uploaded is not restorable" (§9.4 rule 2) is about what *we* can read, not what the remote claims.
  - `prune` lists `remote_dir` (`ssh … ls -1`), filters to `darkmem-app-*` exactly as 4a does, deletes beyond `keep` with one `rm` per file, and returns names. Refuses (raises) if `remote_dir` is empty string or `/`.
  - An end-to-end test against a real sshd is **not** written (no sshd fixture on this host); mark the gap in the test module docstring honestly.
- [ ] **Step 2: Implement.** Temp key material lives under `tempfile.mkdtemp(dir=settings-scratch)` created per operation and deleted in a `finally`; subprocesses via `asyncio.create_subprocess_exec` with explicit timeouts (`asyncio.wait_for`, 1h ship / 15m read-back); stderr tails folded into raised errors.
- [ ] **Step 3:** suite green.

---

### Task 6: The S3 destination (boto3)

**Files:**
- Modify: `backend/pyproject.toml` (add `"boto3>=1.35.0"` with a comment: one client covers AWS/R2/B2/MinIO — §9.2; sync SDK used only via `asyncio.to_thread`, never on the event loop)
- Regenerate: `backend/requirements.lock` (`uv pip compile --universal pyproject.toml -o requirements.lock` — the only sanctioned way)
- Modify: `backend/app/services/backup_ship.py` (`S3Destination`)
- Modify: `backend/tests/test_backup_ship.py`

**Interfaces:**
- Consumes: `S3Settings` (Task 2), protocol (Task 4).
- Produces: `S3Destination` in `build_destination`.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 2 = 5

- [ ] **Step 1: Failing tests.** Inject the client: `S3Destination(cfg, client_factory=...)` defaulting to a boto3 factory; tests pass a fake with `upload_file` / `get_object` / `list_objects_v2` (paginated — assert the pagination loop, a >1000-snapshot bucket must not silently prune from a truncated listing) / `delete_object`. Assert key layout `"{prefix}{filename}"`, read-back hashing streams `get_object`'s body, prune filters `darkmem-app-` and sorts by key (the stamp orders lexically).
- [ ] **Step 2: Implement.** Every boto3 call inside `await asyncio.to_thread(...)`; client built per operation from `endpoint_url/region/access_key_id/secret_access_key` (`boto3.client("s3", endpoint_url=…, region_name=…, aws_access_key_id=…, aws_secret_access_key=…)`).
- [ ] **Step 3:** Verify the lock regen carried no platform leak: `grep -c pywin32 requirements.lock` → 0 (CLAUDE.md, Backend lock). Suite green. Image rebuild sanity in Task 10 covers the size cost — stated (§9.3: "the image grows… Stated, not hidden"); boto3 adds ~90 MB installed.

---

### Task 7: The `backup_ship` job — registration, roster, CLAUDE.md

**Files:**
- Modify: `backend/app/services/job_runners.py` (`make_backup_ship_runner`)
- Modify: `backend/app/main.py` (registration among the direct `job_registry.register(Job(...))` calls, :279-410 region)
- Modify: `backend/tests/test_code_deriver.py:1520-1528` (`expected` roster set)
- Modify: `CLAUDE.md` (Jobs section: counts and lists)
- Modify: `backend/tests/test_backup_ship.py` (runner test)

**Interfaces:**
- Consumes: `ship_all` (Task 4), `BACKUP_SHIP_JOB_KEY` (Task 3).
- Produces: the scheduled job, the Jobs-page row, `POST /api/v1/jobs/backup_ship/trigger` reachability.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 2 = 5

- [ ] **Step 1: Failing test.** Extend `test_main_registers_the_full_direct_job_roster` (`backend/tests/test_code_deriver.py:1520`): add `"BACKUP_SHIP_JOB_KEY"` to `expected`. It fails until registration lands.
- [ ] **Step 2: Runner** in `job_runners.py` (the `make_llm_usage_cleanup_runner` shape at :868):

```python
def make_backup_ship_runner(app, session_factory: async_sessionmaker[AsyncSession]):
    """Dump over the stack network, encrypt, ship, verify, prune (spec §9.3).

    Does NOT shell to scripts/backup.sh — the container cannot reach it (M4);
    the systemd timer stays as the independent host-side producer, separated
    from this one by directory and filename prefix, not by any lock (m4).
    """
    async def run() -> dict:
        from app.services.backup_ship import ship_all
        return await ship_all(session_factory)
    return run
```

- [ ] **Step 3: Registration** in `main.py`, verbatim:

```python
    from app.services.backup_ship import BACKUP_SHIP_JOB_KEY
    job_registry.register(Job(
        key=BACKUP_SHIP_JOB_KEY,
        display_name="Backup Ship",
        description=(
            "Dumps the database over the stack network with the image's own "
            "pg_dump, encrypts with the destination's age recipient, ships to "
            "every enabled destination, reads each upload back to verify it, "
            "and prunes per destination. Independent of the host-side systemd "
            "backup timer by design — two producers, no shared lock."
        ),
        # 04:30 — an hour clear of the systemd timer's 03:30, because nothing
        # can serialize the two producers (m4) and dumping twice concurrently
        # doubles I/O on the same Postgres for no benefit.
        default_cron="30 4 * * *",
        min_interval_seconds=3600,
        runner=make_backup_ship_runner(app, async_session_factory),
        max_run_seconds=7200,
    ))
```

No `config_schema`: retention and destinations are the `backup_destinations` config row's (Task 2) — `FieldDescriptor` cannot carry them and must not be made to.

- [ ] **Step 4: CLAUDE.md** (invariant 23 — same commit as the registration): "Twenty-three registered jobs" → "Twenty-four" with a dated correction note in the existing style; "The seventeen live ones" → eighteen, adding `backup_ship` to the list; add `BACKUP_SHIP_JOB_KEY` to the register-via-constants sentence. **And the third occurrence this plan missed** (cross-plan review m-2, 2026-09-02): the invariant-13 paragraph at `CLAUDE.md:1648-1649` reads "every registered job fires N times per tick; 21 when T4.09 counted, **23 today**, and the number is not what the finding rests on" — update `23 today` to `24 today`. It is a different paragraph from the Jobs section and a `grep` for "Twenty-three" does not find it. Invariant 23 is about exactly this: a "here is the full list" sentence going stale because the count lives in more places than the editor checked.
- [ ] **Step 5: Runner test**: monkeypatch `ship_all`, `trigger("backup_ship")` through a `JobRegistry` instance, assert the summary dict lands in the run record (see `tests/test_job_registry.py` for the harness idiom).
- [ ] **Step 6:** Full backend suite green.

---

### Task 8: Settings binding hook and API types

**Files:**
- Create: `frontend/src/features/settings/use-backups-tab-binding.ts`
- Modify: `frontend/src/features/settings/types.ts` (destination types mirroring Task 2's pydantic models, `MASKED = "***"`)

**Interfaces:**
- Consumes: `GET/PUT /api/v1/config/backup-destinations`; `POST /api/v1/jobs/backup_ship/trigger` (existing route, `backend/app/api/routes/jobs.py:193`); `GET /events?event_type=backup_shipped` via the existing events hook.
- Produces: `useBackupsTabBinding()` returning `{destinations, save, runNow, recentOutcomes, isLoading}` — consumed by Task 9.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 0 = 3

- [ ] **Step 1:** Follow the `use-git-accounts-binding.ts` idiom (same directory): TanStack Query over `apiFetch`, `enabled: !DEMO` on every query (demo mode must make no API calls — session memory), invalidate on save. `runNow` posts the trigger and surfaces the 409-busy case as a toast-friendly result, not a throw.
- [ ] **Step 2:** `cd frontend && npm run typecheck` green.

---

### Task 9: The Backups settings tab

**Files:**
- Create: `frontend/src/features/settings/components/backups-tab.tsx`
- Modify: `frontend/src/routes/_authenticated/settings.tsx` (a `TabsTrigger value="backups"` in the list at :101-136 and a `TabsContent value="backups"` beside :140-152)
- Create: `frontend/src/features/settings/__tests__/backups.test.tsx`

**Interfaces:**
- Consumes: Task 8's binding; darkraise-ui `card`, `dialog`, `switch`, `number-input`, `empty-state`, `sonner`.
- Produces: the operator surface for §9.3's config.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Failing tests** (the settings tests' render harness — see `__tests__/` siblings): the tab lists destinations with kind and retention; secret fields render the mask and submitting an untouched mask round-trips `"***"` (the keep-stored contract); a non-local destination with no age recipient shows the inline validation error from the 422; the "Run now" button posts the trigger.
- [ ] **Step 2: Build the tab.** Destination cards (name, kind badge, enabled `switch`, retention `number-input`, last `backup_shipped`/`backup_verify_failed` outcome line from `recentOutcomes`), an add/edit `dialog` whose fields switch on kind, and a short posture paragraph stating the two-producer design: *"The host's systemd timer keeps its own local dumps independently of this job; the two never share a directory or a retention set."* Restyle built-ins; do not re-implement (CLAUDE.md, darkraise-ui rule).
- [ ] **Step 3:** `npm test -- backups && npm run typecheck && npm run build` green; the full `npm test` too (settings.tsx is rendered by other suites).

---

### Task 10: Gate, changelog, deploy

**Files:**
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: every landed diff above.
- Produces: the running instance the owner reviews.

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 0 - spec 0 - coupling 0 - risk 2 = 2

- [ ] **Step 1:** `./scripts/gate.sh` green (never `--full` casually on this host).
- [ ] **Step 2:** CHANGELOG section for the next derived version — a `feat` push to master cuts a release and fails without the matching `## vN.N.N` section. **Coordinate with the other 2026-08-31 increment plans**: one push, one section.
- [ ] **Step 3:** Commits, atomic: `feat(backup): ship encrypted dumps off-host from a registry job`, `feat(backup): destination config and settings panel`, `docs(claude): job roster gains backup_ship` (or fold the CLAUDE.md edit into the registration commit — it must land in the same push as the roster change either way).
- [ ] **Step 4: Redeploy** (owner ruling 2026-08-21):

```bash
DARKMEM_PUSH=0 ./scripts/build-push.sh   # DARKMEM_PUSH=0 is not optional
docker compose up -d
# healthy, then prove the running image carries the change:
docker exec darkmem-prod-darkmem-1 pg_dump --version
docker exec darkmem-prod-darkmem-1 ls /dumps
curl -s http://127.0.0.1:8000/openapi.json | grep -o backup-destinations
```

- [ ] **Step 5: Watch one ship.** Configure the `local` destination in the new tab, "Run now", confirm `darkmem-app-*.sql.gz` appears under `/srv/darkmem-dumps` on the host and a `backup_shipped` row lands in Activity. Then restore-drill it once against a scratch database (`scripts/restore.sh` accepts either producer's dump — same `--clean --if-exists` shape) — "uploaded is not restorable" applies to the local path too.

## Rollback

Every task is additive: revert the commits and redeploy. The `/dumps` bind mount and the image packages are inert without the job; the `backup_destinations` config row is ignored by a reverted build; no schema moved. The systemd producer is untouched throughout and keeps the floor either way.

## Notes on scope

- **The `worker` destination kind and everything §9.5/§9.6 is increment 7's** (`2026-08-31-backup-worker.md`), which consumes Task 2's config shape, Task 4's protocol and Task 3's artifacts. Land 6 before 7.
- **Off-host copying of the *systemd* dumps remains manual**, unchanged — the job is the off-host path; the timer is the floor that survives the app being down. A backup system that depends on the service it protects is not one (§9.3), which is why the job must never grow a "manage the systemd timer" feature.
- **The dump runs against the live database over the network** — `pg_dump` takes an MVCC snapshot; no lock concern beyond I/O. The 04:30 default and `max_run_seconds=7200` bound the overlap risk with the 03:30 timer (m4, stated not solved).
- **Restore drills:** rule 2 verifies bytes, not restorability-in-anger. The §9.6 UI (increment 7) surfaces verification status; an actual periodic restore drill is the worker's whole job (§9.5).
- The plan deliberately does not touch `scripts/backup.sh` or the timer unit: two producers, zero shared code, per §9.3 as amended.

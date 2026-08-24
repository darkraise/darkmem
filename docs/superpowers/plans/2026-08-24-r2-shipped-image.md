# R2 — Make the Shipped Image Able to Index a Repository

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A container built from this tree can clone and index a repository at all — `git` exists on `PATH` and `/app/data/repositories` is writable by the uid the app runs as — and CORS stops falling back to two hardcoded localhost origins that were never darkmem's.

**Architecture:** Two Dockerfile lines and one `main.py` line, plus assertions in `backend/tests/test_deployment_artifact.py` so none of the three can regress silently. The three changes are batched into one deploy because they all alter the artifact's boot configuration and this host should absorb one deploy window, not two.

**Tech Stack:** Docker, Docker Compose, FastAPI, Starlette CORSMiddleware, pytest.

**Spec:** `docs/superpowers/specs/2026-08-24-review-remediation.md`

## Why these three ship together, and why this stage merges alone

`git` absent from the runtime image and `/app/data/repositories` unwritable are two
halves of one symptom. Shipping either alone leaves repository indexing broken in the
image while the tree looks fixed — fix `git` only, and the first clone fails on a
permission error instead of a missing binary. Both were confirmed against the running
production container:

```
$ docker exec darkmem-prod-darkmem-1 sh -c 'command -v git || echo "GIT ABSENT"'
GIT ABSENT
$ docker exec darkmem-prod-darkmem-1 sh -c 'id; ls -ld /app/data/repositories'
uid=100(app) gid=101(app) groups=101(app)
drwxr-xr-x 2 root root 4096 Aug 10 15:04 /app/data/repositories
```

Production currently has zero rows in `repositories`, which is the only reason this
has not been hit. The first repository anyone adds hits both.

F16 rides along because it is the other change to the artifact's boot configuration.
**This stage merges alone and nothing else merges during its deploy window** — it
changes the artifact every later stage is verified against.

## Global Constraints

- **Backend tests:** from `backend/`, `.venv/bin/python -m pytest -q <path>`. Needs the dev Postgres on `127.0.0.1:5433` and database `darkmem_test`. Baseline on master today is **6179 passed, 22 skipped** — a change in that count is a signal, not noise.
- **Parallel lanes need their own database.** `darkmem_test_2` … `darkmem_test_5` exist for this. Keep `darkmem_test` for whoever runs the controller gate. conftest pins `DATABASE_URL` to `TEST_DATABASE_URL` and then runs `DROP SCHEMA public CASCADE` — never point a lane at a real database.
- **Frontend tests:** from `frontend/`, `npx vitest run <path>`. Typecheck is `npx tsc -b` (plain `tsc` misses the project refs). Baseline is **1233 passing**.
- **Merge gate:** `./scripts/gate.sh` from the repo root. `--full` adds the retrieval eval, the API e2e suite, Playwright and a port-hygiene diff. Each task below says which it needs and why.
- **Commits:** `<type>(<scope>): <subject>`, type one of `feat|fix|docs|style|refactor|test|chore|perf`, subject imperative, ≤ 50 characters, no trailing period. Atomic — never combine two concerns.
- **Comments:** default to none. Add one only where the WHY is non-obvious — a hidden constraint, a subtle invariant, a workaround for a specific bug. Never explain WHAT the code does; never reference this plan, this task, or a ticket.
- **Never** hardcode a value or special-case an input to make a test pass, and never use `--no-verify`. If a fix turns out to be infeasible or a finding turns out to be wrong, say so and stop — do not work around it.
- **This changes the running artifact, so it is redeployed after the gate.** `./scripts/gate.sh` → `DARKMEM_PUSH=0 ./scripts/build-push.sh` → `docker compose up -d` → wait for `healthy` → **then confirm the change is in the running image, not only in the tree**. compose reuses an image whose tag did not move, so a skipped or failed build redeploys the old bits and still reports `Started`. `DARKMEM_PUSH=0` is not optional: the script's default is to push, and image push is CI-only.
- **Verification is against the image, never the tree.** After the deploy: `docker exec darkmem-prod-darkmem-1 git --version`, `docker exec -u app darkmem-prod-darkmem-1 touch /app/data/repositories/.wcheck`, and grep the built `app/main.py` for the CORS change. A skipped or failed build redeploys the old bits and still reports `Started`.
- **Order inside this plan is fixed:** Task 1 (F09+F10) commits before Task 2 (F16). Both append to `backend/tests/test_deployment_artifact.py` and would otherwise conflict at the same offset.
- **This stage needs `--full`.** The API e2e arm boots its own disposable stack over HTTP, which is the only automated thing that exercises a booted app, and the port-hygiene diff is what catches a compose edit that moved a binding. Neither is in the floor.
- **`backend/app/services/repo_manager.py` has four claimants across the programme.** R1's Task 1 was the first; this is the second. Never two lanes at once on that file.

---

### Task 1: Ship git and a writable repo volume in the runtime image

**Effort:** ~45 minutes.

**Files:**
- Modify: `Dockerfile:41-45`
- Modify: `Dockerfile:76`
- Modify: `backend/app/services/repo_manager.py:466-489`
- Modify: `backend/tests/test_deployment_artifact.py:48-52`
- Modify: `backend/tests/test_deployment_artifact.py:164-169`
- Modify: `backend/tests/test_repos.py:263-267`
- Test: `backend/tests/test_deployment_artifact.py`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

**Owner decision this task carries** (answer before starting, not during):

One adjacent defect found while verifying this, deliberately NOT folded into the
fix because it changes the image's user layout and is an owner call.

The app user is created with `adduser --system`, which gives it no home
directory: the running container reports HOME=/nonexistent and
`getent passwd app` shows `app:x:100:101::/nonexistent:/usr/sbin/nologin`. So
`RepoManager.add_git_safe_directory` — which runs `git config --global --add
safe.directory <path>` — can never succeed inside the container. Verified
directly: with HOME=/nonexistent git exits 255 with "error: could not lock
config file /nonexistent/.gitconfig: No such file or directory". The helper is
best-effort and returns False with a warning, so nothing crashes, but it means a
bind-mounted `local_path` repository owned by any uid other than 100 will hit
git's "fatal: detected dubious ownership" refusal with no in-app remedy at all.

Two things the owner needs to settle:
(a) whether to give the app user a real writable home in the same RUN
    (`adduser --system --ingroup app --home /home/app app`, with the existing
    `chown -R app:app /app` extended to it), which would make the helper work;
(b) whether `local_path` repositories are supposed to work in the container at
    all — docker-compose.yml mounts no host source tree into the app service, so
    today the only host paths visible inside are /app and the repo_data volume,
    and a `local_path` row pointing at an operator directory is unreachable
    regardless of ownership.

Neither blocks this task: URL-backed clones land inside the volume, are created
by the uid-100 process itself, and therefore need no safe.directory entry. That
was verified end to end (clone + rev-parse succeeded as uid 100 with
HOME=/nonexistent).

- [ ] **Step 1: Write the failing test**

Three tests across two existing files. Line numbers below are from 2026-08-24 and other agent lanes are actively editing both files, so anchor on the quoted surrounding code, not on the numbers.

=====================================================================
FILE 1 of 2 — backend/tests/test_deployment_artifact.py
=====================================================================

STEP 1a. Add two module-level helpers. Insert them immediately AFTER the
existing `_compose_command` helper and BEFORE the `LAUNCH_PATHS = {` dict.
The existing anchor reads:

    def _compose_command(path: Path, service: str) -> str:
        command = _compose(path)["services"][service].get("command", "")
        return " ".join(command) if isinstance(command, list) else command


    LAUNCH_PATHS = {

Insert between them:

def _dockerfile_stages() -> dict[str, str]:
    """The Dockerfile split into its named build stages, continuations joined."""
    stages: dict[str, str] = {}
    name: str | None = None
    for line in _unwrapped(DOCKERFILE).splitlines():
        header = re.match(r"^FROM\s+\S+\s+AS\s+(\S+)", line, re.IGNORECASE)
        if header:
            name = header.group(1)
            stages[name] = ""
            continue
        if name is not None:
            stages[name] += line + "\n"
    return stages


def _named_volume_targets(service: str) -> list[str]:
    compose = _compose(PROD_COMPOSE)
    declared = set(compose.get("volumes") or {})
    targets = []
    for entry in compose["services"][service].get("volumes", []):
        source, _, rest = str(entry).partition(":")
        if source in declared:
            targets.append(rest.split(":")[0])
    return targets


(`re`, `yaml`, `Path`, `_unwrapped`, `_compose`, `DOCKERFILE`, `PROD_COMPOSE`
and `APP_SERVICE` are already imported/defined at the top of this file, and the
file already carries `from __future__ import annotations`, so `str | None` and
`dict[str, str]` need no further import.)

STEP 1b. Add the two tests. Insert them immediately AFTER the existing
`test_prod_app_service_publishes_its_port_and_keeps_its_repo_volume`, which
reads:

    def test_prod_app_service_publishes_its_port_and_keeps_its_repo_volume():
        service = _compose(PROD_COMPOSE)["services"][APP_SERVICE]
        assert "8000:8000" in service["ports"], service["ports"]
        assert any(v.startswith("repo_data:") for v in service["volumes"]), service["volumes"]

Insert after it:

# ── The runtime image can actually serve the repo volume it mounts ────


def test_runtime_stage_installs_git():
    """RepoManager shells out to `git` by name for every clone, fetch and
    rev-parse. The builder stage's toolchain is discarded and never carried git
    anyway, so without this the first repository anyone adds dies in the
    subprocess call rather than anywhere the operator can see."""
    runtime = _dockerfile_stages()["runtime"]
    installs = [ln for ln in runtime.splitlines() if "apt-get install" in ln]
    assert installs, "the runtime stage installs no packages at all"
    assert any(re.search(r"(?<![\w.-])git(?![\w.-])", ln) for ln in installs), installs


def test_every_named_volume_mountpoint_is_created_before_the_chown():
    """Docker copies the image path's ownership onto an empty named volume the
    first time it mounts it, so a mount point the image never creates is
    initialised root-owned and the uid-100 process cannot write into it. The
    chown is the cut-off because it is what hands the directory to `app`."""
    runtime = _dockerfile_stages()["runtime"].splitlines()
    chown_at = next(
        (i for i, ln in enumerate(runtime)
         if re.search(r"chown\s+-R\s+app:app\s+/app\b", ln)),
        None,
    )
    assert chown_at is not None, "the runtime stage no longer chowns /app to app:app"
    before_chown = "\n".join(runtime[:chown_at])
    targets = _named_volume_targets(APP_SERVICE)
    assert targets, "prod compose mounts no named volume on the app service"
    for target in targets:
        assert re.search(
            rf"mkdir\s+-p\s+{re.escape(target)}(?![\w/])", before_chown
        ), target


=====================================================================
FILE 2 of 2 — backend/tests/test_repos.py
=====================================================================

STEP 2. Append this test at the end of the file. It sits beside the existing
`test_add_git_safe_directory_returns_false_on_failure`, which raises the same
FileNotFoundError from the same fake `subprocess.run`, and matches this file's
house style of importing inside the test body.

async def test_run_git_reports_a_missing_binary_as_runtime_error(tmp_path, monkeypatch):
    """`pull_repo`'s whole recovery path is `except RuntimeError`. A runtime
    image with no git executable raises FileNotFoundError, which walks straight
    past that handler and out of every caller as an uncaught 500."""
    from app.services.repo_manager import RepoManager
    import pytest
    import subprocess

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", "git")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as excinfo:
        await RepoManager._run_git(tmp_path, ["git", "rev-parse", "HEAD"])
    assert "git rev-parse HEAD" in str(excinfo.value)


- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
From /root/repositories/darkmem/backend:

  .venv/bin/python -m pytest -q \
    tests/test_deployment_artifact.py::test_runtime_stage_installs_git \
    tests/test_deployment_artifact.py::test_every_named_volume_mountpoint_is_created_before_the_chown \
    tests/test_repos.py::test_run_git_reports_a_missing_binary_as_runtime_error

Then, as the regression sweep for the surrounding behaviour:

  .venv/bin/python -m pytest -q tests/test_deployment_artifact.py tests/test_repos.py \
    tests/test_code_reconcile.py tests/test_index_debt.py tests/test_code_fail_stale.py \
    tests/test_push_webhook.py tests/test_summary_carryover.py tests/test_memory_dream_residue.py

Both need the dev Postgres on 127.0.0.1:5433 with database darkmem_test.
```

Expected — this is what the run actually printed on master:

The three-node-id command prints `3 failed` (measured 2026-08-24):

  FAILED tests/test_deployment_artifact.py::test_runtime_stage_installs_git - AssertionError: the runtime stage installs no packages at all
  FAILED tests/test_deployment_artifact.py::test_every_named_volume_mountpoint_is_created_before_the_chown - AssertionError: /app/data/repositories
  FAILED tests/test_repos.py::test_run_git_reports_a_missing_binary_as_runtime_error - FileNotFoundError: [Errno 2] No such file or directory: 'git'
  3 failed, 1 warning in 0.73s

The third failure is the exact shape of the production bug: the FileNotFoundError
propagates out of `_run_git` instead of the RuntimeError the callers handle, so
`pytest.raises(RuntimeError)` never catches it (FileNotFoundError is an OSError,
not a RuntimeError).

Independent live confirmation on the running production container, which is what
the two artefact tests stand in for:

  $ docker exec darkmem-prod-darkmem-1 sh -c 'id; command -v git || echo NO_GIT; ls -ld /app/data/repositories; touch /app/data/repositories/.w'
  uid=100(app) gid=101(app) groups=101(app)
  NO_GIT
  drwxr-xr-x 2 root root 4096 Aug 10 15:04 /app/data/repositories
  touch: cannot touch '/app/data/repositories/.w': Permission denied

- [ ] **Step 3: Apply the fix**

Three edits. All were applied and verified on 2026-08-24, then reverted; the
quoted "current code" below is what is on master right now.

---------------------------------------------------------------------
EDIT 1 of 3 — Dockerfile, install git in the runtime stage (F09)
---------------------------------------------------------------------

CURRENT (Dockerfile lines 41-45):

FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

REPLACE WITH:

FROM python:3.12-slim AS runtime

WORKDIR /app

# RepoManager shells out to `git` by name for every clone, fetch and
# rev-parse, so the runtime image needs the binary even though the build
# toolchain above stays in the discarded builder stage.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

Placement matters for build caching: putting the apt layer above the
`COPY --from=builder` means it is invalidated only by a base-image change, not
by every dependency or source edit. `ca-certificates` is already present in
python:3.12-slim (verified: `dpkg -l ca-certificates` reports 20250419 in the
running container), so it installs nothing today — it is named because git's
HTTPS transport depends on it and relying on the base image implicitly is
exactly the class of assumption that produced this bug.

---------------------------------------------------------------------
EDIT 2 of 3 — Dockerfile, create the volume mount point (F10)
---------------------------------------------------------------------

CURRENT (Dockerfile line 76, the last RUN before USER):

RUN addgroup --system app && adduser --system --ingroup app app && chown -R app:app /app
USER app

REPLACE WITH:

# docker-compose.yml mounts the repo_data volume here. Docker copies the
# image path's ownership onto an empty named volume at first mount, so the
# directory has to exist and be app-owned in the image or every clone lands
# in a root-owned mount the uid-100 process cannot write.
RUN mkdir -p /app/data/repositories

RUN addgroup --system app && adduser --system --ingroup app app && chown -R app:app /app
USER app

The mkdir MUST come before the chown; that ordering is what the second test
asserts. Nothing about docker-compose.yml changes.

Note on the already-existing volume: darkmem-prod_repo_data was created
2026-08-10 and its _data directory is root-owned and EMPTY. Docker's
copyExistingContents runs copyOwnership unconditionally on an empty named
volume, so the existing volume is repaired by the ordinary redeploy — no
`docker volume rm`, no manual chown. Verified end to end with a throwaway image
and a pre-created root-owned volume: after the fix the container reported
`drwxr-xr-x app app /app/data/repositories`, `git clone` into it succeeded as
uid 100 with HOME=/nonexistent, and `git rev-parse HEAD` returned the sha.

---------------------------------------------------------------------
EDIT 3 of 3 — backend/app/services/repo_manager.py, _run_git (F09, code half)
---------------------------------------------------------------------

CURRENT (inside `async def _run_git`, around line 478):

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"git command timed out after 300s: {_sanitize_url(' '.join(cmd))}")
        stderr_text = result.stderr.decode()

REPLACE WITH:

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"git command timed out after 300s: {_sanitize_url(' '.join(cmd))}")
        except OSError as exc:
            # pull_repo's whole recovery path is `except RuntimeError`; an image
            # with no git executable raises FileNotFoundError, which walks past
            # it and out of every caller.
            raise RuntimeError(
                f"git command could not be run: {_sanitize_url(' '.join(cmd))}: {exc}"
            ) from exc
        stderr_text = result.stderr.decode()

`OSError` rather than `FileNotFoundError` because the same handler is the right
answer for a vanished cwd (NotADirectoryError) and for an exec permission
failure; `subprocess.TimeoutExpired` derives from SubprocessError, not OSError,
so the two clauses do not overlap and the ordering is free. `_sanitize_url` is
applied for the same reason the two existing raises apply it: `cmd` can carry
an `x-access-token:<pat>@host` URL on an authed clone.

---------------------------------------------------------------------
AFTER LANDING — this alters the running artifact (Dockerfile + backend/),
so the host must be redeployed:

  ./scripts/gate.sh
  DARKMEM_PUSH=0 ./scripts/build-push.sh     # the DARKMEM_PUSH=0 is not optional
  docker compose up -d                        # wait for `healthy`

Then confirm the change is in the RUNNING image, not just the tree — compose
reuses an image whose tag did not move, so a skipped build still reports
Started:

  docker exec darkmem-prod-darkmem-1 sh -c 'command -v git && ls -ld /app/data/repositories && touch /app/data/repositories/.w && rm /app/data/repositories/.w && echo OK'

Expected: `/usr/bin/git`, a line reading `drwxr-xr-x ... app app ...`, then `OK`.

The schema baseline (backend/migrations/versions/0001_baseline.py) is NOT
touched by this task.

- [ ] **Step 4: Run the same command and confirm it passes**

The three-node-id command prints:

  3 passed, 1 warning in 0.55s

The regression sweep over the eight neighbouring files prints:

  100 passed, 36 warnings in 8.25s

(measured 2026-08-24 with the fix applied; the neighbour count moves as other
lanes land tests, the point is zero failures.)

- [ ] **Step 5: Run the surrounding suite for regressions**

Honest list, in descending order of plausibility.

1. `_run_git` now converts OSError into RuntimeError, which widens what
   `pull_repo`'s `except RuntimeError` swallows. Concretely, for a URL-backed
   repo whose git is missing, control now reaches `needs_clone = True`, which
   `shutil.rmtree`s the existing clone directory before attempting the re-clone
   and failing again — where previously the FileNotFoundError escaped before the
   rmtree. That deletes a clone, not user data, and it is only reachable when
   there is no git binary, which edit 1 removes. Called out because it is a real
   behaviour change, not a pure widening.
   For a `local_path` repo the new path logs "Pull failed for local repo
   (working tree left intact)" and returns None instead of raising; the
   operator's checkout is explicitly not touched on that branch.

2. Image size grows by roughly 50 MB in the runtime layer (git plus its
   dependencies). Nothing in the tree asserts an image size or layer count, and
   `test_dockerfile_bakes_in_no_secret` only inspects ARG/ENV lines, so the new
   RUN is invisible to it. The compose memory limit (1g) is unaffected — git is
   on disk, not resident.

3. The build now makes network calls to the Debian archive in the runtime stage.
   The builder stage already does exactly this for build-essential, so the
   build already depends on apt reachability; this adds a second point where a
   dead mirror fails the build.

4. `git` inside the image also becomes reachable from `code_pipeline.py:1756`
   and `api/mcp/server.py:1166-1171`, which call `RepoManager._run_git` for
   `git diff --name-status`. Those paths were dead in the container and now
   execute for real. They are already exercised in the test suite against a
   host git, so this is coverage catching up with production, not new logic.

Existing tests that cover the surrounding behaviour, all green with the fix
applied (verified 2026-08-24, 100 passed):
  backend/tests/test_deployment_artifact.py  — the Dockerfile/compose artefact contract
  backend/tests/test_repos.py                — RepoManager create/delete/validate, add_git_safe_directory, mark_periodic_sync_failure
  backend/tests/test_code_reconcile.py       — pull_repo stubbed, repo_working_dir, indexing claims
  backend/tests/test_code_fail_stale.py      — the stale/error terminal statuses a pull failure produces
  backend/tests/test_index_debt.py           — the debt drain across a pull
  backend/tests/test_push_webhook.py         — pull_repo monkeypatched on the class
  backend/tests/test_summary_carryover.py, backend/tests/test_memory_dream_residue.py — further pull_repo stubs

COLLISION WARNING (as of 2026-08-24 21:30): other agent lanes have
backend/tests/test_deployment_artifact.py modified in the working tree (they
added `test_cors_origins_is_reachable_and_defaults_to_a_parseable_empty_list`
around line 137, in a different section from these additions), and
backend/app/services/repo_manager.py was modified and reverted twice during
this session (a `pull_repo` `--ff-only` change and a `release_indexing_claim`
method). Neither overlaps the `_run_git` except clause or the compose-surface
test section, but both files are shared. Re-read the anchors before editing.

Unrelated housekeeping done while preparing this: a stale, empty
/root/repositories/darkmem/.git/index.lock (81 minutes old, no git process
holding it) was blocking every write-side git command in the repo and was
removed.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile backend/app/services/repo_manager.py backend/tests/test_deployment_artifact.py backend/tests/test_repos.py
git commit -m "fix(docker): ship git and a writable repo volume"
```

### Task 2: Drop the hardcoded CORS fallback origins

**Effort:** ~25 minutes.

**Files:**
- Modify: `backend/app/main.py:814-820`
- Modify: `docker-compose.yml:77-78`
- Modify: `.env.example:45-46`
- Modify: `backend/tests/test_deployment_artifact.py:130-137`
- Create: `backend/tests/test_cors_policy.py`
- Test: `backend/tests/test_cors_policy.py`

**Interfaces:**
- Consumes: nothing from another task in this plan.
- Produces: no new exported symbol — this task changes behaviour inside an existing function.

**Owner decision this task carries** (answer before starting, not during):

CORS_ORIGINS only accepts a JSON array, because config.py types it as list[str]
and pydantic-settings decodes list fields from the environment as JSON.
`CORS_ORIGINS=https://ui.example.com` and `CORS_ORIGINS=a,b` both make the app
refuse to boot with a SettingsError. That diverges from the neighbouring
MCP_ALLOWED_HOSTS, which is typed `str` and parsed from a comma-separated value
by a helper — so an operator who copies that convention gets a dead stack.

Once the fallback is gone, this is the only lever, so the spelling matters more
than it did. Changing cors_origins to a `str` plus a splitter (mirroring
_parse_mcp_allowed_hosts) is a config-shape change with its own surface
(GET /auth/security-posture does not currently serve it, but any future settings
UI would), so I did not make it unilaterally. Owner call: keep the JSON-array
spelling documented in .env.example as this task does, or convert it to CSV in a
follow-up.

- [ ] **Step 1: Write the failing test**

CREATE backend/tests/test_cors_policy.py with exactly this content:

"""Cross-origin policy — an unconfigured deployment allows no credentialed
cross-origin access at all.

Every darkmem client is same-origin: the built SPA is served by the API on
:8000, the dev vite server on :3636 proxies ``/api`` to it, and the browser
extension carries a bearer token from a ``chrome-extension://`` origin. So an
allowlist entry that no client asks for is pure attack surface, and these two
in particular are reachable: SameSite computes "site" from scheme plus
registrable domain and ignores the port, so ``http://localhost:5173`` and
``http://localhost:8000`` are the same site and the ``samesite="strict"``
session cookie rides a ``credentials: 'include'`` fetch between them.
``Access-Control-Allow-Origin`` is then the only thing deciding whether the
calling page may read the reply.
"""
from __future__ import annotations

import pytest
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
from app.main import app

VITE_AND_CRA_DEFAULT_PORTS = ["http://localhost:3000", "http://localhost:5173"]


def _cors_allow_origins() -> list[str]:
    for middleware in app.user_middleware:
        if middleware.cls is CORSMiddleware:
            return list(middleware.kwargs["allow_origins"])
    raise AssertionError("CORSMiddleware is not installed on the app")


def test_the_allowlist_is_exactly_what_the_operator_configured():
    """No literal origin may be baked into the middleware call.

    Stated against ``settings.cors_origins`` rather than against the empty
    list so it holds on a deployment that legitimately names an origin: the
    property is that the allowlist has one source, not that it is empty.
    """
    assert _cors_allow_origins() == list(settings.cors_origins)


@pytest.mark.parametrize("origin", VITE_AND_CRA_DEFAULT_PORTS)
async def test_unconfigured_deployment_refuses_a_credentialed_cross_origin_read(
    client, auth_headers, origin,
):
    """The reply is produced, but no origin is licensed to read it.

    ``Access-Control-Allow-Credentials`` survives on the response either way —
    starlette emits it unconditionally when ``allow_credentials`` is set — and
    it is inert on its own, so the assertion is on the header that actually
    grants the read.
    """
    assert origin not in settings.cors_origins, (
        "this test describes an unconfigured deployment, but CORS_ORIGINS names "
        f"{origin}"
    )

    response = await client.get(
        "/api/v1/auth/audit?limit=1", headers={**auth_headers, "Origin": origin},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("origin", VITE_AND_CRA_DEFAULT_PORTS)
async def test_unconfigured_deployment_refuses_the_preflight(client, origin):
    """The write side is refused before the request is ever made."""
    assert origin not in settings.cors_origins

    response = await client.options(
        "/api/v1/memories",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


---

ALSO ADD this test to backend/tests/test_deployment_artifact.py, immediately
after `test_prod_compose_requires_both_secrets_at_runtime` (which ends at line
134 with `assert f"${{{secret}:?" in entry, entry`) and before the
`# ── The compose surface doc 19 section 5 fixes ─` banner comment. Insert two
blank lines, the function, then keep the two blank lines before the banner:

def test_cors_origins_is_reachable_and_defaults_to_a_parseable_empty_list():
    """The prod stack's environment is an explicit allowlist, so a setting the
    app reads is unreachable until it is named here.

    The default is the JSON empty array, not an empty string: ``cors_origins``
    is typed as a list and pydantic-settings decodes a list from the
    environment as JSON, so ``${CORS_ORIGINS:-}`` raises SettingsError while
    ``app.config`` is still importing and the container never boots.
    """
    environment = _compose(PROD_COMPOSE)["services"][APP_SERVICE]["environment"]
    entry = next(
        (e for e in environment if e.startswith("CORS_ORIGINS=")), None,
    )
    assert entry is not None, "CORS_ORIGINS is not passed through to the app"
    assert entry == "CORS_ORIGINS=${CORS_ORIGINS:-[]}", entry

No new imports are needed — `_compose`, `PROD_COMPOSE` and `APP_SERVICE` are
already module-level in that file.

- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run:

```bash
cd /root/repositories/darkmem/backend && .venv/bin/python -m pytest -q tests/test_cors_policy.py tests/test_deployment_artifact.py

(Needs the dev Postgres on 127.0.0.1:5433 with database darkmem_test. If you are
running several lanes at once, prefix the command with
TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_N"
against your own lane database.)
```

Expected — this is what the run actually printed on master:

6 failed, 22 passed.

tests/test_cors_policy.py::test_the_allowlist_is_exactly_what_the_operator_configured
    >       assert _cors_allow_origins() == list(settings.cors_origins)
    E       AssertionError: assert ['http://loca...calhost:5173'] == []
    E         Left contains 2 more items, first extra item: 'http://localhost:3000'

tests/test_cors_policy.py::test_unconfigured_deployment_refuses_a_credentialed_cross_origin_read[http://localhost:3000]
tests/test_cors_policy.py::test_unconfigured_deployment_refuses_a_credentialed_cross_origin_read[http://localhost:5173]
    >       assert "access-control-allow-origin" not in response.headers
    E       assert 'access-control-allow-origin' not in Headers({'content-length': '43',
            'content-type': 'application/json', 'access-control-allow-credentials': 'true',
            'access-control-allow-origin': 'http://localhost:3000', ...})

tests/test_cors_policy.py::test_unconfigured_deployment_refuses_the_preflight[http://localhost:3000]
tests/test_cors_policy.py::test_unconfigured_deployment_refuses_the_preflight[http://localhost:5173]
    >       assert response.status_code == 400
    E       assert 200 == 400
    E        +  where 200 = <Response [200 OK]>.status_code

tests/test_deployment_artifact.py::test_cors_origins_is_reachable_and_defaults_to_a_parseable_empty_list
    >       assert entry is not None, "CORS_ORIGINS is not passed through to the app"
    E       AssertionError: CORS_ORIGINS is not passed through to the app
    E       assert None is not None

All six were observed failing on this tree at commit 35778a6d.

- [ ] **Step 3: Apply the fix**

THREE edits. Only the first is the security fix; the other two exist because
removing the fallback makes CORS_ORIGINS the only remaining lever, and on the
shipped stack that lever is currently unreachable (the prod compose passes an
explicit env allowlist through to the container, and CORS_ORIGINS is not on it).

── 1. backend/app/main.py, lines 814-820 ──────────────────────────────────────

CURRENT (line 814 begins the block, directly under the `app = FastAPI(...)` line):

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPLACE WITH:

# Empty is the right default: the SPA is served by this app and the dev vite
# server proxies /api, so every first-party client is same-origin and needs no
# entry here. A fallback origin would be readable by any page on that port —
# SameSite ignores the port, so the session cookie rides a cross-origin fetch
# to it and only Access-Control-Allow-Origin decides who may read the reply.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

No import changes. `settings.cors_origins` already defaults to `[]`
(backend/app/config.py:77) and already strips a `"*"` entry in the
`_check_cors_origins` validator, so the `allow_credentials=True` /
`allow_origins=["*"]` illegal combination remains impossible.

── 2. docker-compose.yml, after line 77 ───────────────────────────────────────

CURRENT (line 77, the last entry in the darkmem service's `environment:` list):

      - MCP_ALLOWED_HOSTS=${MCP_ALLOWED_HOSTS:-}

REPLACE WITH:

      - MCP_ALLOWED_HOSTS=${MCP_ALLOWED_HOSTS:-}
      # Cross-origin allowlist for credentialed browser calls. Empty is
      # correct for the shipped topology — this app serves the SPA, so every
      # first-party client is same-origin. The default is the JSON empty array
      # rather than an empty string because config.py types this as a list and
      # pydantic-settings decodes a list from the environment as JSON: a bare
      # `${CORS_ORIGINS:-}` makes the container refuse to boot.
      - CORS_ORIGINS=${CORS_ORIGINS:-[]}

The `[]` default is not cosmetic and was measured on this tree:

  CORS_ORIGINS=''                          -> pydantic_settings.exceptions.SettingsError:
                                              error parsing value for field "cors_origins"
  CORS_ORIGINS='http://a.example'          -> same SettingsError (not valid JSON)
  CORS_ORIGINS='[]'                        -> []
  CORS_ORIGINS='["http://a.example"]'      -> ['http://a.example']

The error is raised at `app/config.py:218` while the module is still importing,
so it is a boot failure, not a 500.

── 3. .env.example, after line 45 ─────────────────────────────────────────────

CURRENT (line 45, the last line of the MCP allowlist block):

MCP_ALLOWED_HOSTS=

REPLACE WITH:

MCP_ALLOWED_HOSTS=

# Origins allowed to make credentialed cross-origin browser calls to the API.
# Leave this alone unless a browser client is served from some OTHER origin:
# darkmem serves its own UI, so the UI is same-origin and needs no entry, and
# an entry here lets any page on that origin read authenticated responses.
# The value is a JSON array, e.g. CORS_ORIGINS=["https://ui.example.com"].
CORS_ORIGINS=[]

── Deploy ─────────────────────────────────────────────────────────────────────

This alters the running artifact (backend/ and docker-compose.yml), so after it
lands the host must be redeployed per CLAUDE.md: ./scripts/gate.sh ->
DARKMEM_PUSH=0 ./scripts/build-push.sh -> docker compose up -d -> wait for
`healthy` -> confirm the change is in the running image, e.g.
`docker exec darkmem-prod-darkmem-1 grep -n "allow_origins" /app/app/main.py`
(it must NOT show the localhost list). It does NOT touch
backend/migrations/versions/0001_baseline.py, so no drop/recreate is involved.

- [ ] **Step 4: Run the same command and confirm it passes**

28 passed.

Verified on this tree: with all three edits applied,
`.venv/bin/python -m pytest -q tests/test_cors_policy.py tests/test_deployment_artifact.py`
prints `28 passed, 5 warnings in 1.25s` (5 new CORS tests + 23 deployment-artifact
tests, one of which is the new one).

Behaviour after the fix, confirmed against the live app:
  - GET /api/v1/auth/audit with a valid bearer token and Origin:
    http://localhost:5173 still returns 200 with the real body, but carries no
    Access-Control-Allow-Origin, so a browser blocks the calling page from
    reading it.
  - The matching preflight (OPTIONS /api/v1/memories, Access-Control-Request-
    Method: POST) returns 400 "Disallowed CORS origin" with no
    Access-Control-Allow-Origin.
  - CORS_ORIGINS='["https://ui.example.com"]' still produces
    allow_origins=['https://ui.example.com'], so the escape hatch works.

- [ ] **Step 5: Run the surrounding suite for regressions**

Low, and the blast radius was checked rather than assumed.

WHAT COULD BREAK: any browser client served from an origin other than the API's
own. There is none in this repository. Verified:
  - frontend/vite.config.ts pins the dev server to :3636 and proxies /api,
    /health and /ws to the backend, so the dev SPA is same-origin and sends no
    Origin header the middleware would have to answer.
  - The built SPA is served by this same app on :8000 (app/api/spa.py), so
    production is same-origin too.
  - extension/ posts with an Authorization bearer token from an MV3 service
    worker holding host_permissions for http://localhost:8000/*; its Origin is
    chrome-extension://<id>, which the fallback list never matched anyway, and
    service-worker fetches under host_permissions are not CORS-gated.
  - `rg` over backend/tests, backend/scripts, frontend/src, frontend/tests,
    extension and docs/e2e finds no other consumer of localhost:3000 or
    localhost:5173 and no test that sends an Origin header to the REST app.
    The only Origin-sending test is tests/test_mcp_transport_security.py, and
    that exercises the MCP transport's own allowlist
    (app/api/mcp/server.py::build_transport_security), which is a separate
    mechanism this change does not touch.

SECOND RISK, and the reason edit 2 is spelled `${CORS_ORIGINS:-[]}`: shipping
`${CORS_ORIGINS:-}` instead would make every container boot raise SettingsError
during `import app.config`. The new test_deployment_artifact.py assertion pins
the exact spelling so that mistake cannot land silently.

EXISTING TESTS COVERING THE SURROUNDING BEHAVIOUR (all green with the fix
applied — 62 passed together):
  backend/tests/test_deployment_artifact.py    — the compose/entrypoint surface
  backend/tests/test_security_posture.py       — GET /auth/security-posture
  backend/tests/test_exposed_deployment_posture.py — trust_proxy_headers posture
  backend/tests/test_auth_security.py          — cookie flags, token rotation
  backend/tests/test_setup_security.py         — trust-on-first-use gating
  backend/tests/test_mcp_transport_security.py — the /mcp Host + Origin allowlist
  backend/tests/test_uvicorn_proxy_headers.py  — --no-proxy-headers, real uvicorn

FULL-SUITE RUN with the fix applied: 6192 passed, 22 skipped in 271s. Three
failures were observed in that run and none of them is caused by this change —
tests/test_repos.py::test_pull_repo_never_rewinds_a_local_checkout and two
tests/test_deployment_artifact.py restore-script tests that do not exist in the
file as committed, both artefacts of other agent lanes editing the shared
working tree concurrently. Separately,
tests/test_backup_script.py has 3 pre-existing failures on this host (the
retention/dump tests need pg_dump, which is not installed here); they fail
identically with and without this change.

- [ ] **Step 6: Commit**

```bash
git add .env.example backend/app/main.py backend/tests/test_cors_policy.py backend/tests/test_deployment_artifact.py docker-compose.yml
git commit -m "fix(security): drop the CORS fallback origins

`settings.cors_origins` defaults to empty and the prod compose never set
CORS_ORIGINS, so every shipped stack allowed credentialed cross-origin
access from http://localhost:3000 and http://localhost:5173 with
allow_methods=["*"]. Neither port belongs to darkmem: the built SPA is
served by this app and the dev vite server on :3636 proxies /api, so both
are same-origin. SameSite ignores the port, so the strict session cookie
rides a cross-origin fetch from those ports and Access-Control-Allow-Origin
was the only thing gating the read.

Pass the configured list straight through, expose CORS_ORIGINS on the prod
compose so a genuine cross-origin client can still be named, and default it
to the JSON empty array — a bare ${CORS_ORIGINS:-} fails to parse and stops
the container booting."
```

---

## Finishing this plan

- [ ] `./scripts/gate.sh --full` from the repo root. This arm needs `DEEPSEEK_API_KEY` exported or the gate exits `GATE BLOCKED` at preflight — that is a missing toolchain, not a red gate. The key is in `.claude/local-credentials.md`; export it, never copy it anywhere tracked.
- [ ] `DARKMEM_PUSH=0 ./scripts/build-push.sh` → `docker compose up -d` → wait for `healthy`.
- [ ] Confirm all three changes in the running image, not the tree:
  ```bash
  docker exec darkmem-prod-darkmem-1 git --version
  docker exec -u app darkmem-prod-darkmem-1 touch /app/data/repositories/.wcheck && echo WRITABLE
  docker exec darkmem-prod-darkmem-1 grep -n 'cors_origins' app/main.py
  ```
- [ ] Then, and only then, let R3 and R4 merge.

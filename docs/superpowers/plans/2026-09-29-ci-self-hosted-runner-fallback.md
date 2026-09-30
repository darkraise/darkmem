# CI Self-Hosted Runner Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Plan review:** 2026-09-29 — dr-superpowers:judge-opus — executability 13 / coherence 17 / coverage 18 / assumptions 13 (round 2)

**Goal:** Every CI and release job runs on an idle self-hosted `darkmem-ci` runner when one exists at the start of the run, and on `ubuntu-latest` otherwise.

**Architecture:** A stdlib-only `scripts/pick_runner.py` lists the repository's runners and prints a JSON `runs-on` value; a `pick-runner` job in each workflow exposes it, and every other job reads `fromJSON(needs.pick-runner.outputs.runs-on)`. Jobs stop depending on fixed host ports, container names and host `psql`, so they are safe on a shared Docker host.

**Tech Stack:** GitHub Actions YAML, Python 3.12 stdlib, pytest, `rhysd/actionlint` (Docker image).

**Spec:** docs/superpowers/specs/2026-09-29-ci-self-hosted-runner-fallback-design.md

**Execution:** inline — `claude --model opus --effort low` — two of four tasks total 4, more than a third, so none is delegated and the session implements all four; the per-task `**Implementer:**` lines are the scored assignment, informational under inline execution.

## Global Constraints

- Branch `ci/self-hosted-runner-fallback`. **Never push master**: a master push cuts a release (CLAUDE.md, "A deploy is not a release").
- The runner label is exactly `darkmem-ci`; the self-hosted `runs-on` value is exactly `["self-hosted","linux","x64","darkmem-ci"]`; the hosted value is exactly `"ubuntu-latest"` (both as JSON text).
- The token secret is named exactly `RUNNER_PICKER_TOKEN`.
- Every picking path answers hosted on doubt: missing token, API error, unknown request, no idle labelled runner.
- No step may use `--network host`, a fixed host port, a fixed container name or a fixed image tag.
- Lint workflows with `rhysd/actionlint:1.7.12` (pinned; the baseline below was measured with it).
- Commit format `<type>(<scope>): <subject>`, subject ≤ 50 chars.

## Contracts

- **C1 — picker CLI.** `python3 scripts/pick_runner.py` reads env `REQUESTED` (`auto` | `hosted` | `self-hosted`, default `auto`), `GH_TOKEN`, `GITHUB_REPOSITORY`, `GITHUB_OUTPUT`, `GITHUB_STEP_SUMMARY`. It appends `runs-on=<json>` and `reason=<one line>` to `$GITHUB_OUTPUT` and exits 0 on every picking path.
- **C2 — `choose(runners: list[dict], requested: str, token_present: bool) -> tuple[str, str]`** in `scripts/pick_runner.py`, pure; returns `(runs_on_json, reason)`.
- **C3 — `pick-runner` job** in each workflow, output `runs-on` (C1's JSON). Consumers write `runs-on: ${{ fromJSON(needs.pick-runner.outputs.runs-on) }}` and list `pick-runner` in `needs`. The one exception is `release.yml`'s `verify`, a reusable-workflow call that cannot carry `runs-on`: it passes the raw string as `with: runs-on: ${{ needs.pick-runner.outputs.runs-on }}` (C4).
- **C4 — `ci.yml` inputs.** `workflow_dispatch` input `runner` (choice `auto`/`hosted`/`self-hosted`, default `auto`); `workflow_call` input `runs-on` (string, default `''`): when non-empty, `ci.yml`'s `pick-runner` echoes it and makes no API call.

## Assumptions (evidence)

- The repository is private (`gh repo view --json visibility,isPrivate` → `PRIVATE`, 2026-09-29), so `pull_request` code comes only from collaborators; it is user-owned (`gh api users/darkraise --jq .type` → `User`), so only repository-level runners exist, and none is registered (`gh api repos/darkraise/darkmem/actions/runners` → `{"total_count":0,"runners":[]}`, 2026-09-29).
- `GITHUB_TOKEN` cannot list runners (the endpoint needs Administration read): https://docs.github.com/en/rest/actions/self-hosted-runners#list-self-hosted-runners-for-a-repository.
- The `job` context is available in steps but not in job-level `env`: https://docs.github.com/en/actions/learn-github-actions/contexts#context-availability. Hence ports are written to `GITHUB_ENV` in a step.
- `job.services.<id>.network`, `.id` and `.ports` exist: https://docs.github.com/en/actions/learn-github-actions/contexts#job-context. That a service container answers on that network under its service id (`postgres`) as hostname is unverified — Task 2 Step 9's watched run verifies it (the smoke probe fails if it does not resolve).
- `job.services.<id>.ports` is keyed by string: actionlint 1.7.12 rejects `ports[5432]` ("property access of object must be type of string but got \"number\"") and accepts `ports['5432']`, measured on a scratch workflow 2026-09-29.
- Plan review closed at round 2 (the cap) with executability 13 and assumptions 13, borderline: the one Important finding (the numeric port index) and three Minors were fixed after it, with the port fix measured above, so no further round was run.
- `backend/tests/conftest.py:14` and the harness read `TEST_DATABASE_URL` / `BENCH_DATABASE_URL` from the environment; other `5433` literals in tests are strings under test, not connections (`rg -n 5433 backend/tests backend/scripts/benchlib/tests`, 2026-09-29). Unverified that no test connects on a literal 5433 — Task 2 verifies it with a real CI run.
- The app listens on `0.0.0.0:8000` inside the image (`entrypoint.sh:20`).
- `actionlint` is not installed on this host (`which actionlint` empty, 2026-09-29); tasks run the `rhysd/actionlint:1.7.12` image. Baseline on the unmodified workflows (2026-09-29): with `-shellcheck=` it exits 0; with shellcheck on it reports 0 findings in `ci.yml` and 7 pre-existing shellcheck findings in `release.yml` (SC2016 and others). The checks therefore require exit 0 with `-shellcheck=`, 0 findings in `ci.yml`, and no more than 7 in `release.yml`.
- Release jobs routed to the picked runner use these host tools beyond Docker: `git` (prepare, tag), `python3` via `actions/setup-python` (plan, github-release), `sed` (prepare), and `gh` (github-release, `release.yml:434`). `ubuntu-latest` ships all of them; the runbook's machine requirements list them (Task 4).
- `backend/tests/conftest.py:59-65` has an autouse session fixture that resets `darkmem_test` on the dev Postgres; the picker tests need no database, so they run with `--noconftest`.
- `ci.yml` has no push trigger (`.github/workflows/ci.yml:3-12`), so pushing a non-master branch starts nothing until it is dispatched.
- The Codex executor lane is off (`codex-gate usable=false reason=plugin-api lane=false`, 2026-09-29).

## Task index

1. Runner picker script
2. Route ci.yml and isolate its jobs
3. Route release.yml
4. Document the runner and the fallback

---

### Task 1: Runner picker script

**Files:**
- Create: `scripts/pick_runner.py`
- Test: `backend/tests/test_pick_runner.py`

**Interfaces:**
- Consumes: nothing.
- Produces: C1, C2.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_pick_runner.py`:

```python
"""`scripts/pick_runner.py` routes every CI job, so its one promise is tested
from each side: an idle darkmem-ci runner is used, and anything else falls back
to GitHub-hosted without failing the run."""
from __future__ import annotations

import importlib.util
import json
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF_HOSTED = '["self-hosted","linux","x64","darkmem-ci"]'
HOSTED = '"ubuntu-latest"'


def _load():
    spec = importlib.util.spec_from_file_location("pick_runner", ROOT / "scripts/pick_runner.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pick = _load()


def _runner(name="box-1", status="online", busy=False, labels=("self-hosted", "darkmem-ci")):
    return {"name": name, "status": status, "busy": busy, "labels": [{"name": n} for n in labels]}


def test_an_idle_labelled_runner_is_used():
    runs_on, reason = pick.choose([_runner()], "auto", True)
    assert runs_on == SELF_HOSTED
    assert "box-1" in reason


def test_a_busy_runner_falls_back():
    runs_on, reason = pick.choose([_runner(busy=True)], "auto", True)
    assert runs_on == HOSTED
    assert reason == "1 darkmem-ci runner(s), 1 online, none idle"


def test_an_offline_runner_falls_back():
    runs_on, reason = pick.choose([_runner(status="offline")], "auto", True)
    assert runs_on == HOSTED
    assert reason == "1 darkmem-ci runner(s), 0 online, none idle"


def test_a_runner_without_the_label_is_ignored():
    runs_on, reason = pick.choose([_runner(labels=("self-hosted", "other"))], "auto", True)
    assert runs_on == HOSTED
    assert reason == "no darkmem-ci runner registered"


def test_an_empty_listing_falls_back():
    assert pick.choose([], "auto", True) == (HOSTED, "no darkmem-ci runner registered")


def test_a_missing_token_falls_back():
    assert pick.choose([_runner()], "auto", False) == (HOSTED, "RUNNER_PICKER_TOKEN is not set")


def test_hosted_can_be_forced():
    assert pick.choose([_runner()], "hosted", True) == (HOSTED, "hosted requested")


def test_self_hosted_can_be_forced_without_a_listing():
    assert pick.choose([], "self-hosted", False) == (SELF_HOSTED, "self-hosted requested")


def test_an_unknown_request_falls_back():
    assert pick.choose([_runner()], "gpu", True) == (HOSTED, "unknown runner request 'gpu'")


def test_the_second_idle_runner_is_found_past_a_busy_one():
    runners = [_runner("box-1", busy=True), _runner("box-2")]
    runs_on, reason = pick.choose(runners, "auto", True)
    assert runs_on == SELF_HOSTED
    assert "box-2" in reason


def test_listing_follows_pages():
    first = [_runner(f"r{i}", labels=("self-hosted",)) for i in range(100)]
    pages = {1: {"total_count": 101, "runners": first}, 2: {"total_count": 101, "runners": [_runner("last")]}}
    seen = []

    def fetch(url, token):
        page = int(url.rsplit("page=", 1)[1])
        seen.append(page)
        return pages[page]

    runners = pick.list_runners("darkraise/darkmem", "t", fetch)
    assert seen == [1, 2]
    assert [r["name"] for r in runners][-1] == "last"
    assert len(runners) == 101


def _env(tmp_path, **extra):
    env = {
        "GITHUB_OUTPUT": str(tmp_path / "out"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
        "GITHUB_REPOSITORY": "darkraise/darkmem",
    }
    env.update(extra)
    return env


def _outputs(tmp_path):
    lines = (tmp_path / "out").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines)


def test_main_writes_both_outputs_for_an_idle_runner(tmp_path):
    env = _env(tmp_path, GH_TOKEN="t")
    assert pick.main(env, fetch=lambda url, token: {"total_count": 1, "runners": [_runner()]}) == 0
    out = _outputs(tmp_path)
    assert out["runs-on"] == SELF_HOSTED
    assert "box-1" in out["reason"]
    assert SELF_HOSTED in (tmp_path / "summary").read_text()


def test_main_falls_back_when_the_api_fails(tmp_path):
    def fetch(url, token):
        raise urllib.error.URLError("timed out")

    assert pick.main(_env(tmp_path, GH_TOKEN="t"), fetch=fetch) == 0
    out = _outputs(tmp_path)
    assert out["runs-on"] == HOSTED
    assert out["reason"].startswith("runner listing failed (URLError")


def test_main_falls_back_without_a_repository(tmp_path):
    env = _env(tmp_path, GH_TOKEN="t")
    del env["GITHUB_REPOSITORY"]
    assert pick.main(env, fetch=lambda url, token: {"total_count": 0, "runners": []}) == 0
    assert _outputs(tmp_path)["runs-on"] == HOSTED


def test_main_makes_no_call_when_hosted_is_forced(tmp_path):
    def fetch(url, token):
        raise AssertionError("the API must not be called")

    assert pick.main(_env(tmp_path, GH_TOKEN="t", REQUESTED="hosted"), fetch=fetch) == 0
    assert _outputs(tmp_path) == {"runs-on": HOSTED, "reason": "hosted requested"}


def test_main_keeps_a_multiline_error_on_one_output_line(tmp_path):
    def fetch(url, token):
        raise RuntimeError("line one\nline two")

    pick.main(_env(tmp_path, GH_TOKEN="t"), fetch=fetch)
    assert len((tmp_path / "out").read_text().splitlines()) == 2


def test_outputs_are_valid_json():
    for requested in ("hosted", "self-hosted"):
        runs_on, _ = pick.choose([], requested, True)
        json.loads(runs_on)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && timeout 120 .venv/bin/python -m pytest -q --noconftest tests/test_pick_runner.py -p no:cacheprovider`
Expected: collection error, `FileNotFoundError` for `scripts/pick_runner.py`.

- [ ] **Step 3: Write the picker**

Create `scripts/pick_runner.py`:

```python
#!/usr/bin/env python3
"""Pick the runner a CI run uses: an idle self-hosted `darkmem-ci` runner when
one exists, GitHub-hosted otherwise.

Every picking path answers GitHub-hosted on doubt and exits 0: the fallback
must never be the thing that fails a run. Stdlib only, so the picker job needs
no install step.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

LABEL = "darkmem-ci"
SELF_HOSTED = json.dumps(["self-hosted", "linux", "x64", LABEL], separators=(",", ":"))
HOSTED = json.dumps("ubuntu-latest")
API = "https://api.github.com"
TIMEOUT_SECONDS = 10


def choose(runners: list[dict], requested: str, token_present: bool) -> tuple[str, str]:
    if requested == "hosted":
        return HOSTED, "hosted requested"
    if requested == "self-hosted":
        return SELF_HOSTED, "self-hosted requested"
    if requested != "auto":
        return HOSTED, f"unknown runner request {requested!r}"
    if not token_present:
        return HOSTED, "RUNNER_PICKER_TOKEN is not set"
    labelled = [
        r for r in runners if any(label.get("name") == LABEL for label in r.get("labels", []))
    ]
    for runner in labelled:
        if runner.get("status") == "online" and not runner.get("busy"):
            return SELF_HOSTED, f"idle self-hosted runner {runner.get('name')}"
    if not labelled:
        return HOSTED, f"no {LABEL} runner registered"
    online = sum(1 for r in labelled if r.get("status") == "online")
    return HOSTED, f"{len(labelled)} {LABEL} runner(s), {online} online, none idle"


def _fetch(url: str, token: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response)


def list_runners(repo: str, token: str, fetch=_fetch) -> list[dict]:
    runners: list[dict] = []
    page = 1
    while True:
        body = fetch(f"{API}/repos/{repo}/actions/runners?per_page=100&page={page}", token)
        batch = body.get("runners", [])
        runners.extend(batch)
        if not batch or len(runners) >= body.get("total_count", 0):
            return runners
        page += 1


def _append(path: str | None, text: str) -> None:
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(text)


def main(env=os.environ, fetch=_fetch) -> int:
    requested = (env.get("REQUESTED") or "auto").strip()
    token = (env.get("GH_TOKEN") or "").strip()
    runners: list[dict] = []
    error = None
    if requested == "auto" and token:
        try:
            runners = list_runners(env["GITHUB_REPOSITORY"], token, fetch)
        except Exception as exc:  # any listing failure falls back to hosted
            error = f"runner listing failed ({type(exc).__name__}: {exc})"
    if error:
        runs_on, reason = HOSTED, error
    else:
        runs_on, reason = choose(runners, requested, bool(token))
    reason = " ".join(reason.split())
    _append(env.get("GITHUB_OUTPUT"), f"runs-on={runs_on}\nreason={reason}\n")
    _append(env.get("GITHUB_STEP_SUMMARY"), f"Runner: `{runs_on}` ({reason})\n")
    print(f"runs-on={runs_on} ({reason})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && timeout 120 .venv/bin/python -m pytest -q --noconftest tests/test_pick_runner.py -p no:cacheprovider`
Expected: `17 passed`.

- [ ] **Step 5: Smoke the CLI with no token**

Run: `cd /tmp && env -u GH_TOKEN GITHUB_OUTPUT=/dev/stdout GITHUB_REPOSITORY=darkraise/darkmem python3 /root/repositories/darkmem/scripts/pick_runner.py; echo "exit $?"`
Expected: output contains `runs-on="ubuntu-latest"` and `reason=RUNNER_PICKER_TOKEN is not set`, then `exit 0`.

- [ ] **Step 6: Commit**

```bash
git add scripts/pick_runner.py backend/tests/test_pick_runner.py
git commit -m "chore(ci): add the self-hosted runner picker"
```

### Task 2: Route ci.yml and isolate its jobs

**Files:**
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: C1, C3.
- Produces: C3 (the `pick-runner` job in `ci.yml`), C4.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 0 - spec 1 - coupling 1 - risk 2 = 4

- [ ] **Step 1: Add the inputs**

Replace the `on:` block's `workflow_dispatch:` and `workflow_call:` lines so the block reads:

```yaml
on:
  pull_request:
  workflow_dispatch:
    inputs:
      runner:
        description: "Where to run: auto picks an idle self-hosted darkmem-ci runner, else GitHub-hosted"
        type: choice
        options: [auto, hosted, self-hosted]
        default: auto
  # Callable so release.yml can gate publishing on this exact pipeline rather
  # than a copy of it: a release can never publish an image whose tests did not
  # run.
  workflow_call:
    inputs:
      runs-on:
        description: "A runs-on value (JSON) the caller already picked; empty picks here"
        type: string
        default: ""
```

- [ ] **Step 2: Add the `pick-runner` job**

Insert as the first job under `jobs:`:

```yaml
  # One pick per run: an idle self-hosted darkmem-ci runner, else GitHub-hosted
  # (scripts/pick_runner.py). Under release.yml the caller has already picked,
  # so its choice passes straight through.
  pick-runner:
    name: Pick runner
    runs-on: ubuntu-latest
    outputs:
      runs-on: ${{ steps.pick.outputs.runs-on }}
    steps:
      - uses: actions/checkout@v4
        if: inputs.runs-on == ''
        with:
          sparse-checkout: scripts/pick_runner.py
          sparse-checkout-cone-mode: false
      - name: Pick
        id: pick
        env:
          CALLER_PICK: ${{ inputs.runs-on }}
          REQUESTED: ${{ inputs.runner || 'auto' }}
          GH_TOKEN: ${{ secrets.RUNNER_PICKER_TOKEN }}
        run: |
          if [ -n "$CALLER_PICK" ]; then
            echo "runs-on=$CALLER_PICK" >> "$GITHUB_OUTPUT"
            echo "Runner: \`$CALLER_PICK\` (picked by the calling workflow)" >> "$GITHUB_STEP_SUMMARY"
          else
            python3 scripts/pick_runner.py
          fi
```

- [ ] **Step 3: Route the four jobs**

In each of `backend`, `frontend`, `frontend-tests` and `images`, replace `runs-on: ubuntu-latest` with these two lines:

```yaml
    needs: pick-runner
    runs-on: ${{ fromJSON(needs.pick-runner.outputs.runs-on) }}
```

- [ ] **Step 4: Give `backend` a random Postgres port**

In `backend`'s `services.postgres.ports`, replace `- 5433:5432` with `- 5432`. Delete the job-level `env:` block (the three `*_DATABASE_URL` lines and the harness comment above `BENCH_DATABASE_URL`). Directly after the `- uses: actions/checkout@v4` step, insert:

```yaml
      # The service publishes a random host port, so two jobs on one
      # self-hosted machine never collide. `job` is not available in job-level
      # env, hence GITHUB_ENV. The harness suite refuses to share a database
      # with the app tests, so it gets its own (benchlib/bench_db.py).
      - name: Point the job at its Postgres service
        env:
          PGPORT: ${{ job.services.postgres.ports['5432'] }}
        run: |
          {
            echo "PGPORT=$PGPORT"
            echo "DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:$PGPORT/darkmem"
            echo "TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:$PGPORT/darkmem_test"
            echo "BENCH_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:$PGPORT/darkmem_bench"
          } >> "$GITHUB_ENV"
```

Replace the `Create test databases` step's `run:` with:

```yaml
        run: |
          docker exec ${{ job.services.postgres.id }} psql -U darkmem -d darkmem \
            -c "CREATE DATABASE darkmem_test;" -c "CREATE DATABASE darkmem_bench;"
```

- [ ] **Step 5: Isolate the `images` job**

In `images`' `services.postgres.ports`, replace `- 5433:5432` with `- 5432`. Add a job-level `env:` block under its `runs-on:` line:

```yaml
    env:
      IMAGE: darkmem:ci-${{ github.run_id }}-${{ github.run_attempt }}
      SMOKE: darkmem-smoke-${{ github.run_id }}-${{ github.run_attempt }}
```

In the `Build image` step replace `tags: darkmem:ci` with `tags: ${{ env.IMAGE }}`.

Replace the whole `Boot the image and probe /health` step's `run:` with:

```yaml
        run: |
          # Joins the service's own network rather than the host's, so the
          # probe can only ever reach this container, never whatever else
          # listens on the runner's :8000.
          docker run -d --name "$SMOKE" \
            --network "${{ job.services.postgres.network }}" \
            -p 127.0.0.1::8000 \
            -e ENVIRONMENT=production \
            -e DB_HOST=postgres -e DB_PORT=5432 \
            -e DB_USER=darkmem -e DB_NAME=darkmem -e DB_PASSWORD=darkmem \
            -e JWT_SECRET=ci-only-secret-not-used-anywhere-else-0123456789 \
            -e COOKIE_SECURE=false \
            "$IMAGE"
          PORT=$(docker port "$SMOKE" 8000/tcp | head -n1 | sed 's/.*://')
          for i in $(seq 1 60); do
            if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
              echo "healthy after ${i}s"
              curl -fsS "http://127.0.0.1:$PORT/health"
              # The SPA ships inside this image; an API-only image is a
              # half-built artifact that /health alone would not catch.
              curl -fsS -o /dev/null -w 'index=%{http_code}\n' "http://127.0.0.1:$PORT/"
              exit 0
            fi
            sleep 1
          done
          echo "::error::image did not answer /health within 60s"
          docker logs "$SMOKE"
          exit 1
```

Replace `docker logs darkmem-smoke || true` with `docker logs "$SMOKE" || true`, and `docker rm -f darkmem-smoke || true` with `docker rm -f "$SMOKE" || true`. In the Trivy step replace `image-ref: darkmem:ci` with `image-ref: ${{ env.IMAGE }}`. Append a last step to `images`:

```yaml
      - name: Remove the image
        if: always()
        run: docker rmi "$IMAGE" || true
```

- [ ] **Step 6: Lint and check nothing fixed is left**

Run: `cd /root/repositories/darkmem && timeout 300 docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint:1.7.12 .github/workflows/ci.yml; echo "exit $?"; rg -n "5433|darkmem-smoke( |$)|darkmem:ci$|tags: darkmem:ci|image-ref: darkmem:ci|network host|ubuntu-latest" .github/workflows/ci.yml`
Expected: `exit 0` with shellcheck on (the baseline for `ci.yml` is 0 findings, so any finding is new and is fixed); the `rg` lists only `pick-runner`'s `runs-on: ubuntu-latest`.

- [ ] **Step 7: Commit, push the branch and dispatch CI**

```bash
git add .github/workflows/ci.yml
git commit -m "chore(ci): route jobs through the runner picker

Every job reads its runs-on from pick-runner. Postgres services publish
random ports, the smoke container joins the service network instead of
the host's, and image and container names carry the run id, so jobs
are safe on a shared self-hosted machine."
git push -u origin ci/self-hosted-runner-fallback
```

Pushing this branch starts no workflow (`ci.yml` has no push trigger and `release.yml` only watches master and tags); only the dispatch runs.

- [ ] **Step 8: Dispatch the run and record its id**

Run:

```bash
cd /root/repositories/darkmem
B=ci/self-hosted-runner-fallback
PREV=$(gh run list --workflow ci.yml --branch "$B" --limit 1 --json databaseId -q '.[0].databaseId // ""')
timeout 60 gh workflow run ci.yml --ref "$B" -f runner=auto
export B PREV
timeout 150 bash -c 'for i in $(seq 1 40); do RUN=$(gh run list --workflow ci.yml --branch "$B" --limit 1 --json databaseId -q ".[0].databaseId // \"\""); if [ -n "$RUN" ] && [ "$RUN" != "$PREV" ]; then echo "RUN=$RUN"; exit 0; fi; sleep 3; done; exit 1'
```

Expected: `RUN=<id>`, an id different from `PREV` (which is empty on the first dispatch). Re-run this whole step after any fix, so the watch never lands on an older run.

- [ ] **Step 9: Watch the run to its end**

Run `timeout 3000 gh run watch <RUN> --exit-status > <scratchpad>/ci-watch.log 2>&1; echo "exit $?"` as a **background** Bash call (the tool's foreground limit is 10 minutes; a run takes 15-30), wait for its completion notice, then run `gh run view <RUN> --log | rg "runs-on=|Runner:" | head -3`.

Expected: `exit 0`; the picker line shows `runs-on="ubuntu-latest"` with `RUNNER_PICKER_TOKEN is not set` (or `no darkmem-ci runner registered` if the owner has added the secret). The smoke step passing proves the service hostname assumption. A red job is fixed on this branch, committed, pushed, and Steps 8-9 re-run before Task 3; a test that connects on a literal `5433` is fixed by reading `TEST_DATABASE_URL` as `conftest.py` does.

### Task 3: Route release.yml

**Files:**
- Modify: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: C1, C3, C4.
- Produces: C3 (the `pick-runner` job in `release.yml`).

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 0 - spec 1 - coupling 1 - risk 2 = 4

- [ ] **Step 1: Add the dispatch input**

Replace the `workflow_dispatch:` line under `on:` with:

```yaml
  workflow_dispatch:
    inputs:
      runner:
        description: "Where to run: auto picks an idle self-hosted darkmem-ci runner, else GitHub-hosted"
        type: choice
        options: [auto, hosted, self-hosted]
        default: auto
```

- [ ] **Step 2: Add the `pick-runner` job**

Insert as the first job under `jobs:`:

```yaml
  # One pick for the whole release, passed into ci.yml too, so a release run
  # never picks twice (scripts/pick_runner.py).
  pick-runner:
    name: Pick runner
    runs-on: ubuntu-latest
    outputs:
      runs-on: ${{ steps.pick.outputs.runs-on }}
    steps:
      - uses: actions/checkout@v4
        with:
          sparse-checkout: scripts/pick_runner.py
          sparse-checkout-cone-mode: false
      - name: Pick
        id: pick
        env:
          REQUESTED: ${{ inputs.runner || 'auto' }}
          GH_TOKEN: ${{ secrets.RUNNER_PICKER_TOKEN }}
        run: python3 scripts/pick_runner.py
```

- [ ] **Step 3: Route the jobs**

- `plan`: add `needs: pick-runner` and replace `runs-on: ubuntu-latest` with `runs-on: ${{ fromJSON(needs.pick-runner.outputs.runs-on) }}`.
- `verify`: in the comment above it, replace the sentence beginning `Deliberately depends on NOTHING.` up to `the release decision gates the irreversible half.` with: `Depends only on pick-runner, whose picking paths always answer (a pick-runner that fails outright, say on checkout, skips the run), and never on plan: this workflow owns master pushes, so if verification were gated on plan saying "this is a release", a push of only docs/chore/refactor commits would run no tests at all -- and a plan that failed on a missing changelog section would skip the suite for a push that does ship code. Master is verified on every push; prepare below is where the release decision gates the irreversible half.` (keep the leading `  # ` on every comment line). Then add `needs: pick-runner` and, below `uses: ./.github/workflows/ci.yml`, add

  ```yaml
    with:
      runs-on: ${{ needs.pick-runner.outputs.runs-on }}
  ```

- `prepare`: `needs: [plan, verify]` becomes `needs: [pick-runner, plan, verify]`; `runs-on` as for `plan`.
- `publish`: `needs: [plan, prepare]` becomes `needs: [pick-runner, plan, prepare]`; `runs-on` as for `plan`.
- `tag`: `needs: [plan, prepare, publish]` becomes `needs: [pick-runner, plan, prepare, publish]`; `runs-on` as for `plan`.
- `github-release`: `needs: [plan, prepare, publish, tag]` becomes `needs: [pick-runner, plan, prepare, publish, tag]`; `runs-on` as for `plan`. Its `if:` line stays exactly as it is.

- [ ] **Step 4: Lint**

Run: `cd /root/repositories/darkmem && timeout 300 docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint:1.7.12 -shellcheck=; echo "exit $?"; timeout 300 docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint:1.7.12 -oneline | awk -F: '{print $1}' | sort | uniq -c; rg -n "ubuntu-latest" .github/workflows/release.yml`
Expected: `exit 0` for the structural run; the shellcheck count shows no `ci.yml` line and at most `7 .github/workflows/release.yml` (the baseline); `rg` lists only `pick-runner`'s `runs-on`.

- [ ] **Step 5: Commit and push**

```bash
git add .github/workflows/release.yml
git commit -m "chore(ci): route release jobs through the picker"
git push
```

`release.yml` runs for real only on the next master push; actionlint and the Task 2 run of the `ci.yml` it calls are its checks until then.

### Task 4: Document the runner and the fallback

**Files:**
- Modify: `docs/runbook-ci.md`
- Modify: `CLAUDE.md` (section "Build, deploy, release")

**Interfaces:**
- Consumes: C1, C3, C4.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 0 = 1

- [ ] **Step 1: Append the runbook section**

Append to `docs/runbook-ci.md`:

```markdown
## Self-hosted runner

Every CI and release run starts with a `pick-runner` job
(`scripts/pick_runner.py`). It sends the whole run to a self-hosted runner
labelled `darkmem-ci` when one is online and idle, and to GitHub-hosted
`ubuntu-latest` otherwise. A missing token, an API error or no idle runner
always means GitHub-hosted, and the run's summary page says which it picked
and why.

**Machine.** A dedicated Linux box, never this host or 192.168.0.199 (both run
production). Ubuntu 22.04 or 24.04 x64 with Docker, git, curl, python3 and the
GitHub CLI `gh` (the release job `github-release` calls `gh release create`,
after the image is pushed and the tag written, so a missing `gh` fails a
release half-way); the runner's user must be in the `docker` group. Jobs use
random host ports and per-run container and image names, so several runners
on one machine are safe. Give each runner its own OS user: `publish` logs in
to Docker Hub and GHCR, and the credentials sit in that user's
`~/.docker/config.json` until the job's post-step logs out.

**Register.** Repository Settings → Actions → Runners → New self-hosted runner;
run the printed `config.sh` with `--labels darkmem-ci`, then install it as a
service (`sudo ./svc.sh install && sudo ./svc.sh start`).

**Token.** Create a fine-grained personal access token for this repository
only, with Repository permissions → Administration: Read-only, and store it
as the Actions secret `RUNNER_PICKER_TOKEN`. `GITHUB_TOKEN` cannot list
runners, so without this secret every run is GitHub-hosted.

**Forcing a choice.** Both workflows' manual dispatch takes `runner`: `auto`
(default), `hosted` or `self-hosted`.

**A run stuck in the queue.** The pick happens once, at the start. If the
runner goes offline afterwards, the run's jobs wait for it. Cancel the run and
re-dispatch it with `runner: hosted`.

**Cost.** With one runner a run takes roughly the sum of its jobs rather than
the longest one; the saving is GitHub-hosted minutes, spent only on the short
picker job.
```

- [ ] **Step 2: Add the CLAUDE.md sentence**

In `CLAUDE.md`, directly after the paragraph that begins `- **A deploy is not a release.**` and ends `Fetch tags before deriving a version locally.`, insert:

```markdown
- **CI picks its runner per run**: `scripts/pick_runner.py` sends every job
  to an idle self-hosted runner labelled `darkmem-ci` and falls back to
  `ubuntu-latest` on any doubt (no `RUNNER_PICKER_TOKEN`, API error, none
  idle). Jobs must not use fixed host ports, container names or image tags,
  or `--network host`. Setup: `docs/runbook-ci.md`.
```

- [ ] **Step 3: Check the text landed**

Run: `rg -n "darkmem-ci" docs/runbook-ci.md CLAUDE.md | head`
Expected: hits in both files.

- [ ] **Step 4: Commit and push**

```bash
git add docs/runbook-ci.md CLAUDE.md
git commit -m "docs(ci): document the self-hosted runner"
git push
```

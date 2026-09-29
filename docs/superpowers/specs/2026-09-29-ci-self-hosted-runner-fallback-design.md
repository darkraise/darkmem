# CI: self-hosted runner when idle, GitHub-hosted otherwise

**Status:** approved in chat 2026-09-29. **Owner rulings:** the runner lives on
a separate machine (never this host or 192.168.0.199); the goal is saving
GitHub-hosted minutes, so a run goes wholly to self-hosted when a runner is
idle.

## Goal

Every CI and release job runs on a self-hosted runner labelled `darkmem-ci`
when at least one such runner is online and idle at the start of the run, and
on `ubuntu-latest` otherwise. A missing token, an API failure or no matching
runner always means GitHub-hosted: the fallback never fails a run.

Out of scope: splitting one run across both kinds of runner, autoscaling,
and registering the runner itself (an owner step, documented).

## Picker (`scripts/pick_runner.py`)

Stdlib-only Python, so the picker job needs no install step.

- `choose(runners, requested, token_present) -> (runs_on, reason)` is pure:
  - `requested == "hosted"` → hosted.
  - `requested == "self-hosted"` → self-hosted, whatever the listing says (an
    explicit operator choice).
  - `auto` without a token → hosted, reason names the missing secret.
  - `auto` → self-hosted when any runner has `status == "online"`,
    `busy == false` and a label named `darkmem-ci`, with `reason` naming the
    first such runner; else hosted, with `reason` saying how many
    `darkmem-ci` runners exist and why none qualified.
- `runs_on` is a JSON string: `["self-hosted","linux","x64","darkmem-ci"]` or
  `"ubuntu-latest"`.
- The I/O shell reads `GH_TOKEN`, `GITHUB_REPOSITORY`, `REQUESTED` (default
  `auto`); lists `GET /repos/{repo}/actions/runners?per_page=100`, following
  pages, with a 10 s timeout per request; any exception → hosted with the
  error in `reason`. It appends `runs-on=` and `reason=` to `GITHUB_OUTPUT`
  and one line to `GITHUB_STEP_SUMMARY`, and exits 0 on every path.
- The token is the `RUNNER_PICKER_TOKEN` secret: a fine-grained PAT on this
  repository only, Administration read-only. `GITHUB_TOKEN` cannot list
  runners. The repository is user-owned, so only repository runners exist.

## Workflow wiring

**`ci.yml`**

- New `workflow_dispatch` input `runner` (choice: `auto`, `hosted`,
  `self-hosted`; default `auto`) and `workflow_call` input `runs-on` (string,
  default `''`).
- New `pick-runner` job on `ubuntu-latest`, output `runs-on`. When
  `inputs.runs-on` is non-empty it echoes it through without an API call
  (release.yml already picked); otherwise it sparse-checks-out
  `scripts/pick_runner.py` and runs it with `REQUESTED=${{ inputs.runner || 'auto' }}`.
- `backend`, `frontend`, `frontend-tests` and `images` gain
  `needs: pick-runner` and
  `runs-on: ${{ fromJSON(needs.pick-runner.outputs.runs-on) }}`.

**`release.yml`**

- New `workflow_dispatch` input `runner` as above, and a `pick-runner` job.
- `verify` passes `with: runs-on: ${{ needs.pick-runner.outputs.runs-on }}`
  and gains `needs: pick-runner`.
- `plan`, `prepare`, `publish`, `tag` and `github-release` route the same way.
  Their existing `needs` lists gain `pick-runner`; their `if:` conditions are
  unchanged.

## Jobs safe on a shared Docker host

A self-hosted machine may run several runners, and a crashed job may leave
containers behind, so no job depends on a fixed host port, container name or
image tag, and none needs a host tool `ubuntu-latest` preinstalls but a plain
Ubuntu box lacks.

- **Postgres services** publish `- 5432` (a random host port). A first step
  writes `PGPORT=${{ job.services.postgres.ports[5432] }}` and the three
  database URLs to `GITHUB_ENV`; the job-level `env` block that hardcodes 5433
  goes (the `job` context is not available at job level).
- **Database creation** runs `docker exec ${{ job.services.postgres.id }} psql
  -U darkmem -d darkmem -c …` instead of host `psql`.
- **Image job**: the tag becomes `darkmem:ci-${{ github.run_id }}-${{ github.run_attempt }}`
  (build, smoke and Trivy all read it from one job-level `env` value); the
  smoke container is named the same way, runs with `-p 127.0.0.1::8000` and
  `--add-host=host.docker.internal:host-gateway`, reaches Postgres at
  `host.docker.internal:$PGPORT`, and the probe reads the published port from
  `docker port`. The cleanup step also removes the image. No step uses
  `--network host`, so the probe can never reach whatever else listens on the
  runner's `:8000`.

Behaviour on GitHub-hosted runners is unchanged apart from the random ports.

## Documentation

- `docs/runbook-ci.md` gains a "Self-hosted runner" section: machine
  requirements (Ubuntu 22.04/24.04 x64, Docker with the runner user in the
  `docker` group, git, curl), registering with the extra label `darkmem-ci`,
  creating `RUNNER_PICKER_TOKEN`, the `runner` dispatch input, and recovery
  when jobs queue on a runner that went offline after the pick (cancel,
  re-run with `runner: hosted`).
- CLAUDE.md's "Build, deploy, release" section gains one sentence naming the
  picker and its fallback.

## Known limits

- The pick happens once per run. A runner taken by another run between the
  pick and the jobs means this run queues behind it, not a failure.
- A runner that goes offline after the pick leaves the run queued until
  GitHub's queue timeout; the recovery is manual (above).
- With one runner, a run takes roughly the sum of its jobs.
- Every run spends one short hosted job on the picker (two on a release).

## Verification

1. `backend/tests/test_pick_runner.py` (beside `test_release_versioning.py`,
   loading the script by path): each `choose` branch (idle, busy, offline,
   wrong label, empty listing, missing token, each `requested` value), pages
   followed, and an API error or timeout yielding hosted with exit 0 and both
   outputs written.
2. `actionlint` over both workflows (the `rhysd/actionlint` image; the host
   has no binary).
3. Push this branch (not master, which releases) and dispatch `ci.yml` on it
   with `runner: auto`. With no runner registered and no secret, the picker
   must choose hosted with the missing-token reason and every job must pass
   on the random ports.
4. `release.yml`'s wiring runs for real only on the next master push; until
   then it is covered by actionlint and review.
5. The self-hosted path is proven only once the owner registers the machine:
   a dispatch with `runner: auto` should report the runner by name.

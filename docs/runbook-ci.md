# CI runtime

The release workflow calls `ci.yml` on every master push. Publishing still
requires the complete reusable workflow to succeed, including all matrix jobs.
No test selection is based on changed files.

Measured on release run `35755669739` before splitting the suites:

| Step | Duration |
| --- | ---: |
| Backend application tests | 604 s |
| Evaluation harness tests (after application tests) | 130 s |
| Frontend unit tests | 417 s |
| Image build, boot and scan (after both suites) | 209 s |

The optimized workflow runs these independently:

- Three backend application shards, each with its own Postgres service. The
  session fixture drops and recreates the schema, so concurrent workers must
  never share a database. `scripts/ci_pytest.py` assigns entire collected files
  by test count, preserving order within each shard. This is a count-based
  balance, not a claim that each test takes the same time. `--durations=20`
  exposes expensive tests for later tuning.
- The evaluation harness in a fourth backend job.
- Four frontend test shards using Vitest's native `--shard` option. Test
  isolation, worker caps and timeouts are unchanged.
- Frontend typecheck, lint and build once, outside the test matrix. Build runs
  Vite directly because the preceding step already ran TypeScript.
- The image build and Trivy scan on GitHub-hosted alongside the suites.
  A workflow artifact transfers the built image to the self-hosted smoke job,
  which exercises its real entrypoint, `/health` and the bundled SPA.
- API and Playwright e2e suites on self-hosted runners, each in a job
  container with a private Postgres service and disposable application stack.

Backend jobs install the lockfile fresh in each job container. Docker
installs the Python lockfile before copying package metadata, allowing the release's version
sync to reuse the dependency layer. Release serialization and publication gates
are unchanged.

Validate workflow edits with `actionlint`. The backend partitioner's behavioral
checks run with:

```sh
backend/.venv/bin/python -m unittest discover -s scripts/tests -p test_ci_pytest.py
```

Vitest sharding is documented in its [performance guide](https://vitest.dev/guide/improving-performance.html#sharding).

Splitting jobs trades extra runner setup and potentially more billed runner
minutes for shorter elapsed time. Compare the slowest shard and total workflow
runtime after deployment; runner queue time and registry uploads remain variable.

## Self-hosted runner

The default splits verification from image production:

| Jobs | Runner |
| --- | --- |
| Backend application/harness tests, frontend checks/unit tests, image boot check | `[self-hosted, linux, x64, darkmem-linux]` while one is online, else `ubuntu-latest` |
| API and Playwright e2e | Always `[self-hosted, linux, x64, darkmem-linux]` |
| Image build/scan, release planning/version sync, image publishing, tag/GitHub release | Always `ubuntu-latest` |
| Short runner-picker jobs | `ubuntu-latest` |

`pick-runner` (`scripts/pick_runner.py`) selects only the first row's runner.
The default is `fallback`: those checks go to `darkmem-linux` whenever a
runner with that label is online, queuing behind its current job when busy,
and to `ubuntu-latest` only when none is online, none is registered or the
runner listing fails. Before choosing hosted it lists the runners once more
after 20 seconds, because ephemeral runners briefly disappear between jobs.
Listing runners needs `RUNNER_PICKER_TOKEN` (below);
without it the picker cannot tell whether the runner is up, so it queues on
self-hosted exactly as an explicit `self-hosted` request would. The release
passes its choice into the
reusable CI workflow. Every master push still runs verification, including
non-release pushes. A release cannot publish until the whole reusable CI
workflow succeeds, including both e2e jobs.

**Machine.** A dedicated Ubuntu 22.04/24.04 x64 Linux box, never this host or
192.168.0.199 (both run production). Install Docker Engine, git, curl and
python3; put the runner user in the `docker` group. Frontend host jobs use
`actions/setup-node` for their toolchain. Backend jobs run in a
`python:3.12-bookworm` job container with a per-job virtualenv, because
`actions/setup-python` found no Python 3.12 build for the runners' OS.
Workflows name a toolchain's version line, never a patch: Node's major comes
from `frontend/.nvmrc` (matching the Dockerfile's `node:` line) and Python's
minor from the Dockerfile's `python:` line, with `check-latest` off, so a
runner reuses the Node build already in its tool cache and holds one per
line (`backend/tests/test_ci_workflows.py`). To share that cache across
runners on one host, give them all the same `RUNNER_TOOL_CACHE`. A moved
image tag such as `python:3.12-bookworm` leaves the previous image dangling;
the Docker prune below reclaims it. Bumping a line is a one-file change:
`.nvmrc` plus the Dockerfile's `FROM`. The
runner no longer needs `gh` or registry login credentials: publishing and
release writes happen on GitHub-hosted.

Backend jobs each get a private Docker network and Postgres service (no
published host port) with separate app and harness databases. Smoke
verification uses a per-run container name and random loopback HTTP port.
API and Playwright jobs use `python:3.12-bookworm` containers, each with its
own Docker network and Postgres service (`darkmem_e2e`, no published host
port). The harness's API ports 8321/8322 and Vite ports 3636/3637 stay inside
those containers, so multiple runners on one machine do not collide.
Playwright installs the lockfile's browser and system dependencies inside
its job container; its failure traces are retained as artifacts for 7 days.
An always-run step returns workspace/temp ownership to the runner user after
container jobs, allowing subsequent host jobs to clean the checkout.

**Models.** The runner's Docker containers must reach the LAN Ollama service.
Set Repository Settings → Secrets and variables → Actions → Variables →
`DARKMEM_OLLAMA_BASE_URL` to its OpenAI-compatible URL; the default is
`http://192.168.0.196:11434/v1`, matching the local gate. It must serve the
seeded `qwen2.5:3b` generation and `qwen3-embedding:0.6b` embedding models.
The API harness's model preflight and all-skipped exit code remain enforced:
a blocked suite fails CI instead of being ignored. Both e2e jobs always stay
self-hosted, even for a manual `runner: hosted` dispatch, because GitHub-hosted
runners cannot reach this LAN endpoint.

**Trust.** Docker access is root-equivalent; use a dedicated trusted machine
and separate OS users per runner. Firewall it off from untrusted networks:
the image smoke check publishes a random loopback port while it runs. The
repository is private, so only collaborators' code runs here. Before making
it public, remove the runner or require approval for all outside contributors'
workflow runs: a fork can name `[self-hosted, darkmem-linux]` directly.
Prune Docker resources only when all runners on that host are idle; Docker
pruning does not clear tool caches on disk.

**Register.** Repository Settings → Actions → Runners → New self-hosted runner;
run the printed `config.sh` with `--labels darkmem-linux`, then install it as a
service (`sudo ./svc.sh install && sudo ./svc.sh start`). For an existing
runner, add `darkmem-linux` through its labels settings. It must also have the
standard `self-hosted`, `linux` and `x64` labels.

**Manual choices.** Both workflows' dispatch input `runner` accepts:

- `fallback` (default, and what every pull request and master push uses):
  `darkmem-linux` while one is online, otherwise hosted.
- `self-hosted`: always queue backend/frontend/smoke checks on `darkmem-linux`.
- `hosted`: send those checks to `ubuntu-latest`.
- `auto`: use an idle `darkmem-linux` runner, otherwise fall back to hosted
  (a busy runner also falls back).

`fallback` and `auto` read the runner list through `RUNNER_PICKER_TOKEN`, a
repository secret holding a fine-grained PAT scoped to this repository with
Administration: Read-only (the runners API needs it, and the workflow's own
`GITHUB_TOKEN` cannot be granted that permission). Without the token
`fallback` queues on self-hosted and `auto` goes hosted; an API error sends
both to hosted. E2e stays self-hosted in every mode, so while the runner is
offline a run's e2e jobs (and therefore a release's publish) still wait for
it. The run summary records the selected check runner and why.

**A run stuck in the queue.** The picker decides once, when the run starts:
a runner that goes offline after that leaves the checks it was given queued.
Restore the `darkmem-linux` runner or wait for its current job. To move the
non-e2e checks to hosted, cancel and re-dispatch with `runner: hosted`; e2e
still requires the self-hosted runner. With one
runner, its jobs execute sequentially.

**Image transfer.** CI saves its hosted build as a Docker tar artifact with
1-day retention and no redundant artifact compression. The smoke job downloads
by artifact ID and loads the build's recorded image reference, so retrying
only the failed smoke job works even when `github.run_attempt` changes. Once
the artifact expires, re-run the whole workflow to rebuild it. Registry pushes
remain exclusive to the gated hosted release job.

**Cost.** Hosted minutes are spent on image builds/scans, release jobs and
short picker jobs (one per CI run, two per release). Tests and e2e use
self-hosted capacity by default. Image transfer also uses artifact storage and
network bandwidth. An account with no hosted minutes left still needs billing
restored before it can run the complete pipeline.

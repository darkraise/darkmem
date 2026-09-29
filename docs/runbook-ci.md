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
- The image build, real entrypoint smoke test and Trivy scan alongside the
  suites. The image stays local to that job until release verification passes.

Python downloads are cached against the dependency files. Docker installs the
Python lockfile before copying package metadata, allowing the release's version
sync to reuse the dependency layer. Release serialization and publication gates
are unchanged.

Validate workflow edits with `actionlint`. The backend partitioner's behavioral
checks run with:

```sh
backend/.venv/bin/python -m unittest discover -s scripts/tests -p test_ci_pytest.py
```

Vitest sharding is documented in its [performance guide](https://vitest.dev/guide/improving-performance.html#sharding).
The Python cache uses [setup-python's dependency caching](https://github.com/actions/setup-python#caching-packages-dependencies).

Splitting jobs trades extra runner setup and potentially more billed runner
minutes for shorter elapsed time. Compare the slowest shard and total workflow
runtime after deployment; runner queue time and registry uploads remain variable.

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
The picker itself runs on GitHub-hosted, so an account with no hosted minutes
left (billing or spending limit) starts no run at all, self-hosted runner or
not.

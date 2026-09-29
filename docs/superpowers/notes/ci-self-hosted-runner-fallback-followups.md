# CI self-hosted runner fallback — open follow-ups

Carried from the plan ledger before its workspace was deleted. Items the
final fix wave closed are omitted.

## Owed before the next master push

- **Task 2:** the routed `ci.yml` has never run live. Dispatch run
  36532238261 (2026-09-29) was refused for GitHub billing before any job
  started, so three things are unverified: the Postgres service answers
  as `postgres` on `job.services.postgres.network`, `ports['5432']` yields
  the host port, and no test connects on a literal 5433. Once billing is
  restored, dispatch `ci.yml` on master with `runner: hosted` before
  pushing, since a master push runs `release.yml`, which calls this
  `ci.yml`.

## Accepted limit (owner ruling 2026-09-29)

- **Task 2:** `pick-runner` itself runs on `ubuntu-latest`, so with no
  hosted minutes no job runs, self-hosted runner or not. Documented in
  `docs/runbook-ci.md` and `CLAUDE.md`; changing it needs a redesign.

## Deferred, docs

- **Task 4:** the runbook's prune advice (`docker system prune -af
  --volumes` from a timer) can race the `images` job between the smoke
  container's removal and the Trivy scan; it should say to prune only
  while the runner is idle.
- **Task 4:** the runbook lists the Trivy cache among what that prune
  clears; `docker system prune` does not touch it.

## Deferred, tests

- **Task 4:** `backend/tests/test_ci_workflows.py` misses a fixed
  `docker run -p H:C` inside a `run` script, and host networking set in
  a service's `options:` string. Nothing in the tree violates either
  today.

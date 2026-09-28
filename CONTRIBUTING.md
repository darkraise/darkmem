# Contributing to darkmem

Thanks for looking. This document covers how to get a change through, and the
few rules that are load-bearing rather than stylistic.

Start with `CLAUDE.md`. It is the business-logic contract, not a style guide:
everything from "Domain model" down describes behaviour that must hold. A
refactor that breaks one of those invariants is a behaviour change, and it needs
to be argued as one.

---

## Getting set up

```bash
git clone https://github.com/darkraise/darkmem.git
cd darkmem
docker compose -f docker-compose.dev.yml up -d      # Postgres on 127.0.0.1:5433
```

Create the test database once:

```bash
psql -h localhost -p 5433 -U darkmem -d darkmem -c "CREATE DATABASE darkmem_test;"
```

Backend:

```bash
cd backend
python -m pytest -q
```

Frontend:

```bash
cd frontend
npm ci
npm run typecheck        # tsc -b; plain tsc misses the project references
npm test                 # vitest
npm run build
```

Dev servers: `./scripts/start_dev_server.sh` runs migrations and uvicorn on
`:8000`; `cd frontend && npm run dev` serves the UI on `:3636` and proxies the
API through.

> The test harness runs `DROP SCHEMA public CASCADE` against
> `TEST_DATABASE_URL`. Never point it at a database you care about.

## The merge gate

One command decides whether a change is mergeable:

```bash
./scripts/gate.sh
```

It runs the migration assertion, the backend suite, the frontend
typecheck/test/build, the browser-extension suite, both SDK suites, the harness
suite and the extraction benchmark. It exits non-zero naming the gate that
failed. `--full` adds the retrieval evaluation, the API end-to-end suite, the
Playwright run and a port-hygiene check.

`GATE BLOCKED` (exit 2) means a missing toolchain, not a red gate.

**Run it before opening a pull request.** One caveat worth internalising:
`pyproject.toml` sets `testpaths = ["tests"]`, so a plain `pytest -q` does
**not** collect the harness tests under `scripts/benchlib/tests`. The harness
can break while the floor stays green — which is exactly why the gate exists.

## Making a change

1. Branch from `master`.
2. Write the test first where it makes sense; the repo leans heavily on tests
   that encode an invariant rather than a snapshot.
3. Run `./scripts/gate.sh`.
4. Open a PR describing **what changed and why**. If you touched anything
   `CLAUDE.md` describes, update `CLAUDE.md` in the same PR.

CI runs the same backend, frontend and image jobs on every push and pull
request. Images are published **only** on a version tag — see
[Releases](#releases).

## Commits

```
<type>(<scope>): <subject>
```

`type` is one of `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`,
`perf`. Subject in the imperative, 50 characters or fewer, no trailing period.
Body wrapped at 72 for anything non-obvious — say what changed and why, not how.

Keep commits atomic. Two concerns are two commits.

## Code style

**Comments explain WHY, never WHAT.** Good names cover what the code does. Add
a comment for a hidden constraint, a subtle invariant, a workaround for a
specific bug, or behaviour that would surprise a reader. Do not reference the
task or ticket that prompted the change — that belongs in the PR and rots in
the source.

Do not delete an existing comment unless you are deleting its code or you know
it is wrong. A comment that looks pointless often encodes a past bug.

**English only** — code, comments, docs, commits, config, errors, tests.

**Inclusive terms**: allowlist/blocklist, primary/replica, placeholder/example,
main branch.

### Frontend

**Check `darkraise-ui` before building any component.** It ships roughly 70,
including the ones people most often re-implement — segmented controls, number
inputs, switches, empty states, toasts, dialogs, combo boxes, date pickers.
List them with `ls frontend/node_modules/darkraise-ui/dist/components/` and read
the `.d.ts` beside the one you want; the props carry their own documentation.

Restyling a library component to fit is encouraged. Re-implementing one is not.
A local component written around a library gap **must record which gap**, so the
next upgrade can retire it — the cost of skipping that is not hypothetical here.

`routeTree.gen.ts` is generated. Never hand-edit it.

### Backend

A few sharp edges that have each cost real debugging time:

- **asyncpg needs explicit casts.** Any bound parameter whose type Postgres
  cannot infer must be cast — `CAST(:vec AS vector)`, `CAST(:id AS uuid)`,
  `CAST(:props AS jsonb)` — especially with variadic `ANY`, `unnest` or
  `jsonb_build_object`.
- **Never open a fresh session while the request transaction still holds locks
  on the same rows.** Commit first.
- **Entity names are lowercase on disk**, with the original casing preserved in
  `properties.display_name`.
- **Never join across embedding partitions.** Vectors from two different models
  have no defined distance between them.

## Changing the schema

**Darkmem is deployed and its data must survive every release.** A schema
change is a new Alembic revision in `backend/migrations/versions/`, chained
after the current head, that upgrades a populated database in place. Never
edit `0001_baseline.py`: its hash is pinned by a test and stamped into every
deployed database, and a boot-time guard refuses to start when they disagree.

- **Keep the chain linear.** The gate asserts exactly one head. If another
  branch added a revision first, point yours at it (`down_revision`).
- **Carry the data.** A new NOT NULL column needs a default or a backfill in
  the same revision; a renamed or retyped column moves its values; drop a
  table or column only once no released code reads it.
- **Test against data.** The suite migrates an empty schema, which proves a
  revision runs but not that it keeps rows. Run it against a restored backup
  before shipping.

## Tests

Never hardcode a value or special-case an input to make a suite pass. If a test
is itself wrong, say so and fix the test with an argument for why — do not work
around it.

The most valuable tests here encode an invariant that would otherwise drift
silently. Several are AST scans that fail the build when a constant is
redeclared or a forbidden import appears; if you are adding a rule that a
reviewer would otherwise have to remember, prefer writing it as one of those.

## Documentation

| Where | What belongs there |
| --- | --- |
| `docs/wiki/` | User-facing: introduction, quick start, deployment, usage |
| `docs/design/` | Design specifications |
| `docs/planning/` | Task plans, analyses, reviews |
| `docs/runbook-*.md` | Operator procedures |
| `CLAUDE.md` | The business-logic contract |
| `CHANGELOG.md` | What changed per release |

If your change alters user-visible behaviour, update `docs/wiki/`. If it alters
an invariant, update `CLAUDE.md`.

## Releases

Tags publish, branches do not. Pushing a tag matching `v*` runs the full CI
pipeline and, only if it passes, builds one image and pushes it to both Docker
Hub (`darkraise/darkmem`) and GHCR (`ghcr.io/darkraise/darkmem`).

Cut releases with `./scripts/release.sh v1.0.0`. It runs the full gate, syncs
the version fields, builds, deploys, and writes the tag **last** — so a tag that
exists is one whose stack came up. It never pushes; `git push origin v1.0.0` is
the separate, irreversible step that publishes.

Versions are full semver (`vN.N.N`). The script rejects anything else, because
the rolling `1.0` and `1` tags come from a semver parse and a partial version
matches none of those patterns.

Publishing needs one repository secret: `DOCKERHUB_TOKEN`, a Docker Hub access
token with Read & Write. GHCR uses the workflow's own token.

## Secrets

**Never commit a credential.** Real keys for this deployment live in
`.claude/local-credentials.md`, which is gitignored. Reference them by
environment variable; do not copy them into a tracked file, a test fixture, a
commit message or an issue.

If a key does reach a tracked file, treat it as burned and rotate it. Removing
it in a later commit does not remove it from history.

## Reporting bugs

Include what you expected, what happened, and enough to reproduce it. For a
runtime problem, `docker compose logs darkmem` and the output of
`GET /health` are usually the two most useful things you can attach.

## License

Contributions are accepted under the [Apache License 2.0](LICENSE), the same
license the project ships under.

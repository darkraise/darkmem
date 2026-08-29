# Per-repo indexing modes: fetch and index as separate, opt-in switches

Date: 2026-08-29
Status: design approved in brainstorming; not yet planned

## Problem

darkmem indexes a repository on two schedules that nobody chose, and only one
of them can be turned off.

`repo_sync` runs every 5 minutes over every repository with `auto_sync = true`
— a column that **defaults to true** — fetches, and indexes when `HEAD` moved.
`code_reconcile` runs every 15 minutes, hashes each indexed repository's
working tree, and reindexes anything whose content hash drifted. It selects
`WHERE last_indexed_commit IS NOT NULL` (`job_runners.py:115`) and **does not
read `auto_sync` at all**.

So turning auto-sync off stops the fetch-and-index loop and leaves the drift
scan running. There is no setting anywhere that stops darkmem reindexing a
working tree.

That is the wrong shape for the deployment this project actually has. darkmem
shares a checkout with other agent stacks. Those stacks commit; they also leave
half-saved files on disk between edits. And a repository may be a remote mirror
darkmem tracks but never writes to. Three different situations, one always-on
policy.

Two further defects fall out of the same design:

1. **The two loops disagree about what a change is.** `repo_sync` asks whether
   `HEAD` moved; `code_reconcile` asks whether file bytes moved. A commit that
   only reorders unchanged files satisfies one and not the other, and the two
   can index the same repository for different reasons within the same tick.

2. **Reconcile-caught work is never embedded.** `make_code_reconcile_runner`
   passes `llm=None` deliberately, so it rebuilds files, symbols and call edges
   but no embeddings. Content that only ever drifts on disk is structurally
   present in the graph and **invisible to semantic code search** until some
   later run moves `HEAD`. Nothing reports this; the repository looks indexed.

## Non-goals

- **A filesystem watcher.** Considered and rejected in brainstorming: inotify
  adds a dependency, consumes a watch per directory, and needs its own
  lifecycle inside the single uvicorn worker. Reading git's ref files costs two
  small file reads per repository per tick and the detection lag is a number the
  operator sets.
- **Migrating existing repositories.** There are zero rows in `repositories` on
  every database that exists. No mapping from `auto_sync` is written, and none
  should be invented later — the column is gone.
- **Per-repo control of the explicit doors.** Manual reindex, the push webhook,
  and the `code_reindex` MCP tool stay unconditional. They are acts, not
  policy; a switch that made an operator's own Reindex button silently do
  nothing would be a bug, not a feature.
- **Queueing or coalescing.** A repository already indexing loses the tick, as
  it does today (`claim_for_indexing`). Unchanged.

## 1. Architecture

One rule carries the whole design:

> **`HEAD` is the single source of truth for when to index. Fetching is a
> separate concern whose only job is to move `HEAD`.**

Today's two loops each answer a different question. Under this design there is
one question — *has the resolved `HEAD` sha moved away from
`last_indexed_commit`?* — and every way code can arrive converges on it:

```
  git fetch (if enabled)  ─┐
  another agent commits   ─┼─→  .git/HEAD moves  ─→  poll notices  ─→  index
  the operator commits    ─┘
```

A pull of twelve commits and a single local commit are the same event by the
time the indexer sees them. There is one code path to reason about, and no way
for two schedules to disagree about whether a repository is current.

Uncommitted work is deliberately *not* on that path. It is a widening of the
trigger, available per repository and off by default (§3).

## 2. Data model

Five columns on `repositories`, replacing `auto_sync`:

| column | type | default | meaning |
|---|---|---|---|
| `fetch_enabled` | bool | `false` | run `git fetch` + fast-forward on a schedule |
| `fetch_interval_seconds` | int | 300 | how often, floor 30 |
| `index_on_commit_enabled` | bool | `false` | poll `HEAD` and index when it moves |
| `commit_poll_seconds` | int | 60 | how often, floor 15 |
| `index_uncommitted` | bool | `false` | widen the trigger to working-tree drift |

`auto_sync` is **dropped, not aliased.** Keeping it as a synonym for one of the
new flags would recreate the present confusion — a field whose name suggests it
governs all automatic behaviour while governing one loop of two. The removal is
a breaking change to `RepoCreate`, `RepoUpdate` and `RepoResponse`, which costs
nothing at zero rows and would be expensive to undo later.

`index_uncommitted` has no interval of its own: the drift scan runs on the same
tick as the `HEAD` poll it widens, because they answer the same question about
the same repository and two intervals would let them disagree about when a
repository was last examined.

### 2.1 The schema is still one baseline

`0001_baseline.py` is regenerated in place, not appended to (CLAUDE.md,
"Migrations"). Every deployed database is dropped and recreated, then restored
through `docs/runbook-deployment.md`'s three-pass procedure, and
`admin_password_hash` plus all eight `llm_purpose_configs` rows are re-seeded —
`llm_seed.py` does not reproduce the `verification` row at the qualified judge
identity.

Measured on production 2026-08-29, the data at risk is 50 memories, 149
entities, 98 knowledge triples and 1007 events. No repositories, no documents.

`app/schema_guard.py` stamps a hash of the baseline file into the database it
migrated and refuses to start when they disagree, so a deploy that skips the
recreate fails closed rather than serving a schema it does not have.

## 3. Trigger semantics

### 3.1 `index_on_commit_enabled` — the indexer

Each due tick, for one repository:

1. Resolve `HEAD` to a sha by **reading git's own files**, not by guessing from
   mtimes:
   - Read `.git/HEAD`. If it holds a raw sha, HEAD is detached and that is the
     answer.
   - If it holds `ref: <path>`, read `.git/<path>`. A loose ref is the answer.
   - If that file does not exist, the ref is packed: fall back to
     `git rev-parse HEAD`.
2. If the resolved sha equals `last_indexed_commit`, and no index debt is
   outstanding, do nothing.
3. Otherwise run `CodePipeline.run(repo_id)` **with the LLM**, exactly as
   `repo_sync` does today.

The common case is two small file reads and no subprocess at all.

**Do not replace step 1 with an mtime check on `.git/HEAD`.** A commit on a
branch does not touch that file — it holds `ref: refs/heads/<branch>` and only
the branch's loose ref moves — so an mtime gate there would miss every ordinary
commit while looking like it worked. The first draft of this spec said exactly
that and was wrong. Reading the ref is both cheaper than a subprocess and
exact, which is why no mtime appears in this design at all.

Outstanding index debt short-circuits step 2 for the reason
`CodePipeline.run` already states: debt is work owed at the *current* sha, so
an unchanged `HEAD` must not stop it draining.

### 3.2 `fetch_enabled` — how code arrives

Each due tick, `RepoManager.pull_repo(repo)`. This is the existing function and
its local-checkout safety is unchanged and load-bearing: a repository with
`local_path` set is advanced with `git merge --ff-only`, never `reset --hard`,
and a failed pull leaves the working tree intact. darkmem must not discard a
commit another agent has not pushed.

Fetch indexes nothing. If `fetch_enabled` is on and
`index_on_commit_enabled` is off, darkmem pulls code and the graph stays where
it was until someone reindexes explicitly. That combination is legitimate —
"track the remote, index on my say-so" — and must not be second-guessed by the
loop.

### 3.3 `index_uncommitted` — the widening

When set, the same tick additionally runs `compute_working_tree_drift`. Any
`(changed, deleted)` result feeds `CodePipeline.run(..., forced_files=...)`,
which is what `code_reconcile` does today.

Two differences from today's behaviour, both deliberate:

- **It is off unless asked for.** On a shared checkout, another agent's
  half-saved file is not a change darkmem should assert into the graph.
- **It runs under the LLM-carrying indexer**, so drift-caught content is
  embedded rather than being structurally indexed and semantically invisible.
  This fixes the defect in the Problem section, and it costs embedder budget on
  work in progress — which is the second reason the default is off.

### 3.4 What each switch touches

Stated because the switches are not symmetric, and the asymmetry is the thing
an operator needs to know:

| switch | writes to your working tree | spends embedder budget |
|---|---|---|
| `fetch_enabled` | **yes** — advances the branch | no |
| `index_on_commit_enabled` | no | yes, on each new commit |
| `index_uncommitted` | no | yes, on each save |

`fetch_enabled` is the only one that modifies the checkout. On a repository
shared with another agent stack, that is the switch to think hardest about.

## 4. Job wiring

`repo_sync` keeps its key and becomes the single loop. Its cron moves to
`*/30 * * * * *` (six-field, seconds first) with `min_interval_seconds = 15`,
and per repository it evaluates the due-times above.

`code_reconcile`'s **job registration is retired**; its scan survives as §3.3
inside the one loop. `compute_working_tree_drift` and `_file_hash` stay where
they are — `reindex_files` imports the latter — so this removes a scheduler
entry, not a module.

The roster therefore goes from twenty-four registered jobs to twenty-three.
`tests/test_code_deriver.py` derives that roster from `app/main.py`'s AST, and
CLAUDE.md's list is prose that has gone stale four times before; both move in
the same change.

Due-times live in an in-process map keyed by repository id. Invariant 13 fixes
the worker count at one, so this needs no cross-process serialisation. The
accepted cost is that a restart makes every repository immediately due, giving
one burst of fetches at boot; at homelab repository counts that is not worth a
column to avoid, and a column would need writing on every tick.

## 5. Adding a repository still indexes once

`RepoManager.create` does not index today. The first index happens because
`auto_sync` defaults to true and `repo_sync` picks the repository up within
five minutes.

With the recurring switches defaulting to off, that would leave a newly added
repository at `pending` forever — adding a repository would do nothing at all,
which is worse than the behaviour being replaced.

So `create_repo` spawns one initial index through the existing
`_spawn_repo_index` path, independent of all three switches. "Opt-in" governs
*recurring* work; asking darkmem to track a repository is itself the opt-in for
indexing it once.

## 6. API surface

`RepoCreate` and `RepoUpdate` accept the five fields; `RepoResponse` serves
them. Interval floors (30s fetch, 15s poll) are enforced in the schema as
`Field(ge=...)`, so a refusal is a 422 at the door rather than a loop spinning
on a two-second interval.

`PUT /repos/{id}` already wakes the sync loop when `auto_sync` flips off→on
(`repos.py:148-154`). That nudge now keys on `fetch_enabled` or
`index_on_commit_enabled` turning on, so switching a repository on acts
immediately instead of waiting out a tick.

The generated SDKs read the live OpenAPI document and refuse to generate
against a field the contract does not serve, so `make generate` in `sdks/` runs
as part of this change.

## 7. UI

One **Indexing** group, identical in the Add Repository dialog and the repo
settings dialog, built from `darkraise-ui` components — `switch` and
`number-input`, both already in the library, neither hand-rolled.

```
Indexing
  ( ) Fetch from remote            every [  5 ] min
      Advances your working tree. Fast-forward only.
  ( ) Index on new commit          every [ 60 ] sec
      Watches HEAD. Covers commits from any source.
      [ ] Also index uncommitted changes
          Indexes saved files before they are committed.
```

Each interval input is disabled while its switch is off. "Also index
uncommitted changes" is nested under the commit switch and disabled when it is
off, because it widens that trigger rather than being a third independent one.

The copy says which switch writes to the working tree. That is the fact an
operator sharing a checkout needs, and it is not inferable from the switch name.

## 8. Testing

Behavioural, against a real git repository in `tmp_path`, following
`test_code_pipeline_union.py`'s existing fixtures:

- Each switch off means the loop does nothing for that repository — asserted
  per switch, since the present bug is exactly one loop ignoring a flag.
- `index_on_commit_enabled` indexes after a commit and does not after an
  unchanged tick.
- A commit made **without** a fetch is picked up: the local-agent case.
- `fetch_enabled` on with `index_on_commit_enabled` off leaves `HEAD` advanced
  and `last_indexed_commit` behind — the combination is legal and must not
  self-correct.
- `index_uncommitted = false` ignores a dirty tree; `true` indexes it.
- A `local_path` repository is never `reset --hard` by a fetch, and a failed
  fetch leaves the tree intact.
- Intervals are honoured: a repository is not re-examined before its interval
  elapses.
- Below-floor intervals are refused at the door with 422.
- The job roster is twenty-three and holds no `code_reconcile` entry.

## 9. Invariant exposure

- **Invariant 13 (single worker)** is relied on for the in-process due-time
  map. Raising the replica count would give each replica its own map and
  therefore N fetches per interval. The T4.10 record already states the count
  is a flagged decision; this adds one more in-process assumption to its
  inventory.
- **Invariant 15** is untouched: nothing here reaches the dream-job family from
  capture or retrieval.
- **The `code_reconcile` retirement is a roster change**, which CLAUDE.md's job
  list has gone stale on four times. The AST-derived test is what keeps it
  honest; update both.

## 10. What this does not fix

`fetch_enabled` on a repository with no reachable remote fails every interval
and logs a warning each time. `pull_repo` already returns `None` and leaves the
tree intact, so the failure is harmless, but it is noise at whatever cadence
the operator chose. Bounding it — a backoff, or disabling the switch after N
consecutive failures the way `mark_periodic_sync_failure` does today for
`auto_sync` — is deliberately out of scope here and worth its own decision.

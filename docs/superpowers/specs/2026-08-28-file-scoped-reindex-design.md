# File-scoped, commit-verified reindex on both doors

Date: 2026-08-28
Status: design revised after adversarial review; not yet planned

Revision note: the first draft of this spec was reviewed against the code and
failed on two load-bearing mechanisms. Both are fixed below, and the coalescing
queue it proposed is **cut** rather than repaired. §10 records what changed and
why, so a reader who saw the first draft does not re-derive the deleted parts.

## Problem

An agent that finishes work and commits has to wait for darkmem to notice.
Today that wait is a polling job: `repo_sync` compares `HEAD` against
`repositories.last_indexed_commit`, and `code_reconcile` hashes the working
tree every 15 minutes to catch drift that never moved `HEAD`. Until one of
those ticks, every code tool answers from a stale graph.

The agent already knows what it changed and which commit it produced. It should
be able to say so.

Three things are missing, and only three — the rest of the machinery exists:

1. **MCP has no write door into the code subsystem at all.** The ten `code_*`
   tools plus `list_repos` are all readers.
2. **No door accepts a file list.** `CodePipeline.run` has a `forced_files`
   parameter, but its only caller is `code_reconcile` and its semantics are
   wrong for this (§3).
3. **No door verifies which commit it is indexing.**

What is *not* missing: push-triggered indexing. `POST
/api/v1/repos/{id}/webhook` (`backend/app/api/routes/repos.py:292`) already
claims the repo and spawns the same background run. This design does not
replace it.

## Non-goals

- Replacing `repo_sync` or `code_reconcile`. Both remain the backstop.
- Registering repositories. A call against a path darkmem does not know is an
  error, not an invitation to create a repository row.
- Queueing requests for a busy repository. Cut in this revision; see §10.
- Per-file *retrieval* freshness. Phases are whole-batch; this changes which
  files enter a run, never how a run is ordered (§2).

## 1. Architecture

One new service module, `app/services/reindex_request.py`, holding the entry
point both doors call:

```
resolve_repo → precheck (status, work_dir exists) → canonicalise files
             → verify HEAD (read-only) → claim ─┬─ ok   → spawn run  (202)
                                                └─ held → 409 repo_busy
```

**The precheck comes before canonicalisation, not after.** Canonicalisation
walks the working tree (§6.2), which for a repository in status `cloning` may
not exist yet, and which a concurrent claimed run may be mid-`rmtree` on. Without
the precheck the door would fail inside an `rglob` — before reaching the claim
whose loss is what produces §6.3's honest `409 repo_busy`. The precheck is
advisory only; `claim_for_indexing` remains the authoritative gate, and losing
the claim after a passed precheck is still a `409 repo_busy`.

Both doors are thin: they resolve their caller's way of naming a repository
(§6), then call this one function. Neither door contains indexing logic, a
claim, or a mutating git call.

## 2. Why ordering is not part of this design

The original framing was "index my files first". The pipeline cannot honour
that observably. Phases are whole-batch: `phase_02` parses every changed file,
`phase_03` writes structure for all of them, `phase_09` (community detection)
is repo-global and commits at the end of the phase. Results become queryable
when a phase commits, not when a file is processed.

The file list earns its place for a different reason, in §3.

## 3. `union_files` — semantics, and the hash filter that makes it safe

`CodePipeline.run` gains one parameter, `union_files: list[str] | None`.

`forced_files` **replaces** the computed diff — that is `code_reconcile`'s
contract (`code_pipeline.py:470-478`) and it must not change. `union_files` is
**added** to what `phase_01_file_discovery` computed.

### 3.1 The hash filter (fixes review findings 4 and 8)

A naive union is defective in both possible orderings relative to the
dependent-caller re-trace at `code_pipeline.py:508-526`. Union *after* it and a
genuinely-changed file has its edges deleted by `phase_03` with its callers
never re-traced — the silent missing-callers staleness `index_debt.py` exists
to prevent. Union *before* it and every named file becomes a re-trace target
even when unchanged, eating the 500-file `DEPENDENT_RETRACE_CAP` and pushing
*genuine* dependents into `index_debt` as phantom debt. Unchanged named files
also stay in `self._parsed`, and `phase_12` iterates that dict
(`code_pipeline.py:1391-1395`), so they would be fully re-embedded on every
request.

Both problems have one cause: files that did not actually change. So filter
them out before the union.

**Branch order is load-bearing.** `_file_hash` returns `None` for a file that
is missing *and* for one that is merely unindexable — `not path.is_file()` is
the first thing it tests (`code_reconcile.py:61`). So a presence test must come
first, or every absent file is swallowed by the unindexable branch and §3.3's
`skipped_missing` never fires at all:

```
for each named path p:
    if not (work_dir / p).is_file():     -> skipped_missing   (§3.3, never delete)
    live = _file_hash(work_dir / p)      # code_reconcile's own function
    if live is None:                     -> skipped_unindexable
                                         #  oversized or unreadable; the pipeline
                                         #  would skip it too (`_parse_one`,
                                         #  code_pipeline.py:918-940)
    if live == CodeFile.content_hash(p): -> skipped_unchanged
    else:                                -> accepted
```

A named file with no `CodeFile` row has `content_hash` NULL, so it never
compares equal and is **accepted** — content the graph has never seen.

The hash function is `code_reconcile._file_hash`, which is documented to
produce exactly what `phase_03`'s own comparison uses
(`code_reconcile.py:16-23`) — so there is one definition of "changed" across
all three call sites, not a second one invented here.

The `accepted` set is unioned into `self._changed_files` **before**
`_find_dependent_caller_files` runs, so genuine changes get their callers
re-traced and unchanged files never enter the run at all.

**Every named file lands in exactly one of the four buckets**, and all four are
reported (§6) on every exit the run can take, the all-filtered one included. `skipped_unindexable` exists so a caller that names a file the
system can never index hears about it: silence is the one outcome this
reporting is for. It inherits a pre-existing wart — a previously-indexed file
that later grew past `MAX_FILE_SIZE` keeps serving its stale graph — which this
design does not fix and does not worsen.

**What the filter deliberately forecloses.** A named file that is unchanged on
disk but whose call edges are already missing — a stale caller, which is
exactly what `index_debt` holds — is dropped rather than re-traced. That is
correct: a caller of a *changed* named file is re-traced automatically by
`_find_dependent_caller_files`, so only pre-existing staleness is out of reach,
and repairing that is `index_debt`'s and `code_reconcile`'s job. Do not "fix"
the filter to serve it; it would reintroduce the phantom-debt failure of §3.1.

**Where it runs.** Inside `phase_01_file_discovery`, not at the door — it has
to read the working tree *after* the run's own `pull_repo`, and it needs the
claim held so the tree cannot move under it. The door therefore validates and
canonicalises paths (§6.2) but cannot know which of them survived the filter;
that outcome is reported by the run, not by the 202 (§6).

**What this costs:** one `sha256` per named file, inside a run that is already
reading those files. Bounded by the file cap in §6.3.

**The all-filtered run needs an early exit.** When every named file is
filtered out, the amended short-circuit (§3.4) has already been bypassed — it
runs before `phase_01`, where the filter lives — so the run proceeds with an
empty changed set. Phases 02-08 are near-free on an empty set, but `phase_09`
(Leiden community detection), `phase_10` (process tracing) and `phase_11`'s
repo-wide edge validation are repo-global and have no empty-set early exit, so
an admin key re-sending the same unchanged list would pay a full Leiden pass
per request. So: **after `phase_01`, if `union_files` was given and the changed,
deleted and debt-batch sets are all empty, commit `ready`, broadcast the
completion and return `up_to_date`.** Scoped to the union path deliberately — no
existing caller's behaviour changes. The broadcast is not optional decoration:
this exit is the one outcome the bucket reporting exists for, so skipping it
would make the reporting silent exactly where it is needed.

### 3.2 What the union buys

On the committed path `union_files ⊆ diff`, so the parameter changes nothing.
It earns its place where the diff cannot see:

- darkmem sharing a working tree with the agent, where a file is edited but not
  yet committed — today only the 15-minute `code_reconcile` sweep finds this;
- a force-push that orphaned `last_indexed_commit`, where the diff falls back
  to a full pass or fails outright;
- rename detection collapsing a pair the caller knows it touched — but only
  the *new* name is indexed immediately. Removing the old name stays with the
  git diff and `code_reconcile` (§3.3), so both spellings can appear in search
  for up to one reconcile tick.

### 3.3 A named file that is not on disk is skipped, never deleted

The first draft reclassified such a file into `self._deleted_files`. That is
unsafe in exactly this design's target deployment: the agent's git runs in the
same working tree, so a request landing mid-`checkout` or mid-rebase sees a
file momentarily absent and `_delete_file_data` (`code_pipeline.py:1556`) drops
its rows, edges and chunks.

Instead the file is reported as `skipped_missing` and nothing is deleted. Real deletions are already handled correctly by the git diff, which is
authoritative for committed removals, and by `code_reconcile` for uncommitted
ones. This door never removes graph rows.

### 3.4 The short-circuit must not swallow the union (fixes review finding 1)

`run()` returns `up_to_date` at `code_pipeline.py:175` when
`old_sha == new_sha and not full and forced_files is None`, releasing the claim
before `phase_01` ever executes. That condition gains `and not union_files`.

Without this the design's own headline case fails: an uncommitted edit arrives
with `HEAD == last_indexed_commit`, so the run returns `up_to_date` after
having answered 202, and the named files are never looked at.

### 3.5 `last_indexed_commit` still advances

Because the full diff still ran. This is the invariant the design is arranged
around: a partial index that stamped the repo as fully indexed at the new HEAD
would leave the unnamed changed files unindexed by anything — no error, no debt
row, no symptom — and the short-circuit would report `up_to_date` forever after.

## 4. Commit verification

The caller may pass the sha it expects darkmem to be at. Verification is
**equality of git-resolved values**: `commit` is accepted in the 7-40 hex
characters `^[0-9a-f]{7,40}$` admits, so the door resolves it
(`git rev-parse <commit>^{commit}`, after `git cat-file -e` establishes the
object exists) and compares that to `HEAD`. A mismatch is **409** naming both
shas — the caller's spelling as `expected`, the full HEAD as `actual`.

Comparing the raw strings was specified until 2026-08-28 and is wrong in one
direction that matters: a *correct* abbreviated sha never equals a 40-character
HEAD, so it refused every time, and refused as `head_mismatch`, whose client
guidance ("darkmem is at a different commit it does hold") is then false about
a repository sitting on exactly the named commit.

| Case | `reason` |
|---|---|
| HEAD ≠ requested sha (behind, ahead, or divergent) | `head_mismatch` |
| Requested sha is not an object in this repository | `unknown_commit` |
| HEAD unreadable (tree being re-cloned by a concurrent run) | `head_unreadable` |

Two refusals sit earlier in the flow and are not commit checks: a repository
whose working directory does not exist or whose status is busy is
`409 repo_unavailable` / `409 repo_busy` at the precheck, and a working-tree
walk that fails mid-`rglob` (a directory vanishing under a concurrent re-clone)
is `409 tree_unreadable` — the canonicalisation analogue of `head_unreadable`.
Note `tree_unreadable` is **near-unreachable as implemented** and is kept as a
guard rather than a live path: `canonicalise_paths` walks no tree and catches
its own per-entry errors, so the only disk touch that could raise is
`work_dir.resolve()`, which does not in non-strict mode. The precheck's real
justification is the line above it — `repo_working_dir` re-validates and raises
for a missing or blocked path, and a busy repository is owed the honest
`repo_busy`.

`commit` is optional; omitting it skips the check.

### 4.1 Verification is read-only and pre-claim (fixes review finding 2)

The first draft verified "after `pull_repo`". That is unsafe: `pull_repo` runs
`git reset --hard FETCH_HEAD` on a clone (`repo_manager.py:467`) and can
`rmtree` and re-clone the directory. Firing it from an *unclaimed* request path
resets or deletes the tree under a concurrent run's parser — today git is
mutated only inside a claimed background run.

So the door resolves HEAD with a bare `git rev-parse HEAD`: no fetch, no reset,
no network. The background run does its own `pull_repo` under the claim, exactly
as it does today.

### 4.2 The guarantee, stated honestly

**"HEAD equalled your sha when the request was accepted."** Nothing stronger.
The spawned run pulls afterwards, so a remote that advanced in between is
indexed at the newer sha — harmless, because the diff from
`last_indexed_commit` still covers the verified commit. A force-push between
check and run indexes a different tree after a 202; that is not detectable at
this door and is not claimed to be.

### 4.3 Clone repositories verify against the last-fetched HEAD

Because the door does not fetch, a clone's HEAD is whatever the last sync left.
An agent that pushed to a remote darkmem has not fetched yet gets a 409 — and
the reason is **`unknown_commit`, not `head_mismatch`**, because darkmem's clone
does not hold that object at all yet. This was stated as `head_mismatch` until
2026-08-28, when Task 4's review found the prose and the table disagreeing:
§4's table is right, and this paragraph was wrong about the commonest case.
It matters because the two reasons carry different client guidance —
`unknown_commit` on a clone is the one that means *retry after a sync*, while
`head_mismatch` means darkmem is at a different commit it does hold.
`commit` is therefore most useful in the shared-working-tree deployment this
design targets, where HEAD is already the agent's commit. Clone-repo callers
should omit `commit`, or treat `unknown_commit` as "retry after sync".

The same staleness applies to `files`, which is why non-member paths are
soft-skipped rather than refused (§6.2).

## 5. Busy repositories: 409, no queue

`claim_for_indexing` returns `False` when a run is in flight
(`BUSY_STATUSES = ("indexing", "cloning")`, `repo_manager.py:234`). This door
answers **409 `repo_busy`**, matching the existing reindex and webhook routes.
The caller retries or lets the scheduled jobs pick the work up.

The first draft queued instead. §10 records why that was cut.

**Known concurrency gap, pre-existing and out of scope:**
`make_code_reconcile_runner` (`job_runners.py:90-151`) never calls
`claim_for_indexing`, so a reconcile run can already execute concurrently with
a webhook or reindex run on the same repository, bypassing the T4.16 gate. This
design relies on the claim as the mutual-exclusion point and inherits that gap;
it does not widen it. Filed as an adjacent finding, not fixed here.

## 6. The two doors

### REST

`POST /api/v1/repos/{repo_id}/reindex-files` — **202**.

```json
{"files": ["src/a.py", "src/b.py"], "commit": "abc123", "enrich_symbols": false}
```

Response: `{"status": "indexing", "repo_id": "...", "commit": "...",
"accepted": 2}` — `accepted` counts paths that passed canonicalisation, which
is all the door can know. Whether a path survived the hash filter is decided
inside the run (§3.1), so the per-file outcome is carried by the
`repo.indexing_completed` websocket broadcast, as `union_accepted` /
`union_skipped_unchanged` / `union_skipped_missing` /
`union_skipped_unindexable` — the four buckets of §3.1, every named file in
exactly one — alongside the existing counters, and by the same four keys on
`run()`'s own return value. The keys are present only when a union was
requested, so an ordinary run's payload is unchanged and a consumer can tell
"no union" from "an empty union".

This said until 2026-08-28 that the buckets also rode the run's `repo_indexed`
event payload. That was an error in this design, not an unimplemented part of
it: `repo_indexed` is `index_debt`'s row and its payload is debt bookkeeping,
owned by a module this door does not write through.

**Both exits report through one payload builder** (`_completion_payload`), so a
consumer never branches on which exit produced the row and the all-filtered
request is not the silent case it would otherwise be. The SPA renders the
buckets rather than a zero count: a run that indexed nothing reads
`Nothing to index` over a plain-language account of the named files
(`3 already up to date · 2 not found`), informational when everything named was
merely current and a warning when a named file was missing or unindexable,
since only that second kind is the caller's to act on.

Path-addressed by id, matching `docs/api-rest-conventions.md` (202
async-accepted) and the SPA, which always holds the id.

### MCP

`code_reindex(repo_path=None, repo_name=None, files=None, commit=None)`.

An agent at commit time knows a working directory, not a UUID. The resolver
tries `repo_path` first — resolved, then matched against `Repository.local_path`
— then `repo_name`. `repositories` has a unique constraint on neither `name`
nor `local_path` (`app/models/code.py:12`), so ambiguity is real; the existing
`code_search` resolves `repo_name` with `scalar_one_or_none()`, which *raises*
`MultipleResultsFound` on duplicates (`server.py:869-874`). This resolver
returns a typed error naming the candidate ids instead.

### 6.1 Authorization: `admin` on both doors (fixes review finding 7)

The first draft used `require_auth` on REST and `capture` on MCP. Both were
wrong. `require_auth` is JWT-session-only (`app/api/auth.py:109-134`), so the
git hook the design is *for* could not call it — API keys go through
`require_scope`. And `capture` would grant index-triggering, with its embedder
spend and its `reset --hard` on clones, to every memory-writing key.

Both doors take **`admin`**: REST via `require_scope("admin")`, the same
dependency the webhook uses (`repos.py:33`), and MCP via a new `ADMIN_TOOLS`
set in `scopes.py` folded into `TOOL_SCOPES` beside `CAPTURE_TOOLS` and
`READ_TOOLS`. This matches doc 18 §5's grouping of repository control under
`admin` and makes all three trigger doors consistent.

Consequences to land with it:

- `admin` is already in `API_KEY_SCOPES` (`api_key_scopes.py:48`) and passes
  `require_tool_scope`'s closed-set check, so nothing in the vocabulary moves.
- Scopes do not imply one another by design (`api_key_scopes.py:22-24`), so an
  agent that both writes memories and triggers indexing needs a key holding
  `capture` **and** `admin`.
- CLAUDE.md's MCP section says "a key holding only `admin` reaches no MCP tool
  at all, since no tool accepts that scope". **That becomes false** and must be
  updated in the same change. Tool roster 33 → 34.
- `TOOL_SCOPES` stops being a two-set partition. The overlap guard at
  `scopes.py:85-90` must extend to all three sets pairwise.
- `tests/test_mcp_auth.py` needs more than the roster pick-up. Line 389 asserts
  `len(CAPTURE_TOOLS) + len(READ_TOOLS) == len(declared)`, which fails the
  moment a tool is classified in a third set; the `unknown` / `stale` checks at
  `:377-380` cover only the two existing sets and need a symmetric
  `ADMIN_TOOLS` clause; and
  `test_an_admin_only_key_reaches_neither_partition` (`:299-305`) stays green
  by accident — it probes only `memory_stats` and `memory_add` — while its name
  and premise become false. It should be reworked into the positive
  admin-reaches-`code_reindex` test §9 lists.
- The "33" prose in the `scopes.py` module docstring.

### 6.2 Path canonicalisation (fixes review finding 6)

`code_files` has **no** unique constraint on `(repo_id, file_path)` — the
baseline creates only the plain index `ix_code_files_repo_path`
(`0001_baseline.py:924`) — and `phase_03` looks up the existing row by exact
string match (`code_pipeline.py:781-789`). A caller spelling `./src/a.py`,
using backslashes, or differing in case on a case-insensitive mount misses the
lookup, is treated as a new file, and **inserts a duplicate `CodeFile` row and
duplicate symbols for one on-disk file**, with search returning both forever.

So path handling is a correctness requirement, not only a traversal defence.
Each entry is resolved against the working directory, then **re-derived in the
discovery spelling** — `Path.relative_to(work_dir).as_posix()`, exactly what
`_list_all_files` produces (`code_pipeline.py:1688-1701`).

**Two failure modes, two different answers.** Conflating them breaks the
motivating caller:

- **Invalid** — escapes the working directory, contains `..`, or is absolute
  and outside. This is caller error and **hard-refuses the whole request**
  with `400 invalid_files`, naming the offending entries.
- **Valid but not a member of `_list_all_files`** — the path is inside the
  repository but is not on disk, or is filtered by `IGNORED_DIRS` /
  `IGNORED_EXTENSIONS`. This is **soft-skipped** and the rest of the request
  proceeds: absent is `skipped_missing` (§3.3), filtered is
  `skipped_unindexable` (§3.1).

The soft-skip is what keeps the door usable on a clone repository. Membership
is evaluated against the **stale, last-fetched tree** (§4.3's admission applies
to `files`, not only to `commit`), so a git hook naming a newly *added* file —
the most ordinary push there is — names a path the stale clone does not have.
Hard-refusing there would reject exactly the push the door exists to announce.
The file is skipped, the run's own diff picks it up after the pull, and the
caller is told which entries were skipped.

Case and unicode variants that differ from the discovery spelling fail
membership and are soft-skipped rather than corrected — safe direction: a
guessed spelling is what inserts the duplicate row.

**Symlinks are deliberately asymmetric.** `_list_all_files` follows them
(`rglob` + `is_file()`), so the pipeline indexes an in-tree symlink pointing
outside the repository; the door's escape check resolves the link and refuses
it. Refusing something the pipeline would index is the safe direction, and is
intentional rather than an oversight.

**Cost.** As implemented, canonicalisation is per-entry `resolve()` and
`relative_to()` with no directory walk, so it is bounded by the caller's list
rather than by repository size. An earlier draft of this section specified a
membership test against `_list_all_files(work_dir)`, which would have cost a
full `rglob("*")` plus a `stat` per entry on every request; that test was not
implemented, and the spelling is pinned by re-deriving
`relative_to(work_dir).as_posix()` instead — which is what actually guarantees
the phase-03 lookup matches. One consequence rides with the change: the door itself
cannot tell a filtered path from an ordinary one, because it performs no walk.
Membership is decided at classify time instead, by discovery's own predicate
(`is_discoverable_path`, which `_list_all_files` calls), and a path that
predicate rejects is `skipped_unindexable`.

This was specified as *accepted* until 2026-08-28, on the ground that
`_diff_files` does not filter either. That ground is wrong, because the two
cases do not end the same way. A named `node_modules/foo.js` genuinely indexed
— rows, symbols, embeddings — and then `code_reconcile`'s next tick classified
that row as deleted, since its own walk goes through `_list_all_files` and
never surfaces the file, and stripped it. The next request re-indexed it. So
the bypass was not a one-off inconsistency but a per-cycle embedder spend, and
it contradicted `skipped_unindexable`'s own charter: a file the system can
never index.

### 6.3 Other input validation

- `files` capped at 1000 entries. An unbounded list is a cheap way to force a
  near-full index on a large repository.
- `commit` must match `^[0-9a-f]{7,40}$` before reaching any git call.
- Repository status `cloning` or `indexing` returns 409 `repo_busy` at the
  precheck (§1); status `error` is claimable and proceeds, matching the
  existing routes. The precheck is advisory — a repo that becomes busy between
  it and `claim_for_indexing` returns the same 409 from the claim.
- A repository whose working directory does not exist returns 409
  `repo_unavailable` at the precheck, before any tree walk.

## 7. Events journalling (fixes review finding 9)

The webhook journals `repo_webhook_received` *before* the lookup, in its own
committed session, so 404 probes and 409 conflicts from a leaked credential
leave a row (`repos.py:320-337`). These doors are the same shape — externally
triggered, key-bearing, refusal-prone — and must do the same.

`EVENT_TYPES` is a closed vocabulary and widening is taxonomy-first: land the
value before its emitter ships, as `block_embeddings_refreshed` was
(`events.py:141-143`). Add **`repo_reindex_requested`**. `repo_webhook_received`
names the wrong door and `repo_indexed` belongs to the run itself.

**Timing: journalled at the end of the door, not before the lookup.** The
webhook writes its row first and can, because it carries only `{"keyed": …}`;
this door's row carries an *outcome*, which does not exist until the door has
finished deciding. One row written last, in its own committed session, records
every computed refusal — 400, 404 and every 409 — and loses only the
unhandled-exception path. That is a smaller gap than the two-row alternative
costs in complexity.

`object_type="repository"`, `source="reindex_api"` / `"reindex_mcp"`, `actor`
and `api_key_id` stamped from the principal on both doors. The payload carries
the file count, the requested commit, and the outcome, whose vocabulary is
every terminal state of §4 and §6 — not only the happy path:

`indexing` · `head_mismatch` · `unknown_commit` · `head_unreadable` ·
`repo_busy` · `repo_unavailable` · `tree_unreadable` · `invalid_files` ·
`too_many_files` · `malformed_commit` · `not_found` · `spawn_failed` ·
`ambiguous_repo` (MCP only) · `embedder_not_configured` (MCP only — the REST
door reaches its pipeline through a dependency that cannot be absent, so this
state has no REST spelling).

**One row per request, and it carries the terminal outcome** — which means the
row cannot be written before the claim is attempted. `prepare_reindex` journals
refusals; the door journals `indexing` or `repo_busy` after the claim, through
the same writer. A row written at acceptance and never amended would say
`indexing` for a request that ended 409.

For the MCP door a request that fails repository resolution has no UUID to
stamp; `record_event`'s `object_id` is nullable, so the row is written id-less
with the caller's `repo_path` / `repo_name` in the payload.

## 8. Cost model

The hash filter (§3.1) bounds the cost of the *files*: unchanged named files
never enter the run, so `phase_12` does not re-embed them and the re-trace cap
is not consumed by them. It does **not** by itself bound the cost of the *run* —
`phase_09`'s Leiden pass, `phase_10`'s process tracing and `phase_11`'s
repo-wide validation are repo-global and run regardless of changed-set size.
That is what §3.1's all-filtered early exit is for: without it, an admin key
re-sending one unchanged file would buy a full Leiden pass per request.

What a request costs when files genuinely changed is one ordinary incremental
run — the same cost the webhook already carries.

Neither door is rate-limited. The `admin` scope in §6.1 is the mitigation: the
population that can spend this is the one that can already trigger the webhook.
A per-repository cooldown is deliberately not designed in; if abuse shows up it
is a follow-up, and the 409 `repo_busy` already serialises the expensive part.

## 9. Testing

Against the invariants, not the happy path:

- `HEAD == last_indexed_commit` plus a named changed file **indexes it** — the
  short-circuit does not fire (§3.4). This is the regression test for the
  defect that failed the first draft.
- A named file whose hash matches the indexed hash never enters `_changed_files`
  and never reaches `phase_12`; the run reports it under
  `union_skipped_unchanged`.
- A named file whose hash differs is unioned *before* the dependent re-trace,
  and its callers are re-traced.
- A named file absent from disk is reported under `union_skipped_missing` and
  no graph rows are deleted.
- `last_indexed_commit` advances, and the changed set is diff ∪ filtered-named,
  never just named.
- `forced_files` semantics unchanged; `code_reconcile`'s existing tests stay
  green with no edit.
- The door performs no mutating git call: a HEAD check against a repository
  whose claim is held leaves the working tree byte-identical.
- A HEAD mismatch refuses before `claim_for_indexing`, so a refused request
  never leaves a repository claimed.
- Path canonicalisation: `./src/a.py`, `src/../src/a.py` and a backslash
  spelling all resolve to the one discovery spelling or are refused — and in no
  case produce a second `CodeFile` row for one on-disk file.
- `..` traversal, an absolute path outside the repo, and an over-cap list are
  each refused at the door.
- Both doors journal `repo_reindex_requested` on success **and** on 404/409,
  with `api_key_id` set for keyed calls.
- A `capture`-only key is refused by the MCP tool; an `admin`-only key is
  accepted. The three-set `TOOL_SCOPES` overlap guard fails the build on a tool
  declared in two sets, and `test_mcp_auth.py:389`'s two-set arithmetic is
  rewritten rather than left to fail.
- **Branch order (§3.1):** a named file that is absent from disk lands in
  `skipped_missing` specifically — not merely "is skipped". Asserting only that
  it does not crash would pass against the defect this test exists for.
- A present-but-oversized named file lands in `skipped_unindexable`, and the
  caller is told.
- An all-filtered request takes the early exit: no Leiden pass runs, the claim
  is released, and the repository ends `ready`.
- `head_unreadable` and `tree_unreadable` are each produced rather than
  surfacing as a 500.
- A repository in status `cloning` returns `409 repo_busy` from the precheck,
  not an `rglob` failure.
- On a clone whose tree is stale, a named file absent from that tree is
  soft-skipped and the request still proceeds; an escaping or `..` path
  hard-refuses the whole request with `400 invalid_files`.

## 10. What the reviews changed

Two adversarial review rounds against the code, both 2026-08-28.

### Round 1 — the first draft

Seven must-fixes; all citations in the draft verified, but two mechanisms
failed:

| # | Finding | Resolution |
|---|---|---|
| 1 | `run()`'s short-circuit swallowed the union and every drain | §3.4 amends the condition |
| 2 | Verification ran `pull_repo` from an unclaimed path, mutating a tree a concurrent run was walking | §4.1 makes it read-only and pre-claim |
| 3 | Coalescing store had no concurrency control, incoherent `cycles`, and no consumer | **Cut** — see below |
| 4 | Dependent re-trace ordering defective in both directions | §3.1 hash filter |
| 5 | Deleted-file reclassification could drop rows for a transiently-absent file | §3.3 skips, never deletes |
| 6 | Caller path spelling could insert duplicate `CodeFile` rows | §6.2 canonicalises to the discovery spelling |
| 7 | `require_auth` unreachable by the motivating git hook; scope bar inconsistent | §6.1 `admin` on both doors |
| 8 | `phase_12` re-embedded every unchanged named file | Solved by §3.1 |
| 9 | No events journalling | §7, `repo_reindex_requested` taxonomy-first |
| 10 | Queued path invisible on every surface | Mostly moot with the queue cut; the surviving half is the four run-reported buckets (§6) and `cloning` → 409 (§6.3) |
| 11 | Draft said "eleven `code_*` tools" | Ten; corrected |
| 12 | Invariant 13/15 exposure | §11 |

### Round 2 — this revision

Round 1's twelve findings all verified addressed, and the coalescing cut
verified clean (no orphaned reference to the pending row, the cycles cap, the
drain loop or a "queued" 202 anywhere in the document). Three new must-fixes,
all in mechanisms the first review had never seen, all paragraph-level:

| # | Finding | Resolution |
|---|---|---|
| N1 | §3.1's branch order made §3.3's `skipped_missing` unreachable — `_file_hash` returns `None` for a missing file first (`code_reconcile.py:61`), so the unindexable branch swallowed every absent file | Presence test moved ahead of the hash; four explicit buckets (§3.1) |
| N2 | §1's flow canonicalised before the precheck, so a `cloning` repo failed inside an `rglob` instead of returning §6.3's `409 repo_busy` | Precheck moved first; `repo_unavailable` and `tree_unreadable` added (§1, §4) |
| N3 | Refuse-versus-skip was asserted both ways, and hard-refusing broke clone-repo hooks on file-adding pushes | Invalid → `400`, valid-but-absent → soft-skip (§6.2); §4.3's stale-tree admission extended to `files` |
| N4 | §7 required journalling before the lookup *and* an outcome in the payload | One row at the end of the door; full outcome vocabulary (§7) |
| N5 | A present-but-unindexable file had no reporting bucket | `skipped_unindexable` (§3.1) |
| N6 | An all-filtered request still bought a repo-global Leiden pass | Early exit after `phase_01`, scoped to the union path (§3.1, §8) |
| N7 | The filter forecloses stale-caller repair; §3.2's rename bullet overclaimed | Both stated explicitly (§3.1, §3.2) |
| N8 | §6.1 understated the `test_mcp_auth.py` changes | Enumerated (§6.1) |
| N9, N10 | Symlink asymmetry and the `rglob` cost were unstated | Both stated (§6.2) |
| N13 | Test list did not cover the new mechanisms' edges | Eight bullets added (§9) |

**Why coalescing was cut rather than repaired.** A `config` row has no locking
(`JobRegistry` protects its `job:*` rows with a per-job asyncio lock; nothing
protects an arbitrary key), so two doors merging into one pending row is a
lost update across awaits even under invariant 13. The `cycles` cap bounded
nothing if a new request reset it and wedged permanently if it did not, because
the designated fallback was false: neither `repo_sync` (`job_runners.py:22-88`,
which calls `pipeline.run(repo.id)` bare and bypasses `_spawn_repo_index`
entirely) nor `code_reconcile` (`job_runners.py:90-151`, which derives its own
drift) would ever have read the row. Repairing it means designing a real
per-repository work queue with its own locking and end-of-life — a larger piece
of work than the door itself, and one that should be its own design once the
door exists and the 409 rate is measurable rather than assumed.

## 11. Invariant exposure

Low, with one stated dependency. The reachability scans match specific
forbidden modules (the dream-job family, `verification_ladder` / `ladder_config`,
`auto_research`, `contradiction_veto`) by import, attribute and string literal;
`reindex_request.py` importing `code_pipeline` and `repo_manager` names none of
them, and the RRF scan checks constant *declarations*, which this adds none of.

Two cautions:

- The new modules must not name the ladder or research modules **even in
  prose** — the literal route matches non-docstring string constants.
- Nothing here adds an in-process lock. If a future revision reintroduces
  queueing and reaches for an `asyncio.Lock`, that is correct only under
  invariant 13 and must be recorded in the T4.10 replica record
  (`docs/planning/analyses/2026-08-16-t4.10-replica-decision.md`) as one more
  in-process assumption.

## 12. Adjacent findings, not fixed here

Surfaced by the review, outside this design's scope:

- `make_code_reconcile_runner` never calls `claim_for_indexing`
  (`job_runners.py:90-151`) — reconcile can run concurrently with any other
  indexing run on the same repository, bypassing the T4.16 gate every other
  caller uses.
- `create_repo` catches `IntegrityError` to return 409 on a duplicate name
  (`repos.py:74-76`), but `repositories` has no unique constraint on `name`
  (`0001_baseline.py:880-898`). The handler is dead and duplicate names are
  freely creatable — which is the ambiguity §6's MCP resolver then has to
  paper over.

# Audit follow-ups — design

**Execution strategy:** sequential — inline execution
**Depth:** full — risk

Rule on, and resolve, the 148 rows that the 2026-11-20 audit-remaining plan
left open in `docs/dforge/registers/2026-11-20-audit-remaining.md` (rows
237-390): the minor findings its task reviewers recorded and the items its
tasks discovered. This spec does not restate the findings. Each row was
re-read against the code at `77f2f912` on 2026-11-23 by five read-only judge
seats; their reports (`.dforge/row-check/lane-{a,b1,b2,c,d}-report.md`) hold,
per row, the evidence, what it breaks, the smallest fix and the test it
earns. The spec says how the rows were ruled, where a design choice was
made, what is declined, and how the result is accepted.

## Decisions

- **Request.** Owner, 2026-11-23: "Rule on the open rows with
  dforge:brainstorming." No question was asked before this spec was
  written; the choices that are the owner's are the `Q:` lines under
  Acceptance and the questions of the spec review.
- **Standard (inherited).** Owner, 2026-11-20: "resolve all remaining
  items". A row that still holds is fixed unless its fix is a redesign or a
  wire change out of proportion to what it breaks; those are declined below,
  each with its reason on its register row.
- **Approaches considered (my call).** (1) Do less: fix the two Important
  findings and defer the other 94 rows that hold. (2) Fix every row that
  holds and whose fix the row check sized under about 50 lines, design the
  one Important finding that needs a choice, decline the redesigns. (3) Fix
  everything, redesigns included. Taken: (2). It is the owner's standard
  applied to rows that are each small, and (1) would leave the register
  with the same 94 rows to rule on again.
- **The verdicts.** Of 148 rows: 96 hold, 22 are gone (a later task of the
  same plan already fixed them), 16 restate another row, 9 record a past
  event with nothing in the tree to change, 2 were never true of this code,
  and 3 could not be told without a run. Row 387 was settled by reads on
  2026-11-23 (production holds 1 repository, 0 `code_files` and 0
  `code_edges`; the disk under the dev Postgres is at 82%); rows 269 and 351
  need a test run and start their task with it.
- **Closed without a change (55 rows, already set in the register).** The
  22 gone, 16 duplicate, 9 record-only and 2 wrong rows are `done` with the
  seat's evidence as their Note. Row 387 is `done` with the reads above, and
  row 384 (an EXPLAIN nobody recorded) against the test that pins the index
  use. Rows 303, 337, 357 and 373 are `deferred` as "no work owed". With
  the 5 declined below, that leaves 88 of the 148 to fix.
- **Declined (my call, 5 rows, each `deferred` with its reason).** 268 (a
  flush cut at shutdown repeats one extraction per row; reusing the work
  needs the extraction result stored on the buffer row), 273 (telling a sent
  importance of 0.5 from an omitted one means carrying "not sent" through
  the buffer replay and the MCP tool's signature, for a caller nobody has
  reported), 312 (accepted: a citation's badge stays fresh wrongly only
  after one owner swaps a method for a property of the same name; storing
  the node kind on new citations is left until one is seen), 362 (island
  separation at hundreds of islands is a layout design of its own), 369 (a
  rotation waits at most the 5 s send timeout per stalled socket; removing
  the wait is a socket-layer redesign). Row 380 is fixed in part: its second
  half, the Code Graph pane widths at 1280x800, is declined as new row 411.
- **Adjacent findings.** The seats reported 24 hazards no row recorded.
  Nineteen are the 18 new open rows 392-408 and 412, fixed here with the
  package that touches the same code (row 406 holds two); two are rows 409
  and 410, `deferred` as no work owed; three are part of rows 355 and 286
  and are fixed with them. That makes 106 open rows: 88 and 18.
- **Phase 5 deadlock (my call).** Rows 254 and 258 are one finding, and it
  is real: the strip of a memory's prior graph rows takes its locks before
  the sorted upserts take theirs, so two writers can each hold a row the
  other wants (seat trace in `lane-b1-report.md`, row 254). Row 258's own
  remedy (order the strip by id) does not close that cycle. Two fixes do:
  retry savepoint B when Postgres aborts it as a deadlock, or lock the prior
  and the new rows together in one global order. Taken: the retry. It is
  about 20 lines against 50 or more, it needs no lock on keys that do not
  exist yet, and it keeps the strip and the write one atomic replace, which
  `CLAUDE.md` states as contract. Its cost is that a deadlock is still paid
  for with Postgres's one-second detection wait before the retry.
- **Tie-breaks (my call).** Row 355 is fixed once in `rrf_fuse`, so every
  RRF consumer gets it, and in each arm. The semantic arm is sorted in
  Python after the fetch, because a second `ORDER BY` key would stop pgvector
  using the HNSW index. Tied rows change rank, and under RRF a changed rank
  changes a fused score, so the retrieval eval's numbers can move. The eval
  cannot run on this checkout (its cache and key were lost with the
  re-clone, register row 228); the re-run is owed and is register row 413.
- **Board edits (my call).** Row 315 offers two ways to carry vectors across
  a register edit. Taken: carry with no orchestrator, under every
  non-retired fingerprint whose partition holds vectors for the document
  (the newest alone may not be the one search reads), so the rule that a
  board edit never waits on an embedder still holds.
- **Session revocations (my call).** Row 331: the in-process copy is
  re-read from the database when it is older than 60 seconds, the interval
  the security review itself proposed. The socket loop calls an async,
  single-flight `refresh_if_stale()`, so the cost is one query a minute for
  the whole process however many sockets are open; a reload merges into the
  copy and never replaces it, and a failed read keeps the copy and logs
  once.
- **Inject log (my call).** Row 405: production's journal holds no `inject`
  or `inject_curbed` event (read 2026-11-23) and nothing writes one, so the
  Distribution tab's inject log is removed, as the 2026-11-20 ruling removed
  the controls that steered nothing. The Activity tab keeps its rendering of
  inject events: only this host's journal was read.
- **Leave guard (my call).** Row 376 is fixed for both ways of leaving: the
  browser's own prompt on close or reload, and a dialog on navigation inside
  the app. The dialog opens only for a refused write or one queued behind
  it: a write that is merely in flight still lands after navigation, because
  the write queue outlives the editor (Fable ruling). The router's blocker has no precedent in this repository; the
  row's loss is most often reached by clicking another document.
- **Declared context (row 342).** Owner, at the spec review: "Remove
  (Recommended)". The wire surface and the SDK verb go; it is a breaking
  change for SDK callers.
- **Deploy.** Owner, at the spec review: "Once, after the follow-ups". The
  2026-11-20 plan's after-merge sequence runs once, after this plan merges.
- **State boards.** Owner, at the spec review: "No new board
  (Recommended)". The
  Backups failed state is added to the existing
  `frontend/src/components/app-chrome/load-failure-states.stories.tsx`, and
  the failed-captures pending state to
  `frontend/src/features/activity/components/failed-captures-section.stories.tsx`.
- **Early CI.** Owner, at the spec review: "No early run (Recommended)".

Early CI: none

Finish: merge

Worktree: in-place

- **Row ownership.** A row is closed by the package that lists it. Rows 255,
  246 and 300 are tests only: the code they guard is right today.

## Rules for every work package

1. **Verify first.** Each task starts by reproducing its row with a failing
   test, or with a command where no test can. A row that does not reproduce
   is closed `done` with the note `not reproduced:` and the evidence, and
   nothing is changed for it.
2. **The seat's fix is the default.** Where this spec names no departure,
   the fix is the one in the row's entry of its lane report.
3. **Contract sentences move with the code.** A change to behaviour that
   `CLAUDE.md` or `docs/two-door-parity.md` states is corrected in place in
   the same commit.
4. **No schema change.** No package adds a revision. A task that finds it
   needs one stops and says so.
5. **Doors.** No route or MCP tool is added. WP11 removes a request field, a
   header and an SDK verb; then the guards leg in
   `CLAUDE.md` runs, `make generate` runs in `sdks/`, and the two prose
   counts are re-read.
6. **No removal without proof.** A module, export or helper is removed only
   after a search shows no importer outside its own tests.
7. **Host limits.** Backend suites run on a lane database, never
   `darkmem_test` from a lane and never production; `free -h` is read before
   a red leg is believed. `scripts/backup.sh` runs against production from
   this checkout at 03:30, so it is edited and tested in one sitting or in a
   worktree, never left half-done overnight.

## Work packages

Row numbers are register rows. "Tests only" means the code is right and the
row asks for a guard.

**WP1 — Phase 5 deadlock** (254, 255, 256, 398). In
`ProcessingPipeline`'s per-memory write, a savepoint B that fails with
SQLSTATE `40P01` is run again, strip included, up to three attempts in all;
the rollback to the savepoint has already released its locks. Any other
error, and a third deadlock, end as today: `graph=error`, savepoint A kept,
with `40P01` in the status error. Each retried deadlock logs one warning
naming the memory and the attempt; the SQLSTATE is read the way
`fact_lift.py` reads `_LOCK_NOT_AVAILABLE`, not from message text.
`pipeline.delete_memory` (398) runs its strip in a savepoint under the same
retry instead of swallowing a deadlock (the two cautions in the Fable
ruling on this decision, on the expired `mem_record` and on locks taken in
savepoint A, bind this task), and runs the fact-source withdrawal
in a second savepoint after it, so a lock timeout there (WP6, row 288)
loses only the withdrawal, which the hourly reap heals, and never the
strip. A delete that exhausts its retries logs the SQLSTATE and is healed by
`graph_orphan_cleanup`. Tests: the two-session swapped-set
case of row 254, the relation sort (255), and row 256's timeout shortened.
`CLAUDE.md`'s Phase 5 paragraph gains the retry sentence.

**WP2 — Deterministic ranking and the embed outage** (355, 276, 400, 279).
`rrf_fuse` and `apply_rank_fusion_factor` order equal scores by row key; the
keyword arm adds `m.id` to its `ORDER BY`; the semantic arm, the inert
dual-level channel and the hybrid-off branch (which reads
`PostgresVectorRepository.search` directly) sort fetched rows by
`(-score, id)`. A rerank's order is kept as it is
(`preserve_order`). With hybrid search off, the branch embeds through
`embed_query`, which is what starts the cooldown, and raises on a failed
embed without dialling again (276, 400). `get_memory_context` applies its limit of 20
after the scope filter, in SQL (279).

**WP3 — Capture and wait_process** (259, 260, 261, 262, 263, 264, 267, 269,
275, 285, 399). The unreachable `extraction_partial` branch goes; the SPA
keeps its label for stored rows (259). When the same-batch reconciliation
raises, the batch's `extracted` journal rows are written from a fresh
session, guarded (260). With no pipeline factory, an inline flush uses the
app's session factory, so it never outlives its request on the request's
session (261, 262). A raising inline flush is logged once and answers the
plain ack (264). An inline flush of one row cut at its own deadline charges that row an
attempt, as the scheduled lone-row path does; a flush of several rows, and
any cut at shutdown, still refund (399), and `CLAUDE.md`'s "either way ...
returned to `pending`" sentence moves with it.
A stream closed early records `ok=False` (275). Row 267 rewords the cap's
comment, and `CLAUDE.md`'s "While eight such flushes are running", to what
the cap counts. Row 269 starts by locating the SAWarning with
`-W error::sqlalchemy.exc.SAWarning`. Row 285 deep-copies the shared
extraction fixture.

**WP4 — Sessions, sockets and the call log** (237, 238, 241, 242, 331, 368,
370, 371, 392, 393, 394, 397). The login limiter says which gate refused: an
in-flight refusal reads "Too many login attempts in progress; retry in Ns"
(237). `session_revocations` re-reads the database when its copy is older
than 60 seconds, as Decisions says (331); `CLAUDE.md`'s "an idle socket
costs no query" sentence and the class docstring's "only writers" claim
move with it. The refresh and change-password routes forget the
renewed mark when cancelled while closing sockets (371).
`PASSWORD_CHANGED_AT_KEY` has one definition (394). The MCP call log puts a
batch back on a pool timeout and on cancellation (392, 393). Test rows: 238
with 397, 241, 242, 368, 370.

**WP5 — Repositories and code indexing** (244, 245, 246, 300, 301, 302, 304,
308, 401, 404). Every failure-path log line in `code_pipeline.py` passes
through `_sanitize_url` (244). The git auth header is scoped to the
repository's origin, `http.<scheme>://<host>[:<port>]/.extraHeader`, built
from the URL with its userinfo removed and its port kept when it names
one, so a git-lfs or submodule fetch to another host carries no token
(245). A re-clone that raises leaves the
repository `error` with a sanitised message; a cancelled one restores the
prior status; both release the claim (300, 301). The deriver's state stamp
carries a `CODE_DERIVER_VERSION`, so a changed derivation re-derives a
repository whose HEAD has not moved (304; a state row with no version
reads as stale, so each repository re-derives once after the deploy); the
code lift's stamp reads that
state, not the newest job-run id, so an idle hour reconciles nothing, the
state key leaves with its repository, and the enrichment snapshot is one
read (308). The phase 09-10 skip digest covers each function's rank by
`line_start` within its file, not the raw line, so an added comment line
does not end the skip (401). Tests
only: 246, 404. Row 302 is a comment.

**WP6 — Fact vault, refine and benches** (286, 288, 289, 291, 294, 295, 296,
297, 298, 412).
`_open_fact_id` takes its lock `NOWAIT` inside the same retry-until-deadline
loop as `_share_lock_memories` and defers the candidate at the deadline
(286). `withdraw_memory_sources` runs under the same `lock_timeout` pair as
`reconcile_memory_sources`, through one shared helper (288). The benchlib
conftest refuses to run under pytest-xdist and names the serial command
(297): the bench database is one fixture set loaded once, and the gate and
CI both run this suite serially. The refine prompt no longer shows the memory's current tags, which
went in unfenced and whose output has been discarded since `bb80816`
(296). Rows 289, 291, 294, 295, 298 and 412 are prose and script nits.

**WP7 — Documents, pages and test isolation** (315, 316, 317, 319, 320, 321,
322, 323, 324, 325, 327, 328, 329, 345, 346, 347, 348, 351, 352, 353, 354,
402, 403). A filing with `embed_inline=False` carries unchanged blocks'
vectors under every non-retired fingerprint that holds vectors for the
document, with no embed call (315); `CLAUDE.md`'s `embed_inline=False`
sentence says so. A block verb on a document runs the filing's revision
prune, by the same 50-and-90-day rule and the same count-only journal row,
so a converted document's old revisions age out (324). An
upload whose `.part` the cleanup collected answers 408 with the envelope
code `request_timeout` (319). The import's
withdrawal guards its own rollback (321). `create_page` runs its second
parse off the event loop (325). `store_upload` is removed (317, rule 6).
`SEMANTIC_ARM_OWNER` and its trace field are removed; if the field is in the
OpenAPI document, rule 5's legs run (345, 347). The session-scope scan fails
on a route that builds a `StreamingResponse` without declaring it, and
states what its floor guards (327, 328). Row 351 starts by finding which of
the seven files named in `lane-c-report.md` leaves a committed entity; that
file cleans up, and `test_repo_entity_merge` asserts only its seeded names
(403). The rest are tests, docstrings and one clause on the
`documents.write` parity row (316, 320, 322, 323, 329, 346, 348, 352, 353,
354, 402).

**WP8 — Scripts and CI** (247, 250, 251, 252, 372, 377, 378, 379, 395,
396). The e2e reset refuses every loopback and unspecified address on port
5432, parsed with `ipaddress` (250); its database defaults to
`darkmem_e2e`, `gate.sh`'s and `release.sh`'s e2e legs name it, `CLAUDE.md`'s
database list and the e2e README gain it with its one-time `CREATE
DATABASE`, and the BLOCKED message names `DARKMEM_OLLAMA_BASE_URL` (372); its `alembic` subprocess has a 600 s timeout (395). `backup.sh` keeps
the newest three `.suspect` dumps (377). `restore-cycle.sh` bounds its image
probe (120 s) and its replay and migrate (3600 s each, each overridable by
an environment variable; the worker's real cycle time is Unknown here and
its journal settles it). The bound wraps the compose command, and exit 124
is tested before the baseline-hash comparison, so a timeout swaps nothing
and exits non-zero (378). The cluster-layout budget test asserts a
500 ms ceiling and logs the measured time, so it holds while the host swaps
(247). Rows 251, 252, 379 and 396 are nits.

**WP9 — Operator screens** (249, 330, 356, 366, 376, 380, 381, 382, 388,
389, 390, 405, 406, 407). The UI/UX contract below. Row 381 also names axe
findings nobody could check without a run: its task starts by running axe
on the review queue, and each finding that holds is fixed or split into a
row of its own.

**WP10 — Frontend hygiene** (343, 359, 363, 365, 374, 375, 408). Search and
paginated POST queries pass their abort signal (374). The code canvas mirror
writes into reused arrays (363). `portal-overlays.ts` and the invalidations
and query key nothing reads are removed (365, 375, 408, rule 6). The
Storybook preview gets an index route (359). Row 343 rewords four comments.

**WP11 — Declared context** (342). The `context` request field, `X-Darkmem-Context`, the envelope
echo, `context_resolution.py`, the SDK `declareContext` verb and the demo
chip go, with their tests and the two design documents that describe them.
Rule 5's legs run: the guards leg, `make generate` in `sdks/`, and the two
prose counts.

**WP12 — Close.** The gate legs (`bash .dforge/gate-legs.sh`), the UI proof,
and the register check. The deploy sequence the 2026-11-20 plan left for
after its merge has not run: production on this host still runs the image
built 2026-11-20 15:09 +07, and row 215 (requeue the 53 failed captures)
waits on it. It runs once, after this plan merges, in that plan's order
(owner, at the spec review).

## CI

`.github/workflows/ci.yml` (also `release.yml`, `cache-cleanup.yml`;
`workflow_dispatch` is declared). Jobs: `pick-runner` and `images` on
`ubuntu-latest`; `backend`, `frontend`, `frontend-tests` and `clients` on the
picked runner; `e2e` on `darkmem-linux`. This host runs GNU coreutils 9.7, so
`uutils (ubuntu-latest)` is uncovered; WP8's two shell scripts use `timeout`,
which on uutils signals only the command it started. Local commands:
`bash .dforge/gate-legs.sh` and the legs `CLAUDE.md` lists. Pushing `master`
releases; an early CI run would push a branch only.

## UI/UX contract

**UI/UX depth:** feature — changed states and one new leave flow on existing Settings, Activity, document, chat, knowledge and code screens

### UI

- **UI-1** — Settings → Backups: a failed read of destinations, inventory or
  outcomes shows the library `empty-state` in its failed kind with a Retry
  button; an empty inventory appears only after a successful read.
- **UI-2** — Settings → LLM shows a banner while `/health` reports
  `pipeline_state: failed_at_boot`: "Processing is stopped: the model setup
  failed at startup. Captures are still queued. Save a working model
  configuration to start it."
- **UI-3** — Dark theme: a disabled button is visibly dimmer than an enabled
  one. `frontend/src/styles/globals.css` sets `--disabled-opacity: 0.38`
  for the dark mode, with a comment naming the library gap (no dark value).
  The token is global: disabled inputs and selects dim with it and must
  stay readable.
- **UI-4** — The Copy Mermaid trigger keeps its own width at the end of its
  row in the Mermaid dialog.
- **UI-5** — The review queue's fact row puts no block element inside a
  paragraph. A chat conversation row is a container holding two sibling
  buttons, select and Delete; neither is nested in the other.
- **UI-6** — Settings → Distribution has no inject log.

### UX

- **UX-1** — Provider dialog. With a stored key shown masked, editing the
  base URL or the API kind disables Save and shows, under the key field,
  "The address or API kind changed. Enter the API key again." Typing a key
  enables Save. No request is sent while Save is disabled.
- **UX-2** — Failed captures. While a Requeue or a Discard for a row runs,
  both of that row's buttons are disabled; they return when it settles.
- **UX-3** — Document block editor. Opening a block puts the caret at the
  end of its text.
- **UX-4** — Document leave guard. While a block write is held (saving,
  refused, or queued behind one), closing or reloading the tab raises the
  browser's leave prompt. While a write is refused, or queued behind a
  refused one, navigating inside the app opens a dialog:
  title "Leave without saving?", body "This block's edit has not been
  saved.", buttons "Stay" and "Leave and discard". Stay, and Escape, close
  the dialog and return focus to the edit box with its text, or to the block
  when the held write has no edit box; Leave and discard navigates. A write
  that is only saving does not block navigation inside the app. With no
  held write neither appears.
- **UX-5** — Code graph. Opening or closing the inspector or the source
  pane re-fits the canvas to its container, so a node click registers without a window resize.
- **UX-6** — Backups "Run now" says a run is already in progress only when
  the server answered 409.
- **UX-7** — A failed request's message is the envelope's `error.message`;
  "API error: N" appears only when the body carries none.

### Output promise

| ID | Promise |
|---|---|
| OP-1 | Proven at 1280x800 and 1920x1080, light and dark. |
| OP-2 | Every changed flow is walked by keyboard alone; changed controls meet WCAG 2.2 AA. |
| OP-3 | Worst-case data: a forced read failure on each Backups query, a keyed provider with a 200-character base URL, a requeue held pending, a 2,000-character block, a refused block write, zero, one and many rows. |
| OP-4 | Out of scope: the Code Graph pane widths (row 411), island separation at hundreds of islands (row 362), the Backups Copy trigger's outline look (row 357); no new screen. |

## Acceptance

A1. [test, neg, high] Row 254: two concurrent re-extractions whose prior and new entity sets are swapped, paused so that each holds its prior row before either upserts, both end `graph=ok`, and neither writes a `pipeline_failures` row.
A2. [test, high] Row 254: a savepoint B that deadlocks on all three attempts ends `graph=error` with the vector write kept and the prior graph intact.
A3. [test, neg, high] Rows 398 and 288: a memory delete that loses one deadlock against a Phase 5 writer still removes the memory's graph contributions and vectors, and a delete whose source withdrawal times out on a fact lock still commits the strip.
A4. [test, high] Row 355: two memories with identical content return in the same order on repeated identical searches, whichever was inserted first, with hybrid search on and off; `rrf_fuse` orders equal scores by row key.
A5. [test, neg, high] Rows 276 and 400: with hybrid search off, two searches during an embedder outage make one embed call between them.
A6. [test, high] Row 279: a seed entity with 25 neighbour memories, of which the 10 with the smallest ids are out of scope, returns the 15 in scope.
A7. [test, high] Row 260: when the same-batch reconciliation raises, every memory the batch wrote still has its `extracted` journal row.
A8. [test, neg, high] Row 261: with no pipeline factory, no flush statement runs on the request's session after the response is sent.
A9. [test, high] Row 399: an inline flush of one row cut at its own deadline charges that row an attempt; an inline flush of several rows cut the same way, and any flush cut at shutdown, charge none.
A10. [test, neg, high] Row 237: a login refused only because five attempts are in flight does not say "failed login attempts".
A11. [test, high] Row 331: a blocklist row written straight to the database closes that session's open socket once the in-process copy is older than 60 seconds, with no restart.
A12. [test, high] Row 371: cancelling a refresh while it waits to close sockets leaves the token not marked renewed.
A13. [test, neg, high] Rows 392 and 393: a pool timeout at the call log's insert, and a cancelled flush, each leave the batch in the buffer.
A14. [test, neg, high] Rows 244 and 246: a failed clone of a URL carrying a token writes the token to no log line, repository row or WebSocket payload.
A15. [test, neg, high] Row 245: for `https://git.lan:8443/o/r.git` and for a default-port URL, the git auth header is configured under that origin, port included, and under no unscoped `http.extraHeader` key.
A16. [test, high] Row 301: a re-clone that raises leaves the repository `error` and its claim released; a cancelled one restores the prior status.
A17. [test, high] Rows 304 and 308: raising `CODE_DERIVER_VERSION` re-derives a repository whose HEAD has not moved, and a deriver tick that derived nothing triggers no code-source reconcile.
A18. [test, neg, high] Row 286: a lift that meets a fact lock held past its deadline defers that candidate and finishes; it does not wait on the lock.
A19. [test, high] Row 315: after a register row edit filed with no orchestrator, every unchanged block has its vector under each of two non-retired fingerprints that held one, and no embed call was made.
A20. [test, high] Row 319: an upload whose `.part` file was collected mid-stream answers 408.
A21. [test, high] Rows 351 and 403: `tests/test_repo_entity_merge.py` passes on a worker database that already holds a committed `(postgresql, database)` entity.
A22. [test, neg, high] Rows 250 and 372: the e2e reset refuses `127.0.0.2`, `::1` and `0.0.0.0` on port 5432, with no database named it targets `darkmem_e2e`, and `gate.sh`'s e2e leg names `darkmem_e2e`.
A23. [test, high] Rows 377 and 378: `backup.sh` keeps the newest three `.suspect` dumps and no more, and touches no real dump; a `restore-cycle.sh` whose migrate overruns its bound swaps nothing and exits non-zero.
A24. [test, high] UX-1 (row 249): changing the base URL of a keyed provider disables Save, shows "The address or API kind changed. Enter the API key again.", and sends no request; typing a key enables Save.
A25. [test, high] UX-2 (row 388): while a row's requeue is pending, that row's Discard and Requeue are disabled.
A26. [test, high] UX-3 (row 389): opening a block for edit puts the selection at the end of its text.
A27. [test, high] UX-4 (row 376): with a refused block write held, an in-app navigation opens "Leave without saving?"; Stay keeps the edit box and its text, Leave and discard navigates; with a write only in flight, or none held, the navigation is immediate.
A28. [test, high] UX-4 (row 376): with a block write held in any state, a `beforeunload` event is cancelled; with none held it is not.
A29. [test, high] UI-1 and UX-6 (rows 366, 406): a failed destinations, inventory or outcomes read each shows the failed state with Retry, Retry re-reads, and a 500 from Run now is not reported as "already in progress".
A30. [test, high] UI-2 (row 330): Settings → LLM shows the stopped-processing banner while `/health` answers `pipeline_state: failed_at_boot`, and not otherwise.
A31. [test, high] UX-5 (row 380): shrinking the code canvas's container refreshes the renderer without a window resize event.
A32. [test, high] UX-7 (row 407): a refusal whose body carries `error.message` and no `detail` shows that message.
A33. [test, high] UI-3 (row 390): in the dark theme a disabled `.dr-btn` has a computed opacity of 0.38.
A34. [demo, high] UI-3 and UI-4 (rows 390, 356): in the dark theme a disabled button, input and select are each dimmer than their enabled twin and still readable, and the Copy Mermaid trigger keeps its width.
A35. [test, confirmed] Row 342: `MemorySearchRequest.context`, the `X-Darkmem-Context` header, the envelope's context echo and the SDK `declareContext` verb are gone from both doors and both SDKs.
A36. [test, neg, high] No Alembic revision, route or MCP tool is added by this plan: `alembic heads` still names `0006_drop_blocks_search_vector` and the guards leg passes unchanged, apart from A35's removals.
A37. [test, high] The register check passes and no row of the register is `open`, `planned` or `doing`.
A38. [test, high] UI-5 and UI-6 (rows 381, 382, 405): the chat row's Delete is not a descendant of its select control, the review queue's fact row renders no block element inside a paragraph, and Settings → Distribution renders no inject log.
A39. [test, high] Row 324: a block verb on a document holding 60 revisions, 10 of them past the newest 50 and older than 90 days, deletes those 10 and journals one `document_revisions_pruned` row.
A40. [test, high] Row 264: a capture with `wait_process` whose inline flush raises answers the 202 ack, and the failure is logged once.
A41. [test, high] Row 275: a stream closed before its end records `ok=False` in `llm_usage`.
A42. [test, neg, high] Row 351: running the test file found to leak leaves no committed `entities` row in its worker database.

## Riskiest assumption

That retrying savepoint B is safe: that a deadlock abort inside the
savepoint leaves the session usable, savepoint A's work intact and no lock
of the failed attempt held. Evidence: PostgreSQL's explicit-locking chapter
says a lock acquired after a savepoint is released when that savepoint is
rolled back to (https://www.postgresql.org/docs/17/explicit-locking.html),
and the seat's trace on 2026-11-23 shows today's handler already rolls back
to the savepoint and commits savepoint A afterwards
(`backend/app/services/pipeline.py:863-866`, `lane-b1-report.md` row 254).
What neither shows is that the cycle is reachable through the real code
paths in a test, so the plan's first task is the two-session reproduction
of A1, which forces the interleaving with the event pauses
`tests/test_phase5_concurrency.py` already uses, written and red before the
retry exists. A test that fails to deadlock shows only that it missed the
interleaving: if it cannot be made red, row 254 is `deferred` as "cannot
tell" with the seat's trace, never `done`, and the retry is not built.

## Review rulings

One `dforge:judge-fable` round on 2026-11-23
(`.dforge/spec-review-2026-11-23-audit-followups-design-1-report.md`): 21
rulings, 2 undecided, 0 Blocker, 1 High (fixed, so no second round).

- Approach (2), and the declines of 268, 273, 312, 362 and 369 — stand; the Notes of 312, 362 and 410 are reworded to what the code shows.
- Row 380 split into 411, the tie-breaks, the board-edit carry, the 60 s revocation reload and no new state board — stand.
- Phase 5 retry — stands, with two cautions the task carries: the second attempt runs with `mem_record` expired by the rollback, and a cycle through a lock taken in savepoint A is not released by it.
- Inject log removal — stands; the Activity tab keeps its inject rendering.
- Leave guard — changed (High): the in-app dialog opens only for a refused write or one queued behind it; the browser prompt covers all held writes.
- A33 / UI-3 — ruled, not the owner's: fix here at 0.38, as a computed-opacity test, with a demo that includes a disabled input and select.
- Closures — 24 sampled `done` rows and every `deferred` row are right; none is closed wrongly.
- Row 399 — the charge applies to a lone row only; a batch refunds.
- Rows 276 and 400 — the hybrid-off branch must embed through `embed_query`, or the cooldown is never set.
- Row 401 — hash each function's rank by `line_start`, not the raw line.
- Row 372 — the `darkmem_e2e` default reaches `gate.sh` and `release.sh`, and the database is created once.
- Row 378 — bounds are overridable and unmeasured here; exit 124 is tested before the hash comparison.
- A23 keeps "touches no real dump"; rule 7 keeps `backup.sh` from being left half-edited across 03:30.
- Rows 324, 264, 275, 406 and 351 — each gained an acceptance statement (A39-A42, A29).
- Row 381 — its axe findings are checked first and fixed or split.
- A1 keeps `high`: the rating grades whether the statement is wanted, and the riskiest-assumption section says what happens if its test cannot be made red.
- Undecided, settled by the owner at the spec review: row 342 is removed, and the 2026-11-20 plan's deploy sequence runs once after this plan merges.

## Critic findings

One `dforge:judge-opus` round on 2026-11-23
(`.dforge/critic-2026-11-23-audit-followups-design-report.md`): 0 Blocker,
1 High, 8 Medium, 4 Nit.

- **High, fixed** — the git auth key left out the port, so a forge on a
  non-default port would lose auth; the key now carries it, A15 tests a
  port-bearing URL, and the rationale names git-lfs and submodule fetches,
  not redirects.
- **Medium, fixed** — the vector carry used the newest fingerprint, which
  search may not read; it now carries under every non-retired fingerprint
  holding vectors for the document.
- **Medium, fixed** — the revocation reload named no trigger, merge rule or
  failure outcome; Decisions and WP4 now state all three and the contract
  sentences that move.
- **Medium, fixed** — the hybrid-off path had no tie-break, so A4 could not
  pass; WP2 names it.
- **Medium, fixed** — "a tie-break cannot move a row past one that outscored
  it" is false under RRF; the claim is gone and the eval re-run is row 413.
- **Medium, fixed** — row 288's lock timeout would have thrown away row
  398's strip; the withdrawal runs in its own savepoint.
- **Medium, fixed** — a deadlock test that cannot be made red no longer
  closes row 254 as `done`.
- **Medium, fixed** — row 324's decline left a retention sentence false; it
  is fixed in WP7.
- **Medium, fixed** — row 312's decline cited a cost only one option has;
  the reason is now the accepted window.
- **Nit** — log each retried deadlock (taken); row 273's reason overstated
  the wire cost (reworded); row 296's reason argued for the fix (row 296 is
  now fixed in WP6); a state row with no deriver version reads as stale
  (stated).

# Audit remaining items — design

**Execution strategy:** sequential — inline execution
**Depth:** full — risk

Resolve every open item of the 2026-11-20 codebase audit
(`docs/2026-11-20-codebase-audit.md` and the eleven track files beside it),
the deferred rows of the three graph registers, and the embedder incident's
follow-ups on this host. The item list is the register
`docs/dforge/registers/2026-11-20-audit-remaining.md` (232 rows). This spec
does not restate the findings: each row names its finding id, and the track
file holds the finding's evidence, location and remedy. The spec says how the
rows are grouped, where the design departs from a reviewer's remedy, what is
declined, and how the result is accepted.

## Decisions

- **Request.** Owner, 2026-11-20: "resolve all remaining items".
- **Process.** Owner: "Full dforge flow (Recommended)".
- **Product items** (local classifier, inject trio, context boost, demo
  views). Owner: "Remove the two with no reader (Recommended)": remove the
  inject trio and the context-boost arm with the Settings controls that
  steer nothing; keep the local classifier and the demo, and make the local
  classifier fail loudly instead of falling back silently.
- **Schema drops** (triple_embeddings tables, stated_expiry arm,
  blocks.search_vector, PDF parser). Owner: "Include all four
  (Recommended)", one revision per drop, each run against a restored
  production backup.
- **Operations.** Owner: "Requeue here, report the rest (Recommended)": the
  53 failed captures are requeued on this host once the fixes are deployed,
  the fork-approval setting is read and reported, and notifications and
  192.168.0.199 stay with the owner.
- **Inherited rulings (audit section 5, owner-delegated 2026-11-20).** The
  LLM `contradiction_scan`, the bar floors and licences, the provider leases
  and `research_rerun` are kept. `ppr_snapshot` and
  `relation_embedding_refresh` stay gated, not deleted. No row reopens them.
- **Two-step drops (my call, from `CLAUDE.md` "Deployed data is durable").**
  A column is dropped only once no released code reads it. v1.17.0, the last
  release, maps `knowledge_triples.stated_expiry` and
  `code_files.last_commit_sha` in its models (`git grep` at `v1.17.0`,
  2026-11-20), so this programme removes every reader and writer of both and
  **does not drop them**: the two drop revisions are register rows deferred
  to the release after the first release that ships without a reader of
  the column. `blocks.search_vector` and the
  `triple_embeddings__*` tables have no reader in v1.17.0 and are dropped
  now.
- **Curb (my call).** With the inject trio gone the curb switch has no
  writer left to stop, so it is removed with the token budget and the watch
  switch; the Distribution policy then holds nothing, so its `PUT` route and
  the `policy` key of the `GET` go too. `docs/two-door-parity.md` records
  that any future inject writer ships with a server-enforced curb.
- **Refine tags (my call).** B3b-4 offers additive-only or summary-only; the
  spec takes summary-only for new refines, which retires B3b-R5. Undo keeps
  its tag restore (B3b-R2 is not taken), because refine events already in
  the journal carry tags.
- **Revision retention.** B5-7 asks for an owner-decided limit, and any
  prune reverses the recorded decision that revisions live as long as their
  document (`docs/superpowers/specs/2026-09-23-work-log-lane-design.md:49,304`).
  Owner, at the spec review: "Beyond 50 and over 90 days (Recommended)": a
  revision is pruned only when it is both past the newest 50 of its
  document and older than 90 days, in the filing savepoint, with no new
  job. Production holds no documents today (0 rows, read 2026-11-20).
- **State boards.** Two Storybook story files, one showing every state of
  the Settings save dialog and one the load-failure pattern, following
  `constellation-board.stories.tsx`; they are the source of the A37 and A41
  proof screenshots (Fable ruling).
- **Kept after the critic's check (my call).** `frontend/nginx.conf` stays:
  `frontend/Dockerfile:17` copies it for the deliberate nginx-in-image
  fallback, so P1-19 is a deferred row. `entailment/cache_span/` stays
  tracked: `faithfulness_gate.py` reads it and the G-F replay ran from it,
  so P1-14 is a deferred row.
- **Declined (my call, each a deferred register row with its reason).**
  B2-22 (the route inventory is the enumeration guard), B3a-19 (the
  reviewer's own condition does not hold), B3b-14 with B3b-R4 and B6-D6
  (each replaces a shape `CLAUDE.md` records as contract and a scan
  enforces; B6-21 removes B6-D6's cost), B3b-R7 (saves nothing), F1-23 (the
  code graph would change appearance two days after it shipped), P1-22
  (waits on owner decision D5), P1-23 (supersession is likely, not shown).
- **Row ownership.** A row listed by two work packages is closed by the
  first that lists it; WP15 edits prose only.

Early CI: none

Finish: merge

Worktree: in-place

## Rules for every work package

1. **Verify first.** The audit says most findings were confirmed only by
   their reviewer. Each task starts by reproducing its finding with a
   failing test, or with a query or command where no test can (a plan
   shape, a CI file). A finding that does not reproduce is closed in the
   register as `done` with the note `not reproduced:` and the evidence, and
   nothing is changed for it.
2. **The reviewer's remedy is the default.** Where this spec names no
   departure, the fix is the remedy in the track file.
3. **Contract sentences move with the code.** A change to behaviour that
   `CLAUDE.md`, `docs/two-door-parity.md` or `docs/api-rest-conventions.md`
   states is corrected in place in the same commit.
4. **Schema.** `0001_baseline.py` is not edited. Each revision chains from
   the head at the time it is written (`0003_board_views` today), stays
   linear, and is run against a
   restored production backup on the dev Postgres before it ships.
5. **Doors.** After any route or MCP tool is added or removed, the guards
   leg in `CLAUDE.md` runs, and the two prose counts it names are re-read.
6. **No removal without proof.** A module, export, script or dependency is
   removed only after a search shows no importer outside its own tests.
7. **Host limits.** Backend suites run on a lane database, never
   `darkmem_test` from a lane and never production; `free -h` is read before
   a red leg is believed.

## Work packages

Rows are named by finding id. "Departs" lists only where the design differs
from the track file's remedy.

**WP1 — Security and exposure.** B6-2, B6-6, B6-7, B6-8, B6-18, B4-19,
P1-2, P1-5, P1-8, P1-10, F2-15.
Departs: P1-2's code half makes the self-hosted e2e job and the picker
refuse a pull request whose head repository is not this one; the GitHub
fork-approval setting is read with `gh` and reported, never changed. P1-10
makes `start_dev_server.sh` use the venv interpreter and refuse to migrate
unless `DATABASE_URL` is set. B6-8's cache holds `sha256(token)` for 60 s in
process and re-checks `expires_at` on every hit. The revoke route adds the
key id to an in-process set of revoked ids after its commit; the set is
checked on every hit and before every insert, so a verify in flight during
a revoke cannot cache the old principal. The cache relies on the single
worker (invariant 13) and on `restore-cycle.sh` stopping the app.

**WP2 — Read-only worker and door parity.** B1-7, B6-3, B2-2, B2-21, B4-12.
B2-2 sends the composition's memory channel through
`HybridSearchService.search_ranked(with_trace=True)` and adds one parity
test per flag kind.

**WP3 — Capture pipeline.** B1-1 remainder, B1-3, B1-4, B1-5, B1-6, B1-8,
B1-9, B1-10, B1-11, B1-12, B1-13, B1-15, B1-18, B1-19, B1-20, B1-21, B1-22.
Departs: B1-15 keeps the local classifier; a save of `classifier_kind=local`
is refused with 422 while torch is not importable. A stored `local` row on
such an image still classifies with the LLM classifier (classification
always runs, under the same single-call merge rule), logs one error per
process, and sets `classifier_unavailable: true` in the `/health` body.
B1-10 deletes the materialised memory through
`MemoryService.delete_memory` after the confirmation UX-12 describes;
`CLAUDE.md`'s `buffer_discarded` sentence changes with it.
B1-22 becomes a module constant.

**WP4 — Retrieval and chat backend.** B2-6, B2-7, B2-8 with B3b-21, B2-9,
B2-13, B2-14, B2-15, B2-16, B2-17, B2-18, B2-19, B2-20.
Departs: B2-13 removes the vector-projection route, its hook, its guard
rows and `utils/math.pca_2d`, which then has no caller. B2-18 removes `flag_measurements` and its badge.

**WP5 — Vault and verification.** B3a-1, B3a-2 with B3b-11, B3a-3, B3a-6,
B3a-7, B3a-8, B3a-9, B3a-10, B3a-11 with B3a-D4, B3a-12, B3a-13, B3a-14,
B3a-15 with B3a-16, B3a-17, B3a-18.
Departs: B3a-7 advances the watermark when a drain returns fewer than
`batch` rows and adds no index. B3a-2 checks the contradiction role's
qualification once at run start, through the judge's own predicate (a
record for the role at the served identity), and skips without draining,
recording the reason `contradiction role unqualified` in the run's result;
the batch default is left alone while the role is unqualified.

**WP6 — Dream, articles, review, research.** B3b-2, B3b-3, B3b-4 with
B3b-R2 and B3b-R5, B3b-5, B3b-6, B3b-7, B3b-8, B3b-9, B3b-10 with B3b-R1,
B3b-12, B3b-13, B3b-15, B3b-16 with B3b-R3, B3b-18, B3b-19, B3b-20.
Departs: B3b-8 makes the dream and hygiene actions strict journal callers
inside their own savepoint; `CLAUDE.md`'s strict-caller list grows. B3b-3
stores a distinct verdict at
`memories.metadata.dream.distinct.<counterpart_id>`, keyed on both content
shas, the shape the `undone_subsume` tombstone already uses, so it needs
no revision. B3b-4
adds a script that lists the memories whose `project/` tags a past refine
removed, from the `consolidated` events' `before.tags`, and can restore
them; WP16 reports its dry run, and the restore runs only on the owner's
word (its own register row).

**WP7 — Code indexing and the MCP code tools.** B4-4 to B4-25, B4 removals
3, 4, 5, 6, 7, B6-15, B6-16, B6-D2.
Departs: B6-D2 comes first: the MCP code tools' queries move into
`CodeQueryService`, which closes B4-9, B4-10 with B6-4, B6-15 and B6-16 in
one place. B4-5 adds one revision with the two `split_part` expression
indexes. B4-25's `last_commit_sha` leaves the model, the response,
`frontend/src/hooks/api/use-code-api.ts` and the raw INSERT in
`scripts/benchlib/promotion_corpus.py` (see Two-step drops). B4-14 records
an unparseable file as a `code_files` row holding its content hash and no
symbols, so the drift scan sees it as indexed; no revision. B4-17 and B4-18
change stored node keys, so WP16 runs a `full=true` reindex of every
repository after the deploy. A code citation stores a node key as
`fact_sources.detail.symbol_key`; the change either shows that no node
kind a citation can name is re-keyed, or rewrites the stored `symbol_key`
values in the same commit, so no citation goes stale from the re-key.

**WP8 — Documents, pages, blocks.** B5-2, B5-3, B5-4, B5-5, B5-7, B5-8,
B5-9, B5-10, B5-12, B5-13, B5-14, B5-15, B5-16, B5-17.
Departs: B5-4 changes two sentences `CLAUDE.md` states as contract: a
re-file reuses the vector of a block whose text is byte-identical, and an
unchanged re-push resolves the fingerprint from `llm_fingerprint()` when
`dimensions` is configured, spending no embed call. B5-7's prune, once the
owner has set its rule: `document_revisions_pruned` enters `EVENT_TYPES`
taxonomy-first with `tests/test_event_taxonomy_map.py`; a journal row that
does not land skips the prune and the put proceeds; a `before` cursor
naming a pruned revision answers 404.

**WP9 — Platform and jobs.** B6-5, B6-9, B6-10, B6-12, B6-13, B6-14, B6-17,
B6-19 with B6-D3, B6-20, B6-21, B6-22, B6-D1, B6-D4, B6-D5.
Departs: B6-5 takes the track's first remedy: the session dependency and
the six generator providers in `api/deps.py` become function-scoped, so
the commit runs before the response on the config routes, on login and
change-password, and on every other write route. Exactly two routes stream
a body from the session, `POST /chat/completions` and
`POST /analytics/reprocess/stream`; their chat and analytics providers get
request-scoped twins used by those two routes only, which commit
explicitly and keep the LLM lease through the stream. B6-D3's `patch_config_row` helper
adds the row lock B6-19 needs. B6-D4 keeps `last_*` out of the `config`
row: the Jobs screen and the failure-notification dedupe read the job's
newest `job_runs` row, `job_run_cleanup` keeps at least the newest row of
every job, and `last_*` keys already stored are ignored on read and
dropped on the next save. That lets B6-10 guard config writes with their
own lock. B6-20 raises the lookahead to three months and reconciles
partitions hourly from the registry's scheduler loop itself, outside any
job, so the job count stays 27 and `PUT /jobs/{key}` is unchanged; the arm
on `pipeline_failure_cleanup` stays. B6-14's `/health` stays 200 and adds
`pipeline_state`: `ok`, `not_configured`, `read_only` or `failed_at_boot`.
B6-21's in-process epoch and blocklist cache relies on the single worker
and on the restore cycle stopping the app. B6-D5: `inject_adapters` and
`client_connect` stay and are documented as CLI-only.

**WP10 — Removals by ruling.** B2-4, B2-11, B2-12 with B3a-5, B3a-4, B5-6,
B5-11, B4 removal 8.
- Context boost: `w_context_boost`, the context half of `rank_fusion`, the
  `by_context_conflict` counter, `community_injection_enabled`, its Settings
  switch and its channel row; also `CONTEXT_BOOST_FLAG` in
  `scripts/benchlib/arm_ablation.py` and the demo's copies of the three
  names with their tests. `by_context_conflict` leaves the retrieval
  envelope chat and MCP serve, a wire change recorded in
  `docs/two-door-parity.md`, and `features/chat/lib/retrieval.ts` stops
  reading it. Stored rows are not rewritten: the flags reader serves only
  keys `FEATURE_FLAGS_DEFAULTS` declares.
- Inject: `inject_watch.py`, `inject_fill.py`, `inject_block.py`,
  `inject_journal.py` (its only callers are the curb route and
  `inject_watch`) and their tests; the Distribution policy's
  `token_budget`, `watch_enabled` and `curbed` with their controls, the
  `PUT /api/v1/distribution/policy` route and the `policy`, `watched` and
  `refresh` keys of the `GET`. `inject_adapters` loses the `watch` cadence: an
  adapter row declaring it is refused with a reason. `inject` and
  `inject_curbed` stay in `EVENT_TYPES` so journalled rows still render. A
  test drives `scripts/connect.py`'s entry function against a session.
- `triple_embeddings.py`, its test and its registry template; one revision
  drops the existing `triple_embeddings__*` child tables.
- The fact-side `stated_expiry` arm in `verification_recompute`,
  `StatedExpiryOutcome`, the `insert_open` parameter, the merge `LEAST`,
  the column's entry in `knowledge_triples._COLUMNS` and
  `tests/test_stated_expiry_facts.py`; the column and index stay (deferred
  row). `app/services/stated_expiry.py`, which sets `memories.expires_at`,
  and `tests/test_self_expiring_memories.py` are live and stay.
- `blocks.search_vector` and `ix_blocks_search_vector`: one revision, with
  the assertions in `tests/test_notes_schema.py` and
  `tests/test_pages_schema.py` and the comment in `block-editor.tsx`.
- PDF parser, its helpers and the four dependencies; the lock is
  regenerated with `uv pip compile --universal`; a PDF stays a designed 422.

**WP11 — Frontend graph and code.** F1-1, F1-2, F1-4, F1-5, F1-6, F1-7,
F1-9 to F1-21, the carried rows constellation-graphs 5, 6, 7,
constellation-real-data 9 and graph-cluster-quality 1, 2, 3, 4, 8.
Constellation-real-data row 10 is F1-7. Graph-cluster-quality row 2 gives
two clusters with one computed name a numeric suffix. Row 4 is a
measurement: the latency measured on an `all_memories` view is recorded in
that register row's Note.

**WP12 — Frontend shell and settings.** F2-2 to F2-18 except F2-12's
finished part.

**WP13 — Frontend content.** F3-1 to F3-9h and the mirror note.
Departs: F3-1 is fixed in the client only: each conversation owns its
stream and its abort controller, so a send in one conversation cannot
abort another's. The mirror note becomes a test that reads the refusal
names out of `block_verbs.py` and fails when `sync-tree.ts` lacks one.

**WP14 — Infrastructure, CI, scripts, extension.** P1-1, P1-3, P1-4, P1-6,
P1-7, P1-9, P1-11, P1-12 remainder, P1-13, P1-15, P1-16, P1-17,
P1-18, P1-20, P1-21, P1-24, lucide-react.
Departs: P1-1 captures a message once its text has not changed for 3
seconds, once per message. P1-13 removes the 0006 loader and its tests and
keeps `llm_providers_transition.py`.

**WP15 — Documents.** B3b-5, B6-22 and P1-6's prose; every `CLAUDE.md`
sentence a work package above changed; the job and tool counts.

**WP16 — After the merge, on this host.** Run each new revision against a
restored backup on the dev Postgres; gate legs; build with
`DARKMEM_PUSH=0`; deploy; confirm the change in the running image; run a
`full=true` reindex of every repository; probe the embedding purpose, and
requeue the 53 `error` buffer rows only if it answers (otherwise the
requeue is reported as blocked, with the reason); report the dry run of
the refine-tag script; read the fork-approval setting with `gh` and report
it; tell the owner that the backup worker's image must move with the
primary, since P1-9 makes an older worker image exit non-zero on a
snapshot carrying these revisions. Nothing is pushed.

## Schema revisions

| Revision | Does | Data |
|---|---|---|
| drop `ix_blocks_search_vector`, then `blocks.search_vector` | B5-6 | a generated column; nothing is lost |
| drop every empty `triple_embeddings__*` table | B2-12 | a table holding a row is left in place and named, with its row count, in the migration log; the upgrade never fails on it |
| add `(repo_id, split_part(source_key,'::',2))` and its target twin on the code edge table | B4-5 | additive |

Deferred to the release after the first release that ships without a
reader of the column: drop `knowledge_triples.stated_expiry`
with its partial index, and `code_files.last_commit_sha`.

## CI

`.github/workflows/ci.yml` (also `release.yml`, `cache-cleanup.yml`;
`workflow_dispatch` is declared). Jobs: `pick-runner` and `images` on
`ubuntu-latest`; `backend`, `frontend`, `frontend-tests` on the picked
runner; `e2e` on `darkmem-linux`. This host runs GNU coreutils 9.7, so
`uutils (ubuntu-latest)` is uncovered. Local commands: `./scripts/gate.sh`
and the legs `CLAUDE.md` lists. Pushing `master` releases; an early CI run
would push a branch only.

## UI/UX contract

**UI/UX depth:** feature — changed states and flows on existing Settings, chat, document, knowledge, graph and code screens

### UI

- **UI-1** — A failed load shows the library `empty-state` with a Retry
  button, and a load in progress shows a skeleton, on Code Graph, Wiki, the
  project switcher, the LLM tab and the graph page. "No … yet" copy appears
  only after a successful, empty load.
- **UI-2** — Both knowledge queues page with the library `pagination`.
- **UI-3** — Every copy action uses the library `clipboard`, so it works on
  the plain-HTTP deployment and reports a failed copy.
- **UI-4** — Settings carries no control that steers nothing: no token
  budget, watch switch or curb on Distribution, no community-injection
  switch and no "unmeasured" badge on Flags; each dormant rank arm carries
  the fixed line "Turned on only after a measured retrieval win".
- **UI-5** — The graph detail panel's close button is named "Close details".
- **UI-6** — Settings → LLM shows "Local classifier unavailable, using the
  LLM classifier" on the classification purpose while `/health` reports
  `classifier_unavailable`.

### UX

- **UX-1** — Settings save. A dialog stays open while its save runs, with
  Save in its pending state; it closes with a "Saved" toast only on success.
  On a refusal it stays open, keeps every edit and shows the server's
  reason inside the dialog. A number field updates as it is typed, so Save
  enables without a blur, and an out-of-range value shows an error. A
  toggle that saves at once returns to its old position and toasts when the
  save fails.
- **UX-2** — Session. `GET /auth/me` and the refresh answer carry
  `expires_at`; the app checks it each minute and on `visibilitychange`,
  and renews the session while more than an hour remains to spare, so a
  draft in either editor survives the 24-hour mark. A renewal and a
  password change both rotate the token. On either, in both the normal and
  the read-only posture, the server closes the sockets bound to the
  presented token with code 4001 "Session renewed", before the blocklist
  write commits; sockets of every other
  session still close as revoked after a password change. The tab that
  rotated records the time in localStorage once its response, and so the
  new cookie, has arrived. A tab whose socket closed with 4001 reconnects
  only after it sees that record (its own response, or the storage event
  in another tab), and goes to sign-in if none arrives within 10 seconds.
  A 401, an expired-close or a handshake refused as "Unauthorized" within
  10 seconds of a recorded renewal is retried once instead of ending the
  session. Outside that window, a socket closed as "Session expired or
  revoked" or a refused renewal sends the app to sign-in once, with no
  further retry. A tab that slept past expiry goes to sign-in by
  client-side navigation, which keeps the notes draft registry; an unsent
  document block edit is lost. The one-second socket revalidation is
  unchanged.
- **UX-3** — Chat. Sending in one conversation leaves another's stream
  running; returning to the first shows its finished answer. A turn that
  never completes leaves its conversation in the list. A failed delete says
  so and keeps the conversation. A streaming token re-renders only the
  streaming message.
- **UX-4** — Document block editor. A refused or failed write keeps the edit
  box open with the typed text and shows the reason; no later queued write
  is sent after a refusal until the operator acts.
- **UX-5** — Hygiene queue. Changing project or page clears the selection.
  A bulk action acts on exactly the selected rows on screen and names their
  count in its confirmation; when some of its actions fail, the toast names
  how many succeeded and how many failed, and the failed rows stay
  selected.
- **UX-6** — Notes. A failed page rename shows an error and leaves the typed
  title in the field.
- **UX-7** — Code. Edit Repository saves a repository cloned from a URL and
  shows its path as text. Blast Radius on a file-level node asks for a
  symbol instead of doing nothing, and a failed request toasts. Typing in
  the code search dims non-matching nodes without restarting the layout or
  moving the camera; a rebuild re-centres a selection that persists.
- **UX-8** — Memory graph. In 2D no 3D data is built. Clicking an entity in
  3D shows that entity. Changing colour mode recolours in place. Turning
  Regions off removes outlines and chips in the same frame. Two clusters
  never show the same name.
- **UX-9** — Lists. A work-log task filter fetches only entries after the
  last one held. Two quick board edits to one register both land. The facts
  filter lists every option the server holds. The Research tab keeps typed
  budgets across a settings reload. The re-embed count is right after an
  embedder change. A setup-status server error shows an error with Retry,
  not the wizard. 119.6 seconds prints as "2m 0s".
- **UX-10** — Demo mode sends no API request from Settings → LLM.
- **UX-11** — The setup wizard holds vendor API keys in memory only.
- **UX-12** — Buffer triage. Discarding a failed capture whose memory
  already exists names that memory in the confirmation, says it will be
  deleted, and deletes it only on confirm.

### Output promise

| ID | Promise |
|---|---|
| OP-1 | Proven at 1280x800 and 1920x1080, light and dark. |
| OP-2 | Every changed flow is walked by keyboard alone; changed controls meet WCAG 2.2 AA. |
| OP-3 | Worst-case data: a 64-character repository name, an unbroken URL, zero, one and many rows, a refused save, a forced load failure, a 20,000-node synthetic graph. |
| OP-4 | Out of scope: no new screen; demo views stay parallel to the real ones; the two layout engines stay. |

## Acceptance

A1. [test, high] B3a-1: with a lift and a re-extraction of the same memory interleaved in two sessions, the fact ends with no source the memory's new graph does not assert.
A2. [test, high] UX-3 (F3-1): a send in a second conversation does not abort the first conversation's stream, and the first answer is stored and shown.
A3. [test, high] UX-7 (F1-1): Edit Repository saves a repository whose `local_path` is null.
A4. [test, high] UX-8 (F1-2): with the 2D view active, a filter change builds no 3D graph data.
A5. [test, high] P1-1: a reply that changes 30 times before settling produces one capture request.
A6. [test, neg, high] P1-2: a pull request from a fork is never routed to a self-hosted runner by the workflow or the picker.
A7. [test, neg, high] B6-2: twenty concurrent wrong-password logins from one address verify at most five passwords, and bcrypt runs off the event loop.
A8. [test, neg, high] B6-6: with `CORS_ORIGINS` unset, a credentialed request from `http://localhost:3000` gets no CORS allow header.
A9. [test, neg, high] B6-7: an SSH destination whose `user` or `host` begins with `-`, or whose `remote_dir` holds a newline, is refused at save.
A10. [test, neg, high] B6-18: saving a provider or destination with a masked secret and a changed URL or host is refused until the secret is entered again.
A11. [test, high] B6-8: a second keyed call within 60 seconds verifies no bcrypt, and a revoked or expired key is refused on its next call.
A12. [test, neg, high] B1-7 and B6-3: in read-only mode the reprocess and failure-retry routes and MCP `memory_reason`, `memory_overview` and `document_search` are refused before any provider call.
A13. [test, high] B2-2: with the reranker stubbed to a fixed scoring, chat, `knowledge_search` and `memory_search` return the same memory order with `hybrid_search_enabled`, `reranker_enabled` and `confidence_rank_gamma` each flipped in turn.
A14. [test, high] B4-12: MCP `code_search` with no embedder returns the keyword arm's rows, marked degraded.
A15. [test, high] B1-4: two concurrent supersessions of one candidate leave one `superseded_by` and one `superseded` event.
A16. [test, high] B1-3: two concurrent Phase 5 writes sharing entities both commit without a deadlock.
A17. [test, high] B1-5: the memory-graph predicates plan as GIN index scans.
A18. [test, high] B1-6 and B1-9: a `wait_process` capture that passes its deadline answers the ack, its flush finishes, and no 201 carries an unprocessed memory.
A19. [test, neg, high] UI-6 (B1-15): saving `classifier_kind=local` without torch answers 422; with a stored `local` row and no torch, `/health` carries `classifier_unavailable: true`, Settings → LLM shows the unavailable line, and memories are still classified.
A20. [test, neg, high] B3b-4: a new refine changes a memory's summary and never its tags, and undoing a refine journalled with tags still restores them.
A21. [test, high] B3b-2: the digest marks a derivation `associate` action undoable exactly when its undo succeeds.
A22. [test, neg, high] B3b-8: a dream or hygiene action whose journal write fails commits nothing.
A23. [test, high] B3b-6: two subjects with one name and different entity types get articles built from their own facts.
A24. [test, high] B3a-2: with the contradiction role unqualified, a scan tick drains nothing and writes no journal row.
A25. [test, high] B5-2: a document block edit whose embed fails answers success with `blocks_embedded` 0, and the block has no stale vector.
A26. [test, high] B5-3: a 50 MB upload in progress does not block a page write in another project.
A27. [test, confirmed] B5-7: a content-changing put prunes exactly the revisions of that document that are both beyond its newest 50 and older than 90 days; one count-only `document_revisions_pruned` event is journalled before the delete, a prune whose journal row does not land is skipped while the put succeeds, and a `before` cursor naming a pruned revision answers 404.
A28. [test, high] B5-4: an unchanged re-push with `dimensions` configured makes no embed call, and a re-file embeds only blocks whose text changed.
A29. [test, high] B6-5 and B6-19: every write route outside the two streaming routes takes the function-scoped session, a source scan fails when a handler returning `StreamingResponse` resolves a function-scoped session or provider, a change-password and a config save are each durable before their response is sent, and two concurrent saves of one config row both survive.
A30. [test, high] B6-9, B6-10 and B6-D4: a raised `min_interval_seconds` in code applies to an existing install, disabling a job answers while that job runs, and a job whose only run is older than 5,000 newer runs of other jobs still shows its last run.
A31. [test, high] B6-14: a boot whose LLM setup raises still reconciles the events partitions, and `/health` answers 200 with `pipeline_state: failed_at_boot`.
A32. [test, high] B6-20: with `pipeline_failure_cleanup` disabled, events partitions still exist three months ahead.
A33. [test, high] B4-6 and B4-11: a file whose embed failed is embedded by the next run, and an unchanged dependent is not re-embedded.
A34. [test, high] B4-7 and B4-8: an incremental run handles a changed `src/é.py`, and a subclass of a base in an unchanged file keeps its `extends` edge to that file.
A35. [test, high] B4-9, B6-4 and B6-16: MCP `code_symbol`, `code_blast_radius` and the repo-named tools answer for an indexed repository, honour repository and owner, and list candidates when a name is ambiguous.
A36. [test, neg, high] B4-13 and B4-20: a failed fetch never deletes a healthy clone, and the fetch lane never fast-forwards a branch other than the default.
A37. [test, high] UX-1: a refused Settings save leaves the dialog open with the edits and the server's reason; a successful one closes it with "Saved".
A38. [test, high] UX-2: with a session 23 hours old the app renews it without a reload, its socket reconnects after the 4001 close once the new cookie has arrived, and a second tab stays signed in; a password change keeps the tab that made it signed in and connected; a socket closed as expired with no recent renewal leads to sign-in with no further retry; the renewal and the password change are each exercised over a real socket in the API e2e suite.
A39. [test, high] UX-4: a refused block write keeps the typed text in the edit box, and no queued write follows it.
A40. [test, neg, high] UX-5: after a project change a bulk action in the hygiene queue touches no row selected before the change.
A41. [demo, high] UI-1: Code Graph, Wiki, the project switcher and the LLM tab show a Retry state on a forced load failure and a skeleton while loading, in both themes.
A42. [demo, high] UI-2, UI-3, UI-5, UX-6, UX-7, UX-8, UX-9: each item is shown working in the proof report at both viewports.
A43. [test, neg, high] UX-10 and UX-11: demo mode makes no request from Settings → LLM, and no vendor API key is written to localStorage.
A44. [test, neg, high] UI-4 (B2-11): the Distribution tab carries no token budget, watch switch or curb, no `inject_watch`, `inject_fill`, `inject_block` or `inject_journal` module and no policy route remains, and `scripts/connect.py` still resolves an adapter.
A45. [test, neg, high] B2-4: no `w_context_boost`, `community_injection_enabled` or `by_context_conflict` remains in code, benchlib, the demo or the UI, the served flags carry none of them even when the stored row does, and retrieval order is unchanged by their removal.
A46. [demo, high] B5-6 and B2-12: on a restored production backup the two drop revisions upgrade in place; the `blocks` row count is recorded before and after, is non-zero (a filed document and a page are seeded on the restored copy when it is zero) and is unchanged; no empty `triple_embeddings__*` table remains, and any left is named with its row count and gets a register row.
A47. [test, neg, high] B3a-4 and B4 removal 8: no code reads or writes `knowledge_triples.stated_expiry` or `code_files.last_commit_sha`, both columns still exist, and `memories.expires_at` is still derived from a stated expiry.
A48. [test, neg, high] B5-11: a PDF filing answers 422, and the lock holds none of pdfplumber, pdfminer-six or pypdfium2.
A49. [test, high] P1-3, P1-9, P1-17, P1-18: a cancelled tag job creates no release, a failed migrate in the restore cycle exits non-zero unless the snapshot is from an older baseline, a dirty tree is not tagged with the HEAD sha, and a dump of the wrong database triggers no prune.
A50. [test, high] P1-15 and P1-4: CI runs the extension suite and both SDK suites, and `numpy` is declared.
A51. [demo, high] WP15: `CLAUDE.md`, `CONTRIBUTING.md` and `docs/two-door-parity.md` state what the code does for every sentence this programme touched, and the job and tool counts are right.
A52. [test, high] Register: every row of `docs/dforge/registers/2026-11-20-audit-remaining.md` is `done` (with a commit, or `not reproduced:` and its evidence) or `deferred` with its reason.
A53. [demo, high] WP16: the running image on this host carries the change, and the 53 failed captures are `done` with a vector on each memory, or the requeue is recorded as blocked with the embedder's answer.
A55. [test, high] UX-12 (B1-10): discarding a failed capture whose memory exists deletes that memory only after a confirmation that names it.
A54. [demo, high] OP-1, OP-2, OP-3, OP-4: the proof report covers both viewports and both themes, a keyboard-only walk of every changed flow and the worst-case data, and shows no new screen.

## Riskiest assumption

That the findings are right as written. The audit says a finding not marked
verified is "the reviewer's own confirmation and has not been checked twice"
(`docs/2026-11-20-codebase-audit.md:30-32`). Evidence that they hold: all 15
fixes of the audit pass had a test that failed first (its section 2), and
five open findings were re-read in the code on 2026-11-20: F1-1
(`frontend/src/features/code/schemas.ts:7`), B6-6
(`backend/app/main.py:932`), P1-10 (`scripts/start_dev_server.sh:14`), B6-4
(`backend/app/api/mcp/server.py:1651`) and B1-18
(`backend/app/services/pipeline.py:508`). Rule 1 bounds the cost of a wrong
one to its reproduction attempt.

## Critic findings

One `dforge:judge-opus` round on 2026-11-20
(`.dforge/critic-2026-11-20-audit-remaining-design-report.md`).

- **Blocker, fixed** — a renewal revoked the token the open socket is
  checked against: UX-2 and A38 now state the 4001 close, the reconnect and
  the cross-tab window.
- **High, fixed** — removing `inject_watch` broke the kept `inject_adapters`
  and `connect.py`: WP10 now removes the watch cadence, `inject_journal`
  and the policy route, and A44 tests `connect.py`.
- **High, fixed** — summary-only refine dropped undo's tag restore: undo
  keeps it, and a script lists and can restore lost `project/` tags.
- **High, fixed** — removing `frontend/nginx.conf` broke the kept
  `frontend/Dockerfile`: the file stays and P1-19 is deferred.
- **High, fixed** — B6-5 left the auth routes committing after the
  response: WP9 takes the function-scoped session for every write route.
- **Medium, fixed** — B6-8's cache race and missing expiry re-check; the
  context-boost removal's missed consumers and stored keys; `job_runs`
  pruning under B6-D4; B1-15's undefined outcome; the unjournalled revision
  prune; storage for B3b-3 and B4-14 and the reindex after key changes;
  untracking `cache_span` (now kept); the refusing drop revision (now skips
  and reports); the `stated_expiry` name clash; B6-20's mechanism; A31's
  status code.
- **Nit, fixed** — the scan's named skip reason; the state-board decision's
  wording; A46's tag and A13's stubbed reranker; row ownership; Rule 4's
  chain wording; `pca_2d`; `last_commit_sha`'s other readers; B5-6's tests;
  UX-5's partial failure.

## Review rulings

`dforge:judge-fable`, round 1, 2026-11-20
(`.dforge/spec-review-2026-11-20-audit-remaining-design-1-report.md`).

- Two-step drops stand; the trigger is the release after the first release that ships without a reader of the column.
- The owner's "Include all four" is met: only the two column drops wait.
- The curb is removed with no owner question (A44 `high`); the parity doc records that a future inject writer ships with a server-enforced curb.
- Summary-only refine stands with no owner question (A20 `high`); undo keeps its tag restore.
- State boards are built as two story files and feed the A37 and A41 proofs.
- `frontend/nginx.conf` and `entailment/cache_span/` stay.
- Every declined item stands as declined.
- Row ownership stands.
- A stored `local` classifier row falls back to the LLM classifier, and the operator sees it in Settings (UI-6).
- The requeue runs only after the embedding purpose answers.
- The function-scoped session is sound for the two streaming routes, given request-scoped twins and the source scan.
- The 4001 close is compatible with the revalidation contract; it fires on every successful refresh in both postures and on a password change.
- The in-process key cache is acceptable under invariant 13 with the revoked-id check on hit and insert.
- The revision prune does not conflict with the journal's retention rule; its number is the owner's (A27).
- Both drop revisions comply with the durable-data rule.
- The critic's Blocker and four Highs are answered; the two holes Fable found in UX-2 are fixed above.
- Round 2: both UX-2 Highs are answered; the 4001 close must stay ahead of the blocklist commit.

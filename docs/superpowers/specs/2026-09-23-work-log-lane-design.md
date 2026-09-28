# Work-log lane: working data separated from memories

Date: 2026-09-23
Status: design, owner-approved section by section on 2026-09-23. Increment 1
planned (`docs/superpowers/plans/2026-09-23-work-log-increment-1-store-and-verbs.md`);
amended the same day with four corrections found while planning, each marked
"Amended 2026-09-23" below. Increments 1-3 done and deployed on this host as
v1.12.0 (2026-09-27); increment 4
(`docs/superpowers/plans/2026-09-27-work-log-increment-4-capture-warning.md`)
done and deployed on this host 2026-09-28, unreleased; increment 5
(retention, `docs/superpowers/plans/2026-09-28-work-log-increment-5-retention.md`)
implemented 2026-09-28, not yet deployed.
Register: `docs/superpowers/registers/2026-09-23-work-log-lane.md`
Companion spec (client side): `darkraise-ai-plugins`,
`docs/superpowers/specs/2026-09-23-darkmem-mirror-design.md`

## Why

The .195 corpus migrated on 2026-09-23 showed what happens when the memory
door is the only obvious place to write: of 787 live memories, the median was
2,177 characters, 495 carried commit hashes, and most were session logs —
ledger lines, gate tallies and merge events re-typed into `memory_add`. The
cleaning pass split them into 6,234 facts and dropped 311 log pieces plus 3
memories that were nothing but merge logs. Extraction accuracy was measured on
memories of median 64 characters (`gold.json`), so every such row is extracted
at a length nobody has measured, and its log content becomes graph entities
that are stale the next day.

Coding clients legitimately need somewhere to keep that working data. The
dr-superpowers plugin already produces it — `.superpowers/handoff/latest.md`
(the checkpoint, client-summarised), `.superpowers/sdd/<plan>/progress.md` (an
append-only ledger), `handoff.md` (constraints, gotchas, open questions) — plus
specs, plans and registers committed under `docs/superpowers/`. None of it
reaches darkmem; the working files are local to one machine, and the planning
documents clutter every repository.

darkmem already has half a lane: `session_checkpoints` (T3.16) is firewalled
from the pipeline and the vault. It is too thin to carry this: save and
"latest for this run" only, keyed on a run identity that ends with the
session, no history, no search. Production on this host holds zero rows.

## Decisions (owner, 2026-09-23)

| # | Question | Decision |
|---|---|---|
| 1 | What clients must do with working data | Resume anywhere; look back over runs; search it; watch it live in the UI; dr-superpowers stores its documents and progress here |
| 2 | Which dr-superpowers files move | Everything: specs, plans, registers, distilled notes, ledgers, handoffs. Review packages stay local scratch |
| 3 | How the plugin reaches them | A local mirror outside the repo, synced; darkmem is the source of truth (companion spec) |
| 4 | History for specs and plans | Document revisions kept in darkmem |
| 5 | Ledger storage | A stream of log entries, one row per line |
| 6 | Grouping and resume key | Workstream per project (client-named), runs under it |
| 7 | Checkpoint content | The client's own summary, stored verbatim; darkmem never re-summarises |
| 8 | Log-like content at `memory_add` | Accepted, with a warning in the response |
| 9 | Retention | Until the workstream is closed, plus N days (default 90) |
| 10 | Store shape | A new work-log store that replaces `session_checkpoints` (approach A of three; a block-first ledger document and an extended `session_checkpoints` were rejected, below) |

This builds on, and does not reopen, the 2026-08-31 artifact-store spec: its
§7 rejections still hold — no task model, no progress prose in `EVENT_TYPES`,
no new LLM purpose or background job that digests progress. Its §3 split
("checkpoints for live, a document for durable") is kept in spirit and
replaced in mechanism: the live half becomes the work-log stream, the durable
half stays documents.

## 1. Data model

One baseline regeneration (greenfield; no migration, no shim).

### `workstreams`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `project` | TEXT NOT NULL | registered lazily through `project_registry.register` |
| `key` | TEXT NOT NULL | client-named; dr-superpowers uses the plan or design slug; CHECK `char_length(key) BETWEEN 1 AND 200` |
| `title` | TEXT | CHECK `char_length(title) <= 500` |
| `client` | TEXT | e.g. `dr-superpowers`; descriptive only |
| `state` | TEXT NOT NULL DEFAULT `'open'` | CHECK `state IN ('open','closed')` |
| `closed_at` | TIMESTAMPTZ | set on close, cleared on reopen; CHECK `(state = 'closed') = (closed_at IS NOT NULL)` |
| `properties` | JSONB NOT NULL DEFAULT `'{}'` | `plan_uri`, `spec_uri`, `handoff_uri`, branch, worktree; CHECK `pg_column_size <= 16384` |
| `retain` | BOOLEAN NOT NULL DEFAULT false | exempts the workstream from retention (§6); set by `worklog_update` |
| `last_entry_at` | TIMESTAMPTZ | set by every append in the same transaction; what the UI lists by |
| `created_at`, `updated_at` | TIMESTAMPTZ | `updated_at` via the `touch_updated_at` trigger |

`UNIQUE (project, key)`. An append to an unknown key creates the workstream;
there is no separate create verb.

### `worklog_entries`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `workstream_id` | UUID NOT NULL | FK → `workstreams` ON DELETE CASCADE |
| `run_key` | TEXT NOT NULL | resolved session identity; undeclared is refused |
| `kind` | TEXT NOT NULL | CHECK `kind IN ('checkpoint','ledger','note')` |
| `body` | TEXT NOT NULL | markdown, verbatim; CHECK `char_length(body) BETWEEN 1 AND 65536` |
| `properties` | JSONB NOT NULL DEFAULT `'{}'` | task number, status, commit; CHECK `pg_column_size <= 16384` |
| `search_vector` | TSVECTOR | filled by an insert trigger, `to_tsvector('english', body)` |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| `seq` | BIGINT GENERATED ALWAYS AS IDENTITY | the order of entries |

**Amended 2026-09-23:** entries order by `seq`, not `(created_at, id)`: every
entry of one append shares the transaction's `now()` and random UUIDs carry
no order, so a ledger's chunks would not concatenate back. `search_vector` is
a generated column (`to_tsvector('english', body)`) rather than a trigger —
the same content with no function to maintain.

Indexes: `(workstream_id, kind, seq DESC)` — the newest checkpoint is a
one-row index scan; `(workstream_id, seq)` — the ledger in order; GIN on
`search_vector`.

Entries are append-only from the API. No verb updates or deletes a single
entry; rows leave only through retention (§6) or a workstream purge.

Bounds are enforced twice, at the schema layer (a 422 the caller can act on)
and by the CHECK constraints (the guarantee), the same posture
`session_checkpoints` has today. The byte bound on `properties` is checked
against the *encoded* size for the reason `chk_session_checkpoints_next_steps_len`
records.

### `worklog_embeddings__<slug>`

A new parent family in `embedder_registry` beside `block_embeddings` and
`page_embeddings`: `(entry_id FK → worklog_entries ON DELETE CASCADE,
project TEXT NOT NULL, embedding vector(N))`, created by `register` for every
fingerprint. Filled by a work-log arm of the existing hourly
`block_embedding_refresh` job with its own `worklog_batch` budget, exactly as
the page arm (`_PAGE_ARM`, `page_batch`) works. Appends never embed inline, so
a write never waits on the LAN embedder.

`project` is denormalised onto the vector row with a btree index, and the
semantic arm computes exact cosine distance over one project's rows with no
HNSW index. The reason is the one that gave pages their own family: an ANN
scan filters after the index probe, so a shared partition lets other
projects' rows crowd the candidate stream. Per-project work logs are small
enough for an exact scan; an index is added only when a measurement says so.

Only the first 8,000 characters of a body are embedded, because
`nomic-embed-text` reads 2,048 tokens and a 65,536-character checkpoint would
otherwise be truncated silently by the embedder. The keyword arm indexes the
whole body, and search results say which arm matched.

### `document_revisions`

**Amended 2026-09-23:** the table already exists in the baseline as an inert
object (`0001_baseline.py`, "Version history: a full post-image snapshot per
commit"; `tests/test_inert_objects.py` lists it) with `id`, `document_id`
(cascade), `content NOT NULL`, `content_hash`, `created_at`. Increment 3 keeps
it and its post-image semantics — each revision is the content a changed put
*wrote*, so the newest revision equals the current content — adds `actor TEXT`
and `api_key_id UUID`, and removes it from `INERT_TABLES`.

### Dropped

`session_checkpoints`, its model, schema, service, routes and MCP tools. Its
content is `kind='checkpoint'` entries now.

### Events

Taxonomy first: `workstream_opened`, `workstream_closed`, `workstream_reopened`,
`workstream_purged` and `capture_flagged` join `EVENT_TYPES`; `workstream`
joins `OBJECT_TYPES`. `checkpoint_saved` and `resumed` leave the vocabulary
with their emitter. No entry body, and no document content, ever lands in an
`events` payload: the journal is unpurgeable by ruling (T2.59), which is why
per-entry events are not journaled at all — the entries table is itself the
history.

## 2. Verbs

Every verb exists on both doors and runs through one service module,
`app/services/worklog.py` (two transports, one implementation — invariant 17).

| Verb | MCP | REST | Scope |
|---|---|---|---|
| Append | `worklog_append` | `POST /api/v1/worklog/entries` → 201 | capture |
| Resume | `worklog_resume` | `GET /api/v1/worklog/resume?project=&workstream=` | read |
| List workstreams | `worklog_workstreams` | `GET /api/v1/worklog/workstreams` | read |
| List entries | `worklog_entries` | `GET /api/v1/worklog/workstreams/{id}/entries` | read |
| Search | `worklog_search` | `POST /api/v1/worklog/search` | read |
| Update workstream | `worklog_update` | `PATCH /api/v1/worklog/workstreams/{id}` | capture |
| Purge workstream | `worklog_purge` | `DELETE /api/v1/worklog/workstreams/{id}` → 204 | admin |
| Document revisions | `document_revisions` | `GET /api/v1/documents/{id}/revisions`, `GET .../revisions/{rev_id}` | read |
| Document manifest | — (REST only) | `GET /api/v1/documents/manifest?project=&uri_prefix=` | read |

Scope counts after the change: capture 13 → 15 (`worklog_append`,
`worklog_update` in), read 25 → 30 (`worklog_resume`,
`worklog_workstreams`, `worklog_entries`, `worklog_search`,
`document_revisions` in), admin 2 → 3 (`worklog_purge`).
`checkpoint_save` and `checkpoint_latest` stay served as the older pair.

**API keys on REST.** A REST route accepts a `dmk_` key only when it declares
`require_scope` (`app/api/auth.py`); `require_auth` decodes a login token and
nothing else, and today the document routes use it. Every work-log route
declares `require_scope` with the scope in the table. So do the document
routes the mirror needs, which is a deliberate widening, route by route, of
which doors a key reaches: `POST /api/v1/documents` (capture),
`GET /api/v1/documents/by-uri` (read), the two revision routes (read) and the
manifest (read). The rest of the document surface stays login-only.

**Manifest.** `GET /api/v1/documents/manifest` answers `{uri, content_hash,
updated_at}` for every document of one project under a uri prefix, keyset-paged,
with no content. It is what lets a mirror pull fetch only what changed; the
existing list route has no prefix filter and serves no hash. REST-only,
recorded as a single-door row on `docs/two-door-parity.md` beside
`documents.reads`: its only caller is a sync client, which speaks REST.

**Append** takes `project`, `workstream` (the key), optional `title` and
`properties` for the workstream, and `entries`: 1–100 items of
`{kind, body, properties?}`, written in one transaction. It answers the
workstream id and the entry ids in order. Appending to a closed workstream
reopens it and journals `workstream_reopened`. Creating one journals
`workstream_opened`.

The workstream row is locked before anything is decided — `SELECT … FOR
UPDATE`, or, when absent, an `INSERT … ON CONFLICT DO NOTHING` whose loser
re-locks the winner's row — and the transition (opened, reopened, continued)
is read from the locked row (amended 2026-09-23: a single upsert read the
prior state from its snapshot and could miss a concurrent close). A retention or purge `DELETE` racing an append therefore
serialises on that row or passes it by: the retention sweep skips a row an
append holds (`FOR UPDATE SKIP LOCKED`; amended 2026-09-28), and once the
append has committed the sweep's `state = 'closed'` predicate no longer
matches, so the workstream survives; if
the delete commits first, the append's upsert creates a fresh workstream.
Neither order loses an entry into a deleted parent.

A `ledger` entry's body is the exact text a client appended, newlines
included, so concatenating a workstream's ledger entries in order reproduces
the file byte for byte. A ledger is therefore stored in chunks of whatever
the client wrote at once, never re-split into lines by the server; blank lines
live inside chunks, which is what lets the 1-character minimum hold.

**Resume** answers one bounded object: the workstream (key, title, state,
properties), the latest `checkpoint` entry verbatim or null, the 50 newest
`note` entries with `notes_truncated` when there are more, and the last 20
`ledger` entries in order. When the workstream does not exist — the ordinary
first-session case — REST answers 404 and MCP answers `null`, exactly as the
two doors answer `checkpoint_latest` today.

**List** verbs are keyset-paged on `(created_at, id)` and filter by `state`
(workstreams) or `kind` and `since` (entries). Entries default to oldest first,
so a client can render a ledger by paging forward.

**Search** takes `project` (required — a scope that can be omitted gets
omitted), `query`, and optional `workstream`, `kind`, `limit`. Two arms: a
`ts_rank` arm over `search_vector` with `plainto_tsquery('english', :q)`, and a
cosine arm over `worklog_embeddings__<slug>` for the active fingerprint,
fused by RRF with `RRF_K` imported from `app/services/rank_fusion.py` (the AST
scans forbid a second declaration). When the embedder is unreachable, or the
instance is read-only, the keyword arm answers alone and the response says
`semantic_ran=false`. Results carry the entry, its workstream key and
`rrf_score`.

**Update** moves `state` (closing sets `closed_at`, journals
`workstream_closed`; reopening clears it), `retain`, `title` and `properties`
(merged, not replaced).

**Purge** erases a workstream with its entries and vectors. It is the strict
journal contract: `workstream_purged` is written first and read back, and the
delete is refused when it did not land (the Events-journal paragraph of
`CLAUDE.md`; a local `WorklogJournalWriteFailed`, since this module is
firewalled from the vault's exception type). `admin` scope, by the
`document_delete_subtree` precedent: a capture key must not be able to erase a
project's history.

**Run identity** resolves exactly as checkpoints resolve it today — explicit
argument, then `X-Darkmem-Client` plus the declared identity, then User-Agent —
and an undeclared run is refused, never merged into an `unknown:` bucket (the
reasoning in `checkpoints.py`'s docstring carries over unchanged: this is a
lookup key, and merging would cross two runs' lines).

**Removed:** `checkpoint_save`, `checkpoint_latest`, `POST /api/v1/checkpoints`,
`GET /api/v1/checkpoints/latest`, and `resume_inject.py`, whose `resume_fill`
has no caller in `backend/app` today. The MCP catalogue goes from 40 tools to
46 (minus 2, plus 8).

## 3. Documents and revisions

Specs, plans, registers, distilled notes and per-plan handoff notes are
ordinary documents filed through `document_put`, under `project = <repository
name>` and a `superpowers/` uri prefix:

| Source today | darkmem |
|---|---|
| `docs/superpowers/specs/<f>.md` | document `superpowers/specs/<f>.md` |
| `docs/superpowers/plans/<f>.md` | document `superpowers/plans/<f>.md` |
| `docs/superpowers/registers/<f>.md` | document `superpowers/registers/<f>.md` |
| `docs/superpowers/distilled/…`, `notes/…` | documents under `superpowers/distilled/`, `superpowers/notes/` |
| `.superpowers/sdd/<plan>/handoff.md` | document `superpowers/handoff/<plan slug>.md` |
| `.superpowers/sdd/<plan>/progress.md` | `ledger` entries in workstream `<plan slug>` |
| `.superpowers/handoff/latest.md` | `checkpoint` entries in the current workstream |
| review packages, other `sdd` scratch | not synced; regenerated from git |

`handoff.md` is a document rather than `note` entries because it is edited in
place; as notes, every edit would duplicate it in `worklog_resume`. The
workstream's `properties.handoff_uri` names it.

**Revisions.** `put_document` gains an `api_key_id` parameter beside its
existing `actor`, which both doors already know, and writes the filed
`content` and `content_hash` as a `document_revisions` row inside the filing's
savepoint whenever a put creates a document or changes its `content_hash`
(post-image, amended 2026-09-23). A byte-identical re-push writes none; a
stale `expected_hash` writes none (nothing was filed); a bytes source, whose
`content` is NULL, writes none. The
revision rolls back with the filing, so a refused or failed put never leaves a
revision behind. Revisions live as long as their document. Amended 2026-09-25:
`put_document` and `file_document` already carry `api_key_id`, so the write
lands in `file_document`'s body, inside the filing's own savepoint. "Changes
its `content_hash`" is decided against the resolved row's hash, or, when the
filing resolved no row, against the document's newest revision read under the
row lock, so two racing first filings of one content write one revision; a
forced reparse of identical bytes writes none.

Block-verb edits on block-first documents write no revision in this version:
one row per block edit would flood the table, and dr-superpowers files through
`put` only. The page tree is untouched. Both limits are stated, not solved.

Diffs are computed by the caller from two contents; the server serves
contents, not patches.

## 4. Client side

The dr-superpowers mirror, the `darkmem-sync` command and the one-time import
of existing files are the companion spec's. This spec owes it the keyed REST
surface of §2 — the work-log routes, `POST /documents`, `GET /documents/by-uri`,
the manifest and the revision routes — and nothing else: the plugin reaches
darkmem over REST with a `dmk_` key, not over MCP.

This repository's own `docs/superpowers/` moves in that import. Before it is
deleted from the tree, `CLAUDE.md` and code comments that cite
`docs/superpowers/…` paths are rewritten to the `superpowers/…` uri form, and
`CLAUDE.md` gains one line saying those documents live in darkmem under
project `darkmem` and are read through the mirror. A reader without the
mirror cannot follow them; that is the accepted cost of decision 2.

## 5. The memory-door warning

`app/services/capture_lint.py`: a pure function over the content, no LLM, no
database. Named signals:

| Signal | Matches |
|---|---|
| `commit_ref` | a hex token of 7–40 characters containing both a digit and a letter, not part of a UUID; `<sha>..<sha>` ranges |
| `tally` | `N passed`, `N failed`, `N/N`, `N commits`, `N of N tasks` |
| `progress` | `Task N`, `Phase N`, `Wave N` with complete/done/started; "all green" |
| `vcs_event` | merged / pushed / fast-forwarded / branch deleted |
| `file_line` | `path.ext:N` |
| `trace` | `Traceback`, `at X.Y(`, `Exception:` lines |
| `narration` | "this session", "next steps", "TODO" |
| `length` | over 1,500 characters |

A capture is flagged when two or more signals match, or `length` alone. The
signal patterns and the threshold are module constants pinned by fixtures,
not configuration.

A flag never refuses. All four capture doors (REST single and batch, MCP
`memory_add` and `memory_batch_add`) gain `warnings: list[str]` on their
answer — empty when clean, per entry for batches. On the 202 path it is a
field of `CaptureAck`. On the 201 `wait_process` path the routes answer a new
`CapturedMemoryResponse`, `MemoryResponse` plus `warnings`, used only by the
capture routes: `MemoryResponse` itself is what every memory read serves, and
a field there would appear, always empty, on every read. MCP's JSON answers
gain the same key. The warning names the signals and points at
`worklog_append` and `document_put`. Each flagged capture journals
`capture_flagged` with `object_type='memory'` and a payload of signal names
only.

**Calibration before the constants are fixed**, recorded in the plan's first
task: run the detector over the 2026-09-23 migration lineage (787 originals,
6,234 cleaned pieces). The acceptance evidence is two rates — the share of
originals flagged and the share of cleaned pieces flagged — and the thresholds
are chosen so the second is low without losing the first. The lineage is user
data and stays outside the repository; only the numbers are recorded in the
plan.

**Instructions** (`prompt.PROMPTS["agent_instructions"]`, extending the
uncommitted "A memory is not a log" change of 2026-09-23 — register item 4):
the section's close becomes "working data goes to `worklog_append`, write-ups
to `document_put`, durable facts to `memory_add`"; a new "Work log" section
lists the seven work-log tools, says to call `worklog_resume` at session start
and append a `checkpoint` at stops, and states the promotion rule — after a
checkpoint, `memory_add` the durable facts the run established, one per entry.
Promotion is the agent's; darkmem never distils logs itself.

## 6. Retention

A new job, `worklog_cleanup` (roster 25 → 26), daily, registered through a
`WORKLOG_CLEANUP_JOB_KEY` constant. `config_schema`: `retention_days` (int,
default 90, min 1). It deletes workstreams with `state='closed'`, `retain = false` and
`closed_at < now() - retention_days`, cascading entries and vectors, and
journals one `workstream_purged` per workstream under the same strict
contract as the purge verb. Open workstreams are never pruned, however old.

Ledgers imported from past plans arrive as closed workstreams with
`retain = true` (companion spec), so the history an import exists to carry is
not deleted 90 days later; clearing `retain` hands one back to the ordinary
rule. The same switch keeps any other workstream the owner wants to keep.

## 7. The wall

`tests/test_block_retrieval.py`'s three structural scans gain the work-log
modules as subjects:

- the retrieval-fusion closure (`HybridSearchService`,
  `LayerCompositionService` and their channel and id-kind registries) must not
  reach `app.services.worklog` or the `worklog_embeddings` family;
- the vault-minting closure must not reach a module that reads a work-log row;
- the work-log modules name neither `KnowledgeTripleRepository`, its module
  nor the `knowledge_triples` table, and the import closure of every
  work-log module except the route module reaches no vault writer.
  Amended 2026-09-25: a scan for every repository method name cannot tell
  `session.get` from a repository's `get`, and the route module reaches the
  repository only through the auth layer every router shares.

And the pipeline half, as `test_block_pipeline.py` does for documents: the
import closure of `app.services.worklog` must not reach
`app.services.pipeline`. `memory_search` never returns an entry;
`worklog_search` never returns a memory.

## 8. UI

- **Project workspace, Progress tab → "Work log".** Left: the project's
  workstreams, open first, closed collapsed, each with title, key, last-entry
  time and state. Right: the selected workstream's entries on darkraise-ui
  `virtualized-timeline` — kind badge, run, time; checkpoints as expandable
  markdown, ledger lines compact; kind filter; refetch every 5 s while the
  workstream is open. Header: links to `plan_uri`, `spec_uri`, `handoff_uri`
  in the Artifacts tab; close/reopen; purge behind a confirmation dialog. A
  search box runs `worklog_search` for the project. The ledger path-suffix
  convention in `project-workspace.tsx` is removed.
- **Activity route.** `CheckpointsTab` becomes a cross-project list of open
  workstreams with their latest entry, linking into the project's Work log.
  `use-checkpoint-runs.ts` (events-derived history) is deleted.
- **Documents.** A Revisions sheet (darkraise-ui `sheet`) on the document view:
  the revision list and a line diff between any two. darkraise-ui has no diff
  component, so this adds the `diff` package and a small local renderer whose
  comment names that gap.
- **Events.** The new event types get frontend event-taxonomy entries (the
  taxonomy-map test enforces it), so flagged captures show in the Activity feed
  with their signal names.
- **Demo mode.** Every new hook carries `enabled: !DEMO`, with demo fixtures
  for the Work log.

## 9. Sequencing

Six increments, each landing green and deployed on this host before the next:

1. **Store and verbs.** Schema (workstreams, entries), `worklog.py`, append / resume / list / update /
   purge on both doors, events vocabulary, scopes, parity doc, content-surface
   inventory, instructions, `CLAUDE.md` counts; `require_scope` on the document
   routes the mirror uses, and the manifest route. The companion spec can start
   after this.
2. **Search.** The embeddings family, the refresh-job arm, the search verb.
3. **Document revisions.** Table, write path, read verbs on both doors.
4. **Memory-door warning.** Calibration, `capture_lint.py`, `warnings` on the
   four doors, `capture_flagged`.
5. **Retention.** `worklog_cleanup`.
6. **UI and checkpoint removal.** Work log tab, Activity list, Revisions
   sheet, demo fixtures; then drop `session_checkpoints`, its tools and routes,
   and move `resolve_checkpoint_origin` into `worklog.py`. Amended 2026-09-23:
   the removal moved here from increment 1 because the SPA's Checkpoints tab
   reads those routes, and removing them before the Work log view exists would
   break the live instance between increments.

## 10. Testing and acceptance

- **Service:** append creates-or-reuses the workstream; the 100-entry batch is
  one transaction; bounds refuse at 422 and the CHECKs refuse below the door;
  undeclared run refused; resume returns the newest checkpoint, all notes and
  the last 20 ledger entries in order, notes capped at 50 with
  `notes_truncated`; ledger entries concatenate back to the appended text byte
  for byte; append to a closed workstream reopens it; an append racing a
  retention delete either keeps the workstream or recreates it, never writes
  into a deleted parent.
- **Doors:** `tests/test_door_parity.py` covers every new verb;
  `test_rest_conformance.py` (201 append, 204 purge, POST search); scopes
  (capture key cannot purge; read key cannot append).
- **Purge and retention:** the journal row lands before the delete; a forced
  journal failure refuses the delete and leaves every row; retention skips
  open and retained workstreams and removes vectors through the cascade.
- **Revisions:** a new put and a changed put each write one revision
  (amended 2026-09-25 to the post-image rule of §1 and §3); unchanged,
  stale-hash, forced-reparse and bytes filings and block verbs write none; a
  put refused for `MAX_BLOCKS` leaves no revision.
- **Search:** each arm alone and fused; `semantic_ran=false` when the embedder
  raises; project scoping enforced in SQL.
- **Lint:** fixtures per signal, positive and negative, and the threshold
  boundary; the four doors carry `warnings`; the journal payload holds no
  content.
- **Wall:** the scans of §7, each with a negative control that proves it can
  fail.
- **Content surfaces:** every new route and tool is classified in
  `app/services/content_surfaces.py`'s inventory, in
  `ROUTES_WITHOUT_MEMORY_CONTENT` / `MCP_TOOLS_WITHOUT_MEMORY_CONTENT` as the
  checkpoint doors are (amended 2026-09-23: they serve no memory content, so
  the scoping classes do not apply); `tests/test_content_surface_scoping.py`
  fails on an unclassified door.
- **Keyed REST:** a `dmk_` key reaches exactly the routes §2 lists and is
  refused (401) on the rest of the document surface.
- **Guards leg:** the mandatory set from `CLAUDE.md` after every increment that
  adds a route or tool; `docs/two-door-parity.md`'s headline counts and this
  file's prose counts re-read by hand.
- **Frontend:** vitest for the Work log tab, the Activity list and the
  Revisions sheet; typecheck; build.

Done means: the register's items 1, 2, 4 and the darkmem half of 3 and 5 are
`done` with evidence; the companion spec carries the rest of 3 and 5.

## 11. What not to build

- **Server-side summarising or distilling of logs.** Clients already summarise
  (decision 7); a server LLM pass would reintroduce the precision problem the
  2026-09-23 cleaning pass needed two recalibrations to contain.
- **Per-entry events.** The entries table is the history; `events` stays free
  of agent prose.
- **Editing or deleting a single entry.** Append-only keeps the ledger honest;
  purge is per workstream.
- **Merging work-log hits into `memory_search`**, in either direction.
- **A task model, statuses per task, dependencies.** Still rejected (2026-08-31
  §7); `properties` carries what a client wants to record.
- **Revisions for block-first documents and pages.** Stated limit (§3).
- **A refusing memory gate.** Decision 8: warn, never lose a write.

## Invariant check

- Invariant 15: no dream job is reachable from the new verbs, and the
  refresh-job arm is an artefact refresh, not a family member.
- Invariant 17: one service module behind both doors for every verb.
- Invariant 13: nothing here adds process-local state beyond the job lock the
  registry already owns.
- Invariant 23 ("here is the full list" prose): the tool count, job roster and
  event vocabulary sentences in `CLAUDE.md` are updated in the increment that
  moves them.

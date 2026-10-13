# A Notion-like progress board over registers and plan tasks

Date: 2026-10-13
Status: design, owner-approved section by section on 2026-10-13; revised the
same day after an independent review (Fable judge seat), owner-approved fixes.
Register: `docs/superpowers/registers/2026-09-23-work-log-lane.md` row 85
(and row 1, whose owed review this board's review closes).
Supersedes: `docs/superpowers/specs/2026-09-04-progress-board-design.md`.
Amends: `docs/superpowers/specs/2026-09-23-work-log-lane-design.md` §11.
Client contract (fixed, owned by the plugin): `darkraise-ai-plugins`,
`docs/superpowers/specs/2026-10-13-darkmem-store-options-design.md` §3.

**Execution strategy:** sequential — every later part consumes the register
parser and row rewriter, which carry the one data-loss risk and land alone
first; the frontend's checks need the live routes.

## Rulings (owner, 2026-10-13)

| # | Question | Decision |
|---|---|---|
| 1 | The board's records | Both register rows and plan tasks, as two record types; the T-epic board (`planning/progress.md`, `planning/tasks/`) is retired |
| 2 | Views | Board and table over the same records, with saved views and built-in views |
| 3 | Where saved views live | A server-side `board_views` table |
| 4 | Properties | Only those the formats carry, plus derived ones; no user-defined properties |
| 5 | Writes | Register rows are writable (state, note, assigned) through a document put; plan tasks are read-only |
| 6 | Approach | A server-side projection service (of three: client-side projection, and a materialised records table, rejected as a second store) |
| 7 | Execution | Sequential |
| 8 | Document properties on a board edit (review I1) | The put passes none, as the REST door and the mirror's own put do |
| 9 | Converting a register or plan to block-first (review I2) | Refused on the server for `superpowers/registers/` and `superpowers/plans/` uris on both doors, and edit mode hidden for them in the SPA |

## Why

The Progress tab's board reads only `planning/progress.md` and T-numbered epic
files, which no current workflow produces (the 2026-09-04 spec measured that
ledger at 309 tasks, 306 of them `done`). The work the owner now tracks
arrives from dr-forge as registers, plans and plan ledgers, and the board can
show none of it. It also has no table, no saved views and no way to move a
card.

The 2026-09-04 spec's core lesson stands and shapes this one: a board is a
projection of records that are already correct, never a second store. Plan
`- [ ]` checkboxes still cannot be progress — across this repository's 114
plans there are 787 `### Task` lines, 3,796 unchecked box lines and 363 checked
ones, for largely finished work (raw line counts, fenced examples included).

Measured 2026-10-13: neither this host's production instance nor
192.168.0.199 holds any `superpowers/` document or workstream yet (the dr-forge
mirror is not running). The design is therefore measured against this
repository's committed registers and plans and against real ledgers in
`darkraise-ai-plugins/.superpowers/sdd/`.

**The ledger properties do not exist yet.** The plugin's push today
(`darkmem-push.mjs`) sends ledger entries with no per-entry properties, and its
import (`darkmem-import.mjs`) does the same. The contract's §3 is designed and
not shipped, and covers push only. §1.3 is built so that a ledger without
properties never reads as unstarted work.

## 1. Records

### 1.1 Corpus

A project's board reads the documents whose uri starts with exactly
`superpowers/registers/` or `superpowers/plans/` and ends in `.md`. No
leftmost-segment matching (the plugin fixed that defect as its dr-forge
register row 13). A repository path in a cell (`docs/forge/<rest>`,
`docs/superpowers/<rest>`, optionally backticked) is normalised to the uri
`superpowers/<rest>` wherever the board resolves a cell to a document.

### 1.2 Text rules shared by both parsers

Both parsers mirror the plugin's shell parsers
(`plugins/dr-forge/scripts/lib/plan.sh`, `lib/register.sh`):

- Lines split on `\n` only (never Python's `splitlines`, which also splits on
  U+2028, U+000C and others). For parsing, `\r` is removed, as the plugin's
  `tr -d '\r'` does; the bytes of the document are never changed by parsing.
- **Fences** follow `plan.sh`'s `in_fence`: an opener is up to three spaces
  then three or more backticks or tildes; it closes only at a bare marker of
  the same character at least as long as the opener. Fence markers and fenced
  lines are skipped.

### 1.3 Register rows

Following `register.sh`:

- the line is trimmed; a line not starting with `|` is not a table line;
- `\|` is held aside before splitting on `|` and restored in each cell
  afterwards, so a cell may contain a pipe;
- the header row (`#` in the first cell) and the separator row are skipped;
- a row is well formed when it splits into exactly eight fields (six cells) and
  its `#` is all digits. Any other table line is listed as **malformed** on its
  register with its line number, never dropped silently;
- two well-formed rows with the same `#` are both listed as malformed (reason:
  duplicate number) and neither is a record.

A row carries `#`, Item (its title), Assigned, Acceptance, State and Note; its
register carries its `# ` title, its `**Covers:**` value and the document's
`content_hash`.

States are `open planned doing verify done deferred n/a`. Any other value keeps
its raw text and lands in **unrecognised**; no committed row does today.
`verify`, `deferred` and `n/a` require a Note, as `REGISTER_NOTE_REQUIRED`
does; a Note that is empty or `-` after trimming is blank, as `blank_note` has
it.

**Plan progress** (derived): when Assigned resolves to exactly one plan
document in the project, the row shows "*d* of *n* done", counting that plan's
tasks whose state (§1.4) is `done`, out of all its tasks. When the plan's tasks
are untracked, the row says so instead of a count. Assigned text naming another
project ("darkraise-ai-plugins: docs/…") stays plain text.

### 1.4 Plan tasks

A **task heading** is what `plan.sh`'s `is_task` accepts: one or more `#`,
whitespace, `Task`, whitespace, then digits, outside a fence. The task number
N is the leading integer (so `Task 5a` is task 5, as in the plugin, and as the
contract's `task` property will be). The label is the heading's text from
`Task` on, verbatim; the title is the text after the number token
(`[0-9]+[A-Za-z]*`) and an optional `:`, `.` or `-`. Two headings in one plan
with the same N are both shown, each flagged "shares task number N; the ledger
cannot tell them apart", and both take N's state.

The `- [ ]` steps under a heading are shown only in the task's detail,
labelled as the implementer's checklist, never counted.

**Workstream.** The project's workstreams whose `properties.plan_uri` equals
the plan's uri (the plugin writes the darkmem uri,
`superpowers/plans/<slug>.md`). When several match, the board uses an open one
over a closed one, then the newest `last_entry_at`, and the plan shows "*k*
other workstreams name this plan".

**State**, in this order:

1. **untracked — no workstream:** no workstream names the plan.
2. **untracked — ledger without properties:** the workstream has no `ledger`
   entry whose `properties.task` is an integer. This covers every ledger pushed
   or imported before the plugin ships its §3. Both untracked kinds are hidden
   by default; the card names which one applies.
3. The `state` property of the newest (highest `seq`) `ledger` entry in the
   workstream whose `properties.task` is the integer N and which carries
   `state`. Entries with a task but no state (minors, parked items, rulings)
   never move it. Values are `wip review blocked done`; any other lands in
   **unrecognised**.
4. **todo:** none of the above applies.

**Known limit.** A ledger pushed partly before the plugin sent properties shows
the tasks finished in that earlier part as `todo`; entries are append-only, so
nothing on this side can repair them. The plugin's own fix (properties on
import, and a re-import) is recorded on its register.

**Integer** means `jsonb_typeof(properties->'task') = 'number'` and the value
equals its own floor; any other `task` is ignored. The plugin's first-match rule
reads a ruling line such as "Task 3: Ruling: HANDBACK … after one BLOCKED run"
as `blocked`; the board shows what the entry says and does not second-guess it.

**Other task properties:**

- **Blocked reason:** when the state is `blocked`, the body of the entry that
  set it, preceded by the bodies of the same workstream's `ledger` entries
  immediately before it in `seq` order that carry identical properties and whose bodies do not end in `\n` —
  the earlier pieces of a ledger line cut at the body limit.
- **Commit:** the newest `commit` property among the task's entries.
- **Last activity:** `created_at` of the task's newest entry of any kind.
- **Orphan:** a ledger task number with no heading in the plan is listed on the
  plan.

Nothing is stored: every read derives the records from documents and entries.

### 1.5 Properties

The one list every view, filter and saved definition draws from:

| Property | Register row | Plan task | Single-value (groupable) |
|---|---|---|---|
| `type` | yes | yes | yes |
| `title` | Item | heading title | |
| `number` | `#` | N | |
| `state` | register vocabulary | task vocabulary, `untracked`, `unrecognised` | yes |
| `source` | register uri | plan uri | yes |
| `note` | Note | blocked reason | |
| `assigned` | Assigned | | yes |
| `acceptance` | Acceptance | | |
| `plan_progress` | derived | | |
| `plan` | resolved from Assigned | the plan | yes |
| `spec` | | workstream `spec_uri` | |
| `workstream_state` | | open or closed | yes |
| `commit` | | newest commit | |
| `last_activity` | | newest entry time | |

## 2. Backend

### 2.1 `app/services/board.py`

- `parse_register(text)`, `parse_plan(text)` and
  `rewrite_register_row(text, number, changes)` are pure: text in, records or
  text out.
- `load_board(session, project)` runs: the corpus documents (id, uri, title,
  content, content_hash); the project's workstreams with a `plan_uri`; per
  (workstream, task), the newest state-bearing ledger entry with its run of
  preceding pieces (§1.4), by `DISTINCT ON`; per (workstream, task), the newest
  entry of any kind, for commit and last activity; per workstream, whether any
  ledger entry carries an integer `task`.
- `board_version(session, project)` is two aggregate queries (the corpus
  documents' count and greatest `updated_at`; the project's greatest entry
  `seq` and workstream `updated_at`) and reads no content.
- It reads `documents.content`, never `blocks`, and imports neither
  `app.services.pipeline` nor any vault module.

**Scan membership**, named so no implementer has to infer it: `board.py` joins
`BLOCK_CHANNEL_MODULES` (`tests/test_block_retrieval.py`, as
`document_revisions` did), `FILING_CLOSURE`'s subjects
(`tests/test_block_pipeline.py`) and `WORKLOG_MODULES`
(`tests/test_worklog_wall.py`, which also subjects it to the memory-table and
fact-store scans). Increment 2 checks that `document_door`'s import closure
passes the work-log service-layer scan once `board.py` is a member.

### 2.2 Routes (`api/routes/board.py`)

REST-only behind login: no MCP tool, no scope, and a `dmk_` key is refused
(401). Recorded as `board.*` single-door rows in `tests/test_door_parity.py`'s
`PARITY_TABLE` (from which `docs/two-door-parity.md` is generated) and
classified in `app/services/content_surfaces.py`'s inventory.

**Errors** carry a structured `detail`, `{reason, message}` plus fields named
per reason (the `reembed.py` precedent), so the UI can tell causes apart.

- `GET /api/v1/board/records?project=` — registers (rows, malformed rows,
  title, covers, `content_hash`, a per-register parse error if any) and plans
  (chosen workstream id, key and state, other-workstream count, `spec_uri`,
  tasks, orphans, a per-plan parse error if any). The frontend flattens them.
  The response carries an `ETag` from `board_version`; a matching
  `If-None-Match` answers 304 before any content is read.
- `PATCH /api/v1/board/registers/{document_id}/rows/{number}` with
  `{expected_hash, state?, note?, assigned?}`; at least one change, else 422.
  The service reads the document, refuses when its hash differs from
  `expected_hash`, rewrites the one row (§2.3) and files the result through
  `document_door.put_document` with the same `expected_hash`, `actor` set to
  the login, no `properties` (ruling 8), and `embed_inline=False` (§2.4). The
  put takes the row lock and the compare-and-set, writes the revision and
  journals its usual `document_filed` event. Answers 200 with the row and the
  new `content_hash`. Errors:

  | Status | `reason` | Cause |
  |---|---|---|
  | 404 | `not_found` | no such document, a document outside `superpowers/registers/`, or no row with that number |
  | 409 | `hash_conflict` | stale `expected_hash` (detail adds `current_hash`) |
  | 409 | `block_first` | the register is block-first |
  | 422 | `duplicate_row` | two rows carry that number |
  | 422 | `malformed_row` | the number exists only on a malformed row |
  | 422 | `unknown_state` | a state outside the register vocabulary |
  | 422 | `note_required` | the resulting state needs a Note and the resulting Note is blank |
  | 422 | `invalid_cell` | a cell value containing `\n` or `\r` |
  | 422 | `no_change` | none of `state`, `note`, `assigned` given |

  Refused by `refuse_when_read_only`.
- `GET /api/v1/board/views?project=` — the two built-ins, then saved views by
  `(position, name)`.
- `POST /api/v1/board/views` (201) with `{project, name, definition,
  position?}`; `position` defaults to one past the project's greatest.
- `PATCH /api/v1/board/views/{id}` with any of `name`, `definition`,
  `position`.
- `DELETE /api/v1/board/views/{id}` (204).

  View errors: 404 `not_found` for an unknown id; 409 `name_taken` for a
  `(project, name)` collision; 422 `builtin_view` for a write to a `builtin:`
  id; 422 `invalid_definition` for a definition failing the schema or encoding
  to more than 16,384 bytes, checked at the door so the CHECK below never
  answers 500 (the work-log `properties` pattern).

### 2.3 The row rewrite

The rewrite is a **splice into the original line**, never a re-serialisation:

- cell boundaries are found with the parser's rule (an escaped `\|` is not a
  boundary);
- for each changed cell, only its trimmed text is replaced; the cell's padding
  is kept;
- the new value is written with `|` escaped as `\|`;
- leading indentation, a trailing `\r`, and anything after the row's last `|`
  are kept;
- every other line of the document is untouched.

### 2.4 Putting without an inline embed

`put_document` commits the filing and then embeds every block; an embed
failure therefore raises after the edit committed, and the request waits on
the LAN embedder. It gains `embed_inline: bool = True`; with `False` it returns
after the filing commits and embeds nothing, and the hourly
`block_embedding_refresh` sweep embeds the register's new blocks, as it does
for page writes. Every existing caller keeps the default. The board's PATCH
therefore needs no orchestrator and answers once the edit is durable. A
register's search hits lag its last board edit by up to an hour.

### 2.5 No block verbs on registers and plans

`block_verbs` refuses a document owner whose uri starts with
`superpowers/registers/` or `superpowers/plans/`, before taking any lock or
converting anything: REST answers 422 with the reason (the dr-forge mirror
owns these documents through content puts), MCP `block_update`,
`block_insert`, `block_move` and `block_delete` answer the same as a tool
error. The SPA hides edit mode for those uris. A register converted before this
lands is recovered by deleting and re-filing it; the board's cards for a
block-first register say so.

### 2.6 `board_views`

One additive Alembic revision, `down_revision` the head at the time:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `project` | TEXT NOT NULL | |
| `name` | TEXT NOT NULL | CHECK `char_length(name) BETWEEN 1 AND 100` |
| `position` | INTEGER NOT NULL | |
| `definition` | JSONB NOT NULL | CHECK `pg_column_size(definition) <= 16384` |
| `created_at`, `updated_at` | TIMESTAMPTZ | `updated_at` via `touch_updated_at` |

`UNIQUE (project, name)`. The definition is validated against a closed schema:
`layout` (`board` or `table`), `group_by` (a groupable property of §1.5, or
null), `filters` (each a property, an operator `in`, `not_in` or `contains`,
and values), `sort` (property and direction), `columns` (properties) and
`show_untracked`. Property names come only from §1.5.

**Built-in views are code constants, not rows.** There are exactly two:
`builtin:open-register-items` (board, register rows grouped by state, `done`
and `n/a` hidden) and `builtin:plans-in-flight` (board, plan tasks of open
workstreams grouped by plan, untracked hidden). They are neither editable nor
deletable; duplicating one is how it is customised. Views journal nothing:
they are layout, not data.

## 3. Frontend

`features/board/` replaces `features/progress/`. The old parsers, gates, the
startable filter, cards, detail and their tests are deleted, with the
`planning/progress.md` and `planning/tasks/` conventions. The Progress tab
keeps the 2026-09-28 layout: board on top, Work log beneath. The `personal`
project shows no board (owner ruling: its documents are visible nowhere in the
SPA); the route still serves it, as every document route does.

- **Toolbar.** View tabs (built-ins, then saved views); the current view's id
  in the URL (`?view=`); a Board/Table switch; group-by; a multi-select per
  groupable property plus a text match over title and note; a show-untracked
  switch; save as view, rename and delete (saved views only).
- **Board.** Grouping by State splits into one swimlane per type, each across
  its own vocabulary plus its unrecognised column (and untracked for plan
  tasks, when shown); two vocabularies never share columns. Any other grouping
  mixes types in shared columns.
- **Cards.** Type badge, title, `#` or the task label, source document's short
  name. A register card adds Assigned and plan progress, and shows its Note
  when in `verify`, `deferred` or `n/a`. A plan-task card adds the commit and
  last activity, its blocked reason when `blocked`, which untracked kind
  applies when untracked, and the shared-number flag when present.
- **Dragging** (`@dnd-kit/core`): register cards only, within the register
  swimlane of a State grouping. Pessimistic: the card shows pending until the
  PATCH answers. A drop into `verify`, `deferred` or `n/a` opens a dialog
  holding the current Note, its confirm disabled while the Note is blank
  (§1.3). A `hash_conflict` reloads the records and shows a toast that the
  register changed since it was loaded; every other refusal shows its
  `message`. Plan-task cards show a lock: "state comes from the plan's
  ledger".
- **Table** (darkraise-ui `table`): column chooser, header-click sort; on
  register rows, State edits through a `select`, Note and Assigned through
  `editable`, all through the same PATCH. No virtualisation until measured
  (about 900 rows with untracked tasks hidden).
- **Detail sheet** (darkraise-ui `sheet`): every property. A register row
  links to its register and its assigned plan in the Artifacts tab. A plan task
  shows its labelled step checklist, links to plan and spec, and "Show in Work
  log", which selects the workstream below with that task filtered.
- **Work log** (register row 1's owed review, folded in): timeline rows show an
  entry's `task`, `state` and `commit` as badges, and the panel gains a task
  filter. While the filter is set, the panel pages through the workstream's
  `ledger` entries (500 per request) until exhausted before filtering, showing
  a loading state, so the filter never reflects only the loaded pages. No route
  changes.
- **Artifacts.** Edit mode is hidden for `superpowers/registers/` and
  `superpowers/plans/` documents (§2.5).
- **Refresh and demo.** Records refetch every 10 s while the tab is visible,
  sending `If-None-Match`. Every new hook carries `enabled: !DEMO`, with demo
  fixtures for records and views.

## 4. Rulings changed

Each old spec gets an "Amended 2026-10-13" note at the section affected.

- **Work-log spec §11** ("a task model, statuses per task, dependencies: still
  rejected") is narrowed, not reversed: darkmem has no task table, no
  server-side writer of a plan task's state and no dependencies. The board
  reads the `task`/`state` entry properties the plugin's §3 will send.
- **Progress-board spec §4** ("no writes") is reversed for register rows only.
  This is the write-through §4 named as its follow-up; the write lands as a
  darkmem document revision, and the dr-forge mirror carries it to the
  repository.
- **Progress-board spec §7**: no second status vocabulary and no mapping onto
  a generic kanban set — kept, each type keeps its own format's vocabulary. No
  burndown or velocity — kept. No checkbox aggregation — kept. No new backend
  route — reversed by ruling 6.
- **Progress-board spec §2.1** (checkboxes are never progress) holds.
- **Block verbs** stop accepting `superpowers/registers/` and
  `superpowers/plans/` documents (ruling 9). No route the dr-forge mirror uses
  changes.

`CLAUDE.md` gains a short Board section (projection, no store; register edits
only through `put_document` with `expected_hash` and no inline embed; block
verbs refused on registers and plans), and its Documents section records the
§2.5 refusal and `embed_inline`. The parity doc's headline counts sentence is
re-read by hand, as `CLAUDE.md` requires.

## 5. Failure handling

- A register or plan that fails to parse reports its error on its own source
  group; the rest of the board renders.
- A plan with no task headings is a plan with no tasks.
- A board edit racing a local edit of the same register: whichever writes
  second meets a hash conflict — the board answers 409 and reloads; the
  mirror's push gets `hash_conflict` and follows the plugin's conflict
  handling. Nothing is overwritten on either side.
- A block-first register is read normally and refused for edits
  (`block_first`); its cards name the recovery (delete and re-file).
- Ledger values outside the contract are ignored (non-integer `task`) or
  surfaced as unrecognised (unknown `state`), never coerced.
- An edit never fails for an embedder reason (§2.4).

## 6. Testing

- **Parsers, against the committed files.** Assertions are relationships, not
  pinned counts, so a new register row breaks nothing: every table line outside
  a fence whose first cell is all digits is a parsed or a malformed row; every
  line `is_task` accepts outside a fence across the plans is a parsed task;
  the work-log register's row 66, whose Item holds an escaped `\|`, parses as
  one well-formed `deferred` row (a split on bare `|` misreads it). Fixture
  cases for the fence rule (a 4-backtick block holding a 3-backtick fence,
  tildes, an indented opener), duplicate numbers, a `-` Note, `Task 5a`, `##`
  and `####` task headings, and U+2028 inside a cell.
- **Rewrite property test** over every row of every committed register:
  changing a state and changing it back reproduces the original bytes; the
  changed text differs from the original in exactly one line. Fixture cases
  for padding, indentation, a trailing `\r`, text after the last `|`, an
  escaped pipe and a Note containing `|`.
- **Ledger derivation**, with fixtures copied from real dr-forge ledger lines:
  newest state-bearing entry wins; stateless task lines do not move it; both
  untracked kinds; todo; a cut line's pieces join into the blocked reason; two
  workstreams naming one plan; `1.5` and `"3"` as `task` ignored; orphan; a
  shared task number.
- **Routes:** REST conformance (PATCH, 201, 204); every row of §2.2's two error
  tables; a successful edit writes exactly one revision carrying the actor and
  embeds nothing inline; the ETag answers 304 when nothing changed and 200
  after a document put or an append; read-only refusal; a `dmk_` key gets 401;
  content-surface classification; the scan memberships of §2.1, each with a
  negative control; the guards leg from `CLAUDE.md`.
- **Block-verb refusal:** each of the four verbs, on both doors, refused for a
  register and a plan uri and still accepted for any other document;
  `put_document`'s default `embed_inline=True` path unchanged.
- **Migration:** the `board_views` revision runs against a restored backup
  holding data, not only the empty test schema.
- **Frontend:** vitest for State swimlanes, register-only dragging, the note
  dialog (blank includes `-`), the conflict toast versus other refusals, table
  edits, saving a view and duplicating a built-in, both untracked kinds on
  cards, the Work log badges and the paging task filter, and hidden edit mode
  for registers and plans; `npm run typecheck`; `npm run build`. One
  Playwright spec drags a card, run through
  `backend/scripts/e2e/run_playwright_e2e.py`, never bare.

## 7. Sequencing

Each increment lands green before the next.

| # | Increment | Depends on |
|---|---|---|
| 1 | Parsers and row rewriter, with their golden and property tests; no routes | — |
| 2 | `load_board`, `board_version`, the ledger joins and the records route; scan memberships | 1 |
| 3 | `board_views` revision and its four routes | — |
| 4 | `embed_inline`, the block-verb refusal (§2.5) and the register-row edit route | 1, 2 |
| 5 | Board, table, views, detail sheet, Work log badges and filter, hidden edit mode, demo fixtures; old board deleted | 2, 3, 4 |
| 6 | Deploy to this host; the owner reviews the board and the Work log UI together | 5 |

Increment 1 is worth landing alone: if the parser cannot hold the committed
registers and plans, that is the finding, before anything is built on it.

**Done means:** increment 6 deployed and confirmed in the running image, and
the owner's review recorded; register rows 85 and 1 close on it. Plan tasks
fill only once the plugin ships its §3; until then they read as untracked,
which is correct.

## 8. What not to build

- **Writes to plan-task state.** The ledger is the plugin's; a server-side
  append would diverge darkmem's ledger from the local file and collide with
  the mirror's `expected_last_seq` reconciliation.
- **Parsing ledger bodies** for task or state. The properties are the contract;
  a ledger without them is untracked.
- **User-defined properties** (priority, tags, due dates): a second store keyed
  on row numbers and task headings that drift.
- **A materialised records table.** Same reason.
- **Calendar, timeline or gallery views, burndown, velocity.** Records carry no
  dates beyond ledger entry times.
- **Checkbox aggregation** into any count, column or percentage.
- **An MCP tool** for the board or its views.
- **Changes to the keyed REST routes** the dr-forge mirror uses.

## Invariant check

- Invariant 13: no process-local state; views are rows.
- Invariant 15: no dream job is reachable from the board.
- Invariant 17: one service module, `board.py`, behind a single REST door; the
  block-verb refusal lives in `block_verbs`, behind both its doors.
- Block firewall and work-log wall: §2.1's named memberships.
- Deployed data is durable: `board_views` is an additive revision; register
  edits go through the existing put, so every change leaves a revision.

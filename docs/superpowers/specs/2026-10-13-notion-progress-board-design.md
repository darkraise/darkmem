# A Notion-like progress board over registers and plan tasks

Date: 2026-10-13
Status: design, owner-approved section by section on 2026-10-13.
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

## Why

The Progress tab's board reads only `planning/progress.md` and T-numbered epic
files, which no current workflow produces: 306 of its 309 rows are `done`. The
work the owner now tracks arrives from dr-forge as registers, plans and plan
ledgers, and the board can show none of it. It also has no table, no saved
views and no way to move a card.

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

## 1. Records

### 1.1 Corpus

A project's board reads the documents whose uri starts with exactly
`superpowers/registers/` or `superpowers/plans/` and ends in `.md`. No
leftmost-segment matching (the plugin fixed that defect as its dr-forge
register row 13). A repository path in a cell (`docs/forge/<rest>`,
`docs/superpowers/<rest>`, optionally backticked) is normalised to the uri
`superpowers/<rest>` wherever the board resolves a cell to a document.

### 1.2 Register rows

The parser follows `plugins/dr-forge/scripts/lib/register.sh` rule for rule:

- lines inside code fences are skipped;
- `\|` is unescaped after splitting, so a cell may contain a pipe;
- the header row (`#` in the first cell) and the separator row are skipped;
- a row is well formed when it has exactly six cells and a numeric `#`. Any
  other table line is listed as **malformed** on its register with its line
  number, never dropped silently.

A row carries `#`, Item (its title), Assigned, Acceptance, State and Note; its
register carries its `# ` title, its `**Covers:**` value and the document's
`content_hash`.

States are `open planned doing verify done deferred n/a`. Any other value keeps
its raw text and lands in **unrecognised**; no committed row does today.
`verify`, `deferred` and `n/a` require a Note, as
`REGISTER_NOTE_REQUIRED` does.

**Plan progress** (derived): when Assigned resolves to exactly one plan
document in the project, the row shows "*d* of *n* done", counting that plan's
tasks whose ledger state (§1.3) is `done`. Assigned text naming another
project ("darkraise-ai-plugins: docs/…") stays plain text.

### 1.3 Plan tasks

Each `### Task N: <title>` heading outside a fence in a plan document is a task.
Its `- [ ]` steps are shown only in the task's detail, labelled as the
implementer's checklist, never counted.

- **Workstream:** the project's workstream whose `properties.plan_uri` equals
  the plan's uri (the plugin writes the darkmem uri, `superpowers/plans/<slug>.md`).
- **State:** the `state` property of the newest (highest `seq`) `ledger` entry
  in that workstream whose `properties.task` is the JSON integer N and which
  carries `state`. Lines with a task but no state (minors, parked items,
  rulings) never move it. Values are `wip review blocked done`; any other lands
  in **unrecognised**.
- **untracked:** the plan has no workstream. Its tasks have no evidence either
  way and are hidden by default; showing them as `todo` would report finished
  work as unstarted.
- **todo:** the plan has a workstream and the task has no state-bearing entry.
- **Blocked reason:** when the state is `blocked`, the body of the entry that
  set it.
- **Commit:** the newest `commit` property among the task's entries.
- **Last activity:** `created_at` of the task's newest entry of any kind.
- **Orphan:** a ledger task number with no heading in the plan is listed on the
  plan.
- A `task` that is not a JSON integer is ignored.

The pieces of a split long ledger line carry the same properties, so the
newest-entry rule reads them as one.

Nothing is stored: every read derives the records from documents and entries.

## 2. Backend

### 2.1 `app/services/board.py`

- `parse_register(text)`, `parse_plan(text)` and
  `rewrite_register_row(text, number, changes)` are pure: text in, records or
  text out.
- `load_board(session, project)` runs three queries: the corpus documents (id,
  uri, title, content, content_hash); the newest state-bearing ledger entry per
  (workstream, task) by `DISTINCT ON`; the newest entry per (workstream, task)
  of any kind, for commit and last activity. Both ledger queries filter
  `jsonb_typeof(properties->'task') = 'number'` and the project's workstreams.
- It reads `documents.content`, never `blocks`, and imports neither
  `app.services.pipeline` nor any vault module. It joins the subjects of
  `tests/test_block_retrieval.py`'s scans and the work-log wall (work-log spec
  §7): no retrieval-fusion or vault-minting closure may reach it.

### 2.2 Routes (`api/routes/board.py`)

REST-only behind login: no MCP tool, no scope, and a `dmk_` key is refused
(401). Recorded as `board.*` single-door rows in `docs/two-door-parity.md` and
classified in `app/services/content_surfaces.py`'s inventory.

- `GET /api/v1/board/records?project=` — registers (rows, malformed rows,
  title, covers, `content_hash`, a per-register parse error if any) and plans
  (workstream id, key and state, `spec_uri`, tasks, orphans, a per-plan parse
  error if any). The frontend flattens them into records.
- `PATCH /api/v1/board/registers/{document_id}/rows/{number}` with
  `{expected_hash, state?, note?, assigned?}` (at least one change). The
  service reads the document, refuses when its hash differs from
  `expected_hash`, rewrites the one row and files the result through
  `document_door.put_document` with the same `expected_hash`, `actor` set to
  the login, and the document's existing title, source type and properties
  passed through unchanged (a put writes properties wholesale). The put takes
  the row lock and the compare-and-set, writes the revision and journals its
  usual `document_filed` event. Answers 200 with the row and the new
  `content_hash`; 409 `hash_conflict` for a stale hash; 409
  `direction_conflict` for a block-first register; 404 for an unknown row, or
  a document that is not under `superpowers/registers/` in a project; 422 for an unknown state, a note-required state with an empty Note, a
  newline in any cell, or a malformed target row. Refused by
  `refuse_when_read_only`, since a put re-embeds the document.
- `GET /api/v1/board/views?project=`, `POST /api/v1/board/views` (201),
  `PATCH /api/v1/board/views/{id}`, `DELETE /api/v1/board/views/{id}` (204).

### 2.3 The row rewrite

Only the target row's line changes. Its six cells are re-serialised with `|`
escaped as `\|`; every other byte of the document, including CRLF line endings
and trailing spaces, is kept. A register must never receive block verbs: the
first one would convert it to block-first, after which both this route and the
dr-forge mirror's own put are refused.

### 2.4 `board_views`

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
`layout` (`board` or `table`), `group_by`, `filters` (property, operator, values),
`sort`, `columns`, `show_untracked`. Property names come from the fixed list
of §1 (type, title, state, source document, note, number, assigned,
acceptance, plan progress, plan, spec, workstream state, commit, last
activity); operators are `in`, `not_in` and `contains`. `group_by` takes only
the single-value properties type, state, source document, assigned, plan and
workstream state.

**Built-in views are code constants, not rows**, served first by the list
route. There are exactly two: `builtin:open-register-items` (board, register
rows grouped by state, `done` and `n/a` hidden) and `builtin:plans-in-flight`
(board, plan tasks of open workstreams grouped by plan, untracked hidden).
They are neither editable nor deletable; duplicating one is
how it is customised. Views journal nothing: they are layout, not data.

## 3. Frontend

`features/board/` replaces `features/progress/`. The old parsers, gates, the
startable filter, cards, detail and their tests are deleted, with the
`planning/progress.md` and `planning/tasks/` conventions. The Progress tab
keeps the 2026-09-28 layout: board on top, Work log beneath. The `personal`
project shows no board (owner ruling: its documents are visible nowhere in the
SPA); the route still serves it, as every document route does.

- **Toolbar.** View tabs (built-ins, then saved views); the current view's id
  in the URL (`?view=`); a Board/Table switch; group-by; a multi-select per
  filterable property (type, state, source document, assigned, plan, workstream
  state) plus a text match over title and note; a show-untracked switch; save
  as view, rename and delete (saved views only).
- **Board.** Grouping by State splits into one swimlane per type, each across
  its own vocabulary plus its unrecognised column (and untracked for plan
  tasks, when shown); two vocabularies never share columns. Any other grouping
  (type, source document, assigned, plan, workstream state) mixes types in
  shared columns.
- **Cards.** Type badge, title, `#` or Task N, source document's short name. A
  register card adds Assigned and plan progress, and shows its Note when in
  `verify`, `deferred` or `n/a`. A plan-task card adds the commit and last
  activity, and its blocked reason (§1.3) when `blocked`.
- **Dragging** (`@dnd-kit/core`): register cards only, within the register
  swimlane of a State grouping. Pessimistic: the card shows pending until the
  PATCH answers. A drop into `verify`, `deferred` or `n/a` opens a dialog
  holding the current Note, its confirm disabled while the Note is empty. A
  409 reloads the records and shows a toast that the register changed since it
  was loaded. Plan-task cards show a lock: "state comes from the plan's ledger".
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
  filter. Client-side only; no route changes.
- **Refresh and demo.** Records refetch every 10 s while the tab is visible.
  Every new hook carries `enabled: !DEMO`, with demo fixtures for records and
  views.

## 4. Rulings changed

Each old spec gets an "Amended 2026-10-13" note at the section affected.

- **Work-log spec §11** ("a task model, statuses per task, dependencies: still
  rejected") is narrowed, not reversed: darkmem has no task table, no
  server-side writer of a plan task's state and no dependencies. The board
  reads the `task`/`state` properties the client already sends.
- **Progress-board spec §4** ("no writes") is reversed for register rows only.
  This is the write-through §4 named as its follow-up; the write lands as a
  darkmem document revision, and the dr-forge mirror carries it to the
  repository.
- **Progress-board spec §7**: no second status vocabulary and no mapping onto
  a generic kanban set — kept, each type keeps its own format's vocabulary. No
  burndown or velocity — kept. No checkbox aggregation — kept. No new backend
  route — reversed by ruling 6.
- **Progress-board spec §2.1** (checkboxes are never progress) holds.

`CLAUDE.md` gains a short Board section (projection, no store; register edits
only through `put_document` with `expected_hash`; never block verbs on a
register). `docs/two-door-parity.md`'s headline counts move with the new
rows.

## 5. Failure handling

- A register or plan that fails to parse reports its error on its own source
  group; the rest of the board renders.
- A plan with no `### Task` headings is a plan with no tasks.
- A board edit racing a local edit of the same register: whichever writes
  second meets a hash conflict — the board answers 409 and reloads; the
  mirror's push gets `hash_conflict` and follows the plugin's conflict
  handling. Nothing is overwritten on either side.
- A block-first register is read normally and refused for edits
  (`direction_conflict`); its cards say why.
- Ledger values outside the contract are ignored (non-integer `task`) or
  surfaced as unrecognised (unknown `state`), never coerced.

## 6. Testing

- **Parsers, against the committed files.** Assertions are relationships, not
  pinned counts, so a new register row breaks nothing: every line outside a
  fence matching `^\| *[0-9]+ *\|` is a parsed or a malformed row; every
  `### Task N:` heading outside a fence across the plans is a parsed task;
  the work-log register's row 66, whose Item holds an escaped `\|`, parses
  as one well-formed `deferred` row (a split on bare `|` misreads it).
- **Rewrite property test** over every row of every committed register:
  changing a state and changing it back reproduces the original bytes; the
  changed text differs from the original in exactly one line. Cases for an
  escaped pipe, CRLF, trailing spaces and a Note containing `|`.
- **Ledger derivation**, with fixtures copied from real dr-forge ledger lines:
  newest state-bearing entry wins; stateless task lines do not move it; split
  pieces agree; untracked, todo and orphan; non-integer task ignored.
- **Routes:** REST conformance (PATCH, 201, 204); each 409, 404 and 422 case;
  a successful edit writes exactly one revision carrying the actor; read-only
  refusal; a `dmk_` key gets 401; content-surface classification; the wall
  scans include `board.py`, each with a negative control; the guards leg from
  `CLAUDE.md`.
- **Migration:** the `board_views` revision runs against a restored backup
  holding data, not only the empty test schema.
- **Frontend:** vitest for State swimlanes, register-only dragging, the note
  dialog, the 409 toast, table edits, saving a view and duplicating a built-in,
  and the Work log badges and task filter; `npm run typecheck`; `npm run
  build`. One Playwright spec drags a card, run through
  `backend/scripts/e2e/run_playwright_e2e.py`, never bare.

## 7. Sequencing

Each increment lands green before the next.

| # | Increment | Depends on |
|---|---|---|
| 1 | Parsers and row rewriter, with their golden and property tests; no routes | — |
| 2 | `load_board`, the ledger joins and the records route; wall scans | 1 |
| 3 | `board_views` revision and its four routes | — |
| 4 | The register-row edit route | 1, 2 |
| 5 | Board, table, views, detail sheet, Work log badges and filter, demo fixtures; old board deleted | 2, 3, 4 |
| 6 | Deploy to this host; the owner reviews the board and the Work log UI together | 5 |

Increment 1 is worth landing alone: if the parser cannot hold the committed
registers and plans, that is the finding, before anything is built on it.

**Done means:** increment 6 deployed and confirmed in the running image, and
the owner's review recorded; register rows 85 and 1 close on it.

## 8. What not to build

- **Writes to plan-task state.** The ledger is the plugin's; a server-side
  append would diverge darkmem's ledger from the local file and collide with
  the mirror's `expected_last_seq` reconciliation.
- **User-defined properties** (priority, tags, due dates): a second store keyed
  on row numbers and task headings that drift.
- **A materialised records table.** Same reason.
- **Calendar, timeline or gallery views, burndown, velocity.** Records carry no
  dates beyond ledger entry times.
- **Checkbox aggregation** into any count, column or percentage.
- **Block verbs on a register**, from the board or any helper.
- **An MCP tool** for the board or its views.
- **Changes to the keyed REST routes** the dr-forge mirror uses.

## Invariant check

- Invariant 13: no process-local state; views are rows.
- Invariant 15: no dream job is reachable from the board.
- Invariant 17: one service module, `board.py`, behind a single REST door.
- Block firewall and work-log wall: `board.py` reads document content and
  ledger rows; nothing in retrieval fusion or the vault reaches it (§2.1).
- Deployed data is durable: `board_views` is an additive revision; register
  edits go through the existing put, so every change leaves a revision.

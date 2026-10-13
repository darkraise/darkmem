# Notion-like Progress Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Progress tab's T-epic board with a board and table over register rows and plan tasks, with saved views, register rows editable through a hash-guarded document put, plan tasks read-only from ledger entry properties, and the Work log's owed task badges and filter.

**Architecture:** A server-side projection, never a store: `board_parse` (pure parsers mirroring dr-forge's `plan.sh` / `register.sh`), `board` (reads `documents.content` and `worklog_entries` on every request, ETag from aggregates), `board_edit` (one register row spliced and filed through `put_document` with `expected_hash` and no inline embed) and `board_views` (one additive table) behind six REST-only login routes. The SPA's `features/board/` flattens the records and renders a dnd-kit board, a darkraise-ui table, a detail sheet and saved views; `features/progress/` is deleted.

**Tech Stack:** FastAPI, SQLAlchemy async (raw SQL), Alembic, PostgreSQL 17; React 19, TanStack Query and Router, darkraise-ui, @dnd-kit/core, vitest on happy-dom, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-13-notion-progress-board-design.md`

**Execution:** inline — `claude --model sonnet --effort high` — 5 of 24 tasks are heavy (Tasks 2, 3, 7, 9 and 24, by total 5+ or risk 3) and are delegated; the rest total 4 or less.

**Plan review:** 2026-10-13 — dr-superpowers:judge-opus — executability 16 / coherence 17 / coverage 18 / assumptions 15 (round 1); its three Important and six Minor findings are fixed in this text.

**Parallelism:** sequential — the spec's execution strategy: every later part consumes the parser and the row rewrite, which carry the one data-loss risk and land first, and the frontend's checks need the live routes.

## Global Constraints

- **The spec is the authority**, as amended with this plan (2026-10-13): `board.py` reads, `board_edit.py` writes, `board_parse.py` is pure; refusals are `BoardRefusal` answered as `error.code`; the row PATCH is not behind `refuse_when_read_only`.
- **Deployed data is durable.** The only schema change is the additive revision `0003` with `down_revision = '0002'`. Never edit `backend/migrations/versions/0001_baseline.py`.
- **Python** is `backend/.venv/bin/python` (there is no `python` on PATH). Every backend test command names `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2`, the lane database; `darkmem_test` is the controller's and the Playwright runner resets it. Never point a test at production (`:5432`).
- **A parametrize id must be identical across pytest-xdist workers**: never build one from `uuid.uuid4()` or the clock.
- **Frontend**: run `npm ci` once in `frontend/` per worktree. `tsc -b` rejects `Array.prototype.at`. Never run `prettier --write` on an existing file (the frontend is not prettier-clean); only files a task creates may be formatted. UI components come from darkraise-ui (`table`, `sheet`, `dialog`, `alert-dialog`, `select`, `multi-select`, `editable`, `switch`, `toggle-group`, `tabs`, `sonner`). Every new hook carries `enabled: !DEMO` and demo `initialData`; every mutation rejects in demo mode without a request.
- **The demo-import floor** in `frontend/src/__tests__/no-restricted-imports-count.test.ts` is two-sided: Task 13 moves it to 113 and Task 18 to 114, each with a one-line re-measurement note. Any other move is a defect in the task that caused it.
- **No route the dr-forge mirror uses changes** (the keyed document routes are a fixed contract). No MCP tool is added.
- **Never run Playwright bare** (`npx playwright test` points `/api` at production on `:8000`); use `backend/scripts/e2e/run_playwright_e2e.py`.
- **Never push** the branch or an image. Build with `DARKMEM_PUSH=0`. A push to master releases.
- **Commits**: `<type>(<scope>): <subject>`, subject ≤ 50 characters, imperative, no attribution trailers of any kind.
- **Exit 143 is the earlyoom kill, not a failure**: check `free -h` and re-run the leg before believing a red.
- **Code comments** say why, never what, and never name the task or the plan.

## Contracts

**Backend parsers** (`backend/app/services/board_parse.py`, no app imports):
- `REGISTER_PREFIX = "superpowers/registers/"`, `PLAN_PREFIX = "superpowers/plans/"`, `BOARD_SOURCE_PREFIXES = (REGISTER_PREFIX, PLAN_PREFIX)`.
- `REGISTER_STATES = ("open", "planned", "doing", "verify", "done", "deferred", "n/a")`; `NOTE_REQUIRED_STATES = {"verify", "deferred", "n/a"}`; `TASK_STATES = ("todo", "wip", "review", "blocked", "done")`; `LEDGER_STATES = {"wip", "review", "blocked", "done"}`.
- `is_board_source(uri) -> bool` (prefix and `.md`), `is_mirror_owned(uri) -> bool` (prefix only), `is_blank_note(note) -> bool` (empty or `-` after trimming), `cell_uri(cell) -> str | None` (`docs/superpowers/<rest>` or `docs/forge/<rest>`, optionally backticked, to `superpowers/<rest>`), `split_lines(text)`, `fence_flags(lines)`.
- `parse_register(text) -> ParsedRegister(title, covers, rows: list[RegisterRow], malformed: list[MalformedRow])`; `RegisterRow(number, item, assigned, acceptance, state, note, line)` with `.state_recognised`; `MalformedRow(line, text, reason, number)`.
- `parse_plan(text) -> ParsedPlan(title, tasks: list[PlanTask])`; `PlanTask(number, label, title, line, steps: list[TaskStep])`; `TaskStep(checked, text)`.
- `rewrite_register_row(text, number, changes: dict[str, str]) -> str`, `changes` keys ⊆ `EDITABLE_COLUMNS = {"state", "note", "assigned"}`; raises `RowEditRefused(reason, message)`, reasons `not_found`, `duplicate_row`, `malformed_row`, `unknown_state`, `note_required`, `invalid_cell`.

**Refusals**: `BoardRefusal(status_code: int, reason: str, message: str, **fields)` in `board_parse`; attributes `status_code`, `reason`, `message`, `fields`. `app/main.py` answers it as `_error_response(status_code, reason, message, [fields] or None)`: body `{"error": {"code": reason, "message": message, "details": [fields] | null}, "detail": message}`.

**Document door**: `put_document(..., embed_inline: bool = True)`; with `False` it returns after the commit with `blocks_embedded == 0`, and `llm` may be `None`. `DocumentMirrorOwned(DocumentNotConvertible)` is raised by every block verb on a document whose uri `is_mirror_owned`.

**Records** (`backend/app/services/board.py`): `load_board(session, project) -> {"project", "registers", "plans"}`; `board_version(session, project) -> str`; `BLOCK_FIRST = "blocks"`. A register: `document_id, uri, title, covers, content_hash, block_first, rows, malformed, error`; a row: `number, item, assigned, acceptance, state` (`unrecognised` outside the vocabulary)`, raw_state, note, note_blank, line, plan_uri, plan_progress {done, total, untracked}`. A plan: `document_id, uri, title, content_hash, workstream {id, key, state} | null, other_workstreams, spec_uri, untracked` (`no_workstream` | `no_properties` | null)`, tasks, orphans, error`; a task: `number, label, title, line, state` (`todo wip review blocked done untracked unrecognised`)`, raw_state, untracked, shared_number, blocked_reason, commit, last_activity, steps`.

**Edit service** (`backend/app/services/board_edit.py`): `edit_register_row(session, *, document_id: str, number: int, expected_hash: str, changes: dict[str, str], actor: str) -> {"document_id", "content_hash", "row"}`.

**Views** (`backend/app/services/board_views.py`): `PROPERTIES` (the 14 of spec §1.5), `GROUPABLE = ("type", "state", "source", "assigned", "plan", "workstream_state")`, `BUILTIN_VIEWS` (`builtin:open-register-items`, `builtin:plans-in-flight`), `ViewDefinition {layout: board|table, group_by: GROUPABLE|null, filters: [{property, operator: in|not_in|contains, values}], sort: {property, direction: asc|desc}|null, columns: [property], show_untracked: bool}`, `validate_definition`, `list_views(session, project)`, `create_view(session, *, project, name, definition, position)`, `update_view(session, view_id, *, changes)`, `delete_view(session, view_id)`. Table `board_views(id, project, name, position, definition, created_at, updated_at)`, `UNIQUE (project, name)`.

**REST** (login only, `require_auth`; a `dmk_` key answers 401):
- `GET /api/v1/board/records?project=` → `BoardRecordsResponse`, `ETag: W/"<board_version>"`, `Cache-Control: private, no-cache`; 304 on a matching `If-None-Match`.
- `PATCH /api/v1/board/registers/{document_id}/rows/{number}` body `{expected_hash, state?, note?, assigned?}` (extra fields refused) → 200 `{document_id, content_hash, row}`; refusals 404 `not_found`, 409 `hash_conflict` (details `[{current_hash}]`), 409 `block_first`, 422 `duplicate_row` `malformed_row` `unknown_state` `note_required` `invalid_cell` `no_change`.
- `GET /api/v1/board/views?project=` → built-ins then saved views by `(position, name)`; `POST /api/v1/board/views` `{project, name, definition, position?}` → 201; `PATCH /api/v1/board/views/{view_id}` `{name?, definition?, position?}` → 200; `DELETE /api/v1/board/views/{view_id}` → 204; refusals 404 `not_found`, 409 `name_taken`, 422 `builtin_view`, `invalid_definition`, `no_change`.

**Frontend**:
- `ApiError(message, status, details?, code?)` with `.code`.
- `frontend/src/hooks/api/use-board-api.ts`: types mirroring the REST shapes (`BoardRecords`, `BoardRegister`, `BoardRegisterRow`, `BoardPlan`, `PlanTask`, `TaskStep`, `PlanProgress`, `Untracked`, `BoardProperty`, `GroupableProperty`, `ViewFilter`, `ViewDefinition`, `BoardView`, `RowChanges`, `RowEditResult`); hooks `useBoardRecords(project)` (key `["boardRecords", project]`, refetch every `BOARD_REFRESH_MS = 10_000`), `useBoardViews(project)` (key `["boardViews", project]`), `useRegisterRowEdit(project)` (variables `{documentId, number, expectedHash, state?, note?, assigned?}`), `useCreateBoardView(project)` (variables `{name, definition}`), `useUpdateBoardView(project)` (variables `{id, name?, definition?}`), `useDeleteBoardView(project)` (variable: the view id).
- `frontend/src/demo/board.ts`: `demoBoardRecords(project)`, `DEMO_BOARD_VIEWS`.
- `frontend/src/features/board/lib/records.ts`: `BoardRecord` (id `r:<document_id>:<number>` or `t:<document_id>:<line>`), `flattenRecords`, `applyView(records, definition, text)`, `boardLanes(records, groupBy, showUntracked) -> BoardLane[]`, `planMove(record, toState) -> "locked" | "noop" | "note" | "patch"`, `propertyValue`, `formatProgress`, `isBlankNote`, `shortName`, `PROPERTIES`, `PROPERTY_LABELS`, `GROUPABLE`, `REGISTER_STATES`, `TASK_STATES`, `NOTE_REQUIRED`, `UNTRACKED_LABEL`.
- `frontend/src/features/board/use-row-editor.ts`: `useRowEditor(project) -> RowEditor {save, move, prompt, confirmPrompt, cancelPrompt, pendingId}`, `NotePrompt`, `CONFLICT_MESSAGE`.
- Components in `frontend/src/features/board/components/`: `NoteDialog`, `RecordCard` + `LEDGER_LOCK = "state comes from the plan's ledger"`, `BoardView` + `dropTarget` + `DROP_PREFIX = "state:"`, `RecordsTable` + `displayValue`, `RecordDetailSheet`, `BoardToolbar` + `withInFilter`, `ViewNameDialog`, `BoardPanel({project, viewId, onViewChange, onOpenDocument, onShowInWorkLog})` + `DEFAULT_VIEW = "builtin:open-register-items"` + `sourceNotes(records) -> string[]` (parse errors, malformed rows, other workstreams naming a plan, orphan task numbers).
- Test fixture `frontend/src/features/board/__tests__/fixtures.ts`: `RECORDS`.
- `useAllLedgerEntries(workstreamId, enabled)` (key `["worklogLedgerAll", id]`, `LEDGER_PAGE = 500` per page); `EntryTimeline` prop `initialTask?: number`; `WorkLogPanel` prop `initialTask?: number`; `entryTask(entry)`.
- `frontend/src/lib/mirror-owned.ts`: `isMirrorOwned(uri)`, `MIRROR_OWNED_PREFIXES`.
- `ProjectWorkspace` props `view?: string`, `onViewChange?: (view: string) => void`; route search param `view`.

## Assumptions (evidence)

- Every code block in this plan ran on 2026-10-13 in a scratch tree of this branch before the plan was written: backend 8435 passed, 26 skipped (`pytest -n 4`); frontend 2202 passed, `tsc -b` and `npm run build` clean; the Playwright spec 5 passed through the runner. The generator that wrote this plan replayed every edit against HEAD `386e23e6` and compared the result with that tree byte for byte (only `CLAUDE.md` and the regenerated parity table were excluded).
- The parsers agree with dr-forge: task numbers equal `plan_tasks` (`darkraise-ai-plugins/plugins/dr-forge/scripts/lib/plan.sh`) on all 114 committed plans, 0 differences; all 128 committed register rows parse with 0 malformed and round-trip byte for byte (2026-10-13).
- `document_door`'s import closure reaches `app.repositories.relational`, which imports a memory model, so `test_no_work_log_module_imports_a_memory_model` fails for any work-log member importing the door (observed 2026-10-13); hence the read/edit split.
- The dev Postgres (`darkmem-postgres-1`, `:5433`) was up with `darkmem_test`, `darkmem_test_2` to `_5` and `darkmem_bench` (`psql`, 2026-10-13). The backend `.venv` and `frontend/node_modules` were absent on the primary checkout until built in this session; Task 1 and Task 11 build them when absent.
- Playwright's chromium revision 1223 was missing and was installed on 2026-10-13 (`npx playwright install chromium-headless-shell chromium`).
- The browser revalidates a `Cache-Control: no-cache` response carrying an `ETag` by itself, sending `If-None-Match` (Fetch standard, request cache mode "default": https://fetch.spec.whatwg.org/#concept-request-cache-mode); the hooks send no header.
- This host's production database held 0 memories and 21 MB at revision `0001`, in an image from 2026-10-03 (`docker ps`, `psql`, 2026-10-13); the real corpus is on 192.168.0.199. The newest local dump (2026-10-08) upgraded `0001 -> 0002 -> 0003` keeping its 994 events and 37 config rows.
- `/root/repositories/darkmem/.env` was missing on 2026-10-13 and the nightly backup has failed since 2026-10-09 on `DB_PASSWORD`; Task 24 stops BLOCKED until the owner restores it. unverified — Task 24 Step 1 verifies it.
- The Codex executor gate answered `lane=false reason=plugin-not-enabled` (2026-10-13), so no task carries an `**Executor:**` line.
- Task 24 deploys this branch before it merges, so the owner reviews the live board (spec §7 increment 6; `CLAUDE.md`'s deploy ruling of 2026-08-21). That stamps production `0003` ahead of master; the plan's ruling is that the branch merges before any other deploy to this host, and Task 24 checks master's head is still `0002` (`git ls-tree master backend/migrations/versions/`, 2026-10-13: `0001`, `0002`).
- `CHANGELOG.md` keeps no Unreleased section; the release cut writes the version section (its history, `git log -- CHANGELOG.md`).

## Task index

1. Register and plan parsers
2. The register row rewrite
3. `put_document` without an inline embed
4. Block verbs refuse registers and plans
5. The board read service
6. The records route
7. The register row edit service
8. The register row edit route
9. The `board_views` table and its service
10. The saved-view routes
11. `ApiError` carries the envelope's code
12. Board types and the records library
13. Board hooks and demo fixtures
14. The row editor and the Note dialog
15. The board view and its cards
16. The table and the detail sheet
17. The toolbar and the view-name dialog
18. The board panel and saved views
19. Work log badges and the paging task filter
20. No edit mode for registers and plans
21. Mount the board in the Progress tab and retire the old one
22. A real drag, end to end
23. Record the board in `CLAUDE.md`
24. Deploy and the owner's review

---

### Task 1: Register and plan parsers

**Files:**
- Create: `backend/app/services/board_parse.py`
- Test: `backend/tests/test_board_parse.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `board_parse` constants and parsers (Contracts §Backend parsers): `REGISTER_PREFIX`, `PLAN_PREFIX`, `BOARD_SOURCE_PREFIXES`, `REGISTER_STATES`, `NOTE_REQUIRED_STATES`, `TASK_STATES`, `LEDGER_STATES`, `is_board_source`, `is_mirror_owned`, `is_blank_note`, `cell_uri`, `split_lines`, `fence_flags`, `parse_register` → `ParsedRegister`, `parse_plan` → `ParsedPlan`.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: Prepare the environment (once per worktree)**

The backend venv and the dev Postgres are prerequisites of every backend task. Skip a line whose check already passes.

````bash
test -x backend/.venv/bin/python || (cd backend && uv venv .venv --python 3.13 \
  && uv pip install --python .venv/bin/python -r requirements.lock \
  && uv pip install --python .venv/bin/python --no-deps -e . \
  && uv pip install --python .venv/bin/python pytest pytest-asyncio pytest-xdist)
docker ps --format '{{.Names}}' | grep -qx darkmem-postgres-1 || docker compose -f docker-compose.dev.yml up -d postgres
docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -Atc "SELECT datname FROM pg_database WHERE datname = 'darkmem_test_2'"
````

Expected: the last command prints `darkmem_test_2`. If it prints nothing, create it: `docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -c "CREATE DATABASE darkmem_test_2;"`.

- [ ] **Step 2: Write the failing tests**

The corpus tests assert relationships against the committed registers and plans, never pinned counts, so a new register row breaks nothing (spec §6).

Create `backend/tests/test_board_parse.py` with:

````python
"""The board's pure parsers and row rewrite (spec 2026-10-13 §1.2-§1.4, §2.3, §6)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services.board_parse import (
    cell_uri,
    fence_flags,
    is_blank_note,
    is_board_source,
    is_mirror_owned,
    parse_plan,
    parse_register,
    split_lines,
)

REPO = Path(__file__).resolve().parents[2]
REGISTERS = sorted((REPO / "docs" / "superpowers" / "registers").glob("*.md"))
PLANS = sorted((REPO / "docs" / "superpowers" / "plans").glob("*.md"))
_IS_TASK = re.compile(r"^#+[ \t]+Task[ \t]+[0-9]+")

HEADER = "| # | Item | Assigned | Acceptance | State | Note |\n|---|---|---|---|---|---|\n"


def _register(*rows: str) -> str:
    return "# Register — fixture\n\n**Covers:** docs/superpowers/specs/x.md\n\n" + HEADER + "".join(
        row + "\n" for row in rows
    )


def _first_cell(line: str) -> str | None:
    trimmed = line.strip(" \t")
    if not trimmed.startswith("|"):
        return None
    fields = trimmed.replace("\\|", "\x01").split("|")
    return fields[1].strip(" \t") if len(fields) > 1 else ""


# --- the committed corpus -------------------------------------------------

def test_the_corpus_is_there():
    assert len(REGISTERS) >= 3 and len(PLANS) >= 100


@pytest.mark.parametrize("path", REGISTERS, ids=lambda p: p.name)
def test_every_numbered_table_line_is_a_row_or_listed_malformed(path):
    text = path.read_text(encoding="utf-8")
    parsed = parse_register(text)
    accounted = {r.line for r in parsed.rows} | {m.line for m in parsed.malformed}
    lines = split_lines(text)
    for index, (line, fenced) in enumerate(zip(lines, fence_flags(lines))):
        first = None if fenced else _first_cell(line)
        if first is not None and first.isdigit():
            assert index + 1 in accounted, f"{path.name}:{index + 1} was dropped"


@pytest.mark.parametrize("path", PLANS, ids=lambda p: p.name)
def test_every_task_heading_outside_a_fence_is_a_task(path):
    text = path.read_text(encoding="utf-8")
    lines = split_lines(text)
    expected = [
        i + 1 for i, (line, fenced) in enumerate(zip(lines, fence_flags(lines)))
        if not fenced and _IS_TASK.match(line)
    ]
    assert [t.line for t in parse_plan(text).tasks] == expected


def test_row_66_keeps_its_escaped_pipe():
    text = (REPO / "docs/superpowers/registers/2026-09-23-work-log-lane.md").read_text(encoding="utf-8")
    row = next(r for r in parse_register(text).rows if r.number == 66)
    assert row.item == (
        "Task 4: frontend apiFetch<CaptureAck | Memory>'s Memory-typed 201 "
        "union arm has no warnings field"
    )
    assert row.state == "deferred"


# --- text rules -----------------------------------------------------------

def test_lines_split_on_newline_only_and_drop_carriage_returns():
    assert split_lines("a\r\nb c\x0cd\n") == ["a", "b c\x0cd", ""]


@pytest.mark.parametrize("text, fenced_lines", [
    ("````\n```\n### Task 1: hidden\n```\n````\n### Task 2: shown\n", [1, 2, 3, 4, 5]),
    ("~~~\n### Task 1: hidden\n~~~\n### Task 2: shown\n", [1, 2, 3]),
    ("   ```\n### Task 1: hidden\n   ```\n### Task 2: shown\n", [1, 2, 3]),
    ("    ```\n### Task 1: indented four is no fence\n", []),
    ("```\n~~~\n### Task 1: hidden\n```\n", [1, 2, 3, 4]),
    ("```\n### Task 1: still fenced\n``\n", [1, 2, 3, 4]),
])
def test_fences_follow_plan_sh(text, fenced_lines):
    flags = fence_flags(split_lines(text))
    assert [i + 1 for i, f in enumerate(flags) if f] == fenced_lines


# --- registers ------------------------------------------------------------

def test_a_register_carries_title_covers_and_rows():
    parsed = parse_register(_register("| 1 | Item | - | - | open | - |"))
    assert parsed.title == "Register — fixture"
    assert parsed.covers == "docs/superpowers/specs/x.md"
    row = parsed.rows[0]
    assert (row.number, row.item, row.state, row.note, row.line) == (1, "Item", "open", "-", 7)


def test_duplicate_numbers_are_both_malformed_and_neither_a_record():
    parsed = parse_register(_register(
        "| 4 | a | - | - | open | - |", "| 4 | b | - | - | done | - |",
    ))
    assert parsed.rows == []
    assert [m.reason for m in parsed.malformed] == ["duplicate number 4"] * 2
    assert [m.number for m in parsed.malformed] == [4, 4]


def test_a_wrong_cell_count_and_a_non_numeric_number_are_malformed():
    parsed = parse_register(_register("| 5 | a | - | open | - |", "| x | a | - | - | open | - |"))
    assert [(m.line, m.number) for m in parsed.malformed] == [(7, 5), (8, None)]


def test_a_cell_may_hold_an_escaped_pipe_and_a_line_separator():
    parsed = parse_register(_register("| 7 | a \\| b | - | - | open | x y |"))
    assert parsed.rows[0].item == "a | b"
    assert parsed.rows[0].note == "x y"


def test_an_unknown_state_keeps_its_text():
    row = parse_register(_register("| 1 | a | - | - | parked | - |")).rows[0]
    assert row.state == "parked" and not row.state_recognised


@pytest.mark.parametrize("note, blank", [("", True), ("-", True), ("  -  ", True), ("why", False)])
def test_blank_notes(note, blank):
    assert is_blank_note(note) is blank


@pytest.mark.parametrize("cell, uri", [
    ("docs/superpowers/plans/a.md", "superpowers/plans/a.md"),
    ("`docs/forge/plans/a.md`", "superpowers/plans/a.md"),
    ("superpowers/plans/a.md", "superpowers/plans/a.md"),
    ("darkraise-ai-plugins: docs/superpowers/plans/a.md", None),
    ("-", None),
    ("", None),
])
def test_cell_uri(cell, uri):
    assert cell_uri(cell) == uri


def test_source_predicates():
    assert is_board_source("superpowers/registers/a.md")
    assert not is_board_source("superpowers/registers/a.txt")
    assert not is_board_source("notes/superpowers/plans/a.md")
    assert is_mirror_owned("superpowers/plans/a.txt")
    assert not is_mirror_owned("superpowers/specs/a.md")


# --- plans ----------------------------------------------------------------

def test_task_headings_numbers_labels_and_titles():
    text = (
        "# Plan\n\n## Task 1: One\n\n#### Task 5a - Five a\n\n### Task 7. Seven\n\n"
        "### Task 8\n\n### Taskless heading\n"
    )
    tasks = parse_plan(text).tasks
    assert [(t.number, t.label, t.title) for t in tasks] == [
        (1, "Task 1: One", "One"),
        (5, "Task 5a - Five a", "Five a"),
        (7, "Task 7. Seven", "Seven"),
        (8, "Task 8", ""),
    ]
    assert parse_plan(text).title == "Plan"


def test_steps_belong_to_their_task_and_fenced_steps_are_skipped():
    text = "### Task 1: A\n- [ ] one\n```\n- [ ] fenced\n```\n- [x] two\n### Task 2: B\n- [ ] three\n"
    first, second = parse_plan(text).tasks
    assert [(s.checked, s.text) for s in first.steps] == [(False, "one"), (True, "two")]
    assert [s.text for s in second.steps] == ["three"]


def test_a_plan_without_headings_has_no_tasks():
    assert parse_plan("# Notes\n\nNothing here.\n").tasks == []
````

- [ ] **Step 3: Run them to see them fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_board_parse.py`
Expected: collection error, `ModuleNotFoundError: No module named 'app.services.board_parse'`

- [ ] **Step 4: Write the parsers**

The fence rule, the task-heading rule and the cell split mirror dr-forge's `plugins/dr-forge/scripts/lib/plan.sh` and `lib/register.sh` exactly (verified 2026-10-13: task numbers equal the plugin's `plan_tasks` on all 114 committed plans). Do not "simplify" `split_lines` to `str.splitlines()`.

Create `backend/app/services/board_parse.py` with:

````python
"""Pure parsers for the progress board: registers, plans and the row rewrite.

They mirror dr-forge's shell parsers (`scripts/lib/plan.sh`, `lib/register.sh`)
so the board and the plugin agree on what a row, a task and a fence are. Text
in, records or text out: no database, no app imports, so `block_verbs` can
import the uri prefixes without reaching the board service.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

REGISTER_PREFIX = "superpowers/registers/"
PLAN_PREFIX = "superpowers/plans/"
BOARD_SOURCE_PREFIXES = (REGISTER_PREFIX, PLAN_PREFIX)

REGISTER_STATES = ("open", "planned", "doing", "verify", "done", "deferred", "n/a")
NOTE_REQUIRED_STATES = frozenset({"verify", "deferred", "n/a"})
TASK_STATES = ("todo", "wip", "review", "blocked", "done")
LEDGER_STATES = frozenset({"wip", "review", "blocked", "done"})

_OPENER = re.compile(r"^ {0,3}(`+|~+)")
_CLOSER_BODY = re.compile(r"`+|~+")
_TASK = re.compile(r"^#+[ \t]+(Task[ \t]+([0-9]+)[A-Za-z]*[ \t]*[:.\-]?[ \t]*(.*))$")
_STEP = re.compile(r"^[ \t]*[-*][ \t]+\[([ xX])\][ \t]+(.*)$")
_SEPARATOR = re.compile(r":?-+:?")
_DIGITS = re.compile(r"[0-9]+")
_ESCAPED_PIPE = "\x01"


def is_board_source(uri: str | None) -> bool:
    """A document the board reads: under a register or plan prefix, `.md`."""
    return bool(uri) and uri.startswith(BOARD_SOURCE_PREFIXES) and uri.endswith(".md")


def is_mirror_owned(uri: str | None) -> bool:
    """A document the dr-forge mirror owns through content puts."""
    return bool(uri) and uri.startswith(BOARD_SOURCE_PREFIXES)


def is_blank_note(note: str | None) -> bool:
    return note is None or note.strip(" \t") in ("", "-")


def cell_uri(cell: str | None) -> str | None:
    """A repository path in a cell, as the darkmem uri it was filed under."""
    if not cell:
        return None
    value = cell.strip(" \t")
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip(" \t")
    for prefix in ("docs/forge/", "docs/superpowers/"):
        if value.startswith(prefix):
            return "superpowers/" + value[len(prefix):]
    if value.startswith("superpowers/"):
        return value
    return None


def split_lines(text: str) -> list[str]:
    """Lines on `\\n` only, with every `\\r` removed, as `tr -d '\\r'` does.

    Never `str.splitlines`: it also splits on U+2028, U+000C and others, which
    would number lines differently from the plugin and break a cell apart.
    """
    return text.replace("\r", "").split("\n")


class _Fence:
    """`plan.sh`'s `in_fence`: True for fence markers and fenced lines."""

    def __init__(self) -> None:
        self.marker = ""

    def step(self, line: str) -> bool:
        if self.marker:
            body = re.sub(r"^ {0,3}", "", line, count=1).rstrip(" \t")
            if (
                _CLOSER_BODY.fullmatch(body)
                and body[0] == self.marker[0]
                and len(body) >= len(self.marker)
            ):
                self.marker = ""
            return True
        match = _OPENER.match(line)
        if match and len(match.group(1)) >= 3:
            self.marker = match.group(1)
            return True
        return False


def fence_flags(lines: list[str]) -> list[bool]:
    fence = _Fence()
    return [fence.step(line) for line in lines]


def _cells(line: str) -> list[str] | None:
    """`register.sh`'s `reg_cells`: the trimmed fields, or None off a table."""
    trimmed = line.strip(" \t")
    if not trimmed.startswith("|"):
        return None
    fields = trimmed.replace("\\|", _ESCAPED_PIPE).split("|")
    return [f.strip(" \t").replace(_ESCAPED_PIPE, "|") for f in fields]


@dataclass(frozen=True)
class RegisterRow:
    number: int
    item: str
    assigned: str
    acceptance: str
    state: str
    note: str
    line: int

    @property
    def state_recognised(self) -> bool:
        return self.state in REGISTER_STATES


@dataclass(frozen=True)
class MalformedRow:
    line: int
    text: str
    reason: str
    number: int | None


@dataclass(frozen=True)
class ParsedRegister:
    title: str | None
    covers: str | None
    rows: list[RegisterRow]
    malformed: list[MalformedRow]


def _first_title(lines: list[str], flags: list[bool]) -> str | None:
    for line, fenced in zip(lines, flags):
        if not fenced and line.startswith("# "):
            return line[2:].strip(" \t")
    return None


def parse_register(text: str) -> ParsedRegister:
    lines = split_lines(text)
    flags = fence_flags(lines)
    title = _first_title(lines, flags)
    covers = None
    candidates: list[tuple[int, list[str], str]] = []
    malformed: list[MalformedRow] = []
    for index, (line, fenced) in enumerate(zip(lines, flags)):
        if fenced:
            continue
        if covers is None and line.startswith("**Covers:**"):
            covers = line[len("**Covers:**"):].strip(" \t")
            continue
        fields = _cells(line)
        if fields is None:
            continue
        first = fields[1] if len(fields) > 1 else ""
        if first == "#" or _SEPARATOR.fullmatch(first):
            continue
        number = index + 1
        row_number = int(first) if _DIGITS.fullmatch(first) else None
        if len(fields) != 8:
            malformed.append(
                MalformedRow(number, line, f"{len(fields) - 2} cells, not 6", row_number)
            )
        elif row_number is None:
            malformed.append(MalformedRow(number, line, "the # cell is not a number", None))
        else:
            candidates.append((number, fields, line))

    counts: dict[int, int] = {}
    for _line, fields, _text in candidates:
        counts[int(fields[1])] = counts.get(int(fields[1]), 0) + 1
    rows: list[RegisterRow] = []
    for number, fields, line in candidates:
        row_number = int(fields[1])
        if counts[row_number] > 1:
            malformed.append(
                MalformedRow(number, line, f"duplicate number {row_number}", row_number)
            )
            continue
        rows.append(RegisterRow(
            number=row_number, item=fields[2], assigned=fields[3],
            acceptance=fields[4], state=fields[5], note=fields[6], line=number,
        ))
    malformed.sort(key=lambda m: m.line)
    return ParsedRegister(title=title, covers=covers, rows=rows, malformed=malformed)


@dataclass(frozen=True)
class TaskStep:
    checked: bool
    text: str


@dataclass(frozen=True)
class PlanTask:
    number: int
    label: str
    title: str
    line: int
    steps: list[TaskStep] = field(default_factory=list)


@dataclass(frozen=True)
class ParsedPlan:
    title: str | None
    tasks: list[PlanTask]


def parse_plan(text: str) -> ParsedPlan:
    lines = split_lines(text)
    flags = fence_flags(lines)
    tasks: list[PlanTask] = []
    current: dict | None = None
    for index, (line, fenced) in enumerate(zip(lines, flags)):
        if fenced:
            continue
        match = _TASK.match(line)
        if match:
            if current is not None:
                tasks.append(PlanTask(**current))
            current = {
                "number": int(match.group(2)),
                "label": match.group(1).rstrip(" \t"),
                "title": match.group(3).strip(" \t"),
                "line": index + 1,
                "steps": [],
            }
            continue
        if current is not None:
            step = _STEP.match(line)
            if step:
                current["steps"].append(
                    TaskStep(checked=step.group(1) != " ", text=step.group(2).rstrip(" \t"))
                )
    if current is not None:
        tasks.append(PlanTask(**current))
    return ParsedPlan(title=_first_title(lines, flags), tasks=tasks)

````

- [ ] **Step 5: Run the tests**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_board_parse.py`
Expected: all pass (about 120 cases: one per register and plan file plus the fixture cases)

- [ ] **Step 6: Commit**

````bash
git add backend/app/services/board_parse.py backend/tests/test_board_parse.py
git commit -m "feat(board): parse registers and plans like dr-forge"
````

---

### Task 2: The register row rewrite

**Files:**
- Modify: `backend/app/services/board_parse.py` (append)
- Test: `backend/tests/test_board_rewrite.py`

**Interfaces:**
- Consumes: Task 1's `parse_register`, `is_blank_note`, `REGISTER_STATES`, `NOTE_REQUIRED_STATES`.
- Produces: `rewrite_register_row(text, number, changes) -> str`, `RowEditRefused(reason, message)` with `.reason`, `EDITABLE_COLUMNS`, and `BoardRefusal(status_code, reason, message, **fields)` (Contracts §Backend parsers, §Refusals).

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

This is the data-loss point of the whole feature: every board edit is this splice applied to a real register. The property test runs over every row of every committed register.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_board_rewrite.py` with:

````python
"""The register row rewrite: a splice, never a re-serialisation (spec 2026-10-13 §2.3, §6)."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.board_parse import (
    NOTE_REQUIRED_STATES,
    RowEditRefused,
    is_blank_note,
    parse_register,
    rewrite_register_row,
)

REPO = Path(__file__).resolve().parents[2]
REGISTERS = sorted((REPO / "docs" / "superpowers" / "registers").glob("*.md"))
HEADER = "| # | Item | Assigned | Acceptance | State | Note |\n|---|---|---|---|---|---|\n"


def _register(*rows: str) -> str:
    return "# Register — fixture\n\n**Covers:** docs/superpowers/specs/x.md\n\n" + HEADER + "".join(
        row + "\n" for row in rows
    )


def _roundtrip_cases():
    for path in REGISTERS:
        text = path.read_text(encoding="utf-8")
        for row in parse_register(text).rows:
            if not row.state_recognised:
                continue
            if row.state in NOTE_REQUIRED_STATES and is_blank_note(row.note):
                continue
            yield pytest.param(path, row.number, row.state, id=f"{path.name}#{row.number}")


@pytest.mark.parametrize("path, number, state", list(_roundtrip_cases()))
def test_changing_a_state_and_back_reproduces_the_bytes(path, number, state):
    text = path.read_text(encoding="utf-8")
    other = "planned" if state == "open" else "open"
    changed = rewrite_register_row(text, number, {"state": other})
    before, after = text.split("\n"), changed.split("\n")
    assert len(before) == len(after)
    assert sum(1 for a, b in zip(before, after) if a != b) == 1
    assert rewrite_register_row(changed, number, {"state": state}) == text


@pytest.mark.parametrize("line, changes, expected", [
    ("| 1 | a | - | - | open |   -   |", {"state": "done"}, "| 1 | a | - | - | done |   -   |"),
    ("  | 1 | a | - | - | open | - |", {"state": "done"}, "  | 1 | a | - | - | done | - |"),
    ("| 1 | a | - | - | open | - |\r", {"state": "done"}, "| 1 | a | - | - | done | - |\r"),
    ("| 1 | a | - | - | open | - | tail", {"state": "done"}, "| 1 | a | - | - | done | - | tail"),
    ("| 1 | a \\| b | - | - | open | - |", {"note": "x"}, "| 1 | a \\| b | - | - | open | x |"),
    ("| 1 | a | - | - | open | - |", {"note": "x | y"}, "| 1 | a | - | - | open | x \\| y |"),
    ("| 1 | a | - | - | open ||", {"note": "x"}, "| 1 | a | - | - | open | x |"),
    ("| 1 | a | - | - | open | - |", {"assigned": "  p.md  "}, "| 1 | a | p.md | - | open | - |"),
])
def test_the_splice_keeps_everything_but_the_changed_text(line, changes, expected):
    text = _register(line)
    assert rewrite_register_row(text, 1, changes) == _register(expected)


@pytest.mark.parametrize("rows, number, changes, reason", [
    (["| 1 | a | - | - | open | - |"], 2, {"state": "done"}, "not_found"),
    (["| 1 | a | - | - | open | - |", "| 1 | b | - | - | open | - |"], 1, {"state": "done"}, "duplicate_row"),
    (["| 1 | a | - | open | - |"], 1, {"state": "done"}, "malformed_row"),
    (["| 1 | a | - | - | open | - |"], 1, {"state": "parked"}, "unknown_state"),
    (["| 1 | a | - | - | open | - |"], 1, {"state": "verify"}, "note_required"),
    (["| 1 | a | - | - | open | why |"], 1, {"state": "deferred", "note": " - "}, "note_required"),
    (["| 1 | a | - | - | open | - |"], 1, {"note": "two\nlines"}, "invalid_cell"),
    (["| 1 | a | - | - | open | - |"], 1, {"note": "cr\r"}, "invalid_cell"),
    (["| 1 | a | - | - | open |x|"], 1, {"note": "ends in \\"}, "invalid_cell"),
])
def test_refusals(rows, number, changes, reason):
    with pytest.raises(RowEditRefused) as refused:
        rewrite_register_row(_register(*rows), number, changes)
    assert refused.value.reason == reason


def test_a_note_and_a_state_change_together():
    text = _register("| 1 | a | - | - | open | - |")
    assert rewrite_register_row(text, 1, {"state": "verify", "note": "check it"}) == _register(
        "| 1 | a | - | - | verify | check it |"
    )
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_board_rewrite.py`
Expected: collection error, `ImportError: cannot import name 'RowEditRefused'`

- [ ] **Step 3: Write the rewrite**

The splice works on the raw line (a trailing `\r` included) and re-parses its own output: a value that would change the row's shape (a trailing backslash escaping the next pipe) is refused as `invalid_cell` rather than written.

Append to `backend/app/services/board_parse.py`, at the end of the file:

````python

# Cell index of each column inside a well-formed row's eight fields.
_CELL_INDEX = {"item": 2, "assigned": 3, "acceptance": 4, "state": 5, "note": 6}
EDITABLE_COLUMNS = frozenset({"state", "note", "assigned"})


class RowEditRefused(ValueError):
    """A register row edit the rewrite will not make; `reason` is the wire code."""

    def __init__(self, reason: str, message: str):
        self.reason = reason
        super().__init__(message)


def _boundaries(line: str) -> list[int]:
    """Indexes of the `|` that split cells: a `|` after a backslash is text."""
    return [i for i, ch in enumerate(line) if ch == "|" and (i == 0 or line[i - 1] != "\\")]


def _splice_cell(segment: str, value: str) -> str:
    core = segment.strip(" \t")
    if not core:
        return f" {value} " if value else segment
    lead = segment[: len(segment) - len(segment.lstrip(" \t"))]
    trail = segment[len(segment.rstrip(" \t")):]
    return f"{lead}{value}{trail}"


def rewrite_register_row(text: str, number: int, changes: dict[str, str]) -> str:
    """Splice new cell values into row `number`, changing nothing else.

    Never re-serialises: only each changed cell's trimmed text is replaced,
    so padding, indentation, a trailing `\\r`, text after the last `|` and
    every other line keep their bytes.
    """
    unknown = set(changes) - EDITABLE_COLUMNS
    if unknown:
        raise ValueError(f"not an editable column: {sorted(unknown)}")
    values: dict[str, str] = {}
    for column, raw in changes.items():
        if "\n" in raw or "\r" in raw:
            raise RowEditRefused("invalid_cell", f"the {column} may not contain a line break")
        values[column] = raw.strip(" \t")
    if "state" in values and values["state"] not in REGISTER_STATES:
        raise RowEditRefused(
            "unknown_state",
            f"{values['state']!r} is not a register state; use one of {', '.join(REGISTER_STATES)}",
        )

    parsed = parse_register(text)
    matches = [row for row in parsed.rows if row.number == number]
    if not matches:
        named = [m for m in parsed.malformed if m.number == number]
        if any(m.reason.startswith("duplicate number") for m in named):
            raise RowEditRefused("duplicate_row", f"two rows carry the number {number}")
        if named:
            raise RowEditRefused(
                "malformed_row", f"row {number} is malformed; fix it in the register first",
            )
        raise RowEditRefused("not_found", f"no row {number} in this register")
    row = matches[0]
    state = values.get("state", row.state)
    note = values.get("note", row.note)
    if state in NOTE_REQUIRED_STATES and is_blank_note(note):
        raise RowEditRefused("note_required", f"a row in {state!r} needs a Note")

    raw_lines = text.split("\n")
    original = raw_lines[row.line - 1]
    pipes = _boundaries(original)
    updated = original
    for column in sorted(values, key=lambda c: _CELL_INDEX[c], reverse=True):
        cell = _CELL_INDEX[column]
        start, end = pipes[cell - 1] + 1, pipes[cell]
        escaped = values[column].replace("|", "\\|")
        updated = updated[:start] + _splice_cell(updated[start:end], escaped) + updated[end:]

    check = _cells(updated.replace("\r", ""))
    if (
        check is None
        or len(check) != 8
        or check[1] != str(number)
        or any(check[_CELL_INDEX[c]] != v for c, v in values.items())
    ):
        raise RowEditRefused(
            "invalid_cell", "that value would change the row's shape; remove a trailing backslash",
        )
    raw_lines[row.line - 1] = updated
    return "\n".join(raw_lines)


class BoardRefusal(Exception):
    """A refusal the board's REST door answers as `error.code` = `reason`.

    `fields` ride `error.details[0]` (e.g. `current_hash` on a hash
    conflict), so the SPA can tell causes apart without parsing prose.
    """

    def __init__(self, status_code: int, reason: str, message: str, **fields):
        self.status_code = status_code
        self.reason = reason
        self.message = message
        self.fields = fields
        super().__init__(message)
````

- [ ] **Step 4: Run the tests**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_board_rewrite.py tests/test_board_parse.py`
Expected: all pass (the round-trip case runs once per committed register row, about 130)

- [ ] **Step 5: Commit**

````bash
git add backend/app/services/board_parse.py backend/tests/test_board_rewrite.py
git commit -m "feat(board): splice one register row without re-serialising"
````

---

### Task 3: `put_document` without an inline embed

**Files:**
- Modify: `backend/app/services/document_door.py` (`put_document`, about line 500)
- Test: `backend/tests/test_document_embed_inline.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `put_document(..., embed_inline: bool = True)`; with `False`, `llm` may be `None` and `blocks_embedded` is 0 (Contracts §Document door).

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

Every existing caller keeps the default, so its behaviour must not move; the early return sits before the `UNCHANGED` branch, which would otherwise spend a real embed call resolving the active fingerprint.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_document_embed_inline.py` with:

````python
"""`put_document(embed_inline=False)` files and commits without an embedder (spec 2026-10-13 §2.4)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services.document_door import put_document

FINGERPRINT = "embed-inline-probe|3"


class StubEmbedder:
    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([[1.0, 0.0, 0.0] for _ in texts], FINGERPRINT)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0], FINGERPRINT


class Untouchable:
    def __getattr__(self, name):
        raise AssertionError(f"embed_inline=False touched the embedder ({name})")


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


async def test_no_inline_embed_files_the_document_and_embeds_nothing(session):
    filed = await put_document(
        session, Untouchable(), project="p", uri="superpowers/registers/r.md",
        content="# R\n\nBody.\n", actor="admin", embed_inline=False,
    )
    assert filed.outcome == "created"
    assert filed.blocks_filed > 0
    assert filed.blocks_embedded == 0
    revisions = (await session.execute(
        text("SELECT count(*) FROM document_revisions WHERE document_id = CAST(:d AS uuid)"),
        {"d": filed.document_id},
    )).scalar_one()
    assert revisions == 1


async def test_an_unchanged_put_without_inline_embed_skips_the_fingerprint_probe(session):
    first = await put_document(
        session, None, project="p", uri="superpowers/plans/x.md", content="# X\n",
        embed_inline=False,
    )
    again = await put_document(
        session, None, project="p", uri="superpowers/plans/x.md", content="# X\n",
        expected_hash=first.content_hash, embed_inline=False,
    )
    assert again.outcome == "unchanged"
    assert again.content_hash == first.content_hash


async def test_the_default_still_embeds_inline(session):
    filed = await put_document(
        session, StubEmbedder(), project="p", uri="notes/a.md", content="# A\n\nBody.\n",
    )
    assert filed.blocks_embedded == filed.blocks_filed > 0
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_document_embed_inline.py`
Expected: 2 FAIL with `TypeError: put_document() got an unexpected keyword argument 'embed_inline'`; the default-path test passes

- [ ] **Step 3: Add the parameter**

In `backend/app/services/document_door.py`, replace:

````python
    expected_hash: str | None = None,
    force_reparse: bool = False,
) -> PutResult:
    if len(content) > MAX_CONTENT_CHARS:
````

with:

````python
    expected_hash: str | None = None,
    force_reparse: bool = False,
    embed_inline: bool = True,
) -> PutResult:
    """File a document, commit, then embed its blocks.

    With `embed_inline=False` it returns once the filing commits and embeds
    nothing, so `llm` may be None: `block_embedding_refresh` embeds the new
    blocks on its next pass, as it does for page writes (spec 2026-10-13
    §2.4). An embedder failure then cannot fail an edit that already landed.
    """
    if len(content) > MAX_CONTENT_CHARS:
````

In `backend/app/services/document_door.py`, replace:

````python
    await session.commit()

    if filed.outcome == UNCHANGED:
        # Resolved from a real embed call
````

with:

````python
    await session.commit()

    if not embed_inline:
        return PutResult(
            document_id=str(filed.document_id),
            outcome=filed.outcome,
            blocks_filed=filed.blocks_written,
            blocks_embedded=0,
            title_applied=filed.outcome != UNCHANGED,
            oversized_blocks=filed.oversized_blocks,
            largest_block_chars=filed.largest_block_chars,
            content_hash=filed.content_hash,
        )

    if filed.outcome == UNCHANGED:
        # Resolved from a real embed call
````

- [ ] **Step 4: Run the tests**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_document_embed_inline.py tests/test_document_revisions.py tests/test_documents_keyed.py`
Expected: all pass

- [ ] **Step 5: Commit**

````bash
git add backend/app/services/document_door.py backend/tests/test_document_embed_inline.py
git commit -m "feat(documents): let a put skip the inline embed"
````

---

### Task 4: Block verbs refuse registers and plans

**Files:**
- Modify: `backend/app/services/document_door.py` (new exception beside `DocumentNotConvertible`, `__all__`)
- Modify: `backend/app/services/block_verbs.py` (import, `_DOC_META`, `_mutate`)
- Test: `backend/tests/test_board_block_refusal.py`

**Interfaces:**
- Consumes: Task 1's `is_mirror_owned`; Task 3's `embed_inline` (the test files documents without an embedder).
- Produces: `DocumentMirrorOwned(DocumentNotConvertible)` in `app.services.document_door` (Contracts §Document door).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4

The refusal sits in `_mutate` right after the row lock and the metadata read (the uri is only known then), before the hash check and before any conversion. Page owners are untouched: `_PAGE_META` carries no `uri`, and the check is gated on `owner.kind == "document"`.

- [ ] **Step 1: Write the failing tests**

Each MCP case is its own test: a refused tool rolls its session back, which ends the test's transaction and takes the filed document with it (see the `session` fixture's docstring in `tests/conftest.py`).

Create `backend/tests/test_board_block_refusal.py` with:

````python
"""Block verbs refuse registers and plans on both doors (spec 2026-10-13 §2.5)."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.services.block_verbs import (
    delete_block,
    insert_block,
    move_block,
    update_block,
)
from app.services.document_door import DocumentMirrorOwned, put_document

FINGERPRINT = "board-refusal-probe|3"
CONTENT = "# Title\n\nFirst paragraph.\n\nSecond paragraph.\n"
OWNED = ("superpowers/registers/r.md", "superpowers/plans/p.md")


class StubEmbedder:
    config = {"model": "probe", "base_url": "http://probe", "api_kind": "openai"}

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([[1.0, 0.0, 0.0] for _ in texts], FINGERPRINT)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0], FINGERPRINT

    def llm_fingerprint(self):
        return FINGERPRINT


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


@pytest.fixture
def stub_llm(client):
    from app.main import app

    previous = getattr(app.state, "llm", None)
    app.state.llm = StubEmbedder()
    yield app.state.llm
    app.state.llm = previous


async def _file(session, uri):
    filed = await put_document(
        session, None, project="p", uri=uri, content=CONTENT, embed_inline=False,
    )
    ids = [
        row[0] for row in await session.execute(
            text("SELECT CAST(id AS text) FROM blocks WHERE document_id = CAST(:d AS uuid) "
                 "ORDER BY order_index"),
            {"d": filed.document_id},
        )
    ]
    return filed.document_id, ids


async def _direction(session, document_id):
    return (await session.execute(
        text("SELECT properties->>'ingest_direction' FROM documents WHERE id = CAST(:d AS uuid)"),
        {"d": document_id},
    )).scalar_one()


def _verbs(document_id, ids):
    return {
        "update": lambda s, llm: update_block(s, llm, block_id=ids[1], text="changed"),
        "insert": lambda s, llm: insert_block(
            s, llm, document_id=document_id, type="paragraph", text="new",
        ),
        "move": lambda s, llm: move_block(s, llm, block_id=ids[2], after_block_id=None),
        "delete": lambda s, llm: delete_block(s, llm, block_id=ids[2]),
    }


@pytest.mark.parametrize("verb", ["update", "insert", "move", "delete"])
@pytest.mark.parametrize("uri", OWNED)
async def test_every_verb_refuses_a_mirror_owned_document(session, uri, verb):
    document_id, ids = await _file(session, uri)
    with pytest.raises(DocumentMirrorOwned):
        await _verbs(document_id, ids)[verb](session, StubEmbedder())
    assert await _direction(session, document_id) is None


@pytest.mark.parametrize("verb", ["update", "insert", "move", "delete"])
async def test_every_verb_still_accepts_any_other_document(session, verb):
    document_id, ids = await _file(session, "superpowers/specs/s.md")
    await _verbs(document_id, ids)[verb](session, StubEmbedder())
    assert await _direction(session, document_id) == "blocks"


@pytest.mark.parametrize("uri", OWNED)
async def test_rest_answers_422_on_each_block_route(client, auth_headers, session, stub_llm, uri):
    document_id, ids = await _file(session, uri)
    base = f"/api/v1/documents/{document_id}/blocks"
    responses = [
        await client.post(base, json={"type": "paragraph", "text": "new"}, headers=auth_headers),
        await client.patch(f"{base}/{ids[1]}", json={"text": "x"}, headers=auth_headers),
        await client.post(f"{base}/{ids[2]}/move", json={}, headers=auth_headers),
        await client.delete(f"{base}/{ids[2]}", headers=auth_headers),
    ]
    for response in responses:
        assert response.status_code == 422, response.text
        assert "mirror owns" in response.json()["detail"]
    assert await _direction(session, document_id) is None


# One tool per test: a refused tool rolls its session back, which ends the
# test's transaction and takes the filed document with it (conftest `session`).
@pytest.mark.parametrize("tool", ["update", "insert", "move", "delete"])
async def test_mcp_answers_not_convertible_on_each_block_tool(session, monkeypatch, tool):
    from app.api.mcp import server as mcp_server

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=StubEmbedder()))
    document_id, ids = await _file(session, OWNED[0])
    call = {
        "update": lambda: mcp_server.block_update(block_id=ids[1], text="x"),
        "insert": lambda: mcp_server.block_insert(
            document_id=document_id, type="paragraph", text="new",
        ),
        "move": lambda: mcp_server.block_move(block_id=ids[2]),
        "delete": lambda: mcp_server.block_delete(block_id=ids[2]),
    }[tool]
    body = json.loads(await call())
    assert body["status"] == "not_convertible", body
    assert "mirror owns" in body["reason"]
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_board_block_refusal.py`
Expected: collection error, `ImportError: cannot import name 'DocumentMirrorOwned'`

- [ ] **Step 3: Add the refusal**

In `backend/app/services/document_door.py`, replace:

````python
@dataclass(frozen=True)
class PutResult:
````

with:

````python
class DocumentMirrorOwned(DocumentNotConvertible):
    """block verb refused: the dr-forge mirror owns this document.

    Registers and plans (`superpowers/registers/`, `superpowers/plans/`) reach
    darkmem as content puts from the mirror, and the progress board edits
    registers the same way. Converting one to block-first would refuse every
    later put and strand the mirror (spec 2026-10-13 §2.5). A subclass, so
    both doors already map it: REST to 422, MCP to `not_convertible`.
    """


@dataclass(frozen=True)
class PutResult:
````

In `backend/app/services/document_door.py`, replace:

````python
    "DocumentJournalWriteFailed",
    "DocumentNothingToChange",
````

with:

````python
    "DocumentJournalWriteFailed",
    "DocumentMirrorOwned",
    "DocumentNothingToChange",
````

In `backend/app/services/block_verbs.py`, replace:

````python
from app.services.document_door import (
    BLOCK_FIRST,
    MAX_BLOCKS,
    MAX_CONTENT_CHARS,
    DocumentNotConvertible,
    DocumentTooLarge,
)
````

with:

````python
from app.services.board_parse import is_mirror_owned
from app.services.document_door import (
    BLOCK_FIRST,
    MAX_BLOCKS,
    MAX_CONTENT_CHARS,
    DocumentMirrorOwned,
    DocumentNotConvertible,
    DocumentTooLarge,
)
````

In `backend/app/services/block_verbs.py`, replace:

````python
_DOC_META = text(
    "SELECT project, content, content_hash, "
````

with:

````python
_DOC_META = text(
    "SELECT project, uri, content, content_hash, "
````

In `backend/app/services/block_verbs.py`, replace:

````python
    if meta is None:
        raise BlockTargetUnresolved(f"no {owner.noun} with id {document_id}")
````

with:

````python
    if meta is None:
        raise BlockTargetUnresolved(f"no {owner.noun} with id {document_id}")
    if owner.kind == "document" and is_mirror_owned(meta["uri"]):
        raise DocumentMirrorOwned(
            f"{meta['uri']} is a register or plan the dr-forge mirror owns through "
            "content puts; the block verbs would convert it to block-first and "
            "refuse every later push. Edit it with document_put, or from the board."
        )
````

- [ ] **Step 4: Run the tests and the block-verb neighbours**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_board_block_refusal.py tests/test_block_verbs.py tests/test_mcp.py tests/test_block_pipeline.py`
Expected: all pass

- [ ] **Step 5: Commit**

````bash
git add backend/app/services/document_door.py backend/app/services/block_verbs.py backend/tests/test_board_block_refusal.py
git commit -m "feat(documents): refuse block verbs on registers and plans"
````

---

### Task 5: The board read service

**Files:**
- Create: `backend/app/services/board.py`
- Modify: `backend/tests/test_block_retrieval.py` (`BLOCK_CHANNEL_MODULES`), `backend/tests/test_worklog_wall.py` (`WORKLOG_MODULES`)
- Test: `backend/tests/test_board_service.py`

**Interfaces:**
- Consumes: Task 1's parsers and constants; Task 3's `embed_inline` (tests file documents without an embedder); `app.services.worklog.append` / `update_workstream` (existing) in tests.
- Produces: `load_board(session, project) -> dict` and `board_version(session, project) -> str`, record shapes as in Contracts §Records; `board.BLOCK_FIRST`.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

`board.py` must never import `app.services.document_door`: the door's import closure reaches `app.repositories.relational`, which imports a memory model, and `test_no_work_log_module_imports_a_memory_model` then fails for `app.services.board` (measured 2026-10-13). That is why `BLOCK_FIRST` is restated here with an equality test, and why the edit lives in Task 7's `board_edit.py`.

- [ ] **Step 1: Write the failing tests**

The ledger fixtures are real dr-forge ledger lines (`darkraise-ai-plugins/.superpowers/sdd/*/progress.md`) carrying the properties the plugin's contract §3 will send.

Create `backend/tests/test_board_service.py` with:

````python
"""The board's read service: records derived from documents and ledgers (spec 2026-10-13 §1, §2.1)."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from app.services import worklog
from app.services.board import board_version, load_board
from app.services.document_door import put_document
from tests._reachability_scan import import_closure
from tests.test_block_retrieval import BLOCK_CHANNEL_MODULES, VAULT_WRITERS
from tests.test_worklog_wall import WORKLOG_MODULES, WORKLOG_SERVICE_LAYER

BACKEND = Path(__file__).resolve().parent.parent
PROJECT = "board-proj"
PLAN_URI = "superpowers/plans/2026-10-13-sample.md"
REGISTER_URI = "superpowers/registers/sample.md"

PLAN = """# Sample plan

### Task 1: Parser

- [ ] **Step 1: Write the failing test**
- [x] **Step 2: Run it**

### Task 2: Rewriter

### Task 3: Routes

### Task 3: Routes again
"""

REGISTER = """# Register — sample

**Covers:** docs/superpowers/specs/sample.md

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | first | `docs/superpowers/plans/2026-10-13-sample.md` | - | doing | - |
| 2 | second | darkraise-ai-plugins: docs/superpowers/plans/x.md | - | open | - |
"""


async def _file(session, uri, content, project=PROJECT):
    return await put_document(
        session, None, project=project, uri=uri, content=content, embed_inline=False,
    )


async def _append(session, key, entries, *, plan_uri=PLAN_URI, project=PROJECT, spec_uri=None):
    properties = {"plan_uri": plan_uri}
    if spec_uri:
        properties["spec_uri"] = spec_uri
    return await worklog.append(
        session, project=project, key=key, run_key="claude:run-1",
        entries=entries, properties=properties,
    )


def _ledger(body, **properties):
    return {"kind": "ledger", "body": body, "properties": properties}


def _plan(board):
    return next(p for p in board["plans"] if p["uri"] == PLAN_URI)


def _task(board, number, index=0):
    return [t for t in _plan(board)["tasks"] if t["number"] == number][index]


async def test_the_corpus_is_exact_prefixes_and_markdown_only(session):
    await _file(session, PLAN_URI, PLAN)
    await _file(session, REGISTER_URI, REGISTER)
    await _file(session, "notes/superpowers/plans/x.md", PLAN)
    await _file(session, "superpowers/plans/not-markdown.txt", PLAN)
    await _file(session, "superpowers/specs/s.md", "# Spec\n")
    board = await load_board(session, PROJECT)
    assert [p["uri"] for p in board["plans"]] == [PLAN_URI]
    assert [r["uri"] for r in board["registers"]] == [REGISTER_URI]


async def test_a_plan_without_a_workstream_is_untracked_no_workstream(session):
    await _file(session, PLAN_URI, PLAN)
    board = await load_board(session, PROJECT)
    plan = _plan(board)
    assert plan["untracked"] == "no_workstream"
    assert {t["state"] for t in plan["tasks"]} == {"untracked"}
    assert {t["untracked"] for t in plan["tasks"]} == {"no_workstream"}


async def test_a_ledger_without_properties_is_untracked_no_properties(session):
    await _file(session, PLAN_URI, PLAN)
    await _append(session, "sample", [_ledger("Task 1: complete (commits a..b)\n")])
    plan = _plan(await load_board(session, PROJECT))
    assert plan["untracked"] == "no_properties"
    assert {t["untracked"] for t in plan["tasks"]} == {"no_properties"}


async def test_the_newest_state_bearing_entry_wins_and_stateless_lines_do_not_move_it(session):
    await _file(session, PLAN_URI, PLAN)
    await _append(session, "sample", [
        _ledger("Task 1: implementer dr-superpowers:impl-opus-medium (assigned; base 065871f)\n",
                task=1, state="wip"),
        _ledger("Task 1: fix round 1/5 (1 addressed, 0 open; commits 535856b..70d319b)\n",
                task=1, state="review", commit="70d319b"),
        _ledger("Task 1: minor (deferred): the reported RED run stashed an implementation\n",
                task=1),
        _ledger("Task 2: implementer dr-superpowers:impl-opus-low (assigned; base 70d319b)\n",
                task=2, state="wip"),
        _ledger("Task 2: complete (commits 70d319b..9abc123, review clean)\n",
                task=2, state="done", commit="9abc123"),
    ])
    board = await load_board(session, PROJECT)
    assert _task(board, 1)["state"] == "review"
    assert _task(board, 1)["commit"] == "70d319b"
    assert _task(board, 2)["state"] == "done"
    assert _task(board, 2)["commit"] == "9abc123"
    assert _task(board, 1)["last_activity"] is not None
    assert _task(board, 3)["state"] == "todo"


async def test_a_cut_line_joins_its_pieces_into_the_blocked_reason(session):
    await _file(session, PLAN_URI, PLAN)
    props = {"task": 2, "state": "blocked"}
    await _append(session, "sample", [
        _ledger("Task 1: complete (commits a..b)\n", task=1, state="done"),
        _ledger("Task 2: BLOCKED — the Codex sandbox refuses ", **props),
        _ledger("127.0.0.1 listeners (EPERM)\n", **props),
    ])
    task = _task(await load_board(session, PROJECT), 2)
    assert task["state"] == "blocked"
    assert task["blocked_reason"] == (
        "Task 2: BLOCKED — the Codex sandbox refuses 127.0.0.1 listeners (EPERM)\n"
    )


async def test_non_integer_tasks_are_ignored_and_unknown_states_are_unrecognised(session):
    await _file(session, PLAN_URI, PLAN)
    await _append(session, "sample", [
        _ledger("Task 1: complete\n", task=1, state="done"),
        _ledger("Task 1.5: odd\n", task=1.5, state="blocked"),
        _ledger("Task 3: odd\n", task="3", state="blocked"),
        _ledger("Task 2: parked\n", task=2, state="parked"),
    ])
    board = await load_board(session, PROJECT)
    assert _task(board, 1)["state"] == "done"
    assert _task(board, 2)["state"] == "unrecognised"
    assert _task(board, 2)["raw_state"] == "parked"
    assert _task(board, 3)["state"] == "todo"


async def test_orphans_and_shared_numbers(session):
    await _file(session, PLAN_URI, PLAN)
    await _append(session, "sample", [
        _ledger("Task 3: complete\n", task=3, state="done"),
        _ledger("Task 9: complete\n", task=9, state="done"),
    ])
    board = await load_board(session, PROJECT)
    plan = _plan(board)
    assert plan["orphans"] == [9]
    first, second = _task(board, 3, 0), _task(board, 3, 1)
    assert first["shared_number"] and second["shared_number"]
    assert first["state"] == second["state"] == "done"
    assert not _task(board, 1)["shared_number"]


async def test_two_workstreams_prefer_the_open_one_and_count_the_other(session):
    await _file(session, PLAN_URI, PLAN)
    await _append(session, "older", [_ledger("Task 1: complete\n", task=1, state="done")])
    closed = await _append(session, "closed-one", [_ledger("Task 1: x\n", task=1, state="blocked")])
    await worklog.update_workstream(session, closed.workstream.id, state="closed")
    plan = _plan(await load_board(session, PROJECT))
    assert plan["workstream"]["key"] == "older"
    assert plan["other_workstreams"] == 1


async def test_steps_are_carried_and_never_counted(session):
    await _file(session, PLAN_URI, PLAN)
    task = _task(await load_board(session, PROJECT), 1)
    assert task["steps"] == [
        {"checked": False, "text": "**Step 1: Write the failing test**"},
        {"checked": True, "text": "**Step 2: Run it**"},
    ]
    assert task["label"] == "Task 1: Parser"
    assert task["title"] == "Parser"


async def test_register_rows_resolve_their_plan_and_show_progress(session):
    await _file(session, PLAN_URI, PLAN)
    await _file(session, REGISTER_URI, REGISTER)
    await _append(session, "sample", [_ledger("Task 2: complete\n", task=2, state="done")])
    board = await load_board(session, PROJECT)
    register = board["registers"][0]
    assert register["title"] == "Register — sample"
    assert register["covers"] == "docs/superpowers/specs/sample.md"
    first, second = register["rows"]
    assert first["plan_uri"] == PLAN_URI
    assert first["plan_progress"] == {"done": 1, "total": 4, "untracked": None}
    assert second["plan_uri"] is None and second["plan_progress"] is None


async def test_an_untracked_plan_says_so_on_the_register_row(session):
    await _file(session, PLAN_URI, PLAN)
    await _file(session, REGISTER_URI, REGISTER)
    row = (await load_board(session, PROJECT))["registers"][0]["rows"][0]
    assert row["plan_progress"]["untracked"] == "no_workstream"


async def test_a_failing_source_reports_its_own_error_and_the_rest_renders(session, monkeypatch):
    from app.services import board as board_module

    await _file(session, PLAN_URI, PLAN)
    await _file(session, REGISTER_URI, REGISTER)

    def boom(_text):
        raise RuntimeError("parser exploded")

    monkeypatch.setattr(board_module, "parse_plan", boom)
    board = await load_board(session, PROJECT)
    assert _plan(board)["error"] == "RuntimeError: parser exploded"
    assert len(board["registers"][0]["rows"]) == 2


async def test_a_block_first_register_reads_normally_and_says_so(session):
    filed = await _file(session, REGISTER_URI, REGISTER)
    await session.execute(
        text("UPDATE documents SET properties = "
             "coalesce(properties, CAST('{}' AS jsonb)) || CAST(:props AS jsonb) "
             "WHERE id = CAST(:id AS uuid)"),
        {"id": filed.document_id, "props": '{"ingest_direction": "blocks"}'},
    )
    register = (await load_board(session, PROJECT))["registers"][0]
    assert register["block_first"] is True
    assert len(register["rows"]) == 2


async def test_the_version_moves_on_a_put_and_on_an_append_and_only_then(session):
    await _file(session, PLAN_URI, PLAN)
    first = await board_version(session, PROJECT)
    assert await board_version(session, PROJECT) == first
    await _file(session, PLAN_URI, PLAN + "\n### Task 4: More\n")
    second = await board_version(session, PROJECT)
    assert second != first
    await _append(session, "sample", [_ledger("Task 1: x\n", task=1, state="wip")])
    third = await board_version(session, PROJECT)
    assert third != second
    await _file(session, "superpowers/specs/s.md", "# Spec\n")
    await _file(session, PLAN_URI, PLAN, project="elsewhere")
    assert await board_version(session, PROJECT) == third


def test_the_board_service_is_a_member_of_both_walls():
    module = "app.services.board"
    assert module in BLOCK_CHANNEL_MODULES
    assert module in WORKLOG_MODULES and module in WORKLOG_SERVICE_LAYER


def test_the_restated_block_first_marker_matches_the_door():
    from app.services import board, document_door

    assert board.BLOCK_FIRST == document_door.BLOCK_FIRST


def test_the_board_service_reaches_neither_the_pipeline_nor_the_vault():
    reached = {"app.services.pipeline", *VAULT_WRITERS} & import_closure(BACKEND, "app.services.board")
    assert not reached, sorted(reached)


def test_the_scan_would_see_the_board_reach_the_pipeline(tmp_path):
    """Negative control: a planted board that imports the pipeline is caught."""
    services = tmp_path / "app" / "services"
    services.mkdir(parents=True)
    (tmp_path / "app" / "__init__.py").write_text("")
    (services / "__init__.py").write_text("")
    (services / "board.py").write_text("from app.services import pipeline\n")
    (services / "pipeline.py").write_text("")
    assert "app.services.pipeline" in import_closure(tmp_path, "app.services.board")
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_board_service.py`
Expected: collection error, `ModuleNotFoundError: No module named 'app.services.board'`

- [ ] **Step 3: Write the service**

Create `backend/app/services/board.py` with:

````python
"""The progress board: a projection of registers, plans and ledgers (spec 2026-10-13).

Nothing is stored. Every read derives the records from `documents.content` and
`worklog_entries`, so a board can never disagree with the files it shows. It
reads `documents`, never `blocks`, and imports neither the memory pipeline nor
any vault module (§2.1; `tests/test_board_service.py` holds the memberships).
Register edits live in `board_edit`, outside the work-log wall, because they
file through `document_door`.
"""
from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.board_parse import (
    LEDGER_STATES,
    PLAN_PREFIX,
    REGISTER_PREFIX,
    REGISTER_STATES,
    cell_uri,
    is_blank_note,
    parse_plan,
    parse_register,
)

# `document_door.BLOCK_FIRST`, restated: importing the door would carry its
# memory-model imports inside the work-log wall (`tests/test_worklog_wall.py`).
# `tests/test_board_service.py` asserts the two stay equal.
BLOCK_FIRST = "blocks"
# Bumped when the records' shape changes, so a browser holding an old ETag
# refetches after a deploy instead of revalidating into the old shape.
BOARD_FORMAT = "1"

# A ledger line past the body limit arrives as consecutive pieces; this bounds
# how far back a blocked reason looks for them (16 x 65,536 characters).
MAX_REASON_PIECES = 16

_CORPUS_WHERE = (
    "project = CAST(:project AS text) "
    "AND (starts_with(uri, CAST(:registers AS text)) OR starts_with(uri, CAST(:plans AS text))) "
    "AND right(uri, 3) = '.md'"
)

_CORPUS = text(
    "SELECT CAST(id AS text) AS id, uri, title, content, content_hash, "
    "       properties->>'ingest_direction' AS direction "
    f"FROM documents WHERE {_CORPUS_WHERE} ORDER BY uri"
)

_WORKSTREAMS = text(
    "SELECT CAST(id AS text) AS id, key, state, last_entry_at, "
    "       properties->>'plan_uri' AS plan_uri, properties->>'spec_uri' AS spec_uri "
    "FROM workstreams "
    "WHERE project = CAST(:project AS text) AND properties->>'plan_uri' IS NOT NULL"
)

# An integer `task` or NULL. Nested CASEs, because only a CASE orders
# evaluation: the cast must never run on a string such as "3a".
_TASK = (
    "CASE WHEN jsonb_typeof(e.properties->'task') = 'number' THEN "
    "CASE WHEN CAST(e.properties->>'task' AS numeric) "
    "        = floor(CAST(e.properties->>'task' AS numeric)) "
    "THEN CAST(e.properties->>'task' AS numeric) END END"
)

_STATES = text(
    f"""
    WITH t AS (
        SELECT e.workstream_id, e.seq, e.body, e.properties, {_TASK} AS task
        FROM worklog_entries e
        WHERE e.workstream_id = ANY(CAST(:ids AS uuid[]))
          AND e.kind = 'ledger'
          AND e.properties->>'state' IS NOT NULL
    )
    SELECT DISTINCT ON (workstream_id, task)
           CAST(workstream_id AS text) AS workstream_id, task, seq, body, properties
    FROM t WHERE task IS NOT NULL
    ORDER BY workstream_id, task, seq DESC
    """
)

_ACTIVITY = text(
    f"""
    WITH t AS (
        SELECT e.workstream_id, e.seq, e.created_at,
               e.properties->>'commit' AS commit, {_TASK} AS task
        FROM worklog_entries e
        WHERE e.workstream_id = ANY(CAST(:ids AS uuid[]))
    )
    SELECT CAST(workstream_id AS text) AS workstream_id, task,
           (array_agg(created_at ORDER BY seq DESC))[1] AS last_activity,
           (array_agg(commit ORDER BY seq DESC) FILTER (WHERE commit IS NOT NULL))[1] AS commit
    FROM t WHERE task IS NOT NULL
    GROUP BY workstream_id, task
    """
)

_LEDGER_TASKS = text(
    f"""
    SELECT DISTINCT CAST(workstream_id AS text) AS workstream_id, task
    FROM (
        SELECT e.workstream_id, {_TASK} AS task
        FROM worklog_entries e
        WHERE e.workstream_id = ANY(CAST(:ids AS uuid[])) AND e.kind = 'ledger'
    ) t
    WHERE task IS NOT NULL
    """
)

_PRECEDING = text(
    "SELECT body, properties FROM worklog_entries "
    "WHERE workstream_id = CAST(:workstream_id AS uuid) AND kind = 'ledger' "
    "AND seq < :seq ORDER BY seq DESC LIMIT :limit"
)

_VERSION_DOCUMENTS = text(
    "SELECT count(*) AS n, max(updated_at) AS at, "
    "       md5(string_agg(coalesce(content_hash, ''), ',' ORDER BY id)) AS hashes "
    f"FROM documents WHERE {_CORPUS_WHERE}"
)

_VERSION_LOG = text(
    "SELECT (SELECT count(*) FROM workstreams WHERE project = CAST(:project AS text)) AS n, "
    "       (SELECT max(updated_at) FROM workstreams WHERE project = CAST(:project AS text)) AS at, "
    "       (SELECT max(e.seq) FROM worklog_entries e JOIN workstreams w ON w.id = e.workstream_id "
    "        WHERE w.project = CAST(:project AS text)) AS seq"
)


def _corpus_params(project: str) -> dict[str, str]:
    return {"project": project, "registers": REGISTER_PREFIX, "plans": PLAN_PREFIX}


async def board_version(session: AsyncSession, project: str) -> str:
    """A fingerprint of everything the board reads, from aggregates only.

    It never reads `content`: a 304 must cost two index-backed aggregates,
    not the parse it saves.
    """
    documents = (await session.execute(_VERSION_DOCUMENTS, _corpus_params(project))).one()
    log = (await session.execute(_VERSION_LOG, {"project": project})).one()
    material = repr((BOARD_FORMAT, tuple(documents), tuple(log)))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def _choose(candidates: list[Any]) -> Any | None:
    """Open over closed, then the newest `last_entry_at`, then the larger id."""
    if not candidates:
        return None
    return max(candidates, key=lambda w: (w.state == "open", w.last_entry_at, w.id))


async def _blocked_reason(session: AsyncSession, workstream_id: str, entry: Any) -> str:
    """The blocking entry's body, preceded by the earlier pieces of its line."""
    pieces = [entry.body]
    rows = await session.execute(
        _PRECEDING,
        {"workstream_id": workstream_id, "seq": entry.seq, "limit": MAX_REASON_PIECES},
    )
    for row in rows:
        if row.properties != entry.properties or row.body.endswith("\n"):
            break
        pieces.insert(0, row.body)
    return "".join(pieces)


def _register_record(document: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "document_id": document.id,
        "uri": document.uri,
        "title": document.title,
        "covers": None,
        "content_hash": document.content_hash,
        "block_first": document.direction == BLOCK_FIRST,
        "rows": [],
        "malformed": [],
        "error": None,
    }
    if document.content is None:
        record["error"] = "this register has no stored text to read"
        return record
    try:
        parsed = parse_register(document.content)
    except Exception as exc:  # one source's failure must not blank the board (§5)
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record
    record["title"] = parsed.title or document.title
    record["covers"] = parsed.covers
    record["rows"] = [
        {
            "number": row.number,
            "item": row.item,
            "assigned": row.assigned,
            "acceptance": row.acceptance,
            "state": row.state if row.state in REGISTER_STATES else "unrecognised",
            "raw_state": row.state,
            "note": row.note,
            "note_blank": is_blank_note(row.note),
            "line": row.line,
            "plan_uri": None,
            "plan_progress": None,
        }
        for row in parsed.rows
    ]
    record["malformed"] = [
        {"line": m.line, "text": m.text, "reason": m.reason} for m in parsed.malformed
    ]
    return record


async def load_board(session: AsyncSession, project: str) -> dict[str, Any]:
    """Every register row and plan task of `project`, derived on read (§1)."""
    documents = (await session.execute(_CORPUS, _corpus_params(project))).all()
    registers = [d for d in documents if d.uri.startswith(REGISTER_PREFIX)]
    plan_documents = [d for d in documents if d.uri.startswith(PLAN_PREFIX)]

    by_plan: dict[str, list[Any]] = {}
    for workstream in (await session.execute(_WORKSTREAMS, {"project": project})).all():
        by_plan.setdefault(workstream.plan_uri, []).append(workstream)
    chosen = {uri: _choose(by_plan.get(uri, [])) for uri in (d.uri for d in plan_documents)}
    ids = sorted({w.id for w in chosen.values() if w is not None})

    states: dict[tuple[str, int], Any] = {}
    activity: dict[tuple[str, int], Any] = {}
    ledger_tasks: dict[str, set[int]] = {}
    if ids:
        for row in (await session.execute(_STATES, {"ids": ids})).all():
            states[(row.workstream_id, int(row.task))] = row
        for row in (await session.execute(_ACTIVITY, {"ids": ids})).all():
            activity[(row.workstream_id, int(row.task))] = row
        for row in (await session.execute(_LEDGER_TASKS, {"ids": ids})).all():
            ledger_tasks.setdefault(row.workstream_id, set()).add(int(row.task))

    plans: list[dict[str, Any]] = []
    for document in plan_documents:
        workstream = chosen[document.uri]
        record: dict[str, Any] = {
            "document_id": document.id,
            "uri": document.uri,
            "title": document.title,
            "content_hash": document.content_hash,
            "workstream": None,
            "other_workstreams": max(len(by_plan.get(document.uri, [])) - 1, 0),
            "spec_uri": None,
            "untracked": None,
            "tasks": [],
            "orphans": [],
            "error": None,
        }
        if workstream is not None:
            record["workstream"] = {
                "id": workstream.id, "key": workstream.key, "state": workstream.state,
            }
            record["spec_uri"] = workstream.spec_uri
        if workstream is None:
            record["untracked"] = "no_workstream"
        elif workstream.id not in ledger_tasks:
            record["untracked"] = "no_properties"
        plans.append(record)
        if document.content is None:
            record["error"] = "this plan has no stored text to read"
            continue
        try:
            parsed = parse_plan(document.content)
        except Exception as exc:  # one source's failure must not blank the board (§5)
            record["error"] = f"{type(exc).__name__}: {exc}"
            continue
        record["title"] = parsed.title or document.title
        counts: dict[int, int] = {}
        for task in parsed.tasks:
            counts[task.number] = counts.get(task.number, 0) + 1
        for task in parsed.tasks:
            record["tasks"].append(
                await _task_record(session, task, workstream, record["untracked"],
                                   states, activity, counts[task.number] > 1)
            )
        if workstream is not None:
            headings = set(counts)
            record["orphans"] = sorted(ledger_tasks.get(workstream.id, set()) - headings)

    progress = {
        plan["uri"]: {
            "done": sum(1 for t in plan["tasks"] if t["state"] == "done"),
            "total": len(plan["tasks"]),
            "untracked": plan["untracked"],
        }
        for plan in plans
        if plan["error"] is None
    }
    register_records = [_register_record(d) for d in registers]
    for register in register_records:
        for row in register["rows"]:
            uri = cell_uri(row["assigned"])
            if uri in progress:
                row["plan_uri"] = uri
                row["plan_progress"] = progress[uri]
    return {"project": project, "registers": register_records, "plans": plans}


async def _task_record(session, task, workstream, untracked, states, activity, shared):
    record: dict[str, Any] = {
        "number": task.number,
        "label": task.label,
        "title": task.title,
        "line": task.line,
        "state": "untracked" if untracked else "todo",
        "raw_state": None,
        "untracked": untracked,
        "shared_number": shared,
        "blocked_reason": None,
        "commit": None,
        "last_activity": None,
        "steps": [{"checked": s.checked, "text": s.text} for s in task.steps],
    }
    if workstream is None:
        return record
    key = (workstream.id, task.number)
    seen = activity.get(key)
    if seen is not None:
        record["commit"] = seen.commit
        record["last_activity"] = seen.last_activity
    if untracked:
        return record
    entry = states.get(key)
    if entry is None:
        return record
    raw = entry.properties.get("state")
    record["raw_state"] = raw if isinstance(raw, str) else str(raw)
    record["state"] = raw if raw in LEDGER_STATES else "unrecognised"
    if record["state"] == "blocked":
        record["blocked_reason"] = await _blocked_reason(session, workstream.id, entry)
    return record
````

- [ ] **Step 4: Classify it in the two walls**

In `backend/tests/test_block_retrieval.py`, replace:

````python
    "app.services.document_revisions",
````

with:

````python
    "app.services.document_revisions",
    # The progress board reads documents' filed content to derive its records
    # (spec 2026-10-13 §2.1), so it is classified with the other readers.
    "app.services.board",
````

In `backend/tests/test_worklog_wall.py`, replace:

````python
    "app.api.routes.worklog",
})
````

with:

````python
    "app.api.routes.worklog",
    # Reads ledger entries for the progress board (spec 2026-10-13 §2.1).
    "app.services.board",
})
````

- [ ] **Step 5: Run the tests and the walls**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_board_service.py tests/test_block_retrieval.py tests/test_block_pipeline.py tests/test_worklog_wall.py`
Expected: all pass

- [ ] **Step 6: Commit**

````bash
git add backend/app/services/board.py backend/tests/test_board_service.py backend/tests/test_block_retrieval.py backend/tests/test_worklog_wall.py
git commit -m "feat(board): derive register rows and plan tasks on read"
````

---

### Task 6: The records route

**Files:**
- Create: `backend/app/schemas/board.py`, `backend/app/api/routes/board.py`
- Modify: `backend/app/main.py` (router import and `include_router`)
- Modify: `backend/tests/test_api/test_rest_conformance.py` (`EXPECTED_STATUS`), `backend/app/services/content_surfaces.py` (`ROUTES_WITHOUT_MEMORY_CONTENT`), `backend/tests/test_door_parity.py` (`PARITY_TABLE`), `docs/two-door-parity.md` (regenerated block and headline)
- Test: `backend/tests/test_api/test_board_routes.py`

**Interfaces:**
- Consumes: Task 5's `load_board`, `board_version`.
- Produces: `GET /api/v1/board/records?project=` answering `BoardRecordsResponse` with a weak `ETag` and `Cache-Control: private, no-cache`, 304 on a matching `If-None-Match` (Contracts §REST); the `board.reads` parity row; `app/api/routes/board.py` with `router`.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_api/test_board_routes.py` with:

````python
"""The board's records route: projection, ETag and login-only access (spec 2026-10-13 §2.2)."""
from __future__ import annotations

from app.services import worklog
from app.services.api_keys import issue_key
from app.services.document_door import put_document

PROJECT = "board-routes"
REGISTER_URI = "superpowers/registers/r.md"
REGISTER = """# Register — routes

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | first | - | - | open | - |
| 2 | dup | - | - | open | - |
| 2 | dup again | - | - | open | - |
| 3 | short | - | open | - |
"""


async def _file(session, uri=REGISTER_URI, content=REGISTER):
    return await put_document(
        session, None, project=PROJECT, uri=uri, content=content, embed_inline=False,
    )


async def test_records_serve_registers_and_plans(client, auth_headers, session):
    await _file(session)
    await _file(session, "superpowers/plans/p.md", "# Plan\n\n### Task 1: One\n")
    response = await client.get(f"/api/v1/board/records?project={PROJECT}", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert [r["uri"] for r in body["registers"]] == [REGISTER_URI]
    assert [row["number"] for row in body["registers"][0]["rows"]] == [1]
    assert {m["reason"] for m in body["registers"][0]["malformed"]} == {
        "duplicate number 2", "5 cells, not 6",
    }
    assert body["plans"][0]["tasks"][0]["state"] == "untracked"
    assert response.headers["cache-control"] == "private, no-cache"
    assert response.headers["etag"].startswith('W/"')


async def test_the_etag_answers_304_until_something_changes(client, auth_headers, session):
    await _file(session)
    url = f"/api/v1/board/records?project={PROJECT}"
    etag = (await client.get(url, headers=auth_headers)).headers["etag"]
    same = await client.get(url, headers={**auth_headers, "If-None-Match": etag})
    assert same.status_code == 304
    assert same.headers["etag"] == etag

    await _file(session, "superpowers/plans/p.md", "# Plan\n")
    after_put = await client.get(url, headers={**auth_headers, "If-None-Match": etag})
    assert after_put.status_code == 200
    etag = after_put.headers["etag"]

    await worklog.append(
        session, project=PROJECT, key="w", run_key="claude:run-1",
        entries=[{"kind": "ledger", "body": "Task 1: x\n", "properties": {"task": 1}}],
        properties={"plan_uri": "superpowers/plans/p.md"},
    )
    after_append = await client.get(url, headers={**auth_headers, "If-None-Match": etag})
    assert after_append.status_code == 200


async def test_a_dmk_key_is_refused(client, session):
    _row, credential = await issue_key(session, name="k-board", scopes=["read", "capture", "admin"])
    response = await client.get(
        f"/api/v1/board/records?project={PROJECT}",
        headers={"Authorization": f"Bearer {credential}"},
    )
    assert response.status_code == 401
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_api/test_board_routes.py`
Expected: FAIL: the records route answers 404

- [ ] **Step 3: Write the schemas and the route**

Create `backend/app/schemas/board.py` with:

````python
"""Wire shapes of the progress board (spec 2026-10-13 §2.2)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlanProgress(BaseModel):
    done: int
    total: int
    # "no_workstream" or "no_properties" when the plan's tasks are untracked.
    untracked: str | None


class RegisterRow(BaseModel):
    number: int
    item: str
    assigned: str
    acceptance: str
    state: str
    raw_state: str
    note: str
    note_blank: bool
    line: int


class BoardRegisterRow(RegisterRow):
    plan_uri: str | None
    plan_progress: PlanProgress | None


class MalformedRow(BaseModel):
    line: int
    text: str
    reason: str


class BoardRegister(BaseModel):
    document_id: str
    uri: str
    title: str | None
    covers: str | None
    content_hash: str | None
    block_first: bool
    rows: list[BoardRegisterRow]
    malformed: list[MalformedRow]
    error: str | None


class TaskStep(BaseModel):
    checked: bool
    text: str


class PlanTask(BaseModel):
    number: int
    label: str
    title: str
    line: int
    state: str
    raw_state: str | None
    untracked: str | None
    shared_number: bool
    blocked_reason: str | None
    commit: str | None
    last_activity: datetime | None
    steps: list[TaskStep]


class PlanWorkstream(BaseModel):
    id: str
    key: str
    state: str


class BoardPlan(BaseModel):
    document_id: str
    uri: str
    title: str | None
    content_hash: str | None
    workstream: PlanWorkstream | None
    other_workstreams: int
    spec_uri: str | None
    untracked: str | None
    tasks: list[PlanTask]
    orphans: list[int]
    error: str | None


class BoardRecordsResponse(BaseModel):
    project: str
    registers: list[BoardRegister]
    plans: list[BoardPlan]
````

Create `backend/app/api/routes/board.py` with:

````python
"""The progress board's REST door (spec 2026-10-13 §2.2).

Provides:
  - GET    /api/v1/board/records

REST-only behind login: no MCP tool, no scope, and a `dmk_` key is refused.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import TokenPayload, require_auth
from app.database import get_session
from app.schemas.board import BoardRecordsResponse
from app.services.board import board_version, load_board

router = APIRouter(prefix="/api/v1/board", tags=["board"])

# Revalidate on every read: the browser sends If-None-Match by itself and a
# 304 costs two aggregates instead of a parse of every register and plan.
_CACHE_CONTROL = "private, no-cache"


def _matches(header: str | None, etag: str) -> bool:
    if not header:
        return False
    tags = [tag.strip() for tag in header.split(",")]
    return "*" in tags or etag in tags or etag.removeprefix("W/") in tags


@router.get("/records", response_model=BoardRecordsResponse)
async def board_records_route(
    request: Request,
    response: Response,
    project: str = Query(..., min_length=1),
    _user: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Every register row and plan task of `project`, derived on read."""
    etag = f'W/"{await board_version(session, project)}"'
    headers = {"ETag": etag, "Cache-Control": _CACHE_CONTROL}
    if _matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers=headers)
    response.headers.update(headers)
    return BoardRecordsResponse(**await load_board(session, project))
````

- [ ] **Step 4: Register the router**

In `backend/app/main.py` (the long `from app.api.routes import ...` line), replace:

````python
from app.api.routes import analytics, backups,
````

with:

````python
from app.api.routes import analytics, backups, board as board_routes,
````

In `backend/app/main.py`, replace:

````python
app.include_router(documents_routes.router)
````

with:

````python
app.include_router(documents_routes.router)
app.include_router(board_routes.router)
````

- [ ] **Step 5: Classify the route in the three enumeration guards**

In `backend/tests/test_api/test_rest_conformance.py`, replace:

````python
    ("GET", "/api/v1/mcp-calls"): 200,
````

with:

````python
    ("GET", "/api/v1/board/records"): 200,
    ("GET", "/api/v1/mcp-calls"): 200,
````

In `backend/app/services/content_surfaces.py`, replace:

````python
    "GET /api/v1/mcp-calls",
    "GET /api/v1/mcp-calls/summary",
````

with:

````python
    "GET /api/v1/mcp-calls",
    "GET /api/v1/mcp-calls/summary",
    # The progress board (spec 2026-10-13). Register and plan text crosses
    # these -- a document's own rows and task headings, plus ledger entry
    # properties -- but no `memories` row does: the board reads `documents`
    # and the work log, both walled off from the memory side, and is
    # REST-only (`board.reads` / `board.write` on docs/two-door-parity.md).
    # Views are layout definitions and carry no content at all.
    "GET /api/v1/board/records",
````

In `backend/tests/test_door_parity.py`, replace:

````python
    Surface(
        name="pages.reads",
````

with:

````python
    Surface(
        name="board.reads",
        status=REST_ONLY,
        rest=(
            ("GET", f"{V1}/board/records"),
        ),
        mcp=(),
        reason=(
            "The progress board is the operator's view of registers and plan "
            "tasks, a projection of documents and ledger entries an agent "
            "already reads over MCP: document_get serves a register's text and "
            "worklog_entries its ledger. A board tool would add a second shape "
            "of the same data, not a capability, and the saved views are the "
            "operator's layout. Nothing here generates or labels content, so no "
            "eval gate is in play; an MCP twin later is additive and an owner "
            "decision (spec 2026-10-13 section 8)."
        ),
    ),
    Surface(
        name="pages.reads",
````

Then regenerate the parity document's table and update its headline counts (the counts are test-enforced):

Run:

````bash
cd backend && .venv/bin/python -c "from tests.test_door_parity import render_markdown; print(render_markdown())" 2>/dev/null > /tmp/parity-table.md && python3 - <<'PY'
from pathlib import Path
doc = Path('../docs/two-door-parity.md')
text = doc.read_text(encoding='utf-8')
begin, end = '<!-- BEGIN GENERATED PARITY TABLE -->', '<!-- END GENERATED PARITY TABLE -->'
pre, rest = text.split(begin, 1)
_, post = rest.split(end, 1)
table = Path('/tmp/parity-table.md').read_text(encoding='utf-8').strip()
doc.write_text(pre + begin + '\n' + table + '\n' + end + post, encoding='utf-8')
PY
````

Expected: `git diff docs/two-door-parity.md` shows one added `board.reads` row. If it shows nothing, the import failed silently: re-run the first line without `2>/dev/null` to see why

In `docs/two-door-parity.md` (the headline counts sentence, outside the generated block), replace:

````markdown
**90 surfaces: 31 two-door, 59 single-door with a stated reason (52 REST-only, 7 MCP-only), 0 divergent.**
````

with:

````markdown
**91 surfaces: 31 two-door, 60 single-door with a stated reason (53 REST-only, 7 MCP-only), 0 divergent.**
````

- [ ] **Step 6: Run the tests and the guards leg**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_api/test_board_routes.py`
Expected: all pass

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py tests/test_event_taxonomy_map.py`
Expected: all pass (`CLAUDE.md`: the guards leg is mandatory after registering a route)

- [ ] **Step 7: Commit**

````bash
git add backend/app/schemas/board.py backend/app/api/routes/board.py backend/app/main.py backend/app/services/content_surfaces.py backend/tests/test_api/test_board_routes.py backend/tests/test_api/test_rest_conformance.py backend/tests/test_door_parity.py docs/two-door-parity.md
git commit -m "feat(board): serve the board's records with an ETag"
````

---

### Task 7: The register row edit service

**Files:**
- Create: `backend/app/services/board_edit.py`
- Modify: `backend/tests/test_block_retrieval.py` (`BLOCK_CHANNEL_MODULES`), `backend/tests/test_block_pipeline.py` (`FILING_CLOSURE`)
- Test: `backend/tests/test_board_edit.py`

**Interfaces:**
- Consumes: Task 2's `rewrite_register_row`, `RowEditRefused`, `BoardRefusal`; Task 3's `embed_inline`; `document_door.BLOCK_FIRST`, `DocumentIsBlockFirst`, `put_document`; `document_ingest.DocumentHashConflict` (existing).
- Produces: `edit_register_row(session, *, document_id, number, expected_hash, changes, actor) -> dict` with keys `document_id`, `content_hash`, `row`; raises `BoardRefusal` (Contracts §Refusals).

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

The membership test has its own planted-import negative control, as Task 5's does. This writes production registers. The put carries the caller's `expected_hash` into its own UPDATE, so a writer racing between this service's read and the put meets `DocumentHashConflict` rather than an overwrite; it passes no `properties` (ruling 8) and `embed_inline=False` (§2.4), so `llm` is `None`. The module stays out of `WORKLOG_MODULES`: it touches no work-log table and its `document_door` import would fail that wall.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_board_edit.py` with:

````python
"""The register row edit service (spec 2026-10-13 §2.2-§2.4)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services import board_edit
from app.services.board_edit import edit_register_row
from app.services.board_parse import BoardRefusal
from app.services.document_door import put_document
from app.services.document_ingest import DocumentHashConflict
from tests.test_block_pipeline import FILING_CLOSURE
from tests.test_block_retrieval import BLOCK_CHANNEL_MODULES
from tests.test_worklog_wall import WORKLOG_MODULES

URI = "superpowers/registers/r.md"
REGISTER = """# Register — edit

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | first | - | - | open | - |
"""


async def _file(session, uri=URI, content=REGISTER):
    return await put_document(
        session, None, project="p", uri=uri, content=content, embed_inline=False,
    )


async def _edit(session, filed, number=1, expected_hash=None, **changes):
    return await edit_register_row(
        session, document_id=filed.document_id, number=number,
        expected_hash=expected_hash or filed.content_hash, changes=changes, actor="admin",
    )


async def test_an_edit_answers_the_row_and_writes_one_revision(session):
    filed = await _file(session)
    result = await _edit(session, filed, state="verify", note="check the board")
    assert result["row"]["state"] == "verify"
    assert result["row"]["note"] == "check the board"
    assert result["content_hash"] != filed.content_hash
    actors = (await session.execute(
        text("SELECT actor FROM document_revisions WHERE document_id = CAST(:d AS uuid) "
             "ORDER BY created_at, id"),
        {"d": filed.document_id},
    )).scalars().all()
    assert actors == [None, "admin"]


async def test_the_same_value_files_nothing_new(session):
    filed = await _file(session)
    result = await _edit(session, filed, state="open")
    assert result["content_hash"] == filed.content_hash


@pytest.mark.parametrize("changes, reason, status", [
    ({}, "no_change", 422),
    ({"state": "parked"}, "unknown_state", 422),
    ({"state": "n/a"}, "note_required", 422),
])
async def test_refusals_carry_reason_and_status(session, changes, reason, status):
    filed = await _file(session)
    with pytest.raises(BoardRefusal) as refused:
        await _edit(session, filed, **changes)
    assert (refused.value.reason, refused.value.status_code) == (reason, status)


async def test_a_missing_row_is_not_found(session):
    filed = await _file(session)
    with pytest.raises(BoardRefusal) as refused:
        await _edit(session, filed, number=7, state="done")
    assert (refused.value.reason, refused.value.status_code) == ("not_found", 404)


async def test_a_document_outside_registers_is_not_found(session):
    filed = await _file(session, uri="superpowers/plans/r.md")
    with pytest.raises(BoardRefusal) as refused:
        await _edit(session, filed, state="done")
    assert refused.value.reason == "not_found"


async def test_a_stale_hash_names_the_current_one(session):
    filed = await _file(session)
    with pytest.raises(BoardRefusal) as refused:
        await _edit(session, filed, expected_hash="stale", state="done")
    assert refused.value.reason == "hash_conflict"
    assert refused.value.fields == {"current_hash": filed.content_hash}


async def test_a_race_lost_inside_the_put_is_a_hash_conflict(session, monkeypatch):
    filed = await _file(session)

    async def lost(*_args, **_kwargs):
        raise DocumentHashConflict(
            document_id=filed.document_id, expected_hash=filed.content_hash, current_hash="winner",
        )

    monkeypatch.setattr(board_edit, "put_document", lost)
    with pytest.raises(BoardRefusal) as refused:
        await _edit(session, filed, state="done")
    assert refused.value.reason == "hash_conflict"
    assert refused.value.fields == {"current_hash": "winner"}


async def test_the_put_carries_no_properties_and_no_inline_embed(session, monkeypatch):
    filed = await _file(session)
    seen = {}
    real = board_edit.put_document

    async def spy(session_, llm, **kwargs):
        seen.update(kwargs, llm=llm)
        return await real(session_, llm, **kwargs)

    monkeypatch.setattr(board_edit, "put_document", spy)
    await _edit(session, filed, state="done")
    assert seen["llm"] is None
    assert seen["embed_inline"] is False
    assert "properties" not in seen
    assert seen["expected_hash"] == filed.content_hash
    assert seen["actor"] == "admin"


def test_the_edit_service_sits_on_the_filing_path_and_outside_the_work_log_wall():
    assert "app.services.board_edit" in FILING_CLOSURE
    assert "app.services.board_edit" in BLOCK_CHANNEL_MODULES
    assert "app.services.board_edit" not in WORKLOG_MODULES


def test_the_scan_would_see_the_edit_service_reach_the_pipeline(tmp_path):
    """Negative control: a planted board_edit that imports the pipeline is caught."""
    from tests._reachability_scan import import_closure

    services = tmp_path / "app" / "services"
    services.mkdir(parents=True)
    (tmp_path / "app" / "__init__.py").write_text("")
    (services / "__init__.py").write_text("")
    (services / "board_edit.py").write_text("from app.services import pipeline\n")
    (services / "pipeline.py").write_text("")
    assert "app.services.pipeline" in import_closure(tmp_path, "app.services.board_edit")
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_board_edit.py`
Expected: collection error, `ModuleNotFoundError: No module named 'app.services.board_edit'`

- [ ] **Step 3: Write the service**

Create `backend/app/services/board_edit.py` with:

````python
"""The board's one write: a register row edit filed as a document put (spec 2026-10-13 §2.2).

Outside `board` on purpose: filing goes through `document_door`, whose import
closure carries memory models, and `board` sits inside the work-log wall.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.board_parse import (
    REGISTER_PREFIX,
    REGISTER_STATES,
    BoardRefusal,
    RowEditRefused,
    is_blank_note,
    parse_register,
    rewrite_register_row,
)
from app.services.document_door import BLOCK_FIRST, DocumentIsBlockFirst, put_document
from app.services.document_ingest import DocumentHashConflict

_REFUSAL_STATUS = {"not_found": 404}

_DOCUMENT = text(
    "SELECT project, uri, content, content_hash, "
    "       properties->>'ingest_direction' AS direction "
    "FROM documents WHERE id = CAST(:id AS uuid)"
)


def _hash_conflict(current_hash: str | None) -> BoardRefusal:
    return BoardRefusal(
        409, "hash_conflict",
        "this register changed since it was loaded; reload it and try again",
        current_hash=current_hash,
    )


def _block_first() -> BoardRefusal:
    return BoardRefusal(
        409, "block_first",
        "this register was converted to block-first and its content is owned by "
        "the block verbs; delete and re-file it to edit it from the board",
    )


async def edit_register_row(
    session: AsyncSession,
    *,
    document_id: str,
    number: int,
    expected_hash: str,
    changes: dict[str, str],
    actor: str,
) -> dict[str, Any]:
    """Rewrite one row and file the register; answers the row and the new hash.

    The put takes the row lock and compares `expected_hash` inside its own
    UPDATE, so a racing writer meets a conflict rather than an overwrite. It
    passes no `properties` (ruling 8) and embeds nothing (§2.4).
    """
    if not changes:
        raise BoardRefusal(422, "no_change", "name at least one of state, note or assigned")
    document = (await session.execute(_DOCUMENT, {"id": document_id})).first()
    if (
        document is None
        or document.uri is None
        or not document.uri.startswith(REGISTER_PREFIX)
        or not document.uri.endswith(".md")
    ):
        raise BoardRefusal(404, "not_found", f"no register with id {document_id}")
    if document.direction == BLOCK_FIRST:
        raise _block_first()
    if document.content_hash != expected_hash:
        raise _hash_conflict(document.content_hash)
    try:
        updated = rewrite_register_row(document.content or "", number, changes)
    except RowEditRefused as exc:
        raise BoardRefusal(_REFUSAL_STATUS.get(exc.reason, 422), exc.reason, str(exc)) from exc
    try:
        result = await put_document(
            session, None,
            project=document.project, uri=document.uri, content=updated,
            actor=actor, source="api", expected_hash=expected_hash, embed_inline=False,
        )
    except DocumentHashConflict as exc:
        raise _hash_conflict(exc.current_hash) from exc
    except DocumentIsBlockFirst as exc:
        raise _block_first() from exc
    row = next(r for r in parse_register(updated).rows if r.number == number)
    return {
        "document_id": result.document_id,
        "content_hash": result.content_hash,
        "row": {
            "number": row.number,
            "item": row.item,
            "assigned": row.assigned,
            "acceptance": row.acceptance,
            "state": row.state if row.state in REGISTER_STATES else "unrecognised",
            "raw_state": row.state,
            "note": row.note,
            "note_blank": is_blank_note(row.note),
            "line": row.line,
        },
    }
````

- [ ] **Step 4: Classify it**

In `backend/tests/test_block_retrieval.py`, replace:

````python
    "app.services.board",
````

with:

````python
    "app.services.board",
    # Reads a register's filed content to rewrite one row.
    "app.services.board_edit",
````

In `backend/tests/test_block_pipeline.py`, replace:

````python
# `block_verbs` seeds the closure too: it writes blocks, so it is a filing
# path, and its own import graph must not reach the memory pipeline either.
FILING_CLOSURE = import_closure(
    BACKEND, "app.services.block_pipeline", DOCUMENT_DOOR, "app.services.block_verbs"
)
````

with:

````python
# `block_verbs` seeds the closure too: it writes blocks, so it is a filing
# path, and its own import graph must not reach the memory pipeline either.
# `board_edit` files register edits through the door, so it seeds it as well.
FILING_CLOSURE = import_closure(
    BACKEND, "app.services.block_pipeline", DOCUMENT_DOOR, "app.services.block_verbs",
    "app.services.board_edit",
)
````

- [ ] **Step 5: Run the tests and the walls**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_board_edit.py tests/test_block_retrieval.py tests/test_block_pipeline.py tests/test_worklog_wall.py`
Expected: all pass

- [ ] **Step 6: Commit**

````bash
git add backend/app/services/board_edit.py backend/tests/test_board_edit.py backend/tests/test_block_retrieval.py backend/tests/test_block_pipeline.py
git commit -m "feat(board): edit a register row as a hash-guarded put"
````

---

### Task 8: The register row edit route

**Files:**
- Modify: `backend/app/schemas/board.py` (append), `backend/app/api/routes/board.py`, `backend/app/main.py` (refusal handler)
- Modify: `backend/tests/test_api/test_rest_conformance.py`, `backend/app/services/content_surfaces.py`, `backend/tests/test_door_parity.py`, `docs/two-door-parity.md`
- Test: `backend/tests/test_api/test_board_row_edit_route.py`

**Interfaces:**
- Consumes: Task 7's `edit_register_row`; Task 2's `BoardRefusal`.
- Produces: `PATCH /api/v1/board/registers/{document_id}/rows/{number}` with `RegisterRowEditRequest`, answering `RegisterRowEditResponse`; every `BoardRefusal` answered as `{error: {code: reason, message, details: [fields] | null}, detail: message}` (Contracts §REST, §Refusals); the `board.write` parity row.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

Not behind `refuse_when_read_only` (spec §2.2 as amended): with no inline embed the route writes rows only, which the viewer role's SQLSTATE 42501 handler already refuses on the backup worker. The route does not depend on `get_llm`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_api/test_board_row_edit_route.py` with:

````python
"""The board's register row edit route (spec 2026-10-13 §2.2-§2.4)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.services.api_keys import issue_key
from app.services.document_door import put_document

PROJECT = "board-routes"
REGISTER_URI = "superpowers/registers/r.md"
REGISTER = """# Register — routes

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | first | - | - | open | - |
| 2 | dup | - | - | open | - |
| 2 | dup again | - | - | open | - |
| 3 | short | - | open | - |
"""


@pytest.fixture
def no_llm(client):
    """The edit must not need an embedder: leave the app without one."""
    from app.main import app

    previous = getattr(app.state, "llm", None)
    app.state.llm = None
    yield
    app.state.llm = previous


async def _file(session, uri=REGISTER_URI, content=REGISTER):
    return await put_document(
        session, None, project=PROJECT, uri=uri, content=content, embed_inline=False,
    )


async def _revisions(session, document_id):
    return (await session.execute(
        text("SELECT actor FROM document_revisions WHERE document_id = CAST(:d AS uuid) "
             "ORDER BY created_at, id"),
        {"d": document_id},
    )).scalars().all()


def _patch(client, headers, document_id, number, **body):
    return client.patch(
        f"/api/v1/board/registers/{document_id}/rows/{number}", json=body, headers=headers,
    )


async def test_a_dmk_key_is_refused(client, session):
    _row, credential = await issue_key(session, name="k-board", scopes=["read", "capture", "admin"])
    response = await client.patch(
        "/api/v1/board/registers/00000000-0000-4000-8000-0000000000b1/rows/1",
        json={"expected_hash": "h", "state": "done"},
        headers={"Authorization": f"Bearer {credential}"},
    )
    assert response.status_code == 401


async def test_an_edit_files_one_revision_by_the_login_and_needs_no_embedder(
    client, auth_headers, session, no_llm,
):
    filed = await _file(session)
    response = await _patch(client, auth_headers, filed.document_id, 1,
                            expected_hash=filed.content_hash, state="doing")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["row"]["state"] == "doing"
    assert body["content_hash"] != filed.content_hash
    assert await _revisions(session, filed.document_id) == [None, "admin"]
    content = (await session.execute(
        text("SELECT content FROM documents WHERE id = CAST(:d AS uuid)"),
        {"d": filed.document_id},
    )).scalar_one()
    assert content == REGISTER.replace("| 1 | first | - | - | open | - |",
                                       "| 1 | first | - | - | doing | - |")


async def test_a_stale_hash_is_a_409_naming_the_current_hash(client, auth_headers, session):
    filed = await _file(session)
    response = await _patch(client, auth_headers, filed.document_id, 1,
                            expected_hash="stale", state="done")
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "hash_conflict"
    assert error["details"] == [{"current_hash": filed.content_hash}]


async def test_a_block_first_register_is_a_409(client, auth_headers, session):
    filed = await _file(session)
    await session.execute(
        text("UPDATE documents SET properties = "
             "coalesce(properties, CAST('{}' AS jsonb)) || CAST(:props AS jsonb) "
             "WHERE id = CAST(:id AS uuid)"),
        {"id": filed.document_id, "props": '{"ingest_direction": "blocks"}'},
    )
    response = await _patch(client, auth_headers, filed.document_id, 1,
                            expected_hash=filed.content_hash, state="done")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "block_first"


@pytest.mark.parametrize("number, body, status, reason", [
    (9, {"state": "done"}, 404, "not_found"),
    (2, {"state": "done"}, 422, "duplicate_row"),
    (3, {"state": "done"}, 422, "malformed_row"),
    (1, {"state": "parked"}, 422, "unknown_state"),
    (1, {"state": "verify"}, 422, "note_required"),
    (1, {"note": "two\nlines"}, 422, "invalid_cell"),
    (1, {}, 422, "no_change"),
])
async def test_row_refusals(client, auth_headers, session, number, body, status, reason):
    filed = await _file(session)
    response = await _patch(client, auth_headers, filed.document_id, number,
                            expected_hash=filed.content_hash, **body)
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == reason
    assert await _revisions(session, filed.document_id) == [None]


async def test_an_unknown_document_and_a_non_register_are_404(client, auth_headers, session):
    plan = await _file(session, "superpowers/plans/p.md", REGISTER)
    for document_id in (str(uuid.uuid4()), plan.document_id):
        response = await _patch(client, auth_headers, document_id, 1,
                                expected_hash=plan.content_hash, state="done")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


async def test_an_unknown_body_field_is_refused(client, auth_headers, session):
    filed = await _file(session)
    response = await _patch(client, auth_headers, filed.document_id, 1,
                            expected_hash=filed.content_hash, item="renamed")
    assert response.status_code == 422
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_api/test_board_row_edit_route.py`
Expected: FAIL: the PATCH answers 404 or 405

- [ ] **Step 3: Add the request and response models**

Append to `backend/app/schemas/board.py`, at the end of the file:

````python


class RegisterRowEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_hash: str = Field(min_length=1)
    state: str | None = None
    note: str | None = None
    assigned: str | None = None


class RegisterRowEditResponse(BaseModel):
    document_id: str
    content_hash: str
    row: RegisterRow
````

- [ ] **Step 4: Add the route**

In `backend/app/api/routes/board.py`, replace:

````python
Provides:
  - GET    /api/v1/board/records

REST-only behind login: no MCP tool, no scope, and a `dmk_` key is refused.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
````

with:

````python
Provides:
  - GET    /api/v1/board/records
  - PATCH  /api/v1/board/registers/{document_id}/rows/{number}

REST-only behind login: no MCP tool, no scope, and a `dmk_` key is refused.
Refusals raise `BoardRefusal`, which `app.main` answers with `error.code` set
to the refusal's reason.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
````

In `backend/app/api/routes/board.py`, replace:

````python
from app.schemas.board import BoardRecordsResponse
from app.services.board import board_version, load_board
````

with:

````python
from app.schemas.board import (
    BoardRecordsResponse,
    RegisterRowEditRequest,
    RegisterRowEditResponse,
)
from app.services.board import board_version, load_board
from app.services.board_edit import edit_register_row
````

Append to `backend/app/api/routes/board.py`, at the end of the file:

````python


@router.patch(
    "/registers/{document_id}/rows/{number}", response_model=RegisterRowEditResponse,
)
async def edit_register_row_route(
    document_id: UUID,
    number: int,
    body: RegisterRowEditRequest,
    user: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> RegisterRowEditResponse:
    """Edit one register row's state, note or assigned, as a document revision."""
    changes = {
        column: value
        for column, value in (("state", body.state), ("note", body.note), ("assigned", body.assigned))
        if value is not None
    }
    result = await edit_register_row(
        session,
        document_id=str(document_id),
        number=number,
        expected_hash=body.expected_hash,
        changes=changes,
        actor=user.sub,
    )
    return RegisterRowEditResponse(**result)
````

- [ ] **Step 5: Answer refusals with their reason**

In `backend/app/main.py`, replace:

````python
from app.services.git_accounts import GitAccountInUse
````

with:

````python
from app.services.git_accounts import GitAccountInUse
from app.services.board_parse import BoardRefusal
````

In `backend/app/main.py`, replace:

````python
@app.exception_handler(GitAccountInUse)
````

with:

````python
@app.exception_handler(BoardRefusal)
async def _board_refusal_handler(_request, exc: BoardRefusal):
    """The board's refusals carry their reason as `error.code`.

    Its own handler because a dict `detail` on the generic HTTPException path
    is flattened to "Request failed"; the reason and its fields are what let
    the SPA tell a hash conflict from a missing Note.
    """
    return _error_response(
        exc.status_code, exc.reason, exc.message, [exc.fields] if exc.fields else None,
    )


@app.exception_handler(GitAccountInUse)
````

- [ ] **Step 6: Classify the route in the three guards**

In `backend/tests/test_api/test_rest_conformance.py`, replace:

````python
    ("GET", "/api/v1/board/records"): 200,
````

with:

````python
    ("GET", "/api/v1/board/records"): 200,
    ("PATCH", "/api/v1/board/registers/{document_id}/rows/{number}"): 200,
````

In `backend/app/services/content_surfaces.py`, replace:

````python
    "GET /api/v1/board/records",
````

with:

````python
    "GET /api/v1/board/records",
    "PATCH /api/v1/board/registers/{document_id}/rows/{number}",
````

In `backend/tests/test_door_parity.py`, replace:

````python
    Surface(
        name="pages.reads",
````

with:

````python
    Surface(
        name="board.write",
        status=REST_ONLY,
        rest=(
            ("PATCH", f"{V1}/board/registers/{{document_id}}/rows/{{number}}"),
        ),
        mcp=(),
        reason=(
            "A register row edit is the operator moving a card; an agent edits "
            "the same register through document_put with expected_hash, which "
            "is the write the row edit itself files, so a tool would duplicate "
            "a door that already exists on MCP. Saved views are the operator's "
            "layout and hold no data. Single-door by owner ruling (spec "
            "2026-10-13 section 8: no MCP tool for the board or its views)."
        ),
    ),
    Surface(
        name="pages.reads",
````

Regenerate the parity table, then move the headline:

Run:

````bash
cd backend && .venv/bin/python -c "from tests.test_door_parity import render_markdown; print(render_markdown())" 2>/dev/null > /tmp/parity-table.md && python3 - <<'PY'
from pathlib import Path
doc = Path('../docs/two-door-parity.md')
text = doc.read_text(encoding='utf-8')
begin, end = '<!-- BEGIN GENERATED PARITY TABLE -->', '<!-- END GENERATED PARITY TABLE -->'
pre, rest = text.split(begin, 1)
_, post = rest.split(end, 1)
table = Path('/tmp/parity-table.md').read_text(encoding='utf-8').strip()
doc.write_text(pre + begin + '\n' + table + '\n' + end + post, encoding='utf-8')
PY
````

Expected: `git diff docs/two-door-parity.md` shows one added `board.write` row (re-run the first line without `2>/dev/null` if it shows nothing)

In `docs/two-door-parity.md` (the headline counts sentence), replace:

````markdown
**91 surfaces: 31 two-door, 60 single-door with a stated reason (53 REST-only, 7 MCP-only), 0 divergent.**
````

with:

````markdown
**92 surfaces: 31 two-door, 61 single-door with a stated reason (54 REST-only, 7 MCP-only), 0 divergent.**
````

- [ ] **Step 7: Run the tests and the guards leg**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_api/test_board_row_edit_route.py tests/test_api/test_board_routes.py tests/test_board_edit.py`
Expected: all pass

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py tests/test_event_taxonomy_map.py`
Expected: all pass

- [ ] **Step 8: Commit**

````bash
git add backend/app/schemas/board.py backend/app/api/routes/board.py backend/app/main.py backend/app/services/content_surfaces.py backend/tests/test_api/test_board_row_edit_route.py backend/tests/test_api/test_rest_conformance.py backend/tests/test_door_parity.py docs/two-door-parity.md
git commit -m "feat(board): edit a register row from the board"
````

---

### Task 9: The `board_views` table and its service

**Files:**
- Create: `backend/migrations/versions/0003_board_views.py`, `backend/app/services/board_views.py`
- Test: `backend/tests/test_board_views_service.py`

**Interfaces:**
- Consumes: Task 2's `BoardRefusal`.
- Produces: table `board_views`; `PROPERTIES`, `GROUPABLE`, `BUILTIN_VIEWS`, `ViewDefinition`, `validate_definition`, `list_views`, `create_view`, `update_view`, `delete_view` (Contracts §Views).

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 3 = 5

A schema change on a deployed database. The revision is additive (one new table, its trigger and constraints) with `down_revision = '0002'`, the current single head (`backend/migrations/versions/0002_mcp_tool_calls.py`). Never touch `0001_baseline.py`. If another lane has added a revision since, rebase this one's `down_revision` onto that head (the single-head assertion in `tests/test_schema_guard.py` enforces it).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_board_views_service.py` with:

````python
"""The saved-view service and its table (spec 2026-10-13 §2.6)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services.board_parse import BoardRefusal
from app.services.board_views import (
    BUILTIN_VIEWS,
    create_view,
    delete_view,
    list_views,
    update_view,
    validate_definition,
)

DEFINITION = {"layout": "board", "group_by": "state"}


async def test_a_view_round_trips_with_schema_defaults_filled(session):
    view = await create_view(session, project="p", name="Mine", definition=DEFINITION, position=None)
    assert view["position"] == 0 and view["builtin"] is False
    assert view["definition"] == {
        "layout": "board", "group_by": "state", "filters": [], "sort": None,
        "columns": [], "show_untracked": False,
    }
    listed = await list_views(session, "p")
    assert [v["id"] for v in listed] == [v["id"] for v in BUILTIN_VIEWS] + [view["id"]]


async def test_positions_default_past_the_greatest(session):
    await create_view(session, project="p", name="A", definition=DEFINITION, position=4)
    second = await create_view(session, project="p", name="B", definition=DEFINITION, position=None)
    assert second["position"] == 5


async def test_names_are_unique_per_project_only(session):
    await create_view(session, project="p", name="Same", definition=DEFINITION, position=None)
    await create_view(session, project="q", name="Same", definition=DEFINITION, position=None)
    with pytest.raises(BoardRefusal) as refused:
        await create_view(session, project="p", name="Same", definition=DEFINITION, position=None)
    assert (refused.value.status_code, refused.value.reason) == (409, "name_taken")


async def test_update_moves_updated_at_through_the_trigger(session):
    view = await create_view(session, project="p", name="Mine", definition=DEFINITION, position=None)
    await session.execute(
        text("UPDATE board_views SET updated_at = now() - interval '1 day' WHERE id = CAST(:id AS uuid)"),
        {"id": view["id"]},
    )
    updated = await update_view(session, view["id"], changes={"name": "Renamed"})
    assert updated["name"] == "Renamed"
    # The test runs in one transaction, so the trigger's now() is created_at's.
    assert updated["updated_at"] == updated["created_at"]


async def test_delete_then_unknown(session):
    view = await create_view(session, project="p", name="Mine", definition=DEFINITION, position=None)
    await delete_view(session, view["id"])
    with pytest.raises(BoardRefusal) as refused:
        await delete_view(session, view["id"])
    assert refused.value.reason == "not_found"


@pytest.mark.parametrize("view_id, reason", [
    ("builtin:open-register-items", "builtin_view"),
    ("nonsense", "not_found"),
])
async def test_ids_that_name_no_saved_view(session, view_id, reason):
    with pytest.raises(BoardRefusal) as refused:
        await update_view(session, view_id, changes={"name": "x"})
    assert refused.value.reason == reason


def test_an_oversized_definition_is_refused_before_the_check_could_fire():
    big = {**DEFINITION, "filters": [
        {"property": "note", "operator": "contains", "values": ["x" * 200] * 200},
    ]}
    with pytest.raises(BoardRefusal) as refused:
        validate_definition(big)
    assert refused.value.reason == "invalid_definition"


async def test_the_table_check_bounds_what_the_door_would_never_send(session):
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await session.execute(
                text("INSERT INTO board_views (project, name, position, definition) "
                     "VALUES ('p', '', 0, CAST('{}' AS jsonb))"),
            )


async def test_a_definition_the_check_refuses_is_invalid_not_a_500(session, monkeypatch):
    """The door measures JSON text, the CHECK measures JSONB; when they
    disagree the refusal must still be `invalid_definition`."""
    import secrets

    from app.services import board_views

    noise = secrets.token_hex(12_000)
    monkeypatch.setattr(board_views, "validate_definition", lambda _d: {"layout": "board", "x": noise})
    with pytest.raises(BoardRefusal) as refused:
        await create_view(session, project="p", name="Huge", definition=DEFINITION, position=None)
    assert (refused.value.status_code, refused.value.reason) == (422, "invalid_definition")
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_board_views_service.py`
Expected: collection error, `ModuleNotFoundError: No module named 'app.services.board_views'`

- [ ] **Step 3: Write the revision**

Create `backend/migrations/versions/0003_board_views.py` with:

````python
"""board_views: the progress board's saved views

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-13

A saved view is layout, not data: a name, a position among the project's
views and a definition (layout, grouping, filters, sort, columns) validated
against a closed schema at the door before it reaches the CHECK below. The
two built-in views are code constants (`app.services.board_views`) and never
rows. Views journal nothing.

Additive only: a new table, its trigger and its constraints, no existing row
touched, so it upgrades a populated database in place.
"""
from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE board_views (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project     TEXT NOT NULL,
            name        TEXT NOT NULL,
            position    INTEGER NOT NULL,
            definition  JSONB NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ux_board_views_project_name UNIQUE (project, name),
            CONSTRAINT chk_board_views_name_len CHECK (char_length(name) BETWEEN 1 AND 100),
            CONSTRAINT chk_board_views_definition_size
                CHECK (pg_column_size(definition) <= 16384)
        )
        """
    )
    op.execute(
        "CREATE TRIGGER board_views_touch_updated_at BEFORE UPDATE "
        "ON board_views FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS board_views")
````

- [ ] **Step 4: Write the service**

The door's byte bound measures compact JSON text while the table's CHECK measures stored JSONB, which spends a header per element, so the service also maps a CHECK violation (SQLSTATE 23514) to `invalid_definition`: the CHECK must never answer 500. `Literal[PROPERTIES]` with a tuple is deliberate: pydantic reads it as the literal union of the tuple's members, so the schema and the property list cannot drift.

Create `backend/app/services/board_views.py` with:

````python
"""The progress board's saved views (spec 2026-10-13 §2.6).

Two built-ins are code constants, listed first and never written; saved views
are `board_views` rows. A definition is checked against a closed schema and a
byte bound here, at the door, so the table's CHECK never answers a 500.
"""
from __future__ import annotations

import json
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.board_parse import BoardRefusal

PROPERTIES = (
    "type", "title", "number", "state", "source", "note", "assigned", "acceptance",
    "plan_progress", "plan", "spec", "workstream_state", "commit", "last_activity",
)
GROUPABLE = ("type", "state", "source", "assigned", "plan", "workstream_state")
MAX_DEFINITION_BYTES = 16_384
BUILTIN_PREFIX = "builtin:"

Property = Literal[PROPERTIES]  # type: ignore[valid-type]
Groupable = Literal[GROUPABLE]  # type: ignore[valid-type]


class ViewFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property: Property
    operator: Literal["in", "not_in", "contains"]
    values: list[str] = Field(max_length=200)


class ViewSort(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property: Property
    direction: Literal["asc", "desc"]


class ViewDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout: Literal["board", "table"]
    group_by: Groupable | None = None
    filters: list[ViewFilter] = Field(default_factory=list, max_length=20)
    sort: ViewSort | None = None
    columns: list[Property] = Field(default_factory=list, max_length=len(PROPERTIES))
    show_untracked: bool = False


_DEFAULT_COLUMNS = ["type", "number", "title", "state", "source", "assigned", "note"]

BUILTIN_VIEWS: tuple[dict[str, Any], ...] = (
    {
        "id": "builtin:open-register-items",
        "name": "Open register items",
        "builtin": True,
        "position": 0,
        "definition": {
            "layout": "board",
            "group_by": "state",
            "filters": [
                {"property": "type", "operator": "in", "values": ["register_row"]},
                {"property": "state", "operator": "not_in", "values": ["done", "n/a"]},
            ],
            "sort": {"property": "number", "direction": "asc"},
            "columns": _DEFAULT_COLUMNS,
            "show_untracked": False,
        },
    },
    {
        "id": "builtin:plans-in-flight",
        "name": "Plans in flight",
        "builtin": True,
        "position": 1,
        "definition": {
            "layout": "board",
            "group_by": "plan",
            "filters": [
                {"property": "type", "operator": "in", "values": ["plan_task"]},
                {"property": "workstream_state", "operator": "in", "values": ["open"]},
            ],
            "sort": {"property": "number", "direction": "asc"},
            "columns": ["number", "title", "state", "plan", "commit", "last_activity"],
            "show_untracked": False,
        },
    },
)

_COLUMNS = (
    "CAST(id AS text) AS id, project, name, position, definition, created_at, updated_at"
)
_LIST = text(
    f"SELECT {_COLUMNS} FROM board_views WHERE project = CAST(:project AS text) "
    "ORDER BY position, name"
)
_GET = text(f"SELECT {_COLUMNS} FROM board_views WHERE id = CAST(:id AS uuid)")
_NEXT_POSITION = text(
    "SELECT coalesce(max(position), -1) + 1 FROM board_views WHERE project = CAST(:project AS text)"
)
_INSERT = text(
    "INSERT INTO board_views (project, name, position, definition) "
    "VALUES (CAST(:project AS text), CAST(:name AS text), :position, CAST(:definition AS jsonb)) "
    f"RETURNING {_COLUMNS}"
)
_DELETE = text("DELETE FROM board_views WHERE id = CAST(:id AS uuid)")


def _row(row: Any) -> dict[str, Any]:
    return {**dict(row._mapping), "builtin": False}


def validate_definition(definition: Any) -> dict[str, Any]:
    try:
        checked = ViewDefinition.model_validate(definition)
    except ValidationError as exc:
        raise BoardRefusal(
            422, "invalid_definition", f"the view definition is invalid: {exc.errors()[0]['msg']}",
        ) from exc
    value = checked.model_dump()
    size = len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    if size > MAX_DEFINITION_BYTES:
        raise BoardRefusal(
            422, "invalid_definition",
            f"the view definition encodes to {size} bytes; the bound is {MAX_DEFINITION_BYTES}",
        )
    return value


def _view_id(view_id: str) -> str:
    """A saved view's uuid; a built-in id is refused, anything else is unknown."""
    if view_id.startswith(BUILTIN_PREFIX):
        raise BoardRefusal(
            422, "builtin_view", "built-in views cannot be changed; save a copy as a new view",
        )
    try:
        return str(UUID(view_id))
    except ValueError as exc:
        raise BoardRefusal(404, "not_found", f"no view with id {view_id}") from exc


def _name_taken(project: str, name: str) -> BoardRefusal:
    return BoardRefusal(409, "name_taken", f"project {project!r} already has a view named {name!r}")


def _sqlstate(exc: IntegrityError) -> str | None:
    return getattr(getattr(exc, "orig", None), "sqlstate", None)


def _refusal(exc: IntegrityError, project: str, name: str | None) -> BoardRefusal | None:
    """A uniqueness clash, or the size CHECK.

    The door's byte bound measures compact JSON text, while the CHECK measures
    the stored JSONB, which spends a header per element; a definition of many
    tiny values can pass one and fail the other, and must not answer 500.
    """
    if _sqlstate(exc) == "23505":
        return _name_taken(project, name or "")
    if _sqlstate(exc) == "23514":
        return BoardRefusal(
            422, "invalid_definition", "the view definition is too large to store",
        )
    return None


async def list_views(session: AsyncSession, project: str) -> list[dict[str, Any]]:
    saved = [_row(r) for r in await session.execute(_LIST, {"project": project})]
    builtins = [
        {**view, "project": project, "created_at": None, "updated_at": None}
        for view in BUILTIN_VIEWS
    ]
    return builtins + saved


async def create_view(
    session: AsyncSession, *, project: str, name: str, definition: Any, position: int | None,
) -> dict[str, Any]:
    checked = validate_definition(definition)
    if position is None:
        position = (await session.execute(_NEXT_POSITION, {"project": project})).scalar_one()
    try:
        async with session.begin_nested():
            row = (await session.execute(_INSERT, {
                "project": project, "name": name, "position": position,
                "definition": json.dumps(checked),
            })).one()
    except IntegrityError as exc:
        refusal = _refusal(exc, project, name)
        if refusal is not None:
            raise refusal from exc
        raise
    await session.commit()
    return _row(row)


async def update_view(
    session: AsyncSession, view_id: str, *, changes: dict[str, Any],
) -> dict[str, Any]:
    target = _view_id(view_id)
    if not changes:
        raise BoardRefusal(422, "no_change", "name at least one of name, definition or position")
    current = (await session.execute(_GET, {"id": target})).first()
    if current is None:
        raise BoardRefusal(404, "not_found", f"no view with id {view_id}")
    assignments, params = [], {"id": target}
    if "name" in changes:
        assignments.append("name = CAST(:name AS text)")
        params["name"] = changes["name"]
    if "definition" in changes:
        assignments.append("definition = CAST(:definition AS jsonb)")
        params["definition"] = json.dumps(validate_definition(changes["definition"]))
    if "position" in changes:
        assignments.append("position = :position")
        params["position"] = changes["position"]
    statement = text(
        f"UPDATE board_views SET {', '.join(assignments)} WHERE id = CAST(:id AS uuid) "
        f"RETURNING {_COLUMNS}"
    )
    try:
        async with session.begin_nested():
            row = (await session.execute(statement, params)).one()
    except IntegrityError as exc:
        refusal = _refusal(exc, current.project, changes.get("name"))
        if refusal is not None:
            raise refusal from exc
        raise
    await session.commit()
    return _row(row)


async def delete_view(session: AsyncSession, view_id: str) -> None:
    target = _view_id(view_id)
    result = await session.execute(_DELETE, {"id": target})
    if result.rowcount == 0:
        raise BoardRefusal(404, "not_found", f"no view with id {view_id}")
    await session.commit()
````

- [ ] **Step 5: Run the tests and the schema guard**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_board_views_service.py tests/test_schema_guard.py`
Expected: all pass (the conftest migrates the empty test schema to head, so 0003 runs)

- [ ] **Step 6: Run the revision against a restored backup holding data**

The test suite proves the revision runs, not that it keeps rows (`CLAUDE.md`). Restore the newest dump into `darkmem_bench` (the harness database, free to reset), count rows, upgrade, count again:

````bash
DUMP=$(ls -t /root/darkmem-backups/darkmem-*.sql.gz | head -1); echo "$DUMP"
docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -qc "DROP DATABASE IF EXISTS darkmem_bench" -c "CREATE DATABASE darkmem_bench"
zcat "$DUMP" | docker exec -i darkmem-postgres-1 psql -U darkmem -d darkmem_bench -q -v ON_ERROR_STOP=1 > /dev/null
COUNTS="SELECT 'events', count(*) FROM events UNION ALL SELECT 'config', count(*) FROM config UNION ALL SELECT 'documents', count(*) FROM documents"
docker exec darkmem-postgres-1 psql -U darkmem -d darkmem_bench -Atc "$COUNTS" > /tmp/before.txt
(cd backend && DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench .venv/bin/python -m alembic upgrade head)
docker exec darkmem-postgres-1 psql -U darkmem -d darkmem_bench -Atc "$COUNTS" > /tmp/after.txt
diff /tmp/before.txt /tmp/after.txt && echo ROWS-KEPT
docker exec darkmem-postgres-1 psql -U darkmem -d darkmem_bench -Atc "SELECT version_num FROM alembic_version" -c "SELECT tgname FROM pg_trigger WHERE tgrelid = 'board_views'::regclass"
````

Expected: alembic logs `Running upgrade ... -> 0003, board_views: ...`; `ROWS-KEPT`; then `0003` and `board_views_touch_updated_at`. Measured 2026-10-13 on the 2026-10-08 dump: 994 events and 37 config rows kept, `0001 -> 0002 -> 0003`. (This host's production holds no memories; the corpus lives on 192.168.0.199, whose dumps are not on this host.)

- [ ] **Step 7: Commit**

````bash
git add backend/migrations/versions/0003_board_views.py backend/app/services/board_views.py backend/tests/test_board_views_service.py
git commit -m "feat(board): store saved board views"
````

---

### Task 10: The saved-view routes

**Files:**
- Modify: `backend/app/schemas/board.py`, `backend/app/api/routes/board.py`
- Modify: `backend/tests/test_api/test_rest_conformance.py`, `backend/app/services/content_surfaces.py`, `backend/tests/test_door_parity.py`, `docs/two-door-parity.md` (regenerated block only; the counts do not move)
- Test: `backend/tests/test_api/test_board_views.py`

**Interfaces:**
- Consumes: Task 9's service functions and `BUILTIN_VIEWS`; Task 8's refusal handler.
- Produces: `GET/POST /api/v1/board/views`, `PATCH/DELETE /api/v1/board/views/{view_id}` (Contracts §REST, §Views).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

`definition` is typed `Any` on both request models on purpose: a non-object definition must answer the service's `invalid_definition`, not FastAPI's generic 422. An explicit `null` field in a PATCH changes nothing (every column it could name is NOT NULL), so `{"name": null}` is `no_change`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_api/test_board_views.py` with:

````python
"""The board's saved views: built-ins, the four routes and their refusals (spec 2026-10-13 §2.6)."""
from __future__ import annotations

import pytest

from app.services.board_views import BUILTIN_VIEWS

PROJECT = "board-views"
DEFINITION = {
    "layout": "table",
    "group_by": "state",
    "filters": [{"property": "type", "operator": "in", "values": ["register_row"]}],
    "sort": {"property": "number", "direction": "desc"},
    "columns": ["number", "title", "state"],
    "show_untracked": True,
}


async def _create(client, headers, name="Mine", **extra):
    return await client.post(
        "/api/v1/board/views",
        json={"project": PROJECT, "name": name, "definition": DEFINITION, **extra},
        headers=headers,
    )


async def test_the_built_ins_come_first_and_saved_views_follow_by_position(client, auth_headers):
    second = await _create(client, auth_headers, "B")
    first = await _create(client, auth_headers, "A", position=0)
    assert second.status_code == first.status_code == 201
    assert second.json()["position"] == 0 and first.json()["position"] == 0
    third = await _create(client, auth_headers, "C")
    assert third.json()["position"] == 1
    listed = (await client.get(f"/api/v1/board/views?project={PROJECT}", headers=auth_headers)).json()
    assert [v["id"] for v in listed[:2]] == [
        "builtin:open-register-items", "builtin:plans-in-flight",
    ]
    assert all(v["builtin"] for v in listed[:2])
    assert [v["name"] for v in listed[2:]] == ["A", "B", "C"]
    assert listed[2]["definition"] == DEFINITION


def test_the_built_in_definitions_pass_their_own_schema():
    from app.services.board_views import validate_definition

    for view in BUILTIN_VIEWS:
        assert validate_definition(view["definition"]) == view["definition"]


async def test_rename_redefine_and_reposition(client, auth_headers):
    view = (await _create(client, auth_headers)).json()
    response = await client.patch(
        f"/api/v1/board/views/{view['id']}",
        json={"name": "Renamed", "position": 5, "definition": {**DEFINITION, "layout": "board"}},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["name"], body["position"], body["definition"]["layout"]) == ("Renamed", 5, "board")


async def test_delete_answers_204_and_the_view_is_gone(client, auth_headers):
    view = (await _create(client, auth_headers)).json()
    response = await client.delete(f"/api/v1/board/views/{view['id']}", headers=auth_headers)
    assert response.status_code == 204
    again = await client.delete(f"/api/v1/board/views/{view['id']}", headers=auth_headers)
    assert again.status_code == 404
    assert again.json()["error"]["code"] == "not_found"


async def test_a_taken_name_is_a_409_on_create_and_on_rename(client, auth_headers):
    await _create(client, auth_headers, "Taken")
    other = (await _create(client, auth_headers, "Other")).json()
    duplicate = await _create(client, auth_headers, "Taken")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "name_taken"
    rename = await client.patch(
        f"/api/v1/board/views/{other['id']}", json={"name": "Taken"}, headers=auth_headers,
    )
    assert rename.status_code == 409
    assert rename.json()["error"]["code"] == "name_taken"


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
async def test_a_built_in_cannot_be_written(client, auth_headers, method):
    response = await client.request(
        method, "/api/v1/board/views/builtin:plans-in-flight",
        json={"name": "x"} if method == "PATCH" else None, headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "builtin_view"


# A fixed id: parametrize ids must match across pytest-xdist workers.
@pytest.mark.parametrize("view_id", ["00000000-0000-4000-8000-0000000000c1", "not-a-uuid"])
async def test_an_unknown_id_is_a_404(client, auth_headers, view_id):
    response = await client.patch(
        f"/api/v1/board/views/{view_id}", json={"name": "x"}, headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("definition", [
    {**DEFINITION, "layout": "calendar"},
    {**DEFINITION, "group_by": "title"},
    {**DEFINITION, "columns": ["priority"]},
    {**DEFINITION, "filters": [{"property": "state", "operator": "regex", "values": []}]},
    {**DEFINITION, "extra": 1},
    {**DEFINITION, "filters": [
        {"property": "note", "operator": "contains", "values": ["x" * 200] * 200},
    ]},
    "not an object",
])
async def test_an_invalid_definition_is_refused_at_the_door(client, auth_headers, definition):
    response = await client.post(
        "/api/v1/board/views",
        json={"project": PROJECT, "name": "Bad", "definition": definition},
        headers=auth_headers,
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "invalid_definition"


async def test_a_patch_naming_nothing_is_no_change(client, auth_headers):
    view = (await _create(client, auth_headers)).json()
    for body in ({}, {"name": None}):
        response = await client.patch(
            f"/api/v1/board/views/{view['id']}", json=body, headers=auth_headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "no_change"
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_api/test_board_views.py`
Expected: FAIL: the view routes answer 404 or 405 (the built-in definitions test passes)

- [ ] **Step 3: Add the view models**

In `backend/app/schemas/board.py`, replace:

````python
from datetime import datetime
````

with:

````python
from datetime import datetime
from typing import Any
````

Append to `backend/app/schemas/board.py`, at the end of the file:

````python


class BoardView(BaseModel):
    id: str
    project: str
    name: str
    position: int
    definition: dict[str, Any]
    builtin: bool
    created_at: datetime | None
    updated_at: datetime | None


class BoardViewCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=100)
    # Validated by `board_views.validate_definition`, which answers
    # `invalid_definition` rather than FastAPI's generic 422.
    definition: Any
    position: int | None = Field(default=None, ge=0, le=1_000_000)


class BoardViewUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    definition: Any = None
    position: int | None = Field(default=None, ge=0, le=1_000_000)
````

- [ ] **Step 4: Add the routes**

In `backend/app/api/routes/board.py`, replace:

````python
  - PATCH  /api/v1/board/registers/{document_id}/rows/{number}
````

with:

````python
  - PATCH  /api/v1/board/registers/{document_id}/rows/{number}
  - GET    /api/v1/board/views
  - POST   /api/v1/board/views
  - PATCH  /api/v1/board/views/{view_id}
  - DELETE /api/v1/board/views/{view_id}
````

In `backend/app/api/routes/board.py`, replace:

````python
from fastapi import APIRouter, Depends, Query, Request, Response
````

with:

````python
from fastapi import APIRouter, Depends, Query, Request, Response, status
````

In `backend/app/api/routes/board.py`, replace:

````python
from app.schemas.board import (
    BoardRecordsResponse,
    RegisterRowEditRequest,
````

with:

````python
from app.schemas.board import (
    BoardRecordsResponse,
    BoardView,
    BoardViewCreateRequest,
    BoardViewUpdateRequest,
    RegisterRowEditRequest,
````

In `backend/app/api/routes/board.py`, replace:

````python
from app.services.board_edit import edit_register_row
````

with:

````python
from app.services.board_edit import edit_register_row
from app.services.board_views import create_view, delete_view, list_views, update_view
````

Append to `backend/app/api/routes/board.py`, at the end of the file:

````python


@router.get("/views", response_model=list[BoardView])
async def list_views_route(
    project: str = Query(..., min_length=1),
    _user: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[BoardView]:
    """The two built-in views, then the project's saved views by (position, name)."""
    return [BoardView(**view) for view in await list_views(session, project)]


@router.post("/views", response_model=BoardView, status_code=status.HTTP_201_CREATED)
async def create_view_route(
    body: BoardViewCreateRequest,
    _user: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> BoardView:
    return BoardView(**await create_view(
        session, project=body.project, name=body.name,
        definition=body.definition, position=body.position,
    ))


@router.patch("/views/{view_id}", response_model=BoardView)
async def update_view_route(
    view_id: str,
    body: BoardViewUpdateRequest,
    _user: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> BoardView:
    # An explicit null changes nothing: every column it could name is NOT NULL.
    changes = {
        field: getattr(body, field)
        for field in body.model_fields_set
        if getattr(body, field) is not None
    }
    return BoardView(**await update_view(session, view_id, changes=changes))


@router.delete("/views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_view_route(
    view_id: str,
    _user: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> None:
    await delete_view(session, view_id)
````

- [ ] **Step 5: Classify the four routes**

In `backend/tests/test_api/test_rest_conformance.py`, replace:

````python
    ("PATCH", "/api/v1/board/registers/{document_id}/rows/{number}"): 200,
````

with:

````python
    ("PATCH", "/api/v1/board/registers/{document_id}/rows/{number}"): 200,
    ("GET", "/api/v1/board/views"): 200,
    ("POST", "/api/v1/board/views"): 201,
    ("PATCH", "/api/v1/board/views/{view_id}"): 200,
    ("DELETE", "/api/v1/board/views/{view_id}"): 204,
````

In `backend/app/services/content_surfaces.py`, replace:

````python
    "PATCH /api/v1/board/registers/{document_id}/rows/{number}",
````

with:

````python
    "PATCH /api/v1/board/registers/{document_id}/rows/{number}",
    "GET /api/v1/board/views",
    "POST /api/v1/board/views",
    "PATCH /api/v1/board/views/{view_id}",
    "DELETE /api/v1/board/views/{view_id}",
````

In `backend/tests/test_door_parity.py`, replace:

````python
        rest=(
            ("GET", f"{V1}/board/records"),
        ),
````

with:

````python
        rest=(
            ("GET", f"{V1}/board/records"),
            ("GET", f"{V1}/board/views"),
        ),
````

In `backend/tests/test_door_parity.py`, replace:

````python
        rest=(
            ("PATCH", f"{V1}/board/registers/{{document_id}}/rows/{{number}}"),
        ),
````

with:

````python
        rest=(
            ("PATCH", f"{V1}/board/registers/{{document_id}}/rows/{{number}}"),
            ("POST", f"{V1}/board/views"),
            ("PATCH", f"{V1}/board/views/{{view_id}}"),
            ("DELETE", f"{V1}/board/views/{{view_id}}"),
        ),
````

Run:

````bash
cd backend && .venv/bin/python -c "from tests.test_door_parity import render_markdown; print(render_markdown())" 2>/dev/null > /tmp/parity-table.md && python3 - <<'PY'
from pathlib import Path
doc = Path('../docs/two-door-parity.md')
text = doc.read_text(encoding='utf-8')
begin, end = '<!-- BEGIN GENERATED PARITY TABLE -->', '<!-- END GENERATED PARITY TABLE -->'
pre, rest = text.split(begin, 1)
_, post = rest.split(end, 1)
table = Path('/tmp/parity-table.md').read_text(encoding='utf-8').strip()
doc.write_text(pre + begin + '\n' + table + '\n' + end + post, encoding='utf-8')
PY
````

Expected: `git diff docs/two-door-parity.md` shows the `board.reads` and `board.write` rows gaining the view routes, and the headline staying at 92 surfaces (re-run the first line without `2>/dev/null` if it shows nothing)

- [ ] **Step 6: Run the tests and the guards leg**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_api/test_board_views.py tests/test_board_views_service.py`
Expected: all pass

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py tests/test_event_taxonomy_map.py`
Expected: all pass

- [ ] **Step 7: Run the whole backend suite**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q -n 4 --dist loadfile -p no:cacheprovider`
Expected: all pass (8435 passed, 26 skipped on 2026-10-13). A parametrize id must be identical across xdist workers, so never build one from `uuid.uuid4()`

- [ ] **Step 8: Commit**

````bash
git add backend/app/schemas/board.py backend/app/api/routes/board.py backend/app/services/content_surfaces.py backend/tests/test_api/test_board_views.py backend/tests/test_api/test_rest_conformance.py backend/tests/test_door_parity.py docs/two-door-parity.md
git commit -m "feat(board): save, rename and delete board views"
````

---

### Task 11: `ApiError` carries the envelope's code

**Files:**
- Modify: `frontend/src/lib/api.ts` (`ApiError`, `apiFetchWithHeaders`, `apiUpload`)
- Test: `frontend/src/lib/__tests__/api-fetch-headers.test.ts` (append), `frontend/src/lib/__tests__/api-upload.test.ts`

**Interfaces:**
- Consumes: Task 8's refusal envelope (`error.code`).
- Produces: `ApiError.code?: string` and a fourth constructor argument `code` (Contracts §Frontend).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

- [ ] **Step 1: Prepare the frontend (once per worktree)**

Run: `cd frontend && test -d node_modules || npm ci`
Expected: node_modules present

- [ ] **Step 2: Write the failing tests**

Append to `frontend/src/lib/__tests__/api-fetch-headers.test.ts`, at the end of the file:

````ts

describe("ApiError from an error envelope", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn())
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("carries the envelope's code and details beside the message", async () => {
    vi.mocked(fetch).mockResolvedValue(
      respond({
        status: 409,
        body: {
          detail: "this register changed since it was loaded",
          error: {
            code: "hash_conflict",
            message: "this register changed since it was loaded",
            details: [{ current_hash: "h2" }],
          },
        },
      }),
    )
    await expect(apiFetch("/board/registers/d/rows/1")).rejects.toMatchObject({
      status: 409,
      code: "hash_conflict",
      details: [{ current_hash: "h2" }],
      message: "this register changed since it was loaded",
    })
  })

  it("leaves the code undefined when the body is not an envelope", async () => {
    vi.mocked(fetch).mockResolvedValue(respond({ status: 500, body: { detail: "boom" } }))
    await expect(apiFetch("/x")).rejects.toMatchObject({ status: 500, code: undefined })
  })
})
````

In `frontend/src/lib/__tests__/api-upload.test.ts` (the end of the file: the new case goes inside the `describe` block), replace:

````ts
    expect(FakeXhr.constructed).toBe(0)
  })
})
````

with:

````ts
    expect(FakeXhr.constructed).toBe(0)
  })

  it("carries the error envelope's code and details, as apiFetch does", async () => {
    FakeXhr.handler = (xhr) => {
      xhr.status = 413
      xhr.responseText = JSON.stringify({
        detail: "too large",
        error: { code: "payload_too_large", message: "too large", details: [{ limit: 1 }] },
      })
      xhr.onload?.()
    }
    await expect(apiUpload("/pages/p1/attachments", new Blob(["x"]))).rejects.toMatchObject({
      status: 413,
      code: "payload_too_large",
      details: [{ limit: 1 }],
      message: "too large",
    })
  })
})
````

- [ ] **Step 3: Run them to see them fail**

Run: `cd frontend && npx vitest run src/lib/__tests__/api-fetch-headers.test.ts src/lib/__tests__/api-upload.test.ts`
Expected: 2 FAIL: `code` is undefined where an error code was expected

- [ ] **Step 4: Carry the code on both transports**

`apiUpload` promises the same `ApiError` shape as `apiFetchWithHeaders`, so it carries the code too.

In `frontend/src/lib/api.ts`, replace:

````ts
  details?: unknown[]

  constructor(message: string, status: number, details?: unknown[]) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.details = details
  }
````

with:

````ts
  details?: unknown[]
  // `error.code` from the ErrorEnvelope: the generic status name
  // (`not_found`, `conflict`) or a door's own reason (the board's
  // `hash_conflict`, `note_required`). Absent when the body was not an
  // envelope.
  code?: string

  constructor(message: string, status: number, details?: unknown[], code?: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.details = details
    this.code = code
  }
````

In `frontend/src/lib/api.ts`, replace:

````ts
    const body = error as { detail?: string; error?: { details?: unknown[] } }
    throw new ApiError(
      body.detail || `API error: ${response.status}`,
      response.status,
      body.error?.details,
    )
````

with:

````ts
    const body = error as {
      detail?: string
      error?: { details?: unknown[]; code?: string }
    }
    throw new ApiError(
      body.detail || `API error: ${response.status}`,
      response.status,
      body.error?.details,
      body.error?.code,
    )
````

In `frontend/src/lib/api.ts`, replace:

````ts
      let details: unknown[] | undefined
      try {
        const parsed = JSON.parse(xhr.responseText) as {
          detail?: string
          error?: { details?: unknown[] }
        }
        message = parsed.detail || message
        details = parsed.error?.details
````

with:

````ts
      let details: unknown[] | undefined
      let code: string | undefined
      try {
        const parsed = JSON.parse(xhr.responseText) as {
          detail?: string
          error?: { details?: unknown[]; code?: string }
        }
        message = parsed.detail || message
        details = parsed.error?.details
        code = parsed.error?.code
````

In `frontend/src/lib/api.ts`, replace:

````ts
      reject(new ApiError(message, xhr.status, details))
````

with:

````ts
      reject(new ApiError(message, xhr.status, details, code))
````

- [ ] **Step 5: Run the test and the typecheck**

Run: `cd frontend && npx vitest run src/lib`
Expected: all pass

Run: `cd frontend && npm run typecheck`
Expected: no errors

- [ ] **Step 6: Commit**

````bash
git add frontend/src/lib/api.ts frontend/src/lib/__tests__/api-fetch-headers.test.ts frontend/src/lib/__tests__/api-upload.test.ts
git commit -m "feat(frontend): carry the error envelope's code on ApiError"
````

---

### Task 12: Board types and the records library

**Files:**
- Create: `frontend/src/hooks/api/use-board-api.ts` (types only; Task 13 adds the hooks)
- Create: `frontend/src/features/board/lib/records.ts`
- Test: `frontend/src/features/board/lib/__tests__/records.test.ts`

**Interfaces:**
- Consumes: the wire shapes of Tasks 6, 8 and 10 (Contracts §REST).
- Produces: the API types (`BoardRecords`, `BoardView`, `ViewDefinition`, `BoardProperty`, `GroupableProperty`, `RowChanges`, `RowEditResult`, ...) and the records library (`BoardRecord`, `flattenRecords`, `applyView`, `boardLanes`, `planMove`, `propertyValue`, `formatProgress`, `isBlankNote`, `shortName`, `PROPERTIES`, `PROPERTY_LABELS`, `GROUPABLE`, `REGISTER_STATES`, `TASK_STATES`, `NOTE_REQUIRED`, `UNTRACKED_LABEL`) (Contracts §Frontend).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

A record id is `r:<document_id>:<number>` for a register row (Task 14's pending marker rebuilds it from the PATCH variables) and `t:<document_id>:<line>` for a task (two headings may share a number).

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/features/board/lib/__tests__/records.test.ts` with:

````ts
import { describe, expect, it } from "vitest"
import type { BoardRecords, ViewDefinition } from "@/hooks/api/use-board-api"
import {
  applyView,
  boardLanes,
  flattenRecords,
  formatProgress,
  isBlankNote,
  planMove,
  type BoardRecord,
} from "../records"

const DATA: BoardRecords = {
  project: "p",
  registers: [
    {
      document_id: "reg",
      uri: "superpowers/registers/r.md",
      title: "Register",
      covers: null,
      content_hash: "h1",
      block_first: false,
      malformed: [],
      error: null,
      rows: [
        {
          number: 1,
          item: "Alpha",
          assigned: "-",
          acceptance: "-",
          state: "open",
          raw_state: "open",
          note: "-",
          note_blank: true,
          line: 5,
          plan_uri: null,
          plan_progress: null,
        },
        {
          number: 2,
          item: "Beta",
          assigned: "docs/superpowers/plans/p.md",
          acceptance: "-",
          state: "verify",
          raw_state: "verify",
          note: "check beta",
          note_blank: false,
          line: 6,
          plan_uri: "superpowers/plans/p.md",
          plan_progress: { done: 1, total: 3, untracked: null },
        },
        {
          number: 3,
          item: "Gamma",
          assigned: "-",
          acceptance: "-",
          state: "unrecognised",
          raw_state: "parked",
          note: "-",
          note_blank: true,
          line: 7,
          plan_uri: null,
          plan_progress: null,
        },
      ],
    },
  ],
  plans: [
    {
      document_id: "plan",
      uri: "superpowers/plans/p.md",
      title: "Plan",
      content_hash: "h2",
      workstream: { id: "w", key: "plan-key", state: "open" },
      other_workstreams: 0,
      spec_uri: "superpowers/specs/s.md",
      untracked: null,
      orphans: [],
      error: null,
      tasks: [
        {
          number: 1,
          label: "Task 1: One",
          title: "One",
          line: 3,
          state: "done",
          raw_state: "done",
          untracked: null,
          shared_number: false,
          blocked_reason: null,
          commit: "abc1234",
          last_activity: "2026-10-13T00:00:00Z",
          steps: [],
        },
        {
          number: 2,
          label: "Task 2: Two",
          title: "Two",
          line: 9,
          state: "blocked",
          raw_state: "blocked",
          untracked: null,
          shared_number: false,
          blocked_reason: "waiting on beta",
          commit: null,
          last_activity: null,
          steps: [],
        },
      ],
    },
    {
      document_id: "loose",
      uri: "superpowers/plans/loose.md",
      title: "Loose",
      content_hash: "h3",
      workstream: null,
      other_workstreams: 0,
      spec_uri: null,
      untracked: "no_workstream",
      orphans: [],
      error: null,
      tasks: [
        {
          number: 1,
          label: "Task 1: Loose",
          title: "Loose",
          line: 3,
          state: "untracked",
          raw_state: null,
          untracked: "no_workstream",
          shared_number: false,
          blocked_reason: null,
          commit: null,
          last_activity: null,
          steps: [],
        },
      ],
    },
  ],
}

const BOARD: ViewDefinition = {
  layout: "board",
  group_by: "state",
  filters: [],
  sort: { property: "number", direction: "asc" },
  columns: [],
  show_untracked: false,
}

const records = flattenRecords(DATA)
const byTitle = (title: string) =>
  records.find((r) => r.title === title) as BoardRecord

describe("flattenRecords", () => {
  it("makes one record per row and per task, with type-specific fields", () => {
    expect(records.map((r) => [r.type, r.label])).toEqual([
      ["register_row", "#1"],
      ["register_row", "#2"],
      ["register_row", "#3"],
      ["plan_task", "Task 1: One"],
      ["plan_task", "Task 2: Two"],
      ["plan_task", "Task 1: Loose"],
    ])
    expect(byTitle("Beta").contentHash).toBe("h1")
    expect(byTitle("Two").note).toBe("waiting on beta")
    expect(byTitle("One").workstreamKey).toBe("plan-key")
    expect(new Set(records.map((r) => r.id)).size).toBe(records.length)
  })
})

describe("applyView", () => {
  it("hides untracked tasks unless asked", () => {
    expect(applyView(records, BOARD, "").map((r) => r.title)).not.toContain(
      "Loose",
    )
    expect(
      applyView(records, { ...BOARD, show_untracked: true }, "").map(
        (r) => r.title,
      ),
    ).toContain("Loose")
  })

  it("applies in, not_in and contains filters", () => {
    const view: ViewDefinition = {
      ...BOARD,
      filters: [
        { property: "type", operator: "in", values: ["register_row"] },
        { property: "state", operator: "not_in", values: ["open"] },
        { property: "title", operator: "contains", values: ["ET", "zzz"] },
      ],
    }
    expect(applyView(records, view, "").map((r) => r.title)).toEqual(["Beta"])
  })

  it("matches the text box against title and note", () => {
    expect(applyView(records, BOARD, "BETA").map((r) => r.title)).toEqual([
      "Beta",
      "Two",
    ])
  })

  it("sorts by the view's property and direction", () => {
    const view: ViewDefinition = {
      ...BOARD,
      sort: { property: "title", direction: "desc" },
    }
    expect(applyView(records, view, "").map((r) => r.title)).toEqual([
      "Two",
      "One",
      "Gamma",
      "Beta",
      "Alpha",
    ])
  })
})

describe("boardLanes", () => {
  it("splits a State grouping into one lane per type over its own vocabulary", () => {
    const lanes = boardLanes(applyView(records, BOARD, ""), "state", false)
    expect(lanes.map((l) => l.key)).toEqual(["register_row", "plan_task"])
    expect(lanes[0]!.columns.map((c) => c.key)).toEqual([
      "open",
      "planned",
      "doing",
      "verify",
      "done",
      "deferred",
      "n/a",
      "unrecognised",
    ])
    expect(lanes[1]!.columns.map((c) => c.key)).toEqual([
      "todo",
      "wip",
      "review",
      "blocked",
      "done",
      "unrecognised",
    ])
    expect(
      lanes[0]!.columns.find((c) => c.key === "unrecognised")!.records[0]!
        .title,
    ).toBe("Gamma")
  })

  it("adds the untracked column only when untracked tasks are shown", () => {
    const shown = { ...BOARD, show_untracked: true }
    const lanes = boardLanes(applyView(records, shown, ""), "state", true)
    expect(lanes[1]!.columns.map((c) => c.key)).toContain("untracked")
  })

  it("drops a lane the filters emptied", () => {
    const registersOnly: ViewDefinition = {
      ...BOARD,
      filters: [{ property: "type", operator: "in", values: ["register_row"] }],
    }
    expect(
      boardLanes(applyView(records, registersOnly, ""), "state", false),
    ).toHaveLength(1)
  })

  it("mixes types in shared columns for any other grouping", () => {
    const [lane] = boardLanes(applyView(records, BOARD, ""), "plan", false)
    expect(lane!.columns.map((c) => [c.title, c.records.length])).toEqual([
      ["p", 3],
      ["(none)", 2],
    ])
  })
})

describe("planMove", () => {
  it("locks plan tasks, ignores a same-column drop and asks for a note where needed", () => {
    expect(planMove(byTitle("One"), "todo")).toBe("locked")
    expect(planMove(byTitle("Alpha"), "open")).toBe("noop")
    expect(planMove(byTitle("Alpha"), "deferred")).toBe("note")
    expect(planMove(byTitle("Alpha"), "doing")).toBe("patch")
  })
})

describe("notes and progress", () => {
  it("reads a dash as a blank note", () => {
    expect(isBlankNote("-")).toBe(true)
    expect(isBlankNote("  ")).toBe(true)
    expect(isBlankNote("why")).toBe(false)
  })

  it("formats progress or names the untracked kind", () => {
    expect(formatProgress({ done: 1, total: 3, untracked: null })).toBe(
      "1 of 3 done",
    )
    expect(
      formatProgress({ done: 0, total: 3, untracked: "no_properties" }),
    ).toMatch(/no task properties/)
  })
})
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd frontend && npx vitest run src/features/board`
Expected: FAIL: cannot resolve `../records` or `@/hooks/api/use-board-api`

- [ ] **Step 3: Write the types**

Create `frontend/src/hooks/api/use-board-api.ts` with:

````ts
export type Untracked = "no_workstream" | "no_properties"

export interface PlanProgress {
  done: number
  total: number
  untracked: Untracked | null
}

export interface RegisterRow {
  number: number
  item: string
  assigned: string
  acceptance: string
  state: string
  raw_state: string
  note: string
  note_blank: boolean
  line: number
}

export interface BoardRegisterRow extends RegisterRow {
  plan_uri: string | null
  plan_progress: PlanProgress | null
}

export interface BoardRegister {
  document_id: string
  uri: string
  title: string | null
  covers: string | null
  content_hash: string | null
  block_first: boolean
  rows: BoardRegisterRow[]
  malformed: { line: number; text: string; reason: string }[]
  error: string | null
}

export interface TaskStep {
  checked: boolean
  text: string
}

export interface PlanTask {
  number: number
  label: string
  title: string
  line: number
  state: string
  raw_state: string | null
  untracked: Untracked | null
  shared_number: boolean
  blocked_reason: string | null
  commit: string | null
  last_activity: string | null
  steps: TaskStep[]
}

export interface BoardPlan {
  document_id: string
  uri: string
  title: string | null
  content_hash: string | null
  workstream: { id: string; key: string; state: "open" | "closed" } | null
  other_workstreams: number
  spec_uri: string | null
  untracked: Untracked | null
  tasks: PlanTask[]
  orphans: number[]
  error: string | null
}

export interface BoardRecords {
  project: string
  registers: BoardRegister[]
  plans: BoardPlan[]
}

export type BoardProperty =
  | "type"
  | "title"
  | "number"
  | "state"
  | "source"
  | "note"
  | "assigned"
  | "acceptance"
  | "plan_progress"
  | "plan"
  | "spec"
  | "workstream_state"
  | "commit"
  | "last_activity"

export type GroupableProperty =
  | "type"
  | "state"
  | "source"
  | "assigned"
  | "plan"
  | "workstream_state"

export interface ViewFilter {
  property: BoardProperty
  operator: "in" | "not_in" | "contains"
  values: string[]
}

export interface ViewDefinition {
  layout: "board" | "table"
  group_by: GroupableProperty | null
  filters: ViewFilter[]
  sort: { property: BoardProperty; direction: "asc" | "desc" } | null
  columns: BoardProperty[]
  show_untracked: boolean
}

export interface BoardView {
  id: string
  project: string
  name: string
  position: number
  definition: ViewDefinition
  builtin: boolean
  created_at: string | null
  updated_at: string | null
}

export interface RowChanges {
  state?: string
  note?: string
  assigned?: string
}

export interface RowEditResult {
  document_id: string
  content_hash: string
  row: RegisterRow
}
````

- [ ] **Step 4: Write the library**

Create `frontend/src/features/board/lib/records.ts` with:

````ts
import type {
  BoardProperty,
  BoardRecords,
  GroupableProperty,
  PlanProgress,
  TaskStep,
  Untracked,
  ViewDefinition,
} from "@/hooks/api/use-board-api"

export type RecordType = "register_row" | "plan_task"

export const REGISTER_STATES = [
  "open",
  "planned",
  "doing",
  "verify",
  "done",
  "deferred",
  "n/a",
] as const
export const TASK_STATES = ["todo", "wip", "review", "blocked", "done"] as const
/** The states whose rows need a Note (`REGISTER_NOTE_REQUIRED` in dr-forge). */
export const NOTE_REQUIRED = new Set<string>(["verify", "deferred", "n/a"])

export const PROPERTY_LABELS: Record<BoardProperty, string> = {
  type: "Type",
  title: "Title",
  number: "#",
  state: "State",
  source: "Source",
  note: "Note",
  assigned: "Assigned",
  acceptance: "Acceptance",
  plan_progress: "Plan progress",
  plan: "Plan",
  spec: "Spec",
  workstream_state: "Workstream",
  commit: "Commit",
  last_activity: "Last activity",
}
export const PROPERTIES = Object.keys(PROPERTY_LABELS) as BoardProperty[]
export const GROUPABLE: GroupableProperty[] = [
  "type",
  "state",
  "source",
  "assigned",
  "plan",
  "workstream_state",
]

export const UNTRACKED_LABEL: Record<Untracked, string> = {
  no_workstream: "untracked — no workstream names this plan",
  no_properties: "untracked — the ledger carries no task properties",
}

/** One card or table row: a register row or a plan task, flattened. */
export interface BoardRecord {
  id: string
  type: RecordType
  number: number
  /** `#12` for a register row, the heading from `Task` on for a plan task. */
  label: string
  title: string
  state: string
  rawState: string | null
  source: string
  sourceTitle: string | null
  documentId: string
  /** The register's hash when it was read: the PATCH's `expected_hash`. */
  contentHash: string | null
  blockFirst: boolean
  /** A register row's Note, or a blocked task's reason. */
  note: string | null
  noteBlank: boolean
  assigned: string | null
  acceptance: string | null
  planProgress: PlanProgress | null
  plan: string | null
  spec: string | null
  workstreamKey: string | null
  workstreamState: "open" | "closed" | null
  commit: string | null
  lastActivity: string | null
  untracked: Untracked | null
  sharedNumber: boolean
  steps: TaskStep[]
}

export function shortName(uri: string | null): string {
  if (!uri) return ""
  const leaf = uri.split("/").pop() ?? uri
  return leaf.endsWith(".md") ? leaf.slice(0, -3) : leaf
}

export function isBlankNote(note: string | null | undefined): boolean {
  const trimmed = (note ?? "").trim()
  return trimmed === "" || trimmed === "-"
}

export function flattenRecords(data: BoardRecords): BoardRecord[] {
  const records: BoardRecord[] = []
  for (const register of data.registers) {
    for (const row of register.rows) {
      records.push({
        id: `r:${register.document_id}:${row.number}`,
        type: "register_row",
        number: row.number,
        label: `#${row.number}`,
        title: row.item,
        state: row.state,
        rawState: row.raw_state,
        source: register.uri,
        sourceTitle: register.title,
        documentId: register.document_id,
        contentHash: register.content_hash,
        blockFirst: register.block_first,
        note: row.note,
        noteBlank: row.note_blank,
        assigned: row.assigned,
        acceptance: row.acceptance,
        planProgress: row.plan_progress,
        plan: row.plan_uri,
        spec: null,
        workstreamKey: null,
        workstreamState: null,
        commit: null,
        lastActivity: null,
        untracked: null,
        sharedNumber: false,
        steps: [],
      })
    }
  }
  for (const plan of data.plans) {
    for (const task of plan.tasks) {
      records.push({
        id: `t:${plan.document_id}:${task.line}`,
        type: "plan_task",
        number: task.number,
        label: task.label,
        title: task.title || task.label,
        state: task.state,
        rawState: task.raw_state,
        source: plan.uri,
        sourceTitle: plan.title,
        documentId: plan.document_id,
        contentHash: null,
        blockFirst: false,
        note: task.blocked_reason,
        noteBlank: !task.blocked_reason,
        assigned: null,
        acceptance: null,
        planProgress: null,
        plan: plan.uri,
        spec: plan.spec_uri,
        workstreamKey: plan.workstream?.key ?? null,
        workstreamState: plan.workstream?.state ?? null,
        commit: task.commit,
        lastActivity: task.last_activity,
        untracked: task.untracked,
        sharedNumber: task.shared_number,
        steps: task.steps,
      })
    }
  }
  return records
}

export function formatProgress(progress: PlanProgress | null): string | null {
  if (!progress) return null
  if (progress.untracked) return UNTRACKED_LABEL[progress.untracked]
  return `${progress.done} of ${progress.total} done`
}

/** A property as text: what filters match, groups key on and sorts compare. */
export function propertyValue(
  record: BoardRecord,
  property: BoardProperty,
): string | null {
  switch (property) {
    case "type":
      return record.type
    case "title":
      return record.title
    case "number":
      return String(record.number)
    case "state":
      return record.state
    case "source":
      return record.source
    case "note":
      return record.note
    case "assigned":
      return record.assigned
    case "acceptance":
      return record.acceptance
    case "plan_progress":
      return formatProgress(record.planProgress)
    case "plan":
      return record.plan
    case "spec":
      return record.spec
    case "workstream_state":
      return record.workstreamState
    case "commit":
      return record.commit
    case "last_activity":
      return record.lastActivity
  }
}

function compare(
  a: BoardRecord,
  b: BoardRecord,
  property: BoardProperty,
): number {
  if (property === "number") return a.number - b.number
  const left = propertyValue(a, property) ?? ""
  const right = propertyValue(b, property) ?? ""
  return left.localeCompare(right)
}

/** The records a view shows, in its order. `text` matches title and Note. */
export function applyView(
  records: BoardRecord[],
  definition: ViewDefinition,
  text: string,
): BoardRecord[] {
  const needle = text.trim().toLowerCase()
  const shown = records.filter((record) => {
    if (!definition.show_untracked && record.state === "untracked") return false
    for (const filter of definition.filters) {
      const value = propertyValue(record, filter.property) ?? ""
      if (filter.operator === "in" && !filter.values.includes(value))
        return false
      if (filter.operator === "not_in" && filter.values.includes(value))
        return false
      if (
        filter.operator === "contains" &&
        !filter.values.some((v) =>
          value.toLowerCase().includes(v.toLowerCase()),
        )
      ) {
        return false
      }
    }
    if (!needle) return true
    return (
      record.title.toLowerCase().includes(needle) ||
      (record.note ?? "").toLowerCase().includes(needle)
    )
  })
  const sort = definition.sort
  if (!sort) return shown
  const sign = sort.direction === "asc" ? 1 : -1
  return [...shown].sort(
    (a, b) => sign * compare(a, b, sort.property) || a.id.localeCompare(b.id),
  )
}

export interface BoardColumn {
  key: string
  title: string
  records: BoardRecord[]
}

export interface BoardLane {
  key: string
  title: string
  /** Set on a State lane: the one type whose cards it holds. */
  type: RecordType | null
  columns: BoardColumn[]
}

const NONE = "(none)"

function groupTitle(property: GroupableProperty, key: string): string {
  if (key === NONE) return NONE
  if (property === "source" || property === "plan") return shortName(key)
  if (property === "type")
    return key === "register_row" ? "Register rows" : "Plan tasks"
  return key
}

/** Columns for a grouping. State splits into one lane per type, each across
 *  its own vocabulary, so the two vocabularies never share a column. */
export function boardLanes(
  records: BoardRecord[],
  groupBy: GroupableProperty | null,
  showUntracked: boolean,
): BoardLane[] {
  if (groupBy === "state") {
    const lanes: BoardLane[] = []
    const specs: [RecordType, string, string[]][] = [
      ["register_row", "Register rows", [...REGISTER_STATES, "unrecognised"]],
      [
        "plan_task",
        "Plan tasks",
        [
          ...TASK_STATES,
          "unrecognised",
          ...(showUntracked ? ["untracked"] : []),
        ],
      ],
    ]
    for (const [type, title, states] of specs) {
      const own = records.filter((r) => r.type === type)
      if (own.length === 0) continue
      lanes.push({
        key: type,
        title,
        type,
        columns: states.map((state) => ({
          key: state,
          title: state,
          records: own.filter((r) => r.state === state),
        })),
      })
    }
    return lanes
  }
  if (groupBy === null) {
    return [
      {
        key: "all",
        title: "All",
        type: null,
        columns: [{ key: "all", title: "All", records }],
      },
    ]
  }
  const columns = new Map<string, BoardRecord[]>()
  for (const record of records) {
    const key = propertyValue(record, groupBy) || NONE
    const column = columns.get(key)
    if (column) column.push(record)
    else columns.set(key, [record])
  }
  const keys = [...columns.keys()].sort((a, b) =>
    a === NONE ? 1 : b === NONE ? -1 : a.localeCompare(b),
  )
  return [
    {
      key: groupBy,
      title: "",
      type: null,
      columns: keys.map((key) => ({
        key,
        title: groupTitle(groupBy, key),
        records: columns.get(key) ?? [],
      })),
    },
  ]
}

export type MoveIntent = "locked" | "noop" | "note" | "patch"

/** What dropping `record` into `toState` asks for. Only register rows move;
 *  a state that needs a Note always opens the Note dialog first. */
export function planMove(record: BoardRecord, toState: string): MoveIntent {
  if (record.type !== "register_row") return "locked"
  if (record.state === toState) return "noop"
  if (NOTE_REQUIRED.has(toState)) return "note"
  return "patch"
}
````

- [ ] **Step 5: Run the tests and the typecheck**

Run: `cd frontend && npx vitest run src/features/board`
Expected: 12 pass

Run: `cd frontend && npm run typecheck`
Expected: no errors

- [ ] **Step 6: Commit**

````bash
git add frontend/src/hooks/api/use-board-api.ts frontend/src/features/board/lib/records.ts frontend/src/features/board/lib/__tests__/records.test.ts
git commit -m "feat(frontend): flatten, filter and group board records"
````

---

### Task 13: Board hooks and demo fixtures

**Files:**
- Modify: `frontend/src/hooks/api/use-board-api.ts` (imports and hooks)
- Create: `frontend/src/demo/board.ts`
- Modify: `frontend/src/lib/query-keys.ts` (`QUERY_KEY_SCOPE`), `frontend/src/hooks/api/index.ts`, `frontend/src/__tests__/no-restricted-imports-count.test.ts` (the demo-import floor)
- Test: `frontend/src/hooks/api/__tests__/use-board-api.demo.test.tsx`, `frontend/src/hooks/api/__tests__/use-board-api.test.tsx`

**Interfaces:**
- Consumes: Task 12's types.
- Produces: `useBoardRecords(project)`, `useBoardViews(project)`, `useRegisterRowEdit(project)`, `useCreateBoardView(project)`, `useUpdateBoardView(project)`, `useDeleteBoardView(project)`, `BOARD_REFRESH_MS`; `demoBoardRecords(project)`, `DEMO_BOARD_VIEWS`; query keys `boardRecords`, `boardViews` (Contracts §Frontend).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

Every hook carries `enabled: !DEMO` and demo `initialData`; every mutation rejects in demo mode without a request (a hook missing that guard 401-redirects the whole demo to /login). There is no hand-rolled `If-None-Match`: the route answers `Cache-Control: private, no-cache` with an `ETag`, so the browser revalidates on its own.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/hooks/api/__tests__/use-board-api.demo.test.tsx` with:

````tsx
import { describe, expect, it, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import {
  useBoardRecords,
  useBoardViews,
  useRegisterRowEdit,
} from "../use-board-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("the board in demo mode", () => {
  it("serves records and the built-in views without a request", () => {
    const records = renderHook(() => useBoardRecords("darkmem"), { wrapper })
    expect(
      records.result.current.data?.registers[0]?.rows.length,
    ).toBeGreaterThan(0)
    expect(records.result.current.data?.plans[0]?.tasks.length).toBeGreaterThan(
      0,
    )
    const other = renderHook(() => useBoardRecords("acme-storefront"), {
      wrapper,
    })
    expect(other.result.current.data?.registers).toEqual([])
    const views = renderHook(() => useBoardViews("darkmem"), { wrapper })
    expect(views.result.current.data?.map((v) => v.id)).toEqual([
      "builtin:open-register-items",
      "builtin:plans-in-flight",
    ])
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it("refuses a row edit without a request", async () => {
    const edit = renderHook(() => useRegisterRowEdit("darkmem"), { wrapper })
    await expect(
      edit.result.current.mutateAsync({
        documentId: "d",
        number: 1,
        expectedHash: "h",
        state: "done",
      }),
    ).rejects.toThrow(/read-only/)
    expect(apiFetch).not.toHaveBeenCalled()
  })
})
````

Create `frontend/src/hooks/api/__tests__/use-board-api.test.tsx` with:

````tsx
import { describe, expect, it, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { useBoardRecords, useRegisterRowEdit } from "../use-board-api"

function setup() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
  return { qc, wrapper }
}

describe("the board hooks", () => {
  it("reads records for the named project", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      project: "darkmem",
      registers: [],
      plans: [],
    })
    const { wrapper } = setup()
    const { result } = renderHook(() => useBoardRecords("darkmem"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe(
      "/board/records?project=darkmem",
    )
  })

  it("sends the row edit with its expected hash and re-reads the records", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      document_id: "d",
      content_hash: "h2",
      row: {},
    })
    const { qc, wrapper } = setup()
    const invalidate = vi.spyOn(qc, "invalidateQueries")
    const { result } = renderHook(() => useRegisterRowEdit("darkmem"), {
      wrapper,
    })
    await result.current.mutateAsync({
      documentId: "d",
      number: 7,
      expectedHash: "h1",
      state: "verify",
      note: "why",
    })
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith(
      "/board/registers/d/rows/7",
      {
        method: "PATCH",
        body: JSON.stringify({
          expected_hash: "h1",
          state: "verify",
          note: "why",
        }),
      },
    )
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ["boardRecords", "darkmem"],
    })
  })
})
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd frontend && npx vitest run src/hooks/api/__tests__/use-board-api`
Expected: FAIL: `useBoardRecords` is not exported

- [ ] **Step 3: Write the demo fixtures**

Create `frontend/src/demo/board.ts` with:

````ts
import type { BoardRecords, BoardView } from "@/hooks/api/use-board-api"

const PLAN_URI = "superpowers/plans/2026-09-28-work-log-increment-6.md"
const SPEC_URI = "superpowers/specs/2026-09-23-work-log-lane-design.md"

/** One register and one plan in the demo's `darkmem` project, tracked by the
 *  open demo workstream (`demo/worklog.ts`). */
const DARKMEM: Omit<BoardRecords, "project"> = {
  registers: [
    {
      document_id: "0f0e1d2c-0000-4000-8000-0000000000b1",
      uri: "superpowers/registers/2026-09-23-work-log-lane.md",
      title: "Register — separate working data from memories",
      covers: "docs/superpowers/specs/2026-09-23-work-log-lane-design.md",
      content_hash: "demo-register-hash",
      block_first: false,
      malformed: [],
      error: null,
      rows: [
        {
          number: 1,
          item: "Separate working progress from memory",
          assigned: "docs/superpowers/plans/2026-09-28-work-log-increment-6.md",
          acceptance: "worklog store and verbs live on both doors",
          state: "verify",
          raw_state: "verify",
          note: "owed: the owner's review of the Work log UI",
          note_blank: false,
          line: 8,
          plan_uri: PLAN_URI,
          plan_progress: { done: 2, total: 4, untracked: null },
        },
        {
          number: 85,
          item: "A progress board like Notion's",
          assigned:
            "docs/superpowers/specs/2026-10-13-notion-progress-board-design.md",
          acceptance: "board and table over register rows and plan tasks",
          state: "doing",
          raw_state: "doing",
          note: "-",
          note_blank: true,
          line: 92,
          plan_uri: null,
          plan_progress: null,
        },
        {
          number: 86,
          item: "Retire the T-epic board",
          assigned: "-",
          acceptance: "-",
          state: "open",
          raw_state: "open",
          note: "-",
          note_blank: true,
          line: 93,
          plan_uri: null,
          plan_progress: null,
        },
      ],
    },
  ],
  plans: [
    {
      document_id: "0f0e1d2c-0000-4000-8000-0000000000b2",
      uri: PLAN_URI,
      title: "Work-log increment 6: UI and checkpoint removal",
      content_hash: "demo-plan-hash",
      workstream: {
        id: "0f0e1d2c-0000-4000-8000-000000000001",
        key: "work-log-increment-6",
        state: "open",
      },
      other_workstreams: 0,
      spec_uri: SPEC_URI,
      untracked: null,
      orphans: [],
      error: null,
      tasks: [
        {
          number: 1,
          label: "Task 1: Work log panel",
          title: "Work log panel",
          line: 40,
          state: "done",
          raw_state: "done",
          untracked: null,
          shared_number: false,
          blocked_reason: null,
          commit: "9513b71",
          last_activity: "2026-07-24T10:00:00Z",
          steps: [
            { checked: false, text: "**Step 1: Write the failing test**" },
          ],
        },
        {
          number: 2,
          label: "Task 2: Activity list",
          title: "Activity list",
          line: 120,
          state: "done",
          raw_state: "done",
          untracked: null,
          shared_number: false,
          blocked_reason: null,
          commit: "1330d43",
          last_activity: "2026-07-24T12:00:00Z",
          steps: [],
        },
        {
          number: 3,
          label: "Task 3: Revisions sheet",
          title: "Revisions sheet",
          line: 200,
          state: "blocked",
          raw_state: "blocked",
          untracked: null,
          shared_number: false,
          blocked_reason: "Task 3: BLOCKED — waiting on an owner ruling\n",
          commit: null,
          last_activity: "2026-07-24T14:10:00Z",
          steps: [],
        },
        {
          number: 4,
          label: "Task 4: Checkpoint removal",
          title: "Checkpoint removal",
          line: 260,
          state: "todo",
          raw_state: null,
          untracked: null,
          shared_number: false,
          blocked_reason: null,
          commit: null,
          last_activity: null,
          steps: [],
        },
      ],
    },
  ],
}

export function demoBoardRecords(project: string): BoardRecords {
  return project === "darkmem"
    ? { project, ...DARKMEM }
    : { project, registers: [], plans: [] }
}

/** The server's two built-ins (`app/services/board_views.py`); the demo has
 *  no saved views. */
export const DEMO_BOARD_VIEWS: BoardView[] = [
  {
    id: "builtin:open-register-items",
    project: "darkmem",
    name: "Open register items",
    position: 0,
    builtin: true,
    created_at: null,
    updated_at: null,
    definition: {
      layout: "board",
      group_by: "state",
      filters: [
        { property: "type", operator: "in", values: ["register_row"] },
        { property: "state", operator: "not_in", values: ["done", "n/a"] },
      ],
      sort: { property: "number", direction: "asc" },
      columns: [
        "type",
        "number",
        "title",
        "state",
        "source",
        "assigned",
        "note",
      ],
      show_untracked: false,
    },
  },
  {
    id: "builtin:plans-in-flight",
    project: "darkmem",
    name: "Plans in flight",
    position: 1,
    builtin: true,
    created_at: null,
    updated_at: null,
    definition: {
      layout: "board",
      group_by: "plan",
      filters: [
        { property: "type", operator: "in", values: ["plan_task"] },
        { property: "workstream_state", operator: "in", values: ["open"] },
      ],
      sort: { property: "number", direction: "asc" },
      columns: ["number", "title", "state", "plan", "commit", "last_activity"],
      show_untracked: false,
    },
  },
]
````

- [ ] **Step 4: Write the hooks**

In `frontend/src/hooks/api/use-board-api.ts` (prepend the imports), replace:

````ts
export type Untracked = "no_workstream" | "no_properties"
````

with:

````ts
import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import { demoBoardRecords, DEMO_BOARD_VIEWS } from "@/demo/board"

export type Untracked = "no_workstream" | "no_properties"
````

Append to `frontend/src/hooks/api/use-board-api.ts`, at the end of the file:

````ts

/** How often the board re-reads its records while the Progress tab is shown.
 *  The server answers 304 from two aggregates when nothing changed. */
export const BOARD_REFRESH_MS = 10_000

const DEMO_REFUSAL = "The demo is read-only: its board cannot be changed."

export function useBoardRecords(project: string) {
  return useQuery<BoardRecords>({
    queryKey: ["boardRecords", project],
    queryFn: () =>
      apiFetch<BoardRecords>(
        `/board/records?${new URLSearchParams({ project })}`,
      ),
    enabled: !DEMO,
    refetchInterval: DEMO ? false : BOARD_REFRESH_MS,
    initialData: DEMO ? demoBoardRecords(project) : undefined,
  })
}

export function useBoardViews(project: string) {
  return useQuery<BoardView[]>({
    queryKey: ["boardViews", project],
    queryFn: () =>
      apiFetch<BoardView[]>(`/board/views?${new URLSearchParams({ project })}`),
    enabled: !DEMO,
    initialData: DEMO
      ? DEMO_BOARD_VIEWS.map((view) => ({ ...view, project }))
      : undefined,
  })
}

function invalidate(
  qc: QueryClient,
  key: "boardRecords" | "boardViews",
  project: string,
) {
  void qc.invalidateQueries({ queryKey: [key, project] })
}

export function useRegisterRowEdit(project: string) {
  const qc = useQueryClient()
  return useMutation<
    RowEditResult,
    Error,
    { documentId: string; number: number; expectedHash: string } & RowChanges
  >({
    mutationFn: ({ documentId, number, expectedHash, ...changes }) =>
      DEMO
        ? Promise.reject(new Error(DEMO_REFUSAL))
        : apiFetch<RowEditResult>(
            `/board/registers/${documentId}/rows/${number}`,
            {
              method: "PATCH",
              body: JSON.stringify({ expected_hash: expectedHash, ...changes }),
            },
          ),
    onSettled: () => invalidate(qc, "boardRecords", project),
  })
}

export function useCreateBoardView(project: string) {
  const qc = useQueryClient()
  return useMutation<
    BoardView,
    Error,
    { name: string; definition: ViewDefinition }
  >({
    mutationFn: ({ name, definition }) =>
      DEMO
        ? Promise.reject(new Error(DEMO_REFUSAL))
        : apiFetch<BoardView>("/board/views", {
            method: "POST",
            body: JSON.stringify({ project, name, definition }),
          }),
    onSuccess: () => invalidate(qc, "boardViews", project),
  })
}

export function useUpdateBoardView(project: string) {
  const qc = useQueryClient()
  return useMutation<
    BoardView,
    Error,
    { id: string; name?: string; definition?: ViewDefinition }
  >({
    mutationFn: ({ id, ...changes }) =>
      DEMO
        ? Promise.reject(new Error(DEMO_REFUSAL))
        : apiFetch<BoardView>(`/board/views/${encodeURIComponent(id)}`, {
            method: "PATCH",
            body: JSON.stringify(changes),
          }),
    onSuccess: () => invalidate(qc, "boardViews", project),
  })
}

export function useDeleteBoardView(project: string) {
  const qc = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (id) =>
      DEMO
        ? Promise.reject(new Error(DEMO_REFUSAL))
        : apiFetch<void>(`/board/views/${encodeURIComponent(id)}`, {
            method: "DELETE",
          }),
    onSuccess: () => invalidate(qc, "boardViews", project),
  })
}
````

- [ ] **Step 5: Register the keys and the export**

`src/lib/__tests__/query-keys.test.ts` fails on any `queryKey` literal missing from this map.

In `frontend/src/lib/query-keys.ts`, replace:

````ts
  worklogResume: {
````

with:

````ts
  boardRecords: {
    kind: "manual",
    reason:
      "GET /board/records requires an explicit `project`; the Progress tab passes the workspace's route param",
  },
  boardViews: {
    kind: "manual",
    reason:
      "GET /board/views requires an explicit `project`; the Progress tab passes the workspace's route param",
  },
  worklogResume: {
````

In `frontend/src/hooks/api/index.ts`, replace:

````ts
export * from "./use-worklog-api"
````

with:

````ts
export * from "./use-worklog-api"
export * from "./use-board-api"
````

- [ ] **Step 6: Move the demo-import floor**

The count is two-sided: `use-board-api.ts` adds one warn-level `src/demo/*` import.

In `frontend/src/__tests__/no-restricted-imports-count.test.ts`, replace:

````ts
    // and the tab's test reads the same fixture.
    expect(countByRule(results, "no-restricted-imports")).toBe(112)
````

with:

````ts
    // and the tab's test reads the same fixture.
    // Re-measured when the board hooks landed: 113 — `use-board-api.ts`
    // imports its fixtures for `initialData` in demo mode (the work-log shape).
    expect(countByRule(results, "no-restricted-imports")).toBe(113)
````

- [ ] **Step 7: Run the tests and the typecheck**

Run: `cd frontend && npx vitest run src/hooks src/lib src/__tests__`
Expected: all pass

Run: `cd frontend && npm run typecheck`
Expected: no errors

- [ ] **Step 8: Commit**

````bash
git add frontend/src/hooks/api/use-board-api.ts frontend/src/demo/board.ts frontend/src/lib/query-keys.ts frontend/src/hooks/api/index.ts frontend/src/__tests__/no-restricted-imports-count.test.ts frontend/src/hooks/api/__tests__/use-board-api.demo.test.tsx frontend/src/hooks/api/__tests__/use-board-api.test.tsx
git commit -m "feat(frontend): read board records and views"
````

---

### Task 14: The row editor and the Note dialog

**Files:**
- Create: `frontend/src/features/board/use-row-editor.ts`, `frontend/src/features/board/components/note-dialog.tsx`
- Create: `frontend/src/features/board/__tests__/fixtures.ts` (shared by Tasks 15-18's tests)
- Test: `frontend/src/features/board/__tests__/row-editor.test.tsx`

**Interfaces:**
- Consumes: Task 11's `ApiError.code`; Task 12's `planMove`, `isBlankNote`, `BoardRecord`; Task 13's `useRegisterRowEdit`.
- Produces: `useRowEditor(project)` returning `{save, move, prompt, confirmPrompt, cancelPrompt, pendingId}`, type `RowEditor`, `NotePrompt`, `CONFLICT_MESSAGE`; `NoteDialog({prompt, onCancel, onConfirm})`; test fixture `RECORDS` (Contracts §Frontend).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

Pessimistic edits (§3 Dragging): nothing moves until the PATCH answers, and every answer re-reads the records (the hook's `onSettled`). A `hash_conflict` toasts `CONFLICT_MESSAGE`; any other refusal toasts the server's own message.

- [ ] **Step 1: Write the fixtures and the failing tests**

Create `frontend/src/features/board/__tests__/fixtures.ts` with:

````ts
import type { BoardRecords } from "@/hooks/api/use-board-api"

/** One register (rows in open, verify and an unrecognised state) and one
 *  tracked plan (a done and a blocked task) for the board's component tests. */
export const RECORDS: BoardRecords = {
  project: "darkmem",
  registers: [
    {
      document_id: "reg",
      uri: "superpowers/registers/r.md",
      title: "Register",
      covers: null,
      content_hash: "h1",
      block_first: false,
      malformed: [],
      error: null,
      rows: [
        {
          number: 1,
          item: "Alpha",
          assigned: "-",
          acceptance: "-",
          state: "open",
          raw_state: "open",
          note: "-",
          note_blank: true,
          line: 5,
          plan_uri: null,
          plan_progress: null,
        },
        {
          number: 2,
          item: "Beta",
          assigned: "docs/superpowers/plans/p.md",
          acceptance: "-",
          state: "verify",
          raw_state: "verify",
          note: "check beta",
          note_blank: false,
          line: 6,
          plan_uri: "superpowers/plans/p.md",
          plan_progress: { done: 1, total: 2, untracked: null },
        },
      ],
    },
  ],
  plans: [
    {
      document_id: "plan",
      uri: "superpowers/plans/p.md",
      title: "Plan",
      content_hash: "h2",
      workstream: { id: "w", key: "plan-key", state: "open" },
      other_workstreams: 0,
      spec_uri: "superpowers/specs/s.md",
      untracked: null,
      orphans: [],
      error: null,
      tasks: [
        {
          number: 1,
          label: "Task 1: One",
          title: "One",
          line: 3,
          state: "done",
          raw_state: "done",
          untracked: null,
          shared_number: false,
          blocked_reason: null,
          commit: "abc1234def",
          last_activity: "2026-10-13T00:00:00Z",
          steps: [
            { checked: false, text: "**Step 1: Write the failing test**" },
          ],
        },
        {
          number: 2,
          label: "Task 2: Two",
          title: "Two",
          line: 9,
          state: "blocked",
          raw_state: "blocked",
          untracked: null,
          shared_number: false,
          blocked_reason: "waiting on beta",
          commit: null,
          last_activity: null,
          steps: [],
        },
      ],
    },
    {
      document_id: "loose",
      uri: "superpowers/plans/loose.md",
      title: "Loose",
      content_hash: "h3",
      workstream: null,
      other_workstreams: 0,
      spec_uri: null,
      untracked: "no_workstream",
      orphans: [],
      error: null,
      tasks: [
        {
          number: 1,
          label: "Task 1: Loose",
          title: "Loose",
          line: 3,
          state: "untracked",
          raw_state: null,
          untracked: "no_workstream",
          shared_number: false,
          blocked_reason: null,
          commit: null,
          last_activity: null,
          steps: [],
        },
      ],
    },
  ],
}
````

Create `frontend/src/features/board/__tests__/row-editor.test.tsx` with:

````tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, render, renderHook, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

import { toast } from "darkraise-ui/components/sonner"
import { ApiError, apiFetch } from "@/lib/api"
import { flattenRecords, type BoardRecord } from "../lib/records"
import { NoteDialog } from "../components/note-dialog"
import { CONFLICT_MESSAGE, useRowEditor } from "../use-row-editor"
import { RECORDS } from "./fixtures"

const records = flattenRecords(RECORDS)
const byTitle = (title: string) =>
  records.find((r) => r.title === title) as BoardRecord

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(toast.error).mockReset()
})

describe("NoteDialog", () => {
  it("holds the current Note and stays disabled while it is blank or a dash", async () => {
    const onConfirm = vi.fn()
    const user = userEvent.setup()
    render(
      <NoteDialog
        prompt={{ record: byTitle("Alpha"), state: "deferred" }}
        onCancel={vi.fn()}
        onConfirm={onConfirm}
      />,
    )
    const note = screen.getByLabelText("Note")
    expect(note).toHaveValue("-")
    expect(screen.getByRole("button", { name: "Move" })).toBeDisabled()
    await user.clear(note)
    await user.type(note, "  ")
    expect(screen.getByRole("button", { name: "Move" })).toBeDisabled()
    await user.type(note, "waiting on the owner")
    await user.click(screen.getByRole("button", { name: "Move" }))
    expect(onConfirm).toHaveBeenCalledWith("waiting on the owner")
  })
})

describe("useRowEditor", () => {
  it("asks for a Note before a move into deferred, and patches after it", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      document_id: "reg",
      content_hash: "h2",
      row: {},
    })
    const { result } = renderHook(() => useRowEditor("darkmem"), { wrapper })
    act(() => result.current.move(byTitle("Alpha"), "deferred"))
    expect(result.current.prompt?.state).toBe("deferred")
    expect(apiFetch).not.toHaveBeenCalled()
    act(() => result.current.confirmPrompt("parked for now"))
    await vi.waitFor(() => expect(apiFetch).toHaveBeenCalled())
    expect(vi.mocked(apiFetch).mock.calls[0]).toEqual([
      "/board/registers/reg/rows/1",
      {
        method: "PATCH",
        body: JSON.stringify({
          expected_hash: "h1",
          state: "deferred",
          note: "parked for now",
        }),
      },
    ])
  })

  it("never patches a plan task", () => {
    const { result } = renderHook(() => useRowEditor("darkmem"), { wrapper })
    act(() => result.current.move(byTitle("One"), "todo"))
    expect(apiFetch).not.toHaveBeenCalled()
    expect(result.current.prompt).toBeNull()
  })

  it("names a conflict as a reload and shows any other refusal's own message", async () => {
    const { result } = renderHook(() => useRowEditor("darkmem"), { wrapper })
    vi.mocked(apiFetch).mockRejectedValueOnce(
      new ApiError("stale", 409, [{ current_hash: "h9" }], "hash_conflict"),
    )
    act(() => result.current.move(byTitle("Alpha"), "doing"))
    await vi.waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(CONFLICT_MESSAGE),
    )
    vi.mocked(apiFetch).mockRejectedValueOnce(
      new ApiError(
        "a row in 'verify' needs a Note",
        422,
        undefined,
        "note_required",
      ),
    )
    act(() => result.current.save(byTitle("Beta"), { note: "" }))
    await vi.waitFor(() =>
      expect(toast.error).toHaveBeenLastCalledWith(
        "a row in 'verify' needs a Note",
      ),
    )
  })
})
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd frontend && npx vitest run src/features/board/__tests__/row-editor.test.tsx`
Expected: FAIL: cannot resolve `../use-row-editor`

- [ ] **Step 3: Write the editor and the dialog**

Create `frontend/src/features/board/use-row-editor.ts` with:

````ts
import { useState } from "react"
import { toast } from "darkraise-ui/components/sonner"
import { useRegisterRowEdit, type RowChanges } from "@/hooks/api"
import { ApiError } from "@/lib/api"
import { planMove, type BoardRecord } from "./lib/records"

export const CONFLICT_MESSAGE =
  "This register changed since the board loaded it; the board has reloaded it. Try again."

/** A move into a state that needs a Note, waiting for one. */
export interface NotePrompt {
  record: BoardRecord
  state: string
}

/** Register row edits from the board and the table. Pessimistic: nothing
 *  moves until the PATCH answers, and every answer re-reads the records. */
export function useRowEditor(project: string) {
  const mutation = useRegisterRowEdit(project)
  const [prompt, setPrompt] = useState<NotePrompt | null>(null)

  const save = (record: BoardRecord, changes: RowChanges) => {
    if (record.type !== "register_row" || !record.contentHash) return
    mutation.mutate(
      {
        documentId: record.documentId,
        number: record.number,
        expectedHash: record.contentHash,
        ...changes,
      },
      {
        onError: (error) =>
          toast.error(
            error instanceof ApiError && error.code === "hash_conflict"
              ? CONFLICT_MESSAGE
              : error.message,
          ),
      },
    )
  }

  const move = (record: BoardRecord, toState: string) => {
    const intent = planMove(record, toState)
    if (intent === "note") setPrompt({ record, state: toState })
    else if (intent === "patch") save(record, { state: toState })
  }

  const confirmPrompt = (note: string) => {
    if (prompt) save(prompt.record, { state: prompt.state, note })
    setPrompt(null)
  }

  const variables = mutation.isPending ? mutation.variables : undefined
  const pendingId = variables
    ? `r:${variables.documentId}:${variables.number}`
    : null

  return {
    save,
    move,
    prompt,
    confirmPrompt,
    cancelPrompt: () => setPrompt(null),
    pendingId,
  }
}

export type RowEditor = ReturnType<typeof useRowEditor>
````

Create `frontend/src/features/board/components/note-dialog.tsx` with:

````tsx
import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Label } from "darkraise-ui/components/label"
import { Textarea } from "darkraise-ui/components/textarea"
import { isBlankNote } from "../lib/records"
import type { NotePrompt } from "../use-row-editor"

function NoteForm({
  prompt,
  onCancel,
  onConfirm,
}: {
  prompt: NotePrompt
  onCancel: () => void
  onConfirm: (note: string) => void
}) {
  const [note, setNote] = useState(prompt.record.note ?? "")
  return (
    <>
      <DialogHeader>
        <DialogTitle>
          Move {prompt.record.label} to {prompt.state}
        </DialogTitle>
        <DialogDescription>
          A row in {prompt.state} needs a Note saying why. A dash counts as
          blank.
        </DialogDescription>
      </DialogHeader>
      <div className="space-y-1.5">
        <Label htmlFor="board-note">Note</Label>
        <Textarea
          id="board-note"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          rows={4}
        />
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          disabled={isBlankNote(note)}
          onClick={() => onConfirm(note.trim())}
        >
          Move
        </Button>
      </DialogFooter>
    </>
  )
}

/** The Note a move into verify, deferred or n/a needs (§3). Confirm stays
 *  disabled while the Note is blank, the rule the server enforces too. */
export function NoteDialog({
  prompt,
  onCancel,
  onConfirm,
}: {
  prompt: NotePrompt | null
  onCancel: () => void
  onConfirm: (note: string) => void
}) {
  return (
    <Dialog open={prompt !== null} onOpenChange={(open) => !open && onCancel()}>
      <DialogContent>
        {prompt ? (
          <NoteForm
            key={`${prompt.record.id}:${prompt.state}`}
            prompt={prompt}
            onCancel={onCancel}
            onConfirm={onConfirm}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
````

- [ ] **Step 4: Run the tests and the typecheck**

Run: `cd frontend && npx vitest run src/features/board`
Expected: all pass

Run: `cd frontend && npm run typecheck`
Expected: no errors

- [ ] **Step 5: Commit**

````bash
git add frontend/src/features/board/use-row-editor.ts frontend/src/features/board/components/note-dialog.tsx frontend/src/features/board/__tests__/fixtures.ts frontend/src/features/board/__tests__/row-editor.test.tsx
git commit -m "feat(frontend): edit register rows from the board"
````

---

### Task 15: The board view and its cards

**Files:**
- Create: `frontend/src/features/board/components/record-card.tsx`, `frontend/src/features/board/components/board-view.tsx`
- Test: `frontend/src/features/board/__tests__/board-view.test.tsx`

**Interfaces:**
- Consumes: Task 12's `boardLanes`, `BoardLane`, `BoardColumn`, `formatProgress`, `NOTE_REQUIRED`, `UNTRACKED_LABEL`, `shortName`; Task 14's fixtures.
- Produces: `BoardView({lanes, pendingId, onMove, onOpen})`, `dropTarget(event)`, `DROP_PREFIX`; `RecordCard`, `LEDGER_LOCK` (Contracts §Frontend).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

Only register cards in the register lane of a State grouping are draggable, and only that lane's columns (not `unrecognised`) are drop targets. dnd-kit's pointer pipeline does not run under happy-dom, so the drop logic lives in `dropTarget`, which the unit test reaches; Task 22's Playwright spec drives a real drag. The mouse sensor's 6px distance keeps a click a click (the page tree's precedent, `features/notes/page-tree.tsx`).

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/features/board/__tests__/board-view.test.tsx` with:

````tsx
import { render, screen, within } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { boardLanes, flattenRecords, type BoardRecord } from "../lib/records"
import { BoardView, dropTarget } from "../components/board-view"
import { RECORDS } from "./fixtures"

const records = flattenRecords(RECORDS)
const byTitle = (title: string) =>
  records.find((r) => r.title === title) as BoardRecord

describe("BoardView", () => {
  it("renders one swimlane per type, each over its own vocabulary", () => {
    const tracked = records.filter((r) => r.state !== "untracked")
    render(
      <BoardView
        lanes={boardLanes(tracked, "state", false)}
        pendingId={null}
        onMove={vi.fn()}
        onOpen={vi.fn()}
      />,
    )
    const rows = screen.getByRole("region", { name: "Register rows" })
    const tasks = screen.getByRole("region", { name: "Plan tasks" })
    expect(
      within(rows).getByRole("heading", { name: /^verify/ }),
    ).toBeInTheDocument()
    expect(within(rows).queryByRole("heading", { name: /^todo/ })).toBeNull()
    expect(
      within(tasks).getByRole("heading", { name: /^blocked/ }),
    ).toBeInTheDocument()
    expect(
      within(tasks).queryByRole("heading", { name: /^planned/ }),
    ).toBeNull()
  })

  it("makes register cards draggable and plan-task cards locked", () => {
    render(
      <BoardView
        lanes={boardLanes(records, "state", false)}
        pendingId={null}
        onMove={vi.fn()}
        onOpen={vi.fn()}
      />,
    )
    const row = screen.getByRole("button", { name: /#1 Alpha/ })
    expect(row).toHaveAttribute("aria-roledescription", "draggable")
    const task = screen.getByRole("article", { name: /Task 2: Two/ })
    expect(task).not.toHaveAttribute("aria-roledescription")
    expect(
      within(task).getByLabelText("state comes from the plan's ledger"),
    ).toBeInTheDocument()
    expect(within(task).getByText("waiting on beta")).toBeInTheDocument()
  })

  it("shows a pending card as saving", () => {
    render(
      <BoardView
        lanes={boardLanes(records, "state", false)}
        pendingId={byTitle("Alpha").id}
        onMove={vi.fn()}
        onOpen={vi.fn()}
      />,
    )
    expect(screen.getByText("saving…")).toBeInTheDocument()
  })

  it("reads a drop's target state only from a register column", () => {
    expect(dropTarget({ over: { id: "state:planned" } } as never)).toBe(
      "planned",
    )
    expect(dropTarget({ over: { id: "elsewhere" } } as never)).toBeNull()
    expect(dropTarget({ over: null })).toBeNull()
  })
})
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd frontend && npx vitest run src/features/board/__tests__/board-view.test.tsx`
Expected: FAIL: cannot resolve `../components/board-view`

- [ ] **Step 3: Write the card and the view**

Create `frontend/src/features/board/components/record-card.tsx` with:

````tsx
import { useDraggable } from "@dnd-kit/core"
import { Lock } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { cn } from "darkraise-ui/lib"
import { formatWhen } from "@/lib/format"
import {
  formatProgress,
  NOTE_REQUIRED,
  shortName,
  UNTRACKED_LABEL,
  type BoardRecord,
} from "../lib/records"

export const LEDGER_LOCK = "state comes from the plan's ledger"

/** One register row or plan task (§3 Cards). Only a register card in the
 *  register lane of a State grouping is draggable. */
export function RecordCard({
  record,
  draggable,
  pending,
  onOpen,
}: {
  record: BoardRecord
  draggable: boolean
  pending: boolean
  onOpen: (record: BoardRecord) => void
}) {
  const { setNodeRef, listeners, attributes, transform, isDragging } =
    useDraggable({
      id: record.id,
      disabled: !draggable || pending,
    })
  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined
  const isRow = record.type === "register_row"
  const progress = formatProgress(record.planProgress)
  return (
    <article
      ref={setNodeRef}
      style={style}
      {...(draggable ? listeners : {})}
      {...(draggable ? attributes : {})}
      aria-label={`${record.label} ${record.title}`}
      aria-busy={pending || undefined}
      onClick={() => onOpen(record)}
      className={cn(
        "bg-card border-border space-y-1.5 rounded-md border p-2.5 text-sm",
        draggable && "cursor-grab",
        isDragging && "z-10 shadow-lg",
        pending && "opacity-60",
      )}
    >
      <div className="flex items-center gap-1.5">
        <Badge variant={isRow ? "secondary" : "outline"}>
          {isRow ? "row" : "task"}
        </Badge>
        <span className="text-muted-foreground truncate font-mono text-xs">
          {isRow ? record.label : `Task ${record.number}`} ·{" "}
          {shortName(record.source)}
        </span>
        {!isRow ? (
          <Lock
            className="text-muted-foreground ml-auto size-3.5 shrink-0"
            aria-label={LEDGER_LOCK}
          >
            <title>{LEDGER_LOCK}</title>
          </Lock>
        ) : null}
      </div>
      <p className="font-medium">{record.title}</p>
      {pending ? (
        <p className="text-muted-foreground text-xs">saving…</p>
      ) : null}
      {isRow && record.assigned && record.assigned !== "-" ? (
        <p className="text-muted-foreground truncate text-xs">
          {record.assigned}
        </p>
      ) : null}
      {isRow && progress ? <p className="text-xs">{progress}</p> : null}
      {isRow && NOTE_REQUIRED.has(record.state) && !record.noteBlank ? (
        <p className="text-muted-foreground text-xs">{record.note}</p>
      ) : null}
      {isRow && record.blockFirst ? (
        <p className="text-destructive text-xs">
          block-first: delete and re-file this register to edit it here
        </p>
      ) : null}
      {!isRow && record.commit ? (
        <p className="font-mono text-xs">{record.commit.slice(0, 7)}</p>
      ) : null}
      {!isRow && record.lastActivity ? (
        <p className="text-muted-foreground text-xs">
          {formatWhen(record.lastActivity)}
        </p>
      ) : null}
      {!isRow && record.state === "blocked" && record.note ? (
        <p className="text-xs whitespace-pre-wrap">{record.note}</p>
      ) : null}
      {record.untracked ? (
        <p className="text-muted-foreground text-xs">
          {UNTRACKED_LABEL[record.untracked]}
        </p>
      ) : null}
      {record.sharedNumber ? (
        <p className="text-xs">
          shares task number {record.number}; the ledger cannot tell them apart
        </p>
      ) : null}
    </article>
  )
}
````

Create `frontend/src/features/board/components/board-view.tsx` with:

````tsx
import {
  DndContext,
  KeyboardSensor,
  MouseSensor,
  TouchSensor,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core"
import { cn } from "darkraise-ui/lib"
import type { BoardColumn, BoardLane, BoardRecord } from "../lib/records"
import { RecordCard } from "./record-card"

export const DROP_PREFIX = "state:"

/** A drop's target state, or null when it did not land on a register column. */
export function dropTarget(event: Pick<DragEndEvent, "over">): string | null {
  const id = event.over ? String(event.over.id) : ""
  return id.startsWith(DROP_PREFIX) ? id.slice(DROP_PREFIX.length) : null
}

function Column({
  column,
  droppable,
  draggable,
  pendingId,
  onOpen,
}: {
  column: BoardColumn
  droppable: boolean
  draggable: boolean
  pendingId: string | null
  onOpen: (record: BoardRecord) => void
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: `${DROP_PREFIX}${column.key}`,
    disabled: !droppable,
  })
  return (
    <section
      ref={setNodeRef}
      aria-label={`column ${column.title}`}
      className={cn(
        "bg-muted/30 flex w-64 shrink-0 flex-col gap-2 rounded-md p-2",
        isOver && droppable && "ring-primary ring-2",
      )}
    >
      <h3 className="flex items-center justify-between text-sm font-semibold">
        <span>{column.title}</span>
        <span className="text-muted-foreground font-mono text-xs">
          {column.records.length}
        </span>
      </h3>
      {column.records.map((record) => (
        <RecordCard
          key={record.id}
          record={record}
          draggable={draggable && !record.blockFirst}
          pending={record.id === pendingId}
          onOpen={onOpen}
        />
      ))}
    </section>
  )
}

/** The board layout (§3 Board). Register cards drag between the register
 *  lane's state columns; nothing else is draggable or a drop target. */
export function BoardView({
  lanes,
  pendingId,
  onMove,
  onOpen,
}: {
  lanes: BoardLane[]
  pendingId: string | null
  onMove: (record: BoardRecord, toState: string) => void
  onOpen: (record: BoardRecord) => void
}) {
  const sensors = useSensors(
    // Without a distance every click is a zero-length drag and a card never opens.
    useSensor(MouseSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, {
      activationConstraint: { delay: 220, tolerance: 6 },
    }),
    useSensor(KeyboardSensor),
  )
  const byId = new Map(
    lanes
      .flatMap((lane) => lane.columns.flatMap((c) => c.records))
      .map((r) => [r.id, r]),
  )
  const handleDragEnd = (event: DragEndEvent) => {
    const state = dropTarget(event)
    const record = byId.get(String(event.active.id))
    if (state && record) onMove(record, state)
  }
  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <div className="space-y-4">
        {lanes.map((lane) => {
          const registerLane = lane.type === "register_row"
          return (
            <section
              key={lane.key}
              aria-label={lane.title || "board"}
              className="space-y-2"
            >
              {lane.title ? (
                <h2 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                  {lane.title}
                </h2>
              ) : null}
              <div className="flex gap-3 overflow-x-auto pb-2">
                {lane.columns.map((column) => (
                  <Column
                    key={column.key}
                    column={column}
                    droppable={registerLane && column.key !== "unrecognised"}
                    draggable={registerLane}
                    pendingId={pendingId}
                    onOpen={onOpen}
                  />
                ))}
              </div>
            </section>
          )
        })}
      </div>
    </DndContext>
  )
}
````

- [ ] **Step 4: Run the tests and the typecheck**

Run: `cd frontend && npx vitest run src/features/board`
Expected: all pass

Run: `cd frontend && npm run typecheck`
Expected: no errors

- [ ] **Step 5: Commit**

````bash
git add frontend/src/features/board/components/record-card.tsx frontend/src/features/board/components/board-view.tsx frontend/src/features/board/__tests__/board-view.test.tsx
git commit -m "feat(frontend): lay the board out in state swimlanes"
````

---

### Task 16: The table and the detail sheet

**Files:**
- Create: `frontend/src/features/board/components/records-table.tsx`, `frontend/src/features/board/components/record-detail-sheet.tsx`
- Test: `frontend/src/features/board/__tests__/records-table.test.tsx`

**Interfaces:**
- Consumes: Task 12's library; Task 14's `RowEditor` and fixtures.
- Produces: `RecordsTable({records, definition, onDefinitionChange, editor, onOpen})`, `displayValue(record, property)`; `RecordDetailSheet({record, onClose, onOpenDocument, onShowInWorkLog})` (Contracts §Frontend).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

Note and Assigned edit through darkraise-ui `editable` (submit on Enter or blur), State through `select`, all through the same PATCH. The `Editable` is keyed on the server value, so a reload after a conflict shows what the file holds. The step checklist is labelled as the implementer's and is never counted.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/features/board/__tests__/records-table.test.tsx` with:

````tsx
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import type { ViewDefinition } from "@/hooks/api"
import { flattenRecords, type BoardRecord } from "../lib/records"
import { RecordsTable } from "../components/records-table"
import { RecordDetailSheet } from "../components/record-detail-sheet"
import type { RowEditor } from "../use-row-editor"
import { RECORDS } from "./fixtures"

const records = flattenRecords(RECORDS)
const byTitle = (title: string) =>
  records.find((r) => r.title === title) as BoardRecord
const TABLE: ViewDefinition = {
  layout: "table",
  group_by: null,
  filters: [],
  sort: null,
  columns: ["number", "title", "state", "assigned", "note"],
  show_untracked: true,
}

function editor(): RowEditor {
  return {
    save: vi.fn(),
    move: vi.fn(),
    prompt: null,
    confirmPrompt: vi.fn(),
    cancelPrompt: vi.fn(),
    pendingId: null,
  }
}

describe("RecordsTable", () => {
  it("sorts on a header click, flipping direction on a second click", async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    const { rerender } = render(
      <RecordsTable
        records={records}
        definition={TABLE}
        onDefinitionChange={onChange}
        editor={editor()}
        onOpen={vi.fn()}
      />,
    )
    await user.click(screen.getByRole("button", { name: "Title" }))
    expect(onChange).toHaveBeenLastCalledWith({
      ...TABLE,
      sort: { property: "title", direction: "asc" },
    })
    const sorted = {
      ...TABLE,
      sort: { property: "title", direction: "asc" } as const,
    }
    rerender(
      <RecordsTable
        records={records}
        definition={sorted}
        onDefinitionChange={onChange}
        editor={editor()}
        onOpen={vi.fn()}
      />,
    )
    expect(screen.getByRole("columnheader", { name: /Title/ })).toHaveAttribute(
      "aria-sort",
      "ascending",
    )
    await user.click(screen.getByRole("button", { name: "Title ↑" }))
    expect(onChange).toHaveBeenLastCalledWith({
      ...TABLE,
      sort: { property: "title", direction: "desc" },
    })
  })

  it("edits State only on register rows", () => {
    render(
      <RecordsTable
        records={records}
        definition={TABLE}
        onDefinitionChange={vi.fn()}
        editor={editor()}
        onOpen={vi.fn()}
      />,
    )
    expect(
      screen.getByRole("combobox", { name: "State of #1" }),
    ).toBeInTheDocument()
    expect(screen.queryByRole("combobox", { name: /State of Task/ })).toBeNull()
    const taskRow = screen.getByRole("button", { name: "Two" }).closest("tr")!
    expect(within(taskRow).getByText("blocked")).toBeInTheDocument()
  })

  it("commits an edited Note through the same PATCH", async () => {
    const rows = editor()
    const user = userEvent.setup()
    render(
      <RecordsTable
        records={records}
        definition={TABLE}
        onDefinitionChange={vi.fn()}
        editor={rows}
        onOpen={vi.fn()}
      />,
    )
    await user.click(screen.getByLabelText("Note of #2"))
    const input = screen.getByLabelText("Edit Note of #2")
    await user.clear(input)
    await user.type(input, "checked by hand{Enter}")
    expect(rows.save).toHaveBeenCalledWith(byTitle("Beta"), {
      note: "checked by hand",
    })
  })
})

describe("RecordDetailSheet", () => {
  it("shows every property, the labelled checklist and the Work log link", async () => {
    const onShow = vi.fn()
    const onOpenDocument = vi.fn()
    const user = userEvent.setup()
    render(
      <RecordDetailSheet
        record={byTitle("One")}
        onClose={vi.fn()}
        onOpenDocument={onOpenDocument}
        onShowInWorkLog={onShow}
      />,
    )
    expect(screen.getByText("Commit")).toBeInTheDocument()
    expect(screen.getByText("abc1234def")).toBeInTheDocument()
    const checklist = screen.getByRole("region", {
      name: "implementer's checklist",
    })
    expect(
      within(checklist).getByText("Step 1: Write the failing test"),
    ).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Show in Work log" }))
    expect(onShow).toHaveBeenCalledWith("plan-key", 1)
    await user.click(screen.getByRole("button", { name: "Open spec" }))
    expect(onOpenDocument).toHaveBeenCalledWith("superpowers/specs/s.md")
  })

  it("links a register row to its register and its assigned plan", async () => {
    const onOpenDocument = vi.fn()
    const user = userEvent.setup()
    render(
      <RecordDetailSheet
        record={byTitle("Beta")}
        onClose={vi.fn()}
        onOpenDocument={onOpenDocument}
        onShowInWorkLog={vi.fn()}
      />,
    )
    await user.click(screen.getByRole("button", { name: "Open register" }))
    await user.click(screen.getByRole("button", { name: "Open plan" }))
    expect(onOpenDocument.mock.calls).toEqual([
      ["superpowers/registers/r.md"],
      ["superpowers/plans/p.md"],
    ])
  })
})
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd frontend && npx vitest run src/features/board/__tests__/records-table.test.tsx`
Expected: FAIL: cannot resolve `../components/records-table`

- [ ] **Step 3: Write the table and the sheet**

Create `frontend/src/features/board/components/records-table.tsx` with:

````tsx
import {
  Editable,
  EditableArea,
  EditableInput,
  EditablePreview,
} from "darkraise-ui/components/editable"
import { MultiSelect } from "darkraise-ui/components/multi-select"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "darkraise-ui/components/table"
import type { BoardProperty, ViewDefinition } from "@/hooks/api"
import { formatWhen } from "@/lib/format"
import {
  formatProgress,
  PROPERTIES,
  PROPERTY_LABELS,
  propertyValue,
  REGISTER_STATES,
  shortName,
  type BoardRecord,
} from "../lib/records"
import type { RowEditor } from "../use-row-editor"

/** A property as a table shows it: uris by short name, times relative. */
export function displayValue(
  record: BoardRecord,
  property: BoardProperty,
): string {
  switch (property) {
    case "type":
      return record.type === "register_row" ? "row" : "task"
    case "number":
      return record.label
    case "source":
    case "plan":
    case "spec":
      return shortName(propertyValue(record, property))
    case "plan_progress":
      return formatProgress(record.planProgress) ?? ""
    case "last_activity":
      return record.lastActivity ? formatWhen(record.lastActivity) : ""
    default:
      return propertyValue(record, property) ?? ""
  }
}

function TextCell({
  record,
  column,
  editor,
}: {
  record: BoardRecord
  column: "note" | "assigned"
  editor: RowEditor
}) {
  const value = (column === "note" ? record.note : record.assigned) ?? ""
  return (
    <Editable
      // Remounts on a new server value, so a reload shows what the file holds.
      key={value}
      defaultValue={value}
      disabled={record.blockFirst || record.id === editor.pendingId}
      onValueCommit={({ value: next }) => {
        if (next !== value) editor.save(record, { [column]: next })
      }}
    >
      <EditableArea>
        <EditablePreview
          aria-label={`${PROPERTY_LABELS[column]} of ${record.label}`}
        />
        <EditableInput
          aria-label={`Edit ${PROPERTY_LABELS[column]} of ${record.label}`}
        />
      </EditableArea>
    </Editable>
  )
}

function Cell({
  record,
  property,
  editor,
  onOpen,
}: {
  record: BoardRecord
  property: BoardProperty
  editor: RowEditor
  onOpen: (record: BoardRecord) => void
}) {
  const editable = record.type === "register_row" && !record.blockFirst
  if (property === "title") {
    return (
      <button
        type="button"
        className="text-left hover:underline"
        onClick={() => onOpen(record)}
      >
        {record.title}
      </button>
    )
  }
  if (editable && property === "state") {
    return (
      <Select
        value={record.state}
        disabled={record.id === editor.pendingId}
        onValueChange={(next) => editor.move(record, next)}
      >
        <SelectTrigger
          className="h-8 w-28"
          aria-label={`State of ${record.label}`}
        >
          <SelectValue>{record.state}</SelectValue>
        </SelectTrigger>
        <SelectContent>
          {REGISTER_STATES.map((state) => (
            <SelectItem key={state} value={state}>
              {state}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    )
  }
  if (editable && (property === "note" || property === "assigned")) {
    return <TextCell record={record} column={property} editor={editor} />
  }
  return <span>{displayValue(record, property)}</span>
}

/** The table layout (§3 Table): a column chooser, header-click sort, and
 *  register rows' State, Note and Assigned edited through the same PATCH. */
export function RecordsTable({
  records,
  definition,
  onDefinitionChange,
  editor,
  onOpen,
}: {
  records: BoardRecord[]
  definition: ViewDefinition
  onDefinitionChange: (next: ViewDefinition) => void
  editor: RowEditor
  onOpen: (record: BoardRecord) => void
}) {
  const columns =
    definition.columns.length > 0 ? definition.columns : PROPERTIES
  const sortBy = (property: BoardProperty) => {
    const current = definition.sort
    const direction =
      current?.property === property && current.direction === "asc"
        ? "desc"
        : "asc"
    onDefinitionChange({ ...definition, sort: { property, direction } })
  }
  return (
    <div className="space-y-2">
      <MultiSelect
        className="max-w-xl"
        placeholder="Columns"
        items={PROPERTIES.map((p) => ({ value: p, label: PROPERTY_LABELS[p] }))}
        value={columns}
        onValueChange={({ value }) =>
          onDefinitionChange({
            ...definition,
            columns: value as BoardProperty[],
          })
        }
      />
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((property) => {
              const sorted = definition.sort?.property === property
              return (
                <TableHead
                  key={property}
                  aria-sort={
                    sorted
                      ? definition.sort?.direction === "asc"
                        ? "ascending"
                        : "descending"
                      : undefined
                  }
                >
                  <button type="button" onClick={() => sortBy(property)}>
                    {PROPERTY_LABELS[property]}
                    {sorted
                      ? definition.sort?.direction === "asc"
                        ? " ↑"
                        : " ↓"
                      : ""}
                  </button>
                </TableHead>
              )
            })}
          </TableRow>
        </TableHeader>
        <TableBody>
          {records.map((record) => (
            <TableRow
              key={record.id}
              aria-busy={record.id === editor.pendingId || undefined}
            >
              {columns.map((property) => (
                <TableCell key={property}>
                  <Cell
                    record={record}
                    property={property}
                    editor={editor}
                    onOpen={onOpen}
                  />
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
````

Create `frontend/src/features/board/components/record-detail-sheet.tsx` with:

````tsx
import { Button } from "darkraise-ui/components/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "darkraise-ui/components/sheet"
import { plainText } from "@/lib/plain-text"
import {
  PROPERTIES,
  PROPERTY_LABELS,
  shortName,
  type BoardRecord,
} from "../lib/records"
import { displayValue } from "./records-table"

/** Every property of one record, its links, and a plan task's step checklist
 *  (§3 Detail sheet). The checklist is the implementer's, never progress. */
export function RecordDetailSheet({
  record,
  onClose,
  onOpenDocument,
  onShowInWorkLog,
}: {
  record: BoardRecord | null
  onClose: () => void
  onOpenDocument: (uri: string) => void
  onShowInWorkLog: (workstreamKey: string, task: number) => void
}) {
  return (
    <Sheet open={record !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-lg">
        {record ? (
          <>
            <SheetHeader>
              <SheetTitle>
                {record.label}{" "}
                {record.type === "register_row" ? record.title : ""}
              </SheetTitle>
              <SheetDescription>{shortName(record.source)}</SheetDescription>
            </SheetHeader>
            <div className="space-y-4 p-4">
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onOpenDocument(record.source)}
                >
                  {record.type === "register_row"
                    ? "Open register"
                    : "Open plan"}
                </Button>
                {record.type === "register_row" && record.plan ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onOpenDocument(record.plan!)}
                  >
                    Open plan
                  </Button>
                ) : null}
                {record.spec ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onOpenDocument(record.spec!)}
                  >
                    Open spec
                  </Button>
                ) : null}
                {record.type === "plan_task" && record.workstreamKey ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      onShowInWorkLog(record.workstreamKey!, record.number)
                    }
                  >
                    Show in Work log
                  </Button>
                ) : null}
              </div>
              <dl className="grid grid-cols-[8rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
                {PROPERTIES.map((property) => (
                  <div key={property} className="contents">
                    <dt className="text-muted-foreground">
                      {PROPERTY_LABELS[property]}
                    </dt>
                    <dd className="break-words whitespace-pre-wrap">
                      {displayValue(record, property) || "—"}
                    </dd>
                  </div>
                ))}
              </dl>
              {record.steps.length > 0 ? (
                <section
                  aria-label="implementer's checklist"
                  className="space-y-1.5"
                >
                  <h3 className="text-sm font-semibold">
                    Implementer's checklist (not progress)
                  </h3>
                  <ul className="space-y-1 text-sm">
                    {record.steps.map((step, index) => (
                      <li key={index} className="flex gap-2">
                        <span aria-hidden>{step.checked ? "☑" : "☐"}</span>
                        <span>{plainText(step.text)}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  )
}
````

- [ ] **Step 4: Run the tests and the typecheck**

Run: `cd frontend && npx vitest run src/features/board`
Expected: all pass

Run: `cd frontend && npm run typecheck`
Expected: no errors

- [ ] **Step 5: Commit**

````bash
git add frontend/src/features/board/components/records-table.tsx frontend/src/features/board/components/record-detail-sheet.tsx frontend/src/features/board/__tests__/records-table.test.tsx
git commit -m "feat(frontend): show board records as a table and a detail sheet"
````

---

### Task 17: The toolbar and the view-name dialog

**Files:**
- Create: `frontend/src/features/board/components/board-toolbar.tsx`, `frontend/src/features/board/components/view-dialogs.tsx`
- Test: `frontend/src/features/board/__tests__/board-toolbar.test.tsx`

**Interfaces:**
- Consumes: Task 12's library and types; Task 14's fixtures.
- Produces: `BoardToolbar({records, definition, onChange, text, onTextChange})`, `withInFilter(definition, property, values)`; `ViewNameDialog({open, title, initial, pending, onSubmit, onCancel})` (Contracts §Frontend).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

Each groupable property gets a `MultiSelect` that owns that property's `in` filter only, so a built-in's `not_in` filter on State survives. The text match is transient: it is never written into a definition.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/features/board/__tests__/board-toolbar.test.tsx` with:

````tsx
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import type { ViewDefinition } from "@/hooks/api"
import { BoardToolbar, withInFilter } from "../components/board-toolbar"
import { ViewNameDialog } from "../components/view-dialogs"
import { flattenRecords } from "../lib/records"
import { RECORDS } from "./fixtures"

const BUILTIN: ViewDefinition = {
  layout: "board",
  group_by: "state",
  filters: [
    { property: "type", operator: "in", values: ["register_row"] },
    { property: "state", operator: "not_in", values: ["done", "n/a"] },
  ],
  sort: null,
  columns: [],
  show_untracked: false,
}

describe("withInFilter", () => {
  it("replaces only the property's in filter and keeps its not_in", () => {
    const next = withInFilter(BUILTIN, "state", ["open"])
    expect(next.filters).toEqual([
      { property: "type", operator: "in", values: ["register_row"] },
      { property: "state", operator: "not_in", values: ["done", "n/a"] },
      { property: "state", operator: "in", values: ["open"] },
    ])
  })

  it("drops the in filter when nothing is selected", () => {
    expect(withInFilter(BUILTIN, "type", []).filters).toEqual([
      { property: "state", operator: "not_in", values: ["done", "n/a"] },
    ])
  })
})

describe("BoardToolbar", () => {
  it("switches layout, toggles untracked and reports the text match", async () => {
    const onChange = vi.fn()
    const onTextChange = vi.fn()
    const user = userEvent.setup()
    render(
      <BoardToolbar
        records={flattenRecords(RECORDS)}
        definition={BUILTIN}
        onChange={onChange}
        text=""
        onTextChange={onTextChange}
      />,
    )
    await user.click(screen.getByRole("radio", { name: "Table" }))
    expect(onChange).toHaveBeenLastCalledWith({ ...BUILTIN, layout: "table" })
    await user.click(screen.getByRole("switch"))
    expect(onChange).toHaveBeenLastCalledWith({
      ...BUILTIN,
      show_untracked: true,
    })
    await user.type(
      screen.getByRole("textbox", { name: "Search title and note" }),
      "b",
    )
    expect(onTextChange).toHaveBeenLastCalledWith("b")
  })
})

describe("ViewNameDialog", () => {
  it("submits a trimmed name and refuses a blank one", async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(
      <ViewNameDialog
        open
        title="Save as view"
        initial=""
        pending={false}
        onSubmit={onSubmit}
        onCancel={vi.fn()}
      />,
    )
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled()
    await user.type(screen.getByLabelText("Name"), "  Mine  ")
    await user.click(screen.getByRole("button", { name: "Save" }))
    expect(onSubmit).toHaveBeenCalledWith("Mine")
  })
})
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd frontend && npx vitest run src/features/board/__tests__/board-toolbar.test.tsx`
Expected: FAIL: cannot resolve `../components/board-toolbar`

- [ ] **Step 3: Write the toolbar and the dialog**

Create `frontend/src/features/board/components/board-toolbar.tsx` with:

````tsx
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { MultiSelect } from "darkraise-ui/components/multi-select"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { Switch } from "darkraise-ui/components/switch"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import type { GroupableProperty, ViewDefinition, ViewFilter } from "@/hooks/api"
import {
  GROUPABLE,
  PROPERTY_LABELS,
  propertyValue,
  shortName,
  type BoardRecord,
} from "../lib/records"

const NO_GROUP = "__none"

/** The `in` filter on `property`, replaced by `values` (removed when empty).
 *  Other filters on the property, such as a built-in's `not_in`, stay. */
export function withInFilter(
  definition: ViewDefinition,
  property: GroupableProperty,
  values: string[],
): ViewDefinition {
  const others = definition.filters.filter(
    (f) => !(f.property === property && f.operator === "in"),
  )
  const added: ViewFilter[] =
    values.length > 0 ? [{ property, operator: "in", values }] : []
  return { ...definition, filters: [...others, ...added] }
}

function optionLabel(property: GroupableProperty, value: string): string {
  return property === "source" || property === "plan" ? shortName(value) : value
}

/** Layout, grouping and filter controls over a view's draft definition. */
export function BoardToolbar({
  records,
  definition,
  onChange,
  text,
  onTextChange,
}: {
  records: BoardRecord[]
  definition: ViewDefinition
  onChange: (next: ViewDefinition) => void
  text: string
  onTextChange: (text: string) => void
}) {
  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <ToggleGroup
        type="single"
        value={definition.layout}
        onValueChange={(value) => {
          if (value)
            onChange({ ...definition, layout: value as "board" | "table" })
        }}
      >
        <ToggleGroupItem value="board" size="sm">
          Board
        </ToggleGroupItem>
        <ToggleGroupItem value="table" size="sm">
          Table
        </ToggleGroupItem>
      </ToggleGroup>
      <Select
        value={definition.group_by ?? NO_GROUP}
        onValueChange={(value) =>
          onChange({
            ...definition,
            group_by: value === NO_GROUP ? null : (value as GroupableProperty),
          })
        }
      >
        <SelectTrigger className="w-auto min-w-36" aria-label="Group by">
          <SelectValue>
            Group:{" "}
            {definition.group_by
              ? PROPERTY_LABELS[definition.group_by]
              : "none"}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={NO_GROUP}>none</SelectItem>
          {GROUPABLE.map((property) => (
            <SelectItem key={property} value={property}>
              {PROPERTY_LABELS[property]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {GROUPABLE.map((property) => {
        const values = [
          ...new Set(
            records
              .map((r) => propertyValue(r, property))
              .filter((v): v is string => Boolean(v)),
          ),
        ].sort()
        const selected =
          definition.filters.find(
            (f) => f.property === property && f.operator === "in",
          )?.values ?? []
        return (
          <MultiSelect
            key={property}
            className="w-44"
            placeholder={PROPERTY_LABELS[property]}
            items={values.map((value) => ({
              value,
              label: optionLabel(property, value),
            }))}
            value={selected}
            onValueChange={({ value }) =>
              onChange(withInFilter(definition, property, value))
            }
          />
        )
      })}
      <Input
        aria-label="Search title and note"
        placeholder="Search title and note"
        className="w-56"
        value={text}
        onChange={(event) => onTextChange(event.target.value)}
      />
      <div className="flex items-center gap-1.5">
        <Switch
          id="board-show-untracked"
          checked={definition.show_untracked}
          onCheckedChange={(checked) =>
            onChange({ ...definition, show_untracked: checked })
          }
        />
        <Label htmlFor="board-show-untracked">Show untracked</Label>
      </div>
    </div>
  )
}
````

Create `frontend/src/features/board/components/view-dialogs.tsx` with:

````tsx
import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"

function NameForm({
  title,
  initial,
  pending,
  onSubmit,
  onCancel,
}: {
  title: string
  initial: string
  pending: boolean
  onSubmit: (name: string) => void
  onCancel: () => void
}) {
  const [name, setName] = useState(initial)
  const trimmed = name.trim()
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        if (trimmed) onSubmit(trimmed)
      }}
    >
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
      </DialogHeader>
      <div className="space-y-1.5 py-3">
        <Label htmlFor="board-view-name">Name</Label>
        <Input
          id="board-view-name"
          value={name}
          maxLength={100}
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={!trimmed || pending}>
          Save
        </Button>
      </DialogFooter>
    </form>
  )
}

/** Names a new view or renames a saved one. */
export function ViewNameDialog({
  open,
  title,
  initial,
  pending,
  onSubmit,
  onCancel,
}: {
  open: boolean
  title: string
  initial: string
  pending: boolean
  onSubmit: (name: string) => void
  onCancel: () => void
}) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
      <DialogContent>
        {open ? (
          <NameForm
            title={title}
            initial={initial}
            pending={pending}
            onSubmit={onSubmit}
            onCancel={onCancel}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
````

- [ ] **Step 4: Run the tests and the typecheck**

Run: `cd frontend && npx vitest run src/features/board`
Expected: all pass

Run: `cd frontend && npm run typecheck`
Expected: no errors

- [ ] **Step 5: Commit**

````bash
git add frontend/src/features/board/components/board-toolbar.tsx frontend/src/features/board/components/view-dialogs.tsx frontend/src/features/board/__tests__/board-toolbar.test.tsx
git commit -m "feat(frontend): group and filter the board"
````

---

### Task 18: The board panel and saved views

**Files:**
- Create: `frontend/src/features/board/components/board-panel.tsx`
- Modify: `frontend/src/__tests__/no-restricted-imports-count.test.ts`
- Test: `frontend/src/features/board/__tests__/board-panel.test.tsx`

**Interfaces:**
- Consumes: Tasks 13-17 (hooks, editor, dialog, view, table, sheet, toolbar, name dialog).
- Produces: `BoardPanel({project, viewId, onViewChange, onOpenDocument, onShowInWorkLog})`, `DEFAULT_VIEW` (Contracts §Frontend).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

The panel keys its body on the view id, so switching views starts from that view's saved definition, never from the last view's draft. "Save as view" on a built-in pre-fills `<name> copy`: that is how a built-in is duplicated. Rename, Delete and Update view appear on saved views only; Update view only once the draft differs.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/features/board/__tests__/board-panel.test.tsx` with:

````tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

import { apiFetch } from "@/lib/api"
import { DEMO_BOARD_VIEWS } from "@/demo/board"
import type { BoardView } from "@/hooks/api"
import { BoardPanel, sourceNotes } from "../components/board-panel"
import { RECORDS } from "./fixtures"

const SAVED: BoardView = {
  ...DEMO_BOARD_VIEWS[0]!,
  id: "11111111-1111-4111-8111-111111111111",
  name: "Mine",
  builtin: false,
  position: 0,
}

function routeApi(views: BoardView[] = DEMO_BOARD_VIEWS, records = RECORDS) {
  vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
    if (path.startsWith("/board/records?")) return Promise.resolve(records)
    if (path.startsWith("/board/views?")) return Promise.resolve(views)
    if (path === "/board/views" && init?.method === "POST") {
      return Promise.resolve({
        ...SAVED,
        id: "22222222-2222-4222-8222-222222222222",
      })
    }
    return Promise.reject(new Error(`unrouted ${path}`))
  })
}

function renderPanel(props: Partial<Parameters<typeof BoardPanel>[0]> = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const onViewChange = vi.fn()
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
  render(
    <BoardPanel
      project="darkmem"
      viewId={undefined}
      onViewChange={onViewChange}
      onOpenDocument={vi.fn()}
      onShowInWorkLog={vi.fn()}
      {...props}
    />,
    { wrapper },
  )
  return { onViewChange }
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("BoardPanel", () => {
  it("opens on the open-register-items built-in: register rows by state, done hidden", async () => {
    routeApi()
    renderPanel()
    const lane = await screen.findByRole("region", { name: "Register rows" })
    expect(within(lane).getByText("Alpha")).toBeInTheDocument()
    expect(within(lane).getByText("Beta")).toBeInTheDocument()
    expect(screen.queryByRole("region", { name: "Plan tasks" })).toBeNull()
    expect(screen.queryByRole("button", { name: "Rename" })).toBeNull()
  })

  it("reports a view change through the tabs", async () => {
    routeApi()
    const user = userEvent.setup()
    const { onViewChange } = renderPanel()
    await user.click(
      await screen.findByRole("tab", { name: "Plans in flight" }),
    )
    expect(onViewChange).toHaveBeenCalledWith("builtin:plans-in-flight")
  })

  it("groups the plans-in-flight view by plan and hides untracked tasks", async () => {
    routeApi()
    renderPanel({ viewId: "builtin:plans-in-flight" })
    expect(
      await screen.findByRole("heading", { name: /^p\s*2$/ }),
    ).toBeInTheDocument()
    expect(screen.queryByText("Loose")).toBeNull()
  })

  it("duplicates a built-in by saving it as a new view", async () => {
    routeApi()
    const user = userEvent.setup()
    const { onViewChange } = renderPanel()
    await user.click(
      await screen.findByRole("button", { name: "Save as view" }),
    )
    const name = screen.getByLabelText("Name")
    expect(name).toHaveValue("Open register items copy")
    await user.click(screen.getByRole("button", { name: "Save" }))
    await waitFor(() =>
      expect(onViewChange).toHaveBeenCalledWith(
        "22222222-2222-4222-8222-222222222222",
      ),
    )
    const post = vi
      .mocked(apiFetch)
      .mock.calls.find(([path]) => path === "/board/views")!
    expect(JSON.parse(String(post[1]!.body))).toEqual({
      project: "darkmem",
      name: "Open register items copy",
      definition: DEMO_BOARD_VIEWS[0]!.definition,
    })
  })

  it("switches to the table layout", async () => {
    routeApi()
    const user = userEvent.setup()
    renderPanel()
    await user.click(await screen.findByRole("radio", { name: "Table" }))
    expect(screen.getByRole("table")).toBeInTheDocument()
  })

  it("offers rename, delete and update only on a saved view", async () => {
    routeApi([...DEMO_BOARD_VIEWS, SAVED])
    const user = userEvent.setup()
    renderPanel({ viewId: SAVED.id })
    expect(
      await screen.findByRole("button", { name: "Rename" }),
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Update view" })).toBeNull()
    await user.click(screen.getByRole("radio", { name: "Table" }))
    expect(
      screen.getByRole("button", { name: "Update view" }),
    ).toBeInTheDocument()
  })

  it("says so when the project has no registers or plans", async () => {
    routeApi(DEMO_BOARD_VIEWS, { project: "darkmem", registers: [], plans: [] })
    renderPanel()
    expect(await screen.findByText("No registers or plans")).toBeInTheDocument()
  })

  it("lists what each source says about itself", async () => {
    const plan = {
      ...RECORDS.plans[0]!,
      other_workstreams: 2,
      orphans: [9, 12],
    }
    const records = { ...RECORDS, plans: [plan, ...RECORDS.plans.slice(1)] }
    expect(sourceNotes(records)).toEqual([
      "superpowers/plans/p.md: 2 other workstreams name this plan",
      "superpowers/plans/p.md: the ledger names task 9, 12 with no heading in the plan",
    ])
    routeApi(DEMO_BOARD_VIEWS, records)
    renderPanel()
    const notes = await screen.findByRole("list", { name: "source notes" })
    expect(within(notes).getAllByRole("listitem")).toHaveLength(2)
  })
})
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd frontend && npx vitest run src/features/board/__tests__/board-panel.test.tsx`
Expected: FAIL: cannot resolve `../components/board-panel`

- [ ] **Step 3: Write the panel**

Create `frontend/src/features/board/components/board-panel.tsx` with:

````tsx
import { useMemo, useState } from "react"
import { ClipboardList } from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "darkraise-ui/components/alert-dialog"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import { Tabs, TabsList, TabsTrigger } from "darkraise-ui/components/tabs"
import { EmptyState } from "@/components/darkmem"
import {
  useBoardRecords,
  useBoardViews,
  useCreateBoardView,
  useDeleteBoardView,
  useUpdateBoardView,
  type BoardRecords,
  type BoardView as SavedView,
} from "@/hooks/api"
import {
  applyView,
  boardLanes,
  flattenRecords,
  type BoardRecord,
} from "../lib/records"
import { useRowEditor } from "../use-row-editor"
import { BoardToolbar } from "./board-toolbar"
import { BoardView } from "./board-view"
import { NoteDialog } from "./note-dialog"
import { RecordDetailSheet } from "./record-detail-sheet"
import { RecordsTable } from "./records-table"
import { ViewNameDialog } from "./view-dialogs"

export const DEFAULT_VIEW = "builtin:open-register-items"

type NameDialog = "save" | "rename" | null

/** What a source says about itself (§1.3, §1.4, §5): a parse error, a
 *  malformed row, other workstreams naming a plan, ledger tasks with no
 *  heading. The rest of the board renders regardless. */
export function sourceNotes(data: BoardRecords): string[] {
  const notes: string[] = []
  for (const r of data.registers) {
    if (r.error) notes.push(`${r.uri}: ${r.error}`)
    for (const m of r.malformed) {
      notes.push(`${r.uri}:${m.line}: malformed row (${m.reason})`)
    }
  }
  for (const p of data.plans) {
    if (p.error) notes.push(`${p.uri}: ${p.error}`)
    if (p.other_workstreams > 0) {
      notes.push(
        `${p.uri}: ${p.other_workstreams} other workstream${p.other_workstreams === 1 ? "" : "s"} name this plan`,
      )
    }
    if (p.orphans.length > 0) {
      notes.push(
        `${p.uri}: the ledger names task ${p.orphans.join(", ")} with no heading in the plan`,
      )
    }
  }
  return notes
}

function SourceNotes({ data }: { data: BoardRecords }) {
  const notes = sourceNotes(data)
  if (notes.length === 0) return null
  return (
    <ul
      aria-label="source notes"
      className="text-muted-foreground space-y-0.5 text-xs"
    >
      {notes.map((note) => (
        <li key={note}>{note}</li>
      ))}
    </ul>
  )
}

function PanelBody({
  project,
  view,
  views,
  data,
  onViewChange,
  onOpenDocument,
  onShowInWorkLog,
}: {
  project: string
  view: SavedView
  views: SavedView[]
  data: BoardRecords
  onViewChange: (id: string) => void
  onOpenDocument: (uri: string) => void
  onShowInWorkLog: (workstreamKey: string, task: number) => void
}) {
  const [definition, setDefinition] = useState(view.definition)
  const [text, setText] = useState("")
  const [openId, setOpenId] = useState<string | null>(null)
  const [naming, setNaming] = useState<NameDialog>(null)
  const [deleting, setDeleting] = useState(false)
  const editor = useRowEditor(project)
  const create = useCreateBoardView(project)
  const update = useUpdateBoardView(project)
  const remove = useDeleteBoardView(project)

  const records = useMemo(() => flattenRecords(data), [data])
  const shown = useMemo(
    () => applyView(records, definition, text),
    [records, definition, text],
  )
  const lanes = useMemo(
    () => boardLanes(shown, definition.group_by, definition.show_untracked),
    [shown, definition.group_by, definition.show_untracked],
  )
  const open: BoardRecord | null = records.find((r) => r.id === openId) ?? null
  const dirty = JSON.stringify(definition) !== JSON.stringify(view.definition)
  const fail = (error: Error) => toast.error(error.message)

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Tabs value={view.id} onValueChange={onViewChange}>
          <TabsList>
            {views.map((v) => (
              <TabsTrigger key={v.id} value={v.id}>
                {v.name}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <Button variant="outline" size="sm" onClick={() => setNaming("save")}>
          Save as view
        </Button>
        {!view.builtin && dirty ? (
          <Button
            size="sm"
            disabled={update.isPending}
            onClick={() =>
              update.mutate({ id: view.id, definition }, { onError: fail })
            }
          >
            Update view
          </Button>
        ) : null}
        {!view.builtin ? (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setNaming("rename")}
            >
              Rename
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setDeleting(true)}>
              Delete
            </Button>
          </>
        ) : null}
      </div>
      <BoardToolbar
        records={records}
        definition={definition}
        onChange={setDefinition}
        text={text}
        onTextChange={setText}
      />
      <SourceNotes data={data} />
      {shown.length === 0 ? (
        <EmptyState
          kind="filtered"
          scope="panel"
          title="No records match this view"
        />
      ) : definition.layout === "board" ? (
        <BoardView
          lanes={lanes}
          pendingId={editor.pendingId}
          onMove={editor.move}
          onOpen={(record) => setOpenId(record.id)}
        />
      ) : (
        <RecordsTable
          records={shown}
          definition={definition}
          onDefinitionChange={setDefinition}
          editor={editor}
          onOpen={(record) => setOpenId(record.id)}
        />
      )}
      <NoteDialog
        prompt={editor.prompt}
        onCancel={editor.cancelPrompt}
        onConfirm={editor.confirmPrompt}
      />
      <RecordDetailSheet
        record={open}
        onClose={() => setOpenId(null)}
        onOpenDocument={onOpenDocument}
        onShowInWorkLog={(key, task) => {
          setOpenId(null)
          onShowInWorkLog(key, task)
        }}
      />
      <ViewNameDialog
        open={naming !== null}
        title={naming === "rename" ? "Rename view" : "Save as view"}
        initial={
          naming === "rename"
            ? view.name
            : view.builtin
              ? `${view.name} copy`
              : ""
        }
        pending={create.isPending || update.isPending}
        onCancel={() => setNaming(null)}
        onSubmit={(name) => {
          if (naming === "rename") {
            update.mutate(
              { id: view.id, name },
              { onSuccess: () => setNaming(null), onError: fail },
            )
          } else {
            create.mutate(
              { name, definition },
              {
                onSuccess: (saved) => {
                  setNaming(null)
                  onViewChange(saved.id)
                },
                onError: fail,
              },
            )
          }
        }}
      />
      <AlertDialog open={deleting} onOpenChange={setDeleting}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete the view {view.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              Only the saved layout goes; no register or plan changes.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              data-variant="destructive"
              onClick={() =>
                remove.mutate(view.id, {
                  onSuccess: () => {
                    setDeleting(false)
                    onViewChange(DEFAULT_VIEW)
                  },
                  onError: fail,
                })
              }
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

/** The Progress tab's board (§3): views over register rows and plan tasks. */
export function BoardPanel({
  project,
  viewId,
  onViewChange,
  onOpenDocument,
  onShowInWorkLog,
}: {
  project: string
  viewId: string | undefined
  onViewChange: (id: string) => void
  onOpenDocument: (uri: string) => void
  onShowInWorkLog: (workstreamKey: string, task: number) => void
}) {
  const records = useBoardRecords(project)
  const views = useBoardViews(project)
  if (records.isError || views.isError) {
    return (
      <EmptyState
        kind="failed"
        scope="panel"
        title="Could not read the board"
        description={(records.error ?? views.error)?.message}
      />
    )
  }
  if (!records.data || !views.data) return <Skeleton className="h-48 w-full" />
  if (records.data.registers.length === 0 && records.data.plans.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={ClipboardList}
        scope="panel"
        title="No registers or plans"
        description="The board reads the registers and plans the dr-forge mirror files under superpowers/registers/ and superpowers/plans/."
      />
    )
  }
  const view =
    views.data.find((v) => v.id === viewId) ??
    views.data.find((v) => v.id === DEFAULT_VIEW) ??
    views.data[0]!
  return (
    <PanelBody
      // A new view starts from its own saved definition, not the last draft.
      key={view.id}
      project={project}
      view={view}
      views={views.data}
      data={records.data}
      onViewChange={onViewChange}
      onOpenDocument={onOpenDocument}
      onShowInWorkLog={onShowInWorkLog}
    />
  )
}
````

- [ ] **Step 4: Move the demo-import floor**

The panel's test reads `DEMO_BOARD_VIEWS`, one more warn-level `src/demo/*` import.

In `frontend/src/__tests__/no-restricted-imports-count.test.ts`, replace:

````ts
    // imports its fixtures for `initialData` in demo mode (the work-log shape).
    expect(countByRule(results, "no-restricted-imports")).toBe(113)
````

with:

````ts
    // imports its fixtures for `initialData` in demo mode (the work-log shape).
    // Re-measured when the board panel's test landed: 114 — it reads the
    // built-in views fixture.
    expect(countByRule(results, "no-restricted-imports")).toBe(114)
````

- [ ] **Step 5: Run the tests and the typecheck**

Run: `cd frontend && npx vitest run src/features/board src/__tests__/no-restricted-imports-count.test.ts`
Expected: all pass

Run: `cd frontend && npm run typecheck`
Expected: no errors

- [ ] **Step 6: Commit**

````bash
git add frontend/src/features/board/components/board-panel.tsx frontend/src/features/board/__tests__/board-panel.test.tsx frontend/src/__tests__/no-restricted-imports-count.test.ts
git commit -m "feat(frontend): switch, save and manage board views"
````

---

### Task 19: Work log badges and the paging task filter

**Files:**
- Modify: `frontend/src/hooks/api/use-worklog-api.ts` (new hook, invalidation list), `frontend/src/lib/query-keys.ts`
- Modify: `frontend/src/features/worklog/components/entry-timeline.tsx`
- Test: `frontend/src/features/worklog/__tests__/entry-timeline-task.test.tsx`

**Interfaces:**
- Consumes: the work-log entries route (`GET /api/v1/worklog/workstreams/{id}/entries`, `kind`, `after`, `limit` up to 500; unchanged).
- Produces: `useAllLedgerEntries(workstreamId, enabled)`, `LEDGER_PAGE`; `EntryTimeline`'s new `initialTask?: number` prop; `entryTask(entry)`; query key `worklogLedgerAll` (Contracts §Frontend).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

This folds in register row 1's owed Work log review (spec §3 Work log). While a task filter is set, the timeline reads the workstream's whole ledger, 500 entries per request until `next_after` is null, before filtering, so the filter never reflects only the loaded pages. No route changes. Do not run prettier over these two existing files: the frontend is not prettier-clean and it would reformat unrelated lines.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/features/worklog/__tests__/entry-timeline-task.test.tsx` with:

````tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import type { WorklogEntry, Workstream } from "@/hooks/api"
import { EntryTimeline } from "../components/entry-timeline"

const WORKSTREAM: Workstream = {
  id: "w1",
  project: "darkmem",
  key: "plan-a",
  title: "Plan A",
  client: "dr-forge",
  state: "closed",
  closed_at: "2026-10-13T00:00:00Z",
  retain: false,
  properties: {},
  last_entry_at: "2026-10-13T00:00:00Z",
  created_at: "2026-10-12T00:00:00Z",
  updated_at: "2026-10-13T00:00:00Z",
}

function ledger(
  seq: number,
  body: string,
  properties: Record<string, unknown>,
): WorklogEntry {
  return {
    id: `e${seq}`,
    workstream_id: "w1",
    seq,
    run_key: "claude-code:r1",
    kind: "ledger",
    body,
    properties,
    created_at: "2026-10-13T09:00:00Z",
  }
}

const FIRST_PAGE = [
  ledger(1, "Task 1: implementer (assigned)\n", { task: 1, state: "wip" }),
  ledger(2, "Task 2: implementer (assigned)\n", { task: 2, state: "wip" }),
]
const SECOND_PAGE = [
  ledger(501, "Task 2: complete (commits a..9abc1234def)\n", {
    task: 2,
    state: "done",
    commit: "9abc1234def",
  }),
  ledger(502, "Task 2.5: odd\n", { task: 2.5 }),
]

function routeApi() {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    const qs = new URLSearchParams(path.split("?")[1])
    if (qs.get("limit") === "500") {
      return Promise.resolve(
        qs.get("after") === "500"
          ? { items: SECOND_PAGE, next_after: null }
          : { items: FIRST_PAGE, next_after: 500 },
      )
    }
    return Promise.resolve({ items: FIRST_PAGE, next_after: 500 })
  })
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("EntryTimeline's task filter", () => {
  it("shows an entry's task, state and commit as badges", async () => {
    routeApi()
    render(<EntryTimeline workstream={WORKSTREAM} />, { wrapper })
    expect(
      await screen.findByText("Task 1: implementer (assigned)"),
    ).toBeInTheDocument()
    expect(screen.getAllByText("task 1").length).toBeGreaterThan(0)
    expect(screen.getAllByText("wip").length).toBeGreaterThan(0)
  })

  it("pages the whole ledger before filtering to the initial task", async () => {
    routeApi()
    render(<EntryTimeline workstream={WORKSTREAM} initialTask={2} />, {
      wrapper,
    })
    expect(
      await screen.findByText("Task 2: complete (commits a..9abc1234def)"),
    ).toBeInTheDocument()
    expect(
      screen.getByText("Task 2: implementer (assigned)"),
    ).toBeInTheDocument()
    expect(screen.queryByText("Task 1: implementer (assigned)")).toBeNull()
    expect(screen.queryByText("Task 2.5: odd")).toBeNull()
    expect(screen.getByText("9abc123")).toBeInTheDocument()
    const ledgerReads = vi
      .mocked(apiFetch)
      .mock.calls.map(([path]) => String(path))
      .filter((path) => path.includes("limit=500"))
    expect(ledgerReads).toEqual([
      "/worklog/workstreams/w1/entries?kind=ledger&limit=500",
      "/worklog/workstreams/w1/entries?kind=ledger&limit=500&after=500",
    ])
  })

  it("filters as the task box is typed and clears back to the paged timeline", async () => {
    routeApi()
    const user = userEvent.setup()
    render(<EntryTimeline workstream={WORKSTREAM} />, { wrapper })
    await screen.findByText("Task 1: implementer (assigned)")
    await user.type(screen.getByRole("textbox", { name: "task" }), "1")
    await waitFor(() =>
      expect(screen.queryByText("Task 2: implementer (assigned)")).toBeNull(),
    )
    expect(
      screen.getByText("Task 1: implementer (assigned)"),
    ).toBeInTheDocument()
    await user.clear(screen.getByRole("textbox", { name: "task" }))
    expect(
      await screen.findByText("Task 2: implementer (assigned)"),
    ).toBeInTheDocument()
  })
})
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd frontend && npx vitest run src/features/worklog/__tests__/entry-timeline-task.test.tsx`
Expected: FAIL: no `task 1` badge, and no textbox named `task`

- [ ] **Step 3: Add the full-ledger hook and its key**

In `frontend/src/hooks/api/use-worklog-api.ts`, replace:

````ts
/** What a new session would load for one workstream;
````

with:

````ts
/** Page size of the full ledger read; the route's own ceiling. */
export const LEDGER_PAGE = 500

/** Every `ledger` entry of one workstream, paged to the end in one read, so a
 *  task filter never reflects only the pages a timeline happened to load. */
export function useAllLedgerEntries(workstreamId: string, enabled: boolean) {
  return useQuery<WorklogEntry[]>({
    queryKey: ["worklogLedgerAll", workstreamId],
    queryFn: async () => {
      const all: WorklogEntry[] = []
      let after: number | null = null
      do {
        const qs = new URLSearchParams({ kind: "ledger", limit: String(LEDGER_PAGE) })
        if (after !== null) qs.set("after", String(after))
        const page: WorklogEntryPage = await apiFetch<WorklogEntryPage>(
          `/worklog/workstreams/${workstreamId}/entries?${qs}`,
        )
        all.push(...page.items)
        after = page.next_after
      } while (after !== null)
      return all
    },
    enabled: !DEMO && enabled,
    initialData: DEMO ? demoEntries(workstreamId, "ledger").items : undefined,
  })
}

/** What a new session would load for one workstream;
````

In `frontend/src/hooks/api/use-worklog-api.ts`, replace:

````ts
  for (const key of ["worklogWorkstreams", "worklogEntries", "worklogResume", "projects"]) {
````

with:

````ts
  for (const key of [
    "worklogWorkstreams",
    "worklogEntries",
    "worklogLedgerAll",
    "worklogResume",
    "projects",
  ]) {
````

In `frontend/src/lib/query-keys.ts`, replace:

````ts
  boardRecords: {
````

with:

````ts
  worklogLedgerAll: {
    kind: "global",
    reason:
      "Every ledger entry of one workstream, addressed by workstream id like worklogEntries",
  },
  boardRecords: {
````

- [ ] **Step 4: Add the badges and the filter to the timeline**

In `frontend/src/features/worklog/components/entry-timeline.tsx`, replace:

````tsx
import { Button } from "darkraise-ui/components/button"
````

with:

````tsx
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
````

In `frontend/src/features/worklog/components/entry-timeline.tsx`, replace:

````tsx
import {
  useWorklogEntries,
  type WorklogEntry,
````

with:

````tsx
import {
  useAllLedgerEntries,
  useWorklogEntries,
  type WorklogEntry,
````

In `frontend/src/features/worklog/components/entry-timeline.tsx`, replace:

````tsx
function KindBadge({ kind }: { kind: WorklogKind }) {
  return <Badge variant={KIND_VARIANT[kind]}>{kind}</Badge>
}
````

with:

````tsx
function KindBadge({ kind }: { kind: WorklogKind }) {
  return <Badge variant={KIND_VARIANT[kind]}>{kind}</Badge>
}

/** An entry's integer `task` property, as dr-forge's push sends it. */
export function entryTask(entry: WorklogEntry): number | null {
  const task = entry.properties.task
  return typeof task === "number" && Number.isInteger(task) ? task : null
}

/** The `task`, `state` and `commit` entry properties, when present. */
function PropertyBadges({ entry }: { entry: WorklogEntry }) {
  const task = entryTask(entry)
  const state = entry.properties.state
  const commit = entry.properties.commit
  return (
    <>
      {task !== null ? <Badge variant="outline">task {task}</Badge> : null}
      {typeof state === "string" ? (
        <Badge variant="secondary">{state}</Badge>
      ) : null}
      {typeof commit === "string" ? (
        <Badge variant="outline" className="font-mono">
          {commit.slice(0, 7)}
        </Badge>
      ) : null}
    </>
  )
}
````

In `frontend/src/features/worklog/components/entry-timeline.tsx`, replace:

````tsx
      <KindBadge kind={entry.kind} />
      <span className="text-muted-foreground w-12 shrink-0 font-mono text-xs">
````

with:

````tsx
      <KindBadge kind={entry.kind} />
      <PropertyBadges entry={entry} />
      <span className="text-muted-foreground w-12 shrink-0 font-mono text-xs">
````

In `frontend/src/features/worklog/components/entry-timeline.tsx`, replace:

````tsx
        <KindBadge kind={entry.kind} />
        <span className="text-muted-foreground font-mono text-xs">
````

with:

````tsx
        <KindBadge kind={entry.kind} />
        <PropertyBadges entry={entry} />
        <span className="text-muted-foreground font-mono text-xs">
````

In `frontend/src/features/worklog/components/entry-timeline.tsx`, replace:

````tsx
export function EntryTimeline({
  workstream,
  initialEntryId,
}: {
  workstream: Workstream
  initialEntryId?: string
}) {
  const [kind, setKind] = useState<KindFilter>("all")
  const [selectedId, setSelectedId] = useState<string | null>(
    initialEntryId ?? null,
  )
  const entries = useWorklogEntries(
    workstream.id,
    kind === "all" ? null : kind,
    workstream.state === "open",
  )
  const items = useMemo(
    () => entries.data?.pages.flatMap((page) => page.items) ?? [],
    [entries.data],
  )
````

with:

````tsx
export function EntryTimeline({
  workstream,
  initialEntryId,
  initialTask,
}: {
  workstream: Workstream
  initialEntryId?: string
  /** Opens filtered to one plan task, as the board's "Show in Work log" does. */
  initialTask?: number
}) {
  const [kind, setKind] = useState<KindFilter>("all")
  const [taskText, setTaskText] = useState(
    initialTask === undefined ? "" : String(initialTask),
  )
  const task = /^\d+$/.test(taskText.trim()) ? Number(taskText.trim()) : null
  const [selectedId, setSelectedId] = useState<string | null>(
    initialEntryId ?? null,
  )
  const entries = useWorklogEntries(
    workstream.id,
    kind === "all" ? null : kind,
    workstream.state === "open",
  )
  // A task filter reads the whole ledger first: filtering only the loaded
  // pages would show a task's early entries and silently miss its later ones.
  const ledger = useAllLedgerEntries(workstream.id, task !== null)
  const paged = useMemo(
    () => entries.data?.pages.flatMap((page) => page.items) ?? [],
    [entries.data],
  )
  const items = useMemo(
    () =>
      task === null
        ? paged
        : (ledger.data ?? []).filter((entry) => entryTask(entry) === task),
    [task, paged, ledger.data],
  )
````

In `frontend/src/features/worklog/components/entry-timeline.tsx`, replace:

````tsx
  let body
  if (entries.isError) {
````

with:

````tsx
  let body
  if (task !== null && ledger.isError) {
    body = (
      <EmptyState
        kind="failed"
        title="Could not read this workstream's ledger"
        description={ledger.error.message}
      />
    )
  } else if (task !== null && ledger.isPending) {
    body = (
      <div className="space-y-2">
        <p className="text-muted-foreground text-sm">Reading the whole ledger…</p>
        <Skeleton className="h-64 w-full" />
      </div>
    )
  } else if (task !== null && items.length === 0) {
    body = (
      <EmptyState kind="filtered" title={`No ledger entries for task ${task}`} />
    )
  } else if (entries.isError) {
````

In `frontend/src/features/worklog/components/entry-timeline.tsx`, replace:

````tsx
    <div className="space-y-3">
      <SegmentGroup
        value={kind}
        onValueChange={(next) => {
          if (next) {
            setKind(next as KindFilter)
            setSelectedId(null)
          }
        }}
        variant="default"
        aria-label="entry kind"
      >
        <SegmentGroupIndicator />
        <SegmentGroupItem value="all">All</SegmentGroupItem>
        <SegmentGroupItem value="checkpoint">Checkpoints</SegmentGroupItem>
        <SegmentGroupItem value="ledger">Ledger</SegmentGroupItem>
        <SegmentGroupItem value="note">Notes</SegmentGroupItem>
      </SegmentGroup>
      {body}
      {entries.hasNextPage ? (
````

with:

````tsx
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <SegmentGroup
          value={kind}
          onValueChange={(next) => {
            if (next) {
              setKind(next as KindFilter)
              setSelectedId(null)
            }
          }}
          variant="default"
          aria-label="entry kind"
        >
          <SegmentGroupIndicator />
          <SegmentGroupItem value="all">All</SegmentGroupItem>
          <SegmentGroupItem value="checkpoint">Checkpoints</SegmentGroupItem>
          <SegmentGroupItem value="ledger">Ledger</SegmentGroupItem>
          <SegmentGroupItem value="note">Notes</SegmentGroupItem>
        </SegmentGroup>
        <Input
          aria-label="task"
          placeholder="Task #"
          inputMode="numeric"
          className="w-24"
          value={taskText}
          onChange={(event) => {
            setTaskText(event.target.value)
            setSelectedId(null)
          }}
        />
      </div>
      {body}
      {task === null && entries.hasNextPage ? (
````

- [ ] **Step 5: Run the tests and the typecheck**

Run: `cd frontend && npx vitest run src/features/worklog src/hooks src/lib`
Expected: all pass

Run: `cd frontend && npm run typecheck`
Expected: no errors

- [ ] **Step 6: Commit**

````bash
git add frontend/src/hooks/api/use-worklog-api.ts frontend/src/lib/query-keys.ts frontend/src/features/worklog/components/entry-timeline.tsx frontend/src/features/worklog/__tests__/entry-timeline-task.test.tsx
git commit -m "feat(worklog): show entry properties and filter by task"
````

---

### Task 20: No edit mode for registers and plans

**Files:**
- Create: `frontend/src/lib/mirror-owned.ts`
- Modify: `frontend/src/features/documents/components/document-actions.tsx`, `frontend/src/features/documents/components/project-workspace.tsx` (the reader branch)
- Test: `frontend/src/features/documents/__tests__/document-actions.test.tsx`

**Interfaces:**
- Consumes: nothing (the prefixes mirror Task 1's `BOARD_SOURCE_PREFIXES`).
- Produces: `isMirrorOwned(uri)`, `MIRROR_OWNED_PREFIXES` (Contracts §Frontend).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 1 = 3

Spec §2.5 and §3 Artifacts: the server refuses block verbs on these uris (Task 4), so the SPA offers no Edit button, and the workspace renders the reader even if a stale `mode` says edit.

- [ ] **Step 1: Write the failing test**

In `frontend/src/features/documents/__tests__/document-actions.test.tsx` (the end of the file: the new case goes inside the `describe` block), replace:

````tsx
    // It spends an LLM call, so opening a document must not fire it.
    renderActions()
    expect(summarize).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole("button", { name: /summarize/i }))
    expect(summarize).toHaveBeenCalledTimes(1)
  })
})
````

with:

````tsx
    // It spends an LLM call, so opening a document must not fire it.
    renderActions()
    expect(summarize).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole("button", { name: /summarize/i }))
    expect(summarize).toHaveBeenCalledTimes(1)
  })

  it.each([
    "superpowers/registers/2026-09-23-work-log-lane.md",
    "superpowers/plans/2026-10-13-board.md",
  ])("offers no edit mode on a mirror-owned document (%s)", (uri) => {
    renderActions({ document: { ...DOC, uri } })
    expect(screen.queryByRole("button", { name: /^edit$/i })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument()
  })
})
````

- [ ] **Step 2: Run it to see it fail**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/document-actions.test.tsx`
Expected: 2 FAIL: an Edit button is present

- [ ] **Step 3: Write the helper and hide the mode**

Create `frontend/src/lib/mirror-owned.ts` with:

````ts
/** The uri prefixes of registers and plans, which the dr-forge mirror owns
 *  through content puts. The server refuses block edits on them, so the SPA
 *  offers no edit mode there (spec 2026-10-13 §2.5). */
export const MIRROR_OWNED_PREFIXES = [
  "superpowers/registers/",
  "superpowers/plans/",
]

export function isMirrorOwned(uri: string | null | undefined): boolean {
  return (
    Boolean(uri) &&
    MIRROR_OWNED_PREFIXES.some((prefix) => uri!.startsWith(prefix))
  )
}
````

In `frontend/src/features/documents/components/document-actions.tsx`, replace:

````tsx
    <div className="flex items-center gap-1">
      <IconButton
        icon={editing ? BookOpen : Pencil}
        label={editing ? "Read" : "Edit"}
        variant={editing ? "default" : "ghost"}
        aria-pressed={editing}
        onClick={() => onModeChange(editing ? "read" : "edit")}
      />
````

with:

````tsx
    <div className="flex items-center gap-1">
      {isMirrorOwned(document.uri) ? null : (
        <IconButton
          icon={editing ? BookOpen : Pencil}
          label={editing ? "Read" : "Edit"}
          variant={editing ? "default" : "ghost"}
          aria-pressed={editing}
          onClick={() => onModeChange(editing ? "read" : "edit")}
        />
      )}
````

In `frontend/src/features/documents/components/document-actions.tsx` (the last `@/` import), replace:

````tsx
import { plainText } from "@/lib/plain-text"
````

with:

````tsx
import { plainText } from "@/lib/plain-text"
import { isMirrorOwned } from "@/lib/mirror-owned"
````

In `frontend/src/features/documents/components/project-workspace.tsx`, replace:

````tsx
                      <Card className="p-4">
                        {mode === "read" ? (
````

with:

````tsx
                      <Card className="p-4">
                        {mode === "read" || isMirrorOwned(selected.uri) ? (
````

In `frontend/src/features/documents/components/project-workspace.tsx` (the last `@/` import), replace:

````tsx
import { plainText } from "@/lib/plain-text"
````

with:

````tsx
import { plainText } from "@/lib/plain-text"
import { isMirrorOwned } from "@/lib/mirror-owned"
````

- [ ] **Step 4: Run the tests and the typecheck**

Run: `cd frontend && npx vitest run src/features/documents`
Expected: all pass

Run: `cd frontend && npm run typecheck`
Expected: no errors

- [ ] **Step 5: Commit**

````bash
git add frontend/src/lib/mirror-owned.ts frontend/src/features/documents/components/document-actions.tsx frontend/src/features/documents/components/project-workspace.tsx frontend/src/features/documents/__tests__/document-actions.test.tsx
git commit -m "feat(frontend): hide edit mode for registers and plans"
````

---

### Task 21: Mount the board in the Progress tab and retire the old one

**Files:**
- Modify: `frontend/src/features/documents/components/project-workspace.tsx` (board region, work log focus, props)
- Modify: `frontend/src/routes/_authenticated/projects_.$project.tsx` (`?view=`)
- Modify: `frontend/src/features/worklog/components/work-log-panel.tsx` (`initialTask`)
- Delete: `frontend/src/features/progress/` (parsers, gates, startable filter, cards, detail and their tests)
- Test: `frontend/src/features/documents/__tests__/project-workspace.test.tsx`

**Interfaces:**
- Consumes: Task 18's `BoardPanel`; Task 19's `EntryTimeline` `initialTask`.
- Produces: `ProjectWorkspace` props `view?: string`, `onViewChange?: (view) => void`; `WorkLogPanel` prop `initialTask?: number`; route search param `view` (Contracts §Frontend).

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

The Progress tab keeps the 2026-09-28 layout: board on top, Work log beneath. The route already refuses the `personal` project, so it shows no board. "Show in Work log" remounts the Work log on the task's workstream with the task filter set, and scrolls it into view.

- [ ] **Step 1: Update the workspace tests first**

In `frontend/src/features/documents/__tests__/project-workspace.test.tsx`, replace:

````tsx
vi.mock("@/features/worklog/components/work-log-panel", () => ({
  WorkLogPanel: ({
    initialWorkstream,
    onOpenDocument,
  }: {
    initialWorkstream?: string
    onOpenDocument?: (uri: string) => void
  }) => (
    <div>
      work-log-panel:{initialWorkstream ?? "none"}
````

with:

````tsx
vi.mock("@/features/board/components/board-panel", () => ({
  BoardPanel: ({
    viewId,
    onViewChange,
    onShowInWorkLog,
  }: {
    viewId?: string
    onViewChange: (id: string) => void
    onShowInWorkLog: (key: string, task: number) => void
  }) => (
    <div>
      board-panel:{viewId ?? "default"}
      <button type="button" onClick={() => onViewChange("builtin:plans-in-flight")}>
        pick plans view
      </button>
      <button type="button" onClick={() => onShowInWorkLog("plan-key", 3)}>
        show task 3
      </button>
    </div>
  ),
}))
vi.mock("@/features/worklog/components/work-log-panel", () => ({
  WorkLogPanel: ({
    initialWorkstream,
    initialTask,
    onOpenDocument,
  }: {
    initialWorkstream?: string
    initialTask?: number
    onOpenDocument?: (uri: string) => void
  }) => (
    <div>
      work-log-panel:{initialWorkstream ?? "none"}
      {initialTask !== undefined ? `:task-${initialTask}` : ""}
````

In `frontend/src/features/documents/__tests__/project-workspace.test.tsx` (delete the progress-corpus fixture and its helper), replace:

````tsx
/** The ledger the progress corpus looks for. Its presence is what makes the
 *  corpus fetch document contents at all, so it is what lets a test tell an
 *  inert scan from a skipped one. */
const LEDGER = {
  id: "22222222-2222-2222-2222-222222222222",
  title: "progress",
  uri: "docs/planning/progress.md",
  source_type: "note",
  project: "darkmem",
  block_count: 1,
}

function contentReads() {
  return vi
    .mocked(apiFetch)
    .mock.calls.filter(([path]) =>
      String(path).includes("include_content=true"),
    )
}

````

with:

````tsx

````

In `frontend/src/features/documents/__tests__/project-workspace.test.tsx`, replace:

````tsx
  it("runs the progress corpus scan the Progress tab reads", async () => {
    mockDocuments({ items: [DOC, LEDGER] })
    renderWorkspace()
    await screen.findByText("design.md")

    expect(screen.getByRole("tab", { name: /progress/i })).toBeInTheDocument()
    // The corpus scan is the Progress tab's data layer.
    await waitFor(() => expect(contentReads().length).toBeGreaterThan(0))
  })
````

with:

````tsx
  it("hands the board its view and reports a view change", async () => {
    mockDocuments({ items: [DOC] })
    const onViewChange = vi.fn()
    renderWorkspace({ tab: "progress", view: "builtin:open-register-items", onViewChange })

    expect(
      await screen.findByText("board-panel:builtin:open-register-items"),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "pick plans view" }))
    expect(onViewChange).toHaveBeenCalledWith("builtin:plans-in-flight")
  })

  it("opens the Work log on a board task's workstream, filtered to it", async () => {
    mockDocuments({ items: [DOC] })
    renderWorkspace({ tab: "progress", workstream: "plan-a" })
    await screen.findByText("work-log-panel:plan-a")

    fireEvent.click(screen.getByRole("button", { name: "show task 3" }))
    expect(await screen.findByText("work-log-panel:plan-key:task-3")).toBeInTheDocument()
  })
````

- [ ] **Step 2: Run them to see them fail**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/project-workspace.test.tsx`
Expected: 2 FAIL: no `board-panel:` text

- [ ] **Step 3: Mount the board and wire the Work log focus**

In `frontend/src/features/documents/components/project-workspace.tsx`, replace:

````tsx
import { ProgressBoard } from "@/features/progress/components/progress-board"
import { useProgressCorpus } from "@/features/progress/use-progress-corpus"
````

with:

````tsx
import { BoardPanel } from "@/features/board/components/board-panel"
````

In `frontend/src/features/documents/components/project-workspace.tsx`, replace:

````tsx
export function ProjectWorkspace({
  project,
  workstream,
  emptyAction,
  ...tabs
}: {
  project: string
  workstream?: string
````

with:

````tsx
export function ProjectWorkspace({
  project,
  workstream,
  view,
  onViewChange,
  emptyAction,
  ...tabs
}: {
  project: string
  workstream?: string
  /** The board view the Progress tab shows (`?view=`). */
  view?: string
  onViewChange?: (view: string) => void
````

In `frontend/src/features/documents/components/project-workspace.tsx`, replace:

````tsx
  const corpus = useProgressCorpus(items)
````

with:

````tsx
  /** The workstream and task "Show in Work log" asked for; `n` remounts the
   *  panel when the same task is asked for twice. */
  const [logFocus, setLogFocus] = useState<{
    key: string
    task: number
    n: number
  } | null>(null)
  const workLogRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (logFocus) workLogRef.current?.scrollIntoView?.({ behavior: "smooth" })
  }, [logFocus])
````

In `frontend/src/features/documents/components/project-workspace.tsx`, replace:

````tsx
        <div>
          <RegionLabel>project board</RegionLabel>
          {/* A projection of the ledger and the epic files, never a second
              store: the board writes nothing, so `progress.md` stays the one
              place task state lives. That is what keeps it cheap, and it is
              also why the board fills only for a project whose corpus holds
              those files. */}
          {corpus.present ? (
            <ProgressBoard corpus={corpus} />
          ) : (
            <EmptyState
              kind="empty"
              icon={FolderTree}
              scope="panel"
              title="No progress ledger"
              description="The board is built from a progress.md ledger and epic files filed into this project. File them to see tasks here."
            />
          )}
        </div>
````

with:

````tsx
        <div>
          <RegionLabel>project board</RegionLabel>
          {/* A projection of registers, plans and ledger entries, never a
              second store: every card is derived on read, and the only write
              is a register row edit filed as a document revision. */}
          <BoardPanel
            project={project}
            viewId={view}
            onViewChange={(next) => onViewChange?.(next)}
            onOpenDocument={openDocumentByUri}
            onShowInWorkLog={(key, task) =>
              setLogFocus((prev) => ({ key, task, n: (prev?.n ?? 0) + 1 }))
            }
          />
        </div>
````

In `frontend/src/features/documents/components/project-workspace.tsx`, replace:

````tsx
        <div>
          <RegionLabel>work log</RegionLabel>
          <WorkLogPanel
            // Keyed on the requested workstream: the panel seeds its selection
            // from it once, so a link to another workstream must remount it.
            key={workstream ?? ""}
            project={project}
            initialWorkstream={workstream}
````

with:

````tsx
        <div ref={workLogRef}>
          <RegionLabel>work log</RegionLabel>
          <WorkLogPanel
            // Keyed on the requested workstream: the panel seeds its selection
            // from it once, so a link to another workstream must remount it.
            key={
              logFocus
                ? `${logFocus.key}:${logFocus.task}:${logFocus.n}`
                : (workstream ?? "")
            }
            project={project}
            initialWorkstream={logFocus?.key ?? workstream}
            initialTask={logFocus?.task}
````

- [ ] **Step 4: Carry the task into the Work log panel**

In `frontend/src/features/worklog/components/work-log-panel.tsx`, replace:

````tsx
export function WorkLogPanel({
  project,
  initialWorkstream,
  onOpenDocument,
}: {
  project: string
  initialWorkstream?: string
  onOpenDocument?: (uri: string) => void
}) {
````

with:

````tsx
export function WorkLogPanel({
  project,
  initialWorkstream,
  initialTask,
  onOpenDocument,
}: {
  project: string
  initialWorkstream?: string
  /** Filters the initial workstream's timeline to one plan task. */
  initialTask?: number
  onOpenDocument?: (uri: string) => void
}) {
````

In `frontend/src/features/worklog/components/work-log-panel.tsx`, replace:

````tsx
              key={`${selected.id}:${focusEntryId ?? ""}`}
              workstream={selected}
              initialEntryId={focusEntryId}
````

with:

````tsx
              key={`${selected.id}:${focusEntryId ?? ""}`}
              workstream={selected}
              initialEntryId={focusEntryId}
              initialTask={
                selected.key === initialWorkstream ? initialTask : undefined
              }
````

- [ ] **Step 5: Add `?view=` to the route**

In `frontend/src/routes/_authenticated/projects_.$project.tsx`, replace:

````tsx
  ): { tab?: WorkspaceTab; workstream?: string } => ({
````

with:

````tsx
  ): { tab?: WorkspaceTab; workstream?: string; view?: string } => ({
````

In `frontend/src/routes/_authenticated/projects_.$project.tsx`, replace:

````tsx
    workstream:
      typeof search.workstream === "string" && search.workstream
        ? search.workstream
        : undefined,
  }),
````

with:

````tsx
    workstream:
      typeof search.workstream === "string" && search.workstream
        ? search.workstream
        : undefined,
    view:
      typeof search.view === "string" && search.view ? search.view : undefined,
  }),
````

In `frontend/src/routes/_authenticated/projects_.$project.tsx`, replace:

````tsx
  const { tab, workstream } = useSearch({
````

with:

````tsx
  const { tab, workstream, view } = useSearch({
````

In `frontend/src/routes/_authenticated/projects_.$project.tsx`, replace:

````tsx
          workstream={workstream}
          tab={tab ?? "artifacts"}
````

with:

````tsx
          workstream={workstream}
          view={view}
          onViewChange={(next) =>
            navigate({ to: ".", search: (prev) => ({ ...prev, view: next }) })
          }
          tab={tab ?? "artifacts"}
````

- [ ] **Step 6: Delete the old board**

Run: `git rm -r -q frontend/src/features/progress && grep -rn 'features/progress' frontend/src || echo NO-REFERENCES`
Expected: `NO-REFERENCES`

- [ ] **Step 7: Run the whole frontend suite, the typecheck and the build**

Run: `cd frontend && npm test`
Expected: all pass (2202 tests on 2026-10-13; check `free -h` before believing an exit 143)

Run: `cd frontend && npm run typecheck`
Expected: no errors

Run: `cd frontend && npm run build`
Expected: `built in`, no type errors

- [ ] **Step 8: Commit**

`git rm` in Step 6 already staged the deletion.

````bash
git add frontend/src/features/documents/components/project-workspace.tsx 'frontend/src/routes/_authenticated/projects_.$project.tsx' frontend/src/features/worklog/components/work-log-panel.tsx frontend/src/features/documents/__tests__/project-workspace.test.tsx
git commit -m "feat(frontend): put the board in the Progress tab" -m "The T-epic board (planning/progress.md, planning/tasks/) is retired."
````

---

### Task 22: A real drag, end to end

**Files:**
- Modify: `backend/scripts/e2e/run_playwright_e2e.py` (argument pass-through)
- Test: `frontend/tests/project-progress-board.spec.ts` (replaced: the T-epic board's cases go with it)

**Interfaces:**
- Consumes: Tasks 8, 15, 18, 20 and 21 through the running app.
- Produces: `run_playwright_e2e.py [playwright args...]`.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3

Never run Playwright bare: `npx playwright test` points `/api` at production on `:8000`. The runner boots its own disposable stack on `:8322` (it resets `darkmem_test`, so nothing else may be using that database while it runs) and tears it down.

- [ ] **Step 1: Let the runner take one spec**

In `backend/scripts/e2e/run_playwright_e2e.py`, replace:

````python
        result = subprocess.run(
            ["npm", "run", "test:e2e"], cwd=str(FRONTEND_DIR), env=env,
        )
````

with:

````python
        # Arguments pass through to `playwright test`, so one spec runs
        # against this stack (`run_playwright_e2e.py tests/x.spec.ts
        # --project=chromium`); with none, the whole suite runs as before.
        result = subprocess.run(
            ["npm", "run", "test:e2e", "--", *sys.argv[1:]],
            cwd=str(FRONTEND_DIR), env=env,
        )
````

- [ ] **Step 2: Replace the spec**

Replace the whole of `frontend/tests/project-progress-board.spec.ts` with:

````ts
import { test, expect, type Page } from "@playwright/test"

/**
 * The progress board and the explorer tree, end to end.
 *
 * Happy-dom performs no layout and dnd-kit's pointer pipeline does not run
 * there, so dragging a card between state columns -- and the register file
 * changing because of it -- is only provable in a real browser. The spec files
 * its own register: the disposable stack starts empty.
 */

const PASSWORD = process.env.E2E_ADMIN_PASSWORD
const PROJECT = "board-e2e"
const URI = "superpowers/registers/e2e.md"

const REGISTER = `# Register — board fixture

**Covers:** docs/superpowers/specs/e2e.md

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | Drag me to planned | - | - | open | - |
| 2 | Stay where you are | - | - | doing | - |
`

async function signIn(page: Page) {
  await page.goto("/login")
  await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
  await page.getByRole("button", { name: /sign in/i }).click()
  await expect(page).toHaveURL("/")
}

/**
 * File the fixture register. The disposable stack has no embedder, so the
 * filing route may answer 500 after the filing committed (it embeds after the
 * commit); the status is not asserted, the document's presence is.
 */
async function fileRegister(page: Page): Promise<string> {
  await page.request.post("/api/v1/documents", {
    data: { project: PROJECT, uri: URI, content: REGISTER },
  })
  const listed = await page.request.get(
    `/api/v1/documents?project=${PROJECT}&limit=100`,
  )
  expect(listed.ok(), `listing: ${listed.status()}`).toBe(true)
  const body = await listed.json()
  const doc = body.items.find((d: { uri: string | null }) => d.uri === URI)
  expect(doc, `${URI} was not filed`).toBeTruthy()
  return doc.id as string
}

test.beforeAll(() => {
  if (!PASSWORD) {
    // Never soft-skip for a missing credential: a skip reads green while
    // asserting nothing.
    throw new Error("E2E_ADMIN_PASSWORD must be set")
  }
})

test.describe("project workspace", () => {
  let documentId = ""

  test.beforeEach(async ({ page }) => {
    await signIn(page)
    documentId = await fileRegister(page)
  })

  test("dragging a register card files the new state into the register", async ({
    page,
  }) => {
    await page.goto(`/projects/${PROJECT}?tab=progress`)

    const lane = page.getByRole("region", { name: "Register rows" })
    const open = lane.getByRole("region", { name: "column open" })
    const planned = lane.getByRole("region", { name: "column planned" })
    const card = open.getByRole("button", { name: /#1 Drag me to planned/ })
    await expect(card).toBeVisible()

    // Columns lay out side by side -- the assertion happy-dom cannot make.
    const openBox = await open.boundingBox()
    const plannedBox = await planned.boundingBox()
    expect(plannedBox!.x).toBeGreaterThan(openBox!.x)

    // dnd-kit's mouse sensor needs a 6px move before a drag starts.
    const from = await card.boundingBox()
    await page.mouse.move(from!.x + 20, from!.y + 10)
    await page.mouse.down()
    await page.mouse.move(from!.x + 40, from!.y + 30, { steps: 5 })
    await page.mouse.move(
      plannedBox!.x + plannedBox!.width / 2,
      plannedBox!.y + 60,
      {
        steps: 15,
      },
    )
    await page.mouse.up()

    await expect(
      planned.getByRole("button", { name: /#1 Drag me to planned/ }),
    ).toBeVisible()
    const read = await page.request.get(
      `/api/v1/documents/${documentId}?include_content=true`,
    )
    expect(read.ok()).toBe(true)
    expect((await read.json()).content).toContain(
      "| 1 | Drag me to planned | - | - | planned | - |",
    )
  })

  test("a row the drag did not touch stays in its column", async ({
    page,
  }) => {
    await page.goto(`/projects/${PROJECT}?tab=progress`)
    const doing = page
      .getByRole("region", { name: "Register rows" })
      .getByRole("region", { name: "column doing" })
    await expect(
      doing.getByRole("button", { name: /#2 Stay where you are/ }),
    ).toBeVisible()
  })

  test("the artifacts tree renders as a file explorer with real row heights", async ({
    page,
  }) => {
    await page.goto(`/projects/${PROJECT}?tab=artifacts`)

    // Only root folders start expanded, so `registers` is a collapsed folder
    // row until opened -- a test of the folder icon's two states.
    const folder = page.getByText("registers", { exact: true }).first()
    await expect(folder).toBeVisible()
    const folderBox = await folder.boundingBox()
    expect(folderBox!.height).toBeGreaterThan(12)

    const row = folder.locator("..")
    await expect(row.locator("svg.lucide-folder")).toBeVisible()
    await expect(row.locator("svg.lucide-folder-open")).toBeHidden()
    await folder.click()
    await expect(row.locator("svg.lucide-folder-open")).toBeVisible()

    const leaf = page.getByText("e2e.md", { exact: true }).first()
    await expect(leaf).toBeVisible()
    const leafBox = await leaf.boundingBox()
    expect(leafBox!.height).toBeGreaterThan(12)
    expect(leafBox!.x).toBeGreaterThan(folderBox!.x)
  })

  test("a register offers no edit mode", async ({ page }) => {
    await page.goto(`/projects/${PROJECT}?tab=artifacts`)
    await page.getByText("registers", { exact: true }).first().click()
    await page.getByText("e2e.md", { exact: true }).first().click()
    await expect(page.getByRole("button", { name: "Details" })).toBeVisible()
    await expect(page.getByRole("button", { name: /^edit$/i })).toHaveCount(0)
  })

  test("the header carries an icon-only back button to Projects", async ({
    page,
  }) => {
    await page.goto(`/projects/${PROJECT}`)
    const back = page.getByRole("link", { name: "Back to Projects" })
    await expect(back).toBeVisible()
    await expect(back).toHaveText("")
    await back.click()
    await expect(page).toHaveURL(/\/projects$/)
  })
})
````

- [ ] **Step 3: Run it through the runner**

If every test dies in 0 ms with `Executable doesn't exist ... chromium_headless_shell-1223`, install the revision first: `cd frontend && npx playwright install chromium-headless-shell chromium`.

Run: `cd backend && .venv/bin/python scripts/e2e/run_playwright_e2e.py tests/project-progress-board.spec.ts --project=chromium --retries=0`
Expected: `5 passed` (13.6 s on 2026-10-13)

- [ ] **Step 4: Confirm nothing is left running**

Run: `ss -ltnp | grep -E ':8322' || echo FREE`
Expected: `FREE`

- [ ] **Step 5: Commit**

````bash
git add backend/scripts/e2e/run_playwright_e2e.py frontend/tests/project-progress-board.spec.ts
git commit -m "test(e2e): drag a register card on the progress board"
````

---

### Task 23: Record the board in `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md` (Commands, Documents, a new Progress board section)

**Interfaces:**
- Consumes: Tasks 1-22.
- Produces: nothing code reads.

**Implementer:** dr-superpowers:impl-sonnet-low
**Evaluation:** files 0 - spec 0 - coupling 0 - risk 0 = 0

The spec itself was amended with the plan, and the superseded specs already carry their "Amended 2026-10-13" notes. No `CHANGELOG.md` section: the release cut writes one, and a push to master fails without it.

- [ ] **Step 1: Edit `CLAUDE.md`**

In `CLAUDE.md`, replace:

````markdown
  plus both SDK suites. Re-run Playwright standalone through
  `backend/scripts/e2e/run_playwright_e2e.py` before believing a red, and
````

with:

````markdown
  plus both SDK suites. Re-run Playwright standalone through
  `backend/scripts/e2e/run_playwright_e2e.py` before believing a red (its
  arguments pass through to `playwright test`, so `run_playwright_e2e.py
  tests/x.spec.ts --project=chromium` runs one spec), and
````

In `CLAUDE.md`, replace:

````markdown
  embed. Resolving the active fingerprint costs one real embed call per
  `unchanged` re-push, unconditionally.
````

with:

````markdown
  embed. Resolving the active fingerprint costs one real embed call per
  `unchanged` re-push, unconditionally.
- **`embed_inline=False`** (the board's register edit) returns once the
  filing commits and embeds nothing, so `llm` may be None and an embedder
  outage cannot fail the write; `block_embedding_refresh` embeds the new
  blocks within the hour.
````

In `CLAUDE.md`, replace:

````markdown
**Block verbs** (`app/services/block_verbs.py`): `block_update`,
`block_insert`, `block_move`, `block_delete`, on both doors for documents
and REST-only for pages (via a `BlockOwner` descriptor).
````

with:

````markdown
**Block verbs** (`app/services/block_verbs.py`): `block_update`,
`block_insert`, `block_move`, `block_delete`, on both doors for documents
and REST-only for pages (via a `BlockOwner` descriptor). They refuse
registers and plans (`superpowers/registers/`, `superpowers/plans/`) after
the row lock with `DocumentMirrorOwned`, a `DocumentNotConvertible` (REST
422, MCP `not_convertible`): the dr-forge mirror owns those documents
through content puts, and the SPA offers no edit mode for them.
````

In `CLAUDE.md`, replace:

````markdown
With no orchestrator, a read-only instance or a failed query embed the
keyword arm answers alone and the answer says `semantic_ran: false`.

## Cross-cutting invariants
````

with:

````markdown
With no orchestrator, a read-only instance or a failed query embed the
keyword arm answers alone and the answer says `semantic_ran: false`.

## Progress board (`app/services/board*.py`)

Spec `docs/superpowers/specs/2026-10-13-notion-progress-board-design.md`.
The Progress tab's board is a **projection, never a store**: every read
derives register rows (`superpowers/registers/*.md`) and plan tasks
(`superpowers/plans/*.md`) from `documents.content` and the ledger entries'
`task` / `state` / `commit` properties; a ledger without them reads as
untracked. `board_parse` holds the pure parsers, which mirror dr-forge's
`plan.sh` / `register.sh` (fences, escaped `\|` cells, `is_task`): change
both sides together. `board` reads and sits inside the work-log wall, so it
must never import `document_door` (its closure reaches a memory model).
`board_edit` is the one write: a register row edit spliced into the original
line, never re-serialised, and filed through `put_document` with the
caller's `expected_hash`, no `properties` and `embed_inline=False`, so a
racing writer gets 409 `hash_conflict` and no edit waits on an embedder.
Plan-task state is read-only (the ledger is the plugin's). Refusals are
`BoardRefusal`, answered with `error.code` = the reason. Six REST-only login
routes under `/api/v1/board` (`board.reads` / `board.write` on the parity
doc); `GET /records` serves a weak ETag with `Cache-Control: private,
no-cache` and answers 304 from two aggregates. Saved views are `board_views`
rows (revision `0003`); the two built-ins are code constants with `builtin:`
ids and refuse writes.

## Cross-cutting invariants
````

- [ ] **Step 2: Re-read the two prose counts by hand**

`CLAUDE.md` requires it: the parity doc's headline must read `92 surfaces: 31 two-door, 61 single-door with a stated reason (54 REST-only, 7 MCP-only), 0 divergent` (a test asserts it), and this file's MCP tool count (46) and job count (27) must be unchanged (no tool, no job was added).

Run: `grep -c '92 surfaces: 31 two-door, 61 single-door' docs/two-door-parity.md; grep -n '46 tools\|Twenty-seven' CLAUDE.md`
Expected: `1`, then both lines

- [ ] **Step 3: Commit**

````bash
git add CLAUDE.md
git commit -m "docs(claude): record the progress board's contract"
````

---

### Task 24: Deploy and the owner's review

**Files:**
- Modify: `docs/superpowers/registers/2026-09-23-work-log-lane.md` (rows 85 and 1, through the register script)

**Interfaces:**
- Consumes: the whole branch.
- Produces: the board running on this host.

**Items:** 85

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 0 - spec 0 - coupling 1 - risk 3 = 4

A production deploy from this branch before it merges, which runs `alembic upgrade head` at boot against this host's database. Deploying first is deliberate: the spec's increment 6 is the owner's review of the live board (`CLAUDE.md`: the owner reviews the live instance). It stamps production with `0003`, a revision master does not have yet, so **this branch must merge into master before any other deploy to this host**: a deploy of master without `0003` would refuse to start on the stamped revision. Say so in the report. On 2026-10-13 production ran an image from 2026-10-03 at revision `0001`, so this deploy also applies `0002` and ships everything merged since. Never push an image (`DARKMEM_PUSH=0`), never push the branch, and stop at the first red.

- [ ] **Step 1: Check the preconditions**

````bash
test -f .env && grep -q '^DB_PASSWORD=' .env && echo ENV-OK
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -Atc "SELECT version_num FROM alembic_version"
````

Expected: `ENV-OK`, then `0001` or `0002`. Then confirm master's migration head is still `0002`, so this branch's `0003` cannot collide with another lane's:

````bash
git ls-tree --name-only master backend/migrations/versions/ | grep -v __
````

Expected: `0001_baseline.py` and `0002_mcp_tool_calls.py` only. If master holds another `0003`, STOP and report BLOCKED: rebase this branch's revision onto it first (Task 9's note).

If `.env` is missing, STOP and report BLOCKED: on 2026-10-13 it was absent from this checkout (the nightly backup has failed since 2026-10-09 on `DB_PASSWORD`), and `docker compose up -d` fails the same way. Only the owner restores `.env`; never recreate a secret. Also run the check from `CLAUDE.md`'s "Prod may run an unmerged branch" note: compare production's stamped `schema_baseline_sha` with this branch's `0001_baseline.py` hash before deploying.

- [ ] **Step 2: Gate**

Run: `./scripts/gate.sh`
Expected: exit 0. Exit 2 is `GATE BLOCKED` (a missing toolchain), and exit 143 is the earlyoom kill, not a failure: check `free -h` and re-run the leg named.

- [ ] **Step 3: Build without pushing, take a backup, deploy**

````bash
DARKMEM_PUSH=0 ./scripts/build-push.sh
docker images darkraise/darkmem --format '{{.Tag}}' | grep -x "$(git rev-parse --short HEAD)"
./scripts/backup.sh /root/darkmem-backups
docker compose up -d
````

Expected: the build succeeds and the `grep` prints `HEAD`'s short sha (the script tags it; a failed build redeploys the old image and still says `Started`); a new dump in `/root/darkmem-backups`.

- [ ] **Step 4: Confirm the change is in the running image**

````bash
until [ "$(docker inspect -f '{{.State.Health.Status}}' darkmem-prod-darkmem-1)" = healthy ]; do sleep 5; done
curl -s http://127.0.0.1:8000/openapi.json | grep -o '/api/v1/board/[a-z{}_/]*' | sort -u
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -Atc "SELECT version_num FROM alembic_version" -c "SELECT count(*) FROM board_views"
docker exec darkmem-prod-darkmem-1 sh -c 'grep -rl "Show in Work log" /app/web | head -1'
````

Expected: the four board paths (`/records`, `/registers/{document_id}/rows/{number}`, `/views`, `/views/{view_id}`); `0003` and `0`; one built asset file path.

- [ ] **Step 5: Ask the owner to review**

Report to the owner, and wait: the board on the Progress tab of a project holding `superpowers/` registers and plans (none exist on this host's production yet, since the dr-forge mirror is not running; file one register through the Artifacts tab's New document at `superpowers/registers/<name>.md`, or point the mirror at this host), a drag between state columns, the Note dialog, the table's inline edits, saving and deleting a view, and the Work log's badges and task filter. The review closes register row 85 and register row 1's owed Work log review.

- [ ] **Step 6: Record the outcome**

After the owner approves (run this on the day of the review):

````bash
S=/root/.claude/plugins/cache/darkraise/dr-superpowers/1.34.1/scripts
F=docs/superpowers/registers/2026-09-23-work-log-lane.md
DATE=$(date +%F); SHA=$(git rev-parse --short HEAD)
NOTE1=$(. "$S/lib/register.sh"; register_rows "$F" | awk -F'	' '$1 == 1 {print $6}')
bash "$S/register" set "$F" 85 done --note "deployed $DATE (image $SHA); the owner reviewed the board on $DATE"
bash "$S/register" set "$F" 1 done --note "$NOTE1; the owner reviewed the Work log UI with the board on $DATE"
bash "$S/register" check "$F"
git add "$F" && git commit -m "docs(registers): close the progress board rows"
````

If the owner asks for changes, leave both rows as they are, record the requests as new register rows (`register add`), and report them.

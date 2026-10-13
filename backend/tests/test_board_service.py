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
        _ledger("Task 1: implementer dr-forge:impl-opus-medium (assigned; base 065871f)\n",
                task=1, state="wip"),
        _ledger("Task 1: fix round 1/5 (1 addressed, 0 open; commits 535856b..70d319b)\n",
                task=1, state="review", commit="70d319b"),
        _ledger("Task 1: minor (deferred): the reported RED run stashed an implementation\n",
                task=1),
        _ledger("Task 2: implementer dr-forge:impl-opus-low (assigned; base 70d319b)\n",
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
    first, second = board["registers"][0]["rows"]
    # The row still names its plan, so the card can say why it shows no progress.
    assert first["plan_uri"] == PLAN_URI and first["plan_progress"] is None
    assert second["plan_uri"] is None


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

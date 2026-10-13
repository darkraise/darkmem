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

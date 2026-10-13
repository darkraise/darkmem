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

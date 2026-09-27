"""The memory-door detector: each signal, both thresholds, the answer."""
from __future__ import annotations

import time

import pytest

from app.services import capture_lint

ONE_SIGNAL = [
    ("commit_ref", "The fix landed in e4363418 on master's tip."),
    ("commit_ref", "Compare a6937345..fd8d2865 for the change."),
    ("tally", "The suite reported 7708 passed."),
    ("tally", "Three shards, 3/4 finished."),
    ("tally", "The branch carries 76 commits."),
    ("tally", "Finished 5 of 12 tasks."),
    ("progress", "Task 5 complete."),
    ("progress", "Phase 2 has started."),
    ("progress", "Everything is all green."),
    ("vcs_event", "The fix was merged into master."),
    ("vcs_event", "The tag was pushed."),
    ("vcs_event", "The feature branch was deleted."),
    ("file_line", "The handler lives at backend/app/main.py:1005 now."),
    ("trace", "Traceback (most recent call last):\n  boom"),
    ("trace", "failed at com.example.Worker.run( with nothing"),
    ("trace", "RuntimeException: boom"),
    ("narration", "In this session the importer was rewritten."),
    ("narration", "Next steps: rewrite the importer."),
    ("narration", "TODO: rewrite the importer."),
]

NO_SIGNAL = [
    "Postgres must listen on all addresses because the API connects across the stack network.",
    "Row 3f2a1c9e-1b2c-4d5e-8f90-123456789abc is a UUID, not a commit.",
    "The value deadbeefcafe has no digit and 1234567 has no letter.",
    "The merge queue passed the check.",
    "The task runner completes jobs on time.",
    "An exception handler maps the error.",
    "A todo list app stores items.",
    "The handler lives in backend/app/main.py.",
]


@pytest.mark.parametrize("name,text", ONE_SIGNAL)
def test_each_signal_matches_alone_and_does_not_flag(name, text):
    found, warnings = capture_lint.lint(text)
    assert found == [name]
    assert warnings == []


@pytest.mark.parametrize("text", NO_SIGNAL)
def test_a_durable_fact_matches_nothing(text):
    assert capture_lint.lint(text) == ([], [])


def test_two_signals_flag():
    found, warnings = capture_lint.lint("Task 5 complete: 7708 passed.")
    assert found == ["tally", "progress"]
    assert capture_lint.is_flagged(found)
    assert warnings == [capture_lint.warning(found)]


def test_the_length_bound_is_exclusive_and_flags_alone():
    at_limit = "x" * capture_lint.LENGTH_LIMIT
    assert capture_lint.lint(at_limit) == ([], [])
    found, warnings = capture_lint.lint(at_limit + "x")
    assert found == ["length"]
    assert len(warnings) == 1


def test_the_constants_are_the_calibrated_ones():
    assert capture_lint.LENGTH_LIMIT == 1500
    assert capture_lint.MIN_SIGNALS == 2
    assert capture_lint.SIGNAL_NAMES == (
        "commit_ref", "tally", "progress", "vcs_event", "file_line", "trace", "narration", "length",
    )


def test_the_warning_names_the_signals_and_where_the_content_belongs():
    text = capture_lint.warning(["commit_ref", "vcs_event"])
    assert "commit_ref, vcs_event" in text
    assert "worklog_append" in text
    assert "document_put" in text


def test_a_long_run_of_word_characters_lints_in_linear_time():
    """file_line must not try every position inside a long unmatched run."""
    content = "a" * 200_000
    started = time.perf_counter()
    found, _warnings = capture_lint.lint(content)
    elapsed = time.perf_counter() - started
    assert "file_line" not in found
    assert elapsed < 1.0

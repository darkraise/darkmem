import json
import logging
from decimal import Decimal

import pytest

from benchlib import ledger


def test_record_and_read_roundtrip(tmp_path):
    path = tmp_path / "runs.jsonl"
    run = {
        "run_id": "run-1",
        "timestamp": "2026-07-26T00:00:00+00:00",
        "corpus_id": "smoke",
        "fingerprint": "fp-abc123",
        "git_sha": "deadbeef",
        "metrics": {"f1": 0.82, "precision": 0.9},
    }
    ledger.record(run, path)
    runs = ledger.read_runs(path)
    assert runs == [run]


def test_record_appends_multiple_lines_in_order(tmp_path):
    path = tmp_path / "runs.jsonl"
    ledger.record({"run_id": "run-1", "live_calls": 5}, path)
    ledger.record({"run_id": "run-2", "live_calls": 0}, path)
    runs = ledger.read_runs(path)
    assert len(runs) == 2
    assert runs[0]["run_id"] == "run-1"
    assert runs[1]["run_id"] == "run-2"


def test_record_never_rewrites_prior_lines(tmp_path):
    path = tmp_path / "runs.jsonl"
    for i in range(3):
        ledger.record({"run_id": f"run-{i}"}, path)
    original_bytes = path.read_bytes()

    ledger.record({"run_id": "run-3"}, path)
    new_bytes = path.read_bytes()

    assert new_bytes[: len(original_bytes)] == original_bytes
    assert len(new_bytes) > len(original_bytes)


def test_read_runs_on_missing_file_returns_empty_list(tmp_path):
    path = tmp_path / "does-not-exist.jsonl"
    assert ledger.read_runs(path) == []


def test_malformed_trailing_line_is_skipped_with_warning(tmp_path, caplog):
    path = tmp_path / "runs.jsonl"
    ledger.record({"run_id": "run-1"}, path)
    ledger.record({"run_id": "run-2"}, path)

    # Simulate a run that was killed mid-write: a truncated JSON fragment
    # with no trailing newline, appended directly (bypassing record()).
    with open(path, "a", encoding="utf-8") as fh:
        fh.write('{"run_id": "run-3", "metr')

    with caplog.at_level(logging.WARNING):
        runs = ledger.read_runs(path)

    assert [r["run_id"] for r in runs] == ["run-1", "run-2"]
    assert any("malformed" in rec.message.lower() for rec in caplog.records)


def test_default_path_lives_under_benchlib_runs():
    assert ledger.DEFAULT_PATH.parent.name == "runs"
    assert ledger.DEFAULT_PATH.parent.parent.name == "benchlib"
    assert ledger.DEFAULT_PATH.name.endswith(".jsonl")


def test_record_lines_are_valid_json_one_per_line(tmp_path):
    path = tmp_path / "runs.jsonl"
    ledger.record({"a": 1}, path)
    ledger.record({"b": 2}, path)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert [json.loads(line) for line in lines] == [{"a": 1}, {"b": 2}]


def test_a_split_multibyte_sequence_does_not_hide_the_good_records(tmp_path):
    """A kill during the buffered flush can cut a UTF-8 sequence in half.

    record() writes ensure_ascii=False, so non-ASCII reaches disk raw and
    this artifact is genuinely reachable. Build it byte-exactly: "é" is the
    two bytes 0xC3 0xA9, truncated here to its 0xC3 lead byte.
    """
    path = tmp_path / "runs.jsonl"
    ledger.record({"run_id": "run-1", "note": "café"}, path)
    ledger.record({"run_id": "run-2"}, path)

    with open(path, "ab") as fh:
        fh.write(b'{"run_id": "run-3", "note": "caf\xc3')

    with pytest.raises(UnicodeDecodeError):
        path.read_text(encoding="utf-8")

    runs = ledger.read_runs(path)
    assert [r["run_id"] for r in runs] == ["run-1", "run-2"]
    assert runs[0]["note"] == "café"


def test_a_split_multibyte_sequence_is_healed_by_the_next_append(tmp_path):
    path = tmp_path / "runs.jsonl"
    ledger.record({"run_id": "run-1", "note": "café"}, path)
    with open(path, "ab") as fh:
        fh.write(b'{"run_id": "run-2", "note": "caf\xc3')

    ledger.record({"run_id": "run-3"}, path)

    assert [r["run_id"] for r in ledger.read_runs(path)] == ["run-1", "run-3"]


def test_a_killed_partial_line_does_not_swallow_the_next_good_run(tmp_path):
    """The artifact: run N killed mid-write leaves a newline-less fragment,
    then run N+1 completes cleanly and calls record(). The healthy run must
    survive as its own readable line."""
    path = tmp_path / "runs.jsonl"
    ledger.record({"run_id": "run-1"}, path)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write('{"run_id": "run-2", "metr')

    fragment_bytes = path.read_bytes()
    ledger.record({"run_id": "run-3", "metrics": {"f1": 0.9}}, path)

    assert path.read_bytes()[: len(fragment_bytes)] == fragment_bytes
    runs = ledger.read_runs(path)
    assert [r["run_id"] for r in runs] == ["run-1", "run-3"]
    assert runs[-1]["metrics"] == {"f1": 0.9}


def test_a_non_json_native_value_raises_instead_of_being_coerced(tmp_path):
    """A Decimal is the idiomatic type once metrics come from Postgres
    numerics. Coercing it to "0.82" makes a later `new < baseline`
    comparison either raise or compare lexicographically; both are worse
    than failing at record time."""
    path = tmp_path / "runs.jsonl"
    ledger.record({"run_id": "run-1", "metrics": {"f1": 0.82}}, path)
    before = path.read_bytes()

    with pytest.raises(TypeError):
        ledger.record({"run_id": "run-2", "metrics": {"f1": Decimal("0.82")}}, path)

    assert path.read_bytes() == before
    assert [r["run_id"] for r in ledger.read_runs(path)] == ["run-1"]


def test_json_native_values_round_trip_with_their_types_intact(tmp_path):
    """read_runs must return what record was given, not lookalikes: an
    unknown key, a nested payload, a float, a bool, and a None all survive
    as themselves."""
    path = tmp_path / "runs.jsonl"
    run = {
        "run_id": "run-1",
        "an_unknown_future_key": {"nested": [1, 2.5, True, None]},
        "note": "café ☕",
        "live_calls": 0,
        "gate_config": {"ml_profile_ref": None, "relation_rescue": False},
    }
    ledger.record(run, path)

    (read_back,) = ledger.read_runs(path)
    assert read_back == run
    assert isinstance(read_back["an_unknown_future_key"]["nested"][1], float)
    assert read_back["gate_config"]["ml_profile_ref"] is None
    assert read_back["gate_config"]["relation_rescue"] is False

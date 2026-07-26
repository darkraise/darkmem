import json
import logging

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

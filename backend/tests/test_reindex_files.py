"""The caller's file list: what each entry means (spec §3.1, §6.2)."""
from __future__ import annotations

from pathlib import Path

from app.services.reindex_files import (
    canonicalise_paths,
    classify_union_files,
)


def _write(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_canonicalise_pins_the_discovery_spelling(tmp_path):
    """Every spelling of one on-disk file collapses to the one string phase_03
    looks up. `code_files` has no uniqueness on (repo_id, file_path), so a
    second spelling inserts a duplicate row rather than matching."""
    _write(tmp_path, "src/a.py", "x = 1\n")

    canonical, invalid = canonicalise_paths(
        tmp_path, ["src/a.py", "./src/a.py", "src/../src/a.py"]
    )

    assert canonical == ["src/a.py"]
    assert invalid == []


def test_canonicalise_refuses_paths_that_escape_the_tree(tmp_path):
    _write(tmp_path, "src/a.py", "x = 1\n")

    canonical, invalid = canonicalise_paths(
        tmp_path, ["src/a.py", "../outside.py", "/etc/passwd"]
    )

    assert canonical == ["src/a.py"]
    assert sorted(invalid) == ["../outside.py", "/etc/passwd"]


def test_canonicalise_keeps_a_valid_path_that_is_not_on_disk(tmp_path):
    """A clone's tree is stale, so a newly added file is absent from it. That
    is a soft skip decided later by the classifier, never a refusal here."""
    _write(tmp_path, "src/a.py", "x = 1\n")

    canonical, invalid = canonicalise_paths(tmp_path, ["src/added.py"])

    assert canonical == ["src/added.py"]
    assert invalid == []


def test_missing_file_lands_in_skipped_missing_not_unindexable(tmp_path):
    """The regression test for the branch order. `_file_hash` maps a missing
    file to None first, so a hash-first order reports it as unindexable and
    the never-delete guarantee loses its reporting."""
    buckets = classify_union_files(tmp_path, ["src/gone.py"], {})

    assert buckets.skipped_missing == ["src/gone.py"]
    assert buckets.skipped_unindexable == []
    assert buckets.accepted == []


def test_unchanged_file_is_dropped(tmp_path):
    import hashlib
    _write(tmp_path, "src/a.py", "x = 1\n")
    digest = hashlib.sha256("x = 1\n".encode()).hexdigest()

    buckets = classify_union_files(tmp_path, ["src/a.py"], {"src/a.py": digest})

    assert buckets.skipped_unchanged == ["src/a.py"]
    assert buckets.accepted == []


def test_changed_file_is_accepted(tmp_path):
    _write(tmp_path, "src/a.py", "x = 2\n")

    buckets = classify_union_files(tmp_path, ["src/a.py"], {"src/a.py": "stale"})

    assert buckets.accepted == ["src/a.py"]


def test_file_with_no_indexed_row_is_accepted(tmp_path):
    """Content the graph has never seen: NULL never compares equal."""
    _write(tmp_path, "src/new.py", "x = 3\n")

    buckets = classify_union_files(tmp_path, ["src/new.py"], {"src/new.py": None})

    assert buckets.accepted == ["src/new.py"]


def test_oversized_file_is_unindexable_not_missing(tmp_path):
    from app.services.code_pipeline import MAX_FILE_SIZE
    _write(tmp_path, "src/big.py", "#" * (MAX_FILE_SIZE + 1))

    buckets = classify_union_files(tmp_path, ["src/big.py"], {})

    assert buckets.skipped_unindexable == ["src/big.py"]
    assert buckets.skipped_missing == []
    assert buckets.accepted == []

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


def test_canonicalise_refuses_an_in_tree_symlink_pointing_outside(tmp_path):
    """Spec §6.2's deliberate asymmetry. `_list_all_files` follows symlinks,
    so the pipeline indexes this file; the door resolves the link and refuses
    it. Refusing something the pipeline would index is the safe direction --
    the door is the surface a caller names paths on."""
    outside = tmp_path.parent / f"outside-{tmp_path.name}.py"
    outside.write_text("secret = 1\n", encoding="utf-8")
    _write(tmp_path, "src/a.py", "x = 1\n")
    (tmp_path / "src" / "link.py").symlink_to(outside)

    canonical, invalid = canonicalise_paths(tmp_path, ["src/a.py", "src/link.py"])

    assert canonical == ["src/a.py"]
    assert invalid == ["src/link.py"]


def test_a_path_discovery_never_surfaces_is_unindexable(tmp_path):
    """Naming an ignored path genuinely indexed it, and `code_reconcile`'s
    next tick classified the resulting row as deleted (its own walk never
    surfaces the file) and stripped it -- so a repeated request paid for rows,
    symbols and embeddings every cycle. It is also what `skipped_unindexable`
    means: a file the system can never index."""
    _write(tmp_path, "node_modules/pkg/index.js", "module.exports = 1\n")
    _write(tmp_path, "src/build.lock", "locked\n")

    buckets = classify_union_files(
        tmp_path, ["node_modules/pkg/index.js", "src/build.lock"], {},
    )

    assert buckets.skipped_unindexable == [
        "node_modules/pkg/index.js", "src/build.lock",
    ]
    assert buckets.accepted == []
    assert buckets.skipped_missing == []


def test_the_ignored_rule_is_discovery_s_own(tmp_path):
    """Pinned against `_list_all_files` rather than against a copy of its
    constants: a rule restated here would drift the moment either list moves,
    and the oscillation above is exactly what a drift reopens."""
    from app.services.code_pipeline import _list_all_files

    _write(tmp_path, "node_modules/pkg/index.js", "module.exports = 1\n")
    _write(tmp_path, "src/build.lock", "locked\n")
    _write(tmp_path, "src/a.py", "x = 1\n")

    surfaced = set(_list_all_files(tmp_path))
    named = ["node_modules/pkg/index.js", "src/build.lock", "src/a.py"]
    buckets = classify_union_files(tmp_path, named, {})

    assert surfaced == {"src/a.py"}
    assert set(buckets.skipped_unindexable) == set(named) - surfaced

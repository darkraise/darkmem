# File-Scoped Reindex Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an agent that just committed tell darkmem to reindex named files of a repository right now, with an optional commit sha darkmem verifies first, instead of waiting for `repo_sync` or the 15-minute `code_reconcile` sweep.

**Architecture:** One new pure module (`reindex_files.py`) decides what a caller's file list means — canonicalising paths door-side and sorting them into four buckets pipeline-side. One new service module (`reindex_request.py`) is the single entry point both doors call: precheck, canonicalise, read-only HEAD verify, claim, spawn. `CodePipeline.run` gains a `union_files` parameter that is added to the git diff rather than replacing it (`forced_files` keeps its replace semantics untouched).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, asyncpg, pytest-asyncio, MCP SDK 2.1.1.

**Spec:** `docs/superpowers/specs/2026-08-28-file-scoped-reindex-design.md` — read it alongside this plan; every task argues from a numbered section of it.

## Global Constraints

- **Backend tests run from `backend/`**: `python -m pytest -q`. Needs the `darkmem_test` database on the dev-compose Postgres (127.0.0.1:5433). The merge gate is `./scripts/gate.sh` from the repo root.
- **Language is English only** — code, comments, docs, commits, tests.
- **Commit format**: `<type>(<scope>): <subject>`, subject ≤50 chars, imperative, no period. Types: feat|fix|docs|style|refactor|test|chore|perf.
- **Comments**: default to none. Add one only when the *why* is non-obvious — a hidden constraint, a subtle invariant, a surprise. Never explain *what* the code does. Never reference a task id.
- **No schema change.** This feature adds no column, no table, no migration. If you find yourself editing `0001_baseline.py`, stop — you have gone off-plan.
- **`forced_files` semantics must not change.** It replaces the diff; that is `code_reconcile`'s contract. `tests/test_code_reconcile.py` must stay green with no edit.
- **Taxonomy is closed.** `EVENT_TYPES` values land in the vocabulary *before* their emitter ships (Task 1 before Task 4).
- **Never `--no-verify`.** Never hardcode a value to make a test pass.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/app/services/reindex_files.py` | **Create.** Pure functions: what a caller's file list means. Canonicalisation (door-side) and four-bucket classification (pipeline-side). No DB, no git, no I/O beyond `stat`/`read`. |
| `backend/app/services/reindex_request.py` | **Create.** The one entry point both doors call: resolve → precheck → canonicalise → verify HEAD → claim → spawn. Owns the refusal vocabulary. |
| `backend/app/services/code_pipeline.py` | **Modify.** `run()` gains `union_files`; the short-circuit gains a clause; `phase_01_file_discovery` applies the filter and unions before the re-trace; an early exit after phase 01. |
| `backend/app/services/events.py` | **Modify.** One new `EVENT_TYPES` value. |
| `backend/app/api/routes/repos.py` | **Modify.** New REST door; `_spawn_repo_index` forwards `union_files`. |
| `backend/app/api/mcp/server.py` | **Modify.** New `code_reindex` tool. |
| `backend/app/api/mcp/scopes.py` | **Modify.** Third `ADMIN_TOOLS` set; three-way overlap guard. |
| `backend/app/schemas/code.py` | **Modify.** `ReindexFilesRequest` / `ReindexFilesResponse`. |
| `CLAUDE.md` | **Modify.** MCP roster 33 → 34; the "admin reaches no MCP tool" sentence becomes false. |

---

### Task 1: Land `repo_reindex_requested` in the events vocabulary

Taxonomy-first: the value exists before anything emits it (spec §7). This is the same pattern `block_embeddings_refreshed` followed at `events.py:141-143`.

**Files:**
- Modify: `backend/app/services/events.py` (the `EVENT_TYPES` list, near line 146)
- Test: `backend/tests/test_events_vocabulary.py` (create if absent; otherwise add to the existing events test module)

**Interfaces:**
- Consumes: nothing.
- Produces: the string literal `"repo_reindex_requested"` as a member of `app.services.events.EVENT_TYPES`.

- [ ] **Step 1: Write the failing test**

Create or append to `backend/tests/test_events_vocabulary.py`:

```python
from app.services.events import EVENT_TYPES


def test_repo_reindex_requested_is_in_the_vocabulary():
    """The file-scoped reindex doors journal under their own event type.

    `repo_indexed` belongs to the run itself and `repo_webhook_received` names
    a different door, so neither can carry this one's outcome.
    """
    assert "repo_reindex_requested" in EVENT_TYPES
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_events_vocabulary.py::test_repo_reindex_requested_is_in_the_vocabulary -q
```

Expected: FAIL — `AssertionError`.

- [ ] **Step 3: Add the value**

In `backend/app/services/events.py`, in the `EVENT_TYPES` list, directly after the `"repo_webhook_received"` entry and its comment block, add:

```python
    # The file-scoped reindex doors (REST + MCP), journalled once at the end of
    # the door with the outcome the door computed. Distinct from `repo_indexed`,
    # which is the run's own work, and from `repo_webhook_received`, which names
    # a different door. Landed ahead of its emitter, taxonomy-first.
    "repo_reindex_requested",
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_events_vocabulary.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/events.py backend/tests/test_events_vocabulary.py
git commit -m "feat(events): add repo_reindex_requested type"
```

---

### Task 2: The four-bucket file classifier and path canonicaliser

Spec §3.1 and §6.2. Both are pure functions over a working directory and a list of caller-supplied names — no DB, no git. Getting them right here is what makes Tasks 3-6 mechanical.

**The branch order is the whole point.** `code_reconcile._file_hash` returns `None` for a file that is missing *and* for one that is merely unindexable — `not path.is_file()` is the first thing it tests (`code_reconcile.py:61`). A hash-first branch order silently swallows every absent file. Test the missing case explicitly, not just "it was skipped".

**Files:**
- Create: `backend/app/services/reindex_files.py`
- Test: `backend/tests/test_reindex_files.py`

**Interfaces:**
- Consumes: `app.services.code_pipeline._list_all_files`, `app.services.code_reconcile._file_hash`.
- Produces:
  - `canonicalise_paths(work_dir: Path, names: Iterable[str]) -> tuple[list[str], list[str]]` returning `(canonical, invalid)`. `canonical` is deduplicated, order-preserving, in the discovery spelling. `invalid` is the caller's original spellings that escaped the tree.
  - `@dataclass(frozen=True) UnionBuckets` with fields `accepted: list[str]`, `skipped_unchanged: list[str]`, `skipped_missing: list[str]`, `skipped_unindexable: list[str]`.
  - `classify_union_files(work_dir: Path, names: Iterable[str], indexed_hashes: Mapping[str, str | None]) -> UnionBuckets`.
  - `MAX_UNION_FILES: int = 1000`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_reindex_files.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_reindex_files.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.reindex_files'`.

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/reindex_files.py`:

```python
"""What a caller's file list means (spec §3.1, §6.2).

Two pure decisions, kept together because they are two halves of one question
and neither touches the database or git:

- ``canonicalise_paths`` runs at the door. It pins every entry to the one
  spelling ``_list_all_files`` produces, because ``code_files`` has no
  uniqueness on ``(repo_id, file_path)`` and phase 03 looks its row up by exact
  string match -- a second spelling inserts a duplicate row and duplicate
  symbols for one on-disk file, and search returns both forever.
- ``classify_union_files`` runs inside the claimed pipeline run, after the
  pull, and sorts the canonical names into the four buckets the caller is
  answered with.

Import ``classify_union_files`` lazily from ``code_pipeline``: this module
imports ``code_reconcile``, which imports ``code_pipeline``, so a module-level
import there would close the cycle.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from app.services.code_reconcile import _file_hash

# Bounds the caller's list, not the repository walk canonicalisation performs.
MAX_UNION_FILES = 1000


@dataclass(frozen=True)
class UnionBuckets:
    """Every named file lands in exactly one bucket, and all four are reported.

    ``skipped_unindexable`` exists so a caller that names a file the system can
    never index hears about it; silence is the outcome this reporting is for.
    """

    accepted: list[str] = field(default_factory=list)
    skipped_unchanged: list[str] = field(default_factory=list)
    skipped_missing: list[str] = field(default_factory=list)
    skipped_unindexable: list[str] = field(default_factory=list)


def canonicalise_paths(
    work_dir: Path, names: Iterable[str],
) -> tuple[list[str], list[str]]:
    """Return ``(canonical, invalid)``.

    ``canonical`` is deduplicated and order-preserving, each entry spelled the
    way ``_list_all_files`` spells it. ``invalid`` carries the caller's own
    spellings for entries that resolve outside the working directory -- caller
    error, which hard-refuses the request rather than being skipped.

    A path inside the tree that is not on disk stays in ``canonical``: a clone's
    tree is stale, so the most ordinary push names a file it does not have yet,
    and refusing there would reject exactly the push this door exists to
    announce. The classifier soft-skips it.
    """
    root = work_dir.resolve()
    canonical: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()

    for raw in names:
        try:
            resolved = (root / raw).resolve()
            relative = resolved.relative_to(root)
        except (ValueError, OSError):
            invalid.append(raw)
            continue
        if not relative.parts:
            invalid.append(raw)
            continue
        spelled = relative.as_posix()
        if spelled not in seen:
            seen.add(spelled)
            canonical.append(spelled)

    return canonical, invalid


def classify_union_files(
    work_dir: Path,
    names: Iterable[str],
    indexed_hashes: Mapping[str, str | None],
) -> UnionBuckets:
    """Sort canonical names into the four buckets.

    Branch order is load-bearing. ``_file_hash`` returns ``None`` for a missing
    file *and* for an unindexable one -- ``not path.is_file()`` is the first
    thing it tests -- so the presence test must come first or every absent file
    is swallowed by the unindexable branch and the never-delete reporting never
    fires.
    """
    buckets = UnionBuckets()

    for name in names:
        path = work_dir / name
        if not path.is_file():
            buckets.skipped_missing.append(name)
            continue
        live = _file_hash(path)
        if live is None:
            buckets.skipped_unindexable.append(name)
            continue
        if live == indexed_hashes.get(name):
            buckets.skipped_unchanged.append(name)
            continue
        buckets.accepted.append(name)

    return buckets
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_reindex_files.py -q
```

Expected: PASS, 8 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/reindex_files.py backend/tests/test_reindex_files.py
git commit -m "feat(code): add union file classifier and canonicaliser"
```

---

### Task 3: Wire `union_files` into the pipeline

Spec §3.1, §3.4, §3.5. Three changes to `code_pipeline.py`, all invariant-bearing:

1. The short-circuit at line 175 gains `and not union_files`, or the design's headline case (uncommitted edit, HEAD unmoved) returns `up_to_date` after having answered 202.
2. The filter runs in `phase_01_file_discovery` and the `accepted` set unions in **before** `_find_dependent_caller_files`, so genuine changes get their callers re-traced and unchanged files never become phantom re-trace targets.
3. An early exit after phase 01 when the union path produced nothing, or a repeated unchanged list buys a repo-global Leiden pass per request.

**Files:**
- Modify: `backend/app/services/code_pipeline.py` (`run` signature and short-circuit ~143-200; `phase_01_file_discovery` ~448-536; the phase sequence in `run` ~218-230)
- Test: `backend/tests/test_code_pipeline_union.py`

**Interfaces:**
- Consumes: `reindex_files.classify_union_files`, `reindex_files.UnionBuckets` (Task 2).
- Produces:
  - `CodePipeline.run(..., union_files: list[str] | None = None)`.
  - `self._union_buckets: UnionBuckets | None` set by `phase_01_file_discovery`.
  - `run()`'s returned stats dict gains `union_accepted`, `union_skipped_unchanged`, `union_skipped_missing`, `union_skipped_unindexable` — each an `int` count — whenever `union_files` was passed.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_code_pipeline_union.py`:

```python
"""union_files: added to the diff, never replacing it (spec §3.1, §3.4)."""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from app.models.code import Repository
from app.services.code_pipeline import CodePipeline
from app.services.repo_manager import RepoManager


async def _make_indexed_repo(session, tmp_path) -> Repository:
    """A local_path repo with one committed, indexed file."""
    import subprocess

    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "a.py").write_text("def alpha():\n    return 1\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "init"],
        cwd=tmp_path, check=True,
    )

    repo = Repository(
        name=f"union-{uuid.uuid4().hex[:8]}",
        local_path=str(tmp_path),
        provider="local",
        status="ready",
    )
    session.add(repo)
    await session.commit()

    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    await pipeline.run(repo.id)
    await session.refresh(repo)
    return repo


async def _indexed_symbols(session, repo_id) -> set[str]:
    rows = (await session.execute(
        text("""
            SELECT cs.name FROM code_symbols cs
            JOIN code_files cf ON cs.file_id = cf.id
            WHERE cf.repo_id = :r
        """),
        {"r": str(repo_id)},
    )).scalars().all()
    return set(rows)


async def test_union_file_is_indexed_when_head_has_not_moved(session, tmp_path):
    """The headline case. An uncommitted edit leaves HEAD equal to
    last_indexed_commit, so without the short-circuit amendment the run returns
    up_to_date and the named file is never looked at."""
    repo = await _make_indexed_repo(session, tmp_path)
    (tmp_path / "src" / "a.py").write_text("def beta():\n    return 2\n")

    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    result = await pipeline.run(repo.id, union_files=["src/a.py"])

    assert result["status"] != "up_to_date"
    assert "beta" in await _indexed_symbols(session, repo.id)


async def test_unchanged_union_file_takes_the_early_exit(session, tmp_path):
    """Nothing changed, so the run must not buy a repo-global pass."""
    repo = await _make_indexed_repo(session, tmp_path)

    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    result = await pipeline.run(repo.id, union_files=["src/a.py"])

    assert result["status"] == "up_to_date"
    assert result["union_skipped_unchanged"] == 1
    await session.refresh(repo)
    assert repo.status == "ready"


async def test_missing_union_file_deletes_nothing(session, tmp_path):
    """Spec §3.3: this door never removes graph rows."""
    repo = await _make_indexed_repo(session, tmp_path)
    before = await _indexed_symbols(session, repo.id)

    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    result = await pipeline.run(repo.id, union_files=["src/never_existed.py"])

    assert result["union_skipped_missing"] == 1
    assert await _indexed_symbols(session, repo.id) == before


async def test_union_does_not_replace_the_diff(session, tmp_path):
    """diff ∪ named, never just named. b.py is committed and named nowhere."""
    import subprocess
    repo = await _make_indexed_repo(session, tmp_path)

    (tmp_path / "src" / "a.py").write_text("def alpha2():\n    return 1\n")
    (tmp_path / "src" / "b.py").write_text("def gamma():\n    return 3\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "two"],
        cwd=tmp_path, check=True,
    )

    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    await pipeline.run(repo.id, union_files=["src/a.py"])

    symbols = await _indexed_symbols(session, repo.id)
    assert "gamma" in symbols, "the diff's own file must still be indexed"
    assert "alpha2" in symbols


async def test_last_indexed_commit_advances_on_a_union_run(session, tmp_path):
    """Spec §3.5. The diff still ran, so the stamp is honest. If a union run
    ever skipped the diff, this advance would strand every unnamed changed
    file: the short-circuit would then report up_to_date forever."""
    import subprocess
    repo = await _make_indexed_repo(session, tmp_path)

    (tmp_path / "src" / "a.py").write_text("def delta():\n    return 4\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "second"],
        cwd=tmp_path, check=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    await pipeline.run(repo.id, union_files=["src/a.py"])

    await session.refresh(repo)
    assert repo.last_indexed_commit == head


async def test_a_variant_spelling_makes_no_second_code_file_row(
    session, tmp_path,
):
    """Spec §6.2. `code_files` has no uniqueness on (repo_id, file_path) and
    phase 03 looks its row up by exact string match, so an uncanonicalised
    spelling inserts a duplicate row and duplicate symbols for one file."""
    from app.services.reindex_files import canonicalise_paths

    repo = await _make_indexed_repo(session, tmp_path)
    (tmp_path / "src" / "a.py").write_text("def epsilon():\n    return 5\n")

    canonical, _ = canonicalise_paths(Path(tmp_path), ["./src/a.py"])
    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None,
        repo_manager=RepoManager(session),
    )
    await pipeline.run(repo.id, union_files=canonical)

    count = (await session.execute(
        text("""
            SELECT count(*) FROM code_files
            WHERE repo_id = CAST(:r AS uuid) AND file_path LIKE '%a.py'
        """),
        {"r": str(repo.id)},
    )).scalar_one()
    assert count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_code_pipeline_union.py -q
```

Expected: FAIL — `TypeError: run() got an unexpected keyword argument 'union_files'`.

- [ ] **Step 3a: Add the parameter and amend the short-circuit**

In `backend/app/services/code_pipeline.py`, change the `run` signature (line ~143) to add the parameter after `forced_files`:

```python
        forced_files: tuple[list[str], list[str]] | None = None,
        union_files: list[str] | None = None,
    ) -> dict:
```

Directly below the existing `forced_files` normalisation block (~line 157-163), add the same normalisation for the union:

```python
        # An empty list is "nothing named", not "a union was requested"; the
        # short-circuit clause below reads this as a falsy value.
        if union_files is not None and not union_files:
            union_files = None
        self._union_files = list(union_files) if union_files else []
        self._union_buckets = None
```

Change the short-circuit condition (line ~175) from:

```python
        if old_sha == new_sha and not full and forced_files is None:
```

to:

```python
        if old_sha == new_sha and not full and forced_files is None and not union_files:
```

In `__init__` (near the other per-run state, ~line 95-105), add:

```python
        self._union_files: list[str] = []
        self._union_buckets = None
```

- [ ] **Step 3b: Apply the filter and union in phase 01**

In `phase_01_file_discovery`, at the very end of the `else:` branch that handles `used_full is False` — that is, immediately **after** the `_find_dependent_caller_files` block and **before** the `for rel_path in self._deleted_files:` loop — the union must land *before* the re-trace, so instead insert it directly before the `targets = self._changed_files + self._deleted_files` line:

```python
                await self._apply_union_files()
                targets = self._changed_files + self._deleted_files
```

Also call it on the `used_full` branch, immediately after `self._deleted_files = await self._find_removed_files(all_files)`, so the buckets are still reported on a full pass:

```python
                await self._apply_union_files()
```

Add the helper method to the class, directly after `phase_01_file_discovery`. It reads `CodeFile.content_hash`, so it is `async`:

```python
    async def _apply_union_files(self) -> None:
        """Add the caller's changed files to this run's changed set.

        Only files whose content actually differs are added. An unchanged one
        would take phase 03's skip path yet still consume the re-trace cap and
        be re-embedded by phase 12, so filtering is what keeps a repeated list
        from manufacturing phantom index debt.
        """
        if not self._union_files:
            return

        from sqlalchemy import select

        from app.models.code import CodeFile
        from app.services.reindex_files import classify_union_files

        rows = (await self.session.execute(
            select(CodeFile.file_path, CodeFile.content_hash)
            .where(
                CodeFile.repo_id == self._repo.id,
                CodeFile.file_path.in_(self._union_files),
            )
        )).all()

        self._union_buckets = classify_union_files(
            self._work_dir, self._union_files, dict(rows),
        )
        already = set(self._changed_files) | set(self._deleted_files)
        self._changed_files.extend(
            f for f in self._union_buckets.accepted if f not in already
        )
```

- [ ] **Step 3c: Report the buckets and add the early exit**

In `run()`, immediately after `await self.phase_01_file_discovery(...)` and before `total = len(self._changed_files)`, add:

```python
            if self._union_buckets is not None:
                self._stats.update({
                    "union_accepted": len(self._union_buckets.accepted),
                    "union_skipped_unchanged": len(self._union_buckets.skipped_unchanged),
                    "union_skipped_missing": len(self._union_buckets.skipped_missing),
                    "union_skipped_unindexable": len(self._union_buckets.skipped_unindexable),
                })
                if not self._changed_files and not self._deleted_files:
                    # Every named file was filtered out and the diff was empty.
                    # Phases 09-11 are repo-global with no empty-set exit, so
                    # continuing would buy a Leiden pass for no content.
                    repo.status = "ready"
                    repo.status_message = None
                    await self.session.commit()
                    self._stats["status"] = "up_to_date"
                    return self._stats
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_code_pipeline_union.py -q
cd backend && python -m pytest tests/test_code_reconcile.py tests/test_index_debt.py tests/test_code_pipeline_integration.py -q
```

Expected: the new file PASSES; the three existing files PASS **with no edit** — `forced_files` semantics are unchanged.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/code_pipeline.py backend/tests/test_code_pipeline_union.py
git commit -m "feat(code): union caller files into the changed set"
```

---

### Task 4: The `reindex_request` service

Spec §1, §4, §5, §6.2, §6.3, §7. The one entry point both doors call. Precheck comes **before** canonicalisation, or a `cloning` repo fails inside an `rglob` instead of returning `409 repo_busy`.

**Files:**
- Create: `backend/app/services/reindex_request.py`
- Test: `backend/tests/test_reindex_request.py`

**Interfaces:**
- Consumes: `reindex_files.canonicalise_paths`, `reindex_files.MAX_UNION_FILES` (Task 2); `RepoManager.repo_working_dir`, `RepoManager.claim_for_indexing`, `RepoManager._run_git`; `events.record_event`; `EVENT_TYPES` value from Task 1.
- Produces:
  - `class ReindexRefused(Exception)` with attributes `status_code: int`, `reason: str`, `detail: dict`.
  - `async def prepare_reindex(session, repo, *, files, commit, actor, api_key_id, source) -> ReindexAccepted` — raises `ReindexRefused` on every refusal, journals `repo_reindex_requested` exactly once either way.
  - `@dataclass(frozen=True) ReindexAccepted` with `union_files: list[str]`, `commit: str | None`, `head: str`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_reindex_request.py`:

```python
"""The shared reindex entry point: refusals, ordering, journalling."""
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from app.models.code import Repository
from app.services.reindex_request import ReindexRefused, prepare_reindex


def _git_repo(tmp_path: Path) -> str:
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "a.py").write_text("x = 1\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "init"],
        cwd=tmp_path, check=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    ).stdout.strip()


async def _repo_row(session, tmp_path, status="ready") -> Repository:
    repo = Repository(
        name=f"rr-{uuid.uuid4().hex[:8]}",
        local_path=str(tmp_path),
        provider="local",
        status=status,
    )
    session.add(repo)
    await session.commit()
    return repo


async def _events(session, repo_id) -> list[dict]:
    rows = (await session.execute(
        text("""
            SELECT payload FROM events
            WHERE event_type = 'repo_reindex_requested'
              AND object_id = CAST(:r AS uuid)
        """),
        {"r": str(repo_id)},
    )).scalars().all()
    return list(rows)


async def test_matching_commit_is_accepted(session, tmp_path):
    head = _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    accepted = await prepare_reindex(
        session, repo, files=["src/a.py"], commit=head,
        actor="t", api_key_id=None, source="reindex_api",
    )

    assert accepted.union_files == ["src/a.py"]
    assert accepted.head == head


async def test_head_mismatch_refuses_with_both_shas(session, tmp_path):
    head = _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)
    wrong = "0" * 40

    with pytest.raises(ReindexRefused) as exc:
        await prepare_reindex(
            session, repo, files=["src/a.py"], commit=wrong,
            actor="t", api_key_id=None, source="reindex_api",
        )

    assert exc.value.status_code == 409
    assert exc.value.reason == "head_mismatch"
    assert exc.value.detail["actual"] == head
    assert exc.value.detail["expected"] == wrong


async def test_escaping_path_hard_refuses_the_request(session, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    with pytest.raises(ReindexRefused) as exc:
        await prepare_reindex(
            session, repo, files=["src/a.py", "../outside.py"], commit=None,
            actor="t", api_key_id=None, source="reindex_api",
        )

    assert exc.value.status_code == 400
    assert exc.value.reason == "invalid_files"


async def test_absent_path_is_soft_skipped_not_refused(session, tmp_path):
    """A clone's tree is stale; the most ordinary push names a file it lacks."""
    _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    accepted = await prepare_reindex(
        session, repo, files=["src/added.py"], commit=None,
        actor="t", api_key_id=None, source="reindex_api",
    )

    assert accepted.union_files == ["src/added.py"]


async def test_cloning_repo_refuses_at_the_precheck(session, tmp_path):
    """Before canonicalisation, which would otherwise fail inside an rglob."""
    _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path, status="cloning")

    with pytest.raises(ReindexRefused) as exc:
        await prepare_reindex(
            session, repo, files=["src/a.py"], commit=None,
            actor="t", api_key_id=None, source="reindex_api",
        )

    assert exc.value.status_code == 409
    assert exc.value.reason == "repo_busy"


async def test_over_cap_list_is_refused(session, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    with pytest.raises(ReindexRefused) as exc:
        await prepare_reindex(
            session, repo, files=[f"src/f{i}.py" for i in range(1001)],
            commit=None, actor="t", api_key_id=None, source="reindex_api",
        )

    assert exc.value.status_code == 400
    assert exc.value.reason == "too_many_files"


async def test_malformed_commit_is_refused_before_any_git_call(session, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    with pytest.raises(ReindexRefused) as exc:
        await prepare_reindex(
            session, repo, files=["src/a.py"], commit="not-a-sha; rm -rf /",
            actor="t", api_key_id=None, source="reindex_api",
        )

    assert exc.value.status_code == 400
    assert exc.value.reason == "malformed_commit"


async def test_a_refusal_is_journalled(session, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    with pytest.raises(ReindexRefused):
        await prepare_reindex(
            session, repo, files=["src/a.py"], commit="0" * 40,
            actor="agent", api_key_id=None, source="reindex_api",
        )

    payloads = await _events(session, repo.id)
    assert len(payloads) == 1
    assert payloads[0]["outcome"] == "head_mismatch"


async def test_the_door_makes_no_mutating_git_call(session, tmp_path):
    """Spec §4.1. `pull_repo` runs `reset --hard` on a clone and can re-clone
    the directory outright, so firing it from this unclaimed path would reset
    the tree under a concurrent run's parser."""
    head = _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)
    (tmp_path / "src" / "dirty.py").write_text("uncommitted = True\n")

    await prepare_reindex(
        session, repo, files=["src/a.py"], commit=head,
        actor="t", api_key_id=None, source="reindex_api",
    )

    assert (tmp_path / "src" / "dirty.py").exists(), (
        "the door reset or re-cloned the working tree"
    )
    still = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert still == head


async def test_acceptance_is_journalled(session, tmp_path):
    head = _git_repo(tmp_path)
    repo = await _repo_row(session, tmp_path)

    await prepare_reindex(
        session, repo, files=["src/a.py"], commit=head,
        actor="agent", api_key_id=None, source="reindex_api",
    )

    payloads = await _events(session, repo.id)
    assert len(payloads) == 1
    assert payloads[0]["outcome"] == "indexing"
    assert payloads[0]["file_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_reindex_request.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.reindex_request'`.

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/reindex_request.py`:

```python
"""The one entry point both file-scoped reindex doors call (spec §1).

Order is the design: precheck, then canonicalise, then verify HEAD, then claim.
Canonicalisation walks the working tree, which for a repository still cloning
may not exist and which a concurrent claimed run may be mid-rmtree on -- so the
status and existence checks come first, or the door fails inside an ``rglob``
instead of returning the honest ``repo_busy``.

The HEAD check is read-only on purpose. ``pull_repo`` runs ``reset --hard`` on a
clone and can re-clone the directory outright; firing it from this unclaimed
path would reset the tree under a concurrent run's parser. The spawned run does
its own pull under the claim, exactly as it does today. The guarantee this door
can honestly make is therefore "HEAD equalled your sha when the request was
accepted", and nothing stronger.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import Repository
from app.services.events import record_event
from app.services.reindex_files import MAX_UNION_FILES, canonicalise_paths
from app.services.repo_manager import RepoManager

logger = logging.getLogger(__name__)

_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")

BUSY_STATUSES = ("indexing", "cloning")


class ReindexRefused(Exception):
    """A refusal with the shape both doors render."""

    def __init__(self, status_code: int, reason: str, **detail):
        super().__init__(reason)
        self.status_code = status_code
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class ReindexAccepted:
    union_files: list[str]
    commit: str | None
    head: str


async def _journal(
    session: AsyncSession,
    repo_id: UUID | None,
    *,
    outcome: str,
    file_count: int,
    commit: str | None,
    actor: str | None,
    api_key_id: UUID | None,
    source: str,
) -> None:
    """One row per request, written last because it carries the outcome.

    The webhook journals before its lookup and can, because its payload is only
    ``{"keyed": ...}``. An outcome does not exist until the door has decided, so
    a pre-lookup row here could not carry one. Writing last records every
    computed refusal and loses only the unhandled-exception path.
    """
    await record_event(
        session,
        event_type="repo_reindex_requested",
        object_type="repository",
        object_id=repo_id,
        actor=actor,
        api_key_id=api_key_id,
        source=source,
        payload={"outcome": outcome, "file_count": file_count, "commit": commit},
    )


async def prepare_reindex(
    session: AsyncSession,
    repo: Repository,
    *,
    files: list[str] | None,
    commit: str | None,
    actor: str | None,
    api_key_id: UUID | None,
    source: str,
) -> ReindexAccepted:
    """Validate and verify, or raise ``ReindexRefused``. Journals either way."""
    files = files or []
    count = len(files)

    async def refuse(status_code: int, reason: str, **detail):
        await _journal(
            session, repo.id, outcome=reason, file_count=count,
            commit=commit, actor=actor, api_key_id=api_key_id, source=source,
        )
        await session.commit()
        raise ReindexRefused(status_code, reason, **detail)

    if count > MAX_UNION_FILES:
        await refuse(400, "too_many_files", limit=MAX_UNION_FILES, given=count)

    if commit is not None and not _SHA_RE.match(commit):
        await refuse(400, "malformed_commit")

    if repo.status in BUSY_STATUSES:
        await refuse(409, "repo_busy", status=repo.status)

    manager = RepoManager(session)
    try:
        work_dir = manager.repo_working_dir(repo)
    except ValueError as exc:
        await refuse(409, "repo_unavailable", error=str(exc))
    if not (work_dir / ".git").exists():
        await refuse(409, "repo_unavailable", error="working directory is not a git repository")

    try:
        canonical, invalid = canonicalise_paths(work_dir, files)
    except OSError as exc:
        await refuse(409, "tree_unreadable", error=str(exc))
    if invalid:
        await refuse(400, "invalid_files", paths=sorted(invalid)[:20])

    try:
        head = (await RepoManager._run_git(
            work_dir, ["git", "rev-parse", "HEAD"],
        )).strip()
    except Exception as exc:
        await refuse(409, "head_unreadable", error=str(exc)[:200])

    if commit is not None and head != commit:
        try:
            await RepoManager._run_git(
                work_dir, ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            )
        except Exception:
            await refuse(409, "unknown_commit", expected=commit, actual=head)
        await refuse(409, "head_mismatch", expected=commit, actual=head)

    await _journal(
        session, repo.id, outcome="indexing", file_count=count,
        commit=commit, actor=actor, api_key_id=api_key_id, source=source,
    )
    await session.commit()
    return ReindexAccepted(union_files=canonical, commit=commit, head=head)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_reindex_request.py -q
```

Expected: PASS, 10 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/reindex_request.py backend/tests/test_reindex_request.py
git commit -m "feat(code): add shared file-scoped reindex entry point"
```

---

### Task 5: The REST door

Spec §6, §6.1, §6.3. `require_scope("admin")` admits both a human session and an `admin` key, which is what makes the door reachable by the git hook that motivated it — `require_auth` decodes a login JWT only.

**Files:**
- Modify: `backend/app/schemas/code.py` (after `ReindexRequest`, line ~74)
- Modify: `backend/app/api/routes/repos.py` (`_spawn_repo_index` ~169-251; new route after `reindex_repo` ~289)
- Test: `backend/tests/test_reindex_route.py`

**Interfaces:**
- Consumes: `prepare_reindex`, `ReindexRefused`, `ReindexAccepted` (Task 4); `CodePipeline.run(union_files=...)` (Task 3).
- Produces: `POST /api/v1/repos/{repo_id}/reindex-files`; `_spawn_repo_index(..., union_files: list[str] | None = None)`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_reindex_route.py`:

```python
"""POST /repos/{id}/reindex-files (spec §6)."""
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from app.models.code import Repository


def _git_repo(tmp_path: Path) -> str:
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "a.py").write_text("x = 1\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "init"],
        cwd=tmp_path, check=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    ).stdout.strip()


async def _repo(session, tmp_path) -> Repository:
    repo = Repository(
        name=f"rt-{uuid.uuid4().hex[:8]}", local_path=str(tmp_path),
        provider="local", status="ready",
    )
    session.add(repo)
    await session.commit()
    return repo


async def test_accepts_and_returns_202(client, session, auth_headers, tmp_path):
    head = _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["src/a.py"], "commit": head},
        headers=auth_headers,
    )

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "indexing"
    assert body["accepted"] == 1


async def test_head_mismatch_is_409_with_both_shas(
    client, session, auth_headers, tmp_path,
):
    head = _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["src/a.py"], "commit": "0" * 40},
        headers=auth_headers,
    )

    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["reason"] == "head_mismatch"
    assert detail["actual"] == head


async def test_escaping_path_is_400(client, session, auth_headers, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["../outside.py"]},
        headers=auth_headers,
    )

    assert resp.status_code == 400
    assert resp.json()["detail"]["reason"] == "invalid_files"


async def test_unknown_repo_is_404(client, auth_headers):
    resp = await client.post(
        f"/api/v1/repos/{uuid.uuid4()}/reindex-files",
        json={"files": ["src/a.py"]},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_requires_credentials(client, session, tmp_path):
    _git_repo(tmp_path)
    repo = await _repo(session, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo.id}/reindex-files",
        json={"files": ["src/a.py"]},
    )
    assert resp.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_reindex_route.py -q
```

Expected: FAIL — 404 on every request; the route does not exist.

- [ ] **Step 3a: Add the schemas**

In `backend/app/schemas/code.py`, after `ReindexRequest` (line ~74):

```python
class ReindexFilesRequest(BaseModel):
    files: list[str] = []
    commit: str | None = None
    enrich_symbols: bool = False


class ReindexFilesResponse(BaseModel):
    status: str
    repo_id: str
    commit: str | None = None
    accepted: int
```

- [ ] **Step 3b: Forward `union_files` through the spawn helper**

In `backend/app/api/routes/repos.py`, add the parameter to `_spawn_repo_index`:

```python
    generate_wiki: bool = False,
    union_files: list[str] | None = None,
) -> asyncio.Task:
```

and inside `_run_index`, after the existing `generate_wiki` clause:

```python
                    if union_files:
                        run_kwargs["union_files"] = union_files
```

- [ ] **Step 3c: Add the route**

In `backend/app/api/routes/repos.py`, directly after `reindex_repo` (~line 289):

```python
@router.post("/{repo_id}/reindex-files", status_code=status.HTTP_202_ACCEPTED)
async def reindex_repo_files(
    repo_id: UUID,
    body: ReindexFilesRequest,
    principal=Depends(_require_repo_admin),
    pipeline: CodePipeline = Depends(get_code_pipeline),
    manager: RepoManager = Depends(get_repo_manager),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
):
    """File-scoped, commit-verified reindex (doc: 2026-08-28 design).

    ``reindex_repo``'s shape with two additions: the caller's file list is
    unioned into the diff rather than replacing it, and an optional sha is
    verified against HEAD before anything is claimed. The verification is
    read-only -- see ``reindex_request`` for why it must not pull here.
    """
    repo = await manager.get(repo_id)
    if not repo:
        async with session_factory() as journal_session:
            await record_event(
                journal_session,
                event_type="repo_reindex_requested",
                object_type="repository",
                object_id=repo_id,
                actor=principal.actor,
                api_key_id=principal.api_key_id,
                source="reindex_api",
                payload={"outcome": "not_found", "file_count": len(body.files)},
            )
            await journal_session.commit()
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        accepted = await prepare_reindex(
            manager.session, repo,
            files=body.files, commit=body.commit,
            actor=principal.actor, api_key_id=principal.api_key_id,
            source="reindex_api",
        )
    except ReindexRefused as refused:
        raise HTTPException(
            status_code=refused.status_code,
            detail={"reason": refused.reason, **refused.detail},
        )

    if not await manager.claim_for_indexing(repo_id, message="Queued for indexing..."):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason": "repo_busy"},
        )

    try:
        _spawn_repo_index(
            repo_id, pipeline, session_factory,
            kind="reindex-files",
            enrich_symbols=body.enrich_symbols,
            union_files=accepted.union_files,
        )
    except Exception as e:
        logger.error("Failed to schedule file reindex for %s: %s", repo_id, e)
        repo.status = "error"
        repo.status_message = "Failed to start indexing"
        await manager.session.commit()
        raise HTTPException(status_code=500, detail="Failed to start indexing")

    return ReindexFilesResponse(
        status="indexing", repo_id=str(repo_id),
        commit=accepted.head, accepted=len(accepted.union_files),
    )
```

Add the imports at the top of the module:

```python
from app.schemas.code import ReindexFilesRequest, ReindexFilesResponse
from app.services.reindex_request import ReindexRefused, prepare_reindex
```

(`record_event` is already imported by this module for the webhook.)

`async_session_factory` and `select` are already module-level imports in
`server.py` (from `app.database` and `sqlalchemy`); do not re-import them.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_reindex_route.py tests/test_repos.py -q
```

Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/code.py backend/app/api/routes/repos.py backend/tests/test_reindex_route.py
git commit -m "feat(api): add file-scoped reindex REST door"
```

---

### Task 6: The MCP door, the third scope set, and the docs

Spec §6, §6.1. `TOOL_SCOPES` stops being a two-set partition, which breaks arithmetic in `tests/test_mcp_auth.py:389` that must be rewritten rather than left to fail.

**Files:**
- Modify: `backend/app/api/mcp/scopes.py` (sets ~47-95; overlap guard ~85-90; docstring "33")
- Modify: `backend/app/api/mcp/server.py` (new tool, after `list_repos` ~840)
- Modify: `backend/tests/test_mcp_auth.py` (lines ~299-305, ~377-390)
- Modify: `CLAUDE.md` (MCP endpoint section)
- Test: `backend/tests/test_mcp_reindex.py`

**Interfaces:**
- Consumes: `prepare_reindex`, `ReindexRefused` (Task 4); `current_api_key_id`, `current_key_name` (already imported by `server.py`).
- Produces: MCP tool `code_reindex`; `ADMIN_TOOLS: frozenset[str]` in `scopes.py`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_mcp_reindex.py`:

```python
"""code_reindex: the first MCP write door into the code subsystem (spec §6.1)."""
from __future__ import annotations

from app.api.mcp.scopes import ADMIN_TOOLS, CAPTURE_TOOLS, READ_TOOLS, TOOL_SCOPES


def test_code_reindex_is_an_admin_tool():
    """Not capture: triggering an index spends embedder budget and can reset a
    clone's working tree, which is repository control, not memory writing."""
    assert "code_reindex" in ADMIN_TOOLS
    assert TOOL_SCOPES["code_reindex"] == "admin"
    assert "code_reindex" not in CAPTURE_TOOLS
    assert "code_reindex" not in READ_TOOLS


def test_the_three_sets_are_disjoint():
    assert not (CAPTURE_TOOLS & READ_TOOLS)
    assert not (CAPTURE_TOOLS & ADMIN_TOOLS)
    assert not (READ_TOOLS & ADMIN_TOOLS)


def test_every_declared_tool_is_classified():
    from tests.test_mcp import _declared_tool_names

    declared = _declared_tool_names()
    assert set(TOOL_SCOPES) == declared
    assert (
        len(CAPTURE_TOOLS) + len(READ_TOOLS) + len(ADMIN_TOOLS) == len(declared)
    )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_mcp_reindex.py -q
```

Expected: FAIL — `ImportError: cannot import name 'ADMIN_TOOLS'`.

- [ ] **Step 3a: Add the third set**

In `backend/app/api/mcp/scopes.py`, after the `READ_TOOLS` definition:

```python
ADMIN_TOOLS: frozenset[str] = frozenset({
    "code_reindex",
})
```

Replace the two-set overlap guard with a three-way one:

```python
_pairs = (
    ("capture", CAPTURE_TOOLS, "read", READ_TOOLS),
    ("capture", CAPTURE_TOOLS, "admin", ADMIN_TOOLS),
    ("read", READ_TOOLS, "admin", ADMIN_TOOLS),
)
for _a_name, _a, _b_name, _b in _pairs:
    _overlap = _a & _b
    if _overlap:
        raise RuntimeError(
            f"{sorted(_overlap)} is declared both {_a_name} and {_b_name}; "
            "a tool has exactly one scope"
        )
```

Extend `TOOL_SCOPES`:

```python
TOOL_SCOPES: dict[str, str] = {
    **{name: "capture" for name in CAPTURE_TOOLS},
    **{name: "read" for name in READ_TOOLS},
    **{name: "admin" for name in ADMIN_TOOLS},
}
```

In the module docstring, change every "33" to "34" and change "names all 33 rather than deriving" to "names all 34 rather than deriving".

- [ ] **Step 3b: Fix the existing auth tests**

In `backend/tests/test_mcp_auth.py`, add `ADMIN_TOOLS` to the import from `app.api.mcp.scopes`. Then replace line ~389:

```python
    assert len(CAPTURE_TOOLS) + len(READ_TOOLS) == len(declared)
```

with:

```python
    assert len(CAPTURE_TOOLS) + len(READ_TOOLS) + len(ADMIN_TOOLS) == len(declared)
```

Add a symmetric staleness clause beside the existing two (~line 380):

```python
    orphaned = ADMIN_TOOLS - declared
    assert not orphaned, f"ADMIN_TOOLS names tools that do not exist: {sorted(orphaned)}"
```

Replace `assert not (CAPTURE_TOOLS & READ_TOOLS)` with the three pairwise assertions.

Rename `test_an_admin_only_key_reaches_neither_partition` (~line 299) to `test_an_admin_only_key_reaches_only_admin_tools` and change its premise: it must assert that an `admin`-only key is refused `memory_stats` and `memory_add` **and admitted to `code_reindex`**.

- [ ] **Step 3c: Add the tool**

In `backend/app/api/mcp/server.py`, after `list_repos`:

```python
@mcp.tool(
    description=(
        "Request an immediate reindex of named files in a repository, "
        "optionally verifying an expected commit sha first. Address the "
        "repository by its working-directory path or its name."
    )
)
async def code_reindex(
    repo_path: str | None = None,
    repo_name: str | None = None,
    files: list[str] | None = None,
    commit: str | None = None,
) -> str:
    """
    Args:
        repo_path: Working directory of the repository (matched against local_path).
        repo_name: Repository name, if the path is not known.
        files: Repository-relative paths the caller changed.
        commit: Expected HEAD sha; the call is refused if darkmem is elsewhere.
    """
    from pathlib import Path

    from app.models.code import Repository
    from app.services.reindex_request import ReindexRefused, prepare_reindex

    if not repo_path and not repo_name:
        raise ValueError("one of repo_path or repo_name is required")

    async with _code_service_context() as session:
        if repo_path:
            resolved = str(Path(repo_path).expanduser().resolve())
            rows = (await session.execute(
                select(Repository).where(Repository.local_path == resolved)
            )).scalars().all()
        else:
            rows = (await session.execute(
                select(Repository).where(Repository.name == repo_name)
            )).scalars().all()

        if not rows:
            raise ValueError(f"Repository not found: {repo_path or repo_name}")
        if len(rows) > 1:
            # `name` and `local_path` carry no uniqueness, so this is reachable;
            # a scalar_one_or_none here would raise MultipleResultsFound at the
            # caller instead of naming the candidates.
            raise ValueError(
                "Repository reference is ambiguous; pass one of these ids: "
                + ", ".join(str(r.id) for r in rows)
            )
        repo = rows[0]

        try:
            accepted = await prepare_reindex(
                session, repo, files=files, commit=commit,
                actor=current_key_name(), api_key_id=current_api_key_id(),
                source="reindex_mcp",
            )
        except ReindexRefused as refused:
            return json.dumps({
                "status": "refused",
                "reason": refused.reason,
                **refused.detail,
            })

    from app.api.routes.repos import _spawn_repo_index
    from app.services.repo_manager import RepoManager

    async with async_session_factory() as claim_session:
        if not await RepoManager(claim_session).claim_for_indexing(
            repo.id, message="Queued for indexing...",
        ):
            return json.dumps({"status": "refused", "reason": "repo_busy"})

    _spawn_repo_index(
        repo.id, _pipeline, async_session_factory,
        kind="reindex-files",
        union_files=accepted.union_files,
    )
    return json.dumps({
        "status": "indexing",
        "repo_id": str(repo.id),
        "commit": accepted.head,
        "accepted": len(accepted.union_files),
    })
```

- [ ] **Step 3d: Update CLAUDE.md**

In the **MCP endpoint** section:
- Change `the full 33-tool catalogue` to `the full 34-tool catalogue`.
- Change `covers the other 25` to `covers 25`.
- Replace the sentence `Scopes do not imply one another — a key holding only `admin` reaches no MCP tool at all, since no tool accepts that scope.` with:

```
Scopes do not imply one another. `admin` reaches exactly one tool,
`code_reindex` — repository control, not memory writing — so a key holding
only `admin` reaches nothing else, and a `capture` key cannot trigger an
index.
```

- Change `Authorization is per tool, not per door: `capture` covers the 8 writers` to note the third set: `... and `admin` covers the 1 repository-control tool`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_mcp_reindex.py tests/test_mcp_auth.py tests/test_mcp.py tests/test_mcp_surface_parity.py -q
```

Expected: all PASS.

- [ ] **Step 5: Run the full backend suite and the gate**

```bash
cd backend && python -m pytest -q
cd /root/repositories/darkmem && ./scripts/gate.sh
```

Expected: green. `GATE BLOCKED` (exit 2) means a missing toolchain, not a red gate.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/mcp/ backend/tests/test_mcp_reindex.py backend/tests/test_mcp_auth.py CLAUDE.md
git commit -m "feat(mcp): add admin-scoped code_reindex tool"
```

---

## After the plan

Per CLAUDE.md's standing rule, this feature alters the running artifact (`backend/`), so it is not finished at a green gate:

```bash
./scripts/gate.sh
DARKMEM_PUSH=0 ./scripts/build-push.sh     # the DARKMEM_PUSH=0 is not optional
docker compose up -d
# wait for healthy, then confirm the change is in the running image:
curl -s localhost:8000/openapi.json | grep -c reindex-files
```

Never publish an image from this machine; `.github/workflows/release.yml` is the only path to a registry.

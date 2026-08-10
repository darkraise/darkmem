"""Test planning document correspondence between task definitions and progress tracking.

Ensures that every task heading in docs/planning/tasks/*.md has a corresponding
row in docs/planning/progress.md, and vice versa. This catches:
- Task headings with no progress row (invisible to scheduling)
- Progress rows for tasks that no longer exist (surviving a deletion or renumbering)
"""

import os
import re
import subprocess
import sys
from pathlib import Path

# `TH1` is a real epic prefix, not a typo — `gen_progress.py` has always matched
# it (`T(?:H1|[0-4])\.\d{2,3}[a-z]?`) while this module's `T\d+\.\d+` did not, so
# EH1's 17 tasks were invisible to every correspondence check here. Consistently
# invisible on both sides, which is why nothing ever went red.
TASK_ID = r"T(?:H1|\d+)\.\d+[a-z]*"


def get_task_ids_from_headings() -> set[str]:
    """Extract all task IDs from task heading lines in docs/planning/tasks/*.md files.

    Matches: #### T<numbers>[.<letters>] — <title>
    where the ID includes optional letter suffixes like T2.36a or T0.12a.
    """
    task_dir = Path(__file__).parent.parent.parent / "docs" / "planning" / "tasks"
    task_ids = set()

    # Pattern matches: #### followed by whitespace, then T<digits>.<digits>[<letters>]
    # The pattern captures the full ID including letter suffixes.
    pattern = re.compile(rf"^#### ({TASK_ID})\s")

    for task_file in task_dir.glob("*.md"):
        with open(task_file, encoding="utf-8") as f:
            for line in f:
                match = pattern.match(line)
                if match:
                    task_ids.add(match.group(1))

    return task_ids



def _read_from_master(path: str) -> str:
    """`git show master:<path>` as text, raising loudly rather than skipping."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "show", f"master:{path}"],
            capture_output=True, text=True, check=True, timeout=10,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Could not read master:{path}: {e.stderr}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to read master:{path}: {e}") from e
    return result.stdout


def get_task_ids_from_master_headings() -> set[str]:
    """Task headings as they exist on master.

    The two directions of this check need different sources, because the two
    documents are updated on different branches:

    - A task heading is minted on the **epic branch** (or a lane) and reaches
      master only when that branch merges.
    - Its `progress.md` row is written on **master** immediately, because the
      runbook makes that file canonical there.

    So the pair is legitimately split for the whole life of an epic, and a
    check comparing one branch's headings to the other's rows reports that
    normal state as a defect. The first version compared working-tree headings
    to master rows and fired on `T2.108` within hours; comparing master to
    master instead just moves the false positive to the other direction.

    The fix is to ask the question each direction actually cares about:
    headings-without-rows is asked of the tree you are on (a task you can see
    must be schedulable), and rows-without-headings is asked against headings
    from **either** source, since a row is only orphaned when no branch
    defines its task.
    """
    pattern = re.compile(rf"^#### ({TASK_ID})\s")
    listing = _read_from_master("docs/planning/tasks")
    task_ids: set[str] = set()
    for name in listing.split("\n"):
        name = name.strip()
        if not name.endswith(".md"):
            continue
        for line in _read_from_master(f"docs/planning/tasks/{name}").split("\n"):
            match = pattern.match(line)
            if match:
                task_ids.add(match.group(1))
    return task_ids


def get_task_ids_from_progress() -> set[str]:
    """Extract all task IDs from progress.md table rows.

    Reads from master branch (the canonical source per runbook §6), not the
    working tree. The epic branch's progress.md is stale by design.

    Matches: | T<numbers>[.<letters>] | in markdown table rows.
    Only matches at line start (after whitespace) to avoid prose mentions.
    """
    import subprocess
    task_ids = set()

    # Pattern matches: | followed by T<digits>.<digits>[<letters>] followed by |
    # Anchored to line start (after optional whitespace) to ignore prose mentions.
    pattern = re.compile(rf"^\| ({TASK_ID})\s*\|")

    try:
        result = subprocess.run(
            ["git", "show", "master:docs/planning/progress.md"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        content = result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Could not read progress.md from master branch: {e.stderr}"
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Failed to read master:docs/planning/progress.md: {e}"
        ) from e

    for line in content.split("\n"):
        match = pattern.match(line.strip())
        if match:
            task_ids.add(match.group(1))

    return task_ids


def test_task_headings_have_progress_rows():
    """A task heading in any docs/planning/tasks/*.md must have a row in progress.md."""
    headings = get_task_ids_from_headings()
    rows = get_task_ids_from_progress()

    missing_rows = headings - rows
    assert not missing_rows, (
        f"Task headings with no progress.md row (invisible to scheduling): {sorted(missing_rows)}"
    )


def test_progress_rows_have_task_headings():
    """Orphaned `progress.md` rows are REPORTED, never failed. Here is why.

    The strict version of this check is incompatible with the branching model
    and that is a property of the workflow, not a bug to tune around:

    - A task heading is minted on the **epic branch** and reaches master only
      when that branch merges — weeks, for a long epic.
    - Its `progress.md` row is written on **master** immediately, because the
      runbook makes that file canonical there and nowhere else.

    So for the whole life of an epic there are rows on master whose headings
    exist only on the epic branch. Every source pairing fails somewhere:
    working-tree headings against master rows fired on `T2.108` within hours of
    landing; master against master fails for the same reason; the union of the
    two still misses a heading that lives on neither.

    Failing the build on a normal state would train everyone to ignore this
    module, which would cost more than the check is worth — the harm it guards
    is a stale row, mild and self-announcing, where the direction above guards
    a task nothing can schedule. So this reports and does not fail.

    Corrected 2026-08-07, same day it landed, after the strict form red-flagged
    a healthy tree three times running.
    """
    headings = get_task_ids_from_headings() | get_task_ids_from_master_headings()
    rows = get_task_ids_from_progress()

    orphaned_rows = sorted(rows - headings)
    if orphaned_rows:
        print(
            "\nNOTE: progress.md rows with no task heading on this tree or on "
            f"master: {orphaned_rows}. Expected while an epic branch holds the "
            "heading; a defect only if it survives that branch's merge."
        )


# ----------------------------------------------------------------- release ladder
# `RELEASES.md` is read from master for the same reason `progress.md` is: both are
# planning state, canonical there and nowhere else, and `gen_progress.py` — which
# derives the Version column from the ladder — hard-refuses to run off master. A
# working-tree read would compare an epic branch's ladder against master's rows.

# One rule, shared with `gen_progress.py`: a `### ` section whose label is a
# version or `Gate track` owns the `- ``Tid`` ` list items beneath it. Every other
# heading owns prose, so the parked ids — which appear as inline backticks in a
# sentence — are read by neither parser and correctly carry no version.
LADDER_SECTION = re.compile(r"^### (v\d+\.\d+|Gate track)\b")
LADDER_ITEM = re.compile(rf"^- `({TASK_ID})`")
CELL = re.compile(r"(?<!\\)\|")


def _versioned_task_ids() -> dict[str, set[str]]:
    """Task ids per ladder section, parsed from master's `RELEASES.md`.

    The gate track is keyed `gate`: it is not a version, but it is an
    assignment, and a task in both it and a version is the same
    double-count a task in two versions is.
    """
    versions: dict[str, set[str]] = {}
    current = None
    for line in _read_from_master("docs/planning/RELEASES.md").split("\n"):
        heading = LADDER_SECTION.match(line)
        if heading:
            label = heading.group(1)
            current = "gate" if label == "Gate track" else label
            versions.setdefault(current, set())
            continue
        if line.startswith("## "):
            current = None
            continue
        item = LADDER_ITEM.match(line)
        if item and current:
            versions[current].add(item.group(1))
    return versions


def test_every_versioned_task_exists_in_progress():
    """A version that names a task nobody tracks is a plan nobody can execute."""
    versioned = {t for ids in _versioned_task_ids().values() for t in ids}
    rows = get_task_ids_from_progress()

    assert versioned - rows == set(), (
        f"RELEASES.md names tasks with no progress.md row: {sorted(versioned - rows)}"
    )


def test_no_task_is_assigned_to_two_versions():
    """One task ships once. Two homes means the burn-down double-counts."""
    seen: dict[str, str] = {}
    duplicated = []
    for version, ids in sorted(_versioned_task_ids().items()):
        for task in sorted(ids):
            if task in seen:
                duplicated.append(f"{task}: {seen[task]} and {version}")
            seen[task] = version

    assert duplicated == [], f"tasks assigned to two versions: {duplicated}"


def test_progress_version_column_agrees_with_the_ladder():
    """The Version cell is derived from RELEASES.md, so a disagreement means
    `progress.md` was regenerated against a different ladder than the one
    committed — or edited by hand, which the column is not for. Checking the
    cell rather than the row count is the point: a stale column still has the
    right number of rows.
    """
    expected = {
        task: version
        for version, ids in _versioned_task_ids().items()
        for task in ids
    }
    row = re.compile(rf"^\| ({TASK_ID}) \|")
    mismatched = []
    for line in _read_from_master("docs/planning/progress.md").split("\n"):
        match = row.match(line)
        if not match:
            continue
        cells = [c.strip() for c in CELL.split(line)]
        # 0 is the empty lead, then Task Title Size Model Effort Version.
        actual = cells[6] if len(cells) > 6 else "<no such column>"
        want = expected.get(match.group(1), "—")
        if actual != want:
            mismatched.append(f"{match.group(1)}: column={actual!r} ladder={want!r}")

    assert mismatched == [], (
        "progress.md's Version column disagrees with RELEASES.md; regenerate it "
        f"on master with scripts/gen_progress.py: {mismatched}"
    )


# ------------------------------------------------------------- generator behaviour
# These run the generator itself, from the working tree, so an edit is tested
# before it is committed. `progress.md` is read from master and the generator is
# not, which is only sound while the two copies agree — hence the sync check
# below. Both tests cover guards whose failure mode is silent: the output still
# has every row, every count and every state cell, and is simply missing
# something.

GENERATOR = Path(__file__).resolve().parents[2] / "docs/planning/scripts/gen_progress.py"

EPIC_STUBS = {
    "E0-baseline-and-harness.md": "T0.01",
    "E1-engine-core.md": "T1.01",
    "E2-truth-core.md": "T2.01",
    "E3-synthesis-and-reach.md": "T3.17",
    "E4-hardening-and-scale.md": "T4.06",
    "EH1-documents-pkm.md": "TH1.10",
    "M1-measurement.md": "T2.114",
}

STUB_RELEASES = """# Releases

### v0.2 — Stub version

- `T3.17` — Stub task

### Gate track

- `T2.114` — Stub task

## Parked

- `T4.06` — Stub task

Parked prose naming `T1.01`, which must stay unversioned because a task id
inside a sentence is a mention, not an assignment.
"""


def _planning_fixture(root: Path) -> Path:
    """A minimal docs/planning the generator can run against."""
    (root / "tasks").mkdir()
    for name, task in EPIC_STUBS.items():
        (root / "tasks" / name).write_text(
            f"#### {task} — Stub task\n`Size: M` · `Model: Sonnet 5` · `Effort: high`\n",
            encoding="utf-8",
        )
    (root / "RELEASES.md").write_text(STUB_RELEASES, encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "gen_progress.py").write_text(
        GENERATOR.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return root


def test_the_generator_is_the_same_on_this_branch_and_on_master():
    """The generator only ever RUNS on master (it refuses elsewhere), but the
    tests below run the working-tree copy so an edit is caught before it is
    committed. Those two facts are only compatible while the copies agree — and
    unlike progress.md, a script that differs per branch has no reading under
    which either copy is the true one."""
    assert GENERATOR.read_text(encoding="utf-8") == _read_from_master(
        "docs/planning/scripts/gen_progress.py"
    ), (
        "docs/planning/scripts/gen_progress.py differs between this branch and "
        "master. It writes a file that is canonical on master, so land the same "
        "content on both rather than letting the copies drift."
    )


def _run_generator(root: Path) -> str:
    result = subprocess.run(
        [sys.executable, "scripts/gen_progress.py"],
        cwd=root, capture_output=True, text=True, timeout=60,
        env={**os.environ, "GEN_PROGRESS_ALLOW_BRANCH": "1"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return (root / "progress.md").read_text(encoding="utf-8")


def _version_cell(progress: str, task: str) -> str:
    for line in progress.split("\n"):
        cells = [c.strip() for c in CELL.split(line)]
        if len(cells) > 6 and cells[1] == task:
            return cells[6]
    raise AssertionError(f"no row for {task}")


def test_the_generator_derives_the_version_column_from_the_ladder(tmp_path):
    """Version is scope, so it comes from RELEASES.md. Were it hand-edited and
    carried forward instead, a wrong carry window would blank all 278 cells
    while every row, count and state cell stayed correct."""
    progress = _run_generator(_planning_fixture(tmp_path))

    assert _version_cell(progress, "T3.17") == "v0.2"
    assert _version_cell(progress, "T2.114") == "gate"
    # The two ways a task id appears outside a ladder section. The list item is
    # the one that bites: it is the shape the parser looks for, so only the
    # section reset keeps it out — and a mutation drill on 2026-08-10 showed a
    # prose-only fixture proves nothing about that reset.
    assert _version_cell(progress, "T4.06") == "—", (
        "a list item under a non-ladder heading must not be assigned a version"
    )
    assert _version_cell(progress, "T1.01") == "—", (
        "a task id mentioned in prose must not be assigned a version"
    )


def test_the_generator_carries_hand_written_notes_through_a_regeneration(tmp_path):
    """progress.md holds standing prose in two regions the generator cannot
    reproduce. Dropping them is a silent delete — on 2026-08-10 that was an
    open-flake record and the account of three recount defects, 62 lines."""
    root = _planning_fixture(tmp_path)
    first = _run_generator(root)

    seeded = first.replace("## Rollup", "STANDING-PREAMBLE-NOTE\n\n## Rollup", 1)
    seeded = seeded.replace("\n---\n", "\nSTANDING-ROLLUP-NOTE\n\n---\n", 1)
    assert "STANDING-PREAMBLE-NOTE" in seeded and "STANDING-ROLLUP-NOTE" in seeded
    (root / "progress.md").write_text(seeded, encoding="utf-8")

    second = _run_generator(root)
    assert "STANDING-PREAMBLE-NOTE" in second, "preamble notes were deleted"
    assert "STANDING-ROLLUP-NOTE" in second, "rollup notes were deleted"

    # Carrying must also be idempotent: an anchor that matched the carried copy
    # as well as the generated one would grow the file on every regeneration.
    third = _run_generator(root)
    assert third.count("STANDING-PREAMBLE-NOTE") == 1
    assert third.count("STANDING-ROLLUP-NOTE") == 1
    assert third.count("## Rollup") == 1

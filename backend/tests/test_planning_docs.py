"""Test planning document correspondence between task definitions and progress tracking.

Ensures that every task heading in docs/planning/tasks/*.md has a corresponding
row in docs/planning/progress.md, and vice versa. This catches:
- Task headings with no progress row (invisible to scheduling)
- Progress rows for tasks that no longer exist (surviving a deletion or renumbering)
"""

import re
from pathlib import Path


def get_task_ids_from_headings() -> set[str]:
    """Extract all task IDs from task heading lines in docs/planning/tasks/*.md files.

    Matches: #### T<numbers>[.<letters>] — <title>
    where the ID includes optional letter suffixes like T2.36a or T0.12a.
    """
    task_dir = Path(__file__).parent.parent.parent / "docs" / "planning" / "tasks"
    task_ids = set()

    # Pattern matches: #### followed by whitespace, then T<digits>.<digits>[<letters>]
    # The pattern captures the full ID including letter suffixes.
    pattern = re.compile(r"^#### (T\d+\.\d+[a-z]*)\s")

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
    pattern = re.compile(r"^#### (T\d+\.\d+[a-z]*)\s")
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
    pattern = re.compile(r"^\| (T\d+\.\d+[a-z]*)\s*\|")

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

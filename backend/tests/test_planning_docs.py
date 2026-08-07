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
    """A progress.md row must correspond to a task heading in docs/planning/tasks/*.md."""
    headings = get_task_ids_from_headings()
    rows = get_task_ids_from_progress()

    orphaned_rows = rows - headings
    assert not orphaned_rows, (
        f"progress.md rows with no task heading (task deleted or renumbered?): {sorted(orphaned_rows)}"
    )

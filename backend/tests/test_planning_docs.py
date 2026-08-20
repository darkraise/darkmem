"""Test planning document correspondence between task definitions and progress tracking.

Ensures that every task heading in docs/planning/tasks/*.md has a corresponding
row in docs/planning/progress.md, and vice versa. This catches:
- Task headings with no progress row (invisible to scheduling)
- Progress rows for tasks that no longer exist (surviving a deletion or renumbering)
"""

import functools
import json
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

TASKS_DIR = Path(__file__).resolve().parents[2] / "docs/planning/tasks"


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



# Where master's content is read from. A working clone has the local branch;
# a CI checkout of a *tag* is a detached HEAD with no local `master` at all,
# only the remote-tracking ref — and every check below then died on
# "invalid object name 'master'" rather than on anything about the documents.
# Both names point at the same content, so resolve rather than assume.
_MASTER_REF_CANDIDATES = ("master", "origin/master", "refs/remotes/origin/master")


@functools.lru_cache(maxsize=1)
def _master_ref() -> str:
    """The first candidate git can resolve. Raises loudly if none exist."""
    import subprocess

    for ref in _MASTER_REF_CANDIDATES:
        probe = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
            capture_output=True, text=True, timeout=10,
        )
        if probe.returncode == 0:
            return ref
    raise RuntimeError(
        "no master ref found — tried "
        + ", ".join(_MASTER_REF_CANDIDATES)
        + ". These checks read the canonical planning docs from master; a "
        "checkout without it cannot answer them. In CI, fetch the branch: "
        "git fetch --depth=1 origin +refs/heads/master:refs/remotes/origin/master"
    )


def _read_from_master(path: str) -> str:
    """`git show <master>:<path>` as text, raising loudly rather than skipping."""
    import subprocess

    ref = _master_ref()
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
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
            ["git", "show", f"{_master_ref()}:docs/planning/progress.md"],
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

# One rule, byte-identical to `gen_progress.py`: a `### ` section whose label is
# a version or `Gate track` owns the `- ``Tid`` ` list items beneath it, and any
# other heading **of any level** ends that section. The reset used to fire only
# on `## `, which left an h3 hole — `### Parked` under `### Gate track` reset
# nothing, so parked list items parsed as `gate`.
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
        if line.startswith("#"):
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


def test_every_open_task_is_assigned_a_version():
    """Open work with no version is the visibility hole the column was added to
    close, and every other test here is blind to it.

    The checks above compare the column against the ladder, so they pass loudest
    exactly when the ladder assigns nothing: the cell is `—`, the derivation
    agrees, and the two are consistently empty. That is not a hypothetical. v1.0
    was minted 2026-08-15 with its scope written as prose — four bullets naming
    their tasks inside sentences — and both parsers own only `` - `Tid` `` list
    items, so all nineteen open tasks it carries read `—` until 2026-08-16 while
    this file stayed green.

    Done and dropped rows are excluded deliberately: v0.1 ships no list items on
    the stated ground that the column answers "which release?" for *open* work.
    """
    row = re.compile(rf"^\| ({TASK_ID}) \|")
    unassigned = []
    for line in _read_from_master("docs/planning/progress.md").split("\n"):
        match = row.match(line)
        if not match:
            continue
        cells = [c.strip() for c in CELL.split(line)]
        if len(cells) <= 8:
            continue
        version, status = cells[6], cells[8]
        if status in {"done", "dropped"}:
            continue
        if version in {"—", "-", ""}:
            unassigned.append(f"{match.group(1)} ({status})")

    assert unassigned == [], (
        "open tasks carry no version — add them as `- `Tid`` list items under "
        "their `### vN.N` or `### Gate track` section in RELEASES.md; naming "
        f"them in prose assigns nothing: {unassigned}"
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

### Parked — an h3, directly under a ladder section

- `T4.06` — Stub task

Parked prose naming `T1.01`, which must stay unversioned because a task id
inside a sentence is a mention, not an assignment.

## Also parked, at h2

- `T2.01` — Stub task
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
    # The ways a task id appears outside a ladder section. A list item is what
    # bites — it is the shape the parser looks for, so only the section reset
    # keeps it out — and the reset must fire at EVERY heading level. `T4.06`
    # sits under an h3 parked heading directly below the gate track, which is
    # the real file's own adjacency and the case a `## `-only reset missed:
    # both parsers stamped it `gate` while every test stayed green, because the
    # column and the ladder agreed with each other on the misparse.
    assert _version_cell(progress, "T4.06") == "—", (
        "a list item under an h3 non-ladder heading must not be assigned a version"
    )
    assert _version_cell(progress, "T2.01") == "—", (
        "a list item under an h2 non-ladder heading must not be assigned a version"
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


# ----------------------------------------------------------------- product version
PRODUCT_VERSION = re.compile(r'version\s*=\s*"(\d+\.\d+\.\d+)"')


def test_the_product_version_is_one_number_in_three_places():
    """Backend, the OpenAPI document and the SPA ship as ONE image, so they are
    one product with one version. The SDK and extension are distributed
    separately (doc 15 §2) and keep their own — they are deliberately not
    checked here."""
    root = Path(__file__).resolve().parents[2]
    pyproject = PRODUCT_VERSION.search(
        (root / "backend/pyproject.toml").read_text(encoding="utf-8")
    ).group(1)
    fastapi = re.search(
        r'FastAPI\([^)]*version="(\d+\.\d+\.\d+)"',
        (root / "backend/app/main.py").read_text(encoding="utf-8"),
    ).group(1)
    package = json.loads(
        (root / "frontend/package.json").read_text(encoding="utf-8")
    )["version"]

    assert pyproject == fastapi == package, (
        f"product version drifted: pyproject={pyproject} "
        f"fastapi={fastapi} package.json={package}"
    )


def test_the_changelog_names_the_version_being_shipped():
    """`release.sh` tags whatever it is given and does not read the changelog.
    A release whose changelog does not name it is the one failure that is
    invisible until someone goes looking for what changed."""
    root = Path(__file__).resolve().parents[2]
    version = PRODUCT_VERSION.search(
        (root / "backend/pyproject.toml").read_text(encoding="utf-8")
    ).group(1)
    tag = "v" + version.rsplit(".", 1)[0]
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")

    assert re.search(rf"^## {re.escape(tag)}\b", changelog, re.M), (
        f"CHANGELOG.md has no `## {tag}` section for the version the product "
        "fields currently claim"
    )


def test_every_shell_script_with_a_shebang_is_executable():
    """A `#!` line is a declaration that the file is run directly, and
    CLAUDE.md tells you to run several of these as `./scripts/<name>.sh`.
    `scripts/build-push.sh` carried a shebang and mode 100644 anyway, so the
    v0.1 release died at its build step after a clean full gate — and the first
    fix used `git update-index --chmod=+x`, which sets the index mode only and
    was silently reverted by the next `git add` of that path. Checking the
    committed mode is what makes the fix stick."""
    root = Path(__file__).resolve().parents[2]
    listing = subprocess.run(
        ["git", "ls-files", "-s", "--", "scripts/*.sh"],
        cwd=root, capture_output=True, text=True, check=True, timeout=10,
    ).stdout

    not_executable = []
    for line in listing.splitlines():
        mode, _, rest = line.partition(" ")
        path = rest.split("\t", 1)[1]
        if (root / path).read_text(encoding="utf-8").startswith("#!") and mode != "100755":
            not_executable.append(f"{path} is {mode}")

    assert not_executable == [], (
        f"shell scripts with a shebang but no executable bit: {not_executable}"
    )


# ------------------------------------------------------------- gate qualifiers
# Owner ruling 2026-08-10: three qualifiers, not two. `(produces)` names the
# class spec §3 already had and §4 had no word for — a task whose OUTPUT is the
# gate. Scope is open tasks only: 181 of the 236 `Gate:` fields sit on done work
# in E0/E1/E2, where the qualifier has no reader (the loop only ever asks whether
# an OPEN task is startable) and stamping them would write a claim about history
# that was never true of it.

GATE_FIELD = re.compile(r"`Gate: (G-[A-F])(?:\s*\(([^)]*)\))?`")
GATE_QUALIFIERS = {"label", "blocking", "produces"}
TASK_HEADING = re.compile(rf"^#### ({TASK_ID}) —")
RESOLVED = {"done", "dropped"}


def _task_state_from_master() -> dict[str, tuple[str, str]]:
    """`{task: (status, version)}` from master's progress.md."""
    state: dict[str, tuple[str, str]] = {}
    row = re.compile(rf"^\| ({TASK_ID}) \|")
    for line in _read_from_master("docs/planning/progress.md").split("\n"):
        match = row.match(line)
        if match:
            cells = [c.strip() for c in CELL.split(line)]
            state[match.group(1)] = (cells[8], cells[6])
    return state


def _open_gate_fields():
    """`(file, line, task, gate, qualifier)` for every unresolved gated task."""
    state = _task_state_from_master()
    found = []
    for path in sorted(TASKS_DIR.glob("*.md")):
        task = None
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            heading = TASK_HEADING.match(line)
            if heading:
                task = heading.group(1)
            for gate, qualifier in GATE_FIELD.findall(line):
                # A task with no row fails closed: it is unschedulable, so a
                # newly minted one must qualify rather than slip through.
                status = state.get(task, ("", ""))[0]
                if status not in RESOLVED:
                    found.append((path.name, number, task, gate, qualifier))
    return found


def test_every_open_gate_field_says_what_it_blocks():
    """An unqualified `Gate:` reads as "blocked until the gate clears", which is
    false for nearly every task carrying one: gates gate labels, and T2.95's
    serving boundary already refuses an unbacked claim. That ambiguity is what
    queued the roadmap behind measurement — 232 tasks done, nothing released."""
    bad = [
        f"{name}:{number} {task} Gate: {gate} ({qualifier or 'unqualified'})"
        for name, number, task, gate, qualifier in _open_gate_fields()
        if qualifier not in GATE_QUALIFIERS
    ]
    assert bad == [], (
        "these Gate fields do not say whether the code is blocked, the label "
        f"waits, or the task produces the gate: {bad}"
    )


def test_the_gate_track_is_qualified_produces():
    """`Version: gate` and `Gate: G-x (produces)` are two spellings of one fact.
    Binding them stops a task being scheduled as feature work in one document
    and as a measurement run in the other."""
    state = _task_state_from_master()
    wrong = [
        f"{task}: Version={state.get(task, ('', '?'))[1]} but Gate ({qualifier or 'unqualified'})"
        for _, _, task, _, qualifier in _open_gate_fields()
        if (state.get(task, ("", ""))[1] == "gate") != (qualifier == "produces")
    ]
    assert wrong == [], f"gate-track marking disagrees across the two documents: {wrong}"


# ── the ledger's status table must agree with the tree, not with its own prose ──
#
# The summary table at the top of `gate-ledger.md` is the first thing a reader
# consults to answer "which gates carry verdicts?", and it is 450 lines above
# the sections that decide the answer. On 2026-08-16 G-C was cleared and its
# record minted; the table went on saying **open** ... "No promotion record
# minted" for a day, on master and on every branch, while the section below it
# and `CLAUDE.md` both said CLEARED. Nothing compared them, because every
# comparison available was prose-to-prose.
#
# So the binding here is doc-to-artifact. A gate's evidence record is minted
# only by a cleared run and never by hand, which makes its presence the one
# machine-readable fact about a gate's status — and the two gates that have
# such a record are exactly the two whose status has actually drifted.

GATE_ROW = re.compile(r"^\| (G-[A-G]) \| [^|]* \| (.*?) \|[^|]*\|[^|]*\|\s*$")


def _gate_status_cells() -> dict[str, str]:
    """`{gate: status cell}` from master's gate-ledger summary table."""
    cells = {}
    for line in _read_from_master("docs/planning/gate-ledger.md").split("\n"):
        match = GATE_ROW.match(line)
        if match:
            cells[match.group(1)] = match.group(2)
    return cells


def test_the_summary_table_lists_every_gate_exactly_once():
    """The parse above is load-bearing for the two tests below: a row it fails
    to match would make them pass by checking nothing."""
    cells = _gate_status_cells()
    assert sorted(cells) == ["G-A", "G-B", "G-C", "G-D", "G-E", "G-F", "G-G"]


def test_g_c_s_row_agrees_with_its_minted_evidence_record():
    """`promotion_metrics_record.json` is minted only by a cleared G-C run
    (T2.95/T2.100) and gates the promoted-fact label at runtime, so it is the
    tree's own answer to whether G-C cleared. The row must say the same thing.

    **The path is resolved from this file, NOT through `claim_gates`**, and the
    first version of this test did the latter and passed vacuously against a
    stale row. `conftest`'s autouse `_corroboration_gate_closed_by_default`
    repoints `PROMOTION_RECORD_PATH` at a nonexistent path so every door drive
    asserts the withheld rung — correct for those tests, and fatal here: it made
    this one read "no record minted" and take the branch that agrees with an
    `**open**` row. That fixture's own docstring says what it stops covering,
    "whether the *shipped* record is well-formed ... a property of the artifact,
    not of the gate"; this is a second such property, and it needs the artifact
    the same way.
    """
    row = _gate_status_cells()["G-C"]
    record = (
        Path(__file__).resolve().parents[1]
        / "app" / "services" / "promotion_metrics_record.json"
    )
    eligible = False
    if record.exists():
        eligible = json.loads(record.read_text(encoding="utf-8")).get(
            "gate_eligible"
        ) is True

    if eligible:
        assert "**CLEARED**" in row, (
            f"{record.name} is minted with gate_eligible true, so G-C has "
            "cleared and promoted statuses are reaching readers — but the "
            f"ledger's summary row still reads: {row[:120]}"
        )
        assert "**open**" not in row
    else:
        assert "**CLEARED**" not in row, (
            "the ledger's summary row says G-C cleared, but no evidence record "
            f"is minted at {record}. The record is what serves the label; a "
            "row claiming a clear the tree does not carry is the wrong way round"
        )


def test_g_d_s_row_agrees_with_the_qualification_records():
    """G-D's evidence is a per-role qualification record (T2.117). Both are
    absent on this branch for stated reasons, so the row must not read cleared;
    if one is ever minted, this fails until the row is updated with it."""
    from app.services import verification_judge as vj

    row = _gate_status_cells()["G-D"]
    minted = sorted(
        role for role, path in vj.QUALIFICATION_RECORD_PATHS.items() if path.exists()
    )
    if not minted:
        assert "**CLEARED**" not in row, (
            "the ledger says G-D cleared while no role carries a qualification "
            "record; `judge()` refuses unconditionally without one, so nothing "
            "in the tree backs that claim"
        )
    else:
        assert "**CLEARED**" in row or "open" in row.lower(), (
            f"qualification records exist for {minted}; G-D's summary row must "
            f"say what they mean rather than predating them: {row[:120]}"
        )

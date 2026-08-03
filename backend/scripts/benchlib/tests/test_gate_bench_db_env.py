"""Guards gate.sh's BENCH_DATABASE_URL passthrough (T2.76).

gate.sh exports TEST_DATABASE_URL with a fallback default but historically
never did the same for BENCH_DATABASE_URL, so any gate arm that imports
benchlib.bench_db (which resolves BENCH_DATABASE_URL at import time) reset
whichever unnumbered darkmem_bench happened to be sitting there regardless of
the caller's lane assignment.

A test that merely greps gate.sh for the string "BENCH_DATABASE_URL" would
pass on a assignment that is present but broken (hardcoded, unconditional,
or with a drifted default) just as easily as on a correct one. Instead this
extracts the *exact* assignment expression from each affected run_gate block
and executes it in bash, so the guard actually exercises the fallback
semantics gate.sh relies on.
"""
import re
import subprocess
from pathlib import Path

import pytest

GATE_SH = Path(__file__).resolve().parents[4] / "scripts" / "gate.sh"
CANONICAL_DEFAULT = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench"


def _gate_sh_text() -> str:
    assert GATE_SH.is_file(), f"gate.sh not found at {GATE_SH}"
    return GATE_SH.read_text()


def _extract_run_gate_block(text: str, name: str) -> str:
    """Return exactly the one logical `run_gate "name" ...` statement.

    A run_gate invocation is a single shell statement spanning multiple
    lines via trailing backslash continuation. Stopping at the next
    `run_gate "` occurrence (rather than the end of continuation) would
    swallow unrelated script text sitting between two arms -- e.g. the
    `--full` section header and PORTS_BEFORE snapshot that sit between the
    F1 bench arm and the retrieval eval arm -- and falsely attribute their
    contents to the wrong block.
    """
    lines = text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.strip().startswith(f'run_gate "{name}"')),
        None,
    )
    assert start is not None, f'run_gate "{name}" block not found in gate.sh'
    block_lines = []
    i = start
    while True:
        line = lines[i]
        block_lines.append(line)
        if not line.rstrip().endswith("\\"):
            break
        i += 1
    return "\n".join(block_lines)


def _extract_assignment(block: str, var: str) -> str:
    match = re.search(rf'{var}="[^\n]*"', block)
    assert match, f"{var} assignment not found in this run_gate block:\n{block}"
    return match.group(0)


def _resolve_in_bash(assignment: str, exported_value: str | None) -> str:
    import os

    env = os.environ.copy()
    if exported_value is None:
        env.pop("BENCH_DATABASE_URL", None)
    else:
        env["BENCH_DATABASE_URL"] = exported_value
    script = f'{assignment}\nprintf %s "$BENCH_DATABASE_URL"'
    result = subprocess.run(
        ["bash", "-c", script], env=env, capture_output=True, text=True, check=True
    )
    return result.stdout


@pytest.fixture(params=["benchlib tests", "retrieval eval"])
def bench_touching_block(request):
    return request.param, _extract_run_gate_block(_gate_sh_text(), request.param)


def test_block_invokes_the_expected_bench_touching_script(bench_touching_block):
    name, block = bench_touching_block
    expected_target = {
        "benchlib tests": "pytest scripts/benchlib/tests",
        "retrieval eval": "scripts/benchlib/run_retrieval_eval.py",
    }[name]
    assert expected_target in block, (
        f'run_gate "{name}" no longer invokes {expected_target!r} — this guard is '
        "pinned to that command and needs updating alongside gate.sh"
    )


def test_block_respects_exported_bench_database_url(bench_touching_block):
    _, block = bench_touching_block
    assignment = _extract_assignment(block, "BENCH_DATABASE_URL")
    resolved = _resolve_in_bash(
        assignment, "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench_11"
    )
    assert resolved == "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench_11"


def test_block_falls_back_to_shared_default_when_unset(bench_touching_block):
    _, block = bench_touching_block
    assignment = _extract_assignment(block, "BENCH_DATABASE_URL")
    resolved = _resolve_in_bash(assignment, None)
    assert resolved == CANONICAL_DEFAULT


@pytest.mark.parametrize(
    "name", ["extraction F1 bench (--algo-only)", "API e2e suite", "playwright e2e"]
)
def test_non_bench_arms_do_not_declare_bench_database_url(name):
    """The audit (T2.76 R2): these arms never import benchlib.bench_db, so
    threading BENCH_DATABASE_URL through them would be a no-op that invites
    someone to believe it matters there. Declaring it must stay confined to
    the two arms that actually resolve it."""
    block = _extract_run_gate_block(_gate_sh_text(), name)
    assert "BENCH_DATABASE_URL" not in block

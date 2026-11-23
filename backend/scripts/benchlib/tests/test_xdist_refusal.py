"""The bench suite shares one database, so a parallel run is refused up front."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest

_CHILD_MARKER = "BENCHLIB_XDIST_REFUSAL_CHILD"
_BACKEND = pathlib.Path(__file__).resolve().parents[3]


@pytest.mark.skipif(bool(os.environ.get(_CHILD_MARKER)), reason="the refused child run")
def test_an_xdist_run_is_refused():
    completed = subprocess.run(
        [
            sys.executable, "-m", "pytest", "scripts/benchlib/tests/test_xdist_refusal.py",
            "-n", "2", "-q", "-k", "nothing",
        ],
        cwd=_BACKEND,
        env={**os.environ, _CHILD_MARKER: "1"},
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = completed.stdout + completed.stderr
    assert completed.returncode == 4, output
    assert ".venv/bin/python -m pytest scripts/benchlib/tests -q" in output

"""``run_e2e.py`` hands its own arguments to pytest, as the Playwright runner
does to Playwright, so one e2e test can run through the one entry point."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

RUNNER = Path(__file__).resolve().parent.parent / "scripts" / "e2e" / "run_e2e.py"


def _runner(monkeypatch, calls: list[list[str]]):
    monkeypatch.setattr(sys, "path", list(sys.path))
    # The real stack module imports e2e_db, which repoints DATABASE_URL for
    # the whole process; the runner only needs boot().
    handle = types.SimpleNamespace(base_url="http://127.0.0.1:1", teardown=lambda: None)
    fake_stack = types.ModuleType("e2e.stack")
    fake_stack.boot = lambda **_kwargs: handle
    monkeypatch.setitem(sys.modules, "e2e.stack", fake_stack)

    spec = importlib.util.spec_from_file_location("run_e2e_under_test", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def run(command, **_kwargs):
        calls.append(command)
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(module, "_extraction_model_is_servable", lambda: (True, "stubbed"))
    monkeypatch.setattr(module, "subprocess", types.SimpleNamespace(run=run))
    return module


def _without_report(command: list[str]) -> list[str]:
    return [arg for arg in command if not arg.startswith("--junitxml=")]


def test_extra_arguments_reach_pytest(monkeypatch):
    calls: list[list[str]] = []
    runner = _runner(monkeypatch, calls)

    monkeypatch.setattr(sys, "argv", ["run_e2e.py"])
    assert runner.main() == 0
    monkeypatch.setattr(sys, "argv", ["run_e2e.py", "-k", "session_rotation"])
    assert runner.main() == 0

    plain, narrowed = calls
    assert _without_report(plain) == [
        sys.executable, "-m", "pytest", "scripts/e2e/tests", "-q", "-rs",
    ]
    assert len(narrowed) == len(plain) + 2
    assert narrowed[-2:] == ["-k", "session_rotation"]
    assert _without_report(narrowed[:-2]) == _without_report(plain)

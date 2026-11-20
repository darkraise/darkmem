"""Dev scripts refuse to touch a database nobody named."""
from __future__ import annotations

import ast
import asyncio
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "backend" / "scripts"
STUBS = ("python", "pip", "alembic", "uvicorn")


def _stub(path: Path, log: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'#!/bin/sh\necho "{path} $*" >> "{log}"\nexit 0\n')
    path.chmod(0o755)


@pytest.fixture
def dev_tree(tmp_path):
    (tmp_path / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "start_dev_server.sh", tmp_path / "scripts")
    (tmp_path / "backend").mkdir()
    log = tmp_path / "calls.log"
    log.touch()
    _stub(tmp_path / "backend" / ".venv" / "bin" / "python", log)
    for name in STUBS:
        _stub(tmp_path / "bin" / name, log)
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    env["PATH"] = f"{tmp_path / 'bin'}:{env.get('PATH', '/usr/bin:/bin')}"
    return tmp_path, log, env


def _run(tree: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["timeout", "10", "bash", str(tree / "scripts" / "start_dev_server.sh")],
        env=env, capture_output=True, text=True, timeout=30,
    )


def test_start_dev_server_refuses_without_database_url(dev_tree):
    tree, log, env = dev_tree

    refused = _run(tree, env)

    assert refused.returncode not in (0, 124)
    assert "DATABASE_URL" in refused.stdout + refused.stderr
    assert log.read_text() == ""

    env["DATABASE_URL"] = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_dev"
    started = _run(tree, env)

    calls = log.read_text().splitlines()
    venv = str(tree / "backend" / ".venv" / "bin" / "python")
    assert started.returncode == 0, started.stderr
    assert calls and calls[0] == f"{venv} -m alembic upgrade head"
    assert not any(line.startswith(f"{tree / 'bin' / 'python'} ") for line in calls)


@pytest.fixture
def e2e_db_module(monkeypatch):
    def load(url: str):
        monkeypatch.setenv("DATABASE_URL", os.environ.get("DATABASE_URL", ""))
        monkeypatch.setenv("TEST_DATABASE_URL", url)
        monkeypatch.syspath_prepend(str(SCRIPTS))
        monkeypatch.delitem(sys.modules, "e2e", raising=False)
        monkeypatch.delitem(sys.modules, "e2e.e2e_db", raising=False)
        module = importlib.import_module("e2e.e2e_db")

        class _NoEngine:
            def begin(self):
                raise AssertionError("SQL reached the database before the target check")

            async def dispose(self):
                return None

        monkeypatch.setattr(module, "engine", _NoEngine())
        return module

    return load


@pytest.mark.parametrize("url", [
    "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem",
    "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench",
    "postgresql+asyncpg://darkmem:darkmem@127.0.0.1:5432/darkmem_test",
    "postgresql+asyncpg://darkmem:darkmem@localhost/darkmem_test_1",
])
def test_e2e_reset_refuses_a_non_disposable_database(e2e_db_module, url):
    module = e2e_db_module(url)

    with pytest.raises(module.NotADisposableDatabase):
        asyncio.run(module.reset_e2e_db())


@pytest.mark.parametrize("url", [
    "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test",
    "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_1",
    "postgresql+asyncpg://darkmem:darkmem@postgres:5432/darkmem_e2e",
])
def test_e2e_reset_accepts_the_suite_databases(e2e_db_module, url):
    module = e2e_db_module(url)

    module.assert_disposable_target(url)


def test_destructive_sql_guard_exemption_names_the_check():
    guard = SCRIPTS / "benchlib" / "tests" / "test_ambient_database_guard.py"
    tree = ast.parse(guard.read_text())
    exempt = next(
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "EXEMPT" for t in node.targets)
    )
    reason = ast.literal_eval(exempt)["e2e/e2e_db.py"]
    assert "never an ambient one" not in reason
    assert "assert_disposable_target" in reason

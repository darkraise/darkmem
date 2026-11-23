"""Acceptance tests for the audit-followups spec, written from its acceptance text."""
from __future__ import annotations

import ast
import gzip
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
BASE = "cee4bf42"
REGISTER = REPO / "docs/dforge/registers/2026-11-20-audit-remaining.md"
REGISTER_TOOL = Path("/root/.claude-alt/plugins/cache/darkraise/dforge/5.1.1/scripts/register")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


# ------------------------------------------------------------------ A22


@pytest.mark.parametrize("host", ["127.0.0.2", "[::1]", "0.0.0.0", "127.0.0.1", "localhost"])
def test_a22_e2e_reset_refuses_every_loopback_and_unspecified_host_on_5432(host):
    sys.path.insert(0, str(BACKEND / "scripts" / "e2e"))
    try:
        import e2e_db
    finally:
        sys.path.pop(0)
    url = f"postgresql+asyncpg://darkmem:pw@{host}:5432/darkmem_e2e"
    with pytest.raises(e2e_db.NotADisposableDatabase):
        e2e_db.assert_disposable_target(url)
    # the same host off the production port is a disposable target
    e2e_db.assert_disposable_target(f"postgresql+asyncpg://darkmem:pw@{host}:5433/darkmem_e2e")


def test_a22_e2e_database_defaults_to_darkmem_e2e_and_gate_names_it():
    env = {k: v for k, v in os.environ.items() if k not in {"TEST_DATABASE_URL", "DATABASE_URL"}}
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, 'scripts/e2e'); import e2e_db; print(e2e_db.TEST_DATABASE_URL)"],
        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().rsplit("/", 1)[-1] == "darkmem_e2e"

    gate = (REPO / "scripts/gate.sh").read_text()
    leg = gate[gate.index("API e2e suite"):]
    leg = leg[: leg.index("run_e2e.py")]
    assert "darkmem_e2e" in leg


# ------------------------------------------------------------------ A23

DUMP_TAIL = "--\n-- PostgreSQL database dump complete\n--\n\n"
OTHER_DATABASE_BODY = "--\n-- PostgreSQL database dump\n--\n\nCREATE TABLE public.notes (id uuid);\n\n"
GOOD_BODY = (
    "--\n-- PostgreSQL database dump\n--\n\nCREATE TABLE public.memories (id uuid);\n\n"
    "COPY public.alembic_version (version_num) FROM stdin;\n0006\n\\.\n\n"
)


def test_a23_backup_keeps_newest_three_suspect_dumps_and_touches_no_real_dump(tmp_path):
    from tests.test_backup_script import _run_backup, _stub

    dest = tmp_path / "backups"
    dest.mkdir()
    real = []
    for i in range(2):
        d = dest / f"darkmem-2019010{i + 1}-000000.sql.gz"
        d.write_bytes(gzip.compress((GOOD_BODY + DUMP_TAIL).encode()))
        os.utime(d, (1000 + i, 1000 + i))
        real.append(d)
    before = {d: (d.read_bytes(), d.stat().st_mtime) for d in real}
    seeded = []
    for i in range(6):
        s = dest / f"darkmem-202002{i + 1:02d}-000000.sql.gz.suspect"
        s.write_bytes(gzip.compress(OTHER_DATABASE_BODY.encode()))
        os.utime(s, (5000 + i, 5000 + i))
        seeded.append(s)
    wrong = _stub(tmp_path, "compose-wrong.sh", f"cat <<'SQL'\n{OTHER_DATABASE_BODY}{DUMP_TAIL}SQL\n")

    result = _run_backup(dest, wrong, keep="14")

    assert result.returncode != 0
    suspects = sorted(dest.glob("*.suspect"))
    new = [s for s in suspects if s not in seeded]
    assert len(suspects) == 3
    assert len(new) == 1
    assert set(suspects) == {*new, *seeded[-2:]}
    assert {d: (d.read_bytes(), d.stat().st_mtime) for d in real} == before


def test_a23_restore_cycle_whose_migrate_overruns_swaps_nothing_and_exits_non_zero(tmp_path):
    from tests.test_restore_cycle_script import _calls, _run

    result, records, elapsed = _run(
        tmp_path, migrate="exec sleep 60", probe="exit 0", env={"RESTORE_MIGRATE_TIMEOUT": "2"}
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert elapsed < 25
    assert not _calls(records, "RENAME")


# ------------------------------------------------------------------ A35


def test_a35_declared_context_is_gone_from_both_doors_and_both_sdks():
    from app.main import app
    from app.schemas.memory import MemorySearchRequest

    assert "context" not in MemorySearchRequest.model_fields
    doc = json.dumps(app.openapi()).lower()
    assert "x-darkmem-context" not in doc

    from app.schemas import envelope

    assert not hasattr(envelope, "ContextEcho")
    assert "context" not in envelope.ResponseEnvelope.model_fields

    assert not (BACKEND / "app/api/context_resolution.py").exists()
    mcp_src = (BACKEND / "app/api/mcp/server.py").read_text().lower()
    assert "x-darkmem-context" not in mcp_src

    ts = (REPO / "sdks/ts/src/client.ts").read_text()
    py = (REPO / "sdks/python/darkmem_sdk/client.py").read_text()
    for text in (ts, py):
        low = text.lower()
        assert "declarecontext" not in low
        assert "declare_context" not in low
        assert "x-darkmem-context" not in low

    for path in (BACKEND / "app").rglob("*.py"):
        assert "x-darkmem-context" not in path.read_text().lower(), path


# ------------------------------------------------------------------ A36


def test_a36_no_revision_route_or_mcp_tool_is_added():
    out = subprocess.run(
        [sys.executable, "-m", "alembic", "heads", "--verbose"], cwd=BACKEND, capture_output=True, text=True, timeout=120
    )
    assert out.returncode == 0, out.stderr
    heads = re.findall(r"^Rev: (\S+) \(head\)", out.stdout, re.M)
    assert heads == ["0006"]
    assert "0006_drop_blocks_search_vector.py" in out.stdout

    added = _git("diff", "--diff-filter=A", "--name-only", BASE, "HEAD", "--", "backend/migrations/versions").split()
    assert added == []

    # no route or tool decorator is added anywhere under the doors
    diff = _git("diff", "-U0", BASE, "HEAD", "--", "backend/app/api", "backend/app/main.py")
    added_decorators = [
        line for line in diff.splitlines()
        if re.match(r"^\+\s*@(router|app|mcp|server)\.(get|post|put|patch|delete|tool|websocket)\b", line)
    ]
    assert added_decorators == []

    from app.api.mcp.scopes import TOOL_SCOPES

    base_src = _git("show", f"{BASE}:backend/app/api/mcp/scopes.py")
    namespace = {"__name__": "app.api.mcp._base_scopes", "__package__": "app.api.mcp"}
    exec(compile(base_src, "base_scopes.py", "exec"), namespace)
    base_tools = set(namespace["TOOL_SCOPES"])
    assert set(TOOL_SCOPES) == base_tools
    assert len(TOOL_SCOPES) == 46


# ------------------------------------------------------------------ A37


def test_a37_register_check_passes_and_no_row_is_open_planned_or_doing():
    out = subprocess.run(
        ["bash", str(REGISTER_TOOL), "check", str(REGISTER)], cwd=REPO, capture_output=True, text=True, timeout=120
    )
    assert out.returncode == 0, out.stdout + out.stderr
    assert " 0 errors" in out.stdout

    header = None
    states = []
    for line in REGISTER.read_text().splitlines():
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells[0] == "#":
            header = cells
            continue
        if header:
            states.append((cells[0], cells[header.index("State")]))
    assert len(states) >= 413 - 1
    assert [row for row, state in states if state in {"open", "planned", "doing"}] == []

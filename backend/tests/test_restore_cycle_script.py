"""scripts/worker/restore-cycle.sh bounds each step that can hang, and a step
that overruns swaps nothing.

Driven through a stub compose command that records every call, as the
restore-loop tests in test_deployment_artifact.py are. A step told to hang
runs `exec sleep 60`, so only the script's own bound can end it.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from tests.test_deployment_artifact import (
    _AGE_STUB,
    REPO_ROOT,
    RESTORE_CYCLE,
    SNAPSHOT,
    _complete_dump,
    _record_fields,
)

_STUB = """#!/usr/bin/env bash
{
  for a in "$@"; do
    printf '%s\\x1f' "$a"
  done
  printf '\\n'
} >> "__LOG_PATH__"
case "$*" in
  *alembic*) __MIGRATE__ ;;
  *"baseline_sha()"*) __PROBE__ ;;
esac
cat >/dev/null
exit 0
"""


def _run(tmp_path: Path, *, migrate: str, probe: str, env: dict[str, str]):
    dumps = tmp_path / "dumps"
    dumps.mkdir()
    (dumps / SNAPSHOT).write_bytes(_complete_dump(tmp_path).read_bytes())
    log_path = tmp_path / "invocations.log"
    log_path.write_text("")
    stub = tmp_path / "compose_stub.sh"
    stub.write_text(
        _STUB.replace("__LOG_PATH__", str(log_path))
        .replace("__MIGRATE__", migrate)
        .replace("__PROBE__", probe)
    )
    stub.chmod(0o755)
    age = tmp_path / "age"
    age.write_text(_AGE_STUB)
    age.chmod(0o755)
    identity = tmp_path / "identity.txt"
    identity.write_text("AGE-SECRET-KEY-STUB")

    run_env = dict(os.environ)
    run_env.update(
        PATH=f"{tmp_path}:{run_env['PATH']}",
        COMPOSE_CMD=str(stub),
        DOCKER_CMD=str(stub),
        WORKER_COMPOSE=str(REPO_ROOT / "docker-compose.worker.yml"),
        DUMP_DIR=str(dumps),
        STATE_FILE=str(tmp_path / "state"),
        AGE_IDENTITY=str(identity),
        OWNER_PASSWORD="owner-pw",
        VIEWER_PASSWORD="viewer-pw",
        DB_NAME="darkmem",
        GRANTS=str(REPO_ROOT / "scripts" / "worker" / "viewer-grants.sql"),
        ATTACHMENT_STORE=str(tmp_path / "attachments"),
        **env,
    )
    started = time.monotonic()
    result = subprocess.run(
        ["bash", str(RESTORE_CYCLE)],
        capture_output=True, text=True, env=run_env, stdin=subprocess.DEVNULL, timeout=30,
    )
    elapsed = time.monotonic() - started
    records = [_record_fields(line) for line in log_path.read_text().splitlines() if line]
    return result, records, elapsed


def _calls(records, needle: str) -> list[int]:
    return [i for i, fields in enumerate(records) if any(needle in f for f in fields)]


def test_an_overrunning_migrate_swaps_nothing(tmp_path):
    result, records, elapsed = _run(
        tmp_path, migrate="exec sleep 60", probe="exit 0",
        env={"RESTORE_MIGRATE_TIMEOUT": "2"},
    )

    assert result.returncode != 0, result.stdout + result.stderr
    assert elapsed < 20
    assert not _calls(records, "RENAME")
    assert "migrate timed out" in result.stderr
    (migrate,) = _calls(records, "alembic")
    container = records[migrate][records[migrate].index("--name") + 1]
    removed = [i for i, fields in enumerate(records) if fields[:3] == ["rm", "-f", container]]
    terminated = _calls(records, "pg_terminate_backend")
    dropped = [
        i for i in _calls(records, "DROP DATABASE IF EXISTS")
        if any("darkmem_restore_" in f for f in records[i])
    ]
    assert removed and terminated and dropped
    assert removed[0] < terminated[0] < dropped[-1]
    assert migrate < removed[0]


def test_an_overrunning_image_probe_exits_non_zero(tmp_path):
    result, records, elapsed = _run(
        tmp_path, migrate="exit 1", probe="exec sleep 60",
        env={"RESTORE_PROBE_TIMEOUT": "2"},
    )

    assert result.returncode != 0, result.stdout + result.stderr
    assert elapsed < 20
    assert not _calls(records, "RENAME")
    assert "image probe timed out" in result.stderr

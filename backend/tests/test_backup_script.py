"""scripts/backup.sh, executed for real against a stub compose command.

Every assertion here is behavioural: the script runs, and the test looks at
what is left in the destination directory. That is the only way to catch this
class of bug, because the failure artefact is a *well-formed* gzip file with
the canonical name -- a text check on the script would have to restate the
fix to notice it was gone.

The stubs stand in for ``docker compose``. backup.sh reads COMPOSE_CMD, so no
container, daemon or database is involved.
"""
from __future__ import annotations

import gzip
import os
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP = REPO_ROOT / "scripts" / "backup.sh"

RETENTION_GLOB = "darkmem-*.sql.gz"

# What pg_dump writes last, and only once the dump has fully succeeded. Every
# dump in /root/darkmem-backups carries it inside the last 512 bytes (pg 17
# appends a \unrestrict line after it).
DUMP_TAIL = (
    "--\n"
    "-- PostgreSQL database dump complete\n"
    "--\n\n"
    "\\unrestrict 8kvVxEh2RfunUmIMTeMD2xzvdmSViN3iUM5sEn1PcqEZ2dw76TtkvKS087t25gb\n\n"
)
DUMP_BODY = "--\n-- PostgreSQL database dump\n--\n\nCREATE TABLE public.memories (id uuid);\n\n"


def _stub(tmp_path: Path, name: str, body: str) -> Path:
    stub = tmp_path / name
    stub.write_text("#!/usr/bin/env bash\n" + body)
    stub.chmod(0o755)
    return stub


def _good_compose(tmp_path: Path) -> Path:
    return _stub(tmp_path, "compose-ok.sh", f"cat <<'SQL'\n{DUMP_BODY}{DUMP_TAIL}SQL\n")


def _failing_compose(tmp_path: Path) -> Path:
    return _stub(
        tmp_path,
        "compose-fail.sh",
        'echo "Error response from daemon: container is not running" >&2\nexit 1\n',
    )


def _truncated_compose(tmp_path: Path) -> Path:
    """Exits 0, having written a dump that stops mid-stream."""
    return _stub(tmp_path, "compose-truncated.sh", f"cat <<'SQL'\n{DUMP_BODY}SQL\n")


def _run_backup(dest: Path, compose: Path, keep: str | None = None):
    env = {**os.environ, "COMPOSE_CMD": str(compose)}
    if keep is not None:
        env["BACKUP_KEEP"] = keep
    return subprocess.run(
        ["bash", str(BACKUP), str(dest)],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _dumps(dest: Path) -> list[Path]:
    return sorted(dest.glob(RETENTION_GLOB))


@pytest.fixture
def dest(tmp_path: Path) -> Path:
    out = tmp_path / "backups"
    out.mkdir()
    return out


def test_a_successful_dump_lands_under_the_retention_name(dest, tmp_path):
    """Without this the failure tests below could pass on a script that
    produces nothing at all."""
    result = _run_backup(dest, _good_compose(tmp_path))
    assert result.returncode == 0, result.stderr
    (dump,) = _dumps(dest)
    assert gzip.decompress(dump.read_bytes()).decode().endswith(DUMP_TAIL)
    assert list(dest.iterdir()) == [dump]


def test_a_failed_dump_leaves_no_file_behind(dest, tmp_path):
    """The redirection creates $OUT before pg_dump writes a byte and gzip -c
    exits 0 on empty input, so the aborted run leaves a well-formed 20-byte
    .sql.gz under the canonical name. Retention is name-and-mtime only, so
    that artefact is the newest file on disk and survives every later prune
    while real dumps age past KEEP."""
    result = _run_backup(dest, _failing_compose(tmp_path))
    assert result.returncode != 0, "a failed dump must still fail the run"
    assert list(dest.iterdir()) == [], "failed run left a file in the backup directory"


def test_a_truncated_dump_leaves_no_file_behind(dest, tmp_path):
    """The variant pipefail cannot see: the dump command exits 0 having
    written a stream that stops before pg_dump's completion marker."""
    result = _run_backup(dest, _truncated_compose(tmp_path))
    assert result.returncode != 0, "an incomplete dump must fail the run"
    assert list(dest.iterdir()) == []


def test_retention_never_deletes_a_real_dump_to_keep_a_failure_artefact(dest, tmp_path):
    """The consequence, end to end. With one real dump already on disk and
    room for two, a failed night followed by a good one must leave both real
    dumps -- not the newest artefact plus the newest dump."""
    old = dest / "darkmem-20200101-000000.sql.gz"
    old.write_bytes(gzip.compress((DUMP_BODY + DUMP_TAIL).encode()))
    os.utime(old, (0, 0))

    failed = _run_backup(dest, _failing_compose(tmp_path), keep="2")
    assert failed.returncode != 0
    # The dump filename is stamped to the second, so without this the good run
    # would overwrite the artefact instead of joining it on disk, and the test
    # would pass today for the wrong reason.
    time.sleep(1.1)

    result = _run_backup(dest, _good_compose(tmp_path), keep="2")
    assert result.returncode == 0, result.stderr

    survivors = _dumps(dest)
    assert old in survivors, "retention pruned a real dump"
    for dump in survivors:
        assert gzip.decompress(dump.read_bytes()), f"{dump.name} is an empty dump"

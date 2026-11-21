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
import tarfile
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
DUMP_BODY = (
    "--\n-- PostgreSQL database dump\n--\n\nCREATE TABLE public.memories (id uuid);\n\n"
    "COPY public.alembic_version (version_num) FROM stdin;\n0006\n\\.\n\n"
)
# A complete dump of some other database: the completion marker is there,
# the darkmem schema and its alembic stamp are not.
OTHER_DATABASE_BODY = "--\n-- PostgreSQL database dump\n--\n\nCREATE TABLE public.notes (id uuid);\n\n"


def _stub(tmp_path: Path, name: str, body: str) -> Path:
    stub = tmp_path / name
    stub.write_text("#!/usr/bin/env bash\n" + body)
    stub.chmod(0o755)
    return stub


def _good_compose(tmp_path: Path) -> Path:
    return _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=1)


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
    env = {
        **os.environ,
        "COMPOSE_CMD": str(compose),
        # Never the host's docker: the default ATTACHMENT_VOLUME is the live
        # production volume, and `docker run -v NAME` would reach it for real.
        "DOCKER_CMD": str(_docker_stub(compose.parent, _volume(compose.parent))),
        "ATTACHMENT_VOLUME": "test_attachment_data",
        "DARKMEM_IMAGE": "darkraise/darkmem:test",
    }
    if keep is not None:
        env["BACKUP_KEEP"] = keep
    return subprocess.run(
        ["bash", str(BACKUP), str(dest)],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
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
    assert _dumps(dest) == [dump]


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



def _seed_dumps(dest: Path, count: int) -> list[Path]:
    """Older real dumps, oldest first by mtime."""
    seeded = []
    for index in range(count):
        dump = dest / f"darkmem-202001{index + 1:02d}-000000.sql.gz"
        dump.write_bytes(gzip.compress((DUMP_BODY + DUMP_TAIL).encode()))
        os.utime(dump, (1000 + index, 1000 + index))
        seeded.append(dump)
    return seeded


def test_wrong_database_dump_triggers_no_prune(dest, tmp_path):
    older = _seed_dumps(dest, 14)
    wrong = _stub(tmp_path, "compose-wrong.sh", f"cat <<'SQL'\n{OTHER_DATABASE_BODY}{DUMP_TAIL}SQL\n")

    result = _run_backup(dest, wrong, keep="14")
    assert result.returncode != 0
    assert "CREATE TABLE public.memories" in result.stderr
    assert "COPY public.alembic_version" in result.stderr
    assert _dumps(dest) == older, "a dump of the wrong database pruned a real one"
    (suspect,) = dest.glob("*.suspect")
    assert suspect.name.startswith("darkmem-") and suspect.name.endswith(".sql.gz.suspect")
    assert gzip.decompress(suspect.read_bytes()).decode().startswith(OTHER_DATABASE_BODY)

    result = _run_backup(dest, _good_compose(tmp_path), keep="14")
    assert result.returncode == 0, result.stderr
    survivors = _dumps(dest)
    assert len(survivors) == 14
    assert older[0] not in survivors and older[1:] == [d for d in survivors if d in older]


def test_failed_dump_still_prunes_nothing(dest, tmp_path):
    older = _seed_dumps(dest, 14)
    result = _run_backup(dest, _failing_compose(tmp_path), keep="2")
    assert result.returncode != 0
    assert _dumps(dest) == older


# ── Task 7: the attachment tarball stage ─────────────────────────────

import socket  # noqa: E402

from app.services.attachment_manifest import COUNT_SQL, MANIFEST_SQL  # noqa: E402

TAR_GLOB = "darkmem-attachments-*.tar.gz"
MANIFEST_A = "a" * 64
MANIFEST_B = "b" * 64


def _tars(dest: Path) -> list[Path]:
    return sorted(dest.glob(TAR_GLOB))


def _attachment_compose(tmp_path: Path, *, manifest: str, rows: int) -> Path:
    """A compose stub that tells the three queries apart.

    The shipped stub answers every invocation with the dump body, which would
    make the "manifest" a multi-line SQL script and the gate meaningless.
    """
    body = (
        'for a in "$@"; do\n'
        '  case "$a" in\n'
        f"    *'count(*)'*) echo '{rows}'; exit 0 ;;\n"
        f"    *string_agg*) echo '{manifest}'; exit 0 ;;\n"
        "  esac\n"
        "done\n"
        f"cat <<'SQL'\n{DUMP_BODY}{DUMP_TAIL}SQL\n"
    )
    return _stub(tmp_path, "compose-attach.sh", body)


def _docker_stub(tmp_path: Path, volume_dir: Path | None) -> Path:
    """Stands in for `docker`. `volume inspect` fails when the fixture
    directory is absent, which is how a missing volume is simulated."""
    missing = "exit 1" if volume_dir is None else "exit 0"
    # A missing volume is one `docker run -v NAME` silently CREATES, so the
    # run branch archives an empty directory rather than failing. A stub that
    # failed at tar would let the inspect guard's test pass for the wrong
    # reason -- the member count, not the guard, would be what refused.
    if volume_dir is None:
        volume_dir = tmp_path / "autocreated-volume"
        volume_dir.mkdir(exist_ok=True)
    src = str(volume_dir)
    body = (
        'case "$1" in\n'
        f"  volume) {missing} ;;\n"
        "  run)\n"
        f"    exec tar -czvf - -C '{src}' --exclude='*.part' "
        "--exclude='./.staging' --ignore-failed-read "
        "--warning=no-file-changed .\n"
        "    ;;\n"
        "esac\n"
        "exit 0\n"
    )
    return _stub(tmp_path, "docker-stub.sh", body)


def _volume(tmp_path: Path, *, files: int = 1) -> Path:
    # exist_ok: `_run_backup` builds this on every call, and
    # `test_retention_never_deletes_a_real_dump_to_keep_a_failure_artefact`
    # runs twice against one tmp_path.
    store = tmp_path / "volume"
    (store / "ab").mkdir(parents=True, exist_ok=True)
    for index in range(files):
        (store / "ab" / f"file{index}").write_bytes(b"payload")
    return store


def _run_with_attachments(dest, compose, docker, *, keep=None, env=None):
    merged = {
        **os.environ,
        "COMPOSE_CMD": str(compose),
        "DOCKER_CMD": str(docker),
        "ATTACHMENT_VOLUME": "test_attachment_data",
        "DARKMEM_IMAGE": "darkraise/darkmem:test",
        **(env or {}),
    }
    if keep is not None:
        merged["BACKUP_ATTACHMENTS_KEEP"] = keep
    return subprocess.run(
        ["bash", str(BACKUP), str(dest)],
        env=merged, capture_output=True, text=True, timeout=180,
    )


def test_the_shell_carries_the_same_manifest_sql_as_the_module():
    """Two producers, one definition. A drift here is a manifest that never
    matches, which silently re-tars the whole volume every night."""
    script = BACKUP.read_text()
    assert " ".join(MANIFEST_SQL.split()) in " ".join(script.split())
    assert " ".join(COUNT_SQL.split()) in " ".join(script.split())


def test_a_changed_manifest_writes_a_tarball_and_a_sidecar(dest, tmp_path):
    result = _run_with_attachments(
        dest,
        _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=1),
        _docker_stub(tmp_path, _volume(tmp_path)),
    )
    assert result.returncode == 0, result.stderr

    (tarball,) = _tars(dest)
    assert (dest / f"{tarball.name}.manifest").read_text().strip() == MANIFEST_A
    assert len(_dumps(dest)) == 1
    assert not list(dest.glob("*.part"))
    # The name is a promise about the content: an empty or non-gzip archive
    # renamed into place would read as current on every later night.
    with tarfile.open(tarball, "r:gz") as archive:
        assert [m.name for m in archive.getmembers() if m.isfile()], "no members"


def test_an_unchanged_manifest_writes_no_second_tarball(dest, tmp_path):
    compose = _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=1)
    docker = _docker_stub(tmp_path, _volume(tmp_path))
    assert _run_with_attachments(dest, compose, docker).returncode == 0
    time.sleep(1.1)
    assert _run_with_attachments(dest, compose, docker).returncode == 0

    assert len(_tars(dest)) == 1
    assert len(_dumps(dest)) == 2


def test_a_moved_manifest_writes_a_second_tarball(dest, tmp_path):
    docker = _docker_stub(tmp_path, _volume(tmp_path))
    assert _run_with_attachments(
        dest, _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=1), docker
    ).returncode == 0
    time.sleep(1.1)
    assert _run_with_attachments(
        dest, _attachment_compose(tmp_path, manifest=MANIFEST_B, rows=1), docker
    ).returncode == 0

    assert len(_tars(dest)) == 2


def test_an_empty_volume_against_rows_fails_and_keeps_the_dump(dest, tmp_path):
    empty = tmp_path / "empty-volume"
    empty.mkdir()
    result = _run_with_attachments(
        dest,
        _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=4),
        _docker_stub(tmp_path, empty),
    )

    assert result.returncode != 0
    assert _tars(dest) == []
    assert len(_dumps(dest)) == 1, "the dump must survive an attachment failure"


def test_a_missing_volume_fails_even_when_the_table_is_empty(dest, tmp_path):
    """The inspect guard on its own. With rows present the member count would
    refuse an auto-created empty volume anyway, so only the empty-table case
    tells the guard apart from the count -- and only when the stage's own
    `set -e` is live, which it is not if the stage is called from `if !`."""
    result = _run_with_attachments(
        dest,
        _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=0),
        _docker_stub(tmp_path, None),
    )

    assert result.returncode != 0
    assert _tars(dest) == []
    assert len(_dumps(dest)) == 1


def test_a_missing_volume_fails_and_keeps_the_dump(dest, tmp_path):
    result = _run_with_attachments(
        dest,
        _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=1),
        _docker_stub(tmp_path, None),
    )

    assert result.returncode != 0
    assert _tars(dest) == []
    assert len(_dumps(dest)) == 1


def test_a_tar_diagnostic_is_not_counted_as_a_member(dest, tmp_path):
    """stderr carries tar's member listing AND its diagnostics. A unix socket
    is the one entry tar refuses for every user, root included (these tests
    run as root, where a chmod 000 file is still readable): tar writes
    `socket ignored` to stderr, mints no member and exits 0. A count that read
    that line as a member would rename an empty tarball onto the canonical
    name and write the real manifest beside it, after which every later night
    compares equal and skips."""
    store = tmp_path / "socket-volume"
    store.mkdir()
    # sun_path caps near 108 bytes; keep this name and the test's own short.
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(str(store / "s"))
    finally:
        sock.close()
    result = _run_with_attachments(
        dest,
        _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=1),
        _docker_stub(tmp_path, store),
    )

    assert result.returncode != 0
    assert _tars(dest) == []
    assert not list(dest.glob("*.manifest"))
    assert len(_dumps(dest)) == 1


def test_a_file_changed_under_tar_is_not_a_failure(dest, tmp_path):
    """tar exits 1 for "file changed as we read it", the expected outcome
    against a live volume the cleanup job may be unlinking from. Under
    `set -euo pipefail` an unhandled 1 would fail the backup nightly."""
    volume = _volume(tmp_path)
    docker = _stub(
        tmp_path,
        "docker-changed.sh",
        'case "$1" in\n'
        "  volume) exit 0 ;;\n"
        "  run)\n"
        f"    tar -czvf - -C '{volume}' .\n"
        "    exit 1\n"
        "    ;;\n"
        "esac\n"
        "exit 0\n",
    )

    result = _run_with_attachments(
        dest, _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=1), docker
    )

    assert result.returncode == 0, result.stderr
    assert len(_tars(dest)) == 1


def test_keep_zero_disables_the_tarball_prune(dest, tmp_path):
    """Same convention as the dump prune's KEEP=0, for a one-off manual run."""
    docker = _docker_stub(tmp_path, _volume(tmp_path))
    for manifest in (MANIFEST_A, MANIFEST_B, "c" * 64):
        assert _run_with_attachments(
            dest,
            _attachment_compose(tmp_path, manifest=manifest, rows=1),
            docker,
            keep="0",
        ).returncode == 0
        time.sleep(1.1)

    assert len(_tars(dest)) == 3


def test_tarball_retention_prunes_sidecars_and_spares_dumps(dest, tmp_path):
    docker = _docker_stub(tmp_path, _volume(tmp_path))
    for manifest in (MANIFEST_A, MANIFEST_B, "c" * 64):
        assert _run_with_attachments(
            dest,
            _attachment_compose(tmp_path, manifest=manifest, rows=1),
            docker,
            keep="2",
        ).returncode == 0
        time.sleep(1.1)

    assert len(_tars(dest)) == 2
    assert len(list(dest.glob("*.manifest"))) == 2
    assert len(_dumps(dest)) == 3

"""The off-host ship: dump, encrypt, deliver, read back, prune.

The dump half is tested against fake `pg_dump` argv rather than a real
server, because what the code has to get right is not the SQL: it is the
completion-marker discipline. `pg_dump` can exit 0 having written a
truncated stream, and `gzip` compresses a truncated stream perfectly
happily, so exit status alone yields a well-formed archive that restores
into a half-populated database. `scripts/backup.sh` learned that on the
host side; this is the same check one layer in, applied to the *raw*
stream so nothing has to be decompressed to run it.

The `age` round-trip skips where the binary is absent, which is every
non-container host that has not installed it. It is not skipped in the
image: `tests/test_deployment_artifact.py` asserts the package is there.
"""
from __future__ import annotations

import gzip
import shutil
import subprocess

import pytest

from app.services import backup_ship


def _fake_dump(monkeypatch, script: str) -> None:
    """Replace the pg_dump argv with a shell one-liner writing `script` to stdout."""
    monkeypatch.setattr(backup_ship, "_dump_argv", lambda: ["sh", "-c", script])


async def test_dump_refuses_a_stream_without_the_completion_marker(
    tmp_path, monkeypatch
):
    _fake_dump(monkeypatch, "printf 'CREATE TABLE x;\\n'")
    with pytest.raises(backup_ship.DumpIncomplete):
        await backup_ship.run_dump(dest_dir=tmp_path)
    assert not list(tmp_path.glob("*.sql.gz"))
    assert not list(tmp_path.glob("*.part"))


async def test_dump_refuses_a_nonzero_exit(tmp_path, monkeypatch):
    _fake_dump(
        monkeypatch,
        "printf -- '-- PostgreSQL database dump complete\\n'; "
        "echo 'connection refused' >&2; exit 1",
    )
    with pytest.raises(backup_ship.DumpIncomplete) as exc:
        await backup_ship.run_dump(dest_dir=tmp_path)
    assert "connection refused" in str(exc.value)
    assert not list(tmp_path.glob("*.part"))


async def test_dump_renames_only_on_marker(tmp_path, monkeypatch):
    _fake_dump(
        monkeypatch,
        "printf 'CREATE TABLE x;\\n-- PostgreSQL database dump complete\\n'",
    )
    out = await backup_ship.run_dump(dest_dir=tmp_path)
    assert out.name.startswith(backup_ship.JOB_PREFIX)
    assert out.name.endswith(".sql.gz")
    assert b"dump complete" in gzip.decompress(out.read_bytes())
    assert not list(tmp_path.glob("*.part"))


async def test_dump_finds_the_marker_across_a_chunk_boundary(tmp_path, monkeypatch):
    """The marker is checked against a rolling tail of the raw stream, so a
    dump larger than one read chunk must still pass. A naive per-chunk check
    passes this test only by accident of chunk size; the padding here is an
    order of magnitude past it."""
    _fake_dump(
        monkeypatch,
        "head -c 3000000 /dev/zero | tr '\\0' 'a'; "
        "printf -- '\\n-- PostgreSQL database dump complete\\n'",
    )
    out = await backup_ship.run_dump(dest_dir=tmp_path)
    assert out.exists()


async def test_dump_refuses_an_unwritable_directory(tmp_path, monkeypatch):
    """Review B-1's failure, named at the source rather than surfacing as a
    truncated `.part` at 04:30."""
    _fake_dump(monkeypatch, "printf -- '-- PostgreSQL database dump complete\\n'")
    missing = tmp_path / "not-created-by-the-operator"
    with pytest.raises(backup_ship.DumpDirectoryUnusable) as exc:
        await backup_ship.run_dump(dest_dir=missing)
    assert str(missing) in str(exc.value)


def test_dump_argv_carries_the_restore_compatible_flags():
    """`--clean --if-exists` matches scripts/backup.sh, so scripts/restore.sh
    replays either producer's dump identically."""
    argv = backup_ship._dump_argv()
    assert argv[0] == "pg_dump"
    assert "--clean" in argv and "--if-exists" in argv


def test_the_password_never_reaches_the_argv(monkeypatch):
    """PGPASSWORD rides the subprocess env; an argv password is world-readable
    in `ps` for the life of the dump. The password is monkeypatched to a value
    that cannot collide with the user or database name, which in the defaults
    are all the same string."""
    from app.config import settings

    monkeypatch.setattr(settings, "db_password", "s3cret-not-in-argv")
    assert "s3cret-not-in-argv" not in " ".join(backup_ship._dump_argv())


async def test_encrypt_round_trips_with_age(tmp_path):
    if shutil.which("age") is None or shutil.which("age-keygen") is None:
        pytest.skip("age not installed on this host")
    keyfile = tmp_path / "identity.txt"
    subprocess.run(
        ["age-keygen", "-o", str(keyfile)], check=True, capture_output=True
    )
    recipient = subprocess.run(
        ["age-keygen", "-y", str(keyfile)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    plain = tmp_path / "snapshot.sql.gz"
    payload = b"the bytes that must survive the round trip" * 100
    plain.write_bytes(payload)

    cipher = await backup_ship.encrypt(plain, recipient)
    assert cipher.name.endswith(".sql.gz.age")
    # The plaintext must not linger beside the ciphertext: a destination that
    # demanded encryption gets no unencrypted twin on local disk.
    assert not plain.exists()

    back = subprocess.run(
        ["age", "-d", "-i", str(keyfile), str(cipher)],
        check=True,
        capture_output=True,
    ).stdout
    assert back == payload


async def test_encrypt_refuses_a_bad_recipient(tmp_path):
    if shutil.which("age") is None:
        pytest.skip("age not installed on this host")
    plain = tmp_path / "snapshot.sql.gz"
    plain.write_bytes(b"x")
    with pytest.raises(backup_ship.EncryptFailed):
        await backup_ship.encrypt(plain, "not-a-recipient")
    # A failed encrypt leaves the plaintext alone rather than deleting the
    # only copy of the dump.
    assert plain.exists()


async def test_sha256_file_matches_hashlib(tmp_path):
    import hashlib

    f = tmp_path / "blob"
    f.write_bytes(b"a" * 200_000)
    assert await backup_ship.sha256_file(f) == hashlib.sha256(b"a" * 200_000).hexdigest()

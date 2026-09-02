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


# ---------------------------------------------------------------------------
# Task 4: the destination protocol, the local destination, journal and prune
# ---------------------------------------------------------------------------

import asyncio  # noqa: E402
from pathlib import Path  # noqa: E402

from sqlalchemy import text as sa_text  # noqa: E402

from app.services import backup_config as bc  # noqa: E402

LOCAL = {"name": "local", "kind": "local", "enabled": True, "retention_keep": 14}


def _touch(path, *, mtime: float) -> None:
    path.write_bytes(b"x")
    import os

    os.utime(path, (mtime, mtime))


async def test_prune_touches_only_the_job_prefix(tmp_path):
    """A systemd-style dump sitting in the same directory -- operator error the
    two-producer design says must be survivable -- is never deleted, whatever
    its age. Different directories is the real separation; the prefix is the
    belt, and this is the test that holds the belt."""
    _touch(tmp_path / "darkmem-20250101-000000.sql.gz", mtime=1_000_000)
    for i in range(5):
        _touch(
            tmp_path / f"darkmem-app-2026010{i}-000000.sql.gz.age",
            mtime=2_000_000 + i,
        )
    dest = backup_ship.LocalDestination(name="local", directory=tmp_path)

    deleted = await dest.prune(keep=2)

    assert len(deleted) == 3
    assert (tmp_path / "darkmem-20250101-000000.sql.gz").exists()
    survivors = sorted(p.name for p in tmp_path.glob("darkmem-app-*"))
    assert survivors == [
        "darkmem-app-20260103-000000.sql.gz.age",
        "darkmem-app-20260104-000000.sql.gz.age",
    ]


async def test_prune_never_matches_part_files(tmp_path):
    """An in-flight `.part` belongs to a dump that is still being written.
    Deleting it destroys the run that is producing it."""
    part = tmp_path / "darkmem-app-20260101-000000.sql.gz.part"
    _touch(part, mtime=2_000_000)
    dest = backup_ship.LocalDestination(name="local", directory=tmp_path)

    assert await dest.prune(keep=0) == []
    assert part.exists()
    assert [s.name for s in await dest.list_snapshots()] == []


async def test_local_read_back_hashes_what_actually_landed(tmp_path):
    blob = tmp_path / "darkmem-app-20260101-000000.sql.gz"
    blob.write_bytes(b"contents")
    dest = backup_ship.LocalDestination(name="local", directory=tmp_path)
    assert await dest.read_back_sha256(blob.name) == await backup_ship.sha256_file(blob)


class _FakeDestination:
    """A destination whose every call is observable and whose read-back can lie."""

    def __init__(self, name, *, sha=None, fail_ship=False, retention_keep=14):
        self.name = name
        self.retention_keep = retention_keep
        self._sha = sha
        self._fail_ship = fail_ship
        self.shipped: list[str] = []
        self.pruned_with: list[int] = []

    async def ship(self, local_path):
        if self._fail_ship:
            raise RuntimeError("the NAS is unplugged")
        self.shipped.append(local_path.name)

    async def read_back_sha256(self, name):
        if self._sha is not None:
            return self._sha
        return await backup_ship.sha256_file(self._local)

    async def list_snapshots(self):
        return []

    async def prune(self, keep):
        self.pruned_with.append(keep)
        return []


async def _dump_into(tmp_path, monkeypatch):
    """Stand a finished dump in `tmp_path` and point the module at it."""
    _fake_dump(
        monkeypatch,
        "printf 'CREATE TABLE x;\\n-- PostgreSQL database dump complete\\n'",
    )
    monkeypatch.setattr(backup_ship, "DUMP_DIR", tmp_path)


async def _payloads(session, event_type):
    """`events` has no ORM model -- every reader is raw SQL over the partitioned
    parent, so the tests read it the way production does."""
    rows = (
        await session.execute(
            sa_text(
                "SELECT payload FROM events WHERE event_type = :t "
                "AND object_type = 'system' ORDER BY created_at, id"
            ),
            {"t": event_type},
        )
    ).scalars().all()
    return rows


async def test_ship_all_verifies_and_journals(
    session, session_factory, tmp_path, monkeypatch
):
    await _dump_into(tmp_path, monkeypatch)
    await bc.save_destinations(
        session, {"destinations": [{**LOCAL, "name": "disk"}]}
    )

    summary = await backup_ship.ship_all(session_factory)

    assert summary["shipped"] == 1
    assert summary["verify_failed"] == []
    # `dump` names the snapshot this run produced; encryption is per-destination
    # packaging, and the artefact each destination actually received is named in
    # its own journal row.
    assert summary["dump"].startswith(backup_ship.JOB_PREFIX)
    assert summary["dump"].endswith(".sql.gz")

    rows = await _payloads(session, "backup_shipped")
    assert len(rows) == 1
    payload = rows[0]
    assert payload["destination"] == "disk"
    assert payload["file"] == summary["dump"]  # unencrypted: artefact is the dump
    assert len(payload["sha256"]) == 64
    assert payload["bytes"] > 0


async def test_ship_all_journals_a_read_back_mismatch(
    session, session_factory, tmp_path, monkeypatch
):
    """Uploaded is not restorable: a destination that hands back a different
    hash than we sent is a verify failure, not a successful ship."""
    await _dump_into(tmp_path, monkeypatch)
    await bc.save_destinations(
        session, {"destinations": [{**LOCAL, "name": "disk"}]}
    )
    liar = _FakeDestination("disk", sha="0" * 64)
    monkeypatch.setattr(backup_ship, "build_destination", lambda cfg: liar)

    summary = await backup_ship.ship_all(session_factory)

    assert summary["shipped"] == 0
    assert summary["verify_failed"] == ["disk"]
    rows = await _payloads(session, "backup_verify_failed")
    assert len(rows) == 1
    assert rows[0]["got"] == "0" * 64
    assert rows[0]["expected"] != "0" * 64
    # A destination that failed verification is still pruned to its retention:
    # the failure is about this snapshot, not about the ones already there.
    assert liar.pruned_with == [14]


async def test_one_failing_destination_does_not_stop_the_others(
    session, session_factory, tmp_path, monkeypatch
):
    await _dump_into(tmp_path, monkeypatch)
    await bc.save_destinations(
        session,
        {
            "destinations": [
                {**LOCAL, "name": "broken"},
                {**LOCAL, "name": "working"},
            ]
        },
    )
    broken = _FakeDestination("broken", fail_ship=True)
    working = _FakeDestination("working")

    def _build(cfg):
        dest = broken if cfg.name == "broken" else working
        dest._local = backup_ship.DUMP_DIR / _the_dump(tmp_path)
        return dest

    monkeypatch.setattr(backup_ship, "build_destination", _build)

    summary = await backup_ship.ship_all(session_factory)

    assert summary["shipped"] == 1
    assert summary["verify_failed"] == ["broken"]
    assert working.shipped, "the second destination never ran"
    rows = await _payloads(session, "backup_verify_failed")
    assert "unplugged" in rows[0]["error"]


def _the_dump(directory):
    return next(
        p.name for p in directory.glob(f"{backup_ship.JOB_PREFIX}*.sql.gz")
    )


async def test_disabled_destinations_are_skipped(
    session, session_factory, tmp_path, monkeypatch
):
    await _dump_into(tmp_path, monkeypatch)
    await bc.save_destinations(
        session,
        {"destinations": [{**LOCAL, "name": "off", "enabled": False}]},
    )

    summary = await backup_ship.ship_all(session_factory)

    assert summary["shipped"] == 0
    # No enabled destination means no dump at all: taking one would spend the
    # I/O of a full database read to produce a file nobody asked for.
    assert summary["dump"] is None
    assert not list(tmp_path.glob("*.sql.gz"))


async def test_a_recipient_encrypts_and_leaves_no_plaintext(
    session, session_factory, tmp_path, monkeypatch
):
    if shutil.which("age") is None or shutil.which("age-keygen") is None:
        pytest.skip("age not installed on this host")
    keyfile = tmp_path / "id.txt"
    subprocess.run(["age-keygen", "-o", str(keyfile)], check=True, capture_output=True)
    recipient = subprocess.run(
        ["age-keygen", "-y", str(keyfile)], check=True, capture_output=True, text=True
    ).stdout.strip()

    dumps = tmp_path / "dumps"
    dumps.mkdir()
    await _dump_into(dumps, monkeypatch)
    await bc.save_destinations(
        session,
        {
            "destinations": [
                {**LOCAL, "name": "disk", "age_recipient": recipient}
            ]
        },
    )

    summary = await backup_ship.ship_all(session_factory)

    assert summary["shipped"] == 1
    assert list(dumps.glob("*.sql.gz.age"))
    assert not list(dumps.glob("*.sql.gz")), "the plaintext lingered beside the cipher"


# ---------------------------------------------------------------------------
# Task 5: the ssh destination
#
# Every argv is unit-tested without a network. There is no sshd fixture on
# this host, so no end-to-end test against a real server exists -- the gap is
# stated here rather than papered over: what is proven below is that the
# commands are built correctly and that the pinned host key and the .part
# discipline reach the wire, not that a real transfer succeeds.
# ---------------------------------------------------------------------------

import os  # noqa: E402
import stat as stat_mod  # noqa: E402


SSH_CFG = bc.DestinationConfig.model_validate(
    {
        "name": "nas",
        "kind": "ssh",
        "retention_keep": 3,
        "age_recipient": "age1qqqqexamplerecipient",
        "ssh": {
            "host": "192.0.2.10",
            "port": 2222,
            "user": "backup",
            "remote_dir": "/srv/darkmem",
            "host_key": "192.0.2.10 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5examplekey",
            "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nexample\n",
        },
    }
)


def test_ssh_pins_the_host_key_and_never_trusts_on_first_use(tmp_path):
    dest = backup_ship.SshDestination(SSH_CFG)
    argv = dest._ssh_base_argv(tmp_path)

    assert "-o" in argv
    joined = " ".join(argv)
    assert "StrictHostKeyChecking=yes" in joined
    assert f"UserKnownHostsFile={tmp_path / 'known_hosts'}" in joined
    # accept-new is trust-on-first-use with a nicer name; the first connection
    # is exactly the one worth intercepting.
    assert "accept-new" not in joined
    assert "StrictHostKeyChecking=no" not in joined

    known = (tmp_path / "known_hosts").read_text()
    assert known.strip() == SSH_CFG.ssh.host_key


def test_ssh_identity_file_is_private_to_this_process(tmp_path):
    dest = backup_ship.SshDestination(SSH_CFG)
    dest._ssh_base_argv(tmp_path)
    identity = tmp_path / "identity"
    assert identity.read_text() == SSH_CFG.ssh.private_key
    mode = stat_mod.S_IMODE(os.stat(identity).st_mode)
    assert mode == 0o600, f"identity file is {oct(mode)}; ssh refuses a loose one"


def test_ssh_ship_uploads_to_a_part_then_renames(tmp_path, monkeypatch):
    """The .part discipline crosses the wire too: a torn upload is never
    listed as a snapshot, so a half-transferred file can never be selected as
    the newest good one by a restore."""
    calls = []

    async def _run(argv, **kwargs):
        calls.append(argv)
        return b""

    dest = backup_ship.SshDestination(SSH_CFG)
    monkeypatch.setattr(dest, "_run", _run)
    blob = tmp_path / "darkmem-app-20260101-000000.sql.gz.age"
    blob.write_bytes(b"x")

    asyncio.run(dest.ship(blob))

    upload = next(c for c in calls if c[0] == "scp")
    assert upload[-1].endswith(f":/srv/darkmem/{blob.name}.part")
    assert "backup@192.0.2.10" in upload[-1]
    rename = next(c for c in calls if c[0] == "ssh")
    assert f"/srv/darkmem/{blob.name}.part" in " ".join(rename)
    assert f"/srv/darkmem/{blob.name}" in " ".join(rename)
    assert calls.index(upload) < calls.index(rename)


def test_ssh_read_back_streams_the_remote_file_into_a_local_hash(monkeypatch):
    """Not a remote `sha256sum`: rule 2 is about what we can read back, and a
    remote checksum proves only that the remote agrees with itself."""
    import hashlib

    payload = b"the bytes that landed" * 500

    async def _run(argv, **kwargs):
        assert argv[0] == "ssh"
        assert "cat" in " ".join(argv)
        return payload

    dest = backup_ship.SshDestination(SSH_CFG)
    monkeypatch.setattr(dest, "_run", _run)

    got = asyncio.run(dest.read_back_sha256("darkmem-app-20260101-000000.sql.gz.age"))
    assert got == hashlib.sha256(payload).hexdigest()


def test_ssh_prune_filters_the_prefix_and_deletes_beyond_keep(monkeypatch):
    listing = b"\n".join(
        [
            b"darkmem-20250101-000000.sql.gz",  # the systemd producer's
            b"darkmem-app-20260101-000000.sql.gz.age",
            b"darkmem-app-20260102-000000.sql.gz.age",
            b"darkmem-app-20260103-000000.sql.gz.age",
            b"darkmem-app-20260104-000000.sql.gz.age",
            b"darkmem-app-20260105-000000.sql.gz.age.part",  # in flight
            b"README",
        ]
    )
    removed = []

    async def _run(argv, **kwargs):
        joined = " ".join(argv)
        if "ls" in joined:
            return listing
        removed.append(joined)
        return b""

    dest = backup_ship.SshDestination(SSH_CFG)
    monkeypatch.setattr(dest, "_run", _run)

    deleted = asyncio.run(dest.prune(keep=2))

    assert deleted == [
        "darkmem-app-20260102-000000.sql.gz.age",
        "darkmem-app-20260101-000000.sql.gz.age",
    ]
    assert not any("darkmem-20250101" in r for r in removed)
    assert not any(".part" in r for r in removed)
    assert not any("README" in r for r in removed)


def test_ssh_prune_refuses_a_dangerous_remote_dir():
    """`rm` beyond a keep count, rooted at / or at an empty string, is not a
    retention pass."""
    for bad in ("", "/", "   "):
        cfg = SSH_CFG.model_copy(deep=True)
        cfg.ssh.remote_dir = bad
        with pytest.raises(ValueError):
            asyncio.run(backup_ship.SshDestination(cfg).prune(keep=1))


def test_ssh_key_material_is_removed_after_every_operation(tmp_path, monkeypatch):
    seen = {}

    async def _run(argv, **kwargs):
        # Capture the scratch directory the operation built its argv from.
        for token in argv:
            if "UserKnownHostsFile=" in str(token):
                seen["dir"] = Path(str(token).split("=", 1)[1]).parent
        return b""

    dest = backup_ship.SshDestination(SSH_CFG)
    monkeypatch.setattr(dest, "_run", _run)
    blob = tmp_path / "darkmem-app-20260101-000000.sql.gz.age"
    blob.write_bytes(b"x")

    asyncio.run(dest.ship(blob))

    assert seen["dir"] and not seen["dir"].exists(), (
        "the private key outlived the operation that needed it"
    )


def test_build_destination_serves_the_ssh_kind():
    assert isinstance(backup_ship.build_destination(SSH_CFG), backup_ship.SshDestination)


# ---------------------------------------------------------------------------
# Task 6: the S3 destination
#
# The client is injected, so nothing here reaches a network. What is worth
# pinning is the key layout, the pagination loop (a bucket past one page must
# not prune from a truncated listing) and that read-back streams the object's
# body rather than trusting any ETag.
# ---------------------------------------------------------------------------

import io  # noqa: E402


S3_CFG = bc.DestinationConfig.model_validate(
    {
        "name": "r2",
        "kind": "s3",
        "retention_keep": 2,
        "age_recipient": "age1qqqqexamplerecipient",
        "s3": {
            "endpoint_url": "https://x.r2.cloudflarestorage.com",
            "bucket": "snapshots",
            "prefix": "darkmem/",
            "region": "auto",
            "access_key_id": "AK",
            "secret_access_key": "SK",
        },
    }
)


class _FakeS3:
    def __init__(self, objects=None, *, page_size=1000):
        self.objects = dict(objects or {})
        self.uploaded = []
        self.deleted = []
        self.list_calls = 0
        self._page_size = page_size

    def upload_file(self, filename, bucket, key):
        self.uploaded.append((filename, bucket, key))
        self.objects[key] = open(filename, "rb").read()

    def get_object(self, Bucket, Key):  # noqa: N803 - boto3's own casing
        return {"Body": io.BytesIO(self.objects[Key])}

    def list_objects_v2(self, **kwargs):
        self.list_calls += 1
        keys = sorted(k for k in self.objects if k.startswith(kwargs.get("Prefix", "")))
        token = kwargs.get("ContinuationToken")
        start = keys.index(token) if token else 0
        page = keys[start : start + self._page_size]
        out = {
            "Contents": [
                {"Key": k, "Size": len(self.objects[k]), "LastModified": None}
                for k in page
            ]
        }
        if start + self._page_size < len(keys):
            out["IsTruncated"] = True
            out["NextContinuationToken"] = keys[start + self._page_size]
        return out

    def delete_object(self, Bucket, Key):  # noqa: N803
        self.deleted.append(Key)
        self.objects.pop(Key, None)


def _s3(fake) -> "backup_ship.S3Destination":
    return backup_ship.S3Destination(S3_CFG, client_factory=lambda: fake)


async def test_s3_ship_uses_the_prefixed_key_layout(tmp_path):
    fake = _FakeS3()
    blob = tmp_path / "darkmem-app-20260101-000000.sql.gz.age"
    blob.write_bytes(b"payload")

    await _s3(fake).ship(blob)

    assert fake.uploaded == [(str(blob), "snapshots", f"darkmem/{blob.name}")]


async def test_s3_read_back_streams_the_body(tmp_path):
    import hashlib

    payload = b"the object as it actually landed" * 400
    fake = _FakeS3({"darkmem/darkmem-app-20260101-000000.sql.gz.age": payload})

    got = await _s3(fake).read_back_sha256("darkmem-app-20260101-000000.sql.gz.age")

    assert got == hashlib.sha256(payload).hexdigest()


async def test_s3_listing_walks_every_page(tmp_path):
    """A bucket past one page must not prune from a truncated listing: the
    newest keep would be computed off page one alone and everything real would
    look like the tail."""
    objects = {
        f"darkmem/darkmem-app-2026{m:02d}01-000000.sql.gz.age": b"x"
        for m in range(1, 13)
    }
    fake = _FakeS3(objects, page_size=5)

    snapshots = await _s3(fake).list_snapshots()

    assert len(snapshots) == 12
    assert fake.list_calls == 3


async def test_s3_prune_keeps_the_newest_and_ignores_foreign_keys():
    objects = {
        "darkmem/darkmem-20250101-000000.sql.gz": b"x",  # the systemd producer's
        "darkmem/README": b"x",
        "darkmem/darkmem-app-20260101-000000.sql.gz.age": b"x",
        "darkmem/darkmem-app-20260102-000000.sql.gz.age": b"x",
        "darkmem/darkmem-app-20260103-000000.sql.gz.age": b"x",
        "darkmem/darkmem-app-20260104-000000.sql.gz.age.part": b"x",
    }
    fake = _FakeS3(objects)

    deleted = await _s3(fake).prune(keep=2)

    assert deleted == ["darkmem-app-20260101-000000.sql.gz.age"]
    assert fake.deleted == ["darkmem/darkmem-app-20260101-000000.sql.gz.age"]


def test_build_destination_serves_the_s3_kind():
    assert isinstance(backup_ship.build_destination(S3_CFG), backup_ship.S3Destination)


def test_the_default_client_factory_carries_the_configured_endpoint(monkeypatch):
    """R2, B2 and MinIO are AWS-compatible only through `endpoint_url`; a
    client built without it silently talks to AWS."""
    seen = {}

    def _fake_client(service, **kwargs):
        seen.update(kwargs, service=service)
        return object()

    import boto3

    monkeypatch.setattr(boto3, "client", _fake_client)
    backup_ship.S3Destination(S3_CFG)._client()

    assert seen["service"] == "s3"
    assert seen["endpoint_url"] == "https://x.r2.cloudflarestorage.com"
    assert seen["region_name"] == "auto"
    assert seen["aws_access_key_id"] == "AK"
    assert seen["aws_secret_access_key"] == "SK"

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
import json
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
    """A destination whose every call is observable and whose read-back can lie.

    `ship` remembers each artefact by name so `read_back_sha256` can hash the
    one it is asked about: a run now ships a dump and a tarball, and one stored
    path would make the second read-back hash the first artefact.
    """

    def __init__(self, name, *, sha=None, fail_ship=False, retention_keep=14,
                 attachments_retention_keep=3, holds=()):
        self.name = name
        self.retention_keep = retention_keep
        self.attachments_retention_keep = attachments_retention_keep
        self._sha = sha
        self._fail_ship = fail_ship
        self._holds = list(holds)
        self._paths: dict[str, object] = {}
        self.shipped: list[str] = []
        self.pruned_with: list[int] = []
        self.pruned_families: list[tuple[int, str]] = []
        self.timeouts: list[float | None] = []

    async def ship(self, local_path, *, timeout=None):
        if self._fail_ship:
            raise RuntimeError("the NAS is unplugged")
        self.timeouts.append(timeout)
        self._paths[local_path.name] = local_path
        self.shipped.append(local_path.name)

    async def read_back_sha256(self, name, *, timeout=None):
        if self._sha is not None:
            return self._sha
        return await backup_ship.sha256_file(self._paths[name])

    async def list_snapshots(self, family=None):
        family = family or backup_ship.DUMPS
        return [
            backup_ship.SnapshotInfo(
                name=n, size=0, modified_at=family.stamp_datetime(n)
            )
            for n in self._holds
            if family.matches(n)
        ]

    async def prune(self, keep, family=None):
        family = family or backup_ship.DUMPS
        self.pruned_with.append(keep)
        self.pruned_families.append((keep, family.prefix))
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
    _fake_archive(monkeypatch)

    summary = await backup_ship.ship_all(session_factory)

    assert summary["shipped"] == 1
    assert summary["verify_failed"] == []
    # `dump` names the snapshot this run produced; encryption is per-destination
    # packaging, and the artefact each destination actually received is named in
    # its own journal row.
    assert summary["dump"].startswith(backup_ship.JOB_PREFIX)
    assert summary["dump"].endswith(".sql.gz")

    rows = await _payloads(session, "backup_shipped")
    assert len(rows) == 2
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
    _fake_archive(monkeypatch)

    summary = await backup_ship.ship_all(session_factory)

    assert summary["shipped"] == 0
    assert summary["verify_failed"] == ["disk"]
    rows = await _payloads(session, "backup_verify_failed")
    assert len(rows) == 2
    assert rows[0]["got"] == "0" * 64
    assert rows[0]["expected"] != "0" * 64
    # A destination that failed verification is still pruned to its retention:
    # the failure is about this snapshot, not about the ones already there.
    assert liar.pruned_with == [14, 3]


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
        return broken if cfg.name == "broken" else working

    monkeypatch.setattr(backup_ship, "build_destination", _build)
    _fake_archive(monkeypatch)

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
    _fake_archive(monkeypatch)

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
    _fake_archive(monkeypatch)

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


# ---------------------------------------------------------------------------
# Task 7: the job
# ---------------------------------------------------------------------------


async def test_the_runner_hands_its_summary_to_the_run_record(monkeypatch):
    """The summary is the run record's whole value: a nightly ship that
    reported only "ok" would tell an operator nothing about which destination
    verified and which one is quietly holding a corrupt snapshot."""
    from sqlalchemy import text as _text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import settings
    from app.services.job_registry import Job, JobRegistry
    from app.services.job_runners import make_backup_ship_runner

    summary = {"dump": "darkmem-app-x.sql.gz", "shipped": 2, "verify_failed": []}

    async def _fake_ship_all(session_factory):
        return summary

    monkeypatch.setattr(backup_ship, "ship_all", _fake_ship_all)

    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    registry = JobRegistry(factory)
    registry.register(
        Job(
            key=backup_ship.BACKUP_SHIP_JOB_KEY,
            display_name="Backup Ship",
            description="d",
            default_cron="30 4 * * *",
            min_interval_seconds=3600,
            runner=make_backup_ship_runner(None, factory),
        )
    )
    try:
        cfg = await registry.trigger(backup_ship.BACKUP_SHIP_JOB_KEY)
        assert cfg.last_status == "ok"
        async with factory() as s:
            detail = (
                await s.execute(
                    _text(
                        "SELECT detail FROM job_runs WHERE job_key = :k "
                        "ORDER BY started_at DESC LIMIT 1"
                    ),
                    {"k": backup_ship.BACKUP_SHIP_JOB_KEY},
                )
            ).scalar_one()
        assert detail == summary
    finally:
        async with factory() as s:
            await s.execute(
                _text("DELETE FROM job_runs WHERE job_key = :k"),
                {"k": backup_ship.BACKUP_SHIP_JOB_KEY},
            )
            await s.execute(
                _text("DELETE FROM config WHERE key = :k"),
                {"k": f"job:{backup_ship.BACKUP_SHIP_JOB_KEY}"},
            )
            await s.commit()
        await registry.stop_all()
        await engine.dispose()


def test_the_job_is_registered_an_hour_clear_of_the_systemd_timer():
    """Nothing serialises the two producers -- different processes, and the
    per-job lock binds in-process only -- so the gap is the whole mitigation
    and belongs under test rather than in a comment alone."""
    import ast

    source = ast.parse(Path("app/main.py").read_text())
    crons = [
        kw.value.value
        for node in ast.walk(source)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Job"
        for kw in node.keywords
        if kw.arg == "default_cron"
        and any(
            k.arg == "key"
            and isinstance(k.value, ast.Name)
            and k.value.id == "BACKUP_SHIP_JOB_KEY"
            for k in node.keywords
        )
    ]
    assert crons == ["30 4 * * *"], crons


# ---------------------------------------------------------------------------
# Increment 7: the worker destination, tested against the real receiver
#
# Not a fake. The whole point of the `worker` kind is that it talks to
# `app.worker_receiver`, so the tests below drive that module's own ASGI app
# over httpx -- a hand-written stub would let the two drift and each keep
# passing its own suite.
# ---------------------------------------------------------------------------

import httpx  # noqa: E402


RECEIVER_TOKEN = "a-receiver-token-of-at-least-32-characters"

WORKER_CFG = bc.DestinationConfig.model_validate(
    {
        "name": "attic",
        "kind": "worker",
        "retention_keep": 2,
        "age_recipient": "age1qqqqexamplerecipient",
        "worker": {"url": "http://receiver", "token": RECEIVER_TOKEN},
    }
)


@pytest.fixture
def receiver_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("RECEIVER_TOKEN", RECEIVER_TOKEN)
    monkeypatch.setenv("RECEIVER_DIR", str(tmp_path))
    return tmp_path


def _worker_destination():
    from app import worker_receiver

    def _client_factory():
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=worker_receiver.app),
            base_url=WORKER_CFG.worker.url,
            timeout=30,
        )

    return backup_ship.WorkerDestination(WORKER_CFG, client_factory=_client_factory)


async def test_worker_ship_and_read_back_agree_with_the_local_hash(
    receiver_dir, tmp_path,
):
    blob = tmp_path / "darkmem-app-20260101-000000.sql.gz.age"
    payload = b"ciphertext as the receiver will hold it" * 300
    blob.write_bytes(payload)
    dest = _worker_destination()

    await dest.ship(blob)

    assert (receiver_dir / blob.name).read_bytes() == payload
    assert await dest.read_back_sha256(blob.name) == await backup_ship.sha256_file(blob)


async def test_worker_ship_sends_the_bearer(receiver_dir, tmp_path):
    """Without it every verb 401s, and a ship that silently could not
    authenticate would look identical to one that had nowhere to go."""
    blob = tmp_path / "darkmem-app-20260101-000000.sql.gz.age"
    blob.write_bytes(b"x")
    bad = WORKER_CFG.model_copy(deep=True)
    bad.worker.token = "wrong-token-but-still-long-enough-here"

    from app import worker_receiver

    dest = backup_ship.WorkerDestination(
        bad,
        client_factory=lambda: httpx.AsyncClient(
            transport=httpx.ASGITransport(app=worker_receiver.app),
            base_url=bad.worker.url,
        ),
    )
    with pytest.raises(RuntimeError) as exc:
        await dest.ship(blob)
    assert "401" in str(exc.value)


async def test_worker_list_and_prune_walk_the_receiver(receiver_dir, tmp_path):
    for stamp in ("20260101", "20260102", "20260103"):
        (receiver_dir / f"darkmem-app-{stamp}-000000.sql.gz.age").write_bytes(b"x")
    # Neither of these is a snapshot: one is in flight, one is the systemd
    # producer's. The receiver refuses to list either, and prune must not
    # invent them.
    (receiver_dir / "darkmem-app-20260104-000000.sql.gz.age.part").write_bytes(b"x")
    (receiver_dir / "darkmem-20250101-000000.sql.gz").write_bytes(b"x")
    dest = _worker_destination()

    assert [s.name for s in await dest.list_snapshots()] == [
        "darkmem-app-20260101-000000.sql.gz.age",
        "darkmem-app-20260102-000000.sql.gz.age",
        "darkmem-app-20260103-000000.sql.gz.age",
    ]

    deleted = await dest.prune(keep=2)

    assert deleted == ["darkmem-app-20260101-000000.sql.gz.age"]
    assert not (receiver_dir / "darkmem-app-20260101-000000.sql.gz.age").exists()
    assert (receiver_dir / "darkmem-20250101-000000.sql.gz").exists()
    assert (receiver_dir / "darkmem-app-20260104-000000.sql.gz.age.part").exists()


async def test_a_worker_mismatch_journals_verify_failed_through_ship_all(
    session, session_factory, receiver_dir, tmp_path, monkeypatch,
):
    """End to end through `ship_all`, because the read-back comparison is the
    thing the whole destination exists for: a receiver holding different bytes
    than we sent must produce a verify failure, not a successful ship."""
    dumps = tmp_path / "dumps"
    dumps.mkdir()
    await _dump_into(dumps, monkeypatch)
    await bc.save_destinations(
        session,
        {
            "destinations": [
                {
                    "name": "attic",
                    "kind": "local",  # local so no age binary is needed here
                    "enabled": True,
                    "retention_keep": 2,
                }
            ]
        },
    )
    liar = _worker_destination()
    monkeypatch.setattr(
        liar, "read_back_sha256", lambda name, timeout=None: _resolved("f" * 64)
    )
    monkeypatch.setattr(backup_ship, "build_destination", lambda cfg: liar)
    _fake_archive(monkeypatch)

    summary = await backup_ship.ship_all(session_factory)

    assert summary["verify_failed"] == ["attic"]
    rows = await _payloads(session, "backup_verify_failed")
    assert [r for r in rows if r["family"] == "dump"][0]["got"] == "f" * 64


async def _resolved(value):
    return value


def test_build_destination_serves_the_worker_kind():
    assert isinstance(
        backup_ship.build_destination(WORKER_CFG), backup_ship.WorkerDestination
    )


# ---------------------------------------------------------------------------
# Increment 7 Task 10: the pull helper
#
# A pulled snapshot gets the same distrust as an uploaded one. The read-back
# comparison here is not ceremony: the bytes we are about to replay into a
# database are the whole point, and a destination that hands back something
# else must stop the restore rather than feed it.
# ---------------------------------------------------------------------------


class _PullSource:
    """A destination that serves two snapshots and can be told to lie."""

    def __init__(self, files: dict, *, sha=None):
        self.name = "source"
        self.retention_keep = 14
        self._files = files
        self._sha = sha

    async def list_snapshots(self, family=None):
        family = family or backup_ship.DUMPS
        return [
            backup_ship.SnapshotInfo(
                name=n, size=len(b), modified_at=family.stamp_datetime(n)
            )
            for n, b in sorted(self._files.items())
            if family.matches(n)
        ]

    async def read_back_sha256(self, name):
        if self._sha is not None:
            return self._sha
        import hashlib

        return hashlib.sha256(self._files[name]).hexdigest()

    async def stream(self, name):
        yield self._files[name]

    async def ship(self, local_path):  # pragma: no cover - not a pull verb
        raise AssertionError("the pull path must never ship")

    async def prune(self, keep):  # pragma: no cover - not a pull verb
        raise AssertionError("the pull path must never prune")


OLD = "darkmem-app-20260101-000000.sql.gz.age"
NEW = "darkmem-app-20260214-000000.sql.gz.age"


def _files():
    return {OLD: b"the older snapshot", NEW: b"the newer snapshot"}


async def test_pull_latest_resolves_the_newest_by_stamp(tmp_path, monkeypatch):
    from app.services import backup_pull

    source = _PullSource(_files())
    monkeypatch.setattr(backup_pull, "_destination_for", lambda *a, **k: _resolved(source))

    out = await backup_pull.pull(source, name=None, out_dir=tmp_path)

    assert out.name == NEW
    assert out.read_bytes() == b"the newer snapshot"
    assert not list(tmp_path.glob("*.part"))


async def test_pull_by_name_fetches_that_one(tmp_path):
    from app.services import backup_pull

    out = await backup_pull.pull(_PullSource(_files()), name=OLD, out_dir=tmp_path)
    assert out.name == OLD


async def test_pull_refuses_a_name_the_destination_does_not_hold(tmp_path):
    from app.services import backup_pull

    with pytest.raises(backup_pull.SnapshotNotFound):
        await backup_pull.pull(
            _PullSource(_files()), name="darkmem-app-19700101-000000.sql.gz", out_dir=tmp_path
        )


async def test_pull_refuses_a_checksum_mismatch_and_leaves_nothing(tmp_path):
    """A pulled snapshot is about to be replayed into a database. Distrusting
    it exactly as much as an uploaded one is the point of the verify."""
    from app.services import backup_pull

    source = _PullSource(_files(), sha="e" * 64)
    with pytest.raises(backup_pull.PullVerifyFailed):
        await backup_pull.pull(source, name=NEW, out_dir=tmp_path)
    assert not list(tmp_path.glob("*"))


async def test_pull_refuses_an_empty_destination(tmp_path):
    from app.services import backup_pull

    with pytest.raises(backup_pull.SnapshotNotFound):
        await backup_pull.pull(_PullSource({}), name=None, out_dir=tmp_path)


# ── Task 3: the two families never see each other ────────────────────

from app.services.attachment_archive import ATTACHMENTS, DUMPS  # noqa: E402

DUMP_OLD = "darkmem-app-20260101-000000.sql.gz"
DUMP_NEW = "darkmem-app-20260102-000000.sql.gz"
TAR_OLD = "darkmem-app-attachments-20260101-000000.tar.gz"
TAR_NEW = "darkmem-app-attachments-20260102-000000.tar.gz"


def _seed_both_families(directory) -> None:
    """Explicit mtimes: LocalDestination.prune orders on (mtime, name), and
    two files written inside one second would leave the order to the tie-break
    rather than to the property under test."""
    for index, name in enumerate((DUMP_OLD, DUMP_NEW, TAR_OLD, TAR_NEW)):
        path = directory / name
        path.write_bytes(b"x")
        os.utime(path, (1_700_000_000 + index, 1_700_000_000 + index))
    os.utime(directory / TAR_OLD, (1_700_000_000, 1_700_000_000))
    os.utime(directory / TAR_NEW, (1_700_000_001, 1_700_000_001))


async def test_local_listing_is_family_scoped(tmp_path):
    _seed_both_families(tmp_path)
    dest = backup_ship.LocalDestination(name="disk", directory=tmp_path)

    assert {s.name for s in await dest.list_snapshots()} == {DUMP_OLD, DUMP_NEW}
    assert {s.name for s in await dest.list_snapshots(DUMPS)} == {DUMP_OLD, DUMP_NEW}
    assert {s.name for s in await dest.list_snapshots(ATTACHMENTS)} == {TAR_OLD, TAR_NEW}


async def test_pruning_one_family_leaves_the_other_whole(tmp_path):
    _seed_both_families(tmp_path)
    dest = backup_ship.LocalDestination(name="disk", directory=tmp_path)

    assert await dest.prune(1, ATTACHMENTS) == [TAR_OLD]
    assert {p.name for p in tmp_path.iterdir()} == {DUMP_OLD, DUMP_NEW, TAR_NEW}

    assert await dest.prune(1) == [DUMP_OLD]
    assert {p.name for p in tmp_path.iterdir()} == {DUMP_NEW, TAR_NEW}


async def test_local_dates_from_mtime_and_the_helper_from_the_name(tmp_path):
    """Local is the one kind that can see a real mtime, and keeps using it.
    The remote kinds have no mtime to trust, so they date from the stamp --
    asserting both here keeps the difference deliberate rather than accidental."""
    _seed_both_families(tmp_path)
    dest = backup_ship.LocalDestination(name="disk", directory=tmp_path)

    tarballs = {s.name: s for s in await dest.list_snapshots(ATTACHMENTS)}
    assert tarballs[TAR_NEW].modified_at.year == 2023
    assert ATTACHMENTS.stamp_datetime(TAR_NEW).year == 2026


async def test_a_transfer_bound_is_overridable_per_call(monkeypatch):
    """The attachment tarball needs a larger bound than a dump; the protocol
    carries it rather than each destination guessing from the name."""
    seen: list[float] = []
    ssh = backup_ship.SshDestination(SSH_CFG)

    async def _run(argv, *, timeout, on_chunk=None):
        seen.append(timeout)
        return b""

    monkeypatch.setattr(ssh, "_run", _run)
    async with ssh._scratch() as (_, base):
        await ssh._remote_names(base, DUMPS, timeout=4242)
    assert 4242 in seen


def test_the_dump_helpers_survive_as_aliases():
    assert backup_ship._is_snapshot(DUMP_NEW)
    assert not backup_ship._is_snapshot(TAR_NEW)
    assert backup_ship._stamp_of(DUMP_NEW).year == 2026


# ── Task 4: S3 never materialises an object ──────────────────────────

import hashlib  # noqa: E402


class _CountingBody:
    """A boto3 body that records how much each `read` asked for.

    The property is "no single read asks for the whole object": a destination
    that buffers a multi-gigabyte tarball OOM-kills a container capped at 1 GB,
    and a test that only compared the final bytes would pass either way.
    """

    def __init__(self, payload: bytes):
        self._buffer = io.BytesIO(payload)
        self.reads: list[int | None] = []
        self.closed = False

    def read(self, size=-1):
        self.reads.append(size)
        return self._buffer.read(size)

    def close(self):
        self.closed = True


class _StreamingFakeS3(_FakeS3):
    def __init__(self, objects=None):
        super().__init__(objects)
        self.bodies: list[_CountingBody] = []

    def get_object(self, Bucket, Key):  # noqa: N803
        body = _CountingBody(self.objects[Key])
        self.bodies.append(body)
        return {"Body": body}


async def test_s3_streams_in_bounded_chunks(tmp_path):
    key = "darkmem/darkmem-app-attachments-20260101-000000.tar.gz.age"
    payload = b"z" * (3 * backup_ship._S3_CHUNK + 7)
    fake = _StreamingFakeS3({key: payload})

    chunks = [
        chunk
        async for chunk in _s3(fake).stream(
            "darkmem-app-attachments-20260101-000000.tar.gz.age"
        )
    ]

    assert b"".join(chunks) == payload
    assert len(chunks) == 4
    assert fake.bodies[0].reads == [backup_ship._S3_CHUNK] * 5
    assert fake.bodies[0].closed


async def test_s3_read_back_hashes_without_buffering(tmp_path):
    key = "darkmem/darkmem-app-attachments-20260101-000000.tar.gz.age"
    payload = b"y" * (2 * backup_ship._S3_CHUNK)
    fake = _StreamingFakeS3({key: payload})

    digest = await _s3(fake).read_back_sha256(
        "darkmem-app-attachments-20260101-000000.tar.gz.age"
    )

    assert digest == hashlib.sha256(payload).hexdigest()
    assert all(size == backup_ship._S3_CHUNK for size in fake.bodies[0].reads)


# ── Task 5: one stamp for both artefacts, and the run budget ─────────


async def test_run_dump_honours_a_caller_supplied_stamp(tmp_path, monkeypatch):
    await _dump_into(tmp_path, monkeypatch)
    out = await backup_ship.run_dump(stamp="20260920-043000")
    assert out.name == "darkmem-app-20260920-043000.sql.gz"


async def test_run_dump_still_mints_its_own_stamp(tmp_path, monkeypatch):
    await _dump_into(tmp_path, monkeypatch)
    out = await backup_ship.run_dump()
    assert backup_ship.DUMPS.stamp_of(out.name) is not None


def test_the_run_budget_covers_one_destination_end_to_end():
    """Both artefacts, both directions, for one destination. Three unreachable
    NASes can still exhaust the budget -- that is accepted -- but a single
    destination must never be cut off mid-verify, because a kill there leaves
    the state row unwritten and repeats the whole decision tomorrow."""
    one_destination = (
        backup_ship.SHIP_TIMEOUT_SECONDS
        + backup_ship.READ_BACK_TIMEOUT_SECONDS
        + backup_ship.ATTACHMENTS_SHIP_TIMEOUT_SECONDS
        + backup_ship.ATTACHMENTS_READ_BACK_TIMEOUT_SECONDS
    )
    assert backup_ship.BACKUP_SHIP_MAX_RUN_SECONDS > one_destination


def test_main_registers_the_job_with_that_budget():
    """A text assertion on purpose: building the app to read one registration
    field would stand a database and a scheduler up for a constant."""
    source = (
        Path(backup_ship.__file__).resolve().parents[1] / "main.py"
    ).read_text()
    assert "max_run_seconds=BACKUP_SHIP_MAX_RUN_SECONDS" in source


# ── Task 6: the build-and-ship decision ──────────────────────────────

ARCHIVE_STAMP = "20260101-000000"
ARCHIVE_NAME = f"darkmem-app-attachments-{ARCHIVE_STAMP}.tar.gz"


async def _journal_attachment(session, destination, stamp, event_type, payload):
    await session.execute(
        sa_text(
            "INSERT INTO events (event_type, object_type, source, payload) "
            "VALUES (:t, 'system', 'backup_ship', CAST(:p AS jsonb))"
        ),
        {"t": event_type, "p": json.dumps(payload)},
    )


async def _journal_attachment_failure(session, destination, stamp):
    await _journal_attachment(
        session, destination, stamp, "backup_verify_failed",
        {"destination": destination, "family": "attachments", "stamp": stamp,
         "error": "read-back mismatch"},
    )


async def _journal_attachment_success(session, destination, stamp):
    await _journal_attachment(
        session, destination, stamp, "backup_shipped",
        {"destination": destination, "family": "attachments", "stamp": stamp,
         "sha256": "ab"},
    )


def _fake_archive(monkeypatch) -> list[str]:
    """Stand in for the tar subprocess and record every stamp it was asked
    for -- the stamp is the property under test, not the bytes. It writes to
    the `dest_dir` it is handed, so it needs no directory of its own."""
    asked: list[str] = []

    async def _build(dest_dir, stamp, *, expect_rows):
        asked.append(stamp)
        out = Path(dest_dir) / f"darkmem-app-attachments-{stamp}.tar.gz"
        out.write_bytes(b"tarball")
        return out

    monkeypatch.setattr(backup_ship, "build_archive", _build)
    return asked


async def _one_destination(session, monkeypatch, tmp_path, fake):
    await _dump_into(tmp_path, monkeypatch)
    await bc.save_destinations(session, {"destinations": [{**LOCAL, "name": fake.name}]})
    monkeypatch.setattr(backup_ship, "build_destination", lambda cfg: fake)


async def test_a_changed_manifest_builds_ships_and_records(
    session, session_factory, tmp_path, monkeypatch
):
    fake = _FakeDestination("disk")
    await _one_destination(session, monkeypatch, tmp_path, fake)
    asked = _fake_archive(monkeypatch)

    summary = await backup_ship.ship_all(session_factory)

    assert summary["attachments"]["built"] is True
    assert summary["attachments"]["shipped"] == 1
    assert len(asked) == 1
    rows = await _payloads(session, "backup_shipped")
    families = [r["family"] for r in rows]
    assert families == ["dump", "attachments"]
    assert rows[1]["stamp"] == asked[0]

    state = await backup_ship.load_state(session)
    assert state is not None and state.stamp == asked[0]


async def test_an_unchanged_manifest_with_a_verified_copy_ships_nothing(
    session, session_factory, tmp_path, monkeypatch
):
    fake = _FakeDestination("disk")
    await _one_destination(session, monkeypatch, tmp_path, fake)
    asked = _fake_archive(monkeypatch)
    await backup_ship.ship_all(session_factory)
    stamp = asked[0]

    # The destination now holds it and the journal says it verified.
    fake._holds = [f"darkmem-app-attachments-{stamp}.tar.gz"]
    asked.clear()

    summary = await backup_ship.ship_all(session_factory)

    assert asked == []
    assert summary["attachments"]["built"] is False
    assert summary["attachments"]["skipped"] == ["disk"]


async def test_a_destination_missing_the_copy_catches_up_at_the_same_stamp(
    session, session_factory, tmp_path, monkeypatch
):
    fake = _FakeDestination("disk")
    await _one_destination(session, monkeypatch, tmp_path, fake)
    asked = _fake_archive(monkeypatch)
    await backup_ship.ship_all(session_factory)
    first = asked[0]
    asked.clear()

    # Listing is empty: the copy is gone. The manifest has not moved.
    summary = await backup_ship.ship_all(session_factory)

    assert asked == [first], "a catch-up must not mint a new stamp"
    assert summary["attachments"]["shipped"] == 1
    state = await backup_ship.load_state(session)
    assert state.stamp == first


async def test_a_listed_copy_that_failed_verification_is_shipped_again(
    session, session_factory, tmp_path, monkeypatch
):
    """The journal half of the decision, and the only test that reaches it.

    The state row must already say this manifest was handled, or `changed`
    would be True and the rebuild would happen for the wrong reason.
    """
    stamp = "20260101-000000"
    fake = _FakeDestination("disk", holds=[f"darkmem-app-attachments-{stamp}.tar.gz"])
    await _one_destination(session, monkeypatch, tmp_path, fake)
    asked = _fake_archive(monkeypatch)

    manifest = await backup_ship.manifest_hash(session)
    await backup_ship.save_state(
        session, backup_ship.ArchiveState(stamp=stamp, manifest_hash=manifest)
    )
    await _journal_attachment_failure(session, "disk", stamp)
    await session.commit()

    summary = await backup_ship.ship_all(session_factory)

    assert asked == [stamp], "a listed but unverified copy must be re-shipped"
    assert summary["attachments"]["skipped"] == []


async def test_a_listed_and_verified_copy_is_not_shipped_again(
    session, session_factory, tmp_path, monkeypatch
):
    """The same setup with a `backup_shipped` row: the pair of tests is what
    proves the journal, not the listing, is what decides."""
    stamp = "20260101-000000"
    fake = _FakeDestination("disk", holds=[f"darkmem-app-attachments-{stamp}.tar.gz"])
    await _one_destination(session, monkeypatch, tmp_path, fake)
    asked = _fake_archive(monkeypatch)

    manifest = await backup_ship.manifest_hash(session)
    await backup_ship.save_state(
        session, backup_ship.ArchiveState(stamp=stamp, manifest_hash=manifest)
    )
    await _journal_attachment_success(session, "disk", stamp)
    await session.commit()

    summary = await backup_ship.ship_all(session_factory)

    assert asked == []
    assert summary["attachments"]["skipped"] == ["disk"]


async def test_the_tarball_transfer_gets_the_larger_bound(
    session, session_factory, tmp_path, monkeypatch
):
    """Defining the constants without passing them would cut a multi-gigabyte
    transfer off at the dump's bound -- the failure the budget exists against."""
    fake = _FakeDestination("disk")
    await _one_destination(session, monkeypatch, tmp_path, fake)
    _fake_archive(monkeypatch)

    await backup_ship.ship_all(session_factory)

    assert fake.timeouts == [None, backup_ship.ATTACHMENTS_SHIP_TIMEOUT_SECONDS]


async def test_the_tarball_read_back_gets_the_larger_bound(
    session, session_factory, tmp_path, monkeypatch
):
    """The upload bound is only half the pair. A read-back left at the dump's
    900s would time out on a multi-gigabyte verify and retract, as a failure, a
    tarball that had in fact landed."""
    fake = _FakeDestination("disk")
    await _one_destination(session, monkeypatch, tmp_path, fake)
    _fake_archive(monkeypatch)
    seen: list[float | None] = []
    inner = fake.read_back_sha256

    async def _record(name, *, timeout=None):
        seen.append(timeout)
        return await inner(name, timeout=timeout)

    monkeypatch.setattr(fake, "read_back_sha256", _record)

    await backup_ship.ship_all(session_factory)

    assert seen == [None, backup_ship.ATTACHMENTS_READ_BACK_TIMEOUT_SECONDS]


async def test_three_destinations_converge_on_one_stamp(
    session, session_factory, tmp_path, monkeypatch
):
    """The catch-up must terminate. If a destination that was behind made the
    run mint a fresh stamp, every *other* destination would then lack that one
    and ship again the night after, forever."""
    fakes = {n: _FakeDestination(n) for n in ("a", "b", "c")}
    await _dump_into(tmp_path, monkeypatch)
    await bc.save_destinations(
        session,
        {"destinations": [{**LOCAL, "name": n} for n in ("a", "b", "c")]},
    )
    monkeypatch.setattr(backup_ship, "build_destination", lambda cfg: fakes[cfg.name])
    asked = _fake_archive(monkeypatch)

    await backup_ship.ship_all(session_factory)
    stamp = asked[0]
    held = f"darkmem-app-attachments-{stamp}.tar.gz"

    # Two destinations kept it; the third lost it.
    fakes["a"]._holds = [held]
    fakes["b"]._holds = [held]
    asked.clear()
    summary = await backup_ship.ship_all(session_factory)
    assert asked == [stamp]
    assert sorted(summary["attachments"]["skipped"]) == ["a", "b"]

    # Now all three hold it: the third run ships nothing and builds nothing.
    fakes["c"]._holds = [held]
    asked.clear()
    summary = await backup_ship.ship_all(session_factory)
    assert asked == []
    assert sorted(summary["attachments"]["skipped"]) == ["a", "b", "c"]


async def test_the_attachments_prune_uses_its_own_family_and_keep(
    session, session_factory, tmp_path, monkeypatch
):
    fake = _FakeDestination("disk", attachments_retention_keep=3)
    await _dump_into(tmp_path, monkeypatch)
    await bc.save_destinations(
        session,
        {"destinations": [{**LOCAL, "name": "disk", "retention_keep": 14,
                           "attachments_retention_keep": 3}]},
    )
    monkeypatch.setattr(backup_ship, "build_destination", lambda cfg: fake)
    _fake_archive(monkeypatch)

    await backup_ship.ship_all(session_factory)

    assert (14, backup_ship.DUMPS.prefix) in fake.pruned_families
    assert (3, backup_ship.ATTACHMENTS.prefix) in fake.pruned_families


async def test_a_failed_tarball_leaves_the_dump_reported_as_shipped(
    session, session_factory, tmp_path, monkeypatch
):
    fake = _FakeDestination("disk")
    await _one_destination(session, monkeypatch, tmp_path, fake)

    async def _boom(dest_dir, stamp, *, expect_rows):
        raise backup_ship.ArchiveIncomplete("the volume is not mounted")

    monkeypatch.setattr(backup_ship, "build_archive", _boom)

    summary = await backup_ship.ship_all(session_factory)

    assert summary["shipped"] == 1
    assert summary["verify_failed"] == []
    assert summary["attachments"]["verify_failed"] == ["disk"]
    assert await backup_ship.load_state(session) is None

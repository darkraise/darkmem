"""The second artefact family, its builder and its state row (spec §5.1, §5.3).

The classification tests are the load-bearing ones. Every prune in this system
takes a family, so a predicate that let a tarball read as a dump would let a
retention pass delete dumps -- which is why the disjointness is asserted in
both directions rather than by checking one example of each.
"""
from __future__ import annotations

import socket
import tarfile
from datetime import timezone
from pathlib import Path

import pytest
from sqlalchemy import text as sa_text

from app.services.attachment_archive import (
    ATTACHMENTS,
    ATTACHMENTS_STATE_KEY,
    DUMPS,
    ArchiveIncomplete,
    ArchiveState,
    build_archive,
    load_state,
    save_state,
)

DUMP = "darkmem-app-20260920-043000.sql.gz"
DUMP_AGE = "darkmem-app-20260920-043000.sql.gz.age"
TAR = "darkmem-app-attachments-20260920-043000.tar.gz"
TAR_AGE = "darkmem-app-attachments-20260920-043000.tar.gz.age"


@pytest.mark.parametrize("name", [DUMP, DUMP_AGE])
def test_dumps_match_only_dumps(name):
    assert DUMPS.matches(name)
    assert not ATTACHMENTS.matches(name)


@pytest.mark.parametrize("name", [TAR, TAR_AGE])
def test_attachments_match_only_attachments(name):
    assert ATTACHMENTS.matches(name)
    assert not DUMPS.matches(name)


@pytest.mark.parametrize(
    "name",
    [
        "darkmem-app-20260920-043000.sql.gz.part",
        "darkmem-app-attachments-20260920-043000.tar.gz.part",
        "darkmem-20260920-043000.sql.gz",
        "darkmem-attachments-20260920-043000.tar.gz",
        "notes.txt",
        "",
    ],
)
def test_neither_family_matches_a_foreign_or_in_flight_name(name):
    assert not DUMPS.matches(name)
    assert not ATTACHMENTS.matches(name)


def test_stamp_of_returns_the_token_and_stamp_datetime_the_value():
    assert DUMPS.stamp_of(DUMP_AGE) == "20260920-043000"
    assert ATTACHMENTS.stamp_of(TAR_AGE) == "20260920-043000"
    moment = ATTACHMENTS.stamp_datetime(TAR_AGE)
    assert (moment.year, moment.hour, moment.tzinfo) == (2026, 4, timezone.utc)


def test_an_unparseable_stamp_is_none_and_the_epoch():
    name = "darkmem-app-attachments-nonsense.tar.gz"
    assert ATTACHMENTS.stamp_of(name) is None
    assert ATTACHMENTS.stamp_datetime(name).year == 1970


async def test_build_archive_writes_a_tarball_of_the_store(tmp_path, monkeypatch):
    store = tmp_path / "attachments"
    (store / "ab").mkdir(parents=True)
    (store / "ab" / "abcd").write_bytes(b"payload")
    (store / "ab" / "abcd.part").write_bytes(b"in flight")
    (store / ".staging" / "job").mkdir(parents=True)
    (store / ".staging" / "job" / "x").write_bytes(b"staged")
    monkeypatch.setattr("app.services.attachment_archive.attachments_root", lambda: store)

    out = await build_archive(tmp_path, "20260920-043000", expect_rows=1)

    assert out.name == "darkmem-app-attachments-20260920-043000.tar.gz"
    with tarfile.open(out) as archive:
        members = {m.name.lstrip("./") for m in archive.getmembers() if m.isfile()}
    assert members == {"ab/abcd"}
    # Neither the `.part` nor the listing file survives: the listing has a file
    # of its own so stderr can stay diagnostics-only, and a dump directory an
    # operator reads is the wrong place to leave it.
    assert {p.name for p in tmp_path.iterdir()} == {"attachments", out.name}


async def test_build_archive_refuses_an_empty_store_when_rows_exist(tmp_path, monkeypatch):
    store = tmp_path / "attachments"
    store.mkdir()
    monkeypatch.setattr("app.services.attachment_archive.attachments_root", lambda: store)

    with pytest.raises(ArchiveIncomplete):
        await build_archive(tmp_path, "20260920-043000", expect_rows=4)
    assert not list(tmp_path.glob("darkmem-app-attachments-*"))


async def test_build_archive_allows_an_empty_store_when_no_rows(tmp_path, monkeypatch):
    store = tmp_path / "attachments"
    store.mkdir()
    monkeypatch.setattr("app.services.attachment_archive.attachments_root", lambda: store)

    out = await build_archive(tmp_path, "20260920-043000", expect_rows=0)
    assert out.is_file()


async def test_a_tar_diagnostic_is_not_counted_as_a_member(tmp_path, monkeypatch):
    """stderr carries tar's diagnostics; the member listing has its own file.

    A unix socket is the one entry tar refuses deterministically for every
    user, root included -- these tests run as root, where a `chmod 000` file is
    still readable, so it cannot stand in for the unreadable-store case this
    guard exists for. tar writes `socket ignored` to stderr, mints no member
    and exits 0. Counting stderr reads that line as one archived file, so a
    store whose files are ALL unreadable would pass the completeness check and
    an empty tarball would land under the canonical name -- the inflation is
    exactly inverse to the signal.
    """
    store = tmp_path / "attachments"
    store.mkdir()
    # sun_path caps near 108 bytes; keep this name and the test's own short.
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(str(store / "s"))
    finally:
        sock.close()
    monkeypatch.setattr("app.services.attachment_archive.attachments_root", lambda: store)

    with pytest.raises(ArchiveIncomplete):
        await build_archive(tmp_path, "20260920-043000", expect_rows=1)
    assert list(tmp_path.iterdir()) == [store]


async def test_state_round_trips_and_starts_absent(session):
    assert await load_state(session) is None
    await save_state(session, ArchiveState(stamp="20260920-043000", manifest_hash="ab" * 32))
    loaded = await load_state(session)
    assert loaded == ArchiveState(stamp="20260920-043000", manifest_hash="ab" * 32)

    row = (
        await session.execute(
            sa_text("SELECT key FROM config WHERE key = :k"),
            {"k": ATTACHMENTS_STATE_KEY},
        )
    ).scalar_one()
    assert row == ATTACHMENTS_STATE_KEY

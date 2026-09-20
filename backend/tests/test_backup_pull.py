"""Fetching a snapshot back off a destination, in both families (spec §5.2).

The pairing rule is the load-bearing one: a restore that takes the *newest*
tarball rather than the newest at or before its dump serves files the dump's
own rows never referenced.
"""
from __future__ import annotations

import hashlib

import pytest

from app.services import backup_pull
from app.services.attachment_archive import ATTACHMENTS


class _Holding:
    """A destination whose contents are a dict. `read_back_sha256` derives
    from the same bytes `stream` serves, as every real kind does."""

    name = "nas"
    retention_keep = 14
    attachments_retention_keep = 3

    def __init__(self, objects: dict[str, bytes]):
        self.objects = objects

    async def list_snapshots(self, family=None):
        family = family or backup_pull.DUMPS
        return [
            backup_pull.SnapshotInfo(
                name=n, size=len(b), modified_at=family.stamp_datetime(n)
            )
            for n, b in sorted(self.objects.items())
            if family.matches(n)
        ]

    async def stream(self, name: str):
        yield self.objects[name]

    async def read_back_sha256(self, name: str) -> str:
        return hashlib.sha256(self.objects[name]).hexdigest()


def _holding(objects: dict[str, bytes]) -> _Holding:
    return _Holding(objects)

DUMP_0102 = "darkmem-app-20260102-000000.sql.gz.age"
TAR_0101 = "darkmem-app-attachments-20260101-000000.tar.gz.age"
TAR_0103 = "darkmem-app-attachments-20260103-000000.tar.gz.age"


async def test_pull_defaults_to_the_dump_family(tmp_path):
    destination = _holding({DUMP_0102: b"dump", TAR_0103: b"tar"})
    out = await backup_pull.pull(destination, name=None, out_dir=tmp_path)
    assert out.name == DUMP_0102


async def test_pull_can_take_the_attachment_family(tmp_path):
    destination = _holding({DUMP_0102: b"dump", TAR_0103: b"tar"})
    out = await backup_pull.pull(
        destination, name=None, out_dir=tmp_path, family=ATTACHMENTS
    )
    assert out.name == TAR_0103


async def test_paired_with_picks_the_newest_at_or_before_the_dump(tmp_path):
    destination = _holding(
        {DUMP_0102: b"dump", TAR_0101: b"older", TAR_0103: b"newer"}
    )
    chosen = await backup_pull.paired_name(destination, DUMP_0102)
    assert chosen == TAR_0101


async def test_paired_with_raises_when_nothing_pairs(tmp_path):
    destination = _holding({DUMP_0102: b"dump", TAR_0103: b"newer"})
    with pytest.raises(backup_pull.SnapshotNotFound):
        await backup_pull.paired_name(destination, DUMP_0102)

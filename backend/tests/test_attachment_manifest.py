"""The attachment set's change gate (spec §3).

The property that matters is not "it hashes something" but that the hash is a
function of the *set*: insertion order must not move it, and a delete followed
by an add of a different file must. A count would satisfy neither.
"""
from __future__ import annotations

import hashlib
from uuid import uuid4

from sqlalchemy import text as sa_text

from app.services.attachment_manifest import attachment_count, manifest_hash

EMPTY_SHA = hashlib.sha256(b"").hexdigest()


async def _insert(session, attachment_id, sha256: str) -> None:
    await session.execute(
        sa_text(
            "INSERT INTO page_attachments "
            "(id, project, filename, content_type, size_bytes, sha256) "
            "VALUES (CAST(:id AS uuid), 'default', 'f.png', 'image/png', 1, :sha)"
        ),
        {"id": str(attachment_id), "sha": sha256},
    )


async def test_an_empty_table_hashes_the_empty_string(session):
    assert await manifest_hash(session) == EMPTY_SHA
    assert await attachment_count(session) == 0


async def test_the_hash_moves_when_a_row_is_added(session):
    before = await manifest_hash(session)
    await _insert(session, uuid4(), "a" * 64)
    after = await manifest_hash(session)
    assert after != before
    assert await attachment_count(session) == 1


async def test_insertion_order_does_not_change_the_hash(session):
    first, second = uuid4(), uuid4()
    await _insert(session, first, "a" * 64)
    await _insert(session, second, "b" * 64)
    forwards = await manifest_hash(session)

    await session.execute(sa_text("DELETE FROM page_attachments"))
    await _insert(session, second, "b" * 64)
    await _insert(session, first, "a" * 64)
    assert await manifest_hash(session) == forwards


async def test_a_delete_plus_add_changes_the_hash(session):
    old = uuid4()
    await _insert(session, old, "a" * 64)
    before = await manifest_hash(session)

    await session.execute(
        sa_text("DELETE FROM page_attachments WHERE id = CAST(:id AS uuid)"),
        {"id": str(old)},
    )
    await _insert(session, uuid4(), "c" * 64)
    assert await manifest_hash(session) != before
    assert await attachment_count(session) == 1

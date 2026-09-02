"""Compare-and-set on the document write (2026-08-31 spec §5.3, review M1).

The property under test is not "a stale hash is rejected" -- a read-then-write
implementation passes that in a single-threaded test. It is that the rejection
survives *concurrency*: two lanes that both read the same current hash must not
both succeed. The race test at the bottom fails under read-then-compare and
passes only when the predicate rides the UPDATE.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.repositories import documents as documents_repo


async def _seed(session, *, uri: str, content_hash: str) -> object:
    return await documents_repo.upsert_by_uri(
        session,
        document_id=uuid4(),
        project="p",
        uri=uri,
        title="t",
        source_type="md",
        content_hash=content_hash,
        content="original",
        properties=None,
    )


@pytest.mark.asyncio
async def test_matching_expected_hash_updates_and_reports_one_row(session):
    doc_id = await _seed(session, uri="cas/a.md", content_hash="a" * 64)
    matched = await documents_repo.update_document(
        session,
        document_id=doc_id,
        title="t2",
        source_type="md",
        content_hash="b" * 64,
        content="updated",
        properties=None,
        expected_hash="a" * 64,
    )
    assert matched == 1
    row = (await session.execute(
        text("SELECT content_hash, content FROM documents WHERE id = CAST(:id AS uuid)"),
        {"id": str(doc_id)},
    )).mappings().one()
    assert row["content_hash"] == "b" * 64
    assert row["content"] == "updated"


@pytest.mark.asyncio
async def test_stale_expected_hash_matches_zero_rows_and_writes_nothing(session):
    doc_id = await _seed(session, uri="cas/b.md", content_hash="a" * 64)
    matched = await documents_repo.update_document(
        session,
        document_id=doc_id,
        title="clobbered",
        source_type="md",
        content_hash="c" * 64,
        content="clobbered",
        properties=None,
        expected_hash="z" * 64,          # not the row's hash
    )
    assert matched == 0
    row = (await session.execute(
        text(
            "SELECT title, content_hash, content FROM documents "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(doc_id)},
    )).mappings().one()
    # Every column untouched: a refused precondition writes nothing at all,
    # not "everything except content_hash".
    assert row["title"] == "t"
    assert row["content_hash"] == "a" * 64
    assert row["content"] == "original"


@pytest.mark.asyncio
async def test_null_expected_hash_keeps_last_writer_wins(session):
    doc_id = await _seed(session, uri="cas/c.md", content_hash="a" * 64)
    matched = await documents_repo.update_document(
        session,
        document_id=doc_id,
        title="t2",
        source_type="md",
        content_hash="d" * 64,
        content="updated",
        properties=None,
    )
    assert matched == 1



# ── The race, deterministically interleaved and shown closed ─────────

import asyncio  # noqa: E402

from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402

from app.services.document_ingest import (  # noqa: E402
    BlockDraft,
    DocumentHashConflict,
    file_document,
)
from tests.conftest import test_engine  # noqa: E402

PROJECT = "cas-race"
URI = "docs/cas-race.md"


def _parse(content: str):
    return lambda: [
        BlockDraft(
            text=content, type="paragraph", parent=None,
            properties=None, char_span=None,
        )
    ]


@pytest.mark.asyncio
async def test_two_lanes_with_the_same_expected_hash_cannot_both_win(setup_database):
    """Review M1's race, interleaved on purpose.

    Both lanes resolve the document at hash H0 before either commit lands --
    the exact window a read-then-write leaves open. Under that implementation
    lane B's own comparison passes (it read H0), its unconditional UPDATE
    blocks on lane A's row lock, then proceeds and clobbers: no exception,
    B's content survives, and this test fails on both assertions. Under the
    compare-and-set the blocked UPDATE re-evaluates its predicate against A's
    committed row, matches zero rows, and B gets DocumentHashConflict naming
    A's hash.
    """
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    seed, lane_a, lane_b = factory(), factory(), factory()
    try:
        first = await file_document(
            seed, project=PROJECT, uri=URI, content="v0", parse=_parse("v0"),
        )
        await seed.commit()
        h0 = first.content_hash

        # Lane A passes the precondition and holds the row lock, uncommitted.
        res_a = await file_document(
            lane_a, project=PROJECT, uri=URI, content="lane A",
            parse=_parse("lane A"), expected_hash=h0,
        )

        # Lane B resolves H0 -- MVCC, the SELECT does not block -- passes any
        # door-level comparison, and must now block on lane A's row lock.
        task_b = asyncio.create_task(asyncio.wait_for(
            file_document(
                lane_b, project=PROJECT, uri=URI, content="lane B",
                parse=_parse("lane B"), expected_hash=h0,
            ),
            timeout=15,
        ))
        await asyncio.sleep(0.3)
        assert not task_b.done(), (
            "lane B finished before lane A committed -- it never entered the "
            "race window this test exists to exercise"
        )

        await lane_a.commit()

        with pytest.raises(DocumentHashConflict) as exc:
            await task_b
        assert exc.value.expected_hash == h0
        assert exc.value.current_hash == res_a.content_hash   # names the winner

        check = factory()
        try:
            row = (await check.execute(
                text(
                    "SELECT content_hash, content FROM documents "
                    "WHERE project = :p AND uri = :u"
                ),
                {"p": PROJECT, "u": URI},
            )).one()
            assert row.content_hash == res_a.content_hash
            assert row.content == "lane A"        # the loser wrote nothing
        finally:
            await check.close()
    finally:
        await lane_b.rollback()
        cleanup = factory()
        try:
            await cleanup.execute(
                text("DELETE FROM documents WHERE project = :p"), {"p": PROJECT},
            )
            await cleanup.commit()
        finally:
            await cleanup.close()
        await seed.close()
        await lane_a.close()
        await lane_b.close()

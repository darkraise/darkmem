"""Document revisions: the filing writes them, both doors read them (spec 2026-09-23 §3)."""
from __future__ import annotations

import asyncio
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.services.document_door import DocumentTooLarge, MAX_BLOCKS, put_document
from app.services.document_ingest import DocumentHashConflict

FINGERPRINT = "revisions-probe|3"


class StubEmbedder:
    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([[1.0, 0.0, 0.0] for _ in texts], FINGERPRINT)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0], FINGERPRINT


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


async def _put(session, content, *, uri="superpowers/specs/a.md", **kwargs):
    return await put_document(
        session, StubEmbedder(), project="proj", uri=uri, content=content, **kwargs,
    )


async def _revisions(session, document_id):
    rows = await session.execute(
        text(
            "SELECT content, content_hash, actor, api_key_id FROM document_revisions "
            "WHERE document_id = CAST(:d AS uuid) ORDER BY created_at, id"
        ),
        {"d": str(document_id)},
    )
    return [tuple(row) for row in rows]


async def test_a_created_document_writes_its_first_revision(session):
    key_id = uuid.uuid4()
    filed = await _put(session, "# A\n\nFirst.\n", actor="k-probe", api_key_id=key_id)
    assert await _revisions(session, filed.document_id) == [
        ("# A\n\nFirst.\n", filed.content_hash, "k-probe", key_id),
    ]


async def test_a_changed_put_writes_one_more_and_the_newest_is_current(session):
    first = await _put(session, "# A\n\nFirst.\n")
    second = await _put(session, "# A\n\nSecond.\n")
    revisions = await _revisions(session, first.document_id)
    assert [r[1] for r in revisions] == [first.content_hash, second.content_hash]
    current = (await session.execute(
        text("SELECT content FROM documents WHERE id = CAST(:d AS uuid)"),
        {"d": first.document_id},
    )).scalar_one()
    assert revisions[-1][0] == current


async def test_an_unchanged_put_writes_none(session):
    first = await _put(session, "# A\n\nFirst.\n")
    again = await _put(session, "# A\n\nFirst.\n")
    assert again.outcome == "unchanged"
    assert len(await _revisions(session, first.document_id)) == 1


async def test_a_stale_expected_hash_writes_none(session):
    first = await _put(session, "# A\n\nFirst.\n")
    with pytest.raises(DocumentHashConflict):
        await _put(session, "# A\n\nSecond.\n", expected_hash="0" * 64)
    assert len(await _revisions(session, first.document_id)) == 1


async def test_a_put_refused_for_max_blocks_leaves_no_revision(session):
    first = await _put(session, "# A\n\nFirst.\n")
    with pytest.raises(DocumentTooLarge):
        await _put(session, "\n\n".join(f"para {i}" for i in range(MAX_BLOCKS + 1)))
    assert len(await _revisions(session, first.document_id)) == 1


async def test_a_forced_reparse_of_identical_content_writes_none(session):
    first = await _put(session, "# A\n\nFirst.\n")
    forced = await _put(session, "# A\n\nFirst.\n", force_reparse=True)
    assert forced.outcome == "updated"
    assert len(await _revisions(session, first.document_id)) == 1


async def test_a_bytes_source_writes_none(session):
    from app.services.document_ingest import BlockDraft, file_document

    as_text = await file_document(
        session, project="proj", uri="raw.md", content="raw",
        parse=lambda: [BlockDraft(text="raw")],
    )
    as_bytes = await file_document(
        session, project="proj", uri="raw.bin", content=b"\x00\x01",
        parse=lambda: [BlockDraft(text="raw")],
    )
    assert len(await _revisions(session, as_text.document_id)) == 1
    assert await _revisions(session, as_bytes.document_id) == []


# The `session` fixture shares one connection, so it cannot show two filings
# waiting on each other. These use the test engine directly, commit for real,
# and delete their documents afterwards; the `document_filed` events they
# journal cannot be deleted and are left under the race project.
RACE_PROJECT = "revisions-race"


@pytest_asyncio.fixture
async def committed(setup_database):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    yield factory
    async with factory() as cleanup:
        await cleanup.execute(text("DELETE FROM documents WHERE project = :p"), {"p": RACE_PROJECT})
        await cleanup.commit()


async def _race_first_filings(committed, first: str, second: str) -> list[str]:
    from app.services.document_ingest import BlockDraft, file_document

    def filing(session, content):
        return file_document(
            session, project=RACE_PROJECT, uri="race.md", content=content,
            parse=lambda: [BlockDraft(text=content)],
        )

    async with committed() as winner, committed() as loser:
        filed = await filing(winner, first)
        late = asyncio.create_task(filing(loser, second))
        await asyncio.sleep(0.3)
        assert not late.done(), "the second filing must wait on the first one's row"
        await winner.commit()
        await late
        await loser.commit()
    async with committed() as check:
        rows = await check.execute(
            text(
                "SELECT content FROM document_revisions WHERE document_id = CAST(:d AS uuid) "
                "ORDER BY created_at, id"
            ),
            {"d": str(filed.document_id)},
        )
        return [row[0] for row in rows]


async def test_two_first_filings_of_the_same_content_write_one_revision(committed):
    assert await _race_first_filings(committed, "same", "same") == ["same"]


async def test_two_first_filings_of_different_content_write_two(committed):
    assert await _race_first_filings(committed, "first", "second") == ["first", "second"]


async def test_a_block_verb_edit_writes_none(session):
    from app.services.block_verbs import update_block

    filed = await _put(session, "# A\n\nFirst.\n")
    block_id = (await session.execute(
        text(
            "SELECT CAST(id AS text) FROM blocks WHERE document_id = CAST(:d AS uuid) "
            "ORDER BY order_index LIMIT 1"
        ),
        {"d": filed.document_id},
    )).scalar_one()
    await update_block(session, StubEmbedder(), block_id=block_id, text="Edited")
    assert len(await _revisions(session, filed.document_id)) == 1


async def test_a_direct_filing_after_a_block_edit_compares_with_the_row(session):
    """A block edit moves the row's hash and writes no revision, so from then on
    the newest revision is not the row. `put_document` refuses a block-first
    document; a direct `file_document` caller does not, and its revision
    follows the row's hash, never the history's."""
    from app.services.block_verbs import update_block
    from app.services.document_ingest import BlockDraft, file_document

    filed = await _put(session, "# A\n\nFirst.\n")
    block_id = (await session.execute(
        text(
            "SELECT CAST(id AS text) FROM blocks WHERE document_id = CAST(:d AS uuid) "
            "ORDER BY order_index LIMIT 1"
        ),
        {"d": filed.document_id},
    )).scalar_one()
    await update_block(session, StubEmbedder(), block_id=block_id, text="Edited")
    edited = (await session.execute(
        text("SELECT content FROM documents WHERE id = CAST(:d AS uuid)"), {"d": filed.document_id},
    )).scalar_one()

    def refile(content, **kwargs):
        return file_document(
            session, project="proj", uri="superpowers/specs/a.md", content=content,
            parse=lambda: [BlockDraft(text=content)], properties={}, **kwargs,
        )

    await refile(edited, force_reparse=True)
    assert len(await _revisions(session, filed.document_id)) == 1
    await refile("# A\n\nFirst.\n")
    assert [r[0] for r in await _revisions(session, filed.document_id)] == [
        "# A\n\nFirst.\n", "# A\n\nFirst.\n",
    ]


async def test_a_page_lists_newest_first_without_content_and_pages_back(session):
    from app.services.document_revisions import list_revisions

    hashes = [
        (await _put(session, f"# A\n\nVersion {n}.\n", actor="k-probe")).content_hash
        for n in range(3)
    ]
    document_id = (await _put(session, "# A\n\nVersion 2.\n")).document_id

    first = await list_revisions(session, document_id=document_id, limit=2)
    assert first["document_id"] == document_id
    assert [item["content_hash"] for item in first["items"]] == [hashes[2], hashes[1]]
    assert set(first["items"][0]) == {"id", "content_hash", "actor", "api_key_id", "created_at"}
    assert first["items"][0]["actor"] == "k-probe"
    assert first["next_before"] == first["items"][1]["id"]

    rest = await list_revisions(
        session, document_id=document_id, before=first["next_before"], limit=2,
    )
    assert [item["content_hash"] for item in rest["items"]] == [hashes[0]]
    assert rest["next_before"] is None


async def test_a_full_last_page_answers_no_cursor(session):
    from app.services.document_revisions import list_revisions

    filed = await _put(session, "# A\n\nOnly.\n")
    page = await list_revisions(session, document_id=filed.document_id, limit=1)
    assert len(page["items"]) == 1
    assert page["next_before"] is None


async def test_a_cursor_from_another_document_is_refused(session):
    from app.services.document_revisions import list_revisions

    a = await _put(session, "# A\n\nA.\n")
    b = await _put(session, "# B\n\nB.\n", uri="superpowers/specs/b.md")
    other = (await list_revisions(session, document_id=b.document_id))["items"][0]["id"]
    with pytest.raises(ValueError, match="names no revision"):
        await list_revisions(session, document_id=a.document_id, before=other)
    with pytest.raises(ValueError, match="not a revision id"):
        await list_revisions(session, document_id=a.document_id, before="nope")


@pytest.mark.parametrize("limit", [0, 201])
async def test_a_limit_out_of_range_is_refused(session, limit):
    from app.services.document_revisions import list_revisions

    with pytest.raises(ValueError, match="limit"):
        await list_revisions(session, document_id=uuid.uuid4(), limit=limit)


async def test_one_revision_carries_its_content_and_only_under_its_document(session):
    from app.services.document_revisions import get_revision, list_revisions

    a = await _put(session, "# A\n\nFirst.\n")
    b = await _put(session, "# B\n\nB.\n", uri="superpowers/specs/b.md")
    revision_id = (await list_revisions(session, document_id=a.document_id))["items"][0]["id"]

    one = await get_revision(session, document_id=a.document_id, revision_id=revision_id)
    assert one["content"] == "# A\n\nFirst.\n"
    assert one["document_id"] == a.document_id
    assert one["content_hash"] == a.content_hash
    assert await get_revision(session, document_id=b.document_id, revision_id=revision_id) is None

"""The `documents` / `blocks` writer — identity and the change gate (TH1.02).

Two properties carry this module, and both are written to be hard to pass by
accident.

**Zero work is counted, not inferred.** A test that re-files a document and
checks the row count is unchanged proves nothing: a writer that re-parsed,
stripped, re-embedded and wrote an identical-looking tree passes it. So the
unchanged path is asserted against five independent witnesses — the parse
callable was never invoked, the engine issued exactly one statement and it was
a SELECT, every block kept the id it had (ids are minted fresh on every write,
so any rewrite renames them all), the document tuple's ``ctid`` did not move
(any UPDATE relocates it, including one writing the values already there), and
the journal gained no second row.

**The constraint is the database's.** The writer resolving to one row is not
the same claim as the uniqueness holding; a writer with the resolve deleted
would still look correct in a single-session test. So the partial unique index
is also probed directly, with the writer out of the way.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError

from app.repositories import documents as documents_repo
from app.services import document_ingest as di
from app.services.document_ingest import (
    CREATED,
    UNCHANGED,
    UPDATED,
    BlockDraft,
    compute_content_hash,
    file_document,
)

from .conftest import test_engine


class _StatementRecorder:
    """Every statement the engine issues while it is attached, in order."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    def __call__(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    @property
    def writes(self) -> list[str]:
        return [
            statement
            for statement in self.statements
            if not statement.lstrip().upper().startswith(("SELECT", "WITH"))
        ]


class _Parser:
    """A parse callable that counts its own invocations."""

    def __init__(self, drafts) -> None:
        self.drafts = list(drafts)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.drafts


def _drafts(*texts: str) -> list[BlockDraft]:
    return [BlockDraft(text=t, type="paragraph") for t in texts]


async def _observe(coro_factory):
    """Run `coro_factory()` with every SQL statement recorded."""
    recorder = _StatementRecorder()
    event.listen(test_engine.sync_engine, "before_cursor_execute", recorder)
    try:
        result = await coro_factory()
    finally:
        event.remove(test_engine.sync_engine, "before_cursor_execute", recorder)
    return result, recorder


async def _block_ids(session, document_id) -> list[str]:
    rows = (await session.execute(
        text("SELECT id FROM blocks WHERE document_id = CAST(:d AS uuid) ORDER BY order_index"),
        {"d": str(document_id)},
    )).scalars().all()
    return [str(r) for r in rows]


async def _row_version(session, document_id) -> str:
    """The document tuple's physical location, which any UPDATE moves.

    Deliberately not ``updated_at``: the ``touch_updated_at`` trigger stamps
    ``now()``, which is transaction-start time, and this whole test runs in one
    transaction — so an ``updated_at`` comparison is equal whether or not the
    row was rewritten, and reads as a passing guard that can never fail.
    ``ctid`` moves on every update, including one that writes the values the
    row already had.
    """
    return str((await session.execute(
        text("SELECT ctid FROM documents WHERE id = CAST(:d AS uuid)"),
        {"d": str(document_id)},
    )).scalar_one())


async def _filed_events(session, document_id) -> int:
    return (await session.execute(
        text("SELECT count(*) FROM events WHERE object_type = 'document' "
             "AND event_type = 'document_filed' AND object_id = CAST(:d AS uuid)"),
        {"d": str(document_id)},
    )).scalar_one()


# ── the change gate: an unchanged document does zero work ───────────


@pytest.mark.asyncio
async def test_reingesting_an_unchanged_document_does_zero_work(session):
    content = "# Title\n\nA paragraph.\n"
    uri = f"file:///corpus/{uuid4()}.md"
    parser = _Parser(_drafts("Title", "A paragraph."))

    first = await file_document(
        session, project="default", uri=uri, content=content, parse=parser,
        title="Title", source_type="md",
    )
    await session.flush()
    assert first.outcome == CREATED
    assert parser.calls == 1

    before_ids = await _block_ids(session, first.document_id)
    before_version = await _row_version(session, first.document_id)
    assert len(before_ids) == 2

    second_parser = _Parser(_drafts("Title", "A paragraph."))
    second, recorder = await _observe(lambda: file_document(
        session, project="default", uri=uri, content=content, parse=second_parser,
        title="Title", source_type="md",
    ))

    assert second.outcome == UNCHANGED
    assert second.document_id == first.document_id

    # 1. the expensive half of the pipeline never ran
    assert second_parser.calls == 0, "the parser ran behind the change gate"

    # 2. nothing was written — not a row, not a journal entry, not a savepoint
    assert recorder.writes == [], (
        "the unchanged path issued write statements:\n" + "\n".join(recorder.writes)
    )
    assert len(recorder.statements) == 1, (
        "the unchanged path should cost exactly one resolving SELECT, got:\n"
        + "\n".join(recorder.statements)
    )

    # 3. no block was rewritten — ids are minted fresh on every write, so an
    #    identical-looking rewrite renames all of them
    assert await _block_ids(session, first.document_id) == before_ids

    # 4. the document row itself was not rewritten — see `_row_version`
    assert await _row_version(session, first.document_id) == before_version

    # 5. nothing downstream gained a row
    assert await _filed_events(session, first.document_id) == 1


@pytest.mark.asyncio
async def test_changed_content_does_the_whole_pipeline(session):
    """The counterpart. Without it, a writer that short-circuits everything
    passes the zero-work test perfectly."""
    uri = f"file:///corpus/{uuid4()}.md"
    parser = _Parser(_drafts("one"))
    first = await file_document(
        session, project="default", uri=uri, content="one", parse=parser,
    )
    await session.flush()
    before_ids = await _block_ids(session, first.document_id)
    before_version = await _row_version(session, first.document_id)

    second_parser = _Parser(_drafts("one", "two"))
    second = await file_document(
        session, project="default", uri=uri, content="one two", parse=second_parser,
    )
    await session.flush()

    assert second.outcome == UPDATED
    assert second.document_id == first.document_id
    assert second_parser.calls == 1
    assert second.blocks_stripped == 1
    assert second.blocks_written == 2

    after_ids = await _block_ids(session, first.document_id)
    assert len(after_ids) == 2
    assert not set(after_ids) & set(before_ids), "a stripped block id survived"
    assert await _row_version(session, first.document_id) != before_version
    assert await _filed_events(session, first.document_id) == 2


@pytest.mark.asyncio
async def test_the_gate_keys_on_content_and_says_so_about_metadata(session):
    """Re-filing identical content under a new title short-circuits, and the
    title does not move. That is the gate's declared cost (module docstring),
    pinned here so it stays a decision rather than becoming a bug report."""
    uri = f"file:///corpus/{uuid4()}.md"
    await file_document(
        session, project="default", uri=uri, content="same", title="first",
        parse=_Parser(_drafts("same")),
    )
    await session.flush()

    result = await file_document(
        session, project="default", uri=uri, content="same", title="second",
        parse=_Parser(_drafts("same")),
    )
    assert result.outcome == UNCHANGED

    title = (await session.execute(
        text("SELECT title FROM documents WHERE id = CAST(:d AS uuid)"),
        {"d": str(result.document_id)},
    )).scalar_one()
    assert title == "first"


@pytest.mark.asyncio
async def test_a_document_with_no_content_hash_is_not_unchanged(session):
    """A row filed before the gate existed (or by any other writer) carries a
    NULL hash. NULL must read as "differs", never as "nothing to do"."""
    doc_id = uuid4()
    await session.execute(
        text("INSERT INTO documents (id, project, uri, content_hash) "
             "VALUES (CAST(:d AS uuid), 'default', :u, NULL)"),
        {"d": str(doc_id), "u": f"file:///legacy/{doc_id}.md"},
    )
    parser = _Parser(_drafts("body"))
    result = await file_document(
        session, project="default", uri=f"file:///legacy/{doc_id}.md",
        content="body", parse=parser,
    )
    assert result.outcome == UPDATED
    assert result.document_id == doc_id
    assert parser.calls == 1


@pytest.mark.asyncio
async def test_the_hash_is_the_same_for_text_and_its_utf8_bytes(session):
    assert compute_content_hash("héllo") == compute_content_hash("héllo".encode())


# ── identity: the partial unique constraint ─────────────────────────


@pytest.mark.asyncio
async def test_refiling_a_uri_resolves_to_one_document(session):
    uri = f"file:///corpus/{uuid4()}.md"
    first = await file_document(
        session, project="default", uri=uri, content="v1", parse=_Parser(_drafts("v1")),
    )
    second = await file_document(
        session, project="default", uri=uri, content="v2", parse=_Parser(_drafts("v2")),
    )
    await session.flush()

    assert second.document_id == first.document_id
    count = (await session.execute(
        text("SELECT count(*) FROM documents WHERE project='default' AND uri = :u"),
        {"u": uri},
    )).scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test_the_same_uri_in_another_project_is_another_document(session):
    uri = f"file:///corpus/{uuid4()}.md"
    a = await file_document(
        session, project="default", uri=uri, content="x", parse=_Parser(_drafts("x")),
    )
    b = await file_document(
        session, project="research", uri=uri, content="x", parse=_Parser(_drafts("x")),
    )
    await session.flush()
    assert a.document_id != b.document_id


@pytest.mark.asyncio
async def test_many_uri_less_documents_coexist(session):
    """The `WHERE uri IS NOT NULL` half. Without the partial predicate the
    second note would collide with the first on (project, NULL)."""
    ids = set()
    for n in range(3):
        result = await file_document(
            session, project="default", content=f"note {n}", parse=_Parser(_drafts("n")),
        )
        ids.add(result.document_id)
    await session.flush()
    assert len(ids) == 3


@pytest.mark.asyncio
async def test_a_note_is_refiled_by_id(session):
    first = await file_document(
        session, project="default", content="draft", parse=_Parser(_drafts("draft")),
    )
    await session.flush()
    unchanged = await file_document(
        session, project="default", document_id=first.document_id, content="draft",
        parse=_Parser(_drafts("draft")),
    )
    assert unchanged.outcome == UNCHANGED
    assert unchanged.document_id == first.document_id


@pytest.mark.asyncio
async def test_naming_both_identities_is_refused(session):
    with pytest.raises(ValueError, match="never both"):
        await file_document(
            session, project="default", uri="file:///a.md", document_id=uuid4(),
            content="x", parse=_Parser(_drafts("x")),
        )


@pytest.mark.asyncio
async def test_the_partial_unique_index_refuses_a_duplicate_uri(session):
    """Probed with the writer out of the way: the writer resolving to one row
    and the constraint holding are two different claims."""
    uri = f"file:///corpus/{uuid4()}.md"
    insert = text(
        "INSERT INTO documents (id, project, uri) "
        "VALUES (CAST(:d AS uuid), 'default', :u)"
    )
    async with session.begin_nested() as savepoint:
        await session.execute(insert, {"d": str(uuid4()), "u": uri})
        with pytest.raises(IntegrityError):
            await session.execute(insert, {"d": str(uuid4()), "u": uri})
        await savepoint.rollback()


@pytest.mark.asyncio
async def test_a_racing_filer_folds_onto_the_existing_row(session, monkeypatch):
    """The resolve is an optimisation; the constraint is the guarantee. With
    the resolve blinded — which is what a concurrent filer looks like from
    inside this session — the write must land on the existing row."""
    uri = f"file:///corpus/{uuid4()}.md"
    first = await file_document(
        session, project="default", uri=uri, content="v1", parse=_Parser(_drafts("v1")),
    )
    await session.flush()

    async def _blind(*args, **kwargs):
        return None

    monkeypatch.setattr(documents_repo, "resolve_by_uri", _blind)
    second = await file_document(
        session, project="default", uri=uri, content="v2", parse=_Parser(_drafts("v2")),
    )
    await session.flush()

    assert second.document_id == first.document_id
    assert second.outcome == UPDATED
    count = (await session.execute(
        text("SELECT count(*) FROM documents WHERE uri = :u"), {"u": uri},
    )).scalar_one()
    assert count == 1


# ── blocks: strip-before-rewrite, tree, spans, closed type ──────────


@pytest.mark.asyncio
async def test_the_strip_is_scoped_to_the_document(session):
    keep = await file_document(
        session, project="default", uri=f"file:///{uuid4()}.md", content="keep",
        parse=_Parser(_drafts("keep-a", "keep-b")),
    )
    target_uri = f"file:///{uuid4()}.md"
    await file_document(
        session, project="default", uri=target_uri, content="v1",
        parse=_Parser(_drafts("v1")),
    )
    await session.flush()
    keep_ids = await _block_ids(session, keep.document_id)

    await file_document(
        session, project="default", uri=target_uri, content="v2",
        parse=_Parser(_drafts("v2")),
    )
    await session.flush()

    assert await _block_ids(session, keep.document_id) == keep_ids


@pytest.mark.asyncio
async def test_the_block_tree_and_spans_land(session):
    drafts = [
        BlockDraft(text="Heading", type="heading", char_span=(0, 7)),
        BlockDraft(text="Body", type="paragraph", parent=0, char_span=(8, 12)),
    ]
    result = await file_document(
        session, project="default", uri=f"file:///{uuid4()}.md", content="Heading\nBody",
        parse=lambda: drafts,
    )
    await session.flush()

    rows = (await session.execute(
        text("SELECT type, parent_id, order_index, lower(char_span) AS lo, "
             "upper(char_span) AS hi FROM blocks "
             "WHERE document_id = CAST(:d AS uuid) ORDER BY order_index"),
        {"d": str(result.document_id)},
    )).mappings().all()

    assert [r["type"] for r in rows] == ["heading", "paragraph"]
    assert rows[0]["parent_id"] is None
    assert rows[1]["parent_id"] is not None
    assert (rows[0]["lo"], rows[0]["hi"]) == (0, 7)
    assert (rows[1]["lo"], rows[1]["hi"]) == (8, 12)


@pytest.mark.asyncio
async def test_deleting_a_document_takes_its_blocks(session):
    result = await file_document(
        session, project="default", uri=f"file:///{uuid4()}.md", content="x",
        parse=_Parser(_drafts("a", "b")),
    )
    await session.flush()
    await session.execute(
        text("DELETE FROM documents WHERE id = CAST(:d AS uuid)"),
        {"d": str(result.document_id)},
    )
    assert await _block_ids(session, result.document_id) == []


@pytest.mark.asyncio
async def test_a_forward_parent_reference_is_refused(session):
    with pytest.raises(ValueError, match="earlier draft"):
        await file_document(
            session, project="default", uri=f"file:///{uuid4()}.md", content="x",
            parse=lambda: [
                BlockDraft(text="child", parent=1),
                BlockDraft(text="parent"),
            ],
        )


@pytest.mark.asyncio
async def test_a_self_parent_reference_is_refused(session):
    with pytest.raises(ValueError, match="earlier draft"):
        await file_document(
            session, project="default", uri=f"file:///{uuid4()}.md", content="x",
            parse=lambda: [BlockDraft(text="loop", parent=0)],
        )


@pytest.mark.asyncio
async def test_an_untabled_block_type_is_normalised_not_stored(session):
    result = await file_document(
        session, project="default", uri=f"file:///{uuid4()}.md", content="x",
        parse=lambda: [
            BlockDraft(text="a", type="Fence"),
            BlockDraft(text="b", type="quasar-block"),
            BlockDraft(text="c", type="BLOCKQUOTE"),
        ],
    )
    await session.flush()
    types = (await session.execute(
        text("SELECT type FROM blocks WHERE document_id = CAST(:d AS uuid) "
             "ORDER BY order_index"),
        {"d": str(result.document_id)},
    )).scalars().all()
    assert types == ["code", "paragraph", "quote"]


@pytest.mark.asyncio
async def test_a_document_with_no_blocks_is_lawful(session):
    result = await file_document(
        session, project="default", uri=f"file:///{uuid4()}.md", content="",
        parse=lambda: [],
    )
    await session.flush()
    assert result.blocks_written == 0
    assert await _block_ids(session, result.document_id) == []


# ── the journal ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_filing_journals_once_and_carries_no_block_text(session):
    body = "a very quotable sentence"
    result = await file_document(
        session, project="default", uri=f"file:///{uuid4()}.md", content=body,
        parse=_Parser(_drafts(body)),
    )
    await session.flush()

    row = (await session.execute(
        text("SELECT payload FROM events WHERE object_id = CAST(:d AS uuid) "
             "AND event_type = 'document_filed'"),
        {"d": str(result.document_id)},
    )).mappings().one()
    payload = row["payload"]
    assert payload["outcome"] == CREATED
    assert payload["content_hash"] == result.content_hash
    assert payload["blocks_written"] == 1
    assert body not in str(payload), "the journal payload copied block content"


def test_the_event_and_object_types_are_in_the_closed_vocabularies():
    from app.services.events import EVENT_TYPES, OBJECT_TYPES

    assert di.DOCUMENT_FILED_EVENT in EVENT_TYPES
    assert di.OBJECT_TYPE in OBJECT_TYPES

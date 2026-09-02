"""One document is one origin, whatever its block count (TH1.12, doc 16 §5).

The rule is an independence rule, and the test that matters is the one that
would catch its opposite: a document that mentions the same claim in many
blocks must not corroborate itself. Keying the origin on the block would
manufacture an origin per mention and promote an opinion on the strength of its
own repetition — the exact failure `COUNT(DISTINCT origin_key)` exists to
prevent, and the failure a per-document test with one block cannot see.

So the central test files a **three-block** document, records all three, and
asserts the distinct-origin count is one. Its counterpart files two documents
and asserts the count is two, because a module that returned a constant would
pass the first test alone.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.repositories.fact_sources import (
    BLOCK_SOURCE_KIND,
    SOURCE_KINDS,
    FactSourceRepository,
    _RESERVED_SOURCE_KINDS,
)
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.block_fact_sources import (
    record_block_source,
    withdraw_blocks,
    withdraw_document,
)
from app.services.document_ingest import BlockDraft, file_document
from app.services.triple_key import compute_triple_key

pytestmark = pytest.mark.asyncio

PROJECT = "th112-docs"


async def _fact(session, *, subject: str = "postgres") -> str:
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=compute_triple_key(PROJECT, subject, "RUNS_ON", "linux"),
        subject_name=subject,
        object_name="linux",
        rel_type="RUNS_ON",
        fact=f"{subject} runs on linux",
        reference_time=datetime(2026, 8, 16, tzinfo=timezone.utc),
        project=PROJECT,
    )
    return row["id"]


async def _file(session, *texts: str, uri: str | None = None) -> tuple[str, list[str]]:
    drafts = [BlockDraft(text=t, type="paragraph") for t in texts]
    ingest = await file_document(
        session, project=PROJECT, content="\n\n".join(texts),
        parse=lambda: drafts, title="doc", source_type="note", uri=uri,
    )
    await session.flush()
    blocks = [str(r) for r in (await session.execute(
        text("SELECT id FROM blocks WHERE document_id = CAST(:d AS uuid) ORDER BY order_index"),
        {"d": str(ingest.document_id)},
    )).scalars().all()]
    return str(ingest.document_id), blocks


# ── the closed set gained its producer ───────────────────────────────


def test_block_is_now_an_assertable_kind_and_no_longer_reserved():
    assert BLOCK_SOURCE_KIND in SOURCE_KINDS
    assert BLOCK_SOURCE_KIND not in _RESERVED_SOURCE_KINDS


def test_document_stays_reserved_and_says_where_to_go():
    """Doc 08 §4.1 names a `document` origin; doc 04 §8.3's column vocabulary
    has no such value. A caller following the former must be told where
    document content actually lands rather than silently refused."""
    assert "document" not in SOURCE_KINDS
    assert "block" in _RESERVED_SOURCE_KINDS["document"]


# ── one document, one origin ─────────────────────────────────────────


async def test_three_blocks_of_one_document_are_one_origin(session):
    """The rule. A document repeating a claim must not corroborate itself."""
    fact_id = await _fact(session)
    _document_id, blocks = await _file(
        session, "Postgres runs on linux.", "It runs on linux.", "Again: linux.",
    )

    for block_id in blocks:
        assert await record_block_source(session, fact_id=fact_id, block_id=block_id)

    count = await FactSourceRepository(session).count_distinct_origins(fact_id)
    assert count == 1, "a document's blocks must collapse to one origin"


async def test_two_documents_are_two_origins(session):
    """The counterpart: without this, a module returning a constant 1 passes
    the rule above and destroys corroboration everywhere."""
    fact_id = await _fact(session)
    _first, first_blocks = await _file(session, "Postgres runs on linux.", uri="file:///a")
    _second, second_blocks = await _file(session, "Confirmed: linux.", uri="file:///b")

    await record_block_source(session, fact_id=fact_id, block_id=first_blocks[0])
    await record_block_source(session, fact_id=fact_id, block_id=second_blocks[0])

    count = await FactSourceRepository(session).count_distinct_origins(fact_id)
    assert count == 2


async def test_the_origin_is_the_document_and_the_ref_is_the_block(session):
    """Origin is about independence, ref about traceability. Collapsing them in
    either direction loses one of the two."""
    fact_id = await _fact(session)
    document_id, blocks = await _file(session, "Postgres runs on linux.")

    await record_block_source(session, fact_id=fact_id, block_id=blocks[0])

    row = (await session.execute(
        text(
            "SELECT source_ref, origin_key FROM fact_sources "
            "WHERE fact_id = CAST(:f AS uuid) AND source_kind = :k"
        ),
        {"f": fact_id, "k": BLOCK_SOURCE_KIND},
    )).mappings().one()
    assert row["source_ref"] == blocks[0]
    assert row["origin_key"] == document_id


async def test_a_block_that_does_not_exist_records_nothing(session):
    """A source pointing at nothing would count toward a fact's independence
    forever."""
    fact_id = await _fact(session)

    assert await record_block_source(
        session, fact_id=fact_id, block_id="11111111-1111-1111-1111-111111111111",
    ) is None
    assert await FactSourceRepository(session).count_distinct_origins(fact_id) == 0


# ── withdrawal closes the window ─────────────────────────────────────


async def test_withdrawing_a_document_removes_its_sources_and_names_the_facts(session):
    fact_id = await _fact(session)
    document_id, blocks = await _file(session, "One.", "Two.")
    for block_id in blocks:
        await record_block_source(session, fact_id=fact_id, block_id=block_id)

    withdrawal = await withdraw_document(session, document_id=document_id)

    assert withdrawal.blocks == 2
    assert withdrawal.sources_removed == 2
    assert withdrawal.facts_enqueued == (fact_id,), "the fact that lost a source is named once"
    assert await FactSourceRepository(session).count_distinct_origins(fact_id) == 0


async def test_withdrawal_leaves_another_documents_sources_alone(session):
    fact_id = await _fact(session)
    first_id, first_blocks = await _file(session, "One.", uri="file:///first")
    _second_id, second_blocks = await _file(session, "Two.", uri="file:///second")
    await record_block_source(session, fact_id=fact_id, block_id=first_blocks[0])
    await record_block_source(session, fact_id=fact_id, block_id=second_blocks[0])

    await withdraw_document(session, document_id=first_id)

    assert await FactSourceRepository(session).count_distinct_origins(fact_id) == 1


async def test_withdrawal_writes_no_verification_column(session):
    """The ladder decides what remaining corroboration is worth. A withdrawal
    that wrote a rung would be a second authority over that column."""
    fact_id = await _fact(session)
    document_id, blocks = await _file(session, "One.")
    await record_block_source(session, fact_id=fact_id, block_id=blocks[0])
    before = (await session.execute(
        text("SELECT verification_status FROM knowledge_triples WHERE id = CAST(:f AS uuid)"),
        {"f": fact_id},
    )).scalar_one()

    await withdraw_document(session, document_id=document_id)

    after = (await session.execute(
        text("SELECT verification_status FROM knowledge_triples WHERE id = CAST(:f AS uuid)"),
        {"f": fact_id},
    )).scalar_one()
    assert after == before


async def test_withdrawing_a_document_with_no_blocks_is_a_no_op(session):
    withdrawal = await withdraw_document(
        session, document_id="22222222-2222-2222-2222-222222222222",
    )
    assert withdrawal.blocks == 0
    assert withdrawal.facts_enqueued == ()


# ── Subtree-scoped withdrawal (increment 8, Task 3) ──────────────────


async def test_withdraw_blocks_leaves_a_sibling_block_standing(session):
    """A block delete removes one subtree, not the document, so only that
    subtree's provenance goes. Withdrawing more would silently strip evidence
    the caller never deleted."""
    fact_id = await _fact(session)
    document_id, blocks = await _file(
        session, "Postgres runs on linux.", "A second claim.", uri="file:///sub",
    )
    for block_id in blocks:
        await record_block_source(session, fact_id=fact_id, block_id=block_id)

    withdrawal = await withdraw_blocks(
        session, block_ids=[blocks[0]], document_id=document_id,
    )
    assert withdrawal.sources_removed == 1
    assert withdrawal.blocks == 1

    # The sibling's source survives, so the fact still has evidence.
    remaining = (await session.execute(
        text(
            "SELECT count(*) FROM fact_sources "
            "WHERE fact_id = CAST(:f AS uuid) AND source_ref = CAST(:b AS text)"
        ),
        {"f": str(fact_id), "b": blocks[1]},
    )).scalar_one()
    assert remaining == 1


async def test_withdraw_document_still_takes_every_block(session):
    """The delegation must not narrow the document-scoped behaviour."""
    fact_id = await _fact(session)
    document_id, blocks = await _file(
        session, "Postgres runs on linux.", "A second claim.", uri="file:///whole",
    )
    for block_id in blocks:
        await record_block_source(session, fact_id=fact_id, block_id=block_id)

    withdrawal = await withdraw_document(session, document_id=document_id)
    assert withdrawal.sources_removed == len(blocks)

    left = (await session.execute(
        text("SELECT count(*) FROM fact_sources WHERE fact_id = CAST(:f AS uuid)"),
        {"f": str(fact_id)},
    )).scalar_one()
    assert left == 0


async def test_withdrawing_no_blocks_writes_nothing(session):
    """block_delete on a subtree that sourced no fact must be a no-op rather
    than a delete with an empty IN list."""
    withdrawal = await withdraw_blocks(
        session, block_ids=[], document_id="00000000-0000-0000-0000-000000000000",
    )
    assert withdrawal.sources_removed == 0
    assert withdrawal.facts_enqueued == ()

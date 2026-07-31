"""The enqueue-for-verification emit hook (doc 05 §8.4, doc 08 §3.3).

Three properties carry the contract, and every one of them fails silently
rather than loudly:

1. **Vocabulary first.** ``sources_changed`` and the ``fact`` object type must
   already be in the closed ``events`` vocabularies, or every emit below
   journals a row while logging a warning nobody reads.
2. **The provenance no-op guard.** A strip-and-rewrite landing the identical
   source set must emit nothing. Without it every reprocess of every memory
   reads as evidence churn and the Tier-C recompute thrashes
   ``corroborated <-> candidate`` on facts whose evidence never moved.
3. **Inline expiry on last-source withdrawal.** A fact whose last source was
   just withdrawn must stop being served in the same transaction, not on the
   next Tier-C tick.

Events are asserted by a direct read of ``events`` throughout — never by a
return value — because the drain (T2.09) reads the table, not this module's
signature.

The pipeline-level tests reuse ``test_pipeline_savepoints``'s bed: Phase 5
opens and commits its own session through ``session_factory``, so it cannot run
on the conftest ``session`` fixture. Rows in ``events`` are deliberately left
behind — that table is append-only by trigger, so the session-end schema reset
is its only cleanup.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.repositories.fact_sources import FactSourceRepository
from app.repositories.graph import PostgresGraphRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.events import EVENT_TYPES, OBJECT_TYPES
from app.services.fact_provenance import (
    MEMORY_SOURCE_KIND,
    memory_source_ref,
    reconcile_memory_sources,
    withdraw_memory_sources,
)
from app.services.triple_key import compute_triple_key
from tests.test_pipeline_savepoints import EXTRACTION, VECTOR, savepoint_bed

NOW = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)


async def seed_fact(session, *, subject, rel_type, obj, project="default") -> dict:
    return await KnowledgeTripleRepository(session).insert_open(
        triple_key=compute_triple_key(project, subject, rel_type, obj),
        subject_name=subject,
        object_name=obj,
        rel_type=rel_type,
        fact=f"{subject} {rel_type} {obj}",
        reference_time=NOW,
        project=project,
    )


async def seed_source(session, *, fact_id, memory_id, origin_key="session-a") -> dict:
    return await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=MEMORY_SOURCE_KIND,
        source_ref=memory_source_ref(memory_id),
        origin_key=origin_key,
    )


async def seed_relation(session, *, memory_id, subject, rel_type, obj) -> None:
    repo = PostgresGraphRepository(session)
    await repo.create_entity(
        name=subject, entity_type="tool", properties={}, memory_id=memory_id
    )
    await repo.create_entity(
        name=obj, entity_type="tool", properties={}, memory_id=memory_id
    )
    await repo.create_relationship(
        source_name=subject,
        target_name=obj,
        rel_type=rel_type,
        properties={},
        weight=0.9,
        memory_id=memory_id,
        source_type="tool",
        target_type="tool",
    )


async def emitted(session, memory_id) -> list[dict]:
    rows = await session.execute(
        text(
            "SELECT object_id, project, payload FROM events "
            "WHERE event_type = 'sources_changed' "
            "AND payload->>'memory_id' = CAST(:m AS text) "
            "ORDER BY created_at, id"
        ),
        {"m": str(memory_id)},
    )
    return [dict(row) for row in rows.mappings().all()]


async def expired_at(session, fact_id):
    return (
        await session.execute(
            text("SELECT expired_at FROM knowledge_triples WHERE id = CAST(:f AS uuid)"),
            {"f": str(fact_id)},
        )
    ).scalar_one()


async def source_rows(session, fact_id) -> int:
    return (
        await session.execute(
            text("SELECT count(*) FROM fact_sources WHERE fact_id = CAST(:f AS uuid)"),
            {"f": str(fact_id)},
        )
    ).scalar_one()


# ── Done-when 1: the vocabulary landed before any emitter ────────────────────


def test_sources_changed_is_already_in_the_closed_event_vocabulary():
    """Taxonomy-first, the events-vocab analog of the LLM taxonomy rule.

    ``record_event`` does not reject an unknown value — it logs a warning and
    writes the row anyway — so an emitter shipped ahead of its vocabulary
    entry produces a journal that looks correct and a warning nobody reads.
    Both halves of the shape §8.4 fixes are asserted: the event type and the
    ``fact`` object type it is emitted under.
    """
    assert "sources_changed" in EVENT_TYPES
    assert "fact" in OBJECT_TYPES


# ── Done-when 2: the provenance no-op guard ──────────────────────────────────


@pytest.mark.asyncio
async def test_an_identical_source_set_emits_nothing(session):
    """The guard with teeth: a rewrite landing the same facts is not evidence."""
    memory_id = uuid.uuid4()
    await seed_relation(
        session, memory_id=memory_id, subject="pgvector", rel_type="REPLACES", obj="faiss"
    )
    fact = await seed_fact(session, subject="pgvector", rel_type="REPLACES", obj="faiss")
    await seed_source(session, fact_id=fact["id"], memory_id=memory_id)

    affected = await reconcile_memory_sources(session, memory_id=memory_id)

    assert affected == []
    assert await emitted(session, memory_id) == []
    assert await source_rows(session, fact["id"]) == 1
    assert await expired_at(session, fact["id"]) is None


@pytest.mark.asyncio
async def test_a_changed_source_set_emits_one_row_per_affected_fact(session):
    """Exactly one row per fact that lost this memory's support, and none for
    the fact the rewrite still asserts."""
    memory_id = uuid.uuid4()
    await seed_relation(
        session, memory_id=memory_id, subject="pgvector", rel_type="REPLACES", obj="faiss"
    )
    kept = await seed_fact(session, subject="pgvector", rel_type="REPLACES", obj="faiss")
    dropped = await seed_fact(session, subject="redis", rel_type="USES", obj="lua")
    await seed_source(session, fact_id=kept["id"], memory_id=memory_id)
    await seed_source(session, fact_id=dropped["id"], memory_id=memory_id)

    affected = await reconcile_memory_sources(session, memory_id=memory_id)

    assert affected == [dropped["id"]]
    rows = await emitted(session, memory_id)
    assert len(rows) == 1
    assert str(rows[0]["object_id"]) == dropped["id"]
    assert rows[0]["project"] == "default"
    assert rows[0]["payload"] == {
        "fact_id": dropped["id"],
        "memory_id": str(memory_id),
    }
    assert await source_rows(session, dropped["id"]) == 0
    assert await source_rows(session, kept["id"]) == 1


@pytest.mark.asyncio
async def test_re_extraction_that_drops_every_relation_withdraws_everything(session):
    """A memory whose rewrite asserts nothing sources nothing.

    The retained set is read back from the graph, so an empty graph is not a
    reason to skip the sweep — it is the strongest possible reason to run it.
    """
    memory_id = uuid.uuid4()
    fact = await seed_fact(session, subject="pgvector", rel_type="REPLACES", obj="faiss")
    await seed_source(session, fact_id=fact["id"], memory_id=memory_id)

    affected = await reconcile_memory_sources(session, memory_id=memory_id)

    assert affected == [fact["id"]]
    assert len(await emitted(session, memory_id)) == 1


# ── Done-when 3: inline expiry on last-source withdrawal ─────────────────────


@pytest.mark.asyncio
async def test_losing_the_last_source_expires_the_triple_inline(session):
    """Read back in the same transaction, before any commit: a fact whose last
    source is gone must stop being served now, not on the next Tier-C tick."""
    memory_id = uuid.uuid4()
    fact = await seed_fact(session, subject="redis", rel_type="USES", obj="lua")
    await seed_source(session, fact_id=fact["id"], memory_id=memory_id)

    await withdraw_memory_sources(session, memory_id=memory_id)

    assert await expired_at(session, fact["id"]) is not None
    live = await KnowledgeTripleRepository(session).get_live(
        project="default", triple_key=fact["triple_key"]
    )
    assert live == []


@pytest.mark.asyncio
async def test_withdrawing_a_source_that_is_not_the_last_leaves_the_fact_live(session):
    """Belief is withdrawn on *no* surviving source, never on one fewer."""
    memory_id = uuid.uuid4()
    other_memory_id = uuid.uuid4()
    fact = await seed_fact(session, subject="redis", rel_type="USES", obj="lua")
    await seed_source(session, fact_id=fact["id"], memory_id=memory_id)
    await seed_source(
        session, fact_id=fact["id"], memory_id=other_memory_id, origin_key="session-b"
    )

    affected = await withdraw_memory_sources(session, memory_id=memory_id)

    assert affected == [fact["id"]]
    assert await expired_at(session, fact["id"]) is None
    assert await source_rows(session, fact["id"]) == 1
    assert len(await emitted(session, memory_id)) == 1


@pytest.mark.asyncio
async def test_an_already_expired_fact_is_enqueued_without_rewriting_its_expiry(session):
    """A fact disbelieved once keeps when. The enqueue still fires: its origin
    profile changed even though its belief did not."""
    memory_id = uuid.uuid4()
    fact = await seed_fact(session, subject="redis", rel_type="USES", obj="lua")
    await seed_source(session, fact_id=fact["id"], memory_id=memory_id)
    withdrawn_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    await session.execute(
        text(
            "UPDATE knowledge_triples SET expired_at = CAST(:e AS timestamptz) "
            "WHERE id = CAST(:f AS uuid)"
        ),
        {"e": withdrawn_at, "f": fact["id"]},
    )

    await withdraw_memory_sources(session, memory_id=memory_id)

    assert await expired_at(session, fact["id"]) == withdrawn_at
    assert len(await emitted(session, memory_id)) == 1


@pytest.mark.asyncio
async def test_provenance_is_withdrawn_across_projects(session):
    """``source_ref`` is a memory id — globally unique, one row, one owner — so
    the sweep is not project-scoped. A memory moved between projects must not
    strand the provenance it wrote under its former scope."""
    memory_id = uuid.uuid4()
    fact = await seed_fact(
        session, subject="redis", rel_type="USES", obj="lua", project="legacy"
    )
    await seed_source(session, fact_id=fact["id"], memory_id=memory_id)

    affected = await reconcile_memory_sources(session, memory_id=memory_id)

    assert affected == [fact["id"]]
    rows = await emitted(session, memory_id)
    assert [row["project"] for row in rows] == ["legacy"]


@pytest.mark.asyncio
async def test_a_fact_still_asserted_in_a_non_default_project_is_retained(session):
    """The retention key is computed per the *fact's* project, not a fixed one.

    ``compute_triple_key`` embeds ``project`` verbatim, so the same
    subject/predicate/object yields a different key in every scope. Computing
    the retained set under any one project would leave a fact that is still
    asserted in another scope matching nothing — withdrawing its provenance,
    inline-expiring a belief nothing had withdrawn, and emitting the spurious
    ``sources_changed`` the no-op guard exists to prevent. The expiry is the
    part that does not heal: ``expire`` COALESCEs, so the first timestamp
    sticks and a later correct sweep cannot undo it.

    The withdrawal-arm test above cannot catch this — it seeds no graph, so its
    retained set is empty whatever project it is computed under. This one seeds
    the assertion, so the key must match for the row to survive.
    """
    memory_id = uuid.uuid4()
    await seed_relation(
        session, memory_id=memory_id, subject="pgvector", rel_type="REPLACES", obj="faiss"
    )
    fact = await seed_fact(
        session,
        subject="pgvector",
        rel_type="REPLACES",
        obj="faiss",
        project="legacy",
    )
    await seed_source(session, fact_id=fact["id"], memory_id=memory_id)

    affected = await reconcile_memory_sources(session, memory_id=memory_id)

    assert affected == []
    assert await emitted(session, memory_id) == []
    assert await source_rows(session, fact["id"]) == 1
    assert await expired_at(session, fact["id"]) is None


# ── Phase 5 and the deletion sweep, end to end ───────────────────────────────


@pytest.mark.asyncio
async def test_phase_five_emits_when_a_re_extraction_drops_a_fact(setup_database):
    """The hook wired into savepoint B, driven through the real write."""
    async with savepoint_bed(["pgvector replaces faiss"], "sources-drop|4") as bed:
        async with bed.factory() as s:
            kept = await seed_fact(
                s, subject="pgvector", rel_type="REPLACES", obj="faiss"
            )
            dropped = await seed_fact(s, subject="redis", rel_type="USES", obj="lua")
            await seed_source(s, fact_id=kept["id"], memory_id=bed.memory_id)
            await seed_source(s, fact_id=dropped["id"], memory_id=bed.memory_id)
            await s.commit()

        try:
            status = await bed.pipe._write_memory(
                bed.entry(content="pgvector replaces faiss"),
                VECTOR, bed.fingerprint, bed.fingerprint,
                dict(EXTRACTION), None, {}, {},
            )
            assert status["graph"] == "ok"

            async with bed.factory() as s:
                rows = await emitted(s, bed.memory_id)
                assert len(rows) == 1
                assert str(rows[0]["object_id"]) == dropped["id"]
                assert await expired_at(s, dropped["id"]) is not None
                assert await expired_at(s, kept["id"]) is None
                assert await source_rows(s, kept["id"]) == 1
        finally:
            await drop_facts(bed.factory, [kept["id"], dropped["id"]])


@pytest.mark.asyncio
async def test_phase_five_emits_nothing_when_the_source_set_is_unchanged(setup_database):
    """The no-op guard through the real write: reprocessing is not churn."""
    async with savepoint_bed(["pgvector replaces faiss"], "sources-noop|4") as bed:
        async with bed.factory() as s:
            fact = await seed_fact(
                s, subject="pgvector", rel_type="REPLACES", obj="faiss"
            )
            await seed_source(s, fact_id=fact["id"], memory_id=bed.memory_id)
            await s.commit()

        try:
            for _ in range(2):
                status = await bed.pipe._write_memory(
                    bed.entry(content="pgvector replaces faiss"),
                    VECTOR, bed.fingerprint, bed.fingerprint,
                    dict(EXTRACTION), None, {}, {},
                )
                assert status["graph"] == "ok"

            async with bed.factory() as s:
                assert await emitted(s, bed.memory_id) == []
                assert await source_rows(s, fact["id"]) == 1
                assert await expired_at(s, fact["id"]) is None
        finally:
            await drop_facts(bed.factory, [fact["id"]])


@pytest.mark.asyncio
async def test_a_rolled_back_savepoint_b_leaves_no_sources_changed_row(
    setup_database, monkeypatch
):
    """Failure *before* the hook: savepoint B never reaches it, and the prior
    graph — and therefore the prior provenance — survives untouched."""
    import app.services.pipeline as pipeline_module

    async def _boom(*a, **k):
        raise RuntimeError("supersession boom")

    async with savepoint_bed(["pgvector replaces faiss"], "sources-rollback|4") as bed:
        async with bed.factory() as s:
            fact = await seed_fact(s, subject="redis", rel_type="USES", obj="lua")
            await seed_source(s, fact_id=fact["id"], memory_id=bed.memory_id)
            await s.commit()

        try:
            monkeypatch.setattr(pipeline_module, "detect_supersessions", _boom)
            status = await bed.pipe._write_memory(
                bed.entry(content="pgvector replaces faiss"),
                VECTOR, bed.fingerprint, bed.fingerprint,
                dict(EXTRACTION), None, {}, {},
            )

            assert status["vector"] == "ok"
            assert status["graph"] == "error"
            async with bed.factory() as s:
                assert await emitted(s, bed.memory_id) == []
                assert await source_rows(s, fact["id"]) == 1
                assert await expired_at(s, fact["id"]) is None
        finally:
            await drop_facts(bed.factory, [fact["id"]])


@pytest.mark.asyncio
async def test_the_emit_rolls_back_with_savepoint_b(setup_database, monkeypatch):
    """Failure *after* the hook — the placement proof.

    The hook runs for real, withdraws the row, expires the triple and journals
    the event; then savepoint B fails. Every one of those has to unwind with
    the graph replace that justified them. An emit sitting outside the
    savepoint (after the commit, as doc 05 §8's flowchart node ordering
    suggests) would leave a withdrawn belief and an append-only event row
    behind for a graph rewrite that never landed.
    """
    import app.services.pipeline as pipeline_module

    real_hook = pipeline_module.reconcile_memory_sources

    async def _hook_then_boom(session, **kwargs):
        await real_hook(session, **kwargs)
        raise RuntimeError("post-hook boom")

    async with savepoint_bed(["pgvector replaces faiss"], "sources-atomic|4") as bed:
        async with bed.factory() as s:
            fact = await seed_fact(s, subject="redis", rel_type="USES", obj="lua")
            await seed_source(s, fact_id=fact["id"], memory_id=bed.memory_id)
            await s.commit()

        try:
            monkeypatch.setattr(
                pipeline_module, "reconcile_memory_sources", _hook_then_boom
            )
            status = await bed.pipe._write_memory(
                bed.entry(content="pgvector replaces faiss"),
                VECTOR, bed.fingerprint, bed.fingerprint,
                dict(EXTRACTION), None, {}, {},
            )

            assert status["vector"] == "ok"
            assert status["graph"] == "error"
            async with bed.factory() as s:
                assert await emitted(s, bed.memory_id) == []
                assert await source_rows(s, fact["id"]) == 1
                assert await expired_at(s, fact["id"]) is None
        finally:
            await drop_facts(bed.factory, [fact["id"]])


@pytest.mark.asyncio
async def test_deleting_a_memory_withdraws_its_sources_and_enqueues(setup_database):
    """The second emitter: the deletion sweep, through ``delete_memory``."""
    async with savepoint_bed(["pgvector replaces faiss"], "sources-delete|4") as bed:
        async with bed.factory() as s:
            fact = await seed_fact(
                s, subject="pgvector", rel_type="REPLACES", obj="faiss"
            )
            await seed_source(s, fact_id=fact["id"], memory_id=bed.memory_id)
            await s.commit()

        try:
            await bed.pipe.delete_memory(bed.memory_id, broadcast=False)

            async with bed.factory() as s:
                rows = await emitted(s, bed.memory_id)
                assert len(rows) == 1
                assert str(rows[0]["object_id"]) == fact["id"]
                assert await source_rows(s, fact["id"]) == 0
                assert await expired_at(s, fact["id"]) is not None
        finally:
            await drop_facts(bed.factory, [fact["id"]])


async def drop_facts(factory, fact_ids) -> None:
    async with factory() as s:
        await s.execute(
            text("DELETE FROM knowledge_triples WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(f) for f in fact_ids]},
        )
        await s.commit()

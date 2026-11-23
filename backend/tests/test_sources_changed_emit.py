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

from app.models.memory import Memory
from app.repositories.fact_sources import FactSourceRepository
from app.repositories.graph import PostgresGraphRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.events import EVENT_TYPES, OBJECT_TYPES
from app.services.fact_provenance import (
    MEMORY_SOURCE_KIND,
    memory_source_ref,
    reap_orphaned_memory_sources,
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


async def seed_source_of_kind(
    session, *, fact_id, source_kind, source_ref, origin_key="session-x"
) -> dict:
    return await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=source_kind,
        source_ref=source_ref,
        origin_key=origin_key,
    )


async def seed_memory(session) -> uuid.UUID:
    memory = Memory(content="a live memory", source="test")
    session.add(memory)
    await session.flush()
    return memory.id


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


# ── The backstop: provenance whose memory is gone, whatever stranded it ──────


def only_mine(affected: list[str], *fact_ids) -> list[str]:
    """Narrow a whole-vault scan's result to the rows this test planted.

    ``reap_orphaned_memory_sources`` has no scope argument — it sweeps every
    ``fact_sources`` row — so asserting exact equality against its return value
    would make these tests fail the day another suite leaks a committed orphan.
    The planted set is the only thing a test can soundly reason about.
    """
    mine = {str(f) for f in fact_ids}
    return [f for f in affected if f in mine]


@pytest.mark.asyncio
async def test_the_backstop_reaps_provenance_whose_memory_is_gone(session):
    """A reaper that reaps nothing is the defect; this proves it reaps.

    Routing the TTL sweep closes the paths that *skip* withdrawal. It cannot
    close ``ProcessingPipeline.delete_memory``, which swallows a withdrawal
    that fails — nothing bypassed the hook there, so there is no bypass to
    route, only stranded rows to heal. The end state is what this test plants:
    a ``('memory', ref)`` row whose ``memories`` row no longer exists.
    """
    gone = uuid.uuid4()
    fact = await seed_fact(session, subject="redis", rel_type="USES", obj="lua")
    await seed_source(session, fact_id=fact["id"], memory_id=gone)

    affected = await reap_orphaned_memory_sources(session)

    assert only_mine(affected, fact["id"]) == [fact["id"]]
    assert await source_rows(session, fact["id"]) == 0
    assert await expired_at(session, fact["id"]) is not None
    rows = await emitted(session, gone)
    assert len(rows) == 1
    assert rows[0]["payload"] == {"fact_id": fact["id"], "memory_id": str(gone)}


@pytest.mark.asyncio
async def test_the_backstop_never_reaps_a_non_memory_source(session):
    """The destructive-failure guard, and the most important test here.

    ``source_ref`` carries no type discriminator — the kind lives in
    ``source_kind`` — so "no ``memories`` row matches this ref" means orphaned
    *only* for the ``memory`` kind. A human reviewer's ref and a repository id
    match no ``memories`` row **by construction**; a predicate that ignored
    ``source_kind`` would reap every one of them, destroying live provenance and
    expiring the facts they solely source. That is strictly worse than the
    stranding the backstop exists to heal.

    Both survivors carry uuid-shaped refs on purpose: a predicate that merely
    skipped unparseable refs would still destroy them, so only the ``source_kind``
    filter can save these rows. The memory-kind orphan alongside them proves the
    reaper ran and discriminated rather than finding nothing to do.
    """
    gone = uuid.uuid4()
    reviewer_ref = str(uuid.uuid4())
    repo_ref = str(uuid.uuid4())
    orphan_fact = await seed_fact(session, subject="redis", rel_type="USES", obj="lua")
    human_fact = await seed_fact(session, subject="celery", rel_type="USES", obj="redis")
    code_fact = await seed_fact(session, subject="uvicorn", rel_type="USES", obj="httptools")
    await seed_source(session, fact_id=orphan_fact["id"], memory_id=gone)
    await seed_source_of_kind(
        session, fact_id=human_fact["id"], source_kind="human", source_ref=reviewer_ref
    )
    await seed_source_of_kind(
        session, fact_id=code_fact["id"], source_kind="code", source_ref=repo_ref
    )

    affected = await reap_orphaned_memory_sources(session)

    assert only_mine(
        affected, orphan_fact["id"], human_fact["id"], code_fact["id"]
    ) == [orphan_fact["id"]]
    assert await source_rows(session, human_fact["id"]) == 1
    assert await source_rows(session, code_fact["id"]) == 1
    assert await expired_at(session, human_fact["id"]) is None
    assert await expired_at(session, code_fact["id"]) is None
    assert await emitted(session, reviewer_ref) == []
    assert await emitted(session, repo_ref) == []


@pytest.mark.asyncio
async def test_the_backstop_leaves_provenance_whose_memory_still_exists(session):
    """Orphanhood is the missing ``memories`` row, not the ``memory`` kind.

    Without the existence test the backstop would withdraw every memory-sourced
    row in the vault on its first tick and expire every fact with it.
    """
    live = await seed_memory(session)
    fact = await seed_fact(session, subject="redis", rel_type="USES", obj="lua")
    await seed_source(session, fact_id=fact["id"], memory_id=live)

    affected = await reap_orphaned_memory_sources(session)

    assert only_mine(affected, fact["id"]) == []
    assert await source_rows(session, fact["id"]) == 1
    assert await expired_at(session, fact["id"]) is None
    assert await emitted(session, live) == []


@pytest.mark.asyncio
async def test_the_backstop_expires_on_no_surviving_source_never_on_one_fewer(session):
    """The backstop reaches the same expiry rule as the by-memory entries."""
    gone = uuid.uuid4()
    live = await seed_memory(session)
    fact = await seed_fact(session, subject="redis", rel_type="USES", obj="lua")
    await seed_source(session, fact_id=fact["id"], memory_id=gone)
    await seed_source(
        session, fact_id=fact["id"], memory_id=live, origin_key="session-b"
    )

    affected = await reap_orphaned_memory_sources(session)

    assert only_mine(affected, fact["id"]) == [fact["id"]]
    assert await source_rows(session, fact["id"]) == 1
    assert await expired_at(session, fact["id"]) is None
    assert len(await emitted(session, gone)) == 1


@pytest.mark.asyncio
async def test_the_backstop_emits_nothing_when_nothing_is_orphaned(session):
    """A tick with nothing to reap is a no-op on every observable surface.

    This does **not** pin ``_withdraw``'s ``if not rows: return []``. That early
    return is unobservable — delete it and the zero-row loop below it still
    emits nothing — so it is a cost saving and a statement of intent, not a
    guard, and no test here claims otherwise. What this does pin is the
    predicate's direction: a reaper that selected live rows would fail here.
    """
    live = await seed_memory(session)
    fact = await seed_fact(session, subject="redis", rel_type="USES", obj="lua")
    await seed_source(session, fact_id=fact["id"], memory_id=live)

    assert only_mine(await reap_orphaned_memory_sources(session), fact["id"]) == []
    count = await session.execute(
        text(
            "SELECT count(*) FROM events WHERE event_type = 'sources_changed' "
            "AND object_id = CAST(:f AS uuid)"
        ),
        {"f": fact["id"]},
    )
    assert count.scalar_one() == 0
    assert await source_rows(session, fact["id"]) == 1


@pytest.mark.asyncio
async def test_the_backstop_never_reaps_a_ref_naming_a_live_memory(session):
    """Reaping is the anti-join's *default*, so a ref it cannot read is spared.

    A ref carrying a live memory's id in a non-canonical spelling matches no
    ``CAST(memories.id AS text)``, so an unguarded ``NOT EXISTS`` deletes it and
    expires the fact it solely sources — destroying provenance whose memory is
    sitting right there, and inverting what ``memory_source_ref``'s docstring
    promises a producer: that a mis-spelled ref is invisible to the sweep, not
    deleted by it.

    The ruling this pins is that the conservative reading wins. "Never
    withdrawn" is a stranding a later fix can repair; "reaped" cannot be undone,
    and ``expire`` COALESCEs so even the timestamp sticks.
    """
    live = await seed_memory(session)
    gone = uuid.uuid4()
    braced = await seed_fact(session, subject="ruff", rel_type="USES", obj="rust")
    upper = await seed_fact(session, subject="mypy", rel_type="USES", obj="python")
    orphan = await seed_fact(session, subject="esbuild", rel_type="USES", obj="go")
    await seed_source_of_kind(
        session,
        fact_id=braced["id"],
        source_kind=MEMORY_SOURCE_KIND,
        source_ref=f"{{{live}}}",
    )
    await seed_source_of_kind(
        session,
        fact_id=upper["id"],
        source_kind=MEMORY_SOURCE_KIND,
        source_ref=str(live).upper(),
    )
    await seed_source(session, fact_id=orphan["id"], memory_id=gone)

    affected = await reap_orphaned_memory_sources(session)

    assert only_mine(affected, braced["id"], upper["id"], orphan["id"]) == [
        orphan["id"]
    ]
    assert await source_rows(session, braced["id"]) == 1
    assert await source_rows(session, upper["id"]) == 1
    assert await expired_at(session, braced["id"]) is None
    assert await expired_at(session, upper["id"]) is None


def test_the_minted_ref_matches_the_shape_the_backstop_trusts():
    """The producer and the reaper's shape filter must not drift apart.

    ``_CANONICAL_REF`` decides which refs the backstop is willing to delete, and
    ``memory_source_ref`` decides which refs get written. If the pattern ever
    stopped matching what the minter emits, the backstop would silently stop
    reaping real orphans; if it widened, it would start reaping spellings the
    minter never produces. Neither has a symptom, so the coupling is pinned
    here rather than left to the two definitions sitting near each other.
    """
    import re

    from app.services.fact_provenance import _CANONICAL_REF

    for _ in range(64):
        assert re.match(_CANONICAL_REF, memory_source_ref(uuid.uuid4()))

    sample = uuid.uuid4()
    for rejected in (
        str(sample).upper(),
        f"{{{sample}}}",
        f" {sample} ",
        str(sample).replace("-", ""),
        "reviewer:alice",
    ):
        assert not re.match(_CANONICAL_REF, rejected), rejected


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


class _SqlState(Exception):
    def __init__(self, sqlstate: str):
        super().__init__(f"sqlstate {sqlstate}")
        self.sqlstate = sqlstate


async def _seed_written_memory_with_source(bed, subject: str) -> dict:
    status = await bed.pipe._write_memory(
        bed.entry(content="pgvector replaces faiss"),
        VECTOR, bed.fingerprint, bed.fingerprint,
        dict(EXTRACTION), None, {}, {},
    )
    assert status["graph"] == "ok", status
    async with bed.factory() as s:
        fact = await seed_fact(s, subject=subject, rel_type="USES", obj="postgres")
        await seed_source(s, fact_id=fact["id"], memory_id=bed.memory_id)
        await s.commit()
    return fact


@pytest.mark.asyncio
async def test_a_delete_that_loses_one_deadlock_still_strips(setup_database, monkeypatch):
    from sqlalchemy.exc import DBAPIError

    async with savepoint_bed(["pgvector replaces faiss"], "delete-deadlock|4") as bed:
        fact = await _seed_written_memory_with_source(bed, f"delete-deadlock-{uuid.uuid4()}")
        assert await bed.entity_names()
        real_strip = PostgresGraphRepository.delete_by_memory_id
        calls = 0

        async def deadlock_once(self, memory_id):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise DBAPIError("UPDATE entities", {}, _SqlState("40P01"))
            return await real_strip(self, memory_id)

        monkeypatch.setattr(PostgresGraphRepository, "delete_by_memory_id", deadlock_once)
        try:
            await bed.pipe.delete_memory(bed.memory_id, broadcast=False)

            assert calls == 2
            assert await bed.entity_names() == set()
            assert await bed.embedding_rows() == 0
            async with bed.factory() as s:
                assert await source_rows(s, fact["id"]) == 0
        finally:
            await drop_facts(bed.factory, [fact["id"]])


@pytest.mark.asyncio
async def test_a_withdrawal_lock_timeout_keeps_the_strip(setup_database, monkeypatch, caplog):
    import asyncio
    import logging

    from app.services import fact_provenance

    async with savepoint_bed(["pgvector replaces faiss"], "delete-locked|4") as bed:
        fact = await _seed_written_memory_with_source(bed, f"delete-locked-{uuid.uuid4()}")
        monkeypatch.setattr(fact_provenance, "WITHDRAWAL_LOCK_TIMEOUT", "200ms")
        caplog.set_level(logging.WARNING, logger="app.services.pipeline")
        try:
            async with bed.factory() as holder:
                await holder.execute(
                    text("SELECT 1 FROM knowledge_triples WHERE id = CAST(:id AS uuid) FOR UPDATE"),
                    {"id": str(fact["id"])},
                )
                await asyncio.wait_for(
                    bed.pipe.delete_memory(bed.memory_id, broadcast=False), 5,
                )
                await holder.rollback()

            assert await bed.embedding_rows() == 0
            assert await bed.entity_names() == set()
            async with bed.factory() as s:
                assert await source_rows(s, fact["id"]) == 1
            warnings = [
                r.getMessage() for r in caplog.records
                if r.name == "app.services.pipeline"
                and r.levelno == logging.WARNING
                and "55P03" in r.getMessage()
            ]
            assert len(warnings) == 1, warnings
        finally:
            await drop_facts(bed.factory, [fact["id"]])


@pytest.mark.asyncio
async def test_a_strip_defect_is_logged_with_its_traceback(setup_database, monkeypatch, caplog):
    """Only contention is the heal's to cover quietly; a defect must be seen."""
    import logging

    async with savepoint_bed(["pgvector replaces faiss"], "delete-defect|4") as bed:
        async def broken_strip(self, memory_id):
            raise RuntimeError("strip defect")

        monkeypatch.setattr(PostgresGraphRepository, "delete_by_memory_id", broken_strip)
        caplog.set_level(logging.WARNING, logger="app.services.pipeline")

        await bed.pipe.delete_memory(bed.memory_id, broadcast=False)

        errors = [
            r for r in caplog.records
            if r.name == "app.services.pipeline" and r.levelno == logging.ERROR
            and "Graph strip failed" in r.getMessage()
        ]
        assert len(errors) == 1
        assert errors[0].exc_info is not None
        assert await bed.embedding_rows() == 0


@pytest.mark.asyncio
async def test_withdrawal_restores_the_callers_lock_timeout(setup_database):
    async with savepoint_bed(["pgvector replaces faiss"], "delete-timeout|4") as bed:
        async with bed.factory() as s:
            fact = await seed_fact(
                s, subject=f"delete-timeout-{uuid.uuid4()}", rel_type="USES", obj="postgres",
            )
            await seed_source(s, fact_id=fact["id"], memory_id=bed.memory_id)
            await s.execute(text("SELECT set_config('lock_timeout', '7s', true)"))

            await withdraw_memory_sources(s, memory_id=bed.memory_id)

            assert (await s.execute(
                text("SELECT current_setting('lock_timeout')")
            )).scalar_one() == "7s"
            assert await source_rows(s, fact["id"]) == 0
            await s.rollback()

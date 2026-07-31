"""T2.62 — ``review_state`` opens on the veto and clears on recovery.

``ix_knowledge_triples_review`` has been partial on the literal ``'open'``
since T0.12b with no writer, so a fact the contradiction veto disputed never
reached doc 08 §6's review queue and nothing cleared the flag when the
contradiction resolved. This suite pins the writer, and — the part that is the
whole task — the **precedence** rule that keeps the clear from dropping a fact
off the queue while another opener still owns it.

Organised by Done-when clause, same convention as the sibling ladder/veto
suites.

**One thing this suite deliberately does not claim.** The Done-when text asks
that ``disputed``-but-unqueued not be a *reachable* state, and the strongest
reading of that is "no concurrent reader ever observes one column moved without
the other". A live two-connection race test is not constructible honestly here:
the ``session`` fixture runs inside an outer transaction that is never
committed, so a second connection sees none of the rows under test, and a
version built on real commits would prove Postgres's statement atomicity rather
than anything about this code. What *is* constructible, and is what
``TestOneStatement`` asserts instead, is the structural property the atomicity
rests on — the two columns are assigned by one UPDATE statement, issued inside
the ``FOR UPDATE`` window ``recompute_fact`` already holds. Read the absence of
a race test as scope, not as a passing race test.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from app.repositories.fact_sources import FactSourceRepository, OriginProfile
from app.repositories.knowledge_triples import (
    REVIEW_STATE_OPEN,
    KnowledgeTripleRepository,
)
from app.services import verification_ladder
from app.services.verification_ladder import (
    NO_DETECTOR,
    LadderConfig,
    LadderDecision,
    decide,
    derive_review_state,
    recompute_fact,
)

T0 = datetime(2025, 6, 20, 12, 0, 0, tzinfo=timezone.utc)


async def _fact(session, *, subject: str, rel: str, obj: str, key: str | None = None) -> str:
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=key or f"{subject}|{rel}|{obj}",
        subject_name=subject,
        object_name=obj,
        rel_type=rel,
        fact=f"{subject} {rel} {obj}",
        reference_time=T0,
        project="default",
    )
    await session.commit()
    return row["id"]


async def _source(session, fact_id, origin_key, *, kind="memory") -> None:
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=kind,
        source_ref=f"{kind}:{origin_key}:{fact_id}",
        origin_key=origin_key,
    )
    await session.commit()


async def _read(session, fact_id) -> dict:
    result = await session.execute(
        text(
            "SELECT verification_status, review_state, confidence "
            "FROM knowledge_triples WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )
    return dict(result.mappings().one())


async def _on_review_queue(session) -> set[str]:
    """Exactly doc 08 §6's queue predicate, and the partial index's."""
    result = await session.execute(
        text("SELECT id FROM knowledge_triples WHERE review_state = 'open'")
    )
    return {str(row[0]) for row in result.all()}


async def _set_review_state_raw(session, fact_id, value: str | None) -> None:
    """Seed the column *around* the writer under test, never through it."""
    await session.execute(
        text(
            "UPDATE knowledge_triples SET review_state = CAST(:v AS text) "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"v": value, "id": str(fact_id)},
    )
    await session.commit()


async def _verified_events(session, fact_id) -> list[dict]:
    result = await session.execute(
        text(
            "SELECT payload FROM events WHERE event_type = 'verified' "
            "AND object_id = CAST(:id AS uuid) ORDER BY created_at, id"
        ),
        {"id": str(fact_id)},
    )
    return [row[0] for row in result.all()]


async def _disputed_pair(session, *, tag: str) -> tuple[str, str]:
    """A fact and a counterpart that vetoes it, through the real detector.

    ``inverse_replacement`` is the deterministic scan's whole reach today
    (``SINGLE_VALUED_RELATIONS`` is empty), so the contradiction has to be a
    REPLACES-family edge asserted in both directions between the same pair, and
    the counterpart has to carry an origin the subject does not.
    """
    first, second = f"{tag}-a", f"{tag}-b"
    subject = await _fact(session, subject=first, rel="REPLACES", obj=second)
    counterpart = await _fact(session, subject=second, rel="REPLACES", obj=first)
    await _source(session, subject, f"{tag}-sess-1")
    await _source(session, subject, f"{tag}-sess-2", kind="code")
    await _source(session, counterpart, f"{tag}-witness")
    return subject, counterpart


async def _resolve_the_contradiction(session, counterpart) -> None:
    """Withdraw belief in the counterpart. The scan skips expired rows."""
    await KnowledgeTripleRepository(session).expire(counterpart)
    await session.commit()


@contextlib.contextmanager
def _captured_sql() -> Iterator[list[str]]:
    statements: list[str] = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(Engine, "before_cursor_execute", _record)
    try:
        yield statements
    finally:
        event.remove(Engine, "before_cursor_execute", _record)


def _decision(*, target: str, current: str = "candidate", outcome: str = "hold") -> LadderDecision:
    return LadderDecision(
        fact_id="f",
        current_status=current,
        target_status=target,
        outcome=outcome,
        origin_count=1,
        required_n=2,
        gate_fired="none",
        source_kinds=("memory",),
        contradiction_blocked=False,
        confidence=0.6,
    )


# ─────────── D1 — the veto opens the flag, under the status write ───────────


class TestTheVetoOpensTheQueue:
    async def test_a_disputed_fact_is_on_the_review_queue(self, session):
        """The clause the missing writer broke: disputed implies queued."""
        subject, _ = await _disputed_pair(session, tag="open")

        decision = await recompute_fact(session, subject)
        await session.commit()

        assert decision.outcome == "dispute"
        assert subject in await _on_review_queue(session)

    async def test_the_status_and_the_flag_are_read_back_together(self, session):
        """One read, both columns — no window in which only one has moved."""
        subject, _ = await _disputed_pair(session, tag="together")

        await recompute_fact(session, subject)
        await session.commit()

        row = await _read(session, subject)
        assert (row["verification_status"], row["review_state"]) == (
            "disputed",
            REVIEW_STATE_OPEN,
        )

    async def test_an_undisputed_fact_never_joins_the_queue(self, session):
        """The control. Without it every assertion above could pass on a
        writer that opens the flag for every fact it touches."""
        fact_id = await _fact(session, subject="darkmem", rel="USES", obj="pgvector")
        await _source(session, fact_id, "sess-a")
        await _source(session, fact_id, "repo-b", kind="code")

        decision = await recompute_fact(session, fact_id)
        await session.commit()

        assert decision.outcome == "promote"
        assert (await _read(session, fact_id))["review_state"] is None
        assert fact_id not in await _on_review_queue(session)

    async def test_a_reconfirmed_dispute_stays_queued(self, session):
        """The ``contradiction_blocked`` hold: status unchanged, still queued.

        Doc 08 §4.2's standing dispute re-adjudicated across a cycle. The open
        is idempotent rather than a no-op the writer may skip, because a fact
        that is still disputed is still one the human has not seen.
        """
        subject, _ = await _disputed_pair(session, tag="reconfirm")
        await recompute_fact(session, subject)
        await session.commit()

        second = await recompute_fact(session, subject)
        await session.commit()

        assert (second.outcome, second.contradiction_blocked) == ("hold", True)
        assert (await _read(session, subject))["review_state"] == REVIEW_STATE_OPEN
        assert subject in await _on_review_queue(session)


class TestOneStatement:
    """The structural half of "not a reachable state" (see the module note)."""

    async def test_one_update_assigns_both_columns(self, session):
        subject, _ = await _disputed_pair(session, tag="onestmt")

        with _captured_sql() as statements:
            await recompute_fact(session, subject)
        await session.commit()

        writes = [s for s in statements if "UPDATE knowledge_triples" in s]
        status_writes = [s for s in writes if "verification_status =" in s]
        review_writes = [s for s in writes if "review_state =" in s]
        assert len(status_writes) == 1, statements
        assert review_writes == status_writes, (
            "review_state must ride the status UPDATE, not a second statement"
        )

    async def test_the_repository_method_is_the_writer(self, session):
        """Called directly, with no ladder above it, it still moves the flag.

        This is what makes the co-location a property of the sole
        verification-axis writer rather than of one caller's habit.
        """
        fact_id = await _fact(session, subject="direct", rel="USES", obj="x")

        await KnowledgeTripleRepository(session).set_verification_status(
            fact_id, "disputed", confidence=0.5, review_state=REVIEW_STATE_OPEN
        )
        await session.commit()

        row = await _read(session, fact_id)
        assert (row["verification_status"], row["review_state"]) == (
            "disputed",
            REVIEW_STATE_OPEN,
        )


# ──────────────────────── D2 — recovery clears it ────────────────────────


class TestRecoveryClears:
    async def test_resolving_the_contradiction_clears_the_flag(self, session):
        subject, counterpart = await _disputed_pair(session, tag="recover")
        await recompute_fact(session, subject)
        await session.commit()
        assert subject in await _on_review_queue(session)

        await _resolve_the_contradiction(session, counterpart)
        decision = await recompute_fact(session, subject)
        await session.commit()

        assert decision.outcome == "recover"
        row = await _read(session, subject)
        assert row["verification_status"] == "corroborated"
        assert row["review_state"] is None
        assert subject not in await _on_review_queue(session)

    def test_silence_from_the_detectors_does_not_clear_the_flag(self):
        """``NO_DETECTOR`` holds the dispute, so it must hold the queue entry.

        The mirror of T2.04's tri-state: a caller that ran no detector cannot
        resolve a dispute by silence, and must not be able to unqueue one
        either. Asserted against ``decide`` rather than ``recompute_fact``,
        because the applier resolves ``NO_DETECTOR`` by *running* the detectors
        — silence is not something a caller can hand it — so routing this
        through the applier would test the real veto over again and prove
        nothing about the third value.
        """
        held = decide(
            "f",
            "disputed",
            OriginProfile(fact_id="f", origins=()),
            LadderConfig(),
            open_contradiction=NO_DETECTOR,
        )

        assert (held.target_status, held.outcome) == ("disputed", "hold")
        assert derive_review_state(held) == REVIEW_STATE_OPEN


# ───── D3 — precedence: the clear is the absence of EVERY opener ─────


class TestPrecedence:
    """The clause this task exists for.

    ``review_state`` is a bare nullable TEXT column indexed partially on the
    literal ``'open'``, and doc 08 §6 gives it three independent openers. The
    ruling in ``derive_review_state`` settles it by derivation: the clear fires
    only when *no* registered opener holds. These tests fail if that becomes an
    unconditional clear.
    """

    async def test_a_second_openers_condition_survives_this_paths_recovery(
        self, session, monkeypatch
    ):
        """T2.46's hazard, stood in for by a registered opener.

        A fact that is disputed **and** held open by another condition must
        stay on the queue when only the contradiction resolves. T2.46 has not
        landed, so its predicate is stood in for here — which is the point of
        making the opener set a registered tuple rather than an ``if``.
        """
        subject, counterpart = await _disputed_pair(session, tag="twoopeners")
        await recompute_fact(session, subject)
        await session.commit()

        monkeypatch.setattr(
            verification_ladder,
            "REVIEW_OPENERS",
            (*verification_ladder.REVIEW_OPENERS, lambda decision: True),
        )
        await _resolve_the_contradiction(session, counterpart)
        decision = await recompute_fact(session, subject)
        await session.commit()

        assert decision.outcome == "recover", "the dispute really did resolve"
        assert (await _read(session, subject))["verification_status"] == "corroborated"
        assert (await _read(session, subject))["review_state"] == REVIEW_STATE_OPEN, (
            "another opener still owns this queue entry"
        )
        assert subject in await _on_review_queue(session)

    async def test_the_stand_in_opener_is_what_holds_it_not_the_recovery_path(
        self, session
    ):
        """The negative control for the test above.

        Without it, that test would pass on a recovery path that simply never
        clears anything, and clause 2 would be silently untested.
        """
        subject, counterpart = await _disputed_pair(session, tag="control")
        await recompute_fact(session, subject)
        await session.commit()

        await _resolve_the_contradiction(session, counterpart)
        await recompute_fact(session, subject)
        await session.commit()

        assert (await _read(session, subject))["review_state"] is None

    async def test_the_clear_does_not_stomp_a_value_it_could_not_have_written(
        self, session
    ):
        """A value with an owner this derivation cannot name is left alone."""
        fact_id = await _fact(session, subject="foreign", rel="USES", obj="y")
        await _source(session, fact_id, "sess-a")
        await _set_review_state_raw(session, fact_id, "held-by-hand")

        await recompute_fact(session, fact_id)
        await session.commit()

        assert (await _read(session, fact_id))["review_state"] == "held-by-hand"

    async def test_the_open_overrides_a_value_it_could_not_have_written(self, session):
        """Opening is unconditional: an unqueued dispute is the worse failure.

        The asymmetry with the test above is deliberate and argued in
        ``set_verification_status``'s docstring — adding to the queue hides
        nothing, removing from it can hide a fact permanently.
        """
        subject, _ = await _disputed_pair(session, tag="stomp")
        await _set_review_state_raw(session, subject, "held-by-hand")

        await recompute_fact(session, subject)
        await session.commit()

        assert (await _read(session, subject))["review_state"] == REVIEW_STATE_OPEN
        assert subject in await _on_review_queue(session)

    async def test_a_caller_with_no_opinion_leaves_the_column_alone(self, session):
        """``UNSET`` and ``None`` are different arguments, and must stay so.

        Collapsing them would make every bare-status caller drain the queue.
        """
        fact_id = await _fact(session, subject="unset", rel="USES", obj="z")
        await _set_review_state_raw(session, fact_id, REVIEW_STATE_OPEN)

        await KnowledgeTripleRepository(session).set_verification_status(
            fact_id, "corroborated"
        )
        await session.commit()

        row = await _read(session, fact_id)
        assert row["verification_status"] == "corroborated"
        assert row["review_state"] == REVIEW_STATE_OPEN

    async def test_an_explicit_none_clears_where_unset_did_not(self, session):
        fact_id = await _fact(session, subject="explicit", rel="USES", obj="z2")
        await _set_review_state_raw(session, fact_id, REVIEW_STATE_OPEN)

        await KnowledgeTripleRepository(session).set_verification_status(
            fact_id, "corroborated", review_state=None
        )
        await session.commit()

        assert (await _read(session, fact_id))["review_state"] is None

    async def test_a_bare_review_state_write_survives_the_early_return(self, session):
        """``review_state`` alone, with no status and no confidence, still writes.

        The early return fires on "nothing to write", and before T2.62 that
        was spelled ``status is None and confidence is None`` — a shape that
        would now swallow the whole argument. The caller shape is not
        hypothetical: T2.05's clear-on-ratify cannot pass a status
        (``confirmed`` is refused before any read) and has no confidence to
        refresh, so it is exactly this call.
        """
        fact_id = await _fact(session, subject="bare", rel="USES", obj="z3")
        await _set_review_state_raw(session, fact_id, REVIEW_STATE_OPEN)

        await KnowledgeTripleRepository(session).set_verification_status(
            fact_id, None, confidence=None, review_state=None
        )
        await session.commit()

        assert (await _read(session, fact_id))["review_state"] is None
        assert fact_id not in await _on_review_queue(session)

    async def test_a_bare_review_state_open_survives_the_early_return(self, session):
        """The same early return, from the other side."""
        fact_id = await _fact(session, subject="bare2", rel="USES", obj="z4")

        await KnowledgeTripleRepository(session).set_verification_status(
            fact_id, None, confidence=None, review_state=REVIEW_STATE_OPEN
        )
        await session.commit()

        assert (await _read(session, fact_id))["review_state"] == REVIEW_STATE_OPEN

    async def test_the_repository_refuses_a_review_state_it_cannot_own(self, session):
        """A label stored here is a row that has silently left the queue."""
        fact_id = await _fact(session, subject="label", rel="USES", obj="w")

        with pytest.raises(ValueError, match="review_state"):
            await KnowledgeTripleRepository(session).set_verification_status(
                fact_id, "candidate", review_state="under-sourced"
            )

    async def test_a_refused_review_state_writes_nothing(self, session):
        fact_id = await _fact(session, subject="label2", rel="USES", obj="w2")

        with pytest.raises(ValueError):
            await KnowledgeTripleRepository(session).set_verification_status(
                fact_id, "disputed", review_state="under-sourced"
            )

        row = await _read(session, fact_id)
        assert row["verification_status"] == "candidate"
        assert row["review_state"] is None


class TestTheDerivationItself:
    """The pure half — no session, no row, just the rule."""

    def test_only_a_disputed_target_opens_today(self):
        assert derive_review_state(_decision(target="disputed")) == REVIEW_STATE_OPEN
        for target in ("candidate", "corroborated", "confirmed"):
            assert derive_review_state(_decision(target=target)) is None

    def test_it_keys_off_the_target_not_the_outcome(self):
        """A reconfirmed dispute is a ``hold``, and must still open."""
        held = _decision(target="disputed", current="disputed", outcome="hold")
        assert derive_review_state(held) == REVIEW_STATE_OPEN

    def test_the_clear_is_the_absence_of_every_opener(self, monkeypatch):
        monkeypatch.setattr(
            verification_ladder,
            "REVIEW_OPENERS",
            (*verification_ladder.REVIEW_OPENERS, lambda decision: True),
        )
        for target in ("candidate", "corroborated", "confirmed", "disputed"):
            assert (
                verification_ladder.derive_review_state(_decision(target=target))
                == REVIEW_STATE_OPEN
            )

    def test_it_is_total_over_every_reachable_target(self):
        """No branch returns "no opinion" — that would restore the ambiguity."""
        for target in ("candidate", "corroborated", "disputed", "confirmed", "missing"):
            assert derive_review_state(_decision(target=target)) in (
                REVIEW_STATE_OPEN,
                None,
            )

    def test_the_opener_set_is_a_registry_not_a_hard_coded_branch(self):
        """T2.46 extends this tuple; it must not add a second writer."""
        assert isinstance(verification_ladder.REVIEW_OPENERS, tuple)
        assert len(verification_ladder.REVIEW_OPENERS) == 1


# ───────── D4 — the journal population and the memories axis ─────────


class TestTheVerifiedEventPopulationIsUnchanged:
    """``review_state`` movement is not a third journal trigger.

    G-C's promotion-rate SQL counts ``verified`` rows on "one row means one
    transition". The counts below are the pre-T2.62 population, asserted per
    transition kind so a new trigger cannot slip in unnoticed.
    """

    async def test_dispute_then_reconfirm_then_recover_journals_three(self, session):
        subject, counterpart = await _disputed_pair(session, tag="events")

        await recompute_fact(session, subject)  # candidate -> disputed
        await session.commit()
        assert len(await _verified_events(session, subject)) == 1

        await recompute_fact(session, subject)  # blocked hold, journals
        await session.commit()
        assert len(await _verified_events(session, subject)) == 2

        await _resolve_the_contradiction(session, counterpart)
        await recompute_fact(session, subject)  # recover
        await session.commit()
        events = await _verified_events(session, subject)
        assert len(events) == 3
        assert events[-1]["before"] == {"verification_status": "disputed"}
        assert events[-1]["after"] == {"verification_status": "corroborated"}

    async def test_an_ordinary_hold_still_journals_nothing(self, session):
        """The clear rides a real transition or nothing at all."""
        fact_id = await _fact(session, subject="hold", rel="USES", obj="q")
        await _source(session, fact_id, "sess-a")

        await recompute_fact(session, fact_id)  # candidate, below N -> hold
        await session.commit()
        await recompute_fact(session, fact_id)
        await session.commit()

        assert await _verified_events(session, fact_id) == []

    async def test_a_clear_over_a_foreign_value_journals_nothing_extra(self, session):
        fact_id = await _fact(session, subject="hold2", rel="USES", obj="q2")
        await _source(session, fact_id, "sess-a")
        await _set_review_state_raw(session, fact_id, "held-by-hand")

        await recompute_fact(session, fact_id)
        await session.commit()

        assert await _verified_events(session, fact_id) == []

    async def test_the_payload_shape_is_the_one_gc_reads(self, session):
        """The exact key set G-C's SQL reads — still no ``review_state`` in it.

        T2.62 added no key; T2.60 added exactly one, ``supersession_blocked``,
        under the ruling in ``verification_ladder.decide``'s docstring. The
        assertion stays an exact set rather than a subset check on purpose: a
        new key is what T2.51's ``KNOWN_PAYLOAD_KEYS`` guard refuses, so this
        is the coupling check that fails loudly if a key is added without the
        metrics runner's vocabulary being widened in step.
        """
        subject, _ = await _disputed_pair(session, tag="payload")

        await recompute_fact(session, subject)
        await session.commit()

        payload = (await _verified_events(session, subject))[0]
        assert set(payload) == {
            "before",
            "after",
            "outcome",
            "origin_count",
            "required_n",
            "gate_fired",
            "source_kinds",
            "contradiction_blocked",
            "supersession_blocked",
            "confidence",
        }


class TestTheMemoriesAxisIsUntouched:
    async def test_the_supersession_check_still_bites(self, session):
        """Clause 4 names ``chk_superseded_has_pointer``, which lives on
        ``memories`` and is nowhere near this change — the two files touched
        are the ladder and the triples repository, neither of which references
        ``memories``. ``tests/honesty/test_superseded_pointer.py`` is the
        standing guard; this asserts the constraint is still enforced after a
        run of the code under test, so "untouched" is evidence rather than an
        assertion.
        """
        subject, _ = await _disputed_pair(session, tag="memories")
        await recompute_fact(session, subject)
        await session.commit()

        result = await session.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conname = 'chk_superseded_has_pointer'"
            )
        )
        assert result.scalar_one_or_none() == "chk_superseded_has_pointer"

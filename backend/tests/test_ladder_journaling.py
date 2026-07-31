"""T2.06 — every ladder transition journaled, and the G-C metrics derivable
by SQL over ``events`` alone.

The first Done-when clause ("every transition writes an event with
before/after and the triggering evidence") was already nearly satisfied:
``recompute_fact`` is the sole writer of ``verification_status``
(``set_verification_status``, called once, under its ``FOR UPDATE`` lock), and
that method already journaled a bare before/after on every real status change.
What was missing, and what this suite pins:

1. The journal payload carries the full ``LadderDecision`` evidence
   (``outcome``, ``origin_count``, ``required_n``, ``gate_fired``,
   ``source_kinds``, ``contradiction_blocked``, ``confidence``) rather than
   just the two status keys — because G-C's promotion-rate and
   false-promotion-audit metrics must be computable from ``events`` alone,
   with no join back to ``knowledge_triples``.
2. A *contradiction-blocked* hold (the veto re-firing on an already-disputed
   fact, status unchanged) is journaled on purpose, unlike every other kind
   of hold — decided and justified in ``set_verification_status``'s
   docstring and re-asserted here.
3. The G-C metric SQL itself, run against seeded transitions, returning the
   exact expected numbers — the deliverable the brief calls "the whole task."

Organised by Done-when clause, same convention as the sibling ladder/veto
suites.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.repositories.fact_sources import FactSourceRepository as _FSR
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.verification_ladder import recompute_fact

T0 = datetime(2025, 6, 20, 12, 0, 0, tzinfo=timezone.utc)


async def _make_fact(session, *, key: str, status: str | None = None) -> str:
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=key,
        subject_name="darkmem",
        object_name=key,
        rel_type="USES",
        fact=f"darkmem uses {key}",
        reference_time=T0,
        project="default",
    )
    if status is not None:
        # Raw SQL, not `set_verification_status`: seeding the starting state
        # through the repository's own writer would itself journal a bare
        # candidate -> status transition, polluting the event count this
        # suite asserts on the *ladder's* transitions, not the fixture's.
        await session.execute(
            text(
                "UPDATE knowledge_triples SET verification_status = CAST(:status AS text) "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"status": status, "id": row["id"]},
        )
    await session.commit()
    return row["id"]


async def _add_origin(session, fact_id, origin_key, *, kind="memory") -> None:
    await _FSR(session).add_source(
        fact_id=fact_id,
        source_kind=kind,
        source_ref=f"{kind}:{origin_key}",
        origin_key=origin_key,
    )
    await session.commit()


async def _events_for(session, fact_id) -> list[dict]:
    result = await session.execute(
        text(
            "SELECT payload FROM events WHERE event_type = 'verified' "
            "AND object_id = CAST(:id AS uuid) ORDER BY created_at, id"
        ),
        {"id": str(fact_id)},
    )
    return [row[0] for row in result.all()]


# ───────────────────────── D1 — every transition journals ─────────────────────────


class TestEveryTransitionJournals:
    async def test_promote_journals_exactly_one_event_with_full_evidence(self, session):
        fact_id = await _make_fact(session, key="promote-1")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")

        decision = await recompute_fact(session, fact_id)
        await session.commit()

        assert decision.outcome == "promote"
        events = await _events_for(session, fact_id)
        assert len(events) == 1
        payload = events[0]
        assert payload["before"] == {"verification_status": "candidate"}
        assert payload["after"] == {"verification_status": "corroborated"}
        assert payload["outcome"] == "promote"
        assert payload["origin_count"] == 2
        assert payload["required_n"] == 2
        assert payload["gate_fired"] == "diversity"
        assert sorted(payload["source_kinds"]) == ["code", "memory"]
        assert payload["contradiction_blocked"] is False
        assert payload["confidence"] == pytest.approx(0.90, abs=5e-5)

    async def test_demote_journals_exactly_one_event(self, session):
        fact_id = await _make_fact(session, key="demote-1", status="corroborated")
        await _add_origin(session, fact_id, "sess-a", kind="memory")

        decision = await recompute_fact(session, fact_id)
        await session.commit()

        assert decision.outcome == "demote"
        events = await _events_for(session, fact_id)
        assert len(events) == 1
        assert events[0]["before"] == {"verification_status": "corroborated"}
        assert events[0]["after"] == {"verification_status": "candidate"}
        assert events[0]["outcome"] == "demote"

    async def test_dispute_journals_exactly_one_event(self, session):
        fact_id = await _make_fact(session, key="dispute-1")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")

        decision = await recompute_fact(session, fact_id, open_contradiction=True)
        await session.commit()

        assert decision.outcome == "dispute"
        events = await _events_for(session, fact_id)
        assert len(events) == 1
        assert events[0]["after"] == {"verification_status": "disputed"}
        assert events[0]["outcome"] == "dispute"
        assert events[0]["contradiction_blocked"] is True

    async def test_recover_journals_exactly_one_event(self, session):
        fact_id = await _make_fact(session, key="recover-1")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        await recompute_fact(session, fact_id, open_contradiction=True)
        await session.commit()

        decision = await recompute_fact(session, fact_id, open_contradiction=False)
        await session.commit()

        assert decision.outcome == "recover"
        assert decision.target_status == "corroborated"
        events = await _events_for(session, fact_id)
        assert len(events) == 2, "the dispute and the recovery are two transitions"
        assert events[1]["before"] == {"verification_status": "disputed"}
        assert events[1]["after"] == {"verification_status": "corroborated"}
        assert events[1]["outcome"] == "recover"

    async def test_a_contradiction_blocked_hold_journals_despite_no_status_change(
        self, session
    ):
        """The deliberate exception: not a transition, but evidence G-C needs.

        A re-run over a standing dispute leaves ``verification_status``
        unchanged (``disputed -> disputed``), so it is not a transition by the
        before/after definition every other test in this class uses. But the
        veto is *still firing* on this recompute cycle, which is exactly the
        ongoing-contradiction evidence the false-promotion audit and any
        veto-persistence metric would otherwise have to reconstruct from
        ``knowledge_triples`` state — the join the brief forbids. So this one
        hold journals on purpose; every other hold in this suite (below)
        proves the negative case.
        """
        fact_id = await _make_fact(session, key="blocked-hold-1")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        await recompute_fact(session, fact_id, open_contradiction=True)
        await session.commit()

        decision = await recompute_fact(session, fact_id, open_contradiction=True)
        await session.commit()

        assert (decision.target_status, decision.outcome) == ("disputed", "hold")
        assert decision.contradiction_blocked is True
        events = await _events_for(session, fact_id)
        assert len(events) == 2
        second = events[1]
        assert second["before"] == {"verification_status": "disputed"}
        assert second["after"] == {"verification_status": "disputed"}
        assert second["outcome"] == "hold"
        assert second["contradiction_blocked"] is True

    async def test_an_unblocked_candidate_hold_journals_nothing(self, session):
        """Below N, no contradiction: not eligible, not a transition, silent."""
        fact_id = await _make_fact(session, key="plain-hold-1")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "sess-b", kind="memory")

        decision = await recompute_fact(session, fact_id)
        await session.commit()

        assert decision.outcome == "hold"
        assert await _events_for(session, fact_id) == []

    async def test_a_corroborated_hold_still_meeting_n_journals_nothing_further(
        self, session
    ):
        fact_id = await _make_fact(session, key="stable-hold-1")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        await recompute_fact(session, fact_id)
        await session.commit()
        assert len(await _events_for(session, fact_id)) == 1

        decision = await recompute_fact(session, fact_id)
        await session.commit()

        assert decision.outcome == "hold"
        assert len(await _events_for(session, fact_id)) == 1

    async def test_a_confirmed_hold_journals_nothing(self, session):
        fact_id = await _make_fact(session, key="confirmed-hold-1")
        await session.execute(
            text(
                "UPDATE knowledge_triples SET verification_status = 'confirmed' "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": fact_id},
        )
        await session.commit()
        await _add_origin(session, fact_id, "human-1", kind="human")

        decision = await recompute_fact(session, fact_id)
        await session.commit()

        assert (decision.target_status, decision.outcome) == ("confirmed", "hold")
        assert await _events_for(session, fact_id) == []


# ─────────────── D2 — the G-C metrics, derivable by SQL over events alone ───────────────

_PROMOTION_RATE_SQL = """
    SELECT
        payload->>'gate_fired' AS gate_fired,
        COUNT(*) FILTER (WHERE payload->>'outcome' = 'promote') AS promoted,
        COUNT(*) AS eligible
    FROM events
    WHERE event_type = 'verified'
      AND object_type = 'fact'
      AND object_id = ANY(CAST(:fact_ids AS uuid[]))
      AND payload->'before'->>'verification_status' = 'candidate'
      AND payload->>'outcome' IN ('promote', 'dispute')
      AND (payload->>'origin_count')::int >= (payload->>'required_n')::int
    GROUP BY payload->>'gate_fired'
    ORDER BY gate_fired
"""

_FALSE_PROMOTION_AUDIT_SQL = """
    SELECT
        (
            -- Doc 17 §5.1's anchor is "corroborated facts," not "facts that
            -- emitted a `promote` event": a fact can reach `corroborated`
            -- through `recover` (candidate -> disputed on an early veto,
            -- then an affirmative clean verdict lands it on `corroborated`
            -- directly) without ever emitting `promote`. Anchoring on
            -- `after.verification_status = 'corroborated'` catches both
            -- outcomes; anchoring on `outcome = 'promote'` alone silently
            -- drops every fact that reached the status via `recover`.
            SELECT COUNT(DISTINCT object_id) FROM events
            WHERE event_type = 'verified'
              AND object_id = ANY(CAST(:fact_ids AS uuid[]))
              AND payload->'after'->>'verification_status' = 'corroborated'
        ) AS total_corroborations,
        (
            SELECT COUNT(DISTINCT p.object_id)
            FROM events p
            JOIN events d
              ON d.object_id = p.object_id
             AND d.event_type = 'verified'
             AND d.payload->>'outcome' = 'dispute'
             -- `id` (a monotonic BIGINT IDENTITY) tie-breaks `created_at`,
             -- matching the ordering convention `object_timeline`/`list_events`
             -- already use in app/services/events.py: same-transaction writes
             -- (a batch recompute, or this very test's non-committing session
             -- fixture) can share one transaction-constant `now()`, so
             -- `created_at` alone cannot always order two rows. `id` order is
             -- in fact the stronger key here: the insert happens while the
             -- applier still holds the fact row's FOR UPDATE lock, so `id`
             -- order is exactly the per-fact serialization order, whereas
             -- `created_at`-first can in principle invert it when a
             -- later-serialized transaction's clock read started earlier.
             AND (d.created_at, d.id) > (p.created_at, p.id)
            WHERE p.event_type = 'verified'
              AND p.object_id = ANY(CAST(:fact_ids AS uuid[]))
              AND p.payload->'after'->>'verification_status' = 'corroborated'
        ) AS falsely_promoted
"""
# Units, pinned for T2.51: both sides of the ratio count DISTINCT facts
# (object_id), not events. A fact that cycles corroborated -> disputed ->
# recovered -> corroborated -> disputed again would otherwise inflate a
# per-event count relative to doc 17's "facts" wording; counting facts on
# both sides keeps the ratio's unit consistent and matches the metric's own
# phrasing ("count of corroborated facts...").
#
# The "or human-rejected" half of doc 17 §5.1's definition is not
# represented here at all: it depends on `review_state` verdicts, which are
# T2.62's write and do not exist yet. This SQL is therefore the
# machine-observable half only (facts disputed by the veto after reaching
# `corroborated`); it is vacuously complete today only because no rejection
# path exists to be missed. When T2.62 lands, its verdicts must themselves
# journal to `events` (the same "events alone" property this task built for
# the veto side) or this query's silence on human rejection becomes a real
# gap rather than a documented one -- T2.51 must not copy this query without
# also adding that arm once it exists.


class TestGCMetricsFromEventsAlone:
    """Work backwards from doc 17 §5.1's two metrics to the seeded transitions
    that must produce them, then prove the SQL against ``events`` alone
    returns exactly those numbers -- no read of ``knowledge_triples``.

    Promotion rate: ``(facts promoted) / (eligible candidate facts)``, sliced
    by which N fired. "Eligible" means the fact actually reached its
    corroboration bar this cycle (``origin_count >= required_n``) -- which,
    by ``decide()``'s own branch structure **as it exists today**, is exactly
    the set of facts that transitioned out of ``candidate`` (to
    ``corroborated`` via ``promote``, or to ``disputed`` via a veto that
    fired *after* the bar was met). A candidate that merely holds below its
    bar was correctly never journaled (previous class): it was never
    eligible, so excluding it needs no extra row, only the filter above. A
    candidate vetoed *before* reaching its bar (an early dispute) is
    journaled but excluded by the same filter, because it was never eligible
    either. This is the finding the brief asked for: the metric does not
    need every hold journaled, only every transition, because "eligible" and
    "journaled transition with origin_count >= required_n" are the same set
    by construction.

    **This equivalence is not permanent, and its expiry date is named.** It
    holds only because no code path today returns a hold for a candidate
    that met its bar. Doc 08 §4's planned supersession blocker (T2.60) is
    defined as exactly that shape -- a deterministic hold on an
    otherwise-eligible candidate -- and the ruling for how T2.60 must
    preserve this equivalence (journal its own blocked hold, the same way
    ``contradiction_blocked`` does here) lives in
    ``app.services.verification_ladder.decide``'s own docstring, not only in
    this comment. T2.46's demote-side hysteresis is the same genus of hazard
    on the other axis (a grace-cycle deferral leaves status unchanged and
    journals nothing today, while doc 17 wants demotion thrash measured from
    this journal too) -- that one lands with T2.46's own applier change and
    is out of this task's scope, noted here only so it is not lost.

    False-promotion audit: the count of *facts* that reached ``corroborated``
    (via ``promote`` or ``recover`` -- see the SQL's own comment) and were
    later disputed. A self-join on ``events`` by ``object_id``, tie-broken by
    ``id`` -- no reconstruction of current state required.
    """

    async def test_promotion_rate_sliced_by_which_n_fired(self, session):
        # Slice "diversity": A promotes, D is vetoed after meeting its bar.
        a = await _make_fact(session, key="gc-a-diversity-promote")
        await _add_origin(session, a, "sess-a", kind="memory")
        await _add_origin(session, a, "repo-a", kind="code")
        decision_a = await recompute_fact(session, a)
        await session.commit()
        assert decision_a.outcome == "promote"

        d = await _make_fact(session, key="gc-d-diversity-vetoed")
        await _add_origin(session, d, "sess-d", kind="memory")
        await _add_origin(session, d, "repo-d", kind="code")
        decision_d = await recompute_fact(session, d, open_contradiction=True)
        await session.commit()
        assert decision_d.outcome == "dispute"
        assert decision_d.origin_count >= decision_d.required_n, (
            "D must have met its bar for the vetoed-but-eligible case to mean anything"
        )

        # Slice "none": C promotes at 3 same-kind same-day origins.
        c = await _make_fact(session, key="gc-c-none-promote")
        for name in ("sess-c1", "sess-c2", "sess-c3"):
            await _add_origin(session, c, name, kind="memory")
        decision_c = await recompute_fact(session, c)
        await session.commit()
        assert decision_c.outcome == "promote"

        # Not eligible: B holds below N (no journal at all).
        b = await _make_fact(session, key="gc-b-below-bar")
        await _add_origin(session, b, "sess-b1", kind="memory")
        await _add_origin(session, b, "sess-b2", kind="memory")
        decision_b = await recompute_fact(session, b)
        await session.commit()
        assert decision_b.outcome == "hold"

        # Not eligible: E is vetoed before ever meeting its bar (one origin).
        e = await _make_fact(session, key="gc-e-early-veto")
        await _add_origin(session, e, "sess-e1", kind="memory")
        decision_e = await recompute_fact(session, e, open_contradiction=True)
        await session.commit()
        assert decision_e.outcome == "dispute"
        assert decision_e.origin_count < decision_e.required_n

        fact_ids = [a, b, c, d, e]
        rows = (
            await session.execute(
                text(_PROMOTION_RATE_SQL), {"fact_ids": fact_ids}
            )
        ).mappings().all()
        by_gate = {row["gate_fired"]: (row["promoted"], row["eligible"]) for row in rows}

        assert by_gate == {
            "diversity": (1, 2),  # A promoted, D eligible-but-vetoed
            "none": (1, 1),  # C promoted; B and E excluded (never eligible)
        }
        assert by_gate["diversity"][0] / by_gate["diversity"][1] == pytest.approx(0.5)
        assert by_gate["none"][0] / by_gate["none"][1] == pytest.approx(1.0)

    async def test_false_promotion_audit_counts_promoted_then_later_disputed(
        self, session
    ):
        # A promotes, then is later disputed -- a false promotion reached via
        # the `promote` outcome.
        a = await _make_fact(session, key="gc-audit-a-false-promotion")
        await _add_origin(session, a, "sess-a", kind="memory")
        await _add_origin(session, a, "repo-a", kind="code")
        await recompute_fact(session, a)
        await session.commit()
        second = await recompute_fact(session, a, open_contradiction=True)
        await session.commit()
        assert second.outcome == "dispute"

        # C promotes and stays corroborated -- a true (uncontested) promotion.
        c = await _make_fact(session, key="gc-audit-c-clean-promotion")
        for name in ("sess-c1", "sess-c2", "sess-c3"):
            await _add_origin(session, c, name, kind="memory")
        await recompute_fact(session, c)
        await session.commit()

        # G reaches `corroborated` via `recover`, never via `promote`: an
        # early veto (before G ever meets its bar) disputes it, a second
        # origin then brings it to the bar, and an affirmative clean verdict
        # recovers it straight to `corroborated` -- no `promote` event is
        # ever emitted. It is then disputed again later. An audit anchored
        # on `outcome = 'promote'` alone would miss this fact entirely.
        g = await _make_fact(session, key="gc-audit-g-recovered-then-disputed")
        await _add_origin(session, g, "sess-g1", kind="memory")
        first = await recompute_fact(session, g, open_contradiction=True)
        await session.commit()
        assert first.outcome == "dispute"
        assert first.origin_count < first.required_n, (
            "G must be vetoed before ever meeting its bar, so no promote "
            "event exists for it to anchor on"
        )
        await _add_origin(session, g, "repo-g1", kind="code")
        recovered = await recompute_fact(session, g, open_contradiction=False)
        await session.commit()
        assert recovered.outcome == "recover"
        assert recovered.target_status == "corroborated"
        redisputed = await recompute_fact(session, g, open_contradiction=True)
        await session.commit()
        assert redisputed.outcome == "dispute"

        fact_ids = [a, c, g]
        row = (
            await session.execute(
                text(_FALSE_PROMOTION_AUDIT_SQL), {"fact_ids": fact_ids}
            )
        ).mappings().one()

        assert row["total_corroborations"] == 3, "A, C and G all reached corroborated"
        assert row["falsely_promoted"] == 2, "A (via promote) and G (via recover)"
        rate = row["falsely_promoted"] / row["total_corroborations"]
        assert rate == pytest.approx(2 / 3)

    async def test_the_audit_sql_never_touches_knowledge_triples(self):
        """A structural guard on the deliverable itself: the SQL text this
        suite runs must not reference the source table, or the "no join back"
        promise is a comment, not a property.
        """
        for sql in (_PROMOTION_RATE_SQL, _FALSE_PROMOTION_AUDIT_SQL):
            assert "knowledge_triples" not in sql
            assert "from events" in sql.lower()

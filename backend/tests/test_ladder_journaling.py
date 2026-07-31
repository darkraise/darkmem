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
            SELECT COUNT(*) FROM events
            WHERE event_type = 'verified'
              AND object_id = ANY(CAST(:fact_ids AS uuid[]))
              AND payload->>'outcome' = 'promote'
        ) AS total_promotions,
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
             -- (a batch recompute, or this very test) can share one `now()`,
             -- so `created_at` alone cannot always order two rows.
             AND (d.created_at, d.id) > (p.created_at, p.id)
            WHERE p.event_type = 'verified'
              AND p.object_id = ANY(CAST(:fact_ids AS uuid[]))
              AND p.payload->>'outcome' = 'promote'
        ) AS falsely_promoted
"""


class TestGCMetricsFromEventsAlone:
    """Work backwards from doc 17 §5.1's two metrics to the seeded transitions
    that must produce them, then prove the SQL against ``events`` alone
    returns exactly those numbers -- no read of ``knowledge_triples``.

    Promotion rate: ``(facts promoted) / (eligible candidate facts)``, sliced
    by which N fired. "Eligible" means the fact actually reached its
    corroboration bar this cycle (``origin_count >= required_n``) -- which,
    by ``decide()``'s own branch structure, is exactly the set of facts that
    transitioned out of ``candidate`` (to ``corroborated`` via ``promote``, or
    to ``disputed`` via a veto that fired *after* the bar was met). A
    candidate that merely holds below its bar was correctly never journaled
    (previous class): it was never eligible, so excluding it needs no extra
    row, only the filter above. A candidate vetoed *before* reaching its bar
    (an early dispute) is journaled but excluded by the same filter, because
    it was never eligible either. This is the finding the brief asked for:
    the metric does not need every hold journaled, only every transition,
    because "eligible" and "journaled transition with origin_count >=
    required_n" are the same set by construction.

    False-promotion audit: the count of facts that promoted and were later
    disputed. A self-join on ``events`` by ``object_id``, ordered by
    ``created_at`` -- no reconstruction of current state required.
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
        # A promotes, then is later disputed -- a false promotion.
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

        fact_ids = [a, c]
        row = (
            await session.execute(
                text(_FALSE_PROMOTION_AUDIT_SQL), {"fact_ids": fact_ids}
            )
        ).mappings().one()

        assert row["total_promotions"] == 2
        assert row["falsely_promoted"] == 1
        rate = row["falsely_promoted"] / row["total_promotions"]
        assert rate == pytest.approx(0.5)

    async def test_the_audit_sql_never_touches_knowledge_triples(self):
        """A structural guard on the deliverable itself: the SQL text this
        suite runs must not reference the source table, or the "no join back"
        promise is a comment, not a property.
        """
        for sql in (_PROMOTION_RATE_SQL, _FALSE_PROMOTION_AUDIT_SQL):
            assert "knowledge_triples" not in sql
            assert sql.strip().upper().count("FROM EVENTS") >= 1 or "from events" in sql.lower()

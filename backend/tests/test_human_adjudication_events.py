"""T2.63 — a human adjudication verdict must reach the journal.

Doc 17 §5.1's false-promotion audit is "the count of corroborated facts later
disputed **or human-rejected**". The disputed half is a self-join over
``verified`` events (pinned in ``test_ladder_journaling.py``). This suite pins
the other half: the ``human_verdict`` event, its closed verdict set, the SQL
that counts it, and the three properties that must survive the change —
``review_state`` gains no value, T2.62's refusal still raises, and the
``verified`` population is untouched.

**The SQL below is pinned for T2.51 the same way T2.06 pinned its own** (see
``test_ladder_journaling.py``'s ``_FALSE_PROMOTION_AUDIT_SQL``, which T2.51's
runner adopted verbatim). ``promotion_metrics.py`` is not on this branch —
T2.51 is committed on an unmerged sibling lane — so this file is where the
arm's query and its vocabulary guard are proved. See the T2.51 note beside
``_HUMAN_REJECTED_AUDIT_SQL``.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.repositories.knowledge_triples import (
    REVIEW_STATE_OPEN,
    KnowledgeTripleRepository,
)
from app.services import human_adjudication
from app.services.events import EVENT_TYPES, OBJECT_TYPES, record_event
from app.services.human_adjudication import (
    HUMAN_VERDICT_EVENT_TYPE,
    HUMAN_VERDICTS,
    record_human_verdict,
    reject_fact,
)

pytestmark = pytest.mark.asyncio

T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
PROJECT = "t2-63-human-verdicts"

# `events.created_at` defaults to `now()`, which is the *transaction* start
# time, so a Python clock read taken anywhere in a test can land on either
# side of it. Every audit call below therefore spans the whole journal and
# lets the tuple compare do the ordering work; one test bounds the window on
# purpose to prove the predicate is live.
EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)
FAR_FUTURE = datetime(2100, 1, 1, tzinfo=timezone.utc)


# ─────────────────────────── the arm T2.51 must adopt ───────────────────────────

# The human-rejected half of doc 17 §5.1's audit, mirroring the disputed
# half's shape exactly: a self-join on `events` by `object_id`, tie-broken by
# `id` because `now()` is constant within one transaction, counting DISTINCT
# facts on both sides. Reads `events` alone — no join back to
# `knowledge_triples`, whose current row may by then be expired, edited, or
# gone, none of which changes the fact that a human rejected it.
#
# **T2.51's `_human_rejected_count` must become this query.** Its present body
# reads `knowledge_triples.review_state` and is structurally 0 forever under
# T2.62's design; its `KNOWN_REVIEW_STATES` tripwire guards a vocabulary that
# is correct and so can never fire. The replacement guard is
# `_HUMAN_VERDICT_VOCABULARY_SQL` below, which fires on a verdict outside
# `HUMAN_VERDICTS` — the read-side backstop against a writer that bypassed
# `record_human_verdict`, exactly the role `KNOWN_REVIEW_STATES` was meant to play.
_HUMAN_REJECTED_AUDIT_SQL = text("""
    SELECT COUNT(DISTINCT p.object_id) AS human_rejected
    FROM events p
    JOIN events h
      ON h.object_id = p.object_id
     AND h.event_type = 'human_verdict'
     AND h.object_type = 'fact'
     AND h.payload->>'verdict' = 'rejected'
     AND (h.created_at, h.id) > (p.created_at, p.id)
    WHERE p.event_type = 'verified'
      AND p.object_type = 'fact'
      AND p.created_at >= :since AND p.created_at <= :until
      AND p.payload->'after'->>'verification_status' = 'corroborated'
""")

_HUMAN_VERDICT_VOCABULARY_SQL = text("""
    SELECT DISTINCT payload->>'verdict' AS verdict
    FROM events
    WHERE event_type = 'human_verdict'
      AND object_type = 'fact'
      AND created_at >= :since
""")


class UnrecognisedVerdictError(RuntimeError):
    """The read-side tripwire's error. T2.51 raises its own
    ``UnrecognisedPayloadError`` here; the shape is what matters."""


async def _human_rejected_count(session, *, since, until) -> int:
    """The arm, whole: guard the vocabulary, then count."""
    verdicts = [
        row[0]
        for row in (await session.execute(_HUMAN_VERDICT_VOCABULARY_SQL, {"since": since})).all()
    ]
    unknown = sorted(v for v in verdicts if v not in HUMAN_VERDICTS)
    if unknown:
        raise UnrecognisedVerdictError(
            f"human_verdict events carry unrecognised verdict(s) {unknown}; "
            f"known verdicts are {sorted(HUMAN_VERDICTS)}"
        )
    return int(
        (await session.execute(_HUMAN_REJECTED_AUDIT_SQL, {"since": since, "until": until}))
        .scalar_one()
    )


# ─────────────────────────────── fixtures ───────────────────────────────


async def _fact(session, *, subject: str, obj: str, status: str | None = None,
                review_state: str | None = None, project: str = PROJECT) -> str:
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=f"k-{uuid4()}",
        subject_name=subject,
        object_name=obj,
        rel_type="RELATED_TO",
        fact=f"{subject} RELATED_TO {obj}",
        reference_time=T0,
        project=project,
        review_state=review_state,
    )
    if status is not None:
        await repo.set_verification_status(row["id"], status)
    await session.flush()
    return row["id"]


async def _corroborate(session, fact_id: str) -> None:
    """A journalled candidate -> corroborated promotion: the audit's left side."""
    await KnowledgeTripleRepository(session).set_verification_status(
        fact_id,
        "corroborated",
        confidence=0.9,
        outcome="promote",
        origin_count=2,
        required_n=2,
        gate_fired="diversity",
        source_kinds=("memory", "document"),
    )
    await session.flush()


async def _events(session, fact_id: str, event_type: str) -> list[dict]:
    rows = await session.execute(
        text(
            "SELECT event_type, object_type, project, actor, payload FROM events "
            "WHERE object_id = CAST(:id AS uuid) AND event_type = CAST(:t AS text) "
            "ORDER BY created_at, id"
        ),
        {"id": fact_id, "t": event_type},
    )
    return [dict(row) for row in rows.mappings().all()]


async def _count_verified(session) -> int:
    return int(
        (await session.execute(
            text("SELECT COUNT(*) FROM events WHERE event_type = 'verified'")
        )).scalar_one()
    )


async def _column(session, fact_id: str, column: str):
    return (await session.execute(
        text(f"SELECT {column} FROM knowledge_triples WHERE id = CAST(:id AS uuid)"),
        {"id": fact_id},
    )).scalar_one()


# ───────────────────── clause 1: the vocabulary, landed first ─────────────────────


async def test_human_verdict_is_in_the_closed_event_vocabulary():
    """Taxonomy-first, made assertable.

    ``record_event`` degrades loudly but never raises, so removing this value
    breaks nothing the emitter does — see the next test for what it actually
    does instead. This assertion is the only thing that fails, which is
    precisely why it has to exist.
    """
    assert HUMAN_VERDICT_EVENT_TYPE == "human_verdict"
    assert HUMAN_VERDICT_EVENT_TYPE in EVENT_TYPES
    assert "fact" in OBJECT_TYPES


async def test_an_off_vocabulary_event_type_warns_and_still_lands(session, caplog):
    """What ``record_event`` actually does with an unlanded value — and it is
    not what the taxonomy-first rule is usually paraphrased as.

    The vocabulary check **warns and inserts anyway**; it neither raises nor
    drops the row. So shipping an emitter ahead of its value fails silently in
    a subtler way than a lost row: the row lands under a value no reader's
    vocabulary lists, so every consumer that enumerates ``EVENT_TYPES`` —
    a metrics runner's guard, a filter UI, a reviewer — is reasoning about a
    journal that contains something they have no name for. Landing the value
    first is what keeps the closed vocabulary an actual description of the
    table's contents.
    """
    fact_id = await _fact(session, subject="off", obj="vocabulary")
    before = (await session.execute(text("SELECT COUNT(*) FROM events"))).scalar_one()
    with caplog.at_level(logging.WARNING, logger="app.services.events"):
        await record_event(
            session,
            event_type="human_verdict_not_yet_landed",
            object_type="fact",
            object_id=uuid.UUID(fact_id),
            project=PROJECT,
            payload={"verdict": "rejected"},
        )
    await session.flush()
    after = (await session.execute(text("SELECT COUNT(*) FROM events"))).scalar_one()
    assert after == before + 1
    assert any("outside the doc 04 §8.1 closed vocabulary" in record.getMessage()
               for record in caplog.records)
    assert await _human_rejected_count(session, since=EPOCH, until=FAR_FUTURE) == 0, (
        "and the audit, which filters on the landed type, cannot see it"
    )


# ───────────────────── clause 2: the payload the audit needs ─────────────────────


async def test_verdict_payload_answers_the_audit_without_touching_the_fact_table(session):
    fact_id = await _fact(session, subject="pg", obj="14", status="disputed",
                          review_state=REVIEW_STATE_OPEN)
    await session.flush()

    await record_human_verdict(
        session,
        fact_id=fact_id,
        verdict="rejected",
        verification_status="disputed",
        review_state=REVIEW_STATE_OPEN,
        project=PROJECT,
        actor="admin",
        note="the benchmark it cites was withdrawn",
    )
    await session.flush()

    rows = await _events(session, fact_id, "human_verdict")
    assert len(rows) == 1
    row = rows[0]
    assert row["object_type"] == "fact"
    assert row["project"] == PROJECT
    assert row["actor"] == "admin"
    assert row["payload"] == {
        "verdict": "rejected",
        "verification_status": "disputed",
        "review_state": REVIEW_STATE_OPEN,
        "note": "the benchmark it cites was withdrawn",
    }


async def test_the_payload_records_the_status_held_not_the_status_left_behind(session):
    """The audit asks what the fact was when the human rejected it. Reading
    ``knowledge_triples`` later answers a different question — which is the
    reason the payload has to carry it."""
    fact_id = await _fact(session, subject="redis", obj="cache")
    await _corroborate(session, fact_id)

    await reject_fact(session, fact_id, actor="admin")
    await session.flush()

    payload = (await _events(session, fact_id, "human_verdict"))[0]["payload"]
    assert payload["verification_status"] == "corroborated"
    assert payload["verdict"] == "rejected"
    assert payload["review_state"] is None


async def test_note_is_truncated_to_the_journal_bound(session):
    fact_id = await _fact(session, subject="long", obj="note")
    await record_human_verdict(
        session,
        fact_id=fact_id,
        verdict="edited",
        verification_status="candidate",
        review_state=None,
        project=PROJECT,
        actor="admin",
        note="x" * (human_adjudication.NOTE_MAX_LENGTH + 50),
    )
    await session.flush()
    payload = (await _events(session, fact_id, "human_verdict"))[0]["payload"]
    assert len(payload["note"]) == human_adjudication.NOTE_MAX_LENGTH


async def test_an_unknown_verdict_is_refused_at_the_write_side(session):
    """The write-side tripwire, and it is stronger than ``EVENT_TYPES`` gives:
    ``record_event`` would warn and drop, this raises before the row exists."""
    fact_id = await _fact(session, subject="bad", obj="verdict")
    with pytest.raises(ValueError, match="unknown human verdict"):
        await record_human_verdict(
            session,
            fact_id=fact_id,
            verdict="dismissed",
            verification_status="candidate",
            review_state=None,
            project=PROJECT,
            actor="admin",
        )
    await session.flush()
    assert await _events(session, fact_id, "human_verdict") == []


async def test_the_verdict_set_is_doc_08_section_6s_verbs_plus_rejection():
    assert HUMAN_VERDICTS == {"ratified", "regrounded", "edited", "rejected"}


# ───────── clause 3: T2.62's review_state ruling is untouched ─────────


async def test_a_verdict_writes_no_review_state(session):
    fact_id = await _fact(session, subject="queued", obj="fact", status="disputed",
                          review_state=REVIEW_STATE_OPEN)
    await session.flush()

    await reject_fact(session, fact_id, actor="admin")
    await session.flush()

    assert await _column(session, fact_id, "review_state") == REVIEW_STATE_OPEN, (
        "a verdict records the queue membership it saw; it never writes it. "
        "Whether the fact leaves the queue is a consequence of the conditions "
        "changing (T2.62), not of this write"
    )


async def test_t2_62s_review_state_refusal_still_raises(session):
    """No new ``review_state`` value exists, and the repository still refuses one."""
    fact_id = await _fact(session, subject="refusal", obj="stands")
    repo = KnowledgeTripleRepository(session)
    for literal in ("rejected", "human_rejected", "resolved"):
        with pytest.raises(ValueError, match="invalid review_state"):
            await repo.set_verification_status(fact_id, "disputed", review_state=literal)


async def test_confirmed_is_still_refused_by_the_machine_path(session):
    """T2.05's boundary: this task did not relax the ratification refusal."""
    fact_id = await _fact(session, subject="confirm", obj="refused")
    with pytest.raises(ValueError, match="cannot write 'confirmed'"):
        await KnowledgeTripleRepository(session).set_verification_status(fact_id, "confirmed")


# ───────── clause 5: not a second writer of `verified` ─────────


async def test_a_rejection_adds_no_verified_event(session):
    fact_id = await _fact(session, subject="sole", obj="journaller")
    await _corroborate(session, fact_id)
    before = await _count_verified(session)

    await reject_fact(session, fact_id, actor="admin")
    await session.flush()

    assert await _count_verified(session) == before
    assert len(await _events(session, fact_id, "human_verdict")) == 1


async def test_a_rejection_leaves_verification_status_alone(session):
    fact_id = await _fact(session, subject="axis", obj="separation")
    await _corroborate(session, fact_id)

    await reject_fact(session, fact_id, actor="admin")
    await session.flush()

    assert await _column(session, fact_id, "verification_status") == "corroborated"


async def test_the_verified_population_is_unchanged_across_representative_transitions(session):
    """Seed a promote, a dispute and a recover, reject after each, and prove
    the ``verified`` count moved only for the transitions themselves."""
    repo = KnowledgeTripleRepository(session)
    fact_id = await _fact(session, subject="cycle", obj="fact")

    baseline = await _count_verified(session)
    await _corroborate(session, fact_id)
    await repo.set_verification_status(fact_id, "disputed", confidence=0.4, outcome="dispute",
                                       origin_count=2, required_n=2, gate_fired="diversity",
                                       source_kinds=("memory",), contradiction_blocked=True)
    await repo.set_verification_status(fact_id, "corroborated", confidence=0.8, outcome="recover",
                                       origin_count=2, required_n=2, gate_fired="diversity",
                                       source_kinds=("memory",))
    await session.flush()
    after_transitions = await _count_verified(session)
    assert after_transitions == baseline + 3

    await reject_fact(session, fact_id, actor="admin")
    await session.flush()
    assert await _count_verified(session) == after_transitions


# ───────── clause 4: the audit arm, and a tripwire that can fire ─────────


async def test_a_seeded_rejection_makes_the_audit_arm_non_zero(session):
    rejected = await _fact(session, subject="wrongly", obj="promoted")
    untouched = await _fact(session, subject="rightly", obj="promoted")
    await _corroborate(session, rejected)
    await _corroborate(session, untouched)
    await session.flush()

    assert await _human_rejected_count(session, since=EPOCH, until=FAR_FUTURE) == 0

    await reject_fact(session, rejected, actor="admin")
    await session.flush()

    assert await _human_rejected_count(session, since=EPOCH, until=FAR_FUTURE) == 1


async def test_the_audit_counts_distinct_facts_not_verdicts(session):
    fact_id = await _fact(session, subject="twice", obj="rejected")
    await _corroborate(session, fact_id)
    await reject_fact(session, fact_id, actor="admin")
    await reject_fact(session, fact_id, actor="someone-else")
    await session.flush()

    assert len(await _events(session, fact_id, "human_verdict")) == 2
    assert await _human_rejected_count(session, since=EPOCH, until=FAR_FUTURE) == 1


async def test_a_rejection_before_corroboration_is_not_a_false_promotion(session):
    """The audit's ordering half: only a rejection *after* the corroboration
    it indicts counts, same tuple-compare the disputed half uses."""
    fact_id = await _fact(session, subject="order", obj="matters")
    await reject_fact(session, fact_id, actor="admin")
    await session.flush()
    await _corroborate(session, fact_id)
    await session.flush()

    assert await _human_rejected_count(session, since=EPOCH, until=FAR_FUTURE) == 0


async def test_a_non_rejection_verdict_is_not_a_false_promotion(session):
    fact_id = await _fact(session, subject="edited", obj="not-rejected")
    await _corroborate(session, fact_id)
    await record_human_verdict(
        session,
        fact_id=fact_id,
        verdict="edited",
        verification_status="corroborated",
        review_state=None,
        project=PROJECT,
        actor="admin",
    )
    await session.flush()

    assert await _human_rejected_count(session, since=EPOCH, until=FAR_FUTURE) == 0


async def test_the_audit_window_bounds_the_corroboration_side(session):
    """The ``since``/``until`` predicate is live, not decorative: a window that
    excludes the corroboration excludes the fact, even though the rejection
    itself is deliberately unbounded above (a false promotion found after the
    window closed is still a false promotion)."""
    fact_id = await _fact(session, subject="window", obj="bounds")
    await _corroborate(session, fact_id)
    await reject_fact(session, fact_id, actor="admin")
    await session.flush()

    assert await _human_rejected_count(session, since=EPOCH, until=FAR_FUTURE) == 1
    assert await _human_rejected_count(session, since=FAR_FUTURE, until=FAR_FUTURE) == 0


async def test_the_read_side_tripwire_fires_on_a_verdict_outside_the_set(session):
    """A writer that bypassed ``record_human_verdict`` — the failure the arm's
    guard exists for. Raw INSERT, because the emitter refuses to produce it."""
    fact_id = await _fact(session, subject="bypass", obj="the-emitter")
    await _corroborate(session, fact_id)
    await session.execute(
        text(
            "INSERT INTO events (event_type, object_type, object_id, project, payload) "
            "VALUES ('human_verdict', 'fact', CAST(:id AS uuid), CAST(:p AS text), "
            "CAST(:payload AS jsonb))"
        ),
        {"id": fact_id, "p": PROJECT, "payload": '{"verdict": "vetoed"}'},
    )
    await session.flush()

    with pytest.raises(UnrecognisedVerdictError, match="vetoed"):
        await _human_rejected_count(session, since=EPOCH, until=FAR_FUTURE)


# ───────── the condition-side change, and the door ─────────


async def test_rejection_withdraws_belief_and_journals_expired(session):
    """Rejection's condition-side expression. Without one it would be the bare
    dismiss doc 08 §6 does not give the human (T2.62)."""
    fact_id = await _fact(session, subject="belief", obj="withdrawn")
    await session.flush()
    assert await _column(session, fact_id, "expired_at") is None

    await reject_fact(session, fact_id, actor="admin")
    await session.flush()

    assert await _column(session, fact_id, "expired_at") is not None
    assert len(await _events(session, fact_id, "expired")) == 1
    live = await KnowledgeTripleRepository(session).get_live(project=PROJECT)
    assert fact_id not in [row["id"] for row in live]


async def test_rejecting_an_unknown_fact_raises_rather_than_journalling(session):
    missing = str(uuid4())
    with pytest.raises(human_adjudication.FactNotFound):
        await reject_fact(session, missing, actor="admin")
    await session.flush()
    assert await _events(session, missing, "human_verdict") == []


async def test_reject_route_requires_auth(client):
    response = await client.post(f"/api/v1/review-queue/facts/{uuid4()}/reject")
    assert response.status_code == 401


async def test_reject_route_404s_on_an_unknown_fact(client, auth_headers):
    response = await client.post(
        f"/api/v1/review-queue/facts/{uuid4()}/reject", headers=auth_headers,
    )
    assert response.status_code == 404


async def test_reject_route_journals_the_verdict_with_the_caller_as_actor(
    client, auth_headers, session,
):
    fact_id = await _fact(session, subject="door", obj="works", status="disputed",
                          review_state=REVIEW_STATE_OPEN)
    await session.commit()

    response = await client.post(
        f"/api/v1/review-queue/facts/{fact_id}/reject",
        headers=auth_headers,
        json={"note": "superseded by the vendor's own retraction"},
    )
    assert response.status_code == 204

    rows = await _events(session, fact_id, "human_verdict")
    assert len(rows) == 1
    assert rows[0]["payload"]["verdict"] == "rejected"
    assert rows[0]["payload"]["verification_status"] == "disputed"
    assert rows[0]["actor"]
    assert await _column(session, fact_id, "expired_at") is not None


async def test_reject_route_rejects_an_over_long_note(client, auth_headers, session):
    fact_id = await _fact(session, subject="note", obj="bound")
    await session.commit()
    response = await client.post(
        f"/api/v1/review-queue/facts/{fact_id}/reject",
        headers=auth_headers,
        json={"note": "x" * (human_adjudication.NOTE_MAX_LENGTH + 1)},
    )
    assert response.status_code == 422


async def test_a_rejected_fact_is_not_dropped_from_the_queue_by_this_write(
    client, auth_headers, session,
):
    """Stated, not engineered. T2.62 makes queue membership a consequence of
    the conditions the derivation reads, so the door does not clear the flag
    and the fact stays listed until a recompute re-derives it."""
    from app.services import review_queue as review_queue_service

    fact_id = await _fact(session, subject="stays", obj="queued", status="disputed",
                          review_state=REVIEW_STATE_OPEN)
    await session.commit()

    response = await client.post(
        f"/api/v1/review-queue/facts/{fact_id}/reject", headers=auth_headers,
    )
    assert response.status_code == 204

    items, _total = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert fact_id in [item["id"] for item in items]

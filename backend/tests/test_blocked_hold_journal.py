"""Blocked holds journal on new evidence only; the suspicion marker and the
dismissal note stay inside their bounds."""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import text

from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.human_adjudication import (
    NOTE_MAX_LENGTH,
    dismiss_contradiction_suspicion,
)
from app.services.verification_ladder import recompute_fact
from tests.test_contradiction_scan import _fact, _record_verdict, _source


def _evidence(counterpart: str) -> dict:
    return {
        "counterpart_id": counterpart,
        "counterpart_subject": "darkmem",
        "counterpart_rel_type": "USES",
        "counterpart_object": f"store-{counterpart[:8]}",
        "rule": "inverse_replacement",
        "witness_origin": "sess-b",
        "enumeration": "first_finding",
    }


async def _verified_rows(session, fact_id) -> int:
    result = await session.execute(
        text(
            "SELECT count(*) FROM events WHERE object_type = 'fact' "
            "AND event_type = 'verified' AND object_id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )
    return result.scalar_one()


async def _contradiction_hold(session, fact_id, counterpart: str) -> None:
    await KnowledgeTripleRepository(session).set_verification_status(
        fact_id,
        None,
        confidence=0.4,
        outcome="hold",
        origin_count=1,
        required_n=3,
        gate_fired="none",
        source_kinds=("memory",),
        contradiction_blocked=True,
        contradiction=_evidence(counterpart),
    )
    await session.commit()


async def _supersession_hold(session, fact_id, origin_count: int) -> None:
    await KnowledgeTripleRepository(session).set_verification_status(
        fact_id,
        None,
        confidence=0.6,
        outcome="hold",
        origin_count=origin_count,
        required_n=3,
        gate_fired="none",
        source_kinds=("memory",),
        supersession_blocked=True,
    )
    await session.commit()


async def test_identical_blocked_hold_is_journalled_once(session):
    fact_id = await _fact(session, subject="darkmem", obj="postgres", status="disputed")
    seeded = await _verified_rows(session, fact_id)
    first, second = str(uuid4()), str(uuid4())

    for _ in range(3):
        await _contradiction_hold(session, fact_id, first)
    assert await _verified_rows(session, fact_id) == seeded + 1

    await _contradiction_hold(session, fact_id, second)
    assert await _verified_rows(session, fact_id) == seeded + 2


async def test_identical_supersession_blocked_hold_is_journalled_once(session):
    fact_id = await _fact(session, subject="darkmem", obj="faiss")
    seeded = await _verified_rows(session, fact_id)

    for _ in range(3):
        await _supersession_hold(session, fact_id, origin_count=3)
    assert await _verified_rows(session, fact_id) == seeded + 1

    await _supersession_hold(session, fact_id, origin_count=4)
    assert await _verified_rows(session, fact_id) == seeded + 2


async def test_confirmed_fact_gets_no_suspicion_marker(session):
    subject = await _fact(
        session, subject="darkmem", obj="postgres",
        fact="darkmem stores its vault in postgres",
    )
    await _source(session, subject, "sess-a")
    counter = await _fact(
        session, subject="darkmem", obj="mysql",
        fact="darkmem stores its vault in mysql",
    )
    await _source(session, counter, "sess-b")
    await _record_verdict(session, subject, counterpart=counter, witness="sess-b")
    await session.execute(
        text(
            "UPDATE knowledge_triples SET verification_status = 'confirmed' "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(subject)},
    )
    await session.commit()

    await recompute_fact(session, subject)
    await session.commit()

    row = (await session.execute(
        text(
            "SELECT contradiction_suspected_at, contradiction_counterpart_id "
            "FROM knowledge_triples WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(subject)},
    )).mappings().one()
    assert row["contradiction_suspected_at"] is None
    assert row["contradiction_counterpart_id"] is None


async def test_dismissal_note_is_bounded(session):
    subject = await _fact(
        session, subject="darkmem", obj="postgres",
        fact="darkmem stores its vault in postgres",
    )
    await _source(session, subject, "sess-a")
    counter = await _fact(
        session, subject="darkmem", obj="mysql",
        fact="darkmem stores its vault in mysql",
    )
    await _source(session, counter, "sess-b")
    await _record_verdict(session, subject, counterpart=counter, witness="sess-b")
    await recompute_fact(session, subject)
    await session.commit()

    assert await dismiss_contradiction_suspicion(
        session, subject, actor="admin", note="x" * 5000,
    )
    await session.commit()

    note = (await session.execute(
        text(
            "SELECT payload ->> 'note' FROM events "
            "WHERE event_type = 'contradiction_dismissed' "
            "AND object_id = CAST(:id AS uuid)"
        ),
        {"id": str(subject)},
    )).scalar_one()
    assert len(note) == NOTE_MAX_LENGTH

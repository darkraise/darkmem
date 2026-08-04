"""Human ratification: the only path to ``confirmed`` (doc 08 §4.4, T2.05).

Four claims, and each is asserted against the shape that would break it rather
than against the happy path alone:

1. The repository refuses ``confirmed`` to every machine caller, and its one
   permitting method refuses it too when no ``human`` source row asserts the
   fact — the refusal is in the UPDATE's predicate, so it holds against a
   caller that writes the row into a different transaction.
2. The ratification *is* a source row (who / when / what-was-shown), so a later
   withdrawal of every memory source leaves the confirmed fact standing.
3. The transition journals once, with an outcome the G-C metrics can bucket and
   deliberately do not count.
4. The door is authenticated REST and has no MCP twin.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.repositories.fact_sources import SOURCE_KINDS, FactSourceRepository
from app.repositories.knowledge_triples import (
    CONFIRMED,
    HUMAN_SOURCE_KIND,
    RATIFY_OUTCOME,
    HumanSourceRequired,
    KnowledgeTripleRepository,
)
from app.services import human_adjudication

PROJECT = "ratification"
REFERENCE = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
RATIFY = "/api/v1/knowledge/facts/{fact_id}/ratify"


async def _fact(session, *, subject: str = "darkmem", obj: str = "postgres") -> str:
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=f"ratify-{uuid.uuid4()}",
        subject_name=subject,
        object_name=obj,
        rel_type="USES",
        fact=f"{subject} uses {obj}",
        reference_time=REFERENCE,
        project=PROJECT,
    )
    await session.flush()
    return row["id"]


async def _memory_origin(session, fact_id: str, origin_key: str) -> None:
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind="memory",
        source_ref=f"memory:{origin_key}",
        origin_key=origin_key,
    )
    await session.flush()


async def _row(session, fact_id: str) -> dict:
    result = await session.execute(
        text(
            "SELECT verification_status, review_state, demotion_pending_since, "
            "demotion_pending_cycles FROM knowledge_triples "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )
    return dict(result.mappings().one())


async def _verified_events(session, fact_id: str) -> list[dict]:
    result = await session.execute(
        text(
            "SELECT payload FROM events WHERE object_id = CAST(:id AS uuid) "
            "AND event_type = 'verified' ORDER BY created_at, id"
        ),
        {"id": str(fact_id)},
    )
    return [row[0] for row in result.all()]


async def _human_verdicts(session, fact_id: str) -> list[dict]:
    result = await session.execute(
        text(
            "SELECT payload, actor FROM events WHERE object_id = CAST(:id AS uuid) "
            "AND event_type = 'human_verdict' ORDER BY created_at, id"
        ),
        {"id": str(fact_id)},
    )
    return [{"payload": row[0], "actor": row[1]} for row in result.all()]


# ───────────────────────────── the refusal ─────────────────────────────


def test_the_human_kind_is_the_one_fact_sources_knows():
    """The repository spells the kind for its UPDATE predicate; a rename in
    ``fact_sources`` that did not reach it would leave the predicate matching
    nothing, which fails *closed* — no fact could ever be confirmed — but would
    do it with a message about missing provenance rather than a typo."""
    assert HUMAN_SOURCE_KIND in SOURCE_KINDS


@pytest.mark.asyncio
async def test_set_verification_status_refuses_confirmed(session):
    fact_id = await _fact(session)
    with pytest.raises(ValueError, match="only a human may ratify"):
        await KnowledgeTripleRepository(session).set_verification_status(
            fact_id, CONFIRMED
        )


@pytest.mark.asyncio
async def test_ratify_refuses_a_fact_no_human_asserts(session):
    """The precondition is the UPDATE's own EXISTS, so a fact with plenty of
    machine provenance is still refused."""
    fact_id = await _fact(session)
    for index in range(5):
        await _memory_origin(session, fact_id, f"session-{index}")

    with pytest.raises(HumanSourceRequired):
        await KnowledgeTripleRepository(session).ratify(fact_id)

    assert (await _row(session, fact_id))["verification_status"] == "candidate"


@pytest.mark.asyncio
async def test_ratify_on_an_unknown_fact_is_none_not_a_refusal(session):
    """Absent and unprovenanced are different answers: one is a 404 at the
    door, the other a 409, and collapsing them would report a missing fact as
    a provenance problem the caller could try to fix."""
    assert await KnowledgeTripleRepository(session).ratify(uuid.uuid4()) is None


@pytest.mark.asyncio
async def test_the_service_requires_a_ratifier(session):
    fact_id = await _fact(session)
    with pytest.raises(ValueError, match="requires an actor"):
        await human_adjudication.ratify_fact(session, fact_id, actor="   ")


@pytest.mark.asyncio
async def test_an_unknown_fact_is_fact_not_found(session):
    with pytest.raises(human_adjudication.FactNotFound):
        await human_adjudication.ratify_fact(session, uuid.uuid4(), actor="admin")


# ───────────────────────── the ratification itself ─────────────────────────


@pytest.mark.asyncio
async def test_ratifying_writes_the_human_source_and_confirms(session):
    fact_id = await _fact(session)
    await _memory_origin(session, fact_id, "session-1")

    await human_adjudication.ratify_fact(
        session, fact_id, actor="admin", shown="asserted by 1 distinct origin"
    )
    await session.flush()

    assert (await _row(session, fact_id))["verification_status"] == CONFIRMED

    sources = (await session.execute(
        text(
            "SELECT source_kind, source_ref, origin_key, detail, created_at "
            "FROM fact_sources WHERE fact_id = CAST(:id AS uuid) "
            "AND source_kind = CAST(:kind AS text)"
        ),
        {"id": str(fact_id), "kind": HUMAN_SOURCE_KIND},
    )).mappings().all()
    assert len(sources) == 1
    human = sources[0]
    assert human["source_ref"] == "human:admin"
    assert human["origin_key"] == "human:admin"
    assert human["detail"]["ratified_by"] == "admin"
    assert human["detail"]["shown"] == "asserted by 1 distinct origin"
    # The "when" is the row's own timestamp, never a caller-supplied field.
    assert human["created_at"] is not None


@pytest.mark.asyncio
async def test_the_human_source_survives_every_memory_source_being_withdrawn(session):
    """Doc 08 §4.4's stated purpose for recording the ratification as a source:
    the source-emptying sweep must not be able to silently discard a fact a
    person vouched for."""
    fact_id = await _fact(session)
    await _memory_origin(session, fact_id, "session-1")
    await human_adjudication.ratify_fact(session, fact_id, actor="admin")
    await session.flush()

    await session.execute(
        text(
            "DELETE FROM fact_sources WHERE fact_id = CAST(:id AS uuid) "
            "AND source_kind = 'memory'"
        ),
        {"id": str(fact_id)},
    )
    await session.flush()

    remaining = await FactSourceRepository(session).count_distinct_origins(fact_id)
    assert remaining == 1
    assert (await _row(session, fact_id))["verification_status"] == CONFIRMED


@pytest.mark.asyncio
async def test_ratifying_clears_the_queue_and_the_pending_demotion(session):
    """Doc 08 §6 has the human's verbs clear ``review_state``; §4.4 makes a
    ratified fact immune to demotion. A caution overlay left on a fact a human
    just vouched for is the badge lying in the direction under-claiming does
    not cover."""
    fact_id = await _fact(session)
    await _memory_origin(session, fact_id, "session-1")
    await session.execute(
        text(
            "UPDATE knowledge_triples SET review_state = 'open', "
            "demotion_pending_since = now(), demotion_pending_cycles = 2 "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )
    await session.flush()

    await human_adjudication.ratify_fact(session, fact_id, actor="admin")
    await session.flush()

    row = await _row(session, fact_id)
    assert row["verification_status"] == CONFIRMED
    assert row["review_state"] is None
    assert row["demotion_pending_since"] is None
    assert row["demotion_pending_cycles"] == 0


@pytest.mark.asyncio
async def test_a_disputed_fact_is_ratifiable(session):
    """The veto is absolute against the *machine* (doc 08 §4.2). A human
    resolving a dispute by vouching is doc 08 §6's whole review loop, so a door
    that refused it would make the queue's principal case unresolvable."""
    fact_id = await _fact(session)
    await _memory_origin(session, fact_id, "session-1")
    await KnowledgeTripleRepository(session).set_verification_status(
        fact_id, "disputed", review_state="open",
    )
    await session.flush()

    await human_adjudication.ratify_fact(session, fact_id, actor="admin")
    await session.flush()

    assert (await _row(session, fact_id))["verification_status"] == CONFIRMED


# ───────────────────────────── the journal ─────────────────────────────


@pytest.mark.asyncio
async def test_the_transition_journals_once_with_a_ratify_outcome(session):
    fact_id = await _fact(session)
    await _memory_origin(session, fact_id, "session-1")

    await human_adjudication.ratify_fact(session, fact_id, actor="admin")
    await session.flush()

    events = await _verified_events(session, fact_id)
    assert len(events) == 1
    payload = events[0]
    assert payload["before"]["verification_status"] == "candidate"
    assert payload["after"]["verification_status"] == CONFIRMED
    assert payload["outcome"] == RATIFY_OUTCOME

    verdicts = await _human_verdicts(session, fact_id)
    assert len(verdicts) == 1
    assert verdicts[0]["payload"]["verdict"] == "ratified"
    # The verdict records the status the fact held when the human formed it,
    # not the one the ratification left behind.
    assert verdicts[0]["payload"]["verification_status"] == "candidate"
    assert verdicts[0]["actor"] == "admin"


@pytest.mark.asyncio
async def test_re_ratifying_does_not_journal_a_second_transition(session):
    """``events`` is append-only, so "a row means a transition" has to hold by
    construction. The human's second act still journals its own verdict."""
    fact_id = await _fact(session)
    await _memory_origin(session, fact_id, "session-1")

    await human_adjudication.ratify_fact(session, fact_id, actor="admin")
    await session.flush()
    await human_adjudication.ratify_fact(session, fact_id, actor="admin")
    await session.flush()

    assert len(await _verified_events(session, fact_id)) == 1
    assert len(await _human_verdicts(session, fact_id)) == 2

    sources = (await session.execute(
        text(
            "SELECT COUNT(*) FROM fact_sources WHERE fact_id = CAST(:id AS uuid) "
            "AND source_kind = CAST(:kind AS text)"
        ),
        {"id": str(fact_id), "kind": HUMAN_SOURCE_KIND},
    )).scalar_one()
    assert sources == 1


@pytest.mark.asyncio
async def test_the_ratify_payload_passes_the_gc_metrics_validator(session):
    """The G-C runner raises on a `verified` payload it cannot bucket, and it
    validates every row in the window rather than only the ones it counts — so
    a ratification it did not know about would fail the whole gate run."""
    from scripts.benchlib.promotion_metrics import validate_verified_event_payload

    fact_id = await _fact(session)
    await _memory_origin(session, fact_id, "session-1")
    await human_adjudication.ratify_fact(session, fact_id, actor="admin")
    await session.flush()

    events = await _verified_events(session, fact_id)
    # Without this the loop below is vacuous: if journaling ever stopped, the
    # test would pass by validating nothing.
    assert events
    for payload in events:
        validate_verified_event_payload(payload, event_id="ratify")


@pytest.mark.asyncio
async def test_a_ratification_is_invisible_to_the_promotion_rate(session):
    """The exclusion is arithmetic G-C depends on, so it is pinned rather than
    left to the eligibility SQL's shape.

    Counting a human's imprimatur in the machine's promotion rate would report
    the reviewer's diligence as the ladder's accuracy. Three independent things
    keep it out — the outcome filter, the absent `origin_count`/`required_n`,
    and the `before='candidate'` anchor — and this asserts the first two on the
    payload the shipped writer actually produces."""
    from scripts.benchlib.promotion_metrics import RATIFY_OUTCOME

    fact_id = await _fact(session)
    await _memory_origin(session, fact_id, "session-1")
    await human_adjudication.ratify_fact(session, fact_id, actor="admin")
    await session.flush()

    payload = (await _verified_events(session, fact_id))[0]
    assert payload["outcome"] == RATIFY_OUTCOME
    # The eligibility filter is `outcome IN ('promote', 'dispute')` plus a
    # supersession-blocked hold; a ratify is none of those.
    assert payload["outcome"] not in ("promote", "dispute", "hold")
    # And it carries no bar to have met, so the `origin_count >= required_n`
    # predicate is NULL for it even before the outcome test.
    assert "origin_count" not in payload and "required_n" not in payload


# ────────────────────────────── the door ──────────────────────────────


@pytest.mark.asyncio
async def test_the_route_ratifies_and_answers_no_content(client, auth_headers, session):
    """204, the shape reject established. The verb serves no memory-derived
    row, so it never becomes a content surface."""
    fact_id = await _fact(session)
    await _memory_origin(session, fact_id, "session-1")
    await session.commit()

    response = await client.post(
        RATIFY.format(fact_id=fact_id),
        json={"shown": "asserted by 1 distinct origin of kinds [memory]"},
        headers=auth_headers,
    )

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
async def test_the_ratified_fact_reads_back_confirmed_and_badged(
    client, auth_headers, session,
):
    """The caller's re-read is the half the verb deliberately does not serve,
    so it is asserted here rather than assumed: the badge the human sees after
    ratifying carries the rung and the trailing human-ratified clause."""
    fact_id = await _fact(session)
    await _memory_origin(session, fact_id, "session-1")
    await session.commit()

    ratified = await client.post(RATIFY.format(fact_id=fact_id), headers=auth_headers)
    assert ratified.status_code == 204

    response = await client.get(
        f"/api/v1/knowledge/facts/{fact_id}", headers=auth_headers
    )
    assert response.status_code == 200
    badge = response.json()["badge"]
    assert badge["verification_status"] == CONFIRMED
    assert badge["human_ratified"] is True
    assert "human-ratified" in badge["claim"]


@pytest.mark.asyncio
async def test_the_route_is_authenticated(client, session):
    fact_id = await _fact(session)
    await session.commit()
    response = await client.post(RATIFY.format(fact_id=fact_id))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_the_route_404s_an_unknown_fact(client, auth_headers):
    response = await client.post(
        RATIFY.format(fact_id=uuid.uuid4()), headers=auth_headers
    )
    assert response.status_code == 404

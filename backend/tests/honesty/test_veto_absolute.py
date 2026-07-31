"""honesty/veto-absolute — one contradiction beats any number of corroborations.

Consensus is not truth (doc 08 §4.2). However many origins corroborate a fact,
one non-echo contradiction over an overlapping validity window flips it to
``disputed``, because a confidently-wrong ``corroborated`` is the worst failure
this system can produce: every article that cites the fact and every agent that
propagates it inherits the claim.

The rule is asserted end to end through the real applier and the real
deterministic scan, because the failure it guards is a *veto expressed as a
weight* — a big enough pile of agreement outvoting one dissent — and that only
shows up when the pile is real.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.verification_ladder import recompute_fact

PROJECT = "honesty-veto-absolute"
REFERENCE = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
CORROBORATIONS = 25


async def _fact(session, *, subject: str, obj: str) -> str:
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=f"honesty-{uuid4()}",
        subject_name=subject,
        object_name=obj,
        rel_type="HAPPENED_ON",
        fact=f"{subject} happened on {obj}",
        reference_time=REFERENCE,
        project=PROJECT,
    )
    await session.flush()
    return row["id"]


async def _assert_origin(session, fact_id: str, origin_key: str) -> None:
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind="memory",
        source_ref=f"memory:{origin_key}",
        origin_key=origin_key,
    )
    await session.flush()


async def _status(session, fact_id: str) -> str:
    result = await session.execute(
        text(
            "SELECT verification_status FROM knowledge_triples "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )
    return result.scalar_one()


@pytest.mark.asyncio
async def test_twenty_five_origins_corroborate_a_fact_nothing_contradicts(session):
    """The control. Without it, the veto below could pass on a ladder that never
    promotes this shape at all."""
    fact_id = await _fact(session, subject="the cutover", obj="2024-03-01")
    for index in range(CORROBORATIONS):
        await _assert_origin(session, fact_id, f"session-{index}")

    decision = await recompute_fact(session, fact_id)

    assert decision.origin_count == CORROBORATIONS
    assert await _status(session, fact_id) == "corroborated"


@pytest.mark.asyncio
async def test_one_contradiction_beats_twenty_five_corroborations(session):
    fact_id = await _fact(session, subject="the cutover", obj="2024-03-01")
    for index in range(CORROBORATIONS):
        await _assert_origin(session, fact_id, f"session-{index}")

    counterpart = await _fact(session, subject="the cutover", obj="2024-09-01")
    await _assert_origin(session, counterpart, "one-dissenting-session")

    decision = await recompute_fact(session, fact_id)

    assert decision.origin_count == CORROBORATIONS, "the pile of agreement is real"
    assert decision.contradiction_blocked is True
    assert decision.target_status == "disputed"
    assert await _status(session, fact_id) == "disputed"


@pytest.mark.asyncio
async def test_the_veto_also_demotes_an_already_corroborated_fact(session):
    """Not merely a promotion block: a standing ``corroborated`` fact falls."""
    fact_id = await _fact(session, subject="the migration", obj="2024-03-01")
    for index in range(CORROBORATIONS):
        await _assert_origin(session, fact_id, f"session-{index}")
    await recompute_fact(session, fact_id)
    assert await _status(session, fact_id) == "corroborated"

    counterpart = await _fact(session, subject="the migration", obj="2024-09-01")
    await _assert_origin(session, counterpart, "one-dissenting-session")

    await recompute_fact(session, fact_id)

    assert await _status(session, fact_id) == "disputed"


@pytest.mark.asyncio
async def test_an_echo_of_the_corroborating_origins_never_vetoes(session):
    """The other half of the honest claim: the veto is absolute, not trigger-happy.

    A veto that fired on the fact's own origins restating themselves would make
    ``disputed`` meaningless, which costs exactly as much truth as a veto that
    never fires.
    """
    fact_id = await _fact(session, subject="the freeze", obj="2024-03-01")
    for index in range(CORROBORATIONS):
        await _assert_origin(session, fact_id, f"session-{index}")

    counterpart = await _fact(session, subject="the freeze", obj="2024-09-01")
    for index in range(CORROBORATIONS):
        await FactSourceRepository(session).add_source(
            fact_id=counterpart,
            source_kind="memory",
            source_ref=f"memory:restatement-{index}",
            origin_key="session-0",
        )
    await session.flush()

    await recompute_fact(session, fact_id)

    assert await _status(session, fact_id) == "corroborated"

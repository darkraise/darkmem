"""Consequence ranking and dispute-staleness decay (doc 08 §6, T2.24).

Three properties every test here is built to be able to fail on:

* **The two orders are seeded to disagree.** Every ranking assertion below
  fixes ``created_at`` explicitly so that arrival order and consequence order
  are *opposite*, and the arrival order is asserted too. A test whose fixture
  lets the two coincide proves nothing about either, so
  ``test_consequence_order_is_the_reverse_of_arrival_order`` pins both
  directions from one fixture.
* **The decay is proved to change priority and nothing else.** The
  invariant-14 test does not merely check the rank: it snapshots
  ``verification_status`` and ``review_state`` on disk across the ranked read,
  re-reads the fact through ordinary retrieval, and checks it is still counted
  by ``/counts`` and still carries both label columns. A decay implemented as
  a status write, a ``review_state`` write, or a narrowed membership predicate
  fails a different assertion in each case.
* **The onset predicate is pinned against the real producer**, not against a
  hand-rolled payload. ``test_onset_is_read_from_what_the_ladder_actually_
  journals`` drives ``set_verification_status`` for real and requires the
  queue to find the onset it wrote; a fixture-only test would happily agree
  with a payload spelling production never emits.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import review_queue as review_queue_service
from app.services.review_queue import ReviewQueueOrder, build_facts_query
from app.services.review_ranking import (
    DEFAULT_DISPUTE_STALE_DAYS,
    REVIEW_QUEUE_CONFIG_KEY,
    RankingConfig,
    W_RETRIEVAL_FREQUENCY,
    W_SUBJECT_SALIENCE,
    get_ranking_config,
)

pytestmark = pytest.mark.asyncio

T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
PROJECT = "t2-24-queue-ranking"


# ─────────────────────────────── fixtures ───────────────────────────────


async def _memory(session, *, content: str = "ranking fixture") -> UUID:
    memory_id = uuid4()
    session.add(Memory(id=memory_id, content=content, source="test", project=PROJECT))
    await session.flush()
    return memory_id


async def _access(session, memory_id: UUID, *, count: int, days_ago: float = 0.0) -> None:
    await session.execute(
        text(
            """
            INSERT INTO memory_access_stats (memory_id, access_count, last_accessed)
            VALUES (
                CAST(:mid AS uuid),
                CAST(:count AS integer),
                now() - (CAST(:days AS double precision) * INTERVAL '1 day')
            )
            """
        ),
        {"mid": str(memory_id), "count": count, "days": days_ago},
    )


async def _fact(
    session,
    *,
    subject: str,
    obj: str,
    rel: str = "RELATED_TO",
    project: str = PROJECT,
    review_state: str | None = "open",
    subject_id: UUID | None = None,
    created_days_ago: float | None = None,
) -> str:
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=f"k-{uuid4()}",
        subject_name=subject,
        object_name=obj,
        rel_type=rel,
        fact=f"{subject} {rel} {obj}",
        reference_time=T0,
        project=project,
        review_state=review_state,
        subject_id=subject_id,
    )
    if created_days_ago is not None:
        await session.execute(
            text(
                "UPDATE knowledge_triples "
                "SET created_at = now() - (CAST(:days AS double precision) "
                "                           * INTERVAL '1 day') "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": row["id"], "days": created_days_ago},
        )
    return row["id"]


async def _mark_disputed(session, fact_id: str) -> None:
    """Set the status without journalling.

    Deliberately not ``set_verification_status``: that writes a ``verified``
    row stamped ``now()``, which would pin the dispute onset to this instant
    and make every staleness fixture below untestable. The tests that need the
    real writer call it explicitly.
    """
    await session.execute(
        text(
            "UPDATE knowledge_triples SET verification_status = 'disputed' "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": fact_id},
    )


async def _dispute_onset(session, fact_id: str, *, days_ago: float, before: str = "candidate") -> None:
    """Journal a ``verified`` row at a controlled time.

    ``events`` is RANGE-partitioned by month and append-only (no UPDATE), so a
    back-dated row needs its partition created first and cannot be written
    through ``record_event`` and then adjusted.
    """
    await session.execute(
        text(
            """
            SELECT events_ensure_partition(
                CAST(date_trunc(
                    'month',
                    now() - (CAST(:days AS double precision) * INTERVAL '1 day')
                ) AS date)
            )
            """
        ),
        {"days": days_ago},
    )
    await session.execute(
        text(
            """
            INSERT INTO events (created_at, event_type, object_type, object_id,
                                project, payload)
            VALUES (
                now() - (CAST(:days AS double precision) * INTERVAL '1 day'),
                'verified', 'fact', CAST(:fid AS uuid), CAST(:project AS text),
                CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "days": days_ago,
            "fid": fact_id,
            "project": PROJECT,
            "payload": (
                '{"before": {"verification_status": "%s"}, '
                '"after": {"verification_status": "disputed"}}' % before
            ),
        },
    )


async def _source(session, fact_id: str, memory_id: UUID, *, ref: str | None = None) -> None:
    await session.execute(
        text(
            """
            INSERT INTO fact_sources (id, fact_id, source_kind, source_ref, origin_key)
            VALUES (gen_random_uuid(), CAST(:fid AS uuid), 'memory',
                    CAST(:ref AS text), CAST(:origin AS text))
            """
        ),
        {
            "fid": fact_id,
            "ref": ref if ref is not None else str(memory_id),
            "origin": f"origin-{uuid4()}",
        },
    )


async def _entity(session, name: str) -> UUID:
    entity_id = uuid4()
    await session.execute(
        text(
            "INSERT INTO entities (id, name, entity_type, memory_ids) "
            "VALUES (CAST(:id AS uuid), CAST(:name AS text), 'concept', '{}'::uuid[])"
        ),
        {"id": str(entity_id), "name": name},
    )
    return entity_id


async def _relate(session, source_id: UUID, target_id: UUID, rel_type: str = "RELATED_TO") -> None:
    await session.execute(
        text(
            "INSERT INTO entity_relations "
            "(id, source_entity_id, target_entity_id, rel_type, memory_ids) "
            "VALUES (gen_random_uuid(), CAST(:src AS uuid), CAST(:tgt AS uuid), "
            "        CAST(:rel AS text), '{}'::uuid[])"
        ),
        {"src": str(source_id), "tgt": str(target_id), "rel": rel_type},
    )


async def _set_config(session, value: dict) -> None:
    await session.execute(
        text(
            "INSERT INTO config (key, value) "
            "VALUES (CAST(:key AS text), CAST(:value AS jsonb)) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ),
        {"key": REVIEW_QUEUE_CONFIG_KEY, "value": __import__("json").dumps(value)},
    )


async def _order(session, **kwargs) -> list[str]:
    items, _ = await review_queue_service.list_open_facts(
        session, project=PROJECT, **kwargs
    )
    return [item["id"] for item in items]


# ───────────────────── retrieval frequency drives rank ─────────────────────


async def test_a_frequently_retrieved_fact_outranks_a_dormant_one(session):
    """Same arrival instant, so nothing but the access counters can separate
    them — a ranking that ignored ``memory_access_stats`` would leave the
    order to the id tiebreak and fail this roughly half the time, so the two
    ids are asserted in both directions of a fixed order rather than as a set."""
    hot_memory = await _memory(session)
    cold_memory = await _memory(session)
    await _access(session, hot_memory, count=200, days_ago=0.0)
    await _access(session, cold_memory, count=1, days_ago=0.0)

    hot = await _fact(session, subject="hot", obj="o", created_days_ago=5.0)
    dormant = await _fact(session, subject="dormant", obj="o", created_days_ago=5.0)
    await _source(session, hot, hot_memory)
    await _source(session, dormant, cold_memory)
    await session.commit()

    assert await _order(session) == [hot, dormant]


async def test_consequence_order_is_the_reverse_of_arrival_order(session):
    """Not-FIFO, proved by seeding the two orders to disagree.

    The hot fact is the *older* one, so arrival order (newest first) and
    consequence order are exact opposites. Reverting ``_DEFAULT_ORDER`` to
    ``ARRIVAL_DESC`` flips the first assertion; deleting the ranking entirely
    flips it too. The second assertion is the control: it shows the fixture
    really does produce a different arrival order, so the first one is not
    passing by accident."""
    hot_memory = await _memory(session)
    await _access(session, hot_memory, count=500, days_ago=0.0)

    old_hot = await _fact(session, subject="old-hot", obj="o", created_days_ago=40.0)
    new_cold = await _fact(session, subject="new-cold", obj="o", created_days_ago=1.0)
    await _source(session, old_hot, hot_memory)
    await session.commit()

    assert await _order(session) == [old_hot, new_cold]
    assert await _order(session, order=ReviewQueueOrder.ARRIVAL_DESC) == [
        new_cold,
        old_hot,
    ]


async def test_a_stale_burst_ranks_below_recent_traffic(session):
    """"The fact an agent hits every day", not the fact once hit a lot.

    Fifty accesses a year ago against five today: without the recency decay
    the raw counts put the dormant fact first, so removing the ``power(0.5,
    ...)`` term inverts this."""
    old_burst = await _memory(session)
    recent = await _memory(session)
    await _access(session, old_burst, count=50, days_ago=365.0)
    await _access(session, recent, count=5, days_ago=0.5)

    dormant = await _fact(session, subject="dormant", obj="o", created_days_ago=5.0)
    live = await _fact(session, subject="live", obj="o", created_days_ago=5.0)
    await _source(session, dormant, old_burst)
    await _source(session, live, recent)
    await session.commit()

    assert await _order(session) == [live, dormant]


async def test_many_cold_sources_do_not_outrank_one_hot_source(session):
    """The aggregate is MAX, not SUM.

    Six sources at 10 accesses each sum to 60 against a single source at 50,
    so a SUM implementation ranks the many-sourced fact first and fails here.
    This is the arm that keeps corroboration (many sources) from being counted
    a second time as consequence."""
    many = await _fact(session, subject="many-sourced", obj="o", created_days_ago=5.0)
    one = await _fact(session, subject="single-sourced", obj="o", created_days_ago=5.0)
    for _ in range(6):
        memory_id = await _memory(session)
        await _access(session, memory_id, count=10, days_ago=0.0)
        await _source(session, many, memory_id)
    hot = await _memory(session)
    await _access(session, hot, count=50, days_ago=0.0)
    await _source(session, one, hot)
    await session.commit()

    assert await _order(session) == [one, many]


async def test_adding_a_cold_source_never_lowers_a_facts_rank(session):
    """The monotonicity that rules AVG out: accumulating evidence must not
    demote a fact down the triage queue."""
    hot = await _memory(session)
    await _access(session, hot, count=100, days_ago=0.0)
    rival_memory = await _memory(session)
    await _access(session, rival_memory, count=30, days_ago=0.0)

    subject = await _fact(session, subject="subject", obj="o", created_days_ago=5.0)
    rival = await _fact(session, subject="rival", obj="o", created_days_ago=5.0)
    await _source(session, subject, hot)
    await _source(session, rival, rival_memory)
    await session.commit()
    assert await _order(session) == [subject, rival]

    cold = await _memory(session)
    await _access(session, cold, count=1, days_ago=90.0)
    await _source(session, subject, cold)
    await session.commit()

    assert await _order(session) == [subject, rival]


# ────────────────────────── subject salience ──────────────────────────


async def test_a_well_connected_subject_outranks_an_isolated_one(session):
    """Equal (absent) retrieval history, so only the salience arm can order
    these. The connected subject has five distinct neighbours; the isolated
    one has an entity row but no relations, which separates "no graph
    presence" from "no entity"."""
    connected = await _entity(session, "connected-subject")
    isolated = await _entity(session, "isolated-subject")
    for i in range(5):
        neighbour = await _entity(session, f"neighbour-{i}")
        await _relate(session, connected, neighbour)

    hub_fact = await _fact(
        session, subject="connected-subject", obj="o",
        subject_id=connected, created_days_ago=40.0,
    )
    lone_fact = await _fact(
        session, subject="isolated-subject", obj="o",
        subject_id=isolated, created_days_ago=1.0,
    )
    await session.commit()

    # Arrival order would put the isolated (newer) fact first; salience alone
    # has to overturn that.
    assert await _order(session) == [hub_fact, lone_fact]


async def test_salience_counts_distinct_neighbours_not_repeated_edges(session):
    """``entity_relations`` is UNIQUE on (source, target, rel_type), so a
    chatty corpus cannot inflate degree by re-asserting — but five relation
    types to one neighbour still would, if the count were over edges. One
    neighbour reached five ways must not outweigh three distinct neighbours."""
    five_ways = await _entity(session, "five-ways")
    three_neighbours = await _entity(session, "three-neighbours")
    single = await _entity(session, "single-neighbour")
    for rel in ("RELATED_TO", "USES", "DEPENDS_ON", "PART_OF", "MENTIONS"):
        await _relate(session, five_ways, single, rel)
    for i in range(3):
        await _relate(session, three_neighbours, await _entity(session, f"n{i}"))

    narrow = await _fact(
        session, subject="five-ways", obj="o",
        subject_id=five_ways, created_days_ago=1.0,
    )
    broad = await _fact(
        session, subject="three-neighbours", obj="o",
        subject_id=three_neighbours, created_days_ago=40.0,
    )
    await session.commit()

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    by_id = {item["id"]: item for item in items}
    assert by_id[narrow]["consequence"]["subject_salience"]["neighbour_count"] == 1
    assert by_id[broad]["consequence"]["subject_salience"]["neighbour_count"] == 3
    assert [item["id"] for item in items] == [broad, narrow]


async def test_incoming_edges_count_toward_salience(session):
    """Degree is undirected: a subject everything points *at* is salient even
    if it asserts nothing itself. Dropping the UNION ALL's second arm would
    silently zero this."""
    target = await _entity(session, "pointed-at")
    for i in range(4):
        await _relate(session, await _entity(session, f"pointer-{i}"), target)

    fact_id = await _fact(
        session, subject="pointed-at", obj="o", subject_id=target, created_days_ago=1.0,
    )
    await session.commit()

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert items[0]["id"] == fact_id
    assert items[0]["consequence"]["subject_salience"]["neighbour_count"] == 4


# ─────────────────────── the per-item explanation ───────────────────────


async def test_the_explanation_carries_every_component_value(session):
    """Done-when 1: explainable per item, not merely scored.

    Each arm's own inputs are asserted against the seeded data, and the total
    is asserted to be the sum of the two weighted components — so the block
    can be reproduced by hand from the parts. Replacing it with a bare float
    fails at the first subscript."""
    memory_id = await _memory(session)
    await _access(session, memory_id, count=64, days_ago=0.0)
    subject = await _entity(session, "explained-subject")
    for i in range(3):
        await _relate(session, subject, await _entity(session, f"e-neighbour-{i}"))

    fact_id = await _fact(
        session, subject="explained-subject", obj="o",
        subject_id=subject, created_days_ago=2.0,
    )
    await _source(session, fact_id, memory_id)
    await session.commit()

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    consequence = items[0]["consequence"]

    frequency = consequence["retrieval_frequency"]
    assert frequency["source_memories"] == 1
    assert frequency["peak_access_count"] == 64
    assert frequency["last_accessed"] is not None
    assert frequency["decayed_access"] == pytest.approx(64.0, rel=0.01)
    assert frequency["half_life_days"] == RankingConfig().access_half_life_days
    assert frequency["weight"] == W_RETRIEVAL_FREQUENCY

    salience = consequence["subject_salience"]
    assert salience["neighbour_count"] == 3
    assert salience["weight"] == W_SUBJECT_SALIENCE

    assert consequence["score"] == pytest.approx(
        frequency["component"] + salience["component"]
    )
    assert frequency["component"] > 0
    assert salience["component"] > 0

    staleness = consequence["staleness"]
    assert staleness["stale"] is False
    assert staleness["label"] == "active"
    assert staleness["threshold_days"] == DEFAULT_DISPUTE_STALE_DAYS


async def test_the_explanation_distinguishes_which_arm_produced_the_score(session):
    """Two facts with the same total for different reasons must not present
    the same explanation — the whole point of carrying components rather than
    a float."""
    memory_id = await _memory(session)
    await _access(session, memory_id, count=7, days_ago=0.0)
    subject = await _entity(session, "graph-only-subject")
    for i in range(3):
        await _relate(session, subject, await _entity(session, f"g-{i}"))

    by_heat = await _fact(session, subject="heat-only", obj="o", created_days_ago=2.0)
    await _source(session, by_heat, memory_id)
    by_graph = await _fact(
        session, subject="graph-only-subject", obj="o",
        subject_id=subject, created_days_ago=2.0,
    )
    await session.commit()

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    by_id = {item["id"]: item["consequence"] for item in items}

    assert by_id[by_heat]["retrieval_frequency"]["component"] > 0
    assert by_id[by_heat]["subject_salience"]["component"] == 0
    assert by_id[by_graph]["retrieval_frequency"]["component"] == 0
    assert by_id[by_graph]["subject_salience"]["component"] > 0


async def test_arrival_order_carries_no_consequence_block(session):
    """The block is a claim about a computation; a caller that opted out of
    the computation must not be handed a fabricated one."""
    await _fact(session, subject="a", obj="b", created_days_ago=1.0)
    await session.commit()

    items, _ = await review_queue_service.list_open_facts(
        session, project=PROJECT, order=ReviewQueueOrder.ARRIVAL_DESC,
    )
    assert items[0]["consequence"] is None


# ───────────── the decay: priority only (doc 08 §6, invariant 14) ─────────────


async def test_a_decayed_dispute_stays_disputed_queued_and_labelled(session):
    """The invariant-14 guard, and the one that matters most.

    A decay implemented as a ``verification_status`` write fails the status
    assertion; as a ``review_state`` write it fails the queue-membership and
    column assertions; as a narrowed membership predicate it fails the
    presence and ``/counts`` assertions; as a retrieval filter it fails the
    ``get_live`` assertions. Only a rank change passes all of them."""
    repo = KnowledgeTripleRepository(session)
    stale = await _fact(session, subject="stale-subject", obj="o", created_days_ago=200.0)
    await _mark_disputed(session, stale)
    await _dispute_onset(session, stale, days_ago=120.0)
    fresh = await _fact(session, subject="fresh-subject", obj="o", created_days_ago=1.0)
    await _mark_disputed(session, fresh)
    await _dispute_onset(session, fresh, days_ago=1.0)
    await session.commit()

    items, total = await review_queue_service.list_open_facts(session, project=PROJECT)
    by_id = {item["id"]: item for item in items}

    # 1. still on the queue, and counted
    assert total == 2
    assert stale in by_id
    counts = await review_queue_service.counts(session)
    assert counts["facts"] >= 2

    # 2. still disputed, still open — on the item and on disk
    assert by_id[stale]["verification_status"] == "disputed"
    assert by_id[stale]["review_state"] == "open"
    assert by_id[stale]["reason"] == "disputed"
    on_disk = (
        await session.execute(
            text(
                "SELECT verification_status, review_state FROM knowledge_triples "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": stale},
        )
    ).mappings().one()
    assert on_disk["verification_status"] == "disputed"
    assert on_disk["review_state"] == "open"

    # 3. labelled as stale, and ranked below the fresh dispute
    assert by_id[stale]["consequence"]["staleness"]["stale"] is True
    assert by_id[stale]["consequence"]["staleness"]["label"] == "stale_labelled"
    assert by_id[stale]["consequence"]["tier"] == 0
    assert by_id[fresh]["consequence"]["staleness"]["stale"] is False
    assert by_id[fresh]["consequence"]["tier"] == 1
    assert [item["id"] for item in items] == [fresh, stale]

    # 4. still served by ordinary retrieval, still carrying its label columns
    live = await repo.get_live(
        project=PROJECT, subject_name="stale-subject", rel_type="RELATED_TO",
    )
    assert [row["id"] for row in live] == [stale]
    assert live[0]["verification_status"] == "disputed"
    assert live[0]["review_state"] == "open"


async def test_a_hot_stale_dispute_still_ranks_below_a_cold_active_one(session):
    """"Drops off the active queue" is categorical, not a penalty factor: a
    multiplicative decay would leave a hot enough stale dispute above fresh
    work, and this is the fixture that would catch it."""
    hot = await _memory(session)
    await _access(session, hot, count=100000, days_ago=0.0)

    stale = await _fact(session, subject="hot-stale", obj="o", created_days_ago=200.0)
    await _mark_disputed(session, stale)
    await _dispute_onset(session, stale, days_ago=120.0)
    await _source(session, stale, hot)
    cold_active = await _fact(session, subject="cold-active", obj="o", created_days_ago=100.0)
    await session.commit()

    assert await _order(session) == [cold_active, stale]


async def test_consequence_still_orders_within_the_stale_tier(session):
    """The decay demotes a tier; it does not flatten the ranking inside it."""
    hot = await _memory(session)
    await _access(session, hot, count=400, days_ago=0.0)

    hot_stale = await _fact(session, subject="hot-stale", obj="o", created_days_ago=200.0)
    cold_stale = await _fact(session, subject="cold-stale", obj="o", created_days_ago=199.0)
    for fact_id in (hot_stale, cold_stale):
        await _mark_disputed(session, fact_id)
        await _dispute_onset(session, fact_id, days_ago=120.0)
    await _source(session, hot_stale, hot)
    await session.commit()

    # cold_stale is the newer arrival, so arrival order would put it first.
    assert await _order(session) == [hot_stale, cold_stale]


async def test_a_reaffirmed_dispute_does_not_reset_the_staleness_clock(session):
    """The contradiction-blocked hold journals ``before == after ==
    disputed`` on every scan pass. Reading the *latest* ``verified`` row as
    the onset would refresh the clock forever and nothing would ever decay,
    so the onset predicate requires the transition into dispute."""
    fact_id = await _fact(session, subject="reaffirmed", obj="o", created_days_ago=200.0)
    await _mark_disputed(session, fact_id)
    await _dispute_onset(session, fact_id, days_ago=120.0)
    await _dispute_onset(session, fact_id, days_ago=0.0, before="disputed")
    await session.commit()

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    staleness = items[0]["consequence"]["staleness"]
    assert staleness["stale"] is True
    assert staleness["dispute_age_days"] == pytest.approx(120.0, abs=0.1)


async def test_a_dispute_that_was_resolved_and_reopened_dates_from_the_reopen(session):
    """The mirror of the test above: a genuine re-entry into dispute *is* a
    new onset, so a fact disputed long ago, recovered, and disputed again
    last week is not stale."""
    fact_id = await _fact(session, subject="reopened", obj="o", created_days_ago=300.0)
    await _mark_disputed(session, fact_id)
    await _dispute_onset(session, fact_id, days_ago=250.0)
    await _dispute_onset(session, fact_id, days_ago=3.0, before="corroborated")
    await session.commit()

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    staleness = items[0]["consequence"]["staleness"]
    assert staleness["stale"] is False
    assert staleness["dispute_age_days"] == pytest.approx(3.0, abs=0.1)


async def test_a_dispute_with_no_journalled_onset_is_not_stale(session):
    """The conservative fallback. Failing to decay costs the maintainer one
    glance; wrongly decaying pushes an item out of the tier they are reading.
    Falling back to ``knowledge_triples.created_at`` would decay this
    year-old fact's brand-new dispute on sight."""
    fact_id = await _fact(session, subject="unjournalled", obj="o", created_days_ago=400.0)
    await _mark_disputed(session, fact_id)
    await session.commit()

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    staleness = items[0]["consequence"]["staleness"]
    assert staleness["stale"] is False
    assert staleness["dispute_opened_at"] is None
    assert staleness["dispute_age_days"] is None
    assert items[0]["consequence"]["tier"] == 1


async def test_a_non_disputed_open_fact_never_decays(session):
    """The decay is scoped to disputes (doc 08 §6). T2.46's under-sourced
    hysteresis opens the same column and must not inherit a clock written for
    a different opener."""
    fact_id = await _fact(session, subject="under-sourced", obj="o", created_days_ago=400.0)
    await _dispute_onset(session, fact_id, days_ago=300.0)
    await session.commit()

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert items[0]["verification_status"] == "candidate"
    assert items[0]["consequence"]["staleness"]["stale"] is False
    assert items[0]["consequence"]["staleness"]["dispute_opened_at"] is None


async def test_onset_is_read_from_what_the_ladder_actually_journals(session):
    """Pins the payload spelling against the real producer.

    ``set_verification_status`` is the sole journaller of verification
    transitions; if its payload shape and this module's onset predicate ever
    disagree, no fixture-seeded test would notice — every dispute would
    silently read as "no onset" and nothing would ever decay."""
    fact_id = await _fact(session, subject="real-writer", obj="o", created_days_ago=5.0)
    repo = KnowledgeTripleRepository(session)
    await repo.set_verification_status(
        fact_id,
        "disputed",
        confidence=0.3,
        outcome="dispute",
        origin_count=1,
        required_n=2,
        gate_fired="none",
        source_kinds=("memory",),
        contradiction_blocked=True,
    )
    await session.commit()

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    staleness = items[0]["consequence"]["staleness"]
    assert staleness["dispute_opened_at"] is not None, (
        "the onset predicate did not match the payload set_verification_status "
        "actually writes"
    )
    assert staleness["dispute_age_days"] == pytest.approx(0.0, abs=0.01)
    assert staleness["stale"] is False


async def test_the_ranked_read_writes_nothing(session):
    """Structural proof that ranking is a read: the full verification-axis
    snapshot is byte-identical across a ranked list call."""
    fact_id = await _fact(session, subject="untouched", obj="o", created_days_ago=200.0)
    await _mark_disputed(session, fact_id)
    await _dispute_onset(session, fact_id, days_ago=150.0)
    await session.commit()

    snapshot_sql = text(
        "SELECT id, verification_status, review_state, confidence, expired_at, "
        "       invalid_at, created_at "
        "FROM knowledge_triples ORDER BY id"
    )
    before = [dict(r) for r in (await session.execute(snapshot_sql)).mappings().all()]
    event_count_sql = text("SELECT COUNT(*) FROM events")
    events_before = (await session.execute(event_count_sql)).scalar_one()

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert items[0]["consequence"]["staleness"]["stale"] is True

    after = [dict(r) for r in (await session.execute(snapshot_sql)).mappings().all()]
    assert after == before
    assert (await session.execute(event_count_sql)).scalar_one() == events_before


# ────────────────────── dispute_stale_days is a config row ──────────────────────


async def test_the_config_row_changes_which_disputes_decay(session):
    """Done-when 3. One fixture, two thresholds, opposite outcomes — so the
    row is proved to drive behaviour rather than merely to be readable."""
    fact_id = await _fact(session, subject="threshold", obj="o", created_days_ago=200.0)
    await _mark_disputed(session, fact_id)
    await _dispute_onset(session, fact_id, days_ago=45.0)
    await session.commit()

    # Default (30 days): a 45-day-old dispute is stale.
    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert items[0]["consequence"]["staleness"]["stale"] is True
    assert items[0]["consequence"]["staleness"]["threshold_days"] == 30

    await _set_config(session, {"dispute_stale_days": 90})
    await session.commit()
    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert items[0]["consequence"]["staleness"]["stale"] is False
    assert items[0]["consequence"]["staleness"]["threshold_days"] == 90

    await _set_config(session, {"dispute_stale_days": 7})
    await session.commit()
    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert items[0]["consequence"]["staleness"]["stale"] is True
    assert items[0]["consequence"]["staleness"]["threshold_days"] == 7


async def test_the_config_row_changes_the_ranked_order(session):
    """Not just the label: widening the threshold has to move an item back up
    into the active tier."""
    stale = await _fact(session, subject="s", obj="o", created_days_ago=200.0)
    await _mark_disputed(session, stale)
    await _dispute_onset(session, stale, days_ago=45.0)
    active = await _fact(session, subject="a", obj="o", created_days_ago=199.0)
    await session.commit()

    assert await _order(session) == [active, stale]

    await _set_config(session, {"dispute_stale_days": 90})
    await session.commit()
    # Both now active and both scoreless, so arrival order decides: `active`
    # is the newer row, hence still first — the ids alone would not show the
    # tier moved, so the tier is asserted directly.
    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert {item["id"]: item["consequence"]["tier"] for item in items} == {
        stale: 1,
        active: 1,
    }


async def test_the_half_life_is_configurable_and_changes_the_score(session):
    memory_id = await _memory(session)
    await _access(session, memory_id, count=1000, days_ago=60.0)
    fact_id = await _fact(session, subject="decaying", obj="o", created_days_ago=1.0)
    await _source(session, fact_id, memory_id)
    await session.commit()

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    # 60 days at a 30-day half-life is two halvings: 1000 -> ~250.
    assert items[0]["consequence"]["retrieval_frequency"]["decayed_access"] == pytest.approx(
        250.0, rel=0.02
    )

    await _set_config(session, {"access_half_life_days": 60})
    await session.commit()
    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert items[0]["consequence"]["retrieval_frequency"]["decayed_access"] == pytest.approx(
        500.0, rel=0.02
    )
    assert items[0]["consequence"]["retrieval_frequency"]["half_life_days"] == 60


async def test_a_malformed_config_row_degrades_to_the_defaults(session):
    """The row is operator-edited with no schema in front of it, and it feeds
    the triage screen — a typo must not take that screen down."""
    await _set_config(
        session,
        {"dispute_stale_days": "thirty", "access_half_life_days": True, "nonsense": 1},
    )
    await session.commit()
    config = await get_ranking_config(session)
    assert config == RankingConfig()

    await _set_config(session, {"dispute_stale_days": 0})
    await session.commit()
    assert (await get_ranking_config(session)).dispute_stale_days == 1

    await _set_config(session, {"dispute_stale_days": 99999})
    await session.commit()
    assert (await get_ranking_config(session)).dispute_stale_days == 3650

    await session.execute(
        text(
            "INSERT INTO config (key, value) VALUES (CAST(:k AS text), CAST(:v AS jsonb)) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ),
        {"k": REVIEW_QUEUE_CONFIG_KEY, "v": '"not-an-object"'},
    )
    await session.commit()
    assert await get_ranking_config(session) == RankingConfig()


# ────────────────────── membership and index are untouched ──────────────────────


async def test_ranking_does_not_change_queue_membership(session):
    """The ranking reorders; it must not add or drop a member. Widening the
    predicate to reach a ranking input is the failure this catches."""
    open_ids = set()
    for i in range(4):
        open_ids.add(await _fact(session, subject=f"open-{i}", obj="o", created_days_ago=i + 1))
    for i in range(3):
        await _fact(session, subject=f"closed-{i}", obj="o", review_state=None)
    await _fact(session, subject="other-project", obj="o", project=f"{PROJECT}-other")
    await session.commit()

    ranked, ranked_total = await review_queue_service.list_open_facts(
        session, project=PROJECT,
    )
    arrival, arrival_total = await review_queue_service.list_open_facts(
        session, project=PROJECT, order=ReviewQueueOrder.ARRIVAL_DESC,
    )
    assert {item["id"] for item in ranked} == open_ids
    assert {item["id"] for item in arrival} == open_ids
    assert ranked_total == arrival_total == 4


async def test_the_ranked_statement_still_uses_the_partial_index(session):
    """T2.22's Done-when, re-proved against the statement that replaced the
    one it proved. Seeded past the point the planner prefers a sequential
    scan on its own merits — no planner hints."""
    await session.execute(
        text(
            """
            INSERT INTO knowledge_triples (
                id, subject_name, object_name, rel_type, reference_time,
                fact, triple_key, review_state, created_at
            )
            SELECT gen_random_uuid(), 'rank-subject-' || g, 'rank-object-' || g,
                   'RELATED_TO', now(), 'rank fact ' || g, 'rank-triple-' || g,
                   CASE WHEN g % 200 = 0 THEN 'open' ELSE NULL END,
                   now() - (g || ' minutes')::interval
            FROM generate_series(1, 6000) g
            """
        )
    )
    await session.execute(text("ANALYZE knowledge_triples"))

    items_sql, _ = build_facts_query(None)
    assert "active_tier" in items_sql, "the default order is no longer CONSEQUENCE"
    plan = "\n".join(
        r[0]
        for r in await session.execute(
            text("EXPLAIN " + items_sql), {"limit": 50, "offset": 0}
        )
    )
    assert "ix_knowledge_triples_review" in plan, plan
    assert "Seq Scan on knowledge_triples" not in plan, plan


async def test_pagination_is_stable_across_pages_under_the_ranked_order(session):
    """Ties fall through to a total order (created_at, id), so no row is
    served twice and none is skipped — a non-total sort key would show up
    here as a duplicate or a gap."""
    ids = [
        await _fact(session, subject="page", obj=f"o{i}", created_days_ago=i + 1)
        for i in range(5)
    ]
    await session.commit()

    seen: list[str] = []
    for offset in range(0, 6, 2):
        page, total = await review_queue_service.list_open_facts(
            session, project=PROJECT, limit=2, offset=offset,
        )
        assert total == 5
        seen.extend(item["id"] for item in page)
    assert seen == ids  # created_days_ago ascending == created_at descending
    assert len(set(seen)) == 5


# ─────────────────────────── degradation paths ───────────────────────────


async def test_a_memory_ref_that_is_not_a_uuid_is_invisible_rather_than_fatal(session):
    """``fact_sources.source_ref`` holds every kind's spelling, and nothing on
    disk stops a memory-kind row carrying a ref ``memory_source_ref`` never
    minted. Without the canonical-shape guard this ref reaches ``CAST(... AS
    uuid)`` and takes the entire triage screen down with an
    ``InvalidTextRepresentation``; with it, the fact scores zero heat and the
    page still renders. Removing the ``~`` predicate turns this into an
    error, not a wrong number."""
    fact_id = await _fact(session, subject="bad-ref", obj="o", created_days_ago=1.0)
    await session.execute(
        text(
            "INSERT INTO fact_sources (id, fact_id, source_kind, source_ref, origin_key) "
            "VALUES (gen_random_uuid(), CAST(:fid AS uuid), 'memory', "
            "        'not-a-uuid-at-all', 'o-1')"
        ),
        {"fid": fact_id},
    )
    await session.commit()

    items, total = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert total == 1
    assert items[0]["consequence"]["retrieval_frequency"]["source_memories"] == 0
    assert items[0]["consequence"]["retrieval_frequency"]["decayed_access"] == 0.0


async def test_a_non_canonically_spelled_ref_scores_no_heat(session):
    """The spelling contract, not the crash guard. Postgres' uuid input
    happens to *accept* the braced form, so this ref would join fine — it is
    excluded anyway, because the withdrawal sweep cannot match it either and a
    ref that is invisible to provenance must not be visible to ranking. A
    producer bypassing ``memory_source_ref`` fails invisibly on both sides
    rather than on one."""
    memory_id = await _memory(session)
    await _access(session, memory_id, count=99, days_ago=0.0)

    fact_id = await _fact(session, subject="braced-ref", obj="o", created_days_ago=1.0)
    await _source(session, fact_id, memory_id, ref=f"{{{memory_id}}}")
    await session.commit()

    items, total = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert total == 1
    assert items[0]["consequence"]["retrieval_frequency"]["source_memories"] == 0
    assert items[0]["consequence"]["retrieval_frequency"]["decayed_access"] == 0.0


async def test_a_non_memory_source_kind_never_reaches_the_uuid_cast(session):
    """A ``human`` reviewer's ref is not a memory id by construction, so a
    hoisted cast would raise here instead of returning a row.

    Honest about its own strength: dropping the ``AS MATERIALIZED`` fence was
    tried and this still passed, because PostgreSQL 17 does not choose to
    hoist the qual for this statement's shape. It pins the *outcome*, not the
    fence. The guard measured to be load-bearing is the canonical-shape regex,
    two tests up."""
    fact_id = await _fact(session, subject="human-sourced", obj="o", created_days_ago=1.0)
    await session.execute(
        text(
            "INSERT INTO fact_sources (id, fact_id, source_kind, source_ref, origin_key) "
            "VALUES (gen_random_uuid(), CAST(:fid AS uuid), 'human', "
            "        'reviewer@example.com', 'human-1')"
        ),
        {"fid": fact_id},
    )
    await session.commit()

    items, total = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert total == 1
    assert items[0]["consequence"]["retrieval_frequency"]["source_memories"] == 0


async def test_a_fact_whose_subject_entity_was_pruned_scores_zero_salience(session):
    """Facts outlive their endpoints by design (the triples carry no FK to
    ``entities``), so a dangling ``subject_id`` must degrade, not raise."""
    subject = await _entity(session, "doomed-subject")
    await _relate(session, subject, await _entity(session, "neighbour"))
    fact_id = await _fact(
        session, subject="doomed-subject", obj="o",
        subject_id=subject, created_days_ago=1.0,
    )
    await session.commit()

    items, _ = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert items[0]["consequence"]["subject_salience"]["neighbour_count"] == 1

    await session.execute(
        text("DELETE FROM entities WHERE id = CAST(:id AS uuid)"), {"id": str(subject)}
    )
    await session.commit()

    items, total = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert total == 1
    assert items[0]["id"] == fact_id
    assert items[0]["consequence"]["subject_salience"]["neighbour_count"] == 0


async def test_a_deleted_source_memory_degrades_that_arm_only(session):
    """``fact_sources`` has no FK to ``memories`` and the withdrawal sweep is
    a backstop on a cadence, so a ref naming a deleted memory is reachable."""
    memory_id = await _memory(session)
    await _access(session, memory_id, count=42, days_ago=0.0)
    fact_id = await _fact(session, subject="orphaned", obj="o", created_days_ago=1.0)
    await _source(session, fact_id, memory_id)
    await session.commit()

    await session.execute(
        text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"), {"id": str(memory_id)}
    )
    await session.commit()

    items, total = await review_queue_service.list_open_facts(session, project=PROJECT)
    assert total == 1
    assert items[0]["consequence"]["retrieval_frequency"]["source_memories"] == 0


# ──────────────────────────── the REST surface ────────────────────────────


async def test_the_consequence_block_rides_the_rest_response(client, auth_headers, session):
    """The explanation has to reach the human, not merely exist in the
    service layer — the response model is where a bare score would be caught."""
    memory_id = await _memory(session)
    await _access(session, memory_id, count=16, days_ago=0.0)
    fact_id = await _fact(session, subject="rest-ranked", obj="o", created_days_ago=1.0)
    await _source(session, fact_id, memory_id)
    await session.commit()

    response = await client.get(
        "/api/v1/review-queue/facts", params={"project": PROJECT}, headers=auth_headers,
    )
    assert response.status_code == 200
    item = response.json()["items"][0]
    consequence = item["consequence"]
    assert consequence["score"] > 0
    assert consequence["tier"] == 1
    assert consequence["retrieval_frequency"]["peak_access_count"] == 16
    assert consequence["subject_salience"]["neighbour_count"] == 0
    assert consequence["staleness"]["stale"] is False
    assert consequence["staleness"]["threshold_days"] == DEFAULT_DISPUTE_STALE_DAYS


async def test_the_rest_response_ranks_by_consequence(client, auth_headers, session):
    hot = await _memory(session)
    await _access(session, hot, count=300, days_ago=0.0)
    old_hot = await _fact(session, subject="rest-old-hot", obj="o", created_days_ago=30.0)
    await _source(session, old_hot, hot)
    new_cold = await _fact(session, subject="rest-new-cold", obj="o", created_days_ago=1.0)
    await session.commit()

    response = await client.get(
        "/api/v1/review-queue/facts", params={"project": PROJECT}, headers=auth_headers,
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [old_hot, new_cold]


async def test_the_ranking_never_writes_the_two_forbidden_columns():
    """A source scan, not a behavioural one. T2.62's ruling forbids this
    layer from writing ``review_state``, and invariant 14 forbids it from
    writing ``verification_status``; a future edit that reached for either is
    caught here even if it never runs in a test."""
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "app" / "services" / "review_ranking.py"
    body = source.read_text(encoding="utf-8")
    for statement in ("UPDATE knowledge_triples", "INSERT INTO", "DELETE FROM"):
        assert statement not in body, (
            f"{statement} in review_ranking.py — the decay changes priority "
            "and nothing else (doc 08 §6, invariant 14)"
        )

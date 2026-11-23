"""T2.70 — grouping and the answer budget, settled at a fixpoint.

The defect this file pins was found by running the real ``search()`` path, not
by reading it: grouping ran to completion and the cut sliced its output, so a
memory nested under a fact that fell past the cut left the result with that
fact. It was served nowhere and counted nowhere, and an unrelated row was
promoted into the slot the pair vacated.

What is asserted here, and in what strength:

* the measured ``limit=4`` case itself, end to end, against real provenance
  rows — the shape the defect was reported in;
* the **general** property behind it (Done-when 1): a row inside the first
  ``limit`` of the ungrouped order is always reachable in the served output,
  swept over randomised support maps rather than over the one fixture that
  happened to expose it;
* the fixpoint rule by name — that the page is the settled point of a
  *descending* iteration, that the iteration really iterates on a fixture
  needing more than one round, and that a step which fails to shrink raises
  instead of spinning;
* the count (Done-when 5, R3): every composed row not reachable in the output
  is tallied in the envelope, checked **at the wire** through the same
  serialiser MCP's ``knowledge_search`` spends.

What is deliberately **not** claimed. ``by_result_limit`` counts rows this
request composed and did not serve; it is not a count of further matches in
the corpus, because each channel fetched at most ``limit`` of its own and
nothing looked past that. And the sweep below randomises the support map and
the budget over one fixed row ordering — it does not randomise band or tier,
so it exercises the interaction of nesting with the cut and not the ordering
that feeds them.

Second residual, from T2.81's review: both sweeps draw **at most one** sourcing
fact per memory (``rng.choice(facts)``, once per memory), so the path where a
memory sources several facts and only some of them survive the cut — the one
where grouping has to choose an incumbent — is never generated here. The
reviewer's own brute force covered it (0–3 facts per memory, 200 configurations,
``F`` evaluated over the full powerset, 0 violations), and the termination and
monotonicity arguments are support-map-agnostic, so this is a stated gap in
these sweeps rather than an untested property. A regression specific to that
path would not be caught below.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.memory import Memory
from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.schemas.knowledge import knowledge_search_response
from app.services import facts_channel, hybrid_search
from app.services import layer_composition as lc
from app.services.fact_provenance import memory_source_ref

PROJECT = "t2-70-grouping-cut"


class _FakeLLM:
    async def embed(self, query: str):
        return [0.0], "fp"


def _memory_row(memory_id, **extra) -> dict:
    row = {
        "memory_id": memory_id,
        "payload": {"content": "a memory"},
        "project": PROJECT,
        "status": "active",
        "rrf_score": 0.1,
    }
    row.update(extra)
    return row


def _fact_row(fact_id, **extra) -> dict:
    row = {
        "fact_id": fact_id,
        "id": fact_id,
        "fact": "a fact",
        "subject_name": "postgres",
        "rel_type": "DEPLOYED_ON",
        "object_name": "homelab",
        "project": PROJECT,
        "verification_status": "corroborated",
        "review_state": None,
        "rrf_score": 0.1,
    }
    row.update(extra)
    return row


def _stub_channels(monkeypatch, memory_rows, fact_rows):
    # Descending scores in list order: the memory channel serves its rows by
    # score, and equal scores would order by id instead of by this list.
    served = [
        {**row, "rrf_score": row["rrf_score"] - index * 1e-3}
        for index, row in enumerate(memory_rows)
    ]

    async def _memory(self, *args, **kwargs):
        return hybrid_search.ChannelTrace(results=list(served))

    async def _facts(self, *args, **kwargs):
        return facts_channel.FactChannelTrace(results=list(fact_rows))

    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _memory)
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _facts)


async def _seed_fact_with_sources(session, *, memory_count: int):
    """One real triple, real memories, and the real ``fact_sources`` rows."""
    memory_ids = []
    for index in range(memory_count):
        memory_id = uuid4()
        session.add(Memory(
            id=memory_id,
            content=f"postgres runs on the homelab box ({index})",
            source="test",
            project=PROJECT,
        ))
        memory_ids.append(memory_id)
    await session.flush()
    fact = await KnowledgeTripleRepository(session).insert_open(
        triple_key=f"k-{uuid4()}",
        subject_name="postgres",
        object_name="homelab",
        rel_type="DEPLOYED_ON",
        fact="postgres runs on the homelab box",
        reference_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        project=PROJECT,
    )
    repo = FactSourceRepository(session)
    for index, memory_id in enumerate(memory_ids):
        await repo.add_source(
            fact_id=fact["id"],
            source_kind="memory",
            source_ref=memory_source_ref(memory_id),
            origin_key=f"session-{index}",
        )
    await session.commit()
    return fact["id"], memory_ids


def _reachable(rows) -> set[str]:
    """Every id a caller can read off the served page, nested rows included."""
    return {row.id for row in rows} | {
        nested.id for row in rows for nested in row.supported_by
    }


# ─────────────── the measured case, on the path it was measured on ───────────────


@pytest.mark.asyncio
async def test_the_measured_limit_four_case_keeps_the_nested_memory(session, monkeypatch):
    """The reported defect, as the reviewer's driver found it.

    Four facts and two memories, with ``M2`` sourcing ``F4``. The ungrouped
    order is ``[F1, M1, F2, M2]`` at a budget of four. Before T2.70 the grouped
    answer was ``[F1, M1, F2, F3]``: ``M2`` had gone into ``F4``'s group, ``F4``
    was the fifth row, and both left together while ``F3`` was promoted into
    the space. ``M2`` had ranked above the cut on its own.

    The ordering it relies on: bands run 1..4 over the fact channel and 1..2
    over the memory channel, and the sort is ``(band, -tier, key)``, so a
    corroborated fact precedes a memory of the same band.
    """
    cut_fact, (nested_memory,) = await _seed_fact_with_sources(session, memory_count=1)
    # The filler facts need no rows of their own: the provenance lookup is
    # keyed by fact id and an id it does not find simply sources nothing.
    served_facts = [uuid4(), uuid4(), uuid4()]
    lone_memory = uuid4()

    _stub_channels(
        monkeypatch,
        [_memory_row(lone_memory), _memory_row(nested_memory)],
        [_fact_row(fact_id) for fact_id in [*served_facts, cut_fact]],
    )
    service = lc.LayerCompositionService(_FakeLLM(), session)

    page = await service.search("q", project=PROJECT, limit=4)

    assert [row.id for row in page.rows] == [
        str(served_facts[0]), str(lone_memory), str(served_facts[1]), str(nested_memory),
    ]
    # M2 is served in its own right, not nested: F4 did not survive the cut, so
    # it is not a fact doc 07 §5 lets anything be nested under.
    assert page.rows[3].grouping == {"grouped_under": None, "relation": None}
    # The two facts that leave are the ordinary tail of the order, and they are
    # counted rather than merely absent.
    assert str(cut_fact) not in _reachable(page.rows)
    assert page.envelope.excluded["by_result_limit"] == 2

    # One slot further and the group is served whole, evidence nested — so the
    # un-nesting above is the budget, not a collapse that stopped working.
    uncut = await service.search("q", project=PROJECT, limit=5)

    assert [row.id for row in uncut.rows][-1] == str(cut_fact)
    assert [n.id for n in uncut.rows[-1].supported_by] == [str(nested_memory)]
    assert uncut.envelope.excluded["by_result_limit"] == 0


# ─────────────── the general property, not the one fixture ───────────────


def _sweep_candidates(fact_count: int, memory_count: int):
    facts = [uuid4() for _ in range(fact_count)]
    memories = [uuid4() for _ in range(memory_count)]
    candidates = [
        lc.fact_candidate(_fact_row(fact_id), channel_rank=rank)
        for rank, fact_id in enumerate(facts, start=1)
    ]
    candidates += [
        lc.memory_candidate(_memory_row(memory_id), channel_rank=rank)
        for rank, memory_id in enumerate(memories, start=1)
    ]
    return facts, memories, candidates


def test_a_row_above_the_cut_is_never_carried_out_by_the_fact_it_nested_under():
    """Done-when 1, as a property over randomised provenance rather than one case.

    For every budget and every support map drawn, the claim checked is the
    task's own: a row that would be served by the ungrouped order at this
    budget is reachable in the grouped page — as a top-level row or nested
    under a fact that is itself served.

    The **counted** half rides along (Done-when 5): the rows that are not
    reachable are exactly ``excluded_by_result_limit`` of them, so no row can
    leave without the envelope moving.
    """
    rng = random.Random(20260804)
    for _ in range(300):
        fact_count = rng.randint(1, 6)
        memory_count = rng.randint(1, 6)
        facts, memories, candidates = _sweep_candidates(fact_count, memory_count)
        support = lc.support_map(
            (rng.choice(facts), memory_id)
            for memory_id in memories
            if rng.random() < 0.7
        )
        limit = rng.randint(1, fact_count + memory_count)

        ungrouped = lc.compose(candidates).rows[:limit]
        page = lc.compose(candidates, fact_sources=support, limit=limit)

        reachable = _reachable(page.rows)
        for row in ungrouped:
            assert row.id in reachable, (
                f"{row.key} ranked inside a budget of {limit} ungrouped and is "
                f"reachable nowhere in the grouped page"
            )
        assert page.excluded_by_result_limit == len(candidates) - len(reachable)


def test_no_served_fact_is_served_beside_its_own_source_memory():
    """Why the *greatest* fixpoint, and not the surviving-prefix alternative.

    A conservative rule — nest only under a fact whose ungrouped position is
    already inside the budget — is sound and single-pass, but it refuses facts
    the budget does in fact reach, and then serves such a fact and its own
    source memory as two top-level rows. That is the triple count step 5
    exists to remove. Descending to the greatest fixpoint makes the pair
    unrepresentable, and this is the assertion that would fail if the rule were
    swapped for the cheaper one.
    """
    rng = random.Random(20260804)
    for _ in range(300):
        fact_count = rng.randint(1, 6)
        memory_count = rng.randint(1, 6)
        facts, memories, candidates = _sweep_candidates(fact_count, memory_count)
        pairs = [
            (rng.choice(facts), memory_id)
            for memory_id in memories
            if rng.random() < 0.7
        ]
        support = lc.support_map(pairs)
        limit = rng.randint(1, fact_count + memory_count)

        rows = lc.compose(candidates, fact_sources=support, limit=limit).rows
        top_level = {row.key for row in rows}
        for fact_id, memory_id in pairs:
            fact_key = lc.composition_key("fact", str(fact_id))
            memory_key = lc.composition_key("memory", str(memory_id))
            assert not (fact_key in top_level and memory_key in top_level), (
                f"{memory_key} is served beside {fact_key}, which it sources"
            )


# ─────────────── the fixpoint rule itself, by name ───────────────


def _descent(monkeypatch):
    """Record the nestable-fact set each round of the iteration was handed."""
    rounds: list[frozenset[str]] = []
    original = lc._group_under_fact

    def _recording(rows, support, nestable_facts):
        rounds.append(nestable_facts)
        return original(rows, support, nestable_facts)

    monkeypatch.setattr(lc, "_group_under_fact", _recording)
    return rounds


def test_the_page_is_the_settled_point_of_a_descending_iteration(monkeypatch):
    """The fixpoint rule, pinned so its failure names it.

    The fixture needs **more than one round**: with every fact nestable the
    page reaches ``F3``, which un-nests nothing; only once ``F4`` is known to
    be out does ``M2`` return to the top level, which pushes ``F3`` out in
    turn. A single-pass rule — group once against the facts that survive an
    ungrouped cut — would stop at the first round and serve a different page.

    Two things are asserted, and they are different claims: that the set handed
    to each round **strictly shrinks** (the termination argument), and that the
    round the page came from is a **fixed point** — every fact anything was
    nested under is a fact the page serves.
    """
    facts = [uuid4() for _ in range(4)]
    memories = [uuid4() for _ in range(2)]
    candidates = [
        lc.fact_candidate(_fact_row(fact_id), channel_rank=rank)
        for rank, fact_id in enumerate(facts, start=1)
    ]
    candidates += [
        lc.memory_candidate(_memory_row(memory_id), channel_rank=rank)
        for rank, memory_id in enumerate(memories, start=1)
    ]
    support = lc.support_map([(facts[3], memories[1])])

    rounds = _descent(monkeypatch)
    rows = lc.compose(candidates, fact_sources=support, limit=4).rows

    assert len(rounds) > 1, "the fixture settled in one round and proves nothing"
    for earlier, later in zip(rounds, rounds[1:]):
        assert later < earlier, f"{sorted(later)} does not strictly shrink {sorted(earlier)}"

    served_facts = {row.key for row in rows if row.id_kind == "fact"}
    nested_under = {
        nested.grouping["grouped_under"] for row in rows for nested in row.supported_by
    }
    assert nested_under <= {row.id for row in rows if row.id_kind == "fact"}
    assert rounds[-1] == served_facts


def test_a_step_that_stops_shrinking_raises_rather_than_spinning(monkeypatch):
    """Termination is enforced, not merely argued.

    The iteration terminates because restricting the nestable facts can only
    un-nest memories, so the surviving set can only shrink. That is a property
    of :func:`_group_under_fact`, and a later change to the nesting rule could
    break it — at which point the loop would have no bound at all. So the step
    checks its own monotonicity and raises.

    The injected pass nests exactly where the restriction forbids. That is not
    a plausible edit; it is the crudest available negation of the property the
    termination argument rests on, chosen because it falsifies that property
    directly rather than by luck. What this proves is that the check fires, not
    that every monotonicity-breaking edit is caught by it.
    """
    facts = [uuid4() for _ in range(4)]
    memories = [uuid4() for _ in range(2)]
    candidates = [
        lc.fact_candidate(_fact_row(fact_id), channel_rank=rank)
        for rank, fact_id in enumerate(facts, start=1)
    ]
    candidates += [
        lc.memory_candidate(_memory_row(memory_id), channel_rank=rank)
        for rank, memory_id in enumerate(memories, start=1)
    ]
    support = lc.support_map([(facts[3], memories[1])])

    original = lc._group_under_fact

    def _inverted(rows, support, nestable_facts):
        every = frozenset(r.key for r in rows if r.id_kind == "fact")
        return original(rows, support, every - nestable_facts)

    monkeypatch.setattr(lc, "_group_under_fact", _inverted)

    with pytest.raises(RuntimeError, match="stopped decreasing"):
        lc.compose(candidates, fact_sources=support, limit=4)


def test_the_iteration_terminates_on_an_adversarial_support_map():
    """Termination over inputs chosen to make the descent work, not one fixture.

    Every memory sources a fact far down the order, so the first round nests
    everything and the page is all facts; each later round un-nests another
    layer and pushes the reach back. The bounded loop raises rather than
    hanging if the descent fails to settle, so completing this sweep without a
    raise is the termination claim — checked over every budget, at sizes where
    the descent takes several rounds.
    """
    for size in range(1, 13):
        facts = [uuid4() for _ in range(size)]
        memories = [uuid4() for _ in range(size)]
        candidates = [
            lc.fact_candidate(_fact_row(fact_id), channel_rank=rank)
            for rank, fact_id in enumerate(facts, start=1)
        ]
        candidates += [
            lc.memory_candidate(_memory_row(memory_id), channel_rank=rank)
            for rank, memory_id in enumerate(memories, start=1)
        ]
        # Reversed pairing: the highest-ranked memory sources the lowest-ranked
        # fact, so un-nesting cascades from the tail of the order upwards.
        support = lc.support_map(zip(reversed(facts), memories))

        for limit in range(1, 2 * size + 1):
            result = lc.compose(candidates, fact_sources=support, limit=limit)
            assert len(result.rows) <= limit
            served = {row.key for row in result.rows}
            for row in result.rows:
                for nested in row.supported_by:
                    assert nested.grouping["grouped_under"] == row.id
            assert result.excluded_by_result_limit == len(candidates) - len(
                served | {n.key for r in result.rows for n in r.supported_by}
            )


# ─────────────── nothing else moved ───────────────


def test_no_budget_leaves_the_grouping_and_the_page_exactly_as_they_were():
    """``limit=None`` is the T2.55 path, unchanged: every fact may be nested under."""
    facts = [uuid4(), uuid4()]
    memories = [uuid4(), uuid4()]
    candidates = [
        lc.fact_candidate(_fact_row(fact_id), channel_rank=rank)
        for rank, fact_id in enumerate(facts, start=1)
    ]
    candidates += [
        lc.memory_candidate(_memory_row(memory_id), channel_rank=rank)
        for rank, memory_id in enumerate(memories, start=1)
    ]
    support = lc.support_map(zip(facts, memories))

    result = lc.compose(candidates, fact_sources=support)

    assert [row.id_kind for row in result.rows] == ["fact", "fact"]
    assert [n.id for row in result.rows for n in row.supported_by] == [
        str(memories[0]), str(memories[1]),
    ]
    assert result.excluded_by_result_limit == 0


def test_the_budget_cuts_an_ungrouped_composition_too():
    """The cut is the answer budget, not a side effect of the grouping pass.

    ``fact_sources=None`` says no provenance was looked up, so step 5 does not
    run — but the budget still binds, and the rows it drops are still counted.
    """
    _, _, candidates = _sweep_candidates(3, 3)

    result = lc.compose(candidates, limit=2)

    assert len(result.rows) == 2
    assert result.grouped is False
    assert result.excluded_by_result_limit == 4


# ─────────────── the count, at the wire ───────────────


@pytest.mark.asyncio
async def test_the_dropped_tail_is_counted_at_the_wire(session, monkeypatch):
    """R3 through the serialiser MCP's ``knowledge_search`` actually spends.

    A count that exists on the service object and not in the payload is the
    T2.46 shape: the service passes its own test and the caller is handed a
    page whose losses it cannot see. So this reads the number off
    :func:`knowledge_search_response`'s dump, and it checks the identity that
    makes the number meaningful — served rows plus nested rows plus the tally
    equals every row the composition ordered.
    """
    fact_id, (nested_memory,) = await _seed_fact_with_sources(session, memory_count=1)
    fact_rows = [_fact_row(uuid4()) for _ in range(3)] + [_fact_row(fact_id)]
    memory_rows = [_memory_row(uuid4()), _memory_row(nested_memory)]
    _stub_channels(monkeypatch, memory_rows, fact_rows)

    result = await lc.LayerCompositionService(_FakeLLM(), session).search(
        "q", project=PROJECT, limit=4,
    )
    payload = knowledge_search_response(result).model_dump()

    served = len(payload["rows"]) + sum(
        len(row["supported_by"]) for row in payload["rows"]
    )
    assert payload["envelope"]["excluded"]["by_result_limit"] == 2
    assert served + payload["envelope"]["excluded"]["by_result_limit"] == len(
        fact_rows
    ) + len(memory_rows)


@pytest.mark.asyncio
async def test_the_budget_tally_is_reported_even_at_zero(session, monkeypatch):
    """A suppressed zero reads as "no check ran" — the same trap as the conflict tally."""
    _stub_channels(monkeypatch, [_memory_row(uuid4())], [_fact_row(uuid4())])

    result = await lc.LayerCompositionService(_FakeLLM(), session).search(
        "q", project=PROJECT, limit=20,
    )

    assert result.envelope.excluded["by_result_limit"] == 0

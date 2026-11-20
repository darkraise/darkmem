"""Doc 07 §5 step 5 — grouping under the fact, and the no-triple-count rule.

Three memories backing one fact are one grounded unit, not three ranked rows.
The properties under test are the ones whose failure is silent: a count that
still sees three, a collapse that only one output shape performs, a rerank that
never saw the row it was supposed to score, and a grouping map keyed on a bare
id in a keyspace where a fact and a memory can share a UUID.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import event

from app.models.memory import Memory
from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import facts_channel, hybrid_search
from app.services import layer_composition as lc
from app.services.fact_provenance import memory_source_ref

PROJECT = "t2-55-result-grouping"


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


def _fact_row(fact_id, *, verification_status="corroborated", **extra) -> dict:
    row = {
        "fact_id": fact_id,
        "id": fact_id,
        "fact": "a fact",
        "subject_name": "postgres",
        "rel_type": "DEPLOYED_ON",
        "object_name": "homelab",
        "project": PROJECT,
        "verification_status": verification_status,
        "review_state": None,
        "rrf_score": 0.1,
    }
    row.update(extra)
    return row


def _one_fact_three_memories():
    """One fact, three memories that source it, and the support map linking them."""
    fact_id = uuid4()
    memory_ids = [uuid4() for _ in range(3)]
    candidates = [lc.fact_candidate(_fact_row(fact_id), channel_rank=1)]
    candidates += [
        lc.memory_candidate(_memory_row(memory_id), channel_rank=rank)
        for rank, memory_id in enumerate(memory_ids, start=1)
    ]
    support = lc.support_map((fact_id, memory_id) for memory_id in memory_ids)
    return fact_id, memory_ids, candidates, support


# ─────────────── the collapse itself: three memories, one result ───────────────


def test_three_memories_supporting_one_fact_are_one_grouped_result():
    fact_id, memory_ids, candidates, support = _one_fact_three_memories()

    rows = lc.compose(candidates, fact_sources=support).rows

    assert len(rows) == 1
    group = rows[0]
    assert group.id_kind == "fact"
    assert group.id == str(fact_id)
    assert {nested.id for nested in group.supported_by} == {
        str(memory_id) for memory_id in memory_ids
    }


def test_the_group_names_its_evidence_without_counting_it_again():
    """Done-when 2, as a counting claim rather than a labelling one.

    The evidence is named — each nested row carries its own id and its
    ``supports fact F`` relation — while every count taken off the result is
    one: one top-level row, and no nested id reachable as a sibling of the
    fact it sits under.
    """
    fact_id, memory_ids, candidates, support = _one_fact_three_memories()

    result = lc.compose(candidates, fact_sources=support)

    assert len(result.rows) == 1
    top_level_ids = {row.id for row in result.rows}
    for memory_id in memory_ids:
        assert str(memory_id) not in top_level_ids

    group = result.rows[0]
    for nested in group.supported_by:
        assert nested.grouping == {
            "grouped_under": str(fact_id),
            "relation": lc.SUPPORTS_FACT_RELATION,
        }


def test_the_group_score_is_the_facts_own_and_nothing_is_folded_in():
    """R2. Evidence does not re-enter the ranking through the row it nests under.

    A sum, an average or any other fold would be the triple count moved from
    the row list into the arithmetic, where no count of results can see it.
    """
    _, _, candidates, support = _one_fact_three_memories()

    ungrouped = {row.key: row for row in lc.compose(candidates).rows}
    group = lc.compose(candidates, fact_sources=support).rows[0]
    alone = ungrouped[group.key]

    assert group.weighted_score == alone.weighted_score
    assert group.cross_layer_rrf == alone.cross_layer_rrf
    assert group.rank_fusion_factor == alone.rank_fusion_factor
    assert group.band == alone.band
    assert group.tier == alone.tier
    assert group.channel_rank == alone.channel_rank


def test_a_nested_row_is_the_row_it_would_have_been_at_the_top_level():
    """Doc 07 §5: a nested memory carries its own rrf/rerank scores in the trace.

    Asserted as identity rather than field by field, so a later field added to
    ``ComposedRow`` is covered without anyone remembering to extend this list.
    """
    _, _, candidates, support = _one_fact_three_memories()

    ungrouped = {row.key: row for row in lc.compose(candidates).rows}
    group = lc.compose(candidates, fact_sources=support).rows[0]

    for nested in group.supported_by:
        alone = ungrouped[nested.key]
        assert nested == replace(
            alone,
            grouping=nested.grouping,
            supported_by=nested.supported_by,
        )
        assert nested.supported_by == ()


def test_the_answer_budget_counts_a_group_as_one():
    """Two groups of two under a limit of two are two results, not six."""
    facts = [uuid4(), uuid4()]
    memories = [(uuid4(), uuid4()), (uuid4(), uuid4())]
    candidates = [
        lc.fact_candidate(_fact_row(fact_id), channel_rank=rank)
        for rank, fact_id in enumerate(facts, start=1)
    ]
    rank = 1
    pairs = []
    for fact_id, group in zip(facts, memories):
        for memory_id in group:
            candidates.append(
                lc.memory_candidate(_memory_row(memory_id), channel_rank=rank)
            )
            pairs.append((fact_id, memory_id))
            rank += 1

    rows = lc.compose(candidates, fact_sources=lc.support_map(pairs)).rows

    assert len(rows) == 2
    assert sum(len(row.supported_by) for row in rows) == 4
    assert [row.id_kind for row in rows[:2]] == ["fact", "fact"]


# ─────────────── the key's presence is the evidence the pass ran ───────────────


def test_no_provenance_lookup_emits_no_grouping_key():
    _, _, candidates, _ = _one_fact_three_memories()

    result = lc.compose(candidates)

    assert result.grouped is False
    assert len(result.rows) == 4
    for row in result.rows:
        assert row.grouping is None
        assert row.supported_by == ()


def test_an_empty_lookup_is_a_lookup_and_says_so():
    """A lookup that found nothing must not read like a lookup that never ran."""
    _, _, candidates, _ = _one_fact_three_memories()

    result = lc.compose(candidates, fact_sources={})

    assert result.grouped is True
    assert len(result.rows) == 4
    for row in result.rows:
        assert row.grouping == {"grouped_under": None, "relation": None}


def test_the_relation_string_is_doc_12s_literal():
    assert lc.SUPPORTS_FACT_RELATION == "supports fact F"


def test_the_two_grouping_fields_move_together():
    """Never a relation with no object, never an object with no relation."""
    fact_id, _, candidates, support = _one_fact_three_memories()

    rows = lc.compose(candidates, fact_sources=support).rows
    every = list(rows) + [nested for row in rows for nested in row.supported_by]

    for row in every:
        named = row.grouping["grouped_under"] is not None
        assert (row.grouping["relation"] is not None) is named


# ─────────────── scoping: what the pass may not remove from view ───────────────


def test_a_memory_whose_fact_is_absent_stays_a_top_level_row():
    """R4. Nesting under a fact the caller was not handed would hide the row."""
    absent_fact = uuid4()
    memory_id = uuid4()
    candidates = [lc.memory_candidate(_memory_row(memory_id), channel_rank=1)]
    support = lc.support_map([(absent_fact, memory_id)])

    rows = lc.compose(candidates, fact_sources=support).rows

    assert [row.id for row in rows] == [str(memory_id)]
    assert rows[0].grouping == {"grouped_under": None, "relation": None}


def test_a_dangling_source_ref_changes_nothing():
    """``fact_sources.source_ref`` has no FK, so it may name a deleted memory.

    The decision is that such a ref is inert rather than special-cased: it can
    neither nest a row nor be counted as evidence, because the pass only ever
    intersects provenance with rows it already holds.
    """
    fact_id = uuid4()
    live_memory = uuid4()
    deleted_memory = uuid4()
    candidates = [
        lc.fact_candidate(_fact_row(fact_id), channel_rank=1),
        lc.memory_candidate(_memory_row(live_memory), channel_rank=1),
    ]
    support = lc.support_map([(fact_id, live_memory), (fact_id, deleted_memory)])

    rows = lc.compose(candidates, fact_sources=support).rows

    assert len(rows) == 1
    assert [nested.id for nested in rows[0].supported_by] == [str(live_memory)]


def test_a_memory_sourcing_two_returned_facts_nests_once():
    """Splitting it across both facts would restore the duplication."""
    first, second = uuid4(), uuid4()
    memory_id = uuid4()
    candidates = [
        lc.fact_candidate(_fact_row(first), channel_rank=1),
        lc.fact_candidate(_fact_row(second), channel_rank=2),
        lc.memory_candidate(_memory_row(memory_id), channel_rank=1),
    ]
    support = lc.support_map([(first, memory_id), (second, memory_id)])

    rows = lc.compose(candidates, fact_sources=support).rows

    assert len(rows) == 2
    nested = [(row.id, [n.id for n in row.supported_by]) for row in rows]
    assert sum(len(ids) for _, ids in nested) == 1
    # The higher-ranked fact takes it: the reader meets the evidence at the
    # first place the claim appears.
    holder = next(row for row in rows if row.supported_by)
    assert holder.id == str(first)


def _article_row(article_id) -> dict:
    return {
        "article_id": article_id,
        "title": "an article",
        "project": PROJECT,
        "verification_status": "candidate",
        "review_state": None,
    }


def test_an_article_is_never_nested_even_when_the_map_says_to():
    """Only an L0 row may be nested, asserted against a map that asks otherwise.

    The map here is built **by hand**, not through ``support_map``, and that is
    the point: ``support_map`` can only mint ``memory:`` on the value side and
    ``add_source`` refuses a derived ``source_kind`` outright, so both upstream
    defences are unreachable from a test that goes through them — it would pass
    with the rule deleted. A hand-built article entry is the construction that
    would nest an article if the composition let it, so this fails the moment
    the id_kind check in ``_group_under_fact`` is removed.
    """
    fact_id, article_id, memory_id = uuid4(), uuid4(), uuid4()
    candidates = [
        lc.fact_candidate(_fact_row(fact_id), channel_rank=1),
        lc.article_candidate(_article_row(article_id), channel_rank=1),
        lc.memory_candidate(_memory_row(memory_id), channel_rank=1),
    ]
    support = {
        f"fact:{fact_id}": frozenset(
            {f"article:{article_id}", f"memory:{memory_id}"}
        )
    }

    rows = lc.compose(candidates, fact_sources=support).rows

    # The article survives at the top level; only the memory is collapsed.
    assert {row.id for row in rows} == {str(fact_id), str(article_id)}
    by_kind = {row.id_kind: row for row in rows}
    assert by_kind["article"].grouping == {"grouped_under": None, "relation": None}
    assert by_kind["article"].supported_by == ()
    assert [n.id for n in by_kind["fact"].supported_by] == [str(memory_id)]


def test_support_map_cannot_mint_an_article_on_the_value_side():
    """The upstream half of the same rule: the minter has one spelling."""
    fact_id, article_id = uuid4(), uuid4()

    mapping = lc.support_map([(fact_id, article_id)])

    assert mapping == {f"fact:{fact_id}": frozenset({f"memory:{article_id}"})}
    assert not any(
        member.startswith("article:")
        for members in mapping.values()
        for member in members
    )


# ─────────────── the keyspace: a fact and a memory may share a UUID ───────────────


def test_support_map_namespaces_both_sides():
    fact_id, memory_id = uuid4(), uuid4()

    mapping = lc.support_map([(fact_id, memory_id)])

    assert mapping == {f"fact:{fact_id}": frozenset({f"memory:{memory_id}"})}


def test_a_uuid_and_its_string_mint_one_support_entry():
    """Invariant 9 normalised at the one place the map is minted."""
    fact_id, memory_id = uuid4(), uuid4()

    mapping = lc.support_map([(fact_id, memory_id), (str(fact_id), str(memory_id))])

    assert len(mapping) == 1
    assert len(next(iter(mapping.values()))) == 1


def test_a_fact_and_a_memory_sharing_a_uuid_do_not_collide():
    """The drill target for keying the grouping map on a bare id.

    ``shared`` names a fact **and** an unrelated memory. Keyed on bare ids the
    two are one entry, so the unrelated memory either swallows the group or
    vanishes from the output; keyed on composition keys they are two objects in
    two spaces and only the real source nests.
    """
    shared = uuid4()
    real_source = uuid4()
    candidates = [
        lc.fact_candidate(_fact_row(shared), channel_rank=1),
        lc.memory_candidate(_memory_row(shared), channel_rank=1),
        lc.memory_candidate(_memory_row(real_source), channel_rank=2),
    ]
    support = lc.support_map([(shared, real_source)])

    rows = lc.compose(candidates, fact_sources=support).rows

    assert len(rows) == 2
    by_kind = {row.id_kind: row for row in rows}
    assert set(by_kind) == {"fact", "memory"}
    # The look-alike memory is served in its own right and holds no evidence.
    assert by_kind["memory"].id == str(shared)
    assert by_kind["memory"].supported_by == ()
    assert [n.id for n in by_kind["fact"].supported_by] == [str(real_source)]


# ─────────────── grouping survives fusion: it is not a renderer ───────────────
#
# T2.56 owns the two output shapes. What is asserted here is the property that
# makes both of them correct without either of them knowing about grouping: the
# collapse has already happened in ``compose()``, so a shape is free to reorder
# or section the list it is handed and can neither undo nor have to repeat it.


def _fused(result) -> list:
    """The fused shape: the one composed order, unchanged."""
    return list(result.rows)


def _sectioned(result) -> dict:
    """The sectioned shape: a pure regroup of the same list by layer."""
    sections: dict[str, list] = {}
    for row in result.rows:
        sections.setdefault(row.layer, []).append(row)
    return sections


def test_grouping_holds_in_the_fused_shape():
    fact_id, memory_ids, candidates, support = _one_fact_three_memories()

    fused = _fused(lc.compose(candidates, fact_sources=support))

    assert len(fused) == 1
    assert fused[0].id == str(fact_id)
    assert len(fused[0].supported_by) == 3


def test_grouping_holds_in_the_sectioned_shape():
    fact_id, memory_ids, candidates, support = _one_fact_three_memories()

    sections = _sectioned(lc.compose(candidates, fact_sources=support))

    # No memory section at all: every L0 row here is evidence for the one fact,
    # so a Memory section listing them would be the triple count restored by
    # the renderer that was supposed to be innocent of grouping.
    assert set(sections) == {"L2"}
    assert len(sections["L2"]) == 1
    assert len(sections["L2"][0].supported_by) == 3


def test_both_shapes_read_the_same_grouped_list():
    _, _, candidates, support = _one_fact_three_memories()
    result = lc.compose(candidates, fact_sources=support)

    fused = _fused(result)
    sectioned = _sectioned(result)

    assert len(fused) == sum(len(rows) for rows in sectioned.values())
    assert [row.key for row in fused] == [
        row.key for rows in sectioned.values() for row in rows
    ]


def test_the_pure_composition_is_what_groups():
    """R1. No session, no service, no renderer — grouping is in ``compose()``."""
    _, _, candidates, support = _one_fact_three_memories()

    result = lc.compose(candidates, fact_sources=support)

    assert result.grouped is True
    assert len(result.rows) == 1


# ─────────────── the order: rerank first, group last (doc 07 §11) ───────────────


class _FakeLLM:
    async def embed(self, query: str):
        return [0.0], "fp"


def _stub_channels(monkeypatch, memory_rows, fact_rows):
    async def _memory(self, *args, **kwargs):
        return hybrid_search.ChannelTrace(results=list(memory_rows))

    async def _facts(self, *args, **kwargs):
        return facts_channel.FactChannelTrace(results=list(fact_rows))

    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _memory)
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _facts)


def test_a_nested_row_carries_the_band_the_rerank_gave_it():
    """The verdict on the nested row survives the collapse that hides the row."""
    fact_id, memory_id = uuid4(), uuid4()
    memory = lc.memory_candidate(_memory_row(memory_id), channel_rank=1)
    fact = lc.fact_candidate(_fact_row(fact_id), channel_rank=1)

    result = lc.compose(
        [memory, fact],
        rerank_scores={memory.key: 9.0, fact.key: 2.0},
        fact_sources=lc.support_map([(fact_id, memory_id)]),
    )

    group = result.rows[0]
    assert group.band == 2
    assert group.supported_by[0].band == 1


# ─────────────── the provenance read: one bounded lookup, real rows ───────────────


class _QueryCounter:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def __call__(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    @property
    def selects(self) -> list[str]:
        return [
            statement
            for statement in self.statements
            if statement.lstrip().upper().startswith(("SELECT", "WITH"))
        ]


async def _seed_fact_with_sources(session, *, memory_count: int):
    """One triple, ``memory_count`` real memories, and real provenance rows."""
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


@pytest.mark.asyncio
async def test_the_provenance_read_is_one_query_for_the_whole_result_set(session):
    """R5. A per-fact call would put a round trip behind every returned fact."""
    from tests.conftest import test_engine

    first_fact, _ = await _seed_fact_with_sources(session, memory_count=3)
    second_fact, _ = await _seed_fact_with_sources(session, memory_count=2)

    counter = _QueryCounter()
    target = test_engine.sync_engine
    event.listen(target, "before_cursor_execute", counter)
    try:
        refs = await FactSourceRepository(session).memory_refs_for_facts(
            [first_fact, second_fact]
        )
    finally:
        event.remove(target, "before_cursor_execute", counter)

    assert len(counter.selects) == 1, counter.selects
    assert len(refs[str(first_fact)]) == 3
    assert len(refs[str(second_fact)]) == 2


@pytest.mark.asyncio
async def test_the_provenance_read_asks_nothing_for_an_empty_set(session):
    from tests.conftest import test_engine

    counter = _QueryCounter()
    target = test_engine.sync_engine
    event.listen(target, "before_cursor_execute", counter)
    try:
        assert await FactSourceRepository(session).memory_refs_for_facts([]) == {}
    finally:
        event.remove(target, "before_cursor_execute", counter)

    assert counter.selects == []


@pytest.mark.asyncio
async def test_the_provenance_read_ignores_a_non_memory_source(session):
    """``source_ref`` carries no type discriminator, so the kind filter is it."""
    fact_id, memory_ids = await _seed_fact_with_sources(session, memory_count=1)
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind="human",
        source_ref="a-reviewer",
        origin_key="reviewer-1",
    )
    await session.commit()

    refs = await FactSourceRepository(session).memory_refs_for_facts([fact_id])

    assert refs[str(fact_id)] == (memory_source_ref(memory_ids[0]),)


@pytest.mark.asyncio
async def test_three_real_memories_group_under_their_real_fact(session, monkeypatch):
    """Done-when 1 through the service, over rows ``fact_sources`` actually holds."""
    fact_id, memory_ids = await _seed_fact_with_sources(session, memory_count=3)
    _stub_channels(
        monkeypatch,
        [_memory_row(memory_id) for memory_id in memory_ids],
        [_fact_row(fact_id)],
    )

    result = await lc.LayerCompositionService(_FakeLLM(), session).search(
        "postgres homelab", project=PROJECT,
    )

    assert len(result.rows) == 1
    group = result.rows[0]
    assert group.id == str(fact_id)
    assert {n.id for n in group.supported_by} == {str(m) for m in memory_ids}
    assert all(
        n.grouping["relation"] == lc.SUPPORTS_FACT_RELATION for n in group.supported_by
    )


@pytest.mark.asyncio
async def test_the_collapse_still_holds_where_the_answer_budget_binds(session, monkeypatch):
    """The tripwire this test used to be, fired — and what replaced it.

    It previously recorded the opposite outcome: ``search()`` sliced
    ``rows[:limit]`` after grouping, so a memory nested under a fact that fell
    past the cut left the result with that fact even though it had ranked above
    the cut alone. That was ruled a gap in the plan rather than in this lane,
    and T2.70 closed it by scoping nesting to the facts the budget reaches. The
    notice worked as intended: the person who moved the slice found out here.

    What stays this lane's claim is the collapse itself under a budget — a
    group is one row against the budget, and its evidence is nested rather than
    ranked beside it. The budget interaction now belongs to
    ``test_grouping_cut.py``, which owns the fixpoint and the tally; this
    asserts only that the collapse survives a limit that binds.

    The ordering it relies on: bands run 1..4 over the fact channel and 1..2
    over the memory channel, and the sort is ``(band, -tier, key)``, so a
    corroborated fact precedes a memory of the same band.
    """
    grouped_fact, (nested_memory,) = await _seed_fact_with_sources(session, memory_count=1)
    # The filler facts need no rows of their own: the provenance lookup is
    # keyed by fact id and an id it does not find simply sources nothing.
    filler_facts = [uuid4(), uuid4(), uuid4()]
    lone_memory = uuid4()

    _stub_channels(
        monkeypatch,
        [_memory_row(lone_memory), _memory_row(nested_memory)],
        [_fact_row(grouped_fact)] + [_fact_row(fact_id) for fact_id in filler_facts],
    )
    service = lc.LayerCompositionService(_FakeLLM(), session)

    cut = await service.search("q", project=PROJECT, limit=4)

    # The sourced fact is rank 1, so the budget reaches it and the memory nests
    # under it: one row for the claim, its evidence named inside.
    group = cut.rows[0]
    assert group.id == str(grouped_fact)
    assert [n.id for n in group.supported_by] == [str(nested_memory)]
    assert str(nested_memory) not in {row.id for row in cut.rows}
    assert len(cut.rows) == 4


@pytest.mark.asyncio
async def test_a_memory_with_no_provenance_is_served_in_its_own_right(session, monkeypatch):
    """Cold start's floor: nothing is nested that nothing asserts a link to."""
    fact_id, memory_ids = await _seed_fact_with_sources(session, memory_count=1)
    unrelated = uuid4()
    _stub_channels(
        monkeypatch,
        [_memory_row(memory_ids[0]), _memory_row(unrelated)],
        [_fact_row(fact_id)],
    )

    result = await lc.LayerCompositionService(_FakeLLM(), session).search(
        "postgres homelab", project=PROJECT,
    )

    assert len(result.rows) == 2
    by_kind = {row.id_kind: row for row in result.rows}
    assert by_kind["memory"].id == str(unrelated)
    assert by_kind["memory"].grouping == {"grouped_under": None, "relation": None}
    assert [n.id for n in by_kind["fact"].supported_by] == [str(memory_ids[0])]

"""Doc 07 §5's composition — the keyspace, the ordering, the labels (T2.43)."""

from __future__ import annotations

import ast
import json
import uuid as uuid_module
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import facts_channel, hybrid_search
from app.services import layer_composition as lc
from app.services import rank_fusion
from app.services.embedder_registry import child_table
from app.services.events import record_event
from app.services.reranker import RerankerService
from app.services.verified_evidence import latest_verified_evidence
from tests._reachability_scan import ReachabilityRules, find_forbidden_reach

PROJECT = "t2-43-layer-composition"


def _memory_row(memory_id, **extra) -> dict:
    row = {
        "memory_id": memory_id,
        "payload": {"content": "a memory"},
        "project": "default",
        "status": "active",
        "rrf_score": 0.1,
    }
    row.update(extra)
    return row


def _fact_row(fact_id, *, verification_status="candidate", **extra) -> dict:
    row = {
        "fact_id": fact_id,
        "id": fact_id,
        "fact": "a fact",
        "subject_name": "postgres",
        "rel_type": "DEPLOYED_ON",
        "object_name": "homelab",
        "project": "default",
        "verification_status": verification_status,
        "review_state": None,
        "rrf_score": 0.1,
    }
    row.update(extra)
    return row


def _article_row(article_id, *, verification_status="candidate", **extra) -> dict:
    row = {
        "article_id": article_id,
        "title": "an article",
        "project": "default",
        "verification_status": verification_status,
        "review_state": None,
        "rrf_score": 0.1,
    }
    row.update(extra)
    return row


# ───────────────────────── the keyspace (D1) ─────────────────────────


def test_a_fact_and_a_memory_sharing_a_uuid_stay_two_rows():
    shared = uuid4()
    memory = lc.memory_candidate(_memory_row(shared), channel_rank=1)
    fact = lc.fact_candidate(_fact_row(shared), channel_rank=1)

    assert memory.key != fact.key
    assert memory.key == f"memory:{shared}"
    assert fact.key == f"fact:{shared}"
    assert memory.layer == "L0"
    assert fact.layer == "L2"


def test_a_uuid_and_its_string_are_one_row():
    raw = uuid4()
    as_uuid = lc.memory_candidate(_memory_row(raw), channel_rank=1)
    as_str = lc.memory_candidate(_memory_row(str(raw)), channel_rank=2)

    assert as_uuid.key == as_str.key
    assert as_uuid.id == str(raw)


def test_the_wire_id_is_the_bare_id_and_agrees_with_the_key():
    from uuid import UUID

    raw = uuid4()
    for candidate in (
        lc.memory_candidate(_memory_row(raw), channel_rank=1),
        lc.fact_candidate(_fact_row(raw), channel_rank=1),
        lc.article_candidate(_article_row(raw), channel_rank=1),
    ):
        assert candidate.key == f"{candidate.id_kind}:{candidate.id}"
        assert UUID(candidate.id) == raw


def test_composition_key_refuses_an_unnormalised_id():
    with pytest.raises(TypeError):
        lc.composition_key("memory", uuid4())


def test_composition_key_refuses_a_foreign_space():
    with pytest.raises(ValueError):
        lc.composition_key("code", str(uuid4()))


def test_a_candidate_cannot_claim_a_foreign_layer():
    with pytest.raises(TypeError):
        lc.LayerCandidate(
            id=str(uuid4()), id_kind="fact", layer="L0", channel_rank=1, row={},
        )


# ─────────────── the dispute, served with both sides (D8) ───────────────


def _counterpart_block(**overrides) -> dict:
    block = {
        "counterpart_id": str(uuid4()),
        "counterpart_subject": "postgres",
        "counterpart_rel_type": "DEPLOYED_ON",
        "counterpart_object": "fly.io",
        "rule": "functional_object_conflict",
        "witness_origin": "origin-7",
        "enumeration": "first_finding",
    }
    block.update(overrides)
    return block


def test_an_undisputed_fact_has_no_dispute_label():
    row = _fact_row(uuid4(), verification_status="corroborated")
    assert lc.dispute_label(row, None) is None


def test_both_sides_are_rendered_in_the_same_shape():
    block = _counterpart_block()
    row = _fact_row(uuid4(), verification_status="disputed", review_state="open")
    label = lc.dispute_label(row, {"payload": {"contradiction": block}})

    assert set(label["claim"]) == set(label["counterpart"])
    assert set(label["claim"]) == {"subject", "rel_type", "object", "id"}
    assert label["claim"]["subject"] == "postgres"
    assert label["claim"]["object"] == "homelab"
    assert label["counterpart"]["object"] == "fly.io"
    assert label["counterpart"]["id"] == block["counterpart_id"]
    assert label["rule"] == "functional_object_conflict"
    assert label["witness_origin"] == "origin-7"


def test_an_absent_block_is_not_an_absent_dispute():
    row = _fact_row(uuid4(), verification_status="disputed", review_state="open")
    label = lc.dispute_label(row, {"payload": {"outcome": "dispute"}})

    assert label is not None
    assert label["counterpart"] is None
    assert label["counterpart_absent"] == lc.COUNTERPART_ABSENT_NO_FINDING
    assert lc.dispute_label(_fact_row(uuid4()), None) is None


def test_the_dispute_label_carries_no_count():
    block = _counterpart_block()
    row = _fact_row(uuid4(), verification_status="disputed", review_state="open")
    label = lc.dispute_label(row, {"payload": {"contradiction": block}})

    assert label["enumeration"] == "first_finding"
    for banned in ("count", "total", "contradiction_count", "contradiction_total"):
        assert banned not in label


@pytest.mark.asyncio
async def test_the_counterpart_comes_from_the_latest_verified_event(session):
    fact_id = uuid4()
    # The stale event is written *second* so it holds the higher identity
    # column. Ordering by identity alone would therefore serve it — which is
    # what makes the created_at term in the reader's ORDER BY breakable.
    await record_event(
        session,
        event_type="verified",
        object_type="fact",
        object_id=fact_id,
        project=PROJECT,
        payload={"contradiction": _counterpart_block(counterpart_object="fresh")},
    )
    await session.execute(
        text(
            "INSERT INTO events (created_at, event_type, object_type, object_id, "
            "project, payload) VALUES (now() - interval '1 minute', 'verified', "
            "'fact', CAST(:id AS uuid), :project, CAST(:payload AS jsonb))"
        ),
        {
            "id": str(fact_id),
            "project": PROJECT,
            "payload": json.dumps(
                {"contradiction": _counterpart_block(counterpart_object="stale")}
            ),
        },
    )
    await session.commit()

    evidence = await latest_verified_evidence(session, [str(fact_id)])
    row = _fact_row(fact_id, verification_status="disputed", review_state="open")
    label = lc.dispute_label(row, evidence.get(str(fact_id)))

    assert label["counterpart"]["object"] == "fresh"


# ─────────────── the tier table and the ordering rule (D4) ───────────────


def test_an_unknown_verification_status_raises():
    candidate = lc.fact_candidate(
        _fact_row(uuid4(), verification_status="probably_true"), channel_rank=1,
    )
    with pytest.raises(ValueError):
        lc.compose([candidate])


def test_verified_sorts_above_labelled_candidate_in_the_same_band():
    """The ordering rule's flagship guard.

    The **article** is load-bearing and must not be simplified to a memory or
    a second fact. ``key`` is the final tie-break and sorts alphabetically,
    where ``"article:…" < "fact:…" < "memory:…"``. That accidentally *agrees*
    with tier order in the obvious fixtures (a fact above a memory, a high
    article above a low fact), so a test built from those passes with the
    ``-tier`` term deleted and the guard gone. A ``confirmed`` fact against a
    ``candidate`` article in the same band is the one cross-channel pairing
    where the tie-break and the tier disagree, which is what makes deleting
    the tier term observable here.
    """
    fact = lc.fact_candidate(
        _fact_row(uuid4(), verification_status="confirmed"), channel_rank=1,
    )
    article = lc.article_candidate(
        _article_row(uuid4(), verification_status="candidate"), channel_rank=1,
    )

    for order in ([fact, article], [article, fact]):
        rows = lc.compose(order).rows
        assert [r.band for r in rows] == [1, 1]
        assert rows[0].id_kind == "fact"
        assert rows[1].id_kind == "article"
        # The tie-break alone would have ordered them the other way round.
        assert sorted(r.key for r in rows)[0].startswith("article:")


def test_no_row_is_dropped_for_its_verification_status():
    candidates = [
        lc.fact_candidate(_fact_row(uuid4(), verification_status="candidate"), channel_rank=i)
        for i in range(1, 4)
    ]
    candidates.append(lc.memory_candidate(_memory_row(uuid4()), channel_rank=1))

    result = lc.compose(candidates)

    assert len(result.rows) == 4
    assert {r.verification_status for r in result.rows} == {"candidate", None}
    assert all(r.labels["project"] == "default" for r in result.rows)


def test_under_sourced_keeps_the_corroborated_tier():
    fact = lc.fact_candidate(
        _fact_row(uuid4(), verification_status="corroborated", review_state="open"),
        channel_rank=1,
    )
    article = lc.article_candidate(
        _article_row(uuid4(), verification_status="candidate"), channel_rank=1,
    )

    rows = lc.compose([fact, article]).rows
    by_kind = {r.id_kind: r for r in rows}

    assert by_kind["fact"].tier == lc.TIER_BY_VERIFICATION_STATUS["corroborated"]
    assert by_kind["fact"].labels["review_state"] == "open"
    assert rows[0].id_kind == "fact"


def test_the_order_is_total_and_reproducible():
    candidates = [
        lc.fact_candidate(_fact_row(uuid4(), verification_status="confirmed"), channel_rank=1),
        lc.memory_candidate(_memory_row(uuid4()), channel_rank=1),
        lc.article_candidate(_article_row(uuid4()), channel_rank=1),
    ]
    first = [r.key for r in lc.compose(candidates).rows]
    second = [r.key for r in lc.compose(list(reversed(candidates))).rows]
    assert first == second


def test_a_memory_lifecycle_status_never_reaches_the_tier_lookup():
    """``scope_labels`` stamps ``status`` on every hybrid row, so wiring the
    tier lookup to it is one keyword away and would raise on every memory in
    the corpus."""
    row = _memory_row(uuid4(), status="active")
    composed = lc.compose([lc.memory_candidate(row, channel_rank=1)]).rows[0]

    assert composed.tier == lc.MEMORY_TIER
    assert composed.labels["status"] == "active"

    with pytest.raises(ValueError):
        lc.tier_for("active")


# ─────────────── the context partition, keyed cross-layer (D6) ───────────────


def _declared(**axes) -> rank_fusion.DeclaredContext:
    return rank_fusion.DeclaredContext(axes)


def test_a_context_conflict_is_excluded_and_counted():
    kept = lc.fact_candidate(
        _fact_row(uuid4(), applies_when={"env": "prod"}), channel_rank=1,
    )
    conflicting = lc.fact_candidate(
        _fact_row(uuid4(), applies_when={"env": "staging"}), channel_rank=2,
    )

    result = lc.compose([kept, conflicting], declared_context=_declared(env="prod"))

    assert [r.key for r in result.rows] == [kept.key]
    assert result.excluded_by_context_conflict == 1


def test_the_conflict_tally_is_reported_even_at_zero():
    result = lc.compose([lc.fact_candidate(_fact_row(uuid4()), channel_rank=1)])
    assert result.excluded_by_context_conflict == 0


def test_a_fact_and_a_memory_sharing_a_uuid_get_their_own_contexts():
    shared = uuid4()
    memory = lc.memory_candidate(
        _memory_row(shared, applies_when={"env": "prod"}), channel_rank=1,
    )
    fact = lc.fact_candidate(
        _fact_row(shared, applies_when={"env": "staging"}), channel_rank=1,
    )

    result = lc.compose([memory, fact], declared_context=_declared(env="prod"))

    assert result.excluded_by_context_conflict == 1
    assert [r.key for r in result.rows] == [memory.key]
    assert result.rows[0].context.match is rank_fusion.ContextMatch.MATCHED


def test_the_boost_is_applied_once():
    weights = {"w_context_boost": 4.0}
    matched = lc.fact_candidate(
        _fact_row(uuid4(), applies_when={"env": "prod"}), channel_rank=1,
    )

    row = lc.compose(
        [matched], weights=weights, declared_context=_declared(env="prod"),
    ).rows[0]

    base = lc.CHANNEL_LIST_WEIGHTS["fact"] * lc.cross_layer_rrf(1)
    boost = row.context.boost
    assert boost == 5.0
    assert row.weighted_score == pytest.approx(base * row.rank_fusion_factor * boost)
    assert row.weighted_score != pytest.approx(base * row.rank_fusion_factor * boost * boost)


# ─────────── the band: what the rerank and the multipliers move (D3, D5) ───────────


def _memory_channel(n, *, importance=None):
    out = []
    for rank in range(1, n + 1):
        extra = {}
        if importance is not None:
            extra["importance"] = importance(rank)
        out.append(lc.memory_candidate(_memory_row(uuid4(), **extra), channel_rank=rank))
    return out


def test_the_reranker_orders_the_bands_and_the_tier_orders_within_one():
    leader = lc.memory_candidate(_memory_row(uuid4()), channel_rank=1)
    fact = lc.fact_candidate(
        _fact_row(uuid4(), verification_status="confirmed"), channel_rank=1,
    )
    article = lc.article_candidate(
        _article_row(uuid4(), verification_status="candidate"), channel_rank=1,
    )
    scores = {leader.key: 0.9, fact.key: 0.8, article.key: 0.8}

    result = lc.compose([leader, fact, article], rerank_scores=scores)
    by_key = {r.key: r for r in result.rows}

    assert result.reranked is True
    assert by_key[leader.key].band == 1
    assert by_key[fact.key].band == 2
    assert by_key[article.key].band == 2
    assert [r.key for r in result.rows] == [leader.key, fact.key, article.key]


def test_an_unscored_row_is_not_a_row_scored_zero():
    rated_zero = lc.fact_candidate(
        _fact_row(uuid4(), verification_status="candidate"), channel_rank=1,
    )
    never_seen = lc.fact_candidate(
        _fact_row(uuid4(), verification_status="confirmed"), channel_rank=2,
    )

    result = lc.compose(
        [rated_zero, never_seen], rerank_scores={rated_zero.key: 0.0},
    )
    by_key = {r.key: r for r in result.rows}

    assert by_key[rated_zero.key].band < by_key[never_seen.key].band
    # The unscored row outranks on tier and still loses: the band it is in is
    # strictly lower, so "never asked" cannot be read as a verdict.
    assert result.rows[0].key == rated_zero.key


def test_one_response_is_ordered_under_one_signal():
    scored = _memory_channel(2)
    tail = [lc.memory_candidate(_memory_row(uuid4()), channel_rank=r) for r in (3, 4)]
    scores = {scored[0].key: 0.9, scored[1].key: 0.5}

    result = lc.compose(scored + tail, rerank_scores=scores)
    by_key = {r.key: r for r in result.rows}

    assert result.reranked is True
    assert by_key[scored[0].key].band == 1
    assert by_key[scored[1].key].band == 2
    # Both tail rows share the one terminal band; neither falls back to its
    # channel rank, which would have given them 3 and 4.
    assert by_key[tail[0].key].band == 3
    assert by_key[tail[1].key].band == 3

    plain = lc.compose(scored + tail)
    assert plain.reranked is False
    assert all(r.band == r.channel_rank for r in plain.rows)


def test_the_unscored_tail_band_orders_by_tier_then_key():
    scored = lc.memory_candidate(_memory_row(uuid4()), channel_rank=1)
    # The memory leads its channel, so its weighted score is the higher of the
    # two; the fact is deep in its own. Ordering the tail band by weighted
    # score would therefore put the memory first, which is the cross-channel
    # magnitude comparison the design forbids.
    tail_memory = lc.memory_candidate(_memory_row(uuid4()), channel_rank=2)
    tail_fact = lc.fact_candidate(
        _fact_row(uuid4(), verification_status="confirmed"), channel_rank=5,
    )

    result = lc.compose(
        [scored, tail_memory, tail_fact], rerank_scores={scored.key: 0.9},
    )
    tail_rows = [r for r in result.rows if r.band == 2]

    assert {r.key for r in tail_rows} == {tail_memory.key, tail_fact.key}
    assert tail_rows[0].key == tail_fact.key
    assert tail_rows[0].weighted_score < tail_rows[1].weighted_score
    assert [r.key for r in tail_rows] == [
        r.key for r in sorted(tail_rows, key=lambda r: (-r.tier, r.key))
    ]


def test_a_multiplier_moves_a_row_across_bands_but_never_across_a_tier():
    """The two halves of doc 07 §6's rank boost, on one fixture.

    (b)'s mutation is **reintroducing the weighted score into the
    cross-channel sort**, not deleting the tier term. Simulated on this exact
    fixture: with ``-tier`` gone the sort falls to ``key``, and ``"fact:…"``
    sorts before ``"memory:…"``, so the fact still leads and the guard passes
    while removed. No fixture can dodge that here, because a memory's key
    prefix always sorts after a fact's — the article fixture in
    ``test_verified_sorts_above_labelled_candidate_in_the_same_band`` is where
    the tier term is observable.
    """
    weights = {"w_importance": 10.0}
    memories = _memory_channel(5, importance=lambda rank: 1.0 if rank == 5 else 0.5)
    fact = lc.fact_candidate(
        _fact_row(uuid4(), verification_status="confirmed"), channel_rank=1,
    )
    boosted = memories[4]

    result = lc.compose(memories + [fact], weights=weights)
    by_key = {r.key: r for r in result.rows}

    # (a) the multiplier is not order-inert: rank 5 re-ranks to band 1.
    assert by_key[boosted.key].channel_rank == 5
    assert by_key[boosted.key].band == 1
    assert by_key[memories[0].key].band == 2

    # (b) inside band 1 the tier still decides, at any weight.
    band_one = [r for r in result.rows if r.band == 1]
    assert {r.key for r in band_one} == {fact.key, boosted.key}
    assert band_one[0].key == fact.key
    assert by_key[boosted.key].weighted_score > by_key[fact.key].weighted_score

    for magnitude in (10.0, 1e6):
        rows = lc.compose(memories + [fact], weights={"w_importance": magnitude}).rows
        assert [r for r in rows if r.band == 1][0].key == fact.key


def test_the_context_boost_is_band_monotone_in_its_weight():
    """Band monotonicity, which is a theorem; **not** position monotonicity,
    which is not.

    Within a channel only matched rows scale, so a matched row's within-channel
    rank is weakly non-increasing in the weight regardless of what any other
    channel does. Composed *position* is a different quantity: with matched
    rows in more than one channel, a matched row rising in its own channel can
    displace the bands above it and push an unrelated row of another channel
    down, so a matched row's position can worsen while its band improves.
    """
    matched_memory = lc.memory_candidate(
        _memory_row(uuid4(), applies_when={"env": "prod"}), channel_rank=3,
    )
    plain_memories = [
        lc.memory_candidate(_memory_row(uuid4()), channel_rank=r) for r in (1, 2)
    ]
    matched_fact = lc.fact_candidate(
        _fact_row(uuid4(), verification_status="corroborated",
                  applies_when={"env": "prod"}),
        channel_rank=2,
    )
    plain_fact = lc.fact_candidate(
        _fact_row(uuid4(), verification_status="confirmed"), channel_rank=1,
    )
    candidates = plain_memories + [matched_memory, plain_fact, matched_fact]

    previous = {}
    for weight in (0.0, 0.5, 2.0, 20.0):
        rows = lc.compose(
            candidates,
            weights={"w_context_boost": weight},
            declared_context=_declared(env="prod"),
        ).rows
        by_key = {r.key: r for r in rows}
        for matched in (matched_memory, matched_fact):
            band = by_key[matched.key].band
            if matched.key in previous:
                assert band <= previous[matched.key], (
                    f"{matched.key} worsened from band {previous[matched.key]} "
                    f"to {band} at w={weight}"
                )
            previous[matched.key] = band

    assert previous[matched_memory.key] == 1
    assert previous[matched_fact.key] == 1


# ─────────── the service: fan-out, envelope, rerank derivation (D7, D10) ───────────


class _FakeLLM:
    def __init__(self, vector, fingerprint):
        self._vector = vector
        self._fingerprint = fingerprint

    async def embed(self, query: str):
        return self._vector, self._fingerprint


class _StubOrchestrator:
    """Counts the reranker's LLM calls and answers each with a fixed score."""

    def __init__(self, score=7):
        self.calls = 0
        self.score = score

    async def chat_completion(self, purpose, messages, **kwargs):
        self.calls += 1
        return json.dumps({"score": self.score})


@pytest.mark.asyncio
async def test_a_memory_keyword_outage_still_reads_partial(session, monkeypatch):
    memory_trace = hybrid_search.ChannelTrace(
        results=[_memory_row(uuid4())], semantic_failed=False, keyword_failed=True,
    )
    fact_trace = facts_channel.FactChannelTrace(
        results=[_fact_row(uuid4())], keyword_failed=False, name_failed=False,
    )

    async def _memory(self, *args, **kwargs):
        return memory_trace

    async def _facts(self, *args, **kwargs):
        return fact_trace

    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _memory)
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _facts)

    service = lc.LayerCompositionService(_FakeLLM([0.0], "fp"), session)
    result = await service.search("q", project="default")

    # Asserted first, deliberately: an unqualified merge loses the memory
    # keyword entry entirely, so a key assertion would raise KeyError and mask
    # whether the flag this test exists for actually flipped.
    assert result.envelope.partial is True

    channels = result.envelope.channels
    assert channels["memory.keyword"].failed is True
    assert channels["fact.keyword"].failed is False
    assert channels["memory.semantic"].failed is False
    assert channels["fact.semantic"].ran is False
    assert channels["article.semantic"].ran is False


@pytest.mark.asyncio
async def test_the_envelope_reports_the_conflict_tally_at_zero(session, monkeypatch):
    async def _memory(self, *args, **kwargs):
        return hybrid_search.ChannelTrace(results=[_memory_row(uuid4())])

    async def _facts(self, *args, **kwargs):
        return facts_channel.FactChannelTrace(results=[])

    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _memory)
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _facts)

    service = lc.LayerCompositionService(_FakeLLM([0.0], "fp"), session)
    result = await service.search("q", project="default")

    assert result.envelope.excluded["by_context_conflict"] == 0
    assert result.envelope.reranked is False


@pytest.mark.asyncio
async def test_the_rerank_mapping_covers_only_the_scored_window(session):
    orchestrator = _StubOrchestrator()
    service = lc.LayerCompositionService(
        _FakeLLM([0.0], "fp"), session, reranker=RerankerService(orchestrator),
    )
    candidates = [
        lc.memory_candidate(_memory_row(uuid4()), channel_rank=rank)
        for rank in range(1, 46)
    ]
    rows = lc.compose(candidates).rows
    assert len(rows) == 45

    scores = await service.derive_rerank_scores("q", rows)

    assert orchestrator.calls == lc.RERANK_WINDOW
    assert len(scores) == lc.RERANK_WINDOW
    window_keys = {r.key for r in rows[: lc.RERANK_WINDOW]}
    assert set(scores) == window_keys
    for tail_row in rows[lc.RERANK_WINDOW:]:
        assert tail_row.key not in scores


@pytest.mark.asyncio
async def test_a_total_rerank_failure_degrades_to_the_deterministic_order(session):
    class _DeadOrchestrator:
        async def chat_completion(self, *args, **kwargs):
            raise RuntimeError("reranker outage")

    service = lc.LayerCompositionService(
        _FakeLLM([0.0], "fp"), session, reranker=RerankerService(_DeadOrchestrator()),
    )
    candidates = [
        lc.memory_candidate(_memory_row(uuid4()), channel_rank=rank) for rank in (1, 2, 3)
    ]
    rows = lc.compose(candidates).rows

    assert await service.derive_rerank_scores("q", rows) is None
    assert lc.compose(candidates).reranked is False


@pytest.mark.asyncio
async def test_an_empty_rerank_mapping_is_no_signal(session):
    service = lc.LayerCompositionService(
        _FakeLLM([0.0], "fp"), session, reranker=RerankerService(_StubOrchestrator()),
    )
    assert await service.derive_rerank_scores("q", []) is None


@pytest.mark.asyncio
async def test_the_composition_serves_both_channels_end_to_end(session):
    fingerprint = "fake-embedder|4"
    vector = [1.0, 0.0, 0.0, 0.0]
    project = "t2-43-e2e"

    memory_id = uuid4()
    session.add(Memory(
        id=memory_id,
        content="postgres runs on the homelab box",
        source="test",
        project=project,
    ))
    await session.flush()
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, 'fake-embedder', 4, 'llm') ON CONFLICT DO NOTHING"
        ),
        {"fp": fingerprint},
    )
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector(4) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), '{}'::jsonb)"
        ),
        {"mid": memory_id, "fp": fingerprint, "vec": str(vector)},
    )

    repo = KnowledgeTripleRepository(session)
    fact = await repo.insert_open(
        triple_key=f"k-{uuid4()}",
        subject_name="postgres",
        object_name="homelab",
        rel_type="DEPLOYED_ON",
        fact="postgres runs on the homelab box",
        reference_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        project=project,
    )
    await repo.set_verification_status(fact["id"], "disputed")
    await record_event(
        session,
        event_type="verified",
        object_type="fact",
        object_id=uuid_module.UUID(fact["id"]),
        project=project,
        payload={"contradiction": _counterpart_block(counterpart_object="fly.io")},
    )
    await session.commit()

    service = lc.LayerCompositionService(_FakeLLM(vector, fingerprint), session)
    result = await service.search("postgres homelab", project=project)

    by_kind = {}
    for row in result.rows:
        by_kind.setdefault(row.id_kind, []).append(row)

    assert set(by_kind) == {"memory", "fact"}
    assert by_kind["memory"][0].id == str(memory_id)
    assert by_kind["memory"][0].labels["project"] == project
    assert by_kind["fact"][0].tier == lc.TIER_BY_VERIFICATION_STATUS["disputed"]
    assert by_kind["fact"][0].dispute["counterpart"]["object"] == "fly.io"
    assert result.envelope.partial is False
    assert set(result.envelope.channels) == {
        "memory.semantic", "memory.keyword",
        "fact.keyword", "fact.name", "fact.semantic",
        "article.semantic",
    }


# ─────────── code search cannot enter: three mechanisms (D9) ───────────
#
# M1 is the typed admission that **raises**; M2 is the closed vocabulary,
# pinned rather than merely declared; M3 is a reachability scan over the one
# file the vocabulary lives in. Each is independently load-bearing: without M1
# the closure becomes a silent filter, without M2 someone adds an adapter no
# scan can see, and without M3 the module can import the door it is closed
# against.

_BACKEND = Path(__file__).resolve().parent.parent
_COMPOSITION_PATH = _BACKEND / "app" / "services" / "layer_composition.py"

_CODE_SEARCH_RULES = ReachabilityRules(
    forbidden_modules=frozenset({"app.services.code_query"}),
    forbidden_attrs=frozenset({"code_query", "search_code"}),
    forbidden_literals=frozenset(
        {"CodeQueryService", "CodeSymbol", "code_chunk_embeddings"}
    ),
)


def test_a_code_shaped_row_cannot_enter_the_composition():
    """M1. The literal below is in the **live** code door's shape and carries
    no ``id`` key at all, which is illustrative of intent rather than the
    guard itself: the guard is the type check, and no shape passes it.

    The raise is the load-bearing half. Under a skip-based design a code row
    would be dropped without a word — ``normalize_row_id`` returns ``None``
    for it and ``rrf_fuse`` would ``continue`` past it — so its absence from
    the output would be indistinguishable from correct behaviour.
    """
    code_row = {
        "chunk_content": "def search_code(...):",
        "file_path": "app/services/code_query.py",
        "repo_id": str(uuid4()),
        "language": "python",
        "symbol_name": "search_code",
        "line_start": 23,
        "line_end": 105,
        "rrf_score": 0.016,
    }
    assert "id" not in code_row

    with pytest.raises(TypeError):
        lc.compose([code_row])
    with pytest.raises(TypeError):
        lc.compose([lc.memory_candidate(_memory_row(uuid4()), channel_rank=1), code_row])


def test_the_layer_vocabulary_is_closed():
    """M2. The only mechanism that sees an added adapter needing no
    code-search import at all — widening the vocabulary is invisible to a
    reachability scan, and this makes it a failing test instead."""
    assert lc.ID_KINDS == frozenset({"memory", "fact", "article"})
    assert lc.LAYERS == frozenset({"L0", "L2", "L3"})
    assert set(lc.LAYER_BY_ID_KIND) == lc.ID_KINDS
    assert set(lc.LAYER_BY_ID_KIND.values()) == lc.LAYERS
    assert set(lc.CHANNEL_LIST_WEIGHTS) == lc.ID_KINDS


def test_the_composition_cannot_reach_code_search():
    """M3, a **global** forbid over one file with an empty allowlist.

    A one-file scan gets no floor from ``app_sources()``, so vacuity is ruled
    out explicitly here: the file exists, parses, and is substantial.
    """
    assert _COMPOSITION_PATH.exists()
    tree = ast.parse(_COMPOSITION_PATH.read_text())
    assert len(list(ast.walk(tree))) > 200, "the scanned file is too small to be real"

    offenders = find_forbidden_reach([_COMPOSITION_PATH], _BACKEND, _CODE_SEARCH_RULES)
    assert not offenders, (
        "the layer composition reached the code-search door:\n" + "\n".join(offenders)
    )


def test_the_code_search_guard_rejects_a_synthesised_reference(tmp_path):
    """In-suite negative control, through the **same** predicate and the
    **same** rules, so the guard and its control cannot drift apart."""
    module = tmp_path / "app" / "services" / "eager_code.py"
    module.parent.mkdir(parents=True)
    module.write_text(
        "from app.services.code_query import CodeQueryService\n"
        "async def compose_with_code(session, query):\n"
        "    return await CodeQueryService(session).search_code(query)\n"
    )

    offenders = find_forbidden_reach([module], tmp_path, _CODE_SEARCH_RULES)
    assert offenders
    assert any("import route" in offender for offender in offenders)
    assert any("attribute route" in offender for offender in offenders)


def test_the_composition_is_on_the_hot_path_floor():
    """Invariant 15's floor carries a maintenance duty, and this discharges it
    for this module. The composition reads the verification label; it must
    never be able to reach the judge that computes one.

    ``facts_channel.py``'s own absence from that set is real and confirmed,
    and is routed to its own task rather than repaired here.
    """
    from tests.test_verification_judge import _HOT_PATH_MODULES

    assert "app/services/layer_composition.py" in _HOT_PATH_MODULES

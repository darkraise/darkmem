"""Doc 07 §5's composition — the keyspace, the ordering, the labels (T2.43)."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services import layer_composition as lc
from app.services import rank_fusion
from app.services.events import record_event
from app.services.verified_evidence import latest_verified_evidence

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

"""Pure, offline tests for the sliced accuracy scorer.

No database, no bench-DB opt-in (contrast test_retrieval_runner.py, which
drives the real pipeline). This is what T0.07's Verify command runs.
"""
import uuid

import pytest

from benchlib.retrieval_scorer import (
    DEFAULT_MIN_PAIRS,
    normalize_memory_id,
    score_retrieval,
)

_UUID_A = "11111111-1111-4111-8111-111111111111"
_UUID_B = "22222222-2222-4222-8222-222222222222"
_UUID_C = "33333333-3333-4333-8333-333333333333"


def _pair(pid, query, relevant, tag, **extra):
    return {"id": pid, "query": query, "relevant_memory_ids": relevant, "slice_tags": [tag], **extra}


# --- The id-normalisation invariant (brief §4) -----------------------------
# CLAUDE.md: hybrid search returns str ids, the vector repo returns UUID.
# A scorer that only ever sees one type in its tests has not tested this.

def test_a_uuid_ranked_id_matches_a_string_gold_id():
    """Ranked ids as UUID objects (the vector-repo-only fallback path)
    against gold holding plain strings (as gold.json stores them)."""
    pairs = [_pair("p1", "q", [_UUID_A], "exact")]
    ranked = {"p1": [uuid.UUID(_UUID_A)]}

    report = score_retrieval(ranked, pairs, k=5)

    assert report.pair_scores["p1"].hit is True
    assert report.pair_scores["p1"].reciprocal_rank == 1.0


def test_a_string_ranked_id_matches_a_uuid_gold_id():
    """The reverse direction: ranked ids as plain strings (the hybrid-search
    path) against gold expressed as UUID objects."""
    pairs = [_pair("p1", "q", [uuid.UUID(_UUID_A)], "exact")]
    ranked = {"p1": [_UUID_A]}

    report = score_retrieval(ranked, pairs, k=5)

    assert report.pair_scores["p1"].hit is True
    assert report.pair_scores["p1"].reciprocal_rank == 1.0


def test_removing_normalisation_would_score_a_real_hit_as_zero():
    """Pins the failure mode itself: comparing raw UUID/str without
    normalize_memory_id never raises, it just silently disagrees. If a
    future edit deletes the normalisation call inside the scorer, the two
    tests above catch it directly; this test documents *why* by showing the
    raw comparison this module exists to avoid."""
    assert uuid.UUID(_UUID_A) != _UUID_A
    assert normalize_memory_id(uuid.UUID(_UUID_A)) == normalize_memory_id(_UUID_A)


def test_mixed_case_uuid_string_still_matches():
    pairs = [_pair("p1", "q", [_UUID_A.upper()], "exact")]
    ranked = {"p1": [_UUID_A]}

    report = score_retrieval(ranked, pairs, k=5)

    assert report.pair_scores["p1"].hit is True


# --- MRR ---------------------------------------------------------------

def test_mrr_is_the_reciprocal_of_the_first_relevant_rank():
    pairs = [_pair("p1", "q", [_UUID_B], "exact")]
    ranked = {"p1": [_UUID_A, _UUID_B, _UUID_C]}

    report = score_retrieval(ranked, pairs, k=10)

    assert report.pair_scores["p1"].reciprocal_rank == pytest.approx(0.5)


def test_mrr_is_zero_when_no_relevant_id_appears():
    pairs = [_pair("p1", "q", [_UUID_C], "exact")]
    ranked = {"p1": [_UUID_A, _UUID_B]}

    report = score_retrieval(ranked, pairs, k=10)

    assert report.pair_scores["p1"].reciprocal_rank == 0.0
    assert report.pair_scores["p1"].hit is False


# --- hit@K is full-relevant-set coverage, not "any hit" -----------------
# This is the definition the multi-hop headroom finding depends on
# (SLICES.md: "the retriever returns only the lexically anchored memory...
# so hit@K over the full relevant set fails").

def test_hit_at_k_requires_every_relevant_id_for_a_multi_hop_pair():
    pairs = [_pair("p1", "q", [_UUID_A, _UUID_B], "multi-hop")]
    # Only the lexically-anchored half (A) is retrieved; the bridge-linked
    # consequence (B) never surfaces -- exactly the multi-hop failure mode.
    ranked = {"p1": [_UUID_A, _UUID_C]}

    report = score_retrieval(ranked, pairs, k=10)

    score = report.pair_scores["p1"]
    assert score.n_relevant == 2
    assert score.n_found == 1
    assert score.hit is False
    # MRR still credits reaching the first half, since MRR is a
    # first-relevant-rank measure, not a coverage measure.
    assert score.reciprocal_rank == 1.0


def test_hit_at_k_true_when_both_relevant_ids_are_within_k():
    pairs = [_pair("p1", "q", [_UUID_A, _UUID_B], "multi-hop")]
    ranked = {"p1": [_UUID_C, _UUID_A, _UUID_B]}

    report = score_retrieval(ranked, pairs, k=10)

    assert report.pair_scores["p1"].hit is True


def test_hit_at_k_respects_the_k_cutoff():
    pairs = [_pair("p1", "q", [_UUID_B], "exact")]
    ranked = {"p1": [_UUID_A, _UUID_C, _UUID_B]}

    assert score_retrieval(ranked, pairs, k=2).pair_scores["p1"].hit is False
    assert score_retrieval(ranked, pairs, k=3).pair_scores["p1"].hit is True


# --- Retired pairs are excluded from scoring ----------------------------

def test_retired_pairs_are_excluded_even_with_no_ranked_results():
    pairs = [
        _pair("p1", "q1", [_UUID_A], "exact"),
        _pair("p2", "q2", [_UUID_B], "exact", retired=True),
    ]
    ranked = {"p1": [_UUID_A]}  # p2 deliberately has no entry

    report = score_retrieval(ranked, pairs, k=5)

    assert set(report.pair_scores) == {"p1"}
    assert report.n_pairs == 1


def test_a_missing_live_pair_raises_instead_of_scoring_zero():
    pairs = [_pair("p1", "q1", [_UUID_A], "exact")]

    with pytest.raises(KeyError, match="p1"):
        score_retrieval({}, pairs, k=5)


# --- Under-powered slices are a distinct state, not a number -----------

def test_a_slice_below_min_pairs_reports_underpowered_not_a_number():
    pairs = [_pair(f"p{i}", f"q{i}", [_UUID_A], "temporal") for i in range(3)]
    ranked = {p["id"]: [_UUID_A] for p in pairs}

    report = score_retrieval(ranked, pairs, k=5, min_pairs=10)

    temporal = report.slices["temporal"]
    assert temporal.n_pairs == 3
    assert temporal.powered is False
    assert temporal.mrr is None
    assert temporal.hit_at_k is None


def test_a_slice_at_or_above_min_pairs_is_powered_with_real_numbers():
    pairs = [_pair(f"p{i}", f"q{i}", [_UUID_A], "fact") for i in range(10)]
    ranked = {p["id"]: [_UUID_A] for p in pairs}

    report = score_retrieval(ranked, pairs, k=5, min_pairs=10)

    fact = report.slices["fact"]
    assert fact.powered is True
    assert fact.mrr == 1.0
    assert fact.hit_at_k == 1.0


def test_a_slice_absent_from_the_input_still_reports_as_zero_pair_underpowered():
    pairs = [_pair("p1", "q1", [_UUID_A], "exact")]
    ranked = {"p1": [_UUID_A]}

    report = score_retrieval(ranked, pairs, k=5)

    assert report.slices["multi-hop"].n_pairs == 0
    assert report.slices["multi-hop"].powered is False


def test_the_aggregate_itself_can_be_underpowered():
    pairs = [_pair("p1", "q1", [_UUID_A], "exact")]
    ranked = {"p1": [_UUID_A]}

    report = score_retrieval(ranked, pairs, k=5, min_pairs=10)

    assert report.aggregate_powered is False
    assert report.aggregate_mrr is None
    assert report.aggregate_hit_at_k is None


def test_default_min_pairs_keeps_every_current_slice_powered():
    """Documents the threshold choice against the live counts named in
    task-T0.07-brief.md §5: exact 12, paraphrase 18, typo 14, fact 18,
    multi-hop 14, temporal 12, knowledge-update 14 -- the smallest is 12,
    comfortably above DEFAULT_MIN_PAIRS."""
    assert DEFAULT_MIN_PAIRS < 12


# --- Aggregate is pooled across all live pairs, not a mean of slice means

def test_aggregate_is_pooled_not_a_mean_of_slice_means():
    # 8 "exact" pairs, all hits (mrr=1.0); 2 "fact" pairs, both misses
    # (mrr=0.0). A macro-average of slice means would give 0.5; the pooled
    # (micro) mean over all 10 pairs gives 0.8.
    exact_pairs = [_pair(f"e{i}", f"q{i}", [_UUID_A], "exact") for i in range(8)]
    fact_pairs = [_pair(f"f{i}", f"q{i}", [_UUID_A], "fact") for i in range(2)]
    ranked = {p["id"]: [_UUID_A] for p in exact_pairs}
    ranked.update({p["id"]: [_UUID_C] for p in fact_pairs})

    report = score_retrieval(ranked, exact_pairs + fact_pairs, k=5, min_pairs=1)

    assert report.aggregate_mrr == pytest.approx(0.8)
    assert report.aggregate_hit_at_k == pytest.approx(0.8)


def test_score_retrieval_accepts_a_subset_of_gold_for_ad_hoc_populations():
    """The multi-hop headroom check (brief §6) scores a named 9-pair subset,
    not the whole slice -- score_retrieval must work over any caller-chosen
    population, keyed only by pair id."""
    pairs = [_pair(f"p{i}", f"q{i}", [_UUID_A], "multi-hop") for i in range(5)]
    ranked = {p["id"]: [_UUID_A] for p in pairs}

    report = score_retrieval(ranked, pairs, k=5, min_pairs=1)

    assert report.n_pairs == 5
    assert report.slices["multi-hop"].n_pairs == 5

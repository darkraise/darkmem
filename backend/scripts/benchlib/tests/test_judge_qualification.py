"""T2.26 — judge qualification: scoring arithmetic, the G-D eligibility lock,
recorder/report/record plumbing, and the runner (no bench DB, no live LLM)."""
import json

import pytest

from benchlib import entailment_gold, judge_qualification as jq

from app.services.verification_judge import JUDGE_VERDICTS, ProbeVerdict


def _pv(verdict=None, valid=None):
    if valid is None:
        valid = verdict is not None
    return ProbeVerdict(verdict=verdict, reason=None, raw=verdict or "", valid=valid)


# The 8-pair miniature: 2 entailed, 3 contradicted, 3 unsupported.
MINI_PAIRS = [
    {"id": "m-1", "verdict": "entailed", "slice_tags": ["verbatim"]},
    {"id": "m-2", "verdict": "entailed", "slice_tags": ["paraphrase"]},
    {"id": "m-3", "verdict": "contradicted", "slice_tags": ["value-swap"]},
    {"id": "m-4", "verdict": "contradicted", "slice_tags": ["value-swap"]},
    {"id": "m-5", "verdict": "contradicted", "slice_tags": ["direction"]},
    {"id": "m-6", "verdict": "unsupported", "slice_tags": ["unrelated"]},
    {"id": "m-7", "verdict": "unsupported", "slice_tags": ["overreach"]},
    {"id": "m-8", "verdict": "unsupported", "slice_tags": ["unrelated"]},
]

MINI_VERDICTS = {
    "m-1": _pv("entailed"),
    "m-2": _pv("entailed"),
    "m-3": _pv("contradicted"),
    "m-4": _pv("contradicted"),
    "m-5": _pv("unsupported"),        # missed contradiction
    "m-6": _pv("unsupported"),
    "m-7": _pv("contradicted"),       # manufactured dispute
    "m-8": _pv(None, valid=False),    # invalid response
}


def test_miniature_arithmetic_hand_computed():
    score = jq.score_judgments(MINI_PAIRS, MINI_VERDICTS)
    assert score.n_pairs == 8
    assert score.invalid == 1
    # Binary grounded: accepts = m-1, m-2 -> TP=2, FP=0.
    assert score.entailed_precision == pytest.approx(2 / 2)
    assert score.entailed_recall == pytest.approx(2 / 2)
    # Contradiction: predicted = m-3, m-4, m-7 -> TP=2, FP=1; gold = 3.
    assert score.contradiction_precision == pytest.approx(2 / 3)
    assert score.contradiction_recall == pytest.approx(2 / 3)


def test_miniature_confusion_matrix_exact():
    score = jq.score_judgments(MINI_PAIRS, MINI_VERDICTS)
    assert score.confusion["entailed"] == {"entailed": 2}
    assert score.confusion["contradicted"] == {"contradicted": 2, "unsupported": 1}
    assert score.confusion["unsupported"] == {
        "unsupported": 1, "contradicted": 1, "invalid": 1,
    }


def test_invalid_is_never_an_acceptance():
    # All-invalid output: nothing accepted, so entailed precision is
    # undefined (None), recall is 0 — an invalid response can only miss.
    verdicts = {p["id"]: _pv(None, valid=False) for p in MINI_PAIRS}
    score = jq.score_judgments(MINI_PAIRS, verdicts)
    assert score.invalid == 8
    assert score.entailed_precision is None
    assert score.entailed_recall == 0.0
    assert score.contradiction_precision is None


def test_per_slice_accuracy():
    score = jq.score_judgments(MINI_PAIRS, MINI_VERDICTS)
    assert score.per_slice["verbatim"] == {"n": 1, "correct": 1, "accuracy": 1.0}
    assert score.per_slice["value-swap"] == {"n": 2, "correct": 2, "accuracy": 1.0}
    assert score.per_slice["direction"] == {"n": 1, "correct": 0, "accuracy": 0.0}
    assert score.per_slice["unrelated"] == {"n": 2, "correct": 1, "accuracy": 0.5}
    assert score.per_slice["overreach"] == {"n": 1, "correct": 0, "accuracy": 0.0}


def test_majority_class_floor():
    score = jq.score_judgments(MINI_PAIRS, MINI_VERDICTS)
    assert score.majority_class_floor == pytest.approx(3 / 8)


def test_judge_verdicts_match_the_gold_vocabulary():
    # The drift guard deferred from the app-side suite (app/ must not
    # import benchlib; this suite may import both sides).
    assert JUDGE_VERDICTS == entailment_gold.VERDICTS


def test_sanity_fixtures_live_outside_the_gold():
    # The plumbing fixtures are a sibling file the gold loader never reads:
    # loading the gold is unaffected by their existence (m2).
    assert jq.SANITY_PAIRS_PATH != entailment_gold.GOLD_PATH
    doc = entailment_gold.load_entailment_gold()
    live = [p for p in doc["pairs"] if not p.get("retired")]
    assert len(live) == sum(doc["declared_verdict_counts"].values())


# ── gate eligibility: the T2.54 lock (doc 17 §11) ────────────────────────


def _synthetic_gold(n_live, n_l2, n_author):
    pairs = []
    for i in range(n_live):
        pairs.append({
            "id": f"eg-{i:04d}",
            "verdict": "entailed",
            "label_source": "author" if i < n_author else "adjudicated",
        })
    return {
        "pairs": pairs,
        "declared_provenance_counts": {
            "hand-authored-synthetic-fact": n_live - n_l2,
            "hand-authored-bench-corpus": 0,
            "synthesis-draft": 0,
            "l2-fact": n_l2,
        },
    }


def test_the_real_gold_is_refused_with_counts_surfaced():
    eligibility = jq.gate_eligibility(entailment_gold.load_entailment_gold())
    assert eligibility.eligible is False
    assert eligibility.live_pairs == 41
    assert eligibility.l2_fact_pairs == 0
    assert eligibility.author_labelled_pairs == 41
    joined = "\n".join(eligibility.reasons)
    assert "41 < 200" in joined
    assert "l2-fact: 0/41" in joined
    assert "author-labelled: 41/41" in joined


def test_a_grown_real_adjudicated_gold_is_eligible_with_counts_visible():
    eligibility = jq.gate_eligibility(_synthetic_gold(200, 25, 0))
    assert eligibility.eligible is True
    assert "l2-fact: 25/200" in "\n".join(eligibility.reasons)


def test_199_pairs_is_refused_exactly_at_the_boundary():
    eligibility = jq.gate_eligibility(_synthetic_gold(199, 25, 0))
    assert eligibility.eligible is False
    assert "199 < 200" in "\n".join(eligibility.reasons)


def test_one_real_pair_in_200_is_accepted_and_loud():
    # The intended minimum-decodable reading of §11: >= 1 real pair blocks
    # the synthetic-only vector mechanically; the adequacy of 1/200 is
    # T2.41's human adjudication, handed the count.
    eligibility = jq.gate_eligibility(_synthetic_gold(200, 1, 0))
    assert eligibility.eligible is True
    assert "l2-fact: 1/200" in "\n".join(eligibility.reasons)


def test_a_single_author_labelled_pair_blocks_eligibility():
    eligibility = jq.gate_eligibility(_synthetic_gold(200, 25, 1))
    assert eligibility.eligible is False
    assert "author-labelled: 1/200" in "\n".join(eligibility.reasons)


def test_retired_pairs_do_not_count_as_live():
    doc = _synthetic_gold(200, 25, 0)
    doc["pairs"].append({
        "id": "eg-9999", "verdict": "entailed",
        "label_source": "author", "retired": True,
    })
    eligibility = jq.gate_eligibility(doc)
    assert eligibility.live_pairs == 200
    assert eligibility.author_labelled_pairs == 0
    assert eligibility.eligible is True

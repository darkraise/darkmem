"""The seeded stratified resample draw (T2.54 Layer 3).

Two properties carry this module, and both are about what the export must
*not* say. The resample is the first accuracy measurement made from outside
the family that labelled the gold, so anything that tells a labeller a pair's
verdict class — a field, an ordering, a manifest entry — turns an independent
check back into a confirming one.
"""
from __future__ import annotations

import json

import pytest

from benchlib import entailment_gold, judge_qualification, resample_draw


@pytest.fixture(scope="module")
def gold_bytes():
    return entailment_gold.GOLD_PATH.read_bytes()


@pytest.fixture(scope="module")
def drawn(gold_bytes):
    return resample_draw.draw(entailment_gold.load_entailment_gold(), gold_bytes)


def test_the_sample_is_the_ratified_size(drawn):
    assert len(drawn["rows"]) == resample_draw.RESAMPLE_N == 93


def test_the_draw_and_the_lock_agree_on_the_size():
    """The lock certifies what the draw produces. If the draw silently tracked
    a loosened lock it would yield a sample too small to support the claim the
    lock makes."""
    assert resample_draw.RESAMPLE_N == judge_qualification.RESAMPLE_N


def test_the_export_carries_no_answer_of_any_kind(drawn):
    fields = {k for row in drawn["rows"] for k in row}
    assert fields == {"id", "premise", "hypothesis"}


def test_the_contradicted_stratum_is_a_full_census(drawn):
    strata = drawn["manifest"]["strata"]["contradicted"]
    assert strata["mode"] == "full census"
    assert strata["drawn"] == strata["live"]


def test_the_remainder_is_split_proportionally(drawn):
    strata = drawn["manifest"]["strata"]
    remainder = resample_draw.RESAMPLE_N - strata["contradicted"]["drawn"]
    assert strata["unsupported"]["drawn"] + strata["entailed"]["drawn"] == remainder
    # Proportional, not equal: entailed is the larger live stratum.
    assert strata["entailed"]["drawn"] > strata["unsupported"]["drawn"]


def test_the_order_does_not_leak_the_strata(drawn):
    """Emitting strata in order hands over the class boundaries even with ids
    stripped: everything before the first boundary would be `contradicted`,
    the stratum actually under review."""
    gold = {p["id"]: p for p in entailment_gold.load_entailment_gold()["pairs"]}
    census_size = drawn["manifest"]["strata"]["contradicted"]["drawn"]
    leading = {gold[row["id"]]["verdict"] for row in drawn["rows"][:census_size]}
    assert len(leading) > 1, "the census stratum is emitted as a contiguous block"


def test_the_manifest_records_no_ids_and_no_labels(drawn):
    """A manifest mapping id -> stratum publishes each drawn pair's verdict
    class. Counts audit the draw just as well and leak nothing; the id set is
    recoverable by re-running against the same gold."""
    blob = json.dumps(drawn["manifest"])
    assert drawn["manifest"]["ids_recorded"] is False
    assert drawn["manifest"]["labels_recorded"] is False
    for pair_id in ("eg-0023", "eg-0142", "eg-0048"):
        assert pair_id not in blob
    for verdict_word in ('"verdict"', '"label_source"'):
        assert verdict_word not in blob


def test_the_seed_is_derived_from_the_gold_not_chosen(drawn, gold_bytes):
    """A seed someone picks is a seed someone can re-pick until the sample
    looks kind."""
    assert drawn["manifest"]["seed"] == resample_draw.derive_seed(gold_bytes)
    assert resample_draw.derive_seed(b"other gold") != resample_draw.derive_seed(gold_bytes)


def test_the_draw_is_reproducible(gold_bytes):
    again = resample_draw.draw(entailment_gold.load_entailment_gold(), gold_bytes)
    once = resample_draw.draw(entailment_gold.load_entailment_gold(), gold_bytes)
    assert [r["id"] for r in again["rows"]] == [r["id"] for r in once["rows"]]


def test_a_census_larger_than_n_refuses_rather_than_truncating(gold_bytes):
    doc = {"pairs": [
        {"id": f"x-{i}", "verdict": "contradicted", "premise": "p",
         "hypothesis": "h"}
        for i in range(resample_draw.RESAMPLE_N + 1)
    ]}
    with pytest.raises(ValueError, match="cannot be honoured"):
        resample_draw.draw(doc, gold_bytes)

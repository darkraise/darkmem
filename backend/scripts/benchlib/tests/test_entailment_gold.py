"""Pure-parsing validation of the entailment gold set (no bench DB).

The machine-checkable half of the gold's trust story: shape, the closed
verdict/slice/provenance vocabularies, slice-verdict consistency, the
declared counts, grounded and ungrounded representation including the hard
near-misses, and the corpus anchor for every pair whose premise claims
bench-corpus provenance. The labelling semantics themselves live in
entailment/LABELLING.md and are a human responsibility (T2.54).
"""
import json

import pytest

from benchlib import entailment_gold
from benchlib.entailment_gold import (
    GROUNDED_SLICES,
    GROUNDED_VERDICTS,
    MIXED_SLICES,
    NEAR_MISS_SLICES,
    PROVENANCES,
    SLICES,
    SLICE_VERDICTS,
    UNGROUNDED_SLICES,
    VERDICTS,
    is_grounded,
    load_entailment_gold,
    validate_gold_against_corpus,
)
from benchlib.retrieval_gold import load_retrieval_corpus

# The documented claim (LABELLING.md + gold.json's declared counts). A
# contributor appending pairs updates all of these together -- a silent
# re-tagging or a drifted count shows up as a failure here.
DOCUMENTED_SLICE_COUNTS = {
    "verbatim": 4,
    "paraphrase": 6,
    "weakening": 5,
    "temporal": 6,
    "direction": 5,
    "overreach": 6,
    "value-swap": 5,
    "unrelated": 4,
}
DOCUMENTED_VERDICT_COUNTS = {
    "entailed": 17,
    "contradicted": 10,
    "unsupported": 14,
}
# synthesis-draft and l2-fact are PINNED AT ZERO: neither producer exists
# (article_synthesis is a PlaceholderJobRunner until T3.02; knowledge_triples
# has no writer until T2.10). The first real harvest from either source is a
# deliberate edit to this pin, never a silent relabel -- provenance honesty
# is what keeps G-D's numbers meaning what they claim.
DOCUMENTED_PROVENANCE_COUNTS = {
    "hand-authored-synthetic-fact": 25,
    "hand-authored-bench-corpus": 16,
    "synthesis-draft": 0,
    "l2-fact": 0,
}


@pytest.fixture(scope="module")
def gold():
    return load_entailment_gold()


@pytest.fixture(scope="module")
def corpus():
    return load_retrieval_corpus()


def _live(gold):
    return [p for p in gold["pairs"] if not p.get("retired")]


def test_the_vocabularies_are_exactly_the_designed_ones():
    assert VERDICTS == {"entailed", "contradicted", "unsupported"}
    assert GROUNDED_VERDICTS == {"entailed"}
    assert GROUNDED_SLICES == {"verbatim", "paraphrase", "weakening"}
    assert MIXED_SLICES == {"temporal"}
    assert UNGROUNDED_SLICES == {"direction", "overreach", "value-swap", "unrelated"}
    assert SLICES == GROUNDED_SLICES | MIXED_SLICES | UNGROUNDED_SLICES
    assert NEAR_MISS_SLICES == {
        "weakening", "temporal", "direction", "overreach", "value-swap"
    }
    assert set(SLICE_VERDICTS) == SLICES


def test_gold_loads_and_declares_version_variant_and_counts(gold):
    assert gold["version"] == 1
    assert gold["variant"] == "claim-fact"
    assert gold["declared_slice_counts"] == DOCUMENTED_SLICE_COUNTS
    assert gold["declared_verdict_counts"] == DOCUMENTED_VERDICT_COUNTS
    assert gold["declared_provenance_counts"] == DOCUMENTED_PROVENANCE_COUNTS


def test_per_slice_counts_match_the_documentation(gold):
    computed = {s: 0 for s in SLICES}
    for pair in _live(gold):
        computed[pair["slice_tags"][0]] += 1
    assert computed == DOCUMENTED_SLICE_COUNTS


def test_verdict_counts_match_and_both_polarities_are_represented(gold):
    computed = {v: 0 for v in VERDICTS}
    for pair in _live(gold):
        computed[pair["verdict"]] += 1
    assert computed == DOCUMENTED_VERDICT_COUNTS
    grounded = [p for p in _live(gold) if is_grounded(p)]
    ungrounded = [p for p in _live(gold) if not is_grounded(p)]
    # The T2.25 Done-when floor: both polarities present in force, so a
    # precision AND a recall number are computable from the seed alone.
    assert len(grounded) >= 10
    assert len(ungrounded) >= 10
    assert len(grounded) + len(ungrounded) == len(_live(gold))


def test_no_slice_is_empty_and_every_near_miss_slice_is_populated(gold):
    tagged = {p["slice_tags"][0] for p in _live(gold)}
    assert tagged == SLICES
    for slice_name in NEAR_MISS_SLICES:
        live = [p for p in _live(gold) if p["slice_tags"][0] == slice_name]
        assert live, f"near-miss slice {slice_name} is empty"


def test_hard_near_misses_exist_on_both_sides_of_the_binary(gold):
    """The pairs that decide whether G-D's number means anything: grounded
    near-misses (an over-strict judge fails recall) and ungrounded
    near-misses (an overlap-driven judge fails precision)."""
    near = [p for p in _live(gold) if p["slice_tags"][0] in NEAR_MISS_SLICES]
    assert any(is_grounded(p) for p in near)
    assert sum(1 for p in near if not is_grounded(p)) >= 10


def test_every_live_pair_verdict_is_lawful_for_its_slice(gold):
    for pair in _live(gold):
        assert pair["verdict"] in SLICE_VERDICTS[pair["slice_tags"][0]]


def test_grounded_is_exactly_the_entailed_verdict(gold):
    for pair in _live(gold):
        assert is_grounded(pair) == (pair["verdict"] == "entailed")


def test_pair_ids_are_unique_and_appended_in_order(gold):
    ids = [p["id"] for p in gold["pairs"]]
    assert len(set(ids)) == len(ids)
    assert ids == sorted(ids)


def test_every_live_pair_records_a_labelling_rationale(gold):
    for pair in _live(gold):
        assert pair["rationale"].strip()


def test_every_live_pair_declares_an_honest_provenance(gold):
    computed = {p: 0 for p in PROVENANCES}
    for pair in _live(gold):
        computed[pair["provenance"]] += 1
    assert computed == DOCUMENTED_PROVENANCE_COUNTS
    # No pair may claim material from a producer that does not exist yet.
    assert computed["synthesis-draft"] == 0
    assert computed["l2-fact"] == 0


def test_corpus_provenance_pairs_anchor_to_the_retrieval_corpus(gold, corpus):
    validate_gold_against_corpus(gold, corpus)
    by_key = {e["key"]: e for e in corpus}
    for pair in _live(gold):
        if pair["provenance"] == "hand-authored-bench-corpus":
            assert pair["premise"] == by_key[pair["corpus_key"]]["content"]
        else:
            assert "corpus_key" not in pair


# ---------------------------------------------------------------------------
# Mutation tests: each guard in the loader is exercised by breaking the file
# and watching the loader refuse it. Removing a guard fails its test here.
# ---------------------------------------------------------------------------

def _reload_with(tmp_path, gold, mutate):
    doc = json.loads(json.dumps(gold))
    mutate(doc)
    path = tmp_path / "gold.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_loader_rejects_a_wrong_variant(tmp_path, gold):
    path = _reload_with(tmp_path, gold, lambda d: d.update(variant="claim-span"))
    with pytest.raises(ValueError, match="variant"):
        load_entailment_gold(path)


def test_loader_rejects_an_untabled_verdict(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["verdict"] = "grounded"

    with pytest.raises(ValueError, match="verdict must be one of"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_verdict_unlawful_for_its_slice(tmp_path, gold):
    """The labelling-consistency guard: a value-swap pair flipped to
    entailed is a labelling error, not a judgement call."""
    def mutate(doc):
        pair = next(p for p in doc["pairs"]
                    if p["slice_tags"][0] == "value-swap" and not p.get("retired"))
        pair["verdict"] = "entailed"
        doc["declared_verdict_counts"]["entailed"] += 1
        doc["declared_verdict_counts"]["contradicted"] -= 1

    with pytest.raises(ValueError, match="not lawful for slice"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_an_untabled_slice_tag(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["slice_tags"] = ["vibes"]

    with pytest.raises(ValueError, match="untabled slice tag"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_multiple_slice_tags(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["slice_tags"] = ["verbatim", "paraphrase"]

    with pytest.raises(ValueError, match="exactly one tag"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_an_unknown_provenance(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["provenance"] = "found-on-disk"

    with pytest.raises(ValueError, match="provenance"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_corpus_pair_without_its_key(tmp_path, gold):
    def mutate(doc):
        pair = next(p for p in doc["pairs"]
                    if p["provenance"] == "hand-authored-bench-corpus"
                    and not p.get("retired"))
        del pair["corpus_key"]

    with pytest.raises(ValueError, match="corpus_key"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_synthetic_pair_carrying_a_corpus_key(tmp_path, gold):
    def mutate(doc):
        pair = next(p for p in doc["pairs"]
                    if p["provenance"] == "hand-authored-synthetic-fact"
                    and not p.get("retired"))
        pair["corpus_key"] = "s01-grafana-port"

    with pytest.raises(ValueError, match="only lawful under a corpus"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_live_pair_without_a_rationale(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["rationale"] = "  "

    with pytest.raises(ValueError, match="rationale"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_an_identical_premise_hypothesis_pair(tmp_path, gold):
    def mutate(doc):
        pair = doc["pairs"][0]
        pair["hypothesis"] = pair["premise"]

    with pytest.raises(ValueError, match="identical"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_duplicate_live_pair(tmp_path, gold):
    def mutate(doc):
        first = doc["pairs"][0]
        second = doc["pairs"][1]
        second["premise"] = first["premise"]
        second["hypothesis"] = first["hypothesis"]

    with pytest.raises(ValueError, match="duplicate live"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_an_unknown_label_source(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["label_source"] = "model"

    with pytest.raises(ValueError, match="label_source"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_out_of_order_pair_ids(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0], doc["pairs"][1] = doc["pairs"][1], doc["pairs"][0]

    with pytest.raises(ValueError, match="ascending order"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


@pytest.mark.parametrize("key,bucket", [
    ("declared_slice_counts", "verbatim"),
    ("declared_verdict_counts", "entailed"),
    ("declared_provenance_counts", "l2-fact"),
])
def test_loader_rejects_declared_counts_that_drift(tmp_path, gold, key, bucket):
    def mutate(doc):
        doc[key][bucket] += 1

    with pytest.raises(ValueError, match="disagree"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_declared_counts_with_missing_keys(tmp_path, gold):
    def mutate(doc):
        del doc["declared_provenance_counts"]["synthesis-draft"]

    with pytest.raises(ValueError, match="declared_provenance_counts"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


def test_a_retired_pair_leaves_counts_but_stays_in_the_file(tmp_path, gold):
    """The append-only discipline: retiring excludes a pair from every
    declared count without deleting it."""
    doc = json.loads(json.dumps(gold))
    victim = doc["pairs"][0]
    victim["retired"] = True
    doc["declared_slice_counts"][victim["slice_tags"][0]] -= 1
    doc["declared_verdict_counts"][victim["verdict"]] -= 1
    doc["declared_provenance_counts"][victim["provenance"]] -= 1
    path = tmp_path / "gold.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    reloaded = load_entailment_gold(path)
    assert len(reloaded["pairs"]) == len(gold["pairs"])
    assert len(_live(reloaded)) == len(_live(gold)) - 1


def test_a_dangling_corpus_key_fails_cross_validation(gold, corpus):
    broken = json.loads(json.dumps(gold))
    pair = next(p for p in broken["pairs"]
                if p.get("corpus_key") and not p.get("retired"))
    pair["corpus_key"] = "zz-not-a-corpus-entry"
    with pytest.raises(ValueError, match="does not resolve"):
        validate_gold_against_corpus(broken, corpus)


def test_corpus_drift_under_a_pair_fails_cross_validation(gold, corpus):
    """The anchor discipline: if the retrieval corpus entry a premise was
    taken from changes content, the pair must fail validation and be
    re-adjudicated under retire-and-replace, never drift silently."""
    live_keys = {p["corpus_key"] for p in _live(gold) if p.get("corpus_key")}
    drifted = json.loads(json.dumps(corpus))
    for entry in drifted:
        if entry.get("key") in live_keys:
            entry["content"] = entry["content"] + " (edited)"
            break
    with pytest.raises(ValueError, match="retire-and-replace"):
        validate_gold_against_corpus(gold, drifted)


def test_default_paths_point_inside_the_entailment_dir():
    assert entailment_gold.GOLD_PATH.name == "gold.json"
    assert entailment_gold.GOLD_PATH.parent == entailment_gold.ENTAILMENT_DIR
    assert entailment_gold.ENTAILMENT_DIR.name == "entailment"

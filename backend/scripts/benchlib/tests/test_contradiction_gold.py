"""Pure-parsing validation of the contradiction-pair gold set (no bench DB).

The machine-checkable half of the gold's trust story: shape, the closed
label/slice/provenance vocabularies, slice-label consistency, the
structural preconditions each slice carries (endpoint sharing, token
disjointness, window overlap through the *shipped* predicate, origin
disjointness/equality), the declared counts, the renderer binding of every
side, and the l2-fact anchor. The opposition judgments themselves live in
contradiction/LABELLING.md and are a human responsibility.
"""
import json

import pytest

from app.services import contradiction_veto
from app.services.fact_lift import fact_sentence

from benchlib import contradiction_gold
from benchlib.contradiction_gold import (
    CONTRADICTION_SLICES,
    GOLD_PATH,
    LABELS,
    LABEL_CONTRADICTION,
    LABEL_NOT_CONTRADICTION,
    NOT_CONTRADICTION_SLICES,
    SIDE_PROVENANCES,
    SLICES,
    SLICE_LABELS,
    is_contradiction,
    load_contradiction_gold,
    pair_windows_overlap,
)
from benchlib.entailment_gold import FACT_KEY_FIELDS

# The documented claim (LABELLING.md + gold.json's declared counts). A
# contributor appending pairs updates all of these together -- a silent
# re-tagging or a drifted count shows up as a failure here.
DOCUMENTED_SLICE_COUNTS = {
    "same-endpoint": 10,
    "lexically-disjoint": 12,
    "non-overlap": 7,
    "echo": 7,
    "similar-unrelated": 8,
    "compatible-same-endpoint": 6,
}
DOCUMENTED_LABEL_COUNTS = {
    "contradiction": 22,
    "not-contradiction": 28,
}
# real-dispute is PINNED AT ZERO: no producer exists (the production
# contradiction scan is a PlaceholderJobRunner until T2.11, and no dispute
# has ever been adjudicated). A producer landing moves the pin visibly.
DOCUMENTED_SIDE_PROVENANCE_COUNTS = {
    "hand-authored-synthetic-fact": 79,
    "l2-fact": 21,
    "real-dispute": 0,
}


@pytest.fixture(scope="module")
def gold():
    return load_contradiction_gold()


def _live(gold):
    return [p for p in gold["pairs"] if not p.get("retired")]


def _render(side):
    side["fact"] = fact_sentence(
        side["subject_name"], side["rel_type"], side["object_name"]
    )


def test_the_vocabularies_are_exactly_the_designed_ones():
    assert LABELS == {"contradiction", "not-contradiction"}
    assert CONTRADICTION_SLICES == {"same-endpoint", "lexically-disjoint"}
    assert NOT_CONTRADICTION_SLICES == {
        "non-overlap", "echo", "similar-unrelated", "compatible-same-endpoint"
    }
    assert SLICES == CONTRADICTION_SLICES | NOT_CONTRADICTION_SLICES
    assert set(SLICE_LABELS) == SLICES
    assert SIDE_PROVENANCES == {
        "hand-authored-synthetic-fact", "l2-fact", "real-dispute"
    }


def test_window_semantics_are_the_shipped_vetos_by_identity():
    """Parity-by-import, asserted: the gold's overlap predicate IS the
    production veto's, so the two can never drift apart."""
    assert contradiction_gold.windows_overlap is contradiction_veto.windows_overlap


def test_gold_loads_and_declares_version_variant_and_counts(gold):
    assert gold["version"] == 1
    assert gold["variant"] == "fact-pair"
    assert gold["declared_slice_counts"] == DOCUMENTED_SLICE_COUNTS
    assert gold["declared_label_counts"] == DOCUMENTED_LABEL_COUNTS
    assert (
        gold["declared_side_provenance_counts"]
        == DOCUMENTED_SIDE_PROVENANCE_COUNTS
    )


def test_per_slice_counts_match_the_documentation(gold):
    computed = {s: 0 for s in SLICES}
    for pair in _live(gold):
        computed[pair["slice_tags"][0]] += 1
    assert computed == DOCUMENTED_SLICE_COUNTS


def test_label_counts_match_and_both_polarities_are_represented(gold):
    computed = {v: 0 for v in LABELS}
    for pair in _live(gold):
        computed[pair["label"]] += 1
    assert computed == DOCUMENTED_LABEL_COUNTS
    positives = [p for p in _live(gold) if is_contradiction(p)]
    negatives = [p for p in _live(gold) if not is_contradiction(p)]
    assert len(positives) >= 10
    assert len(negatives) >= 10
    assert len(positives) + len(negatives) == len(_live(gold))


def test_every_slice_is_populated(gold):
    tagged = {p["slice_tags"][0] for p in _live(gold)}
    assert tagged == SLICES


def test_every_live_pair_label_is_lawful_for_its_slice(gold):
    for pair in _live(gold):
        assert pair["label"] == SLICE_LABELS[pair["slice_tags"][0]]
        assert is_contradiction(pair) == (
            pair["slice_tags"][0] in CONTRADICTION_SLICES
        )


def test_the_disjoint_slice_carries_the_measurement_power(gold):
    """Doc 17 §5.2: the miss-rate bar is read on the lexically-disjoint
    slice, and at least half the contradiction pairs must be disjoint (the
    LABELLING.md reading of the 'at least half' recommendation)."""
    positives = [p for p in _live(gold) if is_contradiction(p)]
    disjoint = [
        p for p in positives if p["slice_tags"][0] == "lexically-disjoint"
    ]
    assert len(disjoint) >= 10, "the writer-trigger bar needs granularity"
    assert len(disjoint) * 2 >= len(positives)


def test_every_disjoint_pair_declares_its_coreference(gold):
    """An alias-mediated opposition without its declared co-reference is
    unadjudicable: the co-reference is part of the label (LABELLING.md)."""
    for pair in _live(gold):
        if pair["slice_tags"][0] == "lexically-disjoint":
            assert "co-refer" in pair["rationale"], pair["id"]


def test_pair_ids_are_unique_and_appended_in_order(gold):
    ids = [p["id"] for p in gold["pairs"]]
    assert len(set(ids)) == len(ids)
    assert ids == sorted(ids)


def test_every_live_pair_records_a_labelling_rationale(gold):
    for pair in _live(gold):
        assert pair["rationale"].strip()


def test_side_provenances_are_honest_and_real_dispute_is_pinned(gold):
    computed = {p: 0 for p in SIDE_PROVENANCES}
    for pair in _live(gold):
        for key in ("a", "b"):
            computed[pair[key]["provenance"]] += 1
    assert computed == DOCUMENTED_SIDE_PROVENANCE_COUNTS
    # No side may claim material from a producer that does not exist yet.
    assert computed["real-dispute"] == 0


def test_anchored_sides_keep_the_open_window_the_harvest_minted(gold):
    for pair in _live(gold):
        for key in ("a", "b"):
            if pair[key]["provenance"] == "l2-fact":
                assert pair[key]["valid_at"] is None
                assert pair[key]["invalid_at"] is None


def test_every_side_is_the_shipping_rendering_of_its_own_triple(gold):
    for pair in _live(gold):
        for key in ("a", "b"):
            side = pair[key]
            assert side["fact"] == fact_sentence(
                side["subject_name"], side["rel_type"], side["object_name"]
            )


def test_window_overlap_matches_each_pairs_slice(gold):
    for pair in _live(gold):
        overlap = pair_windows_overlap(pair)
        assert overlap == (pair["slice_tags"][0] != "non-overlap"), pair["id"]


def test_the_adjacent_boundary_case_is_represented(gold):
    """At least one non-overlap pair must close one window exactly where
    the other opens: the half-open [valid_at, invalid_at) convention is
    what makes adjacency disjoint, and a gold without the boundary case
    would never notice an inclusive-boundary regression in a consumer."""
    adjacent = [
        p for p in _live(gold)
        if p["slice_tags"][0] == "non-overlap"
        and (
            p["a"]["invalid_at"] is not None
            and p["a"]["invalid_at"] == p["b"]["valid_at"]
            or p["b"]["invalid_at"] is not None
            and p["b"]["invalid_at"] == p["a"]["valid_at"]
        )
    ]
    assert adjacent


def test_echo_pairs_carry_equal_origins_and_positives_disjoint(gold):
    for pair in _live(gold):
        a = set(pair["a"]["origin_keys"])
        b = set(pair["b"]["origin_keys"])
        if pair["slice_tags"][0] == "echo":
            assert a == b, pair["id"]
        else:
            assert not (a & b), pair["id"]


def test_default_paths_point_inside_the_contradiction_dir():
    assert GOLD_PATH.name == "gold.json"
    assert GOLD_PATH.parent == contradiction_gold.CONTRADICTION_DIR
    assert contradiction_gold.CONTRADICTION_DIR.name == "contradiction"


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


def _by_id(doc, pair_id):
    return next(p for p in doc["pairs"] if p["id"] == pair_id)


def _first_of_slice(doc, slice_name):
    return next(
        p for p in doc["pairs"]
        if p["slice_tags"][0] == slice_name and not p.get("retired")
    )


def test_loader_rejects_a_wrong_variant(tmp_path, gold):
    path = _reload_with(tmp_path, gold, lambda d: d.update(variant="claim-fact"))
    with pytest.raises(ValueError, match="variant"):
        load_contradiction_gold(path)


def test_loader_rejects_an_untabled_label(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["label"] = "disputed"

    with pytest.raises(ValueError, match="label must be one of"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_label_unlawful_for_its_slice(tmp_path, gold):
    """The labelling-consistency guard: an echo pair flipped to
    contradiction is a labelling error, not a judgement call."""
    def mutate(doc):
        pair = _first_of_slice(doc, "echo")
        pair["label"] = LABEL_CONTRADICTION
        doc["declared_label_counts"][LABEL_CONTRADICTION] += 1
        doc["declared_label_counts"][LABEL_NOT_CONTRADICTION] -= 1

    with pytest.raises(ValueError, match="not lawful for slice"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_an_untabled_slice_tag(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["slice_tags"] = ["vibes"]

    with pytest.raises(ValueError, match="untabled slice tag"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_multiple_slice_tags(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["slice_tags"] = ["same-endpoint", "echo"]

    with pytest.raises(ValueError, match="exactly one tag"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_an_unknown_label_source(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["label_source"] = "model"

    with pytest.raises(ValueError, match="label_source"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_live_pair_without_a_rationale(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["rationale"] = "  "

    with pytest.raises(ValueError, match="rationale"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_out_of_order_pair_ids(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0], doc["pairs"][1] = doc["pairs"][1], doc["pairs"][0]

    with pytest.raises(ValueError, match="ascending order"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_duplicate_unordered_pair(tmp_path, gold):
    """Swapping a's and b's texts into another pair must still be caught:
    sides are unordered, so (x, y) and (y, x) are one pair."""
    def mutate(doc):
        first = doc["pairs"][0]
        second = doc["pairs"][1]
        second["a"] = json.loads(json.dumps(first["b"]))
        second["b"] = json.loads(json.dumps(first["a"]))

    with pytest.raises(ValueError, match="duplicate live pair"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


@pytest.mark.parametrize("key,bucket", [
    ("declared_slice_counts", "echo"),
    ("declared_label_counts", "contradiction"),
    ("declared_side_provenance_counts", "l2-fact"),
])
def test_loader_rejects_declared_counts_that_drift(tmp_path, gold, key, bucket):
    def mutate(doc):
        doc[key][bucket] += 1

    with pytest.raises(ValueError, match="disagree"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_declared_counts_with_missing_keys(tmp_path, gold):
    def mutate(doc):
        del doc["declared_side_provenance_counts"]["real-dispute"]

    with pytest.raises(ValueError, match="declared_side_provenance_counts"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_a_retired_pair_leaves_counts_but_stays_in_the_file(tmp_path, gold):
    doc = json.loads(json.dumps(gold))
    victim = doc["pairs"][0]
    victim["retired"] = True
    doc["declared_slice_counts"][victim["slice_tags"][0]] -= 1
    doc["declared_label_counts"][victim["label"]] -= 1
    for key in ("a", "b"):
        doc["declared_side_provenance_counts"][victim[key]["provenance"]] -= 1
    path = tmp_path / "gold.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    reloaded = load_contradiction_gold(path)
    assert len(reloaded["pairs"]) == len(gold["pairs"])
    assert len(_live(reloaded)) == len(_live(gold)) - 1


# --- side-shape guards -----------------------------------------------------

def test_loader_rejects_a_side_fact_that_is_not_the_rendering(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["a"]["fact"] += " forever"

    with pytest.raises(ValueError, match="fact_sentence rendering"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_non_canonical_name(tmp_path, gold):
    def mutate(doc):
        side = _first_of_slice(doc, "non-overlap")["a"]
        side["subject_name"] = side["subject_name"].upper()
        _render(side)

    with pytest.raises(ValueError, match="canonical"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_an_untabled_rel_type(tmp_path, gold):
    def mutate(doc):
        side = _first_of_slice(doc, "non-overlap")["a"]
        side["rel_type"] = "SUPERSEDES"
        _render(side)

    with pytest.raises(ValueError, match="RELATIONSHIP_TYPES"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_naive_window(tmp_path, gold):
    def mutate(doc):
        _first_of_slice(doc, "non-overlap")["a"]["valid_at"] = (
            "2024-01-01T00:00:00"
        )

    with pytest.raises(ValueError, match="naive"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_an_inverted_window(tmp_path, gold):
    def mutate(doc):
        side = _first_of_slice(doc, "non-overlap")["a"]
        side["valid_at"], side["invalid_at"] = (
            side["invalid_at"], side["valid_at"]
        )

    with pytest.raises(ValueError, match="half-open"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_sides_in_different_projects(tmp_path, gold):
    def mutate(doc):
        pair = _first_of_slice(doc, "non-overlap")
        pair["b"]["project"] = "other"

    with pytest.raises(ValueError, match="one project"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_pair_of_one_triple(tmp_path, gold):
    def mutate(doc):
        pair = _first_of_slice(doc, "echo")
        pair["b"] = json.loads(json.dumps(pair["a"]))

    with pytest.raises(ValueError, match="one triple_key"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_missing_side(tmp_path, gold):
    def mutate(doc):
        del doc["pairs"][0]["b"]

    with pytest.raises(ValueError, match="missing side"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_an_unknown_side_field(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["a"]["confidence"] = 0.9

    with pytest.raises(ValueError, match="only the fields"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_empty_or_duplicate_origin_keys(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["a"]["origin_keys"] = []

    with pytest.raises(ValueError, match="origin_keys"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))

    def mutate_dup(doc):
        keys = doc["pairs"][0]["a"]["origin_keys"]
        doc["pairs"][0]["a"]["origin_keys"] = keys + keys

    with pytest.raises(ValueError, match="origin_keys"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate_dup))


def test_loader_rejects_an_unknown_side_provenance(tmp_path, gold):
    def mutate(doc):
        doc["pairs"][0]["a"]["provenance"] = "found-on-disk"

    with pytest.raises(ValueError, match="provenance"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


# --- l2-fact anchor guards -------------------------------------------------

def _first_l2(doc):
    for pair in doc["pairs"]:
        if pair.get("retired"):
            continue
        for key in ("a", "b"):
            if pair[key]["provenance"] == "l2-fact":
                return pair[key]
    raise AssertionError("no live l2-fact side in the gold")


def test_loader_rejects_an_l2_side_without_a_fact_key(tmp_path, gold):
    def mutate(doc):
        del _first_l2(doc)["fact_key"]

    with pytest.raises(ValueError, match="fact_key"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_fact_key_with_wrong_fields(tmp_path, gold):
    def mutate(doc):
        _first_l2(doc)["fact_key"]["extra"] = "x"

    with pytest.raises(ValueError, match="exactly the fields"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_an_unresolvable_triple_key(tmp_path, gold):
    def mutate(doc):
        _first_l2(doc)["fact_key"]["triple_key"] = (
            "00000000-0000-0000-0000-000000000000"
        )

    with pytest.raises(ValueError, match="does not resolve"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_fact_key_fields_that_disagree(tmp_path, gold):
    def mutate(doc):
        side = _first_l2(doc)
        side["fact_key"]["object_name"] = "something else"

    with pytest.raises(ValueError, match="source of truth"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_bounded_window_on_an_anchored_side(tmp_path, gold):
    def mutate(doc):
        _first_l2(doc)["valid_at"] = "2024-01-01T00:00:00+00:00"

    with pytest.raises(ValueError, match="open-ended window"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_fact_key_on_a_hand_authored_side(tmp_path, gold):
    def mutate(doc):
        donor = _first_l2(doc)
        for pair in doc["pairs"]:
            if pair["a"]["provenance"] == "hand-authored-synthetic-fact":
                pair["a"]["fact_key"] = json.loads(
                    json.dumps(donor["fact_key"])
                )
                return

    with pytest.raises(ValueError, match="only lawful under provenance"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


# --- slice structural preconditions ----------------------------------------

def test_loader_rejects_a_same_endpoint_pair_without_a_shared_name(tmp_path, gold):
    def mutate(doc):
        pair = _first_of_slice(doc, "same-endpoint")
        side = pair["b"]
        side["provenance"] = "hand-authored-synthetic-fact"
        side.pop("fact_key", None)
        side["subject_name"] = "apples"
        side["object_name"] = "oranges"
        _render(side)

    with pytest.raises(ValueError, match="shared endpoint name"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_disjoint_pair_sharing_a_token(tmp_path, gold):
    def mutate(doc):
        pair = _first_of_slice(doc, "lexically-disjoint")
        token = pair["a"]["subject_name"].split()[0]
        side = pair["b"]
        side["provenance"] = "hand-authored-synthetic-fact"
        side.pop("fact_key", None)
        side["subject_name"] = f"{token} appliance"
        _render(side)

    with pytest.raises(ValueError, match="token-disjoint"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_non_overlap_pair_whose_windows_overlap(tmp_path, gold):
    def mutate(doc):
        pair = _first_of_slice(doc, "non-overlap")
        pair["a"]["invalid_at"] = None

    with pytest.raises(ValueError, match="disjoint validity windows"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_disjoint_windows_outside_the_non_overlap_slice(tmp_path, gold):
    def mutate(doc):
        pair = _first_of_slice(doc, "echo")
        pair["a"]["valid_at"] = "2020-01-01T00:00:00+00:00"
        pair["a"]["invalid_at"] = "2021-01-01T00:00:00+00:00"
        pair["b"]["valid_at"] = "2022-01-01T00:00:00+00:00"

    with pytest.raises(ValueError, match="overlapping validity windows"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_an_echo_pair_with_a_fresh_witness(tmp_path, gold):
    def mutate(doc):
        pair = _first_of_slice(doc, "echo")
        pair["b"]["origin_keys"] = ["some-other-origin"]

    with pytest.raises(ValueError, match="equal origin_keys"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_a_positive_with_an_echo_origin_structure(tmp_path, gold):
    """A pair labelled contradiction whose sides share an origin is not
    veto-grade -- the shipped echo test would refuse it -- so the gold
    must refuse it too, or T2.52 would count a non-veto pair as a miss."""
    def mutate(doc):
        pair = _first_of_slice(doc, "same-endpoint")
        pair["b"]["origin_keys"] = list(pair["a"]["origin_keys"])

    with pytest.raises(ValueError, match="disjoint origin_keys"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_similar_unrelated_sharing_a_full_name(tmp_path, gold):
    def mutate(doc):
        pair = _first_of_slice(doc, "similar-unrelated")
        side = pair["b"]
        side["provenance"] = "hand-authored-synthetic-fact"
        side.pop("fact_key", None)
        side["subject_name"] = pair["a"]["subject_name"]
        _render(side)

    with pytest.raises(ValueError, match="no shared full endpoint name"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_similar_unrelated_without_a_shared_token(tmp_path, gold):
    def mutate(doc):
        pair = _first_of_slice(doc, "similar-unrelated")
        for key in ("a", "b"):
            side = pair[key]
            side["provenance"] = "hand-authored-synthetic-fact"
            side.pop("fact_key", None)
        pair["a"]["subject_name"] = "alpha thing"
        pair["a"]["object_name"] = "beta thing2"
        pair["b"]["subject_name"] = "gamma widget"
        pair["b"]["object_name"] = "delta widget2"
        _render(pair["a"])
        _render(pair["b"])

    with pytest.raises(ValueError, match="shared endpoint-name token"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))


def test_loader_rejects_compatible_pair_without_a_shared_name(tmp_path, gold):
    def mutate(doc):
        pair = _first_of_slice(doc, "compatible-same-endpoint")
        for key in ("a", "b"):
            side = pair[key]
            side["provenance"] = "hand-authored-synthetic-fact"
            side.pop("fact_key", None)
        pair["b"]["subject_name"] = "unrelated subject"
        _render(pair["b"])

    with pytest.raises(ValueError, match="shared endpoint name"):
        load_contradiction_gold(_reload_with(tmp_path, gold, mutate))

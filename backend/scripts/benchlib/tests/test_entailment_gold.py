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
    FACT_KEY_FIELDS,
    GROUNDED_SLICES,
    GROUNDED_VERDICTS,
    HARVEST_PATH,
    MIXED_SLICES,
    NEAR_MISS_SLICES,
    PROVENANCES,
    SLICES,
    SLICE_VERDICTS,
    UNGROUNDED_SLICES,
    VERDICTS,
    is_grounded,
    load_entailment_gold,
    load_l2_harvest,
    validate_gold_against_corpus,
)
from benchlib.retrieval_gold import load_retrieval_corpus
from benchlib import round4_frame
from benchlib.entailment_assignment import build_round4_assignment

# The documented claim, DERIVED rather than transcribed. Until the round-4
# gold these three tables were copied from the file they check, so a
# composition drift and its pin moved together and the test could only catch
# a hand edit made in one place. They are now computed from the artifacts that
# decided the composition before any pair existed: the ratified sampling frame
# (`round4_frame.json`, whose matrix the owner ratified at sitting 2) and the
# seeded premise assignment. A gold that does not match the frame it was
# authored against fails here, and no edit to gold.json can move the target.
_FRAME = json.loads(round4_frame.FRAME_PATH.read_text(encoding="utf-8"))

#: Rule 1's largest-remainder slice targets, straight off the ratified frame.
DOCUMENTED_SLICE_COUNTS = dict(_FRAME["slice_targets"])

# The contradicted census is 80 BY DESIGN, not by accident of authoring
# (T2.110): contradiction_recall_bar = 0.95 = 19/20 resolves in steps of
# 1/census, so the bar sits on the achievable lattice only when the census
# is a multiple of 20 — and the resample protocol's full-census stratum
# caps it at 93. 80 is the only multiple of 20 in (55, 93]. The frame's rule
# 2 encodes that derivation; this reads its output.
DOCUMENTED_VERDICT_COUNTS = dict(_FRAME["census"])

#: Slots the seeded round-4 assignment handed out, every one drawing a
#: manifest fact. `temporal` is the only slice it does not assign, because
#: `fact_lift` renders no validity window (doc 17 §11's exemption), so those
#: premises are hand-authored by construction rather than by choice.
_ASSIGNED_SLOTS = len(build_round4_assignment())

#: LABELLING.md, "Skip log (round 4, step 7)": 18 value-swap slots on
#: multi-valued relations, 2 direction slots whose differentiation note could
#: not be met, 1 paraphrase duplicate. Every one was re-authored in place for
#: the same slice and verdict on a hand-authored premise, which is why the
#: slice and verdict tables above are untouched by them and only the
#: provenance split moves. A skip that never reached the log would show up
#: here as a provenance the frame cannot account for.
ROUND4_LOGGED_SKIPS = 21

# synthesis-draft is PINNED AT ZERO: no producer's output has ever been
# authored into the gold. `hand-authored-bench-corpus` is zero for round 4 --
# the fresh round drew its premises from the harvest manifest and its
# hand-authored premises from the temporal exemption, not from the retrieval
# corpus -- and the loader's corpus guards are exercised against constructed
# documents below rather than against whatever a round happens to author.
DOCUMENTED_PROVENANCE_COUNTS = {
    "hand-authored-synthetic-fact": (
        _FRAME["total"] - _ASSIGNED_SLOTS + ROUND4_LOGGED_SKIPS
    ),
    "hand-authored-bench-corpus": 0,
    "synthesis-draft": 0,
    "l2-fact": _ASSIGNED_SLOTS - ROUND4_LOGGED_SKIPS,
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


def _synthetic_ids(doc, count=1):
    """Live `hand-authored-synthetic-fact` ids, in file order.

    The mutation tests below break one pair and watch a *specific* guard
    refuse it, so they need a pair no other guard is already holding. An
    `l2-fact` pair is not that pair: its premise is byte-bound to the harvest
    manifest, so touching it trips the anchor guard first and the test passes
    on the wrong refusal. Round 4 made that live -- the retired set happened to
    open with synthetic pairs and these tests reached for `pairs[0]`.
    """
    ids = [
        p["id"] for p in doc["pairs"]
        if not p.get("retired")
        and p["provenance"] == "hand-authored-synthetic-fact"
    ]
    assert len(ids) >= count, "the gold must carry synthetic pairs to mutate"
    return ids[:count]


def _as_corpus_pair(doc, corpus, corpus_key=None):
    """Convert one live synthetic pair into a lawful bench-corpus pair.

    The three corpus guards used to be exercised against whichever pairs a
    round happened to author with `hand-authored-bench-corpus` provenance.
    Round 4 authored none -- its premises come from the harvest manifest and
    from temporal's hand-authored exemption -- so every one of those tests
    raised `StopIteration` and would have gone on failing for every future
    round that draws its premises the same way. The guards are properties of
    the loader, not of a round's composition, so the pair is constructed here.
    """
    entry = next(e for e in corpus if e["key"] == corpus_key) if corpus_key \
        else corpus[0]
    victim_id = _synthetic_ids(doc)[0]
    pair = next(p for p in doc["pairs"] if p["id"] == victim_id)
    pair["provenance"] = "hand-authored-bench-corpus"
    pair["corpus_key"] = entry["key"]
    pair["premise"] = entry["content"]
    doc["declared_provenance_counts"]["hand-authored-synthetic-fact"] -= 1
    doc["declared_provenance_counts"]["hand-authored-bench-corpus"] += 1
    return pair


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


def test_loader_rejects_a_corpus_pair_without_its_key(tmp_path, gold, corpus):
    def mutate(doc):
        pair = _as_corpus_pair(doc, corpus)
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
        first_id, second_id = _synthetic_ids(doc, 2)
        by_id = {p["id"]: p for p in doc["pairs"]}
        by_id[second_id]["premise"] = by_id[first_id]["premise"]
        by_id[second_id]["hypothesis"] = by_id[first_id]["hypothesis"]

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
    pair = _as_corpus_pair(broken, corpus)
    pair["corpus_key"] = "zz-not-a-corpus-entry"
    with pytest.raises(ValueError, match="does not resolve"):
        validate_gold_against_corpus(broken, corpus)


def test_corpus_drift_under_a_pair_fails_cross_validation(gold, corpus):
    """The anchor discipline: if the retrieval corpus entry a premise was
    taken from changes content, the pair must fail validation and be
    re-adjudicated under retire-and-replace, never drift silently."""
    anchored = json.loads(json.dumps(gold))
    pair = _as_corpus_pair(anchored, corpus)
    drifted = json.loads(json.dumps(corpus))
    entry = next(e for e in drifted if e["key"] == pair["corpus_key"])
    entry["content"] = entry["content"] + " (edited)"
    with pytest.raises(ValueError, match="retire-and-replace"):
        validate_gold_against_corpus(anchored, drifted)


def test_default_paths_point_inside_the_entailment_dir():
    assert entailment_gold.GOLD_PATH.name == "gold.json"
    assert entailment_gold.GOLD_PATH.parent == entailment_gold.ENTAILMENT_DIR
    assert entailment_gold.ENTAILMENT_DIR.name == "entailment"
    assert HARVEST_PATH.name == "l2_harvest.json"
    assert HARVEST_PATH.parent == entailment_gold.ENTAILMENT_DIR


# ---------------------------------------------------------------------------
# The l2-fact anchor (T2.54 Ruling 2): manifest as source of truth, premise
# bound in bytes, manifest self-consistency pinned to the shipping
# compute_triple_key and fact_sentence. Each guard is exercised by forging
# exactly the shape it exists to refuse.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def manifest():
    return load_l2_harvest()


def test_the_committed_manifest_is_self_consistent(manifest):
    assert manifest["facts"], "the committed manifest must carry facts"


def test_l2_capacity_supports_the_authoring_target(manifest):
    """The Step-1 capacity bound, re-checked where the anchor lives: at the
    <= 4 pairs-per-premise cap the harvest must support >= 130 l2-fact
    pairs (the plan's margin target over doc 17 §11's 50% floor)."""
    assert 4 * len(manifest["facts"]) >= 130


def _l2_doc(row, mutate_pair=None):
    """A minimal loadable gold doc with one l2-fact pair anchored to a real
    committed-manifest row."""
    pair = {
        "id": "eg-9001",
        "premise": row["fact"],
        "hypothesis": f"It is recorded that {row['fact']}.",
        "verdict": "entailed",
        "slice_tags": ["verbatim"],
        "provenance": "l2-fact",
        "label_source": "author",
        "rationale": "anchor mutation fixture; verbatim rule",
        "fact_key": {field: row[field] for field in FACT_KEY_FIELDS},
    }
    if mutate_pair:
        mutate_pair(pair)
    return {
        "version": 99,
        "variant": "claim-fact",
        "declared_slice_counts": {s: (1 if s == "verbatim" else 0) for s in SLICES},
        "declared_verdict_counts": {v: (1 if v == "entailed" else 0) for v in VERDICTS},
        "declared_provenance_counts": {
            p: (1 if p == "l2-fact" else 0) for p in PROVENANCES
        },
        "pairs": [pair],
    }


def _load_doc(tmp_path, doc, harvest_path=HARVEST_PATH):
    path = tmp_path / "gold.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return load_entailment_gold(path, harvest_path=harvest_path)


def test_a_properly_anchored_l2_pair_loads(tmp_path, manifest):
    doc = _load_doc(tmp_path, _l2_doc(manifest["facts"][0]))
    assert doc["declared_provenance_counts"]["l2-fact"] == 1


def test_loader_rejects_a_premise_not_byte_equal_to_the_minted_fact(tmp_path, manifest):
    def mutate(pair):
        pair["premise"] = pair["premise"] + "."

    with pytest.raises(ValueError, match="byte-equal"):
        _load_doc(tmp_path, _l2_doc(manifest["facts"][0], mutate))


def test_loader_rejects_the_cased_fields_forgery(tmp_path, manifest):
    """Ruling 2 check 2's rationale: compute_triple_key canonicalises names
    while fact_sentence lowercases only the predicate, so a cased premise
    over correct-looking fields could pass a key-plus-recompute check while
    being a text fact_lift never produced. The byte-binding refuses it."""
    row = next(
        r for r in manifest["facts"] if r["fact"].capitalize() != r["fact"]
    )

    def mutate(pair):
        pair["premise"] = row["fact"].capitalize()

    with pytest.raises(ValueError, match="byte-equal"):
        _load_doc(tmp_path, _l2_doc(row, mutate))


def test_loader_rejects_an_unresolvable_triple_key(tmp_path, manifest):
    def mutate(pair):
        pair["fact_key"]["triple_key"] = "00000000-0000-0000-0000-000000000000"

    with pytest.raises(ValueError, match="does not resolve"):
        _load_doc(tmp_path, _l2_doc(manifest["facts"][0], mutate))


def test_loader_rejects_fact_key_fields_that_disagree_with_the_manifest(tmp_path, manifest):
    def mutate(pair):
        pair["fact_key"]["subject_name"] = pair["fact_key"]["subject_name"].upper()

    with pytest.raises(ValueError, match="source of truth"):
        _load_doc(tmp_path, _l2_doc(manifest["facts"][0], mutate))


def test_loader_rejects_an_l2_pair_without_a_fact_key(tmp_path, manifest):
    def mutate(pair):
        del pair["fact_key"]

    with pytest.raises(ValueError, match="fact_key"):
        _load_doc(tmp_path, _l2_doc(manifest["facts"][0], mutate))


def test_loader_rejects_a_fact_key_with_wrong_fields(tmp_path, manifest):
    def mutate(pair):
        pair["fact_key"]["extra"] = "x"

    with pytest.raises(ValueError, match="exactly the fields"):
        _load_doc(tmp_path, _l2_doc(manifest["facts"][0], mutate))


def test_loader_rejects_a_fact_key_on_a_non_l2_pair(tmp_path, gold, manifest):
    def mutate(doc):
        pair = next(p for p in doc["pairs"]
                    if p["provenance"] == "hand-authored-synthetic-fact"
                    and not p.get("retired"))
        row = manifest["facts"][0]
        pair["fact_key"] = {field: row[field] for field in FACT_KEY_FIELDS}

    with pytest.raises(ValueError, match="only lawful under provenance"):
        load_entailment_gold(_reload_with(tmp_path, gold, mutate))


def _forged_manifest(tmp_path, manifest, mutate):
    forged = json.loads(json.dumps(manifest))
    mutate(forged)
    path = tmp_path / "l2_harvest.json"
    path.write_text(json.dumps(forged), encoding="utf-8")
    return path


def test_manifest_with_a_non_fact_sentence_fact_is_refused(tmp_path, manifest):
    path = _forged_manifest(
        tmp_path, manifest,
        lambda m: m["facts"][0].update(fact=m["facts"][0]["fact"] + " forever"),
    )
    with pytest.raises(ValueError, match="fact_sentence"):
        load_l2_harvest(path)


def test_manifest_with_a_non_identity_triple_key_is_refused(tmp_path, manifest):
    path = _forged_manifest(
        tmp_path, manifest,
        lambda m: m["facts"][0].update(
            triple_key="00000000-0000-0000-0000-000000000000"
        ),
    )
    with pytest.raises(ValueError, match="compute_triple_key"):
        load_l2_harvest(path)


def test_manifest_out_of_order_is_refused(tmp_path, manifest):
    def mutate(m):
        m["facts"][0], m["facts"][1] = m["facts"][1], m["facts"][0]

    with pytest.raises(ValueError, match="sorted"):
        load_l2_harvest(_forged_manifest(tmp_path, manifest, mutate))


def test_gold_load_validates_the_manifest_it_is_pointed_at(tmp_path, gold, manifest):
    """The once-per-load rule: a forged manifest fails the gold load itself,
    even when the gold holds zero l2-fact pairs -- this is also the sunset
    tripwire for a future fact_sentence rendering change."""
    forged = _forged_manifest(
        tmp_path, manifest,
        lambda m: m["facts"][0].update(fact=m["facts"][0]["fact"] + " forever"),
    )
    gold_path = tmp_path / "gold.json"
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    with pytest.raises(ValueError, match="fact_sentence"):
        load_entailment_gold(gold_path, harvest_path=forged)


# ---------------------------------------------------------------------------
# Composition pins that move with Step 4's batches, visibly.
# ---------------------------------------------------------------------------

# The slices whose l2-fact representation requirement is already in force:
# every slice named here must carry at least one live l2-fact pair. Empty
# before Step 4's first append; each authoring batch adds the slices it
# covered, and the final state is every slice except temporal -- the one
# slice whose premises CANNOT be real today (fact_lift renders no validity
# window; doc 17 §11's exemption, sunset by the rendering tripwire above).
L2_TARGET_ASSIGNED_SLICES: frozenset[str] = frozenset({
    "verbatim", "paraphrase", "weakening", "direction", "overreach",
    "value-swap", "unrelated",
})


def test_temporal_is_never_l2_target_assigned():
    assert "temporal" not in L2_TARGET_ASSIGNED_SLICES
    assert L2_TARGET_ASSIGNED_SLICES <= SLICES - {"temporal"}


def test_every_target_assigned_slice_carries_a_live_l2_pair(gold):
    for slice_name in sorted(L2_TARGET_ASSIGNED_SLICES):
        live_l2 = [
            p for p in _live(gold)
            if p["slice_tags"][0] == slice_name and p["provenance"] == "l2-fact"
        ]
        assert live_l2, f"slice {slice_name} has no live l2-fact pair"


def test_no_premise_supports_more_than_four_live_pairs(gold):
    """The pairs-per-premise cap (T2.54 plan): a gold leaning on one premise
    for many pairs would let a single fact dominate every barred metric."""
    by_premise: dict[str, int] = {}
    for pair in _live(gold):
        by_premise[pair["premise"]] = by_premise.get(pair["premise"], 0) + 1
    worst = max(by_premise.values())
    assert worst <= 4, f"a premise supports {worst} live pairs"


# ---------------------------------------------------------------------------
# Census granularity (T2.110): the contradicted census must keep the recall
# bar measurable and the resample protocol honourable.
# ---------------------------------------------------------------------------


def test_the_contradicted_census_keeps_the_recall_bar_on_the_lattice(gold):
    """Recall resolves in steps of 1/census, so contradiction_recall_bar can
    only be exactly cleared or exactly missed when bar * census is integral.
    0.95 = 19/20, so the census must be a multiple of 20; and the resample's
    full-census stratification refuses a census above RESAMPLE_N, so growth
    past 93 needs the protocol re-ratified first, not a bigger append."""
    from app.services.verification_judge import VERIFICATION_BAR_DEFAULTS
    from benchlib import resample_draw

    bar = VERIFICATION_BAR_DEFAULTS["contradiction_recall_bar"]
    assert bar == 0.95, "the modulus below is derived from 0.95 = 19/20"
    census = sum(1 for p in _live(gold) if p["verdict"] == "contradicted")
    assert census % 20 == 0, (
        f"census {census}: 0.95 is not on the 1/{census} recall lattice, so "
        "the bar cannot be exactly cleared or exactly missed"
    )
    assert census <= resample_draw.RESAMPLE_N


# ---------------------------------------------------------------------------
# Ruling R-B: independence is at the proposition, not at the bytes
# ---------------------------------------------------------------------------

# Every duplicated proposition currently live in the gold, measured rather than
# hand-found. **Empty for round 4, and that is the debt being paid rather than
# a weaker check.** The retired set carried nine accepted duplicates (two of
# them `contradicted`, inside the census the G-D recall bar is computed over)
# as ruling R-B's recorded debt, "to be retired at the next round that moves
# the sha"; this is that round, and the byte-level screen finds none. A new
# duplicate therefore fails the build against an empty pin, which is the
# strongest form this test has ever had.
#
# Byte-level is not the whole story: the round's step-9 pass adjudicated
# duplicates this screen cannot see, and those live in
# `entailment/adjudicated_duplicates.json` and are asserted in
# `test_judge_qualification.py`. Nothing here is a claim that the census holds
# no duplicated proposition — only that none is visible at the bytes.
ACCEPTED_DUPLICATE_PROPOSITIONS: set[tuple[str, str]] = set()

CONTRADICTED_DUPLICATES: set[tuple[str, str]] = set()


def test_no_new_duplicate_proposition_enters_the_gold(gold):
    """The guard C-2 showed was missing.

    The loader compares bytes. `eg-0367` said what live `eg-0093` says in
    different words, so it passed, and the History's instruction not to resolve
    a collision by rewording could not reach the slot that never collided. A
    second prose instruction would repeat that at one remove, so the rule ships
    as a check.
    """
    from benchlib.duplicate_propositions import find_duplicate_propositions

    found = {f.key() for f in find_duplicate_propositions(gold["pairs"])}

    assert found - ACCEPTED_DUPLICATE_PROPOSITIONS == set(), (
        "a new duplicated proposition entered the gold — independence is at the "
        "proposition, not at the bytes (LABELLING.md, ruling R-B)"
    )
    assert ACCEPTED_DUPLICATE_PROPOSITIONS - found == set(), (
        "an accepted duplicate is gone; retire the pin with the pairs"
    )


def test_the_contradicted_census_carries_no_duplicated_proposition(gold):
    """The number the G-D reading has to disclose.

    The retired set scored 80 rows over 78 independent propositions, and the
    finding arrived in review after the attempt was spent. Round 4 scores 80
    over 80. Asserted separately from the set above because this is the one
    that changes what the recall bar means: an entailed duplicate sits outside
    the census the bar is computed over, a contradicted one does not.
    """
    from benchlib.duplicate_propositions import find_duplicate_propositions

    pairs = gold["pairs"]
    verdict = {p["id"]: p["verdict"] for p in pairs}
    contradicted = {
        f.key() for f in find_duplicate_propositions(pairs)
        if verdict[f.left] == "contradicted"
    }

    assert contradicted == CONTRADICTED_DUPLICATES


# ── the bare-sortal clause, enforced rather than swept for ───────────────

#: Sortals the 2026-08-17 bare-sortal clause places, by branch. Kept beside the
#: test rather than derived from LABELLING.md: a regex over prose would pass by
#: matching the clause's own examples, which is not the same as knowing a noun
#: was ruled on.
VACUOUS_SORTALS = frozenset({
    "component", "components", "system", "systems", "thing", "things",
    "something",
})
PARTITIONING_SORTALS = frozenset({
    "service", "services", "software", "database", "databases",
    "machine", "machines",
    # Ruled 2026-08-17: these sit between the earned "resource" and the
    # partitioning "database", and the ruling put them on this side.
    "datastore", "datastores", "backend", "backends",
})
RELATION_EARNED_SORTALS = frozenset({
    "host", "hosts", "installation", "installations",
    "dependency", "dependencies", "dependent", "dependents",
    "part", "parts", "constituent", "constituents",
    "resource", "resources", "consumer", "consumers",
    "prerequisite", "prerequisites", "connection", "connections",
})

#: Both shapes the clause reaches. **Two patterns, not one** — the first sweep
#: for this defect matched only quantified forms, and that is exactly how
#: eg-0512 ("Concourse is a piece of software that log-02 makes use of")
#: survived the round that retired eg-0699 for the identical sortal. A guard
#: that covers one shape is how the class comes back.
_SORTAL_PATTERNS = (
    r"(?:at least one|one of the)\s+(?:other\s+|named\s+|deployed\s+)*([a-z-]+)",
    r"\bis (?:a|an|one of the)\s+(?:other\s+|named\s+|deployed\s+)*([a-z-]+)",
    r"\bis among the\s+([a-z-]+)",
    r"\bthere is a\s+([a-z-]+)",
)


def test_every_sortal_a_live_pair_uses_is_one_the_clause_places(gold):
    """No live pair may rest on a sortal nobody ruled on.

    The clause decides a pair by asking whether its sortal restricts the
    premise's world. A sortal the clause does not place leaves that pair's
    label resting on an unwritten reading — which is the exact state the
    2026-08-16 resample miss measured, over 29 pairs at once.

    This fails on the *authoring* of such a pair rather than on a resample
    sitting that costs a measurement attempt to discover it.
    """
    import re

    placed = VACUOUS_SORTALS | PARTITIONING_SORTALS | RELATION_EARNED_SORTALS
    unplaced: dict[str, list[str]] = {}
    for pair in gold["pairs"]:
        if pair.get("retired"):
            continue
        hypothesis = pair["hypothesis"].lower()
        for pattern in _SORTAL_PATTERNS:
            for match in re.finditer(pattern, hypothesis):
                sortal = match.group(1)
                if sortal not in placed:
                    unplaced.setdefault(sortal, []).append(pair["id"])

    assert not unplaced, (
        "live pairs use sortals the bare-sortal clause does not place: "
        f"{unplaced}. Rule the sortal in LABELLING.md first (rule-then-pairs), "
        "then label the pair -- never the other way round."
    )


def test_no_live_pair_carries_a_partitioning_sortal_unearned(gold):
    """The eg-0699 / eg-0512 defect, refused at the file rather than by a model.

    A partitioning sortal is asserted restrictor content, so a hypothesis
    applying one to a witness the premise never classifies is `unsupported` --
    and both of this gold's instances were labelled `entailed`, one of them
    authored as a *replacement* in the round that retired the other. Neither
    was caught by a rule; the first cost a resample sitting and the second was
    found only by widening a sweep.
    """
    import re

    #: Verb-phrase idioms where a partitioning word is not a kind predicated of
    #: an entity. Narrowing the SCAN to the behaviour it is about, rather than
    #: exempting the pairs it misfires on: "Garage is put into service by
    #: data-06" says Garage is *used*, not that Garage is a service.
    idioms = (r"put into service", r"back into service", r"\bin service\b",
              r"out of service")

    offenders = []
    for pair in gold["pairs"]:
        if pair.get("retired") or pair["verdict"] != "entailed":
            continue
        hypothesis = pair["hypothesis"].lower()
        for idiom in idioms:
            hypothesis = re.sub(idiom, " ", hypothesis)
        premise = pair["premise"].lower()
        # SHAPE-FREE on purpose. Three pattern-scoped sweeps each missed a
        # shape the next one found -- existentials missed predicate nominals
        # (eg-0512), and both missed the referential definite (eg-0450). A
        # scan that enumerates syntactic frames can only catch the frames
        # somebody thought of, so this one looks at every word and asks
        # instead whether the PREMISE establishes the kind.
        for word in re.findall(r"[a-z]+", hypothesis):
            if word in PARTITIONING_SORTALS and word.rstrip("s") not in premise:
                offenders.append((pair["id"], word))
                break

    assert not offenders, (
        f"entailed pairs applying a partitioning sortal: {offenders}. The "
        "premise must establish the kind; what the witness 'obviously is' is "
        "world knowledge (procedure 2)."
    )


def test_every_sortal_the_guard_places_is_named_in_the_rulebook():
    """The guard's vocabulary and the clause's prose must not drift apart.

    The guard above decides pairs from three frozensets. If a noun enters
    those sets without entering LABELLING.md, a pair using it passes the
    build while still resting on a reading no committed rule states — which
    is precisely the condition the clause was written to end, reintroduced
    through the guard meant to enforce it.

    Found by a blind labeller, not by design: two replacements authored on
    2026-08-17 used "installation" and "something", both of which the guard
    accepted and the clause did not name.
    """
    rulebook = (entailment_gold.ENTAILMENT_DIR / "LABELLING.md").read_text(
        encoding="utf-8"
    ).lower()
    # Singulars only: the clause names a noun once, not once per inflection.
    placed = VACUOUS_SORTALS | PARTITIONING_SORTALS | RELATION_EARNED_SORTALS

    def is_plural_of_a_placed_noun(word: str) -> bool:
        if word.endswith("ies") and f"{word[:-3]}y" in placed:
            return True
        return word.endswith("s") and word[:-1] in placed

    singulars = {s for s in placed if not is_plural_of_a_placed_noun(s)}
    missing = sorted(s for s in singulars if f'"{s}"' not in rulebook)
    assert not missing, (
        f"sortals the guard places but LABELLING.md never names: {missing}. "
        "Rule the noun in the clause first; the guard enforces the rule, it "
        "is not the rule."
    )

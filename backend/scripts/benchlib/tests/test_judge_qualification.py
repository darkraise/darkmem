"""T2.26 — judge qualification: scoring arithmetic, the G-D eligibility lock,
recorder/report/record plumbing, and the runner (no bench DB, no live LLM)."""
import json
import pathlib

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


@pytest.fixture(autouse=True)
def _qualification_records_redirected(tmp_path_factory, monkeypatch):
    """Point every role's canonical record at a throwaway directory.

    The assertions in this file say "this run minted nothing at the canonical
    location", and they said it by asking whether the real file exists. That
    read whatever `app/services/` happened to contain — which was nothing, only
    because no role had ever qualified. **T2.125 qualified the entailment role
    on 2026-08-17 and four of those assertions inverted in one commit, none of
    them about the mint.** They did not catch a regression; they stopped
    testing the writer.

    Redirecting makes "canonical" mean "the path the writer treats as
    canonical" rather than "the path this checkout ships", so the refusal legs
    are about the writer again and stay true whatever the tree holds. Same
    medicine `conftest`'s `_corroboration_gate_closed_by_default` applies to
    the G-C record, for the same reason.

    What this deliberately stops covering is the SHIPPED records' own state — a
    property of the artifacts, not of the writer — asserted directly below.
    """
    # Named `services/` on purpose: one leg of the minting lock spells the
    # canonical location relatively as `parent/../services/<name>` to prove a
    # dodged path is refused too, and that spelling has to resolve back to the
    # same file for the leg to mean anything.
    root = tmp_path_factory.mktemp("qualification") / "services"
    root.mkdir()
    for role in vj.QUALIFICATION_RECORD_PATHS:
        monkeypatch.setitem(
            vj.QUALIFICATION_RECORD_PATHS,
            role,
            root / f"verification_qualification.{role}.json",
        )


def test_the_shipped_qualification_records_are_what_the_ledger_claims():
    """The artifacts themselves, at their real paths.

    The autouse redirect above hides these from every other test here, so
    without this one the shipped records would be covered by nothing in this
    file.
    """
    services = pathlib.Path(vj.__file__).parent
    contradiction = services / "verification_qualification.contradiction.json"
    entailment = services / "verification_qualification.entailment.json"

    # Contradiction recall has missed an unmoved 0.95 four times across two
    # vendors. A record here would mean something minted it without a cleared
    # run.
    assert not contradiction.exists()

    assert entailment.exists(), "T2.125 minted this; see the ledger's G-D entry"
    record = json.loads(entailment.read_text(encoding="utf-8"))
    assert record["role"] == "entailment"
    assert record["gate_eligible"] is True
    # The content basis, cross-checked against the live gold: a record whose
    # pairs have moved since qualifies nothing (T2.116).
    assert record["gold_pairs_sha256"] == entailment_gold.pairs_content_hash(
        entailment_gold.load_entailment_gold()["pairs"]
    )
    assert set(record["bars_gating_this_role"]) == {
        "groundedness_gate_precision_bar",
        "groundedness_gate_recall_bar",
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


_MISSING = object()


def _certified_resample(pairs=None):
    """A block that would certify, over ``pairs`` when they are given.

    ``pairs`` is optional only so a caller can build a *deliberately*
    uncertified block; every fixture that means to be eligible must pass
    its pairs, because since T2.116 a block that names no pair set is
    refused exactly like one that names the wrong set.
    """
    block = {"n": 93, "disagreements": 0, "seed": 4242,
             "performed_by": "owner", "date": "2026-08-06"}
    if pairs is not None:
        block["pairs_sha256"] = entailment_gold.pairs_content_hash(pairs)
        block["pair_digests"] = entailment_gold.pair_digests(pairs)
    return block


def _synthetic_gold(n_live, n_l2, n_author, resample=_MISSING):
    pairs = []
    for i in range(n_live):
        pairs.append({
            "id": f"eg-{i:04d}",
            "verdict": "entailed",
            "label_source": "author" if i < n_author else "adjudicated",
        })
    doc = {
        "pairs": pairs,
        "declared_provenance_counts": {
            "hand-authored-synthetic-fact": n_live - n_l2,
            "hand-authored-bench-corpus": 0,
            "synthesis-draft": 0,
            "l2-fact": n_l2,
        },
    }
    doc["resample"] = _certified_resample(pairs) if resample is _MISSING else resample
    return doc


def test_the_real_gold_is_now_eligible_on_every_condition():
    """The round-4 gold is eligible on every condition (T2.124, 2026-08-17).

    This test has moved with each resolution rather than being deleted, so the
    honest state stays pinned. It has asserted, in turn: 1 author-labelled
    pair and an absent resample; then the retired set's certified block at 1
    disagreement of 93; and now the fresh set's, at 0 of 93 under glm-5.2.
    **It deliberately asserts the disagreement count exactly**, not merely
    that the bar holds — a later change that quietly relaxed the file to 2
    disagreements would otherwise stay invisible.

    The composition numbers are derived from the ratified frame rather than
    transcribed; `test_entailment_gold.py` owns that derivation and this reads
    it, so a gold matching neither the frame nor this pin fails in both files.

    The conditions themselves are still exercised against synthetic golds
    below -- the real gold must not become the only thing this file checks,
    or the lock would be untested the moment it matters.
    """
    from benchlib.tests.test_entailment_gold import (
        DOCUMENTED_PROVENANCE_COUNTS, DOCUMENTED_VERDICT_COUNTS,
    )

    live_target = sum(DOCUMENTED_VERDICT_COUNTS.values())
    l2_target = DOCUMENTED_PROVENANCE_COUNTS["l2-fact"]

    doc = entailment_gold.load_entailment_gold()
    eligibility = jq.gate_eligibility(doc)
    assert eligibility.eligible is True
    assert eligibility.live_pairs == live_target
    assert eligibility.l2_fact_pairs == l2_target
    assert eligibility.author_labelled_pairs == 0
    # Eligible means exactly one reason: the composition line, no blockers.
    assert len(eligibility.reasons) == 1
    joined = eligibility.reasons[0]
    assert f"l2-fact: {l2_target}/{live_target}" in joined
    assert f"author-labelled: 0/{live_target}" in joined

    # Every escalation is adjudicated: no live pair carries the author's own
    # label, which is the condition `gate_eligibility` blocks on mechanically.
    live = [p for p in doc["pairs"] if not p.get("retired")]
    assert [p["id"] for p in live if p["label_source"] == "author"] == []

    # The certifying sitting, pinned: a non-Claude labeller, under the bar.
    resample = doc["resample"]
    assert resample["n"] == jq.RESAMPLE_N == 93
    # **Exactly, not "within the bar".** The re-sitting after the 2026-08-17
    # excluded-premise repair passed ON the bar (1 of 1 allowed), not under it,
    # and a later change that quietly relaxed the file to 2 would otherwise be
    # invisible. The one disagreement is eg-0423, uncorroborated: no other
    # sitting has ever drawn that pair, which is the case the <= 1 bar exists
    # for — as distinct from the case this round refused, where two independent
    # instruments converged on one pair.
    assert resample["disagreements"] == 1
    assert "deepseek-v4-pro" in resample["performed_by"]
    # The glm-5.2 certification of the pre-repair pair set is kept, not dropped.
    assert len(resample["supersedes"]) == 1
    assert "glm-5.2" in resample["supersedes"][0]["performed_by"]


def test_rule_b_boundary_tracks_labelling_md_and_splits_the_real_gold():
    """Rule B's second population is a claim about judge history that
    no column in `gold.json` records — and deliberately cannot, since adding
    one would move the sha the Layer-3 resample draw is pinned to. So the
    boundary lives in the harness, and the only thing keeping it honest is this
    test: LABELLING.md's History entry is the source of record, and a growth
    round that extends the population without moving the constant would
    otherwise silently shrink the population the gate verdict must hold on.

    **The two populations coincide on a restarted id sequence, and that is a
    ratified reading rather than a degenerate case** (LABELLING.md, "The Rule
    B reading for a gold with no contacted pairs"). Round 4 replaced the file
    with a census no judge has seen, at ids above the boundary, so the pooled
    and Rule-B populations are the same set until the first attempt spends
    against this gold. The proper-subset form this test used to assert would
    now fail on the honest state, so the assertion follows the two cases: a
    coinciding population must be *stated* as such in the rulebook, and a
    split one must carry its range there, both ends verbatim.
    """
    labelling = (
        pathlib.Path(entailment_gold.ENTAILMENT_DIR) / "LABELLING.md"
    ).read_text(encoding="utf-8")
    doc = entailment_gold.load_entailment_gold()
    live = [p for p in doc["pairs"] if not p.get("retired")]
    last_id = max(p["id"] for p in live)

    subset = jq.rule_b_population(live)
    assert subset, (
        "the subset must be non-empty: empty means Rule B silently stops "
        "constraining"
    )
    assert all(p["id"] >= jq.RULE_B_FIRST_ID for p in subset)

    if len(subset) == len(live):
        assert "The Rule B reading for a gold with no contacted pairs" in labelling, (
            "the pooled and Rule B populations coincide, which is lawful only "
            "on a gold with no contacted pairs — LABELLING.md must say so, "
            "because nothing in gold.json records it"
        )
    else:
        # The range LABELLING.md states, both ends, verbatim.
        assert f"{jq.RULE_B_FIRST_ID}..{last_id}" in labelling, (
            "LABELLING.md's Rule B range no longer matches the constant "
            f"({jq.RULE_B_FIRST_ID}) and the gold's last id ({last_id})"
        )
    # Every barred metric must be *computable* on the subset, or the rule's
    # "report on both populations" cannot be satisfied at all.
    verdict_classes = {p["verdict"] for p in subset}
    assert verdict_classes == {"entailed", "contradicted", "unsupported"}, (
        f"subset lacks a verdict class: {sorted(verdict_classes)}"
    )


def test_a_grown_real_adjudicated_gold_is_eligible_with_counts_visible():
    eligibility = jq.gate_eligibility(_synthetic_gold(200, 100, 0))
    assert eligibility.eligible is True
    assert "l2-fact: 100/200" in "\n".join(eligibility.reasons)


def test_199_pairs_is_refused_exactly_at_the_boundary():
    eligibility = jq.gate_eligibility(_synthetic_gold(199, 100, 0))
    assert eligibility.eligible is False
    assert "199 < 200" in "\n".join(eligibility.reasons)


def test_the_50_percent_floor_bites_exactly_at_the_boundary():
    # Ratified 2026-07-31 (doc 17 §11): l2-fact premises must be >= 50% of
    # live pairs. 100/200 clears; 99/200 is refused with the floor named.
    at_floor = jq.gate_eligibility(_synthetic_gold(200, 100, 0))
    assert at_floor.eligible is True

    below = jq.gate_eligibility(_synthetic_gold(200, 99, 0))
    assert below.eligible is False
    joined = "\n".join(below.reasons)
    assert ">=50% floor" in joined
    assert "l2-fact: 99/200" in joined


def test_the_199_synthetic_1_real_vector_is_refused():
    # §11's own clause: "a 199 synthetic / 1 real set must not pass". Under
    # the pre-2026-07-31 >= 1 floor this exact composition WAS eligible.
    eligibility = jq.gate_eligibility(_synthetic_gold(200, 1, 0))
    assert eligibility.eligible is False
    assert ">=50% floor" in "\n".join(eligibility.reasons)


def test_a_single_author_labelled_pair_blocks_eligibility():
    eligibility = jq.gate_eligibility(_synthetic_gold(200, 25, 1))
    assert eligibility.eligible is False
    assert "author-labelled: 1/200" in "\n".join(eligibility.reasons)


def test_retired_pairs_do_not_count_as_live():
    doc = _synthetic_gold(200, 100, 0)
    doc["pairs"].append({
        "id": "eg-9999", "verdict": "entailed",
        "label_source": "author", "retired": True,
    })
    eligibility = jq.gate_eligibility(doc)
    assert eligibility.live_pairs == 200
    assert eligibility.author_labelled_pairs == 0
    assert eligibility.eligible is True


# ── the certification's content basis (T2.116) ───────────────────────────
#
# D-7: the lock validated what the resample block *said* and never tied it
# to the pairs it certified, so a verdict flipped after the sitting left
# eligibility green. These tests are written against that exact case,
# because it is the one the pre-T2.116 lock passed.


def _flip_one_verdict(doc, pair_id=None):
    """Flip one live pair's verdict, returning its id. A label flip is the
    canonical post-certification tamper; everything else is a variation."""
    for pair in doc["pairs"]:
        if pair.get("retired"):
            continue
        if pair_id is not None and pair["id"] != pair_id:
            continue
        pair["verdict"] = (
            "unsupported" if pair["verdict"] != "unsupported" else "entailed"
        )
        return pair["id"]
    raise AssertionError("no live pair to flip")


def test_a_verdict_flipped_after_certification_turns_eligibility_red():
    """**The defect this task closes.** Before T2.116 this gold stayed
    eligible: n, disagreements, seed, performer and date all still read
    exactly as certified, because none of them describes the labels."""
    doc = _synthetic_gold(200, 100, 0)
    assert jq.gate_eligibility(doc).eligible is True

    flipped = _flip_one_verdict(doc)
    eligibility = jq.gate_eligibility(doc)

    assert eligibility.eligible is False
    reason = "\n".join(eligibility.reasons)
    # Named, not merely detected -- a refusal that says "something moved"
    # sends a human to diff 402 pairs by hand.
    assert flipped in reason
    assert "1 changed since certification" in reason


def test_the_refusal_names_added_and_removed_pairs_distinctly():
    """Three ways a pair set moves, and they mean different things: a
    changed label, a pair deleted out from under the certification, and a
    pair it never judged."""
    doc = _synthetic_gold(200, 100, 0)
    doc["pairs"].append({
        "id": "eg-8888", "verdict": "entailed", "label_source": "adjudicated",
    })
    removed = doc["pairs"].pop(0)["id"]
    changed = _flip_one_verdict(doc)

    reason = "\n".join(jq.gate_eligibility(doc).reasons)
    assert f"1 changed since certification: {changed}" in reason
    assert f"1 removed since certification: {removed}" in reason
    assert "1 added since certification: eg-8888" in reason


def test_annotation_churn_does_not_invalidate_a_certification():
    """The basis is narrower than the file sha on purpose. Every round to
    date has rewritten rationales after its sitting, and hashing bytes
    would make that ordinary churn indistinguishable from a label flip --
    a guard that fires on immaterial edits is one people re-stamp past."""
    doc = _synthetic_gold(200, 100, 0)
    for pair in doc["pairs"][:20]:
        pair["rationale"] = "rewritten long after the sitting"
        pair["slice_tags"] = ["some-later-retag"]
    assert jq.gate_eligibility(doc).eligible is True


def test_churn_inside_the_retired_archive_does_not_invalidate():
    """Retirement invalidates -- the pair leaves the live map and reports
    as removed -- but editing an already-retired pair cannot move any
    number the gate reads, so it must not fire the guard."""
    doc = _synthetic_gold(200, 100, 0)
    doc["pairs"].append({
        "id": "eg-7777", "verdict": "entailed",
        "label_source": "adjudicated", "retired": True,
    })
    assert jq.gate_eligibility(doc).eligible is True

    doc["pairs"][-1]["verdict"] = "contradicted"
    doc["pairs"][-1]["rationale"] = "re-adjudicated years later, still retired"
    assert jq.gate_eligibility(doc).eligible is True

    # Retiring a *live* pair is a different act and does invalidate.
    doc["pairs"][0]["retired"] = True
    reason = "\n".join(jq.gate_eligibility(doc).reasons)
    assert "removed since certification" in reason


def test_a_block_naming_no_pair_set_is_refused_like_one_naming_the_wrong_set():
    """A certification that cites no content is the pre-T2.116 shape. It
    must not be grandfathered: that shape is exactly what D-7 describes."""
    doc = _synthetic_gold(200, 100, 0)
    doc["resample"].pop("pairs_sha256")
    assert jq.gate_eligibility(doc).eligible is False
    assert "'pairs_sha256' missing" in "\n".join(jq.gate_eligibility(doc).reasons)

    doc = _synthetic_gold(200, 100, 0)
    doc["resample"].pop("pair_digests")
    assert jq.gate_eligibility(doc).eligible is False
    assert "'pair_digests' missing" in "\n".join(jq.gate_eligibility(doc).reasons)


def test_a_block_whose_map_does_not_derive_its_aggregate_is_refused():
    """The aggregate is the authority and the map is diagnostic, so the
    map is checked to derive the aggregate before it is trusted to explain
    anything. Repairing one field by hand to match the pairs while leaving
    the other stale lands here rather than passing."""
    doc = _synthetic_gold(200, 100, 0)
    flipped = _flip_one_verdict(doc)
    # Tamper: re-point the per-pair map at the new content, leaving the
    # aggregate as certified. Naively diffing the maps would now find
    # nothing moved.
    doc["resample"]["pair_digests"] = entailment_gold.pair_digests(doc["pairs"])

    eligibility = jq.gate_eligibility(doc)
    assert eligibility.eligible is False
    reason = "\n".join(eligibility.reasons)
    assert "internally inconsistent" in reason
    assert flipped not in reason  # it never gets as far as naming pairs


#: How the gold was serialised when the Layer-3 draw was taken over its bytes.
#:
#: The draw seed is a sha over the *file*, so reconstructing the drawn state
#: means re-serialising the way that file was written -- and the round-4 gold
#: was authored at `indent=1` while `resample_score.write_gold` emits
#: `indent=2`, so the certification write reformatted every line of a file
#: whose bytes a seed depends on. Content is unaffected and provably so: the
#: `pairs_sha256` leg above re-derives, and this leg reproduces
#: `gold_sha256` and the seed exactly at the drawn indent.
#:
#: A constant rather than a search over plausible indents: an audit that tries
#: formattings until one matches proves only that some formatting matches.
DRAWN_FILE_INDENT = 1


def test_the_real_gold_carries_a_basis_that_re_derives():
    """Done-when 4: the existing certified gold re-certifies with no manual
    strip. The stamp was not taken on trust -- the gold minus its own
    resample block reproduces the sha the draw manifest pinned, which
    proves the pairs have not moved since the sitting and explains D-8
    entirely: the certified sha differs from the file sha because writing
    the certification into the file is what changed it.

    Round 4 added a second reason the two shas differ, and it is a formatting
    one (see `DRAWN_FILE_INDENT`). The content leg is what carries the claim;
    the byte leg is reconstructed at the drawn indent so the draw stays
    reproducible from the certified file rather than only from git."""
    doc = entailment_gold.load_entailment_gold()
    block = doc["resample"]

    assert block["pairs_sha256"] == entailment_gold.pairs_content_hash(doc["pairs"])
    assert block["pair_digests"] == entailment_gold.pair_digests(doc["pairs"])
    live = [p for p in doc["pairs"] if not p.get("retired")]
    assert len(block["pair_digests"]) == len(live)  # retired excluded
    assert jq.gate_eligibility(doc).eligible is True

    gold_path = pathlib.Path(entailment_gold.__file__).parent / "entailment" / "gold.json"
    on_disk = json.loads(gold_path.read_text(encoding="utf-8"))
    stripped = {k: v for k, v in on_disk.items() if k != "resample"}
    manifest = json.loads(
        (gold_path.parent / "resample_manifest.json").read_text(encoding="utf-8")
    )
    # **The drawn file's own resample state, not "no resample state".** The
    # first certification drew against a file that carried none, so stripping
    # the key reproduced it. A *re*-certification draws against a file still
    # carrying the sitting it will supersede, so the drawn bytes include that
    # block — reconstructing without it cannot match, and the mismatch would
    # read as "the pairs moved" when nothing moved at all.
    prior = on_disk["resample"].get("supersedes") or []
    if prior:
        drawn_state = dict(stripped)
        drawn_state["resample"] = prior[-1]
    else:
        drawn_state = stripped
    reconstructed = hashlib.sha256(
        (
            json.dumps(drawn_state, indent=DRAWN_FILE_INDENT, ensure_ascii=False)
            + "\n"
        ).encode("utf-8")
    ).hexdigest()
    assert reconstructed == manifest["gold_sha256"]
    # And the manifest's seed derives from that same sha, so the draw, the
    # certification and the stamped basis all name one file state -- which is
    # what makes the sitting reproducible from the certified file alone.
    assert manifest["seed"] == int(manifest["gold_sha256"][:8], 16)


def test_the_basis_excludes_the_block_itself():
    """Done-when 1: 'a hash over the pairs alone, excluding the block
    itself'. Without this the field could never be stamped -- writing it
    would change what it hashes."""
    doc = _synthetic_gold(200, 100, 0)
    before = entailment_gold.pairs_content_hash(doc["pairs"])
    doc["resample"]["performed_by"] = "someone else entirely"
    doc["resample"]["supersedes"] = [{"n": 93, "disagreements": 1}]
    assert entailment_gold.pairs_content_hash(doc["pairs"]) == before
    assert jq.gate_eligibility(doc).eligible is True


# ── recorder, report, record writer (Task 5) ─────────────────────────────

import hashlib  # noqa: E402

from benchlib import ledger  # noqa: E402
from benchlib.twin import LatencyRecorder, TokenLedger, Twin  # noqa: E402

from app.services import verification_judge as vj  # noqa: E402


def _mini_twin():
    recorder = LatencyRecorder()
    for _ in range(3):
        recorder.record("fixture_call", 0.01, "live")
    for _ in range(8):
        recorder.record("judge_call", 0.02, "live")
    tokens = TokenLedger()
    for _ in range(11):
        tokens.record_live("verification", {"prompt_tokens": 100, "completion_tokens": 20})
    return Twin.capture(
        recorder, tokens, declared_channels=("fixture_call", "judge_call"),
    )


def _mini_meta(**overrides):
    identity = vj.judge_identity(_fake_cfg())
    meta = {
        "date": "2026-07-31",
        "run_id": "run-1",
        "timestamp": "2026-07-31T00:00:00+00:00",
        "git_sha": "deadbeef",
        "judge_identity": {**identity, "identity_hash": vj.judge_identity_hash(identity)},
        "bars": dict(vj.VERIFICATION_BAR_DEFAULTS),
        "gold_version": 1,
        "gold_sha256": "ab" * 32,
        "gold_touching_attempts": 1,
        "n_fixtures": 3,
        "fixture_tokens": {"verification": {"live_calls": 3}},
        "gold_tokens": {"verification": {"live_calls": 8}},
    }
    meta.update(overrides)
    return meta


def _fake_cfg():
    from app.config import LLMPurposeConfig
    return LLMPurposeConfig(
        model="deepseek-v4-flash", base_url="https://api.deepseek.com/v1",
        api_kind="deepseek", api_key="sk-test",
        params={"temperature": 0},
    )


def test_recorder_refuses_a_twinless_run(tmp_path):
    score = jq.score_judgments(MINI_PAIRS, MINI_VERDICTS)
    with pytest.raises(TypeError):
        jq.record_qualification(score, twin=None, metadata={}, path=tmp_path / "l.jsonl")


def test_recorder_round_trips_through_the_ledger(tmp_path):
    path = tmp_path / "ledger.jsonl"
    score = jq.score_judgments(MINI_PAIRS, MINI_VERDICTS)
    jq.record_qualification(
        score, twin=_mini_twin(), metadata={"run_id": "run-1", "intent_row_id": "att-1"},
        path=path,
    )
    runs = ledger.read_runs(path)
    assert len(runs) == 1
    row = runs[0]
    assert row["kind"] == "judge_qualification"
    assert row["run_id"] == "run-1"
    assert row["intent_row_id"] == "att-1"
    assert row["score"]["n_pairs"] == 8
    assert "tokens_by_purpose" in row["twin"]


def test_report_interim_banner_follows_both_eligibility_and_run_mode():
    """Two independent reasons a report is not a verdict, and each needs its own
    banner. Until 2026-08-08 only the eligibility one existed, and because the
    real gold was ineligible every interim run carried it -- so "unbannered"
    and "gate run" coincided by accident. When the gold became eligible an
    interim report rendered exactly like a gate verdict while minting nothing.
    """
    score = jq.score_judgments(MINI_PAIRS, MINI_VERDICTS)
    twin = _mini_twin()
    eligible = jq.gate_eligibility(_synthetic_gold(200, 100, 0))
    ineligible = jq.gate_eligibility(_synthetic_gold(200, 100, 0, resample=None))

    # Ineligible gold, interim run: both reasons stated, each with its cause.
    text = jq.render_report(score, ineligible, twin, {**_mini_meta(), "gate_run": False})
    assert "not a gate run" in text
    for reason in ineligible.reasons:
        assert reason in text

    # Eligible gold, interim run: still not a verdict, and it says which reason.
    text = jq.render_report(score, eligible, twin, {**_mini_meta(), "gate_run": False})
    assert "INTERIM" in text
    assert "not a gate run" in text
    assert "composition rule" not in text

    # Eligible gold, gate run: the only combination that carries no banner.
    text = jq.render_report(score, eligible, twin, {**_mini_meta(), "gate_run": True})
    assert "INTERIM" not in text


def test_report_records_the_whole_invocation_not_only_its_hash():
    """A reader must be able to reproduce the run from the report alone.

    The identity hash is not invertible, and a run that MISSES a bar writes no
    qualification record -- so before 2026-08-08 a failed run left the model
    name and nothing else. The G-D spike had to probe ~18k candidate configs
    and then attribute cached calls by token checksum to recover what had
    actually been run. Evidence nobody can reproduce the invocation for is
    weaker than it looks, and every G-D run so far has been a miss.
    """
    score = jq.score_judgments(MINI_PAIRS, MINI_VERDICTS)
    meta = {**_mini_meta(), "gate_run": True}
    meta["judge_identity"] = {
        "identity_hash": "abc123",
        "model": "gpt-5.5",
        "base_url": "https://api.openai.com/v1",
        "api_kind": "openai",
        "params": {"max_completion_tokens": 4000, "reasoning_effort": "high"},
        "dimensions": None,
        "reasoning": None,
        "prompt_version": 1,
        "prompt_sha": "f99151e4add69b31",
    }
    text = jq.render_report(score, jq.gate_eligibility(_synthetic_gold(200, 100, 0)),
                            _mini_twin(), meta)

    # Every field that shapes behaviour, not just the ones that are cheap to print.
    assert "https://api.openai.com/v1" in text
    assert "openai" in text
    assert "max_completion_tokens" in text
    assert "reasoning_effort" in text
    assert "4000" in text


# ── the near-mute judge (T2.109, doc 17 §6's 2026-08-08 amendment) ───────


def _near_mute(n_contradicted=55, n_entailed=101):
    """The judge the old gate qualified, reproduced through the shipped scorer.

    ``contradicted`` on exactly one correct pair and ``unsupported`` on every
    other contradiction; perfect on the entailed census. The censuses are the
    real gold's (55 gold-contradicted, 101 gold-entailed), so the recall this
    produces is the ledger's own 1/55 = 0.0182 rather than a number invented
    to make a point.
    """
    pairs, verdicts = [], {}
    for i in range(n_entailed):
        pid = f"e-{i}"
        pairs.append({"id": pid, "verdict": "entailed", "slice_tags": ["verbatim"]})
        verdicts[pid] = _pv("entailed")
    for i in range(n_contradicted):
        pid = f"c-{i}"
        pairs.append({"id": pid, "verdict": "contradicted", "slice_tags": ["value-swap"]})
        verdicts[pid] = _pv("contradicted" if i == 0 else "unsupported")
    return jq.score_judgments(pairs, verdicts)


def test_the_near_mute_judge_scores_the_recorded_numbers():
    """The premise the guard below rests on, measured rather than asserted."""
    score = _near_mute()
    assert score.contradiction_precision == pytest.approx(1.0)
    assert score.contradiction_recall == pytest.approx(1 / 55)
    assert round(score.contradiction_recall, 4) == 0.0182
    assert score.entailed_precision == pytest.approx(1.0)
    assert score.entailed_recall == pytest.approx(1.0)


def test_the_gate_cannot_qualify_a_near_mute_judge():
    """The incoherence that forced doc 08 §4.2's redesign, guarded.

    A judge missing 54 of 55 contradictions passes all three of the bars this
    gate carried before 2026-08-08 — that is asserted here, not assumed, so the
    guard cannot pass by the judge failing for some unrelated reason. What must
    refuse it is ``contradiction_recall_bar`` and nothing else. Dropping that
    key from ``verification_judge.BAR_METRICS`` reddens this test.
    """
    score = _near_mute()
    bars = {**vj.VERIFICATION_BAR_DEFAULTS, "contradiction_recall_bar": 0.90}
    results = jq.bar_results(score, bars)

    assert "contradiction_recall_bar" in results, (
        "contradiction-recall is ungated: the gate qualifies a judge that "
        "finds nothing"
    )
    assert results["contradiction_recall_bar"]["passed"] is False
    assert [k for k, r in results.items() if not r["passed"]] == [
        "contradiction_recall_bar"
    ], "every previously-gated bar passes; only the new one refuses this judge"


def test_an_unstated_bar_cannot_be_cleared_by_any_measurement(monkeypatch):
    """A barred metric with no value fails even a perfect judge.

    Reporting it absent instead would make an unstated bar read as no bar at
    all — the silence the redesign is about — so nothing clears until the
    number is written down.

    Exercised on a synthetic key. This used to run against
    `contradiction_recall_bar`, which carried no default until the owner stated
    it on 2026-08-08; leaving it there would have retired the guard the moment
    the bar was set, which is exactly when the mechanism starts mattering for
    the *next* barred metric.
    """
    monkeypatch.setitem(vj.BAR_METRICS, "a_future_bar", "contradiction_recall")
    perfect = jq.QualificationScore(
        n_pairs=1, invalid=0, confusion={},
        entailed_precision=1.0, entailed_recall=1.0,
        contradiction_precision=1.0, contradiction_recall=1.0,
        per_slice={}, majority_class_floor=1.0,
    )
    result = jq.bar_results(perfect, dict(vj.VERIFICATION_BAR_DEFAULTS))["a_future_bar"]
    assert result["bar"] is None
    assert result["measured"] == 1.0
    assert result["passed"] is False


def test_report_carries_bars_verdicts_and_attempts():
    score = jq.score_judgments(MINI_PAIRS, MINI_VERDICTS)
    eligibility = jq.gate_eligibility(_synthetic_gold(200, 100, 0))
    text = jq.render_report(score, eligibility, _mini_twin(), _mini_meta())
    assert "groundedness_gate_precision_bar" in text
    assert "0.95" in text
    # contradiction precision 2/3 sits below its 0.95 bar.
    assert "FAIL" in text and "PASS" in text
    assert "gold_touching_attempts: 1" in text
    # confusion table and per-slice ns are rendered.
    assert "value-swap" in text and "overreach" in text
    assert "```json" in text


def test_granularity_arithmetic_is_computed_not_hardcoded():
    twin = _mini_twin()
    eligibility = jq.gate_eligibility(_synthetic_gold(200, 100, 0))

    def gold_with_entailed(n_entailed):
        pairs, verdicts = [], {}
        for i in range(n_entailed):
            pid = f"e-{i}"
            pairs.append({"id": pid, "verdict": "entailed", "slice_tags": ["verbatim"]})
            verdicts[pid] = _pv("entailed")
        pairs.append({"id": "u-0", "verdict": "unsupported", "slice_tags": ["unrelated"]})
        verdicts["u-0"] = _pv("unsupported")
        return jq.score_judgments(pairs, verdicts)

    text17 = jq.render_report(gold_with_entailed(17), eligibility, twin, _mini_meta())
    assert "17/18" in text17 and "0.944" in text17
    assert "20/21" not in text17

    text20 = jq.render_report(gold_with_entailed(20), eligibility, twin, _mini_meta())
    assert "20/21" in text20 and "0.952" in text20
    assert "17/18" not in text20


def test_reproducible_metrics_are_serving_invariant():
    score = jq.score_judgments(MINI_PAIRS, MINI_VERDICTS)
    eligibility = jq.gate_eligibility(_synthetic_gold(200, 100, 0))

    all_live = {"verification": {
        "live_calls": 41, "live_prompt_tokens": 4100, "live_completion_tokens": 820,
        "live_cached_prompt_tokens": 0, "live_unknown_calls": 0,
        "cache_known_calls": 0, "cache_known_prompt_tokens": 0,
        "cache_known_completion_tokens": 0, "cache_known_cached_prompt_tokens": 0,
        "cache_unknown_calls": 0,
    }}
    all_replayed = {"verification": {
        "live_calls": 0, "live_prompt_tokens": 0, "live_completion_tokens": 0,
        "live_cached_prompt_tokens": 0, "live_unknown_calls": 0,
        "cache_known_calls": 41, "cache_known_prompt_tokens": 4100,
        "cache_known_completion_tokens": 820, "cache_known_cached_prompt_tokens": 0,
        "cache_unknown_calls": 0,
    }}
    meta_live = _mini_meta(gold_tokens=all_live)
    meta_warm = _mini_meta(gold_tokens=all_replayed, gold_touching_attempts=2)

    block_live = jq.reproducible_metrics(score, eligibility, meta_live)
    block_warm = jq.reproducible_metrics(score, eligibility, meta_warm)
    assert block_live == block_warm

    dumped = json.dumps(block_live)
    assert "timestamp" not in dumped
    assert "p50" not in dumped and "p95" not in dumped
    assert "gold_touching_attempts" not in dumped


def test_record_writer_schema_and_handshake(tmp_path, monkeypatch):
    score = jq.score_judgments(MINI_PAIRS, MINI_VERDICTS)
    # Perfect metrics so the handshake clears the default bars.
    perfect = jq.QualificationScore(
        n_pairs=8, invalid=0, confusion=score.confusion,
        entailed_precision=1.0, entailed_recall=1.0,
        contradiction_precision=1.0, contradiction_recall=1.0,
        per_slice=score.per_slice, majority_class_floor=score.majority_class_floor,
    )
    cfg = _fake_cfg()
    identity = vj.judge_identity(cfg)
    record_path = tmp_path / "record.json"
    gold_path = entailment_gold.GOLD_PATH
    gold_doc = _synthetic_gold(200, 100, 0)

    jq.write_qualification_record(
        record_path, role=vj.ENTAILMENT_ROLE, gold_path=gold_path,
        identity=identity, score=perfect,
        gold_doc=gold_doc, ledger_run_id="run-1",
        bars=dict(vj.VERIFICATION_BAR_DEFAULTS), git_sha="deadbeef",
        timestamp="2026-07-31T00:00:00+00:00",
    )
    record = json.loads(record_path.read_text())
    assert record["gold_sha256"] == hashlib.sha256(gold_path.read_bytes()).hexdigest()
    assert record["ledger_run_id"] == "run-1"
    assert record["gate_eligible"] is True
    assert record["judge_identity"]["identity_hash"] == vj.judge_identity_hash(identity)

    # The three fields the reader demands of a post-split record, written by
    # the one writer that may mint one: which role it qualifies, which pairs
    # produced it, and the confusion cell nothing bounds any more.
    assert record["role"] == vj.ENTAILMENT_ROLE
    assert record["gold_pairs_sha256"] == entailment_gold.pairs_content_hash(
        gold_doc["pairs"])
    assert record["metrics"][vj.LEAK_DISCLOSURE_METRIC] == (
        perfect.confusion.get("contradicted", {}).get("entailed", 0)
    )
    assert record["bars_gating_this_role"] == {
        bar: vj.VERIFICATION_BAR_DEFAULTS[bar]
        for bar in vj.JUDGE_ROLES[vj.ENTAILMENT_ROLE]
    }

    async def default_bars(_session):
        # `contradiction_recall_bar` is barred with no default (T2.109), so a
        # complete bar set has to state it — the resolver's own contract.
        return {**vj.VERIFICATION_BAR_DEFAULTS, "contradiction_recall_bar": 0.90}

    monkeypatch.setattr(vj, "get_verification_bars", default_bars)
    import asyncio
    state = asyncio.run(vj.qualification_state(
        None, {"verification": cfg}, role=vj.ENTAILMENT_ROLE,
        record_path=record_path,
    ))
    assert state.qualified is True, state.reasons

    # And the same record admits nothing as the other role: the writer's role
    # field is what the reader checks, so a minted entailment record leaves the
    # veto's consumer exactly as unqualified as it was.
    other = asyncio.run(vj.qualification_state(
        None, {"verification": cfg}, role=vj.CONTRADICTION_ROLE,
        record_path=record_path,
    ))
    assert other.qualified is False


def test_the_writer_refuses_a_retired_pair_set_for_every_role(tmp_path):
    """The stopping rule at the writer, not only at the runner's front door.

    The runner refuses before any gold contact; this is the second leg, so a
    future caller that reaches the writer by another route still cannot mint a
    record on the pairs whose budget is spent.
    """
    score = jq.score_judgments(MINI_PAIRS, MINI_VERDICTS)
    identity = vj.judge_identity(_fake_cfg())
    retired_path = _retired_gold_path()
    retired_doc = json.loads(retired_path.read_text(encoding="utf-8"))
    assert vj.is_retired_pair_set(
        entailment_gold.pairs_content_hash(retired_doc["pairs"])
    ), "the archived gold is the retired pair set; this test is about that"

    for role in sorted(vj.JUDGE_ROLES):
        with pytest.raises(ValueError, match="retired"):
            jq.write_qualification_record(
                tmp_path / f"{role}.json", role=role,
                gold_path=retired_path, identity=identity,
                score=score, gold_doc=retired_doc, ledger_run_id="run-1",
                bars=dict(vj.VERIFICATION_BAR_DEFAULTS), git_sha="deadbeef",
                timestamp="2026-08-12T00:00:00+00:00",
            )
        assert not (tmp_path / f"{role}.json").exists()


def test_the_runner_refuses_the_retired_pair_set_in_every_mode(tmp_path):
    """No model touches pair set `4975c5cc` again — gate or interim.

    An interim run sends the same pairs to the same model, so "the budget is
    spent" is not a claim about which flag was passed. The refusal lands before
    the intent row, so a refused run is not counted as a contact it never made.
    """
    for gate in (True, False):
        run_dir = tmp_path / f"gate-{gate}"
        stub_cls, seen = make_stub(cycling_script())
        with pytest.raises(RuntimeError, match="retired from qualification"):
            _run(run_dir, stub_cls, gate=gate,
                 gold_path=_retired_gold_path())
        assert not (run_dir / "ledger.jsonl").exists()
        assert {_premise_of(u) for u in seen} <= SANITY_PREMISES


def test_minting_lock_four_legs(tmp_path, monkeypatch):
    score = jq.score_judgments(MINI_PAIRS, MINI_VERDICTS)
    identity = vj.judge_identity(_fake_cfg())
    fixture_gold = tmp_path / "easy_gold.json"
    fixture_gold.write_text("{}")
    common = dict(
        identity=identity, score=score, gold_doc=_synthetic_gold(200, 100, 0),
        ledger_run_id="run-1", bars=dict(vj.VERIFICATION_BAR_DEFAULTS),
        git_sha="deadbeef", timestamp="2026-07-31T00:00:00+00:00",
    )

    role = vj.ENTAILMENT_ROLE
    canonical = vj.qualification_record_path(role)
    common["role"] = role

    # Leg 1: the canonical record path refuses a non-canonical gold.
    with pytest.raises(ValueError):
        jq.write_qualification_record(
            canonical, gold_path=fixture_gold, **common,
        )
    assert not canonical.exists()

    # Leg 2: a relative-path spelling of the canonical location refuses too.
    dodged = canonical.parent / ".." / "services" / canonical.name
    with pytest.raises(ValueError):
        jq.write_qualification_record(dodged, gold_path=fixture_gold, **common)
    assert not canonical.exists()

    # Leg 3: a rehearsal record path accepts any gold.
    rehearsal = tmp_path / "rehearsal-record.json"
    jq.write_qualification_record(rehearsal, gold_path=fixture_gold, **common)
    assert rehearsal.exists()

    # Leg 4: the canonical pairing works (canonical path pointed at tmp).
    tmp_canonical = tmp_path / f"verification_qualification.{role}.json"
    monkeypatch.setitem(vj.QUALIFICATION_RECORD_PATHS, role, tmp_canonical)
    jq.write_qualification_record(
        tmp_canonical, gold_path=entailment_gold.GOLD_PATH, **common,
    )
    assert tmp_canonical.exists()

    # Leg 5: an unknown role refuses before anything is written — the record's
    # role is what the reader gates on, so it may not be free-form.
    with pytest.raises(ValueError, match="unknown judge role"):
        jq.write_qualification_record(
            tmp_path / "faithfulness.json",
            **{**common, "role": "faithfulness", "gold_path": fixture_gold},
        )
    assert not (tmp_path / "faithfulness.json").exists()


# ── the runner (Task 6): stub-driven, no live LLM, no DB ─────────────────

import asyncio  # noqa: E402
import itertools  # noqa: E402

from benchlib import run_judge_qualification as rjq  # noqa: E402
from benchlib.twin import TokenLedger as _TokenLedger  # noqa: E402

SANITY_PREMISES = {
    p["premise"] for p in json.loads(jq.SANITY_PAIRS_PATH.read_text())["pairs"]
}


def make_stub(script):
    """A TwinningOrchestrator-constructor-compatible stub whose responses
    come from ``script(user_content)`` and which records every user message
    it was asked to judge."""
    seen: list[str] = []

    class StubOrchestrator:
        def __init__(self, config, cache_dir):
            self.config = config
            self.tokens = _TokenLedger()
            self.live_calls = 0

        async def chat_completion(self, purpose, messages, response_format=None, seed=None):
            user = messages[1]["content"]
            seen.append(user)
            self.live_calls += 1
            self.tokens.record_live(
                purpose, {"prompt_tokens": 100, "completion_tokens": 20},
            )
            return script(user)

    return StubOrchestrator, seen


def cycling_script():
    cycle = itertools.cycle(sorted(JUDGE_VERDICTS))
    def script(_user):
        return json.dumps({"verdict": next(cycle), "reason": "stub"})
    return script


def perfect_script(gold_path):
    """A stub that answers every pair with the gold's own verdict.

    Needed since 2026-08-08: a gate run that misses a bar no longer writes a
    qualification record, so a test exercising the *write* path needs a judge
    that clears. `cycling_script` cannot -- it answers round-robin.

    Keyed on premise **and** hypothesis. The gold reuses one hypothesis against
    several premises with different verdicts, so a hypothesis-keyed stub answers
    the wrong pair and the run fails a bar for a reason the code does not have.
    """
    doc = json.loads(pathlib.Path(gold_path).read_text(encoding="utf-8"))
    by_pair = {
        (p["premise"].strip(), p["hypothesis"].strip()): p["verdict"]
        for p in doc["pairs"] if not p.get("retired")
    }
    # The plumbing fixtures live outside the gold and carry their expected
    # verdict in a `note` prefix. They are answered too, because the runner
    # sanity-checks the fixture stage before it will touch the gold at all --
    # and that check fails a judge that emits only one verdict class.
    sanity = json.loads(pathlib.Path(jq.SANITY_PAIRS_PATH).read_text(encoding="utf-8"))
    for row in (sanity["pairs"] if isinstance(sanity, dict) else sanity):
        by_pair[(row["premise"].strip(), row["hypothesis"].strip())] = (
            row["note"].split("—", 1)[0].strip()
        )

    def script(user):
        premise = _premise_of(user)
        hypothesis = user.split("HYPOTHESIS:\n", 1)[1].split("\n", 1)[0]
        verdict = by_pair.get((premise.strip(), hypothesis.strip()))
        return json.dumps({"verdict": verdict or "unsupported", "reason": "stub"})

    return script


def _premise_of(user_content):
    return user_content.split("PREMISE:\n", 1)[1].split("\n\nHYPOTHESIS:", 1)[0]


def _run(tmp_path, stub_cls, **kwargs):
    """Drive the runner against a **synthetic** gold unless a test says
    otherwise.

    It used to default to the runner's own default, which is the canonical
    gold — so the plumbing tests drove a stub judge over the real pairs. That
    was already the shape of the 2026-08-08 leak (a stub run reaching gate mode
    on the real gold and minting a record), and since the 2026-08-12 retirement
    it is refused outright: `4975c5cc` may not be contacted for any role, and
    the refusal cannot tell a stub from a model. Defaulting to a fixture gold is
    what the suite wanted anyway — none of these tests is about the real pairs.
    """
    defaults = dict(
        deepseek_api_key="sk-test",
        report_dir=tmp_path / "reports",
        ledger_path=tmp_path / "ledger.jsonl",
        cache_dir=tmp_path / "cache",
        verdicts_dir=tmp_path / "verdicts",
        orchestrator_cls=stub_cls,
    )
    if "gold_path" not in kwargs:
        defaults["gold_path"] = _write_eligible_gold(tmp_path)
    defaults.update(kwargs)
    return asyncio.run(rjq.run_qualification(**defaults))


def _write_eligible_gold(tmp_path):
    # 100/200 l2-fact: the 50% floor exactly. The l2 pairs anchor to REAL
    # committed-manifest rows (premise byte-equal to the minted fact, full
    # fact_key) because the loader refuses any other l2-fact shape.
    n, n_l2 = 200, 100
    manifest_facts = entailment_gold.load_l2_harvest()["facts"]
    pairs = []
    for i in range(n):
        if i < n_l2:
            row = manifest_facts[i % len(manifest_facts)]
            pairs.append({
                "id": f"eg-{i:04d}",
                "premise": row["fact"],
                "hypothesis": f"Blind fixture hypothesis {i} restates the fact.",
                "verdict": "entailed",
                "slice_tags": ["verbatim"],
                "provenance": "l2-fact",
                "label_source": "adjudicated",
                "rationale": "synthetic eligibility fixture",
                "fact_key": {
                    field: row[field]
                    for field in entailment_gold.FACT_KEY_FIELDS
                },
            })
            continue
        # The synthetic half carries all three verdict classes. An all-entailed
        # gold made a *correct* judge emit one class, which the runner's gold
        # backstop rejects outright -- so this fixture could only ever be driven
        # by a judge that was wrong somewhere.
        verdict = ("entailed", "contradicted", "unsupported")[i % 3]
        # Each verdict needs a slice that admits it -- the loader refuses a
        # `verbatim` contradiction outright.
        slice_tag = {"entailed": "verbatim", "contradicted": "value-swap",
                     "unsupported": "unrelated"}[verdict]
        hypothesis = {
            "entailed": f"Value {i} is held by synthetic fact {i}.",
            "contradicted": f"Synthetic fact {i} holds value {i + 1000}.",
            "unsupported": f"Synthetic fact {i} was reviewed in March.",
        }[verdict]
        pairs.append({
            "id": f"eg-{i:04d}",
            "premise": f"Synthetic fact {i} holds value {i}.",
            "hypothesis": hypothesis,
            "verdict": verdict,
            "slice_tags": [slice_tag],
            "provenance": "hand-authored-synthetic-fact",
            "label_source": "adjudicated",
            "rationale": "synthetic eligibility fixture",
        })
    doc = {
        "version": 99,
        "variant": "claim-fact",
        "declared_slice_counts": {
            sl: sum(1 for p in pairs if sl in p["slice_tags"])
            for sl in entailment_gold.SLICES
        },
        "declared_verdict_counts": {v: sum(1 for p in pairs if p["verdict"] == v)
                                    for v in entailment_gold.VERDICTS},
        "declared_provenance_counts": {
            "l2-fact": n_l2,
            "hand-authored-synthetic-fact": n - n_l2,
            "hand-authored-bench-corpus": 0,
            "synthesis-draft": 0,
        },
        # An eligible gold must now carry a certified resample: Layer 3's
        # n = 93 / <= 1 disagreement is what measures label accuracy, and the
        # lock enforces it since 2026-08-06. Since T2.116 the block must also
        # name the pairs it certified, so it is built from them.
        "resample": _certified_resample(pairs),
        "pairs": pairs,
    }
    path = tmp_path / "eligible_gold.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_fixture_stage_failure_aborts_before_any_gold_contact(tmp_path):
    stub_cls, seen = make_stub(lambda _u: "garbage with no verdict token")
    with pytest.raises(RuntimeError, match="fixture"):
        _run(tmp_path, stub_cls)
    assert seen, "the fixture stage must have probed"
    assert {_premise_of(u) for u in seen} <= SANITY_PREMISES
    assert not (tmp_path / "reports").exists() or not list((tmp_path / "reports").iterdir())
    assert not (tmp_path / "ledger.jsonl").exists()


def test_single_class_collapse_on_fixtures_also_aborts(tmp_path):
    stub_cls, seen = make_stub(
        lambda _u: json.dumps({"verdict": "entailed", "reason": "always"})
    )
    with pytest.raises(RuntimeError, match="fixture"):
        _run(tmp_path, stub_cls)
    assert {_premise_of(u) for u in seen} <= SANITY_PREMISES


def test_happy_path_two_ledger_rows_and_report(tmp_path):
    stub_cls, seen = make_stub(cycling_script())
    result = _run(tmp_path, stub_cls)

    rows = ledger.read_runs(tmp_path / "ledger.jsonl")
    assert len(rows) == 2
    intent, scored = rows
    assert intent["kind"] == "judge_qualification_attempt"
    assert scored["kind"] == "judge_qualification"
    assert scored["intent_row_id"] == intent["intent_row_id"]
    assert scored["gold_touching_attempts"] == 1
    for role in vj.JUDGE_ROLES:
        assert not vj.qualification_record_path(role).exists()

    assert result.report_path.exists()
    text = result.report_path.read_text()
    assert "gold_touching_attempts: 1" in text
    assert "INTERIM" in text
    assert "tokens/claim" in text


def test_intent_marker_is_on_disk_before_the_first_gold_call(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    observed = {}

    def script(user):
        if _premise_of(user) not in SANITY_PREMISES:
            observed["rows_at_first_gold_call"] = len(ledger.read_runs(ledger_path))
            raise ConnectionError("transport died on the first gold pair")
        return json.dumps({
            "verdict": next(observed.setdefault("cycle", itertools.cycle(
                sorted(JUDGE_VERDICTS)))), "reason": "stub",
        })

    stub_cls, _seen = make_stub(script)
    with pytest.raises(ConnectionError):
        _run(tmp_path, stub_cls)

    # The write-ahead marker was already durable when the crash hit, so the
    # untidy failure is still counted.
    assert observed["rows_at_first_gold_call"] == 1
    rows = ledger.read_runs(ledger_path)
    assert len(rows) == 1
    assert rows[0]["kind"] == "judge_qualification_attempt"
    assert not (tmp_path / "reports").exists() or not list((tmp_path / "reports").iterdir())


def test_gold_backstop_aborts_leaving_the_intent_row(tmp_path):
    fixture_script = cycling_script()

    def script(user):
        if _premise_of(user) in SANITY_PREMISES:
            return fixture_script(user)
        return "no verdict here"

    stub_cls, _seen = make_stub(script)
    with pytest.raises(RuntimeError, match="backstop"):
        _run(tmp_path, stub_cls)

    rows = ledger.read_runs(tmp_path / "ledger.jsonl")
    assert len(rows) == 1
    assert rows[0]["kind"] == "judge_qualification_attempt"


def test_attempts_count_per_gold_across_identities(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    # Keyed to the fixture gold this run actually contacts. It used to key to
    # the canonical gold, which the runner no longer opens under test.
    gold_path = _write_eligible_gold(tmp_path)
    gold_sha = hashlib.sha256(gold_path.read_bytes()).hexdigest()
    ledger.record({"kind": "judge_qualification_attempt", "intent_row_id": "a1",
                   "identity_hash": "aaaa", "gold_sha256": gold_sha}, path=ledger_path)
    ledger.record({"kind": "judge_qualification_attempt", "intent_row_id": "a2",
                   "identity_hash": "bbbb", "gold_sha256": gold_sha}, path=ledger_path)
    ledger.record({"kind": "judge_qualification_attempt", "intent_row_id": "a3",
                   "identity_hash": "cccc", "gold_sha256": "other"}, path=ledger_path)

    stub_cls, _seen = make_stub(cycling_script())
    result = _run(tmp_path, stub_cls, gold_path=gold_path)

    scored = ledger.read_runs(ledger_path)[-1]
    assert scored["gold_touching_attempts"] == 3
    assert "gold_touching_attempts: 3" in result.report_path.read_text()


# ── the counter keys on the pairs, not the file (T2.116 escalation) ──────


def _attempt(**fields):
    return {"kind": "judge_qualification_attempt", **fields}


def test_a_contact_survives_the_file_moving_under_the_same_pairs():
    """**The case that was actually lost, with its real shas.** T2.116's
    content stamp moved gold.json from 98fc4b49 to 6eadba73 while the pairs
    stayed 4975c5cc. Under the file key the deepseek-v4-flash attempt at
    98fc4b49 stopped counting, so the next G-D run would have reported 0
    contacts for a pair set already measured once.

    This is the regression test for that, and it is written with the
    historical shas rather than synthetic ones because the defect was
    reachable only through a real sequence of events."""
    rows = [_attempt(gold_sha256="98fc4b49", gold_pairs_sha256="4975c5cc",
                     judge_identity={"model": "deepseek-v4-flash"})]

    assert rjq.count_gold_touching_attempts(
        rows, gold_sha256="6eadba73", gold_pairs_sha256="4975c5cc") == 1
    # And the pre-ruling behaviour, for contrast: keyed on the file, it is 0.
    assert sum(1 for r in rows if r.get("gold_sha256") == "6eadba73") == 0


def test_a_different_pair_set_does_not_count_even_at_the_same_file_sha():
    """The other direction: pairs win when recorded. A file sha collision or
    a reused name must not credit a contact with different labels."""
    rows = [_attempt(gold_sha256="6eadba73", gold_pairs_sha256="8e210191")]
    assert rjq.count_gold_touching_attempts(
        rows, gold_sha256="6eadba73", gold_pairs_sha256="4975c5cc") == 0


def test_a_row_predating_the_field_is_still_credited_by_file_sha():
    """An un-backfilled ledger must never *lose* a contact it used to
    count. Under-counting is the one direction an anti-tuning disclosure
    cannot afford, so the two keys are OR'd rather than AND'd."""
    rows = [_attempt(gold_sha256="6eadba73")]              # legacy row
    assert rjq.count_gold_touching_attempts(
        rows, gold_sha256="6eadba73", gold_pairs_sha256="4975c5cc") == 1


def test_the_counter_ignores_rows_that_are_not_attempts():
    rows = [
        _attempt(gold_sha256="x", gold_pairs_sha256="4975c5cc"),
        {"kind": "coverage_distribution", "gold_pairs_sha256": "4975c5cc"},
        {"kind": "judge_qualification_scored", "gold_pairs_sha256": "4975c5cc"},
    ]
    assert rjq.count_gold_touching_attempts(
        rows, gold_sha256="none", gold_pairs_sha256="4975c5cc") == 1


def test_the_backfill_recovers_pair_identity_and_never_invents_it(tmp_path):
    """Evidence recovery, not invention: a row whose gold state is not in
    git history is left alone rather than guessed at."""
    from benchlib import backfill_attempt_pair_hashes as backfill

    real_sha = hashlib.sha256(entailment_gold.GOLD_PATH.read_bytes()).hexdigest()
    ledger_path = tmp_path / "ledger.jsonl"
    ledger.record(_attempt(intent_row_id="known", gold_sha256=real_sha),
                  path=ledger_path)
    ledger.record(_attempt(intent_row_id="unknown", gold_sha256="deadbeef" * 8),
                  path=ledger_path)

    stamped, unresolved = backfill.backfill(ledger_path)
    assert (stamped, unresolved) == (1, 1)

    rows = {r["intent_row_id"]: r for r in ledger.read_runs(ledger_path)}
    # Recovered, and marked as recovered rather than passed off as recorded.
    assert rows["known"]["gold_pairs_sha256"] == entailment_gold.pairs_content_hash(
        entailment_gold.load_entailment_gold()["pairs"])
    assert rows["known"]["gold_pairs_sha256_backfilled"] is True
    # Not invented.
    assert "gold_pairs_sha256" not in rows["unknown"]


def test_gate_mode_refuses_an_ineligible_gold_before_any_call(tmp_path):
    """The refusal must precede every model call, and it must be tested against
    a gold that is *actually* ineligible.

    This used the real gold and passed because the resample had not run. When it
    landed on 2026-08-08 the gold became eligible, the refusal stopped firing,
    and the test drove a stub orchestrator straight through gate mode into
    writing the production qualification record with the stub's own metrics.
    The protection was never the assertion -- it was a data condition that
    expired. So the ineligible gold is now constructed here rather than
    borrowed, and the record path is explicit rather than defaulted.
    """
    doc = json.loads(_write_eligible_gold(tmp_path).read_text(encoding="utf-8"))
    doc.pop("resample", None)          # the one condition, removed deliberately
    gold_path = tmp_path / "no-resample-gold.json"
    gold_path.write_text(json.dumps(doc), encoding="utf-8")

    stub_cls, seen = make_stub(cycling_script())
    with pytest.raises(RuntimeError) as excinfo:
        _run(tmp_path, stub_cls, gate=True, gold_path=gold_path,
             record_dir=tmp_path / "must-not-be-written")
    message = str(excinfo.value)
    assert "resample" in message
    assert seen == [], "eligibility refusal must precede any model call"
    assert not (tmp_path / "must-not-be-written").exists()
    for role in vj.JUDGE_ROLES:
        assert not vj.qualification_record_path(role).exists()


def test_gate_rehearsal_writes_only_a_non_default_record(tmp_path, monkeypatch):
    gold_path = _write_eligible_gold(tmp_path)
    record_dir = tmp_path / "rehearsal-records"
    record_dir.mkdir()
    # A clearing judge: since 2026-08-08 a gate run that misses a bar writes no
    # record at all, so exercising the write path needs one that passes. The
    # runner resolves bars from the code defaults alone, so the owner stating
    # `contradiction_recall_bar` (T2.109) is a committed edit to that dict; it
    # is stood in for here rather than chosen, since the number is theirs.
    monkeypatch.setattr(vj, "VERIFICATION_BAR_DEFAULTS", {
        **vj.VERIFICATION_BAR_DEFAULTS, "contradiction_recall_bar": 0.90,
    })
    stub_cls, _seen = make_stub(perfect_script(gold_path))
    result = _run(tmp_path, stub_cls, gate=True, gold_path=gold_path,
                  record_dir=record_dir)

    # One file per role, because a clearing run clears both roles' bars.
    written = sorted(p.name for p in record_dir.iterdir())
    assert written == sorted(
        f"verification_qualification.{role}.json" for role in vj.JUDGE_ROLES
    )
    for role in vj.JUDGE_ROLES:
        record = json.loads(
            (record_dir / f"verification_qualification.{role}.json").read_text())
        assert record["role"] == role
        assert record["gate_eligible"] is True
        assert record["gold_sha256"] == hashlib.sha256(
            gold_path.read_bytes()).hexdigest()
        assert record["ledger_run_id"] == result.meta["run_id"]

    # The same rehearsal aimed at the real canonical record directory refuses —
    # the minting lock, exercised through the runner surface.
    stub_cls2, _ = make_stub(perfect_script(gold_path))
    with pytest.raises(ValueError):
        _run(tmp_path / "second", stub_cls2, gate=True, gold_path=gold_path,
             record_dir=vj.qualification_record_path(vj.ENTAILMENT_ROLE).parent)
    for role in vj.JUDGE_ROLES:
        assert not vj.qualification_record_path(role).exists()


def test_fixtures_only_never_touches_the_gold(tmp_path):
    stub_cls, seen = make_stub(cycling_script())
    result = _run(tmp_path, stub_cls, fixtures_only=True)
    assert result is None
    assert {_premise_of(u) for u in seen} == SANITY_PREMISES
    assert not (tmp_path / "ledger.jsonl").exists()
    assert not (tmp_path / "reports").exists() or not list((tmp_path / "reports").iterdir())


def test_latency_channels_are_split_fixture_vs_gold(tmp_path):
    stub_cls, _seen = make_stub(cycling_script())
    result = _run(tmp_path, stub_cls)
    fixture = result.twin.channels["fixture_call"]
    gold = result.twin.channels["judge_call"]
    assert fixture.live.n == len(SANITY_PREMISES)
    assert gold.live.n == result.score.n_pairs
    assert result.score.n_pairs > len(SANITY_PREMISES)


# ── the resample condition (T2.54 Step 6, 2026-08-06) ───────────────────


def test_a_gold_without_a_resample_is_refused():
    """The hole this closes: before 2026-08-06 the lock checked size, the
    l2-fact floor and author-labels and nothing else, so a gold whose
    escalations were resolved read as eligible with its label error never
    measured — a policy standing between it and a gate claim that no code
    enforced."""
    eligibility = jq.gate_eligibility(_synthetic_gold(200, 100, 0, resample=None))
    assert eligibility.eligible is False
    assert "resample: absent" in "\n".join(eligibility.reasons)


def test_an_undersized_resample_is_refused():
    small = {**_certified_resample(), "n": jq.RESAMPLE_N - 1}
    eligibility = jq.gate_eligibility(_synthetic_gold(200, 100, 0, resample=small))
    assert eligibility.eligible is False
    assert "below the ratified floor" in "\n".join(eligibility.reasons)


def test_a_resample_over_the_disagreement_bar_is_refused():
    failed = {**_certified_resample(),
              "disagreements": jq.RESAMPLE_MAX_DISAGREEMENTS + 1}
    eligibility = jq.gate_eligibility(_synthetic_gold(200, 100, 0, resample=failed))
    assert eligibility.eligible is False
    assert "exceeds the ratified bar" in "\n".join(eligibility.reasons)


def test_an_uncitable_resample_is_refused():
    """A resample nobody can reproduce or attribute certifies nothing — the
    seed and the performer are what make it a measurement rather than a
    claim."""
    for field in ("seed", "performed_by", "date"):
        anonymous = {**_certified_resample(), field: None}
        eligibility = jq.gate_eligibility(
            _synthetic_gold(200, 100, 0, resample=anonymous)
        )
        assert eligibility.eligible is False, field
        assert f"{field!r} missing" in "\n".join(eligibility.reasons)


def test_the_per_pair_verdict_artifact_is_quarantined_not_committed():
    """T2.115 could not compute the overlap disclosure its plan review
    required, because no artifact joins a pair id to what the judge said: the
    cache is keyed on an identity no run records, and the report withholds the
    per-pair census by design.

    The fix separates the two readers rather than publishing anything. A
    controller needs the join to attribute a re-measure's delta; an author must
    never see it, or the next round's pairs are aimed at the known misses. So
    the artifact lives beside `entailment/cache/` under the same gitignore and
    the same quarantine rule — and this test is what keeps it there, since a
    committed census would be the exact leak the whole firewall exists to stop.
    """
    import pathlib

    from benchlib import run_judge_qualification as rjq

    root = pathlib.Path(__file__).resolve().parents[4]
    ignore = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    rel = "backend/scripts/benchlib/entailment/verdicts/"

    assert rel in ignore, (
        f"{rel} must be gitignored: it holds per-pair judge verdicts, which is "
        "the census the ledger withholds so a future author cannot aim at it"
    )
    # And it is the directory the runner actually writes to, so the ignore rule
    # cannot drift away from the artifact it protects.
    assert rjq.VERDICTS_DIR.name == "verdicts"
    assert rjq.VERDICTS_DIR.parent.name == "entailment"


def test_a_completed_run_never_writes_into_the_real_verdicts_directory(
    tmp_path, monkeypatch,
):
    """T2.122: the module-level ``VERDICTS_DIR`` constant used to be read
    directly at the write site with no override, so any test that drove
    ``run_qualification`` to scoring completion wrote a per-pair verdict
    file into the live, gitignored artifact directory under a real judge
    identity -- 79 such files accumulated there across three days before
    this was caught.

    Stands the module constant in for "the real directory": if the writer
    ever goes back to reading it directly instead of the ``verdicts_dir``
    parameter ``_run`` overrides, a real-looking file lands here and this
    test fails.
    """
    canary = tmp_path / "would-be-the-real-directory"
    monkeypatch.setattr(rjq, "VERDICTS_DIR", canary)

    stub_cls, _seen = make_stub(cycling_script())
    result = _run(tmp_path, stub_cls)

    assert not canary.exists(), (
        "run_qualification wrote into VERDICTS_DIR directly instead of the "
        "verdicts_dir override -- this is the T2.122 leak"
    )
    written = list((tmp_path / "verdicts").glob("*.json"))
    assert len(written) == 1
    assert result.report_path.exists()


# ── census independence is disclosed, not discovered in review ───────────


def test_the_live_gold_discloses_its_contradicted_census_independence():
    """The 2026-08-10 attempt was spent against 80 contradicted rows over 78
    independent propositions and no artifact said so; the finding arrived in
    review, after the attempt was gone. This is that disclosure, and on the
    round-4 gold it discloses a clean census: 80 rows, 80 propositions, no
    duplicate at the bytes.

    Kept asserting the *disclosure* rather than deleted now the number is
    clean. A census that silently reacquired a duplicate would otherwise be
    caught by nothing on this path, and the class this is about — a spent
    attempt with the finding arriving afterwards — is not one a passing round
    retires."""
    from benchlib.tests.test_entailment_gold import DOCUMENTED_VERDICT_COUNTS

    doc = entailment_gold.load_entailment_gold()
    live = [p for p in doc["pairs"] if not p.get("retired")]

    ci = jq.census_independence(live, "contradicted", 0.95)
    assert ci["rows"] == DOCUMENTED_VERDICT_COUNTS["contradicted"]
    assert ci["independent_propositions"] == ci["rows"]
    assert ci["duplicate_pairs"] == []


def test_a_three_row_duplicate_component_collapses_two_rows_not_three():
    """Rows collapse by connected component, not by finding. Three mutually
    duplicate rows yield three pairwise findings and collapse two rows; the
    original arithmetic subtracted the finding count and printed one
    proposition fewer than exist (T2.118 found exactly this shape in the
    entailed census, which is the class R2's mint re-scores)."""
    pairs = [
        {"id": "d-0001", "verdict": "contradicted",
         "premise": "shared", "hypothesis": "the service runs on port 8000"},
        {"id": "d-0002", "verdict": "contradicted",
         "premise": "shared", "hypothesis": "the service runs on port 8000"},
        {"id": "d-0003", "verdict": "contradicted",
         "premise": "shared", "hypothesis": "the service runs on port 8000"},
    ] + [
        {"id": f"u-{i:04d}", "verdict": "contradicted",
         "premise": f"p{i}", "hypothesis": f"h{i}"}
        for i in range(7)
    ]

    ci = jq.census_independence(pairs, "contradicted", 0.95)
    assert len(ci["duplicate_pairs"]) == 3, "three rows make three pairwise findings"
    assert ci["rows"] == 10
    assert ci["independent_propositions"] == 8, "k rows collapse to one, not zero"


def test_the_entailed_census_prints_its_true_proposition_count():
    """T2.118 measured the retired set's 173 entailed rows over 167
    independent propositions: five duplicate components, one of them three
    wide, collapsing six rows, where the finding-count arithmetic printed 166.

    Round 4's entailed census carries no *byte-level* duplicate at all. It is
    not duplicate-free: nine components were found by adjudication, which
    Jaccard cannot see, and they are asserted through the sidecar below. This
    test is the byte-level reading, and asserting it separately is what keeps
    the two sources distinguishable — a sidecar that silently emptied would
    otherwise look like a clean census here."""
    from benchlib.tests.test_entailment_gold import DOCUMENTED_VERDICT_COUNTS

    doc = entailment_gold.load_entailment_gold()
    live = [p for p in doc["pairs"] if not p.get("retired")]

    ci = jq.census_independence(live, "entailed", 0.90)
    assert ci["rows"] == DOCUMENTED_VERDICT_COUNTS["entailed"]
    assert ci["duplicate_pairs"] == [], "no duplicate is visible at the bytes"


def test_it_reports_the_effective_bar_on_both_readings():
    """Both readings, reported whether or not they differ.

    On the retired set the gap ran the dangerous way — 0.95 exactly on rows,
    0.9615 on independent propositions, so a census with duplicates was
    *easier* than the bar it claimed to enforce. Round 4's contradicted census
    holds no duplicate, so the two readings coincide at 76/80 and the gap is
    zero. The report still prints both, and this asserts both: a gold that
    reacquired a duplicate would move the second number, and a reading that
    stopped being computed would be the failure this pin exists for.

    76 is derived, not chosen: 0.95 * 80 = 76 exactly, which is why the frame
    sized the census as a multiple of 20 (T2.110)."""
    import math

    from benchlib.tests.test_entailment_gold import DOCUMENTED_VERDICT_COUNTS

    census = DOCUMENTED_VERDICT_COUNTS["contradicted"]
    min_passing = math.ceil(0.95 * census)

    doc = entailment_gold.load_entailment_gold()
    live = [p for p in doc["pairs"] if not p.get("retired")]

    ci = jq.census_independence(live, "contradicted", 0.95)
    assert (ci["min_passing_rows"], ci["effective_bar_on_rows"]) == (
        min_passing, 0.95
    )
    assert ci["min_passing_independent"] == ci["min_passing_rows"]
    assert ci["effective_bar_on_independent"] == ci["effective_bar_on_rows"]
    assert ci["bar_expressible_on_rows"] is True


def test_a_census_whose_bar_is_not_expressible_says_so():
    """Quantisation makes a stated bar unreachable at some census sizes, and
    the effective bar is then one nobody argued for. 0.95 over 78 rows needs
    75, which is 0.9615."""
    pairs = [
        {"id": f"x-{i:04d}", "verdict": "contradicted",
         "premise": f"p{i}", "hypothesis": f"h{i}"}
        for i in range(78)
    ]
    ci = jq.census_independence(pairs, "contradicted", 0.95)
    assert ci["rows"] == ci["independent_propositions"] == 78
    assert ci["bar_expressible_on_rows"] is False
    assert ci["effective_bar_on_independent"] == 0.9615


def test_the_disclosure_cannot_be_a_function_of_judge_performance():
    """Reports, never judges — asserted on the interface rather than on the
    source text, because a docstring mentioning "score" is not a defect and
    a grep for it is the source-inspection shape this corpus keeps finding.

    The property is structural: no judge output can reach this function,
    because there is no parameter it could arrive through."""
    import inspect
    params = list(inspect.signature(jq.census_independence).parameters)
    assert params == ["pairs", "verdict", "bar"]

    # And it is deterministic on its inputs alone.
    doc = entailment_gold.load_entailment_gold()
    live = [p for p in doc["pairs"] if not p.get("retired")]
    assert jq.census_independence(live, "contradicted", 0.95) == \
        jq.census_independence(live, "contradicted", 0.95)


def _census_with_two_duplicates():
    """80 contradicted rows over 78 propositions, built through the real
    finder rather than hand-asserted, so the fixture cannot drift from the
    shape `census_independence` actually returns."""
    pairs = [
        {"id": f"c-{i:04d}", "verdict": "contradicted",
         "premise": f"subject{i} relates object{i}", "hypothesis": f"claim {i} holds"}
        for i in range(76)
    ]
    for n in (0, 1):
        pairs.append({"id": f"d-{n}a", "verdict": "contradicted",
                      "premise": f"dup{n} has part widget",
                      "hypothesis": f"The widget has dup{n} as a part."})
        pairs.append({"id": f"d-{n}b", "verdict": "contradicted",
                      "premise": f"dup{n} has part widget",
                      "hypothesis": f"dup{n} is a part of the widget."})
    return pairs


def test_a_row_pass_the_independence_reading_would_fail_is_flagged():
    """The owner's 2026-08-12 ruling kept the duplicates and handled
    independence by reporting, which puts the ruling's whole weight on this
    line existing. 76/80 clears 0.95 on rows; if the judge caught both
    correlated pairs the independent reading is 74/78 = 0.9487, below it."""
    ci = jq.census_independence(_census_with_two_duplicates(), "contradicted", 0.95)
    score = jq.QualificationScore(
        n_pairs=402, invalid=0, confusion={}, entailed_precision=1.0,
        entailed_recall=1.0, contradiction_precision=1.0,
        contradiction_recall=76 / 80, per_slice={}, majority_class_floor=0.5,
    )
    text = jq.render_report(
        score, jq.gate_eligibility(_synthetic_gold(200, 100, 0)), _mini_twin(),
        _mini_meta(census_independence=ci),
    )
    assert "not robust to the independence reading" in text
    assert "74/78" in text and "0.9487" in text


def test_a_comfortable_pass_is_not_flagged():
    """The warning has to be selective or it is noise: 80/80 survives the
    independent reading at 78/78 and must not carry the caveat."""
    ci = jq.census_independence(_census_with_two_duplicates(), "contradicted", 0.95)
    score = jq.QualificationScore(
        n_pairs=402, invalid=0, confusion={}, entailed_precision=1.0,
        entailed_recall=1.0, contradiction_precision=1.0,
        contradiction_recall=1.0, per_slice={}, majority_class_floor=0.5,
    )
    text = jq.render_report(
        score, jq.gate_eligibility(_synthetic_gold(200, 100, 0)), _mini_twin(),
        _mini_meta(census_independence=ci),
    )
    assert "Census independence" in text            # still disclosed
    assert "not robust to the independence reading" not in text


# ── the stopping rule binds pairs, not only the set they arrived in ──────


def _retired_gold_path():
    """Where the retired pair set lives: the D1 archive once it exists, the
    canonical path only in pre-archive tree states. Every test about the
    4975c5cc stopping rule reads through this, so none of them starts
    asserting facts about whatever fresh gold later holds the canonical
    path."""
    path = entailment_gold.RETIRED_GOLD_ARCHIVE_PATH
    return path if path.exists() else entailment_gold.GOLD_PATH


def _retired_gold_pairs():
    """The retired pairs, raw ``json.loads`` and not ``load_entailment_gold``:
    the archive is an audit copy pinned by content digests, and running the
    validating loader on it would couple the pin to the *live* harvest
    manifest, a file the archive predates."""
    return json.loads(_retired_gold_path().read_text(encoding="utf-8"))["pairs"]


def test_appending_one_pair_does_not_un_retire_a_gold():
    """The bypass, demonstrated live during T2.117's review: appending one
    synthetic pair moves the set hash off `4975c5cc` while leaving every
    retired pair contactable. Set identity is not pair identity."""
    import copy
    from benchlib import run_judge_qualification as rjq

    mutated = copy.deepcopy(_retired_gold_pairs()) + [{
        "id": "zz-9999", "verdict": "entailed",
        "premise": "a pair nobody has judged", "hypothesis": "and nobody will",
    }]
    assert not vj.is_retired_pair_set(
        entailment_gold.pairs_content_hash(mutated)
    ), "the set hash really does move — that is what makes this a bypass"

    with pytest.raises(RuntimeError, match="retired pairs by content"):
        rjq.refuse_retired_pair_set({"pairs": mutated})


def test_a_retired_pair_under_a_new_id_is_still_retired():
    """The digest basis excludes the id on purpose. This census has twice
    reproduced a retired pair's exact premise and hypothesis under a new id
    (eg-0367, eg-0404), so keying on the id would retire a label rather than
    a pair."""
    import copy
    from benchlib import run_judge_qualification as rjq

    renamed = copy.deepcopy(_retired_gold_pairs()[0])
    renamed["id"] = "renamed-0001"
    assert entailment_gold.retired_pair_overlap([renamed]) == {"renamed-0001"}

    with pytest.raises(RuntimeError, match="retired pairs by content"):
        rjq.refuse_retired_pair_set({"pairs": [renamed]})


def test_a_genuinely_fresh_gold_is_not_refused():
    """The control. A refusal that fires on everything protects nothing and
    would block T2.124, which is the whole remaining path."""
    from benchlib import run_judge_qualification as rjq

    fresh = [
        {"id": f"nw-{i:04d}", "verdict": "entailed",
         "premise": f"a premise nobody has authored before, {i}",
         "hypothesis": f"and its hypothesis, {i}"}
        for i in range(5)
    ]
    assert entailment_gold.retired_pair_overlap(fresh) == set()
    rjq.refuse_retired_pair_set({"pairs": fresh})


def test_the_pinned_digest_file_describes_the_retired_gold():
    """The pin is only as good as its provenance: it must name the pair set it
    was taken from, and cover every pair in it.

    The last three assertions are the A2 repair (T2.124): before them the
    embedded ``count`` and ``pairs_content_hash`` were checked nowhere, and
    the coverage assertion below stopped referencing the retired pairs the
    moment the archive left the canonical path -- so a truncation of the
    digest list would have silently disarmed 414 of 415 content refusals.
    """
    raw = json.loads(entailment_gold.RETIRED_DIGESTS_PATH.read_text(encoding="utf-8"))
    assert vj.is_retired_pair_set(raw["pairs_content_hash"])
    assert raw["digest_basis"] == list(entailment_gold.RETIRED_DIGEST_FIELDS)
    pairs = _retired_gold_pairs()
    assert entailment_gold.retired_pair_overlap(pairs) == {
        pair["id"] for pair in pairs
    }, "every pair of the retired gold must be recognised as retired"

    assert raw["count"] == len(raw["digests"]) == len(set(raw["digests"]))
    assert set(raw["digests"]) == {
        entailment_gold.content_digest(pair) for pair in pairs
    }, "the digest list must be exactly the archived pairs' content digests"
    assert entailment_gold.pairs_content_hash(pairs) == raw["pairs_content_hash"], (
        "the named pair set must be derivable from the archived file's live "
        "pairs -- the pin's provenance claim, checked rather than asserted"
    )


def test_a_truncated_digest_list_refuses_rather_than_disarming(tmp_path, monkeypatch):
    """Removing entries from the pinned digest list must raise, never shrink
    the refusal's reach: 'count' is load-bearing only because this check
    exists, and this test fails if the check is removed."""
    raw = json.loads(entailment_gold.RETIRED_DIGESTS_PATH.read_text(encoding="utf-8"))
    raw["digests"] = raw["digests"][:1]
    truncated = tmp_path / "retired_pair_digests.json"
    truncated.write_text(json.dumps(raw), encoding="utf-8")
    monkeypatch.setattr(entailment_gold, "RETIRED_DIGESTS_PATH", truncated)
    entailment_gold.retired_pair_digests.cache_clear()
    try:
        with pytest.raises(ValueError, match="truncated or padded"):
            entailment_gold.retired_pair_digests()
    finally:
        entailment_gold.retired_pair_digests.cache_clear()


# ── the adjudication sidecar (T2.124 step 9) ─────────────────────────────────
#
# Content-token Jaccard cannot separate a duplicate proposition from a lawful
# near-miss: on the round-4 census a recorded duplicate and an owner-ruled
# lawful pair both score 0.2857. So `census_independence` unions human-tier
# verdicts, and reports a range where the adjudicators split rather than
# picking a side.

def test_an_absent_sidecar_is_lawful_and_degrades_to_the_jaccard_reading(tmp_path):
    """Every tree before step 9 was in this state; it must not raise."""
    empty = jq.load_adjudicated_duplicates(tmp_path / "nope.json")
    assert empty == {"confirmed_duplicates": [], "contested": []}


def test_a_malformed_sidecar_raises_rather_than_silently_restoring_the_overcount(tmp_path):
    bad = tmp_path / "adjudicated.json"
    bad.write_text(json.dumps({"confirmed_duplicates": [{"left": "eg-0001"}]}))
    with pytest.raises(ValueError, match="needs 'left' and 'right'"):
        jq.load_adjudicated_duplicates(bad)

    worse = tmp_path / "worse.json"
    worse.write_text(json.dumps({"contested": "eg-0001,eg-0002"}))
    with pytest.raises(ValueError, match="must be a list"):
        jq.load_adjudicated_duplicates(worse)


def test_the_committed_sidecar_collapses_the_entailed_census():
    """The number this function used to report, and the one it reports now.

    The sidecar was written at step 9, against the census as authored: 14
    components — 8 by unanimous blind adjudication, 6 by the owner's
    2026-08-14 ruling that the opposite-slot precedent does not reach a
    one-directional generalisation — collapsing the entailed census from 110
    rows to 96 propositions.

    Steps 10 and 11 then retired one member of five of those components, and
    `census_independence` reads the sidecar **against the live set**, so a
    component with a retired member stops collapsing anything. That is the
    correct reading and not an erosion of the disclosure: the row it would
    have collapsed is gone from the census too. The sidecar is left intact as
    the step-9 adjudication record — pruning it would delete the audit trail
    of decisions that were made — so the arithmetic below is stated as the
    relation between the two rather than as two independent numbers.
    """
    from benchlib.tests.test_entailment_gold import DOCUMENTED_VERDICT_COUNTS

    doc = entailment_gold.load_entailment_gold()
    live = [
        p for p in doc["pairs"]
        if not ("retired" in p or p.get("retirement_kind"))
    ]
    live_ids = {p["id"] for p in live}
    ci = jq.census_independence(live, "entailed", 0.90)

    # Jaccard alone finds nothing here — which is the whole point.
    assert ci["duplicate_pairs"] == []

    sidecar = jq.load_adjudicated_duplicates()
    recorded = sidecar["confirmed_duplicates"]
    assert len(recorded) == 14, "the step-9 record is 14 components, unpruned"
    still_live = [
        e for e in recorded
        if e["left"] in live_ids and e["right"] in live_ids
    ]
    assert len(ci["adjudicated_duplicate_pairs"]) == len(still_live)
    assert ci["contested_pairs"] == []

    rows = DOCUMENTED_VERDICT_COUNTS["entailed"]
    assert ci["rows"] == rows
    # Every surviving component is a disjoint pair, so each collapses one row.
    assert ci["independent_propositions"] == rows - len(still_live)
    assert ci["independent_propositions_range"] == [
        ci["independent_propositions"], ci["independent_propositions"]
    ]
    assert ci["independence_contested"] is False
    low, high = ci["effective_bar_on_independent_range"]
    assert low >= 0.90 and high >= 0.90


def test_the_contradicted_census_is_untouched_by_the_sidecar():
    """The class carrying the harder bar has no adjudicated duplicate at all."""
    doc = entailment_gold.load_entailment_gold()
    live = [
        p for p in doc["pairs"]
        if not ("retired" in p or p.get("retirement_kind"))
    ]
    ci = jq.census_independence(live, "contradicted", 0.95)
    assert ci["rows"] == 80
    assert ci["independent_propositions"] == 80
    assert ci["independent_propositions_range"] == [80, 80]
    assert ci["independence_contested"] is False
    assert ci["adjudicated_duplicate_pairs"] == []


def test_the_renderer_never_prints_a_count_with_an_empty_pair_list():
    """The regression this wiring could most easily introduce.

    `independent_propositions` now collapses on a source `duplicate_pairs` does
    not carry, so a note built from that key alone reads "8 duplicated
    proposition(s): []".
    """
    doc = entailment_gold.load_entailment_gold()
    live = [
        p for p in doc["pairs"]
        if not ("retired" in p or p.get("retirement_kind"))
    ]
    ci = jq.census_independence(live, "entailed", 0.90)
    collapsing = ci["duplicate_pairs"] + ci["adjudicated_duplicate_pairs"]
    assert len(collapsing) == ci["rows"] - ci["independent_propositions"]
    assert collapsing, "a non-zero collapse must name the pairs that caused it"


# ── T2.124 step 13: the disclosure is owed for BOTH gated classes ─────────


def _independent_census(verdict, n):
    """`n` rows of `verdict`, every one a distinct proposition."""
    return [
        {"id": f"{verdict[:3]}-{i:04d}", "verdict": verdict,
         "premise": f"subject{i} relates object{i}",
         "hypothesis": f"a distinct claim about subject{i} number {i}"}
        for i in range(n)
    ]


def test_the_runner_discloses_the_census_for_both_gated_classes():
    """Derived from the runner's own AST, not from a copy of its literal.

    The done-when asks for the disclosure for both classes because the two
    roles are gated on different numbers: `contradiction` on
    contradiction-recall, `entailment` on the entailed pair. A runner
    disclosing only the contradicted census tells the entailment role's
    reader nothing about the census their bar is applied to — and until
    T2.124 step 13 that is exactly what it did. Asserted structurally so a
    future edit that drops one class fails here rather than shipping a
    half-disclosure that still renders cleanly.
    """
    import ast

    tree = ast.parse(
        pathlib.Path(rjq.__file__).read_text(encoding="utf-8")
    )
    disclosed = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value == "census_independence":
                disclosed = value
    assert disclosed is not None, "the runner no longer builds census_independence"
    assert isinstance(disclosed, ast.List), (
        "census_independence must be a LIST of per-class disclosures; a bare "
        "call can only ever carry one class"
    )
    classes = {
        arg.value
        for call in disclosed.elts
        if isinstance(call, ast.Call)
        for arg in call.args
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
    }
    assert classes == set(jq.CENSUS_RECALL_ATTRS), (
        f"the runner discloses {sorted(classes)} but CENSUS_RECALL_ATTRS gates "
        f"{sorted(jq.CENSUS_RECALL_ATTRS)} -- every class whose recall a bar "
        f"reads must be disclosed"
    )


def test_both_classes_render_their_own_reading_under_their_own_heading():
    """Two classes, two sections, each naming the class it describes.

    The hazard the heading closes: one class's measured recall rendered under
    the other's name reads as a disclosure while being a mis-attribution, and
    the numbers are close enough that nothing downstream would catch it.
    """
    census = [
        jq.census_independence(_census_with_two_duplicates(), "contradicted", 0.95),
        jq.census_independence(_independent_census("entailed", 40), "entailed", 0.90),
    ]
    score = jq.QualificationScore(
        n_pairs=402, invalid=0, confusion={}, entailed_precision=1.0,
        entailed_recall=1.0, contradiction_precision=1.0,
        contradiction_recall=76 / 80, per_slice={}, majority_class_floor=0.5,
    )
    text = jq.render_report(
        score, jq.gate_eligibility(_synthetic_gold(200, 100, 0)), _mini_twin(),
        _mini_meta(census_independence=census),
    )
    assert "Census independence (contradicted)" in text
    assert "Census independence (entailed)" in text
    assert "contradicted-recall" in text
    # The contradicted class carries the duplicates, so only it is flagged.
    assert "not robust to the independence reading" in text
    assert text.count("not robust to the independence reading") == 1


def test_a_rows_equal_propositions_census_says_so_rather_than_going_silent():
    """Silence and independence must not render alike.

    A reader meeting no section cannot tell "this census is independent" from
    "nobody computed the disclosure" — and the second is precisely what the
    2026-08-10 attempt suffered, discovered only in review after the attempt
    was spent.
    """
    census = [jq.census_independence(_independent_census("entailed", 40), "entailed", 0.90)]
    score = jq.QualificationScore(
        n_pairs=40, invalid=0, confusion={}, entailed_precision=1.0,
        entailed_recall=1.0, contradiction_precision=1.0,
        contradiction_recall=1.0, per_slice={}, majority_class_floor=0.5,
    )
    text = jq.render_report(
        score, jq.gate_eligibility(_synthetic_gold(200, 100, 0)), _mini_twin(),
        _mini_meta(census_independence=census),
    )
    assert "Census independence (entailed) — rows == propositions" in text
    assert "no independence reading is owed" in text


def test_a_three_wide_component_collapses_two_rows_not_three_findings():
    """T2.123's arithmetic, pinned on a synthetic census.

    A component of k mutually-duplicate rows yields k(k-1)/2 findings and
    collapses k-1 rows. The sibling pin reads the live gold and therefore
    moves whenever the gold's composition does; this one cannot, so the
    arithmetic stays guarded across a gold swap.
    """
    pairs = _independent_census("entailed", 10)
    for suffix, hypothesis in (
        ("a", "The widget has tri as a part."),
        ("b", "tri is a part of the widget."),
        ("c", "tri is part of the widget."),
    ):
        pairs.append({
            "id": f"tri-{suffix}", "verdict": "entailed",
            "premise": "tri has part widget", "hypothesis": hypothesis,
        })
    ci = jq.census_independence(pairs, "entailed", 0.90)
    assert ci["rows"] == 13
    # Three findings over one three-wide component, but only two rows collapse.
    assert len(ci["duplicate_pairs"]) == 3
    assert ci["independent_propositions"] == 11

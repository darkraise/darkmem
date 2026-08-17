"""TH1.17 — the faithfulness-gate scoring module. Exercised entirely
against ``fixtures/faithfulness_gate_fixture.py``, a **fixture**, never the
real claim/span entailment gold (which does not exist yet — TH1.01 §5)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchlib import faithfulness_gate as fg
from benchlib.tests.fixtures import faithfulness_gate_fixture as fx

from app.services import faithfulness_bars as fb
from app.services.verification_judge import ProbeVerdict

PAIRS = fx.build_fixture_pairs()
# The committed harvest manifest the fixture's anchors resolve against. Anchors
# index into a block's own text (the runtime's basis), so resolution needs the
# manifest rather than a directory of documents.
MANIFEST = fg.load_span_manifest(fx.MANIFEST_PATH)


def _verdict(verdict: str, *, valid: bool = True) -> ProbeVerdict:
    return ProbeVerdict(verdict=verdict, reason="stub", raw="{}", valid=valid)


def _judge_verdict_for(gold_verdict: str) -> str:
    # The judge itself always returns one of the three JUDGE_VERDICTS; a
    # perfect judge on a "not-entailed" gold pair answers "unsupported" (the
    # generic ungrounded case), never a bare "not-entailed" -- that string
    # is this gold's vocabulary, not the judge's.
    return "entailed" if gold_verdict == "entailed" else "unsupported"


def perfect_verdicts(pairs) -> dict[str, ProbeVerdict]:
    return {p["id"]: _verdict(_judge_verdict_for(p["verdict"])) for p in pairs}


# ── the gold loader: absence is reported, never silently empty ──────────


def test_load_span_gold_raises_when_absent(tmp_path):
    missing = tmp_path / "span_gold.json"
    with pytest.raises(fg.SpanGoldAbsent) as excinfo:
        fg.load_span_gold(missing)
    assert excinfo.value.path == missing


def test_load_span_gold_validates_every_pair(tmp_path):
    bad = tmp_path / "span_gold.json"
    bad.write_text(json.dumps({"pairs": [
        {"id": "x", "verdict": "maybe", "provenance": "hand-authored-fixture-span",
         "premise_spans": [{"document_uri": "a", "block_key": "b0",
                             "text_sha256": "c", "char_span": [0, 1]}]},
    ]}))
    with pytest.raises(ValueError, match="verdict"):
        fg.load_span_gold(bad)


# ── m2: hardening -- missing 'pairs', ids, answer_id/hypothesis ─────────────


def _valid_pair(**overrides) -> dict:
    base = {
        "id": "x",
        "answer_id": "ans-1",
        "hypothesis": "some claim",
        "verdict": "entailed",
        "provenance": "hand-authored-fixture-span",
        "slice_tags": ["verbatim"],
        "premise_spans": [{"document_uri": "a", "block_key": "b0",
                            "text_sha256": "c", "char_span": [0, 1]}],
    }
    base.update(overrides)
    return base


def test_load_span_gold_refuses_a_document_with_no_pairs_key(tmp_path):
    """The reproduced defect: a gold missing 'pairs' entirely used to
    KeyError as a raw traceback at the run_faithfulness_gate.py call site
    rather than a readable message from the loader itself."""
    doc = tmp_path / "span_gold.json"
    doc.write_text(json.dumps({"not_pairs": []}))
    with pytest.raises(ValueError, match="pairs"):
        fg.load_span_gold(doc)


def test_load_span_gold_refuses_a_pair_with_no_id(tmp_path):
    doc = tmp_path / "span_gold.json"
    pair = _valid_pair()
    del pair["id"]
    doc.write_text(json.dumps({"pairs": [pair]}))
    with pytest.raises(ValueError, match="id"):
        fg.load_span_gold(doc)


def test_load_span_gold_refuses_a_duplicate_id(tmp_path):
    """The silent-corruption mutation: a duplicate id must be refused, not
    silently overwrite an earlier verdict and double-count a slice."""
    doc = tmp_path / "span_gold.json"
    doc.write_text(json.dumps({"pairs": [
        _valid_pair(id="dup"), _valid_pair(id="dup"),
    ]}))
    with pytest.raises(ValueError, match="duplicate"):
        fg.load_span_gold(doc)


def test_load_span_gold_refuses_a_pair_with_no_answer_id(tmp_path):
    doc = tmp_path / "span_gold.json"
    pair = _valid_pair()
    del pair["answer_id"]
    doc.write_text(json.dumps({"pairs": [pair]}))
    with pytest.raises(ValueError, match="answer_id"):
        fg.load_span_gold(doc)


def test_load_span_gold_refuses_a_pair_with_no_hypothesis(tmp_path):
    doc = tmp_path / "span_gold.json"
    pair = _valid_pair()
    del pair["hypothesis"]
    doc.write_text(json.dumps({"pairs": [pair]}))
    with pytest.raises(ValueError, match="hypothesis"):
        fg.load_span_gold(doc)


def test_load_span_gold_accepts_a_well_formed_document(tmp_path):
    doc = tmp_path / "span_gold.json"
    doc.write_text(json.dumps({"pairs": [_valid_pair()]}))
    loaded = fg.load_span_gold(doc)
    assert len(loaded["pairs"]) == 1


# ── pair-shape validation ────────────────────────────────────────────────


def _pair(**overrides):
    base = {
        "id": "p1",
        "verdict": "entailed",
        "provenance": "hand-authored-fixture-span",
        # Required since 2026-08-17: a pair with no slice_tags used to score
        # into the aggregate and into no slice, hiding itself from every
        # per-slice number. Every real fixture pair already carried it; only
        # this minimal helper did not, which is why the hole survived.
        "slice_tags": ["verbatim"],
        "premise_spans": [{"document_uri": "a", "block_key": "b0",
                            "text_sha256": "c", "char_span": [0, 1]}],
    }
    base.update(overrides)
    return base


def test_validate_pair_shape_rejects_bad_verdict():
    with pytest.raises(ValueError, match="verdict"):
        fg.validate_pair_shape(_pair(verdict="entailedd"))


def test_validate_pair_shape_rejects_unknown_provenance():
    with pytest.raises(ValueError, match="provenance"):
        fg.validate_pair_shape(_pair(provenance="vibes"))


@pytest.mark.parametrize("provenance", ["document-span", "qa-draft"])
def test_real_provenances_are_accepted_since_the_owner_ruled(provenance):
    """The owner ruled 2026-08-17: the gold uses real block spans and QA drafts.

    This replaces a test that parametrized over ``RESERVED_ZERO_PROVENANCE`` and
    asserted each value was refused. Emptying that set to lift the reservation
    would have left that test generating **zero cases and passing vacuously** —
    green while asserting nothing, the same shape as a suite that never signs
    in. So the assertion is inverted rather than deleted: the two values a
    reservation used to forbid are now positively required to load.
    """
    fg.validate_pair_shape(_pair(provenance=provenance))  # must not raise


def test_nothing_is_reserved_at_zero_any_more():
    # A non-empty set here means someone re-reserved a provenance; the ruling
    # that lifted it is the owner's, so re-reserving is theirs too.
    assert fg.RESERVED_ZERO_PROVENANCE == frozenset()


def test_validate_pair_shape_rejects_empty_premise_spans():
    with pytest.raises(ValueError, match="no premise spans"):
        fg.validate_pair_shape(_pair(premise_spans=[]))


# ── slice_tags: the field nothing used to check ───────────────────────────


def test_validate_pair_shape_rejects_missing_slice_tags():
    """The load-bearing one. A pair with no ``slice_tags`` scored into the
    aggregate and into no slice at all, so it was invisible in every per-slice
    number while still moving the headline — ledger rule 4's collapse, arriving
    through a hole rather than a decision."""
    pair = _pair()
    del pair["slice_tags"]
    with pytest.raises(ValueError, match="slice_tags"):
        fg.validate_pair_shape(pair)


@pytest.mark.parametrize("bad", [[], "verbatim", None, {}])
def test_validate_pair_shape_rejects_non_list_or_empty_slice_tags(bad):
    # A bare string is the subtle one: `for tag in "verbatim"` iterates
    # characters, so it would have minted eight single-letter phantom slices.
    with pytest.raises(ValueError, match="slice_tags"):
        fg.validate_pair_shape(_pair(slice_tags=bad))


@pytest.mark.parametrize("bad", ["", "   ", 7])
def test_validate_pair_shape_rejects_a_blank_or_non_string_tag(bad):
    with pytest.raises(ValueError, match="slice tag"):
        fg.validate_pair_shape(_pair(slice_tags=[bad]))


def test_every_scored_pair_lands_in_at_least_one_slice():
    """The property the validation exists to buy: per-slice counts must account
    for every scored pair. Asserted over the fixture gold rather than over a
    hand-made pair, so it also catches a fixture that drifts."""
    scored = fg.score_span_judgments(PAIRS, perfect_verdicts(PAIRS))
    per_slice_total = sum(bucket["n"] for bucket in scored.per_slice.values())
    assert per_slice_total >= scored.n_pairs
    assert all(pair.get("slice_tags") for pair in PAIRS)


def test_validate_pair_shape_accepts_a_well_formed_pair():
    fg.validate_pair_shape(_pair())  # must not raise


# ── span anchors: reconstruction and drift ───────────────────────────────


def test_resolve_anchor_text_reconstructs_every_fixture_pair_span():
    for pair in PAIRS:
        for raw in pair["premise_spans"]:
            anchor = fg._anchor_from_dict(raw)
            assert fg.resolve_anchor_text(anchor, MANIFEST) == raw["text"]


def test_build_premise_concatenates_ordered_spans_for_multi_span_pair():
    multi = next(p for p in PAIRS if len(p["premise_spans"]) > 1)
    premise = fg.build_premise(multi, MANIFEST)
    for raw in multi["premise_spans"]:
        assert raw["text"] in premise
    # order preserved: the first span's text appears before the second's
    first_at = premise.index(multi["premise_spans"][0]["text"])
    second_at = premise.index(multi["premise_spans"][1]["text"])
    assert first_at < second_at


def test_span_anchor_drift_is_detected():
    """The guard: a content_hash that no longer matches the fixture
    document's actual bytes must refuse rather than silently serve a
    stale span. This IS the mutation -- the anchor is hand-corrupted here
    rather than the source file, which exercises the exact failure mode
    (content moved out from under the anchor) without touching a committed
    fixture."""
    good = fg._anchor_from_dict(PAIRS[0]["premise_spans"][0])
    corrupted = fg.SpanAnchor(
        document_uri=good.document_uri,
        block_key=good.block_key,
        text_sha256="0" * 64,
        char_span=good.char_span,
    )
    with pytest.raises(fg.SpanAnchorDrift):
        fg.resolve_anchor_text(corrupted, MANIFEST)
    # and the un-corrupted anchor still resolves -- proves the guard is
    # about the mismatch, not about the fixture file being unreadable
    fg.resolve_anchor_text(good, MANIFEST)


# ── m3: an out-of-range char_span refuses rather than silently truncating ──


def test_resolve_anchor_text_refuses_an_end_past_document_length():
    good = fg._anchor_from_dict(PAIRS[0]["premise_spans"][0])
    # The bound is the BLOCK's text length, not the document's — that is the
    # coordinate system a citation indexes.
    doc_len = len(MANIFEST["blocks"][(good.document_uri, good.block_key)]["text"])
    out_of_range = fg.SpanAnchor(
        document_uri=good.document_uri,
        block_key=good.block_key,
        text_sha256=good.text_sha256,
        char_span=(good.char_span[0], doc_len + 1000),
    )
    with pytest.raises(ValueError, match="out of bounds"):
        fg.resolve_anchor_text(out_of_range, MANIFEST)


def test_resolve_anchor_text_refuses_a_negative_start():
    good = fg._anchor_from_dict(PAIRS[0]["premise_spans"][0])
    negative = fg.SpanAnchor(
        document_uri=good.document_uri,
        block_key=good.block_key,
        text_sha256=good.text_sha256,
        char_span=(-1, good.char_span[1]),
    )
    with pytest.raises(ValueError, match="out of bounds"):
        fg.resolve_anchor_text(negative, MANIFEST)


def test_resolve_anchor_text_refuses_end_before_start():
    good = fg._anchor_from_dict(PAIRS[0]["premise_spans"][0])
    reversed_span = fg.SpanAnchor(
        document_uri=good.document_uri,
        block_key=good.block_key,
        text_sha256=good.text_sha256,
        char_span=(good.char_span[1], good.char_span[0]),
    )
    with pytest.raises(ValueError, match="out of bounds"):
        fg.resolve_anchor_text(reversed_span, MANIFEST)


def test_resolve_anchor_text_still_permits_an_empty_end_equals_start_span():
    """Deliberately NOT fixed here -- TH1.04's known, separate defect
    (`_span_literal` accepting `end == start`) is the owner's. This loader's
    job is only to refuse a span it cannot resolve; an empty range still
    resolves to an empty string."""
    good = fg._anchor_from_dict(PAIRS[0]["premise_spans"][0])
    empty = fg.SpanAnchor(
        document_uri=good.document_uri,
        block_key=good.block_key,
        text_sha256=good.text_sha256,
        char_span=(good.char_span[0], good.char_span[0]),
    )
    assert fg.resolve_anchor_text(empty, MANIFEST) == ""


# ── scoring: precision/recall/invalid/per-slice ──────────────────────────


def test_score_span_judgments_perfect_judge_scores_1_0_1_0():
    score = fg.score_span_judgments(PAIRS, perfect_verdicts(PAIRS))
    assert score.n_pairs == len(PAIRS)
    assert score.invalid == 0
    assert score.entailed_precision == 1.0
    assert score.entailed_recall == 1.0
    for tag, bucket in score.per_slice.items():
        assert bucket["accuracy"] == 1.0, tag


def test_score_span_judgments_precision_recall_arithmetic():
    """A specific, hand-computed wrong judge, not just pass/fail. The gold has
    6 entailed pairs (fx-1, fx-2, fx-5, fx-7, fx-8, fx-9) and 4 not-entailed
    (fx-3, fx-4, fx-6, fx-10). This judge calls fx-3 'entailed' (a false accept)
    and fx-7 'unsupported' (a false refusal), and answers every other pair
    correctly.

    The census is **asserted** rather than only described. Hand-computed
    expectations are the point of this test, but they silently couple it to the
    fixture's composition — when fx-9 and fx-10 were added for the cross-block
    case, the only symptom was `0.8333 != 0.8`, which reads like a scoring bug
    rather than "the fixture grew by two pairs". The assertions below fail with
    the count instead.
    """
    entailed = [p["id"] for p in PAIRS if p["verdict"] == "entailed"]
    not_entailed = [p["id"] for p in PAIRS if p["verdict"] == "not-entailed"]
    assert len(entailed) == 6, f"fixture entailed census moved: {entailed}"
    assert len(not_entailed) == 4, f"fixture not-entailed census moved: {not_entailed}"

    verdicts = perfect_verdicts(PAIRS)
    verdicts["fx-3"] = _verdict("entailed")
    verdicts["fx-7"] = _verdict("unsupported")
    score = fg.score_span_judgments(PAIRS, verdicts)
    # tp = 5 (fx-1, fx-2, fx-5, fx-8, fx-9), fp = 1 (fx-3) -> precision 5/6
    assert score.entailed_precision == pytest.approx(5 / 6)
    # gold_positive = 6, tp = 5 -> recall 5/6
    assert score.entailed_recall == pytest.approx(5 / 6)


def test_recall_is_none_symmetric_with_precision_when_gold_has_no_positives():
    """m1: precision already returns None, never a fabricated 0.0, when
    tp+fp == 0. Recall must do the same when gold_positive == 0 -- 'unmeasured
    is not zero' applied asymmetrically was the defect."""
    all_not_entailed = [p for p in PAIRS if p["verdict"] == "not-entailed"]
    assert all_not_entailed, "fixture must carry at least one not-entailed pair"
    verdicts = {p["id"]: _verdict("unsupported") for p in all_not_entailed}
    score = fg.score_span_judgments(all_not_entailed, verdicts)
    assert score.entailed_recall is None


def test_invalid_verdicts_count_as_a_miss_and_never_an_accept():
    verdicts = perfect_verdicts(PAIRS)
    entailed_pair = next(p for p in PAIRS if p["verdict"] == "entailed")
    verdicts[entailed_pair["id"]] = _verdict(None, valid=False)
    score = fg.score_span_judgments(PAIRS, verdicts)
    assert score.invalid == 1
    # the gold-entailed pair now reads as a false refusal, not an accept:
    # recall drops, precision cannot have risen from an invalid response.
    assert score.entailed_recall < 1.0
    assert score.entailed_precision == 1.0


# ── span-support coverage: reuses the imported predicate, never reimplements it ──


def test_score_answer_coverage_grounds_the_all_entailed_answer_only():
    bars = fb.FAITHFULNESS_BAR_DEFAULTS
    coverage = {c.answer_id: c for c in fg.score_answer_coverage(
        PAIRS, perfect_verdicts(PAIRS), bars,
    )}
    assert coverage["ans-allgood"].grounded is True
    assert coverage["ans-allgood"].entailed == coverage["ans-allgood"].total == 2
    assert coverage["ans-mvcc"].grounded is False
    assert coverage["ans-mvcc"].entailed == 2
    assert coverage["ans-mvcc"].total == 4
    assert coverage["ans-reranker"].grounded is False


def test_score_answer_coverage_calls_the_imported_predicate_not_a_local_copy(monkeypatch):
    """Proof, not assertion: patch ``fb.answer_grounded`` itself to a
    sentinel and confirm every result carries the sentinel's answer. If
    this module ever grows a local `entailed / total >= bar` copy instead
    of calling through, this test starts passing for the wrong reason --
    which is exactly why it checks the *return value* is the patched
    sentinel, not merely that the real predicate was importable."""
    sentinel = object()
    monkeypatch.setattr(fb, "answer_grounded", lambda *a, **k: sentinel)
    coverage = fg.score_answer_coverage(
        PAIRS, perfect_verdicts(PAIRS), fb.FAITHFULNESS_BAR_DEFAULTS,
    )
    assert coverage, "fixture must produce at least one answer group"
    assert all(c.grounded is sentinel for c in coverage)


# ── bar visibility: no config row / honoured / CLAMPED ───────────────────


def test_bar_visibility_no_rows_reports_committed_defaults():
    rows = fg.bar_visibility_rows({})
    assert {v["key"] for v in rows} == set(fb.FAITHFULNESS_BAR_DEFAULTS)
    for v in rows:
        assert v["status"] == "no config row"
        assert v["effective"] == v["committed"]
        assert v["requested"] is None


def test_bar_visibility_tightening_is_honoured():
    rows = fg.bar_visibility_rows({"faithfulness_gate_recall_bar": 0.95})
    row = next(v for v in rows if v["key"] == "faithfulness_gate_recall_bar")
    assert row["status"] == "honoured"
    assert row["effective"] == 0.95


def test_bar_visibility_unlicensed_loosening_is_clamped():
    rows = fg.bar_visibility_rows({"faithfulness_coverage_bar": 0.8})
    row = next(v for v in rows if v["key"] == "faithfulness_coverage_bar")
    assert row["status"] == "CLAMPED"
    assert row["effective"] == row["committed"] == 1.0


def test_bar_visibility_raises_on_an_unreadable_row():
    with pytest.raises(ValueError):
        fg.bar_visibility_rows({"faithfulness_gate_recall_bar": "high"})


def test_render_bar_visibility_names_every_bar_and_its_status():
    text = fg.render_bar_visibility({"faithfulness_coverage_bar": 0.8})
    for key in fb.FAITHFULNESS_BAR_DEFAULTS:
        assert key in text
    assert "CLAMPED" in text
    assert "no config row" in text  # the other two bars carry no row


# ── the cost twin: never a fabricated zero ───────────────────────────────


def test_render_cost_twin_none_says_not_measured_never_a_number():
    text = fg.render_cost_twin(None)
    assert "not measured" in text
    assert "0" not in text  # no bare zero standing in for "unmeasured"


def test_render_cost_twin_with_a_real_twin_reports_channel_and_tokens():
    from benchlib.twin import LatencyRecorder, TokenLedger, Twin

    recorder = LatencyRecorder()
    recorder.record("judge_call", 0.5, "live")
    tokens = TokenLedger()
    tokens.record_live("verification", {"prompt_tokens": 100, "completion_tokens": 20})
    twin = Twin.capture(recorder, tokens, declared_channels=("judge_call",))

    text = fg.render_cost_twin(twin)
    assert "judge_call" in text
    assert "verification" in text
    assert "not measured" not in text


# ── live judge invocation: the ungated probe door, stubbed ───────────────


def make_stub_orchestrator(verdict_for):
    from benchlib.twin import TokenLedger

    class StubOrchestrator:
        def __init__(self, config, cache_dir):
            self.config = config
            self.tokens = TokenLedger()
            self.live_calls = 0

        async def chat_completion(self, purpose, messages, response_format=None, seed=None):
            self.live_calls += 1
            hypothesis = messages[1]["content"].rsplit("HYPOTHESIS:\n", 1)[-1]
            self.tokens.record_live(
                purpose, {"prompt_tokens": 80, "completion_tokens": 15},
            )
            return json.dumps({"verdict": verdict_for(hypothesis), "reason": "stub"})

    return StubOrchestrator


async def test_score_via_live_judge_probes_every_pair_and_captures_the_twin():
    by_hypothesis = {p["hypothesis"]: _judge_verdict_for(p["verdict"]) for p in PAIRS}
    orchestrator_cls = make_stub_orchestrator(lambda h: by_hypothesis[h])

    score, twin, verdicts = await fg.score_via_live_judge(
        PAIRS, MANIFEST, config={"verification": object()},
        cache_dir="/dev/null-unused", orchestrator_cls=orchestrator_cls,
    )

    assert len(verdicts) == len(PAIRS)
    assert score.entailed_precision == 1.0
    assert score.entailed_recall == 1.0
    assert twin.channels["judge_call"].live.n == len(PAIRS)
    assert twin.tokens_by_purpose["verification"]["live_calls"] == len(PAIRS)


# ── the anchor basis: the runtime's coordinate system, not the document's ──


def test_an_anchor_resolves_exactly_what_the_runtime_would_slice():
    """The property the 2026-08-17 ruling bought. `app.services.faithfulness_gate`
    `._entails` puts `block.text[start:end]` to the judge; this asserts the gold
    loader produces the identical string from the identical inputs, so a judge
    qualified here is qualified on the premises production actually constructs."""
    for pair in PAIRS:
        for raw in pair["premise_spans"]:
            anchor = fg._anchor_from_dict(raw)
            block = MANIFEST["blocks"][(anchor.document_uri, anchor.block_key)]
            start, end = anchor.char_span
            runtime_premise = block["text"][start:end]   # what _entails does
            assert fg.resolve_anchor_text(anchor, MANIFEST) == runtime_premise


def test_the_retired_document_coordinate_anchor_is_refused():
    """A `fixture_path` anchor is the retired basis and must not silently load.

    It cannot be resolved faithfully — it indexes the document file while the
    runtime indexes block text — so accepting one would reintroduce exactly the
    divergence the ruling removed, and quietly.
    """
    with pytest.raises(ValueError, match="document_uri"):
        fg._anchor_from_dict(
            {"fixture_path": "doc_mvcc.txt", "content_hash": "0" * 64,
             "block_id": "b1", "char_span": [0, 10]}
        )


def test_a_cross_block_pair_spans_two_different_blocks():
    """The case the retired basis could not express. `doc_pipeline.md` parses to
    six blocks; a pair citing two of them proves the loader keys on the block,
    not on a document offset — under the old basis `b2`'s span would have been
    read against the document and sliced the wrong region."""
    cross = next(p for p in PAIRS if p["id"] == "fx-9")
    keys = {(a["document_uri"], a["block_key"]) for a in cross["premise_spans"]}
    assert len(keys) == 2, "fx-9 must cite two distinct blocks"
    premise = fg.build_premise(cross, MANIFEST)
    for raw in cross["premise_spans"]:
        assert raw["text"] in premise


def test_a_block_that_left_the_manifest_is_drift_not_a_silent_miss():
    good = fg._anchor_from_dict(PAIRS[0]["premise_spans"][0])
    vanished = fg.SpanAnchor(
        document_uri=good.document_uri, block_key="b999",
        text_sha256=good.text_sha256, char_span=good.char_span,
    )
    with pytest.raises(fg.SpanAnchorDrift, match="not in the manifest"):
        fg.resolve_anchor_text(vanished, MANIFEST)


def test_load_span_manifest_reports_an_absent_manifest_with_its_path():
    missing = Path("/nonexistent/span_harvest.json")
    with pytest.raises(fg.SpanManifestAbsent) as excinfo:
        fg.load_span_manifest(missing)
    assert excinfo.value.path == missing

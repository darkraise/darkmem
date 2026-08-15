"""TH1.17 — the faithfulness-gate scoring module. Exercised entirely
against ``fixtures/faithfulness_gate_fixture.py``, a **fixture**, never the
real claim/span entailment gold (which does not exist yet — TH1.01 §5)."""
from __future__ import annotations

import json

import pytest

from benchlib import faithfulness_gate as fg
from benchlib.tests.fixtures import faithfulness_gate_fixture as fx

from app.services import faithfulness_bars as fb
from app.services.verification_judge import ProbeVerdict

PAIRS = fx.build_fixture_pairs()


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
         "premise_spans": [{"fixture_path": "a", "content_hash": "b",
                             "block_id": "c", "char_span": [0, 1]}]},
    ]}))
    with pytest.raises(ValueError, match="verdict"):
        fg.load_span_gold(bad)


# ── pair-shape validation ────────────────────────────────────────────────


def _pair(**overrides):
    base = {
        "id": "p1",
        "verdict": "entailed",
        "provenance": "hand-authored-fixture-span",
        "premise_spans": [{"fixture_path": "a", "content_hash": "b",
                            "block_id": "c", "char_span": [0, 1]}],
    }
    base.update(overrides)
    return base


def test_validate_pair_shape_rejects_bad_verdict():
    with pytest.raises(ValueError, match="verdict"):
        fg.validate_pair_shape(_pair(verdict="entailedd"))


def test_validate_pair_shape_rejects_unknown_provenance():
    with pytest.raises(ValueError, match="provenance"):
        fg.validate_pair_shape(_pair(provenance="vibes"))


@pytest.mark.parametrize("provenance", sorted(fg.RESERVED_ZERO_PROVENANCE))
def test_validate_pair_shape_refuses_reserved_zero_provenance(provenance):
    with pytest.raises(ValueError, match="reserves at zero"):
        fg.validate_pair_shape(_pair(provenance=provenance))


def test_validate_pair_shape_rejects_empty_premise_spans():
    with pytest.raises(ValueError, match="no premise spans"):
        fg.validate_pair_shape(_pair(premise_spans=[]))


def test_validate_pair_shape_accepts_a_well_formed_pair():
    fg.validate_pair_shape(_pair())  # must not raise


# ── span anchors: reconstruction and drift ───────────────────────────────


def test_resolve_anchor_text_reconstructs_every_fixture_pair_span():
    for pair in PAIRS:
        for raw in pair["premise_spans"]:
            anchor = fg._anchor_from_dict(raw)
            assert fg.resolve_anchor_text(anchor, fx.FIXTURE_DIR) == raw["text"]


def test_build_premise_concatenates_ordered_spans_for_multi_span_pair():
    multi = next(p for p in PAIRS if len(p["premise_spans"]) > 1)
    premise = fg.build_premise(multi, fx.FIXTURE_DIR)
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
        fixture_path=good.fixture_path,
        content_hash="0" * 64,
        block_id=good.block_id,
        char_span=good.char_span,
    )
    with pytest.raises(fg.SpanAnchorDrift):
        fg.resolve_anchor_text(corrupted, fx.FIXTURE_DIR)
    # and the un-corrupted anchor still resolves -- proves the guard is
    # about the mismatch, not about the fixture file being unreadable
    fg.resolve_anchor_text(good, fx.FIXTURE_DIR)


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
    """A specific, hand-computed wrong judge, not just pass/fail. The gold
    has 5 entailed pairs (fx-1, fx-2, fx-5, fx-7, fx-8) and 3 not-entailed
    (fx-3, fx-4, fx-6). This judge calls fx-3 'entailed' (a false accept)
    and fx-7 'unsupported' (a false refusal), and answers every other pair
    correctly."""
    verdicts = perfect_verdicts(PAIRS)
    verdicts["fx-3"] = _verdict("entailed")
    verdicts["fx-7"] = _verdict("unsupported")
    score = fg.score_span_judgments(PAIRS, verdicts)
    # tp = 4 (fx-1, fx-2, fx-5, fx-8), fp = 1 (fx-3) -> precision 4/5
    assert score.entailed_precision == pytest.approx(4 / 5)
    # gold_positive = 5, tp = 4 -> recall 4/5
    assert score.entailed_recall == pytest.approx(4 / 5)


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
        PAIRS, fx.FIXTURE_DIR, config={"verification": object()},
        cache_dir="/dev/null-unused", orchestrator_cls=orchestrator_cls,
    )

    assert len(verdicts) == len(PAIRS)
    assert score.entailed_precision == 1.0
    assert score.entailed_recall == 1.0
    assert twin.channels["judge_call"].live.n == len(PAIRS)
    assert twin.tokens_by_purpose["verification"]["live_calls"] == len(PAIRS)

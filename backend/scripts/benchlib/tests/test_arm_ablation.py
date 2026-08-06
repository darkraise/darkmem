"""Tests for the arm-ablation harness (T2.44).

Same two-tier split the rest of benchlib uses: pure tests build tiny
``ScoreReport``/``Twin``/``ArmLeg``/``ArmComparison`` objects by hand and
need no database; the DB-backed tests drive the real ``run_arm_ablation``
end to end against a synthetic corpus through a stubbed
``TwinningOrchestrator`` -- the shipped caching/token-attribution class with
only the model round trip replaced.
"""
import json

import pytest

from benchlib import arm_ablation, retrieval_gold, twin
from benchlib.retrieval_scorer import ScoreReport, SliceScore
from app.services.rank_fusion import RANK_ARMS, RankArm

pytestmark = pytest.mark.usefixtures("_bench_db")


# ── pure helpers: hand-built metric objects, no DB ───────────────────────


def _score_report(*, k=1, retrieval_limit=1, min_pairs=1, mrr=0.5, hit=0.5, n=2, pair_scores=None) -> ScoreReport:
    slices = {
        tag: SliceScore(slice_tag=tag, n_pairs=0, powered=False, mrr=None, hit_at_k=None)
        for tag in retrieval_gold.SLICES
    }
    slices["exact"] = SliceScore(slice_tag="exact", n_pairs=n, powered=True, mrr=mrr, hit_at_k=hit)
    return ScoreReport(
        k=k, retrieval_limit=retrieval_limit, min_pairs=min_pairs, n_pairs=n,
        slices=slices, aggregate_powered=True, aggregate_mrr=mrr, aggregate_hit_at_k=hit,
        pair_scores={} if pair_scores is None else pair_scores,
    )


def _twin_obj(*, live=0, cache=1) -> twin.Twin:
    recorder = twin.LatencyRecorder()
    for _ in range(live):
        recorder.record("end_to_end", 0.9, "live")
    for _ in range(cache):
        recorder.record("end_to_end", 0.001, "cache")
    return twin.Twin.capture(recorder, twin.TokenLedger(), min_samples=1)


def _leg(*, weight, fingerprint="stub-fp|3", mrr=0.5, hit=0.5, n=2) -> arm_ablation.ArmLeg:
    score = _score_report(mrr=mrr, hit=hit, n=n)
    return arm_ablation.ArmLeg(weight=weight, fingerprint=fingerprint, run=twin.EvalRun(score=score, twin=_twin_obj()))


def _arm() -> RankArm:
    return arm_ablation.resolve_arm("w_importance")


def _comparison(*, off_mrr=0.5, off_hit=0.0, on_mrr=0.8, on_hit=0.9, fingerprint="stub-fp|3") -> arm_ablation.ArmComparison:
    off = _leg(weight=0.0, mrr=off_mrr, hit=off_hit, fingerprint=fingerprint)
    on = _leg(weight=1.0, mrr=on_mrr, hit=on_hit, fingerprint=fingerprint)
    return arm_ablation.ArmComparison(arm=_arm(), off=off, on=on, ingest_fingerprint=fingerprint)


# ── resolve_arm: derived from RANK_ARMS, never a hand-list ───────────────


def test_resolve_arm_finds_every_real_arm_by_its_flag_spelling():
    for arm in RANK_ARMS:
        assert arm_ablation.resolve_arm(arm.flag) is arm


def test_resolve_arm_rejects_the_short_name_spelling():
    """Only the flag spelling is accepted (module docstring / brief: the
    task's own Verify line uses --arm w_importance, the flag, not the short
    name 'importance'). Accepting a second spelling for the same arm is the
    ambiguity resolve_arm exists to foreclose."""
    with pytest.raises(ValueError, match="unknown --arm 'importance'"):
        arm_ablation.resolve_arm("importance")


def test_resolve_arm_rejects_unknown_and_names_the_valid_set():
    with pytest.raises(ValueError) as excinfo:
        arm_ablation.resolve_arm("w_not_a_real_arm")
    message = str(excinfo.value)
    assert "w_not_a_real_arm" in message
    for arm in RANK_ARMS:
        assert arm.flag in message


def test_resolve_arm_set_is_derived_from_rank_arms_not_a_hand_list(monkeypatch):
    """Prove there is no second hand-written arm list anywhere in this
    module: add a brand-new fake arm directly to RANK_ARMS and confirm
    resolve_arm finds it immediately, with no edit to arm_ablation.py."""
    fake = RankArm("fake", "w_fake_arm_for_test", 0.0, activation="T9.99")
    monkeypatch.setattr(arm_ablation, "RANK_ARMS", (*RANK_ARMS, fake))
    assert arm_ablation.resolve_arm("w_fake_arm_for_test") is fake

    # And the rejection message picks up the new arm too, proving the
    # "valid set" text is also derived, not a separate hardcoded string.
    with pytest.raises(ValueError, match="w_fake_arm_for_test"):
        arm_ablation.resolve_arm("still_not_real")


# ── ArmLeg / ArmComparison: structural no-twin-no-accuracy guard ─────────


def test_arm_leg_refuses_a_run_that_is_not_a_real_evalrun():
    with pytest.raises(TypeError, match="EvalRun"):
        arm_ablation.ArmLeg(weight=0.0, fingerprint="fp", run="not-an-evalrun")


def test_record_arm_comparison_refuses_anything_but_an_armcomparison(tmp_path):
    with pytest.raises(TypeError, match="ArmComparison"):
        arm_ablation.record_arm_comparison({"arm_comparison": {"fake": True}}, path=tmp_path / "ledger.jsonl")
    assert not (tmp_path / "ledger.jsonl").exists()


def test_comparison_refuses_when_off_leg_is_not_weight_zero():
    off = _leg(weight=0.3)
    on = _leg(weight=1.0)
    with pytest.raises(ValueError, match="OFF leg must run at weight 0.0"):
        arm_ablation.ArmComparison(arm=_arm(), off=off, on=on, ingest_fingerprint="stub-fp|3")


def test_comparison_refuses_when_on_leg_is_also_weight_zero():
    off = _leg(weight=0.0)
    on = _leg(weight=0.0)
    with pytest.raises(ValueError, match="not an ablation"):
        arm_ablation.ArmComparison(arm=_arm(), off=off, on=on, ingest_fingerprint="stub-fp|3")


def test_comparison_refuses_mismatched_scoring_protocol():
    off = _leg(weight=0.0)
    on_score = _score_report(k=2)  # different k
    on = arm_ablation.ArmLeg(weight=1.0, fingerprint="stub-fp|3", run=twin.EvalRun(score=on_score, twin=_twin_obj()))
    with pytest.raises(ValueError, match="different protocols"):
        arm_ablation.ArmComparison(arm=_arm(), off=off, on=on, ingest_fingerprint="stub-fp|3")


def test_comparison_refuses_legs_scored_over_different_gold_pairs():
    """Fix round F5: the pair-set-equality guard (ArmComparison.__post_init__,
    the check right after the protocol-fields check) was previously exercised
    only with pair_scores={} on both sides, which passes vacuously (empty
    set equals empty set regardless of whether the guard runs at all) -- the
    exact hollow-test shape the brief warns about. Same k/min_pairs/n_pairs
    on both legs (so the earlier protocol check does not fire first) but a
    genuinely different pair-id set."""
    off_score = _score_report(pair_scores={"rt-0001": object(), "rt-0002": object()})
    on_score = _score_report(pair_scores={"rt-0001": object(), "rt-0003": object()})
    off = arm_ablation.ArmLeg(weight=0.0, fingerprint="stub-fp|3", run=twin.EvalRun(score=off_score, twin=_twin_obj()))
    on = arm_ablation.ArmLeg(weight=1.0, fingerprint="stub-fp|3", run=twin.EvalRun(score=on_score, twin=_twin_obj()))
    with pytest.raises(ValueError, match="different gold pairs"):
        arm_ablation.ArmComparison(arm=_arm(), off=off, on=on, ingest_fingerprint="stub-fp|3")


# ── mutation-proven guard: cross-fingerprint refusal (invariant 2) ───────


def test_comparison_refuses_when_the_two_legs_have_different_fingerprints():
    """Done-when 3 / CLAUDE.md invariant 2: no cross-fingerprint comparison.
    Mutated by construction here (the two legs are built with different
    fingerprints on purpose) -- this IS the mutation the brief asks to
    prove: restoring equal fingerprints (test right below) passes."""
    off = _leg(weight=0.0, fingerprint="model-a|768")
    on = _leg(weight=1.0, fingerprint="model-b|1024")
    with pytest.raises(ValueError, match="invariant 2 forbids a cross-fingerprint comparison"):
        arm_ablation.ArmComparison(arm=_arm(), off=off, on=on, ingest_fingerprint="model-a|768")


def test_comparison_refuses_when_a_leg_disagrees_with_the_ingested_fingerprint():
    """The other half of the same guard: both legs agree with EACH OTHER
    but neither matches what the corpus was actually ingested under -- a
    subtler drift the leg-vs-leg check alone would miss."""
    off = _leg(weight=0.0, fingerprint="model-a|768")
    on = _leg(weight=1.0, fingerprint="model-a|768")
    with pytest.raises(ValueError, match="corpus was ingested under"):
        arm_ablation.ArmComparison(arm=_arm(), off=off, on=on, ingest_fingerprint="model-b|1024")


def test_comparison_accepts_matching_fingerprints_restoring_the_mutation_above():
    off = _leg(weight=0.0, fingerprint="model-a|768")
    on = _leg(weight=1.0, fingerprint="model-a|768")
    comparison = arm_ablation.ArmComparison(
        arm=_arm(), off=off, on=on, ingest_fingerprint="model-a|768",
    )
    assert comparison.off.fingerprint == comparison.on.fingerprint == "model-a|768"


# ── deltas: per-slice, on minus off, slice set from the gold ─────────────


def test_deltas_are_on_minus_off_per_slice_and_aggregate():
    comparison = _comparison(off_mrr=0.5, on_mrr=0.8, off_hit=0.0, on_hit=0.9)
    deltas = comparison.deltas()
    assert deltas["direction"] == "on minus off"
    assert deltas["aggregate"]["mrr"] == pytest.approx(0.3)
    assert deltas["aggregate"]["hit_at_k"] == pytest.approx(0.9)
    assert deltas["slices"]["exact"]["mrr"] == pytest.approx(0.3)


def test_delta_slice_set_comes_from_the_gold_never_a_hardcoded_list():
    comparison = _comparison()
    assert set(comparison.deltas()["slices"]) == set(retrieval_gold.SLICES)


def test_delta_is_none_for_an_underpowered_slice_never_invented_as_zero():
    comparison = _comparison()
    # every slice but "exact" is under-powered (mrr/hit_at_k=None) in the
    # hand-built helper above.
    for tag in retrieval_gold.SLICES - {"exact"}:
        assert comparison.deltas()["slices"][tag]["mrr"] is None
        assert comparison.deltas()["slices"][tag]["hit_at_k"] is None


def test_ledger_payload_carries_both_legs_full_twins_and_the_weight():
    comparison = _comparison()
    payload = comparison.to_ledger_payload()["arm_comparison"]
    assert payload["flag"] == "w_importance"
    for label in (arm_ablation.LEG_OFF, arm_ablation.LEG_ON):
        leg_payload = payload["legs"][label]
        assert "weight" in leg_payload
        assert "score" in leg_payload
        assert "twin" in leg_payload
    assert payload["legs"][arm_ablation.LEG_OFF]["weight"] == 0.0
    assert payload["legs"][arm_ablation.LEG_ON]["weight"] == 1.0
    # JSON-native: this is exactly what ledger.record() requires.
    json.dumps(payload)


def test_report_path_is_dated_and_names_the_arm_flag():
    from datetime import date
    from pathlib import Path
    p = arm_ablation.report_path(date(2026, 3, 4), _arm(), report_dir=Path("/tmp/x"))
    assert p == Path("/tmp/x/2026-03-04-retrieval-eval-arm-w_importance.md")


def test_render_arm_report_carries_the_weights_and_the_per_slice_table():
    comparison = _comparison(off_mrr=0.5, on_mrr=0.8)
    meta = {
        "run_id": "11111111-1111-1111-1111-111111111111",
        "timestamp": "2026-01-02T00:00:00+00:00", "date": "2026-01-02",
        "git_sha": "deadbeefcafef00d", "fingerprint": "stub-fp|3",
        "arm": "importance", "flag": "w_importance", "weight_off": 0.0, "weight_on": 1.0,
        "corpus_entries": 3, "gold_version": 1, "n_pairs_authored": 2, "n_pairs_live": 2,
    }
    text = arm_ablation.render_arm_report(comparison, meta)
    assert "weights: off=`0.0`, on=`1.0`" in text
    assert "exact" in text
    assert "AGGREGATE" in text
    assert meta["fingerprint"] in text


# ── DB-backed: the real composition, a stubbed model ─────────────────────


def _mid(key: str) -> str:
    return retrieval_gold.memory_id_for_key(key)


def _write_corpus_and_gold(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    entries = [
        {
            "key": "m-alpha", "memory_id": _mid("m-alpha"),
            "content": "The alpha service handles billing.",
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        {
            "key": "m-beta", "memory_id": _mid("m-beta"),
            "content": "The beta pipeline handles ingestion.",
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        {
            "key": "m-gamma", "memory_id": _mid("m-gamma"),
            "content": "The gamma worker handles cleanup.",
            "created_at": "2026-01-01T00:00:00+00:00",
        },
    ]
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(json.dumps({"memories": entries}))

    pairs = [
        {"id": "rt-0001", "query": "alpha", "relevant_memory_ids": [entries[0]["memory_id"]], "slice_tags": ["exact"]},
        {"id": "rt-0002", "query": "beta", "relevant_memory_ids": [entries[1]["memory_id"]], "slice_tags": ["exact"]},
        {"id": "rt-0003", "query": "gamma", "relevant_memory_ids": [entries[2]["memory_id"]], "slice_tags": ["exact"]},
    ]
    declared = {tag: 0 for tag in retrieval_gold.SLICES}
    declared["exact"] = len(pairs)
    gold_path = tmp_path / "gold.json"
    gold_path.write_text(json.dumps({"version": 1, "declared_slice_counts": declared, "pairs": pairs}))

    return corpus_path, gold_path, entries, pairs


def _vec(text: str) -> list[float]:
    lowered = text.lower()
    return [
        1.0 if "alpha" in lowered else 0.0,
        1.0 if "beta" in lowered else 0.0,
        1.0 if "gamma" in lowered else 0.0,
    ]


_STUB_EXTRACTION = (
    '{"entities": [], "relationships": [], "memory_type": "fact", '
    '"importance": 0.5, "summary": "s", "emotions": [], "flags": []}'
)


class _StubTwinLLM(twin.TwinningOrchestrator):
    async def _live_embed(self, text):
        return _vec(text), "stub-embed|3"

    async def _live_embed_batch(self, texts):
        return [_vec(t) for t in texts], "stub-embed|3"

    async def _live_chat(self, purpose, messages, **kwargs):
        return _STUB_EXTRACTION


@pytest.mark.asyncio
async def test_run_arm_ablation_end_to_end_produces_report_and_ledger_row(tmp_path, monkeypatch):
    corpus_path, gold_path, entries, pairs = _write_corpus_and_gold(tmp_path / "gold")

    monkeypatch.setattr(arm_ablation, "TwinningOrchestrator", _StubTwinLLM)

    report_dir = tmp_path / "report"
    ledger_path = tmp_path / "ledger.jsonl"
    from datetime import datetime, timezone
    fixed_date = datetime(2026, 1, 2, tzinfo=timezone.utc)

    result = await arm_ablation.run_arm_ablation(
        arm_flag="w_importance",
        deepseek_api_key="sk-not-used-in-test",
        cache_dir=tmp_path / "cache", corpus_path=corpus_path, gold_path=gold_path,
        k=1, min_pairs=1, report_dir=report_dir, ledger_path=ledger_path, now=fixed_date,
    )

    assert result.comparison.off.weight == 0.0
    assert result.comparison.on.weight == arm_ablation.DEFAULT_PROBE_WEIGHT
    assert result.comparison.off.fingerprint == result.comparison.on.fingerprint
    assert result.report_path == report_dir / "2026-01-02-retrieval-eval-arm-w_importance.md"
    assert result.report_path.read_text() == result.report_text

    from benchlib import ledger as ledger_mod
    rows = ledger_mod.read_runs(ledger_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["arm_comparison"]["flag"] == "w_importance"
    assert set(row["arm_comparison"]["legs"]) == {"off", "on"}
    assert row["run_id"] == result.meta["run_id"]
    assert row["fingerprint"] == result.meta["fingerprint"]

    # T2.44 fix round, F1: the composition-level twin-emission property --
    # what actually reached the ledger, not just what run_arm_ablation
    # returned in memory. A recording path that swapped in a twin-less
    # lookalike dict (bypassing record_arm_comparison) would satisfy every
    # assertion above while failing these; this is what the review's bypass
    # mutation of run_arm_ablation (skipping record_arm_comparison to
    # hand-roll a dict into ledger.record) showed the prior suite missed.
    for label in (arm_ablation.LEG_OFF, arm_ablation.LEG_ON):
        leg_row = row["arm_comparison"]["legs"][label]
        assert {"score", "twin"} <= set(leg_row), (
            f"{label} leg's recorded row is missing 'score' and/or 'twin' -- "
            "an accuracy figure reached the ledger without its twin attached"
        )
        assert leg_row["twin"]["channels"], f"{label} leg's twin has no channels"


@pytest.mark.asyncio
async def test_run_arm_ablation_pins_every_other_flag_identically_between_legs(tmp_path, monkeypatch):
    """Done-when 1's precise reading: the on-leg and off-leg differ ONLY in
    the arm's own weight -- assert the rest of the pinned feature-flags row
    is byte-identical between the two legs, not merely that both ran."""
    corpus_path, gold_path, entries, pairs = _write_corpus_and_gold(tmp_path / "gold")
    monkeypatch.setattr(arm_ablation, "TwinningOrchestrator", _StubTwinLLM)

    captured: list[dict] = []
    real_pin = arm_ablation._pin_arm_weight

    async def spy_pin(session_factory, *, gate_config, arm, weight):
        pinned = await real_pin(session_factory, gate_config=gate_config, arm=arm, weight=weight)
        captured.append(dict(pinned))
        return pinned

    monkeypatch.setattr(arm_ablation, "_pin_arm_weight", spy_pin)

    from datetime import datetime, timezone
    fixed_date = datetime(2026, 1, 2, tzinfo=timezone.utc)
    await arm_ablation.run_arm_ablation(
        arm_flag="w_importance",
        deepseek_api_key="sk-not-used-in-test",
        cache_dir=tmp_path / "cache", corpus_path=corpus_path, gold_path=gold_path,
        k=1, min_pairs=1, report_dir=tmp_path / "report", ledger_path=tmp_path / "ledger.jsonl",
        now=fixed_date,
    )

    assert len(captured) == 2
    off_flags, on_flags = captured
    assert off_flags["w_importance"] == 0.0
    assert on_flags["w_importance"] == arm_ablation.DEFAULT_PROBE_WEIGHT
    diff_keys = {k for k in off_flags if off_flags[k] != on_flags.get(k)}
    assert diff_keys == {"w_importance"}


@pytest.mark.asyncio
async def test_run_arm_ablation_rejects_zero_weight(tmp_path, monkeypatch):
    corpus_path, gold_path, entries, pairs = _write_corpus_and_gold(tmp_path / "gold")
    monkeypatch.setattr(arm_ablation, "TwinningOrchestrator", _StubTwinLLM)

    with pytest.raises(ValueError, match="must be nonzero"):
        await arm_ablation.run_arm_ablation(
            arm_flag="w_importance", weight=0.0,
            deepseek_api_key="sk-not-used-in-test",
            cache_dir=tmp_path / "cache", corpus_path=corpus_path, gold_path=gold_path,
            report_dir=tmp_path / "report", ledger_path=tmp_path / "ledger.jsonl",
        )


@pytest.mark.asyncio
async def test_run_arm_ablation_rejects_an_unknown_arm_before_touching_the_db(tmp_path, monkeypatch):
    corpus_path, gold_path, entries, pairs = _write_corpus_and_gold(tmp_path / "gold")
    monkeypatch.setattr(arm_ablation, "TwinningOrchestrator", _StubTwinLLM)

    with pytest.raises(ValueError, match="unknown --arm"):
        await arm_ablation.run_arm_ablation(
            arm_flag="not_a_real_arm",
            deepseek_api_key="sk-not-used-in-test",
            cache_dir=tmp_path / "cache", corpus_path=corpus_path, gold_path=gold_path,
            report_dir=tmp_path / "report", ledger_path=tmp_path / "ledger.jsonl",
        )


# ── the other two signal classes, and the vacuity guard ─────────────────
#
# `RANK_ARMS` covers only the post-fusion multipliers, so the two tasks that
# own the other classes (T2.35's context boost, T2.50's list weights) could
# not run their own stated Verify line: `resolve_arm` rejected every flag they
# name. `resolve_ablatable` covers all three classes, and the guard below is
# what keeps that coverage honest — an arm whose signal cannot be present
# refuses rather than reporting the exact zero that reads like a verdict.


def test_every_rank_arm_still_resolves_through_the_wider_resolver():
    for arm in RANK_ARMS:
        resolved = arm_ablation.resolve_ablatable(arm.flag)
        assert resolved.arm is arm
        assert resolved.kind == arm_ablation.KIND_FACTOR
        assert resolved.activation == arm.activation


def test_the_list_weights_and_the_context_boost_now_resolve():
    ppr = arm_ablation.resolve_ablatable("w_ppr")
    assert ppr.kind == arm_ablation.KIND_LIST
    assert ppr.project_scoped is True

    dual = arm_ablation.resolve_ablatable("w_dual")
    assert dual.kind == arm_ablation.KIND_LIST

    boost = arm_ablation.resolve_ablatable("w_context_boost")
    assert boost.kind == arm_ablation.KIND_BOOST


def test_semantic_weight_is_not_an_ablatable_arm():
    """It is the split between the two base sides, not a signal that can be
    turned off: an 'off leg' at semantic_weight=0 is a keyword-only retriever,
    which is a different system rather than the same one missing an arm."""
    with pytest.raises(ValueError, match="semantic_weight"):
        arm_ablation.resolve_ablatable("semantic_weight")


def test_the_wider_resolver_is_still_derived_not_a_hand_list(monkeypatch):
    fake = RankArm("fake", "w_fake_arm_for_test", 0.0, activation="T9.99")
    monkeypatch.setattr(arm_ablation, "RANK_ARMS", (*RANK_ARMS, fake))
    assert arm_ablation.resolve_ablatable("w_fake_arm_for_test").arm is fake
    with pytest.raises(ValueError, match="w_fake_arm_for_test"):
        arm_ablation.resolve_ablatable("still_not_real")


def test_a_list_arm_carries_the_gate_its_weight_needs():
    """`w_ppr` alone is inert — `ppr_list_weight` returns zero unless
    `ppr_enabled` is set — so pinning the weight without its companion would
    run the off leg twice and report the difference as a delta."""
    assert dict(arm_ablation.resolve_ablatable("w_ppr").companions) == {
        "ppr_enabled": True
    }
    assert dict(arm_ablation.resolve_ablatable("w_dual").companions) == {
        "dual_level_enabled": True
    }


@pytest.mark.asyncio
async def test_the_companion_gate_is_applied_to_the_on_leg_only(_bench_db):
    """The off leg is the control and must stay exactly the shipped
    configuration; flipping its gate too would make both legs 'on'."""
    arm = arm_ablation.resolve_ablatable("w_ppr")

    off = await arm_ablation._pin_arm_weight(
        arm_ablation.bench_db.session_factory, gate_config={}, arm=arm, weight=0.0,
    )
    assert off["w_ppr"] == 0.0
    assert off["ppr_enabled"] is False

    on = await arm_ablation._pin_arm_weight(
        arm_ablation.bench_db.session_factory, gate_config={}, arm=arm, weight=1.0,
    )
    assert on["w_ppr"] == 1.0
    assert on["ppr_enabled"] is True


@pytest.mark.asyncio
async def test_a_blocked_arm_refuses_before_the_reset(monkeypatch):
    """The guard has to fire before `reset_bench_db`, not after: a refusal
    that has already dropped the bench schema has cost the operator a rebuild
    to learn something knowable from the flag alone."""
    called = False

    async def _boom():
        nonlocal called
        called = True

    monkeypatch.setattr(arm_ablation.bench_db, "reset_bench_db", _boom)

    # `w_dual` was here until T2.94 landed its reader; the entry was removed
    # from `_blocked_reasons` rather than left stale, so this list is derived
    # from what is actually blocked instead of restating it.
    for flag in sorted(arm_ablation._blocked_reasons()):
        with pytest.raises(arm_ablation.ArmNotMeasurable) as excinfo:
            await arm_ablation.run_arm_ablation(arm_flag=flag)
        # The message must say what would have to change, not merely "no".
        assert flag in str(excinfo.value)
        assert len(str(excinfo.value)) > 80
    assert called is False


def test_every_blocked_reason_names_what_would_unblock_it():
    for flag, reason in arm_ablation._blocked_reasons().items():
        assert "Needs" in reason, f"{flag}'s reason does not say what unblocks it"


def test_a_list_arm_probes_at_a_list_sized_weight():
    """1.0 means different things in the two classes. As a factor weight it is
    a moderate swing around identity; as an RRF *list* weight it is the whole
    share of the fusion, and the two shipped lists already split 1.0 between
    them — so a third list at 1.0 outweighs everything else combined and the
    delta measures the probe, not the arm. Measured: the first w_ppr run at
    1.0 reported an aggregate MRR delta of -0.4742."""
    assert arm_ablation.LIST_PROBE_WEIGHT < arm_ablation.DEFAULT_PROBE_WEIGHT
    # The keyword side's own share, so the probe is one more voice of
    # comparable size rather than a dominant one.
    assert arm_ablation.LIST_PROBE_WEIGHT == pytest.approx(0.3)


def test_both_graph_arms_declare_the_artifact_no_ingest_produces():
    """Both fail identically without their artefact — an exact zero on every
    slice — so the preparation belongs to resolving the arm rather than to
    whoever remembers to call it. `w_dual` shipped once without it and
    reported exactly that zero; this is what stops the next one."""
    assert arm_ablation.resolve_ablatable("w_ppr").needs_artifact == "ppr_snapshot"
    assert (
        arm_ablation.resolve_ablatable("w_dual").needs_artifact
        == "relation_embeddings"
    )
    # A factor arm reads a column the ingest already wrote, so it needs none.
    assert arm_ablation.resolve_ablatable("w_importance").needs_artifact is None


def test_every_list_arm_has_a_preparation_path():
    """A list arm whose artefact nothing prepares is the vacuity bug by
    construction: it resolves, runs, and reports a zero. Pins that each
    declared artefact is one the runner actually knows how to build."""
    known = {"ppr_snapshot", "relation_embeddings"}
    for flag in ("w_ppr", "w_dual"):
        arm = arm_ablation.resolve_ablatable(flag)
        assert arm.needs_artifact in known, (
            f"{flag} declares an artefact no preparation path builds"
        )


# ── the access-fed arms: seed and freeze (T2.31) ────────────────────────
#
# The blocker review overturned the original diagnosis. The contamination is
# not answer-biased — at `retrieval_limit = len(entries)` every query's page is
# the whole corpus, so a leg confers heat *uniformly* (the same count on every
# row), the multiplier is constant, and order is preserved. That is a
# guaranteed vacuous zero, and reset-between-legs converges on the same thing.
# Seeding is the only live fix, and the freeze half is mandatory because the
# uniform +102 swamps any seeded skew (heat saturates by ~30).


def test_the_access_fed_arms_declare_their_artifact():
    for flag in ("w_heat", "w_recency"):
        assert arm_ablation.resolve_ablatable(flag).needs_artifact == "access_history"
    assert arm_ablation.resolve_ablatable("w_importance").needs_artifact is None


def test_the_seed_is_uncorrelated_with_the_gold_by_construction():
    """The bug this fixture exists to avoid: if hot memories were the ones the
    gold marks correct, the arm would be scored on a signal derived from the
    answer key and would win by construction. The count is a pure function of
    the memory's own id — nothing the gold knows enters it."""
    import ast
    import inspect
    import textwrap

    source = inspect.getsource(arm_ablation._prepare_access_history)
    tree = ast.parse(textwrap.dedent(source)).body[0]
    # Scan the executable body only — the docstring explains the trap in prose
    # and would otherwise trip the scan that exists to prevent it.
    body = tree.body[1:] if ast.get_docstring(tree) else tree.body
    code = "\n".join(ast.unparse(node) for node in body)

    for forbidden in ("gold", "relevant", "expected", "score"):
        assert forbidden not in code.lower(), (
            f"the access seed reads {forbidden!r}, which risks correlating the "
            "signal with the answer key"
        )
    assert "sha256" in code, "the seed must be stable across processes"
    # `hash()` is salted per process, so a run would not reproduce.
    assert "hash(" not in code.replace("hashlib", "")


def test_the_seed_spans_the_responsive_part_of_the_curve():
    """`heat_signal` saturates at 1 - e^(-n/10): a range all above ~30 is flat
    at the top, and all-zero is flat at the bottom. Either way the multiplier
    is constant and the measurement is vacuous again."""
    from app.services.rank_fusion import heat_signal

    lo = heat_signal(0)
    hi = heat_signal(arm_ablation._ACCESS_SEED_MODULUS - 1)
    assert lo == 0.0
    assert 0.5 < hi < 1.0, "the seed range must not sit in the saturated tail"


def test_the_freeze_suppresses_recording_and_restores_it():
    """Without the freeze the legs write the very table they measure, adding a
    uniform count that swamps the seeded skew."""
    from app.services import access_stats

    original = access_stats.spawn_record_access
    with arm_ablation._freeze_access_recording():
        assert access_stats.spawn_record_access is not original
        assert access_stats.spawn_record_access(["any-id"]) is None
    assert access_stats.spawn_record_access is original


def test_the_freeze_covers_the_call_site_retrieval_actually_uses():
    """`hybrid_search` imported the recorder by value at module load, so
    patching only `access_stats` would leave the live call site untouched —
    the freeze would look applied and record anyway."""
    import sys

    hybrid = sys.modules.get("app.services.hybrid_search")
    if hybrid is None:  # pragma: no cover - import order safety
        import app.services.hybrid_search as hybrid
    original = hybrid.spawn_record_access
    with arm_ablation._freeze_access_recording():
        assert hybrid.spawn_record_access is not original
    assert hybrid.spawn_record_access is original

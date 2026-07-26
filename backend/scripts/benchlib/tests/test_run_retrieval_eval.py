"""Tests for the retrieval eval runner + dated report (T0.10).

Two tiers, matching the split the rest of benchlib uses. The pure tests
(report rendering, the reproducibility projection, the path helper) build
their own tiny ``ScoreReport``/``Twin``/``Comparison`` objects and need no
database. The DB-backed tests drive the real ``run_eval`` end to end against
a synthetic three-memory corpus through a stubbed ``TwinningOrchestrator`` --
the shipped caching/token-attribution class with only the model round trip
replaced -- so the reproducibility guarantee under test is the one the real
composition produces, not a lookalike.
"""
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from benchlib import full_context, retrieval_gold, run_retrieval_eval, twin
from benchlib.retrieval_scorer import ScoreReport, SliceScore

pytestmark = pytest.mark.usefixtures("_bench_db")


# ── pure helpers: hand-built metric objects, no DB ───────────────────────


def _score_report(
    *, k=1, retrieval_limit=1, min_pairs=1, mrr=0.5, hit=0.5,
    multi_hop_mrr=1.0, multi_hop_hit=0.0, n=2,
) -> ScoreReport:
    """``multi_hop_hit`` defaults to 0.0 -- the real production DESIGNED
    state -- and is deliberately decoupled from ``hit`` (the "exact" slice's
    figure): fix round 1 made ``_designed_state_note`` branch on the exact
    multi-hop value, so a test exercising the aggregate-delta branch must not
    accidentally also exercise the drift branch by construction.
    """
    slices = {
        tag: SliceScore(slice_tag=tag, n_pairs=0, powered=False, mrr=None, hit_at_k=None)
        for tag in retrieval_gold.SLICES
    }
    slices["exact"] = SliceScore(slice_tag="exact", n_pairs=n, powered=True, mrr=mrr, hit_at_k=hit)
    slices["multi-hop"] = SliceScore(
        slice_tag="multi-hop", n_pairs=n, powered=True, mrr=multi_hop_mrr, hit_at_k=multi_hop_hit,
    )
    return ScoreReport(
        k=k, retrieval_limit=retrieval_limit, min_pairs=min_pairs, n_pairs=n,
        slices=slices, aggregate_powered=True, aggregate_mrr=mrr, aggregate_hit_at_k=hit,
        pair_scores={},
    )


def _twin_obj(*, live=0, cache=1, tokens=None, declared_channels=twin.CHANNELS) -> twin.Twin:
    recorder = twin.LatencyRecorder()
    for _ in range(live):
        recorder.record("end_to_end", 0.9, "live")
    for _ in range(cache):
        recorder.record("end_to_end", 0.001, "cache")
    captured = twin.Twin.capture(
        recorder, twin.TokenLedger(), min_samples=1, declared_channels=declared_channels,
    )
    if tokens is None:
        return captured
    return twin.Twin(
        channels=captured.channels, tokens_by_purpose=tokens, min_samples_for_percentile=1,
    )


def _comparison(
    *, retrieval_mrr=0.5, retrieval_hit=0.0, fc_mrr=0.8, fc_hit=0.9,
    retrieval_multi_hop_hit=0.0, fc_multi_hop_hit=0.9286,
) -> full_context.Comparison:
    retrieval_score = _score_report(mrr=retrieval_mrr, hit=retrieval_hit, multi_hop_hit=retrieval_multi_hop_hit)
    fc_score = _score_report(mrr=fc_mrr, hit=fc_hit, multi_hop_hit=fc_multi_hop_hit)
    retrieval_run = twin.EvalRun(score=retrieval_score, twin=_twin_obj())
    fc_run = twin.EvalRun(
        score=fc_score, twin=_twin_obj(declared_channels=full_context.CHANNELS),
    )
    context = full_context.ContextBlock(
        text="x", included_ids=("a",), dropped_ids=(), policy=full_context.ContextPolicy(),
    )
    return full_context.Comparison(
        retrieval=retrieval_run, full_context=fc_run,
        id_audit=full_context.IdAudit(), context=context,
    )


def _meta(**overrides) -> dict:
    base = {
        "run_id": "11111111-1111-1111-1111-111111111111",
        "timestamp": "2026-01-02T00:00:00+00:00",
        "date": "2026-01-02", "git_sha": "deadbeefcafef00d", "fingerprint": "stub-fp|3",
        "gate_config": {"ml_profile_ref": None, "classification_mode": "simple", "relation_rescue": True},
        "corpus_entries": 3, "gold_version": 1, "n_pairs_authored": 4, "n_pairs_live": 4,
        "retrieval_limit": 3, "full_context_limit": 3, "k": 1, "min_pairs": 1,
        "ingest_live_calls": 0, "retrieval_live_calls": 0, "full_context_live_calls": 0,
        "total_live_calls": 0,
    }
    base.update(overrides)
    return base


# ── pure tests ────────────────────────────────────────────────────────────


def test_report_path_is_the_dated_docs_eval_filename():
    p = run_retrieval_eval.report_path(date(2026, 3, 4), report_dir=Path("/tmp/x"))
    assert p == Path("/tmp/x/2026-03-04-retrieval-eval.md")


def test_score_summary_excludes_pair_level_detail_but_keeps_every_slice():
    score = _score_report(mrr=0.75, hit=0.5, n=3)
    summary = run_retrieval_eval._score_summary(score)
    assert "pair_scores" not in summary
    assert set(summary["slices"]) == retrieval_gold.SLICES
    assert summary["slices"]["exact"] == {"n_pairs": 3, "powered": True, "mrr": 0.75, "hit_at_k": 0.5}


def test_reproducible_metrics_excludes_latency_and_pair_level_detail():
    comparison = _comparison()
    metrics = run_retrieval_eval.reproducible_metrics(comparison)
    blob = json.dumps(metrics)
    assert "pair_scores" not in blob
    assert "p50" not in blob
    assert "p95" not in blob
    assert metrics["caveat_kinds"] == sorted(c.kind for c in comparison.caveats)


def test_reproducible_metrics_is_stable_across_two_identical_calls():
    comparison = _comparison()
    assert run_retrieval_eval.reproducible_metrics(comparison) == run_retrieval_eval.reproducible_metrics(comparison)


def test_designed_state_note_names_multi_hop_as_designed_when_hit_is_exactly_zero():
    comparison = _comparison(retrieval_multi_hop_hit=0.0)
    note = run_retrieval_eval._designed_state_note(comparison)
    assert "DESIGNED state" in note
    assert "multi-hop hit@1 = 0.0000" in note
    assert "DRIFT" not in note


def test_designed_state_note_flags_a_nonzero_multi_hop_hit_as_drift_to_investigate():
    """Fix round 1, F2: the note must not stamp every possible multi-hop
    value as designed. Proven at two different nonzero values so the branch
    is not coincidentally tied to one number."""
    for nonzero in (0.5, 1.0):
        comparison = _comparison(retrieval_multi_hop_hit=nonzero)
        note = run_retrieval_eval._designed_state_note(comparison)
        assert "DESIGNED state" not in note
        assert "DRIFT" in note
        assert "investigate" in note.lower()
        assert f"multi-hop hit@1 = {nonzero:.4f}" in note


def test_designed_state_note_names_full_context_winning_on_accuracy():
    comparison = _comparison(retrieval_mrr=0.5, fc_mrr=0.9, retrieval_multi_hop_hit=0.0)
    note = run_retrieval_eval._designed_state_note(comparison)
    assert "full context beats retrieval on pooled accuracy" in note


def test_designed_state_note_is_silent_when_retrieval_does_not_lose():
    comparison = _comparison(
        retrieval_mrr=0.9, fc_mrr=0.5, retrieval_hit=0.9, fc_hit=0.5, retrieval_multi_hop_hit=0.0,
    )
    note = run_retrieval_eval._designed_state_note(comparison)
    assert "full context beats retrieval" not in note


# ── pure tests: the F1 caveat-kind guard ─────────────────────────────────


def test_expected_caveat_kinds_matches_the_real_production_shape():
    """94 ingest calls, 102 full-context calls, retrieval cache_unknown,
    no live samples anywhere -- the exact three-caveat state
    task-T0.09-report.md F.5 records for the real 94-memory/102-pair corpus."""
    kinds = run_retrieval_eval._expected_caveat_kinds(
        retrieval_end_to_end_live=False, full_context_end_to_end_live=False,
        retrieval_cache_unknown=True, full_context_cache_unknown=False,
        retrieval_chat_calls=94, full_context_chat_calls=102,
    )
    assert kinds == {
        full_context.CAVEAT_LATENCY_NO_LIVE_SAMPLES,
        full_context.CAVEAT_COST_UNMEASURED,
        full_context.CAVEAT_COST_KIND_ASYMMETRY,
    }


def test_expected_caveat_kinds_still_expects_asymmetry_when_the_counts_coincide():
    """The named trap: full_context.Comparison's own per-purpose
    sum(...) == n_pairs heuristic goes blind the moment ingest calls equal
    the live pair count. This runner's independent derivation -- ingest is
    ALWAYS one-time indexing work, full-context is ALWAYS one call per pair
    -- must not share that blind spot."""
    kinds = run_retrieval_eval._expected_caveat_kinds(
        retrieval_end_to_end_live=False, full_context_end_to_end_live=False,
        retrieval_cache_unknown=False, full_context_cache_unknown=False,
        retrieval_chat_calls=3, full_context_chat_calls=3,
    )
    assert full_context.CAVEAT_COST_KIND_ASYMMETRY in kinds


def test_expected_caveat_kinds_expects_not_like_for_like_when_only_one_arm_is_live():
    kinds = run_retrieval_eval._expected_caveat_kinds(
        retrieval_end_to_end_live=True, full_context_end_to_end_live=False,
        retrieval_cache_unknown=False, full_context_cache_unknown=False,
        retrieval_chat_calls=0, full_context_chat_calls=0,
    )
    assert kinds == {full_context.CAVEAT_LATENCY_NOT_LIKE_FOR_LIKE}


def test_expected_caveat_kinds_expects_nothing_when_both_arms_are_live_and_symmetric():
    kinds = run_retrieval_eval._expected_caveat_kinds(
        retrieval_end_to_end_live=True, full_context_end_to_end_live=True,
        retrieval_cache_unknown=False, full_context_cache_unknown=False,
        retrieval_chat_calls=0, full_context_chat_calls=0,
    )
    assert kinds == set()


def test_assert_expected_caveats_raises_on_a_kind_that_did_not_fire():
    comparison = _comparison()
    actual = {c.kind for c in comparison.caveats}
    with pytest.raises(RuntimeError, match="not-a-real-kind"):
        run_retrieval_eval._assert_expected_caveats(comparison, actual | {"not-a-real-kind"})


def test_assert_expected_caveats_is_silent_when_every_expected_kind_fired():
    comparison = _comparison()
    actual = {c.kind for c in comparison.caveats}
    run_retrieval_eval._assert_expected_caveats(comparison, actual)  # must not raise
    run_retrieval_eval._assert_expected_caveats(comparison, set())  # a subset is fine too


def test_render_report_carries_git_sha_fingerprint_gate_config_and_both_sections():
    comparison = _comparison()
    meta = _meta()
    text = run_retrieval_eval.render_report(comparison, meta)

    assert meta["git_sha"] in text
    assert meta["fingerprint"] in text
    assert "ml_profile_ref=None" in text
    assert "## Comparison (human-readable)" in text
    assert "## Reproducibility" in text
    assert "```json" in text
    # The rendered per-slice table (never collapsed into only an aggregate).
    assert "exact" in text
    assert "AGGREGATE" in text


def test_render_reports_json_block_round_trips_reproducible_metrics():
    comparison = _comparison()
    meta = _meta()
    text = run_retrieval_eval.render_report(comparison, meta)
    start = text.index("```json\n") + len("```json\n")
    end = text.index("\n```", start)
    parsed = json.loads(text[start:end])
    assert parsed == run_retrieval_eval.reproducible_metrics(comparison)


# ── DB-backed: the real composition, a stubbed model ─────────────────────


def _mid(key: str) -> str:
    return retrieval_gold.memory_id_for_key(key)


def _write_corpus_and_gold(tmp_path, *, n_pairs=4):
    """3 memories always (ingest always bills exactly 3 chat calls); the
    live pair COUNT is the parameter the F1 trap test needs to control --
    at ``n_pairs=3`` the full-context arm also bills exactly 3 calls, so
    ingest calls == live pair count, the coincidence
    ``full_context.Comparison``'s own per-purpose heuristic goes blind to
    (fix round 1, F1)."""
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

    all_pairs = [
        {"id": "rt-0001", "query": "alpha", "relevant_memory_ids": [entries[0]["memory_id"]], "slice_tags": ["exact"]},
        {"id": "rt-0002", "query": "beta", "relevant_memory_ids": [entries[1]["memory_id"]], "slice_tags": ["exact"]},
        {"id": "rt-0003", "query": "gamma", "relevant_memory_ids": [entries[2]["memory_id"]], "slice_tags": ["exact"]},
        {"id": "rt-0004", "query": "alpha service", "relevant_memory_ids": [entries[0]["memory_id"]], "slice_tags": ["exact"]},
    ]
    pairs = all_pairs[:n_pairs]
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


def _answer_fn(pairs):
    by_query = {p["query"]: p["relevant_memory_ids"] for p in pairs}

    def answer(messages):
        user = messages[1]["content"]
        for query, ids in by_query.items():
            if f"<query>\n{query}\n</query>" in user:
                return json.dumps({"memory_ids": ids})
        return json.dumps({"memory_ids": []})

    return answer


class _StubTwinLLM(twin.TwinningOrchestrator):
    """The shipped twin orchestrator with only the model round trip
    replaced. The extraction/classification branch deliberately never calls
    ``_log_usage`` -- mirroring the real warm cache's pre-T0.08 entries,
    which carry no usage envelope -- so a replay reads back as
    ``cache_unknown``, exactly like the real 94-memory corpus's ingest cost
    does today (task-T0.09-report.md F.5)."""

    def __init__(self, config, cache_dir, *, answer_fn):
        super().__init__(config, cache_dir)
        self._answer_fn = answer_fn

    async def _live_embed(self, text):
        return _vec(text), "stub-embed|3"

    async def _live_embed_batch(self, texts):
        return [_vec(t) for t in texts], "stub-embed|3"

    async def _live_chat(self, purpose, messages, **kwargs):
        if purpose == full_context.FULL_CONTEXT_PURPOSE:
            self._log_usage(purpose, "stub-model", {"prompt_tokens": 10, "completion_tokens": 2})
            return self._answer_fn(messages)
        return _STUB_EXTRACTION


FIXED_DATE = datetime(2026, 1, 2, tzinfo=timezone.utc)


async def _three_runs(tmp_path, monkeypatch):
    """Cold, warm, warm -- see the module docstring: only the two WARM
    invocations are the reproducibility claim under test; the first call
    exists only to populate the disk cache, exactly as a real machine's
    very first invocation of run_retrieval_eval.py would."""
    corpus_path, gold_path, entries, pairs = _write_corpus_and_gold(tmp_path / "gold")
    responder = _answer_fn(pairs)

    def make_orchestrator(config, cache_dir):
        return _StubTwinLLM(config, cache_dir, answer_fn=responder)

    monkeypatch.setattr(run_retrieval_eval, "TwinningOrchestrator", make_orchestrator)

    kwargs = dict(
        deepseek_api_key="sk-not-used-in-test",
        cache_dir=tmp_path / "cache", corpus_path=corpus_path, gold_path=gold_path,
        k=1, min_pairs=1, full_context_limit=3,
        report_dir=tmp_path / "report", ledger_path=tmp_path / "ledger.jsonl", now=FIXED_DATE,
    )

    cold = await run_retrieval_eval.run_eval(**kwargs)
    warm1 = await run_retrieval_eval.run_eval(**kwargs)
    warm2 = await run_retrieval_eval.run_eval(**kwargs)
    return cold, warm1, warm2


@pytest.mark.asyncio
async def test_the_runner_refuses_when_ingest_calls_equal_the_live_pair_count(tmp_path, monkeypatch):
    """The exact trap ruling 2 names, and the reviewer's own reproduction:
    a corpus where the live pair count equals the ingest chat-call count
    (here 3 memories / 3 live pairs) makes ``Comparison.caveats``'s own
    per-purpose sum(...) == n_pairs heuristic (full_context.py, out of
    bounds) blind to cost-kind-asymmetry, even though ingest remains
    structurally one-time indexing work and full-context remains
    structurally one call per pair. The runner must refuse rather than
    silently write a report and ledger row reading "nothing to qualify" --
    proving the F1 guard bites in the production path, not only in a test
    against a hand-built ``Comparison``."""
    corpus_path, gold_path, entries, pairs = _write_corpus_and_gold(tmp_path / "trap", n_pairs=3)
    responder = _answer_fn(pairs)

    def make_orchestrator(config, cache_dir):
        return _StubTwinLLM(config, cache_dir, answer_fn=responder)

    monkeypatch.setattr(run_retrieval_eval, "TwinningOrchestrator", make_orchestrator)

    report_dir = tmp_path / "report"
    ledger_path = tmp_path / "ledger.jsonl"

    with pytest.raises(RuntimeError, match=full_context.CAVEAT_COST_KIND_ASYMMETRY):
        await run_retrieval_eval.run_eval(
            deepseek_api_key="sk-not-used-in-test",
            cache_dir=tmp_path / "cache", corpus_path=corpus_path, gold_path=gold_path,
            k=1, min_pairs=1, full_context_limit=3,
            report_dir=report_dir, ledger_path=ledger_path, now=FIXED_DATE,
        )

    # The refusal leaves no partial artifact: no report, no ledger row.
    assert not report_dir.exists() or not list(report_dir.glob("*.md"))
    assert not ledger_path.exists()


@pytest.mark.asyncio
async def test_the_first_run_actually_pays_live_calls(tmp_path, monkeypatch):
    cold, _, _ = await _three_runs(tmp_path, monkeypatch)
    assert cold.meta["total_live_calls"] > 0


@pytest.mark.asyncio
async def test_two_warm_runs_make_zero_live_calls(tmp_path, monkeypatch):
    _, warm1, warm2 = await _three_runs(tmp_path, monkeypatch)
    assert warm1.meta["total_live_calls"] == 0
    assert warm2.meta["total_live_calls"] == 0


@pytest.mark.asyncio
async def test_two_warm_runs_reproduce_the_metrics_block_byte_for_byte(tmp_path, monkeypatch):
    """The invariant ruling 3 is built around: two consecutive runs on an
    unchanged tree, against an unchanged warm cache, must be identical on
    every accuracy/token/audit/context/caveat figure."""
    _, warm1, warm2 = await _three_runs(tmp_path, monkeypatch)

    m1 = run_retrieval_eval.reproducible_metrics(warm1.comparison)
    m2 = run_retrieval_eval.reproducible_metrics(warm2.comparison)
    assert m1 == m2

    def _json_block(text):
        start = text.index("```json\n") + len("```json\n")
        end = text.index("\n```", start)
        return text[start:end]

    assert _json_block(warm1.report_text) == _json_block(warm2.report_text)


@pytest.mark.asyncio
async def test_a_warm_run_emits_the_expected_caveat_kinds_not_whatever_is_present(tmp_path, monkeypatch):
    """Ruling 2: assert the caveat kinds this scenario should produce rather
    than rendering whatever happens to be present. This scenario is
    engineered (3 ingest chat calls vs 4 full-context chat calls -- an
    asymmetric, nonzero pair; a fully warm second pass; an extraction stub
    that never attaches a usage envelope) to reproduce the exact
    three-caveat shape the real 94-memory/102-pair production run emits
    today (task-T0.09-report.md F.5)."""
    _, warm1, warm2 = await _three_runs(tmp_path, monkeypatch)

    expected = sorted([
        full_context.CAVEAT_COST_KIND_ASYMMETRY,
        full_context.CAVEAT_COST_UNMEASURED,
        full_context.CAVEAT_LATENCY_NO_LIVE_SAMPLES,
    ])
    assert run_retrieval_eval.reproducible_metrics(warm1.comparison)["caveat_kinds"] == expected
    assert run_retrieval_eval.reproducible_metrics(warm2.comparison)["caveat_kinds"] == expected


@pytest.mark.asyncio
async def test_the_report_is_written_to_the_dated_path_with_required_metadata(tmp_path, monkeypatch):
    _, warm1, warm2 = await _three_runs(tmp_path, monkeypatch)

    assert warm1.report_path == tmp_path / "report" / "2026-01-02-retrieval-eval.md"
    # The file on disk reflects whichever run wrote it LAST (warm2 here --
    # each run_id/timestamp is volatile by design, ruling 4's overwrite
    # discipline), so the disk-content check compares against the final
    # writer, not an earlier in-memory result.
    assert warm2.report_path.read_text() == warm2.report_text
    assert warm1.meta["git_sha"] in warm1.report_text
    assert warm1.meta["fingerprint"] in warm1.report_text
    assert warm1.meta["run_id"] in warm1.report_text
    assert "## Comparison (human-readable)" in warm1.report_text
    assert "## Reproducibility" in warm1.report_text


@pytest.mark.asyncio
async def test_a_rerun_on_the_same_date_overwrites_rather_than_minting_a_variant(tmp_path, monkeypatch):
    _, warm1, warm2 = await _three_runs(tmp_path, monkeypatch)
    assert warm1.report_path == warm2.report_path
    siblings = list((tmp_path / "report").glob("*.md"))
    assert siblings == [warm1.report_path]


@pytest.mark.asyncio
async def test_the_ledger_gains_one_row_per_run_via_the_sanctioned_call(tmp_path, monkeypatch):
    from benchlib import ledger as ledger_mod

    cold, warm1, warm2 = await _three_runs(tmp_path, monkeypatch)
    rows = ledger_mod.read_runs(warm1.ledger_path)
    # cold + warm1 + warm2 == 3 appended rows, one per run_eval() call.
    assert len(rows) == 3
    for row in rows:
        assert set(row["comparison"]["arms"]) == {"retrieval", "full_context"}
        assert "score" in row["comparison"]["arms"]["retrieval"]
        assert "twin" in row["comparison"]["arms"]["retrieval"]

    # Fix round 1, F3: rows are now individually identifiable and orderable.
    run_ids = {row["run_id"] for row in rows}
    assert len(run_ids) == 3  # distinct across the three calls
    for row, result in zip(rows, (cold, warm1, warm2)):
        assert row["run_id"] == result.meta["run_id"]
        assert row["timestamp"] == result.meta["timestamp"]
        assert row["git_sha"] == result.meta["git_sha"]
        assert row["fingerprint"] == result.meta["fingerprint"]

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


_MISSING = object()


def _certified_resample():
    return {"n": 93, "disagreements": 0, "seed": 4242,
            "performed_by": "owner", "date": "2026-08-06"}


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
    doc["resample"] = _certified_resample() if resample is _MISSING else resample
    return doc


def test_the_real_gold_is_eligible_with_counts_and_resample_surfaced():
    """The resample ran on 2026-08-08 (two non-Claude vendors, 0 disagreements
    each), which was the last outstanding condition. This pinned the *refusal*
    until then; it now pins the eligibility, and the counts stay surfaced either
    way so a future composition change is visible in the reasons rather than
    only in a boolean.

    The conditions themselves are still exercised against synthetic golds
    below -- an eligible real gold must not become the only thing this file
    checks, or the lock would be untested the moment it matters.
    """
    doc = entailment_gold.load_entailment_gold()
    eligibility = jq.gate_eligibility(doc)
    assert eligibility.eligible is True
    assert eligibility.live_pairs == 241
    assert eligibility.l2_fact_pairs == 153
    assert eligibility.author_labelled_pairs == 0
    joined = "\n".join(eligibility.reasons)
    assert "l2-fact: 153/241" in joined
    assert "author-labelled: 0/241" in joined
    assert "resample" not in joined

    resample = doc["resample"]
    assert resample["n"] == 93
    assert resample["disagreements"] == 0
    # No human sat, and the record must say so on its face.
    assert "LLM" in resample["performed_by"]


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

    jq.write_qualification_record(
        record_path, gold_path=gold_path, identity=identity, score=perfect,
        gold_doc=_synthetic_gold(200, 100, 0), ledger_run_id="run-1",
        bars=dict(vj.VERIFICATION_BAR_DEFAULTS), git_sha="deadbeef",
        timestamp="2026-07-31T00:00:00+00:00",
    )
    record = json.loads(record_path.read_text())
    assert record["gold_sha256"] == hashlib.sha256(gold_path.read_bytes()).hexdigest()
    assert record["ledger_run_id"] == "run-1"
    assert record["gate_eligible"] is True
    assert record["judge_identity"]["identity_hash"] == vj.judge_identity_hash(identity)

    async def default_bars(_session):
        return dict(vj.VERIFICATION_BAR_DEFAULTS)

    monkeypatch.setattr(vj, "get_verification_bars", default_bars)
    import asyncio
    state = asyncio.run(vj.qualification_state(
        None, {"verification": cfg}, record_path=record_path,
    ))
    assert state.qualified is True, state.reasons


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

    # Leg 1: the canonical record path refuses a non-canonical gold.
    with pytest.raises(ValueError):
        jq.write_qualification_record(
            vj.QUALIFICATION_RECORD_PATH, gold_path=fixture_gold, **common,
        )
    assert not vj.QUALIFICATION_RECORD_PATH.exists()

    # Leg 2: a relative-path spelling of the canonical location refuses too.
    dodged = vj.QUALIFICATION_RECORD_PATH.parent / ".." / "services" / \
        vj.QUALIFICATION_RECORD_PATH.name
    with pytest.raises(ValueError):
        jq.write_qualification_record(dodged, gold_path=fixture_gold, **common)
    assert not vj.QUALIFICATION_RECORD_PATH.exists()

    # Leg 3: a rehearsal record path accepts any gold.
    rehearsal = tmp_path / "rehearsal-record.json"
    jq.write_qualification_record(rehearsal, gold_path=fixture_gold, **common)
    assert rehearsal.exists()

    # Leg 4: the canonical pairing works (canonical constant pointed at tmp).
    tmp_canonical = tmp_path / "verification_qualification.json"
    monkeypatch.setattr(vj, "QUALIFICATION_RECORD_PATH", tmp_canonical)
    jq.write_qualification_record(
        tmp_canonical, gold_path=entailment_gold.GOLD_PATH, **common,
    )
    assert tmp_canonical.exists()


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


def _premise_of(user_content):
    return user_content.split("PREMISE:\n", 1)[1].split("\n\nHYPOTHESIS:", 1)[0]


def _run(tmp_path, stub_cls, **kwargs):
    defaults = dict(
        deepseek_api_key="sk-test",
        report_dir=tmp_path / "reports",
        ledger_path=tmp_path / "ledger.jsonl",
        cache_dir=tmp_path / "cache",
        orchestrator_cls=stub_cls,
    )
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
        pairs.append({
            "id": f"eg-{i:04d}",
            "premise": f"Synthetic fact {i} holds value {i}.",
            "hypothesis": f"Value {i} is held by synthetic fact {i}.",
            "verdict": "entailed",
            "slice_tags": ["verbatim"],
            "provenance": "hand-authored-synthetic-fact",
            "label_source": "adjudicated",
            "rationale": "synthetic eligibility fixture",
        })
    doc = {
        "version": 99,
        "variant": "claim-fact",
        "declared_slice_counts": {s: (n if s == "verbatim" else 0)
                                  for s in entailment_gold.SLICES},
        "declared_verdict_counts": {v: (n if v == "entailed" else 0)
                                    for v in entailment_gold.VERDICTS},
        "declared_provenance_counts": {
            "l2-fact": n_l2,
            "hand-authored-synthetic-fact": n - n_l2,
            "hand-authored-bench-corpus": 0,
            "synthesis-draft": 0,
        },
        # An eligible gold must now carry a certified resample: Layer 3's
        # n = 93 / <= 1 disagreement is what measures label accuracy, and the
        # lock enforces it since 2026-08-06.
        "resample": _certified_resample(),
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
    assert not vj.QUALIFICATION_RECORD_PATH.exists()

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
    gold_sha = hashlib.sha256(entailment_gold.GOLD_PATH.read_bytes()).hexdigest()
    ledger.record({"kind": "judge_qualification_attempt", "intent_row_id": "a1",
                   "identity_hash": "aaaa", "gold_sha256": gold_sha}, path=ledger_path)
    ledger.record({"kind": "judge_qualification_attempt", "intent_row_id": "a2",
                   "identity_hash": "bbbb", "gold_sha256": gold_sha}, path=ledger_path)
    ledger.record({"kind": "judge_qualification_attempt", "intent_row_id": "a3",
                   "identity_hash": "cccc", "gold_sha256": "other"}, path=ledger_path)

    stub_cls, _seen = make_stub(cycling_script())
    result = _run(tmp_path, stub_cls)

    scored = ledger.read_runs(ledger_path)[-1]
    assert scored["gold_touching_attempts"] == 3
    assert "gold_touching_attempts: 3" in result.report_path.read_text()


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
    doc = entailment_gold.load_entailment_gold()
    doc.pop("resample", None)          # the one condition, removed deliberately
    gold_path = tmp_path / "no-resample-gold.json"
    gold_path.write_text(json.dumps(doc), encoding="utf-8")

    stub_cls, seen = make_stub(cycling_script())
    with pytest.raises(RuntimeError) as excinfo:
        _run(tmp_path, stub_cls, gate=True, gold_path=gold_path,
             record_path=tmp_path / "must-not-be-written.json")
    message = str(excinfo.value)
    assert "resample" in message
    assert seen == [], "eligibility refusal must precede any model call"
    assert not (tmp_path / "must-not-be-written.json").exists()
    assert not vj.QUALIFICATION_RECORD_PATH.exists()


def test_gate_rehearsal_writes_only_a_non_default_record(tmp_path):
    gold_path = _write_eligible_gold(tmp_path)
    record_path = tmp_path / "rehearsal-record.json"
    stub_cls, _seen = make_stub(cycling_script())
    result = _run(tmp_path, stub_cls, gate=True, gold_path=gold_path,
                  record_path=record_path)

    record = json.loads(record_path.read_text())
    assert record["gate_eligible"] is True
    assert record["gold_sha256"] == hashlib.sha256(gold_path.read_bytes()).hexdigest()
    assert record["ledger_run_id"] == result.meta["run_id"]

    # The same rehearsal aimed at the real canonical record path refuses —
    # the minting lock, exercised through the runner surface.
    stub_cls2, _ = make_stub(cycling_script())
    with pytest.raises(ValueError):
        _run(tmp_path / "second", stub_cls2, gate=True, gold_path=gold_path,
             record_path=vj.QUALIFICATION_RECORD_PATH)
    assert not vj.QUALIFICATION_RECORD_PATH.exists()


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
    assert gold.live.n == result.score.n_pairs == 241


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

"""T2.26 — the `verification`-purpose judge: probe, parsing, bars, and (Task 2+)
the computed qualification gate and its source scans."""
import json

import pytest

from app.models.config import Config
from app.services.extraction_clean import _content_seed
from app.services import verification_judge as vj


class StubLLM:
    """Minimal orchestrator stand-in: records every chat_completion call's
    arguments and replays canned responses in order."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def chat_completion(self, purpose, messages, response_format=None, seed=None):
        self.calls.append({
            "purpose": purpose,
            "messages": messages,
            "response_format": response_format,
            "seed": seed,
        })
        return self.responses.pop(0)


# ── probe + parsing ──────────────────────────────────────────────────────


@pytest.mark.parametrize("verdict", ["entailed", "contradicted", "unsupported"])
async def test_probe_parses_each_lawful_verdict(verdict):
    llm = StubLLM([json.dumps({"verdict": verdict, "reason": "because"})])
    judge = vj.VerificationJudge(llm)
    result = await judge.qualification_probe("p is true", "h follows")
    assert result.valid is True
    assert result.verdict == verdict
    assert result.reason == "because"


@pytest.mark.parametrize("raw", [
    '{"verdict": "supported", "reason": "untabled verdict"}',
    "this is not json at all",
    "",
])
async def test_probe_never_raises_on_malformed_output(raw):
    llm = StubLLM([raw])
    judge = vj.VerificationJudge(llm)
    result = await judge.qualification_probe("p", "h")
    assert result.valid is False
    assert result.verdict is None
    assert result.raw == raw


async def test_probe_fallback_accepts_a_bare_verdict_token():
    llm = StubLLM(["The verdict is: contradicted"])
    judge = vj.VerificationJudge(llm)
    result = await judge.qualification_probe("p", "h")
    assert result.valid is True
    assert result.verdict == "contradicted"


async def test_probe_fallback_rejects_ambiguous_multi_token_output():
    llm = StubLLM(["either entailed or unsupported, hard to say"])
    judge = vj.VerificationJudge(llm)
    result = await judge.qualification_probe("p", "h")
    assert result.valid is False
    assert result.verdict is None


# ── call construction ────────────────────────────────────────────────────


async def test_probe_dispatches_on_the_verification_purpose_with_seed():
    llm = StubLLM([json.dumps({"verdict": "entailed", "reason": "r"})])
    judge = vj.VerificationJudge(llm)
    premise, hypothesis = "Postgres runs on 5433", "Postgres is reachable"
    await judge.qualification_probe(premise, hypothesis)

    call = llm.calls[0]
    assert call["purpose"] == "verification"
    assert call["response_format"] == {"type": "json_object"}
    assert call["seed"] == _content_seed(premise + "\n" + hypothesis)


def test_messages_are_byte_stable_for_the_same_pair():
    first = vj.build_messages("p text", "h text")
    second = vj.build_messages("p text", "h text")
    assert first == second
    assert first[0]["role"] == "system"
    assert first[1]["role"] == "user"
    assert "p text" in first[1]["content"]
    assert "h text" in first[1]["content"]


def test_system_prompt_names_all_three_verdicts():
    for token in ("entailed", "contradicted", "unsupported"):
        assert f'"{token}"' in vj.SYSTEM_PROMPT


def test_verdict_vocabulary_is_the_gold_three():
    # app/ must not import benchlib, so the set is declared here; the drift
    # guard against entailment_gold.VERDICTS lives in the benchlib suite.
    assert vj.JUDGE_VERDICTS == frozenset({"entailed", "contradicted", "unsupported"})


# ── bars: config rows over stated defaults ───────────────────────────────


RECALL_BAR = "contradiction_recall_bar"


def _state_the_recall_bar(session, value=0.90):
    """T2.109 barred contradiction-recall with no default, so every test that
    wants a resolvable bar set has to state it — the same act a deployment
    performs, and the reason the gate is closed until one does."""
    session.add(Config(key=RECALL_BAR, value={"value": value}))


def test_bar_defaults_are_the_stated_values():
    assert vj.VERIFICATION_BAR_DEFAULTS == {
        # Truth-critical metrics at 0.95, the other at 0.90 — doc 17 §6's rule,
        # which predates every judge run. The amendment moved which
        # contradiction metric is truth-critical; it did not move the rule.
        "groundedness_gate_precision_bar": 0.95,
        "groundedness_gate_recall_bar": 0.90,
        "contradiction_recall_bar": 0.95,
        # Not a truth number since 2026-08-08: a review-load floor.
        "contradiction_precision_bar": 0.70,
    }


def test_contradiction_recall_is_gated_and_barred_by_derivation():
    """Doc 17 §6's 2026-08-08 amendment plus the bars stated under it.

    Recall is barred (so it cannot be ignored) at **0.95**, the value the
    section's own rule gives the truth-critical metric — the rule predates
    every judge run, and the amendment is what made recall truth-critical.

    The second assertion is the one that matters. 0.90 is where a bar chosen
    to clear the measured judge would sit: gpt-5.5 scored contradiction-recall
    0.945, so 0.90 passes it and 0.95 does not. Pinning *against* that value
    is how this file records that the bar was derived rather than fitted.
    """
    assert vj.BAR_METRICS[RECALL_BAR] == "contradiction_recall"
    assert vj.VERIFICATION_BAR_DEFAULTS[RECALL_BAR] == 0.95
    assert vj.VERIFICATION_BAR_DEFAULTS[RECALL_BAR] != 0.90


def test_contradiction_precision_is_a_review_load_floor_not_a_truth_bar():
    """It moved 0.95 -> 0.70 because its consumer changed, not because it was
    missed. A false flag now costs a reviewer a minute rather than a wrong
    belief, so the bar only has to keep the queue workable — noise a clear
    minority. Left at 0.95 it would price precision as truth after §6 stopped
    doing so, and block the gate for a reason unrelated to being right."""
    assert vj.VERIFICATION_BAR_DEFAULTS["contradiction_precision_bar"] == 0.70


async def test_bars_fall_back_to_defaults_on_an_empty_config_table(session):
    _state_the_recall_bar(session)
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars == {**vj.VERIFICATION_BAR_DEFAULTS, RECALL_BAR: 0.90}


async def test_an_unstated_bar_raises_rather_than_resolving(session, monkeypatch):
    """The mechanism, exercised on a barred key that genuinely has no default.

    It used to be exercised on `contradiction_recall_bar`, which was unstated
    by design until 2026-08-08. Stating that bar would have retired this guard
    silently — the mechanism is for *any* future barred metric, not for that
    one, so it is tested against a synthetic key instead.
    """
    monkeypatch.setitem(vj.BAR_METRICS, "a_future_bar", "some_metric")
    with pytest.raises(ValueError, match="a_future_bar"):
        await vj.get_verification_bars(session)


async def test_a_db_bar_row_wins_per_key(session):
    session.add(Config(key="groundedness_gate_recall_bar", value={"value": 0.8}))
    _state_the_recall_bar(session)
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars["groundedness_gate_recall_bar"] == 0.8
    assert bars["groundedness_gate_precision_bar"] == 0.95
    assert bars["contradiction_precision_bar"] == 0.70


async def test_a_bare_scalar_bar_row_is_also_read(session):
    session.add(Config(key="contradiction_precision_bar", value=0.97))
    session.add(Config(key=RECALL_BAR, value=0.88))
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars["contradiction_precision_bar"] == 0.97
    assert bars[RECALL_BAR] == 0.88


async def test_a_malformed_bar_row_raises_not_silently_defaults(session):
    # Falling back to the default would ignore an operator's attempt to
    # move a bar — conservative relative to defaults, not to intent.
    session.add(Config(key="groundedness_gate_precision_bar", value={"value": "0.99"}))
    _state_the_recall_bar(session)
    await session.commit()
    with pytest.raises(ValueError, match="groundedness_gate_precision_bar"):
        await vj.get_verification_bars(session)


# ── qualification state: computed, never remembered (Task 2) ─────────────


def _judge_config(**overrides):
    from app.config import LLMPurposeConfig
    fields = {
        "model": "deepseek-v4-flash",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-test",
        "api_kind": "deepseek",
        "params": {"temperature": 0, "max_tokens": 256, "thinking": {"type": "disabled"}},
    }
    fields.update(overrides)
    return {"verification": LLMPurposeConfig(**fields)}


def _record(llm_config, metrics=None, gate_eligible=True, **extra):
    identity = vj.judge_identity(llm_config["verification"])
    payload = {
        "judge_identity": {**identity, "identity_hash": vj.judge_identity_hash(identity)},
        "metrics": metrics if metrics is not None else {
            "entailed_precision": 1.0,
            "entailed_recall": 1.0,
            "contradiction_precision": 1.0,
            "contradiction_recall": 1.0,
        },
        "gate_eligible": gate_eligible,
        "gold_sha256": "0" * 64,
        "ledger_run_id": "test-run",
        "recorded_at": "2026-07-31T00:00:00+00:00",
        "git_sha": "deadbeef",
    }
    payload.update(extra)
    return payload


def _write_record(tmp_path, payload):
    path = tmp_path / "verification_qualification.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


async def test_no_record_means_unqualified(session, tmp_path):
    state = await vj.qualification_state(
        session, _judge_config(), record_path=tmp_path / "absent.json",
    )
    assert state.qualified is False
    assert any("no qualification record" in r for r in state.reasons)


async def test_a_malformed_record_fails_closed(session, tmp_path):
    path = tmp_path / "verification_qualification.json"
    path.write_text("{not json", encoding="utf-8")
    state = await vj.qualification_state(session, _judge_config(), record_path=path)
    assert state.qualified is False


async def test_gate_ineligible_record_is_unqualified(session, tmp_path):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg, gate_eligible=False))
    state = await vj.qualification_state(session, cfg, record_path=path)
    assert state.qualified is False
    assert any("gate_eligible" in r for r in state.reasons)


async def test_a_matching_clearing_record_qualifies(session, tmp_path):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg))
    _state_the_recall_bar(session)
    await session.commit()
    state = await vj.qualification_state(session, cfg, record_path=path)
    assert state.qualified is True
    assert state.reasons == ()


async def test_an_unstated_bar_fails_closed_naming_it(session, tmp_path, monkeypatch):
    """The posture the malformed-bar-row test already establishes, applied to
    any barred metric with no value: the module fails loud rather
    than defaulting, and the reason says which number is missing so an operator
    is not left guessing at a gate that will not open."""
    monkeypatch.setitem(vj.BAR_METRICS, "a_future_bar", "some_metric")
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg))
    state = await vj.qualification_state(session, cfg, record_path=path)
    assert state.qualified is False
    assert any("a_future_bar" in r and "failing closed" in r for r in state.reasons)


async def test_the_gate_cannot_qualify_a_near_mute_judge(session, tmp_path):
    """The incoherence that forced doc 08 §4.2's redesign, asserted here.

    Measured against the shipped scorer on 2026-08-08: a judge emitting
    ``contradicted`` on exactly one correct pair of the gold's 55 and
    ``unsupported`` everywhere else scores contradiction-precision 1.0, leaves
    entailed precision/recall untouched, and passed all three then-gated bars
    at contradiction-recall 1/55 = 0.0182 — qualifying a judge that finds
    nothing to hold an absolute veto.

    Every metric below except the recall is the near-mute judge's *best* case,
    so nothing but the new bar can be what refuses it. Removing
    ``contradiction_recall_bar`` from ``BAR_METRICS`` reddens this test.
    """
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg, metrics={
        "entailed_precision": 1.0,
        "entailed_recall": 1.0,
        "contradiction_precision": 1.0,
        "contradiction_recall": 1 / 55,
    }))
    _state_the_recall_bar(session)
    await session.commit()

    state = await vj.qualification_state(session, cfg, record_path=path)
    assert state.qualified is False
    assert any("contradiction_recall" in r for r in state.reasons)


async def test_a_model_swap_is_detected_not_remembered(session, tmp_path):
    path = _write_record(tmp_path, _record(_judge_config()))
    swapped = _judge_config(model="deepseek-v4-pro")
    state = await vj.qualification_state(session, swapped, record_path=path)
    assert state.qualified is False
    assert any("identity" in r for r in state.reasons)


async def test_metrics_below_the_default_bar_are_unqualified(session, tmp_path):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg, metrics={
        "entailed_precision": 0.94,
        "entailed_recall": 1.0,
        "contradiction_precision": 1.0,
        "contradiction_recall": 1.0,
    }))
    _state_the_recall_bar(session)
    await session.commit()
    state = await vj.qualification_state(session, cfg, record_path=path)
    assert state.qualified is False
    assert any("groundedness_gate_precision_bar" in r for r in state.reasons)


async def test_raising_a_db_bar_flips_a_qualified_record_back(session, tmp_path):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg, metrics={
        "entailed_precision": 1.0,
        "entailed_recall": 0.95,
        "contradiction_precision": 1.0,
        "contradiction_recall": 1.0,
    }))
    _state_the_recall_bar(session)
    await session.commit()
    state = await vj.qualification_state(session, cfg, record_path=path)
    assert state.qualified is True

    session.add(Config(key="groundedness_gate_recall_bar", value={"value": 1.0}))
    await session.commit()
    state = await vj.qualification_state(session, cfg, record_path=path)
    assert state.qualified is False


@pytest.mark.parametrize("metrics", [
    {"entailed_recall": 1.0, "contradiction_precision": 1.0,
     "contradiction_recall": 1.0},                                         # absent
    {"entailed_precision": None, "entailed_recall": 1.0,
     "contradiction_precision": 1.0, "contradiction_recall": 1.0},         # None
])
async def test_missing_or_null_metrics_fail_closed(session, tmp_path, metrics):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg, metrics=metrics))
    _state_the_recall_bar(session)
    await session.commit()
    state = await vj.qualification_state(session, cfg, record_path=path)
    assert state.qualified is False
    assert any("entailed_precision" in r for r in state.reasons)


async def test_unreadable_bars_fail_the_qualification_closed(session, tmp_path):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg))
    session.add(Config(key="groundedness_gate_recall_bar", value="not-a-number"))
    await session.commit()
    state = await vj.qualification_state(session, cfg, record_path=path)
    assert state.qualified is False
    assert any("failing closed" in r for r in state.reasons)


# ── the gated door ───────────────────────────────────────────────────────


async def test_judge_refuses_when_unqualified(session, tmp_path, monkeypatch):
    monkeypatch.setattr(vj, "QUALIFICATION_RECORD_PATH", tmp_path / "absent.json")
    llm = StubLLM([json.dumps({"verdict": "entailed", "reason": "r"})])
    llm.config = _judge_config()
    judge = vj.VerificationJudge(llm)
    with pytest.raises(vj.JudgeNotQualifiedError):
        await judge.judge(session, "p", "h")
    assert llm.calls == []


async def test_judge_answers_when_qualified(session, tmp_path, monkeypatch):
    llm = StubLLM([json.dumps({"verdict": "contradicted", "reason": "r"})])
    llm.config = _judge_config()
    path = _write_record(tmp_path, _record(llm.config))
    monkeypatch.setattr(vj, "QUALIFICATION_RECORD_PATH", path)
    _state_the_recall_bar(session)
    await session.commit()
    judge = vj.VerificationJudge(llm)
    result = await judge.judge(session, "p", "h")
    assert result.valid is True
    assert result.verdict == "contradicted"


def test_the_gated_door_accepts_no_record_path():
    # A caller-supplied record path would reopen the rehearsal-record bypass
    # one level above the writer's minting lock: a --gate rehearsal may
    # legitimately write a qualifying record from an easy gold to any
    # non-default path, and a consumer pointing the door at it would run as
    # qualified with nothing flagging it. Only the canonical, minting-locked
    # record may qualify a consumer call.
    import inspect
    params = list(inspect.signature(vj.VerificationJudge.judge).parameters)
    assert params == ["self", "session", "premise", "hypothesis"]


# ── identity: what moves the hash, and what must not ─────────────────────


def test_api_key_never_affects_the_identity():
    a = vj.judge_identity(_judge_config()["verification"])
    b = vj.judge_identity(_judge_config(api_key="sk-rotated")["verification"])
    assert vj.judge_identity_hash(a) == vj.judge_identity_hash(b)


def test_prompt_version_moves_the_identity(monkeypatch):
    before = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    # Relative to whatever the current version is, not a literal: pinning "2"
    # here made this test pass only while the shipped version was 1, and it
    # went red the first time the prompt was legitimately revised.
    monkeypatch.setattr(vj, "JUDGE_PROMPT_VERSION", vj.JUDGE_PROMPT_VERSION + 1)
    after = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    assert before != after


def test_system_prompt_text_moves_the_identity(monkeypatch):
    before = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    monkeypatch.setattr(vj, "SYSTEM_PROMPT", vj.SYSTEM_PROMPT + " ")
    after = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    assert before != after


def test_prompt_sha_separates_the_two_texts(monkeypatch):
    # sha256(system + template) without a separator would let text migrate
    # across the boundary while keeping the hash.
    monkeypatch.setattr(vj, "SYSTEM_PROMPT", "AB")
    monkeypatch.setattr(vj, "USER_TEMPLATE", "C")
    moved_boundary = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    monkeypatch.setattr(vj, "SYSTEM_PROMPT", "A")
    monkeypatch.setattr(vj, "USER_TEMPLATE", "BC")
    assert moved_boundary != vj.judge_identity_hash(
        vj.judge_identity(_judge_config()["verification"])
    )


def test_user_template_text_moves_the_identity(monkeypatch):
    before = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    monkeypatch.setattr(vj, "USER_TEMPLATE", vj.USER_TEMPLATE + " ")
    after = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    assert before != after


def test_the_canonical_record_is_absent_on_this_branch():
    # The zero-pin: only a gate-eligible --gate run (T2.41's) may mint the
    # record, so its first appearance must be a deliberate diff that
    # consciously edits this test.
    assert not vj.QUALIFICATION_RECORD_PATH.exists()


# ── source scans: one door to the purpose, and off the hot path ──────────

import re as _re  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

_BACKEND = _Path(__file__).resolve().parent.parent

# The exact quoted token, single- or double-quoted. Matching the token itself
# (not a same-line co-occurrence with chat_completion) is what closes the
# two-line bypass: PURPOSE = "verification" / chat_completion(PURPOSE, msgs).
# Identifier substrings (verification_status, verification_recompute) carry
# no closing quote after "verification" and cannot match.
_QUOTED_VERIFICATION = _re.compile(r"""["']verification["']""")

# The only modules under app/ where the quoted purpose token is lawful today.
# Extend ONLY with a written justification here — never by loosening the
# match rule. (app/config.py was verified to carry no quoted token; it is
# deliberately NOT pre-opened.)
_QUOTED_TOKEN_ALLOWLIST = {
    "app/services/verification_judge.py",   # the judge itself
    "app/services/llm_seed.py",             # the purpose seed row
    "app/services/config.py",               # PURPOSES + get_llm_config defaults
}

# Modules that may reference the judge module or its ungated probe. A consumer
# joins here consciously — and must use judge(), never the probe. For the one
# member below that is re-proved against the parsed tree by
# `test_the_ungated_probe_is_unreachable` and
# `test_the_only_adjudicating_call_is_the_gated_door`, both in
# tests/test_contradiction_scan.py.
_JUDGE_REFERENCE_ALLOWLIST = {
    "app/services/verification_judge.py",
    # T2.11's Tier-C contradiction scan: the first consumer, and gated by the
    # judge's own refusal rather than by this list.
    "app/services/contradiction_scan.py",
    # T3.02's review-queue articles arm. It imports `article_claim_gate` — the
    # judge's *qualification-record* accessor — and never the purpose, the
    # probe or `judge()`. It is here rather than exempted because the reason
    # the single door exists is that two modules must not decide whether the
    # judge is qualified: the queue asks this module and serves the answer, so
    # the door is honoured rather than bypassed. `test_the_article_gate_reads_
    # the_record_and_never_the_purpose` below re-proves the narrow form against
    # the parsed tree, the way the contradiction scan's membership is re-proved.
    "app/services/review_queue.py",
    # T3.03's claim-entailment pass: the second real consumer of the judge,
    # and gated the same way the contradiction scan is — by `judge()`'s own
    # refusal rather than by this list. Re-proved narrowly below.
    "app/services/claim_entailment.py",
    # T3.02/T3.03's synthesis tick constructs the judge and hands it down to
    # the pass. It never calls `judge()` itself and never touches the probe;
    # the construction is here because the judge is built per tick rather
    # than held, so a configuration an operator changed takes effect on the
    # next run. Re-proved narrowly below.
    "app/services/article_synthesis.py",
}

# Capture/retrieval-path modules the judge may NEVER be reachable from
# (invariant 15) — even once consumers exist and the reference allowlist
# grows. This list is a floor with a maintenance duty: any new capture- or
# retrieval-path service (T2.42's facts channel is already minted as a task)
# joins it, and the whole-branch review checks it.
_HOT_PATH_MODULES = {
    "app/services/pipeline.py",
    "app/services/hybrid_search.py",
    "app/services/memory_buffer.py",
    "app/services/memory.py",
    "app/services/code_query.py",
    "app/services/reranker.py",
    "app/services/layer_composition.py",
    "app/services/verified_evidence.py",
}


def _app_sources() -> list[_Path]:
    return [p for p in (_BACKEND / "app").rglob("*.py") if "__pycache__" not in str(p)]


def _rel(path: _Path, root: _Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _single_door_offenders(paths: list[_Path], root: _Path) -> list[str]:
    offenders = []
    for path in paths:
        rel = _rel(path, root)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _QUOTED_VERIFICATION.search(line) and rel not in _QUOTED_TOKEN_ALLOWLIST:
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
            if ("qualification_probe" in line or "verification_judge" in line) \
                    and rel not in _JUDGE_REFERENCE_ALLOWLIST:
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    return offenders


def _hot_path_offenders(paths: list[_Path], root: _Path) -> list[str]:
    offenders = []
    for path in paths:
        rel = _rel(path, root)
        if rel not in _HOT_PATH_MODULES and not rel.startswith("app/api/"):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "verification_judge" in line:
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    return offenders


def _assert_scan_floor(paths: list[_Path]) -> None:
    assert len(paths) > 100, (
        f"only found {len(paths)} files under app/ — the source scan would "
        "pass vacuously; check _BACKEND / the glob path"
    )


def test_only_the_judge_module_reaches_the_verification_purpose():
    paths = _app_sources()
    _assert_scan_floor(paths)
    offenders = _single_door_offenders(paths, _BACKEND)
    assert not offenders, (
        "a module outside the judge reached the verification purpose or its "
        "ungated probe — every consumer must go through "
        "VerificationJudge.judge(), the gated door (doc 17 §6):\n"
        + "\n".join(offenders)
    )


def test_single_door_scan_flags_a_direct_dispatch(tmp_path):
    offending = tmp_path / "app" / "services" / "sneaky.py"
    offending.parent.mkdir(parents=True)
    offending.write_text(
        'async def check(llm, msgs):\n'
        '    return await llm.chat_completion("verification", msgs)\n'
    )
    offenders = _single_door_offenders([offending], tmp_path)
    assert offenders and "verification" in offenders[0]


def test_single_door_scan_flags_the_two_line_indirection(tmp_path):
    offending = tmp_path / "app" / "services" / "sneaky.py"
    offending.parent.mkdir(parents=True)
    offending.write_text(
        'PURPOSE = "verification"\n'
        "async def check(llm, msgs):\n"
        "    return await llm.chat_completion(PURPOSE, msgs)\n"
    )
    offenders = _single_door_offenders([offending], tmp_path)
    assert offenders, "the two-line indirection must still be flagged"


def test_single_door_scan_flags_a_probe_call(tmp_path):
    offending = tmp_path / "app" / "services" / "sneaky.py"
    offending.parent.mkdir(parents=True)
    offending.write_text(
        "async def check(judge, p, h):\n"
        "    return await judge.qualification_probe(p, h)\n"
    )
    offenders = _single_door_offenders([offending], tmp_path)
    assert offenders and "qualification_probe" in offenders[0]


def test_single_door_scan_ignores_identifier_substrings(tmp_path):
    clean = tmp_path / "app" / "services" / "fine.py"
    clean.parent.mkdir(parents=True)
    clean.write_text(
        'JOB = "verification_recompute"\n'
        "verification_status = 'candidate'\n"
    )
    assert _single_door_offenders([clean], tmp_path) == []


def test_the_judge_is_unreachable_from_capture_and_retrieval():
    paths = _app_sources()
    _assert_scan_floor(paths)
    offenders = _hot_path_offenders(paths, _BACKEND)
    assert not offenders, (
        "a capture/retrieval-path module reached the verification judge — "
        "invariant 15: Tier-C only, never the hot path:\n" + "\n".join(offenders)
    )


def test_hot_path_scan_flags_a_planted_route_import(tmp_path):
    offending = tmp_path / "app" / "api" / "routes" / "articles.py"
    offending.parent.mkdir(parents=True)
    offending.write_text(
        "from app.services.verification_judge import VerificationJudge\n"
    )
    offenders = _hot_path_offenders([offending], tmp_path)
    assert offenders and "verification_judge" in offenders[0]


def test_hot_path_scan_flags_a_planted_pipeline_import(tmp_path):
    offending = tmp_path / "app" / "services" / "pipeline.py"
    offending.parent.mkdir(parents=True)
    offending.write_text("from app.services import verification_judge\n")
    offenders = _hot_path_offenders([offending], tmp_path)
    assert offenders


def test_the_article_gate_reads_the_record_and_never_the_purpose():
    """`review_queue`'s allowlist membership, re-proved narrowly.

    Joining `_JUDGE_REFERENCE_ALLOWLIST` buys a module the right to reference
    the judge; it must not buy the right to dispatch it. The articles arm may
    read the qualification record through `article_claim_gate` and nothing
    else — no `judge(`, no probe, no `verification` purpose string.
    """
    import ast as _ast

    root = _Path(__file__).resolve().parents[1]
    source = (root / "app/services/review_queue.py").read_text(encoding="utf-8")
    tree = _ast.parse(source)

    imported: list[str] = []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.ImportFrom) and node.module == (
            "app.services.verification_judge"
        ):
            imported.extend(alias.name for alias in node.names)

    assert imported == ["article_claim_gate"], (
        "the articles arm may read the qualification record and nothing else; "
        f"it imports {imported}"
    )
    assert "judge(" not in source
    assert "qualification_probe" not in source


def test_the_entailment_consumers_use_the_gated_door_and_never_the_probe():
    """Allowlist membership buys the right to *reference* the judge; it must
    not buy the right to bypass it.

    `claim_entailment` calls `judge()` — the qualification-gated door whose
    refusal is what makes T3.03 safe to build before G-D clears — and
    `article_synthesis` only constructs the judge and hands it down. Neither
    may reach `qualification_probe`, which is scan-pinned to the harness
    precisely because it is ungated.
    """
    root = _Path(__file__).resolve().parents[1]

    entailment = (root / "app/services/claim_entailment.py").read_text(encoding="utf-8")
    assert "judge.judge(" in entailment, "the pass must enter through the gated door"
    assert "qualification_probe" not in entailment
    assert "qualification_state" not in entailment, (
        "the pass asks the door, never the record — two modules deciding "
        "whether the judge is qualified is the drift the single door prevents"
    )

    synthesis = (root / "app/services/article_synthesis.py").read_text(encoding="utf-8")
    assert "VerificationJudge(llm)" in synthesis
    assert "qualification_probe" not in synthesis
    assert ".judge(" not in synthesis, (
        "the tick hands the judge down; the pass is what asks it"
    )

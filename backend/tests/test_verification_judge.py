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


def test_bar_defaults_are_the_stated_values():
    assert vj.VERIFICATION_BAR_DEFAULTS == {
        "groundedness_gate_precision_bar": 0.95,
        "groundedness_gate_recall_bar": 0.90,
        "contradiction_precision_bar": 0.95,
    }


async def test_bars_fall_back_to_defaults_on_an_empty_config_table(session):
    bars = await vj.get_verification_bars(session)
    assert bars == vj.VERIFICATION_BAR_DEFAULTS


async def test_a_db_bar_row_wins_per_key(session):
    session.add(Config(key="groundedness_gate_recall_bar", value={"value": 0.8}))
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars["groundedness_gate_recall_bar"] == 0.8
    assert bars["groundedness_gate_precision_bar"] == 0.95
    assert bars["contradiction_precision_bar"] == 0.95


async def test_a_bare_scalar_bar_row_is_also_read(session):
    session.add(Config(key="contradiction_precision_bar", value=0.97))
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars["contradiction_precision_bar"] == 0.97


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
    state = await vj.qualification_state(session, cfg, record_path=path)
    assert state.qualified is True
    assert state.reasons == ()


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
    }))
    state = await vj.qualification_state(session, cfg, record_path=path)
    assert state.qualified is False
    assert any("groundedness_gate_precision_bar" in r for r in state.reasons)


async def test_raising_a_db_bar_flips_a_qualified_record_back(session, tmp_path):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg, metrics={
        "entailed_precision": 1.0,
        "entailed_recall": 0.95,
        "contradiction_precision": 1.0,
    }))
    state = await vj.qualification_state(session, cfg, record_path=path)
    assert state.qualified is True

    session.add(Config(key="groundedness_gate_recall_bar", value={"value": 1.0}))
    await session.commit()
    state = await vj.qualification_state(session, cfg, record_path=path)
    assert state.qualified is False


@pytest.mark.parametrize("metrics", [
    {"entailed_recall": 1.0, "contradiction_precision": 1.0},              # absent
    {"entailed_precision": None, "entailed_recall": 1.0,
     "contradiction_precision": 1.0},                                      # None
])
async def test_missing_or_null_metrics_fail_closed(session, tmp_path, metrics):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg, metrics=metrics))
    state = await vj.qualification_state(session, cfg, record_path=path)
    assert state.qualified is False
    assert any("entailed_precision" in r for r in state.reasons)


# ── the gated door ───────────────────────────────────────────────────────


async def test_judge_refuses_when_unqualified(session, tmp_path):
    llm = StubLLM([json.dumps({"verdict": "entailed", "reason": "r"})])
    llm.config = _judge_config()
    judge = vj.VerificationJudge(llm)
    with pytest.raises(vj.JudgeNotQualifiedError):
        await judge.judge(session, "p", "h", record_path=tmp_path / "absent.json")
    assert llm.calls == []


async def test_judge_answers_when_qualified(session, tmp_path):
    llm = StubLLM([json.dumps({"verdict": "contradicted", "reason": "r"})])
    llm.config = _judge_config()
    path = _write_record(tmp_path, _record(llm.config))
    judge = vj.VerificationJudge(llm)
    result = await judge.judge(session, "p", "h", record_path=path)
    assert result.valid is True
    assert result.verdict == "contradicted"


# ── identity: what moves the hash, and what must not ─────────────────────


def test_api_key_never_affects_the_identity():
    a = vj.judge_identity(_judge_config()["verification"])
    b = vj.judge_identity(_judge_config(api_key="sk-rotated")["verification"])
    assert vj.judge_identity_hash(a) == vj.judge_identity_hash(b)


def test_prompt_version_moves_the_identity(monkeypatch):
    before = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    monkeypatch.setattr(vj, "JUDGE_PROMPT_VERSION", 2)
    after = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    assert before != after


def test_system_prompt_text_moves_the_identity(monkeypatch):
    before = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    monkeypatch.setattr(vj, "SYSTEM_PROMPT", vj.SYSTEM_PROMPT + " ")
    after = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    assert before != after


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

# Modules that may reference the judge module or its ungated probe. Empty
# beyond the judge itself: no consumer exists yet (T2.11, T3.03). A future
# consumer joins here consciously — and must use judge(), never the probe.
_JUDGE_REFERENCE_ALLOWLIST = {
    "app/services/verification_judge.py",
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

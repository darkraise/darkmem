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

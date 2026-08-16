"""The faithfulness gate runs before serving (TH1.09, doc 16 §4).

The property that matters is an **ordering**: no caller can obtain a grounded
answer without the check having already decided. A gate that runs after the
answer is on the wire has failed, and a gate that a caller can skip is not a
gate — so `GatedAnswer.grounded` is the only thing that reads as grounded, and
it is False for everything except `SERVED`.

Today no faithfulness qualification record exists, so the real judge refuses
and every answer is withheld. That is asserted as the shipped behaviour rather
than mocked away: an unqualified judge must not be able to bless a grounded
label, and the honesty/withheld-not-grounded spec is exactly that assertion.
The scripted judges below are how the *other* branches are reachable at all.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from app.models.config import Config
from app.services import block_embeddings as be_mod
from app.services.document_ingest import BlockDraft, file_document
from app.services.faithfulness_gate import FaithfulnessGate, Outcome
from app.services.grounded_qa import GroundedQaService
from app.services.verification_judge import FAITHFULNESS_ROLE, JudgeNotQualifiedError

pytestmark = pytest.mark.asyncio

FINGERPRINT = "th109-probe|4"
PROJECT = "th109-docs"

DIRECTIONS = {"alpha": [1.0, 0.0, 0.0, 0.0]}
FALLBACK = [0.0, 0.0, 0.0, 1.0]


def _direction(value: str) -> list[float]:
    head = value.split()[0].lower() if value.split() else ""
    return DIRECTIONS.get(head, FALLBACK)


class ScriptedLlm:
    def __init__(self, payload=None):
        self.payload = payload

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([_direction(t) for t in texts], FINGERPRINT)

    async def embed(self, value: str):
        return _direction(value), FINGERPRINT

    async def chat_completion(self, purpose, messages, **kwargs):
        return json.dumps(self.payload or {"sentences": []})


class _Verdict:
    def __init__(self, verdict: str):
        self.verdict = verdict


class ScriptedJudge:
    """Answers each call from a list, and records the role it was asked for."""

    def __init__(self, verdicts):
        self.verdicts = list(verdicts)
        self.roles: list[str] = []
        self.premises: list[str] = []

    async def judge(self, session, premise, hypothesis, *, role):
        self.roles.append(role)
        self.premises.append(premise)
        return _Verdict(self.verdicts.pop(0) if self.verdicts else "not_entailed")


class RefusingJudge:
    def __init__(self):
        self.calls = 0

    async def judge(self, session, premise, hypothesis, *, role):
        self.calls += 1
        raise JudgeNotQualifiedError("no faithfulness record on this branch")


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


async def _answer(session, sentences, *, block_text="alpha the sky is blue"):
    drafts = [BlockDraft(text=block_text, type="paragraph", char_span=(0, len(block_text)))]
    ingest = await file_document(
        session, project=PROJECT, content=block_text,
        parse=lambda: drafts, title="doc", source_type="note",
    )
    await session.flush()
    block_ids = [str(r) for r in (await session.execute(
        text("SELECT id FROM blocks WHERE document_id = CAST(:d AS uuid)"),
        {"d": str(ingest.document_id)},
    )).scalars().all()]
    await be_mod.embed_blocks(session, ScriptedLlm(), block_ids=block_ids)

    payload = {"sentences": [
        {"text": s["text"], "block_id": block_ids[0] if s["cited"] else None,
         "span_start": 0, "span_end": 5}
        for s in sentences
    ]}
    return await GroundedQaService(session, ScriptedLlm(payload)).answer(
        "alpha", project=PROJECT,
    )


# ── the shipped behaviour: no record, so nothing is served as grounded ──


async def test_the_real_judge_refuses_today_and_the_answer_is_withheld(session):
    """honesty/withheld-not-grounded, against the real judge rather than a
    stand-in: no faithfulness qualification record exists on this branch, so
    the gate cannot clear and must not serve."""
    from app.services.verification_judge import VerificationJudge

    class _Llm:
        # Only the resolved config is read before the refusal — no model call
        # is reachable from an unqualified judge, which is the point.
        config = {"model": "probe", "base_url": "http://probe", "api_kind": "openai"}

    answer = await _answer(session, [{"text": "The sky is blue.", "cited": True}])

    gated = await FaithfulnessGate(session, VerificationJudge(llm=_Llm())).check(answer)

    assert gated.outcome is Outcome.WITHHELD
    assert gated.grounded is False
    assert gated.judged is False
    assert gated.label == "answer withheld: not grounded"


async def test_an_unqualified_judge_withholds_rather_than_labelling(session):
    """"We could not check" must not be served in the shape of "we checked and
    it is partly grounded" — those are different things to tell a human."""
    answer = await _answer(session, [{"text": "Claim.", "cited": True}])
    judge = RefusingJudge()

    gated = await FaithfulnessGate(session, judge).check(answer, allow_labelled=True)

    assert gated.outcome is Outcome.WITHHELD
    assert gated.judged is False


# ── the decision, once a judge can run ───────────────────────────────


async def test_a_fully_supported_answer_is_served(session):
    answer = await _answer(session, [
        {"text": "One.", "cited": True}, {"text": "Two.", "cited": True},
    ])

    gated = await FaithfulnessGate(session, ScriptedJudge(["entailed", "entailed"])).check(answer)

    assert gated.outcome is Outcome.SERVED
    assert gated.grounded is True
    assert (gated.entailed, gated.total) == (2, 2)
    assert gated.label is None


async def test_a_partially_supported_answer_is_labelled_never_grounded(session):
    answer = await _answer(session, [
        {"text": "One.", "cited": True}, {"text": "Two.", "cited": True},
    ])

    gated = await FaithfulnessGate(session, ScriptedJudge(["entailed", "not_entailed"])).check(answer)

    assert gated.outcome is Outcome.LABELLED
    assert gated.grounded is False
    assert gated.label == "could not fully ground this answer"
    assert (gated.entailed, gated.total) == (1, 2)


async def test_a_caller_that_refuses_labels_gets_the_answer_withheld(session):
    answer = await _answer(session, [
        {"text": "One.", "cited": True}, {"text": "Two.", "cited": True},
    ])

    gated = await FaithfulnessGate(session, ScriptedJudge(["entailed", "not_entailed"])).check(
        answer, allow_labelled=False,
    )

    assert gated.outcome is Outcome.WITHHELD
    assert gated.grounded is False


async def test_an_uncited_sentence_is_not_entailed_and_is_never_sent_to_the_judge(session):
    """Doc 16 §4: a claim with no citation fails outright, with no
    search-for-support fallback. Searching for a span that would support it is
    how a grounding check turns into a grounding service."""
    answer = await _answer(session, [
        {"text": "Cited.", "cited": True}, {"text": "Uncited.", "cited": False},
    ])
    judge = ScriptedJudge(["entailed"])

    gated = await FaithfulnessGate(session, judge).check(answer)

    assert len(judge.roles) == 1, "the uncited sentence must not reach the judge"
    assert gated.outcome is Outcome.LABELLED
    assert (gated.entailed, gated.total) == (1, 2)


async def test_an_empty_answer_is_withheld_rather_than_vacuously_cleared(session):
    answer = await _answer(session, [])

    gated = await FaithfulnessGate(session, ScriptedJudge([])).check(answer)

    assert gated.outcome is Outcome.WITHHELD
    assert (gated.entailed, gated.total) == (0, 0)


# ── one judge, its own role, on the cited span ───────────────────────


async def test_the_gate_asks_for_the_faithfulness_role(session):
    answer = await _answer(session, [{"text": "One.", "cited": True}])
    judge = ScriptedJudge(["entailed"])

    await FaithfulnessGate(session, judge).check(answer)

    assert judge.roles == [FAITHFULNESS_ROLE]
    assert FAITHFULNESS_ROLE == "faithfulness"


async def test_the_premise_is_the_cited_span_not_the_whole_block(session):
    """The discrimination this role is qualified for is claim/span. Sending the
    whole block would ask an easier question than the one the bar was set
    against, and would quietly grade a wider premise as if it were the span."""
    answer = await _answer(
        session, [{"text": "One.", "cited": True}],
        block_text="alpha the sky is blue and much else besides",
    )
    judge = ScriptedJudge(["entailed"])

    await FaithfulnessGate(session, judge).check(answer)

    assert judge.premises == ["alpha"], "the premise must be the cited span"


# ── the threshold is a config row ────────────────────────────────────


async def test_an_unlicensed_loosening_clamps_back_and_the_answer_is_not_served(session):
    """The threshold is a config row **under the floor-clamp shape**, which is
    the more important half: a bare row loosening the bar is honoured by
    nothing. Written first because it is the direction an operator reaches for
    when an answer will not serve."""
    session.add(Config(key="faithfulness_coverage_bar", value={"value": 0.5}))
    await session.flush()

    answer = await _answer(session, [
        {"text": "One.", "cited": True}, {"text": "Two.", "cited": True},
    ])
    gated = await FaithfulnessGate(session, ScriptedJudge(["entailed", "not_entailed"])).check(answer)

    assert gated.outcome is Outcome.LABELLED, "an unlicensed loosening was honoured"


async def test_a_licensed_loosening_is_read_at_decision_time(session):
    """And the read really happens: with a licence naming the parameter, its
    value and where the argument lives, the same partial answer clears. Without
    this the test above would also pass against a gate that ignored config
    entirely."""
    session.add(Config(key="faithfulness_coverage_bar", value={"value": 0.5}))
    session.add(Config(
        key="faithfulness_bar_licences",
        value={"licensed": {"faithfulness_coverage_bar": {
            "value": 0.5, "argument": "gate-ledger.md#th1.09-test",
        }}},
    ))
    await session.flush()

    answer = await _answer(session, [
        {"text": "One.", "cited": True}, {"text": "Two.", "cited": True},
    ])
    gated = await FaithfulnessGate(session, ScriptedJudge(["entailed", "not_entailed"])).check(answer)

    assert gated.outcome is Outcome.SERVED, "the licensed config row was not read"

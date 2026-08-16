"""The span-support faithfulness gate, run **before serving** (TH1.09).

Doc 16 §4: an answer that clears the gate is served with its span-anchored
citations; one below the bar is returned labelled or withheld, **never
presented as if grounded** (invariant 14). This module is the decision, and it
sits between `GroundedQaService.answer` and whatever serves the result — the
ordering is the requirement, not a detail, because a gate that runs after the
answer is on the wire has already failed.

**One judge, its own role.** The check calls `judge(role="faithfulness")`.
That is a third role rather than a reuse of `entailment`: the discrimination is
the same word and a different premise distribution — raw document span text,
which the claim/fact gold does not represent — so the entailment record
qualifies articles and not this (TH1.01's spec §3, doc 17 §6's per-role
amendment). Today no faithfulness record exists, so `judge()` refuses and every
answer is withheld. **That is the gate working**, not a bug to route around:
the judge is unqualified for this discrimination and an unqualified judge must
not be able to bless a grounded label.

**Three outcomes, and the middle one is the point.** `served` when every
sentence's cited span entails it; `labelled` when some do and the caller asked
for the honest partial; `withheld` when the caller did not, or when the judge
could not run at all. A two-outcome gate collapses "we checked and it is
partly grounded" into "we could not check", which are different things to tell
a human.

**Counts, never a rate.** `answer_grounded` takes `(entailed, total)` because
39/40 and 975/1000 are the same 0.975 and not the same evidence, and because a
rate cannot express the zero-claim refusal — an answer with no claims grounds
nothing and must never clear vacuously.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.faithfulness_bars import answer_grounded, get_faithfulness_bars
from app.services.grounded_qa import CitedSentence, GroundedAnswer
from app.services.verification_judge import (
    FAITHFULNESS_ROLE,
    JudgeNotQualifiedError,
)

logger = logging.getLogger(__name__)

__all__ = ["GatedAnswer", "Outcome", "FaithfulnessGate"]


class Outcome(str, Enum):
    SERVED = "served"
    LABELLED = "labelled"
    WITHHELD = "withheld"


@dataclass(frozen=True)
class GatedAnswer:
    """The serving decision, with the counts it was made on.

    `grounded` is the *only* thing a caller may read as "this is grounded", and
    it is False for everything except `SERVED`. The counts ride along so a
    surface can say how far short an answer fell without recomputing anything —
    and so a reader can tell a judge that refused (`judged=False`) from one
    that ran and disagreed.
    """

    outcome: Outcome
    answer: GroundedAnswer
    entailed: int
    total: int
    judged: bool
    reason: str | None = None
    sentence_verdicts: list[bool] = field(default_factory=list)

    @property
    def grounded(self) -> bool:
        return self.outcome is Outcome.SERVED

    @property
    def label(self) -> str | None:
        if self.outcome is Outcome.SERVED:
            return None
        if self.outcome is Outcome.LABELLED:
            return "could not fully ground this answer"
        return "answer withheld: not grounded"


class FaithfulnessGate:
    def __init__(self, session: AsyncSession, judge) -> None:
        self.session = session
        self.judge = judge

    async def check(
        self, answer: GroundedAnswer, *, allow_labelled: bool = True,
    ) -> GatedAnswer:
        """Decide before serving. Never mutates the answer."""
        bars = await get_faithfulness_bars(self.session)

        if not answer.sentences:
            # Zero claims ground nothing. Refused rather than vacuously
            # cleared, so an empty body cannot collect the strongest label.
            return GatedAnswer(
                outcome=Outcome.WITHHELD, answer=answer, entailed=0, total=0,
                judged=False, reason="the answer carries no claims to ground",
            )

        verdicts: list[bool] = []
        for sentence in answer.sentences:
            try:
                verdicts.append(await self._entails(sentence, answer))
            except JudgeNotQualifiedError as exc:
                # The judge is not admitted for this discrimination. Withheld,
                # never labelled: "we could not check" must not be served in
                # the shape of "we checked and it is partly grounded".
                logger.info("faithfulness gate: judge unqualified — withholding")
                return GatedAnswer(
                    outcome=Outcome.WITHHELD, answer=answer, entailed=0,
                    total=len(answer.sentences), judged=False, reason=str(exc),
                )

        entailed = sum(1 for verdict in verdicts if verdict)
        total = len(verdicts)
        if answer_grounded(entailed, total, bars):
            return GatedAnswer(
                outcome=Outcome.SERVED, answer=answer, entailed=entailed,
                total=total, judged=True, sentence_verdicts=verdicts,
            )

        return GatedAnswer(
            outcome=Outcome.LABELLED if allow_labelled else Outcome.WITHHELD,
            answer=answer, entailed=entailed, total=total, judged=True,
            reason=f"{entailed}/{total} sentences are supported by their cited span",
            sentence_verdicts=verdicts,
        )

    async def _entails(self, sentence: CitedSentence, answer: GroundedAnswer) -> bool:
        """Does the cited span entail this sentence?

        An uncited sentence is **not** sent to the judge and is not entailed:
        doc 16 §4 is explicit that a claim with no citation fails outright,
        with no search-for-support fallback. Searching for a span that would
        support it is how a grounding check turns into a grounding *service*.
        """
        if sentence.citation is None:
            return False
        block = next(
            (hit for hit in answer.blocks if hit.block_id == sentence.citation.block_id),
            None,
        )
        if block is None:  # pragma: no cover - grounded_qa validates this first
            return False
        start, end = sentence.citation.char_span
        verdict = await self.judge.judge(
            self.session,
            premise=block.text[start:end],
            hypothesis=sentence.text,
            role=FAITHFULNESS_ROLE,
        )
        return getattr(verdict, "verdict", None) == "entailed"

"""Claim-level entailment and coverage routing (T3.03, doc 09 §4.3).

Doc 09 calls this "the single most important mechanism in the doc: it is what
makes an article's badge honest". Without it, synthesis is a fluent paraphrase
that *looks* grounded; with it, every shipped sentence is provably backed by a
verified fact.

**Coverage is entailed claims / total claims, and it *is* the article's stored
``confidence``** (doc 09 §4.3). So an article's confidence means exactly "the
fraction of my sentences a verified fact entails" — a computable number rather
than a heuristic.

**Unmeasured is not zero, and the distinction is the module's spine.** A
refusing judge, a vendor outage and an invalid response all produce "no
entailment verdict", and none of them is evidence that a claim is ungrounded.
``0.0`` means *measured, and nothing was entailed*; ``None`` means *not
measured*, which is what T3.02 fixed NULL as the spelling of. Treating an
unavailable judge as evidence of ungroundedness is what would let one outage
silently demote an entire corpus.

**This module imports nothing from ``article_synthesis``, and that is invariant
15 rather than taste.** ``dream_jobs`` imports ``article_synthesis``, which
makes it a forbidden module for every non-umbrella file; a hot-path module
reaching this one would otherwise acquire an unpoliced transitive route to the
dream family, because the scan checks direct reach per file. So this module
defines its own :class:`Claim` and the synthesis side adapts *downward* into
it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.services.verification_judge import (
    JudgeNotQualifiedError,
    VerificationJudge,
)

__all__ = [
    "COVERAGE_CONFIG_KEY",
    "DEFAULT_COVERAGE_THRESHOLD",
    "Claim",
    "ClaimVerdict",
    "CoverageOutcome",
    "CoverageResult",
    "coverage",
    "get_coverage_threshold",
    "measure_coverage",
]

# The row and field, named here because two modules read them — this pass and
# `review_queue`'s reason arm — and an unnamed key is how two spellings happen.
COVERAGE_CONFIG_KEY = "article_coverage"
COVERAGE_THRESHOLD_FIELD = "threshold"

# G-E's coverage bar, stated before any measurement exists (no coverage number
# has ever been measured anywhere, so fitting it is impossible — the same
# discipline that committed the promotion bars before the first run). It is
# **convention-recorded, not clamp-enforced**: unlike the verification ladder's
# floors there is no machinery here that refuses a loosening, so lowering it is
# a convention-9 move that owes a recorded argument in the gate ledger.
#
# Quantisation, stated because it bites: at 0.95 any article under 20 claims
# requires *every* claim entailed.
DEFAULT_COVERAGE_THRESHOLD = 0.95

ENTAILED = "entailed"


class ClaimVerdict(str, Enum):
    """What one claim's check concluded.

    ``UNMEASURED`` is a first-class outcome rather than an error code: it is
    what a refusing judge, a vendor error and an invalid response all produce,
    and none of them says anything about the claim.
    """

    ENTAILED = "entailed"
    NOT_ENTAILED = "not_entailed"
    UNCITED = "uncited"
    UNMEASURED = "unmeasured"


class CoverageOutcome(str, Enum):
    """What the pass concluded about the article as a whole."""

    PROMOTED = "promoted"
    HELD = "held"
    UNMEASURED = "unmeasured"


@dataclass(frozen=True)
class Claim:
    """One article sentence and the fact ids proposed to ground it.

    Deliberately *not* ``article_synthesis.DraftSentence`` — see the module
    docstring. The synthesis side builds these; nothing here knows that type
    exists.
    """

    text: str
    fact_ids: tuple[str, ...] = ()
    # The article-body span this claim occupies, for the citation row's
    # `claim_span`. Optional so a caller measuring coverage alone need not
    # compute one.
    span: tuple[int, int] | None = None


@dataclass
class CoverageResult:
    """The pass's answer. **Returned, never raised** (T3.03 D14).

    Raising into `run_article_synthesis`'s per-subject `try` would make each
    subject increment both `written` and `failed` — and with G-D open that is
    every article, every tick, so a permanent standing state would read as a
    permanent vendor outage. Three outcomes for three states instead.
    """

    outcome: CoverageOutcome
    coverage: float | None
    verdicts: list[ClaimVerdict] = field(default_factory=list)
    entailed: list[tuple[Claim, str]] = field(default_factory=list)
    reason: str | None = None

    @property
    def has_uncited(self) -> bool:
        return ClaimVerdict.UNCITED in self.verdicts


def coverage(verdicts: list[ClaimVerdict]) -> float | None:
    """Entailed claims over total claims, or ``None`` when unmeasured.

    Three rules, each of them a decision:

    - **One unmeasurable claim makes the whole article unmeasured.** Scoring
      what *was* measured changes the denominator per run, which would let a
      mostly-errored article promote on a 3-of-25 sample of itself — a
      false-promotion channel.
    - **An uncited claim is in the denominator and never in the numerator.**
      Doc 09 §4.3: an uncited span is by definition ungrounded, with no
      search-for-support fallback.
    - **No claims is ``None``, never ``1.0``.** An article with nothing to
      check is not a perfectly grounded one, and 0/0 rendering as full
      coverage is the vacuity that would promote an empty article.
    """
    if not verdicts:
        return None
    if any(v is ClaimVerdict.UNMEASURED for v in verdicts):
        return None
    entailed = sum(1 for v in verdicts if v is ClaimVerdict.ENTAILED)
    return entailed / len(verdicts)


async def get_coverage_threshold(session: AsyncSession) -> float:
    """The effective bar: the config row over the committed default."""
    row = (
        await session.execute(
            text(
                "SELECT value FROM config WHERE key = CAST(:k AS text)"
            ),
            {"k": COVERAGE_CONFIG_KEY},
        )
    ).scalar_one_or_none()
    if isinstance(row, dict):
        value = row.get(COVERAGE_THRESHOLD_FIELD)
        if isinstance(value, (int, float)):
            return float(value)
    return DEFAULT_COVERAGE_THRESHOLD


async def measure_coverage(
    session: AsyncSession,
    judge: VerificationJudge,
    *,
    claims: list[Claim],
    fact_text: dict[str, str],
    threshold: float | None = None,
) -> CoverageResult:
    """Check every claim against its cited facts and decide the routing.

    ``fact_text`` maps a fact id to the fact's own sentence — the premise. The
    caller supplies it because this module does not read the vault.

    **Grounded iff *any* cited fact entails the claim** (doc 09 §4.2 lets the
    model propose several). Asked per (claim, cited-fact) pair with early exit,
    so a conjunction-grounded sentence — one no single fact entails — fails
    toward review, which is the safe direction.

    **Serial, on one session.** ``judge()`` recomputes the qualification state
    on the session it is handed, so concurrent calls on one session are
    illegal. The per-article loop is where the cost bound already lives.
    """
    bar = threshold if threshold is not None else await get_coverage_threshold(session)

    verdicts: list[ClaimVerdict] = []
    entailed: list[tuple[Claim, str]] = []

    for claim in claims:
        if not claim.fact_ids:
            verdicts.append(ClaimVerdict.UNCITED)
            continue

        outcome = ClaimVerdict.NOT_ENTAILED
        grounding: str | None = None
        for fact_id in claim.fact_ids:
            premise = fact_text.get(fact_id)
            if premise is None:
                # A cited id with no text is not an unentailed claim; it is a
                # caller that did not hand over what it cited.
                continue
            try:
                verdict = await judge.judge(session, premise, claim.text)
            except JudgeNotQualifiedError as refusal:
                # The whole article is unmeasurable, and asking the remaining
                # claims cannot change that — so stop, rather than spending
                # C-k more refusals.
                return CoverageResult(
                    outcome=CoverageOutcome.UNMEASURED,
                    coverage=None,
                    verdicts=verdicts + [ClaimVerdict.UNMEASURED],
                    reason=str(refusal),
                )
            except Exception as error:  # noqa: BLE001 - an outage is not evidence
                return CoverageResult(
                    outcome=CoverageOutcome.UNMEASURED,
                    coverage=None,
                    verdicts=verdicts + [ClaimVerdict.UNMEASURED],
                    reason=f"the judge could not be reached: {error}",
                )

            if not verdict.valid:
                # Neither an exception nor a verdict. The qualification
                # scorer's counts-as-a-miss rule is a scoring convention for
                # measuring the *judge*; it is not evidence about the claim.
                return CoverageResult(
                    outcome=CoverageOutcome.UNMEASURED,
                    coverage=None,
                    verdicts=verdicts + [ClaimVerdict.UNMEASURED],
                    reason="the judge returned an unparseable verdict",
                )
            if verdict.verdict == ENTAILED:
                outcome = ClaimVerdict.ENTAILED
                grounding = fact_id
                break

        verdicts.append(outcome)
        if outcome is ClaimVerdict.ENTAILED and grounding is not None:
            entailed.append((claim, grounding))

    score = coverage(verdicts)
    if score is None:
        return CoverageResult(
            outcome=CoverageOutcome.UNMEASURED, coverage=None, verdicts=verdicts,
            reason="no claims to measure" if not verdicts else None,
        )

    # **An uncited claim blocks promotion outright**, regardless of coverage.
    # The done-when is "uncited sentences are impossible in a shipped article",
    # and a fractional bar does not deliver it: at twenty claims one uncited
    # claim still clears 0.95. A tightening, lawful without amendment.
    uncited = ClaimVerdict.UNCITED in verdicts
    if score >= bar and not uncited:
        return CoverageResult(
            outcome=CoverageOutcome.PROMOTED, coverage=score, verdicts=verdicts,
            entailed=entailed,
        )
    return CoverageResult(
        outcome=CoverageOutcome.HELD, coverage=score, verdicts=verdicts,
        entailed=entailed,
        reason="an uncited claim" if uncited else "coverage below the threshold",
    )

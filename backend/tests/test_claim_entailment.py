"""T3.03 — the claim-level entailment pass and coverage routing (doc 09 §4.3).

The suite's spine is one distinction: **unmeasured is not zero.** A refusing
judge, a vendor outage and an invalid response all produce "no entailment
verdict", and none of them is evidence that a claim is ungrounded. Every test
that could be satisfied by conflating them is written so it cannot be.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services import claim_entailment as ce
from app.services.verification_judge import (
    JudgeNotQualifiedError,
    ProbeVerdict,
)

pytestmark = pytest.mark.asyncio

V = ce.ClaimVerdict


class _StubJudge:
    """Answers per (premise, hypothesis) pair, and counts what it was asked."""

    def __init__(self, answers=None, raises=None, invalid=False):
        self.answers = answers or {}
        self.raises = raises
        self.invalid = invalid
        self.asked: list[tuple[str, str]] = []

    async def judge(self, session, premise, hypothesis):
        self.asked.append((premise, hypothesis))
        if self.raises is not None:
            raise self.raises
        if self.invalid:
            return ProbeVerdict(verdict=None, reason=None, raw="???", valid=False)
        verdict = self.answers.get((premise, hypothesis), "unsupported")
        return ProbeVerdict(verdict=verdict, reason=None, raw=verdict, valid=True)


def _claim(text_: str, *fact_ids: str) -> ce.Claim:
    return ce.Claim(text=text_, fact_ids=tuple(fact_ids))


# ─────────────── Step 1: the pure calculation ───────────────


class TestCoverage:
    async def test_all_entailed_is_one(self):
        assert ce.coverage([V.ENTAILED, V.ENTAILED]) == 1.0

    async def test_an_uncited_claim_is_in_the_denominator_never_the_numerator(self):
        """Doc 09 §4.3: an uncited span is by definition ungrounded, with no
        search-for-support fallback."""
        assert ce.coverage([V.ENTAILED, V.UNCITED]) == 0.5

    async def test_a_not_entailed_claim_lowers_the_fraction(self):
        assert ce.coverage([V.ENTAILED, V.NOT_ENTAILED]) == 0.5

    async def test_one_unmeasurable_claim_makes_the_whole_article_unmeasured(self):
        """Scoring what *was* measured changes the denominator per run, which
        would let a mostly-errored article promote on a 3-of-25 sample of
        itself — a false-promotion channel."""
        assert ce.coverage([V.ENTAILED, V.ENTAILED, V.UNMEASURED]) is None

    async def test_no_claims_is_none_not_one(self):
        """The vacuity that would promote an empty article: 0/0 rendering as
        full coverage. An article with nothing to check is not a perfectly
        grounded one."""
        assert ce.coverage([]) is None

    async def test_nothing_entailed_is_zero_which_is_not_none(self):
        """0.0 means measured and nothing entailed; None means not measured.
        A calculation that returned None here would make an outage and a
        thoroughly ungrounded article indistinguishable."""
        assert ce.coverage([V.NOT_ENTAILED, V.NOT_ENTAILED]) == 0.0


# ─────────────── Step 2: the per-claim pass ───────────────


class TestThePass:
    async def test_it_asks_the_judge_per_claim_and_fact_pair(self, session):
        """`fact_ids` is a list, so the cost is the pair count, not the claim
        count — the correction D7 carries."""
        judge = _StubJudge(answers={("f1 says", "c1"): "entailed"})

        await ce.measure_coverage(
            session, judge,
            claims=[_claim("c1", "f1"), _claim("c2", "f2", "f3")],
            fact_text={"f1": "f1 says", "f2": "f2 says", "f3": "f3 says"},
        )

        assert judge.asked == [
            ("f1 says", "c1"), ("f2 says", "c2"), ("f3 says", "c2"),
        ]

    async def test_a_claim_is_grounded_if_any_cited_fact_entails_it(self, session):
        judge = _StubJudge(answers={("f2 says", "c1"): "entailed"})

        result = await ce.measure_coverage(
            session, judge, claims=[_claim("c1", "f1", "f2")],
            fact_text={"f1": "f1 says", "f2": "f2 says"},
        )

        assert result.verdicts == [V.ENTAILED]
        assert result.entailed == [(_claim("c1", "f1", "f2"), "f2")]

    async def test_it_stops_asking_once_a_claim_is_grounded(self, session):
        judge = _StubJudge(answers={("f1 says", "c1"): "entailed"})

        await ce.measure_coverage(
            session, judge, claims=[_claim("c1", "f1", "f2")],
            fact_text={"f1": "f1 says", "f2": "f2 says"},
        )

        assert judge.asked == [("f1 says", "c1")]

    async def test_a_conjunction_grounded_claim_fails_toward_review(self, session):
        """No single fact entails it, so it is not grounded — the safe
        direction."""
        judge = _StubJudge()

        result = await ce.measure_coverage(
            session, judge, claims=[_claim("c1", "f1", "f2")],
            fact_text={"f1": "f1 says", "f2": "f2 says"},
        )

        assert result.verdicts == [V.NOT_ENTAILED]

    async def test_an_uncited_claim_costs_no_model_call(self, session):
        judge = _StubJudge()

        result = await ce.measure_coverage(
            session, judge, claims=[_claim("c1")], fact_text={},
        )

        assert judge.asked == []
        assert result.verdicts == [V.UNCITED]


class TestUnmeasured:
    async def test_a_refusing_judge_yields_no_coverage(self, session):
        """Not 0.0 — that would mean measured and nothing entailed."""
        judge = _StubJudge(raises=JudgeNotQualifiedError("not qualified"))

        result = await ce.measure_coverage(
            session, judge, claims=[_claim("c1", "f1")],
            fact_text={"f1": "f1 says"},
        )

        assert result.outcome is ce.CoverageOutcome.UNMEASURED
        assert result.coverage is None

    async def test_a_refusal_stops_the_remaining_claims(self, session):
        """The article's outcome is already fixed; spending C-k more refusals
        buys nothing."""
        judge = _StubJudge(raises=JudgeNotQualifiedError("not qualified"))

        await ce.measure_coverage(
            session, judge,
            claims=[_claim("c1", "f1"), _claim("c2", "f2"), _claim("c3", "f3")],
            fact_text={"f1": "a", "f2": "b", "f3": "c"},
        )

        assert len(judge.asked) == 1

    async def test_a_vendor_outage_is_unmeasured_not_unentailed(self, session):
        """Counting an outage as an unentailed claim would drive an article
        below threshold for a reason that has nothing to do with grounding."""
        judge = _StubJudge(raises=RuntimeError("connection refused"))

        result = await ce.measure_coverage(
            session, judge, claims=[_claim("c1", "f1")], fact_text={"f1": "a"},
        )

        assert result.outcome is ce.CoverageOutcome.UNMEASURED
        assert result.coverage is None

    async def test_an_invalid_verdict_is_unmeasured_not_unentailed(self, session):
        """`parse_verdict`'s third state. The qualification scorer counts an
        invalid response as a miss, but that is a convention for measuring the
        *judge* — it is not evidence about the claim."""
        judge = _StubJudge(invalid=True)

        result = await ce.measure_coverage(
            session, judge, claims=[_claim("c1", "f1")], fact_text={"f1": "a"},
        )

        assert result.outcome is ce.CoverageOutcome.UNMEASURED
        assert result.coverage is None

    async def test_an_article_with_no_claims_is_unmeasured(self, session):
        result = await ce.measure_coverage(
            session, _StubJudge(), claims=[], fact_text={},
        )

        assert result.outcome is ce.CoverageOutcome.UNMEASURED
        assert result.coverage is None

    async def test_the_pass_returns_rather_than_raising(self, session):
        """D14. Raising into the driver's per-subject `try` would make each
        subject increment both `written` and `failed` — and with G-D open that
        is every article, every tick, so a permanent standing state would read
        as a permanent vendor outage."""
        judge = _StubJudge(raises=JudgeNotQualifiedError("not qualified"))

        result = await ce.measure_coverage(
            session, judge, claims=[_claim("c1", "f1")], fact_text={"f1": "a"},
        )

        assert isinstance(result, ce.CoverageResult)


# ─────────────── Step 3: the threshold and the routing ───────────────


class TestRouting:
    async def test_at_or_above_the_bar_promotes(self, session):
        judge = _StubJudge(answers={("a", "c1"): "entailed"})

        result = await ce.measure_coverage(
            session, judge, claims=[_claim("c1", "f1")], fact_text={"f1": "a"},
            threshold=0.95,
        )

        assert result.outcome is ce.CoverageOutcome.PROMOTED
        assert result.coverage == 1.0

    async def test_below_the_bar_holds(self, session):
        judge = _StubJudge(answers={("a", "c1"): "entailed"})

        result = await ce.measure_coverage(
            session, judge,
            claims=[_claim("c1", "f1"), _claim("c2", "f2")],
            fact_text={"f1": "a", "f2": "b"}, threshold=0.95,
        )

        assert result.outcome is ce.CoverageOutcome.HELD
        assert result.coverage == 0.5

    async def test_exactly_at_the_bar_promotes(self, session):
        """"below threshold" is strict; a run exactly at the bar is not below
        it, and a `>` here would silently raise the bar."""
        judge = _StubJudge(answers={("a", "c1"): "entailed"})

        result = await ce.measure_coverage(
            session, judge, claims=[_claim("c1", "f1")], fact_text={"f1": "a"},
            threshold=1.0,
        )

        assert result.outcome is ce.CoverageOutcome.PROMOTED

    async def test_an_uncited_claim_blocks_promotion_at_a_clearing_coverage(
        self, session
    ):
        """The done-when is "uncited sentences are impossible in a shipped
        article", and a fractional bar does not deliver it: twenty-three of
        twenty-four clears 0.95 while one claim cites nothing."""
        answers = {(f"f{i}", f"c{i}"): "entailed" for i in range(23)}
        judge = _StubJudge(answers=answers)
        claims = [_claim(f"c{i}", f"f{i}") for i in range(23)] + [_claim("uncited")]

        result = await ce.measure_coverage(
            session, judge, claims=claims,
            fact_text={f"f{i}": f"f{i}" for i in range(23)}, threshold=0.95,
        )

        assert result.coverage == pytest.approx(23 / 24)
        assert result.coverage >= 0.95, "the fraction alone would have promoted"
        assert result.outcome is ce.CoverageOutcome.HELD
        assert result.has_uncited is True


class TestTheThresholdConfig:
    async def test_the_default_is_the_committed_constant(self, session):
        assert await ce.get_coverage_threshold(session) == ce.DEFAULT_COVERAGE_THRESHOLD

    async def test_the_config_row_overrides_it(self, session):
        await session.execute(
            text(
                "INSERT INTO config (key, value) "
                "VALUES (CAST(:k AS text), CAST(:v AS jsonb)) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ),
            {"k": ce.COVERAGE_CONFIG_KEY, "v": '{"threshold": 0.5}'},
        )
        await session.flush()

        assert await ce.get_coverage_threshold(session) == 0.5

    async def test_a_malformed_row_falls_back_rather_than_raising(self, session):
        """A bar that cannot be read must not become a bar of zero."""
        await session.execute(
            text(
                "INSERT INTO config (key, value) "
                "VALUES (CAST(:k AS text), CAST(:v AS jsonb)) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ),
            {"k": ce.COVERAGE_CONFIG_KEY, "v": '{"threshold": "loose"}'},
        )
        await session.flush()

        assert await ce.get_coverage_threshold(session) == ce.DEFAULT_COVERAGE_THRESHOLD


# ─────────────── invariant 15: the module layout is inverted ───────────────


async def test_this_module_does_not_import_article_synthesis():
    """`dream_jobs` imports `article_synthesis`, which makes it a forbidden
    module for every non-umbrella file. A hot-path module reaching this one
    would otherwise acquire an unpoliced transitive route to the dream family,
    because the scan checks direct reach per file — so the dependency runs
    downward, and `article_synthesis` adapts into this module's `Claim`."""
    import ast
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app/services/claim_entailment.py"
    ).read_text()
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert "app.services.article_synthesis" not in imported
    assert not any("dream_jobs" in m for m in imported)

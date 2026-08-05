"""T2.52 -- tests for the contradiction candidate-generator miss-rate runner.

Every test here runs against the real gold file and real pg_trgm, never a
stub: the whole point of this runner is a number measured off deterministic
SQL, so a mocked generator would test nothing the gate cares about. Tests
give each `run_missrate`/`probe_pair` call its own `project` string so they
never collide with each other's rows inside the shared, session-scoped
`_bench_db` fixture (which resets once per test session, not per test).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from benchlib import bench_db
from benchlib.contradiction_gold import load_contradiction_gold
from benchlib.contradiction_missrate import (
    BAR_SLICE,
    WRITER_TRIGGER_BAR,
    MissRateReport,
    SliceResult,
    _get_or_insert,
    run_missrate,
    same_endpoint_candidates,
)

pytestmark = pytest.mark.usefixtures("_bench_db")


async def _run(project: str, top_k: int = 10) -> MissRateReport:
    async with bench_db.session_factory() as session:
        report = await run_missrate(session, top_k=top_k, project=project)
        await session.commit()
    return report


class TestSliceResult:
    """Pure arithmetic -- no database. Pins the bar/granularity reading the
    brief's amendment requires: 2/12 must NOT breach the 20% bar, 3/12 must."""

    def test_granularity_is_one_over_slice_size(self):
        r = SliceResult(slice_tag="lexically-disjoint", total=12, misses=[])
        assert r.granularity == pytest.approx(1 / 12)

    def test_two_of_twelve_misses_does_not_breach_the_20pct_bar(self):
        r = SliceResult(slice_tag="lexically-disjoint", total=12, misses=["cg-a", "cg-b"])
        report = MissRateReport(
            gold_path="x", top_k=10, corpus_size=0,
            slices={"lexically-disjoint": r}, probes=[],
        )
        assert r.miss_rate == pytest.approx(2 / 12)
        assert not report.bar_breached(WRITER_TRIGGER_BAR, BAR_SLICE)

    def test_three_of_twelve_misses_breaches_the_20pct_bar(self):
        """The amendment's whole point: 3/12 = 25% > 20%, so the coarse
        gold's next representable value above 2 misses already breaches --
        there is no representable miss rate between 16.7% and 25%."""
        r = SliceResult(
            slice_tag="lexically-disjoint", total=12,
            misses=["cg-a", "cg-b", "cg-c"],
        )
        report = MissRateReport(
            gold_path="x", top_k=10, corpus_size=0,
            slices={"lexically-disjoint": r}, probes=[],
        )
        assert r.miss_rate == pytest.approx(3 / 12)
        assert report.bar_breached(WRITER_TRIGGER_BAR, BAR_SLICE)


class TestSameEndpointArmAlone:
    """same-endpoint pairs must be caught by the index-lookup arm alone --
    that arm carries no top-K, so corpus size must not matter to it."""

    @pytest.mark.asyncio
    async def test_finds_the_counterpart_of_a_real_same_endpoint_pair(self):
        gold = load_contradiction_gold()
        pair = next(
            p for p in gold["pairs"]
            if not p.get("retired") and p["slice_tags"] == ["same-endpoint"]
        )
        project = "test-same-endpoint-arm-alone"
        async with bench_db.session_factory() as session:
            cache: dict = {}
            ids = {
                side_key: await _get_or_insert(
                    session, project=project, side=pair[side_key],
                    reference_time=datetime.now(timezone.utc), cache=cache,
                )
                for side_key in ("a", "b")
            }
            candidates = await same_endpoint_candidates(
                session, project=project, fact_id=ids["a"],
                subject_name=pair["a"]["subject_name"],
                object_name=pair["a"]["object_name"],
            )
            await session.rollback()
        assert str(ids["b"]) in candidates


class TestCombinedGeneratorNotTrigramAlone:
    """Done-when box 1: the runner measures the COMBINED generator. Proven
    by breaking it on purpose -- probing with the trigram arm forced empty
    (top_k=0) must turn every lexically-disjoint hit into a miss, because
    token-disjoint endpoint names structurally can never satisfy the
    same-endpoint arm (the gold loader enforces this precondition). If this
    test ever passed with top_k=0, the same-endpoint arm would have to be
    matching on something looser than the shared-token equality doc 08
    SS5.3 describes -- itself a bug worth catching."""

    @pytest.mark.asyncio
    async def test_trigram_arm_disabled_misses_every_lexically_disjoint_pair(self):
        report = await _run(project="test-trigram-disabled", top_k=0)
        result = report.slice_result("lexically-disjoint")
        assert result.miss_count == result.total

    @pytest.mark.asyncio
    async def test_combined_generator_recovers_hits_the_trigram_arm_alone_supplies(self):
        """Restoring the trigram arm (its real default) must claw back at
        least one of those hits -- otherwise the arm contributes nothing
        and the 'combined, not trigram-alone' distinction in the Done-when
        box would be vacuous for this gold."""
        disabled = await _run(project="test-trigram-disabled-2", top_k=0)
        enabled = await _run(project="test-trigram-enabled-2", top_k=10)
        disabled_misses = disabled.slice_result("lexically-disjoint").miss_count
        enabled_misses = enabled.slice_result("lexically-disjoint").miss_count
        assert enabled_misses < disabled_misses


class TestRunMissrate:
    @pytest.mark.asyncio
    async def test_same_endpoint_slice_is_fully_caught(self):
        """Regression pin: the index-lookup arm has no top-K and every
        same-endpoint pair shares a full endpoint name by construction
        (the loader enforces it), so this slice's miss rate must stay 0%
        regardless of how the rest of the corpus is populated."""
        report = await _run(project="test-run-missrate-same-endpoint")
        result = report.slice_result("same-endpoint")
        assert result.total == 10
        assert result.miss_count == 0

    @pytest.mark.asyncio
    async def test_measures_all_100_pairs_worth_of_material_deduplicated(self):
        """98, not 100: two gold pairs legitimately reuse an anchor side
        (cg-0002.a == cg-0012.a, cg-0001.a == cg-0022.a) -- see the module
        docstring. A corpus_size of 100 here would mean dedup silently
        broke and two rows are now colliding on one open triple_key."""
        report = await _run(project="test-run-missrate-corpus-size")
        assert report.corpus_size == 98

    @pytest.mark.asyncio
    async def test_render_states_the_bar_before_the_number(self):
        report = await _run(project="test-run-missrate-render")
        text_out = report.render()
        bar_idx = text_out.index("Bar (stated beforehand)")
        number_idx = text_out.index("measured miss rate")
        assert bar_idx < number_idx

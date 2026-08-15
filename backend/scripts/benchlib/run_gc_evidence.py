"""T2.40 — the G-C bench-corpus evidence run, reproducible in one command.

The gate's four probes need a journal that facts have actually flowed
through. The production journal is the primary target
(``run_promotion_metrics.py``'s default); this driver is the bench-side
arm: it flows the committed retrieval corpus through the **shipping**
code paths — real ``ProcessingPipeline`` ingest against the warm disk
cache, ``fact_lift.run_lift`` to exhaustion, then
``verification_recompute.run_recompute`` ticks until the fast arm drains
— and only then measures, with the same SQL the production probe uses
plus the pre-stated ``JOURNAL_COMPLETENESS_SQL``. Nothing here writes an
``events`` row directly: every journal row in the measured window was
written by the production writers, or it does not exist. A metric
measured over hand-written events measures the fixture, which is the
one number this gate must never accept.

Verdicts are applied from ``promotion_bars`` — the bar module committed
**before** this file existed (gate-ledger.md rule 1; the git history is
the witness) — and since T2.128 the run prints the **bars in force** beside
them: per bar the committed value, the effective value, and whether a
``config`` row was absent, honoured or clamped back. Before that block
existed a clamp reached only ``logging`` and this report body was
byte-identical either way, so the artifact a gate ledger quotes could not
show that an operator's row had been refused. This driver never mints
``app/services/promotion_metrics_record.json``: the record that lights
the born-corroborated badge is written only by a run whose verdict
cleared, and only by the gate owner deliberately, never as a side effect
of measuring.

Run from backend/ with the key inline:
  DEEPSEEK_API_KEY=... BENCH_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench_<lane> \
      python scripts/benchlib/run_gc_evidence.py
Expected ``live_calls == 0`` against the warm retrieval cache.

``--corpus promotion`` (T2.108) swaps in the purpose-built measurement corpus
whose captures carry an ``origin_key``, leaving everything from the recompute
ticks down — the SQL, the pre-stated verdicts, the refusal to mint a record —
byte-identical. The default remains the retrieval corpus this file shipped
with, so T2.40's recorded run stays reproducible from the same command.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from sqlalchemy import text  # noqa: E402

from benchlib import bench_db  # noqa: E402  (DATABASE_URL override first)
from benchlib import db_target, promotion_bars, promotion_corpus, promotion_metrics as pm  # noqa: E402
from benchlib.harvest_l2_facts import assert_bench_db_allowed, run_harvest  # noqa: E402
from benchlib.run_smoke import require_deepseek_api_key  # noqa: E402

from app.services.verification_recompute import run_recompute  # noqa: E402

MAX_RECOMPUTE_TICKS = 20
WINDOW_DAYS = 90

RETRIEVAL_CORPUS = "retrieval"
PROMOTION_CORPUS = "promotion"


async def _prepare_retrieval(api_key: str, bench_url: str, db_name: str) -> int:
    harvest = await run_harvest(api_key=api_key, bench_url=bench_url, write=False)
    header = harvest.manifest["header"]
    print(f"bench_db: {db_name}")
    print(f"ingest live_calls: {harvest.live_calls}")
    print(f"embedder fingerprint: {header['embedder_fingerprint']}")
    print(f"lift: {header['lift']}")
    print(f"facts minted through the shipping lift: {harvest.n_facts}")
    return harvest.n_facts


async def _prepare_promotion(
    api_key: str, bench_url: str, db_name: str, *, simulate_capture_time: bool
) -> int:
    target = bench_db.BenchDatabase(bench_url)
    try:
        prepared = await promotion_corpus.prepare(
            api_key=api_key,
            session_factory=target.session_factory,
            reset=target.reset,
            simulate_capture_time=simulate_capture_time,
        )
    finally:
        await target.dispose()
    print(f"bench_db: {db_name}")
    print(f"corpus: promotion ({prepared.corpus_entries} captures, "
          f"sha256 {prepared.corpus_sha256[:16]})")
    print(f"ingest live_calls: {prepared.live_calls}")
    print(f"embedder fingerprint: {prepared.fingerprint}")
    print(f"lift: {prepared.lift}")
    print(f"wave 1 recompute (before wave 2 landed): {prepared.first_recompute}")
    print(f"wave 2: {prepared.wave_two_entries} captures, lift {prepared.wave_two_lift}")
    print(f"capture-time provenance stamped (SIMULATED CLOCK): "
          f"{prepared.capture_time_stamped} rows")
    print(f"repo assertions: {prepared.repo_assertions}")
    print(f"code lift: {prepared.code_lift}")
    print(f"facts minted through the shipping lift: {prepared.n_facts}")
    _print_twin(prepared)
    for note in prepared.notes:
        print(f"note: {note}")
    return prepared.n_facts


def _print_twin(prepared) -> None:
    """Rule 2's twin: no accuracy figure ships without latency and token cost.

    Three consecutive G-C runs shipped without one, which the gate ledger
    flagged for the first two and then stopped noticing — the reporting
    regression outlived the notice of it.

    A fully-replayed run prints zeros, and that is a reading rather than a
    gap: it says this run paid nothing and its numbers rest on cache entries
    some earlier run paid for. `cache_unknown` counts calls whose entry
    predates usage capture; it is never coerced to a paid zero.
    """
    print(f"== twin (rule 2) ==")
    print(f"  wall clock: {prepared.wall_seconds}s")
    print(f"  live model calls: {prepared.live_calls}")
    by_purpose = prepared.tokens_by_purpose or {}
    if not by_purpose:
        print("  tokens: no chat purpose recorded usage this run")
        return
    for purpose, usage in sorted(by_purpose.items()):
        # **Read the keys the ledger actually emits.** This read
        # `prompt_tokens` / `completion_tokens`, which `PurposeUsage` has never
        # had -- its fields are split live/cache_known -- so both columns
        # printed 0 unconditionally. The artifact was correct only while the
        # true values were zero, i.e. on a fully replayed run; the first cold
        # run would have printed `live=246 prompt=0 completion=0`, which is
        # exactly the paid zero this twin exists to refuse, and silently
        # (T2.129 review, Critical C-1).
        live_prompt = usage.get("live_prompt_tokens", 0)
        live_completion = usage.get("live_completion_tokens", 0)
        replayed_prompt = usage.get("cache_known_prompt_tokens", 0)
        replayed_completion = usage.get("cache_known_completion_tokens", 0)
        print(
            f"  {purpose}: live={usage.get('live_calls', 0)} "
            f"paid_prompt={live_prompt} paid_completion={live_completion} "
            f"replayed_prompt={replayed_prompt} "
            f"replayed_completion={replayed_completion} "
            f"cache_known={usage.get('cache_known_calls', 0)} "
            f"cache_unknown={usage.get('cache_unknown_calls', 0)} "
            # The disambiguator the twin was built around and the printer
            # dropped: a live call whose usage the vendor did not report is
            # not a free call.
            f"live_unknown={usage.get('live_unknown_calls', 0)}"
        )


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Flow a corpus through the shipping ladder and measure it."
    )
    parser.add_argument(
        "--corpus", choices=(RETRIEVAL_CORPUS, PROMOTION_CORPUS),
        default=RETRIEVAL_CORPUS,
        help=(
            "which corpus to flow: the committed retrieval corpus (T2.40's "
            "recorded run) or T2.108's promotion measurement corpus"
        ),
    )
    parser.add_argument(
        "--no-capture-time-simulation", action="store_true",
        help=(
            "promotion corpus only: leave every fact_sources row carrying its "
            "write time instead of the capture time of the memory that asserted "
            "it. This is what makes T2.108's one simulated step auditable rather "
            "than asserted -- run it to see exactly which buckets rest on it"
        ),
    )
    args = parser.parse_args(argv)

    api_key = require_deepseek_api_key()
    bench_url = bench_db.BENCH_DATABASE_URL
    db_name = db_target.resolved_database_name(bench_url)
    assert_bench_db_allowed(db_name)

    if args.corpus == RETRIEVAL_CORPUS:
        await _prepare_retrieval(api_key, bench_url, db_name)
    else:
        await _prepare_promotion(
            api_key, bench_url, db_name,
            simulate_capture_time=not args.no_capture_time_simulation,
        )

    target = bench_db.BenchDatabase(bench_url)
    try:
        # The fast arm refuses events younger than its 5s commit-skew margin
        # (_COMMIT_SKEW_MARGIN), so a tick fired straight after the lift sees
        # an empty drain and only the slow arm adjudicates. Waiting the margin
        # out lets the run exercise the production drain path too.
        await asyncio.sleep(6)
        ticks = 0
        total_recomputed = total_transitions = 0
        while ticks < MAX_RECOMPUTE_TICKS:
            async with target.session_factory() as session:
                outcome = await run_recompute(session)
                await session.commit()
            ticks += 1
            total_recomputed += outcome.drain.facts_recomputed
            total_transitions += outcome.drain.transitions
            print(
                f"recompute tick {ticks}: drained {outcome.drain.events_scanned} "
                f"events, recomputed {outcome.drain.facts_recomputed} facts, "
                f"{outcome.drain.transitions} transitions; slow arm "
                f"{'ran' if outcome.slow_arm_ran else 'skipped'} "
                f"(scanned {outcome.reconcile.facts_scanned}, healed "
                f"{outcome.reconcile.facts_healed})"
            )
            if outcome.drain.events_scanned == 0:
                break
        print(
            f"recompute: {ticks} ticks, {total_recomputed} facts recomputed, "
            f"{total_transitions} journaled transitions"
        )

        until = datetime.now(timezone.utc)
        since = until - timedelta(days=WINDOW_DAYS)
        async with target.session_factory() as session:
            report = await pm.compute_promotion_metrics(
                session, since=since, until=until,
                database_identity=f"localhost:5433/{db_name}",
            )
            bar_report = await promotion_bars.get_promotion_bar_report(session)
            bars = bar_report.bars
            completeness = (
                await session.execute(text(promotion_bars.JOURNAL_COMPLETENESS_SQL))
            ).one()

        if args.corpus == PROMOTION_CORPUS:
            async with target.session_factory() as session:
                back = await promotion_corpus.read_back(session)
            print()
            print(promotion_corpus.render_read_back(back))

        print()
        # The predicate's own answer, carried into the report rather than
        # recomputed there. `render_report` holds no bar comparison, so the
        # printed verdict and the scored verdict cannot be two resolutions.
        fp = report.false_promotion
        print(pm.render_report(
            report,
            audit_verdict=pm.AuditVerdict(
                clears=promotion_bars.audit_clears(
                    fp.false_promotions,
                    fp.total_corroborations,
                    bars,
                ),
                bar=bars["verification_false_promotion_bar"],
            ),
        ))

        print("== journal completeness (promotion_bars.JOURNAL_COMPLETENESS_SQL) ==")
        print(
            f"facts: {completeness.facts}; born-rung carve-out: "
            f"{completeness.born_rung_carveout}; violations: {completeness.violations}"
        )

        print()
        print(promotion_bars.render_bar_report(bar_report))

        print()
        print("== pre-stated verdicts (promotion_bars, committed before this run) ==")
        for axis_name, slices in (
            ("by gate_fired", report.by_gate_fired),
            ("by diversity", report.by_diversity),
        ):
            pairs = [(s.promoted, s.eligible) for s in slices]
            promotions = sum(s.promoted for s in slices)
            decidable = promotion_bars.axis_decidable(pairs, promotions, bars)
            print(
                f"{axis_name}: decidable={decidable} "
                f"(eligible per bucket: {[s.eligible for s in slices] or '[]'}, "
                f"promotions: {promotions})"
            )
            if decidable:
                for s in slices:
                    print(
                        f"  bucket {s.bucket}: powered="
                        f"{promotion_bars.slice_powered(s.eligible, bars)} "
                        f"clears={promotion_bars.slice_clears(s.promoted, s.eligible, bars)}"
                    )
        bound = fp.upper_bound(pm.FALSE_PROMOTION_CONFIDENCE)
        print(
            f"false-promotion audit: decidable="
            f"{promotion_bars.audit_decidable(fp.total_corroborations, bars)} "
            f"clears="
            f"{promotion_bars.audit_clears(fp.false_promotions, fp.total_corroborations, bars)} "
            f"(corroborations: {fp.total_corroborations}, "
            f"false promotions: {fp.false_promotions}, "
            # The scored quantity first, the point estimate after it: since
            # T2.132 the verdict is the bound, and printing the rate in the
            # slot a reader's eye goes to is how a superseded rule keeps
            # getting quoted.
            f"scored bound: {bound if bound is None else round(bound, 6)} "
            f"at {pm.FALSE_PROMOTION_CONFIDENCE:.0%} confidence, "
            f"point estimate: {fp.rate}, "
            f"R2 companion -- corroborated facts later expired: "
            f"{fp.expired_after_corroboration})"
        )
        print(
            f"journal completeness: clears="
            f"{promotion_bars.journal_completeness_clears(completeness.violations)} "
            f"over {completeness.facts} facts "
            f"({completeness.born_rung_carveout} carve-out rows) -- vacuous unless "
            f"transitions occurred"
        )
    finally:
        await target.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

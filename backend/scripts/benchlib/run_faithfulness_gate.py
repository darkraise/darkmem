"""Faithfulness-gate runner (TH1.17) — the plumbing behind TH1.10's verify.

Scores the ``verification`` judge against the claim/span entailment gold
(``benchlib/faithfulness_gate.py``'s ``score_span_judgments`` /
``score_answer_coverage``), reports per-slice accuracy, and emits the
latency/token cost twin. Bars come from
``app.services.faithfulness_bars.FAITHFULNESS_BAR_DEFAULTS`` — imported,
never restated; ``scripts/benchlib/tests/test_faithfulness_bar_``
``restatement_scan.py`` is the executable guard against a second copy.

**The real gold does not exist yet** (TH1.01 §5 — authoring it is a
different task's, never this runner's). A bare run therefore takes the
fail-closed path: it reports the absence in words, prints the bars that
would have been checked, states the cost twin as unmeasured, and exits 0 —
this runner's job is to run cleanly and report an honest state, not to
manufacture a pass or a fail out of data that does not exist. It exits
non-zero only on a genuine malfunction: an unreadable bar config row, or a
gold file present but structurally broken.

**Scoring a present gold is opt-in, behind ``--live`` and ``--api-key``.**
Loading a gold file is not the same act as spending a measurement attempt
against it — this runner must never fire a live judge call just because a
file happened to exist at the expected path. Without ``--live`` a present
gold is reported by pair count only, never scored.

No database is touched unless ``--database-url`` is given; without it every
bar reports ``no config row`` against its committed default, which is the
honest state of a database nobody configured this role's bars in yet
(TH1.09 has not wired the role). ``darkmem_test`` and ``darkmem_test_N`` are
refused, same as every other read-only bench reader in this tree — they
belong to pytest, which drops and recreates them under a concurrent run.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from benchlib import db_target, faithfulness_gate as fg  # noqa: E402

from app.services import faithfulness_bars as fb  # noqa: E402

FORBIDDEN_DATABASE_NAMES = {"darkmem_test"}


def _assert_not_forbidden(url: str) -> None:
    db = db_target.resolved_database_name(url)
    if db in FORBIDDEN_DATABASE_NAMES or db.startswith(db_target.LANE_TEST_PREFIX):
        raise RuntimeError(
            f"refusing to point the faithfulness-gate runner at {db!r} — "
            f"darkmem_test and darkmem_test_N belong to pytest alone; see "
            f"CLAUDE.md's three-databases rule"
        )


async def _fetch_bar_rows(database_url: str) -> dict[str, object]:
    _assert_not_forbidden(database_url)
    engine = create_async_engine(
        database_url,
        connect_args={"server_settings": {"default_transaction_read_only": "on"}},
    )
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            return await fb.get_raw_faithfulness_bar_rows(session)
    finally:
        await engine.dispose()


def _print_gold_absent(exc: fg.SpanGoldAbsent) -> None:
    print("== span-support coverage ==")
    print("status: FAIL_CLOSED (gold absent)")
    print(
        f"no block-span entailment gold present at {exc.path} — refusing to "
        f"score. Authoring it is a separate task (TH1.01 §5); this runner "
        f"must never treat its absence as an empty pass."
    )


def _print_missing_qualification() -> None:
    # Structurally true today: TH1.09 owns wiring "faithfulness" into
    # JUDGE_ROLES/BAR_METRICS, and it has not landed. Stated every run so a
    # reader never mistakes "gold absent" for the only closed door.
    print("== judge qualification ==")
    print("status: FAIL_CLOSED (missing qualification)")
    print(
        "the 'faithfulness' judge role is not yet wired into JUDGE_ROLES "
        "(TH1.09); no qualification record can exist for it, so even a "
        "present, scored gold could not license a serving decision today."
    )


async def _run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--gold", default=str(fg.SPAN_GOLD_PATH))
    parser.add_argument(
        "--live", action="store_true",
        help="actually probe the judge against a present gold (spends a "
             "measurement attempt); refused without --api-key",
    )
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-kind", default=None)
    args = parser.parse_args(argv)

    rows: dict[str, object] = {}
    if args.database_url:
        rows = await _fetch_bar_rows(args.database_url)

    try:
        print(fg.render_bar_visibility(rows))
        bars_ok = True
    except ValueError as exc:
        print("== bars in force ==")
        print("status: FAIL_CLOSED (unreadable bar row)")
        print(f"{exc}")
        bars_ok = False

    print()
    _print_missing_qualification()
    print()

    try:
        gold_doc = fg.load_span_gold(args.gold)
    except fg.SpanGoldAbsent as exc:
        _print_gold_absent(exc)
        print()
        print(fg.render_cost_twin(None))
        return 0 if bars_ok else 1

    pairs = gold_doc["pairs"]

    if not args.live:
        print("== span-support coverage ==")
        print(
            f"gold present at {args.gold}: {len(pairs)} pairs. Pass --live "
            f"with --api-key to score them through the judge; a bare run "
            f"never spends a measurement attempt without explicit intent."
        )
        print()
        print(fg.render_cost_twin(None))
        return 0 if bars_ok else 1

    if not args.api_key:
        print("status: FAIL_CLOSED (--live given with no --api-key)")
        return 1

    base_dir = Path(args.gold).resolve().parent
    config = fg.judge_purpose_config(
        args.api_key, model=args.model, base_url=args.base_url,
        api_kind=args.api_kind,
    ) if any((args.model, args.base_url, args.api_kind)) else fg.judge_purpose_config(args.api_key)

    score, twin, verdicts = await fg.score_via_live_judge(
        pairs, base_dir, config, cache_dir=fg.SPAN_CACHE_DIR,
    )
    bars = fb.resolve_faithfulness_bars(rows)
    coverage = fg.score_answer_coverage(pairs, verdicts, bars)

    print("== span-support coverage (per synthetic answer) ==")
    for c in coverage:
        print(f"{c.answer_id}: {c.entailed}/{c.total} grounded={c.grounded}")
    print()
    print(fg.render_per_slice(score))
    print()
    print(
        f"entailed_precision={score.entailed_precision} "
        f"entailed_recall={score.entailed_recall} "
        f"clears_role_bars={fb.faithfulness_role_clears(score.entailed_precision or 0.0, score.entailed_recall, bars)}"
    )
    print()
    print(fg.render_cost_twin(twin))
    return 0 if bars_ok else 1


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(argv))


if __name__ == "__main__":
    sys.exit(main())

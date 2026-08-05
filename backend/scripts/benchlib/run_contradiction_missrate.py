"""T2.52 -- contradiction candidate-generator miss-rate runner.

Measures the combined same-endpoint + `pg_trgm` candidate generator's recall
against the contradiction-pair gold (`contradiction/gold.json`, T2.57), and
states whether the measured miss rate on the `lexically-disjoint` slice
justifies T2.33 (the deferred `triple_embeddings` writer) against the bar
fixed in `contradiction_missrate.WRITER_TRIGGER_BAR` (20%, doc 08 SS5.3 /
doc 17 SS5.2) -- stated in this module before any run, never adjusted to fit
one.

Run from backend/:  python scripts/benchlib/run_contradiction_missrate.py

Deterministic and free: zero model calls, bench database only
(BENCH_DATABASE_URL overrides the default darkmem_bench).
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
# Standalone execution (`python scripts/benchlib/run_contradiction_missrate.py`)
# only puts this file's own directory on sys.path -- unlike pytest, which
# inserts SCRIPTS_DIR itself because backend/scripts/ has no __init__.py. Both
# `benchlib` (under SCRIPTS_DIR) and `app` (under BACKEND_DIR) need to
# resolve, so both go on sys.path explicitly before either is imported.
for _path in (str(SCRIPTS_DIR), str(BACKEND_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

REPORT_DIR = REPO_ROOT / "docs" / "eval"


def _git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(BACKEND_DIR), capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


async def main() -> int:
    from benchlib import bench_db, ledger
    from benchlib.contradiction_missrate import (
        BAR_SLICE, WRITER_TRIGGER_BAR, run_missrate,
    )

    print(f"bar (stated beforehand): writer justified at miss rate > "
          f"{WRITER_TRIGGER_BAR:.0%} on the `{BAR_SLICE}` slice "
          f"(doc 08 SS5.3 / doc 17 SS5.2)")

    await bench_db.reset_bench_db()
    from app.database import engine as app_engine
    await app_engine.dispose()

    async with bench_db.session_factory() as session:
        report = await run_missrate(session)
        await session.commit()

    report_text = report.render()
    print(report_text)

    run_date = datetime.now(timezone.utc).date()
    report_path = REPORT_DIR / f"{run_date.isoformat()}-t2.52-contradiction-missrate.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    print(f"report written to {report_path}")

    breached = report.bar_breached()
    ledger.record({
        "kind": "contradiction_missrate",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "gold_path": str(report.gold_path),
        "top_k": report.top_k,
        "bar": WRITER_TRIGGER_BAR,
        "bar_slice": BAR_SLICE,
        "slices": {
            tag: {
                "total": r.total, "misses": r.miss_count,
                "miss_rate": r.miss_rate, "granularity": r.granularity,
                "missed_pair_ids": r.misses,
            }
            for tag, r in report.slices.items()
        },
        "justifies_t2_33": breached,
    })
    print(f"ledger appended: {ledger.DEFAULT_PATH}")

    return 0


def _run() -> int:
    try:
        return asyncio.run(main())
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"run_contradiction_missrate.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_run())

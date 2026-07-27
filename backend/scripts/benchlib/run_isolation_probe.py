"""G-B isolation probe entry point (T1.35, doc 20 §4).

Counts unlabelled cross-project and superseded rows returned on every front
door in the content-surfaces registry, against deliberately hostile fixtures
in the bench database. The bar is exactly zero; a single leaked row exits
non-zero with the row named.

Run from backend/:  python scripts/benchlib/run_isolation_probe.py

Deterministic and free: zero model calls, bench database only
(BENCH_DATABASE_URL overrides the default darkmem_bench).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
# Standalone execution (`python scripts/benchlib/run_isolation_probe.py`) only
# puts this file's own directory on sys.path -- unlike pytest, which inserts
# SCRIPTS_DIR itself because backend/scripts/ has no __init__.py. Both
# `benchlib` (under SCRIPTS_DIR) and `app` (under BACKEND_DIR) need to
# resolve, so both go on sys.path explicitly before either is imported.
for path in (str(SCRIPTS_DIR), str(BACKEND_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)


def main() -> int:
    from benchlib.isolation_probe import run_probe

    report = asyncio.run(run_probe())
    print(report.render())
    return 0 if report.count() == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

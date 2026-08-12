"""Coverage-distribution runner (T3.24) — the plumbing behind T3.22's verify.

Reports the **distribution** of per-article claim-support coverage against a
named snapshot. States no verdict: T3.22 (Fable, adversarial) reads this and
writes G-E's, per runbook §2's split between measurement design and
measurement plumbing.

**Read-only, structurally.** The default target is the real `darkmem`
database — doc 20 §4 names this the one sanctioned exception to "nothing
automated touches `darkmem`", and it is *read-only and may never write*.
That is enforced at the connection level
(``default_transaction_read_only=on``) exactly as
``run_promotion_metrics`` enforces it, not by convention: an accidental
write in this module fails in Postgres rather than in review.

`darkmem` **is** migrated on this dev machine as of 2026-08-12 — the prod
container runs alembic at startup — so a bare run reads a real, empty
corpus rather than a missing table. (``run_promotion_metrics``' docstring
still says the opposite; it was written before the stack was deployed.) The
no-schema path below is kept for a machine where that is not yet true, and
is reported distinctly so "never deployed" is never read as "deployed and
producing nothing".

Never point ``--database-url`` at `darkmem_test` or any `darkmem_test_N`:
those belong to pytest, which drops and recreates them under a concurrent
reader (CLAUDE.md's three-databases rule).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
# Standalone execution only puts this file's own directory on sys.path.
# Deliberately no `app` import: this runner must not go through
# `app.database`/`app.config`, which derive their own engine and could pick
# up an ambient DATABASE_URL this script does not control.
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from sqlalchemy.exc import DBAPIError  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from benchlib import coverage_distribution as cd, db_target, ledger  # noqa: E402

DEFAULT_DATABASE_URL = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem"
FORBIDDEN_DATABASE_NAMES = {"darkmem_test"}
REPORT_DIR = REPO_ROOT / "docs" / "eval"


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _database_identity(url: str) -> str:
    return db_target.resolved_database_name(url) or "unknown"


def _assert_not_forbidden(url: str) -> None:
    db = db_target.resolved_database_name(url)
    if db in FORBIDDEN_DATABASE_NAMES or db.startswith(db_target.LANE_TEST_PREFIX):
        raise RuntimeError(
            f"refusing to point the coverage-distribution runner at {db!r} — "
            f"darkmem_test and darkmem_test_N belong to pytest alone and are "
            f"dropped/recreated by a concurrent test run; see CLAUDE.md's "
            f"three-databases rule"
        )


def report_path(snapshot: str, report_dir: Path = REPORT_DIR) -> Path:
    return Path(report_dir) / f"{snapshot}-coverage-distribution.md"


def default_snapshot(now: datetime) -> str:
    return now.date().isoformat()


async def run(
    *,
    database_url: str = DEFAULT_DATABASE_URL,
    snapshot: str | None = None,
    report_dir: str | Path = REPORT_DIR,
    ledger_path: str | Path = ledger.DEFAULT_PATH,
    now: datetime | None = None,
) -> cd.CoverageDistributionReport:
    _assert_not_forbidden(database_url)
    read_at = now or datetime.now(timezone.utc)
    snapshot = snapshot or default_snapshot(read_at)
    identity = _database_identity(database_url)

    engine = create_async_engine(
        database_url,
        connect_args={"server_settings": {"default_transaction_read_only": "on"}},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            try:
                report = await cd.compute_coverage_distribution(
                    session, snapshot=snapshot,
                    database_identity=identity, read_at=read_at,
                )
            except DBAPIError as exc:
                # asyncpg's UndefinedTableError arrives wrapped twice; the
                # real class is one level below `.orig`, whose own type name
                # is always "ProgrammingError" regardless of SQLSTATE.
                underlying = getattr(exc.orig, "__cause__", None)
                if underlying is not None and type(underlying).__name__ == "UndefinedTableError":
                    report = cd.no_schema_report(
                        snapshot=snapshot,
                        database_identity=identity,
                        read_at=read_at,
                    )
                else:
                    raise
    finally:
        await engine.dispose()

    report_text = cd.render_report(report)
    path = report_path(snapshot, Path(report_dir))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_text, encoding="utf-8")

    ledger.record(
        cd.to_ledger_row(report, extra={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_sha": _git_sha(),
        }),
        path=ledger_path,
    )

    print(report_text)
    print(f"report written to {path}")
    print(f"ledger appended: {ledger_path}")
    return report


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Per-article claim-support coverage as a distribution, read "
            "read-only from a named snapshot (doc 20 §4). Plumbing only — "
            "no verdict is rendered."
        ),
    )
    parser.add_argument("--database-url", default=None, metavar="URL", help=(
        "Read-only target (default: COVERAGE_DISTRIBUTION_DATABASE_URL env "
        "var, else the real darkmem database on the dev-compose Postgres)."
    ))
    parser.add_argument("--snapshot", default=None, metavar="NAME", help=(
        "Name this run's snapshot (default: today's date). The name and the "
        "population hash together are what make a reported share "
        "attributable to a population."
    ))
    parser.add_argument("--report-dir", default=None, metavar="PATH")
    parser.add_argument("--ledger-path", default=None, metavar="PATH")
    return parser


async def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    database_url = args.database_url or os.environ.get(
        "COVERAGE_DISTRIBUTION_DATABASE_URL", DEFAULT_DATABASE_URL
    )
    await run(
        database_url=database_url,
        snapshot=args.snapshot,
        report_dir=args.report_dir or REPORT_DIR,
        ledger_path=args.ledger_path or ledger.DEFAULT_PATH,
    )
    return 0


def _run() -> int:
    try:
        return asyncio.run(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_run())

"""Promotion-metrics runner (T2.51) — the SQL-over-`events` runner T2.40
reads: promotion rate sliced by source-kind diversity and by which N fired,
plus the false-promotion audit (doc 17 §5.1).

**Plumbing, not judgment.** This script produces numbers; it states no bar
and renders no pass/fail verdict — T2.40 (Fable, adversarial) designs the
bar and reads what this emits (runbook §2's standing rule: measurement
design and measurement plumbing are different tasks). The one judgment this
script does make is statistical power: a 0/0 (or any bucket below
``promotion_metrics.UNDER_POWERED_THRESHOLD``) is reported as under-powered,
never as a pass or a bare percentage.

**Read-only, structurally.** The default target is the real `darkmem`
database — this is the one sanctioned "read-only gate probe measuring
production behaviour" exception the runbook and CLAUDE.md carve out of the
three-databases rule, and it is enforced at the connection level
(``default_transaction_read_only=on``, mirroring
``scripts/cutover/db.py``'s pattern) rather than by convention: an
accidental write in this module would fail in Postgres, not in review.
`darkmem` carries no schema on this dev machine (never migrated here), so a
bare run reports that fact explicitly rather than crashing on
`relation "events" does not exist` — see
``promotion_metrics.no_schema_report``. Point ``--database-url`` (or
``PROMOTION_METRICS_DATABASE_URL``) at a migrated database (e.g.
`darkmem_bench` after a benchlib run has seeded it) to see a live query
exercised; never point it at `darkmem_test` or any `darkmem_test_N` — those
are pytest's alone and get `DROP SCHEMA` out from under a concurrent reader.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
# Standalone execution only puts this file's own directory on sys.path --
# unlike pytest, which inserts SCRIPTS_DIR itself because backend/scripts/
# has no __init__.py. Only `benchlib` (under SCRIPTS_DIR) is needed here —
# deliberately no `app` import (see the module docstring: this runner must
# not go through `app.database`/`app.config`, which derive their own engine
# and could pick up an ambient DATABASE_URL this script does not control).
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.exc import DBAPIError  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from benchlib import db_target, ledger, promotion_metrics as pm  # noqa: E402

DEFAULT_DATABASE_URL = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem"
FORBIDDEN_DATABASE_NAMES = {"darkmem_test"}
REPORT_DIR = REPO_ROOT / "docs" / "eval"
DEFAULT_WINDOW_DAYS = 90


def _git_sha() -> str:
    # A plain subprocess call, not `benchlib.run_smoke.git_sha()` -- that
    # module imports `benchlib.bench_db` at module level, which overrides
    # `os.environ["DATABASE_URL"]` to the bench database as an import-time
    # side effect (see this file's own docstring on why this runner does
    # not go through `app.database`/`app.config`). Duplicating four lines
    # here is cheaper than importing that side effect into a script whose
    # whole point is a database target it fully controls.
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(BACKEND_DIR), capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _database_identity(url: str) -> str:
    parsed = make_url(url)
    host = parsed.host or "unknown"
    port = parsed.port or "?"
    db = unquote(parsed.database) if parsed.database else "unknown"
    return f"{host}:{port}/{db}"


def _assert_not_forbidden(url: str) -> None:
    # The name resolution lives in `db_target` so all five harness doors read
    # one rule. This site used to call `make_url(url).database` itself, which
    # is the *path* component: a `?database=` query param overrides it for the
    # asyncpg dialect, so the check approved a URL that reached the database
    # it was refusing. The read-only GUC still blocks writes either way, but an
    # unguarded name lets the runner measure a database an in-flight
    # `DROP SCHEMA` is tearing down and emit a garbage number into a gate
    # report. `db_target` also percent-decodes, since asyncpg's own DSN parser
    # does, so this check is never looser than whichever path ends up
    # connecting.
    db = db_target.resolved_database_name(url)
    if db in FORBIDDEN_DATABASE_NAMES or db.startswith("darkmem_test_"):
        raise RuntimeError(
            f"refusing to point the promotion-metrics runner at {db!r} — "
            f"darkmem_test and darkmem_test_N belong to pytest alone and are "
            f"dropped/recreated by a concurrent test run; see CLAUDE.md's "
            f"three-databases rule"
        )


def report_path(run_date, report_dir: Path = REPORT_DIR) -> Path:
    return Path(report_dir) / f"{run_date.isoformat()}-promotion-metrics.md"


async def run(
    *,
    database_url: str = DEFAULT_DATABASE_URL,
    since: datetime | None = None,
    until: datetime | None = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
    report_dir: str | Path = REPORT_DIR,
    ledger_path: str | Path = ledger.DEFAULT_PATH,
    now: datetime | None = None,
) -> pm.PromotionMetricsReport:
    _assert_not_forbidden(database_url)
    until = until or (now or datetime.now(timezone.utc))
    since = since or (until - timedelta(days=window_days))
    identity = _database_identity(database_url)

    engine = create_async_engine(
        database_url,
        connect_args={"server_settings": {"default_transaction_read_only": "on"}},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            try:
                report = await pm.compute_promotion_metrics(
                    session, since=since, until=until, database_identity=identity,
                )
            except DBAPIError as exc:
                # asyncpg's UndefinedTableError arrives wrapped twice: SQLAlchemy's
                # own DBAPIError wraps the dialect's AsyncAdapt_asyncpg_dbapi error
                # (`.orig`), which itself wraps the real asyncpg exception as
                # `__cause__` -- `.orig`'s own type name is always "ProgrammingError"
                # regardless of the underlying SQLSTATE, so the real class has to be
                # read one level deeper.
                underlying = getattr(exc.orig, "__cause__", None)
                if underlying is not None and type(underlying).__name__ == "UndefinedTableError":
                    report = pm.no_schema_report(
                        since=since, until=until, database_identity=identity,
                    )
                else:
                    raise
    finally:
        await engine.dispose()

    report_text = pm.render_report(report)
    run_date = (now or datetime.now(timezone.utc)).date()
    path = report_path(run_date, Path(report_dir))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_text, encoding="utf-8")

    ledger.record(
        pm.to_ledger_row(report, extra={
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
            "Promotion rate (by gate_fired, by source-kind diversity) and the "
            "false-promotion audit, computed by SQL over `events` alone "
            "(doc 17 §5.1). Plumbing only — no bar is stated or judged."
        ),
    )
    parser.add_argument("--database-url", default=None, metavar="URL", help=(
        "Read-only target (default: PROMOTION_METRICS_DATABASE_URL env var, "
        "else the real darkmem database on the dev-compose Postgres)."
    ))
    parser.add_argument("--window-days", type=int, default=DEFAULT_WINDOW_DAYS, help=(
        f"Promotion-rate/audit-cohort window in days, ending now (default "
        f"{DEFAULT_WINDOW_DAYS}). The false-promotion audit's dispute check "
        f"itself is never bounded above regardless of this value."
    ))
    parser.add_argument("--report-dir", default=None, metavar="PATH")
    parser.add_argument("--ledger-path", default=None, metavar="PATH")
    return parser


async def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    database_url = args.database_url or os.environ.get(
        "PROMOTION_METRICS_DATABASE_URL", DEFAULT_DATABASE_URL
    )
    await run(
        database_url=database_url,
        window_days=args.window_days,
        report_dir=args.report_dir or REPORT_DIR,
        ledger_path=args.ledger_path or ledger.DEFAULT_PATH,
    )
    return 0


def _run() -> int:
    try:
        return asyncio.run(main())
    # UnrecognisedPayloadError (the T2.60 / unknown-vocabulary guard) is a
    # RuntimeError subclass and is deliberately caught here too: it must
    # exit non-zero with a readable message, never a bare traceback.
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"run_promotion_metrics.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_run())

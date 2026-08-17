"""Refuse to serve against a schema the running image was not built for.

**The hole this closes, measured on production 2026-08-17.** Before the freeze a
schema change *regenerates* `0001_baseline.py` in place rather than appending a
revision, so the revision id never moves. `alembic upgrade head` therefore
compares `0001` to `0001` on an already-stamped database, finds them equal, and
does nothing — and the deploy reports a clean migration while the code runs
against a schema it does not have. Production drifted five columns that way;
`article_synthesis` died on every scheduled run for days, visible only in its own
`config` row, because a job's failure goes to a row rather than to anyone's face.

The revision id cannot detect this. The baseline's *content* can, so this stamps
a hash of the baseline file into the database it migrated and compares on every
boot.

**It fails closed, deliberately.** Refusing to start is loud and its remedy is
cheap pre-freeze (drop and recreate, which is what the policy already says to
do); serving on is quiet and was measured to cost days of a dead job. There is no
override flag on purpose — an env var that lets an operator skip this would be
reached for at exactly the moment it is protecting them.

**After the schema freeze this check must be retired**, not merely satisfied:
once the baseline is frozen and changes arrive as ordinary additive revisions,
the revision id moves again and alembic's own comparison does this job. Retiring
it is part of the freeze, and `docs/planning/baseline-schema-inventory.md` owns
that protocol.
"""
from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

# `app/schema_guard.py` -> parents[1] is the backend root in the repo and /app in
# the image, and `backend/migrations/` ships to `/app/migrations/` in both. It
# lives under `app/` rather than `backend/scripts/` because the Dockerfile does
# not copy `scripts/` — a boot check that is absent from the runtime image is a
# boot check that never runs.
BASELINE = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0001_baseline.py"
CONFIG_KEY = "schema_baseline_sha"


def baseline_sha() -> str:
    return hashlib.sha256(BASELINE.read_bytes()).hexdigest()


async def evaluate(conn) -> int:
    """The decision, against an already-open connection.

    Split from ``check`` so it is testable. ``check`` opens its own engine, and
    a test writing a drifted row through the suite's transactional session is
    invisible to a second connection — the guard would read "no row", stamp, and
    admit, so the refusal path could not be tested at all through ``check``.
    """
    stored = (
        await conn.execute(
            text("SELECT value->>'sha' FROM config WHERE key = :k"),
            {"k": CONFIG_KEY},
        )
    ).scalar()
    current = baseline_sha()

    if stored is None:
        # Freshly migrated, or a database predating this check. It adopts the
        # schema that is actually there, which is the only honest thing it can
        # do: it cannot know retroactively whether that schema was current.
        await conn.execute(
            text(
                "INSERT INTO config (key, value) VALUES "
                "(:k, jsonb_build_object('sha', CAST(:v AS text))) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ),
            {"k": CONFIG_KEY, "v": current},
        )
        print(f"schema baseline stamped: {current[:16]}")
        return 0

    if stored == current:
        print(f"schema baseline current: {current[:16]}")
        return 0

    print(
        "\n*** REFUSING TO START — SCHEMA DRIFT ***\n"
        f"This database was migrated from baseline {stored[:16]}, but the image\n"
        f"carries baseline {current[:16]}. Before the freeze a schema change\n"
        "regenerates 0001_baseline.py in place, so the revision id never moves\n"
        "and `alembic upgrade head` is a NO-OP here — the migration you just saw\n"
        "succeed did nothing, and the code is about to query columns this\n"
        "database does not have.\n\n"
        "This is not recoverable by migrating. Pre-freeze the remedy is the\n"
        "policy's own: back up, drop and recreate the database, redeploy, then\n"
        "restore what must survive. docs/runbook-deployment.md carries the\n"
        "procedure, including the rows a re-seed does NOT reproduce (the\n"
        "verification LLM purpose row and the admin password hash).\n",
        file=sys.stderr,
    )
    return 1


async def check(database_url: str) -> int:
    engine = create_async_engine(database_url, echo=False)
    try:
        async with engine.begin() as conn:
            return await evaluate(conn)
    finally:
        await engine.dispose()


def main() -> int:
    return asyncio.run(check(settings.database_url))


if __name__ == "__main__":
    raise SystemExit(main())

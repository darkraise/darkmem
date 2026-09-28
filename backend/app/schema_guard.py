"""Refuse to serve against a schema the running image was not built for.

**The hole this closes, measured on production 2026-08-17.** Until 2026-09-28 a
schema change *regenerated* `0001_baseline.py` in place rather than appending a
revision, so the revision id never moved. `alembic upgrade head` therefore
compares `0001` to `0001` on a database built from an older copy of that file,
finds them equal, and does nothing — and the deploy reports a clean migration
while the code runs against a schema it does not have. Production drifted five
columns that way; `article_synthesis` died on every scheduled run for days,
visible only in its own `config` row.

**Since 2026-09-28 the baseline is permanent** (`FROZEN_BASELINE_SHA`, pinned by
`tests/test_schema_guard.py`) and every schema change is a new revision chained
after it, which alembic applies itself. The guard stays because the databases
built from the regenerated copies are all still stamped `0001`: to alembic they
look current, and only the file's content tells them apart. A mismatch here
therefore means a database built before the baseline became permanent, which no
revision can upgrade.

The revision id cannot detect this. The baseline's *content* can, so this stamps
a hash of the baseline file into the database it migrated and compares on every
boot.

**It fails closed, deliberately.** Refusing to start is loud; serving on is quiet
and was measured to cost days of a dead job. There is no override flag on
purpose — an env var that lets an operator skip this would be reached for at
exactly the moment it is protecting them.
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
FROZEN_BASELINE_SHA = "3c408f94c0e6b1128df3f8e173839a54d4ac0f0ca2fb2709b140c093e8d1457a"


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
        f"carries baseline {current[:16]}. The database was built from a copy of\n"
        "0001_baseline.py that was regenerated in place before the baseline\n"
        "became permanent (2026-09-28). Alembic sees both as revision 0001, so\n"
        "`alembic upgrade head` is a NO-OP here — the migration you just saw\n"
        "succeed did nothing, and the code is about to query columns this\n"
        "database does not have.\n\n"
        "No revision can upgrade it. Back up, bring the schema to the permanent\n"
        "baseline by hand, then let the guard re-stamp: docs/runbook-deployment.md\n"
        "(\"Recovering from schema drift\") carries the procedure, including the\n"
        "rows a re-seed does NOT reproduce (the verification LLM purpose row and\n"
        "the admin password hash).\n",
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

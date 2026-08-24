"""Phase 6 backfill — populate the new memory metadata columns.

Sets ``technologies`` from entity rows of type tool/service/database/language/
protocol, and recomputes ``confidence`` from the rule-based heuristic. Leaves
``project`` and ``status`` at their server defaults ('default'/'active') for
historical rows; ``superseded_by`` stays NULL because we do not retroactively
chain old REPLACES.

Dry-run by default; pass ``--commit`` to apply. Run from ``backend/``:

    python -m scripts.backfill_metadata_v2
    python -m scripts.backfill_metadata_v2 --commit
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text

from app.config import settings
from app.database import async_session_factory
from app.services.confidence import estimate_confidence
from app.services.relations import TECH_TYPES
from scripts.benchlib.db_target import assert_destructive_target_allowed


_TECH_TYPES_SQL = sorted(TECH_TYPES)


async def _preview_counts(session) -> dict[str, int]:
    totals = {}
    totals["memories"] = int((await session.execute(text("SELECT COUNT(*) FROM memories"))).scalar_one() or 0)
    totals["memories_missing_tech"] = int(
        (await session.execute(
            text("SELECT COUNT(*) FROM memories WHERE technologies = '{}'::text[]")
        )).scalar_one() or 0
    )
    totals["entities_tech_rows"] = int(
        (await session.execute(
            text(
                "SELECT COUNT(*) FROM entities WHERE entity_type = ANY(:types)"
            ),
            {"types": _TECH_TYPES_SQL},
        )).scalar_one() or 0
    )
    totals["memories_referenced_by_tech"] = int(
        (await session.execute(
            text(
                """
                SELECT COUNT(DISTINCT mem_id) FROM (
                    SELECT unnest(memory_ids) AS mem_id FROM entities
                    WHERE entity_type = ANY(:types)
                ) t
                """
            ),
            {"types": _TECH_TYPES_SQL},
        )).scalar_one() or 0
    )
    return totals


async def _backfill_technologies(session) -> int:
    """Single SQL to denormalise tech entity names into `memories.technologies`."""
    result = await session.execute(
        text(
            """
            WITH exploded AS (
                SELECT e.name AS name, unnest(e.memory_ids) AS memory_id
                FROM entities e
                WHERE e.entity_type = ANY(:types)
            ),
            tech AS (
                SELECT memory_id, array_agg(DISTINCT name ORDER BY name) AS tech_names
                FROM exploded
                GROUP BY memory_id
            )
            UPDATE memories m
            SET technologies = t.tech_names
            FROM tech t
            WHERE m.id = t.memory_id
              AND (m.technologies IS NULL OR m.technologies = '{}'::text[])
            """
        ),
        {"types": _TECH_TYPES_SQL},
    )
    return result.rowcount or 0


async def _backfill_confidence(session) -> tuple[int, int]:
    """Compute confidence in Python per memory, UPDATE in batches.

    Returns (touched_rows, non_default_rows).
    """
    rows = (
        await session.execute(text("SELECT id, content, memory_type, confidence FROM memories"))
    ).all()
    touched = 0
    non_default = 0
    batch: list[tuple[str, float]] = []
    for r in rows:
        mem_id = r[0]
        content = r[1]
        memory_type = r[2]
        current = float(r[3]) if r[3] is not None else 0.75
        new = estimate_confidence(content, memory_type)
        if abs(new - current) > 1e-6:
            batch.append((mem_id, new))
            touched += 1
        if abs(new - 0.75) > 1e-6:
            non_default += 1
        if len(batch) >= 500:
            await _apply_confidence_batch(session, batch)
            batch.clear()
    if batch:
        await _apply_confidence_batch(session, batch)
    return touched, non_default


async def _apply_confidence_batch(session, batch: list[tuple[str, float]]) -> None:
    await session.execute(
        text("UPDATE memories SET confidence = :c WHERE id = :id"),
        [{"id": mid, "c": c} for mid, c in batch],
    )


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--commit",
        action="store_true",
        help="Apply the backfill. Without this flag the script reports counts only.",
    )
    args = ap.parse_args()

    if args.commit:
        # --commit runs an unscoped UPDATE across every memory row in
        # whatever database DATABASE_URL resolves to, which on the host that
        # runs the live instance is production. The preview below is
        # read-only, so --help and a dry run stay usable everywhere.
        assert_destructive_target_allowed(
            settings.database_url, actor="backfill_metadata_v2"
        )

    async with async_session_factory() as session:
        counts = await _preview_counts(session)
        print("Preview:")
        for k, v in counts.items():
            print(f"  {k:35s} {v}")

        if not args.commit:
            print("\nDry run — pass --commit to apply.")
            return 0

        tech_rows = await _backfill_technologies(session)
        touched, non_default = await _backfill_confidence(session)
        await session.commit()
        print()
        print(f"technologies updated on {tech_rows} memory rows")
        print(f"confidence updated on {touched} memory rows ({non_default} of them are non-default 0.75)")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

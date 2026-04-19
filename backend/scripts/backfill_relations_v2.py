"""Phase 6.5 backfill — map historical entity_relations rows into the 5-type schema.

For each row in `entity_relations`:
  - If `rel_type` maps to a 5-type label via REL_MAP_5, UPDATE to the new label.
  - If it maps to None (RELATED_TO, HAPPENED_ON, AUTHORED_BY, and the 30-type droppables), DELETE the row.

Dry-run by default; pass ``--commit`` to apply. Always run dry-run first and
take a pg_dump before --commit because the DELETEs are permanent.

Run from ``backend/``:

    python -m scripts.backfill_relations_v2
    python -m scripts.backfill_relations_v2 --commit
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text

from app.database import async_session_factory
from app.services.relations import REL_MAP_5, RELATION_TYPES_V2


async def _preview(session) -> tuple[Counter, Counter, int, int]:
    rows = (
        await session.execute(text("SELECT rel_type, COUNT(*) FROM entity_relations GROUP BY rel_type"))
    ).all()

    update_counts: Counter[tuple[str, str]] = Counter()
    delete_counts: Counter[str] = Counter()
    unknown_counts: Counter[str] = Counter()

    total_rows = 0
    for rel_type, count in rows:
        total_rows += count
        if rel_type in RELATION_TYPES_V2:
            # Already 5-type; no-op.
            continue
        if rel_type in REL_MAP_5:
            mapped = REL_MAP_5[rel_type]
            if mapped is None:
                delete_counts[rel_type] = count
            else:
                update_counts[(rel_type, mapped)] = count
        else:
            unknown_counts[rel_type] = count

    update_rows = sum(update_counts.values())
    delete_rows = sum(delete_counts.values())

    print(f"Total relation rows: {total_rows}")
    print(f"  already 5-type:   {total_rows - update_rows - delete_rows - sum(unknown_counts.values())}")
    print(f"  to update:        {update_rows}")
    print(f"  to delete:        {delete_rows}")
    print(f"  unknown types:    {sum(unknown_counts.values())} (left untouched)")

    if update_counts:
        print("\n  Renames (top 15 by row count):")
        for (old, new), n in update_counts.most_common(15):
            print(f"    {old:20s} -> {new:12s} {n:6d}")
    if delete_counts:
        print("\n  Deletes (top 10 by row count):")
        for old, n in delete_counts.most_common(10):
            print(f"    {old:20s}  {n:6d}")
    if unknown_counts:
        print("\n  Unknown types (no REL_MAP_5 entry):")
        for old, n in unknown_counts.most_common():
            print(f"    {old:20s}  {n:6d}")

    return update_counts, delete_counts, update_rows, delete_rows


async def _apply(session, update_counts: Counter, delete_counts: Counter) -> None:
    # Deletes first so collapsing pairs don't violate the (source, target, rel_type)
    # uniqueness constraint when we rename into a slot that still has a dropped
    # duplicate.
    for old in delete_counts:
        result = await session.execute(
            text("DELETE FROM entity_relations WHERE rel_type = :old"),
            {"old": old},
        )
        print(f"  deleted rel_type={old!r:20s} rows={result.rowcount}")

    for (old, new) in update_counts:
        # Merge on collision to respect (source_entity_id, target_entity_id, rel_type) unique.
        merge = await session.execute(
            text(
                """
                WITH pairs AS (
                    SELECT r_old.id AS old_id,
                           r_new.id AS new_id,
                           r_old.memory_ids AS old_mids,
                           r_old.weight AS old_weight
                    FROM entity_relations r_old
                    JOIN entity_relations r_new
                      ON r_new.source_entity_id = r_old.source_entity_id
                     AND r_new.target_entity_id = r_old.target_entity_id
                     AND r_new.rel_type = :new
                    WHERE r_old.rel_type = :old
                ),
                merged AS (
                    UPDATE entity_relations r_new
                    SET memory_ids = (
                            SELECT ARRAY(
                                SELECT DISTINCT unnest(
                                    COALESCE(r_new.memory_ids, '{}'::uuid[]) ||
                                    COALESCE(p.old_mids, '{}'::uuid[])
                                )
                            )
                        ),
                        weight = GREATEST(COALESCE(r_new.weight, 0), COALESCE(p.old_weight, 0))
                    FROM pairs p
                    WHERE r_new.id = p.new_id
                    RETURNING p.old_id
                )
                DELETE FROM entity_relations
                WHERE id IN (SELECT old_id FROM merged)
                """
            ),
            {"old": old, "new": new},
        )
        rename = await session.execute(
            text("UPDATE entity_relations SET rel_type = :new WHERE rel_type = :old"),
            {"old": old, "new": new},
        )
        print(f"  renamed {old!r:20s} -> {new!r:12s} merged={merge.rowcount} renamed={rename.rowcount}")


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--commit",
        action="store_true",
        help="Apply the backfill. Without this flag the script reports counts only.",
    )
    args = ap.parse_args()

    async with async_session_factory() as session:
        update_counts, delete_counts, _, _ = await _preview(session)

        if not args.commit:
            print("\nDry run — pass --commit to apply.")
            return 0

        print("\nApplying…")
        await _apply(session, update_counts, delete_counts)
        await session.commit()

        print("\nFinal distinct rel_types:")
        rows = (
            await session.execute(
                text("SELECT rel_type, COUNT(*) FROM entity_relations GROUP BY rel_type ORDER BY 2 DESC")
            )
        ).all()
        for rel_type, count in rows:
            print(f"  {rel_type:20s} {count:6d}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

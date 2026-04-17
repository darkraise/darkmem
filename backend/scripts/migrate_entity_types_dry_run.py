"""Preview the 0004 taxonomy migration without mutating any rows.

Reports, per legacy type, how many entities and relations would be renamed.
Run from the backend/ directory: ``python -m scripts.migrate_entity_types_dry_run``.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text

from app.database import async_session_factory
from app.taxonomy import LEGACY_ENTITY_TYPE_MAP, LEGACY_RELATION_TYPE_MAP


async def main() -> int:
    total_entities = 0
    total_relations = 0

    async with async_session_factory() as session:
        print("=== Entities ===")
        for old, new in sorted(LEGACY_ENTITY_TYPE_MAP.items()):
            if old == new:
                continue
            result = await session.execute(
                text("SELECT COUNT(*) FROM entities WHERE entity_type = :old"),
                {"old": old},
            )
            n = int(result.scalar_one() or 0)
            if n:
                print(f"  {old!r:<18s} -> {new!r:<10s}  {n:6d} rows")
            total_entities += n

        print("\n=== Relations ===")
        for old, new in sorted(LEGACY_RELATION_TYPE_MAP.items()):
            if old == new:
                continue
            result = await session.execute(
                text("SELECT COUNT(*) FROM entity_relations WHERE rel_type = :old"),
                {"old": old},
            )
            n = int(result.scalar_one() or 0)
            if n:
                print(f"  {old!r:<20s} -> {new!r:<12s}  {n:6d} rows")
            total_relations += n

    print("\n=== Totals ===")
    print(f"  entities:  {total_entities}")
    print(f"  relations: {total_relations}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

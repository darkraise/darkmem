#!/usr/bin/env python3
"""List, and on request restore, the `project/` tags a past refine removed.

Until refine became a summary-only rewrite, the dreaming pass replaced a
memory's whole tag list with the model's "cleaned" one, and a `project/`
filter tag could go with it. Every such refine journalled the tags it found in
its `consolidated` event's `before.tags`, so the loss reads off the journal: a
`project/` tag in `before.tags` that the memory no longer carries.

A tag a person removed on purpose after the refine reads the same way, which is
why the default is a dry run: it prints, per memory, the tags `--apply` would
add back, and writes nothing. `--apply` only adds those tags; it never removes
or rewrites another.

Without `--database-url` the target is the app's own database (`DATABASE_URL`,
or the URL derived from the `DB_*` variables), which is production inside the
app container, so `--apply` there also needs `--i-am-the-owner`.

Usage (from backend/):

    .venv/bin/python scripts/restore_refine_project_tags.py
    .venv/bin/python scripts/restore_refine_project_tags.py --apply --i-am-the-owner
    .venv/bin/python scripts/restore_refine_project_tags.py --database-url URL --apply
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.memory import memory_tags  # noqa: E402
from app.repositories.relational import PostgresTagRepository  # noqa: E402
from app.schemas.memory import validate_tag_lengths  # noqa: E402
from app.services.dream_journal import (  # noqa: E402
    ACTION_REFINE,
    DETECTOR,
    EVENT_TYPE,
    OBJECT_TYPE,
)

PROJECT_TAG_PREFIX = "project/"

# Bounded by `created_at` at the run's start, so the events a run acts on are
# fixed when it begins.
_LOST_TAGS = text("""
    SELECT DISTINCT CAST(e.object_id AS text) AS memory_id, lost.tag
    FROM events e
    CROSS JOIN LATERAL jsonb_array_elements_text(
        CASE WHEN jsonb_typeof(e.payload -> 'before' -> 'tags') = 'array'
             THEN e.payload -> 'before' -> 'tags' END
    ) AS lost(tag)
    JOIN memories m ON m.id = e.object_id
    WHERE e.event_type = CAST(:event_type AS text)
      AND e.object_type = CAST(:object_type AS text)
      AND e.payload ->> 'action' = CAST(:action AS text)
      AND e.payload ->> 'detector' = CAST(:detector AS text)
      AND e.created_at <= CAST(:until AS timestamptz)
      AND left(lost.tag, length(CAST(:prefix AS text))) = CAST(:prefix AS text)
      AND NOT EXISTS (
          SELECT 1 FROM memory_tags mt
          JOIN tags t ON t.id = mt.tag_id
          WHERE mt.memory_id = m.id AND t.name = lost.tag
      )
    ORDER BY memory_id, lost.tag
""")


async def lost_project_tags(
    session: AsyncSession, *, until: datetime
) -> dict[str, list[str]]:
    rows = await session.execute(
        _LOST_TAGS,
        {
            "event_type": EVENT_TYPE,
            "object_type": OBJECT_TYPE,
            "action": ACTION_REFINE,
            "detector": DETECTOR,
            "until": until,
            "prefix": PROJECT_TAG_PREFIX,
        },
    )
    lost: dict[str, list[str]] = {}
    for memory_id, tag in rows.all():
        lost.setdefault(memory_id, []).append(tag)
    return lost


async def restore(session: AsyncSession, lost: dict[str, list[str]]) -> None:
    tags = PostgresTagRepository(session)
    for memory_id, names in lost.items():
        validate_tag_lengths(names)
        for name in names:
            tag = await tags.get_or_create(name)
            await session.execute(
                insert(memory_tags)
                .values(memory_id=UUID(memory_id), tag_id=tag.id)
                .on_conflict_do_nothing()
            )


async def run(database_url: str, *, apply: bool) -> int:
    engine = create_async_engine(database_url)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            lost = await lost_project_tags(session, until=datetime.now(timezone.utc))
            if apply:
                await restore(session, lost)
                await session.commit()
    finally:
        await engine.dispose()
    for memory_id, names in lost.items():
        print(f"{memory_id}\t{','.join(names)}")
    print(f"memories: {len(lost)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True,
                      help="list what --apply would restore (the default)")
    mode.add_argument("--apply", action="store_true",
                      help="add the lost project/ tags back")
    parser.add_argument("--database-url",
                        help="target database; without it, the app's DATABASE_URL")
    parser.add_argument("--i-am-the-owner", action="store_true",
                        help="required for --apply against the app's own database")
    args = parser.parse_args(argv)

    if args.database_url is None and args.apply and not args.i_am_the_owner:
        print(
            "refusing --apply against DATABASE_URL without --i-am-the-owner",
            file=sys.stderr,
        )
        return 2
    database_url = args.database_url
    if database_url is None:
        from app.config import settings

        database_url = settings.database_url
    return asyncio.run(run(database_url, apply=args.apply))


if __name__ == "__main__":
    sys.exit(main())

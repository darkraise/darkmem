"""The `projects` namespace registry: lazy registration + backfill (doc 04 §7, 09 §5).

`knowledge_triples.triple_key` embeds `project` verbatim in fact identity
(T2.01), so a typo'd project string would silently open a second, parallel
identity space with no corroboration against the original. `register` closes
that: every project string that reaches `_capture_batch` gets a visible row,
so an operator can see `darkmen` sitting next to `darkmem` and merge it by
hand. This module does **not** fuzzy-match, warn on near-misses, or correct
anything — visibility is the whole deliverable (T2.07's Done-when clause 2).

`name` is never canonicalised here. `Foo` and `foo` are distinct supersession
and fact-identity scopes (E2 amendment log, 2026-07-29), so lowercasing or
trimming on the way in would collapse two scopes onto one registry row.

`register` is a single `INSERT … ON CONFLICT (name) DO NOTHING` — no
SELECT-then-INSERT round trip, which would race under concurrent capture —
run inside its own `SAVEPOINT`. A registry failure rolls back only that
savepoint, matching `repo_provision`'s handoff idiom: a secondary concern
degrades loudly (logged) but never fails the capture it rode in on.
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_REGISTER = text(
    "INSERT INTO projects (name) VALUES (:name) ON CONFLICT (name) DO NOTHING"
)

_BACKFILL = text(
    "INSERT INTO projects (name) "
    "SELECT DISTINCT project FROM memories "
    "ON CONFLICT (name) DO NOTHING"
)


async def register(session: AsyncSession, project: str) -> None:
    """Lazily register `project` if it is not already a known namespace.

    Never raises: capture must not fail because the registry write did.
    """
    try:
        async with session.begin_nested():
            await session.execute(_REGISTER, {"name": project})
    except Exception:
        logger.error(
            "project registry write failed for %r; capture continues",
            project, exc_info=True,
        )


async def backfill(session: AsyncSession) -> int:
    """Insert every `DISTINCT memories.project` not already registered.

    Idempotent by construction (`ON CONFLICT DO NOTHING`): a second call with
    no new project strings inserts zero rows and touches no existing one's
    `created_at`. Not a migration — callable at boot or on demand.
    """
    result = await session.execute(_BACKFILL)
    return result.rowcount or 0

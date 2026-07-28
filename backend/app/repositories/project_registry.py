"""Read side of the ``projects`` table — tier 3 of the declared-context chain.

The table has existed since the baseline (doc 04) and has **no writer, no
ORM model and no other reader**. That is a real gap, logged as a Tier-2
amendment: until something owns writing ``properties.applies_when_default``,
tier 3 of doc 12 §5's precedence chain is structurally present and always
empty. This module lands the read half only, so the chain terminates
honestly rather than skipping a tier it claims to have.

Read-only by design. Adding a writer here without deciding who owns project
creation would put three surfaces back to improvising a project registry.
"""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_applies_when_default(
    session: AsyncSession, project: str | None,
) -> Mapping[str, Any] | None:
    """The project's default declared context, or ``None``.

    ``None`` for an absent row, an absent key, and a key that is not a
    non-empty object. A project row that exists but declares nothing must
    not become a declaration — an undeclared context that renders as a
    default is exactly what T1.65 guards against.
    """
    if not project:
        return None
    row = (
        await session.execute(
            text(
                "SELECT properties -> 'applies_when_default' "
                "FROM projects WHERE name = CAST(:name AS text)"
            ),
            {"name": project},
        )
    ).scalar_one_or_none()
    if isinstance(row, dict) and row:
        return row
    return None

"""The first writer for the ``memory_relations`` associative layer (doc 06 §3.1).

The vocabulary landed taxonomy-first and inert; the consolidation passes
(T2.12's near-duplicate arm, then T2.16's proximity/overlap/contradiction arms)
are its first writers. This repository is deliberately free of any pass's own
logic so those tasks can share it unchanged.

**Why the upsert merges instead of assigning ``properties``.** A same-type edge
between the same ordered pair is *one row* — ``UNIQUE (source_memory_id,
target_memory_id, rel_type)`` — so two derivation passes that both propose
``RELATES_TO`` for the same pair land on each other. A whole-object
``SET properties = …`` from either side therefore destroys the other's state,
and the same statement would roll a human's triage back to its derived default
every cycle. Each pass owns one key under ``properties.dream`` and writes only
that key.

**The nested ``jsonb_set`` is load-bearing, not defensive padding.**
``create_if_missing`` creates only the *final* element of a path; every earlier
element must already exist or ``jsonb_set`` returns its target **unchanged and
without raising**. Measured on this deployment's PostgreSQL 17.10, a single
``jsonb_set(properties, '{dream,near_duplicate}', …)`` silently drops the write
for a row whose ``properties`` is ``NULL``, ``{}``, or any object with no
``dream`` key — three of the four shapes that can reach a conflict. The inner
call materialises ``dream`` first, so the outer one has a container to write
into.

``created`` comes from ``(xmax = 0)``, which distinguishes an insert from an
update inside one ``INSERT … ON CONFLICT``. An undo needs it to tell "delete the
row I made" from "restore the block I overwrote"; without it an undo would
delete a row another pass owns.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy import (
    is_projected_memory_relation_type,
    normalize_memory_relation_type,
)
from app.utils.ids import new_id

# The one key under `properties` every derivation pass shares; each pass owns a
# single key beneath it.
DREAM_PROPERTIES_KEY = "dream"


class ProjectedRelationTypeError(ValueError):
    """A caller asked to store a type that is derived at read time."""


@dataclass(frozen=True)
class EdgeWrite:
    created: bool
    before: dict | None


_READ_EDGE = text("""
    SELECT CAST(id AS text) AS id,
           CAST(source_memory_id AS text) AS source_memory_id,
           CAST(target_memory_id AS text) AS target_memory_id,
           rel_type,
           project,
           properties
    FROM memory_relations
    WHERE source_memory_id = CAST(:source AS uuid)
      AND target_memory_id = CAST(:target AS uuid)
      AND rel_type = CAST(:rel_type AS text)
""")

# `jsonb_set` twice: the inner call guarantees `dream` exists so the outer call
# has a container for its final path element. Collapsing these into one path
# write is silent data loss on any row without a `dream` key.
_UPSERT_PASS_BLOCK = text("""
    INSERT INTO memory_relations
        (id, source_memory_id, target_memory_id, rel_type, project, properties)
    VALUES (
        CAST(:id AS uuid),
        CAST(:source AS uuid),
        CAST(:target AS uuid),
        CAST(:rel_type AS text),
        CAST(:project AS text),
        CAST(:props AS jsonb)
    )
    ON CONFLICT (source_memory_id, target_memory_id, rel_type) DO UPDATE
        SET properties = jsonb_set(
                jsonb_set(
                    COALESCE(memory_relations.properties, CAST('{}' AS jsonb)),
                    '{dream}',
                    COALESCE(
                        memory_relations.properties -> 'dream',
                        CAST('{}' AS jsonb)
                    ),
                    true
                ),
                CAST(:block_path AS text[]),
                CAST(:block AS jsonb),
                true
            )
    RETURNING (xmax = 0) AS created
""")


def _resolve_rel_type(rel_type: str | None) -> str:
    if is_projected_memory_relation_type(rel_type):
        raise ProjectedRelationTypeError(
            f"{rel_type!r} is projected from memories.superseded_by at read "
            "time and must never be stored as a memory_relations row"
        )
    return normalize_memory_relation_type(rel_type)


async def get_edge(
    session: AsyncSession,
    *,
    source_memory_id: UUID | str,
    target_memory_id: UUID | str,
    rel_type: str,
) -> dict | None:
    """The existing edge for an ordered pair and type, or ``None``.

    Normalises ``rel_type`` the same way the writer does, so a caller reading
    before it writes cannot look one type up and store another.
    """
    result = await session.execute(
        _READ_EDGE,
        {
            "source": str(source_memory_id),
            "target": str(target_memory_id),
            "rel_type": _resolve_rel_type(rel_type),
        },
    )
    row = result.mappings().first()
    return dict(row) if row is not None else None


async def upsert_edge(
    session: AsyncSession,
    *,
    source_memory_id: UUID | str,
    target_memory_id: UUID | str,
    rel_type: str,
    project: str,
    pass_key: str,
    block: dict,
) -> EdgeWrite:
    """Write one pass's block onto the pair's edge, creating the row if needed.

    Only ``properties.dream.<pass_key>`` is touched. Every sibling pass's block,
    every other top-level key, and anything a future actor adds survive
    untouched — which is what lets two passes share the one row the UNIQUE
    forces them onto.
    """
    resolved = _resolve_rel_type(rel_type)
    before = await get_edge(
        session,
        source_memory_id=source_memory_id,
        target_memory_id=target_memory_id,
        rel_type=resolved,
    )
    result = await session.execute(
        _UPSERT_PASS_BLOCK,
        {
            "id": str(new_id()),
            "source": str(source_memory_id),
            "target": str(target_memory_id),
            "rel_type": resolved,
            "project": project,
            "props": json.dumps({DREAM_PROPERTIES_KEY: {pass_key: block}}),
            "block_path": [DREAM_PROPERTIES_KEY, pass_key],
            "block": json.dumps(block),
        },
    )
    row = result.mappings().first()
    return EdgeWrite(created=bool(row["created"]), before=before)


def pass_block_of(edge: dict | None, pass_key: str) -> dict | None:
    """One pass's block out of an edge row read by :func:`get_edge`."""
    if not edge:
        return None
    properties = edge.get("properties") or {}
    if not isinstance(properties, dict):
        return None
    dream = properties.get(DREAM_PROPERTIES_KEY) or {}
    if not isinstance(dream, dict):
        return None
    block = dream.get(pass_key)
    return block if isinstance(block, dict) else None

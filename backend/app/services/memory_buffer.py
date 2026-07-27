"""The Tier-B ingest buffer: accept durably, hand back a real id, flush later.

Doc 05 §2 splits capture in two. Tier A validates, resolves `source` /
`origin_key` / `project`, commits one buffer row and acks; Tier B claims that
row later and runs the five-phase pipeline. This module owns the buffer side of
that split — the row, its id, and the replay contract. The 202 route is T1.12's
and the `FOR UPDATE SKIP LOCKED` claim loop is T1.13's.

Two properties this module exists to guarantee:

**The id is minted at accept, not at flush.** A 202 that returned no handle, or
a placeholder one, would make the caller poll for something it cannot name. So
capture mints a UUIDv7 up front and the very same value becomes the `memories`
row's id — never re-minted, never remapped.

**Nothing captured is dropped.** The buffer's columns are a subset of what a
caller may send, so every remaining `MemoryCreate` field rides `metadata_` and
is replayed verbatim (doc 04 §8.6). A field that reaches Tier A and not the
pipeline is data loss that looks like a successful capture.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemoryBuffer
from app.utils.ids import new_id

# Everything a caller may supply that the buffer has no column for. Kept as an
# explicit tuple rather than "whatever is left over" so that adding a capture
# field without deciding how it replays is a visible omission.
REPLAYED_METADATA_FIELDS: tuple[str, ...] = (
    "memory_type",
    "tags",
    "importance",
    "expires_at",
    "source_agent",
    "origin_key",
)


def build_buffer_metadata(**fields: Any) -> dict[str, Any]:
    """Collect the caller-supplied fields that ride `metadata_`.

    Unknown keys are kept, not dropped: a field this module has not been taught
    about is still the caller's data, and losing it silently is the failure mode
    doc 04 §8.6 forbids. `None` values are dropped, since "absent" and
    "explicitly null" mean the same thing to the pipeline replay.
    """
    return {k: v for k, v in fields.items() if v is not None}


async def enqueue(
    session: AsyncSession,
    *,
    content: str,
    project: str,
    source: str | None = None,
    origin_key: str | None = None,
    token_size: int | None = None,
    memory_id: uuid.UUID | None = None,
    **extra: Any,
) -> MemoryBuffer:
    """Write one buffered capture and return it, id already minted.

    The caller may pass `memory_id` when it minted the handle itself (the 202
    path does, so it can ack before this commits); otherwise one is minted here.
    The row is added but **not committed** — the caller owns the transaction
    boundary, because invariant 11 requires capture to commit before any flush
    worker opens a session over the row.
    """
    row = MemoryBuffer(
        id=memory_id or new_id(),
        content=content,
        project=project,
        source=source,
        token_size=token_size,
        status="pending",
        metadata_=build_buffer_metadata(origin_key=origin_key, **extra) or None,
    )
    session.add(row)
    await session.flush()
    return row


async def get(session: AsyncSession, buffer_id: uuid.UUID) -> MemoryBuffer | None:
    return (
        await session.execute(select(MemoryBuffer).where(MemoryBuffer.id == buffer_id))
    ).scalar_one_or_none()


async def pending(session: AsyncSession, limit: int = 100) -> list[MemoryBuffer]:
    """Oldest-first pending rows. Reads the partial `WHERE status='pending'`
    index the claim loop is built around."""
    rows = await session.execute(
        select(MemoryBuffer)
        .where(MemoryBuffer.status == "pending")
        .order_by(MemoryBuffer.created_at)
        .limit(limit)
    )
    return list(rows.scalars())

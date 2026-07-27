"""The Tier-B ingest buffer: accept durably, hand back a real id, flush later.

Doc 05 §2 splits capture in two. Tier A validates, resolves `source` /
`origin_key` / `project`, commits one buffer row and acks; Tier B claims that
row later and runs the five-phase pipeline. This module owns the buffer side of
that split — the row, its id, and the replay contract. The 202 route is T1.12's
and the `FOR UPDATE SKIP LOCKED` claim loop is T1.13's.

Two properties this module exists to guarantee:

**The memory id is minted at accept, not at flush.** A 202 that returned no
handle, or a placeholder one, would make the caller poll for something it cannot
name. So capture mints a UUIDv7 up front and the very same value becomes the
`memories` row's id — never re-minted, never remapped. It is carried in
`metadata_` and read back with `buffered_memory_id`; the buffer row's own `id` is
a separate tracking handle (doc 05 §2.2).

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
    # The caller's own `metadata` dict (MemoryCreate.metadata). It nests under
    # this key rather than merging, so a caller key can never collide with the
    # buffer's own bookkeeping (`memory_id`, `origin_key`, ...) and silently
    # win. doc 05 §3.1 lists it among the replayed fields.
    "metadata",
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
    """Write one buffered capture and return it.

    **Two ids, deliberately distinct** (doc 05 §2.2). The buffer row's own `id`
    is the buffer tracking handle; the pre-minted **memory** id is the caller's
    durable reference — the value the 202 returns and the id flush creates the
    `memories` row with, which is what makes a re-claimed row an upsert on a
    known id rather than a duplicate. The memory id rides `metadata_`, so pass
    `memory_id` if you minted one; otherwise one is minted here and returned via
    `buffered_memory_id(row)`.

    The row is added but **not committed** — the caller owns the transaction
    boundary. Invariant 11 and doc 05 §2.2 require capture to **commit the buffer
    row and then ack**, never the reverse: an ack before commit turns a crash in
    that window into an acknowledged capture that no longer exists, which is the
    one failure this whole tier exists to prevent.
    """
    row = MemoryBuffer(
        id=new_id(),
        content=content,
        project=project,
        source=source,
        token_size=token_size,
        status="pending",
        metadata_=build_buffer_metadata(
            memory_id=str(memory_id or new_id()),
            origin_key=origin_key,
            **extra,
        ),
    )
    session.add(row)
    await session.flush()
    return row


def buffered_memory_id(row: MemoryBuffer) -> uuid.UUID:
    """The pre-minted `memories` id this buffered capture will become.

    Distinct from `row.id`, which identifies the buffer entry itself.
    """
    return uuid.UUID(row.metadata_["memory_id"])


async def get(session: AsyncSession, buffer_id: uuid.UUID) -> MemoryBuffer | None:
    return (
        await session.execute(select(MemoryBuffer).where(MemoryBuffer.id == buffer_id))
    ).scalar_one_or_none()


async def pending(session: AsyncSession, limit: int = 100) -> list[MemoryBuffer]:
    """Oldest-first pending rows. Reads the partial `WHERE status='pending'`
    index the claim loop is built around.

    Ties break on `id`: rows enqueued in one transaction share a single
    server-side `now()`, so `created_at` alone leaves within-batch order
    unspecified — and the ids are UUIDv7, so id order IS mint order.
    """
    rows = await session.execute(
        select(MemoryBuffer)
        .where(MemoryBuffer.status == "pending")
        .order_by(MemoryBuffer.created_at, MemoryBuffer.id)
        .limit(limit)
    )
    return list(rows.scalars())

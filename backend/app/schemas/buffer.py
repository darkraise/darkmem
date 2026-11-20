"""Response shapes for the `memory_buffer` read surface (T1.13b, doc 13 §6.1)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class BufferRowResponse(BaseModel):
    """One buffered capture as the monitor renders it.

    `attempts` is a claim count, not a failure count — the flush increments it
    when it claims a row — so it reads "times claimed", never "times failed".
    `max_attempts` rides every row because the number it is measured against is
    runtime config, and a bar rendered from a compile-time copy would disagree
    with the ladder the flush actually walks. `memory_exists` says whether
    the replay materialised the memory row before it failed: a discard deletes
    that memory too.
    """

    id: uuid.UUID
    memory_id: uuid.UUID | None = None
    memory_exists: bool
    project: str
    source: str | None = None
    status: str
    is_stale: bool
    attempts: int
    max_attempts: int
    last_error: str | None = None
    created_at: datetime
    claimed_at: datetime | None = None
    claimed_by: str | None = None
    token_size: int | None = None
    content_preview: str
    content_length: int


class BufferListResponse(BaseModel):
    items: list[BufferRowResponse]
    total: int
    limit: int
    offset: int


class BufferStatsResponse(BaseModel):
    pending: int
    claimed: int
    stale: int
    done: int
    poison: int
    max_attempts: int
    visibility_seconds: int

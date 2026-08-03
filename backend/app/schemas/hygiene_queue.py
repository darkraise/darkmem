from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

MAX_BULK_ITEMS = 100


class HygieneDuplicateItem(BaseModel):
    id: str
    source_memory_id: str
    target_memory_id: str
    rel_type: str
    project: str
    score: float | None
    verdict: str | None
    hygiene_state: str | None
    detected_at: str | None
    created_at: datetime


class HygieneDuplicateListResponse(BaseModel):
    items: list[HygieneDuplicateItem]
    total: int
    limit: int
    offset: int


class HygieneMemoryItem(BaseModel):
    id: str
    project: str
    content_preview: str
    confidence: float | None
    expires_at: datetime | None
    status: str
    superseded_by: str | None
    reason: str
    created_at: datetime


class HygieneMemoryListResponse(BaseModel):
    items: list[HygieneMemoryItem]
    total: int
    limit: int
    offset: int


class HygieneCountsResponse(BaseModel):
    duplicates: int
    low_confidence: int
    expiring_soon: int
    superseded: int


class SupersedeItem(BaseModel):
    memory_id: UUID
    superseded_by: UUID


class BulkSupersedeRequest(BaseModel):
    items: list[SupersedeItem] = Field(min_length=1, max_length=MAX_BULK_ITEMS)


class BulkPruneRequest(BaseModel):
    memory_ids: list[UUID] = Field(min_length=1, max_length=MAX_BULK_ITEMS)


class BulkConfirmDedupRequest(BaseModel):
    relation_ids: list[UUID] = Field(min_length=1, max_length=MAX_BULK_ITEMS)
    hygiene_state: Literal["confirmed", "dismissed"] = "confirmed"


class HygieneActionItemResult(BaseModel):
    id: str
    applied: bool
    event_id: int | None
    reason: str | None


class HygieneBulkActionResponse(BaseModel):
    cycle_id: str
    results: list[HygieneActionItemResult]

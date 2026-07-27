import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.memory import (
    TAG_CATEGORY_MAX_LENGTH,
    TAG_NAME_MAX_LENGTH,
    tag_category,
)


MemoryStatus = Literal["active", "deprecated", "superseded"]


def _validate_tag_lengths(tags: list[str] | None) -> list[str] | None:
    """Reject a tag the `tags` table cannot hold, at the door.

    Capture is a 202 accept: the write it acknowledges happens later, in the
    buffer flush, where a tag longer than its column raises against data the
    caller can no longer be told about. Rejecting it here keeps the ack honest —
    a capture that cannot possibly be materialised is a 4xx, never an accept
    followed by a silent landing in the poison queue (Fable review of T1.13,
    finding I-1).
    """
    if not tags:
        return tags
    for tag in tags:
        if len(tag) > TAG_NAME_MAX_LENGTH:
            raise ValueError(
                f"tag is {len(tag)} characters, over the "
                f"{TAG_NAME_MAX_LENGTH}-character limit: {tag[:40]!r}..."
            )
        category = tag_category(tag)
        if category is not None and len(category) > TAG_CATEGORY_MAX_LENGTH:
            raise ValueError(
                f"tag category {category[:40]!r}... is {len(category)} characters, "
                f"over the {TAG_CATEGORY_MAX_LENGTH}-character limit"
            )
    return tags


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    source: str = "api"
    source_agent: str | None = None
    # Declared capture-session identity. Resolved at the front door before
    # this schema is built; see resolve_origin_key (doc 05 §2.1).
    origin_key: str | None = None
    memory_type: str | None = None
    importance: float = 0.5
    metadata: dict = Field(default_factory=dict)
    expires_at: datetime | None = None
    project: str | None = None

    _check_tags = field_validator("tags")(_validate_tag_lengths)


class CaptureAck(BaseModel):
    """Tier-A accept response (doc 05 §2.2).

    ``id`` is the pre-minted **memory** id — the caller's durable reference,
    resolvable once the buffer flush (T1.13) runs. It is deliberately not the
    internal `memory_buffer` row's own id, which is a tracking handle the
    caller never sees (`memory_buffer.buffered_memory_id`).
    """

    id: uuid.UUID
    status: Literal["accepted"] = "accepted"


class MemoryUpdate(BaseModel):
    content: str | None = None
    tags: list[str] | None = None
    memory_type: str | None = None
    importance: float | None = None
    metadata: dict | None = None
    expires_at: datetime | None = None
    is_archived: bool | None = None
    project: str | None = None
    status: MemoryStatus | None = None

    _check_tags = field_validator("tags")(_validate_tag_lengths)



class MemoryResponse(BaseModel):
    id: uuid.UUID
    content: str
    source: str
    source_agent: str | None
    memory_type: str | None
    importance: float
    metadata: dict
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    is_archived: bool
    llm_classified_type: str | None = None
    llm_summary: str | None = None
    llm_emotions: list[str] | None = None
    llm_flags: list[str] | None = None
    related_memories: list[dict] | None = None
    project: str = "default"
    status: MemoryStatus = "active"
    superseded_by: uuid.UUID | None = None
    technologies: list[str] = Field(default_factory=list)
    confidence: float = 0.75


class PaginatedMemoryResponse(BaseModel):
    items: list[MemoryResponse]
    total: int
    limit: int
    offset: int


class MemorySearchRequest(BaseModel):
    query: str | None = None
    tags_any: list[str] | None = None
    tags_all: list[str] | None = None
    memory_type: str | None = None
    source: str | None = None
    limit: int = Field(default=20, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    project: str | None = None
    status: list[MemoryStatus] = Field(default_factory=lambda: ["active"])
    technologies_any: list[str] | None = None
    source_any: list[str] | None = None
    memory_type_any: list[str] | None = None


class MemoryBatchCreate(BaseModel):
    entries: list[MemoryCreate] = Field(min_length=1, max_length=100)


class MemoryBulkDelete(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class MemoryBulkDeleteResponse(BaseModel):
    deleted: int
    not_found: list[uuid.UUID] = Field(default_factory=list)
    errored: list[uuid.UUID] = Field(default_factory=list)


class MemoryMergeRequest(BaseModel):
    target_id: uuid.UUID

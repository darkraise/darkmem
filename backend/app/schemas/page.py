from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PageCreateRequest(BaseModel):
    project: str = Field(..., min_length=1)
    title: str | None = None
    parent_id: UUID | None = Field(
        None, description="The parent page; absent or null files at the root."
    )
    after_id: UUID | None = Field(
        None,
        description=(
            "The sibling to place after. Absent or null APPENDS after the "
            "last sibling, unlike PATCH, where a null after_id places first."
        ),
    )
    content: str | None = None
    properties: dict | None = None


class PageCreateResponse(BaseModel):
    id: UUID
    project: str
    parent_id: UUID | None
    order_index: int
    title: str | None
    content_hash: str
    blocks_written: int
    blocks_embedded: int


class PageBlock(BaseModel):
    id: UUID
    parent_id: UUID | None
    order_index: int
    type: str
    text: str | None
    properties: dict | None
    char_start: int | None
    char_end: int | None


class PageResponse(BaseModel):
    id: UUID
    project: str
    parent_id: UUID | None
    order_index: int
    title: str | None
    content_hash: str
    properties: dict | None
    blocks: list[PageBlock]
    content: str | None


class PageListItem(BaseModel):
    id: UUID
    project: str
    parent_id: UUID | None
    order_index: int
    title: str | None
    content_hash: str
    properties: dict | None
    created_at: datetime
    updated_at: datetime


class PagePatchRequest(BaseModel):
    title: str | None = Field(None, description="Present renames the page.")
    parent_id: UUID | None = Field(
        None,
        description=(
            "Present moves the page; null moves it to the root. Dispatch is on "
            "presence, not on value."
        ),
    )
    after_id: UUID | None = Field(
        None,
        description=(
            "The sibling to place after within parent_id. Absent or null "
            "places FIRST, unlike POST, where absent appends. Only valid "
            "together with parent_id."
        ),
    )


class PagePatchResponse(BaseModel):
    id: UUID


class PageRestoreResponse(BaseModel):
    restored: int


class PageTrashEmptyResponse(BaseModel):
    purged: int

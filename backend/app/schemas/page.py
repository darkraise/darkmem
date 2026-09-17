from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.services.page_door import MAX_BLOCKS


class PageCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class PageBlock(BaseModel):
    id: UUID
    parent_id: UUID | None
    order_index: int
    type: str
    text: str | None
    properties: dict | None
    char_start: int | None
    char_end: int | None
    # The block's own markdown, sliced from the page's content. `text` is
    # marker-stripped, so the two differ: "Sub" against "## Sub".
    source: str | None = None


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


class PageTrashItem(BaseModel):
    id: UUID
    title: str | None
    parent_id: UUID | None
    deleted_at: datetime


class PagePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class PageBlockInsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1)
    text: str
    parent_id: str | None = None
    after_block_id: str | None = None
    properties: dict | None = None
    expected_hash: str | None = None
    block_id: UUID | None = Field(
        None,
        description=(
            "The new block's id, chosen by the client so it can address the "
            "block before the response arrives. Absent mints one."
        ),
    )


class PageBlockUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    type: str | None = None
    properties: dict | None = None
    expected_hash: str | None = None


class PageBlockMoveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_parent_id: str | None = None
    after_block_id: str | None = None
    expected_hash: str | None = None


class PageBlockBatchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: UUID
    type: str = Field(min_length=1)
    text: str
    properties: dict | None = None
    parent_id: UUID | None = None
    after_block_id: UUID | None = None


class PageBlockBatchInsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocks: list[PageBlockBatchItem] = Field(min_length=1, max_length=MAX_BLOCKS)
    expected_hash: str | None = None

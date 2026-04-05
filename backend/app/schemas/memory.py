import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    content: str
    tags: list[str] = Field(default_factory=list)
    source: str = "api"
    source_agent: str | None = None
    memory_type: str | None = None
    importance: float = 0.5
    metadata: dict = Field(default_factory=dict)
    expires_at: datetime | None = None


class MemoryUpdate(BaseModel):
    content: str | None = None
    tags: list[str] | None = None
    memory_type: str | None = None
    importance: float | None = None
    metadata: dict | None = None
    expires_at: datetime | None = None
    is_archived: bool | None = None


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
    limit: int = 20
    offset: int = 0


class MemoryBatchCreate(BaseModel):
    entries: list[MemoryCreate]


class MemoryMergeRequest(BaseModel):
    target_id: uuid.UUID

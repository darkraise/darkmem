"""Wire shapes for the work-log lane. Both doors validate through these."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.services.worklog import (
    MAX_BODY_CHARS,
    MAX_ENTRIES_PER_APPEND,
    MAX_PROPERTIES_BYTES,
    properties_size,
)

Kind = Literal["checkpoint", "ledger", "note"]
State = Literal["open", "closed"]


def _bounded(value: dict | None) -> dict | None:
    if value is not None and properties_size(value) > MAX_PROPERTIES_BYTES:
        raise ValueError(f"properties encode to more than {MAX_PROPERTIES_BYTES} bytes")
    return value


class WorklogEntryIn(BaseModel):
    kind: Kind
    body: str = Field(min_length=1, max_length=MAX_BODY_CHARS)
    properties: dict = Field(default_factory=dict)

    @field_validator("properties")
    @classmethod
    def _properties_fit(cls, value: dict) -> dict:
        return _bounded(value)


class WorklogAppendRequest(BaseModel):
    project: str = Field(min_length=1, max_length=200)
    workstream: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=500)
    client: str | None = Field(default=None, max_length=200)
    properties: dict = Field(default_factory=dict)
    run_key: str | None = Field(default=None, max_length=500)
    entries: list[WorklogEntryIn] = Field(min_length=1, max_length=MAX_ENTRIES_PER_APPEND)

    @field_validator("properties")
    @classmethod
    def _properties_fit(cls, value: dict) -> dict:
        return _bounded(value)


class WorkstreamUpdateRequest(BaseModel):
    state: State | None = None
    retain: bool | None = None
    title: str | None = Field(default=None, max_length=500)
    properties: dict | None = None

    @field_validator("properties")
    @classmethod
    def _properties_fit(cls, value: dict | None) -> dict | None:
        return _bounded(value)


class WorkstreamOut(BaseModel):
    id: UUID
    project: str
    key: str
    title: str | None
    client: str | None
    state: State
    closed_at: datetime | None
    retain: bool
    properties: dict
    last_entry_at: datetime
    created_at: datetime
    updated_at: datetime


class WorklogEntryOut(BaseModel):
    id: UUID
    workstream_id: UUID
    seq: int
    run_key: str
    kind: Kind
    body: str
    properties: dict
    created_at: datetime


class WorklogAppendResponse(BaseModel):
    workstream: WorkstreamOut
    entry_ids: list[UUID]


class WorklogResumeResponse(BaseModel):
    workstream: WorkstreamOut
    checkpoint: WorklogEntryOut | None
    notes: list[WorklogEntryOut]
    notes_truncated: bool
    ledger: list[WorklogEntryOut]


class WorkstreamListResponse(BaseModel):
    items: list[WorkstreamOut]
    next_before: str | None


class WorklogEntryListResponse(BaseModel):
    items: list[WorklogEntryOut]
    next_after: int | None

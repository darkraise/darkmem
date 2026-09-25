"""Wire shapes for the work-log lane. Both doors validate through these."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


def _unstorable(value: object) -> str | None:
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            if "\x00" in item:
                return "a string or properties value contains U+0000, which cannot be stored"
        elif isinstance(item, float):
            if not math.isfinite(item):
                return (
                    f"a properties value is {item!r}; jsonb stores only finite "
                    "numbers, not NaN or infinity"
                )
        elif isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return None


class _Storable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Postgres text and jsonb cannot hold U+0000, jsonb cannot hold NaN or
    # infinity, and the service maps only IntegrityError, so either value past
    # this point answers 500 on either door. Refused, never stripped or
    # coerced: a ledger body is stored exactly as written.
    @model_validator(mode="after")
    def _storable(self):
        problem = _unstorable(self.model_dump())
        if problem is not None:
            raise ValueError(problem)
        return self


class WorklogEntryIn(_Storable):
    kind: Kind
    body: str = Field(min_length=1, max_length=MAX_BODY_CHARS)
    properties: dict = Field(default_factory=dict)

    @field_validator("properties")
    @classmethod
    def _properties_fit(cls, value: dict) -> dict:
        return _bounded(value)


class WorklogAppendRequest(_Storable):
    project: str = Field(min_length=1, max_length=200)
    workstream: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=500)
    client: str | None = Field(default=None, max_length=200)
    properties: dict = Field(default_factory=dict)
    run_key: str | None = Field(default=None, max_length=500)
    expected_last_seq: int | None = Field(default=None, ge=0)
    entries: list[WorklogEntryIn] = Field(min_length=1, max_length=MAX_ENTRIES_PER_APPEND)

    @field_validator("properties")
    @classmethod
    def _properties_fit(cls, value: dict) -> dict:
        return _bounded(value)

    @model_validator(mode="after")
    def _one_kind_under_a_precondition(self):
        if self.expected_last_seq is not None and len({entry.kind for entry in self.entries}) != 1:
            raise ValueError("expected_last_seq needs every entry of the append to share one kind")
        return self


class WorkstreamUpdateRequest(_Storable):
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
    last_seq: int


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

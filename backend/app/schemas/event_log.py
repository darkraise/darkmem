"""Response shapes for the events read API (T1.08, doc 12 §7).

Distinct from `app.schemas.events`, which validates the transient `/ws`
broadcast payloads (`EVENT_SCHEMAS`) — this module is the durable `events`
table's read side.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EventLogEntry(BaseModel):
    id: int
    created_at: datetime
    event_type: str
    object_type: str
    object_id: UUID | None = None
    project: str | None = None
    actor: str | None = None
    api_key_id: UUID | None = None
    source: str | None = None
    payload: dict = Field(default_factory=dict)


class EventListResponse(BaseModel):
    items: list[EventLogEntry]
    total: int


class CalendarBucket(BaseModel):
    day: date
    count: int


class EventCalendarResponse(BaseModel):
    buckets: list[CalendarBucket]


class EventTimelineResponse(BaseModel):
    items: list[EventLogEntry]
    total: int

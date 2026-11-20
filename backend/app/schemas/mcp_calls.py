"""Wire shapes for the MCP call log (``GET /api/v1/mcp-calls``)."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class McpCallRow(BaseModel):
    id: UUID
    occurred_at: datetime
    tool: str
    scope: str | None = None
    status: str
    duration_ms: int
    api_key_id: UUID | None = None
    key_name: str | None = None
    client: str | None = None
    project: str | None = None
    #: Minimised: content arguments appear as sizes, queries only when the
    #: operator turned query logging on.
    arguments: dict[str, Any]
    result_count: int | None = None
    result_ids: list[str]
    error: str | None = None


class McpCallListResponse(BaseModel):
    items: list[McpCallRow]
    total: int


class McpToolStat(BaseModel):
    tool: str
    scope: str | None = None
    calls: int
    errors: int
    denied: int
    avg_duration_ms: int
    p95_duration_ms: int
    last_at: datetime


class McpCallerStat(BaseModel):
    api_key_id: UUID | None = None
    key_name: str | None = None
    client: str | None = None
    calls: int
    errors: int
    last_at: datetime
    top_tool: str


class McpObjectStat(BaseModel):
    id: str
    hits: int
    last_at: datetime
    tools: list[str]


class McpCallBucket(BaseModel):
    bucket: datetime
    calls: int
    errors: int


class McpCallSummaryResponse(BaseModel):
    since: datetime
    until: datetime
    total: int
    errors: int
    denied: int
    avg_duration_ms: int
    p95_duration_ms: int
    tools: list[McpToolStat]
    callers: list[McpCallerStat]
    top_objects: list[McpObjectStat]
    series: list[McpCallBucket]
    #: Whether search queries are currently stored (the retention job's
    #: ``log_query_text``), so the page can say why a query reads as a length.
    query_text_logged: bool
    #: Calls this process dropped from the log buffer since it started (a
    #: backlog past the buffer bound, or a row the database kept refusing).
    dropped_calls: int = 0

"""Read API over the MCP call log (``mcp_tool_calls``).

Two GET shapes: the recent-calls list with filters, and a window summary
(per tool, per caller, most-returned objects, a time series). Read-only by
construction: rows are written by ``app.services.mcp_call_log`` from the MCP
dispatch middleware and by nothing else; the ``mcp_call_cleanup`` job prunes
them. REST-only and login-gated, like the rest of the Activity surface.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import SessionDep
from app.schemas.mcp_calls import (
    McpCallBucket,
    McpCallerStat,
    McpCallListResponse,
    McpCallRow,
    McpCallSummaryResponse,
    McpObjectStat,
    McpToolStat,
)
from app.services.mcp_call_log import MCP_CALL_CLEANUP_JOB_KEY

router = APIRouter(prefix="/api/v1/mcp-calls", tags=["mcp-calls"])

_DEFAULT_WINDOW = timedelta(days=7)
_TOP = 20


def _filters(
    *,
    tool: str | None,
    status: str | None,
    api_key_id: UUID | None,
    client: str | None,
    project: str | None,
    object_id: str | None,
    since: datetime | None,
    until: datetime | None,
) -> tuple[str, dict]:
    clauses: list[str] = []
    params: dict = {}
    if tool:
        clauses.append("tool = :tool")
        params["tool"] = tool
    if status:
        clauses.append("status = :status")
        params["status"] = status
    if api_key_id:
        clauses.append("api_key_id = CAST(:api_key_id AS uuid)")
        params["api_key_id"] = str(api_key_id)
    if client:
        clauses.append("client = :client")
        params["client"] = client
    if project:
        clauses.append("project = :project")
        params["project"] = project
    if object_id:
        clauses.append("CAST(:object_id AS text) = ANY(result_ids)")
        params["object_id"] = object_id
    if since:
        clauses.append("occurred_at >= :since")
        params["since"] = since
    if until:
        clauses.append("occurred_at < :until")
        params["until"] = until
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.get("", response_model=McpCallListResponse)
async def list_mcp_calls(
    tool: str | None = None,
    status: Literal["ok", "error", "denied"] | None = None,
    api_key_id: UUID | None = None,
    client: str | None = None,
    project: str | None = None,
    object_id: str | None = Query(
        default=None, description="Only calls that returned this object id.",
    ),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    where, params = _filters(
        tool=tool, status=status, api_key_id=api_key_id, client=client,
        project=project, object_id=object_id, since=since, until=until,
    )
    total = (await session.execute(
        text(f"SELECT COUNT(*) FROM mcp_tool_calls {where}"), params,
    )).scalar_one()
    rows = (await session.execute(
        text(
            f"""
            SELECT id, occurred_at, tool, scope, status, duration_ms, api_key_id,
                   key_name, client, project, arguments, result_count,
                   result_ids, error
            FROM mcp_tool_calls {where}
            ORDER BY occurred_at DESC, id DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {**params, "limit": limit, "offset": offset},
    )).mappings().all()
    return McpCallListResponse(
        items=[McpCallRow(**dict(r)) for r in rows], total=int(total),
    )


@router.get("/summary", response_model=McpCallSummaryResponse)
async def summarise_mcp_calls(
    since: datetime | None = None,
    until: datetime | None = None,
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    end = _aware(until) if until else datetime.now(timezone.utc)
    start = _aware(since) if since else end - _DEFAULT_WINDOW
    if start >= end:
        raise HTTPException(status_code=422, detail="since must be before until")
    params = {"since": start, "until": end}
    window = "occurred_at >= :since AND occurred_at < :until"

    totals = (await session.execute(text(
        f"""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE status = 'error') AS errors,
               COUNT(*) FILTER (WHERE status = 'denied') AS denied,
               COALESCE(AVG(duration_ms), 0) AS avg_ms,
               COALESCE(percentile_disc(0.95) WITHIN GROUP (ORDER BY duration_ms), 0) AS p95_ms
        FROM mcp_tool_calls WHERE {window}
        """
    ), params)).mappings().one()

    tools = (await session.execute(text(
        f"""
        SELECT tool, MAX(scope) AS scope, COUNT(*) AS calls,
               COUNT(*) FILTER (WHERE status = 'error') AS errors,
               COUNT(*) FILTER (WHERE status = 'denied') AS denied,
               COALESCE(AVG(duration_ms), 0) AS avg_ms,
               COALESCE(percentile_disc(0.95) WITHIN GROUP (ORDER BY duration_ms), 0) AS p95_ms,
               MAX(occurred_at) AS last_at
        FROM mcp_tool_calls WHERE {window}
        GROUP BY tool ORDER BY calls DESC, tool
        """
    ), params)).mappings().all()

    callers = (await session.execute(text(
        f"""
        SELECT api_key_id, MAX(key_name) AS key_name, client, COUNT(*) AS calls,
               COUNT(*) FILTER (WHERE status <> 'ok') AS errors,
               MAX(occurred_at) AS last_at,
               mode() WITHIN GROUP (ORDER BY tool) AS top_tool
        FROM mcp_tool_calls WHERE {window}
        GROUP BY api_key_id, client ORDER BY calls DESC
        LIMIT :top
        """
    ), {**params, "top": _TOP})).mappings().all()

    objects = (await session.execute(text(
        f"""
        SELECT obj AS id, COUNT(*) AS hits, MAX(occurred_at) AS last_at,
               array_agg(DISTINCT tool ORDER BY tool) AS tools
        FROM mcp_tool_calls, unnest(result_ids) AS obj
        WHERE {window} AND status = 'ok'
        GROUP BY obj ORDER BY hits DESC, last_at DESC
        LIMIT :top
        """
    ), {**params, "top": _TOP})).mappings().all()

    bucket = "hour" if end - start <= timedelta(days=2) else "day"
    series = (await session.execute(text(
        f"""
        SELECT date_trunc('{bucket}', occurred_at AT TIME ZONE 'UTC') AT TIME ZONE 'UTC' AS bucket,
               COUNT(*) AS calls,
               COUNT(*) FILTER (WHERE status <> 'ok') AS errors
        FROM mcp_tool_calls WHERE {window}
        GROUP BY 1 ORDER BY 1
        """
    ), params)).mappings().all()

    cfg = (await session.execute(
        text("SELECT value FROM config WHERE key = :k"),
        {"k": f"job:{MCP_CALL_CLEANUP_JOB_KEY}"},
    )).scalar_one_or_none()
    query_text_logged = (
        isinstance(cfg, dict)
        and int((cfg.get("config") or {}).get("log_query_text", 0) or 0) == 1
    )

    return McpCallSummaryResponse(
        since=start,
        until=end,
        total=int(totals["total"]),
        errors=int(totals["errors"]),
        denied=int(totals["denied"]),
        avg_duration_ms=round(float(totals["avg_ms"])),
        p95_duration_ms=int(totals["p95_ms"]),
        tools=[
            McpToolStat(
                tool=r["tool"], scope=r["scope"], calls=r["calls"],
                errors=r["errors"], denied=r["denied"],
                avg_duration_ms=round(float(r["avg_ms"])),
                p95_duration_ms=int(r["p95_ms"]), last_at=r["last_at"],
            )
            for r in tools
        ],
        callers=[McpCallerStat(**dict(r)) for r in callers],
        top_objects=[McpObjectStat(**dict(r)) for r in objects],
        series=[McpCallBucket(**dict(r)) for r in series],
        query_text_logged=query_text_logged,
    )

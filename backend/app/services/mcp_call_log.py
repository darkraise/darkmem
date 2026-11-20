"""The MCP call log: one ``mcp_tool_calls`` row per ``tools/call``.

``events`` journals what the MCP door *wrote*; nothing recorded what it was
*asked*. This module is that record: which tool, which key and client, when,
how long, how it ended, a minimised view of the arguments and the ids the call
handed back. It answers "what did this client recently request" and the
aggregate questions the Activity page's MCP tab asks of it.

**Off the hot path.** ``record_call`` is synchronous and only appends to an
in-process buffer; one background task drains it in batches on its own session,
the same posture ``access_stats`` takes for read counters. A log miss must never
slow or fail the tool call it describes, so every failure here is swallowed and
logged. A buffer that outgrows ``_BUFFER_MAX`` drops its oldest entries and
counts them (``dropped_calls``, served by the summary route). A failed flush
puts its batch back at the front and the next attempt waits, doubling up to
``_BACKOFF_MAX_SECONDS``, for as long as the connection itself is failing.
Any other failure is settled row by row: an entry that cannot become a row,
or a row refused on its own, is dropped and counted, so one bad call can
neither hold the log back nor take its neighbours with it.

A validation error is stored as its error type and field location only: the
text pydantic produces repeats the offending argument's value.

**Write-time minimisation** (CLAUDE.md, events journal). Content arguments
(``content``, ``entries``, ``findings``, ``text``, ``properties``) are never
stored, only their size. Query arguments (``query``, ``question``, ``subject``)
are stored only while the ``mcp_call_cleanup`` job's ``log_query_text`` is 1;
otherwise only their length. Results are reduced to a count and up to
``_MAX_RESULT_IDS`` ids, never their text.

Not recorded in read-only mode: the backup worker's role cannot write, and the
log is not worth an error per call there.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from app.config import settings
from app.services.job_registry import FieldDescriptor
from app.utils.background import spawn

logger = logging.getLogger(__name__)

MCP_CALL_CLEANUP_JOB_KEY = "mcp_call_cleanup"
MCP_CALL_RETENTION_DAYS_DEFAULT = 30
MCP_CALL_CONFIG_SCHEMA = [
    FieldDescriptor(
        key="retention_days", label="Retention (days)",
        default=MCP_CALL_RETENTION_DAYS_DEFAULT, min=1, max=3650,
        help="MCP call records older than this are deleted.",
    ),
    FieldDescriptor(
        key="log_query_text", label="Log query text (0 = off, 1 = on)",
        default=0, min=0, max=1,
        help=(
            "When 1, search queries and questions are stored with each call. "
            "When 0, only their length is."
        ),
    ),
]

#: Arguments whose value is the caller's content. Stored as a size, always.
CONTENT_ARGS = frozenset({"content", "entries", "findings", "text", "properties"})
#: Arguments whose value is what the caller searched for. Stored verbatim only
#: while ``log_query_text`` is on.
QUERY_ARGS = frozenset({"query", "question", "subject"})

_MAX_STR = 200
_MAX_QUERY = 500
_MAX_LIST = 20
_MAX_RESULT_IDS = 50
_MAX_ERROR = 500
_MAX_PARSE_CHARS = 2_000_000
_BUFFER_MAX = 5_000
_FLUSH_DELAY_SECONDS = 0.5
_FLUSH_BATCH = 500
_BACKOFF_MAX_SECONDS = 60
_CONFIG_TTL_SECONDS = 30.0

# Keys whose value names a returned object, in preference order: a section hit
# carries both its block and its document, and the document is what was read.
_ID_KEYS = ("memory_id", "fact_id", "article_id", "document_id", "id")
_LIST_KEYS = (
    "results", "rows", "items", "hits", "memories", "entries", "facts",
    "articles", "symbols", "workstreams", "revisions", "duplicates",
)


@dataclass
class _Pending:
    occurred_at: datetime
    tool: str
    scope: str | None
    status: str
    duration_ms: int
    api_key_id: uuid.UUID | None
    key_name: str | None
    client: str | None
    arguments: dict = field(default_factory=dict)
    result: Any = None
    error: str | None = None


_buffer: deque[_Pending] = deque()
#: Off only in the test suite, which drains explicitly onto its own
#: rollback-isolated connection instead of committing from a background task.
_auto_flush = True
_flusher: asyncio.Task | None = None
_dropped = 0
_dropped_logged = 0
_backoff_seconds = 0
_config_cache: tuple[float, bool] | None = None


def record_call(
    *,
    tool: str,
    scope: str | None,
    status: str,
    duration_ms: int,
    api_key_id: uuid.UUID | None,
    key_name: str | None,
    client: str | None,
    arguments: Any,
    result: Any = None,
    error: str | None = None,
) -> None:
    """Queue one call for the log. Synchronous, never raises."""
    global _dropped
    if settings.read_only:
        return
    try:
        _buffer.append(_Pending(
            occurred_at=datetime.now(timezone.utc),
            tool=tool,
            scope=scope,
            status=status,
            duration_ms=max(0, int(duration_ms)),
            api_key_id=api_key_id,
            key_name=key_name,
            client=client,
            arguments=dict(arguments) if isinstance(arguments, dict) else {},
            result=result,
            error=(error or None) and minimise_error(str(error))[:_MAX_ERROR],
        ))
        _trim()
        _ensure_flusher()
    except Exception:
        logger.warning("mcp_call_log: could not queue a call", exc_info=True)


_VALIDATION_HEAD = re.compile(r"\d+ validation errors? for \S+")
_VALIDATION_TYPE = re.compile(r"\[type=([\w.]+)")


def minimise_error(error: str) -> str:
    """Reduce a pydantic validation error to its type and field locations.

    Any other text is kept as it is.
    """
    head = _VALIDATION_HEAD.search(error)
    if head is None:
        return error
    fields = []
    location = None
    for line in error[head.end():].splitlines():
        if not line.strip():
            continue
        if not line.startswith(" "):
            location = line.strip()
            continue
        kind = _VALIDATION_TYPE.search(line)
        if kind and location is not None:
            fields.append(f"{location} ({kind.group(1)})")
            location = None
    return f"{error[:head.end()]}: {'; '.join(fields) or 'unparsed'}"


def _trim() -> None:
    global _dropped
    while len(_buffer) > _BUFFER_MAX:
        _buffer.popleft()
        _dropped += 1


def _requeue(batch: list[_Pending]) -> None:
    """Put a batch that failed to write back at the front of the buffer."""
    _buffer.extendleft(reversed(batch))
    _trim()


def dropped_calls() -> int:
    """Calls this process dropped from the log since it started."""
    return _dropped


def _ensure_flusher() -> None:
    global _flusher
    if not _auto_flush:
        return
    if _flusher is not None and not _flusher.done():
        return
    try:
        _flusher = spawn(_flush_loop(), name="mcp_call_log_flush")
    except RuntimeError:
        # No running loop (a sync caller in a test); the next call retries.
        _flusher = None


async def _flush_loop() -> None:
    await asyncio.sleep(_FLUSH_DELAY_SECONDS)
    while _buffer:
        await flush_once()
        if _backoff_seconds:
            await asyncio.sleep(_backoff_seconds)


async def flush_once(session_factory=None) -> int:
    """Write up to one batch from the buffer. Returns rows written."""
    global _backoff_seconds, _dropped, _dropped_logged
    if not _buffer:
        return 0
    batch = [_buffer.popleft() for _ in range(min(len(_buffer), _FLUSH_BATCH))]
    if session_factory is None:
        from app.database import async_session_factory as session_factory
    try:
        async with session_factory() as session:
            log_query_text = await _log_query_text(session)
            rows, unbuildable = _build_rows(batch, log_query_text=log_query_text)
            refused = 0
            try:
                if rows:
                    await session.execute(_INSERT_SQL, rows)
                await session.commit()
            except Exception as exc:
                if _is_outage(exc):
                    raise
                await session.rollback()
                refused = await _write_row_by_row(session, rows)
        # Counted only once the write is durable: an outage before this
        # point puts the whole batch back, and its rows are judged again.
        _dropped += unbuildable + refused
        _backoff_seconds = 0
        if _dropped > _dropped_logged:
            logger.warning(
                "mcp_call_log: dropped %s call(s)", _dropped - _dropped_logged,
            )
            _dropped_logged = _dropped
        return len(rows) - refused
    except Exception:
        _requeue(batch)
        _backoff_seconds = min(_BACKOFF_MAX_SECONDS, _backoff_seconds * 2 or 1)
        logger.warning(
            "mcp_call_log: could not write %s call(s); retrying in %ss",
            len(batch), _backoff_seconds, exc_info=True,
        )
        return 0


def _build_rows(batch: list[_Pending], *, log_query_text: bool) -> tuple[list[dict], int]:
    """The batch's rows, and how many entries could not become one."""
    rows, unbuildable = [], 0
    for pending in batch:
        try:
            rows.append(_to_row(pending, log_query_text=log_query_text))
        except Exception:
            unbuildable += 1
            logger.warning("mcp_call_log: dropped one %s call that cannot be stored",
                           pending.tool, exc_info=True)
    return rows, unbuildable


def _is_outage(exc: BaseException) -> bool:
    """True only when the connection itself failed.

    Anything else is the database (or the driver) refusing this statement,
    which the row-by-row pass settles row by row, so no entry can be put back
    for ever.
    """
    from sqlalchemy.exc import DBAPIError, OperationalError

    if isinstance(exc, DBAPIError):
        return exc.connection_invalidated or isinstance(exc, OperationalError)
    return isinstance(exc, OSError)


async def _write_row_by_row(session, rows: list[dict]) -> int:
    """Write each row in its own savepoint; return how many were refused.

    An outage raises, so the caller puts the whole batch back; nothing is
    committed before the end.
    """
    refused = 0
    for row in rows:
        try:
            async with session.begin_nested():
                await session.execute(_INSERT_SQL, [row])
        except Exception as exc:
            if _is_outage(exc):
                raise
            refused += 1
            logger.warning(
                "mcp_call_log: dropped one %s call the database refused", row.get("tool"),
                exc_info=True,
            )
    await session.commit()
    return refused


async def drain(session_factory=None) -> None:
    """Write everything queued, now. For tests and shutdown."""
    while _buffer:
        if not await flush_once(session_factory):
            break


def _reset_for_tests() -> None:
    global _backoff_seconds, _config_cache, _dropped, _dropped_logged
    _buffer.clear()
    _config_cache = None
    _dropped = 0
    _dropped_logged = 0
    _backoff_seconds = 0


async def _log_query_text(session) -> bool:
    global _config_cache
    now = time.monotonic()
    if _config_cache is not None and now - _config_cache[0] < _CONFIG_TTL_SECONDS:
        return _config_cache[1]
    value = False
    try:
        row = (await session.execute(
            text("SELECT value FROM config WHERE key = :k"),
            {"k": f"job:{MCP_CALL_CLEANUP_JOB_KEY}"},
        )).scalar_one_or_none()
        if isinstance(row, dict):
            value = int((row.get("config") or {}).get("log_query_text", 0) or 0) == 1
    except Exception:
        logger.debug("mcp_call_log: config read failed", exc_info=True)
        await session.rollback()
    _config_cache = (now, value)
    return value


_INSERT_SQL = text(
    """
    INSERT INTO mcp_tool_calls
        (occurred_at, tool, scope, status, duration_ms, api_key_id, key_name,
         client, project, arguments, result_count, result_ids, error)
    VALUES
        (:occurred_at, :tool, :scope, :status, :duration_ms,
         CAST(:api_key_id AS uuid), :key_name, :client, :project,
         CAST(:arguments AS jsonb), :result_count,
         CAST(:result_ids AS text[]), :error)
    """
)


def _to_row(p: _Pending, *, log_query_text: bool) -> dict:
    args = summarise_arguments(p.arguments, log_query_text=log_query_text)
    project = p.arguments.get("project")
    count, ids = (None, []) if p.status != "ok" else summarise_result(p.result)
    return {
        "occurred_at": p.occurred_at,
        "tool": p.tool[:_MAX_STR],
        "scope": p.scope,
        "status": p.status,
        "duration_ms": p.duration_ms,
        "api_key_id": str(p.api_key_id) if p.api_key_id else None,
        "key_name": p.key_name,
        "client": p.client,
        "project": project[:_MAX_STR] if isinstance(project, str) else None,
        "arguments": json.dumps(args, default=str),
        "result_count": count,
        "result_ids": ids,
        "error": p.error,
    }


def _size(value: Any) -> dict:
    if isinstance(value, str):
        return {"chars": len(value)}
    if isinstance(value, (list, tuple, dict)):
        return {"items": len(value)}
    return {"present": value is not None}


def _scalar(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value if len(value) <= _MAX_STR else {"chars": len(value)}
    if isinstance(value, (list, tuple)):
        if all(v is None or isinstance(v, (bool, int, float, str)) for v in value):
            kept = [_scalar(v) for v in value[:_MAX_LIST]]
            if len(value) > _MAX_LIST:
                kept.append({"more": len(value) - _MAX_LIST})
            return kept
        return {"items": len(value)}
    return _size(value)


def summarise_arguments(arguments: dict, *, log_query_text: bool) -> dict:
    """The arguments as stored: content reduced to sizes, queries gated."""
    out: dict = {}
    for key, value in (arguments or {}).items():
        if not isinstance(key, str):
            continue
        if key in CONTENT_ARGS:
            out[key] = _size(value)
        elif key in QUERY_ARGS:
            if log_query_text and isinstance(value, str):
                out[key] = value[:_MAX_QUERY]
            else:
                out[key] = _size(value)
        else:
            out[key] = _scalar(value)
    return out


def _payload(result: Any) -> Any:
    """The JSON a tool returned, or None when it can't be read cheaply."""
    if result is None:
        return None
    structured = getattr(result, "structured_content", None)
    if structured is None and isinstance(result, dict):
        structured = result.get("structuredContent")
    if isinstance(structured, dict):
        if set(structured) == {"result"}:
            # A tool returning `str` is wrapped as {"result": "<its text>"}.
            inner = structured["result"]
            if not isinstance(inner, str):
                return inner
            return _parse(inner)
        return structured
    content = getattr(result, "content", None)
    if content is None and isinstance(result, dict):
        content = result.get("content")
    if not content:
        return None
    first = content[0]
    raw = getattr(first, "text", None)
    if raw is None and isinstance(first, dict):
        raw = first.get("text")
    return _parse(raw)


def _parse(raw: Any) -> Any:
    if not isinstance(raw, str) or len(raw) > _MAX_PARSE_CHARS:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def _item_id(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    for key in _ID_KEYS:
        value = item.get(key)
        if isinstance(value, (str, int)) and str(value):
            return str(value)[:_MAX_STR]
    return None


def _ids_of(items: list) -> list[str]:
    seen: list[str] = []
    for item in items:
        found = _item_id(item)
        if found is not None and found not in seen:
            seen.append(found)
            if len(seen) >= _MAX_RESULT_IDS:
                break
    return seen


def summarise_result(result: Any) -> tuple[int | None, list[str]]:
    """``(result_count, result_ids)`` for a successful call, never raises."""
    try:
        payload = _payload(result)
        if isinstance(payload, list):
            return len(payload), _ids_of(payload)
        if isinstance(payload, dict):
            for key in _LIST_KEYS:
                value = payload.get(key)
                if isinstance(value, list):
                    return len(value), _ids_of(value)
            sections = payload.get("sections")
            if isinstance(sections, dict):
                flat = [
                    item for value in sections.values() if isinstance(value, list)
                    for item in value
                ]
                return len(flat), _ids_of(flat)
            single = _item_id(payload)
            if single is not None:
                return 1, [single]
        return None, []
    except Exception:
        logger.debug("mcp_call_log: result summary failed", exc_info=True)
        return None, []


def make_mcp_call_cleanup_runner(app, session_factory):
    """Prune ``mcp_tool_calls`` to its retention window, by age like
    ``llm_usage_cleanup``: the table answers "what happened in the last N
    days", so a row ceiling would shorten that answer when traffic peaks."""
    from datetime import timedelta

    async def run() -> dict | int:
        registry = getattr(app.state, "job_registry", None)
        retention = MCP_CALL_RETENTION_DAYS_DEFAULT
        if registry is not None:
            cfg = await registry.load_config(MCP_CALL_CLEANUP_JOB_KEY)
            retention = int(
                cfg.config.get("retention_days", MCP_CALL_RETENTION_DAYS_DEFAULT)
            )
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention)
        async with session_factory() as session:
            deleted = (await session.execute(
                text("DELETE FROM mcp_tool_calls WHERE occurred_at < :cutoff"),
                {"cutoff": cutoff},
            )).rowcount
            await session.commit()
        if not deleted:
            return 0
        logger.info(
            "mcp_call_cleanup: deleted %s row(s) older than %s days",
            deleted, retention,
        )
        return {"deleted": deleted, "retention_days": retention}
    return run

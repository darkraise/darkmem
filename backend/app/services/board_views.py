"""The progress board's saved views (spec 2026-10-13 §2.6).

Two built-ins are code constants, listed first and never written; saved views
are `board_views` rows. A definition is checked against a closed schema and a
byte bound here, at the door, so the table's CHECK never answers a 500.
"""
from __future__ import annotations

import json
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.board_parse import BoardRefusal

PROPERTIES = (
    "type", "title", "number", "state", "source", "note", "assigned", "acceptance",
    "plan_progress", "plan", "spec", "workstream_state", "commit", "last_activity",
)
GROUPABLE = ("type", "state", "source", "assigned", "plan", "workstream_state")
MAX_DEFINITION_BYTES = 16_384
BUILTIN_PREFIX = "builtin:"

Property = Literal[PROPERTIES]  # type: ignore[valid-type]
Groupable = Literal[GROUPABLE]  # type: ignore[valid-type]


class ViewFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property: Property
    operator: Literal["in", "not_in", "contains"]
    values: list[str] = Field(max_length=200)


class ViewSort(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property: Property
    direction: Literal["asc", "desc"]


class ViewDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout: Literal["board", "table"]
    group_by: Groupable | None = None
    filters: list[ViewFilter] = Field(default_factory=list, max_length=20)
    sort: ViewSort | None = None
    columns: list[Property] = Field(default_factory=list, max_length=len(PROPERTIES))
    show_untracked: bool = False


_DEFAULT_COLUMNS = ["type", "number", "title", "state", "source", "assigned", "note"]

BUILTIN_VIEWS: tuple[dict[str, Any], ...] = (
    {
        "id": "builtin:open-register-items",
        "name": "Open register items",
        "builtin": True,
        "position": 0,
        "definition": {
            "layout": "board",
            "group_by": "state",
            "filters": [
                {"property": "type", "operator": "in", "values": ["register_row"]},
                {"property": "state", "operator": "not_in", "values": ["done", "n/a"]},
            ],
            "sort": {"property": "number", "direction": "asc"},
            "columns": _DEFAULT_COLUMNS,
            "show_untracked": False,
        },
    },
    {
        "id": "builtin:plans-in-flight",
        "name": "Plans in flight",
        "builtin": True,
        "position": 1,
        "definition": {
            "layout": "board",
            "group_by": "plan",
            "filters": [
                {"property": "type", "operator": "in", "values": ["plan_task"]},
                {"property": "workstream_state", "operator": "in", "values": ["open"]},
            ],
            "sort": {"property": "number", "direction": "asc"},
            "columns": ["number", "title", "state", "plan", "commit", "last_activity"],
            "show_untracked": False,
        },
    },
)

_COLUMNS = (
    "CAST(id AS text) AS id, project, name, position, definition, created_at, updated_at"
)
_LIST = text(
    f"SELECT {_COLUMNS} FROM board_views WHERE project = CAST(:project AS text) "
    "ORDER BY position, name"
)
_GET = text(f"SELECT {_COLUMNS} FROM board_views WHERE id = CAST(:id AS uuid)")
_NEXT_POSITION = text(
    "SELECT coalesce(max(position), -1) + 1 FROM board_views WHERE project = CAST(:project AS text)"
)
_INSERT = text(
    "INSERT INTO board_views (project, name, position, definition) "
    "VALUES (CAST(:project AS text), CAST(:name AS text), :position, CAST(:definition AS jsonb)) "
    f"RETURNING {_COLUMNS}"
)
_DELETE = text("DELETE FROM board_views WHERE id = CAST(:id AS uuid)")


def _row(row: Any) -> dict[str, Any]:
    return {**dict(row._mapping), "builtin": False}


def validate_definition(definition: Any) -> dict[str, Any]:
    try:
        checked = ViewDefinition.model_validate(definition)
    except ValidationError as exc:
        raise BoardRefusal(
            422, "invalid_definition", f"the view definition is invalid: {exc.errors()[0]['msg']}",
        ) from exc
    value = checked.model_dump()
    size = len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    if size > MAX_DEFINITION_BYTES:
        raise BoardRefusal(
            422, "invalid_definition",
            f"the view definition encodes to {size} bytes; the bound is {MAX_DEFINITION_BYTES}",
        )
    return value


def _view_id(view_id: str) -> str:
    """A saved view's uuid; a built-in id is refused, anything else is unknown."""
    if view_id.startswith(BUILTIN_PREFIX):
        raise BoardRefusal(
            422, "builtin_view", "built-in views cannot be changed; save a copy as a new view",
        )
    try:
        return str(UUID(view_id))
    except ValueError as exc:
        raise BoardRefusal(404, "not_found", f"no view with id {view_id}") from exc


def _name_taken(project: str, name: str) -> BoardRefusal:
    return BoardRefusal(409, "name_taken", f"project {project!r} already has a view named {name!r}")


def _sqlstate(exc: IntegrityError) -> str | None:
    return getattr(getattr(exc, "orig", None), "sqlstate", None)


def _refusal(exc: IntegrityError, project: str, name: str | None) -> BoardRefusal | None:
    """A uniqueness clash, or the size CHECK.

    The door's byte bound measures compact JSON text, while the CHECK measures
    the stored JSONB, which spends a header per element; a definition of many
    tiny values can pass one and fail the other, and must not answer 500.
    """
    if _sqlstate(exc) == "23505":
        return _name_taken(project, name or "")
    if _sqlstate(exc) == "23514":
        return BoardRefusal(
            422, "invalid_definition", "the view definition is too large to store",
        )
    return None


async def list_views(session: AsyncSession, project: str) -> list[dict[str, Any]]:
    saved = [_row(r) for r in await session.execute(_LIST, {"project": project})]
    builtins = [
        {**view, "project": project, "created_at": None, "updated_at": None}
        for view in BUILTIN_VIEWS
    ]
    return builtins + saved


async def create_view(
    session: AsyncSession, *, project: str, name: str, definition: Any, position: int | None,
) -> dict[str, Any]:
    checked = validate_definition(definition)
    if position is None:
        position = (await session.execute(_NEXT_POSITION, {"project": project})).scalar_one()
    try:
        async with session.begin_nested():
            row = (await session.execute(_INSERT, {
                "project": project, "name": name, "position": position,
                "definition": json.dumps(checked),
            })).one()
    except IntegrityError as exc:
        refusal = _refusal(exc, project, name)
        if refusal is not None:
            raise refusal from exc
        raise
    await session.commit()
    return _row(row)


async def update_view(
    session: AsyncSession, view_id: str, *, changes: dict[str, Any],
) -> dict[str, Any]:
    target = _view_id(view_id)
    if not changes:
        raise BoardRefusal(422, "no_change", "name at least one of name, definition or position")
    current = (await session.execute(_GET, {"id": target})).first()
    if current is None:
        raise BoardRefusal(404, "not_found", f"no view with id {view_id}")
    assignments, params = [], {"id": target}
    if "name" in changes:
        assignments.append("name = CAST(:name AS text)")
        params["name"] = changes["name"]
    if "definition" in changes:
        assignments.append("definition = CAST(:definition AS jsonb)")
        params["definition"] = json.dumps(validate_definition(changes["definition"]))
    if "position" in changes:
        assignments.append("position = :position")
        params["position"] = changes["position"]
    statement = text(
        f"UPDATE board_views SET {', '.join(assignments)} WHERE id = CAST(:id AS uuid) "
        f"RETURNING {_COLUMNS}"
    )
    try:
        async with session.begin_nested():
            row = (await session.execute(statement, params)).one()
    except IntegrityError as exc:
        refusal = _refusal(exc, current.project, changes.get("name"))
        if refusal is not None:
            raise refusal from exc
        raise
    await session.commit()
    return _row(row)


async def delete_view(session: AsyncSession, view_id: str) -> None:
    target = _view_id(view_id)
    result = await session.execute(_DELETE, {"id": target})
    if result.rowcount == 0:
        raise BoardRefusal(404, "not_found", f"no view with id {view_id}")
    await session.commit()

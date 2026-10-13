"""The saved-view service and its table (spec 2026-10-13 §2.6)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services.board_parse import BoardRefusal
from app.services.board_views import (
    BUILTIN_VIEWS,
    create_view,
    delete_view,
    list_views,
    update_view,
    validate_definition,
)

DEFINITION = {"layout": "board", "group_by": "state"}


async def test_a_view_round_trips_with_schema_defaults_filled(session):
    view = await create_view(session, project="p", name="Mine", definition=DEFINITION, position=None)
    assert view["position"] == 0 and view["builtin"] is False
    assert view["definition"] == {
        "layout": "board", "group_by": "state", "filters": [], "sort": None,
        "columns": [], "show_untracked": False,
    }
    listed = await list_views(session, "p")
    assert [v["id"] for v in listed] == [v["id"] for v in BUILTIN_VIEWS] + [view["id"]]


async def test_positions_default_past_the_greatest(session):
    await create_view(session, project="p", name="A", definition=DEFINITION, position=4)
    second = await create_view(session, project="p", name="B", definition=DEFINITION, position=None)
    assert second["position"] == 5


async def test_names_are_unique_per_project_only(session):
    await create_view(session, project="p", name="Same", definition=DEFINITION, position=None)
    await create_view(session, project="q", name="Same", definition=DEFINITION, position=None)
    with pytest.raises(BoardRefusal) as refused:
        await create_view(session, project="p", name="Same", definition=DEFINITION, position=None)
    assert (refused.value.status_code, refused.value.reason) == (409, "name_taken")


async def test_update_moves_updated_at_through_the_trigger(session):
    view = await create_view(session, project="p", name="Mine", definition=DEFINITION, position=None)
    await session.execute(
        text("UPDATE board_views SET updated_at = now() - interval '1 day' WHERE id = CAST(:id AS uuid)"),
        {"id": view["id"]},
    )
    updated = await update_view(session, view["id"], changes={"name": "Renamed"})
    assert updated["name"] == "Renamed"
    # The test runs in one transaction, so the trigger's now() is created_at's.
    assert updated["updated_at"] == updated["created_at"]


async def test_delete_then_unknown(session):
    view = await create_view(session, project="p", name="Mine", definition=DEFINITION, position=None)
    await delete_view(session, view["id"])
    with pytest.raises(BoardRefusal) as refused:
        await delete_view(session, view["id"])
    assert refused.value.reason == "not_found"


@pytest.mark.parametrize("view_id, reason", [
    ("builtin:open-register-items", "builtin_view"),
    ("nonsense", "not_found"),
])
async def test_ids_that_name_no_saved_view(session, view_id, reason):
    with pytest.raises(BoardRefusal) as refused:
        await update_view(session, view_id, changes={"name": "x"})
    assert refused.value.reason == reason


def test_an_oversized_definition_is_refused_before_the_check_could_fire():
    big = {**DEFINITION, "filters": [
        {"property": "note", "operator": "contains", "values": ["x" * 200] * 200},
    ]}
    with pytest.raises(BoardRefusal) as refused:
        validate_definition(big)
    assert refused.value.reason == "invalid_definition"


async def test_the_table_check_bounds_what_the_door_would_never_send(session):
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await session.execute(
                text("INSERT INTO board_views (project, name, position, definition) "
                     "VALUES ('p', '', 0, CAST('{}' AS jsonb))"),
            )


async def test_a_definition_the_check_refuses_is_invalid_not_a_500(session, monkeypatch):
    """The door measures JSON text, the CHECK measures JSONB; when they
    disagree the refusal must still be `invalid_definition`."""
    import secrets

    from app.services import board_views

    noise = secrets.token_hex(12_000)
    monkeypatch.setattr(board_views, "validate_definition", lambda _d: {"layout": "board", "x": noise})
    with pytest.raises(BoardRefusal) as refused:
        await create_view(session, project="p", name="Huge", definition=DEFINITION, position=None)
    assert (refused.value.status_code, refused.value.reason) == (422, "invalid_definition")


def test_the_demo_builtin_views_match_the_server():
    """The SPA's demo mode has no server, so it carries its own copy."""
    import json
    from pathlib import Path

    demo = Path(__file__).resolve().parents[2] / "frontend/src/demo/board-builtin-views.json"
    assert json.loads(demo.read_text()) == list(BUILTIN_VIEWS)

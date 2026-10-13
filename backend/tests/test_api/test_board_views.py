"""The board's saved views: built-ins, the four routes and their refusals (spec 2026-10-13 §2.6)."""
from __future__ import annotations

import pytest

from app.services.board_views import BUILTIN_VIEWS

PROJECT = "board-views"
DEFINITION = {
    "layout": "table",
    "group_by": "state",
    "filters": [{"property": "type", "operator": "in", "values": ["register_row"]}],
    "sort": {"property": "number", "direction": "desc"},
    "columns": ["number", "title", "state"],
    "show_untracked": True,
}


async def _create(client, headers, name="Mine", **extra):
    return await client.post(
        "/api/v1/board/views",
        json={"project": PROJECT, "name": name, "definition": DEFINITION, **extra},
        headers=headers,
    )


async def test_the_built_ins_come_first_and_saved_views_follow_by_position(client, auth_headers):
    second = await _create(client, auth_headers, "B")
    first = await _create(client, auth_headers, "A", position=0)
    assert second.status_code == first.status_code == 201
    assert second.json()["position"] == 0 and first.json()["position"] == 0
    third = await _create(client, auth_headers, "C")
    assert third.json()["position"] == 1
    listed = (await client.get(f"/api/v1/board/views?project={PROJECT}", headers=auth_headers)).json()
    assert [v["id"] for v in listed[:2]] == [
        "builtin:open-register-items", "builtin:plans-in-flight",
    ]
    assert all(v["builtin"] for v in listed[:2])
    assert [v["name"] for v in listed[2:]] == ["A", "B", "C"]
    assert listed[2]["definition"] == DEFINITION


def test_the_built_in_definitions_pass_their_own_schema():
    from app.services.board_views import validate_definition

    for view in BUILTIN_VIEWS:
        assert validate_definition(view["definition"]) == view["definition"]


async def test_rename_redefine_and_reposition(client, auth_headers):
    view = (await _create(client, auth_headers)).json()
    response = await client.patch(
        f"/api/v1/board/views/{view['id']}",
        json={"name": "Renamed", "position": 5, "definition": {**DEFINITION, "layout": "board"}},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["name"], body["position"], body["definition"]["layout"]) == ("Renamed", 5, "board")


async def test_delete_answers_204_and_the_view_is_gone(client, auth_headers):
    view = (await _create(client, auth_headers)).json()
    response = await client.delete(f"/api/v1/board/views/{view['id']}", headers=auth_headers)
    assert response.status_code == 204
    again = await client.delete(f"/api/v1/board/views/{view['id']}", headers=auth_headers)
    assert again.status_code == 404
    assert again.json()["error"]["code"] == "not_found"


async def test_a_taken_name_is_a_409_on_create_and_on_rename(client, auth_headers):
    await _create(client, auth_headers, "Taken")
    other = (await _create(client, auth_headers, "Other")).json()
    duplicate = await _create(client, auth_headers, "Taken")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "name_taken"
    rename = await client.patch(
        f"/api/v1/board/views/{other['id']}", json={"name": "Taken"}, headers=auth_headers,
    )
    assert rename.status_code == 409
    assert rename.json()["error"]["code"] == "name_taken"


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
async def test_a_built_in_cannot_be_written(client, auth_headers, method):
    response = await client.request(
        method, "/api/v1/board/views/builtin:plans-in-flight",
        json={"name": "x"} if method == "PATCH" else None, headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "builtin_view"


# A fixed id: parametrize ids must match across pytest-xdist workers.
@pytest.mark.parametrize("view_id", ["00000000-0000-4000-8000-0000000000c1", "not-a-uuid"])
async def test_an_unknown_id_is_a_404(client, auth_headers, view_id):
    response = await client.patch(
        f"/api/v1/board/views/{view_id}", json={"name": "x"}, headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("definition", [
    {**DEFINITION, "layout": "calendar"},
    {**DEFINITION, "group_by": "title"},
    {**DEFINITION, "columns": ["priority"]},
    {**DEFINITION, "filters": [{"property": "state", "operator": "regex", "values": []}]},
    {**DEFINITION, "extra": 1},
    {**DEFINITION, "filters": [
        {"property": "note", "operator": "contains", "values": ["x" * 200] * 200},
    ]},
    "not an object",
])
async def test_an_invalid_definition_is_refused_at_the_door(client, auth_headers, definition):
    response = await client.post(
        "/api/v1/board/views",
        json={"project": PROJECT, "name": "Bad", "definition": definition},
        headers=auth_headers,
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "invalid_definition"


async def test_a_patch_naming_nothing_is_no_change(client, auth_headers):
    view = (await _create(client, auth_headers)).json()
    for body in ({}, {"name": None}):
        response = await client.patch(
            f"/api/v1/board/views/{view['id']}", json=body, headers=auth_headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "no_change"

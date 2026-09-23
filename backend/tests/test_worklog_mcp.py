"""The work-log lane over MCP: the same verbs, the same service, the same keys."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

import pytest

from app.api.mcp.client_identity import ORIGIN_HEADER
from app.api.mcp.scopes import TOOL_SCOPES


@pytest.fixture
def mcp_on_the_test_session(session, monkeypatch):
    import app.api.mcp.server as mcp_module

    @asynccontextmanager
    async def _ctx_manager():
        yield session

    monkeypatch.setattr(mcp_module, "async_session_factory", lambda: _ctx_manager())


def _ctx(headers):
    from types import SimpleNamespace

    from starlette.datastructures import Headers

    return SimpleNamespace(
        request_context=SimpleNamespace(request=SimpleNamespace(headers=Headers(headers)))
    )


def test_each_tool_has_the_scope_the_spec_names():
    assert {name: TOOL_SCOPES[name] for name in (
        "worklog_append", "worklog_update", "worklog_resume",
        "worklog_workstreams", "worklog_entries", "worklog_purge",
    )} == {
        "worklog_append": "capture",
        "worklog_update": "capture",
        "worklog_resume": "read",
        "worklog_workstreams": "read",
        "worklog_entries": "read",
        "worklog_purge": "admin",
    }


async def test_append_then_resume_then_list(mcp_on_the_test_session):
    from app.api.mcp import server

    appended = json.loads(await server.worklog_append(
        project="proj",
        workstream="plan-a",
        entries=[{"kind": "checkpoint", "body": "state"}, {"kind": "ledger", "body": "Task 1\n"}],
        run_key="run-1",
    ))
    assert appended["workstream"]["key"] == "plan-a"
    assert len(appended["entry_ids"]) == 2

    resumed = json.loads(await server.worklog_resume(project="proj", workstream="plan-a"))
    assert resumed["checkpoint"]["body"] == "state"

    listed = json.loads(await server.worklog_workstreams(project="proj"))
    assert [w["key"] for w in listed["items"]] == ["plan-a"]

    entries = json.loads(await server.worklog_entries(project="proj", workstream="plan-a", kind="ledger"))
    assert [e["body"] for e in entries["items"]] == ["Task 1\n"]


async def test_the_run_can_come_from_the_origin_header(mcp_on_the_test_session):
    from app.api.mcp import server

    appended = json.loads(await server.worklog_append(
        project="proj", workstream="plan-a",
        entries=[{"kind": "note", "body": "n"}],
        ctx=_ctx({ORIGIN_HEADER: "boot-7"}),
    ))
    resumed = json.loads(await server.worklog_resume(project="proj", workstream="plan-a"))
    assert resumed["notes"][0]["run_key"].endswith("boot-7")
    assert appended["entry_ids"] == [resumed["notes"][0]["id"]]


async def test_an_undeclared_run_is_refused(mcp_on_the_test_session):
    from app.api.mcp import server

    with pytest.raises(ValueError):
        await server.worklog_append(project="proj", workstream="plan-a", entries=[{"kind": "note", "body": "n"}])


async def test_unknown_workstreams_answer_null(mcp_on_the_test_session):
    from app.api.mcp import server

    assert json.loads(await server.worklog_resume(project="proj", workstream="nope")) is None
    assert json.loads(await server.worklog_entries(project="proj", workstream="nope")) is None
    assert json.loads(await server.worklog_update(project="proj", workstream="nope", state="closed")) is None
    assert json.loads(await server.worklog_purge(project="proj", workstream="nope")) is None


async def test_update_then_purge(mcp_on_the_test_session):
    from app.api.mcp import server

    await server.worklog_append(
        project="proj", workstream="plan-a", entries=[{"kind": "note", "body": "n"}], run_key="r"
    )
    closed = json.loads(await server.worklog_update(project="proj", workstream="plan-a", state="closed", retain=True))
    assert closed["state"] == "closed" and closed["retain"] is True
    purged = json.loads(await server.worklog_purge(project="proj", workstream="plan-a"))
    assert purged == {"purged": "plan-a", "entries": 1}


async def test_a_rest_write_is_readable_over_mcp(client, auth_headers, mcp_on_the_test_session):
    from app.api.mcp import server

    response = await client.post(
        "/api/v1/worklog/entries",
        json={"project": "proj", "workstream": "plan-a", "entries": [{"kind": "checkpoint", "body": "from rest"}]},
        headers={**auth_headers, ORIGIN_HEADER: "run-1"},
    )
    assert response.status_code == 201
    resumed = json.loads(await server.worklog_resume(project="proj", workstream="plan-a"))
    assert resumed["checkpoint"]["body"] == "from rest"

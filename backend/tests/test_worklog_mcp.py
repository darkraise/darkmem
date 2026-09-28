"""The work-log lane over MCP: the same verbs, the same service, the same keys."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from uuid import UUID

import pytest
from sqlalchemy import select

from app.api.mcp.client_identity import CLIENT_HEADER, ORIGIN_HEADER
from app.api.mcp.scopes import TOOL_SCOPES
from app.models.worklog import WorklogEntry


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
        "worklog_workstreams", "worklog_entries", "worklog_search", "worklog_purge",
    )} == {
        "worklog_append": "capture",
        "worklog_update": "capture",
        "worklog_resume": "read",
        "worklog_workstreams": "read",
        "worklog_entries": "read",
        "worklog_search": "read",
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


async def test_one_declared_client_lands_on_one_run_key_through_either_door(
    client, auth_headers, mcp_on_the_test_session
):
    """Both transports feed the resolver the client the request declares; a door
    that hard-coded its own source would key the same run twice."""
    from app.api.mcp import server

    rest = await client.post(
        "/api/v1/worklog/entries",
        json={
            "project": "proj", "workstream": "plan-a", "run_key": "boot-9",
            "entries": [{"kind": "note", "body": "over REST"}],
        },
        headers={**auth_headers, CLIENT_HEADER: "codex"},
    )
    assert rest.status_code == 201, rest.text
    await server.worklog_append(
        project="proj", workstream="plan-a", run_key="boot-9",
        entries=[{"kind": "note", "body": "over MCP"}],
        ctx=_ctx({CLIENT_HEADER: "codex"}),
    )

    resumed = json.loads(await server.worklog_resume(project="proj", workstream="plan-a"))
    assert {n["run_key"] for n in resumed["notes"]} == {"codex:boot-9"}
    assert len(resumed["notes"]) == 2


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


@pytest.mark.parametrize("tool,verb,arguments", [
    ("worklog_update", "update_workstream", {"state": "closed"}),
    ("worklog_purge", "purge_workstream", {}),
])
async def test_a_workstream_purged_after_the_lookup_answers_null(
    mcp_on_the_test_session, monkeypatch, tool, verb, arguments
):
    from app.api.mcp import server
    from app.services import worklog

    await server.worklog_append(
        project="proj", workstream="plan-a", entries=[{"kind": "note", "body": "n"}], run_key="r"
    )

    async def purged_meanwhile(session, workstream_id, **_):
        raise worklog.WorkstreamNotFound(str(workstream_id))

    monkeypatch.setattr(worklog, verb, purged_meanwhile)
    answer = await getattr(server, tool)(project="proj", workstream="plan-a", **arguments)
    assert json.loads(answer) is None


async def test_append_answers_seq_conflict_where_the_route_answers_409(mcp_on_the_test_session, session):
    from app.api.mcp import server

    ledger = [{"kind": "ledger", "body": "Task 1\n"}]
    first = json.loads(await server.worklog_append(
        project="proj", workstream="plan-a", entries=ledger, run_key="run-1", expected_last_seq=0,
    ))
    ledger_seq = (await session.execute(
        select(WorklogEntry.seq).where(WorklogEntry.id == UUID(first["entry_ids"][0]))
    )).scalar_one()
    assert first["last_seq"] == ledger_seq
    stale = json.loads(await server.worklog_append(
        project="proj", workstream="plan-a", entries=ledger, run_key="run-1", expected_last_seq=0,
    ))
    assert stale == {
        "status": "seq_conflict",
        "project": "proj",
        "workstream": "plan-a",
        "kind": "ledger",
        "expected_last_seq": 0,
        "current_last_seq": first["last_seq"],
    }


async def test_search_over_mcp_fuses_both_arms(mcp_on_the_test_session, session, monkeypatch):
    from types import SimpleNamespace

    from app.api.mcp import server
    from app.services.embedder_registry import embedder_registry
    from app.services.worklog_embeddings import embed_entries
    from tests.test_worklog_search import SEARCH_FINGERPRINT, TopicEmbedder

    embedder_registry.forget(SEARCH_FINGERPRINT)
    llm = TopicEmbedder()
    monkeypatch.setattr(server, "_pipeline", SimpleNamespace(llm=llm))
    try:
        appended = json.loads(await server.worklog_append(
            project="proj",
            workstream="plan-a",
            entries=[
                {"kind": "note", "body": "The deploy script now retries"},
                {"kind": "note", "body": "Release notes drafted"},
            ],
            run_key="run-1",
        ))
        await embed_entries(session, llm, entry_ids=appended["entry_ids"])
        answer = json.loads(await server.worklog_search(project="proj", query="deploy"))
    finally:
        embedder_registry.forget(SEARCH_FINGERPRINT)
    assert answer["semantic_ran"] is True
    assert [item["entry"]["id"] for item in answer["items"]] == appended["entry_ids"]
    assert answer["items"][0]["arms"] == ["keyword", "semantic"]


async def test_search_over_mcp_without_a_pipeline_is_keyword_only(mcp_on_the_test_session, monkeypatch):
    from app.api.mcp import server

    monkeypatch.setattr(server, "_pipeline", None)
    await server.worklog_append(
        project="proj",
        workstream="plan-a",
        entries=[{"kind": "note", "body": "Task 3 fixed the flaky migration test"}],
        run_key="run-1",
    )
    answer = json.loads(await server.worklog_search(project="proj", query="migration"))
    assert answer["semantic_ran"] is False
    assert [item["entry"]["body"] for item in answer["items"]] == [
        "Task 3 fixed the flaky migration test",
    ]


async def test_search_over_mcp_refuses_an_unknown_kind(mcp_on_the_test_session):
    from app.api.mcp import server

    with pytest.raises(ValueError):
        await server.worklog_search(project="proj", query="deploy", kind="log")


async def test_search_over_mcp_refuses_a_nul_in_the_query(mcp_on_the_test_session):
    from app.api.mcp import server

    with pytest.raises(ValueError):
        await server.worklog_search(project="proj", query="de\x00ploy")

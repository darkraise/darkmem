"""The work-log lane over REST, including which keys reach which verb."""
from __future__ import annotations

import pytest

from app.api.mcp.client_identity import ORIGIN_HEADER
from app.services.api_keys import issue_key
from app.services.worklog_embeddings import embed_entries
from tests.test_worklog_search import SEARCH_FINGERPRINT, TopicEmbedder

V1 = "/api/v1/worklog"
RUN = {ORIGIN_HEADER: "run-1"}


def _append_body(**overrides):
    body = {
        "project": "proj",
        "workstream": "plan-a",
        "entries": [
            {"kind": "checkpoint", "body": "## State\nsaved"},
            {"kind": "ledger", "body": "Task 1: complete\n"},
        ],
    }
    body.update(overrides)
    return body


async def _key(session, *scopes):
    _row, credential = await issue_key(session, name=f"k-{'-'.join(scopes)}", scopes=list(scopes))
    return {"Authorization": f"Bearer {credential}", **RUN}


async def test_append_answers_201_with_the_workstream(client, auth_headers):
    response = await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["workstream"]["key"] == "plan-a"
    assert body["workstream"]["state"] == "open"
    assert len(body["entry_ids"]) == 2


async def test_an_undeclared_run_is_refused(client, auth_headers):
    response = await client.post(f"{V1}/entries", json=_append_body(), headers=auth_headers)
    assert response.status_code == 422
    assert "`run_key`" in response.text


@pytest.mark.parametrize("entries", [
    [],
    [{"kind": "log", "body": "x"}],
    [{"kind": "ledger", "body": ""}],
    [{"kind": "note", "body": "x" * 65_537}],
    [{"kind": "note", "body": "n"}] * 101,
    [{"kind": "note", "body": "n", "properties": {"p": "x" * 13_000}}],
])
async def test_the_schema_refuses_out_of_bounds_entries(client, auth_headers, entries):
    response = await client.post(
        f"{V1}/entries", json=_append_body(entries=entries), headers={**auth_headers, **RUN}
    )
    assert response.status_code == 422


async def test_resume_is_404_then_the_checkpoint(client, auth_headers):
    missing = await client.get(f"{V1}/resume", params={"project": "proj", "workstream": "plan-a"}, headers=auth_headers)
    assert missing.status_code == 404
    await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    found = await client.get(f"{V1}/resume", params={"project": "proj", "workstream": "plan-a"}, headers=auth_headers)
    assert found.status_code == 200
    body = found.json()
    assert body["checkpoint"]["body"] == "## State\nsaved"
    assert [e["body"] for e in body["ledger"]] == ["Task 1: complete\n"]
    assert body["notes"] == [] and body["notes_truncated"] is False


async def test_lists_page_and_filter(client, auth_headers):
    created = await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    workstream_id = created.json()["workstream"]["id"]
    listing = await client.get(f"{V1}/workstreams", params={"project": "proj"}, headers=auth_headers)
    assert listing.status_code == 200
    assert [w["key"] for w in listing.json()["items"]] == ["plan-a"]
    assert listing.json()["next_before"] is None
    bad_cursor = await client.get(f"{V1}/workstreams", params={"project": "proj", "before": "x"}, headers=auth_headers)
    assert bad_cursor.status_code == 422
    entries = await client.get(f"{V1}/workstreams/{workstream_id}/entries", params={"kind": "ledger"}, headers=auth_headers)
    assert entries.status_code == 200
    assert [e["kind"] for e in entries.json()["items"]] == ["ledger"]
    assert entries.json()["next_after"] is None
    unknown = await client.get(f"{V1}/workstreams/00000000-0000-0000-0000-000000000000/entries", headers=auth_headers)
    assert unknown.status_code == 404


async def test_patch_closes_and_delete_purges(client, auth_headers):
    created = await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    workstream_id = created.json()["workstream"]["id"]
    closed = await client.patch(f"{V1}/workstreams/{workstream_id}", json={"state": "closed", "retain": True}, headers=auth_headers)
    assert closed.status_code == 200
    assert closed.json()["state"] == "closed" and closed.json()["retain"] is True
    bad = await client.patch(f"{V1}/workstreams/{workstream_id}", json={"state": "done"}, headers=auth_headers)
    assert bad.status_code == 422
    deleted = await client.delete(f"{V1}/workstreams/{workstream_id}", headers=auth_headers)
    assert deleted.status_code == 204
    gone = await client.delete(f"{V1}/workstreams/{workstream_id}", headers=auth_headers)
    assert gone.status_code == 404


async def test_keys_reach_exactly_their_scopes(client, session):
    read = await _key(session, "read")
    capture = await _key(session, "capture")
    admin = await _key(session, "admin")

    assert (await client.post(f"{V1}/entries", json=_append_body(), headers=read)).status_code == 403
    created = await client.post(f"{V1}/entries", json=_append_body(), headers=capture)
    assert created.status_code == 201
    workstream_id = created.json()["workstream"]["id"]
    assert (await client.get(f"{V1}/workstreams", params={"project": "proj"}, headers=read)).status_code == 200
    assert (await client.delete(f"{V1}/workstreams/{workstream_id}", headers=capture)).status_code == 403
    assert (await client.delete(f"{V1}/workstreams/{workstream_id}", headers=admin)).status_code == 204


async def test_no_credential_is_401(client):
    response = await client.get(f"{V1}/workstreams", params={"project": "proj"})
    assert response.status_code == 401


@pytest.mark.parametrize("overrides", [
    {"entries": [{"kind": "ledger", "body": "Task 1\x00: complete\n"}]},
    {"entries": [{"kind": "note", "body": "n", "properties": {"p": "\x00"}}]},
    {"entries": [{"kind": "note", "body": "n", "properties": {"k\x00": 1}}]},
    {"entries": [{"kind": "note", "body": "n", "properties": {"p": [{"q": "\x00"}]}}]},
    {"properties": {"p": "\x00"}},
    {"project": "pr\x00j"},
    {"workstream": "plan\x00a"},
    {"title": "t\x00"},
    {"client": "c\x00"},
    {"run_key": "run\x00"},
])
async def test_a_nul_in_anything_stored_is_refused_not_stripped(client, auth_headers, overrides):
    response = await client.post(
        f"{V1}/entries", json=_append_body(**overrides), headers={**auth_headers, **RUN}
    )
    assert response.status_code == 422, response.text
    listing = await client.get(f"{V1}/workstreams", params={"project": "proj"}, headers=auth_headers)
    assert listing.json()["items"] == []


@pytest.mark.parametrize("update", [{"title": "t\x00"}, {"properties": {"p": ["\x00"]}}])
async def test_a_nul_in_an_update_is_refused(client, auth_headers, update):
    created = await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    workstream_id = created.json()["workstream"]["id"]
    response = await client.patch(f"{V1}/workstreams/{workstream_id}", json=update, headers=auth_headers)
    assert response.status_code == 422, response.text


# Raw text rather than json=: the test client's encoder refuses non-finite
# floats, and a real client's body carries the tokens verbatim.
NON_FINITE = ["NaN", "Infinity", "-Infinity", "1e400"]
JSON = {"content-type": "application/json"}


@pytest.mark.parametrize("token", NON_FINITE)
@pytest.mark.parametrize("shape", [
    '{{"project": "proj", "workstream": "plan-a", "properties": {{"p": {token}}}, '
    '"entries": [{{"kind": "note", "body": "n"}}]}}',
    '{{"project": "proj", "workstream": "plan-a", '
    '"entries": [{{"kind": "note", "body": "n", "properties": {{"p": [{token}]}}}}]}}',
], ids=["workstream", "entry"])
async def test_a_non_finite_number_in_an_append_is_422(client, auth_headers, token, shape):
    response = await client.post(
        f"{V1}/entries", content=shape.format(token=token), headers={**auth_headers, **RUN, **JSON}
    )
    assert response.status_code == 422, response.text
    assert "finite" in response.json()["error"]["message"]
    listing = await client.get(f"{V1}/workstreams", params={"project": "proj"}, headers=auth_headers)
    assert listing.json()["items"] == []


@pytest.mark.parametrize("token", NON_FINITE)
async def test_a_non_finite_number_in_an_update_is_422(client, auth_headers, token):
    created = await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    workstream_id = created.json()["workstream"]["id"]
    response = await client.patch(
        f"{V1}/workstreams/{workstream_id}",
        content=f'{{"properties": {{"p": {{"q": {token}}}}}}}', headers={**auth_headers, **JSON},
    )
    assert response.status_code == 422, response.text
    assert "finite" in response.json()["error"]["message"]


async def test_an_unknown_key_in_an_entry_is_422(client, auth_headers):
    entries = [{"kind": "note", "body": "n", "propertes": {"task": 1}}]
    response = await client.post(
        f"{V1}/entries", json=_append_body(entries=entries), headers={**auth_headers, **RUN}
    )
    assert response.status_code == 422, response.text


async def test_an_unknown_key_in_an_update_is_422(client, auth_headers):
    created = await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    workstream_id = created.json()["workstream"]["id"]
    response = await client.patch(
        f"{V1}/workstreams/{workstream_id}", json={"retained": True}, headers=auth_headers
    )
    assert response.status_code == 422, response.text
    fetched = await client.get(
        f"{V1}/resume", params={"project": "proj", "workstream": "plan-a"}, headers=auth_headers
    )
    assert fetched.json()["workstream"]["retain"] is False


def test_the_schema_both_doors_share_refuses_a_nul():
    from pydantic import ValidationError

    from app.schemas.worklog import WorklogAppendRequest, WorkstreamUpdateRequest

    with pytest.raises(ValidationError):
        WorklogAppendRequest(project="proj", workstream="plan-a", entries=[{"kind": "note", "body": "\x00"}])
    with pytest.raises(ValidationError):
        WorkstreamUpdateRequest(properties={"p": "\x00"})


async def test_append_answers_its_last_seq(client, auth_headers):
    response = await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    assert response.status_code == 201, response.text
    body = response.json()
    resumed = await client.get(
        f"{V1}/resume", params={"project": "proj", "workstream": "plan-a"}, headers=auth_headers
    )
    # The default body's last entry is its ledger entry.
    [last] = resumed.json()["ledger"]
    assert last["id"] == body["entry_ids"][-1]
    assert body["last_seq"] == last["seq"]


async def test_a_stale_expected_last_seq_answers_409(client, auth_headers):
    headers = {**auth_headers, **RUN}
    ledger = [{"kind": "ledger", "body": "Task 1: complete\n"}]
    first = await client.post(
        f"{V1}/entries", json=_append_body(entries=ledger, expected_last_seq=0), headers=headers
    )
    assert first.status_code == 201, first.text
    stale = await client.post(
        f"{V1}/entries", json=_append_body(entries=ledger, expected_last_seq=0), headers=headers
    )
    assert stale.status_code == 409
    assert f"but it is {first.json()['last_seq']}" in stale.json()["detail"]
    fresh = await client.post(
        f"{V1}/entries",
        json=_append_body(entries=ledger, expected_last_seq=first.json()["last_seq"]),
        headers=headers,
    )
    assert fresh.status_code == 201, fresh.text


async def test_the_schema_refuses_a_negative_expected_last_seq(client, auth_headers):
    response = await client.post(
        f"{V1}/entries",
        json=_append_body(entries=[{"kind": "ledger", "body": "x\n"}], expected_last_seq=-1),
        headers={**auth_headers, **RUN},
    )
    assert response.status_code == 422
    assert "expected_last_seq" in response.text
    assert "one kind" not in response.text


async def test_the_schema_refuses_a_mixed_kind_precondition(client, auth_headers):
    # The default body mixes a checkpoint and a ledger entry.
    response = await client.post(
        f"{V1}/entries", json=_append_body(expected_last_seq=0), headers={**auth_headers, **RUN}
    )
    assert response.status_code == 422
    assert "one kind" in response.text


@pytest.fixture
def topic_llm():
    from app.main import app
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(SEARCH_FINGERPRINT)
    previous = getattr(app.state, "llm", None)
    app.state.llm = TopicEmbedder()
    yield app.state.llm
    app.state.llm = previous
    embedder_registry.forget(SEARCH_FINGERPRINT)


async def test_search_fuses_both_arms(client, auth_headers, session, topic_llm):
    created = await client.post(f"{V1}/entries", json=_append_body(entries=[
        {"kind": "note", "body": "The deploy script now retries"},
        {"kind": "note", "body": "Release notes drafted"},
    ]), headers={**auth_headers, **RUN})
    ids = created.json()["entry_ids"]
    await embed_entries(session, topic_llm, entry_ids=ids)

    response = await client.post(
        f"{V1}/search", json={"project": "proj", "query": "deploy"}, headers=auth_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["semantic_ran"] is True
    assert [item["entry"]["id"] for item in body["items"]] == ids
    assert body["items"][0]["arms"] == ["keyword", "semantic"]
    assert body["items"][1]["arms"] == ["semantic"]
    assert body["items"][0]["workstream"] == "plan-a"


async def test_search_answers_by_keyword_without_an_orchestrator(client, auth_headers, monkeypatch):
    from app.main import app

    monkeypatch.setattr(app.state, "llm", None, raising=False)
    await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    response = await client.post(
        f"{V1}/search", json={"project": "proj", "query": "saved"}, headers=auth_headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["semantic_ran"] is False
    assert [item["entry"]["body"] for item in response.json()["items"]] == ["## State\nsaved"]


@pytest.mark.parametrize("body", [
    {"query": "deploy"},
    {"project": "proj", "query": ""},
    {"project": "proj", "query": "   "},
    {"project": "proj", "query": "deploy", "kind": "log"},
    {"project": "proj", "query": "deploy", "limit": 101},
    {"project": "proj", "query": "de\x00ploy"},
])
async def test_search_refuses_bad_requests(client, auth_headers, body):
    response = await client.post(f"{V1}/search", json=body, headers=auth_headers)
    assert response.status_code == 422


async def test_a_read_key_searches_and_a_capture_key_does_not(client, session):
    read = await _key(session, "read")
    capture = await _key(session, "capture")
    body = {"project": "proj", "query": "deploy"}
    assert (await client.post(f"{V1}/search", json=body, headers=read)).status_code == 200
    assert (await client.post(f"{V1}/search", json=body, headers=capture)).status_code == 403

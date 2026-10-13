"""The board's records route: projection, ETag and login-only access (spec 2026-10-13 §2.2)."""
from __future__ import annotations

from app.services import worklog
from app.services.api_keys import issue_key
from app.services.document_door import put_document

PROJECT = "board-routes"
REGISTER_URI = "superpowers/registers/r.md"
REGISTER = """# Register — routes

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | first | - | - | open | - |
| 2 | dup | - | - | open | - |
| 2 | dup again | - | - | open | - |
| 3 | short | - | open | - |
"""


async def _file(session, uri=REGISTER_URI, content=REGISTER):
    return await put_document(
        session, None, project=PROJECT, uri=uri, content=content, embed_inline=False,
    )


async def test_records_serve_registers_and_plans(client, auth_headers, session):
    await _file(session)
    await _file(session, "superpowers/plans/p.md", "# Plan\n\n### Task 1: One\n")
    response = await client.get(f"/api/v1/board/records?project={PROJECT}", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert [r["uri"] for r in body["registers"]] == [REGISTER_URI]
    assert [row["number"] for row in body["registers"][0]["rows"]] == [1]
    assert {m["reason"] for m in body["registers"][0]["malformed"]} == {
        "duplicate number 2", "5 cells, not 6",
    }
    assert body["plans"][0]["tasks"][0]["state"] == "untracked"
    assert response.headers["cache-control"] == "private, no-cache"
    assert response.headers["etag"].startswith('W/"')


async def test_the_etag_answers_304_until_something_changes(client, auth_headers, session):
    await _file(session)
    url = f"/api/v1/board/records?project={PROJECT}"
    etag = (await client.get(url, headers=auth_headers)).headers["etag"]
    same = await client.get(url, headers={**auth_headers, "If-None-Match": etag})
    assert same.status_code == 304
    assert same.headers["etag"] == etag

    await _file(session, "superpowers/plans/p.md", "# Plan\n")
    after_put = await client.get(url, headers={**auth_headers, "If-None-Match": etag})
    assert after_put.status_code == 200
    etag = after_put.headers["etag"]

    await worklog.append(
        session, project=PROJECT, key="w", run_key="claude:run-1",
        entries=[{"kind": "ledger", "body": "Task 1: x\n", "properties": {"task": 1}}],
        properties={"plan_uri": "superpowers/plans/p.md"},
    )
    after_append = await client.get(url, headers={**auth_headers, "If-None-Match": etag})
    assert after_append.status_code == 200


async def test_a_dmk_key_is_refused(client, session):
    _row, credential = await issue_key(session, name="k-board", scopes=["read", "capture", "admin"])
    response = await client.get(
        f"/api/v1/board/records?project={PROJECT}",
        headers={"Authorization": f"Bearer {credential}"},
    )
    assert response.status_code == 401

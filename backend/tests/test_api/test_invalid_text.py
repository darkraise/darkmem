"""Text Postgres cannot store is the caller's error, not the server's.

A NUL byte passes every Pydantic and FastAPI bound and is refused only when
Postgres decodes the parameter (SQLSTATE 22021), so without a mapping each
route that binds a query parameter answers 500.
"""
from __future__ import annotations

import pytest

CASES = [
    ("/api/v1/worklog/workstreams", {"project": "pr\x00oj"}),
    ("/api/v1/worklog/resume", {"project": "pr\x00oj", "workstream": "a"}),
    ("/api/v1/worklog/resume", {"project": "proj", "workstream": "a\x00b"}),
    ("/api/v1/documents/manifest", {"project": "pr\x00oj"}),
    ("/api/v1/events", {"object_type": "pa\x00ge"}),
]


@pytest.mark.parametrize("path,params", CASES)
async def test_a_nul_byte_in_a_parameter_answers_422(client, auth_headers, path, params):
    response = await client.get(path, params=params, headers=auth_headers)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "invalid_text"

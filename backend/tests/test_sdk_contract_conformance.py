"""T3.14 — the SDK's wire shape, driven against the real doors.

The generator proves that each bound route exists and that its request schema
declares every field the SDK sends; it cannot prove the door accepts the body.
So the wire shape is read out of `sdks/generate.py` rather than restated here:
paths and fields come from `VERBS`, and a re-pointing that breaks the door
fails here rather than in a client nobody has written yet.

`sdks/*/tests` prove the clients emit this shape; this file proves the shape is
one the app honours. Neither alone is the claim.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SDKS = Path(__file__).resolve().parents[2] / "sdks"
sys.path.insert(0, str(SDKS))

import generate as sdk_generate  # noqa: E402

pytestmark = pytest.mark.asyncio

def _sdk_body(verb: str, values: dict) -> dict:
    """The body the generated clients post, with `None` filtered exactly as
    both `_post` implementations filter it."""
    fields = sdk_generate.VERBS[verb]["fields"]
    return {field: values[field] for field in fields if values.get(field) is not None}


class TestTheEmittedShapeIsAccepted:
    async def test_capture_posts_a_body_the_door_accepts(self, client, auth_headers):
        verb = sdk_generate.VERBS["capture"]
        body = _sdk_body(
            "capture",
            {"content": "the SDK's own capture body", "project": "sdk-conformance",
             "source": None},
        )

        response = await client.post(verb["path"], json=body, headers=auth_headers)

        assert response.status_code == 202, response.text
        assert response.json()["id"]

    async def test_search_posts_a_body_the_door_accepts(self, client, auth_headers):
        verb = sdk_generate.VERBS["search"]
        body = _sdk_body(
            "search",
            {"query": "anything", "project": "sdk-conformance", "limit": None,
             "with_trace": True},
        )

        response = await client.post(verb["path"], json=body, headers=auth_headers)

        assert response.status_code == 200, response.text
        assert "envelope" in response.json()


class TestTheTraceIsAlwaysAsked:
    async def test_the_clients_never_send_that_shape(self):
        """`with_trace` is a declared field with a constant expression in both
        languages — there is no argument threading into it, so no caller can
        ask for an untraced search."""
        assert sdk_generate.TS_EXPRESSIONS["with_trace"] == "true"
        assert sdk_generate.PY_EXPRESSIONS["with_trace"] == "True"

        emitted = sdk_generate.render_python("digest")
        assert "with_trace" not in emitted.split("async def search(", 1)[-1].split(")")[0]

        # The TypeScript half, which the first version of this test omitted.
        # `withTrace?: boolean` back in the options type passes `make build`
        # and both client suites while the client ignores the caller and posts
        # `with_trace: true` anyway — vitest transpiles without typechecking,
        # and `sdks/ts` has no tsconfig, so nothing else in the gate can see it.
        assert "withTrace" not in sdk_generate.render_typescript("digest")

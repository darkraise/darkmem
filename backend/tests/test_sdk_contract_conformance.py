"""T3.14 — the SDK's wire shape, driven against the real doors.

**This file exists because a review drove it and the generator's guards did
not.** The generator can prove that a route exists, that a request schema
declares each field, and that a header literal matches the app's constant. It
proved all three while `declareContext` bound a header that **neither bound
door read**: `resolve_declared_context_for_request` had exactly one caller in
the tree, on a door the SDK had just been re-pointed away from. A declaration
went out on every call, no error came back, and every ranking decision proceeded
as if nothing had been declared — the same silent drop as the `applies_when`
body key the task was written to close, relocated to a header.

No schema check can see that, because "the door declares a `context` field" is
necessary and not sufficient — `POST /api/v1/memories/search` declares one and
deliberately never reads it (`MemoryService.resolve_request_context`'s own
docstring says so). Only driving the door answers it. So the wire shape is read
out of `sdks/generate.py` rather than restated here: paths, fields and header
come from `VERBS` and `CONTEXT_HEADER`, and a re-pointing that breaks
consumption fails here rather than in a client nobody has written yet.

`sdks/*/tests` prove the clients emit this shape; this file proves the shape is
one the app honours. Neither alone is the claim.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SDKS = Path(__file__).resolve().parents[2] / "sdks"
sys.path.insert(0, str(SDKS))

import generate as sdk_generate  # noqa: E402

pytestmark = pytest.mark.asyncio

DECLARED = {"env": "prod", "situation": "debugging"}


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
             "context": None, "with_trace": True},
        )

        response = await client.post(verb["path"], json=body, headers=auth_headers)

        assert response.status_code == 200, response.text
        assert "envelope" in response.json()


class TestADeclaredContextIsResolved:
    """The Critical, turned into a standing check.

    Both ranks are asserted, not just one: the rank-1 body argument and the
    rank-2 header are separate mechanisms in doc 12 §5, the SDK now uses each
    for its own purpose, and a door could honour one and drop the other.
    """

    async def test_the_header_reaches_the_bound_search_door(self, client, auth_headers):
        verb = sdk_generate.VERBS["search"]
        assert verb["carries_context"], "the guard should not have allowed this"
        body = _sdk_body(
            "search", {"query": "anything", "project": "default", "with_trace": True},
        )

        response = await client.post(
            verb["path"],
            json=body,
            headers={
                **auth_headers,
                sdk_generate.CONTEXT_HEADER: json.dumps(DECLARED),
            },
        )

        assert response.status_code == 200, response.text
        echo = response.json()["envelope"]["context"]
        assert echo is not None, (
            "the declaration was dropped: this door does not resolve "
            f"{sdk_generate.CONTEXT_HEADER}, so declareContext reaches nothing"
        )
        assert echo["declared"] == DECLARED
        assert echo["declared_by"] == "header"

    async def test_the_per_call_argument_reaches_it_too(self, client, auth_headers):
        verb = sdk_generate.VERBS["search"]
        body = _sdk_body(
            "search",
            {"query": "anything", "project": "default", "context": DECLARED,
             "with_trace": True},
        )

        response = await client.post(verb["path"], json=body, headers=auth_headers)

        echo = response.json()["envelope"]["context"]
        assert echo is not None and echo["declared"] == DECLARED
        assert echo["declared_by"] == "arg"

    async def test_the_argument_outranks_the_header(self, client, auth_headers):
        """Doc 12 §5's precedence, checked from the SDK's side: the client may
        send both, and it is the server that decides — so the SDK is free to
        stop collapsing them into one carrier."""
        verb = sdk_generate.VERBS["search"]
        body = _sdk_body(
            "search",
            {"query": "anything", "project": "default",
             "context": {"env": "dev"}, "with_trace": True},
        )

        response = await client.post(
            verb["path"],
            json=body,
            headers={
                **auth_headers,
                sdk_generate.CONTEXT_HEADER: json.dumps(DECLARED),
            },
        )

        echo = response.json()["envelope"]["context"]
        assert echo["declared"] == {"env": "dev"}
        assert echo["declared_by"] == "arg"

    async def test_no_declaration_echoes_as_undeclared(self, client, auth_headers):
        """`None`, not an empty object and not a default — the distinction the
        SDK relies on when it declines to send an empty declaration."""
        verb = sdk_generate.VERBS["search"]
        body = _sdk_body("search", {"query": "anything", "with_trace": True})

        response = await client.post(verb["path"], json=body, headers=auth_headers)

        assert response.json()["envelope"]["context"] is None


class TestTheUntracedBranchIsWhyTheOptionIsGone:
    """N-1: the door resolves a declaration **only** when asked for the trace.

    `search_memories_paginated` calls `resolve_request_context` on the
    `with_trace=True` branch alone, and the untraced response has no envelope
    to echo into. So an SDK argument that turned the trace off would be an
    argument that silently dropped the declaration — C-1's failure mode in a
    narrower window, and one both of C-1's guards are blind to: the generator's
    arm reads the request schema, which declares `context` unconditionally.

    The clients therefore emit `with_trace` as a constant. This measures the
    behaviour that makes that constant necessary, so a future round that
    re-adds the argument has to walk past a test naming the cost.
    """

    async def test_an_untraced_search_discards_the_declaration(
        self, client, auth_headers
    ):
        verb = sdk_generate.VERBS["search"]
        body = {"query": "anything", "project": "default", "with_trace": False}

        response = await client.post(
            verb["path"],
            json=body,
            headers={
                **auth_headers,
                sdk_generate.CONTEXT_HEADER: json.dumps(DECLARED),
            },
        )

        assert response.status_code == 200
        assert response.json()["envelope"] is None

    async def test_the_clients_never_send_that_shape(self):
        """`with_trace` is a declared field with a constant expression in both
        languages — there is no argument threading into it, so no caller can
        reach the branch above."""
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

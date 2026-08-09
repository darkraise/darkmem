"""T3.14 — the three verbs' behaviour on the wire (doc 15 §6).

The client builds its own ``httpx.AsyncClient``, so the transport is swapped by
patching the module's ``httpx`` binding. Kept in the test rather than added as
a constructor argument: an injectable-transport parameter is client-platform
surface, and doc 15 §6's whole stance is that this SDK is not one.

Tests are synchronous and drive the coroutine with ``asyncio.run`` so the suite
needs no pytest plugin beyond pytest itself — ``cd sdks/python && python -m
pytest -q`` is the task's Verify and it should hold on a bare interpreter.

**What this file cannot tell you**, and ``backend/tests/test_sdk_contract_conformance.py``
can: whether the door on the other end honours any of it. A review found this
client sending a declared context to two doors that both discarded it, with
every test here green, because a mock transport answers whatever it is told to.
The two files are one claim in two halves.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from darkmem_sdk import Darkmem
from darkmem_sdk.client import CAPTURE_PATH, CONTEXT_HEADER, SEARCH_PATH


class Recorder:
    """Captures the requests the client makes and answers each with `reply`."""

    def __init__(self, reply: dict | None = None, status: int = 200):
        self.requests: list[httpx.Request] = []
        self.reply = reply if reply is not None else {}
        self.status = status

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status, json=self.reply)

    @property
    def only(self) -> httpx.Request:
        assert len(self.requests) == 1, f"expected one request, got {len(self.requests)}"
        return self.requests[0]

    def body(self, index: int = 0) -> dict:
        return json.loads(self.requests[index].content)


@pytest.fixture
def recorder(monkeypatch):
    def install(reply: dict | None = None, status: int = 200) -> Recorder:
        rec = Recorder(reply, status)
        original = httpx.AsyncClient

        def factory(*args, **kwargs):
            return original(*args, transport=httpx.MockTransport(rec), **kwargs)

        monkeypatch.setattr("darkmem_sdk.client.httpx.AsyncClient", factory)
        return rec

    return install


class TestCapture:
    def test_it_posts_the_content_to_the_capture_door(self, recorder):
        rec = recorder({"schema_version": 1, "id": "abc", "status": "accepted"})
        client = Darkmem(base_url="http://darkmem.test:8000")

        ack = asyncio.run(client.capture("the tab is on live data"))

        assert str(rec.only.url) == "http://darkmem.test:8000" + CAPTURE_PATH
        assert rec.body()["content"] == "the tab is on live data"
        assert ack["id"] == "abc"

    def test_the_constructor_project_is_the_default_and_the_argument_wins(
        self, recorder
    ):
        rec = recorder()
        client = Darkmem(project="darkmem")

        asyncio.run(client.capture("one"))
        asyncio.run(client.capture("two", project="other"))

        assert rec.body(0)["project"] == "darkmem"
        assert rec.body(1)["project"] == "other"

    def test_an_empty_project_is_a_value_not_an_omission(self, recorder):
        """Nullish, not falsy. `project=""` is a caller saying something, and
        `or` would silently substitute the constructor's project — a divergence
        from the TypeScript client's `??`, which a generated pair must not have
        (found in review as M-2)."""
        rec = recorder()
        client = Darkmem(project="darkmem")

        asyncio.run(client.capture("one", project=""))

        assert rec.body()["project"] == ""

    def test_an_omitted_argument_is_absent_from_the_wire(self, recorder):
        """Never sent as null. `MemoryCreate` would accept a null `source`, but
        `MemorySearchRequest.limit` is a non-nullable int with a default — one
        filter, applied on both doors, keeps an argument the caller never
        passed from becoming a 422."""
        rec = recorder()

        asyncio.run(Darkmem().capture("content only"))

        assert set(rec.body()) == {"content"}

    def test_a_failure_status_raises(self, recorder):
        recorder({"detail": "nope"}, status=422)

        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(Darkmem().capture("rejected"))


class TestSearch:
    def test_it_posts_the_query_to_the_bound_read(self, recorder):
        rec = recorder({"items": [], "total": 0, "limit": 20, "offset": 0,
                        "envelope": {"context": None}})
        client = Darkmem()

        result = asyncio.run(client.search("what replaced redis"))

        assert str(rec.only.url).endswith(SEARCH_PATH)
        assert rec.body() == {"query": "what replaced redis", "with_trace": True}
        assert result["envelope"]["context"] is None

    def test_the_trace_is_always_asked_for(self, recorder):
        """Not a preference, and not an argument. The door resolves a declared
        context only on the traced branch — an untraced search answers 200 with
        a null envelope and discards the declaration on both ranks — so an
        option to turn the trace off would be an option to silently drop the
        declaration, which is the defect this binding exists to close."""
        rec = recorder()
        client = Darkmem()
        client.declare_context({"env": "prod"})

        asyncio.run(client.search("q"))

        assert rec.body()["with_trace"] is True
        assert CONTEXT_HEADER in rec.only.headers
        with pytest.raises(TypeError):
            asyncio.run(Darkmem().search("q", with_trace=False))

    def test_the_limit_rides_the_body(self, recorder):
        rec = recorder()

        asyncio.run(Darkmem().search("q", limit=5))

        assert rec.body()["limit"] == 5


class TestDeclaredContext:
    def test_no_context_sends_no_header(self, recorder):
        rec = recorder()

        asyncio.run(Darkmem().search("undeclared"))

        assert CONTEXT_HEADER not in rec.only.headers

    def test_an_empty_declaration_is_not_a_declaration(self, recorder):
        """`{}` resolves to undeclared server-side, so a header carrying it
        says nothing. Pinned on both clients because the two languages disagree
        about `{}`'s truthiness and a generated pair should not (M-1)."""
        rec = recorder()
        client = Darkmem(context={})

        asyncio.run(client.search("q"))

        assert CONTEXT_HEADER not in rec.only.headers

    def test_a_declaration_rides_the_search_door(self, recorder):
        rec = recorder()
        client = Darkmem()

        client.declare_context({"env": "prod"})
        asyncio.run(client.search("q"))

        assert json.loads(rec.only.headers[CONTEXT_HEADER]) == {"env": "prod"}

    def test_capture_never_carries_a_declaration(self, recorder):
        """The capture door serves no context on either rank — `MemoryCreate`
        has no `context` field and the route reads no header — so sending one
        would be a value discarded in silence, which is the defect this whole
        task exists to close. Generation refuses if a context-carrying verb
        ever binds such a door."""
        rec = recorder()
        client = Darkmem(context={"env": "prod"})

        asyncio.run(client.capture("one"))

        assert CONTEXT_HEADER not in rec.only.headers
        assert "context" not in rec.body()

    def test_a_per_call_context_rides_the_body_at_rank_one(self, recorder):
        """Doc 12 §5's two forms used as two forms: the argument is rank 1 in
        the body, the declaration is rank 2 in the header, and the *server*
        decides between them. The SDK may send both."""
        rec = recorder()
        client = Darkmem(context={"env": "dev"})

        asyncio.run(client.search("q", context={"env": "prod"}))

        assert rec.body()["context"] == {"env": "prod"}
        assert json.loads(rec.only.headers[CONTEXT_HEADER]) == {"env": "dev"}

    def test_a_declaration_can_be_withdrawn(self, recorder):
        rec = recorder()
        client = Darkmem(context={"env": "prod"})

        client.declare_context(None)
        asyncio.run(client.search("undeclared again"))

        assert CONTEXT_HEADER not in rec.only.headers


class TestTransport:
    def test_the_token_becomes_a_bearer_header(self, recorder):
        rec = recorder()

        asyncio.run(Darkmem(token="jwt-value").capture("authenticated"))

        assert rec.only.headers["Authorization"] == "Bearer jwt-value"

    def test_no_token_sends_no_authorization_header(self, recorder):
        rec = recorder()

        asyncio.run(Darkmem().capture("anonymous"))

        assert "Authorization" not in rec.only.headers

    def test_a_trailing_slash_on_the_base_url_does_not_double(self, recorder):
        rec = recorder()

        asyncio.run(Darkmem(base_url="http://darkmem.test:8000/").capture("x"))

        assert str(rec.only.url) == "http://darkmem.test:8000" + CAPTURE_PATH

    def test_the_failure_carries_the_response_the_door_sent(self, recorder):
        """A 422 names the field it rejected, and a caller who cannot read it
        is left guessing. `raise_for_status` hands over the whole response;
        the TypeScript client puts the body in the message for the same
        reason."""
        recorder({"detail": [{"loc": ["body", "limit"], "msg": "too large"}]}, status=422)

        with pytest.raises(httpx.HTTPStatusError) as raised:
            asyncio.run(Darkmem().search("q", limit=9999))

        assert "too large" in raised.value.response.text

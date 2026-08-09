"""T3.14 — the three verbs' behaviour on the wire (doc 15 §6).

The client builds its own ``httpx.AsyncClient``, so the transport is swapped by
patching the module's ``httpx`` binding. Kept in the test rather than added as
a constructor argument: an injectable-transport parameter is client-platform
surface, and doc 15 §6's whole stance is that this SDK is not one.

Tests are synchronous and drive the coroutine with ``asyncio.run`` so the suite
needs no pytest plugin beyond pytest itself — ``cd sdks/python && python -m
pytest -q`` is the task's Verify and it should hold on a bare interpreter.
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

    def body(self) -> dict:
        return json.loads(self.only.content)


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
        rec = recorder({"schema_version": 1, "id": "abc"})
        client = Darkmem(base_url="http://darkmem.test:8000")

        ack = asyncio.run(client.capture("the tab is on live data"))

        assert str(rec.only.url) == "http://darkmem.test:8000" + CAPTURE_PATH
        assert rec.body()["content"] == "the tab is on live data"
        assert ack == {"schema_version": 1, "id": "abc"}

    def test_the_constructor_project_is_the_default_and_the_argument_wins(
        self, recorder
    ):
        rec = recorder()
        client = Darkmem(project="darkmem")

        asyncio.run(client.capture("one"))
        assert rec.requests[0] and json.loads(rec.requests[0].content)["project"] == "darkmem"

        asyncio.run(client.capture("two", project="other"))
        assert json.loads(rec.requests[1].content)["project"] == "other"

    def test_an_omitted_argument_is_absent_from_the_wire(self, recorder):
        """Never sent as null. The contract's `MemoryCreate` would accept a
        null `source`, but `KnowledgeSearchRequest.limit` is a non-nullable
        int with a default — one filter, applied on both doors, keeps an
        argument the caller never passed from becoming a 422."""
        rec = recorder()

        asyncio.run(Darkmem().capture("content only"))

        assert set(rec.body()) == {"content"}

    def test_a_failure_status_raises(self, recorder):
        recorder({"detail": "nope"}, status=422)

        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(Darkmem().capture("rejected"))


class TestSearch:
    def test_it_posts_the_query_to_the_composed_read(self, recorder):
        rec = recorder({"rows": None, "sections": {}, "envelope": {"fused": False}})
        client = Darkmem()

        result = asyncio.run(client.search("what replaced redis"))

        assert str(rec.only.url).endswith(SEARCH_PATH)
        assert rec.body() == {"query": "what replaced redis"}
        assert result["envelope"]["fused"] is False

    def test_fused_maps_to_the_contract_field_name(self, recorder):
        """The SDK argument is doc 15 §6's `fused?`; the wire field is doc 07
        §5's `fuse`. The generator pins the wire name, so a rename on either
        side is caught there rather than here — this only fixes the mapping."""
        rec = recorder({"rows": [], "sections": None, "envelope": {"fused": True}})

        asyncio.run(Darkmem().search("q", fused=True, limit=5))

        assert rec.body() == {"query": "q", "fuse": True, "limit": 5}

    def test_fused_false_is_sent_rather_than_dropped(self, recorder):
        """`False` is a value, not an omission. Filtering on falsiness instead
        of on `None` would make an explicit `fused=False` indistinguishable
        from silence — harmless while the contract default agrees, and a
        silent behaviour change the day it does not."""
        rec = recorder({"rows": None, "sections": {}, "envelope": {"fused": False}})

        asyncio.run(Darkmem().search("q", fused=False))

        assert rec.body() == {"query": "q", "fuse": False}


class TestDeclaredContext:
    def test_no_context_sends_no_header(self, recorder):
        rec = recorder()

        asyncio.run(Darkmem().capture("undeclared"))

        assert CONTEXT_HEADER not in rec.only.headers

    def test_a_declaration_rides_every_later_call(self, recorder):
        rec = recorder()
        client = Darkmem()

        client.declare_context({"env": "prod"})
        asyncio.run(client.capture("one"))
        asyncio.run(client.search("two"))

        for request in rec.requests:
            assert json.loads(request.headers[CONTEXT_HEADER]) == {"env": "prod"}

    def test_a_per_call_context_wins_over_the_declaration(self, recorder):
        rec = recorder()
        client = Darkmem(context={"env": "dev"})

        asyncio.run(client.capture("one", context={"env": "prod"}))

        assert json.loads(rec.only.headers[CONTEXT_HEADER]) == {"env": "prod"}

    def test_only_one_context_is_ever_sent(self, recorder):
        """The header is the SDK's single carrier: no body field named
        `context`, `applies_when` or anything else. An earlier draft of the
        generated client posted `applies_when` — a key no request schema in
        the contract has — so every declaration was dropped by the door with
        nothing said. The field-level guard in `generate.py` is what catches
        that; this pins the emitted shape from the client's side."""
        rec = recorder()
        client = Darkmem()
        client.declare_context({"env": "prod"})

        asyncio.run(client.search("q"))

        assert set(rec.body()) == {"query"}
        assert CONTEXT_HEADER in rec.only.headers

    def test_a_declaration_can_be_withdrawn(self, recorder):
        rec = recorder()
        client = Darkmem(context={"env": "prod"})

        client.declare_context(None)
        asyncio.run(client.capture("undeclared again"))

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

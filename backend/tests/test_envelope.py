"""The payload envelope and the two-door resolution chains (T1.42a).

Section 1 is the characterisation net: the literal wire key sets of every
surface this task touches, so a change to any of them is a visible diff here
rather than a discovery downstream. The remaining sections pin the envelope
itself, the `source` chain on both doors, and the absence of declared context.
"""
from __future__ import annotations

import json
import uuid

from sqlalchemy import select

from app.models.memory import Memory


def _tool_call(name: str, arguments: dict, request_id: int = 1) -> dict:
    return {
        "jsonrpc": "2.0", "id": request_id, "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


async def _post_tool(client, name: str, arguments: dict, headers: dict | None = None) -> dict:
    response = await client.post("/", json=_tool_call(name, arguments), headers=headers or {})
    assert response.status_code == 200, response.text
    body = response.json()
    assert not body["result"].get("isError"), body
    return json.loads(body["result"]["content"][0]["text"])


async def _stored(session, content: str) -> Memory:
    session.expire_all()
    return (
        await session.execute(select(Memory).where(Memory.content == content))
    ).scalar_one()


# --------------------------------------------------------------------------
# 1. Characterisation net — the literal wire shapes
# --------------------------------------------------------------------------

CAPTURE_ACK_KEYS = {"id", "status", "schema_version", "warnings"}


async def test_rest_capture_ack_shape(client, auth_headers):
    resp = await client.post(
        "/api/v1/memories", json={"content": "envelope ack probe"}, headers=auth_headers,
    )
    assert resp.status_code == 202
    assert set(resp.json()) == CAPTURE_ACK_KEYS


async def test_rest_batch_ack_shape(client, auth_headers):
    resp = await client.post(
        "/api/v1/memories/batch",
        json={"entries": [{"content": "envelope batch ack a"}, {"content": "envelope batch ack b"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 202
    body = resp.json()
    assert len(body) == 2
    assert all(set(row) == CAPTURE_ACK_KEYS for row in body)


async def test_rest_search_returns_a_bare_list(client, session, auth_headers):
    """Known asymmetry, recorded rather than fixed here.

    ``POST /memories/search`` has no slot for an envelope — the same
    structural reason T1.33 wired ``with_trace`` only onto the paginated
    route. Conforming the return type is T1.42b's, where the whole REST
    surface moves at once.
    """
    session.add(Memory(content="envelope search probe", source="api"))
    await session.flush()

    resp = await client.post(
        "/api/v1/memories/search", json={"limit": 5}, headers=auth_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_rest_paginated_shape_with_and_without_trace(client, session, auth_headers):
    session.add(Memory(content="envelope paginated probe", source="api"))
    await session.flush()

    plain = await client.post(
        "/api/v1/memories/search/paginated", json={"limit": 5}, headers=auth_headers,
    )
    assert set(plain.json()) == {"items", "total", "limit", "offset", "envelope"}
    # Deliberately null, not an empty envelope. The non-traced path drops rows
    # with `_matches_schema_v2_filters` without counting them, so an envelope
    # there would report `excluded: {}` — "nothing was dropped" — about a path
    # that never measured. An absent envelope says "not measured"; an empty one
    # would read as evidence (invariant 14). T1.33 structured the counting into
    # the with_trace path alone, and T1.42b conforms the route.
    assert plain.json()["envelope"] is None

    traced = await client.post(
        "/api/v1/memories/search/paginated",
        json={"limit": 5, "with_trace": True},
        headers=auth_headers,
    )
    assert set(traced.json()) == {"items", "total", "limit", "offset", "envelope"}
    assert set(traced.json()["envelope"]) == {
        "schema_version", "partial", "excluded", "page",
        "query", "channels", "reranked", "weights", "fused",
    }
    # F4: memory search offers no fuse/sectioned choice at all, so `fused`
    # must read as "no shape choice was on offer" (None) rather than the
    # `False` that would misdescribe an unrelated door as having served
    # the sectioned shape it never offered.
    assert traced.json()["envelope"]["fused"] is None


async def test_mcp_capture_ack_shape(mcp_http_client):
    row = await _post_tool(mcp_http_client, "memory_add", {"content": "mcp envelope ack probe"})
    assert set(row) == CAPTURE_ACK_KEYS


async def test_mcp_batch_ack_shape(mcp_http_client):
    rows = await _post_tool(mcp_http_client, "memory_batch_add", {
        "entries": [{"content": "mcp envelope batch a"}, {"content": "mcp envelope batch b"}],
    })
    assert len(rows) == 2
    assert all(set(row) == CAPTURE_ACK_KEYS for row in rows)


async def test_mcp_search_returns_a_bare_list(mcp_http_client, session):
    """MCP ``memory_search`` is a bare JSON list and stays one through T1.42a.

    Wrapping it in an envelope is a breaking change for every MCP consumer,
    and the boundary table assigns MCP surface conformance to T1.42c. Raised
    as an open question in this task's report rather than made here.
    """
    session.add(Memory(content="mcp envelope search probe", source="api"))
    await session.flush()

    rows = await _post_tool(mcp_http_client, "memory_search", {"limit": 5})
    assert isinstance(rows, list)


# --------------------------------------------------------------------------
# 2. One envelope: the base class and its drift guard
# --------------------------------------------------------------------------


def test_retrieval_envelope_extends_the_one_base():
    from app.schemas.envelope import ResponseEnvelope
    from app.schemas.retrieval_trace import RetrievalEnvelope

    assert issubclass(RetrievalEnvelope, ResponseEnvelope)
    # Inherited, never redeclared: one class owns these.
    own = set(RetrievalEnvelope.__annotations__)
    assert own.isdisjoint({"excluded", "partial", "page", "schema_version"})


def test_no_second_envelope_declares_the_shared_fields():
    """The mechanical form of "one envelope shape across every surface".

    Scoped to **data fields declared on the class itself**, for two reasons
    a naive walk gets wrong. Pydantic v2's ``model_fields`` includes
    inherited fields, so walking it flags every legitimate subclass. And a
    computed override — ``RetrievalEnvelope.partial`` deriving itself from
    its channels — is the opposite of drift, so only annotations count: an
    annotation is what turns ``partial`` back into something a constructor
    can assign.

    ``schema_version`` is deliberately not in this set: ``ErrorEnvelope`` and
    ``CaptureAck`` carry it by design, and the guard below pins that every
    payload carrying it agrees on the *value* instead.
    """
    from app.schemas import envelope as envelope_module
    from app.schemas.envelope import ResponseEnvelope, iter_schema_models

    owned = {"excluded", "partial", "page"}
    offenders = []
    for model in iter_schema_models():
        if model is ResponseEnvelope:
            continue
        clash = set(model.__dict__.get("__annotations__", {})) & owned
        if clash:
            offenders.append((model.__name__, sorted(clash)))
    assert not offenders, (
        f"a second model declares envelope-owned fields: {offenders}. "
        f"Extend {ResponseEnvelope.__name__} in "
        f"{envelope_module.__name__} instead of redeclaring them."
    )


def test_every_versioned_payload_agrees_on_the_version():
    from app.schemas.envelope import ENVELOPE_SCHEMA_VERSION, iter_schema_models

    wrong = {
        model.__name__: model.model_fields["schema_version"].default
        for model in iter_schema_models()
        if "schema_version" in model.__dict__.get("__annotations__", {})
        and model.model_fields["schema_version"].default != ENVELOPE_SCHEMA_VERSION
    }
    assert not wrong, f"schema_version drifted between payloads: {wrong}"


def test_partial_is_derived_from_channels_not_assigned():
    from app.schemas.envelope import ResponseEnvelope
    from app.schemas.retrieval_trace import ChannelStatus, RetrievalEnvelope

    assert ResponseEnvelope().partial is False

    healthy = RetrievalEnvelope(
        query="q", channels={"semantic": ChannelStatus(ran=True), "keyword": ChannelStatus(ran=True)},
    )
    assert healthy.partial is False

    degraded = RetrievalEnvelope(
        query="q",
        channels={
            "semantic": ChannelStatus(ran=True, failed=True),
            "keyword": ChannelStatus(ran=True),
        },
    )
    assert degraded.partial is True
    # A constructor cannot contradict the channels: `partial` is computed, so
    # the keyword is ignored rather than believed.
    assert RetrievalEnvelope(
        query="q", partial=False,
        channels={"semantic": ChannelStatus(ran=True, failed=True)},
    ).partial is True
    assert degraded.model_dump()["partial"] is True


async def test_a_failed_channel_is_visibly_partial_on_the_wire(client, auth_headers, monkeypatch):
    """A degraded result must not render as a complete one (invariant 14).

    The derivation itself is pinned above; this proves the computed field
    survives the route's serialisation, which is where a plain ``@property``
    would silently drop off the wire.
    """
    from app.schemas.envelope import PageInfo
    from app.schemas.retrieval_trace import ChannelStatus, RetrievalEnvelope
    from app.services.memory import MemoryService

    async def _degraded_page(self, params, headers=None):
        return {
            "items": [], "total": 0, "limit": params.limit, "offset": params.offset,
            "envelope": RetrievalEnvelope(
                query=params.query or "",
                channels={
                    "semantic": ChannelStatus(ran=True, failed=True),
                    "keyword": ChannelStatus(ran=True),
                },
                page=PageInfo.build(limit=params.limit, offset=params.offset, total=0),
            ),
        }

    monkeypatch.setattr(MemoryService, "_search_memories_paginated_traced", _degraded_page)

    resp = await client.post(
        "/api/v1/memories/search/paginated",
        json={"query": "partial wire probe", "limit": 5, "with_trace": True},
        headers=auth_headers,
    )
    assert resp.json()["envelope"]["partial"] is True


# --------------------------------------------------------------------------
# 3. `page` agrees with the deprecated top-level trio
# --------------------------------------------------------------------------


async def test_page_agrees_with_the_top_level_trio(client, session, auth_headers):
    for i in range(5):
        session.add(Memory(content=f"page agreement probe {i}", source="page-probe"))
    await session.flush()

    resp = await client.post(
        "/api/v1/memories/search/paginated",
        json={"source": "page-probe", "limit": 2, "offset": 0, "with_trace": True},
        headers=auth_headers,
    )
    body = resp.json()
    page = body["envelope"]["page"]
    assert page["limit"] == body["limit"]
    assert page["offset"] == body["offset"]
    assert page["total"] == body["total"]
    assert page["next_offset"] == 2

    last = await client.post(
        "/api/v1/memories/search/paginated",
        json={"source": "page-probe", "limit": 50, "offset": 0, "with_trace": True},
        headers=auth_headers,
    )
    assert last.json()["envelope"]["page"]["next_offset"] is None


# --------------------------------------------------------------------------
# 4. The error envelope
# --------------------------------------------------------------------------


async def test_http_error_carries_the_error_envelope(client, auth_headers):
    resp = await client.get(f"/api/v1/memories/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["message"] == "Memory not found"
    # `detail` stays a string on every shape: frontend/src/lib/api.ts
    # interpolates it directly, and T1.42b owns retiring the mirror.
    assert body["detail"] == "Memory not found"
    assert body["schema_version"] == 1


async def test_validation_error_detail_is_a_string_not_a_list(client, auth_headers):
    resp = await client.post(
        "/api/v1/memories", json={"content": ""}, headers=auth_headers,
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "validation_error"
    assert isinstance(body["detail"], str)
    assert isinstance(body["error"]["details"], list)


async def test_a_validation_error_echoing_a_non_finite_number_still_renders():
    """A 422 echoes each error's `input`; JSONResponse refuses NaN and infinity,
    so an unsanitised echo turns the refusal into a 500."""
    from fastapi.exceptions import RequestValidationError

    from app.main import _validation_exception_handler

    exc = RequestValidationError([{
        "type": "value_error",
        "loc": ("body", "properties"),
        "msg": "Value error, not finite",
        "input": {"p": float("nan"), "q": [float("inf"), {"r": float("-inf")}], "s": 1.5},
    }])
    response = await _validation_exception_handler(None, exc)
    assert response.status_code == 422
    echoed = json.loads(response.body)["error"]["details"][0]["input"]
    assert echoed == {"p": "nan", "q": ["inf", {"r": "-inf"}], "s": 1.5}


async def test_unhandled_exception_returns_the_envelope_without_a_traceback(client, auth_headers, monkeypatch):
    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.services.memory import MemoryService

    async def _boom(self, memory_id):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(MemoryService, "get_memory", _boom)

    # Starlette's ServerErrorMiddleware sends the handler's response and then
    # re-raises, so the default test transport surfaces the exception instead
    # of the response. A real server sends what this client reads.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as raw:
        resp = await raw.get(f"/api/v1/memories/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "internal_error"
    assert "secret internal detail" not in json.dumps(body)
    assert "Traceback" not in json.dumps(body)
    assert isinstance(body["detail"], str)


async def test_mcp_caller_error_still_raises(mcp_http_client):
    """Doc 12 §3: a caller error raises; only recoverable unavailability
    returns the typed degradation shape. A not-found id is a caller error and
    must never be dressed up as a degradation."""
    response = await mcp_http_client.post(
        "/", json=_tool_call("memory_get", {"memory_id": str(uuid.uuid4())}),
    )
    body = response.json()
    assert body["result"].get("isError") is True


async def test_error_vocabularies_agree_across_the_two_doors():
    """The doors name the same condition with the same word.

    Where a ``code`` lives differs, and the plan under-specified this. On
    REST it is ``ErrorEnvelope.error.code``, keyed off the HTTP status. MCP
    has no status line: a **caller error** raises and surfaces as a JSON-RPC
    tool error with ``isError`` set (pinned separately above), and a
    **recoverable unavailability** returns the typed degradation shape whose
    ``status`` field is the vocabulary slot. So the assertable cross-door
    property is not one shared field name — it is that the same condition
    gets the same word, and that the caller-error/degradation split is the
    same on both doors.
    """
    from app.main import _HTTP_ERROR_CODES
    from app.api.mcp.server import _degraded

    degraded = _degraded("embedder not configured")
    assert degraded["status"] == _HTTP_ERROR_CODES[503] == "unavailable"
    assert degraded["schema_version"] == 1
    # An internal failure is never a caller-facing code, on either door.
    assert "internal_error" not in _HTTP_ERROR_CODES.values()
    assert all(code.islower() and " " not in code for code in _HTTP_ERROR_CODES.values())


async def test_mcp_degradation_shape_is_versioned(session, monkeypatch):
    import app.api.mcp.server as mcp_module
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_module, "async_session_factory", lambda: _fake_ctx())
    monkeypatch.setattr(mcp_module, "_pipeline", None)

    payload = json.loads(await mcp_module.code_search("anything"))
    assert payload["status"] == "unavailable"
    assert payload["schema_version"] == 1
    assert payload["results"] == []


# --------------------------------------------------------------------------
# 5. The `source` chain, on both doors
# --------------------------------------------------------------------------


def test_the_resolver_is_door_agnostic():
    """The same ladder, driven by an MCP ctx or a bare headers mapping."""
    from types import SimpleNamespace

    from starlette.datastructures import Headers

    from app.api.mcp.client_identity import resolve_client_source, resolve_source_agent

    raw = {"x-darkmem-client": "Kiro IDE!", "user-agent": "claude-code/2.0"}
    ctx = SimpleNamespace(request_context=SimpleNamespace(
        request=SimpleNamespace(headers=Headers(raw)),
    ))

    assert resolve_client_source(None, ctx) == resolve_client_source(None, headers=raw) == "kiroide"
    assert resolve_source_agent(None, ctx) == resolve_source_agent(None, headers=raw)

    ua_only = {"user-agent": "claude-code/2.1.172 (cli)"}
    assert resolve_client_source(None, headers=ua_only) == "claude-code"
    # A plain dict is case-sensitive where Starlette's Headers is not.
    assert resolve_client_source(None, headers={"X-Darkmem-Client": "codex"}) == "codex"


def test_the_sentinel_is_per_door():
    from app.api.mcp.client_identity import resolve_client_source

    headers = {"x-darkmem-client": "dashboard"}
    # REST door: its own fallback literal reads as unspecified, a foreign one
    # as a deliberate override.
    assert resolve_client_source("api", headers=headers, fallback="api") == "dashboard"
    assert resolve_client_source("mcp", headers=headers, fallback="api") == "mcp"
    # MCP door: exactly mirrored.
    assert resolve_client_source("mcp", headers=headers, fallback="mcp") == "dashboard"
    assert resolve_client_source("api", headers=headers, fallback="mcp") == "api"
    # And the terminal fallback follows the door.
    assert resolve_client_source(None, headers={}, fallback="api") == "api"
    assert resolve_client_source(None, headers={}, fallback="mcp") == "mcp"


def test_memory_create_source_has_no_default():
    """Done-when box 3, recorded as *satisfied by construction*.

    The box asks for a test that fails if `source` resolution ran after
    validation. That failure mode existed because ``MemoryCreate.source``
    stamped ``"api"`` during validation, erasing the distinction between a
    caller who omitted `source` and one who sent the door's fallback literal.
    Deleting the default removes the erasure at its root — after which pre-
    and post-validation resolution are **observationally equivalent** for
    every input class, and the mutation the box implies passes rather than
    fails. Writing a test that appeared to discriminate would have meant
    either inverting the shipped sentinel or weakening the criterion.

    So this pins the property the box actually protects: the erasure is no
    longer representable. Re-adding a default to ``MemoryCreate.source``
    fails here, by name.

    The raw-dict discipline in ``resolve_entry_identity`` remains the
    contract regardless, for two reasons independent of the default: the MCP
    tool signature is ``entries: list[dict]``, so there is no model to
    interrogate before ``MemoryBatchCreate`` builds one; and the raw dict is
    what the caller actually sent, where a validated model is what the schema
    decided it meant — a later ``default_factory`` or model validator would
    silently reintroduce the erasure behind a post-hoc reader.
    """
    from app.schemas.memory import MemoryCreate

    field = MemoryCreate.model_fields["source"]
    assert field.default is None, (
        "MemoryCreate.source grew a default again. A default is stamped during "
        "validation, which erases the absent-versus-explicit distinction the "
        "per-door sentinel reads — the exact erasure T1.42a removed at the root."
    )
    assert field.default_factory is None
    assert MemoryCreate(content="x").source is None


async def test_rest_single_door_resolves_the_full_ladder(client, session, auth_headers):
    cases = [
        ("rest explicit body source", {"source": "my-orchestrator"},
         {"X-Darkmem-Client": "dashboard"}, "my-orchestrator"),
        ("rest header beats ua", {},
         {"X-Darkmem-Client": "Dashboard!", "User-Agent": "claude-code/1.2"}, "dashboard"),
        ("rest claude code ua", {}, {"User-Agent": "claude-code/1.2"}, "claude-code"),
        ("rest generic ua falls back", {}, {"User-Agent": "python-httpx/0.27"}, "api"),
        # The sentinel: a caller copying the door's own default must not mask
        # detection.
        ("rest explicit api is unspecified", {"source": "api"},
         {"X-Darkmem-Client": "dashboard"}, "dashboard"),
    ]
    for content, extra, headers, expected in cases:
        resp = await client.post(
            "/api/v1/memories?wait_process=true", json={"content": content, **extra},
            headers={**auth_headers, **headers},
        )
        assert resp.status_code in (201, 202), resp.text
        assert (await _stored(session, content)).source == expected, content


async def test_rest_door_origin_key_follows_the_resolved_source(client, session, auth_headers):
    """The recorded behaviour change: REST `origin_key` now reflects the
    resolved client, not the literal body default.

    ``resolve_origin_key`` itself is untouched — its *input* was wrong. Before
    this, every REST fallback key read ``unknown:api:<project>`` no matter
    which client sent the request, so one tool's captures merged with every
    other unattributed HTTP capture in the same project.
    """
    await client.post(
        "/api/v1/memories?wait_process=true",
        json={"content": "rest origin follows source", "project": "ok-proj"},
        headers={**auth_headers, "X-Darkmem-Client": "dashboard"},
    )
    row = await _stored(session, "rest origin follows source")
    assert row.origin_key == "unknown:dashboard:ok-proj"
    assert "None" not in row.origin_key


async def test_rest_batch_resolves_per_entry_from_the_raw_dicts(client, session, auth_headers):
    resp = await client.post(
        "/api/v1/memories/batch?wait_process=true",
        json={"entries": [
            {"content": "rest batch omitted"},
            {"content": "rest batch explicit api", "source": "api"},
            {"content": "rest batch explicit mcp", "source": "mcp", "source_agent": "eval-r3"},
        ]},
        headers={**auth_headers, "X-Darkmem-Client": "dashboard"},
    )
    assert resp.status_code in (201, 202), resp.text
    assert (await _stored(session, "rest batch omitted")).source == "dashboard"
    # The REST door's own fallback literal reads as unspecified...
    assert (await _stored(session, "rest batch explicit api")).source == "dashboard"
    # ...while a foreign literal is a deliberate override.
    explicit = await _stored(session, "rest batch explicit mcp")
    assert explicit.source == "mcp"
    assert explicit.source_agent == "eval-r3"


async def test_a_hundred_entry_batch_is_one_origin(client, session, auth_headers):
    """doc 05 §2.1: a batch is the easiest way to counterfeit independence."""
    resp = await client.post(
        "/api/v1/memories/batch",
        json={"entries": [{"content": f"one origin batch {i}", "project": "one-origin"}
                          for i in range(100)]},
        headers=auth_headers,
    )
    assert resp.status_code == 202, resp.text

    rows = (await session.execute(
        select(Memory).where(Memory.project == "one-origin")
    )).scalars().all()
    assert len(rows) == 0  # buffered, not yet flushed

    from app.models.memory import MemoryBuffer

    buffered = (await session.execute(
        select(MemoryBuffer).where(MemoryBuffer.project == "one-origin")
    )).scalars().all()
    assert len(buffered) == 100
    assert len({row.metadata_["origin_key"] for row in buffered}) == 1


async def test_a_malformed_batch_still_answers_with_the_error_envelope(client, auth_headers):
    """Hand-reading the body must not turn a 422 into a 500."""
    for payload in ({"entries": [{"tags": ["x"]}]}, {"entries": []}, {"entries": "nope"}):
        resp = await client.post("/api/v1/memories/batch", json=payload, headers=auth_headers)
        assert resp.status_code == 422, (payload, resp.text)
        assert isinstance(resp.json()["detail"], str)

    # Non-dict entries and non-string source values reach validation untouched.
    resp = await client.post(
        "/api/v1/memories/batch",
        json={"entries": ["not a dict"]}, headers=auth_headers,
    )
    assert resp.status_code == 422
    resp = await client.post(
        "/api/v1/memories/batch",
        json={"entries": [{"content": "bad source type", "source": 7}]}, headers=auth_headers,
    )
    assert resp.status_code == 422


def test_origin_key_resolution_is_untouched_and_deterministic():
    """T1.11's resolver is edited by nothing here, re-asserted at the moment
    its neighbour changes. A per-request random would counterfeit
    independence and make every E2 corroboration count a fiction (doc 05
    §12)."""
    import inspect

    from app.api.mcp.client_identity import resolve_origin_key

    signature = inspect.signature(resolve_origin_key)
    assert list(signature.parameters) == ["explicit_origin", "ctx", "source", "project"]
    assert signature.parameters["source"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["project"].kind is inspect.Parameter.KEYWORD_ONLY

    first = resolve_origin_key(None, None, source="dashboard", project="p")
    second = resolve_origin_key(None, None, source="dashboard", project="p")
    assert first == second == "unknown:dashboard:p"


# --------------------------------------------------------------------------
# 6. No declared context
# --------------------------------------------------------------------------


async def test_the_search_door_takes_and_echoes_no_declared_context(client, session, auth_headers):
    """Declared context is gone from the memory search door: no request
    field, no header, no envelope echo and nothing in the contract."""
    from app.main import app
    from app.schemas.memory import MemorySearchRequest

    assert "context" not in MemorySearchRequest.model_fields

    session.add(Memory(content="no declared context probe", source="api", project="ctx-gone"))
    await session.flush()
    resp = await client.post(
        "/api/v1/memories/search/paginated",
        json={"project": "ctx-gone", "limit": 5, "with_trace": True},
        headers={**auth_headers, "X-Darkmem-Context": json.dumps({"env": "staging"})},
    )
    assert resp.status_code == 200
    assert "context" not in resp.json()["envelope"]

    document = app.openapi()
    assert "ContextEcho" not in document["components"]["schemas"]
    parameters = [
        parameter["name"].lower()
        for path in document["paths"].values()
        for operation in path.values()
        if isinstance(operation, dict)
        for parameter in operation.get("parameters", [])
    ]
    assert "x-darkmem-context" not in parameters
    assert "x-darkmem-context" not in json.dumps(document).lower()


# --------------------------------------------------------------------------
# 7. Two-door identity audit (envelope half; the row half landed in 764f31b)
# --------------------------------------------------------------------------


async def test_the_two_doors_ack_a_capture_identically(client, auth_headers, mcp_http_client):
    rest = await client.post(
        "/api/v1/memories", json={"content": "two door ack rest"}, headers=auth_headers,
    )
    mcp = await _post_tool(mcp_http_client, "memory_add", {"content": "two door ack mcp"})
    assert set(rest.json()) == set(mcp)

    rest_batch = await client.post(
        "/api/v1/memories/batch",
        json={"entries": [{"content": "two door batch rest"}]}, headers=auth_headers,
    )
    mcp_batch = await _post_tool(
        mcp_http_client, "memory_batch_add", {"entries": [{"content": "two door batch mcp"}]},
    )
    assert set(rest_batch.json()[0]) == set(mcp_batch[0])


async def test_the_two_doors_return_the_same_memory_row_keys(client, session, auth_headers, mcp_http_client):
    from app.schemas.memory import MemoryResponse

    memory = Memory(content="two door row probe", source="api", metadata_={})
    session.add(memory)
    await session.flush()

    rest = await client.get(f"/api/v1/memories/{memory.id}", headers=auth_headers)
    mcp = await _post_tool(mcp_http_client, "memory_get", {"memory_id": str(memory.id)})

    # Keys, not values: a UUID is a string on the MCP door and a UUID on the
    # REST door before serialisation, which is invariant 9's normalisation
    # boundary and is correct.
    assert set(rest.json()) == set(mcp) == set(MemoryResponse.model_fields)


async def test_the_ack_wire_shape_the_frontend_must_bind_to(client, auth_headers):
    """T1.58's target type, fixed here and bound there.

    T1.14 flipped ``POST /memories`` to a buffered 202 while
    ``use-memory-api.ts`` still types the call ``apiFetch<Memory>``. That
    defect is masked only by demo mode defaulting on, and T1.58 removes the
    mask. The backend-only lane records the shape; it must not reach into
    ``frontend/``.
    """
    from app.schemas.memory import CaptureAck

    accepted = await client.post(
        "/api/v1/memories", json={"content": "ack target shape"}, headers=auth_headers,
    )
    assert accepted.status_code == 202
    assert set(accepted.json()) == set(CaptureAck.model_fields)
    assert accepted.json()["status"] == "accepted"

    # `wait_process=true` still returns the settled memory, not the ack, so
    # the frontend's union is CaptureAck | CapturedMemoryResponse keyed on the
    # status code, never one or the other alone.
    from app.schemas.memory import CapturedMemoryResponse

    settled = await client.post(
        "/api/v1/memories?wait_process=true",
        json={"content": "ack settled shape"}, headers=auth_headers,
    )
    if settled.status_code == 201:
        assert set(settled.json()) == set(CapturedMemoryResponse.model_fields)

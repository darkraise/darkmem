import ast
import pathlib

import pytest
from contextlib import asynccontextmanager

import app.api.mcp.server as mcp_module
from app.api.mcp.server import code_search, mcp
from app.services.embedder_registry import embedder_registry

SERVER_PATH = pathlib.Path(__file__).resolve().parents[1] / "app" / "api" / "mcp" / "server.py"

# The roster this server is expected to serve, pinned by name.
#
# Not a count, and not a source-vs-runtime comparison. The decorator is both
# what an AST scan reads and what registers the tool, so removing one drops
# both sides together and an equality check between them stays true — it
# cannot see a loss at all. A count cannot tell a rename from a replacement.
# Only a pinned roster catches every case, and it makes adding or removing a
# tool a deliberate one-line diff here rather than a silent drift.
EXPECTED_TOOLS: frozenset[str] = frozenset({
    "article_get",
    # Increment 8's block verbs, capture-scoped.
    "block_delete",
    "block_insert",
    "block_move",
    "block_update",
    "checkpoint_latest",
    "checkpoint_save",
    "code_blast_radius",
    "code_changes",
    "code_communities",
    "code_context",
    "code_dependencies",
    "code_file_symbols",
    "code_processes",
    "code_reindex",
    "code_rename",
    "code_search",
    "code_symbol",
    "document_delete",
    # Increment 2's subtree delete, the second tool ever held at admin.
    "document_delete_subtree",
    "document_get",
    "document_outline",
    "document_put",
    "document_search",
    "document_update",
    "fact_get",
    "knowledge_search",
    "list_repos",
    "memory_add",
    "memory_batch_add",
    "memory_delete",
    "memory_find_duplicates",
    "memory_get",
    "memory_overview",
    "memory_reason",
    "memory_search",
    "memory_stats",
    "memory_tags",
    "memory_update",
    "research_run",
})


def _declared_tool_names() -> set[str]:
    """Every tool name server.py declares, as the SDK will register it.

    Honours an explicit ``@mcp.tool(name="...")`` override: the AST sees the
    Python function name while the registry reports the resolved tool name,
    and the two diverge exactly when that keyword is used.
    """
    tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if not (isinstance(target, ast.Attribute) and target.attr == "tool"):
                continue
            override = None
            if isinstance(dec, ast.Call):
                for kw in dec.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                        override = kw.value.value
            names.add(override or node.name)
    return names


async def test_mcp_tools_registered():
    declared = _declared_tool_names()
    registered = {t.name for t in await mcp.list_tools()}

    assert declared == EXPECTED_TOOLS, (
        "the declared roster moved; if that is intended, update EXPECTED_TOOLS "
        f"deliberately. missing={sorted(EXPECTED_TOOLS - declared)} "
        f"unexpected={sorted(declared - EXPECTED_TOOLS)}"
    )
    assert registered == EXPECTED_TOOLS, (
        "the live registry does not match the pinned roster. "
        f"missing={sorted(EXPECTED_TOOLS - registered)} "
        f"unexpected={sorted(registered - EXPECTED_TOOLS)}"
    )


async def test_code_search_clamps_limit(session, monkeypatch):
    """code_search must clamp `limit` to [1, _MAX_LIMIT] before it reaches the
    shared query service, like every other limit-bearing tool. An unclamped
    negative value raises a Postgres error; a huge value defeats the result-set
    cap.

    The assertion sits on the tool-to-service boundary rather than on the
    vector repository, because the clamp is the tool's and the service is free
    to fan the bound out across its own channels (it asks each arm for
    ``limit * 2`` before fusing).
    """
    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_module, "async_session_factory", lambda: _fake_ctx())

    class _FakeLLM:
        async def embed(self, _query):
            return ([0.1, 0.2], "fp-test")

    class _FakePipeline:
        llm = _FakeLLM()

    monkeypatch.setattr(mcp_module, "_pipeline", _FakePipeline())

    captured = {}
    from app.services import code_query as code_query_mod

    async def _fake_search(self, query, limit=20, repo_id=None, language=None):
        captured["limit"] = limit
        return []

    monkeypatch.setattr(code_query_mod.CodeQueryService, "search_code", _fake_search)

    await code_search("hello", limit=-5)
    assert captured["limit"] == 1

    await code_search("hello", limit=10_000)
    assert captured["limit"] == mcp_module._MAX_LIMIT


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
    return body


async def _get_memory(session, content: str) -> Memory:
    result = await session.execute(select(Memory).where(Memory.content == content))
    return result.scalar_one()


async def test_memory_add_source_from_header(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "header attribution probe", "wait_process": True},
                     headers={"X-Darkmem-Client": "Codex!"})
    memory = await _get_memory(session, "header attribution probe")
    assert memory.source == "codex"


async def test_memory_add_source_from_claude_code_user_agent(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "ua attribution probe", "wait_process": True},
                     headers={"User-Agent": "claude-code/2.1.172 (cli)"})
    memory = await _get_memory(session, "ua attribution probe")
    assert memory.source == "claude-code"
    assert memory.source_agent == "claude-code/2.1.172 (cli)"


async def test_memory_add_generic_ua_falls_back_to_mcp(mcp_http_client, session):
    # httpx's default python-httpx/<ver> UA must stay on the denylist: every
    # in-process test and raw-httpx harness rides on that entry.
    await _post_tool(mcp_http_client, "memory_add", {"content": "generic ua probe", "wait_process": True})
    memory = await _get_memory(session, "generic ua probe")
    assert memory.source == "mcp"
    assert memory.source_agent.startswith("python-httpx/")


async def test_memory_add_no_ua_leaves_source_agent_null(mcp_http_client, session):
    del mcp_http_client.headers["user-agent"]
    await _post_tool(mcp_http_client, "memory_add", {"content": "no ua probe", "wait_process": True})
    memory = await _get_memory(session, "no ua probe")
    assert memory.source == "mcp"
    assert memory.source_agent is None


async def test_memory_add_explicit_source_beats_header(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "explicit override probe", "source": "my-orchestrator", "wait_process": True},
                     headers={"X-Darkmem-Client": "codex"})
    memory = await _get_memory(session, "explicit override probe")
    assert memory.source == "my-orchestrator"


async def test_memory_update_tags_only_preserves_content(mcp_http_client, session):
    # Updating only tags must replace tags and leave content untouched. The MCP
    # wrapper used to pass content=None explicitly, defeating the service's
    # exclude_unset guard and clobbering the NOT NULL content column (which also
    # aborted before tags were applied).
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "update tags-only probe", "tags": ["keep/a"], "wait_process": True})
    mem = await _get_memory(session, "update tags-only probe")

    await _post_tool(mcp_http_client, "memory_update",
                     {"memory_id": str(mem.id), "tags": ["new/b"]})

    session.expire_all()
    updated = await _get_memory(session, "update tags-only probe")
    assert updated.content == "update tags-only probe"
    assert {t.name for t in updated.tags} == {"new/b"}


async def test_memory_update_type_only_preserves_content_and_tags(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "update type-only probe", "tags": ["keep/c"],
                      "memory_type": "fact", "wait_process": True})
    mem = await _get_memory(session, "update type-only probe")

    await _post_tool(mcp_http_client, "memory_update",
                     {"memory_id": str(mem.id), "memory_type": "decision"})

    session.expire_all()
    updated = await _get_memory(session, "update type-only probe")
    assert updated.content == "update type-only probe"
    assert updated.memory_type == "decision"
    assert {t.name for t in updated.tags} == {"keep/c"}


async def test_memory_batch_add_resolves_per_entry(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_batch_add", {
        "wait_process": True,
        "entries": [
            {"content": "batch omitted source"},
            {"content": "batch explicit api", "source": "api"},
            {"content": "batch explicit mcp", "source": "mcp", "source_agent": "eval-r3"},
        ],
    }, headers={"X-Darkmem-Client": "codex"})
    omitted = await _get_memory(session, "batch omitted source")
    assert omitted.source == "codex"
    assert omitted.source_agent.startswith("python-httpx/")
    assert (await _get_memory(session, "batch explicit api")).source == "api"
    explicit = await _get_memory(session, "batch explicit mcp")
    assert explicit.source == "codex"
    assert explicit.source_agent == "eval-r3"


import json
import uuid


def _tool_payload(body: dict) -> dict:
    return json.loads(body["result"]["content"][0]["text"])


async def test_memory_get_reports_supersession(mcp_http_client, session):
    """An MCP reader must be able to tell a superseded memory from a live one.

    Doc 07 §7 requires a superseded row to be labelled and reachable through
    its successor. The MCP row carried neither field, so an autonomous agent
    read a retired memory as current with no badge and no human in the loop.
    """
    replacement = Memory(
        id=uuid.uuid4(), content="mcp supersession replacement",
        source="test", metadata_={}, project="lane-f",
    )
    session.add(replacement)
    await session.flush()

    retired = Memory(
        id=uuid.uuid4(), content="mcp supersession probe", source="test",
        metadata_={}, project="lane-f", status="superseded",
        superseded_by=replacement.id, technologies=["postgres"],
    )
    session.add(retired)
    await session.flush()

    row = _tool_payload(
        await _post_tool(mcp_http_client, "memory_get", {"memory_id": str(retired.id)})
    )
    assert row["status"] == "superseded"
    assert row["superseded_by"] == str(replacement.id)
    assert row["project"] == "lane-f"
    assert row["technologies"] == ["postgres"]

    live = _tool_payload(
        await _post_tool(mcp_http_client, "memory_get", {"memory_id": str(replacement.id)})
    )
    assert live["status"] == "active"
    assert live["superseded_by"] is None


async def test_memory_get_reports_the_reverse_lineage_too(mcp_http_client, session):
    """T1.47: the MCP door must carry `predecessors`, not only `superseded_by`.

    `memory_get` and REST's `GET /memories/{id}` share one call site
    (`MemoryService.get_memory`), so this proves the field reaches MCP
    without `app/api/mcp/server.py` needing its own edit. The pair is
    produced by the real detector, not hand-set, so a future change to what
    `detect_supersessions` writes breaks this test rather than drifting
    silently past it.
    """
    from datetime import datetime, timedelta, timezone

    from app.services.supersession import detect_supersessions

    now = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    old = Memory(
        id=uuid.uuid4(), content="mcp lineage: promtail for logs",
        source="test", metadata_={}, project="lane-f",
        technologies=["promtail"], created_at=now - timedelta(days=1),
    )
    new = Memory(
        id=uuid.uuid4(), content="mcp lineage: switched to alloy",
        source="test", metadata_={}, project="lane-f",
        technologies=["alloy"], created_at=now,
    )
    session.add_all([old, new])
    await session.flush()

    flipped = await detect_supersessions(
        session,
        new_memory_id=new.id,
        new_memory_text=new.content,
        new_memory_created_at=new.created_at,
        project=new.project,
        new_relations=[{"type": "REPLACES", "source": "alloy", "target": "promtail"}],
        now=now,
    )
    assert flipped == [old.id]
    await session.flush()

    row = _tool_payload(
        await _post_tool(mcp_http_client, "memory_get", {"memory_id": str(new.id)})
    )
    assert len(row["predecessors"]) == 1
    assert row["predecessors"][0]["id"] == str(old.id)
    assert row["predecessors"][0]["content"] == "mcp lineage: promtail for logs"
    assert row["predecessors"][0]["status"] == "superseded"

    childless = _tool_payload(
        await _post_tool(mcp_http_client, "memory_get", {"memory_id": str(old.id)})
    )
    assert childless["predecessors"] == []


async def test_memory_search_rows_carry_the_lifecycle_label(mcp_http_client, session):
    memory = Memory(
        id=uuid.uuid4(), content="mcp search label probe", source="test",
        metadata_={}, project="lane-f",
    )
    session.add(memory)
    await session.flush()

    rows = _tool_payload(
        await _post_tool(mcp_http_client, "memory_search", {"query": "label probe"})
    )
    assert rows, "search returned nothing to inspect"
    for row in rows:
        assert row["status"] in {"active", "superseded", "deprecated"}
        assert "superseded_by" in row
        assert "project" in row


@pytest.mark.asyncio
async def test_block_verbs_answer_envelopes_rather_than_tool_errors(session, monkeypatch):
    """Review M-4: both refusals are outcomes a caller acts on, not crashes.

    An agent can machine-read an envelope and switch strategy; it cannot
    machine-read a traceback. Their REST twins are a 422 and a 409.

    The unconvertible half is a link-reference definition: markdown-it
    consumes it into `env`, minting no token and no block, so nothing can
    serialise it back and converting would leave every reference dangling.
    (Raw HTML stood here until 2026-09-07; it mints an `html` block now and
    converts.)
    """
    import json
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from app.api.mcp import server as mcp_server
    from app.services.document_door import put_document

    class Stub:
        def __init__(self):
            self.fingerprint = "test-fp-mcp-blocks|3"

        async def embed_batch_chunked(self, texts, chunk_size, concurrency):
            return ([[1.0, 0.0, 0.0] for _ in texts], self.fingerprint)

        async def embed(self, value):
            return [1.0, 0.0, 0.0], self.fingerprint

        def llm_fingerprint(self):
            return self.fingerprint

    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget("test-fp-mcp-blocks|3")
    llm = Stub()

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=llm))

    # A document the block model cannot represent refuses, structured.
    filed = await put_document(
        session, llm, project="p", uri="mcp/raw.md",
        content="see [the doc][ref]\n\n[ref]: https://example.test\n",
    )
    await session.commit()
    blocks = json.loads(await mcp_server.document_get(document_id=filed.document_id))
    reply = json.loads(
        await mcp_server.block_update(block_id=blocks[0]["block_id"], text="x")
    )
    assert reply["status"] == "not_convertible"

    # An unresolvable block refuses the same way.
    missing = json.loads(await mcp_server.block_update(
        block_id="00000000-0000-0000-0000-000000000000", text="x",
    ))
    assert missing["status"] == "unresolved"
    embedder_registry.forget("test-fp-mcp-blocks|3")


_HASH_FP = "test-fp-mcp-hash|3"


class _HashStub:
    """Embedder stand-in: the block verbs embed the block they touched."""

    def __init__(self):
        self.fingerprint = _HASH_FP

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([[1.0, 0.0, 0.0] for _ in texts], self.fingerprint)

    async def embed(self, value):
        return [1.0, 0.0, 0.0], self.fingerprint

    def llm_fingerprint(self):
        return self.fingerprint


def _patch_mcp(monkeypatch, session, llm):
    from types import SimpleNamespace

    from app.api.mcp import server as mcp_server

    embedder_registry.forget(_HASH_FP)

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=llm))


@pytest.mark.asyncio
async def test_document_get_answers_an_object_when_include_hash_is_set(
    session, monkeypatch,
):
    """A bare array has nowhere to carry a hash, so the flag boxes the reply
    the same way `include_content` already does, and neither flag leaves the
    array shape every existing caller parses untouched.
    """
    import json

    from app.api.mcp import server as mcp_server
    from app.services.document_door import put_document

    llm = _HashStub()
    _patch_mcp(monkeypatch, session, llm)
    filed = await put_document(
        session, llm, project="p", uri="mcp/hash.md",
        content="# Title\n\nA paragraph.\n",
    )
    await session.commit()

    bare = json.loads(await mcp_server.document_get(document_id=filed.document_id))
    assert isinstance(bare, list)

    boxed = json.loads(await mcp_server.document_get(
        document_id=filed.document_id, include_hash=True))
    assert set(boxed) == {"content_hash", "blocks"}
    assert boxed["blocks"] == bare
    assert boxed["content_hash"] == filed.content_hash

    both = json.loads(await mcp_server.document_get(
        document_id=filed.document_id, include_hash=True, include_content=True))
    assert set(both) == {"content", "content_hash", "blocks"}
    embedder_registry.forget(_HASH_FP)


@pytest.mark.parametrize("verb", ["update", "insert", "move", "delete"])
@pytest.mark.asyncio
async def test_a_stale_hash_answers_a_conflict_envelope(session, monkeypatch, verb):
    """A lost race is an outcome the caller acts on, not a crash: every block
    verb answers the same machine-readable refusal its REST twin answers 409
    for. One verb per case -- a refusal rolls the session back.
    """
    import json

    from app.api.mcp import server as mcp_server
    from app.services.document_door import put_document

    llm = _HashStub()
    _patch_mcp(monkeypatch, session, llm)
    filed = await put_document(
        session, llm, project="p", uri="mcp/hash.md",
        content="# Title\n\nA paragraph.\n",
    )
    await session.commit()
    blocks = json.loads(await mcp_server.document_get(document_id=filed.document_id))
    block_id = blocks[0]["block_id"]
    stale = "0" * 64

    if verb == "update":
        call = mcp_server.block_update(block_id=block_id, text="x", expected_hash=stale)
    elif verb == "insert":
        call = mcp_server.block_insert(
            document_id=filed.document_id, type="paragraph", text="x",
            expected_hash=stale,
        )
    elif verb == "move":
        call = mcp_server.block_move(block_id=block_id, expected_hash=stale)
    else:
        call = mcp_server.block_delete(block_id=block_id, expected_hash=stale)

    envelope = json.loads(await call)
    assert envelope["status"] == "hash_conflict"
    assert envelope["expected_hash"] == stale
    assert envelope["current_hash"] == filed.content_hash
    embedder_registry.forget(_HASH_FP)


@pytest.mark.asyncio
async def test_document_update_carries_both_shapes_as_modes(session, monkeypatch):
    """One tool, two modes: a single document's metadata, or a subtree rename.

    Spec §4.2 puts both shapes on one MCP tool where REST serves two routes,
    so the mode is dispatched on which address the caller named.
    """
    import json
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from app.api.mcp import server as mcp_server
    from app.services.document_door import put_document

    class Stub:
        def __init__(self):
            self.fingerprint = "test-fp-mcp-docupdate|3"

        async def embed_batch_chunked(self, texts, chunk_size, concurrency):
            return ([[1.0, 0.0, 0.0] for _ in texts], self.fingerprint)

        async def embed(self, value):
            return [1.0, 0.0, 0.0], self.fingerprint

        def llm_fingerprint(self):
            return self.fingerprint

    embedder_registry.forget("test-fp-mcp-docupdate|3")
    llm = Stub()

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=llm))

    filed = await put_document(
        session, llm, project="mcp-docupdate", uri="mcpnotes/a/one.md", content="# One\n",
    )
    for uri in ("mcpnotes/a/two.md", "mcpnotes/a/deep/three.md"):
        await put_document(session, llm, project="mcp-docupdate", uri=uri, content="# X\n")
    await session.commit()

    single = json.loads(await mcp_server.document_update(
        document_id=str(filed.document_id), title="New", pinned=True,
        tags=["topic/notes"],
    ))
    assert single["status"] == "ok"
    assert single["document_id"] == str(filed.document_id)

    subtree = json.loads(await mcp_server.document_update(
        project="mcp-docupdate", uri_prefix="mcpnotes/a", new_uri_prefix="mcpnotes/b",
    ))
    assert subtree["status"] == "ok"
    assert subtree["renamed"] == 3
    embedder_registry.forget("test-fp-mcp-docupdate|3")


def test_document_update_is_capture_scoped():
    """A key that can rename a document holds capture power, not read power."""
    from app.api.mcp.scopes import CAPTURE_TOOLS, READ_TOOLS

    assert "document_update" in CAPTURE_TOOLS
    assert "document_update" not in READ_TOOLS


@pytest.mark.asyncio
async def test_document_update_refuses_an_ambiguous_mode(session, monkeypatch):
    """Naming neither address, or both, is a refusal envelope, not a crash.

    The caller can machine-read an envelope and pick a mode; it cannot
    machine-read a traceback.
    """
    import json
    from contextlib import asynccontextmanager

    from app.api.mcp import server as mcp_server

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())

    neither = json.loads(await mcp_server.document_update(title="New"))
    assert neither["status"] == "invalid_mode"

    both = json.loads(await mcp_server.document_update(
        document_id="00000000-0000-0000-0000-000000000000",
        project="mcp-docupdate", uri_prefix="mcpnotes/a", new_uri_prefix="mcpnotes/b",
    ))
    assert both["status"] == "invalid_mode"

    incomplete = json.loads(await mcp_server.document_update(
        project="mcp-docupdate", uri_prefix="mcpnotes/a",
    ))
    assert incomplete["status"] == "invalid_mode"


@pytest.mark.asyncio
async def test_document_update_refusals_are_envelopes(session, monkeypatch):
    """An unresolvable target, a malformed id and an occupied path answer the
    same shapes the block verbs and the REST twin already use.

    The order is load-bearing: a refusal path rolls back the session, and the
    `session` fixture hands out a session bound to the test's own outer
    transaction, so a rollback ends that isolation boundary and anything
    written afterwards commits for real. Writing first keeps every leak
    inside this test's own rows.
    """
    import json
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from app.api.mcp import server as mcp_server
    from app.services.document_door import put_document

    class Stub:
        def __init__(self):
            self.fingerprint = "test-fp-mcp-docupdate2|3"

        async def embed_batch_chunked(self, texts, chunk_size, concurrency):
            return ([[1.0, 0.0, 0.0] for _ in texts], self.fingerprint)

        async def embed(self, value):
            return [1.0, 0.0, 0.0], self.fingerprint

        def llm_fingerprint(self):
            return self.fingerprint

    embedder_registry.forget("test-fp-mcp-docupdate2|3")
    llm = Stub()

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=llm))

    # Every write this test makes happens before the first refusal. A refusal
    # rolls back the session it was handed, and under the `session` fixture
    # that is the fixture's own connection -- see the ordering note in the
    # docstring.
    first = await put_document(
        session, llm, project="mcp-docupdate", uri="mcptaken/one.md", content="# One\n",
    )
    await put_document(
        session, llm, project="mcp-docupdate", uri="mcptaken/two.md", content="# Two\n",
    )
    await session.commit()

    conflict = json.loads(await mcp_server.document_update(
        document_id=str(first.document_id), uri="mcptaken/two.md",
    ))
    assert conflict["status"] == "uri_conflict"

    missing = json.loads(await mcp_server.document_update(
        document_id="00000000-0000-0000-0000-000000000000", title="New",
    ))
    assert missing["status"] == "unresolved"

    # A malformed id is the same refusal rather than a tool error: its REST
    # twin is a 422 on the path parameter.
    malformed = json.loads(await mcp_server.document_update(
        document_id="not-a-uuid", title="New",
    ))
    assert malformed["status"] == "unresolved"
    embedder_registry.forget("test-fp-mcp-docupdate2|3")


@pytest.mark.asyncio
async def test_document_update_bounds_tag_lengths_at_the_door(session, monkeypatch):
    """`get_or_create` validates nothing, so an over-long tag would reach the
    driver as a DataError with no savepoint under it -- a poisoned transaction
    rather than a refusal.

    An envelope rather than a tool error, because every other refusal on this
    tool is one; the shared validator raises `ValueError` because its first
    caller is a pydantic field validator.
    """
    import json
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from app.api.mcp import server as mcp_server

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=object()))

    long_name = json.loads(await mcp_server.document_update(
        document_id="00000000-0000-0000-0000-000000000000",
        tags=["x" * 400],
    ))
    assert long_name["status"] == "invalid_tags"

    # The category axis -- everything before the first `/` -- is the one the
    # REST route missed. A name inside its own bound can still derive a
    # category over the category column's.
    long_category = json.loads(await mcp_server.document_update(
        document_id="00000000-0000-0000-0000-000000000000",
        tags=["a" * 60 + "/x"],
    ))
    assert long_category["status"] == "invalid_tags"


@pytest.mark.asyncio
async def test_document_update_refuses_an_empty_uri(session, monkeypatch):
    """Its REST twin puts `min_length=1` on uri, so the empty string is a 422
    there before the handler runs."""
    import json
    from contextlib import asynccontextmanager

    from app.api.mcp import server as mcp_server

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())

    empty = json.loads(await mcp_server.document_update(
        document_id="00000000-0000-0000-0000-000000000000", uri="",
    ))
    assert empty["status"] == "invalid_mode"
    assert "uri" in empty["reason"]


@pytest.mark.asyncio
async def test_document_update_refuses_a_call_that_changes_nothing(session, monkeypatch):
    """Both shapes journal into an append-only table while moving nothing: a
    metadata call naming no field, and a rename onto the prefix it holds.

    Neither reaches a write, so no ordering note applies -- the refusals here
    precede any row this test could leak.
    """
    import json
    from contextlib import asynccontextmanager

    from app.api.mcp import server as mcp_server

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())

    no_fields = json.loads(await mcp_server.document_update(
        document_id="00000000-0000-0000-0000-000000000000",
    ))
    assert no_fields["status"] == "no_change"

    same_prefix = json.loads(await mcp_server.document_update(
        project="mcp-docupdate", uri_prefix="mcpnotes/a",
        new_uri_prefix="mcpnotes/a",
    ))
    assert same_prefix["status"] == "no_change"


@pytest.mark.asyncio
async def test_document_update_refuses_a_field_from_the_other_mode(session, monkeypatch):
    """A dropped key would answer `ok` for a call that moved nothing.

    The REST twin forbids extras, so naming `project` on a metadata edit is a
    422 there; here it is an `invalid_mode` envelope rather than silence.
    """
    import json
    from contextlib import asynccontextmanager

    from app.api.mcp import server as mcp_server

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())

    crossed = json.loads(await mcp_server.document_update(
        document_id="00000000-0000-0000-0000-000000000000",
        title="New", project="q",
    ))
    assert crossed["status"] == "invalid_mode"
    assert "project" in crossed["reason"]

    other_way = json.loads(await mcp_server.document_update(
        project="q", uri_prefix="a", new_uri_prefix="b", pinned=True,
    ))
    assert other_way["status"] == "invalid_mode"
    assert "pinned" in other_way["reason"]


def test_document_delete_subtree_is_admin_scoped():
    """A capture key can delete one note it can name. Erasing a subtree is
    repository-scale control, so it sits with code_reindex."""
    from app.api.mcp.scopes import ADMIN_TOOLS, CAPTURE_TOOLS, READ_TOOLS

    assert "document_delete_subtree" in ADMIN_TOOLS
    assert "document_delete_subtree" not in CAPTURE_TOOLS
    assert "document_delete_subtree" not in READ_TOOLS
    # The single-document verb keeps the scope it has.
    assert "document_delete" in CAPTURE_TOOLS


@pytest.mark.asyncio
async def test_document_delete_subtree_removes_the_tree(session, monkeypatch):
    """The tree goes, the sibling prefix stays, and the journal names the key.

    The identity half is asserted here rather than left to the service test:
    that test proves `delete_documents` forwards what it is handed, not that
    this door hands it anything. The event row is the only record of who
    erased a subtree, so a door that passed neither would leave an audit
    trail with no actor and every service-level test still green.
    """
    import json
    import uuid as uuid_mod
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from sqlalchemy import text

    from app.api.mcp import server as mcp_server
    from app.services.document_door import DOCUMENTS_DELETED_EVENT, put_document

    class Stub:
        def __init__(self):
            self.fingerprint = "test-fp-mcp-subtree|3"

        async def embed_batch_chunked(self, texts, chunk_size, concurrency):
            return ([[1.0, 0.0, 0.0] for _ in texts], self.fingerprint)

        async def embed(self, value):
            return [1.0, 0.0, 0.0], self.fingerprint

        def llm_fingerprint(self):
            return self.fingerprint

    embedder_registry.forget("test-fp-mcp-subtree|3")
    llm = Stub()

    @asynccontextmanager
    async def _ctx():
        yield session

    key_id = uuid_mod.uuid4()
    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=llm))
    monkeypatch.setattr(mcp_server, "current_key_name", lambda: "subtree-key")
    monkeypatch.setattr(mcp_server, "current_api_key_id", lambda: key_id)

    # Every write before the first refusal -- see the fixture note.
    gone = await put_document(session, llm, project="mcp-subtree",
                              uri="mcpgone/a.md", content="# A\n")
    await put_document(session, llm, project="mcp-subtree",
                       uri="mcpgone/deep/b.md", content="# B\n")
    await put_document(session, llm, project="mcp-subtree",
                       uri="mcpkept/c.md", content="# C\n")
    await session.commit()

    result = json.loads(await mcp_server.document_delete_subtree(
        project="mcp-subtree", uri_prefix="mcpgone",
    ))
    assert result["status"] == "ok"
    assert result["project"] == "mcp-subtree"
    assert result["deleted"] == 2

    survivors = set((await session.execute(
        text("SELECT uri FROM documents WHERE project = 'mcp-subtree'")
    )).scalars().all())
    assert survivors == {"mcpkept/c.md"}

    row = (await session.execute(
        text(
            "SELECT event_type, actor, CAST(api_key_id AS text) AS api_key_id "
            "FROM events WHERE object_id = CAST(:id AS uuid) "
            "ORDER BY created_at DESC, id DESC LIMIT 1"
        ),
        {"id": str(gone.document_id)},
    )).mappings().one()
    assert row["event_type"] == DOCUMENTS_DELETED_EVENT
    assert row["actor"] == "subtree-key"
    assert row["api_key_id"] == str(key_id)

    embedder_registry.forget("test-fp-mcp-subtree|3")


@pytest.mark.asyncio
async def test_document_delete_subtree_refuses_an_empty_prefix(session, monkeypatch):
    """Two refusals, and they are deliberately different shapes.

    An unnamed project is a mode error -- the call addresses nothing. An
    empty `uri_prefix` is the service's own `DocumentNothingToChange`, the
    same refusal the REST twin answers 422 for, so it reaches the service
    rather than being second-guessed at the door.
    """
    import json
    from contextlib import asynccontextmanager

    from app.api.mcp import server as mcp_server

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())

    refused = json.loads(await mcp_server.document_delete_subtree(
        project="mcp-subtree", uri_prefix="",
    ))
    assert refused["status"] == "no_change"

    unaddressed = json.loads(await mcp_server.document_delete_subtree(
        uri_prefix="mcpgone",
    ))
    assert unaddressed["status"] == "invalid_mode"


@pytest.mark.asyncio
async def test_document_delete_answers_an_envelope_for_a_missing_target(
    session, monkeypatch,
):
    """Its sibling document_update answers an envelope; these two disagreed."""
    import json
    from contextlib import asynccontextmanager

    from app.api.mcp import server as mcp_server

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())

    missing = json.loads(await mcp_server.document_delete(
        document_id="00000000-0000-0000-0000-000000000000",
    ))
    assert missing["status"] == "unresolved"

import ast
import pathlib

import pytest
from contextlib import asynccontextmanager

import app.api.mcp.server as mcp_module
from app.api.mcp.server import code_search, mcp

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
    "document_get",
    "document_outline",
    "document_put",
    "document_search",
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
        content="before\n\n<div>raw</div>\n\nafter\n",
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

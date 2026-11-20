"""The MCP tools spend the same service layer as their REST twins.

Invariant 17's payload half: a behaviour must never exist on one door and not
the other by accident. A tool that re-implements its twin's query does not
fail loudly -- it drifts, and the two doors quietly answer the same question
differently. Every guard here is written so that re-inlining the query makes
it fail.
"""
from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager

import pytest

import app.api.mcp.server as mcp_server
from app.models.code import CodeFile, CodeSymbol, Repository
from app.models.memory import Memory
from app.services.code_query import CodeQueryService, CodeSearchAnswer
from app.services.memory import MemoryService


@pytest.fixture
def mcp_session(session, monkeypatch):
    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _fake_ctx())
    return session


class _FakeLLM:
    async def embed(self, _query):
        return ([0.1, 0.2], "fp-test")


class _FakePipeline:
    llm = _FakeLLM()


# ---------------------------------------------------------------------------
# The memory family
# ---------------------------------------------------------------------------


async def test_memory_search_can_scope_to_a_project(mcp_session):
    """MCP callers can narrow a search to one project, as REST callers can.

    ``MemorySearchRequest.project`` has always existed and pushed down in SQL,
    but the MCP tool exposed no argument for it -- the same capability on two
    doors with only one able to reach it. The agent that cannot scope its own
    search is exactly the caller most likely to need to.
    """
    for project in ("proj-a", "proj-b"):
        mcp_session.add(Memory(
            id=uuid.uuid4(), content=f"project pushdown probe {project}",
            source="test", metadata_={}, project=project,
        ))
    await mcp_session.flush()

    scoped = json.loads(await mcp_server.memory_search(
        query="project pushdown probe", project="proj-a", limit=50,
    ))
    assert scoped, "scoped search returned nothing to inspect"
    assert {row["project"] for row in scoped} == {"proj-a"}

    wide = json.loads(await mcp_server.memory_search(
        query="project pushdown probe", limit=50,
    ))
    assert {"proj-a", "proj-b"} <= {row["project"] for row in wide}


async def test_memory_search_goes_through_the_shared_service(mcp_session, monkeypatch):
    calls: list = []
    real = MemoryService.search_memories

    async def _spy(self, params):
        calls.append(params)
        return await real(self, params)

    monkeypatch.setattr(MemoryService, "search_memories", _spy)

    await mcp_server.memory_search(query="anything", project="proj-a", limit=5)

    assert len(calls) == 1
    assert calls[0].project == "proj-a"
    assert calls[0].limit == 5


async def test_memory_search_returns_a_bare_list_by_design(mcp_session):
    """MCP ``memory_search`` answers a bare JSON array and keeps doing so.

    Recorded here in the two-door audit's own terms, so the parity audit
    inherits the reasoning instead of rediscovering it: this is a **stated
    asymmetry between routes that can report a resolution and routes that
    cannot**, not an asymmetry between doors. The REST twin's envelope can
    carry a ContextEcho and the excluded counts; a bare array has nowhere to
    put them, and giving it somewhere means changing the wire shape every
    existing MCP consumer already parses -- a breaking change, which doc 12
    section 3 says ships as a NEW tool name, never as a silent mutation of
    this one.
    """
    mcp_session.add(Memory(
        id=uuid.uuid4(), content="bare list probe", source="test",
        metadata_={}, project="default",
    ))
    await mcp_session.flush()

    payload = json.loads(await mcp_server.memory_search(query="bare list probe"))
    assert isinstance(payload, list)


# ---------------------------------------------------------------------------
# The code family
# ---------------------------------------------------------------------------


async def test_code_search_runs_the_rest_twins_composition(mcp_session, monkeypatch):
    """The tool must fuse through ``CodeQueryService``, not probe vectors alone.

    The tool used to embed the query and read the ANN partition directly, so
    an MCP agent got a semantic-only ranking while the UI got the service's
    fused one -- the same query, two orders, no error. The score the tool
    publishes is the fused value under the twin's own key.
    """
    monkeypatch.setattr(mcp_server, "_pipeline", _FakePipeline())

    calls: list = []

    async def _fake_search(self, query, limit=20, repo_id=None, language=None):
        calls.append({"query": query, "limit": limit, "repo_id": repo_id, "language": language})
        return CodeSearchAnswer(results=[{
            "chunk_content": "def parse(): ...", "file_path": "a.py",
            "repo_id": "11111111-1111-1111-1111-111111111111", "language": "python",
            "symbol_name": "parse", "line_start": 1, "line_end": 2,
            "rrf_score": 0.5,
        }])

    monkeypatch.setattr(CodeQueryService, "search_code", _fake_search)

    rows = json.loads(await mcp_server.code_search("parse", language="python", limit=7))

    assert calls == [{"query": "parse", "limit": 7, "repo_id": None, "language": "python"}]
    assert rows[0]["score"] == 0.5
    # repo_id is the isolation key the content-surface registry declares this
    # surface labels its rows with; the tool emitted no such key at all.
    assert rows[0]["repo_id"] == "11111111-1111-1111-1111-111111111111"


async def test_code_blast_radius_runs_the_rest_twins_traversal(mcp_session, monkeypatch):
    """The traversal is the service's; the tool resolves only the repository.

    A verbatim second copy of the recursive CTE lived here and had already
    drifted from the one behind ``POST /code/blast-radius``: the service emits
    each affected row's owner-qualified graph ``key`` and this tool dropped it,
    so an agent could not address the callers it was being shown.
    """
    repo = Repository(name="parity-repo")
    mcp_session.add(repo)
    await mcp_session.flush()
    code_file = CodeFile(
        id=uuid.uuid4(), repo_id=repo.id, file_path="pkg/mod.py",
        language="python", content_hash="h",
    )
    mcp_session.add(code_file)
    await mcp_session.flush()
    symbol = CodeSymbol(
        id=uuid.uuid4(), file_id=code_file.id, name="target", kind="function",
        line_start=1, line_end=2, source_code="def target(): ...",
    )
    mcp_session.add(symbol)
    await mcp_session.flush()

    calls: list = []
    real = CodeQueryService.calculate_blast_radius

    async def _spy(self, symbol_id, max_depth=10, repo_id=None):
        calls.append((symbol_id, max_depth, repo_id))
        return await real(self, symbol_id, max_depth, repo_id=repo_id)

    monkeypatch.setattr(CodeQueryService, "calculate_blast_radius", _spy)

    payload = json.loads(await mcp_server.code_blast_radius(
        "target", repo_name="parity-repo", max_depth=4,
    ))

    assert calls == [("target", 4, repo.id)]
    assert payload["symbol"]["id"] == str(symbol.id)
    assert payload["symbol"]["file_path"] == "pkg/mod.py"
    assert payload["risk"] == "LOW"
    assert set(payload["by_depth"]) == {"1", "2", "3+"}


async def test_code_blast_radius_publishes_the_graph_key_of_each_caller(
    mcp_session, monkeypatch,
):
    calls: list = []

    async def _fake(self, symbol_id, max_depth=10, repo_id=None):
        calls.append(symbol_id)
        return {
            "symbol": {"id": symbol_id, "name": "target", "file_path": "pkg/mod.py"},
            "affected": [{
                "key": "caller::pkg/other.py", "name": "caller",
                "kind": "function", "file_path": "pkg/other.py", "distance": 1,
            }],
            "by_depth": {"1": [], "2": [], "3+": []},
            "risk": "LOW", "total": 1,
        }

    monkeypatch.setattr(CodeQueryService, "calculate_blast_radius", _fake)

    repo = Repository(name="key-repo")
    mcp_session.add(repo)
    await mcp_session.flush()
    code_file = CodeFile(
        id=uuid.uuid4(), repo_id=repo.id, file_path="pkg/mod.py",
        language="python", content_hash="h",
    )
    mcp_session.add(code_file)
    await mcp_session.flush()
    mcp_session.add(CodeSymbol(
        id=uuid.uuid4(), file_id=code_file.id, name="target", kind="function",
        line_start=1, line_end=2, source_code="def target(): ...",
    ))
    await mcp_session.flush()

    payload = json.loads(await mcp_server.code_blast_radius("target", repo_name="key-repo"))

    assert calls, "the tool did not reach the shared traversal"
    assert payload["affected"][0]["key"] == "caller::pkg/other.py"


async def test_code_blast_radius_still_raises_on_an_unknown_symbol(mcp_session):
    """A caller error raises; it is not a degradation envelope (doc 12 s3)."""
    with pytest.raises(ValueError):
        await mcp_server.code_blast_radius("no-such-symbol")


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


async def test_source_agent_is_the_raw_user_agent_not_the_resolved_source(
    mcp_http_client, session,
):
    """``source_agent`` carries the User-Agent verbatim, independently of
    whichever tier won the ``source`` chain.

    The two are deliberately different facts: ``source`` is a normalised label
    the UI filters and colours by, ``source_agent`` is the unedited string the
    caller sent, which is the only thing that can still identify a client the
    source map does not know.
    """
    from sqlalchemy import select

    raw_ua = "SomeHarness/9.9 (+https://example.invalid)"
    response = await mcp_http_client.post(
        "/",
        json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {
                "name": "memory_add",
                "arguments": {"content": "source agent probe", "wait_process": True},
            },
        },
        headers={"X-Darkmem-Client": "codex", "User-Agent": raw_ua},
    )
    assert response.status_code == 200, response.text

    memory = (await session.execute(
        select(Memory).where(Memory.content == "source agent probe")
    )).scalar_one()
    assert memory.source == "codex"
    assert memory.source_agent == raw_ua

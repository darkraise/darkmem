"""End-to-end code-indexing harness: real files through phases 01-08.

Drives the pipeline phases directly on a temp dir (phase_01 full=True lists
files from disk, no git), so the parse -> structure -> resolve -> call-trace ->
heritage flow can be exercised and asserted without a git repo, vector store, or
LLM. This is the harness the remaining code-graph fixes are built and verified on.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from app.models.code import Repository
from app.services.code_pipeline import CodePipeline
from app.services.code_query import CodeQueryService


async def index_repo(session, tmp_path, files: dict[str, str]) -> Repository:
    for rel, content in files.items():
        p = Path(tmp_path) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    repo = Repository(name=f"repo-{uuid.uuid4().hex[:8]}", local_path=str(tmp_path))
    session.add(repo)
    await session.flush()

    pipe = CodePipeline(session, None, None, None)
    pipe._repo = repo
    pipe._work_dir = Path(tmp_path)
    pipe._repo_id_str = str(repo.id)
    pipe._stats = {
        "status": "indexed", "commit": "t", "files_changed": 0, "files_deleted": 0,
        "files_skipped": 0, "symbols_indexed": 0, "chunks_stored": 0,
        "calls_resolved": 0, "accesses": 0, "errors": [],
    }

    await pipe.phase_01_file_discovery(None, "testsha", full=True)
    await pipe.phase_02_parsing()
    await pipe.phase_03_structure()
    await pipe.phase_04_import_resolution()
    await pipe.phase_05_named_bindings()
    await pipe.phase_06_call_tracing()
    await pipe.phase_07_heritage_mro()
    await pipe.phase_08_cross_file_binding()
    await session.flush()
    return repo


async def symbol_names(session, repo_id) -> set[str]:
    rows = (await session.execute(
        text("""
            SELECT cs.name FROM code_symbols cs
            JOIN code_files cf ON cs.file_id = cf.id
            WHERE cf.repo_id = :r
        """),
        {"r": str(repo_id)},
    )).scalars().all()
    return set(rows)


async def call_edges(session, repo_id) -> list[tuple[str, str]]:
    rows = (await session.execute(
        text("""
            SELECT source_key, target_key FROM code_edges
            WHERE repo_id = :r AND edge_type = 'calls'
        """),
        {"r": str(repo_id)},
    )).mappings().all()
    return [(r["source_key"], r["target_key"]) for r in rows]


@pytest.mark.asyncio
async def test_pipeline_extracts_methods_end_to_end(session, tmp_path):
    repo = await index_repo(session, tmp_path, {
        "svc.py": (
            "class Svc:\n"
            "    def start(self):\n"
            "        return self.helper()\n"
            "    def helper(self):\n"
            "        return 1\n"
        ),
    })
    names = await symbol_names(session, repo.id)
    # Methods must now be persisted (the blocker fix), not just the class.
    assert {"Svc", "start", "helper"} <= names


@pytest.mark.asyncio
async def test_same_named_methods_in_one_file_get_distinct_nodes(session, tmp_path):
    repo = await index_repo(session, tmp_path, {
        "models.py": (
            "class UserRepo:\n    def save(self):\n        return 1\n\n"
            "class OrderRepo:\n    def save(self):\n        return 2\n"
        ),
    })
    nodes = (await session.execute(
        text("""
            SELECT key FROM code_graph_nodes
            WHERE repo_id = :r AND kind = 'symbol' AND label = 'save'
        """),
        {"r": str(repo.id)},
    )).scalars().all()
    # UserRepo.save and OrderRepo.save must be two distinct nodes, not one
    # collided node keyed save::models.py.
    assert len(nodes) == 2


@pytest.mark.asyncio
async def test_inherited_method_call_resolves_to_ancestor(session, tmp_path):
    """self.<method>() where the method is defined only on an ancestor must get a
    call edge via the inheritance walk. The decoy 'greet' in other.py makes the
    global lookup ambiguous, so the resolver returns None — only walking Child's
    extends chain to Base can resolve it."""
    repo = await index_repo(session, tmp_path, {
        "base.py": "class Base:\n    def greet(self):\n        return 1\n",
        "child.py": (
            "class Child(Base):\n"
            "    def run(self):\n"
            "        return self.greet()\n"
        ),
        "other.py": "class Other:\n    def greet(self):\n        return 2\n",
    })
    edges = await call_edges(session, repo.id)
    assert ("run::child.py::Child", "greet::base.py::Base") in edges


@pytest.mark.asyncio
async def test_cross_file_extends_edge_targets_real_base_node(session, tmp_path):
    """A subclass extending a base class defined in another file must point its
    extends edge at the base's real node (Base::base.py), not Base::child.py
    (the child's own file). The malformed key orphaned the edge and broke
    cross-file override / inherited-method detection."""
    repo = await index_repo(session, tmp_path, {
        "base.py": "class Base:\n    def greet(self):\n        return 1\n",
        "child.py": (
            "from base import Base\n"
            "class Child(Base):\n"
            "    def run(self):\n"
            "        return 2\n"
        ),
    })
    rows = (await session.execute(
        text("SELECT source_key, target_key FROM code_edges "
             "WHERE repo_id = :r AND edge_type = 'extends'"),
        {"r": str(repo.id)},
    )).mappings().all()
    edges = [(r["source_key"], r["target_key"]) for r in rows]
    assert ("Child::child.py", "Base::base.py") in edges


@pytest.mark.asyncio
async def test_load_symbol_index_caches_the_query(session, tmp_path, monkeypatch):
    """Phases 06 and 08 ran the same CodeSymbol+CodeFile SELECT and rebuilt an
    identical symbol table twice per index run. _load_symbol_index must build it
    once and cache it, so the second consumer reuses the first's result."""
    repo = await index_repo(session, tmp_path, {
        "a.py": (
            "class A:\n"
            "    def m(self):\n"
            "        return self.n()\n"
            "    def n(self):\n"
            "        return 1\n"
        ),
    })
    pipe = CodePipeline(session, None, None, None)
    pipe._repo = repo
    pipe._repo_id_str = str(repo.id)

    count = {"n": 0}
    orig = session.execute

    async def counting(stmt, *a, **k):
        s = str(stmt)
        if "FROM code_symbols" in s and "code_files.file_path" in s:
            count["n"] += 1
        return await orig(stmt, *a, **k)

    monkeypatch.setattr(session, "execute", counting)

    table1, by_id1, names1, enc1, tb1 = await pipe._load_symbol_index()
    after_first = count["n"]
    table2, by_id2, names2, enc2, tb2 = await pipe._load_symbol_index()
    after_second = count["n"]

    assert after_first == 1
    assert after_second == 1  # cached — no second symbol-table query
    assert table2 is table1 and by_id2 is by_id1  # same cached objects


@pytest.mark.asyncio
async def test_intra_class_call_edge_is_owner_qualified(session, tmp_path):
    repo = await index_repo(session, tmp_path, {
        "svc.py": (
            "class Svc:\n"
            "    def start(self):\n"
            "        return self.helper()\n"
            "    def helper(self):\n"
            "        return 1\n"
        ),
    })
    edges = await call_edges(session, repo.id)
    # The call edge's endpoints must carry the owner segment so they match the
    # owner-qualified method nodes; an un-owned key would orphan the edge.
    assert ("start::svc.py::Svc", "helper::svc.py::Svc") in edges


@pytest.mark.asyncio
async def test_code_graph_view_has_no_orphan_method_edges(session, tmp_path):
    repo = await index_repo(session, tmp_path, {
        "svc.py": (
            "class Svc:\n"
            "    def start(self):\n"
            "        return self.helper()\n"
            "    def helper(self):\n"
            "        return 1\n"
        ),
    })
    graph = await CodeQueryService(session).get_code_graph(repo.id)
    node_ids = {n["id"] for n in graph["nodes"]}
    # Every symbol-keyed edge endpoint must resolve to a node the view emits;
    # the method nodes and the call edge must agree on owner-qualified keys.
    for edge in graph["edges"]:
        if "::" in edge["source"]:
            assert edge["source"] in node_ids
        if "::" in edge["target"]:
            assert edge["target"] in node_ids

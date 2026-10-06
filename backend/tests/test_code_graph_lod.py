"""The Code Graph's level of detail (GET /code/graph/{repo_id}?level=&scope=).

The canvas lays every node out in the browser, and the darkmem repo's 22,507
nodes and 68,032 edges (a 24 MB payload) kept the tab busy past a 30-second
screenshot. ``level=auto`` folds symbols into their files above a node limit,
and ``scope`` drills into one file or folder. With neither argument the route
answers exactly what it always has.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services import code_query
from app.services.code_query import CodeQueryService, normalise_graph_scope
from tests.test_code_pipeline_integration import index_repo

FILES = {
    "pkg/a.py": (
        "from pkg.b import helper\n"
        "\n"
        "def run():\n"
        "    return helper() + helper()\n"
        "\n"
        "def again():\n"
        "    return helper()\n"
    ),
    "pkg/b.py": (
        "def helper():\n"
        "    return inner()\n"
        "\n"
        "def inner():\n"
        "    return 1\n"
    ),
    "pkgx/c.py": (
        "def other():\n"
        "    return 2\n"
    ),
    "README.md": "# notes\n",
}


async def _add_process(session, repo_id, key: str, steps: list[str]) -> None:
    await session.execute(
        text("""
            INSERT INTO code_graph_nodes (repo_id, kind, key, label, properties)
            VALUES (:r, 'process', :k, :k, '{}')
        """),
        {"r": str(repo_id), "k": key},
    )
    for i, step in enumerate(steps, start=1):
        await session.execute(
            text("""
                INSERT INTO code_edges
                    (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                VALUES (:r, 'symbol', :s, 'process', :k, 'step_in_process',
                        jsonb_build_object('step', CAST(:i AS int)))
            """),
            {"r": str(repo_id), "s": step, "k": key, "i": i},
        )


async def _add_community(session, repo_id, key: str, members: list[str]) -> None:
    await session.execute(
        text("""
            INSERT INTO code_graph_nodes (repo_id, kind, key, label, properties)
            VALUES (:r, 'community', :k, :k, '{}')
        """),
        {"r": str(repo_id), "k": key},
    )
    for member in members:
        await session.execute(
            text("""
                INSERT INTO code_edges
                    (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                VALUES (:r, 'symbol', :s, 'community', :k, 'member_of', '{}')
            """),
            {"r": str(repo_id), "s": member, "k": key},
        )


def test_scope_normalises_to_a_relative_path_or_nothing():
    assert normalise_graph_scope(None) is None
    assert normalise_graph_scope("  ") is None
    assert normalise_graph_scope("/") is None
    assert normalise_graph_scope("pkg/") == "pkg"
    assert normalise_graph_scope("/pkg/a.py") == "pkg/a.py"


@pytest.mark.asyncio
async def test_no_level_and_no_scope_is_the_unchanged_whole_graph(session, tmp_path):
    repo = await index_repo(session, tmp_path, FILES)
    svc = CodeQueryService(session)

    legacy = await svc.get_code_graph(repo.id)
    explicit = await svc.get_code_graph(repo.id, level="symbol")

    assert set(legacy) == {"nodes", "edges"}
    assert legacy["nodes"] == explicit["nodes"]
    assert legacy["edges"] == explicit["edges"]
    assert explicit["level"] == "symbol"


@pytest.mark.asyncio
async def test_file_level_folds_symbol_edges_into_weighted_file_edges(session, tmp_path):
    repo = await index_repo(session, tmp_path, FILES)

    graph = await CodeQueryService(session).get_code_graph(repo.id, level="file")

    assert graph["level"] == "file"
    ids = {n["id"] for n in graph["nodes"]}
    # A file that defines no symbol has nothing to fold into it.
    assert ids == {"pkg/a.py", "pkg/b.py", "pkgx/c.py"}
    assert all(n["kind"] == "file" for n in graph["nodes"])
    by_id = {n["id"]: n for n in graph["nodes"]}
    assert by_id["pkg/a.py"]["symbol_count"] == 2

    depends = [e for e in graph["edges"] if e["type"] == "depends_on"]
    assert [(e["source"], e["target"]) for e in depends] == [("pkg/a.py", "pkg/b.py")]
    calls_a_to_b = (await session.execute(
        text("""
            SELECT count(*) FROM code_edges
            WHERE repo_id = :r AND edge_type = 'calls'
              AND split_part(source_key, '::', 2) = 'pkg/a.py'
              AND split_part(target_key, '::', 2) = 'pkg/b.py'
        """),
        {"r": str(repo.id)},
    )).scalar_one()
    assert calls_a_to_b >= 2
    assert depends[0]["properties"]["weight"] == calls_a_to_b
    assert depends[0]["properties"]["edge_types"]["calls"] == calls_a_to_b

    stats = graph["stats"]
    assert stats["files_drawn"] == 3
    assert stats["files_without_symbols"] == stats["files"] - 3 >= 1
    assert stats["file_edges"] == 1
    # helper -> inner stays inside pkg/b.py: counted as folded, never drawn.
    assert stats["symbol_edges"] > calls_a_to_b


@pytest.mark.asyncio
async def test_auto_folds_only_above_the_limit(session, tmp_path, monkeypatch):
    repo = await index_repo(session, tmp_path, FILES)
    svc = CodeQueryService(session)

    small = await svc.get_code_graph(repo.id, level="auto")
    assert small["level"] == "symbol"
    assert small["requested_level"] == "auto"
    assert any(n["kind"] == "function" for n in small["nodes"])

    monkeypatch.setattr(code_query, "CODE_GRAPH_AUTO_LIMIT", 3)
    folded = await svc.get_code_graph(repo.id, level="auto")
    assert folded["level"] == "file"
    assert folded["auto_limit"] == 3

    # The limit counts the scope, so drilling into one file draws its symbols.
    drilled = await svc.get_code_graph(repo.id, level="auto", scope="pkg/b.py")
    assert drilled["level"] == "symbol"
    assert {n["label"] for n in drilled["nodes"] if n["kind"] == "function"} == {
        "helper", "inner",
    }


@pytest.mark.asyncio
async def test_a_folder_scope_never_matches_a_sibling_sharing_its_prefix(session, tmp_path):
    repo = await index_repo(session, tmp_path, FILES)

    graph = await CodeQueryService(session).get_code_graph(repo.id, scope="pkg/")

    assert graph["scope"] == "pkg"
    files = {n.get("file_path") for n in graph["nodes"] if n.get("file_path")}
    assert files == {"pkg/a.py", "pkg/b.py"}
    ids = {n["id"] for n in graph["nodes"]}
    # Every edge the scoped graph ships lands on a node it ships.
    for edge in graph["edges"]:
        if edge["type"] == "step_in_process":
            continue
        assert edge["source"] in ids and edge["target"] in ids


@pytest.mark.asyncio
async def test_a_scoped_process_keeps_every_step(session, tmp_path):
    repo = await index_repo(session, tmp_path, FILES)
    await _add_process(
        session, repo.id, "scored:run::pkg/a.py",
        ["run::pkg/a.py", "helper::pkg/b.py", "other::pkgx/c.py"],
    )

    graph = await CodeQueryService(session).get_code_graph(repo.id, scope="pkg/a.py")

    assert "scored:run::pkg/a.py" in {n["id"] for n in graph["nodes"]}
    steps = [
        e["source"] for e in graph["edges"]
        if e["type"] == "step_in_process" and e["target"] == "scored:run::pkg/a.py"
    ]
    assert steps == ["run::pkg/a.py", "helper::pkg/b.py", "other::pkgx/c.py"]


@pytest.mark.asyncio
async def test_a_folded_file_joins_the_community_most_of_its_symbols_are_in(session, tmp_path):
    repo = await index_repo(session, tmp_path, FILES)
    await _add_community(session, repo.id, "core_0", ["run::pkg/a.py", "again::pkg/a.py", "helper::pkg/b.py"])
    await _add_community(session, repo.id, "edge_1", ["inner::pkg/b.py", "other::pkgx/c.py"])
    await _add_process(session, repo.id, "scored:run::pkg/a.py", ["run::pkg/a.py", "helper::pkg/b.py"])

    graph = await CodeQueryService(session).get_code_graph(repo.id, level="file")

    member = {e["source"]: e["target"] for e in graph["edges"] if e["type"] == "member_of"}
    assert member["pkg/a.py"] == "core_0"
    assert member["pkgx/c.py"] == "edge_1"
    kinds = {n["id"]: n["kind"] for n in graph["nodes"]}
    assert kinds["core_0"] == "community"
    assert kinds["scored:run::pkg/a.py"] == "process"
    steps = [e["source"] for e in graph["edges"] if e["type"] == "step_in_process"]
    assert steps == ["run::pkg/a.py", "helper::pkg/b.py"]


@pytest.mark.asyncio
async def test_the_route_serves_the_level_and_refuses_an_unknown_one(
    session, client, auth_headers, tmp_path,
):
    repo = await index_repo(session, tmp_path, FILES)

    resp = await client.get(
        f"/api/v1/code/graph/{repo.id}", params={"level": "file", "scope": "pkg"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["level"] == "file"
    assert body["scope"] == "pkg"
    assert {n["id"] for n in body["nodes"]} == {"pkg/a.py", "pkg/b.py"}

    legacy = await client.get(f"/api/v1/code/graph/{repo.id}", headers=auth_headers)
    assert set(legacy.json()) == {"nodes", "edges"}

    bad = await client.get(
        f"/api/v1/code/graph/{repo.id}", params={"level": "folder"}, headers=auth_headers,
    )
    assert bad.status_code == 422

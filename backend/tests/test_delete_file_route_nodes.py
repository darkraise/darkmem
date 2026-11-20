"""Deleting a file's data must not leak route/tool graph nodes.

Route/tool nodes have bare keys (no ::file_path) and no file_path property, so
neither delete predicate matched them — the handles_route/handles_tool edge was
removed but the node survived, so incremental indexing accumulated phantom
routes/processes over a repo's lifetime.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.models.code import Repository
from app.services.code_pipeline import CodePipeline


@pytest.mark.asyncio
async def test_delete_file_data_removes_orphaned_route_node(session):
    repo = Repository(name="r")
    session.add(repo)
    await session.flush()

    fp = "app/routes.py"
    route_key = "GET /users"
    await session.execute(
        text("""
            INSERT INTO code_graph_nodes (repo_id, kind, key, label, properties)
            VALUES (:rid, 'route', :k, :k, '{"method":"GET","path":"/users"}'::jsonb)
        """),
        {"rid": str(repo.id), "k": route_key},
    )
    await session.execute(
        text("""
            INSERT INTO code_edges
                (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
            VALUES (:rid, 'file', :src, 'route', :tgt, 'handles_route', '{}')
        """),
        {"rid": str(repo.id), "src": fp, "tgt": route_key},
    )
    await session.flush()

    pipe = CodePipeline(session, None, None, None)
    await pipe._delete_files_data(repo.id, [fp])
    await pipe._sweep_orphan_handlers(repo.id)

    remaining = (await session.execute(
        text("SELECT COUNT(*) FROM code_graph_nodes WHERE repo_id = :rid AND kind = 'route'"),
        {"rid": str(repo.id)},
    )).scalar()
    assert remaining == 0

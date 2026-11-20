import ast
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.models.code import CodeFile, CodeSymbol, Repository
from app.services import code_query
from app.services.code_query import CodeQueryService
from app.services.rank_fusion import RRF_K


@pytest.mark.parametrize("semantic", [False, True])
async def test_search_fusion_keeps_repository_identity(session, monkeypatch, semantic):
    repo_ids = [uuid4(), uuid4()]
    for repo_id in repo_ids:
        session.add(Repository(id=repo_id, name=str(repo_id)))
        await session.flush()
        code_file = CodeFile(repo_id=repo_id, file_path="src/main.py", language="python")
        session.add(code_file)
        await session.flush()
        session.add(CodeSymbol(
            file_id=code_file.id, name="target", kind="function", line_start=1,
            line_end=2, source_code="def target():\n    return 1",
        ))
    await session.flush()
    llm = Mock(embed=AsyncMock(return_value=([0.0], "unused"))) if semantic else None
    chunks = [{
        "repo_id": repo_id, "file_path": "src/main.py", "line_start": 1,
        "line_end": 2, "chunk_content": "target", "language": "python",
    } for repo_id in repo_ids]
    monkeypatch.setattr(
        "app.services.code_query.PostgresVectorRepository.search_code_chunks",
        AsyncMock(return_value=chunks),
    )

    results = (await CodeQueryService(session, llm).search_code("target")).results

    assert {result["repo_id"] for result in results} == {str(repo_id) for repo_id in repo_ids}
    assert len(results) == 2
    assert sum(result["rrf_score"] for result in results) == pytest.approx(
        (2 if semantic else 1) * (1 / (RRF_K + 1) + 1 / (RRF_K + 2))
    )


def test_code_query_declares_no_fusion_of_its_own():
    tree = ast.parse(Path(code_query.__file__).read_text())

    reciprocal_ranks = [
        node.lineno for node in ast.walk(tree)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
        and isinstance(node.left, ast.Constant) and node.left.value == 1
    ]
    fuse_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (getattr(node.func, "id", None) or getattr(node.func, "attr", None)) == "rrf_fuse"
    ]

    assert reciprocal_ranks == []
    assert fuse_calls


async def test_one_failing_arm_leaves_the_other_answering(session, monkeypatch):
    repo_id = uuid4()
    session.add(Repository(id=repo_id, name=str(repo_id)))
    await session.flush()
    code_file = CodeFile(repo_id=repo_id, file_path="src/main.py", language="python")
    session.add(code_file)
    await session.flush()
    session.add(CodeSymbol(
        file_id=code_file.id, name="target", kind="function", line_start=1,
        line_end=2, source_code="def target():\n    return 1",
    ))
    await session.flush()

    async def _broken_arm(self, *args, **kwargs):
        await self.session.execute(text("SELECT CAST('not-a-uuid' AS uuid)"))

    monkeypatch.setattr(
        "app.services.code_query.PostgresVectorRepository.search_code_chunks", _broken_arm,
    )
    llm = Mock(embed=AsyncMock(return_value=([0.0], "unused")))

    answer = await CodeQueryService(session, llm).search_code("target", repo_id=repo_id)

    assert [r["symbol_name"] for r in answer.results] == ["target"]
    assert answer.failed_arms == ("vector",)
    assert (await session.execute(text("SELECT 1"))).scalar_one() == 1

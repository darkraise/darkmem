"""Incremental index runs: a temporary git repository indexed once, changed,
committed and indexed again."""
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from app.models.code import Repository
from app.repositories.vector import PostgresVectorRepository
from app.services.code_pipeline import CodePipeline
from app.services.embedder_registry import child_table, embedder_registry
from app.services.repo_manager import RepoManager


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root, check=True, capture_output=True,
    )


def _commit(root: Path, files: dict[str, str | None]) -> None:
    for name, content in files.items():
        path = root / name
        if content is None:
            _git(root, "rm", "-q", name)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        _git(root, "add", name)
    _git(root, "commit", "-qm", "change")


class _StubEmbedder:
    """Answers every chunk unless it carries ``fail_marker``, and records
    every text it was asked to embed."""

    def __init__(self, fingerprint: str):
        self.fingerprint = fingerprint
        self.fail_marker: str | None = None
        self.texts: list[str] = []

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        if self.fail_marker and any(self.fail_marker in t for t in texts):
            raise RuntimeError("embedder timed out")
        self.texts.extend(texts)
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts], self.fingerprint

    async def embed(self, text_value):
        return [0.1, 0.2, 0.3, 0.4], self.fingerprint


@pytest.fixture
def embedder():
    stub = _StubEmbedder(f"stub-code-{uuid.uuid4().hex[:8]}|4")
    yield stub
    # The registry cache is process-wide while the database rolls back.
    embedder_registry.forget(stub.fingerprint)


async def _repo(session, root: Path, files: dict[str, str]) -> Repository:
    _git(root, "init", "-q")
    _commit(root, files)
    repo = Repository(
        name=f"incr-{uuid.uuid4().hex[:8]}", local_path=str(root),
        provider="local", status="ready",
    )
    session.add(repo)
    await session.commit()
    return repo


async def _index(session, repo: Repository, llm=None) -> dict:
    pipeline = CodePipeline(
        session=session, llm=llm,
        vector_repo=PostgresVectorRepository(session) if llm else None,
        repo_manager=RepoManager(session),
    )
    result = await pipeline.run(repo.id)
    await session.refresh(repo)
    return result


async def _symbols(session, repo_id, file_path: str) -> set[str]:
    return set((await session.execute(
        text("""
            SELECT cs.name FROM code_symbols cs
            JOIN code_files cf ON cs.file_id = cf.id
            WHERE cf.repo_id = :r AND cf.file_path = :p
        """),
        {"r": repo_id, "p": file_path},
    )).scalars().all())


async def _chunk_files(session, repo_id, fingerprint: str) -> set[str]:
    table = child_table("code_chunk_embeddings", fingerprint)
    return set((await session.execute(
        text(f"SELECT DISTINCT file_path FROM {table} WHERE repo_id = :r"),
        {"r": repo_id},
    )).scalars().all())


async def test_non_ascii_path_is_reindexed_and_removed(session, tmp_path):
    path = "src/é.py"
    repo = await _repo(session, tmp_path, {path: "def eacute_one():\n    return 1\n"})
    await _index(session, repo)
    assert await _symbols(session, repo.id, path) == {"eacute_one"}

    _commit(tmp_path, {path: "def eacute_two():\n    return 2\n"})
    await _index(session, repo)
    assert await _symbols(session, repo.id, path) == {"eacute_two"}

    _commit(tmp_path, {path: None})
    await _index(session, repo)
    remaining = (await session.execute(
        text("SELECT count(*) FROM code_files WHERE repo_id = :r AND file_path = :p"),
        {"r": repo.id, "p": path},
    )).scalar_one()
    assert remaining == 0
    assert await _symbols(session, repo.id, path) == set()


async def test_subclass_keeps_its_extends_edge_to_an_unchanged_file(session, tmp_path):
    repo = await _repo(session, tmp_path, {
        "base.py": "class BaseView:\n    def render(self):\n        return 1\n",
        "views.py": "from base import BaseView\n\nclass V(BaseView):\n    pass\n",
    })
    await _index(session, repo)

    _commit(tmp_path, {
        "views.py": (
            "from base import BaseView\n\nclass V(BaseView):\n"
            "    def extra(self):\n        return 2\n"
        ),
    })
    await _index(session, repo)

    targets = set((await session.execute(
        text("""
            SELECT target_key FROM code_edges
            WHERE repo_id = :r AND edge_type = 'extends' AND source_key = 'V::views.py'
        """),
        {"r": repo.id},
    )).scalars().all())
    assert targets == {"BaseView::base.py"}


async def test_file_with_a_failed_embed_is_embedded_by_the_next_run(
    session, tmp_path, embedder,
):
    repo = await _repo(session, tmp_path, {
        "a.py": "def alpha():\n    return 1\n",
        "b.py": "def beta():\n    return 1\n",
    })
    await _index(session, repo, embedder)
    assert await _chunk_files(session, repo.id, embedder.fingerprint) == {"a.py", "b.py"}

    embedder.fail_marker = "ALPHA_TWO"
    _commit(tmp_path, {"a.py": "def alpha():\n    return 'ALPHA_TWO'\n"})
    await _index(session, repo, embedder)
    assert await _chunk_files(session, repo.id, embedder.fingerprint) == {"b.py"}

    embedder.fail_marker = None
    _commit(tmp_path, {"b.py": "def beta():\n    return 2\n"})
    await _index(session, repo, embedder)
    assert await _chunk_files(session, repo.id, embedder.fingerprint) == {"a.py", "b.py"}


async def test_unchanged_dependent_is_not_reembedded(session, tmp_path, embedder):
    repo = await _repo(session, tmp_path, {
        "util.py": "def helper():\n    return 'UTIL_ONE'\n",
        "caller.py": (
            "from util import helper\n\ndef call_it():\n"
            "    return helper() + 'CALLER_BODY'\n"
        ),
    })
    await _index(session, repo, embedder)

    embedder.texts.clear()
    _commit(tmp_path, {"util.py": "def helper():\n    return 'UTIL_TWO'\n"})
    await _index(session, repo, embedder)

    assert any("UTIL_TWO" in t for t in embedder.texts)
    assert not any("CALLER_BODY" in t for t in embedder.texts)
    calls = set((await session.execute(
        text("""
            SELECT target_key FROM code_edges
            WHERE repo_id = :r AND edge_type = 'calls' AND source_key = 'call_it::caller.py'
        """),
        {"r": repo.id},
    )).scalars().all())
    assert calls == {"helper::util.py"}

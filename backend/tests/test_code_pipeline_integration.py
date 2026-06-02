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

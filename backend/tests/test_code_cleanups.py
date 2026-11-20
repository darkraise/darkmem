"""Code indexing leftovers: a deleted repository's wiki row, and the
code_files.last_commit_sha column that nothing reads or writes."""
from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select, text

from app.models.code import Repository
from app.models.config import Config
from app.services.repo_manager import RepoManager

REPO_ROOT = Path(__file__).resolve().parents[2]
SCANNED = [
    REPO_ROOT / "backend" / "app",
    REPO_ROOT / "backend" / "scripts",
    REPO_ROOT / "frontend" / "src",
]


async def test_repo_delete_removes_its_wiki_row(session):
    repo = Repository(name=f"wiki-{uuid.uuid4().hex[:8]}", status="ready")
    session.add(repo)
    await session.flush()
    session.add(Config(key=f"wiki_{repo.id}", value={"overview": "x"}))
    await session.flush()

    await RepoManager(session).delete(repo.id)

    assert (await session.execute(
        select(Config).where(Config.key == f"wiki_{repo.id}")
    )).scalar_one_or_none() is None


def test_last_commit_sha_has_no_reader_or_writer():
    hits = [
        str(path.relative_to(REPO_ROOT))
        for root in SCANNED
        for path in root.rglob("*")
        if path.suffix in {".py", ".ts", ".tsx"}
        and "node_modules" not in path.parts
        and "last_commit_sha" in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert hits == []


async def test_last_commit_sha_column_still_exists(session):
    found = (await session.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'code_files' AND column_name = 'last_commit_sha'
    """))).scalar_one_or_none()
    assert found == 1

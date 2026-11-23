"""Repository lifecycle in the events journal, and counted index progress.

The Activity feed's code tab read "No recent code events" after three
reindexes: the UI's reindex route, repo add/delete and an index run's own
outcome journalled nothing. And reindex progress was a bare phase label
("Parsing files..." sat still for 86 s) with no count.
"""
from __future__ import annotations

import logging
import uuid

import pytest
from sqlalchemy import text

from app.api.routes import repos as repos_route
from app.models.code import Repository
from app.services import code_pipeline
from app.services.code_pipeline import CodePipeline
from app.services.repo_manager import RepoManager
from tests.test_code_pipeline_integration import index_repo


async def _events(session, repo_id) -> list[dict]:
    rows = (await session.execute(
        text("""
            SELECT event_type, actor, source, payload FROM events
            WHERE object_type = 'repository' AND object_id = CAST(:r AS uuid)
            ORDER BY created_at, id
        """),
        {"r": str(repo_id)},
    )).mappings().all()
    return [dict(r) for r in rows]


@pytest.fixture
def no_spawn(monkeypatch):
    spawned: list[str] = []
    monkeypatch.setattr(
        repos_route, "_spawn_repo_index",
        lambda repo_id, *a, kind, **k: spawned.append(kind),
    )
    return spawned


@pytest.mark.asyncio
async def test_add_reindex_and_delete_each_journal_a_row(
    client, session, auth_headers, tmp_path, no_spawn,
):
    repo_dir = tmp_path / "journalled"
    repo_dir.mkdir()
    created = await client.post(
        "/api/v1/repos", json={"name": "journalled", "local_path": str(repo_dir)},
        headers=auth_headers,
    )
    assert created.status_code == 201
    repo_id = created.json()["id"]

    # The initial index holds the claim; release it as a finished run would.
    await session.execute(
        text("UPDATE repositories SET status = 'ready' WHERE id = CAST(:r AS uuid)"),
        {"r": repo_id},
    )
    reindex = await client.post(
        f"/api/v1/repos/{repo_id}/reindex", json={"full": True}, headers=auth_headers,
    )
    assert reindex.status_code == 202
    busy = await client.post(f"/api/v1/repos/{repo_id}/reindex", json={}, headers=auth_headers)
    assert busy.status_code == 409

    rows = await _events(session, repo_id)
    assert [r["event_type"] for r in rows] == [
        "repo_registered", "repo_reindex_requested", "repo_reindex_requested",
    ]
    assert rows[0]["actor"] == "admin"
    assert rows[0]["payload"]["name"] == "journalled"
    assert rows[1]["payload"]["outcome"] == "indexing"
    assert rows[1]["payload"]["full"] is True
    assert rows[2]["payload"]["outcome"] == "repo_busy"

    deleted = await client.delete(f"/api/v1/repos/{repo_id}", headers=auth_headers)
    assert deleted.status_code == 204
    rows = await _events(session, repo_id)
    assert rows[-1]["event_type"] == "repo_deleted"
    assert rows[-1]["payload"] == {"name": "journalled", "outcome": "deleted"}

    feed = await client.get(
        "/api/v1/events", params={"object_type": "repository"}, headers=auth_headers,
    )
    types = {e["event_type"] for e in feed.json()["items"]}
    assert {"repo_registered", "repo_reindex_requested", "repo_deleted"} <= types


async def _repo(session, tmp_path) -> Repository:
    repo = Repository(name=f"run-{uuid.uuid4().hex[:8]}", local_path=str(tmp_path))
    session.add(repo)
    await session.flush()
    return repo


@pytest.mark.asyncio
async def test_a_completed_run_journals_its_counts(session, tmp_path, monkeypatch):
    repo = await _repo(session, tmp_path)

    async def finished(self, repo_id, **kwargs):
        return {
            "status": "indexed", "commit": "abc", "files_changed": 3,
            "files_deleted": 0, "files_skipped": 1, "symbols_indexed": 12,
            "chunks_stored": 9, "errors": ["parse:x.py:boom"],
        }

    monkeypatch.setattr(CodePipeline, "_run", finished)
    await CodePipeline(session, None, None, RepoManager(session)).run(repo.id)

    (row,) = await _events(session, repo.id)
    assert row["event_type"] == "repo_indexed"
    assert row["payload"] == {
        "action": "completed", "outcome": "completed", "commit": "abc",
        "files_changed": 3, "files_deleted": 0, "files_skipped": 1,
        "symbols_indexed": 12, "chunks_stored": 9, "errors": 1,
    }


@pytest.mark.asyncio
async def test_a_failed_run_journals_one_line_of_its_cause_and_still_raises(
    session, tmp_path, monkeypatch,
):
    repo = await _repo(session, tmp_path)

    async def failing(self, repo_id, **kwargs):
        raise RuntimeError(
            "clone https://user:secret@forge.example/r.git failed\n[SQL: INSERT ... content]"
        )

    monkeypatch.setattr(CodePipeline, "_run", failing)
    with pytest.raises(RuntimeError):
        await CodePipeline(session, None, None, RepoManager(session)).run(repo.id)

    (row,) = await _events(session, repo.id)
    assert row["event_type"] == "repo_index_failed"
    cause = row["payload"]["cause"]
    assert cause == "RuntimeError: clone https://***@forge.example/r.git failed"


@pytest.mark.asyncio
async def test_a_credentialed_failure_never_logs_the_token(
    session, tmp_path, monkeypatch, caplog,
):
    secret = "tok-9d2b7e"
    (tmp_path / "a.py").write_text("def a():\n    return 1\n")
    repo = await _repo(session, tmp_path)
    manager = RepoManager(session)
    shas = iter(["sha-good-1", "sha-2"])

    async def _pull(_repo):
        return next(shas)

    manager.pull_repo = _pull
    first = await CodePipeline(session, None, None, manager).run(repo.id, full=True)
    assert first["status"] == "indexed"

    failing = CodePipeline(session, None, None, manager)

    async def credentialed_failure():
        raise RuntimeError(f"fetch https://u:{secret}@host/r.git failed")

    monkeypatch.setattr(failing, "phase_06_call_tracing", credentialed_failure)
    caplog.set_level(logging.DEBUG, logger="app")
    with pytest.raises(RuntimeError):
        await failing.run(repo.id, full=True)

    await session.refresh(repo)
    assert repo.status == "stale"
    assert any("https://***@host" in r.getMessage() for r in caplog.records)
    assert secret not in caplog.text


@pytest.mark.asyncio
async def test_parsing_reports_files_parsed_of_total(session, tmp_path, monkeypatch):
    monkeypatch.setattr(code_pipeline, "PROGRESS_INTERVAL_SECONDS", 0)
    labels: list[str] = []

    async def record(self, message, event_type, event_data):
        labels.append(message)

    monkeypatch.setattr(CodePipeline, "_update_status", record)
    await index_repo(session, tmp_path, {
        "a.py": "def a():\n    return 1\n",
        "b.py": "def b():\n    return 2\n",
        "c.py": "def c():\n    return 3\n",
    })

    assert [m for m in labels if m.startswith("Parsing files")] == [
        "Parsing files... 1/3 files",
        "Parsing files... 2/3 files",
        "Parsing files... 3/3 files",
    ]


@pytest.mark.asyncio
async def test_embedding_reports_chunks_embedded_of_total(session, tmp_path, monkeypatch):
    from app.services import embedder_registry as registry_module

    repo = await index_repo(session, tmp_path, {
        "a.py": "def a():\n    return 1\n\ndef a2():\n    return 1\n",
        "b.py": "def b():\n    return 2\n",
    })
    monkeypatch.setattr(code_pipeline, "PROGRESS_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(registry_module.embedder_registry, "is_known", lambda fp: True)
    labels: list[str] = []

    async def record(self, message, event_type, event_data):
        labels.append(message)

    class FakeLLM:
        async def embed_batch_chunked(self, texts, size, concurrency):
            return [[0.0] for _ in texts], "fake"

    class FakeVectors:
        async def delete_code_chunks_by_file(self, *a):
            return None

        async def upsert_code_chunks(self, *a, **k):
            return None

    monkeypatch.setattr(CodePipeline, "_update_status", record)
    pipe = CodePipeline(session, FakeLLM(), FakeVectors(), RepoManager(session))
    pipe._repo = repo
    pipe._repo_id_str = str(repo.id)
    pipe._stats = {"errors": []}
    pipe._chunks_cleared_in_structure = {"a.py", "b.py"}
    from app.services.code_parser import parse_file
    pipe._parsed = {
        fp: {"parse_result": parse_file(fp, (tmp_path / fp).read_text())}
        for fp in ("a.py", "b.py")
    }
    total = sum(len(p["parse_result"].chunks) for p in pipe._parsed.values())
    assert total >= 2

    await pipe.phase_12_embeddings()

    embedding = [m for m in labels if m.startswith("Generating embeddings")]
    assert embedding[-1] == f"Generating embeddings... {total}/{total} chunks"

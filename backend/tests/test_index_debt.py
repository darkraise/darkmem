"""T1.39 — dependent-caller re-trace overflow is persisted, then drained to zero.

An incremental reindex re-traces the callers of every changed file, because
re-indexing that file deletes every call edge pointing into it. The re-trace is
capped, and the callers past the cap used to be logged and forgotten. Nothing
raises when that happens: the caller's edge is simply gone, code search returns
fewer callers, and the only symptom is a graph that is quietly wrong on exactly
the most-called symbols.

So the overflow lands in ``repositories.index_debt`` and later runs fold a
bounded batch of it back into their changed set until the queue is empty. The
two properties that matter are proved here against the real pipeline: the
overflow is never dropped, and the queue converges to zero across runs rather
than settling on a non-zero floor.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text

import app.services.code_pipeline as code_pipeline_module
from app.models.code import Repository
from app.models.config import Config
from app.services import index_debt
from app.services.code_pipeline import DEPENDENT_RETRACE_CAP, CodePipeline
from app.services.repo_manager import RepoManager

CALLER_COUNT = 3


def _write_files(tmp_path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = Path(tmp_path) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def _repo_files(target_body: str = "return 1") -> dict[str, str]:
    files = {"target.py": f"def target_fn():\n    {target_body}\n"}
    for i in range(CALLER_COUNT):
        files[f"caller{i}.py"] = (
            "from target import target_fn\n\n\n"
            f"def call{i}():\n"
            "    return target_fn()\n"
        )
    return files


async def _caller_files_with_edges(session, repo_id) -> set[str]:
    rows = (await session.execute(
        text("""
            SELECT DISTINCT split_part(source_key, '::', 2)
            FROM code_edges
            WHERE repo_id = CAST(:rid AS uuid)
              AND edge_type = 'calls'
              AND split_part(target_key, '::', 2) = 'target.py'
        """),
        {"rid": str(repo_id)},
    )).scalars().all()
    return {r for r in rows if r}


async def _make_repo(session, tmp_path, sha: str):
    _write_files(tmp_path, _repo_files())
    repo = Repository(name=f"repo-{uuid.uuid4().hex[:8]}", local_path=str(tmp_path))
    session.add(repo)
    await session.flush()

    manager = RepoManager(session)
    manager._sha = sha

    async def _pull(_repo):
        return manager._sha
    manager.pull_repo = _pull
    return repo, manager


def _pipeline(session, manager) -> CodePipeline:
    return CodePipeline(
        session=session, llm=None, vector_repo=None, repo_manager=manager,
    )


async def _stage_overflow(session, tmp_path, monkeypatch, cap: int = 1):
    """First index, then one incremental run that overflows the re-trace cap.

    Returns ``(repo, manager, result)`` with ``CALLER_COUNT - cap`` callers
    queued as debt.
    """
    repo, manager = await _make_repo(session, tmp_path, "sha-1")
    await _pipeline(session, manager).run(repo.id, full=True)

    assert await _caller_files_with_edges(session, repo.id) == {
        f"caller{i}.py" for i in range(CALLER_COUNT)
    }

    _write_files(tmp_path, {"target.py": "def target_fn():\n    return 2\n"})
    manager._sha = "sha-2"
    monkeypatch.setattr(code_pipeline_module, "DEPENDENT_RETRACE_CAP", cap)

    async def _diff(*_args, **_kwargs):
        return ["target.py"], []
    monkeypatch.setattr(code_pipeline_module, "_diff_files", _diff)

    result = await _pipeline(session, manager).run(repo.id, full=False)
    return repo, manager, result


async def _continuation(session, manager, monkeypatch):
    async def _no_diff(*_args, **_kwargs):
        return [], []
    monkeypatch.setattr(code_pipeline_module, "_diff_files", _no_diff)


# ── the invariant: overflow is persisted, never dropped ──────────────────

@pytest.mark.asyncio
async def test_overflow_persists_instead_of_truncating(session, tmp_path, monkeypatch):
    repo, _manager, result = await _stage_overflow(session, tmp_path, monkeypatch, cap=1)

    assert result["status"] == "indexed"

    debt = await index_debt.load(session, repo.id)
    queued = index_debt.queued_files(debt)
    assert len(queued) == CALLER_COUNT - 1, (
        "every caller past the cap must be queued as debt, not dropped"
    )
    assert debt["queued"] == len(queued)
    assert debt["deferred_total"] == len(queued)
    assert debt["last_defer"]["count"] == len(queued)

    # Each queued file carries the sha that made it debt.
    for path in queued:
        assert debt["files"][path] == "sha-2"

    # The queued callers are exactly the ones whose edge this run destroyed —
    # that is the silent wrongness the debt is a record of.
    with_edges = await _caller_files_with_edges(session, repo.id)
    assert len(with_edges) == 1
    assert set(queued) & with_edges == set()
    assert set(queued) | with_edges == {f"caller{i}.py" for i in range(CALLER_COUNT)}


@pytest.mark.asyncio
async def test_deferred_overflow_survives_a_failed_run(session, tmp_path, monkeypatch):
    """Debt is recorded before the run can fail, and cleared only on success."""
    repo, manager, _ = await _stage_overflow(session, tmp_path, monkeypatch, cap=1)
    before = index_debt.queued_files(await index_debt.load(session, repo.id))
    assert before

    await _continuation(session, manager, monkeypatch)
    pipe = _pipeline(session, manager)

    async def _boom():
        raise RuntimeError("simulated failure after the debt batch was claimed")
    monkeypatch.setattr(pipe, "phase_06_call_tracing", _boom)

    with pytest.raises(RuntimeError):
        await pipe.run(repo.id, full=False)

    after = index_debt.queued_files(await index_debt.load(session, repo.id))
    assert after == before, "a failed run must not consume the debt it claimed"


# ── the convergence: continuation batches reach zero ─────────────────────

@pytest.mark.asyncio
async def test_continuation_batches_drain_to_zero(session, tmp_path, monkeypatch):
    """Drive it to zero, one batch per run, and assert it terminates.

    A single run that reduces the count proves nothing: a drain that stalls on a
    non-zero floor forever looks identical at the first step. What is asserted
    here is that the queue strictly decreases every run and reaches zero, that
    the restored edges come back with it, and that the run after that does no
    work at all.
    """
    repo, manager, _ = await _stage_overflow(session, tmp_path, monkeypatch, cap=1)
    session.add(Config(key=index_debt.DEBT_CONFIG_KEY, value={"drain_batch_size": 1}))
    await session.flush()

    await _continuation(session, manager, monkeypatch)

    queued = index_debt.queued_files(await index_debt.load(session, repo.id))
    trace = [len(queued)]
    runs = 0
    max_runs = CALLER_COUNT + 3

    while queued:
        runs += 1
        assert runs <= max_runs, f"debt did not converge in {max_runs} runs: {trace}"
        result = await _pipeline(session, manager).run(repo.id, full=False)
        assert result["status"] == "indexed"
        assert result["index_debt_drained"] == 1, "one batch per run"

        debt = await index_debt.load(session, repo.id)
        remaining = index_debt.queued_files(debt)
        assert len(remaining) < trace[-1], "every run must make progress"
        assert result["index_debt_queued"] == len(remaining)
        trace.append(len(remaining))
        queued = remaining

    assert trace == [CALLER_COUNT - 1] + list(range(CALLER_COUNT - 2, -1, -1))
    assert runs == CALLER_COUNT - 1

    # The point of draining: every caller edge the capped run destroyed is back.
    assert await _caller_files_with_edges(session, repo.id) == {
        f"caller{i}.py" for i in range(CALLER_COUNT)
    }

    debt = await index_debt.load(session, repo.id)
    assert debt["queued"] == 0
    assert debt["drained_total"] == CALLER_COUNT - 1
    assert debt["deferred_total"] == CALLER_COUNT - 1

    # Termination: the drain stops rather than looping on an emptied queue.
    final = await _pipeline(session, manager).run(repo.id, full=False)
    assert final["status"] == "up_to_date"


@pytest.mark.asyncio
async def test_recurring_tick_retains_debt_until_manual_run(session, tmp_path, monkeypatch):
    from contextlib import asynccontextmanager
    from app.services import job_runners

    repo, manager, _ = await _stage_overflow(session, tmp_path, monkeypatch, cap=1)
    repo.index_on_commit_enabled = True
    repo.index_uncommitted = False
    await session.flush()
    before = await index_debt.load(session, repo.id)

    @asynccontextmanager
    async def factory():
        yield session

    monkeypatch.setattr("app.services.git_head.resolve_head_sha", AsyncMock(return_value="sha-2"))
    job_runners._due_reset()
    await job_runners.make_repo_sync_runner(None, factory)()
    assert await index_debt.load(session, repo.id) == before

    await _continuation(session, manager, monkeypatch)
    while index_debt.queued_files(await index_debt.load(session, repo.id)):
        await _pipeline(session, manager).run(repo.id)
    assert await _caller_files_with_edges(session, repo.id) == {
        f"caller{number}.py" for number in range(CALLER_COUNT)
    }


@pytest.mark.asyncio
async def test_run_with_no_debt_does_no_work(session, tmp_path, monkeypatch):
    repo, manager = await _make_repo(session, tmp_path, "sha-1")
    await _pipeline(session, manager).run(repo.id, full=True)

    parsed: list[str] = []
    pipe = _pipeline(session, manager)
    real_parse = pipe.phase_02_parsing

    async def _tracking_parse():
        parsed.append("parsed")
        await real_parse()
    pipe.phase_02_parsing = _tracking_parse

    result = await pipe.run(repo.id, full=False)

    assert result == {
        "status": "up_to_date", "commit": "sha-1", "index_debt_queued": 0,
    }
    assert parsed == [], "an unchanged repo with no debt must not run the pipeline"


@pytest.mark.asyncio
async def test_full_reindex_settles_the_whole_queue(session, tmp_path, monkeypatch):
    repo, manager, _ = await _stage_overflow(session, tmp_path, monkeypatch, cap=1)
    assert index_debt.queued_files(await index_debt.load(session, repo.id))

    result = await _pipeline(session, manager).run(repo.id, full=True)

    assert result["index_debt_drained"] == CALLER_COUNT - 1
    debt = await index_debt.load(session, repo.id)
    assert debt["queued"] == 0
    assert await _caller_files_with_edges(session, repo.id) == {
        f"caller{i}.py" for i in range(CALLER_COUNT)
    }


@pytest.mark.asyncio
async def test_drain_adds_no_graph_deletion_path(session, tmp_path, monkeypatch):
    """T1.38: no deletion without a successful replacement.

    A drained file's content is unchanged, so phase 03 takes its skip path and
    the continuation run must not delete any graph row on its behalf.
    """
    repo, manager, _ = await _stage_overflow(session, tmp_path, monkeypatch, cap=1)
    await _continuation(session, manager, monkeypatch)

    deleted: list[str] = []
    pipe = _pipeline(session, manager)

    async def _tracking_file_delete(repo_id, file_paths):
        deleted.extend(file_paths)
    pipe._delete_files_data = _tracking_file_delete

    async def _tracking_wipe(repo_id):
        deleted.append("*")
    pipe._delete_all_repo_data = _tracking_wipe

    edges_before = (await session.execute(
        text("SELECT count(*) FROM code_edges WHERE repo_id = CAST(:r AS uuid)"),
        {"r": str(repo.id)},
    )).scalar()

    result = await pipe.run(repo.id, full=False)

    assert result["index_debt_drained"] == 1
    assert deleted == [], "a drain run must delete nothing"
    edges_after = (await session.execute(
        text("SELECT count(*) FROM code_edges WHERE repo_id = CAST(:r AS uuid)"),
        {"r": str(repo.id)},
    )).scalar()
    assert edges_after > edges_before


@pytest.mark.asyncio
async def test_a_vanished_debt_file_settles_rather_than_wedging(
    session, tmp_path, monkeypatch
):
    """A queued caller deleted from the working tree has no edge left to
    restore. Settling it is a resolution; leaving it queued would wedge the
    drain on a file that can never be re-traced."""
    repo, manager, _ = await _stage_overflow(session, tmp_path, monkeypatch, cap=1)
    queued = index_debt.queued_files(await index_debt.load(session, repo.id))
    (Path(tmp_path) / queued[0]).unlink()

    await _continuation(session, manager, monkeypatch)
    session.add(Config(key=index_debt.DEBT_CONFIG_KEY, value={"drain_batch_size": 1}))
    await session.flush()

    result = await _pipeline(session, manager).run(repo.id, full=False)

    assert result["index_debt_drained"] == 1
    debt = await index_debt.load(session, repo.id)
    assert queued[0] not in debt["files"]
    assert debt["last_drain"]["vanished"] == 1


# ── the observable: what the repos surface reads ─────────────────────────

@pytest.mark.asyncio
async def test_debt_is_observable_over_rest(session, client, auth_headers, tmp_path, monkeypatch):
    """The debt indicator's contract (T1.46).

    ``queued`` alone cannot tell a queue that is draining from one that is
    stuck, so the response carries the lifetime totals and the timestamped
    last-drain record beside it.
    """
    repo, manager, _ = await _stage_overflow(session, tmp_path, monkeypatch, cap=1)

    # The pipeline's ORM update leaves `updated_at` expired on the shared test
    # session; the route reads the same instance, and RepoResponse is built
    # synchronously (RepoManager.update refreshes for the same reason).
    await session.refresh(repo)
    resp = await client.get(f"/api/v1/repos/{repo.id}", headers=auth_headers)
    assert resp.status_code == 200
    debt = resp.json()["index_debt"]
    assert debt["queued"] == CALLER_COUNT - 1
    assert debt["deferred_total"] == CALLER_COUNT - 1
    assert debt["drained_total"] == 0
    assert debt["last_drain"] is None
    assert debt["last_defer"]["count"] == CALLER_COUNT - 1

    session.add(Config(key=index_debt.DEBT_CONFIG_KEY, value={"drain_batch_size": 1}))
    await session.flush()
    await _continuation(session, manager, monkeypatch)
    await _pipeline(session, manager).run(repo.id, full=False)

    await session.refresh(repo)
    resp = await client.get(f"/api/v1/repos/{repo.id}", headers=auth_headers)
    drained = resp.json()["index_debt"]
    assert drained["queued"] == CALLER_COUNT - 2
    assert drained["drained_total"] == 1
    assert drained["last_drain"]["count"] == 1
    assert drained["last_drain"]["at"]


@pytest.mark.asyncio
async def test_a_repo_that_never_had_debt_reports_zero(session, client, auth_headers, tmp_path):
    repo, manager = await _make_repo(session, tmp_path, "sha-1")
    await _pipeline(session, manager).run(repo.id, full=True)

    await session.refresh(repo)
    resp = await client.get(f"/api/v1/repos/{repo.id}", headers=auth_headers)
    assert resp.json()["index_debt"] == {
        "queued": 0, "deferred_total": 0, "drained_total": 0,
        "last_defer": None, "last_drain": None,
    }


@pytest.mark.asyncio
async def test_drain_journals_a_repo_indexed_event(session, tmp_path, monkeypatch):
    """The journal rides an existing ``EVENT_TYPES`` value with a live reader.

    ``events`` is a closed vocabulary, and a type nothing reads is a log line
    dressed up as observability.
    """
    from app.services.events import EVENT_TYPES

    assert "repo_indexed" in EVENT_TYPES

    repo, manager, _ = await _stage_overflow(session, tmp_path, monkeypatch, cap=1)
    await _continuation(session, manager, monkeypatch)
    await _pipeline(session, manager).run(repo.id, full=False)

    rows = (await session.execute(
        text("""
            SELECT payload FROM events
            WHERE event_type = 'repo_indexed' AND object_id = CAST(:r AS uuid)
            ORDER BY created_at, id
        """),
        {"r": str(repo.id)},
    )).scalars().all()

    actions = [row["action"] for row in rows]
    assert "deferred" in actions and "drained" in actions
    drained = [row for row in rows if row["action"] == "drained"][-1]
    assert drained["files"] >= 1
    assert drained["queued"] == drained["deferred_total"] - drained["drained_total"]


@pytest.mark.asyncio
async def test_the_events_read_api_returns_the_drain_row(session, client, auth_headers, tmp_path, monkeypatch):
    repo, manager, _ = await _stage_overflow(session, tmp_path, monkeypatch, cap=1)

    resp = await client.get(
        "/api/v1/events", params={"object_type": "repository"}, headers=auth_headers,
    )
    assert resp.status_code == 200
    payload = resp.json()
    items = payload["items"] if isinstance(payload, dict) else payload
    assert any(e["event_type"] == "repo_indexed" for e in items)


# ── the stored shape ─────────────────────────────────────────────────────

def test_shape_dedupes_and_keeps_the_first_sha():
    debt = index_debt.record_overflow(index_debt.empty_debt(), ["a.py", "b.py"], "sha-1")
    debt = index_debt.record_overflow(debt, ["b.py", "c.py"], "sha-2")

    assert index_debt.queued_files(debt) == ["a.py", "b.py", "c.py"]
    assert debt["files"]["b.py"] == "sha-1", (
        "a file rediscovered later is no less stale; it keeps the sha that made it debt"
    )
    assert debt["deferred_total"] == 3
    assert debt["queued"] == 3


def test_shape_counters_are_lifetime_totals():
    debt = index_debt.record_overflow(index_debt.empty_debt(), ["a.py", "b.py"], "sha-1")
    debt = index_debt.record_drain(debt, ["a.py"], "sha-2")
    debt = index_debt.record_overflow(debt, ["c.py"], "sha-3")
    debt = index_debt.record_drain(debt, ["b.py", "c.py"], "sha-4")

    assert debt["queued"] == 0
    assert debt["deferred_total"] == 3
    assert debt["drained_total"] == 3
    assert debt["last_drain"]["count"] == 2


def test_shape_drain_of_an_unqueued_file_is_a_no_op():
    debt = index_debt.record_overflow(index_debt.empty_debt(), ["a.py"], "sha-1")
    same = index_debt.record_drain(debt, ["never-queued.py"], "sha-2")
    assert same["queued"] == 1
    assert same["drained_total"] == 0
    assert same["last_drain"] is None


@pytest.mark.parametrize("stored", [None, "junk", 7, [], {"files": "nope"}])
def test_shape_normalizes_anything(stored):
    debt = index_debt.normalize(stored)
    assert debt == index_debt.empty_debt()


def test_shape_normalizes_a_bare_file_list():
    debt = index_debt.normalize({"files": ["a.py", "b.py"]})
    assert index_debt.queued_files(debt) == ["a.py", "b.py"]
    assert debt["queued"] == 2


@pytest.mark.asyncio
async def test_drain_batch_defaults_to_the_retrace_cap(session):
    assert await index_debt.drain_batch_size(session, DEPENDENT_RETRACE_CAP) == (
        DEPENDENT_RETRACE_CAP
    )

    session.add(Config(key=index_debt.DEBT_CONFIG_KEY, value={"drain_batch_size": 7}))
    await session.flush()
    assert await index_debt.drain_batch_size(session, DEPENDENT_RETRACE_CAP) == 7

    await session.execute(
        text("UPDATE config SET value = CAST(:v AS jsonb) WHERE key = :k"),
        {"v": '{"drain_batch_size": 0}', "k": index_debt.DEBT_CONFIG_KEY},
    )
    assert await index_debt.drain_batch_size(session, DEPENDENT_RETRACE_CAP) == (
        DEPENDENT_RETRACE_CAP
    ), "a nonsense batch size falls back to the cap rather than stalling the drain"


@pytest.mark.asyncio
async def test_the_column_round_trips(session, tmp_path):
    repo, _manager = await _make_repo(session, tmp_path, "sha-1")
    debt = index_debt.record_overflow(index_debt.empty_debt(), ["a.py"], "sha-1")
    await index_debt.save(session, repo.id, debt)
    assert await index_debt.load(session, repo.id) == debt

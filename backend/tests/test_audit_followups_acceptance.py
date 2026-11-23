"""Acceptance tests for the audit-followups spec, written from its acceptance text."""
from __future__ import annotations

import ast
import gzip
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
BASE = "cee4bf42"
REGISTER = REPO / "docs/dforge/registers/2026-11-20-audit-remaining.md"
REGISTER_TOOL = Path("/root/.claude-alt/plugins/cache/darkraise/dforge/5.1.1/scripts/register")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


# ------------------------------------------------------------------ A22


@pytest.mark.parametrize("host", ["127.0.0.2", "[::1]", "0.0.0.0", "127.0.0.1", "localhost"])
def test_a22_e2e_reset_refuses_every_loopback_and_unspecified_host_on_5432(host):
    sys.path.insert(0, str(BACKEND / "scripts" / "e2e"))
    try:
        import e2e_db
    finally:
        sys.path.pop(0)
    url = f"postgresql+asyncpg://darkmem:pw@{host}:5432/darkmem_e2e"
    with pytest.raises(e2e_db.NotADisposableDatabase):
        e2e_db.assert_disposable_target(url)
    # the same host off the production port is a disposable target
    e2e_db.assert_disposable_target(f"postgresql+asyncpg://darkmem:pw@{host}:5433/darkmem_e2e")


def test_a22_e2e_database_defaults_to_darkmem_e2e_and_gate_names_it():
    env = {k: v for k, v in os.environ.items() if k not in {"TEST_DATABASE_URL", "DATABASE_URL"}}
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, 'scripts/e2e'); import e2e_db; print(e2e_db.TEST_DATABASE_URL)"],
        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().rsplit("/", 1)[-1] == "darkmem_e2e"

    gate = (REPO / "scripts/gate.sh").read_text()
    leg = gate[gate.index("API e2e suite"):]
    leg = leg[: leg.index("run_e2e.py")]
    assert "darkmem_e2e" in leg


# ------------------------------------------------------------------ A23

DUMP_TAIL = "--\n-- PostgreSQL database dump complete\n--\n\n"
OTHER_DATABASE_BODY = "--\n-- PostgreSQL database dump\n--\n\nCREATE TABLE public.notes (id uuid);\n\n"
GOOD_BODY = (
    "--\n-- PostgreSQL database dump\n--\n\nCREATE TABLE public.memories (id uuid);\n\n"
    "COPY public.alembic_version (version_num) FROM stdin;\n0006\n\\.\n\n"
)


def test_a23_backup_keeps_newest_three_suspect_dumps_and_touches_no_real_dump(tmp_path):
    from tests.test_backup_script import _run_backup, _stub

    dest = tmp_path / "backups"
    dest.mkdir()
    real = []
    for i in range(2):
        d = dest / f"darkmem-2019010{i + 1}-000000.sql.gz"
        d.write_bytes(gzip.compress((GOOD_BODY + DUMP_TAIL).encode()))
        os.utime(d, (1000 + i, 1000 + i))
        real.append(d)
    before = {d: (d.read_bytes(), d.stat().st_mtime) for d in real}
    seeded = []
    for i in range(6):
        s = dest / f"darkmem-202002{i + 1:02d}-000000.sql.gz.suspect"
        s.write_bytes(gzip.compress(OTHER_DATABASE_BODY.encode()))
        os.utime(s, (5000 + i, 5000 + i))
        seeded.append(s)
    wrong = _stub(tmp_path, "compose-wrong.sh", f"cat <<'SQL'\n{OTHER_DATABASE_BODY}{DUMP_TAIL}SQL\n")

    result = _run_backup(dest, wrong, keep="14")

    assert result.returncode != 0
    suspects = sorted(dest.glob("*.suspect"))
    new = [s for s in suspects if s not in seeded]
    assert len(suspects) == 3
    assert len(new) == 1
    assert set(suspects) == {*new, *seeded[-2:]}
    assert {d: (d.read_bytes(), d.stat().st_mtime) for d in real} == before


def test_a23_restore_cycle_whose_migrate_overruns_swaps_nothing_and_exits_non_zero(tmp_path):
    from tests.test_restore_cycle_script import _calls, _run

    result, records, elapsed = _run(
        tmp_path, migrate="exec sleep 60", probe="exit 0", env={"RESTORE_MIGRATE_TIMEOUT": "2"}
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert elapsed < 25
    assert not _calls(records, "RENAME")


# ------------------------------------------------------------------ A35


def test_a35_declared_context_is_gone_from_both_doors_and_both_sdks():
    from app.main import app
    from app.schemas.memory import MemorySearchRequest

    assert "context" not in MemorySearchRequest.model_fields
    doc = json.dumps(app.openapi()).lower()
    assert "x-darkmem-context" not in doc

    from app.schemas import envelope

    assert not hasattr(envelope, "ContextEcho")
    assert "context" not in envelope.ResponseEnvelope.model_fields

    assert not (BACKEND / "app/api/context_resolution.py").exists()
    mcp_src = (BACKEND / "app/api/mcp/server.py").read_text().lower()
    assert "x-darkmem-context" not in mcp_src

    ts = (REPO / "sdks/ts/src/client.ts").read_text()
    py = (REPO / "sdks/python/darkmem_sdk/client.py").read_text()
    for text in (ts, py):
        low = text.lower()
        assert "declarecontext" not in low
        assert "declare_context" not in low
        assert "x-darkmem-context" not in low

    for path in (BACKEND / "app").rglob("*.py"):
        assert "x-darkmem-context" not in path.read_text().lower(), path


# ------------------------------------------------------------------ A36


def test_a36_no_revision_route_or_mcp_tool_is_added():
    out = subprocess.run(
        [sys.executable, "-m", "alembic", "heads", "--verbose"], cwd=BACKEND, capture_output=True, text=True, timeout=120
    )
    assert out.returncode == 0, out.stderr
    heads = re.findall(r"^Rev: (\S+) \(head\)", out.stdout, re.M)
    assert heads == ["0006"]
    assert "0006_drop_blocks_search_vector.py" in out.stdout

    added = _git("diff", "--diff-filter=A", "--name-only", BASE, "HEAD", "--", "backend/migrations/versions").split()
    assert added == []

    # no route or tool decorator is added anywhere under the doors
    diff = _git("diff", "-U0", BASE, "HEAD", "--", "backend/app/api", "backend/app/main.py")
    added_decorators = [
        line for line in diff.splitlines()
        if re.match(r"^\+\s*@(router|app|mcp|server)\.(get|post|put|patch|delete|tool|websocket)\b", line)
    ]
    assert added_decorators == []

    from app.api.mcp.scopes import TOOL_SCOPES

    base_src = _git("show", f"{BASE}:backend/app/api/mcp/scopes.py")
    namespace = {"__name__": "app.api.mcp._base_scopes", "__package__": "app.api.mcp"}
    exec(compile(base_src, "base_scopes.py", "exec"), namespace)
    base_tools = set(namespace["TOOL_SCOPES"])
    assert set(TOOL_SCOPES) == base_tools
    assert len(TOOL_SCOPES) == 46


# ------------------------------------------------------------------ A37


def test_a37_register_check_passes_and_no_row_is_open_planned_or_doing():
    out = subprocess.run(
        ["bash", str(REGISTER_TOOL), "check", str(REGISTER)], cwd=REPO, capture_output=True, text=True, timeout=120
    )
    assert out.returncode == 0, out.stdout + out.stderr
    assert " 0 errors" in out.stdout

    header = None
    states = []
    for line in REGISTER.read_text().splitlines():
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells[0] == "#":
            header = cells
            continue
        if header:
            states.append((cells[0], cells[header.index("State")]))
    assert len(states) >= 413 - 1
    assert [row for row, state in states if state in {"open", "planned", "doing"}] == []


# ================================================================== backend DB groups

import asyncio  # noqa: E402
import contextlib  # noqa: E402
import copy  # noqa: E402
import logging  # noqa: E402
import uuid  # noqa: E402

from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import DBAPIError  # noqa: E402

from app.repositories.graph import PostgresGraphRepository  # noqa: E402
from tests.test_pipeline_savepoints import VECTOR, savepoint_bed  # noqa: E402


class _Deadlock(Exception):
    sqlstate = "40P01"
    pgcode = "40P01"


def _entities_only(names):
    return {"entities": [{"name": n, "type": "tool"} for n in names], "relationships": [], "memory_type": "fact"}


# ------------------------------------------------------------------ A1


@pytest.mark.asyncio
async def test_a1_swapped_prior_and_new_sets_both_end_graph_ok_with_no_failure_row(setup_database, monkeypatch):
    names = ("a1-entity-one", "a1-entity-two")
    async with savepoint_bed(["writer a", "writer b"], "a1-swap|4", entity_names=names) as bed:
        for index, prior in enumerate(((names[1],), (names[0],))):
            status = await bed.pipe._write_memory(
                bed.entry(index), VECTOR, bed.fingerprint, bed.fingerprint,
                _entities_only(prior), None, {}, {},
            )
            assert status["graph"] == "ok", status

        holding = {m: asyncio.Event() for m in bed.memory_ids}
        real_strip = PostgresGraphRepository.delete_by_memory_id

        async def strip_then_wait_for_the_other(self, memory_id):
            result = await real_strip(self, memory_id)
            mine = holding[memory_id]
            if not mine.is_set():
                mine.set()
                other = next(e for m, e in holding.items() if m != memory_id)
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(other.wait(), 3)
            return result

        monkeypatch.setattr(PostgresGraphRepository, "delete_by_memory_id", strip_then_wait_for_the_other)

        statuses = await asyncio.gather(*[
            bed.pipe._write_memory(
                bed.entry(i), VECTOR, bed.fingerprint, bed.fingerprint,
                _entities_only(names), None, {}, {},
            )
            for i in range(2)
        ])

        assert [s["graph"] for s in statuses] == ["ok", "ok"], statuses
        async with bed.factory() as s:
            failures = (await s.execute(
                text("SELECT count(*) FROM pipeline_failures WHERE entity_id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(m) for m in bed.memory_ids]},
            )).scalar_one()
        assert failures == 0
        for i in range(2):
            assert await bed.entity_names(i) == set(names)


# ------------------------------------------------------------------ A2


@pytest.mark.asyncio
async def test_a2_three_deadlocks_end_graph_error_vector_kept_prior_graph_intact(setup_database, monkeypatch):
    async with savepoint_bed(["deadlocked writer"], "a2-dead|4") as bed:
        seeded = await bed.pipe._write_memory(
            bed.entry(), VECTOR, bed.fingerprint, bed.fingerprint, dict(bed.extraction), None, {}, {},
        )
        assert seeded["graph"] == "ok", seeded
        prior_entities = await bed.entity_names()
        prior_relations = await bed.relation_types()
        assert prior_entities

        calls = 0

        async def always_deadlocks(self, memory_id):
            nonlocal calls
            calls += 1
            raise DBAPIError("UPDATE entities", {}, _Deadlock("deadlock detected"))

        monkeypatch.setattr(PostgresGraphRepository, "delete_by_memory_id", always_deadlocks)

        status = await bed.pipe._write_memory(
            bed.entry(), VECTOR, bed.fingerprint, bed.fingerprint,
            _entities_only(("a2-new-entity",)), None, {}, {},
        )

        assert status["graph"] == "error", status
        assert calls == 3
        assert await bed.embedding_rows() == 1
        assert await bed.entity_names() == prior_entities
        assert await bed.relation_types() == prior_relations


# ------------------------------------------------------------------ A3


@pytest.mark.asyncio
async def test_a3_delete_losing_one_deadlock_still_removes_graph_and_vectors(setup_database, monkeypatch):
    async with savepoint_bed(["memory to delete"], "a3-del|4") as bed:
        seeded = await bed.pipe._write_memory(
            bed.entry(), VECTOR, bed.fingerprint, bed.fingerprint, dict(bed.extraction), None, {}, {},
        )
        assert seeded["graph"] == "ok", seeded
        assert await bed.embedding_rows() == 1
        assert await bed.entity_names()

        real_strip = PostgresGraphRepository.delete_by_memory_id
        calls = 0

        async def lose_first_deadlock(self, memory_id):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise DBAPIError("UPDATE entities", {}, _Deadlock("deadlock detected"))
            return await real_strip(self, memory_id)

        monkeypatch.setattr(PostgresGraphRepository, "delete_by_memory_id", lose_first_deadlock)

        await bed.pipe.delete_memory(bed.memory_id, broadcast=False)

        assert calls == 2
        assert await bed.embedding_rows() == 0
        assert await bed.entity_names() == set()
        assert await bed.relation_types() == set()


@pytest.mark.asyncio
async def test_a3_delete_whose_source_withdrawal_times_out_still_commits_the_strip(setup_database, monkeypatch):
    import app.services.pipeline as pipeline_module

    async with savepoint_bed(["memory to delete"], "a3-wd|4") as bed:
        seeded = await bed.pipe._write_memory(
            bed.entry(), VECTOR, bed.fingerprint, bed.fingerprint, dict(bed.extraction), None, {}, {},
        )
        assert seeded["graph"] == "ok", seeded
        assert await bed.entity_names()

        class _LockNotAvailable(Exception):
            sqlstate = "55P03"
            pgcode = "55P03"

        async def withdrawal_times_out(*args, **kwargs):
            raise DBAPIError("SELECT ... FOR UPDATE", {}, _LockNotAvailable("lock timeout"))

        monkeypatch.setattr(pipeline_module, "withdraw_memory_sources", withdrawal_times_out)

        await bed.pipe.delete_memory(bed.memory_id, broadcast=False)

        assert await bed.embedding_rows() == 0
        assert await bed.entity_names() == set()
        assert await bed.relation_types() == set()


# ------------------------------------------------------------------ A4 / A5 / A6

from app.config import FEATURE_FLAGS_DEFAULTS  # noqa: E402
from app.models.memory import Memory  # noqa: E402
from app.services.embedder_registry import child_table  # noqa: E402
from app.services.hybrid_search import HybridSearchService  # noqa: E402
from app.services.rank_fusion import RankedList, rrf_fuse  # noqa: E402
from tests.test_hybrid_search import _FakeLLM, _seed_embedding_partition  # noqa: E402

_LOW = uuid.UUID("00000000-0000-4000-8000-0000000000a1")
_HIGH = uuid.UUID("00000000-0000-4000-8000-0000000000b2")


def _rl(name, *ids):
    return RankedList(name=name, rows=[{"memory_id": str(i)} for i in ids], weight=1.0)


def test_a4_rrf_fuse_orders_equal_scores_by_row_key():
    equal = rrf_fuse([_rl("x", _HIGH, _LOW), _rl("y", _LOW, _HIGH)], limit=10)
    assert equal[0]["rrf_score"] == pytest.approx(equal[1]["rrf_score"])
    assert [str(r["memory_id"]) for r in equal] == [str(_LOW), str(_HIGH)]
    flipped = rrf_fuse([_rl("x", _LOW, _HIGH), _rl("y", _HIGH, _LOW)], limit=10)
    assert [str(r["memory_id"]) for r in flipped] == [str(_LOW), str(_HIGH)]


@pytest.mark.asyncio
@pytest.mark.parametrize("hybrid", [True, False])
async def test_a4_identical_memories_return_in_the_same_order_whichever_was_inserted_first(session, hybrid):
    fingerprint = "a4-embedder|4"
    vector = [1.0, 0.0, 0.0, 0.0]
    await _seed_embedding_partition(session, fingerprint, 4)
    child = child_table("memory_embeddings", fingerprint)
    flags = {**FEATURE_FLAGS_DEFAULTS, "hybrid_search_enabled": hybrid}
    svc = HybridSearchService(_FakeLLM(vector, fingerprint), session)

    seen = []
    for order in ((_HIGH, _LOW), (_LOW, _HIGH)):
        await session.execute(
            text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"), {"ids": [str(_LOW), str(_HIGH)]}
        )
        for mem_id in order:
            session.add(Memory(id=mem_id, content="vorpal glimmerstone a4 note", source="test", project="a4-proj"))
            await session.flush()
            await session.execute(
                text(
                    f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
                    "VALUES (:mid, :fp, CAST(:vec AS vector), '{}'::jsonb)"
                ),
                {"mid": mem_id, "fp": fingerprint, "vec": str(vector)},
            )
        await session.flush()
        session.expunge_all()
        for _ in range(4):
            results = await svc.search_ranked("vorpal glimmerstone", flags=flags, limit=10)
            seen.append(tuple(str(r["memory_id"]) for r in results[:2]))
    assert len(set(seen)) == 1, seen
    assert set(seen[0]) == {str(_LOW), str(_HIGH)}


class _DownEmbedder(_FakeLLM):
    def __init__(self):
        super().__init__([1.0, 0.0, 0.0, 0.0], "a5|4")
        self.calls = 0

    async def embed(self, query: str):
        self.calls += 1
        raise ConnectionError("embedder is down")


@pytest.mark.asyncio
async def test_a5_hybrid_off_two_searches_during_an_embedder_outage_make_one_embed_call(session):
    llm = _DownEmbedder()
    flags = {**FEATURE_FLAGS_DEFAULTS, "hybrid_search_enabled": False}
    svc = HybridSearchService(llm, session)
    for _ in range(2):
        with contextlib.suppress(Exception):
            await svc.search_ranked("anything at all", flags=flags, limit=5)
    assert llm.calls == 1


@pytest.mark.asyncio
async def test_a6_neighbour_context_applies_the_limit_after_the_scope_filter(session):
    from app.services.graph import GraphService

    seed = Memory(id=uuid.UUID("00000000-0000-4000-8000-00000000ff00"), content="seed", source="t", project="a6-in")
    session.add(seed)
    neighbours = []
    for i in range(25):
        in_scope = i >= 10
        neighbours.append(Memory(
            id=uuid.UUID(f"00000000-0000-4000-8000-0000000001{i:02x}"),
            content=f"neighbour {i}", source="t", project="a6-in" if in_scope else "a6-out",
        ))
    session.add_all(neighbours)
    await session.flush()
    await session.execute(
        text(
            "INSERT INTO entities (id, name, entity_type, memory_ids) "
            "VALUES (gen_random_uuid(), 'a6-hub', 'tool', CAST(:mids AS uuid[]))"
        ),
        {"mids": [str(seed.id), *[str(n.id) for n in neighbours]]},
    )
    await session.flush()

    svc = GraphService(session, graph_repo=PostgresGraphRepository(session))
    context = await svc.get_memory_context(str(seed.id))

    returned = {n["id"] for n in context["neighbors"]}
    assert returned == {str(n.id) for n in neighbours[10:]}
    assert len(returned) == 15


# ------------------------------------------------------------------ A7


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["detector-raises", "read-raises"])
async def test_a7_reconciliation_raising_leaves_every_extracted_journal_row(setup_database, monkeypatch, failure):
    from contextlib import asynccontextmanager

    import app.services.pipeline as pipeline_module

    if failure == "detector-raises":
        async def boom(*args, **kwargs):
            raise RuntimeError("reconciliation exploded")

        monkeypatch.setattr(pipeline_module, "detect_supersessions", boom)

    async with savepoint_bed(["a7 older", "a7 newer", "a7 newest"], f"a7-{failure}|4") as bed:
        real_factory = bed.pipe.session_factory
        if failure == "read-raises":
            @asynccontextmanager
            async def failing_read_factory():
                async with real_factory() as session:
                    real_execute = session.execute

                    async def execute(statement, *args, **kwargs):
                        if "ORDER BY memories.created_at, memories.id" in str(statement):
                            raise RuntimeError("reconciliation read failed")
                        return await real_execute(statement, *args, **kwargs)

                    session.execute = execute
                    yield session

            bed.pipe.session_factory = failing_read_factory

        results = await bed.pipe.process_batch([bed.entry(i) for i in range(3)])
        assert len(results) == 3

        async with real_factory() as session:
            journalled = (await session.execute(
                text("SELECT object_id FROM events WHERE event_type = 'extracted' AND object_id = ANY(:ids)"),
                {"ids": bed.memory_ids},
            )).scalars().all()
        assert sorted(journalled) == sorted(bed.memory_ids)


# ------------------------------------------------------------------ A8 / A9 / A40

from sqlalchemy import event  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.services import wait_process  # noqa: E402
from tests.test_buffer_flush import RecordingPipeline, buffer_rows, drop_buffer, factory, seed_buffer  # noqa: E402


@pytest.mark.asyncio
async def test_a8_no_pipeline_factory_no_flush_statement_runs_on_the_request_session_after_the_response(
    client, auth_headers, session, monkeypatch
):
    from contextlib import asynccontextmanager

    import app.services.memory as memory_module
    from app.main import app

    opened: list = []
    gate = asyncio.Event()

    @asynccontextmanager
    async def own_sessions():
        own = AsyncSession(bind=session.bind, expire_on_commit=False)
        opened.append(own)
        try:
            if len(opened) == 1:
                await gate.wait()
            yield own
        finally:
            await own.close()

    monkeypatch.setattr(memory_module, "async_session_factory", own_sessions, raising=False)
    monkeypatch.setattr(memory_module, "BUFFER_WAIT_TIMEOUT_SECONDS", 0.2)
    pipeline = RecordingPipeline()
    app.state.pipeline = pipeline
    try:
        response = await client.post(
            "/api/v1/memories?wait_process=true",
            json={"content": "a8 flush with no pipeline factory"},
            headers=auth_headers,
        )
    finally:
        app.state.pipeline = None
    assert response.status_code == 202

    after_response: list[str] = []

    def record(state):
        after_response.append(str(state.statement))

    event.listen(session.sync_session, "do_orm_execute", record)
    try:
        gate.set()
        await asyncio.gather(*wait_process.continuing_flushes())
    finally:
        event.remove(session.sync_session, "do_orm_execute", record)
    assert after_response == []


async def _hang(pipeline):
    async def hangs(entries):
        pipeline.batches.append(list(entries))
        await asyncio.Event().wait()

    pipeline.process_batch = hangs


async def _cleanup_rows(buffer_ids):
    rows = await buffer_rows(buffer_ids)
    ids = [r["metadata"]["memory_id"] for r in rows.values() if r["metadata"].get("memory_id")]
    if ids:
        async with factory()() as s:
            await s.execute(text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"), {"ids": ids})
            await s.commit()
    await drop_buffer(buffer_ids)


@pytest.mark.asyncio
async def test_a9_lone_row_cut_at_its_deadline_is_charged_an_attempt(setup_database, monkeypatch):
    monkeypatch.setattr(wait_process, "BUFFER_FLUSH_DEADLINE_SECONDS", 0.3)
    ids = await seed_buffer(1)
    pipeline = RecordingPipeline()
    await _hang(pipeline)
    try:
        await wait_process.drive(
            factory(), pipeline, buffer_ids=ids, timeout_seconds=0.05, max_attempts=5, poll_interval_seconds=0.01,
        )
        await asyncio.gather(*wait_process.continuing_flushes(), return_exceptions=True)
        row = (await buffer_rows(ids))[ids[0]]
        assert (row["status"], row["attempts"]) == ("pending", 1)
    finally:
        await _cleanup_rows(ids)


@pytest.mark.asyncio
async def test_a9_several_rows_cut_the_same_way_charge_none(setup_database, monkeypatch):
    monkeypatch.setattr(wait_process, "BUFFER_FLUSH_DEADLINE_SECONDS", 0.3)
    ids = await seed_buffer(3)
    pipeline = RecordingPipeline()
    await _hang(pipeline)
    try:
        await wait_process.drive(
            factory(), pipeline, buffer_ids=ids, timeout_seconds=0.05, max_attempts=5, poll_interval_seconds=0.01,
        )
        await asyncio.gather(*wait_process.continuing_flushes(), return_exceptions=True)
        rows = await buffer_rows(ids)
        assert {(r["status"], r["attempts"]) for r in rows.values()} == {("pending", 0)}
    finally:
        await _cleanup_rows(ids)


@pytest.mark.asyncio
async def test_a9_a_flush_cut_at_shutdown_charges_none(setup_database):
    ids = await seed_buffer(1)
    started = asyncio.Event()
    pipeline = RecordingPipeline()

    async def hangs(entries):
        pipeline.batches.append(list(entries))
        started.set()
        await asyncio.Event().wait()

    pipeline.process_batch = hangs
    try:
        await wait_process.drive(
            factory(), pipeline, buffer_ids=ids, timeout_seconds=0.05, max_attempts=5, poll_interval_seconds=0.01,
        )
        await asyncio.wait_for(started.wait(), 5)
        await wait_process.drain_continuing_flushes(grace_seconds=0.05)
        row = (await buffer_rows(ids))[ids[0]]
        assert (row["status"], row["attempts"]) == ("pending", 0)
    finally:
        await _cleanup_rows(ids)


@pytest.mark.asyncio
async def test_a40_a_raising_inline_flush_answers_the_ack_and_logs_the_failure_once(
    client, auth_headers, session, monkeypatch, caplog
):
    from app.main import app
    from app.services.buffer_flush import as_session_factory

    async def exploding(*args, **kwargs):
        raise RuntimeError("a40 claim exploded")

    monkeypatch.setattr(wait_process, "flush_claimed", exploding)
    caplog.set_level(logging.ERROR)
    pipeline = RecordingPipeline()
    pipeline.session_factory = as_session_factory(session)
    app.state.pipeline = pipeline
    try:
        response = await client.post(
            "/api/v1/memories?wait_process=true",
            json={"content": "a40 a flush that raises"},
            headers=auth_headers,
        )
    finally:
        app.state.pipeline = None

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    reports = [
        r for r in caplog.records
        if r.levelno >= logging.ERROR
        and ("a40 claim exploded" in r.getMessage() or (r.exc_info and "a40 claim exploded" in str(r.exc_info[1])))
    ]
    assert len(reports) == 1, [r.getMessage() for r in reports]


# ------------------------------------------------------------------ A10


@pytest.mark.asyncio
async def test_a10_login_refused_only_for_in_flight_attempts_does_not_say_failed(client, session, monkeypatch):
    import threading

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.api.auth import hash_password
    from app.api.routes import auth as auth_routes
    from app.models.config import Config
    from app.services.login_rate_limit import LoginRateLimiter
    from tests.conftest import test_engine

    monkeypatch.setattr(
        auth_routes, "async_session_factory", async_sessionmaker(test_engine, expire_on_commit=False)
    )
    limiter = LoginRateLimiter(max_failures=5, lockout_seconds=300)
    monkeypatch.setattr(auth_routes, "login_rate_limiter", limiter)
    session.add(Config(key="admin_password_hash", value={"hash": hash_password("correct")}))
    await session.commit()

    release = threading.Event()

    def held_verify(password, hashed):
        release.wait(10)
        return False

    monkeypatch.setattr(auth_routes, "verify_password", held_verify)
    held = [
        asyncio.create_task(client.post("/api/v1/auth/login", json={"password": "wrong"})) for _ in range(5)
    ]
    try:
        for _ in range(500):
            if sum(limiter.in_flight(ip) for ip in list(limiter._state)) == 5:
                break
            await asyncio.sleep(0.01)
        refused = await client.post("/api/v1/auth/login", json={"password": "wrong"})
    finally:
        release.set()
        await asyncio.gather(*held)

    assert refused.status_code == 429
    detail = refused.json()["detail"]
    assert "failed login attempts" not in detail
    assert "retry in" in detail


# ------------------------------------------------------------------ A11 / A12

import time  # noqa: E402

import jwt  # noqa: E402

from app.api import websocket  # noqa: E402
from app.api.auth import ALGORITHM  # noqa: E402
from app.config import settings  # noqa: E402
from tests.test_websocket import INTERVAL, _open, _presented, _shut, _token, manager  # noqa: E402,F401


@pytest.mark.asyncio
async def test_a11_a_blocklist_row_written_to_the_database_closes_the_open_socket_after_60_seconds(
    manager, monkeypatch
):
    from datetime import datetime, timezone

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    clock = [1000.0]
    monkeypatch.setattr(websocket, "_now", lambda: clock[0], raising=False)
    token = _token()
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    socket, task = await _open(token)
    try:
        async with factory() as s:
            await s.execute(
                text("INSERT INTO token_blocklist (id, jti, expires_at) VALUES (gen_random_uuid(), :jti, :exp)"),
                {"jti": claims["jti"], "exp": datetime.fromtimestamp(claims["exp"], tz=timezone.utc)},
            )
            await s.commit()
        await asyncio.sleep(INTERVAL * 4)
        assert not socket.closed.is_set()

        clock[0] += 61
        await asyncio.wait_for(socket.closed.wait(), 3)
    finally:
        await _shut(task)
        async with factory() as s:
            await s.execute(text("DELETE FROM token_blocklist WHERE jti = :jti"), {"jti": claims["jti"]})
            await s.commit()


@pytest.mark.asyncio
async def test_a12_cancelling_a_refresh_while_it_waits_to_close_sockets_leaves_the_token_not_renewed(
    manager, client, auth_headers
):
    presented = _presented(auth_headers)
    jti = jwt.decode(presented, settings.jwt_secret, algorithms=[ALGORITHM])["jti"]
    socket, task = await _open(presented)
    try:
        async with manager._send_lock:
            answer = asyncio.create_task(client.post("/api/v1/auth/refresh", headers=auth_headers))
            for _ in range(200):
                if jti in websocket.session_revocations._renewed:
                    break
                await asyncio.sleep(0.01)
            answer.cancel()
            await asyncio.gather(answer, return_exceptions=True)
        assert jti not in websocket.session_revocations._renewed
        assert not socket.closed.is_set()
    finally:
        await _shut(task)


# ------------------------------------------------------------------ A13

import app.services.mcp_call_log as mcp_call_log  # noqa: E402


@pytest.fixture
def _call_log(monkeypatch):
    monkeypatch.setattr(mcp_call_log, "_auto_flush", False)
    mcp_call_log._reset_for_tests()
    yield
    mcp_call_log._reset_for_tests()


def _queue_calls(n: int, tool: str) -> None:
    for _ in range(n):
        mcp_call_log.record_call(
            tool=tool, scope="read", status="ok", duration_ms=1,
            api_key_id=None, key_name=None, client=None, arguments={},
        )


class _FailingSessions:
    def __init__(self, factory, on_execute):
        self.factory = factory
        self.on_execute = on_execute

    def __call__(self):
        session = self.factory()
        real = session.execute

        async def execute(statement, *args, **kwargs):
            if "mcp_tool_calls" in str(statement):
                await self.on_execute()
            return await real(statement, *args, **kwargs)

        session.execute = execute
        return session


@pytest.mark.asyncio
async def test_a13_a_pool_timeout_at_the_insert_leaves_the_batch_in_the_buffer(setup_database, _call_log):
    from sqlalchemy.exc import TimeoutError as PoolTimeout
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    tool = f"a13-pool-{uuid.uuid4().hex[:8]}"
    _queue_calls(5, tool)

    async def pool_exhausted():
        raise PoolTimeout("QueuePool limit reached, connection timed out")

    factory = _FailingSessions(async_sessionmaker(test_engine, expire_on_commit=False), pool_exhausted)
    assert await mcp_call_log.flush_once(factory) == 0
    assert len(mcp_call_log._buffer) == 5
    assert all(p.tool == tool for p in mcp_call_log._buffer)
    assert mcp_call_log.dropped_calls() == 0


@pytest.mark.asyncio
async def test_a13_a_cancelled_flush_leaves_the_batch_in_the_buffer(setup_database, _call_log):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    tool = f"a13-cancel-{uuid.uuid4().hex[:8]}"
    _queue_calls(5, tool)
    inserting = asyncio.Event()

    async def hang():
        inserting.set()
        await asyncio.Event().wait()

    factory = _FailingSessions(async_sessionmaker(test_engine, expire_on_commit=False), hang)
    task = asyncio.create_task(mcp_call_log.flush_once(factory))
    await asyncio.wait_for(inserting.wait(), timeout=10)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(mcp_call_log._buffer) == 5
    assert all(p.tool == tool for p in mcp_call_log._buffer)
    assert mcp_call_log.dropped_calls() == 0


# ------------------------------------------------------------------ A14 - A17

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402

import app.services.repo_manager as repo_manager_module  # noqa: E402
from app.models.code import Repository  # noqa: E402
from app.services.repo_manager import RepoManager  # noqa: E402


@pytest.mark.asyncio
async def test_a14_a_failed_clone_of_a_url_with_a_token_leaks_it_to_no_log_row_or_payload(
    session, session_factory, tmp_path, monkeypatch, caplog
):
    from app.api.routes import repos as repos_route
    from app.api.websocket import event_manager
    from app.services.code_pipeline import CodePipeline

    secret = "tok-A14-5e1f0a9c"
    base = tmp_path / "clones"
    base.mkdir()
    monkeypatch.setattr(repo_manager_module, "REPOS_BASE_DIR", base)
    repo = Repository(
        name=f"a14-{uuid.uuid4().hex[:6]}",
        url=f"https://u:{secret}@127.0.0.1:9/o/r.git",
        default_branch="main", provider="github", status="indexing",
    )
    session.add(repo)
    await session.flush()

    broadcasts: list = []

    async def record(event_type, data):
        broadcasts.append((event_type, data))

    monkeypatch.setattr(event_manager, "broadcast", record)
    caplog.set_level(logging.DEBUG)

    await repos_route._spawn_repo_index(
        repo.id, CodePipeline(session, None, None, RepoManager(session)), session_factory, kind="reindex",
    )

    row = (await session.execute(
        select(Repository.status, Repository.status_message).where(Repository.id == repo.id)
    )).one()
    assert row.status == "error", row
    assert secret not in (row.status_message or "")
    assert secret not in repr(broadcasts)
    assert secret not in caplog.text
    assert secret not in "".join(str(r.exc_text or "") + str(r.getMessage()) for r in caplog.records)


@pytest.mark.parametrize(
    "url, origin",
    [
        ("https://git.lan:8443/o/r.git", "https://git.lan:8443/"),
        ("https://github.com/o/r.git", "https://github.com/"),
    ],
)
def test_a15_the_git_auth_header_is_scoped_to_the_origin_port_included(url, origin):
    env = RepoManager._auth_env("T", "github", url=url)
    keys = [v for k, v in env.items() if k.startswith("GIT_CONFIG_KEY_")]
    assert keys == [f"http.{origin}.extraHeader"]
    assert "http.extraHeader" not in keys
    assert int(env["GIT_CONFIG_COUNT"]) == 1


async def _managed_clone(session, tmp_path, monkeypatch):
    base = tmp_path / "clones"
    base.mkdir()
    monkeypatch.setattr(repo_manager_module, "REPOS_BASE_DIR", base)
    upstream = tmp_path / "upstream"
    upstream.mkdir()

    def git(cwd, *args):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True, capture_output=True)

    git(upstream, "init", "-q", "-b", "main")
    (upstream / "a.py").write_text("x = 1\n")
    git(upstream, "add", "a.py")
    git(upstream, "commit", "-qm", "init")
    repo = Repository(
        name=f"a16-{uuid.uuid4().hex[:6]}", url="https://example.invalid/o/r.git",
        default_branch="main", provider="github", status="ready",
    )
    session.add(repo)
    await session.flush()
    clone = base / str(repo.id)
    git(tmp_path, "clone", "-q", str(upstream), str(clone))
    return repo, clone


@pytest.mark.asyncio
async def test_a16_a_reclone_that_raises_leaves_the_repository_error_and_its_claim_released(
    setup_database, tmp_path, monkeypatch
):
    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as own:
        repo, clone = await _managed_clone(own, tmp_path, monkeypatch)
        await own.commit()
        repo_id = repo.id
        try:
            (clone / ".git" / "HEAD").unlink()

            async def failing_clone(self, _repo):
                await self.session.execute(select(Repository.id).where(Repository.id == _repo.id))
                raise RuntimeError("clone failed")

            monkeypatch.setattr(RepoManager, "_clone_repo", failing_clone)
            with pytest.raises(RuntimeError, match="clone failed"):
                await RepoManager(own).pull_repo(repo, take_claim=True)

            status = (await own.execute(select(Repository.status).where(Repository.id == repo_id))).scalar_one()
            assert status == "error"
            assert await RepoManager(own).claim_for_indexing(repo_id, message="next run")
        finally:
            await own.rollback()
            await own.execute(delete(Repository).where(Repository.id == repo_id))
            await own.commit()


@pytest.mark.asyncio
async def test_a16_a_cancelled_reclone_restores_the_prior_status(session, tmp_path, monkeypatch):
    repo, clone = await _managed_clone(session, tmp_path, monkeypatch)
    (clone / ".git" / "HEAD").unlink()
    cloning = asyncio.Event()

    async def hanging_clone(self, _repo):
        cloning.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(RepoManager, "_clone_repo", hanging_clone)
    task = asyncio.create_task(RepoManager(session).pull_repo(repo, take_claim=True))
    await asyncio.wait_for(cloning.wait(), timeout=10)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    status = (await session.execute(select(Repository.status).where(Repository.id == repo.id))).scalar_one()
    assert status == "ready"


@pytest.mark.asyncio
async def test_a17_raising_the_deriver_version_rederives_a_repository_whose_head_has_not_moved(
    session, session_factory, monkeypatch
):
    from app.services import code_deriver
    from app.services import code_deriver_job
    from app.services.job_runners import make_code_deriver_runner

    repo = Repository(name=f"a17-{uuid.uuid4().hex[:8]}", status="ready", last_indexed_commit="sha-a17")
    session.add(repo)
    await session.flush()
    derived: list = []

    async def spy(repo_session, repo_id):
        derived.append(repo_id)
        return {"entities": 0, "relations": 0}

    monkeypatch.setattr(code_deriver, "assert_repo_graph", spy)
    runner = make_code_deriver_runner(session_factory)

    await runner()
    assert derived.count(repo.id) == 1
    await runner()
    assert derived.count(repo.id) == 1, "unchanged HEAD and version must not re-derive"

    monkeypatch.setattr(code_deriver_job, "CODE_DERIVER_VERSION", code_deriver_job.CODE_DERIVER_VERSION + 1)
    await runner()
    assert derived.count(repo.id) == 2


@pytest.mark.asyncio
async def test_a17_a_deriver_tick_that_derived_nothing_triggers_no_code_reconcile(session, monkeypatch):
    import app.services.fact_lift as fact_lift_module

    reconciles: list = []
    real = fact_lift_module.reconcile_code_sources

    async def counting(s):
        reconciles.append(1)
        return await real(s)

    monkeypatch.setattr(fact_lift_module, "reconcile_code_sources", counting)
    await fact_lift_module.run_code_lift(session)
    reconciles.clear()
    await session.execute(text(
        "INSERT INTO job_runs (job_key, outcome, started_at, duration_seconds) "
        "VALUES ('code_deriver', 'ok', clock_timestamp(), 0)"
    ))
    await fact_lift_module.run_code_lift(session)
    await fact_lift_module.run_code_lift(session)
    assert reconciles == []


# ------------------------------------------------------------------ A18

from uuid import UUID  # noqa: E402

from app.services import fact_lift  # noqa: E402
from app.services.fact_lift import run_lift  # noqa: E402
from tests.conftest import test_engine as _engine  # noqa: E402
from tests.test_fact_lift import assert_relation, facts, seed_memory  # noqa: E402


@pytest.mark.asyncio
async def test_a18_a_lift_meeting_a_fact_lock_held_past_its_deadline_defers_and_finishes(
    setup_database, monkeypatch
):
    monkeypatch.setattr(fact_lift, "MEMORY_LOCK_WAIT_SECONDS", 0.3)
    factory = async_sessionmaker(_engine, expire_on_commit=False)
    project = f"a18-{uuid.uuid4()}"
    memory_ids = []
    for origin in ("first", "second"):
        async with factory() as seed:
            mid = await seed_memory(seed, project=project, origin_key=origin)
            await assert_relation(seed, memory_id=mid, subject=project, rel_type="USES", obj="postgres")
            await seed.commit()
        memory_ids.append(mid)
        if origin == "first":
            async with factory() as lifter:
                await run_lift(lifter)
                await lifter.commit()

    async with factory() as holder, factory() as lifting, factory() as observer:
        try:
            fact_id = (await facts(observer, project))[0]["id"]
            await holder.execute(
                text("SELECT id FROM knowledge_triples WHERE id = CAST(:id AS uuid) FOR UPDATE"),
                {"id": str(fact_id)},
            )
            loop = asyncio.get_running_loop()
            started = loop.time()
            outcome = await asyncio.wait_for(run_lift(lifting), 0.3 + 3)
            elapsed = loop.time() - started
            await lifting.commit()
            assert outcome.deferred == 1
            assert outcome.failed == 0
            assert elapsed < 0.3 + 2
        finally:
            await holder.rollback()
            await lifting.rollback()
            await observer.rollback()
            async with factory() as cleanup:
                graph = PostgresGraphRepository(cleanup)
                for mid in memory_ids:
                    await graph.delete_by_memory_id(UUID(mid))
                await cleanup.execute(text("DELETE FROM knowledge_triples WHERE project = :p"), {"p": project})
                await cleanup.execute(text("DELETE FROM memories WHERE project = :p"), {"p": project})
                await cleanup.commit()


# ------------------------------------------------------------------ A19

from app.services import board_edit  # noqa: E402
from app.services.block_embeddings import PARENT_TABLE  # noqa: E402
from app.services.board_edit import edit_register_row  # noqa: E402
from app.services.document_door import put_document  # noqa: E402
from app.services.embedder_registry import embedder_registry, ensure_registered  # noqa: E402

_REGISTER_3 = (
    "# Register - a19\n\n| # | Item | Assigned | Acceptance | State | Note |\n|---|---|---|---|---|---|\n"
    "| 1 | first | - | - | open | - |\n| 2 | second | - | - | open | - |\n| 3 | third | - | - | open | - |\n"
)


@pytest.mark.asyncio
async def test_a19_a_register_edit_with_no_orchestrator_carries_every_unchanged_vector_under_both_fingerprints(session):
    fingerprints = ("a19-carry-a|3", "a19-carry-b|3")
    for fp in fingerprints:
        embedder_registry.forget(fp)
        await ensure_registered(session, fp)
    try:
        filed = await put_document(
            session, None, project="p", uri="superpowers/registers/a19.md", content=_REGISTER_3, embed_inline=False,
        )
        rows = await session.execute(
            text("SELECT CAST(id AS text) AS id, text FROM blocks WHERE document_id = CAST(:d AS uuid)"),
            {"d": filed.document_id},
        )
        before = {r.id: r.text for r in rows}
        for fp in fingerprints:
            table = child_table(PARENT_TABLE, fp)
            for block_id in before:
                await session.execute(
                    text(
                        f"INSERT INTO {table} (block_id, fingerprint, embedding) "
                        "VALUES (CAST(:b AS uuid), CAST(:fp AS text), CAST('[1,2,3]' AS vector))"
                    ),
                    {"b": block_id, "fp": fp},
                )

        embed_calls = []

        class _NoEmbed:
            def __getattr__(self, name):
                embed_calls.append(name)
                raise AssertionError("an embed call was made")

        await edit_register_row(
            session, document_id=filed.document_id, number=2, expected_hash=filed.content_hash,
            changes={"state": "done"}, actor="admin",
        )

        rows = await session.execute(
            text("SELECT CAST(id AS text) AS id, text FROM blocks WHERE document_id = CAST(:d AS uuid)"),
            {"d": filed.document_id},
        )
        after = {r.id: r.text for r in rows}
        unchanged = set(after.values()) & set(before.values())
        assert unchanged and len(set(after.values()) - set(before.values())) == 1
        for fp in fingerprints:
            table = child_table(PARENT_TABLE, fp)
            texts = (await session.execute(
                text(
                    f"SELECT b.text FROM blocks b JOIN {table} e ON e.block_id = b.id "
                    "WHERE b.document_id = CAST(:d AS uuid)"
                ),
                {"d": filed.document_id},
            )).scalars().all()
            assert set(texts) == unchanged
        assert embed_calls == []
    finally:
        for fp in fingerprints:
            embedder_registry.forget(fp)


# ------------------------------------------------------------------ A20

from tests.test_page_attachment_routes import PNG, V1, _upload, page, root  # noqa: E402,F401


@pytest.mark.asyncio
async def test_a20_an_upload_whose_part_was_collected_mid_stream_answers_408(
    client, auth_headers, root, page, monkeypatch
):
    from app.api.routes import page_attachments as route

    real = route.stage_upload

    async def stage_then_collect(*args, **kwargs):
        staged = await real(*args, **kwargs)
        staged.part.unlink()
        return staged

    monkeypatch.setattr(route, "stage_upload", stage_then_collect)
    response = await _upload(client, auth_headers, page, PNG)
    assert response.status_code == 408, response.text


# ------------------------------------------------------------------ A21 / A42

PROBE_PLUGIN = '''
import os

import pytest_asyncio
from sqlalchemy import text


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _followups_probe(setup_database):
    from tests.conftest import test_engine

    if os.environ.get("FOLLOWUPS_SEED_ENTITY") == "1":
        async with test_engine.begin() as conn:
            await conn.execute(text(
                "INSERT INTO entities (name, entity_type, properties, memory_ids, repo_ids) "
                "VALUES ('postgresql', 'database', '{}'::jsonb, '{}', '{}')"
            ))
    yield
    out = os.environ.get("FOLLOWUPS_LEAK_FILE")
    if out:
        async with test_engine.connect() as conn:
            rows = (await conn.execute(text("SELECT name || '/' || entity_type FROM entities ORDER BY 1"))).scalars().all()
        with open(out, "w") as fh:
            fh.write("\\n".join(rows))
'''


def _run_file_with_probe(tmp_path, test_file: str, *, seed: bool):
    (tmp_path / "followups_probe.py").write_text(PROBE_PLUGIN)
    leak = tmp_path / f"leak-{Path(test_file).stem}.txt"
    env = {
        **os.environ,
        "PYTHONPATH": f"{tmp_path}{os.pathsep}{os.environ.get('PYTHONPATH', '')}",
        "FOLLOWUPS_LEAK_FILE": str(leak),
        "FOLLOWUPS_SEED_ENTITY": "1" if seed else "0",
    }
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "followups_probe", test_file],
        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=300,
    )
    return out, (leak.read_text().splitlines() if leak.exists() else None)


def test_a21_repo_entity_merge_passes_on_a_database_already_holding_a_committed_postgresql_entity(tmp_path):
    out, _ = _run_file_with_probe(tmp_path, "tests/test_repo_entity_merge.py", seed=True)
    assert out.returncode == 0, out.stdout[-3000:] + out.stderr[-1000:]


LEAK_CANDIDATES = [
    "tests/test_communities.py",
    "tests/test_dedup_discriminator.py",
    "tests/test_contradiction_scan.py",
    "tests/test_drop_triple_embeddings.py",
    "tests/test_pipeline_savepoints.py",
    "tests/test_relation_gating.py",
    "tests/test_repo_entity_anchoring.py",
    "tests/test_repo_entity_merge.py",
]


@pytest.mark.parametrize("test_file", LEAK_CANDIDATES)
def test_a42_running_a_file_that_names_postgresql_leaves_no_committed_entity(tmp_path, test_file):
    out, leaked = _run_file_with_probe(tmp_path, test_file, seed=False)
    assert out.returncode == 0, out.stdout[-3000:]
    assert leaked == [], leaked


# ------------------------------------------------------------------ A39

from tests.test_document_revisions import (  # noqa: E402
    StubEmbedder,
    _history,
    _pruned_events,
    _put,
    _revision_ids,
)


@pytest.mark.asyncio
async def test_a39_a_block_verb_prunes_ten_revisions_and_journals_one_row(session):
    from app.services.block_verbs import update_block

    filed = await _put(session, "# A\n\nFirst.\n", uri="a39.md")
    # 60 revisions: 10 oldest are past the newest 50 and older than 90 days; the next 10 are old but inside the 50.
    await _history(session, filed.document_id, [200] * 10 + [100] * 10 + [10] * 40)
    before = await _revision_ids(session, filed.document_id)
    assert len(before) == 60
    block_id = (await session.execute(
        text(
            "SELECT CAST(id AS text) FROM blocks WHERE document_id = CAST(:d AS uuid) "
            "ORDER BY order_index LIMIT 1"
        ),
        {"d": filed.document_id},
    )).scalar_one()

    await update_block(session, StubEmbedder(), block_id=block_id, text="Edited")

    after = await _revision_ids(session, filed.document_id)
    assert after == before[10:]
    events = await _pruned_events(session, filed.document_id)
    assert len(events) == 1
    assert events[0][1] == {"pruned": 10}


# ------------------------------------------------------------------ A41

import httpx  # noqa: E402

from app.config import LLMPurposeConfig  # noqa: E402
from app.services.llm import LLMOrchestrator  # noqa: E402
from app.services.usage_recorder import UsageRecorder  # noqa: E402


class _SignallingRecorder(UsageRecorder):
    def __init__(self, session_factory):
        super().__init__(session_factory, price_overrides={})
        self.recorded = asyncio.Event()

    async def record(self, **kwargs) -> None:
        await super().record(**kwargs)
        self.recorded.set()


@pytest.mark.asyncio
async def test_a41_a_stream_closed_before_its_end_records_ok_false(session, session_factory):
    model = f"a41-model-{uuid.uuid4().hex[:6]}"

    async def body():
        yield b'data: {"choices":[{"delta":{"content":"he"}}]}\n'
        yield b'data: {"choices":[{"delta":{"content":"llo"}}]}\n'

    recorder = _SignallingRecorder(session_factory)
    orchestrator = LLMOrchestrator(
        {"reasoning": LLMPurposeConfig(base_url="http://mock/v1", model=model, dimensions=3)},
        recorder=recorder,
    )
    orchestrator._client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=body()))
    )
    try:
        stream = orchestrator.chat_completion_stream("reasoning", [{"role": "user", "content": "q"}])
        assert await stream.__anext__() == "he"
        await stream.aclose()
        await asyncio.wait_for(recorder.recorded.wait(), timeout=5)
        rows = (await session.execute(
            text("SELECT ok FROM llm_usage WHERE model = :m"), {"m": model}
        )).scalars().all()
        assert rows == [False]
    finally:
        await orchestrator.close()

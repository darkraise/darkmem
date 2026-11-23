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

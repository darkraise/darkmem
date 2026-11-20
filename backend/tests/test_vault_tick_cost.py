"""What one vault tick or one fact read costs in statements and file reads."""
from __future__ import annotations

import builtins
import json
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import event, text

from app.models.config import Config
from app.services import claim_gates
from app.services.claim_gates import FACT_ID_KIND, served_status
from app.services.fact_lift import run_code_lift
from app.services.fact_provenance import MEMORY_SOURCE_KIND
from app.services.ladder_config import LADDER_CONFIG_KEY, LADDER_MEASUREMENTS_KEY
from app.services.supersession_hold import _SUPERSEDED_SOURCE_SQL
from app.services.verification_ladder import DEMOTE_GRACE_CONFIG_KEY
from app.services.verification_recompute import (
    _COMMIT_SKEW_MARGIN,
    _load_state,
    run_recompute,
)
from tests.conftest import test_engine
from tests.test_contradiction_scan import _enqueue, _fact, _source


@contextmanager
def _statements():
    seen: list[tuple[str, object]] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        seen.append((statement, parameters))

    engine = test_engine.sync_engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        yield seen
    finally:
        event.remove(engine, "before_cursor_execute", record)


async def test_idle_drain_advances_the_watermark(session):
    fact_id = await _fact(session, subject="darkmem", obj="postgres")
    await _enqueue(session, fact_id)
    moment = datetime.now(timezone.utc) + timedelta(minutes=1)

    await run_recompute(session, batch_size=10_000, now=moment)

    state = await _load_state(session)
    assert state.watermark_created_at == moment - _COMMIT_SKEW_MARGIN


async def test_idle_drain_never_moves_the_watermark_back(session):
    later = datetime.now(timezone.utc) + timedelta(minutes=10)
    await run_recompute(session, batch_size=10_000, now=later)

    await run_recompute(session, batch_size=10_000, now=later - timedelta(minutes=5))

    state = await _load_state(session)
    assert state.watermark_created_at == later - _COMMIT_SKEW_MARGIN


async def _plan(session, statement, params) -> list[str]:
    await session.execute(text("SET LOCAL enable_seqscan = off"))
    rows = await session.execute(text(f"EXPLAIN {statement.text}"), params)
    return [row[0] for row in rows.all()]


# Both lead on `memories.id`; the planner takes whichever it costs lower.
_ID_INDEXES = ("memories_pkey", "memories_id_project_key")


def _probes_memories_by_key(plan: list[str]) -> bool:
    for index, line in enumerate(plan):
        if any(f"using {name} on memories m " in line for name in _ID_INDEXES):
            following = plan[index + 1] if index + 1 < len(plan) else ""
            if "Index Cond" in following and "(id = CASE" in following:
                return True
    return False


async def test_memory_source_join_uses_the_primary_key(session):
    from app.repositories.fact_sources import _MEMORY_SOURCES_FOR_FACT
    from app.services.fact_provenance import _CANONICAL_REF as CANONICAL_MEMORY_REF

    # Enough superseded rows that reaching `m` through its status costs more
    # than probing it by id, so the plan shows which probes the join allows.
    keeper = str(uuid4())
    await session.execute(
        text("INSERT INTO memories (id, content, source) VALUES (CAST(:id AS uuid), 'k', 'api')"),
        {"id": keeper},
    )
    await session.execute(
        text("""
            INSERT INTO memories (id, content, source, status, superseded_by)
            SELECT gen_random_uuid(), 'old', 'api', 'superseded', CAST(:id AS uuid)
            FROM generate_series(1, 2000)
        """),
        {"id": keeper},
    )
    await session.execute(text("ANALYZE memories"))

    fact_id = str(uuid4())
    hold = await _plan(
        session, _SUPERSEDED_SOURCE_SQL,
        {"fact_id": fact_id, "kind": MEMORY_SOURCE_KIND, "canonical": CANONICAL_MEMORY_REF},
    )
    sources = await _plan(
        session, _MEMORY_SOURCES_FOR_FACT,
        {"fact_id": fact_id, "kind": MEMORY_SOURCE_KIND, "canonical": CANONICAL_MEMORY_REF},
    )

    assert _probes_memories_by_key(hold), "\n".join(hold)
    assert _probes_memories_by_key(sources), "\n".join(sources)


async def test_code_reconcile_is_skipped_when_no_repository_moved(session):
    await run_code_lift(session)
    with _statements() as seen:
        await run_code_lift(session)

    provenance_reads = [
        statement for statement, _ in seen
        if "fs.source_ref AS repo_ref" in statement
    ]
    assert provenance_reads == []


async def test_ladder_config_is_resolved_once_per_tick(session):
    # A ladder row at its floors, so the measurements row is consulted too.
    session.add(Config(key=LADDER_CONFIG_KEY, value={"n_default": 3}))
    await session.commit()
    for index in range(10):
        fact_id = await _fact(session, subject=f"svc-{index}", obj="postgres")
        await _source(session, fact_id, f"sess-{index}")
        await _enqueue(session, fact_id)

    with _statements() as seen:
        await run_recompute(
            session, batch_size=10_000,
            now=datetime.now(timezone.utc) + timedelta(minutes=1),
        )

    def reads(key: str) -> int:
        return sum(
            1 for statement, parameters in seen
            if "FROM config" in statement and key in (parameters or ())
        )

    assert reads(LADDER_CONFIG_KEY) == 1
    assert reads(LADDER_MEASUREMENTS_KEY) == 1
    assert reads(DEMOTE_GRACE_CONFIG_KEY) == 1


def test_promotion_record_is_read_once_per_response(tmp_path, monkeypatch):
    record = tmp_path / "promotion_metrics_record.json"
    record.write_text(json.dumps({"gate_eligible": True}), encoding="utf-8")
    monkeypatch.setattr(claim_gates, "PROMOTION_RECORD_PATH", record)

    opened: list[str] = []
    real_open = builtins.open

    def counting_open(file, *args, **kwargs):
        if str(file) == str(record):
            opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", counting_open)

    for _ in range(50):
        assert served_status("corroborated", id_kind=FACT_ID_KIND) == ("corroborated", None)
    assert len(opened) == 1

    record.write_text(json.dumps({"gate_eligible": False}), encoding="utf-8")
    stamp = record.stat().st_mtime_ns + 1_000_000_000
    os.utime(record, ns=(stamp, stamp))

    served, reason = served_status("corroborated", id_kind=FACT_ID_KIND)
    assert served != "corroborated" and reason is not None
    assert len(opened) == 2


async def test_get_fact_reads_the_latest_verified_event_once(
    client, session, auth_headers,
):
    fact_id = await _fact(session, subject="darkmem", obj="postgres", status="disputed")

    with _statements() as seen:
        response = await client.get(
            f"/api/v1/knowledge/facts/{fact_id}", headers=auth_headers,
        )

    assert response.status_code == 200
    evidence_reads = [
        statement for statement, _ in seen
        if "DISTINCT ON (object_id) object_id, payload" in statement
        and "event_type = 'verified'" in statement
    ]
    assert len(evidence_reads) == 1

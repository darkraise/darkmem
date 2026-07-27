"""The events read API (T1.08): GET /events, /events/calendar, /events/timeline.

Doc 12 §7 makes this three GET shapes over the durable `events` substrate
(doc 04 §8.1), replacing the coarse `AuditLog` reads. There is no POST here —
`events` is append-only and journaled only by services.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.services.events import record_event

pytestmark = pytest.mark.asyncio


async def _seed(
    session,
    *,
    event_type: str = "created",
    object_type: str = "memory",
    object_id: uuid.UUID | None = None,
    project: str | None = "default",
    payload: dict | None = None,
) -> None:
    await record_event(
        session,
        event_type=event_type,
        object_type=object_type,
        object_id=object_id,
        project=project,
        payload=payload,
    )
    await session.commit()


# `events` forbids UPDATE via a trigger (doc 04 §8.1), so a row with a
# specific timestamp (for date-range / ordering tests) must carry it at
# INSERT time — there is no way to backdate a row after the fact.
async def _seed_at(
    session,
    *,
    created_at: datetime,
    event_type: str = "created",
    object_type: str = "memory",
    object_id: uuid.UUID | None = None,
    project: str | None = "default",
) -> None:
    # A RANGE-partitioned parent with no matching child rejects the insert
    # outright, so a test date outside the baseline's current/next-month
    # partitions must grow its own child first.
    await session.execute(
        text(
            "SELECT events_ensure_partition("
            "  (date_trunc('month', :ts AT TIME ZONE 'UTC'))::date)"
        ),
        {"ts": created_at},
    )
    await session.execute(
        text(
            "INSERT INTO events (event_type, object_type, object_id, project, created_at) "
            "VALUES (:event_type, :object_type, CAST(:object_id AS uuid), :project, :ts)"
        ),
        {
            "event_type": event_type,
            "object_type": object_type,
            "object_id": str(object_id) if object_id else None,
            "project": project,
            "ts": created_at,
        },
    )
    await session.commit()


# ── GET /events ──────────────────────────────────────────────────────


async def test_requires_auth(client):
    response = await client.get("/api/v1/events")
    assert response.status_code in (401, 403)


async def test_list_returns_seeded_event(client, auth_headers, session):
    await _seed(session, event_type="created", object_type="memory")
    response = await client.get("/api/v1/events", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(e["event_type"] == "created" for e in data["items"])


async def test_list_filters_by_event_type(client, auth_headers, session):
    await _seed(session, event_type="created", object_type="memory")
    await _seed(session, event_type="deprecated", object_type="memory")
    response = await client.get(
        "/api/v1/events", params={"event_type": "deprecated"}, headers=auth_headers
    )
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["event_type"] == "deprecated"


async def test_list_filters_by_object_type_and_object_id(client, auth_headers, session):
    target = uuid.uuid4()
    other = uuid.uuid4()
    await _seed(session, event_type="created", object_type="memory", object_id=target)
    await _seed(session, event_type="created", object_type="memory", object_id=other)
    await _seed(session, event_type="created", object_type="entity", object_id=target)

    response = await client.get(
        "/api/v1/events",
        params={"object_type": "memory", "object_id": str(target)},
        headers=auth_headers,
    )
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["object_id"] == str(target)
    assert data["items"][0]["object_type"] == "memory"


async def test_list_is_paginated_newest_first(client, auth_headers, session):
    now = datetime.now(timezone.utc)
    marker = uuid.uuid4()
    for i in range(5):
        await _seed_at(
            session,
            created_at=now - timedelta(minutes=5 - i),
            event_type="created",
            object_type="memory",
            object_id=marker,
            project="pagination-test",
        )

    response = await client.get(
        "/api/v1/events",
        params={"project": "pagination-test", "limit": 2, "offset": 0},
        headers=auth_headers,
    )
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    times = [datetime.fromisoformat(e["created_at"]) for e in data["items"]]
    assert times[0] > times[1]

    page2 = await client.get(
        "/api/v1/events",
        params={"project": "pagination-test", "limit": 2, "offset": 2},
        headers=auth_headers,
    )
    assert len(page2.json()["items"]) == 2


async def test_list_filters_by_date_range(client, auth_headers, session):
    base = datetime(2030, 6, 15, 12, 0, tzinfo=timezone.utc)
    project = f"date-range-{uuid.uuid4().hex[:8]}"
    await _seed_at(session, created_at=base - timedelta(days=10), project=project)
    await _seed_at(session, created_at=base, project=project)
    await _seed_at(session, created_at=base + timedelta(days=10), project=project)

    response = await client.get(
        "/api/v1/events",
        params={
            "project": project,
            "since": (base - timedelta(hours=1)).isoformat(),
            "until": (base + timedelta(hours=1)).isoformat(),
        },
        headers=auth_headers,
    )
    data = response.json()
    assert data["total"] == 1


async def test_list_project_isolation(client, auth_headers, session):
    """T1.08's Done-when: project scoping pushed into SQL. Cross-project rows
    must never appear regardless of how many other projects have events."""
    proj_a = f"alpha-{uuid.uuid4().hex[:8]}"
    proj_b = f"beta-{uuid.uuid4().hex[:8]}"
    await _seed(session, project=proj_a)
    await _seed(session, project=proj_a)
    await _seed(session, project=proj_b)

    response = await client.get(
        "/api/v1/events", params={"project": proj_a}, headers=auth_headers
    )
    data = response.json()
    assert data["total"] == 2
    assert all(e["project"] == proj_a for e in data["items"])


async def test_list_payload_round_trips(client, auth_headers, session):
    await _seed(session, payload={"before": "x", "after": "y", "count": 3})
    response = await client.get("/api/v1/events", headers=auth_headers)
    data = response.json()
    matches = [e for e in data["items"] if e["payload"].get("before") == "x"]
    assert matches
    assert matches[0]["payload"] == {"before": "x", "after": "y", "count": 3}


# ── GET /events/calendar ─────────────────────────────────────────────


async def test_calendar_requires_auth(client):
    response = await client.get("/api/v1/events/calendar")
    assert response.status_code in (401, 403)


async def test_calendar_buckets_by_day_not_rows(client, auth_headers, session):
    project = f"cal-{uuid.uuid4().hex[:8]}"
    day = datetime(2030, 3, 1, tzinfo=timezone.utc)
    await _seed_at(session, created_at=day + timedelta(hours=1), project=project)
    await _seed_at(session, created_at=day + timedelta(hours=5), project=project)
    await _seed_at(session, created_at=day + timedelta(hours=20), project=project)
    await _seed_at(session, created_at=day + timedelta(days=1, hours=2), project=project)

    response = await client.get(
        "/api/v1/events/calendar", params={"project": project}, headers=auth_headers
    )
    assert response.status_code == 200
    buckets = response.json()["buckets"]
    assert buckets == [
        {"day": "2030-03-01", "count": 3},
        {"day": "2030-03-02", "count": 1},
    ]


async def test_calendar_bucket_is_utc_not_session_timezone(client, auth_headers, session):
    """Invariant-bearing (doc 04 §8.1): the bucket expression must be
    `(created_at AT TIME ZONE 'UTC')::date`, not a bare `created_at::date`.
    The bare cast is only STABLE — it resolves against the session's
    `TimeZone` GUC — so a non-UTC session would silently move this row to a
    different calendar day under the wrong implementation.

    23:30 UTC on 2031-06-01 is 06:30 on 2031-06-02 in Asia/Bangkok (+07). If
    the calendar query used `created_at::date` under a Bangkok session, the
    row would bucket on the 2nd; the correct, UTC-pinned query buckets it on
    the 1st regardless of session timezone.
    """
    project = f"tz-{uuid.uuid4().hex[:8]}"
    instant = datetime(2031, 6, 1, 23, 30, tzinfo=timezone.utc)
    await _seed_at(session, created_at=instant, project=project)

    await session.execute(text("SET LOCAL TIME ZONE 'Asia/Bangkok'"))
    response = await client.get(
        "/api/v1/events/calendar", params={"project": project}, headers=auth_headers
    )
    await session.execute(text("SET LOCAL TIME ZONE 'UTC'"))

    assert response.status_code == 200
    buckets = response.json()["buckets"]
    assert buckets == [{"day": "2031-06-01", "count": 1}]


# ── GET /events/timeline ─────────────────────────────────────────────


async def test_timeline_requires_auth(client):
    response = await client.get(
        "/api/v1/events/timeline",
        params={"object_type": "memory", "object_id": str(uuid.uuid4())},
    )
    assert response.status_code in (401, 403)


async def test_timeline_is_per_object_oldest_to_newest(client, auth_headers, session):
    target = uuid.uuid4()
    other = uuid.uuid4()
    now = datetime.now(timezone.utc)
    await _seed_at(session, created_at=now - timedelta(minutes=3), object_type="memory", object_id=target, event_type="created")
    await _seed_at(session, created_at=now - timedelta(minutes=2), object_type="memory", object_id=target, event_type="extracted")
    await _seed_at(session, created_at=now - timedelta(minutes=1), object_type="memory", object_id=target, event_type="superseded")
    await _seed_at(session, created_at=now, object_type="memory", object_id=other, event_type="created")

    response = await client.get(
        "/api/v1/events/timeline",
        params={"object_type": "memory", "object_id": str(target)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert [e["event_type"] for e in data["items"]] == ["created", "extracted", "superseded"]
    assert all(e["object_id"] == str(target) for e in data["items"])


async def test_timeline_is_paginated(client, auth_headers, session):
    target = uuid.uuid4()
    now = datetime.now(timezone.utc)
    for i in range(4):
        await _seed_at(
            session,
            created_at=now - timedelta(minutes=4 - i),
            object_type="memory",
            object_id=target,
            event_type="created",
        )

    response = await client.get(
        "/api/v1/events/timeline",
        params={"object_type": "memory", "object_id": str(target), "limit": 2, "offset": 0},
        headers=auth_headers,
    )
    data = response.json()
    assert data["total"] == 4
    assert len(data["items"]) == 2

    page2 = await client.get(
        "/api/v1/events/timeline",
        params={"object_type": "memory", "object_id": str(target), "limit": 2, "offset": 2},
        headers=auth_headers,
    )
    assert len(page2.json()["items"]) == 2


async def test_timeline_requires_object_type_and_id(client, auth_headers):
    response = await client.get("/api/v1/events/timeline", headers=auth_headers)
    assert response.status_code == 422


# ── Index usage evidence ─────────────────────────────────────────────
#
# EXPLAIN is checked with `enable_seqscan` forced off: the seeded rows here
# are far too few for the real planner to prefer an index over a sequential
# scan on their own merits, so forcing seqscan off is what proves the query
# SHAPE matches the index (predicate columns, expression form) rather than
# proving Postgres always chooses it at this row count.


async def _partition_index_names(session, parent_index: str) -> list[str]:
    """A partitioned index's own name never appears in an EXPLAIN plan — only
    its per-partition children do (`events_202607_project_..._idx`, not
    `ix_events_day`) — so resolve those child names to check a plan against."""
    rows = await session.execute(
        text(
            "SELECT c.relname FROM pg_inherits i "
            "JOIN pg_class c ON c.oid = i.inhrelid "
            "WHERE i.inhparent = to_regclass(:parent_index)"
        ),
        {"parent_index": parent_index},
    )
    return [r[0] for r in rows]


async def test_timeline_query_can_use_object_index(session):
    target = uuid.uuid4()
    await record_event(session, event_type="created", object_type="memory", object_id=target)
    await session.commit()

    child_indexes = await _partition_index_names(session, "ix_events_object")
    assert child_indexes, "ix_events_object has no per-partition children to check against"

    await session.execute(text("SET LOCAL enable_seqscan = off"))
    plan_rows = await session.execute(
        text(
            "EXPLAIN SELECT id, created_at, event_type, object_type, object_id, "
            "project, actor, api_key_id, source, payload FROM events "
            "WHERE object_type = :object_type AND object_id = CAST(:object_id AS uuid) "
            "ORDER BY created_at ASC, id ASC LIMIT 50 OFFSET 0"
        ),
        {"object_type": "memory", "object_id": str(target)},
    )
    plan = "\n".join(r[0] for r in plan_rows)
    assert any(name in plan for name in child_indexes), plan


async def test_calendar_query_can_use_day_index(session):
    project = f"explain-{uuid.uuid4().hex[:8]}"
    await record_event(session, event_type="created", object_type="memory", project=project)
    await session.commit()

    child_indexes = await _partition_index_names(session, "ix_events_day")
    assert child_indexes, "ix_events_day has no per-partition children to check against"

    await session.execute(text("SET LOCAL enable_seqscan = off"))
    plan_rows = await session.execute(
        text(
            "EXPLAIN SELECT (created_at AT TIME ZONE 'UTC')::date AS day, COUNT(*) "
            "FROM events WHERE project = :project "
            "GROUP BY (created_at AT TIME ZONE 'UTC')::date ORDER BY day"
        ),
        {"project": project},
    )
    plan = "\n".join(r[0] for r in plan_rows)
    assert any(name in plan for name in child_indexes), plan

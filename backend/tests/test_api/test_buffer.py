"""The `memory_buffer` read surface and its poison-row actions (T1.13b).

Doc 13 §6.1 names the buffer monitor as the place a poison row appears; before
this task nothing read `memory_buffer` over the API at all, so that surface
could only bind demo data. What is under test is therefore not one route but a
contract with three sharp edges:

* **Staleness has one definition.** The monitor's `stale` filter must agree with
  `buffer_flush.stale_claims()` exactly. Two definitions drift, and the one on
  the screen is the one an operator believes.
* **Project scope is SQL, not Python.** Every other channel was closed in
  T1.29a-c and the service-layer filter that used to backstop them is gone, so a
  scope applied after the fetch would leak `total` and the page boundaries.
* **Only a poison row is actionable, and retention is untouched.** `done` rows
  leave through the flush's own sweep, `error` rows never do, and the one
  deletion here is a row a human named.
"""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import text

from app.services.buffer_flush import stale_claims
from app.services.memory_buffer import buffered_memory_id, enqueue

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/memory-buffer"


async def seed(
    session,
    *,
    status: str = "pending",
    project: str = "default",
    content: str = "buffered capture",
    attempts: int = 0,
    last_error: str | None = None,
    claimed_age_seconds: int | None = None,
    **extra,
) -> uuid.UUID:
    row = await enqueue(
        session, content=content, project=project, source="api", **extra,
    )
    await session.execute(
        text(
            "UPDATE memory_buffer SET status = :status, attempts = :attempts, "
            "last_error = CAST(:last_error AS text), "
            "claimed_at = CASE WHEN CAST(:age AS int) IS NULL THEN NULL "
            "  ELSE NOW() - CAST(:age AS int) * INTERVAL '1 second' END, "
            "claimed_by = CASE WHEN CAST(:age AS int) IS NULL THEN NULL "
            "  ELSE 'host:1' END "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {
            "status": status, "attempts": attempts, "last_error": last_error,
            "age": claimed_age_seconds, "id": str(row.id),
        },
    )
    await session.commit()
    return row.id


async def _events(session, event_type: str) -> list[dict]:
    rows = (await session.execute(
        text("SELECT * FROM events WHERE event_type = :t ORDER BY id"),
        {"t": event_type},
    )).mappings().all()
    return [dict(r) for r in rows]


# ── The read surface ────────────────────────────────────────────────


async def test_list_reports_the_triage_fields(client, auth_headers, session):
    """Done-when 1: status, attempt count, claim timestamp and `last_error` are
    what triage reads; without all four a poison row is visible but not
    diagnosable."""
    buffer_id = await seed(
        session, status="error", attempts=5, last_error="value too long",
        claimed_age_seconds=None, content="poisonous capture",
    )
    response = await client.get(BASE, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    row = body["items"][0]
    assert row["id"] == str(buffer_id)
    assert row["status"] == "error"
    assert row["attempts"] == 5
    assert row["max_attempts"] == 5
    assert row["last_error"] == "value too long"
    assert row["claimed_at"] is None
    assert row["content_preview"] == "poisonous capture"
    assert row["is_stale"] is False
    assert row["memory_id"] is not None


async def test_list_filters_to_claimed_stale_and_poison(client, auth_headers, session):
    pending = await seed(session, status="pending")
    fresh = await seed(session, status="claimed", claimed_age_seconds=5)
    stale = await seed(session, status="claimed", claimed_age_seconds=100_000)
    poison = await seed(session, status="error", attempts=5)
    done = await seed(session, status="done")

    async def ids(state: str) -> set[str]:
        response = await client.get(f"{BASE}?state={state}", headers=auth_headers)
        assert response.status_code == 200
        return {r["id"] for r in response.json()["items"]}

    assert await ids("pending") == {str(pending)}
    assert await ids("claimed") == {str(fresh), str(stale)}
    assert await ids("stale") == {str(stale)}
    assert await ids("poison") == {str(poison)}
    assert await ids("done") == {str(done)}


async def set_visibility(session, seconds: int) -> None:
    """Point the lease at a non-default window, through the same `config` row
    `PUT /api/v1/jobs/buffer_flush/config` writes."""
    await session.execute(
        text(
            "INSERT INTO config (key, value) VALUES "
            "('job:buffer_flush', CAST(:v AS jsonb)) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ),
        {"v": json.dumps(
            {"enabled": True, "config": {"buffer_claim_visibility_seconds": seconds}}
        )},
    )
    await session.commit()


async def test_stale_matches_the_flush_helper_exactly(client, auth_headers, session):
    """Done-when 2. The monitor's staleness and the lease the reclaim arm
    enforces are one predicate, so this equality is the drift tripwire.

    The window is configured away from its default and the claims are aged to
    straddle both values, so a hardcoded constant, a stale default read, or any
    second definition of the arithmetic lands on a different set than
    `stale_claims()` does and fails here rather than quietly showing operators
    rows the flush will not act on.
    """
    await set_visibility(session, 600)
    await seed(session, status="claimed", claimed_age_seconds=5)
    await seed(session, status="claimed", claimed_age_seconds=400)
    stale_ids = {
        str(await seed(session, status="claimed", claimed_age_seconds=900))
        for _ in range(3)
    }
    response = await client.get(f"{BASE}?state=stale", headers=auth_headers)
    from_api = {r["id"] for r in response.json()["items"]}
    from_helper = {
        str(r.id) for r in await stale_claims(session, visibility_seconds=600)
    }
    assert from_api == from_helper == stale_ids

    stats = (await client.get(f"{BASE}/stats", headers=auth_headers)).json()
    assert stats["visibility_seconds"] == 600
    assert stats["stale"] == 3


async def test_is_stale_rides_the_row_not_only_the_filter(client, auth_headers, session):
    """A `claimed` listing has to say which of its rows are past the lease;
    otherwise the operator has to run the arithmetic themselves."""
    await set_visibility(session, 600)
    fresh = await seed(session, status="claimed", claimed_age_seconds=400)
    stale = await seed(session, status="claimed", claimed_age_seconds=900)
    response = await client.get(f"{BASE}?state=claimed", headers=auth_headers)
    by_id = {r["id"]: r for r in response.json()["items"]}
    assert by_id[str(fresh)]["is_stale"] is False
    assert by_id[str(stale)]["is_stale"] is True


async def test_stats_counts_every_state_in_one_read(client, auth_headers, session):
    await seed(session, status="pending")
    await seed(session, status="pending")
    await seed(session, status="claimed", claimed_age_seconds=5)
    await seed(session, status="claimed", claimed_age_seconds=100_000)
    await seed(session, status="done")
    await seed(session, status="error", attempts=5)

    response = await client.get(f"{BASE}/stats", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {
        "pending": 2, "claimed": 2, "stale": 1, "done": 1, "poison": 1,
        "max_attempts": 5, "visibility_seconds": 300,
    }


async def test_a_long_capture_is_previewed_not_streamed(client, auth_headers, session):
    await seed(session, status="error", content="z" * 4000)
    row = (await client.get(BASE, headers=auth_headers)).json()["items"][0]
    assert len(row["content_preview"]) == 500
    assert row["content_length"] == 4000


async def test_the_read_surface_requires_auth(client, session):
    await seed(session, status="error")
    assert (await client.get(BASE)).status_code in (401, 403)
    assert (await client.get(f"{BASE}/stats")).status_code in (401, 403)


# ── Done-when 4: project scope is pushed into SQL ───────────────────


async def test_project_scopes_the_list_and_its_total(client, auth_headers, session):
    """Done-when 4. A Python filter would still return the right items and the
    wrong `total`, which is exactly the shape of leak T1.35's probe looks for,
    so the count is asserted alongside the rows."""
    mine = await seed(session, status="error", project="alpha")
    for _ in range(4):
        await seed(session, status="error", project="beta")

    response = await client.get(f"{BASE}?project=alpha", headers=auth_headers)
    body = response.json()
    assert body["total"] == 1
    assert [r["id"] for r in body["items"]] == [str(mine)]


async def test_project_scopes_the_stats(client, auth_headers, session):
    await seed(session, status="error", project="alpha")
    await seed(session, status="pending", project="beta")
    await seed(session, status="pending", project="beta")

    scoped = (await client.get(f"{BASE}/stats?project=beta", headers=auth_headers)).json()
    assert scoped["pending"] == 2
    assert scoped["poison"] == 0


async def test_project_scopes_the_actions(client, auth_headers, session):
    """A scoped caller must not be able to act on another project's row, and the
    answer is 404 rather than 403: outside the scope the row does not exist."""
    other = await seed(session, status="error", project="beta", attempts=5)
    response = await client.post(
        f"{BASE}/{other}/requeue?project=alpha", headers=auth_headers,
    )
    assert response.status_code == 404
    response = await client.delete(f"{BASE}/{other}?project=alpha", headers=auth_headers)
    assert response.status_code == 404

    still = (await session.execute(
        text("SELECT status FROM memory_buffer WHERE id = CAST(:i AS uuid)"),
        {"i": str(other)},
    )).scalar_one()
    assert still == "error"


async def test_the_project_predicate_is_not_a_python_filter():
    """The scope has to reach the database. A post-fetch filter would satisfy
    every assertion above on today's page sizes and leak the moment a page
    boundary or a count crossed a project."""
    from app.services import buffer_monitor

    assert ":project" in buffer_monitor._PROJECT_PREDICATE
    for sql in (buffer_monitor._LOAD_SQL, buffer_monitor._REQUEUE_SQL):
        assert "project" in str(sql) or "status = 'error'" in str(sql)


# ── Done-when 3: a poison row is actionable ─────────────────────────


async def test_requeue_returns_a_poison_row_to_pending_with_a_clean_ladder(
    client, auth_headers, session,
):
    """Done-when 3. Attempts reset, because an operator requeue follows a fix
    somewhere else and the row deserves the whole ladder rather than the one
    attempt it had left."""
    buffer_id = await seed(
        session, status="error", attempts=5, last_error="value too long",
    )
    response = await client.post(f"{BASE}/{buffer_id}/requeue", headers=auth_headers)
    assert response.status_code == 200
    row = response.json()
    assert row["status"] == "pending"
    assert row["attempts"] == 0
    assert row["last_error"] is None

    stored = (await session.execute(
        text("SELECT status, attempts, last_error, claimed_at, claimed_by "
             "FROM memory_buffer WHERE id = CAST(:i AS uuid)"),
        {"i": str(buffer_id)},
    )).mappings().one()
    assert stored["status"] == "pending"
    assert stored["attempts"] == 0
    assert stored["last_error"] is None
    assert stored["claimed_at"] is None
    assert stored["claimed_by"] is None


async def test_requeue_clears_the_deadline_ladder_too(client, auth_headers, session):
    """`flush_timeouts` is the counter that shrinks the claim batch after a
    deadline. Leaving it behind would make a requeued row keep throttling every
    batch it lands in, long after whatever was slow was fixed."""
    buffer_id = await seed(session, status="error", attempts=5)
    await session.execute(
        text("UPDATE memory_buffer SET metadata = jsonb_set(metadata, "
             "'{flush_timeouts}', '4'::jsonb) WHERE id = CAST(:i AS uuid)"),
        {"i": str(buffer_id)},
    )
    await session.commit()

    await client.post(f"{BASE}/{buffer_id}/requeue", headers=auth_headers)
    metadata = (await session.execute(
        text("SELECT metadata FROM memory_buffer WHERE id = CAST(:i AS uuid)"),
        {"i": str(buffer_id)},
    )).scalar_one()
    assert "flush_timeouts" not in metadata
    assert "memory_id" in metadata, "the pre-minted id is not the ladder's to clear"


async def test_discard_deletes_the_poison_row(client, auth_headers, session):
    buffer_id = await seed(session, status="error", attempts=5)
    response = await client.delete(f"{BASE}/{buffer_id}", headers=auth_headers)
    assert response.status_code == 204
    assert response.content == b""

    remaining = (await session.execute(
        text("SELECT COUNT(*) FROM memory_buffer WHERE id = CAST(:i AS uuid)"),
        {"i": str(buffer_id)},
    )).scalar_one()
    assert remaining == 0


async def test_both_actions_journal_to_events(client, auth_headers, session):
    """Done-when 3. A row that leaves the buffer by a human decision has to
    leave a record behind it — the discarded row's own content is gone."""
    requeued = await seed(session, status="error", attempts=5, last_error="boom")
    discarded = await seed(
        session, status="error", attempts=5, last_error="worse",
        content="the discarded capture", project="alpha",
    )
    memory_ids = {
        r["id"]: r["metadata"]["memory_id"]
        for r in (await session.execute(
            text("SELECT id, metadata FROM memory_buffer")
        )).mappings().all()
    }

    await client.post(f"{BASE}/{requeued}/requeue", headers=auth_headers)
    await client.delete(f"{BASE}/{discarded}", headers=auth_headers)

    journal = await _events(session, "buffer_requeued")
    assert len(journal) == 1
    assert journal[0]["payload"]["buffer_id"] == str(requeued)
    assert journal[0]["payload"]["attempts_before"] == 5
    assert journal[0]["payload"]["last_error"] == "boom"
    assert str(journal[0]["object_id"]) == memory_ids[requeued]

    journal = await _events(session, "buffer_discarded")
    assert len(journal) == 1
    assert journal[0]["payload"]["buffer_id"] == str(discarded)
    assert journal[0]["payload"]["content_preview"] == "the discarded capture"
    assert journal[0]["project"] == "alpha"
    assert str(journal[0]["object_id"]) == memory_ids[discarded]


@pytest.mark.parametrize("status_value", ["pending", "claimed", "done"])
async def test_only_a_poison_row_is_actionable(
    client, auth_headers, session, status_value,
):
    """A `claimed` row may be in flight, and requeueing it behind a live claimer
    would put two claimers on one row — the failure the whole lease exists to
    prevent. A `pending` or `done` row is not a problem to solve."""
    buffer_id = await seed(
        session,
        status=status_value,
        claimed_age_seconds=5 if status_value == "claimed" else None,
    )
    response = await client.post(f"{BASE}/{buffer_id}/requeue", headers=auth_headers)
    assert response.status_code == 409
    response = await client.delete(f"{BASE}/{buffer_id}", headers=auth_headers)
    assert response.status_code == 409

    survived = (await session.execute(
        text("SELECT status FROM memory_buffer WHERE id = CAST(:i AS uuid)"),
        {"i": str(buffer_id)},
    )).scalar_one()
    assert survived == status_value


async def test_the_actions_404_on_an_unknown_row(client, auth_headers):
    missing = uuid.uuid4()
    assert (await client.post(
        f"{BASE}/{missing}/requeue", headers=auth_headers
    )).status_code == 404
    assert (await client.delete(
        f"{BASE}/{missing}", headers=auth_headers
    )).status_code == 404


async def test_the_actions_require_auth(client, session):
    buffer_id = await seed(session, status="error", attempts=5)
    assert (await client.post(f"{BASE}/{buffer_id}/requeue")).status_code in (401, 403)
    assert (await client.delete(f"{BASE}/{buffer_id}")).status_code in (401, 403)


# ── Done-when 5: retention is unchanged ─────────────────────────────


async def test_the_read_surface_never_sweeps(client, auth_headers, session):
    """Done-when 5. This surface reads and acts; it does not clean up. Reading
    every state, twice, must leave the buffer exactly as it found it — a `done`
    row leaves only through the flush's retention sweep and an `error` row never
    leaves on its own."""
    seeded = {
        await seed(session, status="done"),
        await seed(session, status="error", attempts=5),
        await seed(session, status="pending"),
        await seed(session, status="claimed", claimed_age_seconds=100_000),
    }
    for _ in range(2):
        for state in ("", "?state=pending", "?state=claimed", "?state=stale",
                      "?state=done", "?state=poison"):
            assert (await client.get(f"{BASE}{state}", headers=auth_headers)).status_code == 200
        assert (await client.get(f"{BASE}/stats", headers=auth_headers)).status_code == 200

    remaining = set((await session.execute(
        text("SELECT id FROM memory_buffer")
    )).scalars())
    assert remaining == seeded


async def test_the_read_surface_never_touches_the_memories_table(
    client, auth_headers, session,
):
    """A buffered capture's `memories` row is the flush's to write. Requeueing
    or discarding must not mint, enrich or delete one."""
    buffer_id = await seed(session, status="error", attempts=5)
    await client.post(f"{BASE}/{buffer_id}/requeue", headers=auth_headers)
    assert (await session.execute(
        text("SELECT COUNT(*) FROM memories")
    )).scalar_one() == 0


async def test_the_two_ids_stay_apart_on_the_wire(client, auth_headers, session):
    """Doc 05 §2.2. `id` is the buffer's tracking handle and `memory_id` the
    pre-minted reference the 202 already handed the caller; a monitor that
    conflated them would offer an id that resolves to nothing."""
    row = await enqueue(session, content="two ids", project="default", source="api")
    memory_id = buffered_memory_id(row)
    buffer_id = row.id
    await session.commit()

    listed = (await client.get(BASE, headers=auth_headers)).json()["items"][0]
    assert listed["id"] == str(buffer_id)
    assert listed["memory_id"] == str(memory_id)
    assert listed["id"] != listed["memory_id"]


async def test_a_row_with_no_preminted_id_is_still_listed(client, auth_headers, session):
    """The rows written by some path other than `enqueue` are exactly the ones
    the flush rejects to `error`, so the triage surface has to render them
    rather than 500 on the missing handle."""
    orphan = uuid.uuid4()
    await session.execute(
        text("INSERT INTO memory_buffer (id, project, content, source, status, "
             "metadata) VALUES (CAST(:i AS uuid), 'default', 'no handle', 'api', "
             "'error', '{}'::jsonb)"),
        {"i": str(orphan)},
    )
    await session.commit()

    row = (await client.get(f"{BASE}?state=poison", headers=auth_headers)).json()["items"][0]
    assert row["id"] == str(orphan)
    assert row["memory_id"] is None

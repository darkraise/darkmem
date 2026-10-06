"""A keyed call must be visible to the operator (E4.F1, doc 18 §5 convention 8).

The E4 epic review's C1: the credential shipped, three surfaces claimed its use
was observable, and nothing wrote either signal. `api_keys.last_used_at` had
zero writers while the settings card rendered "never used" as a verdict, and
the one keyed route discarded its `Principal`. An operator could not detect a
leaked key in daily use from any surface the product gives them.

**The row is written for the keyed *act*, not for the indexing it triggers.**
The review's suggested shape threaded the principal down into the spawned run's
`repo_indexed` write. That attributes the wrong thing and misses the traffic
that matters: a run may short-circuit on an unchanged HEAD, may never start
(409), or may never be reached at all (404) — and probes and conflicts are
exactly what a leaked credential produces. So the route journals the delivery
itself, before the lookup, in its own committed session.

Each test below fails against the pre-fix tree for a different reason, which is
what makes them a regression suite rather than a restatement.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.services.api_keys import issue_key

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def committed_key():
    """Issue keys through a session of their own, and clean them up.

    `mark_key_used` writes through an independent session precisely so the bump
    survives a request that raises — which means a key living only inside the
    rollback-isolated fixture transaction is invisible to it, and the UPDATE
    would match zero rows. That is a property of the test's visibility, not of
    the writer, so the key has to be genuinely committed for the assertion to
    mean anything.
    """
    from tests.conftest import test_engine

    minted: list[uuid.UUID] = []

    async def _issue(name: str, scopes: list[str]) -> tuple[uuid.UUID, str]:
        # expire_on_commit=False: the id is read after the commit, and an
        # expired attribute would try to refresh itself outside the session's
        # greenlet.
        async with AsyncSession(test_engine, expire_on_commit=False) as own:
            row, token = await issue_key(own, name=name, scopes=scopes)
            await own.commit()
            minted.append(row.id)
            return row.id, token

    yield _issue

    async with AsyncSession(test_engine) as cleanup:
        for key_id in minted:
            await cleanup.execute(
                text("DELETE FROM api_keys WHERE id = CAST(:id AS uuid)"), {"id": str(key_id)}
            )
        await cleanup.commit()


async def _last_used_at(key_id: uuid.UUID):
    from tests.conftest import test_engine

    async with AsyncSession(test_engine) as verify:
        return (await verify.execute(
            select(ApiKey).where(ApiKey.id == key_id)
        )).scalar_one().last_used_at


async def _webhook_rows(event_type: str = "repo_webhook_received") -> list[dict]:
    """Read the journal through a session of its own.

    The route commits these rows independently of the request, so the test's
    own rolled-back fixture session cannot see them — reading through the
    request session would assert against an empty table and pass vacuously
    whatever the route did.
    """
    from tests.conftest import test_engine

    async with AsyncSession(test_engine) as verify:
        rows = (await verify.execute(
            text(
                "SELECT actor, CAST(api_key_id AS text) AS api_key_id, "
                "CAST(object_id AS text) AS object_id, source, payload "
                "FROM events WHERE event_type = :t ORDER BY created_at"
            ),
            {"t": event_type},
        )).mappings().all()
        return [dict(r) for r in rows]


async def test_a_keyed_delivery_journals_its_key_and_actor(
    client, session, auth_headers, tmp_path, monkeypatch,
):
    from tests.test_push_webhook import _capture_background_tasks, _make_local_repo, _mock_run

    repo_id = await _make_local_repo(client, auth_headers, tmp_path)
    _mock_run(monkeypatch)
    _capture_background_tasks(monkeypatch)
    row, token = await issue_key(session, name="ci-observability", scopes=["admin"])
    await session.commit()

    before = len(await _webhook_rows())
    resp = await client.post(
        f"/api/v1/repos/{repo_id}/webhook",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202, resp.text

    rows = await _webhook_rows()
    assert len(rows) == before + 1
    landed = rows[-1]
    assert landed["api_key_id"] == str(row.id)
    assert landed["actor"] == "ci-observability"
    assert landed["object_id"] == repo_id
    assert landed["payload"]["keyed"] is True


async def test_a_probe_against_a_repo_that_does_not_exist_still_journals(
    client, session, monkeypatch,
):
    """The 404 path is the one a leaked key walks while enumerating ids, and
    it is also the path whose request transaction never commits — so this is
    what proves the journal write is independent rather than incidental."""
    from tests.test_push_webhook import _capture_background_tasks, _mock_run

    _mock_run(monkeypatch)
    _capture_background_tasks(monkeypatch)
    _, token = await issue_key(session, name="ci-probe", scopes=["admin"])
    await session.commit()

    before = len(await _webhook_rows())
    missing = uuid.uuid4()
    resp = await client.post(
        f"/api/v1/repos/{missing}/webhook",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404

    rows = await _webhook_rows()
    assert len(rows) == before + 1
    assert rows[-1]["actor"] == "ci-probe"
    assert rows[-1]["object_id"] == str(missing)


async def test_a_keyed_call_bumps_last_used_at(client, committed_key, monkeypatch):
    """`last_used_at` had zero writers, so the settings card's "never used"
    was structurally true of every key however heavily used."""
    from tests.test_push_webhook import _capture_background_tasks, _mock_run

    _mock_run(monkeypatch)
    _capture_background_tasks(monkeypatch)
    key_id, token = await committed_key("ci-lastused", ["admin"])
    assert await _last_used_at(key_id) is None

    await client.post(
        f"/api/v1/repos/{uuid.uuid4()}/webhook",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert await _last_used_at(key_id) is not None


async def test_the_bump_is_throttled_per_key(committed_key, monkeypatch):
    """Every authenticated MCP request marks its key, so the bump moves the
    column at most once a minute rather than writing on every call."""
    from datetime import datetime, timedelta, timezone

    from app.services import api_keys

    key_id, _token = await committed_key("ci-throttle", ["read"])
    start = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)

    await api_keys.mark_key_used(key_id, now=start)
    assert await _last_used_at(key_id) == start

    await api_keys.mark_key_used(key_id, now=start + timedelta(seconds=30))
    assert await _last_used_at(key_id) == start

    # Another process (or this one after a restart) holds no memo; the
    # UPDATE's own predicate keeps the same window.
    monkeypatch.setattr(api_keys, "_last_marked", {})
    await api_keys.mark_key_used(key_id, now=start + timedelta(seconds=45))
    assert await _last_used_at(key_id) == start

    later = start + timedelta(seconds=61)
    await api_keys.mark_key_used(key_id, now=later)
    assert await _last_used_at(key_id) == later


async def test_a_rejected_key_does_not_count_as_use(client, committed_key, monkeypatch):
    """A credential that authenticates and then fails the scope gate did not
    use the key for anything, so it must not refresh the operator's
    staleness signal."""
    from tests.test_push_webhook import _capture_background_tasks, _mock_run

    _mock_run(monkeypatch)
    _capture_background_tasks(monkeypatch)
    key_id, token = await committed_key("ci-wrongscope", ["capture"])

    resp = await client.post(
        f"/api/v1/repos/{uuid.uuid4()}/webhook",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403

    assert await _last_used_at(key_id) is None


async def test_a_human_delivery_journals_no_key_rather_than_a_fabricated_one(
    client, auth_headers, tmp_path, monkeypatch,
):
    from tests.test_push_webhook import _capture_background_tasks, _make_local_repo, _mock_run

    repo_id = await _make_local_repo(client, auth_headers, tmp_path)
    _mock_run(monkeypatch)
    _capture_background_tasks(monkeypatch)

    before = len(await _webhook_rows())
    resp = await client.post(f"/api/v1/repos/{repo_id}/webhook", headers=auth_headers)
    assert resp.status_code == 202, resp.text

    rows = await _webhook_rows()
    assert len(rows) == before + 1
    assert rows[-1]["api_key_id"] is None
    assert rows[-1]["payload"]["keyed"] is False
    assert rows[-1]["actor"], "a human delivery still names its actor"

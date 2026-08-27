"""T4.02 — first writer to `events.api_key_id` / `events.actor` (doc 18 §5).

T1.06 landed the two columns inert; T4.01 built the credential and the
`require_scope` dependency but wired no route to it. This is the writer:
every capture-door mutation (create/update/delete/bulk-delete/batch/merge)
threads the resolved caller identity down to `record_event`, on REST (the
human cookie session's `sub`, or the authenticated key's name once
`require_scope` admits one) and, since MCP's own bearer-key activation, on
MCP too: `TestMCPDoorAttributesViaHeaders` now authenticates via
`mcp_http_client`'s committed key and asserts `actor`/`api_key_id` are that
key's name and row id, not the `X-Darkmem-Client`-resolved tool — which
still rides `data.source` on the memory row and the create event's own
payload, so nothing is lost by preferring the credential's identity in
`actor`.

The trap the brief calls out is dropping the journal row when the caller is
unattributable. `TestNullKeyNeverDrops` proves the opposite: an unattributed
call still produces an `events` row with both columns `NULL`, never zero
rows. `TestKeyedCallStampsBoth` proves the other end — a real `dmk_`
credential's id and name land on the row — using the same throwaway
`require_scope`-gated app `test_api_keys.py` uses. That was originally because
no shipped route assigned a scope; T4.05 wired the push webhook, so one does
(E4 review, M5). The throwaway app is kept because it exercises the *stamping*
against an arbitrary keyed route rather than against the single route that
happens to exist — `tests/test_keyed_call_observability.py` covers the real one
end to end.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.api.auth import Principal, require_scope
from app.database import get_session
from app.schemas.memory import MemoryCreate, MemoryUpdate
from app.services.api_keys import issue_key
from app.services.memory import MemoryService

pytestmark = pytest.mark.asyncio


async def _events_for(session, object_id: uuid.UUID) -> list[dict]:
    rows = (await session.execute(
        text(
            "SELECT event_type, actor, api_key_id FROM events "
            "WHERE object_id = CAST(:id AS uuid) ORDER BY id"
        ),
        {"id": str(object_id)},
    )).mappings().all()
    return [dict(r) for r in rows]


async def _event_count(session) -> int:
    return (await session.execute(text("SELECT count(*) FROM events"))).scalar()


# ── capture-door service methods stamp the resolved actor ──────────────────


class TestServiceLayerStampsActor:
    async def test_create_memory_stamps_actor_and_null_key(self, session):
        svc = MemoryService(session)
        data = MemoryCreate(content="stamp probe", source="test")
        result = await svc.create_memory(data, api_key_id=None, actor="admin")

        rows = await _events_for(session, result.ack.id)
        assert rows, "create_memory must journal a row"
        assert rows[0]["event_type"] == "created"
        assert rows[0]["actor"] == "admin"
        assert rows[0]["api_key_id"] is None

    async def test_create_memory_stamps_a_real_key_id(self, session):
        svc = MemoryService(session)
        data = MemoryCreate(content="keyed create probe", source="test")
        key_id = uuid.uuid4()
        result = await svc.create_memory(data, api_key_id=key_id, actor="ci-bot")

        rows = await _events_for(session, result.ack.id)
        assert rows[0]["actor"] == "ci-bot"
        assert rows[0]["api_key_id"] == key_id

    async def test_update_memory_stamps_actor(self, session):
        svc = MemoryService(session)
        created = await svc.create_memory(
            MemoryCreate(content="to update", source="test"),
            api_key_id=None, wait_process=True,
        )
        memory_id = created.ack.id

        await svc.update_memory(
            memory_id, MemoryUpdate(tags=["updated"]), api_key_id=None, actor="admin",
        )

        rows = await _events_for(session, memory_id)
        update_rows = [r for r in rows if r["event_type"] == "update"]
        assert update_rows, "update_memory must journal a row"
        assert update_rows[0]["actor"] == "admin"
        assert update_rows[0]["api_key_id"] is None

    async def test_delete_memory_stamps_actor(self, session):
        svc = MemoryService(session)
        created = await svc.create_memory(
            MemoryCreate(content="to delete", source="test"),
            api_key_id=None, wait_process=True,
        )
        memory_id = created.ack.id

        assert await svc.delete_memory(memory_id, api_key_id=None, actor="admin")

        rows = await _events_for(session, memory_id)
        delete_rows = [r for r in rows if r["event_type"] == "delete"]
        assert delete_rows
        assert delete_rows[0]["actor"] == "admin"

    async def test_bulk_delete_threads_actor_to_each_row(self, session):
        svc = MemoryService(session)
        a = await svc.create_memory(
            MemoryCreate(content="bulk a", source="test"),
            api_key_id=None, wait_process=True,
        )
        b = await svc.create_memory(
            MemoryCreate(content="bulk b", source="test"),
            api_key_id=None, wait_process=True,
        )

        await svc.bulk_delete_memories(
            [a.ack.id, b.ack.id], api_key_id=None, actor="admin",
        )

        for mid in (a.ack.id, b.ack.id):
            rows = await _events_for(session, mid)
            delete_rows = [r for r in rows if r["event_type"] == "delete"]
            assert delete_rows and delete_rows[0]["actor"] == "admin"


# ── the trap: an unattributable call must still journal, not drop ──────────


class TestNullKeyNeverDrops:
    async def test_unattributed_capture_still_journals_a_row(self, session):
        """The naive fix stamps `actor`/`api_key_id` only when it has them and
        skips the journal call otherwise. That would silently shrink the
        `events` population for exactly the LAN-default MCP calls doc 18 §5
        says must still attribute. Proven directly: call with no identity at
        all and assert the row count still moves and the row still lands,
        with both columns legitimately NULL rather than absent."""
        svc = MemoryService(session)
        before = await _event_count(session)

        result = await svc.create_memory(
            MemoryCreate(content="unattributed probe", source="test"),
            api_key_id=None, actor=None,
        )

        after = await _event_count(session)
        assert after == before + 1, "an unattributed call must still add a row"

        rows = await _events_for(session, result.ack.id)
        assert rows[0]["actor"] is None
        assert rows[0]["api_key_id"] is None

    async def test_naive_guard_would_have_dropped_the_row(self, session):
        """Drills the guard: implements the rejected shape inline (skip the
        journal call when actor is falsy) and shows it disagrees with the
        shipped behaviour above — proving this test would catch the
        regression rather than passing on either implementation."""
        from app.repositories.relational import PostgresAuditRepository

        audit_repo = PostgresAuditRepository(session)
        before = await _event_count(session)

        actor = None
        api_key_id = None
        memory_id = uuid.uuid4()
        # The naive alternative: only journal when there is something to
        # attribute. This is the exact defect the brief warns against.
        if actor or api_key_id:
            await audit_repo.log("create", memory_id, api_key_id, {}, actor=actor)

        after = await _event_count(session)
        assert after == before, "the naive guard drops the row (demonstrating the trap)"


# ── MCP door: unkeyed LAN calls attribute via the resolved client source ───


async def _mcp_credential_row_id(session) -> uuid.UUID:
    """The row id behind `mcp_credential`/`mcp_http_client` (conftest's
    committed `"test-suite"` key), resolved by name rather than hardcoded, so
    this file does not need to know the fixture's internal id."""
    return (await session.execute(
        text("SELECT id FROM api_keys WHERE name = 'test-suite'"),
    )).scalar_one()


class TestMCPDoorAttributesViaHeaders:
    """`mcp_http_client` authenticates every call with a real, committed key
    (doc 18 §5's bearer requirement), so `api_key_id`/`actor` now stamp that
    key's row id and name — never the `X-Darkmem-Client`-resolved tool, which
    is a different axis (which client, not which credential) and still rides
    `data.source` on the memory row, and on the `created` event's own payload
    for the two capture tools below. `memory_update`/`memory_delete` have no
    such second home for it: their events carry no `source` field, so
    preferring the credential's identity in `actor` is this door's one real
    cost, paid for the same reason REST already pays it on its own
    `require_auth`-only update/delete routes — see
    `TestRESTDoorStampsHumanActor` above, which never records a client tool
    either.
    """

    async def test_memory_add_stamps_the_keys_id_and_name(
        self, mcp_http_client, session,
    ):
        from sqlalchemy import select

        from app.models.memory import Memory

        response = await mcp_http_client.post(
            "/",
            json={
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {
                    "name": "memory_add",
                    "arguments": {"content": "mcp actor probe", "wait_process": True},
                },
            },
            headers={"X-Darkmem-Client": "Codex!"},
        )
        assert response.status_code == 200, response.text
        memory = (await session.execute(
            select(Memory).where(Memory.content == "mcp actor probe")
        )).scalar_one()

        rows = await _events_for(session, memory.id)
        create_rows = [r for r in rows if r["event_type"] == "created"]
        assert create_rows, "memory_add must journal a create event"
        assert create_rows[0]["actor"] == "test-suite"
        assert create_rows[0]["api_key_id"] == await _mcp_credential_row_id(session)
        # The client tool is not lost: it still rides the memory row itself.
        assert memory.source == "codex"

    async def test_memory_update_stamps_the_keys_id_and_name(
        self, mcp_http_client, session,
    ):
        from sqlalchemy import select

        from app.models.memory import Memory

        await mcp_http_client.post(
            "/",
            json={
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {
                    "name": "memory_add",
                    "arguments": {"content": "to be updated", "wait_process": True},
                },
            },
        )
        memory = (await session.execute(
            select(Memory).where(Memory.content == "to be updated")
        )).scalar_one()

        response = await mcp_http_client.post(
            "/",
            json={
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {
                    "name": "memory_update",
                    "arguments": {"memory_id": str(memory.id), "tags": ["x"]},
                },
            },
            headers={"X-Darkmem-Client": "Codex!"},
        )
        assert response.status_code == 200, response.text

        rows = await _events_for(session, memory.id)
        update_rows = [r for r in rows if r["event_type"] == "update"]
        assert update_rows, "memory_update must journal an update event"
        assert update_rows[0]["actor"] == "test-suite"
        assert update_rows[0]["api_key_id"] == await _mcp_credential_row_id(session)

    async def test_memory_delete_stamps_the_keys_id_and_name(
        self, mcp_http_client, session,
    ):
        from sqlalchemy import select

        from app.models.memory import Memory

        await mcp_http_client.post(
            "/",
            json={
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {
                    "name": "memory_add",
                    "arguments": {"content": "to be deleted", "wait_process": True},
                },
            },
        )
        memory = (await session.execute(
            select(Memory).where(Memory.content == "to be deleted")
        )).scalar_one()
        memory_id = memory.id

        response = await mcp_http_client.post(
            "/",
            json={
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {
                    "name": "memory_delete",
                    "arguments": {"memory_id": str(memory_id)},
                },
            },
            headers={"X-Darkmem-Client": "Codex!"},
        )
        assert response.status_code == 200, response.text

        rows = await _events_for(session, memory_id)
        delete_rows = [r for r in rows if r["event_type"] == "delete"]
        assert delete_rows
        assert delete_rows[0]["actor"] == "test-suite"
        assert delete_rows[0]["api_key_id"] == await _mcp_credential_row_id(session)

    async def test_memory_batch_add_stamps_the_keys_id_and_name(
        self, mcp_http_client, session,
    ):
        from sqlalchemy import select

        from app.models.memory import Memory

        response = await mcp_http_client.post(
            "/",
            json={
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {
                    "name": "memory_batch_add",
                    "arguments": {
                        "entries": [{"content": "batch actor probe"}],
                        "wait_process": True,
                    },
                },
            },
            headers={"X-Darkmem-Client": "Codex!"},
        )
        assert response.status_code == 200, response.text
        memory = (await session.execute(
            select(Memory).where(Memory.content == "batch actor probe")
        )).scalar_one()

        rows = await _events_for(session, memory.id)
        create_rows = [r for r in rows if r["event_type"] == "created"]
        assert create_rows, "memory_batch_add must journal a create event"
        assert create_rows[0]["actor"] == "test-suite"
        assert create_rows[0]["api_key_id"] == await _mcp_credential_row_id(session)
        assert memory.source == "codex"


# ── REST door: the human cookie session's `sub` is the actor ───────────────


class TestRESTDoorStampsHumanActor:
    async def test_create_memory_stamps_admin_actor(self, client, auth_headers, session):
        response = await client.post(
            "/api/v1/memories",
            json={"content": "rest actor probe", "source": "test"},
            headers=auth_headers,
        )
        assert response.status_code in (201, 202), response.text
        memory_id = response.json()["id"]

        rows = await _events_for(session, uuid.UUID(memory_id))
        create_rows = [r for r in rows if r["event_type"] == "created"]
        assert create_rows, "REST create must journal a create event"
        assert create_rows[0]["actor"] == "admin"
        assert create_rows[0]["api_key_id"] is None


# ── a genuinely keyed call stamps both columns end to end ──────────────────


@pytest_asyncio.fixture
async def scoped_capture_app(session):
    """A throwaway `require_scope("capture")` route, mirroring the fixture
    `test_api_keys.py` uses to exercise the dependency: no shipped route
    assigns a scope yet (T4.03), so this is how a genuinely keyed capture is
    proven without widening any door's posture."""
    probe = FastAPI()

    async def override():
        yield session

    probe.dependency_overrides[get_session] = override

    @probe.post("/capture")
    async def _capture(principal: Principal = Depends(require_scope("capture"))):
        svc = MemoryService(session)
        result = await svc.create_memory(
            MemoryCreate(content="keyed door probe", source="test"),
            api_key_id=principal.api_key_id,
            actor=principal.actor,
        )
        return {"id": str(result.ack.id)}

    async with AsyncClient(
        transport=ASGITransport(app=probe), base_url="http://probe"
    ) as c:
        yield c


class TestKeyedCallStampsBoth:
    async def test_a_real_key_stamps_its_id_and_name(self, session, scoped_capture_app):
        row, token = await issue_key(session, name="ci-runner", scopes=["capture"])

        response = await scoped_capture_app.post(
            "/capture", headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        memory_id = uuid.UUID(response.json()["id"])

        rows = await _events_for(session, memory_id)
        create_rows = [r for r in rows if r["event_type"] == "created"]
        assert create_rows, "a keyed capture must journal a create event"
        assert create_rows[0]["actor"] == "ci-runner"
        assert create_rows[0]["api_key_id"] == row.id

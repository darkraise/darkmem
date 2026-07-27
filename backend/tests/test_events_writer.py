"""The narrow events writer that replaces audit_log's writes (T0.12c).

audit_log is dropped by the baseline (doc 04 §7/§8.1), but its rows were a
live security audit trail. This writer keeps that trail on the substrate
doc 04 §8.1 fixes as authoritative from day one.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services.events import record_event


@pytest.mark.asyncio
async def test_record_event_writes_a_row(session):
    await record_event(
        session,
        event_type="auth_login_success",
        object_type="system",
        payload={"ip": "10.0.0.1"},
    )
    await session.commit()
    row = (
        await session.execute(
            text("SELECT event_type, object_type, payload FROM events "
                 "WHERE event_type = 'auth_login_success'")
        )
    ).one()
    assert row.event_type == "auth_login_success"
    assert row.object_type == "system"
    assert row.payload == {"ip": "10.0.0.1"}


@pytest.mark.asyncio
async def test_record_event_defaults_payload_to_empty_object(session):
    await record_event(session, event_type="auth_logout", object_type="system")
    await session.commit()
    payload = (
        await session.execute(
            text("SELECT payload FROM events WHERE event_type = 'auth_logout'")
        )
    ).scalar_one()
    assert payload == {}

"""A masked secret is only kept while the endpoint it was stored for is unchanged."""
from __future__ import annotations

import pytest

from app.services import backup_config as bc
from tests.test_backup_config import SSH, WORKER

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    "dest,group,secret,field,changed",
    [
        (WORKER, "worker", "token", "url", "http://203.0.113.9:8100"),
        (SSH, "ssh", "private_key", "host", "203.0.113.9"),
        (SSH, "ssh", "private_key", "port", 2222),
        (SSH, "ssh", "private_key", "user", "other"),
    ],
)
async def test_destination_host_change_needs_the_secret_again(
    client, auth_headers, session, dest, group, secret, field, changed,
):
    await bc.save_destinations(session, {"destinations": [dest]})

    moved = {**dest, group: {**dest[group], secret: bc.MASKED, field: changed}}
    r = await client.put(
        "/api/v1/config/backup-destinations",
        json={"destinations": [moved]}, headers=auth_headers,
    )
    assert r.status_code == 422
    assert secret in r.json()["detail"]

    same = {**dest, group: {**dest[group], secret: bc.MASKED}}
    r = await client.put(
        "/api/v1/config/backup-destinations",
        json={"destinations": [same]}, headers=auth_headers,
    )
    assert r.status_code == 200
    raw = await bc.load_destinations(session, masked=False)
    assert getattr(getattr(raw[0], group), secret) == dest[group][secret]


@pytest.mark.parametrize(
    "change", [{"base_url": "http://elsewhere.example/v1"}, {"api_kind": "ollama"}],
)
async def test_provider_url_change_needs_the_key_again(client, auth_headers, change):
    await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "rebind", "api_kind": "openai", "base_url": "http://x/v1", "api_key": "real"},
        headers=auth_headers,
    )
    body = {"api_kind": "openai", "base_url": "http://x/v1", **change}

    masked = await client.put(
        "/api/v1/config/llm-providers/rebind",
        json={**body, "api_key": "***"}, headers=auth_headers,
    )
    assert masked.status_code == 422
    assert "api_key" in masked.text

    reentered = await client.put(
        "/api/v1/config/llm-providers/rebind",
        json={**body, "api_key": "real"}, headers=auth_headers,
    )
    assert reentered.status_code == 200

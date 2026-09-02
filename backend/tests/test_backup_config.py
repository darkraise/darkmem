"""The `backup_destinations` config row and its single-door REST pair.

Two properties carry the increment: a secret that leaves the process is
masked, and a masked secret coming back in means "unchanged" rather than
"store the literal ***". The second is what makes the settings form
round-trippable without ever putting a private key on the wire.

The third is the encrypt-before-egress rule (spec section 9.4 rule 1),
enforced at save rather than at ship: a destination that would send bytes
off this host without an age recipient can never be stored, so no later
code path has to remember to check.
"""
from __future__ import annotations

import pytest

from app.services import backup_config as bc

LOCAL = {"name": "local", "kind": "local", "enabled": True, "retention_keep": 14}
SSH = {
    "name": "nas",
    "kind": "ssh",
    "enabled": True,
    "retention_keep": 30,
    "age_recipient": "age1qqqqexamplerecipient",
    "ssh": {
        "host": "192.0.2.10",
        "port": 22,
        "user": "backup",
        "remote_dir": "/srv/darkmem",
        "host_key": "192.0.2.10 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5examplekey",
        "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nexample\n",
    },
}
S3 = {
    "name": "r2",
    "kind": "s3",
    "enabled": False,
    "retention_keep": 8,
    "age_recipient": "age1qqqqexamplerecipient",
    "s3": {
        "endpoint_url": "https://x.r2.cloudflarestorage.com",
        "bucket": "b",
        "prefix": "darkmem/",
        "region": "auto",
        "access_key_id": "AK",
        "secret_access_key": "SK",
    },
}


async def test_round_trip_and_masking(session):
    await bc.save_destinations(session, {"destinations": [LOCAL, SSH, S3]})
    masked = [d.model_dump() for d in await bc.load_destinations(session, masked=True)]
    assert masked[1]["ssh"]["private_key"] == bc.MASKED
    assert masked[2]["s3"]["secret_access_key"] == bc.MASKED
    # Non-secret fields survive masking untouched.
    assert masked[1]["ssh"]["host"] == "192.0.2.10"

    raw = await bc.load_destinations(session, masked=False)
    assert raw[1].ssh.private_key.startswith("-----BEGIN")
    assert raw[2].s3.secret_access_key == "SK"


async def test_put_with_mask_keeps_stored_secret(session):
    await bc.save_destinations(session, {"destinations": [SSH]})
    edited = {
        **SSH,
        "retention_keep": 60,
        "ssh": {**SSH["ssh"], "private_key": bc.MASKED},
    }
    await bc.save_destinations(session, {"destinations": [edited]})
    raw = await bc.load_destinations(session, masked=False)
    assert raw[0].retention_keep == 60
    assert raw[0].ssh.private_key.startswith("-----BEGIN")


async def test_mask_with_no_stored_value_is_refused(session):
    """A mask means "the value you already hold". With nothing held it means
    nothing, and storing the literal *** would produce a destination that
    authenticates with three asterisks."""
    fresh = {**SSH, "ssh": {**SSH["ssh"], "private_key": bc.MASKED}}
    with pytest.raises(bc.DestinationInvalid):
        await bc.save_destinations(session, {"destinations": [fresh]})


async def test_egress_without_recipient_is_refused(session):
    bad = {**SSH, "age_recipient": None}
    with pytest.raises(bc.DestinationInvalid):
        await bc.save_destinations(session, {"destinations": [bad]})
    # `local` is the one kind allowed unencrypted (spec section 9.4 rule 1):
    # nothing leaves the host, so there is no egress to encrypt before.
    await bc.save_destinations(session, {"destinations": [LOCAL]})


async def test_duplicate_names_refused(session):
    with pytest.raises(bc.DestinationInvalid):
        await bc.save_destinations(session, {"destinations": [LOCAL, LOCAL]})


async def test_unknown_kind_refused(session):
    with pytest.raises(bc.DestinationInvalid):
        await bc.save_destinations(
            session, {"destinations": [{**LOCAL, "kind": "ftp"}]}
        )


async def test_kind_without_its_settings_refused(session):
    with pytest.raises(bc.DestinationInvalid):
        await bc.save_destinations(
            session, {"destinations": [{**SSH, "ssh": None}]}
        )


async def test_retention_out_of_range_refused(session):
    with pytest.raises(bc.DestinationInvalid):
        await bc.save_destinations(
            session, {"destinations": [{**LOCAL, "retention_keep": 0}]}
        )


async def test_empty_when_never_configured(session):
    assert await bc.load_destinations(session) == []


# ---------------------------------------------------------------------------
# The REST pair
# ---------------------------------------------------------------------------


async def test_routes_require_auth(client):
    assert (await client.get("/api/v1/config/backup-destinations")).status_code == 401
    assert (
        await client.put("/api/v1/config/backup-destinations", json={"destinations": []})
    ).status_code == 401


async def test_get_returns_masked_destinations(client, auth_headers, session):
    await bc.save_destinations(session, {"destinations": [SSH]})
    response = await client.get(
        "/api/v1/config/backup-destinations", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["destinations"][0]["ssh"]["private_key"] == bc.MASKED


async def test_put_echoes_the_mask_never_the_secret(client, auth_headers, session):
    response = await client.put(
        "/api/v1/config/backup-destinations",
        headers=auth_headers,
        json={"destinations": [SSH]},
    )
    assert response.status_code == 200
    assert response.json()["destinations"][0]["ssh"]["private_key"] == bc.MASKED
    raw = await bc.load_destinations(session, masked=False)
    assert raw[0].ssh.private_key.startswith("-----BEGIN")


async def test_put_rejects_an_invalid_destination_with_422(client, auth_headers):
    response = await client.put(
        "/api/v1/config/backup-destinations",
        headers=auth_headers,
        json={"destinations": [{**SSH, "age_recipient": None}]},
    )
    assert response.status_code == 422


async def test_the_vocabulary_carries_the_ship_events():
    from app.services.events import EVENT_TYPES

    assert "backup_shipped" in EVENT_TYPES
    assert "backup_verify_failed" in EVENT_TYPES


# ---------------------------------------------------------------------------
# Increment 7: the `worker` kind
# ---------------------------------------------------------------------------

WORKER = {
    "name": "attic",
    "kind": "worker",
    "enabled": True,
    "retention_keep": 7,
    "age_recipient": "age1qqqqexamplerecipient",
    "worker": {"url": "http://192.0.2.20:8100", "token": "a-receiver-token-of-32-chars-plus"},
}


async def test_worker_token_is_masked_and_round_trips(session):
    await bc.save_destinations(session, {"destinations": [WORKER]})
    masked = await bc.load_destinations(session, masked=True)
    assert masked[0].worker.token == bc.MASKED
    assert masked[0].worker.url == "http://192.0.2.20:8100"

    raw = await bc.load_destinations(session, masked=False)
    assert raw[0].worker.token == WORKER["worker"]["token"]


async def test_worker_mask_on_put_keeps_the_stored_token(session):
    await bc.save_destinations(session, {"destinations": [WORKER]})
    edited = {
        **WORKER,
        "retention_keep": 21,
        "worker": {**WORKER["worker"], "token": bc.MASKED},
    }
    await bc.save_destinations(session, {"destinations": [edited]})
    raw = await bc.load_destinations(session, masked=False)
    assert raw[0].retention_keep == 21
    assert raw[0].worker.token == WORKER["worker"]["token"]


async def test_a_worker_destination_must_encrypt(session):
    """The receiver stores ciphertext only. It is a non-local kind, so rule 1
    reaches it for the same reason it reaches ssh and s3 -- but this one is
    worth its own test, because the receiver's bearer token is authorisation
    and not confidentiality, so the encryption is the only thing protecting
    the bytes in flight and at rest on the worker."""
    with pytest.raises(bc.DestinationInvalid):
        await bc.save_destinations(
            session, {"destinations": [{**WORKER, "age_recipient": None}]}
        )


async def test_worker_settings_are_required_for_the_worker_kind(session):
    with pytest.raises(bc.DestinationInvalid):
        await bc.save_destinations(
            session, {"destinations": [{**WORKER, "worker": None}]}
        )

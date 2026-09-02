"""`GET /api/v1/backups/inventory` — the informed-decision surface (spec §9.6).

Two properties carry it. One unreachable destination must not blank the whole
inventory: a NAS being off is exactly when an operator most needs to see what
the *other* destinations hold. And the last outcome per destination comes from
the journal the ship already writes, so the surface cannot claim a verification
the ship never recorded.

There is deliberately no restore verb anywhere near this route. Restoring is a
shell command by design (§9.6); this read exists so the human running it knows
which snapshot to name.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text as sa_text

from app.services import backup_config as bc
from app.services.backup_ship import SnapshotInfo, _stamp_of

LOCAL = {"name": "disk", "kind": "local", "enabled": True, "retention_keep": 14}
NAS = {
    "name": "nas",
    "kind": "ssh",
    "enabled": True,
    "retention_keep": 30,
    "age_recipient": "age1qqqqexample",
    "ssh": {
        "host": "192.0.2.10",
        "port": 22,
        "user": "backup",
        "remote_dir": "/srv/darkmem",
        "host_key": "192.0.2.10 ssh-ed25519 AAAA",
        "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nx\n",
    },
}


class _Listing:
    def __init__(self, name, names):
        self.name = name
        self._names = names

    async def list_snapshots(self):
        return [
            SnapshotInfo(name=n, size=100, modified_at=_stamp_of(n)) for n in self._names
        ]


class _Unreachable:
    def __init__(self, name):
        self.name = name

    async def list_snapshots(self):
        raise RuntimeError("the NAS is unplugged")


@pytest.fixture
def two_destinations(monkeypatch):
    from app.api.routes import backups

    good = _Listing("disk", ["darkmem-app-20260101-000000.sql.gz"])
    bad = _Unreachable("nas")

    def _build(cfg):
        return good if cfg.name == "disk" else bad

    monkeypatch.setattr(backups, "build_destination", _build)
    return good, bad


async def test_requires_auth(client):
    assert (await client.get("/api/v1/backups/inventory")).status_code == 401


async def test_a_never_configured_install_reads_empty(client, auth_headers):
    response = await client.get("/api/v1/backups/inventory", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"destinations": []}


async def test_one_unreachable_destination_does_not_blank_the_inventory(
    client, auth_headers, session, two_destinations,
):
    await bc.save_destinations(session, {"destinations": [LOCAL, NAS]})

    body = (
        await client.get("/api/v1/backups/inventory", headers=auth_headers)
    ).json()

    rows = {d["name"]: d for d in body["destinations"]}
    assert rows["disk"]["error"] is None
    assert [s["name"] for s in rows["disk"]["snapshots"]] == [
        "darkmem-app-20260101-000000.sql.gz"
    ]
    assert "unplugged" in rows["nas"]["error"]
    assert rows["nas"]["snapshots"] == []


async def test_the_last_outcome_is_the_newest_journal_row_per_destination(
    client, auth_headers, session, two_destinations,
):
    """Read off `events`, which the ship already writes -- so the badge cannot
    assert a verification nobody recorded."""
    await bc.save_destinations(session, {"destinations": [LOCAL, NAS]})
    for event_type, destination, payload_extra in (
        ("backup_shipped", "disk", '"sha256": "a"'),
        ("backup_verify_failed", "disk", '"error": "older failure"'),
        ("backup_verify_failed", "nas", '"error": "the NAS is unplugged"'),
    ):
        await session.execute(
            sa_text(
                "INSERT INTO events (event_type, object_type, source, payload) "
                "VALUES (:t, 'system', 'backup_ship', CAST(:p AS jsonb))"
            ),
            {
                "t": event_type,
                "p": '{"destination": "%s", %s}' % (destination, payload_extra),
            },
        )
    await session.flush()

    body = (
        await client.get("/api/v1/backups/inventory", headers=auth_headers)
    ).json()
    rows = {d["name"]: d for d in body["destinations"]}

    # The *newest* row wins, and for `disk` that is the failure written second.
    assert rows["disk"]["last_outcome"]["event_type"] == "backup_verify_failed"
    assert rows["nas"]["last_outcome"]["event_type"] == "backup_verify_failed"


async def test_a_destination_with_no_run_yet_reads_null_rather_than_ok(
    client, auth_headers, session, two_destinations,
):
    """"Never shipped" and "shipped and verified" must not render the same."""
    await bc.save_destinations(session, {"destinations": [LOCAL]})
    body = (
        await client.get("/api/v1/backups/inventory", headers=auth_headers)
    ).json()
    assert body["destinations"][0]["last_outcome"] is None


async def test_no_secret_reaches_the_inventory(
    client, auth_headers, session, two_destinations,
):
    await bc.save_destinations(session, {"destinations": [NAS]})
    raw = (
        await client.get("/api/v1/backups/inventory", headers=auth_headers)
    ).text
    assert "BEGIN OPENSSH" not in raw
    assert "private_key" not in raw


def test_the_module_serves_no_verb_that_mutates():
    """§9.6: restoring is deliberately a shell command and never a route. A
    POST appearing here is the plan being violated, not extended."""
    from app.api.routes import backups

    methods = {
        method
        for route in backups.router.routes
        for method in getattr(route, "methods", set())
    }
    assert methods <= {"GET", "HEAD"}, f"the inventory router grew {methods}"

"""The worker's one write door, and the proof it is not part of the app.

The receiver exists because an https write door *inside* a read-only instance
is a contradiction (review B1). That claim is only true while the process
shares nothing with the app but a filesystem, so the closure walk at the
bottom is not decoration -- it is the claim.

Everything else here is about the two ways a snapshot store goes quietly
wrong: a torn upload that gets listed as a snapshot (a restore would select it
as the newest good one), and a name that is not one of ours.
"""
from __future__ import annotations

import os

import httpx
import pytest

from app import worker_receiver as wr

TOKEN = "a-receiver-token-of-at-least-32-characters"
NAME = "darkmem-app-20260101-000000.sql.gz.age"


@pytest.fixture
def receiver(tmp_path, monkeypatch):
    monkeypatch.setenv("RECEIVER_TOKEN", TOKEN)
    monkeypatch.setenv("RECEIVER_DIR", str(tmp_path))
    return tmp_path


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=wr.app), base_url="http://receiver"
    )


AUTH = {"Authorization": f"Bearer {TOKEN}"}


# ---------------------------------------------------------------------------
# Authorisation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer wrong"}, {"Authorization": TOKEN}],
    ids=["absent", "wrong", "no-scheme"],
)
async def test_every_verb_refuses_without_the_bearer(receiver, headers):
    async with _client() as client:
        assert (await client.get("/snapshots", headers=headers)).status_code == 401
        assert (
            await client.put(f"/snapshots/{NAME}", content=b"x", headers=headers)
        ).status_code == 401
        assert (
            await client.get(f"/snapshots/{NAME}", headers=headers)
        ).status_code == 401
        assert (
            await client.delete(f"/snapshots/{NAME}", headers=headers)
        ).status_code == 401


def test_a_short_token_refuses_to_start(monkeypatch, tmp_path):
    """Below 32 characters a bearer is not a secret, and this is the only
    thing between the network and this directory."""
    monkeypatch.setenv("RECEIVER_TOKEN", "short")
    monkeypatch.setenv("RECEIVER_DIR", str(tmp_path))
    with pytest.raises(wr.ReceiverMisconfigured):
        wr._startup()


def test_an_unwritable_directory_refuses_to_start(monkeypatch, tmp_path):
    """The B-1 twin. The receiver runs the same image as the app, so it runs
    as the same unprivileged user, and a host bind mount is not chowned by
    Docker. Accepting an upload and failing on the write would make a green
    boot mean nothing -- and on the worker host this is the only thing the
    process does, so the failure is total."""
    monkeypatch.setenv("RECEIVER_TOKEN", TOKEN)
    monkeypatch.setenv("RECEIVER_DIR", str(tmp_path / "never-created"))
    with pytest.raises(wr.ReceiverMisconfigured) as exc:
        wr._startup()
    assert str(os.getuid()) in str(exc.value)


# ---------------------------------------------------------------------------
# The upload
# ---------------------------------------------------------------------------


async def test_put_writes_a_part_then_renames(receiver):
    async with _client() as client:
        response = await client.put(
            f"/snapshots/{NAME}", content=b"snapshot bytes", headers=AUTH
        )
    assert response.status_code == 201
    assert response.json() == {"name": NAME, "bytes": 14}
    assert (receiver / NAME).read_bytes() == b"snapshot bytes"
    assert not list(receiver.glob("*.part"))


async def test_a_torn_upload_leaves_no_listable_snapshot(receiver):
    """A restore selects the newest snapshot. A half-transferred file that got
    the final name would be that selection."""

    async def _dies_midway():
        yield b"the first half"
        raise httpx.ReadError("client vanished")

    async with _client() as client:
        with pytest.raises(Exception):
            await client.put(f"/snapshots/{NAME}", content=_dies_midway(), headers=AUTH)

    assert not (receiver / NAME).exists()
    assert not list(receiver.glob("*.part"))


@pytest.mark.parametrize(
    "name",
    [
        "../../etc/passwd",
        "darkmem-app-x.sql.gz/../evil",
        "darkmem-20260101-000000.sql.gz",
        "notes.txt",
        "darkmem-app-x.tar",
    ],
    ids=["traversal", "embedded-traversal", "systemd-prefix", "foreign", "wrong-suffix"],
)
async def test_a_name_that_is_not_ours_is_refused(receiver, name):
    """Path traversal and foreign-prefix uploads die at the same check. The
    systemd producer's own prefix is refused too: this store holds one
    producer's artefacts, so nothing else can accumulate here unnoticed."""
    async with _client() as client:
        response = await client.put(f"/snapshots/{name}", content=b"x", headers=AUTH)
    assert response.status_code in (404, 422)
    assert not list(receiver.rglob("*")) or not any(
        p.is_file() for p in receiver.rglob("*")
    )


async def test_an_oversized_upload_is_refused_and_leaves_nothing(receiver, monkeypatch):
    monkeypatch.setenv("RECEIVER_MAX_BYTES", "8")
    async with _client() as client:
        response = await client.put(
            f"/snapshots/{NAME}", content=b"far more than eight bytes", headers=AUTH
        )
    assert response.status_code == 413
    assert not list(receiver.glob("*"))


# ---------------------------------------------------------------------------
# Read back, list, delete
# ---------------------------------------------------------------------------


async def test_get_streams_the_bytes_back_for_the_verify(receiver):
    payload = b"the bytes the ship will hash" * 500
    (receiver / NAME).write_bytes(payload)
    async with _client() as client:
        response = await client.get(f"/snapshots/{NAME}", headers=AUTH)
    assert response.status_code == 200
    assert response.content == payload


async def test_get_answers_404_for_a_valid_name_that_is_absent(receiver):
    async with _client() as client:
        assert (await client.get(f"/snapshots/{NAME}", headers=AUTH)).status_code == 404


async def test_the_listing_excludes_part_files(receiver):
    (receiver / NAME).write_bytes(b"x")
    (receiver / f"{NAME}.part").write_bytes(b"y")
    (receiver / "darkmem-20260101-000000.sql.gz").write_bytes(b"z")
    async with _client() as client:
        body = (await client.get("/snapshots", headers=AUTH)).json()
    assert [item["name"] for item in body["snapshots"]] == [NAME]
    assert body["snapshots"][0]["size"] == 1


async def test_delete_removes_the_snapshot(receiver):
    (receiver / NAME).write_bytes(b"x")
    async with _client() as client:
        assert (
            await client.delete(f"/snapshots/{NAME}", headers=AUTH)
        ).status_code == 204
    assert not (receiver / NAME).exists()


# ---------------------------------------------------------------------------
# The process-separation claim
# ---------------------------------------------------------------------------


def test_the_receiver_imports_nothing_from_the_app():
    """The whole reason this is a separate process (review B1). A receiver
    that imported `app.database` would hold a connection pool inside the
    read-only instance, and "the worker's only write door writes files, not
    rows" would stop being a structural fact and become a promise."""
    import pathlib

    from tests._reachability_scan import import_closure

    backend = pathlib.Path(__file__).resolve().parent.parent
    closure = import_closure(backend, "app.worker_receiver")

    assert "app.worker_receiver" in closure
    forbidden = {
        module
        for module in closure
        if module in {"app.database", "app.main", "app.config"}
        or module.startswith("app.services.")
        or module.startswith("app.repositories.")
        or module.startswith("app.models.")
        or module.startswith("app.api.")
    }
    assert not forbidden, (
        f"the receiver can now reach {sorted(forbidden)} by import. It is a "
        f"separate process precisely so the worker's one write door holds no "
        f"database connection"
    )

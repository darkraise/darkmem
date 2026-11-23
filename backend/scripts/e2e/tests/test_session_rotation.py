"""Session renewal over a real socket: a refresh or a password change closes
the presented token's socket with 4001 "Session renewed", the client
reconnects with the new cookie, and the new socket receives broadcasts.

Run through ``python scripts/e2e/run_e2e.py -k session_rotation``.
"""
from __future__ import annotations

import asyncio

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

COOKIE = "darkmem_session"
RENEWED = (4001, "Session renewed")
PROJECT = "e2e-session-rotation"


def _ws_url(base_url: str) -> str:
    return base_url.replace("http://", "ws://", 1).replace("https://", "wss://", 1) + "/ws"


def _socket(base_url: str, token: str):
    return connect(_ws_url(base_url), additional_headers={"Cookie": f"{COOKIE}={token}"})


async def _close_of(ws) -> tuple[int, str]:
    with pytest.raises(ConnectionClosed) as closed:
        while True:
            await asyncio.wait_for(ws.recv(), 10)
    frame = closed.value.rcvd
    assert frame is not None, "the server sent no close frame"
    return frame.code, frame.reason


async def _rotate(api_client, base_url: str, call) -> str:
    """Open a socket on the current cookie, rotate through ``call``, and
    answer the new cookie once the old socket has closed as renewed."""
    presented = api_client.cookies.get(COOKIE)
    assert presented
    async with _socket(base_url, presented) as ws:
        answer = await call()
        assert answer.status_code == 200, answer.text
        assert await _close_of(ws) == RENEWED
    issued = api_client.cookies.get(COOKIE)
    assert issued and issued != presented
    return issued


async def _receives_a_broadcast(api_client, base_url: str, token: str) -> None:
    async with _socket(base_url, token) as ws:
        capture = await api_client.post(
            "/api/v1/memories",
            params={"wait_process": "true"},
            json={"content": "A renewed socket still hears the pipeline.", "project": PROJECT},
        )
        assert capture.status_code in (201, 202), capture.text
        message = await asyncio.wait_for(ws.recv(), 30)
        assert '"event"' in message


async def test_renewal_and_password_change_over_a_real_socket(
    api_client, e2e_base_url, e2e_admin_password,
):
    renewed = await _rotate(
        api_client, e2e_base_url, lambda: api_client.post("/api/v1/auth/refresh"),
    )
    await _receives_a_broadcast(api_client, e2e_base_url, renewed)

    interim = "e2e-rotated-password-1"
    answers = []

    async def _change():
        answer = await api_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": e2e_admin_password, "new_password": interim},
        )
        answers.append(answer)
        return answer

    try:
        changed = await _rotate(api_client, e2e_base_url, _change)
        await _receives_a_broadcast(api_client, e2e_base_url, changed)
    finally:
        # Later e2e tests log in with the stack's own password; it moved only
        # if the change answered 200.
        if answers and answers[0].status_code == 200:
            restored = await api_client.post(
                "/api/v1/auth/change-password",
                json={"current_password": interim, "new_password": e2e_admin_password},
            )
            assert restored.status_code == 200, restored.text

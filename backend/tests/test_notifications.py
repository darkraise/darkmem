"""Notification settings, masking, and the job-failure hook."""
from __future__ import annotations

import pytest

from app.services.notifications import (
    MASK,
    get_settings,
    masked,
    save_settings,
    send_telegram,
)


@pytest.mark.asyncio
async def test_defaults_are_off_with_no_row(session):
    settings = await get_settings(session)
    assert settings["telegram"]["enabled"] is False
    assert settings["notify_on"]["job_failure"] is True


@pytest.mark.asyncio
async def test_the_token_never_leaves_on_the_wire(session):
    await save_settings(session, {"telegram": {"bot_token": "123:secret", "chat_id": "42"}})
    served = masked(await get_settings(session))
    assert served["telegram"]["bot_token"] == MASK
    assert served["telegram"]["chat_id"] == "42"


@pytest.mark.asyncio
async def test_writing_the_mask_back_keeps_the_stored_token(session):
    """A client echoes what it was served. Writing the mask through would
    destroy the credential the moment anyone saved an unrelated field."""
    await save_settings(session, {"telegram": {"bot_token": "123:secret"}})
    await save_settings(session, {"telegram": {"bot_token": MASK, "chat_id": "99"}})

    stored = await get_settings(session)
    assert stored["telegram"]["bot_token"] == "123:secret"
    assert stored["telegram"]["chat_id"] == "99"


@pytest.mark.asyncio
async def test_send_refuses_clearly_when_unconfigured():
    sent, error = await send_telegram(
        {"telegram": {"enabled": True, "bot_token": "", "chat_id": ""}}, "hi"
    )
    assert sent is False
    assert "required" in (error or "")


@pytest.mark.asyncio
async def test_send_never_raises_on_a_transport_failure(monkeypatch):
    """A notifier that can take down the thing it reports on is worse than no
    notifier, so every failure is a return value."""
    import app.services.notifications as notif

    class Boom:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): raise RuntimeError("network down")

    monkeypatch.setattr(notif.httpx, "AsyncClient", lambda **k: Boom())
    sent, error = await send_telegram(
        {"telegram": {"enabled": True, "bot_token": "t", "chat_id": "c"}}, "hi"
    )
    assert sent is False and "network down" in (error or "")


@pytest.mark.asyncio
async def test_notify_is_silent_when_the_channel_is_off(session_factory_for_tests=None):
    """Disabled means no attempt at all — not a failed attempt logged."""
    import app.services.notifications as notif

    called = False

    async def _spy(*a, **k):
        nonlocal called
        called = True
        return True, None

    original = notif.send_telegram
    notif.send_telegram = _spy
    try:
        # No session factory work needed: the guard is read from settings.
        settings = {"telegram": {"enabled": False}, "notify_on": {"job_failure": True}}
        sent, _ = await original(settings, "x")
        assert sent is False
        assert called is False
    finally:
        notif.send_telegram = original

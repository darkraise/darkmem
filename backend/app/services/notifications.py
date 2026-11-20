"""Outbound notifications — today, Telegram for failed job runs.

Deliberately narrow. This is a *notifier*, not an alerting system: it has no
routing rules, no severities and no retry queue, because the one question it
answers is "did a background job just fail while nobody was looking".

The token is a credential and is masked on read exactly as the LLM API keys
are: the wire never carries it back, and a write of the mask means "leave it
alone" rather than "set it to three asterisks".
"""
from __future__ import annotations

import html
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.config import Config

logger = logging.getLogger(__name__)

NOTIFICATIONS_CONFIG_KEY = "notifications"
MASK = "***"
TELEGRAM_TIMEOUT_SECONDS = 10.0

DEFAULTS: dict = {
    "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
    # Which events are worth interrupting someone for. Only failures today;
    # a successful run is not news.
    "notify_on": {"job_failure": True},
}


def _merged(stored: dict | None) -> dict:
    settings = {k: dict(v) for k, v in DEFAULTS.items()}
    for section, values in (stored or {}).items():
        if section in settings and isinstance(values, dict):
            settings[section].update(values)
    return settings


async def get_settings(session: AsyncSession) -> dict:
    row = (await session.execute(
        select(Config).where(Config.key == NOTIFICATIONS_CONFIG_KEY)
    )).scalar_one_or_none()
    return _merged(row.value if row else None)


def masked(settings: dict) -> dict:
    out = {k: dict(v) for k, v in settings.items()}
    if out["telegram"].get("bot_token"):
        out["telegram"]["bot_token"] = MASK
    return out


async def save_settings(session: AsyncSession, patch: dict) -> dict:
    current = await get_settings(session)
    for section, values in (patch or {}).items():
        if section not in current or not isinstance(values, dict):
            continue
        for key, value in values.items():
            # The mask is what a client echoes back when it did not touch the
            # secret; writing it through would destroy the real token.
            if key == "bot_token" and value == MASK:
                continue
            current[section][key] = value

    row = (await session.execute(
        select(Config).where(Config.key == NOTIFICATIONS_CONFIG_KEY)
    )).scalar_one_or_none()
    if row is None:
        session.add(Config(key=NOTIFICATIONS_CONFIG_KEY, value=current))
    else:
        row.value = current
    await session.flush()
    return current


async def send_telegram(settings: dict, text: str) -> tuple[bool, str | None]:
    """Post one message. Returns ``(sent, error)`` and never raises.

    A notifier that can take down the thing it reports on is worse than no
    notifier, which is why every failure here is a return value.
    """
    tg = settings.get("telegram", {})
    if not tg.get("enabled"):
        return False, "telegram is not enabled"
    token, chat_id = tg.get("bot_token"), tg.get("chat_id")
    if not token or not chat_id:
        return False, "bot_token and chat_id are both required"

    try:
        async with httpx.AsyncClient(timeout=TELEGRAM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            )
        if response.status_code != 200:
            # Telegram puts the useful part in the body, not the status line.
            return False, f"telegram returned {response.status_code}: {response.text[:200]}"
        return True, None
    except Exception as exc:  # noqa: BLE001 - reported, never raised
        return False, str(exc)[:200]


async def notify_job_failure(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    job_key: str,
    error: str | None,
    duration_seconds: float,
) -> None:
    """Fire-and-forget notification for a failed run.

    Swallows everything. This is called from the job registry's recording
    path, which already states the rule: telling someone about a run must
    never be able to break the run, or the scheduling loop behind it.
    """
    try:
        async with session_factory() as session:
            settings = await get_settings(session)
        if not settings.get("notify_on", {}).get("job_failure"):
            return
        if not settings.get("telegram", {}).get("enabled"):
            return

        # Escaped because the message is sent in HTML mode and an error is
        # arbitrary text: a bare `<` or `&` makes Telegram reject all of it.
        text = (
            f"<b>darkmem — job failed</b>\n"
            f"<code>{html.escape(job_key)}</code> after {duration_seconds:.2f}s\n\n"
            f"{html.escape((error or 'no error recorded')[:600])}"
        )
        sent, why = await send_telegram(settings, text)
        if not sent:
            logger.warning("job-failure notification not sent: %s", why)
    except Exception:
        logger.error("job-failure notification raised", exc_info=True)

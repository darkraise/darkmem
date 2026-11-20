import asyncio
import inspect
import json
import logging
import time

from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.schemas.events import EVENT_SCHEMAS

logger = logging.getLogger(__name__)

# A frozen/backgrounded browser tab stops draining its socket; without a cap a
# producer awaiting the broadcast (the indexing / memory pipeline) would block
# on TCP backpressure behind the slowest consumer.
SEND_TIMEOUT_SECONDS = 5.0
AUTH_CHECK_INTERVAL_SECONDS = 1.0


class SessionRevocations:
    """The blocklisted token ids and the password-change epoch, in process.

    An open socket revalidates every second; reading these from memory keeps
    that check off the database. It is exact only because there is a single
    worker (invariant 13) whose own auth routes are the only writers, each
    updating this after its commit, and because the backup worker's restore
    cycle stops the app before it swaps the database, so a restored snapshot
    is always read by a fresh process.
    """

    def __init__(self) -> None:
        self._revoked: dict[str, float] = {}
        self._epoch: int | None = None
        self._loaded = False
        self._lock = asyncio.Lock()

    def reset(self) -> None:
        self._revoked.clear()
        self._epoch = None
        self._loaded = False

    async def load(self, session_factory) -> None:
        from sqlalchemy import text

        from app.api.auth import PASSWORD_CHANGED_AT_KEY

        async with self._lock:
            if self._loaded:
                return
            async with session_factory() as session:
                rows = (await session.execute(text(
                    "SELECT jti, expires_at FROM token_blocklist WHERE expires_at > now()"
                ))).all()
                stamp = (await session.execute(
                    text("SELECT value FROM config WHERE key = :k"),
                    {"k": PASSWORD_CHANGED_AT_KEY},
                )).scalar_one_or_none()
            for jti, expires_at in rows:
                self._revoked.setdefault(jti, expires_at.timestamp())
            ts = stamp.get("ts") if isinstance(stamp, dict) else None
            if isinstance(ts, int):
                self.set_epoch(ts)
            self._loaded = True

    def revoke(self, jti: str, expires_at: float) -> None:
        now = time.time()
        for stale in [k for k, exp in self._revoked.items() if exp <= now]:
            del self._revoked[stale]
        self._revoked[jti] = expires_at

    def set_epoch(self, ts: int) -> None:
        self._epoch = ts if self._epoch is None else max(self._epoch, ts)

    def check(self, token: str) -> None:
        """Raise the 401 ``validate_session_token`` would, from memory."""
        import jwt

        from app.api.auth import ALGORITHM, TokenPayload
        from app.config import settings

        try:
            payload = TokenPayload(**jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM]))
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
        if payload.jti in self._revoked:
            raise HTTPException(status_code=401, detail="Token has been revoked")
        if self._epoch is not None and payload.iat < self._epoch:
            raise HTTPException(status_code=401, detail="Token has been revoked")


session_revocations = SessionRevocations()


class EventManager:
    def __init__(self):
        self.connections: list[WebSocket] = []
        self._validators = {}
        # Serialize the per-connection send fan-out: broadcast() is awaited from
        # many concurrent coroutines (pipeline fan-out, indexing, jobs, reembed)
        # and Starlette's WebSocket.send is not safe for concurrent senders on
        # one socket — interleaved ASGI sends raise and kill the connection.
        self._send_lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, validator=None):
        await ws.accept()
        self.connections.append(ws)
        if validator is not None:
            self._validators[ws] = validator

    def disconnect(self, ws: WebSocket):
        self._validators.pop(ws, None)
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, event_type: str, data: dict):
        schema = EVENT_SCHEMAS.get(event_type)
        if schema:
            try:
                schema.model_validate(data)
            except ValidationError as e:
                # Send anyway (clients tolerate extra/missing fields), but make
                # it loud that the payload diverged from the declared schema —
                # this usually means a producer drifted from schemas/events.py.
                logger.warning(
                    "Broadcasting event '%s' whose payload failed schema "
                    "validation (sent regardless): %s",
                    event_type,
                    e,
                )
        message = json.dumps({"event": event_type, "data": data})
        # Validation happens before the send lock, so a slow check can never
        # hold every other producer's broadcast behind it.
        targets: list[WebSocket] = []
        refused: list[WebSocket] = []
        dead: list[WebSocket] = []
        for ws in list(self.connections):
            validator = self._validators.get(ws)
            try:
                if validator is not None:
                    verdict = validator()
                    if inspect.isawaitable(verdict):
                        await verdict
            except HTTPException:
                refused.append(ws)
                continue
            except Exception:
                dead.append(ws)
                continue
            targets.append(ws)
        async with self._send_lock:
            for ws in refused:
                try:
                    await ws.close(code=1008, reason="Session expired or revoked")
                except Exception:
                    pass
                dead.append(ws)
            for ws in targets:
                try:
                    await asyncio.wait_for(ws.send_text(message), timeout=SEND_TIMEOUT_SECONDS)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws)


event_manager = EventManager()


async def websocket_endpoint(ws: WebSocket):
    from app.api.auth import COOKIE_NAME, validate_session_token
    from app.database import async_session_factory

    token = ws.cookies.get(COOKIE_NAME)
    if not token:
        await ws.close(code=1008, reason="Unauthorized")
        return
    try:
        async with async_session_factory() as session:
            await validate_session_token(token, session)
        await session_revocations.load(async_session_factory)
    except HTTPException:
        await ws.close(code=1008, reason="Unauthorized")
        return

    def validate():
        session_revocations.check(token)

    await event_manager.connect(ws, validate)
    receive_task = asyncio.create_task(ws.receive_text())
    try:
        while True:
            done, _pending = await asyncio.wait(
                {receive_task}, timeout=AUTH_CHECK_INTERVAL_SECONDS,
            )
            validate()
            if done:
                receive_task.result()
                receive_task = asyncio.create_task(ws.receive_text())
    except HTTPException:
        await ws.close(code=1008, reason="Session expired or revoked")
    except WebSocketDisconnect:
        pass
    except Exception:
        # Any other receive error (e.g. the socket was already torn down by a
        # failed broadcast send) must still evict the connection so the list
        # self-heals instead of leaking a dead socket.
        logger.debug("WebSocket receive loop ended abnormally", exc_info=True)
    finally:
        event_manager.disconnect(ws)
        receive_task.cancel()
        await asyncio.gather(receive_task, return_exceptions=True)

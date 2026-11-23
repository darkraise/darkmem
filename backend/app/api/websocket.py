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
REVOCATION_RELOAD_SECONDS = 60.0
_now = time.monotonic
REVOKED_CLOSE = (1008, "Session expired or revoked")
RENEWED_CLOSE = (4001, "Session renewed")


async def _close_quietly(ws: WebSocket, code: int, reason: str) -> None:
    # Bounded like a send: a close can wait on a frozen tab's closing
    # handshake, and every caller holds the send lock, one of them on the
    # request path of a session rotation.
    try:
        await asyncio.wait_for(ws.close(code=code, reason=reason), timeout=SEND_TIMEOUT_SECONDS)
    except Exception:
        pass


class SessionRenewed(HTTPException):
    """The token was rotated by a refresh or a password change: its holder
    has, or is about to receive, a new cookie."""

    def __init__(self) -> None:
        super().__init__(status_code=401, detail="Session renewed")


def _close_for(refusal: HTTPException) -> tuple[int, str]:
    return RENEWED_CLOSE if isinstance(refusal, SessionRenewed) else REVOKED_CLOSE


class SessionRevocations:
    """The blocklisted token ids and the password-change epoch, in process.

    An open socket revalidates every second; reading these from memory keeps
    that check off the database. The app's auth routes update the copy after
    their commit, and it is re-read from the database once it is
    ``REVOCATION_RELOAD_SECONDS`` old, so a revocation written outside the app
    (a hand-run SQL statement, a restore) reaches open sockets within that
    window. One copy serves every socket only because there is a single
    worker (invariant 13).
    """

    def __init__(self) -> None:
        self._revoked: dict[str, float] = {}
        # Rotated token ids, marked when their sockets close and before the
        # rotation commits, so a socket opened on one in that window is told
        # it was renewed rather than accepted and later closed as revoked.
        self._renewed: dict[str, float] = {}
        self._epoch: int | None = None
        self._read_at: float | None = None
        self._read_failing = False
        self._lock = asyncio.Lock()

    def reset(self) -> None:
        self._revoked.clear()
        self._renewed.clear()
        self._epoch = None
        self._read_at = None
        self._read_failing = False

    async def load(self, session_factory) -> None:
        async with self._lock:
            if self._read_at is None:
                await self._read(session_factory)

    async def refresh_if_stale(self, session_factory) -> None:
        """Re-read the copy once it is stale; concurrent callers share one read.

        A failed read keeps the copy and is tried again once the window has
        passed, logging once until a read succeeds."""
        if not self._stale():
            return
        async with self._lock:
            if not self._stale():
                return
            try:
                await self._read(session_factory)
            except Exception:
                self._read_at = _now()
                if not self._read_failing:
                    self._read_failing = True
                    logger.warning(
                        "Reloading session revocations failed; keeping the in-process copy",
                        exc_info=True,
                    )
                return
            self._read_failing = False

    def _stale(self) -> bool:
        return self._read_at is None or _now() - self._read_at >= REVOCATION_RELOAD_SECONDS

    async def _read(self, session_factory) -> None:
        from sqlalchemy import text

        from app.api.auth import PASSWORD_CHANGED_AT_KEY

        async with session_factory() as session:
            rows = (await session.execute(text(
                "SELECT jti, expires_at FROM token_blocklist WHERE expires_at > now()"
            ))).all()
            stamp = (await session.execute(
                text("SELECT value FROM config WHERE key = :k"),
                {"k": PASSWORD_CHANGED_AT_KEY},
            )).scalar_one_or_none()
        # Merged, never replaced: a revocation recorded while this read was
        # in flight must survive it.
        for jti, expires_at in rows:
            self._revoked.setdefault(jti, expires_at.timestamp())
        ts = stamp.get("ts") if isinstance(stamp, dict) else None
        if isinstance(ts, int):
            self.set_epoch(ts)
        self._read_at = _now()

    def revoke(self, jti: str, expires_at: float) -> None:
        now = time.time()
        for stale in [k for k, exp in self._revoked.items() if exp <= now]:
            del self._revoked[stale]
        self._revoked[jti] = expires_at

    def mark_renewed(self, jti: str, expires_at: float) -> None:
        now = time.time()
        for stale in [k for k, exp in self._renewed.items() if exp <= now]:
            del self._renewed[stale]
        self._renewed[jti] = expires_at

    def forget_renewed(self, jti: str) -> None:
        """For a rotation whose commit failed: the presented token stays the
        session's token."""
        self._renewed.pop(jti, None)

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
        # After the revocations: once the rotation commits, its token is
        # revoked like any other; before that, and under the read-only
        # posture, which revokes nothing, it reads as renewed.
        if payload.jti in self._renewed:
            raise SessionRenewed()


session_revocations = SessionRevocations()


class EventManager:
    def __init__(self):
        self.connections: list[WebSocket] = []
        self._validators = {}
        # Open sockets by the session token id (jti) each was opened with.
        self._by_token: dict[str, set[WebSocket]] = {}
        self._token_of: dict[WebSocket, str] = {}
        # Serialize the per-connection send fan-out: broadcast() is awaited from
        # many concurrent coroutines (pipeline fan-out, indexing, jobs, reembed)
        # and Starlette's WebSocket.send is not safe for concurrent senders on
        # one socket — interleaved ASGI sends raise and kill the connection.
        self._send_lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, validator=None, token_id: str | None = None):
        await ws.accept()
        self.connections.append(ws)
        if validator is not None:
            self._validators[ws] = validator
        if token_id is not None:
            self._token_of[ws] = token_id
            self._by_token.setdefault(token_id, set()).add(ws)

    def disconnect(self, ws: WebSocket):
        self._validators.pop(ws, None)
        token_id = self._token_of.pop(ws, None)
        if token_id is not None:
            sockets = self._by_token.get(token_id)
            if sockets is not None:
                sockets.discard(ws)
                if not sockets:
                    del self._by_token[token_id]
        if ws in self.connections:
            self.connections.remove(ws)

    async def close(self, ws: WebSocket, code: int, reason: str) -> None:
        """Close and evict one socket, once: a socket a rotation or a broadcast
        already closed is not closed again."""
        async with self._send_lock:
            if ws not in self.connections:
                return
            self.disconnect(ws)
            await _close_quietly(ws, code, reason)

    async def close_token(self, token_id: str, code: int, reason: str) -> None:
        async with self._send_lock:
            for ws in list(self._by_token.get(token_id, ())):
                self.disconnect(ws)
                await _close_quietly(ws, code, reason)

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
        refused: list[tuple[WebSocket, tuple[int, str]]] = []
        dead: list[WebSocket] = []
        for ws in list(self.connections):
            validator = self._validators.get(ws)
            try:
                if validator is not None:
                    verdict = validator()
                    if inspect.isawaitable(verdict):
                        await verdict
            except HTTPException as refusal:
                refused.append((ws, _close_for(refusal)))
                continue
            except Exception:
                dead.append(ws)
                continue
            targets.append(ws)
        async with self._send_lock:
            for ws, (code, reason) in refused:
                if ws not in self.connections:
                    continue
                await _close_quietly(ws, code, reason)
                dead.append(ws)
            for ws in targets:
                # Closed while this broadcast waited for the lock.
                if ws not in self.connections:
                    continue
                try:
                    # Again under the lock: a revocation can land while this
                    # broadcast waits for another one's sends, and a cached
                    # check costs nothing.
                    validator = self._validators.get(ws)
                    if validator is not None and not inspect.iscoroutinefunction(validator):
                        try:
                            validator()
                        except HTTPException as refusal:
                            code, reason = _close_for(refusal)
                            await _close_quietly(ws, code, reason)
                            dead.append(ws)
                            continue
                    await asyncio.wait_for(ws.send_text(message), timeout=SEND_TIMEOUT_SECONDS)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws)


event_manager = EventManager()


async def close_renewed_sockets(token_id: str, expires_at: float) -> None:
    """Mark ``token_id`` renewed and close every socket opened with it as
    renewed, not revoked.

    Refresh and change-password call this before their blocklist write
    commits, so the client learns of the rotation from the close code and
    reconnects once it holds the new cookie; a socket opened on the old
    token from here on is closed the same way. A rotation whose commit fails
    calls ``session_revocations.forget_renewed``."""
    session_revocations.mark_renewed(token_id, expires_at)
    await event_manager.close_token(token_id, code=RENEWED_CLOSE[0], reason=RENEWED_CLOSE[1])


async def websocket_endpoint(ws: WebSocket):
    from app.api.auth import COOKIE_NAME, validate_session_token
    from app.database import async_session_factory

    token = ws.cookies.get(COOKIE_NAME)
    if not token:
        await ws.close(code=1008, reason="Unauthorized")
        return
    try:
        await session_revocations.load(async_session_factory)
        # First, so a token rotated but not yet committed is told it was
        # renewed rather than accepted by the query below.
        session_revocations.check(token)
        async with async_session_factory() as session:
            claims = await validate_session_token(token, session)
        # Again: a rotation may have landed while the query awaited.
        session_revocations.check(token)
    except SessionRenewed:
        # Accepted only to carry the close code; a refused handshake has none.
        await ws.accept()
        await ws.close(code=RENEWED_CLOSE[0], reason=RENEWED_CLOSE[1])
        return
    except HTTPException:
        await ws.close(code=1008, reason="Unauthorized")
        return

    def validate():
        session_revocations.check(token)

    manager = event_manager
    await manager.connect(ws, validate, token_id=claims.jti)
    receive_task = asyncio.create_task(ws.receive_text())
    try:
        while True:
            done, _pending = await asyncio.wait(
                {receive_task}, timeout=AUTH_CHECK_INTERVAL_SECONDS,
            )
            # Closed elsewhere (a rotation, a refused broadcast): nothing to
            # close again.
            if ws not in manager.connections:
                return
            await session_revocations.refresh_if_stale(async_session_factory)
            validate()
            if done:
                receive_task.result()
                receive_task = asyncio.create_task(ws.receive_text())
    except HTTPException as refusal:
        await manager.close(ws, *_close_for(refusal))
    except WebSocketDisconnect:
        pass
    except Exception:
        # Any other receive error (e.g. the socket was already torn down by a
        # failed broadcast send) must still evict the connection so the list
        # self-heals instead of leaking a dead socket.
        logger.debug("WebSocket receive loop ended abnormally", exc_info=True)
    finally:
        manager.disconnect(ws)
        receive_task.cancel()
        await asyncio.gather(receive_task, return_exceptions=True)

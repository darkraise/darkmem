import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import (
    PASSWORD_CHANGED_AT_KEY,
    TokenPayload,
    clear_auth_cookie,
    create_access_token,
    hash_password,
    require_auth,
    session_expires_at,
    set_auth_cookie,
    token_expires_at,
    verify_password,
    validate_password_bytes,
)
from app.api.websocket import close_renewed_sockets, session_revocations
from app.config import settings
from app.database import SessionDep, async_session_factory
from app.models.config import Config
from app.models.token_blocklist import TokenBlocklist
from app.services.events import record_event
from app.services.login_rate_limit import REFUSED_IN_FLIGHT, login_rate_limiter

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

ADMIN_PASSWORD_KEY = "admin_password_hash"


async def _record_audit(action: str, details: dict) -> None:
    """Persist an audit row in its own committed session.

    The request's session from ``get_session`` rolls back whenever the
    handler raises (e.g. a failed login raising 401), which silently discards
    audit rows merely flushed into it. Writing through a fresh session commits
    the audit trail independently of the request outcome.
    """
    async with async_session_factory() as audit_session:
        await record_event(
            audit_session, event_type=action, object_type="system", payload=details
        )
        await audit_session.commit()


class PasswordRequest(BaseModel):
    password: str = Field(max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_bytes(value)


def _client_ip(request: Request) -> str:
    # Behind a reverse proxy every request's client.host is the proxy, so all
    # logins would share one rate-limit bucket. When a trusted proxy fronts us,
    # use the address IT observed — NOT the leftmost X-Forwarded-For entry, which
    # the client supplies and can rotate per request to land every guess in a
    # fresh bucket and defeat the lockout. A trusted proxy sets X-Real-IP to its
    # own view of the peer, an overwrite the client cannot forge through it;
    # fall back to the rightmost XFF hop (the value that proxy appended,
    # not the spoofable leftmost) when X-Real-IP is absent.
    if settings.trust_proxy_headers:
        real_ip = request.headers.get("x-real-ip")
        if real_ip and real_ip.strip():
            return real_ip.strip()
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            parts = [p.strip() for p in fwd.split(",") if p.strip()]
            if parts:
                return parts[-1]
    return request.client.host if request.client else "unknown"


@router.post("/login")
async def auth_login(
    body: PasswordRequest,
    request: Request,
    session: AsyncSession = SessionDep,
):
    ip = _client_ip(request)
    limiter = login_rate_limiter

    # A single shared admin password on a reachable LAN needs an attempt-rate
    # boundary; bcrypt slows each guess but doesn't bound the rate. The slot is
    # reserved before the first await, so concurrent guesses count against the
    # threshold while they are still in flight.
    refusal = limiter.acquire(ip)
    if refusal is not None:
        retry_after = refusal.retry_after
        if refusal.gate == REFUSED_IN_FLIGHT:
            detail = f"Too many login attempts in progress; retry in {retry_after}s"
        else:
            detail = f"Too many failed login attempts; retry in {retry_after}s"
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)},
        )
    try:
        result = await session.execute(select(Config).where(Config.key == ADMIN_PASSWORD_KEY))
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin password not set")

        if not await asyncio.to_thread(verify_password, body.password, config.value["hash"]):
            limiter.record_failure(ip)
            await _record_audit("auth_login_failed", {"ip": ip})
            # The acquire gate above already proved this IP was not locked
            # when the request started, so a non-None retry_after here means
            # this exact failure is the one that just crossed the threshold —
            # the transition, not merely the locked state, is what gets audited.
            retry_after_now = limiter.retry_after(ip)
            if retry_after_now is not None:
                await _record_audit(
                    "auth_lockout",
                    {"ip": ip, "retry_after_seconds": retry_after_now},
                )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

        limiter.record_success(ip)
    finally:
        limiter.release(ip)
    await record_event(
        session, event_type="auth_login_success", object_type="system", payload={"ip": ip}
    )

    token = create_access_token({"sub": "admin"})
    response = JSONResponse(content={"ok": True})
    return set_auth_cookie(response, token)


@router.post("/logout")
async def auth_logout(
    payload: TokenPayload = Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    # C2 (increment 7): the cookie is cleared either way. Under the worker's
    # read-only posture the blocklist insert would be refused by the viewer
    # role and 500 the handler, leaving the operator logged in with no error
    # they could act on. Stated cost, reported on GET /auth/security-posture:
    # on the worker only, the cleared token stays valid until its own exp.
    if not settings.read_only:
        expires_at = datetime.fromtimestamp(payload.exp, tz=timezone.utc)
        session.add(TokenBlocklist(jti=payload.jti, expires_at=expires_at))
        await record_event(
            session, event_type="auth_logout", object_type="system",
            payload={"sub": payload.sub},
        )
        await session.commit()
        session_revocations.revoke(payload.jti, float(payload.exp))

    response = JSONResponse(content={"ok": True}, status_code=status.HTTP_200_OK)
    return clear_auth_cookie(response)


@router.post("/change-password")
async def auth_change_password(
    body: ChangePasswordRequest,
    request: Request,
    payload: TokenPayload = Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    # C3 (increment 7): refused before the session is touched. Changing a
    # snapshot's password is meaningless -- the next restore overwrites it --
    # and a handler that failed halfway through the config UPDATE would leave
    # the operator guessing which half landed.
    if settings.read_only:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "read-only instance: the next restore would overwrite this "
                "password anyway"
            ),
        )
    result = await session.execute(select(Config).where(Config.key == ADMIN_PASSWORD_KEY))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin password not set")

    if not await asyncio.to_thread(verify_password, body.current_password, config.value["hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

    config.value = {"hash": await asyncio.to_thread(hash_password, body.new_password)}

    # Stamp the change time so every token issued before now is rejected by
    # require_auth. Without this, outstanding sessions survive a password
    # change and keep full admin access until they expire on their own.
    changed_at = int(datetime.now(timezone.utc).timestamp())
    stamp = (await session.execute(
        select(Config).where(Config.key == PASSWORD_CHANGED_AT_KEY)
    )).scalar_one_or_none()
    if stamp:
        stamp.value = {"ts": changed_at}
    else:
        session.add(Config(key=PASSWORD_CHANGED_AT_KEY, value={"ts": changed_at}))

    await record_event(
        session, event_type="auth_password_change", object_type="system",
        payload={"ip": _client_ip(request)},
    )

    # Rotate: revoke the presented token so it can't be reused after the
    # reissue (belt-and-suspenders with the changed_at epoch).
    session.add(TokenBlocklist(
        jti=payload.jti,
        expires_at=datetime.fromtimestamp(payload.exp, tz=timezone.utc),
    ))
    # Before the commit, so the caller's own socket is told it was renewed
    # rather than revoked; other sessions' sockets close on the epoch.
    try:
        await close_renewed_sockets(payload.jti, float(payload.exp))
        await session.commit()
    except BaseException:
        session_revocations.forget_renewed(payload.jti)
        raise
    session_revocations.set_epoch(changed_at)
    session_revocations.revoke(payload.jti, float(payload.exp))

    response = JSONResponse(content={"ok": True})
    # The caller's own current token predates changed_at and would be rejected
    # on the next request; reissue so they stay logged in after rotating.
    token = create_access_token({"sub": payload.sub})
    return set_auth_cookie(response, token)


@router.post("/refresh")
async def auth_refresh(
    payload: TokenPayload = Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    # Rotating refresh: blocklist the presented jti before issuing a new token
    # so a captured pre-refresh token can't keep working until its 24h exp.
    # Refresh has no changed_at epoch backstop, so this is the only revocation.
    #
    # C1 (increment 7): skipped under the worker's read-only posture, because
    # the SPA viewer this instance exists to serve would otherwise die
    # silently at every access-token expiry. Losing the only revocation is a
    # real cost and is reported as `read_only_token_rotation_disabled` on
    # GET /auth/security-posture rather than left to a runbook.
    #
    # The presented token's sockets close as renewed before the commit, so a
    # client never reads a rotation as a revocation; it reconnects once it
    # holds the new cookie. The read-only posture closes them too.
    try:
        await close_renewed_sockets(payload.jti, float(payload.exp))
        if not settings.read_only:
            session.add(TokenBlocklist(
                jti=payload.jti,
                expires_at=datetime.fromtimestamp(payload.exp, tz=timezone.utc),
            ))
            await session.commit()
    except BaseException:
        session_revocations.forget_renewed(payload.jti)
        raise
    if not settings.read_only:
        session_revocations.revoke(payload.jti, float(payload.exp))

    token = create_access_token({"sub": payload.sub})
    response = JSONResponse(content={"ok": True, "expires_at": token_expires_at(token)})
    return set_auth_cookie(response, token)


@router.get("/me")
async def auth_me(payload: TokenPayload = Depends(require_auth)):
    return {
        "authenticated": True,
        "sub": payload.sub,
        "expires_at": session_expires_at(payload.exp),
    }


class SecurityPostureResponse(BaseModel):
    trust_proxy_headers: bool
    cookie_secure: bool
    cookie_secure_explicit: bool
    # Without this an operator cannot tell an enforced Secure flag from one
    # that overrode their own explicit false — the two render identically.
    cookie_secure_clamped: bool
    environment: str
    mcp_allowed_hosts: list[str]
    rate_limit_max_failures: int
    rate_limit_window_seconds: float
    rate_limit_lockout_seconds: float
    # The backup worker's posture. `read_only` is app-side ergonomics, never
    # the guarantee -- the SELECT-only database role is what enforces. Reported
    # here so an operator can tell which instance they are looking at.
    read_only: bool
    # The flag's stated cost, reported for the same reason `cookie_secure_clamped`
    # is: under it a refresh reissues without blocklisting the token it
    # replaces, so a captured pre-refresh token stays valid until its own exp.
    read_only_token_rotation_disabled: bool


def _parse_mcp_allowed_hosts(raw: str) -> list[str]:
    return [h.strip() for h in raw.split(",") if h.strip()]


@router.get("/security-posture", response_model=SecurityPostureResponse)
async def auth_security_posture(
    _payload: TokenPayload = Depends(require_auth),
) -> SecurityPostureResponse:
    """The live security posture, read off ``settings`` and the shared
    ``login_rate_limiter`` at call time — never a hardcoded assumption.

    T1.62 is about to flip ``trust_proxy_headers``'s default and move the
    limiter onto the transport peer; this endpoint is how an operator sees
    which strategy is actually in effect once that lands, so every field
    here is a live read, not a default echoed back.

    Enumerates fields rather than serialising ``settings`` wholesale: no
    credential (``jwt_secret``, ``db_password``, any provider ``api_key``)
    can appear on this response, by construction rather than by filtering
    one out after the fact.
    """
    return SecurityPostureResponse(
        trust_proxy_headers=settings.trust_proxy_headers,
        cookie_secure=settings.session_cookie_secure,
        cookie_secure_explicit=settings.cookie_secure is not None,
        cookie_secure_clamped=settings.session_cookie_secure_clamped,
        environment=settings.environment,
        mcp_allowed_hosts=_parse_mcp_allowed_hosts(settings.mcp_allowed_hosts),
        rate_limit_max_failures=login_rate_limiter.max_failures,
        rate_limit_window_seconds=login_rate_limiter.window_seconds,
        rate_limit_lockout_seconds=login_rate_limiter.lockout_seconds,
        read_only=settings.read_only,
        read_only_token_rotation_disabled=settings.read_only,
    )


@router.get("/audit")
async def auth_audit(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: str | None = Query(None),
    _payload: TokenPayload = Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    """Admin read surface for the security audit trail (auth_*/setup_* rows).

    The audit rows are committed independently of the request so failed logins
    survive a 401 rollback; this endpoint makes them visible to an operator.
    """
    # Reads the same security trail from ``events``, which replaced
    # ``audit_log`` in the baseline (doc 04 §8.1). The response shape is an
    # operator contract and is preserved verbatim: event_type surfaces as
    # ``action`` and payload as ``details``. T1.09 owns moving readers onto
    # the general /events surface.
    where = "(event_type LIKE 'auth\\_%' OR event_type LIKE 'setup\\_%')"
    params: dict[str, object] = {}
    if action:
        where += " AND event_type = :action"
        params["action"] = action

    total = (await session.execute(
        sa_text(f"SELECT count(*) FROM events WHERE {where}"), params
    )).scalar() or 0

    rows = (await session.execute(
        sa_text(
            f"SELECT id, event_type, payload, created_at FROM events WHERE {where} "
            "ORDER BY created_at DESC, id DESC OFFSET :offset LIMIT :limit"
        ),
        {**params, "offset": offset, "limit": limit},
    )).all()

    return {
        "items": [
            {
                "id": r.id,
                "action": r.event_type,
                "details": r.payload or {},
                "timestamp": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import (
    TokenPayload,
    clear_auth_cookie,
    create_access_token,
    hash_password,
    require_auth,
    set_auth_cookie,
    verify_password,
)
from app.config import settings
from app.database import async_session_factory, get_session
from app.models.audit import AuditLog
from app.models.config import Config
from app.models.token_blocklist import TokenBlocklist
from app.services.login_rate_limit import login_rate_limiter

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

ADMIN_PASSWORD_KEY = "admin_password_hash"
PASSWORD_CHANGED_AT_KEY = "admin_password_changed_at"


async def _record_audit(action: str, details: dict) -> None:
    """Persist an audit row in its own committed session.

    The request-scoped session from ``get_session`` rolls back whenever the
    handler raises (e.g. a failed login raising 401), which silently discards
    audit rows merely flushed into it. Writing through a fresh session commits
    the audit trail independently of the request outcome.
    """
    async with async_session_factory() as audit_session:
        audit_session.add(AuditLog(action=action, details=details))
        await audit_session.commit()


class PasswordRequest(BaseModel):
    password: str = Field(max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


def _client_ip(request: Request) -> str:
    # Behind a reverse proxy every request's client.host is the proxy, so all
    # logins would share one rate-limit bucket. When a trusted proxy fronts us,
    # use the address IT observed — NOT the leftmost X-Forwarded-For entry, which
    # the client supplies and can rotate per request to land every guess in a
    # fresh bucket and defeat the lockout. The bundled nginx sets X-Real-IP to
    # its own $remote_addr (an overwrite the client can't forge through nginx);
    # fall back to the rightmost XFF hop (the value the trusted proxy appended,
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
    session: AsyncSession = Depends(get_session),
):
    ip = _client_ip(request)

    # A single shared admin password on a reachable LAN needs an attempt-rate
    # boundary; bcrypt slows each guess but doesn't bound the rate. Reject early
    # when the IP is locked out, before touching the DB or hashing.
    retry_after = login_rate_limiter.retry_after(ip)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts; retry in {retry_after}s",
            headers={"Retry-After": str(retry_after)},
        )

    result = await session.execute(select(Config).where(Config.key == ADMIN_PASSWORD_KEY))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin password not set")

    if not verify_password(body.password, config.value["hash"]):
        login_rate_limiter.record_failure(ip)
        await _record_audit("auth_login_failed", {"ip": ip})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    login_rate_limiter.record_success(ip)
    session.add(AuditLog(action="auth_login_success", details={"ip": ip}))
    await session.flush()

    token = create_access_token({"sub": "admin"})
    response = JSONResponse(content={"ok": True})
    return set_auth_cookie(response, token)


@router.post("/logout")
async def auth_logout(
    payload: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    expires_at = datetime.fromtimestamp(payload.exp, tz=timezone.utc)
    session.add(TokenBlocklist(jti=payload.jti, expires_at=expires_at))
    session.add(AuditLog(action="auth_logout", details={"sub": payload.sub}))
    await session.commit()

    response = JSONResponse(content={"ok": True}, status_code=status.HTTP_200_OK)
    return clear_auth_cookie(response)


@router.post("/change-password")
async def auth_change_password(
    body: ChangePasswordRequest,
    request: Request,
    payload: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Config).where(Config.key == ADMIN_PASSWORD_KEY))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin password not set")

    if not verify_password(body.current_password, config.value["hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

    config.value = {"hash": hash_password(body.new_password)}

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

    session.add(AuditLog(action="auth_password_change", details={"ip": _client_ip(request)}))

    # Rotate: revoke the presented token so it can't be reused after the
    # reissue (belt-and-suspenders with the changed_at epoch).
    session.add(TokenBlocklist(
        jti=payload.jti,
        expires_at=datetime.fromtimestamp(payload.exp, tz=timezone.utc),
    ))

    response = JSONResponse(content={"ok": True})
    # The caller's own current token predates changed_at and would be rejected
    # on the next request; reissue so they stay logged in after rotating.
    token = create_access_token({"sub": payload.sub})
    return set_auth_cookie(response, token)


@router.post("/refresh")
async def auth_refresh(
    payload: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    # Rotating refresh: blocklist the presented jti before issuing a new token
    # so a captured pre-refresh token can't keep working until its 24h exp.
    # Refresh has no changed_at epoch backstop, so this is the only revocation.
    session.add(TokenBlocklist(
        jti=payload.jti,
        expires_at=datetime.fromtimestamp(payload.exp, tz=timezone.utc),
    ))
    await session.commit()

    token = create_access_token({"sub": payload.sub})
    response = JSONResponse(content={"ok": True})
    return set_auth_cookie(response, token)


@router.get("/me")
async def auth_me(payload: TokenPayload = Depends(require_auth)):
    return {"authenticated": True, "sub": payload.sub}


@router.get("/audit")
async def auth_audit(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: str | None = Query(None),
    _payload: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Admin read surface for the security audit trail (auth_*/setup_* rows).

    The audit rows are committed independently of the request so failed logins
    survive a 401 rollback; this endpoint makes them visible to an operator.
    """
    base = select(AuditLog).where(
        AuditLog.action.like("auth_%") | AuditLog.action.like("setup_%")
    )
    if action:
        base = base.where(AuditLog.action == action)

    total = (await session.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0

    rows = (await session.execute(
        base.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
    )).scalars().all()

    return {
        "items": [
            {
                "id": r.id,
                "action": r.action,
                "details": r.details or {},
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }

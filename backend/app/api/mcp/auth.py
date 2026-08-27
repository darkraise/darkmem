"""Bearer verification for the MCP door (doc 18 §5).

Reuses `app.services.api_keys.authenticate` rather than reading the table
directly, so REST and MCP can never drift into two credential readers with
two different ideas of what a valid key is.

Deliberately does **not** call `mark_key_used` here. REST's `require_scope`
(`app/api/auth.py`) marks a key used only after its scope check passes,
because a call that authenticates and then fails the scope gate did not use
the key for anything. Marking at the transport, before Task 7's per-tool
scope check runs, would make `last_used_at` mean something different on MCP
than it does on REST for the same key. Task 7 owns that call.
"""
import logging
import uuid

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier

from app.database import async_session_factory
from app.services.api_keys import authenticate, parse_credential

logger = logging.getLogger(__name__)


class ApiKeyTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        # `authenticate` returns a KeyPrincipal, which carries the row UUID but
        # not the public key_id, so the id is parsed from the credential the
        # caller presented. Both are needed and they are not interchangeable:
        # the row UUID is what `events.api_key_id` stores, the public key_id
        # is what `client_id` must carry.
        parsed = parse_credential(token)
        if parsed is None:
            return None
        key_id, _secret = parsed

        # A fresh session per call, matching the rest of the MCP door
        # (`app/api/mcp/server.py` does the same): token verification runs
        # ahead of any request-scoped dependency chain, so there is no
        # `get_session`-style session to borrow, and a short-lived session per
        # verification avoids holding a pooled connection for the lifetime of
        # a tool call it has nothing to do with.
        #
        # Every failure mode here — including the database being unreachable —
        # must resolve to a refusal, never a raise: a raised exception at this
        # layer is not a 401, and an unreachable database must never be read as
        # "let the caller through". Fail closed.
        try:
            async with async_session_factory() as session:
                principal = await authenticate(session, token)
        except Exception:
            logger.error("mcp auth: verification failed", exc_info=True)
            return None

        if principal is None:
            return None

        return AccessToken(
            token=token,
            client_id=key_id,
            scopes=sorted(principal.scopes),
            # `authenticate` already refuses expired and revoked keys, so a
            # None here means "no further expiry for the SDK to enforce",
            # never "never expires".
            expires_at=None,
            subject=principal.name,
            # `client_id` above carries the public key_id; `events.api_key_id`
            # wants the row UUID, which `authenticate` resolves but `client_id`
            # has no room for. Riding it in `claims` lets a later caller write
            # `events.api_key_id` from the token it already holds, with no
            # second SELECT per request.
            claims={"api_key_id": str(principal.api_key_id)},
        )


def current_api_key_id() -> uuid.UUID | None:
    """The row id of the key that authenticated this call, or None.

    `AccessToken.client_id` carries only the public `key_id`; the row id —
    what `events.api_key_id` actually stores — already rides in
    `claims["api_key_id"]`, minted once by `verify_token` above. Reading it
    from there costs no database access; a second SELECT keyed on `client_id`
    would just re-derive what the verifier already resolved this call.
    """
    token = get_access_token()
    if token is None:
        return None
    raw = (token.claims or {}).get("api_key_id")
    if raw is None:
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        logger.warning("mcp auth: token carries an unusable api_key_id %r", raw)
        return None


def current_key_name() -> str | None:
    """The name of the key that authenticated this call, or None.

    `verify_token` above sets `subject=principal.name`, so this is also a
    free read off the already-verified token — no lookup needed.
    """
    token = get_access_token()
    return token.subject if token is not None else None

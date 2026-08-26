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
            logger.warning("mcp auth: verification failed", exc_info=True)
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
        )

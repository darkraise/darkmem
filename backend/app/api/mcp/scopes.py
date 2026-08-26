"""Which scope each MCP tool requires, and the gate that enforces it (doc 18 §5).

Scope is decided from the tool actually invoked - the request body - never from
the ``Mcp-Name`` header. The protocol makes the body the source of truth and
requires servers to reject header/body mismatches, so authorizing on the header
would be exploitable by a non-conforming client.

**The gate is one dispatch-level middleware, not a call in each tool body.**
The alternative the plan described - one such call as the first
statement of all 33 tools - is 33 chances to omit one, and an omission is
silent: the tool ships reachable by any valid key. Nothing in the type system,
the decorator or the test suite can see a missing first statement, so the only
guard available would be a test that re-derives the roster and hopes. Here the
check runs in :class:`ToolScopeMiddleware`, which the SDK wraps around *every*
inbound message before params validation, so a tool cannot be declared outside
it. What a new tool can still do is fail to appear in ``TOOL_SCOPES`` below,
and that direction is closed the other way round: an unlisted name is
**refused**, not defaulted. A tool nobody classified is unreachable rather than
readable, and ``tests/test_mcp_auth.py`` fails the build on the drift.

That is also why ``TOOL_SCOPES`` names all 33 rather than deriving "everything
not in ``CAPTURE_TOOLS`` is a reader". A derived partition is total by
construction, which sounds like the stronger property and is the weaker one: it
makes a new *writer* that nobody remembered to list resolve to ``read`` and
ship, with every test still green.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.context import CallNext, HandlerResult, ServerRequestContext
from mcp.shared.exceptions import MCPError

from app.services.api_key_scopes import API_KEY_SCOPES, FORBIDDEN_SCOPES
from app.services.api_keys import mark_key_used

logger = logging.getLogger(__name__)


CAPTURE_TOOLS: frozenset[str] = frozenset({
    "memory_add",
    "memory_batch_add",
    "memory_update",
    "memory_delete",
    "document_put",
    "document_delete",
    "checkpoint_save",
    "research_run",
})

READ_TOOLS: frozenset[str] = frozenset({
    "article_get",
    "checkpoint_latest",
    "code_blast_radius",
    "code_changes",
    "code_communities",
    "code_context",
    "code_dependencies",
    "code_file_symbols",
    "code_processes",
    "code_rename",
    "code_search",
    "code_symbol",
    "document_get",
    "document_outline",
    "document_search",
    "fact_get",
    "knowledge_search",
    "list_repos",
    "memory_find_duplicates",
    "memory_get",
    "memory_overview",
    "memory_reason",
    "memory_search",
    "memory_stats",
    "memory_tags",
})

_overlap = CAPTURE_TOOLS & READ_TOOLS
if _overlap:
    raise RuntimeError(
        f"{sorted(_overlap)} is declared both a writer and a reader; a tool has "
        "exactly one scope"
    )

TOOL_SCOPES: dict[str, str] = {
    **{name: "capture" for name in CAPTURE_TOOLS},
    **{name: "read" for name in READ_TOOLS},
}

# The JSON-RPC code a scope refusal carries. Distinct from every code the SDK
# defines and from the transport's own 401, so a caller can tell "your key is
# not good here" from "you presented no key at all" without parsing prose.
SCOPE_DENIED = -32003


class ScopeDenied(PermissionError):
    """The presented key authenticated but lacks the scope this tool needs."""


def require_tool_scope(scope: str) -> AccessToken:
    """Refuse unless the authenticated key carries ``scope``. Returns the token.

    Reads the principal from the auth context, which is populated from the
    verified bearer - body-side, so the ``Mcp-Name`` header is never consulted
    for an authorization decision.

    The scope literal is validated against the closed set on every call rather
    than only at registration: this is the one place a ``ratify`` string could
    reach a membership test, and ``FORBIDDEN_SCOPES`` must win there even if a
    caller passes it directly.
    """
    if scope in FORBIDDEN_SCOPES or scope not in API_KEY_SCOPES:
        raise ScopeDenied(
            f"{scope!r} is not an API-key scope; the closed set is "
            f"{', '.join(API_KEY_SCOPES)}"
        )
    token = get_access_token()
    if token is None:
        raise ScopeDenied("this door requires an API key")
    if scope not in token.scopes:
        raise ScopeDenied(f"key lacks the {scope!r} scope")
    return token


def require_scope_for_tool(tool_name: str) -> AccessToken:
    """Refuse unless the authenticated key carries ``tool_name``'s scope.

    An unlisted tool is refused rather than defaulted, so shipping a tool
    nobody classified costs its availability instead of its authorization.

    Deliberately not named ``require_scope``: REST's ``app.api.auth`` already
    binds that name to a function taking a *scope*, and this one takes a *tool*.
    Two functions with one name over two domains is a substitution nobody would
    catch in review, and ``tests/test_api_keys.py``'s tree-wide scan reads the
    binding rather than the module, so it would have to see through this call
    to keep proving no route names a scope outside the closed set.
    """
    scope = TOOL_SCOPES.get(tool_name)
    if scope is None:
        raise ScopeDenied(
            f"{tool_name!r} declares no scope; every tool must be classified in "
            "TOOL_SCOPES before it is reachable"
        )
    return require_tool_scope(scope)


def _tool_name(params: Any) -> str | None:
    if not isinstance(params, Mapping):
        return None
    name = params.get("name")
    return name if isinstance(name, str) else None


class ToolScopeMiddleware:
    """Enforce the per-tool scope on every ``tools/call``, at dispatch.

    Registered on ``Server.middleware``, so it wraps every inbound message the
    SDK routes - there is no path to a tool body that does not pass through
    here. It reads the tool name off ``ctx.params``, which is the request body
    before validation; the transport has already refused a body whose name
    disagrees with ``Mcp-Name``.

    ``mark_key_used`` fires here, after the scope check and only on a pass,
    matching REST's ``require_scope``: a call that authenticates and then fails
    the scope gate did not use the key for anything.
    """

    async def __call__(
        self,
        ctx: ServerRequestContext[Any, Any],
        call_next: CallNext,
    ) -> HandlerResult:
        if ctx.method != "tools/call":
            return await call_next(ctx)

        name = _tool_name(ctx.params)
        if name is None:
            # A malformed tools/call carries no name to authorize. Hand it on
            # so the SDK's own params validation names the real problem rather
            # than reporting it as an authorization failure.
            return await call_next(ctx)

        try:
            token = require_scope_for_tool(name)
        except ScopeDenied as exc:
            raise MCPError(code=SCOPE_DENIED, message=str(exc), data=name) from None

        await _mark_used(token)
        return await call_next(ctx)


async def _mark_used(token: AccessToken) -> None:
    raw = (token.claims or {}).get("api_key_id")
    if not raw:
        return
    try:
        api_key_id = UUID(str(raw))
    except ValueError:
        logger.warning("mcp auth: token carries an unusable api_key_id %r", raw)
        return
    await mark_key_used(api_key_id)

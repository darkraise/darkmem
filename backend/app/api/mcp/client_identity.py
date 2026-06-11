"""Resolve which client/tool issued an MCP call.

The MCP endpoint is stateless (``stateless_http=True``), so the handshake's
``clientInfo`` is never available during tool calls. Identity is resolved per
request from explicit tool arguments and HTTP headers instead; see
docs/superpowers/specs/2026-06-11-memory-source-attribution-design.md.
"""
import logging
import re

logger = logging.getLogger(__name__)

CLIENT_HEADER = "x-darkmem-client"
FALLBACK_SOURCE = "mcp"

_SOURCE_MAX_LEN = 100  # memories.source is String(100)
_AGENT_MAX_LEN = 255  # memories.source_agent is String(255)

_SLUG_RE = re.compile(r"[^a-z0-9._-]+")

# Runtime/library User-Agent product tokens that say nothing about which
# tool is calling.
GENERIC_UA_TOKENS = frozenset({
    "node", "bun", "deno", "mozilla", "python-httpx", "python-requests",
    "python-urllib", "python-aiohttp", "aiohttp", "curl", "undici", "axios",
    "go-http-client", "okhttp", "java", "libwww-perl", "wget",
})

# Distinctive User-Agent product tokens -> canonical source names.
KNOWN_UA_SOURCES = {
    "claude-code": "claude-code",
}


def _sanitize(value: str) -> str:
    return _SLUG_RE.sub("", value.strip().lower())[:_SOURCE_MAX_LEN]


def _request_from_ctx(ctx):
    # ``ctx.request_context`` raises ValueError outside a request (e.g.
    # in-process ``call_tool``); over stdio it exists with request=None.
    # LookupError covers an unset request_ctx contextvar on other paths.
    if ctx is None:
        return None
    try:
        return ctx.request_context.request
    except (ValueError, LookupError, AttributeError):
        return None


def _ua_product_source(user_agent: str) -> str | None:
    token = user_agent.split(None, 1)[0] if user_agent.strip() else ""
    product, sep, _version = token.partition("/")
    if not sep:
        return None
    slug = _sanitize(product)
    if not slug or slug in GENERIC_UA_TOKENS:
        return None
    return KNOWN_UA_SOURCES.get(slug, slug)


def resolve_client_source(explicit_source, ctx) -> str:
    """Resolve the source label: explicit arg > header > User-Agent > "mcp".

    The literal "mcp" counts as unspecified so agents copying the old default
    cannot mask detection. Never raises: attribution must not fail a write.
    """
    try:
        if isinstance(explicit_source, str):
            # Lowercased before the sentinel check ("MCP" must not dodge it)
            # and not slug-sanitized — a deliberate value wins as-is, but
            # lowercase keeps UI color/filter lookups consistent with the
            # sanitized tier-2/3 output.
            explicit = explicit_source.strip().lower()
            if explicit and explicit != FALLBACK_SOURCE:
                return explicit[:_SOURCE_MAX_LEN]
        request = _request_from_ctx(ctx)
        if request is not None:
            header_source = _sanitize(request.headers.get(CLIENT_HEADER, ""))
            if header_source:
                return header_source
            ua_source = _ua_product_source(request.headers.get("user-agent", ""))
            if ua_source:
                return ua_source
    except Exception:
        logger.debug("client source resolution failed", exc_info=True)
    return FALLBACK_SOURCE


def resolve_source_agent(explicit_agent, ctx) -> str | None:
    """Explicit value (truncated) or the raw User-Agent; None without either."""
    try:
        if isinstance(explicit_agent, str) and explicit_agent.strip():
            return explicit_agent.strip()[:_AGENT_MAX_LEN]
        request = _request_from_ctx(ctx)
        if request is None:
            return None
        user_agent = request.headers.get("user-agent", "").strip()
        return user_agent[:_AGENT_MAX_LEN] or None
    except Exception:
        return None

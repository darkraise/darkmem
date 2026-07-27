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
ORIGIN_HEADER = "x-darkmem-origin"
FALLBACK_SOURCE = "mcp"

# The prefix that marks a merged, identity-unknown origin. Everything that
# carries it is ONE origin per (source, project) by construction.
UNKNOWN_ORIGIN_PREFIX = "unknown"

_SOURCE_MAX_LEN = 100  # memories.source is String(100)
_AGENT_MAX_LEN = 255  # memories.source_agent is String(255)
_ORIGIN_MAX_LEN = 255  # memories.origin_key is Text; bounded for sanity

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


def _sanitize_origin(value: str) -> str:
    """Keep a declared origin id recognisable but bounded. Deliberately does
    NOT lowercase-slug it away — two distinct client ids must stay distinct."""
    return "".join(ch for ch in value if ch.isprintable() and ch != ":")[:128]


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


def resolve_origin_key(explicit_origin, ctx, *, source: str, project: str) -> str:
    """The corroboration-independence key, stamped at capture (doc 05 §2.1).

    Declared identity wins: `source:origin_id`, from an explicit argument or the
    `X-Darkmem-Origin` header the client sets from a uuid minted **at process
    boot** — a per-boot agent-run id, never a per-request one. Otherwise the
    merge-to-one fallback `unknown:source:project`.

    **The fallback is deliberately coarse and must stay that way.** Every
    corroboration count downstream is `COUNT(DISTINCT origin_key)`, so a
    per-request random here would mint N counterfeit origins from one agent and
    let it corroborate itself — every fact promoted on that count, and every
    article citing it, would inherit the lie. Undercounting only delays a
    promotion; overcounting manufactures one. So when identity is genuinely
    unknown, an untagged flood from one tool collapses to a single origin.

    Never raises: attribution must not fail a write.
    """
    try:
        declared = ""
        if isinstance(explicit_origin, str):
            declared = explicit_origin.strip()
        if not declared:
            request = _request_from_ctx(ctx)
            if request is not None:
                declared = request.headers.get(ORIGIN_HEADER, "").strip()
        if declared:
            return f"{source}:{_sanitize_origin(declared)}"[:_ORIGIN_MAX_LEN]
    except Exception:
        logger.warning("origin_key: declared-identity resolution failed", exc_info=True)
    return f"{UNKNOWN_ORIGIN_PREFIX}:{source}:{project}"[:_ORIGIN_MAX_LEN]

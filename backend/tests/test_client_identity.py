from types import SimpleNamespace

from starlette.datastructures import Headers

from app.api.mcp.client_identity import (
    resolve_client_source,
    resolve_source_agent,
)


class _Ctx:
    """Stand-in for FastMCP Context: request_context.request.headers."""

    def __init__(self, headers: dict[str, str] | None, request_present: bool = True):
        request = SimpleNamespace(headers=Headers(headers or {})) if request_present else None
        self._request_context = SimpleNamespace(request=request)

    @property
    def request_context(self):
        return self._request_context


class _RaisingCtx:
    """Mimics Context outside a request: the property raises ValueError."""

    @property
    def request_context(self):
        raise ValueError("Context is not available outside of a request")


def test_explicit_source_wins_over_header():
    ctx = _Ctx({"x-darkmem-client": "codex"})
    assert resolve_client_source("my-orchestrator", ctx) == "my-orchestrator"


def test_explicit_mcp_is_treated_as_unspecified():
    ctx = _Ctx({"x-darkmem-client": "codex"})
    assert resolve_client_source("mcp", ctx) == "codex"


def test_explicit_source_truncated_to_column_width():
    assert resolve_client_source("x" * 150, None) == "x" * 100


def test_header_sanitized():
    ctx = _Ctx({"x-darkmem-client": "  Kiro IDE!  "})
    assert resolve_client_source(None, ctx) == "kiroide"


def test_header_beats_user_agent():
    ctx = _Ctx({"x-darkmem-client": "kiro", "user-agent": "claude-code/2.0"})
    assert resolve_client_source(None, ctx) == "kiro"


def test_claude_code_user_agent_detected():
    ctx = _Ctx({"user-agent": "claude-code/2.1.172 (cli)"})
    assert resolve_client_source(None, ctx) == "claude-code"


def test_generic_user_agents_rejected():
    for ua in [
        "node",
        "Bun/1.3.8",
        "python-httpx/0.28.1",
        "Mozilla/5.0 (Windows NT 10.0)",
    ]:
        ctx = _Ctx({"user-agent": ua})
        assert resolve_client_source(None, ctx) == "mcp", ua


def test_unknown_distinctive_ua_passes_through_slugged():
    ctx = _Ctx({"user-agent": "FutureAgent/0.3"})
    assert resolve_client_source(None, ctx) == "futureagent"


def test_empty_user_agent_treated_as_absent():
    ctx = _Ctx({"user-agent": ""})
    assert resolve_client_source(None, ctx) == "mcp"
    assert resolve_source_agent(None, ctx) is None


def test_no_signals_falls_back():
    assert resolve_client_source(None, None) == "mcp"
    assert resolve_client_source(None, _Ctx(None, request_present=False)) == "mcp"


def test_raising_request_context_swallowed():
    assert resolve_client_source(None, _RaisingCtx()) == "mcp"
    assert resolve_source_agent(None, _RaisingCtx()) is None


def test_source_agent_defaults_to_raw_ua():
    ctx = _Ctx({"user-agent": "claude-code/2.1.172 (cli)"})
    assert resolve_source_agent(None, ctx) == "claude-code/2.1.172 (cli)"


def test_explicit_source_agent_wins_and_truncates():
    ctx = _Ctx({"user-agent": "claude-code/2.1.172 (cli)"})
    assert resolve_source_agent("eval-r3", ctx) == "eval-r3"
    assert resolve_source_agent("a" * 300, None) == "a" * 255


def test_explicit_source_lowercased():
    assert resolve_client_source("My-Orchestrator", None) == "my-orchestrator"


def test_header_collapsing_to_empty_falls_through():
    ctx = _Ctx({"x-darkmem-client": "!!!", "user-agent": "claude-code/2.0"})
    assert resolve_client_source(None, ctx) == "claude-code"
    assert resolve_client_source(None, _Ctx({"x-darkmem-client": "!!!"})) == "mcp"

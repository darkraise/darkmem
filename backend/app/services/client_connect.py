"""`darkmem connect <tool>` — client MCP configuration (doc 15 §5) — T3.13.

**This writes a file, and that does not contradict T3.09.** The rule there is
that the *server* never writes the *client's* filesystem. This module is a
client-side CLI that happens to live in this repository: it runs on the
machine whose config it edits, at a human's explicit command, and nothing in
the request path imports it. The distinction is the whole trust posture, so it
is stated here rather than left for a reader to reconcile.

**It writes exactly the MCP server entry and nothing more privileged.** Not
secrets, not anything outside the tool's own config file. The LAN default is
unauthenticated behind the Host allowlist (doc 02 §8), so there is no
credential to place; when doc 18 defines one for exposed deployments this
consumes it, it does not design it.

**Idempotence is a merge, never an append.** Re-running must not leave two
darkmem entries — a second entry is not merely untidy, it is a config whose
effective server depends on which the tool reads first. So both writers parse
what is there, replace the darkmem key in place, and leave every other entry
untouched: this edits a file the human also owns.

**A `421` is reported with its real fix and never worked around.** Invariant 20
forbids the anti-pattern explicitly: a foreign-Host rejection is fixed by
extending ``MCP_ALLOWED_HOSTS`` on the server, never by disabling the
protection. This module therefore cannot emit that suggestion — a test asserts
the string never appears — because the moment a tool suggests it, someone does
it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

__all__ = [
    "DEFAULT_MCP_URL",
    "SERVER_KEY",
    "ConnectResult",
    "HandshakeFailed",
    "diagnose",
    "merge_json_config",
    "merge_toml_config",
    "render_server_entry",
    "verify_handshake",
]

# Loopback, which the Host allowlist always permits (invariant 20). A non-
# loopback host is passed explicitly, and the human is told it must be on the
# server's allowlist — the CLI never adds it for them, because the allowlist
# lives on the server and a client that could edit it would not be an allowlist.
DEFAULT_MCP_URL = "http://localhost:8000/mcp/"

# The key the entry lands under in every tool's config. Fixed rather than
# per-tool: it is what makes re-running a merge instead of an append.
SERVER_KEY = "darkmem"


class HandshakeFailed(RuntimeError):
    """Verification failed, carrying the concrete cause rather than a summary."""


@dataclass
class ConnectResult:
    tool: str
    config_path: str
    url: str
    connected: bool
    tool_count: int = 0
    diagnosis: str = ""
    tools: list[str] = field(default_factory=list)


def render_server_entry(url: str = DEFAULT_MCP_URL) -> dict:
    """The darkmem MCP server entry, in the shape every listed tool accepts."""
    return {"type": "http", "url": url}


def merge_json_config(existing: str, url: str = DEFAULT_MCP_URL) -> str:
    """Merge the darkmem entry into a JSON MCP config, preserving everything else.

    A malformed existing file is **not** overwritten silently: it raises, so a
    human who hand-edited their config into invalid JSON is told, rather than
    having the CLI replace their file with a fresh one and lose whatever was
    in it. That is the one case where "just make it work" destroys data the
    tool does not own.
    """
    if existing.strip():
        try:
            document = json.loads(existing)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"the existing MCP config is not valid JSON ({error}); refusing "
                f"to overwrite it. Fix or move the file, then re-run — this "
                f"command edits a file you also own."
            ) from error
        if not isinstance(document, dict):
            raise ValueError("the existing MCP config is not a JSON object")
    else:
        document = {}

    servers = document.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError("`mcpServers` in the existing config is not an object")
    servers[SERVER_KEY] = render_server_entry(url)

    return json.dumps(document, indent=2) + "\n"


_TOML_SECTION = re.compile(
    rf"^\[mcp_servers\.{SERVER_KEY}\]\n(?:(?!\[).*\n?)*", re.M
)


def merge_toml_config(existing: str, url: str = DEFAULT_MCP_URL) -> str:
    """Merge the darkmem table into Codex's TOML config.

    Rewritten as a targeted section replace rather than a parse-and-dump:
    Python ships a TOML *reader* and no writer, so a round trip would mean
    re-emitting a human's whole config from a parsed structure — losing their
    comments and formatting in a file they maintain by hand. Replacing only
    our own table leaves the rest byte-identical.
    """
    section = f'[mcp_servers.{SERVER_KEY}]\nurl = "{url}"\n'

    if _TOML_SECTION.search(existing):
        return _TOML_SECTION.sub(section, existing, count=1)

    separator = "" if not existing.strip() else ("\n" if existing.endswith("\n") else "\n\n")
    return f"{existing}{separator}{section}"


def config_format_for(path: str) -> str:
    """JSON or TOML, by the config file's own extension."""
    return "toml" if path.endswith(".toml") else "json"


async def verify_handshake(call) -> list[str]:
    """Drive `initialize` → `notifications/initialized` → `tools/list`.

    The real handshake, not a ping: doc 15 §5's point is that the human sees a
    green connection rather than trusting a config edit, and a reachable port
    proves neither that the endpoint speaks MCP nor that it will answer this
    client's Host. ``call`` is injected so this is testable without a server —
    the transport is the caller's, the sequence is this function's.
    """
    initialize = await call("initialize", {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "darkmem-connect", "version": "1"},
    })
    if not isinstance(initialize, dict):
        raise HandshakeFailed("initialize returned no result object")

    await call("notifications/initialized", {})

    listed = await call("tools/list", {})
    tools = (listed or {}).get("tools") or []
    if not tools:
        raise HandshakeFailed(
            "the server completed the handshake but listed no tools; the "
            "endpoint is reachable and is not serving darkmem's MCP surface"
        )
    return [t.get("name", "") for t in tools]


def diagnose(status: int | None, *, host: str, error: str | None = None) -> str:
    """The actionable failure line for a verification that did not connect.

    Every branch names the fix on the side that owns it. The `421` branch is
    the one invariant 20 legislates: the allowlist lives on the **server**, so
    the fix is to extend it there — and this function must never suggest
    turning it off, which is why the phrasing is fixed here rather than
    composed at a call site.
    """
    if status == 421:
        return (
            f"connected to the server but it refused Host {host!r} (421). "
            f"This is DNS-rebinding protection working. Fix it on the server "
            f"by adding {host!r} to MCP_ALLOWED_HOSTS, then re-run. Localhost "
            f"is always allowed, so a loopback URL needs no allowlist entry."
        )
    if status == 404:
        return (
            "the URL is reachable but there is no MCP endpoint there; check "
            "the path is /mcp/ and that this is a darkmem server"
        )
    if status in (401, 403):
        return (
            f"the server rejected the request ({status}); this deployment "
            f"requires a credential the CLI was not given"
        )
    if status is not None:
        return f"the server answered {status} rather than completing the handshake"
    return (
        f"could not reach the server ({error or 'no response'}); check it is "
        f"running and that the URL and port are right"
    )

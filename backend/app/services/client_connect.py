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
import tomllib
from pathlib import Path

__all__ = [
    "DEFAULT_MCP_URL",
    "SERVER_KEY",
    "HandshakeFailed",
    "WorkspaceRequired",
    "diagnose",
    "merge_json_config",
    "merge_toml_config",
    "render_server_entry",
    "resolve_config_path",
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


_TABLE_HEADER = re.compile(r"^\s*\[\[?\s*(?P<key>[^\]]+?)\s*\]\]?\s*(?:#.*)?$")

OUR_TABLE = f"mcp_servers.{SERVER_KEY}"


def _normalise_key(raw: str) -> str:
    """`[ mcp_servers."darkmem" ]` and `[mcp_servers.darkmem]` are one table."""
    return ".".join(part.strip().strip('"').strip("'") for part in raw.split("."))


def merge_toml_config(existing: str, url: str = DEFAULT_MCP_URL) -> str:
    """Merge the darkmem table into Codex's TOML config.

    **Line-scanned, not byte-matched, and parsed before it is returned**
    (rewritten 2026-08-09; the first version was a Critical). A regex over the
    table's exact rendering missed nine valid TOML shapes — a trailing comment
    on the header, a trailing space, CRLF, a quoted key, spaced brackets, a
    dotted key, an array-of-tables, an inline table, a multi-line array in the
    body — and every miss **appended a second** ``[mcp_servers.darkmem]``,
    which makes ``tomllib`` reject the operator's whole Codex config. The CLI
    then printed "connected" because the handshake tests the URL and not the
    file: silent data loss with success reported.

    Still a text edit rather than parse-and-dump, for the original reason —
    Python ships no TOML writer, so re-emitting would drop a hand-maintained
    file's comments. What changed is that the table is located structurally
    and the result must parse.
    """
    section = f'[{OUR_TABLE}]\nurl = "{url}"\n'
    newline = "\r\n" if "\r\n" in existing else "\n"
    lines = existing.splitlines()

    start = end = None
    for index, line in enumerate(lines):
        header = _TABLE_HEADER.match(line)
        if not header:
            continue
        if start is None and _normalise_key(header.group("key")) == OUR_TABLE:
            start = index
        elif start is not None and end is None:
            end = index
            break
    if start is not None and end is None:
        end = len(lines)

    if start is None:
        prefix = existing
        if prefix.strip() and not prefix.endswith(("\n", "\r\n")):
            prefix += newline
        if prefix.strip():
            prefix += newline
        merged = prefix + section
    else:
        # Blank and comment lines directly above the next header belong to
        # *that* section in every hand-written config, so they survive rather
        # than being swallowed with our table's body.
        tail = end
        while tail > start + 1 and (
            not lines[tail - 1].strip() or lines[tail - 1].lstrip().startswith("#")
        ):
            tail -= 1
        merged = newline.join(
            [*lines[:start], *section.rstrip("\n").split("\n"), *lines[tail:]]
        )
        if existing.endswith(("\n", "\r\n")):
            merged += newline

    # The guard the first version lacked, and the one that catches all nine
    # shapes at once: never hand back TOML that does not parse, or that does
    # not name our URL where a reader will look for it.
    try:
        parsed = tomllib.loads(merged.replace("\r\n", "\n"))
    except tomllib.TOMLDecodeError as error:
        raise ValueError(
            f"merging the darkmem entry would produce invalid TOML ({error}); "
            f"refusing to write. This command edits a file you also own."
        ) from error
    if parsed.get("mcp_servers", {}).get(SERVER_KEY, {}).get("url") != url:
        raise ValueError(
            "the merged config does not name darkmem's URL where expected; "
            "refusing to write a config whose effective server is unclear"
        )
    return merged


def config_format_for(path: str) -> str:
    """JSON or TOML, by the config file's own extension."""
    return "toml" if path.endswith(".toml") else "json"


class WorkspaceRequired(ValueError):
    """A workspace-relative config would land inside darkmem's own checkout."""


def resolve_config_path(mcp_config: str, *, workspace, repo_root) -> Path:
    """Where a tool's MCP config actually goes.

    Adapters name their config two ways and only one of them is
    self-locating. `~/.codex/config.toml` is a *user* config: absolute once
    expanded, the same file wherever the command runs. `.mcp.json`,
    `.cursor/mcp.json` and `cline_mcp_settings.json` are **workspace**
    configs, meaningful only relative to the project the tool has open — and
    resolving those against the process's cwd is what put three of the four
    shipped adapters' configs inside darkmem's own `backend/`, since that is
    where the CLI's docstring told the human to stand. The handshake then
    reported "connected", because it tests the URL and not the file.

    So a workspace-relative config resolved into this repository is
    **refused**. There is no reading of `darkmem connect claude-code` under
    which the intended answer is darkmem's own source tree, and a refusal
    naming `--workspace` costs a retry where a silent write costs a debugging
    session that starts from "the tool cannot see darkmem".

    Containment, never a name match: a project of the user's that happens to
    be called `darkmem` is a perfectly good workspace. And an *absolute* path
    is honoured even inside the checkout — the guard exists to stop an
    implicit default, not to overrule a path a human typed.
    """
    raw = Path(mcp_config).expanduser()
    if raw.is_absolute():
        return raw

    base = Path(workspace) if workspace is not None else Path.cwd()
    resolved = (base / raw).resolve()
    root = Path(repo_root).resolve()
    if resolved == root or root in resolved.parents:
        raise WorkspaceRequired(
            f"{mcp_config} is a workspace config and this would write it to "
            f"{resolved}, inside darkmem's own checkout — a workspace the "
            f"tool you are connecting never opens. Re-run from the project "
            f"directory, or pass --workspace <dir> naming it."
        )
    return resolved


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

    # A notification, not a request: sent with an id the real server answers
    # JSON-RPC -32602 and never delivers it. Masked here only because
    # darkmem's mount is stateless. `call` is told which it is so the
    # transport can omit the id.
    await call("notifications/initialized", {}, notification=True)

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

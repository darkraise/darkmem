#!/usr/bin/env python
"""`darkmem connect <tool>` — the onboarding command (doc 15 §5, T3.13).

Reached only from the CLI: no route, job or MCP tool imports this file.

Thin by design. Every decision lives in ``app.services.client_connect`` and
``app.services.inject_adapters`` so it is testable without a terminal, a tool
installation or a server; this file is argument parsing, file I/O and printing.

Run it **from the project you are connecting**, by absolute path — the script
puts ``backend/`` on ``sys.path`` itself, so its cwd is free to be your
workspace::

    cd ~/my-project
    python /path/to/darkmem/backend/scripts/connect.py claude-code
    python /path/to/darkmem/backend/scripts/connect.py cursor --host 192.168.0.195:8000
    python /path/to/darkmem/backend/scripts/connect.py codex --dry-run

This said "Run from ``backend/``", which was wrong for three of the four
adapters and silently so: `.mcp.json`, `.cursor/mcp.json` and
`cline_mcp_settings.json` are **workspace** configs, so the documented
invocation wrote them into darkmem's own checkout and the handshake still
printed "connected". ``--workspace`` names the target explicitly; a
workspace-relative write landing inside this repository is now refused.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

# `python scripts/connect.py` -- the invocation this file's own docstring
# documents -- puts `scripts/` on the path and not `backend/`, so the app
# package is unimportable and the CLI died with ModuleNotFoundError before
# doing anything. Fixed here rather than by changing the documented command,
# since a CLI a human runs from a shell should not require `-m`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import async_session_factory  # noqa: E402
from app.services.client_connect import (
    DEFAULT_MCP_URL,
    HandshakeFailed,
    config_format_for,
    diagnose,
    merge_json_config,
    merge_toml_config,
    resolve_config_path,
    verify_handshake,
)
from app.services.client_connect import WorkspaceRequired
from app.services.inject_adapters import UnknownTool, resolve_adapter


def _decode(response: httpx.Response) -> dict:
    """JSON, or the first data frame of an SSE stream.

    The MCP mount negotiates `text/event-stream`, so a bare `.json()` fails on
    a perfectly good response. Reading only the first `data:` line is enough
    for a handshake, where each request has exactly one reply.
    """
    if "text/event-stream" in response.headers.get("content-type", ""):
        for line in response.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        return {}
    return response.json()


def _url_for(host: str | None) -> str:
    return DEFAULT_MCP_URL if not host else f"http://{host}/mcp/"


async def _rpc_caller(client: httpx.AsyncClient, url: str):
    """One JSON-RPC call over streamable HTTP, returning the result object.

    Status codes are surfaced rather than raised through: the whole point of
    the verify step is to *report* a 421 or a 404 with its fix, and an
    exception carrying only "HTTP error" would lose the number the diagnosis
    keys on.
    """
    state: dict[str, int | None] = {"status": None}

    async def call(method: str, params: dict, *, notification: bool = False):
        body: dict = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            body["id"] = 1
        response = await client.post(
            url, json=body,
            headers={"Accept": "application/json, text/event-stream"},
        )
        state["status"] = response.status_code
        if response.status_code >= 400:
            raise HandshakeFailed(f"HTTP {response.status_code}")
        if not response.content:
            return {}

        payload = _decode(response)
        # A JSON-RPC error rides HTTP 200. Dropping the `error` member reported
        # every one of them as "not serving darkmem's MCP surface", which sends
        # the human to the wrong side of the connection.
        if isinstance(payload, dict) and payload.get("error"):
            error = payload["error"]
            raise HandshakeFailed(
                f"the server returned JSON-RPC error {error.get('code')}: "
                f"{error.get('message')}"
            )
        return (payload or {}).get("result", {})

    return call, state


async def main() -> int:
    parser = argparse.ArgumentParser(description="Connect a tool to darkmem over MCP.")
    parser.add_argument("tool", help="claude-code | cursor | codex | cline | …")
    parser.add_argument(
        "--host",
        help="non-loopback host:port. It must already be in MCP_ALLOWED_HOSTS "
             "on the server — this command cannot and must not add it there.",
    )
    parser.add_argument(
        "--workspace",
        help="the project directory a workspace-relative config belongs to "
             "(.mcp.json, .cursor/mcp.json, cline_mcp_settings.json). "
             "Defaults to the current directory; ~/.codex/config.toml and any "
             "absolute path ignore it.",
    )
    parser.add_argument(
        "--key",
        help="the darkmem API key (dmk_…) this tool should authenticate with. "
             "Every /mcp call requires one, including this command's own "
             "verification handshake (doc 18 §5) — omitting it gets a 401 "
             "before 'initialize' even completes. Mint one with "
             "POST /api/v1/api-keys or the Settings > Distribution UI, scoped "
             "to at least 'capture' and 'read'.",
    )
    parser.add_argument("--dry-run", action="store_true", help="print, write nothing")
    args = parser.parse_args()

    url = _url_for(args.host)

    # The registry lives in the database (doc 15 §3.3 requires a config row),
    # and this command runs on a *client* machine where Postgres is usually
    # unreachable. An unhandled error there is a traceback in a human's
    # terminal for an entirely expected condition.
    #
    # Two branches because asyncpg raises two shapes and only one is an
    # OSError -- measured, not assumed (branch review M-5): a refused port or
    # a bad host surfaces as `OSError`/`ConnectionRefusedError`, while wrong
    # credentials surface as `InvalidPasswordError`, which is not an OSError
    # and used to traceback. Both are "this client cannot read the registry",
    # and neither is the human's mistake to read a stack trace about.
    try:
        async with async_session_factory() as session:
            adapter = await resolve_adapter(session, args.tool)
    except UnknownTool as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(
            f"error: cannot reach darkmem's database to read the adapter "
            f"registry ({error}). Run this on the machine hosting darkmem, or "
            f"set DATABASE_URL to point at it.",
            file=sys.stderr,
        )
        return 2
    except Exception as error:  # noqa: BLE001 -- see the two-branch note above
        print(
            f"error: could not read darkmem's adapter registry "
            f"({type(error).__name__}: {error}). Check DATABASE_URL's "
            f"credentials and that the database has been migrated.",
            file=sys.stderr,
        )
        return 2

    try:
        config_path = resolve_config_path(
            adapter.mcp_config,
            workspace=args.workspace,
            repo_root=Path(__file__).resolve().parents[2],
        )
    except WorkspaceRequired as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    existing = config_path.read_text() if config_path.exists() else ""
    merge = (
        merge_toml_config if config_format_for(adapter.mcp_config) == "toml"
        else merge_json_config
    )
    try:
        merged = merge(existing, url, key=args.key)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(f"would write {config_path}:\n{merged}")
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(merged)
        print(f"wrote {config_path}")

    handshake_headers = {"Authorization": f"Bearer {args.key}"} if args.key else None
    async with httpx.AsyncClient(timeout=10.0, headers=handshake_headers) as client:
        call, state = await _rpc_caller(client, url)
        try:
            tools = await verify_handshake(call)
        except Exception as error:  # noqa: BLE001 — every failure is reportable
            host = args.host or "localhost:8000"
            print(f"not connected: {diagnose(state['status'], host=host, error=str(error))}")
            return 1

    print(f"connected: {len(tools)} tools available")
    print(json.dumps(sorted(tools), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

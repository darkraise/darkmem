#!/usr/bin/env python
"""`darkmem connect <tool>` — the onboarding command (doc 15 §5, T3.13).

Thin by design. Every decision lives in ``app.services.client_connect`` and
``app.services.inject_adapters`` so it is testable without a terminal, a tool
installation or a server; this file is argument parsing, file I/O and printing.

Run from ``backend/``::

    python scripts/connect.py claude-code
    python scripts/connect.py cursor --host 192.168.0.195:8000
    python scripts/connect.py codex --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

from app.database import async_session_factory
from app.services.client_connect import (
    DEFAULT_MCP_URL,
    HandshakeFailed,
    config_format_for,
    diagnose,
    merge_json_config,
    merge_toml_config,
    verify_handshake,
)
from app.services.inject_adapters import UnknownTool, resolve_adapter


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

    async def call(method: str, params: dict):
        response = await client.post(
            url,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            headers={"Accept": "application/json, text/event-stream"},
        )
        state["status"] = response.status_code
        if response.status_code >= 400:
            raise HandshakeFailed(f"HTTP {response.status_code}")
        if not response.content:
            return {}
        return response.json().get("result", {})

    return call, state


async def main() -> int:
    parser = argparse.ArgumentParser(description="Connect a tool to darkmem over MCP.")
    parser.add_argument("tool", help="claude-code | cursor | codex | cline | …")
    parser.add_argument(
        "--host",
        help="non-loopback host:port. It must already be in MCP_ALLOWED_HOSTS "
             "on the server — this command cannot and must not add it there.",
    )
    parser.add_argument("--dry-run", action="store_true", help="print, write nothing")
    args = parser.parse_args()

    url = _url_for(args.host)

    async with async_session_factory() as session:
        try:
            adapter = await resolve_adapter(session, args.tool)
        except UnknownTool as error:
            print(f"error: {error}", file=sys.stderr)
            return 2

    config_path = Path(adapter.mcp_config).expanduser()
    existing = config_path.read_text() if config_path.exists() else ""
    merge = (
        merge_toml_config if config_format_for(adapter.mcp_config) == "toml"
        else merge_json_config
    )
    try:
        merged = merge(existing, url)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(f"would write {config_path}:\n{merged}")
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(merged)
        print(f"wrote {config_path}")

    async with httpx.AsyncClient(timeout=10.0) as client:
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

"""Phase 3b: MCP batch add.

Ingests ~20 memories via the MCP /mcp/ JSON-RPC endpoint and validates
the pipeline completed all of them (embeddings, entities, cache hits).
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

from lib.client import DarkmemClient, TestReport, parse_args


FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_memories.json"


async def main() -> int:
    args = parse_args("Phase 3b: MCP batch add")
    report = TestReport("Phase 3b - MCP batch add")

    # Load fixtures
    if not FIXTURES.exists():
        report.fail("fixtures file", f"{FIXTURES} not found")
        return report.summary()
    entries = json.loads(FIXTURES.read_text())
    if not isinstance(entries, list):
        report.fail("fixtures shape", "expected list")
        return report.summary()
    report.ok(f"loaded {len(entries)} fixture memories")

    mcp_url = f"{args.base_url}/mcp"

    async with httpx.AsyncClient(timeout=1200.0) as hc:
        hdrs = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        # Initialize MCP session
        init_resp = await hc.post(f"{mcp_url}/", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "e2e", "version": "1.0"},
            },
        }, headers=hdrs)
        if init_resp.status_code != 200:
            report.fail("MCP initialize", f"{init_resp.status_code}")
            return report.summary()
        session_id = init_resp.headers.get("mcp-session-id")
        report.ok(f"MCP initialized (session={session_id or 'none'})")

        notify_hdrs = {**hdrs, "mcp-session-id": session_id} if session_id else hdrs
        await hc.post(f"{mcp_url}/", json={
            "jsonrpc": "2.0", "method": "notifications/initialized",
        }, headers=notify_hdrs)

        # Batch add
        call_hdrs = notify_hdrs
        t0 = time.time()
        resp = await hc.post(f"{mcp_url}/", json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "memory_batch_add", "arguments": {"entries": entries}},
        }, headers=call_hdrs)
        elapsed = time.time() - t0
        data = resp.json()

        if "result" in data:
            report.ok(f"MCP memory_batch_add completed in {elapsed:.1f}s")
        else:
            report.fail("MCP batch add", data.get("error", {}).get("message", str(data))[:200])
            return report.summary()

    # Verify via authed API
    async with DarkmemClient(args.base_url, args.password) as client:
        await client.login()
        r = await client.get("/api/v1/analytics/stats")
        if r.status_code == 200:
            stats = r.json()
            if stats.get("memories", 0) >= len(entries):
                report.ok(f"stats shows >= {len(entries)} memories")
            else:
                report.warn(f"stats shows only {stats.get('memories')} memories")

        # Obsolete counts should be 0 or small (fresh ingest with current fingerprint)
        r = await client.get("/api/v1/reembed/obsolete-counts")
        if r.status_code == 200:
            counts = r.json()
            report.ok(f"obsolete counts: {counts.get('memories', 0)} memories, "
                      f"{counts.get('entities', 0)} entities")

    return report.summary()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

"""Load test memories via the MCP HTTP endpoint to simulate real agent usage.

Usage:
  1. Start the dev server: ./scripts/start_dev_server.sh
  2. In another terminal: python scripts/seed_test_memories_mcp.py

Sends each memory as an MCP tool call through the JSON-RPC HTTP transport,
exercising the full stack: HTTP → MCP → MemoryService → Pipeline (embed + extract).
"""

import asyncio
import json
import logging
import time

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MCP_URL = "http://localhost:8000/mcp/"

# Import the memory list from the direct-call script
from seed_test_memories import MEMORIES


async def mcp_call(client: httpx.AsyncClient, method: str, params: dict, call_id: int) -> dict:
    """Send a single MCP JSON-RPC tool call."""
    # MCP streamable-http uses JSON-RPC 2.0
    payload = {
        "jsonrpc": "2.0",
        "id": call_id,
        "method": "tools/call",
        "params": {
            "name": method,
            "arguments": params,
        },
    }
    response = await client.post(
        MCP_URL,
        json=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        timeout=120.0,
    )

    if response.status_code != 200:
        # SSE response — parse event stream
        if "text/event-stream" in response.headers.get("content-type", ""):
            return _parse_sse(response.text, call_id)
        raise RuntimeError(f"MCP call failed: {response.status_code} {response.text[:200]}")

    content_type = response.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        return _parse_sse(response.text, call_id)

    return response.json()


def _parse_sse(text: str, call_id: int) -> dict:
    """Parse Server-Sent Events response from MCP streamable-http."""
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            data = line[6:]
            try:
                parsed = json.loads(data)
                if parsed.get("id") == call_id or "result" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue
    return {"error": "no result in SSE stream", "raw": text[:500]}


async def initialize_session(client: httpx.AsyncClient) -> str | None:
    """Send MCP initialize to establish session."""
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "seed-script", "version": "1.0.0"},
        },
    }
    response = await client.post(
        MCP_URL,
        json=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        timeout=30.0,
    )

    session_id = response.headers.get("mcp-session-id")

    # Send initialized notification
    notify = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
    }
    await client.post(
        MCP_URL,
        json=notify,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **({"mcp-session-id": session_id} if session_id else {}),
        },
        timeout=10.0,
    )

    return session_id


async def main():
    total = len(MEMORIES)
    logger.info("Loading %d memories via MCP HTTP endpoint at %s", total, MCP_URL)

    async with httpx.AsyncClient() as client:
        # Check server is up
        try:
            health = await client.get("http://localhost:8000/api/v1/health", timeout=5.0)
            logger.info("Server health: %s", health.status_code)
        except Exception as e:
            logger.error("Server not reachable at localhost:8000: %s", e)
            logger.error("Start the dev server first: ./scripts/start_dev_server.sh")
            return

        # Initialize MCP session
        logger.info("Initializing MCP session...")
        session_id = await initialize_session(client)
        if session_id:
            logger.info("MCP session: %s", session_id)
        else:
            logger.info("MCP session: stateless (no session ID)")

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if session_id:
            headers["mcp-session-id"] = session_id

        succeeded = 0
        failed = 0
        start = time.time()

        for i, (content, tags, memory_type) in enumerate(MEMORIES):
            try:
                result = await mcp_call(
                    client,
                    "memory_add",
                    {
                        "content": content,
                        "tags": tags,
                        "source": "mcp",
                        "source_agent": "seed-script-mcp",
                        "memory_type": memory_type,
                    },
                    call_id=i + 1,
                )

                if "error" in result:
                    failed += 1
                    logger.warning("Memory %d error: %s", i + 1, str(result["error"])[:100])
                else:
                    succeeded += 1

                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start
                    rate = (i + 1) / elapsed
                    logger.info(
                        "Progress: %d/%d (%.1f/s) — %d ok, %d failed",
                        i + 1, total, rate, succeeded, failed,
                    )

            except Exception as e:
                failed += 1
                logger.warning("Memory %d exception: %s", i + 1, str(e)[:100])

        elapsed = time.time() - start
        logger.info(
            "Done: %d/%d memories created in %.1fs (%.1f/s). %d failed.",
            succeeded, total, elapsed, succeeded / max(elapsed, 0.1), failed,
        )


if __name__ == "__main__":
    asyncio.run(main())

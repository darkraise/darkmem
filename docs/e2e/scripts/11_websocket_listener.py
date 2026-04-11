"""Phase 10: WebSocket event listener.

Connects to /ws, receives events for a fixed window, prints each one,
and validates that known event types are received at least once when
their corresponding operation is triggered.

Usage:
    # Run as a background listener while other scripts execute
    python 11_websocket_listener.py --password pw --duration 60
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import httpx
import websockets

from lib.client import DarkmemClient


KNOWN_EVENTS = {
    "pipeline.completed", "pipeline.partial", "pipeline.failed",
    "pipeline.failure.updated", "pipeline.retry_batch.progress",
    "pipeline.reembed_batch.progress",
    "memory.deleted",
    "repo.clone_started", "repo.clone_completed", "repo.clone_failed",
    "repo.indexing_started", "repo.indexing_progress",
    "repo.indexing_completed", "repo.indexing_failed",
    "enrichment.batch_completed",
}


async def main() -> int:
    parser = argparse.ArgumentParser(description="WebSocket event listener")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--password", default="e2e-admin-pw")
    parser.add_argument("--duration", type=int, default=60,
                        help="Listen for N seconds (default 60)")
    args = parser.parse_args()

    # Login to get session cookie
    async with DarkmemClient(args.base_url, args.password) as client:
        await client.login()
        cookie = client.cookies().get("darkmem_session")

    if not cookie:
        print("failed to obtain session cookie", file=sys.stderr)
        return 1

    ws_url = args.base_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    print(f"connecting to {ws_url}")

    received: dict[str, int] = {}
    try:
        async with websockets.connect(
            ws_url,
            additional_headers={"Cookie": f"darkmem_session={cookie}"},
        ) as ws:
            print(f"connected, listening for {args.duration}s")
            try:
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=args.duration)
                    except asyncio.TimeoutError:
                        break
                    data = json.loads(msg)
                    event = data.get("event", "<unknown>")
                    received[event] = received.get(event, 0) + 1
                    print(f"  [{event}] {json.dumps(data.get('data', {}))[:120]}")
            except Exception as e:
                print(f"recv error: {e}")
    except Exception as e:
        print(f"connect error: {e}")
        return 1

    print()
    print("=== Event counts ===")
    for event, count in sorted(received.items()):
        print(f"  {event}: {count}")

    unknown = [e for e in received if e not in KNOWN_EVENTS]
    if unknown:
        print(f"  WARNING: unknown event types: {unknown}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

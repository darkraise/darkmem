"""Phase 7: analytics and reprocessing.

Validates stats, overview, pipeline logs, and reprocess-all flow.
"""

from __future__ import annotations

import asyncio
import sys

from lib.client import DarkmemClient, TestReport, parse_args


async def main() -> int:
    args = parse_args("Phase 7: analytics and reprocess")
    report = TestReport("Phase 7 - Analytics and reprocess")

    async with DarkmemClient(args.base_url, args.password, verbose=args.verbose) as client:
        await client.login()

        # Stats
        r = await client.get("/api/v1/analytics/stats")
        if r.status_code == 200:
            stats = r.json()
            required = ("memories", "tags", "entities", "relationships", "sources")
            if all(k in stats for k in required):
                report.ok(f"stats ok: {stats['memories']} memories, {stats['tags']} tags")
            else:
                report.fail("stats keys", str(stats))
        else:
            report.fail("/analytics/stats", f"{r.status_code}")

        # Overview
        for days in (7, 30):
            r = await client.get(f"/api/v1/analytics/overview?days={days}")
            if r.status_code == 200:
                data = r.json()
                if all(k in data for k in ("counts", "activity", "sources", "top_tags", "recent_memories")):
                    report.ok(f"overview days={days}")
                else:
                    report.fail(f"overview days={days} keys", str(list(data.keys())))
            else:
                report.fail(f"overview days={days}", f"{r.status_code}")

        # Pipeline logs
        r = await client.get("/api/v1/analytics/pipeline-logs?limit=20")
        if r.status_code == 200 and isinstance(r.json(), list):
            report.ok(f"pipeline logs: {len(r.json())} entries")
        else:
            report.fail("pipeline-logs", f"{r.status_code}")

        # Legacy /reprocess-failed must be removed (Feature 2)
        r = await client.post("/api/v1/analytics/reprocess-failed")
        if r.status_code in (404, 405):
            report.ok("legacy /reprocess-failed removed")
        else:
            report.fail("legacy /reprocess-failed", f"expected 404/405, got {r.status_code}")

        # /reprocess still exists
        r = await client.post("/api/v1/analytics/reprocess")
        if r.status_code == 200:
            data = r.json()
            if "processed" in data or "error" in data:
                report.ok(f"reprocess ok: {data.get('processed', 0)} processed")
        else:
            report.warn(f"reprocess returned {r.status_code}")

    return report.summary()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

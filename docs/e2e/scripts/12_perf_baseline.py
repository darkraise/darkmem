"""Phase 11: performance baseline.

Measures latency for key operations. Warns (does not fail) unless
an operation exceeds 3× its baseline.
"""

from __future__ import annotations

import asyncio
import sys
import time

from lib.client import DarkmemClient, TestReport, parse_args


BASELINES = {
    "POST /memories single": 5.0,
    "POST /memories/search": 0.5,
    "POST /memories/search/paginated": 0.8,
    "GET /analytics/overview": 0.3,
    "GET /pipeline-failures": 0.2,
    "GET /reembed/obsolete-counts": 0.3,
    "GET /analytics/stats": 0.3,
}


async def time_op(label: str, coro) -> float:
    t0 = time.time()
    r = await coro
    elapsed = time.time() - t0
    return elapsed, r


async def main() -> int:
    args = parse_args("Phase 11: performance baseline")
    report = TestReport("Phase 11 - Performance baseline")

    async with DarkmemClient(args.base_url, args.password, verbose=False) as client:
        await client.login()

        # Single memory create (cold)
        t, r = await time_op("POST /memories single",
                             client.post("/api/v1/memories", json={
                                 "content": "perf baseline memory",
                                 "source": "e2e-perf",
                             }))
        if r.status_code == 201:
            mem_id = r.json()["id"]
            check(report, "POST /memories single", t, BASELINES["POST /memories single"])

        # Search
        t, r = await time_op("POST /memories/search",
                             client.post("/api/v1/memories/search", json={"query": "perf baseline"}))
        if r.status_code == 200:
            check(report, "POST /memories/search", t, BASELINES["POST /memories/search"])

        # Paginated search
        t, r = await time_op("POST /memories/search/paginated",
                             client.post("/api/v1/memories/search/paginated", json={"query": "perf", "limit": 10}))
        if r.status_code == 200:
            check(report, "POST /memories/search/paginated", t, BASELINES["POST /memories/search/paginated"])

        # Analytics overview
        t, r = await time_op("GET /analytics/overview",
                             client.get("/api/v1/analytics/overview?days=7"))
        if r.status_code == 200:
            check(report, "GET /analytics/overview", t, BASELINES["GET /analytics/overview"])

        # Pipeline failures
        t, r = await time_op("GET /pipeline-failures",
                             client.get("/api/v1/pipeline-failures"))
        if r.status_code == 200:
            check(report, "GET /pipeline-failures", t, BASELINES["GET /pipeline-failures"])

        # Reembed counts
        t, r = await time_op("GET /reembed/obsolete-counts",
                             client.get("/api/v1/reembed/obsolete-counts"))
        if r.status_code == 200:
            check(report, "GET /reembed/obsolete-counts", t, BASELINES["GET /reembed/obsolete-counts"])

        # Stats
        t, r = await time_op("GET /analytics/stats",
                             client.get("/api/v1/analytics/stats"))
        if r.status_code == 200:
            check(report, "GET /analytics/stats", t, BASELINES["GET /analytics/stats"])

        # Cleanup
        if 'mem_id' in locals():
            await client.delete(f"/api/v1/memories/{mem_id}")

    return report.summary()


def check(report, label: str, elapsed: float, baseline: float) -> None:
    if elapsed <= baseline:
        report.ok(f"{label}: {elapsed*1000:.0f}ms (baseline {baseline*1000:.0f}ms)")
    elif elapsed <= baseline * 3:
        report.warn(f"{label}: {elapsed*1000:.0f}ms (baseline {baseline*1000:.0f}ms, over but under 3x)")
    else:
        report.fail(label, f"{elapsed*1000:.0f}ms exceeds 3× baseline {baseline*1000:.0f}ms")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

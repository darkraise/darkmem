"""Phase 8: pipeline failure tracking and retry.

Validates Feature 2's failure tracking API and retry flow.
"""

from __future__ import annotations

import asyncio
import sys

from lib.client import DarkmemClient, TestReport, parse_args


async def main() -> int:
    args = parse_args("Phase 8: pipeline failures")
    report = TestReport("Phase 8 - Pipeline failures")

    async with DarkmemClient(args.base_url, args.password, verbose=args.verbose) as client:
        await client.login()

        # List (may be empty on a healthy system)
        r = await client.get("/api/v1/pipeline-failures")
        if r.status_code == 200:
            data = r.json()
            if "items" in data and "total" in data:
                report.ok(f"list unresolved failures: {data['total']}")
            else:
                report.fail("list shape", str(data)[:200])
        else:
            report.fail("list failures", f"{r.status_code}")

        # Counts
        r = await client.get("/api/v1/pipeline-failures/counts")
        if r.status_code == 200 and isinstance(r.json(), dict):
            report.ok(f"counts by pipeline: {r.json()}")
        else:
            report.fail("counts", f"{r.status_code}")

        # Filter
        r = await client.get("/api/v1/pipeline-failures?pipeline_name=memory_ingest")
        if r.status_code == 200:
            report.ok("filter by pipeline_name=memory_ingest")

        # 404 on missing
        r = await client.get("/api/v1/pipeline-failures/00000000-0000-0000-0000-000000000000")
        if r.status_code == 404:
            report.ok("404 on missing failure")

        # Retry-all with filter (may be a no-op on healthy system)
        r = await client.post("/api/v1/pipeline-failures/retry-all?pipeline_name=memory_ingest")
        if r.status_code == 202:
            data = r.json()
            if data.get("accepted") and "batch_id" in data:
                report.ok(f"retry-all accepted: batch_id={data['batch_id'][:8]}, total={data['total']}")
            else:
                report.fail("retry-all shape", str(data))
        else:
            report.fail("retry-all", f"{r.status_code}")

        # 503 if handler is not registered for an unknown pipeline — can't easily test this
        # without a real failure row, so we skip.

    return report.summary()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

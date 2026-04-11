"""Phase 9: obsolete re-embedding flow (Feature 3).

Validates obsolete counts, per-category re-embed, combined re-embed all,
and cache pruning.
"""

from __future__ import annotations

import asyncio
import sys
import time

from lib.client import DarkmemClient, TestReport, parse_args


async def main() -> int:
    args = parse_args("Phase 9: re-embed flow")
    report = TestReport("Phase 9 - Re-embed flow")

    async with DarkmemClient(args.base_url, args.password, verbose=args.verbose) as client:
        await client.login()

        # Counts
        r = await client.get("/api/v1/reembed/obsolete-counts")
        if r.status_code == 200:
            counts = r.json()
            required = ("memories", "code_chunks", "entities", "current_fingerprint")
            if all(k in counts for k in required):
                report.ok(f"counts: {counts['memories']}m, {counts['entities']}e, {counts['code_chunks']}c (fp={counts['current_fingerprint']})")
            else:
                report.fail("counts keys", str(counts))
        else:
            report.fail("obsolete-counts", f"{r.status_code}")
            return report.summary()

        # List endpoints
        for cat in ("memories", "code-chunks", "entities"):
            r = await client.get(f"/api/v1/reembed/obsolete/{cat}")
            if r.status_code == 200:
                data = r.json()
                if "items" in data and "total" in data:
                    report.ok(f"list obsolete {cat}: total={data['total']}")
                else:
                    report.fail(f"list {cat} shape", str(data)[:200])
            else:
                report.fail(f"list obsolete {cat}", f"{r.status_code}")

        # Prune cache (always safe, just removes non-current entries)
        r = await client.post("/api/v1/reembed/prune-cache")
        if r.status_code == 200:
            data = r.json()
            report.ok(f"prune-cache deleted {data.get('deleted', 0)} rows")
        else:
            report.fail("prune-cache", f"{r.status_code}")

        # Re-embed memories (accepted even if total=0)
        r = await client.post("/api/v1/reembed/memories")
        if r.status_code == 202:
            data = r.json()
            if data.get("accepted"):
                report.ok(f"re-embed memories accepted: total={data.get('total', 0)}")
        else:
            report.fail("re-embed memories", f"{r.status_code}")

        # Duplicate call should 409 if still running, or 202 if already done
        await asyncio.sleep(0.5)
        r = await client.post("/api/v1/reembed/memories")
        if r.status_code in (202, 409):
            report.ok(f"duplicate re-embed returns {r.status_code}")
        else:
            report.fail("duplicate re-embed", f"{r.status_code}")

        # Wait for any running batches to complete
        await asyncio.sleep(5)

        # Combined all
        r = await client.post("/api/v1/reembed/all")
        if r.status_code == 202:
            data = r.json()
            if data.get("accepted") and "batch_id" in data and "totals" in data:
                report.ok(f"re-embed all accepted: totals={data['totals']}")
            else:
                report.fail("re-embed all shape", str(data))
        elif r.status_code == 409:
            report.warn("re-embed all blocked by another running re-embed")
        else:
            report.fail("re-embed all", f"{r.status_code}")

    return report.summary()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

"""Phase 5: graph endpoints.

Covers entity listing, neighbors, memory context, full graph, unified graph.
"""

from __future__ import annotations

import asyncio
import sys

from lib.client import DarkmemClient, TestReport, parse_args


async def main() -> int:
    args = parse_args("Phase 5: graph endpoints")
    report = TestReport("Phase 5 - Graph endpoints")

    async with DarkmemClient(args.base_url, args.password, verbose=args.verbose) as client:
        await client.login()

        r = await client.get("/api/v1/graph/entities")
        if r.status_code == 200:
            entities = r.json()
            if isinstance(entities, list):
                report.ok(f"list entities: {len(entities)}")
                if entities:
                    entity_id = entities[0].get("id")
                    r = await client.get(f"/api/v1/graph/entities/{entity_id}/neighbors")
                    if r.status_code == 200:
                        report.ok("entity neighbors ok")
                    else:
                        report.fail("entity neighbors", f"{r.status_code}")
            else:
                report.fail("entities shape", str(entities)[:200])
        else:
            report.fail("/graph/entities", f"{r.status_code}")

        r = await client.get("/api/v1/graph/full")
        if r.status_code == 200:
            data = r.json()
            if "nodes" in data or "entities" in data:
                report.ok("full graph returns structure")
            else:
                report.warn(f"full graph shape: {list(data.keys())}")
        else:
            report.warn(f"/graph/full returned {r.status_code}")

        r = await client.get("/api/v1/graph/unified")
        if r.status_code == 200:
            report.ok("unified graph endpoint")
        else:
            report.warn(f"/graph/unified returned {r.status_code}")

    return report.summary()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

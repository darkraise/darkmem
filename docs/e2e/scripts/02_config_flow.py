"""Phase 2: configuration endpoints.

Covers LLM config, feature flags, enrichment config, classification areas.
"""

from __future__ import annotations

import asyncio
import sys

from lib.client import DarkmemClient, TestReport, parse_args


async def main() -> int:
    args = parse_args("Phase 2: config flow")
    report = TestReport("Phase 2 - Config flow")

    async with DarkmemClient(args.base_url, args.password, verbose=args.verbose) as client:
        await client.login()

        # 2.1 LLM config GET
        r = await client.get("/api/v1/config/llm")
        if r.status_code == 200:
            data = r.json()
            if all(k in data for k in ("embedding", "extraction", "reasoning", "summarization", "reranker")):
                report.ok("GET /config/llm returns 5 purposes")
            else:
                report.fail("/config/llm keys", str(list(data.keys())))
            # Check api_key masking
            if data.get("embedding", {}).get("api_key") in (None, "***"):
                report.ok("embedding api_key masked or null")
            else:
                report.fail("api_key masking", "raw key leaked")
        else:
            report.fail("GET /config/llm", f"status {r.status_code}")

        # 2.2 Feature flags GET
        r = await client.get("/api/v1/config/feature-flags")
        if r.status_code == 200:
            flags = r.json()
            required = [
                "llm_enrichment_enabled", "hybrid_search_enabled", "reranker_enabled",
                "pipeline_concurrency", "classification_areas", "classification_mode",
                "embedding_batch_size", "embedding_concurrency", "entity_cache_ttl_minutes",
            ]
            missing = [k for k in required if k not in flags]
            if not missing:
                report.ok("feature flags has all required keys")
            else:
                report.fail("feature flags missing keys", str(missing))
        else:
            report.fail("GET /config/feature-flags", f"status {r.status_code}")

        # 2.3 Feature flags validation
        r = await client.put("/api/v1/config/feature-flags", json={"classification_mode": "invalid"})
        if r.status_code == 422:
            report.ok("rejects invalid classification_mode")
        else:
            report.fail("classification_mode validation", f"status {r.status_code}")

        r = await client.put("/api/v1/config/feature-flags", json={"embedding_batch_size": 300})
        if r.status_code == 422:
            report.ok("rejects embedding_batch_size out of range")
        else:
            report.fail("embedding_batch_size validation", f"status {r.status_code}")

        r = await client.put("/api/v1/config/feature-flags", json={"embedding_concurrency": 0})
        if r.status_code == 422:
            report.ok("rejects embedding_concurrency=0")
        else:
            report.fail("embedding_concurrency validation", f"status {r.status_code}")

        r = await client.put("/api/v1/config/feature-flags", json={"entity_cache_ttl_minutes": 2000})
        if r.status_code == 422:
            report.ok("rejects entity_cache_ttl_minutes > 1440")
        else:
            report.fail("entity_cache_ttl_minutes validation", f"status {r.status_code}")

        # Valid update
        r = await client.put("/api/v1/config/feature-flags", json={"classification_mode": "expanded"})
        if r.status_code == 200:
            report.ok("sets classification_mode=expanded")
        r = await client.put("/api/v1/config/feature-flags", json={"classification_mode": "simple"})
        if r.status_code == 200:
            report.ok("reverts classification_mode=simple")

        # 2.4 Classification areas
        r = await client.get("/api/v1/config/classification-areas")
        if r.status_code == 200:
            areas = r.json()
            if isinstance(areas, list) and len(areas) >= 1:
                report.ok(f"classification-areas returns {len(areas)} areas")
                required_area_keys = ("key", "display_name", "types")
                first = areas[0]
                if all(k in first for k in required_area_keys):
                    report.ok("each area has key, display_name, types")
                else:
                    report.fail("area shape", str(first))
            else:
                report.fail("classification-areas shape", str(areas)[:200])
        else:
            report.fail("GET /config/classification-areas", f"status {r.status_code}")

        # 2.5 Enrichment config
        r = await client.get("/api/v1/config/enrichment")
        if r.status_code == 200:
            ec = r.json()
            if all(k in ec for k in ("enabled", "batch_size", "interval_seconds")):
                report.ok("enrichment config has all keys")
            else:
                report.fail("enrichment config", str(ec))

    return report.summary()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

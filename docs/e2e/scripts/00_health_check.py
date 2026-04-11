"""Phase 0: preflight health check.

Verifies the backend, frontend, LLM, and pgvector are all reachable
and the darkmem instance is in a known state.
"""

from __future__ import annotations

import asyncio
import sys

import httpx

from lib.client import DarkmemClient, TestReport, parse_args


async def main() -> int:
    args = parse_args("Phase 0: health check")
    report = TestReport("Phase 0 - Health check")

    async with DarkmemClient(args.base_url, args.password, verbose=args.verbose) as client:
        # /health
        try:
            r = await client.get("/health")
            if r.status_code == 200:
                health = r.json()
                if health.get("services", {}).get("pgvector"):
                    report.ok("pgvector service ok")
                else:
                    report.fail("pgvector service", str(health))
                if health.get("services", {}).get("llm"):
                    report.ok("llm service ok")
                else:
                    report.fail("llm service", str(health))
                if health.get("pipeline"):
                    report.ok("pipeline initialized")
                else:
                    report.fail("pipeline", "not initialized")
            else:
                report.fail("/health", f"status {r.status_code}")
        except Exception as e:
            report.fail("/health", str(e))

        # auth status
        try:
            status = await client.auth_status()
            if "initialized" in status:
                report.ok(f"auth/status returns initialized={status['initialized']}")
            else:
                report.fail("auth/status", f"missing initialized key: {status}")
        except Exception as e:
            report.fail("auth/status", str(e))

    # frontend check (best-effort — do not fail if unreachable from this script)
    frontend_urls = [
        "http://host.docker.internal:3636",
        "http://localhost:3636",
    ]
    async with httpx.AsyncClient(timeout=5.0) as hc:
        for url in frontend_urls:
            try:
                r = await hc.get(url)
                if r.status_code == 200 and "<html" in r.text.lower():
                    report.ok(f"frontend reachable at {url}")
                    break
            except Exception:
                continue
        else:
            report.warn("frontend not reachable at any expected URL (not fatal)")

    return report.summary()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

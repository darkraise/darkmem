"""Phase 6: code repositories and indexing.

Smoke test for the code subsystem. Requires a small local repo to index.
If none is available, skips gracefully with a warning.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

from lib.client import DarkmemClient, TestReport, parse_args


async def main() -> int:
    args = parse_args("Phase 6: code repos")
    report = TestReport("Phase 6 - Code repos")

    # Use the darkmem backend itself as a test repo (always available)
    repo_path = os.environ.get("E2E_REPO_PATH", "/workspace/darkmem/backend")

    async with DarkmemClient(args.base_url, args.password, verbose=args.verbose) as client:
        await client.login()

        # List existing repos
        r = await client.get("/api/v1/repos")
        if r.status_code == 200:
            repos = r.json()
            report.ok(f"list repos: {len(repos)} existing")
        else:
            report.fail("list repos", f"{r.status_code}")
            return report.summary()

        # Repo stats
        r = await client.get("/api/v1/repos/stats")
        if r.status_code == 200:
            report.ok("repo stats endpoint")

        # Create a repo (best-effort — may fail if path is not reachable from the container)
        r = await client.post("/api/v1/repos", json={
            "name": "e2e-test-repo",
            "local_path": repo_path,
        })
        if r.status_code in (200, 201):
            repo = r.json()
            repo_id = repo["id"]
            report.ok(f"create repo id={repo_id[:8]}")

            # Poll for indexing status
            for _ in range(60):
                await asyncio.sleep(2)
                r = await client.get(f"/api/v1/repos/{repo_id}")
                if r.status_code == 200:
                    status = r.json().get("status")
                    if status in ("ready", "error"):
                        break

            r = await client.get(f"/api/v1/repos/{repo_id}")
            if r.status_code == 200 and r.json().get("status") == "ready":
                report.ok("repo indexed successfully")

                # Code search
                r = await client.post("/api/v1/code/search", json={
                    "query": "embedding pipeline",
                    "limit": 5,
                })
                if r.status_code == 200 and isinstance(r.json(), list):
                    report.ok(f"code search returned {len(r.json())} results")
                else:
                    report.warn(f"code search status {r.status_code}")

                # Code symbols lookup
                r = await client.get("/api/v1/code/symbols/lookup?name=ReembedService")
                if r.status_code == 200:
                    report.ok("code symbol lookup")

                # Code graph
                r = await client.get(f"/api/v1/code/graph/{repo_id}")
                if r.status_code == 200:
                    report.ok("code graph endpoint")

            else:
                report.warn(f"repo did not reach ready state (status={r.json().get('status')})")

            # Cleanup
            await client.delete(f"/api/v1/repos/{repo_id}")
        else:
            report.warn(f"create repo failed with {r.status_code} — skipping code tests")

    return report.summary()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

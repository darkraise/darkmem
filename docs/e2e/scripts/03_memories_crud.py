"""Phase 3: memory CRUD and search.

Covers single-memory create, read, update, delete, search, batch,
merge, duplicates, and reason endpoints.
"""

from __future__ import annotations

import asyncio
import sys

from lib.client import DarkmemClient, TestReport, parse_args


async def main() -> int:
    args = parse_args("Phase 3: memory CRUD")
    report = TestReport("Phase 3 - Memory CRUD")

    async with DarkmemClient(args.base_url, args.password, verbose=args.verbose) as client:
        await client.login()

        # 3.1 Create
        r = await client.post("/api/v1/memories", json={
            "content": "E2E test memory: PostgreSQL uses MVCC for concurrent reads.",
            "source": "e2e-test",
            "tags": ["e2e", "tech/databases"],
            "memory_type": "fact",
        })
        if r.status_code == 201:
            mem = r.json()
            memory_id = mem["id"]
            report.ok(f"create memory id={memory_id[:8]}")
        else:
            report.fail("create memory", f"{r.status_code}: {r.text[:200]}")
            return report.summary()

        # Empty content
        r = await client.post("/api/v1/memories", json={"content": "", "source": "e2e"})
        if r.status_code == 422:
            report.ok("reject empty content")
        else:
            report.warn(f"empty content accepted with {r.status_code}")

        # 3.2 Read
        r = await client.get(f"/api/v1/memories/{memory_id}")
        if r.status_code == 200 and r.json()["id"] == memory_id:
            report.ok("read single memory")
        else:
            report.fail("read memory", f"{r.status_code}")

        r = await client.get("/api/v1/memories/00000000-0000-0000-0000-000000000000")
        if r.status_code == 404:
            report.ok("404 on missing memory")
        else:
            report.fail("404 missing", f"{r.status_code}")

        # 3.3 Update
        r = await client.put(f"/api/v1/memories/{memory_id}", json={
            "content": "E2E updated memory: PostgreSQL uses MVCC.",
        })
        if r.status_code == 200 and "updated" in r.json()["content"].lower():
            report.ok("update memory content")
        else:
            report.fail("update content", f"{r.status_code}")

        # 3.4 Create a few more for search
        extra_ids = []
        for i, payload in enumerate([
            {"content": "Redis is an in-memory key-value store.", "tags": ["e2e", "tech/cache"]},
            {"content": "Kafka provides durable partitioned event log.", "tags": ["e2e", "tech/streaming"]},
            {"content": "Elasticsearch is a distributed search engine.", "tags": ["e2e", "tech/search"]},
        ]):
            payload["source"] = "e2e-test"
            r = await client.post("/api/v1/memories", json=payload)
            if r.status_code == 201:
                extra_ids.append(r.json()["id"])

        if len(extra_ids) == 3:
            report.ok("created 3 additional memories for search")
        else:
            report.warn(f"only created {len(extra_ids)} of 3 extras")

        # Wait briefly for pipeline to embed
        await asyncio.sleep(3)

        # 3.5 Search
        r = await client.post("/api/v1/memories/search", json={"query": "database concurrency"})
        if r.status_code == 200 and isinstance(r.json(), list):
            report.ok(f"semantic search returned {len(r.json())} results")
        else:
            report.fail("semantic search", f"{r.status_code}")

        r = await client.post("/api/v1/memories/search", json={"tags_any": ["e2e"]})
        if r.status_code == 200 and len(r.json()) >= 4:
            report.ok(f"tag search returned {len(r.json())} results")
        else:
            report.fail("tag search", f"{r.status_code}")

        r = await client.post("/api/v1/memories/search/paginated", json={
            "query": "database", "limit": 2, "offset": 0,
        })
        if r.status_code == 200:
            data = r.json()
            if "items" in data and "total" in data:
                report.ok(f"paginated search: {len(data['items'])} items, total={data['total']}")
            else:
                report.fail("paginated shape", str(data)[:200])
        else:
            report.fail("paginated search", f"{r.status_code}")

        # 3.6 Duplicates
        r = await client.get(f"/api/v1/memories/{memory_id}/duplicates?threshold=0.5")
        if r.status_code == 200 and isinstance(r.json(), list):
            report.ok("duplicates endpoint returns list")
        else:
            report.fail("duplicates", f"{r.status_code}")

        # 3.7 Merge
        if len(extra_ids) >= 2:
            r = await client.post(f"/api/v1/memories/{extra_ids[0]}/merge", json={
                "target_id": extra_ids[1],
            })
            if r.status_code == 200:
                report.ok("merge memories")
            else:
                report.fail("merge", f"{r.status_code}: {r.text[:200]}")

        # 3.8 Reason
        r = await client.post("/api/v1/memories/reason", json={
            "question": "What database uses MVCC?",
            "limit": 5,
        })
        if r.status_code == 200:
            data = r.json()
            if "answer" in data and "sources" in data:
                report.ok(f"reason returns answer + {len(data['sources'])} sources")
            else:
                report.fail("reason shape", str(data)[:200])
        else:
            report.warn(f"reason returned {r.status_code} (may need longer LLM timeout)")

        # 3.9 Delete
        r = await client.delete(f"/api/v1/memories/{memory_id}")
        if r.status_code == 204:
            report.ok("delete memory")
        else:
            report.fail("delete", f"{r.status_code}")

        r = await client.get(f"/api/v1/memories/{memory_id}")
        if r.status_code == 404:
            report.ok("deleted memory returns 404")

        # Cleanup extras
        for eid in extra_ids:
            await client.delete(f"/api/v1/memories/{eid}")

    return report.summary()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

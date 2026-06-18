"""Round-3 end-to-end extraction eval.

Adds the memories in eval_round3/memories.json via the live MCP HTTP endpoint
(http://localhost:8000/mcp/), then reads the stored graph (entities, relations,
technologies, classification, supersession status) straight from the database.
Writes results.json and prints a readable per-memory summary.

Run from backend/:
    <python> scripts/eval_round3/run.py
"""
import asyncio
import json
import os
import sys
import uuid

import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, BACKEND)

from sqlalchemy import select  # noqa: E402

from app.database import async_session_factory  # noqa: E402
from app.models.graph import Entity, EntityRelation  # noqa: E402
from app.models.memory import Memory  # noqa: E402
from app.services.feature_flags import get_feature_flags_dict  # noqa: E402

MCP_URL = "http://localhost:8000/mcp/"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


def _parse_sse(text: str, call_id: int) -> dict:
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                parsed = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            if parsed.get("id") == call_id or "result" in parsed or "error" in parsed:
                return parsed
    return {"error": "no result in SSE stream", "raw": text[:300]}


async def mcp_post(client: httpx.AsyncClient, payload: dict, call_id: int) -> dict:
    resp = await client.post(MCP_URL, json=payload, headers=HEADERS, timeout=180.0)
    if "text/event-stream" in resp.headers.get("content-type", ""):
        return _parse_sse(resp.text, call_id)
    if resp.status_code != 200:
        raise RuntimeError(f"MCP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


async def initialize(client: httpx.AsyncClient) -> None:
    await mcp_post(client, {
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                   "clientInfo": {"name": "eval-r3", "version": "1.0.0"}},
    }, 0)
    await client.post(MCP_URL, json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                      headers=HEADERS, timeout=30.0)


async def reset_prior(client: httpx.AsyncClient, tag: str) -> int:
    """Delete any memories from a prior run (matched by eval tag) so a re-run
    starts clean and supersession cannot cross-contaminate the two runs."""
    payload = {
        "jsonrpc": "2.0", "id": 9001, "method": "tools/call",
        "params": {"name": "memory_search", "arguments": {"tags_any": [tag], "limit": 100}},
    }
    out = await mcp_post(client, payload, 9001)
    rows = json.loads(out["result"]["content"][0]["text"])
    n = 0
    for row in rows:
        d = {
            "jsonrpc": "2.0", "id": 9002, "method": "tools/call",
            "params": {"name": "memory_delete", "arguments": {"memory_id": row["id"]}},
        }
        await mcp_post(client, d, 9002)
        n += 1
    return n


async def add_memory(client: httpx.AsyncClient, mem: dict, call_id: int) -> dict:
    payload = {
        "jsonrpc": "2.0", "id": call_id, "method": "tools/call",
        "params": {"name": "memory_add", "arguments": {
            "content": mem["content"], "tags": mem.get("tags", []),
            "source": "mcp", "source_agent": "eval-r3",
            "memory_type": mem.get("type_hint"),
        }},
    }
    out = await mcp_post(client, payload, call_id)
    if "error" in out:
        raise RuntimeError(f"memory_add error for {mem['id']}: {out['error']}")
    text = out["result"]["content"][0]["text"]
    return json.loads(text)


async def read_graph(session, mid: uuid.UUID) -> dict:
    mem = (await session.execute(select(Memory).where(Memory.id == mid))).scalar_one_or_none()
    ents = (await session.execute(
        select(Entity).where(Entity.memory_ids.any(mid)).order_by(Entity.name)
    )).scalars().all()
    se = Entity.__table__.alias("se")
    te = Entity.__table__.alias("te")
    rel_rows = (await session.execute(
        select(se.c.name, EntityRelation.rel_type, te.c.name, EntityRelation.weight,
               EntityRelation.properties)
        .join(se, EntityRelation.source_entity_id == se.c.id)
        .join(te, EntityRelation.target_entity_id == te.c.id)
        .where(EntityRelation.memory_ids.any(mid))
        .order_by(se.c.name, EntityRelation.rel_type, te.c.name)
    )).all()
    return {
        "memory_type": mem.memory_type,
        "llm_classified_type": mem.llm_classified_type,
        "llm_summary": mem.llm_summary,
        "llm_emotions": mem.llm_emotions,
        "llm_flags": mem.llm_flags,
        "technologies": list(mem.technologies or []),
        "status": mem.status,
        "superseded_by": str(mem.superseded_by) if mem.superseded_by else None,
        "project": mem.project,
        "confidence": mem.confidence,
        "entities": [
            {"name": e.name, "type": e.entity_type,
             "display_name": (e.properties or {}).get("display_name")}
            for e in ents
        ],
        "relations": [
            {"source": r[0], "type": r[1], "target": r[2], "weight": r[3],
             "properties": r[4] or {}}
            for r in rel_rows
        ],
    }


def fmt_graph(g: dict) -> str:
    lines = [
        f"    type={g['memory_type']}  status={g['status']}"
        + (f"  SUPERSEDED_BY={g['superseded_by']}" if g["superseded_by"] else "")
        + f"  technologies={g['technologies']}",
    ]
    if g["llm_classified_type"] or g["llm_summary"]:
        lines.append(f"    llm_type={g['llm_classified_type']} llm_summary={g['llm_summary']!r}")
    lines.append("    entities:")
    for e in g["entities"]:
        dn = f"  (display:{e['display_name']})" if e["display_name"] else ""
        lines.append(f"      - {e['name']} :{e['type']}{dn}")
    lines.append("    relations:")
    for r in g["relations"]:
        lines.append(f"      - {r['source']} -{r['type']}-> {r['target']}  (w={r['weight']})")
    if not g["relations"]:
        lines.append("      (none)")
    return "\n".join(lines)


async def main():
    mem_file = sys.argv[1] if len(sys.argv) > 1 else "memories.json"
    eval_tag = sys.argv[2] if len(sys.argv) > 2 else "eval/2026-06-04-r3"
    with open(os.path.join(HERE, mem_file), encoding="utf-8") as fh:
        spec = json.load(fh)["memories"]

    async with async_session_factory() as session:
        flags = await get_feature_flags_dict(session)
    print("=== feature flags (behavioral) ===")
    for k in ("hybrid_search_enabled", "reranker_enabled",
              "relation_rescue", "confidence_rank_gamma"):
        print(f"  {k} = {flags.get(k)}")

    results = []
    async with httpx.AsyncClient() as client:
        await initialize(client)
        deleted = await reset_prior(client, eval_tag)
        print(f"\n=== reset: deleted {deleted} prior eval rows ===")
        print(f"=== adding {len(spec)} memories via MCP HTTP ===")
        for i, mem in enumerate(spec, start=1):
            added = await add_memory(client, mem, call_id=i)
            mem["_memory_id"] = added["id"]
            print(f"  {mem['id']}: id={added['id']}")
            await asyncio.sleep(0.4)  # keep created_at strictly ordered for supersession

    async with async_session_factory() as session:
        for mem in spec:
            g = await read_graph(session, uuid.UUID(mem["_memory_id"]))
            results.append({
                "id": mem["id"], "memory_id": mem["_memory_id"],
                "content": mem["content"], "type_hint": mem.get("type_hint"),
                "probe": mem.get("probe"), "gold": mem["gold"], "predicted": g,
            })

    out_path = os.path.join(HERE, os.path.splitext(mem_file)[0] + ".results.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"feature_flags": flags, "results": results}, fh, ensure_ascii=False, indent=2)

    print("\n=== PER-MEMORY EXTRACTION ===")
    for r in results:
        print(f"\n[{r['id']}] {r['content']}")
        print(f"  PROBE: {r['probe']}")
        print(fmt_graph(r["predicted"]))

    # Supersession protection check (m01 must stay active after m02 selection)
    by_id = {r["id"]: r for r in results}
    if "m01" in by_id:
        m01 = by_id["m01"]["predicted"]
        verdict = "PASS" if m01["status"] == "active" else f"FAIL (status={m01['status']})"
        print(f"\n=== supersession protection (m01 redis stays active after m02 selection): {verdict} ===")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())

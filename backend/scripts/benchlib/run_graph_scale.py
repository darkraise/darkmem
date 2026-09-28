"""Time the unified graph at scale on darkmem_bench.

Run from backend/:
  .venv/bin/python scripts/benchlib/run_graph_scale.py [--nodes 20000] [--dims 1024] [--clusters 60]

Resets darkmem_bench, seeds N memories with clustered synthetic vectors under
one fingerprint, then times GraphService.get_unified_graph(all_memories=True)
cold and warm, times the JSON encoding of its result as the route serves it,
and reports the process's peak RSS. Exits 1 when cold exceeds 10 s, warm
exceeds 1 s, peak RSS exceeds 1,500 MB, or the seeded data yields fewer than
two similarity edges per node.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import resource
import sys
import time
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = BACKEND_DIR / "scripts"
# Standalone execution only puts this file's directory on sys.path; both
# `benchlib` and `app` must resolve before either is imported.
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from benchlib import bench_db  # noqa: E402  (overrides DATABASE_URL first)

import numpy as np  # noqa: E402
from fastapi.encoders import jsonable_encoder  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.repositories.vector import PostgresVectorRepository  # noqa: E402
from app.services.embedder_registry import EmbedderInfo, child_table, embedder_registry  # noqa: E402
from app.services.graph import GraphService, reset_graph_caches  # noqa: E402

COLD_BUDGET_S = 10.0
WARM_BUDGET_S = 1.0
PEAK_RSS_BUDGET_MB = 1500
BATCH = 1000
# Same-cluster cosine is about 1 / (1 + NOISE**2), 0.8 here, so every node's
# top-k clears the 0.5 threshold as on a real corpus. Noisier data leaves the
# kNN graph nearly empty and times nothing.
NOISE = 0.5
MIN_EDGES_PER_NODE = 2


def _peak_rss_mb() -> float:
    # ru_maxrss is kilobytes on Linux.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


class _BenchLLM:
    def __init__(self, fingerprint: str):
        self.fingerprint = fingerprint
        self.calls = 0

    def llm_fingerprint(self) -> str:
        return self.fingerprint

    async def chat_completion(self, purpose, **kwargs):
        self.calls += 1
        return "bench cluster"


def _vectors(nodes: int, dims: int, clusters: int) -> np.ndarray:
    rng = np.random.default_rng(42)
    centers = rng.normal(size=(clusters, dims)).astype(np.float32)
    x = centers[rng.integers(0, clusters, nodes)] + rng.normal(scale=NOISE, size=(nodes, dims)).astype(np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


async def _seed(nodes: int, dims: int, clusters: int, fingerprint: str) -> None:
    vectors = _vectors(nodes, dims, clusters)
    async with bench_db.session_factory() as session:
        await embedder_registry.register(
            session, EmbedderInfo(fingerprint=fingerprint, model_id="bench-graph-scale", dims=dims, source="llm"),
        )
        await session.commit()
        child = child_table("memory_embeddings", fingerprint)
        for start in range(0, nodes, BATCH):
            ids = [uuid.uuid4() for _ in range(min(BATCH, nodes - start))]
            await session.execute(
                text(
                    "INSERT INTO memories (id, content, source, importance, metadata, project, "
                    "status, memory_type, is_archived) "
                    "VALUES (:id, :content, 'bench', 0.5, '{}'::jsonb, 'bench', 'active', 'fact', FALSE)"
                ),
                [{"id": mid, "content": f"bench memory {start + i}"} for i, mid in enumerate(ids)],
            )
            await session.execute(
                text(
                    f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
                    "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
                ),
                [
                    {
                        "mid": mid,
                        "fp": fingerprint,
                        "vec": "[" + ",".join(f"{v:.5f}" for v in vectors[start + i]) + "]",
                        "payload": json.dumps({"content": f"bench memory {start + i}", "source": "bench", "tags": [f"topic-{(start + i) % clusters}"]}),
                    }
                    for i, mid in enumerate(ids)
                ],
            )
            await session.commit()


async def _time_graph(fingerprint: str) -> tuple[float, float, dict, int]:
    llm = _BenchLLM(fingerprint)
    reset_graph_caches()
    async with bench_db.session_factory() as session:
        svc = GraphService(session, vector_repo=PostgresVectorRepository(session), llm=llm)
        t0 = time.perf_counter()
        cold = await svc.get_unified_graph(all_memories=True, similarity_threshold=0.5, project="bench")
        t1 = time.perf_counter()
        await svc.get_unified_graph(all_memories=True, similarity_threshold=0.5, project="bench")
        t2 = time.perf_counter()
    return t1 - t0, t2 - t1, cold, llm.calls


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodes", type=int, default=20_000)
    parser.add_argument("--dims", type=int, default=1024)
    parser.add_argument("--clusters", type=int, default=60)
    args = parser.parse_args()
    fingerprint = f"bench-graph-scale|{args.dims}"

    await bench_db.reset_bench_db()
    t_seed = time.perf_counter()
    await _seed(args.nodes, args.dims, args.clusters, fingerprint)
    print(f"seeded {args.nodes} memories in {time.perf_counter() - t_seed:.1f}s")

    rss_before = _peak_rss_mb()
    cold_s, warm_s, result, llm_calls = await _time_graph(fingerprint)
    # The route declares no response model, so every response, cache hits
    # included, pays this encoding on the event loop.
    t_encode = time.perf_counter()
    body = json.dumps(jsonable_encoder(result), ensure_ascii=False, separators=(",", ":"))
    encode_s = time.perf_counter() - t_encode
    rss_after = _peak_rss_mb()
    edges = len(result["similarity_edges"])
    print(
        f"nodes={len(result['memories'])} total={result['total_memories']} "
        f"edges={edges} clusters={len(result['clusters'])} "
        f"llm_calls={llm_calls} cold={cold_s:.2f}s warm={warm_s:.3f}s "
        f"encode={encode_s:.2f}s body={len(body) / 1_000_000:.1f}MB "
        f"peak_rss={rss_after:.0f}MB (after seeding {rss_before:.0f}MB)"
    )
    await bench_db.engine.dispose()
    ok = (
        cold_s <= COLD_BUDGET_S
        and warm_s <= WARM_BUDGET_S
        and rss_after <= PEAK_RSS_BUDGET_MB
        and len(result["memories"]) == args.nodes
        and edges >= MIN_EDGES_PER_NODE * args.nodes
    )
    print(
        "PASS" if ok else
        f"FAIL (budgets: cold <= {COLD_BUDGET_S}s, warm <= {WARM_BUDGET_S}s, "
        f"peak RSS <= {PEAK_RSS_BUDGET_MB}MB, edges >= {MIN_EDGES_PER_NODE} x nodes)"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

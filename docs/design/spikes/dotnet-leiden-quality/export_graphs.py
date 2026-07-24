"""Export real darkmem code graphs (per repo) + synthetic benchmarks as edge lists.

Uses the exact node/edge SQL of app/services/community_detector.py so the managed
implementation is validated on the same graphs production Leiden sees.

Edge-list format: line 1 = "<n_nodes>", then one "src tgt" int pair per line.
Synthetic graphs get a ".planted" file with the ground-truth membership.
"""

import asyncio
import random
import sys
from pathlib import Path

import asyncpg

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "graphs")
DSN = "postgresql://darkmem:darkmem@localhost:5433/darkmem"

NODE_SQL = """
    SELECT key FROM code_graph_nodes
    WHERE repo_id = $1 AND kind = 'symbol'
      AND properties->>'kind' IN ('function','method','class','interface','struct','trait')
"""
EDGE_SQL = """
    SELECT e.source_key, e.target_key
    FROM code_edges e
    JOIN code_graph_nodes src ON src.repo_id = e.repo_id AND src.key = e.source_key
    JOIN code_graph_nodes tgt ON tgt.repo_id = e.repo_id AND tgt.key = e.target_key
    WHERE e.repo_id = $1 AND e.edge_type IN ('calls','extends','implements')
      AND src.kind = 'symbol'
      AND src.properties->>'kind' IN ('function','method','class','interface','struct','trait')
      AND tgt.kind = 'symbol'
      AND tgt.properties->>'kind' IN ('function','method','class','interface','struct','trait')
"""


def write_graph(name: str, n: int, edges: list[tuple[int, int]], planted: list[int] | None = None):
    p = OUT / f"{name}.txt"
    with p.open("w") as f:
        f.write(f"{n}\n")
        for s, t in edges:
            f.write(f"{s} {t}\n")
    if planted is not None:
        (OUT / f"{name}.planted").write_text("\n".join(map(str, planted)))
    print(f"{name}: n={n} m={len(edges)}")


def planted_graph(name: str, n_comm: int, comm_size: int, p_in: float, p_out_edges: int, seed: int):
    rng = random.Random(seed)
    n = n_comm * comm_size
    planted = [i // comm_size for i in range(n)]
    edges = []
    for c in range(n_comm):
        base = c * comm_size
        for i in range(comm_size):
            for j in range(i + 1, comm_size):
                if rng.random() < p_in:
                    edges.append((base + i, base + j))
    for _ in range(p_out_edges):
        a, b = rng.randrange(n), rng.randrange(n)
        if planted[a] != planted[b]:
            edges.append((a, b))
    write_graph(name, n, edges, planted)


async def main():
    OUT.mkdir(exist_ok=True)
    conn = await asyncpg.connect(DSN)
    repos = await conn.fetch("SELECT id, name FROM repositories")
    for r in repos:
        keys = [row["key"] for row in await conn.fetch(NODE_SQL, r["id"])]
        if len(keys) < 3:
            continue
        idx = {k: i for i, k in enumerate(keys)}
        edges = []
        for row in await conn.fetch(EDGE_SQL, r["id"]):
            s, t = idx.get(row["source_key"]), idx.get(row["target_key"])
            if s is not None and t is not None:
                edges.append((s, t))
        if edges:
            write_graph(f"repo-{r['name']}", len(keys), edges)
    await conn.close()

    planted_graph("synth-planted", n_comm=25, comm_size=40, p_in=0.3, p_out_edges=800, seed=7)
    planted_graph("synth-scale", n_comm=200, comm_size=250, p_in=0.08, p_out_edges=50_000, seed=11)


asyncio.run(main())

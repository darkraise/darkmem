"""Run darkmem's exact production Leiden call (leidenalg RBConfigurationVertexPartition)
on each exported graph and record membership + RB-modularity for the managed spike to
compare against. Mirrors community_detector.py: undirected, seed=0; resolution 1.0 /
n_iterations=-1 for graphs <= 10k nodes, resolution 2.0 / 3 iterations above (the
production large-graph regime).
"""

import json
import sys
import time
from pathlib import Path

import igraph
import leidenalg

GRAPHS = Path(sys.argv[1] if len(sys.argv) > 1 else "graphs")
LARGE = 10_000


def rb_modularity(n, edges, membership, gamma):
    m = len(edges)
    if m == 0:
        return 0.0
    deg = [0] * n
    intra = {}
    dsum = {}
    for s, t in edges:
        deg[s] += 1
        deg[t] += 1
        if membership[s] == membership[t]:
            intra[membership[s]] = intra.get(membership[s], 0) + 1
    for v in range(n):
        dsum[membership[v]] = dsum.get(membership[v], 0) + deg[v]
    q = 0.0
    for c, d in dsum.items():
        q += intra.get(c, 0) / m - gamma * (d / (2 * m)) ** 2
    return q


for path in sorted(GRAPHS.glob("*.txt")):
    lines = path.read_text().split("\n")
    n = int(lines[0])
    edges = [tuple(map(int, l.split())) for l in lines[1:] if l.strip()]
    gamma, iters = (2.0, 3) if n > LARGE else (1.0, -1)
    g = igraph.Graph(n=n, edges=edges, directed=False)
    t0 = time.perf_counter()
    part = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        resolution_parameter=gamma, n_iterations=iters, seed=0,
    )
    dt = time.perf_counter() - t0
    membership = list(part.membership)
    q = rb_modularity(n, edges, membership, gamma)
    out = {
        "n": n, "m": len(edges), "gamma": gamma, "n_iterations": iters,
        "communities": len(set(membership)), "rb_modularity": q,
        "seconds": round(dt, 3), "membership": membership,
    }
    path.with_suffix(".python.json").write_text(json.dumps(out))
    print(f"{path.stem}: n={n} m={len(edges)} gamma={gamma} "
          f"comms={out['communities']} Q_rb={q:.4f} {dt:.2f}s")

# Spike: full Leiden quality/scale validation vs leidenalg (the #15 residual)

**Date:** 2026-07-24 · **Context:** feeds `docs/design/03a-backend-stack-dotnet-viability.md` §5.2 (matrix row #15, the last non-harness yellow).

## Why

The 2026-07-23 `dotnet-graph/` spike proved community detection *feasible* in pure
managed C# (Louvain + connectivity refinement), but left #15 yellow: quality parity
versus `leidenalg`'s `RBConfigurationVertexPartition` and behaviour at real darkmem
graph scale were unvalidated. The maintainer's bar is all-green except the eval
harness, so this spike implements **full Leiden** and measures it against darkmem's
exact production call on darkmem's real data.

## What it is

- `Program.cs` — full Leiden in pure managed C#, no dependencies (~450 LOC):
  fast local move (queue-based) → **randomized well-connectedness refinement**
  (nodes/sub-communities merge only when well-connected to their community, target
  chosen randomly among positive-gain candidates, seeded RNG) → **aggregation
  constrained by the unrefined partition** — the actual Leiden algorithm (Traag et
  al. 2019), not the earlier connectivity-only approximation. RBConfiguration
  quality with resolution γ; weighted graphs; self-loops handled.
- `export_graphs.py` — exports the **real darkmem code graph** from the dev Postgres
  (5433) using `community_detector.py`'s exact node/edge SQL, plus two synthetic
  planted-partition benchmarks (1k nodes and 50k nodes / 547k edges).
- `python_reference.py` — darkmem's exact production call (`leidenalg.find_partition`,
  `RBConfigurationVertexPartition`, seed=0; γ=1.0 / converge below 10k nodes,
  γ=2.0 / 3 iterations above — the `community_detector.py` regime switch) on the
  same graphs; records membership + RB-modularity (identical metric formula on both
  sides; the C# side re-scores the Python membership and asserts agreement to 1e-6).

## Result (observed, exit 0 — all PASS)

```
[repo-GitNexus] n=6821 m=4438 gamma=1        (real darkmem code graph)
  managed : comms=3832 Q_rb=0.8858 0.04s
  python  : comms=3842 Q_rb=0.8893 0.09s
  compare : dQ=-0.0035 NMI(managed,python)=0.984 quality-parity=PASS

[synth-planted] n=1000 m=6669 gamma=1
  compare : dQ=+0.0000 NMI(managed,python)=1.000 PASS   planted NMI=1.000 PASS

[synth-scale] n=50000 m=547253 gamma=2       (production large-graph regime)
  managed : comms=200 Q_rb=0.8991 0.18s      (leidenalg: 0.79s)
  compare : dQ=+0.0000 NMI=1.000 PASS        planted NMI=1.000 PASS
  scale   : 0.18s vs 60s prod timeout PASS
```

**Quality parity is measured, not assumed:** −0.4% RB-modularity on the real graph
with 98.4% partition agreement, *exact* quality and membership agreement on both
synthetic benchmarks, and the managed implementation is ~4× faster than leidenalg
at 50k nodes / 547k edges — 7× darkmem's current real graph, at 0.3% of the
production 60s timeout.

## Honest caveats

- Outputs remain **not bit-identical** to Python run-to-run possibilities (different
  implementation and RNG); this is inherent and permanent. Communities are a soft
  signal; tests must not pin exact membership. Deterministic per seed in .NET.
- The refinement picks uniformly at random among positive-gain well-connected
  candidates rather than exp(ΔQ/θ)-weighted (leidenalg's θ=0.01 near-greedy variant);
  the measured parity above is with this simplification.
- The real memory graph (`entities`/`entity_relations`) was empty in the dev DB, so
  the real-data validation covers the code graph; the Louvain memory-graph path
  shares this code and was validated on the synthetics.

## Reproduce

```
docker compose -f docker-compose.dev.yml up -d postgres   # dev DB on 5433
python export_graphs.py graphs
python python_reference.py graphs                          # needs igraph + leidenalg
dotnet run -c Release -- graphs                            # exit 0 = all PASS
```

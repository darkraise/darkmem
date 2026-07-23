# Spike: graph community detection + PageRank in pure-managed .NET

**Date:** 2026-07-23 · **Context:** feeds `docs/design/03a-backend-stack-dotnet-viability.md` §5.2.

## Why

The .NET viability study rated **community detection** the one hard 🔴 with no
drop-in .NET peer — the plan was to P/Invoke the native C **igraph** library for
Leiden. The maintainer named the graph (memory-graph Louvain + code-graph Leiden)
**the deal-breaker**: spike it, and if it is hard in .NET, stay on Python.

This spike tests a sharper question the environment forced: this dev box has
**.NET 10 but no C compiler and no CMake**, and there is **no prebuilt igraph .NET
binding on NuGet** and **no dedicated C# Leiden library**. So — can .NET do the
community detection darkmem needs in **pure managed code, no native interop**?

## What it does (`Program.cs`, ~250 LOC, no dependencies)

- **Louvain** (multi-level local-moving + aggregation) — the memory-graph algorithm.
- **Leiden connectivity refinement** — splits any disconnected community into its
  connected components (the guarantee plain Louvain lacks; the reason Leiden was adopted).
- **PageRank + Personalised PageRank** (CSR-style power iteration) — the target
  graph-augmented retrieval signal (absent in darkmem today).
- Validates against a planted 3-community graph (3 near-cliques + 3 thin bridges).

## Result (observed)

```
Planted communities : 3  -> [0,0,0,0,0,0,1,1,1,1,1,1,2,2,2,2,2,2]
Louvain  communities: 3  Q=0.6042  -> [0,0,0,0,0,0,1,1,1,1,1,1,2,2,2,2,2,2]
Louvain recovers planted structure? YES

Disconnected-community guarantee:
  bad partition       : 3 groups (node 13 forced into community A)
  after Leiden refine : 4 groups  (node 13 split back out: YES)

PPR seed=0 top-5 : [n0:0.241, n5:0.106, n1:0.100, n2:0.100, n3:0.100]
PPR concentrates in seed's community? YES

=== VERDICT: pure-managed community detection + PPR WORKS with NO native dependency ===
```

## Verdict

**The graph deal-breaker is cleared.** Louvain, the Leiden connected-community
guarantee, and PageRank/PPR are all achievable in pure managed C# with **no native
igraph, no CMake, no per-RID native bundling** — which is *easier* than the memo's
P/Invoke-igraph route, and preserves the single-artifact ethos.

## Honest caveats (what this does NOT prove)

- This is a **spike**, not production code. The refinement implements Leiden's
  *connectivity* guarantee, not its full randomised refinement phase; quality parity
  vs `leidenalg`'s `RBConfigurationVertexPartition` and behaviour at **real darkmem
  graph scale** still need validation.
- Results will **not be bit-identical** to the Python/igraph output (different
  implementation) — acceptable for community detection (a soft grouping signal), but
  any test pinning exact membership must tolerate it.
- The resolution parameter γ is supported; its tuning against today's outputs is
  follow-up work.

## Reproduce

```
dotnet new console -o .    # then replace Program.cs with this one
dotnet run -c Release
```
Requires only the .NET SDK (10.x used here). Exit code 0 = all checks pass.

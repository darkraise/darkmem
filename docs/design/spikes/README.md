# .NET gap-closure spikes (2026-07-23)

Hands-on spikes run to drive the non-green rows of the .NET viability matrix
(`../03a-backend-stack-dotnet-viability.md` §4) toward green. The maintainer's bar
was **all risk green** before adopting .NET, so each spike either proves a gap closed
or pins down exactly what residual remains. All ran on **.NET 10.0.302** (this dev
box has the SDK but **no C compiler and no CMake** — that constraint is itself a
finding). Each project: `dotnet run -c Release`, exit 0 = all checks pass.

| Spike | Gap(s) | Result |
|---|---|---|
| `dotnet-graph/` | Leiden (code) + Louvain (memory) + PPR — **the deal-breaker** | 🟢 pure-managed, no native igraph: recovered planted communities Q≈0.60, Leiden connectivity split, PPR localised |
| `dotnet-data/` | per-fingerprint runtime DDL, pgvector, asyncpg-CAST | 🟢 live vs dev Postgres: runtime child-table + sanitised slug + **no-CAST** vector insert + `<=>` cosine round-trip |
| `dotnet-numeric/` | numeric core (DBSCAN / cosine / eigen) | 🟢 DBSCAN recovered 3 clusters + 2 noise; MathNet eigen 2-D projection |
| `dotnet-treesitter/` | tree-sitter binding + grammar breadth | 🟢 binding: parsed C#/Python/PHP + S-expr query + `#eq?` predicate metadata. 🔴 residual: 21/33 grammars bundled, **12 need a per-RID self-compile** (kotlin, lua, yaml, sql, zig, elixir, xml, regex, cmake, make, objc, markdown) — **cleared 2026-07-24 by `dotnet-grammar-ci/`** |
| `dotnet-mcp/` | MCP header source-resolution + Host allowlist | 🟢 over real HTTP: `IHttpContextAccessor` read `X-Darkmem-Client`; allowlist middleware returned **421** for foreign Host, passed localhost to `MapMcp` |
| `dotnet-grammar-ci/` (2026-07-24) | the 12 unbundled grammars — #14, the last red-derived residual | 🟢 **all 12 compiled with `zig cc`** (14 artifacts incl. xml/dtd + markdown/inline; all 8 external scanners) and **loaded 12/12 through stock `Language(path, fn)`** — parse + query end to end, no binding fork; `zig cc -target` cross-compiled win/linux/osx × x64/arm64 from this one box, so CI is a single runner, no OS matrix. Stage 2: **single-DLL grammar pack** (`build-grammar-pack.sh`) — 16 grammars (incl. python + c-sharp) linked into ONE library per RID, zero symbol collisions, 6/6 languages loaded from the single file |
| `dotnet-leiden-quality/` (2026-07-24) | Leiden quality/scale vs `leidenalg` — #15, the last non-harness yellow | 🟢 **full Leiden** (local move + randomized well-connectedness refinement + constrained aggregation, ~450 LOC, no deps) vs darkmem's exact production call on the **real code graph from the dev DB** (6,821n/4,438m: ΔQ −0.4%, NMI 0.984) + planted benchmarks (exact agreement, NMI 1.000) + 50k/547k scale in the prod γ=2 regime (**0.18s vs leidenalg 0.79s**, 60s timeout) |
| `dotnet-benchlib/` (2026-07-24) | eval-harness core — #24, the final yellow | 🟢 all three mechanisms rebuilt in .NET and proven vs the Python originals: Npgsql bench-DB lifecycle (create → schema reset → migrate stand-in → drop); **26/26 reuse of the real Python-built LLM cache** via byte-identical `sha256(content+"\x00"+prompt)[:16]` keys; 4-dim F1 scorer **exactly identical** to run_bench.py on the real cached outputs (26/26 per-memory F1s at 1e-12, exact tp/fp/fn) |

## Verified library versions (NuGet, restored live)

Npgsql 10.0.3 · Pgvector 0.3.2 · MathNet.Numerics 5.0.0 · TreeSitter.DotNet 1.3.0
(21 bundled grammars, 9 RIDs) · ModelContextProtocol.AspNetCore 1.4.1 · zig 0.16.0
(winget `zig.zig`; the grammar-build toolchain).

## Net result

Of the matrix's non-green rows, everything with genuine **feasibility** uncertainty
is now green and spike-proven. The residuals are **not feasibility walls**:

- 🟢 **tree-sitter grammar breadth (#14)** — *cleared 2026-07-24* (`dotnet-grammar-ci/`):
  the assumed "per-RID CI pipeline with a C toolchain" collapsed to a single `zig cc`
  install — all 12 grammars compiled (incl. every external scanner) and loaded 12/12
  through the stock binding's external-library constructor, cross-compiled to all 5
  RIDs from this very box. Residual = wiring the one-runner CI workflow + packaging
  the grammar pack (pure chore). Gotchas recorded there: sql's generated sources live
  on its `gh-pages` branch; `zig cc` needs `-fno-sanitize=undefined`.
- 🟢 **Leiden quality/scale (#15)** — *cleared 2026-07-24* (`dotnet-leiden-quality/`):
  full Leiden implemented and measured against the production leidenalg call on the
  real darkmem code graph (quality parity within 0.4%, 98.4% partition agreement,
  exact on benchmarks, 4× faster at 7× real scale). Bit-exact parity remains
  permanently unattainable (different implementation) — accepted for a soft signal.
- 🟢 **eval harness rebuild (#24)** — *core cleared 2026-07-24* (`dotnet-benchlib/`):
  bench-DB lifecycle, byte-identical cache-key reuse of the existing Python-built
  cache (zero LLM re-hits), and an F1 scorer proven exactly identical to
  run_bench.py on real data. Residual = assembling the full harness (runner CLI,
  remaining benches) around the proven core — scheduled port effort, not risk.

**Matrix status: 24 green / 0 yellow / 0 red — fully green (2026-07-24).**

**Decision (2026-07-24): Option A — Python retained despite the fully-green matrix**
(appetite/benefit call, not feasibility: ship the Python target first). This corpus
is kept as the de-risking record for the deferred post-target .NET migration.

Decisions taken to green two rows: **ORM** → Dapper (hot reads + vector) + DbUp
(migrations), EF Core optional and avoided if Native AOT is wanted; **validation** →
FluentValidation + `IOptions`, porting the pydantic validators by hand.

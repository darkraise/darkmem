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
| `dotnet-treesitter/` | tree-sitter binding + grammar breadth | 🟢 binding: parsed C#/Python/PHP + S-expr query + `#eq?` predicate metadata. 🔴 residual: 21/33 grammars bundled, **12 need a per-RID self-compile** (kotlin, lua, yaml, sql, zig, elixir, xml, regex, cmake, make, objc, markdown) |
| `dotnet-mcp/` | MCP header source-resolution + Host allowlist | 🟢 over real HTTP: `IHttpContextAccessor` read `X-Darkmem-Client`; allowlist middleware returned **421** for foreign Host, passed localhost to `MapMcp` |

## Verified library versions (NuGet, restored live)

Npgsql 10.0.3 · Pgvector 0.3.2 · MathNet.Numerics 5.0.0 · TreeSitter.DotNet 1.3.0
(21 bundled grammars, 9 RIDs) · ModelContextProtocol.AspNetCore 1.4.1.

## Net result

Of the matrix's non-green rows, everything with genuine **feasibility** uncertainty
is now green and spike-proven. The residuals are **not feasibility walls**:

- 🔴 **tree-sitter grammar breadth (#14)** — the one item that cannot be greened on a
  box without a C toolchain: the 12 unbundled grammars need a per-RID CI build
  pipeline (tree-sitter CLI + a C compiler). Bounded build-engineering, not a wall.
- 🟡 **Leiden quality/scale (#15)** — feasibility + the connectivity guarantee are
  proven; bit-exact parity vs `leidenalg` is permanently unattainable (different
  implementation) and large-scale validation remains an implementation task.
- 🟡 **eval harness rebuild (#24)** — `benchlib` must be re-implemented in the new
  stack before parity can be *measured* (doc 00 §7.2); unavoidable effort, not risk.

Decisions taken to green two rows: **ORM** → Dapper (hot reads + vector) + DbUp
(migrations), EF Core optional and avoided if Native AOT is wanted; **validation** →
FluentValidation + `IOptions`, porting the pydantic validators by hand.

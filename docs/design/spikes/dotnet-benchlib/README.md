# Spike: eval-harness core in .NET (the #24 residual — the last yellow)

**Date:** 2026-07-24 · **Context:** feeds `docs/design/03a-backend-stack-dotnet-viability.md` §5.3 / matrix row #24.

## Why

#24 was the final non-green row: "the harness must be rewritten before parity can be
measured." The harness core is three small mechanisms (`benchlib/bench_db.py`,
`benchlib/caching_llm.py`, `extraction_bench/run_bench.py`'s scorer); this spike
rebuilds all three in .NET and proves them against the Python originals on the real
bench data.

## What it proves (all observed, exit 0)

1. **Bench-database lifecycle (Npgsql).** `bench_db.py`'s reset discipline — create a
   dedicated bench DB, `DROP SCHEMA public CASCADE` + `CREATE SCHEMA`, re-migrate
   (stand-in DDL; the DbUp chain is the already-green migrations row), verify, drop —
   runs cleanly against the dev Postgres.
2. **The .NET harness reuses the Python-built LLM cache byte-for-byte.** run_bench.py's
   key (`sha256(content + "\x00" + system_prompt)[:16]`) computed in C# hit
   **26/26** of the real `.cache/` files under `backend/scripts/extraction_bench/`
   (prompt read from `app.services.prompt` via `python_reference.py`). Write-path
   round-trip verified in the same format. Consequence: the ported harness starts
   from the *same raw LLM outputs* with zero re-hits.
3. **F1 scorer parity is exact.** The 4-dimension micro P/R/F1 scorer (entity
   name+type / name-only, relation full/pair, lowercase-norm set semantics) scored
   the raw cached outputs against `gold.json` in both stacks:
   all **26/26 per-memory F1s identical at 1e-12**, and all four aggregate
   dimensions with **exact tp/fp/fn counts** and identical F1s
   (ent_nt 0.825 · ent_n 0.951 · rel_full 0.894 · rel_pair 0.894).

## Why this greens #24

The yellow's risk was "parity cannot be measured until the harness exists." The
measuring machinery now exists and is proven **identical**: same cache keys, same
raw inputs, same scorer output to the digit. When the ~40 `clean_extraction` passes
are ported (scheduled port work, §5.3), their F1 will be measured by this scorer
against the same cached raw outputs — any delta is attributable purely to the ported
passes, not to model drift or metric skew. What remains is assembling the full
harness around the proven core (runner CLI, remaining benches) — effort on the
port's critical path, no longer an unvalidated mechanism.

## Reproduce

```
docker compose -f docker-compose.dev.yml start postgres   # dev DB on 5433
python python_reference.py     # writes prompt.txt + reference.json (real cache, real gold)
dotnet run -c Release          # exit 0 = all three mechanisms PASS
```

`python_reference.py` copies run_bench.py's 25 lines of scoring functions verbatim
(importing run_bench pulls app-database imports); the copy is eye-diffable.

# EH2 — H2: .NET migration (horizon lane) — outline only

**Status:** deliberately **not** broken into tasks.

**Advance gate:** **G-G** — the Python target shipped, and the harness exists in the new
stack *before* any parity claim: byte-identical LLM-cache reuse and exact F1-scorer parity.

---

## Why there are no tasks here

This lane cannot open until the Python target ships (G-G's first clause). Task-level
detail written now would describe a codebase that does not exist yet against a target
shape still being built — it would be obsolete before anyone read it, and maintaining it
through E1–E3 would cost more than rewriting it fresh.

What *is* worth recording now is the entry condition, the proven ground, and the named
residuals — so that when the lane opens, planning starts from evidence rather than from
scratch.

**Horizon pull is a named risk** (doc 20 §8): a clean-slate rewrite is the single most
tempting queue-jump in this roadmap. The firewall is that nothing in Phases 0–4 depends on
this lane, which makes deferring it genuinely free. Pulling it earlier costs the committed
path directly.

---

## Entry conditions (all must hold)

1. **The Python target shipped.** Phases 0–3 complete, G-E cleared.
2. **Maintainer appetite**, explicitly stated — this lane is never entered by momentum.
3. **The harness ports first.** No parity claim may be made before the new stack can
   reproduce the measurement: byte-identical LLM-cache reuse and an F1 scorer proven
   identical to `run_bench.py` on real cached outputs.

---

## Proven ground (spikes already run)

These are settled and should not be re-litigated when the lane opens:

| Question | Verdict | Evidence |
|---|---|---|
| Can the harness port with exact parity? | **Yes** — 26/26 LLM-cache reuse via byte-identical sha256 keys; F1 scorer identical to 1e-12 | `spikes/dotnet-benchlib/` |
| Can runtime partition DDL work from C#? | **Yes** — runtime child-table DDL, sanitised slug, no-CAST vector insert, `<=>` round-trip all proven live | `spikes/dotnet-data/` |
| Does the asyncpg `CAST` workaround carry over? | **No, and it disappears** — Npgsql resolves types client-side, so that whole bug class vanishes | doc 03a §3 |
| Can tree-sitter grammars ship? | **Yes** — stock binding plus a `zig cc` grammar pack (12 grammars, single DLL, all 5 RIDs). A packaging task, not a feasibility risk | doc 03a §5.1.1 |
| Does Leiden match? | **Close, never identical** — −0.4% modularity, 98.4% partition agreement | doc 19 §7 |

---

## Named residuals (no matrix red, but real work)

- **Full-harness assembly** around the proven benchlib core.
- **Telemetry gap:** psutil/pynvml have no direct .NET equivalent. The port needs
  `System.Diagnostics` plus a GPU-vendor library, or a documented graceful degrade.
- **Leiden non-determinism is permanent.** Any test pinning exact community membership
  must tolerate the measured residual. This is already the rule in the Python stack
  (doc 17 §7) and it carries over — it is not a porting defect.

---

## Work shape when the lane opens

Roughly, and in this order — the ordering is the load-bearing part:

1. **Harness first.** Port `benchlib` and the F1 scorer; prove byte-identical cache reuse
   and scorer parity. Nothing else starts until this holds.
2. **SQL-first baseline replay.** The single Alembic baseline (kept plain-SQL by rule)
   becomes the first script of a DbUp chain baselined from a schema snapshot;
   `alembic_version` is dropped. Homelab data carries via `pg_dump`/restore.
3. **Registry DDL in C#.** Boot-time partition reconciliation moves to the C# equivalent,
   carrying register-before-insert, `child_table`-only naming, and no cross-fingerprint
   joins forward as invariants rather than as Python code.
4. **Pipeline + cleanup passes**, each pass gated on a measured F1 delta against the
   ported harness. `gold.json` is stack-neutral JSON and carries verbatim, so any delta is
   attributable purely to the ported pass — never to model drift or metric skew.
5. **Code indexing**, via the grammar pack.

**Magnitude anchor:** ~19–38 weeks (≈5–9 months) single-engineer sequential (doc 03a §9,
carried by doc 20 §10). This is an anchor for phase sizing — **never a commitment and
never a plan.**

---

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| — | — | — | (none yet) | — |

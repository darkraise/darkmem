# G-C evidence run — the bench arm, against T2.108's measurement corpus

**Dispatch brief, 2026-08-13.** Adversarial gate probe. Your charter is to find the
reason G-C should **not** clear, not to clear it.

## The gap this run exists to close

G-C has two arms. The **production** arm (`run_promotion_metrics.py`, reading
`localhost:5433/darkmem` read-only) has been measured twice — T2.40 (2026-08-07) and
T2.111 (2026-08-08) — and both came back under-powered on every probe with the same
numbers: 0 eligible transitions, 0 corroborations, 0 in either audit arm. That is a
true measurement of an empty production journal.

The **bench** arm (`run_gc_evidence.py`) has been run only against the *retrieval*
corpus, which T2.40 proved structurally incapable of promoting: `benchlib/ingest.py`
never set `origin_key`, so all 62 facts folded into the reserved anonymous bucket
that counts once and fires no gate.

T2.108 then built `--corpus promotion` **specifically** to close that — 66 captures
carrying genuine repeated assertions across sessions, plus two shapes designed *not*
to promote (an echo; an under-sourced same-kind pair). Its completion note records
21 corroborations against the 20 decidability threshold, reproduced.

**No G-C verdict has ever been recorded from that corpus.** Search
`gate-ledger.md` for `--corpus promotion`: one incidental mention, no run. The
corpus was built, validated, reviewed and then never driven to a gate verdict.

## What to run

```
cd backend
DEEPSEEK_API_KEY=<from CLAUDE.md, "Live model endpoints"> \
BENCH_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench_gc \
  python scripts/benchlib/run_gc_evidence.py --corpus promotion
```

Notes on the environment, verified 2026-08-13: the dev Postgres is up on 5433
(`darkmem-postgres-1`); the Ollama embedder at `192.168.0.196:11434` answers 200;
`backend/scripts/benchlib/promotion/cache/` is **empty**, so this run makes ~66 live
DeepSeek extraction calls — expect `live_calls > 0` and say so, since the retrieval
arm's docstring expects 0 and a reader may carry that expectation over. Create the
bench database first if it does not exist; `assert_bench_db_allowed` guards the name
and conftest-style resets apply — never point this at `darkmem`.

Run `--no-capture-time-simulation` as a second pass. T2.108 disclosed one simulated
step (`fact_sources.created_at` moved back to the asserting memory's capture time,
because provenance-write time makes the ≥ 7-day gate unreachable on a re-lifted
corpus). The report must state which buckets rest on that simulation and what the
verdict is without it. If the verdict differs between the two passes, that
difference **is** the finding.

## The question you must answer before recording any verdict

**Can a bench-corpus run clear G-C at all, or can it only demonstrate operability?**
The ledger is genuinely ambiguous and this is not yours to settle silently:

- The G-C section calls the production journal "the primary target" and this driver
  "the bench-side arm".
- T2.108's completion note says a purpose-built corpus "was the only pre-cutover
  route to any verdict", since doc 17 §11 sequences the homelab cutover *after*
  these gates.

Those two sentences do not obviously agree. If you conclude the gate's definition
would have to change for a bench run to clear it, that is **Tier 3** under runbook
§5 — write up what you found, what the docs say, why they cannot both be true, and
**stop without recording a clearing verdict**. Recording "CLEARED" on a synthetic
corpus when the gate meant production usage is precisely the failure this corpus of
work exists to prevent.

## What the run must report regardless of verdict

- Every probe with its **denominators**, never a bare rate (rule 4: under-powered
  buckets are reported with their counts and can neither clear nor fail).
- The bars in force. `run_gc_evidence.py` now prints a bar block (T2.128, landed
  today): per bar the committed value, the effective value, and whether a `config`
  row was absent, honoured or clamped. Paste it into the ledger row — a bench
  database carries no rows, so it should read as the explicit no-rows sentence, and
  if it does not, that is a finding about the measured database.
- The R2 fold companion (`expired` events on facts carrying a prior in-window
  corroboration). A non-zero count caps what the audit's zero can claim.
- The R3 born-rung carve-out count beside the completeness probe, so the claim stays
  "100 % of counting-ladder transitions journaled, N born-rung rows excluded", never
  a bare 100 %.
- The two groups the corpus expects to **stay** at `candidate` (the echo and the
  under-sourced pair). If they promoted, the corpus or the ladder is wrong and that
  outranks every other number in the run.

## Do not

- Do not mint `backend/app/services/promotion_metrics_record.json`. That record
  lights the promoted badge and is the gate owner's deliberate act on a cleared run,
  never a side effect of measuring.
- Do not move a bar. `promotion_bars.py`'s six are committed ahead of measurement
  and the licence mechanism exists so a loosening cannot be a silent number edit.
- Do not touch the production database.

## Record

A dated report under `docs/eval/`, and a ledger row under `## G-C` in
`docs/planning/gate-ledger.md` carrying the measured numbers, the artifact path, the
verdict, and — if the Tier-3 question above bites — the escalation instead of a
verdict.

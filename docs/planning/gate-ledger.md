# Gate evidence ledger

**Every phase advance in darkmem is a measured number, not a judgement.** This file is
where those numbers live. A gate is cleared when its row here carries a real measurement,
its artifact path, and a verdict — not when someone believes the work is done.

## The rules

1. **State the bar before the run.** A bar written after seeing the number is not a bar.
   Every bar lives as a `config` row or a harness constant with a stated default.
2. **Accuracy never ships without its twin.** Any accuracy figure recorded here is
   accompanied by p95 latency and token cost. A row missing its twin is incomplete
   evidence, not a pass (doc 17 §2).
3. **A miss is recorded, not retried away.** If a number lands below its bar, write it
   down and leave the gate open. Never re-run until it passes; never widen a bar to fit a
   result. The gate working is the system working.
4. **Per-slice numbers are never collapsed.** A flattering aggregate hiding a collapsed
   slice is the dishonesty the whole harness exists to prevent.
5. **Every entry names its artifact.** A number with no reproducible artifact is an
   anecdote.

## Status

| Gate | Guards | Status | Cleared on | Evidence |
|---|---|---|---|---|
| G-A | Phase 0 → 1 | **open** | — | — |
| G-B | Phase 1 → 2 | **open** | — | — |
| G-C | L2 → deriver; Phase 2 exit | **open** | — | — |
| G-D | L2 → L3 | **open** | — | — |
| G-E | L3 → F7 | **open** | — | — |
| G-F | core → H1 | **open** | — | — |
| G-G | target → H2 | **closed** (entry conditions unmet) | — | — |

---

## G-A — Phase 0 → 1

**Owning task:** T0.17. **Bar lives in:** a harness constant (there is no hosted CI —
the gate is a scripted discipline, doc 17 §9).

Three probes, all of which must hold:

| Probe | Bar | Measured | Twin | Artifact | Verdict |
|---|---|---|---|---|---|
| Extraction F1 bench reproduces the recorded as-is baseline (entity name+type F1, relations F1) | Reproduce T0.05's recorded numbers | — | n/a (deterministic, zero model calls) | — | — |
| Retrieval eval runs with accuracy + p95 latency + token cost | Runs and reports all three columns | — | — | — | — |
| Baseline migration boots clean; boot-time reconciliation idempotent | Clean boot; second boot is a no-op | — | n/a | — | — |

**Recorded as-is baseline (T0.05)** — the reference every later phase compares against:

| Dimension | Gold P / R / F1 | Held-out P / R / F1 |
|---|---|---|
| Entity, name only | — | — |
| Entity, name + type | — | — |
| Relation, pair only | — | — |
| Relation, full triple | — | — |

**Stated G-B parity tolerance:** _(set in T0.05, before Phase 1 starts)_ — …

Run context: git sha —, model —, fingerprint —, date —.

---

## G-B — Phase 1 → 2

**Owning task:** T1.50. **Bar lives in:** a harness constant + `config`.

| Probe | Bar | Measured | Twin | Artifact | Verdict |
|---|---|---|---|---|---|
| Extraction F1 parity with the recorded baseline | Within the T0.05 tolerance | — | n/a | — | — |
| Retrieval eval vs full-context baseline | Reported with twin; no silent regression | — | p95 —, tokens — | — | — |
| Isolation probe: unlabelled cross-project or superseded rows, **every** channel | **Exactly 0** | — | n/a | — | — |

**Isolation probe detail** (T1.35) — a single leaked row fails the gate:

| Channel | Cross-project leaks | Superseded leaks | Verdict |
|---|---|---|---|
| Semantic | — | — | — |
| Keyword | — | — | — |
| Graph | — | — | — |
| `memory_reason` | — | — | — |
| Code search | — | — | — |

---

## G-C — L2 → deriver; Phase 2 exit

**Owning task:** T2.40. **Bar lives in:** `config` rows. **Metrics computed from the
`events` journal by SQL** — an unjournaled transition is an unmeasurable one.

| Probe | Bar | Measured | Artifact | Verdict |
|---|---|---|---|---|
| Promotion rate `(promoted / eligible)`, sliced by source-kind diversity | — | — | — | — |
| Promotion rate, sliced by which N fired | — | — | — | — |
| False-promotion audit (corroborated later disputed or human-rejected) | Under stated bar | — | — | — |
| Every ladder transition journaled | 100% | — | — | — |

**Consequence of a miss:** the code-deriver lane (T2.27–T2.28) stays closed. The deriver
mints facts born `corroborated`; shipping it over an unproven ladder would put unverified
assertions into the vault at the ladder's second rung.

---

## G-D — L2 → L3

**Owning task:** T2.41. **Bar lives in:** `config` + the gold set.

| Probe | Bar | Measured | Artifact | Verdict |
|---|---|---|---|---|
| `verification` judge precision on labelled entailment gold | — | — | — | — |
| `verification` judge recall on labelled entailment gold | — | — | — | — |

**Gold set:** built in T2.25, **before** the judge, so the judge cannot be tuned to its
own test. Material comes from running `article_synthesis` in a labelled non-shipping
mode against `darkmem_bench`, plus hand-authored claim/fact pairs — **not** from real
Phase-3 drafts, which do not exist until after this gate clears.

**Consequence of a miss:** E3 stays closed. Below the bar, no L3 article ships as grounded —
enforced in code (T3.03), not by policy.

---

## G-E — L3 → F7

**Owning task:** T3.22. **Bar lives in:** `config`.

Measured by T3.24's runner. The production read is the one sanctioned exception to
"nothing automated touches `darkmem`" — it is **read-only** and may never write.

| Probe | Bar | Measured | Artifact | Verdict |
|---|---|---|---|---|
| L3 shipped | Articles live in production | — | — | — |
| Per-article claim-support coverage **distribution** above the runtime threshold | — | — | — | — |

**A distribution, not a mean.** One well-covered article does not clear this gate; the
question is whether coverage holds across the corpus in production.

---

## G-F — core → H1

**Owning task:** TH1.10. **Bar lives in:** doc 17 + maintainer appetite.

| Probe | Bar | Measured | Artifact | Verdict |
|---|---|---|---|---|
| Retrieval eval stable | — | — | — | — |
| Promotion metrics stable | — | — | — | — |
| Faithfulness (span-support coverage) on block-span entailment gold | Defined in TH1.01 **before** build | — | — | — |
| Maintainer appetite | Explicitly stated | — | — | — |

---

## G-G — target → H2

**Owning epic:** EH2 (outline only). **Bar lives in:** the doc 03a annex corpus.

Entry conditions, all required before any task exists:

| Condition | Status |
|---|---|
| Python target shipped (Phases 0–3 complete, G-E cleared) | not met |
| Maintainer appetite explicitly stated | not stated |
| Harness ported first: byte-identical LLM-cache reuse | spike-proven, not ported |
| Harness ported first: exact F1-scorer parity (1e-12) | spike-proven, not ported |

**No parity claim may be made before the harness exists in the new stack.** Any F1 delta
must be attributable purely to a ported pass — never to model drift or metric skew.

---

## Standing conditional gates (inside phases, not between them)

These never "clear" once — they apply per activation, every time.

| Gate | Applies to | Rule |
|---|---|---|
| Ranking-arm activation | `w_importance`, `w_heat`, `w_recency`, `w_ppr`, dual-level, community injection | A retrieval-eval delta that is positive **with its latency/cost twin**. An arm that cannot show its number stays at weight 0 — and that outcome is recorded here as a result, not a failure. |
| `triple_embeddings` writer | T2.33 | Ships only when the measured `pg_trgm` contradiction-shortlist miss rate exceeds its stated bar. Groups facts for counting only — never merges rows, never rewrites `triple_key`. |
| Reranker on | `reranker_enabled` | Flips on a measured win **including p95 cost**. Wired and dormant until then. |
| Community injection | `community_injection_enabled` | Measured on answer-quality/groundedness, **not MRR** — it augments context, it is not a ranking signal (doc 17 §2). |

### Arm activation log

| Date | Arm | Slice deltas | p95 latency | Token cost | Decision | Artifact |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

# EH1 — H1: Documents / PKM (horizon lane)

**Goal:** Ship the documents/PKM lane — the block pipeline, block retrieval, the
faithfulness gate, proposition lifting, and the analysis surface.

**Advance gate:** **G-F** — the core eval gate (retrieval eval and promotion metrics
stable) plus maintainer appetite. The faithfulness metric (span-support coverage) must be
**defined before build starts** and **clear its bar before ship**.

**Epic branch:** `feat/eh1-documents-pkm`

**Contract:** [`../agent-runbook.md`](../agent-runbook.md). Amendments log at the bottom.

---

## The firewall — read this before starting

**The firewall runs both directions and it is the reason this lane can be deferred for
free:**

1. **Article synthesis never reads a block.** The vault does not depend on this unshipped
   horizon. If an E3 article could cite a block, deferring H1 would block Phase 3 — and
   the whole point of a horizon lane is that it cannot.
2. **The PKM surface ships only after the core's eval gate clears.** No part of Phases 0–4
   may acquire a dependency on anything in this file.

A task here that breaches the firewall in either direction is a **Tier-3 amendment** — stop
and escalate (doc 16 §1, doc 01 §3.4).

---

## Lane A — the block pipeline

#### TH1.01 — Faithfulness metric definition (before any build)

`Model: Fable 5` · `Depends: G-F appetite` · `Doc: 16 §4, 17 §6` · `Tag: horizon` · `Gate: G-F`

**What.** Define span-support coverage — entailed claims / total claims — **before build
starts**. Doc 20 §4 makes this ordering explicit, and it is the one sequencing rule in
this lane: a metric defined after the thing it measures gets defined to fit.

**Done when:** the metric, its gold-set shape, and its bar are written down and reviewed;
the bar lives as a `config` row; nothing in Lane A has been built yet.
**Verify.** Definition committed and reviewed against doc 17 §6 before TH1.02 starts.

#### TH1.02 — `documents` / `blocks` first writer

`Model: Opus 5` · `Depends: TH1.01, T0.13` · `Doc: 16 §2–§3` · `Tag: horizon` · `Gate: G-F`

**What.** First writer to the tables landed inert in T0.13. Document identity is the
partial `UNIQUE (project, uri)` with `content_hash` as the re-ingest change gate — an
unchanged hash short-circuits the whole pipeline.

**Done when:** re-ingesting an unchanged document does zero work, proven by test; the
partial unique constraint holds; the tables lose their inert label.
**Verify.** `cd backend && python -m pytest tests/test_documents.py -q`

#### TH1.03 — Parser stack (PDF, markdown, notes)

`Model: Sonnet 5` · `Depends: TH1.02` · `Doc: 16 §3` · `Tag: horizon` · `Gate: G-F`

**What.** The ADR is decided, not open: `pdfplumber` for PDF, `markdown-it-py`/`mistune`
for markdown, native segmentation for notes. **`PyMuPDF` is rejected (AGPL)** and
ML-layout parsers are rejected (they violate doc 03's no-heavy-ML floor). Do not re-open
this in the implementation.

**Done when:** all three formats parse to a block tree; a parse failure is per-document,
never fatal to a batch; no AGPL or heavy-ML dependency is added.
**Verify.** `cd backend && python -m pytest tests/test_document_parsers.py -q`

#### TH1.04 — Block tree + strip-before-rewrite by `document_id`

`Model: Opus 5` · `Depends: TH1.03` · `Doc: 16 §2–§3` · `Tag: horizon` · `Gate: G-F`

**What.** A Tier-B pipeline variant — **not** the five-phase memory pipeline. Same
idempotence discipline: strip this `document_id`'s prior blocks before writing the new set.

**Done when:** re-ingest is idempotent; the block tree preserves document structure and
char spans; this path never enters `process_batch`.
**Verify.** `cd backend && python -m pytest tests/test_block_pipeline.py -q`

#### TH1.05 — `block_embeddings__<slug>` writer

`Model: Sonnet 5` · `Depends: TH1.04, T0.13` · `Doc: 16 §3` · `Tag: horizon` · `Gate: G-F`

**What.** First writer to the block partition template landed inert in T0.13.

**Done when:** register-before-insert honoured; naming goes through
`child_table(parent, fingerprint)` only; no cross-fingerprint comparison (invariant 2).
**Verify.** `cd backend && python -m pytest tests/test_block_embeddings.py -q`

---

## Lane B — block retrieval

#### TH1.06 — Semantic-only block channel

`Model: Opus 5` · `Depends: TH1.05` · `Doc: 16 §4, 07 §2` · `Tag: horizon` · `Gate: G-F`

**What.** A separate channel over `block_embeddings__<slug>` — **never fused** into the
four-layer memory/vault composition. The document-RAG twin of code search, which is
semantic-only for the same reason.

**Done when:** the channel exists and is queryable independently; no fusion path can
include it, proven by test; scope predicates are pushed into SQL exactly as T1.29 requires.
**Verify.** `cd backend && python -m pytest tests/test_block_retrieval.py -q`

#### TH1.07 — Trace addendum: `block` id-kind, `document` layer

`Model: Sonnet 5` · `Depends: TH1.06, T1.33` · `Doc: 16 §4` · `Tag: horizon` · `Gate: G-F`

**What.** Additive to the core trace schema — **never assumed by a consumer until H1
ships**. A core consumer that breaks on an unknown id-kind is a core defect to fix, not a
reason to delay the addendum.

**Done when:** the addendum is additive; core trace consumers are unaffected; the new
kind renders in the UI trace without a special case.
**Verify.** `cd backend && python -m pytest tests/test_trace_block_addendum.py -q`

---

## Lane C — the faithfulness gate

#### TH1.08 — Grounded Q&A flow

`Model: Opus 5` · `Depends: TH1.06` · `Doc: 16 §4` · `Tag: horizon` · `Gate: G-F`

**What.** Interactive `reasoning`-purpose flow: retrieve blocks, generate a per-sentence
cited answer.

**Done when:** every sentence carries a block citation with its char span; retrieval and
generation are separately observable; the flow is Tier-A interactive and bounded.
**Verify.** `cd backend && python -m pytest tests/test_grounded_qa.py -q`

#### TH1.09 — Span-support faithfulness check before serving

`Model: Opus 5` · `Depends: TH1.08, TH1.01, T2.26` · `Doc: 16 §4` · `Tag: horizon` · `Gate: G-F`

**What.** A `verification`-purpose check on span-support coverage runs **before serving**.
A below-threshold answer is labelled could-not-fully-ground or withheld — **never served
as grounded** (invariant 14).

**Done when:**
- [ ] The check runs pre-serve, not post-hoc
- [ ] Below threshold, the answer is labelled or withheld — proven by test
- [ ] The judge is the same one T2.26 qualified — one judge, three consumers
- [ ] Threshold is a `config` row

**Verify.** `cd backend && python -m pytest tests/test_faithfulness_gate.py -q`

#### TH1.10 — Faithfulness ship gate (G-F evidence)

`Model: Fable 5` · `Depends: TH1.09` · `Doc: 20 §4, 17 §6` · `Tag: horizon` · `Gate: G-F`

**What.** Double duty: TH1.09 is the per-answer runtime gate; this is the **ship** gate.
The metric defined in TH1.01 must clear its bar on a labelled gold set before H1 ships.

**Done when:** measured on block-span entailment gold; the bar was set in TH1.01, before
the build; verdict in `gate-ledger.md`; a miss leaves H1 unshipped.
**Verify.** `cd backend && python scripts/benchlib/run_faithfulness_gate.py`

---

## Lane D — proposition lifting (the vault bridge)

#### TH1.11 — On-demand Tier-C lift

`Model: Opus 5` · `Depends: TH1.04` · `Doc: 16 §5` · `Tag: horizon` · `Gate: G-F`

**What.** **On-demand only — never automatic on ingest.** Mints proposition memory rows
carrying `(document_id, block_id, char_span)` provenance, which then flow through the
ordinary F2 pipeline.

**Done when:** no ingest path triggers lifting, proven by test; provenance is on the
derived row; lifted rows are ordinary memories from the pipeline's perspective.
**Verify.** `cd backend && python -m pytest tests/test_proposition_lift.py -q`

#### TH1.12 — Block-sourced facts, one document = one origin

`Model: Opus 5` · `Depends: TH1.11, T2.02` · `Doc: 16 §5, 08 §4.1` · `Tag: horizon` · `Gate: G-F`

**What.** Corroborated relations lift to an L2 fact via
`fact_sources(kind='block', origin_key=document_id)`. **One document is one origin
regardless of block count** — matching the one-repo-one-origin rule. A 400-block document
must not manufacture 400 origins.

**Done when:** origin count per document is exactly one, proven by test; the `block` source
kind is added to the closed set; withdrawal of a document demotes its derived facts.
**Verify.** `cd backend && python -m pytest tests/test_block_fact_sources.py -q`

#### TH1.13 — Idempotent lifting, keyed on `document_id`

`Model: Sonnet 5` · `Depends: TH1.12` · `Doc: 16 §5` · `Tag: horizon` · `Gate: G-F`

**What.** Strip-before-rewrite on re-ingest, self-healing through the ordinary
source-withdrawal sweep.

**Done when:** re-lifting is idempotent; a removed document self-heals its derived rows
through the existing sweep, not a bespoke one.
**Verify.** `cd backend && python -m pytest tests/test_lift_idempotence.py -q`

---

## Lane E — the analysis surface

#### TH1.14 — Single-document summary (unbadged)

`Model: Sonnet 5` · `Depends: TH1.04` · `Doc: 16 §6` · `Tag: horizon` · `Gate: G-F`

**What.** Reuses doc 11's `summarization` purpose as an **unbadged report, never a
verified claim**. A summary is not a fact.

**Done when:** no verification badge renders on a summary; summaries are excluded from the
fact ladder; regeneration is explicit, not automatic.
**Verify.** `cd backend && python -m pytest tests/test_document_summary.py -q`

#### TH1.15 — Emergent cross-document connections

`Model: Sonnet 5` · `Depends: TH1.12` · `Doc: 16 §6` · `Tag: horizon` · `Gate: G-F`

**What.** Connections are **emergent from the shared graph after lifting** — entity
overlap, topic communities (doc 06), associative relations (doc 08). **No new analysis
engine.** A verified multi-source write-up is an article (doc 09), never an analysis
feature reading blocks.

**Done when:** connections derive from existing graph machinery only; no new table and no
new job family; multi-document synthesis write-ups are explicitly out of scope.
**Verify.** `cd backend && python -m pytest tests/test_document_connections.py -q`

#### TH1.16 — Documents UI, horizon-labelled

`Model: Sonnet 5` · `Depends: TH1.09, TH1.14` · `Doc: 16 §6, 13` · `Tag: horizon` · `Gate: G-F`

**What.** The lane's one UI surface: grounded Q&A over blocks, single-document summary,
emergent connections. Doc 13's inventory defines no documents screen today — this lands
with the lane, labelled horizon.

**Done when:** Q&A shows per-sentence citations with spans; a withheld answer says so
plainly; summaries render visibly unbadged; the surface is labelled as horizon in the IA.
**Verify.** `cd frontend && npm test -- documents && npm run test:e2e -- documents`

---

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| — | — | — | (none yet) | — |

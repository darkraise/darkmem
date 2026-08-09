# E3 — Phase 3: Synthesis & reach (L3)

**Goal:** Ship synthesis and reach — subject articles behind the groundedness gate, F7
auto-research as a committed fast-follow, and distribution (inject v1, onboarding, SDKs,
browser capture, session checkpoints).

**Entry gate:** **G-D** cleared (T2.41) — **for the grounded-shipping path only, amended
2026-08-06.** G-D certifies that the verification judge is qualified, so what it may
lawfully hold shut is what *asserts groundedness to a reader*: **T3.02** (productive
article runs), **T3.03** (the claim-level entailment pass) and **T3.10** (truth-first
content fill). Every other task in this epic — scorers, writers, adapters, SDK and
extension scaffolds, checkpoints, UI — asserts nothing about groundedness and may be
built and merged with G-D open. They land **inert** where they touch a gated path.

Holding the whole epic shut on G-D was phase coupling, not artifact coupling: it queued a
browser-extension scaffold behind a groundedness evidence run. The gate keeps its teeth
exactly where its stated consequence lives — *"below the bar, no L3 article ships as
grounded"* — and loses them where it never had a claim.

**Done when:** **G-E** cleared — L3 shipped with per-article coverage holding above the
runtime threshold in production — **and** F7 shipped. Phase 3 → 4 is appetite, not a
metric. **G-E is unchanged**: shipping still requires the evidence.

**Epic branch:** `feat/e3-synthesis-and-reach`

**Contract:** [`../agent-runbook.md`](../agent-runbook.md). Amendments log at the bottom.

**F7 is sequenced at the tail on purpose.** It is cheap *because* it follows L3 — pulled
earlier it becomes expensive and re-opens the layer argument (doc 20 §8, fast-follow
creep). Do not start Lane B before Lane A ships.

---

## Lane A — subject articles (L3)

#### T3.01 — Subject eligibility gate + priority scoring

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: —` · `Doc: 09 §4.1–§4.2` · `Tag: target-new` · `Gate: G-D (entry)`

**Unblocked for implementation 2026-08-06 (controller).** Eligibility and
priority *scoring* decides which subjects are worth synthesising; it does not
ship a grounded claim, which is what G-D certifies. The scorer can be built and
tested against the corpus it already has. **The gate moves downstream to T3.02**,
which is where a synthesised article first reaches a reader — that is the
"below the bar, no L3 article ships as grounded" consequence, and it is
unchanged.

**What.** A subject must clear a **hard verified-fact eligibility gate** before it is a
synthesis candidate; eligible subjects are then ordered by a weighted priority score under
a per-run synthesis budget. Eligibility is a gate, not a weight — an under-sourced subject
is never synthesised because it happened to rank high.

**Done when:**
- [ ] Eligibility is boolean and checked before scoring, proven by test
- [ ] Priority weights and the per-run budget are `config` rows
- [ ] One live grounded article per `(project, subject_key)` is enforced by constraint

**Verify.** `cd backend && python -m pytest tests/test_article_eligibility.py -q`

#### T3.02 — `article_synthesis` productive runs

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T3.01, T2.14, T2.95` · `Doc: 09 §4` · `Tag: target-new` · `Gate: G-D`

**Buildable now; the grounded label waits (amended 2026-08-06 with the M1
split).** The title says *productive* runs, and this is where a synthesised
article first reaches a reader — so "below the bar, no L3 article ships as
grounded" binds absolutely. It binds on the **word grounded**, not on synthesis.
With `T2.95` in place articles may be synthesised, stored and read; what no path
may do is label one grounded without G-D's qualification record. Doc 09 §4.3
already withholds never-grounded articles, so the shipped behaviour before M1 is
the one the doc already describes.

**Three seams inherited by name from T2.95's review round (2026-08-06).** All
three are unreachable today because nothing in production writes articles, and
each becomes live the moment this task does:

1. **The review queue's articles arm serves the raw article status.**
   `list_open_articles` emits `"status": row["status"]` without going through
   `fact_badge.row_labels`, and the `knowledge_articles` CHECK admits
   `'corroborated'`. T2.95's gate keys on `id_kind`, which cannot protect a path
   that never asks it, and **both enforcement scans are blind to the `status`
   spelling** — they quantify over `verification_status`. Route it through the
   producer here, and widen the scan to the spelling.
2. **Opening the article gate is the judge's door, not `claim_gates`.** T2.95
   deliberately did not touch `verification_judge.py`: two modules deciding
   whether the judge is qualified is the drift its single-door scan exists to
   prevent. The seam is `served_status`'s `gate=` parameter, which `row_labels`
   does not yet forward. Today articles route to an unconditionally-closed
   groundedness gate — correct and inert; making it *open* on G-D's record is
   this task's work.
3. **A minted fact record must not light an article.** T2.95's round 1 made
   that measured rather than inferred; keep the test that proves it when the
   article path becomes reachable.

**What.** Activates the job registered inert in T2.14. Synthesises **only** from
non-disputed corroborated/confirmed facts — a disputed fact never reaches a draft.

**Done when:**
- [ ] Disputed and candidate facts are excluded at the query, not filtered from the draft
- [ ] Runs Tier-C under the umbrella, within the T3.01 budget
- [ ] Every run journals its inputs so a bad article is traceable to its fact set

**Verify.** `cd backend && python -m pytest tests/test_article_synthesis.py -q`

#### T3.03 — Claim-level entailment pass + coverage routing

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T3.02, T2.26, T2.95` · `Doc: 09 §4.3` · `Tag: target-new` · `Gate: G-E`

**Buildable now (amended 2026-08-06 with the M1 split).** This pass spends the
verification judge whose qualification G-D certifies, and building it against an
unqualified judge is already safe by construction: `judge()` refuses
unconditionally without a record, scan-enforced. So the pass, its coverage
routing and its tests can all land; what they cannot do is produce a served
grounded label, which is `T2.95`'s gate. Its routing decisions become
*meaningful* when the judge qualifies — that is an activation, not a build.

**What.** Every sentence must cite a fact, verified by the `verification` judge. **Coverage
below threshold routes to review — it never ships as corroborated.** This is where the
under-claiming rule meets generated prose.

**Done when:**
- [ ] Uncited sentences are impossible in a shipped article
- [ ] Below-threshold drafts land in the review queue, labelled, not published
- [ ] The threshold is a `config` row and the per-article coverage is recorded (this is
      the G-E signal)

**Verify.** `cd backend && python -m pytest tests/test_claim_entailment.py -q`

#### T3.04 — `article_citations` — the one hard FK

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T3.03` · `Doc: 09 §4.3` · `Tag: target-new` · `Gate: G-E`

**What.** The single hard FK to `knowledge_triples`, safe only because facts are
invalidate-not-delete.

**Done when:** the FK exists and is enforced; an invalidated fact leaves the citation
intact and the article marked stale; a hard fact delete is impossible.
**Verify.** `cd backend && python -m pytest tests/test_article_citations.py -q`

#### T3.05 — Staleness gate + debounced re-synthesis

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T3.04` · `Doc: 09 §4.4` · `Tag: target-new` · `Gate: G-E`

**What.** Staleness is a hash of the **verified** fact set only — a churning candidate
does not trigger re-synthesis. Re-synthesis is debounced, strip-before-rewrite, and
supersedes the prior article.

**Done when:**
- [ ] The hash covers verified facts only, proven by a test that churns candidates
- [ ] Debounce window is a `config` row
- [ ] Re-synthesis supersedes rather than mutating; lineage is preserved

**Verify.** `cd backend && python -m pytest tests/test_article_staleness.py -q`

#### T3.06 — Articles tab

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T3.04` · `Doc: 13 §5.2` · `Tag: target-new` · `Gate: G-E`

**What.** Grounded prose with inline claim citations, the claim-support-coverage readout,
and the stale label.

**Done when:** every sentence's citation is reachable in one click; the coverage number is
shown in **both** Simple and Advanced (it is an honesty signal, not technical detail);
stale articles are labelled, not withheld.
**Verify.** `cd frontend && npm test -- articles && npm run test:e2e -- knowledge`

---

## Lane B — F7 auto-research (tail of Phase 3)

**Entry condition: Lane A shipped and G-E holding.**

#### T3.07 — Research-agent loop through the ordinary capture door

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T3.06, T1.12` · `Doc: 09 §6` · `Tag: target-new` · `Gate: G-E`

**What.** A thin orchestration over already-shipped capture, consolidation, and synthesis.
Evidence is filed through the **ordinary capture front door** — no privileged path, no
second pipeline. That is the entire reason F7 is cheap here.

**Done when:**
- [ ] No new ingestion path is added
- [ ] The loop is Tier-C and bounded by a `config` budget
- [ ] A failed research run leaves no partial state

**Verify.** `cd backend && python -m pytest tests/test_auto_research.py -q`

#### T3.08 — Distinct-origin stamping for researched sources

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T3.07, T1.11` · `Doc: 09 §6` · `Tag: target-new` · `Gate: G-E`

**What.** Each genuinely independent source gets a distinct `origin_key`. **The same
source fetched twice, or an unknown identity, merges to ONE origin** — corroboration is
never manufactured by a crawler visiting the same page twice.

**Done when:**
- [ ] Refetching one URL does not increase the origin count, proven by test
- [ ] Two independent sources asserting the same fact do promote it
- [ ] Unknown identity collapses per the T1.11 rule

**Verify.** `cd backend && python -m pytest tests/test_research_origins.py -q`

---

## Lane C — inject v1 (F10)

#### T3.09 — Managed-block writer, client-side pull-then-write

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: —` · `Doc: 15 §3.1–§3.2` · `Tag: target-new` · `Gate: G-E`

**Unblocked for implementation 2026-08-06 (controller).** The evidence run this
task used to depend on certifies something this task does not assert, so the
dependency was phase coupling rather than artifact coupling. Build the
mechanism now; it lands **inert** and its productive path stays gated exactly
as before. This is the repo's standing pattern — T0.13's inert partitions,
T2.08's placeholder jobs, T2.32/T2.50's build-versus-judge split, invariant 23.

**What.** The client pulls the F3 fused, labelled selection and rewrites a
marker-bounded managed block in the tool's native context file. **The server never writes
the client's filesystem** — that boundary is the whole trust posture of this feature.

**Done when:**
- [ ] Only content between the markers is ever rewritten; user text outside survives
- [ ] A corrupted or missing marker pair fails safe (no write) rather than guessing
- [ ] No server-side filesystem write exists anywhere in the path

**Verify.** `cd backend && python -m pytest tests/test_inject_block.py -q`

#### T3.10 — Truth-first content fill under a token budget

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T3.09, T2.43, T3.23` · `Doc: 15 §3.4` · `Tag: target-new` · `Gate: G-E`

**What.** Fill order is L2 facts, then L3 articles, then L0 memory summaries, under a
`config` token budget. Every item carries its layer, verification, and badge labels — an
injected claim without its label is the silent-authority failure invariant 14 forbids.

**Done when:**
- [ ] Fill order enforced and tested
- [ ] Budget respected; truncation drops the lowest tier, never mid-item
- [ ] Every injected item carries its labels verbatim

**Verify.** `cd backend && python -m pytest tests/test_inject_fill.py -q`

#### T3.11 — Per-tool adapters (Claude Code, Cursor, Codex, Cline)

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T3.09` · `Doc: 15 §3.3` · `Tag: target-new` · `Gate: G-E`

**What.** A managed file block per target tool: `CLAUDE.md`, Cursor's rules, `AGENTS.md`,
Cline. Session-start refresh cadence; `watch` mode is deferred to Phase 4 (T4.06).

**Done when:** each adapter writes the right file with the right marker syntax; an unknown
tool is refused with a message, not a best guess; refresh happens at session start only.
**Verify.** `cd backend && python -m pytest tests/test_inject_adapters.py -q`

#### T3.12 — Inject records journaled as events

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T3.11, T1.07` · `Doc: 13 §6.5` · `Tag: target-new` · `Gate: G-E`

**What.** Every injection journals what was pushed, to which target, under which budget —
the human can always see what the agent was told.

**Done when:** each inject writes an event carrying the item ids and the budget used;
records surface in the timeline and calendar.
**Verify.** `cd backend && python -m pytest tests/test_inject_events.py -q`

---

## Lane D — onboarding, SDKs, browser capture

#### T3.13 — `darkmem connect <tool>`

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T3.11` · `Doc: 15 §5` · `Tag: target-new` · `Gate: G-E`

**What.** Writes the tool's MCP config from a maintained adapter registry and verifies via
the stateless `initialize → tools/list` handshake.

**Done when:**
- [ ] Handshake verification runs and reports the concrete failure
- [ ] A foreign-Host `421` is reported as **"extend `MCP_ALLOWED_HOSTS`"** — never worked
      around, never by disabling the protection
- [ ] Re-running is idempotent and does not duplicate config entries

*terminal-by-design — nothing depends on this; it is a backstop, an activation, or a
leaf surface, not infrastructure another task consumes.*

**Verify.** `cd backend && python -m pytest tests/test_connect_cli.py -q`

#### T3.14 — Minimal TypeScript + Python SDKs

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T3.25` · `Doc: 15 §6` · `Tag: target-new` · `Gate: G-E`

**What.** Three verbs only — `capture`, `search`, `declareContext` — over the doc 12
contract. **Ratify, review, and vault-admin stay out**: the SDK is for agents, and
ratification is a human single-door act.

**Done when:** three verbs each in both languages, over the T3.25 scaffold; a ratify
call is **not expressible** — asserted by a test that greps the generated surface, not
by review.
*terminal-by-design — nothing depends on this; it is a backstop, an activation, or a
leaf surface, not infrastructure another task consumes.*

**Verify.** `cd sdks/ts && npm test` and `cd sdks/python && python -m pytest -q`

#### T3.15 — Browser capture extension

`Model: Sonnet 5` · `Effort: high` · `Size: L` · `Depends: T3.26` · `Doc: 15 §4` · `Tag: target-new` · `Gate: G-E`

**What.** Packages a **human-selected** AI-chat exchange and posts it through the ordinary
capture front door. v1 is human-triggered only — never auto-scraped (that is T4.07,
demand-gated and opt-in).

**Done when:**
- [ ] Adapters for ChatGPT / Claude.ai / Gemini web plus a plain-selection fallback
- [ ] Deduped by content fingerprint and a per-install `origin_key`
- [ ] No automatic capture path exists in v1 — asserted by a test over the built
      bundle, not by review ("proven by review" is not objectively checkable)
- [ ] Uses the ordinary REST/MCP door into `memory_buffer` — no new pipeline

**Verify.** `cd extension && npm test` + `cd backend && python -m pytest tests/test_browser_capture.py -q`

---

## Lane E — session checkpoints and resume

**The store half is Phase-1-capable** (it needs only `origin_key`) and may be pulled
earlier if the resume workflow is wanted before Lane C lands. Recorded here as committed
Phase 3.

#### T3.16 — `session_checkpoints` table + REST/MCP surface

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.11` · `Doc: spec §Feature-2, 04, 12` · `Tag: target-new` · `Gate: G-E`

**What.** Keyed on `origin_key` (the agent-run identity). `POST`/`GET /checkpoints` plus
MCP `checkpoint_save` / `checkpoint_latest`, holding a compact `summary` and structured
`next_steps`.

**Done when:** both doors expose it (invariant 17); latest-per-origin is one indexed
query; payload size is bounded.
*gate-exempt: the store half needs only `origin_key`, so doc 20 records it as
Phase-1-capable and it may be pulled ahead of G-D.*

**Verify.** `cd backend && python -m pytest tests/test_checkpoints.py -q`

#### T3.17 — Resume as a specialised inject

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T3.16, T3.10` · `Doc: 15 §3.2` · `Tag: target-new` · `Gate: G-E`

**What.** At session start the latest checkpoint writes into the managed block under the
token budget, so a fresh session loads a budgeted digest instead of reloading full
context (invariant 17).

**Done when:** resume reuses the T3.10 budget path, not a parallel one; a missing
checkpoint degrades to the ordinary inject; `checkpoint_saved` / `resumed` journal.
**Verify.** `cd backend && python -m pytest tests/test_resume_inject.py -q`

#### T3.18 — Checkpoints are operational, not vault knowledge

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T3.16` · `Doc: 13 §6` · `Tag: target-new` · `Gate: G-E`

**What.** A checkpoint carries **no verification badge** — it is operational state, not a
claim about the world. Conflating the two would put unverified agent notes into the vault.

**Done when:** checkpoints cannot enter the fact ladder; no badge renders on them; they
are excluded from retrieval's vault channels.
*terminal-by-design — nothing depends on this; it is a backstop, an activation, or a
leaf surface, not infrastructure another task consumes.*

*gate-exempt: the store half needs only `origin_key`, so doc 20 records it as
Phase-1-capable and it may be pulled ahead of G-D.*

**Verify.** `cd backend && python -m pytest tests/test_checkpoint_isolation.py -q`

---

## Lane F — distribution UI (F9)

#### T3.19 — Settings → Distribution tab

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T3.11` · `Doc: 13 §6.5` · `Tag: target-new` · `Gate: G-E`

**What.** Per-target managed-block config, inject content policy, and the curb control.

**Done when:** each target's block path and status shown; content policy editable; a
single control stops all injection immediately; Simple/Advanced honoured.
**Verify.** `cd frontend && npm test -- distribution`

#### T3.20 — Inject records in timeline and calendar

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T3.12` · `Doc: 13 §6.5` · `Tag: target-new` · `Gate: G-E`

**What.** Injections appear as journaled events — the human can see and curb push, never
a silent context swap.

**Done when:** injections render in both surfaces with their item counts and budget;
clicking one shows exactly what was pushed; Simple/Advanced honoured.
**Verify.** `cd frontend && npm test -- activity`

#### T3.21 — Session checkpoints / resume view

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T3.17` · `Doc: 13 §6` · `Tag: target-new` · `Gate: G-E`

**What.** Per-run digest, next-steps, and copy-resume in the Activity shell.

**Done when:** latest checkpoint per run is one click away; copy-resume yields the exact
injected text; `checkpoint_saved` / `resumed` events visible; Simple/Advanced honoured.
**Verify.** `cd frontend && npm test -- checkpoints`

---

## Lane G — gate

#### T3.23 — Articles retrieval channel + `article_embeddings` writer

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T3.02, T2.43, T0.13` · `Doc: 07 §2, 04 §5.3` · `Tag: target-new` · `Gate: G-E`

**What.** Doc 07 §2 makes the articles channel target-new and semantic over
`article_embeddings__<slug>` — the channel without which T3.10's truth-first inject fill
has no L3 tier to read, and G-E's "L3 shipped" is unverifiable.

**Done when:**
- [ ] The template loses its inert label; the schema inventory names this as its writer
      (it is the last of the four **mainline** templates — `block_embeddings` waits for
      the EH1 horizon, and `triple_embeddings` may never ship at all)
- [ ] Semantic channel with scope pushdown from the first commit
- [ ] Composed under doc 07 §5's rules (T2.43), never fused ad hoc
- [ ] A stale article is returned labelled stale, not withheld

**Verify.** `cd backend && python -m pytest tests/test_articles_channel.py -q`

#### T3.25 — SDK scaffold and generator

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.42d` · `Doc: 15 §6` · `Tag: target-new` · `Gate: G-E`

**Unblocked for implementation 2026-08-06 (controller).** The evidence run this
task used to depend on certifies something this task does not assert, so the
dependency was phase coupling rather than artifact coupling. Build the
mechanism now; it lands **inert** and its productive path stays gated exactly
as before. This is the repo's standing pattern — T0.13's inert partitions,
T2.08's placeholder jobs, T2.32/T2.50's build-versus-judge split, invariant 23.

**What.** Split out of T3.14, which bundled codegen infrastructure for two languages into
one task. This one names the generator and lands the layout: `sdks/ts/`, `sdks/python/`,
generated from the doc-12 contract.

**Done when:** the generator is named and runs from a documented command; both packages
build; regeneration is idempotent.
**Verify.** `cd sdks && make generate && git diff --exit-code`

#### T3.26 — Browser-extension scaffold

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T1.12` · `Doc: 15 §4` · `Tag: target-new` · `Gate: G-E`

**Unblocked for implementation 2026-08-06 (controller).** The evidence run this
task used to depend on certifies something this task does not assert, so the
dependency was phase coupling rather than artifact coupling. Build the
mechanism now; it lands **inert** and its productive path stays gated exactly
as before. This is the repo's standing pattern — T0.13's inert partitions,
T2.08's placeholder jobs, T2.32/T2.50's build-versus-judge split, invariant 23.

**What.** Split out of T3.15. The extension shell under `extension/` with the plain-selection
fallback and the per-install `origin_key`, before any site adapter exists.

**Done when:** the shell posts a human-selected block through the ordinary capture door;
per-install `origin_key` is stable across restarts; no site adapter is required to work.
**Verify.** `cd extension && npm test`

---

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| 2026-08-06 | T3.01, T3.02, T3.03, T3.09, T3.25, T3.26 | 2 | **A gate blocks what it certifies, not what merely precedes it.** Implementation lands **inert**; only the productive or serving path waits for evidence. This is the repo's own standing pattern, applied more consistently — T0.13's inert partitions, T2.08's `PlaceholderJobRunner` family, T2.32/T2.50's build-versus-judge split, and invariant 23's scaffolding-not-substrate. Dependency edges re-pointed off the evidence runs accordingly | Controller decision: the plan had implementation work queued behind **evaluation artifacts it does not depend on** — an SDK scaffold and a browser-extension scaffold waited on a groundedness evidence run, and a document parser waited on a faithfulness metric. That is phase coupling, not artifact coupling, and it stalls build work on datasets that do not exist yet. Evaluation is deferred to an independent measurement phase after the implementation is complete, where it can be run against the whole system rather than against fixtures. **What was deliberately left gated**: T2.28 (mints facts born `corroborated` — the exact harm G-C names), T3.02 (productive article runs — where a grounded claim first reaches a reader), T3.03 (the groundedness consumer). Freeing those would put unverified assertions in front of users, which is a different thing from unblocking a scaffold. |
| 2026-08-10 | T3.14 (correcting T3.25) | 1 | **The generator's verb bindings were wrong twice and its guard could not see either.** Round 1: the guard widened from route existence to the request-body **fields** each verb sends, after both emitted clients were found posting an `applies_when` key no request schema in the contract has — silently dropped by every door. `declareContext` was re-pointed off `POST /memories/reason` (a route it has no relationship with) onto the `X-Darkmem-Context` header, and `search` off `POST /memories/search` onto `POST /knowledge/search`. Round 2, after the Fable review of 2026-08-10: **`search` re-pointed again, to `POST /memories/search/paginated`**, because the composed read serves neither rank of doc 12 §5's context chain — measured live, the header reached nothing on either bound door, so `declareContext` declared into the void. `capture` lost its `context` argument for the same reason. The guard gained a consumption arm (a context-carrying verb must bind a door whose schema declares the rank-1 `context` field, and some verb must carry the header), the emitted bodies are now rendered from the declared field tuple so the two cannot diverge, and `backend/tests/test_sdk_contract_conformance.py` drives the real app to prove the declaration is resolved | Round 1's argument weighed doc 15 §6's prose ("the F3 read", "labelled results with their trace", a `fused?` argument) and did not record that the section's own mermaid arrow says `POST .../search · memory_search` — the memories twin — which is the counter-evidence and turned out to be right. Doc 01 F3 is the memory retrieval flow, and only the memories door carries the rank-1 `context` field, resolves the header and returns the trace envelope. The cost is that `fused` is not expressible in the SDK; recorded rather than faked. **Doc 15 §6 has been amended in place** with a dated note correcting three diagram labels, which round 1 failed to do — an amendment whose document still says the opposite regenerates the old answer. The general lesson, worth more than the binding: a schema-shaped guard proves a door *accepts* a value, never that anything *reads* it, and for a generated artifact one test must drive the artifact rather than the generator |

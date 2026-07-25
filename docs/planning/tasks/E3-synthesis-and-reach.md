# E3 — Phase 3: Synthesis & reach (L3)

**Goal:** Ship synthesis and reach — subject articles behind the groundedness gate, F7
auto-research as a committed fast-follow, and distribution (inject v1, onboarding, SDKs,
browser capture, session checkpoints).

**Entry gate:** **G-D** cleared (T2.41). **Done when:** **G-E** cleared — L3 shipped with
per-article coverage holding above the runtime threshold in production — **and** F7
shipped. Phase 3 → 4 is appetite, not a metric.

**Epic branch:** `feat/e3-synthesis-and-reach`

**Contract:** [`../agent-runbook.md`](../agent-runbook.md). Amendments log at the bottom.

**F7 is sequenced at the tail on purpose.** It is cheap *because* it follows L3 — pulled
earlier it becomes expensive and re-opens the layer argument (doc 20 §8, fast-follow
creep). Do not start Lane B before Lane A ships.

---

## Lane A — subject articles (L3)

#### T3.01 — Subject eligibility gate + priority scoring

`Model: Opus 5` · `Depends: T2.41` · `Doc: 09 §4.1–§4.2` · `Tag: target-new` · `Gate: G-D (entry)`

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

`Model: Opus 5` · `Depends: T3.01, T2.14` · `Doc: 09 §4` · `Tag: target-new` · `Gate: G-D`

**What.** Activates the job registered inert in T2.14. Synthesises **only** from
non-disputed corroborated/confirmed facts — a disputed fact never reaches a draft.

**Done when:**
- [ ] Disputed and candidate facts are excluded at the query, not filtered from the draft
- [ ] Runs Tier-C under the umbrella, within the T3.01 budget
- [ ] Every run journals its inputs so a bad article is traceable to its fact set

**Verify.** `cd backend && python -m pytest tests/test_article_synthesis.py -q`

#### T3.03 — Claim-level entailment pass + coverage routing

`Model: Opus 5` · `Depends: T3.02, T2.26` · `Doc: 09 §4.3` · `Tag: target-new` · `Gate: G-E`

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

`Model: Sonnet 5` · `Depends: T3.03` · `Doc: 09 §4.3` · `Tag: target-new` · `Gate: G-E`

**What.** The single hard FK to `knowledge_triples`, safe only because facts are
invalidate-not-delete.

**Done when:** the FK exists and is enforced; an invalidated fact leaves the citation
intact and the article marked stale; a hard fact delete is impossible.
**Verify.** `cd backend && python -m pytest tests/test_article_citations.py -q`

#### T3.05 — Staleness gate + debounced re-synthesis

`Model: Opus 5` · `Depends: T3.04` · `Doc: 09 §4.4` · `Tag: target-new` · `Gate: G-E`

**What.** Staleness is a hash of the **verified** fact set only — a churning candidate
does not trigger re-synthesis. Re-synthesis is debounced, strip-before-rewrite, and
supersedes the prior article.

**Done when:**
- [ ] The hash covers verified facts only, proven by a test that churns candidates
- [ ] Debounce window is a `config` row
- [ ] Re-synthesis supersedes rather than mutating; lineage is preserved

**Verify.** `cd backend && python -m pytest tests/test_article_staleness.py -q`

#### T3.06 — Articles tab

`Model: Sonnet 5` · `Depends: T3.04` · `Doc: 13 §5.2` · `Tag: target-new` · `Gate: G-E`

**What.** Grounded prose with inline claim citations, the claim-support-coverage readout,
and the stale label.

**Done when:** every sentence's citation is reachable in one click; the coverage number is
shown, not hidden behind Advanced; stale articles are labelled, not withheld.
**Verify.** `cd frontend && npm test -- articles && npm run test:e2e -- knowledge`

---

## Lane B — F7 auto-research (tail of Phase 3)

**Entry condition: Lane A shipped and G-E holding.**

#### T3.07 — Research-agent loop through the ordinary capture door

`Model: Opus 5` · `Depends: T3.06, T1.12` · `Doc: 09 §6` · `Tag: target-new` · `Gate: G-E`

**What.** A thin orchestration over already-shipped capture, consolidation, and synthesis.
Evidence is filed through the **ordinary capture front door** — no privileged path, no
second pipeline. That is the entire reason F7 is cheap here.

**Done when:**
- [ ] No new ingestion path is added
- [ ] The loop is Tier-C and bounded by a `config` budget
- [ ] A failed research run leaves no partial state

**Verify.** `cd backend && python -m pytest tests/test_auto_research.py -q`

#### T3.08 — Distinct-origin stamping for researched sources

`Model: Opus 5` · `Depends: T3.07, T1.11` · `Doc: 09 §6` · `Tag: target-new` · `Gate: G-E`

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

`Model: Opus 5` · `Depends: T2.41` · `Doc: 15 §3.1–§3.2` · `Tag: target-new` · `Gate: G-E`

**What.** The client pulls the F3 fused, labelled selection and rewrites a
marker-bounded managed block in the tool's native context file. **The server never writes
the client's filesystem** — that boundary is the whole trust posture of this feature.

**Done when:**
- [ ] Only content between the markers is ever rewritten; user text outside survives
- [ ] A corrupted or missing marker pair fails safe (no write) rather than guessing
- [ ] No server-side filesystem write exists anywhere in the path

**Verify.** `cd backend && python -m pytest tests/test_inject_block.py -q`

#### T3.10 — Truth-first content fill under a token budget

`Model: Opus 5` · `Depends: T3.09, T2.43` · `Doc: 15 §3.4` · `Tag: target-new` · `Gate: G-E`

**What.** Fill order is L2 facts, then L3 articles, then L0 memory summaries, under a
`config` token budget. Every item carries its layer, verification, and badge labels — an
injected claim without its label is the silent-authority failure invariant 14 forbids.

**Done when:**
- [ ] Fill order enforced and tested
- [ ] Budget respected; truncation drops the lowest tier, never mid-item
- [ ] Every injected item carries its labels verbatim

**Verify.** `cd backend && python -m pytest tests/test_inject_fill.py -q`

#### T3.11 — Per-tool adapters (Claude Code, Cursor, Codex, Cline)

`Model: Sonnet 5` · `Depends: T3.09` · `Doc: 15 §3.3` · `Tag: target-new` · `Gate: G-E`

**What.** A managed file block per target tool: `CLAUDE.md`, Cursor's rules, `AGENTS.md`,
Cline. Session-start refresh cadence; `watch` mode is deferred to Phase 4 (T4.06).

**Done when:** each adapter writes the right file with the right marker syntax; an unknown
tool is refused with a message, not a best guess; refresh happens at session start only.
**Verify.** `cd backend && python -m pytest tests/test_inject_adapters.py -q`

#### T3.12 — Inject records journaled as events

`Model: Sonnet 5` · `Depends: T3.11, T1.07` · `Doc: 13 §6.5` · `Tag: target-new` · `Gate: G-E`

**What.** Every injection journals what was pushed, to which target, under which budget —
the human can always see what the agent was told.

**Done when:** each inject writes an event carrying the item ids and the budget used;
records surface in the timeline and calendar.
**Verify.** `cd backend && python -m pytest tests/test_inject_events.py -q`

---

## Lane D — onboarding, SDKs, browser capture

#### T3.13 — `darkmem connect <tool>`

`Model: Sonnet 5` · `Depends: T3.11` · `Doc: 15 §5` · `Tag: target-new` · `Gate: G-E`

**What.** Writes the tool's MCP config from a maintained adapter registry and verifies via
the stateless `initialize → tools/list` handshake.

**Done when:**
- [ ] Handshake verification runs and reports the concrete failure
- [ ] A foreign-Host `421` is reported as **"extend `MCP_ALLOWED_HOSTS`"** — never worked
      around, never by disabling the protection
- [ ] Re-running is idempotent and does not duplicate config entries

**Verify.** `cd backend && python -m pytest tests/test_connect_cli.py -q`

#### T3.14 — Minimal TypeScript + Python SDKs

`Model: Sonnet 5` · `Depends: T3.25` · `Doc: 15 §6` · `Tag: target-new` · `Gate: G-E`

**What.** Three verbs only — `capture`, `search`, `declareContext` — over the doc 12
contract. **Ratify, review, and vault-admin stay out**: the SDK is for agents, and
ratification is a human single-door act.

**Done when:** three verbs each in both languages, over the T3.25 scaffold; a ratify
call is **not expressible** — asserted by a test that greps the generated surface, not
by review.
**Verify.** `cd sdks/ts && npm test` and `cd sdks/python && python -m pytest -q`

#### T3.15 — Browser capture extension

`Model: Sonnet 5` · `Depends: T3.26` · `Doc: 15 §4` · `Tag: target-new` · `Gate: G-E`

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

`Model: Sonnet 5` · `Depends: T1.11` · `Doc: spec §Feature-2, 04, 12` · `Tag: target-new` · `Gate: G-E`

**What.** Keyed on `origin_key` (the agent-run identity). `POST`/`GET /checkpoints` plus
MCP `checkpoint_save` / `checkpoint_latest`, holding a compact `summary` and structured
`next_steps`.

**Done when:** both doors expose it (invariant 17); latest-per-origin is one indexed
query; payload size is bounded.
**Verify.** `cd backend && python -m pytest tests/test_checkpoints.py -q`

#### T3.17 — Resume as a specialised inject

`Model: Opus 5` · `Depends: T3.16, T3.10` · `Doc: 15 §3.2` · `Tag: target-new` · `Gate: G-E`

**What.** At session start the latest checkpoint writes into the managed block under the
token budget, so a fresh session loads a budgeted digest instead of reloading full
context (invariant 17).

**Done when:** resume reuses the T3.10 budget path, not a parallel one; a missing
checkpoint degrades to the ordinary inject; `checkpoint_saved` / `resumed` journal.
**Verify.** `cd backend && python -m pytest tests/test_resume_inject.py -q`

#### T3.18 — Checkpoints are operational, not vault knowledge

`Model: Sonnet 5` · `Depends: T3.16` · `Doc: 13 §6` · `Tag: target-new` · `Gate: G-E`

**What.** A checkpoint carries **no verification badge** — it is operational state, not a
claim about the world. Conflating the two would put unverified agent notes into the vault.

**Done when:** checkpoints cannot enter the fact ladder; no badge renders on them; they
are excluded from retrieval's vault channels.
**Verify.** `cd backend && python -m pytest tests/test_checkpoint_isolation.py -q`

---

## Lane F — distribution UI (F9)

#### T3.19 — Settings → Distribution tab

`Model: Sonnet 5` · `Depends: T3.11` · `Doc: 13 §6.5` · `Tag: target-new` · `Gate: G-E`

**What.** Per-target managed-block config, inject content policy, and the curb control.

**Done when:** each target's block path and status shown; content policy editable; a
single control stops all injection immediately.
**Verify.** `cd frontend && npm test -- distribution`

#### T3.20 — Inject records in timeline and calendar

`Model: Sonnet 5` · `Depends: T3.12` · `Doc: 13 §6.5` · `Tag: target-new` · `Gate: G-E`

**What.** Injections appear as journaled events — the human can see and curb push, never
a silent context swap.

**Done when:** injections render in both surfaces with their item counts and budget;
clicking one shows exactly what was pushed.
**Verify.** `cd frontend && npm test -- activity`

#### T3.21 — Session checkpoints / resume view

`Model: Sonnet 5` · `Depends: T3.17` · `Doc: 13 §6` · `Tag: target-new` · `Gate: G-E`

**What.** Per-run digest, next-steps, and copy-resume in the Activity shell.

**Done when:** latest checkpoint per run is one click away; copy-resume yields the exact
injected text; `checkpoint_saved` / `resumed` events visible.
**Verify.** `cd frontend && npm test -- checkpoints`

---

## Lane G — gate

#### T3.22 — G-E evidence run

`Model: Fable 5` · `Depends: T3.05, T3.06, T3.08, T3.24` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-E`

**What.** L3 shipped **and** the per-article coverage distribution holding above the
runtime threshold in production — a distribution, not a single flattering article.

**Done when:** the coverage distribution is reported (not just a mean); the threshold
was stated before measuring; F7 shipped; verdict in `gate-ledger.md`; `CLAUDE.md`
refreshed to the shipped L3 shape. The production read is the one sanctioned exception
to "nothing automated touches `darkmem`" — it is **read-only** and may never write.
**Verify.** `cd backend && python scripts/benchlib/run_coverage_distribution.py`

---

## Lane H — added by review

#### T3.23 — Articles retrieval channel + `article_embeddings` writer

`Model: Opus 5` · `Depends: T3.02, T2.43, T0.13` · `Doc: 07 §2, 04 §5.3` · `Tag: target-new` · `Gate: G-E`

**What.** Doc 07 §2 makes the articles channel target-new and semantic over
`article_embeddings__<slug>` — the last of the four inert partition templates to get a
writer, and the channel without which T3.10's truth-first inject fill has no L3 tier to
read.

**Done when:**
- [ ] The template loses its inert label; the schema inventory names this as its writer
- [ ] Semantic channel with scope pushdown from the first commit
- [ ] Composed under doc 07 §5's rules (T2.43), never fused ad hoc
- [ ] A stale article is returned labelled stale, not withheld

**Verify.** `cd backend && python -m pytest tests/test_articles_channel.py -q`

#### T3.24 — Coverage-distribution runner

`Model: Sonnet 5` · `Depends: T3.03` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-E`

**What.** The plumbing behind T3.22's verify. Reports the **distribution** of per-article
claim-support coverage, not a mean — one well-covered article is not evidence.

**Done when:**
- [ ] Distribution reported with percentiles, not a summary statistic
- [ ] The production read is **read-only** (the sanctioned exception in runbook §7)
- [ ] Runs against a named snapshot so the number is reproducible

**Verify.** `cd backend && python scripts/benchlib/run_coverage_distribution.py`

#### T3.25 — SDK scaffold and generator

`Model: Sonnet 5` · `Depends: T1.42` · `Doc: 15 §6` · `Tag: target-new` · `Gate: G-E`

**What.** Split out of T3.14, which bundled codegen infrastructure for two languages into
one task. This one names the generator and lands the layout: `sdks/ts/`, `sdks/python/`,
generated from the doc-12 contract.

**Done when:** the generator is named and runs from a documented command; both packages
build; regeneration is idempotent.
**Verify.** `cd sdks && make generate && git diff --exit-code`

#### T3.26 — Browser-extension scaffold

`Model: Sonnet 5` · `Depends: T1.12` · `Doc: 15 §4` · `Tag: target-new` · `Gate: G-E`

**What.** Split out of T3.15. The extension shell under `extension/` with the plain-selection
fallback and the per-install `origin_key`, before any site adapter exists.

**Done when:** the shell posts a human-selected block through the ordinary capture door;
per-install `origin_key` is stable across restarts; no site adapter is required to work.
**Verify.** `cd extension && npm test`

---

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| — | — | — | (none yet) | — |

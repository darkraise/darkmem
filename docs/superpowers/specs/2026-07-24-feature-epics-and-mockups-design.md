# Feature Epics & Comprehensive UI Mockups — deliverable design

**Status:** approved 2026-07-24 (brainstorming). Bridges the completed design corpus
(`docs/design/00–20` + reshape spec + ERD) into the detailed planning phase.
**Branch:** `master` (design corpus committed here). **Substrate:** `darkraise-ui@3.1.2`
(bumped from 3.1.1 this session; frontend typecheck + build green).

This spec designs **two pre-planning deliverables**, not implementation code. It fixes their
structure, scope, form, and where they live, so `writing-plans` can decompose them and a
workflow can execute them. It introduces **no new product mechanism and no new design
decision** — it organizes what docs 00–20 already decided.

---

## 1. Purpose & scope

The design phase is complete: 21 design docs fix *what darkmem is* (00–04 foundation),
*how each subsystem works* (05–19), and *the order everything ships in* (20). Doc 13 fixes
the full screen/module/signal/state inventory; doc 14 fixes the signed-off design language.
Before writing detailed implementation plans, the maintainer wants two artifacts that make
the design **actionable and reviewable**:

- **D1 — Feature epics.** The roadmap (doc 20) elaborated into an epic → feature → story
  tree a plan writer can consume directly: every feature carries its phase, its advance
  gate, its honesty tag, its owning doc, and its business-flow reference.
- **D2 — Comprehensive UI mockups.** The full visual surface of the target darkmem —
  every screen, module, and component of every UI feature, in all four render states and
  both themes — assembled into one self-contained `index.html` and published as a
  claude.ai artifact for sign-off (the darkfoto / darkraise-modder pattern).

**Sequencing.** D1 first (it fixes the full feature scope the mockups must visualize),
then D2. Both precede any implementation plan.

**What feeds this.** Doc 20 (phases, gates, F1–F11 dispositions), doc 13 (screen/module/
signal/state inventory), doc 14 (design language + honesty visual vocabulary), and the
honesty tags + invariant catalog from doc 04 §1 / the `gt-invariants` set.

**Divergence rule.** D1 and D2 are organizational *views* of these docs, never overrides:
on any divergence between a deliverable and docs 13/14/20, the corpus doc wins and the
deliverable is corrected. The deliverables carry no authority the corpus did not grant.

---

## 2. Locked decisions (this session)

1. **Epics organized by roadmap phase.** Seven epics = Phase 0–4 + horizon lanes H1, H2.
   Mirrors doc 20's ship order; split subsystems are surfaced by a cross-cutting matrix (§3).
2. **Mockups are fully comprehensive.** Every screen × every module × all four states
   (empty / loading / error / populated) × light + dark. No representative shortcuts.
3. **Fresh rebuild into one canonical artifact.** The existing 7-board
   `docs/design/mockups/knowledge-vault-mockups.html` is retired (archived under
   `docs/design/mockups/_archived/`); its honesty-vocabulary content is rebuilt into the
   new set. One artifact, redeployed to one URL.
4. **Substrate is `darkraise-ui@3.1.2`** on the doc-14 design language. "Fresh rebuild"
   rebuilds the *boards*, not the design language — doc 14 is signed off and not re-opened.
   Doc 14 pins the substrate at 3.1.1; the 3.1.2 bump is a patch that must not change any
   locked or default theme axis (confirmed at build time), and doc 14's + the README's
   version string get a purely editorial touch-up so "doc 14 not re-opened" stays literally
   true (§7).
5. **Defaults for the two delegated sub-questions** (approved implicitly; flag at spec
   review to change): D1 lives at `docs/planning/feature-epics.md` (a planning bridge, not
   a 22nd design doc); the old mockup file is **archived, not deleted**.

---

## 3. Deliverable 1 — Feature epics (`docs/planning/feature-epics.md`)

**Structure. Seven epics, one per roadmap lane, each stating its goal and its advance gate
as the definition of done, with features nested under the phase they ship in.**

| Epic | Lane | Goal | Advance gate (doc 20 §4) |
|---|---|---|---|
| E0 | Phase 0 — Baseline & harness | Single baseline migration with dormant objects inert; eval harness as a first-class deliverable behind a CI gate | G-A |
| E1 | Phase 1 — Engine core at target shape | Capture + `memory_buffer` (with `origin_key` born at capture, doc 05 §2.1), five-phase pipeline, L1 graph & taxonomy, retrieval with **SQL pushdown** + labels + trace, code truth T1–T4, flattened LLM orchestrator, `events`, contract + core UI | G-B |
| E2 | Phase 2 — The truth core (L2) | Verified facts + `fact_sources` (origin diversity counted over the Phase-1 `origin_key`) + the verification ladder, review/hygiene queues, `projects` registry, consolidation/"dreaming" family, memory relations, topics, then the code deriver | G-C (deriver, Phase-2 exit) / G-D (→ Phase 3) |
| E3 | Phase 3 — Synthesis & reach (L3) | Subject articles behind the groundedness gate (entry: G-D); F7 auto-research fast-follow; distribution — inject v1, onboarding, SDKs, browser capture | done = G-E cleared + F7 shipped; Phase 3→4 is appetite/demand, not a metric |
| E4 | Phase 4 — Hardening & scale | `ApiKey` activation + exposed-deployment posture, repo push webhook, inject `watch`, auto-scrape opt-in, the multi-replica decision if taken | demand-gated |
| EH1 | H1 — Documents / PKM (horizon) | Block pipeline, block retrieval, faithfulness gate, proposition lifting, analysis surface | G-F |
| EH2 | H2 — .NET migration (horizon) | SQL-first baseline replay + harness-paritied port, on appetite | G-G |

**Per-feature row schema (the unit of D1).** Every feature under an epic is one row:

- **Feature name** and **story-level bullets** (what it delivers, at the altitude a plan
  writer turns into TDD tasks — not the tasks themselves).
- **Honesty tag** — `exists-today` / `target-new` / `rebuild` / `activation` / `horizon`
  (doc 04 §1), so the plan never claims scaffolding as shipped (invariant 23).
- **Owning doc** — the design doc (05–19) that owns the mechanism; the plan follows the
  pointer for detail, D1 never re-designs it.
- **F-flow ref** — the business flow F1–F11 (doc 01/20 §5) the feature serves.
- **Gate dependency** — the doc-20 §4 gate this feature must clear or that it helps clear.
- **Activation bar** (`activation`-tagged rows only) — the measured number that flips the
  arm/flag on (doc 20 §5/§10); such a feature is never "done" without it — only its
  landing-wired-at-zero is a phase deliverable.

**Ranking arms and flags are activation features, split honestly across phases.** An arm
that lands wired-at-zero (`w_importance`, `w_heat`, `w_recency`, `w_ppr`, dual-level,
community injection) appears twice per doc 20 §5: once in the phase it lands (Phase 1/2
deliverable), once as the measured activation event in its phase — never collapsed into a
single "done" (invariant 23). Arms that already exist need no landing row and appear once
with their standing disposition: `w_conf` (read now, Phase 1), `relation_rescue` (on,
Phase 1, guarded by the F1 bench), and `reranker_enabled` (wired, dormant, **phase: any** —
activation is a measured win including p95 cost, not a phase deliverable). `applies_when`
boost is a genuine split (P1 wiring / P2 tuning). All of these are named in the matrix below,
so none hides in the phase-first shape.

**Two cross-cutting callouts so the phase-first shape hides nothing.**

- **A phase × subsystem matrix** showing where every split subsystem and arm lights up —
  non-exhaustive by intent (it enumerates every doc-20 §5 split, and doc 20 is the authority):
  Code (F11) across P1 T1–T4 / P2 deriver / P4 push webhook; retrieval arms (doc 07)
  P1-wire / P2-activate; knowledge organization (doc 09) topics P2 / articles P3;
  distribution (doc 15) inject v1 P3 / `watch` + auto-scrape P4 / MCP-resource transport
  horizon; migration & ops (doc 19) Phase-0 baseline birth / H2 replay; plus `expires_at`,
  importance/heat/recency arms, graph arms, `reranker_enabled` (phase: any), `applies_when`
  boost, and the `triple_embeddings` writer per their doc-20 §5 rows.
- **F9 (observe & curate) is signal-ships-with-UI in every phase, not a phase of its own**
  (doc 20 §5, principle 10) — called out per epic, so the plan never defers a signal's
  surface.

**Source mapping (which docs feed each epic).** E0 ← 17, 19. E1 ← 05, 06, 07, 10, 11, 12, 13.
E2 ← 08, 06, 09, 10 (deriver). E3 ← 09, 15. E4 ← 18, 10, 15, 02. EH1 ← 16. EH2 ← 19, 03a.
Every epic's gate row is doc 20 §4; every honesty tag traces to the owning doc.

**Definition of done for D1.** Every F1–F11 flow and every ranking arm/flag in doc 20 §5
appears in an epic or the matrix, with all row fields populated and no `TBD`. Every subsystem
in docs 05–19 appears in an epic or the matrix **except the two that own no phase-scoped
feature**: docs 13/14 (frontend architecture + design language) bind *every* phase's UI
features through the F9 "signal-ships-with-UI" callout rather than a single epic — mirroring
doc 20's "there is no UI phase" — so their disposition is the per-epic F9 callout, not an
epic home.

---

## 4. Deliverable 2 — Comprehensive UI mockups (`docs/design/mockups/`)

**Form (the darkfoto / darkraise-modder pattern the README §"UI Mockups" already fixes).**
Under `docs/design/mockups/` — where the existing boards already live; the README names
`docs/ux/mockups/`, a stale path corrected editorially (§7):

- **`G0` design-guideline fragment** — the doc-14 token system, type scale, spacing, motion,
  accessibility, and the honesty visual vocabulary (verification badge / layer chip / overlay
  chips / both-sides dispute / exclusion strip / trace panel) distilled to a reference board.
- **Component-and-states reference fragments (`C01…`)** — the reusable pieces every screen
  composes: the verification-badge matrix (all four ladder rungs + `under-sourced` / `stale`
  overlays + the `code@commit` variant, **plus** the two non-rung treatments doc 14 §3.2
  fixes — an L0 memory carries **no** verification badge but a lifecycle amber, and a
  terminal-`superseded` article shows a superseded badge that **replaces** the rung), the
  layer chips, the global chrome (nav shell, project switcher, the *separate* context chip,
  command palette), and the render-state skeleton — the four states (empty / loading / error /
  populated) **plus the staged variant** (for doc-13-staged modules) **plus the degraded
  populated-with-caution variant** (one retrieval channel failed, doc 07 §2 / doc 14 §5).
- **Numbered screen fragments (`S01…Sxx`)** — one per screen from doc 13's inventory, each
  showing its modules and its four render states.
- **`build.py`** — compiles G0 + C* + S* fragments into one **self-contained `index.html`**:
  no external assets, all CSS / fonts / images inlined, renders offline anywhere.
- **Publish** — rendered via the Artifact tool as a **claude.ai artifact**; the URL recorded
  in the README status table and in darkmem.

**Substrate.** `darkraise-ui@3.1.2` tokens + the doc-14 design language, every board in
**light and dark**. Honesty copy rendered **verbatim** from doc 12 / doc 14 — a verified fact's
badge claims exactly *"asserted by K distinct origins of kinds [X, Y], no known contradiction,
as of T"*, never the words "true" or "verified" (invariant 14, Part B contract 2). The badge
binds to `COUNT(DISTINCT origin_key)`, never a row count.

**Coverage — the screen-fragment manifest (grounded in doc 13 §4–§7).** Each fragment
renders all four states in both themes.

| # | Screen fragment | Key modules (doc 13) |
|---|---|---|
| S01 | Dashboard | contribution calendar (UTC day buckets), live feed, stat tiles, cold-start hints |
| S02 | Memories — search & list | search box + project scope + context chip, result list, honest layer/verification labels, "supports fact F" nesting, degraded single-channel banner (doc 07 §2) |
| S03 | Memories — why-retrieved trace | envelope header (query, fused/sectioned, channels, weights), exclusion strip (`by_project` / `by_status` / `by_context_conflict`), per-row score breakdown (dormant arms rendered **inactive**, doc 14 §4), context-outcome chip with `human` vs `llm_guessed` provenance qualifier |
| S04 | Memories — create, edit & command palette | create-memory dialog, edit-memory dialog (README §UI-Mockups scope), command palette |
| S05 | Memory detail | content, enrichment (`classified_type`/`summary`/`emotions`/`flags`), `technologies`, supersession lineage (amber), memory-relations, per-memory timeline |
| S06 | Knowledge — Facts tab | filterable fact list (subject/relation/status/scope) |
| S07 | Knowledge — Fact detail | verification badge, sources module grouped by `origin_key` (kind: memory/block/code/human), bi-temporal belief-window timeline, `applies_when` labels, `code@commit` variant, disputed **both-sides split panel** (doc 14 §3.5) |
| S08 | Knowledge — Articles tab | article list (one live per `(project, subject_key)`) |
| S09 | Knowledge — Article detail | grounded prose, inline claim citations, claim-support-coverage readout, `stale` overlay, superseded lineage |
| S10 | Knowledge — Topics tab | community list, labels, reports, pin-suggestion nominations (accept/dismiss) |
| S11 | Knowledge — Review mode | disputed facts shown with **both sides**, under-sourced hysteresis, ungrounded articles, ratify-to-`confirmed` (auth-only) — one `/knowledge/review` shell shared with S12 (a mode toggle, not two routes) |
| S12 | Knowledge — Hygiene mode | duplicates, low-confidence, expiring-soon, superseded lineage, bulk actions |
| S13 | Chat | thread list, message pane, context panel rendering the same trace/labels |
| S14 | Code — Repositories | repo list + live indexing status, reindex dialog, fail-stale banner, index-debt indicator, auto-provision registration state (repo-hint → auto-registered, F11), "gated by repository, not project" scope hint (doc 13 §4.2) |
| S15 | Code — Code Graph | force/tree/circles layouts, camera, palette search, Processes panel + Mermaid export, community colouring, symbol browser, blast-radius buckets |
| S16 | Code — Wiki | read-only wiki, empty-state → reindex dialog |
| S17 | Memory Graph | force/tree/community layouts, search, community navigator |
| S18 | Activity — pipeline stepper | five-phase per-memory stepper; `partial` names the failed step |
| S19 | Activity — live feed | transient `/ws` stream |
| S20 | Activity — failure triage | `pipeline_failures` with retry, poison rows surfaced |
| S21 | Activity — job board | JobRegistry per-job config (cron, floors, ceilings) |
| S22 | Activity — staged monitors | buffer-depth monitor + dream-run monitor, shown **as staged** (labelled with its phase, not empty) **and** as its populated target design (so the full target surface is visualised without overclaiming it ships) |
| S23 | Activity — dream digest | cycle summary, grouped-by-object/action list, per-action & per-batch undo with disabled-past-window state |
| S24 | Activity — calendar day drill | `/activity/day/$date` — that day's events incl. inject records |
| S25 | Settings — Flags | `w_*` arms shown active/inactive, graph `*_enabled` flags, N / diversity / cadence config |
| S26 | Settings — LLM | six inline purpose cards + code sub-buckets + `classifier_kind` toggle, save → live-reload |
| S27 | Settings — Jobs | JobRegistry per-job config |
| S28 | Settings — Security | auth, tokens, TOFU status |
| S29 | Settings — Maintenance | re-embed, cleanup, DB ops |
| S30 | Settings — Distribution | connect status per client, managed-block config, inject policy + token budget, curb control, inject log (populated), render watermark, labels-survive-injection visibility (doc 13 §6.5) |
| S31 | Auth — Login | glass card + particle/aurora backdrop |
| S32 | Auth — Setup wizard | multi-step trust-on-first-use (password → LLM → repo → finish) |

Estimated **~50–65 rendered views** across the 32 screen fragments + G0 + C* references
(states × themes vary per screen); `writing-plans` produces the exact board manifest and the
per-fragment task list.

**State discipline (the four-state contract, doc 13 §4).** Every screen's **empty** state is
honest about *why* it is empty — a cold-start vault says "no corroborated facts yet; candidates
are served labelled in search," never a broken grid; Memories distinguishes "no matches" from
"no memories exist." **Error** is the honest failure — a both-channel search failure is an error
state, never an empty list; a partial pipeline names its failed step. A **degraded** result —
one retrieval channel failed — renders as a populated list with a caution banner ("showing
keyword-only results"), never silently as fewer rows (doc 07 §2, invariant 14). Staged
surfaces (buffer / dream monitors) render as *staged*, not as empty panels that overclaim
(invariant 23).

**Definition of done for D2.** Every screen in doc 13's inventory has a fragment; every fragment
renders all four states in both themes (or the **staged variant** where doc 13 stages the module
— staged monitors additionally render their populated target design labelled with its phase — and
the **degraded** populated-with-caution variant wherever a single retrieval channel can fail,
doc 07 §2 / doc 14 §5); every honesty surface renders its doc-12/14 copy verbatim; `build.py`
produces one self-contained `index.html` that renders offline; the artifact is published and its
URL recorded.

---

## 5. Production process

1. This spec → self-review → maintainer review gate.
2. **`writing-plans`** produces (a) the D1 epics-doc task set and (b) the D2 mockup build plan
   (a darkraise-modder-style numbered task list: G0 → component references → screen fragments in
   waves → assembly → publish).
3. **Execution via workflow** (ultracode): G0 and the honesty-vocabulary reference first (they
   bind every screen), then fan-out screen-fragment writers in waves, an adversarial review pass
   (Fable) per wave against the doc-12/14 honesty-copy contract and the four-state discipline,
   then `build.py` assembly and Artifact publish.
4. **Order:** D1 lands first (fixes scope); D2 follows.

---

## 6. Out of scope (YAGNI)

- No interactive / clickable prototype — static annotated boards only (README form).
- No toast/animation motion — a static still-frame stands in only where a transient toast
  carries honesty content (e.g. a dispute alert, doc 13 §2.1); the motion itself is out of scope.
- No new design-language decisions — doc 14 is signed off; D2 renders it, never revises it.
- No frontend implementation code, no route/component scaffolding — that is the implementation
  phase this spec precedes.
- No re-opening of doc 20's phase order, gates, or F1–F11 dispositions — D1 organizes them,
  never re-litigates them (doc 20 introduces order, not mechanism; so does D1).

---

## 7. Open questions & deferred (each with a recommended stance)

- **D1 location.** *Stance: `docs/planning/feature-epics.md`* — a planning bridge, not a 22nd
  design doc; keeps the frozen design corpus (00–20) closed. Change to `docs/design/21-…` at
  review if the maintainer prefers one home.
- **Old mockup file.** *Stance: archive to `docs/design/mockups/_archived/`*, not delete —
  its honesty-vocabulary boards are the reference the rebuild starts from.
- **Board manifest exactness.** *Stance: the §4 table is the scope contract; the precise
  state×theme board count and per-fragment task breakdown are `writing-plans`' output, not
  this spec's.*
- **Doc-14 / README editorial touch-ups (scheduled, not design changes).** *Stance: the
  substrate version string in doc 14 (pinned 3.1.1) and the README move 3.1.1 → 3.1.2, and the
  README's `docs/ux/mockups/` path is corrected to `docs/design/mockups/`.* Both are editorial
  — a version bump and a path fix — and change no design decision, so "doc 14 not re-opened"
  holds; they land with D2, flagged for the maintainer.
- **Commit posture.** *Stance: per CLAUDE.md, commit only when the maintainer asks; the
  darkraise-ui@3.1.2 bump and this spec are staged for an explicit go-ahead.*

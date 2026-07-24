# darkmem — Feature Epics (planning bridge)

**Status:** planning bridge, dated 2026-07-24. Spec:
`docs/superpowers/specs/2026-07-24-feature-epics-and-mockups-design.md` §3.

## Purpose

This document elaborates `docs/design/20-roadmap-and-sequencing.md` into a nested
epic → feature tree that the implementation-planning phase consumes directly: one epic
per roadmap lane, each stating its goal and its advance gate as the definition of done,
with a features table under it whose rows a plan writer turns into TDD tasks. It is a
planning bridge, not a 22nd design document — the design corpus (docs 00–20) stays
closed, and every row here traces to an owning doc. It introduces no new mechanism and
no new decision: it organizes doc 20, and never re-litigates phase order, gates, or the
F1–F11 dispositions.

## Divergence rule

**Divergence rule:** on any conflict between this doc and docs 13/14/20, the corpus doc wins; this doc is an organizational view, never an override.

## Legend

### Row schema (6 fields)

Every feature row under an epic carries these six fields:

| # | Field | Definition |
|---|---|---|
| 1 | Feature name + story bullets | What it delivers, at the altitude a plan writer turns into TDD tasks — not the tasks themselves. |
| 2 | Tag (honesty tag) | One of `exists-today` / `target-new` / `rebuild` / `activation` / `horizon` (doc 04 §1) — so the plan never claims scaffolding as shipped (invariant 23). |
| 3 | Owning doc | The design doc (05–19) that owns the mechanism; this document follows the pointer for detail and never re-designs it. |
| 4 | F-flow | The business flow F1–F11 (doc 01 §9 / doc 20 §5) the feature serves. |
| 5 | Gate | The doc-20 §4 gate (G-A…G-G) this feature must clear, or that it helps clear. |
| 6 | Activation bar | `activation`-tagged rows only — the measured number that flips the arm/flag on (doc 20 §5/§10); such a feature is never "done" without it, only its landing-wired-at-zero is a phase deliverable. |

### Honesty tags

| Tag | Meaning |
|---|---|
| `exists-today` | Ships in the current baseline and the target keeps it as-is (or reads it for the first time, e.g. `w_conf`). |
| `target-new` | A net-new table, column, service, or capability with no equivalent in the current baseline. |
| `rebuild` | The name and/or table survives, but the mechanism is a fresh build with a different semantic. |
| `activation` | The column, model, or arm already exists today, is populated but unread (or wired at zero), and the target begins to spend it once its measured bar clears. |
| `horizon` | Designed now, scoped to a horizon lane (H1/H2), and shipped only on appetite behind its gate — never a Phase 0–4 dependency. |

---

## E0 — Phase 0: Baseline & harness

**Goal:** Land the single baseline migration with its dormant objects landed inert, and
stand up the eval harness as a first-class, CI-gated deliverable.

**Advance gate:** G-A — extraction F1 bench green reproducing the recorded baseline;
retrieval eval running with accuracy + p95 latency + token cost; baseline migration
boots clean and boot-time reconciliation is idempotent (doc 20 §4).

### Features

| Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar |
|---|---|---|---|---|---|---|

*Rows added in Task 2.*

### F9 — signal-ships-with-UI (this phase)

*Filled in Task 4.*

---

## E1 — Phase 1: Engine core at target shape

**Goal:** Rebuild the engine at target shape — capture + `memory_buffer`, the
five-phase pipeline, L1 graph & taxonomy, retrieval with SQL pushdown + labels + trace,
code truth T1–T4, the flattened LLM orchestrator, `events`, and the contract + core UI.

**Advance gate:** G-B — extraction F1 parity with the recorded baseline within a stated
tolerance; retrieval eval vs. the full-context baseline reported with its latency/cost
twin; isolation probes count zero unlabelled cross-project or superseded rows on every
channel (doc 20 §4).

### Features

| Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar |
|---|---|---|---|---|---|---|

*Rows added in Task 2.*

### F9 — signal-ships-with-UI (this phase)

*Filled in Task 4.*

---

## E2 — Phase 2: The truth core (L2)

**Goal:** Ship the truth core (L2) — verified facts + `fact_sources` + the verification
ladder, review/hygiene queues, the `projects` registry, the consolidation ("dreaming")
job family, memory relations, topics, then the code deriver once L2 is proven live.

**Advance gate:** G-C (deriver, Phase-2 exit) — promotion rate and false-promotion audit
under the stated bar, every ladder transition journaled to `events`; G-D (→ Phase 3) —
the groundedness judge's precision/recall clears the bar on a labelled gold set
(doc 20 §4).

### Features

| Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar |
|---|---|---|---|---|---|---|

*Rows added in Task 2.*

### F9 — signal-ships-with-UI (this phase)

*Filled in Task 4.*

---

## E3 — Phase 3: Synthesis & reach (L3)

**Goal:** Ship synthesis & reach (L3) — subject articles behind the groundedness gate,
F7 auto-research as a committed fast-follow, and distribution (inject v1, onboarding,
SDKs, browser capture).

**Advance gate:** done = G-E cleared (L3 shipped, per-article coverage holding above the
runtime threshold in production) + F7 shipped; Phase 3 → 4 is appetite/demand, not a
metric (doc 20 §4).

### Features

| Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar |
|---|---|---|---|---|---|---|

*Rows added in Task 2.*

### F9 — signal-ships-with-UI (this phase)

*Filled in Task 4.*

---

## E4 — Phase 4: Hardening & scale

**Goal:** Harden and scale — `ApiKey` activation + exposed-deployment posture, the repo
push webhook, inject `watch` mode, auto-scrape opt-in, and the multi-replica decision if
ever taken.

**Advance gate:** demand-gated — an actual exposed deployment (or a concrete second
consumer) opens this phase; nothing in Phases 0–3 depends on it (doc 20 §10).

### Features

| Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar |
|---|---|---|---|---|---|---|

*Rows added in Task 2.*

### F9 — signal-ships-with-UI (this phase)

*Filled in Task 4.*

---

## EH1 — H1: Documents / PKM (horizon)

**Goal:** Ship the horizon documents/PKM lane — the block pipeline, block retrieval, the
faithfulness gate, proposition lifting, and the analysis surface.

**Advance gate:** G-F — the core eval gate (doc 16 §1): retrieval eval and promotion
metrics stable, plus maintainer appetite; the faithfulness metric (span-support
coverage) is defined before build starts and gates before ship (doc 20 §4).

### Features

| Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar |
|---|---|---|---|---|---|---|

*Rows added in Task 3.*

### F9 — signal-ships-with-UI (this phase)

*Filled in Task 4.*

---

## EH2 — H2: .NET migration (horizon)

**Goal:** Replay the target shape onto .NET — the SQL-first baseline replay and a
harness-paritied port, entered on appetite.

**Advance gate:** G-G — the Python target shipped; the harness exists in the new stack
before any parity claim: byte-identical LLM-cache reuse and exact F1-scorer parity
(doc 20 §4).

### Features

| Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar |
|---|---|---|---|---|---|---|

*Rows added in Task 3.*

### F9 — signal-ships-with-UI (this phase)

*Filled in Task 4.*

---

## Phase × subsystem matrix

Non-exhaustive by intent: it enumerates every doc-20 §5 split (every arm, flag, and
subsystem whose ship point and activation point differ), and doc 20 is the authority.

| Item | P0 | P1 | P2 | P3 | P4 | Horizon | Activation bar |
|---|---|---|---|---|---|---|---|

*Rows added in Task 4.*

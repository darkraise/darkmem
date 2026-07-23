# darkmem — Comprehensive Design (binding index)

**Status:** design & clarification phase, started 2026-07-23. Branch: `feat/memory-graph-theming`.
**Nature:** a single unified design of the *target* darkmem — existing features and the full evolution vision in one coherent system.

---

## Locked frame (maintainer decisions, 2026-07-23)

1. **Unified target design.** One coherent design of darkmem's target state; existing behavior is captured where it informs the target. This set becomes the single source of truth.
2. **Full vision committed.** The entire evolution vision (graph-for-retrieval, bi-temporal/temporal, consolidation, memory types, knowledge organization, documents/PKM, distribution/last-mile, product surface, auto-research) is in scope as the target — not pruned.
3. **Rebuild acceptable.** The design is first-principles and greenfield-capable. Today's implementation is *reference* (capabilities to preserve + a migration concern), not a structural constraint. A from-scratch rebuild is an accepted risk.
4. **Proven stack retained.** Python/FastAPI + async SQLAlchemy + Postgres/pgvector (single store) + React + MCP. "Rebuild" = clean re-architecture on this stack, not new technologies. The single-Postgres footprint, per-embedder-fingerprint partitioning, and the tree-sitter code graph are deliberate moats to keep.

## Inputs (feed this design; superseded by it as source of truth)

- `docs/2026-07-22-darkmem-evolution-plan.md` (+ `-implementation-notes.md`, `-plan-review.md`) — strategy, source-verified port sketches, Fable review.
- `docs/2026-07-23-darkmem-product-surface-and-harness-{requirements,review}.md` — product surface, harness, and the Fable-verified code-fact corrections.
- `CLAUDE.md` — the as-is business-logic baseline (invariants).
- The session's competitive research (1AIVault + category) and UX research.

## Document set

Each doc states **decisions and their purpose (why)**, not just what. Grouped by concern; numbering is stable.

### Foundation — produced by hand (highest judgment; binds everything below)
- **00 — Overview, vision & principles** — what darkmem is, who for, north-star, non-goals, design principles, the moats.
- **01 — Domain model & business flows** — the entities (memory, entity/relation, topic, knowledge, project, code) and the lifecycles/user-journeys (capture → extract → retrieve → supersede/expire → consolidate).
- **02 — System architecture** — components, boundaries, data stores, deployment topology, the single-Postgres rationale, sync vs async paths.
- **03 — Technology & stack decisions** — ADR-style rationale for each stack + library choice; what was considered and rejected.
- **04 — Data model & schema design** — the fresh schema: tables, per-fingerprint partitioning, indexes, constraints, invariants.

### Subsystems & algorithms — fanned out via workflow (conform to the foundation)
- **05 — Ingestion pipeline** — phases, async/buffer-flush, chunking/segmentation, extraction+classification, idempotency.
- **06 — Knowledge graph & taxonomy** — entities/relations, the closed taxonomy, dedup/canonicalization, discriminators.
- **07 — Retrieval & ranking** — hybrid RRF, reranker, graph-augmented (PPR / dual-level), ranking priors, the retrieval-trace payload; algorithm decisions + why.
- **08 — Temporal, lifecycle & consolidation** — supersession, bi-temporal edges, TTL, background consolidation/"dreaming", contradiction invalidation.
- **09 — Knowledge organization** — topic = memory communities, knowledge = derived memory rows (`insight`/`profile` + `DERIVED_FROM`), personal-vs-KB = `project`; auto-research → KB.
- **10 — Code indexing** — tree-sitter, the code graph, blast-radius / communities / processes / rename.
- **11 — LLM orchestration & providers** — the six+ purposes, provider/profile config, `api_kind` quirks, content seeds, caching.

### Product & UX — via workflow (doc 14 has its own iterative visual sub-phase)
- **12 — API & MCP contract** — REST conventions, the MCP tool surface, auth model.
- **13 — Frontend architecture & information architecture** — routing, state management, data flow (queries/websocket), the screen/route map, navigation, and the product-surface feature inventory (dashboards, contribution calendar, pipeline observability, retrieval explainability, curation/hygiene) — *what* the screens are and how they connect.
- **14 — UI/UX design language & interaction design** — the visual identity building on `darkraise-ui` + the graph-theming/glass-panel/particle work; the light/dark **theme-token system** (retiring the hard-coded-hex debt); typography, spacing, the component system, motion, and accessibility; plus the interaction design of the key screens. The G0-style **design guideline** is authored here; the comprehensive screen/module/component mockups are the separate **UI Mockups** deliverable (its own section below), which this doc's design language drives. This doc is where *look and feel* is decided, distinct from doc 13's *structure*.
- **15 — Distribution & integration** — auto-inject (pull→push), browser capture, one-command onboarding, client SDKs.
- **16 — Documents / PKM surface** — blocks + block-embeddings, grounded citations.

### Foundations & path
- **17 — Measurement & evaluation harness** — `benchlib` walking skeleton (Tasks 1–2 already built), `longmemeval_bench`, `curation_bench`, metrics per subsystem, affordability protocol.
- **18 — Security, multi-tenancy & ops** — auth, per-project scoping/ACLs on every channel, jobs, observability.
- **19 — Migration & coexistence** — getting from today's darkmem to the target without losing the stored graph/memories; data migration; phased cutover vs greenfield.
- **20 — Roadmap & sequencing** — build order, phases, dependencies, risk.

## UI Mockups (comprehensive deliverable → claude.ai artifact)

A first-class deliverable, not a design-decision doc: **annotated mockups for every screen, every module, and every component of every UI feature** — the complete visual surface of the target darkmem — assembled into one self-contained `index.html` and published as a **claude.ai artifact** for sign-off (the darkfoto / darkraise-modder pattern).

- **Scope — all features, existing + evolution.** Existing: Dashboard, Memories (list / detail / create / edit), Chat, Memory Graph, Code Graph, Repositories & Code Wiki, Settings (every tab). New from this design: the memory **contribution calendar**, **Activity** (5-phase pipeline stepper, live "now processing" feed, failure-triage queue, job/run board), **retrieval explainability** ("why retrieved"), **memory hygiene / review queue**, the **"dreaming"/consolidation digest**, **distribution / auto-inject** UI, and the **documents / PKM** surface. For each: the screen, its modules, its components, and their meaningful **states** — empty, loading, error, populated — in **light and dark**.
- **Form.** A `G0` design-guideline fragment + numbered screen fragments (`S01…Sxx`) + a components-and-states reference, each annotated with intent and the theme tokens it uses. Authored under `docs/ux/mockups/`.
- **Assembly.** A `build.py` (or equivalent) compiles the fragments into a single **self-contained `index.html`** — no external assets, fonts/images inlined — so it renders anywhere offline.
- **Publish.** Rendered via the Artifact tool as a **claude.ai artifact** and shared for review; the artifact URL is recorded here and in darkmem.
- **Depends on.** Doc 13 (the screen/route + feature inventory defines *what* to mock) and doc 14 (the design language + theme tokens define *how* it looks). Driven by its own mockup plan (like darkraise-modder's 21-task plan), produced after the design language is signed off.
- **Sign-off gate.** The maintainer approves the design language (doc 14), then the assembled mockup artifact, before any frontend implementation plan is written.

---

## Production approach

1. **Foundation by hand (00–04)** with the maintainer — clarify and lock the binding frame. Low near-term spend.
2. **Subsystem + product docs (05–13, 15–16) via a multi-agent workflow** — one architect pass over the locked foundation, then parallel doc-writers in waves, then an adversarial (Fable) review — the darkfoto-proven pattern. One burst of spend, gated on foundation approval + usage budget.
3. **UI/UX visual sub-phase (doc 14 → UI Mockups)** — the design language first (doc 14, maintainer-signed-off), then the comprehensive **UI Mockups** deliverable: annotated mockups for every screen / module / component of every feature, assembled into one self-contained `index.html` and published as a claude.ai artifact. Iterative and maintainer-reviewed (frontend-design approach), not a headless writer.
4. **Foundations & path docs (17–20)** once subsystems are settled.
5. Each wave ends with a review; the whole set gets a final consistency/audit pass before any implementation plan is written.

## Status

| Doc / deliverable | State |
|---|---|
| 00 — Overview, vision & principles | ✅ drafted (`dcc9fea`, `e9dedc5`) |
| 01 — Domain model & business flows | ✅ drafted, Fable-reviewed |
| 02 — System architecture | ✅ drafted, Fable-reviewed |
| 03–20 (design docs) | not started |
| UI Mockups (→ claude.ai artifact) | not started |

**Paused/parked:** the `benchlib` harness SDD (plan `docs/superpowers/plans/2026-07-23-harness-benchlib-walking-skeleton.md`; Tasks 1–2 committed, `.superpowers/sdd/progress.md`). The harness becomes design doc 17; execution resumes only after the design is settled, if still wanted.

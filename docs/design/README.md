# darkmem — Comprehensive Design (binding index)

**Status:** **design phase COMPLETE 2026-07-24** (started 2026-07-23) — all 21 docs (00–20) + 03a annex + reshape spec + ERD + UI mockups drafted, adversarially reviewed, and diagrammed; consistency pass done. Branch: `feat/memory-graph-theming` (uncommitted). Next: implementation planning.
**Nature:** a single unified design of the *target* darkmem — existing features and the full evolution vision in one coherent system.

---

## Locked frame (maintainer decisions, 2026-07-23)

1. **Unified target design.** One coherent design of darkmem's target state; existing behavior is captured where it informs the target. This set becomes the single source of truth.
2. **Full vision committed.** The entire evolution vision (graph-for-retrieval, bi-temporal/temporal, consolidation, memory types, knowledge organization, documents/PKM, distribution/last-mile, product surface, auto-research) is in scope as the target — not pruned.
3. **Rebuild acceptable.** The design is first-principles and greenfield-capable. Today's implementation is *reference* (capabilities to preserve + a migration concern), not a structural constraint. A from-scratch rebuild is an accepted risk.
4. **Proven stack retained.** Python/FastAPI + async SQLAlchemy + Postgres/pgvector (single store) + React + MCP. "Rebuild" = clean re-architecture on this stack, not new technologies. The single-Postgres footprint, per-embedder-fingerprint partitioning, and the tree-sitter code graph are deliberate moats to keep. *(Reaffirmed 2026-07-24 by the maintainer-requested .NET re-examination in annex 03a: matrix fully green 24/0/0; .NET proven feasible but deferred to a post-target migration on appetite, not feasibility.)*

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
- **03 — Technology & stack decisions** — ADR-style rationale for each stack + library choice; what was considered and rejected. Its backend-language ADR is informed by annex **03a — Backend stack viability (.NET)** (`03a-backend-stack-dotnet-viability.md`, **decided 2026-07-24 — Python retained, .NET fully de-risked but deferred to a post-target migration**; see Status).
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
| 01 — Domain model & business flows | ✅ drafted, Fable-reviewed; **RESHAPED 2026-07-24** (knowledge vault separated from memory — four-layer ladder, verification ladder, code-as-facts, review queue; reviser+review pass, findings applied) |
| 02 — System architecture | ✅ drafted, Fable-reviewed |
| 03a — Backend stack viability (.NET) | ✅ **DECIDED 2026-07-24: Option A — Python retained**; .NET deferred to a post-target migration. Matrix fully green (24/0/0) after annex + spikes (grammar pipeline 12/12 via `zig cc` + single-DLL pack; full-Leiden quality parity vs leidenalg, 4× faster; eval-harness core with byte-identical cache reuse + exact F1-scorer parity) — so the rejection is appetite/benefit-based, not feasibility-based. Locked-frame decision 4 stands; annex + `spikes/` retained as the de-risking corpus for the deferred migration |
| 03 — Technology & stack decisions | ✅ drafted, adversarially reviewed; **RESHAPED 2026-07-24** (LLM-config flattened — 6 inline purposes, providers/profiles/ml_profiles indirection dropped, inline `classifier_kind`; merged one-LLM-call injection topology; UUIDv7 id policy; numpy pinned) |
| 04 — Data model & schema | ✅ drafted, Fable-reviewed; **RESHAPED 2026-07-24** (the knowledge vault — `knowledge_triples` verified-fact layer + `fact_sources` + `knowledge_articles` + `article_citations`; a 4th embedding family; `memory_relations` five types (`DERIVED_FROM` cut); `entities.repo_ids` inert invariant-8 amendment; generic `events` replacing `audit_log`, monthly RANGE; UUIDv7 + `events`-only partitioning; `llm_` prefix dropped; `projects` registry; single baseline + boot-time reconciliation) |
| Knowledge-reshape spec + ERD | ✅ `docs/superpowers/specs/2026-07-24-knowledge-reshape-design.md` (approved) + `docs/design/erd.md` (target-schema Mermaid ERD); drives the reshape of 01/03/04 |
| Diagrams — foundation 00–04 | ✅ retrofitted 2026-07-24 (23 Mermaid diagrams: system-at-a-glance, four-layer ladder, lifecycle state machines, ingest sequence, deployment, focused per-concern ER); diagrams are now a first-class, required element of every design doc (shared convention) |
| **Wave 1 subsystems — 05, 06, 10, 11** | ✅ drafted + adversarially reviewed + diagrams (framing-brief-driven; 38 Mermaid diagrams; all review findings applied; Mermaid validated). 05 ingestion, 06 knowledge graph & taxonomy (+ spike-gated area seam), 10 code indexing (T1–T4 + deriver), 11 LLM orchestration (flattened) |
| **Wave 2 subsystems — 07, 08, 09** | ✅ drafted + adversarially reviewed + diagrams (31 Mermaid; all findings applied; Mermaid validated). 07 retrieval & ranking (four-layer composition + trace payload), 08 temporal/lifecycle/consolidation (verification ladder + dreaming), 09 knowledge organization (article synthesis + grounding) |
| **Wave 3 subsystems — 12, 13, 15, 16** | ✅ drafted + adversarially reviewed + diagrams (34 Mermaid; all 17 findings applied; Mermaid validated). 12 API & MCP contract (two-front-doors, one partial-result envelope, events read API), 13 frontend architecture & IA (vault top-level, WS→invalidation map, four-state screen inventory), 15 distribution & integration (inject-as-delivery, managed block, browser capture, SDKs), 16 documents & PKM (block model, faithfulness gate — **horizon**, gated behind the core eval gate) |
| **14 — UI/UX design language** | ✅ drafted (Fable-written) + adversarially reviewed + diagrams (5 Mermaid; all 6 findings applied — badge copy never says "verified", article terminal `superseded` badge, score-arm token assignment excludes the caution `--chart-4`, `--chart-4` off-by-one, hardcoded-amber migration honesty, rung-name/human-ratified wording; Mermaid validated). Honesty-label visual vocabulary (verification badge / layer chip / overlay chips / both-sides dispute / exclusion strip / trace panel) on the fixed `darkraise-ui@3.1.1` token substrate |
| **UI Mockups (visual sub-phase)** | ✅ `docs/design/mockups/knowledge-vault-mockups.html` + published Artifact — 7 annotated boards (honesty vocabulary, four-layer search, trace ledger, sources-audit + dispute, review triage, activity/calendar/digest, four screen states) on the shipped `darkraise-ui@3.1.1` tokens; both themes; badge claim strings verbatim from doc 12; realises doc 14 over doc 13's inventory |
| **Convergence tier — 17, 18, 19, 20** | ✅ drafted (Fable-written) + adversarially reviewed + diagrams (18 Mermaid; all 15 findings applied; Mermaid validated). 17 test & eval harness (the gate registry — F1 bench, promotion-rate, groundedness = L3 gate, faithfulness = horizon gate, one verification judge / three consumers), 18 security & auth (LAN trust model, app-as-edge flip, TOFU, dormant `ApiKey` activation, SSRF allowlist), 19 migration/deployment/ops (single baseline + boot-time reconciliation, one-image, DbUp .NET replay), 20 roadmap (five ordinal phases behind named doc-17 gates, F1–F11 committed/stretch/horizon, facts-before-articles) |
| **Final cross-doc consistency pass** | ✅ 2026-07-24 — closed the flagged seams: `sources_changed` / `inject_curbed` / `setup_completed` / `auth_lockout` / `repo_hint_rejected` event_types + `system` object_type added to doc 04 §8.1's closed vocabulary; doc 18 security events renamed to doc 04's underscored shape; doc 20 §3 gate-diagram G-B/G-C relabel; broken cross-refs fixed (doc 17→doc 08 §5.3/§9, doc 16 §4); honesty-tag corrections (one-image is target-new, rate-limit thresholds target-new) |
| **DESIGN PHASE COMPLETE** | ✅ 2026-07-24 — 21 design docs (00–20) + 03a annex + reshape spec + ERD + UI mockups; every doc drafted, adversarially reviewed, findings applied, diagrammed (133 validated Mermaid blocks). Uncommitted on `feat/memory-graph-theming`. Next phase: implementation planning |

**Paused/parked:** the `benchlib` harness SDD (plan `docs/superpowers/plans/2026-07-23-harness-benchlib-walking-skeleton.md`; Tasks 1–2 committed, `.superpowers/sdd/progress.md`). The harness becomes design doc 17; execution resumes only after the design is settled, if still wanted.

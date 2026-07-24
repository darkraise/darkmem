# Feature Epics (D1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `docs/planning/feature-epics.md` — the roadmap (doc 20) elaborated into seven roadmap-phase epics with per-feature rows, a phase×subsystem matrix, and per-epic F9 callouts — the epic spine the detailed implementation-planning phase consumes.

**Architecture:** This is a **document deliverable**, not code. It synthesizes the finished design corpus (docs 05–20) into an epic → feature tree, organized by roadmap phase (doc 20's chosen shape). It introduces **no new mechanism and no new decision**; every row traces to an owning doc. Verification is a completeness/consistency check against doc 20 §5 and the owning docs — not TDD. Each task ends with a concrete verification and a commit.

**Tech Stack:** Markdown only. Source of truth: `docs/design/20-roadmap-and-sequencing.md` (phases, gates, F1–F11 dispositions, arms/flags) and the owning subsystem docs 05–19.

**Spec:** `docs/superpowers/specs/2026-07-24-feature-epics-and-mockups-design.md` §3.

## Global Constraints

Copied verbatim from the spec; every task inherits these.

- **Output:** `docs/planning/feature-epics.md` (a planning bridge, NOT a 22nd design doc — the design corpus 00–20 stays closed).
- **Seven epics = roadmap lanes:** E0 Phase 0 (Baseline & harness), E1 Phase 1 (Engine core), E2 Phase 2 (Truth core L2), E3 Phase 3 (Synthesis & reach L3), E4 Phase 4 (Hardening & scale), EH1 (H1 Documents/PKM), EH2 (H2 .NET migration).
- **Per-feature row schema (6 fields):** feature name + story bullets; honesty tag (`exists-today`/`target-new`/`rebuild`/`activation`/`horizon`); owning doc (05–19); F-flow ref (F1–F11); gate dependency (G-A…G-G, doc 20 §4); **activation bar** (`activation` rows only — the measured number that flips the arm/flag on; never "done" without it).
- **Divergence rule:** on any conflict between this doc and docs 13/14/20, the corpus doc wins; this doc is an organizational view, never an override.
- **Docs 13/14 own no epic:** they bind every phase's UI features through the per-epic **F9 "signal-ships-with-UI" callout** (mirroring doc 20's "there is no UI phase").
- **No new decision:** organize doc 20; never re-litigate phase order, gates, or F1–F11 dispositions.
- **No `TBD`/`TODO`.**

## File Structure

- Create: `docs/planning/feature-epics.md` — the deliverable.
- Read-only sources: `docs/design/20-roadmap-and-sequencing.md` (§2 phase table, §3 layer ladder, §4 gate table, §5 flow + arm tables, §6 tag timeline), `docs/design/01-domain-model-and-business-flows.md` §9 (F1–F11), and the owning docs 05–19 for feature detail.

---

### Task 1: Scaffold the epics doc — header, legend, seven epic sections, matrix skeleton

**Files:**
- Create: `docs/planning/feature-epics.md`

**Interfaces:**
- Produces: the section anchors `## E0 … ## EH2`, the row-schema legend, and the `## Phase × subsystem matrix` heading that Tasks 2–4 fill.

- [ ] **Step 1: Create the file with the frontmatter, purpose, the divergence rule, and the 6-field row-schema legend**

Write the title (`# darkmem — Feature Epics (planning bridge)`), a status line dated 2026-07-24 pointing at the spec, a one-paragraph purpose (elaborates doc 20 into an epic spine for planning; introduces no new decision), the **divergence rule** verbatim from Global Constraints, and a legend table defining the 6 row fields and the five honesty tags.

- [ ] **Step 2: Add the seven epic section headers, each with its goal + advance gate placeholder**

For each of E0–E4, EH1, EH2, add `## E<n> — Phase <x>: <name>` with a one-line **Goal** and an **Advance gate** line quoting doc 20 §2/§4 (E0→G-A, E1→G-B, E2→G-C deriver + Phase-2 exit / G-D→Phase 3, E3→done = G-E cleared + F7 shipped; Phase 3→4 appetite, EH1→G-F, EH2→G-G, E4→demand-gated). Leave a `### Features` subheading and an empty rows table (columns: Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar) under each.

- [ ] **Step 3: Add the matrix skeleton and the per-epic F9 callout stubs**

Add `## Phase × subsystem matrix` with an empty table, and under each epic a `### F9 — signal-ships-with-UI (this phase)` stub.

- [ ] **Step 4: Verify structure**

Run: `rg -n "^## E0|^## E1|^## E2|^## E3|^## E4|^## EH1|^## EH2|^## Phase . subsystem matrix" docs/planning/feature-epics.md`
Expected: 8 headings (7 epics + matrix).

- [ ] **Step 5: Commit**

```bash
git add docs/planning/feature-epics.md
git commit -m "docs(planning): scaffold feature-epics D1 skeleton"
```

---

### Task 2: Fill committed-path epic feature rows (E0–E4) from doc 20 §2/§5

**Files:**
- Modify: `docs/planning/feature-epics.md` (the E0–E4 `### Features` tables)

**Interfaces:**
- Consumes: doc 20 §2 (Phase table "What ships"), §5 (F1–F11 disposition table + arm/flag table), and each row's owning doc (05–19) for the story bullets.
- Produces: complete feature rows for E0–E4, each with all 6 fields.

- [ ] **Step 1: E0 rows** — from doc 20 §2 (Phase 0) + docs 17/19: the single baseline migration with dormant objects landed inert (`repo_ids[]`, `documents`/`blocks`, the four partition templates incl. `triple_embeddings`), tag `target-new, inert`, owning doc 19; the eval harness (extraction F1 bench `exists-today` + retrieval eval `target-new`) behind a CI gate, owning doc 17; gate G-A. Each row: story bullets naming the doc-20 §2 deliverable, tag, owning doc, F-flow (F-none/F9), G-A.

- [ ] **Step 2: E1 rows** — from doc 20 §2 (Phase 1) + docs 05/06/07/08/10/11/12/13: Capture + `memory_buffer` **with `origin_key` born at capture** (F1, doc 05, target-new; incl. the repo-hint handoff to F11 with doc 18's SSRF allowlist gate, target-new); five-phase pipeline merged one-call topology (F2, doc 05, rebuild); L1 graph & taxonomy (doc 06, rebuild); retrieval with **SQL pushdown** + labels + trace (F3, doc 07, rebuild — pushdown is the G-B isolation prerequisite); **supersession rules 1–6 verbatim (F4, doc 08 §2.1, exists-today)**; **expiry / TTL sweep (F5, doc 08, exists-today; the `expires_at` self-expiring-dated-fact activation half follows in E2/Phase 2)**; code truth T1–T4 (F11, doc 10, rebuild); flattened LLM orchestrator (doc 11, rebuild); `events` substrate (doc 04 §8.1, target-new); contract + core UI surfaces (doc 12/13). Gate G-B.

- [ ] **Step 3: E2 rows** — from doc 20 §2 (Phase 2) + docs 08/06/09/10: verified facts + `fact_sources` (origin diversity over the Phase-1 `origin_key`) + the verification ladder (doc 08, target-new); review/hygiene queues (doc 08); `projects` registry (doc 04 §7); consolidation/"dreaming" job family + digest + undo (F6, doc 08); memory relations (doc 08 §5.5); topics (doc 09, F9/doc 06); the code deriver, born corroborated, **after G-C** (F11, doc 10). Gate G-C (deriver/exit) and G-D (→ Phase 3).

- [ ] **Step 4: E3 rows** — from doc 20 §2 (Phase 3) + docs 09/15: subject articles + citations behind G-D groundedness (doc 09, target-new); F7 auto-research committed fast-follow, tail of Phase 3 (F7, doc 09 §6/doc 01 §9); distribution — inject v1 managed block (F10, doc 15), onboarding, SDKs, browser capture (doc 15). Gate G-E → F7.

- [ ] **Step 5: E4 rows** — from doc 20 §2 (Phase 4) + docs 18/10/15/02: `ApiKey` activation + exposed-deployment posture (doc 18, activation); repo push webhook (docs 10/15); inject `watch` mode + auto-scrape opt-in (doc 15); the multi-replica decision if taken (invariant 13, doc 02). All demand-gated.

- [ ] **Step 6: Verify F1–F11 coverage and gate correctness**

Run one probe per committed flow (each must return ≥1):
`for f in F1 F2 F3 F4 F5 F6 F7 F9 F10 F11; do printf "%s: " "$f"; rg -c "\b$f\b" docs/planning/feature-epics.md; done`
Expected: every one of F1–F7, F9, F10, F11 ≥ 1 (F8 is horizon → EH1 in Task 3). Then manually confirm each E-epic's gate matches doc 20 §4 (E1 G-B, E2 G-C/G-D, E3 G-E, E4 demand).

- [ ] **Step 7: Commit**

```bash
git add docs/planning/feature-epics.md
git commit -m "docs(planning): E0-E4 committed-path feature rows"
```

---

### Task 3: Fill horizon epics EH1 (Documents/PKM) and EH2 (.NET migration)

**Files:**
- Modify: `docs/planning/feature-epics.md` (EH1, EH2 `### Features` tables)

**Interfaces:**
- Consumes: doc 20 §2 (H1/H2 rows), doc 16 (block pipeline), doc 19/03a (.NET replay).
- Produces: complete rows for both horizon lanes, all tagged `horizon`.

- [ ] **Step 1: EH1 rows** — F8 Document RAG (horizon, doc 16): block pipeline, block retrieval, faithfulness gate (G-F), proposition lifting, analysis surface. Note the firewall (articles never read blocks; PKM ships only after core eval gate). Gate G-F.

- [ ] **Step 2: EH2 rows** — the SQL-first baseline replay + harness-paritied port (doc 19/03a): DbUp baseline replay, registry DDL in C#, byte-identical LLM-cache reuse + exact F1-scorer parity **before** any parity claim. Gate G-G. Anchor: ~19–38 weeks single-engineer (doc 20 §10, an anchor not a plan).

- [ ] **Step 3: Verify** — Run: `rg -n "F8|horizon|G-F|G-G" docs/planning/feature-epics.md`. Expected: F8 present under EH1; both horizon epics tagged `horizon` with their gates.

- [ ] **Step 4: Commit**

```bash
git add docs/planning/feature-epics.md
git commit -m "docs(planning): EH1/EH2 horizon-lane feature rows"
```

---

### Task 4: The phase×subsystem matrix + per-epic F9 callouts + docs 13/14 disposition

**Files:**
- Modify: `docs/planning/feature-epics.md` (matrix table + F9 stubs)

**Interfaces:**
- Consumes: doc 20 §5 (every split), §6 (tag timeline).
- Produces: the non-exhaustive matrix and the F9 callouts that make the phase-first shape hide nothing.

- [ ] **Step 1: Fill the matrix** with every doc-20 §5 split (non-exhaustive by intent, doc 20 is the authority): Code/F11 (P1 T1–T4 / P2 deriver / P4 push webhook); retrieval arms (P1-wire / P2-activate); doc 09 (topics P2 / articles P3); doc 15 (inject v1 P3 / `watch`+auto-scrape P4 / MCP-resource horizon); doc 19 (Phase-0 birth / H2 replay); `expires_at` (P1 exists / P2 activation); `w_conf` (exists-today, read now, P1); `relation_rescue` (exists-today, on, P1, guarded by the F1 bench — reorder/remove only against a measured delta); `w_importance`, `w_heat`, `w_recency`, `w_ppr`, dual-level, community injection (land P1/P2, activate P2 on retrieval-eval win with twin — **graph arms need the snapshot job live first**); `reranker_enabled` (phase: any, measured win incl. p95 cost); `applies_when` boost (P1 wire / P2 tune); `triple_embeddings` writer (P2+, trigram-miss-rate gated — **counting only, `names_distinct` carried**). Columns: Item | P0 | P1 | P2 | P3 | P4 | Horizon | Activation bar.

- [ ] **Step 2: Fill each epic's F9 callout** — one line per epic naming which UI surfaces ship with that phase's signals (doc 13 inventory): E0 → none (harness/CI only, no UI surface this phase); E1 → pipeline stepper + failure triage + job board + **Dashboard incl. the contribution calendar** (Dashboard is E1 core UI and the calendar reads the P1 `events` substrate) + Memories/why-retrieved trace; E2 → verification badges + Review/Hygiene shell + dream digest + topic surfaces; E3 → article + distribution surfaces; E4 → `ApiKey`-use journaled to `events` + inject `watch`/curb surfaces; EH1 → the analysis/blocks surface; EH2 → none (backend replay, no new UI). State that docs 13/14 bind these, owning no epic.

- [ ] **Step 3: Verify** — Run: `rg -n "w_conf|relation_rescue|reranker_enabled|applies_when|triple_embeddings|w_importance|w_heat|w_recency|w_ppr|dual-level|community" docs/planning/feature-epics.md`. Expected: all eight doc-20 §5 arm/flag rows appear in the matrix. Confirm each epic has an F9 line.

- [ ] **Step 4: Commit**

```bash
git add docs/planning/feature-epics.md
git commit -m "docs(planning): phase-subsystem matrix + F9 callouts"
```

---

### Task 5: Completeness self-check + adversarial review + finalize

**Files:**
- Modify: `docs/planning/feature-epics.md`

- [ ] **Step 1: Placeholder + tag scan** — Run: `rg -n "TBD|TODO|FIXME|\\?\\?\\?" docs/planning/feature-epics.md`. Expected: no matches. Then confirm every feature row has all 6 fields populated (activation rows carry an activation bar).

- [ ] **Step 2: Doc-20 §5 coverage cross-check (per-item, not a walk)** — for each of the 11 flows (F1–F11) and each of the 8 arm/flag rows, run an explicit `rg -c "\b<item>\b"` probe and confirm ≥1; list and close any zero. Then sweep docs 05–19: confirm each owning doc appears in an epic row or the matrix (docs 13/14 are the two exceptions, homed by the F9 callouts per Global Constraints).

- [ ] **Step 3: Adversarial review (optional but recommended)** — dispatch a Fable subagent (`model: fable`) to check E1–E4/EH gates against doc 20 §4, F1–F11 coverage, and no-new-decision fidelity; apply findings inline.

- [ ] **Step 4: Commit**

```bash
git add docs/planning/feature-epics.md
git commit -m "docs(planning): finalize feature-epics D1 (coverage verified)"
```

---

## Self-Review (run after writing all tasks)

1. **Spec coverage:** spec §3's epic table, row schema (6 fields incl. activation bar), the two cross-cutting callouts (matrix + F9), the docs-13/14 disposition, and the D1 definition of done are each implemented by a task above. ✓
2. **Placeholder scan:** Task 5 Step 1 greps for them; no `TBD` shipped.
3. **Type consistency:** the 6 row fields and 7 epic ids (E0–E4, EH1, EH2) are used identically across Tasks 1–5.

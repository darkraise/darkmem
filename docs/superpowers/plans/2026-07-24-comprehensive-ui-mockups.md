# Comprehensive UI Mockups (D2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The S-fragment tasks (Waves A–F) are independent and fan out cleanly across parallel agents.

**Goal:** Produce the complete visual surface of the target darkmem — every screen, module, and component from doc 13's inventory, all render states, light + dark — assembled by `build.py` into one self-contained `docs/design/mockups/index.html`, published as a claude.ai artifact for sign-off.

**Architecture:** A fragment-and-assemble static mockup set (the darkfoto / darkraise-modder pattern). A `G0` design-guideline fragment + `C0*` component-and-state references + `S01…S32` screen fragments are authored as standalone HTML, then `build.py` inlines a shared token/chrome CSS and concatenates them into one offline-renderable `index.html`. Boards render the doc-14 design language on the shipped `darkraise-ui@3.1.2` tokens; **no new design decision is made** — the boards realize doc 14 over doc 13's inventory. This is a **static-mockup deliverable**, not code: each task ends with a concrete verification (grep/build checks) and a commit, not a unit test.

**Tech Stack:** Static HTML + hand-authored CSS (token variables from `frontend/node_modules/darkraise-ui/dist/styles.css`, light + dark); Python 3 for `build.py` (stdlib only — no external deps). Published via the Artifact tool.

**Spec:** `docs/superpowers/specs/2026-07-24-feature-epics-and-mockups-design.md` §4. **Inventory source:** `docs/design/13-frontend-architecture-and-ia.md` §3–§7. **Look source:** `docs/design/14-ui-ux-design-language.md`. **Reference (self-containment technique only):** the archived `docs/design/mockups/_archived/knowledge-vault-mockups.html`.

## Global Constraints

Copied verbatim from the spec; **every fragment task inherits these**.

- **Substrate:** `darkraise-ui@3.1.2` tokens + the doc-14 design language. Fresh rebuild rebuilds the *boards*, not the language. Doc 14 is signed off and not re-opened.
- **Every board renders in BOTH themes** — light and dark. The dark tokens ride `@media (prefers-color-scheme: dark)` **and** a `[data-theme="dark"]` override so the board's theme toggle wins both directions.
- **Self-contained `index.html`:** no external assets — all CSS, fonts, and images inlined (data: URIs); zero `http(s)://` `src`/`href`/`@import`/`url()` to any remote host; renders offline.
- **Verbatim honesty copy (never paraphrased, never the words "true" or "verified" as a status):**
  - Verification badge template (doc 12 §4): **`asserted by K distinct origins of kinds [X, Y], no known contradiction, as of T`**. The **G0 reference carries this literal K/X/Y/T template once**; every *screen* board fills it with realistic sample values (e.g. `asserted by 3 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-20`). The badge binds to `COUNT(DISTINCT origin_key)`, never a row count — the sources module makes the count auditable.
  - `confirmed` rung **visible label** (doc 14 §3.2): **`human-ratified`** (never the word "confirmed" as visible chip text); the claim suffix is **`, human-ratified`**.
  - Disputed two-sided form (doc 14 §3.2): **`disputed: 2 origins assert X, 1 origin asserts not-X, as of T`** — both sides, no picked winner.
  - Cold-start vault empty state (doc 13 §5.1 / spec — the chosen wording; doc 14 §5's longer variant is a corpus phrasing difference, not a conflict, so do not churn on it in review): **`no corroborated facts yet; candidates are served labelled in search`**.
  - Degraded single-channel result banner (doc 14 §3.6, **full string**): **`showing keyword-only results — semantic search unavailable`** (populated list + caution banner, never fewer rows silently — doc 07 §2).
  - Retrieval exclusion strip: human copy like **`3 facts excluded by context conflict`** alongside `by_project` and `by_status` — never buried. When everything is excluded, the **empty state itself shows the strip** ("0 shown, N excluded"), never a bare empty (doc 14 §3.6/§5).
  - Article confidence is labelled **`claim-support coverage`**, not a vague score.
  - `llm_guessed` `applies_when` provenance **chip copy** (doc 14 §4): **`LLM-guessed, not human-checked`** (doc 14 deliberately avoids "unverified" to honour the ban on verdict-claiming words); never used as an exclusion basis until a human touches it.
- **Four render states + three variants (doc 13 §4, doc 14 §5):** every screen shows **empty / loading / error / populated**; **staged** where doc 13 stages a module (labelled with its phase, plus its populated target design — never an empty panel that overclaims, invariant 23); **degraded** (populated + caution) wherever a single retrieval channel can fail; **empty-with-exclusions** wherever scope/context can exclude everything (the exclusion strip renders "0 shown, N excluded", never a bare empty — doc 14 §5). Empty states are honest about *why* (cold-start copy; Memories distinguishes "no matches" from "no memories exist"); a both-channel search failure is an **error** state, never an empty list; a `partial` pipeline **names its failed step** (embed / extract / vector / graph).
- **Badge non-rung treatments (doc 14 §3.2):** an L0 memory carries **no** verification badge (a lifecycle amber instead); a terminal-`superseded` article shows a superseded badge that **replaces** the rung. The four ladder rungs are `candidate | corroborated | disputed | confirmed`; `under-sourced` and `stale` are **label overlays**, never a fifth rung.
- **Scope controls are two distinct chips:** the **project switcher** (sets `project` scope) is NOT the **context chip** (declares session `applies_when`) — never conflated.
- **Fragment form:** `G0` + `C0*` + `S01…S32`, assembled by `build.py` → one `index.html`. Old 7-board file archived to `docs/design/mockups/_archived/`, its honesty-vocabulary content rebuilt (not copied) into G0/C0*/the vault fragments.

## File Structure

```
docs/design/mockups/
  _archived/knowledge-vault-mockups.html   # moved here (Task 0)
  assets/
    theme.css      # darkraise-ui@3.1.2 token vars, light + dark (Task 1)
    mockup.css     # board chrome: frame, annotation callouts, state chips, theme toggle (Task 1)
  fragments/
    G0-design-guideline.html                # Task 3
    C01-verification-badges.html            # Task 4
    C02-layer-chips.html                    # Task 5
    C03-global-chrome.html                  # Task 6
    C04-render-states.html                  # Task 7
    S01-dashboard.html … S32-setup-wizard.html   # Waves A–F
  build.py         # assembler → index.html (Task 2)
  index.html       # generated (Task 40)
```

## Fragment authoring protocol (the complete, shared procedure every S-task follows)

Each `S*`/`C*` fragment is one HTML file under `fragments/`. Authoring a fragment means, for the modules and states named in that task's brief:

1. **Board frame.** Wrap each board in `<section class="board" id="<Sxx-state>">` with an `<h2>` board title and an aside `<div class="annotation">` stating the board's intent + the doc-13/doc-14 sections it realizes (annotations are visible in the mockup — this is a design-review artifact).
2. **Both themes.** Author markup once; the board's controls include the shared theme toggle (from `mockup.css`); render the *populated* board as the hero in both themes (two side-by-side `.theme-light` / `.theme-dark` framings), and the other states once each (theme parity is guaranteed by the shared toggle, so non-hero states show in the default theme with a note).
3. **Compose the C-references.** Reuse the badge (`C01`), layer chips (`C02`), chrome (`C03`), and state skeleton (`C04`) classes — never re-invent a badge; the honesty copy lives in one place.
4. **Verbatim copy.** Paste the exact strings from Global Constraints where the brief calls for them.
5. **Annotate honesty decisions.** Where a board renders a label overlay, an exclusion count, a both-sides split, or a staged panel, the annotation says *why* (the invariant it honors).

**Per-fragment verification (the last step of every S/C task):**
- Offline-clean (strip the SVG namespace under **either** scheme before asserting, mirroring `build.py`): `python -c "import re; h=open('docs/design/mockups/fragments/<file>',encoding='utf-8').read(); s=re.sub(r'https?://www\.w3\.org[^\s\"'\'']*','',h); assert 'http://' not in s and 'https://' not in s, 'external ref'; print('offline-clean')"` → `offline-clean` (data: URIs carry no host and pass).
- Honesty copy present — use `rg -F` (literal; the badge contains `[X, Y]`, a regex char class): for any board with a badge, `rg -Fc "distinct origins of kinds" <file>` and `rg -Fc "no known contradiction, as of" <file>` → ≥1; plus any other verbatim string this brief names, each grepped with `-F`.
- Run: `rg -c "class=\"board\"" docs/design/mockups/fragments/<file>` → equals the state/board count in the brief.
- Never "true"/"verified" as a status: `rg -in "\\b(verified|true)\\b" docs/design/mockups/fragments/<file>` → only in allowed non-status contexts (e.g. "verification", a "verified-fact count" noun labelled per its brief), reviewed by eye.
- Commit the fragment.

---

### Task 0: Archive the old boards; scaffold the directory

**Files:**
- Move: `docs/design/mockups/knowledge-vault-mockups.html` → `docs/design/mockups/_archived/knowledge-vault-mockups.html`
- Create dirs: `docs/design/mockups/{assets,fragments,_archived}` (empty dirs don't commit; they land with their first real file in Tasks 1/3 — no `.gitkeep` needed)

- [ ] **Step 1: Archive the old file (git mv preserves history)**

```bash
mkdir -p docs/design/mockups/_archived docs/design/mockups/assets docs/design/mockups/fragments
git mv docs/design/mockups/knowledge-vault-mockups.html docs/design/mockups/_archived/knowledge-vault-mockups.html
```

- [ ] **Step 2: Verify** — Run: `ls docs/design/mockups/_archived/ docs/design/mockups/fragments/ docs/design/mockups/assets/`. Expected: archived file present; two empty dirs.

- [ ] **Step 3: Commit**

```bash
git add -A docs/design/mockups
git commit -m "docs(mockups): archive 7-board set, scaffold fresh mockup dir"
```

---

### Task 1: Shared CSS — `theme.css` (tokens, light+dark) and `mockup.css` (board chrome)

**Files:**
- Create: `docs/design/mockups/assets/theme.css`
- Create: `docs/design/mockups/assets/mockup.css`

**Interfaces:**
- Produces: the CSS custom properties (`--background`, `--foreground`, `--primary`, `--muted`, `--border`, `--chart-1..5`, `--radius`, …) for light and dark, and the board-chrome classes (`.board`, `.annotation`, `.state-chip`, `.badge`, `.theme-light`, `.theme-dark`, the toggle) every fragment consumes.

- [ ] **Step 1: Extract the darkraise-ui@3.1.2 token values into `theme.css`**

Copy the `:root` (light) and dark custom-property blocks from `frontend/node_modules/darkraise-ui/dist/styles.css` into `assets/theme.css`, emitting them under `:root`/`.theme-light` (light) and `@media (prefers-color-scheme: dark)`, `[data-theme="dark"]`, and `.theme-dark` (dark) so both the OS preference and the board toggle resolve. Do **not** pull in Tailwind — copy only the token variable declarations (the `--*` custom properties), since the mockups author against `var(--token)` directly, not Tailwind utilities.

- [ ] **Step 2: Verify tokens present for both themes**

Run: `rg -c -- "--background|--foreground|--chart-|--primary|--border" docs/design/mockups/assets/theme.css` (expect the token set) and `rg -n "prefers-color-scheme: dark|\\[data-theme=\"dark\"\\]|\\.theme-dark" docs/design/mockups/assets/theme.css` (expect all three dark selectors).

- [ ] **Step 3: Author `mockup.css`** — the board chrome authored against the tokens: `body` grid of `.board` cards on `var(--background)`; `.board` frame with `var(--border)`/`var(--radius)`; `.annotation` callout (muted, small); `.state-chip` (empty/loading/error/populated/staged/degraded/excluded pills); `.badge` variants (candidate/corroborated/disputed/confirmed + `.overlay-under-sourced`/`.overlay-stale` + `.badge-code`); `.layer-chip` (l0/l1/l2/l3); the per-board side-by-side `.theme-light`/`.theme-dark` framings (pure CSS — this is what guarantees theme parity in the mockup; there is no custom JS toggle, and the viewer's own toggle drives `[data-theme]` via the dual dark selectors in `theme.css`). No `@import`/remote `url()`.

- [ ] **Step 4: Verify offline-clean** — Run: `rg -n "http://|https://|@import" docs/design/mockups/assets/mockup.css` → no matches.

- [ ] **Step 5: Commit**

```bash
git add docs/design/mockups/assets
git commit -m "docs(mockups): shared theme tokens + board chrome CSS"
```

---

### Task 2: `build.py` — the self-contained assembler

**Files:**
- Create: `docs/design/mockups/build.py`

**Interfaces:**
- Consumes: `assets/theme.css`, `assets/mockup.css`, `fragments/*.html` (ordered `G0`, `C0*`, `S01…S32`).
- Produces: `docs/design/mockups/index.html` — **body-content only** (no doctype/head/body, so it drops cleanly into the Artifact skeleton and still renders offline in any browser), all CSS inlined, a sticky board-index nav; theme parity comes from each board's side-by-side light/dark framings plus the dual dark selectors that let the viewer's own theme toggle drive `[data-theme]` (no custom JS toggle — CSP-safe).

- [ ] **Step 1: Write `build.py` (stdlib only)**

```python
#!/usr/bin/env python3
"""Assemble the darkmem UI mockups into one self-contained, Artifact-ready
index.html body. No external deps, no network — inlines the shared CSS and
every fragment. Emits body-content only (style + nav + main, no doctype/
head/body) so it publishes cleanly through the Artifact tool's own skeleton
and still renders offline in any browser.
"""
from pathlib import Path
import re, sys

ROOT = Path(__file__).parent
FRAG = ROOT / "fragments"
ASSETS = ROOT / "assets"

# Deterministic order: G0, then C0*, then S## ascending. Read the numeric
# suffix right after the leading letters — never strip every digit in the
# slug (which would mis-sort e.g. "S18-5-phase-stepper").
def order_key(p: Path):
    name = p.stem
    bucket = {"G": 0, "C": 1, "S": 2}.get(name[0], 9)
    m = re.match(r"[A-Za-z]+(\d+)", name)
    return (bucket, int(m.group(1)) if m else 0)

def main():
    css = "\n".join((ASSETS / f).read_text(encoding="utf-8") for f in ("theme.css", "mockup.css"))
    frags = sorted(FRAG.glob("*.html"), key=order_key)
    if not frags:
        sys.exit("no fragments found")
    bodies, nav = [], []
    for f in frags:
        anchor = f.stem
        nav.append(f'<a href="#{anchor}">{anchor}</a>')
        bodies.append(f'<article id="{anchor}" class="fragment">\n{f.read_text(encoding="utf-8")}\n</article>')
    # Reject any external reference before emitting (allow only the SVG
    # namespace under either scheme; data: URIs have no host and pass).
    joined = css + "".join(bodies)
    bad = [m for m in re.findall(r'https?://[^\s"\')]+', joined) if "www.w3.org" not in m]
    if bad:
        sys.exit(f"external references present, not self-contained: {bad[:5]}")
    out = (
        f"<style>{css}</style>\n"
        f'<nav class="board-index">{"".join(nav)}</nav>\n'
        f'<main>{"".join(bodies)}</main>\n'
    )
    (ROOT / "index.html").write_text(out, encoding="utf-8")
    print(f"built index.html from {len(frags)} fragments")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify it runs on an empty set gracefully** — Run: `python docs/design/mockups/build.py`. Expected (fragments dir empty): exits `no fragments found`. (After G0 lands it will build.)

- [ ] **Step 3: Commit**

```bash
git add docs/design/mockups/build.py
git commit -m "docs(mockups): self-contained assembler build.py"
```

---

### Task 3: `G0` — design-guideline fragment

**Files:** Create `docs/design/mockups/fragments/G0-design-guideline.html`

**Brief.** One reference board realizing doc 14: the token palette swatches (light+dark), the type scale + spacing scale, motion + accessibility notes, and the **honesty visual vocabulary** summary (verification badge, layer chip, overlay chips, both-sides dispute panel, exclusion strip, trace panel) — each swatch/example annotated with the token it uses. **States:** single reference board (no four-state cycle). Compose nothing yet (this is the reference the C-tasks formalize). **Verbatim copy:** include the badge string once as the canonical example.

- [ ] **Step 1:** Author `G0` per the Fragment authoring protocol + brief.
- [ ] **Step 2:** Verify per protocol (offline-clean; badge string present; `build.py` now succeeds — Run: `python docs/design/mockups/build.py` → `built index.html from 1 fragments`).
- [ ] **Step 3:** Commit: `git add -A docs/design/mockups && git commit -m "docs(mockups): G0 design guideline"`.

---

### Task 4: `C01` — verification-badge matrix

**Files:** Create `fragments/C01-verification-badges.html`

**Brief.** The most-reused honesty component. Render, in both themes: the four ladder rungs (`candidate` served-labelled-below-verified, `corroborated` with the **verbatim badge string**, `disputed` shown with **both sides**, `confirmed` human-only) + the two overlay chips (`under-sourced`, `stale`) shown riding on a still-`corroborated` row (never a fifth rung) + the `code@commit` corroborated variant with `{commit_sha, basis, file_path, symbol_key}` provenance + the two **non-rung** treatments (L0 memory = no badge, lifecycle amber; terminal-`superseded` article = badge replaces rung). The `confirmed` rung's **visible chip label is `human-ratified`** (never "confirmed" as visible text; claim suffix `, human-ratified`), and the `disputed` two-sided form is `disputed: 2 origins assert X, 1 origin asserts not-X, as of T`. Annotate that the count is `COUNT(DISTINCT origin_key)`. **States:** one matrix board (all variants side by side).

- [ ] **Step 1:** Author per protocol + brief. Define the reusable `.badge*` markup other fragments copy.
- [ ] **Step 2:** Verify per protocol — badge string present; `rg -n "under-sourced|stale|code@commit|candidate|corroborated|disputed|confirmed"` all present; no "verified"/"true" as status.
- [ ] **Step 3:** Commit.

---

### Task 5: `C02` — layer chips + honesty label overlays

**Files:** Create `fragments/C02-layer-chips.html`

**Brief.** The layer chips L0 (memory) / L1 (candidate graph) / L2 (verified fact) / L3 (article), both themes, each annotated with which surface uses it and its token color (excluding the caution `--chart-4` from score arms, doc 14 §4 finding). Show the "supports fact F" nesting affordance (a memory nested under the fact it supports). **States:** one reference board.

- [ ] **Step 1:** Author per protocol. **Step 2:** Verify (chips l0–l3 present; offline-clean). **Step 3:** Commit.

---

### Task 6: `C03` — global chrome (nav shell, project switcher, context chip, command palette)

**Files:** Create `fragments/C03-global-chrome.html`

**Brief.** The three-group / eight-destination nav shell (Workspace: Dashboard, Memories, Knowledge, Chat; Explore: Code, Memory Graph; Operate: Activity, Settings), the **project switcher** (scope) and the **separate context chip** (session `applies_when`) rendered as two distinct controls with an annotation that conflating them would silently exclude dev-only facts, and the command palette. Both themes. **States:** one reference board (+ a switched-project variant showing scope refetch intent).

- [ ] **Step 1:** Author per protocol. **Step 2:** Verify (both controls present + the distinct-controls annotation; offline-clean). **Step 3:** Commit.

---

### Task 7: `C04` — render-state skeleton (four states + staged + degraded)

**Files:** Create `fragments/C04-render-states.html`

**Brief.** The reusable state pattern every screen instantiates: **empty / loading / error / populated**, **plus** the **staged** variant (labelled with its phase) **plus** the **degraded** populated-with-caution variant (`showing keyword-only results — semantic search unavailable`) **plus** the **empty-with-exclusions** variant (the exclusion strip on an otherwise-empty result — "0 shown, N excluded" — never a bare empty, doc 14 §5). Annotate each with its honesty rule (empty says why; error ≠ empty list; partial names its step; staged ≠ empty panel; degraded ≠ fewer rows; empty-with-exclusions ≠ bare empty). Both themes. **Verbatim copy:** cold-start line, full degraded banner. **States:** seven pattern cells.

- [ ] **Step 1:** Author per protocol. **Step 2:** Verify (cold-start + full degraded strings present; seven `.state-chip` variants). **Step 3:** Commit.

---

## Wave A — Workspace core (S01–S05) — independent, parallelizable

Each task follows the **Fragment authoring protocol**. States are empty/loading/error/populated unless the brief adds staged/degraded.

### Task 8: `S01` Dashboard
**Modules (doc 13 §4):** contribution calendar (UTC day buckets; a day click → `/activity/day/$date`), live feed, stat tiles (memory / **corroborated-fact** — doc 13's "verified-fact count", labelled by the vault's rung name to avoid a status claim / open-review / buffer-depth counts), cold-start hints. **Empty** = fresh install, blank calendar + first-capture CTA (not a broken grid). **Verify:** calendar + feed + 4 tiles; empty-state CTA copy.

### Task 9: `S02` Memories — search & list
**Modules:** search box + project scope + context chip, result list with layer/verification labels, "supports fact F" nesting. **States:** + **degraded** (`showing keyword-only results`). **Empty** distinguishes "no matches" vs "no memories exist" (two boards). **Error** = both-channel failure (not empty list). **Verify:** degraded banner + both empty-copy variants present.

### Task 10: `S03` Memories — why-retrieved trace
**Modules (doc 07 §8):** envelope header (query, fused/sectioned, channels ran, weights), **exclusion strip** (`by_project` / `by_status` / `by_context_conflict` — e.g. `3 facts excluded by context conflict`), per-row score breakdown (semantic / keyword / ppr / dual_level / rrf_score / rerank / rank_fusion_factor arms; **dormant arms rendered inactive**), context-outcome chip (match/neutral/conflict, `human` vs `llm_guessed` provenance labelled **unverified provenance**), grouping "supports fact F". **Verify:** exclusion copy + inactive-arm rendering + provenance label present.

### Task 11: `S04` Memories — create, edit & command palette
**Modules:** create-memory dialog, **edit-memory dialog**, command palette. **Verify:** both dialogs present.

### Task 12: `S05` Memory detail
**Modules:** content, enrichment (`classified_type`/`summary`/`emotions`/`flags` — no `llm_` prefix), `technologies` chips, **supersession lineage** (amber badge + link to successor), **memory-relations** (`CONTRADICTS`/`ELABORATES`/`DEPENDS_ON`/`FOLLOWS`/`RELATES_TO`), **per-memory timeline** (events by object, each transition naming its from→to rung where applicable, doc 14 §6). **States:** + **superseded** AND **deprecated** (both amber-labelled, retained not hidden — doc 13 §4). **Verify:** amber lineage (superseded + deprecated) + all five relation types + timeline present.

**Wave A commit:** each task commits its own fragment per protocol.

---

## Wave B — Knowledge vault (S06–S12) — independent, parallelizable

### Task 13: `S06` Knowledge — Facts tab
**Modules:** filterable fact list (subject / relation / status / project scope). **Empty** = cold-start (`no corroborated facts yet; candidates are served labelled in search`). **Verify:** cold-start copy verbatim.

### Task 14: `S07` Knowledge — Fact detail
**Modules (doc 08 §3/§4):** verification badge (verbatim), **sources module** grouped by `origin_key` (kind: memory/block/code/human — the count is `COUNT(DISTINCT origin_key)`), **belief-window** timeline (`valid_at`/`invalid_at`/`expired_at` — a closed window reads as retained history), `applies_when` labels, the `code@commit` corroborated variant, the **disputed both-sides split panel**. **Verify:** badge string + sources-by-origin_key annotation + both-sides panel present.

### Task 15: `S08` Knowledge — Articles tab
**Modules:** article list (one live article per `(project, subject_key)`). **Verify:** one-per-subject annotation.

### Task 16: `S09` Knowledge — Article detail
**Modules (doc 09 §4):** grounded prose with **inline claim citations** (each `claim_span` → `fact_id`, hard FK, never dangling), **claim-support coverage** readout (confidence = fraction of sentences a verified fact entails — labelled, not a vague score), verification badge, **stale** overlay (`synthesised before the latest verified change`, still readable). **States:** + **stale**, + **superseded** (badge replaces rung, reachable via lineage). **Verify:** "claim-support coverage" label + stale copy + inline citations present.

### Task 17: `S10` Knowledge — Topics tab
**Modules (doc 09 §3.4):** community list, labels, reports, **pin-suggestion nominations** (subject soft key, community label, "new or grown" reason, member count, anchored-verified-fact count) with accept (creates pinned subject) / dismiss (recorded). **Verify:** nomination fields + accept/dismiss present.

### Task 18: `S11` Knowledge — Review mode
**Modules (doc 08 §6):** `review_state='open'` — disputed facts with **both sides** (no picked winner), under-sourced hysteresis, ungrounded/low-confidence articles; per-item **ratify-to-`confirmed`** (auth-only, writes a `human`-kind source). Consequence-ranked, not FIFO; served-labelled, never gated. Shares one `/knowledge/review` shell with S12 (mode toggle). **States:** + a **`stale_labelled`** decayed section (unreviewed past `dispute_stale_days` — priority decays but the item stays served-labelled and reachable; decay is a priority change, NOT a resolution, doc 13 §6.2 / doc 14 §6). **Empty** = healthy ("no disputes to adjudicate") as reassurance. **Verify:** both-sides + ratify + shared-shell annotation + the decayed section present.

### Task 19: `S12` Knowledge — Hygiene mode
**Modules (doc 08 §6):** candidate duplicates from dreaming, low-confidence memories, expiring-soon rows, superseded lineage; **bulk actions** (set/extend TTL, prune, supersede, confirm dedup). Shares the S11 shell. **Verify:** bulk actions + shared-shell annotation.

---

## Wave C — Explore + Chat (S13–S17) — independent, parallelizable

### Task 20: `S13` Chat
**Modules:** thread list, message pane, **context panel** rendering the same trace/labels as Memories (one ranking path). **Empty** = new-conversation prompt. **Verify:** context panel renders labels/trace.

### Task 21: `S14` Code — Repositories
**Modules (doc 10, 13 §4.2):** repo list + live indexing phase label, reindex dialog (`{full, enrich_symbols, generate_wiki}`), **fail-stale banner** (last-good graph marked stale, never wiped), **index-debt indicator**, **auto-provision registration state** (repo-hint → auto-registered), **"gated by repository, not project"** scope hint. **States:** + **stale**. **Verify:** fail-stale + auto-provision + repo-not-project hint present.

### Task 22: `S15` Code — Code Graph
**Modules (doc 10 code-graph revamp, kept):** force/tree/circles layout switcher, camera + play/pause, command-palette search, Processes panel + Mermaid export, community colouring + navigator, symbol browser, blast-radius risk buckets. **Verify:** all seven revamp feature groups present.

### Task 23: `S16` Code — Wiki
**Modules:** read-only wiki; **empty** state points at the reindex dialog (`GET /code/wiki` never implicitly generates). **Verify:** empty-state → reindex affordance.

### Task 24: `S17` Memory Graph
**Modules:** force/tree/community layout switcher, search, community navigator. Renders L1 candidate graph + emergent topics; annotate that browsing the graph is **not** what ranks search today (built-but-unspent, invariant 23). **Verify:** the built-but-unspent annotation present.

---

## Wave D — Activity (S18–S24) — independent, parallelizable

### Task 25: `S18` Activity — five-phase pipeline stepper
**Modules (doc 02 §5.2):** per-memory stepper (content embed → extract-and-classify → entity embed → dedup → write), terminal `completed`/`partial`/`failed`; a **partial names its failed step** (embed/extract/vector/graph), never a collapsed batch pass/fail. **Verify:** named-step partial present.

### Task 26: `S19` Activity — live feed
**Modules:** the transient `/ws` stream while open; a **dispute-toast still-frame** — the one transient toast that carries honesty content (a `fact.verified` dispute alert, doc 13 §2.1 / spec §6; static frame, motion out of scope). **Verify:** feed board in four states + the dispute-toast still-frame.

### Task 27: `S20` Activity — failure triage
**Modules:** `pipeline_failures` with retry, **poison rows surfaced** (not looping silently). **Verify:** poison-row + retry present.

### Task 28: `S21` Activity — job board
**Modules (doc 02 §5.3):** JobRegistry per-job config (cron, floors, ceilings), gear dialog, busy(409)-on-lock behavior shown. **Verify:** per-job config present.

### Task 29: `S22` Activity — staged monitors
**Modules:** buffer-depth monitor (`memory_buffer` states: pending/claimed/done/error — poison in triage) + dream-run monitor (consolidation cycle). **States:** rendered **as staged** (labelled with its phase) **AND** as the populated target design — never an empty panel (invariant 23). **Verify:** staged label + populated-target both present.

### Task 30: `S23` Activity — dream digest with undo
**Modules (doc 08 §7):** cycle summary (superseded / refined / promoted-demoted / disputed / edges counts), grouped-by-object/action list (supersession, refine, associative-edge, promotion/demotion, ratification, invalidation, re-synthesis), per-action + per-batch **undo**. **States:** undo-past-window = disabled with honest reason (never a broken button). **Verify:** grouped actions + disabled-past-window state present.

### Task 31: `S24` Activity — calendar day drill-down
**Modules:** `/activity/day/$date` — that day's `events` (incl. `inject` records), UTC day-bucket. **Verify:** day-drill board + inject-event row present.

---

## Wave E — Settings (S25–S30) — independent, parallelizable

### Task 32: `S25` Settings — Flags
**Modules (doc 04 §9, doc 07 §11):** `w_*` ranking weights (each shown **active/inactive** — a `w_*`=0 arm renders inactive, invariant 23), graph `*_enabled` flags (`ppr_enabled`/`dual_level_enabled`/`community_injection_enabled`), corroboration `N` + diversity/time gate, job cadences. **Verify:** active-vs-inactive arm rendering present.

### Task 33: `S26` Settings — LLM
**Modules (doc 11, doc 04 §7):** six inline purpose cards (`embedding`/`extraction`/`classification`/`reasoning`/`summarization`/`reranker`) each editing `{model, base_url, api_key, api_kind, params, dimensions?, reasoning?}`; code-summarization sub-buckets (symbol/module/overview); **classifier-kind toggle** (`llm | local`); **no** provider/profile chrome (deleted). **States:** save → live-reload confirmation. **Verify:** six cards + classifier toggle + no-provider-chrome annotation.

### Task 34: `S27` Settings — Jobs
**Modules:** JobRegistry per-job config surface. **Verify:** per-job config board.

### Task 35: `S28` Settings — Security
**Modules:** auth, tokens, TOFU status. **Verify:** TOFU status board.

### Task 36: `S29` Settings — Maintenance
**Modules:** re-embed, cleanup, DB ops. **Verify:** maintenance ops board.

### Task 37: `S30` Settings — Distribution
**Modules (doc 13 §6.5, doc 15):** connect status per client (Claude Code / Cursor / Codex / Cline …), per-target managed-block config, inject content policy + token budget, **curb control** (see and curb push — never a silent swap), **inject log** (populated), render watermark, **labels-survive-injection** visibility (a `corroborated` fact injected as corroborated). **Empty** = "no clients connected" + onboarding CTA. **Verify:** curb + inject-log + labels-survive annotation present.

---

## Wave F — Auth (S31–S32) — independent, parallelizable

### Task 38: `S31` Auth — Login
**Modules:** atmospheric glass card + particle/aurora backdrop (static still-frame — motion out of scope). **Verify:** login board both themes.

### Task 39: `S32` Auth — Setup wizard
**Modules:** multi-step trust-on-first-use (password → LLM → repo path → finish); gated by `require_uninitialized`. **States:** each step board. **Verify:** four-step wizard present.

---

### Task 40: Assemble + full-set verification

**Files:** Generate `docs/design/mockups/index.html`

- [ ] **Step 1: Build** — Run: `python docs/design/mockups/build.py`. Expected: `built index.html from 37 fragments` (G0 + C01–C04 + S01–S32).
- [ ] **Step 2: Self-containment gate** — Run: `rg -n "http://|https://" docs/design/mockups/index.html | rg -v "www.w3.org"`. Expected: no matches (only the SVG namespace allowed). Run: `rg -c "<article " docs/design/mockups/index.html` → 37.
- [ ] **Step 3: Coverage gate** — Run: `rg -o "id=\"S[0-9]+" docs/design/mockups/index.html | sort -u | wc -l` → 32 screen fragments present. Confirm G0 + C01–C04 anchors present.
- [ ] **Step 4: Honesty-copy gate** (use `rg -F` for literals — the badge holds `[X, Y]`): `rg -Fc "asserted by K distinct origins of kinds [X, Y]" docs/design/mockups/index.html` (≥1 — the G0 literal template); `rg -Fc "distinct origins of kinds" docs/design/mockups/index.html` (≥ several — filled badges on screen boards); `rg -Fc "no corroborated facts yet; candidates are served labelled in search" docs/design/mockups/index.html` (≥1); `rg -Fc "showing keyword-only results — semantic search unavailable" docs/design/mockups/index.html` (≥1); `rg -Fc "human-ratified" docs/design/mockups/index.html` (≥1); `rg -in "status[^<]{0,20}\\b(true|verified)\\b" docs/design/mockups/index.html` (0 — no status says true/verified).
- [ ] **Step 5: Render check** — open `index.html` via the run/browser tooling; confirm both themes toggle and boards render offline.
- [ ] **Step 6: Commit** — `git add -A docs/design/mockups && git commit -m "docs(mockups): assemble self-contained index.html (37 fragments)"`.

---

### Task 41: Adversarial review pass (Fable) + apply findings

- [ ] **Step 1:** Dispatch a Fable subagent (`model: fable`) to review `index.html` + the fragments against: the doc-12/14 **verbatim honesty-copy** contract (badge string, no "true"/"verified", overlays-not-rungs, both-sides disputes, `COUNT(DISTINCT origin_key)`), the **four-state + staged + degraded** discipline per fragment, and **manifest completeness** vs doc 13 §3–§7 (every route/module/notable state present). Report `file:board` findings, no edits.
- [ ] **Step 2:** Apply findings inline; re-run Task 40 gates.
- [ ] **Step 3:** Commit fixes.

---

### Task 42: Publish the artifact + record the URL

- [ ] **Step 1:** Read the full `index.html` (required before publishing). It is **body-content only** (build.py emits no doctype/head/body), so it drops cleanly into the Artifact skeleton: pass the `title` "darkmem — target UI mockups" as a **parameter** (not a `<title>` tag), a one-sentence `description`, and a stable `favicon`; it is theme-aware via the dual dark selectors + side-by-side framings. It is our own design work-product (no impersonation) → publishing proactively is fine. **Publish as a NEW artifact** — do not reuse the retired 7-board artifact's URL; the old set is archived and superseded.
- [ ] **Step 2:** Record the artifact URL in `docs/design/README.md` (UI Mockups status row) and save a darkmem memory (milestone) noting the fresh comprehensive set supersedes the 7-board artifact.
- [ ] **Step 3:** Commit the README URL update.

---

### Task 43: Editorial touch-up — version string + path (scheduled by the spec)

- [ ] **Step 1:** In `docs/design/14-ui-ux-design-language.md` and `docs/design/README.md`, change the substrate version string `darkraise-ui@3.1.1` → `@3.1.2` (editorial only — assert no locked/default theme axis changed). In `docs/design/README.md`'s UI-Mockups section, correct the fragment path `docs/ux/mockups/` → `docs/design/mockups/`.
- [ ] **Step 2:** Verify — Run: `rg -n "3\\.1\\.1|docs/ux/mockups" docs/design/14-ui-ux-design-language.md docs/design/README.md`. Expected: no stale 3.1.1 substrate refs, no `docs/ux/mockups` path.
- [ ] **Step 3:** Commit — `git commit -m "docs(design): substrate 3.1.1->3.1.2, mockups path fix (editorial)"`.

---

## Self-Review (run after writing all tasks)

1. **Spec coverage:** spec §4's form (G0 + C0* + S01–S32 + build.py → self-contained index.html → artifact) is Tasks 0–3/40/42; the 32-screen manifest is Waves A–F (S01–S32 map 1:1 to spec §4's table incl. edit/S04, both-sides/S07, auto-provision/S14, staged+populated/S22, inject-log/S30); the four-state + staged + degraded + empty-with-exclusions contract is C04 + each brief + the Task-40 gates; verbatim honesty copy (badge template, `human-ratified`, full degraded banner, `LLM-guessed, not human-checked`) is the Global Constraints + Task-40 `rg -F` gates; archive is Task 0; editorial touch-up is Task 43. ✓
2. **Placeholder scan:** briefs name exact modules/states/copy + a concrete verify; no "add appropriate…". The per-fragment HTML is authored at execution (correct right-sizing for a mockup deliverable — the plan fixes the brief + verification, not the pixels). ✓
3. **Consistency:** the 37-fragment count (G0 + C01–04 + S01–32), the `.board`/`.badge`/`.layer-chip` class names, and the verbatim copy strings are used identically across `build.py`, the protocol, the briefs, and the Task-40 gates. ✓

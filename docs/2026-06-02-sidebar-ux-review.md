# Sidebar / Feature-Group UX Review — 2026-06-02

Goal: reduce the number of sidebar items to cut user distraction, reduce
feature-management overhead, and flag any feature that can be removed to
improve UX.

Method: 18 parallel agents — one per sidebar route (15) plus three
cross-cutting analyses (graph consolidation, system/admin group,
feature-management overhead). Every claim below is backed by file:line
evidence; load-bearing claims were confirmed by more than one agent.

## TL;DR

The sidebar today has **15 items in 4 groups**. The audit finds it can drop
to **7–8 items in 3 groups** with **zero loss of real capability**: three
features are removable outright, four pages fold into existing pages, one is
miscategorised, and two are mislabeled. Separately, the Settings "Feature
Flags" surface exposes ~11 knobs where only ~4 are product-level decisions.

```
BEFORE (15)                          AFTER (7–8)
─────────────────────                ─────────────────────
Overview                             Workspace        (daily)
  Dashboard                            Dashboard
  Memories                             Memories
  Chat                                 Chat
Visualization                        Explore          (occasional)
  Knowledge Graph   ── remove          Memory Graph   (= Unified Graph)
  Unified Graph     ── rename          Repositories   (+ Wiki tab)
  Vector Space      ── remove          Code Graph
  Code Graph        ── regroup       Admin            (set-once)
Code Intelligence                      Settings       (+ LLM/Jobs/Security tabs)
  Repositories                         Maintenance    (= renamed Reindex; optional)
  Code Wiki         ── merge
System
  Analytics         ── remove
  Pipeline          ── nest
  Jobs              ── nest
  Reindex           ── rename+nest
  Security          ── nest
  Settings
```

## Per-route verdicts

| Route | Label | Use | Maturity | Verdict |
| --- | --- | --- | --- | --- |
| `/` | Dashboard | daily | complete | keep |
| `/memories` | Memories | daily | complete | keep |
| `/chat` | Chat | daily | complete | keep |
| `/unified-graph` | Unified Graph | occasional | complete | keep, rename **Memory Graph** |
| `/graph` | Knowledge Graph | occasional | **thin** | **remove** (fold into Memory Graph) |
| `/vectors` | Vector Space | rare | complete | **remove** |
| `/code-graph` | Code Graph | occasional | complete | keep, move to Explore |
| `/repos` | Repositories | occasional | complete | keep |
| `/code-wiki` | Code Wiki | rare | complete | merge into `/repos` (Wiki tab) |
| `/analytics` | Analytics | occasional | complete | **remove** (dup of Dashboard) |
| `/pipeline` | Pipeline | set-once | complete | nest under Settings (LLM tab) |
| `/jobs` | Jobs | set-once | complete | nest under Settings (Jobs tab) |
| `/reindex` | Reindex | rare | complete | rename **Maintenance** + nest |
| `/security` | Security | rare | complete | nest under Settings (Security tab) |
| `/settings` | Settings | set-once | complete | keep — the consolidation anchor |
| `/llm` | (none) | — | **dead** | already a redirect; retarget after move |

## Features to remove (the explicit ask)

1. **Vector Space (`/vectors`)** — strongest removal candidate. A single
   inert canvas scatter: 2D PCA of already-L2-normalized embeddings (lossy by
   construction, `backend/app/utils/math.py:12-22`), capped at 500 points,
   no click-through, no filter, no action. It overlaps the cluster view in
   the Unified Graph. Users open it once out of curiosity and never return.
   Evidence: `vectors.tsx:34-244`, `use-graph-api.ts:99-115`,
   `vectors.py:12-57`.

2. **Analytics (`/analytics`)** — ~90% duplicates the Dashboard. The four
   stat tiles, top-tags bar chart, and sources pie all read the same
   `useOverview`/`useStats` data the Dashboard already renders. The page even
   defers metrics to the Pipeline page in its own description. Its only unique
   element is a 20-row pipeline-log table — which is itself redundant with the
   log table on the maintenance console. Evidence: `analytics.tsx:109-232`
   vs `index.tsx:121-344`; both hit `/analytics/overview`
   (`use-pipeline-api.ts:188-193`).

3. **Knowledge Graph (`/graph`)** — remove as a standalone route (this is a
   fold, not a deletion of capability). Its working "Entity Graph" tab renders
   the exact same `/graph/full` dataset that the Unified Graph already overlays
   behind its **Entity Layer** toggle (backend `_fetch_entity_overlay` calls
   the same `get_full_graph`, `graph.py:203-213`). Its second tab, "Knowledge
   Timeline", is **dead UI**: the hooks return `Promise.resolve([])` with
   `enabled:false`, and the page shows a permanent amber "temporal fact
   timeline is not yet available" banner (`use-graph-api.ts:144-163`,
   `graph.tsx:242-250`). Net: one redundant tab plus one dead tab.

4. **Knowledge Timeline tab** — even if `/graph` survives, this stub should be
   removed until `GET /api/v1/graph/knowledge/timeline` exists. A nav target
   that dead-ends on a "not available" banner is pure distraction.

5. **`/llm.tsx`** — already a dead redirect to `/pipeline`
   (`llm.tsx:3-7`). After Pipeline moves into Settings, retarget it (or delete
   the route).

## Pages to fold (no capability lost)

- **Code Wiki → Repositories.** Code Wiki cannot function standalone — it
  requires selecting an indexed repo, and its empty state links back to
  `/repos` and the reindex flow. Repositories already shows file/symbol counts
  and is the only place that triggers `generate_wiki`. It belongs as a per-repo
  "Wiki" tab on `/repos`, eliminating a sidebar item and a near-orphan
  two-item group. Evidence: `code-wiki.tsx:196-225`, `repos.tsx:504-518`.

- **Pipeline → Settings (LLM tab).** Pipeline is pure set-once LLM
  configuration (purposes, providers, profiles, prompts). It draws from the
  same `@/features/pipeline` components and writes the same `POST /config/llm`
  as Settings, which already has LLM Providers / LLM Profiles / ML Profiles
  tabs. The split forces users to bounce between "Settings → create a profile"
  and "Pipeline → apply it." Evidence: `pipeline.tsx:52-61` vs
  `settings.tsx:571-635`.

- **Jobs → Settings (Jobs tab).** Cron scheduler for four background jobs,
  all shipping sensible `default_cron` values (`main.py:167-215`). Configured
  once, then effectively never revisited. Evidence: `jobs.tsx:392-421`.

- **Security → Settings (Security tab).** Read-only auth/setup audit-log
  viewer with filters and pagination — no mutations. Consulted only when
  investigating a suspicious event. Evidence: `security.tsx:40-140`.

## Mislabeled / miscategorised (fix even if not nesting)

- **`/reindex` is misnamed.** Its component is literally `PipelinePage`, its
  header reads "Pipeline Logs", and it contains pipeline-maintenance panels:
  Reprocess-All, Obsolete-Embeddings re-embed, and failure retry/forget. It
  has **nothing to do with repository reindexing** — that lives on `/repos`
  via the per-row Reindex button and `ReindexDialog`. The label actively
  misleads. Rename it **Maintenance** (or "Pipeline Health"). It can stay
  top-level or fold into Settings/Pipeline. Confirmed independently by three
  agents. Evidence: `reindex.tsx:44-46,569,602-608`, `repos.tsx:423-437,532-545`.

- **`/code-graph` is in the wrong group.** It sits in "Visualization" next to
  the three memory-knowledge views but shares no data with them — it renders a
  per-repo code symbol/call graph (AST, blast-radius, symbol search). It is
  code-intelligence tooling and belongs beside Repositories. Move it; do not
  remove it (it is a fully built, distinct feature). Evidence:
  `code-graph.tsx:13-105`, `code-graph-renderer.tsx:57-243`.

## Graph consolidation detail

The four "Visualization" routes are bespoke at the render layer (three
separate Sigma renderers plus one raw canvas), sharing only color/geometry
helpers — so they were never actually unified despite the name. The right
end state is **two** graph entries:

- **Memory Graph** (`/unified-graph`, renamed) — keep the rich 2D/3D
  clustered renderer. It already has the Entity Layer toggle that subsumes
  `/graph`. If you want to preserve the embedding-space view, add `/vectors`'
  PCA projection as a third **view toggle** (2D / 3D / Embedding) rather than
  a separate route — but the lower-effort path is to drop it.
- **Code Graph** (`/code-graph`) — kept standalone, regrouped under Explore.

Avoid the "tabs inside one route" pattern that produced the dead Timeline tab;
prefer a view toggle on a single working surface.

## Feature-management overhead

The Settings "Feature Flags" card flattens five different concern types into
one list, giving every knob equal weight. All nine backend flags are live
(verified in `config.py:192-207` and their consumers), so this is a layout
problem, not dead config. Restructure into two tiers:

**Keep prominent (genuine product decisions):**
- Hybrid Search (default on) — simplify the "BM25 + RRF" jargon in the label.
- LLM Enrichment — **rewrite the copy**: it currently says "Run LLM
  classification alongside regex for A/B comparison", which mislabels a real
  product feature as an experiment. It is the gate that populates all `llm_*`
  enrichment columns.
- Reranker — and **surface its hidden dependency** on the configured
  "reranker" LLM purpose inline (today the toggle and its prerequisite live on
  two different pages).
- Classification simple/expanded mode.

**Collapse into an "Advanced" disclosure (keep defaults untouched):**
- Throughput numerics: `pipeline_concurrency` (5), `embedding_batch_size`
  (20), `embedding_concurrency` (1), `entity_cache_ttl_minutes` (60) — pure
  internal plumbing per CLAUDE.md ("the rest govern concurrency or
  thresholds").
- `confidence_rank_gamma` (0 / disabled) — expert retrieval-ranking tuning.
- `relation_rescue` (on) — pattern-heuristic implementation detail, disabled
  only for evaluation.
- Per-area classification switches — gate behind expanded mode, label advanced.

On the **Jobs** page, lead with the preset dropdown and tuck the free-text
cron field and min-interval column behind a details disclosure.

Net: the everyday Settings surface drops from ~11 knobs to ~4, while every
advanced lever stays reachable.

## Suggested rollout (low-risk first)

1. **Quick wins, isolated:** delete `/vectors` and `/analytics` routes +
   sidebar entries; remove the dead Knowledge Timeline tab; retarget/delete
   `/llm`. Move `/code-graph` into the Explore/Code group. Rename `/reindex` →
   "Maintenance". (15 → ~11 items, no merges yet.)
2. **Merges:** fold Code Wiki into `/repos` as a Wiki tab; fold `/graph`'s
   entity view into the renamed Memory Graph. (→ ~9 items.)
3. **Admin consolidation:** add Jobs, Security, and LLM (Pipeline) tabs to
   Settings; optionally fold Maintenance in too. (→ 7–8 items.)
4. **Settings card restructure:** Features vs Advanced tiers; relabel LLM
   Enrichment / Hybrid Search; surface the Reranker dependency.

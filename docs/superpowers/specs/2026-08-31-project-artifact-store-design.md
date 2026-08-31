# Darkmem as the project-artifact store and progress surface

Date: 2026-08-31
Status: design; not yet planned. Owner reviewed the first seven decisions and
added two feature areas (§8 personal workspace, §9 backup) on the same day.

No code is written by this document. Every claim in §§1-7 is grounded in files
opened during the design pass; the measured facts it was briefed with are taken
as given and not re-derived. Paths are relative to the repo root.

Standing context: the owner's greenfield ruling of 2026-08-31 (`CLAUDE.md`,
"Greenfield until the freeze") means no change here owes backward compatibility
or a data migration. That does not make the *schema-cost* column below
uninteresting — a baseline regeneration still means dropping and recreating
every deployed database — but it removes migration design from every item.

## Decision summary

| # | Question | Decision | Schema cost |
|---|---|---|---|
| 1 | Channel | Share `documents`/`blocks`, separated by `project` (the existing identity half) + a reserved `properties.kind` label; no new table | no schema change |
| 2 | UI | New `projects` route family (workspace: Artifacts + Progress tabs); `/documents` stays the personal surface and gains a project pin; Activity route unchanged | no schema change |
| 3 | Progress | Live progress = `session_checkpoints` + its existing `events` trail, rendered by the already-half-built Checkpoints UI; durable ledger = a document under a shape convention. Prior events-task proposal rejected as a write surface, accepted as a render path. Owner's single-file position accepted for the durable record, rejected as the live surface | no schema change |
| 4 | Oversized blocks | (a) enable table parsing with new `table`/`table_row` block types (taxonomy-first, code-only), (b) oversized-block warning in `PutResult` + journal, (c) defer doc 16 §3's embed-time chunking | no schema change |
| 5 | Round-trip | Raw content stored now under a reserved `documents.properties` key (bridge); `expected_hash` optimistic-concurrency precondition now; version history deferred; real `content` column folded into the *next already-scheduled* baseline regen, never triggered by this work | no schema change now; one deferred regen rider |
| 6 | Sequencing | Nine increments below; increment 0 (reachability) + 1 (watchable progress) is the smallest visible win | — |
| 7 | Not build | Task model, revisions table now, agent-path block diffing, CRDT/multiplayer, block↔memory fusion, git sync-back, events task vocabulary, second table, bespoke backup UI, in-app restore button | — |
| 8 | Personal workspace | Notion-style block editing for personal notes; forces stable block identity, granular block verbs and per-block re-embed — which also repays the door's whole-document cost model | **baseline regen** |
| 9 | Backup | Pluggable off-host destinations, encrypted and verified; `backup_ship` JobRegistry job over the existing dump/restore scripts; a read-only backup worker running the same image | no schema change |

---

## 1. Channel: one table, separated by `project`

**Decision: project artifacts and personal notes share `documents`/`blocks`.
Separation is the `project` column, which is already half the identity key and
already a hard storage/retrieval boundary. No new channel, no new table.**

Forcing reasons:

- **The separation primitive already exists and is enforced, not advisory.**
  `documents.project` is NOT NULL and the identity is
  `UNIQUE (project, uri) WHERE uri IS NOT NULL`
  (`backend/migrations/versions/0001_baseline.py:1294-1296`);
  `BlockQueryService.search` takes `project` with *no default* — "a retrieval
  scope that can be omitted gets omitted" is its own stated rule
  (`backend/app/services/block_query.py:113-115`); the ANN probe applies the
  project predicate in SQL, never post-fetch
  (`backend/app/services/block_embeddings.py`, `search_blocks`). An agent
  scoped to one project cannot see another's documents today. The gap is UI
  only, exactly as the brief measured.
- **A second table is the expensive axis for zero capability.** It would be a
  baseline regen (drop/recreate every deployed database, re-seed
  `admin_password_hash` + eight `llm_purpose_configs` rows, `schema_guard`
  re-hash), plus a duplicate of the whole five-verb surface, its two doors, the
  firewall tests and the embed partition family — to reproduce an isolation
  property `project` already provides.
- **Doc 16's PKM framing survives.** Doc 16 §1 scopes the surface as a
  *personal memory engine* (`docs/design/16-documents-and-pkm.md:7-9`), but
  every mechanism in it is per-project already (§2's identity, §4's channel).
  Filing project artifacts is a widening of *audience*, not of mechanism:
  nothing below adds a retrieval path, a lift route, or a vault writer, so the
  three structural scans in `tests/test_block_retrieval.py` (retrieval-fusion
  closure, vault-minting closure, repository-method allowlist) are untouched.
- **The firewall is indifferent to what the documents are about.** A progress
  ledger in `blocks` is exactly as firewalled from memory composition as a
  personal note is.

Concrete conventions (documented, not enforced — same posture as
`SOURCE_TYPE_*`, which `document_parsers.py:33-52` deliberately leaves as a
naming convention rather than a CHECK):

- **Project artifacts**: `project = <repo-name>` (matching the
  `project/<repo-name>` tag convention agents already use for memories),
  `uri` = the repo-relative path the file had (`planning/progress.md`,
  `planning/tasks/E1-engine-core.md`). Re-filing updates in place via the
  `(project, uri)` upsert (`backend/app/repositories/documents.py:75-88`).
- **Personal notes**: stay in `default` (what the shipped UI already pins:
  `frontend/src/features/documents/components/documents-view.tsx:30`).
- **Optional `properties.kind` label** (`"artifact"` / `"note"`), written by
  the filing agent into the existing `properties JSONB`
  (`0001_baseline.py:1283`), for finer UI filtering later. Deliberately not a
  column and not load-bearing: the project boundary is the separation; the
  label is decoration.

## 2. UI separation

darkraise-ui was enumerated
(`frontend/node_modules/darkraise-ui/dist/components/`); every primitive named
below ships there: `tabs`, `card`, `badge`, `empty-state`, `tree-view`,
`table`, `timeline`, `virtualized-timeline`, `combobox`, `breadcrumb`,
`segment-group`, `stat`, `skeleton`, `progress`. No new local component is
proposed that the library covers; the local work is composition and restyle.

**New route family** (TanStack file routes, following the existing
`knowledge_.facts_.$factId.tsx` convention):

- `frontend/src/routes/_authenticated/projects.tsx` — project index. Cards
  (`card` + `stat`) per project from `GET /api/v1/projects`
  (`backend/app/api/routes/projects.py:10`; registry model
  `backend/app/models/project.py:23`): document count, latest checkpoint age,
  latest event age.
- `frontend/src/routes/_authenticated/projects_.$project.tsx` — the project
  workspace, `tabs` with two tabs (mirroring `activity.tsx`'s shape):
  - **Artifacts** — left pane: document list for the project
    (`GET /api/v1/documents?project=` — `backend/app/api/routes/documents.py:276`)
    rendered as a `tree-view` grouped by uri path segments (the list route has
    no prefix filter; grouping is client-side over the ≤200-row page, which is
    fine at this corpus size — 446 files). Right pane: outline
    (`GET .../outline`, `document_door.py:document_outline`) as a nested
    `tree-view`, block reader below it (`GET /documents/{id}`,
    `document_blocks`), `breadcrumb` from `SectionHit.heading_path`
    (`backend/app/services/document_door.py:290`) on search hits, search box
    over `POST /documents/search`. `table` blocks (new in §4) render through
    the library `table` component instead of a text blob.
  - **Progress** — top: the pinned ledger document (convention:
    uri `planning/progress.md` in that project), rendered as outline + blocks.
    Below: checkpoint runs filtered to the project, reusing
    `use-checkpoint-runs.ts` (its `useEvents` read already server-filters;
    `list_events` builds project predicates into the SQL —
    `backend/app/services/events.py` module docstring, lines 27-31). Run
    history renders on `timeline` (or `virtualized-timeline` for long runs).
    Live view: TanStack Query `refetchInterval` (~15-30 s) on the events and
    latest-checkpoint queries — no backend change. (Pushing checkpoint events
    over `/ws` is a polish item; I did not open the ws module this pass, so it
    is listed as to-verify, not assumed.)
- **Project switcher**: `combobox` fed by `/api/v1/projects`, in the workspace
  header.

**What happens to existing surfaces:**

- `/documents` (`frontend/src/routes/_authenticated/documents.tsx`) stays the
  *personal* surface: `DocumentsView` keeps its horizon-labelled QA/summary/
  connections panels, drops the hardcoded default (`documents-view.tsx:30`
  takes a `project` prop the route never passes) and pins `default`, with the
  same combobox to switch. The document list/outline/reader pieces are
  extracted into shared components under `frontend/src/features/documents/components/`
  so both surfaces render one implementation.
- **Activity stays exactly as it is** — it is the box-level operational
  surface (pipeline, jobs, triage, dream), and its Checkpoints tab
  (`frontend/src/features/activity/components/checkpoints-tab.tsx`) remains
  the cross-project view of the same data the workspace's Progress tab scopes
  to one project. No route is removed.

## 3. Progress tracking: checkpoints for live, a document for durable

**Decision: the live progress surface is `session_checkpoints` plus the
`checkpoint_saved`/`resumed` events it already journals, rendered by the
Checkpoints UI that already exists. The durable record is a ledger document
filed through the door under a shape convention. Nothing new is stored.**

The agent loop that makes the owner's requirement ("watch a long session from
a browser") true with zero backend schema work:

1. At each meaningful step, the agent calls `checkpoint_save` (MCP,
   `backend/app/api/mcp/server.py:503`; REST twin per
   `docs/two-door-parity.md:59`) with its run's `origin_key`, the project, a
   `summary` (≤4000 chars, `backend/app/services/checkpoints.py:106`) and
   `next_steps`. Each save journals a `checkpoint_saved` event
   (`checkpoints.py:88,212`).
2. The Checkpoints tab already groups runs by `origin_key` and renders
   history from those events (`frontend/src/features/activity/use-checkpoint-runs.ts`).
   Adding the project filter and a poll interval (increment 1) makes it live.
3. At milestones — not per step — the agent updates the ledger document via
   `document_put`.

**Judging the prior events-table proposal: rejected as a write surface,
accepted as a render path.**

- Accepted: rendering progress through the Activity/events readers and
  grouping by run was the right instinct — and it is *already built* for
  checkpoints, which is why the accepted design needs no new code there.
- Rejected: widening `EVENT_TYPES` with task/progress values is unnecessary —
  `checkpoint_saved` and `resumed` are already in the vocabulary
  (`backend/app/services/events.py:187-193`) and `OBJECT_TYPES` already
  carries `checkpoint` and `document` (`events.py:200-211`) — so the
  proposal's one advantage ("no migration") buys nothing the shipped
  vocabulary doesn't have. Worse, `events` is the append-only audit substrate
  whose payloads outlive deletion by ruling (T2.59; the write-time
  minimization rule is standing), and free-form per-step agent prose is
  exactly the content that rule exists to keep out of an unpurgeable store.
  A checkpoint row, by contrast, is an ordinary deletable table. The task
  *model* (statuses, dependencies, per-task rows) stays rejected as the owner
  already conceded — heavier than the need, and any new table is a regen.

**Engaging the owner's single-file position directly.** A progress.md/ledger
file is *sufficient as the durable record* — the measurement itself shows it:
`planning/gate-ledger.md` (667 blocks, largest 13,202 chars) files and
retrieves fine, because it is headings-and-prose. It is *not sufficient as the
live surface*, for three measured or structural reasons:

1. **The mega-table shape fails silently today.** `planning/progress.md`
   parses to a 235,716-char single block; `embed_batch_chunked` slices by
   *count*, never by length (`backend/app/services/llm.py:499`), so the block
   is sent whole and truncated by the embedder. The file reports success and
   is effectively unsearchable — the invariant-14 violation §4 closes. Until
   §4 lands, "the document door is already capable" is false for exactly the
   file the owner points at.
2. **The cost model punishes per-step appends.** An edit strips and re-inserts
   every block and re-embeds the whole document — the door's own stated cost
   ("the cost of editing one paragraph in a large document is the same as
   filing it from scratch", `backend/app/services/document_door.py` module
   contract; strip + fresh INSERT in `repositories/documents.py`). A 43-998
   block ledger updated every few minutes is hundreds of embed calls per
   tick against the LAN Ollama box. One checkpoint row is one INSERT and no
   embed.
3. **Last-writer-wins loses concurrent lanes.** The upsert is a plain
   `ON CONFLICT (project, uri) DO UPDATE` (`repositories/documents.py:81`)
   with no precondition, and this owner's workflow runs 4-5 concurrent agent
   lanes (per the session-memory record of the parallel test-database lanes).
   Two lanes appending to one progress.md race; the loser's append vanishes
   with no error. Checkpoints don't collide: each run writes under its own
   `origin_key`, and the checkpoint door *refuses* undeclared identities
   precisely to prevent cross-run bleed (`checkpoints.py`, `UndeclaredOrigin`).

So the synthesis: file-shaped ledger for what a file is good at (a durable,
human-readable milestone record), checkpoint rows for what a file is bad at
(high-frequency, concurrent, watchable step reporting). Both stores ship; the
work is UI and convention.

One honest limit, stated because the checkpoints module states it
(`checkpoints.py`, module docstring, final paragraph): run correlation is a
client-discipline property. The agent must declare the same `origin_key` to
every save in a run, or the UI shows fragments. The agent-convention doc
(increment 5) carries this.

## 4. The oversized-block silent degradation

**Decision: fix the dominant cause structurally (tables), make the residual
loud (a warning at put), and defer the general mechanism (embed-time
chunking) that doc 16 already sanctions but the shipped partition shape
cannot yet hold.**

1. **Enable table parsing; add `table` and `table_row` to `BLOCK_TYPES`.**
   Taxonomy-first: the vocabulary edit lands in
   `backend/app/taxonomy.py:383-389` before the parser emits it — and it is a
   *code-only* edit, because `blocks.type` is plain `TEXT` with no CHECK
   (`0001_baseline.py:1313`); the closure lives in `normalize_block_type`
   (`taxonomy.py:416`), not the database. The parser
   (`parse_markdown`, `backend/app/services/document_parsers.py`) enables
   markdown-it's `table` rule and emits one `table` block (header cells +
   alignment in `properties`) whose *rows* are child `table_row` blocks
   (`parent_id` onto the table block — the tree already supports it). This is
   not just a size fix, it is the retrieval-correct granularity: a search hit
   on a tracking table returns the relevant *row*, not a 235 KB blob, and the
   workspace UI renders `table` blocks through the library `table` component.
   The three failing files (largest blocks 235,716 / 298,677 / 182,746 chars)
   all fail *because* they are mega-tables; row-splitting dissolves them into
   blocks of ordinary size. Watch one bound: E2's file is already 998 blocks
   against `MAX_BLOCKS` 5,000 (`document_door.py:61`) and row-splitting
   multiplies block count — the corpus should be spot-checked at import
   (increment 5), but a 3,000-row single table is not in the measured corpus.
2. **Oversized-block reporting at put — warn, never refuse.** After parse,
   count blocks whose text exceeds a stated constant (proposal: 8,000 chars —
   the nomic budget, the tighter of the two live embedders per CLAUDE.md's
   endpoint table) and surface the count plus the worst offender's size in
   `PutResult` (`document_door.py:PutResult`), the REST/MCP responses (an
   additive field; the SDK generator regenerates it, invariant 17), and the
   `document_filed` event payload. Refusal is wrong here: 27 corpus files
   exceed the nomic budget and refusing would block the import; invariant 14
   demands honest reporting of degradation, not a new failure mode. The
   constant is a stated conservative floor, not a per-embedder probe — a probe
   would put a model call on the parse path for a warning.
3. **Defer embed-time chunking, with the reason on record.** Doc 16 §3
   *prescribes* the general fix — "Long blocks that exceed the embedder's
   token window are chunked at embed time via payload spans … rather than by
   splitting a block into sub-blocks, because a block is the citation unit
   and must stay one object" (`docs/design/16-documents-and-pkm.md`, §3) — so
   the brief's worry that splitting "breaks block↔vector 1:1" is answered by
   the design doc itself: the block stays one object; the *vectors*
   multiply. But the shipped partition template cannot hold it:
   `PRIMARY KEY (block_id, fingerprint)`
   (`backend/app/services/embedder_registry.py:87-95`) admits one vector per
   block, and child tables are minted at runtime by `CREATE TABLE IF NOT
   EXISTS`, so a template change reaches only *new* partitions — deployed
   ones need a reconciliation pass (not a baseline regen, since these tables
   are registry-created, but a real migration of live partitions plus a
   `search_blocks` dedup change: one block must not occupy N result slots).
   After fixes 1-2 the residual oversized population is giant code fences and
   the rare monster paragraph — real but not the measured defect. Defer until
   a measured need, with the put-time warning as the honest stopgap.
4. **Rider on the same parser increment: YAML frontmatter.** Detect a leading
   `---\n…\n---` fence before tokenising and file it into
   `documents.properties` (e.g. `properties.frontmatter`) instead of letting
   commonmark misparse it into a level-2 heading (the brief's verified
   misparse). Code-only.
5. **The `<!-- BEGIN/END GENERATED -->` loss** (5 `html_block` tokens dropped,
   `document_parsers.py:211-213`) needs no parser change once §5 lands: the
   markers survive in the stored raw content even though no block carries
   them, and the only consumers are regeneration scripts that operate on the
   raw text anyway.

## 5. Round-trip fidelity

**Decision: raw-content storage and an optimistic-concurrency precondition
are required *now*; version history is deferred. Neither required item needs
a schema change; the clean `content` column rides the next baseline regen
that happens for other reasons.**

Why round-trip is required rather than nice-to-have: with git out of the loop,
`document_get` → edit → `document_put` becomes the agents' *only* edit cycle,
and today that cycle launders parse loss into the artifact. `document_get`
serves block text with markdown syntax already stripped (a heading's `#`
markers are gone by design — `document_parsers.py` module docstring: "the
inline content with the `#` marker already stripped"), tables flattened,
`hr`/`html_block` dropped, and heading levels unreachable (`BlockRow` at
`document_door.py:601` carries no `properties`). The first round trip degrades
the document; every subsequent one compounds it. `blocks.char_span` indexes
into a source that is never stored (`documents` has `content_hash` only,
`0001_baseline.py:1282`), so even citation anchors point into text nobody can
fetch. A store that cannot hand back what was put in is a read-index, not a
filesystem replacement — and the filesystem replacement is the assignment.

- **Raw content now, without a regen**: `put_document` writes the source under
  a reserved key in `documents.properties` (e.g. `properties["$content"]`),
  merged server-side with whatever `properties` the caller passed (the upsert
  already overwrites properties wholesale — `repositories/documents.py:81-88`
  — so the merge lives in the door, one place). A new `include_content` flag
  on `GET /documents/{id}` / `document_get` returns it verbatim. Size is safe:
  `MAX_CONTENT_CHARS` is 1,000,000 (`document_door.py:60`) and a 1 MB text
  value TOASTs fine in jsonb. This is explicitly a **bridge**, labelled as
  such in the door's docstring: the clean shape is a `documents.content TEXT`
  column, which is a baseline-regen item and therefore rides the *next regen
  another epic already pays for* (schema changes serialise through one owner
  per epic; triggering a drop/recreate + three-pass restore of production for
  one column is the cost axis this proposal exists to avoid).
- **Optimistic concurrency now**: an optional `expected_hash` on
  `put_document` (both doors): if supplied and the stored `content_hash`
  differs, refuse — 409 on REST (the conventions doc's conflict shape), a
  structured error on MCP. No schema change; `content_hash` exists. Forced by
  the same concurrency fact as §3: parallel lanes over a LWW upsert
  (`repositories/documents.py:81`) silently drop writes today. Get-then-put
  with `expected_hash` turns the silent loss into a retryable conflict.
- **Version history deferred, and what the owner loses by deferring**: no
  rollback after a bad agent overwrite, and no content diff between filings —
  `document_filed` events record *that* and *when* a document changed, never
  what it said before. The bound on the loss: the nightly `darkmem-backup`
  dump caps worst-case content loss at one day, and `expected_hash` removes
  the concurrent-clobber route, leaving only "an agent deliberately put the
  wrong content" — which versioning would mitigate but agents' own session
  context usually recovers. If demand materialises, a `document_revisions`
  table is a baseline-regen item and should be decided together with the
  `content` column so the two ride one regen.

## 6. Sequencing

| # | Increment | Schema | Effort | Risk |
|---|---|---|---|---|
| 0 | **Reachability**: repoint `/root/.claude.json` mcpServers.darkmem from the v0.2.0 box (`192.168.0.195`) to local v1.4.0, mint an API key, add the bearer header | none (config only) | hours | none — but *everything below is moot without it*; the measured config reaches a server with zero document routes |
| 1 | **Watchable progress**: Checkpoints tab project filter + poll interval; agent convention "checkpoint per step" (doc, not code) | no schema change | 1-2 days | low — UI + a query param on an existing read |
| 2 | **Parser fixes**: `table`/`table_row` block types (taxonomy edit), table parsing with row children, frontmatter capture, oversized-block warning in `PutResult`/responses/event payload; regenerate SDKs | no schema change | 2-4 days | medium — parser changes re-shape trees for *re-filed* docs only (existing rows untouched until re-put); the additive response field walks through the SDK generator |
| 3 | **Round-trip**: `$content` bridge + `include_content` + `expected_hash` 409 | no schema change | 2-3 days | low-medium — door-level; upsert semantics gain a refusal path that needs both-door tests |
| 4 | **Workspace UI**: `projects` route family, Artifacts + Progress tabs, shared document components, `/documents` project pin | no schema change | 4-6 days | low — composition over shipped routes and darkraise-ui primitives |
| 5 | **Corpus import + conventions doc**: one-shot script filing `docs/` into project `darkmem` (uri = repo path), spot-checking block counts and oversized warnings; the agent-facing convention doc (project naming, uri scheme, checkpoint discipline, ledger shape: headings-and-prose, never mega-tables) | no schema change | 1-2 days | low — import is re-runnable via the `(project, uri)` upsert |
| 6 | **Backup off-host**: `backup_ship` JobRegistry job; destination config row + settings panel; encryption before egress; post-upload read-back verification; per-destination retention | no schema change | 4-6 days | low — `scripts/backup.sh` and `scripts/restore.sh` already carry the hard parts |
| 7 | **Backup worker**: `READ_ONLY` posture enforced at the door layer + reported on `/auth/security-posture`; scheduled restore-from-latest; snapshot inventory UI | no schema change | 3-5 days | low-medium — the posture must hold at the API, not in the UI |
| 8 | **Personal workspace**: stable block identity (diff-and-update), granular block verbs, per-block re-embed, the editing UI | **baseline regen** | weeks | highest — inverts doc 16 §7 and rewrites the ingest path |
| D1 | *Deferred*: `documents.content` column (+ optional `document_revisions`) | **baseline regen** — rides the next regen another epic pays for | small once riding | regen cost is the risk; never trigger it for this alone |
| D2 | *Deferred*: embed-time chunking via payload spans (doc 16 §3) | no baseline regen, but a live-partition reconciliation (PK change on runtime-created `block_embeddings__*` tables) + `search_blocks` dedup | 3-5 days | medium — touches invariant-2 territory; wait for measured need after Inc 2 |
| D3 | *Deferred, owner decision*: MCP `document_list`. The 2026-08-23 ruling keeps `documents.reads` REST-only on the reasoning that "the agent's list-shaped read of this corpus is the ranked `document_search`" (`docs/two-door-parity.md:55`). That reasoning predates the artifact-store requirement, where deterministic enumeration ("what task files exist?") is load-bearing and semantic search is the wrong verb. Interim: the convention doc has agents maintain an index document per project. If that chafes, revisit the ruling — a ruling amendment, not a quiet tool addition | no schema change | small | ruling change requires the owner |

**Smallest first increment with visible value: 0 + 1.** After it, the owner
opens the Activity Checkpoints tab (later the project workspace) in a browser
and watches a running session's step-by-step notes update — the decisive
requirement — using only shipped storage and doors.

## 7. What NOT to build

- **A task/issue/kanban model.** Owner conceded it is heavier than the need;
  any new table is a regen; the checkpoint + ledger pair covers the actual
  requirement (watch a run, keep a record).
- **New `EVENT_TYPES` for progress.** The needed values exist
  (`events.py:187-193`); free-form agent prose does not belong in the
  unpurgeable audit substrate (T2.59 retention ruling).
- **A second documents table or "artifacts channel".** Regen cost for an
  isolation property `project` already enforces (§1).
- **A revisions table now.** Deferred with its loss stated (§5); decide it
  together with the `content` column so both ride one regen.
- **Block-level diffing / partial re-embed.** The door's whole-document cost
  model is a stated design (`document_door.py` module contract); the workload
  that punished it (per-step ledger appends) is removed by §3's split, so
  the remaining edit frequency (milestones) doesn't justify the complexity.
- **A CRDT or multiplayer editing.** §8 commits an editor — reversing doc 16 §7,
  which is an owner ruling to record, not a quiet addition — but the personal
  workspace is single-user. Last-write-wins per block under §5's `expected_hash`
  precondition is sufficient, and staying off CRDT is what keeps §8 weeks rather
  than months. No canvas.
- **A bespoke backup UI.** The worker runs the same image read-only (§9), so the
  viewer is a posture flag plus a restore loop, not a second frontend to keep in
  step with the first.
- **An in-app restore button.** Restore replaces the live database; a one-click
  path to that in a web UI is a footgun with no upside over the scripted,
  confirmed command that already exists.
- **Fusing blocks into memory retrieval, or a keyword/RRF arm for block
  search now.** The firewall is structurally enforced
  (`tests/test_block_retrieval.py`; `block_query.py:1-50` records
  semantic-only as doc 16 §4's v1 stance). A progress reader navigates by
  outline and uri, not by ranked search; if artifact search quality is later
  measured wanting, a keyword arm inside the block channel is the doc-16
  "later refinement" — it never touches the composition.
- **Git sync-back.** Ruled out by the owner; a bridge would reintroduce the
  dual-source-of-truth problem the move exists to end.
- **A new LLM purpose or dream job** for progress digesting. The eight-purpose
  set is closed by discipline (doc 16 §9's own "not now" stance for a
  document-answer purpose applies a fortiori here), and invariant 15 keeps
  new Tier-C jobs out of this lane's hot path anyway.

## 8. Personal notes as a Notion-style workspace

**Decision: the personal surface becomes a block editor — in-browser editing,
nested pages, drag-to-reorder, slash commands, save-as-you-type. This is the
largest item in the plan and the only one that reverses an existing design
decision. Owner ruling, 2026-08-31.**

**It amends doc 16 §7**, which deliberately declines to commit an editor, canvas
or CRDT. Recording that as a ruling rather than letting it arrive as a quiet
feature is the point of this section.

### 8.1 The blocker is block identity, not the editor

Filing a document strips every block row and inserts a fresh set, minting a new
`id` for each (`strip_blocks` then a plain INSERT —
`backend/app/services/document_ingest.py:246`,
`backend/app/repositories/documents.py`). Block N in the new tree is not the same
object as block N in the old one even when its text never changed; the door's own
contract states this as the cost model ("the cost of editing one paragraph in a
large document is the same as filing it from scratch").

Notion-style editing needs the exact inverse: a block is a durable object that is
mutated, reordered, linked to and cited. So this feature **forces** three changes
the rest of this spec is built to avoid:

1. **Stable block identity** — match incoming blocks against existing rows and
   update in place, instead of dropping and re-minting the tree.
2. **Granular block verbs** — create / update / move / delete *a block*. The door
   today is whole-document `put` only.
3. **Per-block re-embed** — embed what changed, not all N rows.

### 8.2 What it repays

Those same three changes remove the cost model every other section works around.
Editing one paragraph stops costing a full re-file, which is the measured reason
§3 rules a ledger out as the live progress surface. This is not purely new cost:
it repairs the door's sharpest limitation and every surface benefits, including
the agent path, which keeps its simpler whole-document `put` on top of the new
diffing ingest.

Ordering note: §8 supersedes part of §3's reasoning once it lands. §3's split
(checkpoints live, ledger durable) is still right — concurrency and the audit
argument stand on their own — but its *cost* argument weakens, and that should
be re-read rather than carried forward on trust.

### 8.3 Scope boundary

Single-user. Last-write-wins per block under §5's `expected_hash` precondition is
sufficient; **no CRDT, no multiplayer, no canvas**. Staying off CRDT is what keeps
this weeks rather than months, and nothing in the requirement asks for concurrent
human editors.

### 8.4 Cost

**Baseline regeneration.** Under the greenfield ruling that is now an acceptable
price rather than a blocking one, but it still means dropping and recreating every
deployed database, re-seeding `admin_password_hash` and the eight
`llm_purpose_configs` rows, and re-hashing the schema guard. It should ride one
regen together with D1's `documents.content` column — deciding them separately
would pay the same cost twice.

---

## 9. Backup, off-host and restorable

**Decision: keep the shipped dump and restore scripts as the core, add pluggable
destinations, encryption, verification and a read-only backup worker. No schema
change. Owner ruling, 2026-08-31.**

### 9.1 More works today than the gap suggests

`scripts/backup.sh` dumps through the compose service, writes to a `.part` name
the retention glob cannot match, and **renames only after confirming pg_dump's
completion marker** — which catches the truncated stream that still exits 0 and
that `pipefail` cannot see. It prunes to `BACKUP_KEEP` (14), NUL-delimited so a
filename with a newline cannot shift the keep/delete boundary. `scripts/restore.sh`
verifies the same marker, replays into a side database, and swaps it in only on
success, so a dump that aborts partway leaves the live database untouched. The
systemd timer runs nightly at 03:30 with `Persistent=true`.

The gap is everything *after* the file lands on the host that runs the database:
no off-host destination, no encryption, no proof an uploaded snapshot is
restorable, one global retention for all destinations, and no UI visibility.

### 9.2 Destinations

| Provider | Transport | Notes |
|---|---|---|
| Local path | filesystem | What ships today; stays the default and the fast restore path |
| Another machine | ssh / rsync | Key-based; host key pinned in config, never trust-on-first-use |
| S3-compatible | S3 API | One client covers AWS, R2, B2, MinIO — bucket and endpoint are config, not code |
| Backup worker | https | A second darkmem that receives snapshots and serves them read-only (§9.4) |

### 9.3 Where the config lives, and why not in the job schema

Scheduling moves into `JobRegistry` as a `backup_ship` job, which buys the cron
expression, the per-job `asyncio.Lock`, run history and the Jobs-page surface at
no cost. **The systemd timer stays as the floor**: if the app is down it is the
only thing still taking backups, and a backup system that depends on the service
it protects is not one.

**Destination config cannot live in the job's `config_schema`.** `FieldDescriptor`
types `default` as `int` (`backend/app/services/job_registry.py:89-98`), so a job's
generic config surface carries a retention count or an interval but not a bucket
name, an endpoint or a credential. Destinations therefore live in a dedicated
`config` row with their own settings panel — the same shape the LLM providers use,
and the same place per-repo git tokens already live
(`git_token_<repo_id>`, `backend/app/services/repo_manager.py:330`). Neither path
needs a schema change.

### 9.4 Three rules the design turns on

1. **Encrypt before egress.** A snapshot on someone else's disk is a credential
   dump, an append-only events journal and every personal note in the system.
   Encryption is not optional for anything but the local path.
2. **Uploaded is not restorable.** Every shipped snapshot is read back and
   checksummed against what was sent, and the outcome is journalled. An unverified
   backup is a belief, not a backup — the same reasoning that put the completion
   marker in `backup.sh`, applied one hop further out.
3. **Retention is per destination.** Fourteen nightlies locally and a longer
   weekly chain off-host are different policies; one global `BACKUP_KEEP` cannot
   express that.

### 9.5 The worker needs no new UI

The worker runs **the same darkmem image** in a read-only posture against a
restored snapshot. darkmem already serves its own SPA from `:8000`, so the viewer
is a flag and a restore loop rather than a second frontend to build and keep in
step.

It needs one new thing: a `READ_ONLY` posture that **refuses writes at the door
layer**, not in the UI, so the guarantee holds for anything reaching the API, and
that reports itself on `GET /auth/security-posture` the way `cookie_secure_clamped`
already does. The worker restores the newest verified snapshot on its own
schedule, which makes opening it answer both questions at once: what did the data
look like, and does the restore actually work.

### 9.6 Restore stays break-glass

No in-app restore button. Restoring replaces the live database, and a one-click
path to that in a web UI is a footgun with no upside — the operation is rare,
consequential and already scripted safely. The UI's job is to make the decision
informed: snapshot inventory per destination, age, size and verification status,
plus the exact command. `restore.sh` gains `--from <destination>` so pulling a
remote snapshot is not a manual download first.

### 9.7 How this squares with the greenfield ruling

Data stays disposable across *schema* changes; that ruling is unchanged. But once
personal notes (§8) live only in darkmem, the **content** is not disposable even
though the schema is. Backup and restore are what keep the greenfield ruling
survivable: drop and recreate the database freely, then restore the content — which
is only safe if the restore is known to work, which is exactly what the worker
proves continuously rather than at the moment you need it.

---

## Invariant check

- **Inv 13/15/17, doc 16 firewall**: nothing here adds workers, reaches a
  dream job from capture/retrieval, bypasses the one-service-layer rule, or
  gives blocks a route into composition or the vault. New/changed REST fields
  and the `expected_hash`/`include_content` params flow through
  `sdks/generate.py`.
- **Inv 23**: the two "full list" surfaces this touches — `BLOCK_TYPES` and
  the two-door parity table — are edited in the same increments that change
  their referents (Inc 2, D3).
- **Taxonomy-first**: `table`/`table_row` land in `BLOCK_TYPES` before the
  parser emits them; no event vocabulary widens.
- **§8/§9 against the invariants**: §8 changes the ingest path's write shape but
  adds no retrieval route, no vault writer and no composition edge, so
  `tests/test_block_retrieval.py`'s three structural scans are untouched; its
  block-identity change must keep `block_embeddings__<slug>`'s
  `ON DELETE CASCADE` and the per-fingerprint discipline (invariant 2) intact.
  §9 adds one `JobRegistry` job under the existing per-job lock (invariant 13
  unaffected: still one worker), and its `READ_ONLY` posture is a door-layer
  refusal, which keeps it on the one-service-layer rule (invariant 17) rather
  than a per-door guard.
- **Doc 16 §7 is amended by §8**, deliberately and on an owner ruling. Doc 16 §3's
  embed-time-chunking prescription remains unimplementable until D2 moves the
  partition PK; §8's per-block re-embed does not change that, because it reduces
  how often a block is embedded, not how a long one is split.
- **One disagreement with the brief**: option (b) in its question 4 says the
  table plugin "needs a `table` block type — taxonomy-first", which is true,
  but it is worth stating that this is *cheaper than it sounds*: the closure
  is code-side only (`blocks.type` is unconstrained TEXT,
  `0001_baseline.py:1313`), so the taxonomy-first step is a list edit, not a
  schema event. And its option (c) worry ("breaks block↔vector 1:1?") is
  already adjudicated by doc 16 §3 in favour of chunking — the real blocker
  is the shipped partition PK, which is why (c) is deferred rather than
  rejected.

# Darkmem as the project-artifact store and progress surface

Date: 2026-08-31
Status: design, revised 2026-08-31 after an adversarial review (2 blockers, 6
majors). §5 and §8 are rewritten, §9's worker is redesigned, §2 and §9.7 are
amended. Increments 0, 1, 2 and 5 are planned
(`docs/superpowers/plans/2026-08-31-*.md`); 3, 4 and 6 are plannable against this
revision; §8 is gated on two owner decisions and is not plannable.

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
| 2 | UI | New `projects` route family (workspace: Artifacts + Progress tabs); `/documents` stays the personal surface and gains a project pin; Activity route unchanged. **Amended**: increment 4 carries a backend change — the projects endpoint is memories-only | no schema change |
| 3 | Progress | Live progress = `session_checkpoints` + its existing `events` trail, rendered by the already-half-built Checkpoints UI; durable ledger = a document under a shape convention. Prior events-task proposal rejected as a write surface, accepted as a render path. Owner's single-file position accepted for the durable record, rejected as the live surface | no schema change |
| 4 | Oversized blocks | (a) enable table parsing with new `table`/`table_row` block types (taxonomy-first, code-only), (b) oversized-block warning in `PutResult` + journal, (c) defer doc 16 §3's embed-time chunking | no schema change |
| 5 | Round-trip | **Revised**: the properties bridge is cut. `documents.content TEXT` is taken **now**, before any corpus exists; `expected_hash` is a SQL compare-and-set, not a check; versions still deferred | **baseline regen, taken now** |
| 6 | Sequencing | Nine increments below; increment 0 (reachability) + 1 (watchable progress) is the smallest visible win | — |
| 7 | Not build | Task model, revisions table now, agent-path block diffing, CRDT/multiplayer, block↔memory fusion, git sync-back, events task vocabulary, second table, bespoke backup UI, in-app restore button | — |
| 8 | Personal workspace | **Redesigned**: granular block verbs need **no** schema change (the client holds block ids); content-first vs block-first ingest resolves the §5 collision; nested pages and the editor ADR are undecided and gate it | none for the verbs; nested pages TBD |
| 9 | Backup | **Revised**: the job runs `pg_dump` over the stack network, never the host script; the worker's read-only guarantee moves from the door layer to a **Postgres role**, with the receiver and restore loop as separate processes | no schema change |

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

### 2.1 Amendment 2026-08-31 — increment 4 is not backend-free

Two review findings re-rate this section. It was written as composition over shipped
routes; it is not.

- **M2 — `GET /api/v1/projects` is memories-only.** Confirmed: it groups
  `Memory.project` and returns `{name, memory_count}`
  (`backend/app/api/routes/projects.py:38-49`). It has nothing to do with the
  `projects` registry table, and the first draft's pairing of the two citations was
  substantively wrong. **A project holding only documents is invisible to it**, which
  is precisely what increment 5 creates. The project index and the switcher both need
  a scope source that unions the corpora — documents and checkpoints as well as
  memories — so increment 4 carries a **backend change**, and its "low risk /
  composition only" rating is withdrawn.
  Note the same trap one surface earlier: feeding the *checkpoint* tab's project
  filter from this endpoint would hide a checkpoint-only project in its own filter.
  Increment 1's plan derives its options from the loaded runs instead.
- **m1 — the tree truncates.** The list route clamps `limit` to 200
  (`backend/app/api/routes/documents.py:279`) against a corpus of ~465 parseable
  files. "Client-side grouping over the ≤200-row page, which is fine at this corpus
  size" was self-refuting: one page holds under half the corpus and the tree silently
  drops the rest — the invariant-14 shape this spec polices elsewhere. Either
  paginate-and-stitch in the hook or raise the clamp; do not ship the silent version.

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

## 5. Round-trip fidelity — AMENDED 2026-08-31

**Amendment: the `properties["$content"]` bridge is CUT. `documents.content TEXT`
is taken now, before increment 5 imports any corpus. `expected_hash` becomes a SQL
compare-and-set.** The original decision deferred the column to avoid a baseline
regeneration; the review (M3, M6, m3) showed the bridge pays more than it saves,
and the greenfield ruling of the same day removed the cost it was avoiding.

### 5.1 Why the bridge was wrong

The bridge existed for exactly one reason: a `content` column meant a baseline
regeneration. Four findings, all confirmed, retire it:

- **M3 — it dodges a regen the spec itself schedules.** Deferring to "the next regen
  another epic pays for" is not deferral if this spec's own later increments need one.
  Building a bridge and then unbuilding it is two pieces of work to avoid one.
- **M6 — the reserved key is forgeable.** `properties` is caller-supplied, so a
  caller can write `$content` itself. Server-side merge in the door is a rule about
  a namespace the wire format does not own.
- **m3 — old rows never acquire it.** The `UNCHANGED` gate writes no properties, so
  a byte-identical re-push never backfills.
- **Unstated in the review, and decisive on its own:** a 1 MB TOASTed jsonb value
  sits on `documents`, which `_LIST_SQL` and every `documents.*` read touch. A
  dedicated column is the same storage with none of the read amplification.

**The greenfield ruling is what makes this cheap.** `CLAUDE.md`'s "Greenfield until
the freeze" says data is disposable and no migration is owed. Prod holds **0
documents**. Regenerating the baseline now costs a drop, a recreate, a re-seed of
`admin_password_hash` and the eight `llm_purpose_configs` rows, and a schema-guard
re-hash — with nothing to preserve. **It will never be cheaper than it is before
increment 5 imports the corpus**, which is the argument for doing it now rather than
deferring it again.

### 5.2 The shape

- `documents.content TEXT NULL` — the source of record, written by `put_document`,
  returned by `GET /documents/{id}` and `document_get` behind an `include_content`
  flag (default off, so no existing reader pays for it).
- `blocks.char_span` becomes meaningful for the first time: it has always indexed
  into a source the schema did not keep.
- `documents.content_hash` keeps its change-gate role, unchanged.

### 5.3 `expected_hash` is a compare-and-set, not a check

**M1, confirmed.** Reading `content_hash` and then writing if it matches is
check-then-act: two lanes both read the same hash, both proceed, and the second
still clobbers the first — which is the exact race the precondition exists to close.
The predicate must ride the write:

```sql
INSERT INTO documents (...) VALUES (...)
ON CONFLICT (project, uri) WHERE uri IS NOT NULL DO UPDATE SET ...
  WHERE documents.content_hash = CAST(:expected_hash AS text)
RETURNING id
```

A zero-row result is the conflict: 409 on REST (the conventions doc's conflict
shape), a structured refusal on MCP. `expected_hash` stays optional — omitting it
is the current last-writer-wins behaviour, which is correct for a first filing and
for a caller that genuinely owns the document.

### 5.4 Version history — still deferred, loss restated

Deferred, and now decided *with* the column rather than after it, so the two do not
each demand a regeneration. What is lost: no rollback after a bad overwrite, and no
content diff between filings — `document_filed` records that and when a document
changed, never what it said before. The bound: the nightly dump caps worst-case loss
at one day, and §5.3 removes the concurrent-clobber route, leaving only a deliberate
bad write, which an agent's own session context usually recovers. If demand
materialises, `document_revisions` is a further regeneration — cheap while greenfield,
and cheapest taken alongside any other schema change.

## 6. Sequencing

| # | Increment | Schema | Effort | Risk |
|---|---|---|---|---|
| 0 | **Reachability**: repoint `/root/.claude.json` mcpServers.darkmem from the v0.2.0 box (`192.168.0.195`) to local v1.4.0, mint an API key, add the bearer header | none (config only) | hours | none — but *everything below is moot without it*; the measured config reaches a server with zero document routes |
| 1 | **Watchable progress**: Checkpoints tab project filter + poll interval; agent convention "checkpoint per step" (doc, not code) | no schema change | 1-2 days | low — UI + a query param on an existing read |
| 2 | **Parser fixes**: `table`/`table_row` block types (taxonomy edit), table parsing with row children, frontmatter capture, oversized-block warning in `PutResult`/responses/event payload; regenerate SDKs | no schema change | 2-4 days | medium — parser changes re-shape trees for *re-filed* docs only (existing rows untouched until re-put); the additive response field walks through the SDK generator |
| 3 | **Round-trip**: `documents.content` column (baseline regen) + `include_content` + `expected_hash` compare-and-set 409 | **baseline regen** | 2-3 days | low while prod holds 0 documents; **must land before increment 5** |
| 4 | **Workspace UI**: `projects` route family, Artifacts + Progress tabs, shared document components, `/documents` project pin | no schema change | 4-6 days | low — composition over shipped routes and darkraise-ui primitives |
| 5 | **Corpus import + conventions doc**: one-shot script filing `docs/` into project `darkmem` (uri = repo path), spot-checking block counts and oversized warnings; the agent-facing convention doc (project naming, uri scheme, checkpoint discipline, ledger shape: headings-and-prose, never mega-tables) | no schema change | 1-2 days | low — import is re-runnable via the `(project, uri)` upsert |
| 6 | **Backup off-host**: `backup_ship` job running `pg_dump` over the stack network (+ `postgresql-client` in the image, a dump volume, distinct prefixes/retention from the systemd path); destination config row + settings panel; encryption; post-upload verification | no schema change | 5-7 days | low-medium — the process boundary (M4) is designed out, not worked around |
| 7 | **Backup worker**: read-only enforced by a `SELECT`-only **Postgres role**; separate receiver process; restore loop outside the app swapping databases; `DARKMEM_READ_ONLY` demoted to job-disarm + write-on-read skip | no schema change | 5-8 days | medium — enforcement layer moved after B1; plannable against §9.5 |
| 8 | **Personal workspace**: block verbs + block-first ingest. **Gated on two owner decisions** (nested-pages shape, editor ADR) and not plannable until both land | none for the verbs | **no estimate** — withdrawn as unfounded over an unmade technology decision | highest — inverts doc 16's span-anchor doctrine, so doc 16 §5 is affected as well as §7 |
| ~~D1~~ | **Resolved into increment 3** — the column is taken now (§5). `document_revisions` stays deferred and would ride any later regeneration | — | — | — |
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

## 8. Personal notes as a Notion-style workspace — REDESIGNED 2026-08-31

**The first draft claimed a baseline regeneration while naming no schema change,
left "nested pages" undesigned, and did not reconcile its block verbs with §5.
Review finding B2, upheld. This section replaces it.** The feature is not cut; its
design is.

### 8.1 Block identity needs no schema change

B2's sharpest point is that the regen claim had no referent, and it is right —
because the identity problem was misdiagnosed. `blocks.id` is already a stable uuid
primary key. Nothing about the *schema* prevents a durable block; what re-mints ids
is `put_document`'s strip-and-rewrite, which is a **code** path
(`document_ingest.py:246` then a plain INSERT).

An editor does not need the server to infer identity, because **the client already
holds it**: it fetched the blocks, so it knows their ids. Granular verbs take real
ids and mutate the addressed row:

| Verb | Shape |
|---|---|
| `block_update` | `(block_id, text, properties?)` — text and properties only |
| `block_insert` | `(document_id, parent_id?, after_block_id?, type, text)` |
| `block_move` | `(block_id, new_parent_id?, after_block_id?)` |
| `block_delete` | `(block_id)` — subtree cascades via `parent_id` |

No diffing, no matching heuristic, no schema change. `order_index` is `INTEGER`, so
a move renumbers its sibling run — O(siblings), not O(document), and a fractional
index is an optimisation to reach for only if a measurement demands it.

### 8.2 Two ingest directions, which is what §5 collides with

B2 is right that block verbs leave `content_hash`, `content` and `char_span`
undefined, and the resolution is to stop pretending one direction serves both
callers:

- **Content-first (agents, unchanged).** `document_put` takes text, parses it to
  blocks, stores `content` (§5) and `content_hash`. `char_span` indexes into
  `content` and is exact.
- **Block-first (the editor, new).** The block verbs are authoritative. `content` is
  **regenerated from the block tree** after each mutation and `content_hash`
  recomputed from it; `char_span` is **dropped to NULL** on any block the editor
  touches, because a span into a regenerated serialisation is a coordinate into a
  document that no longer exists.

Which direction a document uses is recorded on the row and is **not** a per-call
choice: a `document_put` against a block-first document is a refusal, not a silent
overwrite of someone's editing session. This is the reconciliation §5 was missing.

**Consequence for doc 16, stated because the first draft missed it.** Doc 16's
provenance doctrine treats block ids as churning and the span as the durable anchor.
Block-first documents invert exactly that — the id is durable and the span is gone —
so doc 16 §5's lift must either refuse block-first documents as citation sources or
carry a second anchor kind. **§7 is not the only amendment; §5 of that doc is
affected too.** Left open deliberately: it is a doc-16 owner decision, and pretending
otherwise is what produced this section's first draft.

### 8.3 What is genuinely undesigned, and stays that way until decided

- **Nested pages.** A page inside a page is either a `documents.parent_id`
  (a regeneration, and a second tree beside `blocks.parent_id`) or a block of a new
  `page_ref` type pointing at a document (no regeneration, taxonomy-first). **Not
  decided here.** It is the only part of §8 that might need schema, and it needs its
  own ADR.
- **The editor technology.** M5 is upheld: `darkraise-ui` ships no block editor, so
  this is a build-or-adopt decision (TipTap/ProseMirror, Lexical, or hand-rolled
  contenteditable) with a real bundle-size and control trade-off. **No estimate is
  given in this spec, and the previous "weeks" is withdrawn as unfounded** — an
  estimate over an unmade technology decision is a guess wearing a number.

### 8.4 Scope boundary, unchanged

Single-user. Last-write-wins per block under §5.3's compare-and-set. No CRDT, no
multiplayer, no canvas.

### 8.5 Status

**Not plannable.** Two decisions gate it: the nested-pages shape and the editor ADR.
Neither is a research task; both are owner calls. §8.1's verbs and §8.2's two
directions *are* plannable once those land, and neither needs a regeneration.

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

### 9.3 Where the config lives, and how the job reaches pg_dump — AMENDED

Scheduling moves into `JobRegistry` as a `backup_ship` job, which buys the cron
expression, the per-job `asyncio.Lock`, run history and the Jobs-page surface.

**The job does NOT invoke `scripts/backup.sh`.** Review finding M4, confirmed: the
app container has no `pg_dump`, no compose binary, and no mount reaching either the
host's docker socket or a dump directory — its only mounts are the repo-data volume
and `/host-repos`. A job shelling out to the host script crosses a process boundary
that does not exist.

The fix is to stop crossing it. Prod networking is bridge, so the API already reaches
Postgres across the stack network: **add `postgresql-client` to the image and have
the job run `pg_dump -h postgres` over that connection**, writing to a
dump volume. `scripts/backup.sh` stays exactly as it is for the host-side systemd
path — two independent producers, which is the point of §9.3's floor argument.

Two riders this creates and the first draft did not see:
- **m4 — the per-job lock does not serialize against the systemd timer.** They are
  different processes; the `asyncio.Lock` binds only in-process. Give the two
  producers **distinct filename prefixes and distinct retention sets** so neither
  prunes the other's artefacts, rather than pretending they coordinate.
- The image grows by the client package. Stated, not hidden.

**Destination config cannot live in the job's `config_schema`.** `FieldDescriptor`
types `default` as `int` (`backend/app/services/job_registry.py:89-98`), so the
generic job-config surface carries a retention count or an interval but not a bucket
name, an endpoint or a credential. Destinations live in a dedicated `config` row with
their own settings panel — the shape the LLM providers use, and where per-repo git
tokens already live (`repo_manager.py:330`). No schema change either way.

### 9.4 Three rules the design turns on

1. **Encrypt before egress.** A snapshot on someone else's disk is a credential dump,
   an append-only events journal and every personal note in the system. Not optional
   for anything but the local path.
2. **Uploaded is not restorable.** Every shipped snapshot is read back and checksummed
   against what was sent, and the outcome journalled — the completion-marker
   reasoning in `backup.sh`, applied one hop further out.
3. **Retention is per destination.** Fourteen nightlies locally and a longer weekly
   chain off-host are different policies; one global `BACKUP_KEEP` cannot express it.

### 9.5 The backup worker — REDESIGNED 2026-08-31

**The first draft put a `READ_ONLY` posture at the door layer. It cannot hold, and
the finding (B1) is upheld in full.** Confirmed against the code: `entrypoint.sh`
writes at every boot (alembic, then the schema-guard stamp); `main.py` calls
`job_registry.start_all()` unconditionally, arming all 23 jobs — `buffer_flush`
would make live LLM calls against credentials restored from the snapshot, and
`backup_ship` would ship snapshots of snapshots; and reads write, including
`fact_access_stats`' UPSERT on every fact read. A door-layer guard sits above all
three. **A posture that silently fails to hold is worse than none**, so the
enforcement moves to a layer that cannot be bypassed.

**Enforcement is the Postgres role, not the application.**

- The worker's app connects as a role holding `SELECT` and nothing else. A write
  that escapes any application guard fails at the database, which is the only
  enforcement point below every code path.
- Boot writes are separated from serving: the restore loop (below) migrates and
  stamps the snapshot **as a privileged role while the app is stopped**, so
  `entrypoint.sh`'s writes happen outside the serving window. The app then starts
  with migrations skipped.
- `DARKMEM_READ_ONLY` survives, demoted to what it can honestly do: **do not arm the
  job registry**, and **skip the known write-on-read paths** (`fact_access_stats`,
  access bumps) so they degrade to a no-op instead of erroring under the read-only
  role. It is ergonomics over an enforced floor, not the guarantee itself. It still
  reports on `GET /auth/security-posture`, the way `cookie_secure_clamped` does.

**The receiver is a separate process, not the darkmem app.** B1 is right that an
https endpoint receiving snapshots is itself a write door; putting it inside a
read-only instance is a contradiction. It is a small independent service writing to
the dump directory, sharing nothing with the app but the filesystem.

**The restore loop runs outside the app, and swaps databases rather than mutating
one.** `restore.sh` replays into a side database and RENAMEs, which terminates
connections — doing that under a live app is the collision B1 names. The worker
instead restores into a new database, stops the app, points it at the restored one,
and starts it. The schema guard is satisfied because the privileged migrate-and-stamp
step ran first.

**What the worker still delivers:** the same image, the same SPA, no second frontend
— which was the good part of the original idea and survives the redesign intact.

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
though the schema is.

**Amendment 2026-08-31 (M3).** The first draft said backup makes the greenfield rule
survivable by letting you "drop and recreate the database freely, then restore the
content". That is unsupported as written: `restore.sh` replays a **full** dump, which
carries the old schema wholesale, so it restores a database *as it was* — it cannot
move content across a baseline regeneration. The two operations are unrelated:

- **Backup/restore** answers disaster recovery — same schema, earlier point in time.
- **Crossing a regeneration** would need a content-level transform-restore that does
  not exist and is **not scoped by this spec**.

So the honest statement is narrower: backup bounds *loss*, not *schema change*. Under
the greenfield ruling a regeneration still discards the data, and that is accepted —
which is exactly why §5 takes the `content` column **now, while there is nothing to
lose**, rather than after a corpus exists.

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
- **§8/§9 against the invariants (revised 2026-08-31)**: §8's block verbs add no
  retrieval route, no vault writer and no composition edge, so
  `tests/test_block_retrieval.py`'s three structural scans are untouched; a
  `block_delete` still cascades `block_embeddings__<slug>` per invariant 2, and
  block-first documents must not reach doc 16 §5's lift until that doc decides
  its anchor question (§8.2). §9's job runs under the existing per-job lock, but
  **that lock does not reach the systemd producer** — they are separate processes,
  so the two are separated by filename prefix and retention set, not by mutual
  exclusion (m4). Invariant 13 is unaffected: still one worker. The worker's
  read-only guarantee is **no longer a door-layer refusal** — B1 showed that cannot
  hold — so invariant 17 is not the relevant frame; enforcement is a Postgres role
  beneath every code path, with the app flag demoted to ergonomics.
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

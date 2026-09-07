# Personal notes as a daily driver — a Notion/Obsidian-shaped workspace

Date: 2026-09-07
Status: design. Supersedes AS §8 of
`2026-08-31-project-artifact-store-design.md` (the personal-workspace section)
and retakes four of its rulings, each recorded in §14. Revised 2026-09-07 after
a second adversarial pass (2 blockers, 9 majors, all applied). The increments of
§12 are separately plannable; none is planned yet. No code is written by this
document.

Grounding: every claim about shipped behaviour below was checked by opening the
file named beside it during the design pass. Paths are relative to the repo
root. **`AS §n` cites the 2026-08-31 artifact-store spec; a bare `§n` is a
section of this document.** The greenfield ruling (`CLAUDE.md`, "Greenfield until the freeze") holds,
so no item here owes a migration — but a baseline regeneration still means
dropping and recreating every deployed database and re-seeding
`admin_password_hash`, the eight `llm_purpose_configs` rows and the two
provider rows, and `schema_guard` re-hashes on the next boot.

**Approach:** best-of-3 dispatched (markdown-source/CodeMirror vs
block-store/TipTap vs no-new-framework), then **skip 3** applied on
verification — AS §8.3 had already taken the editor and
nesting decisions, so the ring was not the decider and no judge pass was spent
ranking it. The scouts' drafts became evidence for *retaking* AS §8.3, and the
shipped design is a graft of all three: scout C's block-first verb reuse and
single-table storage, scout A's CodeMirror substrate, scout B's observation that
the artifact-store spec already ruled here. Two advisory passes (Fable) reviewed the
result. The first produced ten findings, folded in where they land: the inert
catalogue column (§1), the missing metadata verb (§4), the compare-and-set that
AS §8.4 assumed but no verb carries (§5), the tag sweep that would delete note
tags hourly (§7), and the conversion refusal that would make imported notes
uneditable (§12). The second reviewed the written spec and returned two
blockers and nine majors, all applied: the block verbs take parsed fields
rather than source and nothing in the tree writes `uri` at all (§4), a `put`
racing a rename reopens the M-3 overwrite (§4.3), the merge seam destroys a
list item's children and the insert seam renumbers its run (§3), the
read-only worker cannot both raise and answer (§8), the `html` type carries an
XSS decision (§12), the seed belongs at boot rather than in the wizard (§1),
increment 1 is four lanes with a forced order (§12), and two claims of mine
were simply false — `update_document` writes `title` but not `uri`, and the
SDK generator never sees this epic (Invariant check).

## Decision summary

The `#` column indexes decisions, not sections; each is argued in the section
named beside it below.

| # | Question | Decision | Schema cost | § |
|---|---|---|---|---|
| 1 | Space | One `documents` table; notes live in a minted `notes` project carrying an enforced `projects.kind='personal'` singleton | one column + partial unique index | §1 |
| 2 | Nesting | Derived from the `uri` path, unchanged from §8.3 | none | §2 |
| 3 | Editor | Per-block CodeMirror 6 over each block's markdown source; markdown stays both the storage and the edit format | none | §3 |
| 4 | Write path | The four shipped block verbs + a server-side `source` mode on `block_update`; one new `document_update` metadata verb in two shapes on both doors | none | §4 |
| 5 | Concurrency | `expected_hash` on all four block verbs; `include_hash` on the MCP blocks read; a serialised client mutation queue | none | §5 |
| 6 | Links | `document_links`, extracted inside `_mutate` after serialisation; unresolved links persist as stubs | new table | §6 |
| 7 | Tags | `document_tags` against the existing `tags` table, with the orphan sweep and histogram widened | new table | §7 |
| 8 | Search | `blocks.search_vector` fused with the cosine arm under RRF inside the block channel | one generated column + GIN | §8 |
| 9 | Attachments | In-database store, its own increment | new table + route | §9 |
| 10 | Revisions | Taken now rather than deferred, because this regen is the moment §5.4 named | new table | §10 |
| 11 | Import | New `html` block type, taxonomy-first, landed before any corpus exists | none (code-side) | §12 |
| 12 | Not build | Table grid, column layouts, canvas, database views, CRDT, git sync-back, block diffing, note→vault lift, new LLM purpose, transclusion | — | §13 |

---

## 1. The space: one table, a real personal project

**Decision: personal notes are `documents` rows in the shared table, belonging
to one project row whose `kind` is `personal`. The project is named `notes` and
is minted at setup.**

AS §1 chose one table separated by `project`, and that holds: the separation is enforced in SQL, not by convention —
`documents.project` is NOT NULL, identity is
`UNIQUE (project, uri) WHERE uri IS NOT NULL`, `BlockQueryService.search` takes
`project` with no default, and the ANN probe applies the predicate in-query
rather than post-fetch. A second table would duplicate the five-verb surface,
its two doors, the firewall tests and the embed partition family to reproduce
an isolation property that already exists.

What changes is that the space stops being a string:

```sql
ALTER TABLE projects ADD COLUMN kind TEXT NOT NULL DEFAULT 'project'
    CHECK (kind IN ('project', 'personal'));
CREATE UNIQUE INDEX ux_projects_one_personal ON projects (kind)
    WHERE kind = 'personal';
```

The singleton is the point: the database refuses a second personal space, which
a `properties.kind` label cannot do. `projects` already carries a
`properties JSONB` that would have taken the label at zero schema cost; it is
rejected precisely because it is unenforceable.

**`default` is not the personal project.** `memories.project` defaults to
`default`, so every agent capture made without a project would land in the
personal space. A new `notes` row avoids that. This reverses AS §1's "Personal
notes: stay in `default`" and AS §2's "`/documents` stays the personal
surface"; see §14.

**Two backend reads make `kind` visible, and without them the column is inert.**
`GET /api/v1/projects` is derived from a union over `memories`, `documents` and
`session_checkpoints` (`app/api/routes/projects.py`, `_UNION_SQL`, whose
docstring says "Derived, never a registry") and never reads `projects` at all.
So the catalogue must LEFT JOIN `projects` for `kind`, `ProjectSummary` must
carry it, and `SELECT name FROM projects WHERE kind = 'personal'` joins the
`names` CTE so an empty personal project still appears. Both project-shaped
surfaces then filter it out: the project switcher and `/documents`, neither of
which should list the notes space as an ordinary project.

**The seed goes at boot, not in the wizard.** `project_registry.register` runs
on every capture and `backfill_projects` runs at boot, both
`INSERT ... ON CONFLICT DO NOTHING` — so a memory captured into `notes` before
any seed mints the row with `kind` defaulting to `'project'`, and a later
DO-NOTHING seed would leave it wrong forever. The seed therefore sits beside
`backfill_projects` as
`INSERT INTO projects (name, kind) VALUES ('notes','personal')
ON CONFLICT (name) DO UPDATE SET kind = 'personal'`, which is idempotent,
self-heals that race, survives a regeneration without a runbook step, and is
skipped under `DARKMEM_READ_ONLY` like every other boot writer. A test fixture
mints it for the suite. The wizard and the runbook re-seed list are **not**
sites for it.

**`kind` gates no write, and that is accepted.** An agent naming
`project='notes'` on a capture lands a memory in the personal space; nothing
refuses it. The column separates surfaces, not permissions.

## 2. Nesting, unchanged

Nesting is the `uri` path — `notes/projects/darkmem.md` sits under
`notes/projects/`. AS §8.3 took this decision and its reasoning stands: `uri` is
required on both doors, so every document already carries a path, and
`documents.parent_id` would cost a regeneration to duplicate what the path
encodes while creating a second hierarchy that can contradict `blocks.parent_id`.

The consequence this design must own is that **a folder rename is N document
renames**, which §4's metadata verb performs in one transaction.

## 3. The editor: per-block CodeMirror 6

**Decision: one CodeMirror 6 instance for the focused block, holding that
block's markdown source. Unfocused blocks render through the `react-markdown`
stack already in `package.json`.**

AS §8.3 chose "markdown-source blocks, no framework" and named the ceiling it was
accepting: "no drag handles, no table editing and no slash menu come for free…
adopting a framework is a decision to retake with evidence, not a default to
drift into." The owner has now stated that ceiling is binding — a slash menu,
drag-to-reorder and inline formatting are non-negotiable for a daily driver —
which is the evidence that clause asked for.

The retake is narrower than it looks, and the narrowness is the argument.
AS §8.3's case against a framework was round-trip fidelity: a WYSIWYG editor
models the document as its own JSON tree and converts markdown in and out on
every edit, and that conversion is where fidelity dies on a corpus whose
purpose is faithful round-trip. **CodeMirror is a text editor**, so storage
format and edit format remain identical and there is no conversion step to get
wrong. TipTap/ProseMirror/Lexical stay rejected on the original reasoning.

Per-block rather than one buffer over `documents.content`, for two reasons that
are structural rather than aesthetic. Real DOM blocks give real drag handles
and drop targets. And a per-block edit writes through the block verbs, so it
embeds one block — a whole-document buffer would write through `document_put`,
which strips and re-embeds every block, and the fix for that (block-level
diffing) is on AS §7's do-not-build list.

Extensions: `@codemirror/lang-markdown` with `codeLanguages` for nested code
highlighting; live-preview decorations that hide markers outside the caret's
own node; an autocomplete source on `/` at an empty line for block types; a
second source on `[[` backed by note titles; widget decorations rendering real
checkboxes over `- [ ] `; line decorations for `> [!note]` callouts; a keymap
for bold/italic/link plus a selection-triggered format bar.

Cross-block behaviour is hand-wired, and this is the largest unbounded item in
the design: Up/Down at a block edge moves focus, Enter at the end is
`block_insert`, Backspace at the start merges into the previous block,
Tab/Shift-Tab re-parents a list item via `block_move`. Notion carries the same
seams; it is a known quantity of work, not a research problem, but it is where
an estimate will move.

**Two of those seams do not survive contact with the shipped verbs, and both
are specified here rather than left to the implementer.** `delete_block`
removes the target's whole `_subtree` (`block_verbs.py`, `_subtree`), so
"merge = `block_update` then `block_delete`" destroys a merged list item's
children. Merge therefore takes a `keep_children` flag on `block_delete`, which
re-parents the doomed block's children onto its parent in the same `apply`
pass; a per-child `block_move` loop is rejected because it is N transactions
where one will do. And Enter after an ordered list item must copy
`properties.marker` onto the new block: `_same_list_run` in the serialiser
splits a run whose markers differ, so an inserted item that falls back to
`DEFAULT_LIST_MARKER` silently renumbers the list above it.

**Stated ceiling of this design, so it is not discovered later:** tables are
edited as markdown source, not as a grid. There are no column layouts, no
canvas, and no live-rendered page transclusion.

**darkraise-ui gap recorded** (per `CLAUDE.md`'s library-first rule): the
library ships `textarea` and `image-editor` and no code or markdown editor of
any kind, which is why CM6 enters the tree. `command` (slash menu, Ctrl+K),
`tree-view` (sidebar), `tags-input` (tag browser) and `kbd` are used as shipped.

## 4. The write path, and the verb that was missing

Notes are **block-first** documents in AS §8.2's existing sense: the block verbs
are authoritative, `content` and `char_span` are regenerated by the serialiser
on each mutation, and `document_put` against a note is refused exactly as it is
for any block-first document.

### 4.1 The verbs take parsed fields, not source — so the server parses

`update_block` takes `(block_id, text, type?, properties?)` where `text` is
**marker-stripped**, and `BlockUpdateRequest` mirrors it. The shipped editor
closes that gap in the browser with `promote(source)`
(`frontend/src/features/documents/components/block-editor.tsx`), whose own
comment calls it "a real duplication" of `block_serializer`. It handles
heading, divider, list, quote, code and paragraph only — no `table`,
`table_row`, no `html`, no nested prefix (a served nested item's `source`
carries its indent, because `emit_lines` records `start` before writing the
prefix), and a paragraph source containing a blank line is written back as one
block whose text re-parses as two, so the tree and `content` diverge with no
guard, because `reproduces_source` never re-runs on a block-first row.

Per-block CodeMirror inherits every one of those holes, so the design closes
them at the server instead:

**`block_update` gains a `source` mode**, mutually exclusive with
`text`/`type`/`properties`. The server strips the block's own container prefix,
runs `parse_markdown` on the remainder, and applies the result **only when it
yields exactly one top-level draft**; anything else is refused with
`source_not_one_block` (422 on REST, an envelope from the tool). A split is
therefore an explicit `block_insert` by the editor, never an accident of
typing. `promote` is retired with its duplication.

### 4.2 Nothing in the tree can rename a document

`_UPDATE_DOCUMENT` (`app/repositories/documents.py`) writes `title`,
`source_type`, `content_hash`, `content` and `properties` — **and no `uri`**;
`upsert_by_uri` writes `title` too, on insert and on conflict. So `uri` has no
writer at all after a row is inserted, and `title` has two. A converted note can
never be renamed, moved or pinned: three of v1's stated requirements.

**Decision: one metadata verb in two shapes.**

- `PATCH /api/v1/documents/{document_id}` → 200, body `{title?, uri?, pinned?,
  tags?}`. Every field is optional; an absent field leaves its column
  untouched. A present `tags` **replaces** the document's tag set rather than
  merging, because a merge-only verb cannot remove a tag. `pinned: true` writes
  `now()`, `false` writes NULL. `project` is deliberately not a field — moving a
  document between spaces is not a rename, and allowing it here would let one
  call cross the boundary AS §1 rests on.
- `POST /api/v1/documents/rename`, body `{project, uri_prefix,
  new_uri_prefix}`, for a subtree. The server selects
  `uri = :prefix OR uri LIKE :prefix || '/%'` and rewrites all of them in one
  transaction — the earlier draft said the verb takes "the list of a subtree's
  ids" alongside a single `uri`, which is unimplementable, since N rows need N
  distinct paths.
- MCP `document_update` carries both shapes as modes of one tool.

`PATCH` rather than `PUT` follows `docs/api-rest-conventions.md`; the
per-route status map in `test_rest_conformance.py` gains both rows.

**Refusals, both defined rather than left to the constraint.** A rename onto an
occupied path violates `ux_documents_project_uri` and answers `uri_conflict`
(409 / envelope). A rename of a block-first document is permitted — it touches
no block — but `document_put` at the vacated path is not (below).

**`document_updated` lands in `EVENT_TYPES` before the emitter ships**; the
vocabulary holds only `document_filed` and `blocks_edited` today, and widening
is taxonomy-first.

**Lock order, because a subtree rename and a link rewrite touch two tables.**
`SELECT id FROM documents WHERE ... ORDER BY id FOR UPDATE` — the same lock
`_mutate` takes, in a deterministic order so two subtree renames cannot
deadlock — then `UPDATE documents`, then `document_links`: rewrite `target_uri`
by `target_document_id` for resolved links, then re-resolve stubs whose
`target_uri` now matches a live document.

### 4.3 The race the new verb reopens

`put_document` locks by `(project, uri)`, and **at a path with no row there is
nothing to lock**. A `put` aimed at a path that a rename is concurrently
vacating passes the direction check against nothing, then `upsert_by_uri`'s
`ON CONFLICT DO UPDATE` blocks on the rename's uncommitted unique entry and
fires against the renamed block-first row — writing `properties` wholesale,
erasing `ingest_direction`, and stripping the editor's blocks. This is review
finding M-3's race, reopened by the new verb.

The direction refusal therefore rides the upsert **as well as** preceding it —
two guards covering two different paths, not one replacing the other.

**Amended 2026-09-07, before implementation.** This section previously said the
refusal rides the upsert *rather than* preceding it, and that "a check before
the statement is check-then-act". Both halves are wrong, and following them
would have caused the data loss this section exists to prevent.
`ingest_document` (`app/services/document_ingest.py`) branches on whether the
document already exists: an existing `(project, uri)` is written through
`update_document` / `_UPDATE_DOCUMENT`, and **`upsert_by_uri` runs only when
the resolve found nothing**. A predicate on the upsert's `ON CONFLICT` is
therefore reached only in the race, never on the ordinary path — so removing
the pre-check would leave every plain `document_put` over a converted note
unguarded, writing `properties` wholesale and stripping its blocks. The
pre-check is also not check-then-act for an existing row: it runs *after*
`_LOCK_DOCUMENT_BY_URI ... FOR UPDATE` (`document_door.py`), and `_mutate`
locks the same row by id, so the two serialise. It is check-then-act only in
the case where there is no row to lock, which is exactly the case the upsert
predicate covers.

So both, each named with the path it guards:

- **The existing-row path** keeps the locked pre-check in `put_document`,
  unchanged. This is the ordinary refusal and the one that fires in practice.
- **The vacated-path race** gains
  `DO UPDATE ... WHERE documents.properties->>'ingest_direction' IS DISTINCT
  FROM 'blocks'` on `upsert_by_uri`. Note the statement ends `RETURNING id`
  with `.scalar_one()`: a predicate-excluded conflict returns zero rows and
  raises `NoResultFound` before any rowcount is read, so the call site must
  use `.scalar_one_or_none()` and raise `DocumentIsBlockFirst` on the None.
  The zero-row outcome is otherwise unambiguous — a non-conflicting INSERT
  returns its row.

This verb also closes a gap agents have today: nothing lets an agent re-file a
renamed artifact.

## 5. Concurrency

AS §8.4 says last-write-wins per block "under AS §5.3's compare-and-set". **That
is not true of the block verbs today** — `_WRITE_DOC` carries no predicate. The
design makes it true:

- `expected_hash` on all four verbs, not two: `insert` and `move` rewrite
  `content_hash` as much as `update` does. On `DELETE` it is a query parameter,
  not a body field.
- `_DOC_META` must select `content_hash`; it does not today, and the compare
  has nothing to read otherwise.
- `content_hash` served on the blocks read. REST's `DocumentBlocksResponse`
  gains the field additively. **MCP needs a shape decision, not a field**:
  `document_get` answers a bare JSON array, and an array cannot carry a hash, so
  it gains `include_hash` returning `{content_hash, blocks}` — the same
  object-under-a-flag shape `include_content` already established, recorded in
  the parity table beside it. Without this an MCP agent cannot precondition its
  first edit.
- A **serialised client mutation queue**. The shipped editor fires a commit and
  an insert synchronously; with a precondition the second call would carry a
  stale hash and 409 against its own predecessor.

The lock in `_mutate` is the first statement of the transaction, so a compare
placed after it is CAS-equivalent and needs no restructuring.

**Undo.** CodeMirror's history is per instance, so an insert, a delete or a
move has no client-side undo at all — the revision history of §10 is the only
recovery path for those. Stated here because a user will expect Ctrl+Z to
cross a block boundary and it will not.

## 6. Links

`document_links (id, source_document_id → documents ON DELETE CASCADE,
source_block_id → blocks ON DELETE CASCADE, target_document_id → documents
ON DELETE SET NULL, target_uri TEXT NOT NULL, link_text TEXT)`.

`[[target|text]]` lives inline in block text, never as a block type. A nullable
`target_document_id` is what makes a link to a note that does not exist yet a
first-class stub — it renders as an offer to create that note, which is how both
products behave.

**Link grammar, defined so two implementers cannot disagree.** `[[target]]`
and `[[target|display]]` take a **project-relative uri with the `.md` suffix
omitted**; `target_uri` stores the canonical uri, suffix included. Titles are
display text only and never a resolution key — Obsidian resolves basenames, and
an implementer reading "autocomplete note titles" would have built that.
Extraction covers `paragraph`, `list`, `quote` and `heading` text and never
`code` or `html` blocks, where `[[` is source, not a link.

**Resolution is scoped to the linking document's own project.** A note may not
link into a project's artifacts and an artifact may not link into the notes
space: `(project, uri)` is the identity, so an unscoped resolution would be
ambiguous the moment two projects hold the same path, and a cross-space link
would make the project boundary — the one thing §1 rests on — porous.

**Extraction runs inside `_mutate` after serialisation**, where the tree is
already in memory and the pass is already O(document), and inside
`document_ingest`, so a content-first filing's links resolve on the same terms
(within its own project) rather than only an editor's. Targets resolve
by uri. Any new module that reads blocks must be added to
`BLOCK_CHANNEL_MODULES` in `tests/test_block_retrieval.py` — an unclassified
module is a hole in the scan, by that test's own stated rule — and must not
enter any `VAULT_WRITERS` closure or reach `app.services.pipeline`.

Backlinks are one query on `target_document_id`. Unlinked mentions are a
`search_vector` match on the note's title minus what is already linked,
computed on read.

**The graph is drawn from `document_links` alone**, never `entities` or
`entity_relations`: blocks are never lifted into L1, and the firewall scan
enforces it.

## 7. Tags

`document_tags (document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
PRIMARY KEY (document_id, tag_id))` against the existing generic
`tags (id SERIAL, name UNIQUE, category)` table, mirroring `memory_tags`.

Tag writes go through `set_tags`' existing writer path rather than a second
one, so `tag_category(name)` and `TAG_NAME_MAX_LENGTH` apply on both doors.

**Two shipped behaviours must widen in the same change or notes lose their
tags hourly.** `RelationalRepository.prune_orphans`
(`app/repositories/relational.py`) deletes every tag with no `memory_tags` row,
and `tag_orphan_cleanup` runs it hourly: a note-only tag and its links would
vanish within the hour under the cascade, or the job would error every tick
without one. The tag histogram counts `memory_tags` only, so the `#tag` browser
would undercount. Both widen to consider `document_tags`.

## 8. Search

`blocks.search_vector tsvector` (generated, GIN-indexed) fused with the existing
cosine arm under RRF inside `BlockQueryService.search`, importing `RRF_K` from
`app/services/rank_fusion.py` — the AST guards fail the build on a second RRF
constant bound anywhere else. The generated expression blanks `code` and `html`
blocks: their text is source, and indexing it makes every note that mentions a
function name a hit for it.

This retakes AS §7's "no keyword/RRF arm for block search now", which named
itself the sanctioned later refinement if search quality was measured wanting. A
daily driver makes it wanted. The arm stays inside the block channel and touches
no composition path, so the three structural scans are unaffected.

Three consequences, decided here rather than left implicit:

- **Ordering carries a separate `rrf_score`;** `score` keeps its raw per-arm
  meaning. Folding the fused value into `score` is the trap `CLAUDE.md` already
  warns memory-search consumers about. `test_the_channel_ranks_its_own_corpus`
  asserts ordering by `score` and moves to the new key.
- **An embedder failure still raises** with the read-only flag off:
  `test_an_embedder_failure_raises_rather_than_reading_as_no_match` pins it, and
  a search that quietly answers on one arm is indistinguishable from a complete
  one.
- **The read-only worker skips the embed rather than attempting it.** Those two
  sentences would contradict each other if the worker *tried* the arm, so it
  follows the shipped pattern: `hybrid_search` already sets `vector=None` under
  `settings.read_only`, and `BlockQueryService.search` does the same, running
  keyword-only and reporting `semantic_ran=False` on both doors' envelopes — the
  articles-channel precedent. `refuse_when_read_only` then comes off the
  document-search route **only**; the QA and reembed routes keep it, because
  they dial out.

Benchmark before committing to a generated column: `_PLACE` rewrites every
block row of the document on each mutation, so each edit produces a new row
version per block and fresh GIN entries with it (HOT applies per row, and only
rows whose indexed columns did not change keep it — the bloat concern stands
either way, since autovacuum does not run on this host). If `EXPLAIN` shows that
dominating, a trigger firing only on a `text` change replaces the generated
column.

## 9. Attachments

An in-database store — table plus upload route plus serving path — with
paste-to-upload in the editor and a widget rendering the image inline.

In-database rather than on disk because the backup design deliberately keeps one
restore story and avoids off-database state. **The cost is real and must be
sized in the same increment:** dumps are already ~250 MB, two producers keep 14
copies each, and the `local` destination already runs at `retention_keep=3`
because it double-counts the systemd floor. Attachment bytes inflate every
nightly dump on both producers. The increment states measured dump growth and
whether the local retention drops again.

## 10. Revisions

`document_revisions (id, document_id → documents ON DELETE CASCADE, content
TEXT NOT NULL, content_hash TEXT NOT NULL, created_at)` — a **full `content`
snapshot** per commit, not a block delta, because the serialiser already
produces exactly that string on every mutation and a delta format would be a
second representation to keep faithful. The snapshot is the **post-image**: the
state the document reached, so restoring a revision is a write of exactly what
is stored rather than a reconstruction.

AS §5.4 deferred version history and said to decide it alongside anything
riding a regeneration; this is that regeneration, and retrofitting it later
costs another drop-and-recreate. A daily driver where a bad edit an hour ago is
unrecoverable is not one. It is also the only undo an insert, delete or move
has (§5).

`document_put`'s UPDATED path writes a revision too. A wholesale overwrite of a
document is exactly the "bad overwrite" AS §5.4 named, and it is the case a
per-block history would otherwise miss entirely.

Two bounds ride with it, for the reason §9 gives about dumps. Consecutive
commits inside a coalescing window (default 5 minutes) **replace** the window's
snapshot rather than appending — a per-keystroke-batch editor would otherwise
write a full copy of the note every few seconds. And retention (default 50
revisions per document) is trimmed **in the same statement, inside `_mutate`'s
savepoint** — deliberately not a job: a new `JobRegistry` entry would move the
24-job roster that `test_main_registers_the_full_direct_job_roster` derives from
`main.py`, and `CLAUDE.md`'s count with it, for work that belongs in the
transaction that caused it.

## 11. Surfaces, doors and parity

`/notes` is a top-level route with its own workspace: uri-derived tree with
drag-to-move, editor, and a right rail carrying the outline, backlinks and tags.
Ctrl+K over `command`; pinned and recents at the top of the tree. `/documents`
remains the corpus-wide browser and stops being the personal surface.

Parity under the 2026-08-23 ruling (`docs/two-door-parity.md`), whose test is
whether a verb generates or labels anything:

| Capability | Door | Reason |
|---|---|---|
| Create a note | both | `document_put`, already two-door |
| Rename / move / pin / tag | both | new `document_update`; an agent re-filing a renamed artifact has no verb either |
| Keyword search | both | rides `document_search`, no new surface |
| Backlinks read | REST | a browsing read over one document, under the `documents.reads` precedent |
| Graph | REST | a rendered candidate view, under the `graph.candidate_read` precedent |
| Recents / pinned list | REST | human picker state, under the `project.catalog` precedent |
| Attachment upload | REST | a browser paste path; an agent files content, not binaries |

Every single-door row needs its reason written into the parity table — **at
least** 80 characters (`_MIN_REASON_CHARS` is a floor, not a ceiling: the test
refuses a reason too short to be one) and free of schedule words — or
`test_door_parity` fails. `include_hash` (§5) is recorded in the same table
beside `include_content`.

One new MCP tool moves the enumeration counts by one: `TOOL_SCOPES` (it is a
`capture`-scope writer), the prompt roster, `CLAUDE.md`'s 12/25/38 counts, and
the SDK regeneration.

## 12. Sequencing

Increment 1 is four lanes with a forced order, not one increment:

- **1a — the `html` block type** (code-only: `BLOCK_TYPES`, the parser's
  `html_block` branch, a serialiser branch, and the `reproduces_source` count
  check). Must precede 1b's re-import.
- **1b — the baseline regeneration**, all six schema objects in one
  drop-and-recreate under one owner (`projects.kind` + singleton index,
  `document_links`, `document_tags`, `blocks.search_vector`,
  `documents.pinned_at`, `document_revisions`, and an index on
  `documents (project, updated_at)` for recents — none exists), plus the
  catalogue join, the boot seed, and then the corpus re-import.
- **1c — the compare-and-set lane** (`expected_hash` on all four verbs,
  `_DOC_META` selecting `content_hash`, `content_hash` served on both doors'
  blocks reads including MCP's `include_hash`). Independent of 1b.
- **1d — the tag sweep and histogram widened.** Must precede 1e.
- **1e — `document_update`** in both shapes, `document_updated` in
  `EVENT_TYPES`, the rename refusals, and the upsert-riding direction predicate
  of §4.3.

Two ordering constraints, each with a concrete failure if inverted. **1a before
1b's re-import**, or every html-bearing document files with no `html` row and
the count check then refuses to convert it, needing
`scripts/reparse_documents.py --force` to recover. **1d before 1e**, or the
first `document_tags` row written by the new verb is deleted within the hour by
`prune_orphans`, which removes any tag no `memory_tags` row references.

Then:

2. **Workspace shell.** `/notes` route, tree with drag-to-move, create, rename,
   delete, pin. Usable as a notes app; editing is still the shipped textarea.
3. **The editor.** Per-block CM6, live preview, slash menu, inline formatting,
   checkboxes, callouts, the cross-block seams of §3, drag, the mutation queue,
   and `block_update`'s `source` mode with `promote` retired.
4. **Links.** `[[` autocomplete, extraction, backlinks panel, unlinked
   mentions, stub creation.
5. **Finding.** The RRF keyword arm, Ctrl+K, tag browser, recents/pinned, the
   read-only worker's document-search refusal lifted.
6. **Attachments.** Table, upload route, serving path, paste handler, dump
   sizing.
7. **Graph.** Over `document_links`, reusing the existing renderers.

**Why `html` leads, and what it is not.** `block_serializer.reproduces_source`
refuses conversion on any raw HTML block or link-reference definition, and
`_mutate` raises `DocumentNotConvertible` — so an imported Obsidian or Notion
note carrying `<img>`, `<details>` or an HTML comment would be readable and
permanently uneditable, because the documented escape (`document_put`) is
refused on block-first rows and the notes UI exposes no other path. The
serialiser's guard is **not** relaxed; it gets a block type to be faithful
with, which means `_UNREPRESENTABLE_TOKENS` drops `html_block` *and* the
count-check tuple gains `("html_block", "html")` — without the second half a
document filed before the widening converts lossily instead of refusing.

The earlier claim that this is free "before any corpus exists" was wrong:
production already holds the artifacts corpus (446 files). What makes it free
is that 1b re-imports that corpus anyway, and `CLAUDE.md` records why the
re-import is the thing that matters — widening a block type obliges a
re-import rather than a redeploy, as adding `divider` left 201 filed documents
carrying `---` with no divider row.

**`html` blocks render as escaped source**, through the `code` path with
language `html`. The SPA's markdown pipeline carries no `rehype-raw`, so raw
HTML is escaped today; an implementer making `<img>` and `<details>` "work"
would add it, and that is the first place an imported file or a capture-scoped
key executes script under the operator's session cookie. Live HTML rendering is
a separate owner decision behind `rehype-sanitize`, not a detail of this
increment.

## 13. What NOT to build

- **A table grid, column layouts, or a canvas.** The stated ceiling of §3.
- **Database / board / calendar views.** A different product; nothing here
  forecloses it.
- **CRDT or multiplayer.** AS §8.4, unchanged. Single user, last-write-wins per
  block under §5's precondition.
- **Git sync-back.** Owner-ruled in AS §7; a bridge reintroduces the
  dual-source-of-truth problem.
- **Block-level diffing or partial re-embed.** AS §7, and unnecessary: block-first
  writes already embed one block.
- **Any route from a note into memories or the fact vault.** The firewall
  stands, structurally.
- **A new LLM purpose or dream job for notes.** AS §7; the eight-purpose set is
  closed by discipline.
- **Inline page transclusion.** AS §8.3 keeps `page_ref` available taxonomy-first
  later if it is wanted; it is not how nesting is modelled.

## 14. Rulings retaken

Four, each deliberate and recorded rather than drifted into:

1. **AS §8.3's "no framework"** — narrowed, not reversed. CM6 keeps markdown as
   both the storage and the edit format, so the round-trip argument that
   grounded the original ruling is untouched; TipTap/ProseMirror/Lexical remain
   rejected on it. Evidence for the retake is the owner declaring the accepted
   ceiling binding, which is the condition AS §8.3 itself set.
2. **AS §1's "personal notes stay in `default`"** and its "`properties.kind`
   label — deliberately not a column and not load-bearing" — reversed. The
   forcing fact is that `memories.project` defaults to `default`, so an
   unscoped agent capture would land in the personal space.
3. **AS §7's deferral of a keyword/RRF arm for block search** — taken now, on
   the condition AS §7 itself named.
4. **AS §5.4's deferral of version history** — taken now, because AS §5.4 said
   to decide it alongside a regeneration and this is one.

AS §2's "`/documents` stays the personal surface and gains a project pin" is
superseded by `/notes` as a consequence of (2).

## 15. Risks

- **The cross-block seams are specified, not solved.** §3 fixes the two that
  the shipped verbs actively break (subtree deletion on merge, marker loss on
  insert); selection across blocks, and undo across a block boundary, remain
  genuinely absent. Increment 3 is where an estimate moves.
- **Every commit is O(document) in row placement**, because `order_index` is a
  global reading order and `_PLACE` rewrites every block row of the document —
  AS §8.1's own 2026-09-01 correction. Every one of those is a new row version,
  and autovacuum does not run on this host, so the bloat is real even though
  the correctness is not in question. Acceptable for personal notes; a
  fractional index stays an optimisation to reach for only on measurement.
- **Frontend invalidation is currently corpus-wide**: every block verb
  invalidates `documentsAll`, which re-stitches up to 25 pages of the project.
  Dropped for `update` and `move` in increment 3.
- **Enumeration churn.** One new verb on two doors trips the parity test, the
  content-surface scoping test, REST conformance's status map, `TOOL_SCOPES`,
  the MCP auth test, `EVENT_TYPES`, `CLAUDE.md`'s counts and the block-type
  "eight" in `normalize_block_type`'s docstring. Only the full gate catches all
  of them.
- **The import ceiling.** Even with an `html` block type, the conversion guard
  is deliberately strict; a construct nobody anticipated still refuses rather
  than converting lossily. That is the correct failure, but the UI must explain
  it rather than showing a dead editor.
- **A stale-tree conversion is the quiet one.** A document filed before a block
  type existed carries the construct in its content and no row for it, and the
  count check is the only thing standing between that and silent loss. It is
  load-bearing in 1a, not a detail.

## Invariant check

- **Inv 13**: no workers added; the editor is a browser client.
- **Inv 15**: nothing here reaches a dream job from capture or retrieval, and
  no note becomes a fact — the vault-minting closure is untouched.
- **Inv 17**: **the SDK is untouched.** An earlier draft claimed
  `document_update` "flows through `sdks/generate.py`"; it does not —
  `VERBS` binds three verbs to `/api/v1/memories` routes only, so the generator
  emits nothing for this epic and `make generate` stays in the gate as a
  no-op check. The same correction applies to the MCP prompt roster, whose test
  matches `memory_*|code_*|list_repos` and so never sees `document_update`.
- **Inv 23**: the "full list" surfaces this touches are edited in the
  increments that change their referents, not after — `BLOCK_TYPES` and
  `normalize_block_type`'s "eight", `EVENT_TYPES`, the two-door parity table
  (including the `include_hash` row and the backlinks/recents/graph route
  list), `TOOL_SCOPES`, `BLOCK_CHANNEL_MODULES`,
  `content_surfaces.REST_ROUTES_WITHOUT_MEMORY_CONTENT`, the
  `test_rest_conformance` status map, and `CLAUDE.md`'s tool counts.
- **Doc 16 firewall**: the keyword arm lives inside the block channel; the link
  and tag modules read blocks and write their own tables, reaching no
  `KnowledgeTripleRepository` method outside the four-method read allowlist.
- **Taxonomy-first**: `html` lands in `BLOCK_TYPES` before the parser emits it;
  `document_updated` lands in `EVENT_TYPES` before the verb emits it.
- **Schema freeze**: unaffected. The freeze is still an event — after v1.0 and
  the owner's visual review — and this regeneration precedes it.


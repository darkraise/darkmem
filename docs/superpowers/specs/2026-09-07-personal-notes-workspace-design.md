# Personal notes as a daily driver — a Notion/Obsidian-shaped workspace

Date: 2026-09-07
Status: design. Supersedes AS §8 of
`2026-08-31-project-artifact-store-design.md` (the personal-workspace section)
and retakes four of its rulings, each recorded in §14. The seven increments of
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
the artifact-store spec already ruled here. One advisory pass (Fable) reviewed
the result and produced ten findings, all folded in where they land: the inert
catalogue column (§1), the missing metadata verb (§4), the compare-and-set that
AS §8.4 assumed but no verb carries (§5), the tag sweep that would delete note
tags hourly (§7), and the conversion refusal that would make imported notes
uneditable (§12).

## Decision summary

The `#` column indexes decisions, not sections; each is argued in the section
named beside it below.

| # | Question | Decision | Schema cost | § |
|---|---|---|---|---|
| 1 | Space | One `documents` table; notes live in a minted `notes` project carrying an enforced `projects.kind='personal'` singleton | one column + partial unique index | §1 |
| 2 | Nesting | Derived from the `uri` path, unchanged from §8.3 | none | §2 |
| 3 | Editor | Per-block CodeMirror 6 over each block's markdown source; markdown stays both the storage and the edit format | none | §3 |
| 4 | Write path | The four shipped block verbs, plus one new `document_update` metadata verb on both doors | none | §4 |
| 5 | Concurrency | `expected_hash` on all four block verbs; a serialised client mutation queue | none | §5 |
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
carry it, and the union must not drop a personal project holding zero
documents. The project switcher then filters the personal project out of the
project workspace, where it does not belong.

Seeding sites, all three of which must move together: the setup wizard's
finalize step (which seeds no projects today), the deployment runbook's
re-seed list, and a test fixture.

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
`block_insert`, Backspace at the start merges into the previous block
(`block_update` then `block_delete`), Tab/Shift-Tab re-parents a list item via
`block_move`. Notion carries the same seams; it is a known quantity of work,
not a research problem, but it is where an estimate will move.

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

**The gap AS §8 did not see: the block verbs cannot rename, move or pin.**
`_WRITE_DOC` (`app/services/block_verbs.py`) updates only `content`,
`content_hash` and the `ingest_direction` flag. The sole writer of
`documents.title` and `documents.uri` is `update_document`
(`app/repositories/documents.py`), reachable only through `put_document`, which
refuses block-first rows. As shipped, a converted note can never be renamed,
moved or pinned — three of v1's stated requirements.

**Decision: one new verb, `document_update`, on both doors**, taking
`title`, `uri`, `pinned`, `tags` — all of it document metadata, so it is one
verb rather than four. Every field is optional and an absent field leaves its
column untouched; a present `tags` **replaces** the document's tag set rather
than merging into it, because a merge-only verb cannot remove a tag and would
need a second verb to do it. On a `uri` change it also re-resolves `document_links`
stubs (§6) and rewrites `target_uri` for links pointing at the old path, in the
same transaction. The verb takes either one document id or the list of a
subtree's ids, so a folder rename is one call and one transaction rather than N
racing ones.

This also closes a gap agents have today: nothing lets an agent re-file a
renamed artifact.

## 5. Concurrency

AS §8.4 says last-write-wins per block "under AS §5.3's compare-and-set". **That is
not true of the block verbs today** — `_WRITE_DOC` carries no predicate. The
design makes it true:

- `expected_hash` on all four verbs, not two: `insert` and `move` rewrite
  `content_hash` as much as `update` does.
- `content_hash` served on `GET /documents/{id}` and on the blocks read, which
  `DocumentBlocksResponse` does not carry today — without it the editor has no
  hash for its first edit, the same gap AS §5.3 found for `put`.
- A **serialised client mutation queue**. The shipped editor
  (`frontend/src/features/documents/components/block-editor.tsx`) fires a
  commit and an insert synchronously; with a precondition the second call would
  carry a stale hash and 409 against its own predecessor.

The lock in `_mutate` is the first statement of the transaction, so a compare
placed after it is CAS-equivalent and needs no restructuring.

## 6. Links

`document_links (id, source_document_id → documents ON DELETE CASCADE,
source_block_id → blocks ON DELETE CASCADE, target_document_id → documents
ON DELETE SET NULL, target_uri TEXT NOT NULL, link_text TEXT)`.

`[[target|text]]` lives inline in block text, never as a block type. A nullable
`target_document_id` is what makes a link to a note that does not exist yet a
first-class stub — it renders as an offer to create that note, which is how both
products behave.

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

`document_tags (document_id, tag_id, PRIMARY KEY (document_id, tag_id))`
against the existing generic `tags (id SERIAL, name UNIQUE, category)` table,
mirroring `memory_tags`.

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
constant bound anywhere else.

This retakes AS §7's "no keyword/RRF arm for block search now", which named itself
the sanctioned later refinement if search quality was measured wanting. A daily
driver makes it wanted. The arm stays inside the block channel and touches no
composition path, so the three structural scans are unaffected.

Three consequences, decided here rather than left implicit:

- **Ordering carries a separate `rrf_score`;** `score` keeps its raw per-arm
  meaning. Folding the fused value into `score` is the trap `CLAUDE.md` already
  warns memory-search consumers about. `test_the_channel_ranks_its_own_corpus`
  asserts ordering by `score` and moves to the new key.
- **An embedder failure still raises rather than degrading to keyword-only.**
  `test_an_embedder_failure_raises_rather_than_reading_as_no_match` pins this,
  and a search that quietly answers on one arm is indistinguishable from a
  complete one.
- **The read-only worker's refusal of document search expires.** It refuses
  because the channel is cosine-only with no keyword arm (`app/api/deps.py`);
  once the arm exists the worker answers on it, as memory and code search
  already do there. Lifting that refusal is part of this change, not a
  follow-up.

Benchmark before committing to a generated column: every `_PLACE` rewrite is
non-HOT because `order_index` is indexed, so each edit inserts fresh GIN
entries for every block in the document. If `EXPLAIN` shows that dominating, a
trigger that fires only on a `text` change replaces the generated column.

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
second representation to keep faithful. AS §5.4 deferred version history and said
to decide it alongside anything riding a regeneration; this is that
regeneration, and retrofitting it later costs another drop-and-recreate. A
daily driver where a bad edit an hour ago is unrecoverable is not one.

Two bounds ride with it, for the reason §9 gives about dumps. Consecutive
commits inside a coalescing window (default 5 minutes) **replace** the window's
snapshot rather than appending — a per-keystroke-batch editor would otherwise
write a full copy of the note every few seconds. And a retention bound (default
50 revisions per document, swept by the existing `job_run_cleanup` sibling
pattern) keeps an actively edited note from dominating the nightly dump.

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

Every single-door row needs its reason written into the parity table, under 80
characters and free of schedule words, or `test_door_parity` fails.

One new MCP tool moves the enumeration counts by one: `TOOL_SCOPES` (it is a
`capture`-scope writer), the prompt roster, `CLAUDE.md`'s 12/25/38 counts, and
the SDK regeneration.

## 12. Sequencing

1. **Backend foundation.** Baseline regen (`projects.kind` + singleton index,
   `document_links`, `document_tags`, `blocks.search_vector`,
   `documents.pinned_at`, `document_revisions`, an index on
   `documents (project, updated_at)` for recents — none exists);
   the `notes` project seeded at setup and in the runbook; `document_update`
   on both doors; `expected_hash` on all four verbs; `content_hash` served on
   document reads; the tag sweep and histogram widened; the catalogue joined to
   `kind`; **and the `html` block type**.
2. **Workspace shell.** `/notes` route, tree with drag-to-move, create, rename,
   delete, pin. Usable as a notes app; editing is still the shipped textarea.
3. **The editor.** Per-block CM6, live preview, slash menu, inline formatting,
   checkboxes, callouts, cross-block keys, drag, the mutation queue.
4. **Links.** `[[` autocomplete, extraction, backlinks panel, unlinked
   mentions, stub creation.
5. **Finding.** The RRF keyword arm, Ctrl+K, tag browser, recents/pinned, the
   read-only worker's refusal lifted.
6. **Attachments.** Table, upload route, serving path, paste handler, dump
   sizing.
7. **Graph.** Over `document_links`, reusing the existing renderers.

**Why the `html` block type is in increment 1 rather than beside the import
work.** `block_serializer.reproduces_source` refuses conversion on any raw HTML
block or link-reference definition, and `_mutate` raises
`DocumentNotConvertible` — so an imported Obsidian or Notion note carrying
`<img>`, `<details>` or an HTML comment would be readable and permanently
uneditable, because the documented escape (`document_put`) is refused on
block-first rows and the notes UI exposes no other path. Widening the block type
is taxonomy-first and code-side only, but `CLAUDE.md` records that widening a
block type **obliges a re-import rather than a redeploy** — adding `divider`
left 201 filed documents carrying `---` with no divider row. Doing it before a
corpus exists makes that free. The serialiser's guard is not relaxed; it gets a
block type to be faithful with.

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

- **Cross-block editing seams** (merge, split, selection) are the unbounded
  part of increment 3.
- **Every commit is O(document) in row placement**, because `order_index` is a
  global reading order and `_PLACE` rewrites every block row — AS §8.1's own
  2026-09-01 correction. Acceptable for personal notes; a fractional index
  stays an optimisation to reach for only on measurement.
- **Frontend invalidation is currently corpus-wide**: every block verb
  invalidates `documentsAll`, which re-stitches up to 25 pages of the project.
  Dropped for `update` and `move` in increment 3.
- **Enumeration churn.** One new verb on two doors trips the parity test, the
  content-surface scoping test, REST conformance, `TOOL_SCOPES`, the MCP auth
  and prompt-roster tests, `CLAUDE.md`'s counts and the SDK generator. Only the
  full gate catches all of them.
- **The import ceiling.** Even with an `html` block type, the conversion guard
  is deliberately strict; a construct nobody anticipated still refuses rather
  than converting lossily. That is the correct failure, but it is a failure the
  UI must explain.

## Invariant check

- **Inv 13**: no workers added; the editor is a browser client.
- **Inv 15**: nothing here reaches a dream job from capture or retrieval, and
  no note becomes a fact — the vault-minting closure is untouched.
- **Inv 17**: `document_update` and the new REST fields flow through
  `sdks/generate.py`; the generator refuses a verb the contract does not serve.
- **Inv 23**: the "full list" surfaces this touches — `BLOCK_TYPES`, the
  two-door parity table, `TOOL_SCOPES`, `BLOCK_CHANNEL_MODULES` and
  `CLAUDE.md`'s tool counts — are edited in the increments that change their
  referents, not after.
- **Doc 16 firewall**: the keyword arm lives inside the block channel; the link
  and tag modules read blocks and write their own tables, reaching no
  `KnowledgeTripleRepository` method outside the four-method read allowlist.
- **Taxonomy-first**: `html` lands in `BLOCK_TYPES` before the parser emits it.
- **Schema freeze**: unaffected. The freeze is still an event — after v1.0 and
  the owner's visual review — and this regeneration precedes it.

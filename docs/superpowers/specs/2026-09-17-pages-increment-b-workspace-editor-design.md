# Pages, Increment B: the notes workspace and a block editor

**Status:** design approved in chat 2026-09-17; revised the same day after an
adversarial review (21 findings), with the owner taking the three recommended
rulings recorded in §1.
**Builds on:** `docs/superpowers/specs/2026-09-08-pages-notion-model-design.md`
(Increment A, merged and deployed 2026-09-17 at `37f5d299`). That spec's §11
named Increment B as "repoint `/notes`, split `project-workspace.tsx`, retire
`treeManagement`, drag to reorder siblings". This spec keeps that scope and adds
the owner's request of 2026-09-17: a real Notion-style editor rather than the
per-block textarea editor `/notes` shows today.

## 1. Decisions

| Question | Ruling |
|---|---|
| Block types the editor offers | Today's types **plus to-do, toggle and callout** |
| Do the new types reach documents? | **No — page-only.** The document parser never mints them; filed documents parse exactly as today |
| Editor library | **BlockNote** (ProseMirror/TipTap based), core packages only |
| Delivery | Three increments, each deployable: **B1** backend, **B2** workspace on a page copy of the existing editor, **B3** BlockNote |
| Page vectors on edit | **An edit deletes the block's vectors; the hourly sweep re-embeds.** No embedder call on the write path |
| Existing personal-project notes | **Accepted as invisible in the SPA** after B2; the rows stay in the database and over REST and MCP |
| Paste and bulk inserts | **A batch insert route in B1**; consecutive unsent inserts go out as one batch |

Rejected, for the record: TipTap headless with an in-house UI (the slash menu,
drag handles, block identity and nesting are exactly what BlockNote already
ships, at weeks of cost for a single-operator surface); Lexical (Notion features
exist only as playground example code, and there is no per-block change stream
to map onto the block verbs); sharing the new types with documents (a document
carrying `- [ ]`, `> [!NOTE]` or `<details>` would parse differently, changing
`/documents` and obliging a re-import of the filed corpus); images and file
embeds (a file-storage subsystem is a project of its own); keeping inline
embedding on page updates (an Ollama round trip behind every typing pause);
keeping old notes visible read-only (a second surface over data the greenfield
ruling makes disposable); capping paste size with serial writes (a pasted
200-block note would be 200 whole-page rewrites).

## 2. Out of scope

- `/documents` (`DocumentsView`) and `/projects/$project` (`ProjectWorkspace`
  without `treeManagement`) keep their current editor and read/edit modes.
- Pages still get no MCP tools, wiki-links, tags or search (Increment A §10).
- No version history; BlockNote's in-session undo is the only undo.
- **No conversion of existing notes.** Today's notes are documents in the
  personal project. `/documents` and the project switcher both filter the
  personal project out (`routes/_authenticated/documents.tsx:25`,
  `project-switcher.tsx:53`), so once `/notes` shows pages those notes are
  visible nowhere in the SPA. They remain in the database and are reachable over
  REST, MCP and by typing `/projects/<personal-name>`. That is the ruling, not an
  oversight.
- No project picker on `/notes`; it stays the personal project only.
  `pages.project` remains a general column for later.

## 3. B1 — backend

### 3.1 Page-only block types

`todo`, `toggle` and `callout` land taxonomy-first in a new
`PAGE_BLOCK_TYPES` in `app/taxonomy.py`, separate from `BLOCK_TYPES`. Keeping
them separate is why `test_taxonomy.py`'s `len(BLOCK_TYPES) == 9` pin holds.

- **A second pure normaliser.** `taxonomy.py`'s module rule is that normalisers
  are pure functions of one string. So `normalize_block_type` is unchanged, and
  a new `normalize_page_block_type` accepts `BLOCK_TYPES ∪ PAGE_BLOCK_TYPES`,
  folding anything else to `paragraph`. `BlockOwner` gains a `normalize_type`
  field naming which function to call; `DOCUMENT_OWNER` names the existing one,
  so a document block verb naming `todo` stores `paragraph` exactly as today.
- **The document parser is untouched.** `parse_markdown` has no task-list
  plugin: `- [ ]` parses as a `list` item with text `[ ] …`, `> [!NOTE]` as a
  `quote`, `<details>` as an `html` block, and no legacy alias maps to the new
  types. A page created with `content` uses the same parser
  (`page_door._parse`), so a to-do exists only once the editor sets that type.
- **No schema change.** `blocks.type` is `TEXT` with no CHECK; `search_vector`
  blanks only `code`/`html`, so the new types index as prose.
- **Guards the new set trips:** `test_taxonomy.py`'s uniqueness/lowercase
  parametrisation gains `PAGE_BLOCK_TYPES`; `test_notes_schema.py`'s prose/source
  partition classifies all three as prose.

### 3.2 Properties, validated inside the verb

| Type | Properties | Rule |
|---|---|---|
| `todo` | `checked: bool` | required |
| `toggle` | none | — |
| `callout` | `variant: "info" \| "warning" \| "error" \| "success"` | required |

Validity depends on the **resulting** block: `update_block` merges properties
over the stored ones and a request may change `type` without `properties` or the
reverse. So validation runs inside the verb's `apply` closure on the merged
block, through a `validate` field on `BlockOwner` (a no-op for documents). A
failure raises `PageBlockInvalid(ValueError)`, added to the page routes'
`_BLOCK_REFUSALS` and mapped to 422.

On a page type change, properties the new type does not define are dropped
(`checked` does not survive onto a paragraph; `ordered`/`marker` do not survive
onto a to-do). Each emit rule reads only its own type's keys.

### 3.3 Nesting on pages

**Allowed parents for a new insert or move:** `list`, `todo`, `toggle`, and the
existing `table` → `table_row` shape. Anything else is refused by the verb with
`PageBlockInvalid` → 422. The document path is unchanged.

**Headings are not containers on pages.** The parser parents every block under
its nearest open heading (`document_parsers.py` `parent()`), so a page created
with `content` would otherwise arrive heading-nested, which BlockNote renders as
indentation and the rule above would refuse to extend. `create_page` therefore
**flattens heading nesting** after parsing: every block whose parent is a
heading is re-parented to that heading's nearest non-heading ancestor (or the
root), keeping reading order. This is lossless: headings do not change the child
prefix, the separator between a heading and its first child is the same blank
line as between root siblings, and list ordinals reset on a non-list predecessor
either way, so `serialize_tree` emits byte-identical content. A test pins that.

Other parser shapes (a quote or list item holding code or paragraph children)
are kept; the editor renders them, and only new inserts or moves under a
disallowed parent are refused.

### 3.4 Page-specific request models and client ids

Pages get their own request models in `app/schemas/page.py`, with
`extra="forbid"`: `PageBlockInsertRequest` (the document fields plus optional
`block_id: UUID`), `PageBlockBatchInsertRequest`, and page copies of update and
move. The shared models in `routes/documents.py` are not touched, so the
document insert route cannot silently accept `block_id`.

A supplied `block_id` becomes the new row's id. Inside the verb, under the page
row lock, `SELECT 1 FROM blocks WHERE id = CAST(:id AS uuid)` precedes the
insert; a hit raises `PageBlockIdTaken` → **409** with detail
`block id <uuid> already exists`. A primary-key violation from a race past that
check surfaces from the savepoint as the same refusal. The client never needs to
tell this 409 from a hash conflict (§5.4 re-reads on every 409).

### 3.5 Batch insert

`POST /api/v1/pages/{page_id}/blocks/batch` → **201**, body
`{blocks: [{block_id, type, text, properties?, parent_id?, after_block_id?}], expected_hash?}`,
at most `MAX_BLOCKS` items. One `_mutate` pass: the whole list is applied in
order to the in-memory tree (a later item may name an earlier item's `block_id`
as parent or `after_block_id`), then one serialise, one placement write, one
journal row, one `content_hash`. Every item carries a client `block_id`. The
first invalid item refuses the whole batch (422 or 409, nothing written). The
response is the single-insert response with `block_ids` in place of `block_id`.

### 3.6 Page block edits drop vectors instead of embedding

Today `insert_block` and `update_block` embed the touched block after commit;
`move_block` and `delete_block` embed nothing. The sweep
(`block_embedding_refresh`) only fills blocks with **no** vector, so turning
inline embedding off alone would leave edited blocks stale forever.

`BlockOwner` gains `embed_inline: bool` (`True` for documents, unchanged;
`False` for pages), and the page path adds a vector drop:

- **Insert / batch insert:** nothing embedded inline; the new block has no
  vector, so the sweep finds it.
- **Update whose `text` or `type` changed:** inside the write savepoint, delete
  that block's rows from `page_embeddings__<slug>` for **every non-retired
  fingerprint** in `embedders`, each named through `child_table`. The sweep then
  re-finds it. A properties-only update (ticking a to-do) keeps its vector.
- **`create_page` with content** also stops embedding inline, for the same
  consistency.

Worst-case page vector staleness is one sweep interval (hourly, `35 * * * *`).
Nothing reads page vectors yet. Trashed pages' new blocks still spend sweep
budget once; accepted, and left for the page-search increment as Increment A
parked it.

### 3.7 Delete returns the new hash

`DELETE /pages/{id}/blocks/{block_id}` stays **204** (REST conventions,
`EXPECTED_STATUS`) and adds an `X-Content-Hash` response header carrying the
page's new `content_hash`, so the client's hash chain needs no re-read. The
header is page-only; the document delete route is unchanged.

### 3.8 The page read serves `source`

`GET /pages/{id}` blocks gain `source`: `content[char_start:char_end]`, derived
the way `document_blocks_route` derives it for documents
(`routes/documents.py:427-429`), read from `pages.content` without requiring
`include_content`. B2's editor edits `source`, as the document editor does.

### 3.9 Trash listing

`GET /api/v1/pages/trash?project=…` returns the **roots of trashed subtrees**
(trashed pages whose parent is NULL or not trashed) with `id`, `title`,
`parent_id`, `deleted_at`, newest first. It takes no row lock. It is registered
**above** `GET /{page_id}` in `routes/pages.py`, as `/trash/empty` already is,
or `trash` would fail UUID parsing with 422.

### 3.10 Serialiser emit rules

`pages.content` stays readable markdown. Nothing re-parses a page's stored
content (blocks are the authority), and the document parser does not learn
these forms.

- **`todo`:** `- [ ] text` / `- [x] text`, continuation lines indented as a
  `list` item's, children under the same indent. `todo` counts as a **bullet
  list kind** in the three list predicates: `_same_list_run` (consecutive
  to-dos, and to-dos adjacent to bullet items, are one tight run),
  `_separator`'s nested-item rule (a `list` or `todo` under a `list`/`todo`
  parent is tight), and the ordinal loop (a `todo` resets the ordered count, as
  any bullet item beside an ordered run does in markdown).
- **`toggle`:** opening lines `<details>` and `<summary>text</summary>`, then a
  blank line, then children, then a blank line and `</details>`. `emit` gains a
  post-children hook for the closing line. The toggle's `char_span` covers the
  two opening lines only, so it stays one contiguous range.
- **`callout`:** GitHub alert form — `> [!NOTE]` on its own line, then the text
  as `> ` lines. Variants: info → `NOTE`, warning → `WARNING`, error →
  `CAUTION`, success → `TIP`. No children.

### 3.11 Enumeration guards

The batch route and the trash route are the twelfth and thirteenth page routes.
Each needs an entry in `ROUTES_WITHOUT_MEMORY_CONTENT` and `EXPECTED_STATUS`.
In `PARITY_TABLE` they join the existing `pages.reads` (trash) and `pages.write`
(batch) surfaces rather than adding surfaces, so the parity doc's hand-written
headline counts do not move; the generated table between its markers
regenerates. Run CLAUDE.md's guards leg **and** `tests/test_read_only_role.py`
(outside that leg; the check Increment A's tasks missed).

## 4. B2 — the `/notes` workspace

### 4.1 Split

- `ProjectWorkspace` returns to being the corpus browser used by
  `/projects/$project`: `treeManagement`, `freeUri` and the notes-only branches
  are deleted, and `/projects/$project` renders as it does today.
- New `frontend/src/features/notes/`:
  - `notes-workspace.tsx` — layout: sidebar tree plus page pane.
  - `page-tree.tsx` — renders the nested tree.
  - `page-pane.tsx` — title field and body.
  - `page-block-editor.tsx` — a **deliberate copy** of
    `features/documents/components/block-editor.tsx` (with its `promote`
    helper) over the page hooks, editing `source` from §3.8. It is recorded as
    a duplicate that B3 deletes; the document editor is not parameterised,
    so `/documents` code does not change.
  - `lib/build-page-tree.ts` — pure: flat rows → nested nodes sorted by
    `order_index`, tolerant of any row order.
  - `lib/drop-target.ts` — pure: pointer position over a row →
    `{parent_id, after_id}` or refusal.
- `frontend/src/hooks/api/use-pages-api.ts` — query and mutation hooks for all
  thirteen routes, every query `enabled: !DEMO`. B2's page block writes reuse
  `features/documents/lib/mutation-queue.ts`'s serialise-per-owner pattern,
  keyed on the page query.
- `move-target.ts` and `uri-tree.ts` are deleted only if nothing else imports
  them. `document-tree.tsx`'s row rendering is shared only if it lifts out
  without changing `/projects/$project`; otherwise `page-tree.tsx` has its own
  row.

### 4.2 Selection

The selected page lives in the URL: `/notes?page=<id>` via the route's
`validateSearch`. A `404` from `GET /pages/{id}` (missing or trashed — the
server does not distinguish) clears the search param and shows the empty pane.

### 4.3 Tree interactions

- **New page** at the root; on row hover, `+` (new child page) and `⋯`
  (rename, delete). A created page is selected with its title field focused.
- **Drag with `@dnd-kit/core`.** The top third of a row drops before that
  sibling, the bottom third after it, the middle third makes the dragged page
  the target's last child. Each becomes `PATCH {parent_id, after_id}`.
- The client refuses a drop onto the page itself or a descendant; the server
  refuses it again (422, the locked cycle guard).
- Moves are optimistic and roll back on refusal with a toast carrying the
  server's message.
- A collapsed row expands after ~600 ms of drag hover. Expanded state persists
  per page in `localStorage`, wrapped in try/catch; without storage the tree
  renders collapsed.

### 4.4 Trash

- A **Trash** entry at the foot of the sidebar opens a sheet listing §3.9's rows
  with relative deletion time.
- **Restore** per row; a refusal (parent still trashed, 409) shows the server's
  message.
- **Empty trash** behind a confirmation dialog.
- Deleting from the tree is the soft delete, followed by a toast with **Undo**
  that calls restore.

### 4.5 Carried from Increment A

`project-switcher.tsx`'s item total adds `page_count`.

## 5. B3 — the BlockNote editor

### 5.1 Packaging and the first probe

- `@blocknote/core`, `@blocknote/react` and `@blocknote/shadcn`, pinned to one
  version. These are MPL-2.0 (to confirm at install); **no `@blocknote/xl-*`
  package**, which are AGPL-3.0 or commercial.
- `PageEditor` is loaded with `React.lazy` together with BlockNote's CSS;
  `npm run build` must show it outside the main chunk.
- **B3's first task is a probe**, committed as vitest cases against the pinned
  version, settling what the repo cannot:
  1. `getChanges()` entry shapes: whether `move` is its own type, whether a
     child edit also reports its parent as `update`, and what `source` values
     appear.
  2. Block id format. If ids are not UUIDs, the editor is configured with a
     `crypto.randomUUID` id generator.
  3. The trailing empty block option, set off.
  4. Whether `checkListItem`, `toggleListItem` and a divider are built in.
  5. Heading levels: whether the built-in heading accepts 4–6. If not, a custom
     heading block with levels 1–6 replaces it.
  6. How nesting is exposed (Tab, `nestBlock`, the side menu), to place the
     §5.2 nesting restriction.
  7. React 19 peer compatibility and whether `@blocknote/shadcn` accepts
     darkraise-ui components; if not, plain CSS overrides over the package
     defaults, recorded as a darkraise-ui gap per CLAUDE.md's UI rule.
  A probe result that contradicts this spec is a ruling for the plan's ruling
  seat, not a silent adaptation.

### 5.2 Block mapping

One editor block is one server block with the same id; nesting is the same tree
(headings hold no children on pages, §3.3).

| BlockNote | Server `type` | Properties |
|---|---|---|
| `paragraph` | `paragraph` | — |
| `heading` (or the probe's custom heading) | `heading` | `level` 1–6; the slash menu offers 1–3 |
| `bulletListItem` / `numberedListItem` | `list` | `ordered`, `marker` |
| `checkListItem` | `todo` | `checked` |
| `toggleListItem` | `toggle` | — |
| custom `callout` | `callout` | `variant` |
| `codeBlock` | `code` | `language` |
| `quote` | `quote` | — |
| `table` | `table` with `table_row` children | `header`, `alignments` / `cells` |
| divider (built in, or a small custom block) | `divider` | — |
| custom read-only `raw` | `html` | shown as source; never offered by the slash menu |

- **Inline content** is limited to what markdown holds: bold, italic, inline
  code, strikethrough, links. Underline, colours and alignment are disabled. A
  pure converter, `lib/inline-markdown.ts`, maps marker-stripped markdown `text`
  ↔ BlockNote inline content, escaping markdown specials in plain text.
- **Nesting** matches §3.3: indenting is blocked unless the would-be parent is a
  list, to-do or toggle item.
- **Tables** are the one many-rows case: an edit updates the `table` block's
  header, then reconciles `table_row` children by position (update, delete
  extras, batch-insert new rows).
- **Title** is `pages.title`, edited in the pane's title field through
  `PATCH /pages/{id}`, not a block.
- **Disabled:** image, video, audio and file blocks, and the emoji picker.

### 5.3 Editor surface

- No read/edit toggle; the editor is the page view. B3 deletes B2's
  `page-block-editor.tsx`.
- Slash menu: only the allowed types, including To-do, Toggle and Callout
  (with variant).
- Formatting toolbar: bold, italic, code, strikethrough, link.
- Side menu: drag handle and `+`; a block drag is a `move` operation.
- Markdown shortcuts: `#`–`###`, `-`, `1.`, `[]`, `>`, triple backtick.
- Paste: BlockNote converts pasted HTML or markdown into blocks; anything
  outside the schema is dropped by the schema. The resulting inserts go out as
  one batch (§5.4).
- Outline rail: headings read from the editor's live document; clicking scrolls.
- Demo mode: `/notes` shows a fixed sample page with the editor non-editable and
  makes no API call.

### 5.4 Save and sync

A pure module, `lib/page-sync-queue.ts`, with no editor dependency; an adapter,
`lib/editor-changes.ts`, turns editor changes into queue operations.

- **Operations.** `insert` (client `block_id`), `update`, `move`, `delete`. The
  adapter ignores an `update` whose block differs from its previous version only
  in `children` (a child's own change is reported separately).
- **Placement is resolved at send time.** An operation carries only its block
  id and kind. When it is sent, `parent_id` and `after_block_id` are read from
  the editor's **current** document (its parent and previous-sibling lookups),
  and `text`/`type`/`properties` from the block's current state. So cancelled
  or reordered siblings can never leave a reference to a block the server never
  had.
- **Coalescing before send.** Updates to one block collapse into one; an unsent
  insert absorbs later updates to that block; an unsent insert whose block is
  deleted before send cancels both; consecutive unsent inserts become one
  **batch insert** (§3.5), ordered so parents precede children.
- **One write in flight.** Each write sends the last known `content_hash` as
  `expected_hash` and takes the new one from the response body, or from
  `X-Content-Hash` on a delete (§3.7). The first hash comes from
  `GET /pages/{id}`.
- **Timing.** Text updates flush after ~800 ms idle; structural operations
  enqueue immediately. Everything pending flushes on editor blur, route change
  and `visibilitychange` to hidden, using `fetch(..., {keepalive: true})` for
  the hidden case. Leaving with a non-empty queue shows the browser's leave
  warning.
- **Save state** in the pane header: `Saving…`, `Saved`, `Unsaved — retrying`.
- **Deciding whether a write landed** — used after a network error, a 5xx, or
  any 409. Re-read `GET /pages/{id}` and check the operation itself: an insert
  landed iff its `block_id` is present; a delete iff its block is absent; an
  update iff the block's `text`, `type` and `properties` equal what was sent; a
  move iff its `parent_id` and previous sibling match. Landed → take the
  re-read's hash and advance. Not landed after a network error or 5xx → resend
  with backoff (1 s, 2 s, 4 s, capped at 30 s). Not landed after a 409 → the
  page changed elsewhere: stop the queue and show the conflict banner.
- **404** (the page was trashed or purged elsewhere, or a referenced block is
  gone): stop the queue and show the banner.
- **422** means the editor let through a shape the server refuses — a bug. Stop
  the queue and show the server's message in the banner.
- **The banner** offers **Reload page**, which discards unsent local operations
  and reloads from the server. Single operator, no merge.
- **Undo/redo** is BlockNote's local history; its changes sync like any edit.

## 6. Error display, all increments

Save state in the page header; conflicts, refusals and a vanished page as a
banner above the editor with **Reload page**; tree and trash refusals as toasts
carrying the server's message. A failed page load (network or 5xx) shows an
error, never the empty state. **The one exception is `404` on
`GET /pages/{id}`**, which means the selection no longer exists and shows the
empty pane (§4.2).

## 7. Testing

### B1 (backend, from `backend/`, on a lane database, never `darkmem_test`)

- Taxonomy: `normalize_page_block_type` accepts the three and folds unknowns;
  `normalize_block_type` still folds them to `paragraph`.
- Serialiser: `todo` (both states, consecutive tight run, beside bullet and
  ordered items, nested under `list` and `todo`); `toggle` with children and its
  span covering only the opening lines; `callout` per variant.
- Heading flattening: `create_page` with nested headings yields no
  heading-parented block, and the stored `content` equals the unflattened
  tree's serialisation byte for byte.
- Isolation, extending `tests/test_page_document_isolation.py`: the document
  parser mints none of the three; a document block verb naming one stores
  `paragraph`; the document insert route rejects nothing new and does not read
  `block_id`; the document delete route carries no `X-Content-Hash`.
- Page routes: each new type valid and invalid (422), including a type change
  that leaves a required property missing; nesting refusals on insert and move;
  client `block_id` and a taken id (409); batch insert order, intra-batch
  references, all-or-nothing refusal; the delete header; `source` on the read;
  trash roots only.
- Vectors: an update changing `text` removes the block's page vectors in every
  registered fingerprint and the sweep restores them; a properties-only update
  keeps them; a document update still embeds inline. Each with a discrimination
  proof.
- CLAUDE.md's guards leg plus `tests/test_read_only_role.py`.

### B2 and B3 (frontend vitest)

- `build-page-tree.ts` with shuffled input; `drop-target.ts` including
  descendant refusal.
- `PageTree`, the trash sheet, selection on 404, and `/projects/$project` still
  rendering `ProjectWorkspace` as before.
- B3's probe cases (§5.1).
- `inline-markdown.ts`: round-trip property tests over generated inline content,
  including markdown specials in plain text.
- Block mapping both directions, per row of §5.2.
- `editor-changes.ts`: children-only updates ignored; placement read at send
  time.
- `page-sync-queue.ts`: coalescing (including insert-then-delete of a middle
  sibling), batch formation, single in-flight write, delete hash from the
  header, the landed check per operation kind for network error and 409, 404
  and 422 stops, flush on hide with `keepalive`.
- `npm run typecheck` and `npm run build` (the editor chunk outside the main
  bundle).

### End to end

Through `backend/scripts/e2e/run_playwright_e2e.py` only, never bare Playwright:
create a page, type, reload and see it persisted; tick a to-do; fold a toggle;
add a callout; paste a multi-block snippet; drag to reorder in the tree; trash
and restore.

## 8. Deploy

No increment is expected to change `0001_baseline.py`: the new types are
code-level vocabulary, client ids use the existing `id` column, the new routes
are queries or verb passes, and the embedding switch is a descriptor field plus
a delete. Each increment is therefore an ordinary redeploy — gate legs,
`DARKMEM_PUSH=0` build, image sha equals HEAD, `docker compose up -d`, the new
route or asset confirmed in the running image. B1's plan verifies the
no-schema-change claim as its first step; if it fails, that increment follows
the drop-and-restore procedure instead.

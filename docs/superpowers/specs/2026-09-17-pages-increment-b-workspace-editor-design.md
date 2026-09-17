# Pages, Increment B: the notes workspace and a block editor

**Status:** design approved in chat 2026-09-17, pending written-spec review.
**Builds on:** `docs/superpowers/specs/2026-09-08-pages-notion-model-design.md`
(Increment A, merged and deployed 2026-09-17 at `37f5d299`). That spec's §11
named Increment B as "repoint `/notes`, split `project-workspace.tsx`, retire
`treeManagement`, drag to reorder siblings". This spec keeps that scope and adds
the owner's request of 2026-09-17: a real Notion-style editor rather than the
per-block textarea editor `/notes` shows today.

## 1. Decisions taken in the design conversation

| Question | Ruling |
|---|---|
| Block types the editor offers | Today's types **plus to-do, toggle and callout** |
| Do the new types reach documents? | **No — page-only.** The document parser never mints them; filed documents parse exactly as today |
| Editor library | **BlockNote** (ProseMirror/TipTap based), core packages only |
| Delivery | Three increments, each deployable: **B1** backend, **B2** workspace on the existing editor, **B3** BlockNote |

Rejected, for the record: TipTap headless with an in-house UI (the slash menu,
drag handles, block identity and nesting are exactly what BlockNote already
ships, at weeks of cost for a single-operator surface); Lexical (Notion features
exist only as playground example code, and there is no per-block change stream
to map onto the block verbs); sharing the new types with documents (a document
carrying `- [ ]`, `> [!NOTE]` or `<details>` would parse differently, changing
`/documents` and obliging a re-import of the filed corpus); images and file
embeds (a file-storage subsystem — upload, serving, backups — is a project of
its own).

## 2. Out of scope

- `/documents` keeps its current textarea `BlockEditor` and its read/edit modes.
- Pages still get no MCP tools, wiki-links, tags or search (Increment A §10).
- No version history; BlockNote's in-session undo is the only undo.
- **No conversion of existing notes.** Today's notes are documents in the
  personal project. Under the greenfield ruling they are not migrated: they stay
  reachable in `/documents`, and `/notes` starts empty.
- No project picker on `/notes`; it stays the personal project only.
  `pages.project` remains a general column for later.

## 3. B1 — backend

### 3.1 Page-only block types

`todo`, `toggle` and `callout` join the vocabulary, in a separate
`PAGE_BLOCK_TYPES` beside `BLOCK_TYPES` in `app/taxonomy.py`, taxonomy-first.

- **Normalisation becomes owner-aware.** `normalize_block_type` today folds any
  unknown value to `paragraph`. The document owner keeps exactly that: a
  document block verb naming `todo` stores a `paragraph`, as it does today. The
  page owner accepts `BLOCK_TYPES ∪ PAGE_BLOCK_TYPES`. The owner descriptor
  (`BlockOwner` in `block_verbs.py`) carries the allowed set so no call site
  branches on owner kind.
- **The document parser is untouched.** `document_parsers.py` mints none of the
  three, so a filed document's blocks cannot change. A page created with
  `content` goes through the same parser and therefore never mints them either;
  a to-do exists only once the editor sets that type.
- **Properties:** `todo` → `{checked: bool}`; `toggle` → none (its children are
  its body); `callout` → `{variant: "info"|"warning"|"error"|"success"}`.
  Unknown or missing values are refused with 422 on the page routes.
- **No schema change.** `blocks.type` is `TEXT` with no CHECK
  (`0001_baseline.py` `CREATE TABLE blocks`); `search_vector` blanks only
  `code`/`html`, so the new types index as prose, which is correct.

### 3.2 Serialiser emit rules

`pages.content` stays readable markdown. `block_serializer.serialize_tree` gains:

| Type | Emitted | Children prefix |
|---|---|---|
| `todo` | `- [ ] text` / `- [x] text` | the item's indent, as `list` |
| `toggle` | `<details>` / `<summary>text</summary>` / children / `</details>` | none (blank-line separated) |
| `callout` | `> [!NOTE] text` (`[!WARNING]`, `[!CAUTION]`, `[!TIP]` for warning, error, success) | none (callouts hold no children) |

These emit rules are one-way by design: nothing re-parses a page's stored
content (blocks are the authority, Increment A §7), and the document parser does
not learn the syntax. `reproduces_source` is not consulted on the page path.

### 3.3 Nesting rules on pages

A page block may have children only when its parent is a `list`, `todo` or
`toggle` block, plus the existing `table` → `table_row` shape. Any other parent
is refused with 422 on insert and move. `quote` and `callout` hold inline text
only. The document path is unchanged.

The rule is enforced at write time on the block verbs only. A page created with
`content` goes through the document parser and can already hold other shapes
(a quote or list item with code or paragraph children); those trees stay valid,
the editor renders them, and only a new insert or move into a disallowed parent
is refused.

### 3.4 Client-supplied block ids

`POST /api/v1/pages/{id}/blocks` accepts an optional `block_id` (UUID). When
present it is the new row's id; an id that already exists anywhere in `blocks`
is refused with 409. This keeps the editor's block ids and the server's
identical with no remapping. The document insert route does not gain it.

### 3.5 Page block edits stop embedding inline

Every block verb today embeds the touched block after commit, one embedder
round trip per write. For pages that would put an Ollama call behind every
typing pause. `BlockOwner` gains `embed_inline: bool`: `True` for documents
(unchanged), `False` for pages. The existing `block_embedding_refresh` page arm
(hourly) fills page vectors. Nothing reads page vectors yet, so staleness of up
to an hour costs nothing; when page search lands, that increment decides whether
to re-enable inline embedding.

### 3.6 Trash listing

`GET /api/v1/pages/trash?project=…` returns the **roots of trashed subtrees** —
trashed pages whose parent is NULL or not trashed — with `id`, `title`,
`parent_id`, `deleted_at`, ordered newest first. This is the twelfth page route,
so it takes a `REST_ONLY` row in `PARITY_TABLE`, an entry in
`ROUTES_WITHOUT_MEMORY_CONTENT` and one in `EXPECTED_STATUS`; the parity doc
headline regenerates. It takes no row lock.

## 4. B2 — the `/notes` workspace on the existing editor

### 4.1 Split

- `ProjectWorkspace` returns to being the documents browser: `treeManagement`,
  `freeUri` and the notes-only branches are deleted, and `/documents` renders as
  it does today. Its tests lose the notes cases.
- New `frontend/src/features/notes/`:
  - `notes-workspace.tsx` — layout: sidebar tree plus page pane.
  - `page-tree.tsx` — renders the nested tree built from flat `GET /pages` rows.
  - `page-pane.tsx` — title field, body. B2 mounts the existing `BlockEditor`
    pointed at the page block routes (with a read renderer beside it); B3
    replaces the body.
  - `lib/build-page-tree.ts` — pure: flat rows → nested nodes, sorted by
    `order_index`, tolerant of any row order (Increment A gives no
    parent-before-child guarantee).
  - `lib/drop-target.ts` — pure: pointer position over a row → `{parent_id,
    after_id}` or refusal.
- `frontend/src/hooks/api/use-pages-api.ts` — query and mutation hooks for all
  twelve routes, every query `enabled: !DEMO`.
- `move-target.ts` and `uri-tree.ts` are deleted if `/documents` no longer
  imports them, otherwise left as they are. `document-tree.tsx`'s row rendering
  is shared only if it lifts out without touching `/documents` behaviour;
  otherwise `page-tree.tsx` has its own row.

### 4.2 Selection

The selected page lives in the URL: `/notes?page=<id>` via the route's
`validateSearch`, so reload, links and back/forward keep it. An id that is
missing or trashed shows the empty pane, not an error.

### 4.3 Tree interactions

- **New page** at the root; on row hover, `+` (new child page) and `⋯`
  (rename, delete). A created page is selected and its title field focused.
- **Drag with `@dnd-kit/core`** (already a dependency). The top third of a row
  drops before that sibling, the bottom third after it, the middle third makes
  the dragged page the target's last child. All three become
  `PATCH {parent_id, after_id}`.
- The client refuses a drop onto the page itself or its descendants; the server
  refuses it again (422, the locked cycle guard).
- Moves are optimistic and roll back on refusal with a toast carrying the
  server's message.
- A collapsed row expands after ~600 ms of drag hover. Expanded state persists
  per page in `localStorage` (wrapped in try/catch; the tree renders collapsed
  when storage is unavailable).

### 4.4 Trash

- A **Trash** entry at the foot of the sidebar opens a sheet listing
  `GET /pages/trash` rows with relative deletion time.
- Each row has **Restore**; a restore refused because the parent is still
  trashed shows the server's message.
- **Empty trash** sits behind a confirmation dialog.
- Deleting from the tree is the soft delete, followed by a toast with **Undo**
  that calls restore.

### 4.5 Carried from Increment A

`project-switcher.tsx`'s item total adds `page_count`.

## 5. B3 — the BlockNote editor

### 5.1 Packaging

- `@blocknote/core`, `@blocknote/react` and the shadcn UI package, all at one
  pinned version. **No `@blocknote/xl-*` package** — those are GPL or
  commercial. The license of each installed package is confirmed at install
  and recorded in the plan.
- `PageEditor` is loaded with `React.lazy` together with BlockNote's CSS, so no
  other route downloads it.
- Styling: BlockNote's CSS variables mapped to darkraise-ui tokens; dark mode
  follows the app theme. The first B3 task probes whether the shadcn package
  accepts darkraise-ui's components; if it does not, the fallback is plain CSS
  overrides over the package's defaults, recorded as a darkraise-ui gap per
  CLAUDE.md's UI rule.

### 5.2 Block mapping

One editor block is one server block with the same id; nesting is the same tree.

| BlockNote | Server `type` | Properties |
|---|---|---|
| `paragraph` | `paragraph` | — |
| `heading` | `heading` | `level`; the slash menu offers 1–3, stored 4–6 render and are preserved |
| `bulletListItem` / `numberedListItem` | `list` | `ordered`, `marker` |
| `checkListItem` | `todo` | `checked` |
| `toggleListItem` | `toggle` | — |
| custom `callout` | `callout` | `variant` |
| `codeBlock` | `code` | `language` |
| `quote` | `quote` | — |
| `table` | `table` with `table_row` children | `header`, `alignments` / `cells` |
| divider (built-in if the pinned version has one, else a small custom block) | `divider` | — |
| custom read-only `raw` | `html` | shown as source; never offered by the slash menu |

- **Inline content** is limited to what markdown holds: bold, italic, inline
  code, strikethrough, links. Underline, text and background colour, and
  alignment are disabled in the schema. A pure converter
  (`lib/inline-markdown.ts`) maps marker-stripped markdown `text` ↔ BlockNote
  inline content, escaping markdown specials in plain text.
- **Nesting** matches §3.3: the editor disables indent (Tab and the side menu's
  nest action) under any parent other than list, to-do and toggle items.
- **Tables** are the one many-rows case: an edit updates the `table` block's
  header, then reconciles `table_row` children by position — update, delete
  extras, insert new rows.
- **Title** is `pages.title`, edited in the pane's title field through
  `PATCH /pages/{id}`, not a block.
- **Disabled:** image, video, audio and file blocks, and the emoji picker.

### 5.3 Editor surface

- No read/edit toggle; the editor is the page view.
- Slash menu: only the allowed types, including To-do, Toggle and Callout
  (with variant).
- Formatting toolbar: bold, italic, code, strikethrough, link.
- Side menu: drag handle and `+`; a block drag is a `move` operation.
- Markdown shortcuts: `#`–`###`, `-`, `1.`, `[]`, `>`, triple backtick.
- Paste: BlockNote converts pasted HTML or markdown into blocks; anything
  outside the schema is dropped by the schema itself.
- Outline rail: headings read from the editor's live document; clicking scrolls.
- Demo mode: `/notes` shows a fixed sample page with the editor non-editable and
  makes no API call.

### 5.4 Save and sync

A pure module, `lib/page-sync-queue.ts`, with no editor dependency.

- **Source of operations.** Each editor change's `getChanges()` becomes ordered
  operations: `insert` (with the client `block_id`), `update`, `move`,
  `delete`; a table change becomes several (§5.2).
- **One write in flight.** Every block route returns the page's new
  `content_hash`, and the next write sends it as `expected_hash`, so writes
  serialise per page. The initial hash comes from `GET /pages/{id}`.
- **Coalescing before send.** Updates to one block collapse to the latest; an
  unsent insert absorbs later updates to that block; an unsent insert followed
  by its delete cancels both; structural operations keep their relative order.
- **Timing.** Text updates flush after ~800 ms idle; structural operations
  enqueue immediately. Everything pending flushes on editor blur, route change
  and `visibilitychange` to hidden. Leaving with a non-empty queue shows the
  browser's leave warning.
- **Save state** in the pane header: `Saving…`, `Saved`, `Unsaved — retrying`.
- **409 hash conflict** (the page changed in another tab): stop the queue, show
  a banner "This page changed elsewhere" with **Reload page**; unsent local
  operations are discarded on reload. Single operator, no merge.
- **Network error or 5xx** (outcome unknown): re-read the page. If its
  `content_hash` differs from the `expected_hash` the failed write carried, the
  write landed — advance. Otherwise resend with backoff (1 s, 2 s, 4 s, capped
  at 30 s). This is sound because one tab is the only writer while the queue is
  healthy; a different tab's write would instead surface as a 409 on the next
  send.
- **422 refusal** means the editor let through a shape the server refuses —
  a bug. Show the server's message in the banner with **Reload page**.
- **Undo/redo** is BlockNote's local history; its changes sync like any edit.

## 6. Error display, all increments

Save state in the page header; conflicts and refusals as a banner above the
editor with **Reload page**; tree and trash refusals as toasts carrying the
server's message. A failed page load shows an error, never the empty state.

## 7. Testing

### B1 (backend, from `backend/`, on a lane database, never `darkmem_test`)

- Serialiser emit rules for `todo` (both states, nested), `toggle` (with
  children), `callout` (each variant).
- Isolation, extending `tests/test_page_document_isolation.py`: the document
  parser mints none of the three types; a document block verb naming one stores
  `paragraph`, exactly as an unknown type does today.
- Page routes: each new type accepted with valid properties, refused with
  invalid ones; nesting refusals on insert and move (422); insert with a client
  `block_id`; a colliding id refused (409); the trash route's root-only rows.
- Embedding: a page block write embeds nothing inline and the refresh sweep
  embeds it; a document block write still embeds inline. Both pinned, each with
  a discrimination proof.
- CLAUDE.md's guards leg **and `tests/test_read_only_role.py`**, which sits
  outside that leg and was the check Increment A's tasks missed.

### B2 and B3 (frontend vitest)

- `inline-markdown.ts`: round-trip property tests over generated inline content,
  including markdown specials in plain text.
- Block mapping both directions, per row of §5.2.
- `page-sync-queue.ts`: coalescing, ordering, single in-flight write, 409 stop,
  unknown-outcome re-read (landed and not landed), flush on hide.
- `build-page-tree.ts` with shuffled input; `drop-target.ts` including
  descendant refusal.
- `PageTree`, the trash sheet, and `/documents` still rendering
  `ProjectWorkspace` unchanged.
- `npm run typecheck` and `npm run build` (the lazy chunk must not enter the
  main bundle).

### End to end

Through `backend/scripts/e2e/run_playwright_e2e.py` only, never bare Playwright:
create a page, type, reload and see it persisted; tick a to-do; fold a toggle;
add a callout; drag to reorder in the tree; trash and restore.

## 8. Deploy

No increment is expected to change `0001_baseline.py`: the new types are
code-level vocabulary, client ids use the existing `id` column, the trash route
is a query, and the embed switch is a descriptor field. Each increment is
therefore an ordinary redeploy — gate legs, `DARKMEM_PUSH=0` build, image sha
equals HEAD, `docker compose up -d`, the new route or asset confirmed in the
running image. B1's plan verifies the no-schema-change claim as its first step;
if it fails, that increment follows the drop-and-restore procedure instead.

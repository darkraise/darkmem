# Pages, Increment B3: the BlockNote editor

**Status:** design approved in chat 2026-09-18.
**Program:** `docs/superpowers/specs/2026-09-17-pages-increment-b-workspace-editor-design.md`
— sub-project 3 of 3. B1 (backend) and B2 (the `/notes` workspace on a copied
per-block editor) are merged.
**Relation to the program spec:** this spec refines §5 of the program spec and
takes precedence over it where the two differ. It records the probe the
program spec deferred (§1), states the two design changes approved on
2026-09-18 (§2), and otherwise inherits §5 and §6–§7 unchanged unless a section
below says otherwise.

## 1. Probe results (BlockNote 0.54.2, run 2026-09-18)

A throwaway probe under jsdom answered §5.1's seven questions. Plan task 1
commits these facts as vitest cases pinned to the version, so an upgrade that
changes one fails loudly.

| Question | Result |
|---|---|
| Licence and peers | `@blocknote/core`, `react`, `shadcn` are MPL-2.0. `react` accepts React 19; `shadcn` requires `tailwindcss ^4.1.12` (the repo has 4.2.2). Yjs peers are optional and are not installed |
| `getChanges()` shapes | `insert`, `delete`, `update`, `move` are distinct. `move` carries `prevParent` / `currentParent`. A child's insert or edit does not report its parent. A table edit is one `update` of the table block. Source is `local` for programmatic calls |
| Block ids | UUID v4 by default; explicit ids are honoured on insert. No custom id generator is needed |
| Trailing block | `trailingBlock: false` is available |
| Built-in blocks | `checkListItem` (`checked`), `toggleListItem`, `divider`, `numberedListItem` (`start`) are built in. Only the callout is custom |
| Headings | `createHeadingBlockSpec({ levels: [1..6] })` accepts level 5. The built-in heading has `isToggleable`; `allowToggleHeadings: false` turns it off |
| Nesting | Tab (`nestBlock`), `moveBlocksUp` / `Down` and drag can place a block under any block, including a paragraph. `onBeforeChange` returning `false` cancels the transaction; a nest under a paragraph was refused that way |
| Tables | One block, `content.type = "tableContent"`, `headerRows`, rows of cells; each cell carries its own `textAlignment`, `colspan`/`rowspan` and colours. `tables: { splitCells, cellBackgroundColor, cellTextColor, headers }` all default off |
| Markdown | `tryParseMarkdownToBlocks` / `blocksToMarkdownLossy` are lossy: `<kbd>` and `![img](u)` vanish, `\*lit\*` becomes `*lit*` (real emphasis on the next parse). They are not used for page content |
| Theme | `@blocknote/shadcn` takes a `shadCNComponents` override for 13 slots (Avatar, Badge, Button, Card, DropdownMenu, Input, Label, Popover, Select, Skeleton, Tabs, Toggle, Tooltip). darkraise-ui ships each; prop compatibility is checked per slot in the plan |

**Not settled by the probe; plan task 1 settles them before anything builds on
them:**

- Whether an `insert` in `onBeforeChange` can be judged by its resulting parent.
  The probe refused a `move` through `currentParent`; an insert's parent must be
  read from the transaction's resulting document (`tr.doc`), not from the editor,
  which has not applied it yet.
- Whether `codeBlock` keeps an arbitrary `language` string (`py`, `tsx`) or
  coerces it to a supported one; if it coerces, the schema configures
  `supportedLanguages` so every stored value survives.
- Whether a table renders `headerRows: 1` with `tables.headers: false`. The
  mapping treats row 0 as the header either way; this decides only styling.

## 2. Changes from the program spec

1. **The save queue diffs snapshots instead of consuming the change log.**
   §5.4's adapter (`lib/editor-changes.ts`), its children-only filter and its
   coalescing rules are replaced by §5 below. Batching, one write in flight,
   send-time placement, timing, save states and banners are kept.
2. **Unrepresentable inline markdown becomes a raw atom** (§4.2), rather than
   being escaped or dropped.
3. **The landed check is one tree comparison** (§5.4), replacing §5.4's
   per-operation rules.
4. **No keepalive flush chain on hide** (§5.6): only the write in flight
   survives a tab close; queued writes are protected by the leave warning.

## 3. Packaging and files

- `@blocknote/core`, `@blocknote/react`, `@blocknote/shadcn` pinned exactly at
  `0.54.2`. No `@blocknote/xl-*` package (AGPL-3.0 or commercial), no Yjs.
- `remark-parse` becomes a direct dependency (it is present today only through
  `react-markdown`).
- Tailwind v4 gets a `@source` for the shadcn package's classes in
  `styles/globals.css`.
- `PageEditor` is loaded with `React.lazy` together with BlockNote's CSS;
  `npm run build` shows it outside the main chunk.

New, under `frontend/src/features/notes/`:

| File | Role |
|---|---|
| `page-editor.tsx` | Builds the editor, mounts `BlockNoteView`, installs the nesting guard, wires sync and the outline |
| `page-outline.tsx` | Heading rail over the live document |
| `use-page-sync.ts` | Binds the sync engine to the editor, timers, visibility, the leave warning and the save state |
| `lib/editor-schema.ts` | The BlockNote schema and editor options (§4.1) |
| `lib/block-mapping.ts` | Pure: server block tree ↔ BlockNote blocks (§4.3) |
| `lib/inline-markdown.ts` | Pure: block `text` ↔ inline content (§4.2) |
| `lib/block-properties.ts` | Pure: the server's property rules (merge, drop, `null` ≡ `{}`) |
| `lib/page-sync.ts` | Pure: the diff, the send loop and the landed check (§5); transport injected |

Deleted: `page-block-editor.tsx` and its test (with `promote`); B2's
`usePageBlockUpdate`, `usePageBlockInsert`, `usePageBlockMove`,
`usePageBlockDelete`, `usePageBlocksInsertBatch` and the per-page
`queues`/`holders` map in `use-pages-api.ts`, replaced by plain request
functions the transport calls. `features/documents/lib/mutation-queue.ts` stays;
`/documents` uses it.

## 4. The editor

### 4.1 Schema and options

- **Blocks:** `paragraph`; `heading` via `createHeadingBlockSpec({ levels:
  [1,2,3,4,5,6], allowToggleHeadings: false })`; `bulletListItem`,
  `numberedListItem`, `checkListItem`, `toggleListItem`; `quote`; `codeBlock`;
  `table`; `divider`; custom `callout` (prop `variant`: `info | warning | error
  | success`, inline content); custom `raw` (`content: "none"`, the stored
  text in a `source` prop, rendered as monospace, maps `html`). No image, video,
  audio or file block.
- **Inline content:** `text`, `link`, custom `rawInline` (an atom holding a
  source string).
- **Styles:** `bold`, `italic`, `code`, `strike`. No underline, text colour or
  background colour.
- **Options:** `trailingBlock: false`; `tables: { headers: false, splitCells:
  false, cellBackgroundColor: false, cellTextColor: false }`, every table
  carrying `headerRows: 1`.
- The default blocks' `backgroundColor`, `textColor` and `textAlignment` props
  remain in their prop schemas; the mapping ignores them and no UI sets them.

### 4.2 Inline markdown

A block's stored `text` is inline markdown with the block marker stripped (the
parser stores `inline.content`). `inline-markdown.ts` parses it with
`remark-parse` (plus GFM strikethrough), using node source positions:

- `text`, `strong`, `emphasis`, `inlineCode`, `delete` and an inline link
  written exactly as `[label](url)` with no title and whose label holds only
  those styles map to BlockNote text, styles and `link`.
- **Everything else becomes a `rawInline` atom whose value is the exact source
  slice**: inline HTML, images, reference links, footnote references, autolinks
  and GFM autolink literals, links with a title or a non-style child, hard
  breaks (`break` nodes), and anything else remark yields. The editor renders it as a monospace chip; it
  can be deleted or moved with the surrounding text but not edited in place.
- A newline inside text maps to a newline in BlockNote text and back.
- The emitter writes styles as `**`, `*`, `` ` `` (fence length chosen to
  exceed any backtick run), `~~`; links as `[label](url)`; escapes markdown
  specials in plain text — including `<` and `&`, because remark decodes
  `&lt;kbd&gt;` to text that would otherwise re-emit as live HTML — and writes
  atoms verbatim. The escape set is whatever makes the acceptance property hold:
  for every generated inline content `c`, `parse(emit(c))` equals `c`.

Spelling normalises (`__b__` → `**b**`, `_i_` → `*i*`, `&amp;` → `\&`) only on a
block the user edits, because the snapshot is canonicalised through the same
converter (§5.1), so an untouched block never differs from it. Atoms survive
every edit byte for byte.

Table cells use the same converter.

### 4.3 Block mapping

As program spec §5.2, with these specifics:

- **Lists.** `numberedListItem` ↔ `list` with `ordered: true`,
  `bulletListItem` ↔ `ordered: false`. The stored `marker` is kept when the kind
  is unchanged; a new or converted item gets `-` or `1.`. Numbering is the
  serialiser's ordinal loop (`_marker_for` rewrites the digits from position),
  so BlockNote's `start` is not mapped.
- **To-do** ↔ `checkListItem` with `checked`; **toggle** ↔ `toggleListItem`;
  **callout** ↔ custom `callout` with `variant`; **divider** ↔ `divider`;
  **code** ↔ `codeBlock`, `language` ↔ `language` (BlockNote's `"text"` default
  maps to no property); **html** ↔ `raw`.
- **Headings** keep levels 1–6.
- **Tables.** One BlockNote table ↔ a `table` block (`header` from row 0,
  `alignments`) plus `table_row` children (`cells`) matched **by position**.
  Existing row ids come from the snapshot; a new row gets a fresh UUID. The
  mapping stays pure: it takes a per-table row-id registry as input and returns
  the updated registry, which the sync engine owns, so repeated conversions
  reuse the same new ids. The stored `alignments` are written back unchanged, padded with
  `null` for a new column; the editor offers no alignment control. A row
  reorder in the editor is therefore row-text updates, not moves.
- **Title** stays `pages.title` over `PATCH /pages/{id}` in the pane's title
  field.

### 4.4 Nesting guard

One `onBeforeChange` handler cancels any transaction containing an `insert` or
`move` whose resulting parent is not a `bulletListItem`, `numberedListItem`,
`checkListItem` or `toggleListItem` (program spec §3.3), reading that parent
from the transaction's resulting document (§1's open item). It covers Tab, the
side menu, drag, `moveBlocksUp`/`Down` and paste. Shapes already on the server
that the rule would refuse (a quote holding a code block) load and render; only
new placements are refused.

Two consequences, accepted and recorded rather than special-cased: children of
such a legacy container cannot be reordered within it (the editor and the
server both refuse the move), and a type change that turns a container with
children into a non-container (a list item with children into a paragraph)
keeps its children, since neither side checks nesting on update — after which
the same reorder limit applies.

### 4.5 Surface

As program spec §5.3:

- Slash menu offers paragraph, headings 1–3, bullet, numbered, to-do, toggle,
  quote, code, table, divider and callout with its four variants. An existing
  heading 4–6 keeps its level. `raw` is never offered.
- Formatting toolbar: bold, italic, code, strikethrough, link.
- Side menu: drag handle and `+`.
- Markdown shortcuts and paste are BlockNote's; pasted content passes through
  the schema and the nesting guard and reaches the server as one batch insert.
- Outline rail: headings of the live document; a click scrolls to the block.
- No read/edit toggle.
- **Theme:** darkraise-ui components are passed through `shadCNComponents`
  wherever their props fit the slot; a slot that does not fit keeps the package
  default with CSS overrides, and `page-editor.tsx` records that darkraise-ui
  gap in a comment (CLAUDE.md's UI rule).
- **Demo mode:** a fixed sample page in a non-editable editor, with no sync
  engine and no API call.

## 5. Save and sync

### 5.1 Two trees

- The **snapshot** is the last tree the server acknowledged, with its
  `content_hash`. It is seeded from `GET /pages/{id}`.
- The **desired** tree is the editor's document through the block mapping.
- Both are the same shape: per block `id`, `parent_id`, sibling order, `type`,
  `text` (emitted markdown), `properties`.
- **Every server tree is canonicalised before it is compared**: the seed read
  and every landed-check re-read pass through the mapping to the editor and back
  (`toServer(toEditor(tree))`). Without this, stored spellings the emitter
  writes differently (`__b__`) and stored properties the editor does not model
  (a list item's `number`) would make every such block differ from the desired
  tree, and the first flush would rewrite the whole page. The server still holds
  its own spelling until a block is edited; an update's properties merge over
  the stored ones, so unmodelled keys survive it.
- **The editor owns its content after mount.** A refetch of the page query
  (after a rename, a tree move, a window refocus) never resets a mounted
  editor. Only **Reload page** remounts it from the server.

### 5.2 The diff

Each flush diffs desired against snapshot and sends **one** write, in this
order:

1. **Inserts, as one batch** (`POST .../blocks/batch`). Every id absent from
   the snapshot, in the desired tree's pre-order. `parent_id` is the desired
   parent, which is on the server or earlier in the batch. `after_block_id` is
   the nearest previous desired sibling that is **already a child of that parent
   on the server** (in the snapshot) or earlier in the batch under the same
   parent; `null` if none. The server refuses an `after_block_id` that is not a
   child of the named parent (`block_verbs.py`, "is not a child of the"), so
   naming a sibling that only a later move will bring under the parent would
   stop the queue with a 422.
2. **Moves**, in the desired tree's **pre-order**. A block present on both
   sides whose parent differs, or whose position among the siblings present on
   both sides differs. Per parent, a longest-increasing-subsequence pass keeps
   the most siblings in place, so an insert never moves its later siblings.
   `after_block_id` follows the same rule as for inserts: the nearest previous
   desired sibling that is a child of the target parent in the snapshot. The
   pre-order matters: when an edit swaps an ancestor and a descendant, the
   block that becomes the ancestor is moved first, so no move asks the server
   to put a block inside its own subtree (which it refuses with 422).
3. **Updates.** `type`, `text` or `properties` differ, properties compared under
   `block-properties.ts` (`null` ≡ `{}`).
4. **Deletes.** Only the topmost absent block of a removed subtree, since the
   server cascades. Deletes go last, so a child moved out of a deleted parent is
   saved first.

After an acknowledged write the op is applied to the snapshot with the server's
own rules (property merge over the stored properties, drop of keys the new type
does not define, placement), the new hash is stored, and the diff runs again
until it is empty. **Convergence is a tested property**: over generated edit
sequences, running the loop to quiescence against a fake server leaves the
snapshot equal to the desired tree and the fake server's tree equal to both.

### 5.3 One write in flight

Each write sends the last known `content_hash` as `expected_hash` and takes the
next one from the response body, or from `X-Content-Hash` on a delete.

### 5.4 Deciding whether a write landed

After a network error, a 5xx or any 409, re-read `GET /pages/{id}` and compare
the server's tree with the snapshot:

- equal to **snapshot with the write applied** → landed: take the re-read's
  hash and continue;
- equal to **the snapshot** → not landed: resend with backoff (1 s, 2 s, 4 s,
  capped at 30 s), using the re-read's hash. `content_hash` hashes only the
  stored content (`page_door.py`, `compute_content_hash(stored_content)`), not
  the title, so a 409 whose re-read equals the snapshot has no benign cause; a
  second consecutive one stops the queue with the banner instead of looping;
- **anything else** → the page changed elsewhere: stop the queue and show the
  conflict banner.

**404** (page trashed or purged, or a referenced block gone) and **422** (the
editor let through a shape the server refuses — a bug) stop the queue and show
the banner with the server's message.

### 5.5 Timing

- A change touching only text schedules a flush after ~800 ms idle.
- Any structural change (insert, move, delete, type change) flushes at once.
- Editor blur and `visibilitychange` to hidden flush at once.

### 5.6 Leaving

- The sync engine lives outside React, one per page id, and keeps draining
  after the pane unmounts, holding the last desired tree. Switching pages never
  blocks and loses nothing.
- Selecting a page whose engine is still draining mounts the editor from the
  engine's desired tree, not the server read.
- An engine that stops (conflict, 404, 422) while its page is not the one shown
  raises a toast naming the page, so the unsent work is not lost silently;
  selecting the page shows the banner. An engine is discarded once it is
  drained and its page is not mounted.
- Every write whose body is 60 KB or less is sent with `fetch(..., { keepalive:
  true })`, so the write in flight at a tab close completes. Writes queued
  behind it cannot follow — each needs the previous write's hash — so the
  browser's leave warning shows while anything is pending or in flight.

### 5.7 Save state and banner

Pane header: `Saving…`, `Saved`, `Unsaved — retrying`. The banner above the
editor carries conflicts, 404 and 422 with **Reload page**, which discards the
engine (and its unsent work) and remounts from the server. Single operator, no
merge. Undo and redo are BlockNote's local history; their results are edits the
diff picks up.

## 6. Testing

Vitest, from `frontend/`:

- **Probe cases** (plan task 1): every row of §1 as an assertion against 0.54.2.
- **`inline-markdown`:** round-trip property over generated inline content
  including markdown specials in plain text; each raw-atom kind (HTML, image,
  reference link, footnote reference, autolink, GFM literal, titled link)
  preserved byte for byte through parse → edit elsewhere → emit; newline
  handling; backtick fence length.
- **`block-mapping`:** both directions for every row of §4.3, including table
  rows by position, new-row id stability across conversions, alignment padding,
  and list marker keep/reset.
- **`block-properties`:** fixtures mirroring `update_block`'s merge and the
  type-change drop rule; `null` vs `{}`.
- **`page-sync`:** the convergence property, with a fake server that enforces
  the real refusals (`after_block_id` not a child of the parent, a move into
  the block's own subtree); batch in pre-order with intra-batch references; a
  block moved under a new parent plus a new sibling after it in one flush;
  an ancestor/descendant swap; minimal moves (an insert before siblings moves
  nothing); a child moved out of a deleted parent is moved before the delete;
  **zero writes on mount** for a page whose stored text and properties use
  non-canonical spellings (`__b__`, `&amp;`, list `number`); the three
  landed-check outcomes and the repeated-409 stop; backoff; 404 and 422 stops;
  delete hash from the header; the keepalive size cutoff; the toast from an
  engine stopping off-screen.
- **Nesting guard:** Tab, move and a pasted nested list under a paragraph are
  refused; under a list, to-do and toggle item they are allowed.
- **Pane:** editor mounted from the engine's desired tree when draining; a page
  query refetch does not reset the editor; demo mode makes no request.
- `npm run typecheck`, `npm test`, `npm run build` (editor chunk outside the
  main bundle).

End to end, through `backend/scripts/e2e/run_playwright_e2e.py` only: create a
page, type, reload and see it persisted; tick a to-do; fold a toggle; add a
callout; paste a multi-block snippet; drag to reorder in the tree; trash and
restore; and a page created over REST containing `<kbd>` keeps it byte for byte
after the neighbouring word is edited.

## 7. Deploy

Frontend only; no schema change, no backend change. An ordinary redeploy per
CLAUDE.md: gate legs, `DARKMEM_PUSH=0 ./scripts/build-push.sh`, image sha equals
HEAD, `docker compose up -d`, the editor chunk confirmed in the running image's
`/app/web`. **B2 is merged but not deployed** (production ran `5d13b529` on
2026-09-18), so the B3 deploy also ships B2 unless B2 is deployed first.

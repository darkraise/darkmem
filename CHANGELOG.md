# Changelog

What changed, per release. One user, one dev environment — this is a "what got
better" log, not release notes for strangers. The ladder is
`docs/planning/RELEASES.md`.

## v1.13.0 — unreleased

**The memory door warns about working data.** A capture that looks like a
log is still stored, but its answer now says so. Closed work logs are now
pruned after 90 days.

### Added

- **Capture warnings.** Every capture door (`POST /api/v1/memories`, its
  batch twin, `memory_add`, `memory_batch_add`) answers `warnings`: empty for
  a clean capture, and one line naming the matched signals (commit
  references, tallies, task progress, VCS events, `file:line`, stack traces,
  session narration, or over 1,500 characters) when two or more match or the
  content is over the length limit. The line points at `worklog_append` and
  `document_put`. Batches answer per entry, and the `wait_process` path
  answers the processed memory plus `warnings`.
- **`capture_flagged` events.** Each flagged capture journals the signal
  names it matched, never its content, on the Activity feed's capture tab.
- **Work-log retention.** A daily `worklog_cleanup` job deletes closed
  workstreams, with their entries and vectors, once they have been closed for
  90 days (`retention_days` on the Jobs page, minimum 1). Open workstreams
  and those marked `retain` are never deleted, however old. Each deletion
  journals `workstream_purged` first, with `retention_days` in its payload,
  and a journal failure stops the sweep before deleting that workstream;
  earlier deletions in the run stand.

## v1.12.0 — 2026-09-27

**Working data has its own lane.** A coding client's checkpoints, progress
ledger and notes to its next session go to a work log instead of into
memories, so none of it is extracted, ranked with memories or verified. This
release carries the lane's first three increments: the store and its verbs on
both doors, search over the log, and revisions of filed documents.

### Added

- **Workstreams and their entries.** A workstream is one piece of a client's
  work in a project, named by the client's own key; its entries are
  append-only checkpoints, ledger chunks and notes. Appending creates the
  workstream, or reopens a closed one, and journals it. Resume answers the
  latest checkpoint, the 50 newest notes and the last 20 ledger entries in one
  read.
- **REST: `/api/v1/worklog`** — append, resume, list workstreams, list entries,
  update (state, retain, title, properties) and purge. Every route admits a
  scoped key: `capture` to write, `read` to read, `admin` to purge.
- **MCP: seven `worklog_*` tools** over the same service, addressing a
  workstream by project and key. With `document_revisions` the catalogue is
  now 48 tools; `worklog_purge` is the third `admin` tool, and it erases a
  workstream irrecoverably after journaling `workstream_purged`.
- **Work-log search.** `worklog_search` and `POST /api/v1/worklog/search`
  (`read`) rank one project's entries by keyword and by meaning (the first
  8,000 characters of each entry) and answer on the keyword arm alone, with
  `semantic_ran: false`, when no embedder is reachable.
- **Compare-and-set appends.** An append may carry `expected_last_seq`: when
  the workstream's newest entry of that kind has another seq, nothing is
  written and the answer is a 409, or a `seq_conflict` from the tool. Every
  append answers `last_seq`.
- **Document revisions.** Every filing that creates a document or changes its
  content keeps that content as a revision, stamped with the key that filed
  it. `GET /api/v1/documents/{id}/revisions[/{revision_id}]` (`read`) and
  `document_revisions` list them newest first and fetch one with its content.
- **The document sync routes admit keys.** `POST /api/v1/documents` takes a
  `capture` key and `GET /api/v1/documents/by-uri` a `read` key, and a new
  `GET /api/v1/documents/manifest` lists `{id, uri, content_hash, updated_at}`
  under a prefix so a mirror fetches only what changed. Keyed filings on both
  doors journal the key's name and id.

### Changed

- The agent instructions and the capture tool descriptions route working data
  to the work log and name what a memory must not carry: commit hashes, test
  and commit counts, task progress, `file:line` references, stack traces, raw
  output and session narration.
- **`block_embedding_refresh` gains a `worklog_batch` knob, default 500.** It
  is the only writer of work-log vectors. An install that stopped the job by
  setting `batch` and `page_batch` to 0 starts embedding work-log entries after
  this upgrade until `worklog_batch` is set to 0 as well.
- Text Postgres cannot store, such as a NUL byte in a query parameter, answers
  422 `invalid_text` instead of 500.
- The schema baseline was regenerated, so a deploy is a drop-and-recreate.

## v1.11.0 — 2026-09-23

### Added

- **MCP connection details on Settings → Integration.** The endpoint, the
  auth header, which key scopes to choose and when `MCP_ALLOWED_HOSTS` is
  needed, plus copyable configs for Claude Code, JSON-config clients and
  Codex and a curl check. A key pasted there fills the snippets without being
  sent or stored; a newly created key's dialog shows them already filled in.
- Initial setup: steps already reached can be clicked to move between them.

### Changed

- The theme is pinned again: only mode, accent colour and surface colour are
  adjustable, on the header and on Settings → Appearance alike. Values saved
  for the other axes are cleared.
- The active sidebar item shows the library's ring and rail again, over the
  accent tint.

### Fixed

- The contribution calendar counted every journal row — logins, setup,
  maintenance runs — as "memories captured", so a fresh install showed
  captures beside an empty Memories page. It now counts memory captures only;
  `GET /api/v1/events/calendar` gains an `object_type` filter for it.
- The contribution calendar no longer overflows the card at laptop widths,
  and its rows are evenly spaced.
- The model dropdown in initial setup and in the LLM purpose dialog opens
  upward instead of being cut off under the footer.

## v1.10.0 — 2026-09-22

### Changed

- Initial setup has a wider responsive layout, labelled provider fields, and
  purpose help tooltips. The folder browser adds breadcrumbs, filtering, and
  explicit selection after a successful repository scan.
- Repository setup selects and scans `/app/data/repositories` by default,
  preserves an existing selection, and reports inaccessible folders before
  allowing the user to continue.

## v1.9.0 — 2026-09-21

**A Notion workspace can be imported into the page tree.** Export a workspace
from Notion as Markdown & CSV, choose **Import from Notion** in the `/notes`
tree header, and the zip is filed under one new page: 2193 pages, six databases
and 61 attachments on the export this was measured against.

### Added

- **`POST /api/v1/pages/import/notion`.** One REST route, REST-only like the
  rest of the page tree. The body is streamed to staging rather than buffered,
  planned off the event loop, then written in one transaction: attachment files
  land first and their rows and pages after, so a crash leaves a file no row
  names and never a row with no file. One import runs at a time; a second gets
  409. A bounded run answers 422 naming `notion_import_max_seconds`.
- **Hierarchy is derived, not read.** A Notion export made without "Create
  folders for subpages" is flat and states none, so a page is parented by
  folder nesting, then database membership (a row page's property block names
  its database's columns), then a link on a line of its own. On the measured
  export that places 2171 of 2193 pages with none ambiguous; the report carries
  how many pages each signal placed, and a cycle is broken with a warning
  rather than dropping pages.
- **The dialog.** Upload progress, an indeterminate bar once the body is sent,
  the counts, and the import's warnings. It refuses closing mid-import and
  says that closing does not cancel an import already at the server.
- **Six ceilings** as settings (`notion_import_max_bytes`, `_max_entries`,
  `_max_uncompressed_bytes`, `_max_pages`, `_max_blocks`, `_max_seconds`), and
  a `pages_imported` journal event on the root page.

### Changed

- The request body cap exempts this route (`bounds_own_body`), as it already
  does the attachment upload; `is_attachment_upload_path` keeps its meaning.
- `create_page` is split so the import and the ordinary create share one
  `_insert_page`, and a page's blocks are now written in one statement instead
  of one per block.

### Limits

- `frontend/nginx.conf` still carries `client_max_body_size 25m`. The image
  serves the SPA itself and does not use it, so it is only a limit for a
  deployment that puts that nginx in front.
- A page's text is read whole up to 16 MiB per member, and the held text of a
  whole export is bounded by `notion_import_max_uncompressed_bytes`, not by the
  1 GB process budget the design assumed.

## v1.8.0 — 2026-09-08

**A document's metadata is editable, on both doors, and a serialised block
tree re-parses to itself.** Retitle, move, pin and re-tag one document or
rewrite a whole `uri` subtree; precondition a block edit on the document's
content hash the way `put` already allows; and three serialiser defects that
made 29 of the corpus's documents fail their own round trip.

**And there is now a place to do it from.** `/notes` is a notes workspace over
the same corpus: create a note or a folder, rename, pin, move — by dragging a
row or by picking a destination from a list — and delete a whole subtree. Every
write goes through the doors above; the UI gained no verb of its own.

### Added

- **A metadata verb and a subtree rename, on both doors.** `PATCH
  /api/v1/documents/{id}` moves one document's title, `uri`, pinned flag or
  tag set; `POST /api/v1/documents/rename` rewrites a whole `uri_prefix`
  subtree and answers the count it moved. MCP carries both as modes of one
  `document_update`, dispatched on whether the call names a `document_id` or a
  `uri_prefix` and refusing one that names both or neither. An omitted field
  writes no assignment at all, so a rename cannot silently unpin a document or
  strip its tags, and `project` is deliberately not a field: moving a document
  between spaces is not a rename. A rename onto a `(project, uri)` another
  document holds is refused rather than merging the two, since that identity
  is what re-filing upserts on.
- **The block verbs take an optional `expected_hash`**, the compare-and-set
  `document_put` already had. The comparison happens after the row lock, never
  before it — above the lock both racing lanes pass their own check — and a
  stale hash answers 409 on the route and a `hash_conflict` envelope from the
  tool, writing nothing on either door. The blocks read serves `content_hash`
  unconditionally and `document_get` takes `include_hash`, so the hash a read
  serves preconditions a write and that write's answer preconditions the next
  one with no read in between. Omitting it keeps last-writer-wins, which is
  what every caller shipped before this still gets.
- **`document_updated` joins the events vocabulary.** One journal row per
  edited document, naming which fields moved and carrying none of their
  values.
- **A subtree delete, on both doors.** `POST /api/v1/documents/delete` and MCP
  `document_delete_subtree` erase every document under a `uri_prefix` and
  answer the count. It is a separate tool rather than a mode on
  `document_delete` because MCP scopes are per tool: a mode would have
  inherited `capture` and let any capture key erase a project's whole corpus.
  It is `admin`-scoped instead, which is the first time that scope reaches
  something irrecoverable — so the settings picker that grants it now names
  all three of that scope's powers, where it used to read "Receive push
  updates" and nothing else. An empty prefix is refused.
  Each deleted document journals a `documents_deleted` row naming the key and
  the actor that ran it, and the delete fails closed when that row cannot be
  written: an erase with no audit trail is worse than a refused one.
- **A notes workspace at `/notes`.** The document browser gains an editing
  mode — per-row actions (new note, new folder, rename, move to…, pin,
  delete), New note and New folder in the pane header and in the empty tree,
  and a project picker that defaults to the project holding the most
  documents. "New folder" files a seeded note inside the folder it names,
  because a folder is derived from the uri path and an empty one has no row
  to exist as. "Move to…" is the only move that needs no pointer: it offers
  the destinations the drag path would accept and dispatches the same verb.
  The reading surface at `/projects/<name>` is unchanged; the mode is a prop,
  so nothing the browser did before gained a write button.
- **Drag a row to move it.** A leaf goes through the metadata PATCH, a folder
  through the subtree rename, and releasing on the pane below the tree moves
  to the top level. A drop that would strand a document under its own
  descendant, or land it where another document already sits, is refused —
  and the refusal is the server's own sentence, which names the colliding
  `uri` rather than the folder you aimed at.
- **`documents_deleted` joins the events vocabulary**, and the list item now
  serves `pinned_at`, which is what makes a pin control renderable at all.
- **Pages: a notes tree of your own, beside documents rather than inside
  them.** `/api/v1/pages` creates, lists, reads, moves, renames, trashes,
  restores and purges pages, and edits a page's blocks with the same four
  verbs documents use. A page must be filed under a parent that exists in the
  same project; a move names the sibling to land after, never an index, and a
  move into a page's own subtree is refused. Creating a page with content
  parses it into blocks and keeps the regenerated source, so a page never
  needs converting — and content the block tree cannot hold, a frontmatter
  fence or a link-reference definition, is refused with a 422 rather than
  dropped behind a 201. Deleting a page moves it and everything under it to
  the trash; only emptying the trash erases rows, and each page a trash,
  restore or purge touches journals its own row before the write or the write
  does not happen. REST-only: no MCP tool reaches a page.
- **Six `page_*` event types and the `page` object type** join the events
  vocabulary, and the project catalogue serves `page_count` and ranks projects
  by it alongside memories, documents and checkpoints.

### Changed

- **Page blocks share the `blocks` table but not the document vectors.** A
  block is owned by exactly one document or one page, and page vectors live in
  their own `page_embeddings__<slug>` family, so a page never enters document
  search, connections or the document embedding sweep. No document query
  changed. The schema baseline was regenerated, so a deploy is a
  drop-and-recreate.
- **`block_embedding_refresh` sweeps page blocks on a second budget,
  `page_batch`, and `batch=0` no longer silences the job.** It now skips a run
  only when both budgets are 0. A stored `batch=0` alone costs one embedder
  probe per tick; `docs/runbook-deployment.md` says what to check before
  redeploying.
- **MCP `document_delete` answers an envelope where it used to raise.** A call
  naming nothing that resolves now returns `{"status": "unresolved"}` with
  `isError: false`, matching `document_update` beside it: two sibling document
  writers must not disagree on the same condition, and an agent can machine-read
  an envelope where it cannot machine-read a traceback. A caller that was
  branching on the tool erroring will now see a success it has to inspect.

### Fixed

- **A subtree move or delete that matched nothing now says so.** Both routes
  answer a count, and `/notes` was discarding it. The tree builds a folder's
  path out of a uri's segments and the routes match the raw uri, so a folder
  whose documents are spelled differently at or above that path — anything
  under a leading slash, or a doubled slash or a scheme's `//` sitting inside
  the folder path itself — matches none of its own rows. The confirm ran, the
  200 came back, the tree refetched unchanged and nothing was said. Zero rows
  is a refusal now, on all three dispatch paths, and a successful folder
  delete names how many notes it removed — which is the only evidence left
  once the rows are gone.

- **A tree row is a drop target across its whole box.** The droppable was the
  row's inner label span, so a release on a folder's chevron, the indent
  gutter or the actions slot — roughly a third of a nested row's width and a
  third of its height — fell through to the pane behind it and resolved as an
  accepted move to the top level. Caught before the move verbs were wired to
  it, so no uri was ever rewritten this way.

- **A tag shared between a memory and a document is no longer dropped from
  the tag list, and its count is no longer multiplied.** The counts query
  joined `memory_tags` directly, so widening it to `document_tags` the same
  way would have reported the product of the two link counts rather than their
  sum, and a document-only tag was invisible entirely. Both link tables are
  counted as correlated subqueries. Note the served field is still named
  `memory_count` and now carries a memory-plus-document sum; renaming it is a
  REST and MCP contract change and is owed separately.
- **A subtree rename into or out of its own path is now order-independent.**
  The rows move one at a time through a unique index, and iterating them in id
  order made which one moved first a coin flip on UUID sort — `notes/a ->
  notes/a/x` either raised a 409 or rewrote both rows, on identical input.
  Depth orders it: deepest first moving into a subtree, shallowest first
  moving out to an ancestor. Lock acquisition stays in id order, so two
  concurrent renames still cannot deadlock.
- **An edit that changes nothing is refused rather than journalled.** A PATCH
  naming no field wrote `{"fields": []}` and a rename onto the prefix it
  already holds wrote one row per document, both into an append-only table
  that can never take them back.
- **A serialised block tree now re-parses to itself.** Sweeping the
  492-document corpus found 29 documents whose regenerated source did not,
  from three separate serialiser defects: the blank line between a quote's
  children carried no `>` prefix and so ended the blockquote; a table cell
  holding a `|` was emitted unescaped, which declared a column the delimiter
  row did not have and **truncated the cell's text** on re-parse; and a
  multi-line setext heading was emitted as one-line ATX, so everything past
  the first newline became a paragraph. The middle one was the only defect
  that destroyed text, and it was the widest at 24 of the 29. Down to 6, all
  of which re-order blocks without losing a character — a parser-side fold of
  a blockquote's paragraph children, not a serialiser defect.

## v1.7.0 — 2026-09-07

**The foundation under a personal notes space, and the retirement of the
proposition lift.** An `html` block type so a document carrying raw HTML can
be edited at all, the six schema objects the notes workspace stands on, and
the seeded personal space itself. The on-demand lift from blocks into the
fact vault is deleted rather than repaired.

### Added

- **An `html` block type, so a document containing raw HTML can be edited at
  all.** The parser minted no block for an HTML run, which meant regenerating
  the document's source from its tree would silently delete it — so the
  conversion guard refused, permanently, every document containing one. Raw
  HTML now parses, serialises verbatim and round-trips, and the guard's
  unrepresentable set is down to the link-reference definition alone. It
  renders as **escaped source, never live markup**: the markdown pipeline
  carries no `rehype-raw`, and adding one to make `<img>`/`<details>` render is
  the first place an imported file would execute script under the operator's
  session cookie.
- **Six schema objects for the notes workspace**, landed in the baseline ahead
  of the surfaces that use them: `projects.kind` (with a partial unique index
  admitting exactly one `personal` space), `documents.pinned_at`,
  `blocks.search_vector` (a stored generated column, blanked for `code` and
  `html` because that text is source rather than prose, GIN-indexed), and the
  `document_links`, `document_tags` and `document_revisions` tables. Wiki-link
  targets are nullable on purpose — `[[a-page]]` pointing at a note that does
  not exist yet is a first-class stub, not an error.
- **The personal notes space is seeded at boot**, not by the setup wizard: a
  capture naming `notes` before any seed ran would mint the row with `kind`
  defaulting to `project`, so the seed repairs an existing row rather than
  only inserting. It is served on the catalogue and kept out of project
  pickers — a space, not a project.

### Removed

- **The on-demand proposition lift and the block-to-fact bridge.** A pricing
  sample — 7 documents minting 2,058 memories into a corpus of 50 hand-captured
  **memories** (the document corpus is 475 documents; this line said
  "a 50-document corpus", wrong unit and a denominator off by roughly tenfold) —
  extrapolated to roughly 104,000 memories and 152,000 LLM calls for a full
  corpus run, a cost the corpus's composition — not call price or token
  volume — made structurally uneconomical. The lift and
  `block_fact_sources`, the bridge that would have carried a fact from a
  lifted block into the vault, are both deleted: there is no route from a
  block to a fact any more. `related-memories` and `document-connections`
  are re-based onto cosine similarity over block vectors instead of the
  retired entity basis.

### Notes

- **Deploying this is destructive.** The baseline is regenerated in place, so
  the revision id does not move and `alembic upgrade head` will report a clean
  migration against a database that does not have these objects —
  `schema_guard` is what catches it and refuses to start. Drop and recreate the
  database, then **re-seed `admin_password_hash`, all eight
  `llm_purpose_configs` rows and the two `llm_providers` rows**; the
  `verification` row especially, since `llm_seed.py` does not reproduce it at
  the qualified judge identity. The additive path in
  `docs/runbook-deployment.md` is **not** available here despite this diff
  being +86/−0: three of the nine objects are columns added inside existing
  `CREATE TABLE` statements, which that procedure's `pg_dump --table=` step
  does not emit. That runbook's precondition has been restated to say so.
- **`blocks.search_vector` is a stored generated column on a populated table**,
  so adding it rewrites every row under an `ACCESS EXCLUSIVE` lock. On the
  recreate path this is paid at import time rather than as downtime.

## v1.6.0 — 2026-09-04

**The project workspace, made usable.** Three surfaces the owner reported as
wrong, plus the markdown rendering underneath them.

### Added

- **The Progress board.** The Progress tab rendered `progress.md` through the
  document reader, so the one question a board exists to answer — what can I
  start right now — still meant joining a 309-row table against eight epic
  files by hand. The board does that join: status columns with epic and lane
  grouping, filters over epic, lane, owner, model and text, and a derived
  **startable** filter that resolves each task's dependencies and its epic's
  entry gate. A `blocked` card renders its Note in full, which is the one thing
  the eleven-column table genuinely hides.
- **Syntax-highlighted code blocks with their language labelled.** The parser
  has stored `properties.language` since it was written and nothing read it.

### Fixed

- **The document reader used none of the app's markdown styling.** Chat and the
  prompt viewer shared `.md-prose`; the reader called a bare `<Markdown>` and
  got Tailwind's preflight instead. Links rendered as plain body text with no
  colour and no underline, inline code had no chip, and `~~strikethrough~~`
  reached the page as literal tildes. All three surfaces now share one
  markdown module, with `remark-gfm` for strikethrough and autolinks.
- **Every markdown surface was broken in light mode.** `.md-prose` applied
  `prose-invert` — the *dark* variant — unconditionally, while the theme
  switcher offers light/dark/system. Chat included. Now gated on the
  `data-mode` attribute the theme provider stamps.
- **Headings below level 3 were the same size and weight as body text**, so a
  document's structure below the second level was invisible. Each level now
  steps, and h6 changes kind rather than shrinking below the text around it.
- **A uniform gap between every block** meant the same distance between two
  list items as between a paragraph and the next section's heading, so nothing
  on the page grouped. Spacing now depends on which two block types meet.
- **A code block set `overflow-x-auto` and `whitespace-pre-wrap` together**,
  which cannot both apply: the wrap meant the box never overflowed, so long
  lines broke mid-token instead of scrolling.
- **The artifacts tree was a plain outline.** It now reads as a file explorer:
  per-extension icons, a folder icon that opens with its branch, dense rows,
  full-row hit target and an indent guide per level — all restyling
  darkraise-ui's own `TreeView` rather than replacing it.
- **The project page had no back button.** The mechanism already existed —
  `AppPageHeader` renders one whenever a page declares a `parent` — and the
  route never declared one. The label also moves into a tooltip, which closes
  a quieter defect: the top-nav layout hid the text label in CSS, so that
  layout already showed a bare arrow with nothing naming its destination.

### Notes

- **The Progress board's own design spec was wrong about the corpus, and the
  parsers found it.** Its task-id pattern dropped all 18 `TH*` rows while still
  parsing 291 and reporting a plausible distribution — which is where the
  spec's measurements came from. The corpus holds **309** tasks, not 312, and
  **zero** are `blocked` rather than the one the spec's motivation rests on.
  The golden tests therefore assert what a count cannot: the ledger's row ids
  and the epic files' task ids are the same set. Spec corrected in place.
- **The board is a projection, never a second store.** It writes nothing;
  `progress.md` stays canonical and hand-edited. The cost, stated rather than
  discovered: dragging a card is not possible, and the board fills only for a
  project whose corpus holds those planning files.
- Four Playwright tests cover what jsdom cannot — real row heights, a leaf
  indented past its folder, the folder icon's state flip, and board columns
  laid out side by side rather than stacked.

## v1.5.0 — 2026-09-03

**G-F cleared, and the faithfulness judge stopped being asked the wrong
question.** The gate that guards grounded Q&A over documents had missed its
precision bar at 0.888 since 2026-08-17. The miss turned out to be the
instrument, not the model.

### Fixed

- **The faithfulness judge was told its premise is "a stored fact".** It is
  not — in this role the premise is a raw document span, which may be a
  checklist item, an instruction or an `Expected:` line that asserts nothing.
  Replaying the old run from its cache at zero live calls showed **12 of its 14
  false-accepts were exactly that**: 11 markdown `[ ]` checklist items and 2
  directives, each read as a claim about the system because the prompt said the
  premise was a fact. The gold had been right all along; it caught a defect in
  the judge's specification. Precision went **0.888 → 0.9825**, recall 0.925 →
  0.9333, errors 23 → 10, and only two genuine false-accepts remain. The repair
  is role-scoped: the shared prompt is byte-identical, so the separately
  qualified entailment judge was not disturbed.
- **A qualification record could be minted from the wrong gold.** The
  faithfulness role's bars measure the same two metrics as the entailment
  role's, so every clearing claim/fact run also wrote a *faithfulness* record —
  off a gold containing no document spans, qualifying the span judge on a
  distribution it had never seen. A test asserted that outcome rather than
  catching it. Each role is now mintable only by the gold that scores it.
- **The span gold had no way to mint its own role's record**, so once the wrong
  door was shut the role was unmintable by anything. It now mints behind an
  explicit `--gate`, and writes nothing when a bar is missed.

### Changed

- **Grounded labels can now be served.** The faithfulness qualification record
  is minted and deployed, and production already resolves the verification
  purpose at the qualified identity. Two disclosures ride with the number and
  are recorded in the gate ledger rather than buried: it is a repaired
  instrument scored against the gold that exposed its own defect, and that gold
  is agent-authored. An independent confirmation on a fresh gold is still owed.

### The project artifact store (increments 1-8)

**The Checkpoints tab became something you can leave open and watch, and
filed documents stopped silently losing their biggest tables.** Increments 1
and 2 of the project artifact store (spec §3, §4, §6).

### Fixed

- **A markdown table no longer parses as one giant paragraph.** The
  `table` rule ships with markdown-it but is off under the commonmark preset,
  so a GFM table became a single block — measured at 235,716 / 298,677 /
  182,746 characters in three corpus files. The embedder truncates a block
  that size and the filing still reports success, so the loss was invisible
  at every surface. Tables now parse structurally: one `table` block carrying
  the header cells and column alignments, one `table_row` child per data row.
  A 300-row table that was one 60KB block is now 300 ordinary ones.
- **YAML frontmatter is captured instead of misparsed.** commonmark reads a
  closing `---` as a setext heading, so a document's frontmatter became part
  of its first heading block. It is now split off before tokenising and filed
  into `documents.properties.frontmatter`. Char spans still index into the
  original source, fences included — the offset is added back, so nothing
  that reads a span moved.

### Added

- **An oversized-block warning on every put surface.** `oversized_blocks` and
  `largest_block_chars` are measured once in the one writer, ride the
  `document_filed` event, and reach both the REST and MCP put replies.
  Counted, never refused: 27 corpus files exceed the budget and refusing
  would block the import, so the honest move is to report the degradation
  rather than invent a new failure mode. `null` rather than `0` when a
  re-filed document was unchanged — nothing was parsed, so nothing was
  measured, and `0` would be a clean bill the filing never issued.
- **`table` and `table_row` join the closed block vocabulary**, taxonomy-first:
  the two members landed before the parser emitted them, and doc 16 §9's
  stance line records the widening and why.

- **A project filter on the Checkpoints tab.** The predicate is pushed to
  `GET /events`, not applied to the loaded page: the journal read is capped at
  200 rows, so a busy project could otherwise push another off the page
  entirely and the filter would hide runs rather than narrow them. The option
  list accumulates every project seen since the tab mounted, because the
  filtered page contains only the project you filtered to — deriving options
  from it would collapse the list to your own selection and strand you there.
  The options deliberately do **not** come from `GET /api/v1/projects`: that
  route derives from `memories` alone, so a project holding only checkpoints
  would have been missing from its own filter.
- **Live polling, on a 15-second interval**, for both the run journal and the
  selected run's latest digest. An unfocused tab stops polling rather than
  running forever.

### Changed

- **The tab now states its own limit.** Checkpoint history shows *when* each
  save and resume happened, and only the newest note's text is readable —
  event payloads carry no step content by design, and no endpoint serves a
  run's past summaries. The surface says so where the reader is, instead of
  looking like a history that failed to load.

- **Documents round-trip.** `documents.content` is now the stored source of
  record: a filing keeps its source verbatim, so `blocks.char_span` finally
  indexes into something the schema holds. Both keyed reads take
  `include_content` (off by default — the source can be a megabyte): the REST
  reads add `content` to their envelope, MCP `document_get` answers
  `{content, blocks}` instead of its bare array. A bytes-filed source stores
  NULL rather than a decode of bytes that are not text.
- **`expected_hash` on put, as a compare-and-set.** File only if the document
  still holds the hash you last saw; omit it for last-writer-wins, which is
  what every existing caller gets. The predicate rides the writer's own UPDATE
  rather than a read-then-compare in Python — that distinction is the whole
  feature, since a Python comparison passes for both of two racing lanes and
  the second still clobbers the first. A stale hash answers 409 on the route
  and a `hash_conflict` envelope from the tool, both naming the hash that won,
  and `put` now echoes `content_hash` so there is something to precondition
  the next edit on.

- **A project workspace.** `/projects` lists every project the corpus holds
  with its memory, document and checkpoint counts;
  `/projects/$project` is the workspace — an Artifacts tab (uri-segment
  document tree, outline, block reader, section search) and a Progress tab
  (the pinned `planning/progress.md` ledger plus that project's checkpoint
  runs, scoped to it with no filter to wander out of). Both surfaces, and the
  personal `/documents` page, render one set of components rather than three.
- **`/documents` and `/projects` are in the sidebar.** `/documents` shipped
  with no navigation entry at all, so the surface existed and could not be
  reached from the app.

- **A per-block editor on the documents surface.** Click a block, edit its
  markdown source, blur to save. Editing converts a document to *block-first*:
  its `content` becomes a serialisation of its blocks, and `document_put` at
  that uri is refused afterwards (409, or a `direction_conflict` envelope over
  MCP) because a content push would strip the blocks an editing session
  placed. Four verbs on both doors — `block_update`, `block_insert`,
  `block_move`, `block_delete` — over one service.
- **The block read serves each block's own source.** `text` has always been
  marker-stripped, so an editor holding it edits a different string from the
  one stored. `source` is the stored one, sliced server-side by the block's
  span. It is also what lets a heading be *demoted*: delete the `##` and it
  becomes a paragraph again.
- **`divider` is a block type.** A thematic break minted no block at all, so a
  document's `---` section rules lived in its source and nowhere in its tree —
  and block-first conversion, which regenerates content from the tree, would
  have deleted every one. Measured on the imported corpus: this took the
  editor's refusal rate from **203 of 475 documents to 3**.

- **Nightly snapshots can now leave the host that runs the database.** A
  `backup_ship` job (04:30) dumps with the image's own `pg_dump` over the
  stack network, encrypts with each destination's `age` recipient, ships to
  every enabled destination, **reads each upload back and hashes it**, and
  prunes per destination. Three kinds ship: `local`, `ssh` (pinned host key,
  never trust-on-first-use) and `s3` (one client covers AWS, R2, B2 and
  MinIO). Uploaded is not restorable, so verification is a full byte
  read-back, never a checksum the remote computes for itself.
- **A Backups settings tab.** Destinations, retention, an enable switch, the
  last outcome per destination, and Run now. Secrets render as `***` and go
  back as `***`, which the server reads as "unchanged" — a private key never
  crosses the wire in either direction.
- **The `age` identity is never stored.** Only the public recipient is
  configurable; a snapshot carrying the key that opens it is not encrypted at
  rest, so decryption happens only where the operator's identity file lives.

- **A backup worker: a second machine serving nightly-restored snapshots
  read-only.** `docker-compose.worker.yml` runs the same image against a
  restored database, and the enforcement is a `darkmem_viewer` Postgres role
  holding `SELECT` and nothing else — not a flag. Every refused write arrives
  as SQLSTATE `42501` and is mapped to one 403 `read_only` envelope, so no
  per-route allowlist has to be maintained: routes rot, an error code cannot.
  `docs/runbook-backup-worker.md` is the bring-up.
- **A snapshot receiver, outside the app.** An https write door inside a
  read-only instance is a contradiction, so the receiver is a separate process
  sharing only a directory with the app — no database, no session, no import
  from `app.main`. A closure walk fails the build the moment one of those
  becomes reachable. It is the fourth destination kind, `worker`.
- **`restore.sh --from <destination>`.** Pull the newest snapshot off a NAS, a
  bucket or a worker, verify its checksum against what the destination reports,
  decrypt it **on the host**, and fall through to the same replay the plain form
  always did. The plain `restore.sh FILE.sql.gz` is pinned byte-compatible.
- **A snapshot inventory on the Backups tab**, with the exact restore command
  and a copy button — and deliberately no restore button. Restoring replaces the
  live database; §9.6 keeps it a shell command so a human reads the inventory
  first. A test clicks every button in the section and asserts none of them
  POSTs.
- **The read-only posture is on the Security tab**, including its cost: while
  the flag is on, a refresh reissues without blocklisting the token it replaces.

### Changed

- **Conversion refuses rather than converting lossily.** A document whose
  source contains something the block model cannot represent — a raw HTML
  block, a link-reference definition — stays content-first and says so, rather
  than being silently rewritten without it. It also refuses when a construct
  is representable but missing from *that document's* tree, which is what a
  document filed before its block type existed looks like.
- **`GET /api/v1/projects` derives from every corpus that carries a project**,
  not `memories` alone. A project holding only documents — exactly what a
  corpus import creates — was invisible in its own scope picker. The switcher
  now counts items across all three corpora, since a document-only project
  reading "0 memories" looks broken.
- **The document list is read in full rather than one page.** The list route
  clamps at 200 and carries no total, so a single page silently dropped more
  than half a several-hundred-file corpus. The workspace pages until a short
  one, dedupes by id, and says so on the surface when it stops at its guard.

### The artifacts workspace (increments 1-3, 5)

**Filed documents became something you can browse and read rather than a
list, and markdown started rendering as markdown.** The Artifacts tab of
`/projects/$project` (spec `2026-09-03-artifacts-workspace-revamp-design.md`).

### Fixed

- **Every heading rendered at the same size.** `properties.level` had been on
  the read surface since increment 8 and was unused, so an `h1` and an `h4`
  were visually identical. Heading text also bypassed the markdown renderer,
  so inline code in a heading showed literal backticks. Both render properly
  now, and the level drives the real tag, so the document outline and screen
  readers agree with what you see.
- **Nested lists lost their nesting.** Blocks rendered flat. `blocks.parent_id`
  was written by the parser and indexed by the baseline all along — it was
  simply missing from the block read surface, so no reader could see the
  structure. Serving it fixes both doors at once. Depth counts *list*
  ancestors only: every block under a heading carries that heading as its
  parent, so a naive parent-chain would have indented whole document bodies
  under their titles.
- **Ordered lists rendered as bullets.** The parser discarded the
  bullet-versus-ordered distinction entirely and wrote no properties for a
  list block at all, so nothing downstream could tell them apart. It now
  records the marker as spelled — sharing the convention `block_serializer`
  already owns, so a block-first round trip does not silently rewrite `1.`
  into a bullet.
- **A table's rows each rendered as their own table**, so columns did not line
  up across what is visually one table. Rows carry the table as their parent,
  so the fix is exact rather than adjacency-guessing.
- **A folder on the open document's path sprang back open when collapsed.**
  The reveal was re-derived every render and unioned into the displayed set,
  so it beat the user every frame. It now applies once per selection change —
  a search hit still reveals a document buried in a folder you never opened.

### Added

- **Document management on the reader pane**: a read/edit toggle, summarize,
  and delete behind a confirm dialog that states what delete actually does —
  it withdraws every block of the document as evidence and expires any fact
  left with no surviving source.
- **`POST /documents/{id}/summary`.** The summary panel could never fill,
  because `summarise_document` shipped with no caller anywhere in the app —
  no route, no job, no tool — so the existing `GET` read a property nothing in
  the tree could write. This is the missing door. It is an explicit act that
  spends a model call, so it is never fired by opening a document.
- **A reparse path for parser changes.** `content_hash` is the change gate, so
  re-pushing a document's own bytes files nothing — right for ordinary
  filings, and exactly what stops a *parser* fix reaching already-filed
  documents. `scripts/reparse_documents.py` re-files in place from
  `documents.content`, so it needs neither the original files nor a login.
  Its cost is re-embedding rather than parsing.
- **A test that the workspace panes actually fill the viewport.** jsdom
  performs no layout, so every unit assertion about the tree and reader panes
  passed whether they filled the window or collapsed to nothing. A Playwright
  spec now pins real heights, side-by-side placement and independent
  scrolling.

- **The Progress board's two parsers**, over `docs/planning/progress.md` and
  `docs/planning/tasks/*.md`, with golden tests against the real committed
  files rather than fixtures. No UI yet; the board is increments 2-4. Landing
  the parsers alone was the point, and it paid: the design spec's task-id
  pattern silently dropped all 18 `TH*` rows while still parsing 291 and
  reporting a plausible distribution, which is where the spec's own
  measurements came from. The corpus holds 309 tasks, not 312, and **zero**
  are `blocked` rather than the one the spec's motivation rests on. The tests
  therefore assert what a count cannot -- that the ledger and the epic files
  describe the *same* 309 ids -- and the spec is corrected in place.

### Notes

- **The baseline was regenerated** to add `documents.content` — the
  programme's only schema change. A deployed database must be dropped and
  recreated: it is already stamped `0001`, so `alembic upgrade head` finds
  current == head and migrates nothing, and `schema_guard` then refuses to
  boot. That is deliberate and has no override.
- **The two producers are separate by construction, not by a lock.** The
  host's `darkmem-backup.timer` is untouched and stays the floor that survives
  the app being down. Nothing serialises it against the job — different
  processes, and the per-job lock binds in-process only — so the separation is
  a directory (`/srv/darkmem-dumps` versus `/root/darkmem-backups`), a
  filename prefix (`darkmem-app-` versus `darkmem-`) and an hour of cron.
  Note `backup.sh`'s retention glob **would** match the job's files, so the
  two must never share a directory; the job's own prune is prefix-scoped and
  never touches a `.part`, so it cannot delete a systemd dump even where an
  operator has pointed both at one place.
- **The dump mount must be writable by the image's unprivileged user.** A host
  bind mount is not chowned by Docker, so `/srv/darkmem-dumps` is created and
  chowned to the image's uid at deploy time. The job refuses up front and
  names the directory and the uid, rather than surfacing as a truncated
  `.part` at 04:30.
- **The image grew** by `postgresql-client`, `age`, `openssh-client`, `rsync`
  and `boto3`. Stated, not hidden: the job cannot call `scripts/backup.sh`
  from inside the container, so it needs its own toolchain.
- **What "read-only" honestly means, stated wherever the feature is described.**
  Writes are prevented by the database role. The flag only prevents *spend* —
  LLM calls from jobs, chat and the reranker — and *noise*, where a quiet no-op
  or a clean 403 beats a 500. A reader who takes away "the flag makes it
  read-only" has been misled, and the runbook, the posture endpoint, the compose
  header and the code comments all carry the correction.
- **The restore loop verifies before it swaps.** It replays into a side
  database, migrates and stamps `schema_guard` there, and grants the viewer role
  — all while the app still serves the previous snapshot. A snapshot from an
  older baseline is *rejected*: the side database is dropped, the swap never
  happens, and the viewer keeps serving what it had. A worker that went down for
  exactly the snapshots one most wants to inspect would be worse than useless.
- **The worker's own costs.** Semantic search needs one live embed per query
  (there is no keyword-only fallback, by choice); repository *file* browsing
  degrades because the worker holds no clones, while DB-backed code-graph reads
  work; and journal and usage rows are silently lost, because both writers
  already swallow their own failures by contract.
- **No schema change** in increments 6 and 7, or in increments 1 and 2. `blocks.type` is plain `TEXT` with no CHECK, so the
  vocabulary widening is a code-side edit; existing rows are untouched, and a
  document re-shapes only when it is re-filed.
- The gate table is unchanged from v1.4.0 — nothing here touches a surface a
  gate governs.

## v1.4.0 — 2026-08-29

**A repository's recurring upkeep stopped being one flag nobody chose.**
`auto_sync` — a single boolean that fetched *and* re-indexed on one schedule,
on by default — is gone. In its place, five per-repo switches, all off by
default until an operator turns them on, and a standalone drift-scan job
that used to sweep every tracked repo unconditionally was retired into the
one loop those switches govern. The gate table is **unchanged from
v1.3.2** — nothing here touches a surface a gate governs.

### Added

- **Five per-repo indexing switches, both dialogs, all off by default.**
  `fetch_enabled` (interval `fetch_interval_seconds`, default 300s, floor
  30s) only moves the repo's `HEAD` — it never indexes. `index_on_commit_enabled`
  (interval `commit_poll_seconds`, default 60s, floor 15s) is the one thing
  that triggers a re-index, and only when `HEAD` has actually moved.
  `index_uncommitted` covers the one case `HEAD` can't see at all — a working
  tree edited without a commit — by hashing the tree against what was last
  indexed, but only while `index_on_commit_enabled` is also on: it widens
  that switch's own poll rather than running on a schedule of its own.
  Adding a repository still indexes it once regardless of any
  switch: a local-path repo at create time, a URL repo the moment its clone
  lands. Nothing recurs afterward unless the operator asks for it.

### Changed

- **`code_reconcile`'s always-on drift scan is retired; the same scan now
  runs inside the one recurring loop, per repo, only when that repo's
  `index_on_commit_enabled` switch is on and its `index_uncommitted` switch
  is also on.** The standalone Tier-C job used to hash
  every tracked repo's working tree on its own cron regardless of what any
  operator wanted, and it ran with no LLM to bound that unconditional cost.
  Because the scan now only ever fires for a repo whose operator explicitly
  opted in, a drift-caught change is indexed with the same LLM any other
  index tick would use — which means it is now **embedded**, not only
  structurally indexed. Under the retired job's `llm=None`, drift-caught
  content reached the symbol/edge graph but never `code_chunk_embeddings`,
  so it was present yet invisible to semantic code search; that gap is
  closed for every repo that turns the switch on.
- **The index lane never fetches.** Fetching and indexing are now two
  independent lanes on two independent schedules: the fetch lane only moves
  `HEAD`, and the index lane only observes it (`CodePipeline.run(...,
  pull=False)` on this path). Previously an unconditional pull ran ahead of
  every index tick, coupling a fetch to every index regardless of whether
  fetching was wanted on its own — for a darkmem-managed clone that meant
  `reset --hard`-ing away the very uncommitted content `index_uncommitted`
  exists to catch, before an index run ever saw it; for the operator's own
  local checkout it meant a fast-forward attempt on every tick rather than
  only when fetching was actually asked for (a conflicting local edit was
  never at risk there — that pull already refused instead of resetting). A
  fetch fault now logs and moves on without touching any switch; an index
  fault disables `index_on_commit_enabled` only, leaving `fetch_enabled`
  alone, because a transient network failure must not silently turn off a
  setting the operator chose.
- **`auto_sync` is gone from the API.** Every repo response, create and
  update payload now carries the five switches above instead. Manual
  reindex, the push webhook, and MCP `code_reindex` are unaffected — they
  bypass all five switches and keep fetching before they index, exactly as
  before.

## v1.3.2 — 2026-08-29

**Master pushes that cut no version were running no tests.** A gating mistake
in the release pipeline, fixed here. Nothing about the published artifact
changes.

### Fixed

- **Master is verified on every push, not only on releases.** When release.yml
  took over master pushes in v1.3.0, ci.yml lost its own push trigger and the
  `verify` job was gated on the release decision. A push carrying only `docs`,
  `chore` or `refactor` commits therefore derived no version, skipped
  verification, and ran nothing — so a refactor could break the suite and stay
  hidden until the next `feat` or `fix` push happened to run it.

  `verify` now depends on nothing and runs on every push; the release decision
  gates `prepare` instead, which is where the irreversible half begins. This
  also fixes the narrower case where a `fix` push with no changelog section
  failed at `plan` and took the whole test suite down with it — code that ships
  is now always tested, whether or not it releases.

## v1.3.1 — 2026-08-29

**The first release cut by CI named the wrong commit on one image tag.** A
one-line fix to the publish job. No behaviour changed and no gate moved; the
v1.3.0 image itself was correct, only its `sha-` tag misidentified what it
contained.

### Fixed

- **The short-sha image tag names the commit that was built.** The publish job
  derived it with `docker/metadata-action`'s `type=sha`, which reads
  `github.sha` — the commit that *triggered* the run. Since the pipeline builds
  the version-sync commit that `prepare` creates one step earlier, v1.3.0
  published `sha-544d349` for an image built from `a0c79463`.

  Every version tag was correct and the digest was right, so nothing shipped
  broken; what was wrong is the one tag whose entire purpose is to answer
  *which commit is running*. `prepare` now emits the short sha alongside the
  full one and the tag is spelled out from it, because GitHub expressions have
  no substring function to slice it at the point of use.

## v1.3.0 — 2026-08-29

**The MCP door grew a lock, and agents can now ask for a reindex of the files
they just wrote.** Three blocks: the MCP endpoint migrated to SDK v2 and now
requires a bearer key with per-tool scopes; a file-scoped reindex door landed on
both REST and MCP; and releases stopped being hand-cut. The gate table is
**unchanged from v1.2.0** — nothing here touches a surface a gate governs.

### Added

- **`/mcp` requires `Authorization: Bearer dmk_<key_id>_<secret>`.** There is no
  flag that disables it. Authorization is per tool, not per door: `capture`
  covers the 8 writers, `read` covers 25, `admin` covers the 1 repository-control
  tool. Scopes do not imply one another, and `tools/list` is deliberately not
  scope-filtered — an authenticated key sees the full catalogue including
  writers it cannot invoke. A keyed capture stamps `events.api_key_id` and
  `events.actor` on the journalled row.

- **The MCP server speaks protocol revision `2026-07-28` on `mcp==2.1.1`.** The
  v2 SDK renamed the server object to `MCPServer`; `FastMCP` is gone.

- **File-scoped reindex, on both doors.** `POST /api/v1/repos/{id}/reindex-files`
  and the `code_reindex` MCP tool take the paths an agent just committed, with
  an optional commit sha darkmem verifies read-only before claiming. Named files
  are **unioned into** the git diff rather than replacing it, and are
  content-hash filtered first so a repeated list cannot manufacture phantom
  index debt. One `repo_reindex_requested` event records the outcome per
  request, whichever branch it took.

- **An API keys card in Settings**, rebuilt around the key list.

### Changed

- **Releases are cut by CI, from a push to master.** `release.yml` derives the
  next version from the conventional-commit types since the last tag, runs the
  full pipeline, publishes to Docker Hub and GHCR, and **only then** writes the
  tag and the GitHub release — a tag that exists is now a tag whose image was
  published. A push carrying no `feat`, `fix`, `perf` or breaking commit cuts
  nothing, and a push whose derived version has no section in this file fails
  before the suite runs. `scripts/release.sh` no longer tags; it is the local
  pre-flight that proves the version serves before you push.

- **Extraction spends roughly 730 fewer tokens per ingest**, and the last four
  prompts are guarded, delimited and seeded like the rest.

### Fixed

- **Minified bundles are no longer indexed.** `IGNORED_EXTENSIONS` had listed
  `.min.js` and `.min.css` since it was written, but the filter tested
  `PurePosixPath.suffix`, which returns only the final extension — so neither
  entry could ever match. Files already indexed become undiscoverable and
  `code_reconcile` strips them on its next tick.

- **A file-scoped run that indexes nothing now says so.** The all-filtered early
  exit returned before the completion broadcast, so a caller naming only
  unchanged files heard nothing — the one outcome the bucket reporting exists
  for. Both exits now report through one payload builder, and the SPA renders
  "Nothing to index" over an account of what was skipped rather than
  "Indexed 0 files".

- **Retriable LLM vendor failures are retried three times.**

- **Extraction stops splitting datastores across types**, and no longer reads a
  selection as a replacement.

- **`reason` cites only memories that fit the context**, and chat citations keep
  the rider unsliced.

- **Bcrypt verification for API keys runs off the event loop.**

## v1.2.1 — 2026-08-26

**The published image could not index a repository, and nothing said so.**
A one-line omission in the runtime stage, fixed here. No gate moved and no
behaviour changed beyond the image gaining a binary it always needed.

### Fixed

- **`git` is installed in the runtime image.** Code indexing shells out to the
  git binary — `RepoManager._run_git` runs `git clone/fetch/rev-parse/diff` as
  a subprocess, and no pure-Python git is in the lockfile — but the runtime
  stage never installed one. `build-essential` lives in the builder stage,
  whose layers deliberately never ship, so the published image had no git at
  all and every repository operation failed with `git: not found`.

  Nothing announced it. The image boots, migrations run, `/health` answers 200
  and the healthcheck passes; the sole symptom is that indexing never works.
  It survived undetected because the deployment holding it had zero
  repositories, so the path was never exercised. Found while wiring a local
  checkout into the indexer, not by any test.

  The regression test asserts against the **runtime stage alone**: a git
  installed only in the builder would satisfy a whole-file grep while leaving
  the shipped artifact exactly as broken.

## v1.2.0 — 2026-08-25

**A face, and a dialog that listens.** Two blocks, neither of them near a gate.
darkmem got an actual mark — the first one it has had that means anything — and
the Add repository dialog stopped throwing away the account you picked. The gate
table is **unchanged from v1.1.0**, and nothing in this release touches a
surface a gate governs.

### Gate verdicts — unchanged

| Gate | Verdict | Moved this release? |
|---|---|---|
| G-C — L2 → deriver | **CLEARED** 2026-08-16 | no |
| G-D — L2 → L3 | **CLEARED on the entailment role**; contradiction still misses | no |
| G-E — L3 → F7 | **not yet measured** — production holds 0 articles | no |
| G-F — core → H1 | **not yet measured** — the claim/span gold does not exist | no |

### Added

- **A brand mark that follows the accent.** An open ring enclosing three
  tapering rungs: the ladder the verification ladder already is, inside the arc
  of a retrieval. It replaces a purple bolt built from fifteen blurred ellipses
  that turned to mush at the 16px a favicon is actually rendered at, and it
  finally supplies `public/logo.svg` — the file `BrandLogo` has requested since
  the day the sidebar shipped, which was 404ing into the fallback letter tile
  nobody recognised as a missing asset.
- **Colour tracks the operator's accent, one mechanism per surface**, because an
  SVG loaded through `<img>` or `<link rel="icon">` is an isolated document that
  cannot read `--primary`. The sidebar paints `logo.svg` as a **CSS mask** over
  `hsl(var(--primary))`, so the shape lives in the file and the colour in the
  token, with no JavaScript. The favicon is **rebuilt at runtime** as a data
  URI, since no mask reaches a browser tab. That constrains the artwork to one
  ink with alpha for tone — a mask reads only the alpha channel — which is why
  the mark's tonal steps are opacity rather than a second colour, and it
  constrains any future edit to it the same way.
- **The mark's geometry has one source.** Three surfaces need byte-identical
  shapes, so all of them derive from `src/lib/brand-mark.ts` and a test fails
  the build when a committed asset drifts from what it emits. Regenerate with
  `node scripts/generate-brand-assets.mjs`.

### Fixed

- **The Add repository dialog reverted every account you chose.**
  `useGitAccountsData` rebuilt its return object on every render, so the
  dialog's preselect effect — which listed that object in its dependencies —
  re-ran after every render including the one your own click caused, and
  overwrote the choice with the provider's default. Selecting "Custom token for
  this repo…" appeared to do nothing at all; a non-default account never
  reached the request. Memoising the hook fixes the cause for all four of its
  consumers, and a ref guard makes the selection structurally un-clobberable
  rather than merely un-clobbered by today's referential luck. The existing
  tests missed it because they only ever asserted the *preselected* value and
  submitted — nothing changed the selection.

### Nearly shipped broken

The accent-tracking favicon passed its unit tests while painting the wrong
colour in a real browser. `ThemeProvider` writes its tokens as inline styles on
`<html>` from its own effect, and React runs child effects **before** parent
ones — so reading `--primary` on mount read the *previous* accent, and nothing
re-triggered, because the component's own dependencies were already at their
final values. The tab sat on blue while the app ran green. The fix observes the
root element instead of subscribing to theme state, which removes the ordering
question rather than timing around it, and is pinned by a test that fails
against the one-shot version. Recorded because the unit tests were green
throughout and only the browser disagreed.

## v1.1.0 — 2026-08-24

**Three blocks, and none of them moves a gate.** Vendor connections became
shared rows instead of eight inline copies; the documents door got its MCP half
and its write verbs; and every vendor call now records what it cost. The gate
table below is **unchanged from v1.0.0** — that is the honest headline, because
two of these blocks touch surfaces a gate governs and neither earned anything
from it.

### Gate verdicts — unchanged

| Gate | Verdict | Moved this release? |
|---|---|---|
| G-C — L2 → deriver | **CLEARED** 2026-08-16 | no |
| G-D — L2 → L3 | **CLEARED on the entailment role**; contradiction still misses | no |
| G-E — L3 → F7 | **not yet measured** — production holds 0 articles | no |
| G-F — core → H1 | **not yet measured** — the claim/span gold does not exist | no |

Two things worth stating rather than leaving to inference. **The two-door
documents ruling clears no gate**: `documents.write` and `documents.retrieval`
went two-door on the owner's ruling of 2026-08-23 because those verbs generate
nothing and label nothing, not because G-F moved. `POST /documents/qa` is still
single-door, still gated, and still withholds every answer. And **the provider
layer did not disturb the judge**: `base_url` and `api_kind` are two of the six
fields the entailment qualification binds to, and both moved onto a provider
row this release. The live identity hash was re-derived from production after
the cutover and is still `fd39e7b2c47fa375` — the record minted 2026-08-17
stands, unre-minted.

### Added

- **LLM providers are shared rows again** (owner ruling 2026-08-20, reversing
  doc 04 §7). One `llm_providers` row per vendor connection, referenced by a
  NOT NULL `provider_name` from each of the eight purposes. The reversal rests
  on one thing the flat shape could not do: a credential rotation or an
  endpoint move must reach every purpose that uses it with no re-apply step,
  and only a live reference does that. Resolution stays **one query with one
  join returning the same flat `LLMPurposeConfig`** — a query-counting test
  pins it — because `benchlib`'s cache key and the judge's identity hash both
  fold the same six field *names* off the resolved object.
- **The judge's provider is frozen field-wise, not row-wise.** `base_url` and
  `api_kind` are refused on the provider serving `verification`; `api_key`
  still rotates, deliberately, because rotating a credential is not a model
  swap and freezing it would block a rotation that is owed. The
  unauthenticated setup door refuses the seeded provider names and the same
  exclusivity the authenticated door enforces, so the least-authenticated door
  in the tree is not the one place the shared state can be produced.
- **A cutover script, because a plain restore cannot cross this change**
  (`backend/scripts/cutover/llm_providers_transition.py`). An old-schema
  `llm_purpose_configs` dump carries columns the new table does not have, and
  stripping them still violates the NOT NULL FK against a database holding zero
  provider rows. The procedure is in `docs/runbook-deployment.md`, alongside a
  new **additive-baseline** path rehearsed against a copy of production, and
  two restore traps that cost the whole `events` journal in rehearsal — a
  missing per-fingerprint child table, and `psql` exiting **0** over a partial
  restore without `ON_ERROR_STOP`.
- **The documents door's write and retrieval verbs, on both doors.** `put`,
  `search`, `outline`, `get` and `delete` reach REST and MCP through the same
  `document_door` functions, resolving a caller-named target by id or by
  `(project, uri)` through one producer so the refusals cannot drift. `(project,
  uri)` is the document's identity: re-filing a path updates in place.
- **`block_embedding_refresh`, the backstop the inline embed needs.** It closes
  three shapes of drift that each leave a document that exists and is
  unfindable with no symptom — an embed that failed after its filing committed,
  an embedder rotation, and a document filed before the door shipped. It
  resolves its fingerprint from a **real embed call**, not a data probe: a
  backstop writer's whole job is filling an empty partition, and "which
  fingerprint already holds data" is biased toward the wrong answer by
  construction. That took three review rounds to land and the reasoning is
  recorded in the module.
- **Token and cost tracking.** One `llm_usage` row per vendor call, written on
  the recorder's **own session** — a usage row on the caller's session is
  rolled back with the work it describes, which would delete the evidence for
  exactly the failed calls this feature exists to surface. Cost is BIGINT
  micro-USD: money never touches a float. Prices are an operator `config` row
  over shipped defaults, with **three** rates rather than two, because a cached
  input token bills at roughly 5% of input on DeepSeek and 50% on OpenAI.
- **An unmeasured call stores NULL, never 0.** A vendor that stops reporting
  usage must not read as a free model, so the token columns are nullable and
  the surface says `not measured` rather than printing a fabricated zero. The
  local Ollama embedders are a *measured* zero, which stays a distinguishable
  state.
- **A usage surface, an outliers view, a Flags tab that documents every
  section, an Appearance tab, a project scope catalog derived from the corpus,
  and a rebuilt graph visual language** — selection by focus rather than
  brightness, entity-type borders, two edge tiers, and every control moved into
  the settings panel.
- **A `Release` workflow, and it is the only path to a registry**
  (`.github/workflows/release.yml`). Tags only; a push to master publishes
  nothing. It reuses the branch CI rather than copying it, builds once and
  pushes the same digest to Docker Hub and GHCR, and creates the GitHub release
  last so the announcement cannot precede the artifact.

### Changed

- **Redeploy this machine after every change that lands** (owner ruling
  2026-08-21). This host runs the instance the owner reviews, so a
  merged-but-undeployed change leaves them looking at the previous build —
  reporting bugs already fixed, or missing ones that are not. The second is
  worse, because the review reads as a pass. Scoped to changes that alter the
  running artifact, and it is a **deploy, not a release**: no tag, no registry.
- **The verification ladder's threshold resolution moved to
  `app/services/ladder_config.py`, and the split is load-bearing.** Invariant
  15's tree-wide scan matches any line naming the ladder module — prose
  included — so the settings door could not have imported the thresholds from
  there without an allowlist entry, and an allowlist entry buys a route the
  whole module. Every moved name is re-exported, so no import changed.
- **Resolution now returns a report, not just a value**, for the ladder as it
  already did for G-C's bars: a clamp that speaks only through `logging`
  renders identically to no clamp, so an operator who types 1 into the settings
  form was shown 1 and never learned the ladder was still running at 3. The
  door answers with the committed value, the effective value, and which of
  *default* / *honoured* / *clamped* happened, per parameter. A clamped value
  is still **written**, so a later measurement licenses the value already
  chosen.
- **`MEASURABLE_FLAGS` gained the five graph channels.** The comment said they
  had no config row, which was stale from the day T2.32 landed all five in
  `FEATURE_FLAGS_DEFAULTS` — and the Flags tab read that same absence off a
  missing *response field* and rendered "no config row exists yet" to
  operators. Missing field and missing row are not the same absence, and only
  one of them was ever true.

### Fixed

- **The document door's `unchanged` path was a silent no-op after an embedder
  rotation.** A re-push of byte-identical content is the caller's one natural
  repair for a filing whose block write committed and whose embed failed
  afterward. It resolved the fingerprint with a data probe, which after a
  rotation prefers the stale, already-complete partition — so it reported
  nothing to repair while retrieval read the empty one. Both callers now
  resolve from a real embed call, which is why **every `unchanged` re-push now
  spends one embed call** unconditionally. That is the stated cost, not a
  regression.
- **A block the embedder rejects no longer starves the ones behind it.** The
  sweep fetches `ORDER BY b.id`, so a failing batch is the *same* failing batch
  every tick; a run that simply raised would be loud in `job_runs.last_error`
  and would still never sweep anything. A failed batch is now retried
  block-at-a-time and the poison row settles alone — the shape
  `memory_buffer`'s flush already uses.
- **An oversized document no longer stages a half-filed row for the caller's
  next commit.** `MAX_BLOCKS` can only be known after parsing, so the filing
  runs inside a SAVEPOINT and the refusal rolls back the document, its blocks
  and the `document_filed` event.
- **Deleting a document withdraws its provenance first.**
  `fact_sources.source_ref` carries no foreign key, so a cascade cannot reach
  it. The delete withdraws the block sources, expires any fact left with no
  surviving source — never one still sourced otherwise, never one already
  expired — and journals a `sources_changed` event per affected fact. It writes
  no `verification_status`: the rung stays the ladder's decision.
- **The Flags tab lost saved values in three places**, found in the owner's own
  review, along with three further Security-tab defects and an unparseable
  `dimensions` value that was accepted rather than refused.
- **Metering kwargs were leaking into benchlib's chat cache key**, which would
  have missed every cached entry on every machine — and G-C's clear rests on an
  independent party reproducing a run byte-identically at 0 live calls.
- **The usage subject now carries the project through every pipeline entry**,
  and a mixed-project batch claims **no** project rather than the first entry's
  — a wrong answer where `None` is a missing one.
- **`chat_completion_stream`'s metering had no test**, while
  `test_usage_wiring.py`'s own docstring claimed both streams were pinned. Four
  tests now cover the compat trailing usage frame (which arrives with
  `choices: []`, an empty list rather than an absent key), Ollama's `done`
  chunk, a client-abandoned stream (recorded unmeasured, never dropped), and a
  failed stream.
- **Demo mode took itself down from the Activity Jobs tab, and the symptom was
  a wedged gate rather than an error.** The usage reads mount in the Activity
  Jobs and Pipeline tabs and shipped without `enabled: !DEMO`, so in demo mode
  they 401 — and `handleUnauthorized` answers a 401 with
  `window.location.href = "/login"`, a hard navigation. The demo browser was
  bounced off the page it was on, every later demo spec landed on a login form,
  and the `--full` gate's Playwright leg ran into its 1800s wall reporting only
  "TIMED OUT". Every usage read now carries the guard `useProjects` already
  had.
- **`/documents` had the same defect and had it since v1.0.0.** Not a
  regression this release — it is what the new guard below found on its first
  run, on a route no demo-project spec covered. `useDocuments` and its two
  keyed siblings now carry the guard too.
- **That defect class is now structural rather than remembered**
  (`frontend/tests/demo-makes-no-api-calls.spec.ts`). It has shipped three
  times — `useProjects`, the usage reads, the documents reads — and each time
  the damage appeared on a page that never made the request, which is what made
  it expensive to find. The new spec walks every route the demo fixture claims
  to render and fails on any `/api/v1/` request, naming the URL and the route
  that issued it, with a separate assertion on the login form so the failure
  says *the page is gone* rather than *one stray GET*. Proven red against a
  reverted guard before it was kept.
- **Invariant 13's job count was stale in `CLAUDE.md`** — 21 when T4.09
  counted, 24 today. Restated so the finding no longer rests on a number that
  goes stale every time a job lands, which is the failure shape invariant 23
  exists to police.

### Known limits, carried forward

- **G-E cannot be measured on this deployment.** Production holds 0 articles
  and 0 documents against 50 memories and 98 triples. The research loop is
  armed but **not driving**: it has no `JobRegistry` job on purpose, and
  `ResearchGatherer` has no in-tree implementation, so an MCP agent with real
  web access has to call `research_run`. Nothing in this tree produces a
  research origin on its own.
- **The contradiction judge role is still unqualified**, missing recall for the
  fourth time across two vendors. No consumer may ship on its verdicts, and
  `groundedness_gate` stays closed.
- **Both live model keys are owed a rotation.** The repo history was rewritten
  and the keys are out of tracked files, but both were also pasted into chat
  transcripts — copies outside this repo's control — so rotation, not the
  rewrite, is what actually retires them. Owed before publication.

## v1.0.0 — 2026-08-20

**Everything remaining, and the gates carry verdicts — except two, which do
not.** Two feature blocks that had been parked ship here — documents/PKM and
the hardening pass — and two of the four open gates get a measured answer
rather than a hope.

**The version rule, ruled 2026-08-15: _both_.** Each of G-C, G-D, G-E and G-F
must carry a verdict, **and** the target is that each clears. Those are different
things, kept apart because one half is not fully in our control: no amount of
work guarantees a model clears a bar. **A measured miss ships. An unmeasured gate
does not.**

### Gate verdicts

| Gate | Verdict | Where |
|---|---|---|
| G-C — L2 → deriver | **CLEARED** 2026-08-16, independently verdicted | `gate-ledger.md`, "G-C on the grown corpus" |
| G-D — L2 → L3 | **CLEARED on the entailment role** 2026-08-17; the contradiction role misses and stays open | `gate-ledger.md`, "G-D on the fresh gold", "G-D ruling" |
| G-E — L3 → F7 | **not yet measured** — production holds no articles to measure | `gate-ledger.md`, "G-E" |
| G-F — core → H1 | **not yet measured** — the claim/span gold does not exist | `gate-ledger.md`, "G-F" |

**The last two held this section at `unreleased` until 2026-08-20, and the tag
was cut anyway — by the owner's explicit ruling, overriding the rule above.**
That is recorded rather than smoothed, because the rule it overrides is stated
on this very version: G-E and G-F carry **no verdict**, so v1.0.0 ships having
measured two of its four gates, not four. Nothing about the numbers changed; a
different call was made about shipping without them.

Both remain blocked on inputs no amount of coding produces: G-E needs a real
corpus accumulating over weeks, and G-F needs a gold set only the owner may
author (`autonomous-loop.md` §7). Neither is a task anyone can pick up and
finish.

**What this costs, stated plainly.** `groundedness_gate` stays closed, so no
article may be served labelled grounded, and no consumer may ship on the
contradiction judge's verdicts — the contradiction role missed its bar for the
fourth time across two vendors. A reader who takes "v1.0.0" to mean "all four
gates cleared" would be wrong on three counts, which is why this paragraph
exists. The measured verdicts that *are* in the table above stand exactly as
they were.

### Added

- **Documents and PKM, the whole block** — parsers for PDF, markdown and notes;
  a `documents`/`blocks` writer with strip-before-rewrite keyed on
  `document_id`; a semantic block retrieval channel; grounded Q&A with a
  span-support faithfulness check **before** serving; on-demand Tier-C lift;
  block-sourced facts where one document is one origin; single-document
  summaries and emergent cross-document connections; and a Documents UI that
  labels its own horizon.
- **The faithfulness metric was defined and barred before any of it was built**
  (`TH1.01`), which is the ordering the whole harness exists to enforce:
  span-support coverage = entailed answer-claims ÷ total answer-claims, per
  answer, with `faithfulness_coverage_bar` = 1.0, and the gate's own
  qualification bars at 0.95 precision / 0.90 recall. The denominator is **every
  sentence of the served answer body, with no exclusion channel** — any
  generator-reachable exclusion rule lets the generator move its own
  denominator, and silencing a claim is the same move as passing it one step
  earlier.
- **API keys and webhooks** (`T4.01`–`T4.05`): a bearer credential with a closed
  scope set, `events.api_key_id`/`actor` stamped on keyed writes, key use
  surfaced in the per-object timeline, and a push webhook receiver that reuses
  the ordinary index pipeline.
- **An exposed-deployment posture** (`T4.03`). `trust_proxy_headers` is now the
  exposure switch rather than only a rate-limiter setting: with it on, an
  explicit `cookie_secure=false` is **clamped** to true rather than honoured,
  and the clamp is reported three ways — a boot warning, a journalled event, and
  a field on `GET /auth/security-posture`. A silent clamp would be a security
  posture nobody could audit.
- **The research loop is armable from the UI** (`T3.28`) — configure, enable and
  trigger, where arming previously meant a manual database write.

### Changed

- **The re-run trigger re-derives; it does not re-file** (`T3.28`), and the
  difference is not cosmetic. The journal stores no finding text by design, so
  the only evidence a re-run can reach is the memories the run filed: a deleted
  one is unrecoverable, and a surviving one already carries that finding's exact
  content and origin key — so re-filing writes a duplicate row asserting the
  same claim under the same origin, and corroboration counts DISTINCT origins.
  A re-file is therefore either impossible or inert. Re-derivation is neither:
  the surviving memories go back through the pipeline and are recomputed under
  the current taxonomy, extractor and dedup while no origin, count or row moves.
- **Single-worker stays, and now for the measured reason** (`T4.09`, `T4.10`).
  The audit found 38 in-process assumptions, 17 of which break at two replicas —
  the WebSocket fan-out, the job scheduler (no lease, so all 21 jobs fire N
  times per tick), the per-IP login limiter, the live orchestrator swap and
  seven unlocked job cursors — and `backend/app` holds no cross-process
  serialisation primitive to build on. The knob has three silent spellings
  (`--workers`, `WEB_CONCURRENCY`, compose `deploy.replicas`) and a tripwire
  test now fails the build on any of them.

### Fixed

- **A Playwright suite had been asserting nothing since it shipped.**
  `frontend/tests/documents.spec.ts` never signed in, so its three assertions
  ran against a logged-out page and passed vacuously. Found by running the full
  gate rather than the floor.
- **`seed_partition` could leave a half-registered fingerprint** (`T4.11`), and
  the same fixture residue was escaping two other suites (`T4.13`).
- **Polling and the webhook could still double-index the same push** (`T4.16`).
- **Two scopes gated nothing** (`T4.15`, `T4.21`). `capture` and `read` were in
  the closed scope set and enforced nowhere, which is worse than absent: a scope
  that appears to restrict and does not is a false assurance printed on a
  credential.

### Known limits

- **G-D cleared on one of its two roles, and the other one failed.** The
  contradiction role missed recall at 0.7875 against an unmoved 0.95 — the
  fourth miss across two vendors. It gates the Tier-C contradiction scan, which
  since T2.109 is not a veto input and so certifies no label G-D guards; that is
  the ruling's basis. But **"articles may ship" does not imply "a qualified
  contradiction judge exists"**, and it will not for the foreseeable future. If
  that role is never re-attempted by roughly 2026-11-12, the per-role split
  reads retroactively as burial rather than separation.
- **The judge that qualified had already seen 41% of the pairs it qualified
  on.** 114 of the 280 measured pairs had been met in two earlier blind
  sittings on the same gold, and all three pairs the judge was known to disagree
  with had been retired before the run. Both facts were disclosed at the time in
  the dispatch that ran them and were then **misstated on every canonical
  surface** — the ledger and the run report each said no pair had been contacted
  before, because the runner emits that line from an attempt counter that cannot
  see a resample or a probe. Corrected, with the worst case computed rather than
  asserted: restoring all three retired disagreements and assuming the judge
  misses each gives recall 105/113 = 0.9292 against 0.90, precision unchanged,
  so no verdict moves. **What is not available is the sentence "cleared on pairs
  it had never seen."**
- **G-C's clear is real and its corpus is authored end to end by the measured
  party.** Every capture, origin, repo and the single dispute; the deterministic
  detector has never fired on an unauthored contradiction; the human-rejection
  arm has never met a human; and one of the three gate paths exists only under
  the harness's simulated clock.
- **A grounded label still is not served.** G-D clearing and a grounded label
  reaching a reader are two events, and only the first has happened.
- **Production's schema had silently drifted from the baseline**, and the
  mechanism that allowed it is still there. Because the pre-freeze baseline
  regenerates in place as revision `0001`, `alembic upgrade head` is a no-op on
  an already-stamped database, so every deploy reported a clean migration while
  shipping code against a schema it lacked — five columns missing, and the
  `article_synthesis` job dying on every run because of it. Repaired by the
  policy's own drop-and-recreate. **Nothing checks that a deployed database
  matches the baseline its image was built from**, and until something does,
  this recurs on the next baseline change.

## v0.5 — 2026-08-15

**An agent can now research a subject and file what it found as ordinary
memories, with one origin per source it actually read.** That last clause is the
whole feature: corroboration counts distinct origins, so a loop that refetches
the same page twice would manufacture its own agreement. The loop is **built and
not armed** — `research_run` refuses while the `auto_research` config row is
disabled, which is the default, and pointing it at real subjects is a separate
decision.

### Added
- The research loop, filing through the ordinary capture door (`T3.07`). One
  batch call per run, so a run either lands whole or does not land: an
  over-budget run refuses rather than filing a truncated version of what it
  found. It ships with **no `JobRegistry` job on purpose** — a cron'd research
  pass would refetch the same sources every tick, which is exactly the
  manufactured-corroboration hazard the origin rule exists to prevent.
- Its one door is MCP, and that is an argument rather than a convenience
  (`T3.27`). `research_run` files evidence *the caller* gathered:
  `ResearchGatherer` has no in-tree implementation by design, because a model
  without web access would invent sources. On MCP the caller is a gatherer; on
  REST neither caller is, so an honest REST shape would need the gatherer the
  design refuses. The tool takes no `source`, no `origin_key` and no `ctx`, so
  the header ladder that steers every other capture's identity has no route in,
  and a finding naming either field is a loud error rather than a dropped key.
- Distinct-origin stamping for researched sources (`T3.08`). One origin per
  evidence **source** — the identity is the source's, never the run's and never
  the finding's — and the canonicalisation aims to collapse the variation a
  fetcher produces mechanically, so that a refetch, a re-run or a paraphrase of
  one page adds no origin. That is a tested property held by generated-spelling
  tests and named pins, not a structural guarantee: three earlier restatements
  of it as a closure did not survive their reviews, and every falsification so
  far is pinned. Researched
  origins stay machine-distinguishable from observed ones, so a measurement that
  pools them does it on purpose.

### Changed
- The census's independence disclosure counts by connected component rather than
  by row (`T2.123`). A component of k mutually-duplicate rows yields k(k−1)/2
  findings and collapses k−1 rows, so the old arithmetic was right only while
  every component was exactly two wide. Entailed corrected 166 → 167;
  contradicted unchanged at 80/78.
- `SINGLE_VALUED_RELATIONS` stays empty, and now says why (`T2.120`). All
  sixteen relations fail the at-most-one-object-per-subject test, and every
  exclusive slot in the misses that motivated it is an **attribute** — port,
  version, TTL, scrape interval — which this taxonomy does not store as a
  relation at all. The hoped-for capacity cannot be added at any membership,
  so the argument lives beside the frozenset rather than being quietly dropped.

### Fixed
- **The origin canonicaliser split one page into two origins**, found by review
  before the loop was armed (`T3.08`). Six spellings did it —
  percent-encoded paths, percent-encoded unreserved characters, dot-segments,
  punycode versus unicode, NFC versus NFD, a duplicated identical parameter —
  and each is a
  spelling this repo's own `httpx` produces. Two variants seven days apart met
  the two-origin bar, which is a promotion off a single page. Repaired
  merge-only, with all seven failing shapes proven red first and three
  over-merge controls guarding the other direction.
- **And the same claim was falsified a second time, before this release was
  cut.** v0.5's version review attacked the repaired canonicaliser with 26
  same-source pairs and found **eleven more splitting pairs across nine
  defect shapes**. The one that matters: this
  module normalised hosts through Python's IDNA**2003** codec while `httpx`
  emits IDNA**2008**, so `straße.example` and the `xn--strae-oqa.example` the
  client produces for it were two attributable origins — one page, and at seven
  days' spacing a promotion. The host pass now uses the `idna` package with
  `httpx`'s own parameters, which also stopped IDNA2003 conflating
  `strasse.example` with `straße.example`, two genuinely different hosts. The
  other eight: a trailing-dot FQDN keeping its dot once a default port came
  off, `:0443` not recognised as `:443`, IPv6 zero-compression, a
  scheme-relative href written without its slashes, an embedded tab or newline
  the URL spec strips, dot-segments popping past the root and gluing the path
  onto the host, and an unparseable id falling back to its pre-normalisation
  spelling.
- **And that repair needed a repair, which is the part worth reading.** It
  reattached a non-default port to the host *before* the trailing-dot, IPv6 and
  IDNA passes ran — so it relocated the ordering bug rather than removing it,
  and every one of those passes stopped working whenever a port was present.
  Worse, strict `idna.encode` raises on the embedded colon where the old
  IDNA2003 codec had tolerated it, so the fix for "one page must not become two
  origins" *created* exactly that failure for an IDN host carrying a port. The
  port is now split off before any canonicalisation and reattached at the end.
  Found by the review of the fix, not by the fix's own tests.
- **And the repair of the repair did it again, which settled the approach.**
  Widening the slash fold to one slash made `tmp` the host of
  `file:/tmp/a.pdf` — the spelling `httpx` itself emits for
  `file:///tmp/a.pdf` — so the third consecutive hand-written repair
  introduced the split class it was closing, again found by the review rather
  than by the fix's own tests. The fold is now scheme-aware (no single slash
  rule is correct for both `https:` and `file:`), and the suite carries the
  reviewers' own instrument instead of relying on hand-written pairs: a
  deterministic generator produces URL spellings mechanically and asserts
  every one agrees with the spelling `httpx` emits for it. On its first run
  that property found three splits no review round had seen — percent-encoded
  hosts, percent-encoded NFD bytes in paths and query values, a leading-zero
  non-default port — each repaired red-first.
- Two fail-open defects in the research loop, also found by review (`T3.07`).
  `bool("false")` is `True`, so a malformed `enabled` value armed the master
  switch — the one field where failing closed matters most was the one without a
  strict guard. And the run committed twice, so a raise in the journal window
  reported a durable filing as failed and would have double-filed on retry.
- The judge-verdicts directory leaked synthetic files under real judge
  identities (`T2.122`). It held 96 files rather than the 80 first measured — a
  stray `verdicts/verdicts/` subdirectory carried 16 more, left by an earlier
  unfinished manual quarantine. 95 removed, the 1 genuine artifact kept with its
  sha recorded outside the gitignored directory.

### Known limits
- **"Merge-only by construction" is retired as a phrase.** It has been stated
  as a structural guarantee twice and falsified twice, by the only two parties
  who attacked it on purpose. It is a tested property with named pins, and the
  next person to extend the canonicaliser should assume there are more splits
  nobody has looked for. Two are deliberate: `;` versus `&` in a query is not
  variation a fetcher produces, and two punycode labels decoding to different
  strings are different hosts.
- **Built is not armed, and armed is not measured.** The loop refuses by
  default. When it is armed, the origins it mints are weaker corroboration than
  independent capture produces: two same-day research origins carry the same
  source kind, so there is no kind diversity between them and they hold at three
  rather than promoting at two.
- **The entailment census is not clean, and the disclosure stands even though
  the verdict does not move** (`T2.118`). Five duplicated entailed propositions
  across seven findings, one component three rows wide, and five of Rule B's 72
  entailed rows restate propositions from the contacted population. The minimum
  pass is 156/173 rows against a measured 0.9827, so the verdict is
  unthreatened — that is a reason to report the duplication, not to stop
  counting it.
- G-C and G-D are still open, so a promoted fact still serves as `candidate`
  with `verification_unmeasured`. Nothing in this release changes what a badge
  means.

### Also in this tag
Gate-track work that landed after v0.5's scope closed. It ships here without
being part of the headline, because the gate track is not a version
(`docs/planning/RELEASES.md`):
- The homelab instance is provisioned fresh on the baseline, with nightly
  backups that actually prune — the dump script had no retention, and an
  unpruned nightly cadence on the host that also runs the database is a slow
  disk-fill that takes production down with it (`T1.54`).
- Qualification records are per consumer **role** over one judge identity, so
  the article consumer stops being gated on a discrimination it never makes
  (`T2.117`).
- G-C's and the judge's bars are floors at runtime, not only in source: a
  `config` row below a floor clamps back unless a licence names the parameter
  and cites its argument, the direction is carried **per bar** because G-C's six
  do not share one, and a clamped run now says so in the artifact rather than
  only in a log nobody configured (`T2.126`, `T2.127`, `T2.128`).
- The promotion corpus grew past the decidable band and the deterministic
  contradiction detector was armed, giving the false-promotion audit a
  numerator for the first time (`T2.129`). Measuring what that verdict was
  worth showed the rule itself was a coin flip at the bar at every sample
  size, so it is now scored on the exact Clopper-Pearson upper bound rather
  than the observed
  rate — a strict tightening that moved no bar and flipped the audit axis from
  a pass to a fail (`T2.130`, `T2.132`).

## v0.4 — 2026-08-12

**The vault writes articles about your subjects, and every sentence has to earn
its place.** A subject with enough corroborated facts gets a synthesised
write-up whose claims each link to the fact that entails them. Nothing about
those articles is badged as verified yet — the groundedness gate is still open,
so they ship labelled `candidate`, which is what the label means rather than a
placeholder for it.

### Added
- Article synthesis runs for real (`T3.02`). A daily Tier-C pass picks eligible
  subjects, gathers only their non-disputed corroborated/confirmed facts, and
  stores one article per subject with the fact ids it was built from
  journalled, so a bad article is traceable to its inputs. Disputed and
  candidate facts are excluded at the query, never filtered out of a draft the
  model already saw.
- Claim-level entailment and coverage routing (`T3.03`). Every sentence is
  checked against the facts it cites, and an article below the coverage
  threshold routes to review instead of shipping. Coverage is served as
  "claim-support coverage" — the fraction of sentences a verified fact entails
  — because that is what the number is.
- The one hard foreign key (`T3.04`). A citation can never dangle, which is
  safe only because facts are invalidate-not-delete; both halves are now
  pinned by test, including two scans proving nothing in the tree deletes a
  fact.
- Staleness and debounced re-synthesis (`T3.05`). An article whose supporting
  facts moved is *labelled* stale and stays readable; re-synthesis waits for a
  quiet period so a burst of corroborations produces one rewrite rather than
  one per tick, then supersedes the old article and keeps the lineage.
- The Articles tab and article detail on live data (`T3.06`), with a read door
  the API contract named and nothing had built (`GET /knowledge/articles`,
  `/articles/{id}`, and MCP's `article_get`). Every claim's citation is one
  click away, and the coverage number shows in Simple as well as Advanced,
  because it is an honesty signal rather than technical detail.
- Articles joined retrieval as their own channel (`T3.23`), stale label
  included — a stale article is returned labelled, never withheld.
- A held re-synthesis now reaches a human. When a rewrite cannot be grounded,
  the *subject* is routed to review while the standing article keeps its badge
  and its place in retrieval; before this, a subject whose knowledge could no
  longer be grounded was visible only as a counter on a job tick.

### Changed
- An invalidated fact now makes its article stale. The staleness gate reads the
  verified **and still believed** set, so a fact whose belief window closed
  stops propping up an article that cites it (doc 09 §4.4, ruled and amended).
- A chronically ungroundable subject is no longer re-attempted every tick. It
  costs one attempt per change to its facts instead of one per day, and the
  attempts it skips are counted rather than silently not happening.

### Fixed
- The Playwright leg of the merge gate collided with any darkmem already
  running on `:8000` — and did not fail cleanly: it health-checked the other
  instance and aimed its admin-setup at it.
- A `subject_key` written without its type half took down the whole articles
  listing with a 500, and stopped the staleness sweep at its first odd row.

### Known limits
- **Articles ship unlabelled, deliberately.** Coverage cannot be measured until
  a verification judge qualifies (G-D), so every article reads `candidate` with
  its coverage shown as "not measured" — a measured absence, not a zero.
- G-E's two bars are stated and pinned, and the runner that reads production
  coverage now exists — but nothing has measured them. Its first run against
  production reports 0 live articles and *not evaluable*, which is the honest
  standing state while G-D is open rather than a fault.
- Synthesis needs corroborated facts, and no fact has ever left `candidate` on
  this machine. A fresh install will correctly show no articles at all.

### Also in this tag
Gate-track hardening landed after v0.4's own scope closed. It ships in this
tag without being part of the release's headline, because the gate track is
not a version (`docs/planning/RELEASES.md`):
- The entailment gold's resample certification is now bound to the pairs it
  certified, so a verdict flipped after a sitting turns eligibility red
  instead of leaving it green on a certification of a different file.
- G-D's anti-tuning disclosure now counts contacts with the gold's *pairs*
  rather than its file bytes. Editing a rationale — or writing the
  certification into the file — used to reset that counter silently.
- The coverage-distribution runner behind G-E, read-only against production.

## v0.3 — 2026-08-11

**Context stays live, and visible.** Push can follow your working context
instead of only firing at session start — and everything it pushes is on
screen, per day and per target.

### Added
- Inject records render in the day timeline and the calendar (`T3.20`). A push
  names its target, its item count and its budget, and opens to show exactly
  what was pushed, per layer. The used-against-budget pair is the diagnostic
  half: a push that spent 40 of 4000 tokens and one that hit its ceiling look
  identical from the id list alone and mean different things about what the
  agent was *not* told. `/events/calendar` gained an `event_type` filter so the
  days holding an inject can be marked without counting rows client-side.
- Watch mode (`T4.06`): re-inject as the project, the open file or the declared
  context shifts. Off by default, and the opt-in is a config flag read at two
  doors. Every refresh journals what shifted — without that, a re-inject is
  indistinguishable from a session start and "you can see the swap" reduces to
  seeing that something was pushed twice.
- Auto-capture in the browser extension (`T4.07`), strictly opt-in. The chat
  surfaces are optional permissions the browser withholds until you grant them,
  so an install that never opted in cannot read those pages at all. Opting in
  captures from that point on; it does not send the conversation you already
  had. A `REC` badge shows while it is running.
- The Distribution tab now shows watch state per target, the curb, and a live
  inject log read from the journal (`T4.08`).

### Changed
- The curb is enforced server-side. A watch refresh re-reads it every time and
  refuses while it is on, so curbing stops the next swap rather than the next
  session — the client is the thing being curbed, which is why the client does
  not decide. The tab's copy said the flag had no enforcer; that stopped being
  true with watch mode and now says so.

### Fixed
- The demo resume block and the demo inject record were prose where the real
  branch reads a payload, so the mockups could not be expanded and could
  disagree with the live surfaces without any test noticing.

### Known limits
- Nothing drives watch mode yet: the client-side loop that would call it is the
  Claude Code plugin, outside this repo. The session-start inject still has no
  HTTP door, so the curb governs the watch cadence today and will govern that
  one the moment it has a caller.
- Verification, groundedness and coverage labels remain withheld pending G-C,
  G-D and G-E.

## v0.2 — 2026-08-11

**Your agent can resume.** A run saves a compact digest, and the next session
loads it instead of reloading the context window it burned.

### Added
- Truth-first content fill for the managed block (`T3.10`): items are chosen
  under one token budget, verified rows first, with a cold-start pass that
  admits candidates only when nothing verified landed — under the *same*
  budget, so a cold-start block is never an over-budget one. An empty L3 tier
  yields an empty tier, never an error; every fresh install has zero articles.
- Resume as a specialised inject (`T3.17`): the latest checkpoint leads that
  same fill as its `lead`, charged against the same budget rather than
  computing a second one. A run with no checkpoint degrades to the ordinary
  inject — a first session has nothing to resume from, which is the common
  case, not a fault. A resume is journalled only when the digest actually
  survived the fill, so the stream counts resumes rather than session starts.
- The Session-checkpoints view is live (`T3.21`): per-run history grouped from
  the journal, the latest digest one click away, and copy-resume. Both doors
  now serve `resume_line` and `token_estimate` — derived from the resume path's
  own functions, so what you copy is what your session receives rather than a
  second rendering of it.

### Changed
- Checkpoints are pinned out of the vault by test, not by convention (`T3.18`):
  no fact-ladder reach, no verification column, no badge on the wire, no
  embedding partition. A checkpoint is what an agent said about its own run.
- `resumed` takes its recorded place in the activity taxonomy.

### Fixed
- The demo resume block spelled `darkmem:resume:begin` markers that no shipped
  code writes. Copied into a `CLAUDE.md`, the real writer would not have
  recognised them and would have appended a second, live marker pair beneath.

### Known limits
- Nothing writes a checkpoint automatically yet. The client half — the hook
  that authors a digest at session end and the one that loads it at session
  start — is the Claude Code plugin, which lives outside this repo.
- Verification, groundedness and coverage labels remain withheld pending G-C,
  G-D and G-E, exactly as in v0.1.

## v0.1 — 2026-08-10

First release. Everything below already existed and had never been tagged or
deployed.

### Added
- Buffered capture on four doors (REST + MCP, single and batch) with
  `origin_key` identity resolution.
- Hybrid retrieval — semantic + keyword under RRF, with an optional reranker.
- The entity/relationship graph, closed taxonomy, supersession, and
  fingerprint-partitioned embeddings.
- Code indexing: symbol graph, code search, blast radius, wiki.
- 21 scheduled jobs under one registry, including the Tier-C dream family —
  20 with real bodies; `article_synthesis` is still a registered placeholder,
  and its productive run is v0.4's.
- The verified-fact vault and its ladder — **badges serve as `candidate` until
  G-C and G-D clear**, which is deliberate, not a defect.
- Session checkpoints on both doors.
- The SPA: memories, knowledge, activity, code, settings.
- Minimal TypeScript and Python SDKs, generated from the live contract.
- A browser capture extension.

### Known limits
- Verification, groundedness and coverage labels are withheld pending G-C, G-D
  and G-E. The system ships **unlabelled** by design (`T2.95`).
- Data is disposable: the schema is not frozen and a schema change drops and
  recreates the database.
- The product version fields read `0.2.0` before this release and had never
  been managed or shipped under it. They reset to `0.1.0`, where the ladder
  starts.

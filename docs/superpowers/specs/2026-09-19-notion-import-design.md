# Notion import and page attachments — design

Date: 2026-09-19. Status: approved in chat, awaiting written-spec review.

## 1. Goal

Let the operator import a Notion workspace export into their personal notes
(`/notes`, the page tree of the `personal` project), keeping hierarchy, text,
databases, links between pages, and images/files. Because pages have no file
storage today, this adds **page attachments** as a general page feature
(storage, serving, editor upload) and builds the import on top of it.

Delivered in three increments, each shippable alone:

1. Attachment storage, routes, cleanup and backups (§3).
2. Editor rendering and upload of images/files (§5).
3. The Notion import route and its dialog (§4, §5.1).

Out of scope: Notion's HTML export, Notion API sync, database views
(filter/sort), re-import/merge into an earlier import, MCP access to pages or
attachments (pages stay REST-only).

## 2. Decisions taken in brainstorming

| Question | Ruling |
|---|---|
| Attachments | Stored, not dropped |
| Storage | Disk volume; metadata in Postgres |
| Editor | Render images/files and allow upload anywhere |
| Databases | A page holding the CSV as a table, row pages as children |
| Parse location | Server-side, one transaction |
| Links between pages | Rewritten to `/notes?page=<id>` |
| Destination | One new root page per import |

## 3. Attachment storage

### 3.1 Data model

New table `page_attachments`, added by regenerating `0001_baseline.py` (the
one-revision rule; drop/recreate, no migration — greenfield ruling):

| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | Also the on-disk file name |
| `page_id` | uuid NOT NULL | FK `pages(id)` ON DELETE CASCADE |
| `project` | text NOT NULL | Denormalised for project-scoped queries |
| `filename` | text NOT NULL | The user's name, display only, length-bounded |
| `content_type` | text NOT NULL | Sniffed from magic bytes, not trusted from the client |
| `size_bytes` | bigint NOT NULL | |
| `sha256` | text NOT NULL | Integrity check on serve-side restore verification |
| `created_at` | timestamptz NOT NULL default now() | |

Index on `page_id`. No dedup by `sha256`: one row per upload keeps deletion
semantics trivial.

### 3.2 Disk layout

A new compose named volume `attachment_data` mounted at
`/app/data/attachments` (settings key `attachments_dir`). File path is
`<attachments_dir>/<id[:2]>/<id>`. **No user-controlled string ever reaches a
path.** Writes go to `<path>.part` then `os.replace`, so a crash never leaves a
truncated file under a final name.

The worker compose file mounts the same volume name on the worker host.

### 3.3 Routes (REST-only, `api/routes/pages.py` or a sibling module)

- `POST /api/v1/pages/{page_id}/attachments` — multipart, one file. 201 with
  `{id, url, filename, content_type, size_bytes}`. 404 on an unknown or
  trashed page; 413 above `attachment_max_bytes` (config, default 50 MB),
  enforced while streaming, not after.
- `GET /api/v1/pages/attachments/{attachment_id}` — serves the bytes.
- `DELETE /api/v1/pages/attachments/{attachment_id}` — 204; row deleted, file
  removed after commit.

`url` is `/api/v1/pages/attachments/<id>`. Serving is cookie-authenticated like
every SPA route, so `<img src>` works same-origin.

All three answer `read_only` on the backup worker for the write verbs through
the existing mechanisms (SQLSTATE 42501 for the row, and
`refuse_when_read_only` for the upload, since it writes a file before any row).

### 3.4 Serving safety

- Always `X-Content-Type-Options: nosniff` and
  `Content-Security-Policy: sandbox`.
- `Content-Disposition: inline` **only** for `image/png`, `image/jpeg`,
  `image/gif`, `image/webp`; everything else — SVG and HTML included — is
  `attachment` with an RFC 6266 `filename*`.
- `ETag` = sha256; attachments are immutable, so
  `Cache-Control: private, max-age=31536000, immutable`.

### 3.5 Referencing from blocks

A block references an attachment through ordinary markdown carrying its URL:
`![alt](/api/v1/pages/attachments/<id>)` for an image,
`[name](/api/v1/pages/attachments/<id>)` for a file. No new block type, no
schema change to `blocks`. Page content stays plain markdown.

### 3.6 Lifecycle

- Trashing a page keeps its attachments (restore must be lossless).
- Emptying the trash cascades the rows; `purge_trash` collects the ids first
  and unlinks the files **after** its commit. A failed unlink is logged and left
  for the cleanup job.
- Deleting a block that references an attachment does not delete it (undo and
  paste can re-reference it).
- New hourly job **`page_attachment_cleanup`** (constant
  `PAGE_ATTACHMENT_CLEANUP_JOB_KEY`), `config_schema` `grace_hours` (default
  168). It removes (a) files with no row, older than one hour (a crash between
  file write and commit), and (b) rows older than the grace period that no
  block of their page references, then their files. Job roster goes
  24 → 25; `tests/test_code_deriver.py` derives it from `app/main.py`.

### 3.7 Backups

`pg_dump` alone would silently omit every attachment.

- `scripts/backup.sh` also writes `darkmem-attachments-<stamp>.tar.gz` (a tar of
  the volume, taken via the running container) beside the dump, pruned with the
  same `BACKUP_KEEP`. Its prune glob must not match the dump's and vice versa.
- `backup_ship` adds `darkmem-app-attachments-<stamp>.tar.gz` to each shipment:
  `age`-encrypted per destination, read back and hashed like the dump, pruned by
  its own prefix.
- The backup worker's `restore-cycle.sh` unpacks the matching tarball into the
  worker's volume after the side-database verification and before the swap. A
  missing tarball is a warning, not a rejection (older snapshots have none).

Restore order in `docs/runbook-deployment.md`: database, then tarball. An
attachment row with no file serves 404 and is removed by nothing (the job only
removes files without rows and unreferenced rows), so the runbook says to
restore both halves from the same stamp.

## 4. Notion import

### 4.1 Route

`POST /api/v1/pages/import/notion` — multipart: `file` (zip), `project`
(must be a known project; the SPA sends the personal one). Behind
`refuse_when_read_only`. Streams the upload to a temp file under the
attachments volume (same filesystem, so accepted attachment files are
`os.replace`d, not copied), capped by `notion_import_max_bytes` (config,
default 1 GB) → 413. Returns 201 with the report (§4.7). Synchronous: page
creation embeds nothing inline (the sweep does), so the cost is parse + insert.

Only the **Markdown & CSV** export is accepted. A zip whose entries are `.html`
pages and no `.md` is refused 422 with "re-export from Notion as Markdown &
CSV". An outer zip whose entries are `*Part-N.zip` is treated as one export: the
inner zips are read in part order as one logical tree.

### 4.2 Hostile-zip defences (checked before any write)

- Entry names are never joined into filesystem paths; everything is read
  through `zipfile` by name. Names are normalised (`/`-separated, `..` and
  absolute components rejected → entry skipped and reported).
- Caps: `notion_import_max_entries` (default 50 000) and
  `notion_import_max_uncompressed_bytes` (default 5 GB) summed from the central
  directory **and** enforced while reading (the directory can lie).
- Symlink entries (mode bits) are skipped. Nested zips are opened only at the
  top level for the Part-N case, never recursively.

### 4.3 Building the tree

Notion names a page `Title <32-hex>.md` and puts its subpages in a sibling
folder `Title <32-hex>/`; a database is `Name <32-hex>.csv` (newer exports also
write `Name <32-hex>_all.csv` — the `_all` one wins) with its row pages in the
folder. The importer:

1. Indexes every entry by the 32-hex id stripped from its name, and derives the
   title from the remainder (also URL-decoded).
2. Builds parent/child from folder nesting.
3. Orders siblings alphabetically by title (the export carries no sidebar
   order). Row pages follow CSV row order where the id or title matches.
4. Assigns every page a UUID **before** writing any content, so links resolve
   in both directions.
5. Places everything under one new root page titled
   `Notion import — <YYYY-MM-DD HH:MM>` at the end of the project's root.

A folder with no matching `.md` becomes an empty page named after the folder.

These naming rules come from Notion's documented export behaviour and are
**unverified against a real export in this repo**; the first implementation
task obtains or constructs a realistic sample and pins it as a fixture.

### 4.4 Translating content

A Notion-specific pre-pass rewrites the markdown, then the existing page parser
and `_flatten_headings` run exactly as in `create_page`:

- A leading `# Title` line equal to the file's title is removed and becomes the
  page title.
- `<aside>…</aside>` becomes a `callout` block (variant `note`; a leading emoji
  stays in the text).
- `- [ ]` / `- [x]` items become `todo` blocks with `checked`.
- A link whose target resolves (after URL-decoding, relative to the file) to
  another `.md`/`.csv` in the export becomes `/notes?page=<uuid>`. An
  unresolvable internal link keeps its text and loses its target, counted in
  the report.
- A link or image whose target resolves to another file in the export becomes
  an attachment (§3), re-pointed to its served URL. Files referenced by several
  pages are stored once per referencing page (keeps §3.6's per-page lifecycle
  simple). A target missing from the zip becomes the text
  `[missing file: <name>]`, counted. External `http(s)` links are unchanged.
- Database row pages keep their leading `Key: value` property lines, turned
  into a bullet list at the top.
- A database page's body is its CSV as a markdown table (header row = CSV
  header; cells have `|` escaped and newlines replaced with spaces).

Content that `reproduces_source` would refuse (frontmatter fence,
link-reference definitions) is not refused: the pre-pass strips a frontmatter
fence and inlines link-reference definitions into their references, then
counts them. An import never fails on one page's content.

### 4.5 Bounds

A page over `MAX_CONTENT_CHARS` or `MAX_BLOCKS` is truncated at a block
boundary to fit and reported, not fatal. A single attachment over
`attachment_max_bytes` becomes a missing-file placeholder, reported.

### 4.6 Atomicity and journal

Extract `create_page`'s insert body into a helper the import calls per page
inside **one** transaction (one advisory lock `root_lock_key(project)` for the
whole import). Attachment files are written before commit; on any exception the
transaction rolls back and every file written by this import is unlinked. A
crash mid-import leaves only row-less files, which `page_attachment_cleanup`
removes. One `page_created` event per page, as a normal create writes; plus one
`pages_imported` event (new `EVENT_TYPES` value, taxonomy-first) on the root
page carrying the report's counts, no titles or text.

### 4.7 Report

```
{ root_page_id, pages_created, databases, attachments_stored,
  attachment_bytes, warnings: [{path, kind, detail}] }
```

`kind` ∈ `missing_file`, `unresolved_link`, `truncated`, `skipped_entry`,
`oversize_attachment`, `stripped_source`. `warnings` capped at 500 entries plus
a count of the rest.

### 4.8 Known limits (documented, not fixed)

- Notion's markdown export writes toggles as ordinary bullet lists, so toggles
  import as lists.
- Synced blocks, embeds and equations import as whatever text Notion wrote.
- Database views, relations and rollups are not reproduced; relation cells
  import as the text Notion wrote.

## 5. Notes UI

### 5.1 Import dialog

An "Import from Notion" item in the page tree header menu opens a
`darkraise-ui` `dialog` with `file-upload` and `progress`:

- One-line instruction: Notion → Settings → Export → Markdown & CSV, include
  subpages and files.
- Upload through `XMLHttpRequest` (for progress events), then an
  indeterminate state while the server imports.
- On success: the report (counts plus a collapsible warning list) and a "Go to
  imported pages" button that selects `root_page_id`. The `["pages", project]`
  query is invalidated.
- On error: the refusal message (413, 422) in the dialog.
- Hidden under `DEMO`, which must make no API calls.

### 5.2 Editor: images and files

Fixed mapping in `lib/block-mapping.ts`:

- A paragraph whose **only** content is `![alt](<attachment url>)` ↔ BlockNote
  `image` block.
- A paragraph whose only content is `[name](<attachment url>)` ↔ BlockNote
  `file` block.
- Anything else (an image inside other text, a non-attachment image URL) stays
  a `rawInline` atom; the atom renders a thumbnail when its target is an
  attachment URL.

Both directions go through the existing canonicalisation, so an unedited image
never diffs as an edit. Server-side nothing changes (they are paragraphs), so
`sync-tree.ts` needs no new refusal mirror.

### 5.3 Upload

BlockNote's `uploadFile` option calls `POST /pages/{id}/attachments` and
returns the URL; paste, drag-drop and the block's own upload button all route
through it. An error surfaces as a `sonner` toast and inserts nothing.

## 6. Testing

- **Backend pytest:** attachment routes (upload, 413 while streaming, 404 on
  trashed page), serving headers per type (SVG and HTML forced to download),
  purge unlinking files after commit, the cleanup job's two arms, backup
  tarball production. Import against fixture zips: nested pages, database with
  row pages, `_all.csv`, Part-N outer zip, internal links both directions,
  attachments, missing file, zip slip, symlink, entry-count and
  uncompressed-size caps (including a lying central directory), HTML export
  refusal, oversize page truncation, and a failure injected midway leaving no
  rows and no files.
- **Guards leg** (CLAUDE.md list) after registering the routes and job.
- **vitest:** image/file block mapping round trip and canonicalisation; import
  dialog states; upload hook error path.
- **Playwright** via `backend/scripts/e2e/run_playwright_e2e.py`: import a
  fixture, see the tree and a rendered image.

## 7. Documentation

- `CLAUDE.md`: job roster (25, `page_attachment_cleanup`), page route count,
  attachments volume and its backup, the Notes paragraph.
- `docs/two-door-parity.md`: `pages.attachments` and `pages.import` single-door
  rows.
- `docs/runbook-deployment.md` and `docs/runbook-backup-worker.md`: the volume,
  the tarball, restore order.
- `CHANGELOG.md` entry for the release carrying increment 3.

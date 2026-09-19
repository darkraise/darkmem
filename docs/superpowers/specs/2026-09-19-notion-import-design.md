# Notion import and page attachments — design

Date: 2026-09-19. Status: revision 2, after the first independent review
(32 findings, all addressed below); awaiting re-review and owner approval.

## 1. Goal

Let the operator import a Notion workspace export into their personal notes
(`/notes`, the page tree of the project whose `kind` is `personal`), keeping
hierarchy, text, databases, links between pages, and images/files. Pages have
no file storage today, so this adds **page attachments** as a general page
feature (storage, serving, editor upload) and builds the import on top of it.

Three increments, each shippable alone:

1. Attachment storage, routes, cleanup job, backups (§3).
2. Editor rendering and upload of images/files (§5.2-5.3).
3. The Notion import route and its dialog (§4, §5.1).

Out of scope: Notion's HTML export, Notion API sync, database views
(filter/sort), re-import or merge into an earlier import, MCP access to pages
or attachments (pages stay REST-only), deleting an attachment by hand.

## 2. Rulings

| Question | Ruling |
|---|---|
| Attachments | Stored, not dropped |
| Storage | Disk volume; metadata in Postgres |
| Ownership | **Project**, not page (copy-paste between pages must keep working) |
| Editor | Render images/files and allow upload anywhere |
| Databases | A page holding the CSV as a table, row pages as children |
| Parse location | Server-side; parse off the event loop, write in one transaction |
| Links between pages | Rewritten to `/notes?page=<id>` |
| Destination | One new root page per import |
| Export setting | The operator enables "Create folders for subpages"; a flat export imports flat with a warning |

## 3. Attachment storage

### 3.1 Data model

New table `page_attachments`, added by regenerating `0001_baseline.py`
(one-revision rule; drop/recreate, no migration — greenfield ruling):

| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | Also the on-disk file name |
| `project` | text NOT NULL | The owner. FK to `projects(name)` if that table's key allows, else unconstrained like `pages.project` |
| `uploaded_for_page_id` | uuid NULL | FK `pages(id)` ON DELETE SET NULL. Provenance only; never decides lifetime |
| `filename` | text NOT NULL | Display only; control characters stripped, at most 255 characters |
| `content_type` | text NOT NULL | One of the four sniffed image types, else `application/octet-stream` (§3.4) |
| `size_bytes` | bigint NOT NULL | |
| `sha256` | text NOT NULL | The `ETag`, and the backup manifest input (§3.7). Never re-hashed per request |
| `created_at` | timestamptz NOT NULL default now() | |

Index on `project`. No dedup by `sha256` across uploads: one row per upload
keeps the lifetime rule trivial. The import stores each distinct file of an
export once, however many pages reference it.

### 3.2 Disk layout

Setting `attachments_dir`, env `ATTACHMENTS_DIR`, defaulting to the relative
`data/attachments` for host-side dev (the `repo_manager.py` pattern). In the
image: a new compose named volume `attachment_data` at `/app/data/attachments`.
The `Dockerfile` creates that directory **before** its `chown -R app:app /app`,
or the named volume is created root-owned and the unprivileged `app` user
cannot write it. Boot asserts the directory is writable (the
`backup_ship._assert_writable` pattern), and on the backup worker asserts only
that it is readable.

File path: `<attachments_dir>/<id[:2]>/<id>`. **No user-controlled string ever
reaches a path.** Every write goes to `<path>.part` then `os.replace`.
`<attachments_dir>/.staging/` holds import staging (§4.1); nothing that walks
attachments descends into a dot-directory.

### 3.3 Routes

REST-only, in a new module `api/routes/page_attachments.py` registered with its
own `include_router` in `main.py` **before** the SPA mount (which must stay
last, `test_spa_edge.py`). Both paths are two-segment under `/pages`, so they
cannot collide with `/{page_id}`.

- `POST /api/v1/pages/{page_id}/attachments` — the **raw body** is the file
  (`Content-Type: application/octet-stream`, the name percent-encoded in
  `X-Filename`). Multipart is not used: FastAPI's `UploadFile` spools the whole
  body before the handler runs, so a size cap could only ever be checked after
  the fact. The handler refuses on `Content-Length` above
  `attachment_max_bytes` (config, default 50 MB) before reading, then consumes
  `request.stream()` with a running counter and refuses 413 the moment the
  counter passes the cap, removing the `.part`. The page must be live
  (404 otherwise). 201 with `{id, url, filename, content_type, size_bytes}`.
  Order: `.part` → `os.replace` → row insert → commit.
- `GET /api/v1/pages/attachments/{attachment_id}` — serves the bytes
  (`FileResponse`, which streams). 404 through the standard error envelope when
  the row or the file is missing.

No DELETE route: nothing calls one. Lifetime is the cleanup job's (§3.6).

`url` is `/api/v1/pages/attachments/<id>`. The session cookie is
`samesite=strict`, so a cookie-authenticated GET is safe cross-site and
`<img src>` works same-origin.

Upload is behind `refuse_when_read_only`. That dependency's docstring and
CLAUDE.md scope it to external calls; the argument is the same for a filesystem
write the database never sees, and both are amended to say so.

### 3.4 Content type and serving safety

- **Type detection** is hand-written magic-byte checks for exactly
  `image/png`, `image/jpeg`, `image/gif` and `image/webp` (libmagic is not in
  the image; `imghdr` is gone in Python 3.13). Everything else is stored as
  `application/octet-stream`. The client's `Content-Type` is never persisted.
- Every response: `X-Content-Type-Options: nosniff`,
  `Content-Security-Policy: sandbox`, `ETag` = `sha256`,
  `Cache-Control: private, max-age=31536000, immutable`.
- `Content-Disposition: inline` for the four image types only; `attachment`
  for everything else, with an ASCII `filename=` fallback and an RFC 5987
  `filename*` (CR/LF stripped, percent-encoded).
- What actually defeats a polyglot is `nosniff` plus a type we sniffed
  ourselves: `CSP` and `Content-Disposition` act only when the file is opened
  as a document, not when an `<img>` loads it.

### 3.5 Referencing from blocks

Ordinary markdown carrying the URL: `![alt](/api/v1/pages/attachments/<id>)`
for an image, `[name](/api/v1/pages/attachments/<id>)` for a file. No new
block type and no change to `blocks`.

### 3.6 Lifetime and the cleanup job

An attachment lives while **any block of any page in its project, trashed pages
included,** references its URL. Trashing and restoring a page therefore never
touch attachments; emptying the trash deletes blocks, which may leave
attachments unreferenced for the job to collect. `purge_trash` is unchanged.

New hourly job **`page_attachment_cleanup`** (constant
`PAGE_ATTACHMENT_CLEANUP_JOB_KEY`; `config_schema`: `grace_hours` default 168,
`staging_max_age_hours` default 6). One run:

1. **Unreferenced rows.** Collects the referenced ids per project with one
   `regexp_matches(text, '/api/v1/pages/attachments/([0-9a-f-]{36})', 'g')`
   pass over `blocks WHERE page_id IS NOT NULL`, then deletes rows older than
   `grace_hours` whose id is not in that set, committing, then unlinks their
   files. The grace period covers an upload whose block the editor has not
   saved yet.
2. **Row-less files.** Files older than one hour with no row (a crash between
   `os.replace` and commit). Stale `*.part` files older than one hour.
3. **Stale staging.** `.staging/<uuid>/` directories older than
   `staging_max_age_hours` (well above the import time budget, §4.1).

Filesystem walking and unlinking run in `asyncio.to_thread`. The job registers
in `app/main.py`; the roster goes 24 → 25, and the hand-written roster tuple in
`tests/test_code_deriver.py` and CLAUDE.md's prose count are both edited.

### 3.7 Backups

`pg_dump` alone would silently leave out every attachment. The files are
backed up as a second artefact family, a full tarball, **written only when the
set changed**, so an unchanged multi-GB set is not copied nightly.

**Manifest.** The sorted `id:sha256` list over `page_attachments`, hashed. A
tarball is written only when this hash differs from the newest existing
tarball's (kept in a sidecar `.manifest` file beside it, or in the job's state
row for `backup_ship`). Restore pairs a dump with the **newest tarball whose
stamp is ≤ the dump's stamp**, which is correct precisely because an unchanged
set writes none.

**Order: dump first, then tar.** A file without a row is harmless and swept;
a row without a file is permanent.

- **`scripts/backup.sh` (host floor).** After the dump, it computes the
  manifest through the same `psql` access, and if it changed, runs `tar`
  through `docker run --rm --entrypoint tar -v <attachment volume>:/src:ro`
  on the darkmem image. That works while the app container is down, which the
  floor exists for; `docker compose exec` into the app would not. Flags:
  `--exclude='*.part' --exclude='./.staging' --warning=no-file-changed`, and an
  exit status of 1 ("file changed as we read it") is accepted explicitly, since
  `set -euo pipefail` would otherwise fail the backup. Written as `.part` then
  `mv`, like the dump. Named `darkmem-attachments-<stamp>.tar.gz`, pruned by its
  own glob to `BACKUP_ATTACHMENTS_KEEP` (default 3). The dump prune glob
  `darkmem-*.sql.gz` cannot match it.
- **`backup_ship` (app producer).** One stamp minted per run and shared by both
  files. The tarball, `darkmem-app-attachments-<stamp>.tar.gz[.age]`, is a
  **separate family**: its own predicate beside `_is_snapshot` (which keeps
  matching dumps only), its own per-destination `attachments_retention_keep`
  (default 3), and a prune that lists and sorts each family separately. Widening
  `_is_snapshot` instead would let tarballs, which sort after dumps by name,
  take every "newest" slot and prune the dumps. Encrypted, read back and hashed
  like the dump. `worker_receiver.py`'s `SNAPSHOT_NAME` pattern is widened to
  accept the second family. Any pull path that would materialise a whole object
  in memory (the S3 `stream()`) must stream the tarball in chunks; the container
  has a 1 GB memory limit.
- **Backup worker.** `docker-compose.worker.yml` mounts a volume at
  `/app/data/attachment-store` and sets
  `ATTACHMENTS_DIR=/app/data/attachment-store/current`, a symlink.
  `restore-cycle.sh` picks the matching tarball (rule above), unpacks it into
  `attachment-store/gen-<stamp>` **while the viewer still serves the previous
  generation**, and re-points `current` with an atomic symlink swap in the same
  step as the database rename, removing the old generation afterwards. A cycle
  that aborts before the swap leaves both halves on the previous generation. A
  missing tarball is a warning and keeps the current generation.

`docs/runbook-deployment.md`: restore the dump, then the tarball paired by the
rule above.

## 4. Notion import

### 4.1 Route and phases

`POST /api/v1/pages/import/notion?project=<name>`, in a new module
`api/routes/page_import.py` registered like §3.3's — raw body is the zip
(`application/zip`), streamed to `<attachments_dir>/.staging/<uuid>/upload.zip`
with the §3.3 counter against `notion_import_max_bytes` (config, default
1 GB). Behind `refuse_when_read_only`. The SPA passes the project whose `kind`
is `personal`; the route accepts any existing project.

Three phases:

1. **Upload** to staging, as above.
2. **Plan** — one `asyncio.to_thread` call, no database access, no lock. Reads
   the zip, runs every check in §4.2, extracts each referenced attachment into
   the staging directory (hashing and sniffing as it goes), builds every page's
   block tree (§4.4), and returns an `ImportPlan`: the page hierarchy with
   pre-assigned UUIDs, titles, trees and properties, plus the staged
   attachments. Refuses 422 before any write when the export has more than
   `notion_import_max_pages` pages (default 10 000).
3. **Write** — one transaction under `root_lock_key(project)`. Inserts the
   attachment rows, the root page, then every page through the insert helper
   (§4.6), moves each staged attachment to its final path with `os.replace`
   (same filesystem), and commits.

`notion_import_max_seconds` (default 900) bounds phases 2 and 3 together,
checked between pages; exceeding it aborts as a failure.

**Stated costs.** Phase 3 holds the project's sibling-set lock, so editor
writes that create or move pages in the personal project wait for it. Block
edits inside an existing page take only that page's lock and are not blocked.
A client that disconnects during phase 3 does not cancel the import: it
commits, and a retry creates a second root.

**Failure paths.** On any exception in any phase, the transaction rolls back,
files already moved to final paths are unlinked, and the staging directory is
removed; all filesystem work runs in a thread. The staging directory is removed
on success too. A crash leaves at most row-less files, a stale staging
directory and stale `.part` files, all of which §3.6 collects.

Only the **Markdown & CSV** export is accepted. An archive with `.html` pages
and no `.md` is refused 422: "re-export from Notion as Markdown & CSV". An
outer zip whose entries are `*Part-N.zip` is one export: each inner zip is
first **extracted to staging** (counted against the caps), never read through
the outer archive, because `zipfile` seeks backwards per entry and a nested
compressed stream re-decompresses from the start on every backward seek. Parts
are then read in part order as one logical tree.

### 4.2 Hostile-zip defences

- Entry names are never joined into filesystem paths; entries are read by name
  through `zipfile`. Names are normalised to `/`-separated; an absolute path, a
  `..` component or a drive letter skips the entry (`skipped_entry`).
- Names without the UTF-8 flag are re-decoded: the cp437 string `zipfile`
  produced is re-encoded to cp437 and decoded as UTF-8, falling back to the
  cp437 string. Duplicate names: the first entry wins, the rest are skipped.
- Symlink entries (Unix mode bits) and encrypted entries are skipped.
- Caps: `notion_import_max_entries` (default 50 000) and
  `notion_import_max_uncompressed_bytes` (default 5 GB). The central
  directory's sizes give a cheap early refusal, but it can lie, so the real
  enforcement is a running counter over chunked `open()` reads. `read()` of a
  whole entry is never called.
- Nested zips are opened only for the top-level Part-N case, never
  recursively.

### 4.3 Building the tree

Facts about Notion's export, taken from its documented behaviour and
**unverified against a real export here**. The first implementation task
obtains or constructs a realistic sample and pins it as a fixture.

- A page is `Title <32-hex>.md`; with "Create folders for subpages" on, its
  subpages are in a sibling folder `Title <32-hex>/`. Notion truncates and
  sanitises long names, so the filename's title is unreliable.
- A database is `Name <32-hex>.csv`; newer exports also write
  `Name <32-hex>_all.csv`, which wins. Row pages sit in the database's folder.
  CSVs are UTF-8 with a BOM.
- Workspace exports wrap everything in id-less folders (`Private & Shared`,
  teamspace names).

The importer:

1. Indexes each entry by the 32-hex id at the end of its stem, where present.
2. **Title:** the file's leading `# ` line whenever present; otherwise the
   filename stem, URL-decoded, with the id stripped.
3. **Parents** from folder nesting. A chain of id-less top-level folders that
   each contain exactly one child is unwrapped. Other id-less folders with no
   `.md` become grouping pages named after the folder.
4. **Flat export:** if no id-bearing folder exists and there is more than one
   `.md`, every page imports as a direct child of the root and the report
   carries one `flat_export` warning.
5. **Order:** siblings alphabetically by title (the export carries no sidebar
   order). A database's row pages follow CSV row order, matched by title (the
   first CSV column), since the CSV carries no ids; unmatched row pages follow,
   alphabetically.
6. Every page gets a UUID before any tree is built, so links resolve in both
   directions. Each page stores `properties.notion_id` (the 32-hex id) for a
   future re-import to key on.
7. Everything goes under one new root page titled
   `Notion import — <YYYY-MM-DD HH:MM> UTC`, placed last among the project's
   root pages.

### 4.4 Translating content

Per page, inside the plan phase:

1. **Text pre-pass** on the markdown:
   - Remove the leading `# ` title line (§4.3 step 2).
   - Remove a leading frontmatter fence; inline link-reference definitions into
     their references (`stripped_source` warning), since a page cannot hold
     either.
   - Rewrite each `<aside>…</aside>` as a blockquote whose first line is
     `[!NOTE]`, every body line prefixed `> `. This has to be textual: a blank
     line ends a CommonMark HTML block, so a multi-paragraph aside would
     otherwise parse as html / paragraph / html.
   - Rewrite links (§4.4.1).
2. **Parse** with the existing page parser (`_parse`).
3. **Post-parse transforms.** The parser never mints page-only types (by
   design; `taxonomy.py` keeps them out of `BLOCK_TYPES`), so the importer
   converts:
   - a `quote` whose text starts `[!LABEL]\n` → `callout`, with `variant` from
     the inverse of `block_serializer._CALLOUT_LABELS` (`NOTE`→`info`,
     `WARNING`→`warning`, `CAUTION`→`error`, `TIP`→`success`; an unknown label
     → `info`) and the label line removed. Callouts hold no children, so a
     callout's child blocks become its following siblings, in order.
     Paragraph breaks inside a callout collapse to line breaks (the parser
     joins them); accepted.
   - a `list` item whose text starts `[ ] ` or `[x] ` → `todo` with `checked`,
     marker removed, list properties dropped. Its children are kept (`todo` may
     hold children).
4. `_flatten_headings`, then the page-parent rule of `block_verbs.py`
   (children only under `list`, `todo`, `toggle`; `table_row` under `table`)
   asserted on the result. A violation is a bug, not a user refusal.
5. **Bounds** (§4.5).

The import does **not** run `reproduces_source`. That check guards a *user's*
content against silent loss at create time. The import deliberately changes the
source, it reports every change, and the check's html-block count would fail
the moment an aside became a callout.

#### 4.4.1 Links

- A relative link whose URL-decoded target, resolved against the file's folder,
  is a `.md` or `.csv` in the export → `/notes?page=<uuid>`.
- A `https://www.notion.so/…-<32hex>` link whose id is in the export →
  `/notes?page=<uuid>`. One whose id is not in the export stays external.
- A relative link or image resolving to any other file in the export → that
  file's attachment URL (§3.5).
- An internal target missing from the zip, or an attachment over
  `attachment_max_bytes`: an image or file becomes the text
  `[missing file: <name>]` (`missing_file` / `oversize_attachment`); a page link
  keeps its text and loses its target (`unresolved_link`).
- Other external links are unchanged.

#### 4.4.2 Databases

- A database page's body is its CSV as a markdown table: header row = CSV
  header; each cell with `|` escaped and newlines replaced by spaces.
- A row page keeps its leading `Key: value` property lines, turned into a
  bullet list at the top.

### 4.5 Bounds

Both bounds are measured on what is stored: `MAX_BLOCKS` counts every block,
`table_row`s included, and `MAX_CONTENT_CHARS` is measured on the serialiser's
output. A page over either is truncated: serialise, drop trailing blocks (for a
table, its trailing rows) until both fit, re-serialise, and record `truncated`
with the number of blocks dropped. Truncation never fails the import.

### 4.6 Writing and the journal

Split `create_page` (`page_door.py`) into:

```python
async def _insert_page(
    session, *, project: str, parent_id: str | None, after_id: str | None,
    title: str | None, tree: list[TreeBlock], properties: dict | None,
    actor: str | None, page_id: UUID | None = None,
) -> PageResult: ...
```

It claims the order index (`_claim_order_index`, whose advisory lock is
transaction-scoped and re-entrant, so repeated calls are fine), serialises,
inserts the page and its blocks, and journals `page_created`. It **never
commits**. Block rows are inserted with one multi-row statement per page (an
`unnest` over arrays) rather than one `INSERT` per block. `create_page` becomes
parse + representability refusal + `_insert_page` + commit, with unchanged
behaviour.

The import module journals one `pages_imported` event on the root page — a new
`EVENT_TYPES` value, landed taxonomy-first, with the event type passed as a
literal (`test_events.py` allowlists only `page_door.py`'s forwarding shape).
It is **non-strict**: the import is re-runnable, so a lost row costs an audit
line, not a denominator. The payload is counts only; titles and paths (which
the report's warnings carry) stay off it.

### 4.7 Report

```
{ root_page_id, pages_created, databases, attachments_stored,
  attachment_bytes, warnings: [{path, kind, detail}], warnings_omitted }
```

`pages_created` excludes the root page. `kind` is one of `missing_file`,
`unresolved_link`, `truncated`, `skipped_entry`, `oversize_attachment`,
`stripped_source`, `flat_export`. `warnings` is capped at 500 entries;
`warnings_omitted` counts the rest.

### 4.8 Known limits

- Notion's markdown export writes toggles as bullet lists, so toggles import as
  lists.
- Synced blocks, embeds and equations import as whatever text Notion wrote.
- Database views, relations and rollups are not reproduced; relation cells
  keep the text Notion wrote.
- Paragraph breaks inside a callout become line breaks.

## 5. Notes UI

### 5.1 Import dialog

"Import from Notion" in the page tree header menu opens a `darkraise-ui`
`dialog` using its `file-upload` and `progress` components:

- Instructions: Notion → Settings → Export → **Markdown & CSV**, with
  "Include subpages", "Create folders for subpages" and files included.
- Upload through `XMLHttpRequest` for progress events, then an indeterminate
  state while the server imports.
- On success: the counts, a collapsible warning list, and "Go to imported
  pages", which selects `root_page_id`. The `["pages", project]` query is
  invalidated.
- On error: the refusal message (413, 422) in the dialog.
- Hidden under `DEMO`, which must make no API calls.

### 5.2 Editor: images and files

`image` and `file` blocks are added to `pageSchema` (`editor-schema.tsx`),
with a fixed mapping in `lib/block-mapping.ts`:

- A paragraph whose **only** content is `![alt](<attachment url>)` ↔ BlockNote
  `image` block.
- A paragraph whose only content is `[name](<attachment url>)` ↔ BlockNote
  `file` block.
- Everything else (an image inside other text, a non-attachment image URL)
  stays a `rawInline` atom, which renders a thumbnail when its target is an
  attachment URL.

Both compared trees already pass through `canonicalTree`, and today an image
paragraph is one `rawInline` atom emitted verbatim, so an unedited image never
diffs as an edit. Server-side these stay paragraphs, so `sync-tree.ts` needs no
new refusal mirror. **Image resizing is disabled**: BlockNote's
`previewWidth` has no place in the markdown, so a resize would be silently lost
on reload.

### 5.3 Upload

BlockNote's `uploadFile` option (configured in `use-page-editor.ts`) sends the
raw-body `POST /pages/{id}/attachments` and returns the URL. Paste, drag-drop
and the block's upload button all route through it. An error shows a `sonner`
toast and inserts nothing.

## 6. Testing and guards

**Backend pytest.**
- Attachments: upload, the `Content-Length` and mid-stream 413s leaving no
  `.part`, 404 on a trashed page, magic-byte sniffing (a PNG-headed HTML file,
  an SVG → octet-stream), serving headers per type, filename header encoding.
- Cleanup job: all three arms; an attachment referenced only from a trashed
  page survives; one referenced from another page after a paste survives.
- `_insert_page` extraction leaves `create_page`'s existing tests green.
- Import against fixture zips: nested pages; a database with `_all.csv` and
  row pages; a Part-N outer zip; links both directions, including `notion.so`
  URLs; callouts (multi-paragraph, nested list) and to-dos (nested); an
  attachment shared by two pages stored once; a missing file; zip slip; a
  symlink; an encrypted entry; a cp437 name; entry-count and uncompressed caps,
  including a lying central directory; an HTML export refused; a flat export;
  id-less wrapper folders; truncation; the page-count cap; and a failure
  injected in phase 3 leaving no rows, no final files and no staging directory.
- Backups: `backup.sh` writes a tarball after the dump, skips when the manifest
  is unchanged, and prunes the two families separately; `backup_ship` keeps
  dumps under the tarball family's pressure; the receiver accepts the new name.

**Guards leg** (the CLAUDE.md list), plus the specific edits it will demand:
- `content_surfaces.py` classifies both new routes.
- `test_rest_conformance.py` `_EXPECTED`: upload 201, import 201, GET's 404 in
  the error envelope.
- The `test_door_parity.py` table gets `pages.attachments` and `pages.import`
  single-door rows, regenerating the doc block.
- `frontend/src/features/activity/event-taxonomy.ts` maps `pages_imported`.
- `test_block_retrieval.py` `BLOCK_CHANNEL_MODULES` includes the import module
  and the cleanup job (both read `blocks`).
- `test_deployment_artifact.py` asserts the attachment volume on the prod and
  worker compose files.
- The `test_code_deriver.py` roster tuple.

**vitest:** image/file mapping round trip and canonicalisation; import dialog
states; the upload hook's error path.

**Playwright** through `backend/scripts/e2e/run_playwright_e2e.py`, whose
disposable stack gets a writable attachments directory: import a fixture, see
the tree and a rendered image.

## 7. Documentation

- `CLAUDE.md`: job roster (25, `page_attachment_cleanup`), page route count
  (13 → 16), the attachments volume and its backups, the Notes paragraph, and
  `refuse_when_read_only`'s scope.
- `docs/two-door-parity.md`: regenerated block plus the headline counts
  sentence, which sits outside it.
- `docs/runbook-deployment.md` and `docs/runbook-backup-worker.md`: the volume,
  the tarball family, the pairing rule and restore order.
- The `pages.py` module docstring route list, and new ones in
  `page_attachments.py` and `page_import.py`.
- `CHANGELOG.md` entry for the release carrying increment 3.

# Notion import route and dialog — design

Date: 2026-09-20. Sub-project 4 of the Notion import programme
(`2026-09-19-notion-import-design.md`), covering its §4 and §5.1. The three
earlier increments — attachment storage, attachment backups, editor images and
files — are merged.

**This spec supersedes §2's flat-export ruling and §4.3's export facts.** Both
were written as unverified assumptions; a real export has since been read and
six of them are wrong. §3 (attachment storage) and §5.2-5.3 (editor rendering
and upload) are shipped and unchanged.

## 1. Goal

Import a Notion "Markdown & CSV" workspace export into the personal project's
page tree over one REST route, keeping hierarchy, text, databases, links between
pages, and images and files. One dialog in the `/notes` page-tree header drives
it.

Out of scope, unchanged from the programme: Notion's HTML export, the Notion
API, database views, re-import or merge into an earlier import, MCP access.

## 2. Rulings

| Question | Ruling |
|---|---|
| Response shape | Synchronous 201 carrying the report, plus 409 while an import is running |
| Concurrency | One import at a time, refused before the body is read |
| Hierarchy on a flat export | **Derived from the export, not discarded** (supersedes the programme's §2 ruling) |
| Upload transport | XHR behind a shared `apiUpload` helper in `lib/api.ts` |
| Ceilings | Six `Settings` fields, not a `config` row |
| Export facts | Verified against a real export before anything was built on them |

## 3. Verified export facts

Read from a real 34.5 MB workspace export: 2260 entries, 37.5 MB uncompressed,
2193 markdown pages, 6 CSVs, 61 assets. Every rule below is measured, not
documented behaviour. The archive stays untracked at `/root/notion-export/`;
the fixtures this spec's plan commits are derived from it.

**Confirmed as the programme assumed:**

- A page is `Title <32-hex>.md`. All 2193 conform.
- Every page opens with a `# ` title line. All 2193 do.
- Assets carry no id (`image.png`, `NY_Large.gpx`, `peer_SPCE_Laptop.conf`) and
  are referenced by relative link. All 61 are referenced, each exactly once.
- A nested `.zip` entry is an attachment, not a Part-N archive. Two of them here.

**Wrong, and what is true instead:**

- **The export is flat.** All 2260 entries sit at depth 0 inside one id-less
  wrapper folder, `Export-<dashed-uuid>/`. "Create folders for subpages" was
  off. §4.3 step 3 unwraps a chain of id-less folders that each hold *exactly
  one* child; this wrapper holds 2260, so that rule does not fire.
- **A flat export is not flat.** 2171 of 2193 pages are parentable from two
  signals in the export itself (§7), leaving 22 roots that read as genuine
  top-level pages. Importing flat would place 2193 pages at the notes root.
- **A database is a page, not a CSV.** `Windows Keys <id>.md` holds `# Windows
  Keys`, a link to `Windows Keys <id>_all.csv`, and trailing `filters:` /
  `sort:` lines. It is a view stub. Four of the six CSVs have a stub whose stem
  matches; the other two are stubbed by a page under a different name —
  `Untitled 1507-2c1e_all.csv` by a page titled "Sprint 47" — which is why stub
  detection needs the link arm in §7.2 and not the stem alone.
- **Only `_all.csv` exists.** No bare `Name <32-hex>.csv` appears. And one CSV
  is `Untitled 1507-2c1e_all.csv` — its id is not 32-hex, so database detection
  cannot key on the id.
- **Row pages cannot be matched by title.** 766 pages are titled `Windows 10
  Pro`, and the CSV itself holds byte-identical duplicate rows. Matching on the
  page's *property block* instead pairs 1882 of 1887 row pages to the right
  database, with none ambiguous.
- **A regex cannot scan the links.** Nine link targets contain `(` — for
  example `1 Image (no compress) + caption <id>.md` — and `\(([^)]+)\)` stops at
  the first `)`. CommonMark allows balanced parentheses in a destination, so the
  scanner must too (§8.2).

**Absent from this corpus**, so the programme's rules for them ship untested
against real data and are recorded as such in §12: `<aside>` blocks (0
occurrences) and `https://www.notion.so/…` links (0).

**Other measurements that set a bound or a test:**

- 289 page-to-page links, every one occupying its whole line. Zero inline. That
  is what makes the standalone-link signal trustworthy.
- 7 links point at CSVs Notion did not export — database views and linked
  databases. They take `unresolved_link`.
- The largest database is 1847 rows, which serialises to 1848 blocks and about
  220 KB on one page: inside `MAX_BLOCKS` (5000) and `MAX_CONTENT_CHARS` (1M),
  so the real corpus needs no truncation.
- 16 pages carry to-do items, 31 carry images.

## 4. Module layout

Four service modules, because §4 of the programme is four separable jobs, and
one route module.

| Module | Job |
|---|---|
| `services/notion_archive.py` | §6. Safe entry enumeration, cp437 re-decode, symlink and encrypted skips, the running uncompressed counter, wrapper-prefix stripping, Part-N flattening. Knows nothing about pages. |
| `services/notion_tree.py` | §7. Entry indexing, titles, the three parent signals and their precedence, the cycle guard, sibling order, UUID pre-assignment. |
| `services/notion_content.py` | §8. Text pre-pass, the link scanner and rewriter, parse, callout and to-do post-transforms, CSV-to-table, §9 truncation. |
| `services/page_import.py` | §5 phases, §10 write, §11 report. The only one that touches the database. |
| `api/routes/page_import.py` | The route. |

Plus the `_insert_page` extraction in `page_door.py` (§10).

## 5. The route and its phases

`POST /api/v1/pages/import/notion?project=<name>`, raw body is the zip.
Registered with its own `include_router` in `main.py` before the SPA mount.
Behind `require_auth` and `refuse_when_read_only`. Two segments under `/pages`,
so it cannot collide with `/{page_id}`; `import`/`notion` matches no existing
two-segment page route.

### 5.1 The edge body cap must be widened

`RequestBodyLimitMiddleware` (`main.py:766`) refuses any request declaring more
than 25 MB and exempts exactly one path, through `is_attachment_upload_path`
(`main.py:724`). A 1 GB import body would be refused at the edge and the route
would never run.

One predicate, `bounds_own_body(path)`, returns true for either path, with
`is_attachment_upload_path` and a new `is_page_import_path` beneath it. Not a
second copy: that module's own comment says two copies is how the surfaces
drift apart.

Recorded limit, not fixed: `frontend/nginx.conf:37` carries the same
`client_max_body_size 25m` and would refuse an import. The nginx-in-image
fallback is not taken, so nothing is live behind it.

### 5.2 Single-flight

A module-level `asyncio.Lock` in `page_import.py`, taken **before the body is
read**, so a second import is refused 409 without transferring its bytes.

```python
if _import_lock.locked():
    raise HTTPException(409, "an import is already running")
async with _import_lock:
    ...
```

Checking then acquiring is check-then-act in general and safe here in
particular: no `await` sits between the two statements, and invariant 13 gives
one worker and one event loop. The comment says exactly that, because the shape
is one a reviewer should challenge.

The lock is held for the whole request, upload included. Two operators
therefore cannot upload concurrently, which is what "one import at a time"
means and is the intended reading for a single-operator homelab.

### 5.3 Phases

1. **Upload** to `<attachments_dir>/.staging/<uuid>/upload.zip`, streamed with
   the same running counter the attachment upload uses, against
   `notion_import_max_bytes`. The project is checked **before** any byte is
   read, so a 1 GB body is never accepted for an unknown name.
2. **Plan** — one call into a dedicated single-thread executor. No database
   access, no lock beyond the one already held. Reads the zip, runs every check
   in §6, extracts each referenced attachment into the staging directory
   (hashing and sniffing as it goes, assigning each a UUID), builds the tree
   (§7) and every page's block tree (§8), and returns an `ImportPlan`.
3. **Write** — one transaction under `root_lock_key(project)`. Places the
   staged attachment files, inserts their rows, inserts the root page, then
   every page through `_insert_page` (§10), journals `pages_imported`, commits.

The executor is created per call and shut down in a `finally`, mirroring
`utils/leiden.py:49`. It exists for the reason the programme gives — not
competing with bcrypt MCP auth, git subprocesses and code parsing on the
default executor — and **not** to serialise: §5.2's lock does that. The
programme inferred serialisation from the executor, which would have bounded
phase 2 only.

`notion_import_max_seconds` (900) bounds phases 2 and 3 together, checked
between pages.

### 5.4 Write order

**Files are placed, then rows are inserted, then the transaction commits.**

The programme's §4.1 has rows first. Its own §3.7 states the rule that decides
this: a file without a row is harmless and swept by the cleanup job's second
arm, while a row without a file is permanent. Rows-first leaves the permanent
failure on a crash between the two steps. This order also matches
`store_upload`, which writes the file, inserts, then commits.

`page_attachments.py` gains two helpers so that no caller-chosen string ever
reaches a path from outside that module:

- `place_staged(staged: Path, attachment_id: UUID) -> None` — shard `mkdir`
  then `os.replace` onto the final path.
- `insert_attachment_row(session, *, attachment_id, project, page_id, filename,
  content_type, size_bytes, sha256) -> None` — the existing `_INSERT`, without
  the commit.

`store_upload` is unchanged and keeps its own commit; the import cannot use it
for that reason.

### 5.5 Free space

`shutil.disk_usage` on the attachments filesystem, twice:

- Before the upload, against the declared `Content-Length` × 3 where one is
  declared.
- After the upload, against the real size × 3, before phase 2.

The 3× derivation, which the programme asserted without stating: staging holds
the zip (1×), the extracted inner parts of a Part-N export (≤1×), and each
referenced attachment extracted once (≤1× in aggregate, since attachments are
the incompressible bulk). Text expands further but is never staged as a file —
it is read into the plan in memory, bounded separately by
`notion_import_max_uncompressed_bytes`.

A shortfall answers 507. Checking before the upload matters because a disk
filled by an import also breaks attachment serving.

### 5.6 Status codes

| Code | Cause |
|---|---|
| 201 | The report (§11) |
| 403 | Read-only instance |
| 409 | An import is already running |
| 413 | Over `notion_import_max_bytes` |
| 422 | Unknown project; an HTML export; no `.md` entry; over the page or block cap |
| 507 | Insufficient free space |

### 5.7 Failure paths

On any exception in any phase the transaction rolls back, files already placed
at final paths are unlinked, and the staging directory is removed; all
filesystem work runs in a thread. Staging is removed on success too. A crash
leaves at most row-less files, a stale staging directory and stale `.part`
files, all of which `page_attachment_cleanup` already collects.

A client that disconnects during phase 3 does not cancel the import: it
commits, and a retry creates a second root. Stated in the dialog, not fixed.

### 5.8 Settings

Six fields on `Settings`, beside `attachment_max_bytes`. Operator ceilings, not
per-job knobs, and no job exists here for a `config_schema` to hang on.

| Field | Default | The real export |
|---|---|---|
| `notion_import_max_bytes` | 1 GB | 34.5 MB |
| `notion_import_max_entries` | 50 000 | 2 260 |
| `notion_import_max_uncompressed_bytes` | 5 GB | 37.5 MB |
| `notion_import_max_pages` | 10 000 | 2 193 |
| `notion_import_max_blocks` | 250 000 | ~12 000 |
| `notion_import_max_seconds` | 900 | — |

## 6. Archive reading

Unchanged from the programme's §4.2 except where noted.

- Entry names are never joined into filesystem paths; entries are read by name
  through `zipfile`. Names are normalised to `/`-separated; an absolute path, a
  `..` component or a drive letter skips the entry (`skipped_entry`).
- Names without the UTF-8 flag are re-decoded: the cp437 string `zipfile`
  produced is re-encoded to cp437 and decoded as UTF-8, falling back to the
  cp437 string. Duplicate names: the first entry wins.
- Symlink entries (Unix mode bits) and encrypted entries are skipped.
- The central directory's sizes give a cheap early refusal, but it can lie, so
  the real enforcement is a running counter over chunked `open()` reads.
  `read()` of a whole entry is never called.
- Nested zips are opened only for the top-level Part-N case, never recursively.
  A `.zip` entry that is not a Part-N part is an attachment — the real export
  holds two.
- **Wrapper stripping replaces the programme's single-child rule.** Compute the
  longest directory prefix that every entry shares and that carries no 32-hex
  id, and strip it. The real export's `Export-<dashed-uuid>/` is stripped by
  this and not by the single-child rule, which does not fire at 2260 children.

An archive with `.html` pages and no `.md` is refused 422: "re-export from
Notion as Markdown & CSV".

## 7. Building the tree

### 7.1 Entry identity

The id is the trailing ` <32-hex>` on the entry's stem, after stripping a
trailing `_all` from a CSV. An entry with no such suffix has no id — every
asset, and `Untitled 1507-2c1e_all.csv`. **Database detection therefore keys on
the `_all.csv` suffix and on a stub page linking to it, never on the id.**

Title: the file's leading `# ` line whenever present, otherwise the filename
stem URL-decoded with the id stripped. All 2193 pages in the real export have
the `# ` line, so the fallback is the untested path.

Every page is assigned a UUID before any tree is built, so links resolve in
both directions. Each page stores `properties.notion_id` where it has one.

### 7.2 Databases

A CSV whose name ends `_all.csv` is a database. Its **page** is found in two
steps, because the stem alone is not enough:

1. The `.md` whose stem matches the CSV's stem with `_all` removed. Four of the
   six databases in the real export resolve here.
2. Failing that, the one page that links to the CSV on a line of its own. The
   other two resolve here, and one of them is the export's own
   `Untitled 1507-2c1e_all.csv`, whose stub page is titled "Sprint 47" — the
   stem rule alone would have minted a grouping page beside a real one.

Where neither resolves, the importer mints a grouping page named after the CSV.
On the real export that never happens; the fixtures cover it.

### 7.3 Parent signals, in precedence

The first signal that yields a parent wins.

1. **Folder nesting.** Where the export carries id-bearing folders
   (`Title <32-hex>/`), a page's parent is the page whose id matches its
   containing folder's. Unchanged from the programme; not exercised by the real
   export, which has no such folders.
2. **Database membership.** A page's *property block* is the run of contiguous
   `Key: value` lines immediately after its title line. Where that key set is
   non-empty and is a subset of exactly one database's CSV columns excluding
   the first, the page becomes a child of that database's page. Measured: 1882
   of 1887 row pages paired, none ambiguous, 48 ordinary pages with a
   property-shaped opening correctly left unpaired.
3. **Standalone link.** A page that is the target of exactly one link occupying
   its whole line, counted across the whole export, becomes that linker's
   child. Two or more inbound standalone links leave it unparented — ambiguous
   parentage is not guessed. Measured: 289 such links, every page-to-page link
   in the export on its own line, zero inline.
4. Otherwise a root of the import.

Measured coverage on the real export, by the rules exactly as stated above:
2171 of 2193 pages parented — 1882 by database membership, 289 by a standalone
link — leaving 22 roots, and no warning of any kind. No target carries two
inbound standalone links, so nothing was left unplaced for ambiguity, and no
cycle arose. All six databases resolve a stub page, so no grouping page is
minted: the import writes 2193 pages under its root, 22 of them directly
beneath it.

The report carries one `derived_hierarchy` warning with the counts per signal,
so the operator can see what was inferred rather than read.

### 7.4 Cycle guard

Signals 2 and 3 do not guarantee a forest: two pages may link to each other on
their own lines. Edges are added in a deterministic order (by entry name), and
an edge that would close a cycle is dropped with a `hierarchy_cycle` warning
naming both pages. The `pages` table's parent FK requires this; without it the
insert order in §10 has no valid topological sort.

### 7.5 Order

- Siblings alphabetically by title, except a database's row-page children,
  which take CSV row order where the property block pairs a unique row, with
  the rest alphabetically after them.
- Roots alphabetically.
- Everything goes under one new root page titled
  `Notion import — <YYYY-MM-DD HH:MM> UTC`, placed last among the project's
  root pages.

The export carries no sidebar order, so alphabetical is a choice, not a
recovery.

## 8. Translating content

Per page, inside the plan phase.

### 8.1 Text pre-pass

- Remove the leading `# ` title line.
- Remove a leading frontmatter fence; inline link-reference definitions into
  their references (`stripped_source`), since a page can hold neither.
- On a **database page**, drop the CSV link and the trailing `filters:` /
  `sort:` lines (`stripped_source`) and emit the CSV table in their place
  (§8.4).
- On a **row page**, the property block becomes a bullet list at the top. It is
  read as the pairing signal in §7.3 before it is rewritten here.
- Rewrite each `<aside>…</aside>` as a blockquote whose first line is
  `[!NOTE]`, every body line prefixed `> `. Textual by necessity: a blank line
  ends a CommonMark HTML block, so a multi-paragraph aside would otherwise
  parse as html / paragraph / html. **Untested against real data** — this
  export holds none.
- Rewrite links (§8.2, §8.3).

### 8.2 The link scanner

Link rewriting runs on the text, so it needs its own destination scanner. A
regex does not work: nine targets in the real export contain `(`.

The scanner finds `](`, then reads the destination with balanced parentheses,
honouring backslash escapes and stopping at whitespace, and also accepts the
`<…>` destination form. `![…](…)` images use the same scanner. Anything inside a
fenced code block or an inline code span is skipped — zero occurrences in this
export, but the rule is cheap and a code sample holding a link is ordinary.

Measured: the scanner resolves 289 page links and 61 assets where the regex
resolved 280 and 61, leaving exactly 7 genuinely unresolvable targets.

### 8.3 Rewriting

- A relative target, URL-decoded and resolved against the entry's folder, that
  is a `.md` in the export → `/notes?page=<uuid>`.
- A relative target that is a **database `_all.csv`** → that database's page,
  `/notes?page=<uuid>`. Not an attachment: the six such links in the real
  export are database references, and serving them as file downloads would be
  wrong.
- A relative target that is any other file in the export → that file's
  attachment URL, `/api/v1/pages/attachments/<id>`.
- A `https://www.notion.so/…-<32hex>` link whose id is in the export →
  `/notes?page=<uuid>`; one whose id is not stays external. **Untested against
  real data** — this export holds none.
- An internal target missing from the zip, or an attachment over
  `attachment_max_bytes`: an image or file becomes the text
  `[missing file: <name>]` (`missing_file` / `oversize_attachment`); a page or
  database link keeps its text and loses its target (`unresolved_link`). Seven
  of these in the real export, all database views Notion did not write.
- Other external links are unchanged.

### 8.4 Databases as tables

A database page's body is its CSV as a markdown table: header row from the CSV
header, each cell with `|` escaped and newlines replaced by spaces. The CSV is
UTF-8 with a BOM; `utf-8-sig` reads it.

The largest real database is 1847 rows, which serialises to 1848 blocks and
about 220 KB — inside both per-page bounds, so §9 does not fire on it.

### 8.5 Parse and post-parse transforms

Parse with the page parser (`page_door._parse`). The parser never mints
page-only types by design (`taxonomy.PAGE_BLOCK_TYPES` is kept out of
`BLOCK_TYPES`), so the importer converts:

- A `quote` whose text is `[!LABEL]`, alone or followed by `\n` → `callout`,
  with `variant` from the inverse of `block_serializer._CALLOUT_LABELS`
  (`NOTE`→`info`, `WARNING`→`warning`, `CAUTION`→`error`, `TIP`→`success`; an
  unknown label → `info`), the label line removed. Callouts hold no children on
  a page, so a callout's child blocks become its following siblings, in order.
  Paragraph breaks inside a callout collapse to line breaks; accepted.
- A `list` item whose text starts `[ ] ` or `[x] ` → `todo` with `checked`, the
  marker removed and list properties dropped. Its children are kept, since a
  `todo` may hold children. 16 pages in the real export exercise this.

Then `page_door._flatten_headings`, then the page-parent rule from
`block_verbs._check_page_nesting` (children only under `list`, `todo`,
`toggle`; `table_row` under `table`) asserted on the result. A violation is a
bug, not a user refusal.

The import does **not** run `reproduces_source`. That check guards a user's
content against silent loss at create time; the import deliberately changes the
source, reports every change, and the check's html-block count would fail the
moment an aside became a callout.

## 9. Bounds

Both bounds are measured on what is stored: `MAX_BLOCKS` counts every block,
`table_row`s included, and `MAX_CONTENT_CHARS` is measured on the serialiser's
output. A page over either is truncated: serialise, drop trailing blocks (for a
table, its trailing rows) until both fit, re-serialise, and record `truncated`
with the number of blocks dropped. Truncation never fails the import.

## 10. Writing and the journal

`create_page` splits, per the programme's §4.6:

```python
async def _insert_page(
    session, *, project: str, parent_id: str | None, after_id: str | None,
    title: str | None, tree: list[TreeBlock], properties: dict | None,
    actor: str | None, page_id: UUID | None = None,
) -> PageResult: ...
```

It claims the order index (`_claim_order_index`, whose advisory lock is
transaction-scoped and re-entrant), serialises, inserts the page and its blocks,
and journals `page_created`. It **never commits**, and the `MAX_BLOCKS` refusal
moves into it so both callers keep it — the import truncates first (§9), so it
never fires there.

Block rows are inserted with one multi-row statement per page (an `unnest` over
arrays, the `block_verbs._PLACE` CAST idiom) rather than one `INSERT` per block.
The per-page parent lock and next-index queries stay: at the 10 000-page cap
they cost a few round trips per page, which fits the time budget, and removing
them would need a second code path.

`create_page` becomes parse, the representability refusal, `_insert_page`, and
commit — behaviour unchanged. Its `MAX_CONTENT_CHARS` check and
`reproduces_source` refusal stay in `create_page`; the import runs neither.

**Cost stated:** an import of N pages writes N+1 `page_created` rows plus one
`pages_imported`. `events` is append-only and month-partitioned, so this is a
volume note, not a hazard. A real export writes about 2200 rows.

`pages_imported` is a new `EVENT_TYPES` value, landed taxonomy-first, written on
the root page with the event type as a literal (`test_events.py` allowlists only
`page_door.py`'s forwarding shape). It is **non-strict**: the import is
re-runnable, so a lost row costs an audit line, not a denominator. The payload
is counts only; titles and paths stay on the report.

## 11. Report

```
{ root_page_id, pages_created, databases, attachments_stored,
  attachment_bytes, warnings: [{path, kind, detail}], warnings_omitted }
```

`pages_created` excludes the root page. `kind` is one of `missing_file`,
`unresolved_link`, `truncated`, `skipped_entry`, `oversize_attachment`,
`stripped_source`, `derived_hierarchy`, `hierarchy_cycle`. `warnings` is capped
at 500 entries; `warnings_omitted` counts the rest.

`path` is the export entry the warning is about, and is **null** for the
export-scoped kinds — `derived_hierarchy` names no one entry, and
`hierarchy_cycle` names two, both in `detail`.

## 12. Known limits

- **The plan is held in memory.** 250 000 `TreeBlock`s at the cap is roughly
  125 MB of Python objects inside a 1 GB container. `notion_import_max_blocks`
  is the dial. Streaming pages into phase 3 would halve it and was rejected: it
  puts blocking zip reads inside the write transaction, holding the project's
  sibling lock for the whole parse.
- **Two rules ship untested against real data**, because this corpus holds no
  instance: the `<aside>` → callout transform (§8.1) and the `notion.so` link
  rule (§8.3). Both are implemented to Notion's documented behaviour and
  covered by constructed fixtures only.
- **Hierarchy is inferred, not read**, on a flat export. A page with two
  inbound standalone links is left at the root rather than guessed; a page whose
  property block coincidentally matches a database's columns is mis-parented.
  The `derived_hierarchy` warning carries the counts so the operator can judge.
- Notion's markdown export writes toggles as bullet lists, so toggles import as
  lists.
- Synced blocks, embeds and equations import as whatever text Notion wrote.
- Database views, relations and rollups are not reproduced; relation cells keep
  the text Notion wrote, and a link to an unexported view CSV becomes
  `unresolved_link`.
- Paragraph breaks inside a callout become line breaks.
- A client disconnect during phase 3 still commits; a retry creates a second
  root.
- `frontend/nginx.conf:37`'s 25 MB cap would refuse an import if the
  nginx-in-image fallback were ever taken.

## 13. Notes UI

### 13.1 `apiUpload`

`lib/api.ts` gains one sibling to `apiFetch`:

```ts
apiUpload<T>(path, body: Blob, opts: {
  headers?: Record<string, string>
  onProgress?: (fraction: number) => void
  signal?: AbortSignal
}): Promise<T>
```

XHR, because `fetch` cannot report upload progress. It reuses the same
`/api/v1` base, `withCredentials: true`, the 401 → `handleUnauthorized`
redirect and `ApiError` extraction from the `{detail}` envelope. This is the
SPA's first XHR; putting it in `lib/api.ts` is what keeps the request plumbing
from being hand-written a second time in a feature component. `uploadAttachment`
may adopt it later for progress it does not have today.

### 13.2 The dialog

`features/notes/notion-import-dialog.tsx`, using `darkraise-ui` `dialog`,
`file-upload` and `progress` (all three ship in v6.6.0; `file-upload` is
selection and validation only, so the transport is ours).

Four states:

| State | Surface |
|---|---|
| Idle | Instructions — Notion → Settings → Export → **Markdown & CSV**, with "Include subpages" and files included — and the picker, `accept=".zip"`, `maxFiles: 1`, `maxFileSize` from the cap |
| Uploading | `Progress value={percent}`, driven by `onProgress` |
| Importing | `Progress value={null}` (indeterminate), with a line saying that closing the dialog does not cancel a committed import |
| Done / failed | The counts, a collapsible warning list and "Go to imported pages"; or the refusal message for 409, 413, 422 and 507 |

`closeOnOutsidePointerDown={false}` and `closeOnEscape={false}` while a request
is in flight. Refusals render in the dialog rather than as a toast — a
deliberate departure from the feature's `refuse` idiom, since the dialog is
still open and is where the operator is looking.

"Create folders for subpages" is **not** in the instructions: the import derives
hierarchy either way (§7), and telling the operator to re-export would be advice
this design made unnecessary.

### 13.3 Entry point

A `MoreHorizontal` `DropdownMenu` beside "New page" in
`notes-workspace.tsx:167-177`. There is no header menu today; the per-row
actions menu at `page-tree.tsx:112-128` is the SPA's only `DropdownMenu` and is
the idiom to match, including its `event.stopPropagation()` on trigger and
content. One item today.

`project` and the `["pages", project]` key are already in scope in
`NotesWorkspace`. On success: `invalidatePageLists(qc)`, then `onSelect(root_page_id)`.
No `query-keys.ts` entry is needed — this is a mutation, not a query.

### 13.4 DEMO and in-flight state

`NotesWorkspace` never mounts under `DEMO` (the route branches to `DemoNotes`),
so the surface is already unreachable; the menu item carries an explicit `DEMO`
guard anyway, matching the codebase's belt-and-braces posture, with a test.

The import's in-flight state deliberately does **not** join
`features/notes/lib/attachments.ts`'s module-wide upload counter. That counter
drives the editor's unload warning and its "Saving…" status, and an import is
not an editor save.

## 14. Testing and guards

**Backend pytest.** Against fixtures derived from the real export, plus
constructed ones for the cases it does not hold:

- Hierarchy: folder nesting; database membership pairing, including a page with
  a property-shaped opening that matches no database; standalone-link parenting;
  a page with two inbound standalone links left at the root; a two-page link
  cycle broken with a warning; signal precedence where two signals disagree.
- Databases: a CSV with a stub page and one without; the non-32-hex CSV id; the
  BOM; CSV row order for children; `|` and newlines in a cell.
- Links: balanced parentheses in a target; the `<…>` form; a link inside a
  fence; a database CSV link becoming a page link, not an attachment; a missing
  target; `notion.so` both in and out of the export.
- Content: callouts (multi-paragraph, nested list) and to-dos (nested); an
  attachment shared by two pages stored once; truncation.
- Archive: zip slip; a symlink; an encrypted entry; a cp437 name; a duplicate
  name; entry-count and uncompressed caps including a lying central directory;
  a Part-N outer zip; a `.zip` attachment not treated as a part; the wrapper
  prefix stripped.
- Route: an unknown project refused before the body is read; 409 on a
  concurrent import; the free-space refusal both before and after the upload;
  413; an HTML export refused; the page and block caps.
- Write: files placed before rows (an injected failure between them leaves no
  row and no final file); a phase-3 failure leaving no rows, no final files and
  no staging directory; `_insert_page`'s extraction leaving `create_page`'s
  existing tests green.
- Edge: the import path exempt from `RequestBodyLimitMiddleware`.

**Guards leg** (the CLAUDE.md list), plus the edits it will demand:

- `content_surfaces.py` classifies `POST /api/v1/pages/import/notion`.
- `test_rest_conformance.py` `_EXPECTED` gains it at 201.
- `test_door_parity.py` gains a `pages.import` single-door row, regenerating the
  doc block; `docs/two-door-parity.md`'s headline counts sentence sits outside
  that block and is edited by hand.
- `frontend/src/features/activity/event-taxonomy.ts` maps `pages_imported`.
- `test_block_retrieval.py` `BLOCK_CHANNEL_MODULES` includes `page_import.py`.

**vitest:** `apiUpload`'s progress callback, its 401 path and its `ApiError`
extraction, against a fake XHR; the dialog's four states; the menu item's `DEMO`
guard.

**Playwright** through `backend/scripts/e2e/run_playwright_e2e.py`: import a
small fixture, see the derived tree and a rendered image.

## 15. Documentation

- `CLAUDE.md`: the Pages paragraph's route inventory, which reads "thirteen
  routes under `/api/v1/pages` ... plus the two attachment routes" and gains
  the import route in its own module; and the `/notes` paragraph, which gains
  the import entry point.
- `docs/two-door-parity.md`: regenerated block plus the headline counts sentence.
- The `page_import.py` module docstring route list.
- `CHANGELOG.md` entry for the release carrying this increment.

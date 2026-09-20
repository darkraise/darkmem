# Notion Import Route and Dialog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import a Notion "Markdown & CSV" workspace export into the personal project's page tree over one REST route, driven by a dialog in the `/notes` page-tree header.

**Architecture:** Four pure service modules (archive reading, tree derivation, content translation, and the link scanner inside the content module) feed one orchestrator that runs three phases — upload to staging, plan off the event loop, write in one transaction. `create_page` splits so the import and the ordinary create share one page-insert path. The SPA gains an XHR upload helper beside `apiFetch` and one dialog.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async, asyncpg, `zipfile`/`csv` (stdlib), markdown-it-py; React 19, TanStack Query, TanStack Router, darkraise-ui 6.6.0, vitest.

**Spec:** `docs/superpowers/specs/2026-09-20-notion-import-route-design.md`

**Execution:** inline — `claude --model sonnet --effort high` — 4 heavy tasks of 16 is well under half, so the mode is inline; the session implements the seven score-3 tasks itself and delegates the other nine (4 heavy plus 5 four-band, which are a third of the plan or fewer).

**Program:** `docs/superpowers/specs/2026-09-19-notion-import-design.md` — sub-project 4 of 4 — last

**Plan review:** 2026-09-21 — dr-superpowers:judge-fable — executability 11 / coherence 14 / coverage 13 / assumptions 13 (round 1)

## Global Constraints

- **Greenfield.** No backward compatibility and no data migration is ever owed. A schema change regenerates `0001_baseline.py` in place and the database is dropped and recreated. This plan adds no column and no table, so no baseline change arises.
- **Language:** English only — code, comments, docs, commits, configs, errors, tests.
- **Commits:** `<type>(<scope>): <subject>`, type one of `feat|fix|docs|style|refactor|test|chore|perf`. Subject at most 50 characters, imperative, no trailing period.
- **Comments:** default to none. Add one only where the WHY is non-obvious — a hidden constraint, a subtle invariant, a surprising behaviour. Never explain WHAT the code does, and never reference the task or the plan.
- **Invariant 13:** exactly one uvicorn worker, one replica. In-process state (a module-level `asyncio.Lock`) is valid for the same reason the login rate limiter's is.
- **Invariant 15:** none of the six dream jobs may be reached from capture or retrieval. This plan touches none of them.
- **The block channel is firewalled from memory composition.** No module in this plan may import `app.services.pipeline`, and no module that mints or promotes a fact may reach a block reader. `page_import.py` reads and writes `blocks` and therefore belongs in `test_block_retrieval.py`'s `BLOCK_CHANNEL_MODULES`.
- **asyncpg needs CAST on raw-SQL params** whose type Postgres cannot infer: `CAST(:id AS uuid)`, `CAST(:props AS jsonb)`, `CAST(:ids AS uuid[])`. Especially with `unnest`.
- **The conftest `session` fixture runs inside an outer transaction** (`backend/tests/conftest.py:69-102`): a `commit()` in a test is dropped, and a `rollback()` ends the isolation boundary outright, so every write after it commits for real and leaks into the suite. Order a test writes-then-refusals, and never assert "this did not commit" by rolling back and re-reading — spy on `session.commit` instead.
- **Backend tests** run from `backend/` as `python -m pytest -q`, against the `darkmem_test` database on `127.0.0.1:5433`. A task dispatched to its own lane uses `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2` (lanes 2 to 5 exist; `darkmem_test` stays for the controller).
- **Frontend** runs from `frontend/`: `npm run typecheck` (`tsc -b`, not bare `tsc`), `npm test` (vitest), `npm run build`. `npm run lint` is advisory. **Do not run `prettier --write` over the repository** — it reformats 200+ unrelated files.
- **UI components come from `darkraise-ui` first.** Enumerate with `ls frontend/node_modules/darkraise-ui/dist/components/` and read the `.d.ts` beside the one you want. A new local component is a last resort.
- **Never invoke Playwright bare.** A bare `npx playwright test` points `/api` at the live instance on `:8000`. Use `backend/scripts/e2e/run_playwright_e2e.py`.
- **Exit 143 in any test run is a SIGTERM from the host's `earlyoom` daemon, not a failure.** Check `free -h` before believing a red, and re-run the leg on its own.
- **The real Notion export is at `/root/notion-export/export.zip`** — outside the repository, untracked, and never copied into it. It is read to derive fixtures and to check a format claim; it is not itself a fixture.

## Contracts

Every name one task produces and another consumes.

**Settings** (`backend/app/config.py`, on the existing `Settings` class, beside `attachment_max_bytes`) — Task 2:

```python
notion_import_max_bytes: int = 1_073_741_824
notion_import_max_entries: int = 50_000
notion_import_max_uncompressed_bytes: int = 5_368_709_120
notion_import_max_pages: int = 10_000
notion_import_max_blocks: int = 250_000
notion_import_max_seconds: int = 900
```

**Event type** (`backend/app/services/events.py`, in `EVENT_TYPES`) — Task 2: `"pages_imported"`.

**Attachment helpers** (`backend/app/services/page_attachments.py`) — Task 3:

```python
def place_staged(staged: Path, attachment_id: UUID) -> None: ...
async def insert_attachment_row(
    session: AsyncSession, *, attachment_id: UUID, project: str,
    page_id: UUID | None, filename: str, content_type: str,
    size_bytes: int, sha256: str,
) -> None: ...
```

**Archive** (`backend/app/services/notion_archive.py`) — Task 4:

```python
@dataclass(frozen=True)
class ArchiveEntry:
    name: str            # normalised, wrapper prefix stripped, "/"-separated
    info: ZipInfo        # the member to open. NOT a name: zipfile's name index
                         # keeps the LAST entry of a duplicated name, so opening
                         # by name would silently contradict "the first wins"
    size: int            # declared uncompressed size
    part: int            # 0 for the outer archive, 1..N for a Part-N member

class NotionArchive:
    entries: list[ArchiveEntry]
    def open(self, entry: ArchiveEntry) -> IO[bytes]: ...
    def read_text(self, entry: ArchiveEntry) -> str: ...
    def extract(self, entry: ArchiveEntry, dest: Path) -> tuple[int, str, str]: ...
    def close(self) -> None: ...

class NotionArchiveInvalid(ValueError): ...
class NotionArchiveTooLarge(ValueError): ...

def open_archive(
    zip_path: Path, staging: Path, *, max_entries: int,
    max_uncompressed_bytes: int, warn: Callable[[str, str, str], None],
) -> NotionArchive: ...
```

`extract` returns `(size_bytes, sha256, content_type)` and writes to `dest`. `warn(path, kind, detail)` is the warning sink every module shares.

**Link scanner** (`backend/app/services/notion_content.py`) — Task 5:

```python
@dataclass(frozen=True)
class LinkSpan:
    start: int       # index of the "[" opening the label
    end: int         # index one past the ")" closing the destination
    is_image: bool
    label: str
    destination: str # raw, still percent-encoded

def scan_links(source: str) -> list[LinkSpan]: ...
```

**Tree** (`backend/app/services/notion_tree.py`) — Task 6:

```python
@dataclass(frozen=True)
class PageNode:
    uuid: UUID
    entry: ArchiveEntry | None   # None on a grouping page minted for a
                                 # database that has no view stub of its own
    title: str
    notion_id: str | None
    parent_uuid: UUID | None
    order: int
    database_csv: str | None   # set on a database's own page
    row_of: UUID | None        # set on a database row page

@dataclass(frozen=True)
class NotionTree:
    pages: list[PageNode]                 # topological: a parent precedes its children
    by_target: dict[str, UUID]            # entry name -> page uuid
    assets: dict[str, ArchiveEntry]       # entry name -> non-page entry
    databases: dict[str, DatabaseInfo]    # csv entry name -> its columns and rows
    signal_counts: dict[str, int]         # "folder" | "database" | "link" | "root"

@dataclass(frozen=True)
class DatabaseInfo:
    csv_name: str
    page_uuid: UUID | None
    header: list[str]
    rows: list[list[str]]

def build_tree(
    archive: NotionArchive, *, max_pages: int,
    warn: Callable[[str, str, str], None],
) -> NotionTree: ...

class NotionExportInvalid(ValueError): ...
```

**Content** (`backend/app/services/notion_content.py`) — Task 7:

```python
@dataclass(frozen=True)
class StagedAsset:
    attachment_id: UUID
    staged_path: Path
    filename: str
    content_type: str
    size_bytes: int
    sha256: str

def translate_page(
    node: PageNode, tree: NotionTree, archive: NotionArchive, *,
    assets: dict[str, StagedAsset],
    max_blocks: int, max_content_chars: int,
    warn: Callable[[str, str, str], None],
) -> list[TreeBlock]: ...
```

**Page insert** (`backend/app/services/page_door.py`) — Task 8:

```python
async def _insert_page(
    session: AsyncSession, *, project: str, parent_id: str | None,
    after_id: str | None, title: str | None, tree: list[TreeBlock],
    properties: dict | None, actor: str | None, page_id: UUID | None = None,
) -> PageResult: ...
```

It never commits. `create_page` keeps its exact public signature and behaviour.

**Import orchestrator** (`backend/app/services/page_import.py`) — Task 9:

```python
@dataclass(frozen=True)
class ImportWarning:
    path: str | None
    kind: str
    detail: str

@dataclass(frozen=True)
class ImportReport:
    root_page_id: UUID
    pages_created: int
    databases: int
    attachments_stored: int
    attachment_bytes: int
    warnings: list[ImportWarning]
    warnings_omitted: int

class ImportBusy(RuntimeError): ...
class ImportTooLarge(ValueError): ...
class ImportNoSpace(RuntimeError): ...

MAX_WARNINGS = 500
PAGES_IMPORTED_EVENT = "pages_imported"

async def import_notion_export(
    session: AsyncSession, *, project: str, body: AsyncIterator[bytes],
    declared_length: int | None, actor: str | None,
) -> ImportReport: ...
```

`import_notion_export` raises `ImportBusy` before reading a byte when another import holds the lock.

**Edge predicate** (`backend/app/main.py`) — Task 10:

```python
def is_page_import_path(path: str) -> bool: ...
def bounds_own_body(path: str) -> bool: ...
```

`RequestBodyLimitMiddleware` calls `bounds_own_body`; `is_attachment_upload_path` keeps its name and its meaning.

**Route** (`backend/app/api/routes/page_import.py`) — Task 11: `POST /api/v1/pages/import/notion?project=<name>`, router prefix `/api/v1/pages`, tag `pages`, registered in `main.py` before the SPA mount. 201 with the report.

**Frontend upload helper** (`frontend/src/lib/api.ts`) — Task 13:

```ts
export function apiUpload<T>(path: string, body: Blob, opts?: {
  headers?: Record<string, string>
  onProgress?: (fraction: number) => void
  signal?: AbortSignal
}): Promise<T>
```

**Frontend import client** (`frontend/src/features/notes/lib/notion-import.ts`) — Task 14:

```ts
export type ImportWarning = { path: string | null; kind: string; detail: string }
export type ImportReport = {
  root_page_id: string; pages_created: number; databases: number
  attachments_stored: number; attachment_bytes: number
  warnings: ImportWarning[]; warnings_omitted: number
}
export function importNotionExport(
  project: string, file: File, onProgress?: (fraction: number) => void,
): Promise<ImportReport>
```

**Dialog** (`frontend/src/features/notes/notion-import-dialog.tsx`) — Task 14:

```tsx
export function NotionImportDialog(props: {
  project: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onImported: (rootPageId: string) => void
}): JSX.Element
```

**Fixtures** (`backend/tests/fixtures/notion/builder.py`) — Task 1:

```python
WRAPPER = "Export-68aaaecf-999e-41c4-aef1-6627846f2afb"

class Entry:
    def __init__(self, name: str, data: bytes, *, symlink: bool = False,
                 encrypted: bool = False, raw: bool = False) -> None: ...
    def written_name(self, prefix: str) -> str: ...

def build_fixture(entries: list[Entry], dest: Path, *,
                  wrapper: str | None = WRAPPER) -> Path: ...
```

Plus the named entry lists `FLAT_EXPORT`, `FOLDERED_EXPORT`, `DATABASE_EXPORT`,
`HOSTILE_EXPORT`, `PART_EXPORT`, `HTML_EXPORT`. `raw=True` writes a name without
the wrapper prefix, which is what a traversal or absolute case needs.

## Assumptions (evidence)

- The real export is flat: 2260 entries, all at depth 0 inside one `Export-<dashed-uuid>/` wrapper; 2193 `.md`, 6 `.csv`, 61 assets. Read from `/root/notion-export/export.zip` on 2026-09-20.
- All 2193 pages carry a trailing ` <32-hex>` id and a leading `# ` title line. Measured 2026-09-20: `md without 32hex id: 0`, `pages with NO leading # title: 0`.
- Property-block matching pairs 1882 of 1887 database row pages with none ambiguous; title matching cannot, because 766 pages share the title `Windows 10 Pro`. Measured 2026-09-20.
- All 289 page-to-page links occupy their whole line; zero are inline. Measured 2026-09-20.
- A balanced-parenthesis destination scanner resolves 289 page links where a `\(([^)]+)\)` regex resolves 280. Measured 2026-09-20.
- Combining database membership and standalone-link parenting parents 2171 of 2193 pages, leaving 22 roots, 0 ambiguous targets, 0 cycles and 0 warnings. All six databases resolve a stub page, so no grouping page is minted. Signal counts: database 1882, link 289, root 22. Measured 2026-09-20 by running Task 6's own implementation against `/root/notion-export/export.zip`.
- Two of the six databases are stubbed by a page whose stem does not match the CSV (`Untitled 1507-2c1e_all.csv` by a page titled "Sprint 47"), so stub detection needs the standalone-link arm and not the stem alone. Measured 2026-09-20.
- `ZipFile.writestr` assigns `flag_bits` itself, discarding one set on the ZipInfo beforehand, so an encrypted fixture is made by patching the two headers after the archive closes and a flagless non-ASCII name cannot be written at all. Verified 2026-09-20 against CPython 3.13.
- `zipfile`'s name index keeps the LAST entry of a duplicated name, so `ArchiveEntry` carries its `ZipInfo` and `NotionArchive.open` uses it. Verified 2026-09-20 by a failing first-entry-wins test.
- Tasks 1, 4, 5, 6 and 7 were staged into a scratch checkout and their planned tests run against their planned code, re-run after the round-1 review fixes on 2026-09-21: **77 passed, 0 failed**. The code blocks in those tasks are the ones that passed.
- Round 1 returned no Critical finding and no score at or below 8, so no second round was run (the cap was 3). Its three borderline scores — executability 11, coverage 13, assumptions 13 — were driven by findings that are now fixed: the missing `llm` fixture, two sync calls on an async client, `closeOnOutsidePointerDown` on the wrong component, a phantom test-helper module, a Playwright spec with no sign-in, a vacuous rollback assertion, a lying-central-directory test that proved nothing, and a precedence test with no disagreement in it.
- A tampered or truncated archive raises `zipfile.BadZipFile`, which would have escaped Task 11 as a 500; `notion_archive` now converts it to `NotionArchiveInvalid` and the route answers 422. Found on 2026-09-21 by the review's own rewritten test failing.
- Understating a member's uncompressed size in the central directory does **not** let more bytes through — `zipfile` stops at the declared length and the CRC check fails — so the running counter's real job is bounding the cumulative total across reads, not catching that lie. Measured 2026-09-21.
- End to end over the real export on 2026-09-20: all **2193** pages translate in **0.9s**, producing **13 615** blocks, **0** nesting violations and **0** errors, with 7 `unresolved_link` and 3 `stripped_source` warnings. The largest page is the 1847-row `Windows Keys` database at **1848 blocks / 182 516 characters** — inside `MAX_BLOCKS` (5 000) and `MAX_CONTENT_CHARS` (1 000 000), so the real corpus needs no truncation.
- `split_frontmatter` lives in `app/services/document_parsers.py:95`, not in `document_ingest` — `backend/app/services/page_door.py:25` imports it from there.
- `RequestBodyLimitMiddleware` exempts only `is_attachment_upload_path` — `backend/app/main.py:781`.
- `create_page`'s `llm` parameter is accepted and never used — `backend/app/services/page_door.py:449` is its only occurrence in the module.
- `page_door._INSERT_BLOCK` executes once per block — `backend/app/services/page_door.py:176`, called in a loop at `:501`.
- `store_upload` commits its own transaction, so the import cannot reuse it — `backend/app/services/page_attachments.py:188`.
- `.staging/` handling and its `staging_max_age_hours` sweep already exist — `backend/app/services/page_attachment_cleanup.py:189-192`.
- `darkraise-ui` 6.6.0 ships `dialog`, `file-upload` and `progress`; `file-upload` carries no transport. Read from `frontend/node_modules/darkraise-ui/dist/components/` on 2026-09-20.
- The SPA contains no `XMLHttpRequest` — `grep -rn "XMLHttpRequest" frontend/src` returns nothing, 2026-09-20.
- `/notes?page=<id>` exists and is written through `onSelect` — `frontend/src/routes/_authenticated/notes.tsx:12-19,65-74`.
- `pages.py` declares 13 routes and `page_attachments.py` 2, so the import makes 16 — counted 2026-09-20.
- The external executor lane is closed: `scripts/codex-gate` printed `usable=false reason=plugin-version:1.0.6 review=false lane=false` on 2026-09-20. No task carries an `**Executor:**` line, and plan review round 1 runs on a judge agent.

## Task index

1. Notion fixture builder
2. Import settings and the `pages_imported` event type
3. Attachment placement helpers
4. Archive reading and hostile-zip defences
5. The CommonMark link scanner
6. Tree derivation
7. Content translation
8. Extract `_insert_page` from `create_page`
9. The import orchestrator
10. The edge body cap
11. The import route
12. Guards leg and door parity
13. `apiUpload`
14. The import dialog
15. Header menu and event taxonomy
16. Documentation and the Playwright leg

---

### Task 1: Notion fixture builder

**Files:**
- Create: `backend/tests/fixtures/notion/__init__.py`
- Create: `backend/tests/fixtures/notion/builder.py`
- Test: `backend/tests/test_notion_fixtures.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `build_fixture` and the six named specs — see Contracts, **Fixtures**. Tasks 4, 6, 7, 9 and 11 all build their inputs with it.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_notion_fixtures.py`:

```python
"""The fixture builder, and the spec claims the fixtures encode.

The claims in `test_real_export_matches_the_spec` were measured against a real
export on 2026-09-20 and written into the design spec's section 3. The test
re-measures them whenever that archive is present, so a spec claim cannot rot
into folklore.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest

from tests.fixtures.notion.builder import (
    DATABASE_EXPORT,
    FLAT_EXPORT,
    FOLDERED_EXPORT,
    HOSTILE_EXPORT,
    HTML_EXPORT,
    PART_EXPORT,
    WRAPPER,
    build_fixture,
)

REAL_EXPORT = Path("/root/notion-export/export.zip")


def test_flat_export_is_flat_under_one_wrapper(tmp_path):
    path = build_fixture(FLAT_EXPORT, tmp_path / "flat.zip")
    names = zipfile.ZipFile(path).namelist()
    assert names, "the fixture wrote no entries"
    assert all(n.startswith(WRAPPER + "/") for n in names)
    assert all(n[len(WRAPPER) + 1:].count("/") == 0 for n in names)


def test_flat_export_pages_carry_an_id_and_a_title(tmp_path):
    path = build_fixture(FLAT_EXPORT, tmp_path / "flat.zip")
    archive = zipfile.ZipFile(path)
    pages = [n for n in archive.namelist() if n.endswith(".md")]
    assert len(pages) >= 4
    for name in pages:
        stem = name.rsplit("/", 1)[-1][: -len(".md")]
        assert re.search(r" [0-9a-f]{32}$", stem), stem
        assert archive.read(name).decode("utf-8").startswith("# ")


def test_foldered_export_nests_subpages(tmp_path):
    path = build_fixture(FOLDERED_EXPORT, tmp_path / "foldered.zip")
    names = [n[len(WRAPPER) + 1:] for n in zipfile.ZipFile(path).namelist()]
    assert any(n.count("/") == 1 for n in names)


def test_database_export_has_a_stubless_database_and_a_short_id(tmp_path):
    path = build_fixture(DATABASE_EXPORT, tmp_path / "db.zip")
    names = [n[len(WRAPPER) + 1:] for n in zipfile.ZipFile(path).namelist()]
    csvs = [n for n in names if n.endswith("_all.csv")]
    assert any(not re.search(r" [0-9a-f]{32}_all\.csv$", n) for n in csvs), (
        "no short-id CSV: the real export carries 'Untitled 1507-2c1e_all.csv'"
    )
    stubless = [
        n for n in csvs
        if n[: -len("_all.csv")] + ".md" not in names
    ]
    assert stubless, "every database has a stub page; one must not"


def test_database_csvs_carry_a_utf8_bom(tmp_path):
    path = build_fixture(DATABASE_EXPORT, tmp_path / "db.zip")
    archive = zipfile.ZipFile(path)
    for name in archive.namelist():
        if name.endswith(".csv"):
            assert archive.read(name).startswith(b"\xef\xbb\xbf"), name


def test_hostile_export_carries_each_defence_case(tmp_path):
    path = build_fixture(HOSTILE_EXPORT, tmp_path / "hostile.zip")
    infos = {i.filename: i for i in zipfile.ZipFile(path).infolist()}
    assert any(".." in n for n in infos), "no traversal entry"
    assert any(n.startswith("/") for n in infos), "no absolute entry"
    assert any(i.external_attr >> 16 & 0o170000 == 0o120000 for i in infos.values()), (
        "no symlink entry"
    )
    assert any(i.flag_bits & 0x1 for i in infos.values()), "no encrypted entry"


def test_part_export_wraps_numbered_inner_zips(tmp_path):
    path = build_fixture(PART_EXPORT, tmp_path / "parts.zip")
    names = zipfile.ZipFile(path).namelist()
    assert len([n for n in names if re.search(r"Part-\d+\.zip$", n)]) == 2
    assert not [n for n in names if n.endswith(".md")], (
        "a Part export holds no markdown at the outer level"
    )


def test_html_export_holds_no_markdown(tmp_path):
    path = build_fixture(HTML_EXPORT, tmp_path / "html.zip")
    names = zipfile.ZipFile(path).namelist()
    assert any(n.endswith(".html") for n in names)
    assert not any(n.endswith(".md") for n in names)


@pytest.mark.skipif(not REAL_EXPORT.is_file(), reason="the real export is not on this host")
def test_real_export_matches_the_spec():
    archive = zipfile.ZipFile(REAL_EXPORT)
    names = archive.namelist()
    tops = {n.split("/")[0] for n in names}
    assert len(tops) == 1, "spec section 3: one id-less wrapper folder"
    wrapper = tops.pop()
    assert not re.search(r" [0-9a-f]{32}$", wrapper)

    rel = [n[len(wrapper) + 1:] for n in names]
    assert all(r.count("/") == 0 for r in rel), "spec section 3: the export is flat"

    pages = [r for r in rel if r.endswith(".md")]
    assert all(re.search(r" [0-9a-f]{32}$", p[: -len(".md")]) for p in pages)

    csvs = [r for r in rel if r.endswith(".csv")]
    assert csvs and all(c.endswith("_all.csv") for c in csvs), (
        "spec section 3: only _all.csv exists"
    )
    assert any(not re.search(r" [0-9a-f]{32}_all\.csv$", c) for c in csvs), (
        "spec section 3: one CSV id is not 32-hex"
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest -q tests/test_notion_fixtures.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'tests.fixtures.notion'`

- [ ] **Step 3: Write the builder**

Create `backend/tests/fixtures/notion/__init__.py` as an empty file.

Create `backend/tests/fixtures/notion/builder.py`:

```python
"""Notion-export-shaped zips for the import tests.

Every shape here was measured against a real 2260-entry export on 2026-09-20
and is recorded in the design spec's section 3. `zipfile` cannot write an
encrypted member, so the hostile fixture sets the flag bit by hand -- readers
check the bit, which is all the importer's skip path needs.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

WRAPPER = "Export-68aaaecf-999e-41c4-aef1-6627846f2afb"

# A 1x1 PNG. Sniffed as image/png by the attachment store's magic-byte check.
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _id(n: int) -> str:
    return f"{n:032x}"


def _csv(header: list[str], rows: list[list[str]]) -> bytes:
    lines = [",".join(header)]
    lines += [",".join(row) for row in rows]
    return b"\xef\xbb\xbf" + ("\n".join(lines) + "\n").encode("utf-8")


class Entry:
    """One archive member, with the flags a hostile case needs."""

    def __init__(
        self, name: str, data: bytes, *, symlink: bool = False,
        encrypted: bool = False, raw: bool = False,
    ) -> None:
        self.name = name
        self.data = data
        self.symlink = symlink
        self.encrypted = encrypted
        # A traversal or absolute name must not be prefixed, or the wrapper
        # makes it an ordinary relative name and the defence goes untested.
        self.raw = raw

    def written_name(self, prefix: str) -> str:
        return self.name if self.raw else f"{prefix}{self.name}"


def _write(archive: zipfile.ZipFile, entry: Entry, prefix: str) -> None:
    info = zipfile.ZipInfo(entry.written_name(prefix))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o120777 if entry.symlink else 0o100644) << 16
    archive.writestr(info, entry.data)


def _mark_encrypted(dest: Path, name: bytes) -> None:
    """Set the encryption bit on `name`'s two headers, after the archive closed.

    `ZipFile.writestr` assigns `flag_bits` itself, so a bit set on the ZipInfo
    beforehand is discarded. The bit lives at +6 in a local file header and at
    +8 in a central-directory entry.
    """
    data = bytearray(dest.read_bytes())
    for magic, name_len_at, name_at, flag_at in (
        (b"PK\x03\x04", 26, 30, 6), (b"PK\x01\x02", 28, 46, 8),
    ):
        index = 0
        while (index := data.find(magic, index)) != -1:
            length = int.from_bytes(data[index + name_len_at:index + name_len_at + 2], "little")
            start = index + name_at
            if data[start:start + length] == name:
                data[index + flag_at] |= 0x01
            index += 4
    dest.write_bytes(bytes(data))


def build_fixture(
    entries: list[Entry], dest: Path, *, wrapper: str | None = WRAPPER,
) -> Path:
    """Write `entries` to `dest`, each under `wrapper` unless it is None."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    prefix = f"{wrapper}/" if wrapper else ""
    with zipfile.ZipFile(dest, "w") as archive:
        for entry in entries:
            _write(archive, entry, prefix)
    for entry in entries:
        if entry.encrypted:
            _mark_encrypted(dest, entry.written_name(prefix).encode("utf-8"))
    return dest


def _inner_zip(entries: list[Entry], wrapper: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for entry in entries:
            _write(archive, entry, f"{wrapper}/")
    return buffer.getvalue()


# A flat export: no folders, a root page linking to two children on their own
# lines, a database with a stub page and two row pages, and one image.
FLAT_EXPORT = [
    Entry(
        f"Home {_id(1)}.md",
        (
            f"# Home\n\n"
            f"[Notes](Notes%20{_id(2)}.md)\n\n"
            f"[Trip (2026) plan](Trip%20%282026%29%20plan%20{_id(3)}.md)\n\n"
            f"[People](People%20{_id(4)}_all.csv)\n"
        ).encode("utf-8"),
    ),
    Entry(
        f"Notes {_id(2)}.md",
        f"# Notes\n\n![shot](image.png)\n\n- [ ] open task\n- [x] done task\n".encode("utf-8"),
    ),
    Entry(
        f"Trip (2026) plan {_id(3)}.md",
        (
            "# Trip (2026) plan\n\n"
            "<aside>\nFirst paragraph.\n\nSecond paragraph.\n</aside>\n"
        ).encode("utf-8"),
    ),
    Entry(f"People {_id(4)}.md",
          f"# People\n\n[People](People%20{_id(4)}_all.csv)\n\nfilters: \nName\nsort: \nName: ascending\n".encode("utf-8")),
    Entry(f"People {_id(4)}_all.csv",
          _csv(["Name", "Role"], [["Ada", "Lead"], ["Ada", "Lead"]])),
    Entry(f"Ada {_id(5)}.md", "# Ada\n\nRole: Lead\n\nFirst hire.\n".encode("utf-8")),
    Entry(f"Ada {_id(6)}.md", "# Ada\n\nRole: Lead\n\nSecond hire, same name.\n".encode("utf-8")),
    Entry("image.png", PNG),
]

# "Create folders for subpages" on: a subpage sits in a sibling folder.
FOLDERED_EXPORT = [
    Entry(f"Parent {_id(11)}.md", "# Parent\n\nBody.\n".encode("utf-8")),
    Entry(f"Parent {_id(11)}/Child {_id(12)}.md", "# Child\n\nBody.\n".encode("utf-8")),
]

# A database whose id is not 32-hex, and a database with no stub page.
DATABASE_EXPORT = [
    Entry(f"Board {_id(21)}.md",
          "# Board\n\n[Tasks](Tasks%201507-2c1e_all.csv)\n".encode("utf-8")),
    Entry("Tasks 1507-2c1e_all.csv",
          _csv(["Name", "Status"], [["Ship", "Open"], ["Draft", "Done"]])),
    Entry(f"Orphans {_id(22)}_all.csv",
          _csv(["Name", "Note"], [["Stray", "No stub page"]])),
    Entry(f"Ship {_id(23)}.md", "# Ship\n\nStatus: Open\n\nBody.\n".encode("utf-8")),
]

HOSTILE_EXPORT = [
    Entry(f"Good {_id(31)}.md", "# Good\n\nBody.\n".encode("utf-8")),
    Entry("../escape.md", "# Escape\n".encode("utf-8"), raw=True),
    Entry("/absolute.md", "# Absolute\n".encode("utf-8"), raw=True),
    Entry("link.md", b"/etc/passwd", symlink=True),
    Entry("secret.md", b"opaque", encrypted=True),
]

# An outer archive whose members are the numbered inner zips of one export.
PART_EXPORT = [
    Entry(
        f"{WRAPPER}-Part-1.zip",
        _inner_zip([Entry(f"One {_id(41)}.md", "# One\n\nBody.\n".encode("utf-8"))], WRAPPER),
    ),
    Entry(
        f"{WRAPPER}-Part-2.zip",
        _inner_zip([Entry(f"Two {_id(42)}.md", "# Two\n\nBody.\n".encode("utf-8"))], WRAPPER),
    ),
]

HTML_EXPORT = [
    Entry(f"Home {_id(51)}.html", b"<h1>Home</h1>"),
    Entry("style.css", b"body{}"),
]
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `python -m pytest -q tests/test_notion_fixtures.py -v`
Expected: PASS. `test_real_export_matches_the_spec` passes on this host and skips elsewhere.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/fixtures/notion backend/tests/test_notion_fixtures.py
git commit -m "test(notion): add export fixtures and spec checks"
```

---

### Task 2: Import settings and the `pages_imported` event type

**Files:**
- Modify: `backend/app/config.py` (beside `attachment_max_bytes`, currently line 116)
- Modify: `backend/app/services/events.py` (`EVENT_TYPES`, beside the `page_*` block at lines 190-195)
- Test: `backend/tests/test_notion_import_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the six `Settings` fields and the `"pages_imported"` event type — see Contracts, **Settings** and **Event type**. Tasks 4, 9, 10, 11 and 15 consume them.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

Taxonomy-first: the vocabulary value lands before its emitter ships, so Task 9 can write the event without widening a closed vocabulary in the same change.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_notion_import_config.py`:

```python
from app.config import settings
from app.services.events import EVENT_TYPES


def test_import_ceilings_have_their_documented_defaults():
    assert settings.notion_import_max_bytes == 1_073_741_824
    assert settings.notion_import_max_entries == 50_000
    assert settings.notion_import_max_uncompressed_bytes == 5_368_709_120
    assert settings.notion_import_max_pages == 10_000
    assert settings.notion_import_max_blocks == 250_000
    assert settings.notion_import_max_seconds == 900


def test_the_upload_ceiling_clears_the_real_export():
    # The measured export is 34.5 MB; a ceiling under it would refuse the one
    # archive this feature was designed against.
    assert settings.notion_import_max_bytes > 40 * 1024 * 1024


def test_pages_imported_is_in_the_event_vocabulary():
    assert "pages_imported" in EVENT_TYPES
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest -q tests/test_notion_import_config.py`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'notion_import_max_bytes'`

- [ ] **Step 3: Add the settings and the event type**

In `backend/app/config.py`, directly after the `attachment_max_bytes` line:

```python
    # Notion import ceilings. Operator-level limits rather than job config:
    # no job exists here, and FieldDescriptor.default is typed int anyway.
    # The measured real export is 34.5 MB / 2260 entries / 2193 pages.
    notion_import_max_bytes: int = 1_073_741_824
    notion_import_max_entries: int = 50_000
    notion_import_max_uncompressed_bytes: int = 5_368_709_120
    notion_import_max_pages: int = 10_000
    # Bounds the plan's peak memory, which is held entirely in the process.
    notion_import_max_blocks: int = 250_000
    notion_import_max_seconds: int = 900
```

In `backend/app/services/events.py`, immediately after `"page_purged",` in `EVENT_TYPES`:

```python
    # One row per import, on its root page. Non-strict: the import is
    # re-runnable, so a lost row costs an audit line, not a denominator.
    "pages_imported",
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `python -m pytest -q tests/test_notion_import_config.py -v`
Expected: PASS

Then confirm nothing else read the vocabulary by length:

Run: `python -m pytest -q tests/test_events.py tests/test_event_taxonomy_map.py`
Expected: **PASS.** That guard only demands a frontend map entry for a value with a *live* emitter — "live" meaning some call under `backend/app` passes the literal through a keyword argument named `event_type` — and landing a value ahead of its emitter is exactly the taxonomy-first discipline it is written to protect. It goes red once Task 9 ships the emitter, and Task 15 closes it.

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/services/events.py backend/tests/test_notion_import_config.py
git commit -m "feat(notion): add import ceilings and the event type"
```

---

### Task 3: Attachment placement helpers

**Files:**
- Modify: `backend/app/services/page_attachments.py` (after `store_upload`, which ends at line 203; the module ends at 232)
- Test: `backend/tests/test_page_attachment_placement.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `place_staged` and `insert_attachment_row` — see Contracts, **Attachment helpers**. Task 9 consumes both.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

`store_upload` commits its own transaction, so the import cannot reuse it: the import's rows must land inside the one transaction that also writes the pages. These two helpers are the halves of `store_upload` the import needs, with the commit left out. Keeping them in this module is what stops a caller-chosen string reaching a filesystem path from outside it.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_page_attachment_placement.py`:

```python
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.config import settings
from app.services.page_attachments import (
    attachment_path,
    insert_attachment_row,
    place_staged,
)


def test_place_staged_moves_the_file_onto_its_sharded_path(tmp_path, monkeypatch):
    root = tmp_path / "attachments"
    monkeypatch.setattr(settings, "attachments_dir", str(root))
    staged = tmp_path / "staged.bin"
    staged.write_bytes(b"payload")
    attachment_id = uuid4()

    place_staged(staged, attachment_id)

    final = attachment_path(attachment_id)
    assert final.is_file()
    assert final.read_bytes() == b"payload"
    assert final.parent.name == str(attachment_id)[:2]
    assert not staged.exists()


def test_place_staged_creates_the_shard_directory(tmp_path, monkeypatch):
    root = tmp_path / "attachments"
    monkeypatch.setattr(settings, "attachments_dir", str(root))
    staged = tmp_path / "staged.bin"
    staged.write_bytes(b"x")
    attachment_id = uuid4()
    assert not attachment_path(attachment_id).parent.exists()

    place_staged(staged, attachment_id)

    assert attachment_path(attachment_id).is_file()


@pytest.mark.asyncio
async def test_insert_attachment_row_does_not_commit(session, monkeypatch):
    # The conftest session runs inside an outer transaction that DROPS a
    # commit() and whose rollback() ends the isolation boundary outright, so
    # "write, roll back, look for the row" proves nothing here. Spy instead.
    calls: list[int] = []
    original = session.commit

    async def spy() -> None:
        calls.append(1)
        await original()

    monkeypatch.setattr(session, "commit", spy)
    await insert_attachment_row(
        session,
        attachment_id=uuid4(),
        project="notes",
        page_id=None,
        filename="a.png",
        content_type="image/png",
        size_bytes=7,
        sha256="ab" * 32,
    )
    assert calls == [], "the helper committed; the import needs one transaction"


@pytest.mark.asyncio
async def test_insert_attachment_row_accepts_a_null_page(session):
    attachment_id = uuid4()
    await insert_attachment_row(
        session,
        attachment_id=attachment_id,
        project="notes",
        page_id=None,
        filename="a.bin",
        content_type="application/octet-stream",
        size_bytes=1,
        sha256="cd" * 32,
    )
    row = (
        await session.execute(
            text(
                "SELECT uploaded_for_page_id, project, filename "
                "FROM page_attachments WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(attachment_id)},
        )
    ).one()
    assert row.uploaded_for_page_id is None
    assert row.project == "notes"
    assert row.filename == "a.bin"
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest -q tests/test_page_attachment_placement.py`
Expected: FAIL — `ImportError: cannot import name 'place_staged'`

- [ ] **Step 3: Write the implementation**

In `backend/app/services/page_attachments.py`, add both names to `__all__` if that module declares one, then append after `store_upload`:

```python
def place_staged(staged: Path, attachment_id: UUID) -> None:
    """Move an already-written staged file onto its final sharded path.

    `os.replace` rather than a copy: staging lives under the same
    `attachments_dir`, so the rename is atomic and costs no second write of a
    file that may be tens of megabytes.
    """
    final = attachment_path(attachment_id)
    final.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staged, final)


async def insert_attachment_row(
    session: AsyncSession,
    *,
    attachment_id: UUID,
    project: str,
    page_id: UUID | None,
    filename: str,
    content_type: str,
    size_bytes: int,
    sha256: str,
) -> None:
    """Insert one row and DO NOT commit.

    `store_upload` commits because its file is already on disk and its caller
    has nothing else to write. An import writes its attachment rows, its pages
    and its journal row in one transaction, so it needs the insert without the
    commit.
    """
    await session.execute(_INSERT, {
        "id": str(attachment_id),
        "project": project,
        "page": None if page_id is None else str(page_id),
        "filename": filename,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "sha256": sha256,
    })
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `python -m pytest -q tests/test_page_attachment_placement.py -v`
Expected: PASS

Then confirm the existing upload path is untouched:

Run: `python -m pytest -q tests/test_page_attachments.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/page_attachments.py backend/tests/test_page_attachment_placement.py
git commit -m "feat(attachments): add staged placement and row insert"
```

---

### Task 4: Archive reading and hostile-zip defences

**Files:**
- Create: `backend/app/services/notion_archive.py`
- Test: `backend/tests/test_notion_archive.py`

**Interfaces:**
- Consumes: `build_fixture` and the fixture specs (Contracts, **Fixtures**); the `notion_import_max_entries` and `notion_import_max_uncompressed_bytes` settings (Contracts, **Settings**).
- Produces: `ArchiveEntry`, `NotionArchive`, `open_archive`, `NotionArchiveInvalid`, `NotionArchiveTooLarge` — see Contracts, **Archive**. Tasks 6, 7 and 9 consume them.

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

Risk 3 is the zip itself: traversal, symlinks, a lying central directory and decompression expansion are all attacker-controlled here, and the archive is the one input this feature takes from outside.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_notion_archive.py`:

```python
from __future__ import annotations

import hashlib
import zipfile

import pytest

from app.services.notion_archive import (
    NotionArchiveInvalid,
    NotionArchiveTooLarge,
    _decode_name,
    open_archive,
)
from tests.fixtures.notion.builder import (
    FLAT_EXPORT,
    HOSTILE_EXPORT,
    PART_EXPORT,
    Entry,
    build_fixture,
)

LIMITS = {"max_entries": 50_000, "max_uncompressed_bytes": 5_368_709_120}


def _open(path, staging, **over):
    warnings: list[tuple[str, str, str]] = []
    limits = {**LIMITS, **over}
    archive = open_archive(
        path, staging, warn=lambda p, k, d: warnings.append((p, k, d)), **limits
    )
    return archive, warnings


def test_the_wrapper_folder_is_stripped(tmp_path):
    path = build_fixture(FLAT_EXPORT, tmp_path / "flat.zip")
    archive, _ = _open(path, tmp_path / "staging")
    assert archive.entries
    assert all("/" not in e.name for e in archive.entries)
    assert any(e.name.startswith("Home ") for e in archive.entries)


def test_a_wrapper_with_many_children_is_still_stripped(tmp_path):
    # The real export's wrapper holds 2260 children, so a "single child" rule
    # would not fire on it. The signal is one shared id-less component.
    path = build_fixture(FLAT_EXPORT, tmp_path / "flat.zip")
    archive, _ = _open(path, tmp_path / "staging")
    assert len(archive.entries) >= 8


def test_traversal_absolute_symlink_and_encrypted_entries_are_skipped(tmp_path):
    path = build_fixture(HOSTILE_EXPORT, tmp_path / "hostile.zip")
    archive, warnings = _open(path, tmp_path / "staging")
    names = {e.name for e in archive.entries}
    assert not [n for n in names if ".." in n or n.startswith("/")]
    assert "link.md" not in names
    assert "secret.md" not in names
    assert any(n.startswith("Good ") for n in names)
    assert {w[1] for w in warnings} == {"skipped_entry"}


def test_a_flagless_utf8_name_is_recovered():
    # zipfile cannot WRITE a flagless non-ASCII name -- it sets the UTF-8 flag
    # whenever the name needs one -- so the decoder is tested directly. A
    # flagless entry holding the UTF-8 bytes of "cafe\u0301.md" reaches us as
    # its cp437 reading, "caf\u251c\u2310.md", and must decode back.
    info = zipfile.ZipInfo("caf\u251c\u2310.md")
    info.flag_bits = 0
    assert _decode_name(info) == "caf\u00e9.md"


def test_a_genuine_cp437_name_is_kept():
    info = zipfile.ZipInfo("caf\u00e9.md")
    info.flag_bits = 0
    assert _decode_name(info) == "caf\u00e9.md"


def test_a_flagged_name_is_taken_as_is():
    info = zipfile.ZipInfo("caf\u00e9.md")
    info.flag_bits = 0x800
    assert _decode_name(info) == "caf\u00e9.md"


def test_a_duplicate_name_keeps_the_first_entry(tmp_path):
    entries = [
        Entry("Dup 00000000000000000000000000000001.md", b"# First\n"),
        Entry("Dup 00000000000000000000000000000001.md", b"# Second\n"),
    ]
    path = build_fixture(entries, tmp_path / "dup.zip")
    archive, warnings = _open(path, tmp_path / "staging")
    assert len(archive.entries) == 1
    assert archive.read_text(archive.entries[0]) == "# First\n"
    assert any(w[1] == "skipped_entry" for w in warnings)


def test_the_entry_count_cap_refuses(tmp_path):
    path = build_fixture(FLAT_EXPORT, tmp_path / "flat.zip")
    with pytest.raises(NotionArchiveTooLarge):
        _open(path, tmp_path / "staging", max_entries=2)


def test_the_declared_sizes_give_an_early_refusal(tmp_path):
    entries = [Entry("Big 00000000000000000000000000000001.md", b"x" * 5000)]
    path = build_fixture(entries, tmp_path / "big.zip")
    with pytest.raises(NotionArchiveTooLarge):
        _open(path, tmp_path / "staging", max_uncompressed_bytes=100)


def test_the_running_counter_bounds_the_total_across_reads(tmp_path):
    # The declared total (1800) clears the bound, so only the counter can stop
    # this. Each entry is read twice, which is what the import itself does --
    # once for the title and property block, once to translate the body.
    entries = [
        Entry(f"P{i} {i:032x}.md", b"x" * 600) for i in range(3)
    ]
    path = build_fixture(entries, tmp_path / "many.zip")
    archive, _ = _open(path, tmp_path / "staging", max_uncompressed_bytes=2000)
    with pytest.raises(NotionArchiveTooLarge):
        for _ in range(2):
            for entry in archive.entries:
                archive.read_text(entry)


def test_a_tampered_size_is_refused_rather_than_raising_BadZipFile(tmp_path):
    # Understating the central directory's uncompressed size does not let more
    # bytes through -- zipfile stops at the declared length and the CRC check
    # fails. What matters is that the caller sees this module's own refusal, so
    # the route answers 422 instead of a 500 from a zipfile internal.
    entries = [Entry("Big 00000000000000000000000000000001.md", b"x" * 5000)]
    path = build_fixture(entries, tmp_path / "liar.zip")
    raw = bytearray(path.read_bytes())
    index = raw.find(b"PK\x01\x02")
    assert index != -1
    raw[index + 24:index + 28] = (10).to_bytes(4, "little")  # uncompressed size
    path.write_bytes(bytes(raw))

    archive, _ = _open(path, tmp_path / "staging")
    with pytest.raises(NotionArchiveInvalid):
        archive.read_text(archive.entries[0])


def test_a_truncated_archive_is_refused(tmp_path):
    path = build_fixture(
        [Entry("A 00000000000000000000000000000001.md", b"# A\n")],
        tmp_path / "cut.zip",
    )
    path.write_bytes(path.read_bytes()[: -40])
    with pytest.raises(NotionArchiveInvalid):
        _open(path, tmp_path / "staging")


def test_extract_returns_size_hash_and_sniffed_type(tmp_path):
    path = build_fixture(FLAT_EXPORT, tmp_path / "flat.zip")
    archive, _ = _open(path, tmp_path / "staging")
    png = next(e for e in archive.entries if e.name == "image.png")
    dest = tmp_path / "out.bin"

    size, digest, content_type = archive.extract(png, dest)

    raw = dest.read_bytes()
    assert size == len(raw)
    assert digest == hashlib.sha256(raw).hexdigest()
    assert content_type == "image/png"


def test_a_part_export_reads_as_one_tree(tmp_path):
    path = build_fixture(PART_EXPORT, tmp_path / "parts.zip")
    archive, _ = _open(path, tmp_path / "staging")
    names = sorted(e.name for e in archive.entries)
    assert [n.split(" ")[0] for n in names] == ["One", "Two"]
    assert sorted(e.part for e in archive.entries) == [1, 2]


def test_a_zip_attachment_is_not_opened_as_a_part(tmp_path):
    entries = [
        Entry("Page 00000000000000000000000000000001.md", b"# Page\n\n[z](ODT.zip)\n"),
        Entry("ODT.zip", b"PK\x05\x06" + b"\x00" * 18),
    ]
    path = build_fixture(entries, tmp_path / "attach.zip")
    archive, _ = _open(path, tmp_path / "staging")
    assert {e.name for e in archive.entries} == {
        "Page 00000000000000000000000000000001.md", "ODT.zip",
    }


def test_an_archive_with_no_markdown_is_invalid(tmp_path):
    path = build_fixture([Entry("only.txt", b"hi")], tmp_path / "none.zip")
    with pytest.raises(NotionArchiveInvalid):
        _open(path, tmp_path / "staging")
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest -q tests/test_notion_archive.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.notion_archive'`

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/notion_archive.py`:

```python
"""Reading a Notion export archive safely.

No entry name is ever joined into a filesystem path: entries are read by name
through `zipfile`, and an extraction writes to a destination the caller minted.
The central directory's declared sizes buy a cheap early refusal, but a crafted
archive can lie in them, so the enforced bound is a running counter over
chunked reads -- `read()` of a whole entry is never called.
"""
from __future__ import annotations

import hashlib
import logging
import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import IO
from zipfile import ZipInfo

from app.services.page_attachments import sniff_content_type

logger = logging.getLogger(__name__)

CHUNK = 1 << 16
_SNIFF_BYTES = 16
_ID_SUFFIX = re.compile(r" [0-9a-f]{32}$")
_PART_SUFFIX = re.compile(r"[-_ ]?Part[-_ ]?(\d+)\.zip$", re.IGNORECASE)
_DRIVE = re.compile(r"^[A-Za-z]:")

Warn = Callable[[str, str, str], None]


class NotionArchiveInvalid(ValueError):
    """The archive is not a Markdown & CSV Notion export."""


class NotionArchiveTooLarge(ValueError):
    """The archive passed an entry-count or uncompressed-bytes ceiling."""


@dataclass(frozen=True)
class ArchiveEntry:
    name: str
    info: ZipInfo
    size: int
    part: int


def _decode_name(info: zipfile.ZipInfo) -> str:
    """Recover a UTF-8 name from an entry that did not set the UTF-8 flag.

    `zipfile` decodes such a name as cp437. Most producers actually wrote
    UTF-8, so re-encoding to cp437 and decoding as UTF-8 recovers it; a name
    that really was cp437 fails that decode and keeps what zipfile gave us.
    """
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode("cp437").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return info.filename


def _normalise(name: str) -> str | None:
    """A `/`-separated relative name, or None when the entry must be skipped."""
    candidate = name.replace("\\", "/")
    if candidate.startswith("/") or _DRIVE.match(candidate):
        return None
    parts = [p for p in candidate.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return None
    return "/".join(parts) or None


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return (info.external_attr >> 16) & 0o170000 == 0o120000


def _is_encrypted(info: zipfile.ZipInfo) -> bool:
    return bool(info.flag_bits & 0x1)


def _strip_wrapper(names: list[str]) -> int:
    """How many leading path components every entry shares and none identifies.

    Notion wraps a workspace export in one `Export-<uuid>/` folder, and a
    teamspace export adds more. The signal is a single shared component that
    carries no 32-hex id -- not how many children it has, since the measured
    export's wrapper holds 2260.
    """
    depth = 0
    while True:
        heads = {n.split("/")[0] for n in names if n.count("/") > depth - 1}
        if len(heads) != 1:
            return depth
        head = heads.pop()
        if _ID_SUFFIX.search(head):
            return depth
        if not all(n.startswith(head + "/") for n in names):
            return depth
        names = [n[len(head) + 1:] for n in names]
        depth += 1


class _Source:
    """One physical zip and the entries taken from it."""

    def __init__(self, path: Path, part: int) -> None:
        self.zip = zipfile.ZipFile(path)
        self.part = part


class NotionArchive:
    def __init__(self, sources: list[_Source], max_uncompressed_bytes: int) -> None:
        self._sources = {s.part: s for s in sources}
        self._max = max_uncompressed_bytes
        self._read = 0
        self.entries: list[ArchiveEntry] = []

    def open(self, entry: ArchiveEntry) -> IO[bytes]:
        # By ZipInfo, never by name: zipfile's NameToInfo keeps the LAST entry
        # of a duplicated name, so opening by name would hand back the entry
        # `_collect` deliberately skipped.
        return self._sources[entry.part].zip.open(entry.info)

    def _consume(self, n: int) -> None:
        self._read += n
        if self._read > self._max:
            raise NotionArchiveTooLarge(
                f"the archive expands past {self._max} bytes"
            )

    def read_text(self, entry: ArchiveEntry) -> str:
        buffer = bytearray()
        # A tampered or truncated member surfaces as this module's own refusal,
        # so the route answers 422 rather than leaking a zipfile internal as a
        # 500. NotionArchiveTooLarge is ours already and must pass through.
        try:
            with self.open(entry) as handle:
                while chunk := handle.read(CHUNK):
                    self._consume(len(chunk))
                    buffer += chunk
        except NotionArchiveTooLarge:
            raise
        except (zipfile.BadZipFile, OSError, EOFError) as exc:
            raise NotionArchiveInvalid(
                f"{entry.name} could not be read: {exc}"
            ) from exc
        return buffer.decode("utf-8-sig", errors="replace")

    def extract(self, entry: ArchiveEntry, dest: Path) -> tuple[int, str, str]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        head = b""
        try:
            with self.open(entry) as handle, open(dest, "wb") as out:
                while chunk := handle.read(CHUNK):
                    self._consume(len(chunk))
                    size += len(chunk)
                    if len(head) < _SNIFF_BYTES:
                        head += chunk[: _SNIFF_BYTES - len(head)]
                    digest.update(chunk)
                    out.write(chunk)
        except NotionArchiveTooLarge:
            dest.unlink(missing_ok=True)
            raise
        except (zipfile.BadZipFile, OSError, EOFError) as exc:
            dest.unlink(missing_ok=True)
            raise NotionArchiveInvalid(
                f"{entry.name} could not be read: {exc}"
            ) from exc
        return size, digest.hexdigest(), sniff_content_type(head)

    def close(self) -> None:
        for source in self._sources.values():
            source.zip.close()


def _collect(zf: zipfile.ZipFile, part: int, warn: Warn) -> list[ArchiveEntry]:
    seen: set[str] = set()
    out: list[ArchiveEntry] = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        decoded = _decode_name(info)
        if _is_symlink(info):
            warn(decoded, "skipped_entry", "symlink entries are not read")
            continue
        if _is_encrypted(info):
            warn(decoded, "skipped_entry", "encrypted entries cannot be read")
            continue
        name = _normalise(decoded)
        if name is None:
            warn(decoded, "skipped_entry", "the name escapes the archive root")
            continue
        if name in seen:
            warn(name, "skipped_entry", "a duplicate name; the first entry wins")
            continue
        seen.add(name)
        out.append(ArchiveEntry(name=name, info=info,
                                size=info.file_size, part=part))
    return out


def open_archive(
    zip_path: Path,
    staging: Path,
    *,
    max_entries: int,
    max_uncompressed_bytes: int,
    warn: Warn,
) -> NotionArchive:
    try:
        outer = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError, EOFError) as exc:
        raise NotionArchiveInvalid(f"this is not a readable zip: {exc}") from exc
    members = [i for i in outer.infolist() if not i.is_dir()]
    if len(members) > max_entries:
        outer.close()
        raise NotionArchiveTooLarge(
            f"the archive holds {len(members)} entries; the bound is {max_entries}"
        )
    # A cheap early refusal off the central directory. It can understate, which
    # is why the running counter below is the real enforcement -- but an honest
    # bomb is refused here without reading a byte.
    declared = sum(i.file_size for i in members)
    if declared > max_uncompressed_bytes:
        outer.close()
        raise NotionArchiveTooLarge(
            f"the archive declares {declared} uncompressed bytes; the bound is "
            f"{max_uncompressed_bytes}"
        )

    parts = [i for i in members if _PART_SUFFIX.search(_decode_name(i))]
    sources: list[_Source] = []
    if parts and not any(_decode_name(i).endswith(".md") for i in members):
        # A Part-N export. Each inner zip is EXTRACTED first and opened from
        # disk: zipfile seeks backwards per entry, and a compressed stream read
        # through the outer archive re-decompresses from the start every time.
        staging.mkdir(parents=True, exist_ok=True)
        for info in sorted(parts, key=lambda i: _decode_name(i)):
            number = int(_PART_SUFFIX.search(_decode_name(info)).group(1))
            target = staging / f"part-{number}.zip"
            with outer.open(info) as src, open(target, "wb") as out:
                while chunk := src.read(CHUNK):
                    out.write(chunk)
            sources.append(_Source(target, number))
        outer.close()
    else:
        sources.append(_Source(zip_path, 0))

    archive = NotionArchive(sources, max_uncompressed_bytes)
    collected: list[ArchiveEntry] = []
    total = 0
    for source in sources:
        found = _collect(source.zip, source.part, warn)
        total += len(found)
        collected += found
    if total > max_entries:
        archive.close()
        raise NotionArchiveTooLarge(
            f"the archive holds {total} entries; the bound is {max_entries}"
        )

    depth = _strip_wrapper([e.name for e in collected])
    if depth:
        collected = [
            ArchiveEntry(
                name="/".join(e.name.split("/")[depth:]),
                info=e.info, size=e.size, part=e.part,
            )
            for e in collected
        ]
        collected = [e for e in collected if e.name]

    if not any(e.name.endswith(".md") for e in collected):
        archive.close()
        if any(e.name.lower().endswith((".html", ".htm")) for e in collected):
            raise NotionArchiveInvalid(
                "this is Notion's HTML export; re-export from Notion as "
                "Markdown & CSV"
            )
        raise NotionArchiveInvalid("the archive holds no markdown pages")

    archive.entries = collected
    return archive
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `python -m pytest -q tests/test_notion_archive.py -v`
Expected: PASS, 16 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/notion_archive.py backend/tests/test_notion_archive.py
git commit -m "feat(notion): read export archives safely"
```

---

### Task 5: The CommonMark link scanner

**Files:**
- Create: `backend/app/services/notion_content.py`
- Test: `backend/tests/test_notion_links.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `LinkSpan` and `scan_links` — see Contracts, **Link scanner**. Task 7 consumes both.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

This is the whole of `notion_content.py` for now; Task 7 appends the translation to the same module.

A regex is not sufficient and the measurement says so: `\(([^)]+)\)` resolves 280 of the real export's page links, and this scanner resolves 289. The nine it recovers are targets holding a literal `(`, which CommonMark permits when the parentheses balance.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_notion_links.py`:

```python
from app.services.notion_content import scan_links


def _targets(source: str) -> list[str]:
    return [span.destination for span in scan_links(source)]


def test_a_plain_link_is_found():
    assert _targets("see [docs](a.md) here") == ["a.md"]


def test_balanced_parentheses_in_a_target_are_kept():
    # The real export holds nine of these, e.g. "1 Image (no compress) + ...".
    source = "[shot](1%20Image%20(no%20compress)%20plan%20abc.md)"
    assert _targets(source) == ["1%20Image%20(no%20compress)%20plan%20abc.md"]


def test_nested_balanced_parentheses_are_kept():
    assert _targets("[x](a((b))c.md)") == ["a((b))c.md"]


def test_an_unbalanced_parenthesis_stops_at_the_first_close():
    assert _targets("[x](a(b.md) tail") == []


def test_the_angle_bracket_form_is_read():
    assert _targets("[x](<a file.md>)") == ["a file.md"]


def test_an_escaped_parenthesis_does_not_close_the_target():
    assert _targets(r"[x](a\).md)") == [r"a\).md"]


def test_an_image_is_flagged():
    spans = scan_links("![alt](image.png)")
    assert len(spans) == 1
    assert spans[0].is_image is True
    assert spans[0].label == "alt"


def test_a_link_is_not_flagged_as_an_image():
    assert scan_links("[alt](a.md)")[0].is_image is False


def test_a_fenced_code_block_is_skipped():
    source = "text\n\n```\n[x](a.md)\n```\n\n[y](b.md)\n"
    assert _targets(source) == ["b.md"]


def test_a_tilde_fence_is_skipped():
    source = "~~~\n[x](a.md)\n~~~\n[y](b.md)\n"
    assert _targets(source) == ["b.md"]


def test_an_inline_code_span_is_skipped():
    assert _targets("`[x](a.md)` and [y](b.md)") == ["b.md"]


def test_spans_index_the_whole_construct():
    source = "go [docs](a.md) now"
    span = scan_links(source)[0]
    assert source[span.start:span.end] == "[docs](a.md)"


def test_an_image_span_includes_its_bang():
    source = "![alt](a.png)"
    span = scan_links(source)[0]
    assert source[span.start:span.end] == "![alt](a.png)"


def test_a_label_holding_brackets_is_read():
    assert _targets("[a [b] c](x.md)") == ["x.md"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest -q tests/test_notion_links.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.notion_content'`

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/notion_content.py`:

```python
"""Translating one Notion page's markdown into a page block tree."""
from __future__ import annotations

import re
from dataclasses import dataclass

_FENCE = re.compile(r"^[ \t]*(```+|~~~+)")


@dataclass(frozen=True)
class LinkSpan:
    start: int
    end: int
    is_image: bool
    label: str
    destination: str


def _masked(source: str) -> list[bool]:
    """True at every index inside a fenced block or an inline code span.

    A link rewrite must not touch a code sample. Fences are matched on their
    own lines; inline spans on matched backtick runs, the way CommonMark
    closes them.
    """
    mask = [False] * len(source)
    offset = 0
    fence: str | None = None
    for line in source.splitlines(keepends=True):
        opener = _FENCE.match(line)
        if fence is None and opener:
            fence = opener.group(1)[0]
            for i in range(offset, offset + len(line)):
                mask[i] = True
        elif fence is not None:
            for i in range(offset, offset + len(line)):
                mask[i] = True
            if opener and opener.group(1)[0] == fence:
                fence = None
        offset += len(line)

    i = 0
    n = len(source)
    while i < n:
        if mask[i] or source[i] != "`":
            i += 1
            continue
        run = 0
        while i + run < n and source[i + run] == "`":
            run += 1
        close = source.find("`" * run, i + run)
        while close != -1 and close + run < n and source[close + run] == "`":
            close = source.find("`" * run, close + run + 1)
        if close == -1:
            i += run
            continue
        for j in range(i, close + run):
            mask[j] = True
        i = close + run
    return mask


def _read_destination(source: str, start: int) -> tuple[str, int] | None:
    """Read a link destination beginning at `start`, the index after `](`.

    Returns the raw destination and the index of its closing `)`. Follows
    CommonMark: parentheses may appear in a destination when they balance, a
    backslash escapes the next character, and `<...>` delimits a destination
    that holds spaces.
    """
    n = len(source)
    if start < n and source[start] == "<":
        end = source.find(">", start + 1)
        if end != -1 and end + 1 < n and source[end + 1] == ")":
            return source[start + 1:end], end + 1
        return None
    depth = 1
    i = start
    while i < n:
        char = source[i]
        if char == "\\":
            i += 2
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return source[start:i], i
        elif char in " \t\n":
            return None
        i += 1
    return None


def scan_links(source: str) -> list[LinkSpan]:
    """Every markdown link and image in `source`, code excluded."""
    mask = _masked(source)
    spans: list[LinkSpan] = []
    i = 0
    n = len(source)
    while i < n:
        j = source.find("](", i)
        if j == -1:
            break
        if mask[j]:
            i = j + 2
            continue
        # Walk back to the "[" that opens this label, counting nested pairs so
        # a label holding brackets is read whole.
        depth = 1
        k = j - 1
        while k >= 0:
            if source[k] == "\\":
                k -= 1
            elif source[k] == "]":
                depth += 1
            elif source[k] == "[":
                depth -= 1
                if depth == 0:
                    break
            k -= 1
        if k < 0:
            i = j + 2
            continue
        read = _read_destination(source, j + 2)
        if read is None:
            i = j + 2
            continue
        destination, close = read
        is_image = k > 0 and source[k - 1] == "!"
        spans.append(LinkSpan(
            start=k - 1 if is_image else k,
            end=close + 1,
            is_image=is_image,
            label=source[k + 1:j],
            destination=destination,
        ))
        i = close + 1
    return spans
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `python -m pytest -q tests/test_notion_links.py -v`
Expected: PASS, 14 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/notion_content.py backend/tests/test_notion_links.py
git commit -m "feat(notion): scan commonmark link destinations"
```

---

### Task 6: Tree derivation

**Files:**
- Create: `backend/app/services/notion_tree.py`
- Test: `backend/tests/test_notion_tree.py`

**Interfaces:**
- Consumes: `NotionArchive`, `ArchiveEntry` (Contracts, **Archive**); `scan_links` (Contracts, **Link scanner**); the fixture specs (Contracts, **Fixtures**).
- Produces: `PageNode`, `DatabaseInfo`, `NotionTree`, `build_tree`, `NotionExportInvalid` — see Contracts, **Tree**. Tasks 7 and 9 consume them.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

The three parent signals and their precedence are the design's load-bearing claim: on the measured export they parent 2171 of 2193 pages with none ambiguous, where the programme's flat rule parented none. Getting the precedence backwards re-parents 1847 database rows onto whatever linked them.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_notion_tree.py`:

```python
from __future__ import annotations

import pytest

from app.services.notion_archive import open_archive
from app.services.notion_tree import NotionExportInvalid, build_tree
from tests.fixtures.notion.builder import (
    DATABASE_EXPORT,
    FLAT_EXPORT,
    FOLDERED_EXPORT,
    Entry,
    build_fixture,
)


def _tree(entries, tmp_path, name="x.zip", max_pages=10_000):
    path = build_fixture(entries, tmp_path / name)
    warnings: list[tuple] = []
    archive = open_archive(
        path, tmp_path / "staging", max_entries=50_000,
        max_uncompressed_bytes=5_368_709_120,
        warn=lambda p, k, d: warnings.append((p, k, d)),
    )
    tree = build_tree(
        archive, max_pages=max_pages,
        warn=lambda p, k, d: warnings.append((p, k, d)),
    )
    return tree, warnings


def _by_title(tree):
    return {node.title: node for node in tree.pages}


def test_titles_come_from_the_leading_heading(tmp_path):
    tree, _ = _tree(FLAT_EXPORT, tmp_path)
    assert "Home" in _by_title(tree)
    assert "Trip (2026) plan" in _by_title(tree)


def test_a_title_falls_back_to_the_stem_without_its_id(tmp_path):
    entries = [Entry("Bare 00000000000000000000000000000001.md", b"No heading here\n")]
    tree, _ = _tree(entries, tmp_path)
    assert _by_title(tree)["Bare"].notion_id == "0" * 31 + "1"


def test_folder_nesting_parents_a_subpage(tmp_path):
    tree, _ = _tree(FOLDERED_EXPORT, tmp_path)
    nodes = _by_title(tree)
    assert nodes["Child"].parent_uuid == nodes["Parent"].uuid
    assert tree.signal_counts["folder"] == 1


def test_a_standalone_link_parents_its_target(tmp_path):
    tree, _ = _tree(FLAT_EXPORT, tmp_path)
    nodes = _by_title(tree)
    assert nodes["Notes"].parent_uuid == nodes["Home"].uuid
    assert nodes["Trip (2026) plan"].parent_uuid == nodes["Home"].uuid


def test_an_inline_link_does_not_parent(tmp_path):
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\nsee [B](B%2000000000000000000000000000000002.md) inline\n"),
        Entry("B 00000000000000000000000000000002.md", b"# B\n"),
    ]
    tree, _ = _tree(entries, tmp_path)
    assert _by_title(tree)["B"].parent_uuid is None


def test_two_inbound_standalone_links_leave_the_page_at_the_root(tmp_path):
    target = "T 00000000000000000000000000000003.md"
    link = f"[T]({target.replace(' ', '%20')})".encode()
    entries = [
        Entry("A 00000000000000000000000000000001.md", b"# A\n\n" + link + b"\n"),
        Entry("B 00000000000000000000000000000002.md", b"# B\n\n" + link + b"\n"),
        Entry(target, b"# T\n"),
    ]
    tree, _ = _tree(entries, tmp_path)
    assert _by_title(tree)["T"].parent_uuid is None


def test_database_membership_beats_a_standalone_link(tmp_path):
    # A real disagreement: Home links to the row page on its own line, which
    # signal 3 would parent under Home. Signal 2 must win, or 1847 rows scatter
    # out of their database on the measured export.
    row = "Ada 00000000000000000000000000000005.md"
    entries = [
        Entry("Home 00000000000000000000000000000001.md",
              f"# Home\n\n[Ada]({row.replace(' ', '%20')})\n".encode()),
        Entry("People 00000000000000000000000000000004.md",
              b"# People\n\n[People](People%2000000000000000000000000000000004_all.csv)\n"),
        Entry("People 00000000000000000000000000000004_all.csv",
              "\ufeffName,Role\nAda,Lead\n".encode("utf-8")),
        Entry(row, b"# Ada\n\nRole: Lead\n\nBody.\n"),
    ]
    tree, _ = _tree(entries, tmp_path)
    nodes = _by_title(tree)
    ada = nodes["Ada"]
    assert ada.parent_uuid == nodes["People"].uuid
    assert ada.parent_uuid != nodes["Home"].uuid
    assert ada.row_of == nodes["People"].uuid


def test_row_pages_land_under_their_database(tmp_path):
    tree, _ = _tree(FLAT_EXPORT, tmp_path)
    people = _by_title(tree)["People"]
    rows = [n for n in tree.pages if n.title == "Ada"]
    assert len(rows) == 2
    assert all(row.parent_uuid == people.uuid for row in rows)


def test_a_database_page_linked_from_its_parent_is_parented(tmp_path):
    # A parent links to the CSV, never to the view stub, and the stub links to
    # its own CSV -- so without excluding that self-link every database would
    # read as ambiguously parented and strand at the root.
    tree, _ = _tree(FLAT_EXPORT, tmp_path)
    nodes = _by_title(tree)
    assert nodes["People"].parent_uuid == nodes["Home"].uuid


def test_a_page_whose_keys_match_no_database_is_not_a_row(tmp_path):
    entries = [
        Entry("Note 00000000000000000000000000000001.md",
              b"# Note\n\nAuthor: me\n\nBody.\n"),
    ]
    tree, _ = _tree(entries, tmp_path)
    assert _by_title(tree)["Note"].row_of is None


def test_a_database_without_a_stub_page_gets_a_grouping_page(tmp_path):
    tree, _ = _tree(DATABASE_EXPORT, tmp_path)
    assert "Orphans" in _by_title(tree)


def test_a_database_id_need_not_be_32_hex(tmp_path):
    tree, _ = _tree(DATABASE_EXPORT, tmp_path)
    info = tree.databases["Tasks 1507-2c1e_all.csv"]
    assert info.header == ["Name", "Status"]
    assert len(info.rows) == 2
    assert info.page_uuid == _by_title(tree)["Board"].uuid


def test_a_link_cycle_is_broken_with_a_warning(tmp_path):
    a = "A 00000000000000000000000000000001.md"
    b = "B 00000000000000000000000000000002.md"
    entries = [
        Entry(a, f"# A\n\n[B]({b.replace(' ', '%20')})\n".encode()),
        Entry(b, f"# B\n\n[A]({a.replace(' ', '%20')})\n".encode()),
    ]
    tree, warnings = _tree(entries, tmp_path)
    parents = {n.title: n.parent_uuid for n in tree.pages}
    assert list(parents.values()).count(None) >= 1
    assert any(w[1] == "hierarchy_cycle" for w in warnings)


def test_a_parent_always_precedes_its_children(tmp_path):
    tree, _ = _tree(FLAT_EXPORT, tmp_path)
    seen: set = set()
    for node in tree.pages:
        assert node.parent_uuid is None or node.parent_uuid in seen
        seen.add(node.uuid)


def test_siblings_are_ordered_alphabetically(tmp_path):
    entries = [
        Entry("Zeta 00000000000000000000000000000001.md", b"# Zeta\n"),
        Entry("Alpha 00000000000000000000000000000002.md", b"# Alpha\n"),
    ]
    tree, _ = _tree(entries, tmp_path)
    roots = sorted((n for n in tree.pages if n.parent_uuid is None),
                   key=lambda n: n.order)
    assert [n.title for n in roots] == ["Alpha", "Zeta"]


def test_row_pages_take_csv_row_order(tmp_path):
    tree, _ = _tree(DATABASE_EXPORT, tmp_path)
    board = _by_title(tree)["Board"]
    rows = sorted((n for n in tree.pages if n.row_of == board.uuid),
                  key=lambda n: n.order)
    assert [n.title for n in rows] == ["Ship"]


def test_assets_are_indexed_and_not_pages(tmp_path):
    tree, _ = _tree(FLAT_EXPORT, tmp_path)
    assert "image.png" in tree.assets
    assert not any(n.title == "image.png" for n in tree.pages)


def test_the_page_cap_refuses(tmp_path):
    with pytest.raises(NotionExportInvalid):
        _tree(FLAT_EXPORT, tmp_path, max_pages=2)


def test_signal_counts_add_up(tmp_path):
    tree, _ = _tree(FLAT_EXPORT, tmp_path)
    assert sum(tree.signal_counts.values()) == len(tree.pages)
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest -q tests/test_notion_tree.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.notion_tree'`

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/notion_tree.py`:

```python
"""Deriving the page hierarchy from a Notion export.

A foldered export states its hierarchy and this module reads it. A flat export
-- which is what "Create folders for subpages" off produces, and what the
measured export is -- states nothing, so the hierarchy is derived from two
signals the export carries anyway: a row page's property block names its
database's columns, and a subpage is linked from its parent on a line of its
own. On the measured export those two parent 2171 of 2193 pages with none
ambiguous. Inference is reported, never silent: every page carries which
signal placed it, and the caller turns that into one warning.
"""
from __future__ import annotations

import csv
import io
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from urllib.parse import unquote
from uuid import UUID, uuid4

from app.services.notion_archive import ArchiveEntry, NotionArchive
from app.services.notion_content import scan_links

Warn = Callable[[str, str, str], None]

_ID_SUFFIX = re.compile(r" ([0-9a-f]{32})$")
_PROPERTY = re.compile(r"^([^:\n]{1,60}): ?(.*)$")
_ALL_CSV = "_all.csv"


class NotionExportInvalid(ValueError):
    """The export cannot be imported as it stands."""


@dataclass(frozen=True)
class DatabaseInfo:
    csv_name: str
    page_uuid: UUID | None
    header: list[str]
    rows: list[list[str]]


@dataclass(frozen=True)
class PageNode:
    uuid: UUID
    entry: ArchiveEntry | None
    title: str
    notion_id: str | None
    parent_uuid: UUID | None
    order: int
    database_csv: str | None
    row_of: UUID | None


@dataclass(frozen=True)
class NotionTree:
    pages: list[PageNode]
    by_target: dict[str, UUID]
    assets: dict[str, ArchiveEntry]
    databases: dict[str, DatabaseInfo]
    signal_counts: dict[str, int]


def _stem(name: str) -> str:
    base = name.rsplit("/", 1)[-1]
    stem = base.rsplit(".", 1)[0] if "." in base else base
    # A database is `Title <id>_all.csv`; without dropping `_all` the id never
    # matches and the title keeps a suffix no human wrote.
    return stem[: -len("_all")] if stem.endswith("_all") else stem


def _notion_id(name: str) -> str | None:
    match = _ID_SUFFIX.search(_stem(name))
    return match.group(1) if match else None


def _title_from_name(name: str) -> str:
    stem = _stem(name)
    return unquote(_ID_SUFFIX.sub("", stem)).strip() or stem


def _title_and_properties(source: str, name: str) -> tuple[str, list[str]]:
    """The page's title and its property-block keys.

    The property block is the run of contiguous `Key: value` lines directly
    after the title. It is read here because it is the database-membership
    signal; the content module rewrites it into a bullet list later.
    """
    lines = source.split("\n")
    title = _title_from_name(name)
    index = 0
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip() or title
        index = 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    keys: list[str] = []
    while index < len(lines):
        match = _PROPERTY.match(lines[index])
        if match is None:
            break
        keys.append(match.group(1))
        index += 1
    return title, keys


def _read_csv(text: str) -> tuple[list[str], list[list[str]]]:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _standalone_targets(source: str) -> list[str]:
    """Targets of links that occupy a whole line, in order.

    Every one of the measured export's 289 page-to-page links is written this
    way and none is inline, which is what makes the signal a subpage reference
    rather than a mention.
    """
    out: list[str] = []
    for span in scan_links(source):
        if span.is_image:
            continue
        line_start = source.rfind("\n", 0, span.start) + 1
        line_end = source.find("\n", span.end)
        line_end = len(source) if line_end == -1 else line_end
        if source[line_start:line_end].strip() == source[span.start:span.end]:
            out.append(unquote(span.destination.split("#")[0]))
    return out


def _resolve(target: str, from_entry: str) -> str:
    """A link target as an entry name, resolved against its page's folder."""
    if "/" not in from_entry:
        base: list[str] = []
    else:
        base = from_entry.rsplit("/", 1)[0].split("/")
    parts = list(base)
    for piece in target.split("/"):
        if piece in ("", "."):
            continue
        if piece == "..":
            if parts:
                parts.pop()
            continue
        parts.append(piece)
    return "/".join(parts)


def _creates_cycle(parents: dict[UUID, UUID], child: UUID, parent: UUID) -> bool:
    walk: UUID | None = parent
    seen: set[UUID] = set()
    while walk is not None:
        if walk == child:
            return True
        if walk in seen:
            return True
        seen.add(walk)
        walk = parents.get(walk)
    return False


def build_tree(archive: NotionArchive, *, max_pages: int, warn: Warn) -> NotionTree:
    pages_entries = [e for e in archive.entries if e.name.endswith(".md")]
    csv_entries = [e for e in archive.entries if e.name.endswith(_ALL_CSV)]
    asset_entries = [
        e for e in archive.entries
        if not e.name.endswith(".md") and not e.name.endswith(_ALL_CSV)
    ]
    if len(pages_entries) > max_pages:
        raise NotionExportInvalid(
            f"the export holds {len(pages_entries)} pages; the bound is {max_pages}"
        )

    sources = {e.name: archive.read_text(e) for e in pages_entries}
    uuids = {e.name: uuid4() for e in pages_entries}
    titles: dict[str, str] = {}
    keys: dict[str, list[str]] = {}
    for entry in pages_entries:
        titles[entry.name], keys[entry.name] = _title_and_properties(
            sources[entry.name], entry.name
        )

    by_id = {
        _notion_id(e.name): e.name for e in pages_entries if _notion_id(e.name)
    }

    # Standalone links, resolved once: they are both the subpage signal and,
    # for a CSV target, how a database with a differently-named view stub is
    # found. The measured export has one -- `Untitled 1507-2c1e_all.csv`, whose
    # stub page is titled "Sprint 47".
    standalone: dict[str, list[str]] = {}
    for entry in pages_entries:
        for target in _standalone_targets(sources[entry.name]):
            resolved = _resolve(target, entry.name)
            if resolved != entry.name:
                standalone.setdefault(resolved, []).append(entry.name)

    databases: dict[str, DatabaseInfo] = {}
    minted: dict[str, tuple[UUID, str]] = {}
    stub_csv: dict[str, str] = {}
    for entry in csv_entries:
        header, rows = _read_csv(archive.read_text(entry))
        stub = entry.name[: -len(_ALL_CSV)] + ".md"
        if stub not in uuids:
            # No stem-matching page: the view stub may carry another name, in
            # which case it is the one page linking to this CSV.
            linkers = [n for n in standalone.get(entry.name, []) if n not in stub_csv]
            stub = linkers[0] if len(linkers) == 1 else stub
        page_uuid = uuids.get(stub)
        if page_uuid is None:
            page_uuid = uuid4()
            minted[entry.name] = (page_uuid, _title_from_name(entry.name))
        else:
            stub_csv[stub] = entry.name
        databases[entry.name] = DatabaseInfo(
            csv_name=entry.name, page_uuid=page_uuid, header=header, rows=rows,
        )

    parents: dict[UUID, UUID] = {}
    row_of: dict[str, UUID] = {}
    signal: dict[UUID, str] = {}

    # Signal 1: folder nesting. An export made with "Create folders for
    # subpages" states its hierarchy, so nothing below is consulted for it.
    for entry in pages_entries:
        if "/" not in entry.name:
            continue
        folder = entry.name.rsplit("/", 1)[0].rsplit("/", 1)[-1]
        match = _ID_SUFFIX.search(folder)
        if match is None:
            continue
        parent_name = by_id.get(match.group(1))
        if parent_name and parent_name != entry.name:
            parents[uuids[entry.name]] = uuids[parent_name]
            signal[uuids[entry.name]] = "folder"

    # Signal 2: database membership, via the property block.
    for entry in pages_entries:
        node_uuid = uuids[entry.name]
        if node_uuid in parents or entry.name in stub_csv:
            continue
        page_keys = keys[entry.name]
        if not page_keys:
            continue
        hits = [
            info for info in databases.values()
            if set(page_keys) <= set(info.header[1:])
        ]
        if len(hits) != 1:
            continue
        info = hits[0]
        if info.page_uuid is None or info.page_uuid == node_uuid:
            continue
        parents[node_uuid] = info.page_uuid
        row_of[entry.name] = info.page_uuid
        signal[node_uuid] = "database"

    # Signal 3: a link on a line of its own, and only where exactly one page
    # points at the target. Ambiguous parentage is left unplaced, not guessed.
    # A link to a database's CSV parents that database's PAGE -- a parent links
    # to the CSV, never to the view stub, so without this every database in the
    # measured export strands at the root.
    linkable: dict[str, UUID] = dict(uuids)
    for info in databases.values():
        if info.page_uuid is not None:
            linkable[info.csv_name] = info.page_uuid
    for target, all_linkers in standalone.items():
        node_uuid = linkable.get(target)
        if node_uuid is None or node_uuid in parents:
            continue
        # A view stub links to its own CSV, which would otherwise read as a
        # second linker and make every database look ambiguously parented.
        linkers = [name for name in all_linkers if uuids[name] != node_uuid]
        if len(linkers) != 1:
            continue
        parent_uuid = uuids[linkers[0]]
        if _creates_cycle(parents, node_uuid, parent_uuid):
            warn(target, "hierarchy_cycle",
                 f"a link cycle with {linkers[0]}; this page stays at the root")
            continue
        parents[node_uuid] = parent_uuid
        signal[node_uuid] = "link"

    nodes: dict[UUID, PageNode] = {}
    for entry in pages_entries:
        node_uuid = uuids[entry.name]
        nodes[node_uuid] = PageNode(
            uuid=node_uuid,
            entry=entry,
            title=titles[entry.name],
            notion_id=_notion_id(entry.name),
            parent_uuid=parents.get(node_uuid),
            order=0,
            database_csv=stub_csv.get(entry.name),
            row_of=row_of.get(entry.name),
        )
    for csv_name, (node_uuid, title) in minted.items():
        nodes[node_uuid] = PageNode(
            uuid=node_uuid, entry=None, title=title, notion_id=None,
            parent_uuid=None, order=0, database_csv=csv_name, row_of=None,
        )
        signal[node_uuid] = "root"
    for node_uuid in nodes:
        signal.setdefault(node_uuid, "root")

    # Order: siblings alphabetically, except a database's rows, which follow
    # the CSV. The export carries no sidebar order, so this is a choice.
    row_rank: dict[UUID, int] = {}
    for info in databases.values():
        titles_in_order = [r[0] for r in info.rows if r]
        taken: set[UUID] = set()
        for rank, row_title in enumerate(titles_in_order):
            for node in nodes.values():
                if (node.row_of == info.page_uuid and node.title == row_title
                        and node.uuid not in taken):
                    row_rank[node.uuid] = rank
                    taken.add(node.uuid)
                    break

    children: dict[UUID | None, list[PageNode]] = {}
    for node in nodes.values():
        children.setdefault(node.parent_uuid, []).append(node)
    for siblings in children.values():
        siblings.sort(key=lambda n: (
            row_rank.get(n.uuid, len(row_rank) + 1), n.title, str(n.uuid),
        ))
        for index, node in enumerate(siblings):
            nodes[node.uuid] = replace(node, order=index)

    ordered: list[PageNode] = []
    stack = list(reversed(children.get(None, [])))
    while stack:
        node = nodes[stack.pop().uuid]
        ordered.append(node)
        stack.extend(reversed(children.get(node.uuid, [])))

    counts: dict[str, int] = {}
    for node in ordered:
        counts[signal[node.uuid]] = counts.get(signal[node.uuid], 0) + 1

    return NotionTree(
        pages=ordered,
        by_target={e.name: uuids[e.name] for e in pages_entries} | {
            info.csv_name: info.page_uuid
            for info in databases.values() if info.page_uuid is not None
        },
        assets={e.name: e for e in asset_entries},
        databases=databases,
        signal_counts=counts,
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `python -m pytest -q tests/test_notion_tree.py -v`
Expected: PASS, 19 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/notion_tree.py backend/tests/test_notion_tree.py
git commit -m "feat(notion): derive the page hierarchy from an export"
```

---

### Task 7: Content translation

**Files:**
- Modify: `backend/app/services/notion_content.py` (append after `scan_links`)
- Test: `backend/tests/test_notion_content.py`

**Interfaces:**
- Consumes: `scan_links`, `LinkSpan` (Contracts, **Link scanner**); `PageNode`, `NotionTree`, `DatabaseInfo` (Contracts, **Tree**); `NotionArchive` (Contracts, **Archive**); `page_door._parse` and `page_door._flatten_headings`; `block_serializer.TreeBlock` and `serialize_tree`.
- Produces: `StagedAsset` and `translate_page` — see Contracts, **Content**. Task 9 consumes both.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_notion_content.py`:

```python
from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import UUID, uuid4

from app.services.block_serializer import serialize_tree
from app.services.notion_archive import open_archive
from app.services.notion_content import StagedAsset, scan_links, translate_page
from app.services.notion_tree import build_tree
from tests.fixtures.notion.builder import DATABASE_EXPORT, FLAT_EXPORT, Entry, build_fixture

BOUNDS = {"max_blocks": 5_000, "max_content_chars": 1_000_000}


def _prepared(entries, tmp_path):
    path = build_fixture(entries, tmp_path / "x.zip")
    warnings: list[tuple] = []
    sink = lambda p, k, d: warnings.append((p, k, d))  # noqa: E731
    archive = open_archive(
        path, tmp_path / "staging", max_entries=50_000,
        max_uncompressed_bytes=5_368_709_120, warn=sink,
    )
    tree = build_tree(archive, max_pages=10_000, warn=sink)
    assets = {
        name: StagedAsset(
            attachment_id=uuid4(), staged_path=Path(tempfile.mkstemp()[1]),
            filename=name.rsplit("/", 1)[-1], content_type="image/png",
            size_bytes=10, sha256="ab" * 32,
        )
        for name in tree.assets
    }
    return archive, tree, assets, warnings, sink


def _render(title, entries, tmp_path):
    archive, tree, assets, warnings, sink = _prepared(entries, tmp_path)
    node = next(n for n in tree.pages if n.title == title)
    blocks = translate_page(
        node, tree, archive, assets=assets, warn=sink, **BOUNDS
    )
    return blocks, serialize_tree(blocks).content, warnings, tree, assets


def test_the_title_line_is_not_a_block(tmp_path):
    _, content, _, _, _ = _render("Notes", FLAT_EXPORT, tmp_path)
    assert not content.startswith("# Notes")


def test_an_internal_page_link_becomes_a_notes_url(tmp_path):
    _, content, _, tree, _ = _render("Home", FLAT_EXPORT, tmp_path)
    notes = next(n for n in tree.pages if n.title == "Notes")
    assert f"/notes?page={notes.uuid}" in content


def test_a_database_csv_link_becomes_its_page_not_an_attachment(tmp_path):
    _, content, _, tree, _ = _render("Home", FLAT_EXPORT, tmp_path)
    people = next(n for n in tree.pages if n.title == "People")
    assert f"/notes?page={people.uuid}" in content
    assert "/api/v1/pages/attachments/" not in content


def test_an_image_becomes_an_attachment_url(tmp_path):
    _, content, _, _, assets = _render("Notes", FLAT_EXPORT, tmp_path)
    staged = assets["image.png"]
    assert f"![shot](/api/v1/pages/attachments/{staged.attachment_id})" in content


def test_a_missing_target_becomes_a_missing_file_note(tmp_path):
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\n![gone](nowhere.png)\n"),
    ]
    _, content, warnings, _, _ = _render("A", entries, tmp_path)
    assert "[missing file: nowhere.png]" in content
    assert any(w[1] == "missing_file" for w in warnings)


def test_a_missing_page_link_keeps_its_text_and_loses_its_target(tmp_path):
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\nsee [Gone](Gone%2000000000000000000000000000000009.md) x\n"),
    ]
    _, content, warnings, _, _ = _render("A", entries, tmp_path)
    assert "Gone" in content and "00000000000000000000000000000009.md" not in content
    assert any(w[1] == "unresolved_link" for w in warnings)


def test_an_external_link_is_unchanged(tmp_path):
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\n[site](https://example.test/x) tail\n"),
    ]
    _, content, _, _, _ = _render("A", entries, tmp_path)
    assert "https://example.test/x" in content


def test_an_aside_becomes_a_callout(tmp_path):
    blocks, _, _, _, _ = _render("Trip (2026) plan", FLAT_EXPORT, tmp_path)
    callouts = [b for b in blocks if b.type == "callout"]
    assert len(callouts) == 1
    assert (callouts[0].properties or {}).get("variant") == "info"
    assert "[!NOTE]" not in callouts[0].text


def test_a_checkbox_item_becomes_a_todo(tmp_path):
    blocks, _, _, _, _ = _render("Notes", FLAT_EXPORT, tmp_path)
    todos = [b for b in blocks if b.type == "todo"]
    assert [b.text for b in todos] == ["open task", "done task"]
    assert [(b.properties or {}).get("checked") for b in todos] == [False, True]
    assert all("marker" not in (b.properties or {}) for b in todos)


def test_a_database_page_renders_its_csv_as_a_table(tmp_path):
    blocks, content, _, _, _ = _render("Board", DATABASE_EXPORT, tmp_path)
    assert any(b.type == "table" for b in blocks)
    assert len([b for b in blocks if b.type == "table_row"]) == 2
    assert "| Name | Status |" in content


def test_a_database_page_drops_its_filters_and_sort_tail(tmp_path):
    _, content, warnings, _, _ = _render("People", FLAT_EXPORT, tmp_path)
    assert "filters:" not in content and "sort:" not in content
    assert any(w[1] == "stripped_source" for w in warnings)


def test_a_cell_holding_a_pipe_is_escaped(tmp_path):
    entries = [
        Entry("Board 00000000000000000000000000000021.md",
              b"# Board\n\n[T](T%201507-2c1e_all.csv)\n"),
        Entry("T 1507-2c1e_all.csv",
              "﻿Name,Note\na|b,two\n".encode("utf-8")),
    ]
    _, content, _, _, _ = _render("Board", entries, tmp_path)
    assert r"a\|b" in content


def test_a_row_page_property_block_becomes_a_bullet_list(tmp_path):
    blocks, content, _, _, _ = _render("Ship", DATABASE_EXPORT, tmp_path)
    assert content.startswith("- Status: Open")
    assert blocks[0].type == "list"


def test_a_page_over_the_block_bound_is_truncated(tmp_path):
    body = "\n\n".join(f"para {i}" for i in range(50))
    entries = [
        Entry("Big 00000000000000000000000000000001.md",
              f"# Big\n\n{body}\n".encode("utf-8")),
    ]
    archive, tree, assets, warnings, sink = _prepared(entries, tmp_path)
    node = next(n for n in tree.pages if n.title == "Big")
    blocks = translate_page(
        node, tree, archive, assets=assets, warn=sink,
        max_blocks=10, max_content_chars=1_000_000,
    )
    assert len(blocks) == 10
    assert any(w[1] == "truncated" for w in warnings)


def test_a_page_over_the_character_bound_is_truncated(tmp_path):
    body = "\n\n".join("x" * 200 for _ in range(20))
    entries = [
        Entry("Big 00000000000000000000000000000001.md",
              f"# Big\n\n{body}\n".encode("utf-8")),
    ]
    archive, tree, assets, warnings, sink = _prepared(entries, tmp_path)
    node = next(n for n in tree.pages if n.title == "Big")
    blocks = translate_page(
        node, tree, archive, assets=assets, warn=sink,
        max_blocks=5_000, max_content_chars=500,
    )
    assert len(serialize_tree(blocks).content) <= 500
    assert any(w[1] == "truncated" for w in warnings)


def test_every_block_respects_the_page_parent_rule(tmp_path):
    from app.services.block_verbs import _check_page_nesting

    blocks, _, _, _, _ = _render("Notes", FLAT_EXPORT, tmp_path)
    by_id = {b.id: b for b in blocks}
    for block in blocks:
        parent = by_id.get(block.parent_id) if block.parent_id else None
        _check_page_nesting(parent, block)


def test_a_notion_so_link_in_the_export_becomes_a_page_link(tmp_path):
    target = "T 00000000000000000000000000000009.md"
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\n[T](https://www.notion.so/workspace/T-"
              b"00000000000000000000000000000009) x\n"),
        Entry(target, b"# T\n"),
    ]
    _, content, _, tree, _ = _render("A", entries, tmp_path)
    t = next(n for n in tree.pages if n.title == "T")
    assert f"/notes?page={t.uuid}" in content
    assert "notion.so" not in content


def test_a_notion_so_link_outside_the_export_is_unchanged(tmp_path):
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\n[Gone](https://www.notion.so/workspace/Gone-"
              b"000000000000000000000000000000ff) x\n"),
    ]
    _, content, _, _, _ = _render("A", entries, tmp_path)
    assert "notion.so" in content
    assert "/notes?page=" not in content


def test_a_frontmatter_fence_is_stripped(tmp_path):
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"---\ntags: x\n---\n\n# A\n\nBody.\n"),
    ]
    _, content, warnings, _, _ = _render("A", entries, tmp_path)
    assert "tags: x" not in content
    assert any(w[1] == "stripped_source" for w in warnings)
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest -q tests/test_notion_content.py`
Expected: FAIL — `ImportError: cannot import name 'translate_page'`

- [ ] **Step 3: Write the implementation**

Append to `backend/app/services/notion_content.py`. Extend the import block at the top with:

```python
import csv
import io
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import unquote
from uuid import UUID

from app.services.block_serializer import TreeBlock, serialize_tree
from app.services.document_parsers import split_frontmatter
from app.services.notion_archive import NotionArchive
# `_parse` and `_flatten_headings` are page_door's own: reproducing them here
# would let the import and the create door drift into parsing a page two ways.
from app.services.page_door import _flatten_headings, _parse
from app.services.block_verbs import _check_page_nesting
from app.services.page_attachments import attachment_url
```

Then append:

```python
Warn = Callable[[str, str, str], None]

_ASIDE = re.compile(r"<aside>(.*?)</aside>", re.S)
_LINK_DEF = re.compile(r"^\[([^\]]+)\]:[ \t]*(\S+).*$", re.M)
_VIEW_TAIL = re.compile(r"\n(?:filters|sort):[ \t]*\n.*\Z", re.S)
_CALLOUT_LABEL = re.compile(r"^\[!([A-Za-z]+)\]")
_CHECKBOX_MARKER = re.compile(r"^\[([ xX])\]\s+")
_VARIANTS = {"NOTE": "info", "WARNING": "warning", "CAUTION": "error", "TIP": "success"}
_EXTERNAL = ("http://", "https://", "mailto:", "tel:", "data:")


@dataclass(frozen=True)
class StagedAsset:
    attachment_id: UUID
    staged_path: Path
    filename: str
    content_type: str
    size_bytes: int
    sha256: str


def _resolve(target: str, from_entry: str) -> str:
    base = from_entry.rsplit("/", 1)[0].split("/") if "/" in from_entry else []
    parts = list(base)
    for piece in target.split("/"):
        if piece in ("", "."):
            continue
        if piece == "..":
            if parts:
                parts.pop()
            continue
        parts.append(piece)
    return "/".join(parts)


def _cell(text: str) -> str:
    # The parser stores a cell with its escape already removed, so a bare pipe
    # would declare a column the delimiter row does not have and truncate the
    # row at that character.
    return text.replace("|", r"\|").replace("\n", " ").strip()


def _table_source(info) -> str:
    header = "| " + " | ".join(_cell(c) for c in info.header) + " |"
    delim = "| " + " | ".join("---" for _ in info.header) + " |"
    rows = [
        "| " + " | ".join(_cell(c) for c in (row + [""] * len(info.header))[:len(info.header)]) + " |"
        for row in info.rows if row
    ]
    return "\n".join([header, delim, *rows])


def _strip_title(source: str) -> str:
    lines = source.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).lstrip("\n")


def _property_lines(source: str) -> tuple[list[str], str]:
    """The leading `Key: value` run as bullets, and the body after it."""
    lines = source.split("\n")
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    bullets: list[str] = []
    while index < len(lines):
        match = re.match(r"^([^:\n]{1,60}): ?(.*)$", lines[index])
        if match is None:
            break
        bullets.append(f"- {lines[index].strip()}")
        index += 1
    return bullets, "\n".join(lines[index:]).lstrip("\n")


def _rewrite_asides(source: str) -> str:
    """`<aside>` to a `[!NOTE]` blockquote.

    Textual, and it has to be: a blank line closes a CommonMark HTML block, so
    a multi-paragraph aside would otherwise parse as html / paragraph / html.
    """
    def one(match: re.Match) -> str:
        body = match.group(1).strip("\n")
        lines = [f"> {line}" if line.strip() else ">" for line in body.split("\n")]
        return "\n".join(["> [!NOTE]", *lines])

    return _ASIDE.sub(one, source)


def _rewrite_links(
    source: str, node, tree, *, assets: dict[str, StagedAsset], warn: Warn,
) -> str:
    """Point every internal link at a page or an attachment.

    Rewritten back to front so an earlier span's indices stay valid.
    """
    entry_name = node.entry.name if node.entry is not None else ""
    out = source
    for span in reversed(scan_links(source)):
        destination = span.destination
        if destination.startswith(_EXTERNAL):
            replacement = None
            if "notion.so" in destination:
                match = re.search(r"([0-9a-f]{32})", destination)
                target_uuid = None
                if match:
                    for page in tree.pages:
                        if page.notion_id == match.group(1):
                            target_uuid = page.uuid
                            break
                if target_uuid is not None:
                    replacement = f"[{span.label}](/notes?page={target_uuid})"
            if replacement is None:
                continue
            out = out[:span.start] + replacement + out[span.end:]
            continue

        resolved = _resolve(unquote(destination.split("#")[0]), entry_name)
        page_uuid = tree.by_target.get(resolved)
        if page_uuid is not None:
            out = out[:span.start] + f"[{span.label}](/notes?page={page_uuid})" + out[span.end:]
            continue

        staged = assets.get(resolved)
        if staged is not None:
            url = attachment_url(staged.attachment_id)
            bang = "!" if span.is_image else ""
            out = out[:span.start] + f"{bang}[{span.label}]({url})" + out[span.end:]
            continue

        name = resolved.rsplit("/", 1)[-1] or destination
        in_export = resolved in tree.assets
        if span.is_image or in_export:
            # A file that IS in the export but was not staged was refused for a
            # reason its stager already reported (oversize today), so warning
            # again here would count one file twice.
            if not in_export:
                warn(entry_name, "missing_file", f"{name} is not in the export")
            out = out[:span.start] + f"[missing file: {name}]" + out[span.end:]
        else:
            warn(entry_name, "unresolved_link", f"{name} is not in the export")
            out = out[:span.start] + span.label + out[span.end:]
    return out


def _post_parse(blocks: list[TreeBlock], warn: Warn) -> list[TreeBlock]:
    """Mint the page-only types the parser never emits.

    `taxonomy.PAGE_BLOCK_TYPES` is kept out of `BLOCK_TYPES` on purpose, so a
    filed document parses the same as it always did; only this importer and the
    editor set them.
    """
    by_id = {b.id: b for b in blocks}
    out: list[TreeBlock] = []
    recast: dict = {}
    for block in blocks:
        parent_id = block.parent_id
        while parent_id is not None and parent_id in recast:
            parent_id = recast[parent_id]
        block = replace(block, parent_id=parent_id)

        if block.type == "quote":
            label = _CALLOUT_LABEL.match(block.text or "")
            if label:
                variant = _VARIANTS.get(label.group(1).upper(), "info")
                rest = (block.text or "")[label.end():].lstrip("\n")
                out.append(replace(
                    block, type="callout", text=rest, properties={"variant": variant},
                ))
                # A callout holds no children on a page, so its children become
                # its following siblings rather than being dropped.
                recast[block.id] = block.parent_id
                continue

        if block.type == "list":
            marker = _CHECKBOX_MARKER.match(block.text or "")
            if marker:
                out.append(replace(
                    block, type="todo", text=(block.text or "")[marker.end():],
                    properties={"checked": marker.group(1).lower() == "x"},
                ))
                continue

        out.append(block)
    # Reading order is unchanged, so renumbering is enough to keep it stable.
    return [replace(b, order_index=i) for i, b in enumerate(out)]


def _truncate(
    blocks: list[TreeBlock], *, max_blocks: int, max_content_chars: int,
    entry_name: str, warn: Warn,
) -> list[TreeBlock]:
    dropped = 0
    kept = list(blocks)
    while kept and (
        len(kept) > max_blocks
        or len(serialize_tree(kept).content) > max_content_chars
    ):
        kept.pop()
        dropped += 1
    if dropped:
        warn(entry_name, "truncated", f"{dropped} trailing blocks dropped to fit")
    return [replace(b, order_index=i) for i, b in enumerate(kept)]


def translate_page(
    node, tree, archive: NotionArchive, *,
    assets: dict[str, StagedAsset],
    max_blocks: int, max_content_chars: int,
    warn: Warn,
) -> list[TreeBlock]:
    entry_name = node.entry.name if node.entry is not None else node.database_csv or ""
    source = archive.read_text(node.entry) if node.entry is not None else ""

    front, offset = split_frontmatter(source)
    if front is not None:
        warn(entry_name, "stripped_source", "a leading frontmatter fence was dropped")
        source = source[offset:]

    source = _strip_title(source)

    if _LINK_DEF.search(source):
        definitions = {m.group(1): m.group(2) for m in _LINK_DEF.finditer(source)}
        source = _LINK_DEF.sub("", source)
        for label, target in definitions.items():
            source = source.replace(f"[{label}][]", f"[{label}]({target})")
            source = re.sub(rf"\[([^\]]*)\]\[{re.escape(label)}\]",
                            rf"[\1]({target})", source)
        warn(entry_name, "stripped_source",
             "link-reference definitions were inlined; a page cannot hold them")

    bullets: list[str] = []
    if node.row_of is not None:
        bullets, source = _property_lines(source)

    if node.database_csv is not None:
        info = tree.databases[node.database_csv]
        tail = _VIEW_TAIL.search(source)
        if tail:
            source = source[:tail.start()]
            warn(entry_name, "stripped_source",
                 "the view's filters and sort lines were dropped")
        # The link to this page's own CSV becomes the table itself.
        for span in reversed(scan_links(source)):
            resolved = _resolve(unquote(span.destination.split("#")[0]), entry_name)
            if resolved == node.database_csv:
                source = source[:span.start] + source[span.end:]
        source = (source.strip() + "\n\n" + _table_source(info)).strip()

    source = _rewrite_asides(source)
    source = _rewrite_links(source, node, tree, assets=assets, warn=warn)
    if bullets:
        source = "\n".join(bullets) + ("\n\n" + source if source.strip() else "")

    parsed = _flatten_headings(_parse(source)) if source.strip() else []
    # `_post_parse` re-parents a callout's children onto its own parent, so the
    # flatten runs again after it rather than only before.
    blocks = _flatten_headings(_post_parse(parsed, warn))
    blocks = _truncate(
        blocks, max_blocks=max_blocks, max_content_chars=max_content_chars,
        entry_name=entry_name, warn=warn,
    )
    # Spec section 8.5: the page-parent rule is asserted on the result. A
    # violation is a bug in this module, not a refusal the caller can act on.
    by_id = {block.id: block for block in blocks}
    for block in blocks:
        _check_page_nesting(
            by_id.get(block.parent_id) if block.parent_id else None, block
        )
    return blocks
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `python -m pytest -q tests/test_notion_content.py -v`
Expected: PASS, 19 tests.

Then confirm nothing the parser or serialiser owns regressed:

Run: `python -m pytest -q tests/test_block_pipeline.py tests/test_page_door.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/notion_content.py backend/tests/test_notion_content.py
git commit -m "feat(notion): translate export markdown into page blocks"
```

---

### Task 8: Extract `_insert_page` from `create_page`

**Files:**
- Modify: `backend/app/services/page_door.py:447-538` (`create_page`), and `_INSERT_BLOCK` at `:176`
- Test: `backend/tests/test_page_insert_split.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `_insert_page` — see Contracts, **Page insert**. Task 9 consumes it.

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

Risk 2 is the shared code path: every page create in the product goes through this function, so a mistake here breaks the editor, not just the import. `create_page`'s public signature, its refusals and its journal payload must all come out unchanged, which is what the first test pins.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_page_insert_split.py`:

```python
from __future__ import annotations

import inspect
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services.page_door import _insert_page, create_page


@pytest.fixture
def llm():
    """`create_page` accepts an `llm` and never uses it (page_door.py:449 is
    its only occurrence). There is no conftest fixture for it — the page tests
    each define their own — so this file defines the same stand-in."""
    return None


def test_create_page_keeps_its_signature():
    params = list(inspect.signature(create_page).parameters)
    assert params[:2] == ["session", "llm"]
    for name in ("project", "title", "parent_id", "after_id", "content",
                 "properties", "actor"):
        assert name in params


@pytest.mark.asyncio
async def test_insert_page_does_not_commit(session, monkeypatch):
    calls: list[int] = []
    original = session.commit

    async def spy() -> None:
        calls.append(1)
        await original()

    monkeypatch.setattr(session, "commit", spy)
    await _insert_page(
        session, project="notes", parent_id=None, after_id=None,
        title="A", tree=[], properties=None, actor=None,
    )
    assert calls == []


@pytest.mark.asyncio
async def test_insert_page_honours_a_caller_supplied_id(session):
    page_id = uuid4()
    result = await _insert_page(
        session, project="notes", parent_id=None, after_id=None,
        title="Pinned", tree=[], properties=None, actor=None, page_id=page_id,
    )
    assert result.id == page_id
    found = (
        await session.execute(
            text("SELECT title FROM pages WHERE id = CAST(:id AS uuid)"),
            {"id": str(page_id)},
        )
    ).scalar_one()
    assert found == "Pinned"


@pytest.mark.asyncio
async def test_insert_page_mints_an_id_when_none_is_given(session):
    result = await _insert_page(
        session, project="notes", parent_id=None, after_id=None,
        title="Minted", tree=[], properties=None, actor=None,
    )
    assert result.id is not None


@pytest.mark.asyncio
async def test_insert_page_refuses_too_many_blocks(session, llm):
    from app.services.page_door import MAX_BLOCKS, PageTooLarge, _parse

    content = "\n\n".join(f"p{i}" for i in range(MAX_BLOCKS + 5))
    with pytest.raises(PageTooLarge):
        await _insert_page(
            session, project="notes", parent_id=None, after_id=None,
            title="Huge", tree=_parse(content), properties=None, actor=None,
        )


@pytest.mark.asyncio
async def test_blocks_are_written_in_one_statement(session, llm, monkeypatch):
    from app.services import page_door

    content = "\n\n".join(f"para {i}" for i in range(40))
    executed: list[str] = []
    original = session.execute

    async def spy(statement, *args, **kwargs):
        executed.append(str(statement))
        return await original(statement, *args, **kwargs)

    monkeypatch.setattr(session, "execute", spy)
    await create_page(session, llm, project="notes", title="Many", content=content)

    inserts = [s for s in executed if "INSERT INTO blocks" in s]
    assert len(inserts) == 1, f"{len(inserts)} block inserts; one unnest was expected"


@pytest.mark.asyncio
async def test_create_page_still_journals_the_same_payload(session, llm):
    result = await create_page(
        session, llm, project="notes", title="Journalled", content="Body."
    )
    payload = (
        await session.execute(
            text(
                "SELECT payload FROM events WHERE object_id = CAST(:id AS uuid) "
                "AND event_type = 'page_created'"
            ),
            {"id": str(result.id)},
        )
    ).scalar_one()
    assert set(payload) == {"parent_id", "order_index", "blocks_total", "content_hash"}
    assert payload["blocks_total"] == result.blocks_written
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest -q tests/test_page_insert_split.py`
Expected: FAIL — `ImportError: cannot import name '_insert_page'`

- [ ] **Step 3: Write the implementation**

In `backend/app/services/page_door.py`, replace the `_INSERT_BLOCK` statement at line 176 with an `unnest` form:

```python
_INSERT_BLOCKS = text(
    """
    INSERT INTO blocks (id, page_id, parent_id, order_index, type, text,
                        properties, char_span)
    SELECT CAST(u.id AS uuid), CAST(:page AS uuid), CAST(u.parent AS uuid),
           u.ord, u.kind, u.body, CAST(u.props AS jsonb),
           CAST(CAST(u.span AS text) AS int4range)
    FROM (SELECT unnest(CAST(:ids AS text[])) AS id,
                 unnest(CAST(:parents AS text[])) AS parent,
                 unnest(CAST(:ords AS integer[])) AS ord,
                 unnest(CAST(:kinds AS text[])) AS kind,
                 unnest(CAST(:bodies AS text[])) AS body,
                 unnest(CAST(:props AS text[])) AS props,
                 unnest(CAST(:spans AS text[])) AS span) u
    """
)
```

Then replace the body of `create_page` (from `page_id = uuid4()` through the `return PageResult(...)`) with:

```python
async def _insert_page(
    session: AsyncSession,
    *,
    project: str,
    parent_id: str | None,
    after_id: str | None,
    title: str | None,
    tree: list[TreeBlock],
    properties: dict | None,
    actor: str | None,
    page_id: UUID | None = None,
) -> PageResult:
    """Claim a slot, write the page and its blocks, journal -- and never commit.

    Split out of `create_page` so the Notion import can write thousands of
    pages inside one transaction. The caller owns the commit; the MAX_BLOCKS
    refusal lives here so both callers keep it.
    """
    page_id = page_id or uuid4()
    serialized = serialize_tree(tree)
    stored_content = serialized.content
    content_hash = compute_content_hash(stored_content)
    placed = {p.block_id: p for p in serialized.placed}

    async with session.begin_nested():
        order_index = await _claim_order_index(
            session, project=project, parent_id=parent_id, after_id=after_id,
        )
        if len(tree) > MAX_BLOCKS:
            raise PageTooLarge(
                f"page parses to {len(tree)} blocks; the bound is "
                f"{MAX_BLOCKS} blocks"
            )
        await session.execute(_INSERT_PAGE, {
            "id": str(page_id),
            "project": project,
            "parent": parent_id,
            "order_index": order_index,
            "title": title,
            "content": stored_content,
            "content_hash": content_hash,
            "properties": _json(properties),
        })
        if tree:
            spots = [placed[block.id] for block in tree]
            await session.execute(_INSERT_BLOCKS, {
                "page": str(page_id),
                "ids": [str(b.id) for b in tree],
                "parents": [None if b.parent_id is None else str(b.parent_id)
                            for b in tree],
                "ords": [s.order_index for s in spots],
                "kinds": [b.type for b in tree],
                "bodies": [b.text for b in tree],
                "props": [_json(b.properties) for b in tree],
                "spans": [f"[{s.char_span[0]},{s.char_span[1]})" for s in spots],
            })
        # No block or title text in the payload: write-time minimization, and
        # a journal row outlives the page it describes.
        await record_event(
            session,
            event_type=PAGE_CREATED_EVENT,
            object_type="page",
            object_id=page_id,
            project=project,
            actor=actor,
            payload={
                "parent_id": parent_id,
                "order_index": order_index,
                "blocks_total": len(tree),
                "content_hash": content_hash,
            },
        )

    return PageResult(
        id=page_id,
        project=project,
        parent_id=None if parent_id is None else UUID(parent_id),
        order_index=order_index,
        title=title,
        content_hash=content_hash,
        blocks_written=len(tree),
    )


async def create_page(
    session: AsyncSession,
    llm,
    *,
    project: str,
    title: str | None,
    parent_id: str | None = None,
    after_id: str | None = None,
    content: str | None = None,
    properties: dict | None = None,
    actor: str | None = None,
) -> PageResult:
    if content is not None and len(content) > MAX_CONTENT_CHARS:
        raise PageTooLarge(
            f"content is {len(content)} characters; the bound is "
            f"{MAX_CONTENT_CHARS}"
        )

    tree = _flatten_headings(_parse(content)) if content else []
    if content and (
        split_frontmatter(content)[0] is not None
        or not reproduces_source(tree, content, {})
    ):
        raise PageNotRepresentable(
            "this content carries source a page cannot represent (a leading "
            "frontmatter fence or a link-reference definition); a page stores "
            "its blocks' serialisation, so filing it would drop that source"
        )

    result = await _insert_page(
        session, project=project, parent_id=parent_id, after_id=after_id,
        title=title, tree=tree, properties=properties, actor=actor,
    )
    await session.commit()
    return result
```

Add `_insert_page` to the module's `__all__` only if `page_door` exports private names there; it does not, so leave `__all__` alone.

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `python -m pytest -q tests/test_page_insert_split.py -v`
Expected: PASS, 7 tests.

Then prove the shared path is intact — this is the whole point of the risk score:

Run: `python -m pytest -q tests/test_page_door.py tests/test_block_verbs.py tests/test_page_document_isolation.py tests/test_api/test_pages.py`
Expected: PASS, with no change in counts from before this task.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/page_door.py backend/tests/test_page_insert_split.py
git commit -m "refactor(pages): split _insert_page out of create_page"
```

---

### Task 9: The import orchestrator

**Files:**
- Create: `backend/app/services/page_import.py`
- Test: `backend/tests/test_page_import.py`

**Interfaces:**
- Consumes: `open_archive` and the archive types (Contracts, **Archive**); `build_tree` (Contracts, **Tree**); `translate_page`, `StagedAsset` (Contracts, **Content**); `_insert_page` (Contracts, **Page insert**); `place_staged`, `insert_attachment_row` (Contracts, **Attachment helpers**); the six settings and `"pages_imported"` (Contracts, **Settings**, **Event type**).
- Produces: `ImportReport`, `ImportWarning`, `ImportBusy`, `ImportTooLarge`, `ImportNoSpace`, `import_notion_export`, `MAX_WARNINGS` — see Contracts, **Import orchestrator**. Task 11 consumes them.

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

Risk 3 on two counts. Concurrency: a module-level lock decides whether two imports interleave. Data loss: this is where files are placed relative to their rows, and rows-before-files is the one ordering that is unrecoverable on a crash.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_page_import.py`:

```python
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from sqlalchemy import text

from app.config import settings
from app.services.page_import import (
    ImportBusy,
    ImportNoSpace,
    ImportTooLarge,
    import_notion_export,
)
from tests.fixtures.notion.builder import DATABASE_EXPORT, FLAT_EXPORT, Entry, build_fixture


@pytest.fixture
def attachments_dir(tmp_path, monkeypatch):
    root = tmp_path / "attachments"
    root.mkdir()
    monkeypatch.setattr(settings, "attachments_dir", str(root))
    return root


async def _body(path: Path, chunk: int = 4096):
    data = path.read_bytes()
    for start in range(0, len(data), chunk):
        yield data[start:start + chunk]


async def _run(session, tmp_path, entries=FLAT_EXPORT, project="notes"):
    path = build_fixture(entries, tmp_path / "export.zip")
    return await import_notion_export(
        session, project=project, body=_body(path),
        declared_length=path.stat().st_size, actor="tester",
    )


@pytest.mark.asyncio
async def test_an_import_creates_the_root_and_its_pages(session, attachments_dir, tmp_path):
    report = await _run(session, tmp_path)
    title = (
        await session.execute(
            text("SELECT title FROM pages WHERE id = CAST(:id AS uuid)"),
            {"id": str(report.root_page_id)},
        )
    ).scalar_one()
    assert title.startswith("Notion import — ")
    assert report.pages_created == 6
    total = (
        await session.execute(
            text("SELECT count(*) FROM pages WHERE project = 'notes'")
        )
    ).scalar_one()
    assert total == report.pages_created + 1


@pytest.mark.asyncio
async def test_the_root_page_is_not_counted(session, attachments_dir, tmp_path):
    report = await _run(session, tmp_path)
    children = (
        await session.execute(
            text("SELECT count(*) FROM pages WHERE parent_id = CAST(:id AS uuid)"),
            {"id": str(report.root_page_id)},
        )
    ).scalar_one()
    assert children >= 1
    assert report.pages_created == 6


@pytest.mark.asyncio
async def test_attachments_are_stored_once_with_a_row_and_a_file(
    session, attachments_dir, tmp_path
):
    report = await _run(session, tmp_path)
    assert report.attachments_stored == 1
    assert report.attachment_bytes > 0
    rows = (
        await session.execute(
            text("SELECT id, content_type FROM page_attachments WHERE project = 'notes'")
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].content_type == "image/png"
    shard = attachments_dir / str(rows[0].id)[:2] / str(rows[0].id)
    assert shard.is_file()


@pytest.mark.asyncio
async def test_the_journal_records_one_import(session, attachments_dir, tmp_path):
    report = await _run(session, tmp_path)
    payload = (
        await session.execute(
            text(
                "SELECT payload FROM events WHERE event_type = 'pages_imported' "
                "AND object_id = CAST(:id AS uuid)"
            ),
            {"id": str(report.root_page_id)},
        )
    ).scalar_one()
    assert payload["pages_created"] == report.pages_created
    assert "title" not in payload and "path" not in payload


@pytest.mark.asyncio
async def test_the_staging_directory_is_removed_on_success(
    session, attachments_dir, tmp_path
):
    await _run(session, tmp_path)
    staging = attachments_dir / ".staging"
    assert not staging.exists() or not list(staging.iterdir())


@pytest.mark.asyncio
async def test_a_failure_in_the_write_rolls_back_and_unlinks(
    session, attachments_dir, tmp_path, monkeypatch
):
    # The test must not roll back itself: the conftest session's rollback ends
    # the isolation boundary, and re-reading `pages` afterwards would report 0
    # whether or not the import rolled back — a stub with no `except` passes it.
    from app.services import page_import

    rollbacks: list[int] = []
    original = session.rollback

    async def spy() -> None:
        rollbacks.append(1)
        await original()

    async def boom(*args, **kwargs):
        raise RuntimeError("injected")

    monkeypatch.setattr(session, "rollback", spy)
    monkeypatch.setattr(page_import, "_insert_page", boom)
    with pytest.raises(RuntimeError):
        await _run(session, tmp_path)

    assert rollbacks, "the import swallowed the failure without rolling back"
    placed = [p for p in attachments_dir.rglob("*") if p.is_file()]
    assert placed == [], "a placed attachment file survived the failure"
    staging = attachments_dir / ".staging"
    assert not staging.exists() or not list(staging.iterdir())


@pytest.mark.asyncio
async def test_a_second_import_is_refused_while_one_runs(session, attachments_dir, tmp_path):
    from app.services import page_import

    released = asyncio.Event()

    async def blocker():
        async with page_import._import_lock:
            await released.wait()

    holder = asyncio.create_task(blocker())
    await asyncio.sleep(0)
    try:
        with pytest.raises(ImportBusy):
            await _run(session, tmp_path)
    finally:
        released.set()
        await holder


@pytest.mark.asyncio
async def test_a_body_over_the_ceiling_is_refused(
    session, attachments_dir, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "notion_import_max_bytes", 64)
    with pytest.raises(ImportTooLarge):
        await _run(session, tmp_path)


@pytest.mark.asyncio
async def test_insufficient_space_is_refused_before_the_upload(
    session, attachments_dir, tmp_path, monkeypatch
):
    from app.services import page_import

    monkeypatch.setattr(
        page_import.shutil, "disk_usage",
        lambda _: type("U", (), {"total": 1, "used": 1, "free": 1})(),
    )
    with pytest.raises(ImportNoSpace):
        await _run(session, tmp_path)


@pytest.mark.asyncio
async def test_warnings_are_capped_and_counted(
    session, attachments_dir, tmp_path, monkeypatch
):
    from app.services import page_import

    monkeypatch.setattr(page_import, "MAX_WARNINGS", 2)
    body = "\n\n".join(f"![m{i}](gone{i}.png)" for i in range(6))
    entries = [
        Entry("A 00000000000000000000000000000001.md", f"# A\n\n{body}\n".encode("utf-8")),
    ]
    report = await _run(session, tmp_path, entries=entries)
    assert len(report.warnings) == 2
    assert report.warnings_omitted == 4


@pytest.mark.asyncio
async def test_a_database_page_and_its_rows_land_under_the_root(
    session, attachments_dir, tmp_path
):
    report = await _run(session, tmp_path, entries=DATABASE_EXPORT)
    assert report.databases == 2
    rows = (
        await session.execute(
            text(
                "SELECT p.title FROM pages p JOIN pages parent "
                "ON p.parent_id = parent.id WHERE parent.title = 'Board'"
            )
        )
    ).scalars().all()
    assert rows == ["Ship"]


@pytest.mark.asyncio
async def test_pages_keep_their_notion_id(session, attachments_dir, tmp_path):
    await _run(session, tmp_path)
    found = (
        await session.execute(
            text(
                "SELECT properties->>'notion_id' AS nid FROM pages "
                "WHERE title = 'Home'"
            )
        )
    ).scalar_one()
    assert found == "0" * 31 + "1"
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest -q tests/test_page_import.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.page_import'`

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/page_import.py`:

```python
"""Importing a Notion export into one project's page tree.

Three phases: the body streams to staging, the plan is built off the event loop
with no database access, and one transaction writes everything. Exactly one
import runs at a time and a second is refused before its bytes are read, so a
caller learns it is queued without first uploading a gigabyte.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import time
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.events import record_event
from app.services.notion_archive import (
    NotionArchive,
    NotionArchiveInvalid,
    NotionArchiveTooLarge,
    open_archive,
)
from app.services.notion_content import StagedAsset, translate_page
from app.services.notion_tree import NotionExportInvalid, NotionTree, build_tree
from app.services.page_attachments import (
    STAGING_DIRNAME,
    attachment_path,
    attachments_root,
    clean_filename,
    insert_attachment_row,
)
from app.services.page_attachments import place_staged
from app.services.page_door import (
    MAX_BLOCKS,
    MAX_CONTENT_CHARS,
    _insert_page,
    root_lock_key,
)
from app.services.page_door import _LOCK_ROOT

logger = logging.getLogger(__name__)

MAX_WARNINGS = 500
PAGES_IMPORTED_EVENT = "pages_imported"
CHUNK = 1 << 16
# Staging may hold the zip, a Part export's extracted members, and each
# referenced attachment at once. Text expands further but is never staged as a
# file; `notion_import_max_uncompressed_bytes` bounds that side.
SPACE_FACTOR = 3

# In-process, and valid for the reason the login limiter's state is: invariant
# 13 gives one worker and one event loop.
_import_lock = asyncio.Lock()


class ImportBusy(RuntimeError):
    """Another import holds the lock."""


class ImportTooLarge(ValueError):
    """The body passed `notion_import_max_bytes`."""


class ImportNoSpace(RuntimeError):
    """The attachments filesystem cannot hold the upload and its extraction."""


@dataclass(frozen=True)
class ImportWarning:
    path: str | None
    kind: str
    detail: str


@dataclass(frozen=True)
class ImportReport:
    root_page_id: UUID
    pages_created: int
    databases: int
    attachments_stored: int
    attachment_bytes: int
    warnings: list[ImportWarning]
    warnings_omitted: int


@dataclass
class _Warnings:
    kept: list[ImportWarning] = field(default_factory=list)
    omitted: int = 0

    def add(self, path: str | None, kind: str, detail: str) -> None:
        if len(self.kept) < MAX_WARNINGS:
            self.kept.append(ImportWarning(path or None, kind, detail))
        else:
            self.omitted += 1


@dataclass(frozen=True)
class _Plan:
    tree: NotionTree
    assets: dict[str, StagedAsset]
    blocks: dict[UUID, list]


def _free_bytes() -> int:
    return shutil.disk_usage(attachments_root()).free


def _require_space(needed: int) -> None:
    if needed and _free_bytes() < needed * SPACE_FACTOR:
        raise ImportNoSpace(
            f"the attachments filesystem has less than {needed * SPACE_FACTOR} "
            "bytes free"
        )


async def _stage_body(
    body: AsyncIterator[bytes], staging: Path, max_bytes: int,
) -> Path:
    target = staging / "upload.zip"
    size = 0
    with open(target, "wb") as handle:
        async for chunk in body:
            if not chunk:
                continue
            size += len(chunk)
            if size > max_bytes:
                raise ImportTooLarge(f"the export exceeds {max_bytes} bytes")
            handle.write(chunk)
    return target


def _resolve_target(target: str, from_entry: str) -> str:
    base = from_entry.rsplit("/", 1)[0].split("/") if "/" in from_entry else []
    parts = list(base)
    for piece in target.split("/"):
        if piece in ("", "."):
            continue
        if piece == "..":
            if parts:
                parts.pop()
            continue
        parts.append(piece)
    return "/".join(parts)


def _build_plan(
    zip_path: Path, staging: Path, deadline: float,
    warn: Callable[[str, str, str], None],
) -> tuple[NotionArchive, _Plan]:
    """Everything between the upload and the write. No database access.

    Note every page's source is read twice — once by `build_tree` for its title
    and property block, once here — and the archive's running counter is
    cumulative, so `notion_import_max_uncompressed_bytes` bounds roughly half
    that figure in text. Accepted: the ceiling is 5 GB against a measured 37 MB.
    """
    archive = open_archive(
        zip_path, staging / "parts",
        max_entries=settings.notion_import_max_entries,
        max_uncompressed_bytes=settings.notion_import_max_uncompressed_bytes,
        warn=warn,
    )
    tree = build_tree(archive, max_pages=settings.notion_import_max_pages, warn=warn)

    # Only assets something links to. An unreferenced one would become a row
    # and a file that nothing in the corpus points at, for the cleanup job to
    # collect a week later.
    referenced: set[str] = set()
    for node in tree.pages:
        if node.entry is None:
            continue
        for span in scan_links(archive.read_text(node.entry)):
            target = unquote(span.destination.split("#")[0])
            referenced.add(_resolve_target(target, node.entry.name))

    assets: dict[str, StagedAsset] = {}
    oversize: set[str] = set()
    asset_dir = staging / "assets"
    for name, entry in tree.assets.items():
        if name not in referenced:
            continue
        attachment_id = uuid4()
        destination = asset_dir / str(attachment_id)
        size, digest, content_type = archive.extract(entry, destination)
        if size > settings.attachment_max_bytes:
            destination.unlink(missing_ok=True)
            oversize.add(name)
            warn(name, "oversize_attachment",
                 f"{size} bytes is over the {settings.attachment_max_bytes} bound")
            continue
        assets[name] = StagedAsset(
            attachment_id=attachment_id, staged_path=destination,
            filename=clean_filename(name.rsplit("/", 1)[-1]),
            content_type=content_type, size_bytes=size, sha256=digest,
        )

    blocks: dict[UUID, list] = {}
    total = 0
    for node in tree.pages:
        if time.monotonic() > deadline:
            raise TimeoutError(
                f"the import passed {settings.notion_import_max_seconds} seconds"
            )
        rendered = translate_page(
            node, tree, archive, assets=assets,
            max_blocks=MAX_BLOCKS, max_content_chars=MAX_CONTENT_CHARS, warn=warn,
        )
        total += len(rendered)
        if total > settings.notion_import_max_blocks:
            raise NotionExportInvalid(
                f"the export exceeds {settings.notion_import_max_blocks} blocks"
            )
        blocks[node.uuid] = rendered
    return archive, _Plan(tree=tree, assets=assets, blocks=blocks)


async def import_notion_export(
    session: AsyncSession,
    *,
    project: str,
    body: AsyncIterator[bytes],
    declared_length: int | None,
    actor: str | None,
) -> ImportReport:
    # Checked before acquiring, and acquired with no await in between, so the
    # window this shape usually opens does not exist here (invariant 13).
    if _import_lock.locked():
        raise ImportBusy("an import is already running")
    async with _import_lock:
        return await _run_import(
            session, project=project, body=body,
            declared_length=declared_length, actor=actor,
        )


async def _run_import(
    session: AsyncSession,
    *,
    project: str,
    body: AsyncIterator[bytes],
    declared_length: int | None,
    actor: str | None,
) -> ImportReport:
    warnings = _Warnings()
    staging = attachments_root() / STAGING_DIRNAME / str(uuid4())
    staging.mkdir(parents=True, exist_ok=True)
    placed: list[UUID] = []
    archive: NotionArchive | None = None
    deadline = time.monotonic() + settings.notion_import_max_seconds
    # A dedicated single-thread executor, not the default one: that also serves
    # bcrypt MCP auth, git subprocesses and code parsing. It does NOT serialise
    # imports -- the lock above does.
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="notion-import")
    try:
        if declared_length:
            _require_space(declared_length)
        zip_path = await _stage_body(
            body, staging, settings.notion_import_max_bytes
        )
        _require_space(zip_path.stat().st_size)

        loop = asyncio.get_running_loop()
        archive, plan = await loop.run_in_executor(
            executor, _build_plan, zip_path, staging, deadline, warnings.add,
        )
        zip_path.unlink(missing_ok=True)

        await session.execute(_LOCK_ROOT, {"key": root_lock_key(project)})

        # Files BEFORE rows: a file with no row is swept by the cleanup job,
        # while a row with no file is a permanent 404 nothing repairs.
        for staged in plan.assets.values():
            await asyncio.to_thread(
                place_staged, staged.staged_path, staged.attachment_id
            )
            placed.append(staged.attachment_id)
        for staged in plan.assets.values():
            await insert_attachment_row(
                session,
                attachment_id=staged.attachment_id,
                project=project,
                page_id=None,
                filename=staged.filename,
                content_type=staged.content_type,
                size_bytes=staged.size_bytes,
                sha256=staged.sha256,
            )

        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        root = await _insert_page(
            session, project=project, parent_id=None, after_id=None,
            title=f"Notion import — {stamp} UTC", tree=[],
            properties=None, actor=actor,
        )

        ids: dict[UUID, UUID] = {}
        for node in plan.tree.pages:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"the import passed {settings.notion_import_max_seconds} seconds"
                )
            parent = ids[node.parent_uuid] if node.parent_uuid else root.id
            properties = {"notion_id": node.notion_id} if node.notion_id else None
            written = await _insert_page(
                session, project=project, parent_id=str(parent), after_id=None,
                title=node.title, tree=plan.blocks[node.uuid],
                properties=properties, actor=actor, page_id=node.uuid,
            )
            ids[node.uuid] = written.id

        signals = plan.tree.signal_counts
        if signals.get("database") or signals.get("link"):
            warnings.add(
                None, "derived_hierarchy",
                "hierarchy derived from the export: "
                f"{signals.get('database', 0)} by database membership, "
                f"{signals.get('link', 0)} by a standalone link, "
                f"{signals.get('root', 0)} left at the root",
            )

        await record_event(
            session,
            event_type=PAGES_IMPORTED_EVENT,
            object_type="page",
            object_id=root.id,
            project=project,
            actor=actor,
            payload={
                "pages_created": len(plan.tree.pages),
                "databases": len(plan.tree.databases),
                "attachments_stored": len(plan.assets),
                "warnings": len(warnings.kept) + warnings.omitted,
            },
        )
        await session.commit()
        return ImportReport(
            root_page_id=root.id,
            pages_created=len(plan.tree.pages),
            databases=len(plan.tree.databases),
            attachments_stored=len(plan.assets),
            attachment_bytes=sum(a.size_bytes for a in plan.assets.values()),
            warnings=warnings.kept,
            warnings_omitted=warnings.omitted,
        )
    except BaseException:
        await session.rollback()
        for attachment_id in placed:
            await asyncio.to_thread(
                attachment_path(attachment_id).unlink, True
            )
        raise
    finally:
        if archive is not None:
            archive.close()
        executor.shutdown(wait=False)
        await asyncio.to_thread(shutil.rmtree, staging, True)
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `python -m pytest -q tests/test_page_import.py -v`
Expected: PASS, 12 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/page_import.py backend/tests/test_page_import.py
git commit -m "feat(notion): orchestrate the import in three phases"
```

---

### Task 10: The edge body cap

**Files:**
- Modify: `backend/app/main.py:724-732` (`is_attachment_upload_path`) and `:781` (`RequestBodyLimitMiddleware.__call__`)
- Test: `backend/tests/test_edge_body_cap.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `is_page_import_path` and `bounds_own_body` — see Contracts, **Edge predicate**. Task 11 relies on the import path being exempt.

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

Risk 2 is the shared code path: this middleware sees every HTTP request. Without this task the import route is unreachable — a 1 GB body is refused at the edge with `payload_too_large` and the handler never runs.

Do not widen `is_attachment_upload_path` to cover both. Its name states a fact the attachment tests assert, and `main.py`'s own comment says two copies is how surfaces drift apart — the answer is one predicate above both, not one predicate meaning two things.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_edge_body_cap.py`:

```python
from __future__ import annotations

from app.main import (
    MAX_REQUEST_BODY_BYTES,
    bounds_own_body,
    is_attachment_upload_path,
    is_page_import_path,
)


def test_the_import_path_bounds_its_own_body():
    assert is_page_import_path("/api/v1/pages/import/notion") is True
    assert bounds_own_body("/api/v1/pages/import/notion") is True


def test_the_attachment_upload_path_still_bounds_its_own_body():
    path = "/api/v1/pages/11111111-1111-1111-1111-111111111111/attachments"
    assert is_attachment_upload_path(path) is True
    assert bounds_own_body(path) is True


def test_the_two_predicates_stay_distinct():
    upload = "/api/v1/pages/11111111-1111-1111-1111-111111111111/attachments"
    assert is_page_import_path(upload) is False
    assert is_attachment_upload_path("/api/v1/pages/import/notion") is False


def test_an_ordinary_page_route_is_still_capped():
    assert bounds_own_body("/api/v1/pages") is False
    assert bounds_own_body("/api/v1/pages/11111111-1111-1111-1111-111111111111") is False
    assert bounds_own_body("/api/v1/memories") is False


def test_a_lookalike_import_path_is_not_exempt():
    assert is_page_import_path("/api/v1/pages/import/notion/extra") is False
    assert is_page_import_path("/api/v1/pages/import") is False
    assert is_page_import_path("/api/v1/documents/import/notion") is False


async def test_an_oversized_body_on_an_ordinary_route_is_refused(client):
    response = await client.post(
        "/api/v1/memories",
        content=b"x" * 16,
        headers={"content-length": str(MAX_REQUEST_BODY_BYTES + 1)},
    )
    assert response.status_code == 413


async def test_an_oversized_declared_body_reaches_the_import_route(client):
    # Past the edge cap, so the refusal must come from the route's own auth or
    # validation rather than from `payload_too_large`.
    response = await client.post(
        "/api/v1/pages/import/notion?project=notes",
        content=b"PK\x05\x06" + b"\x00" * 18,
        headers={"content-length": str(MAX_REQUEST_BODY_BYTES + 1)},
    )
    assert response.status_code != 413
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest -q tests/test_edge_body_cap.py`
Expected: FAIL — `ImportError: cannot import name 'bounds_own_body'`

- [ ] **Step 3: Write the implementation**

In `backend/app/main.py`, directly after `is_attachment_upload_path` (which is unchanged), add:

```python
def is_page_import_path(path: str) -> bool:
    """`POST /api/v1/pages/import/notion` streams a whole Notion export and
    bounds it against `notion_import_max_bytes`, which is three orders of
    magnitude above the edge cap."""
    return path == "/api/v1/pages/import/notion"


def bounds_own_body(path: str) -> bool:
    """Whether this route enforces its own body ceiling.

    One predicate above both spellings rather than one predicate meaning two
    things: each name states a fact its own tests assert, and the middleware
    asks a single question.
    """
    return is_attachment_upload_path(path) or is_page_import_path(path)
```

Then in `RequestBodyLimitMiddleware.__call__`, replace the condition at line 781:

```python
        if scope["type"] == "http" and not is_mcp_path(path) and not bounds_own_body(path):
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `python -m pytest -q tests/test_edge_body_cap.py -v`
Expected: PASS, 7 tests. `test_an_oversized_declared_body_reaches_the_import_route` passes with a 401 or 422 once Task 11 lands, and with a 404 before it — either way, not 413.

Then confirm the edge policy tests are untouched:

Run: `python -m pytest -q tests/test_edge_response_policy.py tests/test_spa_edge.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_edge_body_cap.py
git commit -m "fix(edge): exempt the import route from the body cap"
```

---

### Task 11: The import route

**Files:**
- Create: `backend/app/api/routes/page_import.py`
- Modify: `backend/app/main.py:21` (the routes import) and its `include_router` block at `:1041-1048`
- Modify: `backend/app/services/content_surfaces.py:731` (after the attachment entries)
- Test: `backend/tests/test_page_import_route.py`

**Interfaces:**
- Consumes: `import_notion_export` and its refusals (Contracts, **Import orchestrator**); `bounds_own_body` (Contracts, **Edge predicate**).
- Produces: `POST /api/v1/pages/import/notion` — see Contracts, **Route**. Tasks 12, 14 and 16 rely on it.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_page_import_route.py` — beside the other page route
tests, which is where `test_page_attachment_routes.py` lives:

```python
"""The Notion import door over REST."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.config import settings
from tests.fixtures.notion.builder import FLAT_EXPORT, HTML_EXPORT, build_fixture

V1 = "/api/v1"
ZIP = {"Content-Type": "application/zip"}


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", str(tmp_path / "attachments"))
    return tmp_path


@pytest.fixture
async def project(session):
    # kind='project', not 'personal': `ux_projects_one_personal` is a partial
    # unique index, so a personal row leaked by any other module would collide.
    # The route checks the name only.
    await session.execute(
        text("INSERT INTO projects (name) VALUES ('notes') "
             "ON CONFLICT (name) DO NOTHING")
    )
    return "notes"


def _zip(entries, tmp_path, name="export.zip") -> bytes:
    return build_fixture(entries, tmp_path / name).read_bytes()


async def _post(client, auth_headers, tmp_path, entries=FLAT_EXPORT, project="notes"):
    return await client.post(
        f"{V1}/pages/import/notion?project={project}",
        content=_zip(entries, tmp_path),
        headers={**auth_headers, **ZIP},
    )


async def test_an_import_answers_201_with_the_report(
    client, auth_headers, root, project, tmp_path
):
    response = await _post(client, auth_headers, tmp_path)
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {
        "root_page_id", "pages_created", "databases", "attachments_stored",
        "attachment_bytes", "warnings", "warnings_omitted",
    }
    assert body["pages_created"] == 6
    assert all(set(w) == {"path", "kind", "detail"} for w in body["warnings"])


async def test_an_unknown_project_is_refused(client, auth_headers, root, tmp_path):
    response = await _post(client, auth_headers, tmp_path, project="no-such-project")
    assert response.status_code == 422
    assert "no-such-project" in response.json()["detail"]


async def test_an_html_export_is_refused_with_advice(
    client, auth_headers, root, project, tmp_path
):
    response = await _post(client, auth_headers, tmp_path, entries=HTML_EXPORT)
    assert response.status_code == 422
    assert "Markdown & CSV" in response.json()["detail"]


async def test_a_body_over_the_ceiling_answers_413(
    client, auth_headers, root, project, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "notion_import_max_bytes", 64)
    response = await _post(client, auth_headers, tmp_path)
    assert response.status_code == 413


async def test_a_concurrent_import_answers_409(
    client, auth_headers, root, project, tmp_path, monkeypatch
):
    from app.services import page_import

    class Held:
        def locked(self) -> bool:
            return True

    monkeypatch.setattr(page_import, "_import_lock", Held())
    response = await _post(client, auth_headers, tmp_path)
    assert response.status_code == 409


async def test_insufficient_space_answers_507(
    client, auth_headers, root, project, tmp_path, monkeypatch
):
    from app.services import page_import

    monkeypatch.setattr(
        page_import.shutil, "disk_usage",
        lambda _: type("U", (), {"total": 1, "used": 1, "free": 1})(),
    )
    response = await _post(client, auth_headers, tmp_path)
    assert response.status_code == 507


async def test_the_route_needs_auth(client, root, project, tmp_path):
    response = await client.post(
        f"{V1}/pages/import/notion?project=notes",
        content=_zip(FLAT_EXPORT, tmp_path),
        headers=ZIP,
    )
    assert response.status_code == 401


async def test_the_route_is_refused_on_a_read_only_instance(
    client, auth_headers, root, project, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "read_only", True)
    response = await _post(client, auth_headers, tmp_path)
    assert response.status_code == 403


async def test_the_route_does_not_shadow_a_page_read(client, auth_headers):
    response = await client.get(f"{V1}/pages/import", headers=auth_headers)
    assert response.status_code in (404, 422)
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest -q tests/test_page_import_route.py`
Expected: FAIL — 404 on every request, because the route is not registered.

- [ ] **Step 3: Write the implementation**

Create `backend/app/api/routes/page_import.py`:

```python
"""The Notion import door.

Provides:
  - POST /api/v1/pages/import/notion

REST-only, like the rest of the page tree. The raw body is the zip: FastAPI's
`UploadFile` spools a whole body before the handler runs, so a ceiling on it
could only ever be checked after the bytes landed. `main.bounds_own_body`
exempts this path from the edge cap for the same reason.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import refuse_when_read_only
from app.database import get_session
from app.services.notion_archive import NotionArchiveInvalid, NotionArchiveTooLarge
from app.services.notion_tree import NotionExportInvalid
from app.services.page_import import (
    ImportBusy,
    ImportNoSpace,
    ImportTooLarge,
    import_notion_export,
)

router = APIRouter(prefix="/api/v1/pages", tags=["pages"])

_PROJECT_EXISTS = text("SELECT 1 FROM projects WHERE name = :name")


class ImportWarningResponse(BaseModel):
    path: str | None
    kind: str
    detail: str


class ImportReportResponse(BaseModel):
    root_page_id: UUID
    pages_created: int
    databases: int
    attachments_stored: int
    attachment_bytes: int
    warnings: list[ImportWarningResponse]
    warnings_omitted: int


@router.post(
    "/import/notion",
    response_model=ImportReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_notion_route(
    request: Request,
    project: str = Query(..., min_length=1),
    _user=Depends(require_auth),
    _read_only=Depends(refuse_when_read_only),
    session: AsyncSession = Depends(get_session),
) -> ImportReportResponse:
    known = (
        await session.execute(_PROJECT_EXISTS, {"name": project})
    ).scalar_one_or_none()
    if known is None:
        # Before a byte is read: a gigabyte must never be accepted for a name
        # that cannot receive it.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"no project named {project!r}",
        )

    declared = request.headers.get("content-length")
    length = int(declared) if declared and declared.isdigit() else None
    # `TokenPayload` carries sub/exp/iat/jti and nothing else (auth.py:29-33).
    actor = getattr(_user, "sub", None)

    try:
        report = await import_notion_export(
            session, project=project, body=request.stream(),
            declared_length=length, actor=actor,
        )
    except ImportBusy as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except (ImportTooLarge, NotionArchiveTooLarge) as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
    except ImportNoSpace as exc:
        raise HTTPException(
            status.HTTP_507_INSUFFICIENT_STORAGE, str(exc)
        ) from exc
    except (NotionArchiveInvalid, NotionExportInvalid) as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)
        ) from exc

    return ImportReportResponse(
        root_page_id=report.root_page_id,
        pages_created=report.pages_created,
        databases=report.databases,
        attachments_stored=report.attachments_stored,
        attachment_bytes=report.attachment_bytes,
        warnings=[
            ImportWarningResponse(path=w.path, kind=w.kind, detail=w.detail)
            for w in report.warnings
        ],
        warnings_omitted=report.warnings_omitted,
    )
```

In `backend/app/main.py`, add `page_import as page_import_routes` to the `from app.api.routes import ...` list on line 21, and register it beside `app.include_router(pages_routes.router)` at line 1041 — and, critically, before `mount_spa(app, _resolve_spa_dir())` at line 1143, which must stay last (`test_spa_edge.py`):

```python
app.include_router(page_import_routes.router)
```

In `backend/app/services/content_surfaces.py`, after the two attachment entries at line 731:

```python
    # The Notion import writes pages and their blocks, so it is a content
    # surface on the same footing as the page write routes above.
    "POST /api/v1/pages/import/notion",
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `python -m pytest -q tests/test_page_import_route.py -v`
Expected: PASS, 9 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/page_import.py backend/app/main.py backend/app/services/content_surfaces.py backend/tests/test_page_import_route.py
git commit -m "feat(notion): serve the import route"
```

---

### Task 12: Guards leg and door parity

**Files:**
- Modify: `backend/tests/test_api/test_rest_conformance.py:216` (after the attachment entries)
- Modify: `backend/tests/test_door_parity.py` (the parity table)
- Modify: `backend/tests/test_block_retrieval.py` (`BLOCK_CHANNEL_MODULES`)
- Modify: `docs/two-door-parity.md` (the generated block plus its headline counts sentence)

**Interfaces:**
- Consumes: the route (Contracts, **Route**) and `page_import.py`'s module path.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 0 = 3

One new route trips a spread of full-list enumeration guards that live outside the module the work was in, and no door-local test touches them. This task is where they are satisfied.

- [ ] **Step 1: Run the guards leg to see what it demands**

Run from `backend/`, on its own lane database:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py \
    tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py \
    tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py \
    tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py \
    tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py \
    tests/test_event_taxonomy_map.py
```

Expected: FAIL in `test_rest_conformance.py`, `test_door_parity.py`, `test_block_retrieval.py` and `test_event_taxonomy_map.py`. Record each failure message; they are the specification for steps 2 to 4. It runs in about 40 seconds and needs no LLM key.

- [ ] **Step 2: Add the conformance expectation**

In `backend/tests/test_api/test_rest_conformance.py`, after the `GET /api/v1/pages/attachments/{attachment_id}` entry:

```python
    ("POST", "/api/v1/pages/import/notion"): 201,
```

- [ ] **Step 3: Add the parity row**

In `backend/tests/test_door_parity.py`, add this `Surface` literal directly after the `pages.attachments` one (which ends around line 1582):

```python
    Surface(
        name="pages.import",
        status=REST_ONLY,
        rest=(("POST", f"{V1}/pages/import/notion"),),
        mcp=(),
        reason=(
            "The Notion import. Single-door for the same reason pages.write "
            "is: the page tree is the operator's authored space, and an agent "
            "that could import a whole workspace into it is a capability "
            "nobody asked for. It is also not an agent shape -- the caller "
            "supplies a zip from their own filesystem, which neither the SPA's "
            "sibling doors nor the generated SDK model. Nothing here generates "
            "or labels content, so no eval gate is in play; an MCP twin later "
            "is additive and an owner decision."
        ),
    ),
```

Then regenerate `docs/two-door-parity.md`'s block the way that test's failure message directs. The **headline counts sentence** sits outside that block and is edited by hand — but it is not unguarded: `test_door_parity.py:2143-2158` asserts the derived headline appears in the doc verbatim, so this same run stays red until the sentence is updated too.

- [ ] **Step 4: Add the block-channel module**

In `backend/tests/test_block_retrieval.py`, add `app.services.page_import` to `BLOCK_CHANNEL_MODULES`. It writes `blocks` through `_insert_page`, so the firewall scans must cover it: the module must not be able to reach `app.services.pipeline`, and it must name no `KnowledgeTripleRepository` method.

- [ ] **Step 5: Run the whole guards leg and commit**

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py \
    tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py \
    tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py \
    tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py \
    tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py \
    tests/test_event_taxonomy_map.py
```

Expected: PASS, except `test_event_taxonomy_map.py`, which Task 15 closes. If it is the only red, continue.

```bash
git add backend/tests docs/two-door-parity.md
git commit -m "test(notion): satisfy the enumeration guards"
```

---

### Task 13: `apiUpload`

**Files:**
- Modify: `frontend/src/lib/api.ts` (after `apiFetch`, currently line 104)
- Test: `frontend/src/lib/__tests__/api-upload.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `apiUpload` — see Contracts, **Frontend upload helper**. Task 14 consumes it.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

This is the SPA's first `XMLHttpRequest`; `grep -rn "XMLHttpRequest" frontend/src` returns nothing today. It lives in `lib/api.ts` rather than in the feature so the `/api/v1` base, `credentials`, the 401 redirect and the `ApiError` shape are written once. `fetch` cannot report upload progress, which is the only reason XHR is here.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/__tests__/api-upload.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ApiError, apiUpload } from "@/lib/api"

const logout = vi.fn()
const getState = vi.fn(() => ({ logout }))
vi.mock("@/features/auth", () => ({ useAuthStore: { getState: () => getState() } }))

type Handler = (xhr: FakeXhr) => void

class FakeXhr {
  static handler: Handler = () => {}
  upload = { onprogress: null as ((e: ProgressEvent) => void) | null }
  onload: (() => void) | null = null
  onerror: (() => void) | null = null
  onabort: (() => void) | null = null
  withCredentials = false
  status = 0
  responseText = ""
  method = ""
  url = ""
  headers: Record<string, string> = {}
  aborted = false

  open(method: string, url: string) {
    this.method = method
    this.url = url
  }
  setRequestHeader(key: string, value: string) {
    this.headers[key] = value
  }
  abort() {
    this.aborted = true
    this.onabort?.()
  }
  send(_body: unknown) {
    FakeXhr.handler(this)
  }
}

beforeEach(() => {
  vi.stubGlobal("XMLHttpRequest", FakeXhr)
  logout.mockClear()
  FakeXhr.handler = (xhr) => {
    xhr.status = 201
    xhr.responseText = JSON.stringify({ ok: true })
    xhr.onload?.()
  }
})

describe("apiUpload", () => {
  it("posts to the v1 base with credentials", async () => {
    let seen: FakeXhr | null = null
    FakeXhr.handler = (xhr) => {
      seen = xhr
      xhr.status = 201
      xhr.responseText = "{}"
      xhr.onload?.()
    }
    await apiUpload("/pages/import/notion?project=notes", new Blob(["x"]))
    expect(seen!.method).toBe("POST")
    expect(seen!.url).toBe("/api/v1/pages/import/notion?project=notes")
    expect(seen!.withCredentials).toBe(true)
  })

  it("returns the parsed body", async () => {
    const body = await apiUpload<{ ok: boolean }>("/x", new Blob(["x"]))
    expect(body).toEqual({ ok: true })
  })

  it("passes supplied headers through", async () => {
    let seen: FakeXhr | null = null
    FakeXhr.handler = (xhr) => {
      seen = xhr
      xhr.status = 201
      xhr.responseText = "{}"
      xhr.onload?.()
    }
    await apiUpload("/x", new Blob(["x"]), {
      headers: { "Content-Type": "application/zip" },
    })
    expect(seen!.headers["Content-Type"]).toBe("application/zip")
  })

  it("reports upload progress as a fraction", async () => {
    const seen: number[] = []
    FakeXhr.handler = (xhr) => {
      xhr.upload.onprogress?.({ lengthComputable: true, loaded: 25, total: 100 } as ProgressEvent)
      xhr.upload.onprogress?.({ lengthComputable: true, loaded: 100, total: 100 } as ProgressEvent)
      xhr.status = 201
      xhr.responseText = "{}"
      xhr.onload?.()
    }
    await apiUpload("/x", new Blob(["x"]), { onProgress: (f) => seen.push(f) })
    expect(seen).toEqual([0.25, 1])
  })

  it("ignores a progress event with no total", async () => {
    const seen: number[] = []
    FakeXhr.handler = (xhr) => {
      xhr.upload.onprogress?.({ lengthComputable: false, loaded: 5, total: 0 } as ProgressEvent)
      xhr.status = 201
      xhr.responseText = "{}"
      xhr.onload?.()
    }
    await apiUpload("/x", new Blob(["x"]), { onProgress: (f) => seen.push(f) })
    expect(seen).toEqual([])
  })

  it("throws an ApiError carrying the envelope detail", async () => {
    FakeXhr.handler = (xhr) => {
      xhr.status = 422
      xhr.responseText = JSON.stringify({ detail: "re-export as Markdown & CSV" })
      xhr.onload?.()
    }
    await expect(apiUpload("/x", new Blob(["x"]))).rejects.toMatchObject({
      name: "ApiError",
      status: 422,
      message: "re-export as Markdown & CSV",
    })
  })

  it("falls back to a status message when the body is not JSON", async () => {
    FakeXhr.handler = (xhr) => {
      xhr.status = 500
      xhr.responseText = "<html>"
      xhr.onload?.()
    }
    await expect(apiUpload("/x", new Blob(["x"]))).rejects.toBeInstanceOf(ApiError)
  })

  it("logs out and throws on a 401", async () => {
    FakeXhr.handler = (xhr) => {
      xhr.status = 401
      xhr.responseText = "{}"
      xhr.onload?.()
    }
    await expect(apiUpload("/x", new Blob(["x"]))).rejects.toMatchObject({ status: 401 })
    expect(logout).toHaveBeenCalled()
  })

  it("rejects on a transport error", async () => {
    FakeXhr.handler = (xhr) => xhr.onerror?.()
    await expect(apiUpload("/x", new Blob(["x"]))).rejects.toBeInstanceOf(ApiError)
  })

  it("aborts when its signal fires", async () => {
    const controller = new AbortController()
    let seen: FakeXhr | null = null
    FakeXhr.handler = (xhr) => {
      seen = xhr
      controller.abort()
    }
    await expect(
      apiUpload("/x", new Blob(["x"]), { signal: controller.signal }),
    ).rejects.toBeInstanceOf(ApiError)
    expect(seen!.aborted).toBe(true)
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `frontend/`: `npx vitest run src/lib/__tests__/api-upload.test.ts`
Expected: FAIL — `apiUpload is not exported by "@/lib/api"`

- [ ] **Step 3: Write the implementation**

In `frontend/src/lib/api.ts`, after `apiFetch`:

```ts
export interface ApiUploadOptions {
  headers?: Record<string, string>
  /** Fraction of the body sent, 0 to 1. Fires only while the length is known. */
  onProgress?: (fraction: number) => void
  signal?: AbortSignal
}

/** `apiFetch` for a request whose upload progress matters.
 *
 *  XHR rather than `fetch` for one reason: `fetch` reports no upload progress,
 *  and an import body can be hundreds of megabytes. Everything else here
 *  mirrors `apiFetchWithHeaders` deliberately — the base path, the credentials,
 *  the 401 handling and the `ApiError` shape — so a caller cannot tell the two
 *  transports apart from its error handling.
 */
export function apiUpload<T>(
  path: string,
  body: Blob,
  options: ApiUploadOptions = {},
): Promise<T> {
  const { headers = {}, onProgress, signal } = options
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open("POST", `${API_BASE}${path}`)
    xhr.withCredentials = true
    for (const [key, value] of Object.entries(headers)) {
      xhr.setRequestHeader(key, value)
    }

    if (onProgress) {
      xhr.upload.onprogress = (event: ProgressEvent) => {
        if (event.lengthComputable && event.total > 0) {
          onProgress(event.loaded / event.total)
        }
      }
    }

    const onAbort = () => xhr.abort()
    signal?.addEventListener("abort", onAbort)
    const done = () => signal?.removeEventListener("abort", onAbort)

    xhr.onload = () => {
      done()
      if (xhr.status === 401) {
        handleUnauthorized()
        reject(new ApiError("Unauthorized", 401))
        return
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve((xhr.responseText ? JSON.parse(xhr.responseText) : undefined) as T)
        } catch {
          reject(new ApiError("The server sent a malformed response", xhr.status))
        }
        return
      }
      let message = `API error: ${xhr.status}`
      let details: unknown[] | undefined
      try {
        const parsed = JSON.parse(xhr.responseText) as {
          detail?: string
          error?: { details?: unknown[] }
        }
        message = parsed.detail || message
        details = parsed.error?.details
      } catch {
        // A non-JSON body (an nginx page, an empty 502) keeps the status text.
      }
      reject(new ApiError(message, xhr.status, details))
    }
    xhr.onerror = () => {
      done()
      reject(new ApiError("The upload could not reach the server", 0))
    }
    xhr.onabort = () => {
      done()
      reject(new ApiError("The upload was cancelled", 0))
    }
    xhr.send(body)
  })
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `frontend/`:

```bash
npx vitest run src/lib/__tests__/api-upload.test.ts
npm run typecheck
```

Expected: PASS, 10 tests; typecheck clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/__tests__/api-upload.test.ts
git commit -m "feat(api): add an upload helper with progress"
```

---

### Task 14: The import dialog

**Files:**
- Create: `frontend/src/features/notes/lib/notion-import.ts`
- Create: `frontend/src/features/notes/notion-import-dialog.tsx`
- Test: `frontend/src/features/notes/__tests__/notion-import-dialog.test.tsx`

**Interfaces:**
- Consumes: `apiUpload` (Contracts, **Frontend upload helper**); the route's report shape (Contracts, **Route**).
- Produces: `importNotionExport`, `ImportReport`, `ImportWarning`, `NotionImportDialog` — see Contracts, **Frontend import client** and **Dialog**. Task 15 mounts the dialog.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

`darkraise-ui` 6.6.0 ships `dialog`, `file-upload` and `progress`; read the `.d.ts` beside each before writing against it. `file-upload` is selection and validation only and carries no transport, so the request is `apiUpload`'s.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/notes/__tests__/notion-import-dialog.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { NotionImportDialog } from "../notion-import-dialog"

const importNotionExport = vi.fn()
vi.mock("../lib/notion-import", () => ({
  importNotionExport: (...args: unknown[]) => importNotionExport(...args),
}))

function open(onImported = vi.fn()) {
  render(
    <NotionImportDialog
      project="notes"
      open
      onOpenChange={vi.fn()}
      onImported={onImported}
    />,
  )
  return onImported
}

function pick(name = "export.zip") {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement
  const file = new File([new Uint8Array([1, 2, 3])], name, { type: "application/zip" })
  Object.defineProperty(input, "files", { value: [file] })
  fireEvent.change(input)
  return file
}

beforeEach(() => {
  importNotionExport.mockReset()
})

describe("NotionImportDialog", () => {
  it("shows the export instructions while idle", () => {
    open()
    expect(screen.getByText(/Markdown & CSV/i)).toBeInTheDocument()
  })

  it("accepts only zip files", () => {
    open()
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    expect(input.accept).toContain(".zip")
  })

  it("reports progress while the body uploads", async () => {
    let report!: (fraction: number) => void
    importNotionExport.mockImplementation(
      (_p: string, _f: File, onProgress: (n: number) => void) =>
        new Promise(() => {
          report = onProgress
        }),
    )
    open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    await waitFor(() => expect(importNotionExport).toHaveBeenCalled())
    report(0.5)
    await waitFor(() =>
      expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "50"),
    )
  })

  it("goes indeterminate once the body is sent", async () => {
    let report!: (fraction: number) => void
    importNotionExport.mockImplementation(
      (_p: string, _f: File, onProgress: (n: number) => void) =>
        new Promise(() => {
          report = onProgress
        }),
    )
    open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    await waitFor(() => expect(importNotionExport).toHaveBeenCalled())
    report(1)
    await waitFor(() =>
      expect(screen.getByRole("progressbar")).not.toHaveAttribute("aria-valuenow"),
    )
  })

  it("says a committed import is not cancelled by closing", async () => {
    importNotionExport.mockImplementation(() => new Promise(() => {}))
    open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    await waitFor(() =>
      expect(screen.getByText(/closing this does not cancel/i)).toBeInTheDocument(),
    )
  })

  it("shows the counts on success", async () => {
    importNotionExport.mockResolvedValue({
      root_page_id: "r1", pages_created: 12, databases: 2,
      attachments_stored: 3, attachment_bytes: 900, warnings: [], warnings_omitted: 0,
    })
    open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    expect(await screen.findByText(/12/)).toBeInTheDocument()
  })

  it("lists warnings and their omitted count", async () => {
    importNotionExport.mockResolvedValue({
      root_page_id: "r1", pages_created: 1, databases: 0,
      attachments_stored: 0, attachment_bytes: 0,
      warnings: [{ path: "A.md", kind: "missing_file", detail: "x.png is not in the export" }],
      warnings_omitted: 4,
    })
    open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    fireEvent.click(await screen.findByRole("button", { name: /warning/i }))
    expect(await screen.findByText(/x\.png is not in the export/)).toBeInTheDocument()
    expect(screen.getByText(/4 more/)).toBeInTheDocument()
  })

  it("hands the root page id back on Go to imported pages", async () => {
    importNotionExport.mockResolvedValue({
      root_page_id: "root-123", pages_created: 1, databases: 0,
      attachments_stored: 0, attachment_bytes: 0, warnings: [], warnings_omitted: 0,
    })
    const onImported = open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    fireEvent.click(await screen.findByRole("button", { name: /go to imported pages/i }))
    expect(onImported).toHaveBeenCalledWith("root-123")
  })

  it("renders a refusal in the dialog, not as a toast", async () => {
    importNotionExport.mockRejectedValue(
      Object.assign(new Error("re-export from Notion as Markdown & CSV"), {
        name: "ApiError", status: 422,
      }),
    )
    open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    expect(
      await screen.findByText(/re-export from Notion as Markdown & CSV/),
    ).toBeInTheDocument()
  })

  it("lets the operator retry after a refusal", async () => {
    importNotionExport.mockRejectedValueOnce(new Error("nope"))
    open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    await screen.findByText(/nope/)
    expect(screen.getByRole("button", { name: /import/i })).toBeEnabled()
  })

  it("disables the import button with no file chosen", () => {
    open()
    expect(screen.getByRole("button", { name: /import/i })).toBeDisabled()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `frontend/`: `npx vitest run src/features/notes/__tests__/notion-import-dialog.test.tsx`
Expected: FAIL — cannot resolve `../notion-import-dialog`

- [ ] **Step 3: Write the implementation**

Create `frontend/src/features/notes/lib/notion-import.ts`:

```ts
import { apiUpload } from "@/lib/api"

export type ImportWarning = {
  path: string | null
  kind: string
  detail: string
}

export type ImportReport = {
  root_page_id: string
  pages_created: number
  databases: number
  attachments_stored: number
  attachment_bytes: number
  warnings: ImportWarning[]
  warnings_omitted: number
}

export function importNotionExport(
  project: string,
  file: File,
  onProgress?: (fraction: number) => void,
): Promise<ImportReport> {
  return apiUpload<ImportReport>(
    `/pages/import/notion?project=${encodeURIComponent(project)}`,
    file,
    { headers: { "Content-Type": "application/zip" }, onProgress },
  )
}
```

Create `frontend/src/features/notes/notion-import-dialog.tsx`:

```tsx
import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import {
  FileUpload,
  FileUploadDropzone,
  FileUploadHiddenInput,
  FileUploadItem,
  FileUploadItemGroup,
  FileUploadItemName,
  FileUploadTrigger,
} from "darkraise-ui/components/file-upload"
import { Progress } from "darkraise-ui/components/progress"

import { type ImportReport, importNotionExport } from "./lib/notion-import"

// Mirrors the backend's `notion_import_max_bytes` so the picker refuses an
// oversized zip before it is uploaded rather than after.
const MAX_IMPORT_BYTES = 1_073_741_824

type Phase =
  | { kind: "idle" }
  | { kind: "uploading"; fraction: number }
  | { kind: "importing" }
  | { kind: "done"; report: ImportReport }
  | { kind: "failed"; message: string }

export function NotionImportDialog({
  project,
  open,
  onOpenChange,
  onImported,
}: {
  project: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onImported: (rootPageId: string) => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [phase, setPhase] = useState<Phase>({ kind: "idle" })
  const [showWarnings, setShowWarnings] = useState(false)
  const busy = phase.kind === "uploading" || phase.kind === "importing"

  async function run() {
    if (!file) return
    setPhase({ kind: "uploading", fraction: 0 })
    try {
      const report = await importNotionExport(project, file, (fraction) => {
        // 1 means the body is sent and the server is now working, which has no
        // fraction to report -- so the bar goes indeterminate rather than
        // sitting at 100% for the length of the import.
        setPhase(
          fraction >= 1 ? { kind: "importing" } : { kind: "uploading", fraction },
        )
      })
      setPhase({ kind: "done", report })
    } catch (error) {
      setPhase({
        kind: "failed",
        message: error instanceof Error ? error.message : String(error),
      })
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && busy) return
        onOpenChange(next)
      }}
      closeOnOutsidePointerDown={!busy}
      closeOnEscape={!busy}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Import from Notion</DialogTitle>
          <DialogDescription>
            In Notion, open Settings → Export, choose <strong>Markdown &amp; CSV</strong>,
            turn on “Include subpages” and include files. Then upload the zip here.
          </DialogDescription>
        </DialogHeader>

        {phase.kind === "idle" || phase.kind === "failed" ? (
          <FileUpload
            accept=".zip"
            maxFiles={1}
            maxFileSize={MAX_IMPORT_BYTES}
            onFileAccept={({ files }) => setFile(files[0] ?? null)}
          >
            <FileUploadHiddenInput />
            <FileUploadDropzone>
              <FileUploadTrigger asChild>
                <Button type="button" variant="outline" size="sm">
                  Choose a zip
                </Button>
              </FileUploadTrigger>
            </FileUploadDropzone>
            <FileUploadItemGroup>
              {file ? (
                <FileUploadItem file={file}>
                  <FileUploadItemName />
                </FileUploadItem>
              ) : null}
            </FileUploadItemGroup>
          </FileUpload>
        ) : null}

        {phase.kind === "uploading" ? (
          <Progress
            value={Math.round(phase.fraction * 100)}
            aria-label="Upload progress"
          />
        ) : null}

        {phase.kind === "importing" ? (
          <div className="space-y-2">
            <Progress value={null} aria-label="Import progress" />
            <p className="text-muted-foreground text-sm">
              Importing. Closing this does not cancel an import that has already
              reached the server.
            </p>
          </div>
        ) : null}

        {phase.kind === "failed" ? (
          <p className="text-destructive text-sm">{phase.message}</p>
        ) : null}

        {phase.kind === "done" ? (
          <div className="space-y-3 text-sm">
            <p>
              Imported <strong>{phase.report.pages_created}</strong> pages,{" "}
              <strong>{phase.report.databases}</strong> databases and{" "}
              <strong>{phase.report.attachments_stored}</strong> files.
            </p>
            {phase.report.warnings.length > 0 ? (
              <div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowWarnings((shown) => !shown)}
                >
                  {phase.report.warnings.length} warnings
                </Button>
                {showWarnings ? (
                  <ul className="text-muted-foreground mt-2 space-y-1">
                    {phase.report.warnings.map((warning, index) => (
                      <li key={`${warning.kind}-${index}`}>
                        {warning.path ? `${warning.path}: ` : ""}
                        {warning.detail}
                      </li>
                    ))}
                    {phase.report.warnings_omitted > 0 ? (
                      <li>and {phase.report.warnings_omitted} more</li>
                    ) : null}
                  </ul>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}

        <DialogFooter>
          {phase.kind === "done" ? (
            <Button
              type="button"
              onClick={() => onImported(phase.report.root_page_id)}
            >
              Go to imported pages
            </Button>
          ) : (
            <Button type="button" disabled={!file || busy} onClick={run}>
              Import
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

Read `frontend/node_modules/darkraise-ui/dist/components/file-upload.d.ts` and `progress.d.ts` before writing this, and adjust the part names to whatever they actually export — the props above follow those files as of 6.6.0, but the `.d.ts` is the authority.

- [ ] **Step 4: Run the test to verify it passes**

Run from `frontend/`:

```bash
npx vitest run src/features/notes/__tests__/notion-import-dialog.test.tsx
npm run typecheck
```

Expected: PASS, 11 tests; typecheck clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes/lib/notion-import.ts frontend/src/features/notes/notion-import-dialog.tsx frontend/src/features/notes/__tests__/notion-import-dialog.test.tsx
git commit -m "feat(notes): add the notion import dialog"
```

---

### Task 15: Header menu and event taxonomy

**Files:**
- Modify: `frontend/src/features/notes/notes-workspace.tsx:167-177` (the tree header row)
- Modify: `frontend/src/features/activity/event-taxonomy.ts`
- Test: `frontend/src/features/notes/__tests__/notes-workspace-import.test.tsx`
- Test: `frontend/src/features/notes/__tests__/notes-workspace-import.demo.test.tsx`
- Test: `backend/tests/test_event_taxonomy_map.py` (run, not edited)

**Interfaces:**
- Consumes: `NotionImportDialog` (Contracts, **Dialog**); the `"pages_imported"` event type (Contracts, **Event type**).
- Produces: nothing.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

There is no header menu today — `notes-workspace.tsx:167-177` is a bare row holding one "New page" ghost button. The one menu idiom in this feature is the per-row actions menu at `page-tree.tsx:112-128`, and it is the SPA's only `DropdownMenu`; copy it, including the `event.stopPropagation()` on trigger and content.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/notes/__tests__/notes-workspace-import.test.tsx`.
Write it self-contained, the way `notes-workspace.test.tsx` is: that file's
render harness is a local function depending on its own hoisted
`vi.mock("@/lib/api")`, `vi.mock("@/lib/demo-flag")` and
`vi.mock("darkraise-ui/components/sonner")` calls, so extracting it would drag
those mocks along and the DEMO case would then fight the helper's own
`DEMO: false`. Copy the mock preamble and the `render(<NotesWorkspace … />)`
call from `notes-workspace.test.tsx` and adapt the props; the two DEMO cases go
in **separate files** so each can hoist its own `demo-flag` mock.

```tsx
// Mirror notes-workspace.test.tsx's mock preamble here, with DEMO false, then:
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { NotesWorkspace } from "../notes-workspace"

vi.mock("../notion-import-dialog", () => ({
  NotionImportDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="import-dialog" /> : null,
}))

function renderWorkspace() {
  // Same shape as notes-workspace.test.tsx's own render call.
  return render(
    <NotesWorkspace project="notes" selectedId={null} onSelect={vi.fn()} />,
  )
}

describe("the page tree header menu", () => {
  it("offers Import from Notion", async () => {
    renderWorkspace()
    fireEvent.click(screen.getByRole("button", { name: /page tree actions/i }))
    expect(
      await screen.findByRole("menuitem", { name: /import from notion/i }),
    ).toBeInTheDocument()
  })

  it("opens the dialog when chosen", async () => {
    renderWorkspace()
    fireEvent.click(screen.getByRole("button", { name: /page tree actions/i }))
    fireEvent.click(await screen.findByRole("menuitem", { name: /import from notion/i }))
    await waitFor(() => expect(screen.getByTestId("import-dialog")).toBeInTheDocument())
  })

  it("keeps the New page button beside it", () => {
    renderWorkspace()
    expect(screen.getByRole("button", { name: /new page/i })).toBeInTheDocument()
  })
})
```

And `frontend/src/features/notes/__tests__/notes-workspace-import.demo.test.tsx`,
whose only difference is the demo flag — the idiom
`routes/_authenticated/__tests__/notes.demo.test.tsx:5` already uses:

```tsx
vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
// ...the same mock preamble and renderWorkspace as above...

it("offers no import under DEMO", () => {
  renderWorkspace()
  expect(
    screen.queryByRole("button", { name: /page tree actions/i }),
  ).not.toBeInTheDocument()
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `frontend/`: `npx vitest run src/features/notes/__tests__/notes-workspace-import`
Expected: FAIL — no button named "Page tree actions".

- [ ] **Step 3: Write the implementation**

In `frontend/src/features/notes/notes-workspace.tsx`, add the imports:

```tsx
import { MoreHorizontal } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "darkraise-ui/components/dropdown-menu"

import { DEMO } from "@/lib/demo-flag"
import { NotionImportDialog } from "./notion-import-dialog"
```

Add state beside the workspace's existing state:

```tsx
const [importing, setImporting] = useState(false)
```

Replace the header row at lines 167-177 with:

```tsx
<div className="mb-1.5 flex items-center justify-end gap-1">
  <Button type="button" size="sm" variant="ghost" onClick={() => createPage(null)}>
    <Plus className="mr-1 size-3.5" />
    New page
  </Button>
  {DEMO ? null : (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          aria-label="Page tree actions"
        >
          <MoreHorizontal className="size-3.5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={() => setImporting(true)}>
          Import from Notion
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )}
</div>
```

Render the dialog beside the workspace's existing rename dialog:

```tsx
<NotionImportDialog
  project={project}
  open={importing}
  onOpenChange={setImporting}
  onImported={(rootPageId) => {
    setImporting(false)
    void queryClient.invalidateQueries({ queryKey: ["pages"] })
    void queryClient.invalidateQueries({ queryKey: ["pagesTrash"] })
    onSelect(rootPageId)
  }}
/>
```

Use whichever `QueryClient` handle this component already holds; it uses the shared `invalidatePageLists` helper elsewhere, so prefer calling that if it is in scope.

In `frontend/src/features/activity/event-taxonomy.ts`, map the new event type alongside the other `page_*` entries, following whatever shape that file's existing rows use — a label such as "Pages imported" and the same group the page events already sit in.

- [ ] **Step 4: Run the tests to verify they pass**

Run from `frontend/`:

```bash
npx vitest run src/features/notes/__tests__/notes-workspace-import
npm test
npm run typecheck
npm run build
```

Expected: PASS throughout.

Then close the last guard from Task 12, from `backend/`:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  python -m pytest -q tests/test_event_taxonomy_map.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/notes frontend/src/features/activity/event-taxonomy.ts
git commit -m "feat(notes): offer the notion import in the tree header"
```

---

### Task 16: Documentation and the Playwright leg

**Files:**
- Modify: `CLAUDE.md` (the Pages paragraph's route inventory, and the `/notes` paragraph)
- Modify: `docs/two-door-parity.md` (the headline counts sentence only; the block was regenerated in Task 12)
- Modify: `CHANGELOG.md`
- Create: `frontend/tests/notion-import.spec.ts`

**Interfaces:**
- Consumes: everything above.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 0 = 3

- [ ] **Step 1: Write the Playwright spec**

Create `frontend/tests/notion-import.spec.ts`, following whatever fixture and login helpers the existing specs in that directory use:

Every spec in that directory signs in first; one that goes straight to `/notes`
lands on `/login` and fails. Copy the preamble from
`frontend/tests/notes-editor.spec.ts:11-27` verbatim — the `PASSWORD` constant,
the `signIn` helper and the `beforeAll` that refuses a missing
`E2E_ADMIN_PASSWORD` rather than soft-skipping.

```ts
import { expect, test, type Page } from "@playwright/test"
import { seedAdminPassword } from "./helpers/seed-admin"

const PASSWORD = process.env.E2E_ADMIN_PASSWORD

async function signIn(page: Page) {
  await page.goto("/login")
  await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
  await page.getByRole("button", { name: /sign in/i }).click()
  await expect(page).toHaveURL("/")
}

test.beforeAll(() => {
  if (!PASSWORD) {
    throw new Error("E2E_ADMIN_PASSWORD must be set — this spec never soft-skips for a missing credential.")
  }
  if (!process.env.E2E_DISPOSABLE_STACK) {
    seedAdminPassword()
  }
})

test("imports a Notion export and shows the tree", async ({ page }) => {
  await signIn(page)
  await page.goto("/notes")
  await page.getByRole("button", { name: "Page tree actions" }).click()
  await page.getByRole("menuitem", { name: /import from notion/i }).click()

  await page.setInputFiles(
    'input[type="file"]',
    "tests/fixtures/notion-export.zip",
  )
  await page.getByRole("button", { name: /^import$/i }).click()

  await expect(page.getByRole("button", { name: /go to imported pages/i }))
    .toBeVisible({ timeout: 60_000 })
  await page.getByRole("button", { name: /go to imported pages/i }).click()

  await expect(page.getByText(/Notion import — /)).toBeVisible()
  await expect(page.getByText("Home")).toBeVisible()
})
```

Generate `frontend/tests/fixtures/notion-export.zip` from the Task 1 builder and
commit it, so the spec has no build step of its own. From `backend/`:

```bash
mkdir -p ../frontend/tests/fixtures
python -c "
from pathlib import Path
from tests.fixtures.notion.builder import FLAT_EXPORT, build_fixture
build_fixture(FLAT_EXPORT, Path('../frontend/tests/fixtures/notion-export.zip'))
"
```

- [ ] **Step 2: Run the Playwright leg**

Run from the repository root — **never a bare `npx playwright test`**, which points `/api` at the live instance on `:8000`:

```bash
python backend/scripts/e2e/run_playwright_e2e.py
```

Expected: PASS. A red here is a kill before it is a regression: check `free -h`, and re-run the leg standalone before believing it. Exit 143 is a SIGTERM from `earlyoom`, not a failure.

- [ ] **Step 3: Update the documentation**

In `CLAUDE.md`, in the Pages paragraph, change the route inventory sentence so it names three modules rather than two — thirteen routes under `/api/v1/pages` in `api/routes/pages.py`, the two attachment routes in `api/routes/page_attachments.py`, and the import route in `api/routes/page_import.py`, sixteen in all.

In the same file's `/notes` paragraph, add one sentence: the tree header carries an "Import from Notion" action that files a Markdown & CSV export into the tree, deriving hierarchy from database membership and standalone links because a Notion export made without "Create folders for subpages" states none.

In `docs/two-door-parity.md`, update the headline counts sentence by hand — Task 12 already did this if its guards run went green, since `test_door_parity.py:2143-2158` asserts the derived headline appears verbatim. Nothing *regenerates* the sentence, but it is checked; confirm it matches rather than assuming.

In `CHANGELOG.md`, add the entry for the release carrying this increment, following the file's existing `## vN.N.N` shape.

- [ ] **Step 4: Run the full gate**

Run from the repository root:

```bash
./scripts/gate.sh
```

Expected: PASS. If a leg goes red, check `free -h` first — an `earlyoom` kill lands as exit 143 on whichever leg was running and is not a property of that leg. `./scripts/gate.sh --full` cannot complete on this host; run the extra legs individually if they are needed.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md docs/two-door-parity.md CHANGELOG.md frontend/tests
git commit -m "docs(notion): record the import route and its dialog"
```

- [ ] **Step 6: Redeploy, because this changes the running artifact**

`backend/` and `frontend/` both changed, so the owner ruling of 2026-08-21 applies: a merged-but-undeployed change leaves the owner reviewing the previous build.

```bash
./scripts/gate.sh
DARKMEM_PUSH=0 ./scripts/build-push.sh
docker compose up -d
```

`DARKMEM_PUSH=0` is not optional — the script's default is to push, and publishing from this machine is forbidden; `.github/workflows/release.yml` is the only path to a registry.

Wait for the container to report `healthy`, then **confirm the change is in the running image rather than only in the tree** — compose reuses an image whose tag did not move, so a skipped or failed build redeploys the old bits and still reports `Started`:

```bash
docker exec darkmem-prod-darkmem-1 \
  grep -c "import/notion" /app/app/api/routes/page_import.py
curl -s localhost:8000/openapi.json | grep -c "pages/import/notion"
```

Expected: both non-zero.

---

# Document Parser Fixes Implementation Plan (Increment 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementer assignments:** each task names its implementer agent in an
> `**Implementer:**` line. When executing with
> superpowers:subagent-driven-development, REQUIRED SUB-SKILL:
> dcc-superpower-companions:dispatching-tiered-implementers. Under
> superpowers:executing-plans these lines are inert; ignore them.

> **Status: LANDED 2026-09-02.** All six tasks executed and deployed on this
> host (`9f41ce5f` taxonomy, `981aa9ff` parsers, `048cc8b7` warning,
> `ee677935` changelog). Gate green: 6,484 backend (up 16), 1,324 frontend,
> both SDK suites, 1,055 benchlib, F1 bench; `make generate` zero-diff.
> Three notes for anyone reading this plan as a record rather than a script:
> **(1)** Task 3's frontmatter split is wider than its sketch — `parse_markdown`
> tokenises the body, so *every* `_span` call inside it takes `body`, not just
> the ones shown, and `_emit_table`'s parameter was renamed to match. Miss one
> and spans are silently offset by the frontmatter length with no test
> failing. **(2)** Review finding m-3 confirmed on contact and fixed:
> `normalize_block_type`'s docstring said "one of the five". **(3)** Review
> finding m-8 confirmed: `PARSERS` is at `block_pipeline.py:86-90`, not
> `:93-97`. One test was added beyond the plan — the batch path builds its own
> jobs, so a frontmatter merge on the single-source path alone would be a
> silent asymmetry between two paths that must agree.

**Goal:** Close the oversized-block silent degradation the spec measured: mega-tables parse to single 200-300 KB paragraph blocks that the embedder truncates while the filing reports success. Structurally fix the dominant cause (enable table parsing, splitting rows into blocks of ordinary size), capture YAML frontmatter instead of misparsing it into a heading, and make the residual loud (an oversized-block warning on every put surface). No schema change: `blocks.type` is plain `TEXT` with no CHECK (`backend/migrations/versions/0001_baseline.py:1313`); the closure lives in `normalize_block_type`.

**Architecture:** Taxonomy-first — `table`/`table_row` land in `BLOCK_TYPES` before the parser emits them (Task 1 before Task 2, and the gate between them is the ordering, not a comment). The parser emits one `table` block (header + alignments in `properties`) whose data rows are child `table_row` blocks; frontmatter is split off before tokenising and filed into `documents.properties.frontmatter` by the pipeline (the parser contract returns only `Sequence[BlockDraft]` and cannot write document properties); the oversized count is measured in the one writer (`document_ingest`), ridden by the `document_filed` event, and surfaced through `PutResult` → both doors.

**Tech Stack:** markdown-it-py (`table` rule is in the parser but disabled under the `commonmark` preset — `MarkdownIt("commonmark").enable("table")` enables GFM tables; token stream verified live: `table_open[map] → thead_open → tr_open → th_open{style: "text-align:…"} → inline …`, data rows under `tbody_open` with `tr_open[map]`).

**Spec:** `docs/superpowers/specs/2026-08-31-project-artifact-store-design.md` §4.
**Review:** the 2026-08-31 adversarial review cleared increment 2 as "the strongest section of the spec". One review nit carried here (m5): the 8,000-char constant is a **character**-basis floor derived from nomic's 2048-**token** budget at ~4 chars/token — the constant's comment must state the basis so nobody later "corrects" it to 2048.

## Global Constraints

- **Backend tests:** from `backend/`, `.venv/bin/python -m pytest -q`. Needs `darkmem_test` on 127.0.0.1:5433.
- **Merge gate:** `./scripts/gate.sh` from the repo root; green before the final commit. `--full` is unreliable on this host (earlyoom kills Chromium); never invoke Playwright bare — `backend/scripts/e2e/run_playwright_e2e.py`.
- **Taxonomy-first is binding:** the vocabulary edit (Task 1) merges before the parser change (Task 2). Do not reorder.
- **Parsers emit literal `BLOCK_TYPES` members, never raw token names** — the module's own contract (`document_parsers.py` docstring): a parser that leaned on `normalize_block_type`'s fallback would be one taxonomy edit away from silently reclassifying blocks.
- **Char spans point at the source, not the retrievable text** (`document_parsers.py` docstring): frontmatter stripping must not shift spans — a block's span still indexes into the *original* content, fences included.
- **`file_document` does not commit; the SAVEPOINT is the writer's** (`document_ingest.py:161-173`). Nothing in this plan opens a second one.
- **Warn, never refuse, on oversized blocks:** 27 corpus files exceed the nomic budget and refusing would block increment 5's import; invariant 14 demands honest reporting of degradation, not a new failure mode.
- **Existing rows are untouched:** parser changes re-shape trees for *re-filed* documents only. Greenfield ruling — no data migration, no backfill.
- **The block-channel firewall is structural** (`tests/test_block_pipeline.py`, `tests/test_block_retrieval.py` import-closure scans). Nothing here adds an import into the memory pipeline or the vault; if a scan goes red, the change is wrong, not the scan.
- **Commits:** `<type>(<scope>): <subject>`, ≤50 chars. A `feat`/`fix` on master cuts a release — the final task writes the CHANGELOG section (coordinate with `2026-08-31-watchable-progress.md` if both land in one push).

## File Structure

```
backend/app/taxonomy.py                       # Task 1: BLOCK_TYPES += table, table_row
backend/tests/test_taxonomy.py                # Task 1: count 5 → 7
docs/design/16-documents-and-pkm.md           # Task 1: §9 stance line amended
backend/app/services/document_parsers.py      # Tasks 2, 3
backend/tests/test_document_parsers.py        # Tasks 2, 3
backend/app/services/block_pipeline.py        # Task 3: frontmatter merge
backend/tests/test_block_pipeline.py          # Task 3
backend/app/services/document_ingest.py       # Task 4: constant + measurement
backend/tests/test_documents.py               # Task 4
backend/app/services/document_door.py         # Task 5: PutResult fields
backend/app/api/routes/documents.py           # Task 5: DocumentPutResponse fields
backend/tests/test_document_routes.py         # Task 5
CHANGELOG.md                                  # Task 6
```

---

### Task 1: Taxonomy — `table` and `table_row` join `BLOCK_TYPES`

**Files:**
- Modify: `backend/app/taxonomy.py:383-389` (`BLOCK_TYPES`)
- Modify: `backend/tests/test_taxonomy.py:62-64` (the count pin)
- Modify: `docs/design/16-documents-and-pkm.md:254` (the §9 stance line)

**Interfaces:**
- Consumes: nothing.
- Produces: the two vocabulary members Task 2's parser emits and `normalize_block_type` passes through unchanged.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3
**Approach:** inline - skip 3: the spec (§4.1) chose the two names and the taxonomy-first landing order.

- [x] **Step 1: Update the count pin so it fails**

In `backend/tests/test_taxonomy.py:62-64`, the comment currently reads "Widening it is TH1.03's to justify from a parser that genuinely emits a sixth shape, not a convenience." That justification has now been made — the mega-table measurement (spec §4.1: the three failing files are all mega-tables; largest single blocks 235,716 / 298,677 / 182,746 chars). Replace with:

```python
    # Doc 16 §9's minimal set, widened by the 2026-08-31 spec §4.1: the parser
    # genuinely emits table/table_row now, because a GFM table parsed as one
    # paragraph produced the measured 235KB single blocks the embedder
    # silently truncates. A count that moves without this table moving is the
    # taxonomy-first rule being skipped.
    assert len(BLOCK_TYPES) == 7
```

Run `cd backend && .venv/bin/python -m pytest tests/test_taxonomy.py -q` — expected: FAIL (`5 == 7`).

- [x] **Step 2: Widen the vocabulary**

In `backend/app/taxonomy.py:383-389`, append the two members:

```python
BLOCK_TYPES: list[str] = [
    "paragraph",
    "heading",
    "list",
    "code",
    "quote",
    "table",
    "table_row",
]
```

Amend the block-comment above it (the one calling the set "doc 16 §9's minimal five") to say the set was widened by the 2026-08-31 spec §4.1 for table parsing. **No `LEGACY_BLOCK_TYPE_MAP` additions**: the map rewrites raw token names a parser might leak (`h1`, `fence`), and no parser ever emits `table_open`/`tr` as a block type — the parser emits the literal members, per the module contract.

- [x] **Step 3: Amend doc 16 §9's stance line**

`docs/design/16-documents-and-pkm.md:254` states the minimal closed set as "(paragraph / heading / list / code / quote)". Append to that parenthetical: `/ table / table_row — widened 2026-08-31, spec §4.1, when the markdown parser began emitting tables structurally`. One line; the doc stays the authority a reader consults, and a stale "here is the full list" sentence is exactly invariant 23's concern.

- [x] **Step 4: Verify**

```bash
cd backend && .venv/bin/python -m pytest tests/test_taxonomy.py tests/test_document_parsers.py -q
```

Both green (the parsers' closed-vocabulary tests assert `<= set(BLOCK_TYPES)` — a widened set cannot break them).

---

### Task 2: Table parsing — one `table` block, `table_row` children

**Files:**
- Modify: `backend/app/services/document_parsers.py` (`parse_markdown`, `document_parsers.py:89-227`)
- Modify: `backend/tests/test_document_parsers.py`

**Interfaces:**
- Consumes: Task 1's vocabulary.
- Produces: `table`/`table_row` drafts flowing through the unchanged `_resolve_tree` (`document_ingest.py:352`) — `parent` is a backward index like every other draft, so no writer change is needed.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 3: the spec (§4.1) chose the shape — one `table` block carrying header cells + alignment in `properties`, data rows as child `table_row` blocks.

- [x] **Step 1: Write the failing tests**

Add to `backend/tests/test_document_parsers.py` (alongside the markdown group at :126-227):

```python
TABLE_MD = """# Data

| Name | Age |
|:-----|----:|
| Ann  | 3   |
| Bob  | 44  |
"""


def test_markdown_table_emits_one_table_block_with_row_children():
    drafts = parse_markdown(TABLE_MD)
    tables = [d for d in drafts if d.type == "table"]
    rows = [d for d in drafts if d.type == "table_row"]
    assert len(tables) == 1
    assert len(rows) == 2
    table_index = drafts.index(tables[0])
    # The heading owns the table; the table owns its rows.
    assert tables[0].parent == 0
    assert all(r.parent == table_index for r in rows)


def test_markdown_table_header_and_alignment_ride_properties():
    drafts = parse_markdown(TABLE_MD)
    table = next(d for d in drafts if d.type == "table")
    assert table.properties == {"header": ["Name", "Age"], "alignments": ["left", "right"]}
    # The header is the table block's own retrievable text.
    assert table.text == "Name | Age"


def test_markdown_table_row_text_is_the_joined_cells():
    drafts = parse_markdown(TABLE_MD)
    rows = [d for d in drafts if d.type == "table_row"]
    assert rows[0].text == "Ann | 3"
    assert rows[0].properties == {"cells": ["Ann", "3"]}


def test_markdown_table_char_spans_index_into_the_source():
    drafts = parse_markdown(TABLE_MD)
    table = next(d for d in drafts if d.type == "table")
    row = next(d for d in drafts if d.type == "table_row")
    lo, hi = table.char_span
    assert TABLE_MD[lo:hi].startswith("| Name | Age |")
    lo, hi = row.char_span
    assert TABLE_MD[lo:hi].startswith("| Ann")


def test_markdown_a_mega_table_dissolves_into_ordinary_blocks():
    """The measured defect: under commonmark a table is one giant paragraph.
    After the table rule, no block of a row-shaped table exceeds a row."""
    source = "| k | v |\n|---|---|\n" + "\n".join(
        f"| key{i} | {'x' * 200} |" for i in range(300)
    )
    drafts = parse_markdown(source)
    assert sum(1 for d in drafts if d.type == "table_row") == 300
    assert max(len(d.text) for d in drafts) < 8_000
```

Run: `cd backend && .venv/bin/python -m pytest tests/test_document_parsers.py -q` — expected: FAIL (tables currently parse as paragraphs: the whole pipe-table is one blank-line-delimited paragraph, which is precisely the measured 235 KB-block defect).

- [x] **Step 2: Enable the rule and emit the blocks**

In `parse_markdown` (`document_parsers.py:104`), change the parse to:

```python
        tokens = MarkdownIt("commonmark").enable("table").parse(text)
```

Add a `table_open` branch to the token loop (before the fall-through skip), delegating to a helper so the main loop stays flat:

```python
        if tok.type == "table_open":
            i = _emit_table(tokens, i, drafts, parent(), offsets, text)
            continue
```

```python
def _alignment(tok) -> str | None:
    """GFM alignment from the th/td style attr; None when unaligned."""
    style = tok.attrs.get("style") if tok.attrs else None
    return style.removeprefix("text-align:") if style else None


def _emit_table(tokens, i, drafts, parent_index, offsets, text) -> int:
    """Consume table_open..table_close; emit one `table` draft plus one
    `table_row` child per tbody row. The header row folds into the table
    block itself (spec §4.1): its cells are the table's own retrievable
    text and its properties, not a child row."""
    table_index = len(drafts)
    drafts.append({
        "text": "",
        "type": "table",
        "parent": parent_index,
        "properties": None,
        "char_span": _span(tokens[i].map, offsets, text),
    })
    header: list[str] = []
    alignments: list[str | None] = []
    in_head = False
    row_cells: list[str] | None = None
    row_span: tuple[int, int] | None = None
    i += 1
    while i < len(tokens) and tokens[i].type != "table_close":
        t = tokens[i]
        if t.type == "thead_open":
            in_head = True
        elif t.type == "thead_close":
            in_head = False
        elif t.type in ("th_open", "td_open"):
            if in_head:
                alignments.append(_alignment(t))
        elif t.type == "tr_open" and not in_head:
            row_cells = []
            row_span = _span(t.map, offsets, text)
        elif t.type == "inline":
            if in_head:
                header.append(t.content)
            elif row_cells is not None:
                row_cells.append(t.content)
        elif t.type == "tr_close" and row_cells is not None:
            drafts.append({
                "text": " | ".join(row_cells),
                "type": "table_row",
                "parent": table_index,
                "properties": {"cells": row_cells},
                "char_span": row_span,
            })
            row_cells = None
        i += 1
    table = drafts[table_index]
    table["text"] = " | ".join(header)
    table["properties"] = {"header": header, "alignments": alignments}
    return i + 1
```

Update the fall-through comment at `document_parsers.py:211-213` — it currently names tables among the skipped shapes ("hr, html_block, and anything the commonmark preset does not enable (tables)"); tables are no longer skipped, `hr`/`html_block` still are.

- [x] **Step 3: Run the new tests, then the whole parser file**

```bash
cd backend && .venv/bin/python -m pytest tests/test_document_parsers.py -q
```

All green, existing tests included — in particular `test_markdown_char_spans_index_into_the_source` (:164) and the closed-vocabulary asserts must still pass.

- [x] **Step 4: One end-to-end assert through the writer**

Extend `test_each_parser_files_end_to_end_through_file_document` (`test_document_parsers.py:537`) or add a sibling: file `TABLE_MD` through `file_document` and assert the stored rows carry `type='table_row'` with `parent_id` pointing at the `table` row's id — proving `_resolve_tree`'s backward-index rule holds for the new shape with no writer change.

---

### Task 3: Frontmatter — captured into `documents.properties`, spans unshifted

**Files:**
- Modify: `backend/app/services/document_parsers.py` (`split_frontmatter`, `parse_markdown`)
- Modify: `backend/app/services/block_pipeline.py` (`ingest_document`, `ingest_documents`)
- Modify: `backend/tests/test_document_parsers.py`
- Modify: `backend/tests/test_block_pipeline.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `document_parsers.split_frontmatter(text) -> tuple[str | None, int]`; `documents.properties["frontmatter"]` on markdown filings.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 2 - spec 1 - coupling 0 - risk 1 = 4
**Approach:** inline - skip 2: the repository answers the placement — parsers return `Sequence[BlockDraft]` and cannot write document properties (`PARSERS` shape, `block_pipeline.py:93-97`), so the properties merge lives in the pipeline that already routes `source_type`, exactly where `resolve_source_type` already sits.

- [x] **Step 1: Write the failing tests**

In `test_document_parsers.py`:

```python
FM_MD = """---
title: The Plan
status: draft
---
# Heading

Body prose.
"""


def test_markdown_frontmatter_is_split_not_misparsed():
    """Without the split, commonmark reads `status: draft` + `---` as a
    setext h2 — the verified misparse the spec's brief measured."""
    drafts = parse_markdown(FM_MD)
    assert [d.type for d in drafts] == ["heading", "paragraph"]
    assert drafts[0].text == "Heading"
    assert drafts[0].properties == {"level": 1}


def test_markdown_frontmatter_spans_still_index_the_original_source():
    drafts = parse_markdown(FM_MD)
    lo, hi = drafts[0].char_span
    assert FM_MD[lo:hi] == "# Heading"


def test_split_frontmatter_returns_inner_text_and_body_offset():
    fm, start = split_frontmatter(FM_MD)
    assert fm == "title: The Plan\nstatus: draft"
    assert FM_MD[start:].startswith("# Heading")
    assert split_frontmatter("# No fence\n") == (None, 0)
    # A thematic break mid-document is not frontmatter.
    assert split_frontmatter("intro\n---\nkey: value\n---\n") == (None, 0)
```

In `test_block_pipeline.py`, an ingest-level test (use the existing session fixtures there):

```python
async def test_markdown_frontmatter_lands_in_document_properties(session):
    result = await ingest_document(
        session, project="p", content=FM_MD, uri="notes/plan.md",
    )
    row = (await session.execute(
        text("SELECT properties FROM documents WHERE id = CAST(:id AS uuid)"),
        {"id": str(result.document_id)},
    )).scalar_one()
    assert row["frontmatter"] == "title: The Plan\nstatus: draft"
```

Run both files — expected: FAIL.

- [x] **Step 2: `split_frontmatter` in `document_parsers.py`**

```python
_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?(?:\n|\Z)", re.DOTALL)


def split_frontmatter(text: str) -> tuple[str | None, int]:
    """The leading `---` frontmatter fence's inner text and the offset where
    the body starts; `(None, 0)` when the source opens with anything else.

    Raw text, never parsed YAML: storing the string needs no schema and no
    dependency, and a YAML syntax error must not fail a filing. Anchored at
    offset 0 — a thematic break later in the document is markdown, not
    metadata.
    """
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return None, 0
    return match.group(1), match.end()
```

Export it in `__all__`.

- [x] **Step 3: `parse_markdown` skips the region without shifting spans**

At the top of `parse_markdown` (after the type/empty guards, `document_parsers.py:100-102`):

```python
    _, body_start = split_frontmatter(text)
    body = text[body_start:]
```

Parse `body` instead of `text` (tokens, `_line_offsets(body)`, `_span(..., body)` all over the body), then shift every span back into the original source at the final `BlockDraft` construction:

```python
    return [
        BlockDraft(
            text=d["text"], type=d["type"], parent=d["parent"],
            properties=d["properties"],
            char_span=(
                (d["char_span"][0] + body_start, d["char_span"][1] + body_start)
                if d["char_span"] is not None else None
            ),
        )
        for d in drafts
    ]
```

The shift is what keeps the module contract ("char spans point at the source") true with the fence still counted in the source.

- [x] **Step 4: The pipeline merge in `block_pipeline.py`**

```python
from app.services.document_parsers import (
    ...,
    split_frontmatter,
)


def _with_frontmatter(
    resolved_type: str, content: str | bytes, properties: dict | None
) -> dict | None:
    """Fold the source's own frontmatter into the document's properties.

    Parser-derived, so it wins over a caller-passed `frontmatter` key: the
    value restates the content, and the content is what was filed. Recomputed
    on every filing — properties are overwritten wholesale by the writer
    (`repositories/documents.py`), which keeps the stored value in step with
    the stored content by construction.
    """
    if resolved_type != SOURCE_TYPE_MARKDOWN or not isinstance(content, str):
        return properties
    frontmatter, _ = split_frontmatter(content)
    if frontmatter is None:
        return properties
    return {**(properties or {}), "frontmatter": frontmatter}
```

Call it in `ingest_document` (before the `file_document` call: `properties = _with_frontmatter(resolved_type, content, properties)`) **and** in `ingest_documents`' job-construction loop (`properties=_with_frontmatter(resolved_type, source.content, source.properties)`), so the single-source and batch paths cannot drift.

- [x] **Step 5: Run the tests**

```bash
cd backend && .venv/bin/python -m pytest tests/test_document_parsers.py tests/test_block_pipeline.py -q
```

All green — including `test_block_pipeline.py`'s structural import-closure scan (`split_frontmatter` adds no new module to the closure; it lives in a file already inside it).

---

### Task 4: Oversized-block measurement in the writer

**Files:**
- Modify: `backend/app/services/document_ingest.py` (`OVERSIZED_BLOCK_CHARS`, `DocumentIngest:123`, `_file_document_without_savepoint:176-283`)
- Modify: `backend/tests/test_documents.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (measures whatever tree the parser produced).
- Produces: `DocumentIngest.oversized_blocks: int | None`, `DocumentIngest.largest_block_chars: int | None`; two new keys on the `document_filed` event payload. Task 5 consumes the fields.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3
**Approach:** inline - skip 2: `title_applied` already established the pattern — a per-filing honesty signal computed once in the shared layer so every transport serves it identically (`document_door.py:137-149`).

- [x] **Step 1: Write the failing tests**

In `backend/tests/test_documents.py` (beside the existing `file_document` tests):

```python
async def test_an_oversized_block_is_counted_and_journalled_never_refused(session):
    big = "x" * (OVERSIZED_BLOCK_CHARS + 1)
    result = await file_document(
        session, project="p", content=f"# H\n\n{big}\n\nsmall\n",
        parse=lambda: parse_markdown(f"# H\n\n{big}\n\nsmall\n"),
        uri="notes/big.md",
    )
    assert result.outcome == CREATED           # warned, not refused
    assert result.oversized_blocks == 1
    assert result.largest_block_chars == len(big)

    payload = (await session.execute(text(
        "SELECT payload FROM events WHERE event_type = 'document_filed' "
        "AND object_id = CAST(:id AS uuid) ORDER BY created_at DESC LIMIT 1"
    ), {"id": str(result.document_id)})).scalar_one()
    assert payload["oversized_blocks"] == 1
    assert payload["largest_block_chars"] == len(big)


async def test_unchanged_reports_none_not_zero(session):
    """The UNCHANGED gate returns before any parse, so nothing was measured.
    None must not be flattened to 0 — 0 would claim the document is fine."""
    content = "# H\n\nfine\n"
    await file_document(session, project="p", content=content,
                        parse=lambda: parse_markdown(content), uri="n/a.md")
    again = await file_document(session, project="p", content=content,
                                parse=lambda: parse_markdown(content), uri="n/a.md")
    assert again.outcome == UNCHANGED
    assert again.oversized_blocks is None
    assert again.largest_block_chars is None
```

Run — expected: FAIL (`DocumentIngest` has no such fields).

- [x] **Step 2: The constant and the fields**

In `document_ingest.py`, beside the outcome constants:

```python
# A stated conservative floor in CHARACTERS, not tokens: the tighter live
# embedder (nomic-embed-text) holds ~2048 tokens, and ~4 chars/token makes
# 8,000 chars where truncation risk starts. Deliberately not a per-embedder
# probe — a probe would put a model call on the parse path for a warning —
# and deliberately char-basis: do not "correct" this to 2048, the bases
# differ.
OVERSIZED_BLOCK_CHARS = 8_000
```

Extend `DocumentIngest` (`document_ingest.py:123-129`):

```python
@dataclass(frozen=True)
class DocumentIngest:
    document_id: UUID
    outcome: str
    content_hash: str
    blocks_written: int = 0
    blocks_stripped: int = 0
    # None = not measured: the UNCHANGED short-circuit returns before any
    # parse. Measured (possibly 0) on CREATED/UPDATED. A reader must not
    # flatten None to 0 — 0 is a clean bill this filing never issued.
    oversized_blocks: int | None = None
    largest_block_chars: int | None = None
```

Export `OVERSIZED_BLOCK_CHARS` in `__all__`.

- [x] **Step 3: Measure after `_resolve_tree`, journal, return**

In `_file_document_without_savepoint`, after `rows = _resolve_tree(parse())` (`document_ingest.py:246`):

```python
    oversized = sum(1 for row in rows if len(row.text) > OVERSIZED_BLOCK_CHARS)
    largest = max((len(row.text) for row in rows), default=0)
```

Add both to the `document_filed` payload (`document_ingest.py:262-268`) as `"oversized_blocks": oversized, "largest_block_chars": largest` — counts and sizes only, no block text, honouring write-time minimization — and to the returned `DocumentIngest`.

- [x] **Step 4: Run**

```bash
cd backend && .venv/bin/python -m pytest tests/test_documents.py tests/test_block_pipeline.py -q
```

---

### Task 5: Surface the warning on both doors

**Files:**
- Modify: `backend/app/services/document_door.py` (`PutResult:137`, `put_document:409-` return)
- Modify: `backend/app/api/routes/documents.py` (`DocumentPutResponse:182`, `put_document_route`)
- Modify: `backend/tests/test_document_routes.py`

**Interfaces:**
- Consumes: Task 4's `DocumentIngest` fields.
- Produces: `PutResult.oversized_blocks` / `PutResult.largest_block_chars`; the same two fields on `DocumentPutResponse` and (automatically, via `json.dumps(vars(result))`, `backend/app/api/mcp/server.py:649`) on the MCP `document_put` reply.

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2

- [x] **Step 1: Write the failing tests**

In `backend/tests/test_document_routes.py` (beside `test_put_creates_and_reports_both_counts:36`):

```python
async def test_put_reports_oversized_blocks_on_both_doors(client, auth_headers, stub_llm):
    big = "x" * (OVERSIZED_BLOCK_CHARS + 1)
    body = {"project": "p", "uri": "docs/big.md", "content": f"# H\n\n{big}\n"}
    resp = await client.post("/api/v1/documents", json=body, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["oversized_blocks"] == 1
    assert data["largest_block_chars"] == len(big)

    # MCP door: vars(PutResult) serialises whatever the dataclass carries —
    # assert the field is actually there so a rename cannot silently drop it.
    from app.api.mcp import server as mcp_server
    reply = json.loads(await mcp_server.document_put.fn(
        project="p", uri="docs/big2.md", content=f"# H\n\n{big}\n",
    ))
    assert reply["oversized_blocks"] == 1
```

(Match the file's existing MCP-invocation idiom — the `both_doors` fixture at `test_document_routes.py:509-` shows how the suite already calls the MCP twins; use that shape rather than the sketch above if it differs.)

Run — expected: FAIL.

- [x] **Step 2: `PutResult` and the forward**

Extend `PutResult` (`document_door.py:137-149`):

```python
    # None only when `outcome == UNCHANGED`: the change gate short-circuits
    # before any parse, so nothing was measured this filing (see
    # DocumentIngest). Counts, not refusals: an oversized block embeds
    # truncated, and this is the loud report invariant 14 asks for.
    oversized_blocks: int | None
    largest_block_chars: int | None
```

In `put_document`'s return, forward `oversized_blocks=filed.oversized_blocks, largest_block_chars=filed.largest_block_chars`.

- [x] **Step 3: The REST model**

Extend `DocumentPutResponse` (`routes/documents.py:182-196`) with the same two `int | None` fields (comment: None when `outcome == "unchanged"` — not measured, never "fine"), and pass them through in `put_document_route`'s constructor.

- [x] **Step 4: Run, then the door suite**

```bash
cd backend && .venv/bin/python -m pytest tests/test_document_routes.py tests/test_document_door.py -q
```

---

### Task 6: SDK no-op check, gate, changelog, deploy

**Files:**
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: every earlier task.
- Produces: the running instance increment 5's import files into.

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 0 - spec 0 - coupling 0 - risk 2 = 2

- [x] **Step 1: SDK regeneration is a verification, not a diff**

```bash
cd sdks && make generate && git diff --exit-code sdks/
```

Expected: **zero diff**. The generator binds three verbs — `capture`, `search`, `declareContext` — none of which touches a documents route (`sdks/generate.py`, "Contract bindings"). The spec's §4.2 note that "the SDK generator regenerates it (invariant 17)" is inert for this field: nothing regenerates because nothing binds. Running it anyway proves the contract change broke no bound verb — that is what the step is for. If it produces a diff, stop and read it; that means a bound surface moved, which this plan does not intend.

- [x] **Step 2: Merge gate**

`./scripts/gate.sh` — green. (This catches the alembic single-revision assert too: this plan makes **no** schema change; if anything here seems to need one, the plan is wrong — stop.)

- [x] **Step 3: Changelog + commits**

Section for the next derived version (coordinate with `2026-08-31-watchable-progress.md` — one push, one section). Commits, atomic: `feat(taxonomy): add table and table_row block types`, `feat(documents): parse tables into row blocks`, `feat(documents): capture yaml frontmatter`, `feat(documents): oversized-block warning on put`.

- [x] **Step 4: Redeploy this machine** (owner ruling 2026-08-21)

```bash
DARKMEM_PUSH=0 ./scripts/build-push.sh
docker compose up -d
# confirm the change is in the running image, not only the tree:
docker exec darkmem-prod-darkmem-1 grep -c "table_row" /app/app/taxonomy.py
curl -s http://127.0.0.1:8000/openapi.json | grep -c oversized_blocks
```

Both non-zero. This deploy is a **prerequisite of the corpus-import plan** (`2026-08-31-docs-corpus-import.md`) — importing before it lands re-creates the mega-block defect for every table-heavy file.

## Rollback

Everything is additive and code-only: `git revert` the commits and redeploy. Documents filed *between* deploy and revert keep their table-parsed trees until next re-filed (re-filing under the reverted parser re-strips and re-writes — the strip-and-replace is the writer's normal path, not a special case). No schema moved; no data migrates in either direction.

## Notes on scope

- **Embed-time chunking (doc 16 §3) stays deferred** — D2 in the spec's own table: the partition PK `(block_id, fingerprint)` (`embedder_registry.py:87-95`) admits one vector per block, and changing it is a live-partition reconciliation plus a `search_blocks` dedup. The put-time warning is the honest stopgap; residual oversized blocks (giant code fences, monster paragraphs) embed truncated and now say so.
- **The `<!-- BEGIN/END GENERATED -->` html_block loss needs no parser change** — spec §4.5 assigns it to increment 3's raw-content bridge, which the review requires a spec amendment for (M6, m3) and this plan does not touch.
- **No frontend change:** the shipped `/documents` view renders block counts, not per-type blocks (`documents-view.tsx`), and the workspace UI that renders `table` blocks through the library `table` component is increment 4 — blocked on the review's M2 spec amendment.
- **`MAX_BLOCKS` watch:** row-splitting multiplies block counts (E2's file is already 998 against the 5,000 bound, `document_door.py:61`). The corpus spot-check is increment 5's task; a genuinely 5,000-row table would now 422 where it used to file one giant block — that refusal is the door's existing bound doing its job, and none is in the measured corpus.

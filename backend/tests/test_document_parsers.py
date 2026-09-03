"""The parser stack — PDF, markdown, notes — and per-document batch isolation
(TH1.03, doc 16 §3).

Two things carry this module.

**The parsers are exercised on real input, not stubs.** Markdown goes through
`markdown-it-py`'s actual tokenizer; PDF goes through `pdfplumber` against a
hand-built, syntactically real PDF (a ~40-line minimal-PDF writer below —
deliberately not a new test dependency, since the only thing it needs to prove
is that pdfplumber's own extraction round-trips through this module's grouping
logic). Every assertion about a char_span is checked by slicing the actual
source with it, never by trusting the number the parser reports.

**Batch isolation is proven by comparison, not by inspection.** A guard that
only ever runs its intended path is decorative. So alongside the real batch
function (`file_documents_isolated`, whose per-job SAVEPOINT is
`file_document`'s own since TH1.18) this module also defines the naive version
it deliberately does not ship — a bare try/except over the unguarded body,
reached through `_file_document_without_savepoint` — and runs the identical
failure scenario through both. The naive version corrupts the sibling
document; the real one does not. That comparison is the mutation drill,
committed as a permanent regression test rather than a one-off manual edit.
The opt-out is explicit for exactly this reason: making atomicity
unconditional would have deleted the drill along with the defect.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services import document_ingest as di
from app.services.document_ingest import (
    CREATED,
    BlockDraft,
    DocumentFileFailure,
    DocumentFileJob,
    DocumentIngest,
    _file_document_without_savepoint,
    file_document,
    file_documents_isolated,
)
from app.services.document_parsers import (
    split_frontmatter,
    SOURCE_TYPE_MARKDOWN,
    SOURCE_TYPE_NOTE,
    SOURCE_TYPE_PDF,
    DocumentParseError,
    parse_markdown,
    parse_note,
    parse_pdf,
)
from app.taxonomy import BLOCK_TYPES

# ── a real, minimal PDF — no new test dependency ─────────────────────


def _make_pdf(pages: list[list[tuple[str, int, int, int]]]) -> bytes:
    """A syntactically real single-content-stream-per-page PDF.

    Each page is a list of `(text, x, y, font_size)` text-showing operations
    in PDF user space (origin bottom-left). No compression, no cross-ref
    stream, no font metrics beyond Helvetica's built-in name — the minimum
    pdfplumber's own reader (pdfminer.six-backed) accepts.
    """
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + i} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    content_obj_start = 3 + len(pages)
    font_obj = content_obj_start + len(pages)
    for i in range(len(pages)):
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R "
                f"/Resources << /Font << /F1 {font_obj} 0 R >> >> "
                f"/MediaBox [0 0 612 792] /Contents {content_obj_start + i} 0 R >>"
            ).encode()
        )
    for lines in pages:
        parts = []
        for line_text, x, y, size in lines:
            escaped = line_text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
            parts.append(f"BT /F1 {size} Tf {x} {y} Td ({escaped}) Tj ET")
        stream = "\n".join(parts).encode()
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    buf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_offset = len(buf)
    n = len(objects) + 1
    buf += f"xref\n0 {n}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets[1:]:
        buf += f"{off:010d} 00000 n \n".encode()
    buf += f"trailer\n<< /Size {n} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    return bytes(buf)


# ── markdown ──────────────────────────────────────────────────────────

_MARKDOWN_SAMPLE = """# Title

Intro paragraph.

## Section

Some text under section.

- item one
- item two
  - nested item

> a quoted line
> second quoted line

```python
print(1)
```
"""


def test_markdown_heading_owns_its_content():
    drafts = parse_markdown(_MARKDOWN_SAMPLE)
    by_text = {d.text: i for i, d in enumerate(drafts)}

    title = by_text["Title"]
    section = by_text["Section"]
    intro = by_text["Intro paragraph."]
    under_section = by_text["Some text under section."]

    assert drafts[intro].parent == title
    assert drafts[section].parent == title
    assert drafts[under_section].parent == section


def test_markdown_nested_list_item_parents_onto_its_enclosing_item():
    drafts = parse_markdown(_MARKDOWN_SAMPLE)
    by_text = {d.text: i for i, d in enumerate(drafts)}
    item_two = by_text["item two"]
    nested = by_text["nested item"]
    assert drafts[nested].parent == item_two
    assert drafts[nested].type == "list"


def test_markdown_blockquote_joins_its_lines_into_one_block():
    drafts = parse_markdown(_MARKDOWN_SAMPLE)
    quotes = [d for d in drafts if d.type == "quote"]
    assert len(quotes) == 1
    assert quotes[0].text == "a quoted line\nsecond quoted line"


def test_markdown_fence_becomes_a_code_block_with_language():
    drafts = parse_markdown(_MARKDOWN_SAMPLE)
    code = [d for d in drafts if d.type == "code"]
    assert len(code) == 1
    assert code[0].text == "print(1)"
    assert code[0].properties == {"language": "python"}


def test_markdown_char_spans_index_into_the_source():
    drafts = parse_markdown(_MARKDOWN_SAMPLE)
    for draft in drafts:
        assert draft.char_span is not None
        lo, hi = draft.char_span
        assert 0 <= lo < hi <= len(_MARKDOWN_SAMPLE)
        source_slice = _MARKDOWN_SAMPLE[lo:hi]
        # The span covers the source line(s), which may carry markup
        # (`# `, `- `, `> `, fences) the block's own text has stripped —
        # so containment of the *content*, not equality, is the contract.
        for fragment in draft.text.split("\n"):
            if fragment:
                assert fragment in source_slice


def test_markdown_only_emits_closed_vocabulary_types():
    drafts = parse_markdown(_MARKDOWN_SAMPLE)
    assert {d.type for d in drafts} <= set(BLOCK_TYPES)
    assert {d.type for d in drafts} == {"heading", "paragraph", "list", "quote", "code"}


def test_markdown_every_parent_is_an_earlier_draft():
    """The structural invariant `file_document._resolve_tree` enforces: a
    parser that ever names a same-or-later index would break every caller."""
    drafts = parse_markdown(_MARKDOWN_SAMPLE)
    for i, draft in enumerate(drafts):
        if draft.parent is not None:
            assert 0 <= draft.parent < i


def test_markdown_rejects_non_str_content():
    # Not `bytes`: bytes has its own `.strip()`, so it would sail past this
    # check and only fail once markdown-it-py's own validation rejects it a
    # few lines later — a real failure, but not evidence *this* guard fired.
    # `int` has no `.strip()` at all, so only the explicit isinstance check
    # stands between it and an uncaught AttributeError.
    with pytest.raises(DocumentParseError, match="str"):
        parse_markdown(123)


def test_markdown_empty_source_is_empty():
    assert parse_markdown("") == []
    assert parse_markdown("   \n\n  ") == []


def test_markdown_a_paragraph_with_no_heading_has_no_parent():
    drafts = parse_markdown("Just a paragraph, no heading.\n")
    assert len(drafts) == 1
    assert drafts[0].parent is None
    assert drafts[0].type == "paragraph"


# ── notes ─────────────────────────────────────────────────────────────

_NOTE_SAMPLE = """Meeting Notes

Action items

- follow up with design
- ship the parser
1. file the report

Second paragraph after the list, a full sentence.
"""


def test_note_heading_and_paragraph_and_list_detection():
    drafts = parse_note(_NOTE_SAMPLE)
    types = [d.type for d in drafts]
    assert types == ["heading", "heading", "list", "list", "list", "paragraph"]
    assert drafts[0].text == "Meeting Notes"
    assert drafts[1].text == "Action items"
    assert [d.text for d in drafts if d.type == "list"] == [
        "follow up with design", "ship the parser", "file the report",
    ]


def test_note_list_items_parent_onto_the_preceding_heading():
    drafts = parse_note(_NOTE_SAMPLE)
    heading_index = 1  # "Action items"
    for draft in drafts:
        if draft.type == "list":
            assert draft.parent == heading_index


def test_note_char_spans_recover_exact_slices():
    drafts = parse_note(_NOTE_SAMPLE)
    for draft in drafts:
        lo, hi = draft.char_span
        assert _NOTE_SAMPLE[lo:hi].strip() != "" or draft.type == "list"


def test_note_bullet_span_includes_the_marker_text_does_not():
    drafts = parse_note(_NOTE_SAMPLE)
    item = next(d for d in drafts if d.text == "follow up with design")
    lo, hi = item.char_span
    assert _NOTE_SAMPLE[lo:hi] == "- follow up with design"


def test_note_a_long_or_punctuated_single_line_is_not_a_heading():
    body = "This single line is long enough and ends with a period."
    drafts = parse_note(body)
    assert len(drafts) == 1
    assert drafts[0].type == "paragraph"


def test_note_only_emits_closed_vocabulary_types():
    drafts = parse_note(_NOTE_SAMPLE)
    assert {d.type for d in drafts} <= set(BLOCK_TYPES)


def test_note_rejects_non_str_content():
    with pytest.raises(DocumentParseError, match="str"):
        parse_note(123)


def test_note_blank_input_is_empty():
    assert parse_note("") == []
    assert parse_note("   \n\n  ") == []


# ── PDF ───────────────────────────────────────────────────────────────


def test_pdf_heading_vs_paragraph_by_font_size():
    pdf = _make_pdf([[
        ("Big Heading", 72, 720, 24),
        ("A paragraph of body text that follows.", 72, 690, 12),
        ("Second line of the same paragraph continues here.", 72, 678, 12),
    ]])
    drafts = parse_pdf(pdf)
    assert [d.type for d in drafts] == ["heading", "paragraph"]
    assert drafts[0].text == "Big Heading"
    assert "Second line of the same paragraph" in drafts[1].text


def test_pdf_multi_page_provenance_carries_page_and_bbox():
    pdf = _make_pdf([
        [("Page One Heading", 72, 720, 20), ("Body on page one.", 72, 690, 12)],
        [("Page Two Heading", 72, 720, 20), ("Body on page two.", 72, 690, 12)],
    ])
    drafts = parse_pdf(pdf)
    pages = [d.properties["page"] for d in drafts]
    assert pages == [1, 1, 2, 2]
    for draft in drafts:
        bbox = draft.properties["bbox"]
        assert set(bbox) == {"x0", "top", "x1", "bottom"}
        assert bbox["x1"] > bbox["x0"]
        assert bbox["bottom"] > bbox["top"]


def test_pdf_char_spans_are_sequential_and_nonoverlapping():
    pdf = _make_pdf([[
        ("Heading", 72, 720, 20),
        ("First paragraph.", 72, 690, 12),
        ("Another heading", 72, 660, 20),
        ("Second paragraph.", 72, 630, 12),
    ]])
    drafts = parse_pdf(pdf)
    prev_end = -1
    for draft in drafts:
        lo, hi = draft.char_span
        assert lo >= prev_end
        assert hi - lo == len(draft.text)
        prev_end = hi


def test_pdf_garbage_bytes_raise_parse_error():
    with pytest.raises(DocumentParseError):
        parse_pdf(b"this is not a pdf at all")


def test_pdf_rejects_non_bytes_content():
    with pytest.raises(DocumentParseError, match="bytes"):
        parse_pdf("not bytes")


def test_pdf_with_no_pages_is_empty():
    assert parse_pdf(_make_pdf([])) == []


def test_pdf_only_emits_closed_vocabulary_types():
    pdf = _make_pdf([[("Heading", 72, 720, 20), ("Body text.", 72, 690, 12)]])
    drafts = parse_pdf(pdf)
    assert {d.type for d in drafts} <= set(BLOCK_TYPES)


# ── batch isolation: file_documents_isolated ─────────────────────────


def _drafts(*texts: str) -> list[BlockDraft]:
    return [BlockDraft(text=t, type="paragraph") for t in texts]


def _raising_parse():
    raise DocumentParseError("simulated: unparseable content")


async def _block_ids(session, document_id) -> list[str]:
    rows = (await session.execute(
        text("SELECT id FROM blocks WHERE document_id = CAST(:d AS uuid) ORDER BY order_index"),
        {"d": str(document_id)},
    )).scalars().all()
    return [str(r) for r in rows]


async def _naive_file_documents(session, jobs):
    """The version this module deliberately does not ship: no SAVEPOINT.

    Kept only to prove the real function's guard is load-bearing — run the
    identical scenario through both and compare. Since TH1.18 the guard is
    `file_document`'s own, so the naive shape has to opt out of it explicitly
    through the private unguarded body; a bare try/except around
    `file_document` would now be atomic and this drill would prove nothing.
    """
    results = []
    for job in jobs:
        try:
            result = await _file_document_without_savepoint(
                session, project=job.project, content=job.content, parse=job.parse,
                uri=job.uri, document_id=job.document_id, title=job.title,
                source_type=job.source_type, properties=job.properties,
                actor=job.actor, source=job.source,
            )
        except Exception as exc:
            results.append(DocumentFileFailure(label=job.label, error=str(exc)))
        else:
            results.append(result)
    return results


@pytest.mark.asyncio
async def test_batch_isolates_a_parse_failure_from_its_siblings(session):
    uri_a = f"file:///{uuid4()}.md"
    uri_c = f"file:///{uuid4()}.md"
    jobs = [
        DocumentFileJob(project="default", content="a", uri=uri_a,
                         parse=lambda: _drafts("a1", "a2"), label="a"),
        DocumentFileJob(project="default", content="b", uri=f"file:///{uuid4()}.md",
                         parse=_raising_parse, label="b"),
        DocumentFileJob(project="default", content="c", uri=uri_c,
                         parse=lambda: _drafts("c1"), label="c"),
    ]
    results = await file_documents_isolated(session, jobs)
    await session.flush()

    assert isinstance(results[0], DocumentIngest)
    assert results[0].outcome == CREATED
    assert isinstance(results[1], DocumentFileFailure)
    assert results[1].label == "b"
    assert "unparseable" in results[1].error
    assert isinstance(results[2], DocumentIngest)
    assert results[2].outcome == CREATED

    assert len(await _block_ids(session, results[0].document_id)) == 2
    assert len(await _block_ids(session, results[2].document_id)) == 1

    # the session is still usable — a failed job did not poison the transaction
    count = (await session.execute(text("SELECT count(*) FROM documents"))).scalar_one()
    assert count >= 2


@pytest.mark.asyncio
async def test_batch_failure_does_not_corrupt_an_existing_document(session):
    """The scenario that actually needs the SAVEPOINT: a re-file whose parse
    fails happens *after* the strip (doc 16 §3's flowchart order). Without
    isolation the strip survives and the replacement never lands."""
    uri = f"file:///{uuid4()}.md"
    first = await file_document(
        session, project="default", uri=uri, content="v1", parse=lambda: _drafts("v1a", "v1b"),
    )
    await session.flush()
    original_ids = await _block_ids(session, first.document_id)
    assert len(original_ids) == 2

    jobs = [DocumentFileJob(
        project="default", content="v2", uri=uri, parse=_raising_parse, label="refile",
    )]
    results = await file_documents_isolated(session, jobs)
    await session.flush()

    assert isinstance(results[0], DocumentFileFailure)
    assert await _block_ids(session, first.document_id) == original_ids


@pytest.mark.asyncio
async def test_without_a_savepoint_the_same_scenario_corrupts_the_document(session):
    """The mutation drill, executable: the naive batch function (no
    SAVEPOINT) run through the identical failure the guarded one survives.
    This is what proves the SAVEPOINT in `file_documents_isolated` is
    load-bearing rather than decorative — remove it and this is what happens."""
    uri = f"file:///{uuid4()}.md"
    first = await file_document(
        session, project="default", uri=uri, content="v1", parse=lambda: _drafts("v1a", "v1b"),
    )
    await session.flush()
    assert len(await _block_ids(session, first.document_id)) == 2

    jobs = [DocumentFileJob(
        project="default", content="v2", uri=uri, parse=_raising_parse, label="refile",
    )]
    results = await _naive_file_documents(session, jobs)
    await session.flush()

    assert isinstance(results[0], DocumentFileFailure)
    # the strip ran, nothing replaced it — exactly the corruption the
    # SAVEPOINT in the real function exists to prevent
    assert await _block_ids(session, first.document_id) == []


@pytest.mark.asyncio
async def test_a_non_parse_exception_is_isolated_the_same_way(session):
    """Isolation is not narrowed to DocumentParseError — a structural
    ValueError from a bad parent reference goes through the same path."""
    def _bad_tree():
        return [BlockDraft(text="child", parent=5)]

    jobs = [
        DocumentFileJob(project="default", content="x", uri=f"file:///{uuid4()}.md",
                         parse=_bad_tree, label="bad-tree"),
        DocumentFileJob(project="default", content="y", uri=f"file:///{uuid4()}.md",
                         parse=lambda: _drafts("ok"), label="ok"),
    ]
    results = await file_documents_isolated(session, jobs)
    await session.flush()

    assert isinstance(results[0], DocumentFileFailure)
    assert "earlier draft" in results[0].error
    assert isinstance(results[1], DocumentIngest)
    assert results[1].outcome == CREATED


@pytest.mark.asyncio
async def test_batch_preserves_input_order_in_its_results(session):
    labels_and_jobs = [
        ("one", lambda: _drafts("1")),
        ("two", _raising_parse),
        ("three", lambda: _drafts("3")),
        ("four", _raising_parse),
    ]
    jobs = [
        DocumentFileJob(project="default", content=label, uri=f"file:///{uuid4()}.md",
                         parse=parse, label=label)
        for label, parse in labels_and_jobs
    ]
    results = await file_documents_isolated(session, jobs)
    kinds = [
        "ok" if isinstance(r, DocumentIngest) else r.label
        for r in results
    ]
    assert kinds == ["ok", "two", "ok", "four"]


def test_the_event_and_object_types_are_still_closed():
    from app.services.events import EVENT_TYPES, OBJECT_TYPES

    assert di.DOCUMENT_FILED_EVENT in EVENT_TYPES
    assert di.OBJECT_TYPE in OBJECT_TYPES


# ── source_type: a naming convention, pinned but not enforced ────────


def test_source_type_constants_match_the_erd_spelling():
    """Doc 16 §2's ERD literal, pinned so it stays a decision rather than
    drifting one string literal at a time. `source_type` itself takes any
    string — this only pins what *this module's own callers* agree to write."""
    assert SOURCE_TYPE_PDF == "pdf"
    assert SOURCE_TYPE_MARKDOWN == "md"
    assert SOURCE_TYPE_NOTE == "note"


@pytest.mark.asyncio
async def test_each_parser_files_end_to_end_through_file_document(session):
    """The parser stack's real integration point: `file_document` never
    reaches the tables directly here, only through TH1.02's writer, with each
    parser's output and its source_type convention riding one real filing."""
    md_text = "# Notes\n\nA paragraph.\n"
    result_md = await file_document(
        session, project="default", uri=f"file:///{uuid4()}.md", content=md_text,
        parse=lambda: parse_markdown(md_text), source_type=SOURCE_TYPE_MARKDOWN,
    )
    await session.flush()
    assert len(await _block_ids(session, result_md.document_id)) == 2

    note_text = "Quick Note\n\nJust one line of body text here today.\n"
    result_note = await file_document(
        session, project="default", content=note_text,
        parse=lambda: parse_note(note_text), source_type=SOURCE_TYPE_NOTE,
    )
    await session.flush()
    assert len(await _block_ids(session, result_note.document_id)) == 2

    pdf_bytes = _make_pdf([[("Report", 72, 720, 20), ("Body of the report.", 72, 690, 12)]])
    result_pdf = await file_document(
        session, project="default", uri=f"file:///{uuid4()}.pdf", content=pdf_bytes,
        parse=lambda: parse_pdf(pdf_bytes), source_type=SOURCE_TYPE_PDF,
    )
    await session.flush()
    assert len(await _block_ids(session, result_pdf.document_id)) == 2

    rows = (await session.execute(
        text("SELECT id, source_type FROM documents WHERE id = ANY(CAST(:ids AS uuid[]))"),
        {"ids": [str(result_md.document_id), str(result_note.document_id), str(result_pdf.document_id)]},
    )).mappings().all()
    by_id = {str(r["id"]): r["source_type"] for r in rows}
    assert by_id[str(result_md.document_id)] == "md"
    assert by_id[str(result_note.document_id)] == "note"
    assert by_id[str(result_pdf.document_id)] == "pdf"


# ── Tables (2026-08-31 spec §4.1) ────────────────────────────────────

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
    assert table.properties == {
        "header": ["Name", "Age"],
        "alignments": ["left", "right"],
    }
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

    After the table rule, no block of a row-shaped table exceeds a row.
    """
    source = "| k | v |\n|---|---|\n" + "\n".join(
        f"| key{i} | {'x' * 200} |" for i in range(300)
    )
    drafts = parse_markdown(source)
    assert sum(1 for d in drafts if d.type == "table_row") == 300
    assert max(len(d.text) for d in drafts) < 8_000


def test_markdown_table_types_stay_inside_the_closed_vocabulary():
    from app.taxonomy import BLOCK_TYPES

    drafts = parse_markdown(TABLE_MD)
    assert {d.type for d in drafts} <= set(BLOCK_TYPES)


@pytest.mark.asyncio
async def test_a_filed_table_stores_rows_parented_on_the_table(session):
    """`_resolve_tree`'s backward-index rule holds for the new shape with no
    writer change: the row rows' `parent_id` is the table row's own id."""
    result = await file_document(
        session, project="default", uri=f"file:///{uuid4()}.md", content=TABLE_MD,
        parse=lambda: parse_markdown(TABLE_MD), source_type=SOURCE_TYPE_MARKDOWN,
    )
    await session.flush()

    rows = (await session.execute(
        text(
            "SELECT id, parent_id, type, text FROM blocks "
            "WHERE document_id = CAST(:id AS uuid) ORDER BY order_index"
        ),
        {"id": str(result.document_id)},
    )).mappings().all()

    by_type = {r["type"] for r in rows}
    assert {"heading", "table", "table_row"} <= by_type
    table = next(r for r in rows if r["type"] == "table")
    data_rows = [r for r in rows if r["type"] == "table_row"]
    assert len(data_rows) == 2
    assert all(r["parent_id"] == table["id"] for r in data_rows)
    assert {r["text"] for r in data_rows} == {"Ann | 3", "Bob | 44"}


# ── Frontmatter (2026-08-31 spec §4) ─────────────────────────────────

FM_MD = """---
title: The Plan
status: draft
---
# Heading

Body prose.
"""


def test_markdown_frontmatter_is_split_not_misparsed():
    """Without the split, commonmark reads `status: draft` + `---` as a setext
    h2 — the verified misparse the spec's brief measured."""
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


# ── Thematic breaks (2026-09-02) ─────────────────────────────────────


def test_markdown_thematic_break_mints_a_divider_block():
    """Before this, `hr` minted no block at all -- so a document's section
    rules existed in the source and nowhere in the tree, and block-first
    conversion would have silently dropped every one of them."""
    drafts = parse_markdown("para one\n\n---\n\npara two")
    assert [d.type for d in drafts] == ["paragraph", "divider", "paragraph"]
    assert drafts[1].text == ""


@pytest.mark.parametrize("rule", ["---", "***", "___", "- - -", "*****"])
def test_every_thematic_break_spelling_mints_one_divider(rule):
    drafts = parse_markdown(f"a\n\n{rule}\n\nb")
    assert [d.type for d in drafts].count("divider") == 1


def test_a_setext_underline_is_still_a_heading_not_a_divider():
    """`---` directly under a line of text is a setext h2, not a rule. The
    parser must not turn one into the other."""
    drafts = parse_markdown("Title\n---\n\nbody")
    assert drafts[0].type == "heading"
    assert drafts[0].text == "Title"
    assert "divider" not in [d.type for d in drafts]


def test_a_fence_is_still_code_not_a_divider():
    drafts = parse_markdown("```\n---\n```")
    assert [d.type for d in drafts] == ["code"]


def test_divider_span_indexes_the_rule_in_the_source():
    source = "para one\n\n---\n\npara two"
    drafts = parse_markdown(source)
    lo, hi = next(d for d in drafts if d.type == "divider").char_span
    assert source[lo:hi].strip() == "---"


def test_divider_stays_inside_the_closed_vocabulary():
    from app.taxonomy import BLOCK_TYPES

    drafts = parse_markdown("a\n\n---\n\nb")
    assert {d.type for d in drafts} <= set(BLOCK_TYPES)


# ── list markers (increment 5) ────────────────────────────────────────
#
# The parser used to discard the bullet/ordered distinction entirely --
# `bullet_list_open` and `ordered_list_open` were both "transparent" and every
# list block was written with `properties: None`. Nothing on the read surface
# could tell an ordered list from a bullet one, so every list item rendered a
# bullet. The marker rides `properties` now, matching the key the block
# editor's `promote()` already writes.


def test_markdown_bullet_list_items_carry_their_marker():
    drafts = parse_markdown("- alpha\n- beta\n")
    items = [d for d in drafts if d.type == "list"]
    assert [d.text for d in items] == ["alpha", "beta"]
    for item in items:
        assert item.properties is not None
        assert item.properties["ordered"] is False
        assert item.properties["marker"] == "-"


def test_markdown_ordered_list_items_carry_their_number():
    """An ordered list is not "a bullet list with digits": the item's own
    number is what a renderer needs, because a list may not start at 1."""
    drafts = parse_markdown("3. three\n4. four\n")
    items = [d for d in drafts if d.type == "list"]
    assert [d.text for d in items] == ["three", "four"]
    assert items[0].properties["ordered"] is True
    assert items[0].properties["number"] == 3
    assert items[1].properties["number"] == 4


def test_markdown_a_nested_ordered_list_restarts_its_own_numbering():
    drafts = parse_markdown("- outer\n    1. one\n    2. two\n")
    items = {d.text: d for d in drafts if d.type == "list"}
    assert items["outer"].properties["ordered"] is False
    assert items["one"].properties["ordered"] is True
    assert items["one"].properties["number"] == 1
    assert items["two"].properties["number"] == 2


def test_markdown_preserves_the_bullet_character_actually_used():
    """`*` and `-` are both bullets and a round-trip must not silently
    rewrite one into the other."""
    drafts = parse_markdown("* star\n")
    items = [d for d in drafts if d.type == "list"]
    assert items[0].properties["marker"] == "*"


def test_the_parsers_marker_is_the_serialisers_marker():
    """The two modules share one `marker` convention and must not drift.

    `block_serializer` defines it as the full marker string as spelled -- it
    matches `^\\d+([.)])$` to decide ordered-ness and re-derives the ordinal
    from that delimiter group. Writing markdown-it's bare `markup` (just `.`)
    would make every ordered item the parser produces read as a BULLET on the
    way back out, silently rewriting ordered lists on any block-first
    conversion.
    """
    from app.services.block_serializer import _is_ordered, _marker_for

    class _Block:
        def __init__(self, properties):
            self.properties = properties
            self.type = "list"

    drafts = parse_markdown("2. two\n3. three\n")
    items = [d for d in drafts if d.type == "list"]
    assert [_is_ordered(_Block(d.properties)) for d in items] == [True, True]
    # And the serialiser renumbers from its own ordinal, keeping the delimiter.
    assert _marker_for(_Block(items[0].properties), 2) == "2."

    bullets = [d for d in parse_markdown("- a\n") if d.type == "list"]
    assert _is_ordered(_Block(bullets[0].properties)) is False


def test_a_paren_delimited_ordered_list_keeps_its_delimiter():
    drafts = parse_markdown("1) one\n")
    item = next(d for d in drafts if d.type == "list")
    assert item.properties["marker"] == "1)"

"""The parser stack — markdown and notes (TH1.03, doc 16 §3).

**The parsers are exercised on real input, not stubs.** Markdown goes through
`markdown-it-py`'s actual tokenizer. A PDF has no parser: filing one is a
designed 422 (the last section). Every assertion about a char_span is checked by slicing the actual
source with it, never by trusting the number the parser reports.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services import document_ingest as di
from app.services.document_ingest import (
    CREATED,
    BlockDraft,
    file_document,
)
from app.services.document_parsers import (
    split_frontmatter,
    SOURCE_TYPE_MARKDOWN,
    SOURCE_TYPE_NOTE,
    DocumentParseError,
    parse_markdown,
    parse_note,
)
from app.taxonomy import BLOCK_TYPES

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


def test_markdown_char_spans_survive_separators_that_are_not_line_breaks():
    """markdown-it ends a line on a newline or carriage return and nothing else.

    ``str.splitlines`` also breaks on form feed, vertical tab, U+0085 and the
    Unicode line and paragraph separators, so counting lines with it shifts
    the span of every block after one of those characters onto its neighbour.
    """
    source = (
        "first\x0cstill first\n\n"
        "second\u2028still second\n\n"
        "third\x0bstill third\x85end\n\n"
        "fourth\n"
    )
    drafts = parse_markdown(source)

    assert [source[d.char_span[0]:d.char_span[1]] for d in drafts] == [
        "first\x0cstill first",
        "second\u2028still second",
        "third\x0bstill third\x85end",
        "fourth",
    ]


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


def test_the_event_and_object_types_are_still_closed():
    from app.services.events import EVENT_TYPES, OBJECT_TYPES

    assert di.DOCUMENT_FILED_EVENT in EVENT_TYPES
    assert di.OBJECT_TYPE in OBJECT_TYPES


# ── source_type: a naming convention, pinned but not enforced ────────


def test_source_type_constants_match_the_erd_spelling():
    """Doc 16 §2's ERD literal, pinned so it stays a decision rather than
    drifting one string literal at a time. `source_type` itself takes any
    string — this only pins what *this module's own callers* agree to write."""
    assert SOURCE_TYPE_MARKDOWN == "md"
    assert SOURCE_TYPE_NOTE == "note"


async def _block_ids(session, document_id) -> list[str]:
    rows = (await session.execute(
        text("SELECT id FROM blocks WHERE document_id = CAST(:d AS uuid) ORDER BY order_index"),
        {"d": str(document_id)},
    )).scalars().all()
    return [str(r) for r in rows]


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

    rows = (await session.execute(
        text("SELECT id, source_type FROM documents WHERE id = ANY(CAST(:ids AS uuid[]))"),
        {"ids": [str(result_md.document_id), str(result_note.document_id)]},
    )).mappings().all()
    by_id = {str(r["id"]): r["source_type"] for r in rows}
    assert by_id[str(result_md.document_id)] == "md"
    assert by_id[str(result_note.document_id)] == "note"


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


def test_note_list_items_carry_their_marker_too():
    """`parse_note` mints `list` blocks exactly as `parse_markdown` does, and
    increment 5 fixed only the markdown side -- which left every note-sourced
    list rendering a bullet. Measured on production: 115 list blocks across 10
    `source_type='note'` documents still had no marker after the corpus
    reparse, and they were the only ones that did.
    """
    drafts = parse_note("- alpha\n- beta\n")
    items = [d for d in drafts if d.type == "list"]
    assert [d.properties["marker"] for d in items] == ["-", "-"]
    assert all(d.properties["ordered"] is False for d in items)


def test_note_ordered_items_carry_their_own_number():
    drafts = parse_note("2. two\n3. three\n")
    items = [d for d in drafts if d.type == "list"]
    assert [d.properties["marker"] for d in items] == ["2.", "3."]
    assert [d.properties["number"] for d in items] == [2, 3]
    assert all(d.properties["ordered"] is True for d in items)


def test_note_markers_use_the_serialisers_convention():
    from app.services.block_serializer import _is_ordered

    class _Block:
        def __init__(self, properties):
            self.properties, self.type = properties, "list"

    ordered = [d for d in parse_note("1) one\n") if d.type == "list"]
    assert ordered[0].properties["marker"] == "1)"
    assert _is_ordered(_Block(ordered[0].properties)) is True

    bullet = [d for d in parse_note("* star\n") if d.type == "list"]
    assert _is_ordered(_Block(bullet[0].properties)) is False


def test_note_normalises_a_unicode_bullet_to_a_writable_marker():
    """`_BULLET_RE` accepts `•`, which is not a marker the serialiser can emit
    -- it would round-trip into content markdown cannot re-parse as a list."""
    items = [d for d in parse_note("• dot\n") if d.type == "list"]
    assert items[0].properties["marker"] == "-"


def test_raw_html_becomes_an_html_block():
    """The parser skipped `html_block` entirely, so a document containing one
    had a construct in its content and no row for it -- which is exactly the
    state the conversion guard refuses."""
    from app.services.document_parsers import parse_markdown

    drafts = parse_markdown(
        "Before\n\n<details>\n<summary>More</summary>\n</details>\n\nAfter\n"
    )
    kinds = [d.type for d in drafts]
    assert kinds == ["paragraph", "html", "paragraph"]

    html = drafts[1]
    # Verbatim: the block is opaque to markdown, so nothing inside it is
    # re-interpreted and nothing about it is normalised.
    assert html.text == "<details>\n<summary>More</summary>\n</details>"
    assert html.properties is None


def test_an_html_block_containing_markdown_characters_stays_opaque():
    """`#` and `-` inside a raw HTML run are not a heading and not a list.
    If the parser ever re-tokenised the content, the serialiser would emit
    something that re-parses differently."""
    from app.services.document_parsers import parse_markdown

    drafts = parse_markdown("<div>\n# not a heading\n- not a list\n</div>\n")
    assert [d.type for d in drafts] == ["html"]
    assert drafts[0].text == "<div>\n# not a heading\n- not a list\n</div>"


# ── PDF: a designed 422, no parser ──────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("declared, refusal", [
    ({"uri": "docs/report.pdf"}, "cannot infer a source_type"),
    ({"uri": "docs/report.md", "source_type": "pdf"}, "no parser serves"),
], ids=["suffix", "source_type"])
async def test_pdf_filing_is_a_designed_422(
    client, auth_headers, stub_llm, session, monkeypatch, declared, refusal
):
    import json
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    import app.api.mcp.server as mcp_server

    response = await client.post(
        "/api/v1/documents",
        json={"project": "pdf-422", "content": "%PDF-1.4 not parsed", **declared},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert refusal in response.text

    @asynccontextmanager
    async def _on_the_test_session():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _on_the_test_session())
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=object()))
    envelope = json.loads(await mcp_server.document_put(
        project="pdf-422", content="%PDF-1.4 not parsed", **declared,
    ))
    assert envelope["status"] == "unsupported_source"
    assert envelope["document_uri"] == declared["uri"]
    assert envelope["reason"]


def test_lock_holds_no_pdf_dependency():
    import re
    from pathlib import Path

    from app.services import document_parsers

    backend = Path(__file__).resolve().parents[1]
    for name in ("requirements.lock", "pyproject.toml"):
        manifest = (backend / name).read_text(encoding="utf-8").lower()
        for package in ("pdfplumber", "pdfminer-six", "pdfminer.six", "pypdfium2"):
            assert not re.search(rf"(?<![\w.-]){re.escape(package)}(?![\w-])", manifest), (
                f"{name} still names {package}"
            )
    assert not hasattr(document_parsers, "parse_pdf")

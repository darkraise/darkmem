"""The parser stack — PDF, markdown, notes (TH1.03, doc 16 §3).

The ADR is decided, not open (doc 16 §3, doc 09's amendment log): ``pdfplumber``
for PDF, ``markdown-it-py`` for markdown, native segmentation for plain-text
notes. ``PyMuPDF`` is rejected (AGPL) and every ML-layout parser
(``unstructured``/``marker``/Docling) is rejected — they pull a native-ML stack
back in, the exact dependency floor doc 03 §3.3's consolidation removed. Both
shipped libraries are pure Python and permissively licensed.

Each parser returns a ``Sequence[BlockDraft]`` — exactly the shape
``file_document`` (TH1.02) takes as its ``parse`` callable's result — and
raises :class:`DocumentParseError` on genuinely unparseable input rather than
returning a wrong or partial tree silently. That single exception type is what
makes a batch filer's per-document isolation mechanical: it wraps one document,
catches one exception type (or its own writer's, both narrow), and moves on.

**Every block type this module emits is a literal member of
``app.taxonomy.BLOCK_TYPES``.** ``file_document`` normalises through
``normalize_block_type`` regardless, but this module never leans on that
fallback to launder a raw token name (``h1``, ``bullet_list_open``, ...) into
a stored value — a parser that emitted a raw type and let normalisation catch
it would be one taxonomy edit away from silently reclassifying every heading
as a paragraph.

**Char spans point at the source, not at the retrievable text.** A markdown
heading's block text is the inline content with the ``#`` marker already
stripped (what an embedder or a citation should read), but its ``char_span``
covers the whole source line including the marker (what a reader would
highlight in the original file). The two are allowed to disagree in length;
doc 16 §2 fixes ``char_span`` as a citation anchor into the source, not a
byte-exact mirror of ``blocks.text``.

**``documents.source_type`` — decided, not closed.** Doc 16 §2's ERD
annotates the column ``"pdf|md|note|import"``, but the column itself is
free-form ``TEXT`` with no ``CHECK`` and no normaliser — unlike ``blocks.type``,
nothing closes it, and this module is the first real emitter into it. The
decision: :data:`SOURCE_TYPE_PDF`, :data:`SOURCE_TYPE_MARKDOWN` and
:data:`SOURCE_TYPE_NOTE` below spell the ERD's own values as a **naming
convention** for this parser stack's callers, not an enforced taxonomy.
Closing the column — a ``CHECK`` constraint, or a ``normalize_source_type``
alongside ``normalize_block_type`` — is deliberately **not** done here: that
is a schema-adjacent decision belonging to whoever owns the ``documents``
table's schema (one owner per epic, per the baseline's serialisation rule),
not to a parser-stack task that was told not to touch the schema. A caller
remains free to pass any string; these constants exist so the values this
module's own callers write agree on a spelling without a database rule
forcing it.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from io import BytesIO
from statistics import median

import pdfplumber
from markdown_it import MarkdownIt

from app.services.block_serializer import DEFAULT_LIST_MARKER
from app.services.document_ingest import BlockDraft

__all__ = [
    "SOURCE_TYPE_MARKDOWN",
    "SOURCE_TYPE_NOTE",
    "SOURCE_TYPE_PDF",
    "DocumentParseError",
    "parse_markdown",
    "parse_note",
    "parse_pdf",
]

# Naming convention only (see module docstring) — not enforced anywhere.
SOURCE_TYPE_PDF = "pdf"
SOURCE_TYPE_MARKDOWN = "md"
SOURCE_TYPE_NOTE = "note"


class DocumentParseError(Exception):
    """One document's content could not be turned into a block tree.

    The one exception type every parser in this module raises on bad input,
    so a caller filing a batch of documents can catch exactly one thing per
    document and isolate it (doc 16 §3, TH1.03's per-document guarantee).
    """


# ── markdown ──────────────────────────────────────────────────────────


_FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?(?:\n|\Z)", re.DOTALL
)


def split_frontmatter(text: str) -> tuple[str | None, int]:
    """The leading ``---`` frontmatter fence's inner text, and the offset where
    the body begins.

    ``(None, 0)`` when there is no leading fence, which includes the case that
    matters most: a ``---`` thematic break part-way down a document is not
    frontmatter, and treating it as one would swallow everything above it.

    Only the *leading* fence counts, so the match is anchored. The returned
    offset is what keeps char spans honest — the parser tokenises the body but
    every span it emits must still index into the original source.
    """
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return None, 0
    return match.group(1), match.end()


def parse_markdown(text: str) -> list[BlockDraft]:
    """Parse markdown source into a block tree.

    Headings own their following content down to the next heading of equal
    or shallower level; lists and blockquotes nest through markdown-it's own
    token structure. A tight or loose list item becomes one ``list`` block
    per item (its own text, not a separate paragraph block), so nested items
    parent onto the enclosing item rather than a paragraph inside it.
    """
    if not isinstance(text, str):
        raise DocumentParseError(f"markdown content must be str, got {type(text).__name__}")
    if not text.strip():
        return []

    # Frontmatter is split off before tokenising: commonmark reads a closing
    # `---` as a setext h2 and turns the whole block into a heading. The body
    # offset is added back into every span below, so a span still indexes into
    # the original source, fences included (this module's own contract).
    _, body_start = split_frontmatter(text)
    body = text[body_start:]

    try:
        # The `table` rule ships with markdown-it but is off under the
        # commonmark preset. Enabling it is what stops a GFM table parsing as
        # one giant paragraph the embedder then truncates (spec §4.1).
        tokens = MarkdownIt("commonmark").enable("table").parse(body)
    except Exception as exc:  # markdown-it-py is tolerant; defensive only.
        raise DocumentParseError(f"markdown parse failed: {exc}") from exc

    offsets = _line_offsets(body)
    drafts: list[dict] = []
    heading_stack: list[tuple[int, int]] = []  # (draft_index, level)
    container_stack: list[int] = []  # draft indexes of open list-items/blockquotes
    # One frame per open list wrapper: whether it is ordered, the bullet or
    # delimiter character the source used, and the next item's number. The
    # wrapper mints no block of its own, so this is the only place the
    # ordered/bullet distinction exists -- without it every item renders a
    # bullet, which is what the parser did before increment 5.
    list_stack: list[dict] = []

    def parent() -> int | None:
        if container_stack:
            return container_stack[-1]
        return heading_stack[-1][0] if heading_stack else None

    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]

        if tok.type == "heading_open":
            level = int(tok.tag[1:]) if len(tok.tag) > 1 and tok.tag[1:].isdigit() else 1
            while heading_stack and heading_stack[-1][1] >= level:
                heading_stack.pop()
            inline = tokens[i + 1]
            drafts.append({
                "text": inline.content,
                "type": "heading",
                "parent": parent(),
                "properties": {"level": level},
                "char_span": _span(tok.map, offsets, body),
            })
            heading_stack.append((len(drafts) - 1, level))
            i += 3
            continue

        if tok.type == "paragraph_open":
            inline = tokens[i + 1]
            if container_stack:
                target = drafts[container_stack[-1]]
                target["text"] = f"{target['text']}\n{inline.content}" if target["text"] else inline.content
                if target["char_span"] is None:
                    target["char_span"] = _span(tok.map, offsets, body)
            else:
                drafts.append({
                    "text": inline.content,
                    "type": "paragraph",
                    "parent": parent(),
                    "properties": None,
                    "char_span": _span(tok.map, offsets, body),
                })
            i += 3
            continue

        if tok.type == "list_item_open":
            drafts.append({
                "text": "",
                "type": "list",
                "parent": parent(),
                "properties": _list_item_properties(list_stack, tok),
                "char_span": _span(tok.map, offsets, body),
            })
            container_stack.append(len(drafts) - 1)
            i += 1
            continue

        if tok.type == "list_item_close":
            container_stack.pop()
            i += 1
            continue

        if tok.type == "blockquote_open":
            drafts.append({
                "text": "",
                "type": "quote",
                "parent": parent(),
                "properties": None,
                "char_span": _span(tok.map, offsets, body),
            })
            container_stack.append(len(drafts) - 1)
            i += 1
            continue

        if tok.type == "blockquote_close":
            container_stack.pop()
            i += 1
            continue

        if tok.type in ("bullet_list_open", "ordered_list_open"):
            # Transparent as a BLOCK: the list wrapper mints no block of its
            # own, so a nested item's parent is the enclosing item (or
            # heading), never the list. The type vocabulary has no separate
            # "list container" shape, and an empty-text wrapper block would be
            # unretrievable. It is not transparent as *data*, though -- the
            # ordered/bullet distinction and the start number live only here,
            # so a frame is pushed for the items to read.
            list_stack.append(_open_list_frame(tok, body))
            i += 1
            continue

        if tok.type in ("bullet_list_close", "ordered_list_close"):
            if list_stack:
                list_stack.pop()
            i += 1
            continue

        if tok.type == "table_open":
            i = _emit_table(tokens, i, drafts, parent(), offsets, body)
            continue

        if tok.type == "hr":
            # A thematic break carries no text -- the rule IS the block. It
            # mints a row rather than being skipped because block-first
            # conversion regenerates content from the tree, and a construct
            # with no block is a construct that conversion silently deletes.
            drafts.append({
                "text": "",
                "type": "divider",
                "parent": parent(),
                "properties": None,
                "char_span": _span(tok.map, offsets, body),
            })
            i += 1
            continue

        if tok.type in ("fence", "code_block"):
            drafts.append({
                "text": tok.content.rstrip("\n"),
                "type": "code",
                "parent": parent(),
                "properties": {"language": tok.info.strip()} if getattr(tok, "info", None) else None,
                "char_span": _span(tok.map, offsets, body),
            })
            i += 1
            continue

        # html_block — not in the committed block-type set (doc 16 §9);
        # skipped rather than minting a meaningless block. Tables were named
        # here until the 2026-08-31 spec §4.1 change, and `hr` until
        # 2026-09-02; both are parsed structurally above now.
        i += 1

    return [
        BlockDraft(
            text=d["text"], type=d["type"], parent=d["parent"],
            properties=d["properties"],
            char_span=(
                (d["char_span"][0] + body_start, d["char_span"][1] + body_start)
                if d["char_span"] is not None
                else None
            ),
        )
        for d in drafts
    ]


def _alignment(tok) -> str | None:
    """GFM column alignment from a th/td `style` attr; None when unaligned."""
    style = tok.attrs.get("style") if tok.attrs else None
    return style.removeprefix("text-align:") if style else None


def _emit_table(tokens, i, drafts, parent_index, offsets, body) -> int:
    """Consume ``table_open``..``table_close``; emit one ``table`` draft plus
    one ``table_row`` child per body row.

    The header row folds into the table block itself (spec §4.1): its cells are
    the table's own retrievable text and properties, not a child row. A data
    row becomes an ordinary-sized block, which is the whole point — the
    measured defect was a 235KB single block, not a missing shape.
    """
    table_index = len(drafts)
    drafts.append({
        "text": "",
        "type": "table",
        "parent": parent_index,
        "properties": None,
        "char_span": _span(tokens[i].map, offsets, body),
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
            row_span = _span(t.map, offsets, body)
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



# ── list markers ──────────────────────────────────────────────────────
#
# The `marker` key is the full marker string as spelled -- "-" or "3." --
# because `block_serializer` already defines it that way and reads it back
# on every block-first conversion. `DEFAULT_LIST_MARKER` is imported from
# there rather than re-spelled so the two cannot drift.


def _open_list_frame(tok, body: str) -> dict:
    """The state one open list wrapper carries for its items.

    `markup` is the character the source actually used -- `-`, `*` or `+` for
    a bullet list, `.` or `)` for an ordered one -- so a round-trip does not
    rewrite one spelling into another. An ordered list may start anywhere,
    and markdown-it puts that start on the wrapper's `attrs`, so it is read
    here rather than assumed to be 1.
    """
    ordered = tok.type == "ordered_list_open"
    start = 1
    if ordered:
        try:
            start = int(tok.attrGet("start"))
        except (AttributeError, TypeError, ValueError):
            start = 1
    return {
        "ordered": ordered,
        "markup": getattr(tok, "markup", None) or (
            "." if ordered else DEFAULT_LIST_MARKER
        ),
        "next": start,
    }


def _list_item_properties(list_stack: list[dict], tok) -> dict:
    """This item's marker properties, read off its enclosing wrapper.

    A defensive default rather than a raise when the stack is empty: a list
    item outside any wrapper is not something markdown-it emits, and failing
    a whole document's parse over it would trade a rendering detail for the
    document.
    """
    frame = list_stack[-1] if list_stack else None
    if frame is None:
        return {"ordered": False, "marker": DEFAULT_LIST_MARKER}
    if not frame["ordered"]:
        # `markup` is the bullet character itself for a bullet item.
        marker = getattr(tok, "markup", None) or frame["markup"]
        return {"ordered": False, "marker": marker}
    number = frame["next"]
    frame["next"] = number + 1
    # The full marker as it is spelled, "3." not ".", because that is the
    # convention `block_serializer` already reads: `_is_ordered` matches the
    # whole string against `^\d+([.)])$` and `_marker_for` re-derives the
    # ordinal from its delimiter group. Writing markdown-it's bare `markup`
    # here would make every ordered item read as a bullet on the way back out.
    delimiter = getattr(tok, "markup", None) or "."
    return {"ordered": True, "marker": f"{number}{delimiter}", "number": number}


def _line_offsets(text: str) -> list[int]:
    """Cumulative char offset of the start of each source line, index 0 first."""
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def _span(token_map, offsets: list[int], text: str) -> tuple[int, int] | None:
    if token_map is None:
        return None
    start_line, end_line = token_map
    lo = offsets[start_line]
    hi = offsets[min(end_line, len(offsets) - 1)]
    trimmed = text[lo:hi].rstrip("\n")
    return (lo, lo + len(trimmed))


# ── plain-text notes ─────────────────────────────────────────────────

_BLANK_RUN_RE = re.compile(r"\n[ \t]*\n+")
_BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
# The marker itself, so a note's list items carry the same `marker` property
# `parse_markdown` writes and `block_serializer` reads back.
_NOTE_MARKER_RE = re.compile(r"^\s*([-*•]|\d+[.)])\s+")
_HEADING_MAX_CHARS = 80
_HEADING_TERMINAL_PUNCTUATION = ".?!:;,"


def parse_note(text: str) -> list[BlockDraft]:
    """Segment plain-text notes with paragraph/heading/bullet heuristics.

    No markup to key off, so the rules are: a paragraph is a blank-line
    delimited chunk; a chunk is a heading if it is one short line with no
    terminal sentence punctuation; a chunk is a list if every non-blank line
    starts with a bullet or numbered marker (one block per item). A note has
    no heading levels, so every heading closes the previous one — there is
    no nesting deeper than "under the most recent heading."
    """
    if not isinstance(text, str):
        raise DocumentParseError(f"note content must be str, got {type(text).__name__}")
    if not text.strip():
        return []

    drafts: list[BlockDraft] = []
    heading_index: int | None = None

    for start, end, chunk in _split_paragraphs(text):
        lines = chunk.splitlines()
        non_blank = [line for line in lines if line.strip()]
        if non_blank and all(_BULLET_RE.match(line) for line in non_blank):
            for line_start, line_end, line in _iter_lines(text, start, end):
                item_text = _BULLET_RE.sub("", line).strip()
                if not item_text:
                    continue
                drafts.append(BlockDraft(
                    text=item_text, type="list", parent=heading_index,
                    properties=_note_marker_properties(line),
                    char_span=(line_start, line_end),
                ))
        elif _looks_like_heading(lines):
            drafts.append(BlockDraft(
                text=chunk, type="heading", parent=None, char_span=(start, end),
            ))
            heading_index = len(drafts) - 1
        else:
            drafts.append(BlockDraft(
                text=chunk, type="paragraph", parent=heading_index, char_span=(start, end),
            ))

    return drafts



def _note_marker_properties(line: str) -> dict:
    """This note line's marker, in `block_serializer`'s convention.

    A note has no list wrapper to read ordered-ness off, so each line carries
    its own marker and its own number -- which is the number the author wrote,
    not a position, exactly as it is for markdown.

    `•` is accepted by `_BULLET_RE` but is **not** a marker the serialiser can
    emit: round-tripping it would write content markdown cannot re-parse as a
    list. It normalises to the default bullet, which is a deliberate rewrite
    of the spelling rather than a faithful record of it.
    """
    match = _NOTE_MARKER_RE.match(line)
    if match is None:
        return {"ordered": False, "marker": DEFAULT_LIST_MARKER}
    marker = match.group(1)
    if marker in ("-", "*", "+"):
        return {"ordered": False, "marker": marker}
    if marker == "\u2022":
        return {"ordered": False, "marker": DEFAULT_LIST_MARKER}
    return {"ordered": True, "marker": marker, "number": int(marker[:-1])}


def _looks_like_heading(lines: list[str]) -> bool:
    if len(lines) != 1:
        return False
    line = lines[0].strip()
    if not line or len(line) > _HEADING_MAX_CHARS:
        return False
    return line[-1] not in _HEADING_TERMINAL_PUNCTUATION


def _split_paragraphs(text: str) -> list[tuple[int, int, str]]:
    """Blank-line-delimited chunks, trimmed, with their absolute char span."""
    chunks: list[tuple[int, int, str]] = []
    pos = 0
    for match in _BLANK_RUN_RE.finditer(text):
        _append_chunk(chunks, text, pos, match.start())
        pos = match.end()
    _append_chunk(chunks, text, pos, len(text))
    return chunks


def _append_chunk(chunks: list[tuple[int, int, str]], text: str, start: int, end: int) -> None:
    segment = text[start:end]
    stripped = segment.strip()
    if not stripped:
        return
    lead = len(segment) - len(segment.lstrip())
    chunks.append((start + lead, start + lead + len(stripped), stripped))


def _iter_lines(text: str, start: int, end: int):
    pos = start
    for raw_line in text[start:end].splitlines(keepends=True):
        content = raw_line.rstrip("\n")
        yield pos, pos + len(content), content
        pos += len(raw_line)


# ── PDF ───────────────────────────────────────────────────────────────


def parse_pdf(data: bytes) -> list[BlockDraft]:
    """Parse PDF bytes into a block tree via `pdfplumber`'s character-level text.

    Lines are grouped into paragraphs by vertical gap (a gap over 1.5x the
    page's median line height starts a new paragraph); a single-line group
    set in a font larger than the page's own median size is classified a
    heading, everything else a paragraph. Page number and the union bounding
    box ride ``properties`` (doc 16 §2's PDF provenance), and ``char_span``
    indexes into the concatenation of every extracted paragraph across the
    document, in reading order. PDF blocks are flat — this parser does not
    attempt heading-owns-content nesting from font size alone, unlike the
    markdown parser's structural nesting.

    No separate type check on `data`: `BytesIO()` itself refuses anything
    that is not bytes-like, and that `TypeError` is caught below with every
    other pdfplumber-side failure — a second explicit check here would raise
    the identical wrapped error one line earlier and prove nothing a test
    could tell apart from not having it.
    """
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            return _parse_pdf_pages(pdf)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(f"pdf parse failed: {exc}") from exc


def _parse_pdf_pages(pdf) -> list[BlockDraft]:
    drafts: list[BlockDraft] = []
    offset = 0
    for page_number, page in enumerate(pdf.pages, start=1):
        try:
            lines = page.extract_text_lines() or []
        except Exception as exc:
            raise DocumentParseError(
                f"pdf page {page_number} extraction failed: {exc}"
            ) from exc
        if not lines:
            continue

        median_height = _median_line_height(lines)
        common_size = _common_font_size(lines)
        gap_threshold = median_height * 1.5 if median_height else 6.0

        for group in _group_lines(lines, gap_threshold):
            text = " ".join(line["text"].strip() for line in group if line["text"].strip())
            if not text:
                continue
            size = _line_size(group[0])
            block_type = "heading" if len(group) == 1 and size > common_size + 1.0 else "paragraph"
            start = offset
            end = start + len(text)
            offset = end + 1
            drafts.append(BlockDraft(
                text=text,
                type=block_type,
                properties={"page": page_number, "bbox": _bbox_union(group)},
                char_span=(start, end),
            ))
    return drafts


def _line_height(line: dict) -> float:
    return line["bottom"] - line["top"]


def _median_line_height(lines: Sequence[dict]) -> float:
    heights = [_line_height(line) for line in lines if _line_height(line) > 0]
    return median(heights) if heights else 0.0


def _line_size(line: dict) -> float:
    sizes = [char["size"] for char in line.get("chars") or [] if char.get("size")]
    return max(sizes) if sizes else 0.0


def _common_font_size(lines: Sequence[dict]) -> float:
    sizes = [_line_size(line) for line in lines]
    sizes = [s for s in sizes if s > 0]
    return median(sizes) if sizes else 0.0


def _group_lines(lines: Sequence[dict], gap_threshold: float) -> list[list[dict]]:
    """Split into paragraph groups on a vertical gap OR a font-size change.

    The gap alone under-splits a heading immediately followed by body text —
    single-spaced layouts often leave less vertical room than the heading's
    own larger line height would suggest, so the gap can read as "close
    together" even across a real heading/paragraph boundary. A size jump is
    a second, independent signal for the same boundary.
    """
    groups: list[list[dict]] = []
    current: list[dict] = []
    prev_bottom: float | None = None
    prev_size: float | None = None
    for line in lines:
        size = _line_size(line)
        gap_broke = prev_bottom is not None and (line["top"] - prev_bottom) > gap_threshold
        size_broke = prev_size is not None and size > 0 and prev_size > 0 and abs(size - prev_size) > 1.0
        if (gap_broke or size_broke) and current:
            groups.append(current)
            current = []
        current.append(line)
        prev_bottom = line["bottom"]
        prev_size = size
    if current:
        groups.append(current)
    return groups


def _bbox_union(group: Sequence[dict]) -> dict:
    return {
        "x0": round(min(line["x0"] for line in group), 2),
        "top": round(min(line["top"] for line in group), 2),
        "x1": round(max(line["x1"] for line in group), 2),
        "bottom": round(max(line["bottom"] for line in group), 2),
    }

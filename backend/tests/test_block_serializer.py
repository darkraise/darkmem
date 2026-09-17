"""The serialiser is trusted only as far as the parser agrees with it.

The load-bearing property is the ROUND TRIP: parse(serialize(tree)) must
reproduce the tree's types, texts and structure, and serialize must be a fixed
point. Per-shape emit tests localise a failure; the round-trip test is the
contract.
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from app.services.block_serializer import (
    TreeBlock,
    derive_markers,
    reproduces_source,
    serialize_tree,
)
from app.services.document_parsers import parse_markdown


def _tree_from_drafts(drafts) -> list[TreeBlock]:
    """Adapt parser output to serialiser input, minting ids and resolving the
    backward parent indexes -- the same resolution `_resolve_tree` does."""
    ids = [uuid4() for _ in drafts]
    return [
        TreeBlock(
            id=ids[i],
            parent_id=None if d.parent is None else ids[d.parent],
            order_index=i,
            type=d.type,
            text=d.text,
            properties=d.properties,
        )
        for i, d in enumerate(drafts)
    ]


def _tree_and_spans(source: str) -> tuple[list[TreeBlock], dict]:
    """One parse, so the spans key on the ids the tree actually carries.

    Two separate parses mint two sets of uuids and the spans match nothing --
    which silently makes `derive_markers` a no-op rather than failing.
    """
    drafts = parse_markdown(source)
    tree = _tree_from_drafts(drafts)
    spans = {
        b.id: d.char_span
        for b, d in zip(tree, drafts)
        if d.char_span is not None
    }
    return tree, spans


def _skeleton(blocks) -> list[tuple]:
    """(type, text, parent-position) triples -- the structure that must survive."""
    index = {b.id: i for i, b in enumerate(blocks)}
    return [
        (b.type, b.text, None if b.parent_id is None else index.get(b.parent_id))
        for b in blocks
    ]


ROUND_TRIP_SOURCES = [
    "# Title\n\nA paragraph with **bold** and `code`.",
    "# H1\n\n## H2\n\ndeeper prose\n\n## H2 again",
    "- one\n- two\n  - nested\n- three",
    # Two adjacent lists of different marker styles are TWO lists. The block
    # model has no list-container shape, so only the markers distinguish
    # them -- run them together and the ordered one continues the bullet
    # one's count and loses its blank line.
    "* star\n\n1) one\n2) two",
    "1. first\n2. second\n3. third",
    "> quoted line\n> more of it",
    "```python\nprint('hi')\n```",
    "| Name | Age |\n|---|---:|\n| Ann | 3 |\n| Bo | 4 |",
    "# Doc\n\npara\n\n- item\n  - sub\n\n> quote\n\n```\ncode\n```",
    # Thematic breaks round-trip since `divider` joined the vocabulary
    # (2026-09-02). The adjacency cases matter: a `---` after a paragraph
    # could re-parse as a setext underline if the separator ever stopped
    # writing a blank line, which would turn a rule into a heading.
    "para one\n\n---\n\npara two",
    "# H\n\n---\n\nbody",
    "- one\n- two\n\n---\n\nafter",
    # Raw HTML round-trips since `html` joined the vocabulary (2026-09-07).
    # A fixture here is what tests parser-to-serialiser agreement: the block
    # text is whatever the parser stored, not a string this file chose.
    "before\n\n<div class='x'>raw</div>\n\nafter",
    # A quote's children are separated by a blank line that must itself carry
    # the quote prefix. An unprefixed blank line ENDS the blockquote, so the
    # child re-parses as a second quote and the tree gains a block. Every
    # non-paragraph child is affected -- a quote's paragraph children are
    # folded into its own text by the parser and mint no block at all.
    "> lead\n>\n> - item\n> - two",
    "> lead\n>\n> ```\n> code\n> ```",
    "> lead\n>\n> # inner heading",
    "> lead\n>\n> | A | B |\n> | --- | --- |\n> | 1 | 2 |",
    # A `|` inside a table cell is escaped in the source and stored UNESCAPED
    # in `header`/`cells`, so the serialiser has to put the backslash back.
    # Emitting it bare splits the row into more columns than the delimiter
    # declares, which truncates the cell's text -- content loss, not just a
    # restructure.
    "| a \\| b | c |\n| --- | --- |\n| x \\| y | z |",
    # A setext heading's content may span several lines, and the parser keeps
    # the newline in `text`. Emitted as one-line ATX that newline ends the
    # heading, so the remainder re-parses as a paragraph.
    "line one\nline two\n=====",
]

# Shapes the parser drops on the floor. Only ONE kind is left: markdown-it
# consumes link-reference definitions into `env`, minting no token and no
# block, so nothing can serialise them back and a document containing one
# must REFUSE conversion rather than silently lose it (review M-2). `hr`
# left this list on 2026-09-02 as `divider` and raw HTML on 2026-09-07 as
# `html` -- both now have block shapes and both round-trip above.
NON_CONVERTIBLE_SOURCES = [
    "see [the doc][ref]\n\n[ref]: https://example.test",  # link reference
]


@pytest.mark.parametrize("source", ROUND_TRIP_SOURCES)
def test_parse_serialize_parse_is_stable(source):
    tree = _tree_from_drafts(parse_markdown(source))
    first = serialize_tree(tree)
    reparsed = _tree_from_drafts(parse_markdown(first.content))
    assert _skeleton(reparsed) == _skeleton(tree)
    second = serialize_tree(reparsed)
    assert second.content == first.content        # fixed point


@pytest.mark.parametrize("source", ROUND_TRIP_SOURCES)
def test_every_span_slices_its_own_block_back_out(source):
    tree = _tree_from_drafts(parse_markdown(source))
    result = serialize_tree(tree)
    by_id = {b.id: b for b in tree}
    for placed in result.placed:
        lo, hi = placed.char_span
        sliced = result.content[lo:hi]
        block = by_id[placed.block_id]
        props = block.properties or {}
        if block.type in ("table", "table_row"):
            # A table's `text` is the ` | ` join of its cells, so a cell
            # holding a `|` makes that string one no valid source can
            # contain -- the source has to escape it. Assert the cells
            # survive into the span instead, which is the property that
            # matters: the joined form is covered by the round trip.
            cells = props.get("header") or props.get("cells") or []
            for cell in cells:
                assert cell.replace("|", r"\|") in sliced
            continue
        first_text_line = (block.text or "").split("\n", 1)[0]
        assert first_text_line in sliced or block.text == ""


def test_placed_order_is_the_strictly_increasing_reading_order():
    tree = _tree_from_drafts(parse_markdown("# a\n\npara\n\n- x\n  - y"))
    result = serialize_tree(tree)
    assert [p.order_index for p in result.placed] == list(range(len(tree)))


def test_ordered_lists_renumber_by_position():
    # Markers are derived from the source first, exactly as the conversion
    # pass does: the parser records no marker, so an undelivered tree would
    # serialise as bullets and the renumbering property would be untestable.
    source = "1. a\n2. b\n3. c"
    tree, spans = _tree_and_spans(source)
    tree = derive_markers(tree, source, spans)
    tree = [b for b in tree if b.text != "b"]      # delete the middle item
    result = serialize_tree(tree)
    assert "1. a" in result.content and "2. c" in result.content


def test_a_code_block_containing_backticks_gets_a_longer_fence():
    tree = [TreeBlock(id=uuid4(), parent_id=None, order_index=0, type="code",
                      text="```\nnested\n```", properties=None)]
    content = serialize_tree(tree).content
    assert content.startswith("````")
    assert _skeleton(_tree_from_drafts(parse_markdown(content))) == _skeleton(tree)


def test_derive_markers_reads_the_marker_out_of_the_source():
    source = "* star item\n\n1) paren ordered"
    tree, spans = _tree_and_spans(source)
    derived = derive_markers(tree, source, spans)
    markers = [(b.properties or {}).get("marker") for b in derived if b.type == "list"]
    assert markers == ["*", "1)"]


@pytest.mark.parametrize("source", ROUND_TRIP_SOURCES)
def test_reproduces_source_is_true_for_every_round_trip_fixture(source):
    tree, spans = _tree_and_spans(source)
    assert reproduces_source(tree, source, spans) is True


@pytest.mark.parametrize("source", NON_CONVERTIBLE_SOURCES)
def test_reproduces_source_refuses_what_the_parser_dropped(source):
    """Review M-2: the serialiser cannot emit these, so the guard that gates
    conversion must say so. A False here is the whole protection against a
    block verb silently rewriting a corpus document without its rules or its
    link definitions."""
    tree, spans = _tree_and_spans(source)
    assert reproduces_source(tree, source, spans) is False


def test_frontmatter_is_re_emitted_from_document_properties():
    source = "---\ntitle: T\n---\n# H\n\nbody"
    tree = _tree_from_drafts(parse_markdown(source))
    out = serialize_tree(tree, frontmatter="title: T")
    assert out.content.startswith("---\ntitle: T\n---\n")
    assert "# H" in out.content


def test_a_parent_cycle_raises_instead_of_hanging():
    a, b = uuid4(), uuid4()
    tree = [
        TreeBlock(id=a, parent_id=b, order_index=0, type="paragraph", text="a", properties=None),
        TreeBlock(id=b, parent_id=a, order_index=1, type="paragraph", text="b", properties=None),
    ]
    with pytest.raises(ValueError):
        serialize_tree(tree)


def test_a_frontmatter_document_is_convertible():
    """The guard parses the BODY, not the raw file.

    A document's opening `---` fence is itself an `hr` token, so tokenising
    raw content refused every frontmatter document -- and no imported document
    has frontmatter, which is why the corpus measurement did not catch it.
    """
    source = "---\ntitle: T\n---\n# H\n\nbody"
    tree, spans = _tree_and_spans(source)
    assert reproduces_source(tree, source, spans, frontmatter="title: T") is True


def test_inline_html_does_not_refuse_a_document():
    """`html_inline` is a child of an `inline` token, so a top-level scan
    never sees one -- and the raw tag survives in the paragraph's own text,
    so it round-trips. It was dead weight in the refusal set."""
    source = "a <b>bold</b> c"
    tree, spans = _tree_and_spans(source)
    assert reproduces_source(tree, source, spans) is True


def test_a_stale_tree_is_refused_even_though_the_source_is_representable():
    """The back door into M-2's failure.

    `ingest_document` returns UNCHANGED on a byte-identical re-push without
    touching blocks, so a document filed before `divider` existed has `---` in
    its content and no divider row. Converting it would drop every rule. The
    source alone looks convertible; only comparing it against the tree catches
    this.
    """
    source = "para one\n\n---\n\npara two"
    tree, spans = _tree_and_spans(source)
    assert reproduces_source(tree, source, spans) is True

    stale = [b for b in tree if b.type != "divider"]      # the pre-divider tree
    assert reproduces_source(stale, source, spans) is False


def test_html_round_trips_verbatim():
    """The block is opaque, so serialising it is writing its text back. A
    normalising branch here would change what re-parses."""
    from app.services.block_serializer import TreeBlock, serialize_tree

    blocks = [
        TreeBlock(id=uuid4(), parent_id=None, order_index=0,
                  type="paragraph", text="Before", properties=None),
        TreeBlock(id=uuid4(), parent_id=None, order_index=1, type="html",
                  text="<details>\n<summary>More</summary>\n</details>",
                  properties=None),
    ]
    out = serialize_tree(blocks)
    assert out.content == (
        "Before\n\n<details>\n<summary>More</summary>\n</details>"
    )


def test_a_document_with_html_converts_when_the_tree_has_it():
    """Before the html type existed this document was permanently
    unconvertible, which meant permanently uneditable in the notes UI."""
    from app.services.block_serializer import TreeBlock, reproduces_source

    content = "Before\n\n<div>x</div>\n\nAfter\n"
    blocks = [
        TreeBlock(id=uuid4(), parent_id=None, order_index=0,
                  type="paragraph", text="Before", properties=None),
        TreeBlock(id=uuid4(), parent_id=None, order_index=1,
                  type="html", text="<div>x</div>", properties=None),
        TreeBlock(id=uuid4(), parent_id=None, order_index=2,
                  type="paragraph", text="After", properties=None),
    ]
    assert reproduces_source(blocks, content, {}) is True


def test_a_stale_tree_missing_its_html_block_still_refuses():
    """The count check is the half that keeps the guard honest. A document
    filed BEFORE the html type existed carries the construct in its content
    and no row for it, and `ingest_document` returns UNCHANGED on a
    byte-identical re-push without touching blocks -- so without this check
    the conversion would silently drop the HTML."""
    from app.services.block_serializer import TreeBlock, reproduces_source

    content = "Before\n\n<div>x</div>\n\nAfter\n"
    stale = [
        TreeBlock(id=uuid4(), parent_id=None, order_index=0,
                  type="paragraph", text="Before", properties=None),
        TreeBlock(id=uuid4(), parent_id=None, order_index=1,
                  type="paragraph", text="After", properties=None),
    ]
    assert reproduces_source(stale, content, {}) is False


def _page_block(type_, text="", properties=None, parent=None, order=0):
    return TreeBlock(uuid4(), parent, order, type_, text, properties)


def test_todos_emit_as_a_tight_task_list():
    first = _page_block("todo", "open", {"checked": False})
    second = _page_block("todo", "done", {"checked": True}, order=1)
    assert serialize_tree([first, second]).content == "- [ ] open\n- [x] done"


def test_a_todo_joins_a_bullet_run_and_resets_an_ordered_count():
    bullet = _page_block("list", "bullet", {"ordered": False, "marker": "-"})
    task = _page_block("todo", "task", {"checked": False}, order=1)
    one = _page_block("list", "one", {"ordered": True, "marker": "1."}, order=2)
    two = _page_block("list", "two", {"ordered": True, "marker": "1."}, order=3)
    assert serialize_tree([bullet, task, one, two]).content == (
        "- bullet\n- [ ] task\n\n1. one\n2. two"
    )

    zero = _page_block("list", "zero", {"ordered": True, "marker": "1."})
    mid = _page_block("todo", "mid", {"checked": True}, order=1)
    after = _page_block("list", "after", {"ordered": True, "marker": "1."}, order=2)
    assert serialize_tree([zero, mid, after]).content == (
        "1. zero\n\n- [x] mid\n\n1. after"
    )


def test_todos_nest_tightly_under_list_and_todo_parents():
    item = _page_block("list", "parent", {"ordered": False, "marker": "-"})
    child = _page_block("todo", "child", {"checked": False}, parent=item.id)
    task = _page_block("todo", "tparent", {"checked": True}, order=1)
    grandchild = _page_block(
        "list", "lchild", {"ordered": False, "marker": "-"}, parent=task.id,
    )
    assert serialize_tree([item, child, task, grandchild]).content == (
        "- parent\n  - [ ] child\n- [x] tparent\n  - lchild"
    )


def test_a_multi_line_todo_indents_its_continuation():
    task = _page_block("todo", "line one\nline two", {"checked": False})
    assert serialize_tree([task]).content == "- [ ] line one\n  line two"


def test_a_toggle_wraps_its_children_and_spans_only_its_opening_lines():
    toggle = _page_block("toggle", "Summary")
    inside = _page_block("paragraph", "inside", parent=toggle.id)
    nested = _page_block("todo", "nested", {"checked": False}, parent=toggle.id, order=1)
    after = _page_block("paragraph", "after", order=1)

    result = serialize_tree([toggle, inside, nested, after])

    assert result.content == (
        "<details>\n<summary>Summary</summary>\n\ninside\n\n- [ ] nested\n\n"
        "</details>\n\nafter"
    )
    start, end = next(p.char_span for p in result.placed if p.block_id == toggle.id)
    assert result.content[start:end] == "<details>\n<summary>Summary</summary>"


def test_an_empty_toggle_still_closes():
    assert serialize_tree([_page_block("toggle", "Empty")]).content == (
        "<details>\n<summary>Empty</summary>\n\n</details>"
    )


@pytest.mark.parametrize(
    "variant, label",
    [("info", "NOTE"), ("warning", "WARNING"), ("error", "CAUTION"), ("success", "TIP")],
)
def test_a_callout_emits_a_github_alert(variant, label):
    callout = _page_block("callout", "line1\nline2", {"variant": variant})
    assert serialize_tree([callout]).content == f"> [!{label}]\n> line1\n> line2"

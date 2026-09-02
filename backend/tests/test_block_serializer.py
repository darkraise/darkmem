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
    "1. first\n2. second\n3. third",
    "> quoted line\n> more of it",
    "```python\nprint('hi')\n```",
    "| Name | Age |\n|---|---:|\n| Ann | 3 |\n| Bo | 4 |",
    "# Doc\n\npara\n\n- item\n  - sub\n\n> quote\n\n```\ncode\n```",
]

# Shapes the parser drops on the floor: `hr` and `html_block` mint no block
# (document_parsers.py) and markdown-it consumes link-reference definitions
# into `env`. NOTHING can serialise them back, so a document containing one
# must REFUSE conversion rather than silently lose it (review M-2).
NON_CONVERTIBLE_SOURCES = [
    "para one\n\n---\n\npara two",                       # thematic break
    "before\n\n<div class='x'>raw</div>\n\nafter",       # html_block
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
    block verb silently rewriting a corpus document without its rules, its
    raw HTML or its link definitions."""
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

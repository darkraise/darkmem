"""Serialise a block tree back into markdown source (spec §8.2, increment 8).

Block-first ingest's source-of-record producer: the block verbs are
authoritative and ``documents.content`` is a serialisation of the tree in
reading order. Because this pass writes the content, it knows the offset at
which every block landed -- so ``char_span`` is recomputed here, in the same
pass, never dropped to NULL.

Pure: no session, no I/O, no imports from the writer stack. ``block_verbs``
owns every database write.
"""
from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from uuid import UUID

__all__ = [
    "DEFAULT_LIST_MARKER",
    "PlacedBlock",
    "SerializedDocument",
    "TreeBlock",
    "derive_markers",
    "reproduces_source",
    "serialize_tree",
]

DEFAULT_LIST_MARKER = "-"
_ORDERED_RE = re.compile(r"^\d+([.)])$")
_MARKER_RE = re.compile(r"^[ \t]*([-*+]|\d+[.)])[ \t]+")


@dataclass(frozen=True)
class TreeBlock:
    id: UUID
    parent_id: UUID | None
    order_index: int
    type: str
    text: str
    properties: dict | None


@dataclass(frozen=True)
class PlacedBlock:
    block_id: UUID
    order_index: int
    char_span: tuple[int, int]


@dataclass(frozen=True)
class SerializedDocument:
    content: str
    placed: list[PlacedBlock]


def _children_map(blocks: Sequence[TreeBlock]):
    by_id = {b.id: b for b in blocks}
    children: dict[UUID | None, list[TreeBlock]] = defaultdict(list)
    for b in blocks:
        parent = b.parent_id if b.parent_id in by_id else None
        children[parent].append(b)
    for seq in children.values():
        seq.sort(key=lambda b: (b.order_index, str(b.id)))
    # Cycle guard: every block must be reachable from the roots exactly once.
    # Without it a parent cycle is an infinite walk rather than an error.
    reachable: set[UUID] = set()
    stack = [b.id for b in children[None]]
    while stack:
        node = stack.pop()
        if node in reachable:
            raise ValueError(f"blocks.parent_id cycle at {node}")
        reachable.add(node)
        stack.extend(child.id for child in children.get(node, []))
    if len(reachable) != len(blocks):
        raise ValueError("blocks unreachable from any root: parent cycle")
    return children


def _is_ordered(block: TreeBlock) -> bool:
    raw = (block.properties or {}).get("marker") or DEFAULT_LIST_MARKER
    return _ORDERED_RE.match(raw) is not None


def _same_list_run(previous: TreeBlock | None, current: TreeBlock) -> bool:
    """Whether `current` continues the list `previous` belongs to.

    The block model has no list-container shape, so two adjacent lists are
    indistinguishable from one -- except by their markers. A bullet run
    followed by an ordered run is two lists, and treating them as one both
    renumbers the second wrongly (it continues the first's count) and emits
    them without the blank line that keeps them apart.
    """
    if previous is None or previous.type != "list" or current.type != "list":
        return False
    return _is_ordered(previous) == _is_ordered(current)


def _marker_for(block: TreeBlock, ordinal: int) -> str:
    raw = (block.properties or {}).get("marker") or DEFAULT_LIST_MARKER
    m = _ORDERED_RE.match(raw)
    if m:
        return f"{ordinal}{m.group(1)}"
    return raw


def _fence_for(text: str) -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def _separator(parent: TreeBlock | None, siblings: list[TreeBlock], index: int) -> str:
    current = siblings[index]
    if current.type == "table_row":
        return "\n"                    # rows are lines of their table
    if current.type == "list" and index > 0 and _same_list_run(
        siblings[index - 1], current
    ):
        return "\n"                    # tight list, same run
    if current.type == "list" and parent is not None and parent.type == "list":
        return "\n"                    # nested item under its parent item
    return "\n\n"


def serialize_tree(
    blocks: Sequence[TreeBlock], *, frontmatter: str | None = None
) -> SerializedDocument:
    """Tree in, source plus per-block spans out.

    ``frontmatter`` re-emits the leading ``---`` fence increment 2 filed into
    ``documents.properties.frontmatter``. It is a stored value being restored,
    not a reconstruction: without it every conversion of a corpus document
    would drop its front fence.
    """
    children = _children_map(blocks)
    out: list[str] = []
    placed: list[PlacedBlock] = []
    offset = 0
    walk = 0

    def write(piece: str) -> None:
        nonlocal offset
        out.append(piece)
        offset += len(piece)

    if frontmatter is not None:
        write(f"---\n{frontmatter}\n---\n")

    def emit_lines(lines: list[str], prefix: str) -> tuple[int, int]:
        start = offset
        for i, line in enumerate(lines):
            if i:
                write("\n")
            write(prefix + line if line else prefix.rstrip())
        return (start, offset)

    def emit(block: TreeBlock, prefix: str, ordinal: int) -> None:
        nonlocal walk
        props = block.properties or {}
        child_prefix = prefix
        if block.type == "heading":
            level = int(props.get("level") or 1)
            span = emit_lines([f"{'#' * level} {block.text}"], prefix)
        elif block.type == "code":
            fence = _fence_for(block.text)
            info = props.get("language") or ""
            span = emit_lines(
                [fence + info, *block.text.split("\n"), fence], prefix,
            )
        elif block.type == "quote":
            lines = block.text.split("\n") if block.text else []
            span = emit_lines([f"> {line}" for line in lines] or [">"], prefix)
            child_prefix = prefix + "> "
        elif block.type == "list":
            marker = _marker_for(block, ordinal)
            lines = block.text.split("\n") if block.text else [""]
            indent = " " * (len(marker) + 1)
            span = emit_lines(
                [f"{marker} {lines[0]}", *(indent + line for line in lines[1:])],
                prefix,
            )
            child_prefix = prefix + indent
        elif block.type == "table":
            header = props.get("header") or [c.strip() for c in block.text.split("|")]
            aligns = props.get("alignments") or [None] * len(header)
            delim = {"left": ":---", "right": "---:", "center": ":---:"}
            span = emit_lines([
                "| " + " | ".join(header) + " |",
                "| " + " | ".join(delim.get(a or "", "---") for a in aligns) + " |",
            ], prefix)
        elif block.type == "divider":
            span = emit_lines(["---"], prefix)
        elif block.type == "table_row":
            cells = props.get("cells") or [c.strip() for c in block.text.split("|")]
            span = emit_lines(["| " + " | ".join(cells) + " |"], prefix)
        elif block.type == "html":
            # Verbatim. The run is opaque to markdown, so there is nothing to
            # normalise and any normalisation would change what re-parses.
            span = emit_lines(block.text.split("\n") if block.text else [""], prefix)
        else:  # paragraph and anything normalised to it
            span = emit_lines(block.text.split("\n") if block.text else [""], prefix)

        placed.append(PlacedBlock(block.id, walk, span))
        walk += 1

        kids = children.get(block.id, [])
        list_ordinal = 0
        for i, kid in enumerate(kids):
            previous = kids[i - 1] if i else None
            if kid.type != "list":
                list_ordinal = 0
            elif _same_list_run(previous, kid):
                list_ordinal += 1
            else:
                list_ordinal = 1        # a new list starts its own count
            write(_separator(block, kids, i))
            emit(kid, child_prefix, list_ordinal)

    roots = children[None]
    list_ordinal = 0
    for i, root in enumerate(roots):
        previous = roots[i - 1] if i else None
        if root.type != "list":
            list_ordinal = 0
        elif _same_list_run(previous, root):
            list_ordinal += 1
        else:
            list_ordinal = 1
        if i:
            write(_separator(None, roots, i))
        emit(root, "", list_ordinal)

    return SerializedDocument(content="".join(out), placed=placed)


def derive_markers(
    blocks: Sequence[TreeBlock],
    content: str | None,
    spans: dict[UUID, tuple[int, int]],
) -> list[TreeBlock]:
    """Backfill the markers the parser discarded, from the stored source.

    A ``list`` block does not record whether it was ``-`` or ``1.``, so on the
    first block verb against a content-first document each list block's marker
    is read out of ``content[char_span]``. A block with no span, or a document
    with no stored content, keeps its properties -- deterministic, merely less
    faithful. Quote and heading markers need no record: ``>`` and ATX ``#`` are
    the only spellings the serialiser emits and the parser accepts.
    """
    if not content:
        return list(blocks)
    out: list[TreeBlock] = []
    for block in blocks:
        span = spans.get(block.id)
        if block.type != "list" or span is None:
            out.append(block)
            continue
        match = _MARKER_RE.match(content[span[0]:span[1]])
        if match is None:
            out.append(block)
            continue
        props = {**(block.properties or {}), "marker": match.group(1)}
        out.append(replace(block, properties=props))
    return out


# Token kinds the block model has no shape for. The parser mints no block for
# these, so nothing in a tree records them and no serialiser can put them back.
#
# `hr` left this set on 2026-09-02 when it became the `divider` block type, and
# `html_block` on 2026-09-07 when it became `html`. The set is empty rather
# than deleted: the guard below is the shape that keeps a future construct from
# converting lossily, and an empty frozenset says "nothing is unrepresentable
# today", which is a different claim from "we stopped checking".
#
# `html_inline` was never reachable here and is not unrepresentable anyway:
# inline tokens are children of an `inline` token, so a top-level scan never
# sees one, and the raw tag survives in the paragraph's own text.
_UNREPRESENTABLE_TOKENS: frozenset[str] = frozenset()


def reproduces_source(
    blocks: Sequence[TreeBlock],
    content: str,
    spans: dict[UUID, tuple[int, int]],
    *,
    frontmatter: str | None = None,
) -> bool:
    """Whether this document can become block-first without losing anything.

    The conversion guard (review M-2). The question is NOT whether the
    serialiser reproduces the source byte-for-byte -- it legitimately
    reformats, emitting a table's delimiter row as ``| --- | ---: |`` where
    the author wrote ``|---|---:|``, and a byte comparison would refuse every
    document containing a table for a difference that loses nothing.

    The question is whether the source contains a construct the block model
    cannot represent. Those are detected in the token stream directly, which
    is both stricter and looser than a text diff in the right places: a
    dropped construct re-parses to a tree identical to the original's, so
    comparing trees would miss it, while whitespace never trips it.

    **Do not relax this by removing a token kind to make more documents
    convert.** The way to convert more documents is to make the parser
    represent those shapes as blocks -- a parser change, not a guard change.
    """
    from markdown_it import MarkdownIt

    from app.services.document_parsers import split_frontmatter

    # Parse the BODY, not the whole file. A document's opening `---` fence is
    # itself an `hr` token, so tokenising the raw content refused every
    # document carrying frontmatter -- and no imported document has any, which
    # is exactly why the corpus measurement did not catch it.
    _, body_start = split_frontmatter(content)
    body = content[body_start:]

    env: dict = {}
    tokens = MarkdownIt("commonmark").enable("table").parse(body, env)
    if any(token.type in _UNREPRESENTABLE_TOKENS for token in tokens):
        return False
    # Link reference definitions are consumed into `env` and mint no token at
    # all, so they need their own check: a converted document would lose the
    # definition and leave every reference to it dangling.
    if env.get("references"):
        return False

    # A construct can be representable and still be missing from THIS tree.
    # `ingest_document` returns UNCHANGED on a byte-identical re-push without
    # touching blocks, so a document filed before `divider` existed has `---`
    # in its content and no divider row -- and converting it would drop every
    # rule, which is the exact failure this guard exists to prevent. Comparing
    # counts catches a stale tree without needing to know why it is stale.
    for token_type, block_type in (("hr", "divider"), ("html_block", "html")):
        in_source = sum(1 for t in tokens if t.type == token_type)
        in_tree = sum(1 for b in blocks if b.type == block_type)
        if in_source != in_tree:
            return False
    return True

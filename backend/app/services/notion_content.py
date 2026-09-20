"""Translating one Notion page's markdown into a page block tree."""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import unquote
from uuid import UUID

from app.services.block_serializer import TreeBlock, serialize_tree
from app.services.block_verbs import _check_page_nesting
from app.services.document_parsers import split_frontmatter
from app.services.notion_archive import NotionArchive
from app.services.page_attachments import attachment_url
# `_parse` and `_flatten_headings` are page_door's own: reproducing them here
# would let the import and the create door drift into parsing a page two ways.
from app.services.page_door import _flatten_headings, _parse

_FENCE = re.compile(r"^[ \t]*(```+|~~~+)")


@dataclass(frozen=True)
class LinkSpan:
    start: int
    end: int
    is_image: bool
    label: str
    destination: str


def resolve_target(target: str, from_entry: str) -> str:
    """A link target as an entry name, resolved against its page's folder.

    The tree, the translation and the importer's attachment scan must agree on
    what a link points at, so all three call this one function.
    """
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
    while lines and not lines[0].strip():
        lines.pop(0)
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

        resolved = resolve_target(unquote(destination.split("#")[0]), entry_name)
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
            resolved = resolve_target(unquote(span.destination.split("#")[0]), entry_name)
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
    # The page-parent rule is asserted on the result. A violation is a bug in
    # this module, not a refusal the caller can act on.
    by_id = {block.id: block for block in blocks}
    for block in blocks:
        _check_page_nesting(
            by_id.get(block.parent_id) if block.parent_id else None, block
        )
    return blocks

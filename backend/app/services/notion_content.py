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

"""The marker-bounded managed block (doc 15 §3.1–§3.2) — T3.09.

**This module never touches a filesystem, and that is the feature.** Doc 15's
trust posture is that inject is a *client-side pull-then-write* cycle: the
client asks the server for a labelled selection, and the client writes its own
context file. A server-side write would invert that boundary entirely. So
everything here is text in, text out — the caller owns reading the file, and
the caller owns writing it back. ``tests/test_inject_block.py`` asserts the
absence structurally, because "we just won't do that" is not a boundary.

**Darkmem owns the bytes between two markers and nothing else.** Inside the
file the client writes, a human's own rules live above and below the block, so
a refresh strips the region between the markers and rewrites only that — the
same strip-before-rewrite discipline invariant 8 gives re-extraction, applied
to a text file. Repeated refresh is therefore a fixed point: no second block
accumulates under any cadence.

**A damaged marker pair refuses to write, and the refusal is the design.** The
tempting behaviour is to find the first plausible region and use it — which is
exactly how a writer eats whatever a stray marker happened to bracket. Missing,
unpaired, inverted and duplicated markers all raise
:class:`ManagedBlockCorrupted` instead, naming what was actually found, because
the human fixes this in their own file and a bare "corrupted" sends them
looking at darkmem instead of at their markers.

The one marker style here is Markdown's comment syntax, which is what every
tool in doc 15 §3.3's transport matrix reads today. **Per-tool comment syntax
is T3.11's**, and the parameterisation belongs with the adapters that need it —
adding a style table here before a second style exists would be scaffolding for
a caller that does not exist.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "MARKER_BEGIN",
    "MARKER_END",
    "ManagedBlockCorrupted",
    "apply_block",
    "remove_block",
    "render_block",
]

# Long and distinctive on purpose. The markers are a fixed sentinel, so a human
# who pastes one into their own notes has declared a block there — there is no
# way to distinguish "the writer's marker" from "the same bytes typed by hand",
# and a shorter token would make the collision plausible rather than contrived.
MARKER_BEGIN = "<!-- darkmem:begin -->"
MARKER_END = "<!-- darkmem:end -->"


class ManagedBlockCorrupted(RuntimeError):
    """The file's markers are not a single well-formed pair, so nothing is written.

    Raised rather than repaired. Every repair strategy — take the first begin,
    take the outermost pair, drop the stray marker — writes into a region the
    writer inferred rather than one the writer owns, and the bytes it
    overwrites are the human's.
    """


@dataclass(frozen=True)
class _Bounds:
    begin: int
    end: int


def _locate(text: str) -> _Bounds | None:
    """The single well-formed pair, ``None`` if absent, raise if damaged.

    Counting both markers before looking at either one is what makes the
    duplicate cases fail rather than resolve: ``find`` alone would happily
    return the first begin in a file carrying three.
    """
    begins = text.count(MARKER_BEGIN)
    ends = text.count(MARKER_END)

    if begins == 0 and ends == 0:
        return None
    if begins != 1 or ends != 1:
        raise ManagedBlockCorrupted(
            f"expected exactly one {MARKER_BEGIN} and one {MARKER_END}; "
            f"found {begins} and {ends}. Refusing to write: with the pair "
            f"ambiguous, any region this writer picked would be a guess about "
            f"which bytes are darkmem's and which are yours."
        )

    begin = text.index(MARKER_BEGIN)
    end = text.index(MARKER_END)
    if end < begin:
        raise ManagedBlockCorrupted(
            f"{MARKER_END} appears before {MARKER_BEGIN}. Refusing to write: "
            f"the region between them is not a block, and rewriting it would "
            f"replace whatever lies outside the intended one."
        )
    return _Bounds(begin=begin, end=end)


def render_block(
    items: list[str],
    *,
    project: str,
    generated_at: str,
    token_budget: int,
) -> str:
    """The block body: a provenance header, then one line per item.

    ``generated_at`` is passed in rather than read from a clock so this stays
    a pure function — the caller already knows when it pulled, and a clock read
    here would make the output untestable for equality, which is what
    idempotence is asserted on.

    An item carrying a marker is refused. It is the one way rendering could
    corrupt the file it is written into: the embedded sentinel would create a
    second pair, and the *next* refresh would then refuse on damage darkmem
    itself caused — a failure the operator could not explain from their own
    edits.
    """
    for item in items:
        _refuse_embedded_marker(item, "an injected item")

    header = (
        f"generated {generated_at}, project {project}, "
        f"{len(items)} item{'' if len(items) == 1 else 's'}, "
        f"{token_budget} tokens"
    )
    # The header interpolates `project` and `generated_at`, both free-form,
    # so the composed block is checked as a whole rather than only its items.
    composed = "\n".join([header, *items])
    _refuse_embedded_marker(composed, "the rendered block")
    return composed


def _refuse_embedded_marker(candidate: str, what: str) -> None:
    """Refuse any text that would put a second sentinel inside the block.

    Checked at the *write* boundary rather than only in :func:`render_block`,
    because that is where the damage would actually be done. The item check
    below was not enough: ``render_block`` also interpolates ``project`` and
    ``generated_at`` into its header, both free-form strings, and a caller may
    hand :func:`apply_block` a block this module never rendered at all (a
    per-tool adapter, T3.11). A marker reaching the file this way writes a
    second pair, and the *next* refresh and uninstall both refuse — locking
    the human out of their own file on damage darkmem itself caused, which is
    the exact failure the item check exists to prevent.
    """
    if MARKER_BEGIN in candidate or MARKER_END in candidate:
        raise ManagedBlockCorrupted(
            f"{what} contains a darkmem marker; refusing to write. Embedding "
            f"it would split the managed block in two and the next refresh "
            f"would refuse on a file darkmem broke."
        )


def apply_block(text: str, block: str) -> str:
    """Return ``text`` with the managed block rewritten to ``block``.

    Absent markers append a fresh pair; a present pair is overwritten in place;
    a damaged pair raises. Everything outside the two markers is returned
    unchanged **byte for byte** — no line-ending normalisation, no whitespace
    stripping. A writer that tidied a user's file has still edited it, and the
    diff would land in their commit rather than in ours.
    """
    _refuse_embedded_marker(block, "the block being written")
    bounds = _locate(text)
    body = f"{MARKER_BEGIN}\n{block}\n{MARKER_END}" if block else f"{MARKER_BEGIN}\n{MARKER_END}"

    if bounds is None:
        separator = "" if text == "" or text.endswith("\n") else "\n"
        return f"{text}{separator}{body}\n"

    return text[: bounds.begin] + body + text[bounds.end + len(MARKER_END) :]


def remove_block(text: str) -> str:
    """Return ``text`` with the managed block **and its markers** gone.

    Uninstall must take the sentinels with it: a leftover pair would be read by
    the next install as its own block, so "removed" would silently mean
    "emptied". A damaged pair raises here too — removal is a write, and a
    damaged pair is exactly when "just clean it up" is most tempting and most
    destructive.
    """
    bounds = _locate(text)
    if bounds is None:
        return text
    return text[: bounds.begin] + text[bounds.end + len(MARKER_END) :]

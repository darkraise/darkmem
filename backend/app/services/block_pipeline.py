"""The block pipeline — doc 16 §3's Tier-B variant, end to end (TH1.04).

This is the module that makes doc 16 §3's flowchart a single callable: a
filed source goes through the change gate, is parsed into a block tree by the
parser its ``source_type`` names, and its prior blocks are stripped before the
new set is written. TH1.02 owns the gate and the writer; TH1.03 owns the
parsers; nothing joined them, and the join is where the three properties this
module is accountable for actually live.

**It is emphatically not the five-phase memory pipeline, and that is a
structural claim rather than a promise.** Doc 16 §3's decision is that filing
a document must not run extraction over its content — a raw document is
candidate signal, and extracting every filed PDF would flood the L1 graph with
assertions nobody vouched for. So this path reaches blocks and stops; the
graph is reached only through the on-demand lift in §5.
``tests/test_block_pipeline.py`` proves it by walking the transitive
``app.*`` import closure of this module and asserting
``app.services.pipeline`` is not in it, then scanning every file in that
closure for any AST-visible route to ``process_batch``. A prose firewall goes
stale; this one fails the build.

**The atomic replace lives in the writer, and this module no longer repeats
it.** TH1.04 opened the SAVEPOINT here because ``file_document`` owned none;
that guarded the one door this module serves and left every other direct
caller holding the same foot-gun, which is what TH1.18 closed by moving the
guard into ``file_document`` itself. Both doors below therefore inherit it —
a failure anywhere in parse, strip or write rolls back to the writer's own
mark, the prior tree and the prior hash both survive, and the session stays
usable for the caller. Re-opening a savepoint out here would nest a second one
inside it per call and guard nothing the writer does not already guard.

**The parse stays a callable all the way down.** ``bind_parser`` binds the
parser to its content and returns it *uncalled*; the gate is what decides
whether it ever runs. Materialising the block list here — the obvious
simplification — would pay the expensive half of the pipeline before the gate
could refuse it, which is the whole reason TH1.02's signature takes a callable
instead of a list.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.document_ingest import BlockDraft, DocumentIngest, file_document
from app.services.document_parsers import (
    SOURCE_TYPE_MARKDOWN,
    SOURCE_TYPE_NOTE,
    SOURCE_TYPE_PDF,
    parse_markdown,
    parse_note,
    parse_pdf,
    split_frontmatter,
)

__all__ = [
    "PARSERS",
    "URI_SUFFIX_SOURCE_TYPES",
    "UnsupportedSource",
    "bind_parser",
    "ingest_document",
    "resolve_source_type",
]


class UnsupportedSource(Exception):
    """No parser serves this source, so no block tree can be produced.

    Deliberately not ``DocumentParseError``: nothing was parsed. The two are
    different failures for the caller — an unparseable PDF is a property of
    the content, an unroutable ``source_type`` is a property of the request.
    """


PARSERS: dict[str, Callable[..., Sequence[BlockDraft]]] = {
    SOURCE_TYPE_PDF: parse_pdf,
    SOURCE_TYPE_MARKDOWN: parse_markdown,
    SOURCE_TYPE_NOTE: parse_note,
}

# Inference is a convenience for the realistic caller — a sweep over a corpus
# holds paths, not source types — and it is deliberately a *closed* map that
# refuses rather than guessing. A suffix absent from here is an
# `UnsupportedSource`, never a silent fall back to the note parser, which
# would file a PDF's compressed bytes as prose.
URI_SUFFIX_SOURCE_TYPES: dict[str, str] = {
    ".pdf": SOURCE_TYPE_PDF,
    ".md": SOURCE_TYPE_MARKDOWN,
    ".markdown": SOURCE_TYPE_MARKDOWN,
    ".txt": SOURCE_TYPE_NOTE,
    ".text": SOURCE_TYPE_NOTE,
}


def resolve_source_type(*, source_type: str | None = None, uri: str | None = None) -> str:
    """The parser key for this source, from the declared type or the uri.

    An explicit `source_type` wins and is checked rather than trusted: a value
    with no parser behind it must fail here, where the caller can read why,
    instead of at a `KeyError` inside the parse.
    """
    if source_type is not None:
        if source_type not in PARSERS:
            raise UnsupportedSource(
                f"no parser serves source_type {source_type!r}; "
                f"known types: {', '.join(sorted(PARSERS))}"
            )
        return source_type

    suffix = _uri_suffix(uri)
    if suffix in URI_SUFFIX_SOURCE_TYPES:
        return URI_SUFFIX_SOURCE_TYPES[suffix]
    raise UnsupportedSource(
        f"cannot infer a source_type from uri {uri!r}: pass source_type "
        f"explicitly, one of {', '.join(sorted(PARSERS))}"
    )


def _uri_suffix(uri: str | None) -> str:
    """The lowercased final suffix of `uri`'s path, query and fragment aside.

    Split before suffixing: `?v=2` and `#page=3` are ordinary in a document
    locator and both end in something that is not a suffix at all.
    """
    if not uri:
        return ""
    path = urlsplit(uri).path or uri
    tail = path.rsplit("/", 1)[-1]
    return f".{tail.rsplit('.', 1)[-1].lower()}" if "." in tail else ""


def bind_parser(
    source_type: str, content: str | bytes
) -> Callable[[], Sequence[BlockDraft]]:
    """Bind the parser for `source_type` to `content` without calling it."""
    parser = PARSERS[resolve_source_type(source_type=source_type)]
    return lambda: parser(content)


def _with_frontmatter(
    resolved_type: str, content: str | bytes, properties: dict | None
) -> dict | None:
    """Fold the source's own frontmatter into the document's properties.

    Parser-derived, so it wins over a caller-passed ``frontmatter`` key: the
    value restates the content, and the content is what was filed. Recomputed
    on every filing -- the writer overwrites properties wholesale, which keeps
    the stored value in step with the stored content by construction.

    It lives here rather than in the parser because a parser returns only
    ``Sequence[BlockDraft]`` and cannot write document properties; this is the
    layer that already routes ``source_type``.
    """
    if resolved_type != SOURCE_TYPE_MARKDOWN or not isinstance(content, str):
        return properties
    frontmatter, _ = split_frontmatter(content)
    if frontmatter is None:
        return properties
    return {**(properties or {}), "frontmatter": frontmatter}


async def ingest_document(
    session: AsyncSession,
    *,
    project: str,
    content: str | bytes,
    uri: str | None = None,
    document_id: UUID | None = None,
    source_type: str | None = None,
    title: str | None = None,
    properties: dict | None = None,
    actor: str | None = None,
    api_key_id: UUID | None = None,
    source: str | None = None,
    expected_hash: str | None = None,
    force_reparse: bool = False,
    carry_fingerprint: str | None = None,
    max_blocks: int | None = None,
) -> DocumentIngest:
    """File one source through the block pipeline. Does not commit.

    Raises whatever went wrong — an unparseable source, a malformed tree, a
    database error — after `file_document`'s SAVEPOINT has already rolled the
    whole filing back, so a caller that catches sees the document exactly as
    it was and a session it can keep using.
    """
    resolved_type = resolve_source_type(source_type=source_type, uri=uri)
    parse = bind_parser(resolved_type, content)
    properties = _with_frontmatter(resolved_type, content, properties)
    return await file_document(
        session,
        project=project,
        content=content,
        parse=parse,
        uri=uri,
        document_id=document_id,
        title=title,
        source_type=resolved_type,
        properties=properties,
        actor=actor,
        api_key_id=api_key_id,
        source=source,
        expected_hash=expected_hash,
        force_reparse=force_reparse,
        carry_fingerprint=carry_fingerprint,
        max_blocks=max_blocks,
    )

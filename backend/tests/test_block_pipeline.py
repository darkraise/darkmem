"""The block pipeline — tree, spans, idempotence, and the firewall (TH1.04).

Four properties carry this module, and each is written so that removing the
thing it guards makes it fail.

**Structure and spans are proven against the source, not against the drafts.**
A test that files a hand-built draft list and reads the same shape back proves
the writer round-trips a list; it says nothing about whether a *document's*
structure survived. So the tree tests run real markdown and real notes through
the real parsers and then reconstruct the outline from the stored rows,
comparing it to the source's own nesting. The span tests slice the original
source with the stored ``int4range`` bounds and require the source text back,
and probe containment with the ``@>`` operator a grounded citation would
actually use — a stored span that is off by one, or inclusive where the writer
meant half-open, fails there and nowhere else.

**Idempotence is counted, not inspected.** Re-filing the same content is
TH1.02's short-circuit and is already proven there. What is proven here is the
harder half: a document driven *through* a change and back again lands on
exactly the tree it started with, with no residue — asserted on the full block
tuple set, on a block-id disjointness check (ids are minted fresh, so any
survivor is a strip that missed), and on a statement counter requiring exactly
one DELETE and one INSERT per changed re-ingest. A writer that stripped twice,
wrote per row, or skipped the strip fails one of the three.

**The atomic replace is drilled, not asserted.** ``test_without_the_savepoint_*``
runs the identical failure through the unguarded body and shows the damage:
the blocks gone *and* the document row already carrying the new
``content_hash``, which is the corruption that never announces itself — the
next re-file of that same content short-circuits on a gate agreeing with a
tree that was never written. It is committed as a standing regression in the
shape TH1.03 established for its own SAVEPOINT, and its guarded twin runs the
same failure through the same door to show both halves surviving.

**The unguarded body is contained by a scan, not by its underscore.** Since
TH1.18 the SAVEPOINT is ``file_document``'s default and the drills reach past
it through a private entry point, so "only tests can take the opt-out" has to
be a checked property: every ``.py`` under ``app/``, ``scripts/`` and
``migrations/`` is parsed and every AST-visible route to that name — import,
attribute, bare name, string literal — is an offence, with the sole exemption
being the nodes inside ``file_document``'s own body. A positive control feeds
the same scanner a file that does reach it, so a scan that stopped matching
fails rather than passing silently.

**The firewall is structural.** Doc 16 §3's decision that filing a document
does not run the five-phase pipeline is enforced by walking this module's
transitive ``app.*`` import closure and scanning every file in it for any
AST-visible route to ``process_batch``. The negative control seeds the same
scan with a module that genuinely reaches the pipeline, so a scan that stopped
matching would fail rather than pass silently.
"""
from __future__ import annotations

import ast
import pathlib
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from app.repositories import documents as documents_repo
from app.services import block_pipeline as bp
from app.services.document_ingest import (
    CREATED,
    UNCHANGED,
    UPDATED,
    BlockDraft,
    DocumentFileFailure,
    DocumentIngest,
    _file_document_without_savepoint,
    file_document,
)
from app.services.document_parsers import (
    SOURCE_TYPE_MARKDOWN,
    SOURCE_TYPE_NOTE,
    SOURCE_TYPE_PDF,
    DocumentParseError,
)

from ._reachability_scan import ReachabilityRules, find_forbidden_reach
from .conftest import test_engine
# TH1.03's minimal-PDF writer, reused rather than copied: a second generator
# would be a second set of bytes to keep agreeing with pdfplumber's reader.
from .test_document_parsers import _make_pdf

BACKEND = pathlib.Path(__file__).resolve().parent.parent


# ── reading the stored tree back ────────────────────────────────────


async def _blocks(session, document_id) -> list[dict]:
    """Every stored block of `document_id`, in reading order, with its span
    bounds pulled out of the `int4range` by Postgres rather than by us."""
    rows = (await session.execute(
        text(
            "SELECT id, parent_id, order_index, type, text, properties, "
            "       lower(char_span) AS lo, upper(char_span) AS hi "
            "FROM blocks WHERE document_id = CAST(:d AS uuid) ORDER BY order_index"
        ),
        {"d": str(document_id)},
    )).mappings().all()
    return [dict(row) for row in rows]


def _outline(blocks: list[dict]) -> list[str]:
    """The stored tree rendered as an indented outline.

    Reconstructed from `parent_id` alone, so it is a statement about what the
    database holds — a writer that flattened the tree or reparented a subtree
    renders differently even when every row is otherwise identical.
    """
    depth = {}
    lines = []
    for block in blocks:
        parent = block["parent_id"]
        level = 0 if parent is None else depth[parent] + 1
        depth[block["id"]] = level
        lines.append(f"{'  ' * level}{block['type']}: {block['text']}")
    return lines


def _shape(blocks: list[dict]) -> list[tuple]:
    """Everything about a tree except the ids, which are minted fresh."""
    position = {block["id"]: index for index, block in enumerate(blocks)}
    return [
        (
            block["order_index"],
            block["type"],
            block["text"],
            block["lo"],
            block["hi"],
            None if block["parent_id"] is None else position[block["parent_id"]],
        )
        for block in blocks
    ]


class _StatementRecorder:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def __call__(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    def matching(self, *needles: str) -> list[str]:
        return [
            statement
            for statement in self.statements
            if all(needle in statement for needle in needles)
        ]


async def _observe(coro_factory):
    recorder = _StatementRecorder()
    event.listen(test_engine.sync_engine, "before_cursor_execute", recorder)
    try:
        result = await coro_factory()
    finally:
        event.remove(test_engine.sync_engine, "before_cursor_execute", recorder)
    return result, recorder


class _Parser:
    def __init__(self, drafts) -> None:
        self.drafts = list(drafts)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.drafts


async def _content_hash(session, document_id) -> str | None:
    return (await session.execute(
        text("SELECT content_hash FROM documents WHERE id = CAST(:d AS uuid)"),
        {"d": str(document_id)},
    )).scalar_one()


# ── the block tree preserves document structure ─────────────────────


MARKDOWN = """# Release notes

Shipped this week.

## Retrieval

The fusion arm moved.

- first item
- second item
  - nested item

> a quoted remark

```python
print("hello")
```

## Storage

Nothing changed here.
"""


@pytest.mark.asyncio
async def test_markdown_document_structure_survives_the_round_trip(session):
    result = await bp.ingest_document(
        session, project="default", uri=f"file:///{uuid4()}.md", content=MARKDOWN,
    )
    await session.flush()

    assert result.outcome == CREATED
    outline = _outline(await _blocks(session, result.document_id))

    assert outline == [
        "heading: Release notes",
        "  paragraph: Shipped this week.",
        "  heading: Retrieval",
        "    paragraph: The fusion arm moved.",
        "    list: first item",
        "    list: second item",
        "      list: nested item",
        "    quote: a quoted remark",
        '    code: print("hello")',
        "  heading: Storage",
        "    paragraph: Nothing changed here.",
    ]


@pytest.mark.asyncio
async def test_a_deeper_heading_does_not_reparent_onto_a_shallower_sibling(session):
    """`## B` after `## A` must close A rather than nest inside it. A writer
    that stored `parent_id` from a stack it never popped renders A's subtree
    swallowing B, and every other assertion in this file still passes."""
    source = "# Top\n\n## A\n\nunder a\n\n## B\n\nunder b\n"
    result = await bp.ingest_document(
        session, project="default", uri=f"file:///{uuid4()}.md", content=source,
    )
    await session.flush()

    assert _outline(await _blocks(session, result.document_id)) == [
        "heading: Top",
        "  heading: A",
        "    paragraph: under a",
        "  heading: B",
        "    paragraph: under b",
    ]


@pytest.mark.asyncio
async def test_reading_order_is_strictly_increasing_across_the_whole_tree(session):
    result = await bp.ingest_document(
        session, project="default", uri=f"file:///{uuid4()}.md", content=MARKDOWN,
    )
    await session.flush()
    blocks = await _blocks(session, result.document_id)
    order = [block["order_index"] for block in blocks]
    assert order == sorted(order)
    assert len(set(order)) == len(order)


@pytest.mark.asyncio
async def test_pdf_page_provenance_reaches_the_stored_properties(session):
    """Doc 16 §2 puts page and bbox on `blocks.properties`; the jsonb bind is
    the shape asyncpg cannot infer, so this is also the CAST's proof."""
    pdf = _make_pdf([
        [("Report", 72, 720, 20), ("First page body.", 72, 690, 12)],
        [("Second page body.", 72, 720, 12)],
    ])
    result = await bp.ingest_document(
        session, project="default", uri=f"file:///{uuid4()}.pdf", content=pdf,
    )
    await session.flush()

    blocks = await _blocks(session, result.document_id)
    pages = [block["properties"]["page"] for block in blocks]
    assert pages == sorted(pages)
    assert set(pages) == {1, 2}
    for block in blocks:
        assert set(block["properties"]["bbox"]) == {"x0", "top", "x1", "bottom"}


# ── the block tree preserves char spans ─────────────────────────────


@pytest.mark.asyncio
async def test_stored_spans_slice_the_source_back_out_of_it(session):
    """A note's spans are exact for a heading or a paragraph — the source
    sliced by the stored bounds is the block's own text, character for
    character. A list item's span covers its marker, which its text does not,
    so that one is a containment claim; asserting containment for all of them
    would let a bound drift by one without failing."""
    source = (
        "Weekly log\n\nThe deploy landed on Tuesday.\n\n"
        "- checked the dashboards\n- rotated the key\n"
    )
    result = await bp.ingest_document(
        session, project="default", source_type=SOURCE_TYPE_NOTE, content=source,
    )
    await session.flush()

    blocks = await _blocks(session, result.document_id)
    assert {block["type"] for block in blocks} == {"heading", "paragraph", "list"}
    for block in blocks:
        sliced = source[block["lo"]:block["hi"]]
        if block["type"] == "list":
            assert block["text"] in sliced
        else:
            assert sliced == block["text"], (
                f"span [{block['lo']},{block['hi']}) sliced {sliced!r}, "
                f"not the block text {block['text']!r}"
            )


@pytest.mark.asyncio
async def test_a_markdown_span_covers_the_source_line_including_its_marker(session):
    """Doc 16 §2 fixes `char_span` as an anchor into the *source*, not a mirror
    of `blocks.text`. A heading's text has the `#` stripped; its span does not."""
    source = "# Release notes\n\nBody.\n"
    result = await bp.ingest_document(
        session, project="default", uri=f"file:///{uuid4()}.md", content=source,
    )
    await session.flush()

    heading = (await _blocks(session, result.document_id))[0]
    assert heading["text"] == "Release notes"
    assert source[heading["lo"]:heading["hi"]] == "# Release notes"


@pytest.mark.asyncio
async def test_sibling_spans_are_half_open_and_never_double_claim_a_boundary(session):
    source = "Alpha paragraph here.\n\nBeta paragraph here.\n\nGamma paragraph here.\n"
    result = await bp.ingest_document(
        session, project="default", source_type=SOURCE_TYPE_NOTE, content=source,
    )
    await session.flush()

    blocks = await _blocks(session, result.document_id)
    assert len(blocks) == 3
    for earlier, later in zip(blocks, blocks[1:]):
        assert earlier["hi"] <= later["lo"], (
            "two blocks claim the same source offset, so a containment probe "
            "for a cited span answers twice"
        )


@pytest.mark.asyncio
async def test_no_parser_stores_an_empty_span(session):
    """An empty `int4range` is the span failure that never announces itself.

    `_span_literal` accepts `end == start` and Postgres stores `[5,5)` as
    `empty`, whose `lower()`/`upper()` are NULL and which `@>` answers false
    for every offset — so the block is retrievable and its citation anchor
    resolves to nothing, silently. Asserting the *bounds* of a real ingest
    would not catch it (a NULL bound compares as neither too high nor too
    low), so `isempty` is asked directly.

    Deliberately not a claim about the half-open convention itself: Postgres
    canonicalises every discrete range to `[lo,hi)`, so a probe asking whether
    `char_span @> lower(char_span)` is a tautology about the type rather than
    a statement about this writer.
    """
    sources = [
        dict(source_type=SOURCE_TYPE_MARKDOWN, content=MARKDOWN),
        dict(source_type=SOURCE_TYPE_NOTE, content="Weekly log\n\n- one item\n- two\n"),
        dict(
            source_type=SOURCE_TYPE_PDF,
            content=_make_pdf([[("Report", 72, 720, 20), ("Body text.", 72, 690, 12)]]),
        ),
    ]
    ids = []
    for source in sources:
        result = await bp.ingest_document(session, project="default", **source)
        ids.append(result.document_id)
    await session.flush()

    rows = (await session.execute(
        text(
            "SELECT type, isempty(char_span) AS empty FROM blocks "
            "WHERE document_id = ANY(CAST(:ids AS uuid[])) AND char_span IS NOT NULL"
        ),
        {"ids": [str(i) for i in ids]},
    )).mappings().all()

    assert len(rows) >= 10, f"only {len(rows)} spans reached the assertion"
    assert [row["type"] for row in rows if row["empty"]] == []


# ── re-ingest is idempotent ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_document_driven_through_a_change_and_back_lands_on_its_first_tree(session):
    """The idempotence claim that bites. Re-filing *unchanged* content is
    TH1.02's short-circuit and proves nothing about the write path; driving the
    document through a different revision and back exercises strip-and-rewrite
    twice and must land exactly where it started."""
    uri = f"file:///{uuid4()}.md"
    edited = MARKDOWN.replace("Nothing changed here.", "Everything changed here.")

    first = await bp.ingest_document(session, project="default", uri=uri, content=MARKDOWN)
    await session.flush()
    original = await _blocks(session, first.document_id)
    original_shape = _shape(original)
    original_ids = {block["id"] for block in original}

    await bp.ingest_document(session, project="default", uri=uri, content=edited)
    await session.flush()
    middle_ids = {block["id"] for block in await _blocks(session, first.document_id)}

    third = await bp.ingest_document(session, project="default", uri=uri, content=MARKDOWN)
    await session.flush()
    restored = await _blocks(session, third.document_id)

    assert third.document_id == first.document_id
    assert _shape(restored) == original_shape
    assert len(restored) == len(original_shape), "the tree accumulated rows"

    restored_ids = {block["id"] for block in restored}
    assert not restored_ids & original_ids, "a first-ingest block id survived"
    assert not restored_ids & middle_ids, "a stripped block id survived"


@pytest.mark.asyncio
async def test_a_changed_reingest_strips_once_and_writes_once(session):
    """Counted rather than inspected: an implementation that stripped per
    parent, wrote a row at a time, or ran the strip twice passes every
    row-shaped assertion in this file and fails here."""
    uri = f"file:///{uuid4()}.md"
    await bp.ingest_document(session, project="default", uri=uri, content=MARKDOWN)
    await session.flush()

    _, recorder = await _observe(lambda: bp.ingest_document(
        session, project="default", uri=uri,
        content=MARKDOWN.replace("Storage", "Retention"),
    ))
    await session.flush()

    deletes = recorder.matching("DELETE FROM blocks")
    inserts = recorder.matching("INSERT INTO blocks")
    assert len(deletes) == 1, f"expected one strip, got {len(deletes)}"
    assert len(inserts) == 1, (
        f"expected one block write, got {len(inserts)}; the writer is issuing "
        "a statement per row"
    )


@pytest.mark.asyncio
async def test_the_strip_is_keyed_on_document_id_and_nothing_else(session):
    """Two documents in one project sharing identical content and an identical
    tree: re-filing one must not reach the other's rows."""
    body = "Shared heading\n\nShared body text goes here.\n"
    keep = await bp.ingest_document(
        session, project="default", uri=f"file:///{uuid4()}.txt", content=body,
    )
    target_uri = f"file:///{uuid4()}.txt"
    await bp.ingest_document(session, project="default", uri=target_uri, content=body)
    await session.flush()
    keep_ids = [block["id"] for block in await _blocks(session, keep.document_id)]
    assert keep_ids

    await bp.ingest_document(
        session, project="default", uri=target_uri, content=body + "\nAnd more.\n",
    )
    await session.flush()

    assert [block["id"] for block in await _blocks(session, keep.document_id)] == keep_ids


@pytest.mark.asyncio
async def test_the_gate_still_refuses_before_the_parser_runs(session, monkeypatch):
    """The pipeline must not materialise the block list to hand it over — the
    parse is a callable so the gate can refuse in front of it. Proven with a
    parser that counts its own calls, through the pipeline's own door."""
    uri = f"file:///{uuid4()}.md"
    await bp.ingest_document(session, project="default", uri=uri, content=MARKDOWN)
    await session.flush()

    counting = _Parser([BlockDraft(text="x")])
    monkeypatch.setitem(bp.PARSERS, SOURCE_TYPE_MARKDOWN, lambda content: counting())
    result, recorder = await _observe(lambda: bp.ingest_document(
        session, project="default", uri=uri, content=MARKDOWN,
    ))

    assert result.outcome == UNCHANGED
    assert counting.calls == 0, "the parser ran behind the change gate"
    assert recorder.matching("INSERT INTO blocks") == []
    assert recorder.matching("DELETE FROM blocks") == []


@pytest.mark.asyncio
async def test_the_short_circuit_costs_one_select_plus_the_savepoint_pair(session):
    """The savepoint's declared cost, pinned so it stays a decision. Nothing
    is parsed and nothing is written; what the guard adds is two statements
    that do neither."""
    uri = f"file:///{uuid4()}.txt"
    await bp.ingest_document(session, project="default", uri=uri, content="a note body\n")
    await session.flush()

    result, recorder = await _observe(lambda: bp.ingest_document(
        session, project="default", uri=uri, content="a note body\n",
    ))

    assert result.outcome == UNCHANGED
    kinds = [statement.split()[0].upper() for statement in recorder.statements]
    assert kinds == ["SAVEPOINT", "SELECT", "RELEASE"], recorder.statements


# ── strip before rewrite: the atomic replace ────────────────────────


def _explodes():
    raise DocumentParseError("simulated: unparseable content")


@pytest.mark.asyncio
async def test_a_failed_parse_leaves_the_prior_tree_and_the_prior_hash(session, monkeypatch):
    uri = f"file:///{uuid4()}.md"
    first = await bp.ingest_document(session, project="default", uri=uri, content=MARKDOWN)
    await session.flush()
    original_ids = [block["id"] for block in await _blocks(session, first.document_id)]
    original_hash = await _content_hash(session, first.document_id)
    assert original_ids

    monkeypatch.setitem(bp.PARSERS, SOURCE_TYPE_MARKDOWN, lambda content: _explodes())
    with pytest.raises(DocumentParseError):
        await bp.ingest_document(
            session, project="default", uri=uri, content=MARKDOWN + "\nedited\n",
        )
    await session.flush()

    assert [block["id"] for block in await _blocks(session, first.document_id)] == original_ids
    assert await _content_hash(session, first.document_id) == original_hash
    # the session survived the failure — a poisoned transaction would raise here
    assert (await session.execute(text("SELECT 1"))).scalar_one() == 1


@pytest.mark.asyncio
async def test_file_document_is_atomic_without_a_caller_side_savepoint(session):
    """TH1.18's flip, asserted on the writer's own door rather than the
    pipeline's. The drill below is only evidence about the guard if the guard
    is what the default gives an arbitrary direct caller — and the replay is
    the half that matters: a filing that failed must still be re-filable."""
    uri = f"file:///{uuid4()}.md"
    edited = MARKDOWN + "\nedited\n"
    first = await file_document(
        session, project="default", uri=uri, content=MARKDOWN,
        parse=lambda: [BlockDraft(text="original")],
    )
    await session.flush()
    original_ids = [block["id"] for block in await _blocks(session, first.document_id)]
    original_hash = await _content_hash(session, first.document_id)
    assert original_ids

    with pytest.raises(DocumentParseError):
        await file_document(
            session, project="default", uri=uri, content=edited, parse=_explodes,
        )
    await session.flush()

    assert [block["id"] for block in await _blocks(session, first.document_id)] == original_ids
    assert await _content_hash(session, first.document_id) == original_hash

    replay = await file_document(
        session, project="default", uri=uri, content=edited,
        parse=lambda: [BlockDraft(text="replacement")],
    )
    await session.flush()
    assert replay.outcome == UPDATED
    assert [block["text"] for block in await _blocks(session, first.document_id)] == [
        "replacement"
    ]


@pytest.mark.asyncio
async def test_without_the_savepoint_the_same_failure_destroys_both(session):
    """The mutation drill, executable and permanent. Driven through the
    unguarded body the identical scenario leaves the blocks stripped *and* the
    document already carrying the new `content_hash` — after which the next
    re-file of that content short-circuits on a gate that agrees with a tree
    nobody ever wrote. That is what `file_document`'s default now prevents,
    and the opt-out exists so this stays runnable rather than hypothetical."""
    uri = f"file:///{uuid4()}.md"
    edited = MARKDOWN + "\nedited\n"
    first = await bp.ingest_document(session, project="default", uri=uri, content=MARKDOWN)
    await session.flush()
    assert await _blocks(session, first.document_id)

    with pytest.raises(DocumentParseError):
        await _file_document_without_savepoint(
            session, project="default", uri=uri, content=edited, parse=_explodes,
        )
    await session.flush()

    assert await _blocks(session, first.document_id) == [], (
        "the unguarded call kept its blocks, so this drill no longer "
        "demonstrates what the savepoint buys"
    )
    from app.services.document_ingest import compute_content_hash

    assert await _content_hash(session, first.document_id) == compute_content_hash(edited)

    # and the damage is permanent: the gate now agrees with the missing tree
    replay = await bp.ingest_document(session, project="default", uri=uri, content=edited)
    assert replay.outcome == UNCHANGED
    assert await _blocks(session, first.document_id) == []


@pytest.mark.asyncio
async def test_a_failed_strip_fails_the_write_rather_than_being_written_over(
    session, monkeypatch,
):
    """The strip is not best-effort. If it raises, no replacement may land —
    a swallowed strip leaves the document holding two generations of blocks."""
    uri = f"file:///{uuid4()}.md"
    first = await bp.ingest_document(session, project="default", uri=uri, content=MARKDOWN)
    await session.flush()
    original_ids = [block["id"] for block in await _blocks(session, first.document_id)]

    inserts: list[int] = []
    real_insert = documents_repo.insert_blocks

    async def _counting_insert(session_, document_id, rows):
        inserts.append(len(rows))
        return await real_insert(session_, document_id, rows)

    async def _failing_strip(session_, document_id):
        raise RuntimeError("simulated: the strip could not run")

    monkeypatch.setattr(documents_repo, "strip_blocks", _failing_strip)
    monkeypatch.setattr(documents_repo, "insert_blocks", _counting_insert)
    with pytest.raises(RuntimeError, match="the strip could not run"):
        await bp.ingest_document(
            session, project="default", uri=uri, content=MARKDOWN + "\nmore\n",
        )
    monkeypatch.undo()
    await session.flush()

    assert inserts == [], "blocks were written over a strip that never ran"
    assert [block["id"] for block in await _blocks(session, first.document_id)] == original_ids


@pytest.mark.asyncio
async def test_a_batch_failure_leaves_its_siblings_and_the_batch_usable(session):
    good_uri = f"file:///{uuid4()}.md"
    sources = [
        bp.DocumentSource(project="default", uri=good_uri, content=MARKDOWN, label="good"),
        bp.DocumentSource(
            project="default", uri=f"file:///{uuid4()}.pdf",
            content=b"not a pdf at all", label="broken",
        ),
        bp.DocumentSource(
            project="default", uri=f"file:///{uuid4()}.txt",
            content="A short note.\n", label="also-good",
        ),
    ]
    results = await bp.ingest_documents(session, sources)
    await session.flush()

    assert isinstance(results[0], DocumentIngest)
    assert isinstance(results[1], DocumentFileFailure)
    assert results[1].label == "broken"
    assert isinstance(results[2], DocumentIngest)
    assert await _blocks(session, results[0].document_id)
    assert await _blocks(session, results[2].document_id)


# ── source routing ──────────────────────────────────────────────────


def test_the_suffix_table_routes_every_parser_it_names():
    assert set(bp.URI_SUFFIX_SOURCE_TYPES.values()) <= set(bp.PARSERS)
    assert set(bp.PARSERS) == {SOURCE_TYPE_PDF, SOURCE_TYPE_MARKDOWN, SOURCE_TYPE_NOTE}


@pytest.mark.parametrize(
    "uri,expected",
    [
        ("file:///corpus/report.pdf", SOURCE_TYPE_PDF),
        ("file:///corpus/REPORT.PDF", SOURCE_TYPE_PDF),
        ("https://example.test/a/notes.md?v=2", SOURCE_TYPE_MARKDOWN),
        ("https://example.test/a/notes.markdown#top", SOURCE_TYPE_MARKDOWN),
        ("file:///corpus/scratch.txt", SOURCE_TYPE_NOTE),
    ],
)
def test_a_uri_suffix_routes_to_its_parser(uri, expected):
    assert bp.resolve_source_type(uri=uri) == expected


def test_an_explicit_source_type_wins_over_the_suffix():
    assert bp.resolve_source_type(
        source_type=SOURCE_TYPE_NOTE, uri="file:///a.pdf",
    ) == SOURCE_TYPE_NOTE


@pytest.mark.parametrize(
    "kwargs",
    [
        {"source_type": "docx"},
        {"uri": "file:///corpus/report.docx"},
        {"uri": "file:///corpus/README"},
        {},
    ],
)
def test_an_unroutable_source_is_refused_rather_than_guessed(kwargs):
    """A suffix this module does not know must not fall back to the note
    parser: filing a PDF's compressed bytes as prose produces a document that
    looks filed and retrieves nothing."""
    with pytest.raises(bp.UnsupportedSource):
        bp.resolve_source_type(**kwargs)


@pytest.mark.asyncio
async def test_a_batch_isolates_an_unroutable_source_in_input_order(session):
    sources = [
        bp.DocumentSource(
            project="default", uri=f"file:///{uuid4()}.md",
            content="# One\n\nBody.\n", label="one",
        ),
        bp.DocumentSource(
            project="default", uri=f"file:///{uuid4()}.docx",
            content="whatever", label="two",
        ),
        bp.DocumentSource(
            project="default", uri=f"file:///{uuid4()}.txt",
            content="Three.\n", label="three",
        ),
    ]
    results = await bp.ingest_documents(session, sources)
    await session.flush()

    kinds = ["ok" if isinstance(r, DocumentIngest) else r.label for r in results]
    assert kinds == ["ok", "two", "ok"]
    assert "docx" in results[1].error


@pytest.mark.asyncio
async def test_the_resolved_source_type_is_what_lands_on_the_row(session):
    result = await bp.ingest_document(
        session, project="default", uri=f"file:///{uuid4()}.md", content="# H\n\nB.\n",
    )
    await session.flush()
    stored = (await session.execute(
        text("SELECT source_type FROM documents WHERE id = CAST(:d AS uuid)"),
        {"d": str(result.document_id)},
    )).scalar_one()
    assert stored == SOURCE_TYPE_MARKDOWN


@pytest.mark.asyncio
async def test_a_uri_less_note_is_refiled_by_id_through_the_pipeline(session):
    first = await bp.ingest_document(
        session, project="default", source_type=SOURCE_TYPE_NOTE, content="A draft.\n",
    )
    await session.flush()
    second = await bp.ingest_document(
        session, project="default", document_id=first.document_id,
        source_type=SOURCE_TYPE_NOTE, content="A revised draft, longer now.\n",
    )
    await session.flush()

    assert second.document_id == first.document_id
    assert second.outcome == UPDATED
    assert [block["text"] for block in await _blocks(session, second.document_id)] == [
        "A revised draft, longer now."
    ]


# ── the firewall: this path never enters process_batch ──────────────


MEMORY_PIPELINE = "app.services.pipeline"

_FIREWALL_RULES = ReachabilityRules(
    forbidden_modules=frozenset({MEMORY_PIPELINE}),
    forbidden_attrs=frozenset({"process_batch", "ProcessingPipeline"}),
    forbidden_literals=frozenset({"process_batch", "ProcessingPipeline"}),
)


def _module_path(dotted: str) -> pathlib.Path | None:
    module = BACKEND / (dotted.replace(".", "/") + ".py")
    if module.exists():
        return module
    package = BACKEND / dotted.replace(".", "/") / "__init__.py"
    return package if package.exists() else None


def _app_imports(dotted: str) -> set[str]:
    """Every `app.*` module named by `dotted`'s own absolute imports.

    `from app.services import x` is ambiguous about whether `x` is a submodule
    or a symbol, so the candidate is kept only when a file for it exists —
    which is also what keeps `from app.taxonomy import BLOCK_TYPES` from
    inventing a module.
    """
    path = _module_path(dotted)
    if path is None:
        return set()
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names if a.name.split(".")[0] == "app")
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module or node.module.split(".")[0] != "app":
                continue
            found.add(node.module)
            found.update(
                f"{node.module}.{a.name}"
                for a in node.names
                if _module_path(f"{node.module}.{a.name}")
            )
    return found


def _import_closure(*seeds: str) -> set[str]:
    """Every `app.*` module transitively reachable from `seeds` by import.

    One hop is not enough for this firewall: the claim is that filing a
    document cannot reach `process_batch`, and a helper two hops down that
    imported the memory pipeline would defeat a direct-import check while
    making the reach entirely real.
    """
    seen: set[str] = set()
    pending = list(seeds)
    while pending:
        module = pending.pop()
        if module in seen:
            continue
        seen.add(module)
        pending.extend(_app_imports(module) - seen)
    return seen


BLOCK_PIPELINE_CLOSURE = _import_closure("app.services.block_pipeline")


def test_the_block_pipelines_import_closure_excludes_the_memory_pipeline():
    assert "app.services.block_pipeline" in BLOCK_PIPELINE_CLOSURE
    assert MEMORY_PIPELINE not in BLOCK_PIPELINE_CLOSURE, (
        "the block pipeline can now reach the five-phase memory pipeline by "
        "import; doc 16 §3 forbids running it over document content"
    )


def test_no_file_the_block_pipeline_reaches_names_process_batch():
    paths = [p for p in (_module_path(m) for m in sorted(BLOCK_PIPELINE_CLOSURE)) if p]
    assert len(paths) >= 5, (
        f"the closure resolved to only {len(paths)} files — the scan below "
        "would pass vacuously"
    )
    offenders = find_forbidden_reach(paths, BACKEND, _FIREWALL_RULES)
    assert not offenders, "\n".join(offenders)


def test_the_firewall_scan_reports_a_module_that_does_reach_the_pipeline():
    """The negative control. Without it, a scan whose rules stopped matching —
    a renamed entry point, a widened exemption — passes silently and the
    firewall becomes a comment."""
    closure = _import_closure("app.services.memory")
    assert MEMORY_PIPELINE in closure
    paths = [p for p in (_module_path(m) for m in sorted(closure)) if p]
    assert find_forbidden_reach(paths, BACKEND, _FIREWALL_RULES)


def test_the_memory_pipeline_does_not_reach_the_block_pipeline():
    """The firewall's other direction (doc 16's opening section): the core may
    not acquire a dependency on the horizon lane either."""
    offenders = find_forbidden_reach(
        [BACKEND / "app" / "services" / "pipeline.py"],
        BACKEND,
        ReachabilityRules(
            forbidden_modules=frozenset({
                "app.services.block_pipeline",
                "app.services.document_ingest",
                "app.services.document_parsers",
            }),
            forbidden_attrs=frozenset({"ingest_document", "file_document"}),
        ),
    )
    assert not offenders, "\n".join(offenders)


# ── the opt-out is reachable only from the writer itself ────────────


UNGUARDED_ENTRY = "_file_document_without_savepoint"
WRITER_FILE = "app/services/document_ingest.py"

_OPT_OUT_RULES = ReachabilityRules(
    forbidden_modules=frozenset({f"app.services.document_ingest.{UNGUARDED_ENTRY}"}),
    forbidden_attrs=frozenset({UNGUARDED_ENTRY}),
    forbidden_literals=frozenset({UNGUARDED_ENTRY}),
)


def _writer_body_nodes(rel: str, tree: ast.Module) -> set[int]:
    """Every node inside `file_document`'s own body, in the writer's file.

    The one sanctioned reach: `file_document` is what wraps the unguarded body
    in the SAVEPOINT, so it necessarily names it. Scoped to that function's
    body by node identity, so the same call anywhere else in the same file —
    a second helper, a module-level alias — is still an offence.
    """
    if rel != WRITER_FILE:
        return set()
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "file_document":
            return {id(inner) for stmt in node.body for inner in ast.walk(stmt)}
    raise AssertionError(f"{WRITER_FILE} no longer defines `file_document`")


def _opt_out_offenders(paths: list[pathlib.Path], root: pathlib.Path) -> list[str]:
    """Every AST-visible route from `paths` to the unguarded entry point.

    `find_forbidden_reach` carries the import, attribute, literal and
    loader-call routes. The bare-`Name` route is added here because a name
    pulled in by `from ... import *` reaches the function without any
    statement spelling its module — a bound that scanner documents, and one
    this guard cannot afford, since the whole claim is that no production
    caller can take the opt-out.
    """
    offenders = find_forbidden_reach(
        paths, root, _OPT_OUT_RULES, exempt_node_ids=_writer_body_nodes,
    )
    for path in paths:
        rel = str(path.relative_to(root))
        tree = ast.parse(path.read_text(), filename=rel)
        exempt = _writer_body_nodes(rel, tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Name)
                and node.id == UNGUARDED_ENTRY
                and id(node) not in exempt
            ):
                offenders.append(f"{rel}:{node.lineno}: name route: {node.id}")
    return sorted(offenders)


def _backend_sources() -> list[pathlib.Path]:
    """Every `.py` in the backend tree, tests included, artifacts excluded."""
    artifacts = {"__pycache__", ".venv", "node_modules"}
    paths = [path for path in BACKEND.rglob("*.py") if not artifacts & set(path.parts)]
    assert len(paths) > 200, (
        f"only found {len(paths)} files — the scans below would pass "
        "vacuously; check the backend root / the globs"
    )
    return paths


def _production_sources() -> list[pathlib.Path]:
    """The same set with every `tests/` directory dropped, at any depth.

    That covers `scripts/benchlib/tests` as well as `backend/tests` — the
    exclusion is what the two scans differ on, so it has to mean the same
    thing in both.
    """
    return [path for path in _backend_sources() if "tests" not in path.parts]


def test_no_production_caller_can_reach_the_unguarded_entry_point():
    """TH1.18's opt-out is a proven property, not a naming convention. A
    caller that reached this body would file documents non-atomically again,
    and the failure it reintroduces is silent: blocks gone, hash moved, and
    the replay short-circuiting on a gate that agrees with nothing."""
    offenders = _opt_out_offenders(_production_sources(), BACKEND)
    assert not offenders, "\n".join(offenders)


@pytest.mark.parametrize(
    "route,source",
    [
        ("import", f"from app.services.document_ingest import {UNGUARDED_ENTRY}\n"),
        (
            "attribute",
            "from app.services import document_ingest\n"
            f"reach = document_ingest.{UNGUARDED_ENTRY}\n",
        ),
        (
            "literal",
            "from app.services import document_ingest\n"
            f"reach = getattr(document_ingest, {UNGUARDED_ENTRY!r})\n",
        ),
        (
            "bare name",
            "from app.services.document_ingest import *\n"
            f"reach = {UNGUARDED_ENTRY}\n",
        ),
    ],
)
def test_the_opt_out_scan_reports_a_file_that_does_reach_it(tmp_path, route, source):
    """The positive control, one case per route. Without it a scan whose
    rules stopped matching — a renamed entry point, a route the scanner never
    covered — passes silently and the containment becomes a comment."""
    probe = tmp_path / "probe.py"
    probe.write_text(source)
    assert _opt_out_offenders([probe], tmp_path), route


def test_only_the_two_standing_drills_name_the_opt_out():
    """Containment across the whole tree, not only the shipped half. The
    opt-out is worth exactly the two drills it keeps runnable; anything else
    reaching for it — a third test, a harness under `scripts/benchlib/tests`
    that the production scan skips — wanted the guarded door and took the
    unguarded one."""
    offenders = _opt_out_offenders(_backend_sources(), BACKEND)
    naming = sorted({offender.split(":")[0] for offender in offenders})
    assert naming == [
        "tests/test_block_pipeline.py",
        "tests/test_document_parsers.py",
    ], "\n".join(offenders)



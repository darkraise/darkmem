"""Lifting is on demand, and a lifted row is an ordinary memory (TH1.11).

Two properties, both negative in form, so both are pinned structurally rather
than by example.

**No ingest path triggers lifting.** A scan over `app/` proves nothing but this
module names it. The reason is not cost: lifting is a judgement about what a
document *asserts*, and an ingest that lifted silently would turn filing a PDF
into minting claims the human never asked for.

**There is no second ingestion path.** Lifted rows go through the same buffered
capture the REST and MCP doors use, so the F2 pipeline handles them without
knowing a document was involved. The test asserts the call, not a look-alike:
a module that wrote `memories` rows directly would satisfy every observable
"a memory exists" check and would have bypassed extraction, dedup and
supersession entirely.
"""
from __future__ import annotations

import ast
import json
import textwrap
from pathlib import Path

import pytest
from sqlalchemy import text

from app.services.document_ingest import BlockDraft, file_document
from app.services.proposition_lift import (
    LIFT_SOURCE,
    PROVENANCE_KEY,
    lift_document,
)

pytestmark = pytest.mark.asyncio

BACKEND = Path(__file__).resolve().parent.parent
MODULE = BACKEND / "app" / "services" / "proposition_lift.py"
PROJECT = "th111-docs"


class ScriptedLlm:
    def __init__(self, payload=None):
        self.payload = payload
        self.purposes: list[str] = []

    async def chat_completion(self, purpose, messages, **kwargs):
        self.purposes.append(purpose)
        if isinstance(self.payload, str):
            return self.payload
        return json.dumps(self.payload or {"propositions": []})


class _Ack:
    def __init__(self, id_):
        self.id = id_


class RecordingMemoryService:
    """Stands in for the real capture surface and records what it was handed."""

    def __init__(self):
        self.batches: list[list] = []

    async def batch_create_memories(self, entries, api_key_id, *, actor=None, **kwargs):
        self.batches.append(list(entries))
        return [_Ack(f"mem-{n}") for n, _ in enumerate(entries)]


async def _file(session, *texts: str) -> str:
    drafts = [BlockDraft(text=t, type="paragraph") for t in texts]
    ingest = await file_document(
        session, project=PROJECT, content="\n\n".join(texts),
        parse=lambda: drafts, title="doc", source_type="note",
    )
    await session.flush()
    return str(ingest.document_id)


# ── lifted rows are ordinary memories through the ordinary door ──────


async def test_lifting_goes_through_the_buffered_capture_path(session):
    document_id = await _file(session, "The sky is blue on clear days.")
    llm = ScriptedLlm({"propositions": [
        {"text": "The sky is blue.", "span_start": 0, "span_end": 15},
    ]})
    service = RecordingMemoryService()

    result = await lift_document(session, llm, service, document_id=document_id)

    assert result is not None and result.lifted == 1
    assert len(service.batches) == 1, "one buffered batch, not a per-entry path"
    entry = service.batches[0][0]
    assert entry.content == "The sky is blue."
    assert entry.project == PROJECT


async def test_a_lifted_entry_is_a_plain_memory_create_with_no_special_type(session):
    """"Ordinary from the pipeline's perspective" means the pipeline can see
    nothing document-shaped except metadata it never reads."""
    document_id = await _file(session, "A body sentence.")
    service = RecordingMemoryService()
    await lift_document(
        session, ScriptedLlm({"propositions": [{"text": "A claim."}]}),
        service, document_id=document_id,
    )

    entry = service.batches[0][0]
    assert entry.memory_type is None, "lifting must not invent a document memory type"
    assert entry.source == LIFT_SOURCE == "document"


# ── provenance is on the derived row, down to the block ──────────────


async def test_provenance_names_the_block_and_slices_the_source_back_out(session):
    body = "The sky is blue on clear days."
    document_id = await _file(session, body)
    service = RecordingMemoryService()
    await lift_document(
        session, ScriptedLlm({"propositions": [
            {"text": "The sky is blue.", "span_start": 0, "span_end": 15},
        ]}),
        service, document_id=document_id,
    )

    provenance = service.batches[0][0].metadata[PROVENANCE_KEY]
    assert provenance["document_id"] == document_id
    assert provenance["block_id"], "a document id alone cannot be checked back"
    start, end = provenance["char_span"]
    assert body[start:end] == "The sky is blue"


async def test_an_unusable_span_is_dropped_rather_than_clamped(session):
    """A provenance pair that does not slice the block back out is worse than
    an absent one: a reader checking the source lands on the wrong text and
    believes it."""
    document_id = await _file(session, "Short.")
    service = RecordingMemoryService()
    await lift_document(
        session, ScriptedLlm({"propositions": [
            {"text": "A claim.", "span_start": 0, "span_end": 9_000},
        ]}),
        service, document_id=document_id,
    )

    provenance = service.batches[0][0].metadata[PROVENANCE_KEY]
    assert provenance["char_span"] is None
    assert provenance["block_id"], "the block is still named even with no span"


async def test_every_block_contributes_its_own_provenance(session):
    document_id = await _file(session, "First block.", "Second block.")
    service = RecordingMemoryService()
    await lift_document(
        session, ScriptedLlm({"propositions": [{"text": "A claim."}]}),
        service, document_id=document_id,
    )

    block_ids = {
        entry.metadata[PROVENANCE_KEY]["block_id"] for entry in service.batches[0]
    }
    assert len(block_ids) == 2, "each proposition must name the block it came from"


# ── nothing to lift, and nothing invented ────────────────────────────


async def test_a_document_with_no_blocks_yields_none(session):
    ingest = await file_document(
        session, project=PROJECT, content="", parse=lambda: [],
        title="empty", source_type="note",
    )
    await session.flush()
    service = RecordingMemoryService()

    assert await lift_document(
        session, ScriptedLlm(), service, document_id=str(ingest.document_id),
    ) is None
    assert service.batches == []


async def test_unparseable_extraction_lifts_nothing_rather_than_prose(session):
    document_id = await _file(session, "A body sentence.")
    service = RecordingMemoryService()

    result = await lift_document(
        session, ScriptedLlm("not json"), service, document_id=document_id,
    )

    assert result is not None and result.lifted == 0
    assert service.batches == []


# ── on demand only: nothing under app/ can trigger it ────────────────


def _calls_named(tree: ast.AST, names: set[str]) -> bool:
    """Whether the module *calls* any of these, however it spells the call.

    Both `lift_document(...)` and `proposition_lift.lift_document(...)` count;
    importing a constant from the module does not. The distinction is the whole
    point — the rule is that nothing may **trigger** a lift, not that nothing
    may know the module exists (TH1.15 legitimately reads its provenance key).
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in names:
            return True
        if isinstance(func, ast.Attribute) and func.attr in names:
            return True
    return False


def test_no_module_under_app_triggers_a_lift():
    app_root = BACKEND / "app"
    sources = [p for p in app_root.rglob("*.py") if "__pycache__" not in str(p)]
    assert len(sources) > 100, "the scan would pass vacuously; check the glob"

    offenders = []
    for path in sources:
        if path == MODULE:
            continue
        if _calls_named(ast.parse(path.read_text(encoding="utf-8")), {"lift_document"}):
            offenders.append(str(path.relative_to(BACKEND)))
    assert not offenders, (
        f"a module under app/ can trigger a lift: {offenders} — lifting is "
        "on-demand only (doc 16 §5), and an ingest that lifted silently would "
        "turn filing a document into minting claims nobody asked for"
    )


def test_the_trigger_scan_catches_both_spellings_of_the_call():
    """The drill, because narrowing a scan is exactly when it stops working:
    a bare call and an attribute call must both be caught, and a plain import
    must not be."""
    bare = ast.parse(textwrap.dedent("""
        from app.services.proposition_lift import lift_document

        async def go(s, l, m):
            await lift_document(s, l, m, document_id="d")
    """))
    attribute = ast.parse(textwrap.dedent("""
        from app.services import proposition_lift

        async def go(s, l, m):
            await proposition_lift.lift_document(s, l, m, document_id="d")
    """))
    innocent = ast.parse(textwrap.dedent("""
        from app.services.proposition_lift import PROVENANCE_KEY

        KEY = PROVENANCE_KEY
    """))

    assert _calls_named(bare, {"lift_document"})
    assert _calls_named(attribute, {"lift_document"})
    assert not _calls_named(innocent, {"lift_document"})

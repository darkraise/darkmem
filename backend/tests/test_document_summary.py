"""A summary is a report, never a claim (TH1.14, doc 16 §6).

The three done-when clauses are all "this must NOT happen", which is the shape
that passes vacuously if tested by example. So each is pinned structurally
against the parsed source or the type, not by observing one summary that
happened not to carry a badge:

- **no badge** — the returned type has no verification field at all, so a
  renderer has nothing to render one from;
- **excluded from the fact ladder** — the module imports no fact repository and
  names no ladder symbol, walked in its AST;
- **regeneration is explicit** — no module under `app/` calls it, so no ingest
  path and no job can trigger it.

And the counterpart property, which is stronger than staleness labelling: a
stored summary never outlives the text it was made from. The ingest writer owns
`documents.properties` and replaces it, so an edited document comes back with
no summary rather than one describing text that is gone.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from sqlalchemy import text

from app.services.document_ingest import BlockDraft, file_document
from app.services.document_summary import (
    DocumentSummary,
    read_summary,
    summarise_document,
)

pytestmark = pytest.mark.asyncio

BACKEND = Path(__file__).resolve().parent.parent
MODULE = BACKEND / "app" / "services" / "document_summary.py"
PROJECT = "th114-docs"


def _without_docstrings(tree: ast.AST) -> ast.AST:
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                and isinstance(first.value.value, str):
            body.pop(0)
    return tree


class ScriptedLlm:
    def __init__(self, prose="A summary of the document."):
        self.prose = prose
        self.purposes: list[str] = []
        self.prompts: list[str] = []

    async def chat_completion(self, purpose, messages, **kwargs):
        self.purposes.append(purpose)
        self.prompts.append(messages[-1]["content"])
        return self.prose


async def _file(session, *texts: str, title="doc", uri=None) -> str:
    drafts = [BlockDraft(text=t, type="paragraph") for t in texts]
    ingest = await file_document(
        session, project=PROJECT, content="\n\n".join(texts),
        parse=lambda: drafts, title=title, source_type="note", uri=uri,
    )
    await session.flush()
    return str(ingest.document_id)


# ── it summarises, through the summarization purpose ─────────────────


async def test_a_document_is_summarised_from_its_own_blocks(session):
    document_id = await _file(session, "First para.", "Second para.")
    llm = ScriptedLlm()

    summary = await summarise_document(session, llm, document_id=document_id)

    assert summary is not None
    assert summary.text == "A summary of the document."
    assert summary.block_count == 2
    assert llm.purposes == ["summarization"], "doc 11's summarization purpose, not another"
    assert "First para." in llm.prompts[0] and "Second para." in llm.prompts[0]


async def test_a_document_with_no_blocks_yields_none_not_an_empty_summary(session):
    document_id = await _file(session, "")
    llm = ScriptedLlm()

    assert await summarise_document(session, llm, document_id=document_id) is None
    assert llm.purposes == [], "nothing to summarise means no model call"


async def test_a_stored_summary_reads_back(session):
    document_id = await _file(session, "Body text.")
    await summarise_document(session, ScriptedLlm("Stored."), document_id=document_id)

    stored = await read_summary(session, document_id=document_id)

    assert stored is not None
    assert stored.text == "Stored."


async def test_store_false_leaves_nothing_behind(session):
    document_id = await _file(session, "Body text.")

    await summarise_document(
        session, ScriptedLlm("Ephemeral."), document_id=document_id, store=False,
    )

    assert await read_summary(session, document_id=document_id) is None


# ── no badge, and it is the type that says so ────────────────────────


def test_the_summary_type_carries_no_verification_field():
    """The first done-when as a type: a renderer cannot show a badge for a
    field that does not exist, and adding one here is the visible diff that
    would have to argue for it."""
    fields = set(DocumentSummary.__dataclass_fields__)
    forbidden = {
        "verification_status", "badge", "confidence", "verified",
        "rung", "corroborated", "review_state",
    }
    assert not (fields & forbidden), f"a summary grew a verification field: {fields & forbidden}"


def test_the_module_never_touches_the_fact_ladder():
    """Excluded from the ladder, walked rather than asserted. A summary that
    reached `knowledge_triples` would be a proposition nothing corroborated
    entering the vault under a report's name."""
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(f"{node.module}.{a.name}" for a in node.names)

    forbidden = ("knowledge", "verification", "fact", "ladder", "triple")
    offenders = [name for name in imported if any(f in name.lower() for f in forbidden)]
    assert not offenders, f"the summary module reached the fact layer: {offenders}"

    # Code only: this module's own docstring names the tables it stays away
    # from, and a raw-text scan would convict it of the sentence explaining
    # why it does not do the thing.
    code = ast.unparse(_without_docstrings(tree))
    assert "knowledge_triples" not in code
    assert "fact_sources" not in code


# ── regeneration is explicit: nothing under app/ calls it ────────────


# The one module allowed to trigger a summary: the explicit operator door.
#
# Narrowed from "nothing under app/" on 2026-09-04, the same way this file's
# sibling scan was narrowed when TH1.16's read door landed. The rule this
# guard enforces is that regeneration is *explicit* -- the docstring below
# names the two hazards, and both are implicit paths: a re-ingest rewriting
# the summary, and a summary refreshing itself. An operator pressing
# Summarize is neither.
#
# Before the narrowing the scan forbade every caller under app/, which made
# doc 16 §6's committed single-document summary permanently unreachable: the
# GET door read a property that nothing in the tree could write, so the panel
# was empty by construction on every install. That is what the narrowing
# fixes, and it is deliberately an allowlist of exactly one module rather
# than a relaxed predicate -- a job, the ingest path or the pipeline calling
# this is still the failure this guard exists to catch.
SUMMARY_TRIGGER_DOOR = "app/api/routes/documents.py"


@pytest.mark.filterwarnings("ignore::pytest.PytestWarning")
def test_only_the_explicit_door_triggers_a_summary():
    """A re-ingest that silently rewrote the summary would spend a model call
    per file operation, and a summary that refreshed itself would make "the
    summary says X" a moving claim about a document nobody edited.

    Neither hazard is an operator asking for one, which is why the door is
    allowed and everything else is not."""
    app_root = BACKEND / "app"
    sources = [p for p in app_root.rglob("*.py") if "__pycache__" not in str(p)]
    assert len(sources) > 100, "the scan would pass vacuously; check the glob"

    offenders = []
    for path in sources:
        if path == MODULE:
            continue
        if path.relative_to(BACKEND).as_posix() == SUMMARY_TRIGGER_DOOR:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            named = (
                (isinstance(func, ast.Name) and func.id == "summarise_document")
                or (isinstance(func, ast.Attribute) and func.attr == "summarise_document")
            )
            if named:
                offenders.append(str(path.relative_to(BACKEND)))
                break
    assert not offenders, (
        f"a module under app/ can trigger a summary: {offenders} — regeneration "
        "is explicit by design (doc 16 §6). Only "
        f"{SUMMARY_TRIGGER_DOOR} may, because it is the operator's own request."
    )


def test_the_allowed_trigger_door_actually_triggers():
    """The allowlist must name a module that really calls it. An allowlist
    entry for a module that stopped calling `summarise_document` would sit
    there silently exempting a future implicit caller in the same file."""
    door = ast.parse((BACKEND / SUMMARY_TRIGGER_DOOR).read_text(encoding="utf-8"))
    calls = [
        node for node in ast.walk(door)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "summarise_document")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "summarise_document")
        )
    ]
    assert len(calls) == 1, (
        f"{SUMMARY_TRIGGER_DOOR} should hold exactly one trigger call, found "
        f"{len(calls)} — a second one is a second door hiding inside the "
        "exemption this allowlist grants."
    )


def test_the_ingest_and_job_paths_are_still_convicted():
    """The narrowing must not have turned the scan off. Both named hazards --
    a re-ingest and a scheduled refresh -- are still caught."""
    import textwrap

    hazard = ast.parse(textwrap.dedent("""
        from app.services.document_summary import summarise_document
        async def on_ingest(session, llm, document_id):
            await summarise_document(session, llm, document_id=document_id)
    """))
    triggers = [
        node for node in ast.walk(hazard)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "summarise_document"
    ]
    assert triggers, "the scan's own predicate stopped matching a real trigger"


def test_the_trigger_scan_separates_generating_from_reading():
    """Narrowed from a module-name match when TH1.16's read door landed: that
    door calls `read_summary` and must, while `summarise_document` is the
    trigger and must not be reachable from `app/`. A scan that cannot tell them
    apart forces the read surface to be exempted, which is how an exemption
    list ends up covering the thing it was meant to catch."""
    import textwrap

    generating = ast.parse(textwrap.dedent("""
        from app.services.document_summary import summarise_document

        async def go(s, l):
            await summarise_document(s, l, document_id="d")
    """))
    reading = ast.parse(textwrap.dedent("""
        from app.services.document_summary import read_summary

        async def go(s):
            return await read_summary(s, document_id="d")
    """))

    def _triggers(tree):
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "summarise_document":
                    return True
                if isinstance(func, ast.Attribute) and func.attr == "summarise_document":
                    return True
        return False

    assert _triggers(generating)
    assert not _triggers(reading)


# ── a summary never outlives the text it was made from ───────────────


async def test_a_reingest_clears_the_summary_rather_than_leaving_a_stale_one(session):
    """The invariant that replaced a `stale` flag: an edited document comes
    back with no summary at all, so nothing can render prose about text that no
    longer exists. Nothing regenerates it either — that stays an explicit
    call."""
    uri = "file:///th114/stale.md"
    document_id = await _file(session, "Original body.", uri=uri)
    await summarise_document(session, ScriptedLlm("First."), document_id=document_id)
    assert await read_summary(session, document_id=document_id) is not None

    await file_document(
        session, project=PROJECT, content="Rewritten body.",
        parse=lambda: [BlockDraft(text="Rewritten body.", type="paragraph")],
        title="doc", source_type="note", uri=uri,
    )
    await session.flush()

    assert await read_summary(session, document_id=document_id) is None


async def test_regenerating_after_a_reingest_summarises_the_new_text(session):
    """The counterpart: the explicit call still works, and it reads the
    document as it is now rather than what it was."""
    uri = "file:///th114/refresh.md"
    document_id = await _file(session, "Original body.", uri=uri)
    await summarise_document(session, ScriptedLlm("First."), document_id=document_id)
    await file_document(
        session, project=PROJECT, content="Rewritten body.",
        parse=lambda: [BlockDraft(text="Rewritten body.", type="paragraph")],
        title="doc", source_type="note", uri=uri,
    )
    await session.flush()

    llm = ScriptedLlm("Second.")
    await summarise_document(session, llm, document_id=document_id)

    stored = await read_summary(session, document_id=document_id)
    assert stored is not None and stored.text == "Second."
    assert "Rewritten body." in llm.prompts[0]

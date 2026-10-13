"""The register row edit service (spec 2026-10-13 §2.2-§2.4)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services import board_edit
from app.services.board_edit import edit_register_row
from app.services.board_parse import BoardRefusal
from app.services.document_door import put_document
from app.services.document_ingest import DocumentHashConflict
from tests.test_block_pipeline import FILING_CLOSURE
from tests.test_block_retrieval import BLOCK_CHANNEL_MODULES
from tests.test_worklog_wall import WORKLOG_MODULES

URI = "superpowers/registers/r.md"
REGISTER = """# Register — edit

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | first | - | - | open | - |
"""


async def _file(session, uri=URI, content=REGISTER):
    return await put_document(
        session, None, project="p", uri=uri, content=content, embed_inline=False,
    )


async def _edit(session, filed, number=1, expected_hash=None, **changes):
    return await edit_register_row(
        session, document_id=filed.document_id, number=number,
        expected_hash=expected_hash or filed.content_hash, changes=changes, actor="admin",
    )


async def test_an_edit_answers_the_row_and_writes_one_revision(session):
    filed = await _file(session)
    result = await _edit(session, filed, state="verify", note="check the board")
    assert result["row"]["state"] == "verify"
    assert result["row"]["note"] == "check the board"
    assert result["content_hash"] != filed.content_hash
    actors = (await session.execute(
        text("SELECT actor FROM document_revisions WHERE document_id = CAST(:d AS uuid) "
             "ORDER BY created_at, id"),
        {"d": filed.document_id},
    )).scalars().all()
    assert actors == [None, "admin"]


async def test_the_same_value_files_nothing_new(session):
    filed = await _file(session)
    result = await _edit(session, filed, state="open")
    assert result["content_hash"] == filed.content_hash


@pytest.mark.parametrize("changes, reason, status", [
    ({}, "no_change", 422),
    ({"state": "parked"}, "unknown_state", 422),
    ({"state": "n/a"}, "note_required", 422),
])
async def test_refusals_carry_reason_and_status(session, changes, reason, status):
    filed = await _file(session)
    with pytest.raises(BoardRefusal) as refused:
        await _edit(session, filed, **changes)
    assert (refused.value.reason, refused.value.status_code) == (reason, status)


async def test_an_unknown_column_is_a_caller_error_before_any_read(session, monkeypatch):
    filed = await _file(session)

    async def no_read(*_args, **_kwargs):
        raise AssertionError("the document was read")

    monkeypatch.setattr(session, "execute", no_read)
    with pytest.raises(TypeError, match="acceptance"):
        await _edit(session, filed, acceptance="new")


async def test_a_missing_row_is_not_found(session):
    filed = await _file(session)
    with pytest.raises(BoardRefusal) as refused:
        await _edit(session, filed, number=7, state="done")
    assert (refused.value.reason, refused.value.status_code) == ("not_found", 404)


async def test_a_document_outside_registers_is_not_found(session):
    filed = await _file(session, uri="superpowers/plans/r.md")
    with pytest.raises(BoardRefusal) as refused:
        await _edit(session, filed, state="done")
    assert refused.value.reason == "not_found"


async def test_a_stale_hash_names_the_current_one(session):
    filed = await _file(session)
    with pytest.raises(BoardRefusal) as refused:
        await _edit(session, filed, expected_hash="stale", state="done")
    assert refused.value.reason == "hash_conflict"
    assert refused.value.fields == {"current_hash": filed.content_hash}


async def test_a_race_lost_inside_the_put_is_a_hash_conflict(session, monkeypatch):
    filed = await _file(session)

    async def lost(*_args, **_kwargs):
        raise DocumentHashConflict(
            document_id=filed.document_id, expected_hash=filed.content_hash, current_hash="winner",
        )

    monkeypatch.setattr(board_edit, "put_document", lost)
    with pytest.raises(BoardRefusal) as refused:
        await _edit(session, filed, state="done")
    assert refused.value.reason == "hash_conflict"
    assert refused.value.fields == {"current_hash": "winner"}


async def test_the_put_carries_no_properties_and_no_inline_embed(session, monkeypatch):
    filed = await _file(session)
    seen = {}
    real = board_edit.put_document

    async def spy(session_, llm, **kwargs):
        seen.update(kwargs, llm=llm)
        return await real(session_, llm, **kwargs)

    monkeypatch.setattr(board_edit, "put_document", spy)
    await _edit(session, filed, state="done")
    assert seen["llm"] is None
    assert seen["embed_inline"] is False
    assert "properties" not in seen
    assert seen["expected_hash"] == filed.content_hash
    assert seen["actor"] == "admin"


def test_the_edit_service_sits_on_the_filing_path_and_outside_the_work_log_wall():
    assert "app.services.board_edit" in FILING_CLOSURE
    assert "app.services.board_edit" in BLOCK_CHANNEL_MODULES
    assert "app.services.board_edit" not in WORKLOG_MODULES


def test_the_scan_would_see_the_edit_service_reach_the_pipeline(tmp_path):
    """Negative control: a planted board_edit that imports the pipeline is caught."""
    from tests._reachability_scan import import_closure

    services = tmp_path / "app" / "services"
    services.mkdir(parents=True)
    (tmp_path / "app" / "__init__.py").write_text("")
    (services / "__init__.py").write_text("")
    (services / "board_edit.py").write_text("from app.services import pipeline\n")
    (services / "pipeline.py").write_text("")
    assert "app.services.pipeline" in import_closure(tmp_path, "app.services.board_edit")

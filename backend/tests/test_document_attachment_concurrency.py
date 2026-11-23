from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.auth import create_access_token
from app.config import settings
from app.database import get_session
from app.main import app
from app.services import block_embeddings, block_verbs, page_attachment_cleanup, page_import
from app.services.block_embedding_refresh import refresh_block_embeddings
from app.services.embedder_registry import ensure_registered
from app.services.block_verbs import DOCUMENT_OWNER, PAGE_OWNER, NewBlock
from app.services.document_ingest import BlockDraft, file_document
from app.services.page_attachments import attachment_path, attachment_url, place_upload, stage_upload
from app.services.page_door import create_page
from app.services.page_import import import_notion_export
from tests.conftest import test_engine
from tests.fixtures.notion.builder import Entry, FLAT_EXPORT, PNG, build_fixture


FINGERPRINT = "review-block-freshness|3"


class ControlledEmbedder:
    def __init__(self, entered=None, release=None):
        self.entered = entered
        self.release = release

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        if self.entered is not None:
            self.entered.set()
            await self.release.wait()
        return [[1.0 if body == "old" else 2.0] * 3 for body in texts], FINGERPRINT

    async def embed(self, body):
        return [0.0] * 3, FINGERPRINT


@pytest_asyncio.fixture
async def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", str(tmp_path))
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    project = f"race-{uuid4()}"
    try:
        yield factory, project
    finally:
        async with factory() as cleanup:
            await cleanup.execute(text("DELETE FROM pages WHERE project = :project"), {"project": project})
            await cleanup.execute(text("DELETE FROM documents WHERE project = :project"), {"project": project})
            await cleanup.execute(text("DELETE FROM page_attachments WHERE project = :project"), {"project": project})
            await cleanup.commit()


async def _seed_owner(factory, project, owner):
    async with factory() as session:
        if owner == PAGE_OWNER:
            result = await create_page(session, None, project=project, title="race", content="old")
            owner_id = str(result.id)
        else:
            result = await file_document(
                session, project=project, content="old",
                parse=lambda: [BlockDraft(text="old", type="paragraph")],
                title="race", source_type="note",
            )
            owner_id = str(result.document_id)
        block_id = str((await session.execute(text(
            f"SELECT id FROM blocks WHERE {owner.kind}_id = CAST(:owner AS uuid)"
        ), {"owner": owner_id})).scalar_one())
        await ensure_registered(session, FINGERPRINT)
        await session.commit()
    return owner_id, block_id


async def _vector(session, block_id, owner):
    table = block_embeddings.child_table(owner.embed_parent, FINGERPRINT)
    result = (await session.execute(text(
        f"SELECT embedding::text FROM {table} WHERE block_id = CAST(:block AS uuid)"
    ), {"block": block_id})).scalar_one_or_none()
    return None if result is None else [float(value) for value in result.strip("[]").split(",")]


async def _blocked_or_finished(observer, backend_pid, task):
    async with asyncio.timeout(5):
        while not task.done():
            blocked = (await observer.execute(text(
                "SELECT cardinality(pg_blocking_pids(:pid)) > 0"
            ), {"pid": backend_pid})).scalar_one()
            if blocked:
                return True
            await asyncio.sleep(0.01)
    return False


@pytest.mark.parametrize("owner", [DOCUMENT_OWNER, PAGE_OWNER], ids=["document", "page"])
async def test_provider_completion_cannot_overwrite_newer_text(isolated, owner):
    factory, project = isolated
    _, block_id = await _seed_owner(factory, project, owner)
    entered, release = asyncio.Event(), asyncio.Event()
    async with factory() as older, factory() as newer:
        old_task = asyncio.create_task(block_embeddings.embed_blocks(
            older, ControlledEmbedder(entered, release), block_ids=[block_id], parent=owner.embed_parent,
        ))
        try:
            await asyncio.wait_for(entered.wait(), 5)
            await block_verbs.update_block(
                newer, ControlledEmbedder(), block_id=block_id, text="new", owner=owner,
            )
            if owner == PAGE_OWNER:
                await block_embeddings.embed_blocks(newer, ControlledEmbedder(), block_ids=[block_id], parent=owner.embed_parent)
                await newer.commit()
        finally:
            release.set()
        result = await asyncio.wait_for(old_task, 5)
        await older.commit()
        assert await _vector(newer, block_id, owner) == [2.0, 2.0, 2.0]
        assert result.written == 0


@pytest.mark.parametrize("owner", [DOCUMENT_OWNER, PAGE_OWNER], ids=["document", "page"])
async def test_freshness_lock_covers_vector_write_and_commit(isolated, monkeypatch, owner):
    factory, project = isolated
    _, block_id = await _seed_owner(factory, project, owner)
    entered, release = asyncio.Event(), asyncio.Event()
    async with factory() as embedding, factory() as editing, factory() as observer:
        edit_pid = (await editing.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        original = embedding.execute

        async def pause_insert(statement, *args, **kwargs):
            if str(statement).lstrip().startswith("INSERT INTO " + owner.embed_parent):
                entered.set()
                await release.wait()
            return await original(statement, *args, **kwargs)

        monkeypatch.setattr(embedding, "execute", pause_insert)

        async def embed_and_commit():
            await block_embeddings.embed_blocks(embedding, ControlledEmbedder(), block_ids=[block_id], parent=owner.embed_parent)
            await embedding.commit()

        embedding_task = asyncio.create_task(embed_and_commit())
        await asyncio.wait_for(entered.wait(), 5)
        editing_task = asyncio.create_task(block_verbs.update_block(
            editing, ControlledEmbedder(), block_id=block_id, text="new", owner=owner,
        ))
        try:
            was_blocked = await _blocked_or_finished(observer, edit_pid, editing_task)
        finally:
            release.set()
        await asyncio.wait_for(asyncio.gather(embedding_task, editing_task), 5)
        assert await _vector(observer, block_id, owner) == (None if owner == PAGE_OWNER else [2.0, 2.0, 2.0])
        assert was_blocked


@pytest.mark.parametrize("owner", [DOCUMENT_OWNER, PAGE_OWNER], ids=["document", "page"])
async def test_embedding_waits_for_mutation_commit_then_revalidates(isolated, monkeypatch, owner):
    factory, project = isolated
    _, block_id = await _seed_owner(factory, project, owner)
    provider_entered, provider_release = asyncio.Event(), asyncio.Event()
    commit_entered, commit_release = asyncio.Event(), asyncio.Event()
    async with factory() as embedding, factory() as editing, factory() as observer:
        embed_pid = (await embedding.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        original_commit = editing.commit

        async def pause_commit():
            commit_entered.set()
            await commit_release.wait()
            await original_commit()

        monkeypatch.setattr(editing, "commit", pause_commit)
        embedding_task = asyncio.create_task(block_embeddings.embed_blocks(
            embedding, ControlledEmbedder(provider_entered, provider_release), block_ids=[block_id], parent=owner.embed_parent,
        ))
        await asyncio.wait_for(provider_entered.wait(), 5)
        editing_task = asyncio.create_task(block_verbs.update_block(
            editing, ControlledEmbedder(), block_id=block_id, text="new", owner=owner,
        ))
        await asyncio.wait_for(commit_entered.wait(), 5)
        provider_release.set()
        try:
            was_blocked = await _blocked_or_finished(observer, embed_pid, embedding_task)
        finally:
            commit_release.set()
        result = await asyncio.wait_for(embedding_task, 5)
        await embedding.commit()
        await asyncio.wait_for(editing_task, 5)
        assert result.written == 0
        assert await _vector(observer, block_id, owner) == (None if owner == PAGE_OWNER else [2.0, 2.0, 2.0])
        assert was_blocked


@pytest.mark.parametrize("operation", ["upload", "import"])
@pytest.mark.parametrize("error_type", [asyncio.CancelledError, ConnectionError])
@pytest.mark.parametrize("durable", [False, True], ids=["unknown", "durable"])
async def test_uncertain_commit_preserves_placed_bytes(isolated, tmp_path, monkeypatch, operation, error_type, durable):
    factory, project = isolated
    page_id, _ = await _seed_owner(factory, project, PAGE_OWNER)
    archive = build_fixture(FLAT_EXPORT, tmp_path / "export.zip")

    async def body():
        yield archive.read_bytes() if operation == "import" else b"upload bytes"

    async with factory() as session:
        original_commit = session.commit

        async def uncertain_commit():
            if durable:
                await original_commit()
            raise error_type("commit acknowledgement lost")

        monkeypatch.setattr(session, "commit", uncertain_commit)
        with pytest.raises(error_type):
            if operation == "import":
                await import_notion_export(session, project=project, body=body(), declared_length=None, actor=None)
            else:
                staged = await stage_upload(body(), max_bytes=1024)
                await place_upload(session, staged, page_id=page_id, project=project, filename="asset")
    async with factory() as checking:
        attachment_ids = (await checking.execute(text(
            "SELECT id FROM page_attachments WHERE project = :project"
        ), {"project": project})).scalars().all()
        final_files = [path for path in tmp_path.glob("*/*") if path.is_file() and path.parent.name != ".staging"]
        assert len(final_files) == 1
        assert len(attachment_ids) == int(durable)
        for attachment_id in attachment_ids:
            assert attachment_path(attachment_id).is_file()


async def _seed_attachment(factory, project):
    page_id, block_id = await _seed_owner(factory, project, PAGE_OWNER)
    attachment_id = uuid4()
    path = attachment_path(attachment_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"durable bytes")
    async with factory() as session:
        await session.execute(text(
            "INSERT INTO page_attachments (id, project, filename, content_type, size_bytes, sha256, created_at) "
            "VALUES (:id, :project, 'test', 'application/octet-stream', 13, 'test', now() - interval '200 hours')"
        ), {"id": attachment_id, "project": project})
        await session.commit()
    return page_id, block_id, attachment_id


async def _save_reference(session, project, page_id, block_id, attachment_id, writer):
    body = f"![asset]({attachment_url(attachment_id)})"
    if writer == "import":
        archive = build_fixture([
            Entry("Reference 00000000000000000000000000000001.md", (
                f"# Reference\n\n![asset](https://example.test{attachment_url(attachment_id)})\n"
            ).encode()),
        ], attachment_path(attachment_id).parent.parent / "reference.zip")

        async def chunks():
            yield archive.read_bytes()

        return await import_notion_export(session, project=project, body=chunks(), declared_length=None, actor=None)
    if writer == "create":
        return await create_page(session, None, project=project, title="reference", content=body, parent_id=page_id)
    if writer == "insert":
        return await block_verbs.insert_block(session, None, document_id=page_id, text=body, type="paragraph", owner=PAGE_OWNER)
    if writer == "batch":
        return await block_verbs.insert_blocks(session, None, document_id=page_id, blocks=[NewBlock(str(uuid4()), "paragraph", body)], owner=PAGE_OWNER)
    return await block_verbs.update_block(session, None, block_id=block_id, text=body, owner=PAGE_OWNER)


@pytest.mark.parametrize("writer", ["create", "insert", "batch", "update", "import"])
@pytest.mark.parametrize("first", ["writer", "cleanup"])
async def test_reference_write_and_collection_serialize_through_commit(isolated, monkeypatch, writer, first):
    factory, project = isolated
    page_id, block_id, attachment_id = await _seed_attachment(factory, project)
    entered, release = asyncio.Event(), asyncio.Event()
    async with factory() as writing, factory() as collecting, factory() as observer:
        write_pid = (await writing.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        cleanup_pid = (await collecting.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        first_session = writing if first == "writer" else collecting
        original_commit = first_session.commit

        async def pause_commit():
            entered.set()
            await release.wait()
            await original_commit()

        monkeypatch.setattr(first_session, "commit", pause_commit)

        @asynccontextmanager
        async def cleanup_factory():
            yield collecting

        async def write():
            try:
                return await _save_reference(writing, project, page_id, block_id, attachment_id, writer)
            except BaseException:
                await writing.rollback()
                raise

        async def cleanup():
            return await page_attachment_cleanup.run_cleanup(cleanup_factory, grace_hours=168, staging_max_age_hours=6)

        first_task = asyncio.create_task(write() if first == "writer" else cleanup())
        await asyncio.wait_for(entered.wait(), 5)
        second_task = asyncio.create_task(cleanup() if first == "writer" else write())
        try:
            was_blocked = await _blocked_or_finished(observer, cleanup_pid if first == "writer" else write_pid, second_task)
        finally:
            release.set()
        results = await asyncio.wait_for(asyncio.gather(first_task, second_task, return_exceptions=True), 5)
        if first == "writer":
            assert not any(isinstance(result, BaseException) for result in results), results
            assert attachment_path(attachment_id).is_file()
            assert results[1].rows_deleted == 0
        else:
            assert isinstance(results[1], ValueError), results
            await writing.rollback()
            assert not attachment_path(attachment_id).exists()
            assert results[0].rows_deleted == 1
            saved = (await observer.execute(text(
                "SELECT count(*) FROM blocks WHERE text LIKE :url"
            ), {"url": f"%{attachment_id}%"})).scalar_one()
            assert saved == 0
        assert was_blocked


async def test_refresh_skips_stale_page_vector_and_reports_remaining_work(isolated):
    factory, project = isolated
    _, block_id = await _seed_owner(factory, project, PAGE_OWNER)
    entered, release = asyncio.Event(), asyncio.Event()
    async with factory() as sweeping, factory() as editing:
        sweep = asyncio.create_task(refresh_block_embeddings(
            sweeping, ControlledEmbedder(entered, release), batch=0, page_batch=10, worklog_batch=0,
        ))
        try:
            await asyncio.wait_for(entered.wait(), 5)
            await block_verbs.update_block(editing, None, block_id=block_id, text="new", owner=PAGE_OWNER)
        finally:
            release.set()
        outcome = await asyncio.wait_for(sweep, 5)
        assert await _vector(editing, block_id, PAGE_OWNER) is None
        assert outcome.embedded == 0
        assert not outcome.converged
        repaired = await refresh_block_embeddings(sweeping, ControlledEmbedder(), batch=0, page_batch=10, worklog_batch=0)
        assert repaired.embedded == 1
        assert repaired.converged
        assert await _vector(editing, block_id, PAGE_OWNER) == [2.0, 2.0, 2.0]


async def test_rowless_collection_waits_for_imported_files_to_commit(isolated, tmp_path, monkeypatch):
    factory, project = isolated
    _, _, kept_id = await _seed_attachment(factory, project)
    async with factory() as seed:
        await seed.execute(text("UPDATE page_attachments SET created_at = now() WHERE id = :id"), {"id": kept_id})
        await seed.commit()
    archive = build_fixture(FLAT_EXPORT, tmp_path / "export.zip")
    entered, release = asyncio.Event(), asyncio.Event()
    original_place = page_import.place_staged

    def place_aged(staged, attachment_id):
        original_place(staged, attachment_id)
        old = time.time() - 7200
        os.utime(attachment_path(attachment_id), (old, old))

    monkeypatch.setattr(page_import, "place_staged", place_aged)

    async def body():
        yield archive.read_bytes()

    async with factory() as importing, factory() as collecting, factory() as observer:
        cleanup_pid = (await collecting.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        original_execute = importing.execute

        async def pause_row(statement, *args, **kwargs):
            if str(statement).startswith("INSERT INTO page_attachments"):
                entered.set()
                await release.wait()
            return await original_execute(statement, *args, **kwargs)

        monkeypatch.setattr(importing, "execute", pause_row)

        @asynccontextmanager
        async def cleanup_factory():
            # As closing a factory session does: the transaction-scoped lock
            # goes with the transaction, and the import locks again after it.
            try:
                yield collecting
            finally:
                await collecting.rollback()

        importing_task = asyncio.create_task(import_notion_export(importing, project=project, body=body(), declared_length=None, actor=None))
        await asyncio.wait_for(entered.wait(), 5)
        collecting_task = asyncio.create_task(page_attachment_cleanup.run_cleanup(cleanup_factory, grace_hours=168, staging_max_age_hours=6))
        try:
            was_blocked = await _blocked_or_finished(observer, cleanup_pid, collecting_task)
        finally:
            release.set()
        imported, collected = await asyncio.wait_for(asyncio.gather(importing_task, collecting_task), 5)
        assert imported.attachments_stored == 1
        assert collected.rowless_files_removed == 0
        attachment_ids = (await observer.execute(text("SELECT id FROM page_attachments WHERE project = :project"), {"project": project})).scalars().all()
        assert len(attachment_ids) == 2
        assert all(attachment_path(attachment_id).is_file() for attachment_id in attachment_ids)
        assert was_blocked


@pytest.mark.parametrize("verb", ["move", "delete"])
async def test_move_and_delete_serialize_retained_references_with_collection(isolated, monkeypatch, verb):
    factory, project = isolated
    page_id, block_id, attachment_id = await _seed_attachment(factory, project)
    async with factory() as seed:
        await _save_reference(seed, project, page_id, block_id, attachment_id, "update")
        sibling = await block_verbs.insert_block(seed, None, document_id=page_id, type="paragraph", text="sibling", owner=PAGE_OWNER)
    entered, release = asyncio.Event(), asyncio.Event()
    async with factory() as writing, factory() as collecting, factory() as observer:
        cleanup_pid = (await collecting.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        original_commit = writing.commit

        async def pause_commit():
            entered.set()
            await release.wait()
            await original_commit()

        monkeypatch.setattr(writing, "commit", pause_commit)

        @asynccontextmanager
        async def cleanup_factory():
            yield collecting

        mutation = (
            block_verbs.move_block(writing, None, block_id=block_id, after_block_id=sibling.block_id, owner=PAGE_OWNER)
            if verb == "move" else
            block_verbs.delete_block(writing, None, block_id=sibling.block_id, owner=PAGE_OWNER)
        )
        writing_task = asyncio.create_task(mutation)
        await asyncio.wait_for(entered.wait(), 5)
        collecting_task = asyncio.create_task(page_attachment_cleanup.run_cleanup(cleanup_factory, grace_hours=168, staging_max_age_hours=6))
        try:
            was_blocked = await _blocked_or_finished(observer, cleanup_pid, collecting_task)
        finally:
            release.set()
        _, collected = await asyncio.wait_for(asyncio.gather(writing_task, collecting_task), 5)
        assert collected.rows_deleted == 0
        assert attachment_path(attachment_id).is_file()
        assert was_blocked


async def test_import_waits_for_rowless_scan_and_unlink(isolated, tmp_path, monkeypatch):
    factory, project = isolated
    _, _, kept_id = await _seed_attachment(factory, project)
    async with factory() as seed:
        await seed.execute(text("UPDATE page_attachments SET created_at = now() WHERE id = :id"), {"id": kept_id})
        await seed.commit()
    orphan = attachment_path(uuid4())
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_bytes(b"orphan")
    old = time.time() - 7200
    os.utime(orphan, (old, old))
    archive = build_fixture(FLAT_EXPORT, tmp_path / "export.zip")
    entered, release = asyncio.Event(), asyncio.Event()
    original_count = page_attachment_cleanup.attachment_count

    async def pause_count(session):
        entered.set()
        await release.wait()
        return await original_count(session)

    monkeypatch.setattr(page_attachment_cleanup, "attachment_count", pause_count)

    async def body():
        yield archive.read_bytes()

    async with factory() as importing, factory() as observer:
        import_pid = (await importing.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        collecting_task = asyncio.create_task(page_attachment_cleanup.run_cleanup(factory, grace_hours=168, staging_max_age_hours=6))
        await asyncio.wait_for(entered.wait(), 5)
        importing_task = asyncio.create_task(import_notion_export(importing, project=project, body=body(), declared_length=None, actor=None))
        try:
            was_blocked = await _blocked_or_finished(observer, import_pid, importing_task)
        finally:
            release.set()
        collected, imported = await asyncio.wait_for(asyncio.gather(collecting_task, importing_task), 5)
        assert collected.rowless_files_removed == 1
        assert not orphan.exists()
        assert imported.attachments_stored == 1
        attachment_ids = (await observer.execute(text("SELECT id FROM page_attachments WHERE project = :project"), {"project": project})).scalars().all()
        assert len(attachment_ids) == 2
        assert all(attachment_path(attachment_id).is_file() for attachment_id in attachment_ids)
        assert was_blocked


TWO_FILE_EXPORT = [
    Entry(
        "Pics 00000000000000000000000000000001.md",
        b"# Pics\n\n![a](a.png)\n\n![b](b.png)\n",
    ),
    Entry("a.png", PNG),
    Entry("b.png", PNG + b"b"),
]


@asynccontextmanager
async def _route_client(factory):
    """The real app over committed sessions, so a lock the route takes is one
    other connections can see, and each request's session is kept to inspect."""
    sessions = []

    async def session_per_request():
        async with factory() as session:
            sessions.append(session)
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = session_per_request
    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, sessions, headers
    finally:
        app.dependency_overrides.pop(get_session, None)


def _paused_body(entered, release, *, fail=False):
    async def body():
        yield PNG
        entered.set()
        await release.wait()
        if fail:
            raise ConnectionError("client went away mid-upload")
        yield b"tail"
    return body()


async def _other_project_page(factory):
    other = f"other-{uuid4()}"
    async with factory() as session:
        page = await create_page(session, None, project=other, title="elsewhere", content="text")
    return other, str(page.id)


async def _cleanup_queued_or_done(factory, cleanup, seconds=5):
    """Wait until the collection's exclusive lifecycle lock is queued behind a
    holder, or the collection finished because nothing held it: either way the
    write that follows runs after the cleanup reached its lock."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds
    while not cleanup.done():
        async with factory() as probe:
            waiting = (await probe.execute(text(
                "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' "
                "AND mode = 'ExclusiveLock' AND NOT granted "
                "AND database = (SELECT oid FROM pg_database WHERE datname = current_database())"
            ))).scalar_one()
        if waiting:
            return
        assert loop.time() < deadline, "the cleanup neither queued on its lock nor finished"
        await asyncio.sleep(0.02)


async def _write_within(factory, page_id, seconds=2):
    async with factory() as session:
        await asyncio.wait_for(block_verbs.insert_block(
            session, None, document_id=page_id, type="paragraph", text="written", owner=PAGE_OWNER,
        ), seconds)


async def _drop_project(factory, project):
    async with factory() as session:
        await session.execute(text("DELETE FROM pages WHERE project = :project"), {"project": project})
        await session.commit()


def _final_files(root):
    return [p for p in root.glob("*/*") if p.is_file() and p.parent.name != ".staging"]


async def test_upload_in_progress_does_not_block_a_page_write(isolated):
    factory, project = isolated
    page_id, _ = await _seed_owner(factory, project, PAGE_OWNER)
    other, other_page = await _other_project_page(factory)
    entered, release = asyncio.Event(), asyncio.Event()
    try:
        async with _route_client(factory) as (client, _, headers):
            upload = asyncio.create_task(client.post(
                f"/api/v1/pages/{page_id}/attachments",
                content=_paused_body(entered, release), headers=headers,
            ))
            try:
                await asyncio.wait_for(entered.wait(), 5)
                cleanup = asyncio.create_task(page_attachment_cleanup.run_cleanup(
                    factory, grace_hours=168, staging_max_age_hours=6,
                ))
                await _cleanup_queued_or_done(factory, cleanup)
                await _write_within(factory, other_page)
            finally:
                release.set()
            response = await asyncio.wait_for(upload, 5)
            await asyncio.wait_for(cleanup, 5)
        assert response.status_code == 201, response.text
        assert attachment_path(response.json()["id"]).is_file()
    finally:
        await _drop_project(factory, other)


async def test_upload_holds_no_transaction_while_streaming(isolated):
    factory, project = isolated
    page_id, _ = await _seed_owner(factory, project, PAGE_OWNER)
    entered, release = asyncio.Event(), asyncio.Event()
    async with _route_client(factory) as (client, sessions, headers):
        upload = asyncio.create_task(client.post(
            f"/api/v1/pages/{page_id}/attachments",
            content=_paused_body(entered, release), headers=headers,
        ))
        try:
            await asyncio.wait_for(entered.wait(), 5)
            streaming = sessions[-1].in_transaction()
        finally:
            release.set()
        response = await asyncio.wait_for(upload, 5)
    assert response.status_code == 201, response.text
    assert streaming is False


async def test_interrupted_upload_leaves_no_row_and_no_file(isolated, tmp_path):
    factory, project = isolated
    page_id, _ = await _seed_owner(factory, project, PAGE_OWNER)
    entered, release = asyncio.Event(), asyncio.Event()
    release.set()
    async with _route_client(factory) as (client, _, headers):
        with pytest.raises(ConnectionError):
            await client.post(
                f"/api/v1/pages/{page_id}/attachments",
                content=_paused_body(entered, release, fail=True), headers=headers,
            )
    async with factory() as checking:
        rows = (await checking.execute(text(
            "SELECT count(*) FROM page_attachments WHERE project = :project"
        ), {"project": project})).scalar_one()
    assert rows == 0
    assert [p for p in tmp_path.rglob("*") if p.is_file()] == []


async def test_collected_reference_is_still_refused(isolated, tmp_path):
    factory, project = isolated
    _, _, attachment_id = await _seed_attachment(factory, project)
    archive = build_fixture([
        Entry("Reference 00000000000000000000000000000001.md", (
            f"# Reference\n\n![asset](https://example.test{attachment_url(attachment_id)})\n"
        ).encode()),
    ], tmp_path / "reference.zip")
    entered, release = asyncio.Event(), asyncio.Event()

    async def body():
        data = archive.read_bytes()
        yield data[:10]
        entered.set()
        await release.wait()
        yield data[10:]

    async with factory() as importing:
        importing_task = asyncio.create_task(import_notion_export(
            importing, project=project, body=body(), declared_length=None, actor=None,
        ))
        try:
            await asyncio.wait_for(entered.wait(), 5)
            collected = await asyncio.wait_for(page_attachment_cleanup.run_cleanup(
                factory, grace_hours=168, staging_max_age_hours=6,
            ), 5)
        finally:
            release.set()
        with pytest.raises(ValueError):
            await asyncio.wait_for(importing_task, 5)
    assert collected.rows_deleted == 1
    async with factory() as checking:
        saved = (await checking.execute(text(
            "SELECT count(*) FROM blocks WHERE text LIKE :url"
        ), {"url": f"%{attachment_id}%"})).scalar_one()
    assert saved == 0


async def test_notion_import_takes_the_lock_per_file(isolated, tmp_path, monkeypatch):
    factory, project = isolated
    other, other_page = await _other_project_page(factory)
    archive = build_fixture(TWO_FILE_EXPORT, tmp_path / "two.zip")
    entered, release = asyncio.Event(), asyncio.Event()
    calls = 0
    original_lock = page_import.lock_attachments

    async def lock_second_file_late(session, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            entered.set()
            await release.wait()
        return await original_lock(session, **kwargs)

    monkeypatch.setattr(page_import, "lock_attachments", lock_second_file_late)

    async def body():
        yield archive.read_bytes()

    try:
        async with factory() as importing:
            importing_task = asyncio.create_task(import_notion_export(
                importing, project=project, body=body(), declared_length=None, actor=None,
            ))
            try:
                await asyncio.wait_for(entered.wait(), 5)
                cleanup = asyncio.create_task(page_attachment_cleanup.run_cleanup(
                    factory, grace_hours=168, staging_max_age_hours=6,
                ))
                await _cleanup_queued_or_done(factory, cleanup)
                await _write_within(factory, other_page)
            finally:
                release.set()
            report = await asyncio.wait_for(importing_task, 5)
            await asyncio.wait_for(cleanup, 5)
        assert report.attachments_stored == 2
    finally:
        await _drop_project(factory, other)


async def test_failed_import_withdraws_its_committed_attachments(isolated, tmp_path, monkeypatch):
    factory, project = isolated
    archive = build_fixture(TWO_FILE_EXPORT, tmp_path / "two.zip")

    async def boom(*args, **kwargs):
        raise RuntimeError("page write failed")

    monkeypatch.setattr(page_import, "_insert_page", boom)

    async def body():
        yield archive.read_bytes()

    async with factory() as importing:
        with pytest.raises(RuntimeError):
            await import_notion_export(importing, project=project, body=body(), declared_length=None, actor=None)
    async with factory() as checking:
        rows = (await checking.execute(text(
            "SELECT count(*) FROM page_attachments WHERE project = :project"
        ), {"project": project})).scalar_one()
    assert rows == 0
    assert _final_files(tmp_path) == []

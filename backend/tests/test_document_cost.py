"""What a document or page read or write costs: rows rewritten, content
fetched, where the parse runs, and how often the expensive probes run."""
from __future__ import annotations

import json
import threading
import uuid
from contextlib import contextmanager

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from app.services.document_door import (
    MAX_BLOCKS, DocumentTooLarge, document_blocks, put_document,
)
from app.services.embedder_registry import EmbedderInfo, child_table, embedder_registry

FINGERPRINT = "doccost-probe|3"


class StubEmbedder:
    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([[1.0, 0.0, 0.0] for _ in texts], FINGERPRINT)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0], FINGERPRINT


@pytest.fixture(autouse=True)
def _forget_probe_fingerprints():
    for fingerprint in (FINGERPRINT, MEMO_FP, ROTATED_FP):
        embedder_registry.forget(fingerprint)
    yield
    for fingerprint in (FINGERPRINT, MEMO_FP, ROTATED_FP):
        embedder_registry.forget(fingerprint)


@contextmanager
def statements():
    seen: list[str] = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        seen.append(statement)

    event.listen(Engine, "before_cursor_execute", capture)
    try:
        yield seen
    finally:
        event.remove(Engine, "before_cursor_execute", capture)


# Real commits: inside the shared test transaction two writes can carry one
# transaction id, and `xmin` could not tell a rewritten row from an untouched one.
PAGE_PROJECT = "doccost-pages"


@pytest_asyncio.fixture
async def committed(setup_database):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    yield factory
    async with factory() as cleanup:
        await cleanup.execute(text("DELETE FROM pages WHERE project = :p"), {"p": PAGE_PROJECT})
        await cleanup.commit()


async def test_block_verb_rewrites_only_changed_rows(committed):
    from app.services.block_verbs import PAGE_OWNER, update_block
    from app.services.page_door import create_page

    content = "\n\n".join(f"para {n:02d}" for n in range(50)) + "\n"
    async with committed() as session:
        page = await create_page(
            session, StubEmbedder(), project=PAGE_PROJECT, title="cost", content=content,
        )
    async with committed() as session:
        before = dict((await session.execute(
            text(
                "SELECT CAST(id AS text), CAST(xmin AS text) FROM blocks "
                "WHERE page_id = CAST(:p AS uuid) ORDER BY order_index"
            ),
            {"p": str(page.id)},
        )).all())
        assert len(before) == 50
        first = next(iter(before))
        await session.rollback()
        await update_block(
            session, StubEmbedder(), block_id=first, text="PARA 00", owner=PAGE_OWNER,
        )
    async with committed() as session:
        after = dict((await session.execute(
            text(
                "SELECT CAST(id AS text), CAST(xmin AS text) FROM blocks "
                "WHERE page_id = CAST(:p AS uuid)"
            ),
            {"p": str(page.id)},
        )).all())
    untouched = [block for block, xmin in before.items() if block != first and after[block] == xmin]
    assert len(untouched) >= 45


async def test_block_read_fetches_content_once(session):
    from app.services.page_door import create_page, get_page

    content = "\n\n".join(f"Paragraph {n} — café 🌱 text." for n in range(200)) + "\n"
    filed = await put_document(
        session, StubEmbedder(), project="doccost", uri="many.md", content=content,
    )
    page = await create_page(
        session, StubEmbedder(), project="doccost", title="p", content=content,
    )
    with statements() as seen:
        blocks = await document_blocks(session, document_id=filed.document_id)
        view = await get_page(session, str(page.id))
    assert not [s for s in seen if "substring(" in s.lower()]

    assert len(blocks) == 200
    for block in blocks:
        start, end = block.char_span
        assert block.source == content[start:end]
    page_content = (await session.execute(
        text("SELECT content FROM pages WHERE id = CAST(:p AS uuid)"), {"p": str(page.id)},
    )).scalar_one()
    assert len(view.blocks) == 200
    for block in view.blocks:
        assert block["source"] == page_content[block["char_start"]:block["char_end"]]


async def test_parse_runs_off_the_event_loop(session, monkeypatch):
    from app.services import block_pipeline
    from app.services.document_parsers import SOURCE_TYPE_MARKDOWN

    real = block_pipeline.PARSERS[SOURCE_TYPE_MARKDOWN]
    threads: list[int] = []

    def recording(content):
        threads.append(threading.get_ident())
        return real(content)

    monkeypatch.setitem(block_pipeline.PARSERS, SOURCE_TYPE_MARKDOWN, recording)
    await put_document(
        session, StubEmbedder(), project="doccost", uri="thread.md", content="# A\n\nB.\n",
    )
    assert threads and threads[0] != threading.get_ident()


async def test_block_cap_is_checked_before_any_insert(session):
    content = "\n\n".join(f"para {n}" for n in range(MAX_BLOCKS + 1))
    with statements() as seen:
        with pytest.raises(DocumentTooLarge):
            await put_document(
                session, StubEmbedder(), project="doccost", uri="huge.md", content=content,
            )
    assert [s for s in seen if s.lstrip().upper().startswith("INSERT INTO BLOCKS")] == []


MEMO_FP = "doccost_memo_fp"
ROTATED_FP = "doccost_rotated_fp"


async def _register(session, fingerprint):
    await embedder_registry.register(
        session, EmbedderInfo(fingerprint=fingerprint, model_id="m", dims=3, source="llm"),
    )


async def _embed_document(session, document_id, fingerprint):
    table = child_table("block_embeddings", fingerprint)
    await session.execute(
        text(
            f"INSERT INTO {table} (block_id, fingerprint, embedding, created_at) "
            f"SELECT id, :fp, CAST('[1,0,0]' AS vector), now() FROM blocks "
            f"WHERE document_id = CAST(:d AS uuid) ON CONFLICT DO NOTHING"
        ),
        {"fp": fingerprint, "d": str(document_id)},
    )


async def _file(session, uri, texts):
    from app.services.document_ingest import BlockDraft, file_document

    drafts = [BlockDraft(text=t, type="paragraph") for t in texts]
    filed = await file_document(
        session, project="doccost-conn", uri=uri, content="\n\n".join(texts),
        parse=lambda: drafts, source_type="note",
    )
    return str(filed.document_id)


async def test_connections_are_memoised_per_content(session):
    from app.services.document_connections import connections_for_document

    await _register(session, MEMO_FP)
    mine = await _file(session, "mine.md", ["alpha", "beta"])
    theirs = await _file(session, "theirs.md", ["gamma"])
    for document_id in (mine, theirs):
        await _embed_document(session, document_id, MEMO_FP)

    def probes(seen):
        return sum(1 for s in seen if "CROSS JOIN LATERAL" in s)

    with statements() as seen:
        first = await connections_for_document(session, document_id=mine)
        second = await connections_for_document(session, document_id=mine)
    assert probes(seen) == 1
    assert first.items == second.items
    assert [item.document_id for item in first.items] == [theirs]

    await _file(session, "mine.md", ["alpha", "beta", "delta"])
    await _embed_document(session, mine, MEMO_FP)
    with statements() as seen:
        await connections_for_document(session, document_id=mine)
    assert probes(seen) == 1

    await _register(session, ROTATED_FP)
    await session.execute(
        text(
            "UPDATE embedders SET registered_at = now() + interval '1 minute' "
            "WHERE fingerprint = :fp"
        ),
        {"fp": ROTATED_FP},
    )
    for document_id in (mine, theirs):
        await _embed_document(session, document_id, ROTATED_FP)
    with statements() as seen:
        await connections_for_document(session, document_id=mine)
    assert probes(seen) == 1


async def test_document_list_pages_before_counting_blocks(client, auth_headers, session):
    from app.api.routes.documents import _LIST_SQL

    project = "doccost-list"
    for n in range(3):
        await put_document(
            session, None, project=project, uri=f"with-blocks-{n}.md",
            content=f"# Doc {n}\n\none\n\ntwo\n", embed_inline=False,
        )
    await session.execute(
        text(
            "INSERT INTO documents (id, project, uri, title, content_hash, created_at) "
            "SELECT gen_random_uuid(), :p, 'bare-' || n || '.md', 'bare', md5(n::text), "
            "       now() - make_interval(secs => n) "
            "FROM generate_series(1, 300) AS n"
        ),
        {"p": project},
    )

    params = {"project": project, "limit": 20, "offset": 0}
    plan = (await session.execute(
        text(f"EXPLAIN (ANALYZE, FORMAT JSON) {_LIST_SQL.text}"), params,
    )).scalar_one()
    plan = plan if isinstance(plan, list) else json.loads(plan)

    def nodes(node):
        yield node
        for child in node.get("Plans", ()):
            yield from nodes(child)

    def scans_blocks(node):
        return any(n.get("Relation Name") == "blocks" for n in nodes(node))

    counted = [
        n for n in nodes(plan[0]["Plan"])
        if n.get("Parent Relationship") == "SubPlan" and scans_blocks(n)
    ]
    assert counted, "the block count must be a subquery evaluated per listed document"
    assert all(n["Actual Loops"] == 20 for n in counted)

    answer = await client.get(
        "/api/v1/documents", params={"project": project, "limit": 20}, headers=auth_headers,
    )
    assert answer.status_code == 200
    items = answer.json()["items"]
    assert len(items) == 20
    for item in items:
        direct = (await session.execute(
            text("SELECT count(*) FROM blocks WHERE document_id = CAST(:d AS uuid)"),
            {"d": item["id"]},
        )).scalar_one()
        assert item["block_count"] == direct
    assert any(item["block_count"] > 0 for item in items)

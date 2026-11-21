"""A block's vector follows its text: a document edit drops the old-text vector,
a re-file reuses vectors for unchanged text, inserts are batched, one bad block
cannot stall the sweep, and one helper registers a fingerprint."""
from __future__ import annotations

import ast
import hashlib
import math
import re
from pathlib import Path

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from app.api.deps import get_llm
from app.main import app
from app.services.block_embedding_refresh import refresh_block_embeddings
from app.services.block_embeddings import PARENT_TABLE
from app.services.document_door import put_document
from app.services.embedder_registry import child_table, embedder_registry

FINGERPRINT = "test-fp-lifecycle|3"
TABLE = child_table(PARENT_TABLE, FINGERPRINT)
SERVICES = Path(__file__).resolve().parents[1] / "app" / "services"


@pytest.fixture(autouse=True)
def _forget_fingerprint():
    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


def _vector(value: str) -> list[float]:
    digest = hashlib.sha256(value.encode()).digest()
    return [digest[0] + 1.0, digest[1] + 1.0, digest[2] + 1.0]


class RecordingEmbedder:
    """A distinct vector per text; records every text sent and every call."""

    def __init__(self, *, refuse: str | None = None, down: bool = False):
        self.refuse = refuse
        self.down = down
        self.batches: list[list[str]] = []
        self.probes: list[str] = []

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.batches.append(list(texts))
        if self.down or (self.refuse is not None and self.refuse in texts):
            raise RuntimeError("embedder refused the batch")
        return [_vector(t) for t in texts], FINGERPRINT

    async def embed(self, value: str):
        self.probes.append(value)
        if self.down:
            raise RuntimeError("embedder down")
        return _vector(value), FINGERPRINT

    def llm_fingerprint(self) -> str:
        return FINGERPRINT

    def sent(self) -> list[str]:
        return [t for batch in self.batches for t in batch]


async def _vectors_by_text(session, document_id) -> dict[str, str]:
    rows = await session.execute(text(
        f"SELECT b.text, e.embedding::text AS embedding FROM blocks b "
        f"JOIN {TABLE} e ON e.block_id = b.id WHERE b.document_id = CAST(:id AS uuid)"
    ), {"id": document_id})
    return {r.text: r.embedding for r in rows}


async def test_document_block_edit_with_a_failed_embed_answers_success(
    client, session, auth_headers,
):
    filed = await put_document(
        session, RecordingEmbedder(), project="p", uri="v/edit.md",
        content="# T\n\npara one\n\npara two\n",
    )
    await session.commit()
    block_id = (await session.execute(text(
        "SELECT CAST(id AS text) FROM blocks "
        "WHERE document_id = CAST(:id AS uuid) AND text = 'para one'"
    ), {"id": filed.document_id})).scalar_one()

    app.dependency_overrides[get_llm] = lambda: RecordingEmbedder(down=True)
    try:
        response = await client.patch(
            f"/api/v1/documents/{filed.document_id}/blocks/{block_id}",
            json={"text": "para one rewritten"}, headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_llm, None)

    assert response.status_code == 200, response.text
    assert response.json()["blocks_embedded"] == 0
    stored = (await session.execute(text(
        "SELECT text FROM blocks WHERE id = CAST(:id AS uuid)"
    ), {"id": block_id})).scalar_one()
    assert stored == "para one rewritten"
    vectors = (await session.execute(text(
        f"SELECT count(*) FROM {TABLE} WHERE block_id = CAST(:id AS uuid)"
    ), {"id": block_id})).scalar_one()
    assert vectors == 0


async def test_unchanged_repush_with_dimensions_makes_no_embed_call(session):
    content = "# T\n\npara one\n\npara two\n"
    await put_document(session, RecordingEmbedder(), project="p", uri="v/same.md", content=content)

    llm = RecordingEmbedder()
    again = await put_document(session, llm, project="p", uri="v/same.md", content=content)

    assert again.outcome == "unchanged"
    assert llm.batches == [] and llm.probes == []


async def test_refile_embeds_only_changed_blocks(session):
    paragraphs = [f"paragraph number {i}" for i in range(10)]
    first = await put_document(
        session, RecordingEmbedder(), project="p", uri="v/ten.md",
        content="\n\n".join(paragraphs) + "\n",
    )
    assert first.blocks_filed == 10
    before = await _vectors_by_text(session, first.document_id)

    changed = list(paragraphs)
    changed[4] = "paragraph number four, rewritten"
    llm = RecordingEmbedder()
    second = await put_document(
        session, llm, project="p", uri="v/ten.md", content="\n\n".join(changed) + "\n",
    )

    assert second.outcome == "updated"
    assert llm.sent() == ["paragraph number four, rewritten"]
    after = await _vectors_by_text(session, first.document_id)
    assert len(after) == 10
    for paragraph in paragraphs:
        if paragraph != paragraphs[4]:
            assert after[paragraph] == before[paragraph]


async def test_vector_inserts_are_batched(session):
    inserts: list[str] = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if re.search(rf"INSERT INTO {re.escape(TABLE)}\b", statement):
            inserts.append(statement)

    event.listen(Engine, "before_cursor_execute", capture)
    try:
        filed = await put_document(
            session, RecordingEmbedder(), project="p", uri="v/big.md",
            content="\n\n".join(f"block {i}" for i in range(200)) + "\n",
        )
    finally:
        event.remove(Engine, "before_cursor_execute", capture)

    assert filed.blocks_embedded == 200
    assert len(inserts) <= 5


async def test_unembeddable_block_does_not_poison_the_sweep(session):
    poison = "block 17 the embedder rejects"
    texts = [poison if i == 17 else f"block {i}" for i in range(60)]
    filed = await put_document(
        session, None, project="p", uri="v/sweep.md",
        content="\n\n".join(texts) + "\n", embed_inline=False,
    )
    await session.commit()

    first_llm = RecordingEmbedder(refuse=poison)
    await refresh_block_embeddings(session, first_llm, page_batch=0, worklog_batch=0)
    assert len(await _vectors_by_text(session, filed.document_id)) == 59
    assert len(first_llm.batches) <= 1 + 2 * math.ceil(math.log2(60))

    second_llm = RecordingEmbedder(refuse=poison)
    await refresh_block_embeddings(session, second_llm, page_batch=0, worklog_batch=0)
    assert second_llm.sent().count(poison) <= 1
    assert len(await _vectors_by_text(session, filed.document_id)) == 59


FAMILY_MODULES = (
    "block_embeddings", "worklog_embeddings", "relation_embeddings",
    "entity_anchoring",
)


def _calls_register(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "register"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "embedder_registry"
        ):
            return True
    return False


def _calls_ensure_registered(tree: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Call) and (
            (isinstance(node.func, ast.Name) and node.func.id == "ensure_registered")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "ensure_registered")
        )
        for node in ast.walk(tree)
    )


def test_one_fingerprint_registration_helper():
    copies = [
        f"{path.name}:{node.lineno}"
        for path in sorted(SERVICES.glob("*.py"))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "_ensure_partition"
    ]
    assert copies == []

    for name in FAMILY_MODULES:
        path = SERVICES / f"{name}.py"
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert not _calls_register(tree), name
        assert _calls_ensure_registered(tree), name

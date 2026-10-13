"""`put_document(embed_inline=False)` files and commits without an embedder (spec 2026-10-13 §2.4)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services.document_door import put_document

FINGERPRINT = "embed-inline-probe|3"


class StubEmbedder:
    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([[1.0, 0.0, 0.0] for _ in texts], FINGERPRINT)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0], FINGERPRINT


class Untouchable:
    def __getattr__(self, name):
        raise AssertionError(f"embed_inline=False touched the embedder ({name})")


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


async def test_no_inline_embed_files_the_document_and_embeds_nothing(session):
    filed = await put_document(
        session, Untouchable(), project="p", uri="superpowers/registers/r.md",
        content="# R\n\nBody.\n", actor="admin", embed_inline=False,
    )
    assert filed.outcome == "created"
    assert filed.blocks_filed > 0
    assert filed.blocks_embedded == 0
    revisions = (await session.execute(
        text("SELECT count(*) FROM document_revisions WHERE document_id = CAST(:d AS uuid)"),
        {"d": filed.document_id},
    )).scalar_one()
    assert revisions == 1


async def test_an_unchanged_put_without_inline_embed_skips_the_fingerprint_probe(session):
    first = await put_document(
        session, None, project="p", uri="superpowers/plans/x.md", content="# X\n",
        embed_inline=False,
    )
    again = await put_document(
        session, None, project="p", uri="superpowers/plans/x.md", content="# X\n",
        expected_hash=first.content_hash, embed_inline=False,
    )
    assert again.outcome == "unchanged"
    assert again.content_hash == first.content_hash


async def test_the_default_still_embeds_inline(session):
    filed = await put_document(
        session, StubEmbedder(), project="p", uri="notes/a.md", content="# A\n\nBody.\n",
    )
    assert filed.blocks_embedded == filed.blocks_filed > 0

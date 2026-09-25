"""The work-log vector family: its child table, and the writer that fills it."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services import worklog
from app.services.embedder_registry import EmbedderInfo, EmbedderRegistry, child_table, embedder_registry
from app.services.worklog_embeddings import EMBED_CHARS, MISSING_SQL, PARENT_TABLE, embed_entries

FAMILY_FP = "worklog-family-test|4"


async def _register_family_fingerprint(session) -> None:
    await EmbedderRegistry().register(
        session,
        EmbedderInfo(fingerprint=FAMILY_FP, model_id="worklog-family-test", dims=4, source="llm"),
    )


async def _indexes(session, table: str) -> list[str]:
    return list((await session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = :t"),
        {"t": table},
    )).scalars().all())


async def test_registering_a_fingerprint_creates_the_family_without_an_ann_index(session):
    await _register_family_fingerprint(session)
    table = child_table("worklog_embeddings", FAMILY_FP)

    columns = set((await session.execute(
        text("SELECT column_name FROM information_schema.columns "
             "WHERE table_schema = 'public' AND table_name = :t"),
        {"t": table},
    )).scalars().all())
    assert columns == {"entry_id", "fingerprint", "project", "embedding", "created_at"}

    indexes = await _indexes(session, table)
    assert not [d for d in indexes if "hnsw" in d], indexes
    assert any("(project)" in d for d in indexes), indexes


async def test_every_other_family_keeps_its_ann_index(session):
    await _register_family_fingerprint(session)
    indexes = await _indexes(session, child_table("page_embeddings", FAMILY_FP))
    assert any("hnsw" in d for d in indexes), indexes


WRITER_FP = "worklog-writer-test|3"


class RecordingEmbedder:
    """Answers a direction chosen from the text, or one fixed vector, so a
    test can tell which vector landed on which entry."""

    def __init__(self, fixed=None):
        self.fingerprint = WRITER_FP
        self.fixed = fixed
        self.texts: list[str] = []

    def _vector(self, value):
        if self.fixed is not None:
            return list(self.fixed)
        return [1.0, 0.0, 0.0] if "first" in value else [0.0, 1.0, 0.0]

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.texts.extend(texts)
        return [self._vector(t) for t in texts], self.fingerprint

    async def embed(self, value):
        return self._vector(value), self.fingerprint


@pytest.fixture(autouse=True)
def _forget_writer_fingerprint():
    embedder_registry.forget(WRITER_FP)
    yield
    embedder_registry.forget(WRITER_FP)


async def _append(session, *bodies, project="proj", key="plan-a"):
    result = await worklog.append(
        session, project=project, key=key, run_key="claude:run-1",
        entries=[{"kind": "note", "body": body} for body in bodies],
    )
    return result.workstream, [str(entry_id) for entry_id in result.entry_ids]


async def _vectors(session) -> dict[str, tuple[str, str]]:
    """entry id -> (project, the stored vector as pgvector prints it)."""
    table = child_table(PARENT_TABLE, WRITER_FP)
    rows = (await session.execute(
        text(f"SELECT CAST(entry_id AS text), project, CAST(embedding AS text) FROM {table}")
    )).all()
    return {row[0]: (row[1], row[2]) for row in rows}


async def test_embed_entries_writes_each_entrys_vector_with_its_project(session):
    _workstream, (first, second) = await _append(
        session, "first note", "second note", project="proj-x",
    )
    result = await embed_entries(session, RecordingEmbedder(), entry_ids=[first, second])
    assert result.written == 2
    assert result.fingerprint == WRITER_FP
    assert await _vectors(session) == {
        first: ("proj-x", "[1,0,0]"),
        second: ("proj-x", "[0,1,0]"),
    }


async def test_only_the_head_of_a_long_body_is_embedded(session):
    _workstream, ids = await _append(session, "a" * EMBED_CHARS + "b" * 1_000)
    llm = RecordingEmbedder()
    await embed_entries(session, llm, entry_ids=ids)
    assert llm.texts == ["a" * EMBED_CHARS]


async def test_nothing_to_embed_measures_no_fingerprint(session):
    llm = RecordingEmbedder()
    assert await embed_entries(session, llm, entry_ids=[]) is None
    assert await embed_entries(
        session, llm, entry_ids=["00000000-0000-0000-0000-000000000000"]
    ) is None
    assert llm.texts == []


async def test_re_embedding_replaces_the_vector(session):
    _workstream, ids = await _append(session, "note")
    await embed_entries(session, RecordingEmbedder(fixed=[1.0, 0.0, 0.0]), entry_ids=ids)
    await embed_entries(session, RecordingEmbedder(fixed=[0.0, 0.0, 1.0]), entry_ids=ids)
    assert await _vectors(session) == {ids[0]: ("proj", "[0,0,1]")}


async def test_the_missing_query_lists_only_unembedded_entries(session):
    _workstream, ids = await _append(session, "one", "two")
    await embed_entries(session, RecordingEmbedder(), entry_ids=ids[:1])
    missing = (await session.execute(
        text(MISSING_SQL.format(table=child_table(PARENT_TABLE, WRITER_FP))),
        {"fp": WRITER_FP, "limit": 100},
    )).scalars().all()
    assert ids[1] in missing
    assert ids[0] not in missing


async def test_purging_a_workstream_takes_its_vectors(session):
    workstream, ids = await _append(session, "note")
    await embed_entries(session, RecordingEmbedder(), entry_ids=ids)
    assert set(await _vectors(session)) == set(ids)
    await worklog.purge_workstream(session, workstream.id)
    assert await _vectors(session) == {}

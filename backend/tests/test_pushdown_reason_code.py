"""Project / status / archived pushdown on the last unscoped read channels.

Three channels are covered, each of which hands its rows straight to a model or
to a user without anything downstream to re-filter them:

* **``MemoryService.reason``** — doc 07 section 7's named escape. It has three
  passes (memory-type hint, tag hint, semantic) and the first two run *before*
  the semantic early-return, so a question that never reaches the vector path
  leaked anyway. Every pass renders its scope in SQL here, and the assertions
  are made against the prompt the reasoning model actually receives: a row that
  reaches that string has reached the answer.
* **``ChatService._retrieve``** — the same leak on the chat front door, which
  doc 07 section 9's consumer enumeration omits entirely.
* **Code search** — scoped by *repository*, which is a different axis from
  project: ``repositories`` carries no project column at all, so repository
  scope can never be derived from project scope, and a scoped probe must
  over-fetch for the same reason the memory channel does.

The fixtures are deliberately hostile: every out-of-scope row is an exact
semantic twin of the in-scope one and carries the same ``memory_type`` and
tags, so any pass that stops scoping surfaces it immediately.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.models.code import CodeFile, CodeSymbol, Repository
from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.repositories.relational import PostgresMemoryRepository
from app.repositories.vector import (
    SEMANTIC_FETCH_MULTIPLIER,
    MemoryFilter,
    PostgresVectorRepository,
)
from app.services.chat import ChatService
from app.services.code_query import CodeQueryService
from app.services.embedder_registry import child_table
from app.services.memory import MemoryService

FINGERPRINT = "reason-pushdown|4"
DIMS = 4
QUERY_VECTOR = [1.0, 0.0, 0.0, 0.0]


class _FakeLLM:
    """Records what the reasoning model was asked, and embeds deterministically."""

    def __init__(self):
        self.prompts: list[list[dict]] = []

    async def embed(self, query: str):
        return QUERY_VECTOR, FINGERPRINT

    async def chat_completion(self, purpose, messages=None, **kwargs):
        self.prompts.append(list(messages or []))
        return "synthesised answer"

    @property
    def last_prompt(self) -> str:
        return "\n".join(m["content"] for m in self.prompts[-1])


class _ScopedPipeline:
    """A pipeline whose ``semantic_search`` is the real, scoped SQL probe.

    Standing in a canned list here would prove nothing: the point is that the
    predicate reaches Postgres, so the fake delegates to the repository the
    production path uses and forwards whatever filter it was handed.
    """

    def __init__(self, session, *, ids_as_string: bool = False):
        self.session = session
        self.llm = _FakeLLM()
        self.filters_seen: list[MemoryFilter | None] = []
        self._ids_as_string = ids_as_string

    async def semantic_search(self, query, limit=20, semantic_weight=0.7, filters=None):
        self.filters_seen.append(filters)
        rows = await PostgresVectorRepository(self.session).search(
            QUERY_VECTOR, fingerprint=FINGERPRINT, limit=limit, filters=filters,
        )
        return [
            {
                "memory_id": str(r["memory_id"]) if self._ids_as_string else r["memory_id"],
                "score": r["score"],
            }
            for r in rows
        ]


class _NoSemanticPipeline(_ScopedPipeline):
    """Isolates the type/tag passes: the semantic arm returns nothing at all."""

    async def semantic_search(self, query, limit=20, semantic_weight=0.7, filters=None):
        self.filters_seen.append(filters)
        return []


async def _seed_partition(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": FINGERPRINT, "mid": "reason-pushdown", "dims": DIMS},
    )
    child = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({DIMS}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))


async def _add_memory(session, *, tags=None, **fields) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content="pgbouncer is the connection pooler",
        source="test",
        importance=0.5,
        metadata_={},
        project="alpha",
        status="active",
        memory_type="decision",
        is_archived=False,
    )
    base.update(fields)
    memory = Memory(**base)
    session.add(memory)
    await session.flush()

    child = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), '{}'::jsonb)"
        ),
        {"mid": base["id"], "fp": FINGERPRINT, "vec": str(QUERY_VECTOR)},
    )
    if tags:
        await PostgresMemoryRepository(session).set_tags(memory.id, list(tags))
    await session.flush()
    return memory


async def _hostile_corpus(session, *, tags=None) -> dict[str, Memory]:
    """One in-scope row and four twins that only scoping can tell apart."""
    await _seed_partition(session)
    mine = await _add_memory(
        session, content="IN-SCOPE alpha pooler decision", tags=tags,
    )
    replacement = await _add_memory(
        session, content="alpha replacement decision", tags=tags,
    )
    return {
        "mine": mine,
        "replacement": replacement,
        "foreign": await _add_memory(
            session, project="beta",
            content="LEAK foreign-project pooler decision", tags=tags,
        ),
        "superseded": await _add_memory(
            session, status="superseded", superseded_by=replacement.id,
            content="LEAK superseded pooler decision", tags=tags,
        ),
        "deprecated": await _add_memory(
            session, status="deprecated",
            content="LEAK deprecated pooler decision", tags=tags,
        ),
        "archived": await _add_memory(
            session, is_archived=True,
            content="LEAK archived pooler decision", tags=tags,
        ),
    }


def _source_ids(result: dict) -> set[uuid.UUID]:
    return {uuid.UUID(s["memory_id"]) for s in result["sources"]}


# ── memory_reason: the semantic pass ─────────────────────────────────


@pytest.mark.asyncio
async def test_reason_semantic_pass_scopes_project_status_and_archived(session):
    rows = await _hostile_corpus(session)

    pipeline = _ScopedPipeline(session)
    result = await MemoryService(session, pipeline=pipeline).reason(
        # No memory-type word, so only the semantic pass contributes.
        "which pooler are we using", limit=20, project="alpha",
    )

    assert _source_ids(result) == {rows["mine"].id, rows["replacement"].id}


@pytest.mark.asyncio
async def test_reason_forwards_its_scope_to_the_semantic_channel(session):
    await _hostile_corpus(session)

    pipeline = _ScopedPipeline(session)
    await MemoryService(session, pipeline=pipeline).reason(
        "which pooler are we using", project="alpha",
    )

    assert pipeline.filters_seen == [
        MemoryFilter(project="alpha", statuses=("active",), include_archived=False)
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("ids_as_string", [True, False])
async def test_reason_resolves_both_id_shapes(session, ids_as_string):
    """Hybrid emits ``str`` and the vector repository emits ``UUID``; a
    consumer that stops normalising drops every match with no error."""
    rows = await _hostile_corpus(session)

    pipeline = _ScopedPipeline(session, ids_as_string=ids_as_string)
    result = await MemoryService(session, pipeline=pipeline).reason(
        "which pooler are we using", limit=20, project="alpha",
    )

    assert rows["mine"].id in _source_ids(result)


# ── memory_reason: the passes that run before the semantic arm ───────


@pytest.mark.asyncio
async def test_reason_type_pass_is_scoped_without_reaching_the_vector_path(session):
    """The memory-type pass runs before the semantic early-return, so it leaked
    on questions the vector path never served."""
    rows = await _hostile_corpus(session)

    pipeline = _NoSemanticPipeline(session)
    result = await MemoryService(session, pipeline=pipeline).reason(
        "summarize recent decisions", limit=20, project="alpha",
    )

    assert result["sources"], "the type pass must still surface in-scope rows"
    assert _source_ids(result) == {rows["mine"].id, rows["replacement"].id}


@pytest.mark.asyncio
async def test_reason_tag_pass_is_scoped(session):
    rows = await _hostile_corpus(session, tags=["project/decisions"])

    pipeline = _NoSemanticPipeline(session)
    result = await MemoryService(session, pipeline=pipeline).reason(
        "summarize recent decisions", limit=20, project="alpha",
    )

    assert rows["foreign"].id not in _source_ids(result)
    assert rows["superseded"].id not in _source_ids(result)
    assert rows["archived"].id not in _source_ids(result)
    assert any(
        "project/decisions" in s["tags"] for s in result["sources"]
    ), "the tag pass must still contribute"


# ── memory_reason: nothing out of scope reaches the model ────────────


@pytest.mark.asyncio
async def test_reason_never_puts_an_out_of_scope_row_in_the_model_context(session):
    """The end the leak is measured at: the reasoning prompt itself."""
    rows = await _hostile_corpus(session, tags=["project/decisions"])

    pipeline = _ScopedPipeline(session)
    await MemoryService(session, pipeline=pipeline).reason(
        "summarize recent pooler decisions", limit=20, project="alpha",
    )

    prompt = pipeline.llm.last_prompt
    assert rows["mine"].content in prompt
    assert "LEAK" not in prompt


# ── memory_reason: the defaults, and the explicit opt-in ─────────────


@pytest.mark.asyncio
async def test_reason_without_a_project_still_excludes_dead_rows(session):
    """``project=None`` is 'every project', matching the search surface — but
    it never relaxes the status and archived predicates."""
    rows = await _hostile_corpus(session)

    pipeline = _ScopedPipeline(session)
    result = await MemoryService(session, pipeline=pipeline).reason(
        "which pooler are we using", limit=20,
    )

    ids = _source_ids(result)
    assert rows["foreign"].id in ids
    assert rows["superseded"].id not in ids
    assert rows["deprecated"].id not in ids
    assert rows["archived"].id not in ids


@pytest.mark.asyncio
async def test_reason_lineage_is_an_explicit_opt_in(session):
    """Proves the status predicate is parameterised rather than a literal
    ``'active'`` frozen into the SQL."""
    rows = await _hostile_corpus(session)

    pipeline = _ScopedPipeline(session)
    result = await MemoryService(session, pipeline=pipeline).reason(
        "which pooler are we using", limit=20,
        project="alpha", status=["active", "superseded"],
    )

    ids = _source_ids(result)
    assert rows["superseded"].id in ids
    assert rows["archived"].id not in ids


@pytest.mark.asyncio
async def test_reason_front_door_carries_the_project(client, auth_headers):
    """Invariant 17: a scope the service takes and no front door can set is a
    leak that is merely harder to reach."""
    from app.api.deps import get_memory_service
    from app.main import app

    seen: dict = {}

    class _Recorder:
        async def reason(self, question, limit=10, project=None, status=None):
            seen.update(question=question, limit=limit, project=project)
            return {"answer": "ok", "sources": []}

    app.dependency_overrides[get_memory_service] = lambda: _Recorder()
    try:
        resp = await client.post(
            "/api/v1/memories/reason",
            json={"question": "q", "limit": 5, "project": "alpha"},
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_memory_service, None)

    assert resp.status_code == 200
    assert seen["project"] == "alpha"


# ── chat: the consumer doc 07 section 9 omits ────────────────────────


@pytest.mark.asyncio
async def test_chat_retrieval_scopes_memories_in_sql(session):
    rows = await _hostile_corpus(session)

    svc = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))
    retrieval = await svc._retrieve("which pooler", {"project": "alpha"})

    # Composed rows carry the composition's own normalised str id
    # (invariant 9), so the comparison is spelled in that space.
    ids = {r["id"] for r in retrieval["memories"]}
    assert str(rows["mine"].id) in ids
    assert str(rows["foreign"].id) not in ids
    assert str(rows["superseded"].id) not in ids
    assert str(rows["archived"].id) not in ids


@pytest.mark.asyncio
async def test_chat_retrieval_excludes_dead_rows_without_a_project(session):
    rows = await _hostile_corpus(session)

    svc = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))
    retrieval = await svc._retrieve("which pooler", None)

    ids = {r["id"] for r in retrieval["memories"]}
    assert str(rows["mine"].id) in ids
    assert str(rows["superseded"].id) not in ids
    assert str(rows["deprecated"].id) not in ids
    assert str(rows["archived"].id) not in ids


@pytest.mark.asyncio
async def test_chat_entity_mention_is_scoped_by_asserting_memories(session):
    """Entities are not memory-scoped, so an @mention resolved without a scope
    hands the chat model a foreign project's graph."""
    rows = await _hostile_corpus(session)
    graph_repo = PostgresGraphRepository(session)
    await graph_repo.create_entity("pgbouncer", "tool", {}, rows["mine"].id)
    await graph_repo.create_entity("pgcat", "tool", {}, rows["foreign"].id)
    await session.flush()

    svc = ChatService(session, _FakeLLM(), graph_repo)
    retrieval = await svc._retrieve("compare @pgbouncer and @pgcat", {"project": "alpha"})

    names = {e.get("name") for e in retrieval["entities"]}
    assert "pgbouncer" in names
    assert "pgcat" not in names


# ── code search: scoped by repository, which is not project ──────────


async def _seed_code_partition(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": FINGERPRINT, "mid": "reason-pushdown", "dims": DIMS},
    )
    child = child_table("code_chunk_embeddings", FINGERPRINT)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " repo_id UUID NOT NULL,"
        " file_path VARCHAR(1024) NOT NULL,"
        " language VARCHAR(50),"
        " symbol_name VARCHAR(500),"
        " chunk_content TEXT,"
        " line_start INTEGER,"
        " line_end INTEGER,"
        f" embedding vector({DIMS}) NOT NULL)"
    ))


async def _add_chunk(session, repo_id, *, file_path, language="python", symbol="parse"):
    child = child_table("code_chunk_embeddings", FINGERPRINT)
    await session.execute(
        text(
            f"INSERT INTO {child} (fingerprint, repo_id, file_path, language, "
            "symbol_name, chunk_content, line_start, line_end, embedding) "
            "VALUES (:fp, CAST(:rid AS uuid), :path, :lang, :sym, :body, 1, 2, "
            "CAST(:vec AS vector))"
        ),
        {
            "fp": FINGERPRINT, "rid": str(repo_id), "path": file_path,
            "lang": language, "sym": symbol, "body": f"def {symbol}(): ...",
            "vec": str(QUERY_VECTOR),
        },
    )


async def _two_repos(session) -> tuple[Repository, Repository]:
    await _seed_code_partition(session)
    mine = Repository(name="mine")
    other = Repository(name="other")
    session.add_all([mine, other])
    await session.flush()
    return mine, other


@pytest.mark.asyncio
async def test_code_chunk_search_scopes_by_repository_in_sql(session):
    mine, other = await _two_repos(session)
    await _add_chunk(session, mine.id, file_path="mine/a.py")
    await _add_chunk(session, other.id, file_path="other/b.py")

    rows = await PostgresVectorRepository(session).search_code_chunks(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=10, repo_id=mine.id,
    )

    assert [r["file_path"] for r in rows] == ["mine/a.py"]


@pytest.mark.asyncio
async def test_code_chunk_search_scopes_by_language_in_sql(session):
    mine, _ = await _two_repos(session)
    await _add_chunk(session, mine.id, file_path="a.py", language="python")
    await _add_chunk(session, mine.id, file_path="a.ts", language="typescript")

    rows = await PostgresVectorRepository(session).search_code_chunks(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=10,
        repo_id=mine.id, language="typescript",
    )

    assert [r["file_path"] for r in rows] == ["a.ts"]


@pytest.mark.asyncio
async def test_code_search_scopes_both_arms_by_repository(session):
    """Hostile: the foreign repository holds the *exact* name match, so a
    keyword arm that stops scoping ranks it first rather than dropping it."""
    mine, other = await _two_repos(session)
    for repo, path in ((mine, "mine/a.py"), (other, "other/b.py")):
        cf = CodeFile(
            id=uuid.uuid4(), repo_id=repo.id, file_path=path,
            language="python", content_hash="h",
        )
        session.add(cf)
        await session.flush()
        session.add(CodeSymbol(
            id=uuid.uuid4(), file_id=cf.id, name="parse", kind="function",
            line_start=1, line_end=2, source_code="def parse(): ...",
        ))
        await _add_chunk(session, repo.id, file_path=path)
    await session.flush()

    results = await CodeQueryService(session, llm=_FakeLLM()).search_code(
        "parse", limit=10, repo_id=mine.id,
    )

    assert results
    assert {r["repo_id"] for r in results} == {str(mine.id)}


@pytest.mark.asyncio
async def test_scoped_code_chunk_search_overfetches_then_slices(session):
    """A repository predicate is a post-scan filter over the HNSW candidate
    stream, so a scoped probe that does not widen its fetch under-returns."""
    mine, _ = await _two_repos(session)
    for i in range(8):
        await _add_chunk(session, mine.id, file_path=f"mine/{i}.py")

    calls: list[dict] = []

    class _Recording:
        def __init__(self, inner):
            self._inner = inner

        async def execute(self, statement, params=None, *a, **kw):
            calls.append(dict(params or {}))
            return await self._inner.execute(statement, params, *a, **kw)

        def __getattr__(self, name):
            return getattr(self._inner, name)

    rows = await PostgresVectorRepository(_Recording(session)).search_code_chunks(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=3, repo_id=mine.id,
    )

    assert len(rows) == 3
    assert calls[-1]["limit"] == 3 * SEMANTIC_FETCH_MULTIPLIER


@pytest.mark.asyncio
async def test_unscoped_code_chunk_search_does_not_overfetch(session):
    mine, _ = await _two_repos(session)
    for i in range(8):
        await _add_chunk(session, mine.id, file_path=f"mine/{i}.py")

    calls: list[dict] = []

    class _Recording:
        def __init__(self, inner):
            self._inner = inner

        async def execute(self, statement, params=None, *a, **kw):
            calls.append(dict(params or {}))
            return await self._inner.execute(statement, params, *a, **kw)

        def __getattr__(self, name):
            return getattr(self._inner, name)

    rows = await PostgresVectorRepository(_Recording(session)).search_code_chunks(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=3,
    )

    assert len(rows) == 3
    assert calls[-1]["limit"] == 3


@pytest.mark.asyncio
async def test_repository_scope_is_not_project_scope(session):
    """Doc 07 section 7 draws the distinction deliberately, and the schema
    enforces it: nothing on the code side carries a project, so a repository
    can span any number of them and repository scope can never be derived
    from project scope."""
    columns = set((await session.execute(text(
        "SELECT table_name || '.' || column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' "
        "AND table_name IN ('repositories', 'code_files', 'code_symbols')"
    ))).scalars().all())

    assert not [c for c in columns if c.endswith(".project")]
    assert "repositories.name" in columns

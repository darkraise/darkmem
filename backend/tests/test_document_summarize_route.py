"""The summarize door (artifacts workspace increment 3).

`summarise_document` shipped with the generator and no caller anywhere in
`backend/app` -- no route, no job, no MCP tool -- so `GET /{id}/summary` read
a summary that nothing in the tree could ever write, and every summary panel
was permanently empty by construction. The spec called wiring it "no new
backend"; it is one route.

It spends an LLM call, so it carries `refuse_when_read_only` like the other
dial-out doors rather than only `require_auth`.
"""
import pytest

from app.api.deps import refuse_when_read_only, get_llm
from app.api.routes.auth import require_auth
from app.main import app
from app.services.document_door import put_document


class StubEmbedder:
    fingerprint = "test-fp-summarize|3"

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([[1.0, 0.0, 0.0] for _ in texts], self.fingerprint)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0], self.fingerprint


class StubLLM:
    """Returns fixed prose for the summarization purpose."""

    def __init__(self, prose="A short report over the document."):
        self.prose = prose
        self.purposes: list[str] = []

    async def chat_completion(self, purpose, messages, **kwargs):
        self.purposes.append(purpose)
        return self.prose


@pytest.fixture(autouse=True)
def _forget_fingerprint():
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(StubEmbedder.fingerprint)
    yield
    embedder_registry.forget(StubEmbedder.fingerprint)


@pytest.fixture
def authed():
    app.dependency_overrides[require_auth] = lambda: {"sub": "admin"}
    app.dependency_overrides[refuse_when_read_only] = lambda: None
    yield
    app.dependency_overrides.pop(require_auth, None)
    app.dependency_overrides.pop(refuse_when_read_only, None)
    app.dependency_overrides.pop(get_llm, None)


@pytest.mark.asyncio
async def test_summarize_generates_and_then_the_read_serves_it(
    client, session, authed,
):
    filed = await put_document(
        session, StubEmbedder(), project="p", uri="docs/s.md",
        content="# Title\n\nA paragraph worth summarising.\n",
    )
    await session.commit()

    # Before: the read is a 404, which is the state every install is in.
    missing = await client.get(f"/api/v1/documents/{filed.document_id}/summary")
    assert missing.status_code == 404

    llm = StubLLM()
    app.dependency_overrides[get_llm] = lambda: llm

    created = await client.post(f"/api/v1/documents/{filed.document_id}/summary")
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["text"] == "A short report over the document."
    # Never badged: a summary is a report over one document, not a claim.
    assert body["badged"] is False
    # It resolved the summarization purpose, not some other one.
    assert llm.purposes == ["summarization"]

    # After: the same summary is readable, so it was stored, not just returned.
    again = await client.get(f"/api/v1/documents/{filed.document_id}/summary")
    assert again.status_code == 200
    assert again.json()["text"] == "A short report over the document."


@pytest.mark.asyncio
async def test_summarize_a_document_that_does_not_exist_is_404(client, authed):
    app.dependency_overrides[get_llm] = lambda: StubLLM()
    missing = await client.post(
        "/api/v1/documents/00000000-0000-0000-0000-000000000000/summary"
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_summarize_a_document_with_no_blocks_is_422_not_an_empty_summary(
    client, session, authed,
):
    """`summarise_document` answers None for a document with nothing to
    summarise. Storing "" would later read as "its summary is empty prose",
    which is the distinction the GET route exists to preserve."""
    await session.execute(
        __import__("sqlalchemy").text(
            "INSERT INTO documents (id, project, uri, title, source_type, content_hash) "
            "VALUES (CAST(:id AS uuid), 'p', 'docs/empty.md', 't', 'markdown', 'h')"
        ),
        {"id": "11111111-1111-1111-1111-111111111111"},
    )
    await session.commit()
    app.dependency_overrides[get_llm] = lambda: StubLLM()

    refused = await client.post(
        "/api/v1/documents/11111111-1111-1111-1111-111111111111/summary"
    )
    assert refused.status_code == 422

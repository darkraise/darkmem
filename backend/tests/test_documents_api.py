"""The documents door (TH1.16, doc 16 §6).

The door adds no semantics, so most of what it must get right is what it
*refuses* to soften:

- a **withheld** Q&A answer carries no sentences at all, because prose still on
  the wire is served as ungrounded by any client that forgets to read a flag —
  invariant 14's failure exactly;
- a document with no summary is a **404**, not an empty 200: "no summary has
  been generated" and "the summary is empty prose" are different answers, and
  generating one is an explicit act nobody performed;
- every payload says `horizon`, so a client rendering this data somewhere else
  can still say what it is looking at.

The Q&A tests run against the real faithfulness gate and the real judge, which
refuses today — so the shipped behaviour of this door is `withheld`, and that
is asserted rather than mocked past.
"""
from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services import block_embeddings as be_mod
from app.services.document_ingest import BlockDraft, file_document
from app.services.document_summary import summarise_document

pytestmark = pytest.mark.asyncio

FINGERPRINT = "th116-probe|4"
PROJECT = "th116-docs"


class ScriptedLlm:
    """Embeds and answers; the judge refuses before it is ever consulted."""

    config = {"model": "probe", "base_url": "http://probe", "api_kind": "openai"}

    def __init__(self, payload=None, prose="A summary."):
        self.payload = payload
        self.prose = prose

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([[1.0, 0.0, 0.0, 0.0] for _ in texts], FINGERPRINT)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0, 0.0], FINGERPRINT

    async def chat_completion(self, purpose, messages, **kwargs):
        if purpose == "summarization":
            return self.prose
        return json.dumps(self.payload or {"sentences": []})


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


@pytest.fixture
def scripted_llm(client):
    """Point the app at a scripted orchestrator for the Q&A door.

    The payload is settable per test because the two outcomes below differ only
    in whether a sentence is cited — and that difference is what decides
    whether the judge is consulted at all.
    """
    from app.main import app

    llm = ScriptedLlm({"sentences": []})
    previous = getattr(app.state, "llm", None)
    app.state.llm = llm
    yield llm
    app.state.llm = previous


async def _file(session, *texts: str, title="doc", uri=None) -> str:
    drafts = [BlockDraft(text=t, type="paragraph", char_span=(0, len(t))) for t in texts]
    ingest = await file_document(
        session, project=PROJECT, content="\n\n".join(texts),
        parse=lambda: drafts, title=title, source_type="note", uri=uri,
    )
    await session.flush()
    return str(ingest.document_id)


# ── the list ─────────────────────────────────────────────────────────


async def test_the_list_serves_documents_and_says_it_is_horizon(
    client, session, auth_headers,
):
    await _file(session, "First body.", title="First", uri="file:///d/one")

    response = await client.get(
        f"/api/v1/documents?project={PROJECT}", headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["horizon"] is True
    assert [item["title"] for item in body["items"]] == ["First"]
    assert body["items"][0]["block_count"] == 1


async def test_the_list_requires_auth(client):
    assert (await client.get("/api/v1/documents")).status_code == 401


# ── the summary ──────────────────────────────────────────────────────


async def test_a_document_with_no_summary_is_a_404_not_an_empty_body(
    client, session, auth_headers,
):
    document_id = await _file(session, "Body.", uri="file:///d/nosummary")

    response = await client.get(
        f"/api/v1/documents/{document_id}/summary", headers=auth_headers,
    )

    assert response.status_code == 404
    assert "generated" in response.json()["detail"].lower()


async def test_a_generated_summary_is_served_and_marked_unbadged(
    client, session, auth_headers,
):
    document_id = await _file(session, "Body text.", uri="file:///d/summary")
    await summarise_document(session, ScriptedLlm(prose="Prose."), document_id=document_id)

    response = await client.get(
        f"/api/v1/documents/{document_id}/summary", headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["text"] == "Prose."
    assert body["badged"] is False, "a summary is a report, never a verified claim"
    assert "verification_status" not in body and "badge" not in body


# ── connections ──────────────────────────────────────────────────────


async def test_connections_serve_an_empty_list_rather_than_a_404(
    client, session, auth_headers,
):
    """A document with no connections is an ordinary answer, not an error —
    and the comparison state rides it either way. `embedded` is false here
    because nothing embedded this document's blocks, which is a different
    answer from "nothing relates to it"."""
    document_id = await _file(session, "Body.", uri="file:///d/conn")

    response = await client.get(
        f"/api/v1/documents/{document_id}/connections", headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "items": [], "embedded": False, "comparable_documents": 0,
    }


# ── grounded Q&A, behind its gate ────────────────────────────────────


async def _seed_blocks(session, llm, *texts: str) -> list[str]:
    """Scoped to the document just filed, never `SELECT id FROM blocks`.

    `embed_blocks` registers the fingerprint, and registration **commits** — so
    a document filed by one test outlives that test's rollback and an unscoped
    query picks up a block from another document. The citation then names a
    block the retrieval never returned, the gate drops it, and the outcome
    flips from withheld to labelled: green alone, red in a full run. The same
    residue class T4.11 and T4.13 closed in two other suites.
    """
    document_id = await _file(session, *texts, uri="file:///d/qa")
    block_ids = [str(r) for r in (await session.execute(
        text("SELECT id FROM blocks WHERE document_id = CAST(:d AS uuid) ORDER BY order_index"),
        {"d": document_id},
    )).scalars().all()]
    await be_mod.embed_blocks(session, llm, block_ids=block_ids)
    return block_ids


async def test_a_cited_answer_is_withheld_today_and_carries_no_sentences(
    client, session, auth_headers, scripted_llm,
):
    """The shipped behaviour, against the real judge: a *cited* sentence is the
    one that reaches it, no faithfulness qualification record exists, so the
    gate cannot clear. The response says withheld and the prose does not
    travel."""
    blocks = await _seed_blocks(session, scripted_llm, "The sky is blue.")
    scripted_llm.payload = {"sentences": [
        {"text": "The sky is blue.", "block_id": blocks[0], "span_start": 0, "span_end": 3},
    ]}

    response = await client.post(
        "/api/v1/documents/qa",
        json={"question": "what colour is the sky", "project": PROJECT},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["outcome"] == "withheld"
    assert body["grounded"] is False
    assert body["judged"] is False, "the judge refused rather than disagreeing"
    assert body["sentences"] == [], "a withheld answer must not put prose on the wire"
    assert body["label"] == "answer withheld: not grounded"
    assert body["horizon"] is True


async def test_an_all_uncited_answer_is_labelled_without_consulting_the_judge(
    client, session, auth_headers, scripted_llm,
):
    """The other outcome, and the reason it differs: an uncited sentence never
    reaches the judge (doc 16 §4 — a claim with no citation fails outright),
    so the gate decides on coverage alone and labels. The sentences travel
    here, because "we checked and it is not fully grounded" is an honest
    partial rather than an ungrounded answer served as grounded."""
    await _seed_blocks(session, scripted_llm, "The sky is blue.")
    scripted_llm.payload = {"sentences": [{"text": "Unsupported.", "block_id": None}]}

    response = await client.post(
        "/api/v1/documents/qa",
        json={"question": "what colour is the sky", "project": PROJECT},
        headers=auth_headers,
    )

    body = response.json()
    assert body["outcome"] == "labelled"
    assert body["grounded"] is False
    assert body["judged"] is True
    assert body["label"] == "could not fully ground this answer"
    assert [s["text"] for s in body["sentences"]] == ["Unsupported."]
    assert body["sentences"][0]["citation"] is None


async def test_qa_requires_a_question_and_a_project(client, auth_headers, scripted_llm):
    assert (await client.post(
        "/api/v1/documents/qa", json={"question": "", "project": PROJECT},
        headers=auth_headers,
    )).status_code == 422
    assert (await client.post(
        "/api/v1/documents/qa", json={"question": "q"}, headers=auth_headers,
    )).status_code == 422


async def test_qa_requires_auth(client):
    response = await client.post(
        "/api/v1/documents/qa", json={"question": "q", "project": PROJECT},
    )
    assert response.status_code == 401

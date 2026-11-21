"""The context-boost arm is gone, and retrieval ranks exactly as it did.

No door ever declared a context into the composition, so ``w_context_boost``
never moved a row, ``excluded.by_context_conflict`` was always 0 and
``community_injection_enabled`` had no reader. Removing them must leave every
retrieval order bit-identical: the expected ids below were recorded on the
code before the removal, over a corpus whose ids, text and vectors are all
fixed.
"""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
import re
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.models.config import Config
from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.schemas.memory import MemorySearchRequest
from app.services.chat import CHAT_STATUSES, ChatService
from app.services.embedder_registry import child_table
from app.services.memory import MemoryService

BACKEND = pathlib.Path(__file__).resolve().parents[1]
REMOVED_NAMES = (
    "w_context_boost",
    "community_injection_enabled",
    "by_context_conflict",
    "CONTEXT_BOOST_FLAG",
)

FINGERPRINT = "ctx-removed|8"
DIMS = 8
PROJECT = "ctx-removed"

TOPICS = (
    "pgbouncer connection pooling",
    "postgres vacuum bloat",
    "docker compose bridge network",
    "ollama embedding model rotation",
    "backup dump retention",
    "websocket session revocation",
)
DETAILS = (
    "chosen over pgcat",
    "measured on the homelab",
    "breaks under two workers",
    "documented in the runbook",
    "reverted after a regression",
)
QUERIES = (
    "pgbouncer connection pooling",
    "vacuum bloat on postgres",
    "embedding model rotation runbook",
    "backup retention measured",
    "session revocation regression",
)


def _vector(body: str) -> list[float]:
    """A vector that is a function of the text alone, so a re-run cannot drift."""
    vec = [0.0] * DIMS
    for word in re.findall(r"[a-z]+", body.lower()):
        vec[int(hashlib.sha256(word.encode()).hexdigest(), 16) % DIMS] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class _TextEmbedder:
    async def embed(self, query: str):
        return _vector(query), FINGERPRINT

    async def chat_completion(self, purpose, messages=None, **kwargs):
        return "answer"

    async def chat_completion_stream(self, purpose, messages=None, **kwargs):
        yield "answer"


FILLERS = ("homelab", "staging", "rollout", "ticket", "followup", "audit", "draft")
# One word per hash bucket of `_vector` (alpha -> 0, mike -> 1, ... papa -> 7),
# so every row shares a bucket with every query: an orthogonal row sits at
# cosine distance exactly 1.0, and two of them tie.
COVER = ("alpha", "mike", "bravo", "india", "charlie", "echo", "foxtrot", "papa")
COVER_STEPS = (2, 3, 5, 7, 11, 13, 17, 19)


def _content(n: int) -> str:
    """Every row differs in topic repetition and filler, so no two rows tie on
    either arm for any query (asserted before the doors run)."""
    topic = TOPICS[n % len(TOPICS)]
    filler = " ".join([FILLERS[n % len(FILLERS)]] * (1 + n % 3))
    return (
        " ".join([topic] * (1 + n // len(TOPICS)))
        + f" {DETAILS[n % len(DETAILS)]} {filler} "
        + " ".join(
            word for word, step in zip(COVER, COVER_STEPS) for _ in range(1 + (n * step) % 7)
        )
    )


async def _seed_corpus(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, 'ctx-removed', :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": FINGERPRINT, "dims": DIMS},
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
    for n in range(1, 31):
        body = _content(n)
        session.add(Memory(
            id=uuid.UUID(int=n), content=body, source="test", importance=0.5,
            metadata_={}, project=PROJECT, status="active", memory_type="fact",
            is_archived=False,
        ))
        await session.flush()
        await session.execute(
            text(
                f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
                "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
            ),
            {
                "mid": uuid.UUID(int=n), "fp": FINGERPRINT, "vec": str(_vector(body)),
                "payload": '{"content": "seeded", "source": "test", "tags": []}',
            },
        )
    await session.flush()


@pytest.fixture
def doors(session, monkeypatch):
    from app.api.mcp import server as mcp_server

    @asynccontextmanager
    async def _same_session():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", _same_session)
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=_TextEmbedder()))
    return mcp_server


async def _memory_door(session, query: str) -> list[int]:
    service = MemoryService(session, pipeline=SimpleNamespace(llm=_TextEmbedder()))
    page = await service.search_memories_paginated(MemorySearchRequest(
        query=query, project=PROJECT, status=list(CHAT_STATUSES),
        limit=20, offset=0, with_trace=True,
    ))
    return [uuid.UUID(str(item.memory.id)).int for item in page["items"]]


async def _chat(session, query: str) -> dict:
    svc = ChatService(session, _TextEmbedder(), PostgresGraphRepository(session))
    return await svc._retrieve(query, {"project": PROJECT})


async def _knowledge(mcp_server, query: str) -> dict:
    return json.loads(await mcp_server.knowledge_search(
        query=query, project=PROJECT, limit=20, fuse=True,
    ))


EXPECTED_ORDER: dict[str, dict[str, list[int]]] = {
    "pgbouncer connection pooling": {
        "memory_search": [24, 30, 12, 18, 6, 10, 3, 5, 28, 19, 26, 22, 20, 13, 27, 15, 8, 16, 21, 2],
        "chat": [24, 30, 12, 18, 6, 10, 3, 5, 28, 19],
        "knowledge_search": [24, 30, 12, 18, 6, 10, 3, 5, 28, 19, 26, 22, 20, 13, 27, 15, 8, 16, 21, 2],
    },
    "vacuum bloat on postgres": {
        "memory_search": [25, 7, 1, 13, 19, 2, 11, 23, 4, 9, 16, 8, 18, 30, 14, 26, 29, 20, 6, 15],
        "chat": [25, 7, 1, 13, 19, 2, 11, 23, 4, 9],
        "knowledge_search": [25, 7, 1, 13, 19, 2, 11, 23, 4, 9, 16, 8, 18, 30, 14, 26, 29, 20, 6, 15],
    },
    "embedding model rotation runbook": {
        "memory_search": [3, 29, 15, 1, 27, 22, 17, 11, 23, 19, 21, 7, 5, 13, 25, 4, 9, 8, 12, 18],
        "chat": [3, 29, 15, 1, 27, 22, 17, 11, 23, 19],
        "knowledge_search": [3, 29, 15, 1, 27, 22, 17, 11, 23, 19, 21, 7, 5, 13, 25, 4, 9, 8, 12, 18],
    },
    "backup retention measured": {
        "memory_search": [16, 28, 10, 6, 13, 3, 24, 9, 4, 19, 30, 22, 27, 2, 17, 20, 7, 21, 18, 5],
        "chat": [16, 28, 10, 6, 13, 3, 24, 9, 4, 19],
        "knowledge_search": [16, 28, 10, 6, 13, 3, 24, 9, 4, 19, 30, 22, 27, 2, 17, 20, 7, 21, 18, 5],
    },
    "session revocation regression": {
        "memory_search": [29, 23, 17, 7, 9, 2, 1, 11, 21, 15, 8, 16, 25, 22, 3, 27, 14, 19, 13, 26],
        "chat": [29, 23, 17, 7, 9, 2, 1, 11, 21, 15],
        "knowledge_search": [29, 23, 17, 7, 9, 2, 1, 11, 21, 15, 8, 16, 25, 22, 3, 27, 14, 19, 13, 26],
    },
}


def test_no_context_boost_name_remains_in_the_backend():
    roots = (BACKEND / "app", BACKEND / "scripts" / "benchlib")
    hits = [
        f"{path.relative_to(BACKEND)}: {name}"
        for root in roots
        for path in sorted(root.rglob("*.py"))
        for name in REMOVED_NAMES
        if name in path.read_text(encoding="utf-8")
    ]
    assert hits == []


async def test_stored_keys_are_not_served(session, client, auth_headers):
    session.add(Config(key="feature_flags", value={
        "w_context_boost": 0.4, "community_injection_enabled": True,
    }))
    await session.flush()

    response = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "w_context_boost" not in body
    assert "community_injection_enabled" not in body
    assert "w_context_boost" not in body["numeric_bounds"]
    assert "community_injection" not in {c["name"] for c in body["graph_channels"]}

    for patch in ({"w_context_boost": 0.1}, {"community_injection_enabled": True}):
        refused = await client.put(
            "/api/v1/config/feature-flags", json=patch, headers=auth_headers,
        )
        assert refused.status_code == 422, (patch, refused.text)


async def _assert_no_ties(session, query: str) -> None:
    """Neither arm may tie: the doors break no ties, so a tied pair would
    come back in whatever order the scan produced."""
    ranks = (await session.execute(text(
        "SELECT ts_rank(search_vector, plainto_tsquery('english', :q)) FROM memories "
        "WHERE project = :p AND search_vector @@ plainto_tsquery('english', :q)"
    ), {"q": query, "p": PROJECT})).scalars().all()
    distances = (await session.execute(text(
        f"SELECT embedding <=> CAST(:vec AS vector) FROM {child_table('memory_embeddings', FINGERPRINT)}"
    ), {"vec": str(_vector(query))})).scalars().all()
    assert len(distances) == 30
    assert len(set(ranks)) == len(ranks), (query, sorted(ranks))
    assert len(set(distances)) == len(distances), (query, sorted(distances))


async def test_retrieval_order_is_unchanged(session, doors):
    await _seed_corpus(session)
    for query in QUERIES:
        await _assert_no_ties(session, query)

    observed: dict[str, dict[str, list[int]]] = {}
    for query in QUERIES:
        chat = await _chat(session, query)
        tool = await _knowledge(doors, query)
        observed[query] = {
            "memory_search": await _memory_door(session, query),
            "chat": [uuid.UUID(row["id"]).int for row in chat["memories"]],
            "knowledge_search": [
                uuid.UUID(row["id"]).int for row in tool["rows"] if row["id_kind"] == "memory"
            ],
        }

    assert observed == EXPECTED_ORDER, json.dumps(observed)


async def test_envelope_excluded_has_no_context_counter(session, doors):
    await _seed_corpus(session)

    chat = await _chat(session, QUERIES[0])
    tool = await _knowledge(doors, QUERIES[0])

    for envelope in (chat["envelope"], tool["envelope"]):
        assert "by_result_limit" in envelope["excluded"]
        assert "by_context_conflict" not in envelope["excluded"]

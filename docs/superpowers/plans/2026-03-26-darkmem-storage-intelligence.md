# darkmem Storage & Intelligence — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add LLM-powered processing, vector search (Qdrant), knowledge graph (Neo4j), hybrid search, and entity extraction to the existing darkmem backend.

**Architecture:** Extends the layered monolith with two new repository implementations (Qdrant, Neo4j), an LLM orchestrator, extraction service, and an async processing pipeline that runs on memory create/update. All new services are optional — the system gracefully degrades to Postgres-only when external services are unavailable.

**Tech Stack:** qdrant-client (async), neo4j Python driver (async), httpx (OpenAI-compatible API), asyncio background tasks

---

## Prerequisites

- Plan 1 (Backend Foundation) is complete — 36 tests passing
- PostgreSQL running on localhost:5433
- Qdrant running on localhost:6333 (from docker-compose.dev.yml)
- Neo4j running on localhost:7687 (from docker-compose.dev.yml)

**Neo4j compose fix:** The original healthcheck may fail. Before starting, update `docker-compose.dev.yml` Neo4j healthcheck to:
```yaml
healthcheck:
  test: ["CMD-SHELL", "wget -q --spider http://localhost:7474 || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 5
```

Start services: `docker compose -f docker-compose.dev.yml up -d postgres qdrant neo4j`

---

## File Structure (new/modified files)

```
backend/
├── pyproject.toml                          # MODIFY: add qdrant-client, neo4j
├── app/
│   ├── config.py                           # MODIFY: add LLM config model
│   ├── main.py                             # MODIFY: add lifespan init, new routes
│   ├── services/
│   │   ├── llm.py                          # CREATE: LLM orchestrator
│   │   ├── extraction.py                   # CREATE: entity/relation extraction
│   │   ├── pipeline.py                     # CREATE: async processing pipeline
│   │   └── memory.py                       # MODIFY: hybrid search, cascade ops
│   ├── repositories/
│   │   ├── vector.py                       # CREATE: Qdrant implementation
│   │   └── graph.py                        # CREATE: Neo4j implementation
│   ├── schemas/
│   │   ├── graph.py                        # CREATE: graph response schemas
│   │   └── config.py                       # CREATE: LLM config schemas
│   ├── api/
│   │   ├── deps.py                         # MODIFY: add new dependencies
│   │   └── routes/
│   │       ├── graph.py                    # CREATE: graph query endpoints
│   │       ├── analytics.py               # CREATE: stats endpoint
│   │       └── config.py                   # CREATE: LLM config endpoint
│   │       └── memories.py                 # MODIFY: add merge, duplicates, reason
├── tests/
│   ├── test_llm.py                         # CREATE
│   ├── test_vector_repo.py                 # CREATE
│   ├── test_graph_repo.py                  # CREATE
│   ├── test_extraction.py                  # CREATE
│   ├── test_pipeline.py                    # CREATE
│   └── test_api/
│       ├── test_graph.py                   # CREATE
│       └── test_analytics.py              # CREATE
```

---

### Task 1: Dependencies + LLM Orchestrator

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/config.py`
- Create: `backend/app/services/llm.py`
- Create: `backend/tests/test_llm.py`

- [ ] **Step 1: Add dependencies to `backend/pyproject.toml`**

Add to the `dependencies` list:
```toml
    "qdrant-client>=1.12.0",
    "neo4j>=5.25.0",
```

Run: `cd backend && pip install -e ".[dev]"`

- [ ] **Step 2: Add LLM config model to `backend/app/config.py`**

Replace the entire file:

```python
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMPurposeConfig(BaseModel):
    provider: str = "ollama"
    base_url: str = "http://localhost:11434/v1"
    model: str = "nomic-embed-text"
    api_key: str | None = None
    dimensions: int | None = None
    params: dict = Field(default_factory=dict)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem"
    test_database_url: str = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test"
    qdrant_url: str = "http://localhost:6333"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "darkmem"
    api_key_prefix: str = "dm_"

    llm_embedding: LLMPurposeConfig = LLMPurposeConfig(
        provider="ollama", base_url="http://localhost:11434/v1",
        model="nomic-embed-text", dimensions=768,
    )
    llm_extraction: LLMPurposeConfig = LLMPurposeConfig(
        provider="ollama", base_url="http://localhost:11434/v1",
        model="qwen3:8b", params={"temperature": 0.2},
    )
    llm_reasoning: LLMPurposeConfig = LLMPurposeConfig(
        provider="ollama", base_url="http://localhost:11434/v1",
        model="qwen3:8b", params={"temperature": 0.7},
    )
    llm_summarization: LLMPurposeConfig = LLMPurposeConfig(
        provider="ollama", base_url="http://localhost:11434/v1",
        model="qwen3:8b", params={"temperature": 0.3},
    )


settings = Settings()
```

- [ ] **Step 3: Write LLM tests — `backend/tests/test_llm.py`**

```python
import json

import httpx
import pytest

from app.config import LLMPurposeConfig
from app.services.llm import LLMOrchestrator


def _make_orchestrator(handler):
    """Create orchestrator with a mock HTTP transport."""
    transport = httpx.MockTransport(handler)
    config = {
        "embedding": LLMPurposeConfig(base_url="http://mock", model="test-embed", dimensions=3),
        "extraction": LLMPurposeConfig(base_url="http://mock", model="test-extract", params={"temperature": 0.2}),
        "reasoning": LLMPurposeConfig(base_url="http://mock", model="test-reason"),
        "summarization": LLMPurposeConfig(base_url="http://mock", model="test-sum"),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=transport)
    return llm


async def test_embed():
    def handler(request: httpx.Request):
        body = json.loads(request.content)
        assert body["model"] == "test-embed"
        assert body["input"] == "hello world"
        return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2, 0.3]}]})

    llm = _make_orchestrator(handler)
    result = await llm.embed("hello world")
    assert result == [0.1, 0.2, 0.3]
    await llm.close()


async def test_chat_completion():
    def handler(request: httpx.Request):
        body = json.loads(request.content)
        assert body["model"] == "test-extract"
        assert body["temperature"] == 0.2
        return httpx.Response(200, json={
            "choices": [{"message": {"content": '{"entities": [], "relationships": []}'}}]
        })

    llm = _make_orchestrator(handler)
    result = await llm.chat_completion(
        "extraction",
        messages=[{"role": "user", "content": "test"}],
    )
    assert "entities" in result
    await llm.close()


async def test_chat_completion_with_extra_body():
    def handler(request: httpx.Request):
        body = json.loads(request.content)
        assert body.get("thinking") is False
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "result"}}]
        })

    config = {
        "extraction": LLMPurposeConfig(
            base_url="http://mock", model="test",
            params={"temperature": 0.2, "extra_body": {"thinking": False}},
        ),
        "embedding": LLMPurposeConfig(base_url="http://mock", model="test-embed"),
        "reasoning": LLMPurposeConfig(base_url="http://mock", model="test"),
        "summarization": LLMPurposeConfig(base_url="http://mock", model="test"),
    }
    llm = LLMOrchestrator(config)
    transport = httpx.MockTransport(handler)
    llm._client = httpx.AsyncClient(transport=transport)
    result = await llm.chat_completion("extraction", messages=[{"role": "user", "content": "test"}])
    assert result == "result"
    await llm.close()


async def test_embed_with_api_key():
    def handler(request: httpx.Request):
        assert request.headers["Authorization"] == "Bearer sk-test123"
        return httpx.Response(200, json={"data": [{"embedding": [1.0, 2.0]}]})

    config = {
        "embedding": LLMPurposeConfig(base_url="http://mock", model="test", api_key="sk-test123", dimensions=2),
        "extraction": LLMPurposeConfig(base_url="http://mock", model="test"),
        "reasoning": LLMPurposeConfig(base_url="http://mock", model="test"),
        "summarization": LLMPurposeConfig(base_url="http://mock", model="test"),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    result = await llm.embed("test")
    assert result == [1.0, 2.0]
    await llm.close()
```

- [ ] **Step 4: Implement `backend/app/services/llm.py`**

```python
import httpx

from app.config import LLMPurposeConfig


class LLMOrchestrator:
    def __init__(self, config: dict[str, LLMPurposeConfig]):
        self.config = config
        self._client = httpx.AsyncClient(timeout=120.0)

    async def embed(self, text: str) -> list[float]:
        cfg = self.config["embedding"]
        headers = self._headers(cfg)
        response = await self._client.post(
            f"{cfg.base_url}/embeddings",
            headers=headers,
            json={"input": text, "model": cfg.model},
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

    async def chat_completion(self, purpose: str, messages: list[dict], response_format: dict | None = None) -> str:
        cfg = self.config[purpose]
        headers = self._headers(cfg)

        body: dict = {"model": cfg.model, "messages": messages}
        # Apply standard params
        for key, value in cfg.params.items():
            if key != "extra_body":
                body[key] = value
        # Apply extra_body params (provider-specific)
        if "extra_body" in cfg.params:
            body.update(cfg.params["extra_body"])
        if response_format:
            body["response_format"] = response_format

        response = await self._client.post(
            f"{cfg.base_url}/chat/completions",
            headers=headers,
            json=body,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    async def close(self):
        await self._client.aclose()

    @staticmethod
    def _headers(cfg: LLMPurposeConfig) -> dict:
        headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"
        return headers
```

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_llm.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/app/config.py backend/app/services/llm.py backend/tests/test_llm.py
git commit -m "feat: add LLM orchestrator with per-purpose config"
```

---

### Task 2: Qdrant Vector Repository

**Files:**
- Create: `backend/app/repositories/vector.py`
- Create: `backend/tests/test_vector_repo.py`

- [ ] **Step 1: Write vector repo tests — `backend/tests/test_vector_repo.py`**

These tests require Qdrant running on localhost:6333. They use a test collection that is cleaned up after each test.

```python
import uuid

import pytest
import pytest_asyncio
from qdrant_client import AsyncQdrantClient

from app.repositories.vector import QdrantVectorRepository

TEST_COLLECTION = "test_memories"


@pytest_asyncio.fixture
async def qdrant_client():
    client = AsyncQdrantClient(url="http://localhost:6333")
    try:
        await client.get_collections()
    except Exception:
        pytest.skip("Qdrant not available")
    yield client
    # Cleanup
    try:
        await client.delete_collection(TEST_COLLECTION)
    except Exception:
        pass
    await client.close()


@pytest_asyncio.fixture
async def vector_repo(qdrant_client):
    repo = QdrantVectorRepository(qdrant_client, dimensions=4, collection_name=TEST_COLLECTION)
    await repo.ensure_collection()
    return repo


async def test_upsert_and_search(vector_repo):
    mid = uuid.uuid4()
    await vector_repo.upsert(mid, [0.1, 0.2, 0.3, 0.4], {"memory_id": str(mid), "content": "test"})

    results = await vector_repo.search([0.1, 0.2, 0.3, 0.4], limit=5)
    assert len(results) == 1
    assert results[0]["memory_id"] == mid


async def test_delete(vector_repo):
    mid = uuid.uuid4()
    await vector_repo.upsert(mid, [1.0, 0.0, 0.0, 0.0], {"memory_id": str(mid), "content": "delete me"})
    await vector_repo.delete(mid)

    results = await vector_repo.search([1.0, 0.0, 0.0, 0.0], limit=5)
    assert len(results) == 0


async def test_find_similar(vector_repo):
    m1 = uuid.uuid4()
    m2 = uuid.uuid4()
    m3 = uuid.uuid4()
    await vector_repo.upsert(m1, [1.0, 0.0, 0.0, 0.0], {"memory_id": str(m1), "content": "a"})
    await vector_repo.upsert(m2, [0.99, 0.01, 0.0, 0.0], {"memory_id": str(m2), "content": "b"})
    await vector_repo.upsert(m3, [0.0, 0.0, 0.0, 1.0], {"memory_id": str(m3), "content": "c"})

    similar = await vector_repo.find_similar(m1, threshold=0.9, limit=5)
    similar_ids = [r["memory_id"] for r in similar]
    assert m2 in similar_ids
    assert m3 not in similar_ids
```

- [ ] **Step 2: Implement `backend/app/repositories/vector.py`**

```python
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


class QdrantVectorRepository:
    def __init__(self, client: AsyncQdrantClient, dimensions: int = 768, collection_name: str = "memories"):
        self.client = client
        self.dimensions = dimensions
        self.collection_name = collection_name

    async def ensure_collection(self):
        collections = await self.client.get_collections()
        names = [c.name for c in collections.collections]
        if self.collection_name not in names:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.dimensions, distance=Distance.COSINE),
            )

    async def upsert(self, memory_id: UUID, vector: list[float], payload: dict):
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(id=str(memory_id), vector=vector, payload=payload)],
        )

    async def search(self, vector: list[float], limit: int = 20) -> list[dict]:
        results = await self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=limit,
        )
        return [
            {"memory_id": UUID(p.id), "score": p.score, "payload": p.payload}
            for p in results.points
        ]

    async def delete(self, memory_id: UUID):
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=[str(memory_id)],
        )

    async def find_similar(self, memory_id: UUID, threshold: float = 0.9, limit: int = 10) -> list[dict]:
        points = await self.client.retrieve(
            collection_name=self.collection_name, ids=[str(memory_id)], with_vectors=True,
        )
        if not points:
            return []
        vector = points[0].vector
        results = await self.search(vector, limit=limit + 1)
        return [r for r in results if r["memory_id"] != memory_id and r["score"] >= threshold]
```

- [ ] **Step 3: Run tests**

Run: `cd backend && pytest tests/test_vector_repo.py -v`
Expected: All 3 tests PASS (or skip if Qdrant not running).

- [ ] **Step 4: Commit**

```bash
git add backend/app/repositories/vector.py backend/tests/test_vector_repo.py
git commit -m "feat: add Qdrant vector repository"
```

---

### Task 3: Neo4j Graph Repository

**Files:**
- Create: `backend/app/repositories/graph.py`
- Create: `backend/tests/test_graph_repo.py`

- [ ] **Step 1: Write graph repo tests — `backend/tests/test_graph_repo.py`**

```python
import uuid

import pytest
import pytest_asyncio
from neo4j import AsyncGraphDatabase

from app.config import settings
from app.repositories.graph import Neo4jGraphRepository


@pytest_asyncio.fixture
async def neo4j_driver():
    try:
        driver = AsyncGraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
        await driver.verify_connectivity()
    except Exception:
        pytest.skip("Neo4j not available")
    yield driver
    # Cleanup: delete all test nodes
    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")
    await driver.close()


@pytest_asyncio.fixture
async def graph_repo(neo4j_driver):
    return Neo4jGraphRepository(neo4j_driver)


async def test_create_entity(graph_repo):
    mid = uuid.uuid4()
    entity = await graph_repo.create_entity("PostgreSQL", "technology", {"version": "17"}, mid)
    assert entity["name"] == "PostgreSQL"
    assert entity["entity_type"] == "technology"


async def test_create_relationship(graph_repo):
    mid = uuid.uuid4()
    await graph_repo.create_entity("darkmem", "project", {}, mid)
    await graph_repo.create_entity("PostgreSQL", "technology", {}, mid)
    await graph_repo.create_relationship("darkmem", "PostgreSQL", "USES", {}, 0.9, mid)

    neighbors = await graph_repo.get_neighbors_by_name("darkmem")
    assert len(neighbors["neighbors"]) == 1
    assert neighbors["neighbors"][0]["name"] == "PostgreSQL"


async def test_get_entities(graph_repo):
    mid = uuid.uuid4()
    await graph_repo.create_entity("Alice", "person", {}, mid)
    await graph_repo.create_entity("Bob", "person", {}, mid)
    await graph_repo.create_entity("Redis", "technology", {}, mid)

    people = await graph_repo.get_entities(entity_type="person")
    assert len(people) == 2

    all_entities = await graph_repo.get_entities()
    assert len(all_entities) == 3


async def test_delete_by_memory_id(graph_repo):
    m1 = uuid.uuid4()
    m2 = uuid.uuid4()

    await graph_repo.create_entity("ServiceA", "service", {}, m1)
    await graph_repo.create_entity("ServiceB", "service", {}, m2)
    # ServiceA referenced by both memories
    await graph_repo.create_entity("SharedDB", "service", {}, m1)
    await graph_repo.create_entity("SharedDB", "service", {}, m2)

    await graph_repo.delete_by_memory_id(m1)

    entities = await graph_repo.get_entities()
    names = [e["name"] for e in entities]
    assert "ServiceA" not in names  # only referenced by m1
    assert "ServiceB" in names  # referenced by m2
    assert "SharedDB" in names  # still referenced by m2
```

- [ ] **Step 2: Implement `backend/app/repositories/graph.py`**

```python
from uuid import UUID, uuid4

from neo4j import AsyncDriver


class Neo4jGraphRepository:
    def __init__(self, driver: AsyncDriver):
        self.driver = driver

    async def create_entity(self, name: str, entity_type: str, properties: dict, memory_id: UUID) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MERGE (e:Entity {name: $name, entity_type: $entity_type})
                ON CREATE SET e.id = $id, e.properties = $properties, e.memory_ids = [$memory_id]
                ON MATCH SET e.properties = $properties,
                    e.memory_ids = CASE
                        WHEN NOT $memory_id IN e.memory_ids THEN e.memory_ids + $memory_id
                        ELSE e.memory_ids
                    END
                RETURN e{.id, .name, .entity_type, .properties, .memory_ids} as entity
                """,
                name=name, entity_type=entity_type, id=str(uuid4()),
                properties=properties, memory_id=str(memory_id),
            )
            record = await result.single()
            return record["entity"]

    async def create_relationship(self, source_name: str, target_name: str, rel_type: str, properties: dict, weight: float, memory_id: UUID):
        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (a:Entity {name: $source}), (b:Entity {name: $target})
                MERGE (a)-[r:RELATES_TO {rel_type: $rel_type}]->(b)
                ON CREATE SET r.properties = $properties, r.weight = $weight,
                    r.memory_ids = [$memory_id], r.created_at = datetime()
                ON MATCH SET r.weight = $weight,
                    r.memory_ids = CASE
                        WHEN NOT $memory_id IN r.memory_ids THEN r.memory_ids + $memory_id
                        ELSE r.memory_ids
                    END
                """,
                source=source_name, target=target_name, rel_type=rel_type,
                properties=properties, weight=weight, memory_id=str(memory_id),
            )

    async def get_entities(self, entity_type: str | None = None, name_query: str | None = None, limit: int = 50) -> list[dict]:
        query = "MATCH (e:Entity)"
        params: dict = {"limit": limit}
        conditions = []

        if entity_type:
            conditions.append("e.entity_type = $entity_type")
            params["entity_type"] = entity_type
        if name_query:
            conditions.append("e.name CONTAINS $name_query")
            params["name_query"] = name_query

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " RETURN e{.id, .name, .entity_type, .properties, .memory_ids} as entity LIMIT $limit"

        async with self.driver.session() as session:
            result = await session.run(query, **params)
            records = await result.data()
            return [r["entity"] for r in records]

    async def get_neighbors_by_name(self, name: str, depth: int = 1) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {name: $name})
                OPTIONAL MATCH (e)-[r]-(n:Entity)
                RETURN e{.id, .name, .entity_type, .properties} as entity,
                       collect(distinct n{.id, .name, .entity_type, .properties}) as neighbors,
                       collect(distinct {type: r.rel_type, weight: r.weight, source: startNode(r).name, target: endNode(r).name}) as relations
                """,
                name=name,
            )
            record = await result.single()
            if not record or not record["entity"]:
                return {"entity": None, "neighbors": [], "relations": []}
            return {
                "entity": record["entity"],
                "neighbors": record["neighbors"],
                "relations": record["relations"],
            }

    async def get_neighbors_by_id(self, entity_id: str, depth: int = 1) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {id: $id})
                OPTIONAL MATCH (e)-[r]-(n:Entity)
                RETURN e{.id, .name, .entity_type, .properties} as entity,
                       collect(distinct n{.id, .name, .entity_type, .properties}) as neighbors,
                       collect(distinct {type: r.rel_type, weight: r.weight, source: startNode(r).name, target: endNode(r).name}) as relations
                """,
                id=entity_id,
            )
            record = await result.single()
            if not record or not record["entity"]:
                return {"entity": None, "neighbors": [], "relations": []}
            return {
                "entity": record["entity"],
                "neighbors": record["neighbors"],
                "relations": record["relations"],
            }

    async def delete_by_memory_id(self, memory_id: UUID):
        mid = str(memory_id)
        async with self.driver.session() as session:
            # Remove memory_id from entities, delete orphans
            await session.run(
                """
                MATCH (e:Entity) WHERE $mid IN e.memory_ids
                SET e.memory_ids = [m IN e.memory_ids WHERE m <> $mid]
                """,
                mid=mid,
            )
            await session.run("MATCH (e:Entity) WHERE size(e.memory_ids) = 0 DETACH DELETE e")

            # Remove memory_id from relationships, delete orphans
            await session.run(
                """
                MATCH ()-[r:RELATES_TO]-() WHERE $mid IN r.memory_ids
                SET r.memory_ids = [m IN r.memory_ids WHERE m <> $mid]
                """,
                mid=mid,
            )
            await session.run("MATCH ()-[r:RELATES_TO]-() WHERE size(r.memory_ids) = 0 DELETE r")

    async def get_stats(self) -> dict:
        async with self.driver.session() as session:
            entity_result = await session.run("MATCH (e:Entity) RETURN count(e) as count")
            entity_count = (await entity_result.single())["count"]
            rel_result = await session.run("MATCH ()-[r:RELATES_TO]-() RETURN count(r) as count")
            rel_count = (await rel_result.single())["count"]
            return {"entity_count": entity_count, "relationship_count": rel_count}
```

- [ ] **Step 3: Run tests**

Run: `cd backend && pytest tests/test_graph_repo.py -v`
Expected: All 4 tests PASS (or skip if Neo4j not running).

- [ ] **Step 4: Commit**

```bash
git add backend/app/repositories/graph.py backend/tests/test_graph_repo.py
git commit -m "feat: add Neo4j graph repository"
```

---

### Task 4: Extraction Service

**Files:**
- Create: `backend/app/services/extraction.py`
- Create: `backend/tests/test_extraction.py`

- [ ] **Step 1: Write extraction tests — `backend/tests/test_extraction.py`**

```python
import json

import httpx

from app.config import LLMPurposeConfig
from app.services.extraction import ExtractionService
from app.services.llm import LLMOrchestrator


def _make_extraction_service(llm_response: dict):
    def handler(request: httpx.Request):
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps(llm_response)}}]
        })

    config = {
        "embedding": LLMPurposeConfig(base_url="http://mock", model="test"),
        "extraction": LLMPurposeConfig(base_url="http://mock", model="test"),
        "reasoning": LLMPurposeConfig(base_url="http://mock", model="test"),
        "summarization": LLMPurposeConfig(base_url="http://mock", model="test"),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return ExtractionService(llm)


async def test_extract_entities():
    svc = _make_extraction_service({
        "entities": [
            {"name": "PostgreSQL", "type": "technology", "properties": {"version": "17"}},
            {"name": "darkmem", "type": "project", "properties": {}},
        ],
        "relationships": [
            {"source": "darkmem", "target": "PostgreSQL", "type": "USES", "properties": {}, "weight": 0.9},
        ],
        "memory_type": "architecture",
        "importance": 0.8,
    })

    result = await svc.extract("darkmem uses PostgreSQL 17 for its relational storage")
    assert len(result["entities"]) == 2
    assert result["entities"][0]["name"] == "PostgreSQL"
    assert len(result["relationships"]) == 1
    assert result["memory_type"] == "architecture"
    assert result["importance"] == 0.8
    await svc.llm.close()


async def test_extract_handles_invalid_json():
    def handler(request: httpx.Request):
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "not valid json {{"}}]
        })

    config = {k: LLMPurposeConfig(base_url="http://mock", model="test") for k in ["embedding", "extraction", "reasoning", "summarization"]}
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    svc = ExtractionService(llm)

    result = await svc.extract("some text")
    assert result["entities"] == []
    assert result["relationships"] == []
    assert result["memory_type"] == "fact"
    await llm.close()
```

- [ ] **Step 2: Implement `backend/app/services/extraction.py`**

```python
import json
import logging

from app.services.llm import LLMOrchestrator

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM = """You are a knowledge extraction engine. Extract structured information from text.
Return ONLY valid JSON with no additional text."""

EXTRACTION_PROMPT = """Analyze this text and extract:
1. Named entities (people, services, projects, technologies, concepts)
2. Relationships between entities
3. Memory type classification
4. Importance score (0.0 to 1.0)

Return JSON in this exact format:
{
  "entities": [{"name": "string", "type": "person|service|project|technology|concept|organization", "properties": {}}],
  "relationships": [{"source": "entity_name", "target": "entity_name", "type": "USES|DEPENDS_ON|WORKS_ON|IS_A|HAS_PART|RELATED_TO", "properties": {}, "weight": 0.8}],
  "memory_type": "fact|decision|preference|debug|session|architecture|workflow",
  "importance": 0.7
}

Text:
"""


class ExtractionService:
    def __init__(self, llm: LLMOrchestrator):
        self.llm = llm

    async def extract(self, content: str) -> dict:
        try:
            response = await self.llm.chat_completion(
                "extraction",
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM},
                    {"role": "user", "content": EXTRACTION_PROMPT + content},
                ],
                response_format={"type": "json_object"},
            )
            return json.loads(response)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Extraction failed: {e}")
            return {"entities": [], "relationships": [], "memory_type": "fact", "importance": 0.5}
```

- [ ] **Step 3: Run tests**

Run: `cd backend && pytest tests/test_extraction.py -v`
Expected: All 2 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/extraction.py backend/tests/test_extraction.py
git commit -m "feat: add entity extraction service"
```

---

### Task 5: Processing Pipeline + Upgrade MemoryService

**Files:**
- Create: `backend/app/services/pipeline.py`
- Create: `backend/tests/test_pipeline.py`
- Modify: `backend/app/services/memory.py`
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write pipeline tests — `backend/tests/test_pipeline.py`**

```python
import json
import uuid
from unittest.mock import AsyncMock

import httpx
import pytest_asyncio

from app.config import LLMPurposeConfig
from app.repositories.vector import QdrantVectorRepository
from app.repositories.graph import Neo4jGraphRepository
from app.services.llm import LLMOrchestrator
from app.services.pipeline import ProcessingPipeline


def _make_mock_llm():
    """LLM that returns a fixed embedding and extraction."""
    call_count = {"embed": 0, "chat": 0}

    def handler(request: httpx.Request):
        url = str(request.url)
        if "embeddings" in url:
            call_count["embed"] += 1
            return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2, 0.3]}]})
        else:
            call_count["chat"] += 1
            return httpx.Response(200, json={
                "choices": [{"message": {"content": json.dumps({
                    "entities": [{"name": "TestEntity", "type": "concept", "properties": {}}],
                    "relationships": [],
                    "memory_type": "fact",
                    "importance": 0.7,
                })}}]
            })

    config = {k: LLMPurposeConfig(base_url="http://mock", model="test", dimensions=3)
              for k in ["embedding", "extraction", "reasoning", "summarization"]}
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return llm, call_count


async def test_pipeline_process_memory():
    llm, call_count = _make_mock_llm()
    vector_repo = AsyncMock(spec=QdrantVectorRepository)
    graph_repo = AsyncMock(spec=Neo4jGraphRepository)

    pipeline = ProcessingPipeline(llm, vector_repo, graph_repo)
    mid = uuid.uuid4()

    await pipeline.process_memory(
        memory_id=mid, content="Test content", source="test",
        tags=["tag-a"], memory_type=None, created_at="2026-01-01T00:00:00Z",
    )

    assert call_count["embed"] == 1
    assert call_count["chat"] == 1
    vector_repo.upsert.assert_called_once()
    graph_repo.create_entity.assert_called_once_with(
        name="TestEntity", entity_type="concept", properties={}, memory_id=mid,
    )
    await llm.close()


async def test_pipeline_delete_memory():
    llm, _ = _make_mock_llm()
    vector_repo = AsyncMock(spec=QdrantVectorRepository)
    graph_repo = AsyncMock(spec=Neo4jGraphRepository)

    pipeline = ProcessingPipeline(llm, vector_repo, graph_repo)
    mid = uuid.uuid4()

    await pipeline.delete_memory(mid)

    vector_repo.delete.assert_called_once_with(mid)
    graph_repo.delete_by_memory_id.assert_called_once_with(mid)
    await llm.close()
```

- [ ] **Step 2: Implement `backend/app/services/pipeline.py`**

```python
import asyncio
import logging
from uuid import UUID

from app.repositories.graph import Neo4jGraphRepository
from app.repositories.vector import QdrantVectorRepository
from app.services.extraction import ExtractionService
from app.services.llm import LLMOrchestrator

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    def __init__(self, llm: LLMOrchestrator, vector_repo: QdrantVectorRepository, graph_repo: Neo4jGraphRepository):
        self.llm = llm
        self.extraction = ExtractionService(llm)
        self.vector_repo = vector_repo
        self.graph_repo = graph_repo

    async def process_memory(self, memory_id: UUID, content: str, source: str, tags: list[str], memory_type: str | None, created_at: str):
        try:
            embed_task = self.llm.embed(content)
            extract_task = self.extraction.extract(content)
            results = await asyncio.gather(embed_task, extract_task, return_exceptions=True)
            vector, extraction = results[0], results[1]

            if not isinstance(vector, Exception):
                await self.vector_repo.upsert(
                    memory_id=memory_id, vector=vector,
                    payload={
                        "memory_id": str(memory_id), "content": content,
                        "source": source, "tags": tags,
                        "memory_type": memory_type or (extraction.get("memory_type") if isinstance(extraction, dict) else None),
                        "created_at": created_at,
                    },
                )
            else:
                logger.error(f"Embedding failed for {memory_id}: {vector}")

            if isinstance(extraction, dict):
                for entity in extraction.get("entities", []):
                    await self.graph_repo.create_entity(
                        name=entity["name"], entity_type=entity["type"],
                        properties=entity.get("properties", {}), memory_id=memory_id,
                    )
                for rel in extraction.get("relationships", []):
                    await self.graph_repo.create_relationship(
                        source_name=rel["source"], target_name=rel["target"],
                        rel_type=rel["type"], properties=rel.get("properties", {}),
                        weight=rel.get("weight", 0.5), memory_id=memory_id,
                    )
            else:
                logger.error(f"Extraction failed for {memory_id}: {extraction}")
        except Exception as e:
            logger.error(f"Pipeline failed for {memory_id}: {e}")

    async def delete_memory(self, memory_id: UUID):
        try:
            await asyncio.gather(
                self.vector_repo.delete(memory_id),
                self.graph_repo.delete_by_memory_id(memory_id),
                return_exceptions=True,
            )
        except Exception as e:
            logger.error(f"Cleanup failed for {memory_id}: {e}")

    async def semantic_search(self, query: str, limit: int = 20) -> list[dict]:
        try:
            vector = await self.llm.embed(query)
            return await self.vector_repo.search(vector, limit=limit)
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    async def find_duplicates(self, memory_id: UUID, threshold: float = 0.9) -> list[dict]:
        try:
            return await self.vector_repo.find_similar(memory_id, threshold=threshold)
        except Exception as e:
            logger.error(f"Duplicate search failed: {e}")
            return []
```

- [ ] **Step 3: Upgrade `backend/app/services/memory.py`**

Replace the entire file:

```python
import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.repositories.relational import PostgresAuditRepository, PostgresMemoryRepository
from app.schemas.memory import MemoryCreate, MemorySearchRequest, MemoryUpdate
from app.services.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, session: AsyncSession, pipeline: ProcessingPipeline | None = None):
        self.memory_repo = PostgresMemoryRepository(session)
        self.audit_repo = PostgresAuditRepository(session)
        self.session = session
        self.pipeline = pipeline

    async def create_memory(self, data: MemoryCreate, api_key_id: UUID | None) -> Memory:
        memory = await self.memory_repo.create(
            content=data.content, source=data.source, source_agent=data.source_agent,
            memory_type=data.memory_type, importance=data.importance,
            metadata=data.metadata, expires_at=data.expires_at,
        )
        if data.tags:
            await self.memory_repo.set_tags(memory.id, data.tags)
            await self.session.refresh(memory, ["tags"])

        await self.audit_repo.log("create", memory.id, api_key_id, {"source": data.source})

        # Trigger async processing (non-blocking)
        if self.pipeline:
            asyncio.create_task(self.pipeline.process_memory(
                memory_id=memory.id, content=memory.content, source=memory.source,
                tags=[t.name for t in memory.tags], memory_type=memory.memory_type,
                created_at=memory.created_at.isoformat(),
            ))

        return memory

    async def get_memory(self, memory_id: UUID) -> Memory | None:
        return await self.memory_repo.get(memory_id)

    async def update_memory(self, memory_id: UUID, data: MemoryUpdate, api_key_id: UUID | None) -> Memory | None:
        update_fields = data.model_dump(exclude_unset=True, exclude={"tags"})
        memory = await self.memory_repo.update(memory_id, **update_fields)
        if not memory:
            return None

        if data.tags is not None:
            await self.memory_repo.set_tags(memory_id, data.tags)
            await self.session.refresh(memory, ["tags"])

        await self.audit_repo.log("update", memory_id, api_key_id, {"fields": list(update_fields.keys())})

        # Re-process if content changed
        if self.pipeline and "content" in update_fields:
            asyncio.create_task(self.pipeline.process_memory(
                memory_id=memory.id, content=memory.content, source=memory.source,
                tags=[t.name for t in memory.tags], memory_type=memory.memory_type,
                created_at=memory.created_at.isoformat(),
            ))

        return memory

    async def delete_memory(self, memory_id: UUID, api_key_id: UUID | None) -> bool:
        result = await self.memory_repo.delete(memory_id)
        if result:
            await self.audit_repo.log("delete", memory_id, api_key_id, {})
            if self.pipeline:
                asyncio.create_task(self.pipeline.delete_memory(memory_id))
        return result

    async def search_memories(self, params: MemorySearchRequest) -> list[Memory]:
        # If we have a query and pipeline, try semantic search first
        if params.query and self.pipeline:
            semantic_results = await self.pipeline.semantic_search(params.query, limit=params.limit)
            if semantic_results:
                memory_ids = [r["memory_id"] for r in semantic_results]
                memories = []
                for mid in memory_ids:
                    m = await self.memory_repo.get(mid)
                    if m and not m.is_archived:
                        # Apply additional filters
                        if params.memory_type and m.memory_type != params.memory_type:
                            continue
                        if params.source and m.source != params.source:
                            continue
                        if params.tags_any:
                            tag_names = [t.name for t in m.tags]
                            if not any(t in tag_names for t in params.tags_any):
                                continue
                        memories.append(m)
                return memories[:params.limit]

        # Fallback: Postgres text/tag search
        return await self.memory_repo.search_by_tags(
            query=params.query, tags_any=params.tags_any, tags_all=params.tags_all,
            memory_type=params.memory_type, source=params.source, limit=params.limit,
        )

    async def list_memories(self, offset: int = 0, limit: int = 50) -> tuple[list[Memory], int]:
        return await self.memory_repo.list_memories(offset=offset, limit=limit)

    async def find_duplicates(self, memory_id: UUID, threshold: float = 0.9) -> list[dict]:
        if not self.pipeline:
            return []
        return await self.pipeline.find_duplicates(memory_id, threshold)

    async def merge_memories(self, source_id: UUID, target_id: UUID, api_key_id: UUID | None) -> Memory | None:
        source = await self.memory_repo.get(source_id)
        target = await self.memory_repo.get(target_id)
        if not source or not target:
            return None

        merged_content = f"{target.content}\n\n---\n\n{source.content}"
        merged_tags = list({t.name for t in target.tags} | {t.name for t in source.tags})

        await self.memory_repo.update(target_id, content=merged_content)
        await self.memory_repo.set_tags(target_id, merged_tags)
        await self.memory_repo.delete(source_id)

        if self.pipeline:
            asyncio.create_task(self.pipeline.delete_memory(source_id))
            asyncio.create_task(self.pipeline.process_memory(
                memory_id=target_id, content=merged_content, source=target.source,
                tags=merged_tags, memory_type=target.memory_type,
                created_at=target.created_at.isoformat(),
            ))

        await self.audit_repo.log("merge", target_id, api_key_id, {"source_id": str(source_id)})
        await self.session.refresh(target, ["tags"])
        return await self.memory_repo.get(target_id)
```

- [ ] **Step 4: Update `backend/app/api/deps.py`**

Replace the entire file:

```python
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.repositories.relational import PostgresApiKeyRepository, PostgresTagRepository
from app.services.memory import MemoryService


async def get_memory_service(request: Request, session: AsyncSession = Depends(get_session)) -> MemoryService:
    pipeline = getattr(request.app.state, "pipeline", None)
    return MemoryService(session, pipeline=pipeline)


async def get_tag_repository(session: AsyncSession = Depends(get_session)) -> PostgresTagRepository:
    return PostgresTagRepository(session)


async def get_api_key_repository(session: AsyncSession = Depends(get_session)) -> PostgresApiKeyRepository:
    return PostgresApiKeyRepository(session)
```

- [ ] **Step 5: Update `backend/app/main.py`**

Replace the entire file:

```python
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from neo4j import AsyncGraphDatabase
from qdrant_client import AsyncQdrantClient

from app.api.routes import keys, memories, tags
from app.config import settings
from app.repositories.graph import Neo4jGraphRepository
from app.repositories.vector import QdrantVectorRepository
from app.services.llm import LLMOrchestrator
from app.services.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize optional services
    pipeline = None
    qdrant_client = None
    neo4j_driver = None
    llm = None

    try:
        qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)
        await qdrant_client.get_collections()

        neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password),
        )
        await neo4j_driver.verify_connectivity()

        llm_config = {
            "embedding": settings.llm_embedding,
            "extraction": settings.llm_extraction,
            "reasoning": settings.llm_reasoning,
            "summarization": settings.llm_summarization,
        }
        llm = LLMOrchestrator(llm_config)

        vector_repo = QdrantVectorRepository(qdrant_client, dimensions=settings.llm_embedding.dimensions or 768)
        await vector_repo.ensure_collection()
        graph_repo = Neo4jGraphRepository(neo4j_driver)

        pipeline = ProcessingPipeline(llm, vector_repo, graph_repo)
        app.state.pipeline = pipeline
        app.state.graph_repo = graph_repo
        app.state.vector_repo = vector_repo
        logger.info("Pipeline initialized: Qdrant + Neo4j + LLM connected")
    except Exception as e:
        logger.warning(f"Pipeline not available (Postgres-only mode): {e}")
        app.state.pipeline = None
        app.state.graph_repo = None
        app.state.vector_repo = None

    yield

    # Cleanup
    if llm:
        await llm.close()
    if neo4j_driver:
        await neo4j_driver.close()
    if qdrant_client:
        await qdrant_client.close()


app = FastAPI(title="darkmem", version="0.2.0", description="Centralized memory system for AI agents", lifespan=lifespan)

app.include_router(memories.router)
app.include_router(tags.router)
app.include_router(keys.router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "pipeline": hasattr(app.state, "pipeline") and app.state.pipeline is not None,
    }
```

- [ ] **Step 6: Run all tests**

Run: `cd backend && pytest -v`
Expected: All existing tests still PASS (pipeline is None in test environment, graceful degradation). New pipeline tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/pipeline.py backend/app/services/memory.py backend/app/api/deps.py backend/app/main.py backend/tests/test_pipeline.py
git commit -m "feat: add processing pipeline with hybrid search and cascade ops"
```

---

### Task 6: Graph + Config + Analytics API Routes

**Files:**
- Create: `backend/app/schemas/graph.py`
- Create: `backend/app/schemas/config.py`
- Create: `backend/app/api/routes/graph.py`
- Create: `backend/app/api/routes/analytics.py`
- Create: `backend/app/api/routes/config.py`
- Modify: `backend/app/api/routes/memories.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_api/test_graph.py`
- Create: `backend/tests/test_api/test_analytics.py`

- [ ] **Step 1: Create schemas**

`backend/app/schemas/graph.py`:
```python
from pydantic import BaseModel


class EntityResponse(BaseModel):
    id: str | None
    name: str
    entity_type: str
    properties: dict = {}
    memory_ids: list[str] = []


class RelationResponse(BaseModel):
    type: str | None
    weight: float | None
    source: str | None
    target: str | None


class NeighborsResponse(BaseModel):
    entity: EntityResponse | None
    neighbors: list[EntityResponse]
    relations: list[RelationResponse]
```

`backend/app/schemas/config.py`:
```python
from pydantic import BaseModel, Field


class LLMPurposeConfigSchema(BaseModel):
    provider: str
    base_url: str
    model: str
    api_key: str | None = None
    dimensions: int | None = None
    params: dict = Field(default_factory=dict)


class LLMConfigResponse(BaseModel):
    embedding: LLMPurposeConfigSchema
    extraction: LLMPurposeConfigSchema
    reasoning: LLMPurposeConfigSchema
    summarization: LLMPurposeConfigSchema


class StatsResponse(BaseModel):
    memories: int
    tags: int
    entities: int | None = None
    relationships: int | None = None
    sources: list[str] = []
```

- [ ] **Step 2: Create `backend/app/api/routes/graph.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.auth import require_scope
from app.repositories.graph import Neo4jGraphRepository
from app.schemas.graph import EntityResponse, NeighborsResponse

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


def _get_graph_repo(request: Request) -> Neo4jGraphRepository:
    repo = getattr(request.app.state, "graph_repo", None)
    if not repo:
        raise HTTPException(status_code=503, detail="Graph service not available")
    return repo


@router.get("/entities", response_model=list[EntityResponse])
async def list_entities(
    entity_type: str | None = Query(None),
    name: str | None = Query(None),
    limit: int = Query(50),
    _api_key=Depends(require_scope("read")),
    request: Request = None,
):
    repo = _get_graph_repo(request)
    entities = await repo.get_entities(entity_type=entity_type, name_query=name, limit=limit)
    return [EntityResponse(**e) for e in entities]


@router.get("/entities/{entity_id}/neighbors", response_model=NeighborsResponse)
async def get_neighbors(
    entity_id: str,
    depth: int = Query(1, ge=1, le=3),
    _api_key=Depends(require_scope("read")),
    request: Request = None,
):
    repo = _get_graph_repo(request)
    result = await repo.get_neighbors_by_id(entity_id, depth=depth)
    if not result["entity"]:
        raise HTTPException(status_code=404, detail="Entity not found")
    return NeighborsResponse(
        entity=EntityResponse(**result["entity"]) if result["entity"] else None,
        neighbors=[EntityResponse(**n) for n in result["neighbors"]],
        relations=result["relations"],
    )
```

- [ ] **Step 3: Create `backend/app/api/routes/analytics.py`**

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_scope
from app.database import get_session
from app.models.memory import Memory, Tag
from app.schemas.config import StatsResponse

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    _api_key=Depends(require_scope("read")),
    session: AsyncSession = Depends(get_session),
    request: Request = None,
):
    memory_count = (await session.execute(select(func.count()).select_from(Memory))).scalar()
    tag_count = (await session.execute(select(func.count()).select_from(Tag))).scalar()
    sources_result = await session.execute(select(Memory.source).distinct())
    sources = [r[0] for r in sources_result.all()]

    entity_count = None
    rel_count = None
    graph_repo = getattr(request.app.state, "graph_repo", None) if request else None
    if graph_repo:
        try:
            stats = await graph_repo.get_stats()
            entity_count = stats["entity_count"]
            rel_count = stats["relationship_count"]
        except Exception:
            pass

    return StatsResponse(
        memories=memory_count, tags=tag_count,
        entities=entity_count, relationships=rel_count, sources=sources,
    )
```

- [ ] **Step 4: Create `backend/app/api/routes/config.py`**

```python
from fastapi import APIRouter, Depends

from app.api.auth import require_scope
from app.config import settings
from app.schemas.config import LLMConfigResponse, LLMPurposeConfigSchema

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config(_api_key=Depends(require_scope("admin"))):
    def _to_schema(cfg):
        return LLMPurposeConfigSchema(
            provider=cfg.provider, base_url=cfg.base_url, model=cfg.model,
            api_key="***" if cfg.api_key else None,
            dimensions=cfg.dimensions, params=cfg.params,
        )
    return LLMConfigResponse(
        embedding=_to_schema(settings.llm_embedding),
        extraction=_to_schema(settings.llm_extraction),
        reasoning=_to_schema(settings.llm_reasoning),
        summarization=_to_schema(settings.llm_summarization),
    )
```

- [ ] **Step 5: Add merge + duplicates endpoints to `backend/app/api/routes/memories.py`**

Add these routes at the end of the file (before the closing):

```python
@router.post("/{memory_id}/merge", response_model=MemoryResponse)
async def merge_memory(
    memory_id: UUID,
    body: MemoryMergeRequest,
    api_key: ApiKey = Depends(require_scope("write")),
    service: MemoryService = Depends(get_memory_service),
):
    memory = await service.merge_memories(memory_id, body.target_id, api_key.id)
    if not memory:
        raise HTTPException(status_code=404, detail="One or both memories not found")
    return _to_response(memory)


@router.get("/{memory_id}/duplicates")
async def find_duplicates(
    memory_id: UUID,
    threshold: float = 0.9,
    api_key: ApiKey = Depends(require_scope("read")),
    service: MemoryService = Depends(get_memory_service),
):
    duplicates = await service.find_duplicates(memory_id, threshold)
    return duplicates
```

Also add the missing import at the top: `MemoryMergeRequest` — it should already be imported from schemas.

- [ ] **Step 6: Wire new routes in `backend/app/main.py`**

Add the imports and router includes:

```python
from app.api.routes import analytics, config, graph, keys, memories, tags
```

And add:
```python
app.include_router(graph.router)
app.include_router(analytics.router)
app.include_router(config.router)
```

- [ ] **Step 7: Write API tests**

`backend/tests/test_api/test_analytics.py`:
```python
async def test_get_stats(client, auth_headers):
    response = await client.get("/api/v1/analytics/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "memories" in data
    assert "tags" in data
    assert isinstance(data["sources"], list)


async def test_get_stats_after_creating_memories(client, auth_headers):
    await client.post("/api/v1/memories", json={"content": "Test", "source": "pytest"}, headers=auth_headers)
    response = await client.get("/api/v1/analytics/stats", headers=auth_headers)
    data = response.json()
    assert data["memories"] >= 1
    assert "pytest" in data["sources"]
```

`backend/tests/test_api/test_graph.py`:
```python
async def test_graph_entities_503_when_unavailable(client, auth_headers):
    response = await client.get("/api/v1/graph/entities", headers=auth_headers)
    # Graph repo is None in test env (no Neo4j), so 503
    assert response.status_code == 503
```

- [ ] **Step 8: Run all tests**

Run: `cd backend && pytest -v`
Expected: All tests PASS (existing 36 + new LLM 4 + vector 3 + graph 4 + extraction 2 + pipeline 2 + API analytics 2 + API graph 1 = ~54 total, some may skip if services unavailable).

- [ ] **Step 9: Commit**

```bash
git add backend/app/schemas/graph.py backend/app/schemas/config.py backend/app/api/routes/graph.py backend/app/api/routes/analytics.py backend/app/api/routes/config.py backend/app/api/routes/memories.py backend/app/main.py backend/tests/test_api/test_graph.py backend/tests/test_api/test_analytics.py
git commit -m "feat: add graph, analytics, config API routes and merge/duplicates"
```

---

## Limitations of Plan 2

The following are deferred to Plans 3 and 4:

- **MCP server** — StreamableHTTP interface (Plan 3)
- **WebSocket** — live event push (Plan 3)
- **System prompt profiles** — CRUD and seed data (Plan 3)
- **Reason endpoint** — RAG over memory store (Plan 3, needs prompt engineering)
- **Frontend dashboard** — React SPA (Plan 4)
- **Production Docker Compose** — pull-based images (Plan 4)
- **Build scripts** — build-push.sh for Docker Hub (Plan 4)
- **LLM config persistence** — currently reads from env/settings, not Postgres config table (Plan 3)

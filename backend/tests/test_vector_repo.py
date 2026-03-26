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

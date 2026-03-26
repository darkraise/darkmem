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

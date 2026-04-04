import json
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
                properties=json.dumps(properties), memory_id=str(memory_id),
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
                properties=json.dumps(properties), weight=weight, memory_id=str(memory_id),
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

    async def get_neighbors_by_name(self, name: str) -> dict:
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

    async def get_neighbors_by_id(self, entity_id: str) -> dict:
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

    async def get_full_graph(self, limit: int = 200) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity)
                WITH e LIMIT $limit
                OPTIONAL MATCH (e)-[r:RELATES_TO]->(t:Entity)
                RETURN collect(distinct e{.id, .name, .entity_type, .properties, .memory_ids}) as entities,
                       collect(distinct {source: startNode(r).id, target: endNode(r).id, type: r.rel_type, weight: r.weight}) as relations
                """,
                limit=limit,
            )
            record = await result.single()
            entities = record["entities"] if record else []
            relations = [r for r in (record["relations"] if record else []) if r.get("source") and r.get("target")]
            return {"entities": entities, "relations": relations}

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

    async def get_entities_by_memory_id(self, memory_id: str) -> list[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity) WHERE $mid IN e.memory_ids
                RETURN e{.id, .name, .entity_type, .properties, .memory_ids} as entity
                """,
                mid=memory_id,
            )
            records = await result.data()
            return [r["entity"] for r in records]

    async def get_relations_between(self, entity_names: list[str]) -> list[dict]:
        if not entity_names:
            return []
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity)
                WHERE a.name IN $names AND b.name IN $names
                RETURN {source: a.name, target: b.name, type: r.rel_type, weight: r.weight} as relation
                """,
                names=entity_names,
            )
            records = await result.data()
            return [r["relation"] for r in records]

    async def get_stats(self) -> dict:
        async with self.driver.session() as session:
            entity_result = await session.run("MATCH (e:Entity) RETURN count(e) as count")
            entity_count = (await entity_result.single())["count"]
            rel_result = await session.run("MATCH ()-[r:RELATES_TO]-() RETURN count(r) as count")
            rel_count = (await rel_result.single())["count"]
            return {"entity_count": entity_count, "relationship_count": rel_count}

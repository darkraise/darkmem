import logging
from app.repositories.graph import Neo4jGraphRepository

logger = logging.getLogger(__name__)


class HeritageResolver:
    def __init__(self, graph_repo: Neo4jGraphRepository, repo_id: str):
        self.graph_repo = graph_repo
        self.repo_id = repo_id

    async def resolve_all(self) -> dict:
        overrides = await self._find_overrides()
        implements = await self._find_implements()
        return {"overrides": overrides, "implements": implements}

    async def _find_overrides(self) -> int:
        """Find methods that override parent class methods via EXTENDS chain."""
        async with self.graph_repo.driver.session() as neo:
            result = await neo.run(
                """
                MATCH (child:CodeSymbol {repo_id: $repo_id})-[:EXTENDS]->(parent:CodeSymbol {repo_id: $repo_id})
                MATCH (child)-[:HAS_METHOD]->(cm:CodeSymbol {repo_id: $repo_id})
                MATCH (parent)-[:HAS_METHOD]->(pm:CodeSymbol {repo_id: $repo_id})
                WHERE cm.name = pm.name AND cm <> pm
                MERGE (child)-[:METHOD_OVERRIDES {method: cm.name}]->(pm)
                RETURN count(*) AS count
                """,
                repo_id=self.repo_id,
            )
            record = await result.single()
            count = record["count"] if record else 0
            logger.info("Created %d METHOD_OVERRIDES edges for repo %s", count, self.repo_id)
            return count

    async def _find_implements(self) -> int:
        """Find methods that implement interface methods via IMPLEMENTS chain."""
        async with self.graph_repo.driver.session() as neo:
            result = await neo.run(
                """
                MATCH (child:CodeSymbol {repo_id: $repo_id})-[:IMPLEMENTS]->(iface:CodeSymbol {repo_id: $repo_id})
                MATCH (child)-[:HAS_METHOD]->(cm:CodeSymbol {repo_id: $repo_id})
                MATCH (iface)-[:HAS_METHOD]->(im:CodeSymbol {repo_id: $repo_id})
                WHERE cm.name = im.name AND cm <> im
                MERGE (cm)-[:METHOD_IMPLEMENTS]->(im)
                RETURN count(*) AS count
                """,
                repo_id=self.repo_id,
            )
            record = await result.single()
            count = record["count"] if record else 0
            logger.info("Created %d METHOD_IMPLEMENTS edges for repo %s", count, self.repo_id)
            return count


class AccessResolver:
    """Creates ACCESSES edges for field/property access patterns using type resolution."""

    def __init__(self, graph_repo: Neo4jGraphRepository, repo_id: str):
        self.graph_repo = graph_repo
        self.repo_id = repo_id

    async def resolve(self, type_envs: dict, call_data: dict) -> int:
        """
        For member calls like obj.field, if obj's type resolves to a class
        and field is a Property (not a method), create an ACCESSES edge.

        type_envs: file_path -> TypeEnvironment
        call_data: file_path -> list of ExtractedCall with call_form="member"
        """
        count = 0
        async with self.graph_repo.driver.session() as neo:
            edges = []
            for file_path, calls in call_data.items():
                env = type_envs.get(file_path)
                if not env:
                    continue

                for call in calls:
                    if call.call_form != "member" or not call.receiver_name:
                        continue

                    receiver_type = env.resolve(call.receiver_name)
                    if not receiver_type:
                        continue

                    edges.append({
                        "caller_file": file_path,
                        "caller_line": call.line,
                        "receiver_type": receiver_type,
                        "field_name": call.called_name,
                    })

            if edges:
                result = await neo.run(
                    """
                    UNWIND $edges AS edge
                    MATCH (cls:CodeSymbol {repo_id: $repo_id, name: edge.receiver_type})-[:HAS_PROPERTY]->(prop:Property {repo_id: $repo_id, name: edge.field_name})
                    MATCH (caller:CodeSymbol {repo_id: $repo_id, file_path: edge.caller_file})
                    WHERE caller.line_start <= edge.caller_line AND caller.line_end >= edge.caller_line
                    AND caller.kind IN ['function', 'method']
                    MERGE (caller)-[:ACCESSES]->(prop)
                    RETURN count(*) AS count
                    """,
                    repo_id=self.repo_id, edges=edges,
                )
                record = await result.single()
                count = record["count"] if record else 0

            logger.info("Created %d ACCESSES edges for repo %s", count, self.repo_id)
            return count

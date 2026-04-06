import logging
from app.repositories.graph import Neo4jGraphRepository

logger = logging.getLogger(__name__)


class ProcessTracer:
    def __init__(self, graph_repo: Neo4jGraphRepository, repo_id: str):
        self.graph_repo = graph_repo
        self.repo_id = repo_id

    async def trace(self, max_depth: int = 15) -> int:
        async with self.graph_repo.driver.session() as neo:
            await neo.run(
                "MATCH (p:Process {repo_id: $repo_id}) DETACH DELETE p",
                repo_id=self.repo_id,
            )

            entry_result = await neo.run(
                """
                MATCH (f:CodeFile {repo_id: $repo_id})-[:HANDLES_ROUTE]->(r:Route {repo_id: $repo_id})
                RETURN 'route' AS kind, COALESCE(r.method, '') + ' ' + r.path AS name, f.file_path AS file_path
                UNION
                MATCH (f:CodeFile {repo_id: $repo_id})-[:HANDLES_TOOL]->(t:Tool {repo_id: $repo_id})
                RETURN 'tool' AS kind, t.name AS name, f.file_path AS file_path
                """,
                repo_id=self.repo_id,
            )
            entries = [r async for r in entry_result]

        if not entries:
            return 0

        process_count = 0
        async with self.graph_repo.driver.session() as neo:
            for entry in entries:
                name = entry["name"].strip()
                kind = entry["kind"]
                file_path = entry["file_path"]

                trace_result = await neo.run(
                    """
                    MATCH (start:CodeSymbol {repo_id: $repo_id, file_path: $file_path})
                    WHERE start.kind IN ['function', 'method']
                    MATCH path = (start)-[:CALLS*0..""" + str(max_depth) + """]->(step:CodeSymbol {repo_id: $repo_id})
                    RETURN DISTINCT step.name + '::' + step.file_path AS step_id, length(path) AS depth
                    ORDER BY depth
                    LIMIT 100
                    """,
                    repo_id=self.repo_id, file_path=file_path,
                )
                steps = []
                async for record in trace_result:
                    steps.append({"id": record["step_id"], "depth": record["depth"]})

                if not steps:
                    continue

                proc_name = f"{kind}:{name}"
                await neo.run(
                    """
                    CREATE (p:Process {repo_id: $repo_id, name: $name, entry_kind: $kind, entry_file: $file_path})
                    """,
                    repo_id=self.repo_id, name=proc_name, kind=kind, file_path=file_path,
                )

                if kind == "route":
                    parts = name.split(" ", 1)
                    method = parts[0] if len(parts) > 1 else None
                    path = parts[1] if len(parts) > 1 else parts[0]
                    await neo.run(
                        """
                        MATCH (r:Route {repo_id: $repo_id, path: $path})
                        MATCH (p:Process {repo_id: $repo_id, name: $proc_name})
                        MERGE (r)-[:ENTRY_POINT_OF]->(p)
                        """,
                        repo_id=self.repo_id, path=path, proc_name=proc_name,
                    )
                elif kind == "tool":
                    await neo.run(
                        """
                        MATCH (t:Tool {repo_id: $repo_id, name: $tool_name})
                        MATCH (p:Process {repo_id: $repo_id, name: $proc_name})
                        MERGE (t)-[:ENTRY_POINT_OF]->(p)
                        """,
                        repo_id=self.repo_id, tool_name=name, proc_name=proc_name,
                    )

                if steps:
                    step_data = [{"id": s["id"], "step": i + 1} for i, s in enumerate(steps)]
                    await neo.run(
                        """
                        UNWIND $steps AS s
                        MATCH (sym:CodeSymbol {repo_id: $repo_id})
                        WHERE sym.name + '::' + sym.file_path = s.id
                        MATCH (p:Process {repo_id: $repo_id, name: $proc_name})
                        MERGE (sym)-[:STEP_IN_PROCESS {step: s.step}]->(p)
                        """,
                        repo_id=self.repo_id, proc_name=proc_name, steps=step_data,
                    )

                process_count += 1

        logger.info("Traced %d processes for repo %s", process_count, self.repo_id)
        return process_count

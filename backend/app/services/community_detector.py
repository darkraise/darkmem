import logging
from collections import Counter

from app.repositories.graph import Neo4jGraphRepository

logger = logging.getLogger(__name__)


class CommunityDetector:
    def __init__(self, graph_repo: Neo4jGraphRepository, repo_id: str):
        self.graph_repo = graph_repo
        self.repo_id = repo_id

    async def detect(self) -> int:
        try:
            import igraph
            import leidenalg
        except ImportError:
            logger.warning("igraph or leidenalg not installed, skipping community detection")
            return 0

        async with self.graph_repo.driver.session() as neo:
            nodes_result = await neo.run(
                "MATCH (s:CodeSymbol {repo_id: $repo_id}) WHERE s.kind IN ['function', 'method', 'class', 'interface', 'struct', 'trait'] RETURN s.name + '::' + s.file_path AS id, s.file_path AS file_path",
                repo_id=self.repo_id,
            )
            node_list = []
            node_ids = {}
            async for record in nodes_result:
                idx = len(node_list)
                node_list.append({"id": record["id"], "file_path": record["file_path"]})
                node_ids[record["id"]] = idx

            if len(node_list) < 3:
                return 0

            edges_result = await neo.run(
                """
                MATCH (s1:CodeSymbol {repo_id: $repo_id})-[r:CALLS|EXTENDS|IMPLEMENTS]->(s2:CodeSymbol {repo_id: $repo_id})
                WHERE s1.kind IN ['function', 'method', 'class', 'interface', 'struct', 'trait']
                AND s2.kind IN ['function', 'method', 'class', 'interface', 'struct', 'trait']
                RETURN s1.name + '::' + s1.file_path AS source, s2.name + '::' + s2.file_path AS target
                """,
                repo_id=self.repo_id,
            )
            edge_list = []
            async for record in edges_result:
                src = node_ids.get(record["source"])
                tgt = node_ids.get(record["target"])
                if src is not None and tgt is not None:
                    edge_list.append((src, tgt))

        if not edge_list:
            return 0

        g = igraph.Graph(n=len(node_list), edges=edge_list, directed=False)
        partition = leidenalg.find_partition(g, leidenalg.ModularityVertexPartition)

        communities: dict[int, list[int]] = {}
        for node_idx, comm_id in enumerate(partition.membership):
            communities.setdefault(comm_id, []).append(node_idx)

        comm_labels = {}
        for comm_id, members in communities.items():
            dirs = []
            for idx in members:
                fp = node_list[idx]["file_path"]
                if fp:
                    parts = fp.replace("\\", "/").split("/")
                    if len(parts) > 1:
                        dirs.append(parts[-2] if len(parts) > 1 else parts[0])
                    else:
                        dirs.append(parts[0])
            if dirs:
                most_common = Counter(dirs).most_common(1)[0][0]
                comm_labels[comm_id] = most_common
            else:
                comm_labels[comm_id] = f"community_{comm_id}"

        async with self.graph_repo.driver.session() as neo:
            await neo.run(
                "MATCH (c:Community {repo_id: $repo_id}) DETACH DELETE c",
                repo_id=self.repo_id,
            )

            for comm_id, members in communities.items():
                if len(members) < 2:
                    continue
                label = comm_labels.get(comm_id, f"community_{comm_id}")
                await neo.run(
                    """
                    CREATE (c:Community {repo_id: $repo_id, community_id: $comm_id, label: $label, size: $size})
                    """,
                    repo_id=self.repo_id, comm_id=comm_id, label=label, size=len(members),
                )

                member_ids = [node_list[idx]["id"] for idx in members]
                await neo.run(
                    """
                    UNWIND $member_ids AS mid
                    MATCH (s:CodeSymbol {repo_id: $repo_id})
                    WHERE s.name + '::' + s.file_path = mid
                    MATCH (c:Community {repo_id: $repo_id, community_id: $comm_id})
                    MERGE (s)-[:MEMBER_OF]->(c)
                    """,
                    repo_id=self.repo_id, comm_id=comm_id, member_ids=member_ids,
                )

        total = sum(len(m) for m in communities.values() if len(m) >= 2)
        logger.info("Detected %d communities with %d members for repo %s", len(communities), total, self.repo_id)
        return total

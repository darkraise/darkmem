from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.graph_keys import compose_key

logger = logging.getLogger(__name__)

_LARGE_GRAPH_THRESHOLD = 10_000


class CommunityDetector:
    def __init__(self, session: AsyncSession, repo_id: str):
        self.session = session
        self.repo_id = repo_id

    async def detect(self) -> int:
        try:
            import igraph
            import leidenalg
        except ImportError:
            logger.warning("igraph or leidenalg not installed, skipping community detection")
            return 0

        nodes_result = await self.session.execute(
            text("""
                SELECT key, properties->>'file_path' AS file_path
                FROM code_graph_nodes
                WHERE repo_id = :repo_id
                  AND kind = 'symbol'
                  AND properties->>'kind' IN ('function', 'method', 'class', 'interface', 'struct', 'trait')
            """),
            {"repo_id": self.repo_id},
        )
        node_list = []
        node_ids: dict[str, int] = {}
        for row in nodes_result.mappings():
            idx = len(node_list)
            node_list.append({"id": row["key"], "file_path": row["file_path"]})
            node_ids[row["key"]] = idx

        if len(node_list) < 3:
            return 0

        is_large = len(node_list) > _LARGE_GRAPH_THRESHOLD

        if is_large:
            edges_result = await self.session.execute(
                text("""
                    SELECT e.source_key, e.target_key
                    FROM code_edges e
                    JOIN code_graph_nodes src ON src.repo_id = e.repo_id AND src.key = e.source_key
                    JOIN code_graph_nodes tgt ON tgt.repo_id = e.repo_id AND tgt.key = e.target_key
                    WHERE e.repo_id = :repo_id
                      AND e.edge_type IN ('calls', 'extends', 'implements')
                      AND (e.properties->>'confidence')::float >= 0.5
                      AND src.kind = 'symbol'
                      AND src.properties->>'kind' IN ('function', 'method', 'class', 'interface', 'struct', 'trait')
                      AND tgt.kind = 'symbol'
                      AND tgt.properties->>'kind' IN ('function', 'method', 'class', 'interface', 'struct', 'trait')
                """),
                {"repo_id": self.repo_id},
            )
        else:
            edges_result = await self.session.execute(
                text("""
                    SELECT e.source_key, e.target_key
                    FROM code_edges e
                    JOIN code_graph_nodes src ON src.repo_id = e.repo_id AND src.key = e.source_key
                    JOIN code_graph_nodes tgt ON tgt.repo_id = e.repo_id AND tgt.key = e.target_key
                    WHERE e.repo_id = :repo_id
                      AND e.edge_type IN ('calls', 'extends', 'implements')
                      AND src.kind = 'symbol'
                      AND src.properties->>'kind' IN ('function', 'method', 'class', 'interface', 'struct', 'trait')
                      AND tgt.kind = 'symbol'
                      AND tgt.properties->>'kind' IN ('function', 'method', 'class', 'interface', 'struct', 'trait')
                """),
                {"repo_id": self.repo_id},
            )

        edge_list = []
        node_degree: dict[int, int] = {}
        for row in edges_result.mappings():
            src = node_ids.get(row["source_key"])
            tgt = node_ids.get(row["target_key"])
            if src is not None and tgt is not None:
                edge_list.append((src, tgt))
                node_degree[src] = node_degree.get(src, 0) + 1
                node_degree[tgt] = node_degree.get(tgt, 0) + 1

        if not edge_list:
            return 0

        if is_large:
            active_nodes = {idx for idx, deg in node_degree.items() if deg >= 1}
            filtered_edges = [(s, t) for s, t in edge_list if s in active_nodes and t in active_nodes]
            if not filtered_edges:
                filtered_edges = edge_list
            edge_list = filtered_edges

        g = igraph.Graph(n=len(node_list), edges=edge_list, directed=False)

        if is_large:
            resolution = 2.0
            max_iterations = 3
        else:
            resolution = 1.0
            max_iterations = -1

        try:
            loop = asyncio.get_running_loop()
            partition = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: leidenalg.find_partition(
                        g,
                        leidenalg.RBConfigurationVertexPartition,
                        resolution_parameter=resolution,
                        n_iterations=max_iterations,
                        seed=0,
                    ),
                ),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Leiden timed out for repo %s (%d nodes), falling back to single community",
                self.repo_id,
                len(node_list),
            )
            partition = None

        await self.session.execute(
            text("DELETE FROM code_edges WHERE repo_id = :repo_id AND edge_type = 'member_of'"),
            {"repo_id": self.repo_id},
        )
        await self.session.execute(
            text("DELETE FROM code_graph_nodes WHERE repo_id = :repo_id AND kind = 'community'"),
            {"repo_id": self.repo_id},
        )

        if partition is None:
            return await self._store_single_community(node_list)

        communities: dict[int, list[int]] = {}
        for node_idx, comm_id in enumerate(partition.membership):
            communities.setdefault(comm_id, []).append(node_idx)

        comm_labels: dict[int, str] = {}
        for comm_id, members in communities.items():
            dirs = []
            for idx in members:
                fp = node_list[idx]["file_path"]
                if fp:
                    parts = fp.replace("\\", "/").split("/")
                    dirs.append(parts[-2] if len(parts) > 1 else parts[0])
            if dirs:
                comm_labels[comm_id] = Counter(dirs).most_common(1)[0][0]
            else:
                comm_labels[comm_id] = f"community_{comm_id}"

        total_members = 0
        for comm_id, members in communities.items():
            if len(members) < 2:
                continue

            label = comm_labels.get(comm_id, f"community_{comm_id}")
            # Key must be unique per Leiden community; the directory-derived label
            # is not (two communities can share a dominant directory), and an
            # ON CONFLICT DO UPDATE on a colliding key silently merges them.
            comm_key = compose_key("community", f"{label}_{comm_id}")
            comm_props = json.dumps({"community_id": comm_id, "size": len(members)})

            await self.session.execute(
                text("""
                    INSERT INTO code_graph_nodes (repo_id, kind, key, label, properties)
                    VALUES (:repo_id, 'community', :key, :label, CAST(:props AS jsonb))
                    ON CONFLICT (repo_id, kind, key) DO UPDATE
                        SET properties = EXCLUDED.properties
                """),
                {
                    "repo_id": self.repo_id,
                    "key": comm_key,
                    "label": label,
                    "props": comm_props,
                },
            )

            member_rows = json.dumps([
                {"member_key": node_list[idx]["id"]}
                for idx in members
            ])
            await self.session.execute(
                text("""
                    INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                    SELECT :repo_id, 'symbol', d.member_key, 'community', :comm_key, 'member_of', '{}'
                    FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS d(member_key text)
                    ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                """),
                {"repo_id": self.repo_id, "comm_key": comm_key, "rows": member_rows},
            )

            total_members += len(members)

        await self.session.flush()
        logger.info(
            "Detected %d communities with %d members for repo %s",
            len(communities), total_members, self.repo_id,
        )
        return total_members

    async def _store_single_community(self, node_list: list[dict]) -> int:
        if not node_list:
            return 0
        comm_key = compose_key("community", "all")
        comm_props = json.dumps({"community_id": 0, "size": len(node_list)})
        await self.session.execute(
            text("""
                INSERT INTO code_graph_nodes (repo_id, kind, key, label, properties)
                VALUES (:repo_id, 'community', :key, :key, CAST(:props AS jsonb))
                ON CONFLICT (repo_id, kind, key) DO UPDATE
                    SET properties = EXCLUDED.properties
            """),
            {"repo_id": self.repo_id, "key": comm_key, "props": comm_props},
        )
        member_rows = json.dumps([{"member_key": n["id"]} for n in node_list])
        await self.session.execute(
            text("""
                INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                SELECT :repo_id, 'symbol', d.member_key, 'community', :comm_key, 'member_of', '{}'
                FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS d(member_key text)
                ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
            """),
            {"repo_id": self.repo_id, "comm_key": comm_key, "rows": member_rows},
        )
        await self.session.flush()
        return len(node_list)

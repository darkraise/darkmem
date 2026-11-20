from __future__ import annotations

import json
import logging
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import TypeVar

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.graph_keys import compose_key
from app.utils.leiden import partition_graph

logger = logging.getLogger(__name__)

K = TypeVar("K")

_LARGE_GRAPH_THRESHOLD = 10_000


def _dir_and_stem(file_path: str | None) -> tuple[str, str] | None:
    if not file_path:
        return None
    parts = file_path.replace("\\", "/").split("/")
    stem = parts[-1].rsplit(".", 1)[0] or parts[-1]
    return (parts[-2] if len(parts) > 1 else parts[0]), stem


def _most_common(values: list[str]) -> str | None:
    if not values:
        return None
    counts = Counter(values)
    # Ties break by name so a label never depends on row order.
    return min(counts, key=lambda v: (-counts[v], v))


def label_communities(members: Mapping[K, Iterable[str | None]]) -> dict[K, str]:
    """A distinct, descriptive label per community from its members' files.

    A community is named after the folder most of its members live in. That
    alone named 100 of darkmem's 240 communities "tests", so communities
    sharing a folder are told apart by their most common file stem
    ("tests/test_events"), and any still alike are numbered by size
    ("tests/test_events (2)"). The code graph route relabels with this at
    read time, so a graph indexed before it still reads distinctly.
    """
    paths = {key: [p for p in files] for key, files in members.items()}
    base: dict[K, str] = {}
    for key, files in paths.items():
        dirs = [ds[0] for ds in map(_dir_and_stem, files) if ds]
        base[key] = _most_common(dirs) or "community"

    def by_label(labels: dict[K, str]) -> dict[str, list[K]]:
        groups: dict[str, list[K]] = {}
        for key, label in labels.items():
            groups.setdefault(label, []).append(key)
        return groups

    labels = dict(base)
    for label, keys in by_label(base).items():
        if len(keys) < 2:
            continue
        for key in keys:
            stems = [
                ds[1] for ds in map(_dir_and_stem, paths[key])
                if ds and ds[0] == label
            ]
            stem = _most_common(stems)
            if stem and stem != label:
                labels[key] = f"{label}/{stem}"

    for label, keys in by_label(labels).items():
        if len(keys) < 2:
            continue
        keys.sort(key=lambda k: (-len(paths[k]), str(k)))
        for n, key in enumerate(keys[1:], start=2):
            labels[key] = f"{label} ({n})"
    return labels


class CommunityDetector:
    def __init__(self, session: AsyncSession, repo_id: str):
        self.session = session
        self.repo_id = repo_id

    async def detect(self) -> int:
        nodes_result = await self.session.execute(
            text("""
                SELECT key, properties->>'file_path' AS file_path
                FROM code_graph_nodes
                WHERE repo_id = :repo_id
                  AND kind = 'symbol'
                  AND properties->>'kind' IN ('function', 'method', 'class', 'interface', 'struct', 'trait')
                ORDER BY key
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
                    ORDER BY e.source_key, e.target_key
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
                    ORDER BY e.source_key, e.target_key
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

        if is_large:
            resolution = 2.0
            max_iterations = 3
        else:
            resolution = 1.0
            max_iterations = -1

        result = await partition_graph(
            len(node_list),
            edge_list,
            resolution=resolution,
            n_iterations=max_iterations,
        )
        # A missing clustering library means nothing was computed, and
        # replacing the previous run's communities with nothing in their place
        # is strictly worse than leaving them.
        if result.outcome == "unavailable":
            return 0
        if result.outcome == "timeout":
            logger.warning(
                "Leiden timed out for repo %s (%d nodes), falling back to single community",
                self.repo_id,
                len(node_list),
            )
        membership = result.membership

        if membership is None:
            groups = [list(range(len(node_list)))]
            keys = [compose_key("community", "all")]
            labels = {0: keys[0]}
        else:
            by_comm: dict[int, list[int]] = {}
            for node_idx, comm_id in enumerate(membership):
                by_comm.setdefault(comm_id, []).append(node_idx)
            groups = [members for members in by_comm.values() if len(members) >= 2]
            # Named after the smallest member key: Leiden's community ids are
            # not stable across runs, and each symbol belongs to one community,
            # so that key is unique and moves only when the membership does.
            keys = [
                compose_key("community", "community:" + min(node_list[i]["id"] for i in members))
                for members in groups
            ]
            # Only the communities stored here compete for a label, so the
            # labels written match the ones the code graph route derives.
            labels = label_communities({
                n: [node_list[i]["file_path"] for i in members]
                for n, members in enumerate(groups)
            })

        desired_nodes = {
            key: {
                "key": key,
                "label": labels[n],
                "properties": {"size": len(members)},
            }
            for n, (key, members) in enumerate(zip(keys, groups))
        }
        desired_members = {
            (node_list[i]["id"], key)
            for key, members in zip(keys, groups)
            for i in members
        }
        await self._write_layer(desired_nodes, desired_members)
        logger.info(
            "Detected %d communities with %d members for repo %s",
            len(desired_nodes), len(desired_members), self.repo_id,
        )
        return len(desired_members)

    async def _write_layer(
        self, desired_nodes: dict[str, dict], desired_members: set[tuple[str, str]],
    ) -> None:
        """Write only what differs from the stored layer, so an unchanged
        partition costs two reads and no row churn."""
        stored_members = {
            (row[0], row[1])
            for row in (await self.session.execute(
                text("""
                    SELECT source_key, target_key FROM code_edges
                    WHERE repo_id = :repo_id AND edge_type = 'member_of'
                """),
                {"repo_id": self.repo_id},
            )).all()
        }
        stored_nodes = {
            row[0]: (row[1], row[2])
            for row in (await self.session.execute(
                text("""
                    SELECT key, label, properties FROM code_graph_nodes
                    WHERE repo_id = :repo_id AND kind = 'community'
                """),
                {"repo_id": self.repo_id},
            )).all()
        }

        gone_members = stored_members - desired_members
        if gone_members:
            await self.session.execute(
                text("""
                    DELETE FROM code_edges e
                    USING jsonb_to_recordset(CAST(:rows AS jsonb)) AS d(source_key text, target_key text)
                    WHERE e.repo_id = :repo_id AND e.edge_type = 'member_of'
                      AND e.source_kind = 'symbol' AND e.source_key = d.source_key
                      AND e.target_kind = 'community' AND e.target_key = d.target_key
                """),
                {"repo_id": self.repo_id, "rows": json.dumps([
                    {"source_key": src, "target_key": tgt} for src, tgt in sorted(gone_members)
                ])},
            )
        gone_nodes = sorted(set(stored_nodes) - set(desired_nodes))
        if gone_nodes:
            await self.session.execute(
                text("""
                    DELETE FROM code_graph_nodes
                    WHERE repo_id = :repo_id AND kind = 'community'
                      AND key = ANY(CAST(:keys AS text[]))
                """),
                {"repo_id": self.repo_id, "keys": gone_nodes},
            )
        changed_nodes = [
            node for key, node in sorted(desired_nodes.items())
            if stored_nodes.get(key) != (node["label"], node["properties"])
        ]
        if changed_nodes:
            await self.session.execute(
                text("""
                    INSERT INTO code_graph_nodes (repo_id, kind, key, label, properties)
                    SELECT :repo_id, 'community', n.key, n.label, n.properties
                    FROM jsonb_to_recordset(CAST(:rows AS jsonb))
                        AS n(key text, label text, properties jsonb)
                    ON CONFLICT (repo_id, kind, key) DO UPDATE
                        SET label = EXCLUDED.label, properties = EXCLUDED.properties
                """),
                {"repo_id": self.repo_id, "rows": json.dumps(changed_nodes)},
            )
        new_members = desired_members - stored_members
        if new_members:
            await self.session.execute(
                text("""
                    INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                    SELECT :repo_id, 'symbol', d.source_key, 'community', d.target_key, 'member_of', '{}'
                    FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS d(source_key text, target_key text)
                    ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                """),
                {"repo_id": self.repo_id, "rows": json.dumps([
                    {"source_key": src, "target_key": tgt} for src, tgt in sorted(new_members)
                ])},
            )
        await self.session.flush()

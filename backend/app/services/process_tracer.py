from __future__ import annotations

import json
import logging
import re
from collections import deque
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.graph_keys import compose_key

logger = logging.getLogger(__name__)


TEST_FILE_PATTERNS = re.compile(
    r"(^test_|_test\.|\.test\.|\.spec\.|/tests?/|/spec/)",
    re.IGNORECASE,
)

ENTRY_POINT_NAME_PATTERNS = re.compile(
    r"^(main|run|start|serve|execute|handle|dispatch|process|app|init|boot|launch|cli|entrypoint)$",
    re.IGNORECASE,
)

FRAMEWORK_DECORATOR_PATTERNS = re.compile(
    r"@(app|router|blueprint|click|celery|task|cron|schedule|on_event|asynccontextmanager|contextmanager)",
    re.IGNORECASE,
)


def _compute_entry_score(
    callers: int,
    callees: int,
    func_name: str,
    is_exported: bool,
    decorator_text: str | None,
) -> float:
    export_multiplier = 1.3 if is_exported else 1.0
    name_multiplier = 1.5 if ENTRY_POINT_NAME_PATTERNS.match(func_name) else 1.0
    framework_multiplier = 1.4 if decorator_text and FRAMEWORK_DECORATOR_PATTERNS.search(decorator_text) else 1.0
    ratio = min(callees / (callers + 1), 10.0)
    return ratio * export_multiplier * name_multiplier * framework_multiplier


class ProcessTracer:
    def __init__(self, session: AsyncSession, repo_id: str):
        self.session = session
        self.repo_id = repo_id

    async def trace(self, max_depth: int = 10, max_branching: int = 4, min_edge_confidence: float = 0.5) -> int:
        max_depth = max(1, min(max_depth, 20))

        await self.session.execute(
            text("""
                DELETE FROM code_edges
                WHERE repo_id = :repo_id
                  AND edge_type IN ('step_in_process', 'entry_point_of')
            """),
            {"repo_id": self.repo_id},
        )
        await self.session.execute(
            text("""
                DELETE FROM code_graph_nodes
                WHERE repo_id = :repo_id AND kind = 'process'
            """),
            {"repo_id": self.repo_id},
        )

        sym_count_row = await self.session.execute(
            text("""
                SELECT COUNT(*) FROM code_graph_nodes
                WHERE repo_id = :repo_id AND kind = 'symbol'
            """),
            {"repo_id": self.repo_id},
        )
        symbol_count = sym_count_row.scalar() or 0
        dynamic_cap = max(20, min(symbol_count // 10, 300))

        entries_result = await self.session.execute(
            text("""
                SELECT n.kind, n.key AS name, e.source_key AS file_key
                FROM code_graph_nodes n
                JOIN code_edges e ON e.repo_id = n.repo_id
                    AND e.target_key = n.key
                    AND e.edge_type IN ('handles_route', 'handles_tool')
                WHERE n.repo_id = :repo_id
                  AND n.kind IN ('route', 'tool')
            """),
            {"repo_id": self.repo_id},
        )
        route_entries = list(entries_result.mappings())

        calls_result = await self.session.execute(
            text("""
                SELECT source_key, target_key,
                       COALESCE((e.properties->>'confidence')::float, 1.0) AS confidence
                FROM code_edges e
                WHERE repo_id = :repo_id AND edge_type = 'calls'
                  AND COALESCE((e.properties->>'confidence')::float, 1.0) >= :min_conf
            """),
            {"repo_id": self.repo_id, "min_conf": min_edge_confidence},
        )
        adjacency: dict[str, list[str]] = {}
        edge_confidence: dict[tuple[str, str], float] = {}
        in_edges: dict[str, int] = {}
        out_edges: dict[str, int] = {}
        for row in calls_result.mappings():
            src, tgt = row["source_key"], row["target_key"]
            adjacency.setdefault(src, []).append(tgt)
            edge_confidence[(src, tgt)] = float(row.get("confidence", 1.0))
            out_edges[src] = out_edges.get(src, 0) + 1
            in_edges[tgt] = in_edges.get(tgt, 0) + 1

        sym_result = await self.session.execute(
            text("""
                SELECT n.key AS name, n.properties->>'file_path' AS file_path,
                       n.properties->>'kind' AS sym_kind,
                       n.properties->>'visibility' AS visibility,
                       n.properties->>'signature' AS sig
                FROM code_graph_nodes n
                WHERE n.repo_id = :repo_id
                  AND n.kind = 'symbol'
                  AND n.properties->>'kind' IN ('function', 'method')
            """),
            {"repo_id": self.repo_id},
        )
        all_syms = list(sym_result.mappings())

        scored_entries: list[tuple[float, str, str]] = []

        for sym in all_syms:
            sym_key = sym["name"]
            file_path = sym["file_path"] or ""

            if TEST_FILE_PATTERNS.search(file_path):
                continue

            callers = in_edges.get(sym_key, 0)
            callees = out_edges.get(sym_key, 0)

            if callees == 0:
                continue

            is_exported = sym.get("visibility") not in ("private", "protected")
            func_name = sym_key.split("::")[-2] if "::" in sym_key else sym_key
            score = _compute_entry_score(callers, callees, func_name, is_exported, sym.get("sig"))

            if callers == 0:
                scored_entries.append((score, sym_key, file_path))

        scored_entries.sort(key=lambda x: x[0], reverse=True)
        scored_entries = scored_entries[:dynamic_cap]

        all_entry_sources: list[tuple[str, str, str]] = []
        for entry in route_entries:
            all_entry_sources.append(("route_tool", entry["name"], entry["file_key"]))
        for _score, sym_key, file_path in scored_entries:
            all_entry_sources.append(("scored", sym_key, file_path))

        process_count = 0
        seen_step_sets: list[frozenset[str]] = []
        seen_endpoints: set[str] = set()

        for source_kind, entry_key, file_path in all_entry_sources:
            if source_kind == "route_tool":
                sym_q = await self.session.execute(
                    text("""
                        SELECT key AS name FROM code_graph_nodes
                        WHERE repo_id = :repo_id
                          AND kind = 'symbol'
                          AND properties->>'file_path' = :file_path
                          AND properties->>'kind' IN ('function', 'method')
                        ORDER BY (properties->>'line_start')::int
                        LIMIT 3
                    """),
                    {"repo_id": self.repo_id, "file_path": file_path},
                )
                start_syms = [row[0] for row in sym_q]
            else:
                start_syms = [entry_key]

            if not start_syms:
                continue

            visited: dict[str, int] = {}
            frontier = deque((s, 0) for s in start_syms)
            while frontier:
                node, depth = frontier.popleft()
                if node in visited or depth > max_depth:
                    continue
                visited[node] = depth
                neighbors = adjacency.get(node, [])
                if len(neighbors) > max_branching:
                    neighbors = sorted(neighbors, key=lambda n: edge_confidence.get((node, n), 0.0), reverse=True)[:max_branching]
                for neighbor in neighbors:
                    if neighbor not in visited and depth + 1 <= max_depth:
                        frontier.append((neighbor, depth + 1))

            steps = list(visited.items())

            if len(steps) < 3:
                continue

            step_set = frozenset(sym_key for sym_key, _ in steps)

            is_subset = any(step_set <= existing for existing in seen_step_sets)
            if is_subset:
                continue

            endpoint_id = entry_key
            if endpoint_id in seen_endpoints:
                continue
            seen_endpoints.add(endpoint_id)

            seen_step_sets = [s for s in seen_step_sets if not s < step_set]
            seen_step_sets.append(step_set)

            proc_name = f"{source_kind}:{entry_key}"
            proc_key = compose_key("process", proc_name)
            proc_props = json.dumps({"entry_kind": source_kind, "entry_file": file_path})

            await self.session.execute(
                text("""
                    INSERT INTO code_graph_nodes (repo_id, kind, key, label, properties)
                    VALUES (:repo_id, 'process', :key, :key, CAST(:props AS jsonb))
                    ON CONFLICT (repo_id, kind, key) DO UPDATE
                        SET properties = EXCLUDED.properties
                """),
                {
                    "repo_id": self.repo_id,
                    "key": proc_key,
                    "props": proc_props,
                },
            )

            await self.session.execute(
                text("""
                    INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                    VALUES (:repo_id, 'symbol', :entry_key, 'process', :proc_key, 'entry_point_of', '{}')
                    ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                """),
                {"repo_id": self.repo_id, "entry_key": entry_key, "proc_key": proc_key},
            )

            sorted_steps = sorted(steps, key=lambda x: x[1])[:dynamic_cap]
            step_rows = json.dumps([
                {"sym_key": sym_key, "step": i + 1}
                for i, (sym_key, _depth) in enumerate(sorted_steps)
            ])
            await self.session.execute(
                text("""
                    INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                    SELECT
                        :repo_id,
                        'symbol',
                        d.sym_key,
                        'process',
                        :proc_key,
                        'step_in_process',
                        jsonb_build_object('step', d.step::int)
                    FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS d(sym_key text, step text)
                    ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                """),
                {"repo_id": self.repo_id, "proc_key": proc_key, "rows": step_rows},
            )

            process_count += 1

        await self.session.flush()
        logger.info("Traced %d processes for repo %s", process_count, self.repo_id)
        return process_count

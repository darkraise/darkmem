from __future__ import annotations

import logging
from collections import deque
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

MROStrategy = Literal["c3", "leftmost-base", "implements-split", "qualified-syntax", "single-inheritance"]

_LANGUAGE_MRO: dict[str, MROStrategy] = {
    "python": "c3",
    "cpp": "leftmost-base",
    "csharp": "implements-split",
    "java": "implements-split",
    "kotlin": "implements-split",
    "rust": "qualified-syntax",
}


def _c3_linearize(
    class_key: str,
    parent_map: dict[str, list[str]],
    cache: dict[str, list[str]],
    visiting: set[str] | None = None,
) -> list[str] | None:
    """C3 linearization for Python-style MRO with diamond inheritance."""
    if class_key in cache:
        return cache[class_key]
    visiting = visiting or set()
    if class_key in visiting:
        return None  # cycle
    visiting = visiting | {class_key}

    parents = parent_map.get(class_key, [])
    if not parents:
        cache[class_key] = [class_key]
        return [class_key]

    parent_linearizations = []
    for p in parents:
        lin = _c3_linearize(p, parent_map, cache, visiting)
        if lin is None:
            return None  # cycle in parent
        parent_linearizations.append(list(lin))

    sequences = parent_linearizations + [list(parents)]
    result = [class_key]

    while any(sequences):
        head = None
        for seq in sequences:
            if not seq:
                continue
            candidate = seq[0]
            in_tail = any(candidate in s[1:] for s in sequences if s)
            if not in_tail:
                head = candidate
                break
        if head is None:
            return None  # inconsistent hierarchy
        result.append(head)
        for seq in sequences:
            if seq and seq[0] == head:
                seq.pop(0)
        sequences = [s for s in sequences if s]

    cache[class_key] = result
    return result


def _leftmost_base(class_key: str, parent_map: dict[str, list[str]]) -> list[str]:
    """C++ DFS left-to-right, keep last occurrence for diamond dedup."""
    visited_order: list[str] = []
    visited: set[str] = set()
    stack = [class_key]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        visited_order.append(current)
        parents = parent_map.get(current, [])
        for p in reversed(parents):
            stack.append(p)
    seen: set[str] = set()
    result: list[str] = []
    for key in reversed(visited_order):
        if key not in seen:
            seen.add(key)
            result.append(key)
    result.reverse()
    return result


def _implements_split(
    class_key: str,
    parent_map: dict[str, list[str]],
    edge_types: dict[str, dict[str, str]],
) -> tuple[list[str], list[str]]:
    """Java/C#/Kotlin: single extends chain + multiple implements."""
    extends_chain: list[str] = [class_key]
    implements_list: list[str] = []
    visited: set[str] = {class_key}

    current = class_key
    while True:
        parents = parent_map.get(current, [])
        types = edge_types.get(current, {})
        extends_parent = None
        for p in parents:
            if types.get(p) == "implements":
                implements_list.append(p)
            else:
                extends_parent = p
        if extends_parent:
            if extends_parent in visited:
                break
            visited.add(extends_parent)
            extends_chain.append(extends_parent)
            current = extends_parent
        else:
            break

    return extends_chain, implements_list


def _qualified_syntax(class_key: str, parent_map: dict[str, list[str]]) -> list[str]:
    """Rust: return all parents without ordering preference."""
    return [class_key] + parent_map.get(class_key, [])


def _single_inheritance(class_key: str, parent_map: dict[str, list[str]]) -> list[str]:
    """Default: walk first parent only. Terminates on cycle via visited set."""
    result = [class_key]
    visited = {class_key}
    current = class_key
    while True:
        parents = parent_map.get(current, [])
        if not parents:
            break
        current = parents[0]
        if current in visited:
            break
        visited.add(current)
        result.append(current)
    return result


class HeritageResolver:
    def __init__(self, session: AsyncSession, repo_id: str):
        self.session = session
        self.repo_id = repo_id

    @staticmethod
    def compute_mro(language: str) -> MROStrategy:
        return _LANGUAGE_MRO.get(language.lower(), "single-inheritance")

    def compute_mro_chain(
        self,
        class_key: str,
        language: str,
        parent_map: dict[str, list[str]],
        edge_types: dict[str, dict[str, str]],
        cache: dict[str, list[str]],
    ) -> list[str]:
        """Compute MRO chain for a class using language-appropriate strategy."""
        strategy = self.compute_mro(language)
        if strategy == "c3":
            result = _c3_linearize(class_key, parent_map, cache)
            if result is None:
                logger.warning(
                    "C3 linearization failed for %s (inconsistent hierarchy or cycle); "
                    "falling back to single-inheritance",
                    class_key,
                )
                return _single_inheritance(class_key, parent_map)
            return result
        elif strategy == "leftmost-base":
            return _leftmost_base(class_key, parent_map)
        elif strategy == "implements-split":
            extends, _ = _implements_split(class_key, parent_map, edge_types)
            return extends
        elif strategy == "qualified-syntax":
            return _qualified_syntax(class_key, parent_map)
        else:
            return _single_inheritance(class_key, parent_map)

    async def resolve_all(self) -> dict:
        overrides = await self._find_overrides()
        implements = await self._find_implements()
        inherited = await self._find_inherited_methods()
        return {"overrides": overrides, "implements": implements, "inherited": inherited}

    async def find_inherited_method(
        self, child_class_key: str, method_name: str
    ) -> tuple[str, float] | None:
        """Walk the EXTENDS chain from child_class_key to find a concrete ancestor method.

        Returns (method_key, confidence) at lenient confidence 0.7, or None.
        """
        visited: set[str] = set()
        queue = deque([child_class_key])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            method_result = await self.session.execute(
                text("""
                    SELECT e.target_key
                    FROM code_edges e
                    WHERE e.repo_id = :repo_id
                      AND e.source_key = :class_key
                      AND e.edge_type = 'has_method'
                      AND split_part(e.target_key, '::', 1) = :method_name
                """),
                {
                    "repo_id": self.repo_id,
                    "class_key": current,
                    "method_name": method_name,
                },
            )
            row = method_result.fetchone()
            if row and current != child_class_key:
                return (row[0], 0.7)

            parent_result = await self.session.execute(
                text("""
                    SELECT target_key
                    FROM code_edges
                    WHERE repo_id = :repo_id
                      AND source_key = :class_key
                      AND edge_type IN ('extends', 'implements')
                """),
                {"repo_id": self.repo_id, "class_key": current},
            )
            for parent_row in parent_result.fetchall():
                if parent_row[0] not in visited:
                    queue.append(parent_row[0])

        return None

    async def _find_inherited_methods(self) -> int:
        """Create method_inherited edges using language-aware MRO resolution.

        Walks the MRO chain for each child class and links child methods to the
        first ancestor method with the same name, skipping already-overridden methods.
        """
        parent_result = await self.session.execute(
            text("""
                SELECT source_key, target_key, edge_type
                FROM code_edges
                WHERE repo_id = :repo_id AND edge_type IN ('extends', 'implements')
            """),
            {"repo_id": self.repo_id},
        )
        parent_map: dict[str, list[str]] = {}
        edge_types: dict[str, dict[str, str]] = {}
        for row in parent_result.mappings():
            parent_map.setdefault(row["source_key"], []).append(row["target_key"])
            edge_types.setdefault(row["source_key"], {})[row["target_key"]] = row["edge_type"]

        if not parent_map:
            return 0

        method_result = await self.session.execute(
            text("""
                SELECT source_key AS class_key, target_key AS method_key,
                       split_part(target_key, '::', 1) AS method_name
                FROM code_edges
                WHERE repo_id = :repo_id AND edge_type = 'has_method'
            """),
            {"repo_id": self.repo_id},
        )
        method_map: dict[str, list[tuple[str, str]]] = {}
        for row in method_result.mappings():
            method_map.setdefault(row["class_key"], []).append(
                (row["method_key"], row["method_name"])
            )

        override_result = await self.session.execute(
            text("""
                SELECT source_key FROM code_edges
                WHERE repo_id = :repo_id AND edge_type = 'method_overrides'
            """),
            {"repo_id": self.repo_id},
        )
        already_overridden = {row[0] for row in override_result}

        class_lang_result = await self.session.execute(
            text("""
                SELECT n.key, n.properties->>'file_path' AS file_path
                FROM code_graph_nodes n
                WHERE n.repo_id = :repo_id AND n.kind = 'symbol'
                  AND n.properties->>'kind' IN ('class', 'struct', 'interface', 'trait')
            """),
            {"repo_id": self.repo_id},
        )
        lang_map = {
            "py": "python", "cpp": "cpp", "cc": "cpp",
            "cs": "csharp", "java": "java", "kt": "kotlin", "rs": "rust",
        }
        class_language: dict[str, str] = {}
        for row in class_lang_result.mappings():
            fp = row["file_path"] or ""
            ext = fp.rsplit(".", 1)[-1] if "." in fp else ""
            class_language[row["key"]] = lang_map.get(ext, "")

        cache: dict[str, list[str]] = {}
        edges_to_create: list[tuple[str, str]] = []

        for child_key in parent_map:
            language = class_language.get(child_key, "")
            mro = self.compute_mro_chain(child_key, language, parent_map, edge_types, cache)

            child_methods = method_map.get(child_key, [])
            for method_key, method_name in child_methods:
                if method_key in already_overridden:
                    continue
                for ancestor_key in mro[1:]:
                    ancestor_methods = method_map.get(ancestor_key, [])
                    match = next(
                        (mk for mk, mn in ancestor_methods if mn == method_name and mk != method_key),
                        None,
                    )
                    if match:
                        edges_to_create.append((method_key, match))
                        break

        if not edges_to_create:
            return 0

        import json
        edge_data = json.dumps([
            {"child_method": cm, "ancestor_method": am}
            for cm, am in edges_to_create
        ])
        result = await self.session.execute(
            text("""
                INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                SELECT :repo_id, 'symbol', d.child_method, 'symbol', d.ancestor_method, 'method_inherited',
                       jsonb_build_object('confidence', 0.7)
                FROM jsonb_to_recordset(CAST(:edges AS jsonb)) AS d(child_method text, ancestor_method text)
                ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                RETURNING 1
            """),
            {"repo_id": self.repo_id, "edges": edge_data},
        )
        count = len(result.fetchall())
        logger.info("Created %d method_inherited edges for repo %s", count, self.repo_id)
        return count

    async def _find_overrides(self) -> int:
        """Find methods that override parent class methods via extends chain."""
        result = await self.session.execute(
            text("""
                WITH extends_pairs AS (
                    SELECT source_key AS child_key, target_key AS parent_key
                    FROM code_edges
                    WHERE repo_id = :repo_id AND edge_type = 'extends'
                ),
                child_methods AS (
                    SELECT ep.child_key, ep.parent_key, e.target_key AS method_key,
                           split_part(e.target_key, '::', 1) AS method_name
                    FROM extends_pairs ep
                    JOIN code_edges e ON e.repo_id = :repo_id
                        AND e.source_key = ep.child_key
                        AND e.edge_type = 'has_method'
                ),
                parent_methods AS (
                    SELECT ep.child_key, ep.parent_key, e.target_key AS method_key,
                           split_part(e.target_key, '::', 1) AS method_name
                    FROM extends_pairs ep
                    JOIN code_edges e ON e.repo_id = :repo_id
                        AND e.source_key = ep.parent_key
                        AND e.edge_type = 'has_method'
                ),
                overrides AS (
                    SELECT cm.method_key AS child_method, pm.method_key AS parent_method
                    FROM child_methods cm
                    JOIN parent_methods pm
                        ON cm.child_key = pm.child_key
                        AND cm.parent_key = pm.parent_key
                        AND cm.method_name = pm.method_name
                        AND cm.method_key <> pm.method_key
                )
                INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                SELECT :repo_id, 'symbol', child_method, 'symbol', parent_method, 'method_overrides', '{}'
                FROM overrides
                ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                RETURNING 1
            """),
            {"repo_id": self.repo_id},
        )
        count = len(result.fetchall())
        logger.info("Created %d method_overrides edges for repo %s", count, self.repo_id)
        return count

    async def _find_implements(self) -> int:
        """Find methods that implement interface methods via implements chain."""
        result = await self.session.execute(
            text("""
                WITH impl_pairs AS (
                    SELECT source_key AS child_key, target_key AS iface_key
                    FROM code_edges
                    WHERE repo_id = :repo_id AND edge_type = 'implements'
                ),
                child_methods AS (
                    SELECT ip.child_key, ip.iface_key, e.target_key AS method_key,
                           split_part(e.target_key, '::', 1) AS method_name
                    FROM impl_pairs ip
                    JOIN code_edges e ON e.repo_id = :repo_id
                        AND e.source_key = ip.child_key
                        AND e.edge_type = 'has_method'
                ),
                iface_methods AS (
                    SELECT ip.child_key, ip.iface_key, e.target_key AS method_key,
                           split_part(e.target_key, '::', 1) AS method_name
                    FROM impl_pairs ip
                    JOIN code_edges e ON e.repo_id = :repo_id
                        AND e.source_key = ip.iface_key
                        AND e.edge_type = 'has_method'
                ),
                method_impls AS (
                    SELECT cm.method_key AS child_method, im.method_key AS iface_method
                    FROM child_methods cm
                    JOIN iface_methods im
                        ON cm.child_key = im.child_key
                        AND cm.iface_key = im.iface_key
                        AND cm.method_name = im.method_name
                        AND cm.method_key <> im.method_key
                )
                INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                SELECT :repo_id, 'symbol', child_method, 'symbol', iface_method, 'method_implements', '{}'
                FROM method_impls
                ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                RETURNING 1
            """),
            {"repo_id": self.repo_id},
        )
        count = len(result.fetchall())
        logger.info("Created %d method_implements edges for repo %s", count, self.repo_id)
        return count


class AccessResolver:
    """Creates accesses edges for field/property access patterns using type resolution."""

    def __init__(self, session: AsyncSession, repo_id: str):
        self.session = session
        self.repo_id = repo_id

    async def resolve(self, type_envs: dict, call_data: dict) -> int:
        """
        For member calls like obj.field, if obj's type resolves to a class
        and field is a Property (not a method), create an accesses edge.

        type_envs: file_path -> TypeEnvironment
        call_data: file_path -> list of ExtractedCall with call_form="member"
        """
        count = 0
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
            import json
            edge_data = json.dumps(edges)
            result = await self.session.execute(
                text("""
                    WITH edge_input AS (
                        SELECT
                            d.caller_file,
                            d.caller_line::int AS caller_line,
                            d.receiver_type,
                            d.field_name
                        FROM jsonb_to_recordset(CAST(:edges AS jsonb)) AS d(
                            caller_file   text,
                            caller_line   text,
                            receiver_type text,
                            field_name    text
                        )
                    ),
                    matched AS (
                        SELECT DISTINCT
                            sym_node.key AS caller_key,
                            prop_node.key AS prop_key
                        FROM edge_input ei
                        JOIN code_graph_nodes sym_node
                            ON sym_node.repo_id = :repo_id
                            AND sym_node.kind = 'symbol'
                            AND sym_node.properties->>'file_path' = ei.caller_file
                            AND (sym_node.properties->>'line_start')::int <= ei.caller_line
                            AND (sym_node.properties->>'line_end')::int >= ei.caller_line
                            AND sym_node.properties->>'kind' IN ('function', 'method')
                        JOIN code_graph_nodes cls_node
                            ON cls_node.repo_id = :repo_id
                            AND cls_node.kind = 'symbol'
                            AND split_part(cls_node.key, '::', 1) = ei.receiver_type
                        JOIN code_edges has_prop
                            ON has_prop.repo_id = :repo_id
                            AND has_prop.edge_type = 'has_property'
                            AND has_prop.source_key = cls_node.key
                        JOIN code_graph_nodes prop_node
                            ON prop_node.repo_id = :repo_id
                            AND prop_node.kind = 'property'
                            AND prop_node.key = has_prop.target_key
                            AND split_part(prop_node.key, '::', 1) = ei.field_name
                    )
                    INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                    SELECT :repo_id, 'symbol', caller_key, 'property', prop_key, 'accesses', '{}'
                    FROM matched
                    ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                    RETURNING 1
                """),
                {"repo_id": self.repo_id, "edges": edge_data},
            )
            count = len(result.fetchall())

        logger.info("Created %d accesses edges for repo %s", count, self.repo_id)
        return count

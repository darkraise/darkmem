import logging
from uuid import UUID

from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.code import CodeFile, CodeSymbol
from app.config import settings
from app.repositories.vector import PostgresVectorRepository
from app.services.llm import LLMOrchestrator
from app.services.rank_fusion import RRF_K
from app.utils.graph_keys import compose_key, decompose_key, split_symbol_key

logger = logging.getLogger(__name__)

# Code search fuses its two arms on a ``(repo_id, file_path, line_start)`` key
# rather than on a row id, so it keeps its own accumulation loop; the constant
# is imported because a second declaration of it can drift from the one the
# memory path ranks by while both files still read as if they agreed.
__all__ = ["RRF_K", "CodeQueryService"]

# `level=auto` folds the code graph to files above this many files plus
# symbols in scope. The canvas is an SVG laid out in the browser: ops-tiny's
# 21 nodes draw instantly, the darkmem repo's 22,507 kept the tab busy past a
# 30-second screenshot and drew an unreadable hairball.
CODE_GRAPH_AUTO_LIMIT = 2000
GRAPH_LEVELS = ("symbol", "file", "auto")


def normalise_graph_scope(scope: str | None) -> str | None:
    """A file or folder path relative to the repo root; blank means the
    whole repo. Slashes at either end are dropped, so ``backend/`` and
    ``/backend`` both name the ``backend`` folder."""
    if scope is None:
        return None
    scope = scope.strip().strip("/")
    return scope or None


def _scope_sql(scope: str | None) -> str:
    """The path predicate on ``f.file_path``: the file itself or anything
    under it as a folder, never a sibling that merely shares the prefix
    (``backend/app`` must not match ``backend/apple.py``)."""
    if scope is None:
        return "TRUE"
    return "(f.file_path = :scope OR left(f.file_path, :scope_len) = :scope_dir)"


def _scope_params(scope: str | None) -> dict:
    if scope is None:
        return {}
    return {"scope": scope, "scope_dir": f"{scope}/", "scope_len": len(scope) + 1}


class CodeQueryService:
    def __init__(self, session: AsyncSession, llm: LLMOrchestrator | None = None):
        self.session = session
        self.llm = llm

    async def search_code(
        self,
        query: str,
        limit: int = 20,
        repo_id: UUID | None = None,
        language: str | None = None,
    ) -> list[dict]:
        results_map: dict[tuple[str, str, int], dict] = {}

        # `settings.read_only` skips the vector arm outright rather than
        # letting it attempt and fail: a backup worker makes no external
        # call by ruling, and the ILIKE arm below still answers.
        if self.llm and not settings.read_only:
            try:
                vector, fingerprint = await self.llm.embed(query)
                vector_repo = PostgresVectorRepository(self.session)
                chunk_results = await vector_repo.search_code_chunks(
                    vector, fingerprint=fingerprint,
                    limit=limit * 2, repo_id=repo_id, language=language,
                )
                for rank, chunk in enumerate(chunk_results, start=1):
                    key = (str(chunk["repo_id"]), chunk["file_path"], chunk["line_start"])
                    if key not in results_map:
                        results_map[key] = {
                            "chunk_content": chunk.get("chunk_content", ""),
                            "file_path": chunk.get("file_path", ""),
                            "repo_id": str(chunk.get("repo_id", "")),
                            "language": chunk.get("language"),
                            "symbol_name": chunk.get("symbol_name"),
                            "line_start": chunk.get("line_start", 0),
                            "line_end": chunk.get("line_end", 0),
                            "rrf_score": 0,
                        }
                    results_map[key]["rrf_score"] += 1.0 / (RRF_K + rank)
            except Exception as e:
                logger.warning("Vector search failed: %s", e)

        try:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            text_query = (
                select(CodeSymbol, CodeFile.file_path, CodeFile.repo_id, CodeFile.language)
                .join(CodeFile)
                .where(
                    (CodeSymbol.name.ilike(f"%{escaped}%"))
                    | (CodeSymbol.source_code.ilike(f"%{escaped}%"))
                )
            )
            if repo_id:
                text_query = text_query.where(CodeFile.repo_id == repo_id)
            if language:
                # The vector branch filters by language; without this the keyword
                # side fuses in other-language matches and defeats the filter.
                text_query = text_query.where(CodeFile.language == language)
            # Relevance order so RRF ranks mean something (and truncation is
            # deterministic): exact name > prefix > substring > body-only match,
            # then shorter names first.
            text_query = text_query.order_by(
                case(
                    (CodeSymbol.name.ilike(escaped), 0),
                    (CodeSymbol.name.ilike(f"{escaped}%"), 1),
                    (CodeSymbol.name.ilike(f"%{escaped}%"), 2),
                    else_=3,
                ),
                func.length(CodeSymbol.name),
            )
            text_query = text_query.limit(limit * 2)

            text_results = (await self.session.execute(text_query)).all()
            for rank, (sym, file_path, rid, lang) in enumerate(text_results, start=1):
                key = (str(rid), file_path, sym.line_start)
                if key not in results_map:
                    results_map[key] = {
                        "chunk_content": sym.source_code[:500] if sym.source_code else "",
                        "file_path": file_path,
                        "repo_id": str(rid),
                        "language": lang,
                        "symbol_name": sym.name,
                        "line_start": sym.line_start,
                        "line_end": sym.line_end,
                        "rrf_score": 0,
                    }
                results_map[key]["rrf_score"] += 1.0 / (RRF_K + rank)
        except Exception as e:
            logger.warning("Text search failed: %s", e)

        sorted_results = sorted(results_map.values(), key=lambda x: x["rrf_score"], reverse=True)
        return sorted_results[:limit]

    async def list_symbols(
        self,
        repo_id: UUID | None = None,
        file_path: str | None = None,
        kind: str | None = None,
        q: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        query = select(CodeSymbol, CodeFile.file_path).join(CodeFile, CodeSymbol.file_id == CodeFile.id)
        count_query = select(func.count(CodeSymbol.id)).join(CodeFile, CodeSymbol.file_id == CodeFile.id)

        if repo_id:
            query = query.where(CodeFile.repo_id == repo_id)
            count_query = count_query.where(CodeFile.repo_id == repo_id)
        if file_path:
            query = query.where(CodeFile.file_path == file_path)
            count_query = count_query.where(CodeFile.file_path == file_path)
        if kind:
            query = query.where(CodeSymbol.kind == kind)
            count_query = count_query.where(CodeSymbol.kind == kind)
        if q:
            escaped_q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(CodeSymbol.name.ilike(f"%{escaped_q}%"))
            count_query = count_query.where(CodeSymbol.name.ilike(f"%{escaped_q}%"))

        total = (await self.session.execute(count_query)).scalar() or 0
        rows = (await self.session.execute(query.offset(offset).limit(limit))).all()

        items = []
        for sym, fp in rows:
            items.append({
                "id": sym.id, "name": sym.name, "kind": sym.kind,
                "file_path": fp, "line_start": sym.line_start, "line_end": sym.line_end,
                "signature": sym.signature, "docstring": sym.docstring,
                "visibility": sym.visibility, "source_code": sym.source_code,
                "summary": sym.summary, "enrichment_status": sym.enrichment_status,
            })
        return {"items": items, "total": total}

    async def lookup_symbol(
        self, name: str, file_path: str, owner: str | None = None
    ) -> dict | None:
        stmt = select(CodeSymbol).join(CodeFile).where(
            CodeSymbol.name == name, CodeFile.file_path == file_path,
        )
        if owner:
            # Same-named methods under different classes in one file are only
            # distinguishable by their parent symbol (the owner segment of
            # the graph node key).
            parent = aliased(CodeSymbol)
            stmt = stmt.join(
                parent, CodeSymbol.parent_symbol_id == parent.id
            ).where(parent.name == owner)
        sym = (await self.session.execute(stmt)).scalars().first()
        if not sym:
            return None

        file = (await self.session.execute(
            select(CodeFile).where(CodeFile.id == sym.file_id)
        )).scalar_one_or_none()

        return {
            "id": sym.id, "name": sym.name, "kind": sym.kind,
            "file_path": file.file_path if file else "",
            "line_start": sym.line_start, "line_end": sym.line_end,
            "signature": sym.signature, "docstring": sym.docstring,
            "visibility": sym.visibility, "source_code": sym.source_code,
            "summary": sym.summary, "enrichment_status": sym.enrichment_status,
        }

    async def get_symbol(self, symbol_id: UUID) -> dict | None:
        sym = (await self.session.execute(
            select(CodeSymbol).where(CodeSymbol.id == symbol_id)
        )).scalar_one_or_none()
        if not sym:
            return None

        file = (await self.session.execute(
            select(CodeFile).where(CodeFile.id == sym.file_id)
        )).scalar_one_or_none()

        return {
            "id": sym.id, "name": sym.name, "kind": sym.kind,
            "file_path": file.file_path if file else "",
            "line_start": sym.line_start, "line_end": sym.line_end,
            "signature": sym.signature, "docstring": sym.docstring,
            "visibility": sym.visibility, "source_code": sym.source_code,
            "summary": sym.summary, "enrichment_status": sym.enrichment_status,
        }

    async def list_files(
        self, repo_id: UUID, path_prefix: str | None = None, language: str | None = None,
    ) -> list[dict]:
        query = select(CodeFile).where(CodeFile.repo_id == repo_id)
        if path_prefix:
            query = query.where(CodeFile.file_path.startswith(path_prefix))
        if language:
            query = query.where(CodeFile.language == language)

        rows = (await self.session.execute(query)).scalars().all()
        return [
            {
                "id": f.id, "file_path": f.file_path, "language": f.language,
                "last_commit_sha": f.last_commit_sha, "indexed_at": f.indexed_at,
            }
            for f in rows
        ]

    async def get_code_graph(
        self, repo_id: UUID, level: str | None = None, scope: str | None = None,
    ) -> dict:
        """The repo's node-and-edge graph for the Code Graph canvas.

        With neither argument this is the whole symbol graph, exactly as it
        has always been served. ``level``/``scope`` are the canvas's level of
        detail: ``scope`` narrows to one file or folder, ``level='file'``
        folds symbols into their files, and ``level='auto'`` folds only when
        the scope holds more than ``CODE_GRAPH_AUTO_LIMIT`` files and symbols
        (the canvas lays every node out client-side, and the 3,996-file
        darkmem repo's 22,507 nodes stalled the tab). A caller that passes
        either gets the chosen ``level`` and the folding ``stats`` back
        beside the graph, so it can say what is folded.
        """
        if level is None and scope is None:
            return await self._symbol_graph(repo_id, None)

        scope = normalise_graph_scope(scope)
        requested = level or "symbol"
        if requested not in GRAPH_LEVELS:
            raise ValueError(f"level must be one of {', '.join(GRAPH_LEVELS)}")
        counts = await self._scope_counts(repo_id, scope)
        chosen = requested
        if requested == "auto":
            drawable = counts["files"] + counts["symbols"]
            chosen = "file" if drawable > CODE_GRAPH_AUTO_LIMIT else "symbol"

        if chosen == "file":
            graph = await self._file_graph(repo_id, scope, counts)
        else:
            graph = await self._symbol_graph(repo_id, scope)
            graph["stats"] = dict(counts)
        graph.update({
            "level": chosen,
            "requested_level": requested,
            "scope": scope,
            "auto_limit": CODE_GRAPH_AUTO_LIMIT,
        })
        return graph

    async def _scope_counts(self, repo_id: UUID, scope: str | None) -> dict:
        params = {"repo_id": str(repo_id), **_scope_params(scope)}
        row = (await self.session.execute(
            text(f"""
                SELECT
                    (SELECT count(*) FROM code_files f
                     WHERE f.repo_id = :repo_id AND {_scope_sql(scope)}) AS files,
                    (SELECT count(*) FROM code_symbols s
                     JOIN code_files f ON f.id = s.file_id
                     WHERE f.repo_id = :repo_id AND {_scope_sql(scope)}) AS symbols
            """),
            params,
        )).mappings().one()
        return {"files": row["files"], "symbols": row["symbols"]}

    async def _symbol_graph(self, repo_id: UUID, scope: str | None) -> dict:
        repo_id_str = str(repo_id)
        params = {"repo_id": repo_id_str, **_scope_params(scope)}
        nodes_by_id: dict[str, dict] = {}
        edges: list[dict] = []

        file_rows = (await self.session.execute(
            text(f"SELECT file_path FROM code_files f WHERE repo_id = :repo_id AND {_scope_sql(scope)}"),
            params,
        )).mappings().all()
        for row in file_rows:
            nodes_by_id[row["file_path"]] = {
                "id": row["file_path"], "label": row["file_path"], "kind": "file",
            }

        sym_rows = (await self.session.execute(
            text(f"""
                SELECT s.name, s.kind, f.file_path, p.name AS owner
                FROM code_symbols s
                JOIN code_files f ON f.id = s.file_id
                LEFT JOIN code_symbols p ON p.id = s.parent_symbol_id
                WHERE f.repo_id = :repo_id AND {_scope_sql(scope)}
            """),
            params,
        )).mappings().all()
        for row in sym_rows:
            node_id = compose_key("symbol", row["name"], row["file_path"], owner=row["owner"])
            nodes_by_id[node_id] = {
                "id": node_id, "label": row["name"], "kind": row["kind"],
                "file_path": row["file_path"],
            }

        # Under a scope, the files and symbols above are the scope; every
        # other node (module, route, community, process, ...) is drawn only
        # when an edge ties it to one of them.
        in_scope = set(nodes_by_id) if scope is not None else None
        others: dict[str, dict] = {}

        # code_graph_nodes re-keys files as their path and symbols via the same
        # compose_key, so most aux rows are the nodes above under a generic kind;
        # merge their properties into the kind-specific node instead of emitting
        # a duplicate id.
        aux_rows = (await self.session.execute(
            text("""
                SELECT key, kind, label, properties, properties->>'file_path' AS file_path
                FROM code_graph_nodes
                WHERE repo_id = :repo_id
            """),
            {"repo_id": repo_id_str},
        )).mappings().all()
        for row in aux_rows:
            existing = nodes_by_id.get(row["key"])
            if existing is not None:
                # Only 'file'/'symbol' rows are re-keyed duplicates of nodes
                # already emitted. Uniqueness is per (repo, kind, key), so an
                # unrelated kind may share the key (module "config" vs
                # property "config") and must not clobber the richer node.
                if row["kind"] in ("file", "symbol"):
                    if row["file_path"] and "file_path" not in existing:
                        existing["file_path"] = row["file_path"]
                    if row["properties"]:
                        existing["properties"] = row["properties"]
                continue
            if in_scope is not None and row["kind"] in ("file", "symbol"):
                continue
            node = {"id": row["key"], "label": row["label"] or row["key"], "kind": row["kind"]}
            if row["file_path"]:
                node["file_path"] = row["file_path"]
            if row["properties"]:
                node["properties"] = row["properties"]
            if in_scope is None:
                nodes_by_id[row["key"]] = node
            else:
                others.setdefault(row["key"], node)

        if in_scope is None:
            edge_rows = (await self.session.execute(
                text("""
                    SELECT source_key, target_key, edge_type, properties
                    FROM code_edges
                    WHERE repo_id = :repo_id
                    ORDER BY edge_type, (properties->>'step')::int NULLS LAST, source_key, target_key
                """),
                {"repo_id": repo_id_str},
            )).mappings().all()
        else:
            keys = list(in_scope)
            edge_rows = (await self.session.execute(
                text("""
                    SELECT source_key, target_key, edge_type, properties
                    FROM code_edges
                    WHERE repo_id = :repo_id
                      AND (source_key = ANY(CAST(:keys AS text[]))
                           OR target_key = ANY(CAST(:keys AS text[])))
                    ORDER BY edge_type, (properties->>'step')::int NULLS LAST, source_key, target_key
                """),
                {"repo_id": repo_id_str, "keys": keys},
            )).mappings().all()
            kept = []
            processes: list[str] = []
            for row in edge_rows:
                ends = (row["source_key"], row["target_key"])
                if not all(end in in_scope or end in others for end in ends):
                    continue
                for end in ends:
                    if end not in in_scope and end not in nodes_by_id:
                        nodes_by_id[end] = others[end]
                        if others[end]["kind"] == "process":
                            processes.append(end)
                if row["edge_type"] != "step_in_process":
                    kept.append(row)
            # A process keeps every one of its steps, not only the ones in the
            # scope, so its step count reads the same at every scope.
            if processes:
                kept.extend((await self.session.execute(
                    text("""
                        SELECT source_key, target_key, edge_type, properties
                        FROM code_edges
                        WHERE repo_id = :repo_id AND edge_type = 'step_in_process'
                          AND target_key = ANY(CAST(:procs AS text[]))
                        ORDER BY (properties->>'step')::int NULLS LAST, source_key, target_key
                    """),
                    {"repo_id": repo_id_str, "procs": processes},
                )).mappings().all())
            edge_rows = kept

        for row in edge_rows:
            edge = {"source": row["source_key"], "target": row["target_key"], "type": row["edge_type"]}
            props = row["properties"]
            if props:
                edge["properties"] = props
            edges.append(edge)

        return {"nodes": list(nodes_by_id.values()), "edges": edges}

    async def _file_graph(self, repo_id: UUID, scope: str | None, counts: dict) -> dict:
        """Files as nodes, every symbol->symbol edge folded into a weighted
        file->file ``depends_on`` edge. Files that define no symbol are left
        out: nothing folds into them and there is nothing to drill into."""
        repo_id_str = str(repo_id)
        params = {"repo_id": repo_id_str, **_scope_params(scope)}

        file_rows = (await self.session.execute(
            text(f"""
                SELECT f.file_path, count(s.id) AS symbols
                FROM code_files f
                JOIN code_symbols s ON s.file_id = f.id
                WHERE f.repo_id = :repo_id AND {_scope_sql(scope)}
                GROUP BY f.file_path
                ORDER BY f.file_path
            """),
            params,
        )).mappings().all()
        files = {row["file_path"]: row["symbols"] for row in file_rows}
        nodes: list[dict] = [
            {"id": fp, "label": fp, "kind": "file", "file_path": fp, "symbol_count": n}
            for fp, n in files.items()
        ]

        # Symbol keys always carry the file path as their second segment
        # (graph_keys' invariant), so the fold is a GROUP BY, not a join.
        fold_rows = (await self.session.execute(
            text("""
                SELECT split_part(source_key, '::', 2) AS source_file,
                       split_part(target_key, '::', 2) AS target_file,
                       edge_type, count(*) AS n
                FROM code_edges
                WHERE repo_id = :repo_id AND source_kind = 'symbol' AND target_kind = 'symbol'
                GROUP BY 1, 2, 3
            """),
            {"repo_id": repo_id_str},
        )).mappings().all()
        folded: dict[tuple[str, str], dict] = {}
        symbol_edges = 0
        boundary_edges = 0
        for row in fold_rows:
            src, tgt, n = row["source_file"], row["target_file"], row["n"]
            src_in, tgt_in = src in files, tgt in files
            if src_in and tgt_in:
                symbol_edges += n
                if src == tgt:
                    continue
                entry = folded.setdefault((src, tgt), {"weight": 0, "edge_types": {}})
                entry["weight"] += n
                entry["edge_types"][row["edge_type"]] = entry["edge_types"].get(row["edge_type"], 0) + n
            elif src_in or tgt_in:
                boundary_edges += n
        edges: list[dict] = [
            {"source": src, "target": tgt, "type": "depends_on", "properties": props}
            for (src, tgt), props in sorted(folded.items())
        ]

        # A file sits in the community most of its symbols belong to, so
        # colour-by-community and the navigator still work on the fold.
        member_rows = (await self.session.execute(
            text("""
                SELECT split_part(source_key, '::', 2) AS file_path, target_key, count(*) AS n
                FROM code_edges
                WHERE repo_id = :repo_id AND edge_type = 'member_of'
                GROUP BY 1, 2
                ORDER BY 1, 3 DESC, 2
            """),
            {"repo_id": repo_id_str},
        )).mappings().all()
        community_of: dict[str, str] = {}
        for row in member_rows:
            if row["file_path"] in files:
                community_of.setdefault(row["file_path"], row["target_key"])

        # Process steps stay symbols: the client maps each step to its file,
        # and a process reads as the same number of steps at every level.
        step_rows = (await self.session.execute(
            text("""
                SELECT source_key, target_key, edge_type, properties
                FROM code_edges
                WHERE repo_id = :repo_id AND edge_type = 'step_in_process'
                ORDER BY (properties->>'step')::int NULLS LAST, source_key, target_key
            """),
            {"repo_id": repo_id_str},
        )).mappings().all()
        processes = {
            row["target_key"] for row in step_rows
            if split_symbol_key(row["source_key"])[1] in files
        }

        wanted = set(community_of.values()) | processes
        if wanted:
            aux_rows = (await self.session.execute(
                text("""
                    SELECT key, kind, label, properties
                    FROM code_graph_nodes
                    WHERE repo_id = :repo_id AND kind IN ('community', 'process')
                    ORDER BY kind, key
                """),
                {"repo_id": repo_id_str},
            )).mappings().all()
            for row in aux_rows:
                if row["key"] not in wanted:
                    continue
                node = {"id": row["key"], "label": row["label"] or row["key"], "kind": row["kind"]}
                if row["properties"]:
                    node["properties"] = row["properties"]
                nodes.append(node)
        edges.extend(
            {"source": fp, "target": community, "type": "member_of"}
            for fp, community in community_of.items()
        )
        for row in step_rows:
            if row["target_key"] in processes:
                edge = {"source": row["source_key"], "target": row["target_key"], "type": row["edge_type"]}
                if row["properties"]:
                    edge["properties"] = row["properties"]
                edges.append(edge)

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                **counts,
                "files_drawn": len(files),
                "files_without_symbols": counts["files"] - len(files),
                "symbol_edges": symbol_edges,
                "file_edges": len(folded),
                "boundary_edges": boundary_edges,
            },
        }

    async def calculate_blast_radius(self, symbol_id: str, max_depth: int = 10) -> dict | None:
        sym = None
        file = None
        if "::" in symbol_id:
            name, file_path, _owner = split_symbol_key(symbol_id)
            sym = (await self.session.execute(
                select(CodeSymbol).join(CodeFile).where(
                    CodeSymbol.name == name, CodeFile.file_path == file_path,
                )
            )).scalars().first()
            if sym:
                file = (await self.session.execute(
                    select(CodeFile).where(CodeFile.id == sym.file_id)
                )).scalar_one_or_none()
        else:
            try:
                uid = UUID(symbol_id)
                sym = (await self.session.execute(
                    select(CodeSymbol).where(CodeSymbol.id == uid)
                )).scalar_one_or_none()
                if sym:
                    file = (await self.session.execute(
                        select(CodeFile).where(CodeFile.id == sym.file_id)
                    )).scalar_one_or_none()
            except ValueError:
                pass

        if not sym:
            return None

        repo_id_str = str(file.repo_id) if file else ""
        owner = None
        if file and sym.parent_symbol_id:
            owner = (await self.session.execute(
                select(CodeSymbol.name).where(CodeSymbol.id == sym.parent_symbol_id)
            )).scalar_one_or_none()
        symbol_key = compose_key("symbol", sym.name, file.file_path if file else None, owner=owner)
        clamped_depth = max(1, min(max_depth, 50))

        rows = (await self.session.execute(
            text("""
                WITH RECURSIVE callers AS (
                    SELECT source_key AS name, source_kind AS kind, 1 AS distance
                    FROM code_edges
                    WHERE repo_id = :repo_id
                      AND target_key = :symbol_key
                      AND edge_type IN ('calls', 'extends', 'implements', 'accesses', 'method_overrides')
                    UNION
                    SELECT e.source_key, e.source_kind, c.distance + 1
                    FROM callers c
                    JOIN code_edges e
                        ON e.target_key = c.name
                        AND e.repo_id = :repo_id
                        AND e.edge_type IN ('calls', 'extends', 'implements', 'accesses', 'method_overrides')
                    WHERE c.distance < :max_depth
                )
                SELECT name, kind, MIN(distance) AS distance
                FROM callers
                GROUP BY name, kind
                ORDER BY distance
            """),
            {"repo_id": repo_id_str, "symbol_key": symbol_key, "max_depth": clamped_depth},
        )).mappings().all()

        by_depth: dict[str, list] = {"1": [], "2": [], "3+": []}
        affected = []
        for r in rows:
            raw_key = r["name"]  # full composite source_key (may include ::owner)
            name_val = raw_key
            kind_val = r["kind"]
            dist = r["distance"]
            file_path_val = None
            if "::" in (raw_key or ""):
                name_val, file_path_val = decompose_key("symbol", raw_key)
            # `key` is the graph node id (owner-qualified); name/file_path are for display.
            entry = {"key": raw_key, "name": name_val, "kind": kind_val, "file_path": file_path_val, "distance": dist}
            affected.append(entry)
            if dist == 1:
                by_depth["1"].append(entry)
            elif dist == 2:
                by_depth["2"].append(entry)
            else:
                by_depth["3+"].append(entry)

        direct_callers = len(by_depth["1"])
        risk = "LOW"
        if direct_callers > 10:
            risk = "CRITICAL"
        elif direct_callers > 5:
            risk = "HIGH"
        elif direct_callers > 2:
            risk = "MEDIUM"

        return {
            "symbol": {"id": str(sym.id), "name": sym.name, "file_path": file.file_path if file else ""},
            "affected": affected,
            "by_depth": by_depth,
            "risk": risk,
            "total": len(affected),
        }

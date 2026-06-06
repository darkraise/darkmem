import logging
from uuid import UUID

from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import CodeFile, CodeSymbol
from app.repositories.vector import PostgresVectorRepository
from app.services.llm import LLMOrchestrator
from app.utils.graph_keys import compose_key, decompose_key, split_symbol_key

logger = logging.getLogger(__name__)

RRF_K = 60


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
        results_map: dict[str, dict] = {}

        if self.llm:
            try:
                vector, fingerprint = await self.llm.embed(query)
                vector_repo = PostgresVectorRepository(self.session)
                chunk_results = await vector_repo.search_code_chunks(
                    vector, fingerprint=fingerprint,
                    limit=limit * 2, repo_id=repo_id, language=language,
                )
                for rank, chunk in enumerate(chunk_results, start=1):
                    key = f"{chunk['file_path']}:{chunk['line_start']}"
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
                key = f"{file_path}:{sym.line_start}"
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

    async def lookup_symbol(self, name: str, file_path: str) -> dict | None:
        sym = (await self.session.execute(
            select(CodeSymbol).join(CodeFile).where(
                CodeSymbol.name == name, CodeFile.file_path == file_path,
            )
        )).scalars().first()
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

    async def get_code_graph(self, repo_id: UUID) -> dict:
        repo_id_str = str(repo_id)
        nodes: list[dict] = []
        edges: list[dict] = []

        file_rows = (await self.session.execute(
            text("SELECT file_path FROM code_files WHERE repo_id = :repo_id"),
            {"repo_id": repo_id_str},
        )).mappings().all()
        for row in file_rows:
            nodes.append({"id": row["file_path"], "label": row["file_path"], "kind": "file"})

        sym_rows = (await self.session.execute(
            text("""
                SELECT s.name, s.kind, f.file_path, p.name AS owner
                FROM code_symbols s
                JOIN code_files f ON f.id = s.file_id
                LEFT JOIN code_symbols p ON p.id = s.parent_symbol_id
                WHERE f.repo_id = :repo_id
            """),
            {"repo_id": repo_id_str},
        )).mappings().all()
        for row in sym_rows:
            node_id = compose_key("symbol", row["name"], row["file_path"], owner=row["owner"])
            nodes.append({"id": node_id, "label": row["name"], "kind": row["kind"], "file_path": row["file_path"]})

        aux_rows = (await self.session.execute(
            text("""
                SELECT key, kind, label, properties, properties->>'file_path' AS file_path
                FROM code_graph_nodes
                WHERE repo_id = :repo_id
            """),
            {"repo_id": repo_id_str},
        )).mappings().all()
        for row in aux_rows:
            node = {"id": row["key"], "label": row["label"] or row["key"], "kind": row["kind"]}
            if row["file_path"]:
                node["file_path"] = row["file_path"]
            if row["properties"]:
                node["properties"] = row["properties"]
            nodes.append(node)

        edge_rows = (await self.session.execute(
            text("""
                SELECT source_key, target_key, edge_type, properties
                FROM code_edges
                WHERE repo_id = :repo_id
                ORDER BY edge_type, (properties->>'step')::int NULLS LAST, source_key, target_key
            """),
            {"repo_id": repo_id_str},
        )).mappings().all()
        for row in edge_rows:
            edge = {"source": row["source_key"], "target": row["target_key"], "type": row["edge_type"]}
            props = row["properties"]
            if props:
                edge["properties"] = props
            edges.append(edge)

        return {"nodes": nodes, "edges": edges}

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
                SELECT DISTINCT name, kind, MIN(distance) AS distance
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

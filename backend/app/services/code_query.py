import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.code import CodeFile, CodeSymbol, Repository
from app.config import settings
from app.repositories.vector import PostgresVectorRepository
from app.services.community_detector import label_communities
from app.services.llm import LLMOrchestrator
from app.services.process_tracer import process_display_label
from app.services.rank_fusion import RankedList, rrf_fuse
from app.utils.graph_keys import compose_key, decompose_key, split_symbol_key

logger = logging.getLogger(__name__)

# How many same-named symbols a lookup reads at most; the candidate list of an
# ambiguous reference is bounded by the same number.
SYMBOL_LOOKUP_LIMIT = 50


class RepoNotFound(LookupError):
    """No repository carries this id or name."""


class RepoAmbiguous(LookupError):
    """More than one repository carries this name; `name` is not unique."""

    def __init__(self, reference: str, candidates: list[Repository]):
        super().__init__(f"repository reference {reference!r} is ambiguous")
        self.candidates = candidates


class SymbolAmbiguous(LookupError):
    """More than one symbol matches a reference that should name one."""

    def __init__(self, reference: str, candidates: list[dict]):
        super().__init__(
            f"symbol reference {reference!r} matches {len(candidates)} symbols; "
            "pass one of the candidate keys"
        )
        self.candidates = candidates


def _symbol_fields(sym: CodeSymbol, file_path: str) -> dict:
    return {
        "id": sym.id, "name": sym.name, "kind": sym.kind,
        "file_path": file_path, "line_start": sym.line_start, "line_end": sym.line_end,
        "signature": sym.signature, "docstring": sym.docstring,
        "visibility": sym.visibility, "source_code": sym.source_code,
        "summary": sym.summary, "enrichment_status": sym.enrichment_status,
    }


def _symbol_select():
    """Symbols with their file path, repository and owner name, one statement."""
    parent = aliased(CodeSymbol)
    stmt = (
        select(CodeSymbol, CodeFile.file_path, CodeFile.repo_id, parent.name)
        .join(CodeFile, CodeSymbol.file_id == CodeFile.id)
        .outerjoin(parent, CodeSymbol.parent_symbol_id == parent.id)
    )
    return stmt, parent


def symbol_candidate(row: dict) -> dict:
    return {
        "id": str(row["id"]), "key": row["key"], "name": row["name"],
        "kind": row["kind"], "file_path": row["file_path"],
        "repo_id": str(row["repo_id"]),
    }


class CodeSearchUnavailable(RuntimeError):
    """No arm of code search answered, so an empty list would read as no match."""


@dataclass(frozen=True)
class CodeSearchAnswer:
    """Fused hits plus the arms that raised, so a failed arm never reads as
    an arm that found nothing."""

    results: list[dict]
    failed_arms: tuple[str, ...] = ()
    # Why the vector arm was never attempted (no embedder, read-only), as
    # opposed to attempted and failed.
    semantic_skipped: str | None = None


def _code_hit_key(row: dict) -> tuple[str, str, int]:
    return (row["repo_id"], row["file_path"], row["line_start"])


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
    ) -> CodeSearchAnswer:
        lists: list[RankedList] = []
        failed: list[str] = []
        skipped: str | None = None
        if not self.llm:
            skipped = "no embedder is configured"
        elif settings.read_only:
            # A backup worker makes no external call by ruling, so the vector
            # arm is skipped outright rather than attempted and failed; the
            # ILIKE arm below still answers.
            skipped = "read-only instance"

        if skipped is None:
            try:
                vector, fingerprint = await self.llm.embed(query)
                async with self.session.begin_nested():
                    chunk_results = await PostgresVectorRepository(self.session).search_code_chunks(
                        vector, fingerprint=fingerprint,
                        limit=limit * 2, repo_id=repo_id, language=language,
                    )
                lists.append(RankedList("vector", rows=[
                    {
                        "chunk_content": chunk.get("chunk_content", ""),
                        "file_path": chunk.get("file_path", ""),
                        "repo_id": str(chunk.get("repo_id", "")),
                        "language": chunk.get("language"),
                        "symbol_name": chunk.get("symbol_name"),
                        "line_start": chunk.get("line_start", 0),
                        "line_end": chunk.get("line_end", 0),
                    }
                    for chunk in chunk_results
                ], weight=1.0))
            except Exception as e:
                logger.warning("Vector search failed: %s", e)
                failed.append("vector")

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
        try:
            async with self.session.begin_nested():
                text_results = (await self.session.execute(text_query)).all()
            lists.append(RankedList("keyword", rows=[
                {
                    "chunk_content": sym.source_code[:500] if sym.source_code else "",
                    "file_path": file_path,
                    "repo_id": str(rid),
                    "language": lang,
                    "symbol_name": sym.name,
                    "line_start": sym.line_start,
                    "line_end": sym.line_end,
                }
                for sym, file_path, rid, lang in text_results
            ], weight=1.0))
        except Exception as e:
            logger.warning("Text search failed: %s", e)
            failed.append("keyword")
            if skipped is not None or "vector" in failed:
                raise CodeSearchUnavailable(
                    "code search failed: the keyword arm raised and the vector arm "
                    + (f"did not run ({skipped})" if skipped else "failed")
                ) from e

        return CodeSearchAnswer(
            results=rrf_fuse(lists, limit, key=_code_hit_key),
            failed_arms=tuple(failed),
            semantic_skipped=skipped,
        )

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

    async def resolve_repo(self, name_or_id: str) -> Repository:
        try:
            repo_id = UUID(str(name_or_id))
        except ValueError:
            repo_id = None
        if repo_id is not None:
            repo = await self.session.get(Repository, repo_id)
            if repo is not None:
                return repo
        rows = (await self.session.execute(
            select(Repository)
            .where(Repository.name == name_or_id)
            .order_by(Repository.created_at, Repository.id)
        )).scalars().all()
        if not rows:
            raise RepoNotFound(name_or_id)
        if len(rows) > 1:
            raise RepoAmbiguous(name_or_id, list(rows))
        return rows[0]

    async def lookup_symbol(
        self,
        repo_id: UUID | None,
        name: str,
        file_path: str | None = None,
        owner: str | None = None,
        limit: int = SYMBOL_LOOKUP_LIMIT,
    ) -> list[dict]:
        """Symbols named ``name``, each with its file path, repository and
        owner-qualified graph ``key``, read in one statement."""
        stmt, parent = _symbol_select()
        stmt = stmt.where(CodeSymbol.name == name)
        if repo_id is not None:
            stmt = stmt.where(CodeFile.repo_id == repo_id)
        if file_path is not None:
            stmt = stmt.where(CodeFile.file_path == file_path)
        if owner:
            # Same-named methods under different classes in one file are only
            # distinguishable by their parent symbol (the owner segment of
            # the graph node key).
            stmt = stmt.where(parent.name == owner)
        return await self._symbol_rows(
            stmt.order_by(
                CodeFile.file_path, CodeSymbol.line_start, CodeSymbol.id,
            ).limit(max(1, limit))
        )

    async def _symbol_rows(self, stmt) -> list[dict]:
        return [
            {
                **_symbol_fields(sym, file_path_value),
                "repo_id": row_repo_id,
                "owner": owner_name,
                "key": compose_key(
                    "symbol", sym.name, file_path_value, owner=owner_name,
                ),
            }
            for sym, file_path_value, row_repo_id, owner_name in (
                await self.session.execute(stmt)
            ).all()
        ]

    async def symbols_in_file(self, repo_id: UUID, file_path: str) -> list[dict]:
        rows = (await self.session.execute(
            select(CodeSymbol)
            .join(CodeFile, CodeSymbol.file_id == CodeFile.id)
            .where(CodeFile.repo_id == repo_id, CodeFile.file_path == file_path)
            .order_by(CodeSymbol.line_start, CodeSymbol.id)
        )).scalars().all()
        return [
            {
                "id": str(sym.id), "name": sym.name, "kind": sym.kind,
                "line_start": sym.line_start, "line_end": sym.line_end,
                "signature": sym.signature, "summary": sym.summary,
                "visibility": sym.visibility,
            }
            for sym in rows
        ]

    async def resolve_symbol(
        self, reference: str, repo_id: UUID | None = None,
    ) -> dict | None:
        """One symbol from an id, a graph key or a bare name.

        A key without an owner segment names a top-level symbol when exactly
        one such symbol exists; otherwise every match is a candidate. More
        than one candidate raises :class:`SymbolAmbiguous`.
        """
        if "::" in reference:
            name, file_path, owner = split_symbol_key(reference)
            rows = await self.lookup_symbol(repo_id, name, file_path, owner)
            if not owner:
                top_level = [row for row in rows if row["owner"] is None]
                if len(top_level) == 1:
                    rows = top_level
        else:
            try:
                symbol_id = UUID(reference)
            except ValueError:
                rows = await self.lookup_symbol(repo_id, reference)
            else:
                rows = await self._symbol_by_id(symbol_id, repo_id)
        if not rows:
            return None
        if len(rows) > 1:
            raise SymbolAmbiguous(reference, [symbol_candidate(row) for row in rows])
        return rows[0]

    async def _symbol_by_id(
        self, symbol_id: UUID, repo_id: UUID | None,
    ) -> list[dict]:
        stmt, _parent = _symbol_select()
        stmt = stmt.where(CodeSymbol.id == symbol_id)
        if repo_id is not None:
            stmt = stmt.where(CodeFile.repo_id == repo_id)
        return await self._symbol_rows(stmt)

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
                "indexed_at": f.indexed_at,
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
            return await self._relabel(repo_id, await self._symbol_graph(repo_id, None))

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
        await self._relabel(repo_id, graph)
        graph.update({
            "level": chosen,
            "requested_level": requested,
            "scope": scope,
            "auto_limit": CODE_GRAPH_AUTO_LIMIT,
        })
        return graph

    async def _relabel(self, repo_id: UUID, graph: dict) -> dict:
        """Readable, distinct names for process and community nodes.

        Both are derived at read time so a graph indexed before the labels
        were fixed reads the same as a fresh one: a process key's
        entry-kind prefix is dropped, and every community of the repo is
        labelled together (never only the ones in scope), so a label is
        distinct and does not change as the user drills in.
        """
        communities = [n for n in graph["nodes"] if n.get("kind") == "community"]
        for node in graph["nodes"]:
            if node.get("kind") == "process":
                node["label"] = process_display_label(node["id"])
        if not communities:
            return graph
        rows = (await self.session.execute(
            text("""
                SELECT target_key, split_part(source_key, '::', 2) AS file_path, count(*) AS n
                FROM code_edges
                WHERE repo_id = :repo_id AND edge_type = 'member_of'
                GROUP BY 1, 2
            """),
            {"repo_id": str(repo_id)},
        )).mappings().all()
        members: dict[str, list[str]] = {}
        for row in rows:
            members.setdefault(row["target_key"], []).extend([row["file_path"]] * row["n"])
        labels = label_communities(members)
        for node in communities:
            if node["id"] in labels:
                node["label"] = labels[node["id"]]
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

    async def calculate_blast_radius(
        self, symbol_id: str, max_depth: int = 10, repo_id: UUID | None = None,
    ) -> dict | None:
        """Every symbol that transitively reaches ``symbol_id``.

        ``symbol_id`` is an id, a graph key or a bare name; it resolves inside
        ``repo_id`` when one is given and raises :class:`SymbolAmbiguous` when
        it names more than one symbol.
        """
        sym = await self.resolve_symbol(symbol_id, repo_id)
        if sym is None:
            return None

        repo_id_str = str(sym["repo_id"])
        symbol_key = sym["key"]
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
            "symbol": {"id": str(sym["id"]), "name": sym["name"], "file_path": sym["file_path"]},
            "affected": affected,
            "by_depth": by_depth,
            "risk": risk,
            "total": len(affected),
        }

    async def symbol_context(
        self, symbol_name: str, repo_id: UUID | None = None,
    ) -> dict | None:
        """Callers, callees, heritage, community and processes of one symbol."""
        sym = await self.resolve_symbol(symbol_name, repo_id)
        if sym is None:
            return None
        params = {"repo_id": str(sym["repo_id"]), "symbol_key": sym["key"]}

        async def keys(column: str, match: str, edge_type: str) -> list[str]:
            rows = (await self.session.execute(
                text(f"""
                    SELECT {column} AS key FROM code_edges
                    WHERE repo_id = :repo_id
                      AND {match} = :symbol_key
                      AND edge_type = :edge_type
                """),
                {**params, "edge_type": edge_type},
            )).mappings().all()
            return [row["key"] for row in rows]

        def named(raw_keys: list[str]) -> list[dict]:
            out = []
            for raw in raw_keys:
                name_val, fp_val = raw, None
                if "::" in (raw or ""):
                    name_val, fp_val = decompose_key("symbol", raw)
                out.append({"name": name_val, "file_path": fp_val})
            return out

        community_row = (await self.session.execute(
            text("""
                SELECT n.key, n.label
                FROM code_edges e
                JOIN code_graph_nodes n ON n.key = e.target_key AND n.repo_id = e.repo_id
                WHERE e.repo_id = :repo_id
                  AND e.source_key = :symbol_key
                  AND e.edge_type = 'member_of'
                  AND n.kind = 'community'
                LIMIT 1
            """),
            params,
        )).mappings().first()
        process_rows = (await self.session.execute(
            text("""
                SELECT n.label
                FROM code_edges e
                JOIN code_graph_nodes n ON n.key = e.target_key AND n.repo_id = e.repo_id
                WHERE e.repo_id = :repo_id
                  AND e.source_key = :symbol_key
                  AND e.edge_type = 'step_in_process'
                  AND n.kind = 'process'
            """),
            params,
        )).mappings().all()

        return {
            "symbol": {
                "name": sym["name"],
                "kind": sym["kind"],
                "file_path": sym["file_path"],
                "signature": sym["signature"],
                "summary": sym["summary"],
            },
            "callers": named(await keys("source_key", "target_key", "calls")),
            "callees": named(await keys("target_key", "source_key", "calls")),
            "heritage": {
                "extends": [
                    key.split("::")[0]
                    for key in await keys("target_key", "source_key", "extends")
                ],
                "extended_by": [
                    key.split("::")[0]
                    for key in await keys("source_key", "target_key", "extends")
                ],
                "implements": [
                    key.split("::")[0]
                    for key in await keys("target_key", "source_key", "implements")
                ],
            },
            "accesses": [],
            "processes": [process_display_label(row["label"]) for row in process_rows],
            "community": (
                {"label": community_row["label"], "key": community_row["key"]}
                if community_row else None
            ),
        }

    async def import_edges(
        self, repo_id: UUID, file_path: str | None = None,
    ) -> list[dict]:
        file_filter = " AND source_key = :file_path" if file_path else ""
        params: dict = {"repo_id": str(repo_id)}
        if file_path:
            params["file_path"] = file_path
        rows = (await self.session.execute(
            text(f"""
                SELECT source_key AS file, target_key AS module
                FROM code_edges
                WHERE repo_id = :repo_id
                  AND edge_type = 'imports'
                  {file_filter}
            """),
            params,
        )).mappings().all()
        return [{"file": row["file"], "module": row["module"]} for row in rows]

    async def communities(self, repo_id: UUID) -> list[dict]:
        rows = (await self.session.execute(
            text("""
                SELECT key, label, properties
                FROM code_graph_nodes
                WHERE repo_id = :repo_id AND kind = 'community'
                ORDER BY label
            """),
            {"repo_id": str(repo_id)},
        )).mappings().all()
        return [
            {
                "key": row["key"],
                "label": row["label"],
                "size": (row["properties"] or {}).get("size"),
            }
            for row in rows
        ]

    async def processes(self, repo_id: UUID) -> list[dict]:
        """Each traced process with its steps, in two statements."""
        nodes = (await self.session.execute(
            text("""
                SELECT key, label, properties
                FROM code_graph_nodes
                WHERE repo_id = :repo_id AND kind = 'process'
                ORDER BY label
            """),
            {"repo_id": str(repo_id)},
        )).mappings().all()
        if not nodes:
            return []
        step_rows = (await self.session.execute(
            text("""
                SELECT target_key, source_key
                FROM code_edges
                WHERE repo_id = :repo_id
                  AND edge_type = 'step_in_process'
                  AND target_key = ANY(CAST(:keys AS text[]))
                ORDER BY target_key, properties -> 'step', source_key
            """),
            {"repo_id": str(repo_id), "keys": [node["key"] for node in nodes]},
        )).mappings().all()
        steps: dict[str, list[str]] = {}
        for row in step_rows:
            steps.setdefault(row["target_key"], []).append(
                row["source_key"].split("::")[0]
            )
        return [
            {
                "name": process_display_label(node["key"]),
                "kind": (node["properties"] or {}).get("entry_kind"),
                "entry_file": (node["properties"] or {}).get("entry_file"),
                "steps": steps.get(node["key"], []),
            }
            for node in nodes
        ]

    async def symbols_in_files(
        self, repo_id: UUID, file_paths: list[str],
    ) -> list[dict]:
        rows = (await self.session.execute(
            select(CodeSymbol.name, CodeSymbol.kind, CodeSymbol.line_start, CodeFile.file_path)
            .join(CodeFile, CodeSymbol.file_id == CodeFile.id)
            .where(CodeFile.repo_id == repo_id, CodeFile.file_path.in_(file_paths))
            .order_by(CodeFile.file_path, CodeSymbol.line_start, CodeSymbol.id)
        )).all()
        return [
            {"name": name, "kind": kind, "file_path": path, "line_start": line}
            for name, kind, line, path in rows
        ]

    async def rename_references(
        self, repo_id: UUID, symbol_name: str,
    ) -> list[dict] | None:
        """Every definition of and reference to ``symbol_name``, most certain
        first, or None when no symbol of that name is defined."""
        definitions = (await self.session.execute(
            select(CodeSymbol.line_start, CodeSymbol.kind, CodeFile.file_path)
            .join(CodeFile, CodeSymbol.file_id == CodeFile.id)
            .where(CodeFile.repo_id == repo_id, CodeSymbol.name == symbol_name)
        )).all()
        if not definitions:
            return None
        references: list[dict] = [
            {
                "file_path": path, "line": line, "kind": "definition",
                "symbol_kind": kind, "confidence": 1.0,
            }
            for line, kind, path in definitions
        ]

        # A prefix compare, not LIKE: `_` and `%` are ordinary characters in
        # a symbol name.
        prefix = f"{symbol_name}::"
        edge_rows = (await self.session.execute(
            text("""
                SELECT source_key, edge_type, properties
                FROM code_edges
                WHERE repo_id = :repo_id
                  AND edge_type IN ('calls', 'extends', 'implements', 'imports')
                  AND (
                    target_key = :name
                    OR (edge_type <> 'imports'
                        AND left(target_key, :prefix_len) = :prefix)
                  )
            """),
            {
                "repo_id": str(repo_id), "name": symbol_name,
                "prefix": prefix, "prefix_len": len(prefix),
            },
        )).mappings().all()
        for row in edge_rows:
            source = row["source_key"]
            if row["edge_type"] == "imports":
                references.append({
                    "file_path": source, "line": 0, "kind": "import",
                    "confidence": 0.8,
                })
                continue
            name, path = (
                decompose_key("symbol", source) if "::" in source else (source, None)
            )
            if row["edge_type"] == "calls":
                properties = row["properties"] or {}
                references.append({
                    "file_path": path, "line": properties.get("line"),
                    "kind": "call", "caller": name,
                    "confidence": properties.get("confidence", 0.5),
                })
            else:
                references.append({
                    "file_path": path, "line": None, "kind": "heritage",
                    "symbol": name, "confidence": 0.95,
                })

        references.sort(key=lambda ref: (
            -ref.get("confidence", 0), ref.get("file_path") or "", ref.get("line") or 0,
        ))
        return references

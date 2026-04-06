from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import CodeFile, CodeSymbol, Repository
from app.services.code_parser import (
    ExtractedCall, ExtractedHeritage, ExtractedProperty, ExtractedRoute,
    ExtractedSymbol, parse_file,
)
from app.services.llm import LLMOrchestrator
from app.services.repo_manager import RepoManager
from app.services.type_env import build_type_env, propagate_types
from app.services.heritage_resolver import HeritageResolver, AccessResolver
from app.repositories.graph import Neo4jGraphRepository
from app.repositories.vector import QdrantVectorRepository

logger = logging.getLogger(__name__)

IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", "target", "bin", "obj",
}
IGNORED_EXTENSIONS = {
    ".lock", ".min.js", ".min.css", ".map", ".wasm",
    ".pyc", ".pyo", ".exe", ".dll", ".so", ".dylib",
}
MAX_FILE_SIZE = 500_000
PARALLEL_BATCH = 10


class CodeIndexer:
    def __init__(
        self,
        session: AsyncSession,
        llm: LLMOrchestrator | None = None,
        vector_repo: QdrantVectorRepository | None = None,
        graph_repo: Neo4jGraphRepository | None = None,
    ) -> None:
        self.session = session
        self.llm = llm
        self.vector_repo = vector_repo
        self.graph_repo = graph_repo
        self.repo_manager = RepoManager(session)

    async def index_repo(self, repo_id: UUID, full: bool = False) -> dict:
        repo = await self.repo_manager.get(repo_id)
        if not repo:
            raise ValueError(f"Repository {repo_id} not found")

        new_sha = await self.repo_manager.pull_repo(repo)
        if new_sha is None:
            work_dir = self.repo_manager.repo_working_dir(repo)
            if not work_dir.exists():
                raise RuntimeError(f"Working directory does not exist for repo {repo_id}")
            result = await RepoManager._run_git(work_dir, ["git", "rev-parse", "HEAD"])
            new_sha = result.strip()

        old_sha = repo.last_indexed_commit

        if old_sha == new_sha and not full:
            if repo.status != "ready":
                repo.status = "ready"
                repo.status_message = None
                await self.session.flush()
            return {"status": "up_to_date", "commit": new_sha}

        work_dir = self.repo_manager.repo_working_dir(repo)

        if full or not old_sha:
            changed_files = self._list_all_files(work_dir)
            deleted_files: list[str] = []
            await self._delete_all_repo_data(repo.id)
        else:
            changed_files, deleted_files = await self._diff_files(work_dir, old_sha, new_sha)

        from app.api.websocket import event_manager

        repo.status = "indexing"
        repo.status_message = f"Indexing {len(changed_files)} files..."
        await self.session.commit()

        total_files = len(changed_files)
        await event_manager.broadcast("repo.indexing_started", {"repo_id": str(repo.id), "total_files": total_files})

        stats = {
            "status": "indexed",
            "commit": new_sha,
            "files_changed": 0,
            "files_deleted": 0,
            "files_skipped": 0,
            "symbols_indexed": 0,
            "chunks_stored": 0,
            "calls_resolved": 0,
            "errors": [],
        }

        all_calls: dict[str, list[ExtractedCall]] = {}
        all_file_paths: list[str] = []
        all_imports: dict[str, list[str]] = {}

        for rel_path in deleted_files:
            try:
                await self._delete_file_data(repo.id, rel_path)
                stats["files_deleted"] += 1
            except Exception as exc:
                logger.error("Error deleting data for %s: %s", rel_path, exc)
                stats["errors"].append(f"delete:{rel_path}:{exc}")

        for batch_start in range(0, total_files, PARALLEL_BATCH):
            batch_end = min(batch_start + PARALLEL_BATCH, total_files)
            batch = changed_files[batch_start:batch_end]

            repo.status_message = f"Parsing files {batch_start + 1}-{batch_end}/{total_files}..."
            await self.session.commit()
            await event_manager.broadcast("repo.indexing_progress", {
                "repo_id": str(repo.id), "current": batch_start, "total": total_files,
                "file_path": f"Batch {batch_start // PARALLEL_BATCH + 1}",
            })

            # _parse_file_async does NOT touch self.session.
            # _store_parsed_file DOES use self.session and MUST run sequentially.
            tasks = [self._parse_file_async(work_dir, fp, repo.id) for fp in batch]
            parsed_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(parsed_results):
                rel_path = batch[i]

                if isinstance(result, Exception):
                    logger.error("Error parsing %s: %s", rel_path, result)
                    stats["errors"].append(f"parse:{rel_path}:{result}")
                    continue

                if result is None:
                    stats["files_skipped"] += 1
                    continue

                try:
                    store_result = await self._store_parsed_file(repo, result)
                    if store_result:
                        stats["files_changed"] += 1
                        stats["symbols_indexed"] += store_result.get("symbols", 0)
                        stats["chunks_stored"] += store_result.get("chunks", 0)
                        if store_result.get("calls"):
                            all_calls[rel_path] = store_result["calls"]
                            all_file_paths.append(rel_path)
                        if store_result.get("imports"):
                            all_imports[rel_path] = store_result["imports"]
                    else:
                        stats["files_skipped"] += 1
                except Exception as exc:
                    logger.error("Error storing %s: %s", rel_path, exc)
                    stats["errors"].append(f"store:{rel_path}:{exc}")

            await self.session.commit()

        if self.graph_repo and all_calls:
            repo.status_message = "Resolving function calls..."
            await self.session.commit()
            await event_manager.broadcast("repo.indexing_progress", {
                "repo_id": str(repo.id), "current": total_files, "total": total_files,
                "file_path": "Resolving calls...",
            })
            calls_created = await self._resolve_calls(repo, all_calls, all_file_paths, all_imports)
            stats["calls_resolved"] = calls_created

        # Phase 3: Heritage resolution + type-based edges
        if self.graph_repo:
            repo.status_message = "Resolving inheritance and type relationships..."
            await self.session.commit()
            await event_manager.broadcast("repo.indexing_progress", {
                "repo_id": str(repo.id), "current": total_files, "total": total_files,
                "file_path": "Resolving types...",
            })

            heritage_resolver = HeritageResolver(self.graph_repo, str(repo.id))
            heritage_result = await heritage_resolver.resolve_all()
            stats["method_overrides"] = heritage_result["overrides"]
            stats["method_implements"] = heritage_result["implements"]

            if all_calls:
                work_dir = self.repo_manager.repo_working_dir(repo)
                type_envs = {}
                member_calls = {}
                for file_path, calls in all_calls.items():
                    member = [c for c in calls if c.call_form == "member"]
                    if member:
                        member_calls[file_path] = member
                        full_path = work_dir / file_path
                        if full_path.is_file():
                            try:
                                content = full_path.read_text(encoding="utf-8", errors="replace")
                                from app.services.code_parser import detect_language, _get_language
                                lang = detect_language(file_path)
                                if lang:
                                    lang_obj = _get_language(lang)
                                    if lang_obj:
                                        from tree_sitter import Parser, Language
                                        p = Parser(lang_obj if isinstance(lang_obj, Language) else Language(lang_obj))
                                        tree = p.parse(content.encode("utf-8"))
                                        type_envs[file_path] = build_type_env(tree, content.encode("utf-8"), lang, file_path)
                            except Exception as e:
                                logger.debug("Failed to build type env for %s: %s", file_path, e)

                if type_envs and all_imports:
                    from app.services.call_resolver import build_import_map as _build_import_map
                    phase3_import_map = _build_import_map(list(type_envs.keys()), all_imports)
                    propagate_types(type_envs, phase3_import_map)

                if member_calls and type_envs:
                    access_resolver = AccessResolver(self.graph_repo, str(repo.id))
                    accesses = await access_resolver.resolve(type_envs, member_calls)
                    stats["accesses"] = accesses

        # Phase 4: Community detection + process tracing
        if self.graph_repo:
            repo.status_message = "Detecting communities and tracing execution flows..."
            await self.session.commit()

            from app.services.community_detector import CommunityDetector
            from app.services.process_tracer import ProcessTracer

            detector = CommunityDetector(self.graph_repo, str(repo.id))
            stats["communities"] = await detector.detect()

            tracer = ProcessTracer(self.graph_repo, str(repo.id))
            stats["processes"] = await tracer.trace()

        repo.last_indexed_commit = new_sha
        repo.last_indexed_at = datetime.now(timezone.utc)
        repo.status = "ready"
        repo.status_message = None
        await self.session.commit()

        await event_manager.broadcast("repo.indexing_completed", {"repo_id": str(repo.id), "files_changed": stats["files_changed"], "symbols_indexed": stats["symbols_indexed"]})

        logger.info(
            "Indexed %s: %d changed, %d skipped, %d deleted, %d symbols, %d errors",
            repo.name, stats["files_changed"], stats["files_skipped"],
            stats["files_deleted"], stats["symbols_indexed"], len(stats["errors"]),
        )

        return stats

    async def _index_file(
        self, repo: Repository, work_dir: Path, rel_path: str
    ) -> dict | None:
        full_path = work_dir / rel_path
        if not full_path.is_file():
            return None

        try:
            size = full_path.stat().st_size
        except OSError:
            return None

        if size > MAX_FILE_SIZE:
            return None

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        existing = (
            await self.session.execute(
                select(CodeFile).where(
                    CodeFile.repo_id == repo.id,
                    CodeFile.file_path == rel_path,
                )
            )
        ).scalar_one_or_none()

        if existing and existing.content_hash == content_hash:
            return None

        if existing:
            await self._delete_file_data(repo.id, rel_path)

        parse_result = parse_file(rel_path, content)
        if parse_result is None:
            return None

        code_file = CodeFile(
            id=uuid4(),
            repo_id=repo.id,
            file_path=rel_path,
            language=parse_result.language,
            content_hash=content_hash,
        )
        self.session.add(code_file)
        await self.session.flush()

        symbol_count = 0
        symbol_map: dict[str, UUID] = {}
        for sym in parse_result.symbols:
            symbol_count += self._store_symbol(code_file, sym, None, symbol_map)

        await self.session.flush()

        chunk_count = 0
        if parse_result.chunks and self.llm and self.vector_repo:
            chunk_count = await self._store_chunks(
                repo.id, rel_path, parse_result.language, parse_result.chunks
            )

        if self.graph_repo:
            await self._store_graph(
                repo, rel_path, parse_result.symbols, parse_result.imports,
                heritage=parse_result.heritage,
                properties=parse_result.properties,
                routes=parse_result.routes,
            )

        return {
            "symbols": symbol_count,
            "chunks": chunk_count,
            "calls": parse_result.calls,
            "imports": [imp.source for imp in parse_result.imports],
            "heritage": len(parse_result.heritage),
            "properties": len(parse_result.properties),
            "routes": len(parse_result.routes),
        }

    async def _parse_file_async(
        self, work_dir: Path, rel_path: str, repo_id: UUID,
    ) -> dict | None:
        """Parse a file and generate embeddings without touching the database."""
        full_path = work_dir / rel_path
        if not full_path.is_file():
            return None

        try:
            size = full_path.stat().st_size
        except OSError:
            return None

        if size > MAX_FILE_SIZE:
            return None

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        parse_result = parse_file(rel_path, content)
        if not parse_result:
            return None

        vectors: list = []
        if parse_result.chunks and self.llm:
            texts = [c["content"][:2000] for c in parse_result.chunks]
            try:
                vectors = await self.llm.embed_batch(texts)
            except Exception as exc:
                logger.warning("Batch embedding failed for %s: %s", rel_path, exc)

        return {
            "rel_path": rel_path,
            "content_hash": content_hash,
            "parse_result": parse_result,
            "vectors": vectors,
        }

    async def _store_parsed_file(
        self, repo: Repository, parsed: dict,
    ) -> dict | None:
        """Store a pre-parsed file's data to PostgreSQL, Qdrant, and Neo4j."""
        rel_path = parsed["rel_path"]
        content_hash = parsed["content_hash"]
        parse_result = parsed["parse_result"]
        vectors = parsed["vectors"]

        existing = (
            await self.session.execute(
                select(CodeFile).where(
                    CodeFile.repo_id == repo.id,
                    CodeFile.file_path == rel_path,
                )
            )
        ).scalar_one_or_none()

        if existing and existing.content_hash == content_hash:
            return None

        if existing:
            await self._delete_file_data(repo.id, rel_path)

        code_file = CodeFile(
            id=uuid4(),
            repo_id=repo.id,
            file_path=rel_path,
            language=parse_result.language,
            content_hash=content_hash,
        )
        self.session.add(code_file)
        await self.session.flush()

        symbol_count = 0
        symbol_map: dict[str, UUID] = {}
        for sym in parse_result.symbols:
            symbol_count += self._store_symbol(code_file, sym, None, symbol_map)

        chunk_count = 0
        if vectors and parse_result.chunks and self.vector_repo:
            from qdrant_client.models import PointStruct

            points = []
            for chunk, vector in zip(parse_result.chunks, vectors):
                points.append(PointStruct(
                    id=str(uuid4()),
                    vector=vector,
                    payload={
                        "repo_id": str(repo.id),
                        "file_path": rel_path,
                        "language": parse_result.language,
                        "symbol_name": chunk.get("symbol_name"),
                        "chunk_content": chunk["content"][:5000],
                        "line_start": chunk["line_start"],
                        "line_end": chunk["line_end"],
                    },
                ))
            if points:
                await self.vector_repo.client.upsert(
                    collection_name="code_chunks", points=points,
                )
                chunk_count = len(points)

        if self.graph_repo:
            await self._store_graph(
                repo, rel_path, parse_result.symbols, parse_result.imports,
                heritage=parse_result.heritage,
                properties=parse_result.properties,
                routes=parse_result.routes,
            )

        return {
            "symbols": symbol_count,
            "chunks": chunk_count,
            "calls": parse_result.calls,
            "imports": [imp.source for imp in parse_result.imports],
        }

    def _store_symbol(
        self,
        code_file: CodeFile,
        sym: ExtractedSymbol,
        parent_id: UUID | None,
        symbol_map: dict[str, UUID],
    ) -> int:
        is_exported = sym.visibility not in ("private",) if sym.visibility else True
        if is_exported:
            priority = 2
        elif sym.kind in ("class", "struct", "interface", "trait", "enum", "impl"):
            priority = 1
        else:
            priority = 0

        symbol_id = uuid4()
        symbol = CodeSymbol(
            id=symbol_id,
            file_id=code_file.id,
            name=sym.name,
            kind=sym.kind,
            line_start=sym.line_start,
            line_end=sym.line_end,
            signature=sym.signature,
            docstring=sym.docstring,
            visibility=sym.visibility,
            parent_symbol_id=parent_id,
            source_code=sym.source_code,
            enrichment_priority=priority,
        )
        self.session.add(symbol)
        symbol_map[sym.name] = symbol_id

        count = 1
        for child in sym.children:
            count += self._store_symbol(code_file, child, symbol_id, symbol_map)
        return count

    async def _store_chunks(
        self,
        repo_id: UUID,
        file_path: str,
        language: str,
        chunks: list[dict],
    ) -> int:
        from qdrant_client.models import PointStruct

        texts = [c["content"][:2000] for c in chunks]
        try:
            vectors = await self.llm.embed_batch(texts)
        except Exception as exc:
            logger.warning("Batch embedding failed for %s: %s", file_path, exc)
            return 0

        points = []
        for chunk, vector in zip(chunks, vectors):
            points.append(PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload={
                    "repo_id": str(repo_id),
                    "file_path": file_path,
                    "language": language,
                    "symbol_name": chunk.get("symbol_name"),
                    "chunk_content": chunk["content"][:5000],
                    "line_start": chunk["line_start"],
                    "line_end": chunk["line_end"],
                },
            ))

        if points:
            await self.vector_repo.client.upsert(
                collection_name="code_chunks", points=points
            )
        return len(points)

    async def _store_graph(
        self,
        repo: Repository,
        file_path: str,
        symbols: list[ExtractedSymbol],
        imports: list,
        heritage: list[ExtractedHeritage] | None = None,
        properties: list[ExtractedProperty] | None = None,
        routes: list[ExtractedRoute] | None = None,
    ) -> None:
        sym_data = []
        contains_data = []

        def collect(sym, parent_name=None):
            sym_data.append({
                "name": sym.name,
                "kind": sym.kind,
                "line_start": sym.line_start,
                "line_end": sym.line_end,
                "visibility": sym.visibility,
            })
            if parent_name:
                contains_data.append({"parent": parent_name, "child": sym.name})
            for child in sym.children:
                collect(child, sym.name)

        for sym in symbols:
            collect(sym)

        async with self.graph_repo.driver.session() as neo_session:
            await neo_session.run(
                "MERGE (f:CodeFile {repo_id: $repo_id, file_path: $file_path})",
                repo_id=str(repo.id), file_path=file_path,
            )

            if sym_data:
                await neo_session.run(
                    """
                    UNWIND $symbols AS sym
                    MERGE (f:CodeFile {repo_id: $repo_id, file_path: $file_path})
                    MERGE (s:CodeSymbol {repo_id: $repo_id, file_path: $file_path, name: sym.name})
                    ON CREATE SET s.kind = sym.kind, s.line_start = sym.line_start,
                                  s.line_end = sym.line_end, s.visibility = sym.visibility
                    ON MATCH SET s.kind = sym.kind, s.line_start = sym.line_start,
                                 s.line_end = sym.line_end, s.visibility = sym.visibility
                    MERGE (f)-[:DEFINES]->(s)
                    """,
                    repo_id=str(repo.id), file_path=file_path, symbols=sym_data,
                )

            if contains_data:
                await neo_session.run(
                    """
                    UNWIND $pairs AS pair
                    MATCH (p:CodeSymbol {repo_id: $repo_id, file_path: $file_path, name: pair.parent})
                    MATCH (c:CodeSymbol {repo_id: $repo_id, file_path: $file_path, name: pair.child})
                    MERGE (p)-[:CONTAINS]->(c)
                    """,
                    repo_id=str(repo.id), file_path=file_path, pairs=contains_data,
                )

            if imports:
                import_data = [{"source": imp.source, "names": imp.names} for imp in imports]
                await neo_session.run(
                    """
                    UNWIND $imports AS imp
                    MERGE (f:CodeFile {repo_id: $repo_id, file_path: $file_path})
                    MERGE (m:Module {name: imp.source})
                    MERGE (f)-[:IMPORTS]->(m)
                    """,
                    repo_id=str(repo.id), file_path=file_path, imports=import_data,
                )

            await neo_session.run(
                """
                MERGE (f:CodeFile {repo_id: $repo_id, file_path: $file_path})
                MERGE (r:Repository {id: $repo_id})
                MERGE (r)-[:DEFINES]->(f)
                """,
                repo_id=str(repo.id), file_path=file_path, repo_name=repo.name,
            )

            # HAS_METHOD edges (class → method children)
            method_data = []
            for sym in symbols:
                if sym.kind in ("class", "struct", "interface", "trait"):
                    for child in sym.children:
                        if child.kind in ("method", "function"):
                            method_data.append({"parent": sym.name, "child": child.name})

            if method_data:
                await neo_session.run(
                    """
                    UNWIND $pairs AS pair
                    MATCH (p:CodeSymbol {repo_id: $repo_id, file_path: $file_path, name: pair.parent})
                    MATCH (c:CodeSymbol {repo_id: $repo_id, file_path: $file_path, name: pair.child})
                    MERGE (p)-[:HAS_METHOD]->(c)
                    """,
                    repo_id=str(repo.id), file_path=file_path, pairs=method_data,
                )

            # EXTENDS / IMPLEMENTS edges
            if heritage:
                extends_data = [{"child": h.symbol_name, "parent": h.base_name} for h in heritage if h.relation == "extends"]
                impl_data = [{"child": h.symbol_name, "parent": h.base_name} for h in heritage if h.relation == "implements"]

                if extends_data:
                    await neo_session.run(
                        """
                        UNWIND $pairs AS pair
                        MATCH (child:CodeSymbol {repo_id: $repo_id, file_path: $file_path, name: pair.child})
                        MATCH (parent:CodeSymbol {repo_id: $repo_id, name: pair.parent})
                        MERGE (child)-[:EXTENDS]->(parent)
                        """,
                        repo_id=str(repo.id), file_path=file_path, pairs=extends_data,
                    )

                if impl_data:
                    await neo_session.run(
                        """
                        UNWIND $pairs AS pair
                        MATCH (child:CodeSymbol {repo_id: $repo_id, file_path: $file_path, name: pair.child})
                        MATCH (parent:CodeSymbol {repo_id: $repo_id, name: pair.parent})
                        MERGE (child)-[:IMPLEMENTS]->(parent)
                        """,
                        repo_id=str(repo.id), file_path=file_path, pairs=impl_data,
                    )

            # Property nodes + HAS_PROPERTY edges
            if properties:
                prop_data = [{"name": p.name, "owner": p.owner_name, "type_ann": p.type_annotation, "line": p.line, "vis": p.visibility} for p in properties]
                await neo_session.run(
                    """
                    UNWIND $props AS prop
                    MERGE (p:Property {repo_id: $repo_id, file_path: $file_path, name: prop.name, owner: prop.owner})
                    ON CREATE SET p.type_annotation = prop.type_ann, p.line = prop.line, p.visibility = prop.vis
                    WITH p, prop
                    MATCH (cls:CodeSymbol {repo_id: $repo_id, file_path: $file_path, name: prop.owner})
                    MERGE (cls)-[:HAS_PROPERTY]->(p)
                    """,
                    repo_id=str(repo.id), file_path=file_path, props=prop_data,
                )

            # Route / Tool nodes + edges
            if routes:
                for route in routes:
                    if route.kind == "route":
                        await neo_session.run(
                            """
                            MERGE (r:Route {repo_id: $repo_id, path: $path, method: $method})
                            ON CREATE SET r.framework = $framework
                            MERGE (f:CodeFile {repo_id: $repo_id, file_path: $file_path})
                            MERGE (f)-[:HANDLES_ROUTE]->(r)
                            """,
                            repo_id=str(repo.id), file_path=file_path,
                            path=route.path, method=route.method, framework=route.framework,
                        )
                    elif route.kind == "tool":
                        await neo_session.run(
                            """
                            MERGE (t:Tool {repo_id: $repo_id, name: $name})
                            ON CREATE SET t.framework = $framework
                            MERGE (f:CodeFile {repo_id: $repo_id, file_path: $file_path})
                            MERGE (f)-[:HANDLES_TOOL]->(t)
                            """,
                            repo_id=str(repo.id), file_path=file_path,
                            name=route.path, framework=route.framework,
                        )

    async def _resolve_calls(
        self,
        repo: Repository,
        all_calls: dict[str, list[ExtractedCall]],
        all_file_paths: list[str],
        all_imports: dict[str, list[str]],
    ) -> int:
        from app.services.call_resolver import CallResolver, build_import_map, build_named_imports, build_wildcard_imports
        from app.services.code_parser import extract_return_type_from_signature
        from app.services.symbol_table import SymbolEntry, SymbolTable

        rows = (await self.session.execute(
            select(CodeSymbol, CodeFile.file_path)
            .join(CodeFile)
            .where(CodeFile.repo_id == repo.id)
        )).all()

        symbol_table = SymbolTable()
        symbol_by_id: dict[str, tuple] = {}

        for sym, file_path in rows:
            param_count = None
            if sym.signature:
                params = sym.signature.strip("()").split(",")
                param_count = len([p for p in params if p.strip()]) if params != [""] else 0

            return_type = extract_return_type_from_signature(sym.signature, sym.source_code)

            symbol_table.add(SymbolEntry(
                node_id=str(sym.id),
                file_path=file_path,
                name=sym.name,
                kind=sym.kind,
                param_count=param_count,
                owner_id=str(sym.parent_symbol_id) if sym.parent_symbol_id else None,
                return_type=return_type,
            ))
            symbol_by_id[str(sym.id)] = (sym, file_path)

        enclosing_index: dict[str, list[tuple[int, int, str]]] = {}
        for sym, file_path in rows:
            if sym.kind in ("function", "method"):
                enclosing_index.setdefault(file_path, []).append(
                    (sym.line_start, sym.line_end, sym.name)
                )
        for fp in enclosing_index:
            enclosing_index[fp].sort(key=lambda x: x[0], reverse=True)

        import_map = build_import_map(all_file_paths, all_imports)
        named_imports = build_named_imports(all_imports, all_file_paths)
        wildcard_imports = build_wildcard_imports(all_imports, all_file_paths)
        resolver = CallResolver(symbol_table, import_map, named_imports=named_imports, wildcard_imports=wildcard_imports)
        call_edges = []

        for file_path, calls in all_calls.items():
            for call in calls:
                result = resolver.resolve(call, file_path)
                if not result:
                    continue

                target_id, confidence = result

                enclosing_name = None
                for start, end, name in enclosing_index.get(file_path, []):
                    if start <= call.line <= end:
                        enclosing_name = name
                        break

                if not enclosing_name:
                    continue

                target_entry = symbol_by_id.get(target_id)
                if not target_entry:
                    continue

                target_sym, target_file = target_entry

                call_edges.append({
                    "src_name": enclosing_name,
                    "src_file": file_path,
                    "tgt_name": target_sym.name,
                    "tgt_file": target_file,
                    "confidence": confidence,
                    "line": call.line,
                })

        calls_created = 0
        if call_edges and self.graph_repo:
            async with self.graph_repo.driver.session() as neo_session:
                batch_size = 500
                for i in range(0, len(call_edges), batch_size):
                    batch = call_edges[i:i + batch_size]
                    await neo_session.run(
                        """
                        UNWIND $edges AS edge
                        MATCH (src:CodeSymbol {repo_id: $repo_id, name: edge.src_name, file_path: edge.src_file})
                        MATCH (tgt:CodeSymbol {repo_id: $repo_id, name: edge.tgt_name, file_path: edge.tgt_file})
                        MERGE (src)-[r:CALLS]->(tgt)
                        ON CREATE SET r.confidence = edge.confidence, r.line = edge.line
                        """,
                        repo_id=str(repo.id), edges=batch,
                    )
                    calls_created += len(batch)

        logger.info("Resolved %d CALLS edges for %s", calls_created, repo.name)
        return calls_created

    async def _delete_all_repo_data(self, repo_id: UUID) -> None:
        from sqlalchemy import delete
        await self.session.execute(
            delete(CodeSymbol).where(
                CodeSymbol.file_id.in_(
                    select(CodeFile.id).where(CodeFile.repo_id == repo_id)
                )
            )
        )
        await self.session.execute(
            delete(CodeFile).where(CodeFile.repo_id == repo_id)
        )
        await self.session.flush()

        if self.graph_repo:
            async with self.graph_repo.driver.session() as neo:
                await neo.run("MATCH (n {repo_id: $repo_id}) DETACH DELETE n", repo_id=str(repo_id))

        if self.vector_repo:
            from qdrant_client.models import FieldCondition, Filter, MatchValue
            await self.vector_repo.client.delete(
                collection_name="code_chunks",
                points_selector=Filter(must=[
                    FieldCondition(key="repo_id", match=MatchValue(value=str(repo_id))),
                ]),
            )

        logger.info("Cleared all indexed data for repo %s", repo_id)

    async def _delete_file_data(self, repo_id: UUID, file_path: str) -> None:
        existing = (
            await self.session.execute(
                select(CodeFile).where(
                    CodeFile.repo_id == repo_id,
                    CodeFile.file_path == file_path,
                )
            )
        ).scalar_one_or_none()

        if existing:
            await self.session.delete(existing)
            await self.session.flush()

        if self.graph_repo:
            async with self.graph_repo.driver.session() as neo:
                await neo.run(
                    "MATCH (s:CodeSymbol {repo_id: $repo_id, file_path: $file_path}) DETACH DELETE s",
                    repo_id=str(repo_id), file_path=file_path,
                )
                await neo.run(
                    "MATCH (p:Property {repo_id: $repo_id, file_path: $file_path}) DETACH DELETE p",
                    repo_id=str(repo_id), file_path=file_path,
                )
                await neo.run(
                    "MATCH (f:CodeFile {repo_id: $repo_id, file_path: $file_path}) DETACH DELETE f",
                    repo_id=str(repo_id), file_path=file_path,
                )

        if self.vector_repo:
            from qdrant_client.models import FieldCondition, Filter, MatchValue
            await self.vector_repo.client.delete(
                collection_name="code_chunks",
                points_selector=Filter(must=[
                    FieldCondition(key="repo_id", match=MatchValue(value=str(repo_id))),
                    FieldCondition(key="file_path", match=MatchValue(value=file_path)),
                ]),
            )

    async def _diff_files(
        self, work_dir: Path, old_sha: str, new_sha: str
    ) -> tuple[list[str], list[str]]:
        result = await RepoManager._run_git(
            work_dir, ["git", "diff", "--name-status", old_sha, new_sha]
        )

        changed: list[str] = []
        deleted: list[str] = []

        for line in result.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t", maxsplit=1)
            if len(parts) < 2:
                continue
            status, path = parts[0].strip(), parts[1].strip()
            if status.startswith("D"):
                deleted.append(path)
            else:
                changed.append(path)

        return changed, deleted

    @staticmethod
    def _list_all_files(work_dir: Path) -> list[str]:
        files: list[str] = []
        for path in work_dir.rglob("*"):
            if not path.is_file():
                continue
            parts = path.relative_to(work_dir).parts
            if any(part in IGNORED_DIRS for part in parts):
                continue
            if path.suffix.lower() in IGNORED_EXTENSIONS:
                continue
            files.append(str(path.relative_to(work_dir).as_posix()))
        return files

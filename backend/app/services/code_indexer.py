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
from app.services.code_parser import ExtractedCall, ExtractedSymbol, parse_file
from app.services.llm import LLMOrchestrator
from app.services.repo_manager import RepoManager
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

        for i, rel_path in enumerate(changed_files):
            repo.status_message = f"Indexing file {i + 1}/{total_files}: {rel_path}"
            if i % 5 == 0:
                await self.session.commit()
                await event_manager.broadcast("repo.indexing_progress", {"repo_id": str(repo.id), "current": i + 1, "total": total_files, "file_path": rel_path})
            try:
                result = await self._index_file(repo, work_dir, rel_path)
                if result is None:
                    stats["files_skipped"] += 1
                else:
                    stats["files_changed"] += 1
                    stats["symbols_indexed"] += result.get("symbols", 0)
                    stats["chunks_stored"] += result.get("chunks", 0)
                    if result.get("calls"):
                        all_calls[rel_path] = result["calls"]
                        all_file_paths.append(rel_path)
                    if result.get("imports"):
                        all_imports[rel_path] = result["imports"]
            except Exception as exc:
                logger.error("Error indexing %s: %s", rel_path, exc)
                stats["errors"].append(f"index:{rel_path}:{exc}")

        if self.graph_repo and all_calls:
            repo.status_message = "Resolving function calls..."
            await self.session.commit()
            await event_manager.broadcast("repo.indexing_progress", {
                "repo_id": str(repo.id), "current": total_files, "total": total_files,
                "file_path": "Resolving calls...",
            })
            calls_created = await self._resolve_calls(repo, all_calls, all_file_paths, all_imports)
            stats["calls_resolved"] = calls_created

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
                repo, rel_path, parse_result.symbols, parse_result.imports
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

    async def _resolve_calls(
        self,
        repo: Repository,
        all_calls: dict[str, list[ExtractedCall]],
        all_file_paths: list[str],
        all_imports: dict[str, list[str]],
    ) -> int:
        from app.services.call_resolver import CallResolver, build_import_map
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

            symbol_table.add(SymbolEntry(
                node_id=str(sym.id),
                file_path=file_path,
                name=sym.name,
                kind=sym.kind,
                param_count=param_count,
                owner_id=str(sym.parent_symbol_id) if sym.parent_symbol_id else None,
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
        resolver = CallResolver(symbol_table, import_map)
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

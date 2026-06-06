from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import deque, namedtuple
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import CodeFile, CodeSymbol, Repository
from app.repositories.vector import PostgresVectorRepository
from app.services.code_parser import (
    ExtractedCall, ExtractedHeritage, ExtractedImport, ExtractedProperty,
    ExtractedRoute, ExtractedSymbol, detect_language, parse_file,
)
from app.services.community_detector import CommunityDetector
from app.services.heritage_resolver import AccessResolver, HeritageResolver
from app.services.llm import LLMOrchestrator
from app.services.process_tracer import ProcessTracer
from app.services.repo_manager import RepoManager
from app.services.symbol_table import SymbolEntry, SymbolTable
from app.services.type_env import TypeEnvironment, build_type_env, propagate_types
from app.utils.graph_keys import compose_key, split_symbol_key

logger = logging.getLogger(__name__)

# Plain scalar snapshot of a CodeSymbol, cached across the phase 06 -> 08 commit
# boundary. Holding the ORM row instead would expire on commit (production uses
# expire_on_commit=True) and trigger a lazy load on an AsyncSession — a crash.
_SymbolData = namedtuple("_SymbolData", ["name", "parent_symbol_id"])

IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", "target", "bin", "obj",
}
IGNORED_EXTENSIONS = {
    ".lock", ".min.js", ".min.css", ".map", ".wasm",
    ".pyc", ".pyo", ".exe", ".dll", ".so", ".dylib",
}
MAX_FILE_SIZE = 500_000
SIZE_BUDGET_BYTES = 20 * 1024 * 1024
PARALLEL_MIN_FILES = 15
PARALLEL_MIN_BYTES = 512 * 1024
CROSS_FILE_SKIP_THRESHOLD = 0.03
CROSS_FILE_HARD_CAP = 2000


class CodePipeline:
    """Code indexing pipeline.

    Phases:
      01  File discovery
      02  Parsing (tree-sitter AST, size-budgeted batches)
      03  Structure (CONTAINS/DEFINES graph edges)
      04  Import resolution + topological sort
      05  Named binding propagation + wildcard synthesis
      06  Call tracing (topological order, using type env)
      07  Heritage MRO
      08  Cross-file binding re-resolution
      09  Community detection (Leiden)
      10  Process detection (entry-point scoring)
      11  Validation (confidence scoring, edge cleanup)
      12  Embeddings
      13  Symbol enrichment (opt-in via enrich_symbols)
      14  Wiki generation (opt-in via generate_wiki)
    """

    def __init__(
        self,
        session: AsyncSession,
        llm: LLMOrchestrator | None,
        vector_repo: PostgresVectorRepository | None,
        repo_manager: RepoManager,
    ) -> None:
        self.session = session
        self.llm = llm
        self.vector_repo = vector_repo
        self.repo_manager = repo_manager

        self._repo: Repository | None = None
        self._work_dir: Path | None = None
        self._repo_id_str: str = ""

        self._changed_files: list[str] = []
        self._deleted_files: list[str] = []
        self._all_file_paths: list[str] = []

        self._parsed: dict[str, dict] = {}

        # Files whose existing chunks were already removed during phase 03
        # (changed-existing files), plus brand-new files that never had chunks.
        # Phase 12 consults this to skip a redundant per-fingerprint delete.
        self._chunks_cleared_in_structure: set[str] = set()

        self._all_calls: dict[str, list[ExtractedCall]] = {}
        self._all_imports: dict[str, list[str]] = {}
        # Structured form alongside _all_imports. _all_imports stores the bare
        # module string and feeds build_import_map (which expects strings).
        # build_named_imports / build_wildcard_imports need the full
        # ExtractedImport so they can read the imported symbol names directly.
        self._all_extracted_imports: dict[str, list[ExtractedImport]] = {}
        self._topological_order: list[str] = []
        self._resolved_import_map: dict[str, set[str]] = {}
        # Per-import resolution: file -> {import_source -> resolved_file}.
        # _resolved_import_map collapses a file's imports into one set, losing
        # which source resolved to which file; phase 05 needs the pairing so
        # each named binding resolves to its own source file.
        self._per_import_resolution: dict[str, dict[str, str]] = {}

        self._named_import_map: dict[str, dict[str, tuple[str, str]]] = {}
        self._wildcard_import_map: dict[str, set[str]] = {}

        # (symbol_table, symbol_by_id, id_to_name, enclosing_index) built once
        # from the CodeSymbol rows and reused across phases 06 and 08.
        self._symbol_index: tuple | None = None

        self._stats: dict = {}

    async def run(
        self,
        repo_id: UUID,
        full: bool = False,
        enrich_symbols: bool = False,
        generate_wiki: bool = False,
    ) -> dict:
        from app.api.websocket import event_manager

        self._repo = await self.repo_manager.get(repo_id)
        if not self._repo:
            raise ValueError(f"Repository {repo_id} not found")

        repo = self._repo
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

        self._work_dir = self.repo_manager.repo_working_dir(repo)
        self._repo_id_str = str(repo.id)

        self._stats = {
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

        repo.status = "indexing"
        repo.status_message = "Starting pipeline..."
        await self.session.commit()

        try:
            await self.phase_01_file_discovery(old_sha, new_sha, full)
            total = len(self._changed_files)

            await event_manager.broadcast("repo.indexing_started", {
                "repo_id": self._repo_id_str,
                "total_files": total,
            })

            await self._update_status("Parsing files...", "repo.indexing_progress", {
                "repo_id": self._repo_id_str, "phase": 2, "current": 0, "total": total,
            })
            await self.phase_02_parsing()

            await self._update_status("Building structure graph...", "repo.indexing_progress", {
                "repo_id": self._repo_id_str, "phase": 3, "current": total, "total": total,
            })
            await self.phase_03_structure()

            await self._update_status("Resolving imports...", "repo.indexing_progress", {
                "repo_id": self._repo_id_str, "phase": 4, "current": total, "total": total,
            })
            await self.phase_04_import_resolution()

            await self._update_status("Propagating named bindings...", "repo.indexing_progress", {
                "repo_id": self._repo_id_str, "phase": 5, "current": total, "total": total,
            })
            await self.phase_05_named_bindings()

            await self._update_status("Tracing function calls...", "repo.indexing_progress", {
                "repo_id": self._repo_id_str, "phase": 6, "current": total, "total": total,
            })
            await self.phase_06_call_tracing()

            await self._update_status("Resolving heritage and MRO...", "repo.indexing_progress", {
                "repo_id": self._repo_id_str, "phase": 7, "current": total, "total": total,
            })
            await self.phase_07_heritage_mro()

            await self._update_status("Cross-file binding pass...", "repo.indexing_progress", {
                "repo_id": self._repo_id_str, "phase": 8, "current": total, "total": total,
            })
            await self.phase_08_cross_file_binding()

            await self._update_status("Detecting communities...", "repo.indexing_progress", {
                "repo_id": self._repo_id_str, "phase": 9, "current": total, "total": total,
            })
            await self.phase_09_community_detection()

            await self._update_status("Tracing processes...", "repo.indexing_progress", {
                "repo_id": self._repo_id_str, "phase": 10, "current": total, "total": total,
            })
            await self.phase_10_process_detection()

            await self._update_status("Validating graph...", "repo.indexing_progress", {
                "repo_id": self._repo_id_str, "phase": 11, "current": total, "total": total,
            })
            await self.phase_11_validation()

            await self._update_status("Generating embeddings...", "repo.indexing_progress", {
                "repo_id": self._repo_id_str, "phase": 12, "current": total, "total": total,
            })
            await self.phase_12_embeddings()

            if enrich_symbols:
                await self._update_status("Enriching symbols...", "repo.indexing_progress", {
                    "repo_id": self._repo_id_str, "phase": 13, "current": total, "total": total,
                })
                await self.phase_13_enrich_symbols()

            if generate_wiki:
                await self._update_status("Generating wiki...", "repo.indexing_progress", {
                    "repo_id": self._repo_id_str, "phase": 14, "current": total, "total": total,
                })
                await self.phase_14_generate_wiki(repo_id)

            repo.last_indexed_commit = new_sha
            from datetime import datetime, timezone
            repo.last_indexed_at = datetime.now(timezone.utc)
            repo.status = "ready"
            repo.status_message = None
            await self.session.commit()

            await event_manager.broadcast("repo.indexing_completed", {
                "repo_id": self._repo_id_str,
                "files_changed": self._stats["files_changed"],
                "symbols_indexed": self._stats["symbols_indexed"],
            })

            logger.info(
                "Pipeline complete for %s: %d changed, %d skipped, %d deleted, %d symbols, %d errors",
                repo.name, self._stats["files_changed"], self._stats["files_skipped"],
                self._stats["files_deleted"], self._stats["symbols_indexed"],
                len(self._stats["errors"]),
            )

            # Feature 2: record code indexing failure state
            try:
                from app.services.pipeline_failures import (
                    PipelineFailureService, derive_code_failed_step,
                )
                failure_svc = PipelineFailureService(
                    self.session, broadcast=event_manager.broadcast,
                )
                errors = self._stats.get("errors", [])
                if errors:
                    failed_step = derive_code_failed_step(errors)
                    error_message = "\n".join(errors[:10])
                    await failure_svc.record(
                        entity_type="code_repo",
                        entity_id=repo_id,
                        pipeline_name="code_index",
                        failed_step=failed_step,
                        error_message=error_message,
                        metadata={"error_count": len(errors)},
                    )
                else:
                    await failure_svc.resolve(
                        entity_type="code_repo",
                        entity_id=repo_id,
                        pipeline_name="code_index",
                    )
                await self.session.commit()
            except Exception as e:
                logger.warning("Failed to record code indexing failure state: %s", e)

            return self._stats

        except Exception as exc:
            # If the original failure was a DB error the session is in a
            # need-rollback state; mutating repo.status and committing without
            # rolling back first raises PendingRollbackError and masks the real
            # exception. Roll back so the cleanup runs in a clean transaction.
            await self.session.rollback()
            repo = await self.repo_manager.get(repo_id) or repo
            repo.status = "error"
            repo.status_message = str(exc)[:500]
            try:
                await self._delete_all_repo_data(repo.id)
            except Exception:
                logger.exception("Failed to clean up partial pipeline data for repo %s", repo.id)
            await self.session.commit()

            # Feature 2: record the exception as an unresolved failure
            try:
                from app.services.pipeline_failures import PipelineFailureService
                failure_svc = PipelineFailureService(
                    self.session, broadcast=event_manager.broadcast,
                )
                await failure_svc.record(
                    entity_type="code_repo",
                    entity_id=repo_id,
                    pipeline_name="code_index",
                    failed_step="other",
                    error_message=f"{type(exc).__name__}: {exc}"[:2000],
                )
                await self.session.commit()
            except Exception as e2:
                logger.warning("Failed to record pipeline exception as failure: %s", e2)

            raise

    async def _update_status(self, message: str, event_type: str, event_data: dict) -> None:
        from app.api.websocket import event_manager
        self._repo.status_message = message
        await self.session.commit()
        await event_manager.broadcast(event_type, event_data)

    async def _phase_log(self, name: str) -> float:
        logger.info("[pipeline] starting phase %s", name)
        return time.monotonic()

    def _phase_done(self, name: str, t0: float) -> None:
        elapsed = time.monotonic() - t0
        logger.info("[pipeline] phase %s done in %.2fs", name, elapsed)

    async def phase_01_file_discovery(
        self, old_sha: str | None, new_sha: str, full: bool
    ) -> None:
        t0 = await self._phase_log("01_file_discovery")
        work_dir = self._work_dir

        if full or not old_sha:
            self._changed_files = _list_all_files(work_dir)
            self._deleted_files = []
            await self._delete_all_repo_data(self._repo.id)
        else:
            self._changed_files, self._deleted_files = await _diff_files(work_dir, old_sha, new_sha)
            # Re-trace callers of changed/deleted files so a renamed or removed
            # target doesn't leave an unchanged caller's edge missing until the
            # next full reindex. Computed BEFORE the deleted-file delete loop
            # below (which drops those edges). Added dependents hit phase_03's
            # content-hash skip — no structure rewrite, only their calls are
            # re-resolved in phase_06.
            targets = self._changed_files + self._deleted_files
            if targets:
                deps, total = await _find_dependent_caller_files(
                    self.session, self._repo.id, targets,
                )
                if total > len(deps):
                    logger.info(
                        "Incremental reindex: %d dependent caller files exceed cap "
                        "%d; re-tracing %d (run a full reindex to refresh the rest)",
                        total, DEPENDENT_RETRACE_CAP, len(deps),
                    )
                already = set(targets)
                self._changed_files.extend(d for d in deps if d not in already)

        for rel_path in self._deleted_files:
            try:
                await self._delete_file_data(self._repo.id, rel_path)
                self._stats["files_deleted"] += 1
            except Exception as exc:
                logger.error("Error deleting data for %s: %s", rel_path, exc)
                self._stats["errors"].append(f"delete:{rel_path}:{exc}")

        self._phase_done("01_file_discovery", t0)

    async def phase_02_parsing(self) -> None:
        t0 = await self._phase_log("02_parsing")
        work_dir = self._work_dir
        files = self._changed_files
        total = len(files)

        total_bytes = sum(
            _safe_file_size(work_dir / fp) for fp in files
        )
        use_parallel = total >= PARALLEL_MIN_FILES and total_bytes >= PARALLEL_MIN_BYTES

        if use_parallel:
            await self._parse_parallel(files, work_dir, total_bytes)
        else:
            for fp in files:
                result = await self._parse_one(work_dir, fp)
                if result is not None:
                    self._parsed[fp] = result
                else:
                    self._stats["files_skipped"] += 1

        self._phase_done("02_parsing", t0)

    async def _parse_parallel(
        self, files: list[str], work_dir: Path, total_bytes: int
    ) -> None:
        budget = SIZE_BUDGET_BYTES
        batches: list[list[str]] = []
        current_batch: list[str] = []
        current_size = 0

        for fp in files:
            size = _safe_file_size(work_dir / fp)
            if current_size + size > budget and current_batch:
                batches.append(current_batch)
                current_batch = [fp]
                current_size = size
            else:
                current_batch.append(fp)
                current_size += size

        if current_batch:
            batches.append(current_batch)

        for batch in batches:
            tasks = [self._parse_one(work_dir, fp) for fp in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for fp, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error("Error parsing %s: %s", fp, result)
                    self._stats["errors"].append(f"parse:{fp}:{result}")
                elif result is None:
                    self._stats["files_skipped"] += 1
                else:
                    self._parsed[fp] = result

    async def _parse_one(self, work_dir: Path, rel_path: str) -> dict | None:
        full_path = work_dir / rel_path
        loop = asyncio.get_running_loop()

        def _read_file() -> tuple[str, str] | None:
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
            return (content, hashlib.sha256(content.encode()).hexdigest())

        read_result = await loop.run_in_executor(None, _read_file)
        if read_result is None:
            return None

        content, content_hash = read_result
        parse_result = await loop.run_in_executor(None, parse_file, rel_path, content)
        if not parse_result:
            return None

        return {
            "rel_path": rel_path,
            "content_hash": content_hash,
            "parse_result": parse_result,
            "content": content,
        }

    async def phase_03_structure(self) -> None:
        t0 = await self._phase_log("03_structure")
        repo = self._repo

        # Map each class-like symbol to the file that defines it (across all
        # parsed files, changed or not) so cross-file base classes resolve to
        # their real node when heritage edges are written below.
        class_file_index: dict[str, str] = {}
        _class_kinds = ("class", "struct", "interface", "trait")

        def _index_classes(syms: list[ExtractedSymbol], fp: str) -> None:
            for s in syms:
                if s.kind in _class_kinds:
                    class_file_index.setdefault(s.name, fp)
                if s.children:
                    _index_classes(s.children, fp)

        for fp, parsed in self._parsed.items():
            _index_classes(parsed["parse_result"].symbols, fp)

        for fp, parsed in self._parsed.items():
            pr = parsed["parse_result"]
            existing = (
                await self.session.execute(
                    select(CodeFile).where(
                        CodeFile.repo_id == repo.id,
                        CodeFile.file_path == fp,
                    )
                )
            ).scalar_one_or_none()

            if existing and existing.content_hash == parsed["content_hash"]:
                self._all_file_paths.append(fp)
                if pr.calls:
                    self._all_calls[fp] = pr.calls
                if pr.imports:
                    self._all_imports[fp] = [imp.source for imp in pr.imports]
                    self._all_extracted_imports[fp] = list(pr.imports)
                self._stats["files_skipped"] += 1
                continue

            if existing:
                await self._delete_file_data(repo.id, fp)
            # Either we just removed the old chunks (changed-existing) or the
            # file is brand new and has none; phase 12 need not delete again.
            self._chunks_cleared_in_structure.add(fp)

            code_file = CodeFile(
                id=uuid4(),
                repo_id=repo.id,
                file_path=fp,
                language=pr.language,
                content_hash=parsed["content_hash"],
            )
            self.session.add(code_file)
            await self.session.flush()

            symbol_count = 0
            symbol_map: dict[str, UUID] = {}
            for sym in pr.symbols:
                symbol_count += _store_symbol(self.session, code_file, sym, None, symbol_map)

            await _store_graph(
                self.session, repo, fp, pr.symbols, pr.imports,
                heritage=pr.heritage, properties=pr.properties, routes=pr.routes,
                base_files=class_file_index,
            )

            self._stats["files_changed"] += 1
            self._stats["symbols_indexed"] += symbol_count

            self._all_file_paths.append(fp)
            if pr.calls:
                self._all_calls[fp] = pr.calls
            if pr.imports:
                self._all_imports[fp] = [imp.source for imp in pr.imports]
                self._all_extracted_imports[fp] = list(pr.imports)

        await self.session.commit()
        self._phase_done("03_structure", t0)

    async def phase_04_import_resolution(self) -> None:
        t0 = await self._phase_log("04_import_resolution")

        from app.services.call_resolver import build_import_map
        from app.services.import_resolvers import resolve_import
        from app.services.suffix_index import SuffixIndex

        repo_root = str(self._work_dir)
        file_set = set(self._all_file_paths)
        suffix_index = SuffixIndex(self._all_file_paths)

        refined_imports: dict[str, list[str]] = {}
        for fp, imports in self._all_imports.items():
            lang = detect_language(fp) or "unknown"
            resolved_list: list[str] = []
            per_source: dict[str, str] = {}
            for imp in imports:
                refined = suffix_index.lookup(imp)
                if refined is None:
                    refined = resolve_import(fp, imp, lang, repo_root, self._all_file_paths)
                resolved = refined if refined else imp
                resolved_list.append(resolved)
                per_source[imp] = resolved
            refined_imports[fp] = resolved_list
            self._per_import_resolution[fp] = per_source

        self._resolved_import_map = build_import_map(self._all_file_paths, refined_imports)

        self._topological_order = _kahn_topological_sort(
            self._all_file_paths, self._resolved_import_map
        )

        self._phase_done("04_import_resolution", t0)

    async def phase_05_named_bindings(self) -> None:
        t0 = await self._phase_log("05_named_bindings")

        from app.services.call_resolver import build_named_imports, build_wildcard_imports
        from app.services.named_bindings import propagate

        self._named_import_map = build_named_imports(
            self._all_extracted_imports, self._all_file_paths, self._per_import_resolution
        )
        self._wildcard_import_map = build_wildcard_imports(self._all_extracted_imports, self._all_file_paths)

        symbol_table: dict[str, list[str]] = {}
        for fp in self._all_file_paths:
            parsed = self._parsed.get(fp)
            if not parsed:
                continue
            symbol_table[fp] = [
                sym.name for sym in parsed["parse_result"].symbols
            ]

        for fp in self._topological_order:
            parsed = self._parsed.get(fp)
            if not parsed:
                continue
            lang = detect_language(fp) or "unknown"
            # Map each import source to the file IT resolved to. The previous
            # form picked one arbitrary file from the whole resolved set for
            # every source, so all named bindings in a file pointed at the same
            # path. _per_import_resolution preserves the per-source pairing.
            import_map_for_file = {
                source: resolved
                for source, resolved in self._per_import_resolution.get(fp, {}).items()
                if resolved != fp
            }
            extra = propagate(
                fp, lang, import_map_for_file, symbol_table,
                source_text=parsed.get("content", ""),
            )
            if extra:
                self._named_import_map.setdefault(fp, {}).update(extra)

        for fp, bindings in list(self._named_import_map.items()):
            for name, (source_file, exported_name) in list(bindings.items()):
                resolved = _resolve_binding_chain(name, fp, self._named_import_map)
                if resolved and resolved != (source_file, exported_name):
                    self._named_import_map[fp][name] = resolved

        self._phase_done("05_named_bindings", t0)

    async def _load_symbol_index(self) -> tuple:
        """Load every symbol and derive the call-resolution structures once.

        Returns ``(symbol_table, symbol_by_id, id_to_name, enclosing_index,
        type_bindings)`` and caches them on the instance. Phases 06 and 08 both
        consume this and each previously ran the identical ``CodeSymbol`` SELECT
        and rebuilt everything. ``symbol_by_id`` holds a plain ``_SymbolData``
        snapshot rather than the ORM row so it stays valid across the commits
        between the two phases. ``type_bindings`` (name -> return type) is used
        only by phase 08 to seed its type envs.
        """
        if self._symbol_index is not None:
            return self._symbol_index

        from app.services.code_parser import extract_return_type_from_signature

        rows = (await self.session.execute(
            select(CodeSymbol, CodeFile.file_path)
            .join(CodeFile)
            .where(CodeFile.repo_id == self._repo.id)
        )).all()

        symbol_table = SymbolTable()
        symbol_by_id: dict[str, tuple] = {}
        type_bindings: dict[str, str] = {}
        id_to_name: dict[str, str] = {str(sym.id): sym.name for sym, _fp in rows}

        for sym, fp in rows:
            param_count = None
            if sym.signature:
                params = sym.signature.strip("()").split(",")
                param_count = len([p for p in params if p.strip()]) if params != [""] else 0

            parent_id = str(sym.parent_symbol_id) if sym.parent_symbol_id else None
            return_type = extract_return_type_from_signature(sym.signature, sym.source_code)
            symbol_table.add(SymbolEntry(
                node_id=str(sym.id),
                file_path=fp,
                name=sym.name,
                kind=sym.kind,
                param_count=param_count,
                owner_id=parent_id,
                owner_name=id_to_name.get(parent_id) if parent_id else None,
                return_type=return_type,
            ))
            symbol_by_id[str(sym.id)] = (_SymbolData(sym.name, parent_id), fp)
            if return_type:
                type_bindings[sym.name] = return_type

        # (line_start, line_end, name, owner) — owner disambiguates the caller's
        # key so a call edge's source matches the owner-qualified method node.
        enclosing_index: dict[str, list[tuple[int, int, str, str | None]]] = {}
        for sym, fp in rows:
            if sym.kind in ("function", "method"):
                owner = id_to_name.get(str(sym.parent_symbol_id)) if sym.parent_symbol_id else None
                enclosing_index.setdefault(fp, []).append(
                    (sym.line_start, sym.line_end, sym.name, owner)
                )
        for fp in enclosing_index:
            enclosing_index[fp].sort(key=lambda x: x[0], reverse=True)

        self._symbol_index = (
            symbol_table, symbol_by_id, id_to_name, enclosing_index, type_bindings,
        )
        return self._symbol_index

    async def _resolve_inherited_call(
        self, call, fp: str, enclosing_owner: str | None, heritage_resolver,
    ) -> tuple[str, str, str | None, float] | None:
        """Resolve a ``self.<method>()`` the call resolver couldn't pin down to an
        inherited ancestor method, by walking the enclosing class's extends chain.

        Returns ``(name, file, owner, confidence)`` or None. Fires only for
        self/this member calls inside a class method — there the receiver is the
        enclosing class, so its inheritance chain is the place to look.
        """
        if getattr(call, "call_form", None) != "member" or not enclosing_owner:
            return None
        if getattr(call, "receiver_name", None) not in ("self", "this", "$this"):
            return None
        child_class_key = compose_key("symbol", enclosing_owner, fp)
        inh = await heritage_resolver.find_inherited_method(child_class_key, call.called_name)
        if not inh:
            return None
        target_key, conf = inh
        name, file_path, owner = split_symbol_key(target_key)
        return name, file_path, owner, conf

    async def phase_06_call_tracing(self) -> None:
        t0 = await self._phase_log("06_call_tracing")

        if not self._all_calls:
            self._phase_done("06_call_tracing", t0)
            return

        from app.services.call_resolver import CallResolver

        symbol_table, symbol_by_id, id_to_name, enclosing_index, _ = await self._load_symbol_index()

        type_envs: dict[str, TypeEnvironment] = {}
        for fp in self._all_file_paths:
            parsed = self._parsed.get(fp)
            if not parsed:
                continue
            lang = detect_language(fp) or ""
            if not lang:
                continue
            content = parsed.get("content", "")
            try:
                from app.services.code_parser import _get_language
                from tree_sitter import Language, Parser
                lang_obj = _get_language(lang)
                if lang_obj:
                    p = Parser(lang_obj if isinstance(lang_obj, Language) else Language(lang_obj))
                    tree = p.parse(content.encode("utf-8"))
                    type_envs[fp] = build_type_env(tree, content.encode("utf-8"), lang, fp)
            except Exception as exc:
                logger.debug("Failed to build type env for %s: %s", fp, exc)

        if type_envs:
            propagate_types(type_envs, self._resolved_import_map)

        resolver = CallResolver(
            symbol_table,
            self._resolved_import_map,
            type_envs=type_envs,
            named_import_map=self._named_import_map,
            wildcard_import_map=self._wildcard_import_map,
            topological_order=self._topological_order,
        )

        heritage_resolver = HeritageResolver(self.session, self._repo_id_str)
        call_edges: list[dict] = []
        ordered_files = self._topological_order or list(self._all_calls.keys())

        for fp in ordered_files:
            calls = self._all_calls.get(fp)
            if not calls:
                continue
            for call in calls:
                result = resolver.resolve(call, fp)
                enclosing_name = None
                enclosing_owner = None
                for start, end, name, owner in enclosing_index.get(fp, []):
                    if start <= call.line <= end:
                        enclosing_name = name
                        enclosing_owner = owner
                        break
                if not enclosing_name:
                    continue
                if not result:
                    inherited = await self._resolve_inherited_call(
                        call, fp, enclosing_owner, heritage_resolver,
                    )
                    if inherited:
                        t_name, t_file, t_owner, conf = inherited
                        call_edges.append({
                            "src_name": enclosing_name,
                            "src_file": fp,
                            "src_owner": enclosing_owner,
                            "tgt_name": t_name,
                            "tgt_file": t_file,
                            "tgt_owner": t_owner,
                            "confidence": conf,
                            "line": call.line,
                        })
                    continue
                target_id, confidence = result
                target_entry = symbol_by_id.get(target_id)
                if not target_entry:
                    continue
                target_sym, target_file = target_entry
                target_owner = (
                    id_to_name.get(str(target_sym.parent_symbol_id))
                    if target_sym.parent_symbol_id else None
                )
                call_edges.append({
                    "src_name": enclosing_name,
                    "src_file": fp,
                    "src_owner": enclosing_owner,
                    "tgt_name": target_sym.name,
                    "tgt_file": target_file,
                    "tgt_owner": target_owner,
                    "confidence": confidence,
                    "line": call.line,
                })

        calls_created = 0
        if call_edges:
            batch_size = 500
            for i in range(0, len(call_edges), batch_size):
                batch = call_edges[i:i + batch_size]
                edge_rows = json.dumps([
                    {
                        "src": compose_key("symbol", e["src_name"], e["src_file"], owner=e.get("src_owner")),
                        "tgt": compose_key("symbol", e["tgt_name"], e["tgt_file"], owner=e.get("tgt_owner")),
                        "confidence": e["confidence"],
                        "line": e["line"],
                    }
                    for e in batch
                ])
                await self.session.execute(
                    text("""
                        INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                        SELECT
                            :repo_id,
                            'symbol',
                            d.src,
                            'symbol',
                            d.tgt,
                            'calls',
                            jsonb_build_object('confidence', d.confidence::float, 'line', d.line::int)
                        FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS d(src text, tgt text, confidence text, line text)
                        ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                    """),
                    {"repo_id": self._repo_id_str, "rows": edge_rows},
                )
                calls_created += len(batch)

        await self.session.commit()
        self._stats["calls_resolved"] = calls_created
        logger.info("Resolved %d CALLS edges for %s", calls_created, self._repo.name)
        self._phase_done("06_call_tracing", t0)

    async def phase_07_heritage_mro(self) -> None:
        t0 = await self._phase_log("07_heritage_mro")
        resolver = HeritageResolver(self.session, self._repo_id_str)
        result = await resolver.resolve_all()
        self._stats["method_overrides"] = result["overrides"]
        self._stats["method_implements"] = result["implements"]
        self._stats["method_inherited"] = result.get("inherited", 0)

        if self._all_calls:
            member_calls: dict[str, list[ExtractedCall]] = {}
            for fp, calls in self._all_calls.items():
                member = [c for c in calls if c.call_form == "member"]
                if member:
                    member_calls[fp] = member

            if member_calls:
                type_envs: dict[str, TypeEnvironment] = {}
                for fp in member_calls:
                    parsed = self._parsed.get(fp)
                    if not parsed:
                        continue
                    lang = detect_language(fp) or ""
                    if not lang:
                        continue
                    content = parsed.get("content", "")
                    try:
                        from app.services.code_parser import _get_language
                        from tree_sitter import Language, Parser
                        lang_obj = _get_language(lang)
                        if lang_obj:
                            p = Parser(lang_obj if isinstance(lang_obj, Language) else Language(lang_obj))
                            tree = p.parse(content.encode("utf-8"))
                            type_envs[fp] = build_type_env(tree, content.encode("utf-8"), lang, fp)
                    except Exception as exc:
                        logger.debug("Failed to build type env for %s: %s", fp, exc)

                if type_envs:
                    from app.services.call_resolver import build_import_map as _build_import_map
                    import_map = _build_import_map(list(type_envs.keys()), self._all_imports)
                    propagate_types(type_envs, import_map)
                    access_resolver = AccessResolver(self.session, self._repo_id_str)
                    accesses = await access_resolver.resolve(type_envs, member_calls)
                    self._stats["accesses"] = accesses

        await self.session.commit()
        self._phase_done("07_heritage_mro", t0)

    async def phase_08_cross_file_binding(self) -> None:
        t0 = await self._phase_log("08_cross_file_binding")

        file_count = len(self._all_file_paths)
        if file_count > CROSS_FILE_HARD_CAP:
            logger.info("Phase 08 skipped: file count %d exceeds hard cap %d", file_count, CROSS_FILE_HARD_CAP)
            self._phase_done("08_cross_file_binding", t0)
            return

        total_calls = sum(len(c) for c in self._all_calls.values())
        if total_calls == 0:
            self._phase_done("08_cross_file_binding", t0)
            return

        # Count resolved 'calls' edges whose SOURCE is one of THIS run's files,
        # so resolved_calls and total_calls measure the same population. Counting
        # the whole repo's edges (against this run's call sites) made the rate
        # exceed 1 on incremental runs and skip the phase every time.
        result = await self.session.execute(
            text("""
                SELECT COUNT(*) FROM code_edges
                WHERE repo_id = :repo_id AND edge_type = 'calls'
                  AND split_part(source_key, '::', 2) = ANY(CAST(:files AS text[]))
            """),
            {"repo_id": self._repo_id_str, "files": list(self._all_file_paths)},
        )
        resolved_calls = result.scalar() or 0

        benefit_estimate = _cross_file_benefit(total_calls, resolved_calls)
        if benefit_estimate < CROSS_FILE_SKIP_THRESHOLD:
            logger.info(
                "Phase 08 skipped: estimated benefit %.1f%% < threshold %.1f%%",
                benefit_estimate * 100, CROSS_FILE_SKIP_THRESHOLD * 100,
            )
            self._phase_done("08_cross_file_binding", t0)
            return

        from app.services.call_resolver import CallResolver

        symbol_table, symbol_by_id, id_to_name, enclosing_index, type_bindings = (
            await self._load_symbol_index()
        )

        type_envs: dict[str, TypeEnvironment] = {}
        for fp in self._all_file_paths:
            env = TypeEnvironment(fp)
            for name, type_name in type_bindings.items():
                env.add(name, type_name, "seeded", "file")
            type_envs[fp] = env

        resolver = CallResolver(
            symbol_table,
            self._resolved_import_map,
            type_envs=type_envs,
            named_import_map=self._named_import_map,
            wildcard_import_map=self._wildcard_import_map,
        )

        new_edges: list[dict] = []
        for fp, calls in self._all_calls.items():
            for call in calls:
                result = resolver.resolve(call, fp)
                if not result:
                    continue
                target_id, confidence = result
                if confidence < 0.6:
                    continue
                enclosing_name = None
                enclosing_owner = None
                for start, end, name, owner in enclosing_index.get(fp, []):
                    if start <= call.line <= end:
                        enclosing_name = name
                        enclosing_owner = owner
                        break
                if not enclosing_name:
                    continue
                target_entry = symbol_by_id.get(target_id)
                if not target_entry:
                    continue
                target_sym, target_file = target_entry
                target_owner = (
                    id_to_name.get(str(target_sym.parent_symbol_id))
                    if target_sym.parent_symbol_id else None
                )
                new_edges.append({
                    "src": compose_key("symbol", enclosing_name, fp, owner=enclosing_owner),
                    "tgt": compose_key("symbol", target_sym.name, target_file, owner=target_owner),
                    "confidence": confidence,
                    "line": call.line,
                })

        added = 0
        if new_edges:
            batch_size = 500
            for i in range(0, len(new_edges), batch_size):
                batch = new_edges[i:i + batch_size]
                edge_rows = json.dumps(batch)
                res = await self.session.execute(
                    text("""
                        INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                        SELECT
                            :repo_id,
                            'symbol',
                            d.src,
                            'symbol',
                            d.tgt,
                            'calls',
                            jsonb_build_object('confidence', d.confidence::float, 'line', d.line::int)
                        FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS d(src text, tgt text, confidence float, line int)
                        ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                        RETURNING 1
                    """),
                    {"repo_id": self._repo_id_str, "rows": edge_rows},
                )
                added += len(res.fetchall())

        await self.session.commit()
        self._stats["cross_file_calls_added"] = added
        logger.info("Phase 08 added %d new cross-file call edges", added)
        self._phase_done("08_cross_file_binding", t0)

    async def phase_09_community_detection(self) -> None:
        t0 = await self._phase_log("09_community_detection")
        detector = CommunityDetector(self.session, self._repo_id_str)
        self._stats["communities"] = await detector.detect()
        await self.session.commit()
        self._phase_done("09_community_detection", t0)

    async def phase_10_process_detection(self) -> None:
        t0 = await self._phase_log("10_process_detection")
        tracer = ProcessTracer(self.session, self._repo_id_str)
        self._stats["processes"] = await tracer.trace()
        await self.session.commit()
        self._phase_done("10_process_detection", t0)

    async def phase_11_validation(self) -> None:
        t0 = await self._phase_log("11_validation")

        removed = await self.session.execute(
            text("""
                DELETE FROM code_edges
                WHERE repo_id = :repo_id
                  AND edge_type = 'calls'
                  AND (properties->>'confidence')::float < 0.3
                RETURNING 1
            """),
            {"repo_id": self._repo_id_str},
        )
        removed_count = len(removed.fetchall())

        await self.session.commit()
        self._stats["edges_pruned"] = removed_count
        logger.info("Phase 11 pruned %d low-confidence edges", removed_count)
        self._phase_done("11_validation", t0)

    async def phase_12_embeddings(self) -> None:
        t0 = await self._phase_log("12_embeddings")

        if not self.llm or not self.vector_repo:
            self._phase_done("12_embeddings", t0)
            return

        from app.config import FEATURE_FLAGS_DEFAULTS
        from app.models.config import Config
        result = await self.session.execute(
            select(Config).where(Config.key == "feature_flags")
        )
        config_row = result.scalar_one_or_none()
        concurrency = (config_row.value if config_row else FEATURE_FLAGS_DEFAULTS).get("pipeline_concurrency", 5)
        sem = asyncio.Semaphore(concurrency)

        file_items = []
        for fp, parsed in self._parsed.items():
            pr = parsed["parse_result"]
            if pr.chunks:
                file_items.append((fp, pr))

        embed_results: dict[str, list[list[float]]] = {}

        from sqlalchemy import select as _sa_select
        from app.config import FEATURE_FLAGS_DEFAULTS
        from app.models.config import Config as _ConfigModel
        _flags_row = (await self.session.execute(
            _sa_select(_ConfigModel).where(_ConfigModel.key == "feature_flags")
        )).scalar_one_or_none()
        _merged_flags = dict(FEATURE_FLAGS_DEFAULTS)
        if _flags_row:
            _merged_flags.update(_flags_row.value)
        _embed_chunk_size = _merged_flags.get("embedding_batch_size", 20)
        _embed_concurrency = _merged_flags.get("embedding_concurrency", 1)

        # All chunks share whichever embedder is currently active. We capture
        # the fingerprint from the first embed call and assert agreement.
        embed_fingerprint: dict[str, str] = {}

        async def _embed_one(fp: str, pr) -> None:
            texts = [c["content"][:2000] for c in pr.chunks]
            async with sem:
                try:
                    vectors, fingerprint = await self.llm.embed_batch_chunked(
                        texts, _embed_chunk_size, _embed_concurrency,
                    )
                    embed_results[fp] = vectors
                    embed_fingerprint[fp] = fingerprint
                except Exception as exc:
                    logger.warning("Batch embedding failed for %s: %s", fp, exc)
                    self._stats["errors"].append(f"embed:{fp}:{exc}")

        await asyncio.gather(*[_embed_one(fp, pr) for fp, pr in file_items])

        # Register every distinct fingerprint observed before writing rows.
        if embed_fingerprint:
            from app.services.embedder_registry import (  # noqa: PLC0415
                EmbedderInfo, embedder_registry, parse_fingerprint,
            )
            for fp_value in set(embed_fingerprint.values()):
                if embedder_registry.is_known(fp_value):
                    continue
                model_id, dims = parse_fingerprint(fp_value)
                await embedder_registry.register(
                    self.session,
                    EmbedderInfo(fingerprint=fp_value, model_id=model_id, dims=dims, source="llm"),
                )

        chunk_count = 0
        for fp, pr in file_items:
            vectors = embed_results.get(fp)
            if not vectors:
                continue
            fingerprint = embed_fingerprint[fp]
            chunks_to_store = []
            for chunk, vector in zip(pr.chunks, vectors):
                chunks_to_store.append({
                    "repo_id": self._repo_id_str,
                    "file_path": fp,
                    "language": pr.language,
                    "symbol_name": chunk.get("symbol_name"),
                    "chunk_content": chunk["content"][:5000],
                    "line_start": chunk["line_start"],
                    "line_end": chunk["line_end"],
                    "embedding": vector,
                })
            if chunks_to_store:
                # Phase 03 already cleared chunks for files it wrote fresh
                # (changed or new). Re-deleting here repeats that work once per
                # registered fingerprint. Only unchanged files, which phase 03
                # left untouched, still need the delete to avoid duplicates.
                if fp not in self._chunks_cleared_in_structure:
                    await self.vector_repo.delete_code_chunks_by_file(self._repo.id, fp)
                await self.vector_repo.upsert_code_chunks(chunks_to_store, fingerprint=fingerprint)
                chunk_count += len(chunks_to_store)

        self._stats["chunks_stored"] = chunk_count
        self._phase_done("12_embeddings", t0)

    async def phase_13_enrich_symbols(self) -> None:
        t0 = await self._phase_log("13_enrich_symbols")

        if not self.llm:
            self._phase_done("13_enrich_symbols", t0)
            return

        from app.api.websocket import event_manager
        from app.services.enrichment_worker import EnrichmentWorker

        worker = EnrichmentWorker(self.llm, broadcast=event_manager.broadcast)
        processed = 0
        # Symbols enter the queue with enrichment_status='pending' at creation,
        # so the worker (which reads CodeSymbol directly) can drain them here.
        # Loop until a batch returns no work or the safety cap is hit.
        for _ in range(200):
            count = await worker.process_batch()
            if count == 0:
                break
            processed += count

        self._stats["enrichment_processed"] = processed
        logger.info("Phase 13 enriched %d symbols", processed)
        self._phase_done("13_enrich_symbols", t0)

    async def phase_14_generate_wiki(self, repo_id: UUID) -> None:
        t0 = await self._phase_log("14_generate_wiki")

        from app.services.wiki_generator import WikiGenerator

        try:
            generator = WikiGenerator(self.session, self.llm)
            await generator.generate(repo_id, force=True)
            await self.session.commit()
        except Exception as exc:
            logger.warning("Wiki generation failed for repo %s: %s", repo_id, exc)

        self._phase_done("14_generate_wiki", t0)

    async def _delete_all_repo_data(self, repo_id: UUID) -> None:
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
        await self.session.execute(
            text("DELETE FROM code_edges WHERE repo_id = :repo_id"),
            {"repo_id": str(repo_id)},
        )
        await self.session.execute(
            text("DELETE FROM code_graph_nodes WHERE repo_id = :repo_id"),
            {"repo_id": str(repo_id)},
        )
        await self.session.commit()

        if self.vector_repo:
            await self.vector_repo.delete_code_chunks_by_repo(repo_id)

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

        await self.session.execute(
            text("""
                DELETE FROM code_edges
                WHERE repo_id = :repo_id
                  AND (
                      source_key = :file_path
                      OR target_key = :file_path
                      OR split_part(source_key, '::', 2) = :file_path
                      OR split_part(target_key, '::', 2) = :file_path
                  )
            """),
            {
                "repo_id": str(repo_id),
                "file_path": file_path,
            },
        )
        await self.session.execute(
            text("""
                DELETE FROM code_graph_nodes
                WHERE repo_id = :repo_id
                  AND (properties->>'file_path' = :file_path
                       OR split_part(key, '::', 2) = :file_path)
            """),
            {"repo_id": str(repo_id), "file_path": file_path},
        )

        # Route/tool nodes have bare keys and no file_path property, so the
        # predicates above can't match them; the handles_* edge from this file
        # was just deleted, so remove any route/tool node left with no inbound
        # handler edge — otherwise phantom routes/processes accumulate.
        await self.session.execute(
            text("""
                DELETE FROM code_graph_nodes n
                WHERE n.repo_id = :repo_id
                  AND n.kind IN ('route', 'tool')
                  AND NOT EXISTS (
                      SELECT 1 FROM code_edges e
                      WHERE e.repo_id = n.repo_id
                        AND e.target_key = n.key
                        AND e.edge_type IN ('handles_route', 'handles_tool')
                  )
            """),
            {"repo_id": str(repo_id)},
        )

        if self.vector_repo:
            await self.vector_repo.delete_code_chunks_by_file(repo_id, file_path)


def _resolve_binding_chain(
    name: str,
    source_file: str,
    named_import_map: dict[str, dict[str, tuple[str, str]]],
    visited: set[str] | None = None,
    depth: int = 0,
) -> tuple[str, str] | None:
    if depth > 10:
        logger.warning("_resolve_binding_chain exceeded max depth for %s:%s", source_file, name)
        return None
    visited = visited or set()
    if source_file in visited:
        return None
    visited = visited | {source_file}
    entry = named_import_map.get(source_file, {}).get(name)
    if entry is None:
        return None
    next_file, exported_name = entry
    deeper = named_import_map.get(next_file, {}).get(exported_name)
    if deeper and deeper[0] != next_file:
        chain_result = _resolve_binding_chain(exported_name, next_file, named_import_map, visited, depth + 1)
        if chain_result:
            return chain_result
    return entry


def _kahn_topological_sort(
    file_paths: list[str],
    import_map: dict[str, set[str]],
) -> list[str]:
    """Return files in dependency order using Kahn's algorithm.

    Files in cycles are grouped together at the point where the cycle would be
    processed. The result covers all files in file_paths.
    """
    path_set = set(file_paths)
    in_degree: dict[str, int] = {f: 0 for f in file_paths}
    dependents: dict[str, list[str]] = {f: [] for f in file_paths}

    for fp in file_paths:
        for dep in import_map.get(fp, set()):
            if dep in path_set and dep != fp:
                in_degree[fp] += 1
                dependents[dep].append(fp)

    queue: deque[str] = deque(f for f in file_paths if in_degree[f] == 0)
    result: list[str] = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for dependent in dependents.get(node, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    cycle_nodes = [f for f in file_paths if in_degree[f] > 0]
    result.extend(cycle_nodes)

    return result


def _safe_file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


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


# Cap on dependent caller files re-traced per incremental run, so a change to a
# widely-called utility doesn't balloon an incremental reindex into a near-full
# one. When exceeded, the overflow is logged (not silently dropped).
DEPENDENT_RETRACE_CAP = 500


def _cross_file_benefit(total_calls: int, resolved_calls: int) -> float:
    """Estimated benefit (fraction of unresolved calls) of running phase 08.

    Clamped to [0, 1] so a resolved count exceeding the (same-population) call
    count can never produce a negative benefit and skip the phase spuriously.
    """
    if total_calls <= 0:
        return 0.0
    return 1.0 - min(1.0, resolved_calls / total_calls)


async def _find_dependent_caller_files(
    session: AsyncSession,
    repo_id,
    changed_files: list[str],
    cap: int = DEPENDENT_RETRACE_CAP,
) -> tuple[list[str], int]:
    """Files (outside ``changed_files``) whose ``calls`` edges target a symbol
    in a changed file, so their call edges must be re-traced.

    Incremental reindex parses only changed files. A caller in an unchanged file
    that targets a renamed/moved symbol in a changed file loses its edge
    (``_delete_file_data`` drops it when the changed file is re-indexed) and
    never regains it until a full reindex. Re-tracing these dependents recreates
    the edge. Returns ``(files, total)`` where ``total`` is the pre-cap count so
    the caller can log any truncation rather than silently dropping work.

    Symbol keys are ``name::file_path`` or ``name::file_path::owner``, so the
    file is always segment 2 of ``::`` — matched here with ``split_part`` rather
    than a ``%::<file>`` suffix so owner-qualified method keys still match.
    """
    if not changed_files:
        return [], 0
    changed_set = set(changed_files)
    rows = (await session.execute(
        text("""
            SELECT DISTINCT split_part(source_key, '::', 2) AS caller_file
            FROM code_edges
            WHERE repo_id = :rid
              AND edge_type = 'calls'
              AND split_part(target_key, '::', 2) = ANY(CAST(:files AS text[]))
        """),
        {"rid": str(repo_id), "files": changed_files},
    )).scalars().all()
    deps = sorted({f for f in rows if f and f not in changed_set})
    return deps[:cap], len(deps)


async def _diff_files(
    work_dir: Path, old_sha: str, new_sha: str
) -> tuple[list[str], list[str]]:
    result = await RepoManager._run_git(
        work_dir, ["git", "diff", "--name-status", old_sha, new_sha]
    )
    changed: list[str] = []
    deleted: list[str] = []
    for line in result.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0].strip()
        # Rename (R###) and copy (C###) entries carry two paths:
        # "STATUS\told_path\tnew_path". The new path is what was indexed;
        # for a rename the old path no longer exists and must be deleted.
        if status[:1] in ("R", "C") and len(parts) >= 3:
            old_path, new_path = parts[1].strip(), parts[2].strip()
            changed.append(new_path)
            if status[:1] == "R":
                deleted.append(old_path)
        elif status.startswith("D"):
            deleted.append(parts[1].strip())
        else:
            changed.append(parts[1].strip())
    return changed, deleted


def _store_symbol(
    session: AsyncSession,
    code_file: CodeFile,
    sym: ExtractedSymbol,
    parent_id: UUID | None,
    symbol_map: dict[str, UUID],
) -> int:
    is_exported = sym.visibility not in ("private",) if sym.visibility else True
    if sym.kind in ("class", "struct", "interface", "trait", "enum", "impl"):
        priority = 2 if is_exported else 1
    elif is_exported:
        priority = 2
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
    session.add(symbol)
    symbol_map[sym.name] = symbol_id

    count = 1
    for child in sym.children:
        count += _store_symbol(session, code_file, child, symbol_id, symbol_map)
    return count


async def _store_graph(
    session: AsyncSession,
    repo: Repository,
    file_path: str,
    symbols: list[ExtractedSymbol],
    imports: list,
    heritage: list[ExtractedHeritage] | None = None,
    properties: list[ExtractedProperty] | None = None,
    routes: list[ExtractedRoute] | None = None,
    base_files: dict[str, str] | None = None,
) -> None:
    repo_id = str(repo.id)
    file_key = compose_key("file", file_path)

    await session.execute(
        text("""
            INSERT INTO code_graph_nodes (repo_id, kind, key, label, properties)
            VALUES (:repo_id, 'file', :key, :label, jsonb_build_object('file_path', CAST(:file_path AS text)))
            ON CONFLICT (repo_id, kind, key) DO NOTHING
        """),
        {"repo_id": repo_id, "key": file_key, "label": file_path, "file_path": file_path},
    )

    repo_key = compose_key("module", repo_id)
    await session.execute(
        text("""
            INSERT INTO code_graph_nodes (repo_id, kind, key, label, properties)
            VALUES (:repo_id, 'module', :key, :key, '{}')
            ON CONFLICT (repo_id, kind, key) DO NOTHING
        """),
        {"repo_id": repo_id, "key": repo_key},
    )
    await session.execute(
        text("""
            INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
            VALUES (:repo_id, 'module', :src, 'file', :tgt, 'defines', '{}')
            ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
        """),
        {"repo_id": repo_id, "src": repo_key, "tgt": file_key},
    )

    async def collect_symbols(
        sym: ExtractedSymbol,
        parent_name: str | None = None,
        parent_key: str | None = None,
    ) -> None:
        # Owner-qualify the key so same-named methods of different classes in one
        # file are distinct nodes (owner = the immediate enclosing symbol's name).
        sym_key = compose_key("symbol", sym.name, file_path, owner=parent_name)
        props = json.dumps({
            "kind": sym.kind,
            "line_start": sym.line_start,
            "line_end": sym.line_end,
            "visibility": sym.visibility,
            "file_path": file_path,
        })
        await session.execute(
            text("""
                INSERT INTO code_graph_nodes (repo_id, kind, key, label, properties)
                VALUES (:repo_id, 'symbol', :key, :label, CAST(:props AS jsonb))
                ON CONFLICT (repo_id, kind, key) DO UPDATE
                    SET properties = EXCLUDED.properties
            """),
            {"repo_id": repo_id, "key": sym_key, "label": sym.name, "props": props},
        )
        await session.execute(
            text("""
                INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                VALUES (:repo_id, 'file', :src, 'symbol', :tgt, 'defines', '{}')
                ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
            """),
            {"repo_id": repo_id, "src": file_key, "tgt": sym_key},
        )
        if parent_key:
            await session.execute(
                text("""
                    INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                    VALUES (:repo_id, 'symbol', :src, 'symbol', :tgt, 'contains', '{}')
                    ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                """),
                {"repo_id": repo_id, "src": parent_key, "tgt": sym_key},
            )
        for child in sym.children:
            await collect_symbols(child, parent_name=sym.name, parent_key=sym_key)

    for sym in symbols:
        await collect_symbols(sym)

    for sym in symbols:
        if sym.kind in ("class", "struct", "interface", "trait"):
            parent_key = compose_key("symbol", sym.name, file_path)
            for child in sym.children:
                if child.kind in ("method", "function"):
                    child_key = compose_key("symbol", child.name, file_path, owner=sym.name)
                    await session.execute(
                        text("""
                            INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                            VALUES (:repo_id, 'symbol', :src, 'symbol', :tgt, 'has_method', '{}')
                            ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                        """),
                        {"repo_id": repo_id, "src": parent_key, "tgt": child_key},
                    )

    if imports:
        for imp in imports:
            mod_key = compose_key("module", imp.source)
            await session.execute(
                text("""
                    INSERT INTO code_graph_nodes (repo_id, kind, key, label, properties)
                    VALUES (:repo_id, 'module', :key, :key, '{}')
                    ON CONFLICT (repo_id, kind, key) DO NOTHING
                """),
                {"repo_id": repo_id, "key": mod_key},
            )
            await session.execute(
                text("""
                    INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                    VALUES (:repo_id, 'file', :src, 'module', :tgt, 'imports', '{}')
                    ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                """),
                {"repo_id": repo_id, "src": file_key, "tgt": mod_key},
            )

    if heritage:
        for h in heritage:
            child_key = compose_key("symbol", h.symbol_name, file_path)
            # Resolve the base class to the file that actually defines it; a
            # cross-file base keyed under the child's file points at no node and
            # silently breaks override / inherited-method detection.
            base_file = (base_files or {}).get(h.base_name, file_path)
            parent_key = compose_key("symbol", h.base_name, base_file)
            await session.execute(
                text("""
                    INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                    VALUES (:repo_id, 'symbol', :src, 'symbol', :tgt, :edge_type, '{}')
                    ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                """),
                {"repo_id": repo_id, "src": child_key, "tgt": parent_key, "edge_type": h.relation},
            )

    if properties:
        for prop in properties:
            prop_key = compose_key("property", prop.name)
            prop_props = json.dumps({
                "type_annotation": prop.type_annotation,
                "line": prop.line,
                "visibility": prop.visibility,
                "owner": prop.owner_name,
                "file_path": file_path,
            })
            await session.execute(
                text("""
                    INSERT INTO code_graph_nodes (repo_id, kind, key, label, properties)
                    VALUES (:repo_id, 'property', :key, :key, CAST(:props AS jsonb))
                    ON CONFLICT (repo_id, kind, key) DO NOTHING
                """),
                {"repo_id": repo_id, "key": prop_key, "props": prop_props},
            )
            owner_key = compose_key("symbol", prop.owner_name, file_path)
            await session.execute(
                text("""
                    INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                    VALUES (:repo_id, 'symbol', :src, 'property', :tgt, 'has_property', '{}')
                    ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                """),
                {"repo_id": repo_id, "src": owner_key, "tgt": prop_key},
            )

    if routes:
        for route in routes:
            if route.kind == "route":
                route_name = f"{route.method or ''} {route.path}".strip()
                route_key = compose_key("route", route_name)
                route_props = json.dumps({"method": route.method, "path": route.path, "framework": route.framework})
                await session.execute(
                    text("""
                        INSERT INTO code_graph_nodes (repo_id, kind, key, label, properties)
                        VALUES (:repo_id, 'route', :key, :key, CAST(:props AS jsonb))
                        ON CONFLICT (repo_id, kind, key) DO NOTHING
                    """),
                    {"repo_id": repo_id, "key": route_key, "props": route_props},
                )
                await session.execute(
                    text("""
                        INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                        VALUES (:repo_id, 'file', :src, 'route', :tgt, 'handles_route', '{}')
                        ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                    """),
                    {"repo_id": repo_id, "src": file_key, "tgt": route_key},
                )
            elif route.kind == "tool":
                tool_key = compose_key("tool", route.path)
                tool_props = json.dumps({"framework": route.framework})
                await session.execute(
                    text("""
                        INSERT INTO code_graph_nodes (repo_id, kind, key, label, properties)
                        VALUES (:repo_id, 'tool', :key, :key, CAST(:props AS jsonb))
                        ON CONFLICT (repo_id, kind, key) DO NOTHING
                    """),
                    {"repo_id": repo_id, "key": tool_key, "props": tool_props},
                )
                await session.execute(
                    text("""
                        INSERT INTO code_edges (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
                        VALUES (:repo_id, 'file', :src, 'tool', :tgt, 'handles_tool', '{}')
                        ON CONFLICT (repo_id, source_kind, source_key, target_kind, target_key, edge_type) DO NOTHING
                    """),
                    {"repo_id": repo_id, "src": file_key, "tgt": tool_key},
                )

    await session.flush()

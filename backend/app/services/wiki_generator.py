import asyncio
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import CodeFile, CodeSymbol, Repository
from app.models.config import Config
from app.services.llm import LLMOrchestrator

logger = logging.getLogger(__name__)


class WikiGenerator:
    def __init__(self, session: AsyncSession, llm: LLMOrchestrator | None = None):
        self.session = session
        self.llm = llm

    async def read(self, repo_id: UUID) -> dict | None:
        """Read-only wiki fetch: return the cached wiki (minus internal keys) or
        None when none exists. NEVER generates — generation is an explicit action
        run by the reindex pipeline (POST /repos/{id}/reindex with
        generate_wiki=true), which keeps GET /code/wiki safe and idempotent."""
        cached = (await self.session.execute(
            select(Config).where(Config.key == f"wiki_{repo_id}")
        )).scalar_one_or_none()
        if not cached:
            return None
        return {k: v for k, v in cached.value.items() if not k.startswith("_")}

    async def generate(self, repo_id: UUID, force: bool = False) -> dict:
        """Generate wiki documentation for a repository."""
        repo = (await self.session.execute(
            select(Repository).where(Repository.id == repo_id)
        )).scalar_one_or_none()
        if not repo:
            return {"error": "Repository not found"}

        cache_key = f"wiki_{repo_id}"

        if not force:
            cached = (await self.session.execute(
                select(Config).where(Config.key == cache_key)
            )).scalar_one_or_none()
            if cached:
                cache_data = cached.value
                cached_at = cache_data.get("_cached_at")
                repo_indexed = repo.last_indexed_at.isoformat() if repo.last_indexed_at else None
                if cached_at and cached_at == repo_indexed:
                    result = {k: v for k, v in cache_data.items() if not k.startswith("_")}
                    return result

        files = (await self.session.execute(
            select(CodeFile).where(CodeFile.repo_id == repo_id).order_by(CodeFile.file_path)
        )).scalars().all()

        modules: dict[str, list] = {}
        for f in files:
            parts = f.file_path.replace("\\", "/").split("/")
            module = "/".join(parts[:-1]) if len(parts) > 1 else "root"
            modules.setdefault(module, []).append(f)

        # Fetch every symbol for the repo in one query and group by file, instead
        # of one SELECT per file (an N+1 that scaled queries with repo size).
        symbols_by_file: dict = {}
        file_ids = [f.id for f in files]
        if file_ids:
            all_symbols = (await self.session.execute(
                select(CodeSymbol)
                .where(CodeSymbol.file_id.in_(file_ids))
                .order_by(CodeSymbol.file_id, CodeSymbol.line_start)
            )).scalars().all()
            for s in all_symbols:
                symbols_by_file.setdefault(s.file_id, []).append(s)

        module_entries = []
        to_summarize: list[tuple[dict, str, str]] = []
        for module_path, module_files in sorted(modules.items()):
            entry = {
                "path": module_path,
                "files": [],
                "summary": None,
                "symbol_count": 0,
            }

            file_descriptions = []
            for f in module_files:
                symbols = symbols_by_file.get(f.id, [])

                file_entry = {
                    "path": f.file_path,
                    "language": f.language,
                    "symbols": [
                        {
                            "name": s.name,
                            "kind": s.kind,
                            "signature": s.signature,
                            "summary": s.summary,
                            "line_start": s.line_start,
                        }
                        for s in symbols
                    ],
                }
                entry["files"].append(file_entry)
                entry["symbol_count"] += len(symbols)

                sym_list = ", ".join(f"{s.name} ({s.kind})" for s in symbols[:10])
                file_descriptions.append(f"- {f.file_path}: {sym_list}")

            if self.llm and file_descriptions:
                prompt = (
                    f"Summarize what this code module does in 2-3 sentences "
                    f"based on its files and symbols:\n\nModule: {module_path}\n"
                    + "\n".join(file_descriptions[:20])
                )
                to_summarize.append((entry, module_path, prompt))

            module_entries.append(entry)

        # Run the per-module summarization calls bounded-concurrently rather than
        # awaiting each in sequence (wall-clock was the sum of all module
        # latencies).
        if to_summarize:
            from app.services import prompt as prompt_mod
            system_prompt = prompt_mod.get("summarization")
            sem = asyncio.Semaphore(5)

            async def _summarize(entry: dict, module_path: str, user_prompt: str) -> None:
                async with sem:
                    try:
                        entry["summary"] = await self.llm.chat_completion(
                            "summarization",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                        )
                    except Exception as e:
                        logger.warning("Wiki summary failed for %s: %s", module_path, e)

            await asyncio.gather(*[_summarize(e, m, p) for e, m, p in to_summarize])

        overview = None
        if self.llm and module_entries:
            try:
                module_list = "\n".join(
                    f"- {m['path']}: {m['symbol_count']} symbols"
                    + (f" — {m['summary'][:100]}" if m.get("summary") else "")
                    for m in module_entries[:30]
                )
                overview = await self.llm.chat_completion(
                    "summarization",
                    messages=[
                        {"role": "system", "content": "You are a code documentation assistant."},
                        {
                            "role": "user",
                            "content": (
                                f"Write a brief overview (3-5 sentences) of this repository "
                                f"based on its modules:\n\nRepository: {repo.name}\n{module_list}"
                            ),
                        },
                    ],
                )
            except Exception as e:
                logger.warning("Wiki overview failed: %s", e)

        result = {
            "repo_name": repo.name,
            "overview": overview,
            "modules": module_entries,
            "total_modules": len(module_entries),
            "total_files": len(files),
        }

        cache_value = {**result, "_cached_at": repo.last_indexed_at.isoformat() if repo.last_indexed_at else None}
        existing_cache = (await self.session.execute(
            select(Config).where(Config.key == cache_key)
        )).scalar_one_or_none()
        if existing_cache:
            existing_cache.value = cache_value
        else:
            self.session.add(Config(key=cache_key, value=cache_value))
        await self.session.flush()

        return result

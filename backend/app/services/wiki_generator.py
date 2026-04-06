import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import CodeFile, CodeSymbol, Repository
from app.services.llm import LLMOrchestrator

logger = logging.getLogger(__name__)


class WikiGenerator:
    def __init__(self, session: AsyncSession, llm: LLMOrchestrator | None = None):
        self.session = session
        self.llm = llm

    async def generate(self, repo_id: UUID) -> dict:
        """Generate wiki documentation for a repository."""
        repo = (await self.session.execute(
            select(Repository).where(Repository.id == repo_id)
        )).scalar_one_or_none()
        if not repo:
            return {"error": "Repository not found"}

        files = (await self.session.execute(
            select(CodeFile).where(CodeFile.repo_id == repo_id).order_by(CodeFile.file_path)
        )).scalars().all()

        modules: dict[str, list] = {}
        for f in files:
            parts = f.file_path.replace("\\", "/").split("/")
            module = "/".join(parts[:-1]) if len(parts) > 1 else "root"
            modules.setdefault(module, []).append(f)

        module_entries = []
        for module_path, module_files in sorted(modules.items()):
            entry = {
                "path": module_path,
                "files": [],
                "summary": None,
                "symbol_count": 0,
            }

            file_descriptions = []
            for f in module_files:
                symbols = (await self.session.execute(
                    select(CodeSymbol).where(CodeSymbol.file_id == f.id).order_by(CodeSymbol.line_start)
                )).scalars().all()

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
                try:
                    from app.services.prompt import PromptService
                    system_prompt = await PromptService.get("summarization", self.session)
                    if not system_prompt:
                        system_prompt = "You are a code documentation assistant."

                    prompt = (
                        f"Summarize what this code module does in 2-3 sentences "
                        f"based on its files and symbols:\n\nModule: {module_path}\n"
                        + "\n".join(file_descriptions[:20])
                    )

                    summary = await self.llm.chat_completion(
                        "summarization",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                    )
                    entry["summary"] = summary
                except Exception as e:
                    logger.warning("Wiki summary failed for %s: %s", module_path, e)

            module_entries.append(entry)

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

        return {
            "repo_name": repo.name,
            "overview": overview,
            "modules": module_entries,
            "total_modules": len(module_entries),
            "total_files": len(files),
        }

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.vector import PostgresVectorRepository
from app.services.code_pipeline import CodePipeline
from app.services.llm import LLMOrchestrator
from app.services.repo_manager import RepoManager

logger = logging.getLogger(__name__)


class CodeIndexer:
    """Backward-compatible wrapper around CodePipeline.

    Existing callers continue to use ``CodeIndexer(session, llm, vector_repo).index_repo()``.
    """

    def __init__(
        self,
        session: AsyncSession,
        llm: LLMOrchestrator | None = None,
        vector_repo: PostgresVectorRepository | None = None,
    ) -> None:
        self.session = session
        self.llm = llm
        self.vector_repo = vector_repo
        self.repo_manager = RepoManager(session)

    async def index_repo(self, repo_id: UUID, full: bool = False) -> dict:
        pipeline = CodePipeline(
            session=self.session,
            llm=self.llm,
            vector_repo=self.vector_repo,
            repo_manager=self.repo_manager,
        )
        return await pipeline.run(repo_id, full=full)

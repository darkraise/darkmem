"""Concrete runner functions for the four built-in periodic jobs.

Every runner is a no-arg async coroutine wired into ``JobRegistry``
via ``app.main`` at startup. Runners must not raise during normal
operation — the registry catches exceptions and records them on the
job's config row, but raising on the happy path causes the loop to
look perpetually broken in the UI.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

logger = logging.getLogger(__name__)


def make_repo_sync_runner(
    app,
    session_factory: async_sessionmaker[AsyncSession],
):
    """Periodic loop that fetches every ``auto_sync=true`` repo and runs
    the code pipeline. The per-repo interval was removed in 0002; the
    job's interval is the only knob.
    """
    async def run() -> None:
        from app.models.code import Repository
        from app.services.code_pipeline import CodePipeline
        from app.services.repo_manager import RepoManager
        from app.repositories.vector import PostgresVectorRepository
        from app.api.websocket import event_manager

        active_llm = getattr(app.state, "llm", None)

        async with session_factory() as list_session:
            repos = (await list_session.execute(
                select(Repository).where(Repository.auto_sync == True)  # noqa: E712
            )).scalars().all()
            repos_to_sync = list(repos)

        for repo in repos_to_sync:
            async with session_factory() as repo_session:
                try:
                    code_vector_repo = PostgresVectorRepository(repo_session, "code_chunks")
                    pipeline = CodePipeline(
                        session=repo_session, llm=active_llm,
                        vector_repo=code_vector_repo,
                        repo_manager=RepoManager(repo_session),
                    )
                    await pipeline.run(repo.id)
                    await repo_session.commit()
                except Exception as e:
                    await repo_session.rollback()
                    logger.error("Periodic sync failed for %s: %s", repo.name, e)
                    try:
                        async with session_factory() as fail_session:
                            fail_manager = RepoManager(fail_session)
                            updated = await fail_manager.mark_periodic_sync_failure(repo.id, e)
                        if updated is not None:
                            await event_manager.broadcast(
                                "repo.auto_sync_disabled",
                                {
                                    "repo_id": str(repo.id),
                                    "name": updated.name,
                                    "status_message": updated.status_message or "",
                                },
                            )
                    except Exception as inner_e:
                        logger.error("Failed to mark repo %s errored: %s", repo.id, inner_e)
    return run


def make_token_blocklist_cleanup_runner(session_factory: async_sessionmaker[AsyncSession]):
    """Delete expired entries from the token blocklist."""
    async def run() -> None:
        from app.models.token_blocklist import TokenBlocklist
        async with session_factory() as session:
            await session.execute(
                delete(TokenBlocklist).where(
                    TokenBlocklist.expires_at < datetime.now(timezone.utc)
                )
            )
            await session.commit()
    return run


def make_pipeline_failure_cleanup_runner(session_factory: async_sessionmaker[AsyncSession]):
    """Prune orphaned pipeline-failure rows and old resolved entries."""
    async def run() -> None:
        from app.services.pipeline_failures import PipelineFailureService
        async with session_factory() as session:
            svc = PipelineFailureService(session)
            orphaned = await svc.prune_orphans()
            resolved_pruned = await svc.prune_resolved_older_than(days=30)
            await session.commit()
        logger.info(
            "Pipeline failure cleanup: orphaned=%s resolved_pruned=%s",
            orphaned, resolved_pruned,
        )
    return run


def make_code_enrichment_runner(app, session_factory: async_sessionmaker[AsyncSession]):
    """Run one batch of code-symbol summarisation through the
    EnrichmentWorker. Replaces the worker's internal run_loop so the
    job registry owns scheduling. Reads ``batch_size`` from the
    ``code_enrichment`` job config via the registry.
    """
    async def run() -> None:
        from app.services.enrichment_worker import EnrichmentWorker
        from app.api.websocket import event_manager

        llm = getattr(app.state, "llm", None)
        if not llm:
            logger.info("code_enrichment skipped: no LLM orchestrator")
            return

        # app.state.job_registry is wired after this runner is constructed,
        # so read it lazily here, not at construction time.
        registry = getattr(app.state, "job_registry", None)
        batch_size = 5
        if registry is not None:
            cfg = await registry.load_config("code_enrichment")
            batch_size = int(cfg.config.get("batch_size", 5))

        worker = EnrichmentWorker(llm, broadcast=event_manager.broadcast)
        await worker.process_batch(batch_size=batch_size)
    return run

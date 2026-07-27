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
    """Prune pipeline-failure rows, and keep the `events` partitions ahead.

    The partition-maintenance arm rides here rather than as its own registered
    job (doc 04 §8.1). Boot-time reconciliation alone is not enough: a process
    that boots in January and runs into March outlives the children the baseline
    created, and a RANGE parent rejects every insert that has no partition to
    land in — so the journal would stop, taking the journaled write with it.
    """
    async def run() -> None:
        from app.services.events import reconcile_event_partitions
        from app.services.pipeline_failures import PipelineFailureService
        async with session_factory() as session:
            # Partition maintenance runs FIRST and commits on its own. Sharing a
            # session with the prunes would let a pruning failure roll back the
            # partition that the next month's journaling depends on — and a
            # missing partition stops journaling rather than degrading it.
            children = await reconcile_event_partitions(session)
            await session.commit()

        async with session_factory() as session:
            svc = PipelineFailureService(session)
            orphaned = await svc.prune_orphans()
            resolved_pruned = await svc.prune_resolved_older_than(days=30)
            await session.commit()
        logger.info(
            "Pipeline failure cleanup: orphaned=%s resolved_pruned=%s events_partitions=%s",
            orphaned, resolved_pruned, ",".join(children),
        )
    return run


def make_graph_orphan_cleanup_runner(session_factory: async_sessionmaker[AsyncSession]):
    """Prune entity-graph ghosts: entities/relations no live memory asserts.

    Backstops the per-delete cleanup against swallowed errors and historical
    accumulation, so the Phase-4 dedup never collapses fresh entities onto a
    stale ghost left by an earlier deleted memory."""
    async def run() -> None:
        from app.repositories.graph import PostgresGraphRepository
        async with session_factory() as session:
            repo = PostgresGraphRepository(session)
            stats = await repo.prune_orphan_entities()
            await session.commit()
        if stats["entities_pruned"] or stats["relations_pruned"]:
            logger.info(
                "Graph orphan cleanup: entities=%s relations=%s",
                stats["entities_pruned"], stats["relations_pruned"],
            )
    return run


def make_tag_orphan_cleanup_runner(session_factory: async_sessionmaker[AsyncSession]):
    """Prune tags no live memory carries any more.

    Tags are auto-created from memory tag strings and linked only through
    ``memory_tags`` (ON DELETE CASCADE), so a deleted memory drops the link
    but leaves the tag row behind. The per-delete self-heal in
    ``MemoryService.delete_memory`` covers new deletes; this backstops
    historical orphans and any delete path that skipped it, so the dashboard
    tag count and the tag filter never show tags nothing uses."""
    async def run() -> None:
        from app.repositories.relational import PostgresTagRepository
        async with session_factory() as session:
            repo = PostgresTagRepository(session)
            removed = await repo.prune_orphans()
            await session.commit()
        if removed:
            logger.info("Tag orphan cleanup: tags=%s", removed)
    return run


def make_expired_memory_cleanup_runner(session_factory: async_sessionmaker[AsyncSession]):
    """Delete memories past their ``expires_at`` TTL.

    Without this, a client-set TTL is silently never honored (the column was
    accepted, stored, and never swept). Embedding partition rows go with the
    memory via ON DELETE CASCADE; orphaned graph entities and tags left behind
    are reclaimed by graph_orphan_cleanup / tag_orphan_cleanup."""
    from sqlalchemy import text
    async def run() -> None:
        async with session_factory() as session:
            expired = (await session.execute(text(
                "SELECT id FROM memories WHERE expires_at IS NOT NULL AND expires_at < NOW()"
            ))).scalars().all()
            if not expired:
                return
            ids = list(expired)
            # Demote any memory still pointing at an expiring superseder before
            # the delete. fk_memories_superseded_by is ON DELETE SET NULL, so
            # deleting a superseding memory would null a dependent's
            # superseded_by while its status stays 'superseded' — violating
            # chk_superseded_has_pointer and aborting the whole sweep batch
            # (TTL'd memories would then never be reclaimed). MemoryService.
            # delete_memory does the same demotion for the interactive path.
            await session.execute(
                text(
                    "UPDATE memories SET status='deprecated', superseded_by=NULL "
                    "WHERE superseded_by = ANY(CAST(:ids AS uuid[]))"
                ),
                {"ids": ids},
            )
            result = await session.execute(
                text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[])) RETURNING id"),
                {"ids": ids},
            )
            deleted = len(result.scalars().all())
            await session.commit()
        if deleted:
            logger.info("Expired memory cleanup: deleted=%s", deleted)
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

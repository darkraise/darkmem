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


def make_code_reconcile_runner(app, session_factory: async_sessionmaker[AsyncSession]):
    """Hash every previously-indexed repo's working tree and reconcile drift.

    Catches what `repo_sync`'s HEAD-sha comparison cannot see at all: a working
    tree edited directly (a `local_path` repo with no fetchable remote, or a
    write straight into a clone directory) never moves HEAD, so
    `CodePipeline.run`'s own short-circuit treats it as up to date forever.
    This job hashes the tree independently of HEAD (`compute_working_tree_drift`)
    and, only when that finds a mismatch, feeds it through the same incremental
    path via `CodePipeline.run(..., forced_files=...)`.

    Deliberately runs with `llm=None`: reconcile rebuilds the code graph
    (files, symbols, calls) from a hash mismatch, never the LLM-backed
    embedding or enrichment phases, so it stays deterministic and free even
    though live model credentials exist. A real commit still gets its
    embeddings refreshed via `repo_sync`, which does carry the LLM.
    """
    async def run() -> None:
        from app.models.code import Repository
        from app.services.code_pipeline import CodePipeline
        from app.services.code_reconcile import compute_working_tree_drift
        from app.services.repo_manager import RepoManager

        async with session_factory() as list_session:
            repos = (await list_session.execute(
                select(Repository).where(Repository.last_indexed_commit.isnot(None))
            )).scalars().all()
            repos_to_check = list(repos)

        for repo in repos_to_check:
            async with session_factory() as repo_session:
                try:
                    manager = RepoManager(repo_session)
                    repo_row = await manager.get(repo.id)
                    if repo_row is None:
                        continue
                    work_dir = manager.repo_working_dir(repo_row)
                    if not work_dir.exists():
                        continue

                    changed, deleted = await compute_working_tree_drift(
                        repo_session, repo_row, work_dir,
                    )
                    if not changed and not deleted:
                        continue

                    pipeline = CodePipeline(
                        session=repo_session, llm=None, vector_repo=None,
                        repo_manager=manager,
                    )
                    await pipeline.run(repo_row.id, forced_files=(changed, deleted))
                    await repo_session.commit()
                    logger.info(
                        "Code reconcile: repo=%s changed=%d deleted=%d",
                        repo_row.name, len(changed), len(deleted),
                    )
                except ValueError as e:
                    # repo_working_dir's local_path revalidation rejects a row
                    # whose path moved into a blocked tree since it was created.
                    logger.warning("Code reconcile skipped repo %s: %s", repo.name, e)
                except Exception as e:
                    await repo_session.rollback()
                    logger.error("Code reconcile failed for %s: %s", repo.name, e)
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
        from app.services.events import record_maintenance_run
        try:
            async with session_factory() as session:
                repo = PostgresGraphRepository(session)
                stats = await repo.prune_orphan_entities()
                await session.commit()
        except Exception:
            await record_maintenance_run(
                session_factory, operation="graph_orphan_cleanup", outcome="error",
            )
            raise
        if stats["entities_pruned"] or stats["relations_pruned"]:
            logger.info(
                "Graph orphan cleanup: entities=%s relations=%s",
                stats["entities_pruned"], stats["relations_pruned"],
            )
        await record_maintenance_run(
            session_factory, operation="graph_orphan_cleanup", outcome="ok",
            detail={
                "entities_pruned": stats["entities_pruned"],
                "relations_pruned": stats["relations_pruned"],
            },
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
        from app.services.events import record_maintenance_run
        try:
            async with session_factory() as session:
                repo = PostgresTagRepository(session)
                removed = await repo.prune_orphans()
                await session.commit()
        except Exception:
            await record_maintenance_run(
                session_factory, operation="tag_orphan_cleanup", outcome="error",
            )
            raise
        if removed:
            logger.info("Tag orphan cleanup: tags=%s", removed)
        await record_maintenance_run(
            session_factory, operation="tag_orphan_cleanup", outcome="ok",
            detail={"tags_removed": removed},
        )
    return run


def make_expired_memory_cleanup_runner(session_factory: async_sessionmaker[AsyncSession]):
    """Delete memories past their ``expires_at`` TTL, and heal stranded provenance.

    Without this, a client-set TTL is silently never honored (the column was
    accepted, stored, and never swept). Embedding partition rows go with the
    memory via ON DELETE CASCADE; orphaned graph entities and tags left behind
    are reclaimed by graph_orphan_cleanup / tag_orphan_cleanup.

    ``fact_sources.source_ref`` is a **soft** reference with no FK, so nothing
    cascades there: this sweep withdraws provenance itself (doc 05 §8.4), on the
    same terms as every other delete path. The provenance backstop rides here as
    a second arm rather than on graph_orphan_cleanup because that job is Layer-1
    graph hygiene, on which Phase-4 dedup depends, and a Layer-2 failure sharing
    its session would take it down; this job is already the one that makes
    memories vanish, which is what strands provenance in the first place."""
    from sqlalchemy import text
    # Module-qualified rather than name-imported: the two arms below heal the
    # same end state, so a test proving the sweep withdraws on its own has to be
    # able to stub the backstop out. A name imported here would still see such a
    # patch (this runs when the factory is called, after the patch is applied),
    # but a name imported at module scope — which is what an import hoist or an
    # import sorter produces — would not, and the test would silently pass on
    # the backstop's work instead. Attribute lookup cannot drift that way.
    from app.services import fact_provenance
    from app.services.supersession import demote_dependents
    async def run() -> None:
        from app.services.events import record_maintenance_run
        deleted = 0
        reaped = 0
        try:
            async with session_factory() as session:
                expired = (await session.execute(text(
                    "SELECT id FROM memories WHERE expires_at IS NOT NULL AND expires_at < NOW()"
                ))).scalars().all()
                if expired:
                    ids = list(expired)
                    # Demote before deleting, never after: the demotion is what
                    # keeps the SET-NULL FK from stranding a dependent on
                    # 'superseded' with a null pointer, and one such row aborts
                    # the whole batch so no TTL'd memory is ever reclaimed.
                    # Shared with the interactive delete path
                    # (MemoryService.delete_memory) so the two cannot drift.
                    await demote_dependents(session, ids)
                    # Then withdraw provenance, still before the DELETE and in
                    # the same transaction: a rollback must take the inline
                    # expiry and the append-only sources_changed rows with the
                    # delete that justified them. The batch is all-or-nothing
                    # for the same reason it always was -- a memory whose
                    # withdrawal failed must not be deleted anyway, which is the
                    # stranding this closes.
                    for memory_id in ids:
                        await fact_provenance.withdraw_memory_sources(
                            session, memory_id=memory_id
                        )
                    result = await session.execute(
                        text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[])) RETURNING id"),
                        {"ids": ids},
                    )
                    deleted = len(result.scalars().all())
                    await session.commit()

            # The backstop, in its own transaction after the delete committed,
            # and outside the `if expired` branch: what it heals was stranded by
            # some *other* path -- ProcessingPipeline.delete_memory swallows a
            # failed withdrawal -- so it must run on ticks that expire nothing.
            async with session_factory() as session:
                reaped = len(
                    await fact_provenance.reap_orphaned_memory_sources(session)
                )
                await session.commit()
        except Exception:
            await record_maintenance_run(
                session_factory, operation="expired_memory_cleanup", outcome="error",
            )
            raise
        if deleted or reaped:
            logger.info(
                "Expired memory cleanup: deleted=%s provenance_reaped=%s",
                deleted, reaped,
            )
        await record_maintenance_run(
            session_factory, operation="expired_memory_cleanup", outcome="ok",
            detail={"deleted": deleted, "provenance_reaped": reaped},
        )
    return run


def make_buffer_flush_runner(app, session_factory: async_sessionmaker[AsyncSession]):
    """Claim one batch of buffered captures and replay them (doc 05 §3).

    The pipeline is read from ``app.state`` on every run rather than captured at
    construction, because this runner is built before the lifespan wires the
    pipeline and because a Postgres-only boot leaves it None for the whole
    process. With no pipeline there is nothing to flush INTO, so the run is a
    no-op that leaves every buffered row pending — deliberately, since claiming
    them would spend attempts on work that cannot succeed.
    """
    async def run() -> None:
        from app.services.buffer_flush import flush_once

        pipeline = getattr(app.state, "pipeline", None)
        if pipeline is None:
            logger.info("buffer_flush skipped: no pipeline")
            return

        stats = await flush_once(session_factory, pipeline)
        if any(stats.values()):
            logger.info(
                "Buffer flush: claimed=%s done=%s failed=%s rejected=%s "
                "reclaimed=%s swept=%s",
                stats["claimed"], stats["done"], stats["failed"],
                stats["rejected"], stats["reclaimed"], stats["swept"],
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

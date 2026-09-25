"""Concrete runner functions for the four built-in periodic jobs.

Every runner is a no-arg async coroutine wired into ``JobRegistry``
via ``app.main`` at startup. Runners must not raise during normal
operation — the registry catches exceptions and records them on the
job's config row, but raising on the happy path causes the loop to
look perpetually broken in the UI.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.services.job_registry import FieldDescriptor

logger = logging.getLogger(__name__)

# Per-repo due-times, keyed by repo id then by lane. Invariant 13 fixes the
# worker count at one, so an in-process map needs no cross-process
# serialisation. The accepted cost is that a restart makes every repo
# immediately due: one burst of fetches at boot, which at homelab repo counts
# is not worth a column to avoid.
_DUE: dict[UUID, dict[str, float]] = {}


def _due_reset() -> None:
    """Test hook only."""
    _DUE.clear()


def forget_repo_due(repo_id: UUID) -> None:
    """Drop a repo's due-times so the next tick examines it immediately.

    The due-times are derived from the repo's own switches and intervals, so a
    write that changes one of those leaves them stale -- and a stale entry
    refuses every tick until the *old* interval lapses, which is unbounded
    above (neither interval has a ceiling). Callers: the repo write door, on a
    change to any field this loop schedules on, and on delete, which otherwise
    leaks an entry for a row that no longer exists.

    The map stays private to this module and this is its one public writer:
    a caller reaching into ``_DUE`` directly would be a second owner of the
    loop's scheduling state.
    """
    _DUE.pop(repo_id, None)


def _claim_due(repo_id: UUID, lane: str, interval: int, now: float) -> bool:
    lanes = _DUE.setdefault(repo_id, {})
    if now < lanes.get(lane, 0.0):
        return False
    lanes[lane] = now + interval
    return True


def make_repo_sync_runner(
    app,
    session_factory: async_sessionmaker[AsyncSession],
):
    """The one recurring indexing loop.

    HEAD is the single trigger: a pull, another agent's commit and the
    operator's own commit are the same event by the time this sees them.
    Fetching is a separate lane whose only job is to move HEAD.
    """
    async def run() -> None:
        import time

        from app.models.code import Repository
        from app.services.code_pipeline import CodePipeline
        from app.services.code_reconcile import compute_working_tree_drift
        from app.services.git_head import resolve_head_sha
        from app.services.repo_manager import RepoManager
        from app.repositories.vector import PostgresVectorRepository
        from app.api.websocket import event_manager

        active_llm = getattr(app, "state", None) and getattr(app.state, "llm", None)
        now = time.monotonic()

        async with session_factory() as list_session:
            repos = (await list_session.execute(
                select(Repository).where(
                    (Repository.fetch_enabled == True)  # noqa: E712
                    | (Repository.index_on_commit_enabled == True)  # noqa: E712
                )
            )).scalars().all()
            candidates = [(r.id, r.name) for r in repos]

        for repo_id, repo_name in candidates:
            async with session_factory() as repo_session:
                try:
                    manager = RepoManager(repo_session)
                    repo = await manager.get(repo_id)
                    if repo is None:
                        continue

                    # The index lane below takes claim_for_indexing; this lane
                    # takes nothing, so it has to refuse on the same statuses
                    # that claim refuses on -- otherwise a tick landing inside
                    # an in-flight clone, webhook or manual reindex fetches and
                    # `reset --hard`s the working tree that run owns, and a
                    # fetch failing against a half-written clone rmtree's the
                    # directory the clone is still writing into. The status is
                    # read BEFORE _claim_due so a refused tick does not burn the
                    # interval: the interval bounds how often a fetch happens,
                    # not how often one is skipped, and a repo that goes idle
                    # mid-window would otherwise wait out a whole interval it
                    # never used. The residual window between this read and
                    # pull_repo is accepted at homelab scale.
                    if (
                        repo.fetch_enabled
                        and repo.status not in RepoManager.BUSY_STATUSES
                        and _claim_due(
                            repo_id, "fetch", repo.fetch_interval_seconds, now,
                        )
                    ):
                        # Own try/except: a transient network fault fetching
                        # must not fall into the shared handler below, which
                        # would call mark_periodic_sync_failure and silently
                        # disable index_on_commit_enabled -- a switch the
                        # operator chose, for a fault that has nothing to do
                        # with it. Noticing a local commit needs no network.
                        try:
                            await manager.pull_repo(repo)
                        except Exception as fetch_exc:
                            logger.warning(
                                "Fetch failed for %s: %s", repo_name, fetch_exc,
                            )
                            # pull_repo reaches the DB through get_credential,
                            # whose session.get() calls sit outside the
                            # RuntimeError guard pull_repo puts around its git
                            # subprocess calls. A DB-layer fault there leaves
                            # the session in a failed transaction, which the
                            # index lane below would inherit. Rolling back
                            # expires every loaded attribute, so `repo` has to
                            # be re-read before anything touches it -- a bare
                            # rollback turns this into MissingGreenlet at the
                            # next attribute access.
                            await repo_session.rollback()
                            repo = await manager.get(repo_id)
                            if repo is None:
                                continue

                    if not repo.index_on_commit_enabled:
                        continue
                    if not _claim_due(
                        repo_id, "index", repo.commit_poll_seconds, now,
                    ):
                        continue

                    work_dir = manager.repo_working_dir(repo)
                    if not work_dir.exists():
                        continue

                    head = await resolve_head_sha(work_dir)
                    forced: tuple[list[str], list[str]] | None = None
                    if head is None or head == repo.last_indexed_commit:
                        if not repo.index_uncommitted:
                            continue
                        drift = await compute_working_tree_drift(
                            repo_session, repo, work_dir,
                        )
                        if not drift[0] and not drift[1]:
                            continue
                        forced = drift
                        # The retired standalone code_reconcile job ran every
                        # drift-forced pipeline with llm=None, because it swept
                        # every indexed repo unconditionally and extraction
                        # cost on every repo's every drift tick was too broad
                        # a default. This loop only reaches here for a repo
                        # whose operator opted into index_uncommitted, so the
                        # cost is scoped to what was asked for and carrying
                        # active_llm (the same as any other index tick) is fine.

                    # Losing the claim is the ordinary case, not an error: the
                    # run that holds it is doing this tick's work.
                    if not await manager.claim_for_indexing(
                        repo_id, message="Indexing new commit...",
                    ):
                        continue

                    pipeline = CodePipeline(
                        session=repo_session, llm=active_llm,
                        vector_repo=PostgresVectorRepository(repo_session, "code_chunks"),
                        repo_manager=manager,
                    )
                    # pull=False: the fetch lane above already owns fetching
                    # this tick (or an earlier one); the index lane only ever
                    # observes HEAD, never moves it.
                    await pipeline.run(repo_id, forced_files=forced, pull=False)
                    await repo_session.commit()
                except Exception as e:
                    await repo_session.rollback()
                    logger.error("Indexing loop failed for %s: %s", repo_name, e)
                    try:
                        async with session_factory() as fail_session:
                            updated = await RepoManager(
                                fail_session
                            ).mark_periodic_sync_failure(repo_id, e)
                        if updated is not None:
                            await event_manager.broadcast(
                                "repo.index_on_commit_disabled",
                                {
                                    "repo_id": str(repo_id),
                                    "name": updated.name,
                                    "status_message": updated.status_message or "",
                                },
                            )
                    except Exception as inner_e:
                        logger.error("Failed to mark repo %s errored: %s", repo_id, inner_e)
    return run


def make_code_deriver_runner(session_factory: async_sessionmaker[AsyncSession]):
    """Sweep every indexed repository through `assert_repo_graph` (doc 10 §6).

    T2.96's production trigger for the T2.27 deriver — see
    `code_deriver_job.py` for why this is a Tier-C job rather than a reindex
    hook. Each repo runs in its own session/transaction so one repo's
    failure can't roll back another's write, mirroring
    `make_repo_sync_runner` above.

    A failure never raises out of the sweep: it is recorded in
    `pipeline_failures` under `pipeline_name=CODE_DERIVER_PIPELINE_NAME`,
    distinct from the index run's own `"code_index"` rows, and the sweep
    moves on to the next repo. That is how the failure surfaces without
    ever failing an index run — visible on `GET /api/v1/pipeline-failures`
    the same way an indexing failure is.
    """
    async def run() -> None:
        from app.models.code import Repository
        from app.services.code_deriver import assert_repo_graph
        from app.services.code_deriver_job import CODE_DERIVER_PIPELINE_NAME
        from app.services.pipeline_failures import PipelineFailureService

        async with session_factory() as list_session:
            repo_ids = (await list_session.execute(
                select(Repository.id).where(Repository.last_indexed_commit.isnot(None))
            )).scalars().all()

        for repo_id in repo_ids:
            async with session_factory() as repo_session:
                failure_svc = PipelineFailureService(repo_session)
                try:
                    # One commit covers both the derivation write and the
                    # resolve() update: if resolve() itself raises, the
                    # rollback below undoes the derivation too, so the except
                    # branch records a real failure rather than a phantom one
                    # for a repo whose derivation had actually succeeded.
                    result = await assert_repo_graph(repo_session, repo_id)
                    await failure_svc.resolve(
                        "code_repo", repo_id, CODE_DERIVER_PIPELINE_NAME,
                    )
                    await repo_session.commit()
                    logger.info(
                        "Code deriver: repo=%s entities=%d relations=%d",
                        repo_id, result["entities"], result["relations"],
                    )
                except Exception as e:
                    await repo_session.rollback()
                    logger.error("Code deriver failed for repo %s: %s", repo_id, e)
                    try:
                        await failure_svc.record(
                            entity_type="code_repo", entity_id=repo_id,
                            pipeline_name=CODE_DERIVER_PIPELINE_NAME,
                            failed_step="derive",
                            error_message=f"{type(e).__name__}: {e}"[:2000],
                        )
                        await repo_session.commit()
                    except Exception as e2:
                        logger.error(
                            "Failed to record deriver failure for %s: %s", repo_id, e2,
                        )
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
    async def run() -> dict | None:
        from app.services.buffer_flush import flush_once

        pipeline = getattr(app.state, "pipeline", None)
        if pipeline is None:
            logger.info("buffer_flush skipped: no pipeline")
            return {}

        stats = await flush_once(session_factory, pipeline)
        if any(stats.values()):
            logger.info(
                "Buffer flush: claimed=%s done=%s failed=%s rejected=%s "
                "reclaimed=%s swept=%s",
                stats["claimed"], stats["done"], stats["failed"],
                stats["rejected"], stats["reclaimed"], stats["swept"],
            )
            return stats
        # Empty queue. This runs every five seconds, so saying so is what
        # keeps an idle instance from writing ~17k rows a day.
        return {}
    return run


def make_code_enrichment_runner(app, session_factory: async_sessionmaker[AsyncSession]):
    """Run one batch of code-symbol summarisation through the
    EnrichmentWorker. Replaces the worker's internal run_loop so the
    job registry owns scheduling. Reads ``batch_size`` from the
    ``code_enrichment`` job config via the registry.
    """
    async def run() -> dict:
        from app.services.enrichment_worker import EnrichmentWorker
        from app.api.websocket import event_manager

        llm = getattr(app.state, "llm", None)
        if not llm:
            logger.info("code_enrichment skipped: no LLM orchestrator")
            return {}

        # app.state.job_registry is wired after this runner is constructed,
        # so read it lazily here, not at construction time.
        registry = getattr(app.state, "job_registry", None)
        batch_size = 5
        if registry is not None:
            cfg = await registry.load_config("code_enrichment")
            batch_size = int(cfg.config.get("batch_size", 5))

        worker = EnrichmentWorker(llm, broadcast=event_manager.broadcast)
        processed = await worker.process_batch(batch_size=batch_size)
        # Every ten seconds against an empty symbol queue on an instance with
        # no repositories indexed; an unreported no-op here was ~8.6k rows/day.
        if not processed:
            return {}
        return processed if isinstance(processed, dict) else {"enriched": processed}
    return run


def make_ppr_snapshot_runner(
    app,
    session_factory: async_sessionmaker[AsyncSession],
):
    """Rebuild a rotating batch of projects' PPR snapshots (doc 07 §4).

    Tier C, and the only writer of the in-process cache the graph arms read.
    It is deliberately *not* a member of the dreaming family: contract 6 fixes
    that family as the consolidation passes, and doc 07 §4 owns this artefact's
    mechanics separately. Invariant 15 is unaffected either way — retrieval
    reads the artefact, never this runner.

    **The cursor advances on a visited project, not a successful one.** A
    project whose graph fails deterministically would otherwise pin the
    rotation and starve every project behind it, which is the failure the
    rotation exists to avoid. A short batch means the rotation reached the end,
    so the cursor resets — without that the job goes inert after one pass and
    still reports ``ok``, the half `run_topic_detection` originally missed.

    **A missing fingerprint degrades the snapshot; it never fails the run.**
    Without one the synonymy arm is skipped and the graph is relation-only,
    which is a weaker snapshot but a correct one. Refusing to build at all
    would retire the arm entirely on any install whose embedder is still
    settling.
    """
    async def run() -> None:
        from app.repositories.vector import PostgresVectorRepository
        from app.services.ppr_snapshot import (
            PPR_SNAPSHOT_CONFIG_SCHEMA,
            PPR_SNAPSHOT_JOB_KEY,
            refresh_snapshots,
        )

        registry = getattr(app.state, "job_registry", None)
        knobs = {fd.key: fd.default for fd in PPR_SNAPSHOT_CONFIG_SCHEMA}
        if registry is not None:
            cfg = await registry.load_config(PPR_SNAPSHOT_JOB_KEY)
            knobs.update(cfg.config or {})
        batch_size = int(knobs.pop("batch_size"))

        fingerprint: str | None = None
        llm = getattr(app.state, "llm", None)
        if llm is not None:
            try:
                async with session_factory() as session:
                    fingerprint = await PostgresVectorRepository(
                        session
                    ).resolve_read_fingerprint(llm)
            except Exception as e:
                logger.info(
                    "ppr_snapshot: no resolvable read fingerprint (%s); "
                    "building relation-only snapshots", e,
                )

        after_project = await _load_ppr_cursor(session_factory)
        outcome = await refresh_snapshots(
            session_factory,
            fingerprint=fingerprint,
            batch_size=batch_size,
            after_project=after_project,
            synonymy_threshold=float(knobs["synonymy_threshold_pct"]) / 100.0,
            synonymy_top_k=int(knobs["synonymy_top_k"]),
            synonymy_max_nodes=int(knobs["synonymy_max_nodes"]),
            max_snapshot_edges=int(knobs["max_snapshot_edges"]),
            build_timeout_seconds=float(knobs["build_timeout_seconds"]),
        )

        wrapped = outcome.projects_visited < batch_size
        cursor = None if wrapped else outcome.last_project
        await _save_ppr_cursor(session_factory, cursor)

        logger.info(
            "PPR snapshot visited %d project(s) from cursor %r: %d built, "
            "%d skipped; cursor now %r%s",
            outcome.projects_visited, after_project, outcome.snapshots_built,
            outcome.skipped, cursor, " (wrapped to start)" if wrapped else "",
        )
    return run


def make_relation_embedding_runner(
    app,
    session_factory: async_sessionmaker[AsyncSession],
):
    """Keep `relation_embeddings__<slug>` current (doc 07 §4, doc 19 §6).

    Tier C: the dual-level channel's global arm reads these vectors, and
    writing them during Phase 5 would put an extra embed round trip on every
    capture for a signal retrieval does not read until its flag is on.

    Without an orchestrator there is nothing to embed with, so the run is a
    no-op rather than a failure — the same stance every other model-spending
    runner takes in Postgres-only mode.
    """
    async def run() -> None:
        from app.services.relation_embeddings import (
            RELATION_EMBEDDING_CONFIG_SCHEMA,
            RELATION_EMBEDDING_JOB_KEY,
            refresh_relation_embeddings,
        )

        llm = getattr(app.state, "llm", None)
        if llm is None:
            logger.info("relation_embedding_refresh skipped: no LLM orchestrator")
            return

        registry = getattr(app.state, "job_registry", None)
        knobs = {fd.key: fd.default for fd in RELATION_EMBEDDING_CONFIG_SCHEMA}
        if registry is not None:
            cfg = await registry.load_config(RELATION_EMBEDDING_JOB_KEY)
            knobs.update(cfg.config or {})

        async with session_factory() as session:
            outcome = await refresh_relation_embeddings(
                session, llm,
                missing_batch=int(knobs["missing_batch"]),
                rotation_batch=int(knobs["rotation_batch"]),
                chunk_size=int(knobs["embed_chunk"]),
            )
            await session.commit()

        if outcome.total:
            logger.info(
                "Relation embeddings: %d new, %d rotated under %s",
                outcome.missing_written, outcome.rotated, outcome.fingerprint,
            )
    return run


def make_repo_entity_anchoring_runner(
    app,
    session_factory: async_sessionmaker[AsyncSession],
):
    """Embed repo-minted entities so the code bridge anchors (doc 10 §6, T2.97).

    Tier C, and deliberately not a dreaming-family member: contract 6 fixes that
    family at six, and this is an artefact refresh in the same class as
    `ppr_snapshot` and `relation_embedding_refresh`. Invariant 15 is unaffected
    — Phase 4 reads the partition this fills, never this runner.

    The deriver that mints these entities is LLM-free by structural guard, so
    the embed cannot live at derive time; it lives here, one scheduled tick
    behind. Without an orchestrator there is nothing to embed with, so the run
    is a no-op rather than a failure.
    """
    async def run() -> None:
        from app.services.entity_anchoring import (
            REPO_ENTITY_ANCHORING_CONFIG_SCHEMA,
            REPO_ENTITY_ANCHORING_JOB_KEY,
            refresh_repo_entity_anchors,
        )

        llm = getattr(app.state, "llm", None)
        if llm is None:
            logger.info("repo_entity_anchoring skipped: no LLM orchestrator")
            return

        registry = getattr(app.state, "job_registry", None)
        knobs = {fd.key: fd.default for fd in REPO_ENTITY_ANCHORING_CONFIG_SCHEMA}
        if registry is not None:
            cfg = await registry.load_config(REPO_ENTITY_ANCHORING_JOB_KEY)
            knobs.update(cfg.config or {})

        async with session_factory() as session:
            outcome = await refresh_repo_entity_anchors(
                session, llm,
                missing_batch=int(knobs["missing_batch"]),
                chunk_size=int(knobs["embed_chunk"]),
            )
            await session.commit()

        if outcome.written:
            logger.info(
                "Repo entity anchoring: %d entities embedded under %s",
                outcome.written, outcome.fingerprint,
            )
    return run


def make_repo_entity_merge_runner(
    app,
    session_factory: async_sessionmaker[AsyncSession],
):
    """Fuse the near-named pairs the anchoring order left behind (T2.101).

    Tier C, and deliberately not a dreaming-family member for the same reason
    `repo_entity_anchoring` is not: contract 6 fixes that family at six, and
    this is a graph repair in the class doc 10 §6 owns. Invariant 15 is
    unaffected — neither capture nor retrieval reaches this runner.

    The pass reads vectors rather than producing them, so the orchestrator is
    needed only to name the fingerprint a partition read may key on. Without
    one there is nothing to resolve, so the run is a no-op rather than a
    failure.
    """
    async def run() -> None:
        from app.services.entity_merge import (
            REPO_ENTITY_MERGE_CONFIG_SCHEMA,
            REPO_ENTITY_MERGE_JOB_KEY,
            merge_repo_entity_duplicates,
        )

        llm = getattr(app.state, "llm", None)
        if llm is None:
            logger.info("repo_entity_merge skipped: no LLM orchestrator")
            return

        registry = getattr(app.state, "job_registry", None)
        knobs = {fd.key: fd.default for fd in REPO_ENTITY_MERGE_CONFIG_SCHEMA}
        if registry is not None:
            cfg = await registry.load_config(REPO_ENTITY_MERGE_JOB_KEY)
            knobs.update(cfg.config or {})

        async with session_factory() as session:
            outcome = await merge_repo_entity_duplicates(
                session, llm, candidate_batch=int(knobs["candidate_batch"]),
            )
            await session.commit()

        if outcome.merged:
            logger.info(
                "Repo entity merge: %d pair(s) fused of %d probed under %s",
                outcome.merged, outcome.probed, outcome.fingerprint,
            )
    return run


def make_citation_reverify_runner(
    app,
    session_factory: async_sessionmaker[AsyncSession],
):
    """Re-resolve code citations against each repository's current HEAD.

    Tier C, and not a dream-job family member — contract 6 fixes that family at
    six, and the PPR snapshot is the standing precedent for a scheduled Tier-C
    job outside it. Invariant 15 binds by proximity: a re-index **enqueues**,
    and this job is what the enqueue eventually feeds; neither capture nor
    retrieval may reach it.

    No orchestrator and no model: re-resolution is two indexed lookups and a
    jsonb write, so the run is meaningful in Postgres-only mode where the
    model-spending runners degrade to a no-op.
    """
    async def run() -> None:
        from app.services.citation_reverify import (
            CITATION_REVERIFY_CONFIG_SCHEMA,
            CITATION_REVERIFY_JOB_KEY,
            DEFAULT_REVERIFY_BATCH,
            reverify_citations,
        )

        knobs = {fd.key: fd.default for fd in CITATION_REVERIFY_CONFIG_SCHEMA}
        registry = getattr(app.state, "job_registry", None)
        if registry is not None:
            cfg = await registry.load_config(CITATION_REVERIFY_JOB_KEY)
            knobs.update(cfg.config or {})

        async with session_factory() as session:
            outcome = await reverify_citations(
                session,
                batch_size=int(knobs.get("batch_size", DEFAULT_REVERIFY_BATCH)),
            )
            await session.commit()

        if outcome.marked_stale or outcome.cleared:
            logger.info(
                "Citation re-verify: %d stale, %d cleared, %d facts enqueued",
                outcome.marked_stale, outcome.cleared, outcome.facts_enqueued,
            )
    return run


_PPR_STATE_CONFIG_KEY = "job:ppr_snapshot:state"


async def _load_ppr_cursor(
    session_factory: async_sessionmaker[AsyncSession],
) -> str | None:
    from app.models.config import Config

    async with session_factory() as session:
        row = (
            await session.execute(
                select(Config).where(Config.key == _PPR_STATE_CONFIG_KEY)
            )
        ).scalar_one_or_none()
        if row is None or not isinstance(row.value, dict):
            return None
        cursor = row.value.get("last_project")
        return cursor if isinstance(cursor, str) and cursor else None


async def _save_ppr_cursor(
    session_factory: async_sessionmaker[AsyncSession],
    last_project: str | None,
) -> None:
    from app.models.config import Config

    async with session_factory() as session:
        row = (
            await session.execute(
                select(Config).where(Config.key == _PPR_STATE_CONFIG_KEY)
            )
        ).scalar_one_or_none()
        value = {"last_project": last_project}
        if row is None:
            session.add(Config(key=_PPR_STATE_CONFIG_KEY, value=value))
        else:
            row.value = value
        await session.commit()


LLM_USAGE_CLEANUP_JOB_KEY = "llm_usage_cleanup"
LLM_USAGE_RETENTION_DAYS_DEFAULT = 90
LLM_USAGE_CONFIG_SCHEMA = [
    FieldDescriptor(
        key="retention_days", label="Retention (days)",
        default=LLM_USAGE_RETENTION_DAYS_DEFAULT, min=1, max=3650,
        help="Calls older than this are deleted. Cost history beyond it is gone.",
    ),
]


def make_llm_usage_cleanup_runner(app, session_factory: async_sessionmaker[AsyncSession]):
    """Prune ``llm_usage`` to its retention window.

    Trimmed by age, not by row count -- the opposite of ``job_run_cleanup``
    beside it, and deliberately. The question this table answers is "what did
    the last N days cost", so a row ceiling would silently shorten the answer
    during exactly the busy period an operator is investigating. The cost of
    the choice is that a burst inside the window is unbounded on disk; that is
    the right trade for a table whose whole value is its window.
    """
    async def run() -> dict | int:
        from sqlalchemy import text as sa_text

        registry = getattr(app.state, "job_registry", None)
        retention = LLM_USAGE_RETENTION_DAYS_DEFAULT
        if registry is not None:
            cfg = await registry.load_config(LLM_USAGE_CLEANUP_JOB_KEY)
            retention = int(
                cfg.config.get("retention_days", LLM_USAGE_RETENTION_DAYS_DEFAULT)
            )

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention)
        async with session_factory() as session:
            deleted = (await session.execute(
                sa_text("DELETE FROM llm_usage WHERE occurred_at < :cutoff"),
                {"cutoff": cutoff},
            )).rowcount
            await session.commit()

        if not deleted:
            # 0, not {}: the no-op signal keeps a nightly sweep over a clean
            # table from writing a job_runs row every night to say nothing.
            return 0
        logger.info(
            "llm_usage_cleanup: deleted %s row(s) older than %s days",
            deleted, retention,
        )
        return {"deleted": deleted, "retention_days": retention}
    return run


JOB_RUN_CLEANUP_JOB_KEY = "job_run_cleanup"
JOB_RUN_RETAIN_DEFAULT = 5000


def make_job_run_cleanup_runner(app, session_factory: async_sessionmaker[AsyncSession]):
    """Hold ``job_runs`` to its configured ceiling, newest kept.

    The reason this job exists at all: run telemetry used to go into
    ``events``, which is append-only by trigger and permanent by ruling, so
    nothing could ever remove it. ``job_runs`` is an ordinary table precisely
    so this sweep is possible.

    Trims by row count rather than by age. Age is the wrong knob here — a
    quiet week and a busy week produce wildly different volumes, and the thing
    an operator actually wants to bound is how much of the disk this can take.
    """
    async def run() -> dict:
        from sqlalchemy import text as sa_text

        registry = getattr(app.state, "job_registry", None)
        retain = JOB_RUN_RETAIN_DEFAULT
        if registry is not None:
            cfg = await registry.load_config(JOB_RUN_CLEANUP_JOB_KEY)
            retain = int(cfg.config.get("max_rows", JOB_RUN_RETAIN_DEFAULT))

        async with session_factory() as session:
            # One statement: keep the newest `retain` by (started_at, id) and
            # delete the rest. The id tie-break keeps the cut deterministic
            # when several runs share a timestamp.
            deleted = (await session.execute(
                sa_text(
                    "DELETE FROM job_runs WHERE id IN ("
                    "  SELECT id FROM job_runs"
                    "  ORDER BY started_at DESC, id DESC"
                    "  OFFSET :retain"
                    ")"
                ),
                {"retain": retain},
            )).rowcount
            await session.commit()

        if not deleted:
            return {}
        logger.info("job_run_cleanup: trimmed %s row(s) to ceiling %s", deleted, retain)
        return {"deleted": deleted, "retained": retain}
    return run


def make_block_embedding_runner(
    app,
    session_factory: async_sessionmaker[AsyncSession],
):
    """Keep blocks embedded under the active fingerprint (spec 2026-08-23).

    Documents and pages sweep on separate budgets so neither owner's
    backlog delays the other's.

    Tier C, and deliberately not a dreaming-family member: contract 6 fixes
    that family at six, and this is an artefact refresh in the same class as
    `ppr_snapshot` and `relation_embedding_refresh`. It is the backstop
    `put_document`'s inline embed cannot be — an embed call that failed
    after its filing already committed, an embedder rotation that strands
    existing blocks in a dead partition, or a document filed before this
    door shipped. Off the hot path, never inside capture.

    Without an orchestrator there is nothing to embed with, so the run is a
    no-op rather than a failure — the same stance every other model-spending
    runner takes in Postgres-only mode.
    """
    async def run() -> None:
        from app.services.block_embedding_refresh import (
            BLOCK_EMBEDDING_CONFIG_SCHEMA,
            BLOCK_EMBEDDING_JOB_KEY,
            refresh_block_embeddings,
        )
        from app.services.events import record_event

        llm = getattr(app.state, "llm", None)
        if llm is None:
            logger.info("block_embedding_refresh skipped: no LLM orchestrator")
            return

        registry = getattr(app.state, "job_registry", None)
        knobs = {fd.key: fd.default for fd in BLOCK_EMBEDDING_CONFIG_SCHEMA}
        if registry is not None:
            cfg = await registry.load_config(BLOCK_EMBEDDING_JOB_KEY)
            knobs.update(cfg.config or {})

        # A mismatched fingerprint raises out of refresh_block_embeddings and
        # is deliberately NOT caught here: with the fingerprint resolved from
        # a real embed call (T-doc-door.6 review, round 2), a mismatch can
        # only mean the active embedder's config changed mid-run, and letting
        # it propagate is what lands it in job_runs.last_error where an
        # operator sees it, rather than silently reporting a batch converged
        # under a fingerprint this run never verified.
        async with session_factory() as session:
            outcome = await refresh_block_embeddings(
                session, llm,
                batch=int(knobs["batch"]),
                page_batch=int(knobs["page_batch"]),
                worklog_batch=int(knobs["worklog_batch"]),
            )
            if outcome.embedded:
                journalled = await record_event(
                    session,
                    event_type="block_embeddings_refreshed",
                    object_type="system",
                    payload={
                        "embedded": outcome.embedded,
                        "fingerprint": outcome.fingerprint,
                        "converged": outcome.converged,
                        "failed": outcome.failed,
                    },
                )
                await session.commit()
                if not journalled:
                    logger.warning(
                        "block_embedding_refresh: embedded %d block(s) under %s unjournalled",
                        outcome.embedded, outcome.fingerprint,
                    )

        if outcome.embedded:
            logger.info(
                "Block embeddings: %d embedded under %s (converged=%s, failed=%d)",
                outcome.embedded, outcome.fingerprint, outcome.converged,
                outcome.failed,
            )
    return run


def make_backup_ship_runner(app, session_factory: async_sessionmaker[AsyncSession]):
    """Dump over the stack network, encrypt, ship, verify, prune (spec 9.3).

    Does NOT shell to scripts/backup.sh -- the container cannot reach it (M4):
    no compose binary, no docker socket, no mount onto the host's backup
    directory. The systemd timer stays as the independent host-side producer,
    separated from this one by directory and filename prefix, not by any lock
    (m4): different processes, and the per-job asyncio.Lock binds in-process
    only. The 04:30 default cron is what keeps the two an hour apart.
    """
    async def run() -> dict:
        from app.services.backup_ship import ship_all

        return await ship_all(session_factory)

    return run

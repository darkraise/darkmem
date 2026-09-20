import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.git_accounts import GitAccountInUse
from starlette.middleware.gzip import GZipMiddleware

from sqlalchemy import text

from app.api.mcp.server import mcp as mcp_server, mcp_streamable_http_kwargs, set_pipeline
from app.api.spa import mount_spa
from app.api.routes import analytics, backups, api_keys as api_key_routes, git_accounts as git_account_routes, articles as articles_routes, auth, buffer as buffer_routes, chat, checkpoints as checkpoint_routes, code, config, distribution as distribution_routes, documents as documents_routes, dream_digest as dream_digest_routes, events as events_routes, facts as facts_routes, graph, hygiene_queue, jobs, knowledge_search as knowledge_search_routes, llm_providers, memories, overview as overview_routes, pages as pages_routes, page_attachments as page_attachments_routes, pipeline as pipeline_routes, pipeline_failures, projects as projects_routes, ratification as ratification_routes, reembed, repos, review_queue, setup, system, tags, topics as topics_routes, usage as usage_routes, vectors
from app.api.websocket import websocket_endpoint
from sqlalchemy.exc import DBAPIError

from app.config import settings
from app.schemas.envelope import ErrorDetail, ErrorEnvelope
from app.services.events import reconcile_event_partitions
from app.services.llm import LLMOrchestrator
from app.services.llm_quirks import models_probe
from app.services.pipeline import ProcessingPipeline
from app.services.project_registry import backfill as backfill_projects, seed_personal_project

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure application logging once at import.

    Without this, app loggers inherit uvicorn's defaults (root at WARNING), so
    most ``logger.info`` lines — pipeline lifecycle, LLM token telemetry — are
    silently dropped. ``force=True`` reconfigures even if uvicorn already added
    handlers. Level is driven by LOG_LEVEL.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
    logging.getLogger("app").setLevel(level)


_configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import async_session_factory

    pipeline = None
    llm = None

    # Outside every degrading try below: an unwritable attachments volume
    # must refuse boot, not start an app whose uploads all fail.
    from app.services.page_attachments import assert_attachments_dir_usable

    assert_attachments_dir_usable(read_only=settings.read_only)

    # Load UI-editable system prompts from the DB before anything else needs
    # them (extraction and classification call `prompt.get()` synchronously).
    try:
        from app.services import prompt as _prompt_mod
        async with async_session_factory() as _s:
            await _prompt_mod.refresh_from_db(_s)
        logger.info("Loaded %d system prompt overrides from DB", len(_prompt_mod.get_overrides()))
    except Exception:
        logger.exception("Could not load system_prompts overrides; falling back to in-code defaults")

    try:
        from app.services.config import get_llm_config
        from app.services.usage_recorder import UsageRecorder
        from app.services.embedder_registry import (
            EmbedderInfo, embedder_registry, parse_fingerprint,
        )
        async with async_session_factory() as session:
            llm_config = await get_llm_config(session)
        # The recorder is what makes the metering exist at all: every spending
        # path in the orchestrator reports to `self._recorder`, and one built
        # without it measures nothing while looking identical from outside.
        llm = LLMOrchestrator(
            llm_config, recorder=UsageRecorder(async_session_factory),
        )

        # Hydrate the in-process registry cache from existing rows so that
        # already-known fingerprints don't trigger redundant DDL.
        async with async_session_factory() as session:
            await embedder_registry.warm_cache_from_db(session)

        if settings.read_only:
            # Increment 7's worker posture. The four reconciliations below all
            # degrade under a caught exception, so the SELECT-only role would
            # make them inert anyway -- but depending on a swallowed exception
            # for correctness is the shape review B1 condemns, and a restored
            # snapshot already carries every partition these would create.
            logger.info(
                "DARKMEM_READ_ONLY: boot reconciliations, project backfill and "
                "embedder registration skipped; job registry will not be armed. "
                "Enforcement is the database role, not this flag."
            )
        else:
            # Permanent boot-time partition reconciliation (doc 19 §2). Runs on
            # EVERY startup, after the migration and before anything embeds, so a
            # fingerprint registered before a template was added gains the new
            # parent, and a restored dump missing a child table regrows it. Every
            # statement is IF NOT EXISTS, so the second boot is a no-op.
            try:
                async with async_session_factory() as session:
                    await embedder_registry.reconcile(session)
            except Exception:
                logger.exception("Boot-time partition reconciliation failed")

            # The events journal keeps its monthly children ahead of need on the
            # same boot pass. A missing child does not degrade journaling, it stops
            # it: a RANGE parent rejects any insert with no matching partition.
            try:
                async with async_session_factory() as session:
                    children = await reconcile_event_partitions(session)
                    await session.commit()
                logger.info("events partitions reconciled: %s", ", ".join(children))
            except Exception:
                logger.exception("Boot-time events partition reconciliation failed")

            # Backfill every DISTINCT memories.project into the registry on every
            # boot (doc 04 §7, T2.07). Idempotent (`ON CONFLICT DO NOTHING`), so a
            # restart with nothing new to backfill inserts zero rows; this is a
            # reconciliation pass, not a migration, and lazy registration on
            # capture (project_registry.register) is what keeps it caught up
            # between boots.
            try:
                async with async_session_factory() as session:
                    await seed_personal_project(session)
                    inserted = await backfill_projects(session)
                    await session.commit()
                logger.info("projects registry backfilled: %d row(s)", inserted)
            except Exception:
                logger.exception("Boot-time projects registry backfill failed")

            llm_fp = llm.llm_fingerprint()
            try:
                llm_model_id, llm_dims = parse_fingerprint(llm_fp)
                async with async_session_factory() as session:
                    await embedder_registry.register(
                        session,
                        EmbedderInfo(
                            fingerprint=llm_fp, model_id=llm_model_id,
                            dims=llm_dims, source="llm",
                        ),
                    )
            except Exception:
                logger.exception("Failed to register LLM embedder %s at boot", llm_fp)

        from app.api.websocket import event_manager
        pipeline = ProcessingPipeline(llm, async_session_factory, broadcast=event_manager.broadcast)
        app.state.pipeline = pipeline
        app.state.llm = llm
        app.state.session_factory = async_session_factory
        logger.info("Pipeline initialized: pgvector + LLM connected")
    except Exception:
        logger.exception("Pipeline not available (Postgres-only mode)")
        app.state.pipeline = None
        app.state.session_factory = async_session_factory

    set_pipeline(pipeline)

    # Single shared lock for LLM config / provider / profile writes. Routes
    # used to lazy-create on first touch, which raced under concurrent
    # save clicks (each request saw None, each created its own Lock, the
    # second store overwrote the first — neither serialized).
    app.state.llm_config_lock = asyncio.Lock()

    # The repo_sync_wakeup event is owned by the JobRegistry below and
    # exposed on app.state so route handlers (PUT /repos/{id}) can poke
    # it without depending on the registry import.
    app.state.repo_sync_wakeup = None  # set after registry init

    from app.api.mcp.server import refresh_mcp_instructions
    refresh_mcp_instructions()

    # Feature 2: register retry handlers for the failure tracking system
    from app.services.pipeline_failures import register_retry_handler
    from app.services.code_pipeline import CodePipeline
    from app.services.repo_manager import RepoManager
    from app.repositories.vector import PostgresVectorRepository

    if pipeline is not None:
        _pipeline_ref = pipeline

        @register_retry_handler("memory_ingest")
        async def _retry_memory(memory_id):
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from app.models.memory import Memory
            async with async_session_factory() as s:
                mem = (await s.execute(
                    select(Memory).options(selectinload(Memory.tags)).where(Memory.id == memory_id)
                )).scalar_one_or_none()
                if not mem:
                    return
                entry = {
                    "memory_id": mem.id,
                    "content": mem.content,
                    "source": mem.source,
                    "tags": [t.name for t in mem.tags],
                    "memory_type": mem.memory_type,
                    "created_at": mem.created_at.isoformat() if mem.created_at else "",
                }
            await _pipeline_ref.process_batch([entry])

        @register_retry_handler("code_index")
        async def _retry_code_index(repo_id):
            async with async_session_factory() as s:
                code_vector_repo = PostgresVectorRepository(s, "code_chunks")
                active_llm = getattr(app.state, "llm", None)
                pipeline = CodePipeline(
                    session=s, llm=active_llm,
                    vector_repo=code_vector_repo,
                    repo_manager=RepoManager(s),
                )
                await pipeline.run(repo_id)
                await s.commit()

    # ── Job registry: replaces the previous four bare asyncio loops ──
    from app.services.buffer_flush import (
        BUFFER_FLUSH_CONFIG_SCHEMA,
        BUFFER_FLUSH_CRON,
        BUFFER_FLUSH_JOB_KEY,
        BUFFER_FLUSH_MAX_RUN_SECONDS,
        BUFFER_FLUSH_MIN_INTERVAL_SECONDS,
    )
    from app.services.job_registry import FieldDescriptor, Job, JobRegistry
    from app.services.job_runners import (
        JOB_RUN_CLEANUP_JOB_KEY,
        LLM_USAGE_CLEANUP_JOB_KEY,
        LLM_USAGE_CONFIG_SCHEMA,
        make_job_run_cleanup_runner,
        make_llm_usage_cleanup_runner,
        make_repo_sync_runner,
        make_buffer_flush_runner,
        make_code_enrichment_runner,
        make_token_blocklist_cleanup_runner,
        make_pipeline_failure_cleanup_runner,
        make_graph_orphan_cleanup_runner,
        make_tag_orphan_cleanup_runner,
        make_expired_memory_cleanup_runner,
        make_ppr_snapshot_runner,
        make_relation_embedding_runner,
        make_repo_entity_anchoring_runner,
        make_repo_entity_merge_runner,
        make_code_deriver_runner,
        make_citation_reverify_runner,
        make_block_embedding_runner,
        make_backup_ship_runner,
    )
    from app.services.backup_ship import BACKUP_SHIP_JOB_KEY, BACKUP_SHIP_MAX_RUN_SECONDS
    from app.services.entity_anchoring import (
        REPO_ENTITY_ANCHORING_CONFIG_SCHEMA,
        REPO_ENTITY_ANCHORING_JOB_KEY,
    )
    from app.services.entity_merge import (
        REPO_ENTITY_MERGE_CONFIG_SCHEMA,
        REPO_ENTITY_MERGE_JOB_KEY,
    )
    from app.services.citation_reverify import (
        CITATION_REVERIFY_CONFIG_SCHEMA,
        CITATION_REVERIFY_CRON,
        CITATION_REVERIFY_JOB_KEY,
        CITATION_REVERIFY_MAX_RUN_SECONDS,
        CITATION_REVERIFY_MIN_INTERVAL_SECONDS,
    )
    from app.services.ppr_snapshot import (
        PPR_SNAPSHOT_CONFIG_SCHEMA,
        PPR_SNAPSHOT_JOB_KEY,
    )
    from app.services.relation_embeddings import (
        RELATION_EMBEDDING_CONFIG_SCHEMA,
        RELATION_EMBEDDING_JOB_KEY,
    )
    from app.services.block_embedding_refresh import (
        BLOCK_EMBEDDING_CONFIG_SCHEMA,
        BLOCK_EMBEDDING_CRON,
        BLOCK_EMBEDDING_JOB_KEY,
        BLOCK_EMBEDDING_MAX_RUN_SECONDS,
        BLOCK_EMBEDDING_MIN_INTERVAL_SECONDS,
    )
    from app.services.code_deriver_job import (
        CODE_DERIVER_CRON,
        CODE_DERIVER_JOB_KEY,
        CODE_DERIVER_MAX_RUN_SECONDS,
        CODE_DERIVER_MIN_INTERVAL_SECONDS,
    )
    from app.services.dream_jobs import register_dream_jobs

    job_registry = JobRegistry(async_session_factory)
    job_registry.register(Job(
        key="repo_sync",
        display_name="Repository Sync",
        description=(
            "Per repo, on that repo's own intervals: fetches when Fetch from "
            "remote is on, and indexes when Index on new commit is on and HEAD "
            "has moved. Every switch is off by default. Manual reindex, the "
            "webhook and the code_reindex MCP tool bypass this loop entirely."
        ),
        default_cron="*/30 * * * * *",
        min_interval_seconds=15,
        runner=make_repo_sync_runner(app, async_session_factory),
        max_run_seconds=1800,
    ))
    job_registry.register(Job(
        key=BUFFER_FLUSH_JOB_KEY,
        display_name="Buffer Flush",
        description=(
            "Claims accepted-but-unprocessed captures from the ingest buffer "
            "and runs them through the five-phase pipeline. Disabling this "
            "stops every 202-accepted capture from ever becoming a memory."
        ),
        default_cron=BUFFER_FLUSH_CRON,
        min_interval_seconds=BUFFER_FLUSH_MIN_INTERVAL_SECONDS,
        runner=make_buffer_flush_runner(app, async_session_factory),
        max_run_seconds=BUFFER_FLUSH_MAX_RUN_SECONDS,
        config_schema=BUFFER_FLUSH_CONFIG_SCHEMA,
    ))
    job_registry.register(Job(
        key=JOB_RUN_CLEANUP_JOB_KEY,
        display_name="Job History Cleanup",
        description=(
            "Trims job_runs to its configured ceiling, newest kept. Run "
            "telemetry used to land in the append-only events table where "
            "nothing could remove it; this is what keeps its replacement "
            "bounded."
        ),
        # Weekly. The ceiling is what bounds the table, so the cadence only
        # decides how far past it the table may drift between sweeps.
        default_cron="0 4 * * 0",
        min_interval_seconds=3600,
        runner=make_job_run_cleanup_runner(app, async_session_factory),
        config_schema=[FieldDescriptor(
            key="max_rows", label="Max rows retained",
            default=5000, min=100, max=1000000,
            help="Rows kept after a sweep, newest first.",
        )],
    ))

    job_registry.register(Job(
        key=LLM_USAGE_CLEANUP_JOB_KEY,
        display_name="LLM Usage Retention",
        description=(
            "Deletes llm_usage rows past the retention window. Trimmed by age "
            "rather than by row count, because the question this table answers "
            "is what the last N days cost -- a row ceiling would shorten that "
            "answer during exactly the busy period worth investigating."
        ),
        # Nightly, after the backup timer's 03:30 so a sweep never races a dump.
        default_cron="0 4 * * *",
        min_interval_seconds=3600,
        runner=make_llm_usage_cleanup_runner(app, async_session_factory),
        config_schema=LLM_USAGE_CONFIG_SCHEMA,
    ))

    from app.services.page_attachment_cleanup import (
        PAGE_ATTACHMENT_CLEANUP_CONFIG_SCHEMA,
        PAGE_ATTACHMENT_CLEANUP_JOB_KEY,
        make_page_attachment_cleanup_runner,
    )

    job_registry.register(Job(
        key=PAGE_ATTACHMENT_CLEANUP_JOB_KEY,
        display_name="Page Attachment Cleanup",
        description=(
            "Deletes page attachments no page block references once they are "
            "past the grace period, files left with no row by a crash, and "
            "stale import staging directories. Trashed pages still count as "
            "references, so emptying the trash is what releases a file."
        ),
        default_cron="20 * * * *",
        min_interval_seconds=600,
        runner=make_page_attachment_cleanup_runner(app, async_session_factory),
        config_schema=PAGE_ATTACHMENT_CLEANUP_CONFIG_SCHEMA,
    ))

    job_registry.register(Job(
        key=BACKUP_SHIP_JOB_KEY,
        display_name="Backup Ship",
        description=(
            "Dumps the database over the stack network with the image's own "
            "pg_dump, encrypts with the destination's age recipient, ships to "
            "every enabled destination, reads each upload back to verify it, "
            "and prunes per destination. Independent of the host-side systemd "
            "backup timer by design -- two producers, no shared lock."
        ),
        # 04:30 -- an hour clear of the systemd timer's 03:30, because nothing
        # can serialise the two producers (m4) and dumping twice concurrently
        # doubles I/O on the same Postgres for no benefit.
        default_cron="30 4 * * *",
        min_interval_seconds=3600,
        runner=make_backup_ship_runner(app, async_session_factory),
        max_run_seconds=BACKUP_SHIP_MAX_RUN_SECONDS,
    ))

    job_registry.register(Job(
        key="code_enrichment",
        display_name="Code Symbol Enrichment",
        description=(
            "Runs one batch of LLM summarisation against pending code "
            "symbols (function / class / method docs)."
        ),
        default_cron="*/10 * * * * *",
        min_interval_seconds=1,
        runner=make_code_enrichment_runner(app, async_session_factory),
        max_run_seconds=600,
        config_schema=[FieldDescriptor(
            key="batch_size", label="Batch Size", default=5,
            min=1, max=100,
            help="Code symbols summarised per scheduled run.",
        )],
    ))
    job_registry.register(Job(
        key=CODE_DERIVER_JOB_KEY,
        display_name="Code Graph Deriver",
        description=(
            "Derives each indexed repository's Layer-1 graph assertions from "
            "its import edges (doc 10 §6) — the repo itself, its external "
            "dependencies and languages — into entities.repo_ids[] / "
            "entity_relations.repo_ids[]. Off the reindex path by design: a "
            "derivation failure here is journaled under its own "
            "pipeline_name and never fails an index run."
        ),
        default_cron=CODE_DERIVER_CRON,
        min_interval_seconds=CODE_DERIVER_MIN_INTERVAL_SECONDS,
        runner=make_code_deriver_runner(async_session_factory),
        max_run_seconds=CODE_DERIVER_MAX_RUN_SECONDS,
    ))
    job_registry.register(Job(
        key="token_blocklist_cleanup",
        display_name="Token Blocklist Cleanup",
        description=(
            "Deletes expired entries from the auth token blocklist. Safe "
            "to leave on; disable only if you are debugging revocation."
        ),
        default_cron="0 * * * *",
        min_interval_seconds=60,
        runner=make_token_blocklist_cleanup_runner(async_session_factory),
        max_run_seconds=300,
    ))
    job_registry.register(Job(
        key="pipeline_failure_cleanup",
        display_name="Pipeline Failure Cleanup",
        description=(
            "Prunes orphaned pipeline-failure rows and resolved entries "
            "older than 30 days, AND keeps the events journal's monthly "
            "partitions ahead of need. Leave this on: with it disabled, a "
            "process running past the current partition horizon stops "
            "journaling entirely, because a RANGE parent rejects any row with "
            "no partition to land in."
        ),
        default_cron="0 * * * *",
        min_interval_seconds=60,
        runner=make_pipeline_failure_cleanup_runner(async_session_factory),
        max_run_seconds=300,
    ))
    job_registry.register(Job(
        key="graph_orphan_cleanup",
        display_name="Graph Orphan Cleanup",
        description=(
            "Prunes entity-graph ghosts — entities and relations that no "
            "live memory asserts any more (left by deleted memories). Keeps "
            "entity dedup from collapsing fresh entities onto stale ghosts. "
            "Safe to leave on."
        ),
        default_cron="0 * * * *",
        min_interval_seconds=60,
        runner=make_graph_orphan_cleanup_runner(async_session_factory),
        max_run_seconds=300,
    ))
    job_registry.register(Job(
        key="tag_orphan_cleanup",
        display_name="Tag Orphan Cleanup",
        description=(
            "Prunes tags no live memory carries any more (left behind when "
            "memories are deleted). Keeps the dashboard tag count and the tag "
            "filter from showing unused tags. Safe to leave on."
        ),
        default_cron="0 * * * *",
        min_interval_seconds=60,
        runner=make_tag_orphan_cleanup_runner(async_session_factory),
        max_run_seconds=300,
    ))
    job_registry.register(Job(
        key="expired_memory_cleanup",
        display_name="Expired Memory Cleanup",
        description=(
            "Deletes memories past their expires_at TTL. Without this a "
            "client-set TTL is never honored. Safe to leave on."
        ),
        default_cron="0 * * * *",
        min_interval_seconds=60,
        runner=make_expired_memory_cleanup_runner(async_session_factory),
        max_run_seconds=300,
    ))
    job_registry.register(Job(
        key=PPR_SNAPSHOT_JOB_KEY,
        display_name="PPR Graph Snapshot",
        description=(
            "Rebuilds the cached in-process entity-graph snapshot the PPR "
            "retrieval arm ranks against (doc 07 §4), one rotating batch of "
            "projects per run. Off the hot path by design: retrieval reads "
            "the snapshot and can never trigger a build. Leaving this off "
            "costs nothing while ppr_enabled is off, and starves the arm of "
            "a snapshot once it is on."
        ),
        default_cron="30 * * * *",
        min_interval_seconds=300,
        runner=make_ppr_snapshot_runner(app, async_session_factory),
        max_run_seconds=900,
        config_schema=PPR_SNAPSHOT_CONFIG_SCHEMA,
    ))
    job_registry.register(Job(
        key=RELATION_EMBEDDING_JOB_KEY,
        display_name="Relation Embedding Refresh",
        description=(
            "Keeps the relation_embeddings partition current for the "
            "dual-level retrieval channel (doc 07 §4): embeds relations that "
            "have no vector under the active embedder, then rotates the "
            "oldest embedded slice so a renamed entity's stale vector is "
            "corrected. Off the hot path — never inside capture. Each run "
            "spends embedding calls, so 0 on either batch disables that arm."
        ),
        default_cron="15 * * * *",
        min_interval_seconds=300,
        runner=make_relation_embedding_runner(app, async_session_factory),
        max_run_seconds=900,
        config_schema=RELATION_EMBEDDING_CONFIG_SCHEMA,
    ))
    job_registry.register(Job(
        key=BLOCK_EMBEDDING_JOB_KEY,
        display_name="Block Embedding Refresh",
        description=(
            "Embeds document blocks that have no vector under the active "
            "embedder: an embed that failed after its filing committed, an "
            "embedder rotation, or documents filed before the door shipped. "
            "Off the hot path. Each run spends embedding calls, so 0 disables "
            "it."
        ),
        default_cron=BLOCK_EMBEDDING_CRON,
        min_interval_seconds=BLOCK_EMBEDDING_MIN_INTERVAL_SECONDS,
        runner=make_block_embedding_runner(app, async_session_factory),
        max_run_seconds=BLOCK_EMBEDDING_MAX_RUN_SECONDS,
        config_schema=BLOCK_EMBEDDING_CONFIG_SCHEMA,
    ))
    job_registry.register(Job(
        key=REPO_ENTITY_ANCHORING_JOB_KEY,
        display_name="Repo Entity Anchoring",
        description=(
            "Embeds entities a repository asserts but no memory does, so the "
            "code bridge's dedup probe can see them (doc 10 §6). Without it a "
            "code-minted 'postgres' and a memory-minted 'postgresql' stay two "
            "nodes: they only merge on an exact name match. Off the hot path — "
            "the deriver that mints these rows is LLM-free by design, so the "
            "embed happens here instead."
        ),
        default_cron="45 * * * *",
        min_interval_seconds=300,
        runner=make_repo_entity_anchoring_runner(app, async_session_factory),
        max_run_seconds=900,
        config_schema=REPO_ENTITY_ANCHORING_CONFIG_SCHEMA,
    ))
    job_registry.register(Job(
        key=REPO_ENTITY_MERGE_JOB_KEY,
        display_name="Repo Entity Merge",
        description=(
            "Fuses a repository-asserted entity with the near-named node a "
            "memory already minted, at the same 0.85 threshold and under the "
            "same discriminator Phase 4 uses (doc 10 §6). Anchoring only "
            "closes the order where the repo is indexed first; a repo indexed "
            "after its memories — what every existing install produces — "
            "leaves 'postgres' and 'postgresql' as two nodes forever, because "
            "the deriver's write is an exact-key upsert with no probe. Off "
            "the hot path: it merges after the fact, never during capture."
        ),
        default_cron="50 * * * *",
        min_interval_seconds=300,
        runner=make_repo_entity_merge_runner(app, async_session_factory),
        max_run_seconds=900,
        config_schema=REPO_ENTITY_MERGE_CONFIG_SCHEMA,
    ))
    job_registry.register(Job(
        key=CITATION_REVERIFY_JOB_KEY,
        display_name="Citation Re-verify",
        description=(
            "Re-resolves every code citation's recorded symbol_key against "
            "its repository's current HEAD (doc 10 §6). A citation that no "
            "longer resolves is marked stale and its fact is queued for the "
            "verification recompute, which downgrades the badge — never "
            "expiring the fact, because a deleted symbol may be a rename a "
            "human should confirm. Leaving this off lets a badge keep "
            "claiming evidence that no longer exists."
        ),
        default_cron=CITATION_REVERIFY_CRON,
        min_interval_seconds=CITATION_REVERIFY_MIN_INTERVAL_SECONDS,
        runner=make_citation_reverify_runner(app, async_session_factory),
        max_run_seconds=CITATION_REVERIFY_MAX_RUN_SECONDS,
        config_schema=CITATION_REVERIFY_CONFIG_SCHEMA,
    ))

    # The Tier-C consolidation ("dreaming") family — doc 08 §5. Every member
    # is a placeholder until its owning task (T2.09-T2.14, T2.53) lands the
    # real runner; see app/services/dream_jobs.py.
    register_dream_jobs(job_registry, lambda: getattr(app.state, "llm", None))

    # Expose the repo_sync wakeup so PUT /repos/{id} can nudge the loop
    # immediately when a repo's fetch_enabled or index_on_commit_enabled
    # flips on. The registry owns the event; route handlers just call
    # .set() on it.
    repo_sync_job = job_registry.get("repo_sync")
    if repo_sync_job is not None:
        app.state.repo_sync_wakeup = repo_sync_job.wakeup

    # One-time copy of the legacy enrichment_config.batch_size into the
    # code_enrichment job config, if not already set. Tolerates an absent
    # enrichment_config row (it was created lazily by the removed
    # PUT /config/enrichment, so most installs never had it).
    #
    # Skipped under the worker's read-only posture. Unlike the boot
    # reconciliations above, this write has no `try` around it: under the
    # SELECT-only role it would not degrade, it would raise out of `lifespan`
    # and the worker would never boot.
    _ce_cfg = await job_registry.load_config("code_enrichment")
    if not settings.read_only and "batch_size" not in _ce_cfg.config:
        from app.models.config import Config as _Config
        from sqlalchemy import select as _select
        async with async_session_factory() as _s:
            _row = (await _s.execute(
                _select(_Config).where(_Config.key == "enrichment_config")
            )).scalar_one_or_none()
        _legacy = _row.value if _row and isinstance(_row.value, dict) else {}
        _bs = max(1, min(100, int(_legacy.get("batch_size", 5))))
        await job_registry.set_config("code_enrichment", {"batch_size": _bs})

    app.state.job_registry = job_registry
    # Registration stays unconditional -- it is in-process, writes nothing, and
    # keeps the Jobs page rendering on the worker. Only *arming* is gated: a
    # job's LLM calls, git fetches and egress happen client-side of the
    # database, so the viewer role never sees them, and `backup_ship` on a
    # worker would ship snapshots of snapshots.
    if not settings.read_only:
        await job_registry.start_all()

    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp_server.session_manager.run())
        yield

    await job_registry.stop_all()

    from app.services.task_registry import TaskRegistry
    TaskRegistry.cancel_all()

    # Tear down loaded HF classifier models and their idle-eviction watchdogs;
    # otherwise they leak across reload-heavy dev loops and graceful restarts.
    from app.services.ml_runtime import ml_model_manager
    try:
        await ml_model_manager.shutdown_all()
    except Exception:
        logger.warning("Failed to shut down ML model manager", exc_info=True)

    # Close whichever orchestrator is currently live, not the one from
    # startup — admin saves on the LLM Providers / LLM Config pages
    # replace ``app.state.llm`` mid-session, and the previous instance is
    # already closed by ``_replace_orchestrator``'s background task.
    current_llm = getattr(app.state, "llm", None) or llm
    if current_llm:
        try:
            await current_llm.close()
        except Exception:
            logger.warning("Failed to close active LLM orchestrator at shutdown", exc_info=True)


# The four security headers, the gzip threshold and the body cap below are
# nginx's own values, moved rather than retuned: the nginx-in-image fallback
# (doc 03 section 3.2) must present the same policy as the app-as-edge build,
# and a value that drifts here makes the two postures disagree.
#
# `img-src` is the one deliberate retune. A page block may hold an external
# image, which the original policy blocked outright. `http:` is left out: the
# LAN deployment serves plain HTTP, and allowing cleartext image loads would
# let a pasted note beacon a third party in the clear.
SECURITY_HEADERS = (
    ("x-frame-options", "DENY"),
    ("x-content-type-options", "nosniff"),
    ("referrer-policy", "strict-origin-when-cross-origin"),
    (
        "content-security-policy",
        "default-src 'self'; script-src 'self'; worker-src 'self' blob:; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
        "font-src 'self' data:; connect-src 'self' ws: wss:; object-src 'none'; "
        "frame-ancestors 'none'; base-uri 'self'",
    ),
)

GZIP_MINIMUM_SIZE = 1024
MAX_REQUEST_BODY_BYTES = 25 * 1024 * 1024


def is_mcp_path(path: str) -> bool:
    """Whether a request path belongs to the MCP mount.

    nginx deliberately never fronted /mcp, so none of its response duties nor
    its body cap ever applied there. Applying them now would widen a contract
    surface this task does not touch — most sharply the body cap, which would
    impose a new ceiling on MCP ingestion. One predicate, shared by all three
    middlewares, because two copies is how the surfaces drift apart.
    """
    return path == "/mcp" or path.startswith("/mcp/")


def is_attachment_upload_path(path: str) -> bool:
    """`POST /api/v1/pages/{page_id}/attachments` bounds its own body against
    `attachment_max_bytes`, on the declared length and on the stream; the edge
    cap would pin that setting at 25 MB."""
    return (
        path.startswith("/api/v1/pages/")
        and path.endswith("/attachments")
        and path.count("/") == 5
    )


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or is_mcp_path(scope.get("path", "")):
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS:
                    headers.setdefault(name, value)
            await send(message)

        await self.app(scope, receive, send_with_headers)


class ScopedGZipMiddleware:
    def __init__(self, app, minimum_size: int = GZIP_MINIMUM_SIZE):
        self.app = app
        self.gzip = GZipMiddleware(app, minimum_size=minimum_size)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and is_mcp_path(scope.get("path", "")):
            await self.app(scope, receive, send)
            return
        await self.gzip(scope, receive, send)


class RequestBodyLimitMiddleware:
    """Re-creates nginx's ``client_max_body_size 25m``, which leaves the
    shipped topology with it.

    This bounds requests that declare a Content-Length. A chunked request that
    declares none is NOT bounded here; doing that needs body-stream
    accounting, which is materially more code and is not this cap's job.
    """

    def __init__(self, app, max_bytes: int = MAX_REQUEST_BODY_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if scope["type"] == "http" and not is_mcp_path(path) and not is_attachment_upload_path(path):
            declared = Headers(scope=scope).get("content-length")
            if declared and declared.isdigit() and int(declared) > self.max_bytes:
                response = _error_response(
                    413, "payload_too_large", "Request body is too large"
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


# How often a refusal may write a journal row. The refusal itself is bounded by
# nothing an attacker controls; the journal is, so a public scanner must not be
# able to grow the events table one row per probe. In-process state, which is
# valid for the same reason the login limiter's is (invariant 13).
_PROXIED_MCP_JOURNAL_INTERVAL_SECONDS = 60.0
_last_proxied_mcp_journal = 0.0

# The headers that mean "this request reached us through the proxy". Read only
# to answer that yes/no question — never to derive an address, which is
# `_client_ip`'s job and is a different decision with different rules.
_FORWARDED_MARKERS = ("x-forwarded-for", "x-real-ip", "x-forwarded-proto")


class ProxiedMcpGuardMiddleware:
    """Refuse `/mcp` when it arrives through the proxy (T4.17).

    Every `/mcp` call has required a bearer API key since doc 18 §5's second
    activation (2026-08-26), so this guard's original premise — an
    unauthenticated door with no way to gate who reaches it — is gone. It
    still earns its place, for a reason a valid key cannot answer on its own:
    this guard asks "did this arrive from outside the trusted network",
    which is a question about *where a request came from*, not about
    whether its credential checks out. A leaked or intentionally shared key
    presented from outside the LAN would pass auth and scope checks cleanly;
    this middleware refuses it anyway, because MCP auth carries none of the
    login door's defence in depth — no lockout on repeated bad credentials,
    and every attempt (including a bare guess) still costs one fixed-cost
    bcrypt verification on the shared thread executor. Publishing `/mcp` is
    still not something a bearer requirement alone makes safe. Under
    `trust_proxy_headers` the box is exposed, and the E4 epic review's
    objection is precise: the gap was one allowlist entry from armed, and the
    standing advice for a LAN `421` ("extend the allowlist") points at exactly
    that entry. A runbook sentence is the wrong weight for a hole an operator
    can open by following unrelated correct advice.

    So this closes it in the direction that can only ever refuse more: with the
    exposed switch off, the middleware does nothing at all, and with it on, a
    request that did *not* come through the proxy is untouched. A local or LAN
    agent reaching `/mcp` directly keeps working in both postures — with or
    without a key, since this guard runs ahead of and independent of auth.

    This is **not** the Host allowlist and does not replace it. That guard
    answers "is this Host one I serve" and its refusal is `421`, fixed by
    extending the allowlist. This one answers "did this arrive from outside",
    and extending the allowlist does not fix it — which is the whole point.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or not is_mcp_path(scope.get("path", ""))
            or not settings.trust_proxy_headers
        ):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        if not any(headers.get(marker) for marker in _FORWARDED_MARKERS):
            await self.app(scope, receive, send)
            return

        await self._journal(headers)
        response = _error_response(
            403,
            "mcp_not_exposed",
            "/mcp is not served through a proxy: it must not be routed from "
            "outside the trusted network, even with a valid key. "
            "See docs/runbook-exposed-deployment.md.",
        )
        await response(scope, receive, send)

    async def _journal(self, headers) -> None:
        global _last_proxied_mcp_journal
        import time as _time  # noqa: PLC0415

        logger.warning(
            "Refused a proxied /mcp request — /mcp must not be routed publicly"
        )
        now = _time.monotonic()
        if now - _last_proxied_mcp_journal < _PROXIED_MCP_JOURNAL_INTERVAL_SECONDS:
            return
        _last_proxied_mcp_journal = now
        try:
            from app.database import async_session_factory  # noqa: PLC0415
            from app.services.events import record_event  # noqa: PLC0415

            async with async_session_factory() as journal_session:
                await record_event(
                    journal_session,
                    event_type="mcp_proxied_refused",
                    object_type="system",
                    source="mcp",
                    # No address and no Host: the point of the row is that it
                    # happened at all, and copying attacker-controlled strings
                    # into an append-only substrate is the write-time
                    # minimization rule saying no.
                    payload={"throttled_seconds": _PROXIED_MCP_JOURNAL_INTERVAL_SECONDS},
                )
                await journal_session.commit()
        except Exception:  # pragma: no cover - journalling must never refuse the refusal
            logger.warning("Could not journal the proxied /mcp refusal", exc_info=True)


app = FastAPI(title="darkmem", version="1.8.0", description="Centralized memory system for AI agents", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# add_middleware applies in reverse, so the last added is outermost: gzip
# compresses a body whose security headers are already set, and the body cap
# rejects before either does any work.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ScopedGZipMiddleware)
app.add_middleware(RequestBodyLimitMiddleware)
# Outermost of the MCP-relevant guards: a request refused here must not reach
# the mount at all.
app.add_middleware(ProxiedMcpGuardMiddleware)

_HTTP_ERROR_CODES = {
    400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found",
    405: "method_not_allowed", 409: "conflict", 413: "payload_too_large",
    422: "validation_error", 429: "rate_limited", 502: "upstream_error",
    503: "unavailable", 504: "upstream_timeout",
}


def _error_response(status_code: int, code: str, message: str, details=None, headers=None):
    from starlette.responses import JSONResponse

    return JSONResponse(
        status_code=status_code,
        content=ErrorEnvelope(
            error=ErrorDetail(code=code, message=message, details=details),
            # `detail` is a string mirror of error.message on EVERY shape,
            # including the 422 that FastAPI answers with a list today.
            # frontend/src/lib/api.ts interpolates this field straight into an
            # Error, so a list here renders a stringified array to the user.
            # T1.42b retires the mirror once the frontend reads error.message.
            detail=message,
        ).model_dump(),
        headers=headers,
    )


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(_request, exc: StarletteHTTPException):
    detail = exc.detail
    message = detail if isinstance(detail, str) else "Request failed"
    details = detail if isinstance(detail, list) else None
    code = _HTTP_ERROR_CODES.get(exc.status_code, f"http_{exc.status_code}")
    return _error_response(exc.status_code, code, message, details, getattr(exc, "headers", None))


@app.exception_handler(GitAccountInUse)
async def _git_account_in_use_handler(_request, exc: GitAccountInUse):
    """409 that names the repos still using the account.

    Its own handler because the generic HTTPException path keeps `details` only
    for a list and would otherwise drop both the list and the message.
    """
    return _error_response(409, "conflict", exc.message, exc.repos)


@app.exception_handler(RequestValidationError)
async def _validation_exception_handler(_request, exc: RequestValidationError):
    errors = jsonable_encoder(exc.errors())
    first = errors[0] if errors else {}
    location = ".".join(str(part) for part in first.get("loc", ())[1:])
    message = first.get("msg", "Request validation failed")
    if location:
        message = f"{location}: {message}"
    return _error_response(422, "validation_error", message, errors)


@app.exception_handler(DBAPIError)
async def _read_only_refusal(_request, exc: DBAPIError):
    """SQLSTATE 42501 -> 403 `read_only`, everything else untouched.

    The SELECT-only viewer role refusing a write is the read-only worker
    working as designed (review B1: enforcement below every code path). One
    SQLSTATE check replaces the per-route allowlist the review rejected --
    the route inventory rots, the error code cannot.

    **The re-raise is the design, not a gap.** Raising from inside a Starlette
    exception handler propagates to `ServerErrorMiddleware`, which reaches the
    `Exception` handler just below and produces the ordinary 500 envelope. A
    unique-violation or a syntax error therefore behaves exactly as it did
    before this handler existed.

    Registered on `DBAPIError` rather than `ProgrammingError` because that is
    the base every driver-level error inherits from; asyncpg's
    `InsufficientPrivilegeError.sqlstate` is where the code actually lives.
    """
    if getattr(getattr(exc, "orig", None), "sqlstate", None) == "42501":
        return _error_response(
            403,
            "read_only",
            "This instance is read-only; writes are refused at the database.",
        )
    raise exc


@app.exception_handler(Exception)
async def _unhandled_exception_handler(_request, exc: Exception):
    # Logged with the traceback, answered without one: an internal message can
    # carry a connection string or a row's contents, and this is the one
    # response shape a caller reaches by accident rather than by asking.
    logger.exception("unhandled exception on the request path", exc_info=exc)
    return _error_response(500, "internal_error", "Internal server error")


app.include_router(auth.router)
app.include_router(memories.router)
app.include_router(tags.router)
app.include_router(projects_routes.router)
app.include_router(graph.router)
app.include_router(analytics.router)
app.include_router(config.router)
app.include_router(backups.router)
app.include_router(llm_providers.router)
app.include_router(pipeline_routes.router)
app.include_router(vectors.router)
app.include_router(chat.router)
app.include_router(repos.router)
app.include_router(git_account_routes.router)
app.include_router(code.router)
app.include_router(pipeline_failures.router)
app.include_router(review_queue.router)
app.include_router(checkpoint_routes.router)
app.include_router(distribution_routes.router)
app.include_router(facts_routes.router)
app.include_router(articles_routes.router)
app.include_router(knowledge_search_routes.router)
app.include_router(ratification_routes.router)
app.include_router(overview_routes.router)
app.include_router(topics_routes.router)
app.include_router(hygiene_queue.router)
app.include_router(dream_digest_routes.router)
app.include_router(events_routes.router)
app.include_router(buffer_routes.router)
app.include_router(documents_routes.router)
app.include_router(pages_routes.router)
app.include_router(page_attachments_routes.router)
app.include_router(reembed.router)
app.include_router(usage_routes.router)
app.include_router(api_key_routes.router)
app.include_router(setup.router)
app.include_router(system.router)
app.include_router(jobs.router)


app.add_api_websocket_route("/ws", websocket_endpoint)

_mcp_app = mcp_server.streamable_http_app(**mcp_streamable_http_kwargs())


app.mount("/mcp", _mcp_app)


@app.get("/health")
async def health():
    import httpx
    from starlette.responses import JSONResponse
    from app.database import async_session_factory

    pipeline = getattr(app.state, "pipeline", None)
    llm = getattr(app.state, "llm", None)

    async def check_pgvector() -> bool:
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                )
                return result.scalar_one_or_none() is not None
        except Exception:
            return False

    async def check_llm() -> bool:
        """Light-weight reachability probe for the configured embedding provider.

        Resolves the probe endpoint and auth through the ``api_kind`` quirk
        table instead of assuming Ollama — the original implementation
        hard-coded ``/api/tags`` and stripped ``/v1`` with ``rstrip`` (which
        removes a character set, not a suffix), so it returned False for every
        cloud provider and surfaced as a permanent 503 even when the
        configured LLM was perfectly reachable.
        """
        try:
            embedding_cfg = llm.config.get("embedding") if llm else None
            if embedding_cfg is None or not embedding_cfg.base_url:
                return False
            target = models_probe(
                getattr(embedding_cfg, "api_kind", None),
                embedding_cfg.base_url,
                getattr(embedding_cfg, "api_key", None),
            )

            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(target.url, headers=target.headers)
            return resp.is_success
        except Exception:
            return False

    pgvector_ok, llm_ok = await asyncio.gather(check_pgvector(), check_llm())

    # Status-code policy:
    #   * pgvector is a hard dependency — without it none of the API works;
    #     a failure here returns 503 so orchestrators page on it.
    #   * The LLM is a soft dependency — UI, auth, config and repo endpoints
    #     all work without it. Report the truth in the body but keep the
    #     status code at 200 so a flaky vendor doesn't trigger noisy alerts.
    if not pgvector_ok:
        overall = "down"
        status_code = 503
    elif not llm_ok:
        overall = "degraded"
        status_code = 200
    else:
        overall = "ok"
        status_code = 200

    return JSONResponse(
        {
            "status": overall,
            "pipeline": pipeline is not None and pgvector_ok and llm_ok,
            "services": {
                "pgvector": pgvector_ok,
                "llm": llm_ok,
            },
        },
        status_code=status_code,
    )


def _resolve_spa_dir() -> Path:
    if settings.spa_dir:
        return Path(settings.spa_dir)
    return Path(__file__).resolve().parent.parent / "web"


# Registered last, after every router, the /ws route and the /mcp mount, so
# the catch-all mount shadows nothing.
mount_spa(app, _resolve_spa_dir())

import asyncio
import contextlib
import logging
import math
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
from app.api.routes import analytics, backups, board as board_routes, api_keys as api_key_routes, git_accounts as git_account_routes, articles as articles_routes, auth, buffer as buffer_routes, chat, code, config, distribution as distribution_routes, documents as documents_routes, dream_digest as dream_digest_routes, events as events_routes, facts as facts_routes, graph, hygiene_queue, jobs, knowledge_search as knowledge_search_routes, llm_providers, mcp_calls as mcp_calls_routes, memories, overview as overview_routes, pages as pages_routes, page_attachments as page_attachments_routes, page_import as page_import_routes, pipeline as pipeline_routes, pipeline_failures, projects as projects_routes, ratification as ratification_routes, reembed, repos, review_queue, setup, system, tags, topics as topics_routes, usage as usage_routes, worklog as worklog_routes
from app.api.websocket import websocket_endpoint
from sqlalchemy.exc import DBAPIError

from app.config import settings
from app.schemas.envelope import ErrorDetail, ErrorEnvelope
from app.services.board_parse import BoardRefusal
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


def install_pipeline(app: FastAPI, llm) -> ProcessingPipeline:
    """Build the memory pipeline on ``llm`` and wire everything that reads it.

    Called by the boot and, after a boot whose LLM setup failed, by the first
    configuration save that installs an orchestrator, so captures queued in
    the meantime drain on the next ``buffer_flush`` tick.
    """
    from app.api.websocket import event_manager
    from app.database import async_session_factory
    from app.services.pipeline import memory_retry_handler
    from app.services.pipeline_failures import register_retry_handler

    pipeline = ProcessingPipeline(llm, async_session_factory, broadcast=event_manager.broadcast)
    app.state.pipeline = pipeline
    app.state.pipeline_boot_error = None
    set_pipeline(pipeline)

    register_retry_handler("memory_ingest")(
        memory_retry_handler(pipeline, async_session_factory)
    )

    @register_retry_handler("code_index")
    async def _retry_code_index(repo_id):
        from app.repositories.vector import PostgresVectorRepository
        from app.services.code_pipeline import CodePipeline
        from app.services.llm import lease_llm
        from app.services.repo_manager import RepoManager

        async with async_session_factory() as s:
            code_vector_repo = PostgresVectorRepository(s, "code_chunks")
            active_llm = getattr(app.state, "llm", None)
            with lease_llm(active_llm):
                code_pipeline = CodePipeline(
                    session=s, llm=active_llm,
                    vector_repo=code_vector_repo,
                    repo_manager=RepoManager(s),
                )
                await code_pipeline.run(repo_id)
                await s.commit()

    return pipeline


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

    app.state.session_factory = async_session_factory
    app.state.pipeline = None
    app.state.pipeline_boot_error = None

    if settings.read_only:
        # Increment 7's worker posture. The reconciliations below all degrade
        # under a caught exception, so the SELECT-only role would make them
        # inert anyway -- but depending on a swallowed exception for
        # correctness is the shape review B1 condemns, and a restored snapshot
        # already carries every partition these would create.
        logger.info(
            "DARKMEM_READ_ONLY: boot reconciliations, project backfill and "
            "embedder registration skipped; job registry will not be armed. "
            "Enforcement is the database role, not this flag."
        )
    else:
        # Outside the LLM setup below: a provider table that cannot be read
        # must not also leave the journal without next month's partition.
        from app.services.embedder_registry import embedder_registry

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

    try:
        from app.services.config import get_llm_config
        from app.services.usage_recorder import UsageRecorder
        from app.services.embedder_registry import (
            embedder_registry, ensure_registered,
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

        if not settings.read_only:
            llm_fp = llm.llm_fingerprint()
            llm_model_id, _, llm_dims_text = llm_fp.rpartition("|")
            if llm_dims_text == "0":
                # Dimensions unset: there is no width to register until the
                # first real embed names one (llm_fingerprint's docstring), so
                # this is the expected path, not a failure.
                logger.info(
                    "Embedding dimensions unset; %s registers on its first embed",
                    llm_model_id,
                )
            else:
                try:
                    async with async_session_factory() as session:
                        await ensure_registered(session, llm_fp)
                except Exception:
                    logger.exception("Failed to register LLM embedder %s at boot", llm_fp)

        app.state.llm = llm
        pipeline = install_pipeline(app, llm)
        logger.info("Pipeline initialized: pgvector + LLM connected")
    except Exception as exc:
        # Captures still queue; /health answers `pipeline_state:
        # failed_at_boot` until a configuration save installs an orchestrator
        # and builds the pipeline (`install_pipeline`).
        logger.exception("Pipeline not available: LLM setup failed at boot")
        app.state.pipeline = None
        app.state.pipeline_boot_error = f"{type(exc).__name__}: {exc}"[:500]

    if pipeline is None:
        set_pipeline(None)

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

    # The socket revalidation cache; a socket's handshake retries the load
    # when this one could not read the database.
    from app.api.websocket import session_revocations
    try:
        await session_revocations.load(async_session_factory)
    except Exception:
        logger.exception("Could not load the session revocation cache at boot")

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
            "Fetches and re-indexes each repository on its own schedule, when "
            "that repository's switches are on."
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
            "Turns accepted captures into memories. With it off, new captures "
            "are never processed."
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
            "Keeps job run history to its configured size, dropping the "
            "oldest runs."
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
            "Deletes LLM usage records older than the retention window."
        ),
        # Nightly, after the backup timer's 03:30 so a sweep never races a dump.
        default_cron="0 4 * * *",
        min_interval_seconds=3600,
        runner=make_llm_usage_cleanup_runner(app, async_session_factory),
        config_schema=LLM_USAGE_CONFIG_SCHEMA,
    ))

    from app.services.mcp_call_log import (
        MCP_CALL_CLEANUP_JOB_KEY,
        MCP_CALL_CONFIG_SCHEMA,
        make_mcp_call_cleanup_runner,
    )

    job_registry.register(Job(
        key=MCP_CALL_CLEANUP_JOB_KEY,
        display_name="MCP Call Log Retention",
        description=(
            "Deletes MCP call records older than the retention window. Also "
            "holds the switch that decides whether search queries are logged."
        ),
        default_cron="15 4 * * *",
        min_interval_seconds=3600,
        runner=make_mcp_call_cleanup_runner(app, async_session_factory),
        config_schema=MCP_CALL_CONFIG_SCHEMA,
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
            "Deletes page attachments nothing references any more, after a "
            "grace period."
        ),
        default_cron="20 * * * *",
        min_interval_seconds=600,
        runner=make_page_attachment_cleanup_runner(app, async_session_factory),
        config_schema=PAGE_ATTACHMENT_CLEANUP_CONFIG_SCHEMA,
    ))

    from app.services.worklog_cleanup import (
        WORKLOG_CLEANUP_CONFIG_SCHEMA,
        WORKLOG_CLEANUP_CRON,
        WORKLOG_CLEANUP_JOB_KEY,
        make_worklog_cleanup_runner,
    )
    job_registry.register(Job(
        key=WORKLOG_CLEANUP_JOB_KEY,
        display_name="Work Log Retention",
        description=(
            "Deletes closed workstreams once they pass the retention window. "
            "Open and retained workstreams are kept."
        ),
        default_cron=WORKLOG_CLEANUP_CRON,
        min_interval_seconds=3600,
        runner=make_worklog_cleanup_runner(app, async_session_factory),
        config_schema=WORKLOG_CLEANUP_CONFIG_SCHEMA,
    ))

    job_registry.register(Job(
        key=BACKUP_SHIP_JOB_KEY,
        display_name="Backup Ship",
        description=(
            "Backs up the database, encrypts it and ships it to each enabled "
            "backup destination."
        ),
        # 04:30 UTC, apart from the systemd timer's 03:30 host-local, because
        # nothing can serialise the two producers (m4) and dumping twice
        # concurrently doubles I/O on the same Postgres for no benefit. The
        # gap depends on the host's timezone: about 8 hours at UTC+7.
        default_cron="30 4 * * *",
        min_interval_seconds=3600,
        runner=make_backup_ship_runner(app, async_session_factory),
        max_run_seconds=BACKUP_SHIP_MAX_RUN_SECONDS,
    ))

    job_registry.register(Job(
        key="code_enrichment",
        display_name="Code Symbol Enrichment",
        description=(
            "Writes short summaries for code symbols that don't have one yet."
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
            "Adds each indexed repository, its dependencies and its languages "
            "to the knowledge graph."
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
            "Deletes expired entries from the sign-out token blocklist."
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
            "Prunes old resolved pipeline failures and prepares the activity "
            "journal for the coming months. Leave it on."
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
            "Removes graph entities and relations that no memory mentions any "
            "more."
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
            "Removes tags that no memory carries any more."
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
            "Deletes memories past their expiry time."
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
            "Rebuilds the graph snapshot used by graph-based ranking, a few "
            "projects per run."
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
            "Embeds graph relations for relation-level search."
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
            "Embeds document blocks, note blocks and work-log entries that "
            "are missing an embedding."
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
            "Embeds entities found in repositories so they can be matched to "
            "the same things in memories."
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
            "Merges a repository's entity with the matching entity a memory "
            "already created."
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
            "Re-checks code citations against each repository's latest commit "
            "and flags the ones that no longer resolve."
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
        from app.services.repo_manager import RepoManager

        async with async_session_factory() as _s:
            released = await RepoManager.release_interrupted_runs(_s)
        if released:
            logger.warning("Released %d repository claim(s) left by a previous process", released)
        await job_registry.start_all()

    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp_server.session_manager.run())
        yield

    await job_registry.stop_all()

    from app.services.wait_process import drain_continuing_flushes
    await drain_continuing_flushes()

    # Write whatever MCP calls are still buffered; a log miss is tolerable,
    # but a clean shutdown has no reason to cause one.
    from app.services.mcp_call_log import drain as drain_mcp_call_log
    try:
        await drain_mcp_call_log()
    except Exception:
        logger.warning("Failed to drain the MCP call log at shutdown", exc_info=True)

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


def is_page_import_path(path: str) -> bool:
    """`POST /api/v1/pages/import/notion` streams a whole Notion export and
    bounds it against `notion_import_max_bytes`, which is three orders of
    magnitude above the edge cap."""
    return path == "/api/v1/pages/import/notion"


def bounds_own_body(path: str) -> bool:
    """Whether this route enforces its own body ceiling.

    One predicate above both spellings rather than one predicate meaning two
    things: each name states a fact its own tests assert, and the middleware
    asks a single question.
    """
    return is_attachment_upload_path(path) or is_page_import_path(path)


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
        if scope["type"] == "http" and not is_mcp_path(path) and not bounds_own_body(path):
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


app = FastAPI(title="darkmem", version="1.17.0", description="Centralized memory system for AI agents", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
    code = getattr(exc, "error_code", None) or _HTTP_ERROR_CODES.get(
        exc.status_code, f"http_{exc.status_code}",
    )
    return _error_response(exc.status_code, code, message, details, getattr(exc, "headers", None))


@app.exception_handler(BoardRefusal)
async def _board_refusal_handler(_request, exc: BoardRefusal):
    """The board's refusals carry their reason as `error.code`.

    Its own handler because a dict `detail` on the generic HTTPException path
    is flattened to "Request failed"; the reason and its fields are what let
    the SPA tell a hash conflict from a missing Note.
    """
    return _error_response(
        exc.status_code, exc.reason, exc.message, [exc.fields] if exc.fields else None,
    )


@app.exception_handler(GitAccountInUse)
async def _git_account_in_use_handler(_request, exc: GitAccountInUse):
    """409 that names the repos still using the account.

    Its own handler because the generic HTTPException path keeps `details` only
    for a list and would otherwise drop both the list and the message.
    """
    return _error_response(409, "conflict", exc.message, exc.repos)


def _finite_for_json(value):
    # JSONResponse renders with allow_nan=False, so a 422 echoing a NaN or an
    # infinity in some error's `input` would itself fail and answer 500.
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: _finite_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_finite_for_json(item) for item in value]
    return value


@app.exception_handler(RequestValidationError)
async def _validation_exception_handler(_request, exc: RequestValidationError):
    errors = _finite_for_json(jsonable_encoder(exc.errors()))
    first = errors[0] if errors else {}
    location = ".".join(str(part) for part in first.get("loc", ())[1:])
    message = first.get("msg", "Request validation failed")
    if location:
        message = f"{location}: {message}"
    return _error_response(422, "validation_error", message, errors)


@app.exception_handler(DBAPIError)
async def _database_refusal(_request, exc: DBAPIError):
    """SQLSTATE 42501 -> 403 `read_only`, 22021 -> 422 `invalid_text`,
    everything else untouched.

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

    22021 is text Postgres cannot store (a NUL byte), which no request bound
    catches: it surfaces only when the server decodes the parameter.
    """
    sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None)
    if sqlstate == "42501":
        return _error_response(
            403,
            "read_only",
            "This instance is read-only; writes are refused at the database.",
        )
    if sqlstate == "22021":
        return _error_response(
            422,
            "invalid_text",
            "The request carries text the database cannot store, such as a NUL byte.",
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
app.include_router(chat.router)
app.include_router(repos.router)
app.include_router(git_account_routes.router)
app.include_router(code.router)
app.include_router(pipeline_failures.router)
app.include_router(review_queue.router)
app.include_router(worklog_routes.router)
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
app.include_router(board_routes.router)
# Before `pages_routes`: FastAPI matches in registration order, so a later
# two-segment `POST /pages/{page_id}/x` would shadow `/pages/import/notion`.
app.include_router(page_import_routes.router)
app.include_router(pages_routes.router)
app.include_router(page_attachments_routes.router)
app.include_router(reembed.router)
app.include_router(usage_routes.router)
app.include_router(mcp_calls_routes.router)
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
    from app.services import ml_runtime

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

    async def check_classifier_unavailable() -> bool:
        """A stored `local` classifier this install cannot load."""
        if ml_runtime.ml_extra_available():
            return False
        try:
            async with async_session_factory() as session:
                kind = (await session.execute(text(
                    "SELECT classifier_kind FROM llm_purpose_configs "
                    "WHERE purpose = 'classification'"
                ))).scalar_one_or_none()
        except Exception:
            return False
        return kind == "local"

    async def check_initialised() -> bool:
        try:
            async with async_session_factory() as session:
                return (await session.execute(text(
                    "SELECT 1 FROM config WHERE key = 'admin_password_hash'"
                ))).scalar_one_or_none() is not None
        except Exception:
            return False

    classifier_unavailable = await check_classifier_unavailable()

    if settings.read_only:
        pipeline_state = "read_only"
    elif not await check_initialised():
        pipeline_state = "not_configured"
    elif pipeline is None:
        pipeline_state = "failed_at_boot"
    else:
        pipeline_state = "ok"

    if settings.read_only:
        pgvector_ok, llm_ok = await check_pgvector(), False
    else:
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
            "classifier_unavailable": classifier_unavailable,
            "pipeline_state": pipeline_state,
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

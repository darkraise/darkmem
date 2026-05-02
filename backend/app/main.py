import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from sqlalchemy import select, text

from app.api.mcp.server import mcp as mcp_server, set_pipeline
from app.api.routes import analytics, auth, chat, code, config, graph, memories, pipeline as pipeline_routes, pipeline_failures, reembed, repos, tags, vectors
from app.api.websocket import websocket_endpoint
from app.config import settings
from app.services.llm import LLMOrchestrator
from app.services.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import async_session_factory

    pipeline = None
    llm = None

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
        from app.services.embedder_registry import (
            EmbedderInfo, embedder_registry, parse_fingerprint,
        )
        async with async_session_factory() as session:
            llm_config = await get_llm_config(session)
        llm = LLMOrchestrator(llm_config)

        # Hydrate the in-process registry cache from existing rows so that
        # already-known fingerprints don't trigger redundant DDL.
        async with async_session_factory() as session:
            await embedder_registry.warm_cache_from_db(session)

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
    except Exception as e:
        logger.exception("Pipeline not available (Postgres-only mode)")
        app.state.pipeline = None
        app.state.session_factory = async_session_factory

    set_pipeline(pipeline)

    # Single shared lock for LLM config / provider / profile writes. Routes
    # used to lazy-create on first touch, which raced under concurrent
    # save clicks (each request saw None, each created its own Lock, the
    # second store overwrote the first — neither serialized).
    app.state.llm_config_lock = asyncio.Lock()

    from app.services import prompt
    agent_instructions = prompt.get("agent_instructions")
    if agent_instructions:
        mcp_server._mcp_server.instructions = agent_instructions

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

    async def periodic_repo_sync():
        while True:
            try:
                await asyncio.sleep(300)
                from app.models.code import Repository
                active_llm = getattr(app.state, "llm", None)
                async with async_session_factory() as list_session:
                    repos_result = (await list_session.execute(
                        select(Repository).where(Repository.is_active == True)
                    )).scalars().all()
                    repos_to_sync = list(repos_result)
                for repo in repos_to_sync:
                    if repo.last_indexed_at:
                        from datetime import datetime, timezone, timedelta
                        next_sync = repo.last_indexed_at + timedelta(minutes=repo.sync_interval_minutes)
                        if datetime.now(timezone.utc) < next_sync:
                            continue
                    async with async_session_factory() as repo_session:
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
                            logger.error(f"Periodic sync failed for {repo.name}: {e}")
            except Exception as e:
                logger.error(f"Periodic sync loop error: {e}")

    async def periodic_blocklist_cleanup():
        while True:
            try:
                await asyncio.sleep(3600)
                from datetime import datetime, timezone
                from sqlalchemy import delete
                from app.models.token_blocklist import TokenBlocklist
                async with async_session_factory() as cleanup_session:
                    await cleanup_session.execute(
                        delete(TokenBlocklist).where(TokenBlocklist.expires_at < datetime.now(timezone.utc))
                    )
                    await cleanup_session.commit()
            except Exception as e:
                logger.error(f"Blocklist cleanup error: {e}")

    async def periodic_pipeline_failure_cleanup():
        while True:
            try:
                await asyncio.sleep(3600)
                from app.services.pipeline_failures import PipelineFailureService
                async with async_session_factory() as cleanup_session:
                    svc = PipelineFailureService(cleanup_session)
                    orphaned = await svc.prune_orphans()
                    resolved_pruned = await svc.prune_resolved_older_than(days=30)
                    await cleanup_session.commit()
                logger.info(
                    "Pipeline failure cleanup: orphaned=%s, resolved_pruned=%d",
                    orphaned, resolved_pruned,
                )
            except Exception as e:
                logger.error(f"Pipeline failure cleanup error: {e}")

    sync_task = asyncio.create_task(periodic_repo_sync())
    cleanup_task = asyncio.create_task(periodic_blocklist_cleanup())
    failure_cleanup_task = asyncio.create_task(periodic_pipeline_failure_cleanup())

    enrichment_worker = None
    enrichment_task = None
    if llm:
        from app.services.enrichment_worker import EnrichmentWorker
        from app.models.config import Config as ConfigModel

        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(ConfigModel).where(ConfigModel.key == "enrichment_config")
                )
                config = result.scalar_one_or_none()
                enrichment_config = config.value if config else {"enabled": False}

            enrichment_worker = EnrichmentWorker(llm, broadcast=event_manager.broadcast)

            if enrichment_config.get("enabled", False):
                enrichment_worker.batch_size = enrichment_config.get("batch_size", 5)
                enrichment_worker.interval = enrichment_config.get("interval_seconds", 10)
                enrichment_task = asyncio.create_task(enrichment_worker.run_loop())
                logger.info("Enrichment worker started")

            app.state.enrichment_worker = enrichment_worker
            app.state.enrichment_task = enrichment_task
        except Exception as e:
            logger.warning(f"Failed to start enrichment worker: {e}")

    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp_server.session_manager.run())
        yield

    sync_task.cancel()
    cleanup_task.cancel()
    failure_cleanup_task.cancel()

    if enrichment_worker:
        enrichment_worker.stop()
    if enrichment_task:
        enrichment_task.cancel()

    from app.services.task_registry import TaskRegistry
    TaskRegistry.cancel_all()

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


app = FastAPI(title="darkmem", version="0.2.0", description="Centralized memory system for AI agents", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(memories.router)
app.include_router(tags.router)
app.include_router(graph.router)
app.include_router(analytics.router)
app.include_router(config.router)
app.include_router(pipeline_routes.router)
app.include_router(vectors.router)
app.include_router(chat.router)
app.include_router(repos.router)
app.include_router(code.router)
app.include_router(pipeline_failures.router)
app.include_router(reembed.router)


app.add_api_websocket_route("/ws", websocket_endpoint)

_mcp_app = mcp_server.streamable_http_app()


app.mount("/mcp", _mcp_app)


@app.get("/health")
async def health():
    import httpx
    from starlette.responses import JSONResponse
    from app.database import async_session_factory

    pipeline = getattr(app.state, "pipeline", None)
    llm = getattr(app.state, "llm", None)

    async def check_pgvector():
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                )
                return result.scalar_one_or_none() is not None
        except Exception:
            return False

    async def check_llm():
        try:
            base_url = llm.config.get("embedding", {}).base_url if llm else None
            if not base_url:
                return False
            ollama_base = base_url.rstrip("/v1").rstrip("/")
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{ollama_base}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    pgvector_ok, llm_ok = await asyncio.gather(check_pgvector(), check_llm())

    overall = "ok" if all([pgvector_ok, llm_ok]) else "degraded"
    status_code = 200 if overall == "ok" else 503
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

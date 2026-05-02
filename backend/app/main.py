import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from sqlalchemy import select, text

from app.api.mcp.server import mcp as mcp_server, set_pipeline
from app.api.routes import analytics, auth, chat, code, config, graph, jobs, memories, pipeline as pipeline_routes, pipeline_failures, reembed, repos, setup, system, tags, vectors
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

    # The repo_sync_wakeup event is owned by the JobRegistry below and
    # exposed on app.state so route handlers (PUT /repos/{id}) can poke
    # it without depending on the registry import.
    app.state.repo_sync_wakeup = None  # set after registry init

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

    # ── Job registry: replaces the previous four bare asyncio loops ──
    from app.services.job_registry import Job, JobRegistry
    from app.services.job_runners import (
        make_repo_sync_runner,
        make_code_enrichment_runner,
        make_token_blocklist_cleanup_runner,
        make_pipeline_failure_cleanup_runner,
    )

    job_registry = JobRegistry(async_session_factory)
    job_registry.register(Job(
        key="repo_sync",
        display_name="Repository Sync",
        description=(
            "Fetches every repo with auto-sync enabled and runs the code "
            "indexing pipeline. The per-repo Reindex button bypasses this "
            "loop and runs immediately."
        ),
        default_interval_seconds=300,
        min_interval_seconds=30,
        runner=make_repo_sync_runner(app, async_session_factory),
    ))
    job_registry.register(Job(
        key="code_enrichment",
        display_name="Code Symbol Enrichment",
        description=(
            "Runs one batch of LLM summarisation against pending code "
            "symbols (function / class / method docs). Batch size comes "
            "from the legacy enrichment_config row."
        ),
        default_interval_seconds=10,
        min_interval_seconds=1,
        runner=make_code_enrichment_runner(app, async_session_factory),
    ))
    job_registry.register(Job(
        key="token_blocklist_cleanup",
        display_name="Token Blocklist Cleanup",
        description=(
            "Deletes expired entries from the auth token blocklist. Safe "
            "to leave on; disable only if you are debugging revocation."
        ),
        default_interval_seconds=3600,
        min_interval_seconds=60,
        runner=make_token_blocklist_cleanup_runner(async_session_factory),
    ))
    job_registry.register(Job(
        key="pipeline_failure_cleanup",
        display_name="Pipeline Failure Cleanup",
        description=(
            "Prunes orphaned pipeline-failure rows and resolved entries "
            "older than 30 days. Safe to leave on."
        ),
        default_interval_seconds=3600,
        min_interval_seconds=60,
        runner=make_pipeline_failure_cleanup_runner(async_session_factory),
    ))

    # Expose the repo_sync wakeup so PUT /repos/{id} can nudge the loop
    # immediately when a repo's auto_sync flips. The registry owns the
    # event; route handlers just call .set() on it.
    repo_sync_job = job_registry.get("repo_sync")
    if repo_sync_job is not None:
        app.state.repo_sync_wakeup = repo_sync_job.wakeup

    app.state.job_registry = job_registry
    await job_registry.start_all()

    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp_server.session_manager.run())
        yield

    await job_registry.stop_all()

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
app.include_router(setup.router)
app.include_router(system.router)
app.include_router(jobs.router)


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

        Branches on the provider's ``api_kind`` instead of assuming Ollama —
        the previous implementation hard-coded ``/api/tags`` and stripped
        ``/v1`` with ``rstrip`` (which removes a character set, not a suffix),
        so it returned False for every cloud provider and surfaced as a
        permanent 503 even when the configured LLM was perfectly reachable.
        """
        try:
            embedding_cfg = llm.config.get("embedding") if llm else None
            if embedding_cfg is None or not embedding_cfg.base_url:
                return False
            api_kind = getattr(embedding_cfg, "api_kind", "openai")
            base = embedding_cfg.base_url.rstrip("/")
            api_key = getattr(embedding_cfg, "api_key", None)

            if api_kind == "ollama":
                root = base.removesuffix("/v1").removesuffix("/api")
                url = f"{root}/api/tags"
                headers: dict[str, str] = {}
            else:
                url = f"{base}/models"
                headers = {}
                if api_kind == "anthropic" and api_key:
                    headers["x-api-key"] = api_key
                    headers["anthropic-version"] = "2023-06-01"
                elif api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url, headers=headers)
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

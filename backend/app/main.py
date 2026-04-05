import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import AsyncGraphDatabase
from qdrant_client import AsyncQdrantClient
from starlette.routing import Mount

from sqlalchemy import select

from app.api.mcp.server import mcp as mcp_server, set_pipeline
from app.api.routes import analytics, auth, chat, code, config, graph, memories, repos, tags, vectors
from app.api.websocket import websocket_endpoint
from app.config import settings
from app.repositories.graph import Neo4jGraphRepository
from app.repositories.vector import QdrantVectorRepository
from app.services.llm import LLMOrchestrator
from app.services.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.jwt_secret == "darkmem-jwt-secret-change-me":
        logger.warning("Using default JWT secret — set JWT_SECRET env var for production")

    # Initialize optional services
    pipeline = None
    qdrant_client = None
    neo4j_driver = None
    llm = None

    try:
        qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)
        await qdrant_client.get_collections()

        neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password),
        )
        await neo4j_driver.verify_connectivity()

        # Read LLM config from DB (falls back to env vars)
        from app.services.config import get_llm_config
        from app.database import async_session_factory
        async with async_session_factory() as session:
            llm_config = await get_llm_config(session)
        llm = LLMOrchestrator(llm_config)

        # Auto-detect embedding dimensions
        embedding_dims = llm_config["embedding"].dimensions or 768
        try:
            test_vec = await llm.embed("dimension probe")
            embedding_dims = len(test_vec)
            logger.info(f"Detected embedding dimensions: {embedding_dims}")
        except Exception as e:
            logger.warning(f"Could not auto-detect embedding dimensions: {e}")
        vector_repo = QdrantVectorRepository(qdrant_client, dimensions=embedding_dims)
        await vector_repo.ensure_collection()
        code_vector_repo = QdrantVectorRepository(qdrant_client, dimensions=embedding_dims, collection_name="code_chunks")
        await code_vector_repo.ensure_collection()
        graph_repo = Neo4jGraphRepository(neo4j_driver)

        pipeline = ProcessingPipeline(llm, vector_repo, graph_repo)
        app.state.pipeline = pipeline
        app.state.graph_repo = graph_repo
        app.state.vector_repo = vector_repo
        app.state.llm = llm
        logger.info("Pipeline initialized: Qdrant + Neo4j + LLM connected")
    except Exception as e:
        logger.warning(f"Pipeline not available (Postgres-only mode): {e}")
        app.state.pipeline = None
        app.state.graph_repo = None
        app.state.vector_repo = None

    # Set pipeline reference for MCP tools
    set_pipeline(pipeline)

    # Seed system prompt profiles and load MCP instructions
    from app.db.seed import seed_profiles
    from app.services.prompt import PromptService
    try:
        async with async_session_factory() as session:
            await seed_profiles(session)
            agent_instructions = await PromptService.get("agent_instructions", session)
            if agent_instructions:
                mcp_server._mcp_server.instructions = agent_instructions
        logger.info("Seed data applied")
    except Exception as e:
        logger.warning(f"Failed to seed data: {e}")

    async def periodic_repo_sync():
        while True:
            try:
                await asyncio.sleep(300)
                async with async_session_factory() as sync_session:
                    from app.services.code_indexer import CodeIndexer
                    from app.models.code import Repository
                    repos_result = (await sync_session.execute(
                        select(Repository).where(Repository.is_active == True)
                    )).scalars().all()
                    for repo in repos_result:
                        if repo.last_indexed_at:
                            from datetime import datetime, timezone, timedelta
                            next_sync = repo.last_indexed_at + timedelta(minutes=repo.sync_interval_minutes)
                            if datetime.now(timezone.utc) < next_sync:
                                continue
                        indexer = CodeIndexer(sync_session, llm, vector_repo, graph_repo)
                        try:
                            await indexer.index_repo(repo.id)
                            await sync_session.commit()
                        except Exception as e:
                            await sync_session.rollback()
                            logger.error(f"Periodic sync failed for {repo.name}: {e}")
            except Exception as e:
                logger.error(f"Periodic sync loop error: {e}")

    sync_task = asyncio.create_task(periodic_repo_sync())

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

            enrichment_session = async_session_factory()
            enrichment_worker = EnrichmentWorker(enrichment_session, llm)

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

    if enrichment_worker:
        enrichment_worker.stop()
    if enrichment_task:
        enrichment_task.cancel()

    # Cleanup
    if llm:
        await llm.close()
    if neo4j_driver:
        await neo4j_driver.close()
    if qdrant_client:
        await qdrant_client.close()


app = FastAPI(title="darkmem", version="0.2.0", description="Centralized memory system for AI agents", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
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
app.include_router(vectors.router)
app.include_router(chat.router)
app.include_router(repos.router)
app.include_router(code.router)


app.add_api_websocket_route("/ws", websocket_endpoint)

app.mount("/mcp", mcp_server.streamable_http_app())


@app.get("/health")
async def health():
    import asyncio

    pipeline = getattr(app.state, "pipeline", None)
    vector_repo = getattr(app.state, "vector_repo", None)
    graph_repo = getattr(app.state, "graph_repo", None)
    llm = getattr(app.state, "llm", None)

    async def check_qdrant():
        if not vector_repo:
            return False
        try:
            await vector_repo.client.get_collections()
            return True
        except Exception:
            return False

    async def check_neo4j():
        if not graph_repo:
            return False
        try:
            await graph_repo.driver.verify_connectivity()
            return True
        except Exception:
            return False

    async def check_llm():
        try:
            return llm is not None and llm._client is not None
        except Exception:
            return False

    qdrant_ok, neo4j_ok, llm_ok = await asyncio.gather(
        check_qdrant(), check_neo4j(), check_llm()
    )

    return {
        "status": "ok",
        "pipeline": pipeline is not None and qdrant_ok and neo4j_ok and llm_ok,
        "services": {
            "qdrant": qdrant_ok,
            "neo4j": neo4j_ok,
            "llm": llm_ok,
        },
    }

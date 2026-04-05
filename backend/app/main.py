import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import AsyncGraphDatabase
from qdrant_client import AsyncQdrantClient
from starlette.routing import Mount

from app.api.mcp.server import mcp as mcp_server, set_pipeline
from app.api.routes import analytics, auth, chat, config, graph, memories, repos, tags, vectors
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

    # Seed system prompt profiles
    from app.db.seed import seed_profiles
    try:
        async with async_session_factory() as session:
            await seed_profiles(session)
        logger.info("Seed data applied")
    except Exception as e:
        logger.warning(f"Failed to seed data: {e}")

    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp_server.session_manager.run())
        yield

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

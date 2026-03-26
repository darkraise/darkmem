import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from neo4j import AsyncGraphDatabase
from qdrant_client import AsyncQdrantClient

from app.api.routes import analytics, config, graph, keys, memories, tags
from app.api.websocket import websocket_endpoint
from app.config import settings
from app.repositories.graph import Neo4jGraphRepository
from app.repositories.vector import QdrantVectorRepository
from app.services.llm import LLMOrchestrator
from app.services.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
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

        llm_config = {
            "embedding": settings.llm_embedding,
            "extraction": settings.llm_extraction,
            "reasoning": settings.llm_reasoning,
            "summarization": settings.llm_summarization,
        }
        llm = LLMOrchestrator(llm_config)

        vector_repo = QdrantVectorRepository(qdrant_client, dimensions=settings.llm_embedding.dimensions or 768)
        await vector_repo.ensure_collection()
        graph_repo = Neo4jGraphRepository(neo4j_driver)

        pipeline = ProcessingPipeline(llm, vector_repo, graph_repo)
        app.state.pipeline = pipeline
        app.state.graph_repo = graph_repo
        app.state.vector_repo = vector_repo
        logger.info("Pipeline initialized: Qdrant + Neo4j + LLM connected")
    except Exception as e:
        logger.warning(f"Pipeline not available (Postgres-only mode): {e}")
        app.state.pipeline = None
        app.state.graph_repo = None
        app.state.vector_repo = None

    # Seed system prompt profiles
    from app.db.seed import seed_profiles
    from app.database import async_session_factory
    try:
        async with async_session_factory() as session:
            await seed_profiles(session)
        logger.info("System prompt profiles seeded")
    except Exception as e:
        logger.warning(f"Failed to seed profiles: {e}")

    yield

    # Cleanup
    if llm:
        await llm.close()
    if neo4j_driver:
        await neo4j_driver.close()
    if qdrant_client:
        await qdrant_client.close()


app = FastAPI(title="darkmem", version="0.2.0", description="Centralized memory system for AI agents", lifespan=lifespan)

app.include_router(memories.router)
app.include_router(tags.router)
app.include_router(keys.router)
app.include_router(graph.router)
app.include_router(analytics.router)
app.include_router(config.router)


app.add_api_websocket_route("/ws", websocket_endpoint)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "pipeline": hasattr(app.state, "pipeline") and app.state.pipeline is not None,
    }

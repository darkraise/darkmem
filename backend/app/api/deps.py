from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.repositories.graph import PostgresGraphRepository
from app.repositories.relational import PostgresTagRepository
from app.repositories.vector import PostgresVectorRepository
from app.services.analytics import AnalyticsService
from app.services.chat import ChatService
from app.services.code_pipeline import CodePipeline
from app.services.graph import GraphService
from app.services.memory import MemoryService
from app.services.repo_manager import RepoManager


async def get_memory_service(request: Request, session: AsyncSession = Depends(get_session)) -> MemoryService:
    pipeline = getattr(request.app.state, "pipeline", None)
    return MemoryService(session, pipeline=pipeline)


async def get_chat_service(request: Request, session: AsyncSession = Depends(get_session)) -> ChatService:
    llm = getattr(request.app.state, "llm", None)
    if not llm:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="LLM service unavailable")
    vector_repo = PostgresVectorRepository(session)
    graph_repo = PostgresGraphRepository(session)
    return ChatService(session, llm, vector_repo, graph_repo)


async def get_analytics_service(request: Request, session: AsyncSession = Depends(get_session)) -> AnalyticsService:
    pipeline = getattr(request.app.state, "pipeline", None)
    graph_repo = PostgresGraphRepository(session)
    return AnalyticsService(session, pipeline, graph_repo)


async def get_graph_service(request: Request, session: AsyncSession = Depends(get_session)) -> GraphService:
    llm = getattr(request.app.state, "llm", None)
    vector_repo = PostgresVectorRepository(session)
    graph_repo = PostgresGraphRepository(session)
    return GraphService(session, vector_repo, graph_repo, llm)


async def get_code_pipeline(request: Request, session: AsyncSession = Depends(get_session)) -> CodePipeline:
    llm = getattr(request.app.state, "llm", None)
    vector_repo = PostgresVectorRepository(session, "code_chunks")
    repo_manager = RepoManager(session)
    return CodePipeline(session=session, llm=llm, vector_repo=vector_repo, repo_manager=repo_manager)


async def get_repo_manager(session: AsyncSession = Depends(get_session)) -> RepoManager:
    return RepoManager(session)


async def get_tag_repository(session: AsyncSession = Depends(get_session)) -> PostgresTagRepository:
    return PostgresTagRepository(session)

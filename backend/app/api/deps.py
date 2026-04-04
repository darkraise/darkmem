from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.repositories.relational import PostgresTagRepository
from app.services.chat import ChatService
from app.services.graph import GraphService
from app.services.memory import MemoryService


async def get_memory_service(request: Request, session: AsyncSession = Depends(get_session)) -> MemoryService:
    pipeline = getattr(request.app.state, "pipeline", None)
    return MemoryService(session, pipeline=pipeline)


async def get_chat_service(request: Request, session: AsyncSession = Depends(get_session)) -> ChatService:
    llm = getattr(request.app.state, "llm", None)
    vector_repo = getattr(request.app.state, "vector_repo", None)
    graph_repo = getattr(request.app.state, "graph_repo", None)
    if not llm:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="LLM service unavailable")
    return ChatService(session, llm, vector_repo, graph_repo)


async def get_graph_service(request: Request, session: AsyncSession = Depends(get_session)) -> GraphService:
    vector_repo = getattr(request.app.state, "vector_repo", None)
    graph_repo = getattr(request.app.state, "graph_repo", None)
    llm = getattr(request.app.state, "llm", None)
    return GraphService(session, vector_repo, graph_repo, llm)


async def get_tag_repository(session: AsyncSession = Depends(get_session)) -> PostgresTagRepository:
    return PostgresTagRepository(session)

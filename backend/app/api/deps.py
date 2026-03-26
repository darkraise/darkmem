from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.repositories.relational import PostgresApiKeyRepository, PostgresTagRepository
from app.services.memory import MemoryService


async def get_memory_service(request: Request, session: AsyncSession = Depends(get_session)) -> MemoryService:
    pipeline = getattr(request.app.state, "pipeline", None)
    return MemoryService(session, pipeline=pipeline)


async def get_tag_repository(session: AsyncSession = Depends(get_session)) -> PostgresTagRepository:
    return PostgresTagRepository(session)


async def get_api_key_repository(session: AsyncSession = Depends(get_session)) -> PostgresApiKeyRepository:
    return PostgresApiKeyRepository(session)

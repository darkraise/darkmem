import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import SystemPromptProfile

logger = logging.getLogger(__name__)


class PromptService:
    _cache: dict[str, str] = {}
    _loaded: bool = False

    @classmethod
    async def get(cls, purpose: str, session: AsyncSession) -> str:
        if not cls._loaded:
            await cls._load_all(session)
        return cls._cache.get(purpose, "")

    @classmethod
    async def _load_all(cls, session: AsyncSession) -> None:
        result = await session.execute(select(SystemPromptProfile))
        for profile in result.scalars().all():
            cls._cache[profile.purpose] = profile.content
        cls._loaded = True
        logger.info(f"Loaded {len(cls._cache)} system prompts")

    @classmethod
    def invalidate(cls) -> None:
        cls._loaded = False
        cls._cache.clear()

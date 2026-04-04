from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import LLMPurposeConfig, settings
from app.models.config import Config
from app.schemas.config import LLMPurposeConfigSchema

LLM_CONFIG_KEY = "llm_config"
PURPOSES = ["embedding", "extraction", "reasoning", "summarization"]


def cfg_to_schema(cfg: LLMPurposeConfig, mask_key: bool = True) -> LLMPurposeConfigSchema:
    return LLMPurposeConfigSchema(
        provider=cfg.provider, base_url=cfg.base_url, model=cfg.model,
        api_key="***" if (mask_key and cfg.api_key) else cfg.api_key,
        dimensions=cfg.dimensions, params=cfg.params,
    )


async def get_llm_config(session: AsyncSession) -> dict[str, LLMPurposeConfig]:
    """Read LLM config from DB, fall back to env/settings defaults."""
    result = await session.execute(select(Config).where(Config.key == LLM_CONFIG_KEY))
    db_config = result.scalar_one_or_none()

    defaults = {
        "embedding": settings.llm_embedding,
        "extraction": settings.llm_extraction,
        "reasoning": settings.llm_reasoning,
        "summarization": settings.llm_summarization,
    }

    if not db_config:
        return defaults

    merged = {}
    for purpose in PURPOSES:
        if purpose in db_config.value:
            merged[purpose] = LLMPurposeConfig(**db_config.value[purpose])
        else:
            merged[purpose] = defaults[purpose]
    return merged

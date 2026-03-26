from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_scope
from app.config import settings
from app.database import get_session
from app.models.config import SystemPromptProfile
from app.schemas.config import LLMConfigResponse, LLMPurposeConfigSchema
from app.schemas.prompt import SystemPromptResponse

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config(_api_key=Depends(require_scope("admin"))):
    def _to_schema(cfg):
        return LLMPurposeConfigSchema(
            provider=cfg.provider, base_url=cfg.base_url, model=cfg.model,
            api_key="***" if cfg.api_key else None,
            dimensions=cfg.dimensions, params=cfg.params,
        )
    return LLMConfigResponse(
        embedding=_to_schema(settings.llm_embedding),
        extraction=_to_schema(settings.llm_extraction),
        reasoning=_to_schema(settings.llm_reasoning),
        summarization=_to_schema(settings.llm_summarization),
    )


@router.get("/system-prompt", response_model=SystemPromptResponse)
async def get_system_prompt(
    profile: str = "default",
    _api_key=Depends(require_scope("read")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(SystemPromptProfile).where(SystemPromptProfile.name == profile)
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Profile '{profile}' not found")
    return SystemPromptResponse.model_validate(prompt)


@router.get("/system-prompt/list", response_model=list[SystemPromptResponse])
async def list_system_prompts(
    _api_key=Depends(require_scope("read")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(SystemPromptProfile).order_by(SystemPromptProfile.name))
    return [SystemPromptResponse.model_validate(p) for p in result.scalars().all()]

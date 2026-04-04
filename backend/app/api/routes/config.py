from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.config import LLMPurposeConfig, settings
from app.database import get_session
from app.models.config import Config, SystemPromptProfile
from app.schemas.config import LLMConfigResponse, LLMConfigUpdate, LLMPurposeConfigSchema
from app.schemas.prompt import SystemPromptResponse
from app.services.config import LLM_CONFIG_KEY, PURPOSES, cfg_to_schema
from app.services.config import get_llm_config as fetch_llm_config

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    config = await fetch_llm_config(session)
    return LLMConfigResponse(**{p: cfg_to_schema(c) for p, c in config.items()})


@router.post("/llm", response_model=LLMConfigResponse)
async def update_llm_config(
    body: LLMConfigUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    # Read existing DB config
    result = await session.execute(select(Config).where(Config.key == LLM_CONFIG_KEY))
    db_entry = result.scalar_one_or_none()

    # Build new config from existing + updates
    current = await fetch_llm_config(session)
    update_data = body.model_dump(exclude_unset=True)

    new_value = {}
    for purpose in PURPOSES:
        if purpose in update_data and update_data[purpose] is not None:
            # Merge: keep existing fields, override with provided ones
            existing = current[purpose].model_dump()
            incoming = {k: v for k, v in update_data[purpose].items() if v is not None}
            # If api_key is "***", keep the existing one
            if incoming.get("api_key") == "***":
                incoming.pop("api_key")
            existing.update(incoming)
            new_value[purpose] = existing
        else:
            new_value[purpose] = current[purpose].model_dump()

    if db_entry:
        db_entry.value = new_value
    else:
        session.add(Config(key=LLM_CONFIG_KEY, value=new_value))

    await session.flush()

    # Return updated config (masked)
    updated = {p: LLMPurposeConfig(**v) for p, v in new_value.items()}
    return LLMConfigResponse(**{p: cfg_to_schema(c) for p, c in updated.items()})


@router.get("/system-prompt", response_model=SystemPromptResponse)
async def get_system_prompt(
    profile: str = "default",
    _user=Depends(require_auth),
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
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(SystemPromptProfile).order_by(SystemPromptProfile.name))
    return [SystemPromptResponse.model_validate(p) for p in result.scalars().all()]

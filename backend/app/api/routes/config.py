from fastapi import APIRouter, Depends

from app.api.auth import require_scope
from app.config import settings
from app.schemas.config import LLMConfigResponse, LLMPurposeConfigSchema

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

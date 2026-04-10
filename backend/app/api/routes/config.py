from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.config import FEATURE_FLAGS_DEFAULTS, LLMPurposeConfig, settings
from app.database import get_session
from app.models.config import Config
from app.schemas.config import LLMConfigResponse, LLMConfigUpdate, LLMPurposeConfigSchema
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
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services.llm import LLMOrchestrator

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

    # Swap the live LLM orchestrator so new requests pick up the updated config.
    # In-flight requests keep their existing reference to the old orchestrator (safe).
    updated_config = {p: LLMPurposeConfig(**v) for p, v in new_value.items()}
    new_llm = LLMOrchestrator(updated_config)
    request.app.state.llm = new_llm

    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is not None:
        pipeline.llm = new_llm
        pipeline.extraction.llm = new_llm

    return LLMConfigResponse(**{p: cfg_to_schema(c) for p, c in updated_config.items()})


class FeatureFlagsResponse(BaseModel):
    llm_enrichment_enabled: bool
    hybrid_search_enabled: bool
    reranker_enabled: bool
    pipeline_concurrency: int
    classification_areas: list[str]
    classification_mode: str


class FeatureFlagsUpdate(BaseModel):
    llm_enrichment_enabled: bool | None = None
    hybrid_search_enabled: bool | None = None
    reranker_enabled: bool | None = None
    pipeline_concurrency: int | None = None
    classification_areas: list[str] | None = None
    classification_mode: str | None = None


FEATURE_FLAGS_KEY = "feature_flags"


async def get_feature_flags_dict(session: AsyncSession) -> dict:
    result = await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))
    config = result.scalar_one_or_none()
    if not config:
        return dict(FEATURE_FLAGS_DEFAULTS)
    merged = dict(FEATURE_FLAGS_DEFAULTS)
    merged.update(config.value)
    return merged


@router.get("/feature-flags", response_model=FeatureFlagsResponse)
async def get_feature_flags(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    flags = await get_feature_flags_dict(session)
    return FeatureFlagsResponse(**flags)


@router.put("/feature-flags", response_model=FeatureFlagsResponse)
async def update_feature_flags(
    body: FeatureFlagsUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    current = await get_feature_flags_dict(session)
    updates = body.model_dump(exclude_unset=True)

    if "classification_areas" in updates:
        from app.services.classification_areas import AREAS
        invalid = [a for a in updates["classification_areas"] if a not in AREAS]
        if invalid:
            raise HTTPException(status_code=422, detail=f"Unknown classification areas: {invalid}")

    if "classification_mode" in updates:
        if updates["classification_mode"] not in ("simple", "expanded"):
            raise HTTPException(status_code=422, detail="classification_mode must be 'simple' or 'expanded'")

    current.update(updates)

    result = await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))
    config = result.scalar_one_or_none()
    if config:
        config.value = current
    else:
        session.add(Config(key=FEATURE_FLAGS_KEY, value=current))
    await session.flush()

    return FeatureFlagsResponse(**current)


@router.get("/classification-areas")
async def list_classification_areas(
    _user=Depends(require_auth),
):
    from app.services.classification_areas import AREAS, get_merged_llm_types
    return [
        {
            "key": area.key,
            "display_name": area.display_name,
            "types": list(area.llm_types.keys()),
            "type_descriptions": area.llm_types,
        }
        for area in AREAS.values()
    ]


class EnrichmentConfigUpdate(BaseModel):
    enabled: bool = False
    batch_size: int = 5
    interval_seconds: int = 10


@router.get("/enrichment")
async def get_enrichment_config(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Config).where(Config.key == "enrichment_config"))
    config = result.scalar_one_or_none()
    if not config:
        return {"enabled": False, "batch_size": 5, "interval_seconds": 10}
    return config.value


@router.put("/enrichment")
async def update_enrichment_config(
    body: EnrichmentConfigUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    request: Request = None,
):
    result = await session.execute(select(Config).where(Config.key == "enrichment_config"))
    config = result.scalar_one_or_none()
    new_value = body.model_dump()
    if config:
        config.value = new_value
    else:
        session.add(Config(key="enrichment_config", value=new_value))
    await session.flush()

    worker = getattr(request.app.state, "enrichment_worker", None) if request else None
    if worker:
        worker.batch_size = body.batch_size
        worker.interval = body.interval_seconds
        if body.enabled and not worker._running:
            import asyncio

            old_task = getattr(request.app.state, "enrichment_task", None)
            if old_task and not old_task.done():
                worker.stop()
                old_task.cancel()
                worker._running = False

            task = asyncio.create_task(worker.run_loop())
            request.app.state.enrichment_task = task
        elif not body.enabled and worker._running:
            worker.stop()

    return new_value


@router.post("/enrichment/trigger")
async def trigger_enrichment(
    _user=Depends(require_auth),
    request: Request = None,
):
    from app.services.enrichment_worker import EnrichmentWorker

    llm = getattr(request.app.state, "llm", None) if request else None
    if not llm:
        raise HTTPException(status_code=503, detail="LLM not available")

    worker = EnrichmentWorker(llm)
    count = await worker.process_batch(batch_size=10)

    return {"processed": count}

"""/api/v1/pipeline — aggregator + mode preset + unload + metrics."""
from __future__ import annotations

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.config import FEATURE_FLAGS_DEFAULTS
from app.database import async_session_factory, get_session
from app.models.config import Config
from app.services import ml_models as mm
from app.services import pipeline_aggregator, system_metrics
from app.services.feature_flags import FEATURE_FLAGS_KEY, get_feature_flags_dict
from app.services.pipeline import _refresh_flag_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


@router.get("")
async def get_pipeline(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    state = await pipeline_aggregator.build_pipeline_state(session)
    if mm.models_available():
        state["ml"]["effective_device"] = mm.get_ml_models().device
    return state


class ModeRequest(BaseModel):
    mode: Literal["ml", "llm"]


@router.post("/mode")
async def set_mode(
    body: ModeRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    current = await get_feature_flags_dict(session)
    flag_value = body.mode == "ml"
    current["ml_extraction"] = flag_value
    current["ml_classification"] = flag_value
    current["ml_retrieval"] = flag_value

    stored = {k: current[k] for k in FEATURE_FLAGS_DEFAULTS if k in current}

    row = (
        await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))
    ).scalar_one_or_none()
    if row:
        row.value = stored
    else:
        session.add(Config(key=FEATURE_FLAGS_KEY, value=stored))
    await session.flush()

    await _refresh_flag_cache(async_session_factory)

    return {
        "mode": body.mode,
        "stages": {
            "extraction": body.mode,
            "classification": body.mode,
            "retrieval": body.mode,
        },
    }


@router.post("/unload")
async def unload_pipeline(
    group: Literal["extraction", "classification", "retriever"] | None = Query(None),
    _user=Depends(require_auth),
):
    targets = [group] if group else list(mm.GROUPS)
    unloaded: list[str] = []
    if mm._INSTANCE is not None:
        for name in targets:
            if getattr(mm._INSTANCE, f"{name}_loaded", False):
                await asyncio.to_thread(mm.unload_group, name)
                unloaded.append(name)

    return {"unloaded": unloaded, "groups": mm.group_status()}


@router.get("/metrics")
async def get_metrics(_user=Depends(require_auth)):
    snap = system_metrics.snapshot()
    snap["groups"] = mm.group_status()
    return snap

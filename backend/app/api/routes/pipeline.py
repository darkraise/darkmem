"""/api/v1/pipeline — aggregator + mode preset + unload + metrics."""
from __future__ import annotations

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.config import FEATURE_FLAGS_DEFAULTS
from app.database import get_session
from app.models.config import Config
from app.services import pipeline_aggregator, system_metrics
from app.services.feature_flags import FEATURE_FLAGS_KEY, get_feature_flags_dict
from app.services.ml_models import group_status, models_available

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


@router.get("")
async def get_pipeline(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    state = await pipeline_aggregator.build_pipeline_state(session)
    if models_available():
        try:
            from app.services.ml_models import get_ml_models
            state["ml"]["effective_device"] = get_ml_models().device
        except Exception:
            pass
    return state

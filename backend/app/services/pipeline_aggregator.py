"""Compose /api/v1/pipeline's response payload from existing services.

This module is a read-only composer. It does not mutate state; every write
still goes through the individual /api/v1/config/* endpoints.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ml_pipeline_settings
from app.services.config import get_llm_config as fetch_llm_config
from app.services.config import cfg_to_schema
from app.services.feature_flags import get_feature_flags_dict
from app.services import prompt as _prompt_mod

# Which prompt keys are stage-bound (shown on the Pipeline LLM panel).
# Orphans (chat, cluster_naming, agent_instructions) still come back in
# the `prompts` dict — the frontend decides which ones to render where via
# its own prompt-map.ts, but the aggregator returns them all so Settings's
# Assistant-Prompts tab can also read from this endpoint if it wants.
_STAGE_PROMPT_KEYS = [
    "extraction",
    "extraction_entities",
    "extraction_relationships",
    "classification",
    "reasoning",
    "summarization",
]


async def build_pipeline_state(session: AsyncSession) -> dict:
    flags = await get_feature_flags_dict(session)
    llm = await fetch_llm_config(session)

    await _prompt_mod.refresh_from_db(session)
    defaults = dict(_prompt_mod.PROMPTS)
    overrides = _prompt_mod.get_overrides()
    prompts = {
        k: {
            "default": defaults.get(k, ""),
            "override": overrides.get(k, ""),
            "effective": overrides.get(k, defaults.get(k, "")),
        }
        for k in _STAGE_PROMPT_KEYS
        if k in defaults
    }

    stages = {
        "extraction": "ml" if flags.get("ml_extraction") else "llm",
        "classification": "ml" if flags.get("ml_classification") else "llm",
        "retrieval": "ml" if flags.get("ml_retrieval") else "llm",
    }
    all_ml = all(v == "ml" for v in stages.values())
    all_llm = all(v == "llm" for v in stages.values())
    mode = "ml" if all_ml else ("llm" if all_llm else "mixed")

    idle_ttl = int(flags.get("ml_idle_ttl_minutes") or 0)
    persistence = "persistent" if idle_ttl == 0 else "ttl"

    from app.services.ml_models import list_available_devices  # noqa: PLC0415

    return {
        "mode": mode,
        "stages": stages,
        "shadow_mode": bool(flags.get("ml_shadow_mode", False)),
        "ml": {
            "device": str(flags.get("ml_device", "auto")),
            "effective_device": None,  # filled by caller if loaded
            "cuda_index": int(flags.get("ml_cuda_index") or 0),
            "persistence": persistence,
            "idle_ttl_minutes": idle_ttl,
            "eviction_check_interval_seconds": int(
                flags.get("ml_eviction_check_interval_seconds") or 60
            ),
            "cpu_fallback": bool(getattr(ml_pipeline_settings, "cpu_fallback", True)),
            "available_devices": list_available_devices(),
        },
        "llm": {k: cfg_to_schema(v).model_dump() for k, v in llm.items()},
        "prompts": prompts,
    }

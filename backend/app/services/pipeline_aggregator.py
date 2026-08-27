"""Compose /api/v1/pipeline's response payload from existing services.

This module is a read-only composer. It does not mutate state; every write
still goes through the individual /api/v1/config/* endpoints.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.config import get_llm_config as fetch_llm_config
from app.services.config import cfg_to_schema
from app.services.feature_flags import get_feature_flags_dict
from app.services import prompt as _prompt_mod

_STAGE_PROMPT_KEYS = [
    "extraction",
    "classification",
    "reasoning",
    "summarization",
]

# Prompt keys that are NOT LLM purposes, so no purpose card owns them. The
# frontend counterpart is the map in
# frontend/src/features/settings/llm-purpose-prompts.ts (this comment named a
# `prompt-map.ts` and an `ORPHAN_PROMPTS` symbol, neither of which exists);
# the pin test in test_pipeline_aggregator.py guards the invariant.
ORPHAN_PROMPT_KEYS = frozenset({"chat", "cluster_naming", "agent_instructions"})


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

    return {
        "relation_rescue": bool(flags.get("relation_rescue", True)),
        "llm": {k: cfg_to_schema(v).model_dump() for k, v in llm.items()},
        "prompts": prompts,
    }

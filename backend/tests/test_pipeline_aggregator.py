import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pipeline_aggregator import build_pipeline_state
from app.services.config import PURPOSES


@pytest.mark.asyncio
async def test_aggregator_returns_llm_state(session: AsyncSession):
    state = await build_pipeline_state(session)
    assert set(state["llm"].keys()) == set(PURPOSES)
    assert "extraction" in state["prompts"]
    assert state["relation_rescue"] is True


@pytest.mark.asyncio
async def test_aggregator_reflects_relation_rescue_flag(session):
    from app.models.config import Config
    session.add(Config(key="feature_flags", value={"relation_rescue": False}))
    await session.flush()
    state = await build_pipeline_state(session)
    assert state["relation_rescue"] is False


def test_stage_prompt_keys_exhaust_prompts_module():
    """Every PROMPTS key is either stage-bound or orphan; nothing slips through."""
    from app.services import prompt as _prompt_mod
    from app.services.pipeline_aggregator import _STAGE_PROMPT_KEYS, ORPHAN_PROMPT_KEYS

    defaults = set(_prompt_mod.PROMPTS.keys())
    stage = set(_STAGE_PROMPT_KEYS)

    assert stage.issubset(defaults), f"aggregator references unknown prompts: {stage - defaults}"
    uncovered = defaults - stage - ORPHAN_PROMPT_KEYS
    assert not uncovered, f"PROMPTS has keys not in stage list or orphans: {uncovered}"

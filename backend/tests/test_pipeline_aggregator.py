import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pipeline_aggregator import build_pipeline_state


@pytest.mark.asyncio
async def test_aggregator_empty_db_yields_llm_mode(session: AsyncSession):
    state = await build_pipeline_state(session)
    assert state["mode"] == "llm"
    assert state["stages"] == {
        "extraction": "llm",
        "classification": "llm",
        "retrieval": "llm",
    }
    assert state["shadow_mode"] is False
    assert state["ml"]["persistence"] == "ttl"  # default TTL is 30 min
    assert state["ml"]["idle_ttl_minutes"] == 30
    assert "available_devices" in state["ml"]
    assert set(state["llm"].keys()) == {
        "embedding", "extraction", "classification",
        "reasoning", "summarization", "reranker",
    }
    assert "extraction" in state["prompts"]
    assert "groups" not in state["ml"]  # groups live in /metrics, not aggregator


@pytest.mark.asyncio
async def test_aggregator_mode_derives_ml(session):
    from app.models.config import Config
    session.add(Config(key="feature_flags", value={
        "ml_extraction": True, "ml_classification": True, "ml_retrieval": True,
    }))
    await session.flush()
    state = await build_pipeline_state(session)
    assert state["mode"] == "ml"
    assert state["stages"]["extraction"] == "ml"


@pytest.mark.asyncio
async def test_aggregator_mode_derives_mixed(session):
    from app.models.config import Config
    session.add(Config(key="feature_flags", value={
        "ml_extraction": True, "ml_classification": False, "ml_retrieval": True,
    }))
    await session.flush()
    state = await build_pipeline_state(session)
    assert state["mode"] == "mixed"


@pytest.mark.asyncio
async def test_aggregator_persistence_persistent(session):
    from app.models.config import Config
    session.add(Config(key="feature_flags", value={"ml_idle_ttl_minutes": 0}))
    await session.flush()
    state = await build_pipeline_state(session)
    assert state["ml"]["persistence"] == "persistent"


def test_stage_prompt_keys_exhaust_prompts_module():
    """Every key in _STAGE_PROMPT_KEYS must exist in services.prompt.PROMPTS,
    and every non-orphan PROMPTS key must be in _STAGE_PROMPT_KEYS.

    The orphan allowlist mirrors ORPHAN_PROMPTS in the frontend prompt-map.ts.
    When either side changes, this test is the first thing that fails.
    """
    from app.services import prompt as _prompt_mod
    from app.services.pipeline_aggregator import _STAGE_PROMPT_KEYS

    ORPHANS = {"chat", "cluster_naming", "agent_instructions"}
    defaults = set(_prompt_mod.PROMPTS.keys())
    stage = set(_STAGE_PROMPT_KEYS)

    assert stage.issubset(defaults), f"aggregator references unknown prompts: {stage - defaults}"
    uncovered = defaults - stage - ORPHANS
    assert not uncovered, f"PROMPTS has keys not in stage list or orphans: {uncovered}"

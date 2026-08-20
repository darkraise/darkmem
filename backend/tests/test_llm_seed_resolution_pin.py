"""Two hashes ride on the resolved config, so its values are pinned.

`benchlib/caching_llm.py` keys every cached LLM call on the resolved
`model/base_url/api_kind/dimensions/reasoning/params`, and
`verification_judge.IDENTITY_FIELDS` is the same six. A seed edit that
perturbs a resolved value silently invalidates every bench cache entry and
un-qualifies the judge, and neither failure announces itself.
"""
from __future__ import annotations

import os

import pytest

from app.models.llm_config import LLMPurposeConfigRow
from app.models.llm_provider import LLMProviderRow
from app.services.config import get_llm_config
from app.services.llm_seed import (
    DEFAULT_PROVIDER_ROWS,
    DEFAULT_PURPOSE_CONFIGS,
    default_provider_row_name_for_purpose,
)

# What every purpose resolved to before the provider layer existed: the inline
# values carried by DEFAULT_PURPOSE_CONFIGS itself.
EXPECTED = {
    pc.purpose: {
        "model": pc.model,
        "api_kind": pc.api_kind,
        "base_url": pc.base_url,
        "dimensions": pc.dimensions,
        "params": dict(pc.params),
    }
    for pc in DEFAULT_PURPOSE_CONFIGS
}


async def _seed(session):
    for ps in DEFAULT_PROVIDER_ROWS:
        session.add(LLMProviderRow(
            name=ps.name, api_kind=ps.api_kind, base_url=ps.base_url, api_key=ps.api_key,
        ))
    await session.flush()
    for pc in DEFAULT_PURPOSE_CONFIGS:
        session.add(LLMPurposeConfigRow(
            purpose=pc.purpose,
            provider_name=default_provider_row_name_for_purpose(pc.purpose),
            model=pc.model,
            dimensions=pc.dimensions,
            params=dict(pc.params),
        ))
    await session.flush()


@pytest.mark.asyncio
async def test_fresh_install_resolves_to_the_pre_provider_values(session):
    await _seed(session)
    config = await get_llm_config(session)
    for purpose, expected in EXPECTED.items():
        cfg = config[purpose]
        assert cfg.model == expected["model"], purpose
        assert cfg.api_kind == expected["api_kind"], purpose
        assert cfg.base_url == expected["base_url"], purpose
        assert cfg.dimensions == expected["dimensions"], purpose
        assert cfg.params == expected["params"], purpose


# The one seeded value with a legitimate way to move: `scripts/gate.sh` points
# the Ollama purposes at the LAN embedder for its API e2e step.
_OLLAMA_ENV = "DARKMEM_OLLAMA_BASE_URL"


@pytest.mark.asyncio
async def test_extraction_resolves_to_its_literal_seeded_values(session):
    """One purpose pinned to literals instead of back to the seed it came from.

    The loop above derives model, dimensions and params from the same
    `DEFAULT_PURPOSE_CONFIGS` entries `_seed` writes, so for those three fields
    both sides of the assertion move together and it cannot fail. Written out
    by hand here, a seed edit that shifts a resolved value fails in this file
    rather than surfacing as a silent benchlib cache miss on every machine and
    a gate re-run that quietly pays for live calls.
    """
    await _seed(session)
    cfg = (await get_llm_config(session))["extraction"]

    assert cfg.model == "qwen2.5:3b"
    assert cfg.api_kind == "openai"
    assert cfg.dimensions is None
    assert cfg.reasoning is False
    assert cfg.params == {"temperature": 0}
    assert cfg.base_url == os.getenv(_OLLAMA_ENV, "http://localhost:11434/v1")


@pytest.mark.asyncio
async def test_judge_identity_survives_the_split(session):
    """The qualified identity is computed off the resolved config. Split across
    a provider row and a purpose row, it must hash to the same value."""
    from app.services.verification_judge import judge_identity, judge_identity_hash

    session.add(LLMProviderRow(
        name="openai-judge", api_kind="openai",
        base_url="https://api.openai.com/v1", api_key="sk-x",
    ))
    await session.flush()
    session.add(LLMPurposeConfigRow(
        purpose="verification", provider_name="openai-judge",
        model="gpt-5.5", params={"reasoning_effort": "high"},
    ))
    await session.flush()

    cfg = (await get_llm_config(session))["verification"]
    assert judge_identity_hash(judge_identity(cfg)) == "fd39e7b2c47fa375"

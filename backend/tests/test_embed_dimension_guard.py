"""embed must fail loud when the real vector length contradicts configured dims.

llm_fingerprint() trusts the stored ``dimensions`` to name the partition, but
embeds emit ``model|len(vec)``. If the stored value is wrong (a typo, or
changing the model without the dims), reads route to a partition writes never
populated and counts/search silently break. Raise at embed time so the
misconfiguration surfaces instead of mislabeling partitions.
"""
from __future__ import annotations

import httpx
import pytest

from app.config import LLMPurposeConfig
from app.services.llm import LLMOrchestrator


def _make_llm(dims_returned: int, configured_dims: int | None) -> LLMOrchestrator:
    def handler(request: httpx.Request) -> httpx.Response:
        emb = [0.1] * dims_returned
        return httpx.Response(200, json={"data": [{"embedding": emb, "index": 0}]})

    config = {
        "embedding": LLMPurposeConfig(base_url="http://mock", model="m", dimensions=configured_dims),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return llm


async def test_embed_raises_on_dimension_mismatch():
    llm = _make_llm(dims_returned=3, configured_dims=4)
    with pytest.raises(RuntimeError, match="dimension"):
        await llm.embed("hi")


async def test_embed_ok_when_dimensions_match():
    llm = _make_llm(dims_returned=4, configured_dims=4)
    vec, fp = await llm.embed("hi")
    assert len(vec) == 4
    assert fp == "m|4"


async def test_embed_ok_when_dimensions_unset():
    llm = _make_llm(dims_returned=3, configured_dims=None)
    _vec, fp = await llm.embed("hi")
    assert fp == "m|3"


async def test_embed_batch_raises_on_dimension_mismatch():
    llm = _make_llm(dims_returned=3, configured_dims=4)
    with pytest.raises(RuntimeError, match="dimension"):
        await llm.embed_batch(["a", "b"])

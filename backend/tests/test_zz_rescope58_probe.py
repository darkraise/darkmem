"""T2.58 fix-round-1 re-review probes (scratch — deleted after the run).

Probe A: door parity on a corpus deeper than FUSION_FETCH_DEPTH itself,
i.e. the shape nobody has tried: does the F1 divergence relocate past 300?

Probe B: the real composition outage record versus ``outage_channels`` —
the shipped pin test is circular (it builds the exception from the fallback
and compares the two), so this drives the real raise path on both scopes.
"""
from __future__ import annotations

import importlib.util
import math
import pathlib

import pytest

_spec = importlib.util.spec_from_file_location(
    "rescope58_parity_helpers",
    pathlib.Path(__file__).with_name("test_chat_retrieval_parity.py"),
)
parity = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parity)

pytestmark = pytest.mark.asyncio

DEEP_FILLERS = 305


async def test_probe_parity_holds_past_the_fusion_depth(session):
    await parity._seed_partition(session)
    for i in range(DEEP_FILLERS):
        angle = 0.004 * (i + 1)
        await parity._add_memory(
            session,
            vector=[math.cos(angle), math.sin(angle), 0.0, 0.0],
            content=f"the box runs a database proxy on the LAN, note {i}",
        )
    target = await parity._add_memory(
        session,
        vector=[math.cos(1.4), math.sin(1.4), 0.0, 0.0],
        content="pgbouncer connection pooling was chosen over pgcat",
    )

    chat = await parity._chat_ids(session)
    surface = await parity._search_surface_ids(
        session, limit=parity.CHAT_RETRIEVAL_LIMIT * 2,
    )

    # The target sits at semantic rank 306 — beyond both doors' shared
    # 300-deep arm window — so if the F1 divergence merely relocated to
    # bigger corpora, these two lists would part here.
    assert chat == surface[: len(chat)], (
        f"divergence past depth 300: chat={chat[:5]} surface={surface[:5]}"
    )
    # Record where the keyword-strong row lands (recall bound, shared).
    print("target served by chat:", str(target.id) in chat)
    print("target served by surface(20):", str(target.id) in surface)


async def test_probe_real_outage_record_equals_the_fallback(session, monkeypatch):
    from app.services import facts_channel
    from app.services.hybrid_search import HybridSearchService
    from app.services.layer_composition import (
        CompositionUnavailable,
        LayerCompositionService,
        outage_channels,
    )

    async def _down(self, *args, **kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr(HybridSearchService, "_semantic_search", _down)
    monkeypatch.setattr(HybridSearchService, "_keyword_search", _down)
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _down)

    svc = LayerCompositionService(parity._FakeLLM(), session)

    with pytest.raises(CompositionUnavailable) as scoped:
        await svc.search("q", project=parity.PROJECT, limit=5, statuses=("active",))
    assert scoped.value.channels == outage_channels(fact_asked=True), (
        "the scoped raise's record differs from the fallback record"
    )

    with pytest.raises(CompositionUnavailable) as wide:
        await svc.search("q", project=None, limit=5, statuses=("active",))
    assert wide.value.channels == outage_channels(fact_asked=False), (
        "the wide raise's record differs from the fallback record"
    )

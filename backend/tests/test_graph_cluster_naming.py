"""Cluster naming must dispatch on the purpose that matches the task.

Dispatching a free-text naming task on ``extraction`` borrows params tuned
for JSON extraction and bills the tokens to extraction in ``llm_usage`` -
the table that answers "what did the last N days cost".
"""
from __future__ import annotations

import pytest

from app.services.graph import GraphService


@pytest.mark.asyncio
async def test_cluster_naming_dispatches_on_summarization():
    seen: list[str] = []

    class _Spy:
        async def chat_completion(self, purpose, **kwargs):
            seen.append(purpose)
            return "cluster name"

    service = GraphService(session=None, llm=_Spy())
    await service._generate_cluster_names(
        {1: ["some memory content"]},
        [{"cluster": 1, "content": "some memory content"}],
    )
    assert seen == ["summarization"]

"""Cluster naming must dispatch on the purpose that matches the task.

Dispatching a free-text naming task on ``extraction`` borrows params tuned
for JSON extraction and bills the tokens to extraction in ``llm_usage`` -
the table that answers "what did the last N days cost".
"""
from __future__ import annotations

import pytest

import app.services.graph as graph_module
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


class _CountingLLM:
    def __init__(self, fail: bool = False):
        self.calls = 0
        self.fail = fail

    async def chat_completion(self, purpose, **kwargs):
        self.calls += 1
        if self.fail:
            raise RuntimeError("down")
        return f'"name {self.calls}"'


def _nodes(sizes: dict[int, int], tags: dict[int, list[str]] | None = None) -> tuple[dict, list[dict]]:
    clusters: dict[int, list[str]] = {}
    nodes: list[dict] = []
    for cid, size in sizes.items():
        for i in range(size):
            mid = f"{cid}-{i}"
            clusters.setdefault(cid, []).append(mid)
            nodes.append({
                "id": mid,
                "cluster": cid,
                "content": f"memory {mid}",
                "tags": (tags or {}).get(cid, []),
            })
    return clusters, nodes


@pytest.mark.asyncio
async def test_only_the_largest_clusters_cost_a_call(monkeypatch):
    monkeypatch.setattr(graph_module, "CLUSTER_NAME_LLM_CAP", 2)
    llm = _CountingLLM()
    clusters, nodes = _nodes({0: 3, 1: 5, 2: 1}, tags={2: ["project/darkmem", "retrieval"]})

    names, degraded = await GraphService(session=None, llm=llm)._generate_cluster_names(clusters, nodes)

    assert llm.calls == 2
    assert names["2"] == "retrieval"
    assert names["0"].startswith("name ") and names["1"].startswith("name ")
    assert degraded is False


@pytest.mark.asyncio
async def test_a_name_is_reused_while_its_sample_is_unchanged():
    llm = _CountingLLM()
    clusters, nodes = _nodes({0: 3})
    svc = GraphService(session=None, llm=llm)

    first, _ = await svc._generate_cluster_names(clusters, nodes)
    second, _ = await svc._generate_cluster_names(clusters, nodes)

    assert llm.calls == 1
    assert second == first


@pytest.mark.asyncio
async def test_tag_names_skip_project_tags_and_break_ties_alphabetically():
    clusters, nodes = _nodes(
        {0: 2, 1: 2},
        tags={0: ["project/x", "zeta", "alpha"], 1: ["project/x"]},
    )

    names, degraded = await GraphService(session=None, llm=None)._generate_cluster_names(clusters, nodes)

    assert names == {"0": "alpha", "1": "Cluster 1"}
    assert degraded is False


@pytest.mark.asyncio
async def test_a_failed_call_falls_back_and_is_not_cached():
    llm = _CountingLLM(fail=True)
    clusters, nodes = _nodes({0: 3}, tags={0: ["retrieval"]})
    svc = GraphService(session=None, llm=llm)

    names, degraded = await svc._generate_cluster_names(clusters, nodes)
    await svc._generate_cluster_names(clusters, nodes)

    assert names == {"0": "Cluster 0"}
    assert degraded is True
    assert llm.calls == 2

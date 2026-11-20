"""The two artefact jobs that serve only the graph rank arms run only for an armed arm.

`ppr_snapshot` feeds the PPR list and `relation_embedding_refresh` feeds the
dual-level list. With an arm's flag off nothing reads the artefact, so building
it hourly is CPU, embed calls and a growing partition spent on no reader.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app.services import feature_flags, job_runners, ppr_snapshot, relation_embeddings
from app.services.llm import LLMOrchestrator

pytestmark = pytest.mark.asyncio


@asynccontextmanager
async def _factory():
    yield SimpleNamespace(commit=_noop)


async def _noop(*args, **kwargs):
    return None


def _app(llm=None):
    async def load_config(_key):
        return SimpleNamespace(config={})

    return SimpleNamespace(state=SimpleNamespace(
        llm=llm, job_registry=SimpleNamespace(load_config=load_config),
    ))


def _flags(monkeypatch, **flags):
    async def _read(_session):
        return {"ppr_enabled": False, "dual_level_enabled": False, **flags}

    monkeypatch.setattr(feature_flags, "get_feature_flags_dict", _read)


@pytest.mark.parametrize("armed", [False, True])
async def test_ppr_snapshot_builds_only_while_the_ppr_arm_is_armed(monkeypatch, armed):
    calls = []

    async def _refresh(session_factory, **knobs):
        calls.append(knobs)
        return SimpleNamespace(projects_visited=0, last_project=None, snapshots_built=0, skipped=0)

    _flags(monkeypatch, ppr_enabled=armed)
    monkeypatch.setattr(ppr_snapshot, "refresh_snapshots", _refresh)
    monkeypatch.setattr(job_runners, "_load_ppr_cursor", _noop)
    monkeypatch.setattr(job_runners, "_save_ppr_cursor", _noop)

    await job_runners.make_ppr_snapshot_runner(_app(), _factory)()

    assert len(calls) == (1 if armed else 0)


@pytest.mark.parametrize("armed", [False, True])
async def test_relation_embeddings_refresh_only_while_the_dual_level_arm_is_armed(monkeypatch, armed):
    calls = []

    async def _refresh(session, llm, **knobs):
        calls.append(knobs)
        return SimpleNamespace(total=0)

    _flags(monkeypatch, dual_level_enabled=armed)
    monkeypatch.setattr(relation_embeddings, "refresh_relation_embeddings", _refresh)
    llm = LLMOrchestrator({})
    try:
        await job_runners.make_relation_embedding_runner(_app(llm), _factory)()
    finally:
        await llm.close()

    assert len(calls) == (1 if armed else 0)

"""A flush tick in which every claimed capture failed is a failed run.

The embedder was unreachable for seventeen days in 2026-11 and every capture
failed at content embedding. The job recorded ``ok`` throughout, so neither
the Jobs page nor the failure notification had anything to show.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import buffer_flush, job_runners

pytestmark = pytest.mark.asyncio

_IDLE = {"claimed": 0, "done": 0, "failed": 0, "rejected": 0, "reclaimed": 0, "swept": 0, "timed_out": 0}


def _runner(monkeypatch, **stats):
    async def _flush(session_factory, pipeline):
        return {**_IDLE, **stats}

    monkeypatch.setattr(buffer_flush, "flush_once", _flush)
    app = SimpleNamespace(state=SimpleNamespace(pipeline=object()))
    return job_runners.make_buffer_flush_runner(app, None)


async def test_a_tick_whose_every_capture_failed_is_an_error(monkeypatch):
    with pytest.raises(job_runners.BufferFlushFailed, match="all 3 claimed captures failed"):
        await _runner(monkeypatch, claimed=3, failed=3)()


async def test_a_tick_with_any_success_reports_its_counts(monkeypatch):
    stats = await _runner(monkeypatch, claimed=3, done=1, failed=2)()

    assert (stats["done"], stats["failed"]) == (1, 2)


async def test_an_empty_queue_reports_nothing(monkeypatch):
    assert await _runner(monkeypatch)() == {}

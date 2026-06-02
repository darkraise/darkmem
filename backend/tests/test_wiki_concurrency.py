"""Wiki module summaries must be computed concurrently, not one at a time.

generate() awaited the per-module summarization LLM call inline in the module
loop, so wall-clock time was the sum of all module latencies. Bound-concurrent
gather cuts that to roughly the slowest module.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest

from app.models.code import CodeFile, Repository
from app.services.wiki_generator import WikiGenerator


class _ConcurrencyTrackingLLM:
    def __init__(self):
        self.cur = 0
        self.max = 0

    async def chat_completion(self, purpose, messages, **kwargs):
        self.cur += 1
        self.max = max(self.max, self.cur)
        await asyncio.sleep(0.05)
        self.cur -= 1
        return "summary"


@pytest.mark.asyncio
async def test_wiki_module_summaries_run_concurrently(session):
    repo = Repository(name="r")
    session.add(repo)
    await session.flush()
    for d in ("a", "b", "c"):
        session.add(CodeFile(
            id=uuid.uuid4(), repo_id=repo.id, file_path=f"{d}/f.py",
            language="python", content_hash="h",
        ))
    await session.flush()

    llm = _ConcurrencyTrackingLLM()
    await WikiGenerator(session, llm=llm).generate(repo.id)

    # Three modules → their summary calls overlap rather than running serially.
    assert llm.max >= 2

"""LLM orchestrator that memoises embed + chat_completion to disk.

Keyed by a content hash so a second bench run replays every model call from
disk (self.live_calls stays 0). The parent calls are indirected through
_live_embed / _live_chat so tests can stub the model without a live backend.
"""
import hashlib
import json
import os

from benchlib import bench_db  # noqa: F401  (ensures DATABASE_URL override first)
from app.services.llm import LLMOrchestrator


def _key(kind: str, payload) -> str:
    blob = json.dumps([kind, payload], sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


class CachingLLMOrchestrator(LLMOrchestrator):
    def __init__(self, config, cache_dir: str):
        super().__init__(config)
        self._cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.live_calls = 0

    def _read(self, key: str):
        path = os.path.join(self._cache_dir, key + ".json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        return None

    def _write(self, key: str, value) -> None:
        path = os.path.join(self._cache_dir, key + ".json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(value, fh, ensure_ascii=False)

    async def _live_embed(self, text):
        return await super().embed(text)

    async def _live_chat(self, purpose, messages, **kwargs):
        return await super().chat_completion(purpose, messages, **kwargs)

    async def embed(self, text: str):
        key = _key("embed", text)
        hit = self._read(key)
        if hit is not None:
            return hit[0], hit[1]
        self.live_calls += 1
        vec, fp = await self._live_embed(text)
        self._write(key, [vec, fp])
        return vec, fp

    async def chat_completion(self, purpose, messages, **kwargs):
        key = _key("chat", [purpose, messages, sorted(kwargs.items())])
        hit = self._read(key)
        if hit is not None:
            return hit
        self.live_calls += 1
        result = await self._live_chat(purpose, messages, **kwargs)
        self._write(key, result)
        return result

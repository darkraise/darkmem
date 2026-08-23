"""LLM orchestrator that memoises embed + embed_batch + chat_completion to
disk.

Keyed by a hash of the call's content AND the resolved purpose config, so a
second bench run replays every model call from disk (self.live_calls stays 0)
while a swapped model, base_url, api_kind or output-shaping param misses
instead of replaying the previous configuration's answers under a new label.
The parent calls are indirected through
_live_embed / _live_embed_batch / _live_chat so tests can stub the model
without a live backend.

embed_batch is the seam ProcessingPipeline.process_batch actually uses (via
embed_batch_chunked, Phase 1 content embedding and Phase 3 entity embedding);
plain embed() is only exercised at query time (search), never by process_batch.
"""
import hashlib
import json
import os

from benchlib import bench_db  # noqa: F401  (ensures DATABASE_URL override first)
from app.services.llm import LLMOrchestrator


def _key(kind: str, payload) -> str:
    blob = json.dumps([kind, payload], sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# The resolved purpose fields that change what the model returns. api_key is
# deliberately absent: rotating a credential does not change an answer, and a
# secret has no business in a cache key.
_KEYED_CONFIG_FIELDS = ("model", "base_url", "api_kind", "dimensions", "reasoning", "params")


def _purpose_identity(config, purpose: str):
    cfg = config.get(purpose) if config else None
    if cfg is None:
        return None
    return {field: getattr(cfg, field, None) for field in _KEYED_CONFIG_FIELDS}


def chat_content(entry):
    """Read the response content out of either chat cache-entry shape.

    A bare string is this module's original format; a
    ``{"content": ..., "usage": ...}`` dict is the richer one
    ``benchlib.twin.TwinningOrchestrator`` writes so a replayed call can
    still report what it cost when it was paid. Both formats live in the
    same cache directory, so BOTH classes must read both -- a subclass
    that writes the richer shape into a cache this base class also reads
    would otherwise hand a caller a dict where the whole call surface
    promises a str.
    """
    return entry["content"] if isinstance(entry, dict) else entry


class CachingLLMOrchestrator(LLMOrchestrator):
    def __init__(self, config, cache_dir: str):
        super().__init__(config)
        self._cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.live_calls = 0
        # Every fingerprint embed_batch has resolved a vector under (cache hit
        # or live), so a caller can detect an embedder rotation mid-run by
        # checking this grows past one element. Callers that reuse one
        # orchestrator across multiple runs should .clear() it first.
        self.fingerprints_seen: set[str] = set()

    def _embed_key(self, text: str) -> str:
        return _key("embed", [text, _purpose_identity(self.config, "embedding")])

    #: Arguments that steer *metering*, not the model. ``usage_subject`` carries
    #: the memory id that paid for the call and ``usage_extra`` a note about what
    #: the call bundled; neither reaches the vendor and neither can change the
    #: response. Folding them in would key every entry to the run that produced
    #: it -- a fresh corpus has fresh ids -- so a replay would miss every entry
    #: and reach live, which is exactly the property G-C's clear rests on not
    #: happening. Excluded by name so a new kwarg is cached by default and has
    #: to be argued out, rather than silently ignored.
    _NON_CACHE_KWARGS = ("usage_subject", "usage_extra")

    def _chat_key(self, purpose, messages, kwargs) -> str:
        """The single definition of the chat cache key. Subclasses that
        override chat_completion resolve the key through here rather than
        recomposing the payload list, so a change to what the key folds in
        can never fork one class's entries away from another's."""
        keyed = {
            k: v for k, v in kwargs.items() if k not in self._NON_CACHE_KWARGS
        }
        return _key("chat", [
            purpose, _purpose_identity(self.config, purpose), messages, sorted(keyed.items()),
        ])

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

    async def _live_embed_batch(self, texts):
        return await super().embed_batch(texts)

    async def _live_chat(self, purpose, messages, **kwargs):
        return await super().chat_completion(purpose, messages, **kwargs)

    async def embed(self, text: str):
        key = self._embed_key(text)
        hit = self._read(key)
        if hit is not None:
            return hit[0], hit[1]
        self.live_calls += 1
        vec, fp = await self._live_embed(text)
        self._write(key, [vec, fp])
        return vec, fp

    async def embed_batch(self, texts: list[str]):
        """Per-text cache, one live call per batch of misses.

        ProcessingPipeline reaches embeddings only through embed_batch_chunked
        -> embed_batch (never the single-item embed()), for both Phase 1
        (content) and Phase 3 (entity names) -- see the module docstring.
        Keying per text rather than per whole-batch payload means a corpus
        that grows by one entry doesn't invalidate every previously-cached
        text in the same batch, and it shares cache entries with embed().

        live_calls counts live network round-trips, not texts: one increment
        per invocation of _live_embed_batch that actually fires, mirroring
        embed()/chat_completion()'s existing per-call granularity. A batch
        with any miss increments by exactly 1 regardless of how many texts
        missed, so the counter is exactly zero iff no live call fired during
        the run, and never zero when one did.
        """
        if not texts:
            return [], self.llm_fingerprint()

        keys = [self._embed_key(t) for t in texts]
        resolved: list[list | None] = [None] * len(texts)
        miss_positions = []
        for i, key in enumerate(keys):
            hit = self._read(key)
            if hit is None:
                miss_positions.append(i)
            else:
                resolved[i] = hit

        if miss_positions:
            self.live_calls += 1
            miss_texts = [texts[i] for i in miss_positions]
            vecs, fp = await self._live_embed_batch(miss_texts)
            for local_i, global_i in enumerate(miss_positions):
                entry = [vecs[local_i], fp]
                self._write(keys[global_i], entry)
                resolved[global_i] = entry

        # A stale cache entry from a prior embedder (or a live fetch landing
        # on a different fingerprint than what's cached) must not be silently
        # relabeled under one fingerprint -- that would mislabel which
        # partition the vector belongs to. embed_batch_chunked only compares
        # fingerprints ACROSS its chunk calls; this batch's own hit+miss mix
        # is invisible to that check, so it's re-checked here.
        fingerprints = {entry[1] for entry in resolved}
        if len(fingerprints) > 1:
            raise RuntimeError(
                f"embed_batch produced mixed fingerprints across cache + live "
                f"results: {sorted(fingerprints)}"
            )
        fingerprint = next(iter(fingerprints))
        self.fingerprints_seen.add(fingerprint)
        vectors = [entry[0] for entry in resolved]
        return vectors, fingerprint

    async def chat_completion(self, purpose, messages, **kwargs):
        key = self._chat_key(purpose, messages, kwargs)
        hit = self._read(key)
        if hit is not None:
            return chat_content(hit)
        self.live_calls += 1
        result = await self._live_chat(purpose, messages, **kwargs)
        self._write(key, result)
        return result
